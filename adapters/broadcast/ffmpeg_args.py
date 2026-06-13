"""Pure deterministic config -> FFmpeg CLI argument list.

No spawning.  No subprocess.  No libav imports.  CLI binary only.
Unit-testable in isolation.
"""

from __future__ import annotations

import os
from typing import Any
from urllib.parse import urlparse

_ALLOWED_LAVFI_PATTERNS = frozenset({
    "testsrc", "testsrc2", "smptebars", "smptehdbars",
    "color", "rgbtestsrc", "pal75bars", "pal100bars",
})

_ALLOWED_RTMP_SCHEMES = frozenset({"rtmp", "rtmps", "srt"})

_ALLOWED_MEDIA_DIR = os.environ.get(
    "UMH_BROADCAST_MEDIA_DIR",
    os.path.join(os.environ.get("UMH_ROOT", "/opt/OS"), "data", "media"),
)


def build_args(
    *,
    source_type: str,
    source_config: dict[str, Any],
    output_url: str,
    video_codec: str = "libx264",
    video_bitrate: str = "4500k",
    audio_codec: str = "aac",
    audio_bitrate: str = "128k",
    resolution: str = "1920x1080",
    fps: int = 30,
    keyframe_interval: int = 2,
    preset: str = "veryfast",
    container_format: str = "flv",
    ffmpeg_binary: str = "ffmpeg",
) -> list[str]:
    """Build the full FFmpeg CLI argument list from a broadcast config.

    Returns a list suitable for subprocess/asyncio.create_subprocess_exec.
    """
    args: list[str] = [ffmpeg_binary, "-y"]

    args.extend(_input_args(source_type, source_config, fps, resolution))

    args.extend([
        "-c:v", video_codec,
        "-b:v", video_bitrate,
        "-preset", preset,
        "-g", str(fps * keyframe_interval),
        "-keyint_min", str(fps * keyframe_interval),
    ])

    if video_codec == "libx264":
        args.extend(["-profile:v", "high", "-level", "4.1"])
        args.extend(["-pix_fmt", "yuv420p"])

    args.extend([
        "-c:a", audio_codec,
        "-b:a", audio_bitrate,
        "-ar", "44100",
    ])

    args.extend(["-f", container_format])

    args.extend(["-progress", "pipe:1", "-stats_period", "1"])

    args.append(output_url)

    return args


def _input_args(
    source_type: str,
    config: dict[str, Any],
    fps: int,
    resolution: str,
) -> list[str]:
    """Build input-side arguments based on source type."""
    if source_type == "test_pattern":
        duration = config.get("duration", "")
        pattern = config.get("pattern", "testsrc2")
        if pattern not in _ALLOWED_LAVFI_PATTERNS:
            raise ValueError(f"Disallowed lavfi pattern: {pattern}")
        lavfi = f"{pattern}=size={resolution}:rate={fps}"
        args = ["-re", "-f", "lavfi", "-i", lavfi]
        if not config.get("has_audio", True):
            args.extend(["-f", "lavfi", "-i", "sine=frequency=440:sample_rate=44100"])
        else:
            args.extend(["-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo"])
        if duration:
            args.extend(["-t", str(int(duration))])
        return args

    if source_type == "camera":
        device = config.get("device", "/dev/video0")
        real_dev = os.path.realpath(device)
        if not real_dev.startswith("/dev/video"):
            raise ValueError(f"Invalid camera device: {device}")
        return [
            "-f", "v4l2",
            "-video_size", resolution,
            "-framerate", str(fps),
            "-i", real_dev,
            "-f", "pulse", "-i", "default",
        ]

    if source_type == "rtmp_pull":
        url = config["url"]
        parsed = urlparse(url)
        if parsed.scheme not in _ALLOWED_RTMP_SCHEMES:
            raise ValueError(f"Disallowed URL scheme: {parsed.scheme}")
        _reject_private_host(parsed.hostname or "")
        return ["-i", url]

    if source_type == "file":
        path = config["path"]
        real_path = os.path.realpath(path)
        allowed_dir = os.path.realpath(_ALLOWED_MEDIA_DIR)
        if not real_path.startswith(allowed_dir + os.sep):
            raise ValueError(f"File path outside allowed media dir: {path}")
        args = ["-re", "-i", real_path]
        if config.get("loop", False):
            args = ["-stream_loop", "-1"] + args
        return args

    raise ValueError(f"Unknown source type: {source_type}")


def _reject_private_host(hostname: str) -> None:
    """Reject loopback, private, and link-local addresses to prevent SSRF."""
    import ipaddress
    import socket
    try:
        infos = socket.getaddrinfo(hostname, None, socket.AF_UNSPEC, socket.SOCK_STREAM)
    except socket.gaierror:
        raise ValueError(f"Cannot resolve hostname: {hostname}")
    for info in infos:
        addr = ipaddress.ip_address(info[4][0])
        if addr.is_loopback or addr.is_private or addr.is_link_local:
            raise ValueError(f"RTMP pull target resolves to private/loopback address: {hostname}")
