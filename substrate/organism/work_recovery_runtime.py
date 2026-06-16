"""Work Recovery Runtime — maps work states to recovery actions.

Composes WorkGraph (statuses) + ContinuityRuntime (checkpoints) +
ExecutionCoordinator (lifecycle events) to determine what can be
retried, resumed, unblocked, or escalated.

Gate 3 — Governed Work Runtime. UMH substrate subsystem. Instance-agnostic.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Enums
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class RecoveryState(str, Enum):
    ACTIVE = "active"
    BLOCKED = "blocked"
    FAILED = "failed"
    INTERRUPTED = "interrupted"
    RESUMABLE = "resumable"
    COMPLETE = "complete"


class RecoveryActionType(str, Enum):
    RETRY = "retry"
    RESUME = "resume"
    UNBLOCK = "unblock"
    ESCALATE = "escalate"
    ABANDON = "abandon"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Data classes
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


@dataclass
class RecoveryAction:
    action: RecoveryActionType = RecoveryActionType.RETRY
    work_id: str = ""
    reason: str = ""
    auto_recoverable: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "action": self.action.value
            if isinstance(self.action, RecoveryActionType) else self.action,
            "work_id": self.work_id,
            "reason": self.reason,
            "auto_recoverable": self.auto_recoverable,
        }


@dataclass
class RecoveryAssessment:
    work_id: str = ""
    state: RecoveryState = RecoveryState.ACTIVE
    actions: list[RecoveryAction] = field(default_factory=list)
    assessed_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "work_id": self.work_id,
            "state": self.state.value
            if isinstance(self.state, RecoveryState) else self.state,
            "actions": [a.to_dict() for a in self.actions],
            "assessed_at": self.assessed_at,
        }


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Status → RecoveryState mapping
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

_FAILED_STATUSES = frozenset({"failed"})
_BLOCKED_STATUSES = frozenset({"blocked"})
_INTERRUPTED_STATUSES = frozenset({"paused", "reconverging"})
_COMPLETE_STATUSES = frozenset({
    "completed", "rejected", "superseded", "archived", "cancelled", "cleaned_up",
})


def _classify_recovery_state(status: str) -> RecoveryState:
    if status in _FAILED_STATUSES:
        return RecoveryState.FAILED
    if status in _BLOCKED_STATUSES:
        return RecoveryState.BLOCKED
    if status in _INTERRUPTED_STATUSES:
        return RecoveryState.INTERRUPTED
    if status in _COMPLETE_STATUSES:
        return RecoveryState.COMPLETE
    return RecoveryState.ACTIVE


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# WorkRecoveryRuntime
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class WorkRecoveryRuntime:
    """Maps work states to recovery actions.

    Composes:
      - WorkGraph: live work state projection
      - ContinuityRuntime: checkpoint/resume data
    """

    def __init__(
        self,
        work_graph: Any | None = None,
        continuity_runtime: Any | None = None,
    ) -> None:
        self._work_graph = work_graph
        self._continuity_runtime = continuity_runtime

    @property
    def work_graph(self) -> Any | None:
        if self._work_graph is None:
            try:
                from substrate.organism.work_graph import WorkGraph
                self._work_graph = WorkGraph()
            except Exception:
                logger.debug("WorkGraph unavailable")
        return self._work_graph

    @property
    def continuity_runtime(self) -> Any | None:
        if self._continuity_runtime is None:
            try:
                from substrate.organism.continuity_runtime import ContinuityRuntime
                self._continuity_runtime = ContinuityRuntime()
            except Exception:
                logger.debug("ContinuityRuntime unavailable")
        return self._continuity_runtime

    def assess(self, work_id: str) -> RecoveryAssessment:
        """Assess recovery state and available actions for a work item."""
        if self.work_graph is None:
            return RecoveryAssessment(
                work_id=work_id,
                state=RecoveryState.ACTIVE,
            )

        node = self.work_graph.node(work_id)
        if node is None:
            return RecoveryAssessment(
                work_id=work_id,
                state=RecoveryState.COMPLETE,
                actions=[],
            )

        state = _classify_recovery_state(node.status)
        actions = self._determine_actions(work_id, state, node)

        if state == RecoveryState.INTERRUPTED:
            has_checkpoint = self._has_checkpoint(work_id)
            if has_checkpoint:
                state = RecoveryState.RESUMABLE

        return RecoveryAssessment(
            work_id=work_id,
            state=state,
            actions=actions,
        )

    def recovery_actions(self, work_id: str) -> list[RecoveryAction]:
        return self.assess(work_id).actions

    def interrupted_work(self) -> list[Any]:
        """All work in interrupted/paused states."""
        if self.work_graph is None:
            return []
        return [
            n for n in self.work_graph.all_work()
            if _classify_recovery_state(n.status) == RecoveryState.INTERRUPTED
        ]

    def resumable_work(self) -> list[Any]:
        """Interrupted work that has continuity checkpoints."""
        interrupted = self.interrupted_work()
        return [
            n for n in interrupted
            if self._has_checkpoint(n.node_id)
        ]

    def failed_work(self) -> list[Any]:
        """All work in failed state."""
        if self.work_graph is None:
            return []
        return [
            n for n in self.work_graph.all_work()
            if _classify_recovery_state(n.status) == RecoveryState.FAILED
        ]

    def blocked_work(self) -> list[Any]:
        """All work in blocked state."""
        if self.work_graph is None:
            return []
        return self.work_graph.blocked_work()

    def recoverable_work(self) -> list[RecoveryAssessment]:
        """All work that has at least one recovery action available."""
        if self.work_graph is None:
            return []
        results: list[RecoveryAssessment] = []
        for node in self.work_graph.all_work():
            assessment = self.assess(node.node_id)
            if assessment.actions:
                results.append(assessment)
        return results

    # ── Internal ─────────────────────────────────────────────────

    def _determine_actions(
        self,
        work_id: str,
        state: RecoveryState,
        node: Any,
    ) -> list[RecoveryAction]:
        actions: list[RecoveryAction] = []

        if state == RecoveryState.FAILED:
            risk = getattr(node, "risk_class", "low")
            actions.append(RecoveryAction(
                action=RecoveryActionType.RETRY,
                work_id=work_id,
                reason="Work failed — can be retried",
                auto_recoverable=risk in ("safe", "low"),
            ))
            actions.append(RecoveryAction(
                action=RecoveryActionType.ABANDON,
                work_id=work_id,
                reason="Abandon failed work",
                auto_recoverable=False,
            ))

        elif state == RecoveryState.BLOCKED:
            blockers = getattr(node, "blockers", []) or []
            if blockers:
                for blocker in blockers:
                    desc = getattr(blocker, "description", str(blocker))
                    actions.append(RecoveryAction(
                        action=RecoveryActionType.UNBLOCK,
                        work_id=work_id,
                        reason=f"Unblock: {desc}",
                        auto_recoverable=False,
                    ))
            else:
                actions.append(RecoveryAction(
                    action=RecoveryActionType.UNBLOCK,
                    work_id=work_id,
                    reason="Work is blocked — needs intervention",
                    auto_recoverable=False,
                ))
            actions.append(RecoveryAction(
                action=RecoveryActionType.ESCALATE,
                work_id=work_id,
                reason="Escalate blocked work",
                auto_recoverable=False,
            ))

        elif state == RecoveryState.INTERRUPTED:
            has_checkpoint = self._has_checkpoint(work_id)
            if has_checkpoint:
                actions.append(RecoveryAction(
                    action=RecoveryActionType.RESUME,
                    work_id=work_id,
                    reason="Work was interrupted — checkpoint available",
                    auto_recoverable=True,
                ))
            actions.append(RecoveryAction(
                action=RecoveryActionType.RETRY,
                work_id=work_id,
                reason="Retry interrupted work from scratch",
                auto_recoverable=False,
            ))

        return actions

    def _has_checkpoint(self, work_id: str) -> bool:
        """Check if continuity runtime has a checkpoint for this work."""
        if self.continuity_runtime is None:
            return False
        try:
            state = self.continuity_runtime.current_state()
            if state and hasattr(state, "checkpoints"):
                for cp in state.checkpoints:
                    cp_id = getattr(cp, "checkpoint_id", "")
                    cp_meta = getattr(cp, "metadata", {}) or {}
                    if cp_id == work_id or cp_meta.get("work_id") == work_id:
                        return True
        except Exception:
            pass
        return False
