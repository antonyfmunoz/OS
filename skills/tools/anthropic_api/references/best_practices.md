# Anthropic API — Creator-Level Best Practices
Source: https://docs.anthropic.com/en/api
API Version: 2023-06-01 (anthropic-version header)
SDK Version: anthropic 0.49+ (Python)
Last Researched: 2026-04-04

---

# Tier 1 — Technical Mastery

## Authentication

### API key
Format: `sk-ant-api03-{random}` (starts with `sk-ant-api03-`).
Generated at: console.anthropic.com → API Keys.

```python
import anthropic, os

# Standard initialization
client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

# Will also read from ANTHROPIC_API_KEY env var automatically:
client = anthropic.Anthropic()  # reads env var
```

### HTTP headers (raw HTTP — not used by EOS)
```
POST https://api.anthropic.com/v1/messages
x-api-key: sk-ant-api03-...
anthropic-version: 2023-06-01
content-type: application/json
```

### Key security
- Never commit keys to git (always .env)
- Keys are org-scoped — one key gives access to all models on the account
- Rotate keys at console.anthropic.com if compromised
- EOS stores in `eos_ai/.env` and `services/.env` (same value in both)
- Injected into Docker containers via `ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}` in compose.yml

## Core Operations with Exact Signatures

### POST /v1/messages (primary endpoint)
```python
response = client.messages.create(
    model: str,                         # required — e.g., "claude-sonnet-4-6"
    max_tokens: int,                    # required — max tokens to generate
    messages: list[dict],               # required — conversation turns
    system: str | list[dict] = None,    # system prompt (top-level, NOT a message role)
    temperature: float = 1.0,           # 0.0-1.0 (0 = deterministic, 1 = creative)
    top_p: float = None,                # nucleus sampling (don't combine with temperature)
    top_k: int = None,                  # top-k sampling
    stop_sequences: list[str] = None,   # custom stop strings
    stream: bool = False,               # SSE streaming
    metadata: dict = None,              # {"user_id": str} for abuse detection
    tools: list[dict] = None,           # tool definitions
    tool_choice: dict = None,           # {"type": "auto"|"any"|"tool"|"none"}
    thinking: dict = None,              # {"type": "enabled", "budget_tokens": int}
)

# Response object
response.id: str                        # "msg_..."
response.type: str                      # "message"
response.role: str                      # "assistant"
response.content: list[ContentBlock]    # text, tool_use, thinking blocks
response.model: str                     # model used
response.stop_reason: str               # "end_turn"|"max_tokens"|"stop_sequence"|"tool_use"
response.stop_sequence: str | None      # which stop sequence triggered
response.usage: Usage                   # token counts
    .input_tokens: int
    .output_tokens: int
    .cache_creation_input_tokens: int
    .cache_read_input_tokens: int
```

### Content block types in response
```python
# Text
{"type": "text", "text": "Hello!"}

# Tool use
{"type": "tool_use", "id": "toolu_...", "name": "func_name", "input": {...}}

# Thinking (extended thinking enabled)
{"type": "thinking", "thinking": "Let me reason through this..."}
```

### Message structure
```python
# Simple text
messages = [{"role": "user", "content": "Hello"}]

# Multi-turn
messages = [
    {"role": "user", "content": "Hello"},
    {"role": "assistant", "content": "Hi! How can I help?"},
    {"role": "user", "content": "What is AI?"},
]

# With content blocks (vision)
messages = [{
    "role": "user",
    "content": [
        {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": "..."}},
        {"type": "text", "text": "Describe this image."},
    ],
}]

# Tool result
messages = [
    {"role": "user", "content": "What's the weather?"},
    {"role": "assistant", "content": [{"type": "tool_use", "id": "toolu_1", "name": "get_weather", "input": {"city": "Portland"}}]},
    {"role": "user", "content": [{"type": "tool_result", "tool_use_id": "toolu_1", "content": "72°F, sunny"}]},
]
```

