"""Google Meet caption JSONL bridge.

Canonical, append-only, bounded, operator-inspectable ingestion layer for Meet
captions. Writer half (this section) is owned by Subagent A; reader half is
extended by Subagent B.

Schema (locked):
    {"ts","text","speaker","meeting_code","source","event_id"}

Writer invariants:
- append-only
- one line per caption, LF-terminated
- atomic single-write per line (<= PIPE_BUF, POSIX O_APPEND)
- fsync after each append
- thread-safe and process-safe
- never raises on normal inputs; validation errors return structured dict
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Optional

BRIDGE_ROOT: Path = Path("/opt/OS/eos_ai/.substrate_station/meet_captions")
SCHEMA_VERSION = 1
SOURCE_TAG = "google_meet"

_SANITIZE_RE = re.compile(r"[^a-zA-Z0-9_-]")
_MAX_CODE_LEN = 64

_lock = threading.Lock()


def sanitize_meeting_code(code: str) -> str:
    """Sanitize a meeting code to a filesystem-safe slug.

    Replaces any char outside [a-zA-Z0-9_-] with '_', clips to 64 chars.
    Returns 'unknown' if the result is empty.
    """
    if not isinstance(code, str):
        return "unknown"
    cleaned = _SANITIZE_RE.sub("_", code).strip("_")
    cleaned = cleaned[:_MAX_CODE_LEN]
    return cleaned or "unknown"


def _ensure_root(root: Path) -> Path:
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    try:
        os.chmod(root, 0o700)
    except OSError:
        pass
    return root


def bridge_path_for(meeting_code: str, *, root: Optional[Path] = None) -> Path:
    """Return the JSONL file path for a given meeting code.

    Creates the bridge root directory with mode 0700 if missing.
    """
    r = Path(root) if root is not None else BRIDGE_ROOT
    _ensure_root(r)
    return r / f"{sanitize_meeting_code(meeting_code)}.jsonl"


def compute_event_id(
    ts: str, text: str, speaker: Optional[str], meeting_code: str
) -> str:
    """Deterministic 16-hex event id from the canonical tuple."""
    raw = f"{ts}|{text}|{speaker or ''}|{meeting_code}"
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16]


def now_iso_utc() -> str:
    """Current UTC time as ISO-8601 with trailing Z."""
    return (
        datetime.now(timezone.utc)
        .strftime("%Y-%m-%dT%H:%M:%S.%f")
        + "Z"
    )


class CaptionWriter:
    """Append-only writer for Meet caption JSONL bridge files."""

    def __init__(self, meeting_code: str, *, root: Optional[Path] = None) -> None:
        self._meeting_code = sanitize_meeting_code(meeting_code)
        self._root = Path(root) if root is not None else BRIDGE_ROOT
        self._path = bridge_path_for(self._meeting_code, root=self._root)

    @property
    def path(self) -> Path:
        return self._path

    @property
    def meeting_code(self) -> str:
        return self._meeting_code

    def append(
        self,
        text: str,
        *,
        speaker: Optional[str] = None,
        ts: Optional[str] = None,
        event_id: Optional[str] = None,
        extra: Optional[dict] = None,
    ) -> dict[str, Any]:
        """Append a single caption line. Never raises on normal inputs.

        Returns a status dict: {"status","event_id","path","detail"}.
        """
        if not isinstance(text, str) or not text.strip():
            return {
                "status": "empty_text",
                "event_id": None,
                "path": str(self._path),
                "detail": "text empty or not a string",
            }

        ts_val = ts or now_iso_utc()
        eid = event_id or compute_event_id(
            ts_val, text, speaker, self._meeting_code
        )

        record: dict[str, Any] = {}
        if extra and isinstance(extra, dict):
            record.update(extra)
        # Canonical keys always win.
        record["ts"] = ts_val
        record["text"] = text
        record["speaker"] = speaker
        record["meeting_code"] = self._meeting_code
        record["source"] = SOURCE_TAG
        record["event_id"] = eid

        try:
            line = json.dumps(record, ensure_ascii=False, separators=(",", ":"))
        except (TypeError, ValueError) as e:
            return {
                "status": "error",
                "event_id": eid,
                "path": str(self._path),
                "detail": f"json encode failed: {e}",
            }

        line_bytes = (line + "\n").encode("utf-8")

        with _lock:
            try:
                _ensure_root(self._root)
                fd = os.open(
                    self._path,
                    os.O_WRONLY | os.O_CREAT | os.O_APPEND,
                    0o600,
                )
                try:
                    os.write(fd, line_bytes)
                    os.fsync(fd)
                finally:
                    os.close(fd)
            except OSError as e:
                return {
                    "status": "error",
                    "event_id": eid,
                    "path": str(self._path),
                    "detail": f"write failed: {e}",
                }

        return {
            "status": "ok",
            "event_id": eid,
            "path": str(self._path),
            "detail": None,
        }

    def append_many(self, items: Iterable[dict]) -> dict[str, Any]:
        """Append many items. Each item is a dict with at least 'text'."""
        written = 0
        errors: list[dict[str, Any]] = []
        for item in items:
            if not isinstance(item, dict):
                errors.append({"status": "error", "detail": "not a dict"})
                continue
            result = self.append(
                item.get("text", ""),
                speaker=item.get("speaker"),
                ts=item.get("ts"),
                event_id=item.get("event_id"),
                extra={
                    k: v
                    for k, v in item.items()
                    if k not in {"text", "speaker", "ts", "event_id"}
                },
            )
            if result["status"] == "ok":
                written += 1
            else:
                errors.append(result)
        return {"written": written, "errors": errors}


def append_caption(
    meeting_code: str,
    text: str,
    *,
    speaker: Optional[str] = None,
    ts: Optional[str] = None,
    event_id: Optional[str] = None,
    extra: Optional[dict] = None,
    root: Optional[Path] = None,
) -> dict[str, Any]:
    """Module-level convenience: append a single caption for a meeting."""
    writer = CaptionWriter(meeting_code, root=root)
    return writer.append(
        text, speaker=speaker, ts=ts, event_id=event_id, extra=extra
    )


# === READER API (Subagent B) — appended below ===


from collections import deque  # noqa: E402
from typing import Callable  # noqa: E402

_CANONICAL_KEYS = ("ts", "text", "speaker", "meeting_code", "source", "event_id")
_READER_ERROR_CAP = 32
_DEFAULT_MAX_SEEN = 4096


class BridgeReadError(Exception):
    """Raised only from explicit validation helpers, never from read_new()."""


class CaptionReader:
    """Offset-tailing, dedupe-safe JSONL caption reader.

    Reads only NEW lines since last call, tolerates partial trailing lines,
    skips corrupt JSON, dedupes by event_id. Never raises from read_new().
    """

    def __init__(
        self,
        meeting_code: str,
        *,
        root: Optional[Path] = None,
        max_seen: int = _DEFAULT_MAX_SEEN,
        persist_offset: bool = False,
    ) -> None:
        self._meeting_code = sanitize_meeting_code(meeting_code)
        self._root = Path(root) if root is not None else BRIDGE_ROOT
        self._path = bridge_path_for(self._meeting_code, root=self._root)
        self._lock = threading.Lock()
        self._offset: int = 0
        self._max_seen = max(1, int(max_seen))
        self._seen: "deque[str]" = deque(maxlen=self._max_seen)
        self._seen_set: set[str] = set()
        self._persist_offset = bool(persist_offset)
        self._total_read = 0
        self._total_valid = 0
        self._total_skipped_corrupt = 0
        self._total_skipped_duplicate = 0
        self._recent_errors: "deque[dict]" = deque(maxlen=_READER_ERROR_CAP)
        if self._persist_offset:
            self._load_persisted_offset()

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def path(self) -> Path:
        return self._path

    @property
    def meeting_code(self) -> str:
        return self._meeting_code

    @property
    def offset(self) -> int:
        with self._lock:
            return self._offset

    @property
    def seen_count(self) -> int:
        with self._lock:
            return len(self._seen_set)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def reset_offset(self) -> None:
        """Rewind to 0 (useful for tests and full-replay)."""
        with self._lock:
            self._offset = 0
            if self._persist_offset:
                self._write_persisted_offset(0)

    def read_new(self, max_lines: int = 10) -> list[dict]:
        """Return up to max_lines NEW, valid, deduped caption dicts.

        Partial trailing lines are preserved for next call. Corrupt lines
        are skipped and counted. Never raises.
        """
        if not isinstance(max_lines, int) or max_lines <= 0:
            return []
        results: list[dict] = []
        with self._lock:
            try:
                if not self._path.exists():
                    return []
                file_size = self._path.stat().st_size
                if file_size < self._offset:
                    # File truncated/rotated — rewind.
                    self._offset = 0
                if file_size == self._offset:
                    return []
                with open(self._path, "rb") as f:
                    f.seek(self._offset)
                    remaining = file_size - self._offset
                    chunk = f.read(remaining)
                # Split strictly on LF to preserve partial-line semantics.
                # If chunk ends with \n, the final split element is "" and the
                # full chunk was consumed. Otherwise, the last element is a
                # partial line that must NOT be consumed.
                parts = chunk.split(b"\n")
                if chunk.endswith(b"\n"):
                    complete_lines = parts[:-1]  # drop trailing ""
                    consumed = len(chunk)
                else:
                    complete_lines = parts[:-1]
                    partial = parts[-1]
                    consumed = len(chunk) - len(partial)
                new_offset = self._offset + consumed
                bytes_walked = 0
                stopped_early = False
                for idx, raw_line in enumerate(complete_lines):
                    line_bytes = len(raw_line) + 1  # +1 for \n
                    if len(results) >= max_lines:
                        # Back off offset to start of this line.
                        new_offset = self._offset + bytes_walked
                        stopped_early = True
                        break
                    bytes_walked += line_bytes
                    self._total_read += 1
                    if not raw_line.strip():
                        # blank line — silently skip, advance
                        continue
                    try:
                        rec = json.loads(raw_line.decode("utf-8"))
                    except (ValueError, UnicodeDecodeError) as e:
                        self._total_skipped_corrupt += 1
                        self._recent_errors.append(
                            {
                                "kind": "corrupt_json",
                                "detail": str(e)[:200],
                                "preview": raw_line[:80].decode(
                                    "utf-8", errors="replace"
                                ),
                            }
                        )
                        continue
                    if not isinstance(rec, dict):
                        self._total_skipped_corrupt += 1
                        self._recent_errors.append(
                            {"kind": "not_a_dict", "detail": type(rec).__name__}
                        )
                        continue
                    eid = rec.get("event_id")
                    if not isinstance(eid, str) or not eid:
                        self._total_skipped_corrupt += 1
                        self._recent_errors.append(
                            {"kind": "missing_event_id", "detail": str(rec)[:120]}
                        )
                        continue
                    if eid in self._seen_set:
                        self._total_skipped_duplicate += 1
                        continue
                    # Dedupe bookkeeping with FIFO eviction.
                    if len(self._seen) == self._seen.maxlen:
                        evicted = self._seen.popleft()
                        self._seen_set.discard(evicted)
                    self._seen.append(eid)
                    self._seen_set.add(eid)
                    self._total_valid += 1
                    results.append(rec)
                self._offset = new_offset
                if self._persist_offset:
                    self._write_persisted_offset(self._offset)
            except OSError as e:
                self._recent_errors.append(
                    {"kind": "os_error", "detail": str(e)[:200]}
                )
                return results
        return results

    def stats(self) -> dict[str, Any]:
        """JSON-friendly snapshot."""
        with self._lock:
            file_exists = self._path.exists()
            file_size = self._path.stat().st_size if file_exists else 0
            return {
                "path": str(self._path),
                "meeting_code": self._meeting_code,
                "offset": self._offset,
                "total_read": self._total_read,
                "total_valid": self._total_valid,
                "total_skipped_corrupt": self._total_skipped_corrupt,
                "total_skipped_duplicate": self._total_skipped_duplicate,
                "recent_errors": list(self._recent_errors),
                "file_exists": file_exists,
                "file_size": file_size,
                "seen_count": len(self._seen_set),
                "persist_offset": self._persist_offset,
            }

    def drain_all(self, *, hard_cap: int = 1000) -> list[dict]:
        """Drain up to hard_cap new entries across multiple internal batches."""
        if not isinstance(hard_cap, int) or hard_cap <= 0:
            return []
        drained: list[dict] = []
        # Use batches of 64 for efficiency.
        batch = 64
        while len(drained) < hard_cap:
            remaining = hard_cap - len(drained)
            got = self.read_new(max_lines=min(batch, remaining))
            if not got:
                break
            drained.extend(got)
        return drained[:hard_cap]

    # ------------------------------------------------------------------
    # Offset persistence (optional)
    # ------------------------------------------------------------------

    def _offset_sidecar_path(self) -> Path:
        return self._path.with_suffix(self._path.suffix + ".offset")

    def _load_persisted_offset(self) -> None:
        side = self._offset_sidecar_path()
        try:
            if side.exists():
                text = side.read_text(encoding="utf-8").strip()
                if text:
                    val = int(text)
                    if val >= 0:
                        self._offset = val
        except (OSError, ValueError):
            self._offset = 0

    def _write_persisted_offset(self, value: int) -> None:
        side = self._offset_sidecar_path()
        tmp = side.with_suffix(side.suffix + ".tmp")
        try:
            _ensure_root(self._root)
            tmp.write_text(str(int(value)), encoding="utf-8")
            os.replace(tmp, side)
        except OSError as e:
            self._recent_errors.append(
                {"kind": "offset_persist_failed", "detail": str(e)[:200]}
            )


def make_bridge_hook(
    meeting_code: str,
    *,
    root: Optional[Path] = None,
    reader: Optional[CaptionReader] = None,
    batch_size: int = 1,
) -> Callable[[], Optional[dict]]:
    """Build a hook callable matching GoogleMeetSource's hook contract.

    Each hook call returns the OLDEST not-yet-returned entry in the source
    shape {"text","user_id","participant_name","metadata"} or None if the
    bridge has no new data. An internal micro-queue (<= batch_size) lets
    one read_new() satisfy multiple hook polls.
    """
    r = reader if reader is not None else CaptionReader(meeting_code, root=root)
    bs = max(1, int(batch_size))
    queue: "deque[dict]" = deque()
    qlock = threading.Lock()

    def _to_source_shape(rec: dict) -> dict:
        text = rec.get("text", "")
        speaker = rec.get("speaker")
        metadata = {
            "ts": rec.get("ts"),
            "meeting_code": rec.get("meeting_code"),
            "source": rec.get("source"),
            "event_id": rec.get("event_id"),
        }
        # Preserve any non-canonical keys too.
        for k, v in rec.items():
            if k not in _CANONICAL_KEYS and k not in metadata:
                metadata[k] = v
        return {
            "text": text,
            "user_id": speaker if isinstance(speaker, str) and speaker else None,
            "participant_name": speaker,
            "metadata": metadata,
        }

    def hook() -> Optional[dict]:
        with qlock:
            if queue:
                return queue.popleft()
        # Refill.
        batch = r.read_new(max_lines=bs)
        if not batch:
            return None
        with qlock:
            for rec in batch:
                queue.append(_to_source_shape(rec))
            if queue:
                return queue.popleft()
        return None

    # Attach reader for introspection by callers/tests.
    hook.reader = r  # type: ignore[attr-defined]
    return hook


__all__ = [
    "BRIDGE_ROOT",
    "SCHEMA_VERSION",
    "SOURCE_TAG",
    "sanitize_meeting_code",
    "bridge_path_for",
    "compute_event_id",
    "now_iso_utc",
    "CaptionWriter",
    "append_caption",
    "CaptionReader",
    "BridgeReadError",
    "make_bridge_hook",
]
