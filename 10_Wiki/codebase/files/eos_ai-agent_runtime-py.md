---
type: codebase-file
path: eos_ai/agent_runtime.py
module: eos_ai.agent_runtime
lines: 522
size: 21636
tags: [critical]
generated: 2026-04-12
---

# eos_ai/agent_runtime.py

> **CRITICAL FILE** — Core infrastructure. Read before modifying.

Agent runtime for OS agents.

Routes calls to the correct Claude model based on task type:
  - Haiku  (claude-haiku-4-5-20251001)  — scoring, classification, quick analysis
  - Sonnet (claude-sonnet-4-6)           — generation, deep analysis, content creation
...

**Lines:** 522 | **Size:** 21,636 bytes

## Depends On

- [[eos_ai-authority_engine-py]]
- [[eos_ai-context-py]]
- [[eos_ai-model_preferences-py]]
- [[eos_ai-skill_registry-py]]
- [[eos_ai-venture_knowledge-py]]

## Used By

- [[eos_ai-agent_teams-py]]
- [[eos_ai-cognitive_loop-py]]
- [[eos_ai-evolution_engine-py]]
- [[eos_ai-human_intelligence-py]]
- [[eos_ai-orchestrator-py]]
- [[eos_ai-portfolio_advisor-py]]
- [[eos_ai-reality_engine-py]]
- [[eos_ai-research_engine-py]]
- [[eos_ai-skill_improvement-py]]
- [[eos_ai-strategy_engine-py]]
- [[eos_ai-user_model-py]]
- [[eos_ai-voice_interface-py]]
- [[services-apify_scraper-py]]
- [[services-dm_monitor-py]]
- [[services-icp_scorer-py]]

## Contains

- **class** [[eos_ai-agent_runtime-py-TaskType]] — 0 methods
- **class** [[eos_ai-agent_runtime-py-RateLimiter]] — 1 methods
- **class** [[eos_ai-agent_runtime-py-AgentResult]] — 0 methods
- **class** [[eos_ai-agent_runtime-py-AgentRuntime]] — 5 methods
- **fn** [[eos_ai-agent_runtime-py-calculate_cost]]`(model, tokens_used) → float`

## Import Statements

```python
import os
import time
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from dotenv import load_dotenv
from eos_ai.context import EOSContext
from eos_ai.context import load_context_from_env
from eos_ai.venture_knowledge import VentureKnowledgeBase
from eos_ai.skill_registry import SkillRegistry
from eos_ai.skill_registry import get_skill_registry
from eos_ai.authority_engine import AuthorityEngine
from eos_ai.model_preferences import ModelPreferences
```
