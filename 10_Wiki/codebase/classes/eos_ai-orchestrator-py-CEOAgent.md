---
type: codebase-class
file: eos_ai/orchestrator.py
line: 70
generated: 2026-04-11
---

# CEOAgent

**File:** [[eos_ai-orchestrator-py]] | **Line:** 70

Operates one company under the Portfolio. Breaks high-level objectives
into department tasks, delegates via CoordinationEngine, and produces
a company health snapshot for the morning cycle.

## Methods

- [[eos_ai-orchestrator-py-CEOAgent-__init__]]`(ctx, org_id) → None` — 
- [[eos_ai-orchestrator-py-CEOAgent-delegate_objective]]`(objective, venture_id) → dict` — Formally activate the correct department agents beneath the CEO.
- [[eos_ai-orchestrator-py-CEOAgent-get_company_status]]`() → dict` — Read live company health from Neon.
- [[eos_ai-orchestrator-py-CEOAgent-run_company_morning_cycle]]`() → dict` — Per-company morning snapshot used by run_full_morning_cycle.
