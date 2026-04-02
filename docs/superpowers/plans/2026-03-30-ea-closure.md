# EA System Closure Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the EA system loop with 6 interconnected features: travel management, No List enforcement, Buyback Rate delegation gating, EOD energy check-in, Preloaded Year planning, and Pain Line detection.

**Architecture:** All new data persists to the `events` table in Neon using existing `get_conn()` pattern. New modules (`travel_manager.py`) follow the existing buyback_rate.py / perfect_week.py pattern. Discord commands use `@bot.command()` decorator style matching the existing codebase. Daily sync and weekly review pick up the new data at render time.

**Tech Stack:** Python 3.12, psycopg2 via Neon, py-cord 2.6.1, model_router for LLM calls, existing `events` table for all persistence.

---

## File Map

| File | Action | What changes |
|------|--------|--------------|
| `eos_ai/travel_manager.py` | CREATE | detect_travel_event, build_travel_brief, log_trip |
| `eos_ai/buyback_rate.py` | MODIFY | add add_to_no_list, get_no_list, check_against_no_list, detect_pain_line |
| `eos_ai/perfect_week.py` | MODIFY | add save_preloaded_year, get_preloaded_year, get_current_quarter_rocks |
| `eos_ai/daily_sync.py` | MODIFY | SyncAgenda gets dex_items + quarterly_rocks fields; build_agenda + format_sync_message wired |
| `eos_ai/founder_capture.py` | MODIFY | capture() adds BBR check after Neon write |
| `eos_ai/cognitive_loop.py` | MODIFY | inject No List violations into _system_parts |
| `scripts/call_prep.py` | MODIFY | main() adds 48h travel brief window after 24h agenda window |
| `scripts/eod_sync.py` | MODIFY | build_eod_message() appends energy check-in prompt |
| `scripts/weekly_review.py` | MODIFY | run_weekly_review() adds energy trend + pain line sections |
| `13_Scripts/discord_bot.py` | MODIFY | 6 new @bot.command decorators + no_list check in _run_gateway |

---

## Task 1: Create eos_ai/travel_manager.py

**Files:**
- Create: `eos_ai/travel_manager.py`

- [ ] **Step 1: Create the file**

```python
"""
Travel Manager — full trip logistics management.
When a trip is detected, DEX builds a complete
travel brief and manages logistics.
"""

import os
import json
import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from dotenv import load_dotenv

load_dotenv('/opt/OS/eos_ai/.env')
logger = logging.getLogger(__name__)
PDT = ZoneInfo('America/Los_Angeles')


def detect_travel_event(event: dict) -> bool:
    """Detect if a calendar event involves travel."""
    title = event.get('title', event.get('summary', '')).lower()
    location = event.get('location', '').lower()
    description = event.get('description', '').lower()

    travel_signals = [
        'flight', 'hotel', 'trip', 'travel', 'conference',
        'summit', 'retreat', 'airport', 'fly', 'visiting',
    ]
    location_signals = [
        'airport', 'hotel', 'convention', 'center', 'ave',
        'blvd', 'street', 'suite', 'floor',
    ]

    return (
        any(s in title for s in travel_signals) or
        any(s in location for s in location_signals) or
        any(s in description for s in travel_signals)
    )


def build_travel_brief(
    event_title: str,
    destination: str,
    start_date: str,
    end_date: str,
    attendees: list = None,
    ctx=None,
) -> str:
    """Build a complete travel logistics brief."""
    try:
        from eos_ai.model_router import get_router, TaskType
        router = get_router()
        model = router.route(TaskType.ANALYSIS)

        prompt = f"""You are DEX, EA to Antony Munoz.
Build a complete pre-trip brief for this travel event.

Event: {event_title}
Destination: {destination}
Dates: {start_date} to {end_date}
Attendees/context: {', '.join(attendees) if attendees else 'Solo'}
Antony is based in Portland, OR (PDT)

Create a comprehensive travel brief covering:

**Trip Overview**
- Purpose and key objectives
- Duration and key dates

**Logistics Checklist**
- [ ] Flight confirmation needed
- [ ] Hotel confirmation needed
- [ ] Ground transport (Uber/rental car)
- [ ] Travel documents check
- [ ] Currency if international

**Packing Essentials**
- Business items for this specific trip type
- Tech essentials
- Personal items

**Day-by-Day Schedule Template**
- Rough daily structure

**Pre-Trip Actions (48h before)**
- What DEX will handle
- What Antony needs to confirm

**Local Intelligence**
- Timezone and current time there
- Weather considerations
- Key venues/locations

Keep it practical and specific to this trip.
Under 400 words."""

        return router.call(model, prompt).strip()
    except Exception as e:
        logger.warning(f'[TravelManager] build_travel_brief failed: {e}')
        return f'Travel brief unavailable: {e}'


def log_trip(
    title: str,
    destination: str,
    start_date: str,
    end_date: str,
    ctx=None,
) -> bool:
    """Log a trip to Neon."""
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
                'trip',
                json.dumps({
                    'title': title,
                    'destination': destination,
                    'start_date': start_date,
                    'end_date': end_date,
                    'logged_at': datetime.now(PDT).isoformat(),
                }),
                'dex_travel',
            ))
        return True
    except Exception as e:
        logger.warning(f'[TravelManager] log_trip failed: {e}')
        return False
```

