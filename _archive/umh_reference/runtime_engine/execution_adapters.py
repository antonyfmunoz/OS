"""ExecutionAdapters — environment-specific execution for UMH.

Provides adapter implementations for each ExecutionEnvironment.
Each adapter takes an ExecutableAction and returns a structured
AdapterResult. No real external calls — API adapter is a mock.

Pipeline position:
    EnvironmentRouter → ExecutionAdapter.execute() → AdapterResult

Usage::

    from umh.runtime_engine.execution_adapters import (
        AdapterResult,
        get_adapter,
        execute_with_environment,
    )

    result = execute_with_environment(action)
"""

from __future__ import annotations

import time
from dataclasses import dataclass

from umh.runtime_engine.environment_router import (
    ExecutionEnvironment,
    EnvironmentRoute,
    resolve_environment,
)


# ─── Data models ─────────────────────────────────────────────────


@dataclass(frozen=True)
class AdapterResult:
    """Structured output from an execution adapter."""

    success: bool
    output: dict | None
    error: str | None
    latency_ms: int
    environment: ExecutionEnvironment

    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "output": dict(self.output) if self.output is not None else None,
            "error": self.error,
            "latency_ms": self.latency_ms,
            "environment": self.environment.value,
        }


NO_ADAPTER_RESULT = AdapterResult(
    success=False,
    output=None,
    error="no_adapter",
    latency_ms=0,
    environment=ExecutionEnvironment.UNKNOWN,
)


# ─── Adapter base ────────────────────────────────────────────────


class BaseExecutionAdapter:
    """Base class for execution adapters."""

    name: str = "base"
    environment: ExecutionEnvironment = ExecutionEnvironment.UNKNOWN

    def can_handle(self, action: object) -> bool:
        return False

    def execute(self, action: object) -> AdapterResult:
        raise NotImplementedError


# ─── LocalAdapter ────────────────────────────────────────────────


class LocalAdapter(BaseExecutionAdapter):
    """Executes internal/local actions. Always safe."""

    name = "local"
    environment = ExecutionEnvironment.LOCAL

    def can_handle(self, action: object) -> bool:
        action_type = getattr(action, "action_type", "")
        return action_type in ("TASK", "NO_OP")

    def execute(self, action: object) -> AdapterResult:
        start = time.monotonic()
        action_name = getattr(action, "action_name", "unknown")
        action_id = getattr(action, "action_id", "")
        intent = getattr(action, "intent", "")

        output = {
            "action_name": action_name,
            "action_id": action_id,
            "intent": intent,
            "executed_locally": True,
        }

        elapsed = int((time.monotonic() - start) * 1000)
        return AdapterResult(
            success=True,
            output=output,
            error=None,
            latency_ms=elapsed,
            environment=ExecutionEnvironment.LOCAL,
        )


# ─── HumanAdapter ───────────────────────────────────────────────


class HumanAdapter(BaseExecutionAdapter):
    """Returns instruction payload for human execution. Never auto-executes."""

    name = "human"
    environment = ExecutionEnvironment.HUMAN

    def can_handle(self, action: object) -> bool:
        action_type = getattr(action, "action_type", "")
        return action_type in ("MESSAGE", "HUMAN_INSTRUCTION")

    def execute(self, action: object) -> AdapterResult:
        start = time.monotonic()
        action_name = getattr(action, "action_name", "unknown")
        intent = getattr(action, "intent", "")
        target = getattr(action, "target", None)

        output = {
            "instruction": intent,
            "target": target or "human",
            "action_name": action_name,
            "requires_human": True,
            "auto_executed": False,
        }

        elapsed = int((time.monotonic() - start) * 1000)
        return AdapterResult(
            success=True,
            output=output,
            error=None,
            latency_ms=elapsed,
            environment=ExecutionEnvironment.HUMAN,
        )


# ─── MockAPIAdapter ─────────────────────────────────────────────


