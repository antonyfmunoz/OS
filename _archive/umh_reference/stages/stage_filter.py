"""Stage 5b: Stage filter — guard against premature advice."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from umh.execution.stages import StageContext

_log = logging.getLogger(__name__)


def apply_stage_filter(output: str, ctx: object, venture_id: str | None) -> str:
    """Prepend stage-appropriate correction if the response contains
    premature advice for the current business stage.
    """
    try:
        from umh.runtime_engine.primitives import ContextualReasoningEngine

        _cre = ContextualReasoningEngine(ctx)
        _stage_ctx = _cre.get_current_context(venture_id or "")
        _advice_triggers = [
            "hire",
            "build a team",
            "outsource",
            "automate outreach",
            "run paid",
            "launch ads",
            "paid ads",
            "scale",
            "raise",
            "invest",
            "expand",
        ]
        _resp_lower = output.lower()
        _premature = [t for t in _advice_triggers if t in _resp_lower]
        if _premature and _stage_ctx.get("stage") == 1:
            _eval = _cre.evaluate_principle(
                f"Advice about: {', '.join(_premature)}", _stage_ctx
            )
            if not _eval.get("applies", True):
                _warning = (
                    f"⚠️ Stage check: {_eval.get('warning', '')}\n"
                    f"What applies now: "
                    f"{_eval.get('what_applies_instead', '')}\n\n"
                )
                return _warning + output
    except Exception:
        pass
    return output


@dataclass(frozen=True)
class StageFilterStage:
    name: str = "stage_filter"
    description: str = "Prepend stage-appropriate correction for premature advice"
    dependencies: tuple[str, ...] = ("quality_verification",)
    can_abort: bool = False

    def run(self, context: StageContext) -> StageContext:
        if not context.response or context.response.startswith("[ExecutionSpine]"):
            return context

        context.response = apply_stage_filter(
            context.response,
            context.ctx,
            context.venture_id or getattr(context.ctx, "active_venture_id", None),
        )
        return context
