---
type: codebase-function
file: eos_ai/substrate/meeting_intelligence.py
line: 1003
generated: 2026-04-12
---

# stale_open_loops_count

**File:** [[eos_ai-substrate-meeting_intelligence-py]] | **Line:** 1003
**Signature:** `stale_open_loops_count(summary, now) → int`

Stale open loops: open_loops exist, have aged past STALE_OPEN_LOOP_SECONDS
since first appearing without decisions catching up. Bounded by MAX_OPEN_LOOPS.

## Called By

- [[eos_ai-substrate-meeting_intelligence-py-build_linkage_snapshot]]
- [[eos_ai-substrate-meeting_intelligence-py-intelligence_report_block]]
- [[eos_ai-substrate-meeting_intelligence-py-project_actionable_items]]
- [[eos_ai-substrate-meeting_intelligence-py-temporal_health]]
