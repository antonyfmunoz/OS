# Discovery Report — Session C: Governance + Execution + Adapters

**Date:** 2026-05-18
**Worktree:** jarvis-governance
**Branch:** worktree-jarvis-governance

## What Existed Before This Session

### Main Branch (services/)
- No `services/jarvis/` directory on main branch
- Existing services: discord_bot, bridge_health, cost_tracker, heartbeat, etc.
- No governance, execution, or adapter modules anywhere in `/opt/OS/services/`

### Parallel Worktree: jarvis-layer0
- Complete **protocol pack** (v1) with 13 protocol modules:
  - governance.py — GovernanceDecision, GovernanceVerdict, GovernanceRequest, RiskLevel
  - work_packet.py — WorkPacket, WorkPacketStatus, WorkPacketPriority
  - execution_result.py — ExecutionResult, ExecutionOutcome
  - proof.py — Proof, ProofType, ProofStatus
  - adapter.py — AdapterType, AdapterConfig, AdapterRequest, AdapterResponse
  - trace.py — Trace, TraceEvent, TraceEventType
  - capability.py — Capability, CapabilityCategory, CapabilityInvocation
  - signal.py, interpretation.py, decomposition.py, environment.py,
    memory_candidate.py, outcome.py
- **Foundation layer** (identity, laws, primitives, epistemology, perspective, possibility)
- **Control plane skeleton** (app, event_bus, invariants, router, runtime)

### Other Relevant Patterns
- `core/environment_bridge/work_packet.py` — older WorkPacket model in core layer (different schema)
- `runtime/authority_engine.py` — does NOT exist (referenced in wiki, never built)
- No safe-root or protected-file conventions existed prior

### Tmux Sessions Discovered
- dex_builder_main, dex_main, jarvis, umh_core, umh_tests, umh_worker
- All active, none should be killed

## Integration Points

### Protocol Pack (Layer 0 → This Layer)
This session's modules import directly from the Layer 0 protocol pack:
- `protocols/governance.py` → governance/policy_engine.py, execution/proof_generator.py
- `protocols/work_packet.py` → execution/executor.py, execution/queue.py
- `protocols/execution_result.py` → execution/executor.py, execution/proof_generator.py
- `protocols/proof.py` → execution/proof_generator.py

The protocols were copied from the jarvis-layer0 worktree into this worktree
to ensure import paths work. When branches merge, the protocols must come from
one canonical source.

### Adapter Registration
Adapters implement `AdapterProtocol` (defined in executor.py) — a structural
Protocol (duck-typed). Any object with `name`, `execute()`, and `classify_risk()`
methods satisfies it. This avoids coupling adapters to a specific base class,
though `BaseAdapter` provides deny-rule infrastructure for convenience.
