"""
Unit Tests for Quantum-Safe Mini-VPN Cryptography

Tests cover:
1. Classical ECDH key exchange
2. Kyber-768 post-quantum key exchange (NIST FIPS 203)
3. Hybrid key exchange (Kyber + ECDH)
4. AES-256-GCM encryption / decryption
5. Replay attack protection
6. Tampering detection
7. Integration: full VPN handshake + encrypted channel
8. Benchmarks: Kyber vs ECDH timing
"""

import pytest
import os
import sys
import time
import threading
import socket

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from crypto.classical_kex import ClassicalECDH
from crypto.kyber_kex import KyberKEM, kyber_backend
from crypto.hybrid_kex import HybridKeyExchange
from crypto.aes_gcm import AESGCM256, TamperingError, ReplayAttackError


# ── 1. Classical ECDH ────────────────────────────────────────────────────────

class TestClassicalECDH:
    """Tests for classical ECDH key exchange (quantum-vulnerable, for comparison)."""

    def test_keypair_generation(self):
        ecdh = ClassicalECDH()
        public_key = ecdh.generate_keypair()

        assert public_key is not None
        assert len(public_key) == 97          # Uncompressed P-384 point
        assert ecdh.private_key is not None
        assert ecdh.public_key is not None

    def test_key_exchange_produces_matching_keys(self):
        alice = ClassicalECDH()
        bob   = ClassicalECDH()

        alice_pub = alice.generate_keypair()
        bob_pub   = bob.generate_keypair()

        alice_key = alice.derive_shared_secret(bob_pub)
        bob_key   = bob.derive_shared_secret(alice_pub)

        assert alice_key == bob_key            # MUST match
        assert len(alice_key) == 32            # AES-256 key

    def test_different_sessions_produce_different_keys(self):
        def run_session():
            a = ClassicalECDH()
            b = ClassicalECDH()
            a.generate_keypair()
            b_pub = b.generate_keypair()
            return a.derive_shared_secret(b_pub)

        key1 = run_session()
        key2 = run_session()
        assert key1 != key2                    # Each session is unique

    def test_wrong_peer_key_gives_different_result(self):
        alice = ClassicalECDH()
        bob   = ClassicalECDH()
        eve   = ClassicalECDH()

        alice.generate_keypair()
        bob.generate_keypair()
        eve_pub = eve.generate_keypair()

        alice_key = alice.derive_shared_secret(bob.public_key.public_bytes(
            __import__('cryptography.hazmat.primitives.serialization', fromlist=['Encoding','PublicFormat']).Encoding.X962,
            __import__('cryptography.hazmat.primitives.serialization', fromlist=['Encoding','PublicFormat']).PublicFormat.UncompressedPoint,
        ))
        # Alice uses Eve's public key instead of Bob's → different shared secret
        alice_eve_key = ClassicalECDH()
        alice_eve_key.private_key = alice.private_key
        alice_eve_key.public_key  = alice.public_key
        alice_eve_result = alice_eve_key.derive_shared_secret(eve_pub)

        assert alice_key != alice_eve_result


# ── 2. Kyber-768 Post-Quantum KEM ────────────────────────────────────────────

