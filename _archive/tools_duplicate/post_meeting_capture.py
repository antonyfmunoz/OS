"""
Post-meeting capture — polls for recently ended calendar events
and prompts DEX to capture outcomes in Discord.

Runs every 15 minutes via cron. Deduplicates via /tmp/post_meeting_state.json.
"""

import os
import sys
import json
import asyncio
import discord
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
from dotenv import load_dotenv

sys.path.insert(0, '/opt/OS')
load_dotenv('/opt/OS/services/.env')
load_dotenv('/opt/OS/umh/.env')

PDT = ZoneInfo('America/Los_Angeles')
STATE_FILE = '/tmp/post_meeting_state.json'
GENERAL_CHANNEL_ID = 1486289444830056540


def load_state() -> dict:
    try:
        with open(STATE_FILE) as f:
            return json.load(f)
    except Exception:
        return {}


def save_state(state: dict) -> None:
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f)


async def check_and_prompt() -> None:
    from umh.runtime_engine.gws_connector import GWSConnector

    state = load_state()
    gws = GWSConnector()

    now = datetime.now(timezone.utc)
    window_start = now - timedelta(minutes=30)

    data = gws._run(
        "calendar", "events", "list",
        params={
            "calendarId":   "primary",
            "timeMin":      window_start.isoformat(),
            "timeMax":      now.isoformat(),
            "singleEvents": True,
            "orderBy":      "startTime",
        },
    )
    if data is None:
        print("[PostMeeting] Calendar fetch failed.")
        return
    events = data.get("items", [])

    if not events:
        print('[PostMeeting] No recently ended events.')
        return

    # Filter to events that actually ended (end time <= now)
    ended = []
    for event in events:
        end_raw = event.get('end', {}).get('dateTime', '')
        if not end_raw:
            continue
        try:
            from dateutil import parser as dp
            end_dt = dp.parse(end_raw)
            if end_dt.tzinfo is None:
                end_dt = end_dt.replace(tzinfo=timezone.utc)
            if end_dt <= now:
                ended.append(event)
        except Exception:
            continue

    if not ended:
        print('[PostMeeting] No ended events in window.')
        return

    intents = discord.Intents.default()
    intents.message_content = True
    client = discord.Client(intents=intents)

    @client.event
    async def on_ready():
        channel = client.get_channel(GENERAL_CHANNEL_ID)
        if not channel:
            print(f'[PostMeeting] Channel {GENERAL_CHANNEL_ID} not found.')
            await client.close()
            return

        for event in ended:
            event_id = event.get('id', '')
            if not event_id or event_id in state:
                continue

            title = event.get('summary', 'Untitled')
            attendees = event.get('attendees', [])
            person = next(
                (a.get('displayName') or a.get('email', '') for a in attendees if not a.get('self')),
                'Unknown',
            )

            msg = (
                f"📋 **Post-meeting capture: {title}**\n"
                f"👤 With: {person}\n"
                f"Just ended. What happened?\n\n"
                f"Reply: `!outcome {event_id} [what was decided] | [open follow-ups]`\n"
                f"Or reply naturally and I'll capture it."
            )
            await channel.send(msg)
            state[event_id] = now.isoformat()
            print(f'[PostMeeting] Prompted for: {title}')

        save_state(state)
        await client.close()

    token = os.getenv('DISCORD_BOT_TOKEN')
    if not token:
        print('[PostMeeting] No DISCORD_BOT_TOKEN set.')
        return

    await client.start(token)


if __name__ == '__main__':
    asyncio.run(check_and_prompt())
