# OpenAI — Creator-Level Best Practices
Source: https://platform.openai.com/docs
API Version: v1
SDK Version: openai >=1.0 (v1 rewrite, httpx-based)
Last Researched: 2026-04-06

---

# Tier 1 — Technical Mastery

## Authentication

**Auth method:** Bearer token via API key.

**Key types:**
- `sk-proj-...` — Project-scoped key. Limited to one project's resources. EOS uses this format.
- `sk-org-...` — Organization-scoped key. Access to all projects within an org.
- `sk-...` (legacy) — User-level key. Deprecated for new keys but still functional.

**Where secrets live in EOS:**
- `services/.env` — `OPENAI_API_KEY` (primary)
- `.env.example` — documents the variable as optional

**Token lifetime:** API keys do not expire. Revocation is manual via dashboard.
No refresh flow — keys are static until rotated.

**Scopes/permissions:** Project-scoped keys inherit the project's allowed models
and rate limits. Organization keys inherit org-level limits. Fine-grained permissions
(read-only, write, admin) are set per key in the dashboard.

**Multi-tenant:** Each organization has its own rate limits and billing. Projects
within an organization can have separate keys with different model access.

**SDK initialization:**
```python
from openai import OpenAI

# Minimal — reads OPENAI_API_KEY from env automatically
client = OpenAI()

# Explicit — EOS pattern in model_router.py
client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
    base_url=config.base_url or None,  # override for Groq, Perplexity, etc.
)

# With org/project scoping
client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
    organization="org-xxx",
    project="proj-xxx",
)
```

---

## Core Operations with Exact Signatures

### Chat Completions
```python
client.chat.completions.create(
    model: str,                          # required — "gpt-4o", "gpt-4o-mini", "o1", "o3", "gpt-4.1"
    messages: list[dict],                # required — [{"role": "system"|"user"|"assistant"|"tool", "content": str}]
    max_tokens: int | None = None,       # optional — max output tokens (use max_completion_tokens for o1/o3)
    temperature: float = 1.0,            # optional — 0.0-2.0, lower = more deterministic
    top_p: float = 1.0,                  # optional — nucleus sampling, alternative to temperature
    n: int = 1,                          # optional — number of completions to generate
    stream: bool = False,                # optional — enable streaming
    stop: str | list[str] | None = None, # optional — stop sequences
    presence_penalty: float = 0.0,       # optional — -2.0 to 2.0
    frequency_penalty: float = 0.0,      # optional — -2.0 to 2.0
    tools: list[dict] | None = None,     # optional — function calling tools
    tool_choice: str | dict = "auto",    # optional — "auto" | "none" | "required" | specific function
    response_format: dict | type = None, # optional — {"type": "json_object"} or Pydantic model for structured
    seed: int | None = None,             # optional — deterministic sampling (best effort)
    logprobs: bool = False,              # optional — return log probabilities
    user: str | None = None,             # optional — end-user ID for abuse monitoring
)
# Returns: ChatCompletion
#   .id: str
#   .choices: list[Choice]
#     .choices[0].message.content: str | None
#     .choices[0].message.tool_calls: list[ToolCall] | None
#     .choices[0].finish_reason: "stop" | "length" | "tool_calls" | "content_filter"
#   .usage: CompletionUsage
#     .prompt_tokens: int
#     .completion_tokens: int
#     .total_tokens: int
#   .model: str
```

### Embeddings
```python
client.embeddings.create(
    model: str,                    # required — "text-embedding-3-small" | "text-embedding-3-large"
    input: str | list[str],        # required — text or batch (up to 2048 items)
    dimensions: int | None = None, # optional — reduce dimensions (e.g., 512 for small)
    encoding_format: str = "float",# optional — "float" | "base64"
    user: str | None = None,       # optional — end-user ID
)
# Returns: CreateEmbeddingResponse
#   .data: list[Embedding]
#     .data[0].embedding: list[float]  — the vector
#     .data[0].index: int
#   .usage: EmbeddingUsage
#     .prompt_tokens: int
#     .total_tokens: int
#   .model: str
```

### Structured Outputs (beta)
```python
client.beta.chat.completions.parse(
    model: str,                    # required — must support structured outputs (gpt-4o, gpt-4o-mini)
    messages: list[dict],          # required — same as chat completions
    response_format: type[BaseModel], # required — Pydantic model class
    # ... all other chat completion params
)
# Returns: ParsedChatCompletion
#   .choices[0].message.parsed: BaseModel instance | None
#   .choices[0].message.refusal: str | None  — if model refused
```

