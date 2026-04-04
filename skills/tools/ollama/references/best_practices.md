# Ollama — Creator-Level Best Practices
Source: https://github.com/ollama/ollama/blob/main/docs/api.md
API Version: v1 (REST, all endpoints under /api/)
SDK Version: Raw HTTP via requests (no official Python SDK used by EOS)
Last Researched: 2026-04-04

---

# Tier 1 — Technical Mastery

## Authentication

**None.** Ollama has no authentication layer. The REST API is open to any process that can reach the port.

### Environment variables that control access
| Variable | Purpose | Default |
|----------|---------|---------|
| `OLLAMA_HOST` | Bind address for server | `127.0.0.1:11434` |
| `OLLAMA_ORIGINS` | Allowed CORS origins | none (all blocked) |

**Security implications:**
- `OLLAMA_HOST=127.0.0.1:11434` (default) — only local processes can connect
- `OLLAMA_HOST=0.0.0.0:11434` — any network host can connect (needed for Docker containers)
- EOS uses `0.0.0.0` binding so Docker containers reach Ollama via `host.docker.internal:11434`
- On shared hosts, bind to 127.0.0.1 and use SSH tunnels or Docker networks

### EOS env vars
| Variable | Location | Value |
|----------|----------|-------|
| `OLLAMA_BASE_URL` | `docker-compose.yml` environment block | `http://host.docker.internal:11434` |

`OLLAMA_BASE_URL` is NOT an Ollama variable — it's EOS-specific, consumed by `model_router.py`.

## Core Operations with Exact Signatures

### POST /api/generate (completion — used by EOS)
```python
# Request
{
    "model": str,           # required — e.g., "qwen2.5:0.5b"
    "prompt": str,          # the prompt
    "suffix": str,          # suffix after generated text (fill-in-middle)
    "images": list[str],    # base64-encoded images (multimodal models only)
    "format": str | dict,   # "json" or JSON schema for structured output
    "options": {            # model parameters (all optional)
        "num_predict": int, # max tokens to generate (default: 128, -1=infinite, -2=fill context)
        "temperature": float,  # creativity (default: 0.8)
        "top_k": int,          # diversity filter (default: 40)
        "top_p": float,        # nucleus sampling (default: 0.9)
        "min_p": float,        # minimum probability filter (default: 0.0)
        "num_ctx": int,        # context window size (default: 2048)
        "repeat_last_n": int,  # lookback for repeat penalty (default: 64)
        "repeat_penalty": float,  # repetition penalty (default: 1.1)
        "seed": int,           # random seed (default: 0 = random)
        "stop": list[str],     # stop sequences
        "tfs_z": float,        # tail free sampling (default: 1.0 = disabled)
        "mirostat": int,       # mirostat mode (0=disabled, 1=v1, 2=v2)
        "mirostat_eta": float, # mirostat learning rate (default: 0.1)
        "mirostat_tau": float, # mirostat target entropy (default: 5.0)
    },
    "system": str,          # system prompt
    "template": str,        # override model's prompt template
    "stream": bool,         # default: true — set false for single response
    "raw": bool,            # bypass templating — send prompt as-is
    "keep_alive": str,      # how long to keep model loaded ("5m", "0" to unload immediately)
    "context": list[int],   # context from previous /generate call (for conversation continuity)
}

# Response (stream: false)
{
    "model": str,
    "created_at": str,              # ISO 8601 timestamp
    "response": str,                # generated text
    "done": bool,                   # true when complete
    "done_reason": str,             # "stop" | "length" | "load"
    "context": list[int],           # token context for follow-up calls
    "total_duration": int,          # nanoseconds — total request time
    "load_duration": int,           # nanoseconds — model load time
    "prompt_eval_count": int,       # number of prompt tokens
    "prompt_eval_duration": int,    # nanoseconds — prompt processing
    "eval_count": int,              # number of generated tokens
    "eval_duration": int,           # nanoseconds — generation time
}
```

### POST /api/chat (multi-turn — not used by EOS)
```python
# Request
{
    "model": str,                    # required
    "messages": [                    # required — conversation history
        {
            "role": str,             # "system" | "user" | "assistant" | "tool"
            "content": str,          # message text
            "images": list[str],     # base64-encoded images (optional)
            "tool_calls": list,      # tool call results (optional)
        }
    ],
    "tools": list[dict],             # tool definitions for function calling
    "format": str | dict,            # "json" or JSON schema
    "options": dict,                 # same as /api/generate options
    "stream": bool,                  # default: true
    "keep_alive": str,
}

# Response (stream: false)
{
    "model": str,
    "created_at": str,
    "message": {
        "role": "assistant",
        "content": str,
        "tool_calls": list | None,   # if tools were defined
    },
    "done": bool,
    "done_reason": str,
    "total_duration": int,
    "load_duration": int,
    "prompt_eval_count": int,
    "prompt_eval_duration": int,
    "eval_count": int,
    "eval_duration": int,
}
```

