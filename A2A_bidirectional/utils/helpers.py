from fastapi import FastAPI
import threading, time

from A2A_bidirectional.utils.remote_client import AgentCard
from A2A_bidirectional.server.a2a_server import create_app, start_server

# utils/helpers.py (or directly in each chat() function)

def serve_and_register(app, card, port, host_url):
    """
    1. spin up the FastAPI server in a daemon thread
    2. wait until the socket is open
    3. POST /register to the host
    """
    import socket, threading, time, requests, uvicorn

    # 1) start uvicorn in the background
    def _run():
        uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")

    threading.Thread(target=_run, daemon=True).start()

    # 2) wait for the port to open (max ~3 s)
    for _ in range(30):
        with socket.socket() as s:
            if s.connect_ex(("127.0.0.1", port)) == 0:
                break
        time.sleep(0.1)
    else:
        print(f"⚠️  server on :{port} never came up"); return

    # 3) now it is safe to register
    try:
        requests.post(f"{host_url}/register",
                      json=card.model_dump(), timeout=5)
        print("✅ auto‑registered with HostAgent")
    except requests.RequestException as exc:
        print(f"⚠️  could not register automatically: {exc}")
