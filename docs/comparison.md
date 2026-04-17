# 📊 Classical vs Post-Quantum Cryptography Comparison

This document provides a detailed comparison between classical cryptographic algorithms and their post-quantum replacements used in this project.

---

## Executive Summary

| Aspect | Classical (ECDH) | Post-Quantum (Kyber) |
|--------|------------------|----------------------|
| Quantum Safety | ❌ Broken by Shor | ✅ Secure |
| Standardization | NIST (decades) | NIST FIPS 203 (2024) |
| Maturity | Very high | Emerging |
| Performance | Fast | Faster! |
| Key Sizes | Small | Larger |

---

## Key Exchange Comparison

### ECDH (Elliptic Curve Diffie-Hellman)

**Mathematical Foundation**: Elliptic Curve Discrete Logarithm Problem (ECDLP)

```
Given elliptic curve E over field F_p:
  - Generator point G
  - Public point P = k·G (scalar multiplication)

Problem: Given (G, P), find k
Classical: Hard (exponential time)
Quantum: EASY (Shor's algorithm - polynomial time!)
```

**Used in**:
- TLS 1.3 (default)
- WireGuard VPN
- Signal Protocol
- SSH

### Kyber (ML-KEM)

**Mathematical Foundation**: Module Learning With Errors (M-LWE)

```
Given:
  - Random matrix A ∈ Z_q^(k×k)
  - Public: b = A·s + e  (s is secret, e is small error)

Problem: Given (A, b), find s
Classical: Hard
Quantum: ALSO HARD! (no efficient quantum algorithm known)
```

**Standardized as**:
- NIST FIPS 203 (ML-KEM)
- Available in Kyber-512, Kyber-768, Kyber-1024

---

## Parameter Comparison

### Key Sizes

| Algorithm | Public Key | Private Key | Ciphertext | Shared Secret |
|-----------|------------|-------------|------------|---------------|
| ECDH P-256 | 64 bytes | 32 bytes | 64 bytes | 32 bytes |
| ECDH P-384 | 96 bytes | 48 bytes | 96 bytes | 48 bytes |
| Kyber-512 | 800 bytes | 1,632 bytes | 768 bytes | 32 bytes |
| **Kyber-768** | **1,184 bytes** | **2,400 bytes** | **1,088 bytes** | **32 bytes** |
| Kyber-1024 | 1,568 bytes | 3,168 bytes | 1,568 bytes | 32 bytes |

**Observation**: Kyber keys are ~10-30x larger than ECDH keys.

### Security Levels

| Algorithm | Classical Security | Quantum Security* |
|-----------|-------------------|-------------------|
| ECDH P-256 | 128-bit | **0-bit** (broken) |
| ECDH P-384 | 192-bit | **0-bit** (broken) |
| Kyber-512 | 128-bit | 64-bit |
| **Kyber-768** | **192-bit** | **128-bit** ✅ |
| Kyber-1024 | 256-bit | 192-bit |

*Quantum security assumes existence of large-scale quantum computers

---

## Performance Comparison

### Operation Speed (ops/second on modern CPU)

| Operation | ECDH P-384 | Kyber-768 | Winner |
|-----------|------------|-----------|--------|
| Key Generation | ~15,000 | ~50,000 | **Kyber** |
| Encapsulation/Agreement | ~15,000 | ~55,000 | **Kyber** |
| Decapsulation | ~15,000 | ~45,000 | **Kyber** |

**Surprise!** Kyber is faster than ECDH despite larger keys.

### Bandwidth Impact

| Protocol | Handshake Size | Overhead |
|----------|----------------|----------|
| TLS 1.3 (ECDH) | ~2-3 KB | Baseline |
| TLS (Kyber hybrid) | ~4-5 KB | +100% |
| Our VPN (Kyber+ECDH) | ~6 KB | First packet only |

**Note**: Key exchange overhead is negligible compared to total session traffic.

---

## Algorithm Details

### Classical ECDH Flow

```
Alice                                Bob
  │                                    │
  │  a ← random                        │  b ← random
  │  A = a·G (public)                  │  B = b·G (public)
  │                                    │
  │────────────── A ──────────────────►│
  │◄───────────── B ───────────────────│
  │                                    │
  │  K = a·B = a·b·G                   │  K = b·A = a·b·G
  │                                    │
  └───────── Same shared secret K ─────┘

⚠️ Quantum Attack:
   Given (A, B), Shor's algorithm finds (a, b)!
```

### Post-Quantum Kyber Flow

```
Alice                                Bob
  │                                    │
  │  (pk, sk) = Kyber.KeyGen()         │
  │                                    │
  │──────────────── pk ───────────────►│
  │                                    │  (ct, ss) = Kyber.Encaps(pk)
  │◄───────────── ct ──────────────────│
  │                                    │
  │  ss = Kyber.Decaps(sk, ct)         │
  │                                    │
  └───────── Same shared secret ss ────┘

✅ Quantum-Safe:
   Based on lattice problems - no efficient quantum attack!
```

### Hybrid Approach (Our Implementation)