### Audio (Whisper STT)
```python
client.audio.transcriptions.create(
    model: str = "whisper-1",      # required
    file: FileTypes,               # required — audio file (mp3, wav, etc.)
    language: str | None = None,   # optional — ISO 639-1 code
    prompt: str | None = None,     # optional — guide transcription
    response_format: str = "json", # optional — "json" | "text" | "srt" | "vtt" | "verbose_json"
    temperature: float = 0.0,      # optional
)
# Returns: Transcription
#   .text: str
```

### Audio (TTS)
```python
client.audio.speech.create(
    model: str,                    # required — "tts-1" | "tts-1-hd"
    input: str,                    # required — text to speak (max 4096 chars)
    voice: str,                    # required — "alloy"|"echo"|"fable"|"onyx"|"nova"|"shimmer"
    response_format: str = "mp3",  # optional — "mp3"|"opus"|"aac"|"flac"|"wav"|"pcm"
    speed: float = 1.0,            # optional — 0.25-4.0
)
# Returns: HttpxBinaryResponseContent (stream with .stream_to_file())
```

### Images (DALL-E 3)
```python
client.images.generate(
    model: str = "dall-e-3",       # required
    prompt: str,                   # required — image description
    size: str = "1024x1024",       # optional — "1024x1024"|"1792x1024"|"1024x1792"
    quality: str = "standard",     # optional — "standard"|"hd"
    n: int = 1,                    # optional — DALL-E 3 only supports n=1
    response_format: str = "url",  # optional — "url"|"b64_json"
)
# Returns: ImagesResponse
#   .data[0].url: str
#   .data[0].revised_prompt: str
```

---

## Pagination Patterns

Most OpenAI endpoints do not use pagination (chat completions, embeddings return
in a single response). Endpoints that do paginate:

**List models:**
```python
models = client.models.list()
# Returns SyncPage[Model] — auto-paginates
for model in models:
    print(model.id)
```

**List fine-tuning jobs:**
```python
jobs = client.fine_tuning.jobs.list(limit=20, after="ftjob-xxx")
# .has_more: bool
# .data: list[FineTuningJob]
```

**File listing:**
```python
files = client.files.list()
# SyncPage auto-pagination
```

Pattern: OpenAI uses cursor-based pagination with `after` parameter and `has_more`
field. The SDK's `SyncPage` iterator handles auto-pagination transparently.

---

## Rate Limits

Rate limits vary by model, tier, and key type. Limits are per-organization.

**Tier structure (based on spend):**
| Tier | Spend Required | GPT-4o RPM | GPT-4o TPM | GPT-4o-mini RPM | GPT-4o-mini TPM |
|------|---------------|------------|------------|-----------------|-----------------|
| Free | $0 | 3 | 40,000 | 3 | 40,000 |
| Tier 1 | $5+ | 500 | 30,000 | 500 | 200,000 |
| Tier 2 | $50+ | 5,000 | 450,000 | 5,000 | 2,000,000 |
| Tier 3 | $100+ | 5,000 | 800,000 | 5,000 | 4,000,000 |
| Tier 4 | $250+ | 10,000 | 800,000 | 10,000 | 10,000,000 |
| Tier 5 | $1,000+ | 10,000 | 10,000,000 | 10,000 | 15,000,000 |

**Embedding limits (Tier 1+):**
- text-embedding-3-small: 500 RPM, 1,000,000 TPM
- text-embedding-3-large: 500 RPM, 1,000,000 TPM

**Rate limit headers in response:**
```
x-ratelimit-limit-requests: 500
x-ratelimit-limit-tokens: 200000
x-ratelimit-remaining-requests: 499
x-ratelimit-remaining-tokens: 199500
x-ratelimit-reset-requests: 200ms
x-ratelimit-reset-tokens: 1s
```

**When rate limited:** HTTP 429. `Retry-After` header indicates wait time in seconds.
The SDK has built-in retry with exponential backoff (2 retries by default).

**Backoff strategy:** SDK handles automatically. For custom retry:
```python
client = OpenAI(
    max_retries=5,           # default is 2
    timeout=httpx.Timeout(60.0, connect=5.0),
)
```

---

## Error Codes and Recovery

