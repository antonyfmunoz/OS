# Tool Mastery Author Agent

**Location:** `/opt/OS/core/tool_mastery_author_agent/`
**Status:** v1 — source-grounded drafting, no LLM, verifier-gated
**Introduced:** 2026-04-08

The Author Agent is the **authoring layer** between research and
verification in the Tool Mastery pipeline:

```
detect → classify → queue → research → [AUTHOR] → verify → ready
                                        ^^^^^^
                                        this agent
```

Its single job is to read a source-grounded `research_artifact.json`
produced by the Tool Mastery Research Agent and draft or refresh a
tool skill in a truthful, verifier-aware, traceable way.

---

## What the Author Agent does

1. **Loads** a research artifact and all its successfully fetched
   raw captures off disk.
2. **Maps** the captured material onto the 19 canonical TME
   best-practices sections using conservative keyword scanning.
3. **Drafts** bounded excerpts for every section that has real
   evidence, and honest placeholders for every section that does
   not.
4. **Reconciles** the drafts against the current on-disk skill:
   - No skill → scaffold (via the canonical `scaffold_tool_skill.py`)
     and write drafts to both files.
   - Scaffold on disk → overwrite placeholders with drafts.
   - Real human-authored skill → preserve untouched.
   - `--force-rewrite` → overwrite everything (destructive opt-in).
5. **Verifies** the result by shelling out to
   `scripts/verify_tool_skill.py --skill <slug> --json`.
6. **Reports** a final state (one of four) and writes an
   `authored_provenance.json` sidecar next to the research artifact.

---

## What the Author Agent does NOT do

- **No LLM synthesis.** Every drafted sentence is either a verbatim
  bounded excerpt from a fetched source or a boilerplate honest
  placeholder. This is deliberate: it makes fabrication structurally
  impossible, not just discouraged.
- **No prose generation for Tier 2 creator-intelligence sections.**
  Design Intent, Trajectory, Industry Expert, etc. almost always
  require human creator research. The agent marks them Uncovered by
  default.
- **No destructive rewrites of human-authored skills** unless the
  caller passes `--force-rewrite`. A skill with fewer than 5
  `[To be filled` scaffold markers is treated as human content.
- **No frontmatter mutation.** `source_url` and `last_researched`
  are already maintained by the Research Agent's handoff step
  (`core/tool_mastery_research_agent/handoff.py`). The Author Agent
  preserves existing YAML frontmatter when rewriting the body.
- **No production gotchas.** Those require real incidents; the
  scaffold leaves a `Gotchas` section placeholder that compounds
  over time.

---

## How it uses research artifacts

The input is a `research_artifact.json` at:

```
/opt/OS/logs/tool_mastery_research/<tool_slug>/<timestamp>/research_artifact.json
```

That JSON has the shape:

```jsonc
{
  "schema_version": 1,
  "plan": { "tool_slug": "...", "sources": [...] },
  "artifact": {
    "tool_slug": "notion",
    "mode": "research",
    "sources": [
      {
        "ref": { "url": "...", "tier": "official_docs", "label": "..." },
        "status": "ok",
        "raw_path": "raw/01_developers.notion.com_root.txt",
        "bytes": 311915,
        "http_status": 200
      }
    ],
    "section_coverage": [
      {
        "section": "Authentication",
        "has_source": false,           // honest default
        "source_urls": [...],
        "note": "raw captures available; authoring pass must verify coverage"
      }
    ]
  }
}
```

The research agent's `section_coverage` defaults every row to
`has_source: false` — it does NOT auto-grade coverage. The Author
Agent is the thing that actually reads `raw/*.txt` and decides which
sections have evidence.

---

## How provenance is preserved

Every run writes an **`authored_provenance.json`** sidecar alongside
the research artifact:

```jsonc
{
  "tool_slug": "notion",
  "authored_at": "2026-04-09T01:10:28Z",
  "run_dir": "/opt/OS/logs/tool_mastery_research/notion/<stamp>",
  "drafts": [
    {
      "section": "Authentication",
      "content": "_Source-grounded excerpts..._\n**Excerpt 1:** > ...",
      "sourced": true,
      "source_urls": ["https://developers.notion.com/"],
      "raw_paths": ["/opt/OS/logs/.../raw/01_..."],
      "rationale": "5 keyword hits across 1 source(s)"
    }
  ],
  "preserved_sections": [],
  "notes": [...]
}
```

