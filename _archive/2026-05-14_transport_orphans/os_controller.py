"""
OS controller — deep system control surface beyond browser automation.

Extends local_control.py with richer OS-level actions: coordinate-based
mouse control, keyboard automation, file operations, window management,
and optional OCR screen reading.

Uses pyautogui for input simulation when available, falling back to
xdotool/xclip subprocess calls on headless systems.

Design rules (mirror substrate conventions):
- Additive only.  Hot path never imported.
- Best-effort.  All public functions catch and log; never raise.
- Dependencies on pyautogui/PIL are OPTIONAL.  Lazy import with fallback.
- Thread-safe.  RLock on shared state.
- Reversible.  Removing this file leaves the substrate intact.
- Routing: local_control dispatches here for OS actions beyond browser.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional


# ─── Constants ──────────────────────────────────────────────────────────────


def _log(msg: str) -> None:
    print(f"[substrate.os_controller] {msg}", file=sys.stderr)


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_id(prefix: str = "osc") -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


# ─── Action Types ───────────────────────────────────────────────────────────


class OSAction(str, Enum):
    """Actions the OS controller can perform."""

    OPEN_APP = "open_app"
    FOCUS_WINDOW = "focus_window"
    TYPE_TEXT = "type_text"
    PRESS_KEYS = "press_keys"
    MOVE_MOUSE = "move_mouse"
    CLICK = "click"
    SCROLL = "scroll"
    READ_SCREEN = "read_screen"
    CREATE_FILE = "create_file"
    READ_FILE = "read_file"
    WRITE_FILE = "write_file"
    LIST_WINDOWS = "list_windows"


# ─── Result Dataclass ───────────────────────────────────────────────────────


@dataclass
class OSActionResult:
    """Outcome of a single OS controller action."""

    action: OSAction
    ok: bool
    data: Optional[str] = None
    error: Optional[str] = None
    duration_ms: float = 0.0
    created_at: str = field(default_factory=_utcnow)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a JSON-safe dict."""
        return {
            "action": self.action.value,
            "ok": self.ok,
            "data": self.data,
            "error": self.error,
            "duration_ms": self.duration_ms,
            "created_at": self.created_at,
        }


# ─── Capability Detection ──────────────────────────────────────────────────


def _has_pyautogui() -> bool:
    """Check if pyautogui is importable and a display is available."""
    try:
        import pyautogui  # noqa: F401

        return os.environ.get("DISPLAY") is not None
    except ImportError:
        return False


def _has_xdotool() -> bool:
    return shutil.which("xdotool") is not None


def _has_wmctrl() -> bool:
    return shutil.which("wmctrl") is not None


# ─── OS Controller ──────────────────────────────────────────────────────────


