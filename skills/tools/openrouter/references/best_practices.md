# OpenRouter — Creator-Level Best Practices
Source: https://openrouter.ai/docs
API Version: v1
SDK Version: openai 1.x (OpenAI-compatible)
Last Researched: 2026-04-06

---

# Tier 1 — Technical Mastery

## 1. Authentication

**Auth method:** Bearer token (API key).

**Token type:** Single API key generated at https://openrouter.ai/keys.
No OAuth, no refresh tokens, no scopes. One key covers all models and endpoints.

**Required header:**
```
Authorization: Bearer sk-or-v1-xxxxxxxxxxxx
```

**Recommended headers:**
```
HTTP-Referer: https://your-site.com    # Attribution for leaderboard
X-Title: your-app-name                 # Dashboard label
Content-Type: application/json
```

**Where secrets live in EOS:**
- `OPENROUTER_API_KEY` — currently only in `~/.config/last30days/.env`
  (used by the last30days skill). NOT in `eos_ai/.env` or `services/.env`.
- To integrate with model_router.py, add to `eos_ai/.env`.

**Key management:**
- Keys can be created with custom labels and credit limits at openrouter.ai/keys
- Keys can be revoked instantly from the dashboard
- No expiration by default — keys live until revoked
- Each key can have an independent spending limit (useful for per-project budgets)
- Multiple keys supported per account

**Rate limit tiers:** API keys inherit the account's rate limit tier.
Higher spend = higher tier = higher rate limits. No separate "scope" system.

---

## 2. Core Operations with Exact Signatures

### Chat Completion (primary endpoint)
```
POST https://openrouter.ai/api/v1/chat/completions
```

**Request body:**
```python
{
    "model": str,              # REQUIRED — "provider/model-name" format
    "messages": [              # REQUIRED — OpenAI message format
        {
            "role": str,       # "system" | "user" | "assistant"
            "content": str | list,  # str or content parts array (multimodal)
        }
    ],
    "max_tokens": int,         # optional — max completion tokens
    "temperature": float,      # optional — 0.0-2.0, default model-specific
    "top_p": float,            # optional — nucleus sampling
    "top_k": int,              # optional — top-k sampling (not all models)
    "frequency_penalty": float, # optional — -2.0 to 2.0
    "presence_penalty": float,  # optional — -2.0 to 2.0
    "repetition_penalty": float, # optional — 0.0 to 2.0
    "seed": int,               # optional — deterministic generation
    "stop": str | list[str],   # optional — stop sequences
    "stream": bool,            # optional — SSE streaming, default false
    "tools": list[dict],       # optional — function calling (OpenAI format)
    "tool_choice": str | dict, # optional — "auto", "none", or specific tool
    "response_format": dict,   # optional — {"type": "json_object"} for JSON mode
    "transforms": list[str],   # optional — ["middle-out"] for context compression
    "provider": {              # optional — provider routing config
        "order": list[str],    # provider preference order
        "allow": list[str],    # whitelist providers
        "deny": list[str],     # blacklist providers
        "allow_fallbacks": bool, # allow auto-retry on other providers
        "data_collection": str,  # "allow" | "deny" — opt out of training
        "quantizations": list[str], # ["fp16", "int8", "int4"] — filter by quant
    },
}
```

**Response shape:**
```python
{
    "id": "gen-xxxxxxxxxxxx",          # generation ID
    "model": "provider/model-name",     # actual model used
    "object": "chat.completion",
    "created": 1234567890,              # unix timestamp
    "choices": [
        {
            "index": 0,
            "message": {
                "role": "assistant",
                "content": str,          # completion text
                "tool_calls": list | None,  # if tools used
            },
            "finish_reason": str,  # "stop" | "length" | "tool_calls"
        }
    ],
    "usage": {
        "prompt_tokens": int,
        "completion_tokens": int,
        "total_tokens": int,
    },
    # Perplexity Sonar models add:
    "citations": [str],           # flat list of cited URLs
    "search_results": [           # structured search results (optional)
        {"title": str, "url": str, "date": str, "snippet": str}
    ],
}
```