### Streaming
```python
# Stream helper (recommended)
with client.messages.stream(
    model="claude-sonnet-4-6",
    max_tokens=1000,
    messages=[{"role": "user", "content": "Hello"}],
) as stream:
    for text in stream.text_stream:
        print(text, end="", flush=True)
    final_message = stream.get_final_message()

# Raw SSE
stream = client.messages.create(
    model="claude-sonnet-4-6",
    max_tokens=1000,
    messages=[{"role": "user", "content": "Hello"}],
    stream=True,
)
for event in stream:
    if event.type == "content_block_delta":
        print(event.delta.text, end="", flush=True)
```

### Batch API (50% off)
```python
batch = client.messages.batches.create(
    requests=[
        {"custom_id": "req1", "params": {"model": "claude-haiku-4-5-20251001", "max_tokens": 100, "messages": [...]}},
        {"custom_id": "req2", "params": {"model": "claude-haiku-4-5-20251001", "max_tokens": 100, "messages": [...]}},
    ]
)
# Poll: client.messages.batches.retrieve(batch.id)
# Results: client.messages.batches.results(batch.id)
```

## Pagination Patterns

N/A for the Messages API — each call is a single request/response.

The Batch API returns results as a downloadable JSONL file, not paginated.

Message history for multi-turn conversations must be managed client-side — Anthropic does not store conversation state.

## Rate Limits

### Tier-based limits (token bucket algorithm)
| Tier | Qualification | RPM | ITPM | OTPM |
|------|--------------|-----|------|------|
| Tier 1 | $5 credit purchase | 50 | 30,000 | 10,000 |
| Tier 2 | $40 credit purchase | 1,000 | 80,000 | 40,000 |
| Tier 3 | $200 credit purchase | 2,000 | 400,000 | 80,000 |
| Tier 4 | $400 credit purchase | 4,000 | 2,000,000 | 400,000 |

RPM = requests per minute. ITPM = input tokens per minute. OTPM = output tokens per minute.

### Rate limit headers
```
anthropic-ratelimit-requests-limit: 50
anthropic-ratelimit-requests-remaining: 49
anthropic-ratelimit-requests-reset: 2026-04-04T00:01:00Z
anthropic-ratelimit-tokens-limit: 30000
anthropic-ratelimit-tokens-remaining: 29500
anthropic-ratelimit-tokens-reset: 2026-04-04T00:01:00Z
retry-after: 30  # seconds (only on 429)
```

### Caching and rate limits
Cached tokens (via `cache_control`) do NOT count against ITPM. With 80% cache hit rate, effective ITPM capacity is 5x the stated limit.

### EOS tier
EOS is currently on Tier 1 (50 RPM, 30K ITPM). More than sufficient for single-founder usage with Gemini as primary provider.

## Error Codes and Recovery

| Code | Type | Meaning | Recovery |
|------|------|---------|----------|
| 400 | `invalid_request_error` | Malformed request, missing required params, bad content | Fix request |
| 401 | `authentication_error` | Invalid or missing API key | Check ANTHROPIC_API_KEY in .env |
| 403 | `permission_error` | Key lacks permission for this operation | Check key permissions at console |
| 404 | `not_found_error` | Model not found or resource doesn't exist | Check model name spelling |
| 413 | `request_too_large` | Request body exceeds limits | Reduce input size |
| 429 | `rate_limit_error` | Rate limit exceeded | Exponential backoff, respect retry-after |
| 500 | `api_error` | Anthropic internal error | Retry with backoff |
| 529 | `overloaded_error` | API temporarily overloaded | Retry with backoff, may last minutes |

### Error response shape
```json
{
  "type": "error",
  "error": {
    "type": "authentication_error",
    "message": "Your API key is invalid."
  }
}
```

### EOS error handling (model_router.py)
```python
except Exception as e:
    err_str = str(e)
    if "credit balance is too low" in err_str or "Your credit balance" in err_str:
        # Mark ALL Anthropic models unavailable (shared billing)
        for cfg in MODEL_REGISTRY.values():
            if cfg.provider == ModelProvider.ANTHROPIC:
                cfg.available = False
    else:
        print(f"[ModelRouter] Anthropic error: {e}")
    return ""  # triggers fallback to next provider
```

**Known issue:** Current ANTHROPIC_API_KEY returns 401 (auth error), not credit depletion error. The credit check in model_router.py doesn't catch this pattern — it falls to the else branch and prints the error, still returning empty string (which triggers fallback correctly).

