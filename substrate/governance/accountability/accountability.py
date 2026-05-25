"""
AccountabilityEngine — holds the founder to their word.

When a founder commits to something ("I'll send 20 DMs today"),
this engine logs it and schedules a follow-up. The proactive engine
fires that follow-up at the right time through Telegram or Discord.

DEX is a mentor, not a nag. Follow-ups are asked once, with respect.
The founder's sovereignty is always preserved — the system never judges,
it simply asks what happened.

Usage:
    from substrate.governance.accountability.accountability import AccountabilityEngine
    ae = AccountabilityEngine(ctx)
    commitment = ae.detect_commitment('I will send 20 DMs today', 'lyfe_institute')
    pending = ae.get_pending_follow_ups()
"""

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta


@dataclass
class Commitment:
    id: str
    text: str  # what was committed to
    venture_id: str
    committed_at: datetime
    due_at: datetime  # when to follow up
    fulfilled: bool = None
    follow_up_sent: bool = False


class AccountabilityEngine:
    def __init__(self, ctx):
        self.ctx = ctx

    COMMITMENT_SIGNALS = [
        "i will",
        "i'll",
        "going to",
        "i'm going to",
        "planning to",
        "today i'll",
        "i'm going to send",
        "i'll send",
        "i'll do",
        "gonna",
        "i'm gonna",
        "committing to",
        "promise",
        "20 dms",
        "send dms today",
        "reach out today",
        "follow up today",
    ]

    def detect_commitment(
        self,
        text: str,
        venture_id: str = "",
    ) -> Commitment | None:
        """
        Detect if the text contains a commitment signal.
        If yes, log it and return the Commitment object.
        If no, return None.
        """
        text_lower = text.lower()
        if not any(s in text_lower for s in self.COMMITMENT_SIGNALS):
            return None

        now = datetime.now()

        # Default: follow up next morning at 9am
        due_at = now.replace(hour=9, minute=0, second=0, microsecond=0) + timedelta(days=1)

        # If commitment is for today — follow up this evening
        if any(
            t in text_lower
            for t in [
                "today",
                "right now",
                "tonight",
                "this morning",
                "this afternoon",
            ]
        ):
            due_at = now.replace(hour=20, minute=0, second=0, microsecond=0)
            if due_at < now:
                due_at = now + timedelta(hours=8)

        commitment = Commitment(
            id=str(uuid.uuid4())[:8],
            text=text[:300],
            venture_id=venture_id,
            committed_at=now,
            due_at=due_at,
        )
        self._save_commitment(commitment)
        print(f"[Accountability] Commitment logged: {text[:60]}")
        return commitment

    def _save_commitment(self, commitment: Commitment) -> None:
        try:
            from substrate.state.memory.memory import AgentMemory

            AgentMemory().log_event(
                org_id=self.ctx.org_id,
                event_type="commitment",
                payload={
                    "commitment_id": commitment.id,
                    "text": commitment.text,
                    "venture_id": commitment.venture_id,
                    "due_at": commitment.due_at.isoformat(),
                    "fulfilled": None,
                    "follow_up_sent": False,
                },
            )
        except Exception as e:
            print(f"[Accountability] Save: {e}")

    def get_pending_follow_ups(self) -> list[dict]:
        """
        Return commitments that are due for follow-up and haven't been
        followed up yet.
        """
        try:
            from substrate.state.storage.db import get_conn

            now = datetime.now().isoformat()
            with get_conn(self.ctx.org_id) as cur:
                cur.execute(
                    """
                    SELECT id, payload_json
                    FROM events
                    WHERE org_id = %s
                    AND event_type = 'commitment'
                    AND payload_json->>'fulfilled' = 'null'
                    AND payload_json->>'follow_up_sent' = 'false'
                    AND payload_json->>'due_at' < %s
                    ORDER BY created_at ASC
                    LIMIT 5
                    """,
                    (self.ctx.org_id, now),
                )
                rows = cur.fetchall()
                results = []
                for row in rows:
                    payload = row["payload_json"]
                    if isinstance(payload, str):
                        payload = json.loads(payload)
                    results.append(
                        {
                            "event_id": str(row["id"]),
                            **payload,
                        }
                    )
                return results
        except Exception as e:
            print(f"[Accountability] Follow-ups: {e}")
            return []

    def generate_follow_up_message(self, commitment: dict) -> str:
        text = commitment.get("text", "")
        return (
            f'Earlier you said: "{text[:100]}"\n\nDid you follow through?\nTell me what happened.'
        )

    def mark_follow_up_sent(self, event_id: str) -> None:
        try:
            from substrate.state.memory.memory import AgentMemory

            AgentMemory().merge_event_payload(
                org_id=str(self.ctx.org_id),
                event_id=event_id,
                updates={"follow_up_sent": True},
            )
        except Exception as e:
            print(f"[Accountability] Mark sent: {e}")

    def record_fulfillment(self, event_id: str, fulfilled: bool, notes: str = "") -> dict:
        """Record whether a commitment was fulfilled."""
        try:
            from substrate.state.memory.memory import AgentMemory

            AgentMemory().merge_event_payload(
                org_id=str(self.ctx.org_id),
                event_id=event_id,
                updates={
                    "fulfilled": fulfilled,
                    "fulfillment_notes": notes[:500],
                    "resolved_at": datetime.now().isoformat(),
                },
            )
            return {"recorded": True, "fulfilled": fulfilled}
        except Exception as e:
            print(f"[Accountability] Record fulfillment: {e}")
            return {"recorded": False, "error": str(e)}

    def get_fulfillment_rate(self, days: int = 30) -> dict:
        """Calculate commitment fulfillment rate over N days."""
        try:
            from substrate.state.storage.db import get_conn

            cutoff = (datetime.now() - timedelta(days=days)).isoformat()
            with get_conn(self.ctx.org_id) as cur:
                cur.execute(
                    """
                    SELECT
                        COUNT(*) FILTER (WHERE payload_json->>'fulfilled' = 'true') AS fulfilled,
                        COUNT(*) FILTER (WHERE payload_json->>'fulfilled' = 'false') AS missed,
                        COUNT(*) FILTER (WHERE payload_json->>'fulfilled' = 'null') AS pending,
                        COUNT(*) AS total
                    FROM events
                    WHERE org_id = %s
                    AND event_type = 'commitment'
                    AND created_at >= %s
                    """,
                    (self.ctx.org_id, cutoff),
                )
                row = cur.fetchone()
                total = row["total"] or 0
                fulfilled = row["fulfilled"] or 0
                missed = row["missed"] or 0
                pending = row["pending"] or 0
                rate = fulfilled / max(fulfilled + missed, 1)
                return {
                    "period_days": days,
                    "total": total,
                    "fulfilled": fulfilled,
                    "missed": missed,
                    "pending": pending,
                    "fulfillment_rate": round(rate, 3),
                }
        except Exception as e:
            print(f"[Accountability] Fulfillment rate: {e}")
            return {"fulfillment_rate": 0.0, "error": str(e)}

    def get_streak(self) -> dict:
        """Get current fulfillment streak (consecutive days with commitments met)."""
        try:
            from substrate.state.storage.db import get_conn

            with get_conn(self.ctx.org_id) as cur:
                cur.execute(
                    """
                    SELECT
                        payload_json->>'fulfilled' AS fulfilled,
                        DATE(created_at) AS day
                    FROM events
                    WHERE org_id = %s
                    AND event_type = 'commitment'
                    AND payload_json->>'fulfilled' IS NOT NULL
                    ORDER BY created_at DESC
                    LIMIT 90
                    """,
                    (self.ctx.org_id,),
                )
                rows = cur.fetchall()

            streak = 0
            for row in rows:
                if row["fulfilled"] == "true":
                    streak += 1
                else:
                    break

            return {"current_streak": streak, "based_on": len(rows)}
        except Exception as e:
            print(f"[Accountability] Streak: {e}")
            return {"current_streak": 0, "error": str(e)}

    def audit_trail(self, limit: int = 10) -> list[dict]:
        """Get recent accountability events for transparency."""
        try:
            from substrate.state.storage.db import get_conn

            with get_conn(self.ctx.org_id) as cur:
                cur.execute(
                    """
                    SELECT id, payload_json, created_at
                    FROM events
                    WHERE org_id = %s
                    AND event_type = 'commitment'
                    ORDER BY created_at DESC
                    LIMIT %s
                    """,
                    (self.ctx.org_id, limit),
                )
                rows = cur.fetchall()
                results = []
                for row in rows:
                    payload = row["payload_json"]
                    if isinstance(payload, str):
                        payload = json.loads(payload)
                    results.append(
                        {
                            "event_id": str(row["id"]),
                            "created_at": str(row["created_at"]),
                            **payload,
                        }
                    )
                return results
        except Exception as e:
            print(f"[Accountability] Audit: {e}")
            return []

    def stats(self) -> dict:
        """Full accountability status including rate, streak, and pending."""
        rate = self.get_fulfillment_rate()
        streak = self.get_streak()
        pending = self.get_pending_follow_ups()
        return {
            "fulfillment_rate": rate.get("fulfillment_rate", 0.0),
            "current_streak": streak.get("current_streak", 0),
            "pending_follow_ups": len(pending),
            "period_stats": rate,
        }
