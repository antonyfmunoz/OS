# Organism Phase 3 — Governed Recursive Execution Economy

**Date:** 2026-05-27
**Status:** Complete
**Tests:** 39 passed, 0 failed

## What Was Built

### Phase 3A: Execution Economy (`substrate/organism/execution_economy.py`)

Seven new types tracking execution economics:
- **RuntimeBenchmark** — per-runtime, per-task-class performance tracking (success rate, avg latency, avg quality, cost efficiency, leverage score)
- **ExecutionCost** — cost breakdown (compute, token, wall-clock, subscription flag)
- **ExecutionValue** — value metrics (quality, completeness, correctness, time saved)
- **RuntimePerformanceProfile** — aggregated benchmarks per runtime across task classes
- **TaskExecutionProfile** — which runtimes are best for which task classes
- **ExecutionDecisionRecord** — full decision context per execution (runtime selected, alternatives, cost, value, governance class, verification result, leverage score)
- **ExecutionEconomy** — central tracker that maintains profiles and records

The economy enables RuntimeGraph to progressively learn which runtimes perform best for which task classes. Leverage scoring formula: `0.30 * quality + 0.25 * success + 0.25 * cost_efficiency + 0.20 * latency_efficiency`.

### Phase 3B: Recursion Governance (`substrate/organism/recursion_governance.py`)

Bounded recursive execution control:
- **RecursionLimits** — configurable hard limits (depth=5, objectives=20, work_units=50, budget=$10, wall_clock=3600s, autonomous_scope=10)
- **RecursionState** — tracks cumulative resource consumption
- **RecursionGovernor** — circuit breaker that checks limits before every recursive operation
- **EscalationEvent** — logged when limits are approached (WARNING at 80%) or exceeded (BLOCK)
- **Kill switch** — external signal to halt all autonomous execution immediately
- **Approval matrix** — per-execution-class approval requirements (DETERMINISTIC=none, AGENT=notify, PRODUCTION_IMPACT=block)

Six execution classes with distinct authority rules:
1. DETERMINISTIC — no approval needed
2. AGENT — notification only
3. ADVISOR_DELEGATION — notification only
4. RECURSIVE_IMPROVEMENT — requires approval
5. EXTERNAL_LEVERAGE — requires approval
6. PRODUCTION_IMPACT — blocked (requires explicit override)

### Phase 3C: Advisor Hierarchy (`substrate/organism/advisor_hierarchy.py`)

Governed recursive advisory orchestration:
- **AdvisorNode** — represents any advisor in the hierarchy with explicit scope, authority, budget, recursion limits, spawn limits, reporting cadence, success criteria, shutdown conditions, escalation policy
- **AdvisorHierarchy** — manages the tree with five governance invariants:
  1. Every non-primary advisor has a parent (no unmanaged spawning)
  2. Child scope <= parent scope (scope narrowing)
  3. Child budget <= parent remaining budget (budget cascading)
  4. Child recursion limit <= parent recursion limit - 1 (recursion inheritance)
  5. Spawn count tracked against spawn limit

Four advisor types: PrimaryAdvisor (instance-scoped), DomainAdvisor (company/function), TeamAdvisor (team/workcell), TaskAdvisor (temporary mission).

Primary Advisor is the only default user-facing interface. Sub-advisors are internal orchestration organs.

### Phase 3D: Cockpit Organism Observability API

17 new API endpoints added to `transports/api/cockpit.py`:
- `GET /organism/economy` — execution economy metrics
- `GET /organism/economy/records` — recent execution decision records
- `GET /organism/economy/task-profile/{task_class}` — runtime rankings per task
- `GET /organism/recursion` — recursion governance state
- `GET /organism/recursion/escalations` — escalation event log
- `POST /organism/recursion/kill` — activate kill switch
- `POST /organism/recursion/resume` — deactivate kill switch
- `GET /organism/advisors` — full advisor hierarchy
- `GET /organism/advisors/tree` — nested tree structure
- `GET /organism/advisors/overdue` — advisors with overdue reports
- `GET /organism/leverage` — leverage assimilation status
- `GET /organism/leverage/artifacts` — all assimilation artifacts
- `GET /organism/snapshot` — full organism snapshot (objectives, runtimes, workcells, bottlenecks)
- `GET /organism/topology` — runtime topology with capabilities and health

### Phase 3E: External Leverage Assimilation Maps

Five structured leverage maps in `data/audits/leverage_maps/`:

| Source | Evidence | Leverage Gain | Status |
|--------|----------|---------------|--------|
| cortextOS | PARTIAL | 0.0 | Fully absorbed in Phase 2 |
| Polsia | CLAIMED | 0.15 | Gap: results-on-wake UX tightening |
| Karpathy Claude.md | VERIFIED | 0.0 | All patterns already operational |
| Claude Code Ecosystems | VERIFIED | 0.05 | Minor UX improvements possible |
| Codex/OpenCode/Hermes | PARTIAL | 0.20 | Gaps: async submission, sandbox isolation |

Key insight: UMH has already absorbed the high-value patterns from all five sources. The remaining leverage gaps are:
1. **Async task submission** (from Codex pattern) — coordinator is synchronous
2. **Sandbox isolation** (from Codex pattern) — work_packet.py has types but no enforcement
3. **Results-on-wake UX** (from Polsia positioning) — morning_brief exists but not tight

### Phase 3F: Test Coverage

