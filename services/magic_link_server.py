"""magic_link_server.py — Standalone VPS server for magic-link email interception.

Runs independently on port 8769 (configurable via MAGIC_LINK_SERVER_PORT).
Called by auth flows running on Windows when they need a magic-link URL
extracted from Gmail.

The GWS CLI (with gmail.readonly scope) runs here on VPS where Node.js
and auth are configured. Windows cannot run GWS CLI.

Usage:
    python3 services/magic_link_server.py

Architecture:
    Windows auth_flow → POST http://VPS:8769/api/auth/wait-for-magic-link
    → This server polls Gmail via GWSConnector
    → Extracts magic-link URL from email body
    → Returns {"magic_link_url": "https://..."} to Windows
"""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from aiohttp import web

from services.magic_link_handler import register_routes

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger("magic_link_server")

PORT = int(os.getenv("MAGIC_LINK_SERVER_PORT", "8769"))


def create_app() -> web.Application:
    app = web.Application()

    async def handle_health(_request: web.Request) -> web.Response:
        return web.json_response({"status": "ok", "service": "magic_link_server"})

    app.router.add_get("/health", handle_health)
    register_routes(app)
    return app


if __name__ == "__main__":
    print(f"[MagicLinkServer] Starting on 0.0.0.0:{PORT}")
    print(f"[MagicLinkServer] Endpoint: POST /api/auth/wait-for-magic-link")
    app = create_app()
    web.run_app(app, host="0.0.0.0", port=PORT, print=None)
