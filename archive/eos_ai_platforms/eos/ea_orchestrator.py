"""
EA Orchestrator — main entrypoint for the EOS platform layer.

All founder messages enter through handle_founder_message().  EA parses
intent, builds context, decides whether to handle directly or delegate to
CEO / Portfolio Advisor, creates substrate work if needed, and returns
a founder-facing EAResponse.

Design rules:
- Founder speaks only to EA — never directly to CEO or Portfolio Advisor.
- Even delegated responses are mediated back through EA.
- Execution requests create substrate tasks/pipelines — they don't execute inline.
- Builder is never a founder-facing delegation target.
- Best-effort — substrate failures degrade gracefully, never block the response.
"""

from __future__ import annotations

import sys
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from eos_ai.platforms.eos.context_builder import (
    build_context_for_role,
    build_ea_context,
)
from eos_ai.platforms.eos.decision_log import DecisionLog, EOSDecisionRecord
from eos_ai.platforms.eos.delegation import choose_delegate, should_delegate
from eos_ai.platforms.eos.intent_routing import (
    FounderIntent,
    FounderIntentType,
    parse_founder_intent,
)
from eos_ai.platforms.eos.response_formatter import format_ea_response
from eos_ai.platforms.eos.roles import EOSRole


def _log(msg: str) -> None:
    print(f"[platform.eos.ea_orchestrator] {msg}", file=sys.stderr)


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_id() -> str:
    return f"ea_resp_{uuid.uuid4().hex[:12]}"


# ─── Response model ──────────────────────────────────────────────────────────


@dataclass
class EAResponse:
    """
    The founder-facing output of every EOS platform interaction.

    Even when CEO or Portfolio Advisor produced the underlying analysis,
    the response is always EA-mediated.
    """

    response_id: str
    primary_role: EOSRole
    delegated_role: Optional[EOSRole]
    response_text: str
    created_task_ids: list[str] = field(default_factory=list)
    created_pipeline_ids: list[str] = field(default_factory=list)
    blocked_items: list[str] = field(default_factory=list)
    summary_type: str = "briefing"
    intent: Optional[FounderIntent] = None
    created_at: str = field(default_factory=_utcnow)

    def to_dict(self) -> dict:
        return {
            "response_id": self.response_id,
            "primary_role": self.primary_role.value,
            "delegated_role": (
                self.delegated_role.value if self.delegated_role else None
            ),
            "response_text": self.response_text,
            "created_task_ids": self.created_task_ids,
            "created_pipeline_ids": self.created_pipeline_ids,
            "blocked_items": self.blocked_items,
            "summary_type": self.summary_type,
            "intent": self.intent.to_dict() if self.intent else None,
            "created_at": self.created_at,
        }


# ─── Substrate helpers (best-effort) ─────────────────────────────────────────


def _create_substrate_task(
    text: str,
    *,
    session_id: Optional[str] = None,
) -> Optional[str]:
    """Create a substrate task and return its ID, or None on failure."""
    try:
        from eos_ai.substrate.task_system import create_task

        task = create_task(text, session_id=session_id)
        return task.task_id
    except Exception as exc:
        _log(f"substrate task creation failed: {exc}")
        return None


def _get_blocked_task_titles() -> list[str]:
    """Return titles of tasks waiting on operator."""
    try:
        from eos_ai.substrate.task_system import TaskStore, TaskStatus

        store = TaskStore.default()
        blocked = store.by_status(TaskStatus.WAITING_ON_OPERATOR)
        return [t.title for t in blocked[:10]]
    except Exception as exc:
        _log(f"blocked task query failed: {exc}")
        return []


# ─── Handling strategies ─────────────────────────────────────────────────────


def _handle_status(
    intent: FounderIntent,
    *,
    session_id: Optional[str] = None,
) -> EAResponse:
    """Handle STATUS / briefing requests — EA responds directly."""
    context = build_ea_context(session_id=session_id)
    text = format_ea_response(
        primary_role=EOSRole.EA,
        delegated_role=None,
        context=context,
        summary_type="briefing",
    )
    return EAResponse(
        response_id=_new_id(),
        primary_role=EOSRole.EA,
        delegated_role=None,
        response_text=text,
        summary_type="briefing",
        intent=intent,
    )


def _handle_review(
    intent: FounderIntent,
    *,
    session_id: Optional[str] = None,
) -> EAResponse:
    """Handle REVIEW requests — EA surfaces blocked decisions."""
    blocked = _get_blocked_task_titles()
    context = build_ea_context(session_id=session_id)
    text = format_ea_response(
        primary_role=EOSRole.EA,
        delegated_role=None,
        context=context,
        summary_type="blocked_decisions",
        blocked_items=blocked,
    )
    return EAResponse(
        response_id=_new_id(),
        primary_role=EOSRole.EA,
        delegated_role=None,
        response_text=text,
        blocked_items=blocked,
        summary_type="blocked_decisions",
        intent=intent,
    )


