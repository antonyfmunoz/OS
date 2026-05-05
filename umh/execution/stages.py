"""
UMH Execution Stages — composable units of execution.

Each stage is a stateless function wrapped in the ``ExecutionStage``
protocol.  Stages communicate through ``StageContext``, a mutable
dictionary-like object that accumulates state as it flows through
the pipeline.

A stage may:
  - read from context (inputs it needs)
  - write to context (outputs it produces)
  - produce side effects (DB writes, API calls)
  - abort the pipeline (set ``context.aborted = True``)

A stage must NOT:
  - import platform-specific code at module level
  - hold mutable state between calls
  - depend on execution order beyond its declared dependencies
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable

_log = logging.getLogger(__name__)


@dataclass
class StageContext:
    """Mutable execution context passed through the pipeline.

    Stages read their inputs and write their outputs here.
    The pipeline runner checks ``aborted`` after each stage.
    """

    # ── Identity ─────────────────────────────────────────────────────
    session_id: str = ""
    correlation_id: str = ""

    # ── Inputs (set by caller before pipeline starts) ────────────────
    message: str = ""
    original_message: str = ""
    unified_context: Any = None
    agent_type: str = "executive_assistant"
    authority_class: str = "analyze"
    channel_id: str | None = None
    org_id: str | None = None
    user_id: str | None = None
    task_type: Any = None
    venture_id: str | None = None
    skill_name: str | None = None

    # ── Accumulated state (written by stages) ────────────────────────
    ctx: Any = None  # runtime context from load_context_from_env
    runtime: Any = None  # AgentRuntime instance
    system_prompt: str = ""
    response: str = ""
    model_used: str = "unknown"
    tokens_used: dict[str, int] = field(
        default_factory=lambda: {"input": 0, "output": 0, "total": 0}
    )
    cost_usd: float = 0.0
    latency_ms: int = 0
    was_enhanced: bool = False
    iterations: int = 1
    evaluation: dict | None = None
    signals: Any = None

    # ── Control flow ─────────────────────────────────────────────────
    aborted: bool = False
    abort_result: str = ""

    # ── Observability ────────────────────────────────────────────────
    stage_timings: dict[str, int] = field(default_factory=dict)
    stage_errors: dict[str, str] = field(default_factory=dict)

    # ── Extension slot for future stages ─────────────────────────────
    extra: dict[str, Any] = field(default_factory=dict)


@runtime_checkable
class ExecutionStage(Protocol):
    """Protocol for a single composable execution stage."""

    @property
    def name(self) -> str:
        """Unique stage identifier (e.g. 'authority_check')."""
        ...

    @property
    def description(self) -> str:
        """One-line description of what this stage does."""
        ...

    @property
    def dependencies(self) -> tuple[str, ...]:
        """Names of stages that must run before this one."""
        ...

    @property
    def can_abort(self) -> bool:
        """Whether this stage can abort the pipeline."""
        ...

    def run(self, context: StageContext) -> StageContext:
        """Execute the stage, mutating context in place.

        Must return the same context object.
        If the stage needs to abort, set context.aborted = True
        and context.abort_result to the early-return message.
        """
        ...


@dataclass(frozen=True)
class StageResult:
    """Snapshot of a single stage execution for observability."""

    name: str
    elapsed_ms: int
    error: str | None = None
    aborted: bool = False
