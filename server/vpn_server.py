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
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from crypto.hybrid_kex import HybridKeyExchange
from crypto.aes_gcm import AESGCM256, TamperingError, ReplayAttackError

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
                self.clients[addr] = cipher

            # ── Encrypted tunnel loop ─────────────────────────────────────────
            print(f"\n  {G}┌{'─'*58}┐{X}")
            print(f"  {G}│  TUNNEL ACTIVE  {cid:<40}│{X}")
            print(f"  {G}└{'─'*58}┘{X}\n")

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
                    self._event('attack', client=cid, kind='TAMPERING',
                                detail='GCM authentication tag mismatch',
                                enc_preview=raw.hex()[:48])

                except ReplayAttackError as e:
                    with self._lock:
                        self.stats['attacks'] += 1
                    print(f"  {R}┌─ 🔁 REPLAY ATTACK BLOCKED ────────────────────────────┐{X}")
                    print(f"  {R}│{X} Duplicate counter — packet from {cid}")
                    print(f"  {R}│{X} {D}Wire  [{len(raw):4d} B]:{X} {raw.hex()[:48]}…")
                    print(f"  {R}│{X} {R}Result: DROPPED — counter already in recv_window{X}")
                    print(f"  {R}└{'─'*58}┘{X}\n")
                    self._event('attack', client=cid, kind='REPLAY',
                                detail=str(e), enc_preview=raw.hex()[:48])

        except ConnectionError:
            self._log(f"[{cid}] Disconnected", Y)
            self._event('client_disconnect', client=cid)
        except Exception as exc:
            self._log(f"[{cid}] Error: {exc}", R)
            self._event('error', client=cid, detail=str(exc))
        finally:
            with self._lock:
                self.clients.pop(addr, None)
            try:
                conn.close()
            except Exception:
                pass

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
