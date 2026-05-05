---
name: openrouter
description: "Use when routing LLM calls through a unified multi-model API, selecting models by cost/speed/capability, accessing 200+ models from OpenAI/Anthropic/Google/Meta/Mistral via a single OpenAI-compatible endpoint, or implementing provider-level fallback routing."
allowed-tools: "Read, Bash"
version: 1.0
source_url: "https://openrouter.ai/docs/quickstart"
last_researched: "2026-04-06"
instantiated_from: templates/tools/_template/
api_version: "v1"
sdk_version: "openai 1.x (compatible)"
speed_category: medium
trigger: both
effort: medium
context: fork
---

# Tool: OpenRouter

## What This Tool Does

OpenRouter is a unified API gateway that provides access to 200+ LLM models from
multiple providers (OpenAI, Anthropic, Google, Meta, Mistral, Perplexity, Cohere,
and more) through a single OpenAI-compatible endpoint. Instead of managing separate
API keys and SDKs for each provider, you send all requests to
`https://openrouter.ai/api/v1/chat/completions` with a single API key.

Core capabilities used by EOS:
- **Multi-model access** — single endpoint for GPT-4o, Claude, Gemini, Llama,
  Mistral, Sonar, DeepSeek, Command R+, and 200+ other models via
  `provider/model-name` format (e.g., `perplexity/sonar-pro`,
  `anthropic/claude-sonnet-4-6`, `openai/gpt-4o`).
- **Provider routing** — automatic fallback across providers that host the same
  model. If one provider is down, OpenRouter routes to another. Configurable
  via `provider.order`, `provider.allow`, and `provider.deny` in the request body.
- **Cost normalization** — pay-per-token pricing aggregated across all providers.
  Credits purchased in advance, no per-provider billing. Model pricing visible
  at `https://openrouter.ai/models`.
- **Web-grounded search** — access to Perplexity Sonar models which include
  built-in web search with citations, used by EOS last30days skill.
- **Streaming** — SSE streaming support identical to OpenAI's format.
- **Usage tracking** — per-request cost and token usage in response headers
  and the `/api/v1/auth/key` info endpoint.

## EOS Integration

### last30days research skill (active usage)
`.agents/skills/last30days/scripts/lib/openrouter_search.py` — the primary
production integration. Routes web search queries through Perplexity Sonar Pro
on OpenRouter for the last30days research skill:
```python
ENDPOINT = "https://openrouter.ai/api/v1/chat/completions"
MODEL = "perplexity/sonar-pro"

payload = {
    "model": MODEL,
    "messages": [{"role": "user", "content": prompt}],
    "max_tokens": max_tokens,
}
response = http.post(
    ENDPOINT,
    json_data=payload,
    headers={
        "Authorization": f"Bearer {api_key}",
        "HTTP-Referer": "https://github.com/mvanhorn/last30days-openclaw",
        "X-Title": "last30days",
    },
    timeout=30,
)
```
Returns `search_results` (title, url, date) and `citations` (flat URL list).
Normalizes both formats via `_normalize_results()`.

### Web search backend priority
`.agents/skills/last30days/scripts/lib/env.py` — OpenRouter is the third-priority
web search backend: `Parallel AI > Brave > OpenRouter/Sonar Pro`.
Selected when `OPENROUTER_API_KEY` is set and higher-priority keys are absent.

### Model Router (potential integration point)
`eos_ai/model_router.py` — does NOT currently route through OpenRouter.
It calls providers directly (Anthropic SDK, Gemini SDK, Groq via OpenAI-compat,
Ollama HTTP). OpenRouter could replace `_call_openai_compatible()` as a
universal fallback with automatic provider rotation. The `ModelProvider` enum
does not yet include `OPENROUTER`.

### Future integration opportunity
OpenRouter would be the natural addition to model_router.py's fallback chain:
- Single API key replaces per-provider key management
- Automatic provider failover (if Anthropic is down, OpenRouter retries via
  another host)
- Access to models not in current registry (DeepSeek, Command R+, Qwen)
- Credit-based billing simplifies cost tracking

## Authentication

### API key auth
1. Create account at https://openrouter.ai
2. Go to https://openrouter.ai/keys -> Create Key
3. Store as `OPENROUTER_API_KEY` in the appropriate .env file
4. Never commit keys. Never log keys.

### Required headers
```
Authorization: Bearer {OPENROUTER_API_KEY}
```

### Recommended headers
```
HTTP-Referer: {your_site_url}     # For rankings on openrouter.ai
X-Title: {your_app_name}          # Shows in OpenRouter dashboard
Content-Type: application/json
```

### Env vars
```
OPENROUTER_API_KEY=    # API key from openrouter.ai/keys
```

**Current state:** `OPENROUTER_API_KEY` is NOT in `eos_ai/.env` or `services/.env`.
It is expected in `~/.config/last30days/.env` or passed via environment for the
last30days skill. To add OpenRouter to model_router.py, add the key to `eos_ai/.env`.

## Quick Reference

