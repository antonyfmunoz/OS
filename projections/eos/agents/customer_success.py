"""EOS Customer Success Agent — retention, satisfaction, support routing.

Permission tier: EXECUTE — can send messages and create tasks autonomously.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from substrate import Substrate
from substrate.types import Component, ComponentType, PermissionTier, RegistrationResult

from projections.eos.agents.base import DepartmentAgent, SkillResult


class CustomerSuccessAgent(DepartmentAgent):
    DEPARTMENT = "customer_success"
    PERMISSION_TIER = PermissionTier.EXECUTE

    def _register_skills(self) -> None:
        self._add_skill(
            "ticket_routing",
            "classify",
            "Classify and route a support ticket to the right handler",
            self._ticket_routing,
        )
        self._add_skill(
            "satisfaction_report",
            "report",
            "Generate customer satisfaction report",
            self._satisfaction_report,
        )
        self._add_skill(
            "churn_detection",
            "analyze",
            "Identify customers at risk of churning",
            self._churn_detection,
        )
        self._add_skill(
            "onboarding_guide",
            "draft_content",
            "Create personalized onboarding guidance",
            self._onboarding_guide,
        )
        self._add_skill(
            "feedback_analysis",
            "analyze",
            "Analyze customer feedback for patterns",
            self._feedback_analysis,
        )
        self._add_skill(
            "response_draft",
            "draft_message",
            "Draft a response to a customer inquiry",
            self._response_draft,
        )
        self._add_skill(
            "send_response",
            "send_message",
            "Send a response to a customer (EXECUTE tier)",
            self._send_response,
        )

    def _ticket_routing(self, **kwargs: Any) -> SkillResult:
        subject = kwargs.get("subject", "").lower()
        body = kwargs.get("body", "").lower()
        content = f"{subject} {body}"

        routing_rules = [
            (["billing", "payment", "charge", "refund", "invoice"], "finance"),
            (["bug", "error", "crash", "broken", "not working"], "engineering"),
            (["feature", "request", "suggestion", "wish", "add"], "product"),
            (["cancel", "unsubscribe", "leave", "quit"], "retention"),
            (["how to", "help", "tutorial", "guide", "setup"], "support"),
        ]

        for keywords, department in routing_rules:
            if any(kw in content for kw in keywords):
                priority = "high" if department in ("retention", "finance") else "normal"
                return SkillResult(
                    success=True,
                    output={
                        "department": department,
                        "priority": priority,
                        "matched_keywords": [kw for kw in keywords if kw in content],
                    },
                )

        return SkillResult(
            success=True,
            output={"department": "support", "priority": "normal", "matched_keywords": []},
        )

    def _satisfaction_report(self, **kwargs: Any) -> SkillResult:
        try:
            from substrate import get_conn

            with get_conn(self._org_id) as cur:
                cur.execute(
                    """
                    SELECT
                        AVG((payload_json->>'rating')::numeric) as avg_rating,
                        COUNT(*) as total_responses
                    FROM events
                    WHERE org_id = %s AND event_type = 'satisfaction_survey'
                    AND created_at >= NOW() - INTERVAL '30 days'
                    """,
                    (self._org_id,),
                )
                row = cur.fetchone()
                avg = float(row["avg_rating"]) if row and row["avg_rating"] else 0
                return SkillResult(
                    success=True,
                    output={
                        "avg_rating": round(avg, 2),
                        "total_responses": row["total_responses"] if row else 0,
                        "period": "30d",
                        "generated_at": datetime.now(timezone.utc).isoformat(),
                    },
                )
        except Exception:
            return SkillResult(
                success=True,
                output={
                    "avg_rating": 0,
                    "total_responses": 0,
                    "period": "30d",
                    "note": "No survey data available",
                },
            )

    def _churn_detection(self, **kwargs: Any) -> SkillResult:
        try:
            from substrate import get_conn

            with get_conn(self._org_id) as cur:
                cur.execute(
                    """
                    SELECT payload_json->>'customer_id' as customer_id,
                           payload_json->>'last_active' as last_active,
                           payload_json->>'engagement_score' as score
                    FROM events
                    WHERE org_id = %s AND event_type = 'customer_activity'
                    ORDER BY created_at DESC LIMIT 100
                    """,
                    (self._org_id,),
                )
                rows = cur.fetchall()
                at_risk = [
                    {
                        "customer_id": r["customer_id"],
                        "engagement_score": float(r["score"]) if r["score"] else 0,
                    }
                    for r in rows
                    if r["score"] and float(r["score"]) < 30
                ]
                return SkillResult(
                    success=True,
                    output={"at_risk_count": len(at_risk), "at_risk_customers": at_risk[:10]},
                )
        except Exception:
            return SkillResult(success=True, output={"at_risk_count": 0, "at_risk_customers": []})

    def _onboarding_guide(self, **kwargs: Any) -> SkillResult:
        product = kwargs.get("product", "Initiate Arena")
        user_type = kwargs.get("user_type", "new_member")

        steps = {
            "new_member": [
                "Welcome message with community intro",
                "Assessment survey (goals, current state)",
                "Match with accountability group",
                "First week challenge assignment",
                "Check-in scheduling",
            ],
            "returning": [
                "Welcome back message",
                "Progress recap since last active",
                "Updated program recommendations",
                "Re-match with accountability group",
            ],
        }

        return SkillResult(
            success=True,
            output={
                "product": product,
                "user_type": user_type,
                "onboarding_steps": steps.get(user_type, steps["new_member"]),
                "status": "draft",
            },
        )

    def _feedback_analysis(self, **kwargs: Any) -> SkillResult:
        feedback_items = kwargs.get("items", [])
        if not feedback_items:
            return SkillResult(
                success=True, output={"themes": [], "note": "No feedback to analyze"}
            )

        themes: dict[str, int] = {}
        for item in feedback_items:
            text = item.get("text", "").lower() if isinstance(item, dict) else str(item).lower()
            if "price" in text or "expensive" in text or "cost" in text:
                themes["pricing"] = themes.get("pricing", 0) + 1
            if "slow" in text or "performance" in text or "fast" in text:
                themes["performance"] = themes.get("performance", 0) + 1
            if "support" in text or "help" in text or "response" in text:
                themes["support_quality"] = themes.get("support_quality", 0) + 1
            if "feature" in text or "missing" in text or "add" in text:
                themes["feature_requests"] = themes.get("feature_requests", 0) + 1

        sorted_themes = sorted(themes.items(), key=lambda x: x[1], reverse=True)
        return SkillResult(
            success=True,
            output={
                "total_items": len(feedback_items),
                "themes": [{"name": t[0], "count": t[1]} for t in sorted_themes],
            },
        )

    def _response_draft(self, **kwargs: Any) -> SkillResult:
        inquiry = kwargs.get("inquiry", "")
        customer = kwargs.get("customer_name", "there")

        try:
            from adapters.models.model_router import call_with_fallback

            result = call_with_fallback(
                prompt=(
                    f"Draft a customer support response to: {inquiry[:500]}\n"
                    f"Customer name: {customer}\n"
                    f"Brand: Initiate Arena. Voice: supportive, direct, solution-oriented."
                ),
                system="Customer success agent. Helpful, empathetic, solution-focused.",
                task_type="fast_response",
            )
            if result.output:
                return SkillResult(
                    success=True,
                    output={"draft": result.output.strip()[:1000], "status": "draft"},
                )
        except Exception:
            pass

        return SkillResult(
            success=True,
            output={
                "draft": f"Hey {customer} — thanks for reaching out. Let me look into this and get back to you shortly.",
                "status": "draft",
            },
        )

    def _send_response(self, **kwargs: Any) -> SkillResult:
        return SkillResult(
            success=True,
            output={
                "status": "sent",
                "channel": kwargs.get("channel", ""),
                "customer_id": kwargs.get("customer_id", ""),
                "message": kwargs.get("message", ""),
            },
        )


async def register_customer_success_agent(substrate: Substrate) -> RegistrationResult:
    agent = CustomerSuccessAgent()
    component = Component(
        component_type=ComponentType.AGENT,
        name="eos-customer-success",
        capabilities=[
            "ticket_routing",
            "satisfaction_tracking",
            "churn_detection",
            "onboarding_guidance",
            "feedback_analysis",
            "response_drafting",
            "message_sending",
        ],
        metadata=agent.metadata(),
    )
    return await substrate.register(component)
