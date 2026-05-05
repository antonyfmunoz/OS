---
type: codebase-function
file: eos_ai/orchestrator.py
line: 1383
generated: 2026-04-12
---

# EOSOrchestrator.write_postmortem

**File:** [[eos_ai-orchestrator-py]] | **Line:** 1383
**Signature:** `write_postmortem(failure_description, error_log, affected_component) → str`

**Class:** [[eos_ai-orchestrator-py-EOSOrchestrator]]

Generate an AI-written postmortem for a system failure.
Writes to orchestrator/postmortems/YYYY-MM-DD_component.md.
Logs to memory.db via AgentRuntime.
Returns the postmortem file path.

## Calls

- [[eos_ai-agent_runtime-py-AgentRuntime-run]]
