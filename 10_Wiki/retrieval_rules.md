---
type: retrieval-rules
generated: 2026-04-10
authority: mandatory
---

# Retrieval Rules — Enforced Hierarchy

AI agents in EOS must follow this order when answering ANY question
about the codebase. Skipping a layer wastes the founder's context budget.

## The order

1. **Memory Palace** — [[palace/index|10_Wiki/palace/]]
   Start here. Rooms name the concern; loci name the file.
   If a room covers your question, your answer lives inside it.

2. **Knowledge Graph** — [[codebase/cloud|10_Wiki/codebase/]] and `data/codebase_graph.json`
   Structural answers: dependencies, dependents, call paths, entry points.
   Query with `scripts/query_graph.py`.

3. **Summaries** — `data/node_summaries.json`
   One-line descriptions per node. Faster than opening a file.

4. **Raw source files** — read ONLY when you need implementation detail
   the graph cannot express (control flow, literal values, regex bodies).

5. **Logs / transcripts / databases** — last resort.
   Use only when runtime behavior is the question.

## Mandatory checks before reading source

Before running `Read` on any Python/JS/TS/SQL file, you must be able to
answer yes to one of:

- The palace room for this concern contains this file as a locus.
- `query_graph.py` says this file is a dependent or dependency of the
  target I am reasoning about.
- `query_graph.py freshness` says the graph is stale and I am rebuilding.
- The file is not in the graph (untracked language, new file).

## Mandatory checks before editing

- `query_graph.py dependents <file>` — know the blast radius.
- `query_graph.py critical` — is this file in the critical set? Extra care.
- `query_graph.py path <caller> <file>` — verify the caller you expect.

## Guarantees the system must hold

- Session bootstrap loads [[palace/index|palace]] + [[codebase/cloud|graph rules]] + these rules at start.
- Stale graph (> 24h) raises a warning in session bootstrap.
- Post-merge hook rebuilds graph and palace automatically.
- Pre-commit hook warns when code changes land without a refresh.
- `scripts/verify_knowledge_system.py` validates every layer in one run.

## Language coverage

The graph is built by a modular parser registry at `parsers/`:

| Parser | Languages | Role in graph |
|--------|-----------|---------------|
| PythonParser  | `.py`                           | Authoritative — drives AST graph |
| TSParser      | `.ts`, `.tsx`                   | Files + imports + classes + types + interfaces |
| JSParser      | `.js`, `.jsx`, `.mjs`, `.cjs`   | Files + imports + classes + functions |
| SQLParser     | `.sql`                          | Tables + FROM/JOIN references |
| ConfigParser  | `.json`, `.yaml`, `.yml`, `.toml` | Top-level keys |

Python nodes get the full class/function/call graph. Non-Python nodes
contribute files + symbols + imports into `non_python_files` in
`data/codebase_graph.json`. Query them through `query_graph.py languages`.

To add a new language: implement `parsers.base.Parser` and append the
instance to `REGISTRY` in `parsers/__init__.py`. No other file changes.

## Failure modes to avoid

- Reading `eos_ai/` top-to-bottom to find a class — grep the graph instead.
- Opening a file just to see its imports — the graph already has them.
- Guessing which file calls a function — `query_graph.py dependents` answers.
- Trusting a stale graph without checking freshness.

## Philosophy

The codebase is large. Your context is finite. The graph is deterministic.
Any answer the graph can give, the graph should give. Raw files are for
the last 20% where structure is not enough.
