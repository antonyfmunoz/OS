"""
Mid-day check-in — runs at 12:30pm PDT.
Surfaces afternoon agenda, urgent pending items,
and one afternoon priority.
"""

import os
import sys
import asyncio
import discord
from datetime import datetime
from zoneinfo import ZoneInfo
from dotenv import load_dotenv

sys.path.insert(0, os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS")
load_dotenv(os.path.join(os.environ.get('UMH_ROOT') or os.environ.get('OS_ROOT') or os.environ.get('EOS_ROOT') or '/opt/OS', 'runtime', '.env'))
load_dotenv(os.path.join(os.environ.get('UMH_ROOT') or os.environ.get('OS_ROOT') or os.environ.get('EOS_ROOT') or '/opt/OS', 'services', '.env'))

PDT = ZoneInfo('America/Los_Angeles')
GENERAL_CHANNEL_ID = int(os.getenv('DISCORD_GENERAL_CHANNEL_ID', '0'))


async def midday_checkin():
    from runtime.gws_connector import GWSConnector
    from runtime.context import load_context_from_env
    from runtime.db import get_conn
    from execution.runtime.model_router import get_router, TaskType
    from dateutil.parser import parse as _parse

    ctx = load_context_from_env()
    gws = GWSConnector()
    router = get_router()
    model = router.route(TaskType.FAST_RESPONSE)
    now = datetime.now(PDT)

    try:
        events = gws.get_upcoming_events(days=1)
        afternoon = []
        for e in events:
            start = e.get('start', '')
            if isinstance(start, dict):
                start = start.get('dateTime', '')
            try:
                dt = _parse(str(start)).astimezone(PDT)
                if dt.hour >= 12 and dt.date() == now.date():
                    afternoon.append(
                        f'{dt.strftime("%-I:%M %p")}: '
                        f'{e.get("title", e.get("summary", "Event"))}'
                    )
            except Exception:
                continue
    except Exception:
        afternoon = []

    try:
        with get_conn(ctx.org_id) as cur:
            cur.execute('''
                SELECT payload_json FROM events
                WHERE org_id = %s
                AND event_type IN ('email_draft_pending', 'dex_question')
                AND (payload_json->>\'status\' = \'pending_approval\'
                     OR payload_json->>\'answered\' IS NULL)
                AND created_at >= NOW() - INTERVAL '24 hours'
                LIMIT 5
            ''', (str(ctx.org_id),))
            pending = cur.fetchall()
    except Exception:
        pending = []

    afternoon_text = '\n'.join(afternoon) if afternoon else 'Clear afternoon'
    pending_text = f'{len(pending)} items pending approval' if pending else 'Nothing pending'

    summary = router.call(model, f"""You are DEX, EA to the founder.
Mid-day check-in. Be brief — 3 sentences max.

Afternoon schedule:
{afternoon_text}

Pending items: {pending_text}

Surface anything urgent. Confirm afternoon is on track.
Suggest one afternoon priority if relevant.""").strip()

    message = (
        f'🌤️ **Mid-day — {now.strftime("%-I:%M %p")}**\n\n'
        f'{summary}'
        + (f'\n\n**Afternoon:**\n' + '\n'.join(f'• {e}' for e in afternoon[:4]) if afternoon else '')
    )

    intents = discord.Intents.default()
    client = discord.Client(intents=intents)

    @client.event
    async def on_ready():
        channel = client.get_channel(GENERAL_CHANNEL_ID)
        if channel:
            await channel.send(message[:1900])
        await client.close()

    await client.start(os.getenv('DISCORD_BOT_TOKEN'))


if __name__ == '__main__':
    asyncio.run(midday_checkin())
