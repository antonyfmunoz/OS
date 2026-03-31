"""
DailySync — Dan Martell's Daily Sync Meeting format.

DEX drives the meeting. Antony just responds.
Posted at 6am in #morning-brief via Discord.

7-section agenda (soul doc exact order):
  1. Your list      — Antony's ideas/requests for DEX captured from Discord
  2. Calendar       — 6 weeks on Mondays, 2 weeks other days.
  3. Past meetings  — open loops from Notion Meetings DB
  4. Action items   — dex_task events, deduplicated
  5. Projects       — active work + blockers
  6. Emails         — TO_RESPOND + REVIEW from GPS
  7. Questions      — unanswered dex_question events (omitted if none)

The cloning goal: every question answered trains DEX not to ask it again.
DEX responds without asking. This is the goal: DEX = Antony's clone.
"""

from dataclasses import dataclass, field
from datetime import date, datetime


@dataclass
class SyncAgenda:
    date: str
    your_list: list[str]             = field(default_factory=list)  # S1
    calendar_review: list[str]       = field(default_factory=list)  # S2
    past_meeting_actions: list[str]  = field(default_factory=list)  # S3
    action_items: list[str]          = field(default_factory=list)  # S4
    project_updates: list[str]       = field(default_factory=list)  # S5
    emails: list[str]                = field(default_factory=list)  # S6
    questions: list[str]             = field(default_factory=list)  # S7 (omitted if empty)
    is_monday: bool                  = False
    top_item_reason: str             = ''                            # S4 priority reason
    goal_alignment: str              = ''                            # goal-to-action check
    subscription_alerts: list        = field(default_factory=list)  # renewal warnings
    first_3: list = field(default_factory=list)   # DEX handles in first hour
    last_3: list = field(default_factory=list)    # Antony must complete today
    recurring_3: list = field(default_factory=list)  # DEX owns daily
    dex_items: list = field(default_factory=list)        # S4 tasks below BBR
    quarterly_rocks: list = field(default_factory=list)  # from preloaded year
    important_dates: list = field(default_factory=list)  # upcoming personal dates


def _normalize_task(text: str) -> str:
    """Strip 'TASK:' prefix and normalize for dedup comparison."""
    t = text.strip()
    if t.upper().startswith('TASK:'):
        t = t[5:].strip()
    return t.lower()


class DailySync:

    def __init__(self, ctx):
        self.ctx = ctx

    def build_agenda(self) -> SyncAgenda:
        today     = date.today()
        is_monday = today.weekday() == 0  # Monday = 0
        agenda    = SyncAgenda(
            date=today.strftime('%A, %B %d'),
            is_monday=is_monday,
        )

        # ── Section 1: Your list (Antony's requests for DEX) ─────────────
        # Items Antony dropped in Discord for DEX to handle.
        # dex_task events only — questions go to S7.
        try:
            import json
            from eos_ai.db import get_conn
            with get_conn(self.ctx.org_id) as cur:
                cur.execute('''
                    SELECT payload_json
                    FROM events
                    WHERE org_id = %s
                      AND event_type = 'dex_task'
                      AND (
                        payload_json->>'status' IS NULL
                        OR payload_json->>'completed' = 'false'
                      )
                    ORDER BY created_at DESC
                    LIMIT 5
                ''', (self.ctx.org_id,))
                for row in cur.fetchall():
                    data = row[0]
                    if isinstance(data, str):
                        data = json.loads(data)
                    text = data.get('task', '')
                    if text:
                        agenda.your_list.append(text[:80])
        except Exception as e:
            print(f'[DailySync] Your list: {e}')

        # ── Section 2: Calendar review ────────────────────────────────────
        # Mondays: 6 weeks out. Other days: 2 weeks out.
        try:
            from eos_ai.gws_connector import GWSConnector
            gws  = GWSConnector()
            days = 42 if is_monday else 14
            events = gws.get_upcoming_events(days=days)
            if is_monday:
                agenda.calendar_review.append('📅 Monday — 6-week calendar review')
            for e in events[:10]:
                title    = e.get('title', 'Untitled')
                start    = e.get('start', '')
                location = e.get('location', '')
                desc     = e.get('description', '')
                meet     = e.get('meet_link', '')

                if start and 'T' in str(start):
                    try:
                        dt    = datetime.fromisoformat(str(start).replace('Z', '+00:00'))
                        label = dt.strftime('%a %b %d %I:%M%p').lstrip('0')
                    except Exception:
                        label = str(start)[:16]
                else:
                    label = str(start)[:10] if start else '?'

                missing = []
                if not location and not meet:
                    missing.append('no location/link')
                if not desc:
                    missing.append('no description')

                line = f'{label} — {title}'
                if missing:
                    line += f' ⚠️ {", ".join(missing)}'
                agenda.calendar_review.append(line)

        except Exception as e:
            print(f'[DailySync] Calendar: {e}')

        # ── Section 3: Past meetings — open loops ────────────────────────
        # Completed calls with unresolved follow-ups from Notion Meetings DB.
        try:
            from eos_ai.meetings import get_open_loop_meetings
            _open_loops = get_open_loop_meetings(days_back=7)
            if _open_loops:
                for m in _open_loops:
                    person       = m.get('person', '')
                    meeting_date = m.get('date', '')[:10]
                    loops        = m.get('open_loops', '')
                    if person and loops:
                        agenda.past_meeting_actions.append(
                            f"{person} ({meeting_date}): {loops[:80]}"
                        )
            if not agenda.past_meeting_actions:
                agenda.past_meeting_actions.append('No open loops from past 7 days.')
        except Exception as e:
            print(f'[DailySync] Past meetings: {e}')

        # ── Section 4: Action items (deduplicated) ───────────────────────
        # dex_task events from the last 7 days, not completed.
        # Normalized dedup: strip "TASK:" prefix, case-insensitive.
        try:
            import json
            from eos_ai.db import get_conn
            with get_conn(self.ctx.org_id) as cur:
                cur.execute('''
                    SELECT payload_json FROM events
                    WHERE org_id = %s
                    AND event_type = 'dex_task'
                    AND (payload_json->>\'status\' IS NULL
                         OR payload_json->>\'status\' != \'completed\')
                    AND created_at >= NOW() - INTERVAL \'7 days\'
                    ORDER BY created_at DESC
                    LIMIT 20
                ''', (str(self.ctx.org_id),))
                rows = cur.fetchall()

            seen_normalized: set[str] = set()
            for r in rows:
                payload = r['payload_json'] if isinstance(r['payload_json'], dict) else json.loads(r['payload_json'])
                task = payload.get('task', payload.get('description', ''))
                if not task:
                    continue
                norm = _normalize_task(task)
                if norm in seen_normalized:
                    continue
                seen_normalized.add(norm)
                # Store clean version (strip TASK: prefix)
                clean = task.strip()
                if clean.upper().startswith('TASK:'):
                    clean = clean[5:].strip()
                agenda.action_items.append(clean[:100])

            if not agenda.action_items:
                agenda.action_items = ['No open action items.']
        except Exception as e:
            agenda.action_items = [f'Action items unavailable: {e}']

        # ── Section 4b: Prioritize action items ─────────────────────────
        if len(agenda.action_items) > 1:
            try:
                from eos_ai.model_router import get_router, TaskType
                from eos_ai.portfolio_agent import PortfolioAgent
                import json as _pjson
                router = get_router()
                model = router.route(TaskType.FAST_RESPONSE)

                pa = PortfolioAgent(self.ctx)
                ventures = pa.scan_all_ventures()
                binding = pa.identify_binding_constraint(ventures)
                constraint = binding.recommendation if binding else ''

                items_text = '\n'.join(
                    f'{i+1}. {item}'
                    for i, item in enumerate(agenda.action_items)
                )
                prompt = (
                    'You are DEX, EA to Antony Munoz.\n'
                    f'Portfolio binding constraint: {constraint}\n\n'
                    'Rank these action items by priority (highest leverage first).\n'
                    'Consider: revenue impact, binding constraint alignment, '
                    'time sensitivity, dependencies.\n\n'
                    f'Items:\n{items_text}\n\n'
                    'Return JSON only:\n'
                    '{"ranked": ["item text in priority order"], '
                    '"top_item_reason": "one sentence why #1 is first"}'
                )
                result = router.call(model, prompt).strip()
                if '```' in result:
                    result = result.split('```')[1].replace('json', '').strip()
                ranked = _pjson.loads(result)
                agenda.action_items = ranked.get('ranked', agenda.action_items)
                agenda.top_item_reason = ranked.get('top_item_reason', '')
            except Exception as e:
                print(f'[DailySync] Prioritization failed: {e}')
                agenda.top_item_reason = ''

        # ── Section 4c: Goal alignment — does today's top item move the needle?
        try:
            from eos_ai.model_router import get_router, TaskType
            from eos_ai.portfolio_agent import PortfolioAgent
            _router = get_router()
            _model = _router.route(TaskType.FAST_RESPONSE)

            _pa = PortfolioAgent(self.ctx)
            _ventures = _pa.scan_all_ventures()
            _binding = _pa.identify_binding_constraint(_ventures)
            _constraint = _binding.recommendation if _binding else 'Close the first Initiate Arena client'

            _top_item = agenda.action_items[0] if agenda.action_items else ''
            if _top_item and _top_item != 'No open action items.':
                _align_prompt = (
                    'You are DEX, EA to Antony Munoz.\n\n'
                    f'Binding constraint: {_constraint}\n'
                    f'Top action item today: {_top_item}\n\n'
                    'In one sentence: does this action item move the needle on the binding '
                    'constraint? If yes, say why briefly. If no, say what should replace it.\n'
                    'Be direct. No hedging.'
                )
                agenda.goal_alignment = _router.call(_model, _align_prompt).strip()
        except Exception:
            agenda.goal_alignment = ''

        # ── Quarterly rocks from preloaded year ─────────────────────────
        try:
            from eos_ai.perfect_week import get_current_quarter_rocks
            agenda.quarterly_rocks = get_current_quarter_rocks(self.ctx)
        except Exception:
            agenda.quarterly_rocks = []

        # ── 3-3-3 Framework (Dan Martell) ────────────────────────────────────
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
  "first_3": ["Thing DEX handles in first hour so Antony doesn't have to", "Thing 2", "Thing 3"],
  "last_3": ["Most important thing Antony must personally complete today", "Thing 2", "Thing 3"],
  "recurring_3": ["Task DEX owns completely every day", "Task 2", "Task 3"]
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

        # ── Section 5: Projects ──────────────────────────────────────────
        # In-progress items from all three Notion Tasks databases.
        try:
            import requests as _req
            import os as _os
            _token = _os.getenv('NOTION_API_KEY')
            _headers = {
                'Authorization': f'Bearer {_token}',
                'Notion-Version': '2022-06-28',
                'Content-Type': 'application/json',
            }
            _dbs = {
                'Lyfe Institute':    _os.getenv('NOTION_YOUR_LIST_LYFE'),
                'Empyrean Creative': _os.getenv('NOTION_YOUR_LIST_EMPYREAN'),
                'Personal Brand':    _os.getenv('NOTION_YOUR_LIST_BRAND'),
            }
            agenda.project_updates = []
            for _venture, _db_id in _dbs.items():
                if not _db_id:
                    continue
                _resp = _req.post(
                    f'https://api.notion.com/v1/databases/{_db_id}/query',
                    headers=_headers,
                    json={
                        'filter': {'property': 'Status', 'select': {'equals': 'In progress'}},
                        'page_size': 5,
                    },
                    timeout=10,
                )
                _results = _resp.json().get('results', [])
                for _r in _results:
                    _props = _r.get('properties', {})
                    _name = _props.get('Name', {}).get('title', [{}])[0].get('plain_text', '')
                    _priority = _props.get('Priority', {}).get('select', {}).get('name', '')
                    if _name:
                        _line = f'[{_venture}] {_name}'
                        if _priority:
                            _line += f' ({_priority})'
                        agenda.project_updates.append(_line)
            if not agenda.project_updates:
                agenda.project_updates = ['No active projects in progress.']
        except Exception as e:
            agenda.project_updates = [f'Projects unavailable: {e}']

        # ── Section 6: Emails ────────────────────────────────────────────
        # TO_RESPOND + REVIEW from GPS labels.
        try:
            from eos_ai.email_gps import EmailGPS
            gps            = EmailGPS(self.ctx)
            review_emails  = gps.get_emails_for_review(limit=5)
            respond_emails = gps.get_emails_to_respond(limit=5)
            agenda.emails  = []
            seen_emails: set[tuple[str, str]] = set()

            def _dedup_email(e: dict) -> str | None:
                key = (e.get('from', '').strip().lower(), e.get('subject', '').strip().lower())
                if key in seen_emails:
                    return None
                seen_emails.add(key)
                return f'\u2022 {e.get("from", "")} \u2014 {e.get("subject", "")[:80]}'

            if respond_emails:
                respond_lines = [l for e in respond_emails if (l := _dedup_email(e))]
                if respond_lines:
                    agenda.emails.append(f'**To Respond ({len(respond_lines)}):**')
                    agenda.emails.extend(respond_lines)
            if review_emails:
                review_lines = [l for e in review_emails if (l := _dedup_email(e))]
                if review_lines:
                    agenda.emails.append(f'**To Review ({len(review_lines)}):**')
                    agenda.emails.extend(review_lines)
            if not agenda.emails:
                agenda.emails = ['Inbox clear.']
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
        except Exception as e:
            agenda.emails = [f'Email unavailable: {e}']

        # ── Section 7: Questions (unanswered dex_question events) ────────
        # Only populated if there are real questions DEX cannot resolve alone.
        try:
            import json as _json
            from eos_ai.db import get_conn
            with get_conn(self.ctx.org_id) as cur:
                cur.execute('''
                    SELECT payload_json FROM events
                    WHERE org_id = %s
                    AND event_type = 'dex_question'
                    AND (payload_json->>\'answered\' IS NULL
                         OR payload_json->>\'answered\' != \'true\')
                    AND created_at >= NOW() - INTERVAL \'48 hours\'
                    ORDER BY created_at DESC
                    LIMIT 5
                ''', (str(self.ctx.org_id),))
                rows = cur.fetchall()
            for r in rows:
                payload = r['payload_json'] if isinstance(r['payload_json'], dict) else _json.loads(r['payload_json'])
                q = payload.get('question', '')
                if q:
                    agenda.questions.append(q[:150])
        except Exception:
            pass  # Questions section simply omitted on error

        # Subscription renewal alerts
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

        # ── Upcoming important dates (next 14 days) ──────────────────────
        try:
            from eos_ai.personal_admin import get_upcoming_dates
            upcoming = get_upcoming_dates(days=14, ctx=self.ctx)
            if upcoming:
                agenda.important_dates = [
                    f'{d["person"]} — {d["type"]} in {d["days_until"]} days'
                    for d in upcoming[:3]
                ]
            else:
                agenda.important_dates = []
        except Exception:
            agenda.important_dates = []

        return agenda

    def _get_closing_line(self) -> str:
        """Return the binding constraint recommendation for the lowest health venture."""
        try:
            from eos_ai.portfolio_agent import PortfolioAgent
            pa       = PortfolioAgent(self.ctx)
            ventures = pa.scan_all_ventures()
            binding  = pa.identify_binding_constraint(ventures)
            if binding and binding.recommendation:
                return binding.recommendation
            if binding and binding.binding_constraint:
                return binding.binding_constraint
        except Exception:
            pass
        return 'Close the first Initiate Arena client.'

    def format_sync_message(self, agenda: SyncAgenda, closing_line: str = '') -> str:
        """Format agenda into Discord-ready message. DEX drives."""
        lines = [
            '━━━━━━━━━━━━━━━━━━━━━━━━',
            f'📋 **DAILY SYNC — {agenda.date}**',
            '━━━━━━━━━━━━━━━━━━━━━━━━',
            '',
        ]

        # 1. Your list
        lines.append('**1. 📝 Your List**')
        if agenda.your_list:
            for item in agenda.your_list:
                lines.append(f'  • {item}')
        else:
            lines.append('  No pending requests')
        lines.append('')

        # 2. Calendar
        week_range = '6-week view' if agenda.is_monday else '2-week view'
        lines.append(f'**2. 📅 Calendar ({week_range})**')
        if agenda.calendar_review:
            for item in agenda.calendar_review:
                lines.append(f'  • {item}')
        else:
            lines.append('  Clear — no upcoming meetings')
        lines.append('')

        # 3. Past meetings
        lines.append('**3. 🔄 Past Meetings — Open Loops**')
        for item in agenda.past_meeting_actions:
            lines.append(f'  • {item}')
        lines.append('')

        # 4. Action items (prioritized)
        lines.append('**4. ✅ Action Items**')
        for i, item in enumerate(agenda.action_items):
            if i == 0 and len(agenda.action_items) > 1:
                lines.append(f'  • **{item}**')
                if agenda.top_item_reason:
                    lines.append(f'    ↳ _{agenda.top_item_reason}_')
            else:
                lines.append(f'  • {item}')
        lines.append('')

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

        # 5. Projects
        lines.append('**5. 🎯 Projects**')
        if agenda.project_updates:
            for item in agenda.project_updates:
                lines.append(f'  • {item}')
        else:
            lines.append('  No new activity')
        lines.append('')

        # 6. Emails
        lines.append('**6. 📧 Emails**')
        for item in agenda.emails:
            lines.append(f'  {item}')
        lines.append('')

        # 7. Questions (only if any)
        if agenda.questions:
            lines.append('**7. ❓ Questions for You**')
            for item in agenda.questions:
                lines.append(f'  • {item}')
            lines.append('')

        # Subscription renewal alerts
        if agenda.subscription_alerts:
            lines.append('**💳 Renewals this week:**')
            for alert in agenda.subscription_alerts:
                lines.append(f'  {alert}')
            lines.append('')

        # Important dates
        if agenda.important_dates:
            lines.append('**🗓️ Coming up:**')
            for d in agenda.important_dates:
                lines.append(f'  • {d}')
            lines.append('')

        # Closing
        lines.extend([
            '━━━━━━━━━━━━━━━━━━━━━━━━',
            f'**The one thing that matters today:** {closing_line}',
        ])
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

        return '\n'.join(lines)

    def run_sync(self) -> str:
        """Build agenda and return formatted sync message."""
        agenda       = self.build_agenda()
        closing_line = self._get_closing_line()
        return self.format_sync_message(agenda, closing_line)


# Alias for backwards compatibility
DailySyncEngine = DailySync
