"""
Operator artifacts — report file generation for Discord attachments.

Responsible for:
- Writing markdown reports to temp/staging paths safely
- Deterministic filename patterns
- Returning attachment payloads usable by the Discord bot layer
- Clean separation of artifact generation from message sending

Design rules (substrate conventions):
- Additive only. No hot-path imports.
- No hidden mutation of runtime state.
- Safe temp path handling (atomic writes, UTF-8).
- No coupling to tmux or Discord internals.
- Deterministic filenames.
"""

from __future__ import annotations

import sys
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from umh.substrate.operator_trace import OperatorTrace
from umh.substrate.operator_delivery import (
    build_full_report_markdown,
    build_report_filename,
)

_LOG_PREFIX = "[substrate.operator_artifacts]"
_ARTIFACT_DIR = "/tmp/eos_artifacts"


def _log(msg: str) -> None:
    print(f"{_LOG_PREFIX} {msg}", file=sys.stderr)


# ─── ReportArtifact ─────────────────────────────────────────────────────────


@dataclass
class ReportArtifact:
    """Attachment payload for a full report.

    Contains everything the Discord bot layer needs to attach the file.
    """

    artifact_id: str
    filename: str
    content_type: str
    body_text: str
    file_path: str
    file_size_bytes: int
    created_at: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "artifact_id": self.artifact_id,
            "filename": self.filename,
            "content_type": self.content_type,
            "file_path": self.file_path,
            "file_size_bytes": self.file_size_bytes,
            "created_at": self.created_at,
            "metadata": dict(self.metadata),
        }


# ─── Artifact builder ──────────────────────────────────────────────────────


def _ensure_artifact_dir() -> Path:
    """Ensure the artifact staging directory exists."""
    p = Path(_ARTIFACT_DIR)
    p.mkdir(parents=True, exist_ok=True)
    return p


def _artifact_id() -> str:
    return f"art_{uuid.uuid4().hex[:12]}"


def build_operator_report_artifact(
    trace: OperatorTrace,
    *,
    title: str = "",
    extra_sections: dict[str, str] | None = None,
    filename_override: str = "",
) -> ReportArtifact:
    """Build a complete report artifact from an OperatorTrace.

    Writes the markdown report to a temp file and returns a ReportArtifact
    with all metadata needed for Discord attachment.
    """
    art_id = _artifact_id()

    # Generate content
    body = build_full_report_markdown(
        trace,
        title=title,
        extra_sections=extra_sections,
    )

    # Determine filename
    filename = filename_override or build_report_filename(trace)

    # Write to disk
    artifact_dir = _ensure_artifact_dir()
    file_path = artifact_dir / f"{art_id}_{filename}"
    file_path.write_text(body, encoding="utf-8")

    file_size = file_path.stat().st_size

    artifact = ReportArtifact(
        artifact_id=art_id,
        filename=filename,
        content_type="text/markdown",
        body_text=body,
        file_path=str(file_path),
        file_size_bytes=file_size,
        created_at=datetime.now(timezone.utc).isoformat(),
    )

    _log(f"created: id={art_id} file={filename} size={file_size}B path={file_path}")

    return artifact


def build_approval_context_artifact(
    *,
    approval_id: str,
    title: str = "",
    context_text: str = "",
    metadata: dict[str, Any] | None = None,
) -> ReportArtifact:
    """Build a context artifact for an approval request.

    Similar to a report artifact but contains approval context
    rather than execution results.
    """
    art_id = _artifact_id()
    now = datetime.now(timezone.utc)
    date_str = now.strftime("%Y%m%d_%H%M%S")

    # Build markdown
    title_line = title or "Approval Context"
    lines = [
        f"# {title_line}",
        f"*Generated: {now.strftime('%Y-%m-%d %H:%M UTC')}*",
        f"*Approval ID: `{approval_id}`*",
        "",
        "## Context",
        "",
        context_text or "No additional context provided.",
        "",
    ]
    if metadata:
        lines.append("## Metadata")
        for k, v in metadata.items():
            lines.append(f"- **{k}:** {v}")
        lines.append("")

    body = "\n".join(lines)
    filename = f"approval_context_{date_str}.md"

    # Write to disk
    artifact_dir = _ensure_artifact_dir()
    file_path = artifact_dir / f"{art_id}_{filename}"
    file_path.write_text(body, encoding="utf-8")
    file_size = file_path.stat().st_size

    return ReportArtifact(
        artifact_id=art_id,
        filename=filename,
        content_type="text/markdown",
        body_text=body,
        file_path=str(file_path),
        file_size_bytes=file_size,
        created_at=now.isoformat(),
        metadata={"approval_id": approval_id, **(metadata or {})},
    )


def build_text_artifact(
    body: str,
    *,
    filename: str = "",
    prefix: str = "artifact",
) -> ReportArtifact:
    """Build a generic text artifact from raw markdown.

    Use when you already have the content and just need it packaged
    as an attachment.
    """
    art_id = _artifact_id()
    now = datetime.now(timezone.utc)

    if not filename:
        date_str = now.strftime("%Y%m%d_%H%M%S")
        filename = f"{prefix}_{date_str}.md"

    artifact_dir = _ensure_artifact_dir()
    file_path = artifact_dir / f"{art_id}_{filename}"
    file_path.write_text(body, encoding="utf-8")
    file_size = file_path.stat().st_size

    return ReportArtifact(
        artifact_id=art_id,
        filename=filename,
        content_type="text/markdown",
        body_text=body,
        file_path=str(file_path),
        file_size_bytes=file_size,
        created_at=now.isoformat(),
    )


def cleanup_artifact(artifact: ReportArtifact) -> bool:
    """Remove an artifact's temp file. Returns True if file existed."""
    p = Path(artifact.file_path)
    existed = p.exists()
    p.unlink(missing_ok=True)
    return existed


def validate_artifact(artifact: ReportArtifact) -> dict[str, Any]:
    """Preflight validation for an artifact before Discord send.

    Checks file exists, is readable, and non-empty.
    """
    result: dict[str, Any] = {
        "valid": False,
        "artifact_id": artifact.artifact_id,
        "file_path": artifact.file_path,
        "size_bytes": 0,
        "error": "",
    }

    p = Path(artifact.file_path)
    if not p.exists():
        result["error"] = "artifact_file_missing"
        return result

    size = p.stat().st_size
    result["size_bytes"] = size
    if size == 0:
        result["error"] = "artifact_file_empty"
        return result

    try:
        with open(artifact.file_path, "rb") as f:
            f.read(1)
    except Exception as exc:
        result["error"] = f"artifact_file_unreadable: {exc}"
        return result

    result["valid"] = True
    return result


__all__ = [
    "ReportArtifact",
    "build_operator_report_artifact",
    "build_approval_context_artifact",
    "build_text_artifact",
    "cleanup_artifact",
    "validate_artifact",
]