In addition:

- **Section badges** in `best_practices.md` explicitly mark
  `**Status:** Sourced` or `**Status:** Uncovered`.
- **Excerpt blocks** are wrapped in `> ` blockquotes with a
  visible "Sources:" list.
- **Weak signals** (sub-threshold keyword hits) are shown as
  `_Weak signals observed (below 2-hit threshold): ..._` so a
  reviewer can see why the Author Agent declined to mark a
  section sourced.
- **Every authored section** carries a trailing line:
  `> _Authored by tool_mastery_author_agent from source-grounded
  excerpts. Human review recommended..._`

Auditing is therefore a grep: find every `**Status:** Uncovered`
and every `Authored by tool_mastery_author_agent` and you have
the full machine-authored footprint.

---

## Verifier-aware drafting

The Author Agent knows what `scripts/verify_tool_skill.py` requires
and satisfies only the **structural** requirements truthfully:

| Requirement | How the Author Agent satisfies it |
|---|---|
| SKILL.md ≥ 500 chars | Rendered body always exceeds 500 chars. |
| `Authentication` + `Gotchas` H2/H3 sections | Always emitted. |
| Valid YAML frontmatter with required keys | Preserved from scaffold / research handoff. |
| `best_practices.md` ≥ 2000 chars | 19 placeholder sections easily clear this. |
| All 19 required best-practices sections | Always emitted in canonical order. |
| Canonical snake_case slug | Inherited from scaffold. |

The Author Agent does **NOT** try to game the verifier by writing
fake content just to pass. If the research layer produced zero
evidence, 19 honest "Uncovered" placeholders are written. The
verifier passes on structure and the run ends in `AUTHORED_PARTIAL`
— a deliberate, honest signal that the tool is not actually
mastered, only scaffolded.

### Section name alignment

Verifier accepts section names via prefix matching in
`_tme_common.section_present()`, so the long-form canonical
headings used by the Author Agent (matching
`core.tool_mastery_research_agent.artifact.TME_SECTIONS`) satisfy
the verifier's short-form required sections:

| Verifier requires | Author Agent writes |
|---|---|
| `Core Operations` | `## Core Operations with Exact Signatures` |
| `Pagination` | `## Pagination Patterns` |
| `Error Codes` | `## Error Codes and Recovery` |
| `Webhooks` | `## Webhooks and Events` |
| `Design Intent` | `## Design Intent and Tradeoffs` |
| `Problem-Solution Map` | `## Problem-Solution Map and Hidden Capabilities` |
| `Operational Behavior` | `## Operational Behavior and Edge Cases` |
| `Ecosystem Position` | `## Ecosystem Position and Composition` |
| `Trajectory` | `## Trajectory and Evolution` |
| `Conceptual Model` | `## Conceptual Model and Solution Recipes` |
| `Industry Expert` | `## Industry Expert and Cutting-Edge Usage` |

One source of truth lives in `mapping.py:TME_SECTIONS`.

---

## Integration with Manager and Research Agent

The Author Agent **consumes** what the Research Agent produces:

```
Manager                Research Agent             Author Agent         Verifier
  |                         |                          |                  |
  | ensure_mastery(slug)    |                          |                  |
  |------------------------>| research run             |                  |
  |                         | writes run_dir/          |                  |
  |                         |   research_artifact.json |                  |
  |                         |   raw/*.txt              |                  |
  |                         |   handoff.json           |                  |
  |                         |                          |                  |
  | author(--tool slug --latest)                       |                  |
  |-------------------------------------------------->| scaffold?         |
  |                         |                          | draft             |
  |                         |                          | write files       |
  |                         |                          | provenance        |
  |                         |                          |--verify_skill()-->|
  |                         |                          |<-----passed-------|
  |                         |                          |                  |
  | AuthorResult(status)    |                          |                  |
```

