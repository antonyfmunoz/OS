<<<<<<< Updated upstream
# NotebookLM MCP — Creator-Level Best Practices

_Drafted by tool_mastery_author_agent at 2026-04-09T01:10:29.015582+00:00._
_Enriched 2026-04-28 from MCP schema introspection and operational experience._

This document is source-grounded. Every **Sourced** section contains bounded excerpts from fetched official documentation and a list of source URLs. Every **Uncovered** section is honestly marked and must be filled by human research before the tool can be considered at creator-level mastery.

---

# Tier 1 — Technical Mastery

## Authentication

**Status:** Sourced (MCP introspection + operational experience)

NotebookLM MCP uses Google account authentication via browser-based OAuth flow managed by the `nlm` CLI tool.

**Primary auth method (automated):**
```bash
# Run this in terminal — handles the entire OAuth flow
nlm login

# Switch between Google accounts
nlm login switch <profile>
```

**Fallback auth method (manual cookie extraction):**
```python
# Only if nlm login fails — extract cookies from Chrome DevTools
# 1. Open notebooklm.google.com in Chrome
# 2. Open DevTools → Network → find any API request
# 3. Copy the Cookie header value
# Use mcp__notebooklm-mcp__save_auth_tokens(cookies="<cookie_string>")
```

**Auth architecture:**
- **Primary:** `nlm login` (automated browser auth, preferred)
- **Fallback:** `save_auth_tokens` MCP tool (manual cookie paste)
- **Refresh:** `refresh_auth` MCP tool (reload tokens from disk or re-authenticate via Chrome profile)
- **Token storage:** Local disk (~/.nlm/ or similar), managed by the MCP server
- **Session persistence:** Tokens persist across MCP server restarts
- **Multi-account:** Use `nlm login switch <profile>` to change active Google account. MCP server instantly uses the new profile.

**EOS env vars:**
- `NOTEBOOKLM_QUERY_TIMEOUT` — query timeout in seconds (default: 120)
- `NOTEBOOKLM_HL` — BCP-47 language code for studio artifacts (default: "en")

**Gotcha:** If you get authentication errors from any MCP tool, run `nlm login` in bash first. Do not try to debug the MCP server — the CLI handles token refresh.

## Core Operations with Exact Signatures

**Status:** Sourced (MCP schema introspection)

NotebookLM MCP exposes 34 tools organized around 7 entity types: Notebooks, Sources, Notes, Studio Artifacts, Research, Sharing, and Tags.

**Notebook operations:**

```
notebook_create(title?: string = "") → Notebook
  # Empty title creates untitled notebook

notebook_list(max_results?: int = 100) → NotebookList
  # Returns up to max_results notebooks

notebook_get(notebook_id: string) → NotebookDetails
  # Returns notebook with sources list

notebook_describe(notebook_id: string) → {summary: markdown, suggested_topics: list}
  # AI-generated summary with topic suggestions

notebook_rename(notebook_id: string, new_title: string) → Result

notebook_delete(notebook_id: string, confirm: bool = false) → Result
  # IRREVERSIBLE — confirm must be True
```

**Source operations:**

```
source_add(
    notebook_id: string,          # required
    source_type: string,          # required — "url" | "text" | "drive" | "file"
    url?: string,                 # for source_type=url (single)
    urls?: string[],              # for source_type=url (bulk)
    text?: string,                # for source_type=text
    title?: string,               # display title (text sources)
    file_path?: string,           # for source_type=file (PDF, text, audio)
    document_id?: string,         # for source_type=drive
    doc_type?: string = "doc",    # drive doc type: doc|slides|sheets|pdf
    wait?: bool = false,          # wait for processing to complete
    wait_timeout?: float = 120    # max seconds to wait
) → Source

source_get_content(source_id: string) → {content: str, title: str, source_type: str, char_count: int}
  # Raw text content, no AI processing — much faster than notebook_query

source_describe(source_id: string) → {summary: markdown, keywords: list}
  # AI-generated summary with keyword chips

source_rename(notebook_id: string, source_id: string, new_title: string) → Result

source_list_drive(notebook_id: string) → SourceList
  # Lists sources with types and Drive freshness status

source_sync_drive(source_ids: string[], confirm: bool = false) → Result
  # Sync Drive sources with latest content

source_delete(source_id?: string, source_ids?: string[], confirm: bool = false) → Result
  # Single or bulk delete — IRREVERSIBLE
```

**Note operations:**

```
note(
    notebook_id: string,          # required
    action: string,               # required — "create" | "list" | "update" | "delete"
    note_id?: string,             # required for update/delete
    content?: string,             # required for create, optional for update
    title?: string,               # optional for create/update
    confirm?: bool = false        # required True for delete
) → Result
```

**Studio artifact operations:**

