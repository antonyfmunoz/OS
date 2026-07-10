---
type: codewiki-dir
dir: knowledge
---

# `knowledge/` — the LLM-maintained CANON wiki + precomputed retrieval layer (palace, rules, concepts)

**344 files + 3 symlinks · 522,771 bytes · [Full file inventory](../inventory/knowledge.md)**

## Purpose
`knowledge/` is the **CANON** layer of the wiki model and the top of the
enforced retrieval hierarchy. It holds curated, human-readable, LLM-navigable
pages distilled from raw material (`docs/`, inbox signals, conversations), plus
the **memory palace** — a room-based navigational view of the codebase that an
agent is required to consult before scanning files. Its job is to make sure "AI
NEVER starts blind": before reading raw source, an agent stands in a palace room,
queries the graph, or reads a summary. Two governing documents live here:
`WIKI_RULES.md` (the three-layer CORPUS→CANON→SCHEMA model) and
`retrieval_rules.md` (the non-negotiable Palace→Graph→Summaries→Raw→Logs order).

## How it fits
`knowledge/` is `authority: mandatory` per `retrieval_rules.md` and
`cloud_palace.md`. It is not a code layer — nothing under
projections/transports/adapters/substrate imports it. Instead the session
bootstrap (`scripts/session_bootstrap.py`, per `CLAUDE.md`) loads
`knowledge/palace/index.md`, `knowledge/cloud_palace.md`, and
`knowledge/retrieval_rules.md` at the start of every session. The palace is a
**view over** the codebase graph: `scripts/build_palace.py` regenerates every
room deterministically from `data/codebase_graph.json`, so it never stores truth,
only pointers (loci) into `data/codebase_pages/`.

## Three distinct knowledge systems — stated honestly
This is the load-bearing distinction. There are **three** separate knowledge
systems in the repo, and they are not the same thing:

1. **The CANON / business wiki — `knowledge/`** (this directory). Curated prose
   pages: concepts, entities, decisions, synthesis. Maintained by the LLM under
   `WIKI_RULES.md`, indexed by `knowledge/index.md`, browsed as an Obsidian vault.
   Its vocabulary is a mix of business (ICP, north-star, Initiate Arena) and
   system concepts (execution-spine, execution-class, plan-review).
2. **The auto-generated codebase graph pages — `data/codebase_pages/`** (a
   *different* directory, ~35k files in `files/ classes/ functions/ modules/`).
   Machine-generated from the AST graph; the palace's loci are wikilinks *into*
   these pages. This is the structural layer, rebuilt by `scripts/update-graph`.
3. **This CodeWiki — `docs/codewiki/`** (what you are reading). A fresh, complete
   narrative map of the repository built today from a worktree-scoped graph. It is
   a `docs/` sub-tree, human-authored on top of a deterministic inventory.

The relationship: the **palace** (in system 1) points at **graph pages** (system
2) as its loci; **this CodeWiki** (system 3) is an independent narrative pass over
the same repository and cites both. `knowledge/`'s own `retrieval_rules.md` names
system 2 as "Knowledge Graph — `data/codebase_pages/`", which is why the two are
easy to conflate — they cross-reference but live in different trees.

## Structure
| Subdir | Files | Role |
|---|---|---|
| `knowledge/` (root) | 8 | Governing docs: `WIKI_RULES.md`, `index.md`, `retrieval_rules.md`, `cloud_palace.md`, `log.md` (append-only change log), plus Layer-3 sovereignty/architecture notes |
| `knowledge/concepts/` | 135 | CANON concept pages (recurring ideas/frameworks): execution-class, plan-review, binding-constraint, north-star, LLM-planning |
| `knowledge/palace/` | 74 | Memory palace: `index.md` + `rooms/` (7) + `wings/` (5 pages) + `candidates/` (61 clustered candidate loci) |
| `knowledge/skills/` | 52 | Skill knowledge tree (marketing/content/remotion best-practices) + a `business` symlink → `06_Skills` |
| `knowledge/synthesis/` | 38 | Cross-cutting analyses connecting multiple sources; includes the 422-line `umh-unified-system-synthesis.md` |
| `knowledge/entities/` | 29 | Named things: Initiate Arena, Neon database, BIS service, strategy engine, os-bot |
| `knowledge/decisions/` | 6 | Recorded choices (component-status taxonomy, in-memory task-pause state, running-paid-ads) |
| `knowledge/domains/` | 1 | Domain catalog README |
| `knowledge/sources/` | 1 | `.gitkeep` only — provenance-summary home, currently empty |

