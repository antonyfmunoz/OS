# Phase 8.0 — World Model Construction

**Date**: 2026-05-28
**Status**: COMPLETE
**Goal**: Build the first canonical UMH world model from observed reality.

## What Was Built

### substrate/organism/world_model.py
Organism-level self-model. Deterministic extraction — no LLM required.

**Core entities:**
- `WorldEntity` — a subsystem, interface, runtime, panel, store, etc.
- `WorldCapability` — what an entity provides
- `WorldEvidence` — proof that something exists/works (file_exists, import_succeeds, etc.)
- `WorldGap` — known missing pieces with severity
- `WorldUncertainty` — things we can't verify with confidence
- `WorldModel` — the complete model with query/filter APIs

**Entity categories:**
subsystem, capability, interface, runtime, execution_path, governance,
memory, cockpit_surface, deployment, data_store, transport

**Deterministic extractors (no LLM):**
1. `_extract_subsystems` — 20 organism subsystems from file/import checks
2. `_extract_adapters` — model router, LLM adapter, CC SDK
3. `_extract_transports` — Discord, operator API, cockpit API
4. `_extract_cockpit_surfaces` — all .tsx Panel components
5. `_extract_data_stores` — JSONL/JSON persistence files
6. `_extract_governance` — governance control plane, router, spine
7. `_extract_deployment` — compose, Dockerfile, fly.toml
8. `_extract_api_routes` — all TypeScript route files
9. `_detect_wiring_gaps` — cross-reference subsystems vs routes

**Extraction result:**
- 80 entities across 7 categories
- 49 partial, 27 operational, 4 missing
- 1 gap, 0 uncertainties (clean state)

### API Integration
- Bridge handler: `organism.world_model` in organism_bridge.py
- Route: `GET /api/umh/organism/world-model`

### Tests
- 23 tests in `substrate/organism/tests/test_world_model.py`
- Covers: entity creation, evidence attachment, gap detection, uncertainty tracking,
  serialization, extraction, persistence, daemon integration
- **23/23 PASS**

## Success Criteria
The organism can answer "what exists?" with evidence from observed reality. **MET.**

## Notes
- The existing `understanding/world_model/` is a domain knowledge model (patterns, strategy).
  This new model is a system self-model (subsystems, state, evidence). Complementary, not overlapping.
- All extraction is deterministic — works even when all LLM providers are down.