**Error response shape:**
```json
{
  "error": {
    "message": "Human-readable message",
    "type": "error_type",
    "param": "affected_param_or_null",
    "code": "specific_code_or_null"
  }
}
```

**SDK exception hierarchy:**
```
openai.APIError (base)
  |-- openai.APIConnectionError     — network/connection failure (retryable)
  |-- openai.APITimeoutError        — request timed out (retryable)
  |-- openai.APIStatusError (base for HTTP errors)
        |-- openai.BadRequestError       — 400 (not retryable)
        |-- openai.AuthenticationError   — 401 (not retryable — bad key)
        |-- openai.PermissionDeniedError — 403 (not retryable — wrong scope)
        |-- openai.NotFoundError         — 404 (not retryable — bad model/endpoint)
        |-- openai.ConflictError         — 409 (rare)
        |-- openai.UnprocessableEntityError — 422 (schema violation)
        |-- openai.RateLimitError        — 429 (retryable after backoff)
        |-- openai.InternalServerError   — 500+ (retryable)
```

**Key error types and recovery:**

| HTTP | Exception | Cause | Recovery |
|------|-----------|-------|----------|
| 400 | BadRequestError | Invalid params, bad messages format, unsupported param for model | Fix request. Check model supports the parameter. |
| 401 | AuthenticationError | Invalid/expired/missing API key | Check OPENAI_API_KEY. Rotate if compromised. |
| 403 | PermissionDeniedError | Key lacks access to model/endpoint. Org not verified. | Check project permissions. Verify org for advanced models. |
| 404 | NotFoundError | Model doesn't exist, wrong endpoint | Check model name spelling. Check API version. |
| 429 | RateLimitError | Rate limit or quota exceeded | Wait and retry. Check billing. Upgrade tier. |
| 500 | InternalServerError | OpenAI server error | Retry with backoff. Check status.openai.com. |
| 503 | InternalServerError | Service overloaded | Retry with backoff. |

**EOS-specific error handling pattern (model_router.py):**
```python
try:
    from openai import OpenAI
except ImportError:
    return ""  # SDK not available — skip this provider
try:
    client = OpenAI(api_key=..., base_url=...)
    response = client.chat.completions.create(...)
    return response.choices[0].message.content or ""
except Exception as e:
    print(f"[ModelRouter] {config.provider.value} error: {e}")
    return ""  # empty triggers fallback to next provider
```

---

## SDK Idioms

**Package:** `pip install openai` (v1.0+ is the current major version, complete rewrite from v0.x)

**Import patterns:**
```python
from openai import OpenAI          # sync client
from openai import AsyncOpenAI     # async client
from openai import OpenAIError     # base exception (deprecated — use APIError)
from openai import APIError, RateLimitError, AuthenticationError  # specific exceptions
from openai.types.chat import ChatCompletion  # response types
```

**v1 rewrite key changes from v0.x:**
- `openai.ChatCompletion.create()` -> `client.chat.completions.create()`
- Module-level calls replaced with client instance methods
- All responses are Pydantic models (not dicts)
- `response["choices"][0]` -> `response.choices[0]`
- httpx replaces requests under the hood
- Built-in retry and timeout management

**Sync vs Async:**
```python
# Sync (EOS model_router pattern)
client = OpenAI()
result = client.chat.completions.create(...)

# Async (for Discord bot / asyncio contexts)
client = AsyncOpenAI()
result = await client.chat.completions.create(...)
```

**Context manager (connection cleanup):**
```python
with OpenAI() as client:
    response = client.chat.completions.create(...)
# Connection pool closed on exit
```

**Custom httpx client:**
```python
import httpx
client = OpenAI(
    http_client=httpx.Client(proxy="http://proxy:8080"),
)
```

**Auto-retry configuration:**
```python
client = OpenAI(
    max_retries=5,         # default 2, set 0 to disable
    timeout=60.0,          # seconds, default 600s (10 min)
)
```

---

## Anti-Patterns

### 1. Using v0.x syntax with v1+ SDK
```python
# WRONG — v0.x module-level call
import openai
openai.api_key = "sk-..."
response = openai.ChatCompletion.create(model="gpt-4o", messages=[...])

# CORRECT — v1+ client instance
from openai import OpenAI
client = OpenAI(api_key="sk-...")
response = client.chat.completions.create(model="gpt-4o", messages=[...])
```