```
Alice                                Bob
  │                                    │
  │ (ecdh_pk, ecdh_sk) = ECDH.Gen()    │
  │ (kyber_pk, kyber_sk) = Kyber.Gen() │
  │                                    │
  │──── ecdh_pk ──────────────────────►│
  │──── kyber_pk ─────────────────────►│
  │◄─── bob_ecdh_pk ───────────────────│
  │◄─── bob_kyber_pk ──────────────────│
  │                                    │
  │ ecdh_ss = ECDH(ecdh_sk, bob_ecdh_pk)│
  │ (ct, kyber_ss) = Kyber.Encaps(bob_kyber_pk)
  │                                    │
  │──── ct ───────────────────────────►│
  │                                    │  ecdh_ss = ECDH(...)
  │                                    │  kyber_ss = Kyber.Decaps(ct)
  │                                    │
  │ final_key = SHA384(ecdh_ss || kyber_ss)
  └───────── Same final_key ───────────┘

✅ Secure if EITHER algorithm is secure!
```

---

## Mathematical Foundation Deep Dive

### ECDLP (Classical - Broken)

**Elliptic Curve**: y² = x³ + ax + b (mod p)

```
Discrete Log Problem:
Given: Curve E, Point G, Point P = k·G
Find: k

Best Classical: O(√p) - Baby-step Giant-step
Quantum (Shor): O((log p)³) - POLYNOMIAL TIME!
```

### M-LWE (Post-Quantum - Secure)

**Module LWE over Ring R_q = Z_q[X]/(X^n + 1)**

```
LWE Problem:
Given: Random matrix A ∈ R_q^(k×k)
       Public: b = A·s + e
       Where: s is secret, e is "small" error

Find: s

Why it's hard:
- Adding noise destroys structure
- No known quantum speedup
- Lattice reduction algorithms don't scale

Security reduction:
  Breaking Kyber → Solving hardest lattice problems
```

---

## Real-World Adoption

### Who's Using Post-Quantum Already?

| Organization | Implementation | Status |
|--------------|----------------|--------|
| Google Chrome | TLS with Kyber | Experimental |
| Cloudflare | CIRCL library | Testing |
| Signal | PQXDH protocol | Deployed! |
| AWS | s2n-tls with Kyber | Available |
| Open Quantum Safe | liboqs | Reference impl |

### Timeline to Quantum Threat

```
2024: NIST standardizes ML-KEM (Kyber)
2025: Major products begin integration
2029: Some experts predict cryptographically-relevant QC
2030-2040: Widespread quantum threat likely
2035+: Classical crypto completely obsolete
```

**Key insight**: Migrate NOW because of "Harvest Now, Decrypt Later"

---

## Code Comparison

### Classical ECDH (Python)

```python
from cryptography.hazmat.primitives.asymmetric import ec

# Generate keypair
private_key = ec.generate_private_key(ec.SECP384R1())
public_key = private_key.public_key()

# Derive shared secret
shared_secret = private_key.exchange(ec.ECDH(), peer_public_key)

# ⚠️ Vulnerable to quantum computers!
```

### Post-Quantum Kyber (Python) — This is what Tunnel_VPN uses

```python
# Using kyber-py (real CRYSTALS-Kyber768 / NIST FIPS 203)
from crypto.kyber_kex import KyberKEM

kyber = KyberKEM()

# Generate keypair
public_key, secret_key = kyber.generate_keypair()

# Encapsulate (sender)
ciphertext, shared_secret = kyber.encapsulate(peer_public_key)

# Decapsulate (receiver)
shared_secret = kyber.decapsulate(secret_key, ciphertext)

# ✅ Quantum-safe!
```

---

## Recommendations

### For This Project (All Implemented)
1. ✅ **Kyber-768** — real `kyber-py` library (CRYSTALS-Kyber768 / NIST FIPS 203)
2. ✅ **Hybrid mode** — Kyber-768 + ECDH P-384 (defense in depth)
3. ✅ **AES-256-GCM** — Grover-resistant symmetric encryption
4. ✅ **HTTP/DNS tunneling** — real VPN proxy functionality
5. ✅ **MITM attack demo** — proves replay + tamper protection live
6. ✅ **36 automated tests** — full test suite passing

### For Production Scale
1. Use `liboqs-python` for higher-performance Kyber
2. Add TUN/TAP for transparent system-wide tunneling
3. Add X.509 certificates for server identity verification
4. Follow NIST guidance as standards evolve

---

## Summary Table

```
┌─────────────────────────────────────────────────────────────────┐
│                ALGORITHM COMPARISON SUMMARY                      │
├──────────────────┬──────────────────┬───────────────────────────┤
│     Metric       │   ECDH P-384     │      Kyber-768           │
├──────────────────┼──────────────────┼───────────────────────────┤
│ Quantum Safe     │      ❌ No       │        ✅ Yes            │
│ Public Key Size  │     96 bytes     │      1,184 bytes         │
│ Performance      │     Fast         │       Faster!            │
│ Maturity         │   Decades        │      New (2024)          │
│ Standardization  │   NIST/RFC       │   NIST FIPS 203          │
│ Best For         │ Legacy systems   │   Future-proof systems   │
├──────────────────┴──────────────────┴───────────────────────────┤
│                                                                  │
│  RECOMMENDATION: Use HYBRID (Kyber + ECDH) for transition       │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```
