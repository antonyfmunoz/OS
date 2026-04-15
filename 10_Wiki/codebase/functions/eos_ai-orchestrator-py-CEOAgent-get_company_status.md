---
type: codebase-function
file: eos_ai/orchestrator.py
line: 180
generated: 2026-04-12
---

# CEOAgent.get_company_status

**File:** [[eos_ai-orchestrator-py]] | **Line:** 180
**Signature:** `get_company_status() → dict`

**Class:** [[eos_ai-orchestrator-py-CEOAgent]]

Read live company health from Neon.
Returns ventures revenue, pending tasks, pending approvals,
7-day interaction count, and skill reply rate.

## Calls

- [[eos_ai-db-py-get_conn]]
- [[eos_ai-venture_knowledge-py-VentureKnowledgeBase-get]]
- [[eos_ai-venture_knowledge-py-VentureKnowledgeBase-list_ventures]]

## Called By

- [[eos_ai-orchestrator-py-CEOAgent-run_company_morning_cycle]]
