"""
Post-Quantum Key Exchange using Kyber (ML-KEM)

✅ QUANTUM SAFE!
Based on the Learning With Errors (LWE) problem over lattices.
Standardized by NIST as ML-KEM (FIPS 203).

Kyber-768 provides:
- ~192-bit classical security
- ~128-bit post-quantum security

This implementation uses a simplified educational version.
For production, use liboqs-python or pqcrypto library.
"""

import os
import hashlib
from typing import Tuple
import secrets


class KyberKEM:
    """
    Simplified Kyber Key Encapsulation Mechanism (KEM)
    
    A KEM is different from key exchange:
    - Key Exchange (ECDH): Both parties contribute randomness
    - KEM: One party encapsulates, other decapsulates
    
    Security: Based on Module-LWE (Learning With Errors)
    
    ✅ QUANTUM SAFE - Resistant to Shor's Algorithm!
    """
    
    # Kyber-768 parameters (simplified for education)
    N = 256          # Polynomial degree
    K = 3            # Module rank (Kyber-768)
    Q = 3329         # Modulus
    ETA1 = 2         # Noise parameter
    ETA2 = 2         # Noise parameter
    
    def __init__(self):
        self.public_key = None
        self.secret_key = None
        self.shared_secret = None
    
    def _sample_noise(self, size: int, eta: int) -> list:
        """Sample centered binomial distribution noise"""
        result = []
        for _ in range(size):
            bits = secrets.randbits(2 * eta)
            val = sum((bits >> i) & 1 for i in range(eta))
            val -= sum((bits >> (eta + i)) & 1 for i in range(eta))
            result.append(val % self.Q)
        return result
    
    def _poly_add(self, a: list, b: list) -> list:
        """Add two polynomials mod Q"""
        return [(a[i] + b[i]) % self.Q for i in range(len(a))]
    
    def _poly_mul_simple(self, a: list, b: list) -> list:
        """Simplified polynomial multiplication (schoolbook)"""
        result = [0] * self.N
        for i in range(min(len(a), self.N)):
            for j in range(min(len(b), self.N)):
                idx = (i + j) % self.N
                sign = 1 if (i + j) < self.N else -1
                result[idx] = (result[idx] + sign * a[i] * b[j]) % self.Q
        return result
    
    def generate_keypair(self) -> Tuple[bytes, bytes]:
        """
        Generate Kyber keypair
        
        The public key can be shared openly.
        The secret key must be kept private.
        
        Returns:
            Tuple[bytes, bytes]: (public_key, secret_key)
        """
        # Generate random seed
        seed = os.urandom(32)
        
        # Generate matrix A from seed (simplified - in real Kyber, A is expanded from seed)
        # For simplicity, we store random polynomials
        A = [[secrets.randbelow(self.Q) for _ in range(self.N)] 
             for _ in range(self.K * self.K)]
        
        # Generate secret vector s with small coefficients
        s = [self._sample_noise(self.N, self.ETA1) for _ in range(self.K)]
        
        # Generate error vector e with small coefficients
        e = [self._sample_noise(self.N, self.ETA1) for _ in range(self.K)]
        
        # Compute public key: t = A*s + e
        t = []
        for i in range(self.K):
            ti = [0] * self.N
            for j in range(self.K):
                product = self._poly_mul_simple(A[i * self.K + j], s[j])
                ti = self._poly_add(ti, product)
            ti = self._poly_add(ti, e[i])
            t.append(ti)
        
        # Serialize keys (simplified)
        pk_data = {
            'seed': seed,
            't': t,
            'A': A  # In real Kyber, A is regenerated from seed
        }
        sk_data = {
            's': s
        }
        
        # Simple serialization for education
        import json
        self.public_key = json.dumps({
            'seed': seed.hex(),
            't': t,
            'A': A
        }).encode()
        self.secret_key = json.dumps({
            's': s
        }).encode()
        
        return self.public_key, self.secret_key
    
    def encapsulate(self, public_key: bytes) -> Tuple[bytes, bytes]:
        """
        Encapsulate: Generate shared secret and ciphertext
        
        Only the holder of the corresponding secret key can
        recover the shared secret from the ciphertext.
        
        Args:
            public_key: Recipient's public key
            
        Returns:
            Tuple[bytes, bytes]: (ciphertext, shared_secret)
        """
        import json
        pk = json.loads(public_key.decode())
        t = pk['t']
        A = pk['A']
        
        # Generate random message
        m = os.urandom(32)
        
        # Generate ephemeral vectors r, e1, e2
        r = [self._sample_noise(self.N, self.ETA1) for _ in range(self.K)]
        e1 = [self._sample_noise(self.N, self.ETA2) for _ in range(self.K)]
        e2 = self._sample_noise(self.N, self.ETA2)
        
        # Compute u = A^T * r + e1
        u = []
        for i in range(self.K):
            ui = [0] * self.N
            for j in range(self.K):
                product = self._poly_mul_simple(A[j * self.K + i], r[j])
                ui = self._poly_add(ui, product)
            ui = self._poly_add(ui, e1[i])
            u.append(ui)
        
        # Compute v = t^T * r + e2 + encode(m)
        v = e2.copy()
        for i in range(self.K):
            product = self._poly_mul_simple(t[i], r[i])
            v = self._poly_add(v, product)
        
        # Encode message into polynomial (simplified)
        for i in range(min(32 * 8, self.N)):
            byte_idx = i // 8
            bit_idx = i % 8
            if byte_idx < len(m):
                bit = (m[byte_idx] >> bit_idx) & 1
                v[i] = (v[i] + bit * (self.Q // 2)) % self.Q
        
        # Ciphertext = (u, v)
        ciphertext = json.dumps({
            'u': u,
            'v': v
        }).encode()
        
        # Shared secret = H(m)
        shared_secret = hashlib.sha384(m).digest()[:32]
        
        return ciphertext, shared_secret
    
    def decapsulate(self, secret_key: bytes, ciphertext: bytes) -> bytes:
        """
        Decapsulate: Recover shared secret from ciphertext
        
        Args:
            secret_key: Own secret key
            ciphertext: Ciphertext from encapsulation
            
        Returns:
            bytes: Shared secret (same as encapsulator has)
        """
        import json
        sk = json.loads(secret_key.decode())
        ct = json.loads(ciphertext.decode())
        
        s = sk['s']
        u = ct['u']
        v = ct['v']
        
        # Compute v - s^T * u
        m_poly = v.copy()
        for i in range(self.K):
            product = self._poly_mul_simple(s[i], u[i])
            m_poly = [(m_poly[j] - product[j]) % self.Q for j in range(self.N)]
        
        # Decode message from polynomial
        m = bytearray(32)
        for i in range(min(32 * 8, self.N)):
            byte_idx = i // 8
            bit_idx = i % 8
            # Check if closer to Q/2 (bit=1) or 0 (bit=0)
            if m_poly[i] > self.Q // 4 and m_poly[i] < 3 * self.Q // 4:
                m[byte_idx] |= (1 << bit_idx)
        
        # Shared secret = H(m)
        shared_secret = hashlib.sha384(bytes(m)).digest()[:32]
        
        return shared_secret


def kyber_key_exchange_demo():
    """
    Demonstrate Post-Quantum Kyber key encapsulation
    
    This is what protects against quantum computers!
    """
    print("=" * 60)
    print("🛡️  Post-Quantum Kyber Key Exchange Demo")
    print("✅ QUANTUM SAFE!")
    print("=" * 60)
    
    # Server generates keypair
    server = KyberKEM()
    server_pk, server_sk = server.generate_keypair()
    print(f"\n🖥️  Server public key size: {len(server_pk)} bytes")
    print(f"🔐 Server secret key size: {len(server_sk)} bytes")
    
    # Client encapsulates
    client = KyberKEM()
    ciphertext, client_shared = client.encapsulate(server_pk)
    print(f"\n💻 Client ciphertext size: {len(ciphertext)} bytes")
    print(f"🔑 Client shared secret: {client_shared.hex()[:32]}...")
    
    # Server decapsulates
    server_shared = server.decapsulate(server_sk, ciphertext)
    print(f"🔑 Server shared secret: {server_shared.hex()[:32]}...")
    
    # Verify
    if client_shared == server_shared:
        print("\n✅ Shared secrets match! Key exchange successful.")
    else:
        print("\n❌ Shared secrets don't match!")
        # Note: Simplified implementation may have some decoding errors
        # Production code should use liboqs-python
    
    print("\n" + "=" * 60)
    print("💪 QUANTUM RESISTANCE:")
    print("   Based on Module-LWE (Learning With Errors)")
    print("   No known quantum algorithm can break this efficiently!")
    print("=" * 60)
    
    return client_shared


if __name__ == "__main__":
    kyber_key_exchange_demo()
