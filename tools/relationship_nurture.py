"""
Relationship nurturing — checks for contacts not heard from in 30+ days
and surfaces them. Runs weekly on Mondays at 7am PDT.
"""

import os
import sys
import asyncio
import discord
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from dotenv import load_dotenv

sys.path.insert(0, '/opt/OS')
load_dotenv('/opt/OS/umh/.env')
load_dotenv('/opt/OS/services/.env')

PDT = ZoneInfo('America/Los_Angeles')
GENERAL_CHANNEL_ID = 1486289444830056540


async def check_relationships():
    from umh.environments.system_context import load_context_from_env
    ctx = load_context_from_env()

    import requests as _req
    token = os.getenv('NOTION_API_KEY')
    db_id = os.getenv('NOTION_MEETINGS_ID')
    if not token or not db_id:
        print('[Nurture] NOTION_API_KEY or NOTION_MEETINGS_ID not set — exiting')
        return

    now = datetime.now(PDT)
    cutoff_recent = (now - timedelta(days=30)).date().isoformat()
    cutoff_old = (now - timedelta(days=90)).date().isoformat()

    headers = {
        'Authorization': f'Bearer {token}',
        'Notion-Version': '2022-06-28',
        'Content-Type': 'application/json',
    }

    try:
        resp = _req.post(
            f'https://api.notion.com/v1/databases/{db_id}/query',
            headers=headers,
            json={'filter': {'and': [
                {'property': 'Status', 'select': {'equals': 'Completed'}},
                {'property': 'Date', 'date': {'on_or_after': cutoff_old}},
                {'property': 'Date', 'date': {'before': cutoff_recent}},
            ]}},
            timeout=10,
        )
        meetings = resp.json().get('results', [])
    except Exception as e:
        print(f'[Nurture] Query failed: {e}')
        return

    if not meetings:
        print('[Nurture] No cold contacts found')
        return

    seen = set()
    cold_contacts = []
    for m in meetings:
        props = m.get('properties', {})
        person = (
            props.get('Person', {}).get('rich_text', [{}])[0]
            .get('plain_text', '')
        )
        date = props.get('Date', {}).get('date', {}).get('start', '')
        venture = props.get('Venture', {}).get('select', {}).get('name', '')
        if person and person not in seen:
            seen.add(person)
            cold_contacts.append({
                'person': person,
                'last_contact': date[:10] if date else 'unknown',
                'venture': venture,
            })

    if not cold_contacts:
        return

    # Score and sort by relationship health (lowest first)
    try:
        from umh.runtime_engine.person_recognition import score_relationship_health
        for c in cold_contacts:
            h = score_relationship_health(name=c['person'], ctx=ctx)
            c['health_score'] = h.get('score', 0.5)
            c['health_status'] = h.get('status', 'Unknown')
        cold_contacts.sort(key=lambda x: x.get('health_score', 0.5))
    except Exception:
        pass

    intents = discord.Intents.default()
    client = discord.Client(intents=intents)

    @client.event
    async def on_ready():
        channel = client.get_channel(GENERAL_CHANNEL_ID)
        if not channel:
            await client.close()
            return

        lines = [
            f'🤝 **Relationship check — {len(cold_contacts)} contacts going cold:**'
        ]
        for c in cold_contacts[:8]:
            lines.append(
                f'• {c["person"]} — {c.get("health_status", "")} '
                f'({c.get("health_score", 0.5):.0%}) — '
                f'last contact {c["last_contact"]} ({c["venture"]})'
            )
        lines.append('\nReply `!nurture [name]` to draft a check-in message.')

        await channel.send('\n'.join(lines))
        await client.close()

    discord_token = os.getenv('DISCORD_BOT_TOKEN')
    if not discord_token:
        print('[Nurture] DISCORD_BOT_TOKEN not set — exiting')
        return
    await client.start(discord_token)


if __name__ == '__main__':
    asyncio.run(check_relationships())
