"""Desktop adapter — GUI automation, window management, screenshots.

Runs in the tray companion process (user session with GUI access).
On the service side, requests are proxied to the tray via named pipe.
"""

from __future__ import annotations

import base64
import io
import logging
import sys
from typing import Any

logger = logging.getLogger(__name__)


class DesktopAdapter:
    """Desktop automation using pyautogui + pygetwindow."""

    def execute(self, operation: str, params: dict[str, Any]) -> dict[str, Any]:
        ops = {
            "desktop.click": self._click,
            "desktop.type": self._type,
            "desktop.screenshot": self._screenshot,
            "desktop.focus_window": self._focus_window,
            "desktop.list_windows": self._list_windows,
        }
        handler = ops.get(operation)
        if handler is None:
            return {"success": False, "error": f"unknown operation: {operation}"}
        try:
            return handler(params)
        except ImportError as exc:
            return {"success": False, "error": f"missing dependency: {exc}"}
        except Exception as exc:
            return {"success": False, "error": f"{type(exc).__name__}: {exc}"}

    def _click(self, params: dict[str, Any]) -> dict[str, Any]:
        import pyautogui

        x = params.get("x", 0)
        y = params.get("y", 0)
        button = params.get("button", "left")
        clicks = params.get("clicks", 1)
        pyautogui.click(x=x, y=y, button=button, clicks=clicks)
        return {"success": True, "x": x, "y": y}

    def _type(self, params: dict[str, Any]) -> dict[str, Any]:
        import pyautogui

        text = params.get("text", "")
        interval = params.get("interval", 0.02)
        pyautogui.typewrite(text, interval=interval)
        return {"success": True, "chars_typed": len(text)}

    def _screenshot(self, params: dict[str, Any]) -> dict[str, Any]:
        import pyautogui

        region = params.get("region")
        img = pyautogui.screenshot(region=tuple(region) if region else None)
        quality = params.get("quality", 75)
        fmt = params.get("format", "JPEG").upper()
        if fmt == "JPEG":
            img = img.convert("RGB")
        buf = io.BytesIO()
        if fmt == "JPEG":
            img.save(buf, format="JPEG", quality=quality, optimize=True)
        else:
            img.save(buf, format="PNG")
        raw_size = buf.tell()
        if raw_size > 3 * 1024 * 1024:
            new_w = img.width // 2
            new_h = img.height // 2
            img = img.resize((new_w, new_h))
            buf = io.BytesIO()
            img.save(buf, format=fmt, quality=quality if fmt == "JPEG" else None)
        encoded = base64.b64encode(buf.getvalue()).decode("ascii")
        return {
            "success": True,
            "image_base64": encoded,
            "width": img.width,
            "height": img.height,
            "format": fmt.lower(),
            "size_bytes": len(encoded) * 3 // 4,
        }

    def _focus_window(self, params: dict[str, Any]) -> dict[str, Any]:
        if sys.platform != "win32":
            return {"success": False, "error": "focus_window only supported on Windows"}

        import pygetwindow as gw

        title = params.get("title", "")
        windows = gw.getWindowsWithTitle(title)
        if not windows:
            return {"success": False, "error": f"no window matching: {title}"}
        win = windows[0]
        if win.isMinimized:
            win.restore()
        win.activate()
        return {"success": True, "window": win.title}

    def _list_windows(self, params: dict[str, Any]) -> dict[str, Any]:
        if sys.platform != "win32":
            return {"success": False, "error": "list_windows only supported on Windows"}

        import pygetwindow as gw

        windows = []
        for win in gw.getAllWindows():
            if win.title.strip():
                windows.append(
                    {
                        "title": win.title,
                        "visible": win.visible,
                        "minimized": win.isMinimized,
                        "x": win.left,
                        "y": win.top,
                        "width": win.width,
                        "height": win.height,
                    }
                )
        return {"success": True, "windows": windows[:100]}
