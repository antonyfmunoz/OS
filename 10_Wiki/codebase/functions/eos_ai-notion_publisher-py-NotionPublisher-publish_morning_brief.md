---
type: codebase-function
file: eos_ai/notion_publisher.py
line: 268
generated: 2026-04-11
---

# NotionPublisher.publish_morning_brief

**File:** [[eos_ai-notion_publisher-py]] | **Line:** 268
**Signature:** `publish_morning_brief(content, brief_date) → str`

**Class:** [[eos_ai-notion_publisher-py-NotionPublisher]]

Write morning brief to Notion.
Uses NOTION_MORNING_BRIEF_ID as the parent database.
Returns page URL or ''.

content keys:
...

## Calls

- [[eos_ai-notion_publisher-py-_brief_blocks]]
- [[eos_ai-notion_publisher-py-_create_page]]
- [[eos_ai-notion_publisher-py-_find_page_by_title]]
- [[eos_ai-notion_publisher-py-_get_db_id]]
