---
name: openai
description: "Use when making GPT chat completions, embeddings, function calling, or streaming calls via the OpenAI Python SDK, or when integrating any OpenAI-compatible API (Perplexity, Groq, Together, etc.)."
allowed-tools: "Read, Bash"
version: 1.0
source_url: "https://platform.openai.com/docs"
last_researched: "2026-04-06"
instantiated_from: templates/tools/_template/
api_version: "v1"
sdk_version: "openai >=1.0 (v1 rewrite)"
speed_category: medium
trigger: both
effort: medium
context: fork
---

# Tool: OpenAI (Python SDK)

## What This Tool Does

The OpenAI API provides access to GPT-series language models (GPT-4o, GPT-4o-mini,
o1, o3, GPT-4.1), embedding models (text-embedding-3-small, text-embedding-3-large),
image generation (DALL-E 3), speech (Whisper, TTS), and the Responses API (web search,
code interpreter, file search). The Python SDK (`openai` package v1+) is the official
client library.

Core capabilities used by EOS:
- **Chat Completions** — primary interface for text generation, reasoning, analysis
- **OpenAI-compatible routing** — SDK used as universal client for Perplexity, Groq,
  and any provider that exposes an OpenAI-compatible `/v1/chat/completions` endpoint
- **Function calling / tool use** — structured output extraction, agent tool dispatch
- **Structured Outputs** — JSON schema-enforced responses via `response_format`
- **Embeddings** — text-embedding-3-small/large for semantic search
- **Responses API** — web search tool (used by last30days skill for Reddit discovery)
- **Streaming** — token-by-token delivery for real-time UX
- **Whisper** — speech-to-text (voice_engine.py references as fallback)

## EOS Integration

### OpenAI-compatible client in model_router.py
`eos_ai/model_router.py` — `_call_openai_compatible()` is the universal method that
handles Perplexity, Groq, and any OpenAI-compatible API. It imports `from openai import OpenAI`
and creates a client with a custom `base_url`.

```python
# model_router.py line 535
client = OpenAI(
    api_key=os.getenv(config.api_key_env),
    base_url=config.base_url or None,
)
messages = []
if system:
    messages.append({"role": "system", "content": system})
messages.append({"role": "user", "content": prompt})
response = client.chat.completions.create(
    model=config.model_id,
    messages=messages,
    max_tokens=max_tokens,
)
return response.choices[0].message.content or ""
```

### Providers routed through OpenAI SDK
- **Perplexity** (`perplexity-sonar`) — `base_url="https://api.perplexity.ai"`, model `llama-3.1-sonar-large-128k-online`
- **Groq** (`groq-llama`) — `base_url="https://api.groq.com/openai/v1"`, model `llama-3.3-70b-versatile`
- **OpenAI direct** — `ModelProvider.OPENAI` is registered in the provider enum but
  not currently in `MODEL_REGISTRY` as a standalone entry. Uses `OPENAI_API_KEY` from `services/.env`.

### Responses API usage (last30days skill)
`.agents/skills/last30days/scripts/lib/openai_reddit.py` uses the OpenAI Responses API
(`/v1/responses`) directly via HTTP POST (not the SDK) for Reddit discovery with web search tool.
Model fallback: `gpt-4.1` -> `gpt-4o`. Posts to `https://api.openai.com/v1/responses`.

### Voice engine fallback
`eos_ai/voice_engine.py` — references OpenAI Whisper as STT fallback after faster-whisper.

### Provider priority
OpenAI is not currently in the active fallback chain. The chain is:
CC SDK (Opus) -> Gemini -> Groq -> Anthropic -> Perplexity -> Ollama.
However, the OpenAI SDK is the transport layer for Perplexity and Groq calls.

## Authentication

### API key auth
1. Get API key from https://platform.openai.com/api-keys
2. Store as `OPENAI_API_KEY` in `services/.env`
3. Also referenced in `.env.example` as optional
4. Never commit keys. Never log keys.

### Env vars
```
OPENAI_API_KEY=          # API key from platform.openai.com (services/.env)
```

### Organization / Project scoping
```python
client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
    organization="org-xxx",    # optional — scopes to org
    project="proj-xxx",        # optional — scopes to project
)
```

Keys starting with `sk-proj-` are project-scoped keys (EOS uses this format).
Organization-level keys start with `sk-org-`. Legacy keys start with `sk-`.

## Quick Reference

### Chat completion (non-streaming)
```python
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
response = client.chat.completions.create(
    model="gpt-4o",
    messages=[
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Analyze this signal."},
    ],
    max_tokens=1024,
    temperature=0.7,
)
print(response.choices[0].message.content)
# Token usage: response.usage.prompt_tokens, response.usage.completion_tokens
```

### Chat completion (streaming)
```python
stream = client.chat.completions.create(
    model="gpt-4o",
    messages=[{"role": "user", "content": "Hello"}],
    stream=True,
)
for chunk in stream:
    delta = chunk.choices[0].delta
    if delta.content:
        print(delta.content, end="", flush=True)
```