## SDK Idioms

### Python SDK initialization
```python
import anthropic

# Standard (reads ANTHROPIC_API_KEY from env)
client = anthropic.Anthropic()

# Explicit key
client = anthropic.Anthropic(api_key="sk-ant-api03-...")

# Custom base URL (for proxies)
client = anthropic.Anthropic(base_url="https://proxy.example.com")

# Async client
client = anthropic.AsyncAnthropic()
response = await client.messages.create(...)
```

### Response handling
```python
response = client.messages.create(...)

# Safe text extraction
text = response.content[0].text if response.content else ""

# Check for tool use
if response.stop_reason == "tool_use":
    for block in response.content:
        if block.type == "tool_use":
            tool_name = block.name
            tool_input = block.input
            # Execute tool, then continue conversation with tool_result

# Token tracking
input_tokens = response.usage.input_tokens
output_tokens = response.usage.output_tokens
```

### SDK retry behavior
The SDK has built-in retry with exponential backoff for 429, 500, and 529 errors. Default: 2 retries.
```python
client = anthropic.Anthropic(
    max_retries=3,
    timeout=60.0,  # seconds
)
```

### Typing and IDE support
```python
from anthropic.types import Message, ContentBlock, TextBlock, ToolUseBlock
```

## Anti-Patterns

1. **Using Opus for tasks Haiku can handle** — Opus is 20x more expensive than Haiku. Use Haiku for scoring, classification, summarization. Use Sonnet for generation. Reserve Opus for strategic/architectural decisions.

2. **Not setting max_tokens** — Required parameter. Omitting it raises 400. Always set explicitly based on expected output length.

3. **Putting system instructions in user messages** — Use the top-level `system` parameter. It's designed for persistent instructions that don't change between turns. Putting instructions in user messages wastes tokens and reduces effectiveness.

4. **Ignoring stop_reason** — `"max_tokens"` means the response was truncated. `"tool_use"` means you need to execute a tool and continue. Only `"end_turn"` means the model finished naturally.

5. **Retrying on every error** — 400 errors are permanent (bad request). Only retry 429 (rate limit), 500 (internal), and 529 (overloaded). The SDK handles this automatically.

6. **Not using prompt caching for repeated context** — If you send the same large system prompt on every request, you're paying full price each time. Add `cache_control` to save 90%.

7. **Hardcoding `anthropic.Anthropic()` in service files** — Always go through `model_router.call_with_fallback()` so the fallback chain works. Direct Anthropic calls bypass Gemini/Ollama fallback.

8. **Assuming response.content[0] is always text** — With tools enabled, the first content block may be thinking or tool_use. Always check block.type.

9. **Using temperature > 0 for classification tasks** — Classification, scoring, and structured extraction should use temperature=0 for consistency. EOS doesn't set temperature in model_router (defaults to 1.0) — should be 0.3-0.5 for analytical tasks.

10. **Not tracking token usage** — Without tracking, you can't optimize. EOS tracks via `_last_input_tokens` and `_last_output_tokens` in model_router.py, but doesn't aggregate across sessions yet.

## Data Model

### Request/response lifecycle
```
Client → POST /v1/messages → Anthropic API → Response
           │                                      │
           ├── model (which Claude)                ├── id (msg_...)
           ├── max_tokens (budget)                 ├── content (blocks)
           ├── messages (conversation)             ├── stop_reason
           ├── system (instructions)               ├── usage (tokens)
           └── tools (functions)                   └── model (actual model used)
```

### Content block types
| Type | Direction | Purpose |
|------|-----------|---------|
| `text` | Request + Response | Plain text content |
| `image` | Request only | Base64 or URL image for vision |
| `document` | Request only | PDF or text document |
| `tool_use` | Response only | Model wants to call a tool |
| `tool_result` | Request only | Result of tool execution |
| `thinking` | Response only | Extended thinking reasoning |

### Model hierarchy
```
Claude family
├── Opus 4.6     — most capable, strategic tasks, $5/$25 per 1M tokens
├── Sonnet 4.6   — balanced, generation/analysis, $3/$15 per 1M tokens
└── Haiku 4.5    — fastest, classification/scoring, $1/$5 per 1M tokens
```

