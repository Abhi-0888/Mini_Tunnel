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

### Client Module (`client/vpn_client.py`)

```python
class VPNClient:
    def __init__(host, port)
    def connect() -> bool             # TCP connect + handshake
    def _handshake() -> bool          # Kyber-768 + ECDH P-384 key exchange
    def send(plaintext: bytes)        # AES-256-GCM encrypt + send
    def recv() -> bytes               # Receive + AES-256-GCM decrypt
    def interactive()                 # VPN> prompt with tunnel commands
    def run_demo()                    # 8-step automated tunnel demo
    def disconnect()
```

**Tunnel commands in interactive mode:**
- `fetch <url>` — HTTP request through VPN tunnel (proves IP masking)
- `resolve <host>` — DNS query through VPN tunnel (proves DNS privacy)
- `verify` — PQC verification (proves Kyber-768 is real)
- `ping` — Encrypted round-trip latency test

### Server Module (`server/vpn_server.py`)

```python
class VPNServer:
    def __init__(host, port, event_callback)
    def start()                       # Bind + accept loop
    def _handle_client(conn, addr)    # Handshake + packet loop per client
    def _handshake(conn, addr) -> cipher  # Kyber+ECDH, returns AES cipher
    def _handle_tunnel(plaintext)     # Process TUNNEL:FETCH/DNS/VERIFY
```

**Server acts as VPN proxy:**
- `TUNNEL:FETCH:<url>` — Server fetches HTTP on behalf of client
- `TUNNEL:DNS:<domain>` — Server resolves DNS on behalf of client
- `TUNNEL:VERIFY` — Server runs independent Kyber-768 encaps/decaps test

### Dashboard Module (`dashboard/`)

```python
# dashboard/app.py — Flask SSE server
@app.route('/events')      # Server-Sent Events stream
@app.route('/')            # Real-time web dashboard

# dashboard/templates/index.html — Tailwind dark UI
# Animated network topology, dual wire/plaintext view
# Live attack visualization, packet counters
```

### Attack Module (`attacks/`)

```python
# attacks/mitm_proxy.py — Transparent MITM proxy
class MITMProxy:
    def start()              # Listen on port 5001, forward to port 5000
    def _relay()             # Forward handshake, then attack
    def _replay_attack()     # Resend captured packet (blocked by counter)
    def _tamper_attack()     # Flip 1 bit (blocked by GCM tag)
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

## Current Capabilities & Future Work

### What Is Implemented
1. **Real Kyber-768** — using `kyber-py` (CRYSTALS-Kyber / NIST FIPS 203), not simplified
2. **Multi-client** — threaded server handles unlimited concurrent clients
3. **HTTP/DNS tunnel proxy** — server fetches URLs and resolves DNS on behalf of clients
4. **Bidirectional tunnel** — server pushes welcome + responses, client sends commands
5. **MITM attack demo** — live replay and tamper attacks, both blocked
6. **Real-time web dashboard** — Flask SSE with animated topology and dual wire/plaintext view
7. **36 automated tests** — Kyber, AES-GCM, integration, benchmarks all passing

### What Would Be Added for Commercial Use
1. **TUN/TAP virtual interface** — route ALL system traffic through VPN automatically
2. **Kill switch** — block internet if VPN drops (`iptables`/`netsh`)
3. **UDP transport** — lower latency (like WireGuard)
4. **X.509 certificate verification** — server identity authentication
5. **Auto-reconnect** — resume tunnel after network interruption
6. **Traffic obfuscation** — make VPN traffic look like HTTPS
