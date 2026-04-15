---
type: codebase-function
file: eos_ai/notion_publisher.py
line: 312
generated: 2026-04-12
---

# NotionPublisher.publish_intel_brief

**File:** [[eos_ai-notion_publisher-py]] | **Line:** 312
**Signature:** `publish_intel_brief(content, brief_date) → str`

**Class:** [[eos_ai-notion_publisher-py-NotionPublisher]]

Write intelligence brief to Notion.
Uses NOTION_MORNING_BRIEF_ID or Documents DB fallback.
Returns page URL or ''.

## Calls

- [[eos_ai-notion_publisher-py-_create_page]]
- [[eos_ai-notion_publisher-py-_divider]]
- [[eos_ai-notion_publisher-py-_find_page_by_title]]
- [[eos_ai-notion_publisher-py-_get_db_id]]
- [[eos_ai-notion_publisher-py-_heading]]
- [[eos_ai-notion_publisher-py-_paragraph]]
