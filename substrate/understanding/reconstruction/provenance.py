"""Provenance & persistence primitives for the reconstruction subsystem.

Provides:
  - canonical_json / content_hash : deterministic serialization + SHA-256.
  - file_sha256                   : sha256 of a file's actual bytes (manifest hashing).
  - ActivityRecord                : PROV-aligned activity (who/what/when/used/generated).
  - JsonlAppender                 : append-only JSONL writer, process-local locked, fsync'd.
  - atomic_write_json             : same-dir tmp + os.replace atomic replacement.
  - RunLayout                     : run-scoped directory layout under <self_model_root>/runs/.

Writes ONLY run-scoped instance artifacts under the caller-supplied self-model
root (canonically data/world_models/self/runs/<run_id>/). Never overwrites an
earlier run (raises unless explicit resume).

UMH substrate subsystem. Instance-agnostic.
"""

from __future__ import annotations

import hashlib
import json
import os
import threading
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Optional

try:  # POSIX advisory locking when available; degrade cleanly otherwise.
    import fcntl
except Exception:  # pragma: no cover - non-POSIX
    fcntl = None  # type: ignore[assignment]

# Process-local lock table keyed by absolute path — guards concurrent appends
# within THIS process. fcntl adds cross-process advisory locking on POSIX.
_LOCKS: dict[str, threading.Lock] = {}
_LOCKS_GUARD = threading.Lock()


def _lock_for(path: str) -> threading.Lock:
    with _LOCKS_GUARD:
        lk = _LOCKS.get(path)
        if lk is None:
            lk = threading.Lock()
            _LOCKS[path] = lk
        return lk


def _coerce(o: Any) -> Any:
    to_dict = getattr(o, "to_dict", None)
    if callable(to_dict):
        return to_dict()
    if isinstance(o, (set, frozenset)):
        return sorted(o, key=repr)
    if isinstance(o, (bytes, bytearray)):
        return o.decode("utf-8", errors="replace")
    raise TypeError(f"not JSON-serializable: {type(o).__name__}")


def canonical_json(obj: Any) -> str:
    """Deterministic JSON: sorted keys, compact separators, ASCII-stable."""
    return json.dumps(
        obj,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        default=_coerce,
    )


def content_hash(obj: Any) -> str:
    """SHA-256 hex of an object. bytes hashed directly; else canonical_json."""
    if isinstance(obj, (bytes, bytearray)):
        data = bytes(obj)
    elif isinstance(obj, str):
        data = obj.encode("utf-8")
    else:
        data = canonical_json(obj).encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def file_sha256(path: str | os.PathLike[str]) -> str:
    """SHA-256 hex of a file's actual bytes (bounded, streamed)."""
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


@dataclass(frozen=True)
class ActivityRecord:
    """PROV-aligned activity: an agent performing a kind of work over inputs.

    Lifecycle: the id is derivable BEFORE the activity's outputs exist (identity
    excludes used/generated lineage), so records emitted during the activity can
    reference it; the COMPLETED ActivityRecord — same id, with used_source_ids
    and generated_record_ids populated — is the one appended to
    activities.jsonl. The PROV chain is therefore real lineage, not nominal.
    """

    activity_kind: str  # acquisition | extraction | transformation | evaluation
    agent_id: str  # human:<id> | model:<id> | script:<path>
    run_id: str
    code_version: str = ""
    started_at: Optional[str] = None
    ended_at: Optional[str] = None
    used_source_ids: tuple[str, ...] = ()
    generated_record_ids: tuple[str, ...] = ()
    schema_version: str = "adl-v1"

    def identity_fields(self) -> dict[str, Any]:
        # Lineage (used/generated) is deliberately NOT identity: the completed
        # record must keep the id that in-flight records already referenced.
        return {
            "activity_kind": self.activity_kind,
            "agent_id": self.agent_id,
            "code_version": self.code_version,
            "started_at": self.started_at,
            "run_id": self.run_id,
        }

    @property
    def id(self) -> str:
        payload = canonical_json(self.identity_fields())
        return "activity:" + hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["used_source_ids"] = list(self.used_source_ids)
        d["generated_record_ids"] = list(self.generated_record_ids)
        d["id"] = self.id
        return d


