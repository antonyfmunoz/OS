---
type: codebase-function
file: core/tool_mastery_manager/backlog.py
line: 59
generated: 2026-04-12
---

# build_backlog

**File:** [[core-tool_mastery_manager-backlog-py]] | **Line:** 59
**Signature:** `build_backlog() → list[BacklogEntry]`

Return every discovered tool with its CoverageReport, sorted by priority.

Excludes READY entries by default — "backlog" means "work to do",
and returning 80+ READY tools every call is just noise.

## Calls

- [[core-tool_mastery_manager-backlog-py-_iter_discovered]]

## Called By

- [[core-tool_mastery_manager-backlog-py-backlog_report]]
- [[core-tool_mastery_manager-backlog-py-bootstrap]]
