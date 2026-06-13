"""Scene + SourceEntry models for multi-source compositing.

A Scene is a named preset: per-source positions, scale, and enable states.
Switching scenes = applying the preset via zmq commands to named overlays.
No FFmpeg restart required within a pre-declared source set.
"""

from __future__ import annotations

from typing import Any

import re

from pydantic import BaseModel, Field, field_validator

_SAFE_ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,32}$")


class SourceEntry(BaseModel):
    """One source in a scene — position, scale, and enable state."""

    source_id: str = Field(description="Unique ID within the broadcast session")

    @field_validator("source_id")
    @classmethod
    def _validate_source_id(cls, v: str) -> str:
        if not _SAFE_ID_RE.match(v):
            raise ValueError(
                f"source_id must be 1-32 alphanumeric/underscore/dash chars, got: {v!r}"
            )
        return v
    source_type: str = Field(description="test_pattern | camera | file | rtmp_pull")
    source_config: dict[str, Any] = Field(default_factory=dict)
    x: int = Field(default=0, description="Position X on canvas")
    y: int = Field(default=0, description="Position Y on canvas")
    width: int = Field(default=640, description="Rendered width")
    height: int = Field(default=480, description="Rendered height")
    z_order: int = Field(default=0, description="Layer index, higher = front")
    enabled: bool = Field(default=True, description="Visible in this scene")


class SourceLayout(BaseModel):
    """Position/visibility override for one source in one scene."""

    x: int = Field(default=0)
    y: int = Field(default=0)
    width: int = Field(default=640)
    height: int = Field(default=480)
    enabled: bool = Field(default=True)


class Scene(BaseModel):
    """A named parameter preset over the declared source set."""

    scene_id: str
    name: str

    @field_validator("scene_id")
    @classmethod
    def _validate_scene_id(cls, v: str) -> str:
        if not _SAFE_ID_RE.match(v):
            raise ValueError(
                f"scene_id must be 1-32 alphanumeric/underscore/dash chars, got: {v!r}"
            )
        return v
    source_layouts: dict[str, SourceLayout] = Field(
        default_factory=dict,
        description="Per-source layout overrides keyed by source_id",
    )

    @field_validator("source_layouts")
    @classmethod
    def _validate_layout_keys(cls, v: dict[str, SourceLayout]) -> dict[str, SourceLayout]:
        for key in v:
            if not _SAFE_ID_RE.match(key):
                raise ValueError(
                    f"source_layouts key must be a valid source_id, got: {key!r}"
                )
        return v


class CompositeConfig(BaseModel):
    """Full configuration for a multi-source composited broadcast."""

    sources: list[SourceEntry] = Field(
        description="All sources declared at launch (max fixed at start)",
    )
    scenes: list[Scene] = Field(
        default_factory=list,
        description="Named presets over the source set",
    )
    active_scene_id: str | None = Field(
        default=None,
        description="Currently active scene, None = use source defaults",
    )
    output_url: str = Field(description="RTMP destination URL")
    canvas_width: int = Field(default=1920)
    canvas_height: int = Field(default=1080)
    fps: int = Field(default=30, ge=1, le=120)
    video_codec: str = Field(default="libx264")
    video_bitrate: str = Field(default="4500k")
    audio_codec: str = Field(default="aac")
    audio_bitrate: str = Field(default="128k")
    keyframe_interval: int = Field(default=2, ge=1, le=10)
    preset: str = Field(default="veryfast")
    container_format: str = Field(default="flv")

    def get_active_scene(self) -> Scene | None:
        if self.active_scene_id is None:
            return None
        for s in self.scenes:
            if s.scene_id == self.active_scene_id:
                return s
        return None

    def resolve_layout(self, source: SourceEntry) -> SourceLayout:
        """Get the effective layout for a source — scene override or source defaults."""
        scene = self.get_active_scene()
        if scene and source.source_id in scene.source_layouts:
            return scene.source_layouts[source.source_id]
        return SourceLayout(
            x=source.x, y=source.y,
            width=source.width, height=source.height,
            enabled=source.enabled,
        )
