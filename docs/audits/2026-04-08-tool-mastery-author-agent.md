# Tool Mastery Author Agent — Build Audit

**Date:** 2026-04-08
**Scope:** New subsystem `core/tool_mastery_author_agent/`
**Pipeline position:** `research → [AUTHOR] → verify → ready`

---

## 1. What existed already

Before this build, the Tool Mastery pipeline had four real layers
and one manual gap:

| Layer | Package | Status |
|---|---|---|
| TME core (verifier, registry, staleness, graph, sync, query) | `skills/meta/tool_mastery_engine/` + `scripts/verify_tool_skill.py` + `scripts/_tme_common.py` | solid |
| Tool Mastery Manager (discovery, coverage, ensure, backlog, maintenance, queueing) | `core/tool_mastery_manager/` | solid |
| Tool Mastery Research Agent (source discovery, fetch, artifact, handoff, CLI, dispatcher) | `core/tool_mastery_research_agent/` | solid |
| Control Plane + Orchestrator (governed execution, queueing, handlers) | `core/action_system/` | solid |
| **Authoring** (research_artifact.json → authored skill content) | — | **missing, manual** |

Key constraints I confirmed by reading the real files (not summaries):

- **Verifier contract** — `scripts/verify_tool_skill.py` and
  `scripts/_tme_common.py` together require: SKILL.md ≥ 500 chars
  with `Authentication` + `Gotchas` sections, valid YAML frontmatter
  with keys `name`/`description`/`last_researched`/`source_url`,
  `references/best_practices.md` ≥ 2000 chars with all 19 canonical
  sections, snake_case slug matching frontmatter name.
  Section matching is **tolerant** (`section_present()` does prefix
  matching, so long-form headings like
  `## Core Operations with Exact Signatures` satisfy the short-form
  required section `Core Operations`).

- **Research artifact shape** — JSON at
  `logs/tool_mastery_research/<slug>/<stamp>/research_artifact.json`
  with wrapper `{schema_version, plan, artifact}`. Raw captures
  live under `raw/*.txt`, referenced by relative `raw_path` on each
  `artifact.sources[]` entry. The `section_coverage` ledger is
  **honest-default** — every row starts `has_source: false` and the
  research agent deliberately does NOT auto-grade coverage. That is
  the Author Agent's job.

- **Scaffolder** —
  `skills/meta/tool_mastery_engine/scripts/scaffold_tool_skill.py`
  creates a SKILL.md + best_practices.md from
  `templates/tools/_template/` with `[To be filled ...]` placeholders
  under every section. The Manager already shells out to this
  script rather than importing it, to preserve it as the single
  source of truth for the template layout.

- **Handoff already covers metadata** —
  `core/tool_mastery_research_agent/handoff.py:apply_safe_metadata`
  already applies `source_url` and `last_researched` to existing
  frontmatter. The Author Agent must NOT duplicate this —
  authoring starts at content population (bodies, section text).

- **No prior Author Agent existed.** The notion skill was
  hand-written; stitch and notebooklm_mcp had research runs but
  no skills on disk at all.

---

## 2. What was built

New package `core/tool_mastery_author_agent/` (11 files, ~900 LOC):

```
core/tool_mastery_author_agent/
├── __init__.py
├── __main__.py         # python -m entry point
├── paths.py            # EOS_ROOT-aware
├── models.py           # AuthorRequest, AuthorResult, AuthorStatus, SectionDraft, AuthoredProvenance
├── loader.py           # research_artifact.json + raw captures → LoadedArtifact
├── mapping.py          # TME_SECTIONS, SECTION_KEYWORDS, map_sections()
├── draft.py            # render_best_practices(), render_skill_body()
├── reconcile.py        # plan_reconciliation(), run_scaffold(), preserve logic
├── verify.py           # shell out to verify_tool_skill.py --json
├── agent.py            # author(request) -> AuthorResult orchestrator
└── cli.py              # argparse + main()
```

