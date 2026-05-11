"""
Deadline Monitor — checks tasks with due dates
approaching or overdue. Runs every morning at 6:10am.
Alerts in Discord.
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
GENERAL_CHANNEL_ID = 1486289444830056540


async def check_deadlines():
    from runtime.context import load_context_from_env
    import requests as _req

    ctx = load_context_from_env()
    now = datetime.now(PDT)
    tomorrow = now + timedelta(days=1)

    token = os.getenv('NOTION_API_KEY')
    dbs = {
        'Lyfe Institute': os.getenv('NOTION_YOUR_LIST_LYFE'),
        'Empyrean Creative': os.getenv('NOTION_YOUR_LIST_EMPYREAN'),
        'Personal Brand': os.getenv('NOTION_YOUR_LIST_BRAND'),
    }

    headers = {
        'Authorization': f'Bearer {token}',
        'Notion-Version': '2022-06-28',
        'Content-Type': 'application/json',
    }

    overdue = []
    due_today = []
    due_tomorrow = []

    for venture, db_id in dbs.items():
        if not db_id:
            continue
        try:
            resp = _req.post(
                f'https://api.notion.com/v1/databases/{db_id}/query',
                headers=headers,
                json={'filter': {'and': [
                    {'property': 'Status', 'select': {'does_not_equal': 'Done'}},
                    {'property': 'Due Date', 'date': {'is_not_empty': True}},
                ]}},
                timeout=10,
            )
            if resp.status_code != 200:
                print(f'[Deadlines] {venture} API error: {resp.status_code}')
                continue
            for r in resp.json().get('results', []):
                props = r.get('properties', {})
                name = props.get('Name', {}).get('title', [{}])[0].get('plain_text', '')
                due = props.get('Due Date', {}).get('date', {}).get('start', '')
                if not due or not name:
                    continue
                try:
                    due_dt = datetime.fromisoformat(due)
                    if due_dt.tzinfo is None:
                        due_dt = due_dt.replace(tzinfo=PDT)
                    else:
                        due_dt = due_dt.astimezone(PDT)
                    item = {'name': name, 'due': due[:10], 'venture': venture}
                    if due_dt.date() < now.date():
                        overdue.append(item)
                    elif due_dt.date() == now.date():
                        due_today.append(item)
                    elif due_dt.date() == tomorrow.date():
                        due_tomorrow.append(item)
                except Exception:
                    continue
        except Exception as e:
            print(f'[Deadlines] {venture} failed: {e}')

    if not overdue and not due_today and not due_tomorrow:
        print('[Deadlines] Nothing due — skipping Discord alert')
        return

    intents = discord.Intents.default()
    client = discord.Client(intents=intents)

    @client.event
    async def on_ready():
        channel = client.get_channel(GENERAL_CHANNEL_ID)
        if not channel:
            await client.close()
            return

        lines = ['⏰ **Deadline Alert:**']
        if overdue:
            lines.append(f'\n🔴 **Overdue ({len(overdue)}):**')
            for t in overdue[:5]:
                lines.append(f'• {t["name"]} — due {t["due"]} [{t["venture"]}]')
        if due_today:
            lines.append(f'\n🟡 **Due today ({len(due_today)}):**')
            for t in due_today[:5]:
                lines.append(f'• {t["name"]} [{t["venture"]}]')
        if due_tomorrow:
            lines.append(f'\n🔵 **Due tomorrow ({len(due_tomorrow)}):**')
            for t in due_tomorrow[:3]:
                lines.append(f'• {t["name"]} [{t["venture"]}]')

        await channel.send('\n'.join(lines))
        await client.close()

    await client.start(os.getenv('DISCORD_BOT_TOKEN'))


async def check_stale_tasks():
    """Flag tasks open for 5+ days with no progress."""
    from runtime.context import load_context_from_env
    from runtime.db import get_conn

    ctx = load_context_from_env()
    with get_conn(ctx.org_id) as cur:
        cur.execute('''
            SELECT payload_json, created_at FROM events
            WHERE org_id = %s
            AND event_type = 'dex_task'
            AND (payload_json->>\'status\' IS NULL
                 OR payload_json->>\'status\' = \'pending\')
            AND created_at < NOW() - INTERVAL \'5 days\'
            ORDER BY created_at ASC
            LIMIT 10
        ''', (str(ctx.org_id),))
        rows = cur.fetchall()

    if not rows:
        print('[Deadlines] No stale tasks')
        return

    stale = []
    for r in rows:
        payload = r['payload_json']
        if isinstance(payload, str):
            payload = json.loads(payload)
        task = payload.get('task', '')
        if task:
            age = (datetime.now(PDT) - r['created_at'].astimezone(PDT)).days
            stale.append({'task': task, 'age_days': age})

    if not stale:
        return

    intents = discord.Intents.default()
    client = discord.Client(intents=intents)

    @client.event
    async def on_ready():
        channel = client.get_channel(GENERAL_CHANNEL_ID)
        if not channel:
            await client.close()
            return
        lines = [f'🚧 **Stale tasks ({len(stale)}) — no progress in 5+ days:**']
        for t in stale[:5]:
            lines.append(f'• {t["task"][:70]} ({t["age_days"]}d old)')
        lines.append('\nAre these still relevant? Reply to dismiss or delegate.')
        await channel.send('\n'.join(lines))
        await client.close()

    await client.start(os.getenv('DISCORD_BOT_TOKEN'))


if __name__ == '__main__':
    async def run_all():
        await check_deadlines()
        await check_stale_tasks()
    asyncio.run(run_all())