39 tests across 6 test classes:
- TestExecutionEconomy (7 tests) — record creation, profile tracking, scoring, leverage
- TestRecursionGovernance (11 tests) — all limit types, kill switch, approval matrix, escalation log
- TestAdvisorHierarchy (11 tests) — spawning, scope, budget, recursion, termination, tree
- TestCockpitObservability (3 tests) — snapshot, daemon imports, status structure
- TestExternalLeverageMapSchema (2 tests) — pipeline output, evidence levels
- TestStructuralIntegrity (5 tests) — no product coupling, no instance leaks, no oversized files, canonical types, dependency direction

## How Governance Bounds Recursion

The RecursionGovernor enforces six independent limits simultaneously:
1. **Depth** — maximum nesting of recursive calls (default: 5)
2. **Objectives** — maximum concurrent decomposed objectives (default: 20)
3. **Work Units** — maximum total work units per mission (default: 50)
4. **Budget** — maximum USD spend before requiring approval (default: $10)
5. **Wall Clock** — maximum elapsed time (default: 3600s)
6. **Autonomous Scope** — maximum autonomous operations without human check-in (default: 10)

Warning escalations fire at 80% of any limit. Block escalations fire at 100%.

The kill switch immediately halts all autonomous execution with no delay.

## How Runtime Economy Improves Leverage

Each execution produces an ExecutionDecisionRecord. The economy aggregates these into RuntimePerformanceProfiles and TaskExecutionProfiles. Over time:
- Runtimes that consistently succeed for a task class get higher leverage scores
- Runtimes with lower cost and latency are preferred when quality is equal
- The `best_runtime_for_task()` method returns the highest-leverage runtime for any task class
- This feeds back into RuntimeGraph scoring for progressively better selection

## How Advisor Hierarchy Works

```
PrimaryAdvisor (instance scope, $100 budget, 5 recursion, 20 spawns)
├── DomainAdvisor: Sales (domain scope, $20 budget, 4 recursion)
│   ├── TeamAdvisor: Outreach Team ($5 budget, 3 recursion)
│   └── TaskAdvisor: "Close Deal X" ($2 budget, 2 recursion)
├── DomainAdvisor: Engineering (domain scope, $30 budget, 4 recursion)
│   └── TeamAdvisor: Backend Team ($10 budget, 3 recursion)
└── DomainAdvisor: Marketing (domain scope, $15 budget, 4 recursion)
```

Each advisor has:
- Explicit scope (narrows down the tree)
- Budget that cascades from parent
- Recursion limit that decrements per level
- Spawn limit that constrains children
- Reporting cadence for oversight
- Escalation policy that routes failures up

## How Cockpit Observes the Organism

The 17 new endpoints provide:
- **Economy view**: cost/value/leverage per runtime, per task class
- **Recursion view**: current depth, budget spent, escalation log, kill switch control
- **Advisor view**: full hierarchy tree, overdue reports, scope violations
- **Leverage view**: assimilation artifacts and scored primitives
- **Snapshot view**: point-in-time organism state (objectives, runtimes, workcells, bottlenecks)
- **Topology view**: all runtimes with capabilities and health

## Remaining Bottlenecks

1. **Async execution** — OrganismCoordinator.execute_objective() is synchronous. For distributed execution, async task submission with polling would compress time.
2. **Sandbox enforcement** — work_packet.py defines EnvironmentType but no runtime sandbox enforcement exists yet. Required for safe Beast node execution.
3. **Economy persistence** — ExecutionEconomy is in-memory only. Crash recovery requires serialization to disk/Neon.
4. **Governor persistence** — RecursionGovernor state resets on restart. Should persist limits and state.
5. **Hierarchy persistence** — AdvisorHierarchy is in-memory. Production use needs durable storage.

## Next Sprint Ranked by Time-Compression Impact

1. **Economy persistence + RuntimeGraph feedback loop** — wire economy leverage scores into graph scoring. Highest leverage: every future execution gets smarter. (estimated: 4h)
2. **Async coordinator** — convert execute_objective to async with polling. Enables parallel multi-objective execution. (estimated: 6h)
3. **Governor persistence** — serialize limits/state to disk. Required for crash-safe governance. (estimated: 2h)
4. **Hierarchy persistence** — serialize advisor tree to disk/Neon. Required for cross-session advisor continuity. (estimated: 3h)
5. **Sandbox enforcement** — implement runtime sandbox for Beast node execution. Required for safe autonomous code execution on GPU node. (estimated: 8h)
6. **Results-on-wake UX** — tighten morning_brief to automatically surface overnight execution results. (estimated: 3h)

## Files Created/Modified

New files:
- `substrate/organism/execution_economy.py` (280 lines)
- `substrate/organism/recursion_governance.py` (290 lines)
- `substrate/organism/advisor_hierarchy.py` (310 lines)
- `substrate/organism/tests/test_phase3.py` (480 lines)
- `data/audits/leverage_maps/cortextos.json`
- `data/audits/leverage_maps/polsia.json`
- `data/audits/leverage_maps/karpathy_claude_md.json`
- `data/audits/leverage_maps/claude_code_ecosystems.json`
- `data/audits/leverage_maps/codex_opencode_hermes.json`
- `docs/audits/convergence/organism_phase3_governed_execution_economy.md`

Modified files:
- `substrate/canonical_types.py` — registered 7 new types
- `transports/api/cockpit.py` — added 17 organism observability endpoints

## Validation Results

- [x] 39 Phase 3 tests passing
- [x] All modules compile clean
- [x] No instance leaks in Phase 3 files
- [x] No product dependency coupling
- [x] No files over 3000 lines
- [x] All new types registered in canonical_types.py
- [x] Dependency direction: substrate never imports from transports/services
- [x] No hardcoded DEX/Antony/company names in substrate
