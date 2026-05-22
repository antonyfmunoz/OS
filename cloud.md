---
type: system-context
generated: 2026-04-10
---

# EOS Cloud — System Context

This is the root context file for every AI session in EOS.
It is loaded first. It is not optional.

## What this system is

EntrepreneurOS is a live AI business operating system.
Every file you touch is running in production somewhere.
You are modifying a real system the founder depends on.

## What the knowledge system gives you

You have four layers of pre-computed knowledge. Use them in order:

| Layer | Location | When to use |
|-------|----------|-------------|
| Memory Palace | `knowledge/palace/` | First — room-level orientation |
| Knowledge Graph | `data/codebase_pages/` + `data/codebase_graph.json` | Second — structural queries |
| Summaries | `data/node_summaries.json` | Third — short descriptions |
| Raw source | everywhere | Last — only when implementation matters |

## The enforced hierarchy

See `knowledge/retrieval_rules.md`. The rules are:

1. Palace → which room owns this concern
2. Graph → what depends on what, where does it live
3. Summaries → what does each node do in one line
4. Raw files → open only when you need the implementation
5. Logs / transcripts → last resort

Violating the order means you burn context on blind reads.

## How to query

```bash
python3 scripts/query_graph.py dependents eos_ai/memory.py
python3 scripts/query_graph.py path   services/discord_bot.py eos_ai/db.py
python3 scripts/query_graph.py critical
python3 scripts/query_graph.py centrality --top 20
python3 scripts/query_graph.py freshness
```

## How to stay fresh

```bash
scripts/update-graph          # rebuild codebase_graph.json + codebase vault
python3 scripts/build_palace.py    # rebuild palace from graph
python3 scripts/summarize_nodes.py # refresh summaries (append-only, safe)
scripts/install_graph_hooks.sh     # one-time: wire git pre-commit + post-merge
```

## Invariants

- The graph is a snapshot. Check `query_graph.py freshness` before trusting it.
- Raw source is always authoritative — summaries and graph never overwrite it.
- Summaries are append-only. Old versions stay. Nothing is destroyed.
- The palace is regenerated every build from the graph. It is a view, not state.
- Hooks installed via `scripts/install_graph_hooks.sh` refresh the graph
  on post-merge and warn on pre-commit when graph drifts.

## Escalation

If a query returns nothing useful:

1. Check freshness — the graph may be stale.
2. Fall back to the next layer (palace → graph → summaries → raw).
3. Only then open files blind.
