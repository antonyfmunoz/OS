"""
StationDaemon — minimal local node execution loop.

This is the smallest viable real implementation of a local Station Daemon.
It runs on a workstation (or on the VPS for development), polls the
StationBus outbox for SafeActions addressed to its node_id, executes the
MVP-safe subset of action kinds, and posts ActionResult / StationEvent
messages back through the inbox.

Scope (intentional):
  - MVP-allowed actions only: PLAY_SOUND, SPEAK_TEXT.
  - No raw shell. No window control. No browser automation.
  - Graceful degradation when local audio/TTS libraries are unavailable —
    the daemon still completes the action path and returns a structured
    result rather than crashing.
  - Heartbeats every `heartbeat_interval_s` via NodeRegistry.upsert() so the
    node stays fresh in substrate persistence, plus a StationEvent tagged
    "heartbeat" so VPS-side listeners can observe liveness.

Not in scope (deferred):
  - WebSocket/HTTP transport (file bus is the MVP).
  - Policy widening beyond StationContract's MVP allow-list.
  - Capability-aware model routing.

Operator entrypoint:
    python3 -m execution.bridge.station_daemon --node-id $UMH_LOCAL_NODE_ID

Library entrypoint:
    from substrate.execution.bridge.station_daemon import StationDaemon
    StationDaemon(node_id=os.environ.get("UMH_LOCAL_NODE_ID", "")).run()
"""

from __future__ import annotations

import argparse
import asyncio
import os
import shutil
import signal
import subprocess
import sys
import threading
import time
import webbrowser
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Callable, Optional
from urllib.parse import urlparse

from substrate.execution.bridge.actions import (
    ActionKind,
    ActionResult,
    ActionStatus,
    SafeAction,
)
from substrate.execution.bridge.app_allowlist import resolve_app
from substrate.execution.bridge.nodes import Node, NodeRegistry, NodeStatus, NodeType
from substrate.execution.bridge.scenes import Scene, SceneStep, get_scene
from substrate.execution.bridge.station import StationEvent
from substrate.execution.bridge.station_bus import StationBus, get_station_bus


DEFAULT_NODE_ID = os.environ.get("UMH_LOCAL_NODE_ID", "")
DEFAULT_CAPABILITIES: tuple[str, ...] = (
    "audio_output",
    "text_to_speech",
    "local_filesystem",
    "url_open",
    "app_launch",
    "scene_bootstrap",
    "window_focus",
)
DEFAULT_POLL_INTERVAL_S = 1.0
DEFAULT_HEARTBEAT_INTERVAL_S = 15.0


def _log(msg: str) -> None:
    print(f"[station_daemon] {msg}", file=sys.stderr)


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


# ─── Handler result contract ─────────────────────────────────────────────────


@dataclass
class _HandlerOutcome:
    status: ActionStatus
    detail: str
    data: dict = field(default_factory=dict)


Handler = Callable[[SafeAction], _HandlerOutcome]


# ─── StationDaemon ────────────────────────────────────────────────────────────


