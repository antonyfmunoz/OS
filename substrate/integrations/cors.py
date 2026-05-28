"""CORS configuration for UMH API.

Centralizes allowed origins so they're consistent between the API
and any future services. Includes Tailscale IPs for cross-device access.
"""

from __future__ import annotations

import os

TAILSCALE_VPS = os.environ.get("TAILSCALE_VPS_IP", "")
TAILSCALE_DESKTOP = os.environ.get("TAILSCALE_DESKTOP_IP", "")
TAILSCALE_IPAD = os.environ.get("TAILSCALE_IPAD_IP", "")
TAILSCALE_IPHONE = os.environ.get("TAILSCALE_IPHONE_IP", "")

BACKEND_PORT = int(os.environ.get("UMH_BACKEND_PORT", "8093"))
FRONTEND_PORT = int(os.environ.get("UMH_FRONTEND_PORT", "5173"))


def cors_origins() -> list[str]:
    """Return all allowed CORS origins for the UMH API."""
    origins = [
        # Local development
        f"http://localhost:{FRONTEND_PORT}",
        f"http://localhost:{BACKEND_PORT}",
        f"http://127.0.0.1:{FRONTEND_PORT}",
        # Tailscale cross-device access
        f"http://{TAILSCALE_VPS}:{FRONTEND_PORT}",
        f"http://{TAILSCALE_VPS}:{BACKEND_PORT}",
        f"http://{TAILSCALE_DESKTOP}:{FRONTEND_PORT}",
        f"http://{TAILSCALE_IPAD}:{FRONTEND_PORT}",
        f"http://{TAILSCALE_IPHONE}:{FRONTEND_PORT}",
    ]

    extra = os.environ.get("UMH_CORS_EXTRA_ORIGINS", "")
    if extra:
        origins.extend(o.strip() for o in extra.split(",") if o.strip())

    return origins
