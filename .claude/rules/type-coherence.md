---
globs: ["**/*.py"]
---

# Type Coherence Law

Before defining ANY new Enum, BaseModel, or @dataclass class:

1. Check `substrate/canonical_types.py` — it registers ~80 canonical types
2. If the name exists there → IMPORT it, never redefine
3. If creating a genuinely new type → add it to `canonical_types.py` after defining

Never create a parallel type system. Every divergence costs a full reconvergence audit.

Canonical locations:
- `substrate/types.py` — general domain types (SignalEnvelope, RiskClass, CapabilityStatus, etc.)
- `substrate/contracts/agent_types.py` — TaskType, ModelProvider
- `substrate/execution/runtime/capability_router.py` — Capability (28 job capabilities)
- `substrate/execution/runtime/worker_runtime_contracts.py` — EnvironmentType, AuthorityDomain
- `nodes/environments/work_packet.py` — WorkPacketRiskLevel, WorkPacketStatus
- `substrate/organism/` — RuntimeClass, WorkUnitType, WorkcellRole, etc.

Pre-commit hook enforces this: `scripts/check_type_divergence.py`
