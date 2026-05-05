"""
No-show detector — checks meetings that started 30+ min ago with no
outcome captured, marks as no-show, triggers recovery flow.
Runs every 15 minutes via cron.
"""

import os
import sys
import json
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


async def detect_noshows():
    from umh.environments.system_context import load_context_from_env
    from umh.runtime_engine.model_router import get_router, TaskType

    ctx = load_context_from_env()

    try:
        import requests as _req
        token = os.getenv('NOTION_API_KEY')
        db_id = os.getenv('NOTION_MEETINGS_ID')
        if not token or not db_id:
            print('[NoShow] NOTION_API_KEY or NOTION_MEETINGS_ID not set — exiting')
            return

        now = datetime.now(PDT)
        window_start = (now - timedelta(minutes=90)).isoformat()
        window_end = (now - timedelta(minutes=30)).isoformat()

        headers = {
            'Authorization': f'Bearer {token}',
            'Notion-Version': '2022-06-28',
            'Content-Type': 'application/json',
        }
        resp = _req.post(
            f'https://api.notion.com/v1/databases/{db_id}/query',
            headers=headers,
            json={'filter': {'and': [
                {'property': 'Status', 'select': {'equals': 'Scheduled'}},
                {'property': 'Date', 'date': {'on_or_after': window_start}},
                {'property': 'Date', 'date': {'on_or_before': window_end}},
            ]}},
            timeout=10,
        )
        meetings = resp.json().get('results', [])
    except Exception as e:
        print(f'[NoShow] Notion query failed: {e}')
        return

    if not meetings:
        print(f'[NoShow] No unresolved meetings in 30-90 min window')
        return

    router = get_router()
    model = router.route(TaskType.FAST_RESPONSE)

    intents = discord.Intents.default()
    client = discord.Client(intents=intents)

    @client.event
    async def on_ready():
        channel = client.get_channel(GENERAL_CHANNEL_ID)
        if not channel:
            print('[NoShow] Could not get Discord channel')
            await client.close()
            return

        for m in meetings:
            props = m.get('properties', {})
            person = (
                props.get('Person', {}).get('rich_text', [{}])[0]
                .get('plain_text', 'Unknown')
            )
            notion_id = m['id']

            try:
                import requests as _req2
                token2 = os.getenv('NOTION_API_KEY')
                _req2.patch(
                    f'https://api.notion.com/v1/pages/{notion_id}',
                    headers={
                        'Authorization': f'Bearer {token2}',
                        'Notion-Version': '2022-06-28',
                        'Content-Type': 'application/json',
                    },
                    json={'properties': {
                        'Status': {'select': {'name': 'No-show'}}
                    }},
                    timeout=10,
                )
            except Exception as e:
                print(f'[NoShow] Notion update failed for {person}: {e}')

            try:
                draft = router.call(model, f"""Draft a brief no-show recovery email for {person}.
Warm, no pressure, offer to reschedule.
Under 4 sentences. Include [Calendly link] placeholder.
Subject line included.""").strip()
            except Exception as e:
                draft = f'[Draft unavailable: {e}]'

            # Queue for approval
            try:
                from umh.storage.adapters.neon import get_conn
                import json as _json
                with get_conn(ctx.org_id) as cur:
                    cur.execute('''
                        INSERT INTO events
                        (org_id, event_type, payload_json, handled_by)
                        VALUES (%s, %s, %s, %s)
                    ''', (
                        str(ctx.org_id),
                        'email_draft_pending',
                        _json.dumps({
                            'draft': draft,
                            'to_name': person,
                            'type': 'noshow_recovery',
                            'status': 'pending_approval',
                        }),
                        'dex_noshow',
                    ))
            except Exception as e:
                print(f'[NoShow] Neon queue failed: {e}')

            msg = (
                f'⚠️ **No-show: {person}**\n'
                f'Marked in Notion. Recovery email drafted:\n'
                f'```\n{draft[:500]}\n```\n'
                f'`!approve_followup` to send.'
            )
            await channel.send(msg)

        await client.close()

    token_discord = os.getenv('DISCORD_BOT_TOKEN')
    if not token_discord:
        print('[NoShow] DISCORD_BOT_TOKEN not set — exiting')
        return
    await client.start(token_discord)


if __name__ == '__main__':
    asyncio.run(detect_noshows())