The Author Agent does NOT bypass the Control Plane — it reads
files, writes files under `skills/tools/`, and shells out to two
canonical scripts (`scaffold_tool_skill.py` and
`verify_tool_skill.py`). Orchestration through the Manager or a
future dispatcher can wrap `author()` in a governed `run_action`
exactly like the Research Agent is wrapped today.

---

## Output states

Every authoring run ends in exactly one of four states:

| State | Meaning |
|---|---|
| `AUTHORED_READY` | Verifier passes AND either (a) every section was sourced or (b) an existing human-authored skill was preserved untouched. The tool is ready. |
| `AUTHORED_PARTIAL` | Verifier passes BUT one or more sections on disk are honest Uncovered placeholders. Real improvements were written, structure is valid, but mastery is not complete. |
| `BLOCKED_NO_SOURCES` | The research artifact has zero successfully fetched sources. Nothing the Author Agent can do — research-layer problem. |
| `VERIFY_FAILED` | The Author Agent wrote content but the canonical verifier still fails. Hard stop — tool is NOT ready. |

There are NO additional vague states (e.g. "in progress",
"reviewed", "uploaded"). The orchestration layer must treat these
four as exhaustive.

---

## Limitations

- **Keyword scanning is crude.** An HTML capture that discusses
  authentication only in a `/login` footer link will probably not
  trip the Authentication keyword set. The trade-off is
  reproducibility and zero fabrication; false negatives are
  preferred over false positives.
- **HTML stripping is naive** (regex-based, no BS4). Large SPA
  shells with JS-rendered docs (e.g. `stitch.withgoogle.com`)
  yield thin plain text. This is visible in the provenance — it
  is not a silent failure.
- **No sub-page crawling.** The research agent fetches one level;
  deep API reference trees are out of scope.
- **Tier 2 creator intelligence** is almost always marked Uncovered
  because landing-page HTML rarely contains Design Intent,
  Trajectory, or Industry Expert content. That is correct.
- **Refresh of existing strong skills** currently preserves them
  entirely; selective section-by-section refresh (e.g. "only
  update Rate Limits if the source says something new") is a
  future enhancement.
- **`[To be filled` detection** is heuristic (≥ 5 markers). A
  human halfway through filling a scaffold who has replaced 4
  placeholders could still be treated as a scaffold and clobbered
  — but only on a non-force run where `will_write_skill_md` is
  further guarded by checking for remaining placeholders. The
  five-marker threshold was chosen to bias toward preservation.

---

## CLI

```bash
# Author from a specific research artifact
python3 -m core.tool_mastery_author_agent \
    --tool notion \
    --artifact /opt/OS/logs/tool_mastery_research/notion/<stamp>/research_artifact.json

# Consume the latest run for a tool
python3 -m core.tool_mastery_author_agent --tool stitch --latest

# Refuse to scaffold a missing tool (just report)
python3 -m core.tool_mastery_author_agent --tool foo --latest --no-scaffold

# Force rewrite of an existing human-authored skill (destructive)
python3 -m core.tool_mastery_author_agent --tool foo --latest --force-rewrite

# Machine-readable result for scripting
python3 -m core.tool_mastery_author_agent --tool notion --latest --json
```

Exit codes: `0` = AUTHORED_READY or AUTHORED_PARTIAL,
`1` = VERIFY_FAILED or BLOCKED_NO_SOURCES, `2` = bad invocation.

---

## Files

```
core/tool_mastery_author_agent/
├── __init__.py         # public exports
├── __main__.py         # python -m entry point
├── paths.py            # EOS_ROOT-aware path constants
├── models.py           # AuthorRequest, AuthorResult, AuthorStatus, SectionDraft, AuthoredProvenance
├── loader.py           # research_artifact.json + raw captures → LoadedArtifact
├── mapping.py          # TME_SECTIONS, SECTION_KEYWORDS, map_sections(), scan rules
├── draft.py            # SectionDraft → markdown, render_best_practices(), render_skill_body()
├── reconcile.py        # decide scaffold/write/preserve, shell out to scaffold_tool_skill.py
├── verify.py           # shell out to verify_tool_skill.py --json
├── agent.py            # orchestrator: author(request) -> AuthorResult
└── cli.py              # argparse + main()
```
