---
type: codebase-class
file: core/tool_mastery_manager/models.py
line: 15
generated: 2026-04-11
---

# CoverageStatus

**File:** [[core-tool_mastery_manager-models-py]] | **Line:** 15

Unified verdict for a single tool's mastery coverage.

Ordering reflects repair priority — READY is the only terminal "good"
state. All others represent work to be done.

## Inherits From

- `str`
- `Enum`

## Methods

- [[core-tool_mastery_manager-models-py-CoverageStatus-needs_work]]`() → bool` — 
