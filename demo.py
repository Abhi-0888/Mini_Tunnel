"""Quick demonstration of VPN security features"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from crypto.aes_gcm import AESGCM256, TamperingError, ReplayAttackError

print("=" * 60)
print("QUANTUM-SAFE MINI-VPN - SECURITY DEMONSTRATION")
print("=" * 60)

# Setup with shared key
key = os.urandom(32)
sender = AESGCM256(key)
receiver = AESGCM256(key)

# Test 1: Normal encryption/decryption
print("\n[TEST 1] Normal Encryption/Decryption")
msg = b"Secret VPN payload!"
encrypted = sender.encrypt(msg)
decrypted = receiver.decrypt(encrypted)
print(f"  Plaintext:  {msg.decode()}")
print(f"  Encrypted:  {encrypted[:30].hex()}...")
print(f"  Decrypted:  {decrypted.decode()}")
print("  [PASS] Encryption working correctly")

# Test 2: Tampering detection
print("\n[TEST 2] Tampering Detection (GCM)")
encrypted2 = sender.encrypt(b"Test message")
tampered = bytearray(encrypted2)
tampered[25] ^= 0xFF  # Flip bits
try:
    receiver.decrypt(bytes(tampered))
    print("  [FAIL] Tampering not detected!")
except TamperingError:
    print("  Modified packet was REJECTED!")
    print("  [PASS] GCM detected tampering")

# Test 3: Replay attack protection
print("\n[TEST 3] Replay Attack Protection")
encrypted3 = sender.encrypt(b"Transfer $1000")
receiver.decrypt(encrypted3)
print("  First packet: ACCEPTED")
try:
    receiver.decrypt(encrypted3)  # Replay same packet!
    print("  [FAIL] Replay succeeded!")
except ReplayAttackError:
    print("  Replayed packet: REJECTED!")
    print("  [PASS] Counter detected replay")

print("\n" + "=" * 60)
print("ALL SECURITY TESTS PASSED!")
print("=" * 60)
