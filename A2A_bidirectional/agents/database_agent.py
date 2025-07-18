"""Database Agent – solves inventory tasks, delegates anything else to HostAgent."""
from __future__ import annotations

import random
import typer
from langchain_core.tools import tool

from A2A_bidirectional.utils.remote_client import HostAgent, AgentCard, AgentCapabilities
from A2A_bidirectional.core.react_agent_factory import build_react_agent
from A2A_bidirectional.server.a2a_server import create_app, start_server

# ------------------------------------------------------------------
# Internal skill
# ------------------------------------------------------------------


@tool
def count_products(product_type: str) -> str:
    """Return a *fake* number for demo purposes."""
    return f"We currently have {random.randint(1, 500)} items of {product_type}."


cli = typer.Typer(help="Run the Database Agent")


@cli.command()
def run(
    name: str = "DatabaseAgent",
    port: int = 8001,
    peers: list[str] = typer.Option([], help="Comma separated list of peer URLs"),
):
    host_agent = HostAgent(peers)
    host_agent.initialize()

    extra_instructions = """
    • If the user asks for stock levels or product counts, use your internal count_products() tool.
    • Otherwise, delegate to HostAgent using send_task("HostAgent", original_question).
    """

    react_agent = build_react_agent(name, [count_products], host_agent, extra_instructions)

    card = AgentCard(
        name=name,
        url=f"http://localhost:{port}",
        description="Answers inventory questions; delegates unknown questions to HostAgent.",
        capabilities=AgentCapabilities(streaming=False),
    )

    app = create_app(react_agent, card)
    start_server(app, port)


if __name__ == "__main__":
    cli()