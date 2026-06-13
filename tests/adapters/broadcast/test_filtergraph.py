"""Unit tests for multi-source filtergraph builder + scene switch commands."""

from __future__ import annotations

import os
import sys

_WORKTREE = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, _WORKTREE)
sys.path.insert(1, os.environ.get("UMH_ROOT", "/opt/OS"))

import pytest

from adapters.broadcast.scene_model import (
    CompositeConfig,
    Scene,
    SourceEntry,
    SourceLayout,
)
from adapters.broadcast.filtergraph import (
    build_scene_switch_commands,
    overlay_filter_name,
    _build_filtergraph,
)


def _make_config(
    sources: list[SourceEntry] | None = None,
    scenes: list[Scene] | None = None,
    active_scene_id: str | None = None,
) -> CompositeConfig:
    if sources is None:
        sources = [
            SourceEntry(source_id="a", source_type="test_pattern", x=0, y=0, width=640, height=480),
            SourceEntry(source_id="b", source_type="test_pattern", x=640, y=0, width=320, height=240, z_order=1),
        ]
    return CompositeConfig(
        sources=sources,
        scenes=scenes or [],
        active_scene_id=active_scene_id,
        output_url="rtmp://example.com/live/test",
    )


class TestOverlayFilterName:
    def test_basic(self) -> None:
        assert overlay_filter_name("a") == "overlay@src_a"

    def test_numeric_id(self) -> None:
        assert overlay_filter_name("42") == "overlay@src_42"


class TestBuildFiltergraph:
    def test_two_sources_produces_zmq_and_overlays(self) -> None:
        cfg = _make_config()
        fg = _build_filtergraph(cfg.sources, cfg)

        assert "zmq" in fg
        assert "overlay@src_a" in fg
        assert "overlay@src_b" in fg
        assert "eval=frame" in fg
        assert "[out]" in fg
        assert "color=c=black:s=1920x1080" in fg

    def test_single_source_still_has_zmq(self) -> None:
        cfg = _make_config(sources=[
            SourceEntry(source_id="solo", source_type="test_pattern"),
        ])
        fg = _build_filtergraph(cfg.sources, cfg)

        assert "zmq" in fg
        assert "overlay@src_solo" in fg
        assert "[out]" in fg

    def test_three_sources_z_order_sorting(self) -> None:
        cfg = _make_config(sources=[
            SourceEntry(source_id="bg", source_type="test_pattern", z_order=0),
            SourceEntry(source_id="top", source_type="test_pattern", z_order=2),
            SourceEntry(source_id="mid", source_type="test_pattern", z_order=1),
        ])
        fg = _build_filtergraph(sorted(cfg.sources, key=lambda s: s.z_order), cfg)

        bg_pos = fg.index("overlay@src_bg")
        mid_pos = fg.index("overlay@src_mid")
        top_pos = fg.index("overlay@src_top")
        assert bg_pos < mid_pos < top_pos

    def test_disabled_source_has_enable_0(self) -> None:
        cfg = _make_config(
            sources=[
                SourceEntry(source_id="vis", source_type="test_pattern", enabled=True),
                SourceEntry(source_id="hid", source_type="test_pattern", enabled=False, z_order=1),
            ],
        )
        fg = _build_filtergraph(cfg.sources, cfg)

        assert "enable='0'" in fg
        assert "enable='1'" in fg

    def test_zmq_binds_loopback_not_wildcard(self) -> None:
        cfg = _make_config()
        fg = _build_filtergraph(cfg.sources, cfg)

        assert "127.0.0.1" in fg
        assert "tcp://*:5555" not in fg

    def test_scene_override_positions(self) -> None:
        cfg = _make_config(
            scenes=[Scene(
                scene_id="s1", name="Offset",
                source_layouts={
                    "a": SourceLayout(x=100, y=200, width=640, height=480),
                },
            )],
            active_scene_id="s1",
        )
        fg = _build_filtergraph(cfg.sources, cfg)

        assert "x=100" in fg
        assert "y=200" in fg


