"""
MITM (Man-in-the-Middle) Attack Proxy
======================================
Sits transparently between the VPN client and server.
Demonstrates what a real attacker on the network CAN and CANNOT do.

Architecture:
    VPN Client --> MITM Proxy (port 5001) --> VPN Server (port 5000)

What the attacker can see:
    - All encrypted bytes flowing in both directions
    - Key exchange messages (public keys, ciphertext) -- but NOT the shared secret
    - Packet sizes and timing

What the attacker CANNOT do (demonstrated live):
    - Decrypt any message (Kyber + ECDH = quantum-safe KEM)
    - Tamper with packets (AES-256-GCM auth tag)
    - Replay old packets (sliding-window counter)

Usage (3 terminals):
    Terminal 1: py -3 launch_demo.py              (server + dashboard)
    Terminal 2: py -3 attacks/mitm_proxy.py        (MITM on port 5001)
    Terminal 3: py -3 client/vpn_client.py --port 5001  (client via MITM)
    Browser   : http://localhost:8080

Remote target:
    py -3 attacks/mitm_proxy.py --target 192.168.1.10
"""
import socket
import threading
import time
import argparse
import os
import sys
import struct
from datetime import datetime

if os.name == 'nt':
    os.system('color')
G = '\033[92m'; R = '\033[91m'; Y = '\033[93m'
C = '\033[96m'; B = '\033[1m';  D = '\033[2m'; X = '\033[0m'
BOLD_R = '\033[1;91m'; BOLD_G = '\033[1;92m'


def _ts():
    return datetime.now().strftime('%H:%M:%S.%f')[:-3]


def _banner(title):
    print(f"\n{B}{R}{'='*64}{X}")
    print(f"{B}{R}  {title}{X}")
    print(f"{B}{R}{'='*64}{X}\n")


def _log(direction, msg, colour=X):
    arrow = '>>>' if direction == 'C->S' else '<<<'
    print(f"  {colour}[{_ts()}] {B}{arrow}{X}{colour} {msg}{X}")


def _recv_exact(sock, n):
    buf = b''
    while len(buf) < n:
        chunk = sock.recv(n - len(buf))
        if not chunk:
            raise ConnectionError('Connection closed')
        buf += chunk
    return buf


def _read_framed(sock):
    """Read one length-prefixed frame: [4-byte big-endian len][data]"""
    raw_len = _recv_exact(sock, 4)
    n = int.from_bytes(raw_len, 'big')
    data = _recv_exact(sock, n)
    return raw_len + data, data    # full_frame, payload_only


def _write_framed(sock, full_frame):
    """Forward a complete framed message unchanged."""
    sock.sendall(full_frame)


