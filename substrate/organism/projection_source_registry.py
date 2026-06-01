"""Projection Source Registry — tracks sources per projection for reconciliation.

Phase 14.0. UMH substrate subsystem. Instance-agnostic.

Builds on the general SourceRegistry (Phase 13.3) by adding projection
awareness: each source is linked to a named projection and carries
canonicality/permission metadata needed before any cross-source
reconciliation or feature build can proceed.
"""

from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)

_REPO_ROOT = os.environ.get("UMH_ROOT", "/opt/OS")
_REGISTRY_PATH = os.path.join(
    _REPO_ROOT, "data", "umh", "projection_reconciliation", "source_registry.jsonl"
)


class ProjectionSourceType(str, Enum):
    GOOGLE_DOCS = "google_docs"
    GOOGLE_DRIVE = "google_drive"
    GITHUB_REPOSITORY = "github_repository"
    DEVICE_FILESYSTEM = "device_filesystem"
    LOCAL_FILESYSTEM = "local_filesystem"
    AUDIT_ARTIFACT = "audit_artifact"
    PRODUCTION_TRUTH_ARTIFACT = "production_truth_artifact"
    RUNTIME_STATE = "runtime_state"
    UNKNOWN = "unknown"


class ProjectionName(str, Enum):
    UMH = "UMH"
    SHARED = "Shared"
    UNKNOWN = "Unknown"


class SourceCanonicality(str, Enum):
    PRODUCTION_TRUTH = "production_truth"
    CANDIDATE_CANONICAL = "candidate_canonical"
    PARTIAL = "partial"
    STALE = "stale"
    HISTORICAL = "historical"
    DUPLICATE = "duplicate"
    DIVERGENT = "divergent"
    UNKNOWN = "unknown"


class ReadStatus(str, Enum):
    UNREAD = "unread"
    METADATA_ONLY = "metadata_only"
    INSPECTED = "inspected"
    FULLY_READ = "fully_read"
    PERMISSION_DENIED = "permission_denied"
    UNAVAILABLE = "unavailable"


@dataclass
class ProjectionSource:
    source_id: str = ""
    projection: str = ProjectionName.UNKNOWN.value
    source_type: str = ProjectionSourceType.UNKNOWN.value
    name: str = ""
    device: str = ""
    path_or_locator: str = ""
    contains: list[str] = field(default_factory=list)
    canonicality: str = SourceCanonicality.UNKNOWN.value
    access_required: bool = False
    permission_required: bool = False
    sync_policy: str = "read_only_until_operator_approved"
    read_status: str = ReadStatus.UNREAD.value
    last_seen_at: float = 0.0
    evidence: list[str] = field(default_factory=list)
    notes: str = ""

    def __post_init__(self) -> None:
        if not self.source_id:
            self.source_id = f"psrc-{uuid4().hex[:8]}"
        if not self.last_seen_at:
            self.last_seen_at = time.time()

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_id": self.source_id,
            "projection": self.projection,
            "source_type": self.source_type,
            "name": self.name,
            "device": self.device,
            "path_or_locator": self.path_or_locator,
            "contains": self.contains,
            "canonicality": self.canonicality,
            "access_required": self.access_required,
            "permission_required": self.permission_required,
            "sync_policy": self.sync_policy,
            "read_status": self.read_status,
            "last_seen_at": self.last_seen_at,
            "evidence": self.evidence,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> ProjectionSource:
        valid = {k: v for k, v in d.items() if k in cls.__dataclass_fields__}
        return cls(**valid)


class ProjectionSourceRegistry:
    """Registry of all known projection sources for reconciliation."""

    def __init__(self, path: str | None = None) -> None:
        self._path = path or _REGISTRY_PATH
        self._sources: dict[str, ProjectionSource] = {}
        self._load()

    def _load(self) -> None:
        if not os.path.exists(self._path):
            return
        with open(self._path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    d = json.loads(line)
                    src = ProjectionSource.from_dict(d)
                    self._sources[src.source_id] = src
                except (json.JSONDecodeError, TypeError):
                    logger.warning("Skipping malformed projection source line")

    def _save(self) -> None:
        os.makedirs(os.path.dirname(self._path), exist_ok=True)
        with open(self._path, "w") as f:
            for src in self._sources.values():
                f.write(json.dumps(src.to_dict(), default=str) + "\n")

    def register(self, source: ProjectionSource) -> ProjectionSource:
        for existing in self._sources.values():
            if (
                existing.name == source.name
                and existing.projection == source.projection
                and existing.source_type == source.source_type
            ):
                existing.last_seen_at = time.time()
                existing.notes = source.notes or existing.notes
                self._save()
                return existing
        self._sources[source.source_id] = source
        self._save()
        return source

    def get(self, source_id: str) -> ProjectionSource | None:
        return self._sources.get(source_id)

    def list_sources(
        self,
        projection: str | None = None,
        source_type: str | None = None,
        canonicality: str | None = None,
        read_status: str | None = None,
    ) -> list[ProjectionSource]:
        result = list(self._sources.values())
        if projection:
            result = [s for s in result if s.projection == projection]
        if source_type:
            result = [s for s in result if s.source_type == source_type]
        if canonicality:
            result = [s for s in result if s.canonicality == canonicality]
        if read_status:
            result = [s for s in result if s.read_status == read_status]
        return result

    def update_read_status(self, source_id: str, status: str) -> bool:
        src = self._sources.get(source_id)
        if not src:
            return False
        src.read_status = status
        src.last_seen_at = time.time()
        self._save()
        return True

    def update_canonicality(self, source_id: str, canonicality: str) -> bool:
        src = self._sources.get(source_id)
        if not src:
            return False
        src.canonicality = canonicality
        src.last_seen_at = time.time()
        self._save()
        return True

    def sources_requiring_permission(self) -> list[ProjectionSource]:
        return [s for s in self._sources.values() if s.permission_required]

    def uninspected_sources(self) -> list[ProjectionSource]:
        return [
            s for s in self._sources.values()
            if s.read_status in (ReadStatus.UNREAD.value, ReadStatus.UNAVAILABLE.value)
        ]

    def count(self) -> int:
        return len(self._sources)

    def summary(self) -> dict[str, Any]:
        by_projection: dict[str, int] = {}
        by_type: dict[str, int] = {}
        by_canonicality: dict[str, int] = {}
        by_read_status: dict[str, int] = {}
        for s in self._sources.values():
            by_projection[s.projection] = by_projection.get(s.projection, 0) + 1
            by_type[s.source_type] = by_type.get(s.source_type, 0) + 1
            by_canonicality[s.canonicality] = by_canonicality.get(s.canonicality, 0) + 1
            by_read_status[s.read_status] = by_read_status.get(s.read_status, 0) + 1
        return {
            "total": len(self._sources),
            "by_projection": by_projection,
            "by_type": by_type,
            "by_canonicality": by_canonicality,
            "by_read_status": by_read_status,
            "permission_required_count": len(self.sources_requiring_permission()),
            "uninspected_count": len(self.uninspected_sources()),
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "sources": [s.to_dict() for s in self._sources.values()],
            "summary": self.summary(),
        }


def create_initial_registry(
    path: str | None = None,
    sources: list[ProjectionSource] | None = None,
) -> ProjectionSourceRegistry:
    """Create registry from provided sources or empty.

    The substrate provides the mechanism. Projection-specific source
    definitions are supplied by the caller (typically a projection
    configuration or operator command).
    """
    registry = ProjectionSourceRegistry(path=path)
    for src in sources or []:
        registry.register(src)
    return registry