Commits (clean logical chunks):

1. `tool_mastery_author_agent: package skeleton + models + loader + mapping + draft + reconcile + verify + agent + cli`
2. `tool_mastery_author_agent: preserve-mode counters + AUTHORED_READY status`
3. `docs: tool_mastery_author_agent reference + build audit` (this file)

---

## 3. Authoring strategy

**Core rule: no LLM, no synthesis, no prose generation.** The
Author Agent is a keyword-based extractor that produces bounded
excerpts from fetched raw captures. This is deliberate — it makes
fabrication structurally impossible, not just discouraged.

Section-to-evidence mapping:

- 19 canonical TME sections (matching
  `core.tool_mastery_research_agent.artifact.TME_SECTIONS`)
- A conservative keyword set per section (e.g. Authentication →
  `{authentication, authorization, api key, api token, bearer,
   oauth, access token, integration token}`)
- **2-hit minimum**: a section is marked `sourced=True` only when
  at least 2 distinct keywords from its set appear in at least
  one raw capture (case-insensitive). 1-hit matches are reported
  as "weak signals observed" but do NOT promote to sourced.
- Excerpts are bounded: ≤ 600 chars each, ≤ 3 per section.

Reconciliation decision tree:

| State on disk | `force_rewrite` | Action |
|---|---|---|
| No skill directory | any | scaffold + write both files |
| Scaffold (≥ 5 `[To be filled` markers) | `False` | overwrite best_practices; rewrite SKILL.md body only if it still has scaffold markers; preserve frontmatter |
| Human-authored skill | `False` | **preserve untouched** |
| Any of the above | `True` | overwrite both files from drafts (destructive opt-in) |

Output is always written in canonical TME section order as H2
headings, each with an explicit `**Status:** Sourced` or
`**Status:** Uncovered` badge, so a human reviewer can grep.

---

## 4. Provenance model

Every run writes `authored_provenance.json` next to the research
artifact under `logs/tool_mastery_research/<slug>/<stamp>/`:

```jsonc
{
  "tool_slug": "stitch",
  "authored_at": "2026-04-09T01:10:28Z",
  "run_dir": "/opt/OS/logs/tool_mastery_research/stitch/2026-04-08T23-26-05Z",
  "drafts": [
    {
      "section": "Authentication",
      "content": "...",
      "sourced": false,
      "source_urls": [],
      "raw_paths": [],
      "rationale": "no keywords matched"
    }
  ],
  "preserved_sections": [],
  "notes": [
    "scaffold: CREATED ...",
    "wrote /opt/OS/skills/tools/stitch/references/best_practices.md"
  ]
}
```

In addition to the sidecar, authored markdown carries **inline**
provenance:

- `**Status:** Sourced` / `**Status:** Uncovered` badge under every
  section heading.
- Sourced sections quote bounded excerpts inside `> ` blockquotes
  with a trailing `**Sources:**` bullet list of URLs.
- Uncovered sections that had sub-threshold hits display
  `_Weak signals observed (below 2-hit threshold): ..._` so
  reviewers can see why the agent declined to promote them.
- Every authored section trails with
  `> _Authored by tool_mastery_author_agent from source-grounded
  excerpts. Human review recommended before treating as
  creator-level mastery._`

Auditing the machine-authored footprint reduces to a grep.

---

## 5. Verifier-aware rules

The Author Agent satisfies the verifier's **structural** requirements
always, without fabricating content to pass:

- All 19 section headings emitted in canonical long-form order
  (which prefix-matches the verifier's short-form required sections
  via `_tme_common.section_present()`).
- `Authentication` + `Gotchas` sections present in SKILL.md.
- Frontmatter preserved across body rewrites (see
  `reconcile.replace_body_preserving_frontmatter`) so the
  research-agent handoff's `source_url` and `last_researched`
  updates survive.
- Both files exceed their minimum-length thresholds via the
  19-section scaffold even when every section is Uncovered.

