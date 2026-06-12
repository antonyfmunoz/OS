"""IoU tracker — persistent object IDs across frames.

Assigns stable track_ids to YOLO detections using Intersection over Union
matching. No external dependencies beyond Python stdlib.

Algorithm:
1. For each new frame's detections, compute IoU matrix against active tracks.
2. Greedy-match highest IoU pairs (above threshold).
3. Matched tracks update position; unmatched tracks increment lost_frames.
4. Unmatched detections become new tracks.
5. Tracks exceeding max_lost_frames are removed.

This runs on Beast in the camera thread, same as detection.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class Track:
    track_id: int
    label: str
    confidence: float
    bbox: dict[str, float]
    center: tuple[float, float]
    velocity: tuple[float, float] = (0.0, 0.0)
    first_seen: float = 0.0
    last_seen: float = 0.0
    age_frames: int = 0
    lost_frames: int = 0
    status: str = "active"
    class_id: int = -1

    def to_dict(self) -> dict[str, Any]:
        return {
            "track_id": self.track_id,
            "label": self.label,
            "confidence": self.confidence,
            "bbox": self.bbox,
            "center": list(self.center),
            "velocity": list(self.velocity),
            "first_seen": self.first_seen,
            "last_seen": self.last_seen,
            "age_frames": self.age_frames,
            "lost_frames": self.lost_frames,
            "status": self.status,
        }


def _iou(a: dict[str, float], b: dict[str, float]) -> float:
    """Compute IoU between two bboxes {x, y, w, h} (normalized coords)."""
    ax1, ay1 = a["x"], a["y"]
    ax2, ay2 = ax1 + a["w"], ay1 + a["h"]
    bx1, by1 = b["x"], b["y"]
    bx2, by2 = bx1 + b["w"], by1 + b["h"]

    ix1 = max(ax1, bx1)
    iy1 = max(ay1, by1)
    ix2 = min(ax2, bx2)
    iy2 = min(ay2, by2)

    inter = max(0.0, ix2 - ix1) * max(0.0, iy2 - iy1)
    area_a = a["w"] * a["h"]
    area_b = b["w"] * b["h"]
    union = area_a + area_b - inter

    if union <= 0:
        return 0.0
    return inter / union


def _center(bbox: dict[str, float]) -> tuple[float, float]:
    return (bbox["x"] + bbox["w"] / 2, bbox["y"] + bbox["h"] / 2)


class IoUTracker:
    """Frame-by-frame IoU tracker with persistent IDs."""

    def __init__(
        self,
        iou_threshold: float = 0.25,
        max_lost_frames: int = 30,
        label_must_match: bool = True,
    ) -> None:
        self._iou_threshold = iou_threshold
        self._max_lost_frames = max_lost_frames
        self._label_must_match = label_must_match
        self._next_id: int = 1
        self._tracks: dict[int, Track] = {}
        self._frame_count: int = 0

    @property
    def active_tracks(self) -> list[Track]:
        return [t for t in self._tracks.values() if t.status == "active"]

    @property
    def all_tracks(self) -> list[Track]:
        return list(self._tracks.values())

    def update(self, detections: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Process one frame of detections. Returns detections with persistent track_ids.

        Each detection dict must have: label, confidence, bbox {x, y, w, h}.
        Returns the same dicts with track_id, center, velocity, age_frames,
        lost_frames, status, first_seen, last_seen added.
        """
        now = time.time()
        self._frame_count += 1

        active = [t for t in self._tracks.values() if t.status in ("active", "lost")]

        matched_track_ids: set[int] = set()
        matched_det_indices: set[int] = set()
        results: list[dict[str, Any]] = []

        if active and detections:
            pairs: list[tuple[float, int, int]] = []
            for ti, track in enumerate(active):
                for di, det in enumerate(detections):
                    if self._label_must_match and track.label != det.get("label", ""):
                        continue
                    score = _iou(track.bbox, det["bbox"])
                    if score >= self._iou_threshold:
                        pairs.append((score, ti, di))

            pairs.sort(key=lambda p: p[0], reverse=True)

            for score, ti, di in pairs:
                if ti in {p[1] for p in pairs if p != (score, ti, di) and p[1] == ti and p in matched_track_ids} or di in matched_det_indices:
                    continue
                track = active[ti]
                if track.track_id in matched_track_ids or di in matched_det_indices:
                    continue

                det = detections[di]
                old_center = track.center
                new_center = _center(det["bbox"])
                dt = now - track.last_seen if track.last_seen else 0.016
                if dt > 0:
                    vx = (new_center[0] - old_center[0]) / dt
                    vy = (new_center[1] - old_center[1]) / dt
                else:
                    vx, vy = 0.0, 0.0

                track.bbox = det["bbox"]
                track.center = new_center
                track.velocity = (round(vx, 4), round(vy, 4))
                track.confidence = det.get("confidence", track.confidence)
                track.last_seen = now
                track.age_frames += 1
                track.lost_frames = 0
                track.status = "active"
                if det.get("label"):
                    track.label = det["label"]

                matched_track_ids.add(track.track_id)
                matched_det_indices.add(di)

                result = dict(det)
                result.update(track.to_dict())
                results.append(result)

        for ti, track in enumerate(active):
            if track.track_id not in matched_track_ids:
                track.lost_frames += 1
                if track.lost_frames > self._max_lost_frames:
                    track.status = "removed"
                elif track.lost_frames > 3:
                    track.status = "lost"

        for di, det in enumerate(detections):
            if di in matched_det_indices:
                continue
            bbox = det["bbox"]
            center = _center(bbox)
            track = Track(
                track_id=self._next_id,
                label=det.get("label", "unknown"),
                confidence=det.get("confidence", 0.0),
                bbox=bbox,
                center=center,
                first_seen=now,
                last_seen=now,
                age_frames=1,
                class_id=det.get("class_id", -1),
            )
            self._next_id += 1
            self._tracks[track.track_id] = track

            result = dict(det)
            result.update(track.to_dict())
            results.append(result)

        self._tracks = {
            tid: t for tid, t in self._tracks.items() if t.status != "removed"
        }

        return results

    def get_track(self, track_id: int) -> Track | None:
        return self._tracks.get(track_id)

    def get_track_by_label(self, label: str) -> Track | None:
        label_lower = label.lower()
        candidates = [
            t for t in self._tracks.values()
            if t.label.lower() == label_lower and t.status == "active"
        ]
        if not candidates:
            candidates = [
                t for t in self._tracks.values()
                if t.label.lower() == label_lower
            ]
        if candidates:
            return max(candidates, key=lambda t: t.confidence)
        return None

    def get_scene_description(self) -> str:
        active = self.active_tracks
        if not active:
            return "No objects currently detected."
        parts = []
        for t in sorted(active, key=lambda t: t.confidence, reverse=True):
            cx, cy = t.center
            pos = _describe_position(cx, cy)
            parts.append(f"{t.label} #{t.track_id} ({pos}, {t.confidence:.0%})")
        return "I see " + ", ".join(parts) + "."

    def get_status(self) -> dict[str, Any]:
        return {
            "active_count": len(self.active_tracks),
            "total_count": len(self._tracks),
            "frame_count": self._frame_count,
            "next_id": self._next_id,
        }


def _describe_position(cx: float, cy: float) -> str:
    """Describe normalized center position in human terms."""
    if cy < 0.33:
        v = "top"
    elif cy > 0.66:
        v = "bottom"
    else:
        v = "center"
    if cx < 0.33:
        h = "left"
    elif cx > 0.66:
        h = "right"
    else:
        h = "center"
    if v == "center" and h == "center":
        return "center"
    if v == "center":
        return h
    if h == "center":
        return v
    return f"{v}-{h}"
