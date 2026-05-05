# Phase 6B: Plan Quality + Objective Reconstruction Layer v1 — Completion Report

**Date:** 2026-04-27
**Status:** Complete

---

## Files Created

| File | Purpose |
|------|---------|
| `umh/planning/objective.py` | Objective reconstruction — messy intent → structured PlanObjective |
| `umh/planning/quality.py` | Plan quality scoring — 6-dimension usefulness gate |
| `umh/planning/explanation.py` | Plan explainability — structured decision summary |
| `tests/unit/test_phase6b.py` | 58 tests across 7 categories |

## Files Modified

| File | Change |
|------|---------|
| `umh/planning/models.py` | Added 5 fields to PlanObjective (raw_input, intent_category, inferred_constraints, uncertainty, assumptions), 2 fields to ExecutionPlan (quality_score, explanation), updated to_dict() |
| `umh/planning/planner.py` | Added create_plan_from_raw(), quality scoring + explanation in create_plan(), quality gate in execute_plan(), events |
| `umh/control/api.py` | raw_input support in POST /plans, quality gate in execute endpoint, enriched GET /plans with quality_verdict, expanded plan metrics |

---

## Objective Reconstruction Architecture

```
Raw string ("check system health")
    │
    ▼
reconstruct_objective()  [pure function, no I/O, no LLM]
    │
    ├─ Pattern matching (9 intent patterns)
    ├─ Path extraction (regex)
    ├─ max_steps extraction
    ├─ dry_run / sandbox detection
    ├─ Template hint derivation
    └─ Uncertainty flagging
    │
    ▼
PlanObjective with:
    title = "inspect_system_status"  (template hint)
    intent_category = "system_health"
    context = {}
    raw_input = "check system health"
    uncertainty = ()
    assumptions = ("Template 'inspect_system_status' matches intent",)
```

### Intent Categories

| Category | Pattern Examples | Template Hint |
|----------|-----------------|---------------|
| system_health | "check system health", "system status" | inspect_system_status |
| file_inspect | "inspect /tmp/foo.txt", "read file" | inspect_file |
| directory_list | "list files in /opt/OS", "ls" | list_directory |
| summarize | "summarize this text", "tldr" | summarize_text |
| screenshot | "take a screenshot" | computer_screenshot_review |
| shell_health | "check cpu load", "memory usage" | shell_health_check |
| computer_action | "click", "scroll", "type" | (none — needs LLM) |
| metrics | "show metrics", "dashboard" | inspect_system_status |
| unknown | anything else | (none) |

---

## Quality Scoring Model

```
score_plan(plan, validation) → PlanQualityScore
    │
    ├─ completeness  (title, description, steps present)
    ├─ safety        (known ops, no unsupported, gated properly)
    ├─ specificity   (description length, context, uncertainty)
    ├─ executability  (required inputs present, validation clean)
    ├─ minimality    (step count: 1-3 = 1.0, 4-5 = 0.8, 6-8 = 0.6, 9+ = 0.3)
    └─ constraint_alignment  (allowed_capabilities, max_steps)
    │
    ▼
verdict:
    score >= 0.7  → "pass"
    score >= 0.4  → "warn"
    score < 0.4   → "fail"
    any [FAIL] reason → "fail" (override)
```

Quality is orthogonal to validation:
- **Validation** = structural correctness gate (hard block)
- **Quality** = usefulness/readiness gate (soft block at API)

---

## Explanation Model

```
explain_plan(plan, validation, quality) → PlanExplanation
    │
    ├─ objective_summary: title + description
    ├─ steps_summary: [{index, name, operation, class, rationale}]
    ├─ assumptions: plan + objective assumptions merged
    ├─ risks: approval-gated ops, shell commands, validation issues
    ├─ approval_requirements: which steps need approval
    ├─ plan_selection_reason: "Deterministic template" / "LLM-generated"
    ├─ safety_assessment: "SAFE" / "CONDITIONAL" / "UNSAFE"
    └─ quality_summary: {score, verdict, dimensions}
```

All fields are serializable dicts — no prose blobs.

---

## API Changes

### POST /plans

Now accepts either:
```json
{"raw_input": "check system health"}
```
or the existing structured form:
```json
{"title": "summarize_text", "context": {"text": "hi"}}
```

Response now includes `quality` and `explanation` objects.

### POST /plans/{id}/execute

New quality gate:
- `verdict=fail` → HTTP 422 (blocked)
- `verdict=warn` → HTTP 200, response includes `quality_warnings`
- `verdict=pass` → HTTP 200

### GET /plans

Each plan now includes `quality_verdict` and `quality_score_value` compact fields.

### GET /plans/{id}

Response includes full `quality` and `explanation` objects.

---

## Metrics Changes

Plan metrics now include:

| Field | Type | Description |
|-------|------|-------------|
| `plans_by_quality_verdict` | `{pass, warn, fail}` | Count per verdict |
| `avg_plan_quality` | `float` | Mean quality score |
| `quality_failures` | `int` | Plans with verdict=fail |

Recent plans entries now include `quality_verdict` and `quality_score`.

---

## Events

| Event | When |
|-------|------|
| `objective.reconstructed` | After raw input → PlanObjective conversion |
| `plan.quality_scored` | After quality scoring on validated plans |
| `plan.execution_blocked_quality` | When execute_plan blocked by quality=fail |

---

## Test Results

**58 tests, 58 passed, 0 failures (65s)**

| Category | Count | Coverage |
|----------|-------|----------|
| A. Objective reconstruction | 13 | Intent matching, path/text extraction, uncertainty, dry_run, max_steps |
| B. Quality scoring | 10 | All verdicts, all dimensions, validation interaction |
| C. Explainability | 9 | All output fields, serialization, selection reason |
| D. Planner integration | 9 | Raw input path, quality attachment, quality gate, warn allows |
| E. API | 10 | Raw input, structured, quality gate, metrics, list enrichment |
| F. Events | 3 | objective.reconstructed, plan.quality_scored, execution_blocked |
| G. Regression | 4 | Phase 6A templates, Phase 5G pause, no subprocess, existing plans |

## Regression Impact

- Phase 6A: **64 passed, 0 failures**
- Phase 4+5: pending (running)
- No existing tests modified
- No schema changes
- No changes to execution substrate

---

## What Was Intentionally NOT Added

1. **LLM-based intent classification** — Reconstruction is pure/deterministic
2. **Plan auto-repair** — Rejected plans stay rejected; no recursive fix loops
3. **Quality-based plan rewriting** — Quality gates block execution, don't rewrite
4. **Autonomous retries** — No agent loops, no automatic re-planning
5. **Persistent quality history** — In-memory only, like plans themselves
6. **Force flag for fail verdict** — Even force=True cannot bypass quality=fail
7. **New execution paths** — All execution still goes through execute_task()

---

## Phase 6C Safety Assessment

Phase 6C is safe to proceed. The quality and explanation layers are pure functions with no side effects. The planner integration is additive only. All existing invariants are preserved:
- execute() path unchanged
- Task execution unchanged
- Plan validation unchanged
- Approval flow unchanged
- Guard/environment/adapter enforcement unchanged
- ExecutionRequest/ExecutionResult schemas unchanged
