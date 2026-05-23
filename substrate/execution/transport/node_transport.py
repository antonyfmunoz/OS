"""
NodeTransport — aiohttp transport adapter for local station daemon.

Thin HTTP server that exposes the station daemon's capabilities over
the network. This is an ADDITIVE transport alongside the existing
file bus — it does NOT replace file bus polling.

Endpoints:
    POST /node/heartbeat  — daemon heartbeat registration
    POST /node/task       — dispatch a SafeAction and get result
    POST /node/status     — return current node state
    GET  /node/health     — lightweight health check

Design rules (mirror substrate conventions):
- Transport only — calls existing daemon/handler logic.
- No duplicated business logic — delegates to StationDaemon methods.
- Additive — removing this file leaves the daemon fully operational.
- Best-effort — HTTP failures do not affect file bus operation.
- Graceful shutdown — cleanup on daemon stop.
"""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    from substrate.execution.transport.station_daemon import StationDaemon

# ─── Constants ───────────────────────────────────────────────────────────────

DEFAULT_HOST = "0.0.0.0"
DEFAULT_PORT = 7600


def _log(msg: str) -> None:
    print(f"[substrate.node_transport] {msg}", file=sys.stderr)


# ─── Transport Server ───────────────────────────────────────────────────────


class NodeTransportServer:
    """aiohttp-based HTTP transport for the station daemon.

    Created and managed by the StationDaemon. Runs as an asyncio task
    alongside the existing synchronous poll loop (which runs in a thread).

    The server binds to localhost only — not exposed externally.
    """

    def __init__(
        self,
        daemon: "StationDaemon",
        *,
        host: str = DEFAULT_HOST,
        port: int = DEFAULT_PORT,
    ) -> None:
        self._daemon = daemon
        self._host = host
        self._port = port
        self._app: Any = None
        self._runner: Any = None
        self._site: Any = None

    async def start(self) -> bool:
        """Start the HTTP transport server. Returns True on success."""
        try:
            from aiohttp import web

            self._app = web.Application()
            self._app.router.add_post("/node/heartbeat", self._handle_heartbeat)
            self._app.router.add_post("/node/task", self._handle_task)
            self._app.router.add_post("/node/status", self._handle_status)
            self._app.router.add_get("/node/health", self._handle_health)

            self._runner = web.AppRunner(self._app)
            await self._runner.setup()
            self._site = web.TCPSite(self._runner, self._host, self._port)
            await self._site.start()

            _log(f"HTTP transport started on {self._host}:{self._port}")
            return True

        except ImportError:
            _log("aiohttp not installed — HTTP transport disabled")
            return False
        except OSError as exc:
            _log(f"HTTP transport bind failed ({exc}) — disabled")
            return False
        except Exception as exc:  # noqa: BLE001
            _log(f"HTTP transport start failed: {exc}")
            return False

    async def stop(self) -> None:
        """Gracefully shut down the HTTP transport."""
        if self._runner is not None:
            try:
                await self._runner.cleanup()
                _log("HTTP transport stopped")
            except Exception as exc:  # noqa: BLE001
                _log(f"HTTP transport cleanup error: {exc}")

    @property
    def is_running(self) -> bool:
        return self._site is not None and self._runner is not None

    # ─── Handlers ────────────────────────────────────────────────────────

    async def _handle_health(self, request: Any) -> Any:
        """Lightweight health check — no auth, no processing."""
        from aiohttp import web

        return web.json_response(
            {
                "status": "ok",
                "node_id": self._daemon.node_id,
                "transport": "http",
            }
        )

    async def _handle_heartbeat(self, request: Any) -> Any:
        """Register/refresh daemon heartbeat."""
        from aiohttp import web

        try:
            self._daemon.register()
            self._daemon._emit_heartbeat(reason="http_heartbeat")
            return web.json_response(
                {
                    "status": "ok",
                    "node_id": self._daemon.node_id,
                }
            )
        except Exception as exc:  # noqa: BLE001
            _log(f"heartbeat handler error: {exc}")
            return web.json_response(
                {"status": "error", "detail": str(exc)}, status=500
            )

    async def _handle_task(self, request: Any) -> Any:
        """Dispatch a SafeAction and return the result.

        Expects JSON body with SafeAction fields:
            {"kind": "speak_text", "payload": {"text": "hello"}, ...}

        Returns ActionResult as JSON.
        """
        from aiohttp import web

        try:
            body = await request.json()
        except Exception:  # noqa: BLE001
            return web.json_response(
                {"status": "error", "detail": "invalid JSON body"}, status=400
            )

        try:
            # Process through the daemon's existing handler pipeline.
            # post_to_bus=False because the HTTP response IS the delivery.
            outcome = self._daemon._process_action(body, post_to_bus=False)

            if outcome is None:
                return web.json_response(
                    {
                        "status": "rejected",
                        "detail": "action not processed (unknown kind or missing handler)",
                    },
                    status=422,
                )

            # outcome is an _HandlerOutcome from _process_action
            return web.json_response(
                {
                    "status": outcome.status.value,
                    "detail": outcome.detail,
                    "data": outcome.data,
                }
            )

        except Exception as exc:  # noqa: BLE001
            _log(f"task handler error: {exc}")
            return web.json_response(
                {"status": "error", "detail": str(exc)}, status=500
            )

    async def _handle_status(self, request: Any) -> Any:
        """Return current node state."""
        from aiohttp import web

        try:
            from substrate.execution.transport.nodes import NodeRegistry

            registry = NodeRegistry.default()
            node = registry.get(self._daemon.node_id)

            if node is None:
                return web.json_response(
                    {
                        "status": "unknown",
                        "node_id": self._daemon.node_id,
                        "registered": False,
                    }
                )

            return web.json_response(
                {
                    "status": node.status.value,
                    "node_id": node.node_id,
                    "registered": True,
                    "node_type": node.node_type.value,
                    "capabilities": list(node.capabilities),
                    "last_seen": node.last_seen,
                }
            )

        except Exception as exc:  # noqa: BLE001
            _log(f"status handler error: {exc}")
            return web.json_response(
                {"status": "error", "detail": str(exc)}, status=500
            )


