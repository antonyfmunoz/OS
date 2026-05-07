---
type: codebase-file
path: eos_ai/context.py
module: eos_ai.context
lines: 41
size: 1030
generated: 2026-05-07
---

# eos_ai/context.py

*No docstring.*

**Lines:** 41 | **Size:** 1,030 bytes

## Used By

- [[core-execution_contract-py]]
- [[eos_ai-agent_messages-py]]
- [[eos_ai-authority_engine-py]]
- [[eos_ai-ceo_agent-py]]
- [[eos_ai-context_builder-py]]
- [[eos_ai-context_compaction-py]]
- [[eos_ai-coordination_engine-py]]
- [[eos_ai-decision_log-py]]
- [[eos_ai-evolution_engine-py]]
- [[eos_ai-execution_engine-py]]
- [[eos_ai-gws_scanner-py]]
- [[eos_ai-human_intelligence-py]]
- [[eos_ai-intent_router-py]]
- [[eos_ai-knowledge_graph-py]]
- [[eos_ai-knowledge_integrator-py]]
- [[eos_ai-model_preferences-py]]
- [[eos_ai-notebooklm_sync-py]]
- [[eos_ai-onboarding_backfill-py]]
- [[eos_ai-os_trinity-py]]
- [[eos_ai-pattern_engine-py]]
- [[eos_ai-portfolio_advisor-py]]
- [[eos_ai-primitives-py]]
- [[eos_ai-principle_engine-py]]
- [[eos_ai-reality_context-py]]
- [[eos_ai-reality_engine-py]]
- [[eos_ai-research_engine-py]]
- [[eos_ai-stage_manager-py]]
- [[eos_ai-strategy_engine-py]]
- [[eos_ai-system_context-py]]
- [[eos_ai-task_executor-py]]
- [[eos_ai-trinity-py]]
- [[eos_ai-user_model-py]]
- [[eos_ai-voice_interface-py]]
- [[eos_ai-workflow_engine-py]]
- [[eos_ai-world_pulse-py]]
- [[scripts-inbox_gps_afternoon-py]]
- [[scripts-inbox_zero_init-py]]
- [[scripts-sync_skills_to_neon-py]]
- [[services-apify_scraper-py]]

## Contains

- **class** [[eos_ai-context-py-EOSContext]] — 0 methods
- **fn** [[eos_ai-context-py-load_ventures_from_env]]`() → list`
- **fn** [[eos_ai-context-py-load_context_from_env]]`() → EOSContext`

## Import Statements

```python
from dataclasses import dataclass
from dataclasses import field
import json
import os
from pathlib import Path
from dotenv import load_dotenv
```
