# Tool Mastery Research Agent

Status: **v1.1 (honest executor + deterministic candidate generation)** — 2026-04-08
Location: `/opt/OS/core/tool_mastery_research_agent/`

The Research Agent is the execution layer for the Tool Mastery
pipeline. It consumes `tool_mastery:research|refresh|repair` actions
queued by the Tool Mastery Manager and produces source-grounded
research artifacts that a later authoring pass (human or CC session)
can quote from when filling `SKILL.md` and `references/best_practices.md`.

## Where it sits in the pipeline

```
Tool Mastery Manager
    ↓  queues run_script action via Control Plane
Deferred queue (logs/deferred/*.json)
    ↓  consumed by dispatcher or CLI
Research Agent
    ↓  discovers → fetches → writes artifact
logs/tool_mastery_research/{slug}/{stamp}/
    ↓  read by authoring pass (manual / subagent)
skills/tools/{slug}/SKILL.md + references/best_practices.md
    ↓  verified by scripts/verify_tool_skill.py
Tool Mastery Engine (TME) compliance
```

## Relationship to TME

The Tool Mastery Engine (`skills/meta/tool_mastery_engine/SKILL.md`)
defines **what creator-level mastery looks like**: 19 section headers
split across Tier 1 (technical) and Tier 2 (creator intelligence).
The Research Agent does not replace TME — it produces the **input
material** an authoring pass uses to fill TME's sections.

The agent emits a `section_coverage` ledger that enumerates all 19
TME headers and marks each `has_source: false` by default. Flipping
any entry to `true` remains a **human authoring decision**, not an
automated keyword match. This is the deliberate honesty boundary.

## What it automates vs what it does not

**Automated (v1):**
- Source discovery from `tool_doc_registry.md`, `~/.claude.json`
  mcpServers entries, and explicit URL hints
- HTTP(S) GET with User-Agent, timeout, size cap, raw capture to disk
- Per-source provenance: status, http code, content-type, bytes, error
- `research_artifact.json` (machine) + `summary.md` (human) + `sources.md`
- `manifest.json` with run-level metadata + `next_steps`
- Safe-only frontmatter updates to an existing `SKILL.md`:
  `source_url` and `last_researched` — **only if those fields already
  exist**. No new fields are invented.

**Not automated (and honestly so):**
- Parsing HTML into cleaned prose — downstream authoring reads raw captures
- Writing `references/best_practices.md` section bodies
- Declaring a tool "mastered" — `scripts/verify_tool_skill.py` remains
  the source of truth
- Parallel subagent dispatch (TME Phase 1-3) — v1 runs sequentially
- JavaScript rendering / browser emulation
- MCP handshakes (stitch's endpoint is recorded as a source ref but
  the agent does not POST JSON-RPC to it — that's the MCP client's job)
- Neon sync after authoring
- Auto-adding new entries to `tool_doc_registry.md`

## Provenance

Every run writes a dated directory:
```
logs/tool_mastery_research/{slug}/{YYYY-MM-DDTHH-MM-SSZ}/
    manifest.json            — run metadata + status + next_steps
    source_plan.json         — raw SourcePlan before fetch
    research_artifact.json   — plan + fetched sources + coverage ledger
    summary.md               — human-readable overview
    sources.md               — flat per-source provenance
    handoff.json             — safe-metadata report
    raw/
        01_{host}_{path}.txt — raw fetched bytes (capped at 2 MB)
        02_...
```

Every `FetchedSource` carries: `tier`, `origin` (registry | claude_json |
request), `status`, `http_status`, `content_type`, `bytes`, `error`,
`fetched_at` ISO8601 UTC, and the relative `raw_path` of the captured
bytes. Nothing is summarised away.

## How to run it

### Direct CLI

```bash
# brand new tool (no skill yet)
python3 -m core.tool_mastery_research_agent --tool notion --mode research

# with explicit source hints
python3 -m core.tool_mastery_research_agent \
    --tool stitch --mode research \
    --official-url https://stitch.withgoogle.com \
    --hint https://developers.google.com/stitch

# JSON output
python3 -m core.tool_mastery_research_agent --tool notion --json
```

### Consume a queued Control Plane action

```bash
python3 -m core.tool_mastery_research_agent \
    --consume-action /opt/OS/logs/deferred/<action_id>.json
```

The action file's `inputs.tool` and `inputs.work_type` drive the run;
the action's `id` is preserved in the request for audit.

### Through the dispatcher (Control Plane target)

The `--execute` flag turns the existing dispatcher into a live
executor, preserving backwards compatibility for callers that still
want a printed plan only:

```bash
# print plan (old behaviour, unchanged)
python3 scripts/tool_mastery_research_dispatcher.py \
    --work-type research --tool notion

# execute real research run
python3 scripts/tool_mastery_research_dispatcher.py \
    --work-type research --tool notion --execute
```

## Exit codes & statuses

| Status          | Meaning                                        | Exit |
|-----------------|------------------------------------------------|------|
| `ok`            | all sources fetched successfully               | 0    |
| `partial`       | at least one source ok, one or more failed    | 0    |
| `no_sources`    | discovery returned nothing                     | 0    |
| `fetch_failed`  | sources planned but every fetch failed         | 1    |
| `error`         | unexpected failure                             | 1    |

`no_sources` is intentionally exit 0 — an empty plan is a valid,
honest outcome and the artifact still records why.

## Discovery modes

Discovery runs in a fixed priority order inside `source_discovery.discover_sources()`:

1. **Explicit `--official-url`** — highest trust, always wins.
2. **`--hint <url>` values** — treated as explicit operator assertions.
3. **`tool_doc_registry.md`** — human-maintained canonical list.
4. **`~/.claude.json` MCP entries** — HTTP manifest endpoints for MCP-backed tools.
5. **Operator-approved candidates** (new in v1.1) — the fallback tier
   that unblocks discovery when every upstream source comes up empty.

Only tier 5 is gated by approval. Tiers 1–4 are already curated or
operator-supplied and flow straight into the fetcher.

### Candidate generation (deterministic, no network)

When tiers 1–4 yield nothing, the operator can generate **deterministic
source candidates** using `core/tool_mastery_research_agent/search_discovery.py`.

Six pattern families, each a pure function of the slug:

| Family              | Tier                | Shape                                      |
|---------------------|---------------------|--------------------------------------------|
| `vendor_domain`     | `official_docs`     | `https://<slug>.{com,io,ai}`, `docs.<slug>.com` |
| `api_reference`     | `official_api_ref`  | `https://docs.<slug>.com/{api,reference}`  |
| `github_search`     | `official_repo`     | `https://github.com/search?q=<slug>`       |
| `github_repo_guess` | `official_repo`     | `https://github.com/<slug>/<slug>`         |
| `pypi`              | `official_package`  | `https://pypi.org/project/<slug>/`         |
| `npm`               | `official_package`  | `https://www.npmjs.com/package/<slug>`     |

**Candidates are proposals, not claims.** They are algorithmically
constructed URL shapes — nothing is looked up, no LLM is consulted, no
search provider is called. A candidate only means *"if a source of this
kind exists, this is where convention would put it"*. Every candidate
carries a `rationale` string and an `origin="generated"` tag so
downstream readers can always distinguish a generated URL from a
registry-sourced one.

## Approval flow

The approval gate is **file-based** and composes with the existing
Control Plane without needing a new action type:

```
1. generate
   python3 -m core.tool_mastery_research_agent \
       --tool <slug> --generate-candidates

   → writes logs/tool_mastery_research/<slug>/candidates/<stamp>.json
   → the write is routed through Control Plane `write_file`, so
     logs/execution/<date>-execution.jsonl records:
       - action.type = "write_file"
       - action.description = "tool_mastery:search_candidates:<slug> — ..."
       - source_agent = "tool_mastery_research_agent"
       - idempotency_key = "tool_mastery:search_candidates:<slug>:<ts>"

2. review
   python3 -m core.tool_mastery_research_agent \
       --tool <slug> --show-candidates

3. decide (any combination)
   python3 -m core.tool_mastery_research_agent --tool <slug> --accept 2,5,8
   python3 -m core.tool_mastery_research_agent --tool <slug> --reject 1,4
   python3 -m core.tool_mastery_research_agent --tool <slug> --accept-all
   python3 -m core.tool_mastery_research_agent --tool <slug> --reject-all

   → mutates the same candidates file in place, stamping
     status/decided_at/decided_by on each record.

4. research
   python3 -m core.tool_mastery_research_agent --tool <slug> --mode research

   → discover_sources() automatically loads the *accepted* subset from
     the latest candidates file when tiers 1–4 are empty. Fetching
     then proceeds through the existing fetcher.
```

Only candidates with `status="accepted"` are ever promoted to
`SourceRef` and handed to the fetcher. Pending and rejected candidates
are inert.

## Trust model

The discovery system is built around a single invariant:

> **No URL reaches the fetcher without an explicit trust decision.**

| Source tier              | Trust decision made by            | When |
|--------------------------|-----------------------------------|------|
| `--official-url`         | operator                          | request time |
| `--hint`                 | operator                          | request time |
| `tool_doc_registry.md`   | whoever wrote the registry row    | registry maintenance |
| MCP HTTP manifest        | implicit (the tool is installed)  | install time |
| Generated candidates     | operator, per-URL                 | approval step |

Generated candidates are the *only* tier without prior curation, which
is exactly why they require a per-URL approval step. The approval file
is co-located with the run under `logs/tool_mastery_research/<slug>/candidates/`
so the audit trail for "why did we fetch this URL" is one directory
away from the research artifact that used it.

The system refuses to fabricate. If every tier comes up empty and no
candidates have been approved, `discover_sources()` returns an empty
plan with notes explaining what was checked — the honest empty beats
a confident wrong.

## Limitations

1. **Sequential fetches.** v1 is polite — one source at a time.
2. **Static HTTP only.** JS-heavy vendor docs land as empty shells.
3. **No section-level scoring.** The coverage ledger is a checklist,
   not a classifier.
4. **Stdio MCP tools.** Without a discoverable HTTP URL (notebooklm_mcp
   is the canonical example), the agent correctly reports `no_sources`
   unless the caller supplies `--official-url` or `--hint`.
5. **MCP manifest endpoints** (stitch) reject plain GET (405). The
   endpoint is recorded as provenance; usage patterns still require
   vendor documentation provided via hints.
6. **No LLM synthesis.** Deliberately — synthesis is the responsibility
   of the authoring pass that reads the artifact.

## Extending the agent

Likely next steps, in order of value:

1. Teach discovery to read an `npm` / `pypi` package page when a
   stdio MCP command name is found in `~/.claude.json`.
2. Add a `--subagent` mode that spawns CC subagents per TME phase
   when invoked inside Claude Code (opt-in, not default).
3. Add light HTML → text extraction in `fetcher.py` to make `raw/`
   captures easier to read during authoring.
4. Add a follow-up `authoring` subsystem that reads the artifact and
   drafts `best_practices.md` with explicit `[SOURCE: url]` citations
   on every claim — the source-grounding invariant holds because the
   artifact carries the only ground truth.