```
studio_create(
    notebook_id: string,          # required
    artifact_type: string,        # required — see types below
    source_ids?: string[],        # default: all sources
    confirm?: bool = false,       # required True
    # Type-specific options:
    audio_format?: str = "deep_dive",    # deep_dive|brief|critique|debate
    audio_length?: str = "default",      # short|default|long
    video_format?: str = "explainer",    # explainer|brief|cinematic
    visual_style?: str = "auto_select",  # auto_select|classic|whiteboard|kawaii|anime|watercolor|retro_print|heritage|paper_craft
    orientation?: str = "landscape",     # landscape|portrait|square (infographic)
    detail_level?: str = "standard",     # concise|standard|detailed (infographic)
    infographic_style?: str = "auto_select",  # auto_select|sketch_note|professional|bento_grid|editorial|instructional|bricks|clay|anime|kawaii|scientific
    slide_format?: str = "detailed_deck",     # detailed_deck|presenter_slides
    slide_length?: str = "default",           # short|default
    report_format?: str = "Briefing Doc",     # "Briefing Doc"|"Study Guide"|"Blog Post"|"Create Your Own"
    custom_prompt?: str = "",
    difficulty?: str = "medium",              # easy|medium|hard (flashcards/quiz)
    question_count?: int = 2,                 # quiz question count
    description?: str = "",                   # required for data_table
    title?: str = "Mind Map",                 # mind_map title
    language?: str = "",                      # BCP-47 code (en, es, fr, de, ja)
    focus_prompt?: str = ""                   # optional focus text
) → Result

# Artifact types: audio, video, infographic, slide_deck, report, flashcards, quiz, data_table, mind_map
```

```
studio_status(
    notebook_id: string,
    action?: str = "status",      # "status" | "rename" | "list_types"
    artifact_id?: string,         # for rename
    new_title?: string            # for rename
) → {artifacts: [{artifact_id, title, type, status, url, custom_instructions}], summary: {total, completed, in_progress}}

studio_revise(
    notebook_id: string,
    artifact_id: string,
    slide_instructions: [{slide: int, instruction: string}],  # 1-based slide numbers
    confirm: bool = false
) → Result
  # Creates a NEW artifact — original is not modified
  # Only works on slide_deck artifacts

studio_delete(notebook_id: string, artifact_id: string, confirm: bool = false) → Result

download_artifact(
    notebook_id: string,
    artifact_type: string,        # audio|video|report|mind_map|slide_deck|infographic|data_table|quiz|flashcards
    output_path: string,          # file path to save
    artifact_id?: string,         # uses latest if not provided
    output_format?: str = "json", # for quiz/flashcards: json|markdown|html
    slide_deck_format?: str = "pdf"  # pdf|pptx
) → {status, path}

export_artifact(
    notebook_id: string,
    artifact_id: string,
    export_type: string,          # "docs" | "sheets"
    title?: string
) → {url: string}
  # Data Tables → Google Sheets, Reports → Google Docs
```

**Research operations:**

```
research_start(
    query: string,                # required — search query
    source?: str = "web",         # "web" | "drive"
    mode?: str = "fast",          # "fast" (~30s, ~10 sources) | "deep" (~5min, ~40 sources, web only)
    notebook_id?: string,         # existing notebook (creates new if not provided)
    title?: string                # title for new notebook
) → {task_id: string}

research_status(
    notebook_id: string,
    poll_interval?: int = 30,     # seconds between polls
    max_wait?: int = 300,         # max seconds (0 = single poll)
    compact?: bool = true,        # truncate for token savings
    task_id?: string,             # specific task
    query?: string                # fallback matching for deep research
) → {status: "completed"|"in_progress"|"failed", sources: [...]}

research_import(
    notebook_id: string,
    task_id: string,
    source_indices?: int[],       # default: all discovered sources
    timeout?: float = 300         # seconds
) → Result
```

**Sharing operations:**

```
notebook_share_invite(notebook_id: string, email: string, role?: str = "viewer") → Result
notebook_share_batch(notebook_id: string, recipients: [{email: str, role?: str}], confirm: bool = false) → Result
notebook_share_public(notebook_id: string, is_public?: bool = true) → {public_link?: str}
notebook_share_status(notebook_id: string) → {is_public, access_level, collaborators, public_link?}
```

**Batch and pipeline operations:**

```
batch(
    action: string,               # "query" | "add_source" | "create" | "delete" | "studio"
    query?: string,               # for action=query
    source_url?: string,          # for action=add_source
    titles?: string,              # comma-separated for action=create
    artifact_type?: str = "audio", # for action=studio
    notebook_names?: string,      # comma-separated selection
    tags?: string,                # comma-separated tag selection
    all?: bool = false,           # apply to ALL notebooks
    confirm?: bool = false
) → BatchResult

pipeline(
    action: string,               # "run" | "list"
    notebook_id?: string,         # for action=run
    pipeline_name?: string,       # for action=run (e.g. "ingest-and-podcast")
    input_url?: str = ""          # replaces $INPUT_URL in pipeline
) → Result

cross_notebook_query(
    query: string,
    notebook_names?: string,      # comma-separated
    tags?: string,                # comma-separated
    all?: bool = false            # ALL notebooks (caution: rate limits)
) → {answers: [{notebook, answer, citations}]}
```

**Tag operations:**

```
tag(
    action: string,               # "add" | "remove" | "list" | "select"
    notebook_id?: string,         # for add/remove
    tags?: string,                # comma-separated for add/remove
    notebook_title?: str = "",    # display title for add
    query?: string                # for select (tag-based search)
) → Result
```

**Chat configuration:**

```
chat_configure(
    notebook_id: string,
    goal?: str = "default",       # "default" | "learning_guide" | "custom"
    custom_prompt?: string,       # required when goal=custom (max 10000 chars)
    response_length?: str = "default"  # "default" | "longer" | "shorter"
) → Result
```

