"""
Work order contracts for Phase 93R.1.

Additive-only module. Does not import from or modify any existing
substrate module (actions.py, station.py, station_bus.py, control_commands.py).
These types sit alongside SafeAction and ControlCommand — they do not replace them.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class WorkOrderStatus(str, Enum):
    CREATED = "CREATED"
    QUEUED = "QUEUED"
    SENT_TO_LOCAL = "SENT_TO_LOCAL"
    CLAIMED_BY_LOCAL = "CLAIMED_BY_LOCAL"
    IN_PROGRESS = "IN_PROGRESS"
    WAITING_FOR_USER_APPROVAL = "WAITING_FOR_USER_APPROVAL"
    COMPLETE = "COMPLETE"
    PARTIAL = "PARTIAL"
    BLOCKED = "BLOCKED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


ALLOWED_TRANSITIONS: dict[WorkOrderStatus, set[WorkOrderStatus]] = {
    WorkOrderStatus.CREATED: {WorkOrderStatus.QUEUED, WorkOrderStatus.CANCELLED},
    WorkOrderStatus.QUEUED: {WorkOrderStatus.SENT_TO_LOCAL, WorkOrderStatus.CANCELLED},
    WorkOrderStatus.SENT_TO_LOCAL: {WorkOrderStatus.CLAIMED_BY_LOCAL, WorkOrderStatus.CANCELLED},
    WorkOrderStatus.CLAIMED_BY_LOCAL: {WorkOrderStatus.IN_PROGRESS, WorkOrderStatus.CANCELLED},
    WorkOrderStatus.IN_PROGRESS: {
        WorkOrderStatus.WAITING_FOR_USER_APPROVAL,
        WorkOrderStatus.COMPLETE,
        WorkOrderStatus.PARTIAL,
        WorkOrderStatus.BLOCKED,
        WorkOrderStatus.FAILED,
        WorkOrderStatus.CANCELLED,
    },
    WorkOrderStatus.WAITING_FOR_USER_APPROVAL: {
        WorkOrderStatus.IN_PROGRESS,
        WorkOrderStatus.CANCELLED,
    },
    WorkOrderStatus.COMPLETE: set(),
    WorkOrderStatus.PARTIAL: set(),
    WorkOrderStatus.BLOCKED: set(),
    WorkOrderStatus.FAILED: set(),
    WorkOrderStatus.CANCELLED: set(),
}


class WorkOrderTaskType(str, Enum):
    LOCAL_SOURCE_INVENTORY = "LOCAL_SOURCE_INVENTORY"
    GOOGLE_WORKSPACE_DISCOVERY = "GOOGLE_WORKSPACE_DISCOVERY"
    GOOGLE_DOCS_READ_EXPORT = "GOOGLE_DOCS_READ_EXPORT"
    AI_CHAT_EXPORT = "AI_CHAT_EXPORT"
    CUSTOM_GPT_CONFIG_CAPTURE = "CUSTOM_GPT_CONFIG_CAPTURE"
    OBSIDIAN_VAULT_READ = "OBSIDIAN_VAULT_READ"
    BROWSER_READ_ONLY_NAVIGATION = "BROWSER_READ_ONLY_NAVIGATION"
    SCREENSHOT_EVIDENCE_CAPTURE = "SCREENSHOT_EVIDENCE_CAPTURE"
    RESULT_WRITEBACK = "RESULT_WRITEBACK"


class AuthorityMode(str, Enum):
    READ_ONLY = "READ_ONLY"
    APPROVAL_REQUIRED = "APPROVAL_REQUIRED"
    BLOCKED = "BLOCKED"
    FUTURE_ONLY = "FUTURE_ONLY"


DEFAULT_AUTHORITY: dict[WorkOrderTaskType, AuthorityMode] = {
    WorkOrderTaskType.LOCAL_SOURCE_INVENTORY: AuthorityMode.READ_ONLY,
    WorkOrderTaskType.GOOGLE_WORKSPACE_DISCOVERY: AuthorityMode.READ_ONLY,
    WorkOrderTaskType.GOOGLE_DOCS_READ_EXPORT: AuthorityMode.APPROVAL_REQUIRED,
    WorkOrderTaskType.AI_CHAT_EXPORT: AuthorityMode.APPROVAL_REQUIRED,
    WorkOrderTaskType.CUSTOM_GPT_CONFIG_CAPTURE: AuthorityMode.APPROVAL_REQUIRED,
    WorkOrderTaskType.OBSIDIAN_VAULT_READ: AuthorityMode.READ_ONLY,
    WorkOrderTaskType.BROWSER_READ_ONLY_NAVIGATION: AuthorityMode.READ_ONLY,
    WorkOrderTaskType.SCREENSHOT_EVIDENCE_CAPTURE: AuthorityMode.APPROVAL_REQUIRED,
    WorkOrderTaskType.RESULT_WRITEBACK: AuthorityMode.READ_ONLY,
}


class SensitivityLevel(str, Enum):
    PUBLIC = "PUBLIC"
    PRIVATE = "PRIVATE"
    SENSITIVE = "SENSITIVE"
    MIXED = "MIXED"


UNIVERSAL_BLOCKED_ACTIONS: frozenset[str] = frozenset(
    {
        "edit_documents",
        "delete_files",
        "change_permissions",
        "send_emails",
        "send_dms",
        "post_content",
        "change_account_settings",
        "capture_credentials",
        "process_payments",
        "subscribe_unsubscribe",
        "purchase",
        "install_software",
        "modify_system_settings",
        "autonomous_social_actions",
        "promote_memory_without_governance",
        "run_arbitrary_shell_commands",
    }
)


def _generate_work_order_id() -> str:
    return f"wo_{uuid.uuid4().hex[:12]}"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class WorkOrder:
    work_order_id: str
    created_by_node: str
    assigned_to_node: str
    task_type: WorkOrderTaskType
    objective: str
    source_targets: list[str]
    allowed_actions: list[str]
    blocked_actions: list[str]
    authority_mode: AuthorityMode
    sensitivity_level: SensitivityLevel
    evidence_required: bool
    expected_outputs: list[str]
    timeout_minutes: int
    status: WorkOrderStatus = WorkOrderStatus.CREATED
    created_at: str = field(default_factory=_now_iso)
    claimed_at: str | None = None
    completed_at: str | None = None
    result_path: str | None = None
    required_approvals: list[str] = field(default_factory=list)
    result_schema: str | None = None
    audit_notes: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.work_order_id:
            self.work_order_id = _generate_work_order_id()
        if not self.audit_notes:
            self.audit_notes = [f"{_now_iso()} | CREATED by {self.created_by_node}"]
        for blocked in UNIVERSAL_BLOCKED_ACTIONS:
            if blocked not in self.blocked_actions:
                self.blocked_actions.append(blocked)

    def transition(self, new_status: WorkOrderStatus, detail: str = "") -> None:
        allowed = ALLOWED_TRANSITIONS.get(self.status, set())
        if new_status not in allowed:
            raise ValueError(f"Cannot transition from {self.status.value} to {new_status.value}")
        old = self.status
        self.status = new_status
        if new_status == WorkOrderStatus.CLAIMED_BY_LOCAL and not self.claimed_at:
            self.claimed_at = _now_iso()
        if new_status in (
            WorkOrderStatus.COMPLETE,
            WorkOrderStatus.PARTIAL,
            WorkOrderStatus.FAILED,
        ):
            self.completed_at = _now_iso()
        note = f"{_now_iso()} | {old.value} → {new_status.value}"
        if detail:
            note += f" — {detail}"
        self.audit_notes.append(note)

    def to_dict(self) -> dict[str, Any]:
        return {
            "work_order_id": self.work_order_id,
            "created_by_node": self.created_by_node,
            "assigned_to_node": self.assigned_to_node,
            "task_type": self.task_type.value,
            "objective": self.objective,
            "source_targets": self.source_targets,
            "allowed_actions": self.allowed_actions,
            "blocked_actions": self.blocked_actions,
            "required_approvals": self.required_approvals,
            "authority_mode": self.authority_mode.value,
            "sensitivity_level": self.sensitivity_level.value,
            "evidence_required": self.evidence_required,
            "expected_outputs": self.expected_outputs,
            "result_schema": self.result_schema,
            "timeout_minutes": self.timeout_minutes,
            "status": self.status.value,
            "created_at": self.created_at,
            "claimed_at": self.claimed_at,
            "completed_at": self.completed_at,
            "result_path": self.result_path,
            "audit_notes": self.audit_notes,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> WorkOrder:
        return cls(
            work_order_id=data["work_order_id"],
            created_by_node=data["created_by_node"],
            assigned_to_node=data["assigned_to_node"],
            task_type=WorkOrderTaskType(data["task_type"]),
            objective=data["objective"],
            source_targets=data["source_targets"],
            allowed_actions=data["allowed_actions"],
            blocked_actions=data.get("blocked_actions", []),
            required_approvals=data.get("required_approvals", []),
            authority_mode=AuthorityMode(data["authority_mode"]),
            sensitivity_level=SensitivityLevel(data["sensitivity_level"]),
            evidence_required=data["evidence_required"],
            expected_outputs=data["expected_outputs"],
            result_schema=data.get("result_schema"),
            timeout_minutes=data["timeout_minutes"],
            status=WorkOrderStatus(data.get("status", "CREATED")),
            created_at=data.get("created_at", _now_iso()),
            claimed_at=data.get("claimed_at"),
            completed_at=data.get("completed_at"),
            result_path=data.get("result_path"),
            audit_notes=data.get("audit_notes", []),
        )


@dataclass
class WorkOrderResult:
    work_order_id: str
    result_id: str
    schema_version: str
    executing_node: str
    execution_start: str
    execution_end: str
    execution_duration_minutes: int
    status: WorkOrderStatus
    sources_accessed: list[str]
    safety_confirmation: dict[str, Any]
    approval_log: list[dict[str, Any]]
    audit_notes: list[str]
    evidence_paths: list[str] = field(default_factory=list)
    evidence_transferred: bool = False
    data: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "work_order_id": self.work_order_id,
            "result_id": self.result_id,
            "schema_version": self.schema_version,
            "executing_node": self.executing_node,
            "execution_start": self.execution_start,
            "execution_end": self.execution_end,
            "execution_duration_minutes": self.execution_duration_minutes,
            "status": self.status.value,
            "sources_accessed": self.sources_accessed,
            "safety_confirmation": self.safety_confirmation,
            "approval_log": self.approval_log,
            "audit_notes": self.audit_notes,
            "evidence_paths": self.evidence_paths,
            "evidence_transferred": self.evidence_transferred,
            "data": self.data,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> WorkOrderResult:
        return cls(
            work_order_id=data["work_order_id"],
            result_id=data["result_id"],
            schema_version=data["schema_version"],
            executing_node=data["executing_node"],
            execution_start=data["execution_start"],
            execution_end=data["execution_end"],
            execution_duration_minutes=data["execution_duration_minutes"],
            status=WorkOrderStatus(data["status"]),
            sources_accessed=data["sources_accessed"],
            safety_confirmation=data["safety_confirmation"],
            approval_log=data["approval_log"],
            audit_notes=data["audit_notes"],
            evidence_paths=data.get("evidence_paths", []),
            evidence_transferred=data.get("evidence_transferred", False),
            data=data.get("data", {}),
        )
