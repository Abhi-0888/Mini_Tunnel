# 🔐 Simple VPN Demonstration Guide

This guide explains how the **Mini-VPN** works to secure communication over an insecure network (like the internet).

---

## 🎭 The Scenario

| Who? | Name | Role |
| :--- | :--- | :--- |
| 🧑 | **Client** (Alice) | Sends a sensitive message across the network. |
| 🖥️ | **Server** (Bob) | Receives the message. |
| 🦹 | **Attacker** (Eve) | Tries to intercept, read, or modify the message. |

---

## 📦 Step 1: Encryption (The Secure Envelope)

To prevent eavesdropping, we place the message inside a cryptographic "envelope."

1. **Client** generates a random **session key**.
2. **Client** encrypts the message using **AES-256-GCM**.
3. **Attacker** sees only random noise (ciphertext).

> **Concept:** Encryption transforms readable text into unreadable ciphertext.

---

## 🗝️ Step 2: Key Exchange (The Handshake)

How do the Client and Server share the *same* key without the Attacker seeing it?

**Solution: Post-Quantum Key Exchange (Kyber)**

1. **Client** and **Server** perform a mathematical exchange.
2. They publicly share components that, when combined privately, generate the **shared secret key**.
3. Even if a Quantum Computer analyzes the public components, it cannot deduce the private key.

> **Concept:** This prevents "Harvest Now, Decrypt Later" attacks.

---

## 🛡️ Step 3: Attack Defenses

The demo script (`simple_demo.py`) simulates three types of attacks:

### 1. Sniffing (Eavesdropping)
- **Attack**: Eve captures the packet.
- **Defense**: Encryption makes the payload unreadable.

### 2. Tampering (Modification)
- **Attack**: Eve flips a bit in the encrypted packet to corrupt the data.
- **Defense**: The **GCM Authentication Tag** detects the change and the Server *rejects* the packet.

### 3. Replay Attack
- **Attack**: Eve captures a valid packet and sends it again later.
- **Defense**: A **Counter/Nonce** ensures each packet is unique. The Server rejects old or duplicate packets.

---

## 🧪 Running the Demo

Run the interactive Python script to see these concepts in action:

```bash
# If 'python' command is available:
python simple_demo.py

# Or use the Python Launcher:
py simple_demo.py
```

Follow the on-screen prompts to simulate sending a secure message and witnessing the defenses against Eve.