class TestKyberKEM:
    """Tests for the real CRYSTALS-Kyber-768 KEM (NIST FIPS 203)."""

    def test_backend_is_real_kyber(self):
        """Verify we are running real kyber-py, not the fallback."""
        assert 'kyber-py' in kyber_backend(), (
            f"Expected real kyber-py backend, got: {kyber_backend()}"
        )

    def test_keypair_generation_correct_sizes(self):
        kyber = KyberKEM()
        pk, sk = kyber.generate_keypair()

        assert len(pk) == KyberKEM.PK_SIZE, f"pk should be {KyberKEM.PK_SIZE} bytes"
        assert len(sk) == KyberKEM.SK_SIZE, f"sk should be {KyberKEM.SK_SIZE} bytes"

    def test_encapsulate_returns_correct_sizes(self):
        kyber = KyberKEM()
        pk, _ = kyber.generate_keypair()
        ct, ss = kyber.encapsulate(pk)

        assert len(ct) == KyberKEM.CT_SIZE, f"ciphertext should be {KyberKEM.CT_SIZE} bytes"
        assert len(ss) == KyberKEM.SS_SIZE, f"shared secret should be {KyberKEM.SS_SIZE} bytes"

    def test_shared_secrets_match(self):
        """Core correctness: encapsulate and decapsulate MUST produce the same secret."""
        server = KyberKEM()
        server_pk, server_sk = server.generate_keypair()

        client = KyberKEM()
        ciphertext, client_secret = client.encapsulate(server_pk)

        server_secret = server.decapsulate(server_sk, ciphertext)

        assert client_secret == server_secret, (
            "Kyber-768 shared secrets must match after encaps/decaps"
        )

    def test_shared_secret_is_32_bytes(self):
        kyber = KyberKEM()
        pk, sk = kyber.generate_keypair()
        ct, ss = kyber.encapsulate(pk)
        assert len(ss) == 32

    def test_different_ciphertext_each_encapsulation(self):
        """Re-encapsulation with the same public key must yield different ciphertexts."""
        kyber = KyberKEM()
        pk, _ = kyber.generate_keypair()

        ct1, ss1 = kyber.encapsulate(pk)
        ct2, ss2 = kyber.encapsulate(pk)

        assert ct1 != ct2   # Random encapsulation
        assert ss1 != ss2   # Different shared secrets

    def test_wrong_sk_gives_different_secret(self):
        """Decapsulating with wrong secret key must NOT produce the correct secret."""
        server1 = KyberKEM()
        pk1, sk1 = server1.generate_keypair()

        server2 = KyberKEM()
        _, sk2 = server2.generate_keypair()

        client = KyberKEM()
        ct, correct_ss = client.encapsulate(pk1)

        wrong_ss = server1.decapsulate(sk2, ct)   # wrong key
        assert wrong_ss != correct_ss

    def test_multiple_independent_sessions(self):
        """Multiple independent key exchanges each produce unique, matching secrets."""
        for _ in range(5):
            srv = KyberKEM()
            pk, sk = srv.generate_keypair()
            ct, ss_enc = KyberKEM().encapsulate(pk)
            ss_dec = srv.decapsulate(sk, ct)
            assert ss_enc == ss_dec


# ── 3. Hybrid Key Exchange ───────────────────────────────────────────────────

class TestHybridKeyExchange:
    """Tests for hybrid Kyber-768 + ECDH key exchange."""

    def test_keypair_generation(self):
        hybrid = HybridKeyExchange()
        ecdh_pub, kyber_pub, kyber_sk = hybrid.generate_keypairs()

        assert ecdh_pub   is not None
        assert kyber_pub  is not None
        assert kyber_sk   is not None

    def test_full_exchange_keys_match(self):
        """Server and client MUST derive the identical combined session key."""
        server = HybridKeyExchange()
        server_ecdh_pub, server_kyber_pub, server_kyber_sk = server.generate_keypairs()

        client = HybridKeyExchange()
        client_ecdh_pub, _, _ = client.generate_keypairs()

        kyber_ct, client_key = client.initiate_exchange(
            server_ecdh_pub, server_kyber_pub
        )
        server_key = server.complete_exchange(
            client_ecdh_pub, server_kyber_sk, kyber_ct
        )

        assert client_key == server_key, (
            "Hybrid KEM: client and server session keys must match"
        )
        assert len(client_key) == 32

    def test_hybrid_key_size(self):
        server = HybridKeyExchange()
        s_ep, s_kp, s_ks = server.generate_keypairs()
        client = HybridKeyExchange()
        c_ep, _, _ = client.generate_keypairs()
        kt, ck = client.initiate_exchange(s_ep, s_kp)
        assert len(ck) == 32

    def test_different_sessions_different_keys(self):
        def run():
            srv = HybridKeyExchange()
            ep, kp, ks = srv.generate_keypairs()
            cli = HybridKeyExchange()
            cep, _, _ = cli.generate_keypairs()
            kt, ck = cli.initiate_exchange(ep, kp)
            sk = srv.complete_exchange(cep, ks, kt)
            return ck, sk

        k1c, k1s = run()
        k2c, k2s = run()
        assert k1c == k1s          # Within session: must match
        assert k2c == k2s
        assert k1c != k2c          # Across sessions: must differ


# ── 4. AES-256-GCM ──────────────────────────────────────────────────────────

