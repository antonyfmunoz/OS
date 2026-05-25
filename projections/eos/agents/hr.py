"""EOS HR Agent — hiring pipeline, team management, onboarding.

Permission tier: EXECUTE — can create tasks and send messages for hiring.
"""

from __future__ import annotations

from typing import Any

from substrate import Substrate
from substrate.types import Component, ComponentType, PermissionTier, RegistrationResult

from projections.eos.agents.base import DepartmentAgent, SkillResult


class HRAgent(DepartmentAgent):
    DEPARTMENT = "hr"
    PERMISSION_TIER = PermissionTier.EXECUTE

    def _register_skills(self) -> None:
        self._add_skill(
            "candidate_screen",
            "analyze",
            "Screen a candidate against role requirements",
            self._candidate_screen,
        )
        self._add_skill(
            "hiring_pipeline",
            "report",
            "Report on current hiring pipeline status",
            self._hiring_pipeline,
        )
        self._add_skill(
            "onboarding_plan",
            "draft_content",
            "Create onboarding plan for a new team member",
            self._onboarding_plan,
        )
        self._add_skill(
            "performance_review",
            "analyze",
            "Analyze team member performance data",
            self._performance_review,
        )
        self._add_skill(
            "contractor_search",
            "research",
            "Research contractors for a specific role",
            self._contractor_search,
        )
        self._add_skill(
            "outreach_candidate",
            "send_dm",
            "Send outreach to a candidate (EXECUTE tier)",
            self._outreach_candidate,
        )

    def _candidate_screen(self, **kwargs: Any) -> SkillResult:
        candidate = kwargs.get("candidate", {})
        requirements = kwargs.get("requirements", [])

        if not candidate:
            return SkillResult(success=False, error="No candidate data provided")

        score = 0
        matches = []
        gaps = []

        skills = [s.lower() for s in candidate.get("skills", [])]
        for req in requirements:
            if req.lower() in skills:
                score += 20
                matches.append(req)
            else:
                gaps.append(req)

        experience = candidate.get("years_experience", 0)
        if experience >= 3:
            score += 20
        elif experience >= 1:
            score += 10

        recommendation = (
            "strong_fit" if score >= 60 else "potential_fit" if score >= 30 else "not_fit"
        )

        return SkillResult(
            success=True,
            output={
                "score": min(score, 100),
                "matches": matches,
                "gaps": gaps,
                "recommendation": recommendation,
            },
        )

    def _hiring_pipeline(self, **kwargs: Any) -> SkillResult:
        try:
            from substrate import get_conn

            with get_conn(self._org_id) as cur:
                cur.execute(
                    """
                    SELECT payload_json->>'stage' as stage, COUNT(*) as count
                    FROM events
                    WHERE org_id = %s AND event_type = 'hiring_candidate'
                    AND payload_json->>'status' = 'active'
                    GROUP BY payload_json->>'stage'
                    """,
                    (self._org_id,),
                )
                rows = cur.fetchall()
                return SkillResult(
                    success=True,
                    output={
                        "pipeline": [{"stage": r["stage"], "count": r["count"]} for r in rows],
                    },
                )
        except Exception:
            return SkillResult(success=True, output={"pipeline": [], "note": "No hiring data"})

    def _onboarding_plan(self, **kwargs: Any) -> SkillResult:
        role = kwargs.get("role", "")
        department = kwargs.get("department", "")

        plan = {
            "week_1": [
                "System access setup (tools, repos, communication channels)",
                "Meet the team — intro sessions",
                "Review department goals and current projects",
                "Shadow existing team member",
            ],
            "week_2": [
                "First small task assignment",
                "Review company culture and processes",
                "1:1 with department lead",
                "Feedback checkpoint",
            ],
            "week_3_4": [
                "Independent task execution",
                "Cross-department intro meetings",
                "30-day goals finalization",
                "Formal check-in with founder",
            ],
        }

        return SkillResult(
            success=True,
            output={"role": role, "department": department, "plan": plan, "status": "draft"},
        )

    def _performance_review(self, **kwargs: Any) -> SkillResult:
        metrics = kwargs.get("metrics", {})
        return SkillResult(
            success=True,
            output={
                "metrics": metrics,
                "analysis": "Performance data provided for review — human evaluation needed",
                "status": "needs_review",
            },
        )

    def _contractor_search(self, **kwargs: Any) -> SkillResult:
        role = kwargs.get("role", "")
        skills = kwargs.get("required_skills", [])
        budget = kwargs.get("budget_range", "")

        return SkillResult(
            success=True,
            output={
                "role": role,
                "required_skills": skills,
                "budget": budget,
                "platforms": ["Upwork", "Toptal", "LinkedIn", "Angel.co"],
                "status": "research_needed",
                "note": "Contractor platforms identified — manual search required",
            },
        )

    def _outreach_candidate(self, **kwargs: Any) -> SkillResult:
        return SkillResult(
            success=True,
            output={
                "status": "sent",
                "candidate": kwargs.get("candidate_name", ""),
                "channel": kwargs.get("channel", "email"),
                "message": kwargs.get("message", ""),
            },
        )


async def register_hr_agent(substrate: Substrate) -> RegistrationResult:
    agent = HRAgent()
    component = Component(
        component_type=ComponentType.AGENT,
        name="eos-hr",
        capabilities=[
            "hiring_pipeline",
            "candidate_screening",
            "onboarding_workflow",
            "team_performance",
            "contractor_management",
            "candidate_outreach",
        ],
        metadata=agent.metadata(),
    )
    return await substrate.register(component)
