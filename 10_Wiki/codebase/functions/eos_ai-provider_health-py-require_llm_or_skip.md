---
type: codebase-function
file: eos_ai/provider_health.py
line: 166
generated: 2026-05-07
---

# require_llm_or_skip

**File:** [[eos_ai-provider_health-py]] | **Line:** 166
**Signature:** `require_llm_or_skip(job_name, log_path) → ProviderHealth`

Cron entry-point gate: returns ProviderHealth if at least one provider is up.
If none are up, prints a clear skip line and exits with status 0.

Usage in a cron script:
    from eos_ai.provider_health import require_llm_or_skip
...

## Calls

- [[eos_ai-provider_health-py-check_all]]
