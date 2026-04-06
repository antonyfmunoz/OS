# Groq — Creator-Level Best Practices
Source: https://console.groq.com/docs
API Version: v1 (OpenAI-compatible)
SDK Version: groq 1.1.1 (Python)
Last Researched: 2026-04-06

---

# Tier 1 — Technical Mastery

## 1. Authentication

**Auth method:** API key (bearer token).

**How to obtain:**
1. Sign up at https://console.groq.com
2. Navigate to API Keys section
3. Generate key — format: `gsk_` followed by 52 alphanumeric characters

**Headers:**
```
Authorization: Bearer gsk_xxxxx
Content-Type: application/json
```

**SDK initialization:**
```python
# Native SDK — reads GROQ_API_KEY from env automatically
from groq import Groq
client = Groq()  # auto-reads GROQ_API_KEY

# Explicit key
client = Groq(api_key="gsk_...")

# Async variant
from groq import AsyncGroq
client = AsyncGroq(api_key="gsk_...")

# Via OpenAI SDK (used in EOS model_router)
from openai import OpenAI
client = OpenAI(
    api_key=os.getenv("GROQ_API_KEY"),
    base_url="https://api.groq.com/openai/v1",
)
```

**EOS env var locations:**
- `eos_ai/.env` — `GROQ_API_KEY` — used by model_router.py
- `services/.env` — `GROQ_API_KEY` — used by discord_bot.py

**Token lifetime:** Keys do not expire. Revoke manually from console.

**No scopes:** Single key grants access to all endpoints (chat, audio, models).

**No refresh flow:** Static key. No OAuth. No rotation required unless compromised.

---

## 2. Core Operations with Exact Signatures

### Chat Completions
```python
client.chat.completions.create(
    model: str,                          # required — "llama-3.3-70b-versatile"
    messages: list[dict],                # required — [{"role": "user", "content": "..."}]
    max_tokens: int = None,              # optional — max output tokens
    temperature: float = 1.0,            # optional — 0.0-2.0
    top_p: float = 1.0,                  # optional — nucleus sampling
    n: int = 1,                          # optional — number of completions
    stream: bool = False,                # optional — SSE streaming
    stop: str | list[str] = None,        # optional — stop sequences
    frequency_penalty: float = 0.0,      # optional — -2.0 to 2.0
    presence_penalty: float = 0.0,       # optional — -2.0 to 2.0
    response_format: dict = None,        # optional — {"type": "json_object"}
    tools: list[dict] = None,            # optional — function calling tools
    tool_choice: str | dict = None,      # optional — "auto", "none", or specific
    seed: int = None,                    # optional — deterministic generation
    user: str = None,                    # optional — end-user identifier
)
# Returns: ChatCompletion
# {
#   "id": "chatcmpl-xxx",
#   "object": "chat.completion",
#   "created": 1234567890,
#   "model": "llama-3.3-70b-versatile",
#   "choices": [{
#     "index": 0,
#     "message": {"role": "assistant", "content": "..."},
#     "finish_reason": "stop"       # "stop", "length", "tool_calls"
#   }],
#   "usage": {
#     "prompt_tokens": 50,
#     "completion_tokens": 100,
#     "total_tokens": 150,
#     "queue_time": 0.001,          # Groq-specific: time in queue
#     "prompt_time": 0.005,         # Groq-specific: time to process prompt
#     "completion_time": 0.02       # Groq-specific: time to generate output
#   },
#   "x_groq": {"id": "req_xxx"}    # Groq-specific request ID
# }
```

### Audio Transcription (Whisper STT)
```python
client.audio.transcriptions.create(
    model: str,                          # required — "whisper-large-v3" or "whisper-large-v3-turbo"
    file: BinaryIO,                      # required — audio file object
    language: str = None,                # optional — ISO 639-1 code ("en", "es", "fr")
    prompt: str = None,                  # optional — context hint for transcription
    response_format: str = "json",       # optional — "json", "text", "verbose_json", "srt", "vtt"
    temperature: float = 0.0,            # optional — 0.0-1.0
    timestamp_granularities: list = None # optional — ["word", "segment"] (verbose_json only)
)
# Returns (json format):
# {"text": "Transcribed text here."}
#
# Returns (verbose_json format):
# {
#   "text": "Full text",
#   "segments": [{"id": 0, "start": 0.0, "end": 2.5, "text": "..."}],
#   "words": [{"word": "Hello", "start": 0.0, "end": 0.3}]
# }
```

