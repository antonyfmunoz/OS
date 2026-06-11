"""Object detector — YOLOv8n inference on camera frames.

Loads YOLOv8n (nano) model on first call and runs inference on
numpy frames. Returns normalized bounding boxes (0.0-1.0) for
resolution-independent overlay rendering in the cockpit.

CPU-only by default. GPU used if CUDA is available.
Target: 3-10 FPS detection on Beast hardware.
"""

from __future__ import annotations

import logging
import time
import threading
from typing import Any

logger = logging.getLogger(__name__)

COCO_LABEL_MAP = {
    0: "person",
    24: "backpack",
    25: "umbrella",
    26: "handbag",
    27: "tie",
    28: "suitcase",
    39: "bottle",
    41: "cup",
    56: "chair",
    57: "couch",
    58: "potted_plant",
    59: "bed",
    60: "dining_table",
    62: "tv",
    63: "laptop",
    64: "mouse",
    65: "remote",
    66: "keyboard",
    67: "cell_phone",
    68: "microwave",
    69: "oven",
    72: "refrigerator",
    73: "book",
    74: "clock",
    75: "vase",
}

PRIORITY_CLASSES = {
    "keyboard", "chair", "dining_table", "mouse", "tv", "laptop",
    "person", "cell_phone", "cup", "bottle", "book", "backpack",
    "remote", "couch", "clock", "handbag", "tie",
}

LABEL_REMAP = {
    "dining_table": "desk",
    "tv": "monitor",
    "cell_phone": "phone",
    "potted_plant": "plant",
}


class ObjectDetector:
    """YOLOv8n object detector with lazy model loading."""

    def __init__(self, confidence_threshold: float = 0.35) -> None:
        self._model = None
        self._model_name = "yolov8n"
        self._confidence_threshold = confidence_threshold
        self._loaded = False
        self._load_error: str = ""
        self._lock = threading.Lock()
        self._frame_count = 0
        self._total_inference_ms = 0.0
        self._last_inference_ms = 0.0

    @property
    def loaded(self) -> bool:
        return self._loaded

    @property
    def load_error(self) -> str:
        return self._load_error

    @property
    def avg_inference_ms(self) -> float:
        if self._frame_count == 0:
            return 0.0
        return self._total_inference_ms / self._frame_count

    def load_model(self) -> bool:
        """Load YOLOv8n model. Returns True on success."""
        if self._loaded:
            return True

        with self._lock:
            if self._loaded:
                return True
            try:
                from ultralytics import YOLO
                logger.info("loading YOLOv8n model...")
                t0 = time.monotonic()
                self._model = YOLO("yolov8n.pt")
                load_time = (time.monotonic() - t0) * 1000
                self._loaded = True
                self._load_error = ""
                logger.info("YOLOv8n loaded in %.0fms", load_time)
                return True
            except ImportError:
                self._load_error = "ultralytics not installed"
                logger.warning("object detector: %s", self._load_error)
                return False
            except Exception as exc:
                self._load_error = f"{type(exc).__name__}: {exc}"
                logger.error("object detector load failed: %s", self._load_error)
                return False

    def detect(self, frame) -> list[dict[str, Any]]:
        """Run inference on a numpy frame (BGR, HWC).

        Returns list of detection dicts with normalized coordinates.
        """
        if not self._loaded or self._model is None:
            return []

        t0 = time.monotonic()
        try:
            results = self._model(frame, verbose=False, conf=self._confidence_threshold)
        except Exception as exc:
            logger.warning("inference error: %s", exc)
            return []

        elapsed_ms = (time.monotonic() - t0) * 1000
        self._frame_count += 1
        self._total_inference_ms += elapsed_ms
        self._last_inference_ms = elapsed_ms

        if not results or len(results) == 0:
            return []

        result = results[0]
        h, w = frame.shape[:2]
        if h == 0 or w == 0:
            return []

        detections = []
        boxes = result.boxes
        if boxes is None or len(boxes) == 0:
            return []

        for i in range(len(boxes)):
            cls_id = int(boxes.cls[i].item())
            conf = float(boxes.conf[i].item())
            label = COCO_LABEL_MAP.get(cls_id)
            if label is None:
                continue
            if label not in PRIORITY_CLASSES:
                continue

            display_label = LABEL_REMAP.get(label, label)

            x1, y1, x2, y2 = boxes.xyxy[i].tolist()
            nx = x1 / w
            ny = y1 / h
            nw = (x2 - x1) / w
            nh = (y2 - y1) / h

            detections.append({
                "id": f"det_{self._frame_count}_{i}",
                "label": display_label,
                "confidence": round(conf, 3),
                "bbox": {"x": round(nx, 4), "y": round(ny, 4),
                         "w": round(nw, 4), "h": round(nh, 4)},
                "source": "real",
                "model": self._model_name,
                "class_id": cls_id,
            })

        return detections

    def get_status(self) -> dict[str, Any]:
        return {
            "loaded": self._loaded,
            "model": self._model_name,
            "load_error": self._load_error,
            "frame_count": self._frame_count,
            "avg_inference_ms": round(self.avg_inference_ms, 1),
            "last_inference_ms": round(self._last_inference_ms, 1),
            "confidence_threshold": self._confidence_threshold,
        }
