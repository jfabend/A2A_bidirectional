# A2A_bidirectional - Bidirectional task delegation using A2A
## Introduction
This repository provides a small and easy A2A example written in Python where __each agent can be both client and server at the same time__.
__Each of the agents is capable of receiving tasks and delegating them to other agents__. Each agent can talk to any peer through the lightweight Agent‑to‑Agent (A2A) JSON‑RPC protocol, and register itself dynamically at run‑time.

The host agent represents an __agent registry__. Each agent, which will be added to the setup as a new server, receives the host agent address as input argument during the launch.
It calls the host agent during the launch to get registered. Once it has been registered, other agents are able to call this new agent via the host agent without knowing the address of the newly added agent.

At the moment, this repo leverages only LangGraph ReAct agents. But agents built with other frameworks or individual LangGraph workflows can be added easily as well (described below).

---

## ✨ Quick demo

```bash
# 1️⃣ Install – in a fresh venv
pip install -e .
pip install -r requirements.txt

# 2️⃣ Start the registry / router - !! Sometimes you need to add 'run' at the end and/or the .py
# runs at http://localhost:8000 by default
python -m A2A_bidirectional.agents.host_agent

# 3️⃣ Spin up some specialists
# One dummy agent which counts inventory in a database
python -m A2A_bidirectional.agents.database_agent chat --peers http://localhost:8000
# One dummy agent which converts currencies
python -m A2A_bidirectional.agents.currency_agent chat --peers http://localhost:8000
```
After the **DatabaseAgent** and **CurrencyAgent** have registered themselves with the **HostAgent** you can chat with any of them and they will seamlessly delegate work to the right peer.

The database agent has two tools:
1. Count inventory for a certain product (A dummy function which returns a random int)
2. Ask the host agent for help

The currency agent has two tools:
1. Convert a certain amount from currency A into currency B (A dummy function with 1.1 as fix conversion rate)
2. Ask the host agent for help

---

## 🖼️ How it works

### 1. Runtime interaction

```mermaid
sequenceDiagram
    autonumber
    participant User
    participant DatabaseAgent
    participant CurrencyAgent

    User->>DatabaseAgent: "How many SSDs do we have left? What are 10 Euros in US dollars?"
    DatabaseAgent->>DatabaseAgent: count_inventory("SSD")
    Note right of DatabaseAgent: returns "42"
    DatabaseAgent->>HostAgent: convert(10, "EUR", "USD")
    HostAgent->>CurrencyAgent: convert(10, "EUR", "USD")
    CurrencyAgent-->>HostAgent: "11 USD (demo rate)"
    HostAgent-->>DatabaseAgent: "11 USD (demo rate)"
    DatabaseAgent-->>User: "42 units on stock. And 10 Euros are 11 US dollars."
```

The following way would also be possible (but only via API call towards the host agent. Cli chat has not been implemented here.):
```mermaid
sequenceDiagram
    autonumber
    participant User
    participant HostAgent
    participant DatabaseAgent
    participant CurrencyAgent

    User->>HostAgent: "How many SSDs do we have left? What are 10 Euros in US dollars?"
    HostAgent->>DatabaseAgent: count_inventory("SSD")
    DatabaseAgent-->>HostAgent: "42"
    HostAgent->>CurrencyAgent: convert(10, "EUR", "USD")
    CurrencyAgent-->>HostAgent: "11 USD (demo rate)"
    HostAgent-->>User: "42 units on stock. And 10 Euros are 11 US dollars."
```

### 2. Dynamic agent registration (runs automatically)

```mermaid
sequenceDiagram
    autonumber
    participant NewAgent
    participant HostAgent

    NewAgent->>HostAgent: POST /register (AgentCard)
    HostAgent-->>NewAgent: 201 Created
    Note right of HostAgent: Card is stored in registry and <br/> exposed via list_remote_agents()
```

