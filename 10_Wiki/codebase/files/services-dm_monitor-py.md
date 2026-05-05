---
type: codebase-file
path: services/dm_monitor.py
module: services.dm_monitor
lines: 1383
size: 52865
tags: [entry-point]
generated: 2026-04-12
---

# services/dm_monitor.py

> **ENTRY POINT** — Contains `if __name__` or server start.

*No docstring.*

**Lines:** 1383 | **Size:** 52,865 bytes

## Depends On

- [[eos_ai-agent_runtime-py]]
- [[eos_ai-context-py]]
- [[eos_ai-error_handler-py]]
- [[eos_ai-memory-py]]

## Contains

- **fn** [[services-dm_monitor-py-send_telegram]]`(text)`
- **fn** [[services-dm_monitor-py-load_workflow_prompt]]`(filename)`
- **fn** [[services-dm_monitor-py-get_vault_path]]`()`
- **fn** [[services-dm_monitor-py-move_card_to_stage]]`(username, from_stage, to_stage)`
- **fn** [[services-dm_monitor-py-update_lead_stage]]`(username, new_stage, conversation_stage)`
- **fn** [[services-dm_monitor-py-parse_frontmatter_dm]]`(content)`
- **fn** [[services-dm_monitor-py-update_source_booked]]`(username)`
- **fn** [[services-dm_monitor-py-update_source_reply]]`(username)`
- **fn** [[services-dm_monitor-py-_log_rlhf_outcome]]`(username, outcome_type, score, notes)`
- **fn** [[services-dm_monitor-py-_advance_pipeline]]`(username, stage)`
- **fn** [[services-dm_monitor-py-extract_messages_from_screenshot]]`(screenshot_path)`
- **fn** [[services-dm_monitor-py-detect_stage]]`(conversation_text)`
- **fn** [[services-dm_monitor-py-generate_reply]]`(conversation_text)`
- **fn** [[services-dm_monitor-py-save_conversation]]`(username, messages_text, stage, analysis)`
- **fn** [[services-dm_monitor-py-cleanup_old_screenshots]]`()`
- **fn** [[services-dm_monitor-py-send_telegram_alert]]`(text)`
- **fn** [[services-dm_monitor-py-send_discord_webhook]]`(env_var, content) → None`
- **fn** [[services-dm_monitor-py-get_session_path]]`()`
- **fn** [[services-dm_monitor-py-save_session]]`(context)`
- **fn** [[services-dm_monitor-py-load_session_exists]]`() → bool`
- **fn** [[services-dm_monitor-py-session_is_valid]]`(page)`
- **fn** [[services-dm_monitor-py-_screenshot_login_state]]`(page, label)`
- **fn** [[services-dm_monitor-py-_wait_for_telegram_code]]`(timeout) → str | None`
- **fn** [[services-dm_monitor-py-_wait_for_telegram_code_UNUSED]]`(timeout) → str | None`
- **fn** [[services-dm_monitor-py-do_login]]`(page, context)`
- **fn** [[services-dm_monitor-py-handle_relogin]]`(page, context)`
- **fn** [[services-dm_monitor-py-check_inbox]]`(page, context)`
- **fn** [[services-dm_monitor-py-is_login_page]]`(page)`
- **fn** [[services-dm_monitor-py-_clear_stale_chromium_session]]`()`
- **fn** [[services-dm_monitor-py-main]]`()`

## Import Statements

```python
import os
import sys
import json
import glob
import time
import random
import datetime
import base64
import uuid
import requests
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright
import cost_tracker
from eos_ai.agent_runtime import AgentRuntime
from eos_ai.context import load_context_from_env
from eos_ai.memory import AgentMemory
from eos_ai.error_handler import ErrorHandler
```
