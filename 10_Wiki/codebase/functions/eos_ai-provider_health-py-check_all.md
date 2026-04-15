---
type: codebase-function
file: eos_ai/provider_health.py
line: 175
generated: 2026-04-12
---

# check_all

**File:** [[eos_ai-provider_health-py]] | **Line:** 175
**Signature:** `check_all() → ProviderHealth`

Run all provider checks. Designed to complete in under 15 seconds.

## Calls

- [[eos_ai-provider_health-py-check_anthropic]]
- [[eos_ai-provider_health-py-check_cc_sdk]]
- [[eos_ai-provider_health-py-check_gemini]]
- [[eos_ai-provider_health-py-check_groq]]
- [[eos_ai-provider_health-py-check_ollama]]
- [[eos_ai-provider_health-py-check_perplexity]]

## Called By

- [[eos_ai-provider_health-py-require_llm_or_skip]]
- [[scripts-eos_status-py-main]]
