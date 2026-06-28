"""Desktop streaming adapter — captures screen and emits JPEG frames.

Uses mss for fast screen capture (~30ms per frame at 1080p).
Runs in a background thread, calls frame_callback with the same
dict shape as CameraAdapter so the NodeClient media queue handles both.
"""

from __future__ import annotations

import io
import logging
import time
from threading import Thread
from typing import Any, Callable

logger = logging.getLogger("umh.desktop_stream")


class DesktopStreamAdapter:
    def __init__(self, monitor_index: int = 1, fps: float = 2, quality: int = 60):
        self._monitor_index = monitor_index
        self._fps = fps
        self._quality = quality
        self._active = False
        self._thread: Thread | None = None
        self._callback: Callable[[dict[str, Any]], None] | None = None

    def set_frame_callback(self, cb: Callable[[dict[str, Any]], None]) -> None:
        self._callback = cb

    def start(self) -> None:
        if self._active:
            return
        self._active = True
        self._thread = Thread(target=self._capture_loop, daemon=True, name="desktop-stream")
        self._thread.start()
        logger.info("desktop stream started (monitor=%d, fps=%.1f, quality=%d)",
                     self._monitor_index, self._fps, self._quality)

    def stop(self) -> None:
        self._active = False
        if self._thread:
            self._thread.join(timeout=3)
            self._thread = None
        logger.info("desktop stream stopped")

    def _capture_loop(self) -> None:
        try:
            import mss
            from PIL import Image
        except ImportError as e:
            logger.error("desktop stream requires mss and Pillow: %s", e)
            self._active = False
            return

        interval = 1.0 / self._fps
        with mss.mss() as sct:
            monitors = sct.monitors
            if self._monitor_index >= len(monitors):
                logger.error("monitor index %d not available (have %d)",
                             self._monitor_index, len(monitors) - 1)
                self._active = False
                return

            monitor = monitors[self._monitor_index]
            logger.info("capturing monitor %d: %dx%d", self._monitor_index,
                        monitor["width"], monitor["height"])

            while self._active:
                t0 = time.monotonic()
                try:
                    img = sct.grab(monitor)
                    pil_img = Image.frombytes("RGB", img.size, img.bgra, "raw", "BGRX")
                    buf = io.BytesIO()
                    pil_img.save(buf, format="JPEG", quality=self._quality)
                    jpeg_bytes = buf.getvalue()

                    if self._callback:
                        self._callback({
                            "source": "desktop",
                            "monitor": f"M{self._monitor_index - 1}",
                            "image_jpeg": jpeg_bytes,
                            "width": img.size.width,
                            "height": img.size.height,
                            "timestamp": time.time(),
                        })
                except Exception as exc:
                    logger.debug("capture error: %s", exc)

                elapsed = time.monotonic() - t0
                sleep_time = max(0, interval - elapsed)
                if sleep_time > 0:
                    time.sleep(sleep_time)

        logger.info("capture loop exited")
