# Perplexity — Creator-Level Best Practices
Source: https://docs.perplexity.ai/api-reference/chat-completions
API Version: 2024-01-01 (OpenAI-compatible)
SDK Version: openai 1.x (no native Perplexity SDK needed)
Last Researched: 2026-04-06

---

# Tier 1 — Technical Mastery

## Authentication

**Auth method:** API key (Bearer token).
**Token format:** `pplx-` prefix followed by 48 alphanumeric characters.
**Header:** `Authorization: Bearer pplx-...`

**Where to get it:**
1. https://www.perplexity.ai/settings/api
2. Click "Generate" under API Keys
3. Copy immediately — key is shown only once

**EOS env vars:**
- `PERPLEXITY_API_KEY` in `eos_ai/.env` (model_router, world_pulse, research_engine)
- `PERPLEXITY_API_KEY` in `services/.env` (discord_bot, service scripts)

**Token lifetime:** No expiry. Keys persist until manually revoked.
**Rotation:** Manual only — revoke old key, generate new, update both .env files.
**Scopes:** None — single key grants full API access. No per-endpoint permissions.
**Multi-tenant:** Per-account keys only. No org/team/project scoping.

**OpenAI SDK compatibility:**
```python
from openai import OpenAI
client = OpenAI(
    api_key=os.getenv("PERPLEXITY_API_KEY"),
    base_url="https://api.perplexity.ai",
)
```
This works because Perplexity implements the OpenAI chat completions spec exactly.
No Perplexity-specific SDK exists or is needed.

---

## Core Operations with Exact Signatures

Perplexity has a single endpoint: **Chat Completions**.

### POST /chat/completions

```python
response = client.chat.completions.create(
    model: str,                          # REQUIRED — "sonar", "sonar-pro", "sonar-reasoning", "sonar-deep-research"
    messages: list[dict],                # REQUIRED — [{"role": "system"|"user"|"assistant", "content": str}]
    max_tokens: int = None,              # optional — max output tokens (model-dependent defaults)
    temperature: float = 0.2,            # optional — 0.0 to 2.0, controls randomness
    top_p: float = 0.9,                  # optional — nucleus sampling threshold
    top_k: int = 0,                      # optional — top-k sampling (0 = disabled)
    stream: bool = False,                # optional — SSE streaming
    presence_penalty: float = 0.0,       # optional — -2.0 to 2.0
    frequency_penalty: float = 1.0,      # optional — > 0.0 penalizes repeated tokens
    search_domain_filter: list[str] = None,  # optional — restrict search to these domains
    search_recency_filter: str = None,   # optional — "hour", "day", "week", "month"
    return_related_questions: bool = False,  # optional — return suggested follow-ups
    return_images: bool = False,         # optional — return image results
)
```

**Response shape (non-streaming):**
```json
{
  "id": "chatcmpl-abc123",
  "model": "sonar-pro",
  "object": "chat.completion",
  "created": 1709123456,
  "choices": [
    {
      "index": 0,
      "finish_reason": "stop",
      "message": {
        "role": "assistant",
        "content": "The answer with [1] inline citations [2]..."
      },
      "delta": {"role": "assistant", "content": ""}
    }
  ],
  "citations": [
    "https://source1.com/article",
    "https://source2.com/article"
  ],
  "search_results": [
    {
      "title": "Article Title",
      "url": "https://source1.com/article",
      "date": "2026-04-05",
      "snippet": "Relevant excerpt from the page..."
    }
  ],
  "usage": {
    "prompt_tokens": 50,
    "completion_tokens": 200,
    "total_tokens": 250
  },
  "related_questions": [
    "What are the implications of...",
    "How does this compare to..."
  ]
}
```

**Key fields beyond standard OpenAI format:**
- `citations` — flat array of URLs, indexed 1-based matching `[N]` in content
- `search_results` — richer array with title, url, date, snippet (not always present)
- `related_questions` — only present when `return_related_questions=True`

### Available models

