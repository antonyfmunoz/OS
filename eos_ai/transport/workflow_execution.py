"""
Workflow Execution Layer v1.1 — bounded, deterministic workflow handlers.

Purpose
-------
Executes classified workflow requests through explicit, bounded handlers.
Each workflow kind maps to exactly one handler function.  Handlers return
structured result dicts — no autonomous planning, no multi-step chains.

v1.1: ``analysis`` and ``content_ops`` are now live session-backed handlers
(previously deferred stubs in v1).

Architecture
------------
  workflow classified  (workflow_delegation)
    → policy checked   (workflow_delegation)
    → handler resolved (this module)
    → handler executes (this module)
    → result returned  (structured dict)

Design rules
------------
- One handler per workflow kind.  First match, deterministic.
- Handlers are bounded — single request, single response.
- No background threads, no daemons, no autonomous loops.
- No hot-path imports (gateway, cognitive_loop, model_router,
  agent_runtime, primitives).
- Mode boundary preserved: product mode never silently becomes builder.
- Target-aware: handlers receive and respect execution target.
- Safe degradation: handler failure returns error dict, never raises.

This module imports NOTHING from the hot path.
"""

from __future__ import annotations

from typing import Any, Callable

__all__ = [
    "LAYER_NAME",
    "LAYER_VERSION",
    "execute_workflow_if_allowed",
]

LAYER_NAME = "workflow_execution"
LAYER_VERSION = "v1.1"


# ── individual handlers ───────────────────────────────────────────────────────


def _handle_builder_dev(
    text: str,
    mode: str,
    target: str,
    session_name: str | None,
    metadata: dict[str, Any],
) -> dict[str, Any]:
    """Execute a builder/dev workflow request."""
    if session_name:
        from eos_ai.transport.claude_session_bridge import ask_session

        reply = ask_session(target, session_name, text)
        return {
            "ok": True,
            "result_summary": f"builder_dev executed via session '{session_name}'",
            "details": {"session_name": session_name, "reply": reply},
        }
    return {
        "ok": True,
        "result_summary": "builder_dev classified, no session bound",
        "details": {"deferred": True},
    }


def _handle_product_runtime(
    text: str,
    mode: str,
    target: str,
    session_name: str | None,
    metadata: dict[str, Any],
) -> dict[str, Any]:
    """Execute a product runtime workflow request."""
    if session_name:
        from eos_ai.transport.claude_session_bridge import ask_session

        reply = ask_session(target, session_name, text)
        return {
            "ok": True,
            "result_summary": f"product_runtime executed via session '{session_name}'",
            "details": {"session_name": session_name, "reply": reply},
        }
    return {
        "ok": True,
        "result_summary": "product_runtime classified, no session bound",
        "details": {"deferred": True},
    }


def _content_ops_prefix(mode: str) -> str:
    """Return a mode-aware prompt prefix for content generation."""
    if mode == "product":
        return (
            "[Content generation — product mode] "
            "Keep output product-safe. No internal system references, "
            "no infrastructure language, no builder context. "
            "Focus on the content request:\n\n"
        )
    return (
        "[Content generation — builder mode] "
        "Operational/system-aware content is allowed. "
        "Focus on the content request:\n\n"
    )


def _handle_content_ops(
    text: str,
    mode: str,
    target: str,
    session_name: str | None,
    metadata: dict[str, Any],
) -> dict[str, Any]:
    """Execute a content ops workflow request via session."""
    if session_name:
        from eos_ai.transport.claude_session_bridge import ask_session

        prefixed = _content_ops_prefix(mode) + text
        reply = ask_session(target, session_name, prefixed)
        return {
            "ok": True,
            "result_summary": f"content_ops executed via session '{session_name}'",
            "details": {"session_name": session_name, "reply": reply},
        }
    return {
        "ok": True,
        "result_summary": "content_ops classified, no session bound",
        "details": {"deferred": True},
    }


def _analysis_prefix(mode: str) -> str:
    """Return a mode-aware prompt prefix for analysis requests."""
    if mode == "product":
        return (
            "[Analysis — product mode] "
            "Keep output product-safe. No internal system references, "
            "no infrastructure language, no builder context. "
            "Provide clear, structured analysis:\n\n"
        )
    return (
        "[Analysis — builder mode] "
        "System-aware analysis is allowed. Include technical detail "
        "where relevant. Provide clear, structured analysis:\n\n"
    )


def _handle_analysis(
    text: str,
    mode: str,
    target: str,
    session_name: str | None,
    metadata: dict[str, Any],
) -> dict[str, Any]:
    """Execute an analysis workflow request via session."""
    if session_name:
        from eos_ai.transport.claude_session_bridge import ask_session

        prefixed = _analysis_prefix(mode) + text
        reply = ask_session(target, session_name, prefixed)
        return {
            "ok": True,
            "result_summary": f"analysis executed via session '{session_name}'",
            "details": {"session_name": session_name, "reply": reply},
        }
    return {
        "ok": True,
        "result_summary": "analysis classified, no session bound",
        "details": {"deferred": True},
    }


