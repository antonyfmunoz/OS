"""
FeedbackLoop — closes the loop between DEX recommendations and real outcomes.

Every piece of advice DEX gives is logged. When the founder reports back
what happened, the outcome is captured and tied to the recommendation.
Over time this builds a signal of what actually works vs. what doesn't.

Usage:
    from eos_ai.feedback_loop import FeedbackLoop
    fl = FeedbackLoop(ctx)
    rec_id = fl.log_recommendation('Send 20 DMs today', 'lyfe_institute', 'asked for focus')
    fl.log_outcome('I sent the DMs, got 3 replies', 'lyfe_institute')
    stats = fl.get_recommendation_stats()
"""

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class OutcomeType(Enum):
    SUCCESS = "success"
    FAILURE = "failure"
    PARTIAL = "partial"
    PENDING = "pending"
    SKIPPED = "skipped"


@dataclass
class Recommendation:
    id: str
    content: str  # what DEX recommended
    venture_id: str
    context: str  # what triggered it
    created_at: datetime = field(default_factory=datetime.now)
    outcome: OutcomeType = OutcomeType.PENDING
    outcome_note: str = ""
    outcome_at: datetime = None
    followed: bool = None  # did founder act?


class FeedbackLoop:
    def __init__(self, ctx):
        self.ctx = ctx

    def log_recommendation(
        self,
        content: str,
        venture_id: str,
        context: str = "",
    ) -> str:
        """
        Log actionable DEX recommendation to Neon.
        Filters out agent data dumps, stage checks, and research outputs.
        Returns recommendation ID, or '' if filtered out.
        """
        if not self._is_actionable_advice(content, context):
            return ""

        rec_id = str(uuid.uuid4())[:8]
        try:
            from eos_ai.db import get_conn

            with get_conn(self.ctx.org_id) as cur:
                cur.execute(
                    """
                    INSERT INTO events (
                        id, org_id, event_type,
                        payload_json, created_at)
                    VALUES (%s, %s, %s, %s, NOW())
                    """,
                    (
                        str(uuid.uuid4()),
                        self.ctx.org_id,
                        "recommendation",
                        json.dumps(
                            {
                                "rec_id": rec_id,
                                "content": content[:500],
                                "venture_id": venture_id,
                                "context": context[:200],
                                "outcome": "pending",
                                "followed": None,
                            }
                        ),
                    ),
                )
            print(f"[FeedbackLoop] Logged rec: {rec_id}")
        except Exception as e:
            print(f"[FeedbackLoop] Log failed: {e}")
        return rec_id

    def _is_actionable_advice(self, content: str, context: str) -> bool:
        """
        Returns True only if this is specific actionable advice to the founder.
        Filters out agent data dumps, stage checks, research outputs.
        """
        # Fast keyword filter — skip obvious non-advice
        skip_prefixes = [
            "acknowledged",
            "⚠️ stage check",
            "## research agent",
            "## confidentiality",
        ]
        content_lower = content[:200].lower().strip()
        for prefix in skip_prefixes:
            if content_lower.startswith(prefix):
                return False

        # LLM classification for ambiguous cases
        try:
            from eos_ai.model_router import call_with_fallback, TaskType

            result = call_with_fallback(
                prompt=(
                    "Is this specific actionable advice to a founder? "
                    "Answer only YES or NO.\n\n"
                    f"Content: {content[:300]}"
                ),
                task_type=TaskType.CLASSIFY,
            )
            return "YES" in result.output.upper()
        except Exception:
            # Default to True if classifier fails
            return True

    def log_outcome(
        self,
        text: str,
        venture_id: str = "",
    ) -> bool:
        """
        Detect outcome signals in founder's text and update
        the most recent pending recommendation.
        Uses LLM classifier first, falls back to keywords.
        """
        pending = self._get_pending_recs()
        if not pending:
            return False

        # Try semantic classification first
        outcome = self._classify_outcome_semantic(text)

        # Fall back to keyword matching
        if outcome == "unknown":
            outcome = self._classify_outcome_keywords(text)

        if outcome == "unknown":
            return False

        return self._update_recommendation(
            pending[0]["id"],
            outcome,
            text[:200],
        )

    def _classify_outcome_semantic(self, text: str) -> str:
        """
        LLM classifier for outcome detection.
        Returns: 'success', 'failure', 'partial', or 'unknown'.
        """
        try:
            from eos_ai.model_router import call_with_fallback, TaskType

            result = call_with_fallback(
                prompt=(
                    "Does this message indicate a recommendation "
                    "succeeded, failed, partially worked, or is unrelated?\n"
                    "Answer exactly one word: SUCCESS, FAILURE, PARTIAL, or UNKNOWN.\n\n"
                    f"Message: {text[:300]}"
                ),
                task_type=TaskType.CLASSIFY,
            )
            output = result.output.upper().strip()
            if "SUCCESS" in output:
                return "success"
            if "FAILURE" in output:
                return "failure"
            if "PARTIAL" in output:
                return "partial"
            return "unknown"
        except Exception:
            return "unknown"

    def _classify_outcome_keywords(self, text: str) -> str:
        """Keyword fallback for outcome classification."""
        text_lower = text.lower()

        success_signals = [
            "worked",
            "it worked",
            "got a reply",
            "booked a call",
            "closed",
            "they said yes",
            "got a client",
            "made a sale",
            "it landed",
            "did it",
            "sent the dms",
            "sent 20",
            "converting",
            "is working",
            "are working",
        ]
        failure_signals = [
            "didn't work",
            "no replies",
            "ghosted",
            "failed",
            "didn't do it",
            "couldn't",
            "no response",
            "nobody responded",
            "bombed",
            "skipped",
            "not working",
            "no traction",
        ]
        partial_signals = [
            "kind of worked",
            "some replies",
            "partially",
            "a few",
            "not all",
            "but not",
        ]

        # Check partial before success — "kind of worked" contains "worked"
        if any(s in text_lower for s in partial_signals):
            return "partial"
        if any(s in text_lower for s in success_signals):
            return "success"
        if any(s in text_lower for s in failure_signals):
            return "failure"
        return "unknown"

    def _get_pending_recs(self) -> list[dict]:
        """Get pending recommendations from Neon."""
        try:
            from eos_ai.db import get_conn

            with get_conn(self.ctx.org_id) as cur:
                cur.execute(
                    """
                    SELECT id, payload_json, created_at
                    FROM events
                    WHERE org_id = %s
                    AND event_type = 'recommendation'
                    AND payload_json->>'outcome' = 'pending'
                    ORDER BY created_at DESC
                    LIMIT 5
                    """,
                    (self.ctx.org_id,),
                )
                rows = cur.fetchall()
                return [
                    {
                        "id": r["id"],
                        "payload": (
                            json.loads(r["payload_json"])
                            if isinstance(r["payload_json"], str)
                            else r["payload_json"]
                        ),
                        "created_at": r["created_at"],
                    }
                    for r in rows
                ]
        except Exception as e:
            print(f"[FeedbackLoop] Pending recs: {e}")
            return []

    def _update_recommendation(
        self,
        event_id: str,
        outcome: str,
        note: str = "",
    ) -> bool:
        """Update a recommendation's outcome in Neon."""
        try:
            from eos_ai.db import get_conn

            with get_conn(self.ctx.org_id) as cur:
                cur.execute(
                    "SELECT payload_json FROM events WHERE id = %s",
                    (event_id,),
                )
                row = cur.fetchone()
                if not row:
                    return False

                payload = row["payload_json"]
                if isinstance(payload, str):
                    payload = json.loads(payload)
                payload["outcome"] = outcome
                payload["outcome_note"] = note
                payload["outcome_at"] = datetime.now().isoformat()

                cur.execute(
                    "UPDATE events SET payload_json = %s WHERE id = %s",
                    (json.dumps(payload), event_id),
                )
                print(f"[FeedbackLoop] Outcome logged: {outcome}")
                return True
        except Exception as e:
            print(f"[FeedbackLoop] Update rec: {e}")
            return False

    def get_recommendation_stats(self) -> dict:
        """
        Return outcome distribution across all logged recommendations.
        What percentage are succeeding? What percentage failing?
        """
        try:
            from eos_ai.db import get_conn

            with get_conn(self.ctx.org_id) as cur:
                cur.execute(
                    """
                    SELECT
                        payload_json->>'outcome' as outcome,
                        COUNT(*) as count
                    FROM events
                    WHERE org_id = %s
                    AND event_type = 'recommendation'
                    GROUP BY outcome
                    """,
                    (self.ctx.org_id,),
                )
                rows = cur.fetchall()
                return {r["outcome"]: r["count"] for r in rows}
        except Exception as e:
            print(f"[FeedbackLoop] Stats: {e}")
            return {}

    def check_and_close_observable_signals(self) -> int:
        """
        Check each pending recommendation against observable DB signals.
        Auto-closes when signal is found. Expires after 14 days as inconclusive.
        Returns number of recommendations closed.

        Observable signals:
        - DM/outreach recs → new interactions created after rec
        - Task recs → tasks completed after rec
        - 14 days old → inconclusive (not failed — just unmeasured)
        """
        from datetime import timezone, timedelta

        pending = self._get_pending_recs()
        if not pending:
            return 0

        closed = 0
        try:
            from eos_ai.db import get_conn

            with get_conn(self.ctx.org_id) as cur:
                for rec in pending:
                    event_id = rec["id"]
                    payload = rec["payload"]
                    created_at = rec["created_at"]
                    content = (payload.get("content") or "").lower()
                    outcome = None
                    close_reason = ""

                    # DM/outreach recommendation → check new interactions
                    if any(
                        kw in content
                        for kw in [
                            "dm",
                            "outreach",
                            "send",
                            "message",
                            "reach out",
                        ]
                    ):
                        cur.execute(
                            """
                            SELECT COUNT(*) AS cnt FROM interactions
                            WHERE org_id = %s
                            AND created_at > %s
                            """,
                            (self.ctx.org_id, created_at),
                        )
                        row = cur.fetchone()
                        if row and (row["cnt"] or 0) > 0:
                            outcome = "success"
                            close_reason = (
                                f"observable: {row['cnt']} interactions after rec"
                            )

                    # Task recommendation → check completed tasks
                    if outcome is None and any(
                        kw in content
                        for kw in [
                            "task",
                            "complete",
                            "finish",
                            "do the",
                            "execute",
                        ]
                    ):
                        cur.execute(
                            """
                            SELECT COUNT(*) AS cnt FROM tasks
                            WHERE org_id = %s
                            AND status = 'completed'
                            AND completed_at > %s
                            """,
                            (self.ctx.org_id, created_at),
                        )
                        row = cur.fetchone()
                        if row and (row["cnt"] or 0) > 0:
                            outcome = "success"
                            close_reason = (
                                f"observable: {row['cnt']} tasks completed after rec"
                            )

                    # 14-day expiry → inconclusive
                    if outcome is None and created_at:
                        created_aware = created_at
                        if created_aware.tzinfo is None:
                            created_aware = created_aware.replace(tzinfo=timezone.utc)
                        age = datetime.now(timezone.utc) - created_aware
                        if age > timedelta(days=14):
                            outcome = "inconclusive"
                            close_reason = "expired: 14 days without signal"

                    if outcome:
                        payload["outcome"] = outcome
                        payload["outcome_note"] = close_reason
                        payload["outcome_at"] = datetime.now().isoformat()
                        payload["auto_closed"] = True

                        cur.execute(
                            "UPDATE events SET payload_json = %s WHERE id = %s",
                            (json.dumps(payload), event_id),
                        )
                        closed += 1
                        print(f"[FeedbackLoop] Auto-closed: {outcome} — {close_reason}")

        except Exception as e:
            print(f"[FeedbackLoop] Signal check: {e}")

        return closed
