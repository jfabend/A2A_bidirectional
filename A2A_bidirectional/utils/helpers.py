from fastapi import FastAPI
import threading, time

from A2A_bidirectional.utils.remote_client import AgentCard
from A2A_bidirectional.server.a2a_server import create_app, start_server

def _serve_in_background(agent, card: AgentCard, port: int) -> None:
    """Start the A2A FastAPI server in a daemon thread."""
    app: FastAPI = create_app(agent, card)

    thread = threading.Thread(
        target=start_server, args=(app, port), daemon=True
    )
    thread.start()

    # give Uvicorn a moment to bind the socket before we register
    time.sleep(0.8)