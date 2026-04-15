---
type: codebase-function
file: eos_ai/substrate/resource_guard.py
line: 118
generated: 2026-04-12
---

# current_resource_snapshot

**File:** [[eos_ai-substrate-resource_guard-py]] | **Line:** 118
**Signature:** `current_resource_snapshot() → dict[str, Any]`

Collect a cheap point-in-time resource snapshot.

Uses only stdlib and /proc — no psutil.  Returns a partial dict
if /proc is unavailable (fail-safe).

## Calls

- [[eos_ai-substrate-resource_guard-py-_count_processes]]
- [[eos_ai-substrate-resource_guard-py-_parse_meminfo]]

## Called By

- [[eos_ai-substrate-resource_guard-py-evaluate_resource_guard]]
