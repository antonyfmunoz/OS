---
name: notebooklm
description: "Use when generating audio overviews from source documents, querying uploaded research for citation-backed answers, syncing EOS data into NotebookLM notebooks, or building brand guides from uploaded assets."
allowed-tools: "Read, Bash"
version: 1.0
source_url: "https://notebooklm.google.com"
last_researched: "2026-04-06"
instantiated_from: templates/tools/_template/
api_version: "N/A — web UI + community MCP CLI"
sdk_version: "jacob-bd/notebooklm-mcp-cli v0.5.9"
speed_category: slow
trigger: both
effort: medium
context: fork
---

# Tool: NotebookLM (Google)

## What This Tool Does

NotebookLM is Google's AI-powered research and synthesis tool built on Gemini.
It operates on user-uploaded source documents — not the open web — which means
every answer is grounded in and cited against specific sources you control.

Core capabilities used by EOS:
- **Source-grounded Q&A** — ask questions, get answers with inline citations
  pointing to exact passages in your uploaded documents
- **Audio Overviews** — generates podcast-style audio conversations (two AI hosts)
  that summarize and discuss your sources. 5-30 minute episodes.
- **Notebook Guides** — structured study guides, FAQs, timelines, and briefing
  docs auto-generated from sources
- **Multi-source synthesis** — upload up to 50 sources per notebook (PDFs, Google
  Docs, Slides, web URLs, YouTube videos, plain text, audio files) and query
  across all of them simultaneously
- **Interactive follow-up** — click any citation to see the source passage,
  then ask follow-up questions scoped to that source

NotebookLM has NO official public API. All programmatic access is through
the community-built MCP CLI (`nlm`) which automates the web interface via
browser automation.

## EOS Integration

### Primary module
`eos_ai/notebooklm_sync.py` — `NotebookLMSync` class. Bidirectional sync:
- **Neon -> NotebookLM**: pipeline data, world pulse reports, founder profile docs
- **NotebookLM -> Neon**: query results stored as `notebooklm_insight` events

### Where it connects
- **cognitive_loop.py** (Layer 1e-viii) — injects recent NotebookLM insights
  into DEX context for grounded research answers
- **world_pulse.py** — syncs pulse reports to `world_pulse` notebook after
  Saturday scans; triggers full cross-reference (pipeline + founder profile)
- **harness_registry.py** — registered as `notebooklm` harness, type TOOL,
  provides `grounded_research` and `citation_backed_answers`

### Notebook IDs (env vars)
```
NOTEBOOKLM_LYFE_ID=        # Lyfe Institute research notebook
NOTEBOOKLM_EMPYREAN_ID=    # Empyrean Creative research notebook
NOTEBOOKLM_BRAND_ID=       # Personal brand research notebook
NOTEBOOKLM_PULSE_ID=       # World pulse reports notebook
```

### MCP integration
MCP server: `jacob-bd/notebooklm-mcp-cli v0.5.9`
Toggle: `@notebooklm-mcp` in Claude Code (35 tools — disable when not in use)
Install: `nlm setup add claude-code`

## Authentication

### Google account auth (no API key)
NotebookLM authenticates via Google account session. There is no API key,
no OAuth client ID, no service account flow. This is a web product with
browser-based auth only.

**Setup flow:**
1. Run `nlm login` interactively (first time only)
2. Opens Chrome profile — sign in with Google account
3. Session persists in browser profile after first login
4. Headless operation works after initial interactive login

**EOS convention:**
- Use a dedicated Google account, not the founder's primary account
- Session cookies expire — re-auth required periodically (no formal expiry documented)
- If `nlm` commands start failing silently, re-run `nlm login`

**Limitation:** No programmatic token refresh. No service account.
No headless-from-scratch auth. The Chrome profile dependency means
NotebookLM automation is tied to a specific machine where `nlm login`
was run.

## Quick Reference

### List all notebooks
```bash
nlm notebook list
```

### Create a notebook
```bash
nlm notebook create "Lyfe Institute Research"
# Returns notebook ID — store in .env
```

### Add a source (file)
```bash
nlm source add <notebook_id> --file /path/to/document.pdf
```

### Add a source (URL)
```bash
nlm source add <notebook_id> --url https://example.com/article
```

### Query a notebook
```bash
nlm notebook query <notebook_id> --question "What are the top 3 competitor strategies?"
```

