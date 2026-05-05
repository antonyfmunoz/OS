---
type: codebase-function
file: eos_ai/orchestrator.py
line: 1164
generated: 2026-04-12
---

# write_to_notion_dashboard

**File:** [[eos_ai-orchestrator-py]] | **Line:** 1164
**Signature:** `write_to_notion_dashboard(ctx, morning_data) → None`

DEPRECATED: Use NotionPublisher.publish_morning_brief() instead.
This function is kept for backward compatibility only.
The morning brief is now written to Notion by run_full_morning_cycle()
via NotionPublisher before this function is called.

## Called By

- [[eos_ai-orchestrator-py-run_full_morning_cycle]]