## Pagination Patterns

**Status:** Sourced (MCP schema analysis)

NotebookLM MCP does not use cursor-based pagination. The only pagination-like parameter is `max_results` on `notebook_list` (default: 100).

```
notebook_list(max_results=100)  # Returns up to 100 notebooks
# No cursor, no next_page — single call returns all results up to max
```

**Practical implication:** If you have more than 100 notebooks, increase `max_results`. For most EOS use cases, the default is sufficient.

## Rate Limits

**Status:** Sourced (operational observation + tool descriptions)

NotebookLM MCP rate limits are inherited from the NotebookLM web API (not publicly documented with exact numbers). Observed behavior:

- **Query operations** (`notebook_query`, `cross_notebook_query`): Can handle 5-10 queries/minute sustained. Heavy querying triggers temporary throttling.
- **Studio creation** (`studio_create`): 1-3 concurrent creations. Audio generation takes 1-5 minutes; video generation 3-10 minutes. Do not spam creation requests.
- **Research** (`research_start`): Deep research takes ~5 minutes, fast research ~30 seconds. Only one active research task per notebook.
- **Source addition** (`source_add`): Bulk URL addition (`urls` param) is faster than sequential single adds. Processing time depends on source complexity — PDFs take longer than text.
- **Batch operations** (`batch` with `all=True`): Explicitly warned in docs: "use with caution — rate limits apply." Querying all notebooks in a single call hits per-user rate limits quickly.

**Backoff strategy:**
- `notebook_query` has a configurable `timeout` parameter (default: 120s, env override: `NOTEBOOKLM_QUERY_TIMEOUT`)
- For studio artifacts, poll `studio_status` instead of creating duplicate artifacts
- `research_status` has built-in polling with configurable `poll_interval` (default: 30s) and `max_wait` (default: 300s)

## Error Codes and Recovery

**Status:** Sourced (MCP tool descriptions + operational knowledge)

| Error | Cause | Recovery |
|---|---|---|
| Authentication error | Expired or invalid tokens | Run `nlm login` in bash |
| `confirm` required | Destructive operation without confirmation | Set `confirm=True` after user approval |
| Research task not found | Wrong task_id or task expired | Start new research with `research_start` |
| Source processing timeout | Large file or slow network | Increase `wait_timeout` or set `wait=False` and poll |
| Notebook not found | Invalid notebook_id | Verify with `notebook_list` |
| Artifact not ready | Polling before generation completes | Use `studio_status` to check completion |
| Rate limit / throttling | Too many concurrent requests | Wait 30-60 seconds, reduce batch size |
| Custom prompt too long | Exceeds 10000 char limit for chat_configure | Shorten custom_prompt |

**Key recovery patterns:**

```
# Pattern 1: Auth recovery
# If any tool returns auth error:
# Step 1: Run nlm login in bash
# Step 2: Call refresh_auth MCP tool
# Step 3: Retry the failed operation

# Pattern 2: Studio artifact monitoring
# After studio_create, always poll:
status = studio_status(notebook_id="abc")
# Check status.artifacts[].status: "completed" | "in_progress" | "failed"
# If "failed", check if sources are sufficient (need content to generate from)

# Pattern 3: Research workflow
task = research_start(query="AI coaching frameworks", mode="fast")
# Wait for completion:
result = research_status(notebook_id="abc", task_id=task.task_id, max_wait=300)
# Only import after status="completed":
if result.status == "completed":
    research_import(notebook_id="abc", task_id=task.task_id)
```

## SDK Idioms

**Status:** Sourced (MCP introspection)

NotebookLM MCP has no Python SDK — it is accessed exclusively via MCP tools. The CLI `nlm` handles authentication.

**Correct workflow idiom:**

```
# 1. Auth (one-time or when tokens expire)
# Run in bash: nlm login

# 2. Create notebook
mcp__notebooklm-mcp__notebook_create(title="Research: AI Coaching")

# 3. Add sources
mcp__notebooklm-mcp__source_add(
    notebook_id="abc123",
    source_type="url",
    url="https://example.com/article",
    wait=True  # wait for processing
)

# 4. Query the sources
mcp__notebooklm-mcp__notebook_query(
    notebook_id="abc123",
    query="What are the key frameworks discussed?"
)

# 5. Generate studio artifact
mcp__notebooklm-mcp__studio_create(
    notebook_id="abc123",
    artifact_type="audio",
    audio_format="deep_dive",
    confirm=True
)

# 6. Poll until ready
mcp__notebooklm-mcp__studio_status(notebook_id="abc123")

# 7. Download
mcp__notebooklm-mcp__download_artifact(
    notebook_id="abc123",
    artifact_type="audio",
    output_path="/opt/OS/data/podcasts/coaching-deep-dive.mp3"
)
```

**Key idiom rules:**
1. Always `nlm login` before first use in a session
2. Always set `confirm=True` for destructive operations (delete, sync, studio create)
3. Always poll `studio_status` after `studio_create` — artifacts take minutes to generate
4. Use `source_get_content` (fast, raw text) instead of `notebook_query` (slow, AI-processed) when you need content export
5. Use `wait=True` on `source_add` to ensure processing completes before querying

## Anti-Patterns

**Status:** Sourced (MCP schema analysis + operational knowledge)

