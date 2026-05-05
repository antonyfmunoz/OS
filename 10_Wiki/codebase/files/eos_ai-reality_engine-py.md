---
type: codebase-file
path: eos_ai/reality_engine.py
module: eos_ai.reality_engine
lines: 588
size: 24465
generated: 2026-04-12
---

# eos_ai/reality_engine.py

RealityIntelligenceEngine — continuous market intelligence layer.

Scans for signals across ventures, classifies by priority tier, and routes
through the event bus in real time. Runs every 6 hours during waking hours
(6am, 12pm, 6pm) as a scheduled job wired into the orchestrator and Telegram bot.
...

**Lines:** 588 | **Size:** 24,465 bytes

## Depends On

- [[eos_ai-agent_runtime-py]]
- [[eos_ai-cognitive_loop-py]]
- [[eos_ai-context-py]]
- [[eos_ai-event_bus-py]]
- [[eos_ai-memory-py]]
- [[eos_ai-strategy_engine-py]]
- [[eos_ai-venture_knowledge-py]]

## Contains

- **class** [[eos_ai-reality_engine-py-RealityIntelligenceEngine]] — 7 methods
- **fn** [[eos_ai-reality_engine-py-_notify]]`(text) → None`

## Import Statements

```python
import datetime
import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from eos_ai.context import EOSContext
from eos_ai.cognitive_loop import CognitiveLoop
from eos_ai.event_bus import EventBus
from eos_ai.agent_runtime import TaskType
from eos_ai.venture_knowledge import VentureKnowledgeBase
from eos_ai.strategy_engine import StrategyEngine
from eos_ai.strategy_engine import _parse_labeled_sections
from eos_ai.memory import AgentMemory
```