### Audio Translation (to English)
```python
client.audio.translations.create(
    model: str,                          # required — "whisper-large-v3"
    file: BinaryIO,                      # required — audio file object
    prompt: str = None,                  # optional
    response_format: str = "json",       # optional
    temperature: float = 0.0,            # optional
)
# Returns: {"text": "English translation of audio"}
```

### List Models
```python
client.models.list()
# Returns: {"data": [{"id": "llama-3.3-70b-versatile", "object": "model", ...}]}
```

---

## 3. Pagination Patterns

Groq's API does not use pagination for its primary endpoints (chat completions, audio).

The `/models` endpoint returns all available models in a single response — no cursor
or pagination needed. The model list is small (typically under 20 models).

For streaming responses, iterate the generator:
```python
stream = client.chat.completions.create(model="...", messages=[...], stream=True)
for chunk in stream:
    content = chunk.choices[0].delta.content
    if content:
        process(content)
```

N/A for most use cases. No paginated list endpoints exist.

---

## 4. Rate Limits

Groq enforces rate limits per model, per API key, per time window.
Limits vary significantly between free and paid tiers.

### Free Tier Limits (as of 2025)

| Model | RPM | RPD | TPM | TPD |
|---|---|---|---|---|
| llama-3.3-70b-versatile | 30 | 14,400 | 6,000 | 500,000 |
| llama-3.1-8b-instant | 30 | 14,400 | 20,000 | 500,000 |
| gemma2-9b-it | 30 | 14,400 | 15,000 | 500,000 |
| mixtral-8x7b-32768 | 30 | 14,400 | 5,000 | 500,000 |
| whisper-large-v3 | 20 | 2,000 | — | — |
| whisper-large-v3-turbo | 20 | 2,000 | — | — |

RPM = requests per minute. RPD = requests per day. TPM = tokens per minute. TPD = tokens per day.

### Paid Tier (Developer / Team)
Paid tiers increase limits roughly 10-20x. Exact limits shown in console dashboard.
Enterprise tier offers custom limits negotiated per contract.

### Rate limit headers
Groq returns these headers on every response:
```
x-ratelimit-limit-requests: 30
x-ratelimit-limit-tokens: 6000
x-ratelimit-remaining-requests: 29
x-ratelimit-remaining-tokens: 5500
x-ratelimit-reset-requests: 2s
x-ratelimit-reset-tokens: 1.5s
```

### When rate limited
- HTTP 429 status code returned
- No `Retry-After` header — use the `x-ratelimit-reset-*` headers instead
- Recommended: exponential backoff starting at 1 second, max 60 seconds
- EOS pattern: model_router falls through to next provider on any error

### Audio rate limits
Whisper endpoints have separate rate limits (RPM/RPD) but no token-based limits.
Audio file processing time counts against a per-minute compute budget.

---

## 5. Error Codes and Recovery

### HTTP Status Codes

| Code | Meaning | Retryable | Recovery |
|---|---|---|---|
| 400 | Bad Request — invalid params, malformed JSON | No | Fix request body |
| 401 | Authentication Error — invalid or missing API key | No | Check GROQ_API_KEY |
| 403 | Permission Denied — key lacks access | No | Check account status |
| 404 | Not Found — invalid model name or endpoint | No | Check model ID |
| 413 | Payload Too Large — audio file > 25 MB | No | Chunk audio file |
| 422 | Unprocessable Entity — valid JSON but invalid content | No | Fix field values |
| 429 | Rate Limited — too many requests or tokens | Yes | Exponential backoff |
| 500 | Internal Server Error — Groq infrastructure issue | Yes | Retry after 5s |
| 503 | Service Unavailable — model temporarily down | Yes | Retry after 10s |

### Error response body format
```json
{
  "error": {
    "message": "Rate limit reached for model `llama-3.3-70b-versatile`...",
    "type": "rate_limit_error",
    "code": "rate_limit_exceeded"
  }
}
```

### Groq-specific error types
- `invalid_request_error` — malformed request, unsupported parameter
- `authentication_error` — bad API key
- `rate_limit_error` — 429, includes which limit was hit (RPM, TPM, RPD, TPD)
- `server_error` — Groq infrastructure issue
- `model_not_found_error` — requested model does not exist or is deprecated
- `model_decommissioned` — model has been permanently removed

