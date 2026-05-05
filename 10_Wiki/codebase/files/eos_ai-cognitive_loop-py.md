---
type: codebase-file
path: eos_ai/cognitive_loop.py
module: eos_ai.cognitive_loop
lines: 1679
size: 60468
tags: [critical]
generated: 2026-04-12
---

# eos_ai/cognitive_loop.py

> **CRITICAL FILE** — Core infrastructure. Read before modifying.

CognitiveLoop — full Perceive → Understand → Plan → Execute
→ Verify → Reflect → Learn → Store cycle.

Wraps AgentRuntime with authority gating, prompt enhancement,
quality verification, and reflection logging. Every AI task
...

**Lines:** 1679 | **Size:** 60,468 bytes

## Depends On

- [[eos_ai-agent_runtime-py]]
- [[eos_ai-authority_engine-py]]
- [[eos_ai-context-py]]
- [[eos_ai-memory-py]]
- [[eos_ai-venture_knowledge-py]]

## Used By

- [[eos_ai-evolution_engine-py]]
- [[eos_ai-onboarding_backfill-py]]
- [[eos_ai-reality_engine-py]]
- [[eos_ai-research_engine-py]]
- [[eos_ai-strategy_engine-py]]
- [[eos_ai-user_model-py]]
- [[eos_ai-voice_interface-py]]

## Contains

- **class** [[eos_ai-cognitive_loop-py-MultimodalInput]] — 0 methods
- **class** [[eos_ai-cognitive_loop-py-CognitiveResult]] — 0 methods
- **class** [[eos_ai-cognitive_loop-py-CognitiveLoop]] — 9 methods
- **fn** [[eos_ai-cognitive_loop-py-_get_neon_spend]]`(org_id) → dict`
- **fn** [[eos_ai-cognitive_loop-py-format_response_footer]]`(result, iterations, was_enhanced, original_prompt, enhanced_prompt, org_id) → str`
- **fn** [[eos_ai-cognitive_loop-py-_format_intent_context]]`(intent_data) → str`
- **fn** [[eos_ai-cognitive_loop-py-detect_intent_and_inject]]`(text, req, ctx) → dict`

## Import Statements

```python
from dataclasses import dataclass
from dataclasses import field
from pathlib import Path
import os
import sys
import uuid
import tempfile
import time as _time
from eos_ai.context import EOSContext
from eos_ai.context import load_context_from_env
from eos_ai.agent_runtime import AgentRuntime
from eos_ai.agent_runtime import TaskType
from eos_ai.memory import AgentMemory
from eos_ai.authority_engine import AuthorityEngine
from eos_ai.venture_knowledge import VentureKnowledgeBase
```