class MockAPIAdapter(BaseExecutionAdapter):
    """Simulates API calls. Never makes real external requests."""

    name = "mock_api"
    environment = ExecutionEnvironment.API

    def can_handle(self, action: object) -> bool:
        action_type = getattr(action, "action_type", "")
        return action_type == "API_CALL"

    def execute(self, action: object) -> AdapterResult:
        start = time.monotonic()
        action_name = getattr(action, "action_name", "unknown")
        action_id = getattr(action, "action_id", "")
        target = getattr(action, "target", None)

        output = {
            "action_name": action_name,
            "action_id": action_id,
            "target": target,
            "simulated": True,
            "mock_response": "ok",
        }

        elapsed = int((time.monotonic() - start) * 1000)
        return AdapterResult(
            success=True,
            output=output,
            error=None,
            latency_ms=elapsed,
            environment=ExecutionEnvironment.API,
        )


# ─── ToolAdapter ─────────────────────────────────────────────────


class ToolAdapter(BaseExecutionAdapter):
    """Handles tool/automation environment. Currently local stub."""

    name = "tool"
    environment = ExecutionEnvironment.TOOL

    def can_handle(self, action: object) -> bool:
        domain = getattr(action, "domain", "")
        return domain.lower() in ("automation", "integration")

    def execute(self, action: object) -> AdapterResult:
        start = time.monotonic()
        action_name = getattr(action, "action_name", "unknown")
        action_id = getattr(action, "action_id", "")

        output = {
            "action_name": action_name,
            "action_id": action_id,
            "tool_executed": True,
            "simulated": True,
        }

        elapsed = int((time.monotonic() - start) * 1000)
        return AdapterResult(
            success=True,
            output=output,
            error=None,
            latency_ms=elapsed,
            environment=ExecutionEnvironment.TOOL,
        )


# ─── NoOpAdapter ─────────────────────────────────────────────────


class NoOpAdapter(BaseExecutionAdapter):
    """Safe fallback for unknown or unroutable actions."""

    name = "no_op"
    environment = ExecutionEnvironment.UNKNOWN

    def can_handle(self, action: object) -> bool:
        return True

    def execute(self, action: object) -> AdapterResult:
        action_name = getattr(action, "action_name", "unknown")
        return AdapterResult(
            success=True,
            output={"action_name": action_name, "no_op": True},
            error=None,
            latency_ms=0,
            environment=ExecutionEnvironment.UNKNOWN,
        )


# ─── Adapter registry ───────────────────────────────────────────

DEFAULT_ADAPTERS: dict[str, BaseExecutionAdapter] = {
    "local": LocalAdapter(),
    "human": HumanAdapter(),
    "mock_api": MockAPIAdapter(),
    "tool": ToolAdapter(),
    "no_op": NoOpAdapter(),
}


def get_adapter(
    adapter_name: str,
    adapters: dict[str, BaseExecutionAdapter] | None = None,
) -> BaseExecutionAdapter:
    """Retrieve an adapter by name. Falls back to NoOpAdapter."""
    registry = adapters if adapters is not None else DEFAULT_ADAPTERS
    return registry.get(adapter_name, NoOpAdapter())


# ─── Unified execution ──────────────────────────────────────────


def execute_with_environment(
    action: object,
    adapters: dict[str, BaseExecutionAdapter] | None = None,
) -> tuple[EnvironmentRoute, AdapterResult]:
    """Resolve environment and execute action through the appropriate adapter.

    Returns (route, result) tuple for full observability.
    """
    route = resolve_environment(action)
    adapter = get_adapter(route.adapter_name, adapters)

    try:
        result = adapter.execute(action)
    except Exception as exc:
        result = AdapterResult(
            success=False,
            output=None,
            error=str(exc),
            latency_ms=0,
            environment=route.environment,
        )

    return route, result


if __name__ == "__main__":
    print("execution_adapters import OK")
