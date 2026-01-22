# 🔬 Post-Quantum Cryptography: Theory and Mathematics

This document provides the theoretical foundation for post-quantum cryptography, specifically the lattice-based cryptography used in Kyber/ML-KEM.

---

## Introduction to Post-Quantum Cryptography

### Why Post-Quantum?

Current public-key cryptography relies on problems that quantum computers can solve efficiently:

| Problem | Classical Hardness | Quantum Hardness |
|---------|-------------------|------------------|
| Integer Factorization | Hard (RSA) | **Easy** (Shor) |
| Discrete Logarithm | Hard (DH, DSA) | **Easy** (Shor) |
| Elliptic Curve DLP | Hard (ECDSA, ECDH) | **Easy** (Shor) |

### PQC Families

| Family | Based On | Examples | Status |
|--------|----------|----------|--------|
| **Lattice** | Short vector problems | Kyber, Dilithium | ✅ NIST Standard |
| Code-based | Error-correcting codes | McEliece, BIKE | Finalist |
| Hash-based | Hash functions | SPHINCS+ | ✅ NIST Standard |
| Isogeny | Elliptic curve isogenies | SIKE | ❌ Broken (2022) |
| Multivariate | Solving polynomial systems | Rainbow | ❌ Broken (2022) |

---

## Lattice Cryptography Fundamentals

### What is a Lattice?

A **lattice** is a discrete set of points in n-dimensional space forming a regular grid.

```
Definition:
Given linearly independent vectors b₁, b₂, ..., bₙ ∈ ℝⁿ
The lattice L is: L = { Σᵢ zᵢ·bᵢ : zᵢ ∈ ℤ }

Example (2D lattice):
    •     •     •     •     •
       •     •     •     •     
    •     •     •     •     •
       •     •     •     •     
    •     •     •     •     •
```

### Hard Lattice Problems

#### 1. Shortest Vector Problem (SVP)

```
Given: Basis B of lattice L
Find: Shortest non-zero vector v ∈ L

||v|| = min{ ||x|| : x ∈ L, x ≠ 0 }

Classical: Exponential time (2^O(n))
Quantum: Exponential time (no speedup!)
```

#### 2. Learning With Errors (LWE)

```
Public:
  A ∈ Zq^(m×n)  (random matrix)
  b = A·s + e   (m samples)

Where:
  s ∈ Zq^n      (secret vector)
  e ∈ Zq^m      (small error vector, |eᵢ| << q)

Problem: Given (A, b), find s

Hardness: At least as hard as worst-case lattice problems!
```

**Why LWE is hard:**
- The error `e` destroys the linear structure
- Without error: Just solve linear equations
- With error: Becomes exponentially hard

---

## Module-LWE (M-LWE)

Kyber uses Module-LWE, a structured variant for efficiency.

### Ring R_q

```
R_q = Zq[X] / (X^n + 1)

Where:
  n = 256 (polynomial degree)
  q = 3329 (modulus)

Elements are polynomials of degree < n with coefficients mod q
```

### Module Structure

```
Module: R_q^k (k vectors of polynomials)

For Kyber-768: k = 3
  s = (s₁(X), s₂(X), s₃(X))
  
Each sᵢ(X) is a polynomial with 256 coefficients
```

### M-LWE Problem

```
Given:
  A ∈ R_q^(k×k)  (random matrix of polynomials)
  t = A·s + e    (public key)

Where:
  s ∈ R_q^k      (secret: k polynomials)
  e ∈ R_q^k      (error: k polynomials with small coefficients)

Find: s

Security: Reduces to hard lattice problems!
```

---

## Kyber Algorithm Details

### Key Generation

```python
def Kyber_KeyGen():
    # 1. Sample random Public Matrix
    A ∈ R_q^(k×k)  # deterministically from seed
    
    # 2. Sample secret and error vectors
    s = CBD_η₁(random)    # Centered Binomial Distribution
    e = CBD_η₁(random)    # Small coefficients
    
    # 3. Compute public key
    t = A·s + e
    
    # Return (public_key, secret_key)
    pk = (A, t)
    sk = s
    
    return (pk, sk)
```