| Model | Context | Best For | Latency |
|-------|---------|----------|---------|
| `sonar` | 128k | Quick lookups, simple factual queries | ~2-5s |
| `sonar-pro` | 200k | Market intel, synthesis, multi-source | ~5-15s |
| `sonar-reasoning` | 128k | Complex analysis, chain-of-thought | ~10-30s |
| `sonar-deep-research` | 128k | Multi-step research, comprehensive reports | ~30-120s |

---

## Pagination Patterns

**N/A** — Perplexity has a single chat completions endpoint. No list/query endpoints
that require pagination. All results are returned in a single response.

For multi-turn conversations, pass the full message history in the `messages` array.
There is no session/conversation ID — state is managed client-side.

---

## Rate Limits

Rate limits vary by subscription tier and model:

| Tier | Requests/min | Tokens/min |
|------|-------------|------------|
| Free / Trial | 5 | 20,000 |
| Growth (pay-as-you-go) | 50 | 100,000 |
| Enterprise | Custom | Custom |

**Per-model considerations:**
- `sonar-deep-research` has stricter limits due to internal multi-step execution
- Each internal search step in deep-research counts against token limits

**Rate limit response:**
- HTTP 429 Too Many Requests
- `Retry-After` header with seconds to wait
- Response body: `{"error": {"message": "Rate limit exceeded", "type": "rate_limit_error"}}`

**Recommended backoff strategy:**
```python
import time

def call_with_retry(client, max_retries=3, **kwargs):
    for attempt in range(max_retries):
        try:
            return client.chat.completions.create(**kwargs)
        except Exception as e:
            if "429" in str(e) or "rate_limit" in str(e):
                wait = 2 ** attempt * 5  # 5s, 10s, 20s
                time.sleep(wait)
            else:
                raise
    raise RuntimeError("Rate limit retries exhausted")
```

**EOS context:** World pulse runs 6 queries sequentially. At ~10s per sonar-pro call,
natural spacing keeps well under 50 req/min. No explicit throttling needed for
current workload.

---

## Error Codes and Recovery

| HTTP Code | Error Type | Meaning | Recovery |
|-----------|-----------|---------|----------|
| 400 | `invalid_request_error` | Malformed request, invalid model name, bad params | Fix request. Not retryable. |
| 401 | `authentication_error` | Invalid or missing API key | Check `PERPLEXITY_API_KEY`. Not retryable. |
| 403 | `permission_error` | Key lacks access to requested model/feature | Check subscription tier. Not retryable. |
| 404 | `not_found_error` | Invalid endpoint or deprecated model ID | Update model name. Not retryable. |
| 422 | `validation_error` | Messages format invalid, empty content | Fix message structure. Not retryable. |
| 429 | `rate_limit_error` | Rate limit exceeded | Retry after backoff. Retryable. |
| 500 | `internal_error` | Perplexity server error | Retry with backoff. Retryable. |
| 502/503 | `service_unavailable` | Perplexity temporarily down | Retry after 30s. Retryable. |

**Error response format:**
```json
{
  "error": {
    "message": "Human-readable error description",
    "type": "error_type_slug",
    "code": 429
  }
}
```

**EOS-specific errors observed:**
- Deprecated model ID `llama-3.1-sonar-large-128k-online` may return 404 —
  update to `sonar-pro` in model_router.py
- Empty API key returns 401, not a descriptive "key missing" message

---

## SDK Idioms

**Package:** `openai` (PyPI). No native Perplexity SDK.
**Import:** `from openai import OpenAI`
**Init:**
```python
client = OpenAI(
    api_key=os.getenv("PERPLEXITY_API_KEY"),
    base_url="https://api.perplexity.ai",
)
```

**Sync vs Async:**
```python
# Sync (used in EOS model_router)
response = client.chat.completions.create(model="sonar-pro", messages=messages)

# Async
from openai import AsyncOpenAI
async_client = AsyncOpenAI(
    api_key=os.getenv("PERPLEXITY_API_KEY"),
    base_url="https://api.perplexity.ai",
)
response = await async_client.chat.completions.create(model="sonar-pro", messages=messages)
```

