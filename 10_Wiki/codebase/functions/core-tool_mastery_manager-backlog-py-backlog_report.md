---
type: codebase-function
file: core/tool_mastery_manager/backlog.py
line: 127
generated: 2026-04-12
---

# backlog_report

**File:** [[core-tool_mastery_manager-backlog-py]] | **Line:** 127
**Signature:** `backlog_report() → dict`

Run backlog + optionally persist a report.

Returns a dict with the counts, entries (as dicts), and artifact
paths (when persisted). Suitable for printing or JSON emission.

## Calls

- [[core-tool_mastery_manager-backlog-py-BacklogEntry-to_dict]]
- [[core-tool_mastery_manager-backlog-py-_write_report]]
- [[core-tool_mastery_manager-backlog-py-build_backlog]]

## Called By

- [[scripts-tool_mastery_manager-py-cmd_backlog]]
