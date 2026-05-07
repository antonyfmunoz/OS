---
type: codebase-file
path: eos_ai/substrate/llm_replay.py
module: eos_ai.substrate.llm_replay
lines: 616
size: 24024
generated: 2026-05-07
---

# eos_ai/substrate/llm_replay.py

Replay-safe determinism boundary for the LLM planning layer.

ReplayableStrategy implements DecisionStrategy and owns the entire
determinism contract:
- Config enforcement (enabled, intent eligibility).
...

**Lines:** 616 | **Size:** 24,024 bytes

## Depends On

- [[eos_ai-substrate-decision_engine-py]]
- [[eos_ai-substrate-event_scheduler-py]]
- [[eos_ai-substrate-llm_decision_events-py]]
- [[eos_ai-substrate-llm_planner-py]]

## Contains

- **class** [[eos_ai-substrate-llm_replay-py-LLMDecisionRecord]] — 0 methods
- **class** [[eos_ai-substrate-llm_replay-py-ReplayableStrategy]] — 13 methods
- **fn** [[eos_ai-substrate-llm_replay-py-_log]]`(msg) → None`
- **fn** [[eos_ai-substrate-llm_replay-py-_utcnow_iso]]`() → str`

## Import Statements

```python
from __future__ import annotations
import concurrent.futures
import os
import sys
import threading
import weakref
from dataclasses import dataclass
from datetime import datetime
from datetime import timezone
from typing import Any
from eos_ai.substrate.decision_engine import DecisionOutput
from eos_ai.substrate.event_scheduler import EventScheduler
from eos_ai.substrate.event_scheduler import SchedulerEvent
from eos_ai.substrate.intent_models import IntentType
from eos_ai.substrate.intent_models import get_active_intents_from_state
from eos_ai.substrate.llm_decision_events import build_llm_decision_accepted_event
from eos_ai.substrate.llm_decision_events import build_llm_decision_received_event
from eos_ai.substrate.llm_decision_events import build_llm_decision_rejected_event
from eos_ai.substrate.llm_decision_events import build_llm_decision_requested_event
from eos_ai.substrate.llm_decision_events import build_llm_decision_skipped_event
from eos_ai.substrate.llm_decision_events import build_llm_response_drift_event
from eos_ai.substrate.llm_planner import EventTypeRegistry
from eos_ai.substrate.llm_planner import LLMEventProposal
from eos_ai.substrate.llm_planner import LLMPlannerConfig
from eos_ai.substrate.llm_planner import LLMPlanningStrategy
from eos_ai.substrate.llm_planner import LLMProposalResult
from eos_ai.substrate.llm_planner import ProposedEvent
from eos_ai.substrate.llm_planner import SelectionPolicy
from eos_ai.substrate.llm_planner import ValidationResult
from eos_ai.substrate.llm_planner import _canonical_json
from eos_ai.substrate.llm_planner import _sha256_hex
from eos_ai.substrate.llm_planner import _sha256_prefix
```
