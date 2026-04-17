# Quantum-Safe VPN — Complete Step-by-Step Instructions

> **What this demo shows:**  
> A real, working VPN tunnel protected by **CRYSTALS-Kyber-768** (NIST FIPS 203, 2024) + **ECDH P-384** key exchange and **AES-256-GCM** encryption — with live attack demonstrations that a third party can witness in real time.

---

## Prerequisites

### 1. Install Python 3.10 or newer
- Download from https://python.org  
- During install: ✅ check **"Add Python to PATH"**
- Verify:
  ```
  py -3 --version
  ```

### 2. Install required packages (one time only)
Open a terminal in the project folder and run:
```
py -3 -m pip install kyber-py cryptography flask scapy pytest
```

### 3. Confirm everything works
```
py -3 -m pytest tests/test_crypto.py -v
```
You should see **36 passed** printed at the end.

---

## Finding your LAN IP address

You need this so other devices can connect to your machine.

**Windows:**
```
ipconfig
```
Look for **IPv4 Address** under your Wi-Fi or Ethernet adapter.  
Example: `10.1.160.121`

> **Important:** Both your machine and any connecting device must be on the **same Wi-Fi/network**.

---

## PART 1 — Direct VPN Demo (2 terminals, same machine or LAN)

---

### STEP 1 — Start the VPN Server + Live Dashboard

Open **Terminal 1** in the project folder and run:

```
py -3 launch_demo.py
```

**What you will see:**
```
======================================================================
  QUANTUM-SAFE VPN — LIVE DEMO LAUNCHER
  Kyber-768 (NIST FIPS 203) + ECDH P-384 + AES-256-GCM
======================================================================

  1. Open dashboard in any browser:
       http://10.1.160.121:8080

  2. Connect the VPN client:
       py -3 client/vpn_client.py --host 10.1.160.121
  ...

  Dashboard starting: http://10.1.160.121:8080
  * Serving Flask app 'dashboard.app'
```

✅ The VPN server is now listening on **port 5000** and the web dashboard is on **port 8080**.

---

### STEP 2 — Open the Live Dashboard in a Browser

On **any device on the same network**, open a browser and go to:

```
http://10.1.160.121:8080
```

Example: `http://10.1.160.121:8080`

**What you will see on the dashboard:**
- A dark-themed real-time monitor
- Network topology diagram: `[CLIENT] ─────► [SERVER]`
- Stats: Packets Decrypted, Attacks Blocked, Clients, Key Exchanges
- Dual pane: **Wire (encrypted hex)** vs **Decrypted plaintext** — side by side
- Live Event Log

> Share this URL with your teacher/audience so they can watch live on their phone or laptop.

---

### STEP 3 — Connect a VPN Client

Open **Terminal 2** in the project folder.

**Option A — Automated VPN tunnel demo (8 steps: PQC verify + DNS tunnel + HTTP tunnel + echo tests + latency):**
```
py -3 client/vpn_client.py --host 10.1.160.121 --demo
```

**Option B — Interactive VPN tunnel mode (run your own tunnel commands):**
```
py -3 client/vpn_client.py --host 10.1.160.121
```

**From another device on the same network:**
```
py -3 client/vpn_client.py --host 10.1.160.121 --demo
```

**What you will see in the client terminal (Terminal 2):**
```
============================
  QUANTUM-SAFE VPN CLIENT
============================
  [01:04:32] TCP connected to 10.1.160.121:5000
  [01:04:32] Starting Kyber-768 + ECDH P-384 handshake...
  [01:04:32]   Client ECDH pub: 97 B | Client Kyber pub: 1184 B
  [01:04:32]   Server ECDH pub: 97 B | Server Kyber pub: 1184 B
  [01:04:32] Key exchange done in 15.4 ms  key=3f7a2b...

  ┌─ SEND ────────────────────────────────────────────────────┐
  │ Plain  [  42 B]: Hello Server! Quantum-safe tunnel is live.
  │ Wire   [  78 B]: 0000000000000001ec654b5ddfeab75c...
  │ Nonce  [  12 B]  Counter [  8 B]  GCM-Tag [ 16 B]
  └──────────────────────────────────────────────────────────┘
  ┌─ RECV ────────────────────────────────────────────────────┐
  │ Wire   [ 111 B]: 0000000000000001dfe8db9fd2173129...
  │ Plain  [  75 B]: [SERVER] ACK #1 — decrypted: 'Hello Server!...'
  └──────────────────────────────────────────────────────────┘
```

