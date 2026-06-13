"""Filtergraph builder — scene config -> FFmpeg -filter_complex args.

Generates a compositing filtergraph with:
- Black canvas at target resolution
- Per-source scale + named overlay (overlay@src_{id})
- zmq filter for live parameter control
- eval=frame on overlays so zmq changes apply per-frame

The zmq filter binds to tcp://127.0.0.1:5555 (loopback only). Named overlays
are addressable by zmq commands: "overlay@src_{id} x 100" etc.
"""

from __future__ import annotations

import os
from typing import Any

from adapters.broadcast.scene_model import CompositeConfig, SourceEntry, SourceLayout

_ALLOWED_LAVFI_PATTERNS = frozenset({
    "testsrc", "testsrc2", "smptebars", "smptehdbars",
    "color", "rgbtestsrc", "pal75bars", "pal100bars",
})

_ALLOWED_RTMP_SCHEMES = frozenset({"rtmp", "rtmps", "srt"})

_ALLOWED_MEDIA_DIR = os.environ.get(
    "UMH_BROADCAST_MEDIA_DIR",
    os.path.join(os.environ.get("UMH_ROOT", "/opt/OS"), "data", "media"),
)


def overlay_filter_name(source_id: str) -> str:
    """Canonical overlay filter name for a source — used by zmq commands."""
    return f"overlay@src_{source_id}"


def build_composite_args(config: CompositeConfig) -> list[str]:
    """Build full FFmpeg CLI args for a multi-source composited broadcast.

    Returns a list suitable for asyncio.create_subprocess_exec.
    """
    sources = sorted(config.sources, key=lambda s: s.z_order)
    if not sources:
        raise ValueError("At least one source is required")

    args: list[str] = ["ffmpeg", "-y"]

    for src in sources:
        args.extend(_source_input_args(src, config.fps, config.canvas_width, config.canvas_height))

    args.extend(["-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo"])

    fg = _build_filtergraph(sources, config)
    args.extend(["-filter_complex", fg])

    args.extend(["-map", "[out]", "-map", f"{len(sources)}:a"])

    args.extend([
        "-c:v", config.video_codec,
        "-b:v", config.video_bitrate,
        "-preset", config.preset,
        "-g", str(config.fps * config.keyframe_interval),
        "-keyint_min", str(config.fps * config.keyframe_interval),
    ])

    if config.video_codec == "libx264":
        args.extend(["-profile:v", "high", "-level", "4.1", "-pix_fmt", "yuv420p"])

    args.extend([
        "-c:a", config.audio_codec,
        "-b:a", config.audio_bitrate,
        "-ar", "44100",
    ])

    args.extend(["-f", config.container_format])
    args.extend(["-progress", "pipe:1", "-stats_period", "1"])

    from adapters.broadcast.ffmpeg_args import _validate_output_url
    args.append(_validate_output_url(config.output_url))

    return args


def _source_input_args(
    src: SourceEntry, fps: int, canvas_w: int, canvas_h: int,
) -> list[str]:
    """Generate -i args for a single source."""
    st = src.source_type
    cfg = src.source_config

    if st == "test_pattern":
        pattern = cfg.get("pattern", "testsrc2")
        if pattern not in _ALLOWED_LAVFI_PATTERNS:
            raise ValueError(f"Disallowed lavfi pattern: {pattern}")
        lavfi = f"{pattern}=size={src.width}x{src.height}:rate={fps}"
        return ["-re", "-f", "lavfi", "-i", lavfi]

    if st == "camera":
        device = cfg.get("device", "/dev/video0")
        real_dev = os.path.realpath(device)
        if not real_dev.startswith("/dev/video"):
            raise ValueError(f"Invalid camera device: {device}")
        return [
            "-f", "v4l2",
            "-video_size", f"{src.width}x{src.height}",
            "-framerate", str(fps),
            "-i", real_dev,
        ]

    if st == "rtmp_pull":
        from adapters.broadcast.ffmpeg_args import _validate_input_url
        url = _validate_input_url(cfg["url"])
        return ["-i", url]

    if st == "file":
        path = cfg["path"]
        real_path = os.path.realpath(path)
        allowed_dir = os.path.realpath(_ALLOWED_MEDIA_DIR)
        if not real_path.startswith(allowed_dir + os.sep):
            raise ValueError(f"File path outside allowed media dir: {path}")
        file_args = ["-re", "-i", real_path]
        if cfg.get("loop", False):
            file_args = ["-stream_loop", "-1"] + file_args
        return file_args

    raise ValueError(f"Unknown source type: {st}")


def _build_filtergraph(
    sources: list[SourceEntry],
    config: CompositeConfig,
) -> str:
    """Build the -filter_complex string.

    Layout:
      color=black canvas [canvas]
      per-source: [N:v]scale=WxH[sN]
      zmq filter on the chain for live control
      per-source: overlay@src_{id} with eval=frame

    zmq binds to loopback (127.0.0.1:5555) — not exposed to network.
    Double-escaped colons required by FFmpeg's filtergraph parser.
    """
    parts: list[str] = []

    parts.append(
        f"color=c=black:s={config.canvas_width}x{config.canvas_height}"
        f":rate={config.fps}[canvas]"
    )

    for i, src in enumerate(sources):
        layout = config.resolve_layout(src)
        parts.append(f"[{i}:v]scale={layout.width}:{layout.height}[s{i}]")

    prev_label = "canvas"

    for idx, src in enumerate(sources):
        layout = config.resolve_layout(src)
        out_label = f"c{idx}"
        enable_val = 1 if layout.enabled else 0
        overlay_name = overlay_filter_name(src.source_id)

        if idx == 0:
            zmq_bind = "tcp\\\\://127.0.0.1\\\\:5555"
            parts.append(f"[{prev_label}]zmq=bind_address={zmq_bind}[z]")
            chain_in = "z"
        else:
            chain_in = prev_label

        if idx == len(sources) - 1:
            out_label = "out"

        parts.append(
            f"[{chain_in}][s{idx}]{overlay_name}"
            f"=x={layout.x}:y={layout.y}"
            f":enable='{enable_val}'"
            f":eval=frame"
            f"[{out_label}]"
        )
        prev_label = out_label

    return ";".join(parts)


def build_scene_switch_commands(
    config: CompositeConfig, target_scene_id: str,
) -> list[tuple[str, str, str]]:
    """Compute the zmq commands needed to switch to a target scene.

    Returns list of (filter_name, command, arg) tuples.
    """
    target_scene = None
    for s in config.scenes:
        if s.scene_id == target_scene_id:
            target_scene = s
            break
    if target_scene is None:
        raise ValueError(f"Scene not found: {target_scene_id}")

    commands: list[tuple[str, str, str]] = []
    for src in config.sources:
        fname = overlay_filter_name(src.source_id)
        if src.source_id in target_scene.source_layouts:
            layout = target_scene.source_layouts[src.source_id]
        else:
            layout = SourceLayout(
                x=src.x, y=src.y,
                width=src.width, height=src.height,
                enabled=src.enabled,
            )
        commands.append((fname, "x", str(layout.x)))
        commands.append((fname, "y", str(layout.y)))
        commands.append((fname, "enable", "1" if layout.enabled else "0"))

    return commands