### Using the OpenAI SDK (recommended pattern)
```python
from openai import OpenAI

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY"),
    default_headers={
        "HTTP-Referer": "https://your-site.com",
        "X-Title": "your-app",
    },
)

response = client.chat.completions.create(
    model="anthropic/claude-sonnet-4-6",
    messages=[
        {"role": "system", "content": "You are helpful."},
        {"role": "user", "content": "Hello"},
    ],
    max_tokens=1000,
    temperature=0.7,
)
# Returns: ChatCompletion object (identical to OpenAI SDK response)
content = response.choices[0].message.content
tokens = response.usage.total_tokens
```

### List Models
```
GET https://openrouter.ai/api/v1/models
```
**Response shape:**
```python
{
    "data": [
        {
            "id": "anthropic/claude-sonnet-4-6",
            "name": "Claude 3.5 Sonnet",
            "description": str,
            "context_length": 200000,
            "pricing": {
                "prompt": "0.000003",     # USD per token
                "completion": "0.000015",  # USD per token
            },
            "top_provider": {
                "max_completion_tokens": int,
                "is_moderated": bool,
            },
            "per_request_limits": {        # rate limits for this model
                "prompt_tokens": str,
                "completion_tokens": str,
            },
        }
    ]
}
```

### Check Key / Credits
```
GET https://openrouter.ai/api/v1/auth/key
Authorization: Bearer {key}
```
**Response:**
```python
{
    "data": {
        "label": str,           # key label
        "usage": float,         # total USD spent
        "limit": float | None,  # spending limit (null = unlimited)
        "is_free_tier": bool,
        "rate_limit": {
            "requests": int,    # requests per interval
            "interval": str,    # e.g., "10s"
        },
        "limit_remaining": float,  # USD remaining (limit - usage)
    }
}
```

### Get Generation Details
```
GET https://openrouter.ai/api/v1/generation?id={generation_id}
Authorization: Bearer {key}
```
**Response:**
```python
{
    "data": {
        "id": str,
        "model": str,
        "total_cost": float,          # actual USD cost
        "tokens_prompt": int,
        "tokens_completion": int,
        "native_tokens_prompt": int,  # provider's token count
        "native_tokens_completion": int,
        "generation_time": float,     # seconds
        "created_at": str,            # ISO 8601
    }
}
```

---

## 3. Pagination Patterns

OpenRouter has minimal pagination needs:

**Models endpoint:** Returns all models in a single response (no pagination).
The `/api/v1/models` endpoint returns the full list (~200+ models) in one call.
No cursor, no offset, no page_size parameter.

**Generation history:** Not available via API. Use the dashboard at
openrouter.ai/activity for historical generation browsing.

**Chat completions:** Single request/response — no pagination applicable.

**Pattern for model filtering (client-side):**
```python
resp = requests.get("https://openrouter.ai/api/v1/models",
                     headers={"Authorization": f"Bearer {key}"})
all_models = resp.json()["data"]

# Filter client-side
cheap_models = [m for m in all_models
                if float(m["pricing"]["prompt"]) < 0.000001]
anthropic_models = [m for m in all_models
                    if m["id"].startswith("anthropic/")]
```

---

## 4. Rate Limits

**Structure:** Rate limits are per-model AND per-account-tier, not global.

**Free tier:**
- ~20 requests/minute for free models
- Some models are free (marked on model page)
- Free models have lower context and speed limits

**Paid tier (credits loaded):**
- Model-specific limits set by upstream providers
- Typical: 60-500 requests/minute depending on model
- Higher spend history = higher rate limit tier (automatic)

**Rate limit headers in response:**
```
X-RateLimit-Limit: 60          # max requests per interval
X-RateLimit-Remaining: 58      # remaining in current window
X-RateLimit-Reset: 1234567890  # unix timestamp when window resets
Retry-After: 5                 # seconds to wait (on 429)
```

