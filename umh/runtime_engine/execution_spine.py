"""
ExecutionSpine — thin compatibility shell for EOS execution.

Production entry point: ``run_via_umh()`` builds a UMH ExecutionRequest
and routes through ``umh.execution.engine.execute()``.

``ExecutionSpine.run()`` delegates to a 9-stage composable pipeline
(see ``umh/stages/``).  Each stage is an independent module with
zero coupling to this file.

``SpineResult`` is the return contract — a ``str`` subclass carrying
runtime metadata (model_used, tokens_used, cost_usd, latency_ms).

Helper functions (enhance_prompt, verify_quality, etc.) are re-exported
from ``umh/stages/*.py`` for backward compatibility only.
"""

import logging
import os
import sys
import uuid
from datetime import datetime, timezone

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

_log = logging.getLogger(__name__)

# Risk classes that must fail closed when authority check itself errors.
# LOW/MEDIUM proceed on authority-check infrastructure failure (DB down, etc.)
# HIGH/CRITICAL block — the cost of a false-allow is higher than a false-block.
_FAIL_CLOSED_RISK_CLASSES = frozenset({"HIGH", "CRITICAL"})


class SpineResult(str):
    """Str subclass carrying runtime metadata from the execution spine.

    Acts exactly like a ``str`` in all contexts (startswith, in, lower,
    slicing, etc.) so existing callers need zero changes.  Callers that
    want observability can read the extra attributes::

        result = spine.run(message, unified_context, ...)
        print(result)                # plain string
        print(result.model_used)     # "gemini/gemini-2.5-flash"
        print(result.tokens_used)    # {"input": 80, "output": 120, "total": 200}
        print(result.cost_usd)       # 0.001
        print(result.latency_ms)     # 150
        print(result.session_id)     # "abc-123"
    """

    model_used: str
    tokens_used: dict[str, int]
    cost_usd: float
    latency_ms: int
    session_id: str
    iterations: int
    was_enhanced: bool

    def __new__(
        cls,
        text: str,
        *,
        model_used: str = "unknown",
        tokens_used: dict[str, int] | None = None,
        cost_usd: float = 0.0,
        latency_ms: int = 0,
        session_id: str = "",
        iterations: int = 1,
        was_enhanced: bool = False,
    ) -> "SpineResult":
        instance = super().__new__(cls, text)
        instance.model_used = model_used
        instance.tokens_used = tokens_used or {"input": 0, "output": 0, "total": 0}
        instance.cost_usd = cost_usd
        instance.latency_ms = latency_ms
        instance.session_id = session_id
        instance.iterations = iterations
        instance.was_enhanced = was_enhanced
        return instance

    def __repr__(self) -> str:
        return (
            f"SpineResult({super().__repr__()}, "
            f"model_used={self.model_used!r}, "
            f"tokens={self.tokens_used.get('total', 0)}, "
            f"cost=${self.cost_usd:.4f})"
        )


# ─── Legacy compatibility re-exports ─────────────────────────────────────────
# Canonical implementations now live in umh/stages/*.py.
# These re-exports exist solely so that test files and any straggling import
# paths continue to resolve.  No new code should import these from here.

from umh.stages.footer import (  # noqa: F401
    format_response_footer,
    _get_neon_spend,
)
from umh.stages.enhancement import enhance_prompt  # noqa: F401
from umh.stages.quality import verify_quality, _check_quality  # noqa: F401
from umh.stages.stage_filter import apply_stage_filter  # noqa: F401
from umh.stages.commit import (  # noqa: F401
    integrate_knowledge,
    log_feedback,
    update_world_model,
    log_reflection,
)


# ─── ExecutionSpine ──────────────────────────────────────────────────────────


def _build_default_pipeline():
    """Construct the default 9-stage execution pipeline."""
    from umh.execution.pipeline import ExecutionPipeline
    from umh.stages.authority import AuthorityCheckStage
    from umh.stages.enhancement import PromptEnhancementStage
    from umh.stages.context_assembly import ContextAssemblyStage
    from umh.stages.llm_generation import LLMGenerationStage
    from umh.stages.quality import QualityVerificationStage
    from umh.stages.stage_filter import StageFilterStage
    from umh.stages.outcome import OutcomeEvaluationStage
    from umh.stages.commit import CommitStage
    from umh.stages.footer import ResponseFooterStage

    return ExecutionPipeline(
        [
            AuthorityCheckStage(),
            PromptEnhancementStage(),
            ContextAssemblyStage(),
            LLMGenerationStage(),
            QualityVerificationStage(),
            StageFilterStage(),
            OutcomeEvaluationStage(),
            CommitStage(),
            ResponseFooterStage(),
        ]
    )


