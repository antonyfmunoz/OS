---
type: codebase-function
file: eos_ai/orchestrator.py
line: 354
generated: 2026-04-12
---

# run_full_morning_cycle

**File:** [[eos_ai-orchestrator-py]] | **Line:** 354
**Signature:** `run_full_morning_cycle(ctx, return_content)`

Unified morning cycle producing one coherent Telegram message:
  1. Portfolio Advisor board view
  2. CEO report per company
  3. Strategy binding constraint
  4. Critical reality signals
...

## Calls

- [[eos_ai-memory-py-AgentMemory-log_event]]
- [[eos_ai-orchestrator-py-CEOAgent-run_company_morning_cycle]]
- [[eos_ai-orchestrator-py-_fmt_company_reports]]
- [[eos_ai-orchestrator-py-_fmt_patterns]]
- [[eos_ai-orchestrator-py-_fmt_pending]]
- [[eos_ai-orchestrator-py-_fmt_signals]]
- [[eos_ai-orchestrator-py-_notify]]
- [[eos_ai-orchestrator-py-_send_discord_webhook]]
- [[eos_ai-orchestrator-py-check_proactive_triggers]]
- [[eos_ai-orchestrator-py-write_to_notion_dashboard]]
- [[eos_ai-venture_knowledge-py-VentureKnowledgeBase-get]]
- [[eos_ai-venture_knowledge-py-VentureKnowledgeBase-list_ventures]]