*Any agent can call `register()` **once** on start‑up to make itself discoverable by all other peers.*

---

## 🧩 Repository layout

Currently, all the agents are LangGraph ReAct agents. They can receive multiple tasks within one query, reason which tool to use for each task and delegate single tasks to other agents.

| Path | What’s inside |
|------|---------------|
| `A2A_bidirectional/agents/` | Ready‑to‑run example agents: **host_agent.py**, **database_agent.py**, **currency_agent.py** |
| `A2A_bidirectional/core/` | `react_agent_factory.py` – creates a LangGraph *ReAct* agent and wires in peer‑communication tools |
| `A2A_bidirectional/server/` | Minimal FastAPI JSON‑RPC server exposing an agent under `/.well‑known/agent.json` and `/` |
| `A2A_bidirectional/utils/` | Utility modules: <br/>• `remote_client.py` – sync JSON‑RPC client, registry handling <br/>• `tool_factories.py` – LangChain Tool wrappers <br/>• `helpers.py` – helper for `serve_and_register()` |
| `requirements.txt` | Reproducible dependency lock‑file |

---

## ➕ Adding a new agent in *3 steps*

Currently, all the agents are LangGraph ReAct agents. In the section roadmap, I explain how other agents can be added.

1. **Create your internal skills** – plain Python functions decorated with `@tool` (from *LangChain*).
2. **Wrap them in a ReAct agent** using `build_react_agent()` and provide the extra routing rules that explain **when to delegate**.
3. **Expose & register** the agent:
   ```python
   app  = create_app(react_agent, card) # expects an invokeable, compiled agent
   serve_and_register(app, card, port=8003, host_url="http://localhost:8000")
   ```
   The helper automatically starts the FastAPI server **and** POSTs the `AgentCard` to the HostAgent.

That’s it – all other peers can now call your agent via `send_task(<YourAgentName>, message)` without knowing its IP/port.

---

## 🚀 Why use this framework?

| Benefit | Details |
|---------|---------|
| **Scalable decentral architecture** | Any agent can delegate to any other, avoiding single‑point bottlenecks. |
| **Plug‑and‑play discovery** | Agents self‑register; new capabilities become available at run‑time with zero config changes. |
| **No vendor lock‑in** | Pure Python, standard JSON‑RPC over HTTP; replace LLM/agent implementation freely. |
| **Docker‑ready** | Every example agent is a standalone Python entry‑point → trivial to wrap in a tiny Docker image or deploy as a micro‑service. |
| **LangGraph + ReAct out‑of‑the‑box** | Combines structured tool‑use reasoning with memory, concurrency & streaming if you enable it. |
| **Streamlined DX** | Less than 600 LOC in total, readable and heavily commented code, poetry/flit project metadata. |
| **Observability hooks** | Agent cards expose capabilities (`streaming`, `stateTransitionHistory`) – wire them into tracing/storage back‑ends as needed. |

---

## 🛠️ Configuration

| Variable | Purpose | Default |
|----------|---------|---------|
| `OPENAI_API_KEY` | Needed if you switch to OpenAI models in `react_agent_factory.py` | *none* |
| `MODEL_NAME` | Override the chat model (`gpt‑4o`, `gemma‑2‑it`, …) | `gpt‑4o` |
| `HOST_URL` | URL where the HostAgent is reachable | `http://localhost:8000` |

---

## 📋 Roadmap

- [ ] Make it easier to add new agents (especially based on other frameworks - see below)
- [ ] ✨ Add `docker-compose.yml` with three example services

Currently, all the agents are LangGraph ReAct agents. The _call_agent function in server/a2a_server.py defines ways how agents can be called.
It only contains the invoke call for LangGraph at the moment. But calls for crew.ai, Autogen and all the other frameworks can be added here.
You can then add a framework field to the AgentCard class in utils/remote_client.py where one of these frameworks can be entered.
The _call_agent function could then select the right agent call depending on the framework used of each agent.