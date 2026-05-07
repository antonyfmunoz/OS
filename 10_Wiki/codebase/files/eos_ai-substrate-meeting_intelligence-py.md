---
type: codebase-file
path: eos_ai/substrate/meeting_intelligence.py
module: eos_ai.substrate.meeting_intelligence
lines: 2181
size: 84671
generated: 2026-05-07
---

# eos_ai/substrate/meeting_intelligence.py

Meeting Intelligence Layer v1 — bounded, additive, deterministic.

Sits on top of the existing meeting_transport pipeline:

    inject_transcript → voice_session → responder → SPEAK_TEXT
...

**Lines:** 2181 | **Size:** 84,671 bytes

## Contains

- **class** [[eos_ai-substrate-meeting_intelligence-py-Commitment]] — 1 methods
- **class** [[eos_ai-substrate-meeting_intelligence-py-ActionableItem]] — 1 methods
- **class** [[eos_ai-substrate-meeting_intelligence-py-MeetingSummary]] — 1 methods
- **class** [[eos_ai-substrate-meeting_intelligence-py-ExtractedMemory]] — 1 methods
- **class** [[eos_ai-substrate-meeting_intelligence-py-_MeetingSummaryStore]] — 10 methods
- **fn** [[eos_ai-substrate-meeting_intelligence-py-_log]]`(msg) → None`
- **fn** [[eos_ai-substrate-meeting_intelligence-py-get_meeting_summary_store]]`() → _MeetingSummaryStore`
- **fn** [[eos_ai-substrate-meeting_intelligence-py-reset_meeting_summary_store_for_tests]]`() → None`
- **fn** [[eos_ai-substrate-meeting_intelligence-py-_cap_list]]`(items, cap) → list[str]`
- **fn** [[eos_ai-substrate-meeting_intelligence-py-_extract_json_block]]`(text) → Optional[dict]`
- **fn** [[eos_ai-substrate-meeting_intelligence-py-_fallback_summary]]`(previous, utterances) → dict[str, list[str]]`
- **fn** [[eos_ai-substrate-meeting_intelligence-py-_build_prompt]]`(previous, utterances) → tuple[str, str]`
- **fn** [[eos_ai-substrate-meeting_intelligence-py-update_meeting_summary]]`(node_id, meeting_id, utterances) → dict[str, Any]`
- **fn** [[eos_ai-substrate-meeting_intelligence-py-_count_ambiguity_overlaps]]`(key_points) → int`
- **fn** [[eos_ai-substrate-meeting_intelligence-py-compute_scores]]`(summary) → None`
- **fn** [[eos_ai-substrate-meeting_intelligence-py-_infer_ownership]]`(low_text, raw_text, speaker) → tuple[Optional[str], str]`
- **fn** [[eos_ai-substrate-meeting_intelligence-py-extract_commitments]]`(utterances) → list[Commitment]`
- **fn** [[eos_ai-substrate-meeting_intelligence-py-_merge_commitments]]`(existing, new_items) → list[dict]`
- **fn** [[eos_ai-substrate-meeting_intelligence-py-_tokens]]`(text) → set[str]`
- **fn** [[eos_ai-substrate-meeting_intelligence-py-resolve_commitments]]`(summary, utterances) → list[dict]`
- **fn** [[eos_ai-substrate-meeting_intelligence-py-_apply_pressure_decay]]`(summary, resolved_delta) → None`
- **fn** [[eos_ai-substrate-meeting_intelligence-py-_update_escalation_trend]]`(summary) → None`
- **fn** [[eos_ai-substrate-meeting_intelligence-py-unresolved_commitments]]`(summary) → list[dict]`
- **fn** [[eos_ai-substrate-meeting_intelligence-py-ownership_distribution]]`(summary) → dict[str, int]`
- **fn** [[eos_ai-substrate-meeting_intelligence-py-unassigned_commitments_count]]`(summary) → int`
- **fn** [[eos_ai-substrate-meeting_intelligence-py-ownership_pressure_hint]]`(summary) → str`
- **fn** [[eos_ai-substrate-meeting_intelligence-py-compute_escalation_level]]`(summary) → str`
- **fn** [[eos_ai-substrate-meeting_intelligence-py-commitment_age_seconds]]`(commitment, now) → float`
- **fn** [[eos_ai-substrate-meeting_intelligence-py-oldest_unresolved_commitment_age_seconds]]`(summary, now) → float`
- **fn** [[eos_ai-substrate-meeting_intelligence-py-stale_commitments_count]]`(summary, now) → int`
- **fn** [[eos_ai-substrate-meeting_intelligence-py-stale_open_loops_count]]`(summary, now) → int`
- **fn** [[eos_ai-substrate-meeting_intelligence-py-next_followup_eligible_ts]]`(summary) → Optional[float]`
- **fn** [[eos_ai-substrate-meeting_intelligence-py-is_followup_in_cooldown]]`(summary, now) → bool`
- **fn** [[eos_ai-substrate-meeting_intelligence-py-temporal_health]]`(summary, now) → str`
- **fn** [[eos_ai-substrate-meeting_intelligence-py-detect_follow_up]]`(summary) → Optional[dict]`
- **fn** [[eos_ai-substrate-meeting_intelligence-py-_has_repeated_topic]]`(key_points) → bool`
- **fn** [[eos_ai-substrate-meeting_intelligence-py-detect_intervention]]`(summary) → Optional[dict]`
- **fn** [[eos_ai-substrate-meeting_intelligence-py-_normalize_role]]`(role_slug) → Optional[str]`
- **fn** [[eos_ai-substrate-meeting_intelligence-py-derive_active_role]]`(node_id) → Optional[str]`
- **fn** [[eos_ai-substrate-meeting_intelligence-py-refine_intervention_message]]`(raw_message, role_slug, summary) → str`
- **fn** [[eos_ai-substrate-meeting_intelligence-py-maybe_emit_intervention]]`(node_id, meeting_id, summary) → Optional[dict]`
- **fn** [[eos_ai-substrate-meeting_intelligence-py-extract_memory]]`(summary) → list[ExtractedMemory]`
- **fn** [[eos_ai-substrate-meeting_intelligence-py-on_utterance_injected]]`(node_id, meeting_id, recent_utterances) → None`
- **fn** [[eos_ai-substrate-meeting_intelligence-py-_memory_counts_by_type]]`(memories) → dict[str, int]`
- **fn** [[eos_ai-substrate-meeting_intelligence-py-classify_execution_readiness]]`(item) → dict[str, Any]`
- **fn** [[eos_ai-substrate-meeting_intelligence-py-_decision_implies_followup]]`(decision_text) → bool`
- **fn** [[eos_ai-substrate-meeting_intelligence-py-project_actionable_items]]`(summary) → list[ActionableItem]`
- **fn** [[eos_ai-substrate-meeting_intelligence-py-execution_linkage_block]]`(summary) → dict[str, Any]`
- **fn** [[eos_ai-substrate-meeting_intelligence-py-intelligence_report_block]]`(node_id, meeting_id) → dict[str, Any]`
- **fn** [[eos_ai-substrate-meeting_intelligence-py-_empty_linkage_snapshot]]`(node_id, meeting_id) → dict[str, Any]`
- **fn** [[eos_ai-substrate-meeting_intelligence-py-_normalize_actionable_item]]`(raw) → Optional[dict[str, Any]]`
- **fn** [[eos_ai-substrate-meeting_intelligence-py-build_linkage_snapshot]]`(summary) → dict[str, Any]`
- **fn** [[eos_ai-substrate-meeting_intelligence-py-linkage_snapshot]]`(node_id, meeting_id) → dict[str, Any]`
- **fn** [[eos_ai-substrate-meeting_intelligence-py-product_linkage_block]]`(node_id, meeting_id) → dict[str, Any]`

## Import Statements

```python
from __future__ import annotations
import json
import sys
import threading
import time
from dataclasses import dataclass
from dataclasses import field
from typing import Any
from typing import Optional
import re as _re
```
