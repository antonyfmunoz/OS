---
type: codebase-function
file: eos_ai/substrate/perception.py
line: 679
generated: 2026-05-07
---

# collect_runtime_log_perception

**File:** [[eos_ai-substrate-perception-py]] | **Line:** 679
**Signature:** `collect_runtime_log_perception() → list[PerceptionRecord]`

Inspect recent runtime logs for errors (bounded).

Reads last 100 lines of the most recent .log file in /opt/OS/logs/.
Looks for ERROR/CRITICAL patterns.

## Calls

- [[eos_ai-substrate-perception-py-PerceptionRecord-new]]
- [[eos_ai-substrate-perception-py-_log]]
