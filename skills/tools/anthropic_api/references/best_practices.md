# Anthropic API — Best Practices
Source: https://docs.anthropic.com/en/api/getting-started
Last Researched: 2026-04-01

## Rate Limits (Tier 1)
- claude-haiku-4-5: 50 RPM, 50K TPM
- claude-sonnet-4-6: 50 RPM, 40K TPM
- claude-opus-4-6: 50 RPM, 20K TPM

## Best Practices (Official)
- Use the least powerful model that can handle the task
- Set max_tokens explicitly — don't rely on defaults
- Use system prompt for persistent instructions, not user turn
- Tool use: define tools precisely with clear descriptions
- Streaming for long responses when UX requires it

## Anti-Patterns (Official)
- Don't retry on every error — 529 means overloaded, backoff
- Don't put secrets in prompts
- Don't use Opus for tasks Haiku can handle

## EOS Model Routing (agent_runtime.py)
- GENERATE tasks → Sonnet
- SCORE/CLASSIFY tasks → Haiku
- REVIEW/ARCHITECTURE → Opus
- When credits depleted → Qwen 2.5:3b via Ollama

## Cost Management
- Track tokens per call in cost_log.json
- Haiku ~15x cheaper than Sonnet — route aggressively
- Opus only for code review and architecture decisions

## Common Failures and Fixes
- 401 error: ANTHROPIC_API_KEY missing or invalid — check eos_ai/.env
- 529 Overloaded: exponential backoff, then fallback to Qwen
- Context exceeded: chunk input or use summarization step first