class TestAESGCM:
    """Tests for AES-256-GCM authenticated encryption."""

    def test_encrypt_decrypt_roundtrip(self):
        key = os.urandom(32)
        sender   = AESGCM256(key)
        receiver = AESGCM256(key)

        plaintext = b"Hello, quantum-safe world!"
        assert receiver.decrypt(sender.encrypt(plaintext)) == plaintext

    def test_encryption_overhead_is_36_bytes(self):
        key    = os.urandom(32)
        cipher = AESGCM256(key)
        pt     = b"Test message"
        ct     = cipher.encrypt(pt)
        assert len(ct) == len(pt) + cipher.get_overhead()  # 36 bytes

    def test_unique_nonce_each_encryption(self):
        key    = os.urandom(32)
        cipher = AESGCM256(key)
        pt     = b"Same plaintext"
        assert cipher.encrypt(pt) != cipher.encrypt(pt)

    def test_tampering_detection_single_bit(self):
        key  = os.urandom(32)
        sndr = AESGCM256(key)
        rcvr = AESGCM256(key)
        ct   = sndr.encrypt(b"Sensitive data")
        bad  = bytearray(ct)
        bad[25] ^= 0xFF
        with pytest.raises(TamperingError):
            rcvr.decrypt(bytes(bad))

    def test_tampering_all_positions(self):
        """Any single-byte flip anywhere in the packet must be detected."""
        key  = os.urandom(32)
        sndr = AESGCM256(key)
        rcvr = AESGCM256(key)
        ct   = sndr.encrypt(b"Integrity test payload")
        for pos in [5, 10, 15, 20, 25, 30, -1, -5, -10]:
            bad = bytearray(ct)
            idx = pos if pos >= 0 else len(bad) + pos
            if 0 <= idx < len(bad):
                bad[idx] ^= 0x01
                try:
                    rcvr.decrypt(bytes(bad))
                    pytest.fail(f"Byte flip at pos {pos} was not detected!")
                except (TamperingError, ReplayAttackError, Exception):
                    pass   # expected

    def test_replay_attack_blocked(self):
        key  = os.urandom(32)
        sndr = AESGCM256(key)
        rcvr = AESGCM256(key)
        ct1  = sndr.encrypt(b"First message")
        ct2  = sndr.encrypt(b"Second message")
        rcvr.decrypt(ct1)
        rcvr.decrypt(ct2)
        with pytest.raises(ReplayAttackError):
            rcvr.decrypt(ct1)           # replay of ct1

    def test_duplicate_packet_blocked(self):
        key  = os.urandom(32)
        sndr = AESGCM256(key)
        rcvr = AESGCM256(key)
        ct   = sndr.encrypt(b"Don't duplicate me!")
        rcvr.decrypt(ct)                # first time OK
        with pytest.raises(ReplayAttackError):
            rcvr.decrypt(ct)            # second time rejected

    def test_invalid_key_length(self):
        with pytest.raises(ValueError):
            AESGCM256(b"too short")
        with pytest.raises(ValueError):
            AESGCM256(os.urandom(16))   # 128-bit rejected

    def test_statistics_tracking(self):
        key  = os.urandom(32)
        sndr = AESGCM256(key)
        rcvr = AESGCM256(key)
        msg  = b"Hello stats"
        ct   = sndr.encrypt(msg)
        rcvr.decrypt(ct)
        stats = sndr.get_stats()
        assert stats['packets_sent'] == 1
        assert stats['bytes_encrypted'] == len(msg)


# ── 5. Integration ───────────────────────────────────────────────────────────