Truth guardrails:

- No empty-fluff filler to pad length.
- No fake SDK or API version strings.
- No fabricated Gotchas from thin sources — scaffold placeholder
  stays until real incidents compound.
- Verifier is authoritative: the Author Agent's final state is
  gated on `scripts/verify_tool_skill.py --skill <slug> --json`
  returning `passed: true`.

---

## 6. Validation results

Three real cases were run against existing research artifacts.

### Case 1 — `notion` (strong human-authored skill)

| Metric | Value |
|---|---|
| Status | **AUTHORED_READY** |
| Sections sourced | 0 |
| Sections placeholder | 0 |
| Sections preserved | 19 |
| Verifier passed | ✅ true |
| Files modified | none |

Behavior: Reconciler detected an existing human-authored skill
(fewer than 5 `[To be filled` markers in the 926-line
`best_practices.md`), refused to overwrite, preserved everything
untouched, verifier passed because the human-authored content
already satisfies all structural requirements. This is the correct
behavior against a strong existing skill — **the Author Agent
never clobbered real human work.**

### Case 2 — `stitch` (missing skill, thin research: SPA shell only)

| Metric | Value |
|---|---|
| Status | **AUTHORED_PARTIAL** |
| Sections sourced | 0 |
| Sections placeholder | 19 |
| Sections preserved | 0 |
| Verifier passed | ✅ true |
| Files created | SKILL.md, references/best_practices.md |
| Scaffold | invoked (`CREATED:` messages in notes) |

Behavior: The research run for stitch captured
`stitch.withgoogle.com/` (23 KB of Google SPA shell HTML), plus
404 and 405 errors on two other sources. The 23 KB shell contained
only `api` as a single weak keyword hit across all sections. The
Author Agent correctly refused to promote one-hit matches to
sourced and wrote 19 honest Uncovered placeholders. Verifier
passed because structure is satisfied; status is AUTHORED_PARTIAL
because real placeholders are on disk. **Truth-over-completeness
invariant held** — the agent did not fabricate depth from thin
captures.

Sub-threshold signals visible in the output:
- `Pagination Patterns`: `_Weak signals observed: cursor._`
- `Error Codes and Recovery`: `_Weak signals observed: 400._`

These are correctly reported without being promoted.

### Case 3 — `notebooklm_mcp` (missing skill, pypi page only)

| Metric | Value |
|---|---|
| Status | **AUTHORED_PARTIAL** |
| Sections sourced | 0 |
| Sections placeholder | 19 |
| Sections preserved | 0 |
| Verifier passed | ✅ true |
| Files created | SKILL.md, references/best_practices.md |

Behavior: Research captured `pypi.org/project/notebooklm-mcp/`
(3 KB) after the GitHub fetch failed. Three KB of pypi metadata
isn't enough signal for any TME section at the 2-hit threshold,
so every section is honest Uncovered. Same truthful outcome as
stitch.

### Coverage of the four output states

| State | Exercised by |
|---|---|
| `AUTHORED_READY` | Case 1 (notion, preserved) |
| `AUTHORED_PARTIAL` | Case 2 (stitch), Case 3 (notebooklm_mcp) |
| `BLOCKED_NO_SOURCES` | Not exercised against live data (would require a research run with zero OK fetches). Code path guarded by `loaded.has_any_source`. |
| `VERIFY_FAILED` | Not exercised against live data. Code path guarded on `report.passed` after structural write. |

The two unexercised states have dedicated code paths with explicit
early-return handling and provenance writes — they are just not
triggered by the three available research artifacts. A dedicated
test would need a research run that is valid JSON but has every
source in `status: "fetch_failed"` (or a manually corrupted
best_practices body post-author). That is a test hardening item,
not a v1 blocker.

### Fabrication check

