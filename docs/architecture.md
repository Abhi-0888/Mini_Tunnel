# 🏗️ Quantum-Safe Mini-VPN Architecture

## System Overview

This document describes the architecture of the Quantum-Safe Mini-VPN system, including component design, data flows, and security mechanisms.

---

## Component Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                         MINI-VPN SYSTEM                              │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌─────────────────────┐              ┌─────────────────────┐       │
│  │     VPN CLIENT      │              │     VPN SERVER      │       │
│  │                     │              │                     │       │
│  │  ┌───────────────┐  │              │  ┌───────────────┐  │       │
│  │  │ Packet Capture│  │              │  │ Packet Forward│  │       │
│  │  │   (Scapy)     │  │              │  │               │  │       │
│  │  └───────┬───────┘  │              │  └───────▲───────┘  │       │
│  │          │          │              │          │          │       │
│  │  ┌───────▼───────┐  │              │  ┌───────┴───────┐  │       │
│  │  │  Encryption   │  │    Tunnel    │  │  Decryption   │  │       │
│  │  │  AES-256-GCM  │◄─┼──────────────┼─►│  AES-256-GCM  │  │       │
│  │  └───────┬───────┘  │  (Encrypted) │  └───────┬───────┘  │       │
│  │          │          │              │          │          │       │
│  │  ┌───────▼───────┐  │              │  ┌───────▼───────┐  │       │
│  │  │  Key Exchange │  │              │  │  Key Exchange │  │       │
│  │  │ Kyber + ECDH  │◄─┼──────────────┼─►│ Kyber + ECDH  │  │       │
│  │  └───────────────┘  │              │  └───────────────┘  │       │
│  │                     │              │                     │       │
│  └─────────────────────┘              └─────────────────────┘       │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Protocol Sequence

### Connection Establishment

```
Client                                              Server
   │                                                   │
   │─────────────── TCP Connect ──────────────────────►│
   │                                                   │
   │══════════════ KEY EXCHANGE (Phase 1) ════════════│
   │                                                   │
   │  Generate ECDH keypair                            │
   │  Generate Kyber keypair                           │
   │                                                   │
   │──── Client ECDH Public Key ──────────────────────►│
   │──── Client Kyber Public Key ─────────────────────►│
   │                                                   │
   │                          Generate ECDH keypair    │
   │                          Generate Kyber keypair   │
   │                                                   │
   │◄──── Server ECDH Public Key ──────────────────────│
   │◄──── Server Kyber Public Key ─────────────────────│
   │                                                   │
   │  Kyber.Encapsulate(Server_PK)                     │
   │  → ciphertext, shared_secret                      │
   │                                                   │
   │──── Kyber Ciphertext ────────────────────────────►│
   │                                                   │
   │                     Kyber.Decapsulate(SK, CT)     │
   │                     → shared_secret               │
   │                                                   │
   │  Derive: ECDH_secret                              │  Derive: ECDH_secret
   │  Combine: Hash(ECDH || Kyber)                     │  Combine: Hash(ECDH || Kyber)
   │  → AES_Key                                        │  → AES_Key
   │                                                   │
   │═══════════════ TUNNEL ACTIVE ════════════════════│
   │                                                   │
   │──── AES-GCM(payload, counter=1) ─────────────────►│
   │◄──── AES-GCM(response, counter=1) ────────────────│
   │──── AES-GCM(payload, counter=2) ─────────────────►│
   │                  ...                              │
```

---

## Packet Structure

### Encrypted Packet Format

```
┌────────────────────────────────────────────────────────────────┐
│                    ENCRYPTED VPN PACKET                         │
├────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────┬──────────┬─────────────────────┬──────────────┐  │
│  │ Counter  │  Nonce   │     Ciphertext      │   Auth Tag   │  │
│  │ 8 bytes  │ 12 bytes │    Variable len     │   16 bytes   │  │
│  └──────────┴──────────┴─────────────────────┴──────────────┘  │
│                                                                 │
│  Counter:    Monotonically increasing (replay protection)      │
│  Nonce:      Random per-packet (IV for AES-GCM)                │
│  Ciphertext: Encrypted payload                                  │
│  Auth Tag:   GMAC authentication (integrity)                   │
│                                                                 │
├────────────────────────────────────────────────────────────────┤
│  Overhead: 36 bytes per packet                                  │
└────────────────────────────────────────────────────────────────┘
```

### Wire Format

```
┌─────────────────────────────────────────────────────────────┐
│                    TCP FRAMING                               │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌────────────────┬────────────────────────────────────┐    │
│  │  Length (4B)   │           Payload (N bytes)        │    │
│  └────────────────┴────────────────────────────────────┘    │
│                                                              │
│  Length: Big-endian 32-bit integer                          │
│  Payload: Either encrypted packet or key exchange data      │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## Module Structure

### Crypto Module (`crypto/`)

```
crypto/
├── __init__.py
├── classical_kex.py    # ECDH implementation (quantum-vulnerable)
├── kyber_kex.py        # Kyber KEM (quantum-safe)
├── hybrid_kex.py       # Combined Kyber + ECDH
└── aes_gcm.py          # AES-256-GCM encryption
```

#### Class Hierarchy

```
                    ┌─────────────────┐
                    │  KeyExchange    │
                    │   (Abstract)    │
                    └────────┬────────┘
                             │
            ┌────────────────┼────────────────┐
            │                │                │
    ┌───────▼───────┐ ┌──────▼──────┐ ┌──────▼───────┐
    │ ClassicalECDH │ │  KyberKEM   │ │ HybridKEX    │
    │               │ │             │ │              │
    │ generate()    │ │ generate()  │ │ generate()   │
    │ derive()      │ │ encaps()    │ │ initiate()   │
    │               │ │ decaps()    │ │ complete()   │
    └───────────────┘ └─────────────┘ └──────────────┘
          ⚠️                ✅              ✅
      Q-Vulnerable      Q-Safe          Q-Safe
