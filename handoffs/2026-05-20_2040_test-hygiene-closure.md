# Handoff — 2026-05-20 Test-Hygiene Closure

## Status: COMPLETE

Follows: `2026-05-20_1930_layer3.1-closure.md`

Delta update on top of the Layer 3.1 closure handoff. Test-hygiene
merge closes all downstream test debt from Layer 3.1 sovereignty
cleanup.

## What Changed

**Merge commit**: `4e299a1e` on `main` (test-hygiene-restore-baseline)
**Feature commit**: `c73d4191`
**Scope**: 39 edits in `tests/test_ea_final.py` (1 file changed,
39 insertions, 39 deletions)

Spec estimated ~21 mechanical edits. Actual was 39 lines touched
(+85% over spec). Audit-undercount sample #9 — consistent with the
1.5x–3x magnification pattern documented in the Layer 3.1
retrospective.

### Per-class disposition

| Old Class | New Class | Action | Items |
|---|---|---|---|
| `TestDripMatrix` | `TestTaskYieldMatrix` | FIX | 4 |
| `TestBuybackRate` | `TestFounderRate` | FIX | 4 |
| `TestLeveragePatterns` | (unchanged) | NO-OP | 7 |
| `TestPerfectWeek` | `TestIdealWeek` | FIX | 3 |

`TestLeveragePatterns` was listed as broken in the prior handoff but
already imported from the correct path (`understanding.patterns.leverage_patterns`).
It was being skipped as collateral from the 11 dead `--deselect` flags.
All 7 tests pass without edits.

Module docstring updated: "Dan Martell framework tools" → "founder
leverage tools" (attribution that survived Merge 7's grep — see
findings below).

### Baseline progression

| Checkpoint | Passed | Deselected |
|---|---|---|
| Pre-Layer-3.1 | 73 | 11 |
| Post-Layer-3.1 (Merge 7) | 66 | 18 |
| **Post-test-hygiene** | **84** | **0** |

Net +11 over pre-Layer-3.1 starting point. Zero deselected items.

## New Findings

### Full suite is ~3993 tests, not 84

The "66 passed, 18 deselected" baseline from the Layer 3.1 handoff
was a regression-scoped run (two test files). The full repo suite
collects ~3993 items across all test files.

### 17 pre-existing test failures

Full suite run: 3968 passed, 17 failed, 8 skipped. All 17 failures
are pre-existing — file-not-found errors for removed modules,
attribute errors for missing handlers, stale proof assertions. None
introduced by this merge. Breakdown:

- `test_actuator_maturity_v1.py` — 2 failures (FileNotFoundError, removed core files)
- `test_gws_to_canonical_ingestion_v1.py` — 1 failure (stale proof document ID)
- `test_live_runtime_identity_v1.py` — 5 failures (missing `handlers.substrate_command_handler`)
- `test_persistent_substrate_continuity_engine_v1.py` — 1 failure (missing registry module)
- `test_registry_propagation_integrity_v1.py` — 3 failures (FileNotFoundError, removed files)
- `test_relay_execution_transport_v1.py` — 4 failures (missing `core.workstation.relay_execution_transport_v1`)
- `test_work_state.py` — 1 failure (assertion boundary drift, `20.0 <= 10.0`)

### 1 collection error

`tests/integration/transport/test_day_discord_detect.py` — missing
`import os` at module level. 1-line fix. Confirmed pre-existing on
main prior to this merge.

### Docstring as sovereignty surface

The module docstring at the top of `test_ea_final.py` contained
"Dan Martell framework tools" — external-name attribution that
survived Merge 7's full-repo grep. File-level docstrings should be
grepped as a distinct surface from line-level attribution in future
sovereignty audits.

## Verification Gates

| Gate | Result |
|---|---|
| py_compile | PASS |
| All renamed imports resolve | PASS |
| test_ea_final.py (24/24) | PASS |
| Full suite (3968 passed, 17 pre-existing failures) | PASS |
| Sovereignty grep (zero stale vocabulary) | PASS |
| uvicorn /api/umh/health | Healthy |

## Updated Deferred Queue

### CLOSED by this merge

- **Test-hygiene merge** — all Layer 3.1 downstream test debt resolved

### Still deferred (unchanged from prior handoff)

- **Archive-hygiene merge** — 37+ files in vault/, archive/, data/umh/traces/ (Bucket D). Dormant data, no runtime risk, low priority.
- **Discord command identifiers** — `!buyback`, `!drip`, `!perfectweek`. User-facing breaking change, requires separate decision.
- **6 open architecture questions** — in /tmp/layer3_unified_architecture.md (volatile).
- **Architecture doc merge** — pending.
- **Layer 3 Phase 1 implementation** — pending priority pick.

### NEW deferred items

- **1-line fix: test_day_discord_detect.py** — missing `import os` causes collection error. Trivial, candidate for next session.
- **17 pre-existing test failures** — broader test-cleanup scope across 7 test files. Not urgent, not blocking. Worth a dedicated test-debt session when prioritized.

## Vocabulary Library

Unchanged. All renames applied in this merge map to existing entries
in the Layer 3.1 vocabulary mappings table
(`/opt/OS/10_Wiki/LAYER_3.1_SOVEREIGNTY_CLEANUP.md` Section 3).
No new mappings introduced.

## What's NOT Next

No auto-prioritized queue. Next session picks priority. The deferred
items above are listed for context, not as a queue.

## Worktree State

All worktrees removed. Only `/opt/OS` (main) remains.
`git worktree list` returns single entry.