class OSController:
    """Deep OS-level control surface.

    Singleton via default().  Uses pyautogui when available, falls back
    to xdotool/subprocess.  Thread-safe.
    """

    _default: Optional["OSController"] = None
    _default_lock = threading.Lock()

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._pyautogui_available = _has_pyautogui()
        if self._pyautogui_available:
            try:
                import pyautogui

                pyautogui.FAILSAFE = True
                pyautogui.PAUSE = 0.1
            except Exception:
                self._pyautogui_available = False

    @classmethod
    def default(cls) -> "OSController":
        """Return the process-wide singleton."""
        if cls._default is None:
            with cls._default_lock:
                if cls._default is None:
                    cls._default = cls()
        return cls._default

    @classmethod
    def reset_default_for_tests(cls) -> None:
        """Tear down singleton for test isolation."""
        with cls._default_lock:
            cls._default = None

    # ── Dispatch ─────────────────────────────────────────────────────────

    def execute(
        self, action: OSAction, payload: dict[str, Any] | None = None
    ) -> OSActionResult:
        """Thread-safe dispatch to the appropriate handler.

        Always returns OSActionResult, never raises.
        """
        import time

        payload = payload or {}
        t0 = time.monotonic()

        try:
            with self._lock:
                result = self._dispatch(action, payload)
        except Exception as exc:
            result = OSActionResult(action=action, ok=False, error=str(exc))

        result.duration_ms = round((time.monotonic() - t0) * 1000, 2)
        return result

    def _dispatch(self, action: OSAction, payload: dict[str, Any]) -> OSActionResult:
        """Route to the correct handler.  Caller holds _lock."""
        handlers = {
            OSAction.OPEN_APP: self._do_open_app,
            OSAction.FOCUS_WINDOW: self._do_focus_window,
            OSAction.TYPE_TEXT: self._do_type_text,
            OSAction.PRESS_KEYS: self._do_press_keys,
            OSAction.MOVE_MOUSE: self._do_move_mouse,
            OSAction.CLICK: self._do_click,
            OSAction.SCROLL: self._do_scroll,
            OSAction.READ_SCREEN: self._do_read_screen,
            OSAction.CREATE_FILE: self._do_create_file,
            OSAction.READ_FILE: self._do_read_file,
            OSAction.WRITE_FILE: self._do_write_file,
            OSAction.LIST_WINDOWS: self._do_list_windows,
        }
        handler = handlers.get(action)
        if handler is None:
            label = action.value if isinstance(action, OSAction) else str(action)
            return OSActionResult(
                action=action, ok=False, error=f"unknown action: {label}"
            )
        return handler(payload)

    # ── App / Window Actions ─────────────────────────────────────────────

    def _do_open_app(self, payload: dict[str, Any]) -> OSActionResult:
        """Open an application by name or path."""
        app_name = payload.get("app_name", "")
        if not app_name:
            return OSActionResult(
                action=OSAction.OPEN_APP, ok=False, error="missing app_name"
            )

        xdg = shutil.which("xdg-open")
        if xdg:
            try:
                proc = subprocess.run(
                    [xdg, app_name], capture_output=True, text=True, timeout=10
                )
                if proc.returncode == 0:
                    _log(f"opened app: {app_name}")
                    return OSActionResult(
                        action=OSAction.OPEN_APP, ok=True, data=f"opened: {app_name}"
                    )
                return OSActionResult(
                    action=OSAction.OPEN_APP,
                    ok=False,
                    error=f"xdg-open returned {proc.returncode}: {proc.stderr.strip()}",
                )
            except subprocess.TimeoutExpired:
                return OSActionResult(
                    action=OSAction.OPEN_APP, ok=False, error="xdg-open timed out"
                )

        return OSActionResult(
            action=OSAction.OPEN_APP, ok=False, error="xdg-open not found"
        )

    def _do_focus_window(self, payload: dict[str, Any]) -> OSActionResult:
        """Focus a window by title substring."""
        window_name = payload.get("window_name", "")
        if not window_name:
            return OSActionResult(
                action=OSAction.FOCUS_WINDOW, ok=False, error="missing window_name"
            )

        if _has_wmctrl():
            try:
                proc = subprocess.run(
                    ["wmctrl", "-a", window_name],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                if proc.returncode == 0:
                    _log(f"focused window: {window_name}")
                    return OSActionResult(
                        action=OSAction.FOCUS_WINDOW,
                        ok=True,
                        data=f"focused: {window_name}",
                    )
            except Exception:
                pass

        if _has_xdotool():
            try:
                proc = subprocess.run(
                    ["xdotool", "search", "--name", window_name, "windowactivate"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                if proc.returncode == 0:
                    return OSActionResult(
                        action=OSAction.FOCUS_WINDOW,
                        ok=True,
                        data=f"focused: {window_name}",
                    )
                return OSActionResult(
                    action=OSAction.FOCUS_WINDOW,
                    ok=False,
                    error=f"xdotool focus failed: {proc.stderr.strip()}",
                )
            except Exception as exc:
                return OSActionResult(
                    action=OSAction.FOCUS_WINDOW, ok=False, error=str(exc)
                )

        return OSActionResult(
            action=OSAction.FOCUS_WINDOW,
            ok=False,
            error="neither wmctrl nor xdotool available",
        )

    def _do_list_windows(self, payload: dict[str, Any]) -> OSActionResult:
        """List all open windows."""
        if _has_wmctrl():
            try:
                proc = subprocess.run(
                    ["wmctrl", "-l"], capture_output=True, text=True, timeout=5
                )
                if proc.returncode == 0:
                    return OSActionResult(
                        action=OSAction.LIST_WINDOWS,
                        ok=True,
                        data=proc.stdout.strip() or "(no windows)",
                    )
            except Exception:
                pass

        if _has_xdotool():
            try:
                proc = subprocess.run(
                    ["xdotool", "search", "--name", ""],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                if proc.returncode == 0:
                    return OSActionResult(
                        action=OSAction.LIST_WINDOWS,
                        ok=True,
                        data=proc.stdout.strip() or "(no windows)",
                    )
            except Exception as exc:
                return OSActionResult(
                    action=OSAction.LIST_WINDOWS, ok=False, error=str(exc)
                )

        return OSActionResult(
            action=OSAction.LIST_WINDOWS,
            ok=False,
            error="no window manager tool available",
        )

    # ── Input Actions ────────────────────────────────────────────────────

    def _do_type_text(self, payload: dict[str, Any]) -> OSActionResult:
        """Type text at current cursor position."""
        text = payload.get("text", "")
        if not text:
            return OSActionResult(
                action=OSAction.TYPE_TEXT, ok=False, error="missing text"
            )

        if self._pyautogui_available:
            try:
                import pyautogui

                pyautogui.typewrite(
                    text, interval=0.02
                ) if text.isascii() else pyautogui.write(text)
                _log(f"typed: {text[:40]!r}")
                return OSActionResult(
                    action=OSAction.TYPE_TEXT, ok=True, data=f"typed: {len(text)} chars"
                )
            except Exception as exc:
                _log(f"pyautogui typewrite failed: {exc}")

        if _has_xdotool():
            try:
                proc = subprocess.run(
                    ["xdotool", "type", "--clearmodifiers", text],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                if proc.returncode == 0:
                    return OSActionResult(
                        action=OSAction.TYPE_TEXT,
                        ok=True,
                        data=f"typed: {len(text)} chars",
                    )
                return OSActionResult(
                    action=OSAction.TYPE_TEXT,
                    ok=False,
                    error=f"xdotool type failed: {proc.stderr.strip()}",
                )
            except Exception as exc:
                return OSActionResult(
                    action=OSAction.TYPE_TEXT, ok=False, error=str(exc)
                )

        return OSActionResult(
            action=OSAction.TYPE_TEXT, ok=False, error="no input method available"
        )

    def _do_press_keys(self, payload: dict[str, Any]) -> OSActionResult:
        """Press keyboard keys/shortcuts."""
        keys = payload.get("keys", "")
        if not keys:
            return OSActionResult(
                action=OSAction.PRESS_KEYS, ok=False, error="missing keys"
            )

        if self._pyautogui_available:
            try:
                import pyautogui

                # Handle combo keys like "ctrl+c"
                if "+" in keys:
                    parts = [k.strip() for k in keys.split("+")]
                    pyautogui.hotkey(*parts)
                else:
                    pyautogui.press(keys)
                _log(f"pressed: {keys}")
                return OSActionResult(
                    action=OSAction.PRESS_KEYS, ok=True, data=f"pressed: {keys}"
                )
            except Exception as exc:
                _log(f"pyautogui press failed: {exc}")

        if _has_xdotool():
            try:
                proc = subprocess.run(
                    ["xdotool", "key", keys], capture_output=True, text=True, timeout=5
                )
                if proc.returncode == 0:
                    return OSActionResult(
                        action=OSAction.PRESS_KEYS, ok=True, data=f"pressed: {keys}"
                    )
                return OSActionResult(
                    action=OSAction.PRESS_KEYS,
                    ok=False,
                    error=f"xdotool key failed: {proc.stderr.strip()}",
                )
            except Exception as exc:
                return OSActionResult(
                    action=OSAction.PRESS_KEYS, ok=False, error=str(exc)
                )

        return OSActionResult(
            action=OSAction.PRESS_KEYS, ok=False, error="no input method available"
        )

    def _do_move_mouse(self, payload: dict[str, Any]) -> OSActionResult:
        """Move mouse to absolute coordinates."""
        x = payload.get("x", 0)
        y = payload.get("y", 0)

        if self._pyautogui_available:
            try:
                import pyautogui

                pyautogui.moveTo(x, y, duration=0.2)
                _log(f"mouse moved to ({x}, {y})")
                return OSActionResult(
                    action=OSAction.MOVE_MOUSE, ok=True, data=f"moved to ({x}, {y})"
                )
            except Exception as exc:
                _log(f"pyautogui moveTo failed: {exc}")

        if _has_xdotool():
            try:
                proc = subprocess.run(
                    ["xdotool", "mousemove", str(x), str(y)],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                if proc.returncode == 0:
                    return OSActionResult(
                        action=OSAction.MOVE_MOUSE, ok=True, data=f"moved to ({x}, {y})"
                    )
            except Exception as exc:
                return OSActionResult(
                    action=OSAction.MOVE_MOUSE, ok=False, error=str(exc)
                )

        return OSActionResult(
            action=OSAction.MOVE_MOUSE, ok=False, error="no mouse control available"
        )

    def _do_click(self, payload: dict[str, Any]) -> OSActionResult:
        """Click at coordinates with specified button."""
        x = payload.get("x")
        y = payload.get("y")
        button = payload.get("button", "left")

        if self._pyautogui_available:
            try:
                import pyautogui

                if x is not None and y is not None:
                    pyautogui.click(x=x, y=y, button=button)
                else:
                    pyautogui.click(button=button)
                pos = f"({x}, {y})" if x is not None else "current position"
                _log(f"clicked {button} at {pos}")
                return OSActionResult(
                    action=OSAction.CLICK, ok=True, data=f"clicked {button} at {pos}"
                )
            except Exception as exc:
                _log(f"pyautogui click failed: {exc}")

        if _has_xdotool():
            button_map = {"left": "1", "middle": "2", "right": "3"}
            btn = button_map.get(button, "1")
            try:
                cmds = []
                if x is not None and y is not None:
                    cmds = ["xdotool", "mousemove", str(x), str(y), "click", btn]
                else:
                    cmds = ["xdotool", "click", btn]
                proc = subprocess.run(cmds, capture_output=True, text=True, timeout=5)
                if proc.returncode == 0:
                    return OSActionResult(
                        action=OSAction.CLICK, ok=True, data=f"clicked button {btn}"
                    )
            except Exception as exc:
                return OSActionResult(action=OSAction.CLICK, ok=False, error=str(exc))

        return OSActionResult(
            action=OSAction.CLICK, ok=False, error="no click method available"
        )

    def _do_scroll(self, payload: dict[str, Any]) -> OSActionResult:
        """Scroll by amount (positive = up, negative = down)."""
        amount = payload.get("amount", 0)
        if amount == 0:
            return OSActionResult(
                action=OSAction.SCROLL, ok=False, error="missing or zero amount"
            )

        if self._pyautogui_available:
            try:
                import pyautogui

                pyautogui.scroll(amount)
                direction = "up" if amount > 0 else "down"
                _log(f"scrolled {direction} by {abs(amount)}")
                return OSActionResult(
                    action=OSAction.SCROLL,
                    ok=True,
                    data=f"scrolled {direction} {abs(amount)}",
                )
            except Exception as exc:
                _log(f"pyautogui scroll failed: {exc}")

        if _has_xdotool():
            try:
                # xdotool: button 4 = scroll up, button 5 = scroll down
                btn = "4" if amount > 0 else "5"
                clicks = abs(amount)
                for _ in range(min(clicks, 50)):
                    subprocess.run(
                        ["xdotool", "click", btn],
                        capture_output=True,
                        text=True,
                        timeout=2,
                    )
                return OSActionResult(
                    action=OSAction.SCROLL, ok=True, data=f"scrolled {clicks} clicks"
                )
            except Exception as exc:
                return OSActionResult(action=OSAction.SCROLL, ok=False, error=str(exc))

        return OSActionResult(
            action=OSAction.SCROLL, ok=False, error="no scroll method available"
        )

    # ── Screen Reading ───────────────────────────────────────────────────

    def _do_read_screen(self, payload: dict[str, Any]) -> OSActionResult:
        """Take a screenshot with optional basic OCR."""
        screenshot_path = (
            payload.get("path") or f"/tmp/eos_screen_{uuid.uuid4().hex[:8]}.png"
        )

        # Try pyautogui screenshot first
        if self._pyautogui_available:
            try:
                import pyautogui

                img = pyautogui.screenshot()
                img.save(screenshot_path)
                _log(f"screenshot saved: {screenshot_path}")

                # Optional OCR if pytesseract available
                ocr_text = self._try_ocr(screenshot_path)
                data = f"screenshot: {screenshot_path}"
                if ocr_text:
                    data += f"\nocr: {ocr_text[:500]}"
                return OSActionResult(action=OSAction.READ_SCREEN, ok=True, data=data)
            except Exception as exc:
                _log(f"pyautogui screenshot failed: {exc}")

        # Fallback: import-mss or scrot
        scrot = shutil.which("scrot")
        if scrot:
            try:
                proc = subprocess.run(
                    [scrot, screenshot_path], capture_output=True, text=True, timeout=10
                )
                if proc.returncode == 0:
                    return OSActionResult(
                        action=OSAction.READ_SCREEN,
                        ok=True,
                        data=f"screenshot: {screenshot_path}",
                    )
            except Exception:
                pass

        return OSActionResult(
            action=OSAction.READ_SCREEN,
            ok=False,
            error="no screenshot method available",
        )

    def _try_ocr(self, image_path: str) -> Optional[str]:
        """Best-effort OCR on a screenshot.  Returns text or None."""
        try:
            import pytesseract
            from PIL import Image

            img = Image.open(image_path)
            text = pytesseract.image_to_string(img)
            return text.strip() if text.strip() else None
        except ImportError:
            return None
        except Exception as exc:
            _log(f"OCR failed: {exc}")
            return None

    # ── File Operations ──────────────────────────────────────────────────

    def _do_create_file(self, payload: dict[str, Any]) -> OSActionResult:
        """Create a file with optional content."""
        path = payload.get("path", "")
        content = payload.get("content", "")
        if not path:
            return OSActionResult(
                action=OSAction.CREATE_FILE, ok=False, error="missing path"
            )

        try:
            parent = os.path.dirname(path)
            if parent:
                os.makedirs(parent, exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
            _log(f"created file: {path} ({len(content)} bytes)")
            return OSActionResult(
                action=OSAction.CREATE_FILE, ok=True, data=f"created: {path}"
            )
        except Exception as exc:
            return OSActionResult(action=OSAction.CREATE_FILE, ok=False, error=str(exc))

    def _do_read_file(self, payload: dict[str, Any]) -> OSActionResult:
        """Read a file and return its content."""
        path = payload.get("path", "")
        if not path:
            return OSActionResult(
                action=OSAction.READ_FILE, ok=False, error="missing path"
            )

        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            # Truncate for result — full content in payload
            preview = content[:500] + ("..." if len(content) > 500 else "")
            _log(f"read file: {path} ({len(content)} bytes)")
            return OSActionResult(action=OSAction.READ_FILE, ok=True, data=preview)
        except Exception as exc:
            return OSActionResult(action=OSAction.READ_FILE, ok=False, error=str(exc))

    def _do_write_file(self, payload: dict[str, Any]) -> OSActionResult:
        """Write content to an existing or new file."""
        path = payload.get("path", "")
        content = payload.get("content", "")
        if not path:
            return OSActionResult(
                action=OSAction.WRITE_FILE, ok=False, error="missing path"
            )

        try:
            parent = os.path.dirname(path)
            if parent:
                os.makedirs(parent, exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
            _log(f"wrote file: {path} ({len(content)} bytes)")
            return OSActionResult(
                action=OSAction.WRITE_FILE, ok=True, data=f"wrote: {path}"
            )
        except Exception as exc:
            return OSActionResult(action=OSAction.WRITE_FILE, ok=False, error=str(exc))


# ─── Module-Level API ───────────────────────────────────────────────────────


def get_os_controller() -> OSController:
    """Return the singleton OSController."""
    return OSController.default()


def execute_os_action(
    action: OSAction, payload: dict[str, Any] | None = None
) -> OSActionResult:
    """Convenience: execute an OS action via the singleton controller."""
    return OSController.default().execute(action, payload)


# ─── Exports ────────────────────────────────────────────────────────────────

__all__ = [
    "OSAction",
    "OSActionResult",
    "OSController",
    "get_os_controller",
    "execute_os_action",
]
