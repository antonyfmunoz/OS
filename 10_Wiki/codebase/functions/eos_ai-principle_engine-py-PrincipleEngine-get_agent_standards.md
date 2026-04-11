---
type: codebase-function
file: eos_ai/principle_engine.py
line: 488
generated: 2026-04-11
---

# PrincipleEngine.get_agent_standards

**File:** [[eos_ai-principle_engine-py]] | **Line:** 488
**Signature:** `get_agent_standards(agent_id) → list[str]`

**Class:** [[eos_ai-principle_engine-py-PrincipleEngine]]

Get operational standards for a specific agent.
Injected into the gateway prompt when that agent is active.
Complements domain principles — more specific, action-oriented,
failure-aware.

## Called By

- [[eos_ai-principle_engine-py-PrincipleEngine-format_agent_standards]]
