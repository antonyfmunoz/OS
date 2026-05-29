# Phase 9.5 — Spine-Native Propagation + Template-Guided Campaign

**Completed:** 2026-05-29
**Base Commit:** `f34841e22412dcb93c9b1a3208f37dad7801bd0a`
**Branch:** `phase-9-5-spine-native-propagation`

## Baseline

See: phase9_5_baseline.md

Before Phase 9.5:
- GovernedExecutionSpine accepted `propagation_engine` param but daemon never injected one
- ParallelPropagationEngine existed but was never wired into the mutation pathway
- OutcomeCommitted/OutcomeFailed dataclasses existed but were never emitted
- Campaign/trial code had to manually call propagation
- Zero propagation events, zero template candidates, zero agent profiles

| Metric | Before | After |
|--------|--------|-------|
| Spine-native propagation | No | **Yes** |
| Propagation targets registered | 0 | **10** |
| Propagation events | 0 | **4** |
| Template candidates | 0 | **4** |
| Promoted templates | 0 | **1** |
| Agent capability profiles | 0 | **1** |
| Agent capabilities tracked | 0 | **4** |
| Outcome records | 1 | **5** |
| Memory candidates | 0 | **8+** |
| Readiness score | 28.3 | 28.3 |
| Contradictions | 15 | 15 |
| World model entities | 70 | 70 |

## What Changed

### New Files
- `substrate/organism/propagation_wiring.py` (296 lines) — factory function `build_propagation_engine()` that creates a fully-wired ParallelPropagationEngine with 10 handler closures bound to real subsystem instances

### Modified Files
- `substrate/organism/daemon.py` — creates OutcomeLearningLoop, TemplateRegistry, MemoryPromotionPipeline, AgentCapabilityModel; builds propagation engine via `build_propagation_engine()`; passes to GovernedExecutionSpine; exposes 5 new properties
- `transports/api/organism_bridge.py` — updated `_template_reuse_proof` to check phase9_5 proof/campaign files
- `cockpit/src/renderer/panels/IntelligencePanel.tsx` — added "Spine-Native Propagation" section

### Not Modified (already correct)
- `substrate/organism/governed_spine.py` — already had `propagation_engine` param and `_emit_outcome()` wiring
- `substrate/organism/coherence_propagation.py` — already had ParallelPropagationEngine, OutcomeCommitted, idempotency
- `substrate/organism/trial_runner.py` — already did NOT manually call propagation

## Source-of-Truth Wiring

GovernedExecutionSpine is THE single mutation gateway. After execution:

1. `submit()` → `_execute()` → `_verify()` → `_emit_outcome()`
2. Verified/completed → `OutcomeCommitted` → `propagation_engine.handle_outcome()`
3. Failed/exception/verification_failed → `OutcomeFailed` → `propagation_engine.handle_failure()`
4. Rejected by governance → no outcome event (envelope never executed)

The caller never needs to call propagation. The spine does it.

## Propagation Wiring Architecture

`build_propagation_engine()` creates 10 PropagationTargets across 2 waves:

**Wave 1 (Independent):**
| Target | Primitive | Handler |
|--------|-----------|---------|
| outcome_learning | feedback | Records outcome to OutcomeLearningLoop |
| template_generation | action | Generates TemplateCandidate via TemplateRegistry |
| memory_generation | feedback | Generates memory candidates via MemoryPromotionPipeline |
| agent_capability_update | resource | Updates AgentCapabilityModel reliability |
| world_model_evidence | state | Attaches evidence to WorldModel entities |

**Wave 2 (Derived — runs after Wave 1):**
| Target | Primitive | Handler |
|--------|-----------|---------|
| contradiction_recheck | constraint | Rechecks contradictions in ContradictionEngine |
| readiness_recalculate | state | Recalculates ReadinessModel composite score |
| bottleneck_recalculate | state | Recalculates BottleneckEngine active bottlenecks |
| composition_template_refresh | goal | Refreshes CompositionEngine template index |
| dependency_recompute | constraint | Recomputes DependencyGraph edges |

## Spine-Native Propagation Proof

Controlled test (LOW risk, verified envelope):

| Field | Value |
|-------|-------|
| Envelope ID | `067dd31369e245e5` |
| Status | verified |
| OutcomeCommitted | `oc-37b015f1` |
| Propagation event | `pe-d58e32b4` |
| Total targets | 10 |
| Succeeded | **10/10** |
| Failed | 0 |
| Manual propagation called | **NO** |
| Spine-native | **YES** |

Wave 1 timing: template_generation 0.7ms, agent_capability 2.0ms, memory_generation 2.7ms, outcome_learning 3.1ms, world_model_evidence 10.4ms
Wave 2 timing: bottleneck 0.0ms, composition_refresh 0.0ms, readiness 4.8ms, dependency 8.5ms, contradiction 12.6ms

Proof: `data/umh/trials/phase9_5_spine_native_proof.json`

## Template-Guided Campaign Results