### Recovery strategies
- **429 rate_limit_error**: Read `x-ratelimit-reset-*` headers, wait that duration.
  If unavailable, exponential backoff: 1s, 2s, 4s, 8s, max 60s.
- **500/503**: Retry up to 3 times with 5s delay. If persistent, fall to next provider.
- **401**: Do not retry. Check env var. Key may have been revoked.
- **413**: Split audio into chunks < 25 MB before retrying.

### SDK exception classes (groq 1.1.1)
```python
from groq import (
    APIError,              # base class for all API errors
    APIConnectionError,    # network/connection failure
    RateLimitError,        # 429
    APIStatusError,        # any non-2xx status
    AuthenticationError,   # 401
    BadRequestError,       # 400
    NotFoundError,         # 404
    UnprocessableEntityError,  # 422
    InternalServerError,   # 500
)
```

---

## 6. SDK Idioms

### Package and import
```python
# pip install groq
from groq import Groq, AsyncGroq
```

### Client initialization
```python
# Sync client (auto-reads GROQ_API_KEY env var)
client = Groq()

# Async client
client = AsyncGroq()

# With explicit configuration
client = Groq(
    api_key="gsk_...",
    timeout=30.0,          # default: 60s
    max_retries=2,         # default: 2 (SDK handles retries automatically)
)
```

### SDK auto-retry
The Groq SDK has built-in retry logic for 429, 500, and 503 errors.
Default: 2 retries with exponential backoff. Configure via `max_retries`.

### Async usage
```python
import asyncio
from groq import AsyncGroq

async def main():
    client = AsyncGroq()
    response = await client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[{"role": "user", "content": "Hello"}],
    )
    print(response.choices[0].message.content)

asyncio.run(main())
```

### Context manager (resource cleanup)
```python
with Groq() as client:
    response = client.chat.completions.create(...)
```

### Version: groq 1.1.1
- Uses httpx under the hood (not requests)
- Pydantic models for all response types
- Type hints throughout
- Mirrors OpenAI SDK structure for familiarity

---

## 7. Anti-Patterns

### WRONG: Using Groq SDK for chat in model_router
```python
# WRONG — model_router uses OpenAI SDK for all OpenAI-compatible providers
from groq import Groq
client = Groq(api_key=key)
client.chat.completions.create(...)
```
```python
# RIGHT — OpenAI SDK pointed at Groq base URL
from openai import OpenAI
client = OpenAI(api_key=key, base_url="https://api.groq.com/openai/v1")
client.chat.completions.create(...)
```

### WRONG: Using OpenAI SDK for audio transcription
```python
# WRONG — OpenAI SDK pointed at Groq doesn't support audio endpoints cleanly
from openai import OpenAI
client = OpenAI(api_key=key, base_url="https://api.groq.com/openai/v1")
client.audio.transcriptions.create(...)  # may work but untested path
```
```python
# RIGHT — Use native Groq SDK for audio
from groq import Groq
client = Groq(api_key=key)
client.audio.transcriptions.create(model="whisper-large-v3-turbo", file=f)
```

### WRONG: Not specifying language for Whisper
```python
# WRONG — Whisper auto-detects language, wasting first ~30s of audio on detection
result = client.audio.transcriptions.create(model="whisper-large-v3-turbo", file=f)
```
```python
# RIGHT — specify language for faster, more accurate transcription
result = client.audio.transcriptions.create(
    model="whisper-large-v3-turbo", file=f, language="en"
)
```

### WRONG: Sending max_tokens larger than model context
```python
# WRONG — llama-3.1-8b-instant has 128k context but max output of 8192 tokens
response = client.chat.completions.create(
    model="llama-3.1-8b-instant",
    messages=[...],
    max_tokens=32000,  # exceeds max output, will error
)
```

### WRONG: Assuming Groq models match OpenAI model names
```python
# WRONG — Groq uses its own model IDs
response = client.chat.completions.create(model="gpt-4", ...)  # 404 error
```
```python
# RIGHT — use Groq model IDs
response = client.chat.completions.create(model="llama-3.3-70b-versatile", ...)
```

### WRONG: Not handling audio file size limits
```python
# WRONG — sending large audio files without checking size
with open("long_meeting.wav", "rb") as f:
    result = client.audio.transcriptions.create(model="whisper-large-v3", file=f)
    # Fails with 413 if > 25 MB
```

---