### Chat completion (basic)
```python
from openai import OpenAI

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY"),
)
response = client.chat.completions.create(
    model="anthropic/claude-sonnet-4-6",
    messages=[{"role": "user", "content": "Hello"}],
    max_tokens=1000,
)
print(response.choices[0].message.content)
```

### Chat completion (raw HTTP, EOS pattern)
```python
import requests

response = requests.post(
    "https://openrouter.ai/api/v1/chat/completions",
    headers={
        "Authorization": f"Bearer {api_key}",
        "HTTP-Referer": "https://yoursite.com",
        "X-Title": "your-app",
    },
    json={
        "model": "perplexity/sonar-pro",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 2048,
    },
    timeout=30,
)
data = response.json()
content = data["choices"][0]["message"]["content"]
```

### Model selection by provider
```python
# Format: provider/model-name
"openai/gpt-4o"                  # GPT-4o via OpenAI
"anthropic/claude-sonnet-4-6"  # Claude 3.5 Sonnet
"google/gemini-2.5-flash"       # Gemini 2.5 Flash
"meta-llama/llama-3.3-70b"      # Llama 3.3 70B
"perplexity/sonar-pro"           # Sonar Pro (web search)
"deepseek/deepseek-r1"          # DeepSeek R1 (reasoning)
"mistralai/mistral-large"       # Mistral Large
```

### Provider routing (fallback control)
```python
response = client.chat.completions.create(
    model="anthropic/claude-sonnet-4-6",
    messages=[{"role": "user", "content": prompt}],
    extra_body={
        "provider": {
            "order": ["Anthropic", "Google"],  # Try Anthropic first, Google second
            "allow_fallbacks": True,            # Allow other providers if both fail
        }
    },
)
```

### Streaming
```python
stream = client.chat.completions.create(
    model="openai/gpt-4o",
    messages=[{"role": "user", "content": prompt}],
    stream=True,
)
for chunk in stream:
    if chunk.choices[0].delta.content:
        print(chunk.choices[0].delta.content, end="")
```

### Check remaining credits
```python
resp = requests.get(
    "https://openrouter.ai/api/v1/auth/key",
    headers={"Authorization": f"Bearer {api_key}"},
)
data = resp.json()["data"]
print(f"Credits remaining: ${data['limit_remaining']:.4f}")
print(f"Label: {data['label']}")
```

## Conceptual Model

```
OpenRouter API Gateway
  |
  +-- /api/v1/chat/completions  --- OpenAI-compatible chat
  |     |-- model: "provider/model-name" selects target
  |     |-- provider.order: explicit fallback chain
  |     |-- provider.allow/deny: whitelist/blacklist providers
  |     |-- transforms: ["middle-out"] for context compression
  |     +-- Streaming via SSE (same as OpenAI format)
  |
  +-- /api/v1/models  --- list all available models + pricing
  |
  +-- /api/v1/auth/key  --- check credits and key info
  |
  +-- /api/v1/generation  --- get generation details by ID
  |
  +-- Provider Routing Layer
        |-- Automatic: routes to cheapest/fastest available provider
        |-- Manual: provider.order sets explicit preference
        |-- Fallback: allow_fallbacks=True enables auto-retry
        +-- Data policy: provider.data_collection="deny" for privacy
```

See references/best_practices.md for rate limits, error codes, pricing, and anti-patterns.

## Gotchas

### OPENROUTER_API_KEY not in EOS .env files
The key currently lives only in the last30days skill config
(`~/.config/last30days/.env`), not in `eos_ai/.env` or `services/.env`.
Any new integration in model_router.py or agent_runtime.py will fail silently
if you assume the key is loaded via `load_dotenv()` from the standard EOS env files.

### Model ID format requires provider prefix
OpenRouter model IDs use `provider/model-name` format (e.g., `anthropic/claude-sonnet-4-6`).
Using bare model names like `claude-sonnet-4-6` will return a 400 error.
This is different from direct Anthropic/OpenAI SDKs where you use bare names.

### Sonar Pro response format varies
Perplexity models on OpenRouter return citations in two possible formats:
`search_results` (array of objects with title/url/date) OR `citations` (flat
array of URLs). You must handle both. See `openrouter_search.py`
`_normalize_results()` for the dual-format handling pattern.

### Credit-based billing, not subscription
OpenRouter uses prepaid credits, not monthly subscription. When credits hit zero,
all requests return 402 Payment Required. There is no grace period. Monitor via
`/api/v1/auth/key` endpoint before critical runs.

### Rate limits are per-model, not per-account
Different models have different rate limits set by their upstream providers.
A 429 on `openai/gpt-4o` does not mean `anthropic/claude-sonnet-4-6` is also
rate-limited. The `Retry-After` header indicates wait time.

### HTTP-Referer header affects rankings
OpenRouter uses `HTTP-Referer` and `X-Title` to attribute usage for their
leaderboard. Not strictly required, but omitting them may affect rate limits
for free-tier models. Always include them.
