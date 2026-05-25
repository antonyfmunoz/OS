"""Follow-up workflow — automated follow-up on stale conversations.

Trigger: lead hasn't responded in N days
Steps: check_status → decide_approach → draft_followup → queue
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Any


@dataclass
class FollowUpAction:
    lead_id: str = ""
    days_stale: int = 0
    approach: str = ""
    message: str = ""
    priority: str = "normal"


class FollowUpWorkflow:
    """Automated follow-up workflow for stale leads."""

    def __init__(self, org_id: str = "") -> None:
        self._org_id = org_id

    def check_stale_leads(self, stale_after_days: int = 3) -> list[FollowUpAction]:
        """Find leads that need follow-up and generate actions."""
        stale = self._fetch_stale(stale_after_days)
        actions = []
        for lead in stale:
            days = lead.get("days_since_contact", 0)
            approach = self._decide_approach(days)
            message = self._draft_followup(lead, approach)
            actions.append(
                FollowUpAction(
                    lead_id=lead.get("id", ""),
                    days_stale=days,
                    approach=approach,
                    message=message,
                    priority="high" if days > 7 else "normal",
                )
            )
        return actions

    def _decide_approach(self, days_stale: int) -> str:
        if days_stale <= 3:
            return "gentle_nudge"
        elif days_stale <= 7:
            return "value_add"
        elif days_stale <= 14:
            return "direct_ask"
        return "final_attempt"

    def _draft_followup(self, lead: dict[str, Any], approach: str) -> str:
        name = lead.get("name", "there")
        templates = {
            "gentle_nudge": f"Hey {name} — just following up. No rush, just wanted to keep the conversation going.",
            "value_add": f"Hey {name} — thought of you when I saw this. [relevant resource]. Lmk if you want to chat.",
            "direct_ask": f"Hey {name} — I know you're busy. Quick question: is now a good time to explore this, or should I circle back later?",
            "final_attempt": f"Hey {name} — last check-in from me. If the timing isn't right, no worries at all. The door's open whenever.",
        }
        return templates.get(approach, templates["gentle_nudge"])

    def _fetch_stale(self, stale_after_days: int) -> list[dict[str, Any]]:
        try:
            from substrate import get_conn
            import json

            cutoff = (datetime.now(timezone.utc) - timedelta(days=stale_after_days)).isoformat()
            with get_conn(self._org_id) as cur:
                cur.execute(
                    """
                    SELECT payload_json, created_at FROM events
                    WHERE org_id = %s AND event_type = 'crm_lead'
                    AND payload_json->>'stage' IN ('contacted', 'qualified')
                    AND payload_json->>'last_contact' < %s
                    ORDER BY created_at DESC LIMIT 50
                    """,
                    (self._org_id, cutoff),
                )
                rows = cur.fetchall()
                results = []
                for r in rows:
                    payload = r["payload_json"]
                    if isinstance(payload, str):
                        payload = json.loads(payload)
                    results.append(payload)
                return results
        except Exception:
            return []
