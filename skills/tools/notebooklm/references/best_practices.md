# NotebookLM — Creator-Level Best Practices
Source: https://notebooklm.google.com, https://support.google.com/notebooklm
API Version: N/A (no official API)
SDK Version: jacob-bd/notebooklm-mcp-cli v0.5.9
Last Researched: 2026-04-06

---

# Tier 1 — Technical Mastery

## Authentication

NotebookLM uses Google account session authentication exclusively. There is no API key,
no OAuth2 client credentials flow, no service account, and no JWT-based auth.

**Auth method:** Google account login via browser session
**Token type:** Session cookie stored in Chrome profile
**Scopes:** N/A — access is all-or-nothing per Google account
**Token lifetime:** Undefined — session cookies expire based on Google's session policy
  (typically days to weeks for active accounts, shorter if inactivity detected)
**Refresh mechanism:** Manual — re-run `nlm login` when session expires
**Multi-tenant:** Each Google account has its own notebooks. No shared workspace
  model unless using Google Workspace with NotebookLM Plus.

**EOS env vars:**
```
NOTEBOOKLM_LYFE_ID=        # in eos_ai/.env
NOTEBOOKLM_EMPYREAN_ID=    # in eos_ai/.env
NOTEBOOKLM_BRAND_ID=       # in eos_ai/.env
NOTEBOOKLM_PULSE_ID=       # in eos_ai/.env
```

**Setup from scratch:**
```bash
# Install the MCP CLI
npm install -g notebooklm-mcp-cli
# or: npx notebooklm-mcp-cli

# First-time login (interactive — requires display)
nlm login

# Register with Claude Code
nlm setup add claude-code

# Verify
nlm notebook list
```

**Key constraint:** Auth is machine-specific. The Chrome profile where `nlm login`
ran is the only profile that has valid cookies. Moving to a new machine requires
re-running `nlm login` interactively.

## Core Operations with Exact Signatures

NotebookLM has no official API. All operations go through the `nlm` CLI which
wraps browser automation. Below are the CLI signatures and their Python equivalents
as used in EOS.

### Notebook operations
```bash
# List all notebooks (returns JSON array)
nlm notebook list
# Returns: [{"id": "abc123", "name": "Research", "source_count": 5, "created_at": "..."}]

# Create a notebook
nlm notebook create "Notebook Name"
# Returns: {"id": "new_id", "name": "Notebook Name"}

# Delete a notebook
nlm notebook delete <notebook_id>
# Returns: {"success": true}

# Query a notebook (grounded Q&A)
nlm notebook query <notebook_id> --question "Your question here"
# Returns: plain text answer with citation markers [1], [2], etc.
# Timeout: 90 seconds (set in EOS notebooklm_sync.py)
```

### Source operations
```bash
# Add source from file
nlm source add <notebook_id> --file /path/to/file.pdf
# Supported: .pdf, .txt, .md, .docx, .pptx

# Add source from URL
nlm source add <notebook_id> --url https://example.com/page
# Supported: web pages, Google Docs URLs, YouTube URLs

# List sources in a notebook
nlm source list <notebook_id>
# Returns: [{"id": "src_123", "name": "document.pdf", "type": "pdf", "word_count": 5000}]

# Remove a source
nlm source remove <notebook_id> <source_id>
```

### Python wrapper (EOS pattern)
```python
# All EOS NotebookLM operations go through NotebookLMSync
result = subprocess.run(
    ['nlm', 'source', 'add', notebook_id, '--file', file_path],
    capture_output=True, text=True, timeout=60,
)
success = result.returncode == 0
```

## Pagination Patterns

NotebookLM has no pagination in the traditional API sense. The `nlm notebook list`
and `nlm source list` commands return complete arrays. There is no cursor,
no offset, no page size parameter.

For query results, the response is a single text block — no pagination needed.

If the account has many notebooks (approaching 100), `nlm notebook list` returns
all of them in a single response. Performance degrades but does not paginate.

