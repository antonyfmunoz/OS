---
name: groq
description: "Use when making fast LLM inference calls via Groq, transcribing audio with Groq Whisper, or debugging Groq-related errors in the EOS model routing chain."
allowed-tools: "Read, Bash"
version: 1.0
source_url: "https://console.groq.com/docs"
last_researched: "2026-04-06"
instantiated_from: templates/tools/_template/
api_version: "v1 (OpenAI-compatible)"
sdk_version: "groq 1.1.1"
speed_category: ultra-fast
trigger: both
effort: medium
context: fork
---

# Tool: Groq (Fast Inference API)

## What This Tool Does

Groq provides ultra-fast LLM inference powered by custom LPU (Language Processing Unit)
hardware. It exposes an OpenAI-compatible REST API, meaning any OpenAI SDK client can
point at Groq's base URL and work immediately. Groq is not a model provider — it runs
open-source models (Meta LLaMA, Mistral, Google Gemma, OpenAI Whisper) on its own
silicon at speeds 10-20x faster than GPU-based inference.

Core capabilities used by EOS:
- **Chat completions** — OpenAI-compatible `/chat/completions` endpoint. Models:
  llama-3.3-70b-versatile, llama-3.1-8b-instant, gemma2-9b-it, mixtral-8x7b-32768
- **Audio transcription (STT)** — Whisper large-v3 and large-v3-turbo via
  `/audio/transcriptions`. Used for Discord voice channel speech-to-text
- **Streaming** — SSE-based token streaming for real-time response delivery
- **Function calling / tool use** — supported on LLaMA and Mixtral models
- **JSON mode** — structured output via `response_format={"type": "json_object"}`

What Groq is NOT:
- Not a model trainer — it runs existing open-source models
- Not a fine-tuning platform — no custom model training
- Not a vector database or RAG provider

## EOS Integration

### Model router (chat completions)
`eos_ai/model_router.py` — Groq is priority 2 in the default fallback chain
(CC SDK -> Gemini -> **Groq** -> Anthropic -> Perplexity -> Ollama) and priority 1
in the fast-path chain (Gemini -> **Groq** -> Anthropic -> CC SDK -> Perplexity -> Ollama).

```python
# MODEL_REGISTRY entry
"groq-llama": ModelConfig(
    provider=ModelProvider.GROQ,
    model_id="llama-3.3-70b-versatile",
    api_key_env="GROQ_API_KEY",
    strengths=[TaskType.FAST_RESPONSE, TaskType.CONVERSATION],
    cost_per_1k=0.00059,
    base_url="https://api.groq.com/openai/v1",
)
```

Groq calls route through `_call_openai_compatible()` in ModelRouter — the same
method used for Perplexity. This works because Groq's API is OpenAI-compatible.
The OpenAI Python SDK is used as the client, not the Groq SDK, for chat completions
in the router path.

Quality score for Groq in the routing chain: **0.55** (below Gemini 0.65, above Ollama 0.45).

### Harness registry
`eos_ai/harness_registry.py` registers two Groq harnesses:
- `groq_whisper` — HarnessType.TOOL, provides `speech_to_text`
- `groq_llm` — HarnessType.MODEL, provides `fast_inference`

### Discord voice STT
`services/discord_bot.py` — `transcribe_with_groq()` function. This is the primary
STT path for Discord voice channels. Uses the native Groq Python SDK (not OpenAI SDK).

```python
from groq import Groq as GroqClient

client = GroqClient(api_key=os.getenv("GROQ_API_KEY"))
result = client.audio.transcriptions.create(
    model="whisper-large-v3-turbo",
    file=f,
    language="en",
)
text = result.text.strip()
```

### Voice handler reference
`services/handlers/voice_handler.py` references `transcribe_with_groq` as the
STT function in the voice processing pipeline.

## Authentication

### API key auth
1. Go to https://console.groq.com/keys
2. Create API key — starts with `gsk_`
3. Store as `GROQ_API_KEY` in both `eos_ai/.env` and `services/.env`
4. Never commit keys. Never log keys.

### Env var locations
```
eos_ai/.env      → GROQ_API_KEY=gsk_...   (used by model_router.py)
services/.env    → GROQ_API_KEY=gsk_...   (used by discord_bot.py)
```

Both files must have the key. The model router loads from `eos_ai/.env`.
The Discord bot loads from `services/.env`. If either is missing, that
code path silently fails.

### No OAuth, no scopes
Groq uses simple API key auth. No OAuth flows, no scopes, no refresh tokens.
Keys do not expire unless manually revoked.

## Quick Reference

### Chat completion (via OpenAI SDK — router path)
```python
from openai import OpenAI

client = OpenAI(
    api_key=os.getenv("GROQ_API_KEY"),
    base_url="https://api.groq.com/openai/v1",
)
response = client.chat.completions.create(
    model="llama-3.3-70b-versatile",
    messages=[
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Explain quantum computing in one sentence."},
    ],
    max_tokens=500,
    temperature=0.7,
)
print(response.choices[0].message.content)
```

