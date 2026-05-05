# Adapter Package — Doctrine v1

**Phase**: 96.6
**Status**: ACTIVE
**Date**: 2026-05-05

---

## Core Rule

An Adapter Package is the complete operational bundle for making an external tool, platform, or service usable by UMH at expert level. It is not a connector — it is a fully instrumented integration with 8 mandatory layers. An adapter package without Tool Mastery is technically connected but operationally ignorant.

## 8-Layer Model

| Layer | Name | Purpose |
|-------|------|---------|
| 1 | Access Adapter | Transport, endpoint, SDK binding — how UMH reaches the tool |
| 2 | Auth Adapter | Credential acquisition, refresh, rotation — how UMH authenticates |
| 3 | Capability Map | Enumerated actions the tool exposes — what UMH can do with it |
| 4 | Tool Mastery Pack | Expert knowledge: best practices, anti-patterns, traps, failure modes, validation checklists |
| 5 | Governance Policy | Rate limits, cost controls, safety constraints, secret handling |
| 6 | Execution Wrapper | Retry logic, error normalization, telemetry, timeout handling |
| 7 | Tests / Validation | Contract tests, parity tests, smoke tests — proof the adapter works |
| 8 | Registry Entry | Metadata record in the adapter registry — discovery and selection |

## AdapterPackage Dataclass

The `AdapterPackage` dataclass in `adapter_engine_contracts.py` contains:

- `adapter_profile` — identity, version, owner
- `auth_profile_ref` — reference to auth configuration
- `access_paths` — list of access path categories this package supports
- `capability_map` — capabilities exposed by this adapter
- `governance_policy_ref` — reference to governance policy
- `execution_wrapper_ref` — reference to execution wrapper
- `tool_mastery_pack_ref` — reference to Tool Mastery Pack (required for maturity)
- `tests_ref` — reference to test suite
- `registry_entry_ref` — reference to registry record
- `selection_metadata` — scoring data used by the Selection Engine

## Tool Mastery Is Required for Maturity

Layer 4 (Tool Mastery Pack) is the difference between a basic connector and an expert-level adapter. An adapter can function without mastery — it can connect, authenticate, and execute basic operations. But it cannot be promoted to production maturity without a complete mastery pack.

A complete mastery pack must have: `completeness_requirements`, `failure_modes`, `anti_patterns`, `validation_checklist`. The `tool_mastery_is_mature()` helper validates all four.

## Lifecycle

Adapter packages are created through the Adapter Factory (11-stage lifecycle) and promoted through the Adapter Quality Gate (7 checks including mastery maturity). See `adapter_factory_generation_lifecycle_v1.md` and `adapter_quality_gate_v1.md`.

## Hard Rules

- All 8 layers must be present for an adapter to be promotable.
- Tool Mastery Pack (Layer 4) is not optional for production adapters.
- An adapter that passes checks 1-6 but fails mastery maturity is not promotable.
- The AdapterPackage dataclass is the canonical structure — do not create parallel representations.

## References

- `eos_ai/adapter_engine_contracts.py` — AdapterPackage dataclass, enums
- `docs/operations/adapter_engine_doctrine_v1.md` — engine-level doctrine
- `docs/operations/tool_mastery_pack_doctrine_v1.md` — mastery requirements
- `docs/operations/adapter_quality_gate_v1.md` — promotion gate
- `docs/operations/adapter_factory_generation_lifecycle_v1.md` — creation lifecycle
