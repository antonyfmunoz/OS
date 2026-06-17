"""Documentation Awareness Runtime — content-level metadata for docs.

ProjectionSourceRegistry tracks that sources exist.
DocumentationAwarenessRuntime adds content-level metadata: topics,
entity references, decision count, staleness detection.

Read-only observation pattern. Deterministic keyword extraction.
Instance-agnostic.

Campaign 6.2. UMH substrate layer.
"""

from __future__ import annotations

import logging
import os
import re
import time
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)

_ROOT = os.environ.get("UMH_ROOT") or "/opt/OS"

_DECISION_MARKERS = re.compile(
    r"(?:^|\n)\s*(?:##?\s*)?(?:decision|decided|ruling|resolution)\s*[:—\-]",
    re.IGNORECASE,
)
_CONSTRAINT_MARKERS = re.compile(
    r"(?:^|\n)\s*(?:##?\s*)?(?:constraint|invariant|non-negotiable|must not|never)\s*[:—\-]",
    re.IGNORECASE,
)
_HEADING_PATTERN = re.compile(r"^#{1,4}\s+(.+)$", re.MULTILINE)


# ── Types ─────────────────────────────────────────────────────────────────


class DocumentStatus(str, Enum):
    CURRENT = "current"
    STALE = "stale"
    UNVERIFIED = "unverified"
    MISSING = "missing"


@dataclass
class DocumentEntry:
    doc_id: str
    name: str
    source_id: str
    path_or_url: str
    topics: list[str] = field(default_factory=list)
    entity_refs: list[str] = field(default_factory=list)
    decision_count: int = 0
    constraint_count: int = 0
    last_verified: float = 0.0
    status: str = "unverified"
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class DocumentationSnapshot:
    total_docs: int
    by_status: dict[str, int] = field(default_factory=dict)
    by_source_type: dict[str, int] = field(default_factory=dict)
    stale_docs: list[DocumentEntry] = field(default_factory=list)
    unverified_docs: list[DocumentEntry] = field(default_factory=list)
    detected_at: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_docs": self.total_docs,
            "by_status": self.by_status,
            "by_source_type": self.by_source_type,
            "stale_docs": [d.to_dict() for d in self.stale_docs],
            "unverified_docs": [d.to_dict() for d in self.unverified_docs],
            "detected_at": self.detected_at,
        }


# ── Documentation Awareness Runtime ──────────────────────────────────────