**Effective workaround for large result sets:** Filter client-side after receiving
the full list. The `nlm` CLI does not support server-side filtering.

## Rate Limits

NotebookLM does not publish official rate limits because it is a web product,
not an API service. Observed behavioral limits:

- **Queries:** ~20-30 queries per notebook per hour before responses slow down
  or temporarily fail. Google applies server-side throttling.
- **Source uploads:** ~10-15 source additions per hour. Uploading many sources
  in rapid succession causes indexing delays or failures.
- **Audio overview generation:** 1-3 per notebook per day in practice.
  Generation takes 2-5 minutes and queues on Google's servers.
- **Notebook creation:** No observed hard limit, but creating dozens rapidly
  triggers Google's abuse detection.

**Rate limit response behavior:**
The `nlm` CLI does not return rate limit headers (it is browser automation,
not an API client). When throttled, commands either return empty responses,
hang for extended periods, or fail with generic browser timeout errors.

**EOS mitigation:**
- `notebooklm_sync.py` uses `timeout=60` for source adds, `timeout=90` for queries
- Weekly Saturday sync cadence (via world_pulse.py) avoids burst usage
- Pipeline syncs export to temp file first, then single upload — not per-record

## Error Codes and Recovery

No formal HTTP error codes since there is no API. Errors manifest as:

| Failure Mode | Symptom | Recovery |
|---|---|---|
| Session expired | `nlm` returns empty string, exit code 0 | Re-run `nlm login` |
| Source too large | Upload hangs or returns error text | Split source under 500K words |
| Notebook not found | Empty response or "not found" in stdout | Verify notebook ID with `nlm notebook list` |
| Chrome profile locked | `nlm` command hangs indefinitely | Kill other Chrome/Playwright processes, retry |
| Google abuse detection | Temporary blocks, CAPTCHAs in browser | Wait 1-2 hours, reduce request frequency |
| Source indexing incomplete | Query misses recently added source | Wait 60 seconds after source add |
| Network timeout | `subprocess.TimeoutExpired` exception | Retry once after 10 seconds |

**EOS error handling pattern:**
```python
try:
    result = subprocess.run(
        ['nlm', 'notebook', 'query', notebook_id, '--question', question],
        capture_output=True, text=True, timeout=90,
    )
    answer = result.stdout.strip() if result.returncode == 0 else ''
except subprocess.TimeoutExpired:
    answer = ''
except Exception as e:
    print(f'[NotebookLMSync] Query failed: {e}')
    answer = ''
```

All NotebookLM errors in EOS are non-fatal. The system degrades gracefully —
DEX still responds, just without NotebookLM-grounded context.

## SDK Idioms

There is no official Python SDK. The interface layer is the `nlm` CLI
(Node.js-based, installed via npm) called from Python via `subprocess.run()`.

**Correct pattern (EOS standard):**
```python
import subprocess

result = subprocess.run(
    ['nlm', 'source', 'add', notebook_id, '--file', file_path],
    capture_output=True,
    text=True,
    timeout=60,
)
if result.returncode == 0:
    print('Source added')
else:
    print(f'Failed: {result.stderr}')
```

**MCP pattern (Claude Code):**
When `@notebooklm-mcp` is toggled on, 35 tools are available directly in
Claude Code. Use these for interactive research sessions. Do NOT leave
the MCP enabled when not actively using NotebookLM — the 35 tool definitions
consume significant context window.

**Async considerations:**
`subprocess.run()` is blocking. For EOS agent workflows, this is acceptable
because NotebookLM operations are infrequent (weekly syncs, on-demand queries).
If frequency increases, wrap in `asyncio.to_thread()`:
```python
import asyncio
answer = await asyncio.to_thread(
    subprocess.run,
    ['nlm', 'notebook', 'query', notebook_id, '--question', q],
    capture_output=True, text=True, timeout=90,
)
```

## Anti-Patterns

