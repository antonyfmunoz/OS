---
type: codebase-file
path: services/discord_bot.py
module: services.discord_bot
lines: 4547
size: 169683
tags: [critical, entry-point]
generated: 2026-04-12
---

# services/discord_bot.py

> **CRITICAL FILE** — Core infrastructure. Read before modifying.

> **ENTRY POINT** — Contains `if __name__` or server start.

EntrepreneurOS Discord Bot — DEX conversational layer.

Auto-joins founder's voice channel. Routes text through EOS gateway.
Smart routing: simple → local Qwen (free) → Claude via EOS.
AI name is user-configurable via BIS or AI_NAME env var.
...

**Lines:** 4547 | **Size:** 169,683 bytes

## Depends On

- [[eos_ai-business_instance-py]]
- [[eos_ai-context-py]]
- [[eos_ai-discord_utils-py]]
- [[eos_ai-gateway-py]]
- [[eos_ai-knowledge_integrator-py]]
- [[eos_ai-onboarding_engine-py]]
- [[eos_ai-substrate-discord_text_transport-py]]
- [[eos_ai-voice_engine-py]]

## Contains

- **class** [[services-discord_bot-py-SilenceDetectingSink]] — 4 methods
- **class** [[services-discord_bot-py-DiscordServerManager]] — 6 methods
- **fn** [[services-discord_bot-py-_handle_task_exception]]`(loop, context)`
- **fn** [[services-discord_bot-py-_detect_part]]`(text) → tuple[int, int] | None`
- **fn** [[services-discord_bot-py-_assemble_parts]]`(buf) → str`
- **fn** [[services-discord_bot-py-transcribe_with_groq]]`(audio_path) → str`
- **fn** [[services-discord_bot-py-on_error]]`(event)`
- **fn** [[services-discord_bot-py-_build_request]]`(text, intent, channel_name, username) → dict`
- **fn** [[services-discord_bot-py-_detect_pipeline_update]]`(text) → tuple[str, str] | None`
- **fn** [[services-discord_bot-py-_run_gateway]]`(text, channel_name, username, guild_id, channel_id) → str`
- **fn** [[services-discord_bot-py-handle_meeting_voice]]`(text, meeting_type, channel) → str`
- **fn** [[services-discord_bot-py-start_meeting_mode]]`(meeting_type, lead_name, channel) → str`
- **fn** [[services-discord_bot-py-end_active_meeting]]`(channel) → None`
- **fn** [[services-discord_bot-py-_warmup_cc_sdk]]`()`
- **fn** [[services-discord_bot-py-on_ready]]`()`
- **fn** [[services-discord_bot-py-on_voice_state_update]]`(member, before, after)`
- **fn** [[services-discord_bot-py-_listen_loop]]`(vc, text_channel) → None`
- **fn** [[services-discord_bot-py-on_message]]`(message)`
- **fn** [[services-discord_bot-py-_strip_cc_footer]]`(text) → str`
- **fn** [[services-discord_bot-py-_send_response]]`(message, output) → None`
- **fn** [[services-discord_bot-py-_setup_server_structure]]`(guild) → None`
- **fn** [[services-discord_bot-py-cmd_answer]]`(ctx, session_name)`
- **fn** [[services-discord_bot-py-cmd_watcher_status]]`(ctx)`
- **fn** [[services-discord_bot-py-cmd_brief]]`(ctx)`
- **fn** [[services-discord_bot-py-cmd_status]]`(ctx)`
- **fn** [[services-discord_bot-py-cmd_portfolio]]`(ctx)`
- **fn** [[services-discord_bot-py-cmd_join]]`(ctx)`
- **fn** [[services-discord_bot-py-cmd_leave]]`(ctx)`
- **fn** [[services-discord_bot-py-cmd_say]]`(ctx)`
- **fn** [[services-discord_bot-py-cmd_outcome]]`(ctx)`
- **fn** [[services-discord_bot-py-cmd_eod]]`(ctx)`
- **fn** [[services-discord_bot-py-cmd_accept]]`(ctx, event_id)`
- **fn** [[services-discord_bot-py-cmd_decline]]`(ctx, event_id)`
- **fn** [[services-discord_bot-py-cmd_approve]]`(ctx, approval_id)`
- **fn** [[services-discord_bot-py-cmd_approve_followup]]`(ctx)`
- **fn** [[services-discord_bot-py-cmd_force_send]]`(ctx)`
- **fn** [[services-discord_bot-py-cmd_confidential]]`(ctx)`
- **fn** [[services-discord_bot-py-cmd_pending]]`(ctx)`
- **fn** [[services-discord_bot-py-cmd_relationship]]`(ctx)`
- **fn** [[services-discord_bot-py-cmd_nurture]]`(ctx)`
- **fn** [[services-discord_bot-py-cmd_expenses]]`(ctx)`
- **fn** [[services-discord_bot-py-cmd_setup]]`(ctx)`
- **fn** [[services-discord_bot-py-cmd_align]]`(ctx)`
- **fn** [[services-discord_bot-py-cmd_report]]`(ctx, report_type)`
- **fn** [[services-discord_bot-py-cmd_onboard]]`(ctx)`
- **fn** [[services-discord_bot-py-cmd_sync]]`(ctx)`
- **fn** [[services-discord_bot-py-cmd_inbox]]`(ctx)`
- **fn** [[services-discord_bot-py-cmd_draft]]`(ctx)`
- **fn** [[services-discord_bot-py-cmd_cal]]`(ctx, period)`
- **fn** [[services-discord_bot-py-cmd_block]]`(ctx)`
- **fn** [[services-discord_bot-py-cmd_focus]]`(ctx, hours)`
- **fn** [[services-discord_bot-py-cmd_waiting]]`(ctx)`
- **fn** [[services-discord_bot-py-cmd_verify_inbox]]`(ctx)`
- **fn** [[services-discord_bot-py-cmd_folder_update]]`(ctx, folder)`
- **fn** [[services-discord_bot-py-cmd_delegated]]`(ctx)`
- **fn** [[services-discord_bot-py-cmd_subscriptions]]`(ctx)`
- **fn** [[services-discord_bot-py-cmd_add_sub]]`(ctx)`
- **fn** [[services-discord_bot-py-cmd_help]]`(ctx)`
- **fn** [[services-discord_bot-py-post_to_channel]]`(channel_name, content) → bool`
- **fn** [[services-discord_bot-py-post_morning_brief]]`(brief) → None`
- **fn** [[services-discord_bot-py-post_outreach_alert]]`(alert) → None`
- **fn** [[services-discord_bot-py-post_win]]`(win) → None`
- **fn** [[services-discord_bot-py-cmd_drip]]`(ctx)`
- **fn** [[services-discord_bot-py-cmd_buyback]]`(ctx, income)`
- **fn** [[services-discord_bot-py-cmd_logtime]]`(ctx)`
- **fn** [[services-discord_bot-py-cmd_timeaudit]]`(ctx)`
- **fn** [[services-discord_bot-py-cmd_perfectweek]]`(ctx)`
- **fn** [[services-discord_bot-py-cmd_camcorder]]`(ctx)`
- **fn** [[services-discord_bot-py-cmd_drive]]`(ctx)`
- **fn** [[services-discord_bot-py-cmd_driveaudit]]`(ctx)`
- **fn** [[services-discord_bot-py-cmd_createfolder]]`(ctx)`
- **fn** [[services-discord_bot-py-cmd_trip]]`(ctx)`
- **fn** [[services-discord_bot-py-cmd_nolist]]`(ctx)`
- **fn** [[services-discord_bot-py-cmd_noadd]]`(ctx)`
- **fn** [[services-discord_bot-py-cmd_energy]]`(ctx)`
- **fn** [[services-discord_bot-py-cmd_year]]`(ctx)`
- **fn** [[services-discord_bot-py-cmd_rocks]]`(ctx)`
- **fn** [[services-discord_bot-py-cmd_invoices]]`(ctx)`
- **fn** [[services-discord_bot-py-cmd_invoice]]`(ctx)`
- **fn** [[services-discord_bot-py-cmd_expensereport]]`(ctx, month)`
- **fn** [[services-discord_bot-py-cmd_budget]]`(ctx, target)`
- **fn** [[services-discord_bot-py-cmd_briefdoc]]`(ctx)`
- **fn** [[services-discord_bot-py-cmd_board]]`(ctx)`
- **fn** [[services-discord_bot-py-cmd_investor]]`(ctx)`
- **fn** [[services-discord_bot-py-cmd_slides]]`(ctx)`
- **fn** [[services-discord_bot-py-cmd_factcheck]]`(ctx)`
- **fn** [[services-discord_bot-py-cmd_dates]]`(ctx)`
- **fn** [[services-discord_bot-py-cmd_adddate]]`(ctx)`
- **fn** [[services-discord_bot-py-cmd_gift]]`(ctx)`
- **fn** [[services-discord_bot-py-cmd_flights]]`(ctx)`
- **fn** [[services-discord_bot-py-cmd_hotels]]`(ctx)`
- **fn** [[services-discord_bot-py-cmd_restaurants]]`(ctx)`
- **fn** [[services-discord_bot-py-cmd_proofread]]`(ctx)`
- **fn** [[services-discord_bot-py-cmd_minutes]]`(ctx)`
- **fn** [[services-discord_bot-py-cmd_okr]]`(ctx, subcommand)`
- **fn** [[services-discord_bot-py-cmd_event]]`(ctx)`
- **fn** [[services-discord_bot-py-cmd_talkingpoints]]`(ctx)`
- **fn** [[services-discord_bot-py-cmd_pr]]`(ctx)`
- **fn** [[services-discord_bot-py-cmd_board_update]]`(ctx, venture_id)`
- **fn** [[services-discord_bot-py-cmd_announce]]`(ctx)`
- **fn** [[services-discord_bot-py-cmd_crisis]]`(ctx)`
- **fn** [[services-discord_bot-py-cmd_itinerary]]`(ctx)`
- **fn** [[services-discord_bot-py-cmd_approve_task]]`(ctx, task_id)`
- **fn** [[services-discord_bot-py-cmd_tasks]]`(ctx)`
- **fn** [[services-discord_bot-py-cmd_agent_results]]`(ctx)`
- **fn** [[services-discord_bot-py-cmd_trace]]`(ctx, limit)`

## Import Statements

```python
import asyncio
import logging
import os
import re
import sys
import tempfile
import traceback
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
import discord
from discord.ext import commands
import wave
import time
from discord.sinks import Sink as AudioSink
from dotenv import load_dotenv
from eos_ai.gateway import EOSGateway
from eos_ai.context import load_context_from_env
from eos_ai.knowledge_integrator import KnowledgeIntegrator
from eos_ai.voice_engine import VoiceEngine
from eos_ai.business_instance import get_ai_name
from eos_ai.discord_utils import chunk_message
from eos_ai.discord_utils import post_to_webhook
from eos_ai.substrate.discord_text_transport import maybe_mirror_discord_text_message as _maybe_pseudo_live_text
from handlers.intent_handler import run_gateway as _handler_run_gateway
from handlers.intent_handler import CHANNEL_MAP as _HANDLER_CHANNEL_MAP
from handlers.pipeline_handler import handle_pipeline_update
from handlers.cc_command_handler import try_inline_commands
from eos_ai.onboarding_engine import OnboardingEngine as _OnboardingEngine
```