### Conversation state
Anthropic is **stateless**. No conversation memory between requests. The full conversation history must be sent in every request via the `messages` array. Token cost grows linearly with conversation length.

## Webhooks and Events

N/A — The Messages API is synchronous request-response. No webhook system.

For streaming, the response uses Server-Sent Events (SSE):
```
event: message_start
data: {"type":"message_start","message":{"id":"msg_...","type":"message",...}}

event: content_block_start
data: {"type":"content_block_start","index":0,"content_block":{"type":"text","text":""}}

event: content_block_delta
data: {"type":"content_block_delta","index":0,"delta":{"type":"text_delta","text":"Hello"}}

event: content_block_stop
data: {"type":"content_block_stop","index":0}

event: message_stop
data: {"type":"message_stop"}
```

## Limits

| Resource | Limit |
|----------|-------|
| Max input tokens | 200K standard, 1M extended (model-dependent) |
| Max output tokens | 8,192 (Haiku), 64,000 (Sonnet/Opus with extended) |
| Messages per request | 100,000 |
| System prompt size | Shares input token limit |
| Image size | 20MB per image, max 100 images per request |
| Image resolution | Auto-resized to 1568px on longest edge |
| Tool definitions | Up to 128 tools per request |
| tool_use input | Max 1M characters |
| callback_data | 64 bytes (tool_use id) |
| Batch API | 100,000 requests per batch |
| Batch result TTL | 29 days |

### Model max tokens
| Model | Max Input | Max Output |
|-------|-----------|------------|
| claude-opus-4-6 | 200K | 32K (64K with extended thinking) |
| claude-sonnet-4-6 | 200K | 16K (64K with extended thinking) |
| claude-haiku-4-5 | 200K | 8K |

## Cost Model

### Pricing per 1M tokens (April 2026)
| Model | Input | Output | Cache Write | Cache Read |
|-------|-------|--------|-------------|------------|
| claude-opus-4-6 | $5.00 | $25.00 | $6.25 | $0.50 |
| claude-sonnet-4-6 | $3.00 | $15.00 | $3.75 | $0.30 |
| claude-haiku-4-5 | $1.00 | $5.00 | $1.25 | $0.10 |

### Batch API discount
50% off both input and output tokens. Combined with prompt caching: up to 95% savings.

### Cost optimization strategies
1. **Route by task type** — Use Haiku for classification/scoring ($1/M), Sonnet for generation ($3/M), Opus only for architecture ($5/M)
2. **Prompt caching** — Add `cache_control` to system prompts repeated across requests. First call pays cache write (1.25x), subsequent calls pay cache read (0.1x).
3. **Batch API** — For non-time-sensitive workloads (reporting, analysis), use batch for 50% off
4. **Token monitoring** — Track `usage.input_tokens` and `usage.output_tokens` per call

### EOS cost tracking
```python
# model_router.py stores per-call tokens:
self._last_input_tokens = response.usage.input_tokens
self._last_output_tokens = response.usage.output_tokens
# services/cost_tracker.py aggregates across calls
```

## Version Pinning

### API version
The `anthropic-version` header pins the API behavior. Current: `2023-06-01`.
New versions may change response format, error codes, or default behavior.
The SDK handles this automatically — it sends the version it was built for.

### SDK version
```
pip install anthropic>=0.49
```
The SDK follows semver. Breaking changes in major versions.
Pin in requirements.txt: `anthropic>=0.49,<1.0`

### Model versioning
- `claude-opus-4-6` — latest Opus
- `claude-sonnet-4-6` — latest Sonnet
- `claude-haiku-4-5-20251001` — date-pinned Haiku (stable)

Date-pinned models (`-20251001`) guarantee consistent behavior. Non-dated aliases (`claude-sonnet-4-6`) may update behavior with new releases.

### Deprecation policy
Anthropic provides at least 2 months notice before deprecating models. Deprecated models return a `deprecation` header in responses. Old models (Claude 3 family) are deprecated but still function with reduced SLA.

---

# Tier 2 — Creator Intelligence

## Design Intent and Tradeoffs

Anthropic's API design reflects their "AI safety first" philosophy:

1. **Messages API, not Completions** — Unlike OpenAI's original completions endpoint, Anthropic only offers a structured messages format. This forces conversation structure (alternating user/assistant turns) rather than free-form text completion. The design prevents many prompt injection patterns.

2. **System prompt as first-class parameter** — Not a message role, but a separate parameter. This creates a clear separation between developer instructions (system) and user content (messages). Safety systems treat them differently.

3. **Required max_tokens** — Unlike APIs that default to a large number, Anthropic forces you to declare your budget. This prevents accidental cost overruns and makes cost estimation deterministic.

4. **Thinking as separate content blocks** — Extended thinking reasoning appears as `{"type": "thinking"}` blocks, visually separated from the response. This transparency about the model's reasoning process is an Anthropic differentiator.

5. **Tool use built into the message protocol** — Tools are not a separate endpoint. They're content blocks in the conversation. `tool_use` in assistant messages, `tool_result` in user messages. This keeps the full tool interaction in conversation context.

6. **Stateless by design** — No conversation memory, no session tokens. Every request contains the full context. This means the API never knows more than what you send — a privacy feature, not a limitation.

## Problem-Solution Map and Hidden Capabilities

### "Response is truncated mid-sentence"
Cause: `max_tokens` too low. stop_reason is `"max_tokens"`.
Fix: Increase max_tokens. Or check `stop_reason` and make a continuation request passing the truncated response as an assistant message.

### "Model returns tool_use but I expected text"
Cause: Tools are defined and the model decided to use one.
Fix: If you only want text, don't pass `tools`. Or set `tool_choice: {"type": "none"}`.

### "Credits depleted but key seems valid"
Cause: 401 vs credit error ambiguity. The key exists but the account has no credits.
Fix: Check console.anthropic.com → Billing. The error message may say "authentication_error" when it's really a billing issue.

### "High latency on first request"
Cause: Cold start. Anthropic distributes load across GPUs.
Fix: Normal behavior. First request may be 2-5x slower than subsequent ones. Use streaming to improve perceived latency.

### Hidden capabilities
- **Prompt caching across requests** — Cache large system prompts with `cache_control: {"type": "ephemeral"}`. Cached content persists for 5 minutes. 90% cost reduction on repeated context.
- **Multi-image vision** — Send up to 100 images in a single request for comparison, analysis, or document processing.
- **Structured output** — Use `output_config` with a JSON schema to guarantee response format.
- **Extended thinking with adaptive mode** — `thinking: {"type": "adaptive"}` lets the model decide when to think deeply vs respond quickly.
- **Service tier routing** — `service_tier: "auto"` prioritizes your request for faster response at no extra cost when capacity is available.

## Operational Behavior and Edge Cases

### Token counting
Input tokens are counted before the request is processed. If the count exceeds the model's limit, a 400 error is returned. The SDK doesn't pre-count — the API rejects oversize requests.

### Context window saturation
As input grows, output quality decreases. Claude performs best when the relevant information is near the beginning or end of the context (the "lost in the middle" effect). For large contexts, front-load the most important content.

### Concurrent requests
Multiple concurrent requests to the same model are allowed up to your RPM limit. Each request is independent — no shared state. The token bucket refills continuously.

### Network timeouts
Anthropic's API can take 30-120 seconds for complex requests with large contexts or extended thinking. Set HTTP timeout accordingly. EOS uses the SDK's default timeout. For streaming, the connection stays open but tokens arrive continuously.

### Caching behavior
Prompt caching matches on exact byte-level content. Changing a single character in the cached section invalidates the cache. Cache TTL is 5 minutes (ephemeral) or up to 1 hour (configurable).

## Ecosystem Position and Composition

### Where Anthropic fits in EOS
```
User → Discord/Telegram → EOS Gateway → Agent Runtime → model_router.py
                                                              ↓
                                                    CC SDK (Claude Code)
                                                              ↓
                                                    Anthropic API (Sonnet/Haiku)
                                                              ↓ (if 401/429/depleted)
                                                    Gemini 2.5 Flash
                                                              ↓ (if 429)
                                                    Ollama qwen2.5:0.5b
```

Anthropic is the **primary intelligence provider** — highest quality score (0.80) in the chain. When Anthropic is available, it handles all strategic, generative, and analytical tasks.

