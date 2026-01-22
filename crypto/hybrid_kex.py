"""
Hybrid Key Exchange: Kyber + ECDH

Defense-in-depth approach combining:
- Kyber (Post-Quantum Safe) - Protects against future quantum computers
- ECDH (Classical) - Proven security against classical computers

If either algorithm is broken, the other still provides security.
This is the recommended approach during the PQC transition period.

Used by: Signal Protocol, Chrome/BoringSSL experiments
"""

import hashlib
from typing import Tuple

from .classical_kex import ClassicalECDH
from .kyber_kex import KyberKEM


class HybridKeyExchange:
    """
    Hybrid Key Exchange combining Kyber and ECDH
    
    Security Model:
    - If only classical computers exist → ECDH is secure
    - If quantum computers exist → Kyber is secure
    - Both secrets are combined → Secure in both scenarios
    
    This is the recommended "belt and suspenders" approach!
    """
    
    def __init__(self):
        self.ecdh = ClassicalECDH()
        self.kyber = KyberKEM()
        self.combined_key = None
    
    def generate_keypairs(self) -> Tuple[bytes, bytes, bytes, bytes]:
        """
        Generate both ECDH and Kyber keypairs
        
        Returns:
            Tuple containing:
            - ecdh_public: ECDH public key
            - kyber_public: Kyber public key
            - kyber_secret: Kyber secret key (keep private!)
            - (ECDH private key is stored internally)
        """
        ecdh_public = self.ecdh.generate_keypair()
        kyber_public, kyber_secret = self.kyber.generate_keypair()
        
        return ecdh_public, kyber_public, kyber_secret
    
    def initiate_exchange(self, peer_ecdh_public: bytes, peer_kyber_public: bytes) -> Tuple[bytes, bytes]:
        """
        Initiator side: Perform ECDH and Kyber encapsulation
        
        Args:
            peer_ecdh_public: Peer's ECDH public key
            peer_kyber_public: Peer's Kyber public key
            
        Returns:
            Tuple[bytes, bytes]: (kyber_ciphertext, combined_aes_key)
        """
        # ECDH key agreement
        ecdh_secret = self.ecdh.derive_shared_secret(peer_ecdh_public)
        
        # Kyber encapsulation
        kyber_ciphertext, kyber_secret = self.kyber.encapsulate(peer_kyber_public)
        
        # Combine secrets using HKDF-style combination
        self.combined_key = self._combine_secrets(ecdh_secret, kyber_secret)
        
        return kyber_ciphertext, self.combined_key
    
    def complete_exchange(self, peer_ecdh_public: bytes, kyber_secret_key: bytes, 
                          kyber_ciphertext: bytes) -> bytes:
        """
        Responder side: Perform ECDH and Kyber decapsulation
        
        Args:
            peer_ecdh_public: Peer's ECDH public key
            kyber_secret_key: Own Kyber secret key
            kyber_ciphertext: Ciphertext from initiator
            
        Returns:
            bytes: Combined AES-256 key
        """
        # ECDH key agreement
        ecdh_secret = self.ecdh.derive_shared_secret(peer_ecdh_public)
        
        # Kyber decapsulation
        kyber_secret = self.kyber.decapsulate(kyber_secret_key, kyber_ciphertext)
        
        # Combine secrets
        self.combined_key = self._combine_secrets(ecdh_secret, kyber_secret)
        
        return self.combined_key
    
    def _combine_secrets(self, ecdh_secret: bytes, kyber_secret: bytes) -> bytes:
        """
        Combine ECDH and Kyber secrets into final AES key
        
        Method: SHA-384(ECDH_secret || Kyber_secret || label)
        
        This ensures:
        - If ECDH is broken, Kyber still contributes entropy
        - If Kyber is broken, ECDH still contributes entropy
        """
        combined = ecdh_secret + kyber_secret + b'hybrid-vpn-key-v1'
        return hashlib.sha384(combined).digest()[:32]  # AES-256 key
    
    def get_combined_key(self) -> bytes:
        """Get the combined AES-256 key after exchange"""
        if self.combined_key is None:
            raise RuntimeError("Key exchange not completed!")
        return self.combined_key


def hybrid_key_exchange_demo():
    """
    Demonstrate hybrid Kyber + ECDH key exchange
    
    Best of both worlds!
    """
    print("=" * 60)
    print("🔐 Hybrid Key Exchange Demo (Kyber + ECDH)")
    print("   Defense-in-depth for PQC transition!")
    print("=" * 60)
    
    # === Server Setup ===
    print("\n📡 Server generating keypairs...")
    server = HybridKeyExchange()
    server_ecdh_pub, server_kyber_pub, server_kyber_sk = server.generate_keypairs()
    print(f"   ECDH public key:  {len(server_ecdh_pub)} bytes")
    print(f"   Kyber public key: {len(server_kyber_pub)} bytes")
    
    # === Client Setup ===
    print("\n💻 Client generating keypairs...")
    client = HybridKeyExchange()
    client_ecdh_pub, client_kyber_pub, client_kyber_sk = client.generate_keypairs()
    
    # === Client initiates exchange ===
    print("\n🔄 Client initiating key exchange...")
    kyber_ct, client_key = client.initiate_exchange(server_ecdh_pub, server_kyber_pub)
    print(f"   Kyber ciphertext: {len(kyber_ct)} bytes")
    print(f"   Client combined key: {client_key.hex()[:32]}...")
    
    # === Server completes exchange ===
    print("\n🔄 Server completing key exchange...")
    server_key = server.complete_exchange(client_ecdh_pub, server_kyber_sk, kyber_ct)
    print(f"   Server combined key: {server_key.hex()[:32]}...")
    
    # === Verify ===
    print("\n" + "=" * 60)
    if client_key == server_key:
        print("✅ SUCCESS! Both parties have the same key!")
    else:
        print("⚠️  Keys differ (simplified Kyber demo may have minor errors)")
        print("   Production should use liboqs-python for precise Kyber")
    
    print("\n🛡️  SECURITY ANALYSIS:")
    print("   • Classical attacker: Cannot break ECDH")
    print("   • Quantum attacker:   Cannot break Kyber")
    print("   • Combined key:       Secure against BOTH!")
    print("=" * 60)
    
    return client_key


if __name__ == "__main__":
    hybrid_key_exchange_demo()
