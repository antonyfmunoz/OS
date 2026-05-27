# Sprint 4 — Data/Log Hygiene

**Date:** 2026-05-27
**Branch:** `worktree-sprint4-data-hygiene`
**Status:** Complete

## Problem

3,683 files were tracked in git that should not be:
- 3,482 files in `saas/node_modules/` (~100MB of npm binaries)
- 166 files under `data/runtime/` (proofs, examples, state, memory store)
- 8 operational JSONL logs at `data/` root
- `data/umh/traces/` — 5083-line traces.jsonl (3MB) + 7MB index.json
- `data/umh/memory_candidates/` — 2523-line candidates.jsonl (2MB)
- `data/semantic_space/` — 41MB embeddings file
- `data/merged_graph.json` + `data/codebase_graph_merged.json` — duplicate graph files (4.7MB each)
- `.obsidian/plugins/` — Obsidian plugin binaries (user-specific)

These are runtime artifacts, not source code. They change with every execution,
create noisy diffs, and inflate the repo. Additionally, JSONL writers had no
rotation — files grow unbounded.

## Changes

### 1. Gitignore and untrack 3,683 files

Updated `.gitignore` to cover:
- `node_modules/` and `saas/node_modules/` — npm dependencies (never tracked)
- `data/runtime/` — all generated proofs, examples, and state
- 8 operational JSONL logs (`orchestrator_log`, `control_plane_log`, etc.)
- `data/umh/traces/` and `data/umh/memory_candidates/`
- `data/semantic_space/` — embedding vectors (derivable)
- `data/merged_graph.json`, `data/codebase_graph_merged.json` — duplicate graphs
- `.obsidian/plugins/` — Obsidian plugin binaries

Preserved: `data/config/loop_definitions.jsonl` (actual config, not runtime).

Used `git rm --cached` to untrack files while keeping local copies.
All writers use `mkdir(parents=True, exist_ok=True)` so no `.gitkeep`
files needed — directories recreated on demand.

### 2. JSONL rotation utility

New module: `substrate/observability/jsonl_rotation.py`

- `rotate_if_needed(path, max_lines=5000)` — line-count rotation
- When threshold exceeded: moves file to `archive/` subdir with timestamp
- Creates empty replacement file
- Returns archive path (or None if no rotation needed)

### 3. Rotation wired into major writers

| Writer | File |
|--------|------|
| `substrate/observability/trace_store.py` | `data/umh/traces/traces.jsonl` |
| `substrate/memory/candidate_generator.py` | `data/umh/memory_candidates/candidates.jsonl` |
| `substrate/observability/error_recorder.py` | `logs/errors.jsonl` |

### 4. Verification tests

`tests/test_sprint4_data_hygiene.py` — 20 tests:
- 12 gitignore assertions (runtime files ignored, config not ignored)
- 4 rotation logic tests (threshold, preservation, nonexistent files)
- 3 wiring tests (rotation imported in all writers)

## Files modified

- `.gitignore`
- `substrate/observability/jsonl_rotation.py` (new)
- `substrate/observability/trace_store.py`
- `substrate/observability/error_recorder.py`
- `substrate/memory/candidate_generator.py`
- `tests/test_sprint4_data_hygiene.py` (new)
- `docs/audits/convergence/20260527-sprint4-data-hygiene.md` (new)

## Net repo impact

- 3,683 files removed from tracking (still exist locally)
- ~170MB of data no longer in git history going forward
- JSONL files auto-rotate at 5000 lines to prevent unbounded growth