class TestBuildSceneSwitchCommands:
    def test_basic_switch(self) -> None:
        cfg = _make_config(
            scenes=[
                Scene(scene_id="s1", name="Side by Side", source_layouts={
                    "a": SourceLayout(x=0, y=0, width=640, height=480),
                    "b": SourceLayout(x=640, y=0, width=320, height=240),
                }),
                Scene(scene_id="s2", name="B Only", source_layouts={
                    "a": SourceLayout(x=0, y=0, enabled=False),
                    "b": SourceLayout(x=0, y=0, width=1920, height=1080),
                }),
            ],
            active_scene_id="s1",
        )

        cmds = build_scene_switch_commands(cfg, "s2")

        assert len(cmds) == 6
        a_cmds = [(f, c, a) for f, c, a in cmds if f == "overlay@src_a"]
        b_cmds = [(f, c, a) for f, c, a in cmds if f == "overlay@src_b"]

        assert ("overlay@src_a", "enable", "0") in a_cmds
        assert ("overlay@src_b", "enable", "1") in b_cmds
        assert ("overlay@src_b", "x", "0") in b_cmds
        assert ("overlay@src_b", "y", "0") in b_cmds

    def test_switch_to_unknown_scene_raises(self) -> None:
        cfg = _make_config(scenes=[
            Scene(scene_id="s1", name="Only"),
        ])
        with pytest.raises(ValueError, match="Scene not found"):
            build_scene_switch_commands(cfg, "nonexistent")

    def test_source_without_scene_layout_uses_defaults(self) -> None:
        cfg = _make_config(
            sources=[
                SourceEntry(source_id="a", source_type="test_pattern", x=10, y=20),
            ],
            scenes=[Scene(scene_id="s1", name="Sparse")],
        )
        cmds = build_scene_switch_commands(cfg, "s1")

        assert ("overlay@src_a", "x", "10") in cmds
        assert ("overlay@src_a", "y", "20") in cmds
        assert ("overlay@src_a", "enable", "1") in cmds

    def test_command_count_per_source(self) -> None:
        cfg = _make_config(
            sources=[
                SourceEntry(source_id="a", source_type="test_pattern"),
                SourceEntry(source_id="b", source_type="test_pattern", z_order=1),
                SourceEntry(source_id="c", source_type="test_pattern", z_order=2),
            ],
            scenes=[Scene(scene_id="s1", name="Three")],
        )
        cmds = build_scene_switch_commands(cfg, "s1")

        assert len(cmds) == 9


class TestIdValidation:
    def test_source_id_rejects_semicolons(self) -> None:
        with pytest.raises(Exception):
            SourceEntry(source_id="a;[evil]", source_type="test_pattern")

    def test_source_id_rejects_brackets(self) -> None:
        with pytest.raises(Exception):
            SourceEntry(source_id="a[0]", source_type="test_pattern")

    def test_source_id_rejects_spaces(self) -> None:
        with pytest.raises(Exception):
            SourceEntry(source_id="a b", source_type="test_pattern")

    def test_source_id_rejects_equals(self) -> None:
        with pytest.raises(Exception):
            SourceEntry(source_id="a=b", source_type="test_pattern")

    def test_source_id_rejects_long(self) -> None:
        with pytest.raises(Exception):
            SourceEntry(source_id="a" * 33, source_type="test_pattern")

    def test_source_id_accepts_valid(self) -> None:
        s = SourceEntry(source_id="cam-1_HD", source_type="test_pattern")
        assert s.source_id == "cam-1_HD"

    def test_scene_id_rejects_injection(self) -> None:
        with pytest.raises(Exception):
            Scene(scene_id="s1;zmq", name="evil")

    def test_scene_id_accepts_valid(self) -> None:
        s = Scene(scene_id="scene_01-A", name="Scene One")
        assert s.scene_id == "scene_01-A"

    def test_source_layout_key_rejects_injection(self) -> None:
        with pytest.raises(Exception):
            Scene(
                scene_id="s1", name="ok",
                source_layouts={"a;[evil]": SourceLayout()},
            )


class TestCompositeConfig:
    def test_resolve_layout_with_active_scene(self) -> None:
        cfg = _make_config(
            scenes=[Scene(
                scene_id="s1", name="Custom",
                source_layouts={"a": SourceLayout(x=999, y=888)},
            )],
            active_scene_id="s1",
        )
        layout = cfg.resolve_layout(cfg.sources[0])
        assert layout.x == 999
        assert layout.y == 888

    def test_resolve_layout_without_scene(self) -> None:
        cfg = _make_config()
        layout = cfg.resolve_layout(cfg.sources[0])
        assert layout.x == 0
        assert layout.y == 0

    def test_get_active_scene_none(self) -> None:
        cfg = _make_config()
        assert cfg.get_active_scene() is None

    def test_empty_sources_raises(self) -> None:
        from adapters.broadcast.filtergraph import build_composite_args
        cfg = _make_config(sources=[])
        with pytest.raises(ValueError, match="At least one source"):
            build_composite_args(cfg)