### POST /api/embed (embeddings)
```python
# Request
{
    "model": str,                    # required
    "input": str | list[str],       # text(s) to embed
    "truncate": bool,               # truncate to context length (default: true)
    "options": dict,                 # model parameters
    "keep_alive": str,
}

# Response
{
    "model": str,
    "embeddings": list[list[float]], # one vector per input
    "total_duration": int,
    "load_duration": int,
    "prompt_eval_count": int,
}
```

### GET /api/tags (list local models)
```python
# Response
{
    "models": [
        {
            "name": str,            # e.g., "qwen2.5:0.5b"
            "model": str,           # same as name
            "modified_at": str,     # ISO 8601
            "size": int,            # bytes on disk
            "digest": str,          # SHA256
            "details": {
                "parent_model": str,
                "format": str,      # "gguf"
                "family": str,      # "qwen2", "llama", etc.
                "families": list[str],
                "parameter_size": str,  # "494.03M", "7.6B"
                "quantization_level": str,  # "Q4_K_M", "Q8_0"
            }
        }
    ]
}
```

### GET /api/ps (running models)
```python
# Response
{
    "models": [
        {
            "name": str,
            "model": str,
            "size": int,            # total model size
            "size_vram": int,       # VRAM used (0 = CPU only)
            "digest": str,
            "details": dict,
            "expires_at": str,      # when model will be unloaded
        }
    ]
}
```

### POST /api/show (model info)
```python
# Request: {"name": "qwen2.5:0.5b"}
# Response
{
    "modelfile": str,          # the Modelfile content
    "parameters": str,         # parameter overrides
    "template": str,           # prompt template
    "details": dict,           # same as /api/tags details
    "model_info": dict,        # architecture details
}
```

### POST /api/pull (download model)
```python
# Request
{"name": "qwen2.5:7b", "stream": false, "insecure": false}

# Response (stream: false)
{"status": "success"}
```

### POST /api/create (create custom model from Modelfile)
```python
# Request
{
    "name": str,              # new model name
    "modelfile": str,         # Modelfile content
    "quantize": str,          # quantization level (e.g., "q4_K_M")
    "stream": bool,
}
```

### POST /api/copy
```python
{"source": "qwen2.5:0.5b", "destination": "my-qwen"}
```

### DELETE /api/delete
```python
{"name": "model-to-delete"}
```

### GET / (health check)
Returns `"Ollama is running"` with HTTP 200.

## Pagination Patterns

N/A — Ollama returns complete responses. No endpoints are paginated.

`/api/tags` returns all models in one response. `/api/ps` returns all loaded models.
Streaming endpoints (`stream: true`) return newline-delimited JSON chunks, but this is streaming output, not pagination.

## Rate Limits

**No rate limits.** Ollama processes requests sequentially or in parallel depending on config.

### Concurrency control
| Variable | Purpose | Default |
|----------|---------|---------|
| `OLLAMA_NUM_PARALLEL` | Max concurrent requests per model | 1 (CPU), 4 (GPU) |
| `OLLAMA_MAX_LOADED_MODELS` | Max models loaded simultaneously | 1 (CPU), 3 (GPU) |
| `OLLAMA_MAX_QUEUE` | Max queued requests before 503 | 512 |

When `OLLAMA_MAX_QUEUE` is exceeded, Ollama returns **HTTP 503 Service Unavailable**.

### Practical throughput (EOS VPS, CPU-only, qwen2.5:0.5b)
- Prompt processing: ~50-100 tokens/second
- Generation: ~20-40 tokens/second
- First-request latency (cold model): 1-2 seconds (model load from disk)
- Subsequent request latency: <100ms to start generating

EOS uses `OLLAMA_NUM_PARALLEL=1` (default) because requests are sequential fallback calls, not parallel workloads.

## Error Codes and Recovery

### HTTP status codes
| Code | Cause | Recovery |
|------|-------|----------|
| 200 | Success | — |
| 400 | Bad request (invalid JSON, missing model) | Fix request payload |
| 404 | Model not found locally | `ollama pull model-name` |
| 500 | Internal error (OOM, model load failure, inference crash) | Check logs: `journalctl -u ollama --since 5m` |
| 503 | Queue full (`OLLAMA_MAX_QUEUE` exceeded) | Wait and retry, or increase queue limit |