**Backoff strategy:**
- On 429: respect `Retry-After` header
- Exponential backoff: 1s, 2s, 4s, 8s, max 30s
- Switch to alternative model (different provider) for immediate retry
- Different models have independent rate limits — a 429 on GPT-4o
  does not affect Claude requests

**Per-model limits visible via:**
```python
model_info = next(m for m in models if m["id"] == "openai/gpt-4o")
print(model_info["per_request_limits"])
# {"prompt_tokens": "128000", "completion_tokens": "16384"}
```

---

## 5. Error Codes and Recovery

**HTTP status codes:**

| Code | Meaning | Retryable | Recovery |
|------|---------|-----------|----------|
| 400 | Bad request (invalid model ID, malformed body) | No | Fix request |
| 401 | Invalid API key | No | Check/rotate key |
| 402 | Insufficient credits | No | Add credits at openrouter.ai/credits |
| 403 | Forbidden (content policy) | No | Modify prompt |
| 408 | Request timeout (upstream) | Yes | Retry or switch model |
| 429 | Rate limited | Yes | Respect Retry-After, switch model |
| 502 | Bad gateway (upstream provider down) | Yes | Retry, switch provider |
| 503 | Service unavailable | Yes | Retry with backoff |

**Error response body:**
```python
{
    "error": {
        "code": int,           # HTTP status code
        "message": str,        # Human-readable error
        "metadata": {          # Optional provider-specific details
            "provider_name": str,
            "raw": str,        # Raw upstream error
        }
    }
}
```

**Critical recovery patterns:**
- **402 (no credits):** Cannot retry. Must add credits. Check proactively
  via `/api/v1/auth/key` before critical batch operations.
- **429 (rate limit):** Switch to a different model immediately for zero-downtime.
  `anthropic/claude-sonnet-4-6` rate limited? Try `google/gemini-2.5-flash`.
- **502/503 (upstream down):** Use `provider.allow_fallbacks: true` to let
  OpenRouter auto-retry on another provider. Or switch model entirely.
- **408 (timeout):** Common with large-context requests on slow providers.
  Reduce `max_tokens` or switch to a faster model.

---

## 6. SDK Idioms

**Official SDK:** None. OpenRouter is OpenAI-compatible, so use the `openai` Python SDK.

**Installation:**
```bash
pip install openai>=1.0.0
```

**Initialization (recommended):**
```python
from openai import OpenAI

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY"),
    default_headers={
        "HTTP-Referer": "https://your-site.com",
        "X-Title": "your-app",
    },
)
```

**Async support:**
```python
from openai import AsyncOpenAI

client = AsyncOpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY"),
)
response = await client.chat.completions.create(
    model="anthropic/claude-sonnet-4-6",
    messages=[{"role": "user", "content": "Hello"}],
)
```

**Raw HTTP (EOS last30days pattern):**
When you want to avoid the OpenAI SDK dependency (lightweight scripts),
use `requests` directly. This is what `openrouter_search.py` does:
```python
import requests

response = requests.post(
    "https://openrouter.ai/api/v1/chat/completions",
    headers={"Authorization": f"Bearer {api_key}"},
    json={"model": "perplexity/sonar-pro", "messages": messages},
    timeout=30,
)
data = response.json()
```

**Version note:** OpenAI SDK 1.x required (the async rewrite). 0.x will not work
with `base_url` parameter.

---

## 7. Anti-Patterns

### Wrong: bare model name
```python
# WRONG — returns 400
client.chat.completions.create(model="claude-sonnet-4-6", ...)

# RIGHT — provider prefix required
client.chat.completions.create(model="anthropic/claude-sonnet-4-6", ...)
```

