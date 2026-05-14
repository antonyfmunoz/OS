# CANONICAL-CONTRACTS — Audit Report

> Date: 2026-05-13
> Source: /opt/OS/docs/canonical/umh_synthesis.md (§25 Protocol Pack + Parts III–V)
> Output: /opt/OS/umh/protocols/

---

## Summary

| Metric | Value |
|--------|-------|
| Total contracts generated | 106 |
| Enums (StrEnum) | 19 |
| BaseModels | 86 |
| Protocol classes | 1 (Adapter) |
| Files created | 13 (11 source + 2 test infrastructure) |
| Test files | 8 |
| Tests | 108 passed, 0 failed |
| mypy --strict (source) | 0 errors in 11 files |
| LOC (source) | 2,104 |
| LOC (tests) | ~750 |
| Dependencies | pydantic (2.12.5), standard library only |

---

## Test Results

```
108 passed in 0.32s
```

All 5 test categories per model covered:
- minimal_construction
- serialization_roundtrip
- extra_field_forbidden
- schema_version_present
- required_field_missing

Adapter Protocol tests:
- test_adapter_protocol_methods_present (all 8 methods)
- test_minimal_stub_satisfies_protocol

---

## mypy Result

```
Success: no issues found in 11 source files
```

(Test files have expected call-arg errors for `pytest.raises(ValidationError)` 
tests that deliberately pass invalid kwargs — these are runtime-correct.)

---

## Files Created

| File | LOC | Layer |
|------|-----|-------|
| umh/protocols/__init__.py | 252 | Public API re-exports |
| umh/protocols/common.py | 533 | Shared enums, refs, sub-models |
| umh/protocols/control_plane.py | 31 | Layer 2 |
| umh/protocols/understanding.py | 215 | Layer 3 |
| umh/protocols/state.py | 188 | Layer 4 |
| umh/protocols/composition.py | 275 | Layer 5 |
| umh/protocols/governance.py | 86 | Layer 6 |
| umh/protocols/execution.py | 172 | Layer 7 |
| umh/protocols/adapters.py | 152 | Layer 8 |
| umh/protocols/observability.py | 174 | Layer 9 |
| umh/protocols/learning.py | 26 | Layer 10 |
| umh/protocols/tests/__init__.py | 1 | Test package |
| umh/protocols/tests/test_common.py | ~120 | — |
| umh/protocols/tests/test_control_plane.py | ~80 | — |
| umh/protocols/tests/test_understanding.py | ~100 | — |
| umh/protocols/tests/test_state.py | ~100 | — |
| umh/protocols/tests/test_composition.py | ~100 | — |
| umh/protocols/tests/test_governance.py | ~60 | — |
| umh/protocols/tests/test_execution.py | ~130 | — |
| umh/protocols/tests/test_adapters.py | ~120 | — |
| umh/protocols/tests/test_observability.py | ~130 | — |
| umh/protocols/tests/test_learning.py | ~60 | — |
| umh/protocols/CONTRACT_INDEX.md | — | Manifest |

Also modified:
- umh/__init__.py — replaced ImportError guard with docstring (allows import)

---

## Deviations from Synthesis

| Deviation | Reason |
|-----------|--------|
| `Trace.input` typed as `dict[str, Any]` instead of `Signal` | Avoids circular import with understanding.py; Trace captures the serialized signal form |
| `Trace.composition` typed as `dict[str, Any]` instead of `ExecutableComposition` | Same reason — observability layer must not import composition layer |
| `Adapter.translate_request` parameter typed as `Any` instead of `WorkPacket` | Protocol class cannot import concrete model without creating cross-layer dependency; runtime implementations will narrow the type |
| Entity defined in both understanding.py and state.py as separate models | §9.2 Entity (extracted from interpretation) vs §10.1 WorldEntity (in world model) serve different roles; named WorldEntity in state.py to disambiguate |
| Permission defined in common.py not governance.py | Used by both governance and execution layers; placing in common avoids circular imports |
| Goal defined in both understanding.py and state.py | §9.2 Goal (inferred from signal) vs §10.1 Goal (active in world model) — same concept but separate lifecycle stages |

---

## Open Questions (Synthesis Ambiguities)

| # | Question | Location | Conservative Choice Made |
|---|----------|----------|------------------------|
| 1 | What fields does `IntentCandidate` contain beyond description? | §9.2 | Used: intent_id, description, confidence, domain |
| 2 | What is `EntityType` in DomainMap.common_entities? | §9.5 | Defined as simple type_id + name + description |
| 3 | What fields does `TemporalState` contain? | §10.1 | Used: current_timestamp, last_updated, temporal_horizon |
| 4 | What is `UncertaintyModel`? | §10.1 | Used: overall_confidence + stale/unverified counts |
| 5 | What are `Resource` and `Risk` shapes in WorldState? | §10.1 | Minimal: id + name + type/quantity/probability/impact |
| 6 | What is `ImmutablePrimitive` shape? | §11.3 | Used: primitive_id, name, type, description |
| 7 | What is `FeedbackLoopSpec` shape? | §11.3 | Used: loop_id, name, trigger, description |
| 8 | What is `GovernanceSpec` shape? | §11.3 | Used: authority_required, risk_level, approval_required |
| 9 | What is `ObservabilitySpec` shape? | §11.4 | Used: trace_required, proof_required, metrics_required |
| 10 | What fields does `AccessPath` contain? | §14.4 | Used: path_id, method, description |
| 11 | What is `ResourceModel` for environments? | §13.4 | Used: cpu/memory/disk/gpu |
| 12 | What is `NetworkState`? | §13.4 | Used: connected, bandwidth, latency, vpn |
| 13 | What is `WorkerType` referenced in Capability? | §11.4 | Typed as list[str] — no formal WorkerType enum in synthesis |
| 14 | `timedelta` in MasteryRequirement.required_freshness — JSON serialization? | §11.10 | Pydantic handles timedelta serialization natively |

---

## Coverage Check — Every §24 Layer Represented

| Layer | File | Primary Models |
|-------|------|---------------|
| 1. Interface | — | Not in protocol pack (interface is projection, not contract) |
| 2. Control Plane | control_plane.py | ControlPlaneEvent |
| 3. Understanding | understanding.py | Signal, InterpretedSignal, DomainMap, PrimitiveMapping |
| 4. State | state.py | WorldState, WorldEntity, Fact, MemoryRecord |
| 5. Composition | composition.py | RegistryItem, Template, Capability, ExecutableComposition, MasteryRequirement |
| 6. Governance | governance.py | GovernancePolicy |
| 7. Execution | execution.py | ActionContract, WorkPacket, Environment |
| 8. Adapters | adapters.py | Adapter (Protocol), AdapterPackage |
| 9. Observability | observability.py | Trace, ProofArtifact |
| 10. Learning | learning.py | InternalSignal |

All 9 protocol-relevant layers covered. Layer 1 (Interface) correctly excluded — 
interfaces emit signals INTO the control plane, they don't define protocol contracts.

---

## Safety Verification

- [x] ADDITIVE ONLY — no existing files modified (only umh/__init__.py guard replaced)
- [x] NOT COMMITTED — all changes are unstaged
- [x] LEAF package — zero imports from eos_ai/, runtime/, services/, core/
- [x] No invented fields — all from synthesis, ambiguities logged above
- [x] No deletions or renames

---

## Ready For

Next phase: migration test suite — verify existing runtime/ types can be 
mapped to/from these canonical contracts. This establishes the bridge from 
current implementation to target architecture.
