"""Brain system — identity, expression, and coordination over the shared substrate.

Public API:
    from umh.brains import BrainProfile, ExpressionState, get_brain_registry
    from umh.brains.context import build_brain_context
    from umh.brains.signals import emit_signal, list_signals
"""

from umh.brains.profile import AuthorityLevel, BrainProfile, ExpressionState
from umh.brains.registry import (
    BrainRegistry,
    get_brain_registry,
    register,
    get,
    list_all,
    list_brains,
    children,
    get_expression,
    update_expression,
    apply_correction,
    create_child,
    resolve_with_inheritance,
    ensure_default_brains,
    clear,
)
from umh.brains.signals import BrainSignal, emit_signal

__all__ = [
    "AuthorityLevel",
    "BrainProfile",
    "BrainRegistry",
    "BrainSignal",
    "ExpressionState",
    "apply_correction",
    "children",
    "clear",
    "create_child",
    "emit_signal",
    "ensure_default_brains",
    "get",
    "get_brain_registry",
    "get_expression",
    "list_all",
    "list_brains",
    "register",
    "resolve_with_inheritance",
    "update_expression",
]
