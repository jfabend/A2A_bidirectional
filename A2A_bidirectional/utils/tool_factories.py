"""Build LangChain Tool wrappers around HostAgent helpers."""
from __future__ import annotations

from langchain_core.tools import tool
from A2A_bidirectional.utils.remote_client import HostAgent

__all__ = ["make_list_agents_tool", "make_send_task_tool"]


def make_list_agents_tool(host_agent: HostAgent):
    @tool
    def list_remote_agents() -> list:
        """Return meta‑info of all known peers (name, url, description)."""
        return host_agent.list_agents_info()

    return list_remote_agents


def make_send_task_tool(host_agent: HostAgent):
    @tool
    def send_task(agent_name: str, message: str) -> str:
        """Forward *message* to *agent_name* and return the raw peer response."""
        return host_agent.send_task(agent_name, message)

    return send_task