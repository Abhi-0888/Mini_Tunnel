# Quantum-Safe VPN — Visual Demonstration Guide

This guide walks through what a real VPN does — and how Tunnel_VPN proves each feature live.

---

## The Scenario

| Who | Role | What they see |
|---|---|---|
| **Client** (your laptop) | Sends HTTP/DNS requests through VPN | Plaintext + encrypted wire bytes side by side |
| **Server** (VPN server) | Receives encrypted traffic, proxies to internet | Decrypts client requests, fetches on their behalf |
| **Attacker** (Eve/MITM) | Intercepts all packets between client and server | Only random-looking ciphertext. Cannot read, modify, or replay. |
| **Dashboard** (browser) | Real-time monitor for the teacher/audience | Animated topology, wire hex vs plaintext, attack alerts |

---

## What the VPN Demo Proves

### 1. Encrypted Tunnel — All Data Is Ciphertext

```
Client sends:  "TUNNEL:FETCH:http://httpbin.org/ip"   ← readable text
Wire carries:  0000000000000001ec654b5ddfeab75c...     ← 70 bytes of random-looking data

Attacker sees the wire bytes. CANNOT see the plaintext.
```

### 2. IP Masking — Your IP Is Hidden

```
VPN> fetch http://httpbin.org/ip

Without VPN: httpbin sees YOUR IP → 10.1.160.121
With VPN:    httpbin sees SERVER IP → 103.217.237.55
```

The server made the HTTP request on your behalf. Your IP was never exposed.

### 3. DNS Privacy — ISP Sees Nothing

```
VPN> resolve google.com

Without VPN: ISP DNS log → "User looked up google.com at 23:31"
With VPN:    ISP sees → encrypted bytes to port 5000. Zero DNS queries.
```

### 4. Attack Resistance — Replay & Tamper Blocked

```
Replay: Attacker resends same packet → Server: "Counter already seen. DROPPED."
Tamper: Attacker flips 1 bit       → Server: "GCM tag mismatch. DROPPED."
```

### 5. Post-Quantum Crypto — Future-Proof

```
Kyber-768 key sizes match NIST FIPS 203:
  Public key: 1184 B ✓  Ciphertext: 1088 B ✓  Secret: 32 B ✓
  Lattice: n=256, k=3, q=3329 (Module-LWE)
  Security: ~161 qubits — no quantum computer can break this today
```

---

## Running the Demo (3 Terminals + Browser)

```
Terminal 1:  py -3 launch_demo.py                                    ← Server + Dashboard
Terminal 2:  py -3 attacks/mitm_proxy.py --target <LAN-IP>           ← MITM Attacker
Terminal 3:  py -3 client/vpn_client.py --host <LAN-IP> --port 5001 --demo  ← Client through MITM
Browser:     http://<LAN-IP>:8080                                    ← Live dashboard
```

The 8-step automated demo runs:
1. PQC verification (prove Kyber-768 is real)
2. DNS tunnel: resolve google.com through VPN
3. DNS tunnel: resolve github.com through VPN
4. HTTP tunnel: fetch public IP through VPN (proves IP masking)
5. HTTP tunnel: fetch headers through VPN
6. Echo test: encrypt sensitive data through tunnel
7. Echo test: encrypt medical data through tunnel
8. Latency test: measure full encrypted round-trip

All traffic shows on the dashboard in real time with wire hex vs plaintext side by side.