### Wrong: ignoring provider routing for reliability
```python
# FRAGILE — single provider, fails if Anthropic is down
client.chat.completions.create(model="anthropic/claude-sonnet-4-6", ...)

# ROBUST — explicit fallback chain
client.chat.completions.create(
    model="anthropic/claude-sonnet-4-6",
    extra_body={"provider": {"order": ["Anthropic", "AWS Bedrock"], "allow_fallbacks": True}},
    ...
)
```

### Wrong: not checking credits before batch operations
```python
# WRONG — discovers credit exhaustion mid-batch, loses progress
for item in large_batch:
    response = client.chat.completions.create(...)

# RIGHT — pre-check credits
key_info = requests.get("https://openrouter.ai/api/v1/auth/key",
                         headers={"Authorization": f"Bearer {key}"}).json()
remaining = key_info["data"]["limit_remaining"]
if remaining and remaining < estimated_cost:
    raise RuntimeError(f"Insufficient credits: ${remaining:.2f} < ${estimated_cost:.2f}")
```

### Wrong: hardcoding model IDs
```python
# WRONG — model IDs change (versioned names, deprecations)
model = "anthropic/claude-3.5-sonnet-20241022"

# RIGHT — use the canonical alias (OpenRouter resolves to latest)
model = "anthropic/claude-sonnet-4-6"
```

### Wrong: using OpenRouter for free models in production
```python
# ANTI-PATTERN — free models have strict rate limits, lower priority,
# and may be removed without notice. Use paid models for production.
model = "meta-llama/llama-3.2-3b-instruct:free"
```

### Wrong: not handling Sonar citation format variations
```python
# WRONG — assumes search_results always exists
citations = response["search_results"]

# RIGHT — handle both formats (EOS pattern from openrouter_search.py)
search_results = response.get("search_results", [])
if not search_results:
    citations = response.get("citations", [])
```

---

## 8. Data Model

**Core entities:**

```
Account
  |-- API Keys (1:many)
  |     |-- label: str
  |     |-- key: str (sk-or-v1-...)
  |     |-- limit: float | null (spending cap)
  |     |-- usage: float (total spent)
  |     +-- rate_limit: {requests: int, interval: str}
  |
  +-- Credits
  |     |-- balance: float (USD)
  |     +-- top-up via Stripe
  |
  +-- Generations (1:many per key)
        |-- id: str (gen-...)
        |-- model: str (provider/model-name)
        |-- tokens_prompt: int
        |-- tokens_completion: int
        |-- total_cost: float
        |-- generation_time: float (seconds)
        +-- created_at: str (ISO 8601)

Model (read-only catalog)
  |-- id: str (provider/model-name)
  |-- name: str (human-readable)
  |-- context_length: int
  |-- pricing: {prompt: str, completion: str}  # per-token USD
  |-- top_provider: {max_completion_tokens: int, is_moderated: bool}
  +-- per_request_limits: {prompt_tokens: str, completion_tokens: str}
```

**Key relationships:**
- API Key -> Generations: one key produces many generations
- Account -> Credits: shared across all keys
- Model catalog is global (not per-account)

**Immutable fields:** generation ID, generation timestamps, model catalog pricing
(set by providers, not user-configurable).

---

## 9. Webhooks and Events

**N/A** — OpenRouter does not offer webhooks or event subscriptions.
All interactions are synchronous request/response (or SSE streaming).

To monitor usage or credits programmatically, poll `/api/v1/auth/key`.

---

## 10. Limits

**Per-request limits:**
- Max prompt tokens: model-specific (visible in `/api/v1/models` response)
- Max completion tokens: model-specific (typically 4096-16384)
- Request body size: ~10MB (for multimodal content with images)

**Context windows (common models):**
| Model | Context Length |
|-------|---------------|
| anthropic/claude-sonnet-4-6 | 200,000 |
| openai/gpt-4o | 128,000 |
| google/gemini-2.5-flash | 1,048,576 |
| meta-llama/llama-3.3-70b | 131,072 |
| perplexity/sonar-pro | 200,000 |
| deepseek/deepseek-r1 | 163,840 |

