"""Tailscale Admin API adapter.

Wraps the Tailscale v2 API for device management operations.
Auth key stored in env var TAILSCALE_API_KEY (injected via 1Password).

UMH adapter layer. Instance-agnostic.
"""

from __future__ import annotations

import json
import logging
import os
import urllib.request
import urllib.error
from typing import Any

logger = logging.getLogger(__name__)

_BASE_URL = "https://api.tailscale.com/api/v2"


def _api_key() -> str:
    key = os.environ.get("TAILSCALE_API_KEY", "")
    if not key:
        raise RuntimeError("TAILSCALE_API_KEY not set")
    return key


def _request(
    method: str,
    path: str,
    body: dict[str, Any] | None = None,
    timeout: int = 15,
) -> dict[str, Any]:
    """Make an authenticated request to the Tailscale API."""
    tailnet = os.environ.get("TAILSCALE_TAILNET", "-")
    url = f"{_BASE_URL}/tailnet/{tailnet}{path}" if path.startswith("/") else f"{_BASE_URL}/{path}"

    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", f"Bearer {_api_key()}")
    req.add_header("Content-Type", "application/json")

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        error_body = exc.read().decode() if exc.fp else ""
        logger.error("Tailscale API %s %s → %d: %s", method, path, exc.code, error_body)
        raise RuntimeError(f"Tailscale API error {exc.code}: {error_body}") from exc


def generate_auth_key(
    *,
    reusable: bool = False,
    ephemeral: bool = False,
    preauthorized: bool = True,
    expiry_seconds: int = 3600,
) -> dict[str, Any]:
    """Generate a Tailscale pre-auth key.

    Returns: { "key": "tskey-auth-...", "id": "...", "expires": "..." }
    """
    payload = {
        "capabilities": {
            "devices": {
                "create": {
                    "reusable": reusable,
                    "ephemeral": ephemeral,
                    "preauthorized": preauthorized,
                    "tags": [],
                },
            },
        },
        "expirySeconds": expiry_seconds,
    }
    return _request("POST", "/keys", body=payload)


def list_devices() -> list[dict[str, Any]]:
    """List all devices in the tailnet."""
    resp = _request("GET", "/devices")
    return resp.get("devices", [])


def remove_device(device_id: str) -> bool:
    """Remove a device from the tailnet. Returns True on success.

    Uses the device-level endpoint (not /tailnet/ prefixed).
    """
    try:
        _request("DELETE", f"device/{device_id}")
        return True
    except RuntimeError:
        return False


def api_key_expiry_check() -> dict[str, Any]:
    """Check API key validity. Returns status dict."""
    try:
        _request("GET", "/devices?limit=1")
        return {"valid": True, "error": ""}
    except RuntimeError as exc:
        return {"valid": False, "error": str(exc)}
