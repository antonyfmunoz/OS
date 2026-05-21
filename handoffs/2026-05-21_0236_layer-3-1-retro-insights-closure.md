# Handoff — 2026-05-21 Layer 3.1 Retro Insights Closure

## Status: COMPLETE

Follows: `2026-05-21_0221_remove-dead-excludes-array-closure.md`

Promoted four systemic insights from today's session into the
Layer 3.1 retrospective at `10_Wiki/LAYER_3.1_SOVEREIGNTY_CLEANUP.md`.
Each insight is a calibration finding about the work itself — not
about a specific code area — with reusable rules for future sessions.

## What Changed

**Branch commit**: `2358bef5` on `layer-3-1-retro-insights`
**Merge commit**: `ae74b407` on `main` (--no-ff)
**Push**: `667a8b8b..ae74b407` to `origin/main`
**Scope**: 1 file changed, 96 insertions, 0 deletions

### Files modified

| File | Change |
|------|--------|
| `10_Wiki/LAYER_3.1_SOVEREIGNTY_CLEANUP.md` | +96 lines: §2 "Post-Closure Corroboration" subsection + §7 items #5, #6, #7 |

### §2 addition: Post-Closure Corroboration

New subsection documenting that the audit-undercount law held across
three subsequent cleanup arcs:

| Arc | Estimate | Actual | Ratio |
|---|---|---|---|
| Archive Bucket D (dormant files) | ~40 | 1,122 | ~28x |
| Q1 codebase pages migration | 2,416 | 5,805 | 2.4x |
| Sovereignty-grep tool itself | 19 | 20 | +1 (recursive) |

Includes the recursive case where the audit tool itself undercounted
by 1 (docs/migrations/ hit below scan window pre-Q2-Q6).

### §7 additions: Strategic Learnings #5, #6, #7

| Item | Title | Source | Rule |
|------|-------|--------|------|
| #5 | Post-migration import verification is non-optional | fix-spine-import merge | Run `python3 -c "from <pkg> import <mod>"` for every module post-reorg |
| #6 | Verification tools can mask their own failures | pytest --tb=no masking | Check collection separately via `pytest --collect-only` |
| #7 | Dead code in shell scripts has no natural predator | remove-dead-excludes-array merge | Audit for old scaffolding when tool choice changes mid-implementation |

### Verification

- Sovereignty grep: **20 hits, all DATA** (baseline preserved)
- Doc line count: 527 (was 432)
- Header nesting: correct (all ### under parent ##)
- Markdown tables: well-formed

## Deferred Items

### CLOSED by this merge
- Four "consider for LAYER_3.1 retro" insights (audit-undercount law promotion, post-migration import audit pattern, pytest --tb=no masking, shell dead-code danger)

### UNCHANGED
- Layer 3 Phase 1 implementation (heavyweight, fresh session)
- Discord command identifiers (`!buyback`, `!drip`, `!perfectweek`) — UX decision
- eos_ai/ status — confirmed dead (0 imports, untracked), safe to delete
- Snapshot-graph tarball script (low priority)
- Flaky ingestion test — `test_completes_full_cycle` uses LLM-dependent assertion counts

### NEW (raised during 20-hit scan, not addressed)
- **Frozen pre-3.1 audit docs** containing `martell_patterns.py` references in audit/classification files (data/audits/2026-05-14_runtime_layer_classification.md 5 hits, docs/audits/file_classification_table.md 1 hit, docs/audits/essentialism_audit.md 2 hits). Technically DATA (historical system memory) but represent a degenerate category — internal vocabulary that no longer exists. Consider future exclusion category parallel to `docs/migrations/`, or per-doc DATA confirmation. Small/medium scope.

## What's NOT Next

No auto-prioritized queue. Next session picks priority.
