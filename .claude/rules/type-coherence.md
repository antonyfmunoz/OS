---
globs: ["**/*.py"]
---

# Type Coherence Law

Before defining ANY new Enum, BaseModel, or @dataclass class:

1. Check `substrate/canonical_types.py` — it registers ~1040 canonical types
2. If the name exists there → IMPORT it, never redefine
3. If creating a genuinely new type → add it to `canonical_types.py` after defining

Never create a parallel type system. Every divergence costs a full reconvergence audit.

Canonical locations:
- `substrate/types.py` — general domain types (SignalEnvelope, RiskClass, CapabilityStatus, etc.)
- `substrate/contracts/agent_types.py` — TaskType, ModelProvider
- `substrate/execution/runtime/capability_router.py` — Capability (28 job capabilities)
- `substrate/execution/runtime/worker_runtime_contracts.py` — EnvironmentType, AuthorityDomain
- `nodes/environments/work_packet.py` — EnvironmentEnvironmentPacketRiskLevel, EnvironmentEnvironmentPacketStatus, EnvironmentWorkPacket
- `substrate/organism/` — RuntimeClass, WorkUnitType, WorkcellRole, etc.

Legacy homonym exemptions live in `LEGACY_DUPLICATES_META` (owner/sunset/rationale
required per entry) and must SHRINK, never grow. The list is fail-closed audited.

Enforcement (`scripts/check_type_divergence.py`):
- pre-commit hook: blocks NEW divergence in staged files.
- `--registry-audit`: fail-closed truthfulness check — every registry entry
  resolves to a real symbol, no duplicate keys, every exemption resolves and
  carries valid metadata. Run this in CI.
- `--all`: full-tree name-shadow scan (worktree-aware). The pre-existing debt is
  enumerated in `data/audits/2026-07-04_type_divergence_ledger.md` and capped by
  `tests/test_type_divergence.py::test_full_codebase_scan_no_growth` (may only
  shrink).
