"""
Day Reminder — fires reminders throughout the day.
Runs every 5 minutes via cron.
Checks for events starting in the next 10-15 minutes
and fires a Discord alert if not already sent.
"""

import os
import sys
import asyncio
import discord
import json
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from dotenv import load_dotenv

sys.path.insert(0, os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS")
load_dotenv(os.path.join(os.environ.get('UMH_ROOT') or os.environ.get('OS_ROOT') or os.environ.get('EOS_ROOT') or '/opt/OS', 'runtime', '.env'))
load_dotenv(os.path.join(os.environ.get('UMH_ROOT') or os.environ.get('OS_ROOT') or os.environ.get('EOS_ROOT') or '/opt/OS', 'services', '.env'))

PDT = ZoneInfo('America/Los_Angeles')
STATE_FILE = '/tmp/day_reminder_state.json'
GENERAL_CHANNEL_ID = int(os.getenv('DISCORD_GENERAL_CHANNEL_ID', '0'))


async def check_and_remind():
    from adapters.google_workspace.gws_connector import GWSConnector
    from substrate.understanding.intelligence.person_recognition import build_intelligence_profile

    gws = GWSConnector()
    now = datetime.now(PDT)

    try:
        with open(STATE_FILE) as f:
            sent = json.load(f)
    except Exception:
        sent = {}

    cutoff = (now - timedelta(hours=24)).isoformat()
    sent = {k: v for k, v in sent.items() if v > cutoff}

    try:
        events = gws.get_upcoming_events(days=1)
    except Exception:
        return

    alerts = []
    for event in events:
        event_id = event.get('id', '')
        if not event_id or event_id in sent:
            continue

        start_raw = event.get('start', '')
        if isinstance(start_raw, dict):
            start_raw = start_raw.get('dateTime', '')
        if not start_raw:
            continue

        try:
            from dateutil.parser import parse as _parse
            event_start = _parse(str(start_raw)).astimezone(PDT)
            minutes_until = (event_start - now).total_seconds() / 60

            if 8 <= minutes_until <= 15:
                title = event.get('title', event.get('summary', 'Meeting'))
                attendees = event.get('attendees', [])
                attendee_email = next(
                    (a.get('email') for a in attendees if not a.get('self')),
                    ''
                )

                person_context = ''
                if attendee_email:
                    try:
                        profile = build_intelligence_profile(email=attendee_email)
                        if profile and getattr(profile, 'notes', ''):
                            person_context = f'\n💡 {profile.notes[:100]}'
                    except Exception:
                        pass

                time_str = event_start.strftime('%-I:%M %p')
                meet_link = event.get('meet_link', '')

                alert = (
                    f'⏰ **{title}** in ~{int(minutes_until)} min ({time_str})'
                    + (f'\n🔗 {meet_link}' if meet_link else '')
                    + person_context
                )
                alerts.append((event_id, alert))
        except Exception:
            continue

    if not alerts:
        return

    intents = discord.Intents.default()
    client = discord.Client(intents=intents)

    @client.event
    async def on_ready():
        channel = client.get_channel(GENERAL_CHANNEL_ID)
        if channel:
            for event_id, alert in alerts:
                await channel.send(alert)
                sent[event_id] = now.isoformat()

        with open(STATE_FILE, 'w') as f:
            json.dump(sent, f)

        await client.close()

    await client.start(os.getenv('DISCORD_BOT_TOKEN'))


if __name__ == '__main__':
    asyncio.run(check_and_remind())
