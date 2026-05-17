"""export_bridge_handler.py — Windows-side handler for fire_export bridge messages.

Receives fire_export commands from the VPS bridge server and executes
the PowerShell export script. Streams MFA challenges back to VPS.

This module extends local_bridge_server.py via its register_routes() function.
Does NOT modify the existing bridge server — additive only.

Architecture:
    VPS trigger_export.py → POST /fire-export on bridge server
    → This handler validates + dispatches PowerShell script
    → On MFA challenge: POST /mfa-challenge to VPS webhook receiver
    → VPS surfaces to Discord → user responds → POST /mfa-response here
    → Handler injects code into Playwright form
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import subprocess
import time
from pathlib import Path
from typing import Any

from aiohttp import web

logger = logging.getLogger("export_bridge")

_REPO_ROOT = Path(os.getenv("EOS_REPO_ROOT", str(Path.home() / "OS")))
_VPS_WEBHOOK_URL = os.getenv("EOS_VPS_WEBHOOK_URL", "http://100.77.233.50:8765")
_PROFILE_DIR = Path(os.getenv("PLAYWRIGHT_USER_DATA_DIR", str(Path.home() / ".playwright-profiles")))

_pending_mfa: dict[str, asyncio.Future] = {}


def _get_powershell_path() -> str:
    """Find PowerShell executable (pwsh preferred over powershell.exe)."""
    for candidate in ["pwsh", "powershell.exe", "pwsh.exe"]:
        try:
            result = subprocess.run(
                ["which", candidate],
                capture_output=True,
                timeout=5,
            )
            if result.returncode == 0:
                return candidate
        except (FileNotFoundError, subprocess.TimeoutExpired):
            continue
    return "powershell.exe"


async def _notify_vps_mfa(service: str, mfa_type: str, url: str, screenshot_path: str | None) -> bool:
    """POST MFA challenge back to VPS webhook receiver for Discord surfacing."""
    import aiohttp

    payload = {
        "type": "mfa_challenge",
        "service": service,
        "mfa_type": mfa_type,
        "url": url,
        "screenshot_path": screenshot_path,
        "timestamp": time.time(),
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{_VPS_WEBHOOK_URL}/mfa-challenge",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=10),
            ) as resp:
                return resp.status == 200
    except Exception as exc:
        logger.error("[ExportBridge] Failed to notify VPS of MFA: %s", exc)
        return False


async def _run_export(service: str, dry_run: bool = False) -> dict[str, Any]:
    """Execute the export script and monitor for MFA challenges."""
    if dry_run:
        logger.info("[ExportBridge] DRY RUN — would execute: fire_exports_windows.ps1 -Service %s", service)
        return {
            "ok": True,
            "message": f"dry_run: would execute fire_exports_windows.ps1 -Service {service}",
            "dry_run": True,
        }

    script_path = _REPO_ROOT / "scripts" / "fire_exports_windows.ps1"
    if not script_path.exists():
        return {"ok": False, "error": f"script not found: {script_path}"}

    ps = _get_powershell_path()

    env = os.environ.copy()
    env["BROWSER_HEADLESS"] = "false"
    env["PLAYWRIGHT_USER_DATA_DIR"] = str(_PROFILE_DIR / service)
    env["EOS_EXPORT_MFA_CALLBACK_URL"] = f"http://localhost:{os.getenv('EOS_LOCAL_BRIDGE_PORT', '8766')}/mfa-response"

    _PROFILE_DIR.mkdir(parents=True, exist_ok=True)
    (_PROFILE_DIR / service).mkdir(parents=True, exist_ok=True)

    logger.info("[ExportBridge] Executing: %s %s -Service %s", ps, script_path, service)

    try:
        proc = await asyncio.create_subprocess_exec(
            ps, "-ExecutionPolicy", "Bypass", "-File", str(script_path), "-Service", service,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env,
            cwd=str(_REPO_ROOT),
        )

        stdout_lines: list[str] = []
        mfa_detected = False

        async def _read_stream(stream: asyncio.StreamReader) -> None:
            nonlocal mfa_detected
            while True:
                line = await stream.readline()
                if not line:
                    break
                decoded = line.decode("utf-8", errors="replace").rstrip()
                stdout_lines.append(decoded)
                logger.info("[ExportBridge:%s] %s", service, decoded)

                if "MFA CHALLENGE DETECTED" in decoded or "MFA_CHALLENGE" in decoded:
                    mfa_detected = True
                    mfa_type = "UNKNOWN"
                    for prev_line in reversed(stdout_lines[-10:]):
                        if "Observed MFA type:" in prev_line:
                            mfa_type = prev_line.split(":", 1)[1].strip()
                            break

                    await _notify_vps_mfa(
                        service=service,
                        mfa_type=mfa_type,
                        url=decoded,
                        screenshot_path=None,
                    )

                    future: asyncio.Future = asyncio.get_event_loop().create_future()
                    _pending_mfa[service] = future

                    try:
                        mfa_response = await asyncio.wait_for(future, timeout=300)
                        logger.info("[ExportBridge:%s] MFA response received: %s", service, mfa_response)
                    except asyncio.TimeoutError:
                        logger.warning("[ExportBridge:%s] MFA response timed out (300s)", service)
                    finally:
                        _pending_mfa.pop(service, None)

        if proc.stdout:
            await _read_stream(proc.stdout)
        await proc.wait()

        return {
            "ok": proc.returncode == 0,
            "exit_code": proc.returncode,
            "mfa_detected": mfa_detected,
            "output_lines": len(stdout_lines),
            "message": f"export {service} completed with exit code {proc.returncode}",
        }

    except asyncio.TimeoutError:
        return {"ok": False, "error": "export process timed out"}
    except Exception as exc:
        return {"ok": False, "error": f"execution failed: {exc}"}


async def handle_fire_export(request: web.Request) -> web.Response:
    """Handle fire_export dispatch from VPS."""
    try:
        data = await request.json()
    except json.JSONDecodeError:
        return web.json_response({"ok": False, "error": "invalid json"}, status=400)

    service = data.get("service", "").lower()
    dry_run = data.get("dry_run", False)

    if service not in ("claude", "chatgpt", "instagram", "all"):
        return web.json_response(
            {"ok": False, "error": f"invalid service: {service}"},
            status=400,
        )

    if service == "all":
        results = {}
        for svc in ("claude", "chatgpt", "instagram"):
            results[svc] = await _run_export(svc, dry_run=dry_run)
        ok = all(r.get("ok") for r in results.values())
        return web.json_response({"ok": ok, "results": results})

    result = await _run_export(service, dry_run=dry_run)
    status_code = 200 if result.get("ok") else 500
    return web.json_response(result, status=status_code)


async def handle_mfa_response(request: web.Request) -> web.Response:
    """Receive MFA code/approval from VPS (routed from Discord user).

    Payload: {service: str, code: str, response_type: "code"|"approved"}
    """
    try:
        data = await request.json()
    except json.JSONDecodeError:
        return web.json_response({"ok": False, "error": "invalid json"}, status=400)

    service = data.get("service", "").lower()
    code = data.get("code", "").strip()
    response_type = data.get("response_type", "code")

    if not service:
        return web.json_response({"ok": False, "error": "missing service"}, status=400)

    future = _pending_mfa.get(service)
    if not future or future.done():
        return web.json_response(
            {"ok": False, "error": f"no pending MFA for {service}"},
            status=404,
        )

    future.set_result({"code": code, "response_type": response_type})
    logger.info("[ExportBridge] MFA response delivered for %s: type=%s", service, response_type)

    return web.json_response({"ok": True, "message": f"MFA response delivered to {service}"})


def register_routes(app: web.Application) -> None:
    """Register export bridge routes on the existing bridge server app.

    Call from local_bridge_server.py's create_app() to extend it.
    """
    app.router.add_post("/fire-export", handle_fire_export)
    app.router.add_post("/mfa-response", handle_mfa_response)
    logger.info("[ExportBridge] Routes registered: /fire-export, /mfa-response")
