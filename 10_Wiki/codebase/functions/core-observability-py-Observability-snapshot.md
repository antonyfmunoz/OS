---
type: codebase-function
file: core/observability.py
line: 160
generated: 2026-04-12
---

# Observability.snapshot

**File:** [[core-observability-py]] | **Line:** 160
**Signature:** `snapshot() → dict[str, Any]`

**Class:** [[core-observability-py-Observability]]

A single dict summarizing the whole system.

## Calls

- [[core-observability-py-Observability-_filter_env]]
- [[core-observability-py-Observability-agent_status]]
- [[core-observability-py-_read_json]]
- [[core-observability-py-_read_jsonl_tail]]

## Called By

- [[core-observability-py-Observability-compare_to_production]]
- [[scripts-eos_os-py-_cmd_status]]
