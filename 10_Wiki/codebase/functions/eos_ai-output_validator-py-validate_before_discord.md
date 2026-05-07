---
type: codebase-function
file: eos_ai/output_validator.py
line: 288
generated: 2026-05-07
---

# validate_before_discord

**File:** [[eos_ai-output_validator-py]] | **Line:** 288
**Signature:** `validate_before_discord(content, context, ctx) → str`

Convenience function — call before ANY Discord post.

Validates content, logs violations, returns auto-fixed content
when a critical violation is found. Never blocks posting.

## Calls

- [[eos_ai-output_validator-py-OutputValidator-log_violation]]
- [[eos_ai-output_validator-py-OutputValidator-validate_discord_message]]
- [[eos_ai-output_validator-py-get_validator]]
