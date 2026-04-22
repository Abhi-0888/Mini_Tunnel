"""
VPN Server - Quantum-Safe Encrypted Tunnel
==========================================
Real-network VPN server binding to 0.0.0.0 (all interfaces).
Reachable from any device on the LAN.

Features:
- Hybrid Kyber-768 + ECDH P-384 key exchange (NIST FIPS 203)
- AES-256-GCM authenticated encryption
- Replay & tampering attack detection
- Live event callbacks for web dashboard
- Multiple simultaneous clients

Usage (standalone):
    py -3 server/vpn_server.py [--host 0.0.0.0] [--port 5000]

Usage (from launch_demo.py):
    server = VPNServer(event_callback=emit_fn)
    threading.Thread(target=server.start, daemon=True).start()
"""
import os
import sys
import socket
import threading
import time
import argparse
import json
from datetime import datetime
from urllib.request import urlopen, Request
from urllib.error import URLError

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from crypto.hybrid_kex import HybridKeyExchange
from crypto.aes_gcm import AESGCM256, TamperingError, ReplayAttackError
from crypto.kyber_kex import kyber_backend, _REAL_KYBER

if os.name == 'nt':
    os.system('color')
G = '\033[92m'; R = '\033[91m'; Y = '\033[93m'
C = '\033[96m'; B = '\033[1m';  D = '\033[2m'; X = '\033[0m'


def _ts():
    return datetime.now().strftime('%H:%M:%S.%f')[:-3]


