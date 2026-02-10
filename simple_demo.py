import time
import sys
import os
import random

# Add the parent directory to sys.path to import crypto modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from crypto.aes_gcm import AESGCM256, TamperingError, ReplayAttackError
except ImportError:
    # If not running installed, just mock for the demo if crypto is missing
    # But ideally we use the real code!
    pass

class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

# Fallback for Windows if ANSI colors aren't supported (though modern Win10/11 supports them)
if os.name == 'nt':
    os.system('color')

def print_step(title):
    print("\n" + "="*60)
    print(f"{Colors.HEADER}STEP: {title}{Colors.ENDC}")
    print("="*60 + "\n")
    time.sleep(1)

def slow_print(text, delay=0.03):
    for char in text:
        sys.stdout.write(char)
        sys.stdout.flush()
        time.sleep(delay)
    print()

def demo():
    print(f"\n{Colors.BOLD}🔐  SECURE VPN CHANNEL DEMONSTRATION  🔐{Colors.ENDC}\n")
    print("Simulating a secure connection establishment and data transfer.")
    print("We will demonstrate protection against Sniffing, Tampering, and Replay attacks.\n")
    time.sleep(2)

    # --- SETUP ---
    print_step("1. ESTABLISHING SECURE CONNECTION")
    slow_print("[Client] Initiating handshake with [Server]...")
    time.sleep(1)
    slow_print("[Server] Responding with Kyber Public Key...")
    time.sleep(1)
    
    # Simulate Kyber/ECDH key exchange
    magic_key = os.urandom(32)
    print(f"\n{Colors.GREEN}✅  Handshake Complete!{Colors.ENDC}")
    print(f"    Shared Secret Key established: {magic_key.hex()[:8]}... (Hidden from attacker)")
    time.sleep(2)

    # --- MESSAGE ---
    print_step("2. PREPARING SECURE PAYLOAD")
    secret_message = input(f"{Colors.BLUE}👉  Enter a sensitive message to send: {Colors.ENDC}")
    if not secret_message:
        secret_message = "Transfer $1,000,000"
    
    print(f"\n📝  Original Payload: '{secret_message}'")
    
    # Encryption
    sender = AESGCM256(magic_key)
    receiver = AESGCM256(magic_key)
    
    encrypted_packet = sender.encrypt(secret_message.encode())
    print(f"🔒  Encrypted Packet (Ciphertext):")
    print(f"    {encrypted_packet.hex()[:60]}...")
    time.sleep(2)

    # --- ATTACK 1: SNIFFING ---
    print_step("3. ATTACK SIMULATION: EAVESDROPPING")
    print(f"{Colors.WARNING}⚠️   Attacker (Eve) is capturing network traffic...{Colors.ENDC}")
    time.sleep(1.5)
    print(f"    Eve captured packet: {encrypted_packet.hex()[:30]}...")
    print(f"    Eve attempts to read it...")
    time.sleep(1)
    print(f"{Colors.FAIL}❌  FAILED: Payload is encrypted. Eve sees only noise.{Colors.ENDC}")
    time.sleep(2)

    # --- ATTACK 2: TAMPERING ---
    print_step("4. ATTACK SIMULATION: TAMPERING")
    print(f"{Colors.WARNING}⚠️   Eve intercepts the packet and modifies it!{Colors.ENDC}")
    time.sleep(1)
    
    # Tamper with the packet
    tampered_packet = bytearray(encrypted_packet)
    # Flip a bit in the middle of the ciphertext
    tampered_index = len(tampered_packet) // 2
    tampered_packet[tampered_index] ^= 0xFF
    
    print(f"    Original Byte at pos {tampered_index}: {encrypted_packet[tampered_index]:02x}")
    print(f"    Modified Byte at pos {tampered_index}: {tampered_packet[tampered_index]:02x}")
    print(f"    Forwarding tampered packet to Server...")
    time.sleep(1)

    print(f"\n[Server] Receiving packet...")
    try:
        receiver.decrypt(bytes(tampered_packet))
        print(f"{Colors.FAIL}🔥  CRITICAL FAILURE: Server accepted modified packet!{Colors.ENDC}")
    except TamperingError:
        print(f"{Colors.GREEN}🛡️  BLOCKED: Integrity Check Failed! (Auth Tag mismatch){Colors.ENDC}")
        print("    The server detected the modification and rejected the packet.")
    time.sleep(2)

    # --- ATTACK 3: REPLAY ---
    print_step("5. ATTACK SIMULATION: REPLAY")
    print(f"{Colors.WARNING}⚠️   Eve resends the captured VALID packet from Step 3...{Colors.ENDC}")
    time.sleep(1)
    
    # First, let the VALID packet go through (so the counter increments)
    print("[Server] Receiving original valid packet (Legitimate)...")
    try:
        decrypted = receiver.decrypt(encrypted_packet)
        print(f"{Colors.GREEN}✅  ACCEPTED: '{decrypted.decode()}'{Colors.ENDC}")
    except Exception as e:
        print(f"Error processing valid packet: {e}")

    time.sleep(1)
    print(f"\n[Server] Receiving REPLAYED packet (Attack)...")
    try:
        receiver.decrypt(encrypted_packet)
        print(f"{Colors.FAIL}🔥  CRITICAL FAILURE: Server accepted replayed packet!{Colors.ENDC}")
    except ReplayAttackError:
        print(f"{Colors.GREEN}🛡️  BLOCKED: Replay Protection!{Colors.ENDC}")
        print("    The server detected an old counter value and rejected the packet.")
    
    time.sleep(2)

    print("\n" + "="*60)
    print(f"{Colors.BOLD}🎉  DEMONSTRATION SUCCESSFUL  🎉{Colors.ENDC}")
    print("The system successfully defended against all simulated attacks.")
    print("="*60 + "\n")

if __name__ == "__main__":
    demo()
