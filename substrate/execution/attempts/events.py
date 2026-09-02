"""Execution-slice event emission on the ONE shared EventSpine.

No new JSONL event authority is created here (Convergence Law): every execution
event lands on the single process-wide persisted spine
(``get_shared_event_spine()`` → ``<runtime-state>/events/organism_events.jsonl``)
under ``EventDomain.EXECUTION``, extending the Wave 1 correlation chain

    conversation_id → message_id → intent_id → … → plan_record_id
    → decision_ref → grant_id → task_id → attempt_id → proof_id

Emission never raises: an observability failure must never break a governed
execution mutation.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

_SOURCE = "execution_attempts"


def emit_execution_event(
    event_type: str,
    data: dict[str, Any],
    correlation_id: str = "",
) -> str:
    """Emit one ``execution.*`` event on the shared spine. Returns the event_id
    (empty string on any failure — the caller stamps it onto the attempt
    transition only when non-empty)."""
    try:
        from substrate.organism.event_spine import EventDomain, get_shared_event_spine

        event = get_shared_event_spine().emit(
            domain=EventDomain.EXECUTION,
            event_type=event_type,
            source=_SOURCE,
            data=data,
            correlation_id=correlation_id or None,
        )
        return getattr(event, "event_id", "") or ""
    except Exception as exc:  # observability must never break a mutation
        logger.debug("execution event emit failed (%s): %s", event_type, exc)
        return ""


__all__ = ["emit_execution_event"]