### 2. Treating responses as dicts instead of Pydantic models
```python
# WRONG — dict access on v1 response
content = response["choices"][0]["message"]["content"]

# CORRECT — attribute access
content = response.choices[0].message.content
```

### 3. Using max_tokens with reasoning models (o1, o3)
```python
# WRONG — max_tokens ignored or errors on o1/o3
response = client.chat.completions.create(model="o1", max_tokens=1000, ...)

# CORRECT — use max_completion_tokens for reasoning models
response = client.chat.completions.create(model="o1", max_completion_tokens=1000, ...)
```

### 4. Not handling tool_calls in the response
```python
# WRONG — assumes content is always present
result = response.choices[0].message.content  # None when tool_calls present!

# CORRECT — check for tool calls first
msg = response.choices[0].message
if msg.tool_calls:
    for tc in msg.tool_calls:
        args = json.loads(tc.function.arguments)
        # execute function, append tool result, call again
elif msg.content:
    result = msg.content
```

### 5. Hardcoding model names without version awareness
```python
# WRONG — model may be deprecated
response = client.chat.completions.create(model="gpt-4-turbo-preview", ...)

# CORRECT — use current stable models
response = client.chat.completions.create(model="gpt-4o", ...)  # latest GPT-4 class
# Or pin to dated version: "gpt-4o-2024-08-06" for reproducibility
```

### 6. Ignoring finish_reason
```python
# WRONG — assuming output is complete
result = response.choices[0].message.content

# CORRECT — check why generation stopped
choice = response.choices[0]
if choice.finish_reason == "length":
    # Output was truncated — increase max_tokens or summarize input
    pass
elif choice.finish_reason == "content_filter":
    # Output was filtered — content policy violation
    pass
```

### 7. Creating a new client per request
```python
# WRONG — creates new connection pool each time
def get_answer(prompt):
    client = OpenAI()  # new httpx connection pool
    return client.chat.completions.create(...)

# CORRECT — reuse client across requests
client = OpenAI()  # module-level or singleton
def get_answer(prompt):
    return client.chat.completions.create(...)
```

---

## Data Model

**Core entities:**

```
ChatCompletion
  |-- id: str (e.g., "chatcmpl-abc123")
  |-- object: "chat.completion"
  |-- created: int (unix timestamp)
  |-- model: str (actual model used, may differ from requested)
  |-- choices: list[Choice]
  |     |-- index: int
  |     |-- message: ChatCompletionMessage
  |     |     |-- role: "assistant"
  |     |     |-- content: str | None
  |     |     |-- tool_calls: list[ToolCall] | None
  |     |     |     |-- id: str
  |     |     |     |-- type: "function"
  |     |     |     +-- function: Function(name, arguments)
  |     |     +-- refusal: str | None
  |     +-- finish_reason: "stop" | "length" | "tool_calls" | "content_filter"
  |-- usage: CompletionUsage
  |     |-- prompt_tokens: int
  |     |-- completion_tokens: int
  |     +-- total_tokens: int
  +-- system_fingerprint: str | None (for reproducibility tracking)

Embedding
  |-- object: "embedding"
  |-- embedding: list[float]
  +-- index: int

Model
  |-- id: str (e.g., "gpt-4o")
  |-- object: "model"
  |-- created: int
  +-- owned_by: str
```

**Message roles:**
- `system` — sets behavior/instructions. One per conversation (first message).
- `user` — human input. Can include text and images (vision).
- `assistant` — model output. Include in messages for multi-turn context.
- `tool` — function call result. Must include `tool_call_id` matching the assistant's request.

**Immutable after creation:** Chat completion IDs, embedding vectors. Cannot update — create new.

---

## Webhooks and Events

**Fine-tuning events:** OpenAI sends fine-tuning job status updates. Poll via
`client.fine_tuning.jobs.retrieve(job_id)` or list events with
`client.fine_tuning.jobs.list_events(job_id)`. No push-based webhooks for fine-tuning.

**Batch API:** Submit batch requests, poll for completion. No webhook notification.
```python
batch = client.batches.create(input_file_id="file-xxx", endpoint="/v1/chat/completions", ...)
# Poll: client.batches.retrieve(batch.id) until status == "completed"
```

**Realtime API (WebSocket):** For voice and real-time applications. Uses WebSocket
connection at `wss://api.openai.com/v1/realtime`. Not used by EOS currently.

N/A for standard push webhooks. OpenAI does not send webhook callbacks to user endpoints.

