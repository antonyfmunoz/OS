"""Outreach workflow — automated prospect outreach sequence.

Trigger: new lead enters pipeline
Steps: qualify → research → draft DM → review → send
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


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
        """Deterministic lead qualification."""
        score = 0
        if lead.get("source") in ("instagram", "referral", "event"):
            score += 30
        if lead.get("age_range") in ("18-25", "25-35"):
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
            f"I work with {lead.get('demographic', 'young men')} who want to "
            f"build real structure in their lives. Would be down to chat about "
            f"what you're working on. No pressure — just a conversation."
        )

        try:
            from adapters.models.model_router import call_with_fallback

            result = call_with_fallback(
                prompt=(
                    f"Personalize this outreach DM based on research:\n"
                    f"Template: {template}\n"
                    f"Research: {research}\n"
                    f"Keep it under 3 sentences. Natural, not salesy."
                ),
                system="Write outreach DMs for Initiate Arena. Voice: direct, authentic, no hype.",
                task_type="fast_response",
            )
            if result.output and len(result.output.strip()) > 20:
                return result.output.strip()[:500]
        except Exception:
            pass

        return template