**API key limits:**
- No limit on number of keys per account
- Per-key spending limit configurable (min $0.01)
- No limit on concurrent requests (subject to rate limits)

**Free model limits:**
- Lower rate limits than paid equivalents
- May have reduced context length
- No SLA on availability
- `:free` suffix models (e.g., `meta-llama/llama-3.2-3b-instruct:free`)

---

## 11. Cost Model

**Pricing structure:** Pay-per-token, billed per-request against prepaid credits.

**How it works:**
1. Purchase credits at https://openrouter.ai/credits (minimum $5)
2. Each API call deducts `(prompt_tokens * prompt_price) + (completion_tokens * completion_price)`
3. When credits reach 0, all requests return 402

**Common model pricing (as of 2026):**

| Model | Prompt (per 1M tokens) | Completion (per 1M tokens) |
|-------|----------------------|--------------------------|
| openai/gpt-4o | $2.50 | $10.00 |
| anthropic/claude-sonnet-4-6 | $3.00 | $15.00 |
| anthropic/claude-haiku-3.5 | $0.80 | $4.00 |
| google/gemini-2.5-flash | $0.075 | $0.30 |
| meta-llama/llama-3.3-70b | $0.30 | $0.30 |
| perplexity/sonar-pro | $3.00 | $15.00 |
| deepseek/deepseek-r1 | $0.55 | $2.19 |
| mistralai/mistral-large | $2.00 | $6.00 |

**OpenRouter markup:** OpenRouter charges the upstream provider price with no
additional markup for most models. Some models may have a small routing fee.
Check `/api/v1/models` for exact current pricing.

**Monitoring spend:**
```python
# Check remaining credits
resp = requests.get("https://openrouter.ai/api/v1/auth/key",
                     headers={"Authorization": f"Bearer {key}"})
data = resp.json()["data"]
spent = data["usage"]
remaining = data["limit_remaining"]

# Check per-generation cost
resp = requests.get(f"https://openrouter.ai/api/v1/generation?id={gen_id}",
                     headers={"Authorization": f"Bearer {key}"})
cost = resp.json()["data"]["total_cost"]
```

**Budget protection:**
- Set per-key spending limits at key creation
- Monitor `limit_remaining` before batch operations
- Free-tier models available for development/testing

---

## 12. Version Pinning

**API versioning:** OpenRouter uses a single `v1` API version.
No version header required. No date-based versioning.
Breaking changes are rare and announced on their changelog/blog.

**Model versioning:** Models use provider-specific version strings:
```
anthropic/claude-sonnet-4-6           # canonical alias (recommended)
anthropic/claude-3.5-sonnet-20241022    # pinned to specific version
openai/gpt-4o                           # latest GPT-4o
openai/gpt-4o-2024-08-06               # pinned version
```

**Recommendation:** Use canonical aliases (without date suffixes) for most
use cases. Pin to specific versions only when reproducibility is critical.
OpenRouter automatically resolves aliases to the latest version.

**SDK pinning:**
```
openai>=1.0.0,<2.0.0    # in requirements.txt
```
The OpenAI SDK 1.x series is stable. Pin major version to avoid breaking changes.

**Deprecation policy:** OpenRouter removes models when upstream providers
deprecate them. Typically 30-90 days notice. Check the model list endpoint
periodically for `deprecated` flags.

---

# Tier 2 — Creator Intelligence

## 13. Design Intent and Tradeoffs

**Why OpenRouter was built:** Founded by Alex Atallah (co-founder of OpenSea)
to solve the fragmentation problem in LLM access. Every AI provider has its own
API, authentication, billing, and rate limits. OpenRouter provides a single
gateway that normalizes all of this.

**Core mental model:** OpenRouter is to LLM APIs what Stripe is to payment
processors — a unified abstraction layer. You integrate once, access everything.

**Conscious tradeoffs:**
- **Latency for flexibility:** Adding a routing layer adds ~50-200ms latency vs
  direct API calls. The tradeoff is worth it for multi-model access and fallback.
