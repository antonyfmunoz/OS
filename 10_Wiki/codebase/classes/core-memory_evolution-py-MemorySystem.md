---
type: codebase-class
file: core/memory_evolution.py
line: 115
generated: 2026-05-07
---

# MemorySystem

**File:** [[core-memory_evolution-py]] | **Line:** 115

Adaptive memory that learns from primitive-level execution history.

Operates entirely on primitives — not logs, not raw output.
Detects which primitive combinations succeed and suggests
improvements for future compositions.

## Methods

- [[core-memory_evolution-py-MemorySystem-__init__]]`(persist) → None` — 
- [[core-memory_evolution-py-MemorySystem-_load_history]]`() → None` — Load persisted run records from disk.
- [[core-memory_evolution-py-MemorySystem-_persist_run]]`(record) → None` — Append a single run record to disk.
- [[core-memory_evolution-py-MemorySystem-record_run]]`() → RunRecord` — Record a completed execution run.
- [[core-memory_evolution-py-MemorySystem-extract_patterns]]`(min_occurrences) → list[PrimitivePattern]` — Detect recurring primitive combinations across runs.
- [[core-memory_evolution-py-MemorySystem-rank_patterns]]`() → list[PrimitivePattern]` — Return patterns ranked by average score (best first).
- [[core-memory_evolution-py-MemorySystem-suggest_optimizations]]`() → list[dict[str, Any]]` — Suggest primitive composition improvements based on history.
- [[core-memory_evolution-py-MemorySystem-get_runs]]`(limit) → list[RunRecord]` — Return most recent runs.
- [[core-memory_evolution-py-MemorySystem-get_domain_stats]]`() → dict[str, dict[str, Any]]` — Aggregate statistics per domain type.
