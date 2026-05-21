"""
umh.substrate.artifact_contract — Reusable artifact/report objects
that any publication layer can consume.

Contract and storage primitive only. No Notion rendering, no Discord
formatting, no file I/O. All state transitions expressed as SET/REMOVE
mutations for replay-safe persistence.

Public API:
    RuntimeArtifact          — frozen artifact record
    compute_artifact_id      — deterministic artifact ID
    build_runtime_artifact   — construct a new artifact
    artifact_to_mutations    — persistence mutations
    load_runtime_artifact    — reconstruct from state
    list_recent_artifacts    — enumerate recent artifact IDs (bounded)

Separation note:
    This module is harness-only. Product layers (Notion publisher,
    Discord renderer) consume these artifacts — they do not live here.
"""

from __future__ import annotations

import hashlib
import json
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

_LOG_PREFIX = "[substrate.artifact_contract]"


def _log(msg: str) -> None:
    print(f"{_LOG_PREFIX} {msg}", file=sys.stderr)


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# State key helpers
# ---------------------------------------------------------------------------
_ARTIFACT_KEY_PREFIX = "runtime_artifact."
_RECENT_INDEX_PREFIX = "runtime_artifact_index.recent."


def _artifact_key(artifact_id: str) -> str:
    return f"{_ARTIFACT_KEY_PREFIX}{artifact_id}"


def _recent_key(artifact_id: str) -> str:
    return f"{_RECENT_INDEX_PREFIX}{artifact_id}"


# ---------------------------------------------------------------------------
# RuntimeArtifact — frozen artifact record
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class RuntimeArtifact:
    """Immutable artifact/report that any publication layer can consume.

    Fields:
        artifact_id:    deterministic artifact identifier
        session_id:     owning session
        artifact_type:  type tag (report, brief, summary, transcript, etc.)
        title:          human-readable title
        body:           artifact content
        content_type:   MIME-like type (default: text/markdown)
        created_at:     ISO timestamp
        source:         originating module/system
        correlation_id: links artifact to upstream event chain
    """

    artifact_id: str
    session_id: str
    artifact_type: str
    title: str
    body: str
    content_type: str = "text/markdown"
    created_at: str = ""
    source: str = ""
    correlation_id: str = ""

    def __post_init__(self) -> None:
        if not self.created_at:
            object.__setattr__(self, "created_at", _utcnow())

    def to_dict(self) -> dict[str, Any]:
        """Serialize to plain dict — deterministic key order."""
        return {
            "artifact_id": self.artifact_id,
            "artifact_type": self.artifact_type,
            "body": self.body,
            "content_type": self.content_type,
            "correlation_id": self.correlation_id,
            "created_at": self.created_at,
            "session_id": self.session_id,
            "source": self.source,
            "title": self.title,
        }

    @staticmethod
    def from_dict(d: dict[str, Any]) -> RuntimeArtifact:
        """Reconstruct from plain dict."""
        return RuntimeArtifact(
            artifact_id=str(d.get("artifact_id", "")),
            session_id=str(d.get("session_id", "")),
            artifact_type=str(d.get("artifact_type", "")),
            title=str(d.get("title", "")),
            body=str(d.get("body", "")),
            content_type=str(d.get("content_type", "text/markdown")),
            created_at=str(d.get("created_at", "")),
            source=str(d.get("source", "")),
            correlation_id=str(d.get("correlation_id", "")),
        )


# ---------------------------------------------------------------------------
# Deterministic ID
# ---------------------------------------------------------------------------


def compute_artifact_id(
    session_id: str,
    artifact_type: str,
    title: str,
) -> str:
    """Deterministic artifact ID: same inputs → same ID.

    Uses SHA-256 of canonical JSON (sorted keys, compact separators).
    """
    canonical = json.dumps(
        {
            "artifact_type": artifact_type,
            "session_id": session_id,
            "title": title,
        },
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )
    return f"art_{hashlib.sha256(canonical.encode()).hexdigest()[:12]}"


# ---------------------------------------------------------------------------
# Builder
# ---------------------------------------------------------------------------


def build_runtime_artifact(
    *,
    session_id: str,
    artifact_type: str,
    title: str,
    body: str,
    content_type: str = "text/markdown",
    source: str = "",
    correlation_id: str = "",
    artifact_id: str | None = None,
) -> RuntimeArtifact:
    """Construct a new RuntimeArtifact with deterministic ID."""
    aid = artifact_id or compute_artifact_id(
        session_id,
        artifact_type,
        title,
    )
    return RuntimeArtifact(
        artifact_id=aid,
        session_id=session_id,
        artifact_type=artifact_type,
        title=title,
        body=body,
        content_type=content_type,
        created_at=_utcnow(),
        source=source,
        correlation_id=correlation_id,
    )


# ---------------------------------------------------------------------------
# Mutation builders — SET / REMOVE only
# ---------------------------------------------------------------------------


def artifact_to_mutations(
    artifact: RuntimeArtifact,
) -> list[dict[str, Any]]:
    """Build mutations to persist an artifact.

    Writes:
        1. Artifact record: runtime_artifact.{artifact_id}
        2. Recent index: runtime_artifact_index.recent.{artifact_id}
    """
    return [
        {
            "op": "SET",
            "key": _artifact_key(artifact.artifact_id),
            "value": artifact.to_dict(),
        },
        {
            "op": "SET",
            "key": _recent_key(artifact.artifact_id),
            "value": {
                "session_id": artifact.session_id,
                "artifact_type": artifact.artifact_type,
                "title": artifact.title,
                "created_at": artifact.created_at,
            },
        },
    ]


# ---------------------------------------------------------------------------
# Load / list helpers
# ---------------------------------------------------------------------------


def load_runtime_artifact(
    state: dict[str, Any],
    artifact_id: str,
) -> RuntimeArtifact | None:
    """Reconstruct a RuntimeArtifact from state, or None if missing."""
    raw = state.get(_artifact_key(artifact_id))
    if not isinstance(raw, dict):
        return None
    return RuntimeArtifact.from_dict(raw)


def list_recent_artifacts(
    state: dict[str, Any],
    limit: int = 10,
) -> tuple[str, ...]:
    """Return most recent artifact IDs from state (bounded).

    Sorts by created_at descending from recent index entries,
    returns at most ``limit`` entries.
    """
    entries: list[tuple[str, str]] = []
    for k, v in state.items():
        if not k.startswith(_RECENT_INDEX_PREFIX):
            continue
        if not isinstance(v, dict):
            continue
        aid = k[len(_RECENT_INDEX_PREFIX) :]
        created = str(v.get("created_at", ""))
        entries.append((created, aid))
    entries.sort(reverse=True)
    return tuple(aid for _, aid in entries[:limit])