---

## Limits

| Resource | Limit |
|----------|-------|
| Chat messages array | No hard limit (bounded by context window) |
| Context window — GPT-4o | 128,000 tokens |
| Context window — GPT-4o-mini | 128,000 tokens |
| Context window — o1 | 200,000 tokens |
| Context window — o3 | 200,000 tokens |
| Context window — GPT-4.1 | 1,000,000 tokens |
| Max output — GPT-4o | 16,384 tokens |
| Max output — GPT-4o-mini | 16,384 tokens |
| Max output — o1 | 100,000 tokens |
| Max output — o3 | 100,000 tokens |
| Embedding batch size | 2,048 items per request |
| Embedding input | 8,191 tokens per item |
| TTS input | 4,096 characters |
| Whisper audio | 25 MB file size |
| Image prompt | 4,000 characters |
| DALL-E 3 n | 1 (only 1 image per request) |
| Tool/function definitions | 128 per request |
| System message | No explicit limit (uses context window) |
| Request body | 100 MB |

---

## Cost Model

**Chat completion pricing (per 1M tokens, as of early 2026):**

| Model | Input | Output | Cached Input |
|-------|-------|--------|--------------|
| GPT-4o | $2.50 | $10.00 | $1.25 |
| GPT-4o-mini | $0.15 | $0.60 | $0.075 |
| o1 | $15.00 | $60.00 | $7.50 |
| o3 | $10.00 | $40.00 | $5.00 |
| o3-mini | $1.10 | $4.40 | $0.55 |
| GPT-4.1 | $2.00 | $8.00 | $0.50 |
| GPT-4.1-mini | $0.40 | $1.60 | $0.10 |
| GPT-4.1-nano | $0.10 | $0.40 | $0.025 |

**Embedding pricing:**
| Model | Price per 1M tokens |
|-------|-------------------|
| text-embedding-3-small | $0.02 |
| text-embedding-3-large | $0.13 |

**Other:**
- Whisper: $0.006 per minute
- TTS: $15.00 per 1M characters (tts-1), $30.00 (tts-1-hd)
- DALL-E 3: $0.04 (standard 1024x1024), $0.08 (HD), $0.12 (HD 1792x)
- Image input (vision): token-based, ~85 tokens per tile (512x512)

**Monitoring:** Dashboard at https://platform.openai.com/usage.
Set spending limits and email alerts in org settings.

**EOS cost tracking:** model_router.py tracks `input_tokens` and `output_tokens`
per call via `response.usage.prompt_tokens` and `response.usage.completion_tokens`.

---

## Version Pinning

**API versioning:** OpenAI uses model-based versioning, not API versioning.
All endpoints are at `/v1/`. No API version header.

**Model versioning:**
- Undated aliases point to latest: `gpt-4o` -> latest GPT-4o snapshot
- Dated snapshots are stable: `gpt-4o-2024-08-06` won't change
- Use dated snapshots for reproducibility in production
- Undated aliases for development / always-latest behavior

**SDK versioning:**
- `openai>=1.0` — v1 is the current major. Pin in requirements.txt.
- `pip install openai==1.51.0` for exact pinning
- Breaking changes only in major versions

**Deprecation policy:**
- Model deprecation announced minimum 6 months in advance
- Deprecated models return warnings in response headers before removal
- After removal: 404 NotFoundError
- Check https://platform.openai.com/docs/deprecations for timeline

**Known deprecations (as of 2026):**
- `gpt-4-turbo-preview` -> use `gpt-4o`
- `gpt-3.5-turbo` -> use `gpt-4o-mini`
- `text-embedding-ada-002` -> use `text-embedding-3-small`

---

# Tier 2 — Creator Intelligence

## Design Intent and Tradeoffs

OpenAI's API design philosophy centers on **simplicity of the happy path**.
The chat completions endpoint uses a messages array that maps directly to a
conversation transcript — system sets behavior, user provides input, assistant
provides output. This is intentionally simple to reason about.

**Key tradeoffs:**
- **Stateless over stateful:** Every request contains the full conversation history.
  No server-side session. This trades bandwidth for simplicity and reliability.
- **Messages over templates:** Unlike Anthropic's XML-heavy approach, OpenAI uses
  role-based messages. Simpler to construct, harder to do complex document injection.
- **Model aliases over API versions:** OpenAI chose to version models, not the API
  itself. This means the API shape is stable but model behavior can shift under aliases.
