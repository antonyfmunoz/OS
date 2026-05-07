---
type: codebase-function
file: eos_ai/substrate/perception.py
line: 871
generated: 2026-05-07
---

# collect_live_session_perception

**File:** [[eos_ai-substrate-perception-py]] | **Line:** 871
**Signature:** `collect_live_session_perception() → list[PerceptionRecord]`

Inspect live sessions for issues.

Detects:
- Live sessions paused for > 1 hour
- Live sessions in WAITING_ON_OPERATOR state
...

## Calls

- [[eos_ai-substrate-perception-py-PerceptionRecord-new]]
- [[eos_ai-substrate-perception-py-PerceptionStore-all]]
- [[eos_ai-substrate-perception-py-PerceptionStore-default]]
- [[eos_ai-substrate-perception-py-_log]]
- [[eos_ai-substrate-perception-py-_now]]
