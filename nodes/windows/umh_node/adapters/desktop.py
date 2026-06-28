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
            "desktop.rotate_monitor": self._rotate_monitor,
            "desktop.get_monitor_orientation": self._get_monitor_orientation,
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

    def _get_monitor_orientation(self, params: dict[str, Any]) -> dict[str, Any]:
        if sys.platform != "win32":
            return {"success": False, "error": "Windows only"}

        monitor_index = params.get("monitor_index", 0)
        device_name = _find_active_display(monitor_index)
        if not device_name:
            return {"success": False, "error": f"monitor index {monitor_index} not found"}

        dm = _get_display_settings(device_name)
        if not dm:
            return {"success": False, "error": f"could not get settings for {device_name}"}

        orient_map = {0: "landscape", 1: "portrait", 2: "landscape_flipped", 3: "portrait_flipped"}
        return {
            "success": True,
            "device": device_name,
            "orientation": orient_map.get(dm.dmDisplayOrientation, "unknown"),
            "width": dm.dmPelsWidth,
            "height": dm.dmPelsHeight,
        }

    def _rotate_monitor(self, params: dict[str, Any]) -> dict[str, Any]:
        """Rotate a monitor. orientation: landscape|portrait|landscape_flipped|portrait_flipped|toggle"""
        if sys.platform != "win32":
            return {"success": False, "error": "Windows only"}

        monitor_index = params.get("monitor_index", 0)
        target = params.get("orientation", "toggle")

        device_name = _find_active_display(monitor_index)
        if not device_name:
            return {"success": False, "error": f"monitor index {monitor_index} not found"}

        dm = _get_display_settings(device_name)
        if not dm:
            return {"success": False, "error": f"could not get settings for {device_name}"}

        orient_values = {"landscape": 0, "portrait": 1, "landscape_flipped": 2, "portrait_flipped": 3}

        if target == "toggle":
            is_portrait = dm.dmDisplayOrientation in (1, 3)
            target = "landscape" if is_portrait else "portrait"

        new_orient = orient_values.get(target)
        if new_orient is None:
            return {"success": False, "error": f"invalid orientation: {target}"}

        current = dm.dmDisplayOrientation
        is_90_shift = abs(new_orient - current) in (1, 3)
        if is_90_shift:
            dm.dmPelsWidth, dm.dmPelsHeight = dm.dmPelsHeight, dm.dmPelsWidth

        dm.dmDisplayOrientation = new_orient
        dm.dmFields = dm.dmFields | 0x00000080  # DM_DISPLAYORIENTATION

        result = _change_display_settings(device_name, dm)
        if result == 0:  # DISP_CHANGE_SUCCESSFUL
            orient_map = {v: k for k, v in orient_values.items()}
            return {
                "success": True,
                "device": device_name,
                "orientation": orient_map.get(new_orient, "unknown"),
                "width": dm.dmPelsWidth,
                "height": dm.dmPelsHeight,
            }
        return {"success": False, "error": f"ChangeDisplaySettingsEx returned {result}"}


# ── ctypes display helpers (avoids pywin32 EnumDisplayDevices crash on Python 3.14) ──

if sys.platform == "win32":
    import ctypes
    import ctypes.wintypes as _wt

    class _DISPLAY_DEVICE(ctypes.Structure):
        _fields_ = [
            ("cb", _wt.DWORD),
            ("DeviceName", ctypes.c_wchar * 32),
            ("DeviceString", ctypes.c_wchar * 128),
            ("StateFlags", _wt.DWORD),
            ("DeviceID", ctypes.c_wchar * 128),
            ("DeviceKey", ctypes.c_wchar * 128),
        ]

    class _DEVMODE(ctypes.Structure):
        _fields_ = [
            ("dmDeviceName", ctypes.c_wchar * 32),
            ("dmSpecVersion", _wt.WORD),
            ("dmDriverVersion", _wt.WORD),
            ("dmSize", _wt.WORD),
            ("dmDriverExtra", _wt.WORD),
            ("dmFields", _wt.DWORD),
            ("dmPositionX", ctypes.c_long),
            ("dmPositionY", ctypes.c_long),
            ("dmDisplayOrientation", _wt.DWORD),
            ("dmDisplayFixedOutput", _wt.DWORD),
            ("dmColor", ctypes.c_short),
            ("dmDuplex", ctypes.c_short),
            ("dmYResolution", ctypes.c_short),
            ("dmTTOption", ctypes.c_short),
            ("dmCollate", ctypes.c_short),
            ("dmFormName", ctypes.c_wchar * 32),
            ("dmLogPixels", _wt.WORD),
            ("dmBitsPerPel", _wt.DWORD),
            ("dmPelsWidth", _wt.DWORD),
            ("dmPelsHeight", _wt.DWORD),
            ("dmDisplayFlags", _wt.DWORD),
            ("dmDisplayFrequency", _wt.DWORD),
        ]

    def _find_active_display(monitor_index: int) -> str | None:
        u32 = ctypes.windll.user32
        idx = 0
        for i in range(20):
            dd = _DISPLAY_DEVICE()
            dd.cb = ctypes.sizeof(dd)
            if not u32.EnumDisplayDevicesW(None, i, ctypes.byref(dd), 0):
                break
            if dd.StateFlags & 1:  # DISPLAY_DEVICE_ACTIVE
                if idx == monitor_index:
                    return dd.DeviceName
                idx += 1
        return None

    def _get_display_settings(device_name: str) -> "_DEVMODE | None":
        dm = _DEVMODE()
        dm.dmSize = ctypes.sizeof(dm)
        u32 = ctypes.windll.user32
        if u32.EnumDisplaySettingsW(device_name, -1, ctypes.byref(dm)):
            return dm
        return None

    def _change_display_settings(device_name: str, dm: _DEVMODE) -> int:
        u32 = ctypes.windll.user32
        return u32.ChangeDisplaySettingsExW(device_name, ctypes.byref(dm), None, 1, None)

else:
    def _find_active_display(monitor_index: int) -> str | None:
        return None

    def _get_display_settings(device_name: str) -> Any:
        return None

    def _change_display_settings(device_name: str, dm: Any) -> int:
        return -1