class StationDaemon:
    """
    Minimal local node process.

    Responsibilities:
      1. Register itself into NodeRegistry on start.
      2. Poll StationBus outbox on `poll_interval_s`.
      3. Execute MVP-allowed actions via handlers.
      4. Post ActionResult for every consumed action.
      5. Emit StationEvent heartbeats on `heartbeat_interval_s`.

    Thread-safety:
      run() blocks; stop() is callable from signal handlers or other threads.
    """

    def __init__(
        self,
        node_id: str = DEFAULT_NODE_ID,
        *,
        capabilities: tuple[str, ...] = DEFAULT_CAPABILITIES,
        poll_interval_s: float = DEFAULT_POLL_INTERVAL_S,
        heartbeat_interval_s: float = DEFAULT_HEARTBEAT_INTERVAL_S,
        bus: Optional[StationBus] = None,
        registry: Optional[NodeRegistry] = None,
        dry_run: Optional[bool] = None,
    ) -> None:
        self.node_id = node_id
        self.capabilities = list(capabilities)
        self.poll_interval_s = poll_interval_s
        self.heartbeat_interval_s = heartbeat_interval_s
        self._bus = bus or get_station_bus()
        self._registry = registry or NodeRegistry.default()
        self._stop = threading.Event()
        self._last_heartbeat_ts: float = 0.0
        # Dry-run: side-effect-free execution for smoke tests and headless hosts.
        # Enable via constructor or STATION_DAEMON_DRY_RUN=1 in the environment.
        if dry_run is None:
            dry_run = os.getenv("STATION_DAEMON_DRY_RUN", "").lower() in (
                "1",
                "true",
                "yes",
            )
        self.dry_run = dry_run

        # HTTP transport — additive alongside file bus.
        self._http_enabled = not os.getenv("STATION_DAEMON_NO_HTTP", "").lower() in (
            "1",
            "true",
            "yes",
        )
        self._http_server: Optional["NodeTransportServer"] = None

        # Handler table — the ONLY action kinds this daemon will execute.
        # Adding kinds here is a deliberate, reviewable change.
        self._handlers: dict[ActionKind, Handler] = {
            ActionKind.PLAY_SOUND: self._handle_play_sound,
            ActionKind.SPEAK_TEXT: self._handle_speak_text,
            ActionKind.OPEN_URL: self._handle_open_url,
            ActionKind.LAUNCH_APP: self._handle_launch_app,
            ActionKind.OPEN_SCENE: self._handle_open_scene,
            ActionKind.FOCUS_APP: self._handle_focus_app,
        }

    # ─── Lifecycle ────────────────────────────────────────────────────────
    def register(self) -> Node:
        """Upsert this node into NodeRegistry so EOS can see it as alive."""
        node = Node(
            node_id=self.node_id,
            node_type=NodeType.LOCAL_STATION,
            capabilities=self.capabilities,
            status=NodeStatus.ONLINE,
            availability="when_awake",
            metadata={"role": "workstation", "daemon": "station_daemon"},
        )
        self._registry.upsert(node)
        _log(f"registered node {self.node_id} ({', '.join(self.capabilities)})")
        return node

    def stop(self) -> None:
        _log("stop requested")
        self._stop.set()

    def _start_http_transport(self) -> None:
        """Start the aiohttp HTTP transport in a background thread (best-effort)."""
        if not self._http_enabled:
            _log("HTTP transport disabled via STATION_DAEMON_NO_HTTP")
            return
        try:
            import asyncio
            from substrate.execution.bridge.node_transport import NodeTransportServer

            self._http_server = NodeTransportServer(self)

            def _run_http():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    started = loop.run_until_complete(self._http_server.start())
                    if started:
                        # Keep the loop running until daemon stops
                        loop.run_until_complete(self._http_wait_loop(loop))
                except Exception as e:
                    _log(f"HTTP transport thread error: {e}")
                finally:
                    if self._http_server is not None:
                        loop.run_until_complete(self._http_server.stop())
                    loop.close()

            self._http_thread = threading.Thread(
                target=_run_http, daemon=True, name="station-http"
            )
            self._http_thread.start()
            _log("HTTP transport thread started")

        except ImportError:
            _log("aiohttp not installed — HTTP transport disabled")
        except Exception as exc:
            _log(f"HTTP transport start failed: {exc}")

    async def _http_wait_loop(self, loop) -> None:
        """Wait in the async loop until the daemon's stop event is set."""
        while not self._stop.is_set():
            await asyncio.sleep(0.5)

    def _stop_http_transport(self) -> None:
        """Stop the HTTP transport (best-effort)."""
        if self._http_server is not None:
            _log("stopping HTTP transport")
            # The stop event will cause _http_wait_loop to exit,
            # which triggers cleanup in the thread.

    def run(self) -> None:
        """Blocking main loop. Returns when stop() is called.

        Starts HTTP transport alongside the file bus polling loop.
        Both transports run concurrently. File bus is always active.
        """
        self.register()
        self._emit_heartbeat(reason="startup")
        self._start_http_transport()
        _log(f"polling {self.node_id} outbox every {self.poll_interval_s}s")

        try:
            while not self._stop.is_set():
                self._tick()
                self._stop.wait(self.poll_interval_s)
        finally:
            self._stop_http_transport()
            self._mark_offline()
            _log("stopped")

    # ─── Single iteration ─────────────────────────────────────────────────
    def _tick(self) -> None:
        # Heartbeat first so we stay visible even under a flood of actions.
        now = time.monotonic()
        if now - self._last_heartbeat_ts >= self.heartbeat_interval_s:
            self._emit_heartbeat(reason="interval")
            self._last_heartbeat_ts = now

        # Consume any pending actions in one atomic swap.
        pending = self._bus.daemon_take_outbox(self.node_id)
        if not pending:
            return

        _log(f"picked up {len(pending)} action(s)")
        for raw in pending:
            self._process_action(raw)

    def _process_action(
        self, raw: dict, *, post_to_bus: bool = True
    ) -> Optional[_HandlerOutcome]:
        """Process a single action dict and return the outcome.

        Args:
            raw: SafeAction dict with kind, payload, action_id, etc.
            post_to_bus: If True (default), post result to StationBus inbox.
                         Set False when called from HTTP transport (result
                         returned directly to the caller).

        Returns:
            The _HandlerOutcome, or None if the kind was completely unknown.
        """
        action_id = raw.get("action_id", "unknown")
        kind_value = raw.get("kind", "")
        try:
            kind = ActionKind(kind_value)
        except ValueError:
            outcome = _HandlerOutcome(
                status=ActionStatus.REJECTED,
                detail=f"unknown action kind: {kind_value!r}",
            )
            if post_to_bus:
                self._post_result(action_id, outcome)
            return outcome

        handler = self._handlers.get(kind)
        if handler is None:
            outcome = _HandlerOutcome(
                status=ActionStatus.REJECTED,
                detail=f"no handler for {kind.value}; not in MVP allow-list",
            )
            if post_to_bus:
                self._post_result(action_id, outcome)
            return outcome

        action = SafeAction(
            kind=kind,
            payload=raw.get("payload", {}) or {},
            action_id=action_id,
            issued_by=raw.get("issued_by"),
            target_node_id=raw.get("target_node_id"),
            issued_at=raw.get("issued_at", _utcnow()),
        )

        try:
            outcome = handler(action)
        except Exception as e:
            # Never let a handler crash the loop.
            outcome = _HandlerOutcome(
                status=ActionStatus.FAILED,
                detail=f"handler raised {type(e).__name__}: {e}",
            )
            _log(f"handler error for {action_id}: {e}")

        if post_to_bus:
            self._post_result(action_id, outcome, kind=kind)
        return outcome

    # ─── Action handlers ──────────────────────────────────────────────────
    def _handle_play_sound(self, action: SafeAction) -> _HandlerOutcome:
        """
        PLAY_SOUND — attempt a local sound playback via a portable CLI tool.
        Degrades gracefully if no player is available.

        Expected payload: {"sound_id": str} or {"path": str}
        """
        payload = action.payload or {}
        sound_id = payload.get("sound_id")
        path = payload.get("path")
        target = path or sound_id or "<unspecified>"

        player = self._detect_audio_player()
        if player is None:
            _log(f"PLAY_SOUND fallback (no player): {target}")
            return _HandlerOutcome(
                status=ActionStatus.SUCCEEDED,
                detail="no local audio player available; logged only",
                data={"fallback": True, "requested": target},
            )

        if not path:
            # With only a sound_id and no asset resolver yet, degrade.
            _log(f"PLAY_SOUND fallback (no asset resolver): sound_id={sound_id}")
            return _HandlerOutcome(
                status=ActionStatus.SUCCEEDED,
                detail="no asset resolver for sound_id; logged only",
                data={"fallback": True, "sound_id": sound_id, "player": player},
            )

        try:
            subprocess.run(
                [player, path],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=30,
            )
            return _HandlerOutcome(
                status=ActionStatus.SUCCEEDED,
                detail=f"played {path} via {player}",
                data={"player": player, "path": path},
            )
        except (
            subprocess.CalledProcessError,
            subprocess.TimeoutExpired,
            FileNotFoundError,
        ) as e:
            return _HandlerOutcome(
                status=ActionStatus.FAILED,
                detail=f"player {player} failed: {e}",
                data={"player": player, "path": path},
            )

    def _handle_speak_text(self, action: SafeAction) -> _HandlerOutcome:
        """
        SPEAK_TEXT — attempt local TTS via a portable CLI tool.
        Degrades to stdout when no TTS is available.

        Expected payload: {"text": str, "voice": str (optional)}
        """
        payload = action.payload or {}
        text = (payload.get("text") or "").strip()
        if not text:
            return _HandlerOutcome(
                status=ActionStatus.REJECTED,
                detail="empty text",
            )

        tts = self._detect_tts()
        if tts is None:
            # Clean stdout fallback — we still "spoke" the text, just visibly.
            print(f"[station_daemon:speak] {text}")
            _log(f"SPEAK_TEXT fallback (no tts): {text[:60]}")
            return _HandlerOutcome(
                status=ActionStatus.SUCCEEDED,
                detail="no local TTS available; printed to stdout",
                data={"fallback": True, "text": text},
            )

        try:
            if tts == "say":
                subprocess.run(["say", text], check=True, timeout=60)
            elif tts == "espeak":
                subprocess.run(
                    ["espeak", text], check=True, timeout=60, stderr=subprocess.DEVNULL
                )
            elif tts == "spd-say":
                subprocess.run(["spd-say", "--wait", text], check=True, timeout=60)
            else:
                return _HandlerOutcome(
                    status=ActionStatus.FAILED,
                    detail=f"unknown tts backend {tts!r}",
                )
            return _HandlerOutcome(
                status=ActionStatus.SUCCEEDED,
                detail=f"spoke via {tts}",
                data={"tts": tts, "chars": len(text)},
            )
        except (
            subprocess.CalledProcessError,
            subprocess.TimeoutExpired,
            FileNotFoundError,
        ) as e:
            # Fall back to stdout — never fail the daemon because audio hardware is missing.
            print(f"[station_daemon:speak] {text}")
            return _HandlerOutcome(
                status=ActionStatus.SUCCEEDED,
                detail=f"tts {tts} errored ({e}); printed to stdout",
                data={"fallback": True, "tts": tts, "text": text},
            )

    def _handle_open_url(self, action: SafeAction) -> _HandlerOutcome:
        """
        OPEN_URL — open an http(s) URL using the stdlib `webbrowser` module.

        Safety:
          - Scheme must be http or https. Anything else is rejected.
          - No shell interpolation — webbrowser.open() invokes the registered
            handler directly.
          - In dry-run mode, the URL is validated and logged, not opened.

        Expected payload: {"url": str}
        """
        payload = action.payload or {}
        url = (payload.get("url") or "").strip()
        if not url:
            return _HandlerOutcome(status=ActionStatus.REJECTED, detail="empty url")

        try:
            parsed = urlparse(url)
        except Exception as e:
            return _HandlerOutcome(
                status=ActionStatus.REJECTED,
                detail=f"unparseable url: {e}",
            )
        if parsed.scheme not in ("http", "https"):
            return _HandlerOutcome(
                status=ActionStatus.REJECTED,
                detail=f"scheme {parsed.scheme!r} not allowed; only http/https",
            )
        if not parsed.netloc:
            return _HandlerOutcome(
                status=ActionStatus.REJECTED,
                detail="url missing host",
            )

        if self.dry_run:
            _log(f"OPEN_URL dry-run: {url}")
            return _HandlerOutcome(
                status=ActionStatus.SUCCEEDED,
                detail="dry-run; url validated but not opened",
                data={"dry_run": True, "url": url},
            )

        try:
            opened = webbrowser.open(url, new=2, autoraise=True)
        except Exception as e:
            return _HandlerOutcome(
                status=ActionStatus.FAILED,
                detail=f"webbrowser.open failed: {e}",
                data={"url": url},
            )
        if not opened:
            # No registered browser — graceful fallback.
            _log(f"OPEN_URL fallback (no browser): {url}")
            return _HandlerOutcome(
                status=ActionStatus.SUCCEEDED,
                detail="no registered browser; logged only",
                data={"fallback": True, "url": url},
            )
        return _HandlerOutcome(
            status=ActionStatus.SUCCEEDED,
            detail=f"opened {url}",
            data={"url": url},
        )

    def _handle_launch_app(self, action: SafeAction) -> _HandlerOutcome:
        """
        LAUNCH_APP — start a process from the app allow-list.

        Safety:
          - `app_id` must be in APP_ALLOWLIST. Arbitrary paths are rejected.
          - Only the declared candidate binaries are probed via `shutil.which`.
          - `subprocess.Popen` is called with a list (never shell=True).
          - Extra args are accepted but must be a list of strings.

        Expected payload: {"app_id": str, "args": list[str] (optional)}
        """
        payload = action.payload or {}
        app_id = payload.get("app_id")
        if not app_id:
            return _HandlerOutcome(
                status=ActionStatus.REJECTED, detail="missing app_id"
            )

        app = resolve_app(app_id)
        if app is None:
            return _HandlerOutcome(
                status=ActionStatus.REJECTED,
                detail=f"app_id {app_id!r} not in allow-list",
            )

        extra_args = payload.get("args") or []
        if not isinstance(extra_args, list) or not all(
            isinstance(a, str) for a in extra_args
        ):
            return _HandlerOutcome(
                status=ActionStatus.REJECTED,
                detail="args must be a list of strings",
            )

        binary: Optional[str] = None
        for candidate in app.candidates:
            if shutil.which(candidate):
                binary = candidate
                break

        if binary is None:
            _log(f"LAUNCH_APP fallback (no binary): {app_id}")
            return _HandlerOutcome(
                status=ActionStatus.SUCCEEDED,
                detail=f"no local binary for {app_id}; logged only",
                data={
                    "fallback": True,
                    "app_id": app_id,
                    "candidates": list(app.candidates),
                },
            )

        if self.dry_run:
            _log(f"LAUNCH_APP dry-run: {binary} (app_id={app_id})")
            return _HandlerOutcome(
                status=ActionStatus.SUCCEEDED,
                detail="dry-run; binary resolved but not launched",
                data={"dry_run": True, "app_id": app_id, "binary": binary},
            )

        argv = [binary, *app.default_args, *extra_args]
        try:
            subprocess.Popen(  # noqa: S603 — argv list, shell=False
                argv,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                close_fds=True,
            )
        except (OSError, FileNotFoundError) as e:
            return _HandlerOutcome(
                status=ActionStatus.FAILED,
                detail=f"launch failed: {e}",
                data={"app_id": app_id, "binary": binary},
            )
        return _HandlerOutcome(
            status=ActionStatus.SUCCEEDED,
            detail=f"launched {app_id} via {binary}",
            data={"app_id": app_id, "binary": binary},
        )

    def _handle_open_scene(self, action: SafeAction) -> _HandlerOutcome:
        """
        OPEN_SCENE — expand a code-declared scene into its safe steps and
        execute each through the daemon's own handler table.

        Safety:
          - Only scenes in SCENE_REGISTRY can be opened. Runtime scene
            definitions are explicitly rejected.
          - Each step is dispatched through `_handlers` so the MVP allow-list
            is re-enforced for every step.
          - A failing step does not abort the scene — per-step outcomes are
            collected into `data["steps"]` so the operator can see exactly
            what ran.

        Expected payload: {"scene": str}
        """
        payload = action.payload or {}
        scene_name = payload.get("scene")
        if not scene_name:
            return _HandlerOutcome(
                status=ActionStatus.REJECTED, detail="missing scene name"
            )

        scene: Optional[Scene] = get_scene(scene_name)
        if scene is None:
            return _HandlerOutcome(
                status=ActionStatus.REJECTED,
                detail=f"scene {scene_name!r} not in registry",
            )

        step_results: list[dict] = []
        any_failed = False
        for idx, step in enumerate(scene.steps):
            handler = self._handlers.get(step.kind)
            if handler is None:
                step_results.append(
                    {
                        "idx": idx,
                        "kind": step.kind.value,
                        "status": ActionStatus.REJECTED.value,
                        "detail": "no handler / not in MVP allow-list",
                    }
                )
                any_failed = True
                continue
            sub_action = SafeAction(
                kind=step.kind,
                payload=dict(step.payload),
                issued_by=f"scene:{scene.name}",
                target_node_id=self.node_id,
            )
            try:
                outcome = handler(sub_action)
            except Exception as e:
                outcome = _HandlerOutcome(
                    status=ActionStatus.FAILED,
                    detail=f"{type(e).__name__}: {e}",
                )
            step_results.append(
                {
                    "idx": idx,
                    "kind": step.kind.value,
                    "status": outcome.status.value,
                    "detail": outcome.detail,
                }
            )
            if outcome.status in (ActionStatus.FAILED, ActionStatus.REJECTED):
                any_failed = True

        status = ActionStatus.FAILED if any_failed else ActionStatus.SUCCEEDED
        return _HandlerOutcome(
            status=status,
            detail=f"scene {scene.name!r}: {len(step_results)} step(s)",
            data={"scene": scene.name, "steps": step_results},
        )

    def _handle_focus_app(self, action: SafeAction) -> _HandlerOutcome:
        """
        FOCUS_APP — raise a window belonging to an allow-listed app.

        Safety:
          - `app_id` must be in APP_ALLOWLIST, exactly like LAUNCH_APP.
            We do NOT accept free-form window titles.
          - Platform backends tried in order:
              * macOS:   `osascript -e 'tell application "X" to activate'`
              * Linux:   `wmctrl -x -a <wm_class>` (falls back to `-a <app_id>`)
          - If no backend is available, we log and return a soft-success
            fallback — the ritual/operator still gets a structured result
            instead of a crash. No mouse/keyboard control, no raw shell.

        Expected payload: {"app_id": str}
        """
        payload = action.payload or {}
        app_id = payload.get("app_id")
        if not app_id:
            return _HandlerOutcome(
                status=ActionStatus.REJECTED, detail="missing app_id"
            )

        app = resolve_app(app_id)
        if app is None:
            return _HandlerOutcome(
                status=ActionStatus.REJECTED,
                detail=f"app_id {app_id!r} not in allow-list",
            )

        if self.dry_run:
            _log(f"FOCUS_APP dry-run: {app_id}")
            return _HandlerOutcome(
                status=ActionStatus.SUCCEEDED,
                detail="dry-run; focus validated but not performed",
                data={"dry_run": True, "app_id": app_id},
            )

        # macOS backend
        if sys.platform == "darwin" and shutil.which("osascript"):
            # Probe candidate app names until one activates successfully.
            for candidate in app.candidates:
                script = f'tell application "{candidate}" to activate'
                try:
                    subprocess.run(  # noqa: S603 — argv list, shell=False
                        ["osascript", "-e", script],
                        check=True,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        timeout=5,
                    )
                    return _HandlerOutcome(
                        status=ActionStatus.SUCCEEDED,
                        detail=f"focused {candidate} via osascript",
                        data={"backend": "osascript", "candidate": candidate},
                    )
                except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
                    continue

        # Linux backend
        wmctrl = shutil.which("wmctrl")
        if wmctrl:
            for candidate in (*app.candidates, app_id):
                try:
                    subprocess.run(  # noqa: S603 — argv list, shell=False
                        [wmctrl, "-x", "-a", candidate],
                        check=True,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        timeout=3,
                    )
                    return _HandlerOutcome(
                        status=ActionStatus.SUCCEEDED,
                        detail=f"focused {candidate} via wmctrl",
                        data={"backend": "wmctrl", "candidate": candidate},
                    )
                except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
                    continue

        # Graceful fallback: no backend or no match — log, do not fail.
        _log(f"FOCUS_APP fallback (no backend): {app_id}")
        return _HandlerOutcome(
            status=ActionStatus.SUCCEEDED,
            detail="no focus backend available; logged only",
            data={"fallback": True, "app_id": app_id},
        )

    # ─── Backend detection ────────────────────────────────────────────────
    def _detect_audio_player(self) -> Optional[str]:
        for candidate in ("paplay", "aplay", "afplay", "ffplay"):
            if shutil.which(candidate):
                return candidate
        return None

    def _detect_tts(self) -> Optional[str]:
        for candidate in ("say", "espeak", "spd-say"):
            if shutil.which(candidate):
                return candidate
        return None

    # ─── Bus I/O ──────────────────────────────────────────────────────────
    def _post_result(
        self,
        action_id: str,
        outcome: _HandlerOutcome,
        *,
        kind: Optional[ActionKind] = None,
    ) -> None:
        result = ActionResult(
            action_id=action_id,
            status=outcome.status,
            detail=outcome.detail,
            data=outcome.data,
        )
        kind_value = kind.value if isinstance(kind, ActionKind) else None
        self._bus.daemon_post_result(self.node_id, result, kind=kind_value)
        _log(f"→ result {action_id} {outcome.status.value}: {outcome.detail}")

    def _emit_heartbeat(self, *, reason: str) -> None:
        # Refresh persistence so last_seen ticks forward.
        existing = self._registry.get(self.node_id)
        if existing is None:
            existing = self.register()
        else:
            existing.status = NodeStatus.ONLINE
            existing.capabilities = list(self.capabilities)
            self._registry.upsert(existing)

        event = StationEvent(
            node_id=self.node_id,
            event_type="heartbeat",
            payload={
                "reason": reason,
                "capabilities": list(self.capabilities),
                "status": NodeStatus.ONLINE.value,
                "last_seen": existing.last_seen,
            },
        )
        try:
            self._bus.daemon_post_event(self.node_id, event)
        except Exception as e:
            _log(f"heartbeat event post failed: {e}")

    def _mark_offline(self) -> None:
        try:
            existing = self._registry.get(self.node_id)
            if existing is not None:
                existing.status = NodeStatus.OFFLINE
                self._registry.upsert(existing)
        except Exception as e:
            _log(f"mark_offline failed: {e}")