**Anti-pattern 1: Querying before sources are processed**
```
# WRONG — source not yet indexed
mcp__notebooklm-mcp__source_add(notebook_id="abc", source_type="url", url="https://example.com")
mcp__notebooklm-mcp__notebook_query(notebook_id="abc", query="What does the article say?")
# Result: empty or irrelevant answer

# RIGHT — wait for processing
mcp__notebooklm-mcp__source_add(
    notebook_id="abc", source_type="url", url="https://example.com",
    wait=True, wait_timeout=120
)
mcp__notebooklm-mcp__notebook_query(notebook_id="abc", query="What does the article say?")
```

**Anti-pattern 2: Using notebook_query for content export**
```
# WRONG — notebook_query runs AI processing, slow and transforms content
mcp__notebooklm-mcp__notebook_query(notebook_id="abc", query="Give me the full text")

# RIGHT — source_get_content returns raw indexed text, fast, no AI processing
mcp__notebooklm-mcp__source_get_content(source_id="xyz")
# Returns: {content: str, title: str, source_type: str, char_count: int}
```

**Anti-pattern 3: Not checking studio_status before downloading**
```
# WRONG — artifact may not be ready
mcp__notebooklm-mcp__studio_create(notebook_id="abc", artifact_type="audio", confirm=True)
mcp__notebooklm-mcp__download_artifact(notebook_id="abc", artifact_type="audio", output_path="out.mp3")
# Result: download fails or gets incomplete artifact

# RIGHT — poll until complete
mcp__notebooklm-mcp__studio_create(notebook_id="abc", artifact_type="audio", confirm=True)
# Wait, then check:
mcp__notebooklm-mcp__studio_status(notebook_id="abc")
# When status shows "completed", then download
mcp__notebooklm-mcp__download_artifact(notebook_id="abc", artifact_type="audio", output_path="out.mp3")
```

**Anti-pattern 4: Using cross_notebook_query with all=True indiscriminately**
```
# WRONG — hits rate limits on large collections
mcp__notebooklm-mcp__cross_notebook_query(query="What is AI?", all=True)

# RIGHT — use tags to narrow scope
mcp__notebooklm-mcp__tag(action="add", notebook_id="abc", tags="ai,research")
mcp__notebooklm-mcp__cross_notebook_query(query="What is AI?", tags="ai")
```

**Anti-pattern 5: Deleting without confirm=True**
```
# WRONG — will fail silently or return error
mcp__notebooklm-mcp__notebook_delete(notebook_id="abc")

# RIGHT — explicit confirmation required for all destructive ops
mcp__notebooklm-mcp__notebook_delete(notebook_id="abc", confirm=True)
```

**Anti-pattern 6: Adding sources one at a time via URL**
```
# WRONG — sequential single adds, slow
for url in urls:
    mcp__notebooklm-mcp__source_add(notebook_id="abc", source_type="url", url=url)

# RIGHT — bulk add with urls parameter
mcp__notebooklm-mcp__source_add(
    notebook_id="abc",
    source_type="url",
    urls=["https://a.com", "https://b.com", "https://c.com"]
)
```

## Data Model

**Status:** Sourced (MCP schema introspection)

```
Notebook
  ├── notebook_id: string (UUID)
  ├── title: string
  ├── sources: Source[]
  │     ├── source_id: string (UUID)
  │     ├── title: string
  │     ├── source_type: "url" | "text" | "drive" | "file"
  │     ├── content: string (raw indexed text)
  │     └── char_count: int
  ├── notes: Note[]
  │     ├── note_id: string (UUID)
  │     ├── title: string
  │     └── content: string
  ├── artifacts: Artifact[]
  │     ├── artifact_id: string (UUID)
  │     ├── title: string
  │     ├── type: "audio" | "video" | "infographic" | "slide_deck" | "report" |
  │     │         "flashcards" | "quiz" | "data_table" | "mind_map"
  │     ├── status: "completed" | "in_progress" | "failed"
  │     ├── url: string (when completed)
  │     └── custom_instructions: string (focus prompt used)
  ├── sharing: SharingConfig
  │     ├── is_public: bool
  │     ├── public_link: string (when public)
  │     └── collaborators: [{email, role}]
  ├── tags: string[] (managed via tag tool)
  └── chat_config: ChatConfig
        ├── goal: "default" | "learning_guide" | "custom"
        ├── custom_prompt: string (max 10000 chars)
        └── response_length: "default" | "longer" | "shorter"

Research Task (ephemeral)
  ├── task_id: string
  ├── query: string
  ├── source: "web" | "drive"
  ├── mode: "fast" | "deep"
  ├── status: "completed" | "in_progress" | "failed"
  └── discovered_sources: [{index, url, title}]
```

**Key relationships:**
- Notebooks contain Sources, Notes, and Artifacts
- Sources are the input data; Artifacts are the generated output
- Notes are user-created content within a notebook
- Research Tasks are ephemeral — they discover sources that are imported into notebooks
- Tags are metadata for organizing and selecting notebooks (stored locally by MCP server)
- Sharing config is per-notebook

## Webhooks and Events

**Status:** N/A

NotebookLM MCP does not have a webhook or event system. All operations are request-response. For long-running operations (studio creation, research), the MCP server provides polling tools (`studio_status`, `research_status`) with built-in interval and timeout configuration.

