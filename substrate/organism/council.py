"""Council — multi-perspective advisory layer for the advisor.

Provides structured review from 7 advisory perspectives for
high-leverage decisions. the advisor convenes the council; the council
is advisory, not authoritative. Governance remains the authority.
The operator remains sovereign.

Thin MVP: single model call with structured role prompting.
Future: multi-model parallel calls per role.

UMH substrate subsystem. Instance-agnostic.
"""

from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class CouncilRole:
    """Assessment from one advisory perspective."""

    role: str
    assessment: str
    concerns: list[str] = field(default_factory=list)
    recommendation: str = "approve"
    confidence: float = 0.5

    def to_dict(self) -> dict[str, Any]:
        return {
            "role": self.role,
            "assessment": self.assessment,
            "concerns": self.concerns,
            "recommendation": self.recommendation,
            "confidence": self.confidence,
        }


@dataclass
class CouncilReview:
    """Full council review with role assessments and consensus."""

    decision_context: str
    proposed_plan: str
    roles: list[CouncilRole] = field(default_factory=list)
    consensus: str = "approve"
    dissenting_points: list[str] = field(default_factory=list)
    risk_summary: str = ""
    required_changes: list[str] = field(default_factory=list)
    final_recommendation: str = ""
    reviewed_at: str = field(
        default_factory=lambda: time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "decision_context": self.decision_context,
            "proposed_plan": self.proposed_plan,
            "roles": [r.to_dict() for r in self.roles],
            "consensus": self.consensus,
            "dissenting_points": self.dissenting_points,
            "risk_summary": self.risk_summary,
            "required_changes": self.required_changes,
            "final_recommendation": self.final_recommendation,
            "reviewed_at": self.reviewed_at,
        }


COUNCIL_ROLES = [
    {
        "role": "product_architect",
        "perspective": "Product intent, UX, roadmap, user value",
        "question": "Does this serve the operator's actual goal?",
    },
    {
        "role": "systems_architect",
        "perspective": "Architecture, integration, scaling, state management",
        "question": "Does this fit the 4-layer architecture? Any dependency violations?",
    },
    {
        "role": "implementation_lead",
        "perspective": "Feasibility, file ownership, workcell sequencing, time budget",
        "question": "Can this actually be built today with current resources?",
    },
    {
        "role": "governance_reviewer",
        "perspective": "Permissions, risk classification, destructive actions, overnight safety",
        "question": "Are approval gates correct? Any governance bypass?",
    },
    {
        "role": "qa_reviewer",
        "perspective": "Tests, acceptance criteria, regression risk, verification completeness",
        "question": "Is verification sufficient? What could slip through?",
    },
    {
        "role": "skeptic",
        "perspective": "Hidden failure modes, scope creep, fake functionality, false confidence",
        "question": "What will break? What looks done but isn't? What's being oversold?",
    },
    {
        "role": "operator_advocate",
        "perspective": "Operator empowerment, friction reduction, daily usability",
        "question": "Does this actually help the human? Or just look impressive?",
    },
]


