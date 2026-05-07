---
type: codebase-function
file: core/memory_evolution.py
line: 210
generated: 2026-05-07
---

# MemorySystem.extract_patterns

**File:** [[core-memory_evolution-py]] | **Line:** 210
**Signature:** `extract_patterns(min_occurrences) → list[PrimitivePattern]`

**Class:** [[core-memory_evolution-py-MemorySystem]]

Detect recurring primitive combinations across runs.

Groups runs by their primitive tag set and computes statistics
for each group.

## Called By

- [[core-memory_evolution-py-MemorySystem-rank_patterns]]
- [[core-memory_evolution-py-MemorySystem-suggest_optimizations]]