Spot-inspected
`skills/tools/stitch/references/best_practices.md` after authoring:
every section contains the literal uncovered placeholder, no
made-up prose, no fabricated keys, no hallucinated API endpoints.
Every line is either scaffold boilerplate, the canonical
`⚠ **Uncovered.**` placeholder, a real keyword observation, or
section structure. **Zero fabrication detected.**

---

## 7. Honest limitations

1. **Keyword scanning is crude.** An HTML page that discusses
   authentication only via a `/login` footer link will not cross
   the 2-hit threshold. The trade-off is reproducibility and zero
   fabrication; we prefer false negatives (honest Uncovered) over
   false positives (fake mastery). This is the central design
   decision and should not be weakened.

2. **HTML stripping is naive** (regex-based). Large SPA shells with
   JS-rendered docs (e.g. `stitch.withgoogle.com`) yield thin
   plain text. This is visible in the provenance — it is not a
   silent failure — but it does mean some otherwise-rich sources
   will be under-mined.

3. **No sub-page crawling.** The research agent fetches one URL
   per source; deep API reference trees require multiple sources
   specified upfront. This is a research-layer limitation the
   author inherits.

4. **Tier 2 creator intelligence is almost always Uncovered.**
   Design Intent, Trajectory, Industry Expert content rarely
   lives in landing-page HTML. This is correct — those sections
   should be hand-authored.

5. **Refresh of existing strong skills preserves entirely.**
   Selective section-by-section refresh (e.g. "update only Rate
   Limits when the upstream doc changes") is a future enhancement.
   v1 is coarse-grained: preserve everything, or rewrite
   everything under `--force-rewrite`.

6. **Scaffold-detection heuristic is threshold-based** (≥ 5
   `[To be filled` markers). A human halfway through manually
   filling a scaffold who has replaced 4 placeholders could still
   be treated as scaffold. The threshold was chosen to bias
   toward preservation; it is adjustable in one place
   (`reconcile._looks_like_scaffold`).

7. **No LLM integration hook.** By design for v1. A future v2
   could add a gated `--llm-synthesize` mode that runs an LLM on
   raw captures and tags generated content with a distinct
   provenance badge, but v1 deliberately proves the pipeline
   works without fabrication risk.

8. **BLOCKED_NO_SOURCES and VERIFY_FAILED states are code-guarded
   but not live-validated.** Recommended test hardening: add a
   smoke test that synthesises a no-source artifact in a temp
   dir and asserts the state transition.

---

## 8. Recommended next step

**Wire the Author Agent into the Manager's ensure flow.**

Right now the Manager queues a `research` action via the Control
Plane when a tool is MISSING / STALE / INVALID / PARTIAL. After
research completes, authoring is still a manual `python3 -m
core.tool_mastery_author_agent --tool X --latest` invocation.

The natural next build is a handoff in the research dispatcher
(or a new author dispatcher) that, after a research run finishes
with `status in {ok, partial}`, queues a follow-on governed
action:

```
run_action(
    type="run_script",
    inputs={
        "path": "/opt/OS/scripts/tool_mastery_author_dispatcher.py",
        "args": ["--tool", slug, "--artifact", artifact_path],
        "work_type": "author",
        "tool": slug,
    },
    risk_level="medium",
    idempotency_key=f"tool_mastery:author:{slug}",
)
```

That closes the loop end-to-end:

```
detect → classify → queue research → research runs → queue author →
author runs → verify → READY (or PARTIAL / BLOCKED / VERIFY_FAILED)
```

Secondary next steps (smaller):

- Add unit tests for `loader`, `mapping` (keyword threshold edge
  cases), and `reconcile` (scaffold vs. human detection).
- Add a smoke test that synthesises a no-source artifact and
  asserts `BLOCKED_NO_SOURCES`.
- Expand `SECTION_KEYWORDS` per-section as real research runs
  reveal false negatives. This is a living dict.
- Consider a `--diff` mode that shows what would be written
  without actually writing, for safe review of refresh runs
  against strong skills.

None of these are v1 blockers. The Author Agent is shipped.