### Centered Binomial Distribution (CBD)

```
CBD_η samples coefficients in range [-η, η]:

For η = 2:
  Sample 4 random bits: b₀, b₁, b₂, b₃
  Return: (b₀ + b₁) - (b₂ + b₃)
  
Result: Small integer in {-2, -1, 0, 1, 2}
```

This ensures error polynomials have small coefficients.

### Encapsulation

```python
def Kyber_Encaps(pk):
    (A, t) = pk
    
    # 1. Sample random message
    m ← {0,1}^256
    
    # 2. Sample ephemeral vectors
    r = CBD_η₁(random)
    e₁ = CBD_η₂(random)
    e₂ = CBD_η₂(random)
    
    # 3. Compute ciphertext components
    u = Aᵀ·r + e₁           # k polynomials
    v = tᵀ·r + e₂ + ⌈q/2⌋·m  # 1 polynomial
    
    # 4. Derive shared secret
    K = H(m)  # Hash of message
    
    ciphertext = (u, v)
    shared_secret = K
    
    return (ciphertext, shared_secret)
```

### Decapsulation

```python
def Kyber_Decaps(sk, ciphertext):
    s = sk
    (u, v) = ciphertext
    
    # 1. Decrypt
    m' = v - sᵀ·u
    
    # Why this works:
    # v - sᵀ·u = tᵀ·r + e₂ + ⌈q/2⌋·m - sᵀ·(Aᵀ·r + e₁)
    #          = (A·s + e)ᵀ·r + e₂ + ⌈q/2⌋·m - sᵀ·Aᵀ·r - sᵀ·e₁
    #          = sᵀ·Aᵀ·r + eᵀ·r + e₂ + ⌈q/2⌋·m - sᵀ·Aᵀ·r - sᵀ·e₁
    #          = ⌈q/2⌋·m + (eᵀ·r + e₂ - sᵀ·e₁)
    #                      ↑ small error (decoding error)
    
    # 2. Decode message (round coefficients)
    #    If coeff ≈ ⌈q/2⌋ → bit = 1
    #    If coeff ≈ 0 → bit = 0
    m = Decode(m')
    
    # 3. Derive shared secret
    K = H(m)
    
    return K
```

---

## Security Analysis

### Reduction to Lattice Problems

```
Security Proof (informal):

If an attacker can break Kyber:
  → They can solve M-LWE
  → They can solve worst-case lattice problems
  → But these are believed hard even for quantum computers!
```

### Concrete Security

| Variant | Classical | Quantum (Core-SVP) |
|---------|-----------|-------------------|
| Kyber-512 | 2^118 | 2^107 |
| **Kyber-768** | **2^182** | **2^161** |
| Kyber-1024 | 2^256 | 2^218 |

**NIST Security Level:**
- Kyber-768 matches AES-192 security

### Known Attacks

| Attack | Complexity | Quantum Speedup? |
|--------|------------|------------------|
| Lattice reduction (BKZ) | 2^O(n) | Marginal |
| Combinatorial attacks | 2^O(n) | No |
| Algebraic attacks | Not applicable | N/A |

**Key insight**: No known quantum algorithm provides significant advantage!

---

## Comparison with Classical Crypto Math

### RSA Problem

```
Public: N = p·q, e
Private: p, q, d

Math: Factoring N to find p, q
Classical: ~2^(n^(1/3)) (Number Field Sieve)
Quantum: O(n³) (Shor) ← BROKEN!
```

### ECDLP Problem

```
Public: Curve E, Point G, Point P = k·G
Private: k

Math: Find k given G and P
Classical: ~2^(n/2) (Pollard rho)
Quantum: O(n³) (Shor) ← BROKEN!
```

### M-LWE Problem

