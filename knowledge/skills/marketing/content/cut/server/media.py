"""Media I/O — upload, probe, and Range-capable streaming.

Upload (D4) streams in 64KB chunks with a running sha256 and a mid-write
size check, so a 5GB body is rejected after ~4GB written rather than after
the whole thing lands. The partial file is unlinked before the 413.

Streaming (D3) implements HTTP Range because `<video>` seeking requires it:
without a 206 response the browser can only play from the start.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import uuid
from pathlib import Path
from typing import Iterator

from substrate.execution.cpu_gate import gated_subprocess_run
from substrate.execution.media.media_processor import MediaProcessor

logger = logging.getLogger("cutstudio.media")

CHUNK = 64 * 1024
DEFAULT_MAX_UPLOAD = 4 * 1024**3  # 4GB

ALLOWED_TYPES = {
    "video/mp4",
    "video/webm",
    "video/quicktime",
    "video/x-matroska",
}

SAFE_EXT = re.compile(r"^\.[A-Za-z0-9]{1,5}$")


class UploadTooLarge(Exception):
    """Body exceeded the configured cap; the partial file was removed."""


class UnsupportedMedia(Exception):
    """Content-Type is not an accepted video/audio type."""


def max_upload_bytes() -> int:
    try:
        return int(os.environ.get("CUTSTUDIO_MAX_UPLOAD", "") or DEFAULT_MAX_UPLOAD)
    except ValueError:
        return DEFAULT_MAX_UPLOAD


def check_content_type(content_type: str | None) -> str:
    """Normalize and validate an upload content-type."""
    normalized = (content_type or "").split(";")[0].strip().lower()
    if normalized in ALLOWED_TYPES or normalized.startswith("audio/"):
        return normalized
    raise UnsupportedMedia("unsupported content type: %s" % (normalized or "missing"))


def safe_name(client_filename: str | None) -> str:
    """Server-generated filename — the client's name is display metadata only."""
    ext = Path(client_filename or "").suffix
    if not SAFE_EXT.match(ext):
        ext = ".mp4"
    return uuid.uuid4().hex[:12] + ext.lower()


async def stream_upload(upload_file, dest: Path, cap: int | None = None) -> dict:
    """Write an UploadFile to `dest` in chunks. Returns {size, sha256}."""
    limit = cap if cap is not None else max_upload_bytes()
    digest = hashlib.sha256()
    size = 0
    dest.parent.mkdir(parents=True, exist_ok=True)
    with open(dest, "wb") as out:
        while True:
            chunk = await upload_file.read(CHUNK)
            if not chunk:
                break
            size += len(chunk)
            if size > limit:
                out.close()
                dest.unlink(missing_ok=True)
                raise UploadTooLarge("upload exceeds %d bytes" % limit)
            digest.update(chunk)
            out.write(chunk)
    return {"size": size, "sha256": digest.hexdigest()}


# ── probing ──────────────────────────────────────────────────────────────
def probe(path: Path) -> dict:
    """ffprobe a media file: duration/width/height/codec/has_audio + fps.

    Dimensions come from the existing gated helper (do not rewrite it); fps
    is a separate gated call because `get_video_metadata` does not report it
    and the CMX3600 exporter needs a frame rate for timecodes.
    """
    meta = MediaProcessor().get_video_metadata(str(path))
    meta = dict(meta or {})
    meta["fps"] = probe_fps(path)
    if not meta.get("duration"):
        meta["duration"] = probe_duration(path)
    return meta


def probe_fps(path: Path, default: float = 30.0) -> float:
    """Read r_frame_rate ("30000/1001") and reduce it to a float."""
    result = gated_subprocess_run(
        [
            "ffprobe",
            "-v",
            "quiet",
            "-select_streams",
            "v:0",
            "-show_entries",
            "stream=r_frame_rate",
            "-of",
            "json",
            str(path),
        ],
        caller="cutstudio.ffprobe_fps",
        timeout=30,
    )
    if result is None or result.returncode != 0:
        return default
    try:
        streams = json.loads(result.stdout).get("streams") or []
        raw = streams[0].get("r_frame_rate", "")
        num, _, den = raw.partition("/")
        value = float(num) / float(den or 1)
        return round(value, 6) if value > 0 else default
    except (ValueError, TypeError, IndexError, AttributeError, ZeroDivisionError):
        return default


def probe_duration(path: Path, default: float = 0.0) -> float:
    """Container duration, used when the video-stream probe reports none
    (audio-only uploads have no video stream)."""
    result = gated_subprocess_run(
        [
            "ffprobe",
            "-v",
            "quiet",
            "-show_entries",
            "format=duration",
            "-of",
            "json",
            str(path),
        ],
        caller="cutstudio.ffprobe_duration",
        timeout=30,
    )
    if result is None or result.returncode != 0:
        return default
    try:
        return round(float(json.loads(result.stdout)["format"]["duration"]), 3)
    except (ValueError, TypeError, KeyError):
        return default


# ── Range streaming ──────────────────────────────────────────────────────
_RANGE_RE = re.compile(r"bytes=(\d*)-(\d*)")


def parse_range(header: str | None, size: int) -> tuple[int, int] | None:
    """Parse a Range header into an inclusive (start, end). None = whole file."""
    if not header:
        return None
    m = _RANGE_RE.match(header.strip())
    if not m:
        return None
    raw_start, raw_end = m.group(1), m.group(2)
    if raw_start == "" and raw_end == "":
        return None
    if raw_start == "":  # suffix range: last N bytes
        length = min(int(raw_end), size)
        if length <= 0:
            return None
        return size - length, size - 1
    start = int(raw_start)
    end = int(raw_end) if raw_end else size - 1
    end = min(end, size - 1)
    if start > end or start >= size:
        return None
    return start, end


def file_chunks(path: Path, start: int, end: int) -> Iterator[bytes]:
    """Yield [start, end] inclusive in CHUNK-sized pieces."""
    remaining = end - start + 1
    with open(path, "rb") as f:
        f.seek(start)
        while remaining > 0:
            data = f.read(min(CHUNK, remaining))
            if not data:
                break
            remaining -= len(data)
            yield data


CONTENT_TYPES = {
    ".mp4": "video/mp4",
    ".m4v": "video/mp4",
    ".webm": "video/webm",
    ".mov": "video/quicktime",
    ".mkv": "video/x-matroska",
    ".wav": "audio/wav",
    ".mp3": "audio/mpeg",
    ".m4a": "audio/mp4",
    ".srt": "text/plain",
}


def content_type_for(path: Path) -> str:
    return CONTENT_TYPES.get(path.suffix.lower(), "application/octet-stream")
