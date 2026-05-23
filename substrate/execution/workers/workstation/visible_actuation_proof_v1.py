"""Visible Actuation Proof v1.

Classifies real relay execution results into maturity-aware proof
artifacts. Enforces that L1_VISIBLE_ACTUATION requires real Chrome
PID, real HWND, foreground focus, screenshot, and founder confirmation.

No dry-run paths. No simulated evidence.

UMH substrate subsystem.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from substrate.execution.actuation.actuator_maturity_v1 import (

    MATURITY_LABELS,
    ActuatorMaturityLevel,
    maturity_ceiling,
    validate_maturity_claim,
)

import os
_ROOT = os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS"



@dataclass
class VisibleActuationEvidence:
    """Evidence collected from a real relay execution."""

    chrome_pid: int = 0
    window_handle: int = 0
    window_title: str = ""
    foreground_focused: bool = False
    screenshot_path: str = ""
    screenshot_hash: str = ""
    desktop_unlocked: bool = False
    desktop_session_active: bool = False
    monitor_detected: bool = False
    founder_confirmed: bool = False
    relay_node_id: str = ""
    relay_machine: str = ""
    is_dry_run: bool = False
    trace_id: str = ""
    request_id: str = ""

    @property
    def has_chrome_pid(self) -> bool:
        return self.chrome_pid > 0

    @property
    def has_window_handle(self) -> bool:
        return self.window_handle > 0

    @property
    def has_screenshot(self) -> bool:
        return bool(self.screenshot_path) and bool(self.screenshot_hash)

    @property
    def has_foreground_focus(self) -> bool:
        return self.foreground_focused and self.has_window_handle

    @property
    def missing_evidence(self) -> list[str]:
        missing = []
        if not self.has_chrome_pid:
            missing.append("chrome_pid")
        if not self.has_window_handle:
            missing.append("window_handle")
        if not self.has_foreground_focus:
            missing.append("foreground_focus")
        if not self.has_screenshot:
            missing.append("screenshot")
        if not self.founder_confirmed:
            missing.append("founder_confirmation")
        return missing

    def to_dict(self) -> dict[str, Any]:
        return {
            "chrome_pid": self.chrome_pid,
            "window_handle": self.window_handle,
            "window_title": self.window_title,
            "foreground_focused": self.foreground_focused,
            "screenshot_path": self.screenshot_path,
            "screenshot_hash": self.screenshot_hash,
            "desktop_unlocked": self.desktop_unlocked,
            "desktop_session_active": self.desktop_session_active,
            "monitor_detected": self.monitor_detected,
            "founder_confirmed": self.founder_confirmed,
            "relay_node_id": self.relay_node_id,
            "relay_machine": self.relay_machine,
            "is_dry_run": self.is_dry_run,
            "has_chrome_pid": self.has_chrome_pid,
            "has_window_handle": self.has_window_handle,
            "has_screenshot": self.has_screenshot,
            "has_foreground_focus": self.has_foreground_focus,
            "missing_evidence": self.missing_evidence,
        }


@dataclass
class VisibleActuationProof:
    """Proof artifact for visible Chrome actuation."""

    proof_id: str = ""
    proof_type: str = "visible_actuation"
    evidence: VisibleActuationEvidence = field(default_factory=VisibleActuationEvidence)
    maturity_level: ActuatorMaturityLevel = ActuatorMaturityLevel.L0_SIMULATED
    maturity_label: str = ""
    maturity_ceiling: ActuatorMaturityLevel = ActuatorMaturityLevel.L0_SIMULATED
    escalation_blocked: bool = True
    escalation_reason: str = ""
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()
        if not self.maturity_label:
            self.maturity_label = MATURITY_LABELS[self.maturity_level]
        if not self.proof_id:
            self.proof_id = f"VAP-{hashlib.sha256(self.timestamp.encode()).hexdigest()[:8]}"

    def to_dict(self) -> dict[str, Any]:
        return {
            "proof_id": self.proof_id,
            "proof_type": self.proof_type,
            "evidence": self.evidence.to_dict(),
            "maturity_level": self.maturity_level.value,
            "maturity_level_name": self.maturity_level.name,
            "maturity_label": self.maturity_label,
            "maturity_ceiling": self.maturity_ceiling.value,
            "maturity_ceiling_name": self.maturity_ceiling.name,
            "escalation_blocked": self.escalation_blocked,
            "escalation_reason": self.escalation_reason,
            "timestamp": self.timestamp,
        }


def classify_visible_actuation(
    evidence: VisibleActuationEvidence,
) -> VisibleActuationProof:
    """Classify evidence into a maturity-aware visible actuation proof.

    L1_VISIBLE_ACTUATION requires ALL of:
    - real Chrome PID (not 0)
    - real HWND (not 0)
    - foreground focus
    - screenshot captured
    - founder confirmation
    - NOT a dry run
    """
    if evidence.is_dry_run:
        return VisibleActuationProof(
            evidence=evidence,
            maturity_level=ActuatorMaturityLevel.L0_SIMULATED,
            maturity_ceiling=ActuatorMaturityLevel.L0_SIMULATED,
            escalation_blocked=True,
            escalation_reason="dry_run_cannot_escalate",
        )

    ceiling = maturity_ceiling(
        has_window_handle=evidence.has_window_handle,
        has_screenshot=evidence.has_screenshot,
        has_founder_confirmation=evidence.founder_confirmed,
    )

    computed_evidence = {
        "chrome_pid": evidence.chrome_pid,
        "window_handle": evidence.window_handle,
        "focused": evidence.foreground_focused,
        "navigation_detected": False,
        "screenshot_path": evidence.screenshot_path,
        "founder_confirmed": evidence.founder_confirmed,
        "replay_hash": "",
    }

    from execution.actuation.actuator_maturity_v1 import compute_maturity_level

    raw_level = compute_maturity_level(computed_evidence)
    level = min(raw_level, ceiling)

    missing = evidence.missing_evidence
    if missing:
        blocked = True
        reason = f"missing_evidence: {', '.join(missing)}"
    else:
        blocked = level < ActuatorMaturityLevel.L1_PROCESS_STARTED
        reason = "" if not blocked else "insufficient_maturity"

    return VisibleActuationProof(
        evidence=evidence,
        maturity_level=level,
        maturity_ceiling=ceiling,
        escalation_blocked=blocked,
        escalation_reason=reason,
    )


def extract_evidence_from_relay_result(
    relay_result: dict[str, Any],
    founder_confirmed: bool = False,
) -> VisibleActuationEvidence:
    """Extract visible actuation evidence from a relay outbox result."""
    obs = relay_result.get("observed_desktop_state", {})
    return VisibleActuationEvidence(
        chrome_pid=obs.get("chrome_pid", relay_result.get("process_id", 0)),
        window_handle=obs.get("window_handle", 0),
        window_title=obs.get("window_title", ""),
        foreground_focused=obs.get("focused", obs.get("is_foreground", False)),
        screenshot_path=obs.get("screenshot_path", relay_result.get("screenshot_path", "")),
        screenshot_hash=obs.get("screenshot_hash", relay_result.get("screenshot_hash", "")),
        desktop_unlocked=obs.get("desktop_unlocked", False),
        desktop_session_active=obs.get("desktop_session_active", False),
        monitor_detected=obs.get("monitor_detected", False),
        founder_confirmed=founder_confirmed,
        relay_node_id=relay_result.get("node_id", ""),
        relay_machine=relay_result.get("machine_name", ""),
        is_dry_run=relay_result.get("dry_run", False),
        trace_id=relay_result.get("trace_id", ""),
        request_id=relay_result.get("request_id", ""),
    )


PROOF_DIR = Path("data/runtime/workstation_relay/actuation_proofs")


def persist_visible_actuation_proof(
    proof: VisibleActuationProof,
    base_dir: Path = Path(_ROOT),
) -> Path:
    """Persist a visible actuation proof artifact."""
    proof_dir = base_dir / PROOF_DIR
    proof_dir.mkdir(parents=True, exist_ok=True)
    path = proof_dir / f"{proof.proof_id}.json"
    path.write_text(json.dumps(proof.to_dict(), indent=2, default=str))
    return path


@dataclass
class FounderConfirmationArtifact:
    """Records the founder's confirmation or denial of visible actuation."""

    confirmation_id: str = ""
    confirmed: bool = False
    trace_id: str = ""
    request_id: str = ""
    channel: str = "discord"
    founder_response: str = ""
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()
        if not self.confirmation_id:
            self.confirmation_id = f"FC-{hashlib.sha256(self.timestamp.encode()).hexdigest()[:8]}"

    def to_dict(self) -> dict[str, Any]:
        return {
            "confirmation_id": self.confirmation_id,
            "confirmed": self.confirmed,
            "trace_id": self.trace_id,
            "request_id": self.request_id,
            "channel": self.channel,
            "founder_response": self.founder_response,
            "timestamp": self.timestamp,
        }


def persist_founder_confirmation(
    artifact: FounderConfirmationArtifact,
    base_dir: Path = Path(_ROOT),
) -> Path:
    """Persist a founder confirmation artifact."""
    proof_dir = base_dir / PROOF_DIR
    proof_dir.mkdir(parents=True, exist_ok=True)
    path = proof_dir / f"{artifact.confirmation_id}.json"
    path.write_text(json.dumps(artifact.to_dict(), indent=2, default=str))
    return path