## 8. Data Model

### Chat Completion Object
```
ChatCompletion
  ├── id: str                    # "chatcmpl-xxx"
  ├── object: "chat.completion"
  ├── created: int               # Unix timestamp
  ├── model: str                 # Actual model used
  ├── choices: list
  │     └── Choice
  │           ├── index: int
  │           ├── message: Message
  │           │     ├── role: "assistant"
  │           │     ├── content: str | None
  │           │     └── tool_calls: list | None
  │           └── finish_reason: str  # "stop", "length", "tool_calls"
  ├── usage: Usage
  │     ├── prompt_tokens: int
  │     ├── completion_tokens: int
  │     ├── total_tokens: int
  │     ├── queue_time: float     # Groq-specific
  │     ├── prompt_time: float    # Groq-specific
  │     └── completion_time: float # Groq-specific
  └── x_groq: dict               # {"id": "req_xxx"}
```

### Transcription Object
```
Transcription
  ├── text: str                  # Full transcribed text
  ├── segments: list (verbose_json only)
  │     └── Segment
  │           ├── id: int
  │           ├── start: float   # seconds
  │           ├── end: float     # seconds
  │           └── text: str
  └── words: list (verbose_json + timestamp_granularities=["word"] only)
        └── Word
              ├── word: str
              ├── start: float
              └── end: float
```

### Model IDs (immutable — use exactly as listed)
- `llama-3.3-70b-versatile` — 128k context, best quality
- `llama-3.1-8b-instant` — 128k context, fastest
- `gemma2-9b-it` — 8k context, Google instruction-tuned
- `mixtral-8x7b-32768` — 32k context, Mistral MoE
- `whisper-large-v3` — best STT accuracy
- `whisper-large-v3-turbo` — faster STT

---

## 9. Webhooks and Events

N/A. Groq does not offer webhooks or event subscriptions.
All interactions are synchronous request-response (or streaming SSE).
There is no notification system for quota changes, model updates,
or account events.

---

## 10. Limits

| Limit | Value |
|---|---|
| Max audio file size | 25 MB |
| Supported audio formats | mp3, mp4, mpeg, mpga, m4a, wav, webm, flac |
| Max output tokens (llama-3.3-70b) | 32,768 |
| Max output tokens (llama-3.1-8b) | 8,192 |
| Max output tokens (mixtral-8x7b) | 32,768 |
| Max context window (llama-3.3-70b) | 128,000 |
| Max context window (llama-3.1-8b) | 128,000 |
| Max context window (gemma2-9b-it) | 8,192 |
| Max context window (mixtral-8x7b) | 32,768 |
| Max number of messages per request | No documented limit (context window is the constraint) |
| Max tool definitions per request | 128 |
| Max stop sequences | 4 |
| Request body size limit | ~4 MB (for JSON body, not audio) |
| API keys per account | Unlimited |
| Concurrent requests | Subject to RPM limits |

---

## 11. Cost Model

### Free tier
- No credit card required
- Rate limited (see Section 4)
- Suitable for development and light production
- No cost per token — completely free within limits

### Paid tiers (as of 2025)

| Tier | Cost | Benefit |
|---|---|---|
| Free | $0/month | 30 RPM, low TPM |
| Developer | Pay-as-you-go | Higher limits, usage-based pricing |
| Team | Custom | Shared org keys, higher limits |
| Enterprise | Custom | SLAs, dedicated capacity |

### Token pricing (Developer pay-as-you-go)

| Model | Input (per 1M tokens) | Output (per 1M tokens) |
|---|---|---|
| llama-3.3-70b-versatile | $0.59 | $0.79 |
| llama-3.1-8b-instant | $0.05 | $0.08 |
| gemma2-9b-it | $0.20 | $0.20 |
| mixtral-8x7b-32768 | $0.24 | $0.24 |
| whisper-large-v3 | $0.111/hour | — |
| whisper-large-v3-turbo | $0.04/hour | — |

### EOS cost context
- EOS model_router registers Groq at `cost_per_1k=0.00059` ($0.59/1M input)
- At free tier: $0 actual cost, 500K TPD limit
- A typical EOS fast_response call (500 tokens out) costs ~$0.0004 on paid tier
- Whisper-large-v3-turbo: 1 hour of audio = $0.04. Discord voice sessions
  are typically 30s-5min, so STT cost is negligible.