```

### Client Module (`client/`)

```python
class VPNClient:
    def __init__(server_host, server_port)
    def connect() -> bool
    def _perform_key_exchange() -> bool
    def send_encrypted(data: bytes) -> bool
    def receive_encrypted() -> bytes
    def start_interactive()
    def disconnect()
```

### Server Module (`server/`)

```python
class VPNServer:
    def __init__(host, port)
    def start()
    def _accept_clients()
    def _handle_client(socket, addr)
    def _perform_key_exchange(socket, addr) -> cipher
    def _client_communication_loop(socket, cipher, addr)
    def stop()
```

---

## Security Mechanisms

### 1. Key Exchange Security

| Mechanism | Purpose | Implementation |
|-----------|---------|----------------|
| Kyber KEM | Quantum-safe key agreement | `kyber_kex.py` |
| ECDH | Classical security (backup) | `classical_kex.py` |
| Hybrid | Defense-in-depth | `hybrid_kex.py` |
| Key Derivation | Uniform key from secrets | SHA-384 HKDF |

### 2. Encryption Security

| Mechanism | Purpose | Implementation |
|-----------|---------|----------------|
| AES-256 | Confidentiality | `AESGCM256` class |
| GCM Mode | Integrity + Auth | Built-in to AES-GCM |
| Random Nonce | Unique ciphertext | `os.urandom(12)` |
| Counter | Replay protection | Included in AAD |

### 3. Attack Mitigations

| Attack | Mitigation | How it Works |
|--------|------------|--------------|
| Eavesdropping | AES-256-GCM | Encrypted payload |
| Tampering | GMAC tag | Any change detected |
| Replay | Packet counter | Duplicates rejected |
| Quantum | Kyber KEM | Lattice-based KEX |

---

## Data Flow

### Sending Data (Client → Server)

```
Plaintext
    │
    ▼
┌───────────────┐
│ Get Counter   │
│ counter++     │
└───────┬───────┘
        │
        ▼
┌───────────────┐
│ Generate      │
│ Random Nonce  │
└───────┬───────┘
        │
        ▼
┌───────────────┐
│ AES-256-GCM   │
│ Encrypt       │
│ (key, nonce,  │
│  plaintext,   │
│  counter)     │
└───────┬───────┘
        │
        ▼
┌───────────────┐
│ Build Packet  │
│ [cnt|nonce|   │
│  ciphertext|  │
│  tag]         │
└───────┬───────┘
        │
        ▼
┌───────────────┐
│ Send over     │
│ TCP Socket    │
└───────────────┘
```

### Receiving Data (Server ← Client)

```
TCP Data
    │
    ▼
┌───────────────┐
│ Parse Packet  │
│ Extract:      │
│ counter, nonce│
│ ciphertext,tag│
└───────┬───────┘
        │
        ▼
┌───────────────┐
│ Check Replay  │
│ counter >     │
│ last_seen?    │
└───────┬───────┘
        │
   ┌────┴────┐
   │         │
   ▼         ▼
 Valid    Replay!
   │      (REJECT)
   │
   ▼
┌───────────────┐
│ AES-256-GCM   │
│ Decrypt       │
│ (verify tag)  │
└───────┬───────┘
        │
   ┌────┴────┐
   │         │
   ▼         ▼
 Valid   Tampered!
   │     (REJECT)
   │
   ▼
┌───────────────┐
│ Update Replay │
│ Window        │
└───────┬───────┘
        │
        ▼
Plaintext
```

---

## Configuration Options

### Server Configuration
```python
VPNServer(
    host='0.0.0.0',     # Bind address
    port=5000           # Listen port
)
```

### Client Configuration
```python
VPNClient(
    server_host='localhost',  # Server address
    server_port=5000          # Server port
)
```

### Security Parameters
```python
# AES-GCM
NONCE_SIZE = 12     # 96-bit nonce (GCM standard)
TAG_SIZE = 16       # 128-bit auth tag
KEY_SIZE = 32       # 256-bit key

# Replay Protection
WINDOW_SIZE = 64    # Sliding window size

# Kyber
KYBER_VARIANT = 768  # Kyber-768 (192-bit security)
```

---

## Limitations & Future Work

### Current Limitations
1. **Simplified Kyber** - Educational implementation, not production-ready
2. **No certificate verification** - No PKI for server authentication
3. **Single connection** - Server handles clients sequentially
4. **No IP tunneling** - Only encrypts application payloads

### Future Enhancements
1. Use `liboqs-python` for production Kyber
2. Add X.509 certificate verification
3. Implement IP-level packet encryption
4. Add connection multiplexing
5. Implement perfect forward secrecy with session keys
