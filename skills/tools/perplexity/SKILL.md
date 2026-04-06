---
name: perplexity
description: "Use when any agent needs real-time web search, grounded answers with citations, market intelligence, competitor monitoring, or current-event fact-checking via the Perplexity Sonar API."
allowed-tools: "Read, Bash"
version: 1.0
source_url: "https://docs.perplexity.ai/api-reference/chat-completions"
last_researched: "2026-04-06"
instantiated_from: templates/tools/_template/
api_version: "2024-01-01"
sdk_version: "openai 1.x (compatible)"
speed_category: medium
trigger: both
effort: medium
context: fork
---

# Tool: Perplexity (Sonar API)

## What This Tool Does

Perplexity provides an OpenAI-compatible chat completions API with built-in
real-time web search. Every response is grounded in live web results and
returns structured citations linking claims to sources.

Core capabilities used by EOS:
- **Web-grounded search** — every response searches the live web before answering,
  returning cited sources. Not a traditional search engine — it synthesizes results
  into coherent answers with inline `[N]` citation references.
- **Market intelligence** — daily world pulse scans for competitor moves,
  market trends, pricing shifts, and industry news across all ventures.
- **AI landscape scanning** — research_engine uses Perplexity to map current
  AI model pricing, capabilities, and releases.
- **Fact-checking** — real-time data grounding prevents hallucination on
  time-sensitive questions (pricing, availability, recent events).
- **Citation extraction** — responses include `citations` array (URLs) and
  optionally `search_results` array (URLs + titles + dates) for source verification.

Available models:
- **sonar** — lightweight, fast web search. Best for quick lookups.
- **sonar-pro** — deeper search, more sources, better synthesis. Default for EOS.
- **sonar-reasoning** — chain-of-thought reasoning with web grounding. Extended thinking.
- **sonar-deep-research** — multi-step autonomous research. Runs multiple searches,
  synthesizes across sources. High latency, high quality.

## EOS Integration

### Model Router registration
`eos_ai/model_router.py` — registered as `perplexity-sonar` in `MODEL_REGISTRY`:
```python
"perplexity-sonar": ModelConfig(
    provider=ModelProvider.PERPLEXITY,
    model_id="llama-3.1-sonar-large-128k-online",
    api_key_env="PERPLEXITY_API_KEY",
    strengths=[TaskType.WEB_SEARCH, TaskType.MARKET_INTEL],
    cost_per_1k=0.001,
    base_url="https://api.perplexity.ai",
)
```
Routed via `_call_openai_compatible()` — same codepath as Groq.
Quality score: `0.60` in `PROVIDER_QUALITY`.

### Model Preferences routing
`eos_ai/model_preferences.py` — auto-selected when `require_realtime=True` or
`task_type` is `market_research`, `competitor_intel`, `realtime_data`, or `fact_check`:
```python
if require_realtime or task_type in (
    'market_research', 'competitor_intel', 'realtime_data', 'fact_check'
):
    if self._key_available('PERPLEXITY_API_KEY'):
        return PROVIDER_CONFIGS['perplexity-sonar']
```

### World Pulse (daily market intel)
`eos_ai/world_pulse.py` — `_scan_with_perplexity()` runs 6 categorized queries
daily at 6am via orchestrator:
- AI services market (Empyrean Creative)
- Men's coaching market (Lyfe Institute)
- Creator economy / algorithm changes (Personal Brand)
- Competitor intelligence (Gadzhi, Hormozi, etc.)
- AI tools and models (weekly landscape)
- AI agency and automation market

Each query calls `router.call_with_fallback(RouterTaskType.MARKET_INTEL, ...)` with
`max_tokens=500`. Results stored as `market_intel` signals in Neon.

### Research Engine (AI landscape)
`eos_ai/research_engine.py` — `scan_ai_landscape()` checks for `PERPLEXITY_API_KEY`
to route AI landscape scans through Perplexity for real-time model pricing data.

### OpenRouter proxy path
`.agents/skills/last30days/scripts/lib/openrouter_search.py` — uses
`perplexity/sonar-pro` via OpenRouter for the last30days research skill.
Returns `search_results` (title, url, date) and `citations` (flat URL list).

### Harness Registry
`eos_ai/harness_registry.py` — registered as `perplexity` harness:
```python
'perplexity': HarnessEntry(
    id='perplexity',
    name='Perplexity Sonar',
    harness_type=HarnessType.MODEL,
    provides=['web_search', 'market_intel'],
    config_key='PERPLEXITY_API_KEY',
)
```

## Authentication

### API key auth
1. Go to https://www.perplexity.ai/settings/api
2. Generate API key (starts with `pplx-`)
3. Store as `PERPLEXITY_API_KEY` in both:
   - `eos_ai/.env` — used by model_router, world_pulse, research_engine
   - `services/.env` — used by discord_bot and service scripts
4. Never commit keys. Never log keys.

### OpenAI-compatible auth
Perplexity uses the same `Authorization: Bearer {key}` header as OpenAI.
The `openai` Python SDK works directly — just change `base_url`:
```python
from openai import OpenAI
client = OpenAI(
    api_key=os.getenv("PERPLEXITY_API_KEY"),
    base_url="https://api.perplexity.ai",
)
```

### Env vars
```
PERPLEXITY_API_KEY=pplx-...   # API key from perplexity.ai/settings/api
```

## Quick Reference

### Basic web search query
```python
from openai import OpenAI
import os

client = OpenAI(
    api_key=os.getenv("PERPLEXITY_API_KEY"),
    base_url="https://api.perplexity.ai",
)

response = client.chat.completions.create(
    model="sonar-pro",
    messages=[
        {"role": "system", "content": "Be precise and cite sources."},
        {"role": "user", "content": "What are the latest AI model releases this week?"},
    ],
    max_tokens=1000,
)

answer = response.choices[0].message.content
# Content includes inline [1], [2] citation markers
```

### Extract citations from response
```python
# Citations are in the response as a list of URLs
# Access via the raw response dict (not the OpenAI SDK object)
import json
raw = json.loads(response.model_dump_json())
citations = raw.get("citations", [])  # ["https://...", "https://..."]

# Some responses also include search_results with richer metadata:
search_results = raw.get("search_results", [])
# [{"title": "...", "url": "...", "date": "...", "snippet": "..."}]
```

### EOS pattern: call via model_router
```python
from eos_ai.model_router import get_router, TaskType

router = get_router()
result = router.call_with_fallback(
    TaskType.MARKET_INTEL,
    prompt="What are AI agencies charging for automation services in 2026?",
    max_tokens=500,
)
# Automatically routes to Perplexity when PERPLEXITY_API_KEY is available
```

### Streaming response
```python
stream = client.chat.completions.create(
    model="sonar-pro",
    messages=[{"role": "user", "content": "Latest AI news"}],
    stream=True,
)
for chunk in stream:
    if chunk.choices[0].delta.content:
        print(chunk.choices[0].delta.content, end="")
# Note: citations only available in the final chunk or non-streamed response
```

### Search with domain filter
```python
response = client.chat.completions.create(
    model="sonar-pro",
    messages=[{"role": "user", "content": "AI automation pricing"}],
    search_domain_filter=["techcrunch.com", "theverge.com"],  # limit to these domains
    search_recency_filter="week",  # "month", "week", "day", "hour"
)
```

### Deep research (multi-step)
```python
response = client.chat.completions.create(
    model="sonar-deep-research",
    messages=[{"role": "user", "content": "Comprehensive analysis of men's coaching market in 2026"}],
    max_tokens=4096,
)
# High latency (30-120s) — runs multiple search iterations internally
```

## Conceptual Model

```
Perplexity Sonar API
  |
  +-- Chat Completions (OpenAI-compatible)
  |     |-- POST https://api.perplexity.ai/chat/completions
  |     |-- Auth: Bearer token (pplx-* key)
  |     |-- Request: messages[], model, max_tokens, temperature, stream
  |     +-- Response: choices[], citations[], search_results[], usage{}
  |
  +-- Models (search-augmented LLMs)
  |     |-- sonar          — fast, lightweight search
  |     |-- sonar-pro      — deeper search, more sources (EOS default)
  |     |-- sonar-reasoning — CoT reasoning + web grounding
  |     +-- sonar-deep-research — multi-step autonomous research
  |
  +-- Search Features
  |     |-- search_domain_filter — restrict to specific domains
  |     |-- search_recency_filter — hour/day/week/month
  |     |-- return_related_questions — suggests follow-ups
  |     +-- return_images — includes image results
  |
  +-- EOS Integration Layer
        |-- model_router.py → _call_openai_compatible()
        |-- model_preferences.py → auto-route for realtime tasks
        |-- world_pulse.py → daily market intel (6 queries)
        |-- research_engine.py → AI landscape scans
        +-- harness_registry.py → 'perplexity' harness entry
```

See references/best_practices.md for rate limits, error codes, pricing, and anti-patterns.

## Gotchas

### Model ID mismatch in model_router
`model_router.py` registers `model_id="llama-3.1-sonar-large-128k-online"` but
`model_preferences.py` references `model="sonar-pro"`. These are different models.
The old `llama-3.1-sonar-large-128k-online` model name may be deprecated.
Current model names are `sonar`, `sonar-pro`, `sonar-reasoning`, `sonar-deep-research`.
Update `model_router.py` to use `sonar-pro` to match preferences.

### Citations not available via OpenAI SDK object
The OpenAI Python SDK's response object does not expose Perplexity-specific fields
like `citations` or `search_results`. You must call `response.model_dump_json()`
or access the raw HTTP response to get citation data. The SDK silently drops
unknown fields from the typed response object.

### search_results vs citations
Perplexity returns two citation formats: `search_results` (array of objects with
title, url, date, snippet) and `citations` (flat array of URLs). `search_results`
is richer but not always present. Always check `search_results` first, fall back
to `citations`. See `openrouter_search.py` `_normalize_results()` for the pattern.

### Streaming drops citations
When using `stream=True`, citation data is only available in the final streamed chunk
or may be absent entirely depending on the model. For citation-dependent workflows,
use non-streaming requests.

### Deep research latency
`sonar-deep-research` can take 30-120+ seconds per request. It runs multiple internal
search iterations. Do not use for real-time conversational responses. Set appropriate
timeouts (minimum 180s) when calling this model.

### Rate limits are per-minute, not per-second
Perplexity rate limits are measured per minute. Burst-sending 50 requests in 1 second
will hit the limit even though you haven't sent 50/min yet. Space requests with
at least 1-second delays for batch operations like world_pulse.

### PERPLEXITY_API_KEY must be in both env files
The key lives in both `eos_ai/.env` and `services/.env`. If only one is set,
some codepaths will route to Perplexity and others won't. The model_preferences
check `_key_available('PERPLEXITY_API_KEY')` loads from whichever env is in scope.
