"""
OnboardingBackfill — reads all connected integrations on first connect and
builds a complete knowledge base before the first interaction.

When a user connects their Google Workspace, this runs automatically and
populates: Drive docs, Gmail contacts, Calendar patterns, Google Tasks,
CRM lead profiles, and a synthesized business intelligence summary.

Usage:
    from runtime.context import load_context_from_env
    from runtime.onboarding_backfill import OnboardingBackfill

    ctx = load_context_from_env()
    ob  = OnboardingBackfill(ctx)
    results = ob.run_full_backfill('lyfe_institute')
    print(ob.get_backfill_status())
"""

import re
from datetime import datetime, timezone, timedelta

from runtime.context import EOSContext
from runtime.gws_connector import GWSConnector
from control_plane.runtime.cognitive_loop import CognitiveLoop
from runtime.human_intelligence import HumanIntelligenceEngine
from runtime.knowledge_graph import KnowledgeGraph
from runtime.embedding_engine import EmbeddingEngine


class OnboardingBackfill:

    def __init__(self, ctx: EOSContext) -> None:
        self.ctx     = ctx
        self.gws     = GWSConnector()
        self.loop    = CognitiveLoop(ctx)
        self.hie     = HumanIntelligenceEngine(ctx)
        self.kg      = KnowledgeGraph(ctx)
        self.ee      = EmbeddingEngine()
        self.results: dict = {}

    # ─── Orchestrator ─────────────────────────────────────────────────────────

    def run_full_backfill(self, venture_id: str) -> dict:
        """
        Run all backfill sources in sequence.
        Returns summary dict of what was found across all sources.
        """
        print("[Backfill] Starting full backfill...")
        self.results = {}

        self._backfill_drive(venture_id)
        self._backfill_gmail(venture_id)
        self._backfill_calendar(venture_id)
        self._backfill_tasks()
        self._backfill_crm(venture_id)
        self._build_knowledge_base(venture_id)

        print(f"[Backfill] Complete — {self.results}")
        return self.results

    # ─── Drive ────────────────────────────────────────────────────────────────

    def _backfill_drive(self, venture_id: str) -> None:
        """Read Google Drive docs and store as events for future retrieval."""
        docs = self.gws.search_drive(
            query="mimeType='application/vnd.google-apps.document'",
            max_results=20,
        )

        skip_terms = ["untitled", "copy of", "template", ".jpg", ".png"]
        processed = 0

        for doc in docs:
            name    = doc.get("name", "")
            file_id = doc.get("id", "")

            if any(t in name.lower() for t in skip_terms):
                continue

            content = self.gws.read_document(file_id)
            if not content or len(content) < 100:
                continue

            from runtime.memory import AgentMemory
            mem = AgentMemory()
            mem.log_event(
                org_id=self.ctx.org_id,
                event_type="backfill_drive_doc",
                payload={
                    "doc_name":        name,
                    "file_id":         file_id,
                    "content_preview": content[:500],
                    "venture_id":      venture_id,
                    "source":          "google_drive",
                },
            )

            # Link the doc to this venture in the knowledge graph
            try:
                self.kg.link_entities(
                    from_type="drive_doc",
                    from_id=file_id,
                    to_type="venture",
                    to_id=venture_id,
                    relationship="venture_document",
                    metadata={"name": name},
                )
            except Exception:
                pass

            processed += 1

        self.results["drive_docs"] = processed
        print(f"[Backfill] Drive: {processed} docs processed")

    # ─── Gmail ────────────────────────────────────────────────────────────────

    def _backfill_gmail(self, venture_id: str) -> None:
        """Extract email contacts and link them to the venture graph."""
        emails = self.gws.get_recent_emails(max_results=50)

        skip_domains = [
            "noreply", "no-reply", "donotreply", "notifications",
            "support", "mailer", "bounce",
        ]

        contacts_found = 0
        seen: set[str] = set()

        for email in emails:
            sender  = email.get("from", "")
            subject = email.get("subject", "")
            snippet = email.get("snippet", "")

            match = re.search(r"[\w.\-+]+@[\w.\-]+", sender)
            if not match:
                continue

            email_addr = match.group().lower()

            if any(x in email_addr for x in skip_domains):
                continue
            if email_addr in seen:
                continue
            seen.add(email_addr)

            try:
                self.kg.link_entities(
                    from_type="email_contact",
                    from_id=email_addr,
                    to_type="venture",
                    to_id=venture_id,
                    relationship="email_contact",
                    metadata={
                        "subject": subject[:100],
                        "snippet": snippet[:200],
                    },
                )
            except Exception:
                pass

            contacts_found += 1

        self.results["gmail_contacts"] = contacts_found
        print(f"[Backfill] Gmail: {contacts_found} contacts linked")

    # ─── Calendar ─────────────────────────────────────────────────────────────

    def _backfill_calendar(self, venture_id: str) -> None:
        """Read 90 days of calendar events and store time/contact patterns."""
        now       = datetime.now(timezone.utc)
        start_90d = (now - timedelta(days=90)).isoformat()

        data = self.gws._run(
            "calendar", "events", "list",
            params={
                "calendarId":   "primary",
                "timeMin":      start_90d,
                "timeMax":      now.isoformat(),
                "maxResults":   100,
                "singleEvents": True,
                "orderBy":      "startTime",
            },
        )

        events: list = data.get("items", []) if data else []

        recurring: dict[str, int] = {}
        contacts:  set[str]       = set()

        for e in events:
            title     = e.get("summary", "")
            attendees = e.get("attendees", [])
            for a in attendees:
                email = a.get("email", "")
                if email and "google" not in email:
                    contacts.add(email)
            if e.get("recurringEventId"):
                recurring[title] = recurring.get(title, 0) + 1

        if events:
            try:
                from runtime.os_trinity import OSTrinity
                trinity = OSTrinity(self.ctx)
                trinity.update_intelligence_profile(
                    self.ctx.user_id,
                    {
                        "peak_performance_windows": [{
                            "source":             "calendar_backfill",
                            "recurring_meetings": list(recurring.items())[:10],
                            "unique_contacts":    len(contacts),
                        }],
                    },
                )
            except Exception as e:
                print(f"[Backfill] Calendar profile update skipped: {e}")

        self.results["calendar_events"]   = len(events)
        self.results["calendar_contacts"] = len(contacts)
        print(
            f"[Backfill] Calendar: {len(events)} events, "
            f"{len(contacts)} contacts"
        )

    # ─── Tasks ────────────────────────────────────────────────────────────────

    def _backfill_tasks(self) -> None:
        """Import existing Google Tasks into the Neon tasks table."""
        tasks    = self.gws.get_tasks()
        imported = 0

        for task in tasks:
            title = task.get("title", "").strip()
            if not title:
                continue
            try:
                from runtime.coordination_engine import CoordinationEngine
                ce = CoordinationEngine(self.ctx)
                ce.assign_task(
                    task_description=title,
                    assignee_type="human",
                    assignee_id=self.ctx.user_id,
                    priority="normal",
                    due_by=task.get("due") or None,
                )
                imported += 1
            except Exception as e:
                print(f"[Backfill] Task import failed for '{title}': {e}")

        self.results["tasks_imported"] = imported
        print(f"[Backfill] Tasks: {imported} imported")

    # ─── CRM ─────────────────────────────────────────────────────────────────

    def _backfill_crm(self, venture_id: str) -> None:
        """Profile all CRM leads — builds human_profiles in Neon."""
        result = self.hie.profile_all_crm_leads()
        self.results["crm_leads"] = result.get("leads_processed", 0)
        print(f"[Backfill] CRM: {self.results['crm_leads']} leads processed")

    # ─── Knowledge synthesis ─────────────────────────────────────────────────

    def _build_knowledge_base(self, venture_id: str) -> None:
        """
        Synthesize all gathered data into a structured business intelligence
        summary. Stored as an event and logged for future retrieval.
        """
        from runtime.agent_runtime import TaskType

        summary_prompt = (
            f"Based on the following sources that were just analyzed for "
            f"venture '{venture_id}':\n"
            f"- {self.results.get('drive_docs', 0)} Google Drive documents\n"
            f"- {self.results.get('gmail_contacts', 0)} email contacts\n"
            f"- {self.results.get('calendar_events', 0)} calendar events "
            f"({self.results.get('calendar_contacts', 0)} unique contacts)\n"
            f"- {self.results.get('crm_leads', 0)} CRM leads\n\n"
            f"Generate a concise business intelligence summary covering:\n"
            f"1. What this business appears to do based on its activity\n"
            f"2. Who the key contacts and relationships are\n"
            f"3. What the operational patterns look like\n"
            f"4. What opportunities or gaps are visible from the data\n"
            f"5. Recommended first actions for the AI to take immediately"
        )

        try:
            result = self.loop.run(
                input=summary_prompt,
                agent="research_agent",
                task_type=TaskType.ANALYZE,
                venture_id=venture_id,
            )
            knowledge_summary = (result.output or "")[:1000]
        except Exception as e:
            print(f"[Backfill] Knowledge synthesis failed: {e}")
            knowledge_summary = ""

        from runtime.memory import AgentMemory
        mem = AgentMemory()
        try:
            mem.log_event(
                org_id=self.ctx.org_id,
                event_type="onboarding_backfill_complete",
                payload={
                    "venture_id":        venture_id,
                    "sources":           self.results,
                    "knowledge_summary": knowledge_summary,
                },
            )
        except Exception as e:
            print(f"[Backfill] Event log failed: {e}")

        self.results["knowledge_summary"] = knowledge_summary[:300]
        print(f"[Backfill] Knowledge base built ({len(knowledge_summary)} chars)")

    # ─── Status ───────────────────────────────────────────────────────────────

    def get_backfill_status(self) -> str:
        """Return a Telegram-ready status summary."""
        lines = ["Onboarding Backfill Status\n"]
        items = [
            ("drive_docs",         "Drive docs"),
            ("gmail_contacts",     "Gmail contacts"),
            ("calendar_events",    "Calendar events"),
            ("calendar_contacts",  "Cal contacts"),
            ("crm_leads",          "CRM leads"),
            ("tasks_imported",     "Tasks imported"),
        ]
        for key, label in items:
            val = self.results.get(key, 0)
            lines.append(f"  {label}: {val}")

        if self.results.get("knowledge_summary"):
            lines.append(
                f"\nSummary:\n{self.results['knowledge_summary']}"
            )

        return "\n".join(lines)
