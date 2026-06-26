"""Settings Persistence — flock + atomic write for settings domains.

Handles file I/O only. Runtime application happens in the transport layer
where imports from adapters/ are permitted.

Domains:
  model_routing   → data/umh/settings/model_routing.json
  governance      → data/umh/settings/governance_policy.json

Device roles persist to infra/device_registry.json via device_registry_writer.

UMH substrate subsystem. Instance-agnostic.
"""

from __future__ import annotations

import fcntl
import json
import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

_ROOT = os.environ.get("UMH_ROOT") or "/opt/OS"
SETTINGS_DIR = os.path.join(_ROOT, "data", "umh", "settings")

DEVICE_ROLE_CONSTRAINTS: dict[str, dict[str, Any]] = {
    "mobile": {"allowed": ["controller"], "reason": "Mobile device — cannot run daemon"},
    "tablet": {"allowed": ["controller"], "reason": "Tablet device — cannot run daemon"},
    "pc": {"allowed": ["controller", "executor", "orchestrator"]},
    "laptop": {"allowed": ["controller", "executor"], "note": "executor requires daemon install"},
    "server": {"allowed": ["controller", "executor", "orchestrator"]},
    "vps": {"allowed": ["orchestrator", "executor", "controller"]},
    "unknown": {"allowed": ["controller"], "reason": "Role restricted until diagnosed"},
}

PROVISIONING_STRATEGY: dict[str, str] = {
    "mobile": "none",
    "tablet": "none",
    "pc": "daemon_install",
    "laptop": "ssh",
    "server": "daemon_install",
    "vps": "manual",
    "unknown": "none",
}


def load_settings(domain: str) -> dict[str, Any]:
    """Load persisted settings for a domain. Returns {} if no file."""
    path = os.path.join(SETTINGS_DIR, f"{domain}.json")
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r") as f:
            data = json.load(f)
        if isinstance(data, dict):
            return data
        logger.warning("Settings file %s is not a dict, ignoring", path)
        return {}
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("Could not read settings %s: %s", path, exc)
        return {}


def save_settings(domain: str, data: dict[str, Any]) -> None:
    """Atomic write with flock. Creates dir if needed."""
    os.makedirs(SETTINGS_DIR, exist_ok=True)
    path = os.path.join(SETTINGS_DIR, f"{domain}.json")
    tmp_path = path + ".tmp"
    lock_path = path + ".lock"

    with open(lock_path, "w") as lock_fd:
        fcntl.flock(lock_fd, fcntl.LOCK_EX)
        try:
            with open(tmp_path, "w") as f:
                json.dump(data, f, indent=2)
                f.write("\n")
            os.replace(tmp_path, path)
            logger.info("Settings saved: %s (%d keys)", domain, len(data))
        finally:
            fcntl.flock(lock_fd, fcntl.LOCK_UN)


def backfill_device_role_fields(registry_path: str | None = None) -> bool:
    """Backfill role pipeline fields on existing devices. Idempotent.

    Returns True if any changes were written.
    """
    path = registry_path or os.path.join(_ROOT, "infra", "device_registry.json")
    try:
        with open(path, "r") as f:
            devices = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return False

    changed = False
    now_iso = _now_iso()

    for dev in devices:
        device_type = dev.get("device_type", "unknown")
        constraints = DEVICE_ROLE_CONSTRAINTS.get(device_type, DEVICE_ROLE_CONSTRAINTS["unknown"])

        defaults = {
            "role_status": "confirmed",
            "role_source": "operator",
            "allowed_roles": constraints["allowed"],
            "candidate_roles": constraints["allowed"],
            "provisioning_mode": PROVISIONING_STRATEGY.get(device_type, "none"),
            "install_capable": device_type in ("pc", "server", "vps", "laptop"),
            "diagnosis_status": "complete",
            "last_role_reviewed_at": now_iso,
            "role_confidence": 1.0,
        }

        for key, value in defaults.items():
            if key not in dev:
                dev[key] = value
                changed = True

    if changed:
        from substrate.organism.device_registry_writer import write_device_registry

        write_device_registry(devices, registry_path=path)
        logger.info("Backfilled role pipeline fields on %d devices", len(devices))

    return changed


def _now_iso() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).isoformat()