**Accessing Perplexity-specific fields:**
The OpenAI SDK typed response does not include `citations` or `search_results`.
Access them via:
```python
# Option 1: model_dump (dict)
raw = response.model_dump()
citations = raw.get("citations", [])

# Option 2: JSON roundtrip
import json
raw = json.loads(response.model_dump_json())
citations = raw.get("citations", [])

# Option 3: httpx raw response (if using custom client)
# Access response.headers for rate limit info
```

**EOS pattern (model_router.py line 522-551):**
```python
def _call_openai_compatible(self, config, prompt, system, max_tokens):
    client = OpenAI(api_key=os.getenv(config.api_key_env), base_url=config.base_url)
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})
    response = client.chat.completions.create(
        model=config.model_id, messages=messages, max_tokens=max_tokens,
    )
    return response.choices[0].message.content or ""
```
Note: EOS currently does not extract citations — only the text content.

---

## Anti-Patterns

### 1. Using old model IDs
```python
# WRONG — deprecated model name
model="llama-3.1-sonar-large-128k-online"

# RIGHT — current model name
model="sonar-pro"
```
Perplexity moved from `llama-3.1-sonar-*` naming to simplified `sonar-*` names.
Old names may return 404 or route to different models silently.

### 2. Expecting citations in the SDK typed response
```python
# WRONG — citations is not a field on ChatCompletion
citations = response.citations  # AttributeError

# RIGHT — access via dict dump
raw = response.model_dump()
citations = raw.get("citations", [])
```

### 3. Using high temperature for factual search
```python
# WRONG — high temp = creative/random answers, defeats search grounding
temperature=1.5

# RIGHT — low temp for factual web search
temperature=0.2  # or omit for default 0.2
```
Perplexity defaults to 0.2 for good reason — search-grounded answers should
be deterministic, not creative.

### 4. Ignoring search_recency_filter for time-sensitive queries
```python
# WRONG — may return outdated results for "this week" queries
messages=[{"role": "user", "content": "AI news this week"}]

# RIGHT — explicitly filter recent results
search_recency_filter="week"
```

### 5. Using sonar-deep-research with short timeouts
```python
# WRONG — deep research needs 30-120s, default timeout is 30s
response = client.chat.completions.create(
    model="sonar-deep-research", messages=messages
)

# RIGHT — set appropriate timeout
response = client.chat.completions.create(
    model="sonar-deep-research", messages=messages,
    timeout=180.0,  # 3 minutes
)
```

### 6. Sending empty system message
```python
# WRONG — some models treat empty system message differently
messages=[{"role": "system", "content": ""}, {"role": "user", "content": "query"}]

# RIGHT — omit system message if not needed
messages=[{"role": "user", "content": "query"}]
```

---

## Data Model

Perplexity has a minimal data model — it is a stateless API.

**Request entities:**
- `Message` — `{role: "system"|"user"|"assistant", content: str}`
- `ChatCompletionRequest` — model + messages[] + optional params

**Response entities:**
- `ChatCompletion` — id, model, choices[], citations[], search_results[], usage
- `Choice` — index, finish_reason, message
- `Citation` — bare URL string (indexed 1-based)
- `SearchResult` — `{title: str, url: str, date: str|null, snippet: str}`
- `Usage` — prompt_tokens, completion_tokens, total_tokens
- `RelatedQuestion` — bare string (suggested follow-up)

**Relationships:**
- `[N]` markers in `choices[0].message.content` map to `citations[N-1]`
- `search_results` entries correspond to citations but with richer metadata
- `related_questions` are independent suggestions, not tied to citations

**No persistent state:** Perplexity does not store conversations, histories,
or user data server-side. Every request is independent. Multi-turn context
must be passed in the messages array each time.

---

## Webhooks and Events

**N/A** — Perplexity provides no webhook or event system. It is a stateless
request-response API. There are no callbacks, subscriptions, or push notifications.

