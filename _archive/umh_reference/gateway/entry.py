"""UMH Gateway Entry — canonical input/output contract.

Every external service (Discord, Telegram, webhook, CLI) translates its
native request format into a UMHInput, calls translate_and_run(), and
receives a UMHOutput. This is the ONLY entry point for external signals.

No platform-specific logic lives here. Platform policy (approval gates,
CEO context, agent selection) belongs in the platform wrapper layer
(e.g. umh/gateway.py).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from umh.governance.authority import AuthorityLevel
from umh.run import RunResult, run


@dataclass
class UMHInput:
    """Canonical input shape for all external signals.

    Services translate their native format into this before calling UMH.
    """

    source: str
    raw_input: str
    metadata: dict[str, Any] = field(default_factory=dict)
    attachments: list[dict[str, Any]] = field(default_factory=list)
    authority: AuthorityLevel = AuthorityLevel.ANALYZE
    org_id: str = "default"
    constraints: dict[str, Any] = field(default_factory=dict)


@dataclass
class UMHOutput:
    """Canonical output shape returned to all external services."""

    success: bool
    response: str
    run_id: str
    operation: str
    capability_used: str
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_run_result(cls, result: RunResult) -> UMHOutput:
        return cls(
            success=result.success,
            response=result.response,
            run_id=result.run_id,
            operation=result.operation,
            capability_used=result.capability_used,
            metadata=result.metadata,
        )

    @classmethod
    def error(cls, message: str, source: str = "gateway") -> UMHOutput:
        return cls(
            success=False,
            response=message,
            run_id="",
            operation="error",
            capability_used="none",
            metadata={"error_source": source},
        )


def utility_llm_call(
    prompt: str,
    system: str | None = None,
    operation: str = "utility",
    max_tokens: int = 1024,
) -> str:
    """Quick LLM call routed through UMH's execution engine.

    For classification, extraction, and other utility calls that don't need
    the full 9-stage run loop. Routes through lightweight_execute() →
    execute() → configured ExecutionBackend, giving these calls the same
    observer/backend/rate-limiting pipeline as full runs.

    Returns the raw LLM response string. Returns empty string on failure.
    """
    from umh.execution.engine import lightweight_execute

    result = lightweight_execute(
        operation=operation,
        prompt=prompt,
        system=system,
        max_tokens=max_tokens,
    )
    text = result.outputs.get("text", "")
    if result.status.value == "succeeded" and text:
        return text
    return ""


def translate_and_run(input: UMHInput) -> UMHOutput:
    """Execute a UMHInput through the full run loop.

    This is the single function that replaces all direct LLM calls,
    gateway bypasses, and competing control planes.
    """
    try:
        result = run(
            input_text=input.raw_input,
            source=input.source,
            org_id=input.org_id,
            authority=input.authority,
            constraints=input.constraints if input.constraints else None,
        )
        output = UMHOutput.from_run_result(result)
        output.metadata["input_metadata"] = input.metadata
        if input.attachments:
            output.metadata["attachments_count"] = len(input.attachments)
        return output
    except Exception as exc:
        return UMHOutput.error(f"UMH run failed: {exc}", source=input.source)
