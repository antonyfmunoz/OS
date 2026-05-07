---
type: codebase-file
path: eos_ai/substrate/llm_planner.py
module: eos_ai.substrate.llm_planner
lines: 749
size: 25111
generated: 2026-05-07
---

# eos_ai/substrate/llm_planner.py

LLM planning strategy — constrained plan proposer.

Proposes candidate events based on state + active intents, validates
them against an authoritative EventTypeRegistry, and returns a
structured result bundle.  This module NEVER emits events, writes
...

**Lines:** 749 | **Size:** 25,111 bytes

## Used By

- [[eos_ai-substrate-llm_replay-py]]

## Contains

- **class** [[eos_ai-substrate-llm_planner-py-SelectionPolicy]] — 0 methods
- **class** [[eos_ai-substrate-llm_planner-py-LLMPlannerConfig]] — 1 methods
- **class** [[eos_ai-substrate-llm_planner-py-EventSchema]] — 0 methods
- **class** [[eos_ai-substrate-llm_planner-py-EventTypeRegistry]] — 9 methods
- **class** [[eos_ai-substrate-llm_planner-py-ProposedEvent]] — 2 methods
- **class** [[eos_ai-substrate-llm_planner-py-LLMEventProposal]] — 0 methods
- **class** [[eos_ai-substrate-llm_planner-py-ValidationResult]] — 0 methods
- **class** [[eos_ai-substrate-llm_planner-py-LLMProposalResult]] — 0 methods
- **class** [[eos_ai-substrate-llm_planner-py-LLMPlanningStrategy]] — 3 methods
- **fn** [[eos_ai-substrate-llm_planner-py-_log]]`(msg) → None`
- **fn** [[eos_ai-substrate-llm_planner-py-_normalize_for_canonical]]`(obj) → Any`
- **fn** [[eos_ai-substrate-llm_planner-py-_canonical_json]]`(obj) → str`
- **fn** [[eos_ai-substrate-llm_planner-py-_sha256_hex]]`(data) → str`
- **fn** [[eos_ai-substrate-llm_planner-py-_sha256_prefix]]`(data, length) → str`
- **fn** [[eos_ai-substrate-llm_planner-py-_truncate_state]]`(canonical_state, config) → str`
- **fn** [[eos_ai-substrate-llm_planner-py-_build_event_catalog]]`(registry) → str`
- **fn** [[eos_ai-substrate-llm_planner-py-build_llm_prompt]]`(canonical_state, active_intents, registry, config) → str`
- **fn** [[eos_ai-substrate-llm_planner-py-compute_prompt_hash]]`(prompt, model_name, temperature, config_version, registry_version) → str`

## Import Statements

```python
from __future__ import annotations
import hashlib
import json
import sys
import threading
import time
import unicodedata
from dataclasses import dataclass
from dataclasses import field
from enum import Enum
from typing import Any
from typing import Callable
from eos_ai.substrate.intent_models import IntentType
```