- **Tools over plugins:** After the plugin ecosystem failed (2023), OpenAI pivoted to
  function calling — giving developers raw tool integration instead of a marketplace.
- **Structured Outputs as constraint:** Rather than trusting the model to output JSON,
  structured outputs enforce a JSON schema at the decoding level. This is a philosophical
  shift from "hope it works" to "guarantee it works."

**What OpenAI is NOT:** It is not an agent framework. It provides primitives (completion,
embedding, tool calling) that agent frameworks compose. The Responses API is their first
step toward agentic primitives but it's additive, not a replacement.

---

## Problem-Solution Map and Hidden Capabilities

**Hidden capabilities most users miss:**

1. **Seed parameter for reproducibility:** `seed=42` makes outputs near-deterministic.
   Combined with `system_fingerprint` in response, you can detect when OpenAI's backend
   changes affected your output.

2. **Logprobs for confidence scoring:** `logprobs=True, top_logprobs=5` returns
   token-level probabilities. Use for: classification confidence, detecting hallucination
   (low confidence on factual claims), calibrating when to escalate to a better model.

3. **Parallel tool calls:** When multiple tools are relevant, GPT-4o returns multiple
   `tool_calls` in a single response. Execute them in parallel, return all results,
   get a single synthesis — saves round trips.

4. **Prompt caching:** Repeated prefixes (long system prompts) are automatically cached
   at 50% discount. Structure prompts with static content first, dynamic content last.

5. **Batch API for async workloads:** 50% cost reduction for non-time-sensitive tasks.
   Submit JSONL files, get results within 24 hours. Perfect for bulk scoring, embedding
   generation, content classification.

6. **Vision with detail parameter:** `{"type": "image_url", "image_url": {"url": "...", "detail": "low"}}`.
   `detail: "low"` uses fixed 85 tokens regardless of image size — massive cost saving
   for simple image understanding tasks.

7. **Predicted outputs:** For code editing tasks, pass the expected output in `prediction`
   parameter. OpenAI skips generating tokens that match, reducing latency and cost.

---

## Operational Behavior and Edge Cases

**Eventual consistency on model updates:** When OpenAI updates an undated model alias
(e.g., `gpt-4o`), the rollout is gradual. For hours or days, the same alias may route
to different model versions depending on load balancing. Pin dated snapshots to avoid this.

**Empty content with tool_calls:** When the model decides to call a tool,
`message.content` is `None`. Code that assumes content is always a string will crash.
Always check `message.tool_calls` first.

**Streaming + tool calls:** In streaming mode, tool call arguments arrive as fragments
across multiple chunks. You must accumulate `delta.tool_calls[i].function.arguments`
across chunks before parsing as JSON.

**Temperature 0 is not deterministic:** `temperature=0` uses greedy decoding but
hardware-level floating point differences across GPUs can produce different outputs.
Use `seed` parameter for better (but still not perfect) reproducibility.

**Content filter false positives:** The content filter can trigger on legitimate
business content (medical, legal, financial discussions). `finish_reason: "content_filter"`
means the output was truncated. Retry with rephrased input or use a different model.

**Long system prompts cost more than you think:** Token counting includes the system
prompt on every request. A 2000-token system prompt sent 100 times costs as much as
200K input tokens. Use prompt caching (automatic for repeated prefixes) to mitigate.

**JSON mode without schema:** `response_format={"type": "json_object"}` guarantees
valid JSON but not any particular structure. Use structured outputs (Pydantic model)
when you need a guaranteed schema.

---

## Ecosystem Position and Composition

**Position:** OpenAI is the **de facto standard API shape** for LLM services. The
`/v1/chat/completions` interface has become an industry standard that competitors
implement for compatibility.

**Natural complements in EOS:**
- **Groq** — OpenAI-compatible API at `base_url="https://api.groq.com/openai/v1"`.
  Same SDK, different models (Llama 3.3 70B). Ultra-fast inference.
- **Perplexity** — OpenAI-compatible at `base_url="https://api.perplexity.ai"`.
  Adds real-time web search augmentation to LLM responses.
- **Together AI** — OpenAI-compatible. Access to open-source models.
- **Neon (pgvector)** — Store OpenAI embeddings in Postgres for semantic search.

**Integration anti-patterns:**
- Don't use OpenAI embeddings with non-cosine similarity metrics — they're normalized
  for cosine similarity.
