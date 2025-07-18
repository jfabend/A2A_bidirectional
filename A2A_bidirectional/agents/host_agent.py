from __future__ import annotations

import typer
from langchain_core.tools import tool

from A2A_bidirectional.utils.remote_client import HostAgent, AgentCard, AgentCapabilities
from A2A_bidirectional.core.react_agent_factory import build_react_agent
from A2A_bidirectional.server.a2a_server import create_app, start_server

cli = typer.Typer(help="Run the Host Agent.")


# ------------------------------------------------------------------
# Dynamic wrapper tools that *delegate* to specialised peers
# ------------------------------------------------------------------

def _make_router_tools(host_agent: HostAgent):
    @tool
    def count_inventory(product_type: str) -> str:
        """Delegate inventory count to DatabaseAgent."""
        prompt = f"How many {product_type} do we have in stock?"
        return host_agent.send_task("DatabaseAgent", prompt)

    @tool
    def convert(amount: float, from_: str, to: str) -> str:  # noqa: A002
        """Delegate currency conversion to CurrencyAgent."""
        prompt = f"Convert {amount} {from_} to {to}"
        return host_agent.send_task("CurrencyAgent", prompt)

    return [count_inventory, convert]


@cli.command()
def run(
    name: str = "HostAgent",
    port: int = 8000,
    peers: list[str] = typer.Option([], help="Comma separated list of peer URLs"),
):
    # --------------------------------------------------------------
    # 1. Discover peers
    # --------------------------------------------------------------
    host_agent = HostAgent(peers)
    host_agent.initialize()

    # --------------------------------------------------------------
    # 2. Build ReAct agent with *delegation* wrappers
    # --------------------------------------------------------------
    internal_tools = _make_router_tools(host_agent)

    extra_instructions = """
    • For inventory count queries use count_inventory() which routes to DatabaseAgent.
    • For currency conversion queries use convert() which routes to CurrencyAgent.
    • For any other topic reply politely that you are not the right specialist.
    """

    react_agent = build_react_agent(name, internal_tools, host_agent, extra_instructions)

    # --------------------------------------------------------------
    # 3. Expose via FastAPI A2A server
    # --------------------------------------------------------------
    card = AgentCard(
        name=name,
        url=f"http://localhost:{port}",
        description="Delegates inventory & FX tasks to specialised peers.",
        capabilities=AgentCapabilities(streaming=False),
    )

    app = create_app(react_agent, card)
    start_server(app, port)


if __name__ == "__main__":
    cli()