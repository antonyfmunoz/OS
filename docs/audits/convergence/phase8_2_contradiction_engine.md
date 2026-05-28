# Phase 8.2 — Contradiction Engine

**Date**: 2026-05-28
**Status**: COMPLETE
**Goal**: Detect mismatches between declared state and observed reality.

## What Was Built

### substrate/organism/contradiction_engine.py

**Core entities:**
- `Claim` — what the system declares to be true
- `Observation` — what we actually observe
- `Contradiction` — a mismatch between claim and observation, with severity, confidence, evidence, recommended fix
- `ContradictionReport` — collection of contradictions with filtering and summary
- `ContradictionEngine` — runs all checks and produces a report

**Contradiction types:**
declared_missing_observed, observed_missing_declared, stale_deployment,
route_mismatch, api_contract_mismatch, wiring_mismatch, capability_gap,
security_mismatch, dependency_mismatch, data_integrity, status_contradiction

**7 deterministic checks:**
1. Missing subsystem files — declared but not on disk
2. Empty data stores — file exists but zero bytes
3. Orphaned subsystems — no dependency connections
4. Missing deployment files — expected configs absent
5. Route/panel mismatch — panels without API backing
6. Dependency cycles — architecture violations
7. Missing governance — governance systems not found

**Every contradiction includes:**
- Evidence (what was observed)
- Source (where the claim came from)
- Severity (critical/high/medium/low/info)
- Confidence (0.0-1.0)
- Recommended fix

### API Integration
- Bridge handler: `organism.contradictions` in organism_bridge.py
- Route: `GET /api/umh/organism/contradictions`

### Tests
- 17 tests in `substrate/organism/tests/test_contradiction_engine.py`
- Covers: claim/observation matching, stale build detection, missing route detection, wiring mismatch, confidence scoring, serialization, persistence
- **17/17 PASS**

## Success Criteria
The organism can say "we claim X, but reality shows Y" with evidence. **MET.**