- Don't mix embedding models in the same vector store — dimensions and semantic spaces
  differ between text-embedding-3-small and text-embedding-3-large.
- Don't assume OpenAI-compatible providers support all parameters — Groq ignores
  `logprobs`, Perplexity ignores `tools`, etc.

**EOS architecture position:** OpenAI SDK is the **transport layer** for multiple
providers via `base_url` override. model_router.py's `_call_openai_compatible()` is
the single method that handles Perplexity, Groq, and potentially OpenAI direct. The
OpenAI SDK is infrastructure, not just another provider.

---

## Trajectory and Evolution

**Current trajectory (2025-2026):**
- **Responses API** — New agentic endpoint with built-in tools (web search, code
  interpreter, file search). Positioning as the future replacement for chat completions
  for agentic workflows. Already used by EOS last30days skill.
- **Agents SDK** — Open-source Python framework for building multi-agent systems.
  Separate from the API SDK. Competitor to LangChain/CrewAI.
- **Reasoning models (o-series)** — o1, o3, o3-mini. Chain-of-thought reasoning
  with "thinking tokens" that don't appear in output. Higher quality, higher latency,
  higher cost. `max_completion_tokens` instead of `max_tokens`.
- **GPT-4.1 family** — 1M context window. Three tiers: GPT-4.1, GPT-4.1-mini,
  GPT-4.1-nano. Positioned for long-document and code tasks.
- **Prompt caching** — Automatic 50% discount on repeated input prefixes. Incentivizes
  putting static context at the start of messages.
- **Structured outputs maturing** — Moving from beta to stable. Pydantic integration
  getting tighter.

**Deprecation signals:**
- Chat Completions remains stable — no deprecation signals.
- `gpt-3.5-turbo` effectively deprecated by `gpt-4o-mini` (cheaper and better).
- Plugin ecosystem fully dead — replaced by function calling and Responses API tools.
- Legacy embedding model `text-embedding-ada-002` deprecated in favor of v3 models.

**What to adopt early:** Structured outputs, prompt caching patterns, Batch API for
cost-sensitive workloads, Responses API for web-search-augmented tasks.

---

## Conceptual Model and Solution Recipes

**Mental model:** Think of the OpenAI API as a **stateless function machine**.
Input: messages + configuration. Output: completion + metadata. Every call is independent.
State (conversation history) is managed client-side by appending messages.

**Primitives:**
- **Message** — the atom. Role + content.
- **Completion** — the verb. Transform messages into an assistant response.
- **Tool** — the extension. Let the model request external actions.
- **Embedding** — the projection. Map text to vector space for similarity.

**Recipe 1: Multi-turn conversation with memory**
```python
messages = [{"role": "system", "content": "You are a helpful assistant."}]
while True:
    user_input = input("> ")
    messages.append({"role": "user", "content": user_input})
    response = client.chat.completions.create(model="gpt-4o", messages=messages)
    assistant_msg = response.choices[0].message.content
    messages.append({"role": "assistant", "content": assistant_msg})
    print(assistant_msg)
    # Trim messages when approaching context limit
```

**Recipe 2: Tool-calling agent loop**
```python
messages = [{"role": "system", "content": "Use tools to answer questions."}]
messages.append({"role": "user", "content": user_query})
while True:
    response = client.chat.completions.create(model="gpt-4o", messages=messages, tools=tools)
    msg = response.choices[0].message
    messages.append(msg)  # append assistant message (with or without tool_calls)
    if not msg.tool_calls:
        break  # model is done — final answer in msg.content
    for tc in msg.tool_calls:
        result = execute_tool(tc.function.name, json.loads(tc.function.arguments))
        messages.append({"role": "tool", "tool_call_id": tc.id, "content": json.dumps(result)})
```

**Recipe 3: Structured extraction pipeline**
```python
from pydantic import BaseModel
class Lead(BaseModel):
    name: str
    company: str
    pain_point: str
    icp_score: int

response = client.beta.chat.completions.parse(
    model="gpt-4o",
    messages=[
        {"role": "system", "content": "Extract lead info from this conversation."},
        {"role": "user", "content": raw_conversation_text},
    ],
    response_format=Lead,
)
lead = response.choices[0].message.parsed
# Guaranteed to be a Lead instance with correct types
```