### Common error scenarios
| Scenario | Symptom | Recovery |
|----------|---------|----------|
| Model not pulled | 404 on generate | `POST /api/pull {"name": "model"}` |
| OOM during inference | 500, process may crash | Use smaller model or reduce `num_ctx` |
| Timeout | Connection timeout or no response | Increase client timeout (EOS uses 300s) |
| Server not running | Connection refused | `systemctl start ollama` or `ollama serve` |
| Stale model in memory | Slow first request after long idle | Normal — model reloads from disk |
| Corrupted model file | 500 on load | `ollama rm model && ollama pull model` |
| GGUF format mismatch | 500 with "unsupported" in logs | Update Ollama: `curl -fsSL https://ollama.com/install.sh \| sh` |

### EOS error handling
```python
# From model_router.py _call_ollama:
try:
    resp = requests.post(..., timeout=300)
    if resp.status_code == 200:
        data = resp.json()
        return data.get("response", "")
except Exception as e:
    print(f"[ModelRouter] Ollama error: {e}")
return ""  # empty string triggers next fallback
```
EOS treats any Ollama failure as "empty response" and falls through. No retry logic — the fallback chain IS the retry strategy.

## SDK Idioms

### Official Python SDK (not used by EOS)
```python
# pip install ollama
import ollama

# Generate
response = ollama.generate(model='qwen2.5:0.5b', prompt='Hello')
print(response['response'])

# Chat
response = ollama.chat(
    model='qwen2.5:0.5b',
    messages=[{'role': 'user', 'content': 'Hello'}]
)
print(response['message']['content'])

# Streaming
for chunk in ollama.chat(model='qwen2.5:0.5b', messages=[...], stream=True):
    print(chunk['message']['content'], end='')

# Async
import ollama
response = await ollama.AsyncClient().chat(model='...', messages=[...])

# List models
models = ollama.list()

# Pull model
ollama.pull('qwen2.5:7b')
```

### EOS pattern (raw HTTP via requests)
```python
import requests, os

base = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

# Health check
def ollama_available():
    try:
        return requests.get(f"{base}/api/tags", timeout=2).status_code == 200
    except:
        return False

# Generate
def call_ollama(prompt, system="", model="qwen2.5:0.5b", max_tokens=256):
    payload = {
        "model": model,
        "prompt": prompt[:4000],
        "stream": False,
        "options": {"num_predict": max_tokens},
    }
    if system:
        payload["system"] = system[:3000]
    resp = requests.post(f"{base}/api/generate", json=payload, timeout=300)
    if resp.status_code == 200:
        return resp.json().get("response", "")
    return ""
```

EOS uses raw HTTP because:
1. One fewer dependency (no `ollama` package in requirements.txt)
2. Full control over timeout, truncation, and error handling
3. Ollama API is simple enough that a wrapper SDK adds no value

### CLI idioms
```bash
# Interactive chat
ollama run qwen2.5:0.5b

# One-shot generation
echo "What is Python?" | ollama run qwen2.5:0.5b

# List models
ollama list

# Pull model
ollama pull qwen2.5:7b

# Show model info
ollama show qwen2.5:0.5b

# Remove model
ollama rm qwen2.5:3b

# Server management
ollama serve                    # start in foreground
systemctl start ollama          # start as system service
systemctl status ollama         # check service status
journalctl -u ollama --since 5m # recent logs
```

## Anti-Patterns

1. **Forgetting `"stream": false`** — Default is streaming (newline-delimited JSON chunks). Without `stream: false`, `resp.json()` fails because the response isn't a single JSON object. EOS always passes `"stream": false`.

2. **Not truncating system prompts for small models** — qwen2.5:0.5b times out with system prompts longer than ~1500 chars. The model's small context window gets consumed by the system prompt, leaving no room for generation. EOS truncates to 3000 chars (safe for 7b, tight for 0.5b).

3. **Using `/api/generate` for multi-turn conversation** — `/api/generate` is stateless. Each call starts fresh. For conversation, either pass the `context` token array from the previous response, or use `/api/chat` with full message history. EOS uses `/api/generate` intentionally for single-shot fallback tasks.

4. **Not setting `num_ctx` explicitly** — Default is the model's training context (32768 for qwen2.5). On limited RAM, this pre-allocates a massive KV cache. Set `"num_ctx": 2048` to reduce memory usage for short prompts.

5. **Assuming token counts are always present** — `prompt_eval_count` and `eval_count` can return 0 or be missing on internal errors. Always use `.get("field", 0) or 0` pattern.

6. **Running Ollama inside Docker** — Ollama manages its own model storage and llama.cpp processes. It should run on the host. Docker containers connect via network. Don't containerize Ollama alongside application services.

7. **Pulling large models without checking RAM** — `ollama pull qwen2.5:7b` downloads 4.7GB. Loading requires ~5-6GB RAM. If Docker services are using 4GB, the VPS will OOM. Check `free -h` and `docker stats --no-stream` first.

