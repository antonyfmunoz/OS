---
type: codewiki-dir
dir: graphify-out
---

# `graphify-out/` — the `/graphify` tree-sitter AST index (multi-language structural graph)

**1 file · ~43.7 MB · [Full file inventory](../inventory/graphify-out.md)**

*(Counts as of the manifest's `generated_at` 2026-07-10T20:18Z, git SHA `a5f09e48e`. Single file: `graph.json`. Its own `metadata.builtAt` was 2026-07-10T20:23Z — it is rebuilt in place on each `/graphify` run.)*

## Purpose
`graphify-out/` holds the output of the gstack `/graphify` skill: a structural AST index of the codebase built with tree-sitter across ~12 languages (classes, functions, imports, call graph). Its single artifact, `graph.json`, is a nodes/edges graph used for fast structural navigation of unfamiliar code — the skill is meant to be run before searching or after editing. It is fully gitignored (`.gitignore` line 163, `graphify-out/`) as a derivable index.

## How it fits
This is a tooling artifact, not part of the running substrate — no UMH code imports it. It is produced by an external skill (`/graphify`) and consumed by that skill's query tools and by developers exploring the tree. Architecturally it is a *parallel, secondary* structural index that sits beside UMH's own primary graph; the two are built by different pipelines and must not be conflated.

## Structure
One file:

| Path | Bytes | Shape |
|---|---|---|
| `graph.json` | ~43.7 MB | `{ nodes, edges, metadata }`. At the current build: `metadata = { files: 2985, nodes: 67931, edges: 65065, builtAt: <ISO> }`. |

## Key components
- `graphify-out/graph.json` — the whole directory. `nodes` are code symbols (files, classes, functions), `edges` are structural relations (imports, calls). `metadata.files` (2,985) is the source-file count scanned; `metadata.nodes` (67,931) and `metadata.edges` (65,065) size the graph.

## Relationship to the UMH graph (important — three distinct things)
These names collide; keep them straight:

| Artifact | Producer | What it is |
|---|---|---|
| `graphify-out/graph.json` | gstack `/graphify` **skill** (tree-sitter, 12 languages) | This directory. Secondary AST index for exploration. |
| `data/graphify_overlay.json` | `scripts/run_graphify.py` (UMH internal "Graphify adapter") | An **additive enrichment** over UMH's primary graph — clusters, co-occurrence edges, cross-language links. Never touches the primary graph. |
| `data/codebase_graph.json` | `scripts/codebase_graph.py` | UMH's **primary** structural graph (Python AST), the source of truth for `query_graph.py` and the cognition stack. |

`scripts/merge_graphs.py` merges `data/graphify_overlay.json` into `data/codebase_graph.json`, writing `data/codebase_graph_merged.json` by default (the primary is source-of-truth and is never overwritten; `--in-place` exists but is discouraged). The overlay is tagged `"source": "graphify"` on every added edge. **`graphify-out/graph.json` is not an input to `merge_graphs.py`** — the merge consumes `data/graphify_overlay.json`, a different file. The name overlap between the gstack skill and UMH's `run_graphify.py` adapter is purely nominal.

## Data & state
A single generated JSON file. Rebuilt wholesale each `/graphify` run (in-place overwrite; the `builtAt` timestamp tracks freshness). No incremental update, no Neon. Deleting it is safe — re-running `/graphify` regenerates it.

## Gotchas
- **Don't confuse it with UMH's graph.** The retrieval hierarchy in `CLAUDE.md` (Palace → Graph → Summaries → …) refers to `data/codebase_graph.json` via `query_graph.py`, **not** to `graphify-out/graph.json`. Structural queries in this repo go through `scripts/query_graph.py`, not this file.
- **Gitignored and derivable.** Never commit it; it is 43.7 MB of regenerable index and would bloat git history against Node Role Discipline.
- **Staleness is silent.** The only freshness signal is `metadata.builtAt` inside the file. If you rely on it for navigation after editing, re-run `/graphify` — nothing auto-rebuilds it.

## See also
- [`data/`](data.md) — `data/graphify_overlay.json`, `data/codebase_graph.json`, `data/merged_graph.json`
- [`scripts/`](scripts.md) — `run_graphify.py`, `merge_graphs.py`, `codebase_graph.py`, `query_graph.py`
- [Architecture](../architecture.md) · [Tech stack](../tech-stack.md)
