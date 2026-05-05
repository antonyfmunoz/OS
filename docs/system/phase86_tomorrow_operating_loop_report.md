# Phase 86 — EOS Tomorrow Operating Loop v1

**Date**: 2026-05-03
**Status**: Complete
**Extends**: Phase 85B (Council Thinker Archetypes + Adversarial Deliberation)
**Tests**: 81 passing (Phase 86), 1149 total regression (Phase 80–86)
**Safety**: 5 modules checked, 0 violations, 0 warnings
**Hard rules**: 8

## Executive Summary

Phase 86 builds the Tomorrow Operating Loop — the minimum EOS functionality
for the founder to wake up and use EOS to run/improve the first operating
workflow (Personal Brand → Initiate Arena Revenue Loop). The loop threads
a unified daily cycle: prepare → brief → execute → review → close → handoff
→ completed, with typed state at every phase transition and two-day
continuity through TomorrowHandoff.

The first workflow template maps the 16-stage revenue loop from
`docs/strategy/first_operating_workflow.md` into typed contracts: 16
WorkflowStages, 17 KPIDefinitions, structured failure modes, and data
capture specs. The orchestrator produces state — it does not call adapters,
LLMs, or external services. v1 is fully deterministic.

## Architecture

### Daily Loop State Machine

```
NOT_STARTED → PREPARE → BRIEF → EXECUTE → REVIEW → CLOSE → HANDOFF → COMPLETED
     ↓            ↓         ↓        ↓          ↓        ↓         ↓
   FAILED      FAILED    FAILED   FAILED     FAILED   FAILED    FAILED
```

Every non-terminal phase can transition to FAILED. Terminal phases
(COMPLETED, FAILED) have no outbound transitions. The UNKNOWN phase
exists as a normalization fallback but is excluded from the transition table.

### Phase Responsibilities

| Phase | Responsibility |
|-------|---------------|
| PREPARE | Generate today's objectives from template stages (or carry from handoff) |
| BRIEF | Produce structured morning briefing: objectives, active/blocked stages, KPI targets, carried warnings |
| EXECUTE | User works on objectives; supports mid-day adds and completions |
| REVIEW | Analyze day: completion rate → outcome classification (ON_TRACK / NEEDS_ADJUSTMENT / BLOCKED / CRITICAL) |
| CLOSE | Finalize day, set tomorrow's priorities on the review |
| HANDOFF | Produce TomorrowHandoff: unresolved objectives, blockers, continuity notes, KPI snapshot, tomorrow's starting objectives |
| COMPLETED | Terminal state |

### Two-Day Continuity

`TomorrowHandoff` is the sole contract between consecutive days:

- `tomorrow_objectives` — priorities + carried unresolved items (max 5)
- `blockers_carried` — unresolved blockers from today's review
- `continuity_notes` — contextual notes based on review outcome
- `kpi_snapshot` — top 10 KPI current values at handoff time

`initialize_loop()` consumes the previous handoff, seeding the new day
with objectives and warning annotations for carried blockers.

### Review Outcome Classification

| Outcome | Condition |
|---------|-----------|
| ON_TRACK | All objectives completed, no blockers |
| NEEDS_ADJUSTMENT | ≥50% completed but not all, or 0 objectives |
| BLOCKED | Any blockers reported |
| CRITICAL | <50% completed |

## First Workflow Template

**Name**: Personal Brand → Initiate Arena Revenue Loop
**Stages**: 16 | **KPIs**: 17 | **Cadence**: Daily | **Owner**: antony
**Binding constraint**: $10K/month net

### 16 Stages

| # | Stage | Priority | Key KPIs |
|---|-------|----------|----------|
| 1 | Content Strategy | High | Posts/week |
| 2 | Content Production | High | Posts/week |
| 3 | Publishing | High | Posts/week |
| 4 | Engagement Capture | Medium | Comments/post |
| 5 | DM/Comment Conversation | Medium | DMs/week |
| 6 | Lead Capture | Medium | Leads/week |
| 7 | Qualification | Medium | Qualified leads/week |
| 8 | Sales Conversation / Call Booking | Medium | Calls booked, show-up rate, objections |
| 9 | Close / Payment | Medium | Close rate, revenue/month |
| 10 | Onboarding | Medium | Onboarding completion |
| 11 | Initiate Arena Fulfillment | Medium | Fulfillment completion, manual hours |
| 12 | Progress Tracking | Medium | Progress signals |
| 13 | Testimonial / Case Study | Medium | Testimonials/cohort |
| 14 | Upsell Path to Game of Lyfe | Medium | Upsell conversion |
| 15 | End-of-Day Review | Medium | — |
| 16 | Weekly Improvement Loop | Medium | Repeated bottlenecks |

### 17 KPIs

