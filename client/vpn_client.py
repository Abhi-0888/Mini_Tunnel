"""
VPN Client - Quantum-Safe Encrypted Tunnel
==========================================
Connects to any device on the LAN running vpn_server.py.

Usage:
    py -3 client/vpn_client.py                         # localhost
    py -3 client/vpn_client.py --host 192.168.1.10     # LAN device
    py -3 client/vpn_client.py --host 192.168.1.10 --port 5001  # via MITM
    py -3 client/vpn_client.py --host 192.168.1.10 --demo       # automated
"""

import socket
import sys
import threading
import argparse
import os
import time
from datetime import datetime

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


class VPNClient:
    """Quantum-Safe VPN Client (Kyber-768 + ECDH + AES-256-GCM)."""

    def __init__(self, host='localhost', port=5000):
        self.host = host
        self.port = port
        self.sock = None
        self.cipher = None
        self.running = False
        self._kex = HybridKeyExchange()
        self.session_key = None

    def _log(self, msg, colour=X):
        print(f"  {colour}[{_ts()}] {msg}{X}")
    
    # ── socket helpers ───────────────────────────────────────────────────────────

    def _recv_exact(self, n):
        buf = b''
        while len(buf) < n:
            chunk = self.sock.recv(n - len(buf))
            if not chunk:
                raise ConnectionError('Connection closed')
            buf += chunk
        return buf

    def _send_data(self, data):
        self.sock.sendall(len(data).to_bytes(4, 'big') + data)

    def _recv_data(self):
        n = int.from_bytes(self._recv_exact(4), 'big')
        return self._recv_exact(n)

    # ── connection & handshake ───────────────────────────────────────────────

    def connect(self):
        print(f"\n{B}{C}{'='*62}{X}")
        print(f"{B}{C}  QUANTUM-SAFE VPN CLIENT{X}")
        print(f"{B}{C}{'='*62}{X}")
        print(f"  {D}Connecting to:{X} {B}{self.host}:{self.port}{X}\n")

        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.connect((self.host, self.port))
            self._log(f"TCP connected to {self.host}:{self.port}", G)
        except ConnectionRefusedError:
            print(f"  {R}Connection refused — is the server running?{X}")
            return False
        except Exception as exc:
            print(f"  {R}Connection error: {exc}{X}")
            return False

        return self._handshake()

    def _handshake(self):
        self._log('Starting Kyber-768 + ECDH P-384 handshake...', C)
        try:
            # Generate our keypairs
            c_ep, c_kp, c_ks = self._kex.generate_keypairs()
            self._log(f'  Client ECDH pub: {len(c_ep)} B | '
                      f'Client Kyber pub: {len(c_kp)} B', D)

            # Send our public keys first
            self._send_data(c_ep)
            self._send_data(c_kp)

            # Receive server public keys
            s_ep = self._recv_data()
            s_kp = self._recv_data()
            self._log(f'  Server ECDH pub: {len(s_ep)} B | '
                      f'Server Kyber pub: {len(s_kp)} B', D)

            # Encapsulate + send Kyber ciphertext
            t0 = time.perf_counter()
            kyber_ct, session_key = self._kex.initiate_exchange(s_ep, s_kp)
            kex_ms = (time.perf_counter() - t0) * 1000
            self._send_data(kyber_ct)

            self.session_key = session_key
            self.cipher = AESGCM256(session_key)

            self._log(f'Key exchange done in {kex_ms:.1f} ms  '
                      f'key={session_key.hex()[:16]}...', G)
            print(f"\n  {G}Secure tunnel established!{X}")
            print(f"  {D}Algorithm : Kyber-768 + ECDH P-384 (Hybrid){X}")
            print(f"  {D}Session   : AES-256-GCM authenticated encryption{X}")
            print(f"  {D}Kyber CT  : {len(kyber_ct)} bytes sent  |  "
                  f"ECDH pub: {len(c_ep)} bytes sent{X}")

            # PQC verification
            pqc_ok = (_REAL_KYBER and len(s_kp) == 1184
                      and len(kyber_ct) == 1088 and len(session_key) == 32)
            print(f"\n  {C}┌─ PQC PROOF {'─'*46}┐{X}")
            print(f"  {C}│{X} Backend : {G if _REAL_KYBER else R}{kyber_backend()}{X}")
            print(f"  {C}│{X} Kyber pk: {len(s_kp)} B {'✓' if len(s_kp)==1184 else '✗'}  "
                  f"ct: {len(kyber_ct)} B {'✓' if len(kyber_ct)==1088 else '✗'}  "
                  f"key: {len(session_key)} B {'✓' if len(session_key)==32 else '✗'}")
            print(f"  {C}│{X} Lattice : n=256, k=3, q=3329 (Module-LWE)")
            print(f"  {C}│{X} Verdict : {G+'REAL POST-QUANTUM CRYPTO' if pqc_ok else R+'FALLBACK'}{X}")
            print(f"  {C}└{'─'*58}┘{X}")

            # Receive server-initiated welcome (proves server→client works)
            try:
                welcome_raw = self._recv_data()
                welcome_pt = self.cipher.decrypt(welcome_raw)
                welcome_msg = welcome_pt.decode('utf-8', errors='replace')
                print(f"\n  {C}┌─ SERVER→CLIENT (bidirectional proof) {'─'*20}┐{X}")
                print(f"  {C}│{X} {D}Wire  [{len(welcome_raw):4d} B]:{X} {welcome_raw.hex()[:48]}…")
                print(f"  {C}│{X} {C}Plain [{len(welcome_pt):4d} B]:{X} {welcome_msg[:65]}")
                print(f"  {C}└{'─'*58}┘{X}\n")
            except Exception:
                pass

            return True

        except Exception as exc:
            self._log(f'Handshake error: {exc}', R)
            return False

    # ── send / receive ─────────────────────────────────────────────────────────

    def send(self, plaintext: bytes):
        ct = self.cipher.encrypt(plaintext)
        msg = plaintext.decode('utf-8', errors='replace')
        print(f"\n  {G}┌─ SEND {'─'*52}┐{X}")
        print(f"  {G}│{X} {B}Plain  [{len(plaintext):4d} B]:{X} {msg[:65]}")
        print(f"  {G}│{X} {D}Wire   [{len(ct):4d} B]:{X} {ct.hex()[:48]}…")
        print(f"  {G}│{X} {D}Nonce  [  12 B]  Counter [  8 B]  GCM-Tag [ 16 B]{X}")
        print(f"  {G}└{'─'*58}┘{X}")
        self._send_data(ct)

    def recv(self):
        raw = self._recv_data()
        try:
            pt = self.cipher.decrypt(raw)
            msg = pt.decode('utf-8', errors='replace')
            print(f"  {C}┌─ RECV {'─'*52}┐{X}")
            print(f"  {C}│{X} {D}Wire   [{len(raw):4d} B]:{X} {raw.hex()[:48]}…")
            print(f"  {C}│{X} {C}Plain  [{len(pt):4d} B]:{X} {msg[:65]}")
            print(f"  {C}└{'─'*58}┘{X}")
            return pt
        except TamperingError:
            print(f"  {R}┌─ ⚡ TAMPERING on server response! {'─'*23}┐{X}")
            print(f"  {R}│{X} GCM tag invalid — server/MITM tampered the ACK")
            print(f"  {R}└{'─'*58}┘{X}")
            return None
        except ReplayAttackError:
            print(f"  {R}┌─ 🔁 REPLAY on server response! {'─'*26}┐{X}")
            print(f"  {R}└{'─'*58}┘{X}")
            return None

    # ── interactive & demo modes ──────────────────────────────────────────────

    def interactive(self):
        self.running = True
        threading.Thread(target=self._recv_loop, daemon=True).start()

        print(f"  {B}VPN Tunnel ready. All traffic is encrypted with AES-256-GCM.{X}")
        print(f"  {D}Tunnel commands:{X}")
        print(f"    {C}fetch <url>{X}     — HTTP request tunneled through VPN (proves IP masking)")
        print(f"    {C}resolve <host>{X}  — DNS query tunneled through VPN (proves DNS privacy)")
        print(f"    {C}verify{X}          — cryptographic proof that Kyber-768 PQC is real")
        print(f"    {C}ping{X}            — encrypted round-trip latency test")
        print(f"    {C}stats{X}           — show encryption statistics")
        print(f"    {C}quit{X}            — close VPN tunnel\n")

        try:
            while self.running:
                msg = input(f'  {B}VPN>{X} ').strip()
                if not msg:
                    continue
                if msg.lower() == 'quit':
                    break
                if msg.lower() == 'stats':
                    print(f'  Stats: {self.cipher.get_stats()}')
                    continue
                if msg.lower().startswith('fetch '):
                    url = msg[6:].strip()
                    if not url.startswith('http'):
                        url = 'http://' + url
                    print(f"  {C}Tunneling HTTP request through VPN…{X}")
                    self.send(f'TUNNEL:FETCH:{url}'.encode())
                    resp = self.recv()
                    continue
                if msg.lower().startswith('resolve '):
                    domain = msg[8:].strip()
                    print(f"  {C}Tunneling DNS lookup through VPN…{X}")
                    self.send(f'TUNNEL:DNS:{domain}'.encode())
                    resp = self.recv()
                    continue
                if msg.lower() == 'verify':
                    print(f"  {C}Requesting server-side PQC verification…{X}")
                    self.send(b'TUNNEL:VERIFY')
                    resp = self.recv()
                    continue
                if msg.lower() == 'ping':
                    t0 = time.perf_counter()
                    self.send(b'TUNNEL:FETCH:http://httpbin.org/get')
                    resp = self.recv()
                    rtt = (time.perf_counter() - t0) * 1000
                    print(f"  {G}VPN round-trip: {rtt:.0f} ms (encrypted){X}")
                    continue
                # Any other text = encrypted tunnel echo test
                print(f"  {D}[tunnel echo test — encrypting and sending through VPN]{X}")
                self.send(msg.encode())
        except (KeyboardInterrupt, EOFError):
            pass
        finally:
            self.disconnect()

    def run_demo(self, messages=None):
        demo_steps = [
            ('verify', b'',                        'PQC PROOF — verify Kyber-768 is real NIST crypto'),
            ('dns',    b'google.com',              'DNS TUNNEL - resolve google.com through VPN'),
            ('dns',    b'github.com',              'DNS TUNNEL - resolve github.com through VPN'),
            ('fetch',  b'http://httpbin.org/ip',   'HTTP TUNNEL - fetch our public IP through VPN (proves IP masking)'),
            ('fetch',  b'http://httpbin.org/headers', 'HTTP TUNNEL - fetch request headers through VPN'),
            ('echo',   b'CLASSIFIED: Troop movement at 0600 UTC - Sector 7', 'ECHO TEST - encrypted payload through tunnel'),
            ('echo',   b'EHR: Patient 00421 - critical alert acknowledged',    'ECHO TEST - sensitive data encrypted in transit'),
            ('ping',   b'',                        'LATENCY TEST - encrypted VPN round-trip'),
        ]
        total = len(demo_steps)
        print(f"  {B}Running VPN tunnel demo ({total} steps)...{X}\n")
        for i, (kind, payload, desc) in enumerate(demo_steps, 1):
            print(f"  {D}─── Step {i}/{total}: {desc} ───{X}")
            if kind == 'echo':
                print(f"  {D}[encrypting and tunneling payload]{X}")
                self.send(payload)
                self.recv()
            elif kind == 'dns':
                print(f"  {C}Tunneling DNS: {payload.decode()}{X}")
                self.send(b'TUNNEL:DNS:' + payload)
                self.recv()
            elif kind == 'fetch':
                print(f"  {C}Tunneling HTTP: {payload.decode()}{X}")
                self.send(b'TUNNEL:FETCH:' + payload)
                self.recv()
            elif kind == 'verify':
                print(f"  {C}Requesting server-side Kyber-768 encaps/decaps test…{X}")
                self.send(b'TUNNEL:VERIFY')
                self.recv()
            elif kind == 'ping':
                t0 = time.perf_counter()
                self.send(b'TUNNEL:FETCH:http://httpbin.org/get')
                self.recv()
                rtt = (time.perf_counter() - t0) * 1000
                print(f"  {G}VPN round-trip: {rtt:.0f} ms (encrypted end-to-end){X}")
            time.sleep(0.5)
        print(f"\n  {G}Demo complete. All traffic was encrypted with AES-256-GCM")
        print(f"  through a Kyber-768 + ECDH P-384 quantum-safe tunnel.{X}")
        self.disconnect()

    def _recv_loop(self):
        while self.running:
            try:
                raw = self._recv_data()
                if not raw:
                    break
                try:
                    pt = self.cipher.decrypt(raw)
                    msg = pt.decode('utf-8', errors='replace')
                    print(f"\n  {C}┌─ RECV ({'─'*52})┐{X}")
                    print(f"  {C}│{X} {D}Wire  [{len(raw):4d} B]:{X} {raw.hex()[:48]}…")
                    print(f"  {C}│{X} {C}Plain [{len(pt):4d} B]:{X} {msg[:65]}")
                    print(f"  {C}└{'─'*58}┘{X}")
                    print(f'  {B}VPN>{X} ', end='', flush=True)
                except Exception:
                    pass
            except Exception:
                break

    def disconnect(self):
        self.running = False
        try:
            self.sock.close()
        except Exception:
            pass
        print(f"\n  {Y}Disconnected.{X}")

    def get_stats(self):
        return self.cipher.get_stats() if self.cipher else {}


def main():
    ap = argparse.ArgumentParser(description='Quantum-Safe VPN Client')
    ap.add_argument('--host', default='localhost',
                    help='VPN server IP  (default: localhost)')
    ap.add_argument('--port', type=int, default=5000,
                    help='VPN server port (default: 5000)')
    ap.add_argument('--demo', action='store_true',
                    help='Run automated 5-message demo then exit')
    a = ap.parse_args()

    client = VPNClient(host=a.host, port=a.port)
    if not client.connect():
        sys.exit(1)

    if a.demo:
        client.run_demo()
    else:
        client.interactive()


if __name__ == '__main__':
    main()
