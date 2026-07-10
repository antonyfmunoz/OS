"""Outreach workflow — automated prospect outreach sequence.

Trigger: new lead enters pipeline
Steps: qualify → research → draft DM → review → send
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from projections.eos.workflows.types import WorkflowStep


@dataclass
class OutreachStep:
    name: str
    status: str = "pending"
    output: str = ""


@dataclass
class OutreachResult:
    lead_id: str = ""
    steps: list[OutreachStep] = field(default_factory=list)
    completed: bool = False
    message_draft: str = ""


class OutreachWorkflow:
    """Multi-step outreach workflow for new prospects."""

    STEPS = ["qualify", "research", "draft", "review", "send"]

    def __init__(self, org_id: str = "", venture_id: str = "") -> None:
        self._org_id = org_id
        self._venture_id = venture_id

    def steps(self, lead: dict[str, Any]) -> list[WorkflowStep]:
        """Return governed workflow steps for the WorkflowRunner."""
        self._lead = lead
        self._result = OutreachResult(lead_id=lead.get("id", ""))
        return [
            WorkflowStep(
                name="qualify",
                mutation_name="command_submit",
                intent=f"Qualify lead: {lead.get('name', 'unknown')[:60]}",
                execute_fn=lambda: self._step_qualify(),
            ),
            WorkflowStep(
                name="research",
                mutation_name="command_submit",
                intent=f"Research lead: {lead.get('name', 'unknown')[:60]}",
                execute_fn=lambda: self._step_research(),
            ),
            WorkflowStep(
                name="draft",
                mutation_name="command_submit",
                intent=f"Draft outreach for: {lead.get('name', 'unknown')[:60]}",
                execute_fn=lambda: self._step_draft(),
            ),
        ]

    def _step_qualify(self) -> tuple[str, bool]:
        result = self._qualify(self._lead)
        self._result.steps.append(OutreachStep("qualify", "completed", result))
        if "not qualified" in result.lower():
            return (result, False)
        return (result, True)

    def _step_research(self) -> tuple[str, bool]:
        research = self._research(self._lead)
        self._result.steps.append(OutreachStep("research", "completed", research))
        self._research_output = research
        return (research, True)

    def _step_draft(self) -> tuple[str, bool]:
        research = getattr(self, "_research_output", "")
        draft = self._draft_message(self._lead, research)
        self._result.steps.append(OutreachStep("draft", "completed", draft))
        self._result.message_draft = draft
        self._result.completed = True
        return (draft, True)

    def execute(self, lead: dict[str, Any]) -> OutreachResult:
        """Run the full outreach workflow for a lead."""
        result = OutreachResult(lead_id=lead.get("id", ""))

        qualified = self._qualify(lead)
        result.steps.append(OutreachStep("qualify", "completed", qualified))
        if "not qualified" in qualified.lower():
            return result

        research = self._research(lead)
        result.steps.append(OutreachStep("research", "completed", research))

        draft = self._draft_message(lead, research)
        result.steps.append(OutreachStep("draft", "completed", draft))
        result.message_draft = draft

        result.steps.append(OutreachStep("review", "pending_approval"))
        result.completed = True
        return result

    def _qualify(self, lead: dict[str, Any]) -> str:
        """Deterministic lead qualification. ICP age bands come from tenant BIS."""
        from projections.eos import instance

        score = 0
        if lead.get("source") in ("instagram", "referral", "event"):
            score += 30
        target_ages = instance.icp_age_ranges(
            instance.load_bis(self._org_id, self._venture_id)
        )
        if target_ages and lead.get("age_range") in target_ages:
            score += 20
        if lead.get("engagement"):
            score += 15
        if lead.get("expressed_interest"):
            score += 25

        if score >= 50:
            return f"Qualified (score: {score})"
        return f"Not qualified (score: {score})"

    def _research(self, lead: dict[str, Any]) -> str:
        """Build context about the lead."""
        parts = []
        if lead.get("bio"):
            parts.append(f"Bio: {lead['bio'][:200]}")
        if lead.get("interests"):
            parts.append(f"Interests: {', '.join(lead['interests'][:5])}")
        if lead.get("pain_points"):
            parts.append(f"Pain points: {', '.join(lead['pain_points'][:3])}")
        return " | ".join(parts) or "No additional research data"

    def _draft_message(self, lead: dict[str, Any], research: str) -> str:
        """Draft outreach message. Deterministic template, AI-enhanced when available."""
        name = lead.get("name", "there")
        hook = lead.get("expressed_interest", "self-improvement")

        template = (
            f"Hey {name} — I noticed your interest in {hook}. "
            f"I work with {lead.get('demographic', 'people')} who want to "
            f"build real structure in their lives. Would be down to chat about "
            f"what you're working on. No pressure — just a conversation."
        )

        try:
            from adapters.models.model_router import call_with_fallback
            from projections.eos import instance

            _offer = instance.offer_name(
                instance.load_bis(self._org_id, self._venture_id)
            )
            result = call_with_fallback(
                prompt=(
                    f"Personalize this outreach DM based on research:\n"
                    f"Template: {template}\n"
                    f"Research: {research}\n"
                    f"Keep it under 3 sentences. Natural, not salesy."
                ),
                system=f"Write outreach DMs for {_offer}. Voice: direct, authentic, no hype.",
                task_type="fast_response",
            )
            if result.output and len(result.output.strip()) > 20:
                return result.output.strip()[:500]
        except Exception:
            pass

        return template
