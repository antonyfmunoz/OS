"""Windows Foreground Actuator v1 (Maturity-Aware).

Orchestrates real GUI actuation on the live Windows workstation
and classifies the result against the L0-L7 maturity model.

This actuator does NOT execute directly — it dispatches to the
PowerShell relay via filesystem inbox/outbox and classifies the
relay's observed state against maturity requirements.

Key invariant: maturity level can NEVER exceed the evidence.
- No HWND → capped at L1
- No screenshot → capped at L4
- No founder confirmation → capped at L5

UMH substrate subsystem. Phase 96.8AN.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .actuator_backend_registry_v1 import (
    ActuatorBackendRegistry,
    BackendCapability,
    get_backend_registry,
)
from .actuator_maturity_v1 import (
    MATURITY_LABELS,
    ActuatorMaturityLevel,
    compute_maturity_level,
    maturity_ceiling,
    validate_maturity_claim,
)
from .observed_desktop_state_v1 import (
    ObservedDesktopStateV1,
    from_relay_result,
)


SAFE_PROOF_URL = "https://www.google.com"


@dataclass
class ActuatorProofRequest:
    """Request to produce an actuation proof."""

    request_id: str = ""
    trace_id: str = ""
    url: str = SAFE_PROOF_URL
    dry_run: bool = False
    backend_id: str = "windows_interactive_desktop_relay"
    proof_dir: str = ""

    def __post_init__(self) -> None:
        if not self.request_id:
            self.request_id = f"ACT-PROOF-{uuid.uuid4().hex[:8]}"
        if not self.trace_id:
            self.trace_id = f"TRACE-ACT-{uuid.uuid4().hex[:8]}"


@dataclass
class ActuatorProofResult:
    """Result of an actuation proof attempt with maturity classification."""

    request_id: str
    trace_id: str
    backend_used: str
    maturity_level: ActuatorMaturityLevel = ActuatorMaturityLevel.L0_SIMULATED
    observed_state: ObservedDesktopStateV1 | None = None
    chrome_pid: int = 0
    window_handle: int = 0
    window_title: str = ""
    visible: bool = False
    focused: bool = False
    screenshot_path: str = ""
    screenshot_hash: str = ""
    founder_confirmed: bool = False
    founder_confirmation_required: bool = True
    founder_confirmation_status: str = "pending"
    replay_hash: str = ""
    is_dry_run: bool = False
    error: str = ""
    stages_completed: list[str] = field(default_factory=list)
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()

    @property
    def succeeded(self) -> bool:
        return (
            self.maturity_level >= ActuatorMaturityLevel.L1_PROCESS_STARTED
            and not self.is_dry_run
            and not self.error
        )

    @property
    def status(self) -> str:
        if self.error:
            return "FAILED_REAL_ACTUATION"
        if self.is_dry_run:
            return "SIMULATED"
        if self.maturity_level >= ActuatorMaturityLevel.L1_PROCESS_STARTED:
            return "REAL_ACTUATION"
        return "FAILED_REAL_ACTUATION"

    def compute_replay_hash(self) -> str:
        payload = json.dumps(
            {
                "request_id": self.request_id,
                "trace_id": self.trace_id,
                "backend_used": self.backend_used,
                "chrome_pid": self.chrome_pid,
                "window_handle": self.window_handle,
                "screenshot_hash": self.screenshot_hash,
                "maturity_level": self.maturity_level.value,
            },
            sort_keys=True,
        )
        self.replay_hash = hashlib.sha256(payload.encode()).hexdigest()[:16]
        return self.replay_hash

    def to_dict(self) -> dict[str, Any]:
        return {
            "request_id": self.request_id,
            "trace_id": self.trace_id,
            "backend_used": self.backend_used,
            "maturity_level": self.maturity_level.value,
            "maturity_label": MATURITY_LABELS[self.maturity_level],
            "status": self.status,
            "succeeded": self.succeeded,
            "chrome_pid": self.chrome_pid,
            "window_handle": self.window_handle,
            "window_title": self.window_title,
            "visible": self.visible,
            "focused": self.focused,
            "screenshot_path": self.screenshot_path,
            "screenshot_hash": self.screenshot_hash,
            "founder_confirmed": self.founder_confirmed,
            "founder_confirmation_required": self.founder_confirmation_required,
            "founder_confirmation_status": self.founder_confirmation_status,
            "replay_hash": self.replay_hash,
            "is_dry_run": self.is_dry_run,
            "error": self.error,
            "stages_completed": self.stages_completed,
            "timestamp": self.timestamp,
        }


def classify_relay_result(
    relay_result: dict[str, Any],
    backend_id: str = "windows_interactive_desktop_relay",
) -> ActuatorProofResult:
    """Classify a PowerShell relay result into a maturity-aware proof result."""
    obs = from_relay_result(relay_result, backend=backend_id)
    is_dry = relay_result.get("dry_run", False)

    result = ActuatorProofResult(
        request_id=relay_result.get("request_id", ""),
        trace_id=relay_result.get("trace_id", ""),
        backend_used=backend_id,
        observed_state=obs,
        chrome_pid=obs.chrome_pid,
        window_handle=obs.window_handle,
        window_title=obs.window_title,
        visible=obs.visible,
        focused=obs.focused,
        screenshot_path=obs.screenshot_path,
        screenshot_hash=obs.screenshot_hash,
        founder_confirmed=obs.founder_confirmed,
        is_dry_run=is_dry,
        stages_completed=relay_result.get("stages_completed", []),
    )

    result.maturity_level = obs.maturity_level
    result.compute_replay_hash()
    return result


def build_backend_selection_proof(
    registry: ActuatorBackendRegistry | None = None,
) -> dict[str, Any]:
    """Build the backend selection proof artifact."""
    if registry is None:
        registry = get_backend_registry()

    selected = registry.select_for_proof()
    return {
        "selected_backend": selected.backend_id if selected else "none",
        "selection_reason": (
            "Already deployed, zero integration time, full capability coverage (7/7)"
            if selected
            else "no_backend_available"
        ),
        "evaluated_backends": registry.to_dict(),
        "required_capabilities": [
            "chrome_launch",
            "hwnd_observation",
            "screenshot_capture",
            "foreground_detection",
        ],
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def persist_proof_artifacts(
    result: ActuatorProofResult,
    proof_dir: Path,
    backend_selection: dict[str, Any] | None = None,
) -> dict[str, Path]:
    """Persist all proof artifacts to the proof directory."""
    proof_dir.mkdir(parents=True, exist_ok=True)
    paths: dict[str, Path] = {}

    if backend_selection:
        p = proof_dir / "backend_selection.json"
        p.write_text(json.dumps(backend_selection, indent=2, default=str))
        paths["backend_selection"] = p

    if result.observed_state:
        p = proof_dir / "observed_desktop_state.json"
        p.write_text(json.dumps(result.observed_state.to_dict(), indent=2, default=str))
        paths["observed_desktop_state"] = p

    p = proof_dir / "chrome_process_state.json"
    p.write_text(
        json.dumps(
            {
                "chrome_pid": result.chrome_pid,
                "window_handle": result.window_handle,
                "window_title": result.window_title,
                "visible": result.visible,
                "focused": result.focused,
                "is_dry_run": result.is_dry_run,
                "timestamp": result.timestamp,
            },
            indent=2,
        )
    )
    paths["chrome_process_state"] = p

    p = proof_dir / "window_focus_state.json"
    p.write_text(
        json.dumps(
            {
                "window_handle": result.window_handle,
                "window_title": result.window_title,
                "focused": result.focused,
                "visible": result.visible,
                "timestamp": result.timestamp,
            },
            indent=2,
        )
    )
    paths["window_focus_state"] = p

    report = {
        "request_id": result.request_id,
        "trace_id": result.trace_id,
        "backend_used": result.backend_used,
        "maturity_level": result.maturity_level.value,
        "maturity_label": MATURITY_LABELS[result.maturity_level],
        "status": result.status,
        "chrome_pid": result.chrome_pid,
        "window_handle": result.window_handle,
        "screenshot_path": result.screenshot_path,
        "screenshot_hash": result.screenshot_hash,
        "founder_confirmed": result.founder_confirmed,
        "founder_confirmation_required": result.founder_confirmation_required,
        "founder_confirmation_status": result.founder_confirmation_status,
        "is_dry_run": result.is_dry_run,
        "stages_completed": result.stages_completed,
        "replay_hash": result.replay_hash,
        "timestamp": result.timestamp,
    }
    p = proof_dir / "actuator_maturity_report.json"
    p.write_text(json.dumps(report, indent=2, default=str))
    paths["actuator_maturity_report"] = p

    summary = {
        "phase": "96.8AN",
        "proof_type": "actuator_maturity",
        "backend_used": result.backend_used,
        "maturity_level": result.maturity_level.value,
        "maturity_label": MATURITY_LABELS[result.maturity_level],
        "status": result.status,
        "succeeded": result.succeeded,
        "chrome_pid": result.chrome_pid,
        "window_handle": result.window_handle,
        "window_title": result.window_title,
        "visible": result.visible,
        "focused": result.focused,
        "screenshot_path": result.screenshot_path,
        "screenshot_hash": result.screenshot_hash,
        "founder_confirmed": result.founder_confirmed,
        "founder_confirmation_required": result.founder_confirmation_required,
        "founder_confirmation_status": result.founder_confirmation_status,
        "replay_hash": result.replay_hash,
        "is_dry_run": result.is_dry_run,
        "stages_completed": result.stages_completed,
        "timestamp": result.timestamp,
    }
    p = proof_dir / "final_actuator_summary.json"
    p.write_text(json.dumps(summary, indent=2, default=str))
    paths["final_actuator_summary"] = p

    return paths