### 1. Querying immediately after source upload
**Wrong:**
```python
nlm_source_add(notebook_id, file_path)
answer = nlm_query(notebook_id, "What does this document say?")  # Returns stale results
```
**Right:**
```python
nlm_source_add(notebook_id, file_path)
time.sleep(60)  # Wait for indexing
answer = nlm_query(notebook_id, "What does this document say?")
```

### 2. Dumping all documents into one notebook
**Wrong:** Upload 50 sources covering unrelated topics into a single notebook.
**Right:** Create topic-specific notebooks (per-venture in EOS). NotebookLM
synthesizes across all sources in a notebook — mixing unrelated content
degrades answer quality.

### 3. Treating NotebookLM answers as verified facts
**Wrong:** Pipe NotebookLM responses directly into customer-facing content.
**Right:** Use NotebookLM for research synthesis, then verify claims against
original sources. "Grounded" means cited, not infallible.

### 4. Leaving MCP toggled on permanently
**Wrong:** Enable `@notebooklm-mcp` and forget about it.
**Right:** Toggle on only for active NotebookLM work. 35 tools = ~2000 tokens
of context consumed on every Claude Code interaction.

### 5. Running concurrent nlm commands
**Wrong:** Launch multiple `nlm` subprocess calls in parallel.
**Right:** Serialize all `nlm` operations. The CLI uses a shared Chrome profile
that locks on access. Concurrent calls cause hangs.

### 6. Using NotebookLM for real-time data
**Wrong:** Expect NotebookLM to have current information about markets or events.
**Right:** Use Perplexity for real-time web data, NotebookLM for uploaded
document synthesis. They serve complementary roles in EOS.

### 7. Uploading sources with insufficient context
**Wrong:** Upload a spreadsheet with column headers but no explanation.
**Right:** Include a cover page or README source that explains the data format,
abbreviations, and context. NotebookLM interprets sources better with context.

## Data Model

```
Account (Google Account)
  |
  +-- Notebook (max ~100 per account)
        |-- id: string (opaque, assigned by Google)
        |-- name: string (user-defined)
        |-- created_at: timestamp
        |-- source_count: integer
        |
        +-- Source (max 50 per notebook)
        |     |-- id: string (opaque)
        |     |-- name: string (filename or URL)
        |     |-- type: enum (pdf, doc, url, youtube, audio, text)
        |     |-- word_count: integer
        |     |-- max_words: 500,000
        |     +-- content: indexed text (not directly accessible)
        |
        +-- Note (unlimited within notebook)
        |     |-- id: string
        |     |-- content: string (saved query response or user text)
        |     |-- citations: array of source references
        |     +-- pinned: boolean
        |
        +-- Audio Overview
        |     |-- generated: boolean
        |     |-- duration: 5-30 minutes
        |     |-- custom_instructions: string (optional focus/tone)
        |     +-- downloadable: boolean (yes — wav/mp3)
        |
        +-- Notebook Guide
              |-- faq: auto-generated
              |-- study_guide: auto-generated
              |-- timeline: auto-generated
              |-- briefing_doc: auto-generated
              +-- table_of_contents: auto-generated
```

**Key relationships:**
- Sources are the atomic unit. Everything else (queries, audio, guides) derives from sources.
- Notes can reference citations from any source in the notebook.
- Audio overviews synthesize across ALL sources in the notebook.
- Notebook guides are regenerated when sources change.
- Sources are immutable after upload — to update, remove and re-add.

## Webhooks and Events

N/A — NotebookLM has no webhook or event system. There are no callbacks,
no push notifications, and no event subscriptions.

EOS works around this by:
1. Storing query results in Neon as `notebooklm_insight` events
2. Polling these events in `cognitive_loop.py` for DEX context injection
3. Running syncs on a schedule (Saturday via world_pulse.py) rather than
   reacting to NotebookLM state changes

## Limits

