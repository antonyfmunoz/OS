---
name: notion-tool
description: "Notion API integration for EOS. Use when any agent needs to read or write Notion databases (tasks, CRM pipeline, goals, metrics)."
allowed-tools: "Read, Bash"
version: 1.0
source_url: "https://developers.notion.com/"
last_researched: "2026-04-01"
effort: low
trigger: both
context: fork
---

!`python3 /opt/OS/scripts/bis_context.py --fields name,icp,offer,stage,primary_channel,binding_constraint,north_star`


# Tool: Notion

## What This Tool Does
Notion API provides read/write access to pages, databases, blocks, and users.
EOS uses it as the external delivery layer for the active venture — tasks, CRM, and course content live in Notion.

## EOS Integration
- DEX reads task databases to populate daily briefs
- CEO agents write daily objectives to Notion task DBs
- orchestrator/ syncs state to Notion on cron
- Venture configs store Notion DB IDs (notion_tasks_db, notion_pipeline_crm_db, etc.)

## Authentication
Integration token stored in services/.env as NOTION_TOKEN.
Token scoped to specific pages/databases via Notion integration settings.

## Quick Reference
```python
from notion_client import Client
notion = Client(auth=os.getenv("NOTION_TOKEN"))

# Query database
results = notion.databases.query(database_id="...", filter={...})

# Create page
notion.pages.create(parent={"database_id": "..."}, properties={...})

# Update page
notion.pages.update(page_id="...", properties={...})
```

See references/best_practices.md for rate limits and anti-patterns.


## Gotchas
- Add failures here as they occur.
- This section compounds over time.
