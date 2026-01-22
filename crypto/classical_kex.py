"""
Classical ECDH Key Exchange

⚠️ WARNING: This is QUANTUM VULNERABLE!
Shor's algorithm can break ECDH in polynomial time on a quantum computer.
This module is included for educational comparison with post-quantum Kyber.

Used to demonstrate:
- Why current VPN protocols (OpenVPN, WireGuard) are vulnerable
- The "Harvest Now, Decrypt Later" attack threat
"""

from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.backends import default_backend
import hashlib


class ClassicalECDH:
    """
    Elliptic Curve Diffie-Hellman Key Exchange
    
    Security: 192-bit (using SECP384R1)
    
    ⚠️ QUANTUM VULNERABLE - Shor's Algorithm breaks this!
    """
    
    def __init__(self):
        self.private_key = None
        self.public_key = None
        self.shared_secret = None
        self.aes_key = None
    
    def generate_keypair(self):
        """
        Generate ECDH keypair using NIST P-384 curve
        
        Returns:
            bytes: Serialized public key for transmission
        """
        self.private_key = ec.generate_private_key(
            ec.SECP384R1(),  # 384-bit curve for ~192-bit security
            default_backend()
        )
        self.public_key = self.private_key.public_key()
        
        # Serialize public key for transmission
        from cryptography.hazmat.primitives.serialization import (
            Encoding, PublicFormat
        )
        return self.public_key.public_bytes(
            Encoding.X962,
            PublicFormat.UncompressedPoint
        )
    
    def derive_shared_secret(self, peer_public_key_bytes: bytes) -> bytes:
        """
        Derive shared secret from peer's public key
        
        Args:
            peer_public_key_bytes: Peer's serialized public key
            
        Returns:
            bytes: 32-byte AES-256 key derived from shared secret
        """
        # Deserialize peer's public key
        peer_public_key = ec.EllipticCurvePublicKey.from_encoded_point(
            ec.SECP384R1(),
            peer_public_key_bytes
        )
        
        # ECDH key exchange
        self.shared_secret = self.private_key.exchange(
            ec.ECDH(),
            peer_public_key
        )
        
        # Derive AES-256 key using HKDF
        self.aes_key = HKDF(
            algorithm=hashes.SHA384(),
            length=32,  # 256 bits for AES-256
            salt=None,
            info=b'classical-ecdh-vpn-key',
            backend=default_backend()
        ).derive(self.shared_secret)
        
        return self.aes_key
    
    def get_aes_key(self) -> bytes:
        """Get the derived AES-256 key"""
        if self.aes_key is None:
            raise RuntimeError("Key exchange not completed yet!")
        return self.aes_key


def classical_key_exchange_demo():
    """
    Demonstrate classical ECDH key exchange between Alice and Bob
    
    This shows what quantum computers can break!
    """
    print("=" * 60)
    print("🔐 Classical ECDH Key Exchange Demo")
    print("⚠️  WARNING: Quantum Vulnerable!")
    print("=" * 60)
    
    # Alice generates keypair
    alice = ClassicalECDH()
    alice_public = alice.generate_keypair()
    print(f"\n👩 Alice's public key: {alice_public[:32].hex()}...")
    
    # Bob generates keypair
    bob = ClassicalECDH()
    bob_public = bob.generate_keypair()
    print(f"👨 Bob's public key:   {bob_public[:32].hex()}...")
    
    # Exchange public keys and derive shared secret
    alice_aes = alice.derive_shared_secret(bob_public)
    bob_aes = bob.derive_shared_secret(alice_public)
    
    print(f"\n🔑 Alice's AES key: {alice_aes.hex()}")
    print(f"🔑 Bob's AES key:   {bob_aes.hex()}")
    
    # Verify same key
    assert alice_aes == bob_aes, "Keys don't match!"
    print("\n✅ Keys match! Key exchange successful.")
    
    print("\n" + "=" * 60)
    print("⚠️  QUANTUM THREAT:")
    print("   A quantum computer running Shor's algorithm could")
    print("   recover the shared secret from the public keys!")
    print("=" * 60)
    
    return alice_aes


if __name__ == "__main__":
    classical_key_exchange_demo()
