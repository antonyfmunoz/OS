---
type: codebase-file
path: eos_ai/notion_sync.py
module: eos_ai.notion_sync
lines: 470
size: 14070
generated: 2026-04-11
---

# eos_ai/notion_sync.py

Notion Sync — EOS runtime write layer.
Pushes EOS primitives to Notion databases.
Called by cognitive_loop, orchestrator, and agent_runtime.

All write functions return Notion page ID (str) or '' on failure.
...

**Lines:** 470 | **Size:** 14,070 bytes

## Used By

- [[scripts-notion_seed-py]]
- [[scripts-notion_seed_all-py]]

## Contains

- **fn** [[eos_ai-notion_sync-py-get_db_id]]`(venture_id, db_key) → str`
- **fn** [[eos_ai-notion_sync-py-_title]]`(value) → dict`
- **fn** [[eos_ai-notion_sync-py-_text]]`(value) → dict`
- **fn** [[eos_ai-notion_sync-py-_select]]`(value) → dict`
- **fn** [[eos_ai-notion_sync-py-_date]]`(value) → dict`
- **fn** [[eos_ai-notion_sync-py-_number]]`(value) → dict`
- **fn** [[eos_ai-notion_sync-py-_checkbox]]`(value) → dict`
- **fn** [[eos_ai-notion_sync-py-_create_page]]`(db_id, properties) → str`
- **fn** [[eos_ai-notion_sync-py-_update_page]]`(page_id, properties) → bool`
- **fn** [[eos_ai-notion_sync-py-write_task]]`(venture_id, name, status, priority, department, assigned_to, assignee_type, source, task_type, due_date, neon_id, notes, requires_approval) → str`
- **fn** [[eos_ai-notion_sync-py-update_task_status]]`(page_id, status) → bool`
- **fn** [[eos_ai-notion_sync-py-write_pipeline_entry]]`(venture_id, name, stage, entry_type, channel, score, email, notes, next_action, source, ai_qualified, value) → str`
- **fn** [[eos_ai-notion_sync-py-update_pipeline_stage]]`(page_id, stage) → bool`
- **fn** [[eos_ai-notion_sync-py-write_metric]]`(venture_id, metric_name, value, target, unit, period, category, department, linked_goal, notes) → str`
- **fn** [[eos_ai-notion_sync-py-write_meeting]]`(venture_id, name, meeting_type, status, person, email, date, duration_min, outcomes, open_loops, meet_link, prep_notes) → str`
- **fn** [[eos_ai-notion_sync-py-write_decision]]`(venture_id, decision, department, impact, made_by, rationale, outcome) → str`
- **fn** [[eos_ai-notion_sync-py-write_document]]`(venture_id, title, doc_type, department, category, content, source, confidence, file_path, linked_entity) → str`
- **fn** [[eos_ai-notion_sync-py-push_pending_tasks_to_notion]]`(venture_id, ctx) → int`
- **fn** [[eos_ai-notion_sync-py-push_all_ventures]]`(ctx) → dict`

## Import Statements

```python
import os
import json as _json
import logging
import requests
from datetime import datetime
from dotenv import load_dotenv
```