**Recipe 4: Semantic search with embeddings**
```python
# Index phase
texts = ["doc1 content", "doc2 content", ...]
resp = client.embeddings.create(model="text-embedding-3-small", input=texts)
vectors = [d.embedding for d in resp.data]
# Store vectors in pgvector / Neon

# Query phase
q_resp = client.embeddings.create(model="text-embedding-3-small", input=[query])
q_vec = q_resp.data[0].embedding
# SELECT * FROM docs ORDER BY embedding <=> q_vec LIMIT 5
```

---

## Industry Expert and Cutting-Edge Usage

**Expert patterns in production (2025-2026):**

1. **Cascade routing (what EOS does):** Use cheap models first (GPT-4o-mini, Haiku),
   escalate to expensive models (GPT-4o, Opus) only when quality score is below threshold.
   EOS model_router.py implements this with `_should_escalate()` at threshold 0.40.

2. **Prompt caching optimization:** Structure all prompts with static system content
   first (venture context, soul docs, skill instructions) and dynamic user content last.
   OpenAI automatically caches repeated prefixes at 50% discount. This aligns with
   EOS's system prompt injection order in agent_runtime.py.

3. **Structured outputs for all agent communication:** Replace free-text parsing with
   Pydantic models. Eliminates regex/JSON parsing failures. Use for: ICP scoring,
   lead classification, content generation templates.

4. **Batch API for overnight processing:** Submit bulk scoring/classification jobs
   before EOD. Results ready by morning. 50% cost reduction. Perfect for EOS nightly
   maintenance cycle (nightly_maintenance.sh).

5. **Embedding-based deduplication:** Before processing new leads/signals, embed and
   compare against existing vectors. Cosine similarity > 0.95 = duplicate. Prevents
   redundant processing and memory bloat.

6. **Multi-model consensus:** For high-stakes decisions (authority_engine CRITICAL class),
   run the same prompt through multiple models (GPT-4o + Claude + Gemini) and compare
   outputs. Agreement = high confidence. Disagreement = human review.

7. **Logprobs for hallucination detection:** On factual claims, check token-level
   logprobs. Low probability tokens on named entities or numbers are hallucination
   signals. Route to web search for verification.

---

## EOS Usage Patterns

### Primary: OpenAI-compatible transport layer
`model_router.py::_call_openai_compatible()` (line 522) is the single method that
routes all OpenAI-format calls. Currently serves:
- Perplexity Sonar (web search / market intel)
- Groq Llama 3.3 70B (fast inference)
- Any future OpenAI-compatible provider

### Secondary: Responses API for web search
`.agents/skills/last30days/scripts/lib/openai_reddit.py` uses the Responses API
(`/v1/responses`) directly via HTTP for Reddit thread discovery with web search tool.
Does not use the Python SDK — uses raw HTTP POST.

### Tertiary: OPENAI_API_KEY in services/.env
Available for direct OpenAI calls if needed. Not currently in the active fallback
chain but registered as `ModelProvider.OPENAI` in model_router.py.

### Not currently used but available:
- Embeddings (EOS uses Neon pgvector but could use OpenAI embeddings)
- Fine-tuning (no current need — prompt engineering covers all use cases)
- DALL-E (no current image generation need)
- TTS (EOS uses Coqui TTS locally)

---

## Gotchas

### v0.x -> v1 migration breaks everything
The v1 SDK is a complete rewrite. No backward compatibility. All import paths, method
names, and response types changed. If you see `openai.ChatCompletion.create()` in any
code, it's v0.x and will not work with v1+.

### openai package not installed on VPS bare metal
Only available in Docker containers. `_call_openai_compatible()` guards with
`try: from openai import OpenAI except ImportError: return ""`.

### Responses API is NOT the same as Chat Completions
Different endpoint (`/v1/responses` vs `/v1/chat/completions`), different request
shape, different response shape. The last30days skill uses Responses API directly
via HTTP. Do not try to use it through `client.chat.completions.create()`.

### gpt-4o-mini does not support web_search tool with filters
Confirmed in last30days skill — excluded from MODEL_FALLBACK_ORDER. If you need
web search, use gpt-4.1 or gpt-4o.

### Some OpenAI-compatible providers return None for usage
Guard with `or 0` when reading `response.usage.prompt_tokens` and
`response.usage.completion_tokens`. EOS model_router.py already does this (line 549-550).

### Content in response is None when tool_calls are present
The most common source of NoneType errors. Always check `message.tool_calls` before
accessing `message.content`.
