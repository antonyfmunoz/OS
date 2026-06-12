"""Camera adapter — webcam capture and PTZ control for Insta360 Link 2.

Uses OpenCV for frame capture and duvc-ctl for hardware pan/tilt/zoom.
Supports preset positions (physically moves the gimbal), snapshot capture,
and low-FPS preview streaming via signal emission.
"""

from __future__ import annotations

import base64
import json
import logging
import queue
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
        self._presets_path = presets_path or _DEFAULT_PRESETS_PATH
        self._presets: dict[str, dict[str, Any]] = {}
        self._load_presets()

        saved_device = self._load_device_preference()
        self._device_index = saved_device if saved_device is not None else device_index

        self._stream_active = False
        self._stream_thread: threading.Thread | None = None
        self._stream_lock = threading.Lock()
        self._frame_callback: Callable[[dict[str, Any]], None] | None = None

        self._ptz_queue: queue.Queue[tuple[dict[str, Any], threading.Event, list]] = queue.Queue()

        self._detector = None
        self._detect_min_interval = 0.5
        self._detect_last_at = 0.0
        self._detection_enabled = True
        self._init_detector()

    def _init_detector(self) -> None:
        try:
            from nodes.windows.umh_node.adapters.object_detector import ObjectDetector
            self._detector = ObjectDetector(confidence_threshold=0.35)
            loaded = self._detector.load_model()
            if loaded:
                logger.info("object detector ready (YOLOv8n)")
            else:
                logger.warning("object detector not loaded: %s", self._detector.load_error)
        except Exception as exc:
            logger.warning("object detector init failed: %s", exc)
            self._detector = None

    def get_detector_status(self) -> dict[str, Any]:
        if self._detector is None:
            return {"loaded": False, "model": "none", "load_error": "detector not initialized"}
        return self._detector.get_status()

    def set_frame_callback(self, cb: Callable[[dict[str, Any]], None]) -> None:
        self._frame_callback = cb

    def execute(self, operation: str, params: dict[str, Any]) -> dict[str, Any]:
        ops = {
            "camera.snapshot": self._snapshot,
            "camera.stream_start": self._stream_start,
            "camera.stream_stop": self._stream_stop,
            "camera.list_devices": self._list_devices,
            "camera.select_device": self._select_device,
            "camera.set_preset": self._set_preset,
            "camera.save_preset": self._save_preset,
            "camera.list_presets": self._list_presets,
            "camera.get_position": self._get_position,
            "camera.set_position": self._set_position,
            "camera.set_position_relative": self._set_position_relative,
            "camera.status": self._status,
            "camera.detector_status": self._detector_status,
            "camera.scene_describe": self._scene_describe,
            "camera.track_query": self._track_query,
            "camera.active_tracks": self._active_tracks,
            "camera.delete_preset": self._delete_preset,
            "camera.correct_label": self._correct_label,
            "camera.label_corrections": self._label_corrections_list,
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

    def _process_ptz_queue(self, cap: Any) -> None:
        """Drain queued PTZ commands — called from stream thread only."""
        import cv2
        while not self._ptz_queue.empty():
            try:
                ptz_params, done_event, result_slot = self._ptz_queue.get_nowait()
            except queue.Empty:
                break
            try:
                pan = ptz_params.get("pan")
                tilt = ptz_params.get("tilt")
                zoom = ptz_params.get("zoom")
                props = []
                if pan is not None:
                    props.append((cv2.CAP_PROP_PAN, int(pan)))
                if tilt is not None:
                    props.append((cv2.CAP_PROP_TILT, int(tilt)))
                if zoom is not None:
                    props.append((cv2.CAP_PROP_ZOOM, int(zoom)))
                for prop_id, val in props:
                    cap.set(prop_id, val)
                    cap.read()
                result_slot.append({
                    "success": True,
                    "pan": int(cap.get(cv2.CAP_PROP_PAN)),
                    "tilt": int(cap.get(cv2.CAP_PROP_TILT)),
                    "zoom": int(cap.get(cv2.CAP_PROP_ZOOM)),
                })
            except Exception as exc:
                result_slot.append({"success": False, "error": str(exc)})
            finally:
                done_event.set()

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
        frame_n = 0

        try:
            while self._stream_active:
                self._process_ptz_queue(cap)

                t0 = time.monotonic()
                frame_n += 1
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
                    payload: dict[str, Any] = {
                        "type": "camera_frame",
                        "image_base64": encoded,
                        "width": frame.shape[1],
                        "height": frame.shape[0],
                        "quality": quality,
                        "timestamp": time.time(),
                        "size_bytes": len(buf),
                    }

                    now_mono = time.monotonic()
                    detect_due = (now_mono - self._detect_last_at) >= self._detect_min_interval
                    if (self._detection_enabled
                            and self._detector is not None
                            and self._detector.loaded
                            and detect_due):
                        try:
                            detections = self._detector.detect(frame)
                            infer_ms = self._detector._last_inference_ms
                            self._detect_last_at = time.monotonic()
                            if infer_ms > 400:
                                self._detect_min_interval = min(self._detect_min_interval * 1.5, 5.0)
                                logger.info("detection backpressure: inference %.0fms, interval now %.2fs", infer_ms, self._detect_min_interval)
                            elif infer_ms < 150 and self._detect_min_interval > 0.5:
                                self._detect_min_interval = max(self._detect_min_interval * 0.8, 0.5)
                            if frame_n % 45 == 0:
                                logger.info("detection frame %d: %d objects, %.0fms, interval %.2fs", frame_n, len(detections), infer_ms, self._detect_min_interval)
                            det_status = self._detector.get_status()
                            payload["detector_status"] = {
                                "source": "beast",
                                "host": "windows-desktop",
                                "model": det_status["model"],
                                "loaded": det_status["loaded"],
                                "device": det_status.get("device", "cpu"),
                                "inference_ms": det_status["last_inference_ms"],
                                "avg_inference_ms": det_status["avg_inference_ms"],
                                "detection_frames": det_status["frame_count"],
                                "detect_interval": self._detect_min_interval,
                                "tracker_active": det_status.get("tracker_active", False),
                                "active_tracks": det_status.get("active_tracks", 0),
                            }
                            if detections:
                                payload["overlays"] = [
                                    {
                                        "track_id": str(d.get("track_id", d.get("id", f"det_{frame_n}_{i}"))),
                                        "label": d["label"],
                                        "confidence": d["confidence"],
                                        "x": d["bbox"]["x"],
                                        "y": d["bbox"]["y"],
                                        "w": d["bbox"]["w"],
                                        "h": d["bbox"]["h"],
                                        "source": "real",
                                        "model": d.get("model", "yolov8n"),
                                        "age_frames": d.get("age_frames", 0),
                                        "lost_frames": d.get("lost_frames", 0),
                                        "status": d.get("status", "active"),
                                        "velocity": d.get("velocity", [0, 0]),
                                    }
                                    for i, d in enumerate(detections)
                                ]
                        except Exception as exc:
                            if frame_n % 45 == 0:
                                logger.warning("detection error frame %d: %s", frame_n, exc)

                    self._frame_callback(payload)

                elapsed = time.monotonic() - t0
                sleep_time = interval - elapsed
                if sleep_time > 0:
                    time.sleep(sleep_time)
        except Exception as exc:
            logger.error("camera stream error: %s", exc)
        finally:
            while not self._ptz_queue.empty():
                try:
                    _, done_event, result_slot = self._ptz_queue.get_nowait()
                    result_slot.append({"success": False, "error": "stream stopped"})
                    done_event.set()
                except queue.Empty:
                    break
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

        if self._stream_active:
            result_slot: list[dict[str, Any]] = []
            done = threading.Event()
            self._ptz_queue.put(({}, done, result_slot))
            if done.wait(timeout=5.0) and result_slot:
                return result_slot[0]
            return {"success": False, "error": "PTZ read timed out"}

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

        if self._stream_active:
            result_slot: list[dict[str, Any]] = []
            done = threading.Event()
            ptz_params = {}
            if pan is not None:
                ptz_params["pan"] = pan
            if tilt is not None:
                ptz_params["tilt"] = tilt
            if zoom is not None:
                ptz_params["zoom"] = zoom
            self._ptz_queue.put((ptz_params, done, result_slot))
            if done.wait(timeout=10.0) and result_slot:
                return result_slot[0]
            return {"success": False, "error": "PTZ command timed out"}

        import cv2
        cap = cv2.VideoCapture(self._device_index, cv2.CAP_DSHOW)
        if not cap.isOpened():
            return {"success": False, "error": "camera unavailable"}
        try:
            props = []
            if pan is not None:
                props.append((cv2.CAP_PROP_PAN, int(pan)))
            if tilt is not None:
                props.append((cv2.CAP_PROP_TILT, int(tilt)))
            if zoom is not None:
                props.append((cv2.CAP_PROP_ZOOM, int(zoom)))
            for prop_id, val in props:
                cap.set(prop_id, val)
                cap.read()
            return {
                "success": True,
                "pan": int(cap.get(cv2.CAP_PROP_PAN)),
                "tilt": int(cap.get(cv2.CAP_PROP_TILT)),
                "zoom": int(cap.get(cv2.CAP_PROP_ZOOM)),
            }
        finally:
            cap.release()

    def _set_position_relative(self, params: dict[str, Any]) -> dict[str, Any]:
        """Apply relative pan/tilt/zoom deltas to current position."""
        pos = self._get_position({})
        if not pos["success"]:
            return pos
        new_pan = pos["pan"] + params.get("pan_delta", 0)
        new_tilt = pos["tilt"] + params.get("tilt_delta", 0)
        new_zoom = max(100, pos["zoom"] + params.get("zoom_delta", 0))
        return self._set_position({"pan": new_pan, "tilt": new_tilt, "zoom": new_zoom})

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
        preset_device = preset.get("device_id")
        device_mismatch = preset_device is not None and preset_device != self._device_index

        result = self._set_position({
            "pan": preset.get("pan"),
            "tilt": preset.get("tilt"),
            "zoom": preset.get("zoom"),
        })
        if result["success"]:
            result["preset"] = name
            result["label"] = preset.get("label", name)
            result["analysis_hint"] = preset.get("analysis_hint", "")
            if device_mismatch:
                result["device_mismatch"] = True
                result["preset_device_id"] = preset_device
                result["current_device_id"] = self._device_index
                logger.warning(
                    "preset '%s' was saved on device %s but current device is %s",
                    name, preset_device, self._device_index,
                )
        return result

    def _save_preset(self, params: dict[str, Any]) -> dict[str, Any]:
        name = params.get("preset", "")
        label = params.get("label", name)
        analysis_hint = params.get("analysis_hint", "")
        mode = params.get("mode", "physical_ptz")
        roi = params.get("roi")

        if not name:
            return {"success": False, "error": "preset name required"}

        if params.get("pan") is not None and params.get("tilt") is not None:
            pan = int(params["pan"])
            tilt = int(params["tilt"])
            zoom = int(params.get("zoom", 100))
        else:
            pos = self._get_position({})
            if not pos["success"]:
                return pos
            pan = pos["pan"]
            tilt = pos["tilt"]
            zoom = pos["zoom"]

        existing = self._presets.get(name, {})
        now_ms = int(time.time() * 1000)
        preset_data: dict[str, Any] = {
            "id": existing.get("id", name),
            "label": label,
            "pan": pan,
            "tilt": tilt,
            "zoom": zoom,
            "mode": mode,
            "device_id": self._device_index,
            "analysis_hint": analysis_hint,
            "created_at": existing.get("created_at", now_ms),
            "updated_at": now_ms,
        }
        if roi and isinstance(roi, dict):
            preset_data["roi"] = roi

        self._presets[name] = preset_data
        self._save_presets_to_disk()
        logger.info("saved preset '%s': pan=%s tilt=%s zoom=%s device=%s", name, pan, tilt, zoom, self._device_index)
        return {
            "success": True,
            "preset": name,
            "pan": pan,
            "tilt": tilt,
            "zoom": zoom,
            "device_id": self._device_index,
        }

    # ── Device enumeration ───────────────────────────────────────────

    def _get_wmi_device_names(self) -> dict[int, str]:
        """Get webcam/camera device names via Windows WMI. Returns {index: name}.

        Only returns PNPClass 'Camera' — excludes 'Image' (printers/scanners).
        """
        names: dict[int, str] = {}
        if sys.platform != "win32":
            return names
        try:
            import subprocess
            result = subprocess.run(
                ["powershell", "-NoProfile", "-Command",
                 "Get-CimInstance Win32_PnPEntity | Where-Object { $_.PNPClass -eq 'Camera' } | Select-Object -ExpandProperty Name"],
                capture_output=True, text=True, timeout=5,
            )
            if result.returncode == 0:
                for idx, line in enumerate(result.stdout.strip().splitlines()):
                    name = line.strip()
                    if name:
                        names[idx] = name
        except Exception as exc:
            logger.debug("WMI device name lookup failed: %s", exc)
        return names

    def _list_devices(self, params: dict[str, Any]) -> dict[str, Any]:
        import cv2
        import concurrent.futures

        wmi_names = self._get_wmi_device_names()
        logger.info("list_devices: stream_active=%s, wmi_names=%s, device_index=%s",
                     self._stream_active, wmi_names, self._device_index)
        devices = []

        if self._stream_active:
            # Active device — get resolution from running capture
            cap_ref = getattr(self, '_cap', None)
            w = int(cap_ref.get(cv2.CAP_PROP_FRAME_WIDTH)) if cap_ref else 0
            h = int(cap_ref.get(cv2.CAP_PROP_FRAME_HEIGHT)) if cap_ref else 0
            devices.append({
                "index": self._device_index,
                "name": wmi_names.get(self._device_index, f"Camera {self._device_index}"),
                "width": w,
                "height": h,
                "online": True,
                "busy": True,
                "selected": True,
            })
            # WMI-only for other devices — DirectShow hangs when a capture is active
            for idx, name in wmi_names.items():
                if idx != self._device_index:
                    devices.append({
                        "index": idx,
                        "name": name,
                        "width": 0,
                        "height": 0,
                        "online": True,
                        "busy": False,
                        "selected": False,
                    })
            devices.sort(key=lambda d: d["index"])
            return {
                "success": True,
                "devices": devices,
                "selected_index": self._device_index,
            }

        # No active stream — safe to probe with cv2.VideoCapture
        def probe_index(i: int) -> dict[str, Any] | None:
            try:
                cap = cv2.VideoCapture(i, cv2.CAP_DSHOW)
                if cap.isOpened():
                    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                    cap.release()
                    return {
                        "index": i,
                        "name": wmi_names.get(i, f"Camera {i}"),
                        "width": w,
                        "height": h,
                        "online": True,
                        "busy": False,
                        "selected": False,
                    }
                cap.release()
            except Exception:
                pass
            return None

        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
            futures = {pool.submit(probe_index, i): i for i in range(8)}
            for fut in concurrent.futures.as_completed(futures, timeout=6):
                try:
                    result = fut.result(timeout=3)
                    if result:
                        devices.append(result)
                except Exception:
                    pass

        devices.sort(key=lambda d: d["index"])
        return {
            "success": True,
            "devices": devices,
            "selected_index": self._device_index,
        }

    def _select_device(self, params: dict[str, Any]) -> dict[str, Any]:
        """Select camera device by index. Restarts stream if active."""
        new_index = params.get("device_index")
        if new_index is None:
            return {"success": False, "error": "device_index required"}
        new_index = int(new_index)

        import cv2
        cap = cv2.VideoCapture(new_index, cv2.CAP_DSHOW)
        if not cap.isOpened():
            return {"success": False, "error": f"device {new_index} unavailable or in use"}
        cap.release()

        old_index = self._device_index
        self._device_index = new_index
        self._save_device_preference()
        logger.info("camera device changed: %d -> %d", old_index, new_index)

        if self._stream_active:
            logger.info("restarting stream on new device %d", new_index)
            self._stream_active = False
            if self._stream_thread and self._stream_thread.is_alive():
                self._stream_thread.join(timeout=3.0)
            self._stream_start({
                "device_index": new_index,
                "fps": 2, "width": 640, "height": 480, "quality": 60,
            })

        return {"success": True, "device_index": new_index, "restarted_stream": self._stream_active}

    def _save_device_preference(self) -> None:
        pref_path = self._presets_path.parent / "device_preference.json"
        try:
            pref_path.parent.mkdir(parents=True, exist_ok=True)
            pref_path.write_text(json.dumps({"device_index": self._device_index}))
        except Exception as exc:
            logger.warning("failed to save device preference: %s", exc)

    def _load_device_preference(self) -> int | None:
        pref_path = self._presets_path.parent / "device_preference.json"
        try:
            if pref_path.exists():
                data = json.loads(pref_path.read_text())
                return data.get("device_index")
        except Exception as exc:
            logger.debug("device preference load failed: %s", exc)
        return None

    # ── Status ───────────────────────────────────────────────────────

    def _status(self, params: dict[str, Any]) -> dict[str, Any]:
        det = self.get_detector_status()
        return {
            "success": True,
            "streaming": self._stream_active,
            "device_index": self._device_index,
            "presets_loaded": len(self._presets),
            "detector": det,
            "detect_interval": round(self._detect_min_interval, 2),
        }

    def _detector_status(self, params: dict[str, Any]) -> dict[str, Any]:
        return {"success": True, **self.get_detector_status()}

    def _scene_describe(self, params: dict[str, Any]) -> dict[str, Any]:
        if self._detector is None:
            return {"success": False, "error": "detector not initialized"}
        return {"success": True, "description": self._detector.get_scene_description()}

    def _track_query(self, params: dict[str, Any]) -> dict[str, Any]:
        if self._detector is None:
            return {"success": False, "error": "detector not initialized"}
        label = params.get("label", "")
        if not label:
            return {"success": False, "error": "label required"}
        track = self._detector.get_track_by_label(label)
        if track:
            return {"success": True, "track": track}
        return {"success": False, "error": f"no active track for '{label}'"}

    def _active_tracks(self, params: dict[str, Any]) -> dict[str, Any]:
        if self._detector is None:
            return {"success": False, "error": "detector not initialized"}
        return {"success": True, "tracks": self._detector.get_active_tracks()}

    def _delete_preset(self, params: dict[str, Any]) -> dict[str, Any]:
        name = params.get("preset", "")
        if not name:
            return {"success": False, "error": "preset name required"}
        if name not in self._presets:
            return {"success": False, "error": f"unknown preset: {name}"}
        del self._presets[name]
        self._save_presets_to_disk()
        logger.info("deleted preset '%s'", name)
        return {"success": True, "preset": name}

    def _correct_label(self, params: dict[str, Any]) -> dict[str, Any]:
        track_id = params.get("track_id", "")
        corrected = params.get("corrected_label", "")
        if not track_id or not corrected:
            return {"success": False, "error": "track_id and corrected_label required"}
        if self._detector is None:
            return {"success": False, "error": "detector not initialized"}
        self._detector.correct_label(str(track_id), corrected)
        logger.info("label correction: track %s → '%s'", track_id, corrected)
        return {"success": True, "track_id": track_id, "corrected_label": corrected}

    def _label_corrections_list(self, params: dict[str, Any]) -> dict[str, Any]:
        if self._detector is None:
            return {"success": False, "error": "detector not initialized"}
        return {"success": True, "corrections": self._detector.get_label_corrections()}


def _default_presets() -> dict[str, dict[str, Any]]:
    return {
        "home": {
            "label": "Home",
            "pan": 0,
            "tilt": 0,
            "zoom": 100,
            "mode": "physical_ptz",
            "analysis_hint": "operator face, posture, presence",
        },
        "keyboard": {
            "label": "Keyboard",
            "pan": 0,
            "tilt": -45,
            "zoom": 150,
            "mode": "physical_ptz",
            "analysis_hint": "hands, keyboard, desk interaction",
        },
        "monitor": {
            "label": "Monitor",
            "pan": 0,
            "tilt": 0,
            "zoom": 130,
            "mode": "physical_ptz",
            "analysis_hint": "screen content, monitor state",
        },
        "desk": {
            "label": "Desk",
            "pan": 0,
            "tilt": -30,
            "zoom": 120,
            "mode": "physical_ptz",
            "analysis_hint": "desk objects, workspace state",
        },
    }
