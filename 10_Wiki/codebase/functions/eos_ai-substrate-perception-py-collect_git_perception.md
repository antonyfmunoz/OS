---
type: codebase-function
file: eos_ai/substrate/perception.py
line: 619
generated: 2026-05-07
---

# collect_git_perception

**File:** [[eos_ai-substrate-perception-py]] | **Line:** 619
**Signature:** `collect_git_perception() → list[PerceptionRecord]`

Inspect git state (bounded, safe read-only).

Detects:
- Uncommitted changes count > 20 files
- Unpushed commits

## Calls

- [[eos_ai-substrate-perception-py-PerceptionRecord-new]]
- [[eos_ai-substrate-perception-py-_log]]
