---
type: codebase-function
file: eos_ai/substrate/perception.py
line: 751
generated: 2026-05-07
---

# collect_station_presence_perception

**File:** [[eos_ai-substrate-perception-py]] | **Line:** 751
**Signature:** `collect_station_presence_perception() → list[PerceptionRecord]`

Inspect station presence for workstation-level issues.

Detects:
- Station mode AWAY while blocked operator tasks exist
- Local node restored (available changed to True with recent trigger)
...

## Calls

- [[eos_ai-substrate-perception-py-PerceptionRecord-new]]
- [[eos_ai-substrate-perception-py-PerceptionStore-default]]
- [[eos_ai-substrate-perception-py-PerceptionStore-get]]
- [[eos_ai-substrate-perception-py-_log]]
