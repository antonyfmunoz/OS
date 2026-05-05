---
type: codebase-function
file: services/icp_scorer.py
line: 381
generated: 2026-04-12
---

# create_lead_file

**File:** [[services-icp_scorer-py]] | **Line:** 381
**Signature:** `create_lead_file(username, comment_text, source, post_url, timestamp, result, opener, opener_index)`

Write lead markdown file and return filepath.

## Calls

- [[eos_ai-memory-py-AgentMemory-log_lead_scored]]
- [[services-icp_scorer-py-push_lead_to_notion]]
- [[services-icp_scorer-py-update_opener_stats_sent]]

## Called By

- [[services-icp_scorer-py-main]]