8. **Not handling cold start latency** — First request after model unload (beyond `keep_alive`) triggers disk load. For 0.5b this is 1-2s, for 7b it's 5-15s. Set timeout accordingly. EOS uses 300s timeout.

9. **Using temperature=0 expecting determinism** — Ollama with `temperature: 0` is nearly deterministic but not guaranteed across different hardware/quantization levels. Use `seed` for reproducible outputs, but even seeds don't guarantee cross-platform determinism with GGUF.

10. **Ignoring `done_reason`** — "stop" means natural completion, "length" means `num_predict` was hit (response is truncated). If you're getting incomplete responses, increase `num_predict`.

## Data Model

### Model storage hierarchy
```
~/.ollama/
├── models/
│   ├── manifests/
│   │   └── registry.ollama.ai/
│   │       └── library/
│   │           └── qwen2.5/
│   │               ├── 0.5b     # manifest (JSON, references blobs)
│   │               └── 7b
│   └── blobs/
│       ├── sha256-abc123...  # model weights (GGUF)
│       ├── sha256-def456...  # tokenizer
│       └── sha256-ghi789...  # template/system prompt
```

### Model lifecycle states
```
Not present → pull → Downloaded (on disk)
Downloaded → first request → Loading (into RAM)
Loading → loaded → Running (in RAM, serving requests)
Running → keep_alive expires → Unloaded (back to disk)
Unloaded → next request → Loading again
```

### Key entities
- **Model** — a named reference to a manifest. Names follow `name:tag` format.
- **Manifest** — JSON file listing blobs that compose a model (weights, template, license).
- **Blob** — content-addressable file (SHA256). Shared across models when possible.
- **Modelfile** — declarative spec for creating custom models (FROM, PARAMETER, SYSTEM, TEMPLATE).

### Modelfile instructions
| Instruction | Purpose | Example |
|-------------|---------|---------|
| `FROM` | Base model or GGUF file | `FROM qwen2.5:0.5b` |
| `PARAMETER` | Override model parameter | `PARAMETER temperature 0.7` |
| `SYSTEM` | Default system prompt | `SYSTEM You are helpful.` |
| `TEMPLATE` | Custom prompt template | `TEMPLATE """{{.System}}\n{{.Prompt}}"""` |
| `ADAPTER` | LoRA adapter path | `ADAPTER ./lora.gguf` |
| `LICENSE` | License text | `LICENSE """MIT"""` |
| `MESSAGE` | Pre-seed conversation | `MESSAGE user Hello` |

### Parameter defaults and ranges
| Parameter | Default | Range | Notes |
|-----------|---------|-------|-------|
| `temperature` | 0.8 | 0.0 – 2.0 | Higher = more creative |
| `top_k` | 40 | 1 – 100+ | Token diversity filter |
| `top_p` | 0.9 | 0.0 – 1.0 | Nucleus sampling threshold |
| `min_p` | 0.0 | 0.0 – 1.0 | Minimum probability filter |
| `num_predict` | 128 | -2 – unlimited | -1=infinite, -2=fill context |
| `num_ctx` | 2048 | 1 – model max | Context window size |
| `repeat_last_n` | 64 | 0 – num_ctx | 0=disabled, -1=full context |
| `repeat_penalty` | 1.1 | 0.0 – 2.0 | Higher = less repetition |
| `seed` | 0 | 0 – 2^32 | 0 = random |
| `tfs_z` | 1.0 | 0.0 – 2.0 | 1.0 = disabled |
| `mirostat` | 0 | 0, 1, 2 | 0=disabled |
| `mirostat_eta` | 0.1 | 0.0 – 1.0 | Learning rate |
| `mirostat_tau` | 5.0 | 0.0 – 10.0 | Target entropy |

## Webhooks and Events

N/A — Ollama has no webhook or event system. It is a request-response service.

For monitoring, use:
- `GET /api/ps` to poll loaded models
- `OLLAMA_DEBUG=1` for debug logging to stdout/journald
- `journalctl -u ollama -f` to stream logs in real time

## Limits

| Resource | Limit |
|----------|-------|
| Model name length | No hard limit (follows `name:tag` convention) |
| Prompt length | No hard limit — capped by `num_ctx` tokens |
| System prompt length | No hard limit — shares `num_ctx` with prompt |
| `num_ctx` max | Model-dependent (qwen2.5: 131072 training, practical: limited by RAM) |
| `num_predict` max | No hard limit (-1 = generate until stop token) |
| Concurrent requests | `OLLAMA_NUM_PARALLEL` (default 1 CPU, 4 GPU) |
| Max queue depth | `OLLAMA_MAX_QUEUE` (default 512) |
| Max loaded models | `OLLAMA_MAX_LOADED_MODELS` (default 1 CPU, 3 GPU) |
| Image input size | No hard limit (base64 encoded, limited by RAM) |
| Request body size | No hard limit (Go HTTP server default) |

