# Campaign 12 — Learning Intelligence & Outcome Compounding

**Status:** COMPLETE
**Commit:** e39945e1
**Branch:** worktree-c4-6-cockpit-finalization
**Date:** 2026-06-18
**LOC:** 4,326 (18 files changed)
**Tests:** 92 passing

---

## What This Is

C12 closes the cognitive cycle that C5-C11 built:

```
Intent → Goals → Decisions → Capabilities → Work → Outcomes
     → LEARNING → Improved Capabilities → Better Outcomes
```

The system can now answer: "What did we learn? What patterns recur? Which capabilities are evolving? Where is learning stalled?"

## Architecture

**4 substrate runtimes** (all read-only composition, zero LLM calls):

### C12.0 — LearningExtractionRuntime (690 LOC)
Cross-subsystem semantic lesson extraction. Composes OutcomeLearningLoop + DecisionRegistry + AssumptionTrackingRuntime + OutcomeTrackingRuntime + StrategicMemoryEngine.
- 6 lesson categories (success/failure patterns, assumption invalidation, decision consequence, capability gap, process improvement)
- Evidence fingerprint deduplication via SHA-256
- `provenance()` traces every evidence source for a lesson (per user requirement)
- `confidence_reason` + `source_count` fields for explainability

### C12.1 — OutcomePatternEngine (748 LOC)
Recurring pattern detection + outcome attribution. This is the intellectual core (40% of engineering attention).
- 7 pattern types (recurring success/failure, decision correlation, capability bottleneck, assumption chain failure, goal drift, velocity trend)
- 5 pattern detectors: recurring outcomes, decision correlations, capability bottlenecks, assumption chains, velocity trends
- Attribution traces outcomes backward through decision lineage with proximity decay scoring
- JSONL persistence at data/umh/learning/patterns.jsonl

### C12.2 — CapabilityEvolutionEngine (523 LOC)
Per-capability evolution trajectory + maturity trend analysis.
- 7 event types (maturity advance/decline, new evidence, gap identified/closed, pattern-driven proposal, operationalization linked)
- 4 maturity levels: emerging → validated → operational → institutional
- Trajectory computation with trend analysis + next-level prediction
- Recommendation priorities: Critical > Invest > Attention > Stalled > Momentum

### C12.3 — LearningPortfolioRuntime (562 LOC)
Composition façade — portfolio health + drift detection + compounding.
- Health classification: THRIVING / HEALTHY / STAGNANT / DECLINING / CRITICAL
- 5 drift detectors: lesson staleness, pattern blindness, capability stall, outcome loop silence, compounding blockage
- Weighted compounding score from 5 subsystem signals
- Pure read-only — no persistence

## Cockpit Integration

### API (10 endpoints under /learning/)
- `/overview` — full portfolio snapshot
- `/lessons` — recent lessons
- `/lessons/actionable` — actionable lessons only
- `/patterns` — top detected patterns
- `/patterns/{id}` — single pattern detail
- `/evolution` — all capability trajectories
- `/evolution/{id}` — single trajectory detail
- `/drift` — drift warnings
- `/health` — health + effectiveness
- `/compounding` — compounding score + velocity

### Frontend
- Zustand store (learningStore.ts) with 5 parallel fetches
- 5-tab LearningPanel: Overview, Lessons, Patterns, Evolution, Drift
- `'learning'` + `'workintelligence'` added to cockpitStore.ts Panel type

### Executive Integration
- Executive brief: `learning_health`, `learning_velocity`, `learning_drift_count` fields
- Strategic context: `learning_health` dict with health/compounding_score/lesson_count/velocity/drift_count

## Compliance

- 20 new types registered in canonical_types.py
- All pre-commit gates pass: type divergence, dependency direction, instance leak
- No file exceeds 3,000 lines
- Python 3.11 compatible (no 3.12+ syntax)
- substrate/ never imports from transports/ or services/
- Deterministic-first: zero LLM calls
- OutcomeLearningLoop composed, not replaced

## Key Design Decisions

1. **OutcomeLearningLoop = mechanical authority** (outcome→reliability). **C12 = semantic authority** (outcome→meaning→pattern→lesson→capability recommendation). No overlap.
2. **6→5 phase consolidation**: Merged Outcome Attribution + Pattern Intelligence into OutcomePatternEngine because attribution IS pattern detection applied to outcomes.
3. **Explainability fields**: `confidence_reason` + `source_count` on ExtractedLesson — future campaigns will need explainability.
4. **Provenance traceability**: Given a lesson, `provenance()` shows every outcome, decision, assumption, and capability evidence that produced it.

## Acceptance Tests

- [x] Given an outcome, extract a semantic lesson with category + confidence + evidence
- [x] Given 3+ similar outcomes, detect a recurring pattern
- [x] Given a capability, compute its evolution trajectory with trend
- [x] Given the whole portfolio, classify learning health + detect drift
- [x] Given a lesson, show every outcome/decision/assumption/capability evidence that produced it
- [x] Zero LLM calls — all deterministic
- [x] All 92 tests pass
- [x] All pre-commit gates clean