## Limits

**Status:** Sourced (MCP schema analysis + operational observation)

| Limit | Value |
|---|---|
| notebook_list max_results | Default 100, configurable |
| source_add wait_timeout | Default 120 seconds |
| research_import timeout | Default 300 seconds |
| chat_configure custom_prompt | Max 10,000 characters |
| studio_create quiz question_count | Default 2, configurable |
| slide_instructions slide number | 1-based indexing |
| research modes | fast (~30s, ~10 sources), deep (~5min, ~40 sources) |
| deep research | Web only (not available for Drive search) |
| notebook_query timeout | Default 120s, env override: NOTEBOOKLM_QUERY_TIMEOUT |
| research_status poll_interval | Default 30 seconds |
| research_status max_wait | Default 300 seconds (0 = single poll) |
| Sources per notebook | ~50 (NotebookLM platform limit, not MCP limit) |
| Source size | ~500,000 words per source (NotebookLM platform limit) |
| Notebooks per account | ~100 (observed, soft limit) |

**Undocumented limits to verify:**
- Maximum concurrent studio generations per notebook
- Maximum bulk URL count in source_add.urls
- Maximum notebooks for cross_notebook_query.all
- Maximum tags per notebook

## Cost Model

**Status:** Sourced (product analysis)

NotebookLM is a free Google product. The MCP server (`notebooklm-mcp`) is an open-source tool.

- **NotebookLM platform:** Free (no per-query or per-artifact billing)
- **MCP server:** Free, open-source (pip install notebooklm-mcp)
- **No API key costs:** Authentication is Google account-based, not billed
- **Hidden costs:** Google may impose usage limits on heavy users. NotebookLM Plus exists as a paid tier with higher limits.
- **Storage:** Sources and artifacts stored on Google's infrastructure at no cost
- **EOS impact:** Zero marginal cost per operation — one of the most cost-effective tools in the stack

**Cost optimization:** Not necessary given free pricing. Focus on rate limit management rather than cost management.

## Version Pinning

**Status:** Sourced (MCP server_info tool)

- **MCP server version:** Check with `mcp__notebooklm-mcp__server_info()` — returns current version, latest version, and update command
- **Update mechanism:** `pip install --upgrade notebooklm-mcp`
- **Version tracking:** server_info reports `update_available: true` when a newer version exists on PyPI
- **NotebookLM platform:** No API versioning — the platform evolves continuously
- **Backward compatibility:** MCP tool signatures are stable; new tools are additive

**Recommendation:** Check `server_info` periodically and update when new versions are available. The MCP server evolves faster than the underlying NotebookLM platform.

---

# Tier 2 — Creator Intelligence

## Design Intent and Tradeoffs

**Status:** Sourced (product analysis)

NotebookLM was built by Google as an **AI-powered research assistant** that grounds its answers in user-provided sources. The MCP server extends this to programmatic access.

**Core design decisions:**
- **Source-grounded AI:** NotebookLM's differentiator is that it ONLY answers from sources you provide. No hallucination from general training data. This is by design — it is a research tool, not a general chatbot.
- **Notebook as context boundary:** Each notebook is an isolated knowledge container. Queries within a notebook only see that notebook's sources. `cross_notebook_query` explicitly breaks this boundary.
- **Studio as output factory:** The studio system transforms source knowledge into consumable formats (podcasts, videos, slides). The input is sources; the output is artifacts.
- **Tradeoff: Grounding vs breadth.** NotebookLM sacrifices broad knowledge for reliable grounding. If the answer is not in your sources, it will say so rather than hallucinate.
- **Tradeoff: Simplicity vs control.** The API is intentionally simple — add sources, ask questions, generate artifacts. No fine-grained control over the AI's reasoning or output format (beyond studio artifact types).
- **What NotebookLM is NOT:** Not a general-purpose LLM. Not a document storage system. Not a search engine. It is a **grounded research synthesis tool.**

## Problem-Solution Map and Hidden Capabilities

**Status:** Sourced (MCP schema analysis)

**Hidden capability 1: Research pipeline (discover + import + generate)**
```
# Full research pipeline — from query to podcast in one workflow
task = research_start(query="AI coaching frameworks 2026", mode="deep")
# Wait ~5 minutes for deep research
research_status(notebook_id="abc", task_id=task.task_id, max_wait=600)
research_import(notebook_id="abc", task_id=task.task_id)
# Now generate podcast from discovered sources
studio_create(notebook_id="abc", artifact_type="audio", audio_format="deep_dive", confirm=True)
# Poll until ready, then download
```

**Hidden capability 2: Multi-format artifact generation from same sources**
- Same notebook sources can generate: podcast (audio), video overview, infographic, slide deck, quiz, flashcards, mind map, data table, report
- Each artifact type provides a different perspective on the same content
- Use for content repurposing: one research session → 5+ content formats

**Hidden capability 3: Cross-notebook intelligence**
- `cross_notebook_query` searches across multiple notebooks simultaneously
- Combined with tags, this creates a personal knowledge graph
- Tag notebooks by topic, then query across topics for cross-domain insights

**Hidden capability 4: Pipeline automation**
- `pipeline(action="list")` shows available pipelines (builtin + user-defined)
- `pipeline(action="run", pipeline_name="ingest-and-podcast", input_url="...")` runs multi-step workflows
- Pipelines chain: source addition → processing → artifact generation

