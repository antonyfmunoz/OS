---
type: codebase-function
file: eos_ai/notebooklm_sync.py
line: 198
generated: 2026-05-07
---

# NotebookLMSync.query_for_context

**File:** [[eos_ai-notebooklm_sync-py]] | **Line:** 198
**Signature:** `query_for_context(venture_id, question) → str`

**Class:** [[eos_ai-notebooklm_sync-py-NotebookLMSync]]

Query a NotebookLM notebook via nlm CLI.
Stores the answer in Neon as a notebooklm_insight event for DEX.
Returns the answer string.