class TestIntegration:
    """End-to-end integration tests combining all cryptographic components."""

    def test_full_vpn_handshake_and_communication(self):
        """
        Full protocol: Hybrid key exchange → AES-256-GCM channel.
        Both parties MUST encrypt/decrypt successfully with matching session keys.
        """
        # Key exchange
        server = HybridKeyExchange()
        client = HybridKeyExchange()

        s_ep, s_kp, s_ks = server.generate_keypairs()
        c_ep, _,   _     = client.generate_keypairs()

        kt, client_key   = client.initiate_exchange(s_ep, s_kp)
        server_key       = server.complete_exchange(c_ep, s_ks, kt)

        assert client_key == server_key, "Session keys must match before communication"

        # Encrypted channel
        c_cipher = AESGCM256(client_key)
        s_cipher = AESGCM256(server_key)

        for msg in [b"Ping!", b"Classified data", b"\x00" * 512, b"A" * 4096]:
            ct  = c_cipher.encrypt(msg)
            out = s_cipher.decrypt(ct)
            assert out == msg, f"Decrypted output must equal original for {msg[:16]!r}"

    def test_bidirectional_communication(self):
        """Client and server can send messages in both directions."""
        server = HybridKeyExchange()
        client = HybridKeyExchange()

        s_ep, s_kp, s_ks = server.generate_keypairs()
        c_ep, _,   _     = client.generate_keypairs()

        kt, client_key = client.initiate_exchange(s_ep, s_kp)
        server_key     = server.complete_exchange(c_ep, s_ks, kt)

        c2s = AESGCM256(client_key)
        s2c_enc = AESGCM256(server_key)
        c2s_dec = AESGCM256(server_key)
        s2c_dec = AESGCM256(client_key)

        # Client → Server
        ct = c2s.encrypt(b"Hello Server")
        assert c2s_dec.decrypt(ct) == b"Hello Server"

        # Server → Client
        ct2 = s2c_enc.encrypt(b"Hello Client")
        assert s2c_dec.decrypt(ct2) == b"Hello Client"

    def test_multiple_sequential_messages(self):
        """A sequence of messages all decrypt correctly in order."""
        key  = os.urandom(32)
        sndr = AESGCM256(key)
        rcvr = AESGCM256(key)

        messages = [b"msg1", b"msg2", b"", b"A" * 1000, b"\xff" * 256]
        for msg in messages:
            assert rcvr.decrypt(sndr.encrypt(msg)) == msg

    def test_server_client_socket_tunnel(self):
        """
        Spin up a real TCP server/client in threads, perform hybrid key exchange
        over sockets, then exchange encrypted messages — verifying the full
        networking + crypto stack end-to-end.
        """
        errors  = []
        results = {}

        # ── server thread ─────────────────────────────────────────────────
        def server_thread():
            try:
                srv_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                srv_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                srv_sock.bind(('127.0.0.1', 0))
                srv_sock.listen(1)
                results['port'] = srv_sock.getsockname()[1]
                results['ready'] = True

                conn, _ = srv_sock.accept()

                def send(data):
                    conn.sendall(len(data).to_bytes(4, 'big') + data)

                def recv():
                    n = int.from_bytes(_recv_exact(conn, 4), 'big')
                    return _recv_exact(conn, n)

                kex = HybridKeyExchange()
                ep, kp, ks = kex.generate_keypairs()
                c_ep = recv(); c_kp = recv()
                send(ep); send(kp)
                kt = recv()
                key = kex.complete_exchange(c_ep, ks, kt)

                cipher = AESGCM256(key)
                msg = cipher.decrypt(recv())
                results['server_received'] = msg
                send(cipher.encrypt(b"Server ACK: " + msg))

                conn.close()
                srv_sock.close()
            except Exception as exc:
                errors.append(('server', exc))

        # ── client thread ─────────────────────────────────────────────────
        def client_thread():
            try:
                while 'ready' not in results:
                    time.sleep(0.01)
                port = results['port']

                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.connect(('127.0.0.1', port))

                def send(data):
                    sock.sendall(len(data).to_bytes(4, 'big') + data)

                def recv():
                    n = int.from_bytes(_recv_exact(sock, 4), 'big')
                    return _recv_exact(sock, n)

                kex = HybridKeyExchange()
                ep, kp, ks = kex.generate_keypairs()
                send(ep); send(kp)
                s_ep = recv(); s_kp = recv()
                kt, key = kex.initiate_exchange(s_ep, s_kp)
                send(kt)

                cipher = AESGCM256(key)
                secret_msg = b"Quantum-safe tunnel payload"
                send(cipher.encrypt(secret_msg))
                ack = cipher.decrypt(recv())
                results['ack'] = ack

                sock.close()
            except Exception as exc:
                errors.append(('client', exc))

        def _recv_exact(s, n):
            buf = b''
            while len(buf) < n:
                chunk = s.recv(n - len(buf))
                assert chunk, "Connection closed"
                buf += chunk
            return buf

        t_srv = threading.Thread(target=server_thread, daemon=True)
        t_cli = threading.Thread(target=client_thread, daemon=True)
        t_srv.start()
        t_cli.start()
        t_srv.join(timeout=10)
        t_cli.join(timeout=10)

        assert not errors, f"Socket tunnel errors: {errors}"
        assert results.get('server_received') == b"Quantum-safe tunnel payload"
        assert results.get('ack', b'').startswith(b"Server ACK:")


