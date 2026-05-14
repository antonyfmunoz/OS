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
  load_dotenv(os.path.join(os.environ.get('UMH_ROOT') or os.environ.get('OS_ROOT') or os.environ.get('EOS_ROOT') or '/opt/OS', 'runtime', '.env'))
  load_dotenv(os.path.join(os.environ.get('UMH_ROOT') or os.environ.get('OS_ROOT') or os.environ.get('EOS_ROOT') or '/opt/OS', 'services', '.env'))
  from runtime.eod_closing_loop import EODClosingLoop
  from runtime.context import load_context_from_env
  from runtime.discord_utils import post_to_webhook
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
        today_str = date.today().strftime("%A, %B %d")
        sections = []

        # ── Meetings today ────────────────────────────────────────────────
        meetings = self._get_todays_meetings()
        if meetings:
            section = ["**Meetings today:**"]
            for m in meetings:
                section.append(f"  • {m}")
            sections.append("\n".join(section))

        # ── Purchases / expenses ──────────────────────────────────────────
        purchases = self._get_todays_purchases()
        if purchases:
            section = ["**Purchases/expenses:**"]
            for p in purchases:
                section.append(f"  • {p}")
            sections.append("\n".join(section))

        # ── Overdue invoice check ─────────────────────────────────────────
        try:
            from state.finance.expense_tracker import get_overdue_invoices

            overdue = get_overdue_invoices()
            if overdue:
                section = [f"**🔴 Overdue invoices ({len(overdue)}):**"]
                for inv in overdue[:3]:
                    section.append(
                        f"  • {inv['invoice_id']} — "
                        f"{inv['client_name']} — "
                        f"${inv['total']:,.2f}"
                    )
                sections.append("\n".join(section))
        except Exception:
            pass

        # ── Project updates ───────────────────────────────────────────────
        updates = self._get_todays_project_updates()
        if updates:
            section = ["**Project updates:**"]
            for u in updates:
                section.append(f"  • {u}")
            sections.append("\n".join(section))

        # ── Decisions made ────────────────────────────────────────────────
        decisions = self._get_todays_decisions()
        if decisions:
            section = ["**Decisions made:**"]
            for d in decisions:
                section.append(f"  • {d}")
            sections.append("\n".join(section))

        # Next day preview
        try:
            from adapters.google_workspace.gws_connector import GWSConnector
            from datetime import timedelta
            from zoneinfo import ZoneInfo
            from dateutil.parser import parse as _parse

            PDT = ZoneInfo("America/Los_Angeles")
            gws_nd = GWSConnector()
            tomorrow_str = (datetime.now(PDT) + timedelta(days=1)).strftime("%Y-%m-%d")
            tomorrow_events = []
            for e in gws_nd.get_upcoming_events(days=2):
                start = e.get("start", "")
                if isinstance(start, dict):
                    start = start.get("dateTime", "")
                try:
                    dt = _parse(str(start)).astimezone(PDT)
                    if dt.date().isoformat() == tomorrow_str:
                        tomorrow_events.append(
                            f"• {dt.strftime('%-I:%M %p')} — "
                            f"{e.get('title', e.get('summary', 'Event'))}"
                        )
                except Exception:
                    pass
            if tomorrow_events:
                sections.append("**📅 Tomorrow:**")
                sections.extend(tomorrow_events[:4])
                sections.append("")
        except Exception:
            pass

        if not sections:
            body = "No activity logged today."
        else:
            body = "\n\n".join(sections)

        return (
            f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📋 **EOD Closing Loop — {today_str}**\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"\n"
            f"{body}\n"
            f"\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"— DEX"
        )

    def run_and_publish(self) -> str:
        """
        Run EOD closing loop, write to Notion, post link to Discord.
        Returns Notion URL or '' on failure.
        """
        import os

        report = self.run()

        # Write to Notion
        notion_url = ""
        try:
            from adapters.notion.notion_publisher import get_publisher

            publisher = get_publisher(self.ctx)
            notion_url = publisher.publish_eod_sync(
                content={
                    "completed": report,
                }
            )
            if notion_url:
                print(f"[EOD] Written to Notion: {notion_url}")
        except Exception as e:
            print(f"[EOD] Notion publish failed: {e}")

        # Post to Discord
        try:
            from runtime.discord_utils import post_to_webhook

            webhook = os.getenv("DISCORD_BRIEF_WEBHOOK", "")
            if webhook:
                if notion_url:
                    post_to_webhook(
                        f"📋 **EOD Sync ready**\n{notion_url}",
                        webhook_url=webhook,
                    )
                else:
                    post_to_webhook(report, webhook_url=webhook)
        except Exception as e:
            print(f"[EOD] Discord post failed: {e}")

        return notion_url

    def _get_todays_meetings(self) -> list[str]:
        try:
            from adapters.google_workspace.gws_connector import GWSConnector

            gws = GWSConnector()
            events = gws.get_today_events()
            result = []
            for e in events[:8]:
                title = e.get("title", "Untitled")
                start = e.get("start", "")
                if start and "T" in str(start):
                    try:
                        dt = datetime.fromisoformat(str(start).replace("Z", "+00:00"))
                        label = dt.strftime("%I:%M%p").lstrip("0")
                    except Exception:
                        label = str(start)[11:16]
                else:
                    label = str(start)[:10]
                result.append(f"{label} — {title}")
            return result
        except Exception as e:
            print(f"[EOD] Meetings: {e}")
            return []

    def _get_todays_purchases(self) -> list[str]:
        """Pull receipts/financials from GPS RECEIPTS label for today."""
        try:
            from adapters.google_workspace.gws_connector import GWSConnector

            gws = GWSConnector()
            label_id = gws.get_or_create_label("Receipts-Financials")
            if not label_id:
                return []

            today_start = datetime.now(timezone.utc).replace(
                hour=0, minute=0, second=0, microsecond=0
            )
            msgs = gws.get_messages_by_label(label_id, max_results=50)
            result = []

            for msg_ref in msgs[:20]:
                detail = gws._run(
                    "gmail",
                    "users",
                    "messages",
                    "get",
                    params={
                        "userId": "me",
                        "id": msg_ref["id"],
                        "format": "metadata",
                        "metadataHeaders": ["Subject", "Date"],
                    },
                )
                if not detail:
                    continue
                hdrs = {
                    h["name"]: h["value"]
                    for h in detail.get("payload", {}).get("headers", [])
                }
                date_str = hdrs.get("Date", "")
                subject = hdrs.get("Subject", "")
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
            print(f"[EOD] Purchases: {e}")
            return []

    def _get_todays_project_updates(self) -> list[str]:
        try:
            from state.storage.db import get_conn

            since = (datetime.now(timezone.utc) - timedelta(hours=12)).isoformat()
            with get_conn(self.ctx.org_id) as cur:
                cur.execute(
                    """
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
                """,
                    (self.ctx.org_id, since),
                )
                rows = cur.fetchall()

            result = []
            email_count = 0
            for event_type, data in rows:
                if isinstance(data, str):
                    data = json.loads(data)
                if event_type == "email_classified":
                    email_count += 1
                elif event_type == "pipeline_entry":
                    name = data.get("name", "")
                    stage = data.get("stage", "")
                    if name:
                        result.append(f"Pipeline: {name} → {stage}")
                elif event_type in ("icp_signal", "lead_qualified"):
                    name = data.get("name", "") or data.get("handle", "")
                    score = data.get("score", "")
                    if name:
                        result.append(
                            f"Lead: {name} ({score}/10)" if score else f"Lead: {name}"
                        )

            if email_count:
                result.insert(0, f"Email GPS: {email_count} emails processed")
            return result
        except Exception as e:
            print(f"[EOD] Project updates: {e}")
            return []

    def _get_todays_decisions(self) -> list[str]:
        """Decisions = dex_question events answered today."""
        try:
            from state.storage.db import get_conn

            since = (datetime.now(timezone.utc) - timedelta(hours=12)).isoformat()
            with get_conn(self.ctx.org_id) as cur:
                cur.execute(
                    """
                    SELECT payload_json
                    FROM events
                    WHERE org_id = %s
                      AND event_type = 'dex_question'
                      AND payload_json->>'answered' = 'true'
                      AND created_at > %s
                    ORDER BY created_at DESC
                    LIMIT 5
                """,
                    (self.ctx.org_id, since),
                )
                rows = cur.fetchall()

            result = []
            for row in rows:
                data = row[0]
                if isinstance(data, str):
                    data = json.loads(data)
                q = data.get("question", "")
                a = data.get("answer", "")
                if q:
                    result.append(f"{q[:50]} → {a[:30]}" if a else q[:70])
            return result
        except Exception as e:
            print(f"[EOD] Decisions: {e}")
            return []
