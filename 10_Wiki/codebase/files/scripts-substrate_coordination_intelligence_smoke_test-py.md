---
type: codebase-file
path: scripts/substrate_coordination_intelligence_smoke_test.py
module: scripts.substrate_coordination_intelligence_smoke_test
lines: 275
size: 9382
tags: [entry-point]
generated: 2026-04-12
---

# scripts/substrate_coordination_intelligence_smoke_test.py

> **ENTRY POINT** — Contains `if __name__` or server start.

Smoke test for Coordination Intelligence Layer v1.

Validates the additive, bounded ownership-awareness layered on top of
Temporal/Resolution/Execution intelligence. No hot-path changes, no new
pipelines, no daemons. Time is simulated where needed.
...

**Lines:** 275 | **Size:** 9,382 bytes

## Depends On

- [[eos_ai-substrate-actions-py]]

## Contains

- **fn** [[scripts-substrate_coordination_intelligence_smoke_test-py-_fresh_summary]]`() → mi.MeetingSummary`
- **fn** [[scripts-substrate_coordination_intelligence_smoke_test-py-_utt]]`(text, speaker) → dict`
- **fn** [[scripts-substrate_coordination_intelligence_smoke_test-py-check_first_person_with_speaker]]`() → None`
- **fn** [[scripts-substrate_coordination_intelligence_smoke_test-py-check_first_person_no_speaker]]`() → None`
- **fn** [[scripts-substrate_coordination_intelligence_smoke_test-py-check_named_third_party]]`() → None`
- **fn** [[scripts-substrate_coordination_intelligence_smoke_test-py-check_group_owner]]`() → None`
- **fn** [[scripts-substrate_coordination_intelligence_smoke_test-py-check_distribution_and_unassigned]]`() → None`
- **fn** [[scripts-substrate_coordination_intelligence_smoke_test-py-check_scoring_pressure_owned]]`() → None`
- **fn** [[scripts-substrate_coordination_intelligence_smoke_test-py-check_scoring_ambiguity_unowned]]`() → None`
- **fn** [[scripts-substrate_coordination_intelligence_smoke_test-py-check_follow_up_targets_owner]]`() → None`
- **fn** [[scripts-substrate_coordination_intelligence_smoke_test-py-check_follow_up_unassigned_prompts_assignment]]`() → None`
- **fn** [[scripts-substrate_coordination_intelligence_smoke_test-py-check_high_escalation_more_direct]]`() → None`
- **fn** [[scripts-substrate_coordination_intelligence_smoke_test-py-check_report_block_exposes_ownership]]`() → None`
- **fn** [[scripts-substrate_coordination_intelligence_smoke_test-py-check_pressure_hint_values]]`() → None`
- **fn** [[scripts-substrate_coordination_intelligence_smoke_test-py-check_distribution_cap]]`() → None`
- **fn** [[scripts-substrate_coordination_intelligence_smoke_test-py-check_malformed_input]]`() → None`
- **fn** [[scripts-substrate_coordination_intelligence_smoke_test-py-check_hot_path_clean]]`() → None`
- **fn** [[scripts-substrate_coordination_intelligence_smoke_test-py-main]]`() → int`

## Import Statements

```python
from __future__ import annotations
import subprocess
import sys
import time
from eos_ai.substrate import meeting_intelligence as mi
```
