---
name: anthropic_api
description: "Use when any agent needs Claude model calls for text generation, classification, analysis, tool use, vision, or extended thinking via the Anthropic Messages API."
allowed-tools: "Read, Bash"
version: 1.0
source_url: "https://docs.anthropic.com/en/api"
last_researched: "2026-04-04"
instantiated_from: templates/tools/_template/
api_version: "2023-06-01 (anthropic-version header)"
sdk_version: "anthropic 0.49+ (Python SDK)"
speed_category: "fast"
trigger: both
effort: medium
context: fork
---

# Tool: Anthropic API (Claude)

## What This Tool Does

The Anthropic API provides access to Claude models (Opus, Sonnet, Haiku) via the Messages API. It is EOS's highest-quality intelligence provider — used for generation, classification, analysis, tool use, vision, extended thinking, and code review.

Core capabilities:
- **Messages API** — POST /v1/messages with structured conversation turns
- **System prompts** — persistent instructions via top-level `system` parameter
- **Tool use** — function calling with JSON schema definitions
- **Vision** — image analysis via base64 or URL in content blocks
- **Extended thinking** — chain-of-thought reasoning with configurable token budgets
- **Streaming** — server-sent events for real-time token delivery
- **Prompt caching** — cache large system prompts/contexts for 90% cost reduction
- **Batch API** — 50% off for non-time-sensitive workloads

## EOS Integration

### Primary: model_router.py
- Provider priority: **CC_SDK (0) > Anthropic (1)** > Gemini (2) > Groq (3) > Ollama (5)
- Quality score: 0.80 (highest in the chain)
- Models registered:
  - `claude-haiku` → `claude-haiku-4-5-20251001` (scoring, classification, fast)
  - `claude-sonnet` → `claude-sonnet-4-6` (generation, analysis, conversation)
  - CC_MODEL_MAP routes task types to specific models (Opus for strategic, Haiku for fast)
- Cost tracking: Haiku $0.00025/1K, Sonnet $0.003/1K
- Called via `ModelRouter._call_anthropic()` using `anthropic.Anthropic` client

### CC_MODEL_MAP (task-type routing for Claude Code SDK)
```python
CC_MODEL_MAP = {
    TaskType.STRATEGIC: "claude-opus-4-6",
    TaskType.CODE: "claude-opus-4-6",
    TaskType.PLAN: "claude-opus-4-6",
    TaskType.ANALYZE: "claude-sonnet-4-6",
    TaskType.GENERATE: "claude-sonnet-4-6",
    TaskType.RESEARCH: "claude-sonnet-4-6",
    TaskType.SCORE: "claude-haiku-4-5-20251001",
    TaskType.CLASSIFY: "claude-haiku-4-5-20251001",
    TaskType.FAST_RESPONSE: "claude-haiku-4-5-20251001",
}
```

### Secondary: agent_runtime.py
- Exposes `client` property for services that manage their own Anthropic calls
- `_claude_available` flag for fallback when key is invalid/depleted
- Legacy compatibility layer used by dm_monitor.py and some services

### Other modules:
- `model_preferences.py` — business context routing preferences
- `cognitive_loop.py` — core PERCEIVE/GENERATE/ACT loop
- `services/cost_tracker.py` — per-call token and cost logging

## Authentication

### API Key
```python
# In eos_ai/.env
ANTHROPIC_API_KEY=sk-ant-api03-...

# In code — always load from env
import anthropic, os
client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
```

### HTTP headers
```
x-api-key: sk-ant-api03-...
anthropic-version: 2023-06-01
content-type: application/json
```

### Key management
- Keys generated at console.anthropic.com
- Start with `sk-ant-api03-` prefix
- One key per project recommended
- Stored in `eos_ai/.env` and `services/.env` (same value)
- Injected into Docker containers via `environment:` block in compose.yml

## Quick Reference

### Text generation (EOS standard — matches model_router._call_anthropic)
```python
import anthropic, os

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
response = client.messages.create(
    model="claude-sonnet-4-6",
    max_tokens=1000,
    system="You are a business analyst.",
    messages=[{"role": "user", "content": "Analyze this situation."}],
)
text = response.content[0].text
# Token tracking:
input_tokens = response.usage.input_tokens
output_tokens = response.usage.output_tokens
```

### Vision (image analysis)
```python
import base64
from pathlib import Path

image_data = base64.b64encode(Path("screenshot.png").read_bytes()).decode()
response = client.messages.create(
    model="claude-sonnet-4-6",
    max_tokens=500,
    messages=[{
        "role": "user",
        "content": [
            {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": image_data}},
            {"type": "text", "text": "What's in this image?"},
        ],
    }],
)
```

### Tool use
```python
response = client.messages.create(
    model="claude-sonnet-4-6",
    max_tokens=1000,
    tools=[{
        "name": "get_lead_status",
        "description": "Get the current status of a lead in the CRM pipeline.",
        "input_schema": {
            "type": "object",
            "properties": {"lead_id": {"type": "string"}},
            "required": ["lead_id"],
        },
    }],
    messages=[{"role": "user", "content": "What's the status of lead ABC?"}],
)
# Check stop_reason == "tool_use"
# Parse response.content for tool_use blocks
```

### Streaming
```python
with client.messages.stream(
    model="claude-sonnet-4-6",
    max_tokens=1000,
    messages=[{"role": "user", "content": "Write a market analysis."}],
) as stream:
    for text in stream.text_stream:
        print(text, end="", flush=True)
```

### Extended thinking
```python
response = client.messages.create(
    model="claude-sonnet-4-6",
    max_tokens=8000,
    thinking={"type": "enabled", "budget_tokens": 4000},
    messages=[{"role": "user", "content": "Solve this complex problem."}],
)
# response.content may include {"type": "thinking", "thinking": "..."}
# followed by {"type": "text", "text": "..."}
```

### Prompt caching (cost optimization)
```python
response = client.messages.create(
    model="claude-sonnet-4-6",
    max_tokens=1000,
    system=[
        {"type": "text", "text": large_system_prompt, "cache_control": {"type": "ephemeral"}},
    ],
    messages=[{"role": "user", "content": "Question about the system prompt."}],
)
# cache_creation_input_tokens on first call
# cache_read_input_tokens on subsequent calls (90% cheaper)
```

## Gotchas

### Anthropic key returns 401 auth error (ACTIVE)
Current ANTHROPIC_API_KEY returns authentication_error (401), not credit depletion. model_router.py checks for "credit balance is too low" in error string but the actual error is different. All Anthropic models are marked unavailable after first 401.

### Credit depletion marks all Anthropic models unavailable (BY DESIGN)
When any Anthropic call fails with credit error, `_call_anthropic` marks ALL Anthropic models (Haiku, Sonnet, Opus) unavailable for the session. They share one billing account.

### response.content[0].text assumes text block (FRAGILE)
If the model responds with a tool_use block instead of text, `response.content[0].text` throws AttributeError. Always check `response.stop_reason` and content block types.

### System prompt is NOT a message role
`system` is a top-level parameter on `messages.create()`, not a role in the messages array. Passing `{"role": "system", "content": "..."}` in messages raises 400 Bad Request.

### max_tokens is required, not optional
Unlike some APIs, Anthropic requires explicit `max_tokens`. No default. Omitting it raises 400.

### Economy mode forces Haiku (ACTIVE)
When business stage is `pre_revenue`, economy mode in model_preferences.py forces Haiku for most tasks. Override with `agent_type='ceo'` in `call_with_fallback()` for strategic tasks.

See references/best_practices.md for full API reference, rate limits, pricing, and anti-patterns.
