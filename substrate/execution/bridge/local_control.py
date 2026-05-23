"""
Local control — safe OS-level action layer for the local machine.

NOT raw shell access. This is structured machine control with mode
enforcement. Every action goes through a permission check before it can
execute, and the current LocalControlMode gates what categories of
actions are available.

Modes (escalating trust):
  PASSIVE      — read-only observation (screen state, window list)
  ASSISTED     — open/focus apps and URLs, open scenes
  FULL_CONTROL — everything including typing, mouse, keyboard input

All requests are persisted through substrate.storage so they survive
across process boundaries. The store is bounded to 500 entries; oldest
completed requests are pruned first.

execute_control_request dispatches browser actions through
browser_agent (Playwright) and OS-level actions through subprocess
calls (xdg-open, wmctrl, xdotool). Scene actions resolve steps
from the registry and execute each one recursively.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Any, Optional


# ─── Constants ───────────────────────────────────────────────────────────────

_STORAGE_KEY_REQUESTS = "local_control_requests"
_STORAGE_KEY_MODE = "local_control_mode"
_MAX_REQUESTS = 500


def _log(msg: str) -> None:
    print(f"[substrate.local_control] {msg}", file=sys.stderr)


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def _make_id() -> str:
    return f"lcr_{uuid.uuid4().hex[:12]}"


# ─── Enums ───────────────────────────────────────────────────────────────────


class LocalControlAction(str, Enum):
    """Actions the local control layer can perform."""

    OPEN_APP = "open_app"
    FOCUS_APP = "focus_app"
    OPEN_URL = "open_url"
    OPEN_SCENE = "open_scene"
    TYPE_TEXT = "type_text"
    MOVE_MOUSE = "move_mouse"
    CLICK_MOUSE = "click_mouse"
    PRESS_KEYS = "press_keys"
    READ_SCREEN_STATE = "read_screen_state"
    LIST_WINDOWS = "list_windows"


class LocalControlMode(str, Enum):
    """Trust level for local machine control."""

    PASSIVE = "passive"
    ASSISTED = "assisted"
    FULL_CONTROL = "full_control"


class RequestStatus(str, Enum):
    """Lifecycle status of a control request."""

    PENDING = "pending"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"


# ─── Dataclass ───────────────────────────────────────────────────────────────


@dataclass
class LocalControlRequest:
    """A single local control request with full lifecycle tracking."""

    request_id: str
    action: LocalControlAction
    payload: dict[str, Any]
    created_at: str
    requested_by: str = "system"
    requires_confirmation: bool = False
    status: RequestStatus = RequestStatus.PENDING
    result: Optional[str] = None
    error: Optional[str] = None
    updated_at: str = ""

    def __post_init__(self) -> None:
        if not self.updated_at:
            self.updated_at = self.created_at

    @classmethod
    def new(
        cls,
        action: LocalControlAction,
        payload: dict[str, Any],
        *,
        requested_by: str = "system",
        requires_confirmation: bool = False,
    ) -> LocalControlRequest:
        """Create a new request with generated ID and timestamps."""
        now = _utcnow()
        return cls(
            request_id=_make_id(),
            action=action,
            payload=dict(payload),
            created_at=now,
            requested_by=requested_by,
            requires_confirmation=requires_confirmation,
            status=RequestStatus.PENDING,
            result=None,
            error=None,
            updated_at=now,
        )

    def to_dict(self) -> dict:
        """Serialize to a plain dict for storage."""
        return {
            "request_id": self.request_id,
            "action": self.action.value,
            "payload": self.payload,
            "created_at": self.created_at,
            "requested_by": self.requested_by,
            "requires_confirmation": self.requires_confirmation,
            "status": self.status.value,
            "result": self.result,
            "error": self.error,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, d: dict) -> LocalControlRequest:
        """Deserialize from a plain dict."""
        try:
            action = LocalControlAction(d["action"])
        except (KeyError, ValueError):
            action = LocalControlAction.LIST_WINDOWS  # safe fallback

        try:
            status = RequestStatus(d.get("status", "pending"))
        except ValueError:
            status = RequestStatus.PENDING

        return cls(
            request_id=str(d.get("request_id", _make_id())),
            action=action,
            payload=d.get("payload") or {},
            created_at=d.get("created_at") or _utcnow(),
            requested_by=str(d.get("requested_by", "system")),
            requires_confirmation=bool(d.get("requires_confirmation", False)),
            status=status,
            result=d.get("result"),
            error=d.get("error"),
            updated_at=d.get("updated_at") or _utcnow(),
        )


# ─── Store ───────────────────────────────────────────────────────────────────


class LocalControlStore:
    """Persistent store for local control requests and mode state.

    Singleton via ``default()`` classmethod. Backed by substrate.storage
    so data survives across process boundaries.
    """

    def __init__(self, *, autoload: bool = True) -> None:
        self._lock = threading.RLock()
        self._requests: dict[str, LocalControlRequest] = {}
        self._mode: LocalControlMode = LocalControlMode.PASSIVE
        self._loaded = False
        if autoload:
            self._load()

    # ── Persistence ──────────────────────────────────────────────────────

    def _load(self) -> None:
        with self._lock:
            if self._loaded:
                return
            try:
                from substrate.execution.bridge.storage import get_storage

                raw = get_storage().get(_STORAGE_KEY_REQUESTS, default={}) or {}
            except Exception as e:
                _log(f"load requests failed ({e}); starting empty")
                raw = {}

            rows = raw.get("rows", {}) if isinstance(raw, dict) else {}
            if isinstance(rows, dict):
                for rid, row in rows.items():
                    if not isinstance(row, dict):
                        continue
                    try:
                        self._requests[str(rid)] = LocalControlRequest.from_dict(row)
                    except Exception:
                        continue

            # Load mode
            try:
                from substrate.execution.bridge.storage import get_storage

                mode_raw = get_storage().get(_STORAGE_KEY_MODE, default=None)
            except Exception as e:
                _log(f"load mode failed ({e}); defaulting to PASSIVE")
                mode_raw = None

            if isinstance(mode_raw, dict):
                mode_val = mode_raw.get("mode", "passive")
            elif isinstance(mode_raw, str):
                mode_val = mode_raw
            else:
                mode_val = "passive"

            try:
                self._mode = LocalControlMode(mode_val)
            except ValueError:
                self._mode = LocalControlMode.PASSIVE

            self._loaded = True

    def _flush(self) -> None:
        """Persist current state to storage. Caller holds the lock."""
        try:
            from substrate.execution.bridge.storage import get_storage

            payload = {
                "rows": {rid: r.to_dict() for rid, r in self._requests.items()},
                "updated_at": _utcnow(),
            }
            get_storage().put(_STORAGE_KEY_REQUESTS, payload)
        except Exception as e:
            _log(f"flush requests failed: {e}")

    def _flush_mode(self) -> None:
        """Persist mode to storage. Caller holds the lock."""
        try:
            from substrate.execution.bridge.storage import get_storage

            get_storage().put(
                _STORAGE_KEY_MODE,
                {"mode": self._mode.value, "updated_at": _utcnow()},
            )
        except Exception as e:
            _log(f"flush mode failed: {e}")

    def _prune(self) -> None:
        """Drop oldest completed requests when over _MAX_REQUESTS. Caller holds lock."""
        if len(self._requests) <= _MAX_REQUESTS:
            return
        # Partition into completed and non-completed
        completed = [
            (rid, r)
            for rid, r in self._requests.items()
            if r.status in (RequestStatus.COMPLETED, RequestStatus.FAILED)
        ]
        completed.sort(key=lambda kv: kv[1].created_at)
        drop_count = len(self._requests) - _MAX_REQUESTS
        for rid, _ in completed[:drop_count]:
            self._requests.pop(rid, None)
        # If still over, drop oldest regardless of status
        if len(self._requests) > _MAX_REQUESTS:
            remaining = sorted(self._requests.items(), key=lambda kv: kv[1].created_at)
            extra = len(self._requests) - _MAX_REQUESTS
            for rid, _ in remaining[:extra]:
                self._requests.pop(rid, None)

    # ── Public API ───────────────────────────────────────────────────────

    def get(self, request_id: str) -> Optional[LocalControlRequest]:
        """Retrieve a single request by ID."""
        with self._lock:
            return self._requests.get(request_id)

    def put(self, request: LocalControlRequest) -> None:
        """Persist a request (insert or update), pruning if over cap."""
        with self._lock:
            self._requests[request.request_id] = request
            self._prune()
            self._flush()

    def all(self) -> list[LocalControlRequest]:
        """All requests sorted by created_at descending."""
        with self._lock:
            return sorted(
                self._requests.values(),
                key=lambda r: r.created_at,
                reverse=True,
            )

    def by_status(self, status: RequestStatus) -> list[LocalControlRequest]:
        """Filter requests by status, sorted by created_at descending."""
        with self._lock:
            return sorted(
                [r for r in self._requests.values() if r.status == status],
                key=lambda r: r.created_at,
                reverse=True,
            )

    def pending(self) -> list[LocalControlRequest]:
        """Convenience: all PENDING requests."""
        return self.by_status(RequestStatus.PENDING)

    def get_mode(self) -> LocalControlMode:
        """Return the current control mode (reads from loaded state)."""
        with self._lock:
            return self._mode

    def set_mode(self, mode: LocalControlMode) -> None:
        """Set the control mode and persist."""
        with self._lock:
            self._mode = mode
            self._flush_mode()
            _log(f"control mode set to {mode.value}")

    # ── Singleton ────────────────────────────────────────────────────────

    _default: Optional[LocalControlStore] = None
    _default_lock = threading.Lock()

    @classmethod
    def default(cls) -> LocalControlStore:
        """Return the process-wide singleton, creating on first call."""
        if cls._default is None:
            with cls._default_lock:
                if cls._default is None:
                    cls._default = cls()
        return cls._default

    @classmethod
    def reset_default_for_tests(cls) -> None:
        """Drop the singleton. Next ``default()`` rehydrates from storage."""
        with cls._default_lock:
            cls._default = None


# ─── Mode enforcement ────────────────────────────────────────────────────────

_PASSIVE_ALLOWED: set[LocalControlAction] = {
    LocalControlAction.READ_SCREEN_STATE,
    LocalControlAction.LIST_WINDOWS,
}

_ASSISTED_ALLOWED: set[LocalControlAction] = _PASSIVE_ALLOWED | {
    LocalControlAction.OPEN_APP,
    LocalControlAction.FOCUS_APP,
    LocalControlAction.OPEN_URL,
    LocalControlAction.OPEN_SCENE,
}

_FULL_CONTROL_ALLOWED: set[LocalControlAction] = _ASSISTED_ALLOWED | {
    LocalControlAction.TYPE_TEXT,
    LocalControlAction.MOVE_MOUSE,
    LocalControlAction.CLICK_MOUSE,
    LocalControlAction.PRESS_KEYS,
}

_MODE_ALLOWED: dict[LocalControlMode, set[LocalControlAction]] = {
    LocalControlMode.PASSIVE: _PASSIVE_ALLOWED,
    LocalControlMode.ASSISTED: _ASSISTED_ALLOWED,
    LocalControlMode.FULL_CONTROL: _FULL_CONTROL_ALLOWED,
}


def is_action_allowed(
    action: LocalControlAction, mode: Optional[LocalControlMode] = None
) -> bool:
    """Check if action is allowed in the given (or current) control mode."""
    if mode is None:
        mode = LocalControlStore.default().get_mode()
    return action in _MODE_ALLOWED.get(mode, set())


# ─── Safe action handlers ────────────────────────────────────────────────────


def submit_control_request(
    action: LocalControlAction,
    payload: dict[str, Any],
    *,
    requested_by: str = "system",
    requires_confirmation: bool = False,
    local_available: bool = False,
) -> LocalControlRequest:
    """Submit a local control request.

    1. Check mode enforcement — if action not allowed, set status=BLOCKED.
    2. Check local_available — if False, set status=BLOCKED with error.
    3. If allowed, set status=PENDING (actual execution is external).
    4. Persist and return.
    """
    req = LocalControlRequest.new(
        action,
        payload,
        requested_by=requested_by,
        requires_confirmation=requires_confirmation,
    )

    store = LocalControlStore.default()

    if not is_action_allowed(action):
        req.status = RequestStatus.BLOCKED
        req.error = (
            f"action {action.value} not allowed in mode {store.get_mode().value}"
        )
        req.updated_at = _utcnow()
        store.put(req)
        _log(f"BLOCKED {req.request_id}: {req.error}")
        return req

    if not local_available:
        req.status = RequestStatus.BLOCKED
        req.error = "local machine not available (no station daemon connected)"
        req.updated_at = _utcnow()
        store.put(req)
        _log(f"BLOCKED {req.request_id}: no local machine")
        return req

    # Allowed and local is available — mark pending for external pickup
    req.status = RequestStatus.PENDING
    req.updated_at = _utcnow()
    store.put(req)
    _log(f"PENDING {req.request_id}: {action.value}")
    return req


def execute_control_request(request_id: str) -> LocalControlRequest:
    """Mark a request as executing and dispatch to the appropriate handler.

    Routes browser actions through browser_agent and OS-level actions
    through subprocess calls. Scene actions resolve steps and execute
    each one recursively.
    """
    store = LocalControlStore.default()
    req = store.get(request_id)
    if req is None:
        now = _utcnow()
        return LocalControlRequest(
            request_id=request_id,
            action=LocalControlAction.LIST_WINDOWS,
            payload={},
            created_at=now,
            status=RequestStatus.FAILED,
            error=f"request {request_id} not found",
            updated_at=now,
        )

    req.status = RequestStatus.EXECUTING
    req.updated_at = _utcnow()

    _DISPATCH: dict[LocalControlAction, Any] = {
        LocalControlAction.OPEN_URL: _dispatch_browser_open_url,
        LocalControlAction.CLICK_MOUSE: _dispatch_browser_click,
        LocalControlAction.TYPE_TEXT: _dispatch_browser_type,
        LocalControlAction.PRESS_KEYS: _dispatch_browser_press_keys,
        LocalControlAction.READ_SCREEN_STATE: _dispatch_browser_screenshot,
        LocalControlAction.OPEN_APP: _dispatch_subprocess_open_app,
        LocalControlAction.FOCUS_APP: _dispatch_subprocess_focus_app,
        LocalControlAction.LIST_WINDOWS: _dispatch_subprocess_list_windows,
        LocalControlAction.MOVE_MOUSE: _dispatch_move_mouse,
        LocalControlAction.OPEN_SCENE: _dispatch_open_scene,
    }

    handler = _DISPATCH.get(req.action)
    if handler is None:
        req.status = RequestStatus.FAILED
        req.error = f"no handler for action {req.action.value}"
        req.updated_at = _utcnow()
        store.put(req)
        return req

    try:
        req = handler(req)
    except Exception as e:  # noqa: BLE001
        req.status = RequestStatus.FAILED
        req.error = f"dispatch error: {e}"
        req.updated_at = _utcnow()

    store.put(req)
    _log(f"{req.status.value.upper()} {req.request_id}: {req.result or req.error}")
    return req


# ─── Dispatch helpers ───────────────────────────────────────────────────────


def _dispatch_browser_open_url(req: LocalControlRequest) -> LocalControlRequest:
    """Open a URL via browser_agent."""
    from substrate.execution.bridge.browser_agent import BrowserActionType, execute_browser_action

    url = req.payload.get("url", "")
    result = execute_browser_action(BrowserActionType.OPEN_URL, {"url": url})
    if result.ok:
        req.status = RequestStatus.COMPLETED
        req.result = f"opened: {result.data}"
    else:
        req.status = RequestStatus.FAILED
        req.error = f"browser open_url failed: {result.error}"
    req.updated_at = _utcnow()
    return req


def _dispatch_browser_click(req: LocalControlRequest) -> LocalControlRequest:
    """Click an element via browser_agent."""
    from substrate.execution.bridge.browser_agent import BrowserActionType, execute_browser_action

    selector = req.payload.get("selector", "")
    result = execute_browser_action(BrowserActionType.CLICK, {"selector": selector})
    if result.ok:
        req.status = RequestStatus.COMPLETED
        req.result = f"clicked: {result.data}"
    else:
        req.status = RequestStatus.FAILED
        req.error = f"browser click failed: {result.error}"
    req.updated_at = _utcnow()
    return req


def _dispatch_browser_type(req: LocalControlRequest) -> LocalControlRequest:
    """Type text into an element via browser_agent."""
    from substrate.execution.bridge.browser_agent import BrowserActionType, execute_browser_action

    selector = req.payload.get("selector", "")
    text = req.payload.get("text", "")
    result = execute_browser_action(
        BrowserActionType.TYPE_TEXT, {"selector": selector, "text": text}
    )
    if result.ok:
        req.status = RequestStatus.COMPLETED
        req.result = f"typed into: {result.data}"
    else:
        req.status = RequestStatus.FAILED
        req.error = f"browser type_text failed: {result.error}"
    req.updated_at = _utcnow()
    return req


def _dispatch_browser_press_keys(req: LocalControlRequest) -> LocalControlRequest:
    """Press keyboard keys via browser_agent page.keyboard.press."""
    from substrate.execution.bridge.browser_agent import get_browser_agent

    keys = req.payload.get("keys", "")
    agent = get_browser_agent()
    try:
        with agent._lock:
            if not agent._has_page():
                req.status = RequestStatus.FAILED
                req.error = "no active page — call OPEN_URL first"
                req.updated_at = _utcnow()
                return req
            agent._page.keyboard.press(keys)
        req.status = RequestStatus.COMPLETED
        req.result = f"pressed: {keys}"
    except Exception as e:  # noqa: BLE001
        req.status = RequestStatus.FAILED
        req.error = f"browser press_keys failed: {e}"
    req.updated_at = _utcnow()
    return req


def _dispatch_browser_screenshot(req: LocalControlRequest) -> LocalControlRequest:
    """Take a screenshot via browser_agent."""
    from substrate.execution.bridge.browser_agent import BrowserActionType, execute_browser_action

    result = execute_browser_action(BrowserActionType.SCREENSHOT, {})
    if result.ok:
        req.status = RequestStatus.COMPLETED
        req.result = f"screenshot: {result.data}"
    else:
        req.status = RequestStatus.FAILED
        req.error = f"browser screenshot failed: {result.error}"
    req.updated_at = _utcnow()
    return req


def _dispatch_subprocess_open_app(req: LocalControlRequest) -> LocalControlRequest:
    """Open an application via xdg-open."""
    app_id = req.payload.get("app_id", "")
    xdg = shutil.which("xdg-open")
    if not xdg:
        req.status = RequestStatus.FAILED
        req.error = "xdg-open not found on this system"
        req.updated_at = _utcnow()
        return req
    try:
        proc = subprocess.run(
            [xdg, app_id],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if proc.returncode == 0:
            req.status = RequestStatus.COMPLETED
            req.result = f"dispatched: open_app {app_id}"
        else:
            req.status = RequestStatus.FAILED
            req.error = f"xdg-open returned {proc.returncode}: {proc.stderr.strip()}"
    except subprocess.TimeoutExpired:
        req.status = RequestStatus.FAILED
        req.error = f"xdg-open timed out opening {app_id}"
    except Exception as e:  # noqa: BLE001
        req.status = RequestStatus.FAILED
        req.error = f"open_app error: {e}"
    req.updated_at = _utcnow()
    return req


def _dispatch_subprocess_focus_app(req: LocalControlRequest) -> LocalControlRequest:
    """Focus an application window via wmctrl or xdotool."""
    app_name = req.payload.get("app_name", "")
    wmctrl = shutil.which("wmctrl")
    if wmctrl:
        try:
            proc = subprocess.run(
                [wmctrl, "-a", app_name],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if proc.returncode == 0:
                req.status = RequestStatus.COMPLETED
                req.result = f"focused (wmctrl): {app_name}"
                req.updated_at = _utcnow()
                return req
        except Exception:  # noqa: BLE001
            pass  # fall through to xdotool

    xdotool = shutil.which("xdotool")
    if xdotool:
        try:
            proc = subprocess.run(
                [xdotool, "search", "--name", app_name, "windowactivate"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if proc.returncode == 0:
                req.status = RequestStatus.COMPLETED
                req.result = f"focused (xdotool): {app_name}"
                req.updated_at = _utcnow()
                return req
            else:
                req.status = RequestStatus.FAILED
                req.error = f"xdotool focus failed: {proc.stderr.strip()}"
                req.updated_at = _utcnow()
                return req
        except Exception as e:  # noqa: BLE001
            req.status = RequestStatus.FAILED
            req.error = f"xdotool error: {e}"
            req.updated_at = _utcnow()
            return req

    req.status = RequestStatus.FAILED
    req.error = "neither wmctrl nor xdotool found on this system"
    req.updated_at = _utcnow()
    return req


def _dispatch_subprocess_list_windows(req: LocalControlRequest) -> LocalControlRequest:
    """List windows via wmctrl or xdotool."""
    wmctrl = shutil.which("wmctrl")
    if wmctrl:
        try:
            proc = subprocess.run(
                [wmctrl, "-l"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if proc.returncode == 0:
                req.status = RequestStatus.COMPLETED
                req.result = proc.stdout.strip() or "(no windows)"
                req.updated_at = _utcnow()
                return req
        except Exception:  # noqa: BLE001
            pass

    xdotool = shutil.which("xdotool")
    if xdotool:
        try:
            proc = subprocess.run(
                [xdotool, "search", "--name", ""],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if proc.returncode == 0:
                req.status = RequestStatus.COMPLETED
                req.result = proc.stdout.strip() or "(no windows)"
                req.updated_at = _utcnow()
                return req
            else:
                req.status = RequestStatus.FAILED
                req.error = f"xdotool list failed: {proc.stderr.strip()}"
                req.updated_at = _utcnow()
                return req
        except Exception as e:  # noqa: BLE001
            req.status = RequestStatus.FAILED
            req.error = f"xdotool error: {e}"
            req.updated_at = _utcnow()
            return req

    req.status = RequestStatus.FAILED
    req.error = "neither wmctrl nor xdotool found on this system"
    req.updated_at = _utcnow()
    return req


def _dispatch_move_mouse(req: LocalControlRequest) -> LocalControlRequest:
    """Move mouse via xdotool mousemove."""
    x = req.payload.get("x", 0)
    y = req.payload.get("y", 0)
    xdotool = shutil.which("xdotool")
    if not xdotool:
        req.status = RequestStatus.FAILED
        req.error = "xdotool not found on this system"
        req.updated_at = _utcnow()
        return req
    try:
        proc = subprocess.run(
            [xdotool, "mousemove", str(x), str(y)],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if proc.returncode == 0:
            req.status = RequestStatus.COMPLETED
            req.result = f"mouse moved to ({x}, {y})"
        else:
            req.status = RequestStatus.FAILED
            req.error = f"xdotool mousemove failed: {proc.stderr.strip()}"
    except Exception as e:  # noqa: BLE001
        req.status = RequestStatus.FAILED
        req.error = f"move_mouse error: {e}"
    req.updated_at = _utcnow()
    return req


def _action_kind_to_control_action(kind_value: str) -> Optional[LocalControlAction]:
    """Map an ActionKind value to a LocalControlAction for scene step dispatch."""
    _MAP = {
        "open_scene": LocalControlAction.OPEN_SCENE,
        "focus_app": LocalControlAction.FOCUS_APP,
        "launch_app": LocalControlAction.OPEN_APP,
        "run_browser_flow": LocalControlAction.OPEN_URL,
    }
    return _MAP.get(kind_value)


def _dispatch_open_scene(req: LocalControlRequest) -> LocalControlRequest:
    """Resolve a scene and execute each step recursively as a control request."""
    scene_name = req.payload.get("scene_name", "")
    try:
        from substrate.execution.bridge.scenes import get_scene

        scene = get_scene(scene_name)
    except Exception as e:  # noqa: BLE001
        req.status = RequestStatus.FAILED
        req.error = f"scene resolution error: {e}"
        req.updated_at = _utcnow()
        return req

    if scene is None:
        req.status = RequestStatus.FAILED
        req.error = f"scene '{scene_name}' not found in registry"
        req.updated_at = _utcnow()
        return req

    step_results: list[str] = []
    step_failures: list[str] = []
    store = LocalControlStore.default()

    for i, step in enumerate(scene.steps):
        control_action = _action_kind_to_control_action(step.kind.value)
        if control_action is None:
            step_failures.append(f"step {i}: unmapped action kind {step.kind.value}")
            continue

        # Submit a child request for this step (bypass local_available check
        # since the parent was already allowed through)
        child = LocalControlRequest.new(
            control_action,
            step.payload,
            requested_by=f"scene:{scene_name}",
        )
        child.status = RequestStatus.PENDING
        store.put(child)

        child_result = execute_control_request(child.request_id)
        if child_result.status == RequestStatus.COMPLETED:
            step_results.append(
                f"step {i} ({control_action.value}): {child_result.result}"
            )
        else:
            step_failures.append(
                f"step {i} ({control_action.value}): {child_result.error}"
            )

    total = len(scene.steps)
    ok_count = len(step_results)
    fail_count = len(step_failures)

    if fail_count == 0:
        req.status = RequestStatus.COMPLETED
        req.result = (
            f"scene '{scene_name}' completed: {ok_count}/{total} steps succeeded"
        )
    elif ok_count > 0:
        req.status = RequestStatus.COMPLETED
        req.result = (
            f"scene '{scene_name}' partial: {ok_count}/{total} ok, "
            f"{fail_count} failed — {'; '.join(step_failures)}"
        )
    else:
        req.status = RequestStatus.FAILED
        req.error = (
            f"scene '{scene_name}' all {total} steps failed — "
            f"{'; '.join(step_failures)}"
        )
    req.updated_at = _utcnow()
    return req


def open_scene(
    scene_name: str,
    *,
    requested_by: str = "system",
    local_available: bool = False,
) -> LocalControlRequest:
    """Convenience: submit an OPEN_SCENE request.

    Resolves scene_name against the scene registry. If the scene is not
    found, the request is immediately marked FAILED.
    """
    try:
        from substrate.execution.bridge.scenes import get_scene

        scene = get_scene(scene_name)
    except Exception as e:
        _log(f"scene lookup error: {e}")
        scene = None

    if scene is None:
        now = _utcnow()
        req = LocalControlRequest(
            request_id=_make_id(),
            action=LocalControlAction.OPEN_SCENE,
            payload={"scene_name": scene_name},
            created_at=now,
            requested_by=requested_by,
            status=RequestStatus.FAILED,
            error=f"scene '{scene_name}' not found in registry",
            updated_at=now,
        )
        LocalControlStore.default().put(req)
        _log(f"FAILED {req.request_id}: scene '{scene_name}' not found")
        return req

    return submit_control_request(
        LocalControlAction.OPEN_SCENE,
        {"scene_name": scene_name, "description": scene.description},
        requested_by=requested_by,
        local_available=local_available,
    )


# ─── Summary helper ──────────────────────────────────────────────────────────


def get_local_control_summary() -> dict:
    """Get summary suitable for open_day/close_day integration.

    Returns:
        {
            "control_mode": str,
            "pending_requests": int,
            "recent_completed": int,  # last 24h
            "recent_failed": int,
            "recent_blocked": int,
        }
    """
    store = LocalControlStore.default()
    all_reqs = store.all()
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()

    recent_completed = 0
    recent_failed = 0
    recent_blocked = 0

    for r in all_reqs:
        if r.created_at < cutoff:
            continue
        if r.status == RequestStatus.COMPLETED:
            recent_completed += 1
        elif r.status == RequestStatus.FAILED:
            recent_failed += 1
        elif r.status == RequestStatus.BLOCKED:
            recent_blocked += 1

    return {
        "control_mode": store.get_mode().value,
        "pending_requests": len(store.pending()),
        "recent_completed": recent_completed,
        "recent_failed": recent_failed,
        "recent_blocked": recent_blocked,
    }


# ─── Exports ─────────────────────────────────────────────────────────────────

__all__ = [
    "LocalControlAction",
    "LocalControlMode",
    "RequestStatus",
    "LocalControlRequest",
    "LocalControlStore",
    "is_action_allowed",
    "submit_control_request",
    "execute_control_request",
    "open_scene",
    "get_local_control_summary",
]
