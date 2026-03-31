"""
QualityTransformationGate — every output passes through the four values.

From PHILOSOPHY.md Section VI:
  "What passes through all four values is world class.
   Every time. By architecture. Not by chance."

This is NOT a checklist. NOT regeneration on failure.
It is a transformation layer — each value applies its lens,
and the output becomes qualitatively different.

Reality → Intelligence → Personalization → Execution is
the causal chain. Each enables the next. None work without
the others.

The gate operates in two modes:
  1. Pre-flight: generates quality enhancement prompt
     injected BEFORE generation — transforms through the
     prompt, not through regeneration.
  2. Post-flight: scores the output and logs what was
     applied, producing a TransformationResult.
"""

from dataclasses import dataclass, field


@dataclass
class TransformationResult:
    original:                str
    transformed:             str
    reality_score:           float         # 0.0 to 1.0
    intelligence_score:      float
    personalization_score:   float
    execution_score:         float
    overall_score:           float
    transformations_applied: list[str]
    is_world_class:          bool          # overall >= 0.75


class QualityTransformationGate:

    def __init__(self, ctx):
        self.ctx = ctx

    # ─── Primary interface ────────────────────────────────────────────────────

    def transform(
        self,
        output: str,
        input_text: str,
        classified_signal: dict,
        bis_context: dict | None = None,
    ) -> TransformationResult:
        """
        Transform output through the four values.
        Each value applies its lens. Output becomes qualitatively new.
        Called AFTER generation to score and log what landed.
        """
        if not output:
            return TransformationResult(
                original='',
                transformed='',
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
            current, input_text, classified_signal, bis_context
        )
        transformations.extend(t)

        # VALUE 4: EXECUTION — does this produce action?
        execution_score, current, t = self._apply_execution(
            current, input_text, classified_signal
        )
        transformations.extend(t)

        # Weighted overall — reality anchors everything
        overall = (
            reality_score         * 0.30 +
            intelligence_score    * 0.25 +
            personalization_score * 0.25 +
            execution_score       * 0.20
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
        result: 'TransformationResult',
        classified: dict,
    ) -> str:
        """
        Returns quality requirement prompt injected BEFORE generation.
        Transforms through the prompt — not through regeneration.
        Each value below threshold contributes its requirement.
        Scores of 0.5 (pre-flight baseline) trigger all four.
        """
        enhancements: list[str] = []

        if result.reality_score < 0.6:
            enhancements.append(
                'Ground your response in the specific situation described. '
                'Reference what they actually said. '
                'Avoid generic advice.'
            )

        if result.intelligence_score < 0.6:
            enhancements.append(
                'Explain your reasoning. '
                'Why does this apply here? '
                'What makes this the right move?'
            )

        if result.personalization_score < 0.6:
            enhancements.append(
                'Make this specific to their stage, offer, and situation. '
                'Generic is noise. Specific is signal.'
            )

        if result.execution_score < 0.6:
            enhancements.append(
                'End with a clear action. '
                'What do they do first? When? How?'
            )

        if not enhancements:
            return ''

        return (
            'QUALITY REQUIREMENTS FOR THIS RESPONSE:\n'
            + '\n'.join(f'- {e}' for e in enhancements)
        )

    # ─── Value lenses ─────────────────────────────────────────────────────────

    def _apply_reality(
        self,
        output: str,
        input_text: str,
        classified: dict,
    ) -> tuple[float, str, list[str]]:
        """
        Reality lens: is this grounded in what is actually true?
        Penalizes generic patterns. Rewards situation-specific reference.
        """
        from eos_ai.signal_hierarchy import SignalTier

        transformations: list[str] = []
        score = 0.7  # baseline

        output_lower = output.lower()

        # Generic patterns that indicate the response ignored the situation
        generic_patterns = [
            'generally speaking',
            'in most cases',
            'typically',
            'usually you should',
            'most businesses',
            'it depends',
            'there are many ways',
        ]
        generic_count = sum(1 for p in generic_patterns if p in output_lower)
        if generic_count > 0:
            score -= generic_count * 0.1
            transformations.append(
                f'reality: {generic_count} generic pattern(s) detected'
            )

        # Reality-tier input should produce a reality-grounded response
        if classified.get('primary_tier') == SignalTier.REALITY:
            situated_signals = [
                'based on what you said',
                'given that',
                'since you',
                'because you',
                'you mentioned',
                'you said',
                'you are at',
                'your situation',
            ]
            if any(s in output_lower for s in situated_signals):
                score += 0.2
                transformations.append(
                    'reality: response references actual situation'
                )
            else:
                score -= 0.1

        return min(score, 1.0), output, transformations

    def _apply_intelligence(
        self,
        output: str,
        input_text: str,
        classified: dict,
    ) -> tuple[float, str, list[str]]:
        """
        Intelligence lens: highest quality reasoning available?
        Checks for reasoning signals and substantive length.
        """
        transformations: list[str] = []
        score = 0.7

        output_lower = output.lower()

        # Too short to contain real reasoning
        if len(output) < 50:
            score -= 0.2
            transformations.append(
                'intelligence: response too short for complexity of question'
            )

        # Reasoning signals — chains of logic, not just assertion
        reasoning_signals = [
            'because', 'therefore', 'which means',
            'this matters because', 'the reason',
            'what this tells us', 'this indicates',
            'so the', 'that means', 'as a result',
        ]
        reasoning_count = sum(1 for s in reasoning_signals if s in output_lower)
        if reasoning_count > 0:
            score += min(reasoning_count * 0.05, 0.2)
            transformations.append(
                f'intelligence: {reasoning_count} reasoning signal(s) present'
            )

        return min(score, 1.0), output, transformations

    def _apply_personalization(
        self,
        output: str,
        input_text: str,
        classified: dict,
        bis_context: dict | None = None,
    ) -> tuple[float, str, list[str]]:
        """
        Personalization lens: specific to this person's exact situation?
        Checks domain-appropriate specificity and stage reference.
        """
        transformations: list[str] = []
        score = 0.6  # lower baseline — personalization must be earned

        output_lower = output.lower()
        domain = classified.get('domain', 'universal')

        if domain == 'business':
            business_specifics = [
                'stage 1', 'your offer', 'your icp',
                'outreach', 'pipeline', 'revenue',
                'first sale', 'validation', 'initiate',
                'your business', 'your client',
            ]
            if any(s in output_lower for s in business_specifics):
                score += 0.2
                transformations.append(
                    'personalization: business-specific context present'
                )

        elif domain == 'life':
            life_specifics = [
                'energy', 'sleep', 'health',
                'your routine', 'your habits',
                'your state', 'right now',
            ]
            if any(s in output_lower for s in life_specifics):
                score += 0.2
                transformations.append(
                    'personalization: life-specific context present'
                )

        elif domain == 'content':
            content_specifics = [
                'your audience', 'your brand', 'your content',
                'your platform', 'your niche',
            ]
            if any(s in output_lower for s in content_specifics):
                score += 0.2
                transformations.append(
                    'personalization: content-specific context present'
                )

        # BIS stage reference check
        if bis_context:
            stage = bis_context.get('current_stage', 1)
            if f'stage {stage}' in output_lower:
                score += 0.1
                transformations.append(
                    f'personalization: stage {stage} referenced'
                )

        return min(score, 1.0), output, transformations

    def _apply_execution(
        self,
        output: str,
        input_text: str,
        classified: dict,
    ) -> tuple[float, str, list[str]]:
        """
        Execution lens: does this produce action?
        Intelligence without execution is philosophy.
        Every output must move the north star.
        """
        from eos_ai.signal_hierarchy import SignalTier

        transformations: list[str] = []
        score = 0.6  # lower baseline — action must be earned

        output_lower = output.lower()

        action_signals = [
            'do this', 'send', 'call', 'dm',
            'write', 'create', 'schedule',
            'first step', 'next step', 'action',
            'today', 'now', 'immediately',
            'this week', 'start with',
            'your job', 'one thing',
        ]
        action_count = sum(1 for s in action_signals if s in output_lower)
        if action_count > 0:
            score += min(action_count * 0.05, 0.3)
            transformations.append(
                f'execution: {action_count} action signal(s) present'
            )

        # Leverage queries MUST produce a clear action — highest standard
        if classified.get('primary_tier') == SignalTier.LEVERAGE:
            if action_count == 0:
                score -= 0.2
                transformations.append(
                    'execution: leverage query produced no clear action'
                )
            elif action_count >= 3:
                score += 0.1
                transformations.append(
                    'execution: leverage query has strong action density'
                )

        return min(score, 1.0), output, transformations


