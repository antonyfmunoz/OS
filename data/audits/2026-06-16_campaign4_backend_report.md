# Campaign 4 — Operator-Orchestrator Convergence
## Backend Complete (C4.0–C4.5)

**Date:** 2026-06-16
**Branch:** worktree-gate-5-capability-runtime
**PR:** #65 — https://github.com/antonyfmunoz/OS/pull/65
**Commit:** 16ac45e5

---

## Campaign Thesis

Campaign 4 reframes the Right Rail from a chat system to the **communication interface between the operator and the UMH orchestrator**. The campaign answers 4 questions:

1. Can the orchestrator understand UMH?
2. Can the operator live inside UMH?
3. Can the orchestrator coordinate the organism?
4. Can the operator leave and return?

---

## Build Summary

| Workstream | File | LOC | Tests | Status |
|---|---|---|---|---|
| C4.0 Orchestrator Awareness | `substrate/organism/orchestrator_awareness_runtime.py` | 570 | 59 | ✅ COMPLETE |
| C4.1 Operating Loop | `substrate/workstation/operating_loop_runtime.py` | 300 | 40 | ✅ COMPLETE |
| C4.2 Unified Approval | `substrate/workstation/unified_approval_runtime.py` | 492 | 52 | ✅ COMPLETE |
| C4.3 Loop Coherence | `substrate/organism/operating_loop_coherence_runtime.py` | 475 | 45 | ✅ COMPLETE |
| C4.4 Session Continuity | `substrate/operator/workstation_session_runtime.py` | 412 | 42 | ✅ COMPLETE |
| C4.5 MVP Readiness | `substrate/workstation/mvp_readiness_runtime.py` | 443 | 37 | ✅ COMPLETE |

**Totals:**
- 6 runtimes: 2,692 LOC
- 6 route files: 472 LOC
- 6 test files: 2,917 LOC
- **Grand total: 6,123 LOC, 275 tests (all passing)**
- 30 canonical type registrations across 6 workstreams
- 19 files changed in commit

---

## Workstream Details

### C4.0 — Orchestrator Awareness Runtime
**Question:** "Does the orchestrator understand the complete state of UMH?"

- Synthesized reality model across **6 domains, 23 subsystems**
- `OrchestratorContext` — 32-field dataclass, the orchestrator's single read path
- 6 domain queries: operator, cockpit, organism, execution, development, source_truth
- **Dual capability layer:** EmergentCapability (what UMH learned) vs Capability enum (job/tool capabilities) — never conflated
- `awareness_score()` — 0.0-1.0 ratio of active/total subsystems
- All 23 constructor deps as `Any | None = None` for graceful degradation
- Routes: 5 endpoints under `/orchestrator/`

### C4.1 — Operating Loop Runtime
**Question:** "Can every active loop be visible?"

- **Visibility layer only** — NOT an execution engine
- Planning/assignment/execution/review already belong to MetaIDEProjectionLoopRuntime, AgentFleetRuntime, ComputeFabricRuntime, GovernedWorkRuntime
- 9-stage `OperatingLoopStage` enum: intent → plan → assign → execute → review → approve → learn → complete | failed
- `track()` — register loop from intent; `record_transition()` — advance stage
- `correlate_intent()` — connect intent_id to downstream execution
- `lineage_for()` — ExecutionGraph integration for full trace
- Routes: 8 endpoints under `/operating-loop/`

### C4.2 — Unified Approval Runtime
**Question:** "What requires operator intervention, from one place?"

- **10 approval sources** unified into one queue:
  1. GovernedWorkRuntime
  2. ApprovalInterceptService
  3. OperatorApprovalGate
  4. StrategicGapEngine
  5. CompoundingEngine (uses `PromotionStatus.PROPOSED` enum)
  6. TemplateRegistry
  7. MemoryPromotionPipeline
  8. OvernightQueue
  9. AutomationPipeline
  10. ReconciliationEngine
- **Deterministic urgency scoring:** `RISK_WEIGHTS[risk_class] * (age_minutes / 60.0)`
- `approve()`/`reject()` route to correct source subsystem
- **Approvals owned by Top HUD** — NOT the Right Rail (enforced in C4.6)
- Routes: 7 endpoints under `/approvals/unified/`

### C4.3 — Operating Loop Coherence Runtime
**Question:** "Do all systems agree on reality after loops execute?"

