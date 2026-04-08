"""
Live Dashboard — Quantum-Safe VPN
===================================
Flask web server that shows real-time VPN events via Server-Sent Events (SSE).
No extra dependencies beyond Flask (already installed).

Started automatically by launch_demo.py, but can also be imported standalone.

Browser: http://localhost:8080  (or replace localhost with LAN IP)
"""
import os
import sys
import json
import queue
import threading
from datetime import datetime
from flask import Flask, Response, render_template, jsonify

# ── shared state (written by VPN server thread, read by Flask) ────────────────

_history   = []          # last 200 events (list of dicts)
_sub_qs    = []          # one Queue per SSE subscriber
_sub_lock  = threading.Lock()

stats = {
    'packets'    : 0,
    'attacks'    : 0,
    'clients'    : 0,
    'kex_done'   : 0,
    'server_ip'  : '—',
    'server_port': 5000,
}


def emit_event(event_type: str, **kwargs):
    """
    Called by the VPN server (from any thread) to push a live event.
    Stores in history and broadcasts to all SSE subscribers.
    """
    event = {
        'type' : event_type,
        'time' : datetime.now().strftime('%H:%M:%S'),
        **kwargs,
    }

    # update stats
    if event_type == 'message':
        stats['packets'] += 1
    elif event_type == 'attack':
        stats['attacks'] += 1
    elif event_type == 'client_connect':
        stats['clients'] += 1
    elif event_type == 'kex_done':
        stats['kex_done'] += 1
    elif event_type == 'server_start':
        stats['server_ip']   = kwargs.get('host', '—')
        stats['server_port'] = kwargs.get('port', 5000)

    _history.append(event)
    if len(_history) > 200:
        del _history[:len(_history) - 200]

    with _sub_lock:
        dead = []
        for q in _sub_qs:
            try:
                q.put_nowait(event)
            except queue.Full:
                dead.append(q)
        for q in dead:
            _sub_qs.remove(q)


# ── Flask app ─────────────────────────────────────────────────────────────────

def create_app():
    app = Flask(__name__,
                template_folder=os.path.join(os.path.dirname(__file__), 'templates'))

    @app.route('/')
    def index():
        return render_template('index.html')

    @app.route('/api/stream')
    def stream():
        """Server-Sent Events endpoint — one persistent connection per browser tab."""
        q = queue.Queue(maxsize=500)
        # seed with recent history so new viewers catch up
        for ev in _history[-40:]:
            q.put(ev)
        with _sub_lock:
            _sub_qs.append(q)

        def generate():
            try:
                while True:
                    try:
                        ev = q.get(timeout=15)
                        yield f"data: {json.dumps(ev)}\n\n"
                    except queue.Empty:
                        yield ": heartbeat\n\n"   # keep connection alive
            except GeneratorExit:
                pass
            finally:
                with _sub_lock:
                    if q in _sub_qs:
                        _sub_qs.remove(q)

        return Response(
            generate(),
            mimetype='text/event-stream',
            headers={
                'Cache-Control'    : 'no-cache',
                'X-Accel-Buffering': 'no',
                'Connection'       : 'keep-alive',
            },
        )

    @app.route('/api/stats')
    def api_stats():
        return jsonify(stats)

    @app.route('/api/history')
    def api_history():
        return jsonify(_history[-50:])

    return app


# ── standalone entry-point ────────────────────────────────────────────────────

if __name__ == '__main__':
    app = create_app()
    print('\n  Dashboard: http://localhost:8080\n')
    app.run(host='0.0.0.0', port=8080, debug=False, threaded=True)
