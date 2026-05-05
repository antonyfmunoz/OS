# Adapter as Universal Orchestration Boundary v1

**Phase:** 96.8A.1
**Status:** Active
**Layer:** UMH Substrate

## Core Principle

Adapters are not only API integrations.

Adapters are the universal translation boundary between UMH's internal
model and all external reality. Every external system — whether a SaaS
API, a local GUI, a CLI tool, an AI model, a human approval process,
or a physical-world sensor — must be accessed through an adapter.

## What Adapters Translate

### External Reality → UMH

Adapters translate external reality into:
- UMH primitives
- State
- Change
- Constraints
- Resources
- Time
- Signals
- Feedback
- Goals
- Actions
- Outcomes
- Proof artifacts

### UMH Intent → External Action

Adapters translate UMH intent into:
- Work packets
- Governed actions
- External API calls
- CLI commands
- GUI actions
- Human approval requests
- Model calls
- Data ingestion operations

## Adapter Engine Scope

The Adapter Engine is the complete collection of adapter categories:

| Category | Examples |
|----------|----------|
| Tool | Claude Code, Codex |
| SaaS | Google Workspace, Notion, Linear |
| API | REST endpoints, GraphQL, gRPC |
| CLI | gcloud, aws, gh, npm |
| MCP | MCP servers and tools |
| Environment | VPS, WSL, tmux, Windows GUI |
| Runtime | Docker, Lambda, containers |
| Model | Anthropic, OpenAI, Ollama |
| Human Approval | Founder confirmation, team approval |
| Data Source | Filesystems, databases |
| Browser | Chrome, browser automation |
| Computer Use | GUI observation, accessibility tree |
| Physical World | Sensors, actuators, devices |

## Why Not Just APIs

If adapters were only API integrations, then:
- Local GUI execution would bypass governance
- Human approvals would bypass proof requirements
- Model calls would bypass maturity gates
- Filesystem access would bypass the boundary law
- Environment transitions would have no contracts

The External Boundary Law prevents this by requiring every external
interaction — regardless of type — to pass through an adapter.

## Requirements for Every Adapter

Per the External Boundary Law, every adapter must have:
1. Adapter identity (package or family)
2. Capability contract
3. Governance policy
4. Proof requirements
5. Maturity gate
6. Tool Mastery requirement (for tool-based categories)
7. Result ingestion path

## Module

`core/adapter_engine/adapter_taxonomy.py`