def _handle_execution(
    intent: FounderIntent,
    *,
    session_id: Optional[str] = None,
) -> EAResponse:
    """
    Handle EXECUTION requests — EA creates substrate tasks.

    Creates one task per extracted directive, or one from the raw text
    if no directives were extracted.
    """
    created_task_ids: list[str] = []
    directives = intent.extracted_directives or [intent.raw_text]

    for directive in directives:
        task_id = _create_substrate_task(directive, session_id=session_id)
        if task_id:
            created_task_ids.append(task_id)

    context = build_ea_context(session_id=session_id)
    text = format_ea_response(
        primary_role=EOSRole.EA,
        delegated_role=None,
        context=context,
        summary_type="execution_summary",
        created_task_ids=created_task_ids,
    )
    return EAResponse(
        response_id=_new_id(),
        primary_role=EOSRole.EA,
        delegated_role=None,
        response_text=text,
        created_task_ids=created_task_ids,
        summary_type="execution_summary",
        intent=intent,
    )


def _handle_strategy(
    intent: FounderIntent,
    *,
    session_id: Optional[str] = None,
) -> EAResponse:
    """Handle STRATEGY requests — delegated to CEO, returned through EA."""
    context = build_context_for_role(EOSRole.CEO, session_id=session_id)
    text = format_ea_response(
        primary_role=EOSRole.EA,
        delegated_role=EOSRole.CEO,
        context=context,
        summary_type="strategic_recommendation",
    )
    return EAResponse(
        response_id=_new_id(),
        primary_role=EOSRole.EA,
        delegated_role=EOSRole.CEO,
        response_text=text,
        summary_type="strategic_recommendation",
        intent=intent,
    )


def _handle_portfolio(
    intent: FounderIntent,
    *,
    session_id: Optional[str] = None,
) -> EAResponse:
    """Handle PORTFOLIO requests — delegated to Portfolio Advisor, returned through EA."""
    context = build_context_for_role(EOSRole.PORTFOLIO_ADVISOR, session_id=session_id)
    text = format_ea_response(
        primary_role=EOSRole.EA,
        delegated_role=EOSRole.PORTFOLIO_ADVISOR,
        context=context,
        summary_type="portfolio_recommendation",
    )
    return EAResponse(
        response_id=_new_id(),
        primary_role=EOSRole.EA,
        delegated_role=EOSRole.PORTFOLIO_ADVISOR,
        response_text=text,
        summary_type="portfolio_recommendation",
        intent=intent,
    )


def _handle_direct_ea(
    intent: FounderIntent,
    *,
    session_id: Optional[str] = None,
) -> EAResponse:
    """Handle DIRECT_EA / UNKNOWN — EA responds with briefing."""
    context = build_ea_context(session_id=session_id)
    text = format_ea_response(
        primary_role=EOSRole.EA,
        delegated_role=None,
        context=context,
        summary_type="briefing",
    )
    return EAResponse(
        response_id=_new_id(),
        primary_role=EOSRole.EA,
        delegated_role=None,
        response_text=text,
        summary_type="briefing",
        intent=intent,
    )


# ─── Handler dispatch ────────────────────────────────────────────────────────

_HANDLERS = {
    FounderIntentType.STATUS: _handle_status,
    FounderIntentType.REVIEW: _handle_review,
    FounderIntentType.EXECUTION: _handle_execution,
    FounderIntentType.STRATEGY: _handle_strategy,
    FounderIntentType.PORTFOLIO: _handle_portfolio,
    FounderIntentType.DIRECT_EA: _handle_direct_ea,
    FounderIntentType.UNKNOWN: _handle_direct_ea,
}


# ─── Main entrypoint ─────────────────────────────────────────────────────────


def handle_founder_message(
    text: str,
    *,
    session_id: Optional[str] = None,
) -> EAResponse:
    """
    Main platform entrypoint — every founder message enters here.

    Flow:
    1. Parse founder intent (deterministic, zero LLM).
    2. Route to handler based on intent type.
    3. Handler builds context, creates substrate work if needed,
       formats response.
    4. Log decision.
    5. Return EAResponse (always EA-mediated).
    """
    # 1. Parse intent
    intent = parse_founder_intent(text)
    _log(
        f"intent={intent.intent_type.value} "
        f"role={intent.suggested_role.value} "
        f"confidence={intent.confidence}"
    )

    # 2. Route to handler
    handler = _HANDLERS.get(intent.intent_type, _handle_direct_ea)
    response = handler(intent, session_id=session_id)

    # 3. Log decision
    try:
        log = DecisionLog.default()
        log.record(
            EOSDecisionRecord(
                decision_id=f"eosd_{uuid.uuid4().hex[:12]}",
                source_intent_id=intent.intent_id,
                primary_role=response.primary_role.value,
                delegated_role=(
                    response.delegated_role.value if response.delegated_role else None
                ),
                summary=(f"{intent.intent_type.value} → {response.summary_type}"),
                created_task_ids=response.created_task_ids,
            )
        )
    except Exception as exc:
        _log(f"decision log failed: {exc}")

    return response
