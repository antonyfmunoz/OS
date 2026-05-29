# Phase 9.5 Baseline Snapshot

**Captured:** 2026-05-29 10:09:36 UTC
**Commit:** 60bbceed03df03e16a3be5c1f8093db302742fa4
**Branch:** worktree-unified-channel-notifications

## Metrics

| Metric | Value |
|--------|-------|
| Readiness Score | 28.3 |
| Contradictions (total) | 15 |
| Contradictions (medium) | 1 |
| Contradictions (info) | 14 |
| World Model Entities | 70 |
| Dependency Graph Edges | 32 |
| Dependency Graph Orphans | 43 |
| Outcome Records | 0 |
| Memory Candidates | 0 |
| Template Candidates | 0 |
| Promoted Templates | 0 |
| Agent Capability Profiles | 0 |
| Propagation Events | 0 |
| Execution Journal Entries | 0 |
| Propagation Targets | 0 |
| Composition Template Index | available |
| Cockpit Status | operational |

## State Summary

Before Phase 9.5:
- GovernedExecutionSpine emits generic `envelope_completed` event only
- ParallelPropagationEngine exists but is never called
- OutcomeCommitted/OutcomeFailed events are defined but never created
- Trial/campaign code records outcomes manually through OutcomeLearningLoop
- No spine-native propagation path exists
