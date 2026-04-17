# 🛡️ Threat Model

This document analyzes the security threats to the Quantum-Safe Mini-VPN system and documents the mitigations implemented.

---

## System Overview

### Assets to Protect
| Asset | Confidentiality | Integrity | Availability |
|-------|-----------------|-----------|--------------|
| VPN Payloads | Critical | Critical | High |
| Encryption Keys | Critical | Critical | High |
| Session State | Medium | High | Medium |
| Metadata | Low | Low | Low |

### Trust Boundaries

```
┌────────────────────────────────────────────────────────────────┐
│                    UNTRUSTED NETWORK                            │
│                                                                 │
│  ┌──────────────────┐                ┌──────────────────┐      │
│  │ TRUSTED:         │    Tunnel      │ TRUSTED:         │      │
│  │ Client Host      │◄══════════════►│ Server Host      │      │
│  │                  │   (Encrypted)  │                  │      │
│  └──────────────────┘                └──────────────────┘      │
│                                                                 │
│           ▲                                    ▲                │
│           │                                    │                │
│      ┌────┴────┐                          ┌────┴────┐          │
│      │ Attacker│                          │ Attacker│          │
│      └─────────┘                          └─────────┘          │
│                                                                 │
└────────────────────────────────────────────────────────────────┘
```

---

## Threat Actors

### 1. Passive Network Attacker (Eve)
- **Capabilities**: Monitor all network traffic
- **Goals**: Read sensitive data
- **Resources**: Moderate (traffic capture tools)

### 2. Active Network Attacker (Mallory)
- **Capabilities**: Intercept, modify, inject packets
- **Goals**: Tamper with data, inject commands
- **Resources**: Moderate to High

### 3. Quantum-Capable Attacker (Future)
- **Capabilities**: Quantum computer with Shor's algorithm
- **Goals**: Break key exchange, decrypt traffic
- **Resources**: Very High (nation-state)

### 4. Replay Attacker
- **Capabilities**: Capture and resend valid packets
- **Goals**: Duplicate transactions, re-authenticate
- **Resources**: Low

---

## Threat Analysis (STRIDE)

### Spoofing

| Threat | Target | Mitigation | Status |
|--------|--------|------------|--------|
| Client impersonation | Server | No mitigation | ⚠️ (Future: Certificates) |
| Server impersonation | Client | No mitigation | ⚠️ (Future: Certificates) |

**Note**: This implementation focuses on channel security, not endpoint authentication.

### Tampering

| Threat | Target | Mitigation | Status |
|--------|--------|------------|--------|
| Modify ciphertext | Packets | AES-GCM auth tag | ✅ Protected |
| Modify nonce | Packets | Included in tag computation | ✅ Protected |
| Modify counter | Packets | Included in AAD | ✅ Protected |
| Bit-flip attacks | Packets | GCM detects any modification | ✅ Protected |

### Repudiation

| Threat | Target | Mitigation | Status |
|--------|--------|------------|--------|
| Deny sending message | Logs | Not in scope | ℹ️ N/A |

### Information Disclosure

| Threat | Target | Mitigation | Status |
|--------|--------|------------|--------|
| Read payload | Packets | AES-256-GCM encryption | ✅ Protected |
| Read encryption key | Key exchange | Kyber (quantum-safe) | ✅ Protected |
| Traffic analysis | Metadata | Not mitigated | ⚠️ Inherent |
| Timing analysis | Metadata | Not mitigated | ⚠️ Inherent |

### Denial of Service

| Threat | Target | Mitigation | Status |
|--------|--------|------------|--------|
| Connection flooding | Server | Not mitigated | ⚠️ (Future: Rate limiting) |
| Resource exhaustion | Server | Not mitigated | ⚠️ |
| Network disruption | Tunnel | TCP retry | Partial |

### Elevation of Privilege

| Threat | Target | Mitigation | Status |
|--------|--------|------------|--------|
| Key compromise | Session | Ephemeral keys | ✅ Protected |
| Code injection | System | Input validation | ✅ Protected |

---

## Attack Scenarios

### Scenario 1: Eavesdropping Attack

```
Attacker Goal: Read VPN traffic content

Attack Flow:
1. Attacker captures packets with Wireshark
2. Attacker sees encrypted bytes
3. Attacker cannot decrypt (no key)

Defense:
- AES-256-GCM provides confidentiality
- Key derived from Kyber (quantum-safe)

Result: ATTACK FAILS ✅
```

### Scenario 2: Man-in-the-Middle (Active)

```
Attacker Goal: Modify transaction amount

Attack Flow:
1. Attacker intercepts encrypted packet
2. Attacker modifies ciphertext bytes
3. Attacker forwards modified packet
4. Server receives and attempts decryption

Defense:
- GCM authentication tag verification fails
- Modified packet is REJECTED

Result: ATTACK FAILS ✅
```

### Scenario 3: Replay Attack

```
Attacker Goal: Duplicate a payment transaction

Attack Flow:
1. Attacker captures valid encrypted packet
2. Attacker re-sends same packet later
3. Server receives replayed packet

Defense:
- Packet contains monotonic counter
- Server tracks seen counters (sliding window)
- Duplicate counter REJECTED

Result: ATTACK FAILS ✅
```

