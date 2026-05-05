---
type: codebase-function
file: core/tool_mastery_research_agent/source_quality.py
line: 355
generated: 2026-04-12
---

# classify_quality

**File:** [[core-tool_mastery_research_agent-source_quality-py]] | **Line:** 355
**Signature:** `classify_quality(reports) → str`

Derive a run-level quality flag from per-source signal reports.

Rules:
    - zero passing sources          → "low"
    - all passing sources           → "high"
...