### Memory requirements (approximate, Q4_K_M quantization)
| Model | Disk | RAM (inference) | Notes |
|-------|------|-----------------|-------|
| qwen2.5:0.5b | 397MB | ~600MB | Fits alongside Docker on EOS VPS |
| qwen2.5:3b | 1.9GB | ~2.5GB | OOM on EOS VPS with Docker running |
| qwen2.5:7b | 4.7GB | ~5.5GB | Requires stopping Docker services |
| llama3.1:8b | 4.9GB | ~6GB | Does not fit on EOS VPS |
| mistral:7b | 4.1GB | ~5GB | Does not fit on EOS VPS |

### EOS VPS memory budget
```
Total RAM: ~8GB
Docker services: 2-4GB (steady state)
OS + system: ~1GB
Available for Ollama: 3-5GB
Safe model: qwen2.5:0.5b (~600MB)
Possible with Docker stopped: qwen2.5:7b (~5.5GB)
```

## Cost Model

**Free.** Ollama is open source (MIT license). No per-request charges. No API keys. No usage tiers.

Real costs:
- **RAM** — models consume RAM while loaded. Larger models = more RAM = larger VPS = more $/month
- **CPU** — inference is CPU-bound without GPU. Adds latency but minimal cost on fixed-price VPS
- **Disk** — model files consume disk space (~400MB to ~5GB per model)
- **Electricity/VPS cost** — keeping Ollama running 24/7 adds negligible overhead to VPS bill

### Cost comparison for EOS
| Provider | Cost per 1K tokens | Quality gate score |
|----------|--------------------|--------------------|
| Anthropic (Claude) | $0.015 (Haiku) | 0.70 |
| Gemini (Flash) | $0.000075 | 0.55 |
| Ollama (qwen2.5:0.5b) | $0.00 | 0.35 |

Ollama is the cheapest option but lowest quality. Used only as last-resort fallback.

## Version Pinning

### Current versions (EOS VPS)
- Ollama: **0.18.2**
- Default model: **qwen2.5:0.5b** (Q4_K_M quantization)
- Also pulled: **qwen2.5:7b** (Q4_K_M, not in active use)

### Update Ollama
```bash
curl -fsSL https://ollama.com/install.sh | sh
# Or on Linux:
sudo systemctl restart ollama
```

### Versioning policy
- Ollama follows semver loosely. Breaking API changes are rare.
- New model format support (GGUF versions) may require Ollama updates.
- Model registry updates happen independently of Ollama version.
- No API versioning in URL — the API is unversioned. Changes are backwards-compatible.

### Deprecation risks
- Old GGUF format versions may stop loading after Ollama updates. Re-pull models.
- llama.cpp is rapidly evolving — Ollama tracks upstream changes. New quantization methods appear frequently.
- No announced deprecations of existing API endpoints as of April 2026.

---

# Tier 2 — Creator Intelligence

## Design Intent and Tradeoffs

Ollama's fundamental design bet: **make local LLM inference as easy as `docker pull` + `docker run`.**

1. **Go server wrapping llama.cpp** — Ollama is a Go HTTP server that manages llama.cpp instances. The Go layer handles HTTP, model management, and process lifecycle. llama.cpp does the actual inference. This separation means Ollama gets Go's concurrency and HTTP handling while leveraging llama.cpp's optimized inference kernels.

2. **GGUF as the universal format** — Ollama only supports GGUF (via llama.cpp). This means any model must be quantized to GGUF to run. The tradeoff: you can't run PyTorch or safetensors models directly, but you get consistent performance characteristics and smaller model files.

3. **Model registry modeled on Docker** — `ollama pull` mirrors `docker pull`. Models are content-addressable blobs with manifests. This is intentional — the mental model transfers from container images to model images.

4. **No authentication by design** — Ollama is local-first. Auth would add friction to the "just run it" experience. The security model is: whoever has network access to the port can use it. This is fine for single-user VPS, problematic for shared hosts.

5. **Streaming by default** — The API streams by default because LLM generation is slow. Streaming lets clients show tokens as they generate, improving perceived latency. EOS disables streaming (`stream: false`) because it processes complete responses, not token-by-token UI.

6. **Automatic model loading/unloading** — Ollama loads models into RAM on first request and unloads after `keep_alive` expires (default 5m). This means RAM is only consumed while the model is in use. The tradeoff: cold start latency on first request after idle.

## Problem-Solution Map and Hidden Capabilities

### "Response is garbage/incoherent"
Cause: Model too small for the task. qwen2.5:0.5b has 494M parameters — it struggles with complex reasoning, long context, and nuanced language.
Fix: Either simplify the prompt (shorter, more direct) or upgrade to 7b (requires stopping Docker).

