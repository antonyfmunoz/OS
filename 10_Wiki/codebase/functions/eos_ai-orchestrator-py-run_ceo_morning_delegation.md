---
type: codebase-function
file: eos_ai/orchestrator.py
line: 655
generated: 2026-04-12
---

# run_ceo_morning_delegation

**File:** [[eos_ai-orchestrator-py]] | **Line:** 655
**Signature:** `run_ceo_morning_delegation(ctx, ventures) → None`

CEO agent morning delegation cycle.
For each venture, identifies today's key objective
and delegates to specialist agents via CoordinationEngine.
Runs after the morning brief.

## Calls

- [[eos_ai-orchestrator-py-_send_discord_webhook]]
- [[eos_ai-venture_knowledge-py-VentureKnowledgeBase-get]]
