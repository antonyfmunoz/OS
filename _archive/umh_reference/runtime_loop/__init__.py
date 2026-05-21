"""umh.runtime — End-to-end lifecycle orchestration and live runtime loop."""

from umh.runtime_loop.action_executor import ActionExecutionResult, ActionRequest
from umh.runtime_loop.context import RuntimeContext
from umh.runtime_loop.input_router import InputEvent, RoutedInput, route_input
from umh.runtime_loop.lifecycle import run_lifecycle
from umh.runtime_loop.live_loop import LiveRuntime, get_or_create_runtime, evict_runtime

__all__ = [
    "ActionExecutionResult",
    "ActionRequest",
    "InputEvent",
    "LiveRuntime",
    "evict_runtime",
    "get_or_create_runtime",
    "RoutedInput",
    "RuntimeContext",
    "route_input",
    "run_lifecycle",
]

from umh.runtime_loop.lifecycle_behaviors import install as _install_behaviors

_install_behaviors()
