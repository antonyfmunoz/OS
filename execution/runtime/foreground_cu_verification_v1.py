"""Foreground Computer Use Verification v1 for the UMH substrate layer.

Enforces that CU ingestion occurs through visible foreground Chrome
on the live Windows workstation. No API fallback. No headless. No
background execution. No simulated extraction.

The founder must physically observe Chrome opening, Drive/Docs
navigation, and extraction activity.

Composes existing infrastructure:
  - ChromeVisibleLaunchProof (chrome_visible_launch.py)
  - WorkstationPresenceState (runtime_presence_state_v1.py)
  - ProofArtifactType (runtime_execution_result_v1.py)

UMH substrate subsystem. Phase 96.8AH.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any

from execution.environments.chrome_visible_launch import (
    ChromeVisibleLaunchProof,
    ChromeVisibleLaunchStatus,
    visible_launch_proof_allows_next_gate,
)
from .runtime_presence_state_v1 import (
    WorkstationPresenceState,
    is_execution_capable,
)


class ExecutionMode(str, Enum):
    API = "api"
    HEADLESS = "headless"
    COMPUTER_USE_FOREGROUND = "computer_use_foreground"
    COMPUTER_USE_BACKGROUND = "computer_use_background"


FOREGROUND_CU_REQUIRED_MODE = ExecutionMode.COMPUTER_USE_FOREGROUND

FORBIDDEN_EXECUTION_MODES = frozenset(
    {
        ExecutionMode.API,
        ExecutionMode.HEADLESS,
        ExecutionMode.COMPUTER_USE_BACKGROUND,
    }
)

FOREGROUND_CU_FORBIDDEN_ACTIONS = frozenset(
    {
        "api_extraction_fallback",
        "headless_browser_fallback",
        "simulated_extraction",
        "replay_only_validation",
        "mock_browser_execution",
        "background_hidden_execution",
        "cached_extraction_reuse",
        "broad_drive_ingestion",
        "mutate_drive",
        "mutate_docs",
        "auto_promote_canonical_truth",
        "mutate_world_model",
        "recursively_ingest",
        "credential_access",
        "screenshot_as_primary_extraction",
    }
)


@dataclass
class WorkstationReadiness:
    """Pre-execution readiness of the local Windows workstation."""

    windows_session_active: bool = False
    desktop_unlocked: bool = False
    chrome_available: bool = False
    gui_automation_available: bool = False
    monitor_attached: bool = False
    local_runtime_alive: bool = False
    node_parity_valid: bool = False
    foreground_session_owned: bool = False

    @property
    def is_ready(self) -> bool:
        return all(
            [
                self.windows_session_active,
                self.desktop_unlocked,
                self.chrome_available,
                self.gui_automation_available,
                self.local_runtime_alive,
                self.node_parity_valid,
                self.foreground_session_owned,
            ]
        )

    @property
    def denial_reasons(self) -> list[str]:
        reasons: list[str] = []
        if not self.windows_session_active:
            reasons.append("windows_session_not_active")
        if not self.desktop_unlocked:
            reasons.append("desktop_locked")
        if not self.chrome_available:
            reasons.append("chrome_not_available")
        if not self.gui_automation_available:
            reasons.append("gui_automation_not_available")
        if not self.local_runtime_alive:
            reasons.append("local_runtime_not_alive")
        if not self.node_parity_valid:
            reasons.append("node_parity_invalid")
        if not self.foreground_session_owned:
            reasons.append("foreground_session_not_owned")
        return reasons

    def to_dict(self) -> dict[str, Any]:
        return {
            "windows_session_active": self.windows_session_active,
            "desktop_unlocked": self.desktop_unlocked,
            "chrome_available": self.chrome_available,
            "gui_automation_available": self.gui_automation_available,
            "monitor_attached": self.monitor_attached,
            "local_runtime_alive": self.local_runtime_alive,
            "node_parity_valid": self.node_parity_valid,
            "foreground_session_owned": self.foreground_session_owned,
            "is_ready": self.is_ready,
            "denial_reasons": self.denial_reasons,
        }


@dataclass
class ForegroundCUVerification:
    """Verification of foreground Computer Use execution."""

    chrome_running: bool = False
    window_visible: bool = False
    focus_confirmed: bool = False
    desktop_active: bool = False
    user_session_active: bool = False
    navigation_observed: bool = False
    extraction_observed: bool = False
    founder_confirmation_required: bool = True
    founder_confirmation_received: bool = False
    founder_confirmed: bool = False

    @property
    def is_verified(self) -> bool:
        return all(
            [
                self.chrome_running,
                self.window_visible,
                self.focus_confirmed,
                self.desktop_active,
                self.user_session_active,
                self.navigation_observed,
                self.extraction_observed,
                self.founder_confirmed,
            ]
        )

    @property
    def denial_reasons(self) -> list[str]:
        reasons: list[str] = []
        if not self.chrome_running:
            reasons.append("chrome_not_running")
        if not self.window_visible:
            reasons.append("window_not_visible")
        if not self.focus_confirmed:
            reasons.append("focus_not_confirmed")
        if not self.desktop_active:
            reasons.append("desktop_not_active")
        if not self.user_session_active:
            reasons.append("user_session_not_active")
        if not self.navigation_observed:
            reasons.append("navigation_not_observed")
        if not self.extraction_observed:
            reasons.append("extraction_not_observed")
        if not self.founder_confirmed:
            reasons.append("founder_not_confirmed")
        return reasons

    def to_dict(self) -> dict[str, Any]:
        return {
            "chrome_running": self.chrome_running,
            "window_visible": self.window_visible,
            "focus_confirmed": self.focus_confirmed,
            "desktop_active": self.desktop_active,
            "user_session_active": self.user_session_active,
            "navigation_observed": self.navigation_observed,
            "extraction_observed": self.extraction_observed,
            "founder_confirmation_required": self.founder_confirmation_required,
            "founder_confirmation_received": self.founder_confirmation_received,
            "founder_confirmed": self.founder_confirmed,
            "is_verified": self.is_verified,
            "denial_reasons": self.denial_reasons,
        }


@dataclass
class ForegroundCUProof:
    """Complete proof of foreground CU ingestion execution."""

    proof_id: str
    trace_id: str
    execution_mode: str = ExecutionMode.COMPUTER_USE_FOREGROUND.value
    workstation_readiness: WorkstationReadiness | None = None
    cu_verification: ForegroundCUVerification | None = None
    chrome_launch_proof: ChromeVisibleLaunchProof | None = None
    chrome_pid: int = 0
    workstation_session_id: str = ""
    desktop_state: str = "active"
    runtime_mode: str = ExecutionMode.COMPUTER_USE_FOREGROUND.value
    visibility_status: str = "visible"
    focus_state: str = "foreground"
    stages_completed: list[str] = field(default_factory=list)
    ingestion_proof_id: str = ""
    replay_hash: str = ""
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()
        if not self.proof_id:
            self.proof_id = f"FGCU-PROOF-{uuid.uuid4().hex[:8]}"
        if not self.workstation_session_id:
            self.workstation_session_id = f"SESSION-{uuid.uuid4().hex[:8]}"

    @property
    def passed(self) -> bool:
        if self.cu_verification:
            return self.cu_verification.is_verified
        return False

    def compute_replay_hash(self) -> str:
        payload = json.dumps(
            {
                "proof_id": self.proof_id,
                "trace_id": self.trace_id,
                "execution_mode": self.execution_mode,
                "stages_completed": self.stages_completed,
                "chrome_pid": self.chrome_pid,
            },
            sort_keys=True,
        )
        self.replay_hash = hashlib.sha256(payload.encode()).hexdigest()
        return self.replay_hash

    def to_dict(self) -> dict[str, Any]:
        return {
            "proof_id": self.proof_id,
            "trace_id": self.trace_id,
            "execution_mode": self.execution_mode,
            "workstation_readiness": (
                self.workstation_readiness.to_dict() if self.workstation_readiness else None
            ),
            "cu_verification": (self.cu_verification.to_dict() if self.cu_verification else None),
            "chrome_launch_proof": (
                self.chrome_launch_proof.to_dict() if self.chrome_launch_proof else None
            ),
            "chrome_pid": self.chrome_pid,
            "workstation_session_id": self.workstation_session_id,
            "desktop_state": self.desktop_state,
            "runtime_mode": self.runtime_mode,
            "visibility_status": self.visibility_status,
            "focus_state": self.focus_state,
            "stages_completed": self.stages_completed,
            "ingestion_proof_id": self.ingestion_proof_id,
            "replay_hash": self.replay_hash,
            "passed": self.passed,
            "timestamp": self.timestamp,
        }


def validate_execution_mode(
    requested_mode: ExecutionMode,
    config: dict[str, Any],
) -> list[str]:
    """Validate execution mode against config enforcement."""
    errors: list[str] = []

    if config.get("require_foreground_cu", False):
        if requested_mode != ExecutionMode.COMPUTER_USE_FOREGROUND:
            errors.append(f"foreground_cu_required_but_got_{requested_mode.value}")

    if not config.get("allow_api_fallback", True):
        if requested_mode == ExecutionMode.API:
            errors.append("api_fallback_not_allowed")

    if not config.get("allow_headless", True):
        if requested_mode == ExecutionMode.HEADLESS:
            errors.append("headless_not_allowed")

    if requested_mode in FORBIDDEN_EXECUTION_MODES:
        if config.get("require_foreground_cu", False):
            errors.append(f"execution_mode_{requested_mode.value}_forbidden")

    return errors


def validate_workstation_readiness(
    readiness: WorkstationReadiness,
    config: dict[str, Any],
) -> list[str]:
    """Validate workstation readiness for foreground CU execution."""
    errors: list[str] = []

    if config.get("require_local_windows_desktop", False):
        if not readiness.windows_session_active:
            errors.append("windows_session_required_but_inactive")

    if config.get("require_active_session", False):
        if not readiness.foreground_session_owned:
            errors.append("active_session_required_but_not_owned")

    if config.get("require_chrome_process", False):
        if not readiness.chrome_available:
            errors.append("chrome_process_required_but_unavailable")

    if not readiness.is_ready:
        errors.extend(readiness.denial_reasons)

    return errors


def build_foreground_cu_proof(
    trace_id: str,
    workstation_readiness: WorkstationReadiness,
    cu_verification: ForegroundCUVerification,
    chrome_launch_proof: ChromeVisibleLaunchProof | None = None,
    chrome_pid: int = 0,
    stages_completed: list[str] | None = None,
    ingestion_proof_id: str = "",
) -> ForegroundCUProof:
    """Build a complete foreground CU proof from verification results."""
    proof = ForegroundCUProof(
        proof_id="",
        trace_id=trace_id,
        workstation_readiness=workstation_readiness,
        cu_verification=cu_verification,
        chrome_launch_proof=chrome_launch_proof,
        chrome_pid=chrome_pid,
        stages_completed=stages_completed or [],
        ingestion_proof_id=ingestion_proof_id,
    )
    proof.compute_replay_hash()
    return proof


def persist_foreground_cu_proof(
    proof: ForegroundCUProof,
    proof_dir: Path,
) -> Path:
    """Persist foreground CU proof to disk."""
    proof_dir.mkdir(parents=True, exist_ok=True)
    path = proof_dir / f"{proof.proof_id}.json"
    path.write_text(json.dumps(proof.to_dict(), indent=2, default=str))
    return path
