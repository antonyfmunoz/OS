"""
EOD Sync — 6pm PDT daily closing loop.
Sections: Meetings today | Purchases/expenses |
Project updates | Decisions made.
Posts to #morning-brief channel.
"""

import os
import sys
import json
import asyncio
import discord
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from dotenv import load_dotenv

sys.path.insert(0, os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS")
load_dotenv(os.path.join(os.environ.get('UMH_ROOT') or os.environ.get('OS_ROOT') or os.environ.get('EOS_ROOT') or '/opt/OS', 'eos_ai', '.env'))
load_dotenv(os.path.join(os.environ.get('UMH_ROOT') or os.environ.get('OS_ROOT') or os.environ.get('EOS_ROOT') or '/opt/OS', 'services', '.env'))

PDT = ZoneInfo('America/Los_Angeles')
MORNING_BRIEF_CHANNEL_ID = 1485765524766982234


def _get_todays_meetings() -> list[str]:
    try:
        from eos_ai.gws_connector import GWSConnector
        gws = GWSConnector()
        events = gws.get_today_events()
        result = []
        for e in events[:8]:
            title = e.get('title', 'Untitled')
            start = e.get('start', '')
            if start and 'T' in str(start):
                try:
                    dt = datetime.fromisoformat(str(start).replace('Z', '+00:00'))
                    label = dt.strftime('%I:%M%p').lstrip('0')
                except Exception:
                    label = str(start)[11:16]
            else:
                label = str(start)[:10]
            result.append(f'{label} — {title}')
        return result
    except Exception as e:
        print(f'[EOD] Meetings: {e}')
        return [f'unavailable ({e})']


def _get_todays_purchases() -> list[str]:
    """Pull receipts from expense tracker — processes new emails and returns monthly summary."""
    try:
        from eos_ai.expense_tracker import (
            process_receipt_emails,
            get_monthly_summary,
        )
        process_receipt_emails()
        summary = get_monthly_summary()
        if summary.get('total', 0) > 0:
            lines = [f'💳 Month to date: ${summary["total"]:,.2f}']
            for cat, amt in sorted(
                summary['by_category'].items(),
                key=lambda x: x[1], reverse=True
            )[:5]:
                lines.append(f'  • {cat}: ${amt:,.2f}')
            return lines
        return ['💳 No expenses logged this month.']
    except Exception as e:
        print(f'[EOD] Purchases: {e}')
        return [f'💳 Expenses unavailable: {e}']


def _get_todays_project_updates(ctx) -> list[str]:
    try:
        from eos_ai.db import get_conn
        since = (datetime.now(timezone.utc) - timedelta(hours=12)).isoformat()
        with get_conn(ctx.org_id) as cur:
            cur.execute('''
                SELECT event_type, payload_json
                FROM events
                WHERE org_id = %s
                  AND event_type IN (
                    'pipeline_entry', 'icp_signal',
                    'lead_qualified', 'email_classified'
                  )
                  AND created_at > %s
                ORDER BY created_at DESC
                LIMIT 10
            ''', (ctx.org_id, since))
            rows = cur.fetchall()

        result = []
        email_count = 0
        for event_type, data in rows:
            if isinstance(data, str):
                data = json.loads(data)
            if event_type == 'email_classified':
                email_count += 1
            elif event_type == 'pipeline_entry':
                name = data.get('name', '')
                stage = data.get('stage', '')
                if name:
                    result.append(f'Pipeline: {name} → {stage}')
            elif event_type in ('icp_signal', 'lead_qualified'):
                name = data.get('name', '') or data.get('handle', '')
                score = data.get('score', '')
                if name:
                    result.append(f'Lead: {name} ({score}/10)' if score else f'Lead: {name}')

        if email_count:
            result.insert(0, f'Email GPS: {email_count} emails processed')
        return result
    except Exception as e:
        print(f'[EOD] Project updates: {e}')
        return [f'unavailable ({e})']


def _get_todays_decisions(ctx) -> list[str]:
    """Decisions = dex_question events answered today."""
    try:
        from eos_ai.db import get_conn
        since = (datetime.now(timezone.utc) - timedelta(hours=12)).isoformat()
        with get_conn(ctx.org_id) as cur:
            cur.execute('''
                SELECT payload_json
                FROM events
                WHERE org_id = %s
                  AND event_type = 'dex_question'
                  AND payload_json->>'answered' = 'true'
                  AND created_at > %s
                ORDER BY created_at DESC
                LIMIT 5
            ''', (ctx.org_id, since))
            rows = cur.fetchall()

        result = []
        for row in rows:
            data = row[0]
            if isinstance(data, str):
                data = json.loads(data)
            q = data.get('question', '')
            a = data.get('answer', '')
            if q:
                result.append(f'{q[:50]} → {a[:30]}' if a else q[:70])
        return result
    except Exception as e:
        print(f'[EOD] Decisions: {e}')
        return [f'unavailable ({e})']


def build_eod_message() -> str:
    from eos_ai.context import load_context_from_env
    ctx = load_context_from_env()

    now = datetime.now(PDT)
    today_str = now.strftime('%A, %B %d')
    sections = []

    meetings = _get_todays_meetings()
    if meetings:
        section = ['**📅 Meetings today:**']
        for m in meetings:
            section.append(f'  • {m}')
        sections.append('\n'.join(section))

    purchases = _get_todays_purchases()
    if purchases:
        section = ['**💳 Purchases/expenses:**']
        for p in purchases:
            section.append(f'  • {p}')
        sections.append('\n'.join(section))

    updates = _get_todays_project_updates(ctx)
    if updates:
        section = ['**🔨 Project updates:**']
        for u in updates:
            section.append(f'  • {u}')
        sections.append('\n'.join(section))

    decisions = _get_todays_decisions(ctx)
    if decisions:
        section = ['**🎯 Decisions made:**']
        for d in decisions:
            section.append(f'  • {d}')
        sections.append('\n'.join(section))

    # Overdue delegations
    try:
        from eos_ai.delegation_tracker import get_overdue_delegations
        overdue_dels = get_overdue_delegations(ctx)
        if overdue_dels:
            section = [f'**🔄 Overdue delegations ({len(overdue_dels)}):**']
            for d in overdue_dels[:3]:
                section.append(f'  • {d.get("task","")[:60]} → {d.get("delegated_to","")}')
            sections.append('\n'.join(section))
    except Exception as e:
        print(f'[EOD] Delegations: {e}')

    # Energy check-in prompt
    sections.append(
        '**⚡ Energy Check-in:**\n'
        '`!energy [1-10] | [what drained you] | [what energized you]`\n'
        '_Feeds your DRIP Matrix and helps DEX protect your energy._'
    )

    body = '\n\n'.join(sections) if sections else 'No activity logged today.'

    return (
        f'━━━━━━━━━━━━━━━━━━━━━━━━\n'
        f'🌆 **EOD Sync — {today_str}**\n'
        f'━━━━━━━━━━━━━━━━━━━━━━━━\n'
        f'\n'
        f'{body}\n'
        f'\n'
        f'_Reply with anything that needs to carry forward to tomorrow._\n'
        f'━━━━━━━━━━━━━━━━━━━━━━━━\n'
        f'— DEX'
    )


async def build_and_post_eod():
    message = build_eod_message()

    intents = discord.Intents.default()
    client = discord.Client(intents=intents)

    @client.event
    async def on_ready():
        channel = client.get_channel(MORNING_BRIEF_CHANNEL_ID)
        if channel:
            if len(message) > 1900:
                chunks = [message[i:i+1900] for i in range(0, len(message), 1900)]
                for chunk in chunks:
                    await channel.send(chunk)
            else:
                await channel.send(message)
        await client.close()

    await client.start(os.getenv('DISCORD_BOT_TOKEN'))


if __name__ == '__main__':
    asyncio.run(build_and_post_eod())
