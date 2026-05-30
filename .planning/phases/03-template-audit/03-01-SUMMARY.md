---
phase: 03-template-audit
plan: "01"
subsystem: template-registry
tags: [template-audit, organism, cadence, classification]
dependency_graph:
  requires: []
  provides: [data/umh/templates/phase10_0_template_audit.json]
  affects: [Phase 4 template seeding]
tech_stack:
  added: []
  patterns: [8-label classification scheme, candidate discovery gap analysis]
key_files:
  created:
    - data/umh/templates/phase10_0_template_audit.json
  modified:
    - .planning/ROADMAP.md
decisions:
  - "Phase 4 must seed to data/umh/organism/templates/ (runtime path), not data/umh/templates/ (default registry path)"
  - "trial_outcomes.jsonl records are unusable as evidence — null outcome_id means no traceable evidence chain"
  - "substrate/state/registries/template_registry.py is stale relative to execution template supply — different domain (business blueprints vs execution patterns)"
  - "The require_template gate is correct behavior — fix is seeding templates, not relaxing the gate"
metrics:
  duration_minutes: 2
  completed_date: "2026-05-30"
  tasks_completed: 2
  files_modified: 2
  files_created: 1
---

# Phase 03 Plan 01: Template Audit Summary

**One-liner:** Inspected 9 template sources, classified with 8-label scheme, documented 5 candidate discovery gaps (including critical path mismatch at data/umh/organism/templates/), identified 10 missing template categories with TemplateType mappings and evidence references.

## What Was Built

`data/umh/templates/phase10_0_template_audit.json` — structured audit file consumed by Phase 4 seeding as its input contract.

The audit covers every template source in the codebase. The primary finding: cadence returns 0 candidates because `data/umh/organism/templates/` does not exist. This is the runtime path daemon.py passes to TemplateRegistry (`str(self._state_dir / "templates")`). Without this directory, `_candidates={}` and `_promoted={}` from the start of every daemon run.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Inspect all template sources and classify each item | (read-only — no write) | 7 source files read |
| 2 | Write the structured audit JSON and update ROADMAP | 3708f0f8 | data/umh/templates/phase10_0_template_audit.json, .planning/ROADMAP.md |

## Key Findings

### Classified Items (8 total across 9 sources)

| Item | Classification | Notes |
|------|---------------|-------|
| substrate/organism/template_registry.py | production_ready | Code is correct — gap is data |
| substrate/organism/autonomous_improvement_lane.py | production_ready | require_template gate is intentional |
| substrate/state/registries/template_registry.py | stale | Different domain: business blueprints, not execution templates |
| docs/operations/template_candidate_inventory_v1.md | stale | Business ops domain |
| docs/operations/template_pattern_promotion_policy_v1.md | stale | Business ops domain |
| tpl-0b21c294 | needs_evidence, missing_validation, missing_rollback | Wrong path + generic stubs |
| phase9-5b-batch-17 templates | needs_evidence | Temp store only — never persisted to runtime |
| trial_outcomes.jsonl (12 records) | missing_validation, stale | All outcome_id=null — untraceable |

### Candidate Discovery Gaps (5)

1. **gap-1 (CRITICAL):** `data/umh/organism/templates/` does not exist — daemon initializes TemplateRegistry there, loads nothing
2. **gap-2 (CRITICAL):** `require_template=True` blocks ALL candidates when registry is empty
3. **gap-3 (HIGH):** tpl-0b21c294 stored at wrong path — runtime registry never loads it
4. **gap-4 (MEDIUM):** trial_outcomes.jsonl has null outcome_id on all 12 records — generate_candidate_from_outcome() would produce untraceable templates
5. **gap-5 (HIGH):** 0 templates for any of 15 TemplateType values — every find_matching() call returns []

### Missing Template Categories (10)

| Category | Template Type | Priority |
|----------|--------------|---------|
| observation_path_fix | OBSERVATION_ACCURACY_FIX | high |
| contradiction_resolution | CONTRADICTION_FIX | high |
| readiness_dimension_improvement | READINESS_IMPROVEMENT | high |
| api_contract_alignment | API_CONTRACT_FIX | high |
| world_model_staleness_fix | WORLD_MODEL_ACCURACY_FIX | medium |
| test_failure_repair | TEST_REPAIR | medium |
| dependency_graph_refresh | DEPENDENCY_GRAPH_FIX | medium |
| cockpit_endpoint_gap_fix | COCKPIT_PANEL_FIX | medium |
| line_count_gate_fix | ROUTE_EXTRACTION_FIX | medium |
| documentation_alignment_fix | DOCUMENTATION_ALIGNMENT | low |

## Deviations from Plan

None — plan executed exactly as written. The audit data matches all assertions specified in the plan's interfaces section.

One clarification discovered: the `trial_outcomes.jsonl` records use schema keys `id`, `action_type`, `plan_id`, `step_id` rather than `outcome_id`, `success`, `phase`. This means the null fields are not just missing values — the schema itself is incompatible with `generate_candidate_from_outcome()`. Documented as part of gap-4.

## Phase 4 Seeding Contract

Phase 4 must:
1. Create `data/umh/organism/templates/` directory
2. Seed `templates.jsonl` (promoted, not candidates) — find_matching() checks `_promoted` first
3. Seed at minimum 10 template types: MAINTENANCE_ACTION, CONTRADICTION_FIX, READINESS_IMPROVEMENT, OBSERVATION_ACCURACY_FIX, WORLD_MODEL_ACCURACY_FIX, API_CONTRACT_FIX, TEST_REPAIR, COCKPIT_PANEL_FIX, ROUTE_EXTRACTION_FIX, DEPENDENCY_GRAPH_FIX
4. Use evidence from `data/umh/autonomous_lane/` phase artifacts (phase9_6 through phase9_9)
5. Avoid trial_outcomes.jsonl and proof_templates/template_candidates.jsonl as evidence sources

## Self-Check: PASSED

- [x] `data/umh/templates/phase10_0_template_audit.json` exists and parses
- [x] All 8 classification labels addressed in eight_label_summary
- [x] 5 candidate discovery gaps documented with gap_id, severity, title, description, fix_in_phase
- [x] 10 missing categories with template_type_mapping and evidence_reference
- [x] phase4_seeding_instructions.runtime_path = "data/umh/organism/templates/"
- [x] All 15 TemplateType values in template_type_coverage with seeded_count=0
- [x] ROADMAP.md Phase 3 entry updated — plan marked complete, progress table updated
- [x] Commit 3708f0f8 confirmed in git log
