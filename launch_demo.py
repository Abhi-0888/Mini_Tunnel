"""
Quantum-Safe VPN — One-Command Demo Launcher
=============================================
Starts both the VPN server and the live web dashboard in a single process.

Usage:
    py -3 launch_demo.py                # default host/ports
    py -3 launch_demo.py --vpn-port 5000 --dash-port 8080

Then in separate terminals:
    py -3 client/vpn_client.py --host <LAN-IP>
    py -3 client/vpn_client.py --host <LAN-IP> --demo
    py -3 attacks/mitm_proxy.py --target <LAN-IP>

And open the dashboard in any browser:
    http://<LAN-IP>:8080
"""
import os
import sys
import threading
import argparse
import socket as _socket

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def _get_lan_ip():
    try:
        return _socket.gethostbyname(_socket.gethostname())
    except Exception:
        return '127.0.0.1'


def main():
    ap = argparse.ArgumentParser(description='Quantum-Safe VPN Demo Launcher')
    ap.add_argument('--vpn-port',  type=int, default=5000,
                    help='VPN server port (default 5000)')
    ap.add_argument('--dash-port', type=int, default=8080,
                    help='Dashboard port (default 8080)')
    a = ap.parse_args()

    lan_ip = _get_lan_ip()

    if os.name == 'nt':
        os.system('color')

    B = '\033[1m'; C = '\033[96m'; G = '\033[92m'
    Y = '\033[93m'; D = '\033[2m'; X = '\033[0m'

    print(f"\n{B}{C}{'='*66}{X}")
    print(f"{B}{C}  QUANTUM-SAFE VPN — LIVE DEMO LAUNCHER{X}")
    print(f"{B}{C}  Kyber-768 (NIST FIPS 203) + ECDH P-384 + AES-256-GCM{X}")
    print(f"{B}{C}{'='*66}{X}\n")

    # ── import dashboard emit function ────────────────────────────────────────
    from dashboard.app import emit_event, create_app

    # ── start VPN server in background thread ─────────────────────────────────
    from server.vpn_server import VPNServer
    vpn = VPNServer(host='0.0.0.0', port=a.vpn_port, event_callback=emit_event)
    vpn_thread = threading.Thread(target=vpn.start, daemon=True, name='vpn-server')
    vpn_thread.start()

    # small delay so server has time to print its banner
    import time; time.sleep(0.5)

    # ── print teacher-facing instructions ─────────────────────────────────────
    print(f"\n{B}{'─'*66}{X}")
    print(f"{B}  DEMO INSTRUCTIONS  (share this with your audience){X}")
    print(f"{'─'*66}")
    print(f"\n  {G}1. Open dashboard in any browser on the same network:{X}")
    print(f"       {B}http://{lan_ip}:{a.dash_port}{X}\n")
    print(f"  {G}2. Connect the VPN client (another device or new terminal):{X}")
    print(f"       {B}py -3 client/vpn_client.py --host {lan_ip}{X}")
    print(f"       {B}py -3 client/vpn_client.py --host {lan_ip} --demo{X}\n")
    print(f"  {G}3. Start the MITM attacker (shows interception live):{X}")
    print(f"       {B}py -3 attacks/mitm_proxy.py --target {lan_ip}{X}")
    print(f"     Then connect client THROUGH the attacker:{X}")
    print(f"       {B}py -3 client/vpn_client.py --host {lan_ip} --port 5001 --demo{X}\n")
    print(f"  {G}4. Watch the dashboard — see every packet, key exchange,{X}")
    print(f"     {G}and every blocked attack in real time.{X}")
    print(f"\n{D}  Press Ctrl+C to stop.{X}\n")
    print(f"{'─'*66}\n")

    # ── start Flask dashboard (blocks in main thread) ─────────────────────────
    app = create_app()
    print(f"  {G}Dashboard starting:{X} {B}http://{lan_ip}:{a.dash_port}{X}\n")

    import logging
    log = logging.getLogger('werkzeug')
    log.setLevel(logging.WARNING)   # suppress Flask request noise

    try:
        app.run(host='0.0.0.0', port=a.dash_port,
                debug=False, threaded=True, use_reloader=False)
    except KeyboardInterrupt:
        print(f"\n  {Y}Launcher stopped.{X}\n")


if __name__ == '__main__':
    main()
