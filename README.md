# A2A_bidirectional - Bidirectional task delegation using A2A
## Introduction
This repository provides a small and easy python example for letting agents communicate and delegate tasks bidirectionally via the agent-to-agent protocol (A2A).

In most of the A2A examples available on Github, there is one host agent which acts as client and delegates tasks to other agents (A2A servers).
In a complex multi-agent-scenario where several agents delegate tasks to other agents, this one-client-agent-setup is not sufficient.

__In this example, each agent acts as A2A client and A2A server at the same time. Each of the agents is capable of receiving tasks and delegating it to other agents.__

The host agent represents an agent registry. Each agent, which will be added to the setup as a new server, receives the host agent address as input argument during the launch.
It calls the host agent during the launch to get registered. Once it has been registered, other agents are able to call this new agent via the host agent without knowing the address of the newly added agent.

## Initial setup

```bash
pip install -e .
```
```bash
pip install -r requirements.txt
```

## Launch of the agents

```bash
python -m A2A_bidirectional.agents.host_agent.py
```
```bash
python A2A_bidirectional/agents/database_agent.py chat --peers http://localhost:8000
```
```bash
python A2A_bidirectional/agents/currency_agent.py chat --peers http://localhost:8000
```