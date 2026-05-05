---
name: ollama
description: "Use when any agent needs local LLM inference, model management, or Ollama API calls."
allowed-tools: "Read, Bash"
version: 1.0
source_url: "https://github.com/ollama/ollama/blob/main/docs/api.md"
last_researched: "2026-04-03"
instantiated_from: templates/tools/_template/
api_version: "v1 (REST, no versioned path — all endpoints under /api/)"
sdk_version: "raw HTTP (no SDK)"
speed_category: fast
trigger: both
effort: medium
context: fork
---

# Tool: Ollama

## What This Tool Does

Ollama is a local LLM runtime that wraps llama.cpp in a user-friendly service layer.
It provides a REST API for running GGUF-quantized language models on CPU or GPU,
with automatic model management (pull, create, copy, delete), Modelfile-based
customization, and streaming/non-streaming inference.

Core capabilities:
- **Text generation** — `/api/generate` (completion) and `/api/chat` (multi-turn)
- **Embeddings** — `/api/embed` for vector generation
- **Model management** — pull, list, show, copy, delete, create (from Modelfile)
- **Process monitoring** — `/api/ps` shows loaded models and VRAM usage
- **Streaming** — SSE-style newline-delimited JSON by default, `"stream": false` for single response

Design philosophy: Local-first inference. No API keys. No cloud dependency.
Models download once and run from `~/.ollama/models/`. The server is a single
binary that manages the llama.cpp lifecycle transparently.

## EOS Integration

**Primary role:** Last-resort fallback in `model_router.py` when Anthropic and Gemini are both down.

**Fallback chain:** CC SDK -> Anthropic API -> Gemini -> Ollama

**Current model:** `qwen2.5:0.5b` (fits in available RAM after Docker takes ~4 GiB)

**Config in model_router.py:**
```python
"ollama-qwen": ModelConfig(
    provider=ModelProvider.OLLAMA,
    model_id="qwen2.5:0.5b",
    api_key_env="",
    strengths=[TaskType.FAST_RESPONSE, TaskType.CONVERSATION, TaskType.ANALYSIS],
    cost_per_1k=0.0,
    base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
)
```

**How EOS calls it** (`_call_ollama` in model_router.py):
```python
payload = {
    "model": config.model_id,
    "prompt": prompt[:4000],
    "stream": False,
    "options": {"num_predict": max_tokens},
}
if system:
    payload["system"] = system[:3000]
resp = requests.post(f"{config.base_url}/api/generate", json=payload, timeout=300)
data = resp.json()
return data.get("response", "")
```

**Availability check** (`_ollama_available`):
```python
resp = requests.get(f"{base}/api/tags", timeout=2)
return resp.status_code == 200
```

**Which agents use it:** All agents via `call_with_fallback()` when cloud providers fail.
Quality gate score for Ollama is 0.35 — lowest in the chain, but better than no response.

**Docker access:** Containers reach host Ollama via `OLLAMA_BASE_URL` env var
(typically `http://host.docker.internal:11434` or the host gateway IP).

## Authentication

**None required.** Ollama is a local service with no authentication layer.

Configuration is via environment variables:
| Variable | Purpose | Default |
|---|---|---|
| `OLLAMA_HOST` | Bind address for Ollama server | `127.0.0.1:11434` |
| `OLLAMA_MODELS` | Model storage directory | `~/.ollama/models` |
| `OLLAMA_KEEP_ALIVE` | How long models stay loaded after last request | `5m` |
| `OLLAMA_NUM_PARALLEL` | Max concurrent requests per model | `1` (CPU), `4` (GPU) |
| `OLLAMA_MAX_LOADED_MODELS` | Max models loaded simultaneously | `1` (CPU), `3` (GPU) |
| `OLLAMA_MAX_QUEUE` | Max queued requests before 503 | `512` |
| `OLLAMA_ORIGINS` | Allowed CORS origins | none |
| `OLLAMA_DEBUG` | Enable debug logging | `false` |

**EOS-specific:** `OLLAMA_BASE_URL` (not an Ollama var — EOS uses this to point Docker containers at the host Ollama instance). Default: `http://localhost:11434`.

To expose Ollama to Docker containers: `OLLAMA_HOST=0.0.0.0:11434`

## Quick Reference

