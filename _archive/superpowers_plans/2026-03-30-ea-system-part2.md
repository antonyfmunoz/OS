# EA System Part 2 — Deadline Tracking, Delegation, Agenda, Subscriptions, SLA, Stale Tasks, 3-3-3

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Wire seven EA system features into EOS: deadline alerts, delegation tracking, pre-meeting agenda emails, subscription/vendor management, email SLA checking, blocked-task escalation, and the 3-3-3 morning brief structure.

**Architecture:** All new state is stored in the existing `events` table in Neon — no schema changes needed. New standalone modules (`delegation_tracker.py`, `subscription_tracker.py`) are added to `eos_ai/`. New script `scripts/deadline_monitor.py` runs via cron. Four existing files are modified: `eos_ai/meetings.py`, `scripts/call_prep.py`, `eos_ai/daily_sync.py`, `eos_ai/email_gps.py`. Discord commands added to `13_Scripts/discord_bot.py`. EOD report patched in `scripts/eod_sync.py`. Gateway delegation hook added in `eos_ai/gateway.py`.

**Tech Stack:** Python 3.12, psycopg2 (via eos_ai.db), discord.py (py-cord 2.6.1), Notion API, Google Calendar via GWSConnector, existing model_router pattern.

---

## File Map

| Action | File | Responsibility |
|--------|------|----------------|
| Create | `scripts/deadline_monitor.py` | Cron: Notion due-date alerts + stale task alerts |
| Create | `eos_ai/delegation_tracker.py` | Log/query delegations from events table |
| Create | `eos_ai/subscription_tracker.py` | Subscription registry + renewal alerts |
| Modify | `eos_ai/meetings.py` | Add `draft_meeting_agenda()` |
| Modify | `scripts/call_prep.py` | Add 24h agenda-window check in `main()` |
| Modify | `eos_ai/daily_sync.py` | Add `SyncAgenda` fields + 3-3-3 + subscription alerts + SLA injection |
| Modify | `eos_ai/email_gps.py` | Add `sla_check()` method |
| Modify | `scripts/eod_sync.py` | Add overdue delegations section |
| Modify | `eos_ai/gateway.py` | Log delegation when routing to CEO agent |
| Modify | `13_Scripts/discord_bot.py` | Add `!delegated`, `!subscriptions`, `!add_sub` commands + update `!help` |

---

## Task 1: Create `scripts/deadline_monitor.py`

**Files:**
- Create: `scripts/deadline_monitor.py`

- [ ] **Step 1: Write the file**

```python
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

sys.path.insert(0, '/opt/OS')
load_dotenv('/opt/OS/eos_ai/.env')
load_dotenv('/opt/OS/13_Scripts/.env')

PDT = ZoneInfo('America/Los_Angeles')
GENERAL_CHANNEL_ID = 1486289444830056540


async def check_deadlines():
    from eos_ai.context import load_context_from_env
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
            for r in resp.json().get('results', []):
                props = r.get('properties', {})
                name = props.get('Name', {}).get('title', [{}])[0].get('plain_text', '')
                due = props.get('Due Date', {}).get('date', {}).get('start', '')
                if not due or not name:
                    continue
                try:
                    due_dt = datetime.fromisoformat(due).replace(tzinfo=PDT)
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
    from eos_ai.context import load_context_from_env
    from eos_ai.db import get_conn

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
        if channel:
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
```

- [ ] **Step 2: Verify import check**

```bash
python3 -c "
import sys; sys.path.insert(0, '/opt/OS')
from scripts.deadline_monitor import check_deadlines, check_stale_tasks
print('import ok')
"
```
Expected: `import ok`

- [ ] **Step 3: Add crontab entry**

```bash
(crontab -l 2>/dev/null; echo "10 6 * * * cd /opt/OS && python3 scripts/deadline_monitor.py >> /opt/OS/logs/deadlines.log 2>&1") | crontab -
crontab -l | grep deadline_monitor
```
Expected: line printed showing the cron entry.

- [ ] **Step 4: Commit**

```bash
git add scripts/deadline_monitor.py
git commit -m "feat: add deadline monitor — notion due dates + stale task alerts"
```

---

## Task 2: Create `eos_ai/delegation_tracker.py`

**Files:**
- Create: `eos_ai/delegation_tracker.py`

- [ ] **Step 1: Write the file**

```python
"""
Delegation Tracker — tracks tasks routed to CEO agents
or other parties. Follows up if not completed.
"""

import json
import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)
PDT = ZoneInfo('America/Los_Angeles')


def log_delegation(
    task: str,
    delegated_to: str,
    due_hours: int = 24,
    ctx=None,
) -> bool:
    """Log a delegated task for follow-up tracking."""
    try:
        from eos_ai.context import load_context_from_env
        from eos_ai.db import get_conn
        ctx = ctx or load_context_from_env()
        now = datetime.now(PDT)
        due_at = (now + timedelta(hours=due_hours)).isoformat()

        with get_conn(ctx.org_id) as cur:
            cur.execute('''
                INSERT INTO events
                (org_id, event_type, payload_json, handled_by)
                VALUES (%s, %s, %s, %s)
            ''', (
                str(ctx.org_id),
                'delegation',
                json.dumps({
                    'task': task,
                    'delegated_to': delegated_to,
                    'status': 'pending',
                    'delegated_at': now.isoformat(),
                    'due_at': due_at,
                }),
                'dex_delegation',
            ))
        return True
    except Exception as e:
        logger.warning(f'[Delegation] log_delegation failed: {e}')
        return False


def get_overdue_delegations(ctx=None) -> list[dict]:
    """Get delegated tasks that are overdue."""
    try:
        from eos_ai.context import load_context_from_env
        from eos_ai.db import get_conn
        ctx = ctx or load_context_from_env()

        with get_conn(ctx.org_id) as cur:
            cur.execute('''
                SELECT id, payload_json, created_at FROM events
                WHERE org_id = %s
                AND event_type = 'delegation'
                AND payload_json->>\'status\' = \'pending\'
                AND (payload_json->>\'due_at\')::timestamp < NOW()
                ORDER BY created_at ASC
                LIMIT 10
            ''', (str(ctx.org_id),))
            rows = cur.fetchall()

        results = []
        for r in rows:
            payload = r['payload_json']
            if isinstance(payload, str):
                payload = json.loads(payload)
            payload['event_id'] = str(r['id'])
            results.append(payload)
        return results
    except Exception as e:
        logger.warning(f'[Delegation] get_overdue_delegations failed: {e}')
        return []


def mark_delegation_complete(event_id: str, ctx=None) -> bool:
    """Mark a delegation as completed."""
    try:
        from eos_ai.context import load_context_from_env
        from eos_ai.db import get_conn
        ctx = ctx or load_context_from_env()

        with get_conn(ctx.org_id) as cur:
            cur.execute('''
                UPDATE events
                SET payload_json = payload_json || \'{"status": "completed"}\'::jsonb
                WHERE id = %s AND org_id = %s
            ''', (event_id, str(ctx.org_id)))
        return True
    except Exception as e:
        logger.warning(f'[Delegation] mark_complete failed: {e}')
        return False
```

- [ ] **Step 2: Verify import**

```bash
python3 -c "
import sys; sys.path.insert(0, '/opt/OS')
from eos_ai.delegation_tracker import log_delegation, get_overdue_delegations, mark_delegation_complete
print('import ok')
"
```
Expected: `import ok`

- [ ] **Step 3: Commit**

```bash
git add eos_ai/delegation_tracker.py
git commit -m "feat: add delegation tracker module"
```

---

## Task 3: Wire delegation into `gateway.py` and `eod_sync.py`

**Files:**
- Modify: `eos_ai/gateway.py` (line ~857 — after `agent_to_use` is resolved in `_route_agent_task`)
- Modify: `scripts/eod_sync.py` (line ~184 — after decisions section in `build_eod_message`)

- [ ] **Step 1: Read gateway.py lines 845–870 to confirm exact insertion point**

Read file at offset 845, limit 30. The insertion target is after `agent_to_use = self._route_to_agent(prompt)` (line ~857) and before `result = loop.run(...)`. The agent_to_use must already be resolved.

- [ ] **Step 2: Edit gateway.py — add delegation log after agent_to_use is finalized**

In `_route_agent_task`, after this block:
```python
            if not agent_to_use:
                agent_to_use = self._route_to_agent(prompt)
```

Add immediately after (before `result = loop.run(`):
```python
            # Log delegation if routing to a CEO agent
            _CEO_AGENTS = frozenset({'lyfe_ceo', 'empyrean_ceo', 'brand_ceo'})
            if agent_to_use in _CEO_AGENTS:
                try:
                    from eos_ai.delegation_tracker import log_delegation
                    log_delegation(
                        task=prompt[:200],
                        delegated_to=agent_to_use,
                        due_hours=24,
                    )
                except Exception:
                    pass
```

- [ ] **Step 3: Verify gateway.py import check**

```bash
python3 -c "
import sys; sys.path.insert(0, '/opt/OS')
from eos_ai.gateway import EOSGateway
print('import ok')
"
```
Expected: `import ok`

- [ ] **Step 4: Edit eod_sync.py — add overdue delegations after decisions section**

In `build_eod_message()`, after the `decisions` block (line ~184), add before the `body = '\n\n'.join(sections)` line:

```python
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
```

- [ ] **Step 5: Verify eod_sync.py import**

```bash
python3 -c "
import sys; sys.path.insert(0, '/opt/OS')
from scripts.eod_sync import build_eod_message
print('import ok')
"
```
Expected: `import ok`

- [ ] **Step 6: Add `!delegated` command to discord_bot.py**

Find the last `@bot.command` before `@bot.command(name='help')` (line ~2404). Add the new command before it:

```python
@bot.command(name='delegated')
async def cmd_delegated(ctx: commands.Context):
    """Show overdue delegations."""
    def _run():
        try:
            from eos_ai.delegation_tracker import get_overdue_delegations
            overdue = get_overdue_delegations()
            if not overdue:
                return '✅ No overdue delegations.'
            lines = [f'📋 **Overdue delegations ({len(overdue)}):**']
            for d in overdue[:8]:
                task = d.get('task', '')[:60]
                to = d.get('delegated_to', 'Unknown')
                due = d.get('due_at', '')[:10]
                lines.append(f'• {task} → {to} (due {due})')
            return '\n'.join(lines)
        except Exception as e:
            return f'❌ Error: {e}'
    loop = asyncio.get_event_loop()
    output = await loop.run_in_executor(None, _run)
    await ctx.reply(output)
```

- [ ] **Step 7: Update `!help` in discord_bot.py to add `!delegated`**

In the help command output (line ~2413 area), add `'`!delegated` — overdue delegations',` to the EA Commands section.

- [ ] **Step 8: Commit**

```bash
git add eos_ai/gateway.py scripts/eod_sync.py 13_Scripts/discord_bot.py
git commit -m "feat: wire delegation tracking into gateway, eod, discord"
```

---

## Task 4: Add `draft_meeting_agenda()` to `eos_ai/meetings.py`

**Files:**
- Modify: `eos_ai/meetings.py` (append after last function `build_prep_brief`)

- [ ] **Step 1: Append `draft_meeting_agenda` to the end of meetings.py**

Add after the closing of `build_prep_brief` (after line 545):

```python


def draft_meeting_agenda(
    title: str,
    person: str,
    email: str,
    meeting_type: str,
    venture: str,
    duration_minutes: int = 60,
    ctx=None,
) -> str:
    """
    Draft a meeting agenda to send to attendee 24h before.
    Returns formatted agenda as string.
    """
    try:
        from eos_ai.context import load_context_from_env
        from eos_ai.model_router import get_router, TaskType
        from eos_ai.person_recognition import build_intelligence_profile
        ctx = ctx or load_context_from_env()
        router = get_router()
        model = router.route(TaskType.FAST_RESPONSE)

        profile = build_intelligence_profile(
            name=person, email=email, ctx=ctx
        )

        prompt = f"""Draft a pre-meeting agenda email.

Meeting: {title}
With: {person}
Type: {meeting_type}
Duration: {duration_minutes} minutes
Venture: {venture}
Their context: {profile.notes or 'New contact'}

Format:
Subject: [subject — specific, not generic]

Hi {person},

[2-3 sentence opener — warm, direct]

For our call:
- [agenda item 1 — specific to their situation]
- [agenda item 2]
- [agenda item 3 if needed]

[one sentence on what they should bring/prepare if relevant]

Looking forward to it.
[Antony/DEX]

Keep it under 150 words. No corporate speak."""

        return router.call(model, prompt).strip()
    except Exception as e:
        logger.warning(f'[Meetings] draft_meeting_agenda failed: {e}')
        return ''
```

- [ ] **Step 2: Verify import**

```bash
python3 -c "
import sys; sys.path.insert(0, '/opt/OS')
from eos_ai.meetings import draft_meeting_agenda
print('import ok')
"
```
Expected: `import ok`

- [ ] **Step 3: Commit**

```bash
git add eos_ai/meetings.py
git commit -m "feat: add draft_meeting_agenda to meetings module"
```

---

## Task 5: Add 24h agenda window to `scripts/call_prep.py`

**Files:**
- Modify: `scripts/call_prep.py` (inside `main()`, after `mark_prepped(event_id)`)

- [ ] **Step 1: Read call_prep.py lines 148–179 to confirm exact insertion point**

The main loop ends after `mark_prepped(event_id)`. The 24h agenda check is a completely separate loop — it should run after the 30-min prep loop. Add it to `main()` after `for event in upcoming:` loop closes.

- [ ] **Step 2: Edit call_prep.py — add agenda window check in `main()`**

After the `for event in upcoming:` loop (line ~175), before the function ends, add:

```python
    # 24h agenda window — draft agenda for tomorrow's meetings
    try:
        import json as _json
        from datetime import timezone
        from dateutil.parser import parse as _parse
        from eos_ai.gws_connector import GWSConnector
        from eos_ai.context import load_context_from_env

        _ctx = load_context_from_env()
        _gws = GWSConnector(_ctx)
        _all_events = _gws.get_upcoming_events(days=2)

        _agenda_state_file = '/tmp/agenda_sent_state.json'
        try:
            with open(_agenda_state_file) as _f:
                _agenda_state = _json.load(_f)
        except Exception:
            _agenda_state = {}

        _now_utc = datetime.now(timezone.utc)
        _agenda_window_start = _now_utc + timedelta(hours=23)
        _agenda_window_end = _now_utc + timedelta(hours=25)

        for _event in (_all_events or []):
            _event_id = _event.get('id', '') or (
                _event.get('title', '') + '_' + str(_event.get('start', ''))[:16]
            )
            if not _event_id or _event_id in _agenda_state:
                continue

            _start_str = _event.get('start', '')
            if not _start_str or 'T' not in str(_start_str):
                continue

            try:
                _event_start = _parse(str(_start_str))
                if _event_start.tzinfo is None:
                    _event_start = _event_start.replace(tzinfo=timezone.utc)

                if not (_agenda_window_start <= _event_start <= _agenda_window_end):
                    continue

                _attendees = _event.get('attendees', [])
                _attendee_email = next(
                    (a.get('email') for a in _attendees if not a.get('self')),
                    '',
                )
                if not _attendee_email:
                    continue

                from eos_ai.meetings import draft_meeting_agenda
                from eos_ai.db import get_conn

                _agenda = draft_meeting_agenda(
                    title=_event.get('title', _event.get('summary', 'Our call')),
                    person=_attendee_email.split('@')[0],
                    email=_attendee_email,
                    meeting_type='Meeting',
                    venture='',
                    ctx=_ctx,
                )

                if _agenda:
                    with get_conn(_ctx.org_id) as _cur:
                        _cur.execute('''
                            INSERT INTO events
                            (org_id, event_type, payload_json, handled_by)
                            VALUES (%s, %s, %s, %s)
                        ''', (
                            str(_ctx.org_id),
                            'email_draft_pending',
                            _json.dumps({
                                'draft': _agenda,
                                'to_email': _attendee_email,
                                'type': 'meeting_agenda',
                                'event_id': _event_id,
                                'status': 'pending_approval',
                            }),
                            'call_prep',
                        ))

                    _webhook = os.getenv('DISCORD_BRIEF_WEBHOOK')
                    if _webhook:
                        import requests as _req
                        _msg = (
                            f'📋 **Agenda drafted for tomorrow:**\n'
                            f'{_event.get("title", "Meeting")} with {_attendee_email}\n'
                            f'```\n{_agenda[:600]}\n```\n'
                            f'`!approve_followup` to send.'
                        )
                        _req.post(_webhook, json={'content': _msg}, timeout=5)

                    _agenda_state[_event_id] = _now_utc.isoformat()
                    print(f'[CallPrep] Agenda drafted for: {_event.get("title")}')

            except Exception as _e:
                print(f'[CallPrep] Agenda for {_event_id} failed: {_e}')

        with open(_agenda_state_file, 'w') as _f:
            _json.dump(_agenda_state, _f)

    except Exception as _e:
        print(f'[CallPrep] Agenda window check failed: {_e}')
```

- [ ] **Step 3: Verify import**

```bash
python3 -c "
import sys; sys.path.insert(0, '/opt/OS')
from scripts.call_prep import main
print('import ok')
"
```
Expected: `import ok`

- [ ] **Step 4: Commit**

```bash
git add scripts/call_prep.py
git commit -m "feat: add 24h agenda drafting window to call_prep"
```

---

## Task 6: Create `eos_ai/subscription_tracker.py`

**Files:**
- Create: `eos_ai/subscription_tracker.py`

- [ ] **Step 1: Write the file**

```python
"""
Subscription Tracker — maintains a registry of active
subscriptions, renewal dates, and costs.
Alerts on upcoming renewals and flags unused tools.
"""

import json
import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)
PDT = ZoneInfo('America/Los_Angeles')


def get_subscriptions(ctx=None) -> list[dict]:
    """Get all tracked subscriptions from Neon (most recent per vendor)."""
    try:
        from eos_ai.context import load_context_from_env
        from eos_ai.db import get_conn
        ctx = ctx or load_context_from_env()

        with get_conn(ctx.org_id) as cur:
            cur.execute('''
                SELECT payload_json, created_at FROM events
                WHERE org_id = %s
                AND event_type = 'subscription'
                ORDER BY created_at DESC
            ''', (str(ctx.org_id),))
            rows = cur.fetchall()

        subs = []
        seen_vendors: set[str] = set()
        for r in rows:
            payload = r['payload_json']
            if isinstance(payload, str):
                payload = json.loads(payload)
            vendor = payload.get('vendor', '')
            if vendor not in seen_vendors:
                seen_vendors.add(vendor)
                subs.append(payload)
        return subs
    except Exception as e:
        logger.warning(f'[SubTracker] get_subscriptions failed: {e}')
        return []


def add_subscription(
    vendor: str,
    amount: float,
    billing_cycle: str,
    next_renewal: str,
    category: str = 'Software/SaaS',
    notes: str = '',
    ctx=None,
) -> bool:
    """Add or update a subscription record."""
    try:
        from eos_ai.context import load_context_from_env
        from eos_ai.db import get_conn
        ctx = ctx or load_context_from_env()

        with get_conn(ctx.org_id) as cur:
            cur.execute('''
                INSERT INTO events
                (org_id, event_type, payload_json, handled_by)
                VALUES (%s, %s, %s, %s)
            ''', (
                str(ctx.org_id),
                'subscription',
                json.dumps({
                    'vendor': vendor,
                    'amount': amount,
                    'billing_cycle': billing_cycle,
                    'next_renewal': next_renewal,
                    'category': category,
                    'notes': notes,
                    'added_at': datetime.now(PDT).isoformat(),
                }),
                'dex_subscriptions',
            ))
        return True
    except Exception as e:
        logger.warning(f'[SubTracker] add_subscription failed: {e}')
        return False


def get_upcoming_renewals(days: int = 14, ctx=None) -> list[dict]:
    """Get subscriptions renewing in the next N days."""
    subs = get_subscriptions(ctx)
    now = datetime.now(PDT)
    cutoff = now + timedelta(days=days)
    upcoming = []
    for s in subs:
        renewal = s.get('next_renewal', '')
        if not renewal:
            continue
        try:
            renewal_dt = datetime.fromisoformat(renewal).replace(tzinfo=PDT)
            if now <= renewal_dt <= cutoff:
                s = dict(s)
                s['days_until'] = (renewal_dt.date() - now.date()).days
                upcoming.append(s)
        except Exception:
            continue
    return sorted(upcoming, key=lambda x: x.get('days_until', 99))


def get_monthly_subscription_total(ctx=None) -> float:
    """Calculate total monthly subscription cost."""
    subs = get_subscriptions(ctx)
    total = 0.0
    for s in subs:
        amount = float(s.get('amount', 0))
        cycle = s.get('billing_cycle', 'monthly').lower()
        if cycle == 'annual':
            total += amount / 12
        elif cycle == 'monthly':
            total += amount
        elif cycle == 'weekly':
            total += amount * 4.33
    return total
```

- [ ] **Step 2: Verify import**

```bash
python3 -c "
import sys; sys.path.insert(0, '/opt/OS')
from eos_ai.subscription_tracker import (
    get_subscriptions, add_subscription,
    get_upcoming_renewals, get_monthly_subscription_total,
)
print('import ok')
"
```
Expected: `import ok`

- [ ] **Step 3: Commit**

```bash
git add eos_ai/subscription_tracker.py
git commit -m "feat: add subscription tracker module"
```

---

## Task 7: Add subscription commands to `discord_bot.py`

**Files:**
- Modify: `13_Scripts/discord_bot.py` (add two commands before `cmd_help`)

- [ ] **Step 1: Read discord_bot.py lines 2400–2410 to find exact insertion point**

Insert the two new commands before `@bot.command(name='help')` at line ~2404.

- [ ] **Step 2: Add `!subscriptions` command before `cmd_help`**

```python
@bot.command(name='subscriptions')
async def cmd_subscriptions(ctx: commands.Context):
    """Show subscription registry and upcoming renewals."""
    def _run():
        try:
            from eos_ai.subscription_tracker import (
                get_subscriptions,
                get_upcoming_renewals,
                get_monthly_subscription_total,
            )
            subs = get_subscriptions()
            renewals = get_upcoming_renewals(days=14)
            monthly = get_monthly_subscription_total()

            if not subs:
                return (
                    '📋 No subscriptions tracked yet.\n'
                    'Add one: `!add_sub [vendor] [amount] [monthly/annual] [YYYY-MM-DD]`'
                )

            lines = [f'📋 **Subscriptions — ${monthly:,.2f}/month**']
            for s in subs[:10]:
                lines.append(
                    f'• {s["vendor"]} — ${s["amount"]} '
                    f'({s.get("billing_cycle","monthly")}) — '
                    f'renews {s.get("next_renewal","?")[:10]}'
                )
            if renewals:
                lines.append(f'\n⚠️ **Renewing soon:**')
                for r in renewals[:3]:
                    lines.append(
                        f'• {r["vendor"]} in {r["days_until"]}d — ${r["amount"]}'
                    )
            return '\n'.join(lines)
        except Exception as e:
            return f'❌ Error: {e}'
    loop = asyncio.get_event_loop()
    output = await loop.run_in_executor(None, _run)
    await ctx.reply(output)


@bot.command(name='add_sub')
async def cmd_add_sub(ctx: commands.Context, *, args: str = ''):
    """Add a subscription. Usage: !add_sub [vendor] [amount] [monthly/annual] [YYYY-MM-DD]"""
    parts = args.strip().split()
    if len(parts) < 4:
        await ctx.reply('Usage: `!add_sub [vendor] [amount] [monthly/annual] [YYYY-MM-DD]`')
        return

    def _run():
        try:
            from eos_ai.subscription_tracker import add_subscription
            vendor = parts[0]
            amount = float(parts[1])
            cycle = parts[2]
            renewal = parts[3]
            ok = add_subscription(
                vendor=vendor,
                amount=amount,
                billing_cycle=cycle,
                next_renewal=renewal,
            )
            if ok:
                return f'✅ Added: {vendor} — ${amount}/{cycle} — renews {renewal}'
            return '❌ Failed to add subscription.'
        except Exception as e:
            return f'❌ Error: {e}'
    loop = asyncio.get_event_loop()
    output = await loop.run_in_executor(None, _run)
    await ctx.reply(output)
```

- [ ] **Step 3: Update `!help` to list new commands**

In `cmd_help`, add to the EA Commands section:
```
'`!subscriptions` — subscription registry + upcoming renewals',
'`!add_sub [vendor] [amount] [cycle] [date]` — track a subscription',
```

- [ ] **Step 4: Verify discord_bot.py imports**

```bash
python3 -c "
import sys; sys.path.insert(0, '/opt/OS')
import ast
with open('13_Scripts/discord_bot.py') as f:
    ast.parse(f.read())
print('syntax ok')
"
```
Expected: `syntax ok`

- [ ] **Step 5: Commit**

```bash
git add 13_Scripts/discord_bot.py
git commit -m "feat: add !subscriptions and !add_sub discord commands"
```

---

## Task 8: Add subscription renewal alerts to `daily_sync.py`

**Files:**
- Modify: `eos_ai/daily_sync.py`

- [ ] **Step 1: Add `subscription_alerts` field to `SyncAgenda` dataclass**

In `SyncAgenda` (line ~24), after `goal_alignment: str = ''`, add:
```python
    subscription_alerts: list = field(default_factory=list)  # renewal warnings
```

- [ ] **Step 2: Add subscription renewal check in `build_agenda()`**

In `build_agenda()`, after the Section 7 questions block (after line ~351, before `return agenda`), add:

```python
        # Subscription renewal alerts (Section 8 — injected into format)
        try:
            from eos_ai.subscription_tracker import get_upcoming_renewals
            renewals = get_upcoming_renewals(days=7)
            if renewals:
                agenda.subscription_alerts = [
                    f'• {r["vendor"]} renews in {r["days_until"]}d — ${r["amount"]}'
                    for r in renewals
                ]
        except Exception:
            pass
```

- [ ] **Step 3: Add subscription alerts block in `format_sync_message()`**

In `format_sync_message()`, in the Closing section — after Section 7 questions block but before the closing `━━━` lines, add:

```python
        # Subscription renewal alerts
        if agenda.subscription_alerts:
            lines.append('**💳 Renewals this week:**')
            for alert in agenda.subscription_alerts:
                lines.append(f'  {alert}')
            lines.append('')
```

- [ ] **Step 4: Verify import**

```bash
python3 -c "
import sys; sys.path.insert(0, '/opt/OS')
from eos_ai.daily_sync import DailySync, SyncAgenda
a = SyncAgenda(date='test')
print('subscription_alerts' in a.__dict__, 'import ok')
"
```
Expected: `True import ok`

- [ ] **Step 5: Commit**

```bash
git add eos_ai/daily_sync.py
git commit -m "feat: add subscription renewal alerts to daily sync"
```

---

## Task 9: Add `sla_check()` to `eos_ai/email_gps.py`

**Files:**
- Modify: `eos_ai/email_gps.py` (add method to `EmailGPS` class, after `get_emails_for_review`)

- [ ] **Step 1: Find exact insertion line**

```bash
grep -n "def get_emails_for_review\|def get_drafts_pending" /opt/OS/eos_ai/email_gps.py
```
Add `sla_check` between `get_emails_for_review` and `get_drafts_pending`.

- [ ] **Step 2: Add `sla_check` method to `EmailGPS` after `get_emails_for_review`**

After the closing of `get_emails_for_review` (line ~1081), before `def get_drafts_pending`, add:

```python
    def sla_check(self) -> list[dict]:
        """
        Check TO_RESPOND emails older than 24h with no draft.
        Returns list of SLA breaches sorted oldest first.
        """
        try:
            from email.utils import parsedate_to_datetime
            from datetime import datetime, timedelta, timezone

            emails = self.get_emails_to_respond(limit=20)
            now = datetime.now(timezone.utc)
            breaches = []

            for e in emails:
                date_str = e.get('date', '')
                if not date_str:
                    continue
                try:
                    email_dt = parsedate_to_datetime(date_str)
                    age = now - email_dt.astimezone(timezone.utc)
                    if age.total_seconds() > 24 * 3600:
                        e['age_hours'] = int(age.total_seconds() / 3600)
                        breaches.append(e)
                except Exception:
                    continue

            return sorted(breaches, key=lambda x: x.get('age_hours', 0), reverse=True)
        except Exception as e:
            logger.warning(f'[EmailGPS] sla_check failed: {e}')
            return []

```

- [ ] **Step 3: Verify import**

```bash
python3 -c "
import sys; sys.path.insert(0, '/opt/OS')
from eos_ai.email_gps import EmailGPS
from eos_ai.context import load_context_from_env
ctx = load_context_from_env()
gps = EmailGPS(ctx)
print(hasattr(gps, 'sla_check'), 'import ok')
"
```
Expected: `True import ok`

- [ ] **Step 4: Commit**

```bash
git add eos_ai/email_gps.py
git commit -m "feat: add sla_check to EmailGPS"
```

---

## Task 10: Wire SLA check into `daily_sync.py` Section 6

**Files:**
- Modify: `eos_ai/daily_sync.py` (Section 6 emails block, lines ~296–326)

- [ ] **Step 1: Read daily_sync.py lines 296–330 to confirm the emails section**

The emails section ends around line 326. Add SLA injection after `agenda.emails` is built and before the `except` closes.

- [ ] **Step 2: Add SLA breach injection to Section 6**

In the Section 6 block, after `if not agenda.emails: agenda.emails = ['Inbox clear.']` (line ~324), before `except Exception as e:`, add:

```python
            # SLA check — flag TO_RESPOND emails over 24h
            try:
                sla_breaches = gps.sla_check()
                if sla_breaches:
                    agenda.emails.insert(0,
                        f'⚠️ **SLA breach — {len(sla_breaches)} emails over 24h:**'
                    )
                    for _b in sla_breaches[:3]:
                        agenda.emails.insert(1,
                            f'  🔴 {_b.get("from","")[:30]} — '
                            f'{_b.get("subject","")[:40]} ({_b.get("age_hours","?")}h old)'
                        )
            except Exception:
                pass
```

- [ ] **Step 3: Verify daily_sync still imports cleanly**

```bash
python3 -c "
import sys; sys.path.insert(0, '/opt/OS')
from eos_ai.daily_sync import DailySync
print('import ok')
"
```
Expected: `import ok`

- [ ] **Step 4: Commit**

```bash
git add eos_ai/daily_sync.py
git commit -m "feat: inject SLA breach warnings into daily sync email section"
```

---

## Task 11: Add 3-3-3 structure to `daily_sync.py`

**Files:**
- Modify: `eos_ai/daily_sync.py`

- [ ] **Step 1: Add three fields to `SyncAgenda` dataclass**

After `subscription_alerts: list = field(default_factory=list)`, add:
```python
    first_3: list = field(default_factory=list)   # DEX handles in first hour
    last_3: list = field(default_factory=list)    # Antony must complete today
    recurring_3: list = field(default_factory=list)  # DEX owns daily
```

- [ ] **Step 2: Add 3-3-3 generation in `build_agenda()` after action items are prioritized**

After the goal_alignment block (after line ~250, before Section 5), add:

```python
        # ── 3-3-3 Framework (Dan Martell) ────────────────────────────────
        try:
            from eos_ai.model_router import get_router, TaskType
            import json as _pjson333
            _router333 = get_router()
            _model333 = _router333.route(TaskType.FAST_RESPONSE)

            _emails_ctx = '\n'.join(agenda.emails[:5]) if agenda.emails else 'None'
            _tasks_ctx = '\n'.join(agenda.action_items[:5]) if agenda.action_items else 'None'
            _cal_ctx = '\n'.join(agenda.calendar_review[:3]) if agenda.calendar_review else 'None'

            _333_prompt = f"""You are DEX, EA to Antony Munoz.
Apply Dan Martell's 3-3-3 EA framework to today.

Emails to handle: {_emails_ctx}
Tasks pending: {_tasks_ctx}
Calendar today: {_cal_ctx}
Binding constraint: focus on first sale

Return JSON only:
{{
  "first_3": [
    "Thing DEX handles in first hour so Antony doesn't have to",
    "Thing 2",
    "Thing 3"
  ],
  "last_3": [
    "Most important thing Antony must personally complete today",
    "Thing 2",
    "Thing 3"
  ],
  "recurring_3": [
    "Task DEX owns completely every day",
    "Task 2",
    "Task 3"
  ]
}}"""

            _333_result = _router333.call(_model333, _333_prompt).strip()
            if '```' in _333_result:
                _333_result = _333_result.split('```')[1].replace('json', '').strip()
            _333_data = _pjson333.loads(_333_result)
            agenda.first_3 = _333_data.get('first_3', [])
            agenda.last_3 = _333_data.get('last_3', [])
            agenda.recurring_3 = _333_data.get('recurring_3', [])
        except Exception as _e333:
            print(f'[DailySync] 3-3-3 generation failed: {_e333}')
```

- [ ] **Step 3: Add 3-3-3 block in `format_sync_message()` after Section 4**

In `format_sync_message()`, after the Section 4 Action Items block (after the `lines.append('')` that closes Section 4, line ~413), add:

```python
        # 3-3-3 block
        if agenda.first_3 or agenda.last_3:
            lines.append('**⚡ 3-3-3 Today:**')
            if agenda.first_3:
                lines.append('_DEX handles (first hour):_')
                for item in agenda.first_3:
                    lines.append(f'  • {item}')
            if agenda.last_3:
                lines.append('_You must complete:_')
                for item in agenda.last_3:
                    lines.append(f'  • {item}')
            if agenda.recurring_3:
                lines.append('_DEX owns daily:_')
                for item in agenda.recurring_3:
                    lines.append(f'  • {item}')
            lines.append('')
```

- [ ] **Step 4: Verify full daily_sync import**

```bash
python3 -c "
import sys; sys.path.insert(0, '/opt/OS')
from eos_ai.daily_sync import DailySync, SyncAgenda
a = SyncAgenda(date='test')
for field in ['first_3', 'last_3', 'recurring_3', 'subscription_alerts']:
    assert field in a.__dict__, f'Missing: {field}'
print('all fields present, import ok')
"
```
Expected: `all fields present, import ok`

- [ ] **Step 5: Commit**

```bash
git add eos_ai/daily_sync.py
git commit -m "feat: add 3-3-3 framework to daily sync morning brief"
```

---

## Task 12: Final verification and deploy

- [ ] **Step 1: Full import sweep**

```bash
python3 -c "
import sys; sys.path.insert(0, '/opt/OS')
from eos_ai.delegation_tracker import get_overdue_delegations
from eos_ai.subscription_tracker import get_subscriptions, get_monthly_subscription_total
from eos_ai.meetings import draft_meeting_agenda
from eos_ai.email_gps import EmailGPS
from eos_ai.daily_sync import DailySync, SyncAgenda
from eos_ai.gateway import EOSGateway
from scripts.eod_sync import build_eod_message
from scripts.deadline_monitor import check_deadlines, check_stale_tasks
from scripts.call_prep import main
print('all imports clean')
"
```
Expected: `all imports clean`

- [ ] **Step 2: Run daily sync dry run**

```bash
python3 -c "
import sys; sys.path.insert(0, '/opt/OS')
from eos_ai.context import load_context_from_env
from eos_ai.daily_sync import DailySync
ctx = load_context_from_env()
ds = DailySync(ctx)
print(ds.run_sync())
" 2>&1 | head -60
```
Expected: Discord message with all sections including 3-3-3 block.

- [ ] **Step 3: Restart services**

```bash
docker compose restart os-discord os-webhook
sleep 15
docker logs os-discord --tail 10
docker logs os-webhook --tail 10
```
Expected: `online` or `started` in logs, no `Traceback`.

- [ ] **Step 4: Final commit**

```bash
git add -u
git commit -m "feat: ea system part 2 complete — deadline, delegation, agenda, subscriptions, sla, stale, 3-3-3"
```