```
Public: Matrix A, Vector t = A·s + e
Private: s

Math: Find s given noisy linear equations
Classical: ~2^O(n) (Lattice reduction)
Quantum: ~2^O(n) (No significant speedup) ← SECURE!
```

---

## Number Theoretic Transform (NTT)

Kyber uses NTT for efficient polynomial multiplication.

### Basic Idea

```
Standard polynomial multiplication: O(n²)
NTT-based multiplication: O(n log n)

Method:
1. Transform polynomials to NTT domain
2. Point-wise multiply in NTT domain
3. Transform back

Similar to FFT but over finite field Z_q
```

### Why q = 3329?

```
Requirements for NTT:
1. q is prime (for field properties)
2. q ≡ 1 (mod 2n) for NTT to work
3. q has small coefficients (efficiency)

3329 = 13 × 256 + 1 = 13 × 2⁸ + 1

This enables efficient 256-point NTT!
```

---

## Security Assumptions Summary

### Hardness Assumptions

1. **M-LWE Assumption**: 
   - Given (A, A·s+e), cannot distinguish from random
   - Hardness parameter: dimension n, modulus q, error distribution

2. **M-SIS Assumption** (for signatures):
   - Given A, hard to find short vector m where A·m = 0

3. **Worst-case to Average-case Reduction**:
   - Average M-LWE is as hard as worst-case lattice problems

### Why We Trust This

```
Historical analysis:
- Lattice problems studied since 1980s
- LWE introduced 2005 (Oded Regev)
- Kyber analyzed 2017-2024
- Survived 8 years of NIST competition
- No significant attacks found!
```

---

## Practical Considerations

### Key Sizes vs Security

| Algorithm | Public Key | Security Claim |
|-----------|------------|----------------|
| RSA-2048 | 256 bytes | 112-bit (broken by quantum) |
| ECDH P-256 | 64 bytes | 128-bit (broken by quantum) |
| Kyber-768 | 1,184 bytes | 128-bit quantum |

**Trade-off**: Larger keys for quantum security

### Performance on Hardware

```
Kyber operations per second (modern CPU):
- Key generation: ~50,000
- Encapsulation: ~55,000  
- Decapsulation: ~45,000

Faster than ECDH despite larger keys!
(NTT is very efficient on modern CPUs)
```

---

## Further Reading

### Original Papers

1. **LWE**: Regev, "On Lattices, Learning with Errors, Random Linear Codes" (2005)
2. **Ring-LWE**: Lyubashevsky et al. (2010)
3. **Kyber**: Schwabe et al. "CRYSTALS-Kyber" (2017)

### NIST Standards

1. **FIPS 203**: ML-KEM (Kyber) Specification (2024)
2. **SP 800-208**: PQC Migration Guidelines

### Textbooks

1. Peikert, "A Decade of Lattice Cryptography" (2016)
2. Micciancio & Goldwasser, "Complexity of Lattice Problems"

---

## Summary

```
┌──────────────────────────────────────────────────────────────────┐
│           POST-QUANTUM CRYPTOGRAPHY FOUNDATIONS                   │
├──────────────────────────────────────────────────────────────────┤
│                                                                   │
│  Core Idea:                                                       │
│  Replace number-theoretic problems (factoring, DLP)              │
│  with geometric problems (lattices) that resist quantum attacks  │
│                                                                   │
│  Key Concepts:                                                    │
│  • Lattices: Regular grid of points in n-dimensions              │
│  • LWE: Noisy linear equations - destroying structure            │
│  • M-LWE: Efficient structured variant using polynomial rings    │
│  • NTT: Fast polynomial multiplication                           │
│                                                                   │
│  Security:                                                        │
│  • Based on worst-case lattice hardness                          │
│  • No known quantum speedup                                       │
│  • Extensively analyzed during NIST competition                  │
│                                                                   │
│  Result: Cryptography that survives the quantum era!             │
│                                                                   │
└──────────────────────────────────────────────────────────────────┘
```
