---
type: codebase-function
file: eos_ai/trinity.py
line: 42
generated: 2026-05-07
---

# TrinityEngine.get_user_subscriptions

**File:** [[eos_ai-trinity-py]] | **Line:** 42
**Signature:** `get_user_subscriptions() → list[str]`

**Class:** [[eos_ai-trinity-py-TrinityEngine]]

Load OS subscriptions from BIS.
Defaults to EntrepreneurOS if not set or on any error.

## Called By

- [[eos_ai-trinity-py-TrinityEngine-format_for_prompt]]
- [[eos_ai-trinity-py-TrinityEngine-get_active_os_count]]
- [[eos_ai-trinity-py-TrinityEngine-get_cross_os_insight]]
- [[eos_ai-trinity-py-TrinityEngine-is_full_trinity]]
