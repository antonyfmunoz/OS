---
type: codebase-class
file: eos_ai/orchestrator.py
line: 1181
generated: 2026-04-12
---

# EOSOrchestrator

**File:** [[eos_ai-orchestrator-py]] | **Line:** 1181

*No docstring.*

## Methods

- [[eos_ai-orchestrator-py-EOSOrchestrator-__init__]]`() → None` — 
- [[eos_ai-orchestrator-py-EOSOrchestrator-_query_7d_stats]]`(venture_id) → dict` — Query Neon for interactions + outcomes in the last 7 days for a given
- [[eos_ai-orchestrator-py-EOSOrchestrator-get_north_star_status]]`() → list[dict]` — Return revenue vs target for every venture.
- [[eos_ai-orchestrator-py-EOSOrchestrator-morning_brief]]`() → str` — DEPRECATED: Use run_full_morning_cycle() instead.
- [[eos_ai-orchestrator-py-EOSOrchestrator-write_postmortem]]`(failure_description, error_log, affected_component) → str` — Generate an AI-written postmortem for a system failure.
- [[eos_ai-orchestrator-py-EOSOrchestrator-run_morning_cycle]]`() → None` — Full cycle: north star check → morning brief → skill improvement →