### Natural complements
- **Gemini** — fallback when Anthropic is down. Comparable quality at lower cost but weaker at structured reasoning.
- **Ollama** — last-resort local fallback. Dramatically lower quality but zero cost and no network dependency.
- **Claude Code SDK** — higher-level interface that wraps the Anthropic API with agentic capabilities (file reading, code execution).

### When NOT to use Anthropic
- When Gemini is sufficient and cheaper (simple classification, quick responses)
- For embeddings (Gemini or local fastembed are cheaper)
- For real-time web search (use Perplexity or Google Search grounding)
- When rate limits are a concern (Gemini has more generous limits)

## Trajectory and Evolution

### Recent changes (2025-2026)
- **Claude 4.5/4.6 family** — significant cost reduction (67% cheaper than 4.1)
- **Extended thinking** — configurable reasoning budgets
- **Prompt caching** — 90% savings on repeated context
- **Tool use improvements** — parallel tool calls, web search tool, code execution tool
- **Batch API** — 50% off for async workloads
- **1M token context** — on Opus and Sonnet with extended context

### Direction
- **Agents** — Claude Code, Agent SDK, containerized agents
- **Multimodal** — video understanding, audio processing
- **Cost reduction** — each generation significantly cheaper than the last
- **Enterprise** — workspace management, SSO, audit logging

### Deprecation risks
- Claude 3 family models deprecated (still functional with reduced SLA)
- `anthropic-version: 2023-06-01` is the only version and likely to be replaced
- The old completion-style API was never offered — no deprecation risk there

## Conceptual Model and Solution Recipes

### Mental model
Think of the Anthropic API as **a conversation with a brilliant colleague**:
1. **System** — set the colleague's role and constraints (persistent context)
2. **Messages** — the conversation history (user questions, assistant responses)
3. **Tools** — capabilities the colleague can request (function calling)
4. **Max tokens** — a time budget for the response

### Recipe: EOS standard call via model_router
```python
from eos_ai.model_router import call_with_fallback, TaskType

result = call_with_fallback(
    task_type=TaskType.GENERATE,
    prompt="Write a follow-up message for this lead.",
    system="You are a sales conversation assistant.",
    max_tokens=500,
)
# result is a string — empty if all providers failed
# model_router handles Anthropic → Gemini → Ollama fallback
```

### Recipe: CEO override (force best model)
```python
result = call_with_fallback(
    task_type=TaskType.STRATEGIC,
    prompt="Should we pivot our pricing strategy?",
    system="You are the CEO advisor for Lyfe Institute.",
    max_tokens=2000,
    agent_type='ceo',  # bypasses economy mode
)
```

### Recipe: Classification with Haiku (cheapest)
```python
import anthropic, os

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
response = client.messages.create(
    model="claude-haiku-4-5-20251001",
    max_tokens=50,
    temperature=0,
    messages=[{"role": "user", "content": f"Classify this intent: '{message}'\nOptions: interested, not_interested, question, spam\nRespond with just the classification."}],
)
classification = response.content[0].text.strip()
```

### Recipe: Cost-optimized batch scoring
```python
# Batch API: 50% off, non-real-time
leads = [...]  # list of lead texts to score
requests = [
    {
        "custom_id": f"lead_{i}",
        "params": {
            "model": "claude-haiku-4-5-20251001",
            "max_tokens": 20,
            "temperature": 0,
            "messages": [{"role": "user", "content": f"Score this lead 1-10: {lead}"}],
        }
    }
    for i, lead in enumerate(leads)
]
batch = client.messages.batches.create(requests=requests)
```

## Industry Expert and Cutting-Edge Usage

### Pattern: Prompt caching for agent system prompts
EOS agents have long system prompts (soul docs + hierarchy context + business context). Cache them:
```python
response = client.messages.create(
    model="claude-sonnet-4-6",
    max_tokens=1000,
    system=[{
        "type": "text",
        "text": long_system_prompt,  # 2000+ tokens
        "cache_control": {"type": "ephemeral"},
    }],
    messages=messages,
)
# First call: pays 1.25x for cache creation
# Next calls within 5 min: pays 0.1x for cache read
# Net savings: 90% on system prompt tokens
```