- Composes **9 subsystems** (7 existing + C4.1 + C4.0)
- 4 detection methods:
  - `detect_orphans()` — intents without work, work without intents
  - `detect_broken_chains()` — skipped stages in lineage
  - `detect_stale_approvals()` — pending > threshold
  - `detect_contradictions()` — ContradictionEngine integration
- `full_report()` — aggregates all detectors
- `coherence_score()` — deterministic, severity-weighted
- Routes: 7 endpoints under `/loop-coherence/`

### C4.4 — Workstation Session Runtime
**Question:** "Can the operator leave and return later?"

- **Full OrchestratorContext restore on resume** — not just session metadata
- Composes 4 continuity levels + C4.0-C4.3
- `checkpoint()` — captures orchestrator context, active loops, pending approvals, coherence score, attention
- `pause()` → auto-checkpoint → record departure
- `resume()` → 12-step restore: last checkpoint, organism diff, workstation transition, full OrchestratorContext, loops, approvals, coherence, attention, recommendations, changes, next_actions
- `_derive_next_actions()` — blocked loops + pending approvals + attention → actionable list
- Routes: 9 endpoints under `/session/`

### C4.5 — MVP Readiness Runtime
**Question:** "Is UMH actually the MVP?"

- **14 dimensions** (including `orchestrator_awareness` — new for Campaign 4):
  1. orchestrator_awareness, 2. intent_capture, 3. intent_understanding
  4. plan_creation, 5. work_assignment, 6. execution_routing
  7. execution_tracking, 8. approval_routing, 9. lineage_capture
  10. learning_capture, 11. continuity, 12. coherence
  13. cockpit_coverage, 14. projection_awareness
- 4 status levels: READY (≥0.8), PARTIAL (≥0.4), BLOCKED (>0), MISSING (0)
- `escape_points()` — where operator must leave UMH
- `recommended_next()` — ordered by impact (lowest scores first)
- Routes: 6 endpoints under `/mvp-readiness/`

---

## Architecture Decisions

1. **OrchestratorContext as single read path** — orchestrator never reasons across 23 runtimes per-message; one synthesized model
2. **Dual capability layers** — EmergentCapability (organism/capability_runtime.py) vs Capability enum (execution/runtime/capability_router.py) kept distinct
3. **All deps optional** — every constructor uses `Any | None = None`; zero deps = valid construction, graceful degradation
4. **`_safe_call`/`_safe_dict`/`_safe_list` pattern** — standardized across all 6 runtimes; catches exceptions, returns typed defaults
5. **Visibility not execution** — C4.1 observes loops, doesn't own them; execution stays in MetaIDE/Fleet/Fabric/GovernedWork
6. **Top HUD owns approvals** — Right Rail only explains; approval buttons in Top HUD (enforced in C4.6)

---

## Verification

| Gate | Status |
|---|---|
| `python3 -m py_compile` (all 18 files) | ✅ Clean |
| `pytest` (275 tests) | ✅ 275/275 pass |
| `check_type_divergence.py` | ✅ Clean |
| `check_dependency_direction.py` | ✅ Clean |
| `check_projection_leak.py` | ✅ Clean |
| `check_instance_leak.py` | ✅ Clean |
| No file over 3,000 lines | ✅ Largest: 570 LOC |
| substrate/ imports | ✅ No upward deps |

---

## Remaining: C4.6 — Cockpit Finalization

- 5 TypeScript stores (orchestratorAwareness, operatingLoop, unifiedApproval, session, mvpReadiness)
- 5 panels (OrchestratorPanel, OperatingLoopPanel, UnifiedApprovalPanel [Top HUD], SessionPanel, MVPReadinessPanel)
- cockpit.py: 6 new route mounts
- Shell.tsx: Top HUD enforcement — approvals there, not Right Rail
- routes.ts: 4 new panel routes

---

## Campaign 4 Acceptance Criteria

| # | Criterion | Backend Status |
|---|---|---|
| 1 | Awareness — orchestrator understands UMH | ✅ C4.0 |
| 2 | Development — operator can initiate from right rail | ✅ C4.0 + C4.1 |
| 3 | Governance — approvals surface in Top HUD | ✅ C4.2 (UI in C4.6) |
| 4 | Visibility — every active loop visible | ✅ C4.1 |
| 5 | Coherence — organism agrees on reality | ✅ C4.3 |
| 6 | Continuity — operator can leave and return | ✅ C4.4 |
| 7 | Readiness — 14-dimension MVP scoring | ✅ C4.5 |

**All 7 acceptance criteria have backend support. C4.6 frontend completes the campaign.**
