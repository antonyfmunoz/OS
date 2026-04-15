---
type: codebase-function
file: eos_ai/substrate/meeting_intelligence.py
line: 988
generated: 2026-04-12
---

# stale_commitments_count

**File:** [[eos_ai-substrate-meeting_intelligence-py]] | **Line:** 988
**Signature:** `stale_commitments_count(summary, now) → int`

Count of unresolved commitments older than COMMITMENT_STALE_SECONDS.

## Calls

- [[eos_ai-substrate-meeting_intelligence-py-commitment_age_seconds]]
- [[eos_ai-substrate-meeting_intelligence-py-unresolved_commitments]]

## Called By

- [[eos_ai-substrate-meeting_intelligence-py-build_linkage_snapshot]]
- [[eos_ai-substrate-meeting_intelligence-py-intelligence_report_block]]
- [[eos_ai-substrate-meeting_intelligence-py-temporal_health]]