class ExecutionSpine:
    def run(
        self,
        message: str,
        unified_context: object,
        agent_type: str = "executive_assistant",
        authority_class: str = "analyze",
        session_id: str | None = None,
        channel_id: str | None = None,
        org_id: str | None = None,
        user_id: str | None = None,
        task_type: object = None,
        venture_id: str | None = None,
        skill_name: str | None = None,
    ) -> SpineResult:
        """Execute via the composable stage pipeline.

        Builds a StageContext from parameters, runs it through the
        default 9-stage pipeline, and returns a SpineResult.
        """
        from umh.execution.stages import StageContext

        _session_id = session_id or str(uuid.uuid4())
        _start = datetime.now(timezone.utc)

        context = StageContext(
            session_id=_session_id,
            message=message,
            original_message=message,
            unified_context=unified_context,
            agent_type=agent_type,
            authority_class=authority_class,
            channel_id=channel_id,
            org_id=org_id,
            user_id=user_id,
            task_type=task_type,
            venture_id=venture_id,
            skill_name=skill_name,
        )

        pipeline = _build_default_pipeline()
        result = pipeline.run(context)
        ctx = result.context

        if ctx.aborted:
            return SpineResult(ctx.abort_result, session_id=_session_id)

        _elapsed = (datetime.now(timezone.utc) - _start).total_seconds()
        _elapsed_ms = int(_elapsed * 1000)
        _log.info(
            "agent=%s session=%s enhanced=%s iterations=%d elapsed=%.1fs stages=%s",
            agent_type,
            _session_id[:8],
            ctx.was_enhanced,
            ctx.iterations,
            _elapsed,
            list(ctx.stage_timings.keys()),
        )

        return SpineResult(
            ctx.response,
            model_used=ctx.model_used,
            tokens_used=ctx.tokens_used,
            cost_usd=ctx.cost_usd,
            latency_ms=ctx.latency_ms or _elapsed_ms,
            session_id=_session_id,
            iterations=ctx.iterations,
            was_enhanced=ctx.was_enhanced,
        )


def run_via_umh(
    message: str,
    unified_context: object,
    agent_type: str = "executive_assistant",
    authority_class: str = "analyze",
    session_id: str | None = None,
    channel_id: str | None = None,
    org_id: str | None = None,
    user_id: str | None = None,
    task_type: object = None,
    venture_id: str | None = None,
    skill_name: str | None = None,
) -> SpineResult:
    """Execute an LLM operation through the UMH execution engine.

    Accepts the same parameters as ``ExecutionSpine.run()`` and returns a
    ``SpineResult``.  Internally builds a UMH ``ExecutionRequest`` and
    routes through ``umh.execution.engine.execute()``, which delegates
    back to the ``SubstrateExecutionBackend`` adapter.

    This is the migration entry point: callsites switch from
    ``ExecutionSpine().run(...)`` to ``run_via_umh(...)`` with no other
    changes.
    """
    from datetime import datetime, timezone as _tz

    from umh.execution.contract import (
        ExecutionClass,
        ExecutionConstraints,
        ExecutionContext,
        ExecutionRequest,
        ExecutionStatus,
        ExecutionTarget,
        _compute_idempotency_key,
        _new_execution_id,
    )
    from umh.execution.engine import execute

    _session_id = session_id or str(uuid.uuid4())
    _correlation_id = str(uuid.uuid4())
    _now = datetime.now(_tz.utc).isoformat()

    system_prompt = ""
    if hasattr(unified_context, "to_system_prompt"):
        try:
            system_prompt = unified_context.to_system_prompt()
        except Exception:
            pass

    inputs = {
        "prompt": message,
        "system_prompt": system_prompt,
        "task_type": str(task_type) if task_type else None,
        "skill_name": skill_name,
    }

    request = ExecutionRequest(
        execution_id=_new_execution_id(),
        correlation_id=_correlation_id,
        causal_event_id=f"call_{_correlation_id[:12]}",
        session_id=_session_id,
        operation="llm_generate",
        inputs=inputs,
        execution_class=ExecutionClass.LLM_CALL,
        constraints=ExecutionConstraints(timeout_s=120, max_retries=1),
        target=ExecutionTarget(node_id="local", transport="in_process"),
        context=ExecutionContext(
            session_id=_session_id,
            correlation_id=_correlation_id,
            authority_class=authority_class,
            agent_type=agent_type,
            venture_id=venture_id or "",
            channel=channel_id or "",
            user_id=user_id or "",
            org_id=org_id or "",
        ),
        issued_at=_now,
        issued_by="execution_spine.run_via_umh",
        idempotency_key=_compute_idempotency_key("llm_generate", inputs),
    )

    result = execute(request)

    if result.status == ExecutionStatus.SUCCEEDED:
        return SpineResult(
            result.outputs.get("text", ""),
            model_used=result.model_used or "unknown",
            tokens_used=result.tokens_used or {},
            cost_usd=result.cost_usd or 0.0,
            latency_ms=result.latency_ms or 0,
            session_id=_session_id,
            iterations=result.outputs.get("iterations", 1),
            was_enhanced=result.outputs.get("was_enhanced", False),
        )

    error_msg = result.error or "UMH execution failed"
    _log.error("run_via_umh failed: %s", error_msg)
    return SpineResult(error_msg, session_id=_session_id)


if __name__ == "__main__":
    print("ExecutionSpine import OK")
    spine = ExecutionSpine()
    print("ExecutionSpine instantiation OK")
