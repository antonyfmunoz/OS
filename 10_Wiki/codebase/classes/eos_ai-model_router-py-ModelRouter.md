---
type: codebase-class
file: eos_ai/model_router.py
line: 364
generated: 2026-04-11
---

# ModelRouter

**File:** [[eos_ai-model_router-py]] | **Line:** 364

*No docstring.*

## Methods

- [[eos_ai-model_router-py-ModelRouter-__init__]]`(ctx) → None` — 
- [[eos_ai-model_router-py-ModelRouter-_check_availability]]`() → None` — 
- [[eos_ai-model_router-py-ModelRouter-route]]`(task_type, prefer_fast, prefer_cheap) → ModelConfig | None` — Select the best available model for the given task type.
- [[eos_ai-model_router-py-ModelRouter-call]]`(model_config, prompt, system, max_tokens) → str` — Universal model call — routes to correct API by provider.
- [[eos_ai-model_router-py-ModelRouter-call_with_fallback]]`(task_type, prompt, system, max_tokens) → str` — Try models in priority order until one returns a non-empty response.
- [[eos_ai-model_router-py-ModelRouter-_call_anthropic]]`(config, prompt, system, max_tokens) → str` — 
- [[eos_ai-model_router-py-ModelRouter-_call_openai_compatible]]`(config, prompt, system, max_tokens) → str` — Works for Perplexity, Groq, OpenAI — all OpenAI-compatible APIs.
- [[eos_ai-model_router-py-ModelRouter-_call_ollama]]`(config, prompt, system, max_tokens) → str` — 
- [[eos_ai-model_router-py-ModelRouter-_call_gemini]]`(config, prompt, system, max_tokens) → str` — 
- [[eos_ai-model_router-py-ModelRouter-get_status]]`() → str` — 
