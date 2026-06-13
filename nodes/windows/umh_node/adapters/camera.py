"""Camera adapter — webcam capture and PTZ control for Insta360 Link 2.

Uses OpenCV for frame capture and duvc-ctl for hardware pan/tilt/zoom.
Supports preset positions (physically moves the gimbal), snapshot capture,
and streaming with decoupled perception pipeline.
"""

from __future__ import annotations

import base64
import copy
import json
import logging
import queue
import sys
import threading
import time
from pathlib import Path
from typing import Any, Callable

logger = logging.getLogger(__name__)

# ── Camera profiles ──────────────────────────────────────────────
# Each profile specifies capture resolution, FPS target, and JPEG quality.
# The actual negotiated values depend on hardware capability.

CAMERA_PROFILES: dict[str, dict[str, Any]] = {
    "smooth":   {"width": 1280, "height": 720,  "fps": 30, "quality": 55, "label": "720p30 Smooth"},
    "balanced": {"width": 1280, "height": 720,  "fps": 30, "quality": 70, "label": "720p30 Balanced"},
    "high":     {"width": 1920, "height": 1080, "fps": 30, "quality": 80, "label": "1080p30 High"},
    "perf":     {"width": 1920, "height": 1080, "fps": 60, "quality": 65, "label": "1080p60 Performance"},
    "quality":  {"width": 3840, "height": 2160, "fps": 15, "quality": 85, "label": "4K15 Quality"},
    "analysis": {"width": 1920, "height": 1080, "fps": 5,  "quality": 95, "label": "1080p5 Analysis"},
}

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
        self._device_name: str | None = None

        self._stream_active = False
        self._stream_thread: threading.Thread | None = None
        self._stream_lock = threading.Lock()
        self._frame_callback: Callable[[dict[str, Any]], None] | None = None

        self._ptz_queue: queue.Queue[tuple[dict[str, Any], threading.Event, list]] = queue.Queue()

        # Decoupled detector — runs on its own thread, never blocks preview
        self._detector = None
        self._detect_min_interval = 0.5
        self._detect_last_at = 0.0
        self._detection_enabled = True
        self._detect_error_count = 0
        self._detect_error_last_log = 0.0
        self._detect_thread: threading.Thread | None = None
        self._detect_frame: Any = None
        self._detect_frame_lock = threading.Lock()
        self._detect_results: dict[str, Any] = {}
        self._detect_results_lock = threading.Lock()

        # Stream metrics
        self._stream_frame_count = 0
        self._stream_dropped = 0
        self._stream_profile = "balanced"
        self._negotiated_width = 0
        self._negotiated_height = 0
        self._negotiated_fps = 0.0
        self._measured_fps_window: list[float] = []
        self._stream_bytes_total = 0

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
            "camera.capabilities": self._query_capabilities,
            "camera.set_profile": self._set_profile,
            "camera.stream_metrics": self._stream_metrics,
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

            encode_params = [int(cv2.IMWRITE_JPEG_QUALITY), int(quality)]
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

        profile_name = params.get("profile", "")
        if profile_name and profile_name in CAMERA_PROFILES:
            profile = CAMERA_PROFILES[profile_name]
            fps = min(params.get("fps", profile["fps"]), 60)
            width = params.get("width", profile["width"])
            height = params.get("height", profile["height"])
            quality = params.get("quality", profile["quality"])
            self._stream_profile = profile_name
        else:
            fps = min(params.get("fps", 30), 60)
            width = params.get("width", 1280)
            height = params.get("height", 720)
            quality = params.get("quality", 70)
            self._stream_profile = "balanced"

        device = params.get("device_index", self._device_index)
        self._stream_frame_count = 0
        self._stream_dropped = 0
        self._stream_bytes_total = 0
        self._measured_fps_window = []

        self._stream_active = True
        self._stream_thread = threading.Thread(
            target=self._stream_loop,
            args=(device, fps, width, height, quality),
            daemon=True,
            name="camera-stream",
        )
        self._stream_thread.start()

        # Start decoupled detector thread
        if self._detection_enabled and self._detector is not None:
            self._start_detect_thread()

        logger.info("camera stream started: %dx%d @%dfps q%d profile=%s", width, height, fps, quality, self._stream_profile)
        return {"success": True, "fps": fps, "width": width, "height": height, "quality": quality, "profile": self._stream_profile}

    def _stream_stop(self, params: dict[str, Any]) -> dict[str, Any]:
        self._stream_active = False
        if self._detect_thread and self._detect_thread.is_alive():
            self._detect_thread.join(timeout=3.0)
            self._detect_thread = None
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

    def _start_detect_thread(self) -> None:
        """Launch detector on its own thread — preview never waits on inference."""
        if self._detect_thread and self._detect_thread.is_alive():
            return
        self._detect_thread = threading.Thread(
            target=self._detect_loop,
            daemon=True,
            name="camera-detect",
        )
        self._detect_thread.start()
        logger.info("detector thread started (decoupled from preview)")

    def _detect_loop(self) -> None:
        """Continuously runs YOLO on the latest frame, independent of preview cadence."""
        while self._stream_active:
            with self._detect_frame_lock:
                frame = self._detect_frame
            if frame is None:
                time.sleep(0.05)
                continue

            now_mono = time.monotonic()
            if (now_mono - self._detect_last_at) < self._detect_min_interval:
                time.sleep(0.02)
                continue

            if self._detector is None or not self._detector.loaded:
                time.sleep(0.5)
                continue

            try:
                detections = self._detector.detect(frame)
                infer_ms = self._detector._last_inference_ms
                self._detect_last_at = time.monotonic()

                if infer_ms > 400:
                    self._detect_min_interval = min(self._detect_min_interval * 1.5, 5.0)
                elif infer_ms < 150 and self._detect_min_interval > 0.5:
                    self._detect_min_interval = max(self._detect_min_interval * 0.8, 0.5)

                det_status = self._detector.get_status()
                results: dict[str, Any] = {
                    "detector_status": {
                        "source": "beast",
                        "host": "windows-desktop",
                        "model": det_status["model"],
                        "loaded": det_status["loaded"],
                        "device": det_status.get("device", "cpu"),
                        "nms_device": det_status.get("nms_device", "cpu"),
                        "nms_fallback": det_status.get("nms_fallback", False),
                        "inference_ms": det_status["last_inference_ms"],
                        "avg_inference_ms": det_status["avg_inference_ms"],
                        "detection_frames": det_status["frame_count"],
                        "detect_interval": self._detect_min_interval,
                        "tracker_active": det_status.get("tracker_active", False),
                        "active_tracks": det_status.get("active_tracks", 0),
                        "total_tracks": det_status.get("total_tracks", 0),
                        "consecutive_errors": det_status.get("consecutive_errors", 0),
                    },
                    "timestamp": time.time(),
                }
                if detections:
                    results["overlays"] = [
                        {
                            "track_id": str(d.get("track_id", d.get("id", f"det_{i}"))),
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
                            "first_seen": d.get("first_seen", 0),
                            "last_seen": d.get("last_seen", 0),
                        }
                        for i, d in enumerate(detections)
                    ]
                with self._detect_results_lock:
                    self._detect_results = results
            except Exception as exc:
                self._detect_error_count += 1
                now_err = time.monotonic()
                if now_err - self._detect_error_last_log >= 30.0:
                    logger.warning(
                        "detection error (count=%d): %s",
                        self._detect_error_count, type(exc).__name__,
                    )
                    self._detect_error_last_log = now_err
                time.sleep(0.1)

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
                if fps >= 30:
                    cap.set(cv2.CAP_PROP_FPS, fps)
                return True
            return False

        if not open_camera():
            logger.error("camera stream: device %d unavailable", device)
            self._stream_active = False
            return

        actual_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        actual_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        actual_fps = cap.get(cv2.CAP_PROP_FPS) or fps
        self._negotiated_width = actual_w
        self._negotiated_height = actual_h
        self._negotiated_fps = actual_fps
        logger.info("negotiated: %dx%d @%.1ffps (requested %dx%d @%d)", actual_w, actual_h, actual_fps, width, height, fps)

        encode_params = [int(cv2.IMWRITE_JPEG_QUALITY), int(quality)]
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
                    frame_bytes = buf.tobytes()
                    encoded = base64.b64encode(frame_bytes).decode("ascii")
                    self._stream_frame_count += 1
                    self._stream_bytes_total += len(frame_bytes)

                    # Track measured FPS
                    now_mono_fps = time.monotonic()
                    self._measured_fps_window.append(now_mono_fps)
                    cutoff = now_mono_fps - 2.0
                    self._measured_fps_window = [t for t in self._measured_fps_window if t >= cutoff]

                    payload: dict[str, Any] = {
                        "type": "camera_frame",
                        "image_base64": encoded,
                        "width": frame.shape[1],
                        "height": frame.shape[0],
                        "quality": quality,
                        "timestamp": time.time(),
                        "size_bytes": len(frame_bytes),
                        "capture_timestamp": time.time(),
                        "profile": self._stream_profile,
                        "frame_seq": self._stream_frame_count,
                    }

                    # Feed frame to detector thread (non-blocking)
                    with self._detect_frame_lock:
                        self._detect_frame = frame.copy()

                    # Attach latest detection results (never blocks preview)
                    with self._detect_results_lock:
                        det = self._detect_results
                    if det:
                        if "detector_status" in det:
                            payload["detector_status"] = det["detector_status"]
                        if "overlays" in det:
                            payload["overlays"] = det["overlays"]

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
        # duvc_ctl opens USB device — deadlocks when stream holds it via OpenCV
        if not self._stream_active:
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
            if done.wait(timeout=2.0) and result_slot:
                return result_slot[0]
            logger.warning("PTZ read timed out (stream_active=%s, queue_size=%d)", self._stream_active, self._ptz_queue.qsize())
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

        # duvc_ctl opens USB device — deadlocks when stream holds it via OpenCV
        if not self._stream_active:
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
            if done.wait(timeout=3.0) and result_slot:
                return result_slot[0]
            logger.warning("PTZ set timed out (stream_active=%s, queue_size=%d)", self._stream_active, self._ptz_queue.qsize())
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

    def _resolve_device_name(self, wmi_cameras: list[dict[str, str]]) -> str:
        """Best-effort name for the active DirectShow index using WMI data."""
        if len(wmi_cameras) == 1:
            return wmi_cameras[0]["name"]
        if self._device_index < len(wmi_cameras):
            return wmi_cameras[self._device_index]["name"]
        return f"Camera {self._device_index}"

    def _get_wmi_cameras(self) -> list[dict[str, str]]:
        """Get physical camera devices via WMI with name and DeviceID for dedup.

        Only returns PNPClass 'Camera'. Each entry has 'name' and 'device_id'.
        """
        cameras: list[dict[str, str]] = []
        if sys.platform != "win32":
            return cameras
        try:
            import subprocess
            result = subprocess.run(
                ["powershell", "-NoProfile", "-Command",
                 "Get-CimInstance Win32_PnPEntity | Where-Object { $_.PNPClass -eq 'Camera' } "
                 "| Select-Object Name, DeviceID | ConvertTo-Json -Compress"],
                capture_output=True, text=True, timeout=5,
            )
            if result.returncode == 0 and result.stdout.strip():
                data = json.loads(result.stdout.strip())
                if isinstance(data, dict):
                    data = [data]
                for entry in data:
                    name = entry.get("Name", "").strip()
                    device_id = entry.get("DeviceID", "").strip()
                    if name:
                        cameras.append({"name": name, "device_id": device_id})
        except Exception as exc:
            logger.debug("WMI camera lookup failed: %s", exc)
        return cameras

    def _build_physical_device_map(
        self, wmi_cameras: list[dict[str, str]], probed: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Merge WMI physical cameras with DirectShow probe results.

        Groups duplicate DirectShow indexes under one physical device.
        Returns one entry per physical camera, not per endpoint.
        """
        seen_names: dict[str, dict[str, Any]] = {}
        wmi_name_set = {c["name"] for c in wmi_cameras}

        for dev in probed:
            name = dev["name"]
            if name in seen_names:
                seen_names[name]["raw_indexes"].append(dev["index"])
                if dev["width"] > seen_names[name]["width"]:
                    seen_names[name]["width"] = dev["width"]
                    seen_names[name]["height"] = dev["height"]
                    seen_names[name]["index"] = dev["index"]
            else:
                dev["raw_indexes"] = [dev["index"]]
                seen_names[name] = dev

        # Only return devices whose name matches a WMI physical camera
        # (eliminates virtual/phantom DirectShow endpoints with no physical device)
        result = []
        for dev in seen_names.values():
            if dev["name"] in wmi_name_set or not wmi_name_set:
                result.append(dev)

        result.sort(key=lambda d: d["index"])
        return result

    def _validate_device(self, index: int) -> dict[str, Any]:
        """Validate a device produces real frames. Returns status info."""
        import cv2
        try:
            cap = cv2.VideoCapture(index, cv2.CAP_DSHOW)
            if not cap.isOpened():
                return {"status": "unavailable", "error": "could not open device"}
            try:
                cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
                cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
                w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

                ret, frame1 = cap.read()
                if not ret or frame1 is None:
                    return {"status": "error", "error": "no frames", "width": w, "height": h}

                ret2, frame2 = cap.read()
                frames_advance = ret2 and frame2 is not None
                fps_est = 0.0
                if frames_advance:
                    t0 = time.monotonic()
                    read_count = 0
                    while time.monotonic() - t0 < 0.5:
                        r, _ = cap.read()
                        if r:
                            read_count += 1
                    elapsed = time.monotonic() - t0
                    if elapsed > 0:
                        fps_est = round(read_count / elapsed, 1)

                return {
                    "status": "usable" if frames_advance else "stale",
                    "width": w,
                    "height": h,
                    "fps": fps_est,
                    "error": None if frames_advance else "frames do not advance",
                }
            finally:
                cap.release()
        except Exception as exc:
            return {"status": "error", "error": str(exc)}

    def _list_devices(self, params: dict[str, Any]) -> dict[str, Any]:
        import cv2
        import concurrent.futures

        wmi_cameras = self._get_wmi_cameras()
        wmi_by_name: dict[str, str] = {c["name"]: c["device_id"] for c in wmi_cameras}
        wmi_names = set(wmi_by_name.keys())
        devices = []
        now_ms = int(time.time() * 1000)
        validate = params.get("validate", False)

        if self._stream_active:
            w = 0
            h = 0
            fps_est = 0.0
            cap_ref = getattr(self, '_cap', None)
            if cap_ref:
                try:
                    w = int(cap_ref.get(cv2.CAP_PROP_FRAME_WIDTH))
                    h = int(cap_ref.get(cv2.CAP_PROP_FRAME_HEIGHT))
                    fps_est = round(cap_ref.get(cv2.CAP_PROP_FPS) or 0, 1)
                except Exception:
                    pass
            active_name = getattr(self, '_device_name', None) or self._resolve_device_name(wmi_cameras)
            active_pid = wmi_by_name.get(active_name, "")
            devices.append({
                "index": self._device_index,
                "name": active_name,
                "physical_id": active_pid,
                "raw_indexes": [self._device_index],
                "width": w,
                "height": h,
                "fps": fps_est,
                "status": "usable",
                "online": True,
                "busy": True,
                "selected": True,
                "last_validated_at": now_ms,
                "last_probe_error": None,
            })
            seen_names = {active_name}
            for cam in wmi_cameras:
                if cam["name"] not in seen_names:
                    seen_names.add(cam["name"])
                    devices.append({
                        "index": -1,
                        "name": cam["name"],
                        "physical_id": cam["device_id"],
                        "raw_indexes": [],
                        "width": 0,
                        "height": 0,
                        "fps": 0,
                        "status": "unknown",
                        "online": True,
                        "busy": False,
                        "selected": False,
                        "last_validated_at": 0,
                        "last_probe_error": None,
                    })
            devices.sort(key=lambda d: d["index"])
            return {"success": True, "devices": devices, "selected_index": self._device_index}

        # Fast path: WMI-only enumeration (no DirectShow probe).
        # DirectShow probing can hard-crash the process on Windows when
        # a device is in a bad state. Only probe when validate=true.
        if not validate:
            for i, cam in enumerate(wmi_cameras):
                devices.append({
                    "index": i,
                    "name": cam["name"],
                    "physical_id": cam["device_id"],
                    "raw_indexes": [i],
                    "width": 0,
                    "height": 0,
                    "fps": 0,
                    "status": "unknown",
                    "online": True,
                    "busy": False,
                    "selected": i == self._device_index,
                    "last_validated_at": 0,
                    "last_probe_error": None,
                })
            if not devices:
                devices.append({
                    "index": self._device_index,
                    "name": f"Camera {self._device_index}",
                    "physical_id": "",
                    "raw_indexes": [self._device_index],
                    "width": 0, "height": 0, "fps": 0,
                    "status": "unknown", "online": True,
                    "busy": False, "selected": True,
                    "last_validated_at": 0, "last_probe_error": None,
                })
            return {"success": True, "devices": devices, "selected_index": self._device_index}

        # Slow path: DirectShow probe (only when validate=true)
        wmi_name_by_idx: dict[int, str] = {}
        wmi_id_by_idx: dict[int, str] = {}
        if len(wmi_cameras) > 0:
            for i, c in enumerate(wmi_cameras):
                wmi_name_by_idx[i] = c["name"]
                wmi_id_by_idx[i] = c["device_id"]

        def probe_index(i: int) -> dict[str, Any] | None:
            try:
                cap = cv2.VideoCapture(i, cv2.CAP_DSHOW)
                if cap.isOpened():
                    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                    status = "usable"
                    fps_est = 0.0
                    probe_error = None
                    ret, frame = cap.read()
                    if not ret or frame is None:
                        status = "error"
                        probe_error = "no frames"
                    else:
                        t0 = time.monotonic()
                        count = 0
                        while time.monotonic() - t0 < 0.3:
                            r, _ = cap.read()
                            if r:
                                count += 1
                        elapsed = time.monotonic() - t0
                        fps_est = round(count / elapsed, 1) if elapsed > 0 else 0.0
                    cap.release()
                    return {
                        "index": i,
                        "name": wmi_name_by_idx.get(i, f"Camera {i}"),
                        "physical_id": wmi_id_by_idx.get(i, ""),
                        "raw_indexes": [i],
                        "width": w,
                        "height": h,
                        "fps": fps_est,
                        "status": status,
                        "online": True,
                        "busy": False,
                        "selected": False,
                        "last_validated_at": now_ms,
                        "last_probe_error": probe_error,
                    }
                cap.release()
            except Exception:
                pass
            return None

        probed = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
            futures = {pool.submit(probe_index, i): i for i in range(8)}
            for fut in concurrent.futures.as_completed(futures, timeout=8):
                try:
                    result = fut.result(timeout=4)
                    if result:
                        probed.append(result)
                except Exception:
                    pass

        # Deduplicate: group DirectShow indexes under physical cameras
        devices = self._build_physical_device_map(wmi_cameras, probed)
        for d in devices:
            d["selected"] = d["index"] == self._device_index
        return {"success": True, "devices": devices, "selected_index": self._device_index}

    def _select_device(self, params: dict[str, Any]) -> dict[str, Any]:
        """Select camera device by index. Validates frames before claiming success.

        Transactional: rolls back to previous device on failure.
        """
        new_index = params.get("device_index")
        if new_index is None:
            return {"success": False, "error": "device_index required"}
        new_index = int(new_index)
        old_index = self._device_index

        if new_index == old_index:
            return {"success": True, "device_index": new_index, "restarted_stream": False,
                    "message": "already on this device"}

        import cv2

        validation = self._validate_device(new_index)
        if validation["status"] not in ("usable", "stale"):
            return {
                "success": False,
                "error": f"device {new_index} validation failed: {validation.get('error', validation['status'])}",
                "validation": validation,
            }

        was_streaming = self._stream_active
        if was_streaming:
            logger.info("stopping stream on device %d for switch to %d", old_index, new_index)
            self._stream_active = False
            if self._stream_thread and self._stream_thread.is_alive():
                self._stream_thread.join(timeout=3.0)

        self._device_index = new_index
        self._save_device_preference()
        logger.info("camera device changed: %d -> %d", old_index, new_index)

        restarted = False
        if was_streaming:
            logger.info("restarting stream on new device %d", new_index)
            start_result = self._stream_start({
                "device_index": new_index,
                "fps": params.get("fps", 15),
                "width": params.get("width", 1280),
                "height": params.get("height", 720),
                "quality": params.get("quality", 70),
            })
            if not start_result.get("success"):
                logger.warning("switch rollback: stream failed on device %d, reverting to %d", new_index, old_index)
                self._device_index = old_index
                self._save_device_preference()
                self._stream_start({
                    "device_index": old_index,
                    "fps": params.get("fps", 15),
                    "width": params.get("width", 1280),
                    "height": params.get("height", 720),
                    "quality": params.get("quality", 70),
                })
                return {
                    "success": False,
                    "error": f"stream failed on device {new_index} — rolled back to {old_index}",
                    "device_index": old_index,
                    "rolled_back": True,
                }
            restarted = True

        wmi_cameras = self._get_wmi_cameras()
        name = self._resolve_device_name(wmi_cameras)
        self._device_name = name
        return {
            "success": True,
            "device_index": new_index,
            "device_name": name,
            "restarted_stream": restarted,
            "validation": validation,
        }

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
        status: dict[str, Any] = {
            "success": True,
            "streaming": self._stream_active,
            "device_index": self._device_index,
            "presets_loaded": len(self._presets),
            "detector": det,
            "detect_interval": round(self._detect_min_interval, 2),
            "profile": self._stream_profile,
            "negotiated_width": self._negotiated_width,
            "negotiated_height": self._negotiated_height,
            "negotiated_fps": round(self._negotiated_fps, 1),
        }
        if self._stream_active:
            metrics = self._stream_metrics({})
            status["measured_fps"] = metrics.get("measured_fps", 0)
            status["bitrate_kbps"] = metrics.get("bitrate_kbps", 0)
            status["total_frames"] = metrics.get("total_frames", 0)
        return status

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

    # ── Camera capability negotiation ────────────────────────────────

    def _query_capabilities(self, params: dict[str, Any]) -> dict[str, Any]:
        """Probe camera for supported resolutions and FPS."""
        import cv2

        test_modes = [
            {"width": 1280, "height": 720, "label": "720p"},
            {"width": 1920, "height": 1080, "label": "1080p"},
            {"width": 3840, "height": 2160, "label": "4K"},
        ]
        supported: list[dict[str, Any]] = []
        device = params.get("device_index", self._device_index)

        if self._stream_active:
            supported.append({
                "width": self._negotiated_width,
                "height": self._negotiated_height,
                "fps": self._negotiated_fps,
                "label": f"{self._negotiated_height}p",
                "verified": True,
                "active": True,
            })
            for mode in test_modes:
                if mode["width"] != self._negotiated_width or mode["height"] != self._negotiated_height:
                    supported.append({
                        "width": mode["width"],
                        "height": mode["height"],
                        "fps": 0,
                        "label": mode["label"],
                        "verified": False,
                        "active": False,
                    })
            return {
                "success": True,
                "modes": supported,
                "profiles": CAMERA_PROFILES,
                "active_profile": self._stream_profile,
                "note": "stream active — non-active modes unverified",
            }

        cap = cv2.VideoCapture(device, cv2.CAP_DSHOW)
        if not cap.isOpened():
            return {"success": False, "error": "camera unavailable"}
        try:
            for mode in test_modes:
                cap.set(cv2.CAP_PROP_FRAME_WIDTH, mode["width"])
                cap.set(cv2.CAP_PROP_FRAME_HEIGHT, mode["height"])
                actual_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                actual_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                actual_fps = cap.get(cv2.CAP_PROP_FPS) or 0

                matched = (actual_w == mode["width"] and actual_h == mode["height"])
                if matched or actual_w >= mode["width"] * 0.9:
                    ret, _ = cap.read()
                    supported.append({
                        "width": actual_w,
                        "height": actual_h,
                        "fps": round(actual_fps, 1),
                        "label": mode["label"],
                        "verified": ret,
                        "active": False,
                    })
        finally:
            cap.release()

        return {
            "success": True,
            "modes": supported,
            "profiles": CAMERA_PROFILES,
            "active_profile": self._stream_profile,
        }

    def _set_profile(self, params: dict[str, Any]) -> dict[str, Any]:
        """Switch to a named camera profile. Restarts stream with new params."""
        profile_name = params.get("profile", "")
        if profile_name not in CAMERA_PROFILES:
            return {
                "success": False,
                "error": f"unknown profile: {profile_name}",
                "available": list(CAMERA_PROFILES.keys()),
            }
        profile = CAMERA_PROFILES[profile_name]
        was_streaming = self._stream_active
        if was_streaming:
            self._stream_stop({})

        result = self._stream_start({
            "profile": profile_name,
            "fps": profile["fps"],
            "width": profile["width"],
            "height": profile["height"],
            "quality": profile["quality"],
        })
        result["profile"] = profile_name
        result["profile_label"] = profile["label"]
        return result

    def _stream_metrics(self, params: dict[str, Any]) -> dict[str, Any]:
        """Return live stream performance metrics."""
        now = time.monotonic()
        cutoff = now - 2.0
        recent = [t for t in self._measured_fps_window if t >= cutoff]
        measured_fps = len(recent) / 2.0 if len(recent) >= 2 else 0.0

        avg_frame_bytes = 0
        if self._stream_frame_count > 0:
            avg_frame_bytes = self._stream_bytes_total // self._stream_frame_count

        bitrate_bps = int(measured_fps * avg_frame_bytes * 8) if measured_fps > 0 else 0

        det_status = self.get_detector_status()
        return {
            "success": True,
            "profile": self._stream_profile,
            "negotiated_width": self._negotiated_width,
            "negotiated_height": self._negotiated_height,
            "negotiated_fps": round(self._negotiated_fps, 1),
            "measured_fps": round(measured_fps, 1),
            "total_frames": self._stream_frame_count,
            "dropped_frames": self._stream_dropped,
            "avg_frame_bytes": avg_frame_bytes,
            "bitrate_bps": bitrate_bps,
            "bitrate_kbps": bitrate_bps // 1000,
            "detector_fps": round(1.0 / max(self._detect_min_interval, 0.001), 1),
            "detector_inference_ms": det_status.get("last_inference_ms", 0),
            "detector_device": det_status.get("device", "unknown"),
            "detector_nms_device": det_status.get("nms_device", "unknown"),
            "tracker_active": det_status.get("tracker_active", False),
            "tracker_active_tracks": det_status.get("active_tracks", 0),
        }


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
