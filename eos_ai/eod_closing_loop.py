"""
EODClosingLoop — DEX's end-of-day report.

Runs at 6pm daily. Posts to Discord #morning-brief (same channel as daily sync).

Sections:
  Meetings today         — what actually happened
  Purchases/expenses     — receipts from GPS RECEIPTS label
  Project updates        — pipeline moves, decisions logged
  Decisions made         — answered dex_questions (Antony's logged decisions)

Cron:
  0 18 * * * python3 -c "
  import sys; sys.path.insert(0, '/opt/OS')
  from dotenv import load_dotenv
  load_dotenv('/opt/OS/eos_ai/.env')
  load_dotenv('/opt/OS/13_Scripts/.env')
  from eos_ai.eod_closing_loop import EODClosingLoop
  from eos_ai.context import load_context_from_env
  from eos_ai.discord_utils import post_to_webhook
  import os
  ctx = load_context_from_env()
  eod = EODClosingLoop(ctx)
  report = eod.run()
  webhook = os.getenv('DISCORD_BRIEF_WEBHOOK')
  if webhook:
      post_to_webhook(report, webhook=webhook)
  print(report)
  " >> /opt/OS/logs/eod_closing.log 2>&1
"""

import json
from datetime import date, datetime, timezone, timedelta


class EODClosingLoop:

    def __init__(self, ctx):
        self.ctx = ctx

    def run(self) -> str:
        today_str = date.today().strftime('%A, %B %d')
        sections  = []

        # ── Meetings today ────────────────────────────────────────────────
        meetings = self._get_todays_meetings()
        if meetings:
            section = ['**Meetings today:**']
            for m in meetings:
                section.append(f'  • {m}')
            sections.append('\n'.join(section))

        # ── Purchases / expenses ──────────────────────────────────────────
        purchases = self._get_todays_purchases()
        if purchases:
            section = ['**Purchases/expenses:**']
            for p in purchases:
                section.append(f'  • {p}')
            sections.append('\n'.join(section))

        # ── Overdue invoice check ─────────────────────────────────────────
        try:
            from eos_ai.expense_tracker import get_overdue_invoices
            overdue = get_overdue_invoices()
            if overdue:
                section = [f'**🔴 Overdue invoices ({len(overdue)}):**']
                for inv in overdue[:3]:
                    section.append(
                        f'  • {inv["invoice_id"]} — '
                        f'{inv["client_name"]} — '
                        f'${inv["total"]:,.2f}'
                    )
                sections.append('\n'.join(section))
        except Exception:
            pass

        # ── Project updates ───────────────────────────────────────────────
        updates = self._get_todays_project_updates()
        if updates:
            section = ['**Project updates:**']
            for u in updates:
                section.append(f'  • {u}')
            sections.append('\n'.join(section))

        # ── Decisions made ────────────────────────────────────────────────
        decisions = self._get_todays_decisions()
        if decisions:
            section = ['**Decisions made:**']
            for d in decisions:
                section.append(f'  • {d}')
            sections.append('\n'.join(section))

        if not sections:
            body = 'No activity logged today.'
        else:
            body = '\n\n'.join(sections)

        return (
            f'━━━━━━━━━━━━━━━━━━━━━━━━\n'
            f'📋 **EOD Closing Loop — {today_str}**\n'
            f'━━━━━━━━━━━━━━━━━━━━━━━━\n'
            f'\n'
            f'{body}\n'
            f'\n'
            f'━━━━━━━━━━━━━━━━━━━━━━━━\n'
            f'— DEX'
        )

    def _get_todays_meetings(self) -> list[str]:
        try:
            from eos_ai.gws_connector import GWSConnector
            gws    = GWSConnector()
            events = gws.get_today_events()
            result = []
            for e in events[:8]:
                title = e.get('title', 'Untitled')
                start = e.get('start', '')
                if start and 'T' in str(start):
                    try:
                        dt    = datetime.fromisoformat(str(start).replace('Z', '+00:00'))
                        label = dt.strftime('%I:%M%p').lstrip('0')
                    except Exception:
                        label = str(start)[11:16]
                else:
                    label = str(start)[:10]
                result.append(f'{label} — {title}')
            return result
        except Exception as e:
            print(f'[EOD] Meetings: {e}')
            return []

    def _get_todays_purchases(self) -> list[str]:
        """Pull receipts/financials from GPS RECEIPTS label for today."""
        try:
            from eos_ai.gws_connector import GWSConnector
            gws      = GWSConnector()
            label_id = gws.get_or_create_label('Receipts-Financials')
            if not label_id:
                return []

            today_start = datetime.now(timezone.utc).replace(
                hour=0, minute=0, second=0, microsecond=0
            )
            msgs   = gws.get_messages_by_label(label_id, max_results=50)
            result = []

            for msg_ref in msgs[:20]:
                detail = gws._run(
                    'gmail', 'users', 'messages', 'get',
                    params={
                        'userId':          'me',
                        'id':              msg_ref['id'],
                        'format':          'metadata',
                        'metadataHeaders': ['Subject', 'Date'],
                    },
                )
                if not detail:
                    continue
                hdrs = {
                    h['name']: h['value']
                    for h in detail.get('payload', {}).get('headers', [])
                }
                date_str = hdrs.get('Date', '')
                subject  = hdrs.get('Subject', '')
                # Only include emails from today
                if date_str:
                    try:
                        from email.utils import parsedate_to_datetime
                        msg_dt = parsedate_to_datetime(date_str)
                        if msg_dt.astimezone(timezone.utc) >= today_start:
                            result.append(subject[:60])
                    except Exception:
                        pass  # Can't parse date — skip
            return result
        except Exception as e:
            print(f'[EOD] Purchases: {e}')
            return []

    def _get_todays_project_updates(self) -> list[str]:
        try:
            from eos_ai.db import get_conn
            since = (datetime.now(timezone.utc) - timedelta(hours=12)).isoformat()
            with get_conn(self.ctx.org_id) as cur:
                cur.execute('''
                    SELECT event_type, payload_json
                    FROM events
                    WHERE org_id = %s
                      AND event_type IN (
                        'pipeline_entry', 'icp_signal',
                        'lead_qualified', 'email_classified'
                      )
                      AND created_at > %s
                    ORDER BY created_at DESC
                    LIMIT 10
                ''', (self.ctx.org_id, since))
                rows = cur.fetchall()

            result = []
            email_count = 0
            for event_type, data in rows:
                if isinstance(data, str):
                    data = json.loads(data)
                if event_type == 'email_classified':
                    email_count += 1
                elif event_type == 'pipeline_entry':
                    name  = data.get('name', '')
                    stage = data.get('stage', '')
                    if name:
                        result.append(f'Pipeline: {name} → {stage}')
                elif event_type in ('icp_signal', 'lead_qualified'):
                    name  = data.get('name', '') or data.get('handle', '')
                    score = data.get('score', '')
                    if name:
                        result.append(f'Lead: {name} ({score}/10)' if score else f'Lead: {name}')

            if email_count:
                result.insert(0, f'Email GPS: {email_count} emails processed')
            return result
        except Exception as e:
            print(f'[EOD] Project updates: {e}')
            return []

    def _get_todays_decisions(self) -> list[str]:
        """Decisions = dex_question events answered today."""
        try:
            from eos_ai.db import get_conn
            since = (datetime.now(timezone.utc) - timedelta(hours=12)).isoformat()
            with get_conn(self.ctx.org_id) as cur:
                cur.execute('''
                    SELECT payload_json
                    FROM events
                    WHERE org_id = %s
                      AND event_type = 'dex_question'
                      AND payload_json->>'answered' = 'true'
                      AND created_at > %s
                    ORDER BY created_at DESC
                    LIMIT 5
                ''', (self.ctx.org_id, since))
                rows = cur.fetchall()

            result = []
            for row in rows:
                data = row[0]
                if isinstance(data, str):
                    data = json.loads(data)
                q = data.get('question', '')
                a = data.get('answer', '')
                if q:
                    result.append(
                        f'{q[:50]} → {a[:30]}' if a else q[:70]
                    )
            return result
        except Exception as e:
            print(f'[EOD] Decisions: {e}')
            return []
