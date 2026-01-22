"""
Replay Attack Demonstration

This script demonstrates:
1. Capturing a valid encrypted VPN packet
2. Re-sending (replaying) the same packet
3. Server detecting and rejecting the replay

Defense mechanism: Packet counter with sliding window

Real-world impact:
Without replay protection, an attacker could:
- Re-send payment transactions
- Re-authenticate with old credentials
- Duplicate commands/actions
"""

import socket
import time
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from crypto.aes_gcm import AESGCM256, ReplayAttackError


def replay_attack_demo():
    """
    Demonstrate replay attack detection
    
    This shows how the VPN protects against packet replay
    """
    print("=" * 70)
    print("[ATTACK DEMONSTRATION] Replay Attack")
    print("=" * 70)
    
    # Simulate shared key (in real attack, attacker doesn't have this)
    # We use it here just to show the detection mechanism
    key = os.urandom(32)
    
    # === Setup: Legitimate sender and receiver ===
    sender = AESGCM256(key)
    receiver = AESGCM256(key)
    
    print("\n[SCENARIO]")
    print("   Alice sends encrypted message to Bob through VPN tunnel.")
    print("   Eve (attacker) captures the packet and tries to replay it.")
    
    # === Step 1: Legitimate packet ===
    print("\n" + "-" * 70)
    print("STEP 1: Alice sends legitimate encrypted packet")
    print("-" * 70)
    
    original_message = b"Transfer $1000 to account 12345"
    encrypted_packet = sender.encrypt(original_message)
    
    print(f"   >>> Original message: {original_message.decode()}")
    print(f"   >>> Encrypted packet: {encrypted_packet[:40].hex()}...")
    print(f"   >>> Packet size: {len(encrypted_packet)} bytes")
    
    # === Step 2: Bob receives and processes ===
    print("\n" + "-" * 70)
    print("STEP 2: Bob receives and decrypts the packet")
    print("-" * 70)
    
    decrypted = receiver.decrypt(encrypted_packet)
    print(f"   <<< Decrypted: {decrypted.decode()}")
    print(f"   [PASS] Packet accepted! Counter validated.")
    
    # === Step 3: Eve captures the packet ===
    print("\n" + "-" * 70)
    print("STEP 3: Eve (attacker) captures the encrypted packet")
    print("-" * 70)
    
    captured_packet = encrypted_packet  # Eve's copy
    print(f"   [!] Eve captured: {captured_packet[:40].hex()}...")
    print(f"   [!] Eve cannot read the content (encrypted)")
    print(f"   [!] But Eve knows this packet caused a $1000 transfer!")
    
    # === Step 4: Eve replays the packet ===
    print("\n" + "-" * 70)
    print("STEP 4: Eve replays the captured packet (ATTACK!)")
    print("-" * 70)
    
    print(f"   [ATTACK] Eve re-sends the same packet to Bob...")
    time.sleep(1)  # Dramatic pause
    
    try:
        # Try to decrypt the replayed packet
        receiver.decrypt(captured_packet)
        print(f"   [FAIL] VULNERABLE! Packet was accepted again!")
        print(f"   [FAIL] Another $1000 transferred!")
    except ReplayAttackError as e:
        print(f"   [SUCCESS] PROTECTED! Server detected replay attack:")
        print(f"      >> {e}")
        print(f"   [SUCCESS] Packet REJECTED - no duplicate transfer!")
    
    # === Step 5: Multiple replay attempts ===
    print("\n" + "-" * 70)
    print("STEP 5: Eve tries multiple replay variations")
    print("-" * 70)
    
    attacks = [
        ("Same packet immediately", captured_packet),
        ("Same packet after delay", captured_packet),
    ]
    
    for attack_name, packet in attacks:
        print(f"\n   [ATTACK] Attempting: {attack_name}")
        try:
            receiver.decrypt(packet)
            print(f"      [FAIL] Attack succeeded - VULNERABLE!")
        except ReplayAttackError:
            print(f"      [SUCCESS] Attack blocked - PROTECTED!")
    
    # === Summary ===
    print("\n" + "=" * 70)
    print("📊 DEFENSE MECHANISM: Packet Counter + Sliding Window")
    print("=" * 70)
    print("""
    How it works:
    1. Each packet has a unique counter value
    2. Receiver tracks highest counter seen
    3. Receiver maintains a window of recent counters
    4. Any packet with:
       - Counter already seen → REJECTED
       - Counter too old → REJECTED
       - Counter in valid range and new → ACCEPTED
    
    Why this works:
    - Attacker cannot generate new valid counters (no key)
    - Replaying old packets always fails
    - Even network delays/reordering handled by sliding window
    """)


def replay_attack_against_server():
    """
    Attempt replay attack against running VPN server
    
    ⚠️ Requires VPN server to be running!
    """
    print("=" * 70)
    print("🔴 LIVE REPLAY ATTACK against VPN Server")
    print("=" * 70)
    
    SERVER_HOST = 'localhost'
    SERVER_PORT = 5000
    
    print(f"\n⚠️  Make sure VPN server is running on {SERVER_HOST}:{SERVER_PORT}")
    print("   Run: python -m server.vpn_server")
    
    try:
        # We would need to:
        # 1. Capture packets between legitimate client and server
        # 2. Store the encrypted packet
        # 3. Replay it
        
        # For demo, we'll just show the concept
        print("\n📋 Attack steps (conceptual):")
        print("   1. Use Wireshark to capture VPN traffic")
        print("   2. Filter by port: tcp.port == 5000")
        print("   3. Find encrypted packet in TCP payload")
        print("   4. Copy the payload bytes")
        print("   5. Use Python socket to resend same bytes")
        print("   6. Observe server rejecting the replay")
        
        print("\n💡 See sniffing_demo.md for Wireshark instructions")
        
    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Replay Attack Demo')
    parser.add_argument('--live', action='store_true',
                        help='Attempt live attack against running server')
    
    args = parser.parse_args()
    
    if args.live:
        replay_attack_against_server()
    else:
        replay_attack_demo()
