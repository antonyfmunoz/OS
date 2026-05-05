"""
WAITING_ON checker — scans emails in WAITING_ON folder
that are older than 48h and surfaces them in Discord.
Runs every morning at 6:05am after the brief.
"""

import asyncio
import os
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

sys.path.insert(0, '/opt/OS')
from dotenv import load_dotenv
load_dotenv('/opt/OS/eos_ai/.env')
load_dotenv('/opt/OS/services/.env')

import discord

PDT = ZoneInfo('America/Los_Angeles')
GENERAL_CHANNEL_ID = 1486289444830056540


async def check_waiting_on():
    from eos_ai.context import load_context_from_env
    from eos_ai.email_gps import EmailGPS

    ctx = load_context_from_env()
    gps = EmailGPS(ctx)

    try:
        waiting = gps.get_waiting_on(limit=20)
    except Exception as e:
        print(f'[WaitingOn] get_waiting_on failed: {e}')
        return

    if not waiting:
        print('[WaitingOn] Nothing in WAITING_ON folder.')
        return

    # Filter those older than 48h
    now = datetime.now(PDT)
    overdue = []
    for email in waiting:
        date_str = email.get('date', '')
        try:
            from email.utils import parsedate_to_datetime
            email_date = parsedate_to_datetime(date_str)
            age = now - email_date.astimezone(PDT)
            if age.total_seconds() > 48 * 3600:
                email['age_days'] = age.days
                overdue.append(email)
        except Exception:
            continue

    if not overdue:
        print(f'[WaitingOn] {len(waiting)} waiting, none overdue.')
        return

    print(f'[WaitingOn] {len(overdue)} overdue items found.')

    intents = discord.Intents.default()
    client = discord.Client(intents=intents)

    @client.event
    async def on_ready():
        channel = client.get_channel(GENERAL_CHANNEL_ID)
        if not channel:
            print(f'[WaitingOn] Channel {GENERAL_CHANNEL_ID} not found.')
            await client.close()
            return

        lines = [f'⏳ **Waiting on — {len(overdue)} overdue:**']
        for e in overdue[:5]:
            age = e.get('age_days', '?')
            sender = e.get('from', 'Unknown')
            subject = e.get('subject', 'No subject')
            lines.append(f'• {sender} — {subject[:60]} ({age}d ago)')
        lines.append('\nReply `!followup [email_id]` to draft a follow-up.')

        await channel.send('\n'.join(lines))
        await client.close()

    token = os.getenv('DISCORD_BOT_TOKEN')
    if not token:
        print('[WaitingOn] DISCORD_BOT_TOKEN not set.')
        return

    await client.start(token)


if __name__ == '__main__':
    asyncio.run(check_waiting_on())
