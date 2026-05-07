---
type: codebase-function
file: eos_ai/provider_health.py
line: 151
generated: 2026-05-07
---

# check_all

**File:** [[eos_ai-provider_health-py]] | **Line:** 151
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
