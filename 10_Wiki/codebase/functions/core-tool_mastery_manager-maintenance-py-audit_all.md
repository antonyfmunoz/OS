---
type: codebase-function
file: core/tool_mastery_manager/maintenance.py
line: 41
generated: 2026-05-07
---

# audit_all

**File:** [[core-tool_mastery_manager-maintenance-py]] | **Line:** 41
**Signature:** `audit_all() → dict`

Return a full coverage snapshot across all discovered tools.

Unlike build_backlog(), this includes READY entries so callers can
see the entire picture at once. Useful for CLI `status`-style
commands and for the audit report.

## Called By

- [[scripts-tool_mastery_manager-py-cmd_scan]]
