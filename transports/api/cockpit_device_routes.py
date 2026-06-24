"""Cockpit device management routes — scan, diagnose, register, provision.

Provides REST endpoints for the full device onboarding lifecycle.
Satellite module mounted in cockpit.py via Pattern B.

UMH transport layer. Instance-agnostic.
"""

from __future__ import annotations

import json
import logging
import os
import re
from typing import Any

from fastapi import APIRouter, Depends, Request

from substrate.execution.cpu_gate import gated_subprocess_run

_SAFE_ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")
_VALID_ROLES = {"controller", "executor", "orchestrator"}
_VALID_DEVICE_TYPES = {"server", "pc", "laptop", "tablet", "mobile", "unknown"}
_VALID_OS = {"linux", "windows", "macos", "ios", "ipados", "android", "unknown"}

logger = logging.getLogger(__name__)

_ROOT = os.environ.get("UMH_ROOT") or "/opt/OS"
_REGISTRY_PATH = os.path.join(_ROOT, "infra", "device_registry.json")

device_router: APIRouter = APIRouter()
_configured = False


def configure(require_operator_dep: Any) -> None:
    """Configure device routes with auth dependency."""
    global _configured
    auth = [Depends(require_operator_dep)]

    device_router.add_api_route(
        "/devices/list", _devices_list, methods=["GET"], dependencies=auth,
    )
    device_router.add_api_route(
        "/devices/scan", _devices_scan, methods=["GET"], dependencies=auth,
    )
    device_router.add_api_route(
        "/devices/diagnose", _devices_diagnose, methods=["POST"], dependencies=auth,
    )
    device_router.add_api_route(
        "/devices/register", _devices_register, methods=["POST"], dependencies=auth,
    )
    device_router.add_api_route(
        "/devices/remove", _devices_remove, methods=["POST"], dependencies=auth,
    )
    device_router.add_api_route(
        "/devices/provision", _devices_provision, methods=["POST"], dependencies=auth,
    )
    device_router.add_api_route(
        "/devices/invite", _devices_invite, methods=["POST"], dependencies=auth,
    )
    _configured = True


def _load_registry() -> list[dict[str, Any]]:
    try:
        with open(_REGISTRY_PATH) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def _get_tailscale_peers() -> list[dict[str, Any]]:
    """Get all Tailscale peers via CLI."""
    result = gated_subprocess_run(
        ["tailscale", "status", "--json"],
        caller="device_routes.scan",
        capture_output=True,
        text=True,
        timeout=15,
    )
    if result is None or result.returncode != 0:
        return []
    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError:
        return []

    peers: list[dict[str, Any]] = []
    registry = _load_registry()
    registered_names = {
        d.get("tailscale_name", "").lower() for d in registry
    }

    peer_map = data.get("Peer", {})
    for _key, peer in peer_map.items():
        hostname = peer.get("HostName", "")
        dns_name = peer.get("DNSName", "").split(".")[0]
        os_name = peer.get("OS", "").lower()
        ips = peer.get("TailscaleIPs", [])
        online = peer.get("Online", False)

        peers.append({
            "hostname": hostname,
            "dns_name": dns_name,
            "os": os_name,
            "tailscale_ips": ips,
            "online": online,
            "registered": dns_name.lower() in registered_names
            or hostname.lower() in registered_names,
        })

    self_node = data.get("Self", {})
    if self_node:
        hostname = self_node.get("HostName", "")
        dns_name = self_node.get("DNSName", "").split(".")[0]
        peers.append({
            "hostname": hostname,
            "dns_name": dns_name,
            "os": self_node.get("OS", "").lower(),
            "tailscale_ips": self_node.get("TailscaleIPs", []),
            "online": True,
            "registered": dns_name.lower() in registered_names
            or hostname.lower() in registered_names,
        })

    return peers


# ── Route Handlers ────────────────────────────────────────────────


async def _devices_list(request: Request) -> list[dict[str, Any]]:
    """GET /devices/list — all registered devices."""
    return _load_registry()


async def _devices_scan(request: Request) -> dict[str, Any]:
    """GET /devices/scan — Tailscale peers with registered flag."""
    peers = _get_tailscale_peers()
    return {
        "peers": peers,
        "total": len(peers),
        "unregistered": sum(1 for p in peers if not p["registered"]),
    }


