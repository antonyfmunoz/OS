# Sprint 5 — Documentation Truth

**Date:** 2026-05-27
**Branch:** `worktree-sprint5-doc-truth`
**Status:** Complete

## Problem

After convergence (2026-05-23), several key docs still referenced
pre-convergence directory structure (`eos_ai/`, `core/`), nonexistent
paths (`runtime/.env`), removed names (`AgentOS`), and a broken
session resume snippet that referenced a nonexistent field (`ctx.stage`).

## Assessment

- **README.md** — stale install instructions, old directory structure
- **docs/SYSTEM_ARCHITECTURE.md** — `runtime/.env` path (fixed in Sprint 1 code, not docs)
- **docs/system/current_system_status.md** — pre-convergence directory table
- **docs/corporate-structure.md** — AgentOS reference
- **.claude/CLAUDE.md** — session resume called `load_context_from_env()` (fail-closed)
  and referenced `ctx.stage` (field doesn't exist)
- **418 broken wikilinks** in `knowledge/` — 404 are auto-generated entity→summary
  cross-references (machine-generated, not hand-written), 14 are real content links
  (mostly `[[cloud]]` references to repo-root `cloud.md`)
- **52 ops docs** reference `eos_ai/` — these are historical phase records documenting
  completed work; mass-rewriting would break their archival value

## Changes

### 1. README.md
- Removed stale `curl` install command with `[repo]` placeholder
- Fixed `eos_ai/.env` → `.env`
- Replaced pre-convergence directory structure with post-convergence layout

### 2. docs/SYSTEM_ARCHITECTURE.md
- Fixed `runtime/.env` → `.env` in connection strings section

### 3. docs/system/current_system_status.md
- Updated system identity section (removed `eos_ai/` and `core/` references)
- Replaced directory architecture table with post-convergence layout
- Updated timestamp to 2026-05-27

### 4. docs/corporate-structure.md
- Removed `AgentOS` from SaaS product list

### 5. .claude/CLAUDE.md (session resume)
- Changed `load_context_from_env()` → `try_load_context_from_env()`
- Removed `ctx.stage` (field doesn't exist on `EntrepreneurOSContext`)
- Added graceful fallback when env vars not set

### 6. Deliberately NOT changed
- 52 `docs/operations/` files referencing `eos_ai/` — historical phase records
- 404 auto-generated broken wikilinks in `knowledge/entities/` — machine-generated
  cross-references, not navigational docs
- `docs/canonical/umh_synthesis.md` `runtime/.env` reference — documenting the Sprint 1
  bug discovery, historically accurate

## Sprint 4 regression fix (bundled)

Sprint 4 untracked `data/runtime/` (generated artifacts). Two test files
had `TestExampleArtifacts` classes that asserted file existence without
skip guards — 13 failures total (6 in transformation_state_ledger, 7 in
interpretation_engine_v1).

Fix: added `_require_example()` helper with `self.skipTest()` to both:
- `tests/test_transformation_state_ledger.py`
- `tests/test_interpretation_engine_v1.py`

Tests now skip gracefully when runtime artifacts aren't on disk.

## Verification tests

`tests/test_sprint5_doc_truth.py` — 9 tests:
- README: no `eos_ai/.env`, has post-convergence dirs, no placeholder URLs
- CLAUDE.md: uses `try_load_context_from_env`, no `ctx.stage`
- SYSTEM_ARCHITECTURE.md: no `runtime/.env`
- current_system_status.md: has post-convergence dirs
- corporate-structure.md: no AgentOS

## Files modified

- `README.md`
- `.claude/CLAUDE.md`
- `docs/SYSTEM_ARCHITECTURE.md`
- `docs/system/current_system_status.md`
- `docs/corporate-structure.md`
- `tests/test_sprint5_doc_truth.py` (new)
- `tests/test_transformation_state_ledger.py` (skip guards)
- `tests/test_interpretation_engine_v1.py` (skip guards)
- `docs/audits/convergence/20260527-sprint5-doc-truth.md` (new)
