"""
Computer-use backend contracts for Phase 94D.3.

Additive-only module. Defines backend classes for local execution,
selection policy, and the explicit approval requirement for browser
automation fallback.

Does not import from or modify any existing substrate module.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from runtime.transport.work_order_contracts import WorkOrderTaskType


class ComputerUseBackend(str, Enum):
    GUI_COMPUTER_USE = "GUI_COMPUTER_USE"
    BROWSER_AUTOMATION = "BROWSER_AUTOMATION"
    API_CONNECTOR = "API_CONNECTOR"
    MANUAL_FALLBACK = "MANUAL_FALLBACK"


DEFAULT_BACKEND_BY_TASK_TYPE: dict[WorkOrderTaskType, ComputerUseBackend] = {
    WorkOrderTaskType.GOOGLE_WORKSPACE_DISCOVERY: ComputerUseBackend.GUI_COMPUTER_USE,
    WorkOrderTaskType.GOOGLE_DOCS_READ_EXPORT: ComputerUseBackend.GUI_COMPUTER_USE,
    WorkOrderTaskType.AI_CHAT_EXPORT: ComputerUseBackend.GUI_COMPUTER_USE,
    WorkOrderTaskType.CUSTOM_GPT_CONFIG_CAPTURE: ComputerUseBackend.GUI_COMPUTER_USE,
    WorkOrderTaskType.OBSIDIAN_VAULT_READ: ComputerUseBackend.API_CONNECTOR,
    WorkOrderTaskType.BROWSER_READ_ONLY_NAVIGATION: ComputerUseBackend.GUI_COMPUTER_USE,
    WorkOrderTaskType.SCREENSHOT_EVIDENCE_CAPTURE: ComputerUseBackend.GUI_COMPUTER_USE,
    WorkOrderTaskType.RESULT_WRITEBACK: ComputerUseBackend.API_CONNECTOR,
    WorkOrderTaskType.LOCAL_SOURCE_INVENTORY: ComputerUseBackend.API_CONNECTOR,
}


class BackendSelectionReason(str, Enum):
    DEFAULT = "default"
    FOUNDER_OVERRIDE = "founder_override"
    FALLBACK = "fallback"
    WORK_ORDER_SPECIFIED = "work_order_specified"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class BackendPolicy:
    work_order_id: str
    task_type: WorkOrderTaskType
    selected_backend: ComputerUseBackend
    selection_reason: BackendSelectionReason
    browser_automation_allowed: bool = False
    browser_automation_approved_by: str | None = None
    browser_automation_approval_id: str | None = None
    gui_available: bool | None = None
    api_available: bool | None = None
    selected_at: str = field(default_factory=_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return {
            "work_order_id": self.work_order_id,
            "task_type": self.task_type.value,
            "selected_backend": self.selected_backend.value,
            "selection_reason": self.selection_reason.value,
            "browser_automation_allowed": self.browser_automation_allowed,
            "browser_automation_approved_by": self.browser_automation_approved_by,
            "browser_automation_approval_id": self.browser_automation_approval_id,
            "gui_available": self.gui_available,
            "api_available": self.api_available,
            "selected_at": self.selected_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> BackendPolicy:
        return cls(
            work_order_id=data["work_order_id"],
            task_type=WorkOrderTaskType(data["task_type"]),
            selected_backend=ComputerUseBackend(data["selected_backend"]),
            selection_reason=BackendSelectionReason(data["selection_reason"]),
            browser_automation_allowed=data.get("browser_automation_allowed", False),
            browser_automation_approved_by=data.get("browser_automation_approved_by"),
            browser_automation_approval_id=data.get("browser_automation_approval_id"),
            gui_available=data.get("gui_available"),
            api_available=data.get("api_available"),
            selected_at=data.get("selected_at", _now_iso()),
        )


def select_backend(
    task_type: WorkOrderTaskType,
    work_order_id: str,
    *,
    gui_available: bool = True,
    api_available: bool = False,
    founder_override: ComputerUseBackend | None = None,
    browser_automation_approved: bool = False,
    approval_id: str | None = None,
) -> BackendPolicy:
    """Select execution backend for a work order task.

    Rules:
    - Founder override wins if provided
    - Browser automation requires explicit approval
    - If GUI not available and no override, returns GUI_COMPUTER_USE
      with gui_available=False — caller must request approval for fallback
    """
    if founder_override is not None:
        reason = BackendSelectionReason.FOUNDER_OVERRIDE
        backend = founder_override
        browser_allowed = (
            backend == ComputerUseBackend.BROWSER_AUTOMATION and browser_automation_approved
        )
        return BackendPolicy(
            work_order_id=work_order_id,
            task_type=task_type,
            selected_backend=backend,
            selection_reason=reason,
            browser_automation_allowed=browser_allowed,
            browser_automation_approved_by="founder" if browser_allowed else None,
            browser_automation_approval_id=approval_id if browser_allowed else None,
            gui_available=gui_available,
            api_available=api_available,
        )

    default = DEFAULT_BACKEND_BY_TASK_TYPE.get(task_type, ComputerUseBackend.GUI_COMPUTER_USE)

    return BackendPolicy(
        work_order_id=work_order_id,
        task_type=task_type,
        selected_backend=default,
        selection_reason=BackendSelectionReason.DEFAULT,
        browser_automation_allowed=False,
        gui_available=gui_available,
        api_available=api_available,
    )


def requires_approval_for_browser_automation(policy: BackendPolicy) -> bool:
    """Check if browser automation requires explicit founder approval.

    Always True unless founder has already approved.
    """
    if policy.selected_backend != ComputerUseBackend.BROWSER_AUTOMATION:
        return False
    return not policy.browser_automation_allowed
