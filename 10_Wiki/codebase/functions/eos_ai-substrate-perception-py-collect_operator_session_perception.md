---
type: codebase-function
file: eos_ai/substrate/perception.py
line: 462
generated: 2026-05-07
---

# collect_operator_session_perception

**File:** [[eos_ai-substrate-perception-py]] | **Line:** 462
**Signature:** `collect_operator_session_perception() → list[PerceptionRecord]`

Inspect operator session state.

Detects:
- OVERNIGHT mode active for > 12 hours
- Day open for > 16 hours
...

## Calls

- [[eos_ai-substrate-perception-py-PerceptionRecord-new]]
- [[eos_ai-substrate-perception-py-PerceptionStore-default]]
- [[eos_ai-substrate-perception-py-PerceptionStore-get]]
- [[eos_ai-substrate-perception-py-_log]]
- [[eos_ai-substrate-perception-py-_now]]