## Key components
- `knowledge/WIKI_RULES.md` (207 lines) — the schema. Defines CORPUS (immutable:
  `01_Inbox/`, `data/`, `docs/`), CANON (this dir, five page types with
  frontmatter), and the ingestion/update/log discipline. Read before any
  knowledge work per `CLAUDE.md`.
- `knowledge/retrieval_rules.md` (86 lines) — the enforced order
  Palace→Graph→Summaries→Raw→Logs, plus the pre-read/pre-edit checks and the
  parser-registry language table (`parsers/`). This is why an agent must run a
  `query_graph.py` command before `Read`-ing a tracked file.
- `knowledge/palace/index.md` — palace entry point. Currently reports **30 loci
  promoted, 7 rooms, 4 wings** in its Wings section (runtime, services, scripts,
  core). Rooms: `intelligence_core`, `memory_persistence`, `substrate`,
  `strategy_orchestration` (runtime wing); `transports` (services); `tooling`
  (scripts); `core_agents` (core).
- `knowledge/cloud_palace.md` (77 lines) — how agents traverse the palace:
  concern → room → purpose line → core-loci table (rank
  `inbound*2 + outbound + critical*10 + entry*3`) → graph page → raw file.
- `knowledge/index.md` (241 lines) — the CANON wiki index, organized by page type;
  `WIKI_RULES.md` requires every new CANON page be added here.
- The palace build: `scripts/build_palace.py:ROOM_DEFS` defines rooms;
  `score_file()` sets locus weights; rerun regenerates idempotently from the graph.

## Data & state
- **Reads:** `data/codebase_graph.json` and `data/node_summaries.json` (the palace
  and retrieval layer are computed from these).
- **Writes:** palace pages under `knowledge/palace/` (regenerated, not
  hand-edited); CANON pages hand-authored by the LLM; `knowledge/log.md` appended
  on every CANON mutation.
- **Symlinks (3):** `knowledge/skills/business` → `/opt/OS/06_Skills`, plus two
  Remotion skill symlinks under `knowledge/skills/marketing/content/remotion/`
  (`.claude/` and `.cursor/` → `../../.agents/skills/remotion-best-practices`).
- **Freshness:** stale graph (>24h) raises a warning in session bootstrap; a
  post-merge hook rebuilds graph + palace; `scripts/verify_knowledge_system.py`
  validates every layer in one pass.

## Gotchas
- **Palace rooms can be empty even when the index looks healthy.** The
  `substrate` room page (`knowledge/palace/rooms/substrate.md`) has an **empty
  Core Loci table and empty Raw Paths block** — its concern ("voice/meeting/
  operator pipeline") matched no files under the prefixes the last build used, so
  it promoted zero loci. Trust the index counts, but verify the specific room has
  loci before relying on it; re-run `scripts/build_palace.py` after graph changes.
- **The index lists 4 wings; `wings/` has 5 files.** `knowledge/palace/wings/`
  contains `eos_ai-wing.md` in addition to the four the current index names
  (runtime, services, scripts, core). The `eos_ai` wing page is a build artifact
  from an earlier module layout not surfaced in the current index — do not treat
  it as a live navigation entry.
- **Don't conflate the three knowledge systems** (see above): `knowledge/` (CANON
  prose), `data/codebase_pages/` (auto graph pages), and `docs/codewiki/` (this
  wiki). `retrieval_rules.md` deliberately names all of them.
- **CANON is derived, CORPUS is immutable.** Never copy `docs/` content verbatim
  into `knowledge/`; summarize, structure, and wikilink. CANON is the source of
  truth over conversation logs, not over the code.
- **Auto-memory is a separate system.** `WIKI_RULES.md` explicitly excludes CC
  auto-memory (`~/.claude/projects/`) from CANON — that is the per-session memory
  index, not this wiki.
- **Links are Obsidian `[[wikilinks]]`, not markdown links** inside CANON pages —
  a hard rule in `WIKI_RULES.md`. (This CodeWiki uses markdown links instead,
  because it is a `docs/` narrative tree, not a CANON page.)

## See also
- [`docs/`](docs.md) — the CORPUS reference tree that CANON summarizes
- [`.obsidian/`](dot-obsidian.md) — the vault config that makes `knowledge/` browsable with backlinks + graph
- [`scripts/`](scripts.md) — `build_palace.py`, `query_graph.py`, `session_bootstrap.py`, `verify_knowledge_system.py`
- [`data/`](data.md) — `codebase_pages/`, `codebase_graph.json`, `node_summaries.json`
- [Architecture overview](../architecture.md) · [Conventions](../conventions.md)
