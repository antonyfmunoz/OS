"""Vision scene model — grounded workspace state from camera frames.

Every visual claim must trace to a real frame, timestamp, and confidence
score. No frame means no scene claim. Deterministic state management
with optional VLM enhancement for semantic analysis.
"""

from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

SCENE_EXPIRY_S = 300
OBJECT_LOST_THRESHOLD_S = 30
MAX_TRACKED_OBJECTS = 50
MAX_WATCH_ITEMS = 10
MAX_LABELED_ITEMS = 50
MAX_LABEL_LENGTH = 64


@dataclass
class DetectedObject:
    """A single object detected in a frame."""

    track_id: str
    label: str
    description: str = ""
    bbox: list[float] = field(default_factory=lambda: [0.0, 0.0, 0.0, 0.0])
    confidence: float = 0.0
    first_seen: float = 0.0
    last_seen: float = 0.0
    status: str = "visible"
    source: str = "detector"
    operator_confirmed: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "track_id": self.track_id,
            "label": self.label,
            "description": self.description,
            "bbox": self.bbox,
            "confidence": self.confidence,
            "first_seen": self.first_seen,
            "last_seen": self.last_seen,
            "status": self.status,
            "source": self.source,
            "operator_confirmed": self.operator_confirmed,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> DetectedObject:
        return cls(
            track_id=d.get("track_id", ""),
            label=d.get("label", ""),
            description=d.get("description", ""),
            bbox=d.get("bbox", [0.0, 0.0, 0.0, 0.0]),
            confidence=d.get("confidence", 0.0),
            first_seen=d.get("first_seen", 0.0),
            last_seen=d.get("last_seen", 0.0),
            status=d.get("status", "visible"),
            source=d.get("source", "detector"),
            operator_confirmed=d.get("operator_confirmed", False),
        )


@dataclass
class WatchItem:
    """An operator-requested watch on a tracked object."""

    watch_id: str
    target_label: str
    track_id: str = ""
    condition: str = "moved"
    camera_id: str = "default"
    cadence_fps: float = 1.0
    notify_on_change: bool = True
    expires_at: float = 0.0
    active: bool = True
    created_at: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "watch_id": self.watch_id,
            "target_label": self.target_label,
            "track_id": self.track_id,
            "condition": self.condition,
            "camera_id": self.camera_id,
            "cadence_fps": self.cadence_fps,
            "notify_on_change": self.notify_on_change,
            "expires_at": self.expires_at,
            "active": self.active,
            "created_at": self.created_at,
        }


@dataclass
class FollowState:
    """Active follow-mode state."""

    active: bool = False
    target: str = ""
    track_id: str = ""
    started_at: float = 0.0
    last_adjustment_at: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "active": self.active,
            "target": self.target,
            "track_id": self.track_id,
            "started_at": self.started_at,
            "last_adjustment_at": self.last_adjustment_at,
        }


@dataclass
class VisionScene:
    """Complete scene state from the latest camera observation."""

    scene_id: str = ""
    camera_id: str = "default"
    timestamp: float = 0.0
    frame_id: str = ""
    preset: str = ""
    objects: list[DetectedObject] = field(default_factory=list)
    regions: dict[str, dict[str, Any]] = field(default_factory=dict)
    summary: str = ""
    vlm_analyzed: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "scene_id": self.scene_id,
            "camera_id": self.camera_id,
            "timestamp": self.timestamp,
            "frame_id": self.frame_id,
            "preset": self.preset,
            "objects": [o.to_dict() for o in self.objects],
            "regions": self.regions,
            "summary": self.summary,
            "vlm_analyzed": self.vlm_analyzed,
        }

    def is_expired(self) -> bool:
        return (time.time() - self.timestamp) > SCENE_EXPIRY_S if self.timestamp else True

    def get_object_by_label(self, label: str) -> DetectedObject | None:
        label_lower = label.lower()
        for obj in self.objects:
            if obj.label.lower() == label_lower:
                return obj
        return None

    def get_object_by_track_id(self, track_id: str) -> DetectedObject | None:
        for obj in self.objects:
            if obj.track_id == track_id:
                return obj
        return None

    def get_visible_objects(self) -> list[DetectedObject]:
        return [o for o in self.objects if o.status in ("visible", "likely_visible")]


