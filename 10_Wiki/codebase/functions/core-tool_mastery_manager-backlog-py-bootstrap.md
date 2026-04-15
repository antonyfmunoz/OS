---
type: codebase-function
file: core/tool_mastery_manager/backlog.py
line: 151
generated: 2026-04-12
---

# bootstrap

**File:** [[core-tool_mastery_manager-backlog-py]] | **Line:** 151
**Signature:** `bootstrap() → dict`

Fresh-environment flow: backlog → ensure_mastery on each non-ready tool.

Every ensure call is routed through the Control Plane. In dry_run
mode nothing is scaffolded or queued — the result is purely a plan.

## Calls

- [[core-tool_mastery_manager-backlog-py-BacklogEntry-to_dict]]
- [[core-tool_mastery_manager-backlog-py-build_backlog]]

## Called By

- [[scripts-tool_mastery_manager-py-cmd_bootstrap]]
