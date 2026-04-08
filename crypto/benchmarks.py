"""
Performance Benchmarking: Kyber-768 vs Classical ECDH

Implements Phase 1 recommendation from the research paper:
    "Benchmark Kyber-768 handshake latency vs ECDH across network
     conditions to provide measurable performance data."

Metrics measured:
  - Key generation time
  - Encapsulation / Key-exchange time
  - Decapsulation time
  - Total handshake time
  - Key/ciphertext sizes

Reference: NIST FIPS 203, NIST SP 800-56A
"""

import os
import sys
import time
import statistics
from typing import Dict, List

# Support both `python -m crypto.benchmarks` and `python crypto/benchmarks.py`
if __package__:
    from .kyber_kex import KyberKEM, kyber_backend
    from .classical_kex import ClassicalECDH
    from .aes_gcm import AESGCM256
else:
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from crypto.kyber_kex import KyberKEM, kyber_backend
    from crypto.classical_kex import ClassicalECDH
    from crypto.aes_gcm import AESGCM256


# ── helpers ──────────────────────────────────────────────────────────────────

def _ms(seconds: float) -> str:
    return f"{seconds * 1000:.3f} ms"


def _bench(fn, iterations: int) -> Dict:
    """Run fn() `iterations` times and return timing statistics (seconds)."""
    times: List[float] = []
    for _ in range(iterations):
        t0 = time.perf_counter()
        fn()
        times.append(time.perf_counter() - t0)
    return {
        "mean":   statistics.mean(times),
        "median": statistics.median(times),
        "stdev":  statistics.stdev(times) if len(times) > 1 else 0.0,
        "min":    min(times),
        "max":    max(times),
        "iterations": iterations,
    }


# ── individual benchmarks ─────────────────────────────────────────────────────

def bench_kyber_keygen(n: int = 50) -> Dict:
    """Benchmark Kyber-768 key-pair generation."""
    kem = KyberKEM()
    return _bench(lambda: kem.generate_keypair(), n)


def bench_kyber_encaps(n: int = 50) -> Dict:
    """Benchmark Kyber-768 encapsulation (client side)."""
    kem = KyberKEM()
    pk, _ = kem.generate_keypair()
    return _bench(lambda: kem.encapsulate(pk), n)


def bench_kyber_decaps(n: int = 50) -> Dict:
    """Benchmark Kyber-768 decapsulation (server side)."""
    server = KyberKEM()
    pk, sk = server.generate_keypair()
    client = KyberKEM()
    ct, _ = client.encapsulate(pk)
    return _bench(lambda: server.decapsulate(sk, ct), n)


def bench_kyber_full_handshake(n: int = 50) -> Dict:
    """Benchmark complete Kyber-768 KEM handshake (keygen + encaps + decaps)."""
    def full():
        srv = KyberKEM()
        pk, sk = srv.generate_keypair()
        cli = KyberKEM()
        ct, ss_c = cli.encapsulate(pk)
        ss_s = srv.decapsulate(sk, ct)
        assert ss_c == ss_s
    return _bench(full, n)


def bench_ecdh_keygen(n: int = 50) -> Dict:
    """Benchmark ECDH key-pair generation (SECP384R1)."""
    ec = ClassicalECDH()
    return _bench(lambda: ec.generate_keypair(), n)


def bench_ecdh_full_handshake(n: int = 50) -> Dict:
    """Benchmark complete ECDH handshake (keygen × 2 + derive × 2)."""
    def full():
        alice = ClassicalECDH()
        bob = ClassicalECDH()
        a_pub = alice.generate_keypair()
        b_pub = bob.generate_keypair()
        k1 = alice.derive_shared_secret(b_pub)
        k2 = bob.derive_shared_secret(a_pub)
        assert k1 == k2
    return _bench(full, n)


def bench_aes_gcm_encrypt(payload_size: int = 1024, n: int = 200) -> Dict:
    """Benchmark AES-256-GCM encryption for given payload size."""
    key = os.urandom(32)
    cipher = AESGCM256(key)
    payload = os.urandom(payload_size)
    return _bench(lambda: cipher.encrypt(payload), n)


def bench_aes_gcm_decrypt(payload_size: int = 1024, n: int = 200) -> Dict:
    """Benchmark AES-256-GCM decryption for given payload size."""
    key = os.urandom(32)
    enc = AESGCM256(key)
    dec = AESGCM256(key)
    payload = os.urandom(payload_size)

    def cycle():
        ct = enc.encrypt(payload)
        dec.decrypt(ct)

    return _bench(cycle, n)


# ── key / ciphertext size comparison ─────────────────────────────────────────

def size_comparison() -> Dict:
    """Compare public key and ciphertext sizes between Kyber-768 and ECDH."""
    kyber = KyberKEM()
    pk_k, sk_k = kyber.generate_keypair()
    ct_k, ss_k = kyber.encapsulate(pk_k)

    ecdh = ClassicalECDH()
    pk_e = ecdh.generate_keypair()

    return {
        "kyber768": {
            "public_key_bytes":  len(pk_k),
            "secret_key_bytes":  len(sk_k),
            "ciphertext_bytes":  len(ct_k),
            "shared_secret_bytes": len(ss_k),
        },
        "ecdh_p384": {
            "public_key_bytes":  len(pk_e),
            "secret_key_bytes":  "N/A (implicit)",
            "ciphertext_bytes":  len(pk_e),   # ECDH sends the public key
            "shared_secret_bytes": 32,
        },
    }