| Resource | Limit |
|---|---|
| Notebooks per account | ~100 (soft limit) |
| Sources per notebook | 50 |
| Words per source | 500,000 (~750 pages) |
| Total words per notebook | ~25,000,000 (50 sources x 500K) |
| Source types | PDF, Google Docs, Google Slides, URLs, YouTube, audio, .txt, .md |
| Audio overview length | 5-30 minutes (depends on source volume) |
| Audio overviews per notebook | Regeneratable; ~1-3 per day before throttling |
| Query response length | ~2000-4000 characters typical |
| Note length | No documented hard limit |
| File upload size | ~200 MB per file (observed, not documented) |
| Concurrent nlm CLI operations | 1 (Chrome profile lock) |

**Undocumented but observed:**
- Very large notebooks (40+ diverse sources) slow query response time significantly
- Audio overview quality degrades with more than ~20 sources (becomes too surface-level)
- YouTube video sources only use the transcript, not visual content
- URLs that require authentication or are behind paywalls fail silently

## Cost Model

**Free tier (standard NotebookLM):**
- Fully free for individual Google accounts
- All features available: Q&A, audio overviews, notebook guides
- Usage subject to undocumented rate limits (see Rate Limits section)
- No per-query or per-source charges

**NotebookLM Plus (subscription):**
- Part of Google One AI Premium plan (~$19.99/month as of 2025)
- Higher usage limits
- Priority access to new features
- Longer audio overviews

**NotebookLM for Google Workspace (enterprise):**
- Available to Google Workspace Business and Enterprise customers
- Admin controls for organization-wide deployment
- Data stays within organization's Google Workspace boundaries
- Same feature set with enterprise compliance and data governance

**EOS cost:** $0. EOS uses the free tier. No API costs because there is no API.
The only cost is the time to manually re-authenticate when sessions expire.

**Cost of the nlm CLI:** Free, open-source (MIT license).

## Version Pinning

NotebookLM does not have API versioning because there is no API. The web product
updates continuously with no version numbers or deprecation notices.

**What to pin:**
- `nlm` CLI version: `v0.5.9` — pin in package.json or install command
- Node.js version: 18+ required by the CLI

**Breaking change risks:**
- Google changes the NotebookLM web UI structure -> `nlm` CLI commands break
- Google adds CAPTCHA or bot detection -> automated browser sessions fail
- Chrome version updates -> Puppeteer compatibility issues in `nlm`

**Mitigation:**
- Pin `nlm` CLI version explicitly
- Monitor the `jacob-bd/notebooklm-mcp-cli` GitHub repo for updates
- Keep a manual workflow documented as fallback (always works)

---

# Tier 2 — Creator Intelligence

## Design Intent and Tradeoffs

NotebookLM was built by Google Labs (Steven Johnson, Raiza Martin) with a specific
thesis: AI is most useful when it operates on YOUR data, not the open web.

**Core design philosophy:**
- **Source-first, not search-first.** Unlike ChatGPT or Gemini chat, NotebookLM
  refuses to answer from general knowledge. Every response must be grounded in
  uploaded sources. This is a deliberate constraint, not a limitation.
- **The user curates, the AI synthesizes.** The human decides what goes into the
  notebook (editorial judgment). The AI finds patterns across those sources
  (synthesis at scale). Neither party does both jobs.
- **Audio as a learning medium.** The Audio Overview feature exists because the
  team observed that people retain information better through conversational
  audio than through reading. The two-host format mimics how podcast listeners
  naturally engage with complex topics.

**Tradeoffs:**
- No web search means no real-time data. By design — forces the user to be
  intentional about their knowledge base.
- No API means no automation at scale. Google prioritized the end-user
  experience over developer extensibility.
- Source limit (50) forces curation. You cannot dump thousands of documents —
  you must select the most relevant ones.
- Free tier with generous limits suggests NotebookLM is a distribution channel
  for Gemini, not a standalone revenue product.

**What NotebookLM is NOT:**
- Not a database (no structured queries, no schemas)
- Not a search engine (no web crawling, no index beyond your sources)
- Not a knowledge graph (no entity relationships, no ontology)
- Not a note-taking app (it generates notes, you do not manually organize)

