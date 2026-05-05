---
type: codebase-function
file: eos_ai/notion_sync.py
line: 333
generated: 2026-04-12
---

# write_document

**File:** [[eos_ai-notion_sync-py]] | **Line:** 333
**Signature:** `write_document(venture_id, title, doc_type, department, category, content, source, confidence, file_path, linked_entity) → str`

Create a document/knowledge row. Returns page ID or ''.

## Calls

- [[eos_ai-notion_sync-py-_create_page]]
- [[eos_ai-notion_sync-py-_select]]
- [[eos_ai-notion_sync-py-_text]]
- [[eos_ai-notion_sync-py-_title]]
- [[eos_ai-notion_sync-py-get_db_id]]

## Called By

- [[scripts-notion_seed_all-py-seed_content_calendars]]
- [[scripts-notion_seed_all-py-seed_empyrean]]
- [[scripts-notion_seed_all-py-seed_personal_brand]]
