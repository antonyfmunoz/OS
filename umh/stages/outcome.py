"""Stage 5c: Outcome evaluation + signal attribution."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from umh.execution.stages import StageContext

_log = logging.getLogger(__name__)


@dataclass(frozen=True)
class OutcomeEvaluationStage:
    name: str = "outcome_evaluation"
    description: str = "Evaluate response quality and route signals for world model"
    dependencies: tuple[str, ...] = ("stage_filter",)
    can_abort: bool = False

    def run(self, context: StageContext) -> StageContext:
        if not context.response or context.response.startswith("[ExecutionSpine]"):
            return context

        try:
            from umh.feedback.outcome_evaluator import evaluate_outcome
            from umh.runtime_engine.signal_router import route_signals

            context.evaluation = evaluate_outcome(
                input_text=context.original_message,
                output_text=context.response,
                context={
                    "agent_type": context.agent_type,
                    "venture_id": context.venture_id or "",
                    "task_type": str(context.task_type)
                    if context.task_type
                    else "unknown",
                },
                metadata={
                    "model_used": context.model_used,
                    "iterations": context.iterations,
                    "was_enhanced": context.was_enhanced,
                },
            )
            context.signals = route_signals(context.evaluation)
            _log.debug(
                "Evaluation: score=%.2f confidence=%.2f flags=%s wm=%s",
                context.evaluation["quality_score"],
                context.evaluation["confidence"],
                context.evaluation["flags"],
                "routed" if context.signals.world_model else "gated",
            )
        except Exception as e:
            _log.debug("Outcome evaluation skipped: %s", e)
        return context
