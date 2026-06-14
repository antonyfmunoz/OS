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

def _get_allowed_media_dir() -> str:
    return os.environ.get(
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

    args.append(_validate_output_url(output_url))

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
        url = _validate_input_url(config["url"])
        return ["-i", url]

    if source_type == "file":
        path = config["path"]
        real_path = os.path.realpath(path)
        allowed_dir = os.path.realpath(_get_allowed_media_dir())
        if not real_path.startswith(allowed_dir + os.sep):
            raise ValueError(f"File path outside allowed media dir: {path}")
        args = ["-re", "-i", real_path]
        if config.get("loop", False):
            args = ["-stream_loop", "-1"] + args
        return args

    raise ValueError(f"Unknown source type: {source_type}")


_ALLOWED_OUTPUT_SCHEMES = frozenset({"rtmp", "rtmps", "srt"})


_TLS_SCHEMES = frozenset({"rtmps", "srt"})


def _validate_output_url(url: str) -> str:
    """Validate output URL — streaming protocols or safe local file paths."""
    _reject_control_chars(url)
    if url.startswith("-"):
        raise ValueError("Output URL must not start with '-'")

    if len(url) >= 2 and url[1] == ":" and url[0].isalpha():
        return _validate_file_output(url)

    parsed = urlparse(url)

    if parsed.scheme in _ALLOWED_OUTPUT_SCHEMES:
        hostname = parsed.hostname or ""
        if not hostname:
            raise ValueError("Output URL must have a hostname")
        if parsed.username or parsed.password:
            raise ValueError("Credentials must not be embedded in output URL — use env var side channel")
        if parsed.query:
            raise ValueError("Query parameters not allowed in output URL (push-only)")
        resolved_ip = _resolve_and_pin(hostname)
        return _rebuild_url(parsed, resolved_ip)

    if not parsed.scheme or parsed.scheme == "file":
        return _validate_file_output(url)

    raise ValueError(
        f"Disallowed output scheme: {parsed.scheme!r} "
        f"(allowed: {', '.join(sorted(_ALLOWED_OUTPUT_SCHEMES))} or local file)"
    )


def _validate_file_output(path: str) -> str:
    """Validate a local file output path — must be under allowed media dir."""
    if path.startswith("file:///"):
        path = path[len("file:///"):]
    elif path.startswith("file://"):
        path = path[len("file://"):]

    real_path = os.path.realpath(path)
    allowed_dir = os.path.realpath(_get_allowed_media_dir())
    if not real_path.startswith(allowed_dir + os.sep) and real_path != allowed_dir:
        raise ValueError(
            f"File output path outside allowed media dir ({allowed_dir}): {path}"
        )
    return real_path


def _validate_input_url(url: str) -> str:
    """Validate RTMP pull input URL — same hardening as output."""
    _reject_control_chars(url)
    if url.startswith("-"):
        raise ValueError("Input URL must not start with '-'")
    parsed = urlparse(url)
    if parsed.scheme not in _ALLOWED_RTMP_SCHEMES:
        raise ValueError(f"Disallowed URL scheme: {parsed.scheme}")
    hostname = parsed.hostname or ""
    if not hostname:
        raise ValueError("Input URL must have a hostname")
    resolved_ip = _resolve_and_pin(hostname)
    return _rebuild_url(parsed, resolved_ip)


def _rebuild_url(parsed: Any, resolved_ip: str) -> str:
    """Rebuild URL with pinned IP. Preserves hostname for TLS schemes (SNI)."""
    if parsed.scheme in _TLS_SCHEMES:
        _resolve_and_pin(parsed.hostname or "")
        host = parsed.hostname or ""
    else:
        host = f"[{resolved_ip}]" if ":" in resolved_ip else resolved_ip
    port_str = f":{parsed.port}" if parsed.port else ""
    return f"{parsed.scheme}://{host}{port_str}{parsed.path}"


def _reject_control_chars(url: str) -> None:
    """Reject whitespace/control characters that could smuggle FFmpeg options."""
    import re
    if re.search(r"[\x00-\x1f\x7f\s]", url):
        raise ValueError("URL contains control characters or whitespace")


def _resolve_and_pin(hostname: str) -> str:
    """Resolve hostname once, validate ALL addresses, return first valid IP.

    Pins the resolved IP to eliminate DNS rebinding (TOCTOU).
    Checks IPv4-mapped, IPv4-compatible, and 6to4 embedded addresses.
    """
    import ipaddress
    import socket
    try:
        infos = socket.getaddrinfo(hostname, None, socket.AF_UNSPEC, socket.SOCK_STREAM)
    except socket.gaierror:
        raise ValueError(f"Cannot resolve hostname: {hostname}")
    if not infos:
        raise ValueError(f"No addresses found for hostname: {hostname}")
    first_ip = None
    for info in infos:
        addr = ipaddress.ip_address(info[4][0])
        _reject_addr(addr, hostname)
        if isinstance(addr, ipaddress.IPv6Address):
            if addr.ipv4_mapped:
                _reject_addr(addr.ipv4_mapped, hostname)
            if addr.sixtofour:
                _reject_addr(addr.sixtofour, hostname)
            if addr in ipaddress.IPv6Network("::/96"):
                embedded = ipaddress.IPv4Address(int(addr) & 0xFFFFFFFF)
                _reject_addr(embedded, hostname)
        if first_ip is None:
            first_ip = str(addr)
    return first_ip


def _reject_addr(addr: Any, hostname: str) -> None:
    """Reject an address if it falls into any disallowed category."""
    if (addr.is_loopback or addr.is_private or addr.is_link_local
            or addr.is_reserved or addr.is_unspecified or addr.is_multicast):
        raise ValueError(f"Host resolves to disallowed address: {hostname} -> {addr}")