### Monitoring usage
- Dashboard: https://console.groq.com/settings/usage
- No programmatic usage API
- No budget alerts — monitor manually or track via response headers

---

## 12. Version Pinning

### API version
Groq uses a single API version (`v1`) in the base URL:
`https://api.groq.com/openai/v1`. No version header or date-based versioning.
Breaking changes are communicated via email and changelog.

### SDK version
Current: `groq==1.1.1` (installed on EOS VPS, but NOT in requirements.txt).

Pin in requirements.txt:
```
groq==1.1.1
```

### Model versioning
Groq models use descriptive IDs (e.g., `llama-3.3-70b-versatile`) rather than
date-pinned versions. When Groq updates underlying model weights, the same
model ID may point to a newer version. No way to pin to a specific model
checkpoint.

### Deprecation policy
Groq announces model deprecations via email and console banner. Typical notice
period: 2-4 weeks. Deprecated models return `model_decommissioned` error.

### Known deprecations
- `llama2-70b-4096` — deprecated, replaced by llama-3 variants
- `llama-3-70b-8192` — deprecated, replaced by llama-3.1/3.3 variants
- Groq periodically removes older model versions — always check `/models` endpoint

---

# Tier 2 — Creator Intelligence

## 13. Design Intent and Tradeoffs

Groq was founded by Jonathan Ross (former Google TPU architect) with one thesis:
inference speed is the bottleneck for AI adoption, and custom silicon can solve it.
The LPU (Language Processing Unit) is a purpose-built ASIC that eliminates the
memory bandwidth bottleneck that makes GPU inference slow.

**Core design philosophy:**
- Speed over flexibility. Groq does not offer fine-tuning, embeddings, or image
  generation. It does one thing — run inference fast on supported models.
- OpenAI compatibility as moat reduction. By matching the OpenAI API exactly, Groq
  makes switching trivial. One line change (base_url) to migrate from OpenAI.
- Open-source model ecosystem. Groq bets that open-source models (LLaMA, Mixtral)
  will close the gap with closed models, making the inference layer more valuable
  than the model layer.

**Tradeoffs:**
- No fine-tuning = you use models as-is. System prompts are your only customization.
- Limited model selection = only models Groq has compiled for LPU hardware.
- No embeddings API = cannot replace OpenAI for RAG pipelines (need separate provider).
- Free tier rate limits are aggressive = not viable for production without paid plan.

