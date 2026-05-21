"""Stage 2: Prompt enhancement — expand short prompts into precise form."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from umh.execution.stages import StageContext

_log = logging.getLogger(__name__)

_GREETING_SIGNALS = [
    "hey",
    "hi",
    "hello",
    "morning",
    "good morning",
    "gm",
    "what's up",
    "whats up",
    "sup",
    "yo",
    "how are",
    "how's it",
    "hows it",
    "what's going on",
    "wassup",
    "good evening",
    "good afternoon",
    "evening",
    "night",
]


def enhance_prompt(
    prompt: str,
    ctx: object,
    runtime: object | None = None,
) -> str:
    """Expand short/ambiguous prompts into precise, actionable form.

    Uses trust-adjusted thresholds from UserModel and falls back to
    a generic Haiku expansion.  Greetings are never enhanced.
    """
    _p = prompt.lower().strip().rstrip("?!.")
    if any(
        _p == g or _p.startswith(g + " ") or _p.startswith(g + ",")
        for g in _GREETING_SIGNALS
    ):
        return prompt

    try:
        from umh.runtime_engine.user_model import UserModel

        _um = UserModel(ctx)
        _trust = _um.get_trust_level()
        threshold = max(5, 15 - (_trust * 2))
    except Exception:
        threshold = 15

    if len(prompt.split()) >= threshold:
        return prompt

    try:
        from umh.runtime_engine.user_model import UserModel

        um = UserModel(ctx)
        expanded = um.get_intent_expansion(prompt)
        if expanded != prompt:
            return expanded
    except Exception:
        pass

    if runtime is None:
        return prompt
    try:
        from umh.runtime_engine.agent_runtime import TaskType

        _ctx_hint = (
            "Business context: Lyfe Institute (Initiate Arena, $750, "
            "90-day program, men 18-25). "
            "Empyrean Creative (AI infrastructure, creative studio). "
            "DEX is the name of the AI Executive Assistant — "
            "never expand DEX as decentralized exchange. "
            "Founder: Antony Munoz. North star: $10K/month. Stage 1 validation.\n\n"
        )
        enhancement = runtime.run(
            task_type=TaskType.CLASSIFY,
            prompt=(
                _ctx_hint + "You are expanding a founder's shorthand message into a "
                "precise, actionable execution prompt for their AI EA. "
                "Preserve the original intent exactly. Do not add unrelated "
                "context. Return ONLY the expanded prompt, nothing else:\n\n" + prompt
            ),
            agent="prompt_engine",
        )
        expanded = enhancement.output.strip()
        return expanded if expanded else prompt
    except Exception:
        return prompt


@dataclass(frozen=True)
class PromptEnhancementStage:
    name: str = "prompt_enhancement"
    description: str = "Trust-adjusted prompt expansion via UserModel or Haiku"
    dependencies: tuple[str, ...] = ("authority_check",)
    can_abort: bool = False

    def run(self, context: StageContext) -> StageContext:
        try:
            from umh.runtime_engine.agent_runtime import AgentRuntime

            context.runtime = AgentRuntime()
        except Exception as e:
            _log.warning("AgentRuntime init failed, skipping enhancement: %s", e)

        context.original_message = context.message

        enhanced = enhance_prompt(context.message, context.ctx, context.runtime)
        context.was_enhanced = enhanced != context.message
        context.message = enhanced

        return context