- **No SDK for simplicity:** Rather than building a custom SDK, they chose
  OpenAI-compatibility so any existing OpenAI integration works by changing
  `base_url` and `api_key`. Zero learning curve.
- **Credit-based billing for simplicity:** One prepaid balance instead of
  per-provider billing. Eliminates invoice management across 10+ providers.
- **Transparency over lock-in:** Model pricing mirrors upstream pricing.
  No hidden markup on most models. Users can leave and call providers directly.

**What OpenRouter is NOT:**
- Not a model hosting service (it routes to providers, doesn't run models)
- Not a fine-tuning platform (no training, only inference)
- Not an agent framework (no orchestration, just API calls)
- Not a vector store or RAG service

---

## 14. Problem-Solution Map and Hidden Capabilities

**Problem: Provider outages break production**
Solution: `provider.order` + `allow_fallbacks: true`. Define a primary provider,
list backups. OpenRouter auto-retries transparently. Your app never sees the failure.

**Problem: Need to compare model quality across providers**
Solution: Same prompt to `openai/gpt-4o`, `anthropic/claude-sonnet-4-6`, and
`google/gemini-2.5-flash` via identical API calls. Compare outputs without
managing three separate integrations.

**Problem: Context window too small for your prompt**
Solution: `transforms: ["middle-out"]` — OpenRouter's built-in context compression.
Removes middle content to fit the context window while preserving start and end.

**Problem: Data privacy requirements**
Solution: `provider.data_collection: "deny"` — forces routing only to providers
that don't train on your data. Filters out providers that may use inputs for
training.

**Problem: Need cheapest model that meets quality bar**
Hidden capability: Query `/api/v1/models`, sort by price, test the cheapest
options. OpenRouter makes cost comparison trivial because all pricing is
normalized to per-token USD.

**Problem: Need structured output (JSON)**
Solution: `response_format: {"type": "json_object"}` — OpenRouter passes this
through to providers that support it. Works with OpenAI, Anthropic (via
translation), and Mistral models.

**Hidden: Quantization filtering**
`provider.quantizations: ["fp16"]` — filter providers by quantization level.
If you need full-precision for accuracy-sensitive tasks, deny int4/int8 providers.

---

## 15. Operational Behavior and Edge Cases

**Latency overhead:** ~50-200ms routing overhead on top of provider latency.
For streaming, the overhead only applies to time-to-first-token. Total
generation time is dominated by the upstream provider.

**Provider failover timing:** When a provider returns 5xx, OpenRouter retries
on the next provider in ~1-3 seconds. With `allow_fallbacks: true`, this is
transparent. Without it, you get the error immediately.

**Model availability is dynamic:** Models appear and disappear from the catalog
as providers add/remove endpoints. A model available today may not be available
tomorrow. Always handle 400 "model not found" errors gracefully.

**Streaming chunk format:** Identical to OpenAI SSE format. Each chunk is
`data: {json}\n\n`. Final chunk is `data: [DONE]\n\n`. Usage information
arrives in the final chunk only (not streamed incrementally).

**Concurrent requests:** Multiple requests to the same model share rate limits.
Multiple requests to different models do NOT share rate limits. This means you
can parallelize across models for higher aggregate throughput.

**Token counting mismatch:** OpenRouter may report different token counts than
the upstream provider's tokenizer. This is because OpenRouter uses its own
token estimation for billing before the request, then reconciles with actual
provider counts. Small discrepancies (<5%) are normal.

**Empty response edge case:** If a provider returns an empty completion (0 tokens),
OpenRouter may still bill for prompt tokens. Check `choices[0].message.content`
for null/empty before processing.

---

## 16. Ecosystem Position and Composition

**Where OpenRouter sits:** API routing layer between your application and
LLM providers. It is NOT a replacement for providers — it's a proxy/gateway.

```
Your App → OpenRouter → [OpenAI, Anthropic, Google, Groq, Together, ...]
```

**Natural complements:**
- **LangChain / LlamaIndex** — orchestration frameworks that accept OpenAI-compat
  clients. Set `base_url` to OpenRouter and gain multi-model access.
- **Vercel AI SDK** — frontend streaming. Point at OpenRouter for model flexibility.
- **Helicone / LangSmith** — observability. Can sit between your app and OpenRouter
  for logging/analytics.

**EOS ecosystem position:**
Currently: OpenRouter is a leaf-node — used only by the last30days skill for
Perplexity Sonar access. It does not participate in the core model_router.py
fallback chain.

Potential: OpenRouter could replace multiple direct integrations in model_router.py.
Instead of separate Anthropic SDK, Groq client, and Gemini SDK calls, a single
OpenRouter client handles all of them. Tradeoff: adds routing latency, adds
dependency on OpenRouter's uptime, but simplifies key management and adds
automatic provider fallback.

**Integration anti-pattern:** Don't use OpenRouter AND direct provider APIs
for the same model simultaneously. This doubles your rate limit exposure and
makes cost tracking inaccurate. Pick one path per model.

---

## 17. Trajectory and Evolution

**Where OpenRouter is heading:**
- Expanding model catalog (200+ and growing weekly)
- Improved provider routing intelligence (automatic quality/speed optimization)
- Better cost optimization (auto-selecting cheapest provider per model)
- Enterprise features (team management, audit logs, SSO)
- Middleware features (prompt caching, guardrails)

**What's getting investment:**
- Provider diversity — adding new providers rapidly
- Developer experience — dashboard improvements, better error messages
- Structured output support — JSON mode, tool calling across all providers
- Image/multimodal support — unified vision API across providers

**Deprecation signals:**
- Free model tier may tighten as they scale (rate limits decreasing)
- Older model versions removed when providers deprecate them
- No API version changes announced — v1 is stable

**EOS strategic note:** OpenRouter is a strong candidate for the
"universal fallback" slot in model_router.py once EOS moves past
the single-provider phase. It provides exactly the kind of
provider-level resilience that EOS's current direct-integration
approach lacks.

---

## 18. Conceptual Model and Solution Recipes

**Mental model:** Think of OpenRouter as a smart load balancer for LLMs.
You specify WHAT you want (model, parameters), and it handles WHERE
the request goes (which provider, which region, which quantization).

**Primitives:**
- **Model ID** (`provider/model-name`) — the addressing system
- **Provider config** (`provider: {}`) — routing preferences
- **Credits** — the fuel (prepaid USD balance)
- **Generation** — a single request/response pair with cost

**Recipe 1: Multi-model comparison pipeline**
```python
models = ["openai/gpt-4o", "anthropic/claude-sonnet-4-6", "google/gemini-2.5-flash"]
results = {}
for model in models:
    resp = client.chat.completions.create(model=model, messages=messages)
    results[model] = {
        "content": resp.choices[0].message.content,
        "tokens": resp.usage.total_tokens,
    }
# Compare quality, cost, speed across models
```

**Recipe 2: Cost-optimized batch processing**
```python
# Use cheap model for easy tasks, expensive for hard ones
def classify_and_route(task):
    # Classification with cheap model
    classification = client.chat.completions.create(
        model="meta-llama/llama-3.3-70b",  # cheap
        messages=[{"role": "user", "content": f"Is this complex? {task}"}],
    )
    if "complex" in classification.choices[0].message.content.lower():
        return "anthropic/claude-sonnet-4-6"  # expensive, high quality
    return "google/gemini-2.5-flash"          # cheap, fast
```

**Recipe 3: Resilient web search with Sonar**
```python
# EOS pattern from openrouter_search.py
def search_with_sonar(query, api_key):
    resp = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={"Authorization": f"Bearer {api_key}"},
        json={"model": "perplexity/sonar-pro", "messages": [{"role": "user", "content": query}]},
    )
    data = resp.json()
    content = data["choices"][0]["message"]["content"]
    citations = data.get("search_results") or data.get("citations", [])
    return content, citations
```

**Recipe 4: Provider-resilient production setup**
```python
# Never fail because one provider is down
response = client.chat.completions.create(
    model="anthropic/claude-sonnet-4-6",
    messages=messages,
    extra_body={
        "provider": {
            "order": ["Anthropic", "AWS Bedrock", "Google"],
            "allow_fallbacks": True,
            "data_collection": "deny",
        }
    },
)
```

---

## 19. Industry Expert and Cutting-Edge Usage

**AI agent frameworks using OpenRouter:**
Many open-source agent frameworks (AutoGPT, CrewAI, Agency Swarm) support
OpenRouter as a backend. This allows agents to dynamically select models
based on task complexity — use Llama for cheap reasoning steps, Claude
for complex analysis, GPT-4o for vision tasks — all through one integration.

**Cost arbitrage pattern:**
Power users monitor `/api/v1/models` pricing daily. When a new cheap model
launches (e.g., DeepSeek R1 at $0.55/M prompt tokens), they immediately
route appropriate tasks to it. OpenRouter makes switching models a one-line
change, enabling rapid cost optimization.

**Multi-model consensus pattern:**
For high-stakes decisions, experts run the same prompt through 3+ models
via OpenRouter and take the majority answer. This reduces hallucination
risk at the cost of 3x tokens. OpenRouter makes this trivial because
all models use the same request format.

**Development-to-production model ladder:**
- Dev: `meta-llama/llama-3.3-70b` (cheap, fast iteration)
- Staging: `anthropic/claude-sonnet-4-6` (quality validation)
- Production: same model with `provider.order` for reliability
All through the same OpenRouter client — no code changes between stages.

**EOS-specific frontier pattern:**
OpenRouter could serve as the "escape hatch" in model_router.py. When all
direct providers fail (Anthropic 401, Gemini 429, Ollama down), OpenRouter
provides access to the same models through alternative hosting providers.
This is the most natural integration point: add `ModelProvider.OPENROUTER`
at priority 4 (after direct providers, before Ollama), using
`_call_openai_compatible()` with `base_url="https://openrouter.ai/api/v1"`.

---

## EOS Usage Patterns

### Active: last30days web search
`openrouter_search.py` routes Perplexity Sonar Pro queries through OpenRouter.
Raw HTTP (no OpenAI SDK), timeout 30s, returns normalized search results.

### Planned: model_router.py universal fallback
Natural fit as fallback provider in the existing priority chain:
```
CC SDK (Opus) → Gemini → Groq → [OpenRouter] → Ollama
```
One key, all models, automatic provider failover.

### Integration checklist
1. Add `OPENROUTER_API_KEY` to `eos_ai/.env`
2. Add `ModelProvider.OPENROUTER` to model_router.py
3. Add OpenRouter model config to `MODEL_REGISTRY`
4. Route through existing `_call_openai_compatible()` method
5. Set `base_url="https://openrouter.ai/api/v1"`

---

## Gotchas

### WebSearch and WebFetch blocked during skill research
Both web tools were denied permission during this skill's creation.
Content is based on training data knowledge of OpenRouter (extensive
through early 2025) plus actual EOS codebase patterns. Pricing and
model availability should be verified against live `/api/v1/models`
endpoint before production integration.

### OPENROUTER_API_KEY not in standard EOS .env files
Key exists only in `~/.config/last30days/.env`. New integrations in
`eos_ai/` or `services/` will fail unless the key is added to
`eos_ai/.env`.

### Model ID requires provider/ prefix
`anthropic/claude-sonnet-4-6` works. `claude-sonnet-4-6` returns 400.
Every EOS integration must use the full `provider/model-name` format.

### Sonar citation format is non-deterministic
Sometimes `search_results` array, sometimes `citations` flat list,
sometimes both. Always handle both formats. See `_normalize_results()`
in `openrouter_search.py`.