# ── 6. Security Properties ───────────────────────────────────────────────────

class TestSecurityProperties:
    """Higher-level security property tests."""

    def test_ciphertext_looks_random(self):
        """Encrypted output of repetitive plaintext must appear random (high entropy)."""
        key    = os.urandom(32)
        cipher = AESGCM256(key)
        pt     = b"AAAA" * 100
        ct     = cipher.encrypt(pt)
        unique = len(set(ct[20:-16]))     # skip counter/nonce/tag
        assert unique > 50

    def test_kyber_shared_secret_is_random(self):
        """Two fresh Kyber encapsulations must not produce the same shared secret."""
        kyber = KyberKEM()
        pk, _ = kyber.generate_keypair()
        _, ss1 = kyber.encapsulate(pk)
        _, ss2 = kyber.encapsulate(pk)
        assert ss1 != ss2

    def test_hybrid_key_changes_each_session(self):
        """Each hybrid handshake produces a distinct session key."""
        def run():
            srv = HybridKeyExchange()
            ep, kp, ks = srv.generate_keypairs()
            cli = HybridKeyExchange()
            cep, _, _ = cli.generate_keypairs()
            kt, ck = cli.initiate_exchange(ep, kp)
            return ck

        assert run() != run()

    def test_aes_gcm_counter_increments(self):
        key    = os.urandom(32)
        cipher = AESGCM256(key)
        for _ in range(5):
            cipher.encrypt(b"x")
        assert cipher.send_counter == 5


# ── 7. Benchmarks ────────────────────────────────────────────────────────────

class TestBenchmarks:
    """Light performance smoke-tests (not strict timing assertions)."""

    def test_kyber_keygen_runs_in_reasonable_time(self):
        kyber = KyberKEM()
        t0 = time.perf_counter()
        for _ in range(10):
            kyber.generate_keypair()
        elapsed = time.perf_counter() - t0
        assert elapsed < 10.0, f"10 Kyber keygens took {elapsed:.2f}s — too slow"

    def test_kyber_vs_ecdh_latency(self):
        """Report relative latency; do not enforce a hard ratio."""
        n = 10

        t0 = time.perf_counter()
        for _ in range(n):
            k = KyberKEM(); pk, sk = k.generate_keypair()
            ct, ss1 = k.encapsulate(pk); k.decapsulate(sk, ct)
        kyber_t = (time.perf_counter() - t0) / n

        t0 = time.perf_counter()
        for _ in range(n):
            a = ClassicalECDH(); b = ClassicalECDH()
            ap = a.generate_keypair(); bp = b.generate_keypair()
            a.derive_shared_secret(bp); b.derive_shared_secret(ap)
        ecdh_t = (time.perf_counter() - t0) / n

        print(f"\n  [Benchmark] Kyber-768 handshake : {kyber_t*1000:.2f} ms/op")
        print(f"  [Benchmark] ECDH P-384 handshake: {ecdh_t*1000:.2f} ms/op")
        ratio = kyber_t / ecdh_t if ecdh_t > 0 else 1
        print(f"  [Benchmark] Ratio (Kyber/ECDH)  : {ratio:.2f}x")
        # Both should complete well within 1 second per handshake
        assert kyber_t < 1.0
        assert ecdh_t  < 1.0

    def test_aes_gcm_throughput(self):
        key    = os.urandom(32)
        cipher = AESGCM256(key)
        rcvr   = AESGCM256(key)
        payload = os.urandom(64 * 1024)   # 64 KB
        n       = 20
        t0      = time.perf_counter()
        for _ in range(n):
            rcvr.decrypt(cipher.encrypt(payload))
        elapsed = time.perf_counter() - t0
        mbps = (n * len(payload)) / elapsed / (1024 ** 2)
        print(f"\n  [Benchmark] AES-256-GCM throughput: {mbps:.1f} MB/s")
        assert mbps > 1.0, "AES-GCM should encrypt faster than 1 MB/s"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
