# Handoff — 2026-05-20 Archive-Hygiene Closure

## Status: COMPLETE

Follows: `2026-05-20_2110_import-os-fix-closure.md`

Closes Bucket D from Layer 3.1 Merge 7 grep — the last deferred
cleanup item with active-code implications. All remaining sovereignty
grep hits are now DATA per Leverage Principle.

## What Changed

**Merge commit**: `d7d1fa4c` on `main` (archive-hygiene-bucket-d)
**Feature commits**: `4502223d`, `a204e8e5`, `04172e63`
**Scope**: 1125 files moved, 2 files created, 0 active code modified

### Stage 1: MOVE operations

| Source | Destination | Files | Sovereignty hits removed |
|---|---|---|---|
| `archive/umh_reference/` | `_archive/umh_reference/` | 899 | 33 |
| `archive/tools_duplicate/` | `_archive/tools_duplicate/` | 211 | 3 |
| `docs/superpowers/plans/` | `_archive/superpowers_plans/` | 12 | 280 |
| **Total** | | **1122** | **316** |

### Stage 2: Sovereignty grep codification

Two new files:
- `scripts/sovereignty-grep.sh` — one-command canonical audit
- `10_Wiki/SOVEREIGNTY_GREP_EXCLUSIONS.md` — per-exclusion rationale

Exclusion list covers 14 path patterns across 5 categories:
tooling, session records, conversation transcripts, historical
archives, and auto-generated indices.

Implementation note: `rg` not installed on VPS. Script uses `grep`
with `--exclude-dir` for directory-level and pipe `grep -v` for
path-specific exclusions.

### Stage 3: Graph regeneration

Ran `scripts/update-graph` + `scripts/merge_graphs.py`. Graph
rebuilt fresh (303 Python files, 7615 edges) but auto-generated
files still carry stale `eos_ai/` entries — the graph scanner is
additive (does not prune entries for deleted files). These entries
are handled by the exclusion list, not manual stripping.

## New Findings

### Graph scanner is additive

The codebase graph scanner does not prune entries for files that no
longer exist on disk. `eos_ai/martell_patterns.py` and 10 other
deleted `eos_ai/` files persist in the graph JSON across rebuilds.
Not a sovereignty issue (excluded from canonical grep) but a graph
hygiene issue for a future session.

### eos_ai/ Python files are fully clean

Zero hits in `eos_ai/` on disk. The `eos_ai/` directory has zero
`.py` files remaining — all were moved or deleted during prior
cleanup phases.

### docs/superpowers/plans/ was not in original Bucket D

The 280-hit cluster in `docs/superpowers/plans/` was not classified
as Bucket D in the Merge 7 grep (it was in `docs/`, not
`data/`/`archive/`/`vault/`). Surfaced during the spec-phase
re-grep. Moved to `_archive/` alongside the classified Bucket D
material.

### Steady-state residual: 20 hits

Canonical sovereignty grep now returns 20 hits, all DATA:
- 5 hits in `data/audits/` — historical audit report tables
- 3 hits in `skills/tools/` — `hormozi` as Instagram monitoring target
- 2 hits in `data/drive_doc_ingestion_tab_aware/` — ingested user docs
- 1 hit in `understanding/knowledge/knowledge_integrator.py` — docstring example
- 1 hit in `data/system/runtime_domain_module_map.json` — module map
- 1 hit in `.planning/codebase/INTEGRATIONS.md` — competitor list
- 1 hit in `09_Content/` — original content idea title
- 1 hit in `10_Wiki/SOVEREIGNTY_GREP_EXCLUSIONS.md` — the exclusion doc itself
- 1 hit in `data/audits/` — exhaustive system audit
- 4 remaining from historical audit classification tables

All 20 classified as DATA per Leverage Principle. Zero IDENTITY
violations remain.

## Verification Gates

| Gate | Result |
|---|---|
| Regression suite (88/0/0) | PASS |
| sovereignty-grep.sh executable | PASS |
| sovereignty-grep.sh count | 20 (all DATA) |
| uvicorn /api/umh/health | Healthy |

## Updated Deferred Queue

### CLOSED by this merge

- **Archive-hygiene merge (Bucket D)** — all Layer 3.1 deferred archive cleanup resolved
- **Sovereignty grep codification** — canonical tool now exists

### Still deferred (unchanged)

- **Discord command identifiers** — `!buyback`, `!drip`, `!perfectweek`. User-facing breaking change, requires separate decision.
- **6 open architecture questions** — in /tmp/layer3_unified_architecture.md (volatile).
- **Architecture doc merge** — pending.
- **Layer 3 Phase 1 implementation** — pending priority pick.
- **17 pre-existing test failures** — broader test-cleanup scope across 7 test files.

### NEW deferred items

- **Graph pruning** — additive scanner leaves stale entries for deleted files. Not urgent, cosmetic.

## Layer 3.1 Downstream Closure Summary

With this merge, all downstream artifacts of Layer 3.1 sovereignty
cleanup are now closed:

| Item | Closed in | Commit |
|---|---|---|
| Test-hygiene (4 broken classes) | test-hygiene-restore-baseline | `4e299a1e` |
| Collection error (import os) | fix-import-os-test-day-discord | `ef6ab7fc` |
| Archive-hygiene (Bucket D) | archive-hygiene-bucket-d | `d7d1fa4c` |
| Sovereignty grep codification | archive-hygiene-bucket-d | `d7d1fa4c` |

Remaining deferred items (Discord commands, architecture questions,
Layer 3 Phase 1) are not downstream of Layer 3.1 — they are
independent work items.

## What's NOT Next

No auto-prioritized queue. Next session picks priority.

## Worktree State

All worktrees removed. Only `/opt/OS` (main) remains.
