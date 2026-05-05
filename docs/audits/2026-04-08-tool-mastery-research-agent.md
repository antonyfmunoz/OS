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

## Phase 4 — JS Rendering Unlock

Problem: clo3d and higgsfield returned empty or near-empty static
HTML. Crawl was correct, data was inaccessible — client-rendered
shells (Next.js, hydrated apps, Mintlify-style docs) hide prose
behind JS execution. urllib cannot reach it.

### Implementation

- New module: `core/tool_mastery_research_agent/headless_fetcher.py`
  - `is_likely_spa(raw_bytes)` — dual-trigger heuristic:
    1. explicit framework marker (`__next`, `__nuxt`, `docusaurus`,
       `mintlify`, `data-reactroot`, `window.__NEXT_DATA__`, etc.)
    2. any HTML document with ≥1 `<script>` tag (reached only after
       the signal gate already dropped the source — rendering is the
       last-resort retry)
  - `render_low_signal_sources(candidates, run_dir, max_renders=6)`
    — Playwright Chromium, headless, `networkidle` wait, 20s per page,
    3 MB cap per rendered DOM, strict run-level budget of 6 renders.
    Rewrites the capture file in place so the signal gate re-measures
    the hydrated body.
- Provenance stamped: re-captured sources get
  `origin = "headless_render@<iso8601>"` and
  `content_type = "text/html; rendered=headless"`.
- Render report written to `headless_render.json` next to the
  artifact, with per-URL activation reason, byte counts, timestamps,
  and errors.

### Conditional activation

Headless mode runs only inside `artifact.build_artifact`, only for
sources that were OK-fetched statically *and* dropped by the signal
gate *and* whose body passes `is_likely_spa`. Sources that already
passed the signal gate are never re-rendered. This preserves the
normal fetch path intact — rendering is strictly additive.

### Safety constraints

- Max 6 renders per research run (separate budget from the urllib
  fetch budget of 20).
- 20s navigation timeout per page — failed renders are logged, not
  retried.
- 3 MB cap on rendered DOM — matches the static fetcher's ethos.
- Playwright import is lazy; a missing install is degraded gracefully
  (report written with `playwright_available=false`, run continues).

### Validation

Re-ran the two failing tools. Before/after:

**clo3d** (`refresh`)

| Source | Before (static) | After (headless) |
|---|---|---|
| www.clo3d.com/docs | 173 B, 0 prose blocks → dropped | **592 KB, 55 prose blocks, 6,849 prose chars → passes** |
| pypi.org/project/clo3d | 960 B → dropped | 13 KB, 0 prose → still dropped (empty pypi page) |
| clo3d.com root | 2.4 KB WAF challenge → dropped | render timeout (WAF blocks chromium too) |
| github.com/search | 250 KB → 2 blocks dropped | 264 KB → 2 blocks still below floor |

Status flipped `fetch_failed` → `partial`. Headless unlocked a real
docs surface (`www.clo3d.com/docs`) that was invisible to static
fetch.

**higgsfield** (`refresh`)

| Source | Before (static) | After (headless) |
|---|---|---|
| higgsfield.ai | 1.75 MB, 201 prose chars → dropped | 1.79 MB, still 201 prose chars → dropped |
| github.com/search | 260 KB → 397 prose chars (1 under floor) | 274 KB → 397 prose chars → still dropped |

Status remained `fetch_failed`. **This is a valid outcome.** The
signal gate confirmed that higgsfield.ai's homepage — even fully
hydrated — is a marketing landing page with no technical prose. No
amount of rendering can synthesise content that isn't there. Phase 4
made the *correctness* of that verdict auditable: `headless_render.json`
proves the agent *tried* to unlock the content.

### Cost tradeoffs

- Browser launch: ~1-2s per render call (Chromium cold start).
- Total wall time added for clo3d run: +15s (4 renders, 1 timeout).
- Total wall time added for higgsfield run: +6s (2 renders, both fast).
- No network cost beyond normal page loads.
- Budget of 6 renders keeps worst-case at ~2 minutes of extra work per
  run — acceptable for the class of sources Phase 4 targets.

### Principle

Before Phase 4, the agent was crawling harder when it should have been
*seeing differently*. The static fetcher had already reached the right
URLs — the bytes on the wire just didn't contain the prose. Phase 4
adds a second viewing mode (headless DOM) that kicks in exactly when
the first one failed, and stays silent otherwise. The pipeline shape
— discover → fetch → signal → author — is unchanged. We only taught
the fetch step to retry with a different pair of eyes.

---

## Phase 5 — Structured Extraction

Date: 2026-04-09
Scope: convert high-signal prose and rendered docs into structured,
reusable mastery knowledge. Where Phase 1–4 focused on *access*,
Phase 5 focuses on *understanding*.

### Motivation

