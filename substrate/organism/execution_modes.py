"""Execution Modes — governed transition from observation to action.

Four execution classes with increasing autonomy:
  1. OBSERVE    — read-only, no mutations
  2. RECOMMEND  — produce action plans only
  3. ASSISTED   — require operator approval before execution
  4. AUTONOMOUS — bounded policy-controlled execution

All execution modes are:
  - logged (audit trail)
  - governed (mode transitions require justification)
  - recoverable (state can be rolled back)

The organism starts in OBSERVE mode and earns higher autonomy
through demonstrated reliability.

UMH substrate subsystem. Instance-agnostic.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class ExecutionMode(str, Enum):
    OBSERVE = "observe"
    RECOMMEND = "recommend"
    ASSISTED = "assisted"
    AUTONOMOUS = "autonomous"


class TransitionReason(str, Enum):
    RELIABILITY_THRESHOLD = "reliability_threshold"
    OPERATOR_PROMOTION = "operator_promotion"
    OPERATOR_DEMOTION = "operator_demotion"
    FAILURE_DEMOTION = "failure_demotion"
    GOVERNANCE_OVERRIDE = "governance_override"
    SYSTEM_STARTUP = "system_startup"


@dataclass
class ModeTransition:
    from_mode: ExecutionMode
    to_mode: ExecutionMode
    reason: TransitionReason
    justification: str = ""
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "from_mode": self.from_mode.value,
            "to_mode": self.to_mode.value,
            "reason": self.reason.value,
            "justification": self.justification,
            "timestamp": self.timestamp,
        }


@dataclass
class ExecutionDecision:
    task_id: str
    mode: ExecutionMode
    action_description: str
    approved: bool = False
    executed: bool = False
    result: str = ""
    reversible: bool = True
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "mode": self.mode.value,
            "action": self.action_description,
            "approved": self.approved,
            "executed": self.executed,
            "result": self.result[:200] if self.result else "",
            "reversible": self.reversible,
            "timestamp": self.timestamp,
        }


_MODE_HIERARCHY = {
    ExecutionMode.OBSERVE: 0,
    ExecutionMode.RECOMMEND: 1,
    ExecutionMode.ASSISTED: 2,
    ExecutionMode.AUTONOMOUS: 3,
}

_PROMOTION_THRESHOLDS = {
    ExecutionMode.RECOMMEND: 0.8,
    ExecutionMode.ASSISTED: 0.9,
    ExecutionMode.AUTONOMOUS: 0.95,
}

_MAX_DECISIONS = 1000
_MAX_TRANSITIONS = 200


class ExecutionModeManager:
    """Manages the organism's execution autonomy level.

    Tracks reliability and governs transitions between modes.
    Higher modes unlock more autonomous execution capability.
    """

    def __init__(
        self,
        initial_mode: ExecutionMode = ExecutionMode.OBSERVE,
        event_spine: Any | None = None,
    ) -> None:
        self._current_mode = initial_mode
        self._event_spine = event_spine
        self._transitions: list[ModeTransition] = []
        self._decisions: list[ExecutionDecision] = []
        self._success_count: int = 0
        self._failure_count: int = 0

    @property
    def current_mode(self) -> ExecutionMode:
        return self._current_mode

    @property
    def reliability(self) -> float:
        total = self._success_count + self._failure_count
        if total == 0:
            return 0.0
        return self._success_count / total

    def can_execute(self, task_requires_mode: ExecutionMode = ExecutionMode.OBSERVE) -> bool:
        return _MODE_HIERARCHY[self._current_mode] >= _MODE_HIERARCHY[task_requires_mode]

    def propose_action(
        self,
        task_id: str,
        action_description: str,
        required_mode: ExecutionMode = ExecutionMode.ASSISTED,
        reversible: bool = True,
    ) -> ExecutionDecision:
        decision = ExecutionDecision(
            task_id=task_id,
            mode=self._current_mode,
            action_description=action_description,
            reversible=reversible,
        )

        if self.can_execute(required_mode):
            if self._current_mode == ExecutionMode.AUTONOMOUS:
                decision.approved = True
            elif self._current_mode == ExecutionMode.ASSISTED:
                decision.approved = False
            elif self._current_mode == ExecutionMode.RECOMMEND:
                decision.approved = False
            else:
                decision.approved = False
        else:
            decision.approved = False

        if len(self._decisions) >= _MAX_DECISIONS:
            self._decisions = self._decisions[-(_MAX_DECISIONS // 2):]
        self._decisions.append(decision)

        return decision

    def record_outcome(self, task_id: str, success: bool, result: str = "") -> None:
        if success:
            self._success_count += 1
        else:
            self._failure_count += 1

        for d in reversed(self._decisions):
            if d.task_id == task_id:
                d.executed = True
                d.result = result
                break

        self._check_auto_transition()

    def promote(
        self,
        to_mode: ExecutionMode,
        reason: TransitionReason = TransitionReason.OPERATOR_PROMOTION,
        justification: str = "",
    ) -> bool:
        if _MODE_HIERARCHY[to_mode] <= _MODE_HIERARCHY[self._current_mode]:
            return False
        return self._transition(to_mode, reason, justification)

    def demote(
        self,
        to_mode: ExecutionMode,
        reason: TransitionReason = TransitionReason.OPERATOR_DEMOTION,
        justification: str = "",
    ) -> bool:
        if _MODE_HIERARCHY[to_mode] >= _MODE_HIERARCHY[self._current_mode]:
            return False
        return self._transition(to_mode, reason, justification)

    def _transition(
        self,
        to_mode: ExecutionMode,
        reason: TransitionReason,
        justification: str,
    ) -> bool:
        transition = ModeTransition(
            from_mode=self._current_mode,
            to_mode=to_mode,
            reason=reason,
            justification=justification,
        )

        if len(self._transitions) >= _MAX_TRANSITIONS:
            self._transitions = self._transitions[-(_MAX_TRANSITIONS // 2):]
        self._transitions.append(transition)

        old = self._current_mode
        self._current_mode = to_mode

        logger.info(
            "execution mode transition: %s → %s (reason=%s)",
            old.value, to_mode.value, reason.value,
        )

        if self._event_spine is not None:
            from substrate.organism.event_spine import EventDomain, EventPriority
            self._event_spine.emit(
                EventDomain.GOVERNANCE,
                "execution_mode_changed",
                "execution_mode_manager",
                transition.to_dict(),
                priority=EventPriority.HIGH,
            )

        return True

    def _check_auto_transition(self) -> None:
        rel = self.reliability
        current_level = _MODE_HIERARCHY[self._current_mode]

        if self._failure_count > 0 and rel < 0.5 and current_level > 0:
            modes = sorted(_MODE_HIERARCHY, key=lambda m: _MODE_HIERARCHY[m])
            target = modes[max(0, current_level - 1)]
            self._transition(
                target,
                TransitionReason.FAILURE_DEMOTION,
                f"reliability dropped to {rel:.2f}",
            )
            return

        for mode, threshold in _PROMOTION_THRESHOLDS.items():
            mode_level = _MODE_HIERARCHY[mode]
            if mode_level == current_level + 1 and rel >= threshold:
                total = self._success_count + self._failure_count
                if total >= 10:
                    self._transition(
                        mode,
                        TransitionReason.RELIABILITY_THRESHOLD,
                        f"reliability {rel:.2f} >= {threshold}",
                    )
                break

    def transition_history(self, limit: int = 20) -> list[dict[str, Any]]:
        return [t.to_dict() for t in self._transitions[-limit:]]

    def to_dict(self) -> dict[str, Any]:
        return {
            "current_mode": self._current_mode.value,
            "reliability": round(self.reliability, 4),
            "success_count": self._success_count,
            "failure_count": self._failure_count,
            "total_decisions": len(self._decisions),
            "transitions": len(self._transitions),
            "last_transition": (
                self._transitions[-1].to_dict() if self._transitions else None
            ),
        }