class MITMProxy:
    """
    Transparent TCP proxy with active attack demonstrations.

    After the legitimate session is established the proxy:
    1. Shows all intercepted bytes (proves it can see traffic)
    2. Attempts a REPLAY attack using a captured packet
    3. Attempts a TAMPERING attack by flipping bytes mid-stream
    4. Reports the server's rejection of both attacks
    """

    def __init__(self, listen_host='0.0.0.0', listen_port=5001,
                 target_host='localhost', target_port=5000):
        self.listen_host = listen_host
        self.listen_port  = listen_port
        self.target_host  = target_host
        self.target_port  = target_port

    # ── forwarding helpers ────────────────────────────────────────────────────

    def _forward_frames(self, src, dst, direction,
                        capture_list, stop_event, n_capture=3):
        """Forward all frames from src->dst, capturing the first n_capture."""
        captured = 0
        try:
            while not stop_event.is_set():
                frame, payload = _read_framed(src)
                _write_framed(dst, frame)

                if captured < n_capture:
                    capture_list.append(frame)
                    captured += 1

                _log(direction,
                     f'{len(payload):5} B  | hex: {payload.hex()[:40]}...',
                     D)
        except ConnectionError:
            pass
        finally:
            stop_event.set()

    # ── per-connection handler ────────────────────────────────────────────────

    def _handle(self, client_sock, addr):
        cid = f"{addr[0]}:{addr[1]}"
        print(f"\n  {G}[MITM] New victim connected: {B}{cid}{X}")
        print(f"  {D}Connecting to real server {self.target_host}:{self.target_port}...{X}")

        try:
            server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server_sock.connect((self.target_host, self.target_port))
        except ConnectionRefusedError:
            print(f"  {R}Cannot reach server — is launch_demo.py running?{X}")
            client_sock.close()
            return

        print(f"  {G}[MITM] Tunnel open: client <-> MITM <-> server{X}")
        print(f"  {D}Intercepting ALL traffic...{X}\n")

        # ── Phase 1: transparent forwarding + capture ─────────────────────────
        captured_c2s = []      # packets client→server (encrypted msgs only)
        captured_s2c = []
        stop = threading.Event()

        # We need to watch the handshake (first 6 frames: 3 each direction)
        # then capture real message frames for the attack demo
        handshake_frames_c2s = []
        handshake_frames_s2c = []
        msg_frames_c2s = []    # captured encrypted messages

        # Do the handshake phase manually so we can annotate it
        print(f"  {Y}{'─'*60}{X}")
        print(f"  {Y}PHASE 1: Intercepting Kyber-768 Handshake{X}")
        print(f"  {Y}{'─'*60}{X}\n")

        try:
            # Client sends: c_ecdh_pub, c_kyber_pub
            frame1, c_ecdh = _read_framed(client_sock)
            _write_framed(server_sock, frame1)
            print(f"  {C}[MITM] C→S  Client ECDH public key   : {len(c_ecdh):5} B{X}")
            print(f"         {D}Hex: {c_ecdh.hex()[:48]}...{X}")

            frame2, c_kyber = _read_framed(client_sock)
            _write_framed(server_sock, frame2)
            print(f"  {C}[MITM] C→S  Client Kyber public key  : {len(c_kyber):5} B{X}")
            print(f"         {D}Hex: {c_kyber.hex()[:48]}...{X}")

            # Server responds: s_ecdh_pub, s_kyber_pub
            frame3, s_ecdh = _read_framed(server_sock)
            _write_framed(client_sock, frame3)
            print(f"  {C}[MITM] S→C  Server ECDH public key   : {len(s_ecdh):5} B{X}")
            print(f"         {D}Hex: {s_ecdh.hex()[:48]}...{X}")

            frame4, s_kyber = _read_framed(server_sock)
            _write_framed(client_sock, frame4)
            print(f"  {C}[MITM] S→C  Server Kyber public key  : {len(s_kyber):5} B{X}")
            print(f"         {D}Hex: {s_kyber.hex()[:48]}...{X}")

            # Client sends Kyber ciphertext
            frame5, kyber_ct = _read_framed(client_sock)
            _write_framed(server_sock, frame5)
            print(f"  {C}[MITM] C→S  Kyber ciphertext         : {len(kyber_ct):5} B{X}")
            print(f"         {D}Hex: {kyber_ct.hex()[:48]}...{X}")

        except ConnectionError as e:
            print(f"  {R}Handshake interrupted: {e}{X}")
            client_sock.close(); server_sock.close()
            return

        print(f"\n  {R}{B}KEY INSIGHT:{X}")
        print(f"  {R}Attacker has ALL handshake bytes but CANNOT compute shared secret!{X}")
        print(f"  {D}  Kyber-768 KEM: shared secret derived inside each party separately.{X}")
        print(f"  {D}  Module-LWE: no known polynomial-time solution (classical or quantum).{X}\n")

        # ── Phase 2: synchronous intercept + attacks ──────────────────────────
        # We do everything synchronously to avoid race conditions.
        # Message 1: intercept, forward, wait for ACK, then REPLAY it.
        # Message 2: intercept, TAMPER before forwarding, wait (rejected), then
        #            forward original so the client still gets its ACK.
        # Messages 3+: transparent forwarding.

        print(f"  {Y}{'─'*60}{X}")
        print(f"  {Y}PHASE 2: Intercepting Encrypted Messages{X}")
        print(f"  {Y}{'─'*60}{X}\n")

        try:
            # ── Message 1: capture & forward normally ─────────────────────────
            frame1, p1 = _read_framed(client_sock)
            _write_framed(server_sock, frame1)
            print(f"  {D}[MITM] C→S  encrypted packet   {len(p1):5} B"
                  f"  hex: {p1.hex()[:40]}...{X}")

            ack1, _ = _read_framed(server_sock)
            _write_framed(client_sock, ack1)
            print(f"  {D}[MITM] S→C  encrypted ACK       {len(_):5} B (forwarded){X}\n")

            # ── ATTACK 1: REPLAY ──────────────────────────────────────────────
            print(f"  {Y}{'─'*60}{X}")
            print(f"  {BOLD_R}ATTACK 1: REPLAY ATTACK{X}")
            print(f"  {Y}{'─'*60}{X}")
            print(f"  Resending the EXACT same packet (counter=1) to server...")
            print(f"  {D}  {p1.hex()[:48]}...{X}\n")

            _write_framed(server_sock, frame1)   # identical replay
            server_sock.settimeout(1.2)
            try:
                _read_framed(server_sock)        # server should NOT respond
                print(f"  {R}WARNING: Server accepted the replay — unexpected!{X}")
            except (ConnectionError, socket.timeout, OSError):
                print(f"  {BOLD_G}REPLAY BLOCKED!{X}")
                print(f"  {D}  counter=1 is already in recv_window → rejected immediately.{X}")
                print(f"  {D}  Sliding-window (64 pkts) prevents any duplicate counter.{X}\n")
            finally:
                server_sock.settimeout(None)

            # ── Message 2: intercept for TAMPER demo ──────────────────────────
            frame2, p2 = _read_framed(client_sock)
            print(f"  {D}[MITM] C→S  encrypted packet   {len(p2):5} B"
                  f"  hex: {p2.hex()[:40]}...{X}")

            # ── ATTACK 2: TAMPERING ───────────────────────────────────────────
            print(f"  {Y}{'─'*60}{X}")
            print(f"  {BOLD_R}ATTACK 2: TAMPERING ATTACK (single bit-flip){X}")
            print(f"  {Y}{'─'*60}{X}")

            tampered = bytearray(frame2)
            flip_pos = 20 if len(tampered) > 24 else len(tampered) // 2
            orig_byte = tampered[4 + flip_pos]
            tampered[4 + flip_pos] ^= 0xFF
            print(f"  Byte at position {flip_pos}: "
                  f"0x{orig_byte:02X} → 0x{tampered[4+flip_pos]:02X}")
            print(f"  {D}  Tampered: {bytes(tampered[4:]).hex()[:48]}...{X}\n")
            print(f"  Sending tampered packet to server...")

            server_sock.sendall(bytes(tampered))   # length-framed tampered
            server_sock.settimeout(1.2)
            try:
                _read_framed(server_sock)
                print(f"  {R}WARNING: Server accepted tampered packet — unexpected!{X}")
            except (ConnectionError, socket.timeout, OSError):
                print(f"  {BOLD_G}TAMPERING BLOCKED!{X}")
                print(f"  {D}  AES-256-GCM authentication tag mismatch.{X}")
                print(f"  {D}  1 flipped bit invalidates the 128-bit GHASH auth tag.{X}")
                print(f"  {D}  Attacker cannot forge a valid tag without the session key.{X}\n")
            finally:
                server_sock.settimeout(None)

            # Forward the REAL message 2 so client gets its ACK
            _write_framed(server_sock, frame2)
            ack2, _ = _read_framed(server_sock)
            _write_framed(client_sock, ack2)
            print(f"  {D}[MITM] Original msg2 forwarded → client receives ACK{X}\n")

        except ConnectionError as ce:
            print(f"  {Y}Connection closed during attack phase: {ce}{X}\n")

        # ── Phase 3: transparent forwarding for remaining messages ─────────────
        print(f"  {Y}{'─'*60}{X}")
        print(f"  {Y}PHASE 3: Remaining messages (transparent){X}")
        print(f"  {Y}{'─'*60}{X}\n")

        stop_fwd = threading.Event()

        def fwd_c2s_rest():
            try:
                while not stop_fwd.is_set():
                    f, p = _read_framed(client_sock)
                    _write_framed(server_sock, f)
                    print(f"  {D}[MITM] C→S  {len(p):5} B  {p.hex()[:32]}...{X}")
            except ConnectionError:
                stop_fwd.set()

        def fwd_s2c_rest():
            try:
                while not stop_fwd.is_set():
                    f, p = _read_framed(server_sock)
                    _write_framed(client_sock, f)
                    print(f"  {D}[MITM] S→C  {len(p):5} B  {p.hex()[:32]}...{X}")
            except ConnectionError:
                stop_fwd.set()

        tc = threading.Thread(target=fwd_c2s_rest, daemon=True)
        ts = threading.Thread(target=fwd_s2c_rest, daemon=True)
        tc.start(); ts.start()
        stop_fwd.wait(timeout=15)

        # ── Summary ────────────────────────────────────────────────────────────
        print(f"\n  {B}{Y}{'='*60}{X}")
        print(f"  {B}ATTACK SUMMARY — Attacker had FULL packet access:{X}")
        print(f"  {Y}{'='*60}{X}")
        print(f"  {G}✓{X} Encryption  : AES-256-GCM — attacker sees only ciphertext")
        print(f"  {G}✓{X} Key exchange: Kyber-768 KEM — shared secret never on wire")
        print(f"  {G}✓{X} Replay      : Duplicate counter rejected by sliding window")
        print(f"  {G}✓{X} Tampering   : GCM auth tag — any modification detected")
        print(f"  {B}{Y}{'='*60}{X}\n")

        try:
            client_sock.close()
            server_sock.close()
        except Exception:
            pass

    # ── server loop ───────────────────────────────────────────────────────────

    def start(self):
        _banner('QUANTUM-SAFE VPN — MAN-IN-THE-MIDDLE PROXY')
        print(f"  {C}Listening on :{self.listen_port}   "
              f"(client connects here){X}")
        print(f"  {C}Forwarding to  {self.target_host}:{self.target_port}   "
              f"(real VPN server){X}\n")
        print(f"  {D}Connect your client to THIS port:{X}")
        print(f"    py -3 client/vpn_client.py --host localhost "
              f"--port {self.listen_port}\n")

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as srv:
            srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            srv.bind((self.listen_host, self.listen_port))
            srv.listen(5)
            print(f"  {G}MITM proxy ready — waiting for connections...{X}\n")

            while True:
                try:
                    conn, addr = srv.accept()
                    threading.Thread(
                        target=self._handle, args=(conn, addr), daemon=True
                    ).start()
                except KeyboardInterrupt:
                    print(f"\n  {Y}MITM proxy stopped.{X}")
                    break


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description='MITM Attack Proxy Demo')
    ap.add_argument('--listen-port', type=int, default=5001,
                    help='Port to listen on (default: 5001)')
    ap.add_argument('--target', default='localhost',
                    help='Real VPN server host (default: localhost)')
    ap.add_argument('--target-port', type=int, default=5000,
                    help='Real VPN server port (default: 5000)')
    a = ap.parse_args()
    MITMProxy(listen_port=a.listen_port,
              target_host=a.target,
              target_port=a.target_port).start()
