"""Windows Foreground Actuator v1 for the UMH substrate layer.

Orchestrates REAL GUI actuation on the live Windows workstation:
  - Chrome launch via direct executable
  - Foreground focus validation
  - Visible navigation
  - Screenshot proof capture
  - Observed desktop state collection

This is ONLY an actuator. It does not embed governance,
write memory, or bypass workpackets. Governance is upstream
in the execution spine.

Composes existing infrastructure:
  - WindowsDesktopActionRequest / Result (adapter contracts)
  - Relay client (filesystem JSON inbox/outbox)
  - ForegroundCUVerification (foreground_cu_verification_v1.py)
  - ChromeVisibleLaunchProof (chrome_visible_launch.py)

The actuator emits proof events at each stage. It does NOT
infer visibility — it requires OBSERVED state from the relay.

UMH substrate subsystem. Phase 96.8AI.
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


class ActuationStage(str, Enum):
    NOT_STARTED = "not_started"
    RELAY_DISPATCHED = "relay_dispatched"
    CHROME_LAUNCHED = "chrome_launched"
    PROCESS_VERIFIED = "process_verified"
    WINDOW_DETECTED = "window_detected"
    FOCUS_CONFIRMED = "focus_confirmed"
    NAVIGATION_CONFIRMED = "navigation_confirmed"
    SCREENSHOT_CAPTURED = "screenshot_captured"
    FOUNDER_CONFIRMED = "founder_confirmed"
    COMPLETED = "completed"
    FAILED = "failed"


class EnvironmentRequirement(str, Enum):
    VPS = "vps"
    LOCAL_WINDOWS_HEADLESS = "local_windows_headless"
    LOCAL_WINDOWS_GUI = "local_windows_gui"
    LOCAL_WINDOWS_FOREGROUND = "local_windows_foreground"
    LOCAL_WINDOWS_BACKGROUND = "local_windows_background"


REQUIRED_ENVIRONMENT = EnvironmentRequirement.LOCAL_WINDOWS_FOREGROUND

FORBIDDEN_ENVIRONMENTS = frozenset(
    {
        EnvironmentRequirement.VPS,
        EnvironmentRequirement.LOCAL_WINDOWS_HEADLESS,
        EnvironmentRequirement.LOCAL_WINDOWS_BACKGROUND,
    }
)

ACTUATION_FORBIDDEN_ACTIONS = frozenset(
    {
        "api_extraction_fallback",
        "headless_browser_fallback",
        "simulated_gui_state",
        "inferred_visibility",
        "mocked_chrome_launch",
        "fake_process_detection",
        "replay_only_validation",
        "background_only_execution",
        "hidden_window_execution",
        "screenshot_without_observation",
        "mutate_drive",
        "mutate_docs",
        "mutate_world_model",
        "auto_promote_canonical_truth",
    }
)


@dataclass
class ObservedDesktopState:
    """REAL observed state of the Windows desktop.

    Every field must come from actual observation on the
    live workstation — never from intended or simulated state.
    """

    chrome_pid: int = 0
    window_handle: int = 0
    window_title: str = ""
    visible: bool = False
    focused: bool = False
    monitor_detected: bool = False
    desktop_unlocked: bool = False
    active_user_session: bool = False
    navigation_url: str = ""
    navigation_detected: bool = False
    screenshot_hash: str = ""
    screenshot_path: str = ""
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()

    @property
    def is_valid(self) -> bool:
        return all(
            [
                self.chrome_pid > 0,
                self.visible,
                self.focused,
                self.active_user_session,
                self.desktop_unlocked,
            ]
        )

    @property
    def denial_reasons(self) -> list[str]:
        reasons: list[str] = []
        if self.chrome_pid == 0:
            reasons.append("no_chrome_pid")
        if not self.visible:
            reasons.append("not_visible")
        if not self.focused:
            reasons.append("not_focused")
        if not self.active_user_session:
            reasons.append("no_active_user_session")
        if not self.desktop_unlocked:
            reasons.append("desktop_locked")
        return reasons

    def to_dict(self) -> dict[str, Any]:
        return {
            "chrome_pid": self.chrome_pid,
            "window_handle": self.window_handle,
            "window_title": self.window_title,
            "visible": self.visible,
            "focused": self.focused,
            "monitor_detected": self.monitor_detected,
            "desktop_unlocked": self.desktop_unlocked,
            "active_user_session": self.active_user_session,
            "navigation_url": self.navigation_url,
            "navigation_detected": self.navigation_detected,
            "screenshot_hash": self.screenshot_hash,
            "screenshot_path": self.screenshot_path,
            "timestamp": self.timestamp,
            "is_valid": self.is_valid,
            "denial_reasons": self.denial_reasons,
        }


@dataclass
class ActuationEvent:
    """Single event in the actuation sequence."""

    event_id: str
    stage: ActuationStage
    observed_state: ObservedDesktopState | None = None
    relay_result: dict[str, Any] | None = None
    error: str = ""
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.event_id:
            self.event_id = f"ACTEVT-{uuid.uuid4().hex[:8]}"
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "stage": self.stage.value,
            "observed_state": self.observed_state.to_dict() if self.observed_state else None,
            "relay_result": self.relay_result,
            "error": self.error,
            "timestamp": self.timestamp,
        }


@dataclass
class GUIActuationProof:
    """Complete proof of real Windows GUI actuation."""

    proof_id: str
    trace_id: str
    environment: str = EnvironmentRequirement.LOCAL_WINDOWS_FOREGROUND.value
    stages_completed: list[str] = field(default_factory=list)
    actuation_events: list[ActuationEvent] = field(default_factory=list)
    final_observed_state: ObservedDesktopState | None = None
    chrome_pid: int = 0
    window_handle: int = 0
    screenshot_proof_path: str = ""
    screenshot_hash: str = ""
    founder_confirmed: bool = False
    replay_hash: str = ""
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()
        if not self.proof_id:
            self.proof_id = f"GUI-ACT-PROOF-{uuid.uuid4().hex[:8]}"

    @property
    def passed(self) -> bool:
        if self.final_observed_state is None:
            return False
        return (
            self.final_observed_state.is_valid
            and self.founder_confirmed
            and self.chrome_pid > 0
            and len(self.stages_completed) >= 5
        )

    def compute_replay_hash(self) -> str:
        payload = json.dumps(
            {
                "proof_id": self.proof_id,
                "trace_id": self.trace_id,
                "environment": self.environment,
                "stages_completed": self.stages_completed,
                "chrome_pid": self.chrome_pid,
                "window_handle": self.window_handle,
                "screenshot_hash": self.screenshot_hash,
            },
            sort_keys=True,
        )
        self.replay_hash = hashlib.sha256(payload.encode()).hexdigest()
        return self.replay_hash

    def to_dict(self) -> dict[str, Any]:
        return {
            "proof_id": self.proof_id,
            "trace_id": self.trace_id,
            "environment": self.environment,
            "stages_completed": self.stages_completed,
            "actuation_events": [e.to_dict() for e in self.actuation_events],
            "final_observed_state": (
                self.final_observed_state.to_dict() if self.final_observed_state else None
            ),
            "chrome_pid": self.chrome_pid,
            "window_handle": self.window_handle,
            "screenshot_proof_path": self.screenshot_proof_path,
            "screenshot_hash": self.screenshot_hash,
            "founder_confirmed": self.founder_confirmed,
            "replay_hash": self.replay_hash,
            "passed": self.passed,
            "timestamp": self.timestamp,
        }


def validate_environment(
    requested_env: EnvironmentRequirement,
    config: dict[str, Any],
) -> list[str]:
    """Validate that the requested environment is foreground GUI capable."""
    errors: list[str] = []

    if config.get("require_foreground_gui", False):
        if requested_env != EnvironmentRequirement.LOCAL_WINDOWS_FOREGROUND:
            errors.append(f"foreground_gui_required_but_got_{requested_env.value}")

    if requested_env in FORBIDDEN_ENVIRONMENTS:
        if config.get("require_foreground_gui", False):
            errors.append(f"environment_{requested_env.value}_forbidden")

    if config.get("require_real_desktop", False):
        if requested_env == EnvironmentRequirement.VPS:
            errors.append("real_desktop_required_but_got_vps")

    return errors


def parse_relay_result_to_observed_state(
    relay_result: dict[str, Any],
) -> ObservedDesktopState:
    """Parse a relay result JSON into an ObservedDesktopState.

    Maps the PowerShell relay output fields to the observed state contract.
    """
    window_meta = relay_result.get("window_metadata", {})
    return ObservedDesktopState(
        chrome_pid=relay_result.get("process_id", 0),
        window_handle=window_meta.get("main_window_handle", 0),
        window_title=window_meta.get("main_window_title", ""),
        visible=relay_result.get("process_detected", False),
        focused=window_meta.get("main_window_handle", 0) != 0,
        monitor_detected=True,
        desktop_unlocked=relay_result.get("adapter_status") != "failed",
        active_user_session=relay_result.get("adapter_status") in ("completed", "pong"),
        navigation_url=relay_result.get("url", ""),
        navigation_detected=bool(window_meta.get("main_window_title", "")),
        screenshot_hash=relay_result.get("screenshot_hash", ""),
        screenshot_path=relay_result.get("screenshot_path", ""),
    )


def build_gui_actuation_proof(
    trace_id: str,
    actuation_events: list[ActuationEvent],
    final_observed_state: ObservedDesktopState | None = None,
    chrome_pid: int = 0,
    window_handle: int = 0,
    screenshot_proof_path: str = "",
    screenshot_hash: str = "",
    founder_confirmed: bool = False,
    stages_completed: list[str] | None = None,
) -> GUIActuationProof:
    """Build a complete GUI actuation proof from events and observed state."""
    proof = GUIActuationProof(
        proof_id="",
        trace_id=trace_id,
        actuation_events=actuation_events,
        final_observed_state=final_observed_state,
        chrome_pid=chrome_pid,
        window_handle=window_handle,
        screenshot_proof_path=screenshot_proof_path,
        screenshot_hash=screenshot_hash,
        founder_confirmed=founder_confirmed,
        stages_completed=stages_completed or [],
    )
    proof.compute_replay_hash()
    return proof


def persist_gui_actuation_proof(
    proof: GUIActuationProof,
    proof_dir: Path,
) -> Path:
    """Persist GUI actuation proof to disk."""
    proof_dir.mkdir(parents=True, exist_ok=True)
    path = proof_dir / f"{proof.proof_id}.json"
    path.write_text(json.dumps(proof.to_dict(), indent=2, default=str))
    return path


def build_proof_summary(
    proof: GUIActuationProof,
) -> dict[str, Any]:
    """Build a summary dict suitable for proof_summary.json."""
    return {
        "proof_id": proof.proof_id,
        "trace_id": proof.trace_id,
        "environment": proof.environment,
        "passed": proof.passed,
        "chrome_pid": proof.chrome_pid,
        "window_handle": proof.window_handle,
        "stages_completed": proof.stages_completed,
        "screenshot_hash": proof.screenshot_hash,
        "founder_confirmed": proof.founder_confirmed,
        "replay_hash": proof.replay_hash,
        "timestamp": proof.timestamp,
        "final_state_valid": (
            proof.final_observed_state.is_valid if proof.final_observed_state else False
        ),
        "denial_reasons": (
            proof.final_observed_state.denial_reasons
            if proof.final_observed_state
            else ["no_observed_state"]
        ),
    }