For event-driven patterns in EOS, the orchestrator triggers Perplexity calls
on a cron schedule (6am daily world pulse) rather than reacting to events.

---

## Limits

| Limit | Value |
|-------|-------|
| Max messages per request | No hard limit (bounded by context window) |
| Context window (sonar) | 128,000 tokens |
| Context window (sonar-pro) | 200,000 tokens |
| Context window (sonar-reasoning) | 128,000 tokens |
| Context window (sonar-deep-research) | 128,000 tokens |
| Max output tokens (sonar) | 4,096 |
| Max output tokens (sonar-pro) | 8,192 |
| Max output tokens (sonar-reasoning) | 8,192 |
| Max output tokens (sonar-deep-research) | 16,384 |
| search_domain_filter max domains | 3 |
| Message content max length | No documented hard limit (bounded by context) |
| Request body size | Standard HTTP limits (~10MB) |
| Concurrent requests | Governed by rate limit, not explicit concurrency cap |

---

## Cost Model

**Pricing (per 1M tokens, as of 2025):**

| Model | Input $/1M | Output $/1M | Search Cost | Notes |
|-------|-----------|------------|-------------|-------|
| sonar | $1.00 | $1.00 | $5/1000 searches | Cheapest, fast |
| sonar-pro | $3.00 | $15.00 | $5/1000 searches | EOS default |
| sonar-reasoning | $2.00 | $8.00 | $5/1000 searches | CoT included |
| sonar-deep-research | $2.00 | $8.00 | $5/1000 searches | Multi-step |

**Search cost:** Each API call that triggers a web search incurs the per-search fee
regardless of token count. A simple "hello" costs a search fee if sent to a sonar model.

**EOS cost estimate:**
- World pulse: 6 queries/day x sonar-pro = ~$0.03/day search + ~$0.01 tokens = ~$0.04/day
- Monthly world pulse: ~$1.20
- Ad-hoc research: variable, typically $0.01-0.05 per query

**Budget monitoring:** Perplexity dashboard at https://www.perplexity.ai/settings/api
shows usage and remaining credits. No programmatic budget alerts.

**Free tier:** New accounts get $5 free API credits. No ongoing free tier.

---

## Version Pinning

**API versioning:** Perplexity does not use explicit API version headers or URL versioning.
The API is versioned implicitly through model names. When models change, the model ID
changes (e.g., `llama-3.1-sonar-large-128k-online` → `sonar-pro`).

**SDK versioning:** Uses the `openai` Python package. Pin in requirements:
```
openai>=1.0.0
```
No Perplexity-specific SDK to pin.

**Model deprecation pattern:**
- Old model names (e.g., `llama-3.1-sonar-*`) are deprecated silently or return 404
- No formal deprecation timeline published
- Monitor https://docs.perplexity.ai/changelog for model updates

**EOS action items:**
- `model_router.py` uses `llama-3.1-sonar-large-128k-online` — should be updated to `sonar-pro`
- `model_preferences.py` already uses `sonar-pro` — this is correct
- Check model names quarterly or when API calls start returning 404

---

# Tier 2 — Creator Intelligence

## Design Intent and Tradeoffs

**Why Perplexity was built:**
Aravind Srinivas (CEO) built Perplexity to be the "answer engine" — not a search engine
that returns links, but an AI that reads the web and gives you the answer directly with
sources. The core insight: most searches are questions, and users want answers, not
10 blue links to read themselves.

**Design philosophy:**
- **Search-first, not generation-first** — every response starts with a live web search.
  The LLM synthesizes search results, not its training data. This inverts the typical
  ChatGPT pattern where web search is optional.
- **Citation as first-class citizen** — inline `[N]` citations are not optional metadata,
  they are core to the response format. Every claim should be verifiable.
- **OpenAI compatibility** — deliberate choice to use the OpenAI chat completions format
  so any existing OpenAI integration can swap in Perplexity with a base_url change.

