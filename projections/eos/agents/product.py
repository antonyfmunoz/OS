"""EOS Product Agent — roadmap management, feature prioritization, user feedback.

Permission tier: DRAFT — can create tasks and documents but not send/execute externally.
"""

from __future__ import annotations

from typing import Any

from substrate import Substrate
from substrate.types import Component, ComponentType, PermissionTier, RegistrationResult

from projections.eos.agents.base import DepartmentAgent, SkillResult


class ProductAgent(DepartmentAgent):
    DEPARTMENT = "product"
    PERMISSION_TIER = PermissionTier.DRAFT

    def _register_skills(self) -> None:
        self._add_skill(
            "roadmap_status",
            "report",
            "Report on product roadmap status",
            self._roadmap_status,
        )
        self._add_skill(
            "feature_prioritize",
            "analyze",
            "Prioritize features using ICE scoring",
            self._feature_prioritize,
        )
        self._add_skill(
            "user_feedback_summary",
            "analyze",
            "Summarize user feedback into themes",
            self._user_feedback_summary,
        )
        self._add_skill(
            "competitor_analysis",
            "research",
            "Research competitor features and positioning",
            self._competitor_analysis,
        )
        self._add_skill(
            "release_plan",
            "draft_content",
            "Draft a release plan for a feature set",
            self._release_plan,
        )
        self._add_skill(
            "spec_draft",
            "create_document",
            "Draft a product specification document",
            self._spec_draft,
        )

    def _roadmap_status(self, **kwargs: Any) -> SkillResult:
        try:
            from substrate import get_conn

            with get_conn(self._org_id) as cur:
                cur.execute(
                    """
                    SELECT payload_json->>'feature' as feature,
                           payload_json->>'status' as status,
                           payload_json->>'priority' as priority
                    FROM events
                    WHERE org_id = %s AND event_type = 'roadmap_item'
                    ORDER BY payload_json->>'priority' ASC
                    LIMIT 20
                    """,
                    (self._org_id,),
                )
                rows = cur.fetchall()
                return SkillResult(
                    success=True,
                    output={
                        "items": [
                            {
                                "feature": r["feature"],
                                "status": r["status"],
                                "priority": r["priority"],
                            }
                            for r in rows
                        ],
                    },
                )
        except Exception:
            return SkillResult(success=True, output={"items": [], "note": "No roadmap data"})

    def _feature_prioritize(self, **kwargs: Any) -> SkillResult:
        features = kwargs.get("features", [])
        if not features:
            return SkillResult(success=False, error="No features provided to prioritize")

        scored = []
        for f in features:
            if isinstance(f, str):
                f = {"name": f, "impact": 5, "confidence": 5, "ease": 5}
            impact = f.get("impact", 5)
            confidence = f.get("confidence", 5)
            ease = f.get("ease", 5)
            ice_score = (impact * confidence * ease) / 10
            scored.append(
                {
                    "name": f.get("name", ""),
                    "impact": impact,
                    "confidence": confidence,
                    "ease": ease,
                    "ice_score": round(ice_score, 1),
                }
            )

        scored.sort(key=lambda x: x["ice_score"], reverse=True)
        return SkillResult(success=True, output={"prioritized": scored})

    def _user_feedback_summary(self, **kwargs: Any) -> SkillResult:
        try:
            from substrate import get_conn

            with get_conn(self._org_id) as cur:
                cur.execute(
                    """
                    SELECT payload_json->>'text' as text,
                           payload_json->>'sentiment' as sentiment
                    FROM events
                    WHERE org_id = %s AND event_type = 'user_feedback'
                    AND created_at >= NOW() - INTERVAL '30 days'
                    ORDER BY created_at DESC LIMIT 50
                    """,
                    (self._org_id,),
                )
                rows = cur.fetchall()
                positive = sum(1 for r in rows if r["sentiment"] == "positive")
                negative = sum(1 for r in rows if r["sentiment"] == "negative")
                return SkillResult(
                    success=True,
                    output={
                        "total": len(rows),
                        "positive": positive,
                        "negative": negative,
                        "neutral": len(rows) - positive - negative,
                    },
                )
        except Exception:
            return SkillResult(success=True, output={"total": 0, "note": "No feedback data"})

    def _competitor_analysis(self, **kwargs: Any) -> SkillResult:
        competitor = kwargs.get("competitor", "")
        try:
            from adapters.models.model_router import call_with_fallback

            result = call_with_fallback(
                prompt=(
                    f"Brief competitive analysis of {competitor} vs Initiate Arena. "
                    f"Cover: target audience, pricing, key features, differentiators. "
                    f"Be concise — bullet points."
                ),
                system="Product strategist. Objective competitive analysis.",
                task_type="fast_response",
            )
            if result.output:
                return SkillResult(
                    success=True,
                    output={"competitor": competitor, "analysis": result.output.strip()[:1000]},
                )
        except Exception:
            pass

        return SkillResult(
            success=True,
            output={"competitor": competitor, "analysis": "Manual research needed"},
        )

    def _release_plan(self, **kwargs: Any) -> SkillResult:
        features = kwargs.get("features", [])
        target_date = kwargs.get("target_date", "")

        return SkillResult(
            success=True,
            output={
                "features": features,
                "target_date": target_date,
                "phases": [
                    {"phase": "development", "duration": "2 weeks"},
                    {"phase": "internal_testing", "duration": "3 days"},
                    {"phase": "beta", "duration": "1 week"},
                    {"phase": "launch", "duration": "1 day"},
                ],
                "status": "draft",
            },
        )

    def _spec_draft(self, **kwargs: Any) -> SkillResult:
        feature = kwargs.get("feature", "")
        try:
            from adapters.models.model_router import call_with_fallback

            result = call_with_fallback(
                prompt=(
                    f"Write a product spec outline for: {feature}\n"
                    f"Include: Problem, Solution, User Stories, Success Metrics, "
                    f"Technical Requirements, Timeline. Be concise."
                ),
                system="Product manager writing specs. Clear, actionable, measurable.",
                task_type="fast_response",
            )
            if result.output:
                return SkillResult(
                    success=True,
                    output={
                        "feature": feature,
                        "spec": result.output.strip()[:2000],
                        "status": "draft",
                    },
                )
        except Exception:
            pass

        return SkillResult(
            success=True,
            output={
                "feature": feature,
                "sections": ["Problem", "Solution", "User Stories", "Success Metrics", "Timeline"],
                "status": "outline",
            },
        )


async def register_product_agent(substrate: Substrate) -> RegistrationResult:
    agent = ProductAgent()
    component = Component(
        component_type=ComponentType.AGENT,
        name="eos-product",
        capabilities=[
            "roadmap_management",
            "feature_prioritization",
            "user_feedback_analysis",
            "competitor_tracking",
            "release_planning",
            "spec_drafting",
        ],
        metadata=agent.metadata(),
    )
    return await substrate.register(component)