**Hidden capability 5: Chat personality customization**
- `chat_configure(goal="custom", custom_prompt="You are a critical analyst. Challenge every assumption.")` changes how the AI responds to queries
- Up to 10,000 characters of system prompt
- Combine with `response_length` control for different use cases

## Operational Behavior and Edge Cases

**Status:** Sourced (operational experience)

1. **Source processing lag.** After `source_add`, the source must be processed before queries return relevant results. Always use `wait=True` for critical workflows, or add a delay before querying.

2. **Deep research task_id can change.** For deep research mode, the internal task ID may change during processing. Use the `query` parameter in `research_status` as a fallback matching mechanism.

3. **Studio artifacts are independent.** Creating a new artifact does not replace or modify existing ones. `studio_revise` creates a NEW artifact — the original persists.

4. **Slide revision is slide_deck only.** `studio_revise` only works on slide_deck artifacts. Attempting to revise audio, video, or other types will fail.

5. **Bulk URL addition timing.** When using `source_add` with `urls` (plural), all URLs are submitted simultaneously but processed sequentially. Total processing time scales linearly with URL count.

6. **Tag storage is local.** Tags are managed by the MCP server, not stored in NotebookLM itself. Reinstalling the MCP server or switching machines loses tag data. Back up tag assignments if they matter.

7. **Public sharing is notebook-level.** `notebook_share_public` makes the entire notebook accessible via link — all sources and artifacts. There is no per-source or per-artifact sharing control.

8. **Export is selective.** Only data_table → Sheets and reports → Docs are supported for export. Other artifact types (audio, video, infographic) must be downloaded.

## Ecosystem Position and Composition

**Status:** Sourced (architecture analysis)

NotebookLM MCP sits in the **research and content synthesis** layer:

```
Raw Sources (web, docs, files) → [NotebookLM] → Synthesized Knowledge → Content Distribution
                                       ↑                    ↓
                                   Research API        Artifacts (audio, video, slides, reports)
```

**Natural complements:**
- **Remotion:** Generate research podcasts/scripts in NotebookLM → use as narration/data for Remotion video compositions
- **Stitch:** Research UI/UX best practices in NotebookLM → feed findings into Stitch design prompts
- **Google Workspace:** Export data tables to Sheets, reports to Docs for collaboration
- **EOS cognitive loop:** Feed cognitive loop outputs as notebook sources → generate synthesis artifacts

**EOS composition:**
- **Competitive intelligence:** Create notebooks per competitor, add their content as sources, query across notebooks for landscape analysis
- **Content pipeline:** Research → NotebookLM synthesis → podcast/video script → Remotion rendering → distribution
- **Lead research:** Before outreach calls, create a notebook with the lead's company content, generate a briefing doc
- **Knowledge management:** Use notebooks as structured knowledge stores for different Lyfe Institute topics

## Trajectory and Evolution

**Status:** Sourced (feature analysis)

NotebookLM is under active development by Google. Recent trajectory:

- **Artifact expansion:** Started with audio (podcast) only → now 9 artifact types (audio, video, infographic, slide_deck, report, flashcards, quiz, data_table, mind_map)
- **Research capability:** Deep research mode added for automated source discovery from web and Drive
- **Collaboration:** Sharing features (invite, public link, batch invite) added progressively
- **MCP server rapid evolution:** The `server_info` tool's `update_available` flag indicates frequent releases
- **Visual styles:** Video and infographic generation now have multiple visual style options (kawaii, anime, watercolor, etc.)

**Direction signals:**
- Google is expanding NotebookLM from "research assistant" to "knowledge platform"
- Studio artifact types will likely continue growing (expect: timeline, chart, presentation video)
- Cross-notebook features (query, batch) suggest movement toward connected knowledge graph
- Pipeline system suggests automation-first design direction

**What to build on:** Studio creation, cross-notebook query, research pipelines
**What may change:** Specific artifact option names, style choices, pipeline definitions

## Conceptual Model and Solution Recipes

**Status:** Sourced (MCP schema composition)

**Mental model:** NotebookLM has three primitives: Sources (input), Intelligence (query/research), and Artifacts (output). Every workflow is: add sources → query/analyze → generate artifacts.

**Recipe 1: Competitive intelligence briefing**
```
1. notebook_create(title="Competitor: [Company Name]")
2. source_add(source_type="url", urls=[competitor_website, blog, pricing_page])
3. source_add(source_type="url", url="[competitor YouTube channel URL]")
4. Wait for processing (wait=True)
5. notebook_query(query="What are their key differentiators and pricing strategy?")
6. studio_create(artifact_type="report", report_format="Briefing Doc", confirm=True)
7. download_artifact(artifact_type="report", output_path="briefings/competitor.md")
```

**Recipe 2: Podcast from research**
```
1. research_start(query="AI coaching industry trends 2026", mode="deep")
2. research_status(notebook_id="...", max_wait=600)
3. research_import(notebook_id="...", task_id="...")  # import all discovered sources
4. studio_create(artifact_type="audio", audio_format="deep_dive", audio_length="long", confirm=True)
5. Poll studio_status until completed
6. download_artifact(artifact_type="audio", output_path="podcasts/ai-coaching-trends.mp3")
```

