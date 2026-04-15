---
type: codebase-file
path: services/telegram_control.py
module: services.telegram_control
lines: 3148
size: 118578
tags: [critical]
generated: 2026-04-12
---

# services/telegram_control.py

> **CRITICAL FILE** — Core infrastructure. Read before modifying.

*No docstring.*

**Lines:** 3148 | **Size:** 118,578 bytes

## Contains

- **fn** [[services-telegram_control-py-_get_chat_lock]]`(chat_id) → asyncio.Lock`
- **fn** [[services-telegram_control-py-parse_pipeline]]`()`
- **fn** [[services-telegram_control-py-format_lead_line]]`(card)`
- **fn** [[services-telegram_control-py-build_briefing_text]]`()`
- **fn** [[services-telegram_control-py-send_morning_briefing]]`(update, context)`
- **fn** [[services-telegram_control-py-scheduled_morning_briefing]]`(context)`
- **fn** [[services-telegram_control-py-scheduled_signal_scan]]`(context)`
- **fn** [[services-telegram_control-py-schedule_morning_briefing]]`(app)`
- **fn** [[services-telegram_control-py-run_command]]`(command, update)`
- **fn** [[services-telegram_control-py-research]]`(update, context)`
- **fn** [[services-telegram_control-py-market]]`(update, context)`
- **fn** [[services-telegram_control-py-content]]`(update, context)`
- **fn** [[services-telegram_control-py-outreach]]`(update, context)`
- **fn** [[services-telegram_control-py-leads]]`(update, context)`
- **fn** [[services-telegram_control-py-sent]]`(update, context)`
- **fn** [[services-telegram_control-py-stats]]`(update, context)`
- **fn** [[services-telegram_control-py-hashtags]]`(update, context)`
- **fn** [[services-telegram_control-py-blacklist_tag]]`(update, context)`
- **fn** [[services-telegram_control-py-add_hashtag]]`(update, context)`
- **fn** [[services-telegram_control-py-move_pipeline_card_by_username]]`(username, from_stage, to_stage)`
- **fn** [[services-telegram_control-py-log_call_outcome]]`(username, outcome)`
- **fn** [[services-telegram_control-py-closed]]`(update, context)`
- **fn** [[services-telegram_control-py-revenue]]`(update, context)`
- **fn** [[services-telegram_control-py-showed]]`(update, context)`
- **fn** [[services-telegram_control-py-noshow]]`(update, context)`
- **fn** [[services-telegram_control-py-approve_cost]]`(update, context)`
- **fn** [[services-telegram_control-py-stop_scraper]]`(update, context)`
- **fn** [[services-telegram_control-py-midnight_snapshot]]`(context)`
- **fn** [[services-telegram_control-py-costs]]`(update, context)`
- **fn** [[services-telegram_control-py-report]]`(update, context)`
- **fn** [[services-telegram_control-py-scheduled_eod_report]]`(context)`
- **fn** [[services-telegram_control-py-brief]]`(update, context)`
- **fn** [[services-telegram_control-py-gateway_research]]`(update, context)`
- **fn** [[services-telegram_control-py-capture_context]]`(update, context)`
- **fn** [[services-telegram_control-py-gateway_approve]]`(update, context)`
- **fn** [[services-telegram_control-py-strategy]]`(update, context)`
- **fn** [[services-telegram_control-py-decide]]`(update, context)`
- **fn** [[services-telegram_control-py-gateway_reject]]`(update, context)`
- **fn** [[services-telegram_control-py-portfolio]]`(update, context)`
- **fn** [[services-telegram_control-py-board]]`(update, context)`
- **fn** [[services-telegram_control-py-intel]]`(update, context)`
- **fn** [[services-telegram_control-py-competitor_cmd]]`(update, context)`
- **fn** [[services-telegram_control-py-truth]]`(update, context)`
- **fn** [[services-telegram_control-py-research_cmd]]`(update, context)`
- **fn** [[services-telegram_control-py-gaps]]`(update, context)`
- **fn** [[services-telegram_control-py-domains_cmd]]`(update, context)`
- **fn** [[services-telegram_control-py-domain_cmd]]`(update, context)`
- **fn** [[services-telegram_control-py-trinity_cmd]]`(update, context)`
- **fn** [[services-telegram_control-py-connect_cmd]]`(update, context)`
- **fn** [[services-telegram_control-py-permit_cmd]]`(update, context)`
- **fn** [[services-telegram_control-py-revoke_cmd]]`(update, context)`
- **fn** [[services-telegram_control-py-aistate_cmd]]`(update, context)`
- **fn** [[services-telegram_control-py-handle_errors]]`(update, context)`
- **fn** [[services-telegram_control-py-handle_outcome]]`(update, context)`
- **fn** [[services-telegram_control-py-evolve]]`(update, context)`
- **fn** [[services-telegram_control-py-performance]]`(update, context)`
- **fn** [[services-telegram_control-py-journey]]`(update, context)`
- **fn** [[services-telegram_control-py-patterns]]`(update, context)`
- **fn** [[services-telegram_control-py-tasks_cmd]]`(update, context)`
- **fn** [[services-telegram_control-py-done_cmd]]`(update, context)`
- **fn** [[services-telegram_control-py-assign_cmd]]`(update, context)`
- **fn** [[services-telegram_control-py-model_cmd]]`(update, context)`
- **fn** [[services-telegram_control-py-gateway_pending]]`(update, context)`
- **fn** [[services-telegram_control-py-wants_voice_response]]`(text) → bool`
- **fn** [[services-telegram_control-py-_get_vi]]`(ctx) → 'VoiceInterface'`
- **fn** [[services-telegram_control-py-calendar_cmd]]`(update, context)`
- **fn** [[services-telegram_control-py-gtasks_cmd]]`(update, context)`
- **fn** [[services-telegram_control-py-gmail_cmd]]`(update, context)`
- **fn** [[services-telegram_control-py-meeting_cmd]]`(update, context)`
- **fn** [[services-telegram_control-py-handle_backfill]]`(update, context)`
- **fn** [[services-telegram_control-py-handle_sync]]`(update, context)`
- **fn** [[services-telegram_control-py-handle_media_message]]`(update, context)`
- **fn** [[services-telegram_control-py-check_model_triggers]]`(text, prefs) → str | None`
- **fn** [[services-telegram_control-py-handle_natural_message]]`(update, context)`
- **fn** [[services-telegram_control-py-executions_cmd]]`(update, context)`
- **fn** [[services-telegram_control-py-trace_cmd]]`(update, context)`
- **fn** [[services-telegram_control-py-stage_cmd]]`(update, context)`
- **fn** [[services-telegram_control-py-bis_cmd]]`(update, context)`
- **fn** [[services-telegram_control-py-pulse_cmd]]`(update, context)`
- **fn** [[services-telegram_control-py-advance_cmd]]`(update, context)`
- **fn** [[services-telegram_control-py-_run_pre_meeting_automation]]`(ctx, lead_name, bot, chat_id) → str`
- **fn** [[services-telegram_control-py-_run_post_meeting_automation]]`(ctx, lead_name, summary, action_items, next_steps, bot, chat_id) → None`
- **fn** [[services-telegram_control-py-standup_cmd]]`(update, context)`
- **fn** [[services-telegram_control-py-review_cmd]]`(update, context)`
- **fn** [[services-telegram_control-py-handle_browser_command]]`(update, context) → None`

## Import Statements

```python
import asyncio
import subprocess
import os
import sys
import json
import glob
import datetime
import tempfile
from pathlib import Path
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder
from telegram.ext import CommandHandler
from telegram.ext import ContextTypes
from telegram.ext import MessageHandler
from telegram.ext import filters
import kpi_tracker
import cost_tracker
```
