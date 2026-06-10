"""Vision Preset Studio — full CRUD for camera presets.

Presets define camera position (PTZ or ROI), associated tracker stacks,
quality modes, and named zones. This is the operator-editable preset
system, separate from the Beast hardware preset storage.

All state is ephemeral (in-memory) with optional JSON persistence.
"""

from __future__ import annotations

import json
import logging
import os
import time
import uuid
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

MAX_PRESETS = 50
MAX_ZONES_PER_PRESET = 20
MAX_PRESET_NAME_LENGTH = 64


@dataclass
class PresetZone:
    """A named region within a preset's view."""

    zone_id: str
    label: str
    polygon: list[list[float]] = field(default_factory=list)
    zone_type: str = "general"

    def to_dict(self) -> dict[str, Any]:
        return {
            "zone_id": self.zone_id,
            "label": self.label,
            "polygon": self.polygon,
            "zone_type": self.zone_type,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> PresetZone:
        return cls(
            zone_id=d.get("zone_id", ""),
            label=d.get("label", ""),
            polygon=d.get("polygon", []),
            zone_type=d.get("zone_type", "general"),
        )


@dataclass
class VisionPreset:
    """A fully-editable camera preset."""

    preset_id: str
    label: str
    description: str = ""
    camera_id: str = "default"
    mode: str = "physical_ptz"
    ptz: dict[str, int] = field(default_factory=lambda: {"pan": 0, "tilt": 0, "zoom": 100})
    roi: dict[str, float] = field(default_factory=lambda: {"x": 0.0, "y": 0.0, "w": 1.0, "h": 1.0})
    tracker_stack_id: str = ""
    quality_mode: str = "balanced"
    zones: list[PresetZone] = field(default_factory=list)
    trigger_chain_ids: list[str] = field(default_factory=list)
    created_at: float = 0.0
    updated_at: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "preset_id": self.preset_id,
            "label": self.label,
            "description": self.description,
            "camera_id": self.camera_id,
            "mode": self.mode,
            "ptz": dict(self.ptz),
            "roi": dict(self.roi),
            "tracker_stack_id": self.tracker_stack_id,
            "quality_mode": self.quality_mode,
            "zones": [z.to_dict() for z in self.zones],
            "trigger_chain_ids": list(self.trigger_chain_ids),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> VisionPreset:
        return cls(
            preset_id=d.get("preset_id", ""),
            label=d.get("label", ""),
            description=d.get("description", ""),
            camera_id=d.get("camera_id", "default"),
            mode=d.get("mode", "physical_ptz"),
            ptz=d.get("ptz", {"pan": 0, "tilt": 0, "zoom": 100}),
            roi=d.get("roi", {"x": 0.0, "y": 0.0, "w": 1.0, "h": 1.0}),
            tracker_stack_id=d.get("tracker_stack_id", ""),
            quality_mode=d.get("quality_mode", "balanced"),
            zones=[PresetZone.from_dict(z) for z in d.get("zones", [])],
            trigger_chain_ids=d.get("trigger_chain_ids", []),
            created_at=d.get("created_at", 0.0),
            updated_at=d.get("updated_at", 0.0),
        )


class VisionPresetManager:
    """Full CRUD manager for vision presets."""

    def __init__(self, persist_path: str = "") -> None:
        self._presets: dict[str, VisionPreset] = {}
        self._active_preset_id: str = ""
        self._persist_path = persist_path
        if persist_path and os.path.exists(persist_path):
            self._load()

    @property
    def active_preset(self) -> VisionPreset | None:
        return self._presets.get(self._active_preset_id)

    def create(
        self,
        preset_id: str,
        label: str,
        description: str = "",
        ptz: dict[str, int] | None = None,
        mode: str = "physical_ptz",
        tracker_stack_id: str = "",
        quality_mode: str = "balanced",
    ) -> VisionPreset | None:
        if len(preset_id) > MAX_PRESET_NAME_LENGTH:
            logger.warning("preset_id too long: %s", preset_id[:20])
            return None
        if len(self._presets) >= MAX_PRESETS:
            logger.warning("max presets reached (%d)", MAX_PRESETS)
            return None

        now = time.time()
        preset = VisionPreset(
            preset_id=preset_id,
            label=label,
            description=description,
            mode=mode,
            ptz=ptz or {"pan": 0, "tilt": 0, "zoom": 100},
            tracker_stack_id=tracker_stack_id,
            quality_mode=quality_mode,
            created_at=now,
            updated_at=now,
        )
        self._presets[preset_id] = preset
        self._persist()
        logger.info("preset created: %s (%s)", preset_id, label)
        return preset

    def rename(self, preset_id: str, new_label: str) -> bool:
        preset = self._presets.get(preset_id)
        if not preset:
            return False
        preset.label = new_label
        preset.updated_at = time.time()
        self._persist()
        return True

    def update_description(self, preset_id: str, description: str) -> bool:
        preset = self._presets.get(preset_id)
        if not preset:
            return False
        preset.description = description
        preset.updated_at = time.time()
        self._persist()
        return True

    def update_ptz(self, preset_id: str, ptz: dict[str, int]) -> bool:
        preset = self._presets.get(preset_id)
        if not preset:
            return False
        preset.ptz = dict(ptz)
        preset.updated_at = time.time()
        self._persist()
        return True

    def nudge_ptz(
        self, preset_id: str, pan_delta: int = 0, tilt_delta: int = 0, zoom_delta: int = 0,
    ) -> bool:
        preset = self._presets.get(preset_id)
        if not preset:
            return False
        preset.ptz["pan"] = preset.ptz.get("pan", 0) + pan_delta
        preset.ptz["tilt"] = preset.ptz.get("tilt", 0) + tilt_delta
        preset.ptz["zoom"] = max(100, preset.ptz.get("zoom", 100) + zoom_delta)
        preset.updated_at = time.time()
        self._persist()
        return True

    def set_tracker_stack(self, preset_id: str, stack_id: str) -> bool:
        preset = self._presets.get(preset_id)
        if not preset:
            return False
        preset.tracker_stack_id = stack_id
        preset.updated_at = time.time()
        self._persist()
        return True

    def add_zone(
        self, preset_id: str, label: str, polygon: list[list[float]], zone_type: str = "general",
    ) -> PresetZone | None:
        preset = self._presets.get(preset_id)
        if not preset:
            return None
        if len(preset.zones) >= MAX_ZONES_PER_PRESET:
            logger.warning("max zones per preset reached (%d)", MAX_ZONES_PER_PRESET)
            return None
        zone = PresetZone(
            zone_id=f"zone_{uuid.uuid4().hex[:6]}",
            label=label,
            polygon=polygon,
            zone_type=zone_type,
        )
        preset.zones.append(zone)
        preset.updated_at = time.time()
        self._persist()
        return zone

    def remove_zone(self, preset_id: str, zone_id: str) -> bool:
        preset = self._presets.get(preset_id)
        if not preset:
            return False
        before = len(preset.zones)
        preset.zones = [z for z in preset.zones if z.zone_id != zone_id]
        if len(preset.zones) < before:
            preset.updated_at = time.time()
            self._persist()
            return True
        return False

    def duplicate(self, preset_id: str, new_id: str) -> VisionPreset | None:
        preset = self._presets.get(preset_id)
        if not preset:
            return None
        if len(self._presets) >= MAX_PRESETS:
            return None
        now = time.time()
        dup = VisionPreset(
            preset_id=new_id,
            label=f"{preset.label} (copy)",
            description=preset.description,
            camera_id=preset.camera_id,
            mode=preset.mode,
            ptz=dict(preset.ptz),
            roi=dict(preset.roi),
            tracker_stack_id=preset.tracker_stack_id,
            quality_mode=preset.quality_mode,
            zones=[PresetZone(
                zone_id=f"zone_{uuid.uuid4().hex[:6]}",
                label=z.label,
                polygon=list(z.polygon),
                zone_type=z.zone_type,
            ) for z in preset.zones],
            created_at=now,
            updated_at=now,
        )
        self._presets[new_id] = dup
        self._persist()
        return dup

    def delete(self, preset_id: str) -> tuple[bool, list[str]]:
        """Delete a preset. Returns (success, affected_trigger_chain_ids)."""
        preset = self._presets.get(preset_id)
        if not preset:
            return False, []
        affected = list(preset.trigger_chain_ids)
        if self._active_preset_id == preset_id:
            self._active_preset_id = ""
        del self._presets[preset_id]
        self._persist()
        return True, affected

    def activate(self, preset_id: str) -> bool:
        if preset_id not in self._presets:
            return False
        self._active_preset_id = preset_id
        logger.info("preset activated: %s", preset_id)
        return True

    def get(self, preset_id: str) -> VisionPreset | None:
        return self._presets.get(preset_id)

    def list_all(self) -> list[VisionPreset]:
        return list(self._presets.values())

    def get_state_summary(self) -> dict[str, Any]:
        return {
            "active_preset_id": self._active_preset_id,
            "presets": {k: v.to_dict() for k, v in self._presets.items()},
            "count": len(self._presets),
        }

    def _persist(self) -> None:
        if not self._persist_path:
            return
        try:
            data = {k: v.to_dict() for k, v in self._presets.items()}
            with open(self._persist_path, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as exc:
            logger.warning("preset persist failed: %s", exc)

    def _load(self) -> None:
        try:
            with open(self._persist_path) as f:
                data = json.load(f)
            for k, v in data.items():
                self._presets[k] = VisionPreset.from_dict(v)
            logger.info("loaded %d presets from %s", len(self._presets), self._persist_path)
        except Exception as exc:
            logger.warning("preset load failed: %s", exc)


_preset_mgr: VisionPresetManager | None = None


def get_preset_manager() -> VisionPresetManager:
    global _preset_mgr
    if _preset_mgr is None:
        _preset_mgr = VisionPresetManager()
    return _preset_mgr