Phase 4 unlocked real technical content on SPA-heavy docs sites via
the headless render pass. Re-running clo3d through that pipeline
produced `prose_blocks=55, prose_chars=6849` — and on paper that looked
like a win. Inspecting the actual prose told a different story: all
55 blocks were cookie-consent / GDPR boilerplate. The signal gate
passes it because it is prose; it just isn't technical prose. The
Author Agent would have attempted to author creator-level mastery
content from GDPR language.

The bottleneck was no longer access. It was *understanding*.

### What was added

New module: `core/tool_mastery_research_agent/extraction.py`

Two responsibilities:

1. **Content-based source type classification.** Not URL-based. Each
   surviving OK source is classified as one of:
       - `docs_prose`
       - `rendered_docs_prose` (passed through headless render)
       - `api_reference`
       - `code_example`
       - `unknown`
   Classification is driven by technical-vocabulary density per 1000
   prose chars, API-marker hits (`endpoint`, `request body`, `returns`),
   raw HTTP-method tokens (`GET /api/...`), and code-fence density. The
   thresholds are deliberately coarse — we would rather mark a page
   `unknown` than promote a cookie banner.

2. **Pattern extraction layer.** Pure-Python regex scans (no LLM) that
   pull structured patterns in three buckets:
       - **usage** — install commands (pip / npm / yarn / brew),
         setup flows (numbered lists of install/configure/create
         actions), env-var config blocks.
       - **api** — function signatures (`def name(` / `function name(`),
         parameter tables (`name (type) — description`), JSON schema
         fields (`"field": "type"`).
       - **workflows** — `## Step N` headers and ordered-list action
         sequences.
   Every emitted pattern carries its source URL, a bounded excerpt, an
   explicit confidence level, and an occurrence count.

### The repeat-signal rule

A pattern is only emitted if it meets one of:
- occurrences ≥ 2 in the same source, OR
- it sits inside an obviously structured container (heading sequence,
  ordered list, or parameter table with ≥2 rows).

Single isolated hits are dropped. This is how we keep the extractor
honest — no guessing, no "looks about right".

### Code-preserving preprocessor

The Author Agent's `sanitize_text` aggressively strips symbol-dense
lines so keyword matching operates on human prose only. That's right
for prose scoring but wrong for pattern extraction — install commands,
JSON blobs, and parameter tables look like "code lines" and get
thrown away.

`extraction.preprocess_for_extraction` is a gentler pass: scripts,
styles, noscript, and HTML tags are stripped; code fences, JSON
blocks, and install commands are preserved. Pattern extractors run on
this view; classification + prose density still use the Author-Agent
sanitiser so research and author agree on what "prose" means.

### Data contract changes

`ResearchArtifact` gains two fields:

- `source_type_reports: list[dict]` — per-source classification report.
- `extracted_patterns: dict[str, list[dict]]` — three buckets (usage /
  api / workflows).

Loader + mapper on the Author Agent side were extended in lockstep:

- `LoadedArtifact.extracted_patterns` carries the patterns through.
- `mapping._apply_pattern_evidence` routes each pattern by `kind` to
  the TME section it is valid evidence for (e.g. `install_command` →
  `SDK Idioms`, `parameter_definitions` → `Core Operations with Exact
  Signatures`, `json_schema_fields` → `Data Model`). Medium- and
  high-confidence patterns can promote an uncovered section to sourced
  on their own — they already passed the repeat-signal rule in the
  research agent.

Low-confidence patterns never contribute. The honesty boundary is
non-negotiable.

### Honesty demotion

Sources classified as `unknown` are demoted from OK to SKIPPED with
`error="phase5 classifier: ..."` before the artifact is written. The
Author Agent physically cannot see them.

### Validation

#### clo3d (rebuild from 2026-04-09T05-47-51Z run)

| Phase | ok fetches | Phase-5 type | extracted patterns | authored |
|---|---|---|---|---|
| Phase 4 | 1 (cookie banner) | n/a | n/a | would author from cookie text |
| Phase 5 | **0** | `unknown` (tech_vocab=9, density=1.3/1k, api_markers=0) | 0 | honest refuse |

The single surviving source from Phase 4 (`https://www.clo3d.com/docs`,
6,849 prose chars) was demoted to SKIPPED by the Phase 5 classifier.
clo3d genuinely has no accessible technical documentation reachable
from the Research Agent's current source set, and the output now says
so.

#### remotion (rebuild from 2026-04-09T04-52-34Z run)

| Metric | Value |
|---|---|
| Sources classified | 6 |
| Type distribution | 4 `docs_prose`, 1 `api_reference`, 1 `unknown` |
| OK sources after filter | 5 |
| Extracted patterns | 2 |

Two `setup_flow` patterns (confidence `high`, 4 and 9 occurrences)
were extracted from remotion migration guides. Example excerpts:

    - import {Config} from 'remotion';
    - Don't use the [`npx remotion install`](/docs/cli/install) command anymore
    - **remotion**: [`transparent`] has been added to `offthreadvideo`

Running the Author Agent against the rebuilt artifact:

- 5 of 19 TME sections sourced
- `SDK Idioms` promoted via `pattern:setup_flow` marker + 3 existing
  prose keyword hits
- Pattern URLs recorded in `source_urls`, excerpts appended to the
  section's excerpt list, up to the existing `MAX_EXCERPTS_PER_SECTION`
  bound

### Effect on authored output

Quality signal shifts from quantitative (bytes, blocks) to qualitative
(technical signal present at all). The 19-section coverage ledger is
now defended from two new failure modes:

1. **Boilerplate promotion** — cookie / GDPR / marketing prose can no
   longer pass the signal gate. It reaches the classifier, is labelled
   `unknown`, and is dropped.
2. **Prose-only blind spots** — pages where the body is code-dense
   rather than word-dense (SDK reference fragments, migration guides,
   JSON schemas) can now contribute structured evidence even when the
   prose-block count is marginal. The pattern extractor reads them
   directly.

### Principle

Do not collect information. Understand it.

---

## Phase 7 — Code/Config Extraction (2026-04-09)

### Problem

Comparative batch analysis showed 4 TME sections at **0/8 tools** coverage:

| Section | Before | Root Cause |
|---|---|---|
| Version Pinning | 0/8 | Version strings live in code/config, not prose |
| Design Intent and Tradeoffs | 0/8 | Rationale in headings/comparison tables, filtered by prose gate |
| Operational Behavior and Edge Cases | 0/8 | Warnings, error handling, retries — all code-shaped |
| Conceptual Model and Solution Recipes | 0/8 | Tutorial flows fail action-verb filter in workflow extractor |

The prose gate (`is_prose_block`: letter_ratio ≥0.65, symbol_ratio ≤0.08)
correctly rejects code — but these sections *are* code/config/structural signal.

### Solution: 4 new extractors, 14 new pattern kinds

**extraction.py** — Added 4 structural extractors that bypass the prose gate:

1. **`_extract_version_pins`** → `version_header`, `version_constraint`,
   `pinned_dependencies`, `version_pin_guidance`
   - Sources: API version headers (`Notion-Version`, `X-API-Version`),
     semver in config context, pinned dependency manifests, version-pin prose

2. **`_extract_design_intent`** → `design_rationale`, `comparison_table`,
   `tradeoff_reasoning`
   - Sources: design/philosophy/rationale headings with body content,
     markdown comparison tables (≥3 rows), "we chose X over Y" language

3. **`_extract_operational_behavior`** → `warning_admonition`,
   `error_handling_pattern`, `retry_backoff_pattern`, `edge_case_documentation`
   - Sources: warning/caution/note blocks, try/catch and status-code checks,
     retry/backoff/rate-limit patterns, explicit edge case documentation

4. **`_extract_conceptual_model`** → `quickstart_flow`,
   `conceptual_explanation`, `tutorial_progression`
   - Sources: getting-started/quickstart/overview headings, mental-model
     language ("think of it as", "under the hood"), tutorial step progressions

### Integration points modified

| File | Change |
|---|---|
| `extraction.py` | +4 extractors, +14 pattern kinds, wired into `extract_from_source` |
| `extraction.py` | `PATTERN_SECTION_MAP`: 8 → 22 entries |
| `mapping.py` | `_PATTERN_SECTION_MAP`: 12 → 26 entries (mirrored) |
| `draft.py` | `_CODE_FENCE_KINDS` +4, `_ORDERED_KINDS` +2, `_PATTERN_LABELS` +14 |

### Validation results

Synthetic test content covering all 4 target sections:

| Section | Patterns extracted | Confidence | Sourced? |
|---|---|---|---|
| Version Pinning | 4 (header, constraint, deps, guidance) | high/medium | ✓ |
| Design Intent and Tradeoffs | 3 (rationale, table, reasoning) | high | ✓ |
| Operational Behavior and Edge Cases | 4 (warning, error, retry, edge) | high/medium | ✓ |
| Conceptual Model and Solution Recipes | 3 (quickstart, conceptual, tutorial) | high/medium | ✓ |

All patterns route correctly through `_apply_pattern_evidence()` →
`sourced=True` → `build_drafts()` → rendered markdown with `[SOURCE: url]`.

### Coverage impact

| Metric | Before | After |
|---|---|---|
| Pattern kinds in PATTERN_SECTION_MAP | 8 | 22 |
| TME sections reachable by patterns | 4/19 | 8/19 |
| Sections with 0/8 structural coverage | 4 | 0 (all recoverable) |
| Pattern contribution to coverage | ~5% | expanded by 14 new extraction channels |

### Design principle applied

Do not look for meaning in text. Extract meaning from structure.

The prose gate stays strict — it correctly rejects code. But code IS the signal
for these 4 sections. The pattern extractors read structure (version headers,
comparison tables, warning blocks, tutorial steps) and route through the
established pattern-priority architecture, bypassing the prose gate entirely.
