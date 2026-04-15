---
type: codebase-function
file: eos_ai/notebooklm_sync.py
line: 77
generated: 2026-04-12
---

# NotebookLMSync.sync_pipeline_to_notebook

**File:** [[eos_ai-notebooklm_sync-py]] | **Line:** 77
**Signature:** `sync_pipeline_to_notebook(venture_id) → bool`

**Class:** [[eos_ai-notebooklm_sync-py-NotebookLMSync]]

Export pipeline data from Neon and upload to the venture's notebook.
Called manually or via check_and_update() on Saturdays.

## Calls

- [[eos_ai-notebooklm_sync-py-NotebookLMSync-_nlm_source_add]]
- [[eos_ai-notebooklm_sync-py-NotebookLMSync-_write_tmp]]

## Called By

- [[eos_ai-notebooklm_sync-py-NotebookLMSync-check_and_update]]
