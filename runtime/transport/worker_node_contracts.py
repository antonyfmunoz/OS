"""
Worker node organism contracts for Phase 94D.4.

Defines worker modes, states, profiles, and event types for execution
nodes that operate like organism cells — perceive, plan, execute, observe,
report, emit feedback.

Workers default to AUTO mode. Manual local fallback requires explicit selection.
"""

from __future__ import annotations

import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class WorkerMode(str, Enum):
    AUTO = "auto"
    MANUAL_FALLBACK = "manual_fallback"
    PAUSED = "paused"
    DISABLED = "disabled"


class WorkerState(str, Enum):
    BOOTING = "booting"
    IDLE = "idle"
    CLAIMING_WORK = "claiming_work"
    VALIDATING_WORK = "validating_work"
    PLANNING = "planning"
    WAITING_FOR_ADVISOR_APPROVAL = "waiting_for_advisor_approval"
    EXECUTING = "executing"
    OBSERVING = "observing"
    REPORTING = "reporting"
    FEEDBACK_SYNC = "feedback_sync"
    BLOCKED = "blocked"
    FAILED = "failed"
    COMPLETE = "complete"


TERMINAL_STATES: frozenset[WorkerState] = frozenset(
    {
        WorkerState.FAILED,
        WorkerState.COMPLETE,
    }
)

WORKER_STATE_TRANSITIONS: dict[WorkerState, set[WorkerState]] = {
    WorkerState.BOOTING: {WorkerState.IDLE, WorkerState.FAILED},
    WorkerState.IDLE: {WorkerState.CLAIMING_WORK},
    WorkerState.CLAIMING_WORK: {WorkerState.VALIDATING_WORK, WorkerState.IDLE, WorkerState.FAILED},
    WorkerState.VALIDATING_WORK: {WorkerState.PLANNING, WorkerState.BLOCKED, WorkerState.FAILED},
    WorkerState.PLANNING: {
        WorkerState.EXECUTING,
        WorkerState.WAITING_FOR_ADVISOR_APPROVAL,
        WorkerState.BLOCKED,
    },
    WorkerState.WAITING_FOR_ADVISOR_APPROVAL: {
        WorkerState.EXECUTING,
        WorkerState.BLOCKED,
        WorkerState.FAILED,
    },
    WorkerState.EXECUTING: {
        WorkerState.OBSERVING,
        WorkerState.WAITING_FOR_ADVISOR_APPROVAL,
        WorkerState.REPORTING,
        WorkerState.BLOCKED,
        WorkerState.FAILED,
    },
    WorkerState.OBSERVING: {WorkerState.EXECUTING, WorkerState.REPORTING, WorkerState.BLOCKED},
    WorkerState.REPORTING: {WorkerState.FEEDBACK_SYNC, WorkerState.EXECUTING, WorkerState.COMPLETE},
    WorkerState.FEEDBACK_SYNC: {WorkerState.IDLE, WorkerState.COMPLETE},
    WorkerState.BLOCKED: {
        WorkerState.EXECUTING,
        WorkerState.WAITING_FOR_ADVISOR_APPROVAL,
        WorkerState.FAILED,
    },
    WorkerState.FAILED: set(),
    WorkerState.COMPLETE: set(),
}


class WorkerRole(str, Enum):
    GUI_COMPUTER_USE = "gui_computer_use"
    BROWSER_AUTOMATION = "browser_automation"
    API_WORKER = "api_worker"
    FILE_WORKER = "file_worker"
    LLM_WORKER = "llm_worker"
    MANUAL_OPERATOR = "manual_operator"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_id() -> str:
    return uuid.uuid4().hex[:12]


@dataclass
class WorkerProfile:
    worker_id: str
    node_id: str
    roles: list[WorkerRole]
    capabilities: list[str]
    mode: WorkerMode = WorkerMode.AUTO
    max_concurrent_work_orders: int = 1
    metadata: dict[str, Any] = field(default_factory=dict)

    def supports_capability(self, cap: str) -> bool:
        return cap in self.capabilities

    def is_auto(self) -> bool:
        return self.mode == WorkerMode.AUTO

    def to_dict(self) -> dict[str, Any]:
        return {
            "worker_id": self.worker_id,
            "node_id": self.node_id,
            "roles": [r.value for r in self.roles],
            "capabilities": self.capabilities,
            "mode": self.mode.value,
            "max_concurrent_work_orders": self.max_concurrent_work_orders,
            "metadata": self.metadata,
        }


@dataclass
class WorkerRuntimeState:
    worker_id: str
    state: WorkerState
    mode: WorkerMode
    active_work_order_id: str | None = None
    current_action: str | None = None
    pending_approval_id: str | None = None
    actions_completed: int = 0
    actions_remaining: int = 0
    last_state_change: str = field(default_factory=_now_iso)
    error_detail: str | None = None

    def transition(self, new_state: WorkerState) -> None:
        allowed = WORKER_STATE_TRANSITIONS.get(self.state, set())
        if new_state not in allowed:
            raise ValueError(f"Invalid worker transition: {self.state.value} → {new_state.value}")
        self.state = new_state
        self.last_state_change = _now_iso()

    def is_terminal(self) -> bool:
        return self.state in TERMINAL_STATES

    def to_dict(self) -> dict[str, Any]:
        return {
            "worker_id": self.worker_id,
            "state": self.state.value,
            "mode": self.mode.value,
            "active_work_order_id": self.active_work_order_id,
            "current_action": self.current_action,
            "pending_approval_id": self.pending_approval_id,
            "actions_completed": self.actions_completed,
            "actions_remaining": self.actions_remaining,
            "last_state_change": self.last_state_change,
            "error_detail": self.error_detail,
        }


@dataclass
class WorkerAction:
    action_id: str = field(default_factory=_new_id)
    action_type: str = ""
    target: str = ""
    description: str = ""
    requires_approval: bool = False
    risk_level: str = "low"
    backend: str = "gui_computer_use"
    work_order_id: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class WorkerFeedbackEvent:
    event_id: str = field(default_factory=_new_id)
    worker_id: str = ""
    work_order_id: str = ""
    event_type: str = ""
    detail: str = ""
    data: dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> WorkerFeedbackEvent:
        return cls(
            event_id=data.get("event_id", _new_id()),
            worker_id=data.get("worker_id", ""),
            work_order_id=data.get("work_order_id", ""),
            event_type=data.get("event_type", ""),
            detail=data.get("detail", ""),
            data=data.get("data", {}),
            timestamp=data.get("timestamp", _now_iso()),
        )
