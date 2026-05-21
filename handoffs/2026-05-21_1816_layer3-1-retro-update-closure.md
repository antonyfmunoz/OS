# Handoff — 2026-05-21 LAYER_3.1 Retro §7 Update: Phase 2 Insights

## Status: COMPLETE

Follows: `2026-05-21_1756_cleanup-eos-ai-closure.md`

LAYER_3.1 retrospective §7 (Strategic Learnings) expanded from 7 to 18
items, consolidating all insights surfaced during Layer 3 Phase 2
(Slices A-E) and the eos_ai/ cleanup.

## What Changed

**Branch commit**: `47c3549b` on `layer3-1-retro-phase2-insights`
**Merge commit**: `84774ee4` on `main` (--no-ff)
**Push**: `d07f3ad1..84774ee4` to `origin/main`
**Scope**: 1 file changed, 255 insertions, 2 deletions
**Line count**: 528 → 780 (+252)

### Files modified

| File | Change |
|------|--------|
| `10_Wiki/LAYER_3.1_SOVEREIGNTY_CLEANUP.md` | Updated §7 intro (removed stale "Four observations" count), added items #8-#18 grouped into three categories with source SHAs, mechanisms, and generalizable rules |

### Items added

**Architectural Principles (#8-#12)**

| # | Title | Source |
|---|-------|--------|
| 8 | Reconstruct-on-demand beats stored derived state | Slice C (`49b313a5`) |
| 9 | Birth-certificate-vs-medical-chart separation | Slice E (`585be683`) |
| 10 | Type-narrowing seam at registration | Slice E (`585be683`) |
| 11 | Dict-vs-cast for fail-loud discoverability | Slice D (`70b44de5`) |
| 12 | L1-skip as non-sequential algorithm validation | Slice E (`585be683`) |

**Calibration Findings (#13-#15)**

| # | Title | Source |
|---|-------|--------|
| 13 | Predicate parser convention drift | Slice B (`7e3dd5e6`) |
| 14 | Cumulative-subset vs threshold escalation | Slice B (`7e3dd5e6`) |
| 15 | Specs drift, code is truth | Slice C (`49b313a5`) |

**Process Insights (#16-#18)**

| # | Title | Source |
|---|-------|--------|
| 16 | Worktree rename CWD lock | Slice E (`585be683`) |
| 17 | `git ls-tree HEAD` as definitive deadness check | eos_ai cleanup (`d07f3ad1`) |
| 18 | Verify-then-act saves wasted ceremony | eos_ai cleanup (`d07f3ad1`) |

### Verification

- Sovereignty grep: DATA-only hits, no new issues
- Full test suite: 4145 passed in worktree (known module-cache offset); post-merge on main baseline preserved at 4277
- 1 known flaky failure (`test_completes_full_cycle`) — LLM-dependent, unrelated
- py_compile: N/A (markdown-only change)

## Deferred Items

### CLOSED this merge
- LAYER_3.1 retro insight consolidation — all Phase 2 insights now pinned

### NEXT priority
- **Phase 3 investigation start** — Generalized Capability Discovery. Repurpose TME pipeline for adapter capability discovery; per Slice E's birth-certificate/medical-chart separation (item #9), discovery updates manifests not health records.

### REMAINING operational queue
- Discord command identifiers (`!buyback`, `!drip`, `!perfectweek`) — UX decision
- Snapshot-graph tarball script (low priority)
- Frozen pre-3.1 audit docs with stale `martell_patterns.py` references (small/medium scope)
- Flaky `test_completes_full_cycle` — now characterized as Gemini 429 rate-limit failure; may respond to backoff/retry rather than test logic changes

## What's NOT Next

No auto-prioritized queue. Next session picks priority.
