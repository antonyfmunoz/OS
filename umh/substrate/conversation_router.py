"""
Conversation Router — thin routing layer at the inbound message entry point.

Determines whether an inbound message is a retrieval query or a task,
and routes accordingly.  Also provides a simple high-context-risk
heuristic for messages that may need special handling.

Design rules:
  - Thin.  This module is a routing shim, not a processing engine.
  - Deterministic.  No LLM calls.
  - Best-effort.  Routing failures fall through to task pipeline.
  - Composable.  Sits on top of query_brain, never modifies stores.
"""

from __future__ import annotations

import re
import sys
from typing import Any

# ─── Config ──────────────────────────────────────────────────────────────────

_LOG_PREFIX = "[substrate.conversation_router]"


def _log(msg: str) -> None:
    print(f"{_LOG_PREFIX} {msg}", file=sys.stderr)


# ─── Browser / Media Intent Detection ──────────────────────────────────────

# Patterns that indicate a browser or media intent — used to tag routing
# result so downstream systems (permission layer, Discord bridge) know
# this is a local browser action, not a network/research operation.

_BROWSER_INTENT_PATTERNS: list[re.Pattern[str]] = [
    re.compile(
        r"\b(open|go to|navigate to|visit|launch|browse|pull up)\s+", re.IGNORECASE
    ),
    re.compile(r"\b(play|put on|listen to|queue up|throw on)\s+", re.IGNORECASE),
    re.compile(r"\b(search\s+(?:for\s+)?|look\s+up\s+|google\s+)", re.IGNORECASE),
    re.compile(r"https?://", re.IGNORECASE),
    re.compile(
        r"\b(youtube|gmail|notion|github|spotify|instagram|reddit|twitter)\b",
        re.IGNORECASE,
    ),
]


def _is_browser_intent(text: str) -> bool:
    """Quick check: does this message look like a browser/media intent?"""
    return any(pat.search(text) for pat in _BROWSER_INTENT_PATTERNS)


# ─── Message routing ─────────────────────────────────────────────────────────


def route_message(
    text: str,
    *,
    interface: str = "discord",
    correlation_id: str = "",
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Route an inbound message to either query_brain or the task pipeline.

    Args:
        text: The raw inbound message text.
        interface: Source interface (discord, vps_cli, etc).
        correlation_id: Workflow-level correlation ID.
        metadata: Optional additional context from the transport layer.

    Returns:
        A routing dict with:
          - routed_to: "query_brain" | "task_pipeline"
          - is_query: bool
          - For queries: result (QueryResult.to_dict()), response_text
          - For tasks: text, correlation_id
    """
    try:
        from umh.substrate.query_brain import execute_query, is_query

        if is_query(text):
            result = execute_query(text)
            return {
                "routed_to": "query_brain",
                "is_query": True,
                "result": result.to_dict(),
                "response_text": result.response_text,
            }
    except Exception as exc:
        _log(f"query detection/execution failed, falling through to task: {exc}")

    # Tag browser/media intents so downstream systems can classify correctly
    is_browser = _is_browser_intent(text)
    if is_browser:
        _log(f"tagged as browser intent: {text[:80]!r}")

    # ── Context risk pre-check ─────────────────────────────────────────
    high_context_risk = detect_high_context_risk(text)

    # ── Orchestration planning ─────────────────────────────────────────
    # Assess context budget and decide execution shape before routing
    # to the task pipeline.  The plan is advisory in V1 — it accompanies
    # the task as metadata.  Existing execution paths are unchanged.
    orchestration_plan: dict[str, Any] | None = None
    try:
        from umh.substrate.adaptive_orchestration_policy import (
            plan_task_orchestration,
            RiskLevel,
        )
        from umh.substrate.orchestration_record import (
            record_orchestration_plan,
        )

        meta = metadata or {}
        plan = plan_task_orchestration(
            text,
            current_session_chars=meta.get("current_session_chars", 0),
            task_metadata={
                "is_browser_intent": is_browser,
                "interface": interface,
                **(meta.get("task_metadata", {})),
            },
        )
        orchestration_plan = plan.to_dict()

        # Store for traceability
        record_orchestration_plan(
            plan,
            correlation_id=correlation_id,
            metadata={"interface": interface},
        )

        _log(
            f"orchestration plan: mode={plan.mode.value} "
            f"pressure={plan.context_budget.pressure.value if plan.context_budget else '?'} "
            f"complexity={plan.context_budget.task_complexity.value if plan.context_budget else '?'}"
        )
    except Exception as exc:
        _log(f"orchestration planning failed (non-blocking): {exc}")

    # ── Semantic decomposition (V2, best-effort) ────────────────────
    semantic_plan_dict: dict[str, Any] | None = None
    try:
        from umh.substrate.semantic_planner import semantic_decompose

        if orchestration_plan is not None:
            pressure = orchestration_plan.get("context_budget", {}).get(
                "pressure", "low"
            )
            plan_mode = orchestration_plan.get("mode", "")
            sem_plan = semantic_decompose(
                text,
                plan_mode=plan_mode,
                context={"pressure": pressure},
            )
            if sem_plan.subtask_count > 1:
                semantic_plan_dict = sem_plan.to_dict()
                _log(
                    f"semantic plan: {sem_plan.subtask_count} subtasks, "
                    f"merge={sem_plan.merge_strategy.value}"
                )
    except Exception as exc:
        _log(f"semantic planning failed (non-blocking): {exc}")

    # ── Session rhythm context (additive, best-effort) ─────────────────
    rhythm_context: dict[str, Any] | None = None
    try:
        from umh.substrate.session_rhythm import get_combined_execution_hints

        rhythm_context = get_combined_execution_hints()
    except Exception as exc:
        _log(f"rhythm context failed (non-blocking): {exc}")

    return {
        "routed_to": "task_pipeline",
        "is_query": False,
        "is_browser_intent": is_browser,
        "high_context_risk": high_context_risk,
        "text": text,
        "correlation_id": correlation_id,
        "orchestration_plan": orchestration_plan,
        "semantic_plan": semantic_plan_dict,
        "rhythm_context": rhythm_context,
        "_plan_object": plan if "plan" in dir() else None,
    }


# ─── High-context-risk detection ────────────────────────────────────────────


def detect_high_context_risk(text: str) -> dict[str, Any]:
    """Simple heuristic to flag messages that may overwhelm context.

    Checks:
      - Message length > 3000 chars
      - Multiple numbered phases ("phase 1" AND "phase 2")
      - More than 5 paragraphs (split by double newline)

    Returns a dict with high_context_risk (bool) and reason if True.
    """
    if not text:
        return {"high_context_risk": False}

    # Length check
    if len(text) > 3000:
        return {
            "high_context_risk": True,
            "reason": "message_length",
            "char_count": len(text),
        }

    # Multi-phase detection
    lower = text.lower()
    has_phase_1 = "phase 1" in lower
    has_phase_2 = "phase 2" in lower
    if has_phase_1 and has_phase_2:
        return {
            "high_context_risk": True,
            "reason": "multi_phase_detected",
        }

    # Many sections
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    if len(paragraphs) > 5:
        return {
            "high_context_risk": True,
            "reason": "many_sections",
            "section_count": len(paragraphs),
        }

    return {"high_context_risk": False}


# ─── Exports ─────────────────────────────────────────────────────────────────

__all__ = [
    "route_message",
    "detect_high_context_risk",
    "is_browser_intent",
]


# Module-level alias for external callers
is_browser_intent = _is_browser_intent