async def _devices_diagnose(request: Request) -> dict[str, Any]:
    """POST /devices/diagnose — SSH probe + hardware diagnosis."""
    body = await request.json()
    hostname = body.get("hostname", "")
    tailscale_ip = body.get("tailscale_ip", "")
    os_hint = body.get("os", "")
    dns_name = body.get("dns_name", "")

    if not tailscale_ip:
        return {"success": False, "error": "tailscale_ip required"}

    from substrate.organism.device_provisioner import diagnose_device

    diag = diagnose_device(
        hostname=hostname,
        tailscale_ip=tailscale_ip,
        os_hint=os_hint,
        dns_name=dns_name,
    )
    return {"success": True, "diagnosis": diag.to_dict()}


def _validate_registry_entry(entry: dict[str, Any]) -> str | None:
    """Validate registry entry fields. Returns error message or None."""
    for field in ("id", "tailscale_name", "mesh_node_id"):
        val = entry.get(field, "")
        if val and not _SAFE_ID_RE.match(str(val)):
            return f"Invalid {field}: must be alphanumeric/dash/underscore, 1-64 chars"
    role = entry.get("role", "controller")
    if role not in _VALID_ROLES:
        return f"Invalid role: {role!r} (must be one of {_VALID_ROLES})"
    device_type = entry.get("device_type", "unknown")
    if device_type not in _VALID_DEVICE_TYPES:
        return f"Invalid device_type: {device_type!r}"
    os_val = entry.get("os", "unknown").lower()
    if os_val not in _VALID_OS:
        return f"Invalid os: {os_val!r}"
    if entry.get("always_online"):
        return "always_online cannot be set via API"
    return None


async def _devices_register(request: Request) -> dict[str, Any]:
    """POST /devices/register — add to registry + invalidate caches."""
    body = await request.json()
    entry = body.get("entry")
    if not entry or not entry.get("id"):
        return {"success": False, "error": "entry with id required"}

    err = _validate_registry_entry(entry)
    if err:
        return {"success": False, "error": err}

    from substrate.organism.device_registry_writer import add_device

    try:
        add_device(entry)
        return {"success": True, "device_id": entry["id"]}
    except ValueError as exc:
        return {"success": False, "error": str(exc)}


async def _devices_remove(request: Request) -> dict[str, Any]:
    """POST /devices/remove — remove from registry + caches + mesh token."""
    body = await request.json()
    device_id = body.get("device_id", "")
    if not device_id:
        return {"success": False, "error": "device_id required"}

    # Read mesh_node_id BEFORE deleting from registry
    registry = _load_registry()
    target = next((d for d in registry if d.get("id") == device_id), None)
    mesh_node_id = target.get("mesh_node_id", device_id) if target else device_id

    from substrate.organism.device_registry_writer import remove_device

    try:
        remove_device(device_id)
    except ValueError as exc:
        return {"success": False, "error": str(exc)}

    try:
        from substrate.organism.device_provisioner import (
            remove_mesh_token,
            signal_mesh_reload,
        )
        if remove_mesh_token(mesh_node_id):
            signal_mesh_reload()
    except Exception as exc:
        logger.debug("Mesh token cleanup failed for %s: %s", device_id, exc)

    return {"success": True, "device_id": device_id}


async def _devices_provision(request: Request) -> dict[str, Any]:
    """POST /devices/provision — run provisioner for a registered device."""
    body = await request.json()
    device_id = body.get("device_id", "")
    role = body.get("role", "")

    if not device_id:
        return {"success": False, "error": "device_id required"}

    registry = _load_registry()
    device = next((d for d in registry if d.get("id") == device_id), None)

    if not device:
        return {"success": False, "error": f"Device '{device_id}' not found in registry"}

    effective_role = role or device.get("role", "controller")

    if effective_role == "controller":
        return {"success": True, "result": {"success": True, "device_id": device_id,
                "role": "controller", "steps": [], "mesh_connected": False}}

    tailscale_ip = device.get("tailscale_ip", "")
    if not tailscale_ip:
        return {"success": False, "error": "No tailscale_ip for device"}

    from substrate.organism.device_provisioner import provision_compute_node

    result = provision_compute_node(
        device_id=device_id,
        entry=device,
        tailscale_ip=tailscale_ip,
        os_name=device.get("os", ""),
    )
    return {"success": result.success, "result": result.to_dict()}


async def _devices_invite(request: Request) -> dict[str, Any]:
    """POST /devices/invite — generate Tailscale auth key."""
    try:
        from adapters.tailscale.tailscale_api import generate_auth_key
        body = await request.json()
        key_data = generate_auth_key(
            reusable=body.get("reusable", False),
            ephemeral=body.get("ephemeral", False),
            preauthorized=body.get("preauthorized", True),
            expiry_seconds=body.get("expiry_seconds", 3600),
        )
        return {"success": True, "auth_key": key_data}
    except Exception as exc:
        logger.error("Device invite failed: %s", exc)
        return {"success": False, "error": str(exc)}