**Conscious tradeoffs:**
- Latency > hallucination: Perplexity is slower than pure LLM calls because every
  request runs a web search first. This is by design — freshness over speed.
- Breadth > depth: sonar/sonar-pro cast a wide net across many sources rather than
  deeply analyzing one. sonar-deep-research trades this for depth.
- No conversation memory: stateless by design. Perplexity is a search tool, not a
  persistent assistant. This keeps the API simple and privacy-friendly.

**What Perplexity is NOT:**
- Not a general-purpose LLM — don't use it for creative writing, code generation, or
  tasks that don't benefit from web grounding.
- Not a replacement for domain-specific databases — it searches the public web, not
  your private data.

---

## Problem-Solution Map and Hidden Capabilities

**Problem: Real-time competitive intelligence**
Perplexity excels at "what is X doing right now?" queries that would require manual
monitoring across dozens of sources. The AI reads recent articles, social posts, and
news, then synthesizes a competitive brief. EOS uses this for daily competitor monitoring
in world_pulse.py.

**Problem: Price/feature comparison with current data**
Ask Perplexity to compare current pricing across services (hosting, APIs, SaaS tools)
and it returns today's prices, not training-data prices from months ago.

**Problem: Fact-checking claims before publishing**
Route fact-check queries through Perplexity before publishing content. The citations
provide verifiable sources for any claim.

**Hidden capability: search_domain_filter as a site-specific search engine**
Use `search_domain_filter=["docs.python.org"]` to turn Perplexity into a
documentation-specific search engine. Searches only that domain and synthesizes results.

**Hidden capability: search_recency_filter + domain_filter for monitoring**
Combine `search_recency_filter="day"` with a competitor's domain to get a daily
digest of their new content without scraping.

**Hidden capability: multi-turn for progressive research**
Pass previous Q&A in messages to build on prior research. Perplexity searches fresh
for each turn, so follow-up questions get new web results informed by prior context.

**Hidden capability: sonar-reasoning for analysis with sources**
sonar-reasoning provides chain-of-thought reasoning grounded in web results —
essentially a research analyst that shows its work with citations.

---

## Operational Behavior and Edge Cases

**Search quality varies by query specificity:**
Vague queries ("tell me about AI") return generic results. Specific queries
("Anthropic Claude pricing changes April 2026") return targeted, high-quality results.
Always craft prompts with specific entities, timeframes, and domains.

**Citation numbering is 1-based:**
Content references `[1]` maps to `citations[0]`. Off-by-one errors are common
when parsing citation references programmatically.

**search_results not always present:**
The `search_results` array with rich metadata (title, url, date, snippet) is not
guaranteed. Some responses only return the flat `citations` array. Always code
defensively: check `search_results` first, fall back to `citations`.

**Empty citations on non-search queries:**
If the model determines no web search is needed (e.g., "what is 2+2"), the response
may have empty `citations` and no `search_results`. Don't assume every response
has citations.

**Timeout behavior:**
- sonar: ~2-5s typical, rarely >10s
- sonar-pro: ~5-15s typical, can reach 30s on complex queries
- sonar-deep-research: ~30-120s, can exceed 180s on comprehensive topics
- The OpenAI SDK default timeout is 600s, but EOS should set per-model timeouts

**Eventual consistency in search index:**
Very recent content (published within the last hour) may not appear in results even
with `search_recency_filter="hour"`. Perplexity's search index has a delay of
~15-60 minutes for new content.

**Unicode and encoding:**
Responses handle Unicode correctly. International characters in queries and results
work without special handling. Emoji in queries work but may confuse search intent.

---

## Ecosystem Position and Composition

**Position:** Perplexity sits as a **real-time knowledge layer** in EOS's architecture.
It is not the reasoning engine (that's Anthropic/Gemini) or the data store (that's Neon).
It's the bridge between "what does the AI know from training" and "what's true right now."

