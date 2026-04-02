---
name: notion-discord-pattern
description: "Use when building any feature that generates reports, briefs, summaries, or structured content for Discord. Ensures correct architecture: Notion is the visual layer, Discord is the interaction layer. Never send full content to Discord."
allowed-tools: "Read"
effort: low
trigger: both
version: "1.0"
last_updated: "2026-04-02"
---

# Notion + Discord Architecture Pattern

## Purpose
Canonical pattern for how EOS surfaces
structured content. Built once. Every
brief, report, and summary uses this.

## The Rule
Notion = visual layer (READ and REVIEW)
Discord = interaction layer (COMMAND and RESPOND)

Never send full report content to Discord.
Always write to Notion first.
Send the Notion URL to Discord.

## The Pattern

Every report/brief/summary follows this:

```python
# 1. Generate content as a dict
content = {
    'binding_constraint': '...',
    'one_objective': '...',
    # etc.
}

# 2. Write to Notion via NotionPublisher
from eos_ai.notion_publisher import get_publisher
publisher = get_publisher(ctx)
url = publisher.publish_morning_brief(
    content=content,
)

# 3. Send link to Discord
from eos_ai.discord_utils import post_to_webhook
import os
webhook = os.getenv('DISCORD_BRIEF_WEBHOOK', '')
if url:
    post_to_webhook(
        f'Brief ready\n{url}',
        webhook_url=webhook,
    )
else:
    # Fallback only if Notion fails
    post_to_webhook(
        summary[:1800],
        webhook_url=webhook,
    )
```

## Available Publisher Methods

```python
publisher.publish_morning_brief(content=dict)
publisher.publish_intel_brief(content=dict)
publisher.publish_constraint_diagnosis(
    venture_id=str, diagnosis=dict)
publisher.publish_portfolio_status(status=dict)
publisher.publish_eod_sync(content=dict)
publisher.publish_ceo_delegation(content=dict)
```

All methods return a Notion URL (str) or ''
on failure. Empty string = Notion failed,
use fallback.

## What Stays in Discord (NOT Notion)
- Approval requests (interactive)
- Error alerts (real-time)
- Stage transition alerts (short, actionable)
- "Brief ready" confirmations (the new pattern)
- Proactive alerts (urgent, time-sensitive)

## What Goes to Notion First
- Morning briefs
- Intelligence briefs
- CEO delegation reports
- Constraint diagnoses
- Portfolio status reports
- EOD syncs
- Weekly reviews
- Postmortems

## Env Vars
- NOTION_API_KEY — integration secret
- NOTION_MORNING_BRIEF_ID — daily brief DB
- NOTION_{VENTURE}_{TYPE}_DB — per-venture DBs
- DISCORD_BRIEF_WEBHOOK — webhook URL

## Gotchas
- Notion API has 100-block limit per page create.
  Publisher already caps at 100 blocks.
- If NOTION_API_KEY is unset, publisher returns ''
  silently. Always check return value.
- NOTION_MORNING_BRIEF_ID is a database ID,
  not a page ID. The old write_to_notion_dashboard
  used page_id parent — that was wrong.
- Discord webhook messages have 2000 char limit.
  URLs are always under 100 chars. Safe.
- The publisher deduplicates by title per day.
  Running twice returns the existing URL.