class JsonlAppender:
    """Append-only JSONL writer with process-local + advisory locking and fsync.

    Each record is written as one canonical-JSON line. The file is opened in
    append mode per write so concurrent appenders never truncate each other.
    """

    def __init__(self, path: str | os.PathLike[str]) -> None:
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)

    @property
    def path(self) -> Path:
        return self._path

    def append(self, record: Any) -> str:
        """Append one record; returns the canonical JSON line written."""
        line = canonical_json(record)
        key = str(self._path.resolve())
        with _lock_for(key):
            with open(self._path, "a", encoding="utf-8") as fh:
                if fcntl is not None:
                    fcntl.flock(fh.fileno(), fcntl.LOCK_EX)
                try:
                    fh.write(line + "\n")
                    fh.flush()
                    os.fsync(fh.fileno())
                finally:
                    if fcntl is not None:
                        fcntl.flock(fh.fileno(), fcntl.LOCK_UN)
        return line

    def append_all(self, records: list[Any]) -> int:
        for rec in records:
            self.append(rec)
        return len(records)

    def read_all(self) -> list[dict[str, Any]]:
        if not self._path.exists():
            return []
        out: list[dict[str, Any]] = []
        with open(self._path, "r", encoding="utf-8") as fh:
            for raw in fh:
                raw = raw.strip()
                if raw:
                    out.append(json.loads(raw))
        return out


def atomic_write_json(path: str | os.PathLike[str], obj: Any) -> None:
    """Atomically write canonical JSON to path via same-dir tmp + os.replace."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_name(f".{target.name}.tmp.{os.getpid()}")
    with open(tmp, "w", encoding="utf-8") as fh:
        fh.write(canonical_json(obj))
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp, target)


# Canonical run artifact filenames.
RUN_ARTIFACTS: tuple[str, ...] = (
    "manifest.json",
    "sources.jsonl",
    "activities.jsonl",
    "observations.jsonl",
    "claims.jsonl",
    "identity_resolutions.jsonl",
    "model.json",
    "coverage.json",
    "divergence.json",
    "test_report.json",  # v1.2: run copy of the pytest evidence artifact (optional)
    "acceptance.json",
    "convergence.md",
    "report.md",
)


class RunLayout:
    """Run-scoped directory layout under <self_model_root>/runs/<run_id>/.

    self_model_root is the UNAMBIGUOUS self-model root (canonically
    <repo>/data/world_models/self) — no path segments are appended to it besides
    runs/<run_id>, so a run always lands exactly where the caller says.

    run_id is caller-supplied (tests pass a fixed id for determinism; production
    callers pass their own). A run directory is never silently reused: create()
    raises if the directory already exists and is non-empty unless resume=True.
    """

    def __init__(self, run_id: str, *, self_model_root: str | os.PathLike[str]) -> None:
        if not run_id or "/" in run_id or "\\" in run_id or run_id in (".", ".."):
            raise ValueError(f"invalid run_id: {run_id!r}")
        self.run_id = run_id
        self.self_root = Path(self_model_root)
        self.runs_root = self.self_root / "runs"
        self.run_dir = self.runs_root / run_id

    def path(self, artifact: str) -> Path:
        if artifact not in RUN_ARTIFACTS:
            raise KeyError(f"unknown run artifact: {artifact!r}")
        return self.run_dir / artifact

    def create(self, resume: bool = False) -> "RunLayout":
        if self.run_dir.exists() and any(self.run_dir.iterdir()) and not resume:
            raise FileExistsError(
                f"run dir already exists and is non-empty: {self.run_dir} "
                f"(pass resume=True to append to an existing run)"
            )
        self.run_dir.mkdir(parents=True, exist_ok=True)
        return self

    def appender(self, artifact: str) -> "JsonlAppender":
        if not artifact.endswith(".jsonl"):
            raise ValueError(f"appender requires a .jsonl artifact, got {artifact!r}")
        return JsonlAppender(self.path(artifact))

    def update_latest_pointer(self) -> None:
        """Atomically point data/world_models/self/latest.json at this run."""
        atomic_write_json(
            self.self_root / "latest.json",
            {"run_id": self.run_id, "run_dir": str(self.run_dir)},
        )