class VisionSceneManager:
    """Manages the current scene state, tracked objects, watch items, and follow mode.

    All state is ephemeral (in-memory). No persistent storage.
    """

    def __init__(self) -> None:
        self._scene = VisionScene()
        self._tracked: dict[str, DetectedObject] = {}
        self._watches: dict[str, WatchItem] = {}
        self._follow = FollowState()
        self._labeled_items: dict[str, DetectedObject] = {}
        self._frame_counter = 0

    @property
    def scene(self) -> VisionScene:
        return self._scene

    @property
    def follow_state(self) -> FollowState:
        return self._follow

    @property
    def tracked_objects(self) -> dict[str, DetectedObject]:
        return dict(self._tracked)

    @property
    def active_watches(self) -> dict[str, WatchItem]:
        return {k: v for k, v in self._watches.items() if v.active}

    def update_scene_from_frame(
        self,
        frame_id: str,
        camera_id: str = "default",
        preset: str = "",
        detected_objects: list[dict[str, Any]] | None = None,
        summary: str = "",
        vlm_analyzed: bool = False,
    ) -> VisionScene:
        """Update scene state from a new frame analysis."""
        now = time.time()
        self._frame_counter += 1

        self._scene = VisionScene(
            scene_id=f"scene_{uuid.uuid4().hex[:8]}",
            camera_id=camera_id,
            timestamp=now,
            frame_id=frame_id,
            preset=preset,
            summary=summary,
            vlm_analyzed=vlm_analyzed,
        )

        if detected_objects:
            for obj_data in detected_objects:
                label = obj_data.get("label", "unknown")
                existing = self._find_tracked_by_label(label)

                if existing:
                    existing.last_seen = now
                    existing.confidence = obj_data.get("confidence", existing.confidence)
                    existing.bbox = obj_data.get("bbox", existing.bbox)
                    existing.status = "visible"
                    self._scene.objects.append(existing)
                else:
                    obj = DetectedObject(
                        track_id=f"obj_{uuid.uuid4().hex[:6]}",
                        label=label,
                        description=obj_data.get("description", ""),
                        bbox=obj_data.get("bbox", [0.0, 0.0, 0.0, 0.0]),
                        confidence=obj_data.get("confidence", 0.0),
                        first_seen=now,
                        last_seen=now,
                        status="visible",
                        source=obj_data.get("source", "detector"),
                    )
                    self._scene.objects.append(obj)

        self._update_tracking_states(now)
        self._check_watches(now)

        return self._scene

    def start_tracking(
        self, label: str, track_hint: str = "", camera_id: str = "default",
    ) -> DetectedObject | None:
        """Start tracking a labeled item. Returns the tracked object or None if not visible."""
        if len(self._tracked) >= MAX_TRACKED_OBJECTS:
            logger.warning("max tracked objects reached (%d)", MAX_TRACKED_OBJECTS)
            return None

        existing = self._find_tracked_by_label(label)
        if existing:
            existing.status = "visible"
            self._tracked[existing.track_id] = existing
            return existing

        scene_obj = self._scene.get_object_by_label(label)
        if scene_obj:
            self._tracked[scene_obj.track_id] = scene_obj
            return scene_obj

        labeled = self._labeled_items.get(label.lower())
        if labeled:
            labeled.status = "unknown"
            self._tracked[labeled.track_id] = labeled
            return labeled

        now = time.time()
        obj = DetectedObject(
            track_id=f"obj_{uuid.uuid4().hex[:6]}",
            label=label,
            description=track_hint,
            first_seen=now,
            last_seen=now,
            status="unknown",
            source="operator_labeled",
            operator_confirmed=True,
        )
        self._tracked[obj.track_id] = obj
        return obj

    def stop_tracking(self, label_or_id: str) -> bool:
        """Stop tracking by label or track_id."""
        if label_or_id in self._tracked:
            del self._tracked[label_or_id]
            return True
        for tid, obj in list(self._tracked.items()):
            if obj.label.lower() == label_or_id.lower():
                del self._tracked[tid]
                return True
        return False

    def get_tracking_status(self, label_or_id: str) -> DetectedObject | None:
        if label_or_id in self._tracked:
            return self._tracked[label_or_id]
        for obj in self._tracked.values():
            if obj.label.lower() == label_or_id.lower():
                return obj
        return None

    def label_item(
        self, label: str, frame_id: str = "", bbox: list[float] | None = None,
    ) -> DetectedObject | None:
        """Operator labels a visible item. Requires confirmation (operator_confirmed=True)."""
        if len(label) > MAX_LABEL_LENGTH:
            logger.warning("label too long (%d > %d): %s…", len(label), MAX_LABEL_LENGTH, label[:20])
            return None

        now = time.time()
        existing = self._labeled_items.get(label.lower())
        if existing:
            existing.last_seen = now
            existing.operator_confirmed = True
            if bbox:
                existing.bbox = bbox
            return existing

        if len(self._labeled_items) >= MAX_LABELED_ITEMS:
            logger.warning("max labeled items reached (%d)", MAX_LABELED_ITEMS)
            return None

        obj = DetectedObject(
            track_id=f"obj_{uuid.uuid4().hex[:6]}",
            label=label,
            bbox=bbox or [0.0, 0.0, 0.0, 0.0],
            confidence=1.0,
            first_seen=now,
            last_seen=now,
            status="visible",
            source="operator_labeled",
            operator_confirmed=True,
        )
        self._labeled_items[label.lower()] = obj
        return obj

    def start_watch(
        self, target_label: str, condition: str = "moved",
        camera_id: str = "default", expires_minutes: int = 60,
    ) -> WatchItem | None:
        """Start watching for a condition on a tracked/labeled item."""
        if len(self._watches) >= MAX_WATCH_ITEMS:
            logger.warning("max watch items reached (%d)", MAX_WATCH_ITEMS)
            return None

        now = time.time()
        watch = WatchItem(
            watch_id=f"watch_{uuid.uuid4().hex[:6]}",
            target_label=target_label,
            condition=condition,
            camera_id=camera_id,
            expires_at=now + (expires_minutes * 60),
            active=True,
            created_at=now,
        )

        tracked = self._find_tracked_by_label(target_label)
        if tracked:
            watch.track_id = tracked.track_id

        self._watches[watch.watch_id] = watch
        logger.info("watch started: %s → %s (%s)", watch.watch_id, target_label, condition)
        return watch

    def stop_watch(self, target_or_id: str) -> bool:
        """Stop and remove a watch by target label or watch_id."""
        if target_or_id in self._watches:
            del self._watches[target_or_id]
            return True
        for wid, watch in list(self._watches.items()):
            if watch.target_label.lower() == target_or_id.lower():
                del self._watches[wid]
                return True
        return False

    def start_follow(self, target: str = "operator") -> FollowState:
        """Activate follow mode for a target."""
        now = time.time()
        self._follow = FollowState(
            active=True,
            target=target,
            started_at=now,
            last_adjustment_at=now,
        )

        tracked = self._find_tracked_by_label(target)
        if tracked:
            self._follow.track_id = tracked.track_id

        logger.info("follow mode activated: target=%s", target)
        return self._follow

    def stop_follow(self) -> None:
        """Deactivate follow mode immediately."""
        self._follow = FollowState()
        logger.info("follow mode deactivated")

    def query_visual(self, target: str) -> dict[str, Any]:
        """Answer a visual query from scene state. No LLM — pure state lookup."""
        result: dict[str, Any] = {
            "target": target,
            "camera_active": bool(self._scene.timestamp),
            "scene_age_s": time.time() - self._scene.timestamp if self._scene.timestamp else -1,
        }

        if self._scene.is_expired():
            result["status"] = "no_recent_frame"
            result["answer"] = "I don't have a recent frame to check. The camera may be off or the scene data has expired."
            return result

        if not target:
            result["status"] = "scene_summary"
            result["objects"] = [o.to_dict() for o in self._scene.get_visible_objects()]
            result["answer"] = self._scene.summary or f"I can see {len(self._scene.get_visible_objects())} objects."
            return result

        obj = self._scene.get_object_by_label(target)
        if not obj:
            tracked = self._find_tracked_by_label(target)
            if tracked:
                obj = tracked

        if obj:
            age_s = time.time() - obj.last_seen
            result["status"] = obj.status
            result["object"] = obj.to_dict()
            result["last_seen_age_s"] = age_s
            if obj.status == "visible":
                result["answer"] = (
                    f"I can see {obj.label} (confidence: {obj.confidence:.0%}). "
                    f"Last confirmed {age_s:.0f}s ago."
                )
            elif obj.status == "lost":
                result["answer"] = (
                    f"I lost sight of {obj.label}. Last seen {age_s:.0f}s ago."
                )
            else:
                result["answer"] = (
                    f"{obj.label} status: {obj.status}. Last seen {age_s:.0f}s ago."
                )
        else:
            labeled = self._labeled_items.get(target.lower())
            if labeled:
                result["status"] = labeled.status
                result["object"] = labeled.to_dict()
                result["answer"] = f"{labeled.label} was labeled but current status is {labeled.status}."
            else:
                result["status"] = "not_found"
                result["answer"] = f"I haven't seen '{target}' in the current scene."

        return result

    def get_state_summary(self) -> dict[str, Any]:
        """Return full state for cockpit UI."""
        now = time.time()
        self._expire_watches(now)

        return {
            "scene": self._scene.to_dict() if self._scene.timestamp else None,
            "scene_expired": self._scene.is_expired(),
            "tracked_objects": [o.to_dict() for o in self._tracked.values()],
            "labeled_items": [o.to_dict() for o in self._labeled_items.values()],
            "active_watches": [w.to_dict() for w in self._watches.values() if w.active],
            "follow_mode": self._follow.to_dict(),
        }

    def _find_tracked_by_label(self, label: str) -> DetectedObject | None:
        label_lower = label.lower()
        for obj in self._tracked.values():
            if obj.label.lower() == label_lower:
                return obj
        for obj in self._labeled_items.values():
            if obj.label.lower() == label_lower:
                return obj
        return None

    def _update_tracking_states(self, now: float) -> None:
        """Mark tracked objects as lost if not seen recently."""
        visible_labels = {o.label.lower() for o in self._scene.objects}
        for obj in self._tracked.values():
            if obj.label.lower() in visible_labels:
                obj.status = "visible"
                obj.last_seen = now
            elif (now - obj.last_seen) > OBJECT_LOST_THRESHOLD_S:
                if obj.status != "lost":
                    obj.status = "lost"
                    logger.info("tracked object lost: %s (%s)", obj.label, obj.track_id)

    def _check_watches(self, now: float) -> None:
        """Check watch conditions against current scene."""
        self._expire_watches(now)
        for watch in self._watches.values():
            if not watch.active:
                continue
            obj = self._find_tracked_by_label(watch.target_label)
            if not obj:
                continue
            if watch.condition == "disappeared" and obj.status == "lost":
                logger.info(
                    "watch triggered: %s — %s disappeared",
                    watch.watch_id, watch.target_label,
                )

    def _expire_watches(self, now: float) -> None:
        expired = [
            wid for wid, w in self._watches.items()
            if w.active and w.expires_at and now > w.expires_at
        ]
        for wid in expired:
            logger.info("watch expired: %s", wid)
            del self._watches[wid]


_manager: VisionSceneManager | None = None


def get_scene_manager() -> VisionSceneManager:
    """Get the singleton scene manager instance."""
    global _manager
    if _manager is None:
        _manager = VisionSceneManager()
    return _manager
