"""Webcam perception — face detection for operator presence tracking.

Uses OpenCV Haar cascade for lightweight face detection. Runs in a
background thread, polling at ~1 FPS. Emits presence state changes
(present → absent, absent → present) as callbacks for the perception
router to wire into OperatorMode transitions.

Graceful degradation:
  - No OpenCV → WebcamMonitor.start() returns False
  - No camera → WebcamMonitor.start() returns False
  - Detection failure → logs, continues polling
"""

from __future__ import annotations

import logging
import os
import sys
import threading
import time
from dataclasses import dataclass
from typing import Any, Callable

logger = logging.getLogger(__name__)

sys.path.insert(0, os.environ.get("UMH_ROOT", "/opt/OS"))


@dataclass
class PresenceState:
    """Current webcam presence observation."""

    face_detected: bool = False
    face_count: int = 0
    last_seen_at: float = 0.0
    absent_since: float = 0.0
    confidence: float = 0.0

    @property
    def seconds_absent(self) -> float:
        if self.face_detected or self.absent_since == 0.0:
            return 0.0
        return time.monotonic() - self.absent_since


class WebcamMonitor:
    """Background webcam monitor with face detection.

    Polls the camera at poll_interval_s (default 1.0s), runs Haar cascade
    face detection, and calls on_presence_change when presence state flips.
    """

    def __init__(
        self,
        on_presence_change: Callable[[PresenceState], None] | None = None,
        camera_index: int = 0,
        poll_interval_s: float = 1.0,
    ) -> None:
        self._on_change = on_presence_change
        self._camera_index = camera_index
        self._poll_interval_s = poll_interval_s
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._state = PresenceState()
        self._capture: Any = None
        self._cascade: Any = None
        self._running = False

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def state(self) -> PresenceState:
        return self._state

    def start(self) -> bool:
        """Start webcam monitoring. Returns False if camera/OpenCV unavailable."""
        if self._running:
            return True

        try:
            import cv2
        except ImportError:
            logger.info("OpenCV not installed — webcam perception disabled")
            return False

        cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        if not os.path.exists(cascade_path):
            logger.warning("Haar cascade file not found: %s", cascade_path)
            return False

        self._cascade = cv2.CascadeClassifier(cascade_path)

        cap = cv2.VideoCapture(self._camera_index)
        if not cap.isOpened():
            logger.info("Camera %d not available — webcam perception disabled", self._camera_index)
            cap.release()
            return False

        self._capture = cap
        self._stop_event.clear()
        self._running = True
        self._thread = threading.Thread(target=self._poll_loop, daemon=True, name="umh-webcam")
        self._thread.start()
        logger.info("Webcam monitor started (camera %d)", self._camera_index)
        return True

    def stop(self) -> None:
        """Stop webcam monitoring and release camera."""
        self._stop_event.set()
        self._running = False
        if self._thread is not None:
            self._thread.join(timeout=3.0)
            self._thread = None
        if self._capture is not None:
            try:
                self._capture.release()
            except Exception:
                pass
            self._capture = None

    def _poll_loop(self) -> None:
        """Frame capture + face detection loop (runs in background thread)."""
        import cv2

        was_present = False

        while not self._stop_event.is_set():
            try:
                ret, frame = self._capture.read()
                if not ret or frame is None:
                    time.sleep(self._poll_interval_s)
                    continue

                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                faces = self._cascade.detectMultiScale(
                    gray,
                    scaleFactor=1.1,
                    minNeighbors=5,
                    minSize=(80, 80),
                )

                face_count = len(faces) if faces is not None else 0
                is_present = face_count > 0
                now = time.monotonic()

                self._state.face_detected = is_present
                self._state.face_count = face_count
                self._state.confidence = min(face_count * 0.5, 1.0) if is_present else 0.0

                if is_present:
                    self._state.last_seen_at = now
                    self._state.absent_since = 0.0
                elif was_present and not is_present:
                    self._state.absent_since = now

                if is_present != was_present and self._on_change is not None:
                    try:
                        self._on_change(self._state)
                    except Exception as exc:
                        logger.debug("Presence change callback failed: %s", exc)

                was_present = is_present

            except Exception as exc:
                logger.debug("Webcam poll error: %s", exc)

            self._stop_event.wait(self._poll_interval_s)

    def get_snapshot(self) -> dict[str, Any]:
        """Return current webcam state as a dict for status display."""
        return {
            "running": self._running,
            "face_detected": self._state.face_detected,
            "face_count": self._state.face_count,
            "seconds_absent": round(self._state.seconds_absent, 1),
            "confidence": round(self._state.confidence, 2),
        }