### Function calling / tool use
```python
tools = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Get current weather for a location",
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {"type": "string", "description": "City name"},
                    "unit": {"type": "string", "enum": ["celsius", "fahrenheit"]},
                },
                "required": ["location"],
            },
        },
    }
]
response = client.chat.completions.create(
    model="gpt-4o",
    messages=[{"role": "user", "content": "What's the weather in Portland?"}],
    tools=tools,
    tool_choice="auto",  # "auto" | "none" | "required" | {"type": "function", "function": {"name": "get_weather"}}
)
# Check if model wants to call a tool
msg = response.choices[0].message
if msg.tool_calls:
    for tc in msg.tool_calls:
        print(tc.function.name, tc.function.arguments)  # arguments is JSON string
```

### Structured Outputs (JSON schema enforcement)
```python
from pydantic import BaseModel

class LeadScore(BaseModel):
    score: int
    reasoning: str
    next_action: str

response = client.beta.chat.completions.parse(
    model="gpt-4o",
    messages=[{"role": "user", "content": "Score this lead..."}],
    response_format=LeadScore,
)
lead = response.choices[0].message.parsed  # LeadScore instance
```

### Embeddings
```python
response = client.embeddings.create(
    model="text-embedding-3-small",  # or text-embedding-3-large
    input="Search query text",
    dimensions=1536,  # optional — reduce dimensions for cost savings
)
vector = response.data[0].embedding  # list[float]
# Batch: pass list of strings as input for up to 2048 items
```

### OpenAI-compatible provider (EOS pattern)
```python
# Groq, Perplexity, Together, etc.
client = OpenAI(
    api_key=os.getenv("GROQ_API_KEY"),
    base_url="https://api.groq.com/openai/v1",
)
# Same chat.completions.create() interface
```

### Async client
```python
from openai import AsyncOpenAI

client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
response = await client.chat.completions.create(
    model="gpt-4o",
    messages=[{"role": "user", "content": "Hello"}],
)
```

## Conceptual Model

```
OpenAI API v1
  |
  +-- Chat Completions (/v1/chat/completions)
  |     |-- Messages array (system, user, assistant, tool)
  |     |-- Tools/Functions — structured tool calling
  |     |-- Structured Outputs — JSON schema enforcement
  |     |-- Streaming — Server-Sent Events
  |     |-- Vision — image URLs in user messages
  |     +-- Logprobs — token-level confidence
  |
  +-- Responses API (/v1/responses) — newer agentic interface
  |     |-- Built-in tools: web_search, code_interpreter, file_search
  |     |-- Multi-turn with previous_response_id
  |     +-- Used by last30days for Reddit discovery
  |
  +-- Embeddings (/v1/embeddings)
  |     |-- text-embedding-3-small (1536 dims, cheap)
  |     +-- text-embedding-3-large (3072 dims, better)
  |
  +-- Audio (/v1/audio)
  |     |-- Whisper STT (transcriptions, translations)
  |     +-- TTS (tts-1, tts-1-hd — 6 voices)
  |
  +-- Images (/v1/images)
  |     +-- DALL-E 3 generation and editing
  |
  +-- OpenAI SDK (Python client layer)
        |-- OpenAI() — sync client
        |-- AsyncOpenAI() — async client
        |-- base_url override — any compatible API
        |-- Automatic retries (2x by default)
        |-- Pydantic response models
        +-- httpx under the hood
```

See references/best_practices.md for rate limits, error codes, and anti-patterns.

## Gotchas

### OpenAI SDK not installed on VPS
The `openai` Python package is not installed system-wide on the EOS VPS. It IS available
inside Docker containers. The `_call_openai_compatible()` method in model_router.py
wraps the import in a try/except ImportError and returns empty string if unavailable.
Install with `pip install openai` if needed outside Docker.

### Responses API vs Chat Completions API
The Responses API (`/v1/responses`) is a newer endpoint with built-in tools (web_search,
code_interpreter). The last30days skill uses it directly via HTTP, not the SDK. Do not
confuse with chat completions. The Responses API has different request/response shapes.

### gpt-4o-mini does not support web_search with filters
The last30days skill explicitly excludes gpt-4o-mini from its fallback chain because
it does not support the `web_search` tool with filter parameters. Model fallback order
for web search: `gpt-4.1` -> `gpt-4o`.

### Project-scoped keys (sk-proj-) have limited permissions
EOS uses a `sk-proj-` key which is scoped to a specific project. These keys cannot
access organization-level endpoints (usage dashboard, fine-tuning across projects).
If you get a 403 on an endpoint that should work, check if the key has the required
project permissions.

### max_tokens vs max_completion_tokens
For o1/o3 reasoning models, use `max_completion_tokens` instead of `max_tokens`.
Chat models (GPT-4o, GPT-4o-mini) use `max_tokens`. Passing the wrong parameter
silently has no effect or errors depending on the model.

### OpenAI-compatible providers may not support all parameters
When using `base_url` to route to Groq/Perplexity/Together, not all OpenAI parameters
are supported. Groq ignores `logprobs`, Perplexity ignores `tools`. Always check the
provider's compatibility docs.

### Token counting for usage tracking
`response.usage.prompt_tokens` and `response.usage.completion_tokens` — EOS model_router
reads these in `_call_openai_compatible()` (lines 549-550). Some providers return None
for usage — the code guards with `or 0`.
