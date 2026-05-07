---
type: codebase-function
file: eos_ai/substrate/perception.py
line: 396
generated: 2026-05-07
---

# collect_pipeline_perception

**File:** [[eos_ai-substrate-perception-py]] | **Line:** 396
**Signature:** `collect_pipeline_perception() → list[PerceptionRecord]`

Inspect pipeline system for blocked/failed state.

Detects:
- Pipelines in FAILED status
- Pipelines in WAITING_ON_OPERATOR status
...

## Calls

- [[eos_ai-substrate-perception-py-PerceptionRecord-new]]
- [[eos_ai-substrate-perception-py-PerceptionStore-all]]
- [[eos_ai-substrate-perception-py-PerceptionStore-default]]
- [[eos_ai-substrate-perception-py-_log]]
- [[eos_ai-substrate-perception-py-_now]]
