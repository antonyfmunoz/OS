"""Object detector — YOLOv8n inference on camera frames.

Loads YOLOv8n (nano) model on first call and runs inference on
numpy frames. Returns normalized bounding boxes (0.0-1.0) for
resolution-independent overlay rendering in the cockpit.

CPU-only by default. GPU used if CUDA is available.
Target: 3-10 FPS detection on Beast hardware.
"""

from __future__ import annotations

import json
import logging
import sys
import time
import threading
from pathlib import Path
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


_DEFAULT_CORRECTIONS_PATH = (
    Path("C:\\ProgramData\\UMH\\label_corrections.json")
    if sys.platform == "win32"
    else Path.home() / ".umh" / "label_corrections.json"
)


class ObjectDetector:
    """YOLOv8n object detector with lazy model loading and IoU tracking."""

    def __init__(self, confidence_threshold: float = 0.35) -> None:
        self._model = None
        self._model_name = "yolov8n"
        self._device = "cpu"
        self._confidence_threshold = confidence_threshold
        self._loaded = False
        self._load_error: str = ""
        self._lock = threading.Lock()
        self._frame_count = 0
        self._total_inference_ms = 0.0
        self._last_inference_ms = 0.0
        self._tracker = None
        self._corrections_path = _DEFAULT_CORRECTIONS_PATH
        self._label_corrections: dict[str, str] = self._load_corrections()
        self._init_tracker()

    def _init_tracker(self) -> None:
        try:
            from nodes.windows.umh_node.adapters.iou_tracker import IoUTracker
            self._tracker = IoUTracker(
                iou_threshold=0.25,
                max_lost_frames=30,
                label_must_match=True,
            )
            logger.info("IoU tracker initialized")
        except Exception as exc:
            logger.warning("tracker init failed, detections will lack persistent IDs: %s", exc)
            self._tracker = None

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
                import torch
                self._device = "cuda" if torch.cuda.is_available() else "cpu"
                logger.info("loading YOLOv8n on %s (CUDA available: %s)...", self._device, torch.cuda.is_available())
                if self._device == "cuda":
                    logger.info("GPU: %s", torch.cuda.get_device_name(0))
                t0 = time.monotonic()
                self._model = YOLO("yolov8n.pt")
                self._model.to(self._device)
                load_time = (time.monotonic() - t0) * 1000
                self._loaded = True
                self._load_error = ""
                logger.info("YOLOv8n loaded on %s in %.0fms", self._device, load_time)
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
            results = self._model(frame, verbose=False, conf=self._confidence_threshold, device=self._device)
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

        raw_detections = []
        boxes = result.boxes
        if boxes is None or len(boxes) == 0:
            if self._tracker:
                self._tracker.update([])
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

            raw_detections.append({
                "label": display_label,
                "confidence": round(conf, 3),
                "bbox": {"x": round(nx, 4), "y": round(ny, 4),
                         "w": round(nw, 4), "h": round(nh, 4)},
                "source": "real",
                "model": self._model_name,
                "class_id": cls_id,
            })

        if self._tracker:
            tracked = self._tracker.update(raw_detections)
            for d in tracked:
                tid = str(d.get("track_id", ""))
                if tid in self._label_corrections:
                    d["raw_label"] = d["label"]
                    d["label"] = self._label_corrections[tid]
            return tracked

        for i, d in enumerate(raw_detections):
            d["id"] = f"det_{self._frame_count}_{i}"
            d["track_id"] = d["id"]
        return raw_detections

    def get_status(self) -> dict[str, Any]:
        status: dict[str, Any] = {
            "loaded": self._loaded,
            "model": self._model_name,
            "device": self._device,
            "load_error": self._load_error,
            "frame_count": self._frame_count,
            "avg_inference_ms": round(self.avg_inference_ms, 1),
            "last_inference_ms": round(self._last_inference_ms, 1),
            "confidence_threshold": self._confidence_threshold,
            "tracker_active": self._tracker is not None,
        }
        if self._tracker:
            ts = self._tracker.get_status()
            status["active_tracks"] = ts["active_count"]
            status["total_tracks"] = ts["total_count"]
        return status

    def get_scene_description(self) -> str:
        if not self._tracker:
            return "Tracker not available."
        return self._tracker.get_scene_description()

    def get_track_by_label(self, label: str) -> dict[str, Any] | None:
        if not self._tracker:
            return None
        track = self._tracker.get_track_by_label(label)
        return track.to_dict() if track else None

    def get_active_tracks(self) -> list[dict[str, Any]]:
        if not self._tracker:
            return []
        tracks = []
        for t in self._tracker.active_tracks:
            d = t.to_dict()
            tid = str(d.get("track_id", ""))
            if tid in self._label_corrections:
                d["raw_label"] = d["label"]
                d["label"] = self._label_corrections[tid]
            tracks.append(d)
        return tracks

    def _load_corrections(self) -> dict[str, str]:
        if self._corrections_path.exists():
            try:
                return json.loads(self._corrections_path.read_text())
            except Exception as exc:
                logger.warning("failed to load label corrections: %s", exc)
        return {}

    def _save_corrections(self) -> None:
        try:
            self._corrections_path.parent.mkdir(parents=True, exist_ok=True)
            self._corrections_path.write_text(json.dumps(self._label_corrections, indent=2))
        except Exception as exc:
            logger.warning("failed to save label corrections: %s", exc)

    def correct_label(self, track_id: str, corrected_label: str) -> bool:
        self._label_corrections[str(track_id)] = corrected_label
        self._save_corrections()
        if self._tracker:
            track = self._tracker.get_track(int(track_id)) if track_id.isdigit() else None
            if track:
                track.label = corrected_label
                return True
        return True

    def remove_label_correction(self, track_id: str) -> None:
        self._label_corrections.pop(str(track_id), None)
        self._save_corrections()

    def get_label_corrections(self) -> dict[str, str]:
        return dict(self._label_corrections)
