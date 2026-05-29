# Phase 9.5A — Baseline Reconciliation

## Date: 2026-05-29

## Active State

| Item | Value |
|------|-------|
| Active branch | `worktree-phase9-5a-spine-propagation` (forked from `main`) |
| Active commit | `39063a8c` (main HEAD, includes merged PR #36) |
| Main commit | `39063a8c` |
| Worktree commit | `39063a8c` (worktree from main) |
| Runtime commit | `39063a8c` (os-operator uses main) |
| Data root | `data/umh/organism/` |

## Baseline Counts

| Metric | Count | Source |
|--------|-------|--------|
| Outcome records (outcome_learning.jsonl) | 3 lines (1 outcome + 1 signal + 1 reliability) | `wc -l data/umh/organism/outcome_learning.jsonl` |
| Propagation events | 0 | No `data/umh/organism/propagation/` directory existed |
| Template candidates | 0 | `data/umh/organism/templates/` did not exist |
| Agent capability profiles | 2 (builder, researcher) | `ls data/umh/organism/agents/` |
| Memory candidates | 0 | `data/umh/organism/memory/` did not exist |

## Snapshot Discrepancy Explanation

The task mentioned two baseline snapshots showing different outcome record counts (0 vs 1).

**Explanation**: The 3 lines in `outcome_learning.jsonl` were created by Phase 9.4's test probe execution (commit `1ab0aa1f`). The "0 outcomes" snapshot was taken before the test probe ran; the "1 outcome" snapshot was taken after. Both are correct — they represent the state at different points during Phase 9.5 development.

The test probe created:
1. An outcome record (`id: 665cd00e`, action_type: `test_probe`, status: `success`)
2. A reliability signal (reliability updated from 0.500 to 1.000)
3. A reliability record (action_type: `test_probe`, value: 1.0)

## Propagation State at Baseline

- `ParallelPropagationEngine` code exists in `coherence_propagation.py`
- `propagation_wiring.py` exists with `build_propagation_engine()` factory
- `daemon.py` already calls `build_propagation_engine()` and passes it to `GovernedExecutionSpine`
- `governed_spine.py` already has `_emit_outcome()` calling `propagation.handle_outcome()`
- No propagation data directories existed on disk (no prior live propagation)
- Trial runner has zero manual propagation calls

## Reconciliation Status

**Reconciled.** Active target is `main` at `39063a8c` (includes merged PR #35 + PR #36). This pass adds:
- Bug fix: outcome_learning.py enum deserialization (was causing test failures)
- Bug fix: organism_bridge.py spine propagation status handler (was creating empty engine)
- Refreshed proof files with all criteria met
- Updated audit documentation
