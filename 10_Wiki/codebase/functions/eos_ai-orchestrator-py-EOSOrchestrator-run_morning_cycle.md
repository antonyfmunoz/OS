---
type: codebase-function
file: eos_ai/orchestrator.py
line: 1444
generated: 2026-04-12
---

# EOSOrchestrator.run_morning_cycle

**File:** [[eos_ai-orchestrator-py]] | **Line:** 1444
**Signature:** `run_morning_cycle() → None`

**Class:** [[eos_ai-orchestrator-py-EOSOrchestrator]]

Full cycle: north star check → morning brief → skill improvement →
Telegram.  Called by cron at 6am.

## Calls

- [[eos_ai-agent_runtime-py-AgentRuntime-run]]
- [[eos_ai-context-py-load_context_from_env]]
- [[eos_ai-orchestrator-py-EOSOrchestrator-get_north_star_status]]
- [[eos_ai-orchestrator-py-EOSOrchestrator-morning_brief]]
- [[eos_ai-orchestrator-py-_notify]]
- [[eos_ai-orchestrator-py-refresh_ambient_state]]
- [[eos_ai-venture_knowledge-py-VentureKnowledgeBase-get]]
- [[eos_ai-venture_knowledge-py-VentureKnowledgeBase-list_ventures]]
