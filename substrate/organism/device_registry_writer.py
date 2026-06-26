"""Device Registry Writer — atomic writes + cache invalidation.

Single canonical writer for infra/device_registry.json. All mutations
to the device registry MUST go through this module.

Atomic write: write to .tmp, rename over original.
File lock: fcntl.flock prevents concurrent corruption.
Cache invalidation: resets all module-level and instance-level caches.

UMH substrate subsystem. Instance-agnostic.
"""

from __future__ import annotations

import fcntl
import json
import logging
import os
import weakref
from typing import Any

logger = logging.getLogger(__name__)

_ROOT = os.environ.get("UMH_ROOT") or "/opt/OS"
_DEFAULT_REGISTRY_PATH = os.path.join(_ROOT, "infra", "device_registry.json")


def _read_registry(path: str) -> list[dict[str, Any]]:
    """Read current registry from disk."""
    try:
        with open(path, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        logger.warning("Could not read device registry %s: %s", path, exc)
        return []


def write_device_registry(
    devices: list[dict[str, Any]],
    registry_path: str | None = None,
) -> None:
    """Atomic write with file lock. Write to .tmp, rename over original."""
    path = registry_path or _DEFAULT_REGISTRY_PATH
    tmp_path = path + ".tmp"
    lock_path = path + ".lock"

    os.makedirs(os.path.dirname(path), exist_ok=True)

    with open(lock_path, "w") as lock_fd:
        fcntl.flock(lock_fd, fcntl.LOCK_EX)
        try:
            with open(tmp_path, "w") as f:
                json.dump(devices, f, indent=2)
                f.write("\n")
            os.replace(tmp_path, path)
            logger.info("Device registry written: %d devices", len(devices))
        finally:
            fcntl.flock(lock_fd, fcntl.LOCK_UN)

    invalidate_all_caches()


def add_device(
    entry: dict[str, Any],
    registry_path: str | None = None,
) -> None:
    """Add a device. Validates no duplicate id or tailscale_name. Atomic."""
    path = registry_path or _DEFAULT_REGISTRY_PATH
    lock_path = path + ".lock"

    os.makedirs(os.path.dirname(path), exist_ok=True)

    with open(lock_path, "w") as lock_fd:
        fcntl.flock(lock_fd, fcntl.LOCK_EX)
        try:
            devices = _read_registry(path)

            new_id = entry.get("id", "")
            new_ts_name = entry.get("tailscale_name", "")
            for d in devices:
                if d.get("id") == new_id:
                    raise ValueError(f"Device with id '{new_id}' already exists")
                if new_ts_name and d.get("tailscale_name") == new_ts_name:
                    raise ValueError(f"Device with tailscale_name '{new_ts_name}' already exists")

            devices.append(entry)

            tmp_path = path + ".tmp"
            with open(tmp_path, "w") as f:
                json.dump(devices, f, indent=2)
                f.write("\n")
            os.replace(tmp_path, path)
            logger.info("Device added: %s (%s)", new_id, new_ts_name)
        finally:
            fcntl.flock(lock_fd, fcntl.LOCK_UN)

    invalidate_all_caches()


def remove_device(
    device_id: str,
    registry_path: str | None = None,
) -> None:
    """Remove a device. Cannot remove always_online devices. Atomic."""
    path = registry_path or _DEFAULT_REGISTRY_PATH
    lock_path = path + ".lock"

    with open(lock_path, "w") as lock_fd:
        fcntl.flock(lock_fd, fcntl.LOCK_EX)
        try:
            devices = _read_registry(path)

            target = next((d for d in devices if d.get("id") == device_id), None)
            if target is None:
                raise ValueError(f"Device '{device_id}' not found")
            if target.get("always_online"):
                raise ValueError(f"Cannot remove always_online device '{device_id}'")

            devices = [d for d in devices if d.get("id") != device_id]

            tmp_path = path + ".tmp"
            with open(tmp_path, "w") as f:
                json.dump(devices, f, indent=2)
                f.write("\n")
            os.replace(tmp_path, path)
            logger.info("Device removed: %s", device_id)
        finally:
            fcntl.flock(lock_fd, fcntl.LOCK_UN)

    invalidate_all_caches()


def update_device(
    device_id: str,
    fields: dict[str, Any],
    registry_path: str | None = None,
) -> dict[str, Any]:
    """Update fields on an existing device. Returns old values for audit.

    Blocked fields: id, tailscale_name (immutable identifiers).
    Role changes auto-set role_status/role_source/last_role_reviewed_at.
    """
    path = registry_path or _DEFAULT_REGISTRY_PATH
    lock_path = path + ".lock"
    blocked = {"id", "tailscale_name"}
    bad_fields = blocked & set(fields.keys())
    if bad_fields:
        raise ValueError(f"Cannot update immutable fields: {bad_fields}")

    old_values: dict[str, Any] = {}

    with open(lock_path, "w") as lock_fd:
        fcntl.flock(lock_fd, fcntl.LOCK_EX)
        try:
            devices = _read_registry(path)
            target = next((d for d in devices if d.get("id") == device_id), None)
            if target is None:
                raise ValueError(f"Device '{device_id}' not found")

            for key, value in fields.items():
                old_values[key] = target.get(key)
                target[key] = value

            if "role" in fields:
                from datetime import datetime, timezone

                if target.get("role_status") == "confirmed":
                    target["role_status"] = "needs_review"
                target["role_source"] = "operator"
                target["last_role_reviewed_at"] = datetime.now(timezone.utc).isoformat()

            tmp_path = path + ".tmp"
            with open(tmp_path, "w") as f:
                json.dump(devices, f, indent=2)
                f.write("\n")
            os.replace(tmp_path, path)
            logger.info("Device updated: %s fields=%s", device_id, list(fields.keys()))
        finally:
            fcntl.flock(lock_fd, fcntl.LOCK_UN)

    invalidate_all_caches()
    return old_values


def invalidate_all_caches() -> None:
    """Reset all module-level and instance-level device caches."""
    # 1. MeshReconciler module-level cache
    try:
        from substrate.organism import mesh_reconciler

        mesh_reconciler._DEVICE_REGISTRY_CACHE = None
        logger.debug("Invalidated mesh_reconciler cache")
    except Exception as exc:
        logger.debug("Could not invalidate mesh_reconciler cache: %s", exc)

    # 2. DeviceAwarenessRuntime tracked instances
    try:
        from substrate.organism import device_awareness

        for ref in list(device_awareness._INSTANCES):
            instance = ref()
            if instance is not None:
                instance.reload()
            else:
                device_awareness._INSTANCES.discard(ref)
        logger.debug(
            "Invalidated %d DeviceAwarenessRuntime instances", len(device_awareness._INSTANCES)
        )
    except Exception as exc:
        logger.debug("Could not invalidate device_awareness instances: %s", exc)