**What you will see in the server terminal (Terminal 1):**
```
  ┌──────────────────────────────────────────────────────────┐
  │  TUNNEL ACTIVE  10.1.160.121:54321                      │
  └──────────────────────────────────────────────────────────┘

  ┌─ PKT #001 ── from 10.1.160.121:54321 ──────────────┐
  │ Wire  [  78 B]: 0000000000000001ec654b5ddfeab75c...
  │ Plain [  42 B]: Hello Server! Quantum-safe tunnel is live.
  └──────────────────────────────────────────────────────────┘
```

**What updates on the dashboard:**
- Topology line animates a green dot flying from CLIENT → SERVER
- Kyber handshake row appears in the dual pane (key preview, latency, bytes)
- Every message shows as a card: left = encrypted hex, right = plaintext
- Packet count, byte count, and client counter all increment

---

## PART 2 — Man-in-the-Middle Attack Demo (3 terminals)

This shows a **real third-party attacker** positioned between the client and server.

---

### STEP 1 — Start the VPN Server + Dashboard (same as before)

In **Terminal 1:**
```
py -3 launch_demo.py
```

---

### STEP 2 — Start the MITM Attacker Proxy

Open **Terminal 2** in the project folder and run:

```
py -3 attacks/mitm_proxy.py --target 10.1.160.121
```

Example:
```
py -3 attacks/mitm_proxy.py --target 10.1.160.121
```