### Pattern: Structured output for reliable parsing
```python
response = client.messages.create(
    model="claude-sonnet-4-6",
    max_tokens=500,
    output_config={"type": "json_schema", "schema": {
        "type": "object",
        "properties": {
            "intent": {"type": "string", "enum": ["interested", "not_interested", "question"]},
            "urgency": {"type": "integer", "minimum": 1, "maximum": 10},
            "suggested_reply": {"type": "string"},
        },
        "required": ["intent", "urgency", "suggested_reply"],
    }},
    messages=[{"role": "user", "content": f"Analyze this DM: {dm_text}"}],
)
import json
result = json.loads(response.content[0].text)
```

### Pattern: Extended thinking for complex decisions
```python
response = client.messages.create(
    model="claude-opus-4-6",
    max_tokens=8000,
    thinking={"type": "enabled", "budget_tokens": 4000},
    messages=[{"role": "user", "content": "Should we add a second offer tier to Initiate Arena?"}],
)
# Response includes thinking blocks (internal reasoning) + text blocks (final answer)
for block in response.content:
    if block.type == "thinking":
        print(f"[REASONING] {block.thinking[:200]}...")
    elif block.type == "text":
        print(f"[ANSWER] {block.text}")
```

### Pattern: Vision for competitor analysis
```python
import base64
from pathlib import Path

screenshots = ["competitor1.png", "competitor2.png", "competitor3.png"]
content = []
for ss in screenshots:
    data = base64.b64encode(Path(ss).read_bytes()).decode()
    content.append({"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": data}})
content.append({"type": "text", "text": "Compare these competitor landing pages. What tactics are they using? What can we learn?"})

response = client.messages.create(
    model="claude-sonnet-4-6",
    max_tokens=2000,
    messages=[{"role": "user", "content": content}],
)
```

---

## EOS Usage Patterns

### Fallback chain position
```
CC SDK → Anthropic API → Gemini → Ollama
              ↑
      quality_score: 0.80
      cost_per_1k: $0.00025 (Haiku) to $0.003 (Sonnet)
      fallback_priority: 1 (highest available)
```

### model_router.py integration
- Config keys: `"claude-haiku"`, `"claude-sonnet"` in MODEL_REGISTRY
- Provider priority: 1 (second only to CC SDK)
- Latency priority: 0 (fastest)
- Health check: key presence via `os.getenv("ANTHROPIC_API_KEY")`
- Call method: `_call_anthropic()` using `anthropic.Anthropic` client
- Error handling: credit depletion marks ALL Anthropic models unavailable

### CC_MODEL_MAP (task-type routing)
Strategic/Code/Plan → Opus 4.6
Analyze/Generate/Research/Conversation → Sonnet 4.6
Score/Classify/Summarize/Fast → Haiku 4.5

### Current status (April 2026)
ANTHROPIC_API_KEY returns 401 (authentication error). All Anthropic models are unavailable. Traffic falls through to Gemini (also 429) → Ollama (active).

## Gotchas

### 401 auth error vs credit depletion (ACTIVE)
model_router.py checks for "credit balance is too low" in error string, but the actual error from the current key is a 401 authentication_error. The code falls to the else branch, prints the error, and returns empty string — which correctly triggers fallback. But the error log is misleading.

### All Anthropic models share billing (BY DESIGN)
When credits are depleted, ALL models (Haiku, Sonnet, Opus) fail simultaneously. model_router.py correctly marks all Anthropic models unavailable on credit error.

### max_tokens required but easy to forget
Unlike Gemini and OpenAI which have defaults, Anthropic requires explicit max_tokens. Missing it returns 400. EOS passes max_tokens in all model_router calls.

### Temperature defaults to 1.0
Higher than most users expect. For analytical/classification tasks, should be 0-0.3. EOS doesn't override temperature in model_router — uses the default 1.0 for all tasks. This affects consistency of classification results.

### System prompt as array for caching
To use prompt caching, system must be an array of text blocks, not a plain string:
```python
# Won't cache:
system="You are helpful."
# Will cache:
system=[{"type": "text", "text": "You are helpful.", "cache_control": {"type": "ephemeral"}}]
```
EOS currently passes system as a plain string in model_router._call_anthropic — no caching benefit.