### "Response is truncated mid-sentence"
Cause: `num_predict` default is 128 tokens.
Fix: Pass `"options": {"num_predict": 512}` or higher. -1 for unlimited.

### "Request takes 5+ minutes"
Cause: Large `num_ctx` pre-allocating huge KV cache on CPU, or system prompt too long for model size.
Fix: Set `"options": {"num_ctx": 2048}` and truncate prompts.

### "Model loads but gives empty response"
Cause: Prompt or system prompt contains characters the tokenizer can't handle, or prompt is too long and gets truncated to nothing.
Fix: Ensure prompt is valid UTF-8. Check `prompt_eval_count` in response — if 0, the prompt wasn't processed.

### "Server crashes during large model load"
Cause: OOM. The model doesn't fit in available RAM.
Fix: Check `free -h` before pulling. Rule of thumb: model size on disk × 1.3 = RAM needed for inference.

### Hidden capabilities
- **Structured output** — Pass a JSON schema as `"format"` for guaranteed JSON structure:
  ```json
  {"format": {"type": "object", "properties": {"answer": {"type": "string"}}, "required": ["answer"]}}
  ```
- **Fill-in-middle** — Use `"suffix"` parameter for code completion between prefix and suffix.
- **Tool calling** — `/api/chat` supports `"tools"` parameter for function calling (model must support it).
- **Custom models via Modelfile** — Create domain-specific models with baked-in system prompts:
  ```
  FROM qwen2.5:0.5b
  SYSTEM You are the EOS sales assistant.
  PARAMETER temperature 0.3
  PARAMETER num_predict 256
  ```
- **Model warm-up** — Send a request with `"keep_alive": "24h"` to keep model loaded. Eliminates cold start latency for the next 24 hours.
- **Embedding generation** — `/api/embed` generates vectors for semantic search. Useful for RAG pipelines with local models.

## Operational Behavior and Edge Cases

### Model loading lifecycle
1. Request arrives → check if model is loaded (`/api/ps`)
2. If not loaded → load from disk (1-2s for 0.5b, 5-15s for 7b)
3. Model loaded into RAM → begin inference
4. After last request + `keep_alive` → unload from RAM
5. Next request → reload from disk

### Memory behavior
- Model weights are memory-mapped (mmap). The OS pages them in on demand.
- KV cache is allocated based on `num_ctx`. Larger context = more RAM per request.
- With `OLLAMA_NUM_PARALLEL > 1`, each parallel slot gets its own KV cache. 4 parallel × 32k context = 4× the KV cache RAM.
- On CPU: all RAM comes from system memory. No VRAM involvement.

### Concurrent request behavior
- Default: 1 concurrent request (CPU). Requests queue up.
- Queue limit: 512 (then 503 errors).
- With parallel > 1: requests share the loaded model but get independent KV caches.
- Different models: only `OLLAMA_MAX_LOADED_MODELS` models can be in RAM simultaneously. Loading a new model may evict the least-recently-used model.

### Token counting quirks
- `prompt_eval_count` may be 0 on the first request if the prompt was cached from a previous request to the same model.
- `eval_count` can be 0 if the model generated nothing (empty response).
- Duration fields are in **nanoseconds**, not milliseconds. Divide by 1e9 for seconds.

### Template behavior
Ollama applies a chat template to prompts by default. The template wraps your prompt in the format the model was trained on. If your prompt is already formatted, use `"raw": true` to bypass templating. EOS does not use `raw` — the `/api/generate` endpoint with `prompt` and `system` fields lets Ollama handle templating correctly.

## Ecosystem Position and Composition

### Where Ollama fits in the EOS stack
```
User message → Discord bot → EOS Gateway → Agent Runtime
                                              ↓
                                         model_router.py
                                              ↓
                                    CC SDK (Anthropic) → fail
                                              ↓
                                    Anthropic API → fail (401)
                                              ↓
                                    Gemini → fail (429)
                                              ↓
                                    Ollama (qwen2.5:0.5b) → response
                                              ↓
                                    quality_score: 0.35
```

Ollama is the **last-resort fallback**. It ensures EOS always has SOME intelligence available, even when all cloud providers are down. The quality is significantly lower than Gemini or Claude, but a mediocre response beats no response.

### Natural complements
- **Docker** — Ollama runs on host, Docker services connect via network. They coexist but compete for RAM.
- **Neon** — Ollama could generate embeddings for semantic search against Neon-stored data (not implemented in EOS yet).
- **Whisper** — Audio → text → Ollama → response. Local pipeline with no cloud dependency.

### When NOT to use Ollama
- CEO/strategic tasks → always use best available (Opus/Sonnet via `agent_type='ceo'`)
- Tasks requiring long context (>2K tokens with 0.5b) → cloud models only
- Tasks requiring factual accuracy → cloud models have better knowledge
- High-stakes content generation → quality gate score 0.35 is too low

