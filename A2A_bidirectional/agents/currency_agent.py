from __future__ import annotations

import typer
from langchain_core.tools import tool

from A2A_bidirectional.utils.remote_client import HostAgent, AgentCard, AgentCapabilities
from A2A_bidirectional.core.react_agent_factory import build_react_agent
from A2A_bidirectional.server.a2a_server import create_app, start_server

# ------------------------------------------------------------------
# Internal skill
# ------------------------------------------------------------------


@tool
def convert(amount: float, from_: str, to: str) -> str:  # noqa: A002
    """Naive conversion with fake rate."""
    fake_rate = 1.1  # static demo rate
    return f"{amount} {from_} = {amount * fake_rate:.2f} {to} (demo rate)"


cli = typer.Typer(help="Run the Currency Agent")


@cli.command()
def run(
    name: str = "CurrencyAgent",
    port: int = 8002,
    peers: list[str] = typer.Option([], help="Comma separated list of peer URLs"),
):
    host_agent = HostAgent(peers)
    host_agent.initialize()

    extra_instructions = """
    • If the question is clearly a money conversion, use your internal convert() tool.
    • Otherwise delegate to HostAgent by send_task("HostAgent", original_question).
    """

    react_agent = build_react_agent(name, [convert], host_agent, extra_instructions)

    card = AgentCard(
        name=name,
        url=f"http://localhost:{port}",
        description="Converts currencies; delegates unknown questions to HostAgent.",
        capabilities=AgentCapabilities(streaming=False),
    )

    app = create_app(react_agent, card)
    start_server(app, port)


if __name__ == "__main__":
    cli()