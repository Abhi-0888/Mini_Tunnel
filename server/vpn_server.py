"""
VPN Server - Encrypted Tunnel Endpoint

This server:
1. Accepts client connections
2. Performs quantum-safe key exchange (Kyber/Hybrid)
3. Decrypts incoming packets with AES-256-GCM
4. Detects tampering and replay attacks
5. Can forward decrypted packets (in full implementation)

Demonstrates:
- Post-Quantum key exchange
- Authenticated encryption
- Attack detection
"""

import socket
import sys
import threading
import argparse
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from crypto.hybrid_kex import HybridKeyExchange
from crypto.aes_gcm import AESGCM256, TamperingError, ReplayAttackError


class VPNServer:
    """
    VPN Server with quantum-safe encryption
    
    Handles:
    - Client connections
    - Hybrid key exchange (Kyber + ECDH)
    - Encrypted tunnel communication
    - Attack detection (tampering, replay)
    """
    
    def __init__(self, host: str = '0.0.0.0', port: int = 5000):
        self.host = host
        self.port = port
        self.server_socket = None
        self.running = False
        self.clients = {}  # client_addr -> (socket, cipher)
    
    def start(self):
        """Start the VPN server"""
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        try:
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(5)
            self.running = True
            
            print("=" * 60)
            print("QUANTUM-SAFE VPN SERVER")
            print(f"   Listening on {self.host}:{self.port}")
            print("   Using: Kyber + ECDH + AES-256-GCM")
            print("=" * 60)
            
            self._accept_clients()
            
        except OSError as e:
            print(f"Error: Cannot bind to port {self.port}: {e}")
            sys.exit(1)
    
    def _accept_clients(self):
        """Accept incoming client connections"""
        print("\nWAITING: for client connections...\n")
        
        try:
            while self.running:
                try:
                    client_socket, client_addr = self.server_socket.accept()
                    print(f"CONNECT: New connection from {client_addr}")
                    
                    # Handle client in new thread
                    handler = threading.Thread(
                        target=self._handle_client,
                        args=(client_socket, client_addr),
                        daemon=True
                    )
                    handler.start()
                    
                except socket.timeout:
                    continue
                    
        except KeyboardInterrupt:
            print("\n\nSIGNAL: Shutting down server...")
            self.stop()
    
    def _handle_client(self, client_socket: socket.socket, client_addr: tuple):
        """Handle individual client connection"""
        cipher = None
        
        try:
            # Perform key exchange
            cipher = self._perform_key_exchange(client_socket, client_addr)
            
            if not cipher:
                print(f"FAILED: Key exchange failed with {client_addr}")
                client_socket.close()
                return
            
            self.clients[client_addr] = (client_socket, cipher)
            print(f"SUCCESS: Secure tunnel established with {client_addr}")
            
            # Handle encrypted communication
            self._client_communication_loop(client_socket, cipher, client_addr)
            
        except Exception as e:
            print(f"ERROR: handling {client_addr}: {e}")
            import traceback
            traceback.print_exc()
        finally:
            if client_addr in self.clients:
                del self.clients[client_addr]
            try:
                client_socket.close()
            except:
                pass
            print(f"DISCONNECT: Client {client_addr} disconnected")
    
    def _perform_key_exchange(self, client_socket: socket.socket, 
                               client_addr: tuple) -> AESGCM256:
        """
        Perform hybrid Kyber + ECDH key exchange
        
        Returns:
            AESGCM256 cipher if successful, None otherwise
        """
        print(f"\n[KEY_EXCHANGE] with {client_addr}...")
        
        try:
            key_exchange = HybridKeyExchange()
            
            # Generate our keypairs
            server_ecdh_pub, server_kyber_pub, server_kyber_sk = \
                key_exchange.generate_keypairs()
            
            # Receive client's public keys
            print(f"   <<< Receiving client public keys...")
            client_ecdh_pub = self._recv_data(client_socket)
            client_kyber_pub = self._recv_data(client_socket)
            
            if not client_ecdh_pub or not client_kyber_pub:
                return None
            
            # Send our public keys
            print(f"   >>> Sending server public keys...")
            self._send_data(client_socket, server_ecdh_pub)
            self._send_data(client_socket, server_kyber_pub)
            
            # Receive Kyber ciphertext from client
            print(f"   <<< Receiving Kyber ciphertext...")
            kyber_ct = self._recv_data(client_socket)
            
            if not kyber_ct:
                return None
            
            # Complete key exchange (server decapsulates)
            shared_key = key_exchange.complete_exchange(
                client_ecdh_pub, server_kyber_sk, kyber_ct
            )
            
            print(f"   Shared key established: {shared_key[:16].hex()}...")
            
            # Create cipher
            return AESGCM256(shared_key)
            
        except Exception as e:
            print(f"   ERROR: Key exchange error: {e}")
            return None
    
    def _client_communication_loop(self, client_socket: socket.socket,
                                    cipher: AESGCM256, client_addr: tuple):
        """Handle encrypted communication with client"""
        print(f"\nACTIVE: Tunnel active with {client_addr}")
        print("   Listening for encrypted packets...\n")
        
        while self.running:
            try:
                # Receive encrypted data
                encrypted = self._recv_data(client_socket)
                
                if not encrypted:
                    break
                
                # Decrypt and verify
                try:
                    plaintext = cipher.decrypt(encrypted)
                    print(f"RECV [{client_addr[0]}]: {plaintext.decode()}")
                    
                    # Echo back (in real VPN, would forward the packet)
                    response = f"Server received: {plaintext.decode()}"
                    encrypted_response = cipher.encrypt(response.encode())
                    self._send_data(client_socket, encrypted_response)
                    
                except TamperingError as e:
                    print(f"ALERT: SECURITY from {client_addr}: {e}")
                    # Don't respond to tampered packets
                    
                except ReplayAttackError as e:
                    print(f"ALERT: SECURITY from {client_addr}: {e}")
                    # Don't respond to replayed packets
                    
            except ConnectionResetError:
                break
            except Exception as e:
                print(f"❌ Communication error: {e}")
                break
    
    def _send_data(self, sock: socket.socket, data: bytes):
        """Send length-prefixed data"""
        length = len(data).to_bytes(4, 'big')
        sock.sendall(length + data)
    
    def _recv_data(self, sock: socket.socket) -> bytes:
        """Receive length-prefixed data"""
        length_bytes = self._recv_exact(sock, 4)
        if not length_bytes:
            return None
        length = int.from_bytes(length_bytes, 'big')
        return self._recv_exact(sock, length)
    
    def _recv_exact(self, sock: socket.socket, n: int) -> bytes:
        """Receive exactly n bytes"""
        data = b''
        while len(data) < n:
            try:
                chunk = sock.recv(n - len(data))
                if not chunk:
                    return None
                data += chunk
            except:
                return None
        return data
    
    def stop(self):
        """Stop the VPN server"""
        self.running = False
        
        # Close all client connections
        for addr, (sock, _) in list(self.clients.items()):
            try:
                sock.close()
            except:
                pass
        
        # Close server socket
        if self.server_socket:
            try:
                self.server_socket.close()
            except:
                pass
        
        print("🛑 Server stopped")


def main():
    parser = argparse.ArgumentParser(description='Quantum-Safe VPN Server')
    parser.add_argument('--host', '-H', default='0.0.0.0',
                        help='Bind address (default: 0.0.0.0)')
    parser.add_argument('--port', '-p', type=int, default=5000,
                        help='Listen port (default: 5000)')
    parser.add_argument('--test', action='store_true',
                        help='Run in test mode')
    
    args = parser.parse_args()
    
    server = VPNServer(args.host, args.port)
    
    try:
        server.start()
    except KeyboardInterrupt:
        server.stop()


if __name__ == "__main__":
    main()
