---
type: codebase-function
file: core/observability.py
line: 264
generated: 2026-04-12
---

# Observability.agent_status

**File:** [[core-observability-py]] | **Line:** 264
**Signature:** `agent_status() → list[dict[str, Any]]`

**Class:** [[core-observability-py-Observability]]

Read each persistent agent's state file.

## Calls

- [[core-observability-py-_read_json]]

## Called By

- [[core-observability-py-Observability-snapshot]]
- [[scripts-eos_os-py-_cmd_agents]]
