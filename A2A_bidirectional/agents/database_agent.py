from __future__ import annotations

import typer, random, requests, os
from langchain_core.messages import AIMessage
from langchain_core.tools import tool

from A2A_bidirectional.utils.remote_client import HostAgent
from A2A_bidirectional.core.react_agent_factory import build_react_agent
from A2A_bidirectional.server.a2a_server import create_app, start_server
from A2A_bidirectional.utils.remote_client import AgentCard, AgentCapabilities


###############################################################################
# Helpers – tools that DELEGATE to remote peers
###############################################################################
def _make_router_tools(host_agent: HostAgent, self_card: AgentCard):
    @tool
    def count_inventory(product_type: str) -> str:
        """Delegate inventory count to DatabaseAgent."""
        return str(random.randint(0,9))

    @tool
    def convert(amount: float, from_: str, to: str) -> str:  # noqa: A002
        """Delegate currency conversion to CurrencyAgent."""
        return host_agent.send_task(
            "CurrencyAgent", f"Convert {amount} {from_} to {to}"
        )
    
    @tool
    def register(host_url: str = "http://localhost:8000") -> str:
        """
        Tell HostAgent where I am.  Needs to be called only once.
        """
        requests.post(f"{host_url}/register", json=self_card.model_dump(), timeout=5)
        return "✅ registered with HostAgent"

    return [register, count_inventory, convert]


###############################################################################
# Typer CLI
###############################################################################
cli = typer.Typer(help="Run the HostAgent")

# ----- 1) NEW: interactive chat ------------------------------------------------
@cli.command()
def chat(
    name: str = "DatabaseAgent",
    port: int = 8001,
    peers: list[str] = typer.Option(
        [], help="Comma‑separated list of peer URLs (e.g. http://localhost:8001)"
    ),
):
    """Start an interactive REPL talking to the HostAgent."""
    # 1. discover peers
    host_agent = HostAgent(peers)
    host_agent.initialize()

    card = AgentCard(
        name=name,
        url=f"http://localhost:{port}",
        description="Provides information about inventory",
        capabilities=AgentCapabilities(streaming=False),
    )

    # 2. build ReAct agent with delegation wrappers
    react_agent = build_react_agent(
        name,
        _make_router_tools(host_agent, card),
        host_agent,
        extra_instructions="""
• For inventory questions call count_inventory().
• For currency questions  call convert().
• Otherwise answer politely that you’re not the right specialist.
""",
    )

    typer.echo(f"{name} ready. Type 'exit' to quit.")
    while True:
        user_msg = typer.prompt("\nUser")
        if user_msg.lower() in {"exit", "quit", "bye"}:
            typer.echo("Good‑bye!")
            break

        raw = react_agent.invoke(
            {"messages": [{"role": "user", "content": user_msg}]},
            config={"configurable": {"thread_id": "cli-session"}},
        )

        # pick the last AIMessage if LangGraph returned a list
        reply = (
            next((m.content for m in reversed(raw["messages"]) if isinstance(m, AIMessage)), None)
            if isinstance(raw, dict) and "messages" in raw
            else raw
        )
        typer.echo(f"{name}: {reply}")


# ----- 2) OLD: still possible to expose as HTTP (renamed) ---------------------
@cli.command()
def run(
    name: str = "DatabaseAgent",
    port: int = 8001,
    peers: list[str] = typer.Option([], help="Comma‑separated list of peer URLs"),
):
    host_agent = HostAgent(peers)
    host_agent.initialize()

    card = AgentCard(
        name=name,
        url=f"http://localhost:{port}",
        description="Provides information about inventory",
        capabilities=AgentCapabilities(streaming=False),
    )

    react_agent = build_react_agent(
        name, _make_router_tools(host_agent, card), host_agent, extra_instructions=""
    )

    start_server(create_app(react_agent, card), port)


if __name__ == "__main__":
    cli()