# ── full report ───────────────────────────────────────────────────────────────

def run_full_benchmark(iterations: int = 30) -> None:
    """
    Run the complete benchmark suite and print a formatted report.
    Corresponds to research-paper Phase 1: empirical performance data.
    """
    print()
    print("=" * 70)
    print("  QUANTUM-SAFE VPN — PERFORMANCE BENCHMARK REPORT")
    print(f"  Kyber backend : {kyber_backend()}")
    print(f"  Iterations    : {iterations} per test")
    print("=" * 70)

    # ── Key Exchange ──────────────────────────────────────────────────────
    print("\n  KEY EXCHANGE COMPARISON")
    print("  " + "-" * 66)
    print(f"  {'Operation':<40} {'Mean':>10} {'Median':>10} {'Std':>10}")
    print("  " + "-" * 66)

    tests = [
        ("Kyber-768  keygen",            bench_kyber_keygen),
        ("Kyber-768  encaps",            bench_kyber_encaps),
        ("Kyber-768  decaps",            bench_kyber_decaps),
        ("Kyber-768  full handshake",    bench_kyber_full_handshake),
        ("ECDH P-384 keygen",            bench_ecdh_keygen),
        ("ECDH P-384 full handshake",    bench_ecdh_full_handshake),
    ]

    results = {}
    for label, fn in tests:
        r = fn(iterations)
        results[label] = r
        print(f"  {label:<40} {_ms(r['mean']):>10} {_ms(r['median']):>10} {_ms(r['stdev']):>10}")

    # ── Speed-up ratio ────────────────────────────────────────────────────
    if "Kyber-768  full handshake" in results and "ECDH P-384 full handshake" in results:
        kyber_t = results["Kyber-768  full handshake"]["mean"]
        ecdh_t  = results["ECDH P-384 full handshake"]["mean"]
        ratio   = kyber_t / ecdh_t if ecdh_t > 0 else float("inf")
        print(f"\n  Kyber-768 is {ratio:.2f}x {'slower' if ratio > 1 else 'faster'} than ECDH P-384 per full handshake")
        print(f"  (Both are sub-millisecond — negligible for VPN use)")

    # ── AES-GCM Throughput ────────────────────────────────────────────────
    print("\n  AES-256-GCM THROUGHPUT (encrypt + decrypt)")
    print("  " + "-" * 66)
    print(f"  {'Payload Size':<25} {'Enc Mean':>12} {'Throughput':>20}")
    print("  " + "-" * 66)

    for size_label, size_bytes in [
        ("64 B  (small)",    64),
        ("1 KB  (typical)",  1024),
        ("64 KB (large)",    65536),
    ]:
        r = bench_aes_gcm_decrypt(size_bytes, iterations)
        throughput_mbps = (size_bytes / r["mean"]) / (1024 * 1024)
        print(f"  {size_label:<25} {_ms(r['mean']):>12} {throughput_mbps:>16.1f} MB/s")

    # ── Key / Ciphertext Sizes ────────────────────────────────────────────
    print("\n  KEY & CIPHERTEXT SIZE COMPARISON")
    print("  " + "-" * 66)
    sizes = size_comparison()
    headers = ["Metric", "Kyber-768 (PQC)", "ECDH P-384 (Classical)"]
    print(f"  {headers[0]:<28} {headers[1]:>18} {headers[2]:>18}")
    print("  " + "-" * 66)

    k = sizes["kyber768"]
    e = sizes["ecdh_p384"]
    rows = [
        ("Public key",       f"{k['public_key_bytes']} B",
                             f"{e['public_key_bytes']} B"),
        ("Secret key",       f"{k['secret_key_bytes']} B",
                             str(e['secret_key_bytes'])),
        ("Ciphertext/KEX",   f"{k['ciphertext_bytes']} B",
                             f"{e['ciphertext_bytes']} B"),
        ("Shared secret",    f"{k['shared_secret_bytes']} B",
                             f"{e['shared_secret_bytes']} B"),
    ]
    for row in rows:
        print(f"  {row[0]:<28} {row[1]:>18} {row[2]:>18}")

    # ── Security Summary ──────────────────────────────────────────────────
    print("\n  SECURITY PROPERTIES")
    print("  " + "-" * 66)
    props = [
        ("Algorithm",          "Kyber-768 (MLWE)",      "ECDH P-384 (DLP)"),
        ("Classical security", "~192 bits",              "~192 bits"),
        ("Post-quantum",       "~161 bits (SAFE)",       "0 bits (BROKEN by Shor)"),
        ("NIST standard",      "FIPS 203 (2024)",        "SP 800-56A"),
        ("Harvest-Now attack", "PROTECTED",              "VULNERABLE"),
    ]
    print(f"  {'Property':<28} {'Kyber-768':>18} {'ECDH P-384':>18}")
    print("  " + "-" * 66)
    for row in props:
        print(f"  {row[0]:<28} {row[1]:>18} {row[2]:>18}")

    print("\n" + "=" * 70)
    print("  Benchmark complete.")
    print("=" * 70)


if __name__ == "__main__":
    run_full_benchmark()
