---
type: codebase-function
file: eos_ai/substrate/perception.py
line: 813
generated: 2026-05-07
---

# collect_local_control_perception

**File:** [[eos_ai-substrate-perception-py]] | **Line:** 813
**Signature:** `collect_local_control_perception() → list[PerceptionRecord]`

Inspect local control for blocked/failed requests.

Detects:
- Requests blocked by current control mode
- Failed requests in the last 24 hours

## Calls

- [[eos_ai-substrate-perception-py-PerceptionRecord-new]]
- [[eos_ai-substrate-perception-py-PerceptionStore-all]]
- [[eos_ai-substrate-perception-py-PerceptionStore-default]]
- [[eos_ai-substrate-perception-py-_log]]
- [[eos_ai-substrate-perception-py-_now]]
