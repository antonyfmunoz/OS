"""Workstation Relay Proof v1.

Handles proof artifacts from real workstation relay execution.
Reads relay output, classifies maturity, and persists proof.

UMH substrate subsystem. Phase 96.8AO.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from core.actuation.actuator_maturity_v1 import (
    MATURITY_LABELS,
    ActuatorMaturityLevel,
    compute_maturity_level,
    maturity_ceiling,
)
from core.actuation.observed_desktop_state_v1 import (
    ObservedDesktopStateV1,
    from_relay_result,
)


RELAY_PROOF_DIR = Path("data/runtime/workstation_relay/proofs")


def classify_relay_proof(
    relay_result: dict[str, Any],
) -> dict[str, Any]:
    """Classify a relay result into a maturity-aware proof summary."""
    obs = from_relay_result(relay_result)
    level = obs.maturity_level

    return {
        "proof_type": "workstation_relay_execution",
        "request_id": relay_result.get("request_id", ""),
        "trace_id": relay_result.get("trace_id", ""),
        "action_type": relay_result.get("action_type", ""),
        "backend_used": "windows_interactive_desktop_relay",
        "maturity_level": level.value,
        "maturity_label": MATURITY_LABELS[level],
        "chrome_pid": obs.chrome_pid,
        "window_handle": obs.window_handle,
        "window_title": obs.window_title,
        "visible": obs.visible,
        "focused": obs.focused,
        "screenshot_path": obs.screenshot_path,
        "screenshot_hash": obs.screenshot_hash,
        "founder_confirmed": obs.founder_confirmed,
        "is_dry_run": obs.is_dry_run,
        "stages_completed": relay_result.get("stages_completed", []),
        "adapter_status": relay_result.get("adapter_status", ""),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def persist_relay_proof(
    relay_result: dict[str, Any],
    base_dir: Path = Path("/opt/OS"),
) -> Path:
    """Persist a relay proof artifact."""
    proof_dir = base_dir / RELAY_PROOF_DIR
    proof_dir.mkdir(parents=True, exist_ok=True)

    summary = classify_relay_proof(relay_result)
    trace_id = (
        summary["trace_id"] or f"UNKNOWN-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
    )
    path = proof_dir / f"{trace_id}.json"
    path.write_text(json.dumps(summary, indent=2, default=str))
    return path


def compute_proof_hash(relay_result: dict[str, Any]) -> str:
    """Compute a deterministic hash of a relay proof."""
    obs = relay_result.get("observed_desktop_state", {})
    payload = json.dumps(
        {
            "request_id": relay_result.get("request_id", ""),
            "trace_id": relay_result.get("trace_id", ""),
            "chrome_pid": obs.get("chrome_pid", 0),
            "window_handle": obs.get("window_handle", 0),
            "screenshot_hash": obs.get("screenshot_hash", ""),
        },
        sort_keys=True,
    )
    return hashlib.sha256(payload.encode()).hexdigest()[:16]
