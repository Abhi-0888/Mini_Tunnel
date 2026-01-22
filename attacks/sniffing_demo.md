# 📡 Packet Sniffing Demonstration

This guide demonstrates how to capture and analyze VPN tunnel traffic using Wireshark, showing that encrypted payloads are unreadable.

## Prerequisites

1. **Wireshark** - Download from [wireshark.org](https://www.wireshark.org/)
2. **Running VPN** - Start the mini-vpn server and client
3. **Admin privileges** - Required for packet capture

---

## Step 1: Start the VPN Tunnel

### Terminal 1 - Start Server
```powershell
cd d:\SrmAP\Fullstack\Tunnel_VPN\mini-vpn
python -m server.vpn_server --port 5000
```

### Terminal 2 - Start Client
```powershell
cd d:\SrmAP\Fullstack\Tunnel_VPN\mini-vpn
python -m client.vpn_client --server localhost --port 5000
```

---

## Step 2: Configure Wireshark

### 2.1 Select Interface
1. Open Wireshark
2. Select **Loopback: lo0** (or **Npcap Loopback Adapter** on Windows)
3. If testing between machines, select the appropriate network interface

### 2.2 Apply Capture Filter
```
tcp port 5000
```

### 2.3 Start Capture
Click the blue shark fin button to start capturing

---

## Step 3: Generate Traffic

In the VPN client terminal, send some messages:
```
📤 You: Hello, this is a secret message!
📤 You: My password is: SuperSecret123
📤 You: Transfer $10000 to account 99999
```

---

## Step 4: Analyze Captured Packets

### 4.1 Stop Capture
Click the red square to stop capturing

### 4.2 Examine a Packet
1. Click on a TCP packet with data
2. Look at the **TCP** layer → **Payload**
3. Observe the data section

### Expected Result:
```
┌────────────────────────────────────────────────────────────┐
│ Data (encrypted)                                           │
├────────────────────────────────────────────────────────────┤
│ 00 00 00 00 00 00 00 01  7a 9c 3f 8b 2e 1d 5a 6c           │
│ 8f 0e 2b 4d 6a 8c 0e 2f  d3 a7 19 5e 82 c4 f0 1b           │
│ ...                                                        │
│ [Random-looking bytes - no readable text!]                 │
└────────────────────────────────────────────────────────────┘
```

### What You Should See:
- ✅ **Source/Destination IP** - Visible (network layer)
- ✅ **Source/Destination Port** - Visible (transport layer)
- ✅ **Packet length** - Visible
- ❌ **Original message** - NOT visible (encrypted!)
- ❌ **Passwords/sensitive data** - NOT visible
- ❌ **Transaction details** - NOT visible

---

## Step 5: Compare with Unencrypted Traffic

### Without VPN (Raw TCP)
If you captured unencrypted traffic, you would see:
```
┌────────────────────────────────────────────────────────────┐
│ Data (plaintext - VULNERABLE!)                             │
├────────────────────────────────────────────────────────────┤
│ 48 65 6c 6c 6f 2c 20 74  68 69 73 20 69 73 20 61   Hello, this is a│
│ 20 73 65 63 72 65 74 20  6d 65 73 73 61 67 65 21    secret message!│
└────────────────────────────────────────────────────────────┘
```

### With VPN (AES-256-GCM Encrypted)
```
┌────────────────────────────────────────────────────────────┐
│ Data (encrypted - PROTECTED!)                              │
├────────────────────────────────────────────────────────────┤
│ 00 00 00 01 a7 3b 9f c2  d8 4e 6a 1b f3 82 5d 09   ........N.j.]..│
│ e7 a1 c4 56 8b 2f d0 93  7c 1e 4a b8 f6 25 3d 81   ...V./...|.J.%=.│
│ [Completely random - no patterns or readable text!]        │
└────────────────────────────────────────────────────────────┘
```

---

## Step 6: Packet Structure Analysis

### Encrypted Packet Format
```
┌─────────────┬───────────────┬────────────────────┬──────────────┐
│ Counter     │ Nonce         │ Ciphertext         │ Auth Tag     │
│ (8 bytes)   │ (12 bytes)    │ (variable)         │ (16 bytes)   │
└─────────────┴───────────────┴────────────────────┴──────────────┘
     │              │                  │                 │
     │              │                  │                 └── GCM authentication
     │              │                  └── Encrypted payload
     │              └── Random per-packet IV
     └── Replay protection counter
```

### In Wireshark, you can decode:
- **Bytes 0-7**: Packet counter (incrementing)
- **Bytes 8-19**: Nonce (random each packet)
- **Bytes 20-end-16**: Encrypted data
- **Last 16 bytes**: Authentication tag

---

## Wireshark Display Filters

### Useful filters for analysis:
```
# VPN traffic only
tcp.port == 5000

# Packets with data
tcp.port == 5000 && tcp.len > 0

# Large packets (likely data, not handshake)
tcp.port == 5000 && frame.len > 100

# Specific direction
tcp.port == 5000 && ip.src == 127.0.0.1
```

---

## Security Observations

### What the Attacker CAN See:
| Information | Visible? | Impact |
|-------------|----------|--------|
| VPN server IP | ✅ Yes | Knows VPN exists |
| Connection timing | ✅ Yes | Traffic analysis |
| Packet sizes | ✅ Yes | Pattern analysis |
| Message content | ❌ No | Protected! |

### What the Attacker CANNOT Do:
- ❌ Read message contents
- ❌ See usernames/passwords
- ❌ View transaction details
- ❌ Modify packets undetected (GCM)
- ❌ Replay old packets (counter)

---

## Conclusion

This demonstration proves that:

1. **Confidentiality** ✅
   - Encrypted payloads appear as random bytes
   - No readable text visible in Wireshark
   
2. **Network Metadata Leakage**
   - IP addresses and timing are still visible
   - This is inherent to network protocols
   - Real VPNs hide this via tunneling to VPN server

3. **Defense in Depth**
   - Even if packets are captured, they're useless without the key
   - Key was exchanged using quantum-safe Kyber
   - Future quantum computers cannot break the key exchange

---

## Screenshots to Include in Report

1. Wireshark capture showing encrypted VPN traffic
2. Packet details showing random bytes (no readable text)
3. Comparison with unencrypted traffic (if available)
4. Filter demonstration showing only VPN packets
