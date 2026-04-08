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
Example: `10.1.176.145`

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
       http://10.1.176.145:8080

  2. Connect the VPN client:
       py -3 client/vpn_client.py --host 10.1.176.145
  ...

  Dashboard starting: http://10.1.176.145:8080
  * Serving Flask app 'dashboard.app'
```

✅ The VPN server is now listening on **port 5000** and the web dashboard is on **port 8080**.

---

### STEP 2 — Open the Live Dashboard in a Browser

On **any device on the same network**, open a browser and go to:

```
http://<YOUR-LAN-IP>:8080
```

Example: `http://10.1.176.145:8080`

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

**Option A — Automated demo (5 pre-set messages):**
```
py -3 client/vpn_client.py --host <YOUR-LAN-IP> --demo
```

**Option B — Interactive mode (type your own messages):**
```
py -3 client/vpn_client.py --host <YOUR-LAN-IP>
```

**From another device on the same network:**
```
py -3 client/vpn_client.py --host 10.1.176.145 --demo
```

**What you will see in the client terminal (Terminal 2):**
```
============================
  QUANTUM-SAFE VPN CLIENT
============================
  [01:04:32] TCP connected to 10.1.176.145:5000
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
  │  TUNNEL ACTIVE  10.1.176.145:54321                      │
  └──────────────────────────────────────────────────────────┘

  ┌─ PKT #001 ── from 10.1.176.145:54321 ──────────────┐
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
py -3 attacks/mitm_proxy.py --target <YOUR-LAN-IP>
```

Example:
```
py -3 attacks/mitm_proxy.py --target 10.1.176.145
```

**What you will see in Terminal 2 (attacker's view):**
```
  ══════════════════════════════════════════════════
  QUANTUM-SAFE VPN — MAN-IN-THE-MIDDLE PROXY
  ══════════════════════════════════════════════════

  Listening on 0.0.0.0:5001
  Forwarding to 10.1.176.145:5000

  Waiting for a victim to connect...
```

> The attacker is now sitting between the client (port 5001) and the real server (port 5000).  
> Anyone connecting to **port 5001** is unknowingly going through the attacker.

---

### STEP 3 — Connect the Client THROUGH the Attacker

Open **Terminal 3** in the project folder and run:

```
py -3 client/vpn_client.py --host <YOUR-LAN-IP> --port 5001 --demo
```

Example:
```
py -3 client/vpn_client.py --host 10.1.176.145 --port 5001 --demo
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
  │ Duplicate counter — packet from 10.1.176.145:61234
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
  │ GCM auth tag mismatch — packet from 10.1.176.145:61234
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

## PART 3 — Interactive Mode (Type Your Own Messages)

Instead of `--demo`, run the client without any extra flag:

```
py -3 client/vpn_client.py --host <YOUR-LAN-IP>
```

Then type any message and press Enter:
```
  YOU> Hello from the quantum-safe tunnel!
  YOU> This is a secret message
  YOU> stats          ← shows encryption statistics
  YOU> quit           ← closes the connection
```

Every message you type will appear in the server terminal AND update the dashboard live.

---

## Quick-Reference Cheat Sheet

| Terminal | Command | Purpose |
|---|---|---|
| 1 | `py -3 launch_demo.py` | Start VPN server (port 5000) + Dashboard (port 8080) |
| 2 | `py -3 attacks/mitm_proxy.py --target LAN_IP` | Start MITM attacker (port 5001) |
| 3 | `py -3 client/vpn_client.py --host LAN_IP --demo` | Client → direct to server |
| 3 | `py -3 client/vpn_client.py --host LAN_IP --port 5001 --demo` | Client → through MITM |
| Browser | `http://LAN_IP:8080` | Live dashboard (any device on network) |

---

## Custom Ports (Optional)

```
py -3 launch_demo.py --vpn-port 5000 --dash-port 8080
py -3 attacks/mitm_proxy.py --target LAN_IP --listen-port 5001 --target-port 5000
py -3 client/vpn_client.py --host LAN_IP --port 5001
```

---

## What Each Packet Contains (for the teacher)

Every encrypted packet on the wire has this structure:

```
┌─────────────┬──────────────┬─────────────────────┬──────────────┐
│ Counter (8B)│  Nonce (12B) │  Ciphertext (variable)│  GCM Tag(16B)│
└─────────────┴──────────────┴─────────────────────┴──────────────┘
```

- **Counter** — monotonically increasing; server rejects any duplicate → **replay protection**
- **Nonce** — random 96-bit value; unique per packet → **prevents pattern analysis**
- **Ciphertext** — AES-256 encrypted payload; unreadable without session key → **confidentiality**
- **GCM Tag** — 128-bit authentication tag; any 1-bit change invalidates it → **tampering detection**

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