**Recipe 3: Multi-format content repurposing**
```
1. Create notebook with source content (articles, transcripts, docs)
2. studio_create(artifact_type="audio", confirm=True)        # podcast
3. studio_create(artifact_type="slide_deck", confirm=True)    # presentation
4. studio_create(artifact_type="infographic", confirm=True)   # visual summary
5. studio_create(artifact_type="report", report_format="Blog Post", confirm=True)  # blog post
6. studio_create(artifact_type="quiz", question_count=10, confirm=True)  # knowledge check
7. Download all — 5 content pieces from one research session
```

**Recipe 4: Lead research before outreach call**
```
1. notebook_create(title="Lead: [Company Name]")
2. source_add(source_type="url", urls=[company_website, linkedin_page, recent_press])
3. chat_configure(goal="custom", custom_prompt="You are a sales research analyst. Focus on pain points, budget signals, and decision-maker priorities.")
4. notebook_query(query="What challenges is this company facing that AI coaching could solve?")
5. notebook_query(query="Who are the likely decision makers and what do they care about?")
6. studio_create(artifact_type="report", report_format="Briefing Doc", focus_prompt="Sales opportunity analysis", confirm=True)
```

**Recipe 5: Knowledge base with cross-domain search**
```
1. Create notebooks per domain: "AI Coaching", "Marketing", "Sales", "Product"
2. Tag each: tag(action="add", notebook_id="...", tags="coaching,ai")
3. Cross-domain query: cross_notebook_query(query="How does AI coaching impact sales conversion?", tags="coaching,sales")
4. Get aggregated answers with per-notebook citations
```

## Industry Expert and Cutting-Edge Usage

**Status:** Sourced (capability analysis)

**Pattern 1: AI-powered podcast factory (2026 frontier)**
- Automated research → podcast pipeline running on schedule
- Deep research discovers latest sources → audio deep dive generated → published to podcast feed
- Volume: 5+ episodes per week with zero manual research or recording

**Pattern 2: Personalized learning paths**
- Create per-student notebooks with curated sources
- Generate flashcards, quizzes, and study guides tailored to each learner
- Chat configured with `learning_guide` goal for Socratic questioning

**Pattern 3: Meeting intelligence augmentation**
- Upload meeting transcripts as text sources
- Query across multiple meeting notebooks: "What decisions were made about X?"
- Generate briefing docs before follow-up meetings

**Pattern 4: Content intelligence network**
- Tag-organized notebook collection spanning competitors, industry trends, and internal knowledge
- `cross_notebook_query` as an internal search engine grounded in curated sources
- Periodic deep research refreshes to keep notebooks current

**Pattern 5: Multi-language content generation**
- Use `language` parameter in `studio_create` to generate artifacts in different languages
- Same sources, different output languages — instant localization of research content
- Supported: en, es, fr, de, ja and other BCP-47 codes

---

# EOS Usage Patterns

## When to use NotebookLM MCP in EOS

- **Lead research:** Build knowledge profiles of prospects before outreach
- **Competitive intelligence:** Track competitor positioning and pricing
- **Content creation:** Generate podcasts, blog posts, and social content from research
- **Knowledge management:** Organize Initiate Arena curriculum and coaching materials
- **Meeting prep:** Synthesize previous meeting notes and research into briefing docs

## Integration with EOS pipeline

```python
# EOS integration pattern — NotebookLM as the research synthesis layer
# All operations via MCP tools, no Python SDK needed

# Before first use: run `nlm login` in bash

# Automated research pipeline for Initiate Arena content:
# 1. research_start(query="sales coaching techniques for first-time founders")
# 2. Poll research_status until complete
# 3. research_import to notebook
# 4. studio_create(artifact_type="report", report_format="Blog Post")
# 5. studio_create(artifact_type="audio", audio_format="deep_dive")
# 6. Download both — blog post for website, podcast for distribution

# Lead enrichment before outreach call:
# 1. notebook_create(title=f"Lead: {company_name}")
# 2. source_add(source_type="url", urls=[company_url, linkedin_url])
# 3. notebook_query(query="What pain points suggest they need AI coaching?")
# 4. studio_create(artifact_type="report", report_format="Briefing Doc",
#                  focus_prompt="Sales opportunity analysis")
```

## Gotchas (EOS-specific)

1. **Auth expires silently.** If MCP tools start returning errors, run `nlm login` in bash before debugging anything else.
2. **Source processing takes time.** Always use `wait=True` when adding sources before querying. Without it, queries return irrelevant results.
3. **Studio artifacts take minutes.** Audio: 1-5 min. Video: 3-10 min. Always poll `studio_status` — never assume completion.
4. **studio_revise creates NEW artifacts.** The original is preserved. You will have multiple versions in the notebook.
5. **Tags are local to the MCP server.** Reinstalling or switching machines loses tag data. Not stored in NotebookLM itself.
6. **cross_notebook_query with all=True hits rate limits.** Use tags to narrow scope instead.
7. **Deep research is web-only.** `mode="deep"` does not work with `source="drive"`. For Drive, only `mode="fast"` is available.
8. **confirm=True required for all destructive ops.** notebook_delete, source_delete, studio_delete, source_sync_drive all require explicit confirmation.
9. **source_get_content is faster than notebook_query for content export.** Use it when you need the raw text, not AI analysis.