3 trials using a single promoted template (tpl-3f614958):

| Trial | Description | Status | Template Confidence |
|-------|-------------|--------|-------------------|
| campaign_trial_1 | Contradiction verification | verified | 0.6 → 1.0 |
| campaign_trial_2 | Readiness dimension assessment | verified | 1.0 → 1.0 |
| campaign_trial_3 | Dependency graph orphan documentation | verified | 1.0 → 1.0 |

Agent capability (`developer_agent`):
- Overall reliability: 1.0
- Total attempts: 10, successes: 10, failures: 0
- Capabilities tracked: code_search, evidence_verification, contradiction_detection, dependency_analysis
- All at confidence 1.0

All 3 trials used spine-native propagation. Zero manual propagation calls.

Proof: `data/umh/trials/phase9_5_campaign_results.json`

## Idempotency

- Key format: `{action_envelope_id}:{completed_at}`
- Persisted to `data/umh/propagation/processed_outcomes.jsonl`
- Duplicate outcomes return None, no re-propagation
- Tests verify: no duplicate records, templates, memory candidates, reliability counts

## Failure Isolation

- One target failure does not block sibling targets in same wave
- Wave 2 runs even if Wave 1 has partial failures
- Original execution success preserved when propagation partially fails
- Propagation failure logged but never thrown to caller
- Tests verify all scenarios

## Tests

65 new tests across 8 test classes:

| Class | Tests | Coverage |
|-------|-------|----------|
| TestSpineNativePropagation | 14 | Outcome emission, propagation fire, wave ordering, subsystem updates |
| TestBackwardCompatibility | 4 | Spine without propagation still works |
| TestIdempotency | 9 | Duplicate rejection, persistence, edge cases |
| TestFailureIsolation | 5 | Target independence, wave independence, execution preservation |
| TestTemplateGuidedCampaign | 8 | Template reuse, confidence updates, agent reliability |
| TestOutcomeEvents | 5 | OutcomeCommitted/Failed dataclass contracts |
| TestDaemonWiring | 8 | Daemon creates and wires all subsystems |
| TestPropagationWiring | 6 | Factory function creates correct targets/waves |
| TestPropagationEngine | 7 | Engine summary, dict, events, failure handling |

Additional test suites verified (zero regressions):
- substrate/ tests: 70 passed
- test_convergence_acceptance: 9 passed
- test_daemon_e2e: 7 passed
- test_governance_full: 10 passed

**Total: 161 tests passed, 0 failures**

## Gates

| Gate | Status |
|------|--------|
| py_compile (propagation_wiring.py) | PASS |
| py_compile (daemon.py) | PASS |
| py_compile (organism_bridge.py) | PASS |
| Dependency direction (substrate/) | PASS — no transports/services imports |
| Line count (all modified files) | PASS — max 884 (daemon.py), all < 3000 |
| Daemon wiring verification | PASS — spine_native=True, 10 targets, 5 subsystems |

## Cockpit Surface

IntelligencePanel now shows:
- Spine-Native Propagation status (ACTIVE / NOT WIRED)
- Targets registered count
- Processed outcomes count
- Total propagations count

## Success Criteria

| # | Criterion | Met |
|---|-----------|-----|
| 1 | GovernedExecutionSpine emits OutcomeCommitted after verified success | YES |
| 2 | GovernedExecutionSpine emits OutcomeFailed after failed execution | YES |
| 3 | ParallelPropagationEngine runs automatically from spine events | YES |
| 4 | Trial/campaign code does not manually trigger propagation | YES |
| 5 | Propagation is idempotent (composite key) | YES |
| 6 | Propagation failures are isolated and visible | YES |
| 7 | Duplicate OutcomeCommitted events do not double-count | YES |
| 8 | At least 2 real template-guided improvements succeed | YES (3/3) |
| 9 | Template confidence updates from real reuse | YES (0.6→1.0) |
| 10 | Agent capability reliability updates from real outcomes | YES (1.0) |
| 11 | WorldModel/Contradiction/Readiness updates | YES |
| 12 | Cockpit exposes spine-native propagation state | YES |
| 13 | Governance preserved across all mutations | YES |
| 14 | No direct mutation bypass occurs | YES |

## Architecture Impact

The spine is now the source of mutation truth AND propagation truth. When governed execution completes:

1. OutcomeCommitted fires automatically
2. ParallelPropagationEngine runs automatically (10 targets, 2 waves)
3. All downstream subsystems update automatically
4. No caller needs to remember to propagate

Manual propagation is eliminated. Spine-native propagation is organism behavior.

## Remaining Blockers

None for this phase. Candidate queue (`data/umh/trials/phase9_5_candidate_queue.json`) has 20 items for future campaigns.

## Next Highest-Leverage Step

Run real template-guided campaigns against the 20 queued candidates using the spine-native path. Focus on the 1 medium-severity contradiction (execution_journal zero-byte file) and the 43 dependency graph orphans.
