"""
QualityGate — every output passes through four value lenses.

This is a transformation layer — each value applies its lens,
and the output becomes qualitatively different.

Reality -> Intelligence -> Personalization -> Execution is
the causal chain.  Each enables the next.  None work without
the others.

The gate operates in two modes:
  1. Pre-flight: generates quality enhancement prompt
     injected BEFORE generation — transforms through the
     prompt, not through regeneration.
  2. Post-flight: scores the output and logs what was
     applied, producing a TransformationResult.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class TransformationResult:
    """Scores and metadata produced by a single quality-gate pass."""

    original: str
    transformed: str
    reality_score: float  # 0.0 to 1.0
    intelligence_score: float
    personalization_score: float
    execution_score: float
    overall_score: float
    transformations_applied: list[str]
    is_world_class: bool  # overall >= 0.75


class QualityGate:
    """Platform-agnostic quality transformation gate.

    Scores and (optionally) transforms LLM output through four
    value lenses: Reality, Intelligence, Personalization, Execution.

    Parameters
    ----------
    ctx : object or None
        Optional runtime context.  Not required for scoring.
    """

    def __init__(self, ctx: object | None = None) -> None:
        self.ctx = ctx

    # ── Primary interface ────────────────────────────────────────────────

    def transform(
        self,
        output: str,
        input_text: str,
        classified_signal: dict,
        stage_context: dict | None = None,
    ) -> TransformationResult:
        """Score *output* through the four value lenses.

        Parameters
        ----------
        output:
            The LLM-generated text to evaluate.
        input_text:
            The original user input that prompted the output.
        classified_signal:
            Dict with at least ``primary_tier`` (str) and
            optionally ``domain`` (str).
        stage_context:
            Optional dict.  If it contains a ``current_stage`` key
            the personalization lens uses it for stage-reference scoring.
        """
        if not output:
            return TransformationResult(
                original="",
                transformed="",
                reality_score=0.0,
                intelligence_score=0.0,
                personalization_score=0.0,
                execution_score=0.0,
                overall_score=0.0,
                transformations_applied=[],
                is_world_class=False,
            )

        transformations: list[str] = []
        current = output

        # VALUE 1: REALITY — is this grounded in what is true?
        reality_score, current, t = self._apply_reality(
            current, input_text, classified_signal
        )
        transformations.extend(t)

        # VALUE 2: INTELLIGENCE — highest quality reasoning?
        intelligence_score, current, t = self._apply_intelligence(
            current, input_text, classified_signal
        )
        transformations.extend(t)

        # VALUE 3: PERSONALIZATION — specific to this person?
        personalization_score, current, t = self._apply_personalization(
            current, input_text, classified_signal, stage_context
        )
        transformations.extend(t)

        # VALUE 4: EXECUTION — does this produce action?
        execution_score, current, t = self._apply_execution(
            current, input_text, classified_signal
        )
        transformations.extend(t)

        # Weighted overall — reality anchors everything
        overall = (
            reality_score * 0.30
            + intelligence_score * 0.25
            + personalization_score * 0.25
            + execution_score * 0.20
        )

        return TransformationResult(
            original=output,
            transformed=current,
            reality_score=reality_score,
            intelligence_score=intelligence_score,
            personalization_score=personalization_score,
            execution_score=execution_score,
            overall_score=round(overall, 3),
            transformations_applied=transformations,
            is_world_class=overall >= 0.75,
        )

    def get_enhancement_prompt(
        self,
        result: TransformationResult,
        classified: dict,
    ) -> str:
        """Return quality-requirement prompt for pre-flight injection.

        Each value below threshold contributes its requirement.
        Returns empty string when all scores are adequate.
        """
        enhancements: list[str] = []

        if result.reality_score < 0.6:
            enhancements.append(
                "Ground your response in the specific situation described. "
                "Reference what they actually said. "
                "Avoid generic advice."
            )

        if result.intelligence_score < 0.6:
            enhancements.append(
                "Explain your reasoning. "
                "Why does this apply here? "
                "What makes this the right move?"
            )

        if result.personalization_score < 0.6:
            enhancements.append(
                "Make this specific to their stage, offer, and situation. "
                "Generic is noise. Specific is signal."
            )

        if result.execution_score < 0.6:
            enhancements.append(
                "End with a clear action. What do they do first? When? How?"
            )

        if not enhancements:
            return ""

        return "QUALITY REQUIREMENTS FOR THIS RESPONSE:\n" + "\n".join(
            f"- {e}" for e in enhancements
        )

    # ── Value lenses ─────────────────────────────────────────────────────

    def _apply_reality(
        self,
        output: str,
        input_text: str,
        classified: dict,
    ) -> tuple[float, str, list[str]]:
        """Reality lens: is this grounded in what is actually true?

        Penalizes generic patterns.  Rewards situation-specific reference.
        """
        transformations: list[str] = []
        score = 0.7  # baseline

        output_lower = output.lower()

        # Generic patterns that indicate the response ignored the situation
        generic_patterns = [
            "generally speaking",
            "in most cases",
            "typically",
            "usually you should",
            "most businesses",
            "it depends",
            "there are many ways",
        ]
        generic_count = sum(1 for p in generic_patterns if p in output_lower)
        if generic_count > 0:
            score -= generic_count * 0.1
            transformations.append(
                f"reality: {generic_count} generic pattern(s) detected"
            )

        # Reality-tier input should produce a reality-grounded response
        if classified.get("primary_tier") == "reality":
            situated_signals = [
                "based on what you said",
                "given that",
                "since you",
                "because you",
                "you mentioned",
                "you said",
                "you are at",
                "your situation",
            ]
            if any(s in output_lower for s in situated_signals):
                score += 0.2
                transformations.append("reality: response references actual situation")
            else:
                score -= 0.1

        return min(score, 1.0), output, transformations

    def _apply_intelligence(
        self,
        output: str,
        input_text: str,
        classified: dict,
    ) -> tuple[float, str, list[str]]:
        """Intelligence lens: highest quality reasoning available?

        Checks for reasoning signals and substantive length.
        """
        transformations: list[str] = []
        score = 0.7

        output_lower = output.lower()

        # Too short to contain real reasoning
        if len(output) < 50:
            score -= 0.2
            transformations.append(
                "intelligence: response too short for complexity of question"
            )

        # Reasoning signals — chains of logic, not just assertion
        reasoning_signals = [
            "because",
            "therefore",
            "which means",
            "this matters because",
            "the reason",
            "what this tells us",
            "this indicates",
            "so the",
            "that means",
            "as a result",
        ]
        reasoning_count = sum(1 for s in reasoning_signals if s in output_lower)
        if reasoning_count > 0:
            score += min(reasoning_count * 0.05, 0.2)
            transformations.append(
                f"intelligence: {reasoning_count} reasoning signal(s) present"
            )

        return min(score, 1.0), output, transformations

    def _apply_personalization(
        self,
        output: str,
        input_text: str,
        classified: dict,
        stage_context: dict | None = None,
    ) -> tuple[float, str, list[str]]:
        """Personalization lens: specific to this person's exact situation?

        Checks domain-appropriate specificity and stage reference.
        """
        transformations: list[str] = []
        score = 0.6  # lower baseline — personalization must be earned

        output_lower = output.lower()
        domain = classified.get("domain", "universal")

        if domain == "business":
            business_specifics = [
                "stage 1",
                "your offer",
                "your icp",
                "outreach",
                "pipeline",
                "revenue",
                "first sale",
                "validation",
                "initiate",
                "your business",
                "your client",
            ]
            if any(s in output_lower for s in business_specifics):
                score += 0.2
                transformations.append(
                    "personalization: business-specific context present"
                )

        elif domain == "life":
            life_specifics = [
                "energy",
                "sleep",
                "health",
                "your routine",
                "your habits",
                "your state",
                "right now",
            ]
            if any(s in output_lower for s in life_specifics):
                score += 0.2
                transformations.append("personalization: life-specific context present")

        elif domain == "content":
            content_specifics = [
                "your audience",
                "your brand",
                "your content",
                "your platform",
                "your niche",
            ]
            if any(s in output_lower for s in content_specifics):
                score += 0.2
                transformations.append(
                    "personalization: content-specific context present"
                )

        # Stage reference check (generic — any context with current_stage)
        if stage_context:
            stage = stage_context.get("current_stage", 1)
            if f"stage {stage}" in output_lower:
                score += 0.1
                transformations.append(f"personalization: stage {stage} referenced")

        return min(score, 1.0), output, transformations

    def _apply_execution(
        self,
        output: str,
        input_text: str,
        classified: dict,
    ) -> tuple[float, str, list[str]]:
        """Execution lens: does this produce action?

        Intelligence without execution is philosophy.
        Every output must move the needle.
        """
        transformations: list[str] = []
        score = 0.6  # lower baseline — action must be earned

        output_lower = output.lower()

        action_signals = [
            "do this",
            "send",
            "call",
            "dm",
            "write",
            "create",
            "schedule",
            "first step",
            "next step",
            "action",
            "today",
            "now",
            "immediately",
            "this week",
            "start with",
            "your job",
            "one thing",
        ]
        action_count = sum(1 for s in action_signals if s in output_lower)
        if action_count > 0:
            score += min(action_count * 0.05, 0.3)
            transformations.append(
                f"execution: {action_count} action signal(s) present"
            )

        # Leverage queries MUST produce a clear action — highest standard
        if classified.get("primary_tier") == "leverage":
            if action_count == 0:
                score -= 0.2
                transformations.append(
                    "execution: leverage query produced no clear action"
                )
            elif action_count >= 3:
                score += 0.1
                transformations.append(
                    "execution: leverage query has strong action density"
                )

        return min(score, 1.0), output, transformations
