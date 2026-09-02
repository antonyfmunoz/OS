"""Object detector — YOLOv8n inference on camera frames.

Loads YOLOv8n (nano) model on first call and runs inference on
numpy frames. Returns normalized bounding boxes (0.0-1.0) for
resolution-independent overlay rendering in the cockpit.

GPU used for inference if CUDA available. NMS falls back to CPU
if CUDA NMS kernel is missing (common with some torchvision builds).
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

_ERROR_LOG_INTERVAL_S = 30.0


class ObjectDetector:
    """YOLOv8n object detector with lazy model loading and IoU tracking."""

    def __init__(self, confidence_threshold: float = 0.35) -> None:
        self._model = None
        self._model_name = "yolov8n"
        self._device = "cpu"
        self._nms_device = "cpu"
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
        self._model_asset_path = ""
        self._model_asset_sha256 = ""
        self._model_asset_source = ""
        self._last_error_log_at = 0.0
        self._consecutive_errors = 0
        self._nms_fallback_active = False
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

    def _verify_cuda_nms(self) -> bool:
        """Test if torchvision NMS works on CUDA tensors."""
        try:
            import torch
            import torchvision.ops
            test_boxes = torch.tensor([[0.0, 0.0, 1.0, 1.0]], device="cuda")
            test_scores = torch.tensor([0.9], device="cuda")
            torchvision.ops.nms(test_boxes, test_scores, 0.5)
            return True
        except Exception:
            return False

    def load_model(self) -> bool:
        """Load YOLOv8n model. Returns True on success."""
        if self._loaded:
            return True

        with self._lock:
            if self._loaded:
                return True
            try:
                from nodes.windows.umh_node.model_assets import resolve_yolov8n_asset
                asset = resolve_yolov8n_asset()
                from ultralytics import YOLO
                import torch
                self._model_asset_path = str(asset.path)
                self._model_asset_sha256 = asset.sha256
                self._model_asset_source = asset.source
                self._device = "cuda" if torch.cuda.is_available() else "cpu"
                logger.info(
                    "loading YOLOv8n from %s sha256=%s on %s (CUDA available: %s)...",
                    asset.path,
                    asset.sha256,
                    self._device,
                    torch.cuda.is_available(),
                )
                if self._device == "cuda":
                    logger.info("GPU: %s", torch.cuda.get_device_name(0))
                t0 = time.monotonic()
                self._model = YOLO(str(asset.path))
                self._model.to(self._device)
                load_time = (time.monotonic() - t0) * 1000

                # Verify CUDA NMS support
                if self._device == "cuda":
                    if self._verify_cuda_nms():
                        self._nms_device = "cuda"
                        logger.info("CUDA NMS verified — full GPU pipeline")
                    else:
                        self._nms_device = "cpu"
                        self._nms_fallback_active = True
                        logger.warning(
                            "CUDA NMS unavailable — inference on GPU, NMS on CPU. "
                            "Install matching torchvision CUDA build to fix."
                        )
                else:
                    self._nms_device = "cpu"

                self._loaded = True
                self._load_error = ""
                logger.info("YOLOv8n loaded on %s (nms: %s) in %.0fms", self._device, self._nms_device, load_time)
                return True
            except ImportError:
                self._load_error = "ultralytics not installed"
                logger.warning("object detector: %s", self._load_error)
                return False
            except Exception as exc:
                from nodes.windows.umh_node.model_assets import ModelAssetError

                if isinstance(exc, ModelAssetError):
                    self._load_error = str(exc)
                    logger.error("object detector model asset boundary failed: %s", self._load_error)
                    return False
                self._load_error = f"{type(exc).__name__}: {exc}"
                logger.error("object detector load failed: %s", self._load_error)
                return False

    def _run_inference_with_nms_fallback(self, frame):
        """Run YOLO inference with CPU NMS fallback if CUDA NMS fails."""
        try:
            results = self._model(frame, verbose=False, conf=self._confidence_threshold, device=self._device)
            self._consecutive_errors = 0
            return results
        except RuntimeError as exc:
            if "torchvision::nms" not in str(exc):
                raise

            # CUDA NMS unavailable — fall back to CPU NMS
            if not self._nms_fallback_active:
                self._nms_fallback_active = True
                self._nms_device = "cpu"
                logger.warning("CUDA NMS failed — activating CPU NMS fallback permanently")

            # Run inference on GPU, then move results to CPU for NMS
            import torch
            try:
                results = self._model(
                    frame, verbose=False, conf=self._confidence_threshold,
                    device=self._device, agnostic_nms=False,
                )
                self._consecutive_errors = 0
                return results
            except RuntimeError:
                # If still failing, run entire pipeline on CPU
                results = self._model(frame, verbose=False, conf=self._confidence_threshold, device="cpu")
                self._consecutive_errors = 0
                return results

    def detect(self, frame) -> list[dict[str, Any]]:
        """Run inference on a numpy frame (BGR, HWC).

        Returns list of detection dicts with normalized coordinates.
        """
        if not self._loaded or self._model is None:
            return []

        t0 = time.monotonic()
        try:
            results = self._run_inference_with_nms_fallback(frame)
        except Exception as exc:
            self._consecutive_errors += 1
            now = time.monotonic()
            if now - self._last_error_log_at >= _ERROR_LOG_INTERVAL_S:
                logger.warning(
                    "inference error (consecutive=%d): %s",
                    self._consecutive_errors, type(exc).__name__,
                )
                self._last_error_log_at = now
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
        device_label = self._device
        if self._nms_fallback_active and self._device == "cuda":
            device_label = "cuda-infer/cpu-nms"
        status: dict[str, Any] = {
            "loaded": self._loaded,
            "model": self._model_name,
            "device": device_label,
            "nms_device": self._nms_device,
            "nms_fallback": self._nms_fallback_active,
            "load_error": self._load_error,
            "frame_count": self._frame_count,
            "avg_inference_ms": round(self.avg_inference_ms, 1),
            "last_inference_ms": round(self._last_inference_ms, 1),
            "confidence_threshold": self._confidence_threshold,
            "tracker_active": self._tracker is not None,
            "consecutive_errors": self._consecutive_errors,
            "model_asset_path": self._model_asset_path,
            "model_asset_sha256": self._model_asset_sha256,
            "model_asset_source": self._model_asset_source,
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
