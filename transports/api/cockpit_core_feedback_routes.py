"""Cockpit feedback & notification routes — extracted from cockpit_core_routes.py.

Covers: /feedback, /feedback/stats, /feedback/skills, /feedback/recommendations,
        /notifications, /notifications/send.
Phase 0.3 route split. UMH transport layer.
"""
from __future__ import annotations

import logging
from typing import Any

from fastapi import Depends

from transports.api.governed import governed_mutation

logger = logging.getLogger(__name__)


def register_feedback_routes(router, _require_operator_role, helpers):
    """Register feedback and notification routes onto the given router."""

    @router.get("/notifications")
    def notification_history(limit: int = 50):
        """Recent notification history."""
        try:
            from substrate.sockets.notification_engine import get_notification_engine

            engine = get_notification_engine()
            return {
                "history": engine.recent_history(limit),
                "stats": engine.stats,
                "channels": engine.available_channels,
            }
        except Exception as e:
            return {"error": str(e), "history": []}

    @router.post("/feedback")
    def record_feedback(payload: dict):
        """Record explicit RLHF feedback for an interaction."""
        from substrate.execution.feedback_loop import (
            FeedbackEntry,
            OutcomeCategory,
            Rating,
            get_feedback_loop,
        )

        interaction_id = payload.get("interaction_id", "")
        if not interaction_id:
            return {"ok": False, "error": "interaction_id required"}

        try:
            rating = Rating(str(payload.get("rating", "")))
        except ValueError:
            valid = [r.value for r in Rating]
            return {"ok": False, "error": f"invalid rating, must be one of: {valid}"}

        try:
            outcome_type = OutcomeCategory(payload.get("outcome_type", ""))
        except ValueError:
            valid = [o.value for o in OutcomeCategory]
            return {"ok": False, "error": f"invalid outcome_type, must be one of: {valid}"}

        def _do_record():
            loop = get_feedback_loop()
            entry = FeedbackEntry(
                interaction_id=interaction_id,
                rating=rating,
                outcome_type=outcome_type,
                notes=payload.get("notes", ""),
            )
            success = loop.record_feedback(entry)
            return f"feedback recorded for {interaction_id}", success

        resp = governed_mutation(
            mutation_name="state_mutate",
            intent=f"record feedback for interaction {interaction_id}",
            execute_fn=_do_record,
            source="cockpit",
        )
        return resp.to_http_dict()

    @router.get("/feedback/stats")
    def feedback_stats(agent: str = ""):
        """Aggregate RLHF feedback statistics, optionally filtered by agent."""
        from substrate.execution.feedback_loop import get_feedback_loop

        loop = get_feedback_loop()
        return loop.get_feedback_stats(agent=agent)

    @router.get("/feedback/skills")
    def feedback_skill_effectiveness(
        agent: str = "",
        skill: str = "",
        window_days: int = 30,
    ):
        """Skill effectiveness based on RLHF feedback.

        Query: ?agent=eos-sales&skill=analyze_icp_signal&window_days=30
        """
        from substrate.execution.feedback_loop import get_feedback_loop

        if not agent or not skill:
            return {"error": "both agent and skill query params required"}

        loop = get_feedback_loop()
        return loop.skill_effectiveness(agent=agent, skill=skill, window_days=window_days)

    @router.get("/feedback/recommendations")
    def feedback_recommendations():
        """Routing adjustment recommendations based on RLHF feedback patterns."""
        from substrate.execution.feedback_loop import get_feedback_loop

        loop = get_feedback_loop()
        return {"recommendations": loop.recommend_routing_adjustment()}

    @router.post("/notifications/send", dependencies=[Depends(_require_operator_role)])
    def send_notification(payload: dict):
        """Send a notification through the engine."""
        def _do_send():
            try:
                from substrate.sockets.notification_engine import (
                    get_notification_engine,
                    Notification,
                    NotificationPriority,
                    NotificationChannel,
                )

                engine = get_notification_engine()
                channels = []
                for ch in payload.get("channels", []):
                    try:
                        channels.append(NotificationChannel(ch))
                    except ValueError:
                        pass

                notification = Notification(
                    title=payload.get("title", ""),
                    body=payload.get("body", ""),
                    priority=NotificationPriority(payload.get("priority", "normal")),
                    channel_preference=channels,
                    source=payload.get("source", "cockpit"),
                    target_user=payload.get("target_user", ""),
                )
                result = engine.send(notification)
                return f"notification sent: {result.sent}", result.sent
            except Exception as e:
                return str(e), False

        resp = governed_mutation(
            mutation_name="channel_message_send",
            intent=f"send notification: {payload.get('title', '')[:50]}",
            execute_fn=_do_send,
            source="cockpit",
        )
        return resp.to_http_dict()