### Generate (completion) — used by EOS
```bash
POST /api/generate
{
  "model": "qwen2.5:0.5b",
  "prompt": "Why is the sky blue?",
  "system": "You are a helpful assistant.",
  "stream": false,
  "options": {
    "num_predict": 256,
    "temperature": 0.7,
    "top_p": 0.9,
    "num_ctx": 2048
  }
}
# Response (stream: false):
{
  "model": "qwen2.5:0.5b",
  "response": "The sky is blue because...",
  "done": true,
  "total_duration": 1234567890,
  "load_duration": 123456789,
  "prompt_eval_count": 15,
  "prompt_eval_duration": 234567890,
  "eval_count": 42,
  "eval_duration": 567890123
}
```

### Chat (multi-turn)
```bash
POST /api/chat
{
  "model": "qwen2.5:0.5b",
  "messages": [
    {"role": "system", "content": "You are helpful."},
    {"role": "user", "content": "Hello"}
  ],
  "stream": false,
  "options": {"num_predict": 256}
}
# Response:
{
  "model": "qwen2.5:0.5b",
  "message": {"role": "assistant", "content": "Hello! How can I help?"},
  "done": true,
  "total_duration": ...,
  "prompt_eval_count": ...,
  "eval_count": ...
}
```

### List models
```bash
GET /api/tags
# Response:
{
  "models": [
    {
      "name": "qwen2.5:0.5b",
      "model": "qwen2.5:0.5b",
      "size": 397764608,
      "digest": "a8b0c5...",
      "details": {
        "parent_model": "",
        "format": "gguf",
        "family": "qwen2",
        "parameter_size": "0.5B",
        "quantization_level": "Q4_K_M"
      }
    }
  ]
}
```

### Show model info
```bash
POST /api/show
{"name": "qwen2.5:0.5b"}
```

### Pull model
```bash
POST /api/pull
{"name": "qwen2.5:7b", "stream": false}
```

### Embeddings
```bash
POST /api/embed
{
  "model": "qwen2.5:0.5b",
  "input": ["text to embed"]
}
# Response: {"model": "...", "embeddings": [[0.123, -0.456, ...]]}
```

### Running models (VRAM check)
```bash
GET /api/ps
# Response: {"models": [{"name": "qwen2.5:0.5b", "size": 397764608, "size_vram": 0, ...}]}
```

### Health check
```bash
GET /
# Returns "Ollama is running" with 200 OK
```

## Gotchas

1. **qwen2.5:3b OOM on this VPS.** Needs ~1.9 GiB RAM for inference. Docker services consume 4+ GiB of the VPS's total RAM. Only 0.5b fits reliably alongside Docker. 7b was pulled but requires stopping Docker services to run.

2. **System prompt must be truncated for small models.** The 0.5b model times out with system prompts longer than ~1500 chars. EOS truncates to 3000 chars in `_call_ollama` (safe for 7b, still risky for 0.5b). If switching to 0.5b, further truncation may be needed.

3. **After model change, restart Docker services.** Python files are bind-mounted, but the model_id is read at import time from `MODEL_REGISTRY`. After changing models: `docker restart os-discord os-monitor os-webhook`.

4. **Streaming is ON by default.** If you forget `"stream": false`, the response is newline-delimited JSON chunks, not a single JSON object. EOS always passes `"stream": false`.

5. **No request authentication means no request isolation.** Any process on the host (or network, if `OLLAMA_HOST=0.0.0.0`) can send requests. On shared hosts, bind to `127.0.0.1` only.

6. **Model loading latency.** First request after idle (beyond `OLLAMA_KEEP_ALIVE`) triggers model load from disk into RAM. For 0.5b this is ~1-2s. For 7b it's 5-15s. EOS uses a 300s timeout to handle this.

7. **`/api/generate` vs `/api/chat` context handling.** `/api/generate` does NOT maintain conversation context between calls. Each call is stateless. `/api/chat` also stateless unless you pass full message history. EOS uses `/api/generate` for single-shot tasks — correct for fallback use.

8. **num_ctx defaults to model's training context.** For qwen2.5 models, default is 32768 tokens. On limited RAM, this pre-allocates a large KV cache. Explicitly set `"num_ctx": 2048` in options to reduce RAM usage for short prompts.

9. **Token counts may be zero.** `prompt_eval_count` and `eval_count` can return 0 or be missing if the model errors internally. EOS handles this with `data.get("prompt_eval_count", 0) or 0`.

10. **Ollama must be installed on the HOST, not in Docker.** It manages its own model storage and llama.cpp processes. Docker containers reach it via network. Don't try to run Ollama inside a container alongside other services.

See references/best_practices.md for full API reference, memory requirements, and quantization details.