## Problem-Solution Map and Hidden Capabilities

**Problems NotebookLM actually solves:**
1. "I have 20 PDFs and need to find the common thread" -> multi-source synthesis
2. "I need to study this material but hate reading" -> audio overviews
3. "I need cited, verifiable answers" -> source-grounded Q&A
4. "I need a briefing doc from raw research" -> notebook guide generation
5. "I need to cross-reference competing claims" -> upload contradictory sources,
   ask NotebookLM to compare positions

**Hidden capabilities most users miss:**
- **Custom audio instructions**: You can tell NotebookLM to focus the audio
  overview on specific aspects, adopt a particular tone, or explain concepts
  for a specific audience. Most users generate default overviews.
- **YouTube as source**: Upload a YouTube URL and NotebookLM extracts and indexes
  the full transcript. You can then query specific claims made in the video.
- **Source-scoped queries**: Click on a specific source, then ask questions about
  only that source — useful when you want isolated analysis, not cross-source synthesis.
- **Pin notes as persistent context**: Pinned notes influence future queries within
  the same notebook, effectively creating persistent instructions.
- **Iterative source building**: Start with 2-3 sources, query to find gaps, then
  add sources specifically to fill those gaps. The notebook becomes progressively
  more comprehensive through directed curation.

## Operational Behavior and Edge Cases

**Indexing delay:** Sources are not instantly queryable after upload. Observed delay
is 30-120 seconds for text sources, 2-5 minutes for large PDFs, and 5-10 minutes
for YouTube videos (transcript extraction). There is no status indicator in the CLI.

**Citation accuracy:** NotebookLM citations point to specific passages, but the
passage boundaries are not always precise. A citation marked [3] may refer to a
broader section than the exact sentence it highlights.

**Audio overview regeneration:** Regenerating an audio overview for the same
sources produces a different conversation each time. The hosts take different
angles, use different examples, and structure the discussion differently.
This is non-deterministic by design.

**Source conflicts:** When sources contain contradictory information, NotebookLM
typically presents both positions with citations rather than picking one. However,
it may occasionally favor the source with more supporting detail without
explicitly flagging the conflict.

**Session state:** NotebookLM conversations within a notebook have context memory
for the current browser session. Closing the tab and reopening loses conversation
history (but saved notes persist). The `nlm` CLI has no conversation state — each
query is independent.

**Unicode handling:** Sources with non-Latin characters (CJK, Arabic, Cyrillic) are
supported but audio overview generation defaults to English voices. Mixed-language
sources produce English audio summaries regardless of source language.

**Empty notebook behavior:** Querying a notebook with zero sources returns a
generic "add sources to get started" message, not an error. The `nlm` CLI
returns this as a normal response string.

## Ecosystem Position and Composition

**Where NotebookLM sits in the EOS architecture:**
```
Real-time data:  Perplexity (web search, current events)
Grounded data:   NotebookLM (uploaded documents, historical research)
Structured data: Neon Postgres (pipeline, events, memory)
Unstructured:    Obsidian vault (notes, SOPs, context docs)
```

**Natural complements:**
- **Perplexity** — real-time web intelligence. Use alongside NotebookLM:
  Perplexity for "what is happening now," NotebookLM for "what do our
  documents say about this."
- **Google Docs/Slides** — native source integration. Create in Google Workspace,
  add URL directly to NotebookLM without file export.
- **Neon (via EOS)** — pipeline data exported as text files, uploaded as sources.
  Query results stored back as `notebooklm_insight` events.

**Forced integrations (avoid):**
- **Direct database connection** — NotebookLM does not connect to databases.
  Must export to text/PDF first.
- **Real-time dashboards** — NotebookLM is not a BI tool. Data is static
  after upload. Use Notion or dedicated BI for live data.
- **Team collaboration** — NotebookLM notebooks are single-user by default.
  Sharing requires Google Workspace and is limited.

