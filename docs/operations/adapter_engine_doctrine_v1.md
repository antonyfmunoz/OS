# Adapter Engine — Doctrine v1

**Phase**: 96.5  
**Status**: ACTIVE  
**Date**: 2026-05-04

---

## Core Rule

The Adapter Engine is the UMH subsystem that makes external tools, SaaS platforms, sources, protocols, runtimes, and backends usable by UMH. It does not merely connect — it integrates operationally. Every adapter is an 8-layer package. Tool Mastery is an internal layer of the Adapter Engine, not a separate system.

## 8-Layer Adapter Package Model

| Layer | Name | Purpose |
|-------|------|---------|
| 1 | Access Adapter | Transport, endpoint, SDK binding — how UMH reaches the tool |
| 2 | Auth Adapter | Credential acquisition, refresh, rotation — how UMH authenticates |
| 3 | Capability Map | Enumerated actions the tool exposes — what UMH can do with it |
| 4 | Tool Mastery Pack | Best practices, workflows, failure modes, edge cases, quality standards — how to use the tool like a master |
| 5 | Governance Policy | Rate limits, cost controls, safety constraints, secret handling |
| 6 | Execution Wrapper | Retry logic, error normalization, telemetry, timeout handling |
| 7 | Tests / Validation | Contract tests, parity tests, smoke tests — proof the adapter works |
| 8 | Registry Entry | Metadata record in the adapter registry — discovery and selection |

## Architectural Boundaries

- **Backend Selection** chooses which adapter package to use for a given task.
- **Worker Runtime** executes through the selected adapter package.
- **Tool Mastery Packs** live inside adapters, not alongside them. A mastery pack without its parent adapter is incomplete. An adapter without its mastery pack is technically connected but operationally ignorant.
- **Adapter Factory** generates new adapter packages through an 11-stage lifecycle.

## Key Distinctions

- Adapters are not integrations. Integrations connect. Adapters make tools usable at expert level.
- Tool Mastery is not documentation. It is encoded operational expertise — failure modes, edge cases, quality standards that inform execution and testing.
- The 8 layers are not optional tiers. All 8 must be present for an adapter to be promotable.

## Phase 96.6 Terminology Update

- **"Backend" now means "access path"** in precise terminology. When referring to how data is reached (API, SDK, MCP, CU, etc.), use "access path." See `technical_terminology_glossary_v1.md` for full definitions.
- **BackendCategory enum retained** for backward compatibility. Semantically it represents access path categories. Code rename deferred; semantic correction is immediate.
- **Tool Mastery Pack maturity requirements strengthened.** A mastery pack must now have `completeness_requirements`, `failure_modes`, `anti_patterns`, and `validation_checklist` to be considered mature. The `tool_mastery_is_mature()` helper validates all 4. An adapter with a mastery pack that lacks any of these fails the quality gate.
- **AdapterPackage dataclass added** in `adapter_engine_contracts.py` as the formal 8-layer bundle structure. Contains: adapter_profile, auth_profile_ref, access_paths, capability_map, governance_policy_ref, execution_wrapper_ref, tool_mastery_pack_ref, tests_ref, registry_entry_ref, selection_metadata.

## References

- `eos_ai/adapter_engine.py` — core engine
- `eos_ai/adapter_registry.py` — registry and discovery
- `eos_ai/adapter_best_practices_loader.py` — Tool Mastery Pack loader
- `eos_ai/adapter_factory.py` — generation lifecycle
- `eos_ai/adapter_quality_gate.py` — promotion gate
- `docs/operations/adapter_quality_gate_v1.md` — quality gate policy
- `docs/operations/adapter_factory_generation_lifecycle_v1.md` — generation stages
