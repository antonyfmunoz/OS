---
type: codebase-function
file: scripts/summarize_conversations.py
line: 391
generated: 2026-04-12
---

# process_session

**File:** [[scripts-summarize_conversations-py]] | **Line:** 391
**Signature:** `process_session(filepath, dry_run) → bool`

Process a single conversation file. Returns True if summary created.

## Calls

- [[scripts-summarize_conversations-py-_call_llm]]
- [[scripts-summarize_conversations-py-_extract_body]]
- [[scripts-summarize_conversations-py-_is_trivial]]
- [[scripts-summarize_conversations-py-_parse_llm_response]]
- [[scripts-summarize_conversations-py-update_memory_index]]
- [[scripts-summarize_conversations-py-write_summary]]

## Called By

- [[scripts-summarize_conversations-py-main]]