class VPNServer:
    """
    Quantum-Safe VPN Server.
    Binds to 0.0.0.0 so any LAN device can connect.
    Pass event_callback=fn(event_type, **kwargs) for live dashboard.
    """
    
    def __init__(self, host='0.0.0.0', port=5000, event_callback=None):
        self.host = host
        self.port = port
        self._emit = event_callback
        self.clients = {}
        self._lock = threading.Lock()
        self.stats = {'connections': 0, 'packets': 0, 'attacks': 0, 'kex_done': 0}

    # ── helpers ───────────────────────────────────────────────────────────────

    def _log(self, msg, colour=X):
        print(f"  {colour}[{_ts()}] {msg}{X}")

    def _event(self, etype, **kw):
        if self._emit:
            try:
                self._emit(etype, timestamp=_ts(), **kw)
            except Exception:
                pass

    def _recv_exact(self, conn, n):
        buf = b''
        while len(buf) < n:
            chunk = conn.recv(n - len(buf))
            if not chunk:
                raise ConnectionError('Connection closed')
            buf += chunk
        return buf

    def _send_data(self, conn, data):
        conn.sendall(len(data).to_bytes(4, 'big') + data)

    def _recv_data(self, conn):
        n = int.from_bytes(self._recv_exact(conn, 4), 'big')
        return self._recv_exact(conn, n)

    # ── per-client handler ────────────────────────────────────────────────────

    def _handle_client(self, conn, addr):
        cid = f"{addr[0]}:{addr[1]}"
        self._log(f"New connection: {B}{cid}{X}", G)
        with self._lock:
            self.stats['connections'] += 1
        self._event('client_connect', client=cid, ip=addr[0], port=addr[1])

        try:
            # ── Hybrid Kyber-768 + ECDH key exchange ──────────────────────────
            self._log(f"[{cid}] Starting Kyber-768 + ECDH handshake...", C)
            kex = HybridKeyExchange()
            s_ep, s_kp, s_ks = kex.generate_keypairs()

            self._event('kex_start', client=cid,
                        kyber_pk_bytes=len(s_kp), ecdh_pk_bytes=len(s_ep))

            # Receive client's public keys, then send ours
            c_ep = self._recv_data(conn)
            c_kp = self._recv_data(conn)
            self._send_data(conn, s_ep)
            self._send_data(conn, s_kp)

            # Receive Kyber ciphertext and complete key exchange
            kyber_ct = self._recv_data(conn)
            t0 = time.perf_counter()
            session_key = kex.complete_exchange(c_ep, s_ks, kyber_ct)
            kex_ms = (time.perf_counter() - t0) * 1000

            self._log(f"[{cid}] Key exchange OK in {kex_ms:.1f} ms  "
                      f"key={session_key.hex()[:12]}...", G)
            with self._lock:
                self.stats['kex_done'] += 1
            self._event('kex_done', client=cid,
                        latency_ms=round(kex_ms, 1),
                        key_preview=session_key.hex()[:16],
                        algorithm='Kyber-768 + ECDH P-384',
                        kyber_ct_bytes=len(kyber_ct))

            cipher = AESGCM256(session_key)
            with self._lock:
                self.clients[cid] = {'conn': conn, 'cipher': cipher, 'addr': addr}

            # ── PQC verification output ──────────────────────────────────────
            pqc_ok = (_REAL_KYBER and len(s_kp) == 1184
                      and len(kyber_ct) == 1088 and len(session_key) == 32)
            print(f"\n  {C}┌─ PQC VERIFICATION {'─'*39}┐{X}")
            print(f"  {C}│{X} Backend   : {G if _REAL_KYBER else R}{kyber_backend()}{X}")
            print(f"  {C}│{X} Kyber pk  : {len(s_kp):5d} B  (NIST spec: 1184) {'✓' if len(s_kp)==1184 else '✗'}")
            print(f"  {C}│{X} Kyber ct  : {len(kyber_ct):5d} B  (NIST spec: 1088) {'✓' if len(kyber_ct)==1088 else '✗'}")
            print(f"  {C}│{X} Secret    :    {len(session_key):2d} B  (256-bit key)    {'✓' if len(session_key)==32 else '✗'}")
            print(f"  {C}│{X} ECDH pk   :    {len(s_ep):2d} B  (P-384 uncompressed)")
            print(f"  {C}│{X} Lattice   : n=256, k=3, q=3329 (Module-LWE)")
            print(f"  {C}│{X} Quantum   : {'~161 qubits (Level 3) — SECURE' if pqc_ok else 'UNVERIFIED'}")
            print(f"  {C}└{'─'*58}┘{X}")

            self._event('pqc_verify', client=cid, real_kyber=_REAL_KYBER,
                        backend=kyber_backend(),
                        pk_bytes=len(s_kp), ct_bytes=len(kyber_ct),
                        key_bytes=len(session_key), verified=pqc_ok)

            # ── Encrypted tunnel loop ─────────────────────────────────────────
            print(f"\n  {G}┌{'─'*58}┐{X}")
            print(f"  {G}│  TUNNEL ACTIVE  {cid:<40}│{X}")
            print(f"  {G}└{'─'*58}┘{X}\n")

            # Server-initiated welcome (proves bidirectional)
            welcome = (f"[SERVER→CLIENT] Welcome! Tunnel ready. "
                       f"PQC={'VERIFIED' if pqc_ok else 'UNVERIFIED'} | "
                       f"Backend: {kyber_backend()}")
            self._send_data(conn, cipher.encrypt(welcome.encode()))
            self._log(f"[{cid}] Sent server-initiated welcome (bidirectional proof)", C)

            pkt_num = 0
            while True:
                raw = self._recv_data(conn)
                pkt_num += 1
                try:
                    plaintext = cipher.decrypt(raw)
                    msg = plaintext.decode('utf-8', errors='replace')
                    with self._lock:
                        self.stats['packets'] += 1
                    hex_preview = raw.hex()[:48]

                    # ── Tunnel commands ──────────────────────────────────────
                    response = self._handle_tunnel_cmd(msg, cid)
                    if response is not None:
                        self._send_data(conn, cipher.encrypt(response.encode()))
                        continue

                    print(f"  {G}┌─ PKT #{pkt_num:03d} ── from {cid} {'─'*max(0,30-len(cid))}┐{X}")
                    print(f"  {G}│{X} {D}Wire  [{len(raw):4d} B]:{X} {hex_preview}…")
                    print(f"  {G}│{X} {G}Plain [{len(plaintext):4d} B]:{X} {B}{msg[:70]}{X}")
                    print(f"  {G}└{'─'*58}┘{X}\n")
                    self._event('message', client=cid,
                                content=msg,
                                enc_preview=raw.hex()[:48],
                                pkt_bytes=len(raw))
                    ack = f"[SERVER] ACK #{pkt_num} — decrypted: '{msg}'"
                    self._send_data(conn, cipher.encrypt(ack.encode()))

                except TamperingError:
                    with self._lock:
                        self.stats['attacks'] += 1
                    print(f"  {R}┌─ ⚡ TAMPERING ATTACK BLOCKED ─────────────────────────┐{X}")
                    print(f"  {R}│{X} GCM auth tag mismatch — packet from {cid}")
                    print(f"  {R}│{X} {D}Wire  [{len(raw):4d} B]:{X} {raw.hex()[:48]}…")
                    print(f"  {R}│{X} {R}Result: DROPPED — attacker cannot forge a valid GCM tag{X}")
                    print(f"  {R}└{'─'*58}┘{X}\n")
                    # Send attack event to dashboard with detailed explanation
                    self._event('attack', client=cid, kind='TAMPERING',
                                detail='GCM authentication tag mismatch — 1 flipped bit invalidates 128-bit GHASH',
                                enc_preview=raw.hex()[:48],
                                pkt_bytes=len(raw),
                                reason='Attacker modified ciphertext but cannot forge valid auth tag without AES key')

                except ReplayAttackError as e:
                    with self._lock:
                        self.stats['attacks'] += 1
                    print(f"  {R}┌─ 🔁 REPLAY ATTACK BLOCKED ────────────────────────────┐{X}")
                    print(f"  {R}│{X} Duplicate counter — packet from {cid}")
                    print(f"  {R}│{X} {D}Wire  [{len(raw):4d} B]:{X} {raw.hex()[:48]}…")
                    print(f"  {R}│{X} {R}Result: DROPPED — counter already in recv_window{X}")
                    print(f"  {R}└{'─'*58}┘{X}\n")
                    # Send attack event to dashboard with detailed explanation
                    self._event('attack', client=cid, kind='REPLAY',
                                detail=f'{str(e)} — 64-packet sliding window rejects duplicates',
                                enc_preview=raw.hex()[:48],
                                pkt_bytes=len(raw),
                                reason='Attacker resent same packet but counter already processed')

        except ConnectionError:
            self._log(f"[{cid}] Disconnected", Y)
            self._event('client_disconnect', client=cid)
        except Exception as exc:
            self._log(f"[{cid}] Error: {exc}", R)
            self._event('error', client=cid, detail=str(exc))
        finally:
            with self._lock:
                self.clients.pop(cid, None)
            try:
                conn.close()
            except Exception:
                pass

    # ── tunnel command handler ─────────────────────────────────────────────────

    def _handle_tunnel_cmd(self, msg, cid):
        """Handle tunnel proxy commands. Returns response string or None."""

        # TUNNEL:FETCH:<url> — server fetches URL and returns body through VPN
        if msg.startswith('TUNNEL:FETCH:'):
            url = msg[13:].strip()
            print(f"  {C}┌─ 🌐 TUNNEL FETCH ── from {cid} {'─'*max(0,25-len(cid))}┐{X}")
            print(f"  {C}│{X} URL: {url}")
            self._event('tunnel', client=cid, kind='FETCH', target=url)
            try:
                req = Request(url, headers={'User-Agent': 'QuantumVPN-Tunnel/1.0'})
                with urlopen(req, timeout=8) as resp:
                    body = resp.read(4096).decode('utf-8', errors='replace')
                    status = resp.status
                print(f"  {C}│{X} {G}Status: {status} | Body: {len(body)} B{X}")
                print(f"  {C}└{'─'*58}┘{X}\n")
                return f"[TUNNEL:FETCH] HTTP {status} | {body[:2048]}"
            except Exception as e:
                print(f"  {C}│{X} {R}Error: {e}{X}")
                print(f"  {C}└{'─'*58}┘{X}\n")
                return f"[TUNNEL:FETCH] ERROR: {e}"

        # TUNNEL:DNS:<domain> — server resolves DNS and returns IPs
        if msg.startswith('TUNNEL:DNS:'):
            domain = msg[11:].strip()
            print(f"  {C}┌─ 🔍 TUNNEL DNS ── from {cid} {'─'*max(0,27-len(cid))}┐{X}")
            print(f"  {C}│{X} Domain: {domain}")
            self._event('tunnel', client=cid, kind='DNS', target=domain)
            try:
                results = socket.getaddrinfo(domain, None, socket.AF_INET)
                ips = sorted(set(r[4][0] for r in results))
                print(f"  {C}│{X} {G}Resolved: {', '.join(ips)}{X}")
                print(f"  {C}└{'─'*58}┘{X}\n")
                return f"[TUNNEL:DNS] {domain} → {', '.join(ips)}"
            except Exception as e:
                print(f"  {C}│{X} {R}Error: {e}{X}")
                print(f"  {C}└{'─'*58}┘{X}\n")
                return f"[TUNNEL:DNS] ERROR: {e}"

        # TUNNEL:VERIFY — independent PQC verification
        if msg.startswith('TUNNEL:VERIFY'):
            print(f"  {C}┌─ 🔬 PQC VERIFY REQUEST ── from {cid} {'─'*max(0,18-len(cid))}┐{X}")
            print(f"  {C}└{'─'*58}┘{X}\n")
            self._event('tunnel', client=cid, kind='VERIFY', target='PQC')
            from crypto.kyber_kex import KyberKEM
            kem = KyberKEM()
            pk, sk = kem.generate_keypair()
            ct, ss1 = kem.encapsulate(pk)
            ss2 = kem.decapsulate(sk, ct)
            match = (ss1 == ss2)
            result = json.dumps({
                'backend': kyber_backend(),
                'real_kyber': _REAL_KYBER,
                'pk_bytes': len(pk), 'nist_pk': 1184,
                'ct_bytes': len(ct), 'nist_ct': 1088,
                'ss_bytes': len(ss1), 'nist_ss': 32,
                'encaps_decaps_match': match,
                'lattice': 'n=256 k=3 q=3329 (Module-LWE)',
                'quantum_security': '~161 qubits (NIST Level 3)',
                'standard': 'FIPS 203 (Aug 2024)',
                'verdict': 'REAL POST-QUANTUM CRYPTO' if (match and _REAL_KYBER) else 'FALLBACK MODE'
            }, indent=2)
            return f"[TUNNEL:VERIFY]\n{result}"

        return None

    # ── public API ────────────────────────────────────────────────────────────

    def start(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as srv:
            srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            srv.bind((self.host, self.port))
            srv.listen(20)

            try:
                local_ip = socket.gethostbyname(socket.gethostname())
            except Exception:
                local_ip = '127.0.0.1'

            print(f"\n{B}{C}{'='*62}{X}")
            print(f"{B}{C}  QUANTUM-SAFE VPN SERVER  (Kyber-768 / NIST FIPS 203){X}")
            print(f"{B}{C}{'='*62}{X}")
            print(f"  {G}VPN  port   :{X} {B}0.0.0.0:{self.port}{X}")
            print(f"  {G}LAN IP      :{X} {B}{local_ip}{X}")
            print(f"  {G}Dashboard   :{X} {B}http://{local_ip}:8080{X}")
            print(f"\n  {D}Run client  :{X} py -3 client/vpn_client.py --host {local_ip}")
            print(f"  {D}Run attacker:{X} py -3 attacks/mitm_proxy.py --target {local_ip}")
            print(f"\n{B}{C}{'='*62}{X}\n")

            self._event('server_start', host=local_ip, port=self.port)

            while True:
                try:
                    conn, addr = srv.accept()
                    threading.Thread(
                        target=self._handle_client,
                        args=(conn, addr),
                        daemon=True
                    ).start()
                except KeyboardInterrupt:
                    break
                except Exception as exc:
                    self._log(f"Accept error: {exc}", R)


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description='Quantum-Safe VPN Server')
    ap.add_argument('--host', default='0.0.0.0')
    ap.add_argument('--port', type=int, default=5000)
    a = ap.parse_args()
    VPNServer(host=a.host, port=a.port).start()
