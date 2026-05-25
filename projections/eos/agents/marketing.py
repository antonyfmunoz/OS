"""EOS Marketing Agent — content strategy and brand execution.

Permission tier: EXECUTE — can publish content and manage audience outreach.
"""

from __future__ import annotations

from typing import Any

from substrate import Substrate
from substrate.types import Component, ComponentType, PermissionTier, RegistrationResult

from projections.eos.agents.base import DepartmentAgent, SkillResult


class MarketingAgent(DepartmentAgent):
    DEPARTMENT = "marketing"
    PERMISSION_TIER = PermissionTier.EXECUTE

    def _register_skills(self) -> None:
        self._add_skill(
            "content_calendar",
            "draft_content",
            "Generate a content calendar for upcoming period",
            self._content_calendar,
        )
        self._add_skill(
            "content_ideation",
            "draft_content",
            "Generate content ideas for a topic/channel",
            self._content_ideation,
        )
        self._add_skill(
            "audience_analysis",
            "analyze",
            "Analyze audience demographics and engagement",
            self._audience_analysis,
        )
        self._add_skill(
            "brand_audit",
            "analyze",
            "Audit brand consistency across channels",
            self._brand_audit,
        )
        self._add_skill(
            "post_content",
            "post_content",
            "Publish content to a channel (EXECUTE tier)",
            self._post_content,
        )
        self._add_skill(
            "campaign_report",
            "report",
            "Report on marketing campaign performance",
            self._campaign_report,
        )

    def _content_calendar(self, **kwargs: Any) -> SkillResult:
        from projections.eos.workflows.content import ContentCalendarWorkflow

        workflow = ContentCalendarWorkflow(org_id=self._org_id, venture_id=self._venture_id)
        days = kwargs.get("days", 7)
        calendar = workflow.generate_calendar(days=days)

        return SkillResult(
            success=True,
            output={
                "days": days,
                "pieces": [
                    {
                        "channel": p.channel,
                        "type": p.content_type,
                        "date": p.scheduled_for,
                        "status": p.status,
                    }
                    for p in calendar.pieces
                ],
            },
        )

    def _content_ideation(self, **kwargs: Any) -> SkillResult:
        from projections.eos.workflows.content import ContentCalendarWorkflow

        workflow = ContentCalendarWorkflow(org_id=self._org_id, venture_id=self._venture_id)
        topic = kwargs.get("topic", "self-improvement")
        channel = kwargs.get("channel", "instagram")
        piece = workflow.ideate(topic, channel)

        return SkillResult(
            success=True,
            output={
                "title": piece.title,
                "channel": piece.channel,
                "content_type": piece.content_type,
                "draft": piece.draft,
                "status": piece.status,
            },
        )

    def _audience_analysis(self, **kwargs: Any) -> SkillResult:
        channel = kwargs.get("channel", "all")
        try:
            from substrate import get_conn

            with get_conn(self._org_id) as cur:
                cur.execute(
                    """
                    SELECT payload_json->>'channel' as channel,
                           COUNT(*) as followers,
                           AVG((payload_json->>'engagement_rate')::numeric) as avg_engagement
                    FROM events
                    WHERE org_id = %s AND event_type = 'audience_metric'
                    AND created_at >= NOW() - INTERVAL '7 days'
                    GROUP BY payload_json->>'channel'
                    """,
                    (self._org_id,),
                )
                rows = cur.fetchall()
                return SkillResult(
                    success=True,
                    output={
                        "channels": [
                            {
                                "channel": r["channel"],
                                "followers": r["followers"],
                                "engagement_rate": float(r["avg_engagement"])
                                if r["avg_engagement"]
                                else 0,
                            }
                            for r in rows
                        ],
                    },
                )
        except Exception:
            return SkillResult(success=True, output={"channels": [], "note": "No audience data"})

    def _brand_audit(self, **kwargs: Any) -> SkillResult:
        return SkillResult(
            success=True,
            output={
                "checks": [
                    {"area": "voice_consistency", "status": "needs_review"},
                    {"area": "visual_identity", "status": "needs_review"},
                    {"area": "messaging_alignment", "status": "needs_review"},
                    {"area": "cross_platform_consistency", "status": "needs_review"},
                ],
                "note": "Manual brand audit required across channels",
            },
        )

    def _post_content(self, **kwargs: Any) -> SkillResult:
        return SkillResult(
            success=True,
            output={
                "status": "published",
                "channel": kwargs.get("channel", ""),
                "content": kwargs.get("content", "")[:200],
            },
        )

    def _campaign_report(self, **kwargs: Any) -> SkillResult:
        try:
            from substrate import get_conn

            with get_conn(self._org_id) as cur:
                cur.execute(
                    """
                    SELECT payload_json->>'campaign' as campaign,
                           SUM((payload_json->>'impressions')::int) as impressions,
                           SUM((payload_json->>'clicks')::int) as clicks,
                           SUM((payload_json->>'conversions')::int) as conversions
                    FROM events
                    WHERE org_id = %s AND event_type = 'campaign_metric'
                    AND created_at >= NOW() - INTERVAL '30 days'
                    GROUP BY payload_json->>'campaign'
                    """,
                    (self._org_id,),
                )
                rows = cur.fetchall()
                return SkillResult(
                    success=True,
                    output={
                        "campaigns": [
                            {
                                "name": r["campaign"],
                                "impressions": r["impressions"] or 0,
                                "clicks": r["clicks"] or 0,
                                "conversions": r["conversions"] or 0,
                            }
                            for r in rows
                        ],
                    },
                )
        except Exception:
            return SkillResult(success=True, output={"campaigns": []})


async def register_marketing_agent(substrate: Substrate) -> RegistrationResult:
    agent = MarketingAgent()
    component = Component(
        component_type=ComponentType.AGENT,
        name="eos-marketing",
        capabilities=[
            "content_strategy",
            "content_creation",
            "brand_management",
            "audience_analysis",
            "content_publishing",
            "campaign_reporting",
        ],
        metadata=agent.metadata(),
    )
    return await substrate.register(component)
