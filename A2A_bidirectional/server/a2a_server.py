"""Very small FastAPI wrapper exposing the agent via A2A."""
from __future__ import annotations

import asyncio
import uuid
from uuid import uuid4
from typing import Any, Dict

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse

from A2A_bidirectional.utils.remote_client import AgentCard, TaskState

__all__ = ["create_app", "start_server"]


async def _call_agent(agent, user_msg: str, thread_id: str | None = None) -> str:
    thread_id = thread_id or str(uuid4())
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(
        None,
        lambda: agent.invoke(
            {"messages": [{"role": "user", "content": user_msg}]},
            config={"configurable": {"thread_id": thread_id}},
        ),
    )


def create_app(agent, agent_card: AgentCard) -> FastAPI:
    """Expects an invokeable agent and an agent card as inputs."""
    
    app = FastAPI(title=agent_card.name)

    @app.get("/.well-known/agent.json")
    async def agent_card_endpoint():  # noqa: D401
        return JSONResponse(agent_card.model_dump())

    @app.post("/")
    async def json_rpc(body: Dict[str, Any]):  # noqa: ANN401
        try:
            method = body["method"]
        except KeyError as exc:  # noqa: B904
            raise HTTPException(status_code=400, detail="Missing method") from exc

        if method != "tasks/send":
            raise HTTPException(status_code=400, detail="Unsupported method")

        params = body["params"]
        text = params["message"]["parts"][0]["text"]
        session_id = params.get("sessionId") or str(uuid.uuid4())
        _ = session_id  # left here in case you want session memories

        reply = await _call_agent(agent, text, session_id)

        # Normalise reply → we always send COMPLETED for demo
        result = {
            "id": params["id"],
            "status": {"state": TaskState.COMPLETED},
            "output": str(reply),
        }
        return JSONResponse({"jsonrpc": "2.0", "result": result, "id": body["id"]})

    return app


def start_server(app: FastAPI, port: int = 8000):
    import uvicorn  # local import to keep deps optional

    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")