# UMH External Boundary Law v1

**Phase:** 96.8A.1
**Status:** Active
**Layer:** UMH Substrate — Foundational Law

## The Law

**No external system, tool, SaaS, model, runtime, environment, human
approval process, or data source may be used directly by UMH.**

**Every external interaction must pass through an Adapter Package or
Adapter Family member that translates the external reality into UMH
primitives, contracts, capabilities, constraints, actions, outcomes,
and proof artifacts.**

**Adapters are the universal orchestration boundary.**

## What Is External to UMH

- SaaS tools (Google Workspace, Notion, Linear, Slack, etc.)
- APIs (REST, GraphQL, gRPC, etc.)
- CLIs (gcloud, aws, gh, etc.)
- MCP servers
- Local/remote runtimes (VPS, WSL, containers, etc.)
- Operating systems
- Tmux/shell sessions
- Local Windows GUI
- Browser sessions (Chrome, Firefox, etc.)
- Models/LLMs (Anthropic, OpenAI, Ollama, etc.)
- Humans/founder approvals
- Filesystems outside UMH-controlled contracts
- Databases (Neon, Postgres, SQLite, etc.)
- Emails/docs/messages
- Physical-world devices/sensors/actors

## What Is Internal to UMH

- Primitives
- Contracts
- Control plane policies
- Memory models
- Adapter registry metadata
- Work packet definitions
- Maturity gates
- Proof requirements
- Canonical/instance schemas

## Why This Law Exists

Without this law, UMH degrades into a collection of ad-hoc scripts
that directly call external systems. The adapter boundary ensures:

1. **Governance** — every external interaction has allowed/blocked actions
2. **Proof** — every external interaction produces auditable artifacts
3. **Maturity** — no immature external path executes in production
4. **Safety** — dangerous operations are blocked at the boundary
5. **Universality** — the same orchestration pattern works for APIs,
   GUIs, CLIs, models, databases, and human approvals

## Enforcement

- `core/adapter_engine/external_boundary_law.py` — evaluates compliance
- `core/adapter_engine/adapter_boundary_validator.py` — validates boundaries
- `core/adapter_engine/external_interaction_contract.py` — records interactions
- `core/environment_bridge/packet_validator.py` — enforces at packet level

## Module

`core/adapter_engine/external_boundary_law.py`
