"""Research artifact loader.

Reads a research_artifact.json + its on-disk raw captures into
normalised in-memory structures the mapper can reason about.

Does NOT parse or score content — that is the mapper's job. This
module's only responsibility is honest I/O with clear errors.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class RawCapture:
    """One successfully fetched source, loaded from disk."""

    url: str
    tier: str
    label: str
    raw_path: str  # absolute
    text: str
    http_status: int | None = None
    bytes: int = 0
    error: str | None = None  # load error, not fetch error


@dataclass
class LoadedArtifact:
    """Normalised research artifact + raw bodies."""

    tool_slug: str
    mode: str
    generated_at: str
    run_dir: Path
    artifact_path: Path
    raw_captures: list[RawCapture] = field(default_factory=list)
    planned_sources: list[dict[str, Any]] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    load_errors: list[str] = field(default_factory=list)

    @property
    def has_any_source(self) -> bool:
        return any(c.text for c in self.raw_captures)

    @property
    def total_raw_bytes(self) -> int:
        return sum(len(c.text) for c in self.raw_captures)


def _read_text_safely(path: Path, max_bytes: int = 2_000_000) -> tuple[str, str | None]:
    """Read a raw capture off disk.

    Bounded at 2MB per file — the research agent captures bounded
    HTML dumps; anything bigger than 2MB is almost certainly a
    mis-fetch and would hurt keyword scanning more than it helps.
    """
    try:
        raw = path.read_bytes()[:max_bytes]
    except OSError as e:
        return "", f"read error: {e}"
    try:
        return raw.decode("utf-8", errors="replace"), None
    except Exception as e:  # defensive — decode('replace') should never raise
        return "", f"decode error: {e}"


def load_artifact(artifact_path: Path) -> LoadedArtifact:
    """Load research_artifact.json and all OK raw captures.

    Raises nothing on per-file failures — load_errors accumulates.
    """

    if not artifact_path.is_file():
        raise FileNotFoundError(f"research artifact not found: {artifact_path}")

    data = json.loads(artifact_path.read_text(encoding="utf-8"))
    artifact = data.get("artifact") or {}
    plan = data.get("plan") or {}

    run_dir = artifact_path.parent
    loaded = LoadedArtifact(
        tool_slug=str(artifact.get("tool_slug", "")),
        mode=str(artifact.get("mode", "")),
        generated_at=str(artifact.get("generated_at", "")),
        run_dir=run_dir,
        artifact_path=artifact_path,
        planned_sources=list(plan.get("sources") or []),
        notes=list(artifact.get("notes") or []),
    )
    if not loaded.tool_slug:
        loaded.load_errors.append("artifact has no tool_slug")
        return loaded

    for entry in artifact.get("sources") or []:
        if entry.get("status") != "ok":
            continue
        ref = entry.get("ref") or {}
        raw_rel = entry.get("raw_path")
        if not raw_rel:
            loaded.load_errors.append(
                f"ok source {ref.get('url')!r} has no raw_path"
            )
            continue
        raw_abs = run_dir / raw_rel
        text, err = _read_text_safely(raw_abs)
        if err:
            loaded.load_errors.append(f"{ref.get('url')!r}: {err}")
            continue
        loaded.raw_captures.append(
            RawCapture(
                url=str(ref.get("url", "")),
                tier=str(ref.get("tier", "")),
                label=str(ref.get("label", "")),
                raw_path=str(raw_abs),
                text=text,
                http_status=entry.get("http_status"),
                bytes=entry.get("bytes") or 0,
            )
        )

    return loaded
