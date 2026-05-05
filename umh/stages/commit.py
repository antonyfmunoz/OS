"""Stage 6: Commit — persist the winning response (memory, knowledge, feedback, world model)."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from umh.execution.stages import StageContext

_log = logging.getLogger(__name__)


# ── Re-derived commit helpers ───────────────────────────────────────────────
# Each function below was extracted from execution_spine.py and re-derived
# here as a self-contained unit.  Zero imports from execution_spine.


def integrate_knowledge(
    message: str,
    response: str,
    ctx: object,
    agent: str = "system",
    task_type: str = "unknown",
    source: str = "spine_conversation",
) -> None:
    """Permanently integrate conversation into the knowledge base."""
    try:
        from umh.runtime_engine.knowledge_integrator import KnowledgeIntegrator
        from datetime import datetime, timezone as _tz

        _ki = KnowledgeIntegrator(ctx)
        if message and response:
            _ki.integrate(
                content=(
                    f"Conversation:\nFounder: {message[:500]}\nSystem: {response[:500]}"
                ),
                source=source,
                category="conversation",
                metadata={
                    "task_type": task_type,
                    "agent": agent,
                    "timestamp": datetime.now(_tz.utc).isoformat(),
                },
            )
    except Exception as e:
        _log.debug("Knowledge integration skipped: %s", e)


def log_feedback(
    message: str,
    response: str,
    ctx: object,
    venture_id: str = "",
    evaluation: dict | None = None,
) -> None:
    """Log actionable advice as recommendation; detect outcome reports in user message."""
    try:
        from umh.runtime_engine.feedback_loop import FeedbackLoop

        _fl = FeedbackLoop(ctx)

        if response and any(
            signal in response.lower()
            for signal in [
                "send",
                "do this",
                "focus on",
                "action:",
                "next step",
                "today:",
                "one thing:",
                "start with",
            ]
        ):
            _fl.log_recommendation(
                content=response[:500],
                venture_id=venture_id,
                context=message[:200],
                evaluation=evaluation,
            )

        if message:
            _fl.log_outcome(text=message, venture_id=venture_id)
    except Exception as e:
        _log.debug("Feedback loop skipped: %s", e)


def update_world_model(
    message: str,
    response: str,
    org_id: str,
    evaluation: dict | None = None,
    world_model_signal: object | None = None,
) -> None:
    """Write interaction observations to the instance world model."""
    try:
        from umh.world.model import WorldModel

        if world_model_signal is None and evaluation is None:
            return

        if world_model_signal is not None:
            outcome = world_model_signal.outcome
        elif evaluation:
            score = evaluation.get("quality_score", 0.5)
            confidence = evaluation.get("confidence", 0.5)
            from umh.runtime_engine.signal_router import WORLD_MODEL_CONFIDENCE_THRESHOLD

            if confidence < WORLD_MODEL_CONFIDENCE_THRESHOLD:
                return
            outcome = None
            if score >= 0.7:
                outcome = "good"
            elif score < 0.4:
                outcome = "poor"
        else:
            return

        _wm = WorldModel(org_id=org_id)
        _wm.update_from_interaction(message, response, outcome=outcome)
    except Exception as e:
        _log.debug("World model update skipped: %s", e)


def log_reflection(
    message: str,
    iterations: int,
    agent: str,
    ctx: object,
) -> None:
    """Log cognitive reflection when quality loop required multiple iterations."""
    if iterations <= 1:
        return
    try:
        from umh.runtime_engine.memory import AgentMemory

        mem = AgentMemory()
        mem.log_event(
            org_id=ctx.org_id,
            event_type="cognitive_reflection",
            payload={
                "prompt": message[:200],
                "insight": (
                    f"Required {iterations} iterations. "
                    "Prompt may benefit from more specificity."
                ),
                "iterations": iterations,
                "agent": agent,
            },
        )
    except Exception as e:
        _log.debug("Reflection logging skipped: %s", e)


# ── Stage class ─────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class CommitStage:
    name: str = "commit"
    description: str = "Persist winning response via commit_pipeline (stages 6-10)"
    dependencies: tuple[str, ...] = ("outcome_evaluation",)
    can_abort: bool = False

    def run(self, context: StageContext) -> StageContext:
        from umh.runtime_engine.commit_pipeline import commit_winner

        commit_winner(
            message=context.original_message,
            response=context.response,
            ctx=context.ctx,
            agent_type=context.agent_type,
            session_id=context.session_id,
            channel_id=context.channel_id,
            org_id=context.org_id,
            task_type=context.task_type,
            venture_id=context.venture_id,
            skill_name=context.skill_name,
            evaluation=context.evaluation,
            world_model_signal=context.signals.world_model if context.signals else None,
            model_used=context.model_used,
            tokens_used=context.tokens_used,
            iterations=context.iterations,
        )
        return context