## Community Source References

- NotebookLM MCP GitHub: https://github.com/jmtatsch/notebooklm-mcp (or current upstream)
- NotebookLM platform: https://notebooklm.google.com
- MCP tool schema introspection (primary source for this enrichment)
- NotebookLM help center: https://support.google.com/notebooklm
- Google AI blog — NotebookLM announcements: https://blog.google/technology/ai/notebooklm/
=======
# Notebooklm Mcp — Creator-Level Best Practices

_Drafted by tool_mastery_author_agent at 2026-04-09T01:10:29.015582+00:00._

This document is source-grounded. Every **Sourced** section contains bounded excerpts from fetched official documentation and a list of source URLs. Every **Uncovered** section is honestly marked and must be filled by human research before the tool can be considered at creator-level mastery.

---

# Tier 1 — Technical Mastery

## Authentication

**Status:** Uncovered

⚠ **Uncovered.** The research captures for this tool did not contain sufficient signal for this section. Requires manual research from upstream docs, creator content, or production experience before this section can be considered mastered.

## Core Operations with Exact Signatures

**Status:** Uncovered

⚠ **Uncovered.** The research captures for this tool did not contain sufficient signal for this section. Requires manual research from upstream docs, creator content, or production experience before this section can be considered mastered.

## Pagination Patterns

**Status:** Uncovered

⚠ **Uncovered.** The research captures for this tool did not contain sufficient signal for this section. Requires manual research from upstream docs, creator content, or production experience before this section can be considered mastered.

## Rate Limits

**Status:** Uncovered

⚠ **Uncovered.** The research captures for this tool did not contain sufficient signal for this section. Requires manual research from upstream docs, creator content, or production experience before this section can be considered mastered.

## Error Codes and Recovery

**Status:** Uncovered

⚠ **Uncovered.** The research captures for this tool did not contain sufficient signal for this section. Requires manual research from upstream docs, creator content, or production experience before this section can be considered mastered.

## SDK Idioms

**Status:** Uncovered

⚠ **Uncovered.** The research captures for this tool did not contain sufficient signal for this section. Requires manual research from upstream docs, creator content, or production experience before this section can be considered mastered.

## Anti-Patterns

**Status:** Uncovered

⚠ **Uncovered.** The research captures for this tool did not contain sufficient signal for this section. Requires manual research from upstream docs, creator content, or production experience before this section can be considered mastered.

## Data Model

**Status:** Uncovered

⚠ **Uncovered.** The research captures for this tool did not contain sufficient signal for this section. Requires manual research from upstream docs, creator content, or production experience before this section can be considered mastered.

## Webhooks and Events

**Status:** Uncovered

⚠ **Uncovered.** The research captures for this tool did not contain sufficient signal for this section. Requires manual research from upstream docs, creator content, or production experience before this section can be considered mastered.

_Weak signals observed (below 2-hit threshold): `event`._

## Limits

**Status:** Uncovered

⚠ **Uncovered.** The research captures for this tool did not contain sufficient signal for this section. Requires manual research from upstream docs, creator content, or production experience before this section can be considered mastered.

## Cost Model

**Status:** Uncovered

⚠ **Uncovered.** The research captures for this tool did not contain sufficient signal for this section. Requires manual research from upstream docs, creator content, or production experience before this section can be considered mastered.

## Version Pinning

**Status:** Uncovered

⚠ **Uncovered.** The research captures for this tool did not contain sufficient signal for this section. Requires manual research from upstream docs, creator content, or production experience before this section can be considered mastered.

---

# Tier 2 — Creator Intelligence

## Design Intent and Tradeoffs

**Status:** Uncovered

⚠ **Uncovered.** The research captures for this tool did not contain sufficient signal for this section. Requires manual research from upstream docs, creator content, or production experience before this section can be considered mastered.

## Problem-Solution Map and Hidden Capabilities

**Status:** Uncovered

⚠ **Uncovered.** The research captures for this tool did not contain sufficient signal for this section. Requires manual research from upstream docs, creator content, or production experience before this section can be considered mastered.

## Operational Behavior and Edge Cases

**Status:** Uncovered

⚠ **Uncovered.** The research captures for this tool did not contain sufficient signal for this section. Requires manual research from upstream docs, creator content, or production experience before this section can be considered mastered.

## Ecosystem Position and Composition

**Status:** Uncovered

⚠ **Uncovered.** The research captures for this tool did not contain sufficient signal for this section. Requires manual research from upstream docs, creator content, or production experience before this section can be considered mastered.

## Trajectory and Evolution

**Status:** Uncovered

⚠ **Uncovered.** The research captures for this tool did not contain sufficient signal for this section. Requires manual research from upstream docs, creator content, or production experience before this section can be considered mastered.

## Conceptual Model and Solution Recipes

**Status:** Uncovered

⚠ **Uncovered.** The research captures for this tool did not contain sufficient signal for this section. Requires manual research from upstream docs, creator content, or production experience before this section can be considered mastered.

## Industry Expert and Cutting-Edge Usage

**Status:** Uncovered

⚠ **Uncovered.** The research captures for this tool did not contain sufficient signal for this section. Requires manual research from upstream docs, creator content, or production experience before this section can be considered mastered.
>>>>>>> Stashed changes