### Generate audio overview
Done via web UI at notebooklm.google.com:
1. Open notebook
2. Click "Audio Overview" in the notebook guide panel
3. Optionally provide custom instructions for focus/tone
4. Wait 2-5 minutes for generation
5. Play or download the audio

No CLI command for audio generation — this is web-only.

### EOS sync pattern (Python)
```python
from eos_ai.context import load_context_from_env
from eos_ai.notebooklm_sync import NotebookLMSync

ctx = load_context_from_env()
nls = NotebookLMSync(ctx)

# Neon -> NotebookLM
nls.sync_world_pulse_to_notebook(report_text)
nls.sync_pipeline_to_notebook('lyfe_institute')
nls.sync_founder_profile()

# NotebookLM -> Neon
answer = nls.query_for_context('lyfe_institute', 'What is our ICP?')

# Get cached insights for DEX
insights = nls.get_recent_insights(venture_id='lyfe_institute', limit=5)
```

## Conceptual Model

```
NotebookLM
  |
  +-- Notebook (container — up to 100 per account)
  |     |
  |     +-- Sources (up to 50 per notebook)
  |     |     |-- Google Docs, Slides, PDF, TXT, Markdown
  |     |     |-- Web URLs (crawled and indexed)
  |     |     |-- YouTube videos (transcript extracted)
  |     |     |-- Audio files (transcribed)
  |     |     +-- Each source: max 500,000 words
  |     |
  |     +-- Notes (user-created or AI-generated)
  |     |     |-- Saved queries and responses
  |     |     +-- User annotations
  |     |
  |     +-- Notebook Guide (auto-generated)
  |     |     |-- FAQ, Study Guide, Timeline, Briefing Doc
  |     |     +-- Table of Contents
  |     |
  |     +-- Audio Overview
  |           |-- Podcast-style two-host conversation
  |           |-- 5-30 minutes depending on source volume
  |           |-- Custom instructions for focus/tone
  |           +-- Downloadable as audio file
  |
  +-- nlm CLI (community MCP — browser automation)
  |     |-- nlm login        — Google auth via Chrome
  |     |-- nlm notebook *   — CRUD + query
  |     |-- nlm source *     — add/remove sources
  |     +-- 35 MCP tools exposed to Claude Code
  |
  +-- Gemini backbone
        |-- All responses grounded in uploaded sources only
        |-- Inline citations point to exact source passages
        +-- No web search — sources are the entire knowledge base
```

See references/best_practices.md for limits, anti-patterns, and advanced recipes.

## Gotchas

### No official API — all automation is fragile
NotebookLM has zero official API surface. The `nlm` CLI uses browser automation
which can break on any Google UI update. Treat all automated workflows as
best-effort, not guaranteed. Always have a manual fallback.

### Audio overview generation is web-only
There is no CLI or API endpoint to trigger audio overview generation.
You must use the web UI at notebooklm.google.com. This means audio
generation cannot be automated in EOS pipelines.

### Session cookie expiry causes silent failures
`nlm` commands fail silently (return empty output, exit code 0) when the
Google session expires. The fix is `nlm login` — but this requires
interactive browser access. Monitor for empty responses.

### Source upload has no confirmation callback
`nlm source add` returns before the source is fully indexed. Querying
immediately after adding a source may not include that source's content.
Wait 30-60 seconds after adding sources before querying.

### 50 source limit per notebook
Each notebook supports a maximum of 50 sources. For EOS ventures with
many documents, you must curate which sources are most relevant rather
than dumping everything in.

### 500,000 word limit per source
Individual sources cannot exceed 500,000 words (~750 pages). Large PDFs
or doc collections need to be split before upload.

### Chrome profile lock on VPS
The `nlm` CLI uses a Chrome profile directory. If another process (e.g.,
Playwright, another nlm instance) locks the profile, `nlm` commands hang
indefinitely. Only run one `nlm` operation at a time.

### 35 MCP tools consume context window
When `@notebooklm-mcp` is toggled on, 35 tool definitions are injected into
the Claude Code context. Always toggle off when not actively using NotebookLM
to preserve context for other operations.

### NotebookLM answers are grounded but not infallible
Grounded means every claim cites a source — it does not mean the interpretation
is correct. The Gemini model can still misinterpret source content, especially
with ambiguous or contradictory sources. Always verify critical insights.