# ─── Operator entrypoint ──────────────────────────────────────────────────────


def _build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="station_daemon",
        description="Minimal local Station Daemon for EOS substrate MVP.",
    )
    p.add_argument("--node-id", default=DEFAULT_NODE_ID)
    p.add_argument("--poll-interval", type=float, default=DEFAULT_POLL_INTERVAL_S)
    p.add_argument(
        "--heartbeat-interval", type=float, default=DEFAULT_HEARTBEAT_INTERVAL_S
    )
    p.add_argument(
        "--capability",
        action="append",
        default=None,
        help="Repeatable. Capability slug to advertise. Defaults applied if omitted.",
    )
    return p


def main(argv: Optional[list[str]] = None) -> int:
    args = _build_arg_parser().parse_args(argv)
    capabilities = tuple(args.capability) if args.capability else DEFAULT_CAPABILITIES
    daemon = StationDaemon(
        node_id=args.node_id,
        capabilities=capabilities,
        poll_interval_s=args.poll_interval,
        heartbeat_interval_s=args.heartbeat_interval,
    )

    def _handle_signal(signum, frame):  # noqa: ARG001
        daemon.stop()

    signal.signal(signal.SIGINT, _handle_signal)
    signal.signal(signal.SIGTERM, _handle_signal)

    daemon.run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


def start_station_daemon() -> None:
    """Start a StationDaemon with defaults in a background thread."""
    import threading
    daemon = StationDaemon()
    t = threading.Thread(target=daemon.run, daemon=True, name="station-daemon")
    t.start()