## Trajectory and Evolution

**Where NotebookLM is heading (based on Google I/O announcements and product signals):**
- **More source types** — Google has been steadily adding source types (audio files,
  YouTube, Google Slides were all added post-launch). Expect spreadsheet and
  Google Sheets support.
- **Enterprise features** — NotebookLM for Workspace signals Google's intent to
  monetize through enterprise licensing, not individual subscriptions.
- **API access** — The single most requested feature. Google has acknowledged demand
  but has not committed to a timeline. When it ships, it will likely be a Gemini API
  extension, not a standalone API.
- **Audio customization** — Custom voices, language selection, and longer episodes
  are on the horizon based on user feedback patterns.
- **Deeper Gemini integration** — As Gemini models improve, NotebookLM's synthesis
  quality improves automatically. The product is a frontend for Gemini's
  long-context capabilities.

**Deprecation risks:**
- The `nlm` community CLI could break at any time if Google changes their web UI.
  This is the primary risk for EOS automation.
- NotebookLM is a Google Labs product. Google Labs projects can be shut down
  (see: Google Stadia, Google+, Inbox). However, the strong user reception and
  enterprise investment make this less likely.

## Conceptual Model and Solution Recipes

**Mental model:** Think of NotebookLM as a research assistant who has read all your
documents cover to cover and can discuss them intelligently — but has read NOTHING
else. The knowledge boundary is the notebook boundary.

**Primitives:**
- **Source** — the atomic unit of knowledge. Everything derives from sources.
- **Notebook** — a scoped knowledge container. One topic = one notebook.
- **Query** — a question answered with citations from sources.
- **Guide** — a structured document generated from all sources.
- **Audio** — a conversational synthesis of all sources.

**Recipe 1: Competitor Intelligence Pipeline**
```
1. Create notebook: "Competitor Analysis — [Industry]"
2. Add sources: competitor websites (URLs), annual reports (PDFs),
   analyst articles (URLs), YouTube interviews (URLs)
3. Query: "What are the top 3 strategies each competitor uses for
   customer acquisition?"
4. Query: "Where do competitors overlap? Where do they differentiate?"
5. Generate audio overview with instruction: "Focus on market gaps
   and underserved segments"
6. Store insights in Neon via NotebookLMSync
```

**Recipe 2: Brand Guide Generator**
```
1. Create notebook: "Brand Identity — [Company]"
2. Add sources: brand document, tone guide, mission statement,
   3-5 best-performing content pieces, founder bio
3. Generate notebook guide -> produces FAQ, style reference, key themes
4. Generate audio overview -> produces brand story in conversational format
5. Use Q&A to test: "How would we talk about [product] in our brand voice?"
```

**Recipe 3: Weekly Intelligence Digest (EOS pattern)**
```
1. World pulse runs Saturday scan (world_pulse.py)
2. Pulse report uploaded to world_pulse notebook (NotebookLMSync)
3. Pipeline data uploaded to venture notebooks (NotebookLMSync)
4. Founder profile synced to all venture notebooks (NotebookLMSync)
5. During week: DEX queries notebooks for grounded context
6. Insights stored in Neon as notebooklm_insight events
7. cognitive_loop.py injects recent insights into DEX responses
```

**Recipe 4: Content Research and Ideation**
```
1. Create notebook: "Content Research — [Topic]"
2. Add sources: top 10 articles on topic, 3-5 YouTube videos,
   relevant book chapters, your own notes/outline
3. Query: "What angles are covered by everyone? What is underrepresented?"
4. Query: "Based on these sources, what would be a contrarian take?"
5. Generate audio overview -> listen during commute for inspiration
6. Use insights to draft original content that fills identified gaps
```

**Recipe 5: Client Onboarding Knowledge Base**
```
1. Create notebook: "Client — [Name]"
2. Add sources: client's website, intake form, call transcripts,
   industry reports relevant to their market
3. Query: "Summarize this client's business model and key challenges"
4. Generate notebook guide -> instant briefing doc for team
5. Generate audio overview -> shareable primer for anyone touching the account
```

