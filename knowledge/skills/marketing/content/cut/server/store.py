"""Project storage — the filesystem IS the database.

Layout under UMH_ROOT/data/cutstudio/projects/<id>/:
    project.json   {id, name, media, duration, width, height, fps, created, edl_rev}
    <media file>   the uploaded source (server-generated name)
    transcript.json
    <media>.srt
    edl.json
    renders/       rendered outputs + their regenerated .srt sidecars

Everything is plain text except the media, so a project is inspectable,
diffable, and rsync-able to the Beast without a migration story.
"""

from __future__ import annotations

import json
import os
import shutil
import time
import uuid
from pathlib import Path

MIN_FREE_GB = 10.0
RENDER_PRUNE_DAYS = 14


class StoreError(Exception):
    """Raised for project-level storage failures (missing project, bad rev)."""


class RevMismatch(StoreError):
    """The caller's If-Match rev is not the current rev (optimistic lock)."""


def root() -> Path:
    """Project root. Read from env each call so tests can relocate it."""
    return Path(os.environ.get("UMH_ROOT", "/opt/OS")) / "data" / "cutstudio" / "projects"


def project_dir(project_id: str) -> Path:
    """Resolve a project directory, refusing anything that escapes the root."""
    base = root().resolve()
    candidate = (base / project_id).resolve()
    if candidate != base and base not in candidate.parents:
        raise StoreError("invalid project id")
    return candidate


def free_gb(path: Path | None = None) -> float:
    target = path or root()
    probe = target
    while not probe.exists() and probe != probe.parent:
        probe = probe.parent
    return shutil.disk_usage(str(probe)).free / (1024**3)


def disk_ok() -> bool:
    return free_gb() >= MIN_FREE_GB


def new_id() -> str:
    return uuid.uuid4().hex[:12]


# ── project.json ─────────────────────────────────────────────────────────
def read_meta(project_id: str) -> dict:
    path = project_dir(project_id) / "project.json"
    if not path.exists():
        raise StoreError("project not found: %s" % project_id)
    with open(path) as f:
        return json.load(f)


def write_meta(project_id: str, meta: dict) -> dict:
    d = project_dir(project_id)
    d.mkdir(parents=True, exist_ok=True)
    (d / "project.json").write_text(json.dumps(meta, indent=1))
    return meta


def create(project_id: str, name: str, media_name: str, probe: dict) -> dict:
    """Write the initial project.json from an ffprobe result."""
    meta = {
        "id": project_id,
        "name": name,
        "media": media_name,
        "duration": round(float(probe.get("duration") or 0.0), 3),
        "width": int(probe.get("width") or 0),
        "height": int(probe.get("height") or 0),
        "fps": float(probe.get("fps") or 30.0),
        "created": time.time(),
        "edl_rev": 0,
    }
    return write_meta(project_id, meta)


def render_names(project_id: str) -> list[str]:
    """Rendered output filenames for a project.

    Bare names, not objects: a name is all the media-token endpoint needs
    (`media-token?name=<file>`), and stat()-ing every render on every list
    call would cost a syscall per file for metadata no caller reads.
    """
    d = project_dir(project_id) / "renders"
    return sorted(p.name for p in d.glob("*.mp4")) if d.exists() else []


def summarize(meta: dict, project_dir_path: Path) -> dict:
    """The canonical project summary shape.

    ONE definition, used by both the list and the single-project reads, so
    the two can never drift apart again (they did: the list omitted `media`,
    the detail read omitted `renders`, and a client had to call both).
    """
    project_id = meta.get("id", project_dir_path.name)
    renders_dir_path = project_dir_path / "renders"
    return {
        "id": project_id,
        "name": meta.get("name", project_dir_path.name),
        "media": meta.get("media", ""),
        "created": meta.get("created", 0),
        "duration": meta.get("duration", 0),
        "width": meta.get("width", 0),
        "height": meta.get("height", 0),
        "fps": meta.get("fps", 0),
        "edl_rev": meta.get("edl_rev", 0),
        "has_transcript": (project_dir_path / "transcript.json").exists(),
        "renders": (
            sorted(p.name for p in renders_dir_path.glob("*.mp4"))
            if renders_dir_path.exists()
            else []
        ),
    }


def list_projects() -> list[dict]:
    base = root()
    if not base.exists():
        return []
    out = []
    for d in sorted(base.iterdir()):
        meta_path = d / "project.json"
        if not meta_path.is_dir() and meta_path.exists():
            try:
                with open(meta_path) as f:
                    meta = json.load(f)
            except (ValueError, OSError):
                continue
            out.append(summarize(meta, d))
    out.sort(key=lambda p: p.get("created", 0), reverse=True)
    return out


def delete(project_id: str) -> None:
    d = project_dir(project_id)
    if not d.exists():
        raise StoreError("project not found: %s" % project_id)
    shutil.rmtree(d)


def media_path(project_id: str) -> Path:
    meta = read_meta(project_id)
    return project_dir(project_id) / meta["media"]


def renders_dir(project_id: str) -> Path:
    d = project_dir(project_id) / "renders"
    d.mkdir(parents=True, exist_ok=True)
    return d


# ── EDL with optimistic locking ──────────────────────────────────────────
def read_edl(project_id: str) -> tuple[dict, int]:
    path = project_dir(project_id) / "edl.json"
    if not path.exists():
        raise StoreError("edl not found: %s" % project_id)
    with open(path) as f:
        edl = json.load(f)
    return edl, int(read_meta(project_id).get("edl_rev", 0))


def write_edl(project_id: str, edl: dict, if_match: int | None = None) -> tuple[dict, int]:
    """Persist an EDL, bumping the revision.

    `if_match=None` is an unconditional write (used when creating a project);
    any integer must equal the current rev or RevMismatch is raised.
    """
    meta = read_meta(project_id)
    current = int(meta.get("edl_rev", 0))
    if if_match is not None and int(if_match) != current:
        raise RevMismatch("edl rev is %d, not %s" % (current, if_match))
    (project_dir(project_id) / "edl.json").write_text(json.dumps(edl, indent=1))
    meta["edl_rev"] = current + 1
    write_meta(project_id, meta)
    return edl, meta["edl_rev"]


def read_transcript(project_id: str) -> dict | None:
    path = project_dir(project_id) / "transcript.json"
    if not path.exists():
        return None
    with open(path) as f:
        return json.load(f)


def prune_renders(project_id: str, days: int = RENDER_PRUNE_DAYS) -> int:
    """Delete render artifacts older than `days`. Returns the count removed."""
    d = project_dir(project_id) / "renders"
    if not d.exists():
        return 0
    cutoff = time.time() - days * 86400
    removed = 0
    for p in d.iterdir():
        try:
            if p.is_file() and p.stat().st_mtime < cutoff:
                p.unlink()
                removed += 1
        except OSError:
            continue
    return removed
