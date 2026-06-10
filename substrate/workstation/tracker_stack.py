"""Tracker stack — independent, stackable vision trackers.

Each tracker category can be independently enabled/disabled.
Trackers report cost, fps, and latency. The stack degrades
gracefully — one tracker failure doesn't break others.

No LLM in the hot path. All state is ephemeral (in-memory).
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

MAX_ACTIVE_TRACKERS = 12


@dataclass
class TrackerConfig:
    """Configuration for a single tracker in the stack."""

    tracker_id: str
    category: str
    enabled: bool = False
    fps: int = 10
    overlay: bool = True
    cpu_cost: float = 0.0
    gpu_cost: float = 0.0
    status: str = "idle"
    last_update: float = 0.0
    error: str = ""
    available: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "tracker_id": self.tracker_id,
            "category": self.category,
            "enabled": self.enabled,
            "fps": self.fps,
            "overlay": self.overlay,
            "cpu_cost": self.cpu_cost,
            "gpu_cost": self.gpu_cost,
            "status": self.status,
            "last_update": self.last_update,
            "error": self.error,
            "available": self.available,
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

SENSITIVE_TRACKERS = {"face_tracker", "operator_presence_tracker", "unknown_person_tracker"}

DEFAULT_FPS: dict[str, int] = {
    "object_detector": 5,
    "item_tracker": 5,
    "person_tracker": 10,
    "face_tracker": 10,
    "hand_tracker": 15,
    "pose_tracker": 10,
    "motion_tracker": 10,
    "region_tracker": 5,
    "scene_change_tracker": 2,
    "operator_presence_tracker": 5,
    "unknown_person_tracker": 5,
}


@dataclass
class TrackerStack:
    """A named collection of tracker configurations."""

    stack_id: str
    label: str = ""
    enabled: bool = True
    trackers: dict[str, TrackerConfig] = field(default_factory=dict)
    created_at: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "stack_id": self.stack_id,
            "label": self.label,
            "enabled": self.enabled,
            "trackers": {k: v.to_dict() for k, v in self.trackers.items()},
            "created_at": self.created_at,
        }


class TrackerStackManager:
    """Manages tracker stacks and individual tracker enable/disable."""

    def __init__(self) -> None:
        self._stacks: dict[str, TrackerStack] = {}
        self._active_stack_id: str = ""
        self._capabilities: dict[str, bool] = {}

    @property
    def active_stack(self) -> TrackerStack | None:
        return self._stacks.get(self._active_stack_id)

    def set_capabilities(self, caps: dict[str, bool]) -> None:
        self._capabilities = dict(caps)

    def get_capabilities(self) -> dict[str, bool]:
        return dict(self._capabilities)

    def create_stack(
        self, stack_id: str, label: str = "", tracker_categories: list[str] | None = None,
    ) -> TrackerStack:
        """Create a new tracker stack with specified categories enabled."""
        now = time.time()
        stack = TrackerStack(
            stack_id=stack_id,
            label=label or stack_id,
            created_at=now,
        )

        for cat in TRACKER_CATEGORIES:
            available = self._capabilities.get(cat, True)
            cfg = TrackerConfig(
                tracker_id=f"{stack_id}_{cat}",
                category=cat,
                enabled=cat in (tracker_categories or []),
                fps=DEFAULT_FPS.get(cat, 5),
                available=available,
            )
            stack.trackers[cat] = cfg

        self._stacks[stack_id] = stack
        logger.info("tracker stack created: %s (%d trackers)", stack_id, len(stack.trackers))
        return stack

    def delete_stack(self, stack_id: str) -> bool:
        if stack_id in self._stacks:
            if self._active_stack_id == stack_id:
                self._active_stack_id = ""
            del self._stacks[stack_id]
            return True
        return False

    def activate_stack(self, stack_id: str) -> bool:
        if stack_id not in self._stacks:
            return False
        self._active_stack_id = stack_id
        logger.info("tracker stack activated: %s", stack_id)
        return True

    def enable_tracker(self, category: str, stack_id: str = "") -> bool:
        """Enable a tracker in the active (or specified) stack."""
        sid = stack_id or self._active_stack_id
        stack = self._stacks.get(sid)
        if not stack:
            return False
        cfg = stack.trackers.get(category)
        if not cfg:
            return False
        if not cfg.available:
            logger.warning("tracker %s not available on Beast", category)
            return False

        active_count = sum(1 for t in stack.trackers.values() if t.enabled)
        if active_count >= MAX_ACTIVE_TRACKERS:
            logger.warning("max active trackers reached (%d)", MAX_ACTIVE_TRACKERS)
            return False

        cfg.enabled = True
        cfg.status = "active"
        cfg.last_update = time.time()
        logger.info("tracker enabled: %s in stack %s", category, sid)
        return True

    def disable_tracker(self, category: str, stack_id: str = "") -> bool:
        """Disable a tracker in the active (or specified) stack."""
        sid = stack_id or self._active_stack_id
        stack = self._stacks.get(sid)
        if not stack:
            return False
        cfg = stack.trackers.get(category)
        if not cfg:
            return False
        cfg.enabled = False
        cfg.status = "idle"
        cfg.last_update = time.time()
        logger.info("tracker disabled: %s in stack %s", category, sid)
        return True

    def get_enabled_trackers(self, stack_id: str = "") -> list[TrackerConfig]:
        sid = stack_id or self._active_stack_id
        stack = self._stacks.get(sid)
        if not stack:
            return []
        return [t for t in stack.trackers.values() if t.enabled]

    def is_sensitive_tracker_enabled(self, stack_id: str = "") -> bool:
        """Check if any sensitive tracker (face/presence) is active."""
        for t in self.get_enabled_trackers(stack_id):
            if t.category in SENSITIVE_TRACKERS:
                return True
        return False

    def get_total_cost(self, stack_id: str = "") -> dict[str, float]:
        """Sum CPU/GPU cost across all enabled trackers."""
        enabled = self.get_enabled_trackers(stack_id)
        return {
            "cpu": sum(t.cpu_cost for t in enabled),
            "gpu": sum(t.gpu_cost for t in enabled),
        }

    def get_state_summary(self) -> dict[str, Any]:
        active = self.active_stack
        return {
            "active_stack_id": self._active_stack_id,
            "stacks": {k: v.to_dict() for k, v in self._stacks.items()},
            "capabilities": dict(self._capabilities),
            "enabled_trackers": [t.to_dict() for t in self.get_enabled_trackers()] if active else [],
            "total_cost": self.get_total_cost() if active else {"cpu": 0, "gpu": 0},
        }


_tracker_mgr: TrackerStackManager | None = None


def get_tracker_manager() -> TrackerStackManager:
    global _tracker_mgr
    if _tracker_mgr is None:
        _tracker_mgr = TrackerStackManager()
    return _tracker_mgr
