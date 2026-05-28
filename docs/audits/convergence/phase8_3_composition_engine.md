# Phase 8.3 — Composition Engine

**Date**: 2026-05-28
**Status**: COMPLETE
**Goal**: Build deterministic composition engine that turns intent + context + constraints into executable system proposals.

## What Was Built

### substrate/organism/composition_engine.py

**Core entities:**
- `CompositionIntent` — what the operator wants to achieve
- `CompositionContext` — current system state (readiness, contradictions, bottlenecks)
- `CompositionConstraint` — hard/soft constraints on the plan
- `CapabilityMatch` — capabilities available for the plan
- `CompositionStep` — a single step with action, dependencies, risk, governance
- `CompositionRisk` — identified risks with mitigation
- `CompositionPlan` — complete plan with steps, risks, prerequisites, evidence

**Intent classification (deterministic):**
- `fix_contradictions` — triggered by "contradiction", "mismatch", "truth"
- `improve_readiness` — triggered by "readiness", "improve", "strengthen"
- `wire_missing_panel` — triggered by "panel", "wire", "cockpit surface"
- `safe_maintenance` — triggered by "maintenance", "cleanup", "rotate"
- `general` — fallback 4-step pattern

**Each plan includes:**
- Sequential steps with dependencies
- Risk classification per step and overall
- Governance mode (autonomous/assisted/operator_required)
- Validation strategy
- Rollback plan
- Evidence trail from world model + dependencies + contradictions

### API Integration
- Bridge handler: `organism.compose` in organism_bridge.py
- Route: `POST /api/umh/organism/compose`

### Tests
- 21 tests in `substrate/organism/tests/test_composition_engine.py`
- Covers: intent parsing, capability matching, missing dependency detection, plan generation, risk classification, governance requirement, serialization, persistence
- **21/21 PASS**

## Success Criteria
The organism can generate an evidence-based executable plan from observed reality. **MET.**