### Scenario 4: Harvest Now, Decrypt Later

```
Attacker Goal: Decrypt traffic with future quantum computer

Attack Flow (Classical VPN):
1. Attacker records ECDH key exchange
2. Attacker stores encrypted traffic
3. Years later: Run Shor's algorithm
4. Recover ECDH private key
5. Derive encryption key
6. Decrypt all stored traffic!

Defense (Our VPN):
- Uses Kyber for key exchange
- Kyber based on lattice problems
- No known quantum algorithm breaks lattice

Result: ATTACK FAILS ✅
```

---

## Security Controls

### Cryptographic Controls

| Control | Implementation | Purpose |
|---------|----------------|---------|
| Key Exchange | Kyber-768 + ECDH | Quantum-safe key agreement |
| Encryption | AES-256-GCM | Confidentiality + Integrity |
| Key Derivation | SHA-384 HKDF | Uniform key from secrets |
| Nonce Generation | `os.urandom(12)` | Unique per-packet IV |

### Protocol Controls

| Control | Implementation | Purpose |
|---------|----------------|---------|
| Replay Protection | Packet counter + sliding window | Prevent duplicate processing |
| Length Prefix | 4-byte big-endian | Message framing |
| Counter in AAD | Included in authentication | Binds counter to ciphertext |

### Security Configuration

```python
# Cryptographic Parameters
AES_KEY_SIZE = 32      # 256 bits (Grover-resistant)
GCM_NONCE_SIZE = 12    # 96 bits (recommended)
GCM_TAG_SIZE = 16      # 128 bits (strong auth)

# Replay Protection
REPLAY_WINDOW = 64     # Handle reordering up to 64 packets

# Key Exchange
KYBER_VARIANT = 768    # ~192-bit classical, ~128-bit quantum
ECDH_CURVE = SECP384R1 # 192-bit classical
```

---

## Risk Assessment

### Risk Matrix

| Threat | Likelihood | Impact | Risk Level | Mitigated? |
|--------|------------|--------|------------|------------|
| Eavesdropping | High | High | Critical | ✅ Yes |
| Tampering | Medium | High | High | ✅ Yes |
| Replay | Medium | High | High | ✅ Yes |
| Quantum Attack | Low (now) | Critical | High | ✅ Yes |
| MitM (no auth) | Medium | Critical | Critical | ⚠️ Partial |
| DoS | Medium | Medium | Medium | ❌ No |

### Residual Risks

1. **No Server Authentication**
   - Risk: Client could connect to malicious server
   - Mitigation: Use known server address, future PKI

2. **Traffic Analysis**
   - Risk: Attacker can see packet timing/sizes
   - Mitigation: Not in scope (would need padding/timing obfuscation)

3. **Endpoint Security**
   - Risk: Compromised client/server
   - Mitigation: Outside VPN scope (OS security)

---

## Security Recommendations

### For Production Use

1. **Add Certificate-Based Authentication**
   ```python
   # Verify server certificate before key exchange
   cert = receive_certificate()
   verify_certificate(cert, trusted_ca)
   ```

2. **Implement Rate Limiting**
   ```python
   if connection_count > MAX_CONNECTIONS:
       reject_connection()
   ```

3. **Kyber Backend Already Real**
   ```python
   # We use kyber-py (CRYSTALS-Kyber768 / NIST FIPS 203)
   # For higher performance: switch to liboqs
   from oqs import KeyEncapsulation
   kem = KeyEncapsulation("Kyber768")
   ```

4. **Perfect Forward Secrecy Already Implemented**
   - Fresh Kyber + ECDH keypairs generated for every session
   - Key compromise of one session does not affect others

---

## Compliance Considerations

| Standard | Requirement | Status |
|----------|-------------|--------|
| NIST SP 800-57 | AES-256 for sensitive data | ✅ Compliant |
| NIST SP 800-56A | Key establishment | ✅ Compliant |
| NIST FIPS 203 | Post-quantum KEX | ✅ Kyber (ML-KEM) |
| GDPR Art. 32 | Encryption in transit | ✅ Compliant |

---

## Summary

```
┌──────────────────────────────────────────────────────────────┐
│                    SECURITY SUMMARY                           │
├──────────────────────────────────────────────────────────────┤
│                                                               │
│  Protected Against:                                          │
│  ✅ Eavesdropping (AES-256-GCM encryption)                   │
│  ✅ Packet tampering (GCM authentication)                    │
│  ✅ Replay attacks (Counter + sliding window)                │
│  ✅ Quantum key recovery (Kyber lattice-based KEX)           │
│                                                               │
│  Not Protected Against:                                       │
│  ⚠️ Man-in-the-middle (no endpoint authentication)          │
│  ⚠️ Traffic analysis (timing/size patterns)                  │
│  ⚠️ Denial of service (no rate limiting)                    │
│  ⚠️ Endpoint compromise (out of scope)                      │
│                                                               │
│  Overall: Real working VPN with PQC, HTTP/DNS tunneling,     │
│  MITM attack demo, and live monitoring dashboard.             │
│  Production use would add TUN/TAP, kill switch, UDP.         │
│                                                               │
└──────────────────────────────────────────────────────────────┘
```
