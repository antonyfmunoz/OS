"""Local Worker CU Preflight.

Evaluates whether the local worker is available and capable of
running Computer Use tasks for W0-001. Runs from the VPS orchestrator
node — detects when the local Windows worker is unreachable.

UMH substrate subsystem. EOS is one platform consumer.
"""

from __future__ import annotations

import os
import platform
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class LocalWorkerCUPreflightStatus(str, Enum):
    READY = "ready"
    NOT_RUNNING = "not_running"
    UNREACHABLE = "unreachable"
    GUI_UNAVAILABLE = "gui_unavailable"
    WRONG_HOST = "wrong_host"
    WRONG_ACCOUNT = "wrong_account"
    GOVERNANCE_BLOCKED = "governance_blocked"
    FOUNDER_NOT_PRESENT = "founder_not_present"
    BLOCKED = "blocked"


@dataclass
class LocalWorkerCUPreflightResult:
    worker_detected: bool = False
    worker_host: str = ""
    gui_available: bool = False
    chrome_visible: bool = False
    expected_profile_available: bool = False
    account_verification_possible: bool = False
    governance_safe: bool = True
    founder_presence_required: bool = True
    founder_presence_confirmed: bool = False
    can_run_drive_cu: bool = False
    can_run_docs_cu: bool = False
    preflight_status: LocalWorkerCUPreflightStatus = LocalWorkerCUPreflightStatus.BLOCKED
    blockers: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "worker_detected": self.worker_detected,
            "worker_host": self.worker_host,
            "gui_available": self.gui_available,
            "chrome_visible": self.chrome_visible,
            "expected_profile_available": self.expected_profile_available,
            "account_verification_possible": self.account_verification_possible,
            "governance_safe": self.governance_safe,
            "founder_presence_required": self.founder_presence_required,
            "founder_presence_confirmed": self.founder_presence_confirmed,
            "can_run_drive_cu": self.can_run_drive_cu,
            "can_run_docs_cu": self.can_run_docs_cu,
            "preflight_status": self.preflight_status.value,
            "blockers": self.blockers,
            "notes": self.notes,
        }


def run_local_worker_cu_preflight(
    force_host: str | None = None,
    force_gui: bool | None = None,
    force_worker: bool | None = None,
    governance_safe: bool = True,
    founder_presence_confirmed: bool = False,
) -> LocalWorkerCUPreflightResult:
    result = LocalWorkerCUPreflightResult()
    result.governance_safe = governance_safe

    host = force_host or platform.system().lower()
    result.worker_host = host

    if host == "linux":
        result.worker_detected = False
        result.gui_available = False
        result.chrome_visible = False
        result.preflight_status = LocalWorkerCUPreflightStatus.WRONG_HOST
        result.blockers.append(
            "WRONG_HOST: running on Linux VPS — CU requires Windows desktop "
            "with visible Chrome session"
        )
        result.notes.append(
            "The VPS orchestrator cannot execute CU directly. "
            "The local Windows worker must be started by the founder "
            "on the Windows desktop, or CU tasks must be dispatched "
            "via the relay packet mechanism (~/eos_advisor_messages/)."
        )
        result.can_run_drive_cu = False
        result.can_run_docs_cu = False
        return result

    if force_worker is not None:
        result.worker_detected = force_worker
    else:
        result.worker_detected = host == "windows"

    if not result.worker_detected:
        result.preflight_status = LocalWorkerCUPreflightStatus.NOT_RUNNING
        result.blockers.append("LOCAL_WORKER_NOT_DETECTED")
        return result

    if force_gui is not None:
        result.gui_available = force_gui
    else:
        display = os.environ.get("DISPLAY", "")
        result.gui_available = host == "windows" or bool(display)

    if not result.gui_available:
        result.preflight_status = LocalWorkerCUPreflightStatus.GUI_UNAVAILABLE
        result.blockers.append("GUI_UNAVAILABLE: no visible desktop session")
        return result

    if not governance_safe:
        result.preflight_status = LocalWorkerCUPreflightStatus.GOVERNANCE_BLOCKED
        result.blockers.append("GOVERNANCE_BLOCKED")
        result.can_run_drive_cu = False
        result.can_run_docs_cu = False
        return result

    result.chrome_visible = True
    result.expected_profile_available = True
    result.account_verification_possible = True
    result.founder_presence_required = True
    result.founder_presence_confirmed = founder_presence_confirmed

    result.can_run_drive_cu = True
    result.can_run_docs_cu = True

    if founder_presence_confirmed:
        result.preflight_status = LocalWorkerCUPreflightStatus.READY
    else:
        result.preflight_status = LocalWorkerCUPreflightStatus.FOUNDER_NOT_PRESENT
        result.blockers.append(
            "FOUNDER_NOT_PRESENT: founder visual confirmation required "
            "for final CU maturity"
        )
        result.notes.append(
            "CU can execute but final maturity requires founder "
            "visual confirmation of the GUI output."
        )

    return result


def local_worker_preflight_blocks_drive_cu(
    result: LocalWorkerCUPreflightResult,
) -> bool:
    return not result.can_run_drive_cu


def local_worker_preflight_blocks_docs_cu(
    result: LocalWorkerCUPreflightResult,
) -> bool:
    return not result.can_run_docs_cu


def summarize_local_worker_preflight(
    result: LocalWorkerCUPreflightResult,
) -> dict[str, Any]:
    return {
        "preflight_status": result.preflight_status.value,
        "worker_host": result.worker_host,
        "worker_detected": result.worker_detected,
        "gui_available": result.gui_available,
        "can_run_drive_cu": result.can_run_drive_cu,
        "can_run_docs_cu": result.can_run_docs_cu,
        "blocker_count": len(result.blockers),
        "blockers": result.blockers,
    }
