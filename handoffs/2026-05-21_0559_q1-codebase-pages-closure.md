# Handoff — 2026-05-21 Q1 Codebase Pages Migration

## Status: COMPLETE

Follows: `2026-05-20_2200_archive-hygiene-closure.md`

Resolves Q1 of the 6 Layer 3 architecture questions — the only Phase 1
implementation gate. Other 5 batched as far-phase direction confirms.

## What Changed

**Merge commit**: `ebcf068b` on `main` (q1-codebase-pages-migration)
**Feature commits**: `a7944569`, `8375d676`
**Scope**: 5,805 files deleted from 10_Wiki/codebase/, 12 files updated,
1 .gitignore entry added

Moved auto-generated codebase graph pages from `10_Wiki/codebase/` to
`data/codebase_pages/` and gitignored the new location.

## Vault Root Resolution

Gate check: `/opt/OS/.obsidian/` exists. Vault root is `/opt/OS/`.
TARGET locked: `data/codebase_pages/` (inside vault root, bare wikilinks
in palace room loci continue to resolve via filename match).

## Pruning Step (Commit 1 in spec — DROPPED)

`generate_obsidian()` already does `shutil.rmtree(WIKI_DIR)` + full
rebuild on every run (line 690 of `scripts/codebase_graph.py`). The
additive-staleness diagnosis was incorrect — the generator already
prunes by nuking the output directory. Git churn was the real problem,
not orphan files. Commit 1 dropped from the spec.

## Path Reference Updates

12 files updated (spec estimated 15 — the 3 self-references inside
`codebase_graph.py` were already handled in Commit 2):

| File | Change |
|---|---|
| scripts/codebase_graph.py | WIKI_DIR constant + 3 in-file doc refs |
| scripts/session_bootstrap.py | cloud.md load path + docstring |
| scripts/verify_knowledge_system.py | required doc + vault subdirs + file count |
| scripts/build_palace.py | docstring + palace index cloud link |
| scripts/vault_backlink_audit.py | skip directory |
| scripts/sovereignty-grep.sh | exclusion path |
| CLAUDE.md | cognition stack load order |
| cloud.md | knowledge graph table row |
| 10_Wiki/retrieval_rules.md | layer 2 link + bootstrap guarantee |
| 10_Wiki/cloud_palace.md | locus traversal instruction |
| 10_Wiki/SOVEREIGNTY_GREP_EXCLUSIONS.md | entry path + provenance note |
| skills/tools/obsidian_markdown/references/best_practices.md | codebase graph section |

Calibration: spec said "15 path references across consumers and docs."
Actual was 12 files / 16 individual line edits. The 3-file overcount was
because codebase_graph.py's 4 internal edits counted in Commit 2, not
Commit 3. The total edit count was accurate.

## Verification Gates

| Gate | Result |
|---|---|
| py_compile (4 scripts) | PASS |
| session_bootstrap.py --compact | PASS — `data/codebase_pages/cloud.md` resolves `[ok]` |
| verify_knowledge_system.py | PASS — 11/11, 0 warn, 0 fail |
| build_palace.py | PASS — palace generated fresh |
| sovereignty-grep.sh --count | PASS — 20 hits (unchanged) |
| Test suite | 19 failed / 3970 passed / 8 skipped (17 pre-existing + 2 order-dependent flakes, 0 new regressions) |
| update-graph output | PASS — 2,414 pages in data/codebase_pages/, 0 in 10_Wiki/codebase/ |
| git status post-regen | PASS — 0 codebase_pages entries (gitignored) |

## Net Effect

Before: every `scripts/update-graph` run produced ~7,000+ git status
entries (4,749 deleted + 1,361 untracked + 1,055 modified) in the
CANON wiki namespace.

After: `data/codebase_pages/` is gitignored. Graph regens produce
0 git noise from codebase pages. Only the JSON graph, palace, and
summary files appear in git status (these are tracked intentionally).

## Architecture Question Status

| # | Question | Status |
|---|---|---|
| Q1 | 10_Wiki/codebase/ migration | **CLOSED** — this merge |
| Q2 | Notion socket wiring timing | Deferred — far-phase direction confirm |
| Q3 | CU harness LLM integration | Deferred — far-phase direction confirm |
| Q4 | SCHEMA layer formalization | Deferred — far-phase direction confirm |
| Q5 | Cross-device diagnostic timing | Deferred — far-phase direction confirm |
| Q6 | Memory dedup on promotion | Deferred — far-phase direction confirm |

## Still Deferred

- Q2-Q6 batched as architecture doc confirm pass
- Discord command identifiers (`!buyback`, `!drip`, `!perfectweek`)
- Architecture doc merge (/tmp/layer3_unified_architecture.md)
- Layer 3 Phase 1 implementation
- 17 pre-existing test failures (+ 2 order-dependent flakes)
- Graph JSON pruning (stale entries for deleted files, cosmetic)
- snapshot-graph.sh tarball script (deferred from Q1 spec)

## What's NOT Next

No auto-prioritized queue. Next session picks priority.