### Alternatives in the same space
- **llama.cpp server** — lower-level, more control, no model management. Use when you need custom inference parameters.
- **vLLM** — GPU-focused, higher throughput for batch workloads. Overkill for single-user EOS.
- **LocalAI** — OpenAI-compatible API wrapper for multiple backends. More complex, more features.
- **LM Studio** — Desktop GUI. Not applicable for VPS.

## Trajectory and Evolution

### Recent changes (2025-2026)
- **Tool calling support** — `/api/chat` now supports function calling for compatible models
- **Structured outputs** — JSON schema validation in `format` parameter
- **Fill-in-middle** — `suffix` parameter for code completion
- **Vision support** — Multimodal models via `images` parameter
- **Model creation from safetensors** — Direct import without manual GGUF conversion
- **Improved quantization** — Support for newer GGUF quantization levels (IQ, Q4_K variants)

### Direction
- **Performance** — Flash attention, speculative decoding, KV cache optimization
- **Multi-GPU** — Better support for model parallelism across GPUs
- **API compatibility** — More OpenAI-compatible endpoints
- **Model ecosystem** — Larger registry, more official model variants
- **Running models as services** — Longer-term plans for daemon-managed model lifecycles

### Deprecation risks
- None currently. The API is stable and unversioned.
- Old GGUF versions may require re-pulling models after Ollama updates.
- llama.cpp upstream changes occasionally require Ollama updates for new model architectures.

## Conceptual Model and Solution Recipes

### Mental model
Think of Ollama as **a local model server** with three operations:
1. **Manage** — pull, list, create, delete models (like Docker images)
2. **Generate** — send prompt, get completion (stateless per request)
3. **Configure** — parameters control quality/speed/memory tradeoffs

### Recipe: EOS fallback generation
```python
# Standard EOS pattern via model_router.py
from eos_ai.model_router import call_with_fallback

result = call_with_fallback(
    prompt="Analyze this sales conversation",
    system="You are a sales analyst.",
    max_tokens=500,
    task_type="analysis",
)
# result.provider tells you which model was used
# If "ollama", quality is lower — flag if needed
```

### Recipe: Check Ollama health
```bash
# Is Ollama running?
curl -s http://localhost:11434/ && echo "OK" || echo "DOWN"

# What models are available?
curl -s http://localhost:11434/api/tags | python3 -c "
import sys, json
for m in json.load(sys.stdin)['models']:
    print(f'{m[\"name\"]} — {m[\"details\"][\"parameter_size\"]} — {m[\"details\"][\"quantization_level\"]}')"

# What's loaded in RAM?
curl -s http://localhost:11434/api/ps | python3 -m json.tool

# System resources
free -h && echo "---" && docker stats --no-stream
```

### Recipe: Create custom EOS model
```bash
cat > /tmp/eos-sales.modelfile << 'EOF'
FROM qwen2.5:0.5b
SYSTEM You are a sales conversation assistant for Initiate Arena. Keep replies under 3 sentences. Be direct.
PARAMETER temperature 0.3
PARAMETER num_predict 200
PARAMETER num_ctx 2048
EOF

curl -s http://localhost:11434/api/create \
  -d '{"name":"eos-sales","modelfile":"'"$(cat /tmp/eos-sales.modelfile)"'","stream":false}'
```

### Recipe: Switch active model (with safety)
```bash
# 1. Check current RAM
free -h
docker stats --no-stream

# 2. Pull new model (downloads only, doesn't load)
ollama pull qwen2.5:7b

# 3. Update model_router.py model_id
# 4. Restart Docker services to pick up change
docker restart os-discord os-bot os-webhook
sleep 15
docker logs os-discord --tail 5
```

### Recipe: Performance baseline
```bash
# Generate 100 tokens and measure speed
curl -s -w "\nTotal: %{time_total}s\n" http://localhost:11434/api/generate \
  -d '{"model":"qwen2.5:0.5b","prompt":"Write a paragraph about AI.","stream":false,"options":{"num_predict":100}}' \
  | python3 -c "
import sys, json
d = json.load(sys.stdin)
eval_dur = d.get('eval_duration', 1) / 1e9
eval_count = d.get('eval_count', 0)
print(f'Tokens: {eval_count}')
print(f'Speed: {eval_count/eval_dur:.1f} tok/s')
print(f'Load: {d.get(\"load_duration\", 0)/1e9:.2f}s')
"
```

## Industry Expert and Cutting-Edge Usage

### Pattern: Warm model with keep_alive
Keep the model loaded permanently to eliminate cold start latency:
```bash
curl http://localhost:11434/api/generate -d '{"model":"qwen2.5:0.5b","prompt":"warmup","keep_alive":"24h","stream":false}'
```
Run this on cron every 23 hours. Model stays in RAM, every request starts instantly.

