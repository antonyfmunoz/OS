---
name: anthropic-api-tool
description: "Anthropic API integration for EOS. Use when any agent needs to call Claude models for generation, classification, or analysis tasks."
allowed-tools: "Read, Bash"
version: 1.0
source_url: "https://docs.anthropic.com/en/api/getting-started"
last_researched: "2026-04-01"
effort: low
trigger: both
context: fork
---

# Tool: Anthropic API

## What This Tool Does
The Anthropic API provides access to Claude models (Haiku, Sonnet, Opus) for text generation,
classification, tool use, and vision tasks.

EOS uses it via agent_runtime.py as the primary intelligence layer.

## EOS Integration
- agent_runtime.py handles all model routing
- model_router.py selects model based on task type and cost
- Current: Qwen 2.5:3b (local Ollama) as fallback when Anthropic credits depleted
- model_preferences.py maps task types to preferred models

## Key Models in Use
- claude-haiku-4-5: scoring, classification, fast tasks
- claude-sonnet-4-6: generation, complex reasoning
- claude-opus-4-6: architecture and review (expensive — use sparingly)

## Quick Reference
```python
import anthropic

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

message = client.messages.create(
    model="claude-sonnet-4-6",
    max_tokens=1024,
    messages=[{"role": "user", "content": "Hello"}]
)
print(message.content[0].text)
```

See references/best_practices.md for tool use, rate limits, and cost management.


## Gotchas
- Add failures here as they occur.
- This section compounds over time.
