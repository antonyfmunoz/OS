---
type: codebase-function
file: core/memory_evolution.py
line: 249
generated: 2026-05-07
---

# MemorySystem.suggest_optimizations

**File:** [[core-memory_evolution-py]] | **Line:** 249
**Signature:** `suggest_optimizations() → list[dict[str, Any]]`

**Class:** [[core-memory_evolution-py-MemorySystem]]

Suggest primitive composition improvements based on history.

Analyses:
1. High-performing combinations → recommend reuse
2. Low-performing combinations → recommend transformation
...

## Calls

- [[core-memory_evolution-py-MemorySystem-extract_patterns]]