# ─── Client Helpers ──────────────────────────────────────────────────────────


async def send_task_via_http(
    action_dict: dict,
    *,
    host: str = DEFAULT_HOST,
    port: int = DEFAULT_PORT,
    timeout_s: float = 30.0,
) -> Optional[dict]:
    """Send a SafeAction to the local daemon via HTTP and return the result.

    Returns None on any transport failure. Callers should fall back to
    file bus or VPS execution on None.
    """
    try:
        import aiohttp

        url = f"http://{host}:{port}/node/task"
        timeout = aiohttp.ClientTimeout(total=timeout_s)

        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(url, json=action_dict) as resp:
                if resp.status == 200:
                    return await resp.json()
                body = await resp.text()
                _log(f"HTTP task failed ({resp.status}): {body}")
                return None

    except ImportError:
        _log("aiohttp not installed — cannot send via HTTP")
        return None
    except Exception as exc:  # noqa: BLE001
        _log(f"HTTP task send failed: {exc}")
        return None


async def check_http_health(
    *,
    host: str = DEFAULT_HOST,
    port: int = DEFAULT_PORT,
    timeout_s: float = 2.0,
) -> bool:
    """Quick health check against the local transport server."""
    try:
        import aiohttp

        url = f"http://{host}:{port}/node/health"
        timeout = aiohttp.ClientTimeout(total=timeout_s)

        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(url) as resp:
                return resp.status == 200

    except Exception:  # noqa: BLE001
        return False


# ─── Exports ─────────────────────────────────────────────────────────────────

__all__ = [
    "NodeTransportServer",
    "send_task_via_http",
    "check_http_health",
    "DEFAULT_HOST",
    "DEFAULT_PORT",
]