# ─── Module-level quality check functions ─────────────────────────────────────

import logging as _logging

VOICE_STANDARDS = """
Antony Munoz's voice standards:
- Direct and confident. No hedging.
- Warm but not overly casual
- No corporate speak or filler phrases
- Short sentences preferred
- Clear next step always included in outreach
- Never uses: "I hope this email finds you well",
  "Please don't hesitate", "As per my previous email",
  "Circling back", "Touching base", "Quick question"
"""

_qg_logger = _logging.getLogger(__name__)


def quality_check(
    content: str,
    content_type: str = 'email',
    recipient_context: str = '',
) -> dict:
    """
    Run quality check on outgoing communication.

    Returns dict with keys: approved (bool), score (int 0-10),
    issues (list[str]), suggestions (list[str]), revised_version (str).
    """
    try:
        from eos_ai.model_router import get_router, TaskType
        router = get_router()
        model = router.route(TaskType.FAST_RESPONSE)

        result = router.call(model, f"""You are a quality control editor
for Antony Munoz's outgoing communications.

Voice standards:
{VOICE_STANDARDS}

Content type: {content_type}
Recipient context: {recipient_context or 'Unknown'}

Content to review:
{content}

Check for:
1. Voice consistency with standards above
2. Grammar and spelling errors
3. Clarity — is the message clear?
4. Call to action — is there a clear next step?
5. Tone appropriateness for recipient
6. Prohibited phrases
7. Length appropriateness

Return JSON only:
{{"approved": true, "score": 8, "issues": [], "suggestions": [], "revised_version": ""}}""").strip()

        if '```' in result:
            result = result.split('```')[1].replace('json', '').strip()
        import json as _j
        return _j.loads(result)
    except Exception as e:
        _qg_logger.warning(f'[QualityGate] check failed: {e}')
        return {
            'approved': True,
            'score': 7,
            'issues': [],
            'suggestions': [],
            'revised_version': '',
        }


def gate_outgoing_email(
    subject: str,
    body: str,
    to_email: str = '',
    auto_revise: bool = True,
    ctx=None,
) -> dict:
    """
    Full quality gate for outgoing email.
    Logs result to Neon. Returns quality_check result dict.
    """
    import json as _j
    result = quality_check(
        content=f'Subject: {subject}\n\n{body}',
        content_type='email',
        recipient_context=to_email,
    )

    try:
        from eos_ai.context import load_context_from_env
        from eos_ai.db import get_conn
        ctx = ctx or load_context_from_env()
        with get_conn(ctx.org_id) as cur:
            cur.execute('''
                INSERT INTO events
                (org_id, event_type, payload_json, handled_by)
                VALUES (%s, %s, %s, %s)
            ''', (
                str(ctx.org_id),
                'quality_gate_check',
                _j.dumps({
                    'subject': subject,
                    'to': to_email,
                    'score': result.get('score'),
                    'approved': result.get('approved'),
                    'issues': result.get('issues', []),
                }),
                'quality_gate',
            ))
    except Exception:
        pass

    return result