def _handle_system_ops(
    text: str,
    mode: str,
    target: str,
    session_name: str | None,
    metadata: dict[str, Any],
) -> dict[str, Any]:
    """Execute a system ops workflow request."""
    if session_name:
        from eos_ai.transport.claude_session_bridge import ask_session

        reply = ask_session(target, session_name, text)
        return {
            "ok": True,
            "result_summary": f"system_ops executed via session '{session_name}'",
            "details": {"session_name": session_name, "reply": reply},
        }
    return {
        "ok": True,
        "result_summary": "system_ops classified, no session bound",
        "details": {"deferred": True},
    }


# ── handler registry ──────────────────────────────────────────────────────────

# Lazy import constants at module level is safe — workflow_delegation has no
# hot-path imports itself.
from eos_ai.transport.workflow_delegation import (
    KIND_ANALYSIS,
    KIND_BUILDER_DEV,
    KIND_CONTENT_OPS,
    KIND_PRODUCT_RUNTIME,
    KIND_SYSTEM_OPS,
)

_HANDLER_REGISTRY: dict[str, Callable[..., dict[str, Any]]] = {
    KIND_BUILDER_DEV: _handle_builder_dev,
    KIND_PRODUCT_RUNTIME: _handle_product_runtime,
    KIND_CONTENT_OPS: _handle_content_ops,
    KIND_ANALYSIS: _handle_analysis,
    KIND_SYSTEM_OPS: _handle_system_ops,
}


def _resolve_handler(
    workflow_kind: str,
) -> tuple[Callable[..., dict[str, Any]] | None, str]:
    """Return (handler_fn, handler_name) or (None, '') for unknown kinds."""
    handler = _HANDLER_REGISTRY.get(workflow_kind)
    if handler is None:
        return None, ""
    return handler, handler.__name__


# ── main entry point ──────────────────────────────────────────────────────────


def execute_workflow_if_allowed(
    text: str,
    mode: str,
    *,
    target: str | None = None,
    session_name: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Classify, policy-check, and execute a workflow request.

    This is the single entry point for the execution layer.  It chains
    classification (workflow_delegation) with handler dispatch (this module).

    Parameters
    ----------
    text : str
        The user request text.
    mode : str
        Current operating mode ("builder" or "product").
    target : str | None
        Execution target ("local" or "vps").  Resolved automatically if None.
    session_name : str | None
        Claude session name for session-backed handlers.
    metadata : dict | None
        Request metadata dict (passed through to classifier and handlers).

    Returns
    -------
    dict[str, Any]
        Structured result.  Always contains ``workflow_executed`` (bool),
        ``layer``, and ``version``.  See module docstring for full shapes.
    """
    meta = metadata if metadata is not None else {}

    # 1. Classify intent (lazy import)
    from eos_ai.transport.workflow_delegation import (
        INTENT_WORKFLOW,
        classify_workflow_intent,
        resolve_workflow_policy,
    )

    intent_result = classify_workflow_intent(text, mode, metadata=meta)
    intent = intent_result.get("intent", "conversation")
    kind = intent_result.get("workflow_kind", "none")

    # 2. Early exit: not a workflow
    if intent != INTENT_WORKFLOW:
        return {
            "workflow_executed": False,
            "reason": "not_workflow",
            "intent": intent,
            "workflow_kind": kind,
            "mode": mode,
            "target": target,
            "layer": LAYER_NAME,
            "version": LAYER_VERSION,
        }

    # 3. Policy check
    policy = resolve_workflow_policy(mode, intent_result)
    if not policy.get("allowed", False):
        return {
            "workflow_executed": False,
            "reason": "policy_blocked",
            "workflow_kind": kind,
            "mode": mode,
            "target": target,
            "policy_reason": policy.get("policy_reason", "unknown"),
            "layer": LAYER_NAME,
            "version": LAYER_VERSION,
        }

    # 4. Resolve execution target if not provided
    resolved_target = target
    if resolved_target is None:
        from eos_ai.transport.target_policy import resolve_execution_target

        resolved_target = resolve_execution_target(mode, meta)

    # 5. Resolve handler
    handler, handler_name = _resolve_handler(kind)
    if handler is None:
        return {
            "workflow_executed": False,
            "reason": "no_handler",
            "workflow_kind": kind,
            "mode": mode,
            "target": resolved_target,
            "layer": LAYER_NAME,
            "version": LAYER_VERSION,
        }

    # 6. Execute handler — safe degradation on failure
    try:
        handler_result = handler(text, mode, resolved_target, session_name, meta)
    except Exception as exc:
        return {
            "workflow_executed": False,
            "reason": "handler_error",
            "workflow_kind": kind,
            "handler": handler_name,
            "mode": mode,
            "target": resolved_target,
            "error": str(exc),
            "layer": LAYER_NAME,
            "version": LAYER_VERSION,
        }

    # 7. Return structured success result
    return {
        "workflow_executed": True,
        "ok": handler_result.get("ok", False),
        "workflow_kind": kind,
        "handler": handler_name,
        "mode": mode,
        "target": resolved_target,
        "result_summary": handler_result.get("result_summary", ""),
        "execution_class": "workflow",
        "details": handler_result.get("details", {}),
        "layer": LAYER_NAME,
        "version": LAYER_VERSION,
    }