### Chat completion (via native Groq SDK)
```python
from groq import Groq

client = Groq(api_key=os.getenv("GROQ_API_KEY"))
response = client.chat.completions.create(
    model="llama-3.3-70b-versatile",
    messages=[{"role": "user", "content": "Hello"}],
    max_tokens=500,
)
print(response.choices[0].message.content)
```

### Audio transcription (Whisper STT)
```python
from groq import Groq

client = Groq(api_key=os.getenv("GROQ_API_KEY"))
with open("audio.wav", "rb") as f:
    result = client.audio.transcriptions.create(
        model="whisper-large-v3-turbo",  # or "whisper-large-v3"
        file=f,
        language="en",                    # optional, improves accuracy
        response_format="json",           # or "text", "verbose_json"
    )
print(result.text)
```

### Streaming chat completion
```python
from groq import Groq

client = Groq(api_key=os.getenv("GROQ_API_KEY"))
stream = client.chat.completions.create(
    model="llama-3.3-70b-versatile",
    messages=[{"role": "user", "content": "Tell me a story."}],
    stream=True,
)
for chunk in stream:
    delta = chunk.choices[0].delta.content
    if delta:
        print(delta, end="", flush=True)
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
                },
                "required": ["location"],
            },
        },
    }
]
response = client.chat.completions.create(
    model="llama-3.3-70b-versatile",
    messages=[{"role": "user", "content": "What's the weather in Portland?"}],
    tools=tools,
    tool_choice="auto",
)
```

### JSON mode
```python
response = client.chat.completions.create(
    model="llama-3.3-70b-versatile",
    messages=[{"role": "user", "content": "List 3 fruits as JSON array"}],
    response_format={"type": "json_object"},
)
```

## Conceptual Model

```
Groq Cloud
  |
  +-- LPU Inference Engine (custom ASIC hardware)
  |     |-- Deterministic execution — no GPU memory bottlenecks
  |     |-- Linear scaling — latency stays flat as batch increases
  |     +-- 10-20x faster than GPU inference for supported models
  |
  +-- OpenAI-Compatible REST API
  |     |-- /chat/completions — text generation (LLaMA, Mixtral, Gemma)
  |     |-- /audio/transcriptions — speech-to-text (Whisper)
  |     |-- /audio/translations — speech translation to English
  |     |-- /models — list available models
  |     +-- All endpoints accept OpenAI SDK format
  |
  +-- Models (open-source, hosted by Groq)
  |     |-- llama-3.3-70b-versatile  — best quality, 128k context
  |     |-- llama-3.1-8b-instant     — fastest text, 128k context
  |     |-- gemma2-9b-it             — Google's 9B instruction-tuned
  |     |-- mixtral-8x7b-32768       — Mistral MoE, 32k context
  |     |-- whisper-large-v3         — best STT accuracy
  |     +-- whisper-large-v3-turbo   — faster STT, slightly less accurate
  |
  +-- groq Python SDK 1.1.1
        |-- groq.Groq — sync client
        |-- groq.AsyncGroq — async client
        |-- Mirrors OpenAI SDK structure exactly
        +-- Adds audio.transcriptions and audio.translations
```

See references/best_practices.md for rate limits, error codes, and anti-patterns.

## Gotchas

### OpenAI SDK vs Groq SDK — two paths in EOS
The model router uses the OpenAI SDK (`from openai import OpenAI`) pointed at
`https://api.groq.com/openai/v1` for chat completions. The Discord bot uses the
native Groq SDK (`from groq import Groq`) for Whisper STT. Both use the same
`GROQ_API_KEY`. Do not mix them up — the OpenAI SDK does not support
`audio.transcriptions.create()`.

### GROQ_API_KEY must be in BOTH env files
`eos_ai/.env` and `services/.env` both need `GROQ_API_KEY`. The model router
only loads `eos_ai/.env`. The Discord bot only loads `services/.env`. Missing
either causes that code path to silently return empty strings.

### whisper-large-v3-turbo vs whisper-large-v3
EOS uses `whisper-large-v3-turbo` in Discord STT for speed. If you need
higher accuracy (e.g., noisy audio, accented speech), switch to `whisper-large-v3`.
The turbo variant is ~3x faster but slightly less accurate on edge cases.

### Rate limits hit 429 without warning
Groq's free tier has aggressive rate limits (30 RPM for LLaMA 70B).
The model router handles this by falling through to the next provider,
but if Groq is the only available provider, requests will fail.
There is no Retry-After header — implement exponential backoff manually.

### 6000 token per minute limit on free tier (LLaMA 70B)
The free tier TPM limit for llama-3.3-70b-versatile is very low.
A single long prompt can exhaust the entire minute's token budget.
For high-throughput use, switch to llama-3.1-8b-instant (higher limits)
or upgrade to a paid plan.

### Audio file size limit: 25 MB
Whisper endpoints reject files over 25 MB. Discord voice recordings
can exceed this for long sessions. The SilenceDetectingSink in
discord_bot.py handles this by chunking at silence boundaries.

### groq SDK not in requirements.txt
The `groq` package (1.1.1) is installed on the VPS but is NOT listed in
`services/requirements.txt`. If the Docker image is rebuilt from scratch,
Groq STT will break. The chat completion path is unaffected because it
uses the `openai` SDK (which is in requirements.txt).
