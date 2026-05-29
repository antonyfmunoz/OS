# Phase 9.5 Baseline Snapshot

**Commit:** `f34841e22412dcb93c9b1a3208f37dad7801bd0a`
**Branch:** `main`
**Timestamp:** 2026-05-29

## Readiness

| Dimension   | Score |
|-------------|-------|
| Composite   | 28.3  |
| Execution   | 31.0  |
| Governance  | 30.0  |
| Deployment  | 26.0  |
| Operator    | 62.5  |
| Memory      | 0.0   |
| Composition | 0.0   |

## Contradictions

| Severity | Count |
|----------|-------|
| Medium   | 1     |
| Info     | 14    |
| **Total**| **15**|

## World Model

- Entities: 70
- Dependency graph edges: 32
- Dependency graph orphans: 43

## Organism State

| Metric                     | Value |
|----------------------------|-------|
| Outcome records            | 1     |
| Memory candidates          | 0     |
| Template candidates        | 0     |
| Promoted templates         | 0     |
| Agent capability profiles  | 0     |
| Agent capabilities tracked | 0     |
| Propagation events         | 0     |
| Propagation targets        | 0     |
| Execution journal entries  | 0     |

## Spine-Native Propagation

- **Wired:** No
- **Status:** Daemon does not inject ParallelPropagationEngine into GovernedExecutionSpine

## Key Gap

The GovernedExecutionSpine accepts `propagation_engine` as an optional parameter
and already has `_emit_outcome()` wiring, but the OrganismDaemon constructs the
spine without a propagation engine. This means propagation is only triggered by
manual calls from trial/campaign code, not automatically from the spine.

Phase 9.5 fixes this by wiring the propagation engine into the daemon and
removing manual propagation calls from campaign code.
