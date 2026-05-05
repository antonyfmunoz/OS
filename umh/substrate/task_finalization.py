"""Stub for task finalization after pseudolive/webhook delivery.

Placeholder implementation that satisfies imports from
discord/bot.py and webhooks/cc_receiver.py. Returns a
FinalizationResult with safe defaults (no-op).

Replace with full implementation when clear/readiness
logic is built out.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from enum import Enum
from typing import Any


_LOG_PREFIX = "[substrate.task_finalization:stub]"


def _log(msg: str) -> None:
    print(f"{_LOG_PREFIX} {msg}", file=sys.stderr)


class FinalizationStage(Enum):
    """Tracks how far finalization progressed."""

    NOT_STARTED = "not_started"
    DELIVERY_RECORDED = "delivery_recorded"
    CLEAR_EVALUATED = "clear_evaluated"
    COMPLETE = "complete"


@dataclass
class FinalizationResult:
    """Return type for finalize_completed_task."""

    success: bool = True
    clear_executed: bool = False
    clear_readiness: bool = False
    clear_stalled_safe: bool = False
    stage: FinalizationStage = FinalizationStage.COMPLETE


def finalize_completed_task(
    *,
    delivery_success: bool = True,
    delivery_mode: str = "",
    source_session: str = "",
    role: str = "",
    interface: str = "",
    final_output: str = "",
    clear_target: str = "vps",
    correlation_id: str = "",
    auto_clear: Any = None,
    **kwargs: Any,
) -> FinalizationResult:
    """Stub: record delivery and evaluate clear eligibility.

    Currently returns a no-op result. Full implementation will
    evaluate session readiness, stalled-safe conditions, and
    optionally execute auto-clear.
    """
    _log(
        f"called: session={source_session} mode={delivery_mode} "
        f"interface={interface} delivery_ok={delivery_success}"
    )
    return FinalizationResult(
        success=delivery_success,
        clear_executed=False,
        clear_readiness=False,
        clear_stalled_safe=False,
        stage=FinalizationStage.COMPLETE,
    )