**What Groq is NOT:**
- Not a model company (doesn't train models)
- Not a full AI platform (no fine-tuning, no vector store, no agents)
- Not a GPU cloud (custom ASIC, not rented GPUs)

---

## 14. Problem-Solution Map and Hidden Capabilities

**Problem: Need fastest possible LLM response for real-time UX**
→ Solution: Groq + llama-3.1-8b-instant. Sub-100ms time-to-first-token.
Faster than any GPU provider for equivalent model quality.

**Problem: Need cheap, fast speech-to-text for voice interfaces**
→ Solution: Groq Whisper. whisper-large-v3-turbo at $0.04/hour is 2.7x cheaper
than OpenAI Whisper ($0.006/min = $0.36/hour) with comparable speed.

**Problem: Need tool calling with open-source models**
→ Solution: Groq + llama-3.3-70b-versatile with parallel tool calling.
LLaMA 3.3 70B has strong function calling that rivals GPT-4 in structured output.

**Hidden capabilities:**
- **Seed parameter**: Pass `seed=42` for deterministic outputs. Useful for testing
  and reproducibility. Not widely known.
- **Groq-specific usage fields**: `queue_time`, `prompt_time`, `completion_time`
  in usage response — lets you diagnose whether latency is from queuing or inference.
- **Word-level timestamps**: `timestamp_granularities=["word"]` with verbose_json
  gives per-word timing — useful for subtitle generation or audio alignment.
- **Prompt-based STT conditioning**: Pass `prompt` parameter to Whisper to guide
  transcription style, vocabulary, or continuation from previous segment.

---

## 15. Operational Behavior and Edge Cases

### Queue time variability
During peak hours, Groq's queue_time can spike from <1ms to >500ms.
The LPU inference itself stays fast, but waiting for a slot adds latency.
Monitor `usage.queue_time` in responses to detect this.

### Whisper hallucination on silence
Whisper models (including on Groq) hallucinate text on silent or near-silent
audio. Common hallucinations: "Thank you for watching", "Subscribe to my channel",
"Thanks for watching". Always use VAD (Voice Activity Detection) to filter
silence BEFORE sending to Groq STT. EOS handles this via SilenceDetectingSink.

### Streaming chunk format
Streaming chunks occasionally arrive with `choices[0].delta.content = None`
(not empty string, but None). Always null-check:
```python
content = chunk.choices[0].delta.content
if content:  # handles both None and ""
    process(content)
```

### Model availability is not guaranteed
Groq occasionally takes models offline for maintenance. A model that was
available yesterday may 404 today. The `/models` endpoint is the source of truth.
EOS model_router handles this by falling through to the next provider.

### Temperature behavior
LLaMA models on Groq with `temperature=0.0` are NOT fully deterministic
(unlike OpenAI). Use `seed` parameter in addition to `temperature=0` for
closest-to-deterministic behavior.

### Audio format sensitivity
Whisper on Groq performs best with WAV (16-bit, 16kHz, mono). Stereo audio
(Discord default: 48kHz stereo) works but may reduce accuracy. Discord bot
records at 48kHz stereo — Whisper handles the conversion internally but
optimal accuracy requires pre-conversion to 16kHz mono.

---

## 16. Ecosystem Position and Composition

### Where Groq sits in the AI stack
Groq is a **pure inference layer**. It sits between model providers (Meta, Mistral,
Google) and applications. It does not compete with OpenAI on model quality — it
competes on speed and cost for open-source model inference.

### Natural complements in EOS
- **Anthropic Claude** (via CC SDK) — quality-critical tasks. Groq handles speed.
- **Gemini** — multimodal and long-context. Groq handles fast text.
- **Ollama** — local free fallback. Groq is the cloud fast fallback.
- **Neon PostgreSQL** — store Groq outputs. No native Groq storage.
- **Discord (py-cord)** — voice recordings → Groq Whisper → text → EOS gateway.

### Integration pattern
```
Discord Voice → SilenceDetectingSink → WAV file
  → Groq Whisper STT (transcribe_with_groq)
  → Text → EOS gateway → cognitive_loop
  → Response → Discord text channel
```

### Forced integration anti-patterns
- Do NOT use Groq for embeddings (no embedding API — use OpenAI or local)
- Do NOT use Groq for image generation (no image API)
- Do NOT use Groq for fine-tuning (no training API)
- Do NOT assume Groq model IDs work on OpenAI (they don't — different model names)

---

## 17. Trajectory and Evolution

### Where Groq is heading (2025-2026)
- **More models**: Groq continuously adds new open-source models as they are
  compiled for LPU. Expect LLaMA 4 models within weeks of Meta release.
- **Vision models**: Groq has added multimodal support for LLaVA and LLaMA 3.2
  vision models. Expect expanded vision capabilities.
- **Batch API**: Groq is developing async batch endpoints for high-volume,
  latency-insensitive workloads at reduced cost (similar to OpenAI Batch API).
- **Enterprise features**: Dedicated capacity, SLAs, VPC peering on roadmap.

### Deprecation signals
- Models with older LLaMA versions (2, 3.0) are being removed
- `llama-3-70b-8192` already deprecated in favor of `llama-3.3-70b-versatile`
- Always use latest model generation — Groq deprecates older versions aggressively

### What to watch
- Groq GroqCloud API changelog: https://console.groq.com/docs/changelog
- Groq Twitter/X: @GroqInc for model addition announcements
- LPU hardware roadmap: next-gen chip promises 2-3x current speed

---

## 18. Conceptual Model and Solution Recipes

### Mental model: Groq as a speed multiplier
Think of Groq as a turbocharger for open-source models. The models are the same
ones you can run on any GPU — Groq just runs them 10-20x faster. Your job is
to pick the right model for the task, write a good prompt, and handle the
response. Everything else (model weights, architecture, capabilities) is
determined by the model provider (Meta, Mistral, Google), not Groq.

### Primitives
1. **Chat completion** — text in, text out. The core primitive.
2. **Audio transcription** — audio in, text out. Whisper-powered.
3. **Audio translation** — non-English audio in, English text out.
4. **Streaming** — token-by-token delivery for real-time UX.
5. **Tool calling** — structured function invocation within chat.

### Recipe: Real-time voice assistant
```
1. Capture audio via Discord SilenceDetectingSink
2. Save utterance as WAV file
3. client.audio.transcriptions.create(model="whisper-large-v3-turbo", file=f, language="en")
4. Classify speech via VoiceEngine.intelligent.classify_speech(text)
5. Route actionable text to EOS gateway
6. Generate response via model_router.call_with_fallback()
7. Post response to Discord text channel
```

### Recipe: Fast agent responses on budget
```
1. Route fast_response/conversation tasks to Groq first (PROVIDER_PRIORITY_FAST)
2. Use llama-3.3-70b-versatile for quality, llama-3.1-8b-instant for speed
3. Set max_tokens to 500-800 (matches _HAIKU_TOKEN_CAPS pattern)
4. If quality_score < 0.40, escalate to CC SDK (Opus)
5. Total cost on free tier: $0. On paid: ~$0.0004 per response.
```

### Recipe: Structured data extraction
```
1. Use response_format={"type": "json_object"}
2. System prompt: "Extract the following fields as JSON: name, email, company"
3. User message: paste raw text
4. Parse response.choices[0].message.content as JSON
5. Validate with Pydantic model
```

---

## 19. Industry Expert and Cutting-Edge Usage

### Speed-first architecture pattern
Leading AI startups use Groq as the "fast path" in a dual-model architecture:
Groq for initial response (sub-200ms), then a stronger model (Claude, GPT-4)
for complex follow-ups. This is exactly what EOS does with its fast-path vs
heavy-path routing in model_router.py.

### Whisper pipeline optimization
Expert pattern for high-volume STT:
1. VAD pre-filtering (Silero or webrtcvad) to skip silence
2. Audio chunking at silence boundaries (not fixed-time)
3. Parallel Groq Whisper calls for each chunk
4. Concatenate transcriptions
This reduces cost and improves accuracy by avoiding Whisper hallucinations on silence.

### Speculative decoding pattern
Use Groq's llama-3.1-8b-instant to generate a draft response, then validate
or refine with a larger model. The 8B model's sub-50ms latency makes this
viable for real-time applications where the draft is "good enough" 80% of
the time and only 20% need escalation.

### Tool calling for structured workflows
Groq's LLaMA 3.3 70B with parallel tool calling enables multi-step agent
workflows at speeds not possible with GPU-hosted models. Expert pattern:
define tools that map to EOS primitives, let the model orchestrate, execute
tools locally, return results in the conversation.

### Cost optimization for startups
The free tier (500K TPD) supports roughly 1000-2000 short conversations per day.
For a pre-revenue startup like EOS, this means the fast inference path is
effectively free. Graduate to paid only when daily volume exceeds free limits.

---

## EOS Usage Patterns

### Model router integration
Groq is registered in `MODEL_REGISTRY` as `groq-llama` with provider
`ModelProvider.GROQ`. Calls route through `_call_openai_compatible()` which
uses the OpenAI SDK pointed at Groq's base URL. Quality score: 0.55.

### Discord STT pipeline
`services/discord_bot.py` → `transcribe_with_groq()` uses native Groq SDK.
Model: `whisper-large-v3-turbo`. Audio comes from `SilenceDetectingSink`
which records 48kHz stereo WAV from Discord voice channels.

### Harness registry
Two entries: `groq_whisper` (TOOL, provides speech_to_text) and
`groq_llm` (MODEL, provides fast_inference). Both keyed on `GROQ_API_KEY`.

### Fallback chain position
Default: CC SDK → Gemini → **Groq** → Anthropic → Perplexity → Ollama
Fast path: Gemini → **Groq** → Anthropic → CC SDK → Perplexity → Ollama

## Gotchas

### groq package missing from requirements.txt
The `groq==1.1.1` package is installed on the VPS but NOT listed in
`services/requirements.txt`. Docker rebuild will break Groq STT.
Add `groq>=1.1.0` to requirements.txt.

### Two SDK paths — do not cross them
Model router: OpenAI SDK → `https://api.groq.com/openai/v1`
Discord STT: Groq SDK → `client.audio.transcriptions.create()`
The OpenAI SDK path does not reliably support audio endpoints on Groq.

### Whisper hallucination on silence
Empty or near-silent audio produces phantom transcriptions like
"Thank you for watching." Always VAD-filter before sending to Groq.

### Free tier TPM exhaustion
llama-3.3-70b-versatile free tier: 6,000 TPM. A single 4000-token prompt
leaves only 2000 tokens for the rest of the minute. Use 8B model for
high-frequency tasks.