### Pattern: Structured output for reliable parsing
Instead of parsing free-text LLM output, enforce JSON schema:
```python
payload = {
    "model": "qwen2.5:0.5b",
    "prompt": "Classify this message: 'I want to sign up'",
    "format": {
        "type": "object",
        "properties": {
            "intent": {"type": "string", "enum": ["interested", "not_interested", "question"]},
            "confidence": {"type": "number"}
        },
        "required": ["intent", "confidence"]
    },
    "stream": False
}
```
Ollama guarantees the response matches the schema. Eliminates JSON parse failures.

### Pattern: Local embeddings for privacy-sensitive data
Use `/api/embed` for vectors that never leave the VPS:
```python
resp = requests.post(f"{base}/api/embed", json={
    "model": "qwen2.5:0.5b",
    "input": ["customer conversation text"]
})
vector = resp.json()["embeddings"][0]
# Store in Neon with pgvector for semantic search
```

### Pattern: Model switching based on task complexity
```python
def get_ollama_model(task_type):
    """Use 7b for complex tasks (if available), 0.5b for simple ones."""
    if task_type in ("analysis", "strategy", "writing"):
        # Check if 7b is available and RAM allows
        ps = requests.get(f"{base}/api/ps").json()
        loaded = [m["name"] for m in ps.get("models", [])]
        if "qwen2.5:7b" in loaded or free_ram_gb() > 6:
            return "qwen2.5:7b"
    return "qwen2.5:0.5b"
```

### Pattern: Graceful degradation messaging
When Ollama is the active provider, tell the user:
```python
if result.provider == "ollama":
    result.output += "\n\n_[Running on local AI — response quality may be limited]_"
```
EOS doesn't do this yet — but should, to set expectations.

---

## EOS Usage Patterns

### Fallback chain position
```
CC SDK → Anthropic API → Gemini → Ollama
                                    ↑
                            quality_score: 0.35
                            cost_per_1k: $0.00
                            fallback_priority: 5
```

### model_router.py integration
- Config key: `"ollama-qwen"` in `MODEL_REGISTRY`
- Model ID: `qwen2.5:0.5b`
- Base URL: `os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")`
- Health check: `_ollama_available()` — GET `/api/tags` with 2s timeout
- Call method: `_call_ollama()` — POST `/api/generate` with 300s timeout
- Prompt truncation: prompt[:4000], system[:3000]
- Token tracking: `prompt_eval_count` and `eval_count` from response

### Current model inventory (VPS)
| Model | Size | Status |
|-------|------|--------|
| qwen2.5:0.5b | 397MB | Active — in fallback chain |
| qwen2.5:7b | 4.7GB | Pulled — not in fallback chain (RAM constraint) |

### Docker access pattern
All Docker services reach Ollama via:
```yaml
# docker-compose.yml
extra_hosts:
  - "host.docker.internal:host-gateway"
environment:
  - OLLAMA_BASE_URL=http://host.docker.internal:11434
```

## Gotchas

### qwen2.5:3b OOM (RESOLVED)
Tried running 3b model alongside Docker services. Total RAM exceeded VPS capacity. Exit code 137 on multiple containers. Fixed by switching to 0.5b. The 3b model was removed: `ollama rm qwen2.5:3b`.

### System prompt timeout with 0.5b (ACTIVE)
Long system prompts (>1500 chars) cause 0.5b to time out. The model's small context window fills with system prompt, leaving minimal room for prompt processing and generation. EOS truncates to 3000 chars in `_call_ollama` — this is safe for 7b but borderline for 0.5b. May need further truncation to 1500 chars.

### Model name mismatch after pull
`ollama pull qwen2.5:0.5b` stores the model as `qwen2.5:0.5b`. But `MODEL_REGISTRY` in model_router.py must reference the exact same string. If you pull `qwen2.5:latest` and reference `qwen2.5:0.5b`, it fails with 404.

### Docker services don't pick up model changes
The model_id is resolved at import time from `MODEL_REGISTRY`. Changing the Ollama model on the host (e.g., swapping 0.5b → 7b in code) requires restarting Docker services: `docker restart os-discord os-bot os-webhook`.

### Duration fields are nanoseconds
`total_duration`, `load_duration`, `eval_duration` are all in **nanoseconds**. Dividing by 1000 gives microseconds, not milliseconds. Divide by 1e9 for seconds. This has caused confusing "0ms latency" logs when someone divides by 1000 instead of 1e9.

### Empty response on valid request
Occasionally, 0.5b returns an empty `response` field on a valid 200 OK. This happens when the model generates only whitespace or stop tokens. EOS handles this with `data.get("response", "")` which falls through to the next provider.
