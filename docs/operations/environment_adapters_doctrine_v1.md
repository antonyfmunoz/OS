# Environment Adapters Doctrine v1

**Status:** ACTIVE
**Layer:** Adapter Boundary Layer
**Scope:** Environment subsystem

---

## Doctrine

VPS, WSL, tmux, Windows GUI, Chrome, and the local worker bridge are **external environments/surfaces**. They require adapter boundaries. They are not part of UMH's internal intelligence layer.

---

## Classification

| System | Classification |
|--------|---------------|
| VPS (100.77.233.50) | Environment — always-on orchestrator host |
| Local WSL | Environment — Linux execution on Windows |
| Windows GUI | Environment — visual desktop surface |
| Chrome Browser | Environment/Surface — browser automation target |
| tmux | Execution Surface — persistent terminal session |
| Local Worker Bridge | Environment Adapter / bridge boundary |
| Local Worker | Worker Runtime — process that performs execution |
| SSH tunnel | Transport path (part of bridge) |
| Tailscale | Network adapter (part of bridge) |

---

## Key Distinctions

### Local Worker is a Worker Runtime

The local worker is **not** intelligence. It is a worker runtime — a process/session that performs execution on behalf of the Execution Plane. It claims work packets, runs them, and returns results.

### tmux is an Execution Surface

tmux provides a persistent terminal session where commands execute. It is not an adapter — it is a surface managed by an adapter. The tmux surface model (`core/environment_bridge/tmux_surface.py`) constructs commands but does not independently execute.

### The Bridge is an Environment Adapter

The VPS ↔ Local Worker Bridge (`core/environment_bridge/vps_local_bridge.py`) is an Environment Adapter / bridge boundary. It:
- Connects the VPS to local environments
- Translates work packets into dispatchable instructions
- Validates that packets meet governance requirements
- Does NOT independently execute

### Windows GUI and Chrome are Explicit Environments

They require:
- Environment Adapter boundary
- Worker Runtime binding
- Mastery requirements (Computer Use mastery)
- Proof artifact requirements
- Governance (17 CU blocked actions)

### Founder Confirmation is a Human Approval Adapter Path

The founder confirmation gate is mediated by a Human Approval Adapter. It is not a direct bypass — it is a governed approval path with its own adapter boundary.

---

## Relationship to Phase 96.8A

Phase 96.8A built the VPS ↔ Local Worker Bridge as Environment Adapter infrastructure:
- Work Packet contract (governed executable instruction)
- Packet Validator (governance enforcement)
- Local Pull Protocol (transport mechanism)
- Result Ingestion (proof normalization)
- Heartbeat (worker liveness)
- tmux Surface (execution surface model)
- VPS-Local Bridge (status evaluation)

All of this is Adapter Boundary Layer + Execution Plane infrastructure.
