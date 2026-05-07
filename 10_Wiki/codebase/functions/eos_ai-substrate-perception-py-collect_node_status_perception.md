---
type: codebase-function
file: eos_ai/substrate/perception.py
line: 551
generated: 2026-05-07
---

# collect_node_status_perception

**File:** [[eos_ai-substrate-perception-py]] | **Line:** 551
**Signature:** `collect_node_status_perception() → list[PerceptionRecord]`

Inspect node registry for availability issues.

Detects:
- Nodes with status OFFLINE or DEGRADED
- Local station node not seen in > 1 hour

## Calls

- [[eos_ai-substrate-perception-py-PerceptionRecord-new]]
- [[eos_ai-substrate-perception-py-PerceptionStore-all]]
- [[eos_ai-substrate-perception-py-PerceptionStore-default]]
- [[eos_ai-substrate-perception-py-_log]]
- [[eos_ai-substrate-perception-py-_now]]