**What you will see in Terminal 2 (attacker's view):**
```
  ══════════════════════════════════════════════════
  QUANTUM-SAFE VPN — MAN-IN-THE-MIDDLE PROXY
  ══════════════════════════════════════════════════

  Listening on 0.0.0.0:5001
  Forwarding to 10.1.160.121:5000

  Waiting for a victim to connect...
```

> The attacker is now sitting between the client (port 5001) and the real server (port 5000).  
> Anyone connecting to **port 5001** is unknowingly going through the attacker.

---

### STEP 3 — Connect the Client THROUGH the Attacker

Open **Terminal 3** in the project folder and run:

```
py -3 client/vpn_client.py --host 10.1.160.121 --port 5001 --demo
```

Example:
```
py -3 client/vpn_client.py --host 10.1.160.121 --port 5001 --demo
```

> The client thinks it's connecting directly to the VPN server. In reality, all traffic passes through the MITM proxy first.

---

### STEP 4 — Watch the Attacks in Real Time

**In Terminal 2 (attacker's terminal), you will see:**

#### Phase 1 — Handshake Interception
```
  [MITM] C→S  Client ECDH public key  :    97 B
         Hex: 04a1b2c3d4e5f6...
  [MITM] C→S  Client Kyber public key :  1184 B
         Hex: 3186171f8a19...
  [MITM] S→C  Server ECDH public key  :    97 B
  [MITM] S→C  Server Kyber public key :  1184 B
  [MITM] C→S  Kyber ciphertext        :  1088 B

  KEY INSIGHT:
  Attacker has ALL handshake bytes but CANNOT compute shared secret!
    Kyber-768 KEM: shared secret derived inside each party separately.
    Module-LWE: no known polynomial-time solution.
```

#### Phase 2 — Attack 1: Replay Attack
```
  ATTACK 1: REPLAY ATTACK
  Resending the EXACT same packet (counter=1) to server...

  REPLAY BLOCKED!
    counter=1 is already in recv_window → rejected immediately.
```

**In Terminal 1 (server), you will see:**
```
  ┌─ 🔁 REPLAY ATTACK BLOCKED ────────────────────────────┐
  │ Duplicate counter — packet from 10.1.160.121:61234
  │ Wire  [  78 B]: 0000000000000001ec654b5d...
  │ Result: DROPPED — counter already in recv_window
  └──────────────────────────────────────────────────────────┘
```

#### Phase 2 — Attack 2: Tampering Attack
```
  ATTACK 2: TAMPERING ATTACK (single bit-flip)
  Byte at position 20: 0xCD → 0x32

  TAMPERING BLOCKED!
    AES-256-GCM authentication tag mismatch.
    1 flipped bit invalidates the 128-bit GHASH auth tag.
```

**In Terminal 1 (server), you will see:**
```
  ┌─ ⚡ TAMPERING ATTACK BLOCKED ─────────────────────────┐
  │ GCM auth tag mismatch — packet from 10.1.160.121:61234
  │ Wire  [  85 B]: 00000000000000022a8446f4...
  │ Result: DROPPED — attacker cannot forge a valid GCM tag
  └──────────────────────────────────────────────────────────┘
```

#### On the Dashboard (browser):
- Topology changes to `[CLIENT] →[👁️ MITM]→ [SERVER]`
- Attack cards appear in the dual pane with red border and flash effect
- Server icon flashes **red** on each blocked attack
- Attacks Blocked counter increments

#### Attack Summary (Terminal 2):
```
  ============================================================
  ATTACK SUMMARY — Attacker had FULL packet access:
  ============================================================
  ✓ Encryption  : AES-256-GCM — attacker sees only ciphertext
  ✓ Key exchange: Kyber-768 KEM — shared secret never on wire
  ✓ Replay      : Duplicate counter rejected by sliding window
  ✓ Tampering   : GCM auth tag — any modification detected
  ============================================================
```

---

## PART 3 — Interactive VPN Tunnel Mode

Instead of `--demo`, run the client without any extra flag:

```
py -3 client/vpn_client.py --host 10.1.160.121
```

### Available Tunnel Commands

| Command | What It Does | VPN Proof |
|---|---|---|
| `fetch <any-url>like <http://httpbin.org/ip>` | **HTTP tunnel** — server fetches **any** URL for you through VPN | Proves IP masking (websites see server's IP) |
| `resolve <any-domain> like <google.com>` | **DNS tunnel** — server resolves **any** domain through VPN | Proves DNS privacy (ISP sees nothing) |
| `verify` | **PQC proof** — server runs Kyber-768 encaps/decaps test | Proves post-quantum crypto is real |
| `ping` | **Latency test** — encrypted VPN round-trip timing | Proves end-to-end tunnel performance |
| `stats` | Show encryption statistics (packets sent, bytes encrypted) | Shows packet counters |
| `quit` | Close VPN tunnel | — |

**You can fetch ANY URL and resolve ANY domain — examples:**

```
VPN> fetch http://httpbin.org/ip          ← best for demo (shows server's IP cleanly)
VPN> fetch https://api.github.com         ← any HTTPS URL works
VPN> fetch http://ifconfig.me             ← another IP-check service
VPN> fetch https://www.google.com         ← fetches Google's homepage through VPN

VPN> resolve youtube.com                  ← resolves YouTube's IPs through VPN
VPN> resolve canva.com                    ← resolves Canva's IPs through VPN
VPN> resolve github.com                   ← resolves GitHub's IPs through VPN
VPN> resolve stackoverflow.com            ← any domain works
```

> The demo uses `httpbin.org/ip` and `google.com` because they give short, clean output — but the tunnel works with **any URL or domain**.

> **Note:** Any text that isn't a recognized command is sent as an **encrypted tunnel echo test** — it proves the tunnel encrypts and decrypts arbitrary data, but the primary VPN features are `fetch`, `resolve`, `verify`, and `ping`.

### Example: Prove IP Masking (VPN Proxy)

```
  VPN> fetch http://httpbin.org/ip
  Tunneling HTTP request through VPN…

  ┌─ SEND ────────────────────────────────────────────────────┐
  │ Plain  [  34 B]: TUNNEL:FETCH:http://httpbin.org/ip
  │ Wire   [  70 B]: 0000000000000001a8b3c2d4e5f6...
  │ Nonce  [  12 B]  Counter [  8 B]  GCM-Tag [ 16 B]
  └──────────────────────────────────────────────────────────┘
  ┌─ RECV ────────────────────────────────────────────────────┐
  │ Wire   [  95 B]: 0000000000000002c4d5e6f7a8b9...
  │ Plain  [  59 B]: [TUNNEL:FETCH] HTTP 200 | { "origin": "103.217.237.55" }
  └──────────────────────────────────────────────────────────┘
```

> The IP `103.217.237.55` is the **server's** IP, not yours. The HTTP request was made by the server on your behalf. Your IP was never sent to httpbin.org. This is **exactly** how NordVPN and every commercial VPN masks your identity.

### Example: Prove DNS Privacy

```
  VPN> resolve google.com
  Tunneling DNS lookup through VPN…

  ┌─ SEND ────────────────────────────────────────────────────┐
  │ Plain  [  21 B]: TUNNEL:DNS:google.com
  │ Wire   [  57 B]: 00000000000000030552...
  └──────────────────────────────────────────────────────────┘
  ┌─ RECV ────────────────────────────────────────────────────┐
  │ Plain  [  43 B]: [TUNNEL:DNS] google.com → 142.251.221.238
  └──────────────────────────────────────────────────────────┘
```

> DNS resolution happened **on the VPN server**, not your machine. Your ISP cannot see that you looked up google.com — they only see encrypted bytes going to the VPN server.

### Example: Prove Post-Quantum Crypto Is Real

```
  VPN> verify
  Requesting server-side PQC verification…

  ┌─ RECV ────────────────────────────────────────────────────┐
  │ Plain  [ 421 B]: [TUNNEL:VERIFY]
  │ {
  │   "backend": "kyber-py (CRYSTALS-Kyber768 / NIST FIPS 203)",
  │   "real_kyber": true,
  │   "pk_bytes": 1184, "nist_pk": 1184,
  │   "ct_bytes": 1088, "nist_ct": 1088,
  │   "encaps_decaps_match": true,
  │   "lattice": "n=256 k=3 q=3329 (Module-LWE)",
  │   "quantum_security": "~161 qubits (NIST Level 3)",
  │   "verdict": "REAL POST-QUANTUM CRYPTO"
  │ }
  └──────────────────────────────────────────────────────────┘
```

> The server ran an **independent** Kyber-768 key generation + encapsulation + decapsulation test and proved all sizes match the NIST FIPS 203 standard exactly.

### Example: Encrypted VPN Round-Trip Latency

```
  VPN> ping
  VPN round-trip: 706 ms (encrypted)
```

> Measures: client encrypts → TCP → server decrypts → server fetches httpbin.org → server encrypts response → TCP → client decrypts. The entire VPN pipeline in one measurement.

Every command you run updates the server terminal AND the live dashboard in real time.

---

## PART 4 — What Happens During Connection (PQC Proof)

When any client connects, **both terminals automatically print**:

### Client Terminal:
```
  ┌─ PQC PROOF ──────────────────────────────────────────────┐
  │ Backend : kyber-py (CRYSTALS-Kyber768 / NIST FIPS 203)
  │ Kyber pk: 1184 B ✓  ct: 1088 B ✓  key: 32 B ✓
  │ Lattice : n=256, k=3, q=3329 (Module-LWE)
  │ Verdict : REAL POST-QUANTUM CRYPTO
  └──────────────────────────────────────────────────────────┘

  ┌─ SERVER→CLIENT (bidirectional proof) ────────────────────┐
  │ Wire  [ 132 B]: 0000000000000001a8b3c2d4e5f6...
  │ Plain [  96 B]: [SERVER→CLIENT] Welcome! Tunnel ready. PQC=VERIFIED
  └──────────────────────────────────────────────────────────┘
```

### Server Terminal:
```
  ┌─ PQC VERIFICATION ───────────────────────────────────────┐
  │ Backend   : kyber-py (CRYSTALS-Kyber768 / NIST FIPS 203)
  │ Kyber pk  :  1184 B  (NIST spec: 1184) ✓
  │ Kyber ct  :  1088 B  (NIST spec: 1088) ✓
  │ Secret    :    32 B  (256-bit key)     ✓
  │ ECDH pk   :    97 B  (P-384 uncompressed)
  │ Lattice   : n=256, k=3, q=3329 (Module-LWE)
  │ Quantum   : ~161 qubits (Level 3) — SECURE
  └──────────────────────────────────────────────────────────┘
```

This proves:
- **Kyber-768 is real** (key sizes match NIST FIPS 203 exactly)
- **Bidirectional** (server pushes welcome to client without being asked)
- **Session key derived** from both Kyber lattice + ECDH elliptic curve

---

## Quick-Reference Cheat Sheet

| Terminal | Command | Purpose |
|---|---|---|
| 1 | `py -3 launch_demo.py` | Start VPN server (port 5000) + Dashboard (port 8080) |
| 2 | `py -3 attacks/mitm_proxy.py --target 10.1.160.121` | Start MITM attacker (port 5001) |
| 3 | `py -3 client/vpn_client.py --host 10.1.160.121 --demo` | Client → direct to server |
| 3 | `py -3 client/vpn_client.py --host 10.1.160.121 --port 5001 --demo` | Client → through MITM |
| Browser | `http://10.1.160.121:8080` | Live dashboard (any device on network) |

---

## Custom Ports (Optional)

```
py -3 launch_demo.py --vpn-port 5000 --dash-port 8080
py -3 attacks/mitm_proxy.py --target 10.1.160.121 --listen-port 5001 --target-port 5000
py -3 client/vpn_client.py --host 10.1.160.121 --port 5001
```

---

## What Each Packet Contains (for the teacher)

Every encrypted VPN packet on the wire has this exact structure:

```
┌─────────────┬──────────────┬─────────────────────┬──────────────┐
│ Counter (8B)│  Nonce (12B) │  Ciphertext (var)   │ GCM Tag(16B) │
└─────────────┴──────────────┴─────────────────────┴──────────────┘
```

- **Counter (8 bytes)** — monotonically increasing; server maintains a 64-packet sliding window and rejects any counter it has already seen → **replay protection**
- **Nonce (12 bytes)** — random 96-bit value generated with `os.urandom(12)` for each packet; ensures that sending the same plaintext twice produces completely different ciphertext → **prevents pattern analysis**
- **Ciphertext (variable)** — AES-256 encrypted payload; without the 32-byte session key, this is indistinguishable from random bytes → **confidentiality**
- **GCM Tag (16 bytes)** — 128-bit GHASH authentication tag computed over the counter, nonce, and ciphertext; flipping even 1 bit in any field invalidates this tag → **tampering detection**

**Overhead:** 36 bytes per packet (8+12+16). A 34-byte plaintext becomes 70 bytes on the wire.

### What Wireshark / an attacker sees for this packet:

```
00 00 00 00 00 00 00 01   ← Counter=1 (cannot decode meaning)
a8 b3 c2 d4 e5 f6 07 18   ← Nonce (random, no pattern)
29 3a 4b 5c 7f 2e 4d 8c   ← Start of ciphertext (looks random)
a1 b0 c3 d4 ... (34 B)    ← Rest of encrypted payload
e3 f4 05 16 27 38 49 5a   ← GCM tag (first 8 bytes)
6b 7c 8d 9e af b0 c1 d2   ← GCM tag (last 8 bytes)

The attacker sees 70 bytes of seemingly random data.
They cannot tell if it's a DNS query, HTTP request, or text.
They cannot modify it (tag fails) or replay it (counter rejected).
```

---

## Why Kyber-768 Matters

| Algorithm | Against Classical Computers | Against Quantum Computers |
|---|---|---|
| RSA-2048 | Secure (2048-bit problem) | ❌ BROKEN (Shor's Algorithm) |
| ECDH P-384 | Secure (discrete log) | ❌ BROKEN (Shor's Algorithm) |
| **Kyber-768** | **Secure (Module-LWE)** | **✅ SECURE (~161 qubit security)** |

Kyber-768 was standardised as **NIST FIPS 203** in August 2024.  
This VPN uses **both** ECDH and Kyber — so it is secure against classical *and* quantum attackers.

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `ModuleNotFoundError: kyber` | Run `py -3 -m pip install kyber-py` |
| `Address already in use` | Another process using port 5000 — restart the terminal or change port with `--vpn-port 5001` |
| Client can't connect from another device | Make sure both devices are on the same Wi-Fi; check Windows Firewall allows Python |
| Dashboard not loading | Make sure `launch_demo.py` is still running in Terminal 1 |
| `36 passed` not showing in tests | Run `py -3 -m pip install pytest` then retry |

### Allow Python through Windows Firewall
1. Windows Search → **"Windows Defender Firewall"**
2. Click **"Allow an app through firewall"**
3. Click **"Allow another app"** → Browse to `python.exe`
4. Check both **Private** and **Public** → OK