**Natural complements in EOS:**
- **Anthropic (Opus/Sonnet)** — strategic reasoning on top of Perplexity's fresh data
- **Neon Postgres** — store Perplexity research results as persistent knowledge
- **Apify** — when Perplexity can't access paywalled/authenticated content, Apify scrapes it
- **Knowledge Integrator** — world_pulse feeds Perplexity results into EOS's permanent memory

**Data flow in EOS:**
```
Perplexity (fresh web data) → world_pulse.py → KnowledgeIntegrator → Neon (permanent)
                            → research_engine.py → domain knowledge updates
```

**What Perplexity replaces:**
- Manual Google searching + reading articles
- RSS feed monitoring for market changes
- Setting up custom news alerts

**What Perplexity cannot replace:**
- Apify for scraping specific structured data (product listings, social metrics)
- Google Gemini for document/image analysis
- Direct database queries for internal business data

**Integration anti-pattern:** Don't chain Perplexity → Perplexity (search about search).
If first query returns insufficient data, refine the query rather than asking
Perplexity to elaborate on its own previous answer without new search context.

---

## Trajectory and Evolution

**Where Perplexity is heading:**
- Sonar model family keeps expanding: from sonar → sonar-pro → sonar-reasoning →
  sonar-deep-research. Expect more specialized variants.
- Deep research is the growth area: multi-step autonomous research with iterative
  search refinement is the premium tier.
- Image and multimodal search is expanding (return_images parameter).

**Deprecation signals:**
- `llama-3.1-sonar-*` model names are already deprecated → `sonar-*` is current
- The `pplx-` prefix models (like `pplx-70b-online`) from 2024 are fully dead
- Expect model name changes every 6-12 months as underlying models upgrade

**What to build on (safe):**
- The OpenAI-compatible chat completions format — this is their stable interface
- `sonar` and `sonar-pro` model names — core product
- Citations in responses — fundamental to the product

**What to be cautious about:**
- Specific model capability details (context windows, max output) change with updates
- `search_results` response field format may evolve
- Pricing changes frequently as Perplexity scales

**EOS implications:**
- Keep model_router.py model IDs updated quarterly
- Don't build workflows that depend on exact citation format — parse defensively
- Budget for price increases as Perplexity matures from growth-stage pricing

---

## Conceptual Model and Solution Recipes

**Mental model:** Think of Perplexity as a **research assistant with a browser**.
You ask a question, it opens multiple tabs, reads the content, synthesizes an answer,
and gives you the source links. The primitives are:

- **Query** — the question you ask (prompt engineering matters for search quality)
- **Search** — the web lookup Perplexity performs automatically
- **Synthesis** — the LLM combining search results into a coherent answer
- **Citations** — the evidence chain linking claims to sources
- **Recency** — the time filter controlling how fresh results must be

**Recipe 1: Daily competitive intelligence briefing**
```
1. Define competitor list and monitoring dimensions
2. Craft specific queries per competitor: "{name} new content/offers/pricing {date_range}"
3. Set search_recency_filter="week" for weekly monitoring
4. Call sonar-pro with max_tokens=500 per query (concise intel, not essays)
5. Store results in Neon via KnowledgeIntegrator
6. Post digest to Discord via webhook
→ EOS does this in world_pulse.py with PERPLEXITY_QUERIES
```

**Recipe 2: Market pricing research**
```
1. Query: "Current pricing for {service category} in {year}"
2. Use search_domain_filter to target review/comparison sites
3. Extract pricing data from response content
4. Store as structured data in knowledge domain
5. Compare against last month's scan for changes
→ Used in research_engine.scan_ai_landscape()
```

**Recipe 3: Content idea validation**
```
1. Before creating content, query: "What content about {topic} is performing well this {period}?"
2. Use sonar-pro for broad synthesis across platforms
3. Check citations for top-performing pieces
4. Identify gaps — what's NOT being covered well
5. Create content targeting the gap
→ Supports personal brand content strategy
```

