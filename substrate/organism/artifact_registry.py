"""Artifact Registry — indexes produced outputs across UMH.

RealityGraph knows entities (projects, repos, workspaces, devices).
ArtifactRegistry indexes produced artifacts: proof packages, decisions,
configs, templates, audit reports, engineering artifacts.

ProjectionSourceRegistry (existing) indexes INPUT sources.
ArtifactRegistry indexes PRODUCED outputs.
They link: artifacts reference sources, sources contain artifacts.

Read-only observation pattern. JSONL persistence. Instance-agnostic.

Campaign 6.0. UMH substrate layer.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import time
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)

_ROOT = os.environ.get("UMH_ROOT") or "/opt/OS"
_DEFAULT_STORE = os.path.join(_ROOT, "data", "umh", "artifacts", "artifact_registry.jsonl")


# ── Types ─────────────────────────────────────────────────────────────────


class ArtifactType(str, Enum):
    PROOF_PACKAGE = "proof_package"
    AUDIT_REPORT = "audit_report"
    ENGINEERING_ARTIFACT = "engineering_artifact"
    DECISION_RECORD = "decision_record"
    CONFIGURATION = "configuration"
    TEMPLATE = "template"
    MIGRATION = "migration"
    TEST_SUITE = "test_suite"
    DEPLOYMENT_MANIFEST = "deployment_manifest"


class ArtifactStatus(str, Enum):
    ACTIVE = "active"
    SUPERSEDED = "superseded"
    ARCHIVED = "archived"
    DRAFT = "draft"


@dataclass
class ArtifactEntry:
    artifact_id: str
    artifact_type: str
    name: str
    source_path: str
    source_system: str
    entity_refs: list[str] = field(default_factory=list)
    created_at: float = 0.0
    last_verified: float = 0.0
    status: str = "active"
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ArtifactEntry:
        return cls(
            artifact_id=data.get("artifact_id", ""),
            artifact_type=data.get("artifact_type", ""),
            name=data.get("name", ""),
            source_path=data.get("source_path", ""),
            source_system=data.get("source_system", ""),
            entity_refs=data.get("entity_refs", []),
            created_at=data.get("created_at", 0.0),
            last_verified=data.get("last_verified", 0.0),
            status=data.get("status", "active"),
            metadata=data.get("metadata", {}),
        )


# ── Artifact Registry ────────────────────────────────────────────────────


class ArtifactRegistry:
    """Registry of produced artifacts across UMH subsystems.

    Indexes proof packages, audit reports, decision records, configs,
    templates, and other output artifacts. Links them to RealityGraph
    entities via entity_refs.
    """

    def __init__(self, store_path: str | None = None) -> None:
        self._store_path = store_path or _DEFAULT_STORE
        self._artifacts: dict[str, ArtifactEntry] = {}
        self._load()

    # ── CRUD ──────────────────────────────────────────────────────────

    def register(self, entry: ArtifactEntry) -> ArtifactEntry:
        """Register or update an artifact. Deduplicates on artifact_id."""
        if not entry.artifact_id:
            entry.artifact_id = self._generate_id(entry)
        if not entry.created_at:
            entry.created_at = time.time()
        if not entry.last_verified:
            entry.last_verified = entry.created_at

        self._artifacts[entry.artifact_id] = entry
        self._persist(entry)
        return entry

    def get(self, artifact_id: str) -> ArtifactEntry | None:
        return self._artifacts.get(artifact_id)

    def find_by_type(self, artifact_type: str) -> list[ArtifactEntry]:
        return [
            a for a in self._artifacts.values()
            if a.artifact_type == artifact_type
        ]

    def find_by_entity(self, entity_id: str) -> list[ArtifactEntry]:
        return [
            a for a in self._artifacts.values()
            if entity_id in a.entity_refs
        ]

    def find_by_source(self, source_path: str) -> list[ArtifactEntry]:
        return [
            a for a in self._artifacts.values()
            if a.source_path == source_path
        ]

    def list_artifacts(
        self,
        artifact_type: str | None = None,
        status: str | None = None,
    ) -> list[ArtifactEntry]:
        result = list(self._artifacts.values())
        if artifact_type:
            result = [a for a in result if a.artifact_type == artifact_type]
        if status:
            result = [a for a in result if a.status == status]
        return result

    def count(self) -> int:
        return len(self._artifacts)

    def summary(self) -> dict[str, Any]:
        by_type: dict[str, int] = {}
        by_status: dict[str, int] = {}
        for a in self._artifacts.values():
            by_type[a.artifact_type] = by_type.get(a.artifact_type, 0) + 1
            by_status[a.status] = by_status.get(a.status, 0) + 1

        return {
            "total": len(self._artifacts),
            "by_type": by_type,
            "by_status": by_status,
        }

    # ── Persistence ───────────────────────────────────────────────────

    def _load(self) -> None:
        if not os.path.exists(self._store_path):
            return
        try:
            with open(self._store_path, "r") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        data = json.loads(line)
                        entry = ArtifactEntry.from_dict(data)
                        if entry.artifact_id:
                            self._artifacts[entry.artifact_id] = entry
                    except (json.JSONDecodeError, KeyError) as exc:
                        logger.debug("Skipping malformed artifact line: %s", exc)
        except OSError as exc:
            logger.debug("Could not load artifact registry %s: %s", self._store_path, exc)

    def _persist(self, entry: ArtifactEntry) -> None:
        try:
            os.makedirs(os.path.dirname(self._store_path), exist_ok=True)
            with open(self._store_path, "a") as f:
                f.write(json.dumps(entry.to_dict()) + "\n")
        except OSError as exc:
            logger.debug("Could not persist artifact: %s", exc)

    def _compact(self) -> None:
        """Rewrite store with only current state (deduplicates)."""
        try:
            os.makedirs(os.path.dirname(self._store_path), exist_ok=True)
            with open(self._store_path, "w") as f:
                for entry in self._artifacts.values():
                    f.write(json.dumps(entry.to_dict()) + "\n")
        except OSError as exc:
            logger.debug("Could not compact artifact registry: %s", exc)

    @staticmethod
    def _generate_id(entry: ArtifactEntry) -> str:
        key = f"{entry.artifact_type}:{entry.source_path}:{entry.name}"
        return f"art-{hashlib.sha256(key.encode()).hexdigest()[:12]}"
