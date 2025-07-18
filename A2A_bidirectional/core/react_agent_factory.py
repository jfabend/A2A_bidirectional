"""Factory producing a ReAct‑pattern LangGraph agent with peer tools and custom instructions."""
from __future__ import annotations

from typing import List

from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import create_react_agent

from A2A_bidirectional.utils.tool_factories import make_list_agents_tool, make_send_task_tool
from A2A_bidirectional.utils.remote_client import HostAgent

from dotenv import load_dotenv
load_dotenv()

__all__ = ["build_react_agent"]


def build_react_agent(
    agent_name: str,
    internal_tools: List,  # already @tool‑decorated callables
    host_agent: HostAgent,
    extra_instructions: str | None = None,
):
    """Return a LangGraph ReAct agent whose prompt already knows how to route.

    *internal_tools* – list of @tool functions specific to this agent.
    *host_agent* – gives access to peer communication tools.
    *extra_instructions* – plain‑text section to specialise tool‑routing logic
      (e.g. "If question is about currency, use convert(); otherwise delegate...").
    """
    llm = ChatOpenAI(model="gpt-4o")
    memory = MemorySaver()

    # peer tools
    list_peers = make_list_agents_tool(host_agent)
    send_task = make_send_task_tool(host_agent)

    base_prompt = f"""
    You are **{agent_name}**, an autonomous ReAct agent.

    Tools available:
      • INTERNAL TOOLS – your proprietary skills listed in internal_tools.
      • PEER TOOLS – provided automatically:
          – list_remote_agents(): enumerate known peers.
          – send_task(agent_name, msg): delegate work to a peer and return its raw answer.

    Always think step‑by‑step. If you can satisfy the query with an INTERNAL TOOL, do so.
    Otherwise delegate with send_task.
    """

    if extra_instructions:
        base_prompt += extra_instructions.strip()

    all_tools = internal_tools + [list_peers, send_task]
    return create_react_agent(llm, all_tools, checkpointer=memory, prompt=base_prompt)