**Recipe 4: Real-time fact-checking pipeline**
```
1. Agent generates a claim or statistic
2. Route to Perplexity: "Verify: {claim}. Provide sources."
3. Check citations — at least 2 independent sources for factual claims
4. If citations conflict or are thin, flag for human review
5. Include verified citations in published content
→ Can be added to content publishing workflow
```

**Recipe 5: Technology scouting**
```
1. Weekly query: "New {technology category} tools/releases this week"
2. Use sonar-reasoning for deeper analysis of implications
3. Filter for relevance to current tech stack
4. Store as technology domain knowledge
5. Surface actionable items in morning brief
→ Supports research_engine AI landscape scans
```

---

## Industry Expert and Cutting-Edge Usage

**AI agent web grounding (frontier pattern):**
The most powerful use of Perplexity in agent systems is as a "grounding layer" —
before any agent makes a decision based on external facts, route the factual questions
through Perplexity first. This prevents the common agent failure mode of acting on
stale training data. EOS already does this for market intel; extend it to any agent
that reasons about external reality.

**Multi-model research pipeline:**
Expert pattern: Use Perplexity sonar for initial web research, then pass the results
(with citations) to a stronger reasoning model (Opus, Gemini) for strategic analysis.
The reasoning model gets fresh data without needing web access itself. This is more
cost-effective than using sonar-deep-research for everything.

**Citation verification as quality signal:**
Count the number of unique domains in citations. Answers backed by 5+ independent
sources are more reliable than answers citing the same site repeatedly. Use citation
diversity as a programmatic confidence score.

**Structured data extraction from web:**
Use Perplexity's system message to request structured output:
```python
system = "Return results as JSON with keys: name, price, url, last_updated"
```
Perplexity synthesizes web data into your requested structure. More reliable than
scraping + parsing for semi-structured public data.

**Temporal comparison queries:**
Ask Perplexity to compare "now vs 3 months ago" for any metric/trend. The model
searches for both current and historical data points. Useful for tracking market
shifts without maintaining your own time-series data.

**Deep research for long-form content:**
sonar-deep-research can produce 2000+ word research reports with 20+ citations in
a single call. Use it for quarterly market reports, competitive analyses, or
research briefs that would take hours manually. Worth the 30-120s latency.

---

## EOS Usage Patterns

**Primary integration:** `eos_ai/model_router.py` via `_call_openai_compatible()`.
All Perplexity calls route through the same OpenAI-compatible codepath as Groq.
The router creates a new `OpenAI` client per call (no connection pooling).

**Task type routing:** `TaskType.WEB_SEARCH` and `TaskType.MARKET_INTEL` both
route to `perplexity-sonar` when the key is available. If unavailable, falls back
to next provider in the fallback chain.

**Current model ID issue:** `model_router.py` uses `llama-3.1-sonar-large-128k-online`
while `model_preferences.py` uses `sonar-pro`. These should be reconciled to `sonar-pro`.

**Citation extraction gap:** EOS currently extracts only `response.choices[0].message.content`
and discards citations. For world_pulse market intel, citations would add source
verification to stored signals. Consider extracting `citations` in the router or
in world_pulse `_scan_with_perplexity()`.

---

## Gotchas

### Model ID mismatch between router and preferences
`model_router.py` registers `llama-3.1-sonar-large-128k-online` but `model_preferences.py`
references `sonar-pro`. The old ID may be deprecated or map to a different model.
Action: update model_router.py to use `sonar-pro`.

### Citations silently dropped by OpenAI SDK
The typed `ChatCompletion` response from the `openai` package does not include
Perplexity-specific fields. Use `response.model_dump()` to get the full dict
including `citations` and `search_results`.

### WebFetch/WebSearch unavailable during research
Could not access live Perplexity API docs during skill creation. Pricing, rate limits,
and model details are based on training data (last verified May 2025) and codebase
analysis. Verify current pricing at https://docs.perplexity.ai/guides/pricing.

### search_domain_filter limited to 3 domains
You cannot filter to more than 3 domains per request. For broader domain filtering,
make multiple requests or filter client-side from the citations.
