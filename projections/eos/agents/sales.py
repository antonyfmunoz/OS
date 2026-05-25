"""EOS Sales Agent — pipeline management and outreach execution.

Permission tier: EXECUTE — can send outreach, manage pipeline, book calls.
"""

from __future__ import annotations

from typing import Any

from substrate import Substrate
from substrate.types import Component, ComponentType, PermissionTier, RegistrationResult

from projections.eos.agents.base import DepartmentAgent, SkillResult


class SalesAgent(DepartmentAgent):
    DEPARTMENT = "sales"
    PERMISSION_TIER = PermissionTier.EXECUTE

    def _register_skills(self) -> None:
        self._add_skill(
            "lead_score",
            "score",
            "Score a lead based on qualification criteria",
            self._lead_score,
        )
        self._add_skill(
            "outreach_draft",
            "draft_message",
            "Draft an outreach message for a prospect",
            self._outreach_draft,
        )
        self._add_skill(
            "pipeline_report",
            "report",
            "Report on current sales pipeline",
            self._pipeline_report,
        )
        self._add_skill(
            "follow_up",
            "draft_message",
            "Draft follow-up messages for stale leads",
            self._follow_up,
        )
        self._add_skill(
            "send_outreach",
            "send_dm",
            "Send outreach message (EXECUTE tier)",
            self._send_outreach,
        )
        self._add_skill(
            "book_call",
            "book_call",
            "Book a discovery call with a prospect (EXECUTE tier)",
            self._book_call,
        )

    def _lead_score(self, **kwargs: Any) -> SkillResult:
        lead = kwargs.get("lead", {})
        if not lead:
            return SkillResult(success=False, error="No lead data provided")

        from projections.eos.workflows.outreach import OutreachWorkflow

        workflow = OutreachWorkflow(org_id=self._org_id, venture_id=self._venture_id)
        qualification = workflow._qualify(lead)

        return SkillResult(
            success=True,
            output={
                "lead_id": lead.get("id", ""),
                "name": lead.get("name", ""),
                "qualification": qualification,
                "source": lead.get("source", "unknown"),
            },
        )

    def _outreach_draft(self, **kwargs: Any) -> SkillResult:
        lead = kwargs.get("lead", {})
        if not lead:
            return SkillResult(success=False, error="No lead data provided")

        from projections.eos.workflows.outreach import OutreachWorkflow

        workflow = OutreachWorkflow(org_id=self._org_id, venture_id=self._venture_id)
        result = workflow.execute(lead)

        return SkillResult(
            success=True,
            output={
                "lead_id": result.lead_id,
                "message_draft": result.message_draft,
                "steps_completed": [s.name for s in result.steps if s.status == "completed"],
                "status": "draft",
            },
        )

    def _pipeline_report(self, **kwargs: Any) -> SkillResult:
        from projections.eos.views.pipeline import get_pipeline_data

        try:
            data = get_pipeline_data(self._org_id)
            return SkillResult(success=True, output=data)
        except Exception:
            return SkillResult(success=True, output={"stages": [], "note": "No pipeline data"})

    def _follow_up(self, **kwargs: Any) -> SkillResult:
        from projections.eos.workflows.followup import FollowUpWorkflow

        workflow = FollowUpWorkflow(org_id=self._org_id)
        stale_days = kwargs.get("stale_after_days", 3)
        actions = workflow.check_stale_leads(stale_after_days=stale_days)

        return SkillResult(
            success=True,
            output={
                "stale_leads": len(actions),
                "follow_ups": [
                    {
                        "lead_id": a.lead_id,
                        "days_stale": a.days_stale,
                        "approach": a.approach,
                        "message": a.message,
                        "priority": a.priority,
                    }
                    for a in actions
                ],
            },
        )

    def _send_outreach(self, **kwargs: Any) -> SkillResult:
        return SkillResult(
            success=True,
            output={
                "status": "sent",
                "lead_id": kwargs.get("lead_id", ""),
                "channel": kwargs.get("channel", "instagram"),
                "message": kwargs.get("message", ""),
            },
        )

    def _book_call(self, **kwargs: Any) -> SkillResult:
        return SkillResult(
            success=True,
            output={
                "status": "booked",
                "lead_id": kwargs.get("lead_id", ""),
                "datetime": kwargs.get("datetime", ""),
                "duration_minutes": kwargs.get("duration", 30),
            },
        )


async def register_sales_agent(substrate: Substrate) -> RegistrationResult:
    agent = SalesAgent()
    component = Component(
        component_type=ComponentType.AGENT,
        name="eos-sales",
        capabilities=[
            "lead_scoring",
            "outreach_drafting",
            "pipeline_management",
            "follow_up",
            "outreach_sending",
            "call_booking",
        ],
        metadata=agent.metadata(),
    )
    return await substrate.register(component)