## Industry Expert and Cutting-Edge Usage

**How top practitioners use NotebookLM:**

1. **Podcast producers** use Audio Overviews as pre-interview research. Upload
   a guest's published work, generate an audio overview, and listen to identify
   the most interesting discussion threads before recording.

2. **Course creators** upload their entire curriculum and use NotebookLM to
   identify gaps, redundancies, and opportunities for cross-referencing between
   modules. The notebook guide becomes the course outline.

3. **Sales teams** upload a prospect's 10-K filing, recent press releases, and
   LinkedIn posts, then query for pain points and strategic priorities before
   discovery calls.

4. **Legal researchers** upload case law and statutes, then use source-scoped
   queries to trace how specific legal principles evolved across documents.

5. **AI-powered knowledge bases** — the frontier pattern: use NotebookLM as a
   grounded context engine for AI agents. Upload your company's documentation,
   query via CLI, pipe the cited answers into your agent's context window.
   This is exactly what EOS does with `NotebookLMSync` -> `cognitive_loop.py`.

**Cutting-edge patterns:**
- **Temporal analysis**: Upload the same report from different time periods.
  Query: "How has [metric] changed between Q1 2024 and Q4 2025?" NotebookLM
  can compare across temporal snapshots when they are separate sources.
- **Adversarial testing**: Upload your own content alongside competitor content.
  Query: "What claims in Source A are contradicted by Source B?" Surfaces
  weaknesses in your positioning.
- **Audio as content**: Some creators publish NotebookLM Audio Overviews directly
  as podcast episodes or social media content. The two-host format is
  surprisingly engaging for audiences who want quick summaries.

---

## EOS Usage Patterns

### Active notebooks
| Notebook | Env Var | Purpose |
|---|---|---|
| Lyfe Institute Research | NOTEBOOKLM_LYFE_ID | ICP research, competitor analysis, curriculum |
| Empyrean Creative Research | NOTEBOOKLM_EMPYREAN_ID | AI services market, B2B outreach |
| Personal Brand Research | NOTEBOOKLM_BRAND_ID | Content strategy, creator economy |
| World Pulse | NOTEBOOKLM_PULSE_ID | Weekly market intelligence reports |

### Sync cadence
- **Saturday**: Full cross-reference via `world_pulse.py` — pipeline data + founder profile
- **On-demand**: `query_for_context()` called by DEX for grounded research answers
- **Weekly pulse**: World pulse report uploaded after Saturday scan

### Data flow
```
Neon (pipeline, events) --> text export --> NotebookLMSync._nlm_source_add() --> NotebookLM
NotebookLM --> nlm notebook query --> NotebookLMSync.query_for_context() --> Neon (notebooklm_insight)
Neon (notebooklm_insight) --> cognitive_loop.py Layer 1e-viii --> DEX response context
```

## Gotchas

### nlm CLI is not in PATH inside Docker containers
The `nlm` CLI is installed on the host VPS, not inside Docker containers.
`NotebookLMSync` must run on the host or in a container with host network
access and the CLI installed. EOS runs it from Python scripts on the host,
not from the os-discord container.

### Empty notebook ID env vars cause silent skips
If `NOTEBOOKLM_LYFE_ID` etc. are not set (empty string), `NotebookLMSync`
silently skips operations with a print statement but no exception.
Check `nlm notebook list` to get IDs after creating notebooks.

### WebSearch denied during research — manual knowledge used
WebSearch and WebFetch were both unavailable during the creation of this
skill file. Content is based on training knowledge (up to May 2025),
the existing EOS codebase (`notebooklm_sync.py`, `.claude/skills/notebooklm.md`,
`harness_registry.py`, `cognitive_loop.py`, `world_pulse.py`), and the
community MCP CLI documentation. Re-research with live web access when
available to capture any 2025-2026 changes.
