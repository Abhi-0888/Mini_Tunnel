"""
AES-256-GCM Authenticated Encryption

Features:
- AES-256 encryption (Quantum-resistant key size)
- GCM mode provides authentication (detects tampering!)
- Unique nonce per encryption
- Packet counter for replay attack protection

GCM = Galois/Counter Mode
- Encrypts data (confidentiality)
- Produces authentication tag (integrity + authenticity)
- Any modification to ciphertext will be detected!
"""

import os
import struct
from typing import Tuple, Optional
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.exceptions import InvalidTag


class TamperingError(Exception):
    """Raised when packet tampering is detected by GCM"""
    pass


class ReplayAttackError(Exception):
    """Raised when a replay attack is detected"""
    pass


class AESGCM256:
    """
    AES-256-GCM Authenticated Encryption for VPN packets
    
    Security:
    - AES-256: 256-bit key (Grover-resistant, effective 128-bit post-quantum)
    - GCM: Authenticated encryption - detects any modification
    - Nonce: 96-bit random nonce per packet
    - Counter: Monotonic counter prevents replay attacks
    """
    
    NONCE_SIZE = 12     # 96 bits (recommended for GCM)
    TAG_SIZE = 16       # 128-bit authentication tag
    COUNTER_SIZE = 8    # 64-bit packet counter
    
    def __init__(self, key: bytes):
        """
        Initialize with AES-256 key
        
        Args:
            key: 32-byte (256-bit) AES key from key exchange
        """
        if len(key) != 32:
            raise ValueError(f"Key must be 32 bytes, got {len(key)}")
        
        self.aesgcm = AESGCM(key)
        self.send_counter = 0
        self.recv_counter = 0
        self.recv_window = set()  # Sliding window for replay protection
        self.window_size = 64
    
    def encrypt(self, plaintext: bytes, associated_data: Optional[bytes] = None) -> bytes:
        """
        Encrypt plaintext with AES-256-GCM
        
        Args:
            plaintext: Data to encrypt
            associated_data: Additional authenticated data (not encrypted but authenticated)
            
        Returns:
            bytes: counter(8) + nonce(12) + ciphertext + tag(16)
        """
        # Increment send counter
        self.send_counter += 1
        counter = self.send_counter
        
        # Generate random nonce
        nonce = os.urandom(self.NONCE_SIZE)
        
        # Include counter in AAD for additional integrity
        if associated_data is None:
            associated_data = b''
        aad = struct.pack('>Q', counter) + associated_data
        
        # Encrypt with authentication
        ciphertext_with_tag = self.aesgcm.encrypt(nonce, plaintext, aad)
        
        # Pack: counter + nonce + ciphertext + tag
        packet = struct.pack('>Q', counter) + nonce + ciphertext_with_tag
        
        return packet
    
    def decrypt(self, packet: bytes, associated_data: Optional[bytes] = None) -> bytes:
        """
        Decrypt packet and verify integrity
        
        Args:
            packet: Encrypted packet from encrypt()
            associated_data: Same AAD used during encryption
            
        Returns:
            bytes: Decrypted plaintext
            
        Raises:
            TamperingError: If packet was modified
            ReplayAttackError: If packet is a replay
        """
        if len(packet) < self.COUNTER_SIZE + self.NONCE_SIZE + self.TAG_SIZE:
            raise ValueError("Packet too short")
        
        # Unpack
        counter = struct.unpack('>Q', packet[:self.COUNTER_SIZE])[0]
        nonce = packet[self.COUNTER_SIZE:self.COUNTER_SIZE + self.NONCE_SIZE]
        ciphertext_with_tag = packet[self.COUNTER_SIZE + self.NONCE_SIZE:]
        
        # Check for replay attack
        if not self._check_replay(counter):
            raise ReplayAttackError(f"Replay attack detected! Counter: {counter}")
        
        # Reconstruct AAD
        if associated_data is None:
            associated_data = b''
        aad = struct.pack('>Q', counter) + associated_data
        
        # Decrypt and verify
        try:
            plaintext = self.aesgcm.decrypt(nonce, ciphertext_with_tag, aad)
        except InvalidTag:
            raise TamperingError("Packet tampering detected! Authentication failed.")
        
        # Update replay window
        self._update_replay_window(counter)
        
        return plaintext
    
    def _check_replay(self, counter: int) -> bool:
        """
        Check if packet counter is valid (not a replay)
        
        Uses sliding window algorithm:
        - Reject if counter is too old
        - Reject if counter was already seen
        - Accept otherwise
        """
        # Too old - outside window
        if counter <= self.recv_counter - self.window_size:
            return False
        
        # Already seen
        if counter in self.recv_window:
            return False
        
        return True
    
    def _update_replay_window(self, counter: int):
        """Update replay protection state after successful decryption"""
        self.recv_window.add(counter)
        
        # Update highest seen counter
        if counter > self.recv_counter:
            self.recv_counter = counter
            
            # Clean old entries from window
            min_valid = self.recv_counter - self.window_size
            self.recv_window = {c for c in self.recv_window if c > min_valid}
    
    def get_overhead(self) -> int:
        """Get encryption overhead in bytes (counter + nonce + tag)"""
        return self.COUNTER_SIZE + self.NONCE_SIZE + self.TAG_SIZE  # 36 bytes