class Council:
    """Multi-perspective advisory council for high-leverage decisions."""

    def review(
        self,
        decision_context: str,
        proposed_plan: str,
        artifacts: dict[str, Any] | None = None,
    ) -> CouncilReview:
        """Run council review. Thin MVP: single model call with structured prompting.

        Returns structured CouncilReview even if LLM call fails (deterministic fallback).
        """
        prompt = self._build_review_prompt(decision_context, proposed_plan, artifacts)
        raw_response = self._call_model(prompt)
        if raw_response:
            review = self._parse_response(raw_response, decision_context, proposed_plan)
        else:
            review = self._deterministic_fallback(decision_context, proposed_plan)

        self._persist_review(review)
        return review

    def _build_review_prompt(
        self,
        context: str,
        plan: str,
        artifacts: dict[str, Any] | None,
    ) -> str:
        roles_text = "\n".join(
            f"- **{r['role']}** ({r['perspective']}): {r['question']}"
            for r in COUNCIL_ROLES
        )
        artifact_text = ""
        if artifacts:
            artifact_text = (
                f"\n\nArtifacts:\n{json.dumps(artifacts, indent=2, default=str)[:2000]}"
            )

        return (
            "You are a council of 7 advisory roles reviewing a decision "
            "for UMH (Universal Mastery Hierarchy).\n\n"
            f"Decision context:\n{context[:2000]}\n\n"
            f"Proposed plan:\n{plan[:3000]}\n"
            f"{artifact_text}\n\n"
            "For each role below, provide: assessment (1-2 sentences), "
            "concerns (list), recommendation (approve/revise/block), "
            "confidence (0.0-1.0).\n\n"
            f"Roles:\n{roles_text}\n\n"
            "After all roles, provide:\n"
            "- consensus: approve/revise/block (majority vote)\n"
            "- dissenting_points: list of unresolved concerns\n"
            "- risk_summary: one paragraph\n"
            "- required_changes: list (empty if approve)\n"
            "- final_recommendation: one paragraph\n\n"
            "Respond in JSON format:\n"
            '{"roles": [{"role": "...", "assessment": "...", "concerns": '
            '[...], "recommendation": "...", "confidence": 0.0}], '
            '"consensus": "...", "dissenting_points": [...], '
            '"risk_summary": "...", "required_changes": [...], '
            '"final_recommendation": "..."}'
        )

    def _call_model(self, prompt: str) -> str | None:
        """Call best available model for council review."""
        try:
            from adapters.models.model_router import call_with_fallback

            result = call_with_fallback(
                prompt=prompt,
                agent_type="ceo",
                force_opus=True,
            )
            return result if result else None
        except Exception as exc:
            logger.warning("council model call failed: %s", exc)
            return None

    def _parse_response(
        self,
        raw: str,
        context: str,
        plan: str,
    ) -> CouncilReview:
        """Parse LLM JSON response into CouncilReview."""
        try:
            # Extract JSON from response (may have markdown wrapping)
            json_str = raw
            if "```json" in raw:
                json_str = raw.split("```json")[1].split("```")[0]
            elif "```" in raw:
                json_str = raw.split("```")[1].split("```")[0]

            data = json.loads(json_str)
            roles = [
                CouncilRole(
                    role=r.get("role", "unknown"),
                    assessment=r.get("assessment", ""),
                    concerns=r.get("concerns", []),
                    recommendation=r.get("recommendation", "approve"),
                    confidence=float(r.get("confidence", 0.5)),
                )
                for r in data.get("roles", [])
            ]
            return CouncilReview(
                decision_context=context[:500],
                proposed_plan=plan[:500],
                roles=roles,
                consensus=data.get("consensus", "approve"),
                dissenting_points=data.get("dissenting_points", []),
                risk_summary=data.get("risk_summary", ""),
                required_changes=data.get("required_changes", []),
                final_recommendation=data.get("final_recommendation", ""),
            )
        except (json.JSONDecodeError, KeyError, TypeError) as exc:
            logger.warning("council response parse failed: %s", exc)
            return self._deterministic_fallback(context, plan)

    def _deterministic_fallback(self, context: str, plan: str) -> CouncilReview:
        """Fallback when LLM is unavailable — deterministic role assessments."""
        roles = [
            CouncilRole(
                role=r["role"],
                assessment=(
                    f"Deterministic review from {r['perspective']} perspective. "
                    "LLM unavailable."
                ),
                concerns=[
                    f"Unable to perform deep {r['role']} analysis without LLM."
                ],
                recommendation="revise",
                confidence=0.3,
            )
            for r in COUNCIL_ROLES
        ]
        return CouncilReview(
            decision_context=context[:500],
            proposed_plan=plan[:500],
            roles=roles,
            consensus="revise",
            dissenting_points=[
                "LLM unavailable — council operated in deterministic fallback mode."
            ],
            risk_summary=(
                "Council review ran without LLM. "
                "Recommendations are conservative defaults."
            ),
            required_changes=[
                "Re-run council review when LLM is available for full analysis."
            ],
            final_recommendation=(
                "Proceed with caution. "
                "Council review was deterministic fallback only."
            ),
        )

    def _persist_review(self, review: CouncilReview) -> None:
        """Persist council review to journal."""
        try:
            journal_path = os.path.join(
                os.environ.get("UMH_ROOT", "/opt/OS"),
                "data",
                "umh",
                "organism",
                "council_reviews.jsonl",
            )
            os.makedirs(os.path.dirname(journal_path), exist_ok=True)
            with open(journal_path, "a") as f:
                f.write(json.dumps(review.to_dict()) + "\n")
        except Exception as exc:
            logger.debug("council review persistence failed: %s", exc)
