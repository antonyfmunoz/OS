---
type: codebase-function
file: core/tool_mastery_research_agent/source_quality.py
line: 266
generated: 2026-05-07
---

# measure_signal

**File:** [[core-tool_mastery_research_agent-source_quality-py]] | **Line:** 266
**Signature:** `measure_signal() → SignalReport`

Measure how much human-readable technical prose a capture contains.

Uses the SAME sanitizer and prose detector the Author Agent uses,
so research and author agree on what counts as usable. We import
lazily to keep this module dependency-light at import time.

## Calls

- [[core-tool_mastery_research_agent-source_quality-py-_is_raw_text_source]]