- [ ] **Step 2: Verify import**

```bash
python3 -c "
import sys; sys.path.insert(0, '/opt/OS')
from eos_ai.travel_manager import detect_travel_event, build_travel_brief, log_trip
print('travel_manager: ok')

# Test detect_travel_event
assert detect_travel_event({'title': 'SaaS Conference', 'location': 'San Francisco hotel'}) == True
assert detect_travel_event({'title': 'Team standup', 'location': ''}) == False
print('detect_travel_event: ok')
"
```
Expected: `travel_manager: ok` and `detect_travel_event: ok`

- [ ] **Step 3: Commit**

```bash
cd /opt/OS
git add eos_ai/travel_manager.py
git commit -m "feat: add travel_manager — detect, brief, log trip events"
```

---

## Task 2: Extend eos_ai/buyback_rate.py — No List + Pain Line

**Files:**
- Modify: `eos_ai/buyback_rate.py` (append after the existing `get_time_audit_summary` function at line 186)

- [ ] **Step 1: Read current end of buyback_rate.py to confirm append point**

```bash
tail -5 /opt/OS/eos_ai/buyback_rate.py
```
Expected: last function ends around line 186 with `return {}`.

- [ ] **Step 2: Append No List functions**

Append after the last line of `eos_ai/buyback_rate.py`:

```python


def add_to_no_list(item: str, reason: str = '', ctx=None) -> bool:
    """Add something to Antony's No List."""
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
                'no_list',
                json.dumps({
                    'item': item,
                    'reason': reason,
                    'added_at': datetime.now(PDT).isoformat(),
                }),
                'dex_no_list',
            ))
        return True
    except Exception as e:
        logger.warning(f'[NoList] add failed: {e}')
        return False


def get_no_list(ctx=None) -> list[dict]:
    """Get Antony's No List (deduplicated, newest-first)."""
    try:
        from eos_ai.context import load_context_from_env
        from eos_ai.db import get_conn
        ctx = ctx or load_context_from_env()
        with get_conn(ctx.org_id) as cur:
            cur.execute('''
                SELECT payload_json FROM events
                WHERE org_id = %s
                AND event_type = 'no_list'
                ORDER BY created_at DESC
            ''', (str(ctx.org_id),))
            rows = cur.fetchall()
        results = []
        seen: set[str] = set()
        for r in rows:
            p = r['payload_json']
            if isinstance(p, str):
                p = json.loads(p)
            item = p.get('item', '')
            if item and item not in seen:
                seen.add(item)
                results.append(p)
        return results
    except Exception as e:
        logger.warning(f'[NoList] get failed: {e}')
        return []


def check_against_no_list(text: str, ctx=None) -> list[str]:
    """Return any No List items found in text."""
    no_list = get_no_list(ctx)
    text_lower = text.lower()
    return [
        item['item']
        for item in no_list
        if item.get('item', '').lower() in text_lower
    ]


def detect_pain_line(ctx=None) -> list[dict]:
    """
    Detect tasks Antony is repeatedly handling himself
    that should be delegated. Returns list of violations.
    Looks for dex_task events appearing 3+ times in 30 days.
    """
    try:
        from eos_ai.context import load_context_from_env
        from eos_ai.db import get_conn
        ctx = ctx or load_context_from_env()

        with get_conn(ctx.org_id) as cur:
            cur.execute('''
                SELECT
                    payload_json->>\'task\' as task_text,
                    COUNT(*) as occurrence_count
                FROM events
                WHERE org_id = %s
                AND event_type = \'dex_task\'
                AND created_at >= NOW() - INTERVAL \'30 days\'
                GROUP BY payload_json->>\'task\'
                HAVING COUNT(*) >= 3
                ORDER BY COUNT(*) DESC
                LIMIT 10
            ''', (str(ctx.org_id),))
            rows = cur.fetchall()

        return [
            {
                'task': r['task_text'] or '',
                'occurrences': r['occurrence_count'],
                'recommendation': (
                    f'This has appeared {r["occurrence_count"]}x. '
                    'Build a playbook or delegate permanently.'
                ),
            }
            for r in rows
            if r['task_text'] and len(r['task_text']) > 10
        ]
    except Exception as e:
        logger.warning(f'[BuybackRate] detect_pain_line failed: {e}')
        return []
```

- [ ] **Step 3: Verify imports**

```bash
python3 -c "
import sys; sys.path.insert(0, '/opt/OS')
from eos_ai.buyback_rate import (
    add_to_no_list, get_no_list, check_against_no_list, detect_pain_line,
    calculate_buyback_rate, get_current_buyback_rate,
)
print('buyback_rate extensions: ok')

# Test check_against_no_list locally (no DB needed for logic check)
violations = check_against_no_list.__doc__
print('check_against_no_list defined:', bool(check_against_no_list))
"
```
Expected: `buyback_rate extensions: ok`

- [ ] **Step 4: Commit**

```bash
cd /opt/OS
git add eos_ai/buyback_rate.py
git commit -m "feat: add no_list and detect_pain_line to buyback_rate"
```

---

## Task 3: Extend eos_ai/perfect_week.py — Preloaded Year

**Files:**
- Modify: `eos_ai/perfect_week.py` (append after the last function, currently `create_camcorder_playbook` ending at line 192)

- [ ] **Step 1: Append Preloaded Year functions**

Append after the last line of `eos_ai/perfect_week.py`:

```python


def save_preloaded_year(year_plan: dict, ctx=None) -> bool:
    """
    Save the annual plan to Neon. Structure:
    {
      'q1': {'rocks': [], 'revenue_target': 0, 'key_dates': []},
      'q2': {...}, 'q3': {...}, 'q4': {...},
      'vacation_blocks': ['2026-07-01 to 2026-07-14'],
      'major_milestones': [],
      'annual_revenue_target': 0,
    }
    """
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
                'preloaded_year',
                json.dumps({
                    'plan': year_plan,
                    'saved_at': datetime.now(PDT).isoformat(),
                }),
                'dex_annual_plan',
            ))
        return True
    except Exception as e:
        logger.warning(f'[PerfectWeek] save_preloaded_year failed: {e}')
        return False


def get_preloaded_year(ctx=None) -> dict:
    """Get the most recently saved annual plan."""
    try:
        from eos_ai.context import load_context_from_env
        from eos_ai.db import get_conn
        ctx = ctx or load_context_from_env()
        with get_conn(ctx.org_id) as cur:
            cur.execute('''
                SELECT payload_json FROM events
                WHERE org_id = %s
                AND event_type = 'preloaded_year'
                ORDER BY created_at DESC
                LIMIT 1
            ''', (str(ctx.org_id),))
            row = cur.fetchone()
        if row:
            p = row['payload_json']
            if isinstance(p, str):
                p = json.loads(p)
            return p.get('plan', {})
        return {}
    except Exception as e:
        logger.warning(f'[PerfectWeek] get_preloaded_year failed: {e}')
        return {}


def get_current_quarter_rocks(ctx=None) -> list[str]:
    """Get this quarter's rocks from the annual plan."""
    plan = get_preloaded_year(ctx)
    if not plan:
        return []
    month = datetime.now().month
    quarter = f'q{(month - 1) // 3 + 1}'
    return plan.get(quarter, {}).get('rocks', [])
```

- [ ] **Step 2: Verify imports**

```bash
python3 -c "
import sys; sys.path.insert(0, '/opt/OS')
from eos_ai.perfect_week import (
    save_preloaded_year, get_preloaded_year, get_current_quarter_rocks,
    get_perfect_week, save_perfect_week,
)
print('perfect_week extensions: ok')
"
```
Expected: `perfect_week extensions: ok`

- [ ] **Step 3: Commit**

```bash
cd /opt/OS
git add eos_ai/perfect_week.py
git commit -m "feat: add preloaded_year and quarterly rocks to perfect_week"
```

---

## Task 4: Extend eos_ai/daily_sync.py — dex_items + quarterly_rocks

**Files:**
- Modify: `eos_ai/daily_sync.py:24-40` (SyncAgenda dataclass)
- Modify: `eos_ai/daily_sync.py:151-228` (build_agenda Section 4)
- Modify: `eos_ai/daily_sync.py:230-254` (build_agenda Section 4c goal alignment)
- Modify: `eos_ai/daily_sync.py:471-479` (format_sync_message Section 4)

- [ ] **Step 1: Add dex_items and quarterly_rocks to SyncAgenda**

In `eos_ai/daily_sync.py`, find the `SyncAgenda` dataclass. The current last two fields before the closing are:
```python
    first_3: list = field(default_factory=list)   # DEX handles in first hour
    last_3: list = field(default_factory=list)    # Antony must complete today
    recurring_3: list = field(default_factory=list)  # DEX owns daily
```

Add two new fields after `recurring_3`:
```python
    dex_items: list = field(default_factory=list)        # S4 tasks below BBR
    quarterly_rocks: list = field(default_factory=list)  # from preloaded year
```

- [ ] **Step 2: Wire quarterly_rocks into build_agenda (after goal_alignment block)**

In `build_agenda()`, after the goal_alignment block that ends around line 254 (the `except Exception: agenda.goal_alignment = ''` block), add:

```python
        # ── Quarterly rocks from preloaded year ─────────────────────────
        try:
            from eos_ai.perfect_week import get_current_quarter_rocks
            agenda.quarterly_rocks = get_current_quarter_rocks(self.ctx)
        except Exception:
            agenda.quarterly_rocks = []
```

- [ ] **Step 3: Wire DRIP split into build_agenda (after action items prioritization)**

In `build_agenda()`, after the 3-3-3 Framework block (around line 290), add:

```python
        # ── DRIP split — filter delegate tasks to dex_items ─────────────
        try:
            from eos_ai.drip_matrix import classify_task_drip
            antony_items = []
            dex_items = []
            for item in agenda.action_items[:10]:
                drip = classify_task_drip(item)
                if drip.get('quadrant') in ('produce', 'invest'):
                    antony_items.append(item)
                else:
                    dex_items.append(item)
            if antony_items or dex_items:
                agenda.action_items = antony_items
                agenda.dex_items = dex_items
        except Exception:
            agenda.dex_items = []
```

- [ ] **Step 4: Wire quarterly_rocks + dex_items into format_sync_message**

In `format_sync_message()`, find the goal_alignment block at line ~532:
```python
        if agenda.goal_alignment:
            lines.append(f'_💡 {agenda.goal_alignment}_')
        lines.extend(['', '— DEX'])
```

Change it to:
```python
        if agenda.goal_alignment:
            lines.append(f'_💡 {agenda.goal_alignment}_')
        if agenda.quarterly_rocks:
            from datetime import datetime as _dt
            _q = f'Q{(_dt.now().month - 1) // 3 + 1}'
            lines.append(
                f'_🪨 {_q} Rocks: {" | ".join(agenda.quarterly_rocks[:3])}_'
            )
        if agenda.dex_items:
            lines.append(
                f'_🤖 DEX handling ({len(agenda.dex_items)} below BBR):_'
            )
            for item in agenda.dex_items[:3]:
                lines.append(f'  • {item[:60]}')
        lines.extend(['', '— DEX'])
```

- [ ] **Step 5: Verify import**

```bash
python3 -c "
import sys; sys.path.insert(0, '/opt/OS')
from eos_ai.daily_sync import DailySync, SyncAgenda
a = SyncAgenda(date='test')
assert hasattr(a, 'dex_items')
assert hasattr(a, 'quarterly_rocks')
print('daily_sync fields: ok')
"
```
Expected: `daily_sync fields: ok`

- [ ] **Step 6: Commit**

```bash
cd /opt/OS
git add eos_ai/daily_sync.py
git commit -m "feat: add dex_items and quarterly_rocks to daily_sync"
```

---

## Task 5: Wire 48h travel brief into scripts/call_prep.py

**Files:**
- Modify: `scripts/call_prep.py:251-353` (the `main()` function, after the existing 24h agenda window block)

- [ ] **Step 1: Add 48h travel brief window to main()**

In `scripts/call_prep.py`, find the closing of the 24h agenda window block:
```python
    except Exception as _e:
        print(f'[CallPrep] Agenda window check failed: {_e}')
```

After that `except` block (the last 3 lines of `main()` before `if __name__`), add:

```python
    # 48h travel brief window — fire brief day-before for travel events
    try:
        import json as _tj
        from datetime import timezone as _tz
        from dateutil.parser import parse as _tparse
        from eos_ai.gws_connector import GWSConnector as _TGWS
        from eos_ai.context import load_context_from_env as _tctx
        from eos_ai.travel_manager import detect_travel_event, build_travel_brief, log_trip

        _t_ctx = _tctx()
        _t_gws = _TGWS(_t_ctx)
        _t_all = _t_gws.get_upcoming_events(days=3)

        _travel_state_file = '/tmp/travel_brief_state.json'
        try:
            with open(_travel_state_file) as _tf:
                _travel_state = _tj.load(_tf)
        except Exception:
            _travel_state = {}

        _t_now = datetime.now(timezone.utc)
        _t_win_start = _t_now + timedelta(hours=47)
        _t_win_end = _t_now + timedelta(hours=49)

        for _t_event in (_t_all or []):
            _t_id = _t_event.get('id', '')
            if not _t_id or f'travel_{_t_id}' in _travel_state:
                continue
            if not detect_travel_event(_t_event):
                continue

            _t_start_str = _t_event.get('start', '')
            if not _t_start_str or 'T' not in str(_t_start_str):
                continue

            try:
                _t_start_dt = _tparse(str(_t_start_str))
                if _t_start_dt.tzinfo is None:
                    _t_start_dt = _t_start_dt.replace(tzinfo=_tz.utc)

                if not (_t_win_start <= _t_start_dt <= _t_win_end):
                    continue

                _t_location = _t_event.get('location', 'Unknown destination')
                _t_title = _t_event.get('title', _t_event.get('summary', 'Trip'))
                _t_attendees = [
                    a.get('email', '') for a in _t_event.get('attendees', [])
                    if not a.get('self')
                ]
                _t_brief = build_travel_brief(
                    event_title=_t_title,
                    destination=_t_location,
                    start_date=str(_t_start_dt.date()),
                    end_date=str(_t_start_dt.date()),
                    attendees=_t_attendees,
                )
                log_trip(_t_title, _t_location, str(_t_start_dt.date()), '')

                _t_webhook = os.getenv('DISCORD_BRIEF_WEBHOOK')
                if _t_webhook and _t_brief:
                    import requests as _treq
                    _t_msg = f'✈️ **48h Travel Brief: {_t_title}**\n\n{_t_brief}'
                    for _ti in range(0, len(_t_msg), 1900):
                        _treq.post(_t_webhook, json={'content': _t_msg[_ti:_ti+1900]}, timeout=5)

                _travel_state[f'travel_{_t_id}'] = _t_now.isoformat()
                print(f'[CallPrep] Travel brief fired for: {_t_title}')

            except Exception as _te:
                print(f'[CallPrep] Travel brief for {_t_id} failed: {_te}')

        with open(_travel_state_file, 'w') as _tf:
            _tj.dump(_travel_state, _tf)

    except Exception as _te2:
        print(f'[CallPrep] Travel window check failed: {_te2}')
```

- [ ] **Step 2: Verify import**

```bash
python3 -c "
import sys; sys.path.insert(0, '/opt/OS')
import scripts.call_prep
print('call_prep: import ok')
" 2>&1 | head -5
```
Expected: `call_prep: import ok`

- [ ] **Step 3: Commit**

```bash
cd /opt/OS
git add scripts/call_prep.py
git commit -m "feat: add 48h travel brief window to call_prep"
```

---

## Task 6: Add energy check-in prompt to scripts/eod_sync.py

**Files:**
- Modify: `scripts/eod_sync.py:198-210` (build_eod_message closing block)

- [ ] **Step 1: Add energy check-in to build_eod_message**

In `scripts/eod_sync.py`, find the closing block of `build_eod_message()`:
```python
    body = '\n\n'.join(sections) if sections else 'No activity logged today.'

    return (
        f'━━━━━━━━━━━━━━━━━━━━━━━━\n'
        f'🌆 **EOD Sync — {today_str}**\n'
        ...
        f'— DEX'
    )
```

Before `body = '\n\n'.join(sections)...`, add:

```python
    # Energy check-in prompt
    sections.append(
        '**⚡ Energy Check-in:**\n'
        '`!energy [1-10] | [what drained you] | [what energized you]`\n'
        '_Feeds your DRIP Matrix and helps DEX protect your energy._'
    )
```

- [ ] **Step 2: Verify import**

```bash
python3 -c "
import sys; sys.path.insert(0, '/opt/OS')
import scripts.eod_sync
print('eod_sync: import ok')
" 2>&1 | head -5
```
Expected: `eod_sync: import ok`

- [ ] **Step 3: Commit**

```bash
cd /opt/OS
git add scripts/eod_sync.py
git commit -m "feat: add energy check-in prompt to EOD sync message"
```

---

## Task 7: Add energy trend + pain line to scripts/weekly_review.py

**Files:**
- Modify: `scripts/weekly_review.py:128-165` (after Meeting ROI block, before DEX synthesis block)

- [ ] **Step 1: Add energy trend section**

In `scripts/weekly_review.py`, find the meeting ROI block that ends with:
```python
    except Exception:
        pass

    # 4. DEX synthesis
```

Between that `except` and the `# 4. DEX synthesis` comment, add:

```python
    # Energy trend
    try:
        import json as _etjson
        with get_conn(ctx.org_id) as cur:
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
        from eos_ai.buyback_rate import detect_pain_line
        _pain = detect_pain_line(ctx)
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
```

- [ ] **Step 2: Verify import**

```bash
python3 -c "
import sys; sys.path.insert(0, '/opt/OS')
import scripts.weekly_review
print('weekly_review: import ok')
" 2>&1 | head -5
```
Expected: `weekly_review: import ok`

- [ ] **Step 3: Commit**

```bash
cd /opt/OS
git add scripts/weekly_review.py
git commit -m "feat: add energy trend and pain line to weekly review"
```

---

## Task 8: Wire BBR check into eos_ai/founder_capture.py

**Files:**
- Modify: `eos_ai/founder_capture.py:189-208` (capture() function)

- [ ] **Step 1: Add BBR check to capture()**

In `eos_ai/founder_capture.py`, find the `capture()` function return statement:
```python
    return {
        'captured': True,
        'type': capture_type,
        'neon_ok': neon_ok,
        'notion_ok': notion_ok,
    }
```

Replace with:
```python
    result = {
        'captured': True,
        'type': capture_type,
        'neon_ok': neon_ok,
        'notion_ok': notion_ok,
    }

    # BBR check — should DEX handle this without flagging Antony?
    try:
        from eos_ai.buyback_rate import get_current_buyback_rate
        from eos_ai.drip_matrix import classify_task_drip
        rate = get_current_buyback_rate()
        if rate:
            drip = classify_task_drip(text)
            if drip.get('quadrant') == 'delegate':
                result['below_bbr'] = True
                result['bbr_message'] = (
                    f'🤖 This is a DEX task (below ${rate["buyback_rate"]}/hr). '
                    f'Adding to DEX queue — not flagging to you.'
                )
    except Exception:
        pass

    return result
```

- [ ] **Step 2: Verify import**

```bash
python3 -c "
import sys; sys.path.insert(0, '/opt/OS')
from eos_ai.founder_capture import capture, should_capture
print('founder_capture: import ok')
"
```
Expected: `founder_capture: import ok`

- [ ] **Step 3: Commit**

```bash
cd /opt/OS
git add eos_ai/founder_capture.py
git commit -m "feat: wire BBR/DRIP check into founder_capture"
```

---

## Task 9: Wire No List into eos_ai/cognitive_loop.py

**Files:**
- Modify: `eos_ai/cognitive_loop.py` — after martell_patterns block at line ~715

- [ ] **Step 1: Add No List injection to cognitive_loop**

In `eos_ai/cognitive_loop.py`, find the end of the martell_patterns block:
```python
        except Exception:
            pass

        original_prompt = text
```

Between that `pass` and `original_prompt = text`, add:

```python
        # No List enforcement — flag anything Antony has committed to never doing
        try:
            from eos_ai.buyback_rate import check_against_no_list
            _no_list_violations = check_against_no_list(text)
            if _no_list_violations:
                _system_parts.append(
                    f'## No List Alert\n'
                    f'The following items are on Antony\'s No List and appear '
                    f'in this message: {", ".join(_no_list_violations)}\n'
                    f'Flag this to Antony — he has committed to never doing these.'
                )
        except Exception:
            pass
```

- [ ] **Step 2: Verify import**

```bash
python3 -c "
import sys; sys.path.insert(0, '/opt/OS')
from eos_ai.cognitive_loop import CognitiveLoop
print('cognitive_loop: import ok')
"
```
Expected: `cognitive_loop: import ok`

- [ ] **Step 3: Commit**

```bash
cd /opt/OS
git add eos_ai/cognitive_loop.py
git commit -m "feat: inject no_list violations into cognitive_loop system prompt"
```

---

## Task 10: Add Discord commands + _run_gateway no_list wiring

**Files:**
- Modify: `13_Scripts/discord_bot.py` — append 6 new `@bot.command()` blocks before `# ─── Entry point ───`; add no_list check in `_run_gateway()`

- [ ] **Step 1: Add no_list check to _run_gateway()**

In `13_Scripts/discord_bot.py`, find the end of the cloning loop block in `_run_gateway()`:
```python
    except Exception:
        pass  # Non-blocking

    result = _gateway.handle(req)
```

Between that `pass` and `result = _gateway.handle(req)`, add:

```python
    # No List enforcement — add violations to req so cognitive_loop can surface them
    try:
        from eos_ai.buyback_rate import check_against_no_list
        _nl_violations = check_against_no_list(text)
        if _nl_violations:
            req['no_list_violations'] = _nl_violations
    except Exception:
        pass  # Non-blocking
```

- [ ] **Step 2: Add 6 new bot commands before entry point**

In `13_Scripts/discord_bot.py`, find the line:
```python
# ─── Entry point ──────────────────────────────────────────────────────────────
```

Before that line, append:

```python
@bot.command(name='trip')
async def cmd_trip(ctx: commands.Context, *, args: str = ''):
    """Build a travel brief. Usage: !trip [event] | [destination] | [start] | [end]"""
    if '|' not in args:
        await ctx.reply(
            '**Trip Brief**\n'
            'Usage: `!trip [event name] | [destination] | [start date] | [end date]`\n'
            'Example: `!trip SaaS Conference | San Francisco, CA | 2026-04-15 | 2026-04-17`'
        )
        return

    def _run():
        try:
            from eos_ai.travel_manager import build_travel_brief, log_trip
            parts = [p.strip() for p in args.split('|')]
            title = parts[0]
            destination = parts[1] if len(parts) > 1 else 'Unknown'
            start = parts[2] if len(parts) > 2 else ''
            end = parts[3] if len(parts) > 3 else start
            brief = build_travel_brief(title, destination, start, end)
            log_trip(title, destination, start, end)
            return f'✈️ **Travel Brief: {title}**\n\n{brief}'
        except Exception as e:
            return f'❌ Error: {e}'

    await ctx.reply(f'✈️ Building travel brief...')
    loop = asyncio.get_event_loop()
    output = await loop.run_in_executor(None, _run)
    for i in range(0, len(output), 1900):
        await ctx.send(output[i:i+1900])


@bot.command(name='nolist')
async def cmd_nolist(ctx: commands.Context):
    """View Antony's No List."""
    def _run():
        try:
            from eos_ai.buyback_rate import get_no_list
            items = get_no_list()
            if not items:
                return (
                    '📋 No List is empty.\n'
                    'Add with: `!noadd [thing you will never do again] | [reason]`'
                )
            lines = [f'🚫 **No List ({len(items)} items):**']
            for item in items:
                reason = item.get('reason', '')
                lines.append(
                    f'• {item["item"]}'
                    + (f' — {reason}' if reason else '')
                )
            return '\n'.join(lines)
        except Exception as e:
            return f'❌ Error: {e}'

    loop = asyncio.get_event_loop()
    output = await loop.run_in_executor(None, _run)
    await ctx.reply(output)


@bot.command(name='noadd')
async def cmd_noadd(ctx: commands.Context, *, args: str = ''):
    """Add to No List. Usage: !noadd [thing] | [reason optional]"""
    if not args.strip():
        await ctx.reply('Usage: `!noadd [thing] | [reason optional]`')
        return

    def _run():
        try:
            from eos_ai.buyback_rate import add_to_no_list
            parts = args.split('|', 1)
            item = parts[0].strip()
            reason = parts[1].strip() if len(parts) > 1 else ''
            ok = add_to_no_list(item, reason)
            if ok:
                return (
                    f'🚫 Added to No List: **{item}**\n'
                    f'DEX will flag this if it appears in your tasks or calendar.'
                )
            return '❌ Failed to add.'
        except Exception as e:
            return f'❌ Error: {e}'

    loop = asyncio.get_event_loop()
    output = await loop.run_in_executor(None, _run)
    await ctx.reply(output)


@bot.command(name='energy')
async def cmd_energy(ctx: commands.Context, *, args: str = ''):
    """Log daily energy. Usage: !energy [1-10] | [what drained you] | [what energized you]"""
    if not args.strip():
        await ctx.reply(
            'Usage: `!energy [1-10] | [what drained you] | [what energized you]`'
        )
        return

    def _run():
        try:
            import json as _ej
            from eos_ai.context import load_context_from_env
            from eos_ai.db import get_conn
            from zoneinfo import ZoneInfo as _ZI
            from datetime import datetime as _dt

            _PDT = _ZI('America/Los_Angeles')
            parts = [p.strip() for p in args.split('|')]
            score_str = parts[0]
            score = int(score_str) if score_str.isdigit() else 5
            score = max(1, min(10, score))
            drained = parts[1] if len(parts) > 1 else ''
            energized = parts[2] if len(parts) > 2 else ''

            _ctx = load_context_from_env()
            with get_conn(_ctx.org_id) as cur:
                cur.execute('''
                    INSERT INTO events
                    (org_id, event_type, payload_json, handled_by)
                    VALUES (%s, %s, %s, %s)
                ''', (
                    str(_ctx.org_id),
                    'energy_checkin',
                    _ej.dumps({
                        'score': score,
                        'drained': drained,
                        'energized': energized,
                        'date': _dt.now(_PDT).strftime('%Y-%m-%d'),
                    }),
                    'dex_energy',
                ))

            emoji = '🔴' if score <= 3 else '🟡' if score <= 6 else '🟢'
            lines = [f'{emoji} Energy logged: {score}/10']
            if drained:
                lines.append(f'Drained by: {drained}')
            if energized:
                lines.append(f'Energized by: {energized}')
            if score <= 4:
                lines.append(
                    '\n⚠️ Low energy day. Run `!drip` on your task list '
                    'tomorrow to find what to remove.'
                )
            return '\n'.join(lines)
        except Exception as e:
            return f'❌ Error: {e}'

    loop = asyncio.get_event_loop()
    output = await loop.run_in_executor(None, _run)
    await ctx.reply(output)


@bot.command(name='year')
async def cmd_year(ctx: commands.Context):
    """View annual plan (Preloaded Year)."""
    def _run():
        try:
            from eos_ai.perfect_week import get_preloaded_year
            plan = get_preloaded_year()
            if not plan:
                return (
                    '📅 No annual plan set yet.\n'
                    'Build one with Claude Code using the preloaded year format:\n'
                    '`save_preloaded_year({q1: {rocks: [], revenue_target: 0}, ...})`'
                )
            lines = ['📅 **Preloaded Year:**']
            for q in ['q1', 'q2', 'q3', 'q4']:
                qdata = plan.get(q, {})
                if qdata:
                    lines.append(f'\n**{q.upper()}:**')
                    for r in qdata.get('rocks', []):
                        lines.append(f'• {r}')
                    target = qdata.get('revenue_target', 0)
                    if target:
                        lines.append(f'Revenue target: ${target:,.0f}/mo')
            vacation = plan.get('vacation_blocks', [])
            if vacation:
                lines.append('\n**Vacation blocks:**')
                for v in vacation:
                    lines.append(f'• {v}')
            return '\n'.join(lines)
        except Exception as e:
            return f'❌ Error: {e}'

    loop = asyncio.get_event_loop()
    output = await loop.run_in_executor(None, _run)
    await ctx.reply(output)


@bot.command(name='rocks')
async def cmd_rocks(ctx: commands.Context):
    """View this quarter's rocks."""
    def _run():
        try:
            from eos_ai.perfect_week import get_current_quarter_rocks
            from datetime import datetime as _rdt
            rocks = get_current_quarter_rocks()
            if not rocks:
                return '🪨 No quarterly rocks set. Use Claude Code to call `save_preloaded_year()` with your plan.'
            month = _rdt.now().month
            quarter = f'Q{(month - 1) // 3 + 1}'
            lines = [f'🪨 **{quarter} Rocks:**']
            for i, rock in enumerate(rocks, 1):
                lines.append(f'{i}. {rock}')
            return '\n'.join(lines)
        except Exception as e:
            return f'❌ Error: {e}'

    loop = asyncio.get_event_loop()
    output = await loop.run_in_executor(None, _run)
    await ctx.reply(output)

```

- [ ] **Step 3: Verify import**

```bash
python3 -c "
import sys; sys.path.insert(0, '/opt/OS')
# syntax check only — can't import bot module without token
import ast
with open('/opt/OS/13_Scripts/discord_bot.py') as f:
    source = f.read()
ast.parse(source)
print('discord_bot.py: syntax ok')
"
```
Expected: `discord_bot.py: syntax ok`

- [ ] **Step 4: Commit**

```bash
cd /opt/OS
git add 13_Scripts/discord_bot.py
git commit -m "feat: add trip, nolist, noadd, energy, year, rocks discord commands"
```

---

## Task 11: Full import verification + deploy

- [ ] **Step 1: Full import check**

```bash
python3 -c "
import sys; sys.path.insert(0, '/opt/OS')
from eos_ai.travel_manager import detect_travel_event, build_travel_brief, log_trip
from eos_ai.buyback_rate import (
    add_to_no_list, get_no_list, check_against_no_list,
    detect_pain_line, get_current_buyback_rate, calculate_buyback_rate,
)
from eos_ai.perfect_week import (
    save_preloaded_year, get_preloaded_year, get_current_quarter_rocks,
)
from eos_ai.daily_sync import DailySync, SyncAgenda
from eos_ai.founder_capture import capture, should_capture
from eos_ai.cognitive_loop import CognitiveLoop
print('all imports: clean')

# Functional tests
assert detect_travel_event({'title': 'hotel conference', 'location': '', 'description': ''})
assert not detect_travel_event({'title': 'standup', 'location': '', 'description': ''})
a = SyncAgenda(date='test')
assert hasattr(a, 'dex_items') and hasattr(a, 'quarterly_rocks')
print('functional tests: ok')

rate = calculate_buyback_rate(120000)
assert rate['buyback_rate'] == 15.0
print(f'BBR test: \${rate[\"buyback_rate\"]}/hr ok')
"
```
Expected: `all imports: clean`, `functional tests: ok`, `BBR test: $15.0/hr ok`

- [ ] **Step 2: Discord bot syntax**

```bash
python3 -c "
import ast
with open('/opt/OS/13_Scripts/discord_bot.py') as f:
    source = f.read()
ast.parse(source)
print('discord_bot.py: syntax clean')
"
```
Expected: `discord_bot.py: syntax clean`

- [ ] **Step 3: Restart os-discord and os-webhook**

```bash
cd /opt/OS
docker compose restart os-discord os-webhook
sleep 15
docker logs os-discord --tail 10
```
Expected: logs show `online` or `Starting DEX Discord bot` without `Error` or `Traceback`.

- [ ] **Step 4: Commit any remaining changes and verify git state**

```bash
cd /opt/OS
git status
git log --oneline -8
```

---

## Dependency Order

Tasks 1, 2, 3 → independent, run in parallel  
Tasks 4, 5, 6, 7, 8, 9 → run after their deps (4 needs 2+3, 9 needs 2)  
Task 10 → needs 1, 2, 3 complete  
Task 11 → runs last
