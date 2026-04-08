# Tool Mastery Research Agent — Build Audit

Date: 2026-04-08
Author: Developer Agent (Claude Opus 4.6)
Scope: v1 implementation of the Research Agent subsystem

## 1. What existed already

- **Tool Mastery Engine** (`skills/meta/tool_mastery_engine/`) — complete
  decision tree + 19-section research protocol + tool_doc_registry.md.
  **Planning-complete, execution-empty.**
- **Tool Mastery Manager** (`core/tool_mastery_manager/`) — discovery,
  coverage evaluator, backlog writer, scaffolding, queueing into
  Control Plane via `ensure_mastery()`.
- **Control Plane** (`core/action_system/`) — validated/deferred
  medium-risk actions written to `logs/deferred/*.json`.
- **Research dispatcher** (`scripts/tool_mastery_research_dispatcher.py`)
  — prints a structured next-steps plan for a queued action but does
  NOT execute research. Exit 0 on plan printed.
- Two real deferred actions already queued for `notebooklm_mcp` and
  `stitch` (`logs/deferred/5aa5544b...json` and `f84f746a...json`).

**The missing layer was the research executor itself.** The entire
system could plan, queue, and describe research but never actually
fetched a byte of documentation.

## 2. What was built

New subsystem: `/opt/OS/core/tool_mastery_research_agent/`

| Module              | Responsibility |
|---------------------|----------------|
| `__init__.py`       | Public surface — models + agent entry |
| `paths.py`          | EOS_ROOT-centralised path resolution (mirrors manager) |
| `models.py`         | `ResearchRequest`, `SourcePlan`, `SourceRef`, `FetchedSource`, `ResearchArtifact`, `ResearchResult` + enums. All JSON-serialisable via `asdict()`. |
| `source_discovery.py` | Builds a prioritised `SourcePlan` from explicit URLs → `tool_doc_registry.md` → `~/.claude.json` mcpServers. Honest empty result when nothing is found. |
| `fetcher.py`        | Dependency-free `urllib` GET with UA, 15 s timeout, 2 MB cap, raw capture to disk, per-source error recording. Never raises. |
| `artifact.py`       | Builds `ResearchArtifact`, writes `research_artifact.json` (machine) + `summary.md` (human) + `sources.md` (provenance). Includes the 19-section **honesty ledger** defaulting `has_source=false`. |
| `handoff.py`        | Safe-only SKILL.md frontmatter updates (`source_url`, `last_researched`). Never creates files, never touches `best_practices.md`, never invents new fields. |
| `agent.py`          | Orchestrator `run(request) → ResearchResult`. Writes `manifest.json`. |
| `cli.py` + `__main__.py` | `python3 -m core.tool_mastery_research_agent` with `--tool`, `--mode`, `--official-url`, `--hint`, `--consume-action`, `--json`. |

Plus one existing-file edit:

- `scripts/tool_mastery_research_dispatcher.py` gained an `--execute`
  flag that delegates to the agent. Backwards-compatible — default
  behaviour unchanged.

## 3. How queued research actions are consumed

Two supported entry points, both exercising the same `agent.run()`:

**A. Consume a deferred action file directly:**
```bash
python3 -m core.tool_mastery_research_agent \
    --consume-action /opt/OS/logs/deferred/<id>.json
```
The action's `inputs.tool`, `inputs.work_type`, `id`, and
`source_agent` are all preserved into the `ResearchRequest` for audit.

**B. Let Control Plane call the dispatcher with `--execute`:**
```bash
python3 scripts/tool_mastery_research_dispatcher.py \
    --work-type research --tool stitch --execute
```

Either path writes a fully-audited run under
`logs/tool_mastery_research/{slug}/{stamp}/`.

## 4. Validation on notebooklm_mcp and stitch

### stitch (HTTP MCP endpoint)
- Discovery found `https://stitch.googleapis.com/mcp` from
  `~/.claude.json` (tier `mcp_manifest`) and notes explaining the
  endpoint is a live manifest not a docs page.
- First run: `fetch_failed` — GET against the MCP endpoint returns
  HTTP 405 Method Not Allowed. **Correctly reported**, not swallowed.
- Second run with `--official-url https://stitch.withgoogle.com
  --hint https://developers.google.com/stitch`: `partial` status —
  withgoogle.com fetched OK (200, 23,500 B), developers.google.com/stitch
  returned 404 (honestly recorded), MCP endpoint still 405.
- Artifact at
  `logs/tool_mastery_research/stitch/2026-04-08T23-26-05Z/` with real
  raw capture + per-source provenance.

### notebooklm_mcp (stdio MCP)
- Discovery correctly identified the tool as stdio-only (no HTTP URL
  available) and emitted `no_sources` with an explanatory note.
- Second run with `--official-url
  https://github.com/danielmeppiel/notebooklm-mcp --hint
  https://pypi.org/project/notebooklm-mcp/`: `partial` — PyPI page
  fetched OK (200, 3,101 B), the guessed GitHub URL returned 404
  (honestly recorded).
- Artifact at
  `logs/tool_mastery_research/notebooklm_mcp/2026-04-08T23-26-06Z/`.

### Sanity check on a well-known tool
- `notion` — `ok` status, 2/2 sources fetched (developers.notion.com
  root + reference), 758 KB of raw HTML captured across two files.

### Invariants preserved
- Tool Mastery Manager: untouched.
- Control Plane: untouched; new `--execute` flag is additive on the
  dispatcher only.
- Coverage ledger: every one of the 19 TME sections written with
  `has_source=false` — **zero fabricated completion**.
- Handoff: for all three tools, handoff skipped cleanly because no
  SKILL.md exists yet (or frontmatter keys absent).

## 5. What remains manual

- Authoring `references/best_practices.md` section bodies by reading
  the raw captures — deliberately kept manual so quotes stay grounded.
- Flipping individual `section_coverage` rows to `has_source=true`
  after verifying the source actually covers the section.
- Running `scripts/verify_tool_skill.py --skill <slug>` after authoring.
- Syncing to Neon after verification.
- Adding new vendor docs URLs to `tool_doc_registry.md` so future runs
  don't need explicit `--official-url` hints.

## 6. Next recommended step

Build a small **authoring assistant** that reads a `research_artifact.json`
and drafts `references/best_practices.md` with explicit `[SOURCE: url]`
citations on every claim, section-by-section against the 19 TME
headers. Run it as a separate `--author` pass, not as an automatic
continuation of the research run, so the source-grounding invariant
stays enforceable and reviewable.

Alternatives, ranked:
1. Author assistant (above) — highest leverage, closes the loop.
2. Light HTML→text extraction in `fetcher.py` to make raw captures
   easier to read during manual authoring.
3. Parallel fetch + per-source diffing for refresh mode.
4. Package-registry discovery (npm / pypi) keyed off stdio MCP
   command names so tools like `notebooklm_mcp` get hints for free.
