"""
Packet Tampering Demonstration

This script demonstrates:
1. Intercepting an encrypted VPN packet
2. Modifying bits in the ciphertext
3. Server detecting tampering via GCM authentication tag

Defense mechanism: AES-GCM Authenticated Encryption

Real-world impact:
Without integrity protection, an attacker could:
- Modify transaction amounts
- Change destination addresses
- Inject malicious commands
- Corrupt data silently
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from crypto.aes_gcm import AESGCM256, TamperingError


def tampering_demo():
    """
    Demonstrate packet tampering detection
    
    Shows how AES-GCM detects ANY modification to ciphertext
    """
    print("=" * 70)
    print("[ATTACK DEMONSTRATION] Packet Tampering")
    print("=" * 70)
    
    # Setup encryption
    key = os.urandom(32)
    sender = AESGCM256(key)
    receiver = AESGCM256(key)
    
    print("\n[SCENARIO]")
    print("   Alice sends encrypted message to Bob through VPN tunnel.")
    print("   Eve (attacker) intercepts and modifies the encrypted packet.")
    
    # === Step 1: Original packet ===
    print("\n" + "-" * 70)
    print("STEP 1: Alice encrypts and sends a message")
    print("-" * 70)
    
    original_message = b"Transfer $100 to account 12345"
    encrypted_packet = sender.encrypt(original_message)
    
    print(f"   >>> Original: {original_message.decode()}")
    print(f"   >>> Encrypted: {encrypted_packet.hex()[:60]}...")
    
    # === Step 2: Eve intercepts ===
    print("\n" + "-" * 70)
    print("STEP 2: Eve intercepts the encrypted packet")
    print("-" * 70)
    
    print(f"   [!] Eve captured the packet")
    print(f"   [!] Eve cannot read it (encrypted)")
    print(f"   [!] But what if Eve flips some bits?")
    
    # === Step 3: Various tampering attempts ===
    print("\n" + "-" * 70)
    print("STEP 3: Eve attempts various tampering attacks")
    print("-" * 70)
    
    tampering_attacks = [
        ("Flip 1 bit in ciphertext", 25, 0x01),
        ("Flip 8 bits (1 byte)", 30, 0xFF),
        ("Modify counter field", 2, 0x01),
        ("Modify nonce field", 10, 0x55),
        ("Modify authentication tag", -5, 0xAA),
    ]
    
    for attack_name, position, xor_value in tampering_attacks:
        print(f"\n   [ATTACK] Attack: {attack_name}")
        
        # Create tampered packet
        tampered = bytearray(encrypted_packet)
        
        # Handle negative index
        pos = position if position >= 0 else len(tampered) + position
        
        original_byte = tampered[pos]
        tampered[pos] ^= xor_value
        modified_byte = tampered[pos]
        
        print(f"      Position {pos}: 0x{original_byte:02X} → 0x{modified_byte:02X}")
        
        # Try to decrypt
        try:
            decrypted = receiver.decrypt(bytes(tampered))
            print(f"      [FAIL] VULNERABLE! Modified data accepted:")
            print(f"         {decrypted.decode()}")
        except TamperingError:
            print(f"      [SUCCESS] PROTECTED! Tampering detected and blocked!")
        except Exception as e:
            print(f"      [SUCCESS] PROTECTED! Error: {type(e).__name__}")
    
    # === Step 4: Why this matters ===
    print("\n" + "-" * 70)
    print("STEP 4: Theoretical bit-flipping attack (without GCM)")
    print("-" * 70)
    
    print("""
    Without authentication (e.g., AES-CTR or AES-CBC without MAC):
    
    Original plaintext:  "Transfer $100 to account 12345"
    Attacker knows position of "$100" in the message structure.
    
    With CTR/CBC (no auth):
    - XOR specific ciphertext bits
    - Corresponding plaintext bits flip!
    - Change "$100" to "$900" by flipping bits
    - Receiver decrypts modified amount!
    
    With GCM:
    - ANY modification detected
    - Authentication tag verification fails
    - Packet is REJECTED entirely
    """)
    
    # === Summary ===
    print("=" * 70)
    print("📊 DEFENSE MECHANISM: Galois/Counter Mode (GCM)")
    print("=" * 70)
    print("""
    How GCM protects:
    
    1. ENCRYPTION (Counter Mode):
       - Encrypts plaintext for confidentiality
       - Uses incrementing counter + AES block cipher
    
    2. AUTHENTICATION (GMAC):
       - Computes authentication tag over:
         * Ciphertext
         * Additional Authenticated Data (AAD)
         * Lengths of both
       - Tag is appended to ciphertext
    
    3. VERIFICATION:
       - Receiver recomputes tag
       - Compares with received tag
       - ANY mismatch → reject packet
    
    Result:
    - Attacker cannot modify ciphertext undetected
    - Attacker cannot forge valid tag (needs key)
    - Even 1-bit change will be caught!
    """)


def bit_flip_visualization():
    """
    Visualize what bit-flipping looks like
    """
    print("\n" + "=" * 70)
    print("🔬 Bit-Flip Attack Visualization")
    print("=" * 70)
    
    # Show bit representation
    original = b"$100"
    print(f"\n   Original bytes: {original}")
    print(f"   As hex:         {original.hex()}")
    print(f"   As binary:", end="")
    
    for byte in original:
        print(f" {byte:08b}", end="")
    print()
    
    # XOR attack
    xor_value = 0x08  # Flip bit to change '1' to '9'
    modified = bytearray(original)
    modified[1] ^= xor_value
    
    print(f"\n   XOR with:       00000000 {xor_value:08b} 00000000 00000000")
    print(f"   Result binary: ", end="")
    for byte in modified:
        print(f" {byte:08b}", end="")
    print()
    
    print(f"\n   Modified bytes: {bytes(modified)}")
    print(f"   Amount changed: $100 → ${chr(modified[1])}{chr(modified[2])}{chr(modified[3])}")


if __name__ == "__main__":
    tampering_demo()
    bit_flip_visualization()