def aes_gcm_demo():
    """
    Demonstrate AES-256-GCM encryption with attack detection
    """
    print("=" * 60)
    print("🔐 AES-256-GCM Authenticated Encryption Demo")
    print("=" * 60)
    
    # Create cipher with shared key (from key exchange)
    key = os.urandom(32)  # In real VPN, this comes from Kyber/ECDH
    cipher = AESGCM256(key)
    
    # === Normal Encryption/Decryption ===
    print("\n📤 Encrypting message...")
    plaintext = b"Hello, secure VPN tunnel! This is confidential data."
    encrypted = cipher.encrypt(plaintext)
    print(f"   Plaintext:  {plaintext.decode()}")
    print(f"   Encrypted:  {encrypted[:40].hex()}... ({len(encrypted)} bytes)")
    print(f"   Overhead:   {cipher.get_overhead()} bytes")
    
    # Create receiver cipher with same key
    receiver = AESGCM256(key)
    decrypted = receiver.decrypt(encrypted)
    print(f"\n📥 Decrypted: {decrypted.decode()}")
    
    # === Tampering Detection ===
    print("\n" + "=" * 60)
    print("🔴 ATTACK 1: Packet Tampering")
    print("=" * 60)
    
    tampered = bytearray(encrypted)
    tampered[25] ^= 0xFF  # Flip some bits
    
    try:
        receiver.decrypt(bytes(tampered))
        print("❌ Should have detected tampering!")
    except TamperingError as e:
        print(f"✅ DETECTED: {e}")
    
    # === Replay Attack Detection ===
    print("\n" + "=" * 60)
    print("🔴 ATTACK 2: Replay Attack")
    print("=" * 60)
    
    # Send another packet
    encrypted2 = cipher.encrypt(b"Second message")
    receiver.decrypt(encrypted2)
    print("   ✓ First legitimate packet accepted")
    
    # Try to replay
    try:
        receiver.decrypt(encrypted2)  # Same packet again!
        print("❌ Should have detected replay!")
    except ReplayAttackError as e:
        print(f"✅ DETECTED: {e}")
    
    print("\n" + "=" * 60)
    print("🛡️  SECURITY SUMMARY:")
    print("   • Confidentiality: AES-256 encryption")
    print("   • Integrity:       GCM authentication tag")
    print("   • Anti-replay:     Packet counter + sliding window")
    print("   • Quantum-safe:    256-bit key (Grover-resistant)")
    print("=" * 60)


if __name__ == "__main__":
    aes_gcm_demo()
