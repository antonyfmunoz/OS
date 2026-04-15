---
type: codebase-function
file: eos_ai/substrate/meeting_intelligence.py
line: 1978
generated: 2026-04-12
---

# build_linkage_snapshot

**File:** [[eos_ai-substrate-meeting_intelligence-py]] | **Line:** 1978
**Signature:** `build_linkage_snapshot(summary) → dict[str, Any]`

Build a stable, versioned Product Linkage snapshot for the given summary.

Pure transform. Side-effect free. Always returns a fully-populated dict
conforming to LINKAGE_SCHEMA_VERSION. Degrades safely on any failure.

## Calls

- [[eos_ai-substrate-meeting_intelligence-py-_MeetingSummaryStore-get]]
- [[eos_ai-substrate-meeting_intelligence-py-_empty_linkage_snapshot]]
- [[eos_ai-substrate-meeting_intelligence-py-_log]]
- [[eos_ai-substrate-meeting_intelligence-py-_normalize_actionable_item]]
- [[eos_ai-substrate-meeting_intelligence-py-execution_linkage_block]]
- [[eos_ai-substrate-meeting_intelligence-py-is_followup_in_cooldown]]
- [[eos_ai-substrate-meeting_intelligence-py-next_followup_eligible_ts]]
- [[eos_ai-substrate-meeting_intelligence-py-oldest_unresolved_commitment_age_seconds]]
- [[eos_ai-substrate-meeting_intelligence-py-ownership_distribution]]
- [[eos_ai-substrate-meeting_intelligence-py-ownership_pressure_hint]]
- [[eos_ai-substrate-meeting_intelligence-py-stale_commitments_count]]
- [[eos_ai-substrate-meeting_intelligence-py-stale_open_loops_count]]
- [[eos_ai-substrate-meeting_intelligence-py-temporal_health]]
- [[eos_ai-substrate-meeting_intelligence-py-unassigned_commitments_count]]
- [[eos_ai-substrate-meeting_intelligence-py-unresolved_commitments]]

## Called By

- [[eos_ai-substrate-meeting_intelligence-py-linkage_snapshot]]
