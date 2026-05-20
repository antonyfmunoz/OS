"""
Weekly business review — Sunday 7pm PDT.
Portfolio health, open items, DEX synthesis.
Posts to #general.
"""

import os
import sys
import asyncio
import discord
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from dotenv import load_dotenv

sys.path.insert(0, os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS")
load_dotenv(os.path.join(os.environ.get('UMH_ROOT') or os.environ.get('OS_ROOT') or os.environ.get('EOS_ROOT') or '/opt/OS', 'runtime', '.env'))
load_dotenv(os.path.join(os.environ.get('UMH_ROOT') or os.environ.get('OS_ROOT') or os.environ.get('EOS_ROOT') or '/opt/OS', 'services', '.env'))

PDT = ZoneInfo('America/Los_Angeles')
GENERAL_CHANNEL_ID = 1486289444830056540


async def run_weekly_review():
    from state.context.context import load_context_from_env
    from state.storage.db import get_conn
    from control_plane.strategy.portfolio_advisor import PortfolioAdvisor as PortfolioAgent
    from execution.runtime.model_router import get_router, TaskType
    import json as _json

    ctx = load_context_from_env()
    now = datetime.now(PDT)

    sections = []
    sections.append(
        f'## Weekly Review — Week of {(now - timedelta(days=7)).strftime("%B %d")}'
    )
    sections.append('')

    # 1. What got done this week
    try:
        with get_conn(ctx.org_id) as cur:
            cur.execute('''
                SELECT event_type, payload_json, created_at
                FROM events
                WHERE org_id = %s
                AND created_at >= NOW() - INTERVAL '7 days'
                AND event_type IN (
                    'meeting_scheduled', 'pipeline_entry',
                    'dex_task', 'decision'
                )
                ORDER BY created_at DESC
                LIMIT 30
            ''', (str(ctx.org_id),))
            rows = cur.fetchall()

        completed = []
        for r in rows:
            payload = r['payload_json']
            if isinstance(payload, str):
                payload = _json.loads(payload)
            et = r['event_type']
            if et == 'meeting_scheduled':
                completed.append(f'📅 Met with {payload.get("person", "someone")}')
            elif et == 'pipeline_entry':
                completed.append(f'📊 Pipeline: {payload.get("name", "lead")}')
            elif et == 'dex_task':
                completed.append(f'✅ {payload.get("task", "task")[:60]}')
            elif et == 'decision':
                completed.append(f'🎯 {payload.get("description", "decision")[:60]}')

        sections.append('**This week:**')
        if completed:
            for item in completed[:10]:
                sections.append(f'• {item}')
        else:
            sections.append('• Nothing logged this week.')
        sections.append('')
    except Exception as e:
        sections.append(f'**This week:** unavailable ({e})\n')

    # 2. Open action items carrying forward
    try:
        with get_conn(ctx.org_id) as cur:
            cur.execute("""
                SELECT payload_json FROM events
                WHERE org_id = %s
                AND event_type = 'dex_task'
                AND (payload_json->>'status' IS NULL
                     OR payload_json->>'status' != 'completed')
                AND created_at >= NOW() - INTERVAL '14 days'
                ORDER BY created_at ASC
                LIMIT 10
            """, (str(ctx.org_id),))
            open_rows = cur.fetchall()

        sections.append('**Carrying forward:**')
        if open_rows:
            for r in open_rows[:5]:
                payload = r['payload_json']
                if isinstance(payload, str):
                    payload = _json.loads(payload)
                task = payload.get('task', '')
                if task:
                    sections.append(f'• {task[:80]}')
        else:
            sections.append('• No open items.')
        sections.append('')
    except Exception as e:
        sections.append('**Carrying forward:** unavailable\n')

    # 3. Portfolio health snapshot
    try:
        pa = PortfolioAgent(ctx)
        ventures = pa.scan_all_ventures()
        binding = pa.identify_binding_constraint(ventures)
        sections.append('**Portfolio health:**')
        for v in ventures:
            bar = '█' * int(v.health_score * 10) + '░' * (10 - int(v.health_score * 10))
            sections.append(f'• {v.name}: [{bar}] {v.health_score:.0%}')
        if binding:
            sections.append(
                f'\n🎯 Binding constraint: **{binding.name}** — {binding.binding_constraint}'
            )
        sections.append('')
    except Exception as e:
        sections.append(f'**Portfolio:** unavailable\n')

    # Meeting ROI
    try:
        from adapters.calendar.meetings import calculate_meeting_roi
        _wr_roi = calculate_meeting_roi(days=7)
        if _wr_roi and _wr_roi.get('total', 0) > 0:
            sections.append('**📊 Meeting ROI this week:**')
            sections.append(
                f'• {_wr_roi["total"]} meetings | '
                f'{_wr_roi["completed"]} completed | '
                f'{_wr_roi["no_show"]} no-shows'
            )
            if _wr_roi['top_converting_type']:
                sections.append(
                    f'• Best type: {_wr_roi["top_converting_type"]}'
                )
            sections.append('')
    except Exception:
        pass

    # Energy trend
    try:
        import json as _etjson
        from state.storage.db import get_conn as _et_conn
        with _et_conn(ctx.org_id) as cur:
            cur.execute('''
                SELECT payload_json FROM events
                WHERE org_id = %s
                AND event_type = 'energy_checkin'
                AND created_at >= NOW() - INTERVAL '7 days'
                ORDER BY created_at DESC
            ''', (str(ctx.org_id),))
            _et_rows = cur.fetchall()
        if _et_rows:
            _et_scores = []
            _et_drains = []
            for _et_r in _et_rows:
                _et_p = _et_r['payload_json']
                if isinstance(_et_p, str):
                    _et_p = _etjson.loads(_et_p)
                _et_scores.append(_et_p.get('score', 5))
                _et_drain = _et_p.get('drained', '')
                if _et_drain:
                    _et_drains.append(_et_drain)
            _et_avg = sum(_et_scores) / len(_et_scores)
            _et_emoji = '🔴' if _et_avg <= 4 else '🟡' if _et_avg <= 6 else '🟢'
            sections.append('**⚡ Energy this week:**')
            sections.append(f'• Average: {_et_emoji} {_et_avg:.1f}/10')
            if _et_drains:
                from collections import Counter
                _et_top = Counter(_et_drains).most_common(1)[0][0]
                sections.append(f'• Biggest drain: {_et_top}')
            sections.append('')
    except Exception:
        pass

    # Pain Line — recurring delegate tasks
    try:
        from state.metrics.founder_rate import detect_delegation_threshold
        _pain = detect_delegation_threshold(ctx)
        if _pain:
            sections.append('**⚠️ Pain Line — recurring tasks to delegate:**')
            for _p in _pain[:3]:
                sections.append(
                    f'• "{_p["task"][:50]}" — {_p["occurrences"]}x this month'
                )
            sections.append('Use `!camcorder` to build a playbook for these.')
            sections.append('')
    except Exception:
        pass

    # 4. DEX synthesis
    try:
        router = get_router()
        model = router.route(TaskType.ANALYSIS)
        context_block = '\n'.join(sections)
        synthesis = router.call(model, f"""You are DEX, EA to Antony Munoz.
Based on this week's activity:

{context_block}

In 2-3 sentences, what's the one thing that needs to change next week to move the needle?
Be direct. No hedging. Focus on the binding constraint.""").strip()
        sections.append('**DEX assessment:**')
        sections.append(synthesis)
        sections.append('')
    except Exception:
        pass

    sections.append('**Next week starts tomorrow. What do you want to protect?**')
    sections.append('— DEX')

    full_message = '\n'.join(sections)

    intents = discord.Intents.default()
    client = discord.Client(intents=intents)

    @client.event
    async def on_ready():
        channel = client.get_channel(GENERAL_CHANNEL_ID)
        if channel:
            for i in range(0, len(full_message), 1900):
                await channel.send(full_message[i:i + 1900])
        await client.close()

    discord_token = os.getenv('DISCORD_BOT_TOKEN')
    if not discord_token:
        print('[WeeklyReview] DISCORD_BOT_TOKEN not set — exiting')
        return
    await client.start(discord_token)


if __name__ == '__main__':
    asyncio.run(run_weekly_review())
