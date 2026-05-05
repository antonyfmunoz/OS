"""ExecutionRouter — deterministic action dispatch for UMH.

Routes ExecutableActions to handlers through a two-tier resolution:
1. Exact match on action_name
2. Type fallback on action_type

Returns a structured ExecutionResult. Never raises to the caller.
All handlers in this slice are safe local stubs — no real API calls,
no external side effects.

Usage::

    from umh.actions.router import ExecutionRouter, ExecutionRequest
    from umh.actions.schema import ExecutableAction

    router = ExecutionRouter()
    result = router.route(ExecutionRequest(action=my_action))
"""

from __future__ import annotations

from dataclasses import dataclass


# ─── Data models ────────────────────────────────────────────────


@dataclass(frozen=True)
class ExecutionRequest:
    """Wrapper for execution entrypoint."""

    action: object  # ExecutableAction

    def to_dict(self) -> dict:
        action = self.action
        if hasattr(action, "to_dict"):
            return {"action": action.to_dict()}
        return {"action": str(action)}


@dataclass(frozen=True)
class ExecutionResult:
    """Universal execution result contract."""

    action_id: str
    action_name: str
    handler_name: str | None
    status: str  # "success" | "failed" | "skipped" | "unhandled"
    output: dict[str, float | int | str | bool | None] | None
    error: str | None

    def to_dict(self) -> dict:
        return {
            "action_id": self.action_id,
            "action_name": self.action_name,
            "handler_name": self.handler_name,
            "status": self.status,
            "output": dict(self.output) if self.output is not None else None,
            "error": self.error,
        }

    @classmethod
    def from_dict(cls, d: dict) -> ExecutionResult:
        return cls(
            action_id=d["action_id"],
            action_name=d["action_name"],
            handler_name=d.get("handler_name"),
            status=d["status"],
            output=d.get("output"),
            error=d.get("error"),
        )


@dataclass(frozen=True)
class HandlerResolution:
    """Makes handler routing inspectable/debuggable."""

    action_name: str
    action_type: str
    resolved_handler: str | None
    resolution_path: str  # "exact" | "type_fallback" | "none"

    def to_dict(self) -> dict:
        return {
            "action_name": self.action_name,
            "action_type": self.action_type,
            "resolved_handler": self.resolved_handler,
            "resolution_path": self.resolution_path,
        }


# ─── Handler interface ──────────────────────────────────────────


class BaseHandler:
    """Base class for execution handlers."""

    name: str = "base"

    def execute(self, action: object) -> dict[str, float | int | str | bool | None]:
        raise NotImplementedError


# ─── Built-in handlers ──────────────────────────────────────────


class NoOpHandler(BaseHandler):
    name = "no_op"

    def execute(self, action: object) -> dict[str, float | int | str | bool | None]:
        return {"message": "no operation"}


class LogHandler(BaseHandler):
    name = "log"

    def execute(self, action: object) -> dict[str, float | int | str | bool | None]:
        return {
            "logged_action": getattr(action, "action_name", "unknown"),
            "target": getattr(action, "target", None),
            "domain": getattr(action, "domain", "unknown"),
        }


class HumanInstructionHandler(BaseHandler):
    name = "human_instruction"

    def execute(self, action: object) -> dict[str, float | int | str | bool | None]:
        return {
            "instruction": getattr(action, "intent", ""),
            "target": getattr(action, "target", None) or "human",
        }


# ─── Default registries ────────────────────────────────────────


DEFAULT_ACTION_HANDLERS: dict[str, BaseHandler] = {
    "no_op": NoOpHandler(),
    "log": LogHandler(),
    "human_instruction": HumanInstructionHandler(),
}

DEFAULT_TYPE_FALLBACK: dict[str, str] = {
    "NO_OP": "no_op",
    "TASK": "log",
    "MESSAGE": "human_instruction",
    "HUMAN_INSTRUCTION": "human_instruction",
    "API_CALL": "log",
}


# ─── Handler resolution ────────────────────────────────────────


def resolve_handler(
    action: object,
    handlers: dict[str, BaseHandler],
    type_fallback: dict[str, str],
) -> HandlerResolution:
    """Resolve which handler should process this action.

    Resolution order:
    1. Exact match on action.action_name in handlers
    2. Type fallback: action.action_type → mapped handler name → handlers
    3. None (unhandled)
    """
    action_name = getattr(action, "action_name", "")
    action_type = getattr(action, "action_type", "")

    if action_name in handlers:
        return HandlerResolution(
            action_name=action_name,
            action_type=action_type,
            resolved_handler=action_name,
            resolution_path="exact",
        )

    fallback_name = type_fallback.get(action_type)
    if fallback_name is not None and fallback_name in handlers:
        return HandlerResolution(
            action_name=action_name,
            action_type=action_type,
            resolved_handler=fallback_name,
            resolution_path="type_fallback",
        )

    return HandlerResolution(
        action_name=action_name,
        action_type=action_type,
        resolved_handler=None,
        resolution_path="none",
    )


# ─── Execution router ──────────────────────────────────────────


class ExecutionRouter:
    """Deterministic action dispatch.

    Accepts an ExecutionRequest, resolves the handler, executes,
    and returns an ExecutionResult. Never raises to the caller.
    """

    def __init__(
        self,
        handlers: dict[str, BaseHandler] | None = None,
        type_fallback: dict[str, str] | None = None,
    ) -> None:
        self._handlers = (
            handlers if handlers is not None else dict(DEFAULT_ACTION_HANDLERS)
        )
        self._type_fallback = (
            type_fallback if type_fallback is not None else dict(DEFAULT_TYPE_FALLBACK)
        )

    def route(self, request: ExecutionRequest) -> ExecutionResult:
        """Route an ExecutionRequest to the appropriate handler.

        Returns ExecutionResult with status:
        - "success" — handler executed cleanly
        - "failed" — handler raised an exception
        - "unhandled" — no handler resolved
        """
        action = request.action
        action_id = getattr(action, "action_id", "")
        action_name = getattr(action, "action_name", "")

        resolution = resolve_handler(action, self._handlers, self._type_fallback)

        if resolution.resolved_handler is None:
            return ExecutionResult(
                action_id=action_id,
                action_name=action_name,
                handler_name=None,
                status="unhandled",
                output=None,
                error=f"No handler resolved for '{action_name}' (type={resolution.action_type})",
            )

        handler = self._handlers[resolution.resolved_handler]

        try:
            output = handler.execute(action)
        except Exception as exc:
            return ExecutionResult(
                action_id=action_id,
                action_name=action_name,
                handler_name=handler.name,
                status="failed",
                output=None,
                error=str(exc),
            )

        return ExecutionResult(
            action_id=action_id,
            action_name=action_name,
            handler_name=handler.name,
            status="success",
            output=output,
            error=None,
        )

    def get_resolution(self, action: object) -> HandlerResolution:
        """Inspect handler resolution without executing."""
        return resolve_handler(action, self._handlers, self._type_fallback)


if __name__ == "__main__":
    print("execution_router import OK")