| KPI | Type | Target |
|-----|------|--------|
| Posts published per week | COUNT | 7+ |
| Comments generated per post | COUNT | increasing trend |
| DMs opened per week | COUNT | 20+ |
| Leads captured per week | COUNT | 10+ |
| Qualified leads per week | COUNT | 5+ |
| Calls booked per week | COUNT | 3+ |
| Show-up rate | PERCENTAGE | 80%+ |
| Close rate | PERCENTAGE | 20%+ |
| Revenue collected per month | CURRENCY | $10K+ net |
| Onboarding completion rate | PERCENTAGE | 95%+ |
| Fulfillment completion rate | PERCENTAGE | 80%+ |
| Progress signals per student per week | COUNT | 3+ |
| Testimonials captured per cohort | PERCENTAGE | 50%+ of completers |
| Objections captured | COUNT | all documented |
| Upsell conversion rate | PERCENTAGE | track from first graduate |
| Manual hours per student per week | DURATION | decreasing trend |
| Repeated bottlenecks | COUNT | decreasing trend |

## Files Created

| File | Lines | Purpose |
|------|-------|---------|
| `umh/tomorrow/__init__.py` | 5 | Package marker |
| `umh/tomorrow/contracts.py` | ~260 | Enums (5), normalizers (4), dataclasses (8), `_loop_id()` |
| `umh/tomorrow/orchestrator.py` | ~411 | Phase transition rules, all 7 phase functions, `run_full_cycle()` |
| `umh/tomorrow/first_workflow.py` | ~441 | 16 stages + 17 KPIs as typed WorkflowTemplate |
| `umh/tomorrow/views.py` | ~182 | UI-safe views: TomorrowLoopView, WorkflowTemplateView, DailyBriefView |
| `umh/tomorrow/safety.py` | ~91 | AST-based forbidden import checker |
| `tests/test_phase86_tomorrow_operating_loop.py` | ~810 | 81 tests across 12 test classes |

## Files Modified

None. Phase 86 is a net-new `umh/tomorrow/` package.

## Test Coverage

| Class | Tests | Covers |
|-------|-------|--------|
| TestContractEnums | 6 | All 5 enums, UNKNOWN presence |
| TestContractNormalization | 5 | Round-trips, bad input → UNKNOWN, `_loop_id` format |
| TestContractDataclasses | 10 | to_dict, properties, completion_rate, terminal states |
| TestOrchestratorTransitions | 4 | Transition table completeness, terminal phases, fail paths, happy path |
| TestOrchestratorInitialize | 3 | Basic init, handoff carry-forward, auto-date |
| TestOrchestratorPhases | 14 | All 7 phases, objective CRUD, invalid transitions, review outcomes |
| TestOrchestratorFullCycle | 3 | Full cycle, handoff production, two-day continuity |
| TestFirstWorkflowTemplate | 12 | 16 stages, 17 KPIs, names, numbering, ownership, failure modes, metadata |
| TestViews | 6 | All 3 views + to_dict round-trips |
| TestSafety | 3 | Validation passes, to_dict, manual forbidden import check |
| TestFullPipeline | 2 | End-to-end with first workflow, 3-day continuity chain |
| TestPhase86Regression | 13 | Phase 75B–86 import smoke tests |
| **Total** | **81** | |

## Hard Rules

1. No LLM calls in any tomorrow module
2. No adapter calls — orchestrator produces state only
3. No mutation of external systems
4. No subprocess, requests, httpx, aiohttp, selenium, playwright, smtplib, telegram, discord imports
5. All phase transitions validated against `_VALID_TRANSITIONS`
6. Terminal phases (COMPLETED, FAILED) cannot transition
7. All enums have UNKNOWN fallback
8. All dataclasses have `to_dict()` serialization

## Regression

- **Phase 86 tests**: 81/81 passing
- **Phase 80–86 regression**: 1149/1149 passing
- **Safety validation**: 5 modules, 0 violations
- **Pre-existing collection errors**: 17 (execution engine tests from prior phases — not Phase 86)

## What Phase 86 Enables

The Tomorrow Operating Loop is now the minimum viable daily operating cycle:

1. **Morning**: `initialize_loop()` + `run_prepare()` + `run_brief()` → structured daily briefing
2. **During day**: `start_execute()` + `record_objective_completion()` / `add_objective()` → tracked work
3. **Evening**: `run_review()` + `run_close()` → outcome analysis + tomorrow priorities
4. **Overnight**: `run_handoff()` + `complete_loop()` → continuity for next day

The first workflow template maps the entire Personal Brand → Initiate Arena
revenue loop into this cycle. Every stage has typed objectives, failure modes,
data capture specs, and KPI bindings.

## What Comes Next

- **Phase 87**: Wire Tomorrow Loop to existing UMH day rituals (`open_day`/`close_day`)
- **Phase 88**: KPI tracking persistence and trend analysis
- **Phase 89**: LLM-enhanced briefing and review (advisory, not autonomous)
- **Phase 90**: CLI/API surface for daily interaction
