# substrate/

## Purpose
Canonical UMH substrate — the governed intelligence control plane runtime.

## Status: STAGING
This directory will receive modules migrated from `eos_ai/` and `core/`
through the staged convergence plan (see `docs/system/staged_convergence_migration_plan.md`).

Active runtime code currently lives in:
- `eos_ai/` — ACTIVE_RUNTIME_LEGACY_NAME
- `core/` — PARTIAL_CANONICAL_SUBSTRATE

## Target Structure
```
substrate/
├── control_plane/       # Signal routing, authority, orchestration
├── ontology/            # Primitive types, relationships, schemas
├── perception/          # Signal intake
├── interpretation/      # Intent classification
├── decomposition/       # Primitive observation extraction
├── memory/              # Canonical/instance memory stores
├── world_model/         # External reality representation
├── planning/            # Goal decomposition, strategy
├── composition/         # Action plan assembly
├── governance/          # Constitutional checks, authority
├── execution/           # Adapter invocation, dispatch
├── capabilities/        # Abstract action definitions
├── adapters/            # External system bridges
├── environments/        # Runtime contexts
├── registries/          # Entity inventories
├── observability/       # Tracing, proofs, metrics
├── learning/            # Feedback loops, patterns
├── workstation/         # Physical workstation relay
└── security/            # Secrets, redaction
```

## Migration Rules
- No module moves here without a compatibility shim in the source location
- Every moved module must pass `python3 -m py_compile`
- Tests must be updated to import from new location
- See `docs/migrations/eos_ai_to_substrate_migration_plan.md`
- See `docs/migrations/core_to_substrate_migration_plan.md`

> Created: Phase 96.8BK — 2026-05-09
