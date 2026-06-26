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
        "/devices/list",
        _devices_list,
        methods=["GET"],
        dependencies=auth,
    )
    device_router.add_api_route(
        "/devices/scan",
        _devices_scan,
        methods=["GET"],
        dependencies=auth,
    )
    device_router.add_api_route(
        "/devices/diagnose",
        _devices_diagnose,
        methods=["POST"],
        dependencies=auth,
    )
    device_router.add_api_route(
        "/devices/register",
        _devices_register,
        methods=["POST"],
        dependencies=auth,
    )
    device_router.add_api_route(
        "/devices/remove",
        _devices_remove,
        methods=["POST"],
        dependencies=auth,
    )
    device_router.add_api_route(
        "/devices/provision",
        _devices_provision,
        methods=["POST"],
        dependencies=auth,
    )
    device_router.add_api_route(
        "/devices/invite",
        _devices_invite,
        methods=["POST"],
        dependencies=auth,
    )
    device_router.add_api_route(
        "/devices/update",
        _devices_update,
        methods=["POST"],
        dependencies=auth,
    )
    _configured = True


def _load_registry() -> list[dict[str, Any]]:
    try:
        with open(_REGISTRY_PATH) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []


_TAILSCALE_SOCK = "/var/run/tailscale/tailscaled.sock"


def _tailscale_local_api() -> dict[str, Any] | None:
    """Query tailscale status via the local API Unix socket.

    Works inside Docker when the host socket is bind-mounted.
    Falls back to CLI if socket unavailable.
    """
    import http.client
    import socket as _socket

    if not os.path.exists(_TAILSCALE_SOCK):
        return None
    try:
        conn = http.client.HTTPConnection("local-tailscaled.sock")
        conn.sock = _socket.socket(_socket.AF_UNIX, _socket.SOCK_STREAM)
        conn.sock.settimeout(10)
        conn.sock.connect(_TAILSCALE_SOCK)
        conn.request("GET", "/localapi/v0/status")
        resp = conn.getresponse()
        if resp.status != 200:
            return None
        return json.loads(resp.read().decode())
    except Exception as exc:
        logger.debug("tailscale local API failed: %s", exc)
        return None


def _tailscale_cli() -> dict[str, Any] | None:
    """Query tailscale status via CLI. Fallback when socket unavailable."""
    try:
        result = gated_subprocess_run(
            ["tailscale", "status", "--json"],
            caller="device_routes.scan",
            capture_output=True,
            text=True,
            timeout=15,
        )
    except FileNotFoundError:
        logger.debug("tailscale CLI not found — scan unavailable in this environment")
        return None
    if result is None or result.returncode != 0:
        return None
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return None


_INFRA_PREFIXES = ("umh-cockpit",)


def _get_tailscale_status() -> dict[str, Any] | None:
    """Get raw Tailscale status. Shared by scan and list enrichment."""
    return _tailscale_local_api() or _tailscale_cli()


def _is_infrastructure(dns_name: str) -> bool:
    return any(dns_name.startswith(p) for p in _INFRA_PREFIXES)


def _get_tailscale_peers() -> list[dict[str, Any]]:
    """Get unregistered, non-infrastructure Tailscale peers only."""
    data = _get_tailscale_status()
    if data is None:
        return []

    peers: list[dict[str, Any]] = []
    registry = _load_registry()
    registered_names = {d.get("tailscale_name", "").lower() for d in registry}

    all_nodes = list(data.get("Peer", {}).values())
    self_node = data.get("Self")
    if self_node:
        self_node["_is_self"] = True
        all_nodes.append(self_node)

    for peer in all_nodes:
        hostname = peer.get("HostName", "")
        dns_name = peer.get("DNSName", "").split(".")[0]
        os_name = peer.get("OS", "")

        if _is_infrastructure(dns_name):
            continue

        is_registered = dns_name.lower() in registered_names or hostname.lower() in registered_names
        if is_registered:
            continue

        ips = peer.get("TailscaleIPs", [])
        online = True if peer.get("_is_self") else peer.get("Online", False)
        display_hostname = dns_name if dns_name else hostname

        peers.append(
            {
                "hostname": hostname,
                "dns_name": dns_name,
                "display_hostname": display_hostname,
                "os": os_name,
                "tailscale_ips": ips,
                "online": online,
            }
        )

    return peers


# ── Route Handlers ────────────────────────────────────────────────


async def _devices_list(request: Request) -> list[dict[str, Any]]:
    """GET /devices/list — registered devices enriched with live Tailscale status."""
    registry = _load_registry()
    data = _get_tailscale_status()
    if not data:
        for dev in registry:
            dev.setdefault("online", dev.get("always_online", False))
        return registry

    ts_by_dns: dict[str, dict[str, Any]] = {}
    for peer in data.get("Peer", {}).values():
        dn = peer.get("DNSName", "").split(".")[0].lower()
        if dn:
            ts_by_dns[dn] = peer
    self_node = data.get("Self")
    if self_node:
        dn = self_node.get("DNSName", "").split(".")[0].lower()
        if dn:
            ts_by_dns[dn] = {**self_node, "_is_self": True}

    for dev in registry:
        ts_name = dev.get("tailscale_name", "").lower()
        ts_peer = ts_by_dns.get(ts_name)
        if ts_peer:
            dev["online"] = True if ts_peer.get("_is_self") else ts_peer.get("Online", False)
            live_ips = ts_peer.get("TailscaleIPs", [])
            if live_ips:
                dev["tailscale_ips"] = live_ips
        else:
            dev["online"] = dev.get("always_online", False)

    return registry


async def _devices_scan(request: Request) -> dict[str, Any]:
    """GET /devices/scan — unregistered, non-infrastructure Tailscale peers."""
    peers = _get_tailscale_peers()
    return {
        "peers": peers,
        "total": len(peers),
        "unregistered": len(peers),
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
        return {
            "success": True,
            "result": {
                "success": True,
                "device_id": device_id,
                "role": "controller",
                "steps": [],
                "mesh_connected": False,
            },
        }

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


async def _devices_update(request: Request) -> dict[str, Any]:
    """POST /devices/update — update device fields via mutation runtime."""
    body = await request.json()
    device_id = body.get("device_id", "")
    fields = body.get("fields", {})

    if not device_id:
        return {"success": False, "error": "device_id required"}
    if not fields:
        return {"success": False, "error": "fields required"}

    from transports.api.cockpit_settings_mutations import update_device_fields

    result = update_device_fields(device_id, fields)

    if not result.ok:
        return {"success": False, "error": result.errors[0] if result.errors else "Unknown error"}

    return {
        "success": True,
        "warnings": result.warnings,
        "audit": result.audit_event,
        "applied_state": result.applied_state,
        "requires_approval": result.requires_approval,
        "approval_reason": result.approval_reason,
    }
