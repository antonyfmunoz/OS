---
type: codebase-function
file: core/action_system/deferred.py
line: 63
generated: 2026-04-12
---

# list_deferred

**File:** [[core-action_system-deferred-py]] | **Line:** 63
**Signature:** `list_deferred() → list[dict[str, Any]]`

Return summary dicts for every currently deferred action.

Summary includes id, type, description, risk_level, source_agent,
and deferred_at — enough to render a CLI table without loading
every full payload.

## Called By

- [[core-orchestrator-loop-py-_scan_stale_deferred]]
- [[scripts-deferred-py-cmd_list]]
- [[scripts-deferred-py-cmd_prune]]
- [[scripts-orchestrator_status-py-deferred_summary]]
