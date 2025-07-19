"""CurrencyAgent – converts money or delegates to HostAgent."""
from __future__ import annotations

import typer, requests, json
from langchain_core.messages import AIMessage
from langchain_core.tools import tool

from A2A_bidirectional.utils.remote_client import HostAgent
from A2A_bidirectional.core.react_agent_factory import build_react_agent
from A2A_bidirectional.server.a2a_server import create_app, start_server
from A2A_bidirectional.utils.remote_client import AgentCard, AgentCapabilities

def _make_router_tools(host_agent: HostAgent, self_card: AgentCard):
    @tool
    def convert(amount: float, from_: str, to: str) -> str:  # noqa: A002
        """Naïve conversion using a fixed demo rate."""
        rate = 1.1
        return f"{amount} {from_} = {amount * rate:.2f} {to} (demo rate)"

    @tool
    def count_inventory(product_type: str) -> str:
        """Delegate currency conversion to CurrencyAgent."""
        return host_agent.send_task(
            "DatabaseAgent", f"Count inventory for product type {product_type}"
        )
    
    @tool
    def register(host_url: str = "http://localhost:8000") -> str:
        """
        Tell HostAgent where I am.  Needs to be called only once.
        """
        requests.post(f"{host_url}/register", json=self_card.model_dump(), timeout=5)
        return "✅ registered with HostAgent"
 
    return [register, convert, count_inventory]


EXTRA_INSTRUCTIONS = """
• If the question is a currency conversion, use convert().
• Otherwise delegate to HostAgent via send_task("HostAgent", original_question).
"""

cli = typer.Typer(help="Run the CurrencyAgent")


@cli.command()
def chat(
    name: str = "CurrencyAgent",
    port: int = 8002,
    peers: list[str] = typer.Option(
        [], help="Peer URLs (typically just the HostAgent, e.g. http://localhost:8000)"
    ),
):
    host_agent = HostAgent(peers)
    host_agent.initialize()

    card = AgentCard(
        name=name,
        url=f"http://localhost:{port}",
        description="Converts currencies; delegates unknown questions to HostAgent.",
        capabilities=AgentCapabilities(streaming=False),
    )

    react_agent = build_react_agent(name, _make_router_tools(host_agent, card), host_agent, EXTRA_INSTRUCTIONS)

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
        reply = (
            next((m.content for m in reversed(raw["messages"]) if isinstance(m, AIMessage)), None)
            if isinstance(raw, dict) and "messages" in raw
            else raw
        )
        typer.echo(f"{name}: {reply}")


@cli.command()
def run(
    name: str = "CurrencyAgent",
    port: int = 8002,
    peers: list[str] = typer.Option([], help="Peer URLs"),
):
    host_agent = HostAgent(peers)
    host_agent.initialize()

    card = AgentCard(
        name=name,
        url=f"http://localhost:{port}",
        description="Converts currencies; delegates unknown questions to HostAgent.",
        capabilities=AgentCapabilities(streaming=False),
    )

    react_agent = build_react_agent(name, _make_router_tools(host_agent, card), host_agent, EXTRA_INSTRUCTIONS)

    start_server(create_app(react_agent, card), port)


if __name__ == "__main__":
    cli()
