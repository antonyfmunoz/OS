"""Stage 5a: Quality verification — iterative improvement for GENERATE tasks."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from umh.execution.stages import StageContext

_log = logging.getLogger(__name__)


def _check_quality(
    output: str,
    original_prompt: str,
    task_type: object,
    runtime: object,
) -> dict:
    """Single quality check.  Returns {'passes': bool, 'issues': str|None}."""
    from umh.runtime_engine.agent_runtime import TaskType

    if len(output) < 50:
        return {"passes": False, "issues": "Output too short"}

    if task_type in (TaskType.SCORE, TaskType.CLASSIFY):
        return {"passes": True, "issues": None}

    try:
        check = runtime.run(
            task_type=TaskType.CLASSIFY,
            prompt=(
                "Does this output adequately address the request? "
                "Reply with PASS or FAIL and one sentence why.\n\n"
                f"Request: {original_prompt[:200]}\n\n"
                f"Output: {output[:500]}"
            ),
            agent="quality_checker",
        )
        passes = "PASS" in check.output.upper()
        return {"passes": passes, "issues": check.output if not passes else None}
    except Exception:
        return {"passes": True, "issues": None}


def verify_quality(
    output: str,
    original_prompt: str,
    task_type: object,
    runtime: object,
) -> tuple[str, int]:
    """Post-generation quality verification loop (up to 3 iterations).

    Only fires for GENERATE tasks.  SCORE/CLASSIFY/SUMMARIZE/ANALYZE
    are structured by design.  FAST_RESPONSE/CONVERSATION are latency-sensitive.

    Returns (final_output, total_iterations).
    """
    from umh.runtime_engine.agent_runtime import TaskType

    _tt_val = getattr(task_type, "value", None)
    _skip = _tt_val in (
        "fast_response",
        "conversation",
        "score",
        "classify",
        "summarize",
        "analyze",
    )
    if _skip:
        return output, 1

    max_iterations = 3
    current_output = output
    iteration = 0

    while iteration < max_iterations:
        quality = _check_quality(current_output, original_prompt, task_type, runtime)
        if quality["passes"]:
            break
        try:
            result = runtime.run(
                task_type=task_type,
                prompt=(
                    f"{original_prompt}\n\nPrior attempt:\n"
                    f"{current_output}\n\nIssues found:\n"
                    f"{quality['issues']}\n\nImprove:"
                ),
                agent="quality_checker",
            )
            current_output = result.output or current_output
        except Exception:
            break
        iteration += 1

    return current_output, iteration + 1


@dataclass(frozen=True)
class QualityVerificationStage:
    name: str = "quality_verification"
    description: str = (
        "Post-generation quality loop (up to 3 iterations, GENERATE only)"
    )
    dependencies: tuple[str, ...] = ("llm_generation",)
    can_abort: bool = False

    def run(self, context: StageContext) -> StageContext:
        if not context.runtime:
            return context
        if not context.response or context.response.startswith("[ExecutionSpine]"):
            return context

        try:
            context.response, context.iterations = verify_quality(
                context.response,
                context.original_message,
                context.task_type,
                context.runtime,
            )
        except Exception as e:
            _log.debug("Quality verification skipped: %s", e)
        return context
