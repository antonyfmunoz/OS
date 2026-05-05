---
type: codebase-function
file: eos_ai/model_router.py
line: 419
generated: 2026-04-12
---

# ModelRouter.call

**File:** [[eos_ai-model_router-py]] | **Line:** 419
**Signature:** `call(model_config, prompt, system, max_tokens) → str`

**Class:** [[eos_ai-model_router-py-ModelRouter]]

Universal model call — routes to correct API by provider.

## Calls

- [[eos_ai-model_router-py-ModelRouter-_call_anthropic]]
- [[eos_ai-model_router-py-ModelRouter-_call_gemini]]
- [[eos_ai-model_router-py-ModelRouter-_call_ollama]]
- [[eos_ai-model_router-py-ModelRouter-_call_openai_compatible]]

## Called By

- [[eos_ai-model_router-py-ModelRouter-call_with_fallback]]
- [[eos_ai-model_router-py-call_with_fallback]]
