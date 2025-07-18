"""Synchronous JSON‑RPC client + lightweight discovery for A2A peers."""
from __future__ import annotations

import uuid
from typing import Dict, List, Optional

import requests

__all__ = [
    "AgentCapabilities",
    "AgentCard",
    "TaskState",
    "RemoteAgentClient",
    "HostAgent",
]


class AgentCapabilities:
    def __init__(
        self,
        streaming: bool = False,
        pushNotifications: bool = False,
        stateTransitionHistory: bool = False,
    ) -> None:
        self.streaming = streaming
        self.pushNotifications = pushNotifications
        self.stateTransitionHistory = stateTransitionHistory

    def model_dump(self) -> dict:  # helper for JSON
        return self.__dict__


class AgentCard:
    """Minimal subset of the A2A AgentCard spec for demo purposes."""

    def __init__(
        self,
        name: str,
        url: str,
        version: str = "0.1.0",
        capabilities: Optional[AgentCapabilities] = None,
        description: str | None = None,
    ) -> None:
        self.name = name
        self.url = url
        self.version = version
        self.capabilities = capabilities or AgentCapabilities()
        self.description = description or "No description."

    # -------------------------------------------------------------
    # JSON helpers (FastAPI loves dicts)
    # -------------------------------------------------------------
    def model_dump(self) -> dict:  # compatible with Pydantic‑style
        return {
            "name": self.name,
            "url": self.url,
            "version": self.version,
            "description": self.description,
            "capabilities": self.capabilities.model_dump(),
        }


class TaskState:
    SUBMITTED = "submitted"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELED = "canceled"
    UNKNOWN = "unknown"
    INPUT_REQUIRED = "input_required"


class RemoteAgentClient:
    """Communicates with ONE remote agent (sync JSON‑RPC)."""

    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")
        self.agent_card: AgentCard | None = None

    # ---------------------------------------------------------
    # Discovery
    # ---------------------------------------------------------
    def fetch_agent_card(self) -> AgentCard:
        url = f"{self.base_url}/.well-known/agent.json"
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        self.agent_card = AgentCard(
            name=data["name"],
            url=self.base_url,
            version=data["version"],
            description=data.get("description", ""),
            capabilities=AgentCapabilities(**data["capabilities"]),
        )
        return self.agent_card

    # ---------------------------------------------------------
    # JSON‑RPC call (blocking)
    # ---------------------------------------------------------
    def send_task(self, task_id: str, session_id: str, message_text: str) -> dict:
        payload = {
            "jsonrpc": "2.0",
            "id": str(uuid.uuid4()),
            "method": "tasks/send",
            "params": {
                "id": task_id,
                "sessionId": session_id,
                "message": {
                    "role": "user",
                    "parts": [{"type": "text", "text": message_text}],
                },
            },
        }
        resp = requests.post(self.base_url, json=payload, timeout=60)
        resp.raise_for_status()
        return resp.json().get("result", {})


class HostAgent:
    """Stores *several* RemoteAgentClients and offers convenience wrappers."""

    def __init__(self, peer_urls: List[str]):
        self._clients: Dict[str, RemoteAgentClient] = {
            url: RemoteAgentClient(url) for url in peer_urls
        }

    # ---------------- Public helpers ----------------
    def initialize(self) -> None:
        for client in self._clients.values():
            try:
                client.fetch_agent_card()
            except Exception as exc:  # noqa: BLE001
                print(f"[WARN] Could not load AgentCard from {client.base_url}: {exc}")

    def list_agents_info(self) -> list[dict]:
        infos = []
        for c in self._clients.values():
            card = c.agent_card
            infos.append(
                {
                    "name": card.name if card else c.base_url,
                    "url": c.base_url,
                    "description": card.description if card else "(unavailable)",
                    "streaming": bool(card.capabilities.streaming) if card else False,
                }
            )
        return infos

    def send_task(self, agent_name: str, message: str) -> str:
        for c in self._clients.values():
            if c.agent_card and c.agent_card.name == agent_name:
                task_id = str(uuid.uuid4())
                session_id = "session‑p2p"
                try:
                    result = c.send_task(task_id, session_id, message)
                    state = (
                        result.get("status", {}).get("state") or TaskState.UNKNOWN
                    )
                    return f"state={state}, result={result}"
                except Exception as exc:  # noqa: BLE001
                    return f"Error while calling peer: {exc}"
        return f"No peer named '{agent_name}'."