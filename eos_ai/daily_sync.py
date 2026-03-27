"""
DailySyncEngine — Dan Martell's Daily Sync Meeting format.

DEX drives the meeting. Antony just responds.
Posted at 6am in #morning-brief via Discord.

7-section agenda (exact Martell system):
  1. Calendar review
  2. Purchases / expenses
  3. Past meeting action items
  4. Antony's action items
  5. Pipeline feedback loop
  6. Emails for review (REVIEW folder only)
  7. Questions for Antony (shrinks as DEX clones)

The cloning goal: Section 7 starts long.
Over time it shrinks to zero.
DEX learns Antony's decisions.
DEX responds without asking.
This is the goal: DEX = Antony's clone.
"""

from dataclasses import dataclass, field
from datetime import date


@dataclass
class SyncAgenda:
    date: str
    calendar_review: list[str]       = field(default_factory=list)
    purchases_expenses: list[str]    = field(default_factory=list)
    past_meeting_actions: list[str]  = field(default_factory=list)
    antony_action_items: list[str]   = field(default_factory=list)
    pipeline_feedback: list[str]     = field(default_factory=list)
    emails_for_review: list[str]     = field(default_factory=list)
    questions_for_antony: list[str]  = field(default_factory=list)


class DailySyncEngine:

    def __init__(self, ctx):
        self.ctx = ctx

    def build_agenda(self) -> SyncAgenda:
        """Pull live data for each of the 7 agenda sections."""
        agenda = SyncAgenda(date=date.today().strftime('%A, %B %d'))

        # ── Section 1: Calendar ──────────────────────────────────────────
        try:
            from eos_ai.gws_connector import GWSConnector
            gws    = GWSConnector()
            events = gws.get_today_events()
            for e in events[:5]:
                title = e.get('title', '') or e.get('summary', '')
                start = e.get('start', '')
                if start and 'T' in str(start):
                    start = str(start).split('T')[1][:5]
                elif isinstance(start, dict):
                    dt = start.get('dateTime', '') or start.get('date', '')
                    if dt and 'T' in dt:
                        start = dt.split('T')[1][:5]
                    else:
                        start = dt
                agenda.calendar_review.append(f'{start} — {title}')
        except Exception as e:
            print(f'[DailySync] Calendar: {e}')

        # ── Section 2: Receipts / purchases ─────────────────────────────
        try:
            from eos_ai.gws_connector import GWSConnector
            gws       = GWSConnector()
            # Look specifically for financial emails
            financials = gws.get_recent_emails(
                max_results=20,
                query='receipt OR invoice OR payment OR order',
            )
            for email in financials[:5]:
                subject = email.get('subject', '')
                if subject:
                    agenda.purchases_expenses.append(subject[:60])
        except Exception as e:
            print(f'[DailySync] Purchases: {e}')

        # ── Section 3 & 4: Action items ──────────────────────────────────
        try:
            from eos_ai.accountability import AccountabilityEngine
            ae      = AccountabilityEngine(self.ctx)
            pending = ae.get_pending_follow_ups()
            for item in pending[:5]:
                text = item.get('text', '') or item.get('description', '')
                if text:
                    agenda.antony_action_items.append(text[:80])
        except Exception as e:
            print(f'[DailySync] Action items: {e}')

        # ── Section 5: Pipeline feedback ─────────────────────────────────
        try:
            import json
            from eos_ai.db import get_conn
            with get_conn(self.ctx.org_id) as cur:
                cur.execute('''
                    SELECT payload_json
                    FROM events
                    WHERE org_id = %s
                    AND event_type = 'pipeline_entry'
                    ORDER BY created_at DESC
                    LIMIT 5
                ''', (self.ctx.org_id,))
                rows = cur.fetchall()
                for row in rows:
                    data = row[0]
                    if isinstance(data, str):
                        data = json.loads(data)
                    name  = data.get('name', '')
                    stage = data.get('stage', '')
                    if name:
                        agenda.pipeline_feedback.append(f'{name} → {stage}')
        except Exception as e:
            print(f'[DailySync] Pipeline: {e}')

        # ── Section 6: REVIEW folder emails ──────────────────────────────
        try:
            from eos_ai.email_gps import EmailGPS, EmailFolder
            gps       = EmailGPS(self.ctx)
            processed = gps.process_inbox(limit=20)
            review    = processed.get(EmailFolder.REVIEW, [])
            for e in review[:5]:
                sender = e.from_name or e.from_address
                agenda.emails_for_review.append(
                    f'{sender}: {e.subject[:50]}'
                )
        except Exception as e:
            print(f'[DailySync] Emails: {e}')

        # ── Section 7: Questions for Antony (DEX uncertainty log) ────────
        # Shrinks over time as DEX learns Antony's decision patterns.
        # Goal: reaches zero — DEX is a full clone.
        try:
            import json
            from eos_ai.db import get_conn
            with get_conn(self.ctx.org_id) as cur:
                cur.execute('''
                    SELECT payload_json
                    FROM events
                    WHERE org_id = %s
                    AND event_type = 'dex_question'
                    AND payload_json->>'answered' = 'false'
                    ORDER BY created_at DESC
                    LIMIT 5
                ''', (self.ctx.org_id,))
                rows = cur.fetchall()
                for row in rows:
                    data = row[0]
                    if isinstance(data, str):
                        data = json.loads(data)
                    q = data.get('question', '')
                    if q:
                        agenda.questions_for_antony.append(q[:80])
        except Exception as e:
            print(f'[DailySync] Questions: {e}')

        return agenda

    def format_sync_message(self, agenda: SyncAgenda) -> str:
        """Format agenda into Discord-ready message. DEX drives."""
        lines = [
            '━━━━━━━━━━━━━━━━━━━━━━━━',
            f'📋 **DAILY SYNC — {agenda.date}**',
            '━━━━━━━━━━━━━━━━━━━━━━━━',
            '',
        ]

        # 1. Calendar
        lines.append('**1. 📅 Calendar Today**')
        if agenda.calendar_review:
            for item in agenda.calendar_review:
                lines.append(f'  • {item}')
        else:
            lines.append('  Clear — no meetings')
        lines.append('')

        # 2. Purchases
        if agenda.purchases_expenses:
            lines.append('**2. 💳 Purchases/Expenses**')
            for item in agenda.purchases_expenses:
                lines.append(f'  • {item}')
            lines.append('')

        # 3. Past meeting actions
        if agenda.past_meeting_actions:
            lines.append('**3. 🔄 Past Meeting Actions**')
            for item in agenda.past_meeting_actions:
                lines.append(f'  • {item}')
            lines.append('')

        # 4. Antony's action items
        if agenda.antony_action_items:
            lines.append('**4. ✅ Your Action Items**')
            for item in agenda.antony_action_items:
                lines.append(f'  • {item}')
            lines.append('')
        else:
            lines.append('**4. ✅ Action Items:** None pending')
            lines.append('')

        # 5. Pipeline
        if agenda.pipeline_feedback:
            lines.append('**5. 🎯 Pipeline Updates**')
            for item in agenda.pipeline_feedback:
                lines.append(f'  • {item}')
            lines.append('')

        # 6. Emails for review
        if agenda.emails_for_review:
            lines.append('**6. 📬 Emails — Review Folder**')
            for item in agenda.emails_for_review:
                lines.append(f'  • {item}')
            lines.append('')
        else:
            lines.append('**6. 📬 Emails:** Nothing needs you')
            lines.append('')

        # 7. Questions (shrinks over time as DEX clones Antony)
        if agenda.questions_for_antony:
            lines.append('**7. ❓ Questions for You**')
            for item in agenda.questions_for_antony:
                lines.append(f'  • {item}')
            lines.append('')

        # Closing — the only thing that matters
        lines.extend([
            '━━━━━━━━━━━━━━━━━━━━━━━━',
            '**The only thing that matters today:**',
            'Send 20 DMs for Lyfe Institute.',
            'I handle everything else.',
            '',
            '— DEX',
        ])

        return '\n'.join(lines)

    def run_sync(self) -> str:
        """Build agenda and return formatted sync message."""
        agenda = self.build_agenda()
        return self.format_sync_message(agenda)
