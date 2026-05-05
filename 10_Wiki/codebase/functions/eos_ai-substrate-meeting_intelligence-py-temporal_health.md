---
type: codebase-function
file: eos_ai/substrate/meeting_intelligence.py
line: 1051
generated: 2026-04-12
---

# temporal_health

**File:** [[eos_ai-substrate-meeting_intelligence-py]] | **Line:** 1051
**Signature:** `temporal_health(summary, now) → str`

Deterministic temporal quality signal for operator reporting.
Returns one of: "fresh" | "aging" | "stale".

## Calls

- [[eos_ai-substrate-meeting_intelligence-py-oldest_unresolved_commitment_age_seconds]]
- [[eos_ai-substrate-meeting_intelligence-py-stale_commitments_count]]
- [[eos_ai-substrate-meeting_intelligence-py-stale_open_loops_count]]

## Called By

- [[eos_ai-substrate-meeting_intelligence-py-build_linkage_snapshot]]
- [[eos_ai-substrate-meeting_intelligence-py-intelligence_report_block]]