class DocumentationAwarenessRuntime:
    """Content-level metadata for documentation sources.

    Composes ProjectionSourceRegistry to know WHICH docs exist, then
    adds topics, entity references, decision/constraint counts, and
    staleness detection via deterministic content analysis.
    """

    def __init__(
        self,
        projection_source_registry: Any = None,
        artifact_registry: Any = None,
        reality_graph: Any = None,
        staleness_days: int = 30,
    ) -> None:
        self._sources = projection_source_registry
        self._artifacts = artifact_registry
        self._graph = reality_graph
        self._staleness_days = staleness_days
        self._documents: dict[str, DocumentEntry] = {}

    def scan_documentation(self) -> DocumentationSnapshot:
        """Scan all documentation sources and build awareness.

        Scans from registries (source and artifact) and merges with any
        previously manually-indexed documents. Registry entries overwrite
        manual entries on doc_id collision.
        """
        now = time.time()

        if self._sources is not None:
            self._scan_from_source_registry(now)

        if self._artifacts is not None:
            self._scan_from_artifact_registry(now)

        by_status: dict[str, int] = {}
        by_source_type: dict[str, int] = {}
        stale: list[DocumentEntry] = []
        unverified: list[DocumentEntry] = []

        for doc in self._documents.values():
            by_status[doc.status] = by_status.get(doc.status, 0) + 1
            src_type = doc.metadata.get("source_type", "unknown")
            by_source_type[src_type] = by_source_type.get(src_type, 0) + 1

            if doc.status == DocumentStatus.STALE.value:
                stale.append(doc)
            elif doc.status == DocumentStatus.UNVERIFIED.value:
                unverified.append(doc)

        return DocumentationSnapshot(
            total_docs=len(self._documents),
            by_status=by_status,
            by_source_type=by_source_type,
            stale_docs=stale,
            unverified_docs=unverified,
            detected_at=now,
        )

    def index_document(
        self,
        doc_id: str,
        name: str,
        content: str,
        source_id: str = "",
        path_or_url: str = "",
        last_modified: float = 0.0,
        source_type: str = "unknown",
    ) -> DocumentEntry:
        """Index a document with deterministic content analysis."""
        now = time.time()
        topics = self._extract_topics(content)
        entity_refs = self._extract_entity_refs(content)
        decisions = len(_DECISION_MARKERS.findall(content))
        constraints = len(_CONSTRAINT_MARKERS.findall(content))

        status = self._determine_status(last_modified, now)

        entry = DocumentEntry(
            doc_id=doc_id,
            name=name,
            source_id=source_id,
            path_or_url=path_or_url,
            topics=topics,
            entity_refs=entity_refs,
            decision_count=decisions,
            constraint_count=constraints,
            last_verified=last_modified or now,
            status=status,
            metadata={"source_type": source_type},
        )
        self._documents[doc_id] = entry
        return entry

    def find_docs_for_entity(self, entity_id: str) -> list[DocumentEntry]:
        return [
            d for d in self._documents.values()
            if entity_id in d.entity_refs
        ]

    def find_stale_docs(self, max_age_days: int | None = None) -> list[DocumentEntry]:
        cutoff = time.time() - (max_age_days or self._staleness_days) * 86400
        return [
            d for d in self._documents.values()
            if d.last_verified < cutoff
        ]

    def get_document(self, doc_id: str) -> DocumentEntry | None:
        return self._documents.get(doc_id)

    def list_documents(
        self,
        status: str | None = None,
        source_type: str | None = None,
    ) -> list[DocumentEntry]:
        result = list(self._documents.values())
        if status:
            result = [d for d in result if d.status == status]
        if source_type:
            result = [d for d in result if d.metadata.get("source_type") == source_type]
        return result

    def snapshot(self) -> dict[str, Any]:
        if self._documents:
            return self.scan_documentation().to_dict()
        snap = self.scan_documentation()
        return snap.to_dict()

    # ── Internal ──────────────────────────────────────────────────────

    def _scan_from_source_registry(self, now: float) -> None:
        sources = []
        if hasattr(self._sources, "list_sources"):
            sources = self._sources.list_sources()
        elif hasattr(self._sources, "_sources"):
            sources = list(self._sources._sources.values())

        doc_source_types = {"google_docs", "google_drive", "local_filesystem", "notion_page"}
        for source in sources:
            src_type = getattr(source, "source_type", None)
            src_type_val = src_type.value if hasattr(src_type, "value") else str(src_type) if src_type else ""

            if src_type_val.lower() not in doc_source_types:
                continue

            source_id = getattr(source, "source_id", "") or getattr(source, "id", "")
            name = getattr(source, "name", source_id)
            path = getattr(source, "path_or_locator", "") or getattr(source, "url", "")

            content = self._read_local_content(path) if os.path.isfile(path) else ""
            last_mod = self._file_mtime(path) if os.path.isfile(path) else 0.0

            self.index_document(
                doc_id=f"doc-{source_id}",
                name=name,
                content=content,
                source_id=source_id,
                path_or_url=path,
                last_modified=last_mod,
                source_type=src_type_val,
            )

    def _scan_from_artifact_registry(self, now: float) -> None:
        artifacts = []
        if hasattr(self._artifacts, "list_artifacts"):
            artifacts = self._artifacts.list_artifacts(artifact_type="decision_record")
        elif hasattr(self._artifacts, "_artifacts"):
            artifacts = [
                a for a in self._artifacts._artifacts.values()
                if a.artifact_type == "decision_record"
            ]

        for artifact in artifacts:
            a_id = getattr(artifact, "artifact_id", "")
            name = getattr(artifact, "name", a_id)
            path = getattr(artifact, "source_path", "")
            content = self._read_local_content(path) if path and os.path.isfile(path) else ""

            self.index_document(
                doc_id=f"doc-art-{a_id}",
                name=name,
                content=content,
                source_id=a_id,
                path_or_url=path,
                last_modified=self._file_mtime(path) if path and os.path.isfile(path) else 0.0,
                source_type="artifact",
            )

    def _extract_topics(self, content: str) -> list[str]:
        headings = _HEADING_PATTERN.findall(content)
        topics: list[str] = []
        seen: set[str] = set()
        for h in headings[:20]:
            clean = h.strip()
            lower = clean.lower()
            if lower not in seen and len(clean) > 2:
                seen.add(lower)
                topics.append(clean)
        return topics

    def _extract_entity_refs(self, content: str) -> list[str]:
        if self._graph is None:
            return []

        refs: list[str] = []
        seen: set[str] = set()
        content_lower = content.lower()

        for entity in self._graph.all_entities():
            name_lower = entity.name.lower()
            if len(name_lower) >= 3 and name_lower in content_lower:
                if entity.entity_id not in seen:
                    seen.add(entity.entity_id)
                    refs.append(entity.entity_id)
        return refs

    def _determine_status(self, last_modified: float, now: float) -> str:
        if last_modified <= 0:
            return DocumentStatus.UNVERIFIED.value
        age_days = (now - last_modified) / 86400
        if age_days > self._staleness_days:
            return DocumentStatus.STALE.value
        return DocumentStatus.CURRENT.value

    @staticmethod
    def _read_local_content(path: str, max_bytes: int = 100_000) -> str:
        try:
            with open(path, "r", errors="replace") as f:
                return f.read(max_bytes)
        except OSError:
            return ""

    @staticmethod
    def _file_mtime(path: str) -> float:
        try:
            return os.path.getmtime(path)
        except OSError:
            return 0.0
