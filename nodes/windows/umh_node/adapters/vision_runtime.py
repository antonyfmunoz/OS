"""Vision runtime — CV capability detection and tracker management on Beast.

Detects which CV backends are available (OpenCV contrib, MediaPipe, ONNX),
reports capabilities to VPS, and manages tracker processes that emit
overlay metadata (bounding boxes, landmarks) alongside camera frames.

All detection is deterministic — no LLM calls. Trackers run in threads
with independent FPS targets. Overlay metadata uses normalized 0.0-1.0
coordinates for resolution-independent rendering.
"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable

logger = logging.getLogger(__name__)


@dataclass
class CVCapability:
    """A single computer vision capability."""

    name: str
    available: bool = False
    backend: str = ""
    version: str = ""
    gpu_supported: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "available": self.available,
            "backend": self.backend,
            "version": self.version,
            "gpu_supported": self.gpu_supported,
        }


@dataclass
class TrackerProcess:
    """A running tracker thread with its metadata."""

    category: str
    target_fps: int = 10
    running: bool = False
    actual_fps: float = 0.0
    cpu_cost: float = 0.0
    gpu_cost: float = 0.0
    frame_count: int = 0
    last_error: str = ""
    _thread: threading.Thread | None = field(default=None, repr=False)
    _stop_event: threading.Event = field(default_factory=threading.Event, repr=False)

    def to_dict(self) -> dict[str, Any]:
        return {
            "category": self.category,
            "target_fps": self.target_fps,
            "running": self.running,
            "actual_fps": self.actual_fps,
            "cpu_cost": self.cpu_cost,
            "gpu_cost": self.gpu_cost,
            "frame_count": self.frame_count,
            "last_error": self.last_error,
        }


TRACKER_CATEGORIES = [
    "object_detector",
    "item_tracker",
    "person_tracker",
    "face_tracker",
    "hand_tracker",
    "pose_tracker",
    "motion_tracker",
    "region_tracker",
    "scene_change_tracker",
    "operator_presence_tracker",
    "unknown_person_tracker",
]


def detect_capabilities() -> dict[str, CVCapability]:
    """Detect available CV backends on this machine."""
    caps: dict[str, CVCapability] = {}

    # OpenCV
    try:
        import cv2
        caps["opencv"] = CVCapability(
            name="opencv",
            available=True,
            backend="opencv",
            version=cv2.__version__,
            gpu_supported=cv2.cuda.getCudaEnabledDeviceCount() > 0 if hasattr(cv2, 'cuda') else False,
        )
    except Exception:
        caps["opencv"] = CVCapability(name="opencv", available=False)

    # MediaPipe
    try:
        import mediapipe as mp
        caps["mediapipe"] = CVCapability(
            name="mediapipe",
            available=True,
            backend="mediapipe",
            version=mp.__version__,
        )
    except Exception:
        caps["mediapipe"] = CVCapability(name="mediapipe", available=False)

    # ONNX Runtime
    try:
        import onnxruntime as ort
        providers = ort.get_available_providers()
        caps["onnxruntime"] = CVCapability(
            name="onnxruntime",
            available=True,
            backend="onnxruntime",
            version=ort.__version__,
            gpu_supported="CUDAExecutionProvider" in providers,
        )
    except Exception:
        caps["onnxruntime"] = CVCapability(name="onnxruntime", available=False)

    return caps


def map_capabilities_to_trackers(caps: dict[str, CVCapability]) -> dict[str, bool]:
    """Map detected CV capabilities to which tracker categories are supported."""
    has_opencv = caps.get("opencv", CVCapability(name="opencv")).available
    has_mediapipe = caps.get("mediapipe", CVCapability(name="mediapipe")).available
    has_onnx = caps.get("onnxruntime", CVCapability(name="onnxruntime")).available

    return {
        "object_detector": has_opencv or has_onnx,
        "item_tracker": has_opencv,
        "person_tracker": has_opencv or has_mediapipe,
        "face_tracker": has_mediapipe or has_opencv,
        "hand_tracker": has_mediapipe,
        "pose_tracker": has_mediapipe,
        "motion_tracker": has_opencv,
        "region_tracker": has_opencv,
        "scene_change_tracker": has_opencv,
        "operator_presence_tracker": has_mediapipe or has_opencv,
        "unknown_person_tracker": has_mediapipe or has_opencv,
    }


class VisionRuntime:
    """Manages CV capability detection and tracker processes on Beast."""

    def __init__(self, emit_fn: Callable[[str, dict[str, Any]], None] | None = None) -> None:
        self._capabilities = detect_capabilities()
        self._tracker_support = map_capabilities_to_trackers(self._capabilities)
        self._trackers: dict[str, TrackerProcess] = {}
        self._emit_fn = emit_fn
        logger.info(
            "vision runtime initialized: opencv=%s mediapipe=%s onnx=%s",
            self._capabilities.get("opencv", CVCapability(name="opencv")).available,
            self._capabilities.get("mediapipe", CVCapability(name="mediapipe")).available,
            self._capabilities.get("onnxruntime", CVCapability(name="onnxruntime")).available,
        )

    @property
    def capabilities(self) -> dict[str, CVCapability]:
        return dict(self._capabilities)

    @property
    def tracker_support(self) -> dict[str, bool]:
        return dict(self._tracker_support)

    def start_tracker(self, category: str, target_fps: int = 10) -> bool:
        """Start a tracker thread for the given category."""
        if category not in TRACKER_CATEGORIES:
            logger.warning("unknown tracker category: %s", category)
            return False
        if not self._tracker_support.get(category, False):
            logger.warning("tracker %s not supported (missing CV backend)", category)
            return False
        if category in self._trackers and self._trackers[category].running:
            logger.info("tracker %s already running", category)
            return True

        proc = TrackerProcess(category=category, target_fps=target_fps)
        proc._stop_event.clear()
        proc.running = True
        proc._thread = threading.Thread(
            target=self._tracker_loop,
            args=(proc,),
            daemon=True,
            name=f"tracker-{category}",
        )
        self._trackers[category] = proc
        proc._thread.start()
        logger.info("tracker started: %s @ %d fps", category, target_fps)
        return True

    def stop_tracker(self, category: str) -> bool:
        proc = self._trackers.get(category)
        if not proc or not proc.running:
            return False
        proc._stop_event.set()
        proc.running = False
        if proc._thread and proc._thread.is_alive():
            proc._thread.join(timeout=2.0)
        logger.info("tracker stopped: %s (%d frames)", category, proc.frame_count)
        return True

    def stop_all(self) -> None:
        for category in list(self._trackers.keys()):
            self.stop_tracker(category)

    def get_running_trackers(self) -> list[TrackerProcess]:
        return [p for p in self._trackers.values() if p.running]

    def get_state_summary(self) -> dict[str, Any]:
        return {
            "capabilities": {k: v.to_dict() for k, v in self._capabilities.items()},
            "tracker_support": dict(self._tracker_support),
            "running_trackers": [p.to_dict() for p in self.get_running_trackers()],
        }

    def _tracker_loop(self, proc: TrackerProcess) -> None:
        """Placeholder tracker loop — emits dummy overlay metadata at target FPS."""
        interval = 1.0 / max(proc.target_fps, 1)
        while not proc._stop_event.is_set():
            start = time.monotonic()
            proc.frame_count += 1

            if self._emit_fn:
                self._emit_fn("tracker_overlay", {
                    "category": proc.category,
                    "frame_number": proc.frame_count,
                    "overlays": [],
                })

            elapsed = time.monotonic() - start
            sleep_time = interval - elapsed
            if sleep_time > 0:
                proc._stop_event.wait(sleep_time)

            if proc.frame_count % 100 == 0:
                proc.actual_fps = 1.0 / max(interval, 0.001)
