# Handoff — 2026-05-21 Cleanup: Remove Dead eos_ai/ Directory

## Status: COMPLETE

Follows: `2026-05-21_1740_layer3-phase2-slice-e-closure.md`

Removes the eos_ai/ directory, closing a long-standing deferred queue
item tracked across multiple Phase 2 slices. The directory was confirmed
dead: zero tracked files in git, zero production imports, zero script/CI
references.

## What Changed

**Scope**: Filesystem cleanup only — zero git-tracked files remained.
Wave 6 (`8454a648`) already `git rm`'d all 459 files. What remained was
5 empty subdirectories and 1 untracked symlink (.env → ../runtime/.env).

No branch or merge was needed — there was nothing to commit. The cleanup
was a filesystem `rm` of untracked debris, plus a CLAUDE.md line removal.

### Files modified

| File | Change |
|------|--------|
| `.claude/CLAUDE.md` | Removed `eos_ai/` line from project structure section |

### Files removed (filesystem only, not git-tracked)

| Path | Type |
|------|------|
| `eos_ai/.env` | Symlink → ../runtime/.env |
| `eos_ai/interfaces/` | Empty directory |
| `eos_ai/platforms/` | Empty directory (contained empty `eos/` subdir) |
| `eos_ai/runtime/` | Empty directory |
| `eos_ai/substrate/` | Empty directory |
| `eos_ai/transport/` | Empty directory |

### Pre-deletion verification

| Check | Result |
|-------|--------|
| `grep "from eos_ai"` across production .py | 0 hits (60+ hits all in archive/) |
| `grep "import eos_ai"` across production .py | 0 hits (1 hit is string literal in shim_retirement_monitor.py) |
| `grep "eos_ai"` across .sh | 0 hits |
| `grep "eos_ai"` across .yml/.yaml/.toml | 0 hits |
| `git ls-tree HEAD eos_ai/` | Empty (0 tracked files) |
| `find eos_ai/ -type f` | 0 regular files |
| `find eos_ai/ -type l` | 1 symlink (.env) |
| 10_Wiki/ references | Historical/documentary only — palace candidates, wing page, migration logs, wikilinks to deleted graph entities. All stale; cleaned up on next graph rebuild. |

### Post-deletion verification

| Check | Result |
|-------|--------|
| Full test suite | 4276 passed, 1 failed (pre-existing LLM-dependent flaky), 3 skipped |
| Sovereignty grep | All DATA hits, no sovereignty issues |
| py_compile | N/A (no production .py files referenced eos_ai) |

## Deferred Items

### CLOSED this merge
- eos_ai/ deletion — long-standing dead-code item

### NEW priority candidates for next session
1. **Layer 3.1 retro update** — consolidate 7 accumulated insights into architecture doc §7 items #8-#14:
   - Predicate parser convention drift (`_gt_Npct` suffix reconstructs field name with `_pct`)
   - Cumulative-subset vs threshold escalation (test uses field-base matching)
   - Reconstruct-on-demand pattern (`_build_evidence()` as single extension point)
   - Advisor spec field-name drift: specs say `successful_execution_count`, code says `success_count`
   - Dict-vs-cast for fail-loud/discoverability
   - Birth-certificate-vs-medical-chart separation principle
   - Type-narrowing seam at registration + L1-skip as non-sequential algorithm validation
2. **Phase 3 investigation start** — Generalized Capability Discovery (repurpose TME pipeline for adapter capability discovery; will use manifest declarations as input per Slice E's separation principle)

### REMAINING operational queue
- Discord command identifiers (`!buyback`, `!drip`, `!perfectweek`) — UX decision
- Snapshot-graph tarball script (low priority)
- Frozen pre-3.1 audit docs with stale `martell_patterns.py` references (small/medium scope)
- Flaky `test_completes_full_cycle` (passed in Slice E run, failed this run due to Gemini 429; LLM-dependent, watch)

### Wiki references to eos_ai (stale, low priority)
Will self-clean on next `scripts/update-graph` run:
- `10_Wiki/palace/wings/eos_ai-wing.md` — wing page for deleted directory
- `10_Wiki/palace/candidates/cluster_000.md`, `cluster_001.md`, `cluster_002.md` — graph snapshots
- Various concept/entity/synthesis pages with `[[eos_ai-*]]` wikilinks — dangling refs

## What's NOT Next

No auto-prioritized queue. Next session picks priority.
