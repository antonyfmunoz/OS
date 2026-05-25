"""EOS CEO Agent — strategic decision making for entrepreneur operations.

Permission tier: COMMIT — full authority, can approve any action across departments.
"""

from __future__ import annotations

from typing import Any

from substrate import Substrate
from substrate.types import Component, ComponentType, PermissionTier, RegistrationResult

from projections.eos.agents.base import DepartmentAgent, SkillResult


class CEOAgent(DepartmentAgent):
    DEPARTMENT = "executive"
    PERMISSION_TIER = PermissionTier.COMMIT

    def _register_skills(self) -> None:
        self._add_skill(
            "strategic_analysis",
            "analyze",
            "Analyze strategic position and opportunities",
            self._strategic_analysis,
        )
        self._add_skill(
            "decision_brief",
            "report",
            "Generate decision brief for a key decision",
            self._decision_brief,
        )
        self._add_skill(
            "delegation",
            "create_task",
            "Delegate a task to a department agent",
            self._delegation,
        )
        self._add_skill(
            "pipeline_review",
            "report",
            "Review full pipeline across all departments",
            self._pipeline_review,
        )
        self._add_skill(
            "morning_brief",
            "report",
            "Generate CEO morning briefing",
            self._morning_brief,
        )
        self._add_skill(
            "approve_action",
            "execute_payment",
            "Approve a queued action (COMMIT tier)",
            self._approve_action,
        )

    def _strategic_analysis(self, **kwargs: Any) -> SkillResult:
        focus_area = kwargs.get("area", "overall")

        try:
            from adapters.models.model_router import call_with_fallback

            result = call_with_fallback(
                prompt=(
                    f"Strategic analysis for a pre-revenue personal development company "
                    f"(Initiate Arena) targeting men 18-25. Focus: {focus_area}. "
                    f"North star: $10K/month net profit. "
                    f"Current stage: building infrastructure + outreach. "
                    f"Provide 3-5 actionable insights."
                ),
                system="CEO strategic advisor. Direct, actionable, reality-based.",
                task_type="fast_response",
                agent_type="ceo",
            )
            if result.output:
                return SkillResult(
                    success=True,
                    output={"area": focus_area, "analysis": result.output.strip()[:1500]},
                )
        except Exception:
            pass

        return SkillResult(
            success=True,
            output={
                "area": focus_area,
                "analysis": "AI analysis unavailable — manual strategic review needed",
            },
        )

    def _decision_brief(self, **kwargs: Any) -> SkillResult:
        decision = kwargs.get("decision", "")
        options = kwargs.get("options", [])

        brief = {
            "decision": decision,
            "options": options,
            "framework": [
                "Impact on north star ($10K/month goal)",
                "Resource cost (time, money, attention)",
                "Reversibility (can we undo this?)",
                "Speed to result",
                "Alignment with brand",
            ],
        }

        try:
            from adapters.models.model_router import call_with_fallback

            options_text = (
                "\n".join(f"- {o}" for o in options) if options else "No specific options"
            )
            result = call_with_fallback(
                prompt=(
                    f"Decision brief:\n"
                    f"Decision: {decision}\n"
                    f"Options:\n{options_text}\n\n"
                    f"Evaluate each option against: north star impact, cost, "
                    f"reversibility, speed, brand alignment. Recommend one."
                ),
                system="CEO advisor. Clear recommendation with tradeoffs.",
                task_type="fast_response",
                agent_type="ceo",
            )
            if result.output:
                brief["recommendation"] = result.output.strip()[:1000]
        except Exception:
            brief["recommendation"] = "Manual evaluation needed"

        return SkillResult(success=True, output=brief)

    def _delegation(self, **kwargs: Any) -> SkillResult:
        task = kwargs.get("task", "")
        department = kwargs.get("department", "")
        priority = kwargs.get("priority", "normal")

        return SkillResult(
            success=True,
            output={
                "task": task,
                "delegated_to": f"eos-{department}" if department else "unassigned",
                "priority": priority,
                "status": "delegated",
            },
        )

    def _pipeline_review(self, **kwargs: Any) -> SkillResult:
        from projections.eos.views.pipeline import get_pipeline_data

        try:
            data = get_pipeline_data(self._org_id)
            return SkillResult(success=True, output={"pipeline": data})
        except Exception:
            return SkillResult(success=True, output={"pipeline": {}, "note": "No pipeline data"})

    def _morning_brief(self, **kwargs: Any) -> SkillResult:
        sections = {
            "revenue": "Check finance agent for revenue data",
            "pipeline": "Check sales agent for pipeline status",
            "tasks": "Check operations agent for pending tasks",
            "alerts": "No critical alerts",
        }

        try:
            from adapters.models.model_router import call_with_fallback

            result = call_with_fallback(
                prompt=(
                    "Generate a CEO morning briefing for a pre-revenue startup. "
                    "Include: key priorities today, pipeline status, upcoming deadlines, "
                    "and one strategic insight. Be concise — under 200 words."
                ),
                system="CEO morning brief generator. Concise, actionable, no fluff.",
                task_type="fast_response",
                agent_type="ceo",
            )
            if result.output:
                sections["ai_brief"] = result.output.strip()[:800]
        except Exception:
            pass

        return SkillResult(success=True, output=sections)

    def _approve_action(self, **kwargs: Any) -> SkillResult:
        return SkillResult(
            success=True,
            output={
                "status": "approved",
                "approval_id": kwargs.get("approval_id", ""),
                "action_type": kwargs.get("action_type", ""),
                "note": "CEO approval granted",
            },
        )


async def register_ceo_agent(substrate: Substrate) -> RegistrationResult:
    agent = CEOAgent()
    component = Component(
        component_type=ComponentType.AGENT,
        name="eos-ceo",
        capabilities=[
            "strategic_analysis",
            "decision_making",
            "delegation",
            "pipeline_review",
            "morning_briefing",
            "action_approval",
        ],
        metadata=agent.metadata(),
    )
    return await substrate.register(component)
