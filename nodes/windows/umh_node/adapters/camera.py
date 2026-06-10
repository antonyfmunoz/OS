"""Camera adapter — webcam capture and PTZ control for Insta360 Link 2.

Uses OpenCV for frame capture and duvc-ctl for hardware pan/tilt/zoom.
Supports preset positions (physically moves the gimbal), snapshot capture,
and low-FPS preview streaming via signal emission.
"""

from __future__ import annotations

import base64
import json
import logging
import sys
import threading
import time
from pathlib import Path
from typing import Any, Callable

logger = logging.getLogger(__name__)

_DEFAULT_PRESETS_PATH = (
    Path("C:\\ProgramData\\UMH\\camera_presets.json")
    if sys.platform == "win32"
    else Path.home() / ".umh" / "camera_presets.json"
)


class CameraAdapter:
    """Webcam capture + PTZ control via OpenCV and duvc-ctl."""

    def __init__(
        self,
        device_index: int = 0,
        presets_path: Path | None = None,
    ) -> None:
        self._device_index = device_index
        self._presets_path = presets_path or _DEFAULT_PRESETS_PATH
        self._presets: dict[str, dict[str, Any]] = {}
        self._load_presets()

        self._stream_active = False
        self._stream_thread: threading.Thread | None = None
        self._stream_lock = threading.Lock()
        self._frame_callback: Callable[[dict[str, Any]], None] | None = None

    def set_frame_callback(self, cb: Callable[[dict[str, Any]], None]) -> None:
        self._frame_callback = cb

    def execute(self, operation: str, params: dict[str, Any]) -> dict[str, Any]:
        ops = {
            "camera.snapshot": self._snapshot,
            "camera.stream_start": self._stream_start,
            "camera.stream_stop": self._stream_stop,
            "camera.list_devices": self._list_devices,
            "camera.set_preset": self._set_preset,
            "camera.save_preset": self._save_preset,
            "camera.list_presets": self._list_presets,
            "camera.get_position": self._get_position,
            "camera.set_position": self._set_position,
            "camera.status": self._status,
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

    # ── Frame capture ────────────────────────────────────────────────

    def _snapshot(self, params: dict[str, Any]) -> dict[str, Any]:
        import cv2

        width = params.get("width", 1280)
        height = params.get("height", 720)
        quality = params.get("quality", 75)
        device = params.get("device_index", self._device_index)

        cap = cv2.VideoCapture(device, cv2.CAP_DSHOW)
        if not cap.isOpened():
            return {"success": False, "error": "camera unavailable or in use by another application"}

        try:
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)

            for _ in range(5):
                ret, frame = cap.read()
                if ret:
                    break
            else:
                return {"success": False, "error": "failed to capture frame after 5 attempts"}

            encode_params = [cv2.IMWRITE_JPEG_QUALITY, quality]
            success, buf = cv2.imencode(".jpg", frame, encode_params)
            if not success:
                return {"success": False, "error": "JPEG encoding failed"}

            encoded = base64.b64encode(buf.tobytes()).decode("ascii")
            return {
                "success": True,
                "image_base64": encoded,
                "width": frame.shape[1],
                "height": frame.shape[0],
                "format": "jpeg",
                "quality": quality,
                "size_bytes": len(buf),
            }
        finally:
            cap.release()

    # ── Streaming ────────────────────────────────────────────────────

    def _stream_start(self, params: dict[str, Any]) -> dict[str, Any]:
        with self._stream_lock:
            if self._stream_active and self._stream_thread and self._stream_thread.is_alive():
                return {"success": True, "message": "stream already active"}
            self._stream_active = False
            if self._stream_thread and self._stream_thread.is_alive():
                self._stream_thread.join(timeout=3.0)

        fps = min(params.get("fps", 2), 30)
        width = params.get("width", 640)
        height = params.get("height", 480)
        quality = params.get("quality", 60)
        device = params.get("device_index", self._device_index)

        self._stream_active = True
        self._stream_thread = threading.Thread(
            target=self._stream_loop,
            args=(device, fps, width, height, quality),
            daemon=True,
            name="camera-stream",
        )
        self._stream_thread.start()
        logger.info("camera stream started: %dx%d @%dfps q%d", width, height, fps, quality)
        return {"success": True, "fps": fps, "width": width, "height": height, "quality": quality}

    def _stream_stop(self, params: dict[str, Any]) -> dict[str, Any]:
        self._stream_active = False
        if self._stream_thread:
            self._stream_thread.join(timeout=3.0)
            self._stream_thread = None
        logger.info("camera stream stopped")
        return {"success": True}

    def _stream_loop(
        self, device: int, fps: int, width: int, height: int, quality: int,
    ) -> None:
        import cv2

        interval = 1.0 / max(fps, 1)
        consecutive_failures = 0
        max_reconnect_attempts = 5
        cap = None

        def open_camera():
            nonlocal cap
            if cap is not None:
                try:
                    cap.release()
                except Exception:
                    pass
            cap = cv2.VideoCapture(device, cv2.CAP_DSHOW)
            if cap.isOpened():
                cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
                cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
                return True
            return False

        if not open_camera():
            logger.error("camera stream: device %d unavailable", device)
            self._stream_active = False
            return

        encode_params = [cv2.IMWRITE_JPEG_QUALITY, quality]

        try:
            while self._stream_active:
                t0 = time.monotonic()
                ret, frame = cap.read()
                if not ret:
                    consecutive_failures += 1
                    if consecutive_failures >= 10:
                        logger.warning("camera: %d consecutive read failures, reconnecting (attempt %d/%d)", consecutive_failures, min(consecutive_failures // 10, max_reconnect_attempts), max_reconnect_attempts)
                        if consecutive_failures // 10 > max_reconnect_attempts:
                            logger.error("camera: max reconnect attempts exceeded, stopping stream")
                            break
                        backoff = min(2.0 ** (consecutive_failures // 10 - 1), 10.0)
                        time.sleep(backoff)
                        if open_camera():
                            logger.info("camera: reconnected to device %d", device)
                            consecutive_failures = 0
                        continue
                    time.sleep(0.1)
                    continue

                consecutive_failures = 0
                success, buf = cv2.imencode(".jpg", frame, encode_params)
                if success and self._frame_callback:
                    encoded = base64.b64encode(buf.tobytes()).decode("ascii")
                    self._frame_callback({
                        "type": "camera_frame",
                        "image_base64": encoded,
                        "width": frame.shape[1],
                        "height": frame.shape[0],
                        "quality": quality,
                        "timestamp": time.time(),
                        "size_bytes": len(buf),
                    })

                elapsed = time.monotonic() - t0
                sleep_time = interval - elapsed
                if sleep_time > 0:
                    time.sleep(sleep_time)
        except Exception as exc:
            logger.error("camera stream error: %s", exc)
        finally:
            if cap is not None:
                try:
                    cap.release()
                except Exception:
                    pass
            self._stream_active = False

    # ── PTZ control (OpenCV UVC properties, duvc-ctl optional) ─────

    def _get_position(self, params: dict[str, Any]) -> dict[str, Any]:
        try:
            import duvc_ctl as duvc
            with duvc.CameraController() as cam:
                return {"success": True, "pan": cam.pan, "tilt": cam.tilt, "zoom": cam.zoom}
        except ImportError:
            pass
        except Exception as exc:
            logger.debug("duvc-ctl get_position failed: %s, falling back to OpenCV", exc)

        import cv2
        cap = cv2.VideoCapture(self._device_index, cv2.CAP_DSHOW)
        if not cap.isOpened():
            return {"success": False, "error": "camera unavailable"}
        try:
            return {
                "success": True,
                "pan": int(cap.get(cv2.CAP_PROP_PAN)),
                "tilt": int(cap.get(cv2.CAP_PROP_TILT)),
                "zoom": int(cap.get(cv2.CAP_PROP_ZOOM)),
            }
        finally:
            cap.release()

    def _set_position(self, params: dict[str, Any]) -> dict[str, Any]:
        pan = params.get("pan")
        tilt = params.get("tilt")
        zoom = params.get("zoom")

        try:
            import duvc_ctl as duvc
            with duvc.CameraController() as cam:
                if pan is not None:
                    cam.pan = int(pan)
                if tilt is not None:
                    cam.tilt = int(tilt)
                if zoom is not None:
                    cam.zoom = int(zoom)
                return {"success": True, "pan": cam.pan, "tilt": cam.tilt, "zoom": cam.zoom}
        except ImportError:
            pass
        except Exception as exc:
            logger.debug("duvc-ctl set_position failed: %s, falling back to OpenCV", exc)

        import cv2
        cap = cv2.VideoCapture(self._device_index, cv2.CAP_DSHOW)
        if not cap.isOpened():
            return {"success": False, "error": "camera unavailable"}
        try:
            if pan is not None:
                cap.set(cv2.CAP_PROP_PAN, int(pan))
            if tilt is not None:
                cap.set(cv2.CAP_PROP_TILT, int(tilt))
            if zoom is not None:
                cap.set(cv2.CAP_PROP_ZOOM, int(zoom))
            return {
                "success": True,
                "pan": int(cap.get(cv2.CAP_PROP_PAN)),
                "tilt": int(cap.get(cv2.CAP_PROP_TILT)),
                "zoom": int(cap.get(cv2.CAP_PROP_ZOOM)),
            }
        finally:
            cap.release()

    # ── Presets (stored PTZ positions) ───────────────────────────────

    def _load_presets(self) -> None:
        if self._presets_path.exists():
            try:
                self._presets = json.loads(self._presets_path.read_text())
            except Exception as exc:
                logger.warning("failed to load camera presets: %s", exc)
                self._presets = {}
        else:
            self._presets = _default_presets()

    def _save_presets_to_disk(self) -> None:
        try:
            self._presets_path.parent.mkdir(parents=True, exist_ok=True)
            self._presets_path.write_text(json.dumps(self._presets, indent=2))
        except Exception as exc:
            logger.warning("failed to save camera presets: %s", exc)

    def _list_presets(self, params: dict[str, Any]) -> dict[str, Any]:
        return {
            "success": True,
            "presets": {
                name: {
                    "label": p.get("label", name),
                    "pan": p.get("pan"),
                    "tilt": p.get("tilt"),
                    "zoom": p.get("zoom"),
                    "analysis_hint": p.get("analysis_hint", ""),
                }
                for name, p in self._presets.items()
            },
        }

    def _set_preset(self, params: dict[str, Any]) -> dict[str, Any]:
        name = params.get("preset", "")
        if name not in self._presets:
            return {
                "success": False,
                "error": f"unknown preset: {name}",
                "available": list(self._presets.keys()),
            }

        preset = self._presets[name]
        result = self._set_position({
            "pan": preset.get("pan"),
            "tilt": preset.get("tilt"),
            "zoom": preset.get("zoom"),
        })
        if result["success"]:
            result["preset"] = name
            result["label"] = preset.get("label", name)
            result["analysis_hint"] = preset.get("analysis_hint", "")
        return result

    def _save_preset(self, params: dict[str, Any]) -> dict[str, Any]:
        name = params.get("preset", "")
        label = params.get("label", name)
        analysis_hint = params.get("analysis_hint", "")

        if not name:
            return {"success": False, "error": "preset name required"}

        pos = self._get_position({})
        if not pos["success"]:
            return pos

        self._presets[name] = {
            "label": label,
            "pan": pos["pan"],
            "tilt": pos["tilt"],
            "zoom": pos["zoom"],
            "analysis_hint": analysis_hint,
        }
        self._save_presets_to_disk()
        logger.info("saved preset '%s': pan=%s tilt=%s zoom=%s", name, pos["pan"], pos["tilt"], pos["zoom"])
        return {
            "success": True,
            "preset": name,
            "pan": pos["pan"],
            "tilt": pos["tilt"],
            "zoom": pos["zoom"],
        }

    # ── Device enumeration ───────────────────────────────────────────

    def _list_devices(self, params: dict[str, Any]) -> dict[str, Any]:
        import cv2

        devices = []
        for i in range(5):
            cap = cv2.VideoCapture(i, cv2.CAP_DSHOW)
            if cap.isOpened():
                w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                devices.append({"index": i, "width": w, "height": h})
                cap.release()
        return {"success": True, "devices": devices}

    # ── Status ───────────────────────────────────────────────────────

    def _status(self, params: dict[str, Any]) -> dict[str, Any]:
        return {
            "success": True,
            "streaming": self._stream_active,
            "device_index": self._device_index,
            "presets_loaded": len(self._presets),
        }


def _default_presets() -> dict[str, dict[str, Any]]:
    return {
        "operator": {
            "label": "Look at me",
            "pan": 0,
            "tilt": 0,
            "zoom": 100,
            "analysis_hint": "operator face, posture, presence",
        },
        "keyboard": {
            "label": "Look at my keyboard",
            "pan": 0,
            "tilt": -45,
            "zoom": 150,
            "analysis_hint": "hands, keyboard, desk interaction",
        },
        "desk": {
            "label": "Look at the desk",
            "pan": 0,
            "tilt": -30,
            "zoom": 120,
            "analysis_hint": "desk objects, workspace state",
        },
        "room": {
            "label": "Watch the room",
            "pan": 0,
            "tilt": 0,
            "zoom": 100,
            "analysis_hint": "general room awareness",
        },
    }
