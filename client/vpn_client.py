"""
VPN Client - Packet Capture and Encrypted Tunnel

This client:
1. Captures network packets using Scapy
2. Performs quantum-safe key exchange (Kyber/Hybrid)
3. Encrypts packet payloads with AES-256-GCM
4. Sends encrypted packets through tunnel to server

⚠️ Requires Administrator/root privileges for packet capture!
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


class VPNClient:
    """
    VPN Client with quantum-safe encryption
    
    Flow:
    1. Connect to VPN server
    2. Perform hybrid key exchange (Kyber + ECDH)
    3. Capture packets and encrypt payloads
    4. Send encrypted packets through tunnel
    5. Receive and decrypt response packets
    """
    
    def __init__(self, server_host: str, server_port: int):
        self.server_host = server_host
        self.server_port = server_port
        self.socket = None
        self.cipher = None
        self.running = False
        self.key_exchange = HybridKeyExchange()

    def __repr__(self):
        status = "Connected" if self.cipher else "Disconnected"
        return f"<VPNClient(server={self.server_host}:{self.server_port}, status={status})>"
    
    def connect(self) -> bool:
        """
        Connect to VPN server and perform key exchange
        
        Returns:
            bool: True if connection and key exchange successful
        """
        print(f"Connecting to VPN server at {self.server_host}:{self.server_port}...")
        
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.server_host, self.server_port))
            print("Done: Connected to server")
            
            # Perform key exchange
            if self._perform_key_exchange():
                print("Done: Quantum-safe key exchange complete!")
                return True
            else:
                print("Error: Key exchange failed")
                return False
                
        except ConnectionRefusedError:
            print(f"Error: Connection refused. Is the server running?")
            return False
        except Exception as e:
            print(f"Error: Connection error: {e}")
            return False
    
    def _perform_key_exchange(self) -> bool:
        """
        Perform hybrid Kyber + ECDH key exchange with server
        
        Protocol:
        1. Client generates keypairs
        2. Client sends ECDH public + Kyber public to server
        3. Server responds with ECDH public + Kyber ciphertext
        4. Both derive same shared key
        """
        print("\n[KEY_EXCHANGE] Initiating quantum-safe key exchange...")
        
        try:
            # Generate our keypairs
            client_ecdh_pub, client_kyber_pub, client_kyber_sk = \
                self.key_exchange.generate_keypairs()
            
            print(f"   >>> Sending client public keys...")
            
            # Send our public keys (length-prefixed)
            self._send_data(client_ecdh_pub)
            self._send_data(client_kyber_pub)
            
            # Receive server's public keys
            print(f"   <<< Receiving server public keys...")
            server_ecdh_pub = self._recv_data()
            server_kyber_pub = self._recv_data()
            
            if not server_ecdh_pub or not server_kyber_pub:
                return False
            
            # Initiate exchange (client encapsulates)
            kyber_ct, shared_key = self.key_exchange.initiate_exchange(
                server_ecdh_pub, server_kyber_pub
            )
            
            # Send Kyber ciphertext to server
            print(f"   >>> Sending Kyber ciphertext...")
            self._send_data(kyber_ct)
            
            # Initialize cipher with shared key
            self.cipher = AESGCM256(shared_key)
            
            print(f"   Shared key established: {shared_key[:16].hex()}...")
            return True
            
        except Exception as e:
            print(f"   Error during key exchange: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def _send_data(self, data: bytes):
        """Send length-prefixed data"""
        length = len(data).to_bytes(4, 'big')
        self.socket.sendall(length + data)
    
    def _recv_data(self) -> bytes:
        """Receive length-prefixed data"""
        length_bytes = self._recv_exact(4)
        if not length_bytes:
            return None
        length = int.from_bytes(length_bytes, 'big')
        return self._recv_exact(length)
    
    def _recv_exact(self, n: int) -> bytes:
        """Receive exactly n bytes"""
        data = b''
        while len(data) < n:
            chunk = self.socket.recv(n - len(data))
            if not chunk:
                return None
            data += chunk
        return data

    def get_stats(self) -> dict:
        """Get VPN session statistics"""
        if self.cipher:
            return self.cipher.get_stats()
        return {}
    
    def send_encrypted(self, data: bytes) -> bool:
        """
        Encrypt and send data through VPN tunnel
        
        Args:
            data: Plaintext data to send
            
        Returns:
            bool: True if sent successfully
        """
        if not self.cipher:
            print("❌ Not connected or key exchange not complete")
            return False
        
        try:
            encrypted = self.cipher.encrypt(data)
            self._send_data(encrypted)
            return True
        except Exception as e:
            print(f"❌ Send error: {e}")
            return False
    
    def receive_encrypted(self) -> bytes:
        """
        Receive and decrypt data from VPN tunnel
        
        Returns:
            bytes: Decrypted data, or None on error
        """
        if not self.cipher:
            return None
        
        try:
            encrypted = self._recv_data()
            if not encrypted:
                return None
            
            decrypted = self.cipher.decrypt(encrypted)
            return decrypted
            
        except TamperingError as e:
            print(f"🔴 SECURITY ALERT: {e}")
            return None
        except ReplayAttackError as e:
            print(f"🔴 SECURITY ALERT: {e}")
            return None
        except Exception as e:
            print(f"❌ Receive error: {e}")
            return None
    
    def start_interactive(self):
        """
        Start interactive mode - send messages through tunnel
        """
        self.running = True
        
        # Start receiver thread
        receiver = threading.Thread(target=self._receiver_loop, daemon=True)
        receiver.start()
        
        print("\n" + "=" * 50)
        print("🔐 VPN Tunnel Active - Type messages to send")
        print("   Type 'quit' to disconnect")
        print("=" * 50 + "\n")
        
        try:
            while self.running:
                message = input("📤 You: ")
                if message.lower() == 'quit':
                    break
                
                if message.lower() == 'stats':
                    print(f"📊 Stats: {self.get_stats()}")
                    continue

                if message:
                    if not self.send_encrypted(message.encode()):
                        print("❌ Failed to send message (connection lost?)")
                        break
        except KeyboardInterrupt:
            print("\n\n⚡ Interrupted")
        finally:
            self.disconnect()
    
    def _receiver_loop(self):
        """Background thread to receive messages"""
        while self.running:
            try:
                data = self.receive_encrypted()
                if data:
                    print(f"\n📥 Server: {data.decode()}")
                    print("📤 You: ", end='', flush=True)
            except:
                break
    
    def disconnect(self):
        """Disconnect from VPN server"""
        self.running = False
        if self.socket:
            try:
                self.socket.close()
            except:
                pass
        print("🔌 Disconnected from VPN server")


def capture_packets_demo():
    """
    Demonstrate packet capture with Scapy
    
    ⚠️ Requires Administrator privileges!
    """
    print("=" * 60)
    print("📡 Packet Capture Demo (Scapy)")
    print("⚠️  Requires Administrator/root privileges!")
    print("=" * 60)
    
    try:
        from scapy.all import sniff, IP, TCP, UDP, Raw
        
        def packet_callback(packet):
            if IP in packet:
                src = packet[IP].src
                dst = packet[IP].dst
                proto = "TCP" if TCP in packet else "UDP" if UDP in packet else "Other"
                
                print(f"\n📦 Captured Packet:")
                print(f"   Source:      {src}")
                print(f"   Destination: {dst}")
                print(f"   Protocol:    {proto}")
                
                if Raw in packet:
                    payload = bytes(packet[Raw])
                    print(f"   Payload:     {payload[:50]}..." if len(payload) > 50 else f"   Payload:     {payload}")
        
        print("\n🔍 Capturing 5 packets... (this may take a moment)")
        sniff(prn=packet_callback, count=5, store=False)
        print("\n✅ Capture complete!")
        
    except PermissionError:
        print("\n❌ Permission denied! Run as Administrator.")
    except ImportError:
        print("\n❌ Scapy not installed. Run: pip install scapy")
    except Exception as e:
        print(f"\n❌ Error: {e}")


def main():
    parser = argparse.ArgumentParser(description='Quantum-Safe VPN Client')
    parser.add_argument('--server', '-s', default='localhost',
                        help='VPN server address (default: localhost)')
    parser.add_argument('--port', '-p', type=int, default=5000,
                        help='VPN server port (default: 5000)')
    parser.add_argument('--capture', '-c', action='store_true',
                        help='Run packet capture demo')
    parser.add_argument('--test', action='store_true',
                        help='Run in test mode')
    
    args = parser.parse_args()
    
    if args.capture:
        capture_packets_demo()
        return
    
    print("=" * 60)
    print("🛡️  Quantum-Safe VPN Client")
    print("   Using: Kyber + ECDH + AES-256-GCM")
    print("=" * 60)
    
    client = VPNClient(args.server, args.port)
    
    if client.connect():
        if args.test:
            # Test mode - send one message and exit
            client.send_encrypted(b"Test message from client!")
            response = client.receive_encrypted()
            if response:
                print(f"📥 Response: {response.decode()}")
            client.disconnect()
        else:
            # Interactive mode
            client.start_interactive()
    else:
        print("\n❌ Failed to connect to VPN server")
        sys.exit(1)


if __name__ == "__main__":
    main()
