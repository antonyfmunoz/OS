---
type: codebase-class
file: eos_ai/notebooklm_sync.py
line: 41
generated: 2026-04-12
---

# NotebookLMSync

**File:** [[eos_ai-notebooklm_sync-py]] | **Line:** 41

*No docstring.*

## Methods

- [[eos_ai-notebooklm_sync-py-NotebookLMSync-__init__]]`(ctx)` — 
- [[eos_ai-notebooklm_sync-py-NotebookLMSync-_nlm_source_add]]`(notebook_id, file_path) → bool` — Run nlm source add and return success.
- [[eos_ai-notebooklm_sync-py-NotebookLMSync-_write_tmp]]`(content, suffix) → str` — Write content to a temp file and return its path.
- [[eos_ai-notebooklm_sync-py-NotebookLMSync-sync_pipeline_to_notebook]]`(venture_id) → bool` — Export pipeline data from Neon and upload to the venture's notebook.
- [[eos_ai-notebooklm_sync-py-NotebookLMSync-sync_world_pulse_to_notebook]]`(report) → bool` — Upload a world pulse report to the world_pulse notebook.
- [[eos_ai-notebooklm_sync-py-NotebookLMSync-sync_founder_profile]]`() → bool` — Upload founder profile and brand docs to all venture notebooks.
- [[eos_ai-notebooklm_sync-py-NotebookLMSync-query_for_context]]`(venture_id, question) → str` — Query a NotebookLM notebook via nlm CLI.
- [[eos_ai-notebooklm_sync-py-NotebookLMSync-get_recent_insights]]`(venture_id, limit) → list[dict]` — Retrieve recent NotebookLM insights from Neon for DEX context injection.
- [[eos_ai-notebooklm_sync-py-NotebookLMSync-check_and_update]]`() → dict` — Full cross-reference: sync founder profile and venture pipelines to NotebookLM.
