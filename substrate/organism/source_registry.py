"""Source Registry — tracks all context sources available to UMH.

A ContextSource represents any system, document, repository, or artifact
that contains information UMH can ingest, diagnose, and reconcile against
canonical truth.

Phase 13.3. UMH substrate subsystem. Instance-agnostic.
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
_SOURCES_PATH = os.path.join(
    _REPO_ROOT, "data", "umh", "context_assimilation", "sources.jsonl"
)


class SourceType(str, Enum):
    GITHUB_REPO = "github_repo"
    AUDIT_DOC = "audit_doc"
    LOCAL_DOC = "local_doc"
    LOCAL_JSON_ARTIFACT = "local_json_artifact"
    GOOGLE_DRIVE = "google_drive"
    GOOGLE_DOC = "google_doc"
    GMAIL = "gmail"
    CALENDAR = "calendar"
    NOTION = "notion"
    DISCORD = "discord"
    SLACK = "slack"
    CHAT_HISTORY = "chat_history"
    SPREADSHEET = "spreadsheet"
    EXTERNAL_URL = "external_url"
    OPERATOR_CONVERSATION = "operator_conversation"
    RUNTIME_ARTIFACT = "runtime_artifact"
    PRODUCTION_TRUTH_DELTA = "production_truth_delta"
    WORK_PACKET = "work_packet"
    KNOWLEDGE_MODEL = "knowledge_model"


class SyncPolicy(str, Enum):
    READ_ONLY = "read_only"
    SUGGEST_UPDATE = "suggest_update"
    OPERATOR_APPROVED_WRITE = "operator_approved_write"
    AUTOMATIC_SAFE_WRITE = "automatic_safe_write"
    DEPRECATED_SOURCE = "deprecated_source"
    CANONICAL_SOURCE = "canonical_source"
    ARCHIVE_ONLY = "archive_only"
    IGNORE = "ignore"


class Canonicality(str, Enum):
    UNKNOWN = "unknown"
    RAW_SOURCE = "raw_source"
    REFERENCE_ONLY = "reference_only"
    COMPETING_TRUTH = "competing_truth"
    CANONICAL = "canonical"
    DEPRECATED = "deprecated"
    SUPERSEDED = "superseded"


class SourceStatus(str, Enum):
    ACTIVE = "active"
    PENDING_INGESTION = "pending_ingestion"
    INGESTED = "ingested"
    STALE = "stale"
    BLOCKED = "blocked"
    FAILED = "failed"
    DEPRECATED = "deprecated"
    IGNORED = "ignored"


@dataclass
class ContextSource:
    source_id: str = ""
    source_type: str = SourceType.LOCAL_DOC.value
    title: str = ""
    description: str = ""
    owner: str = ""
    account_ref: str = ""
    location_ref: str = ""
    connector_ref: str = ""
    sync_policy: str = SyncPolicy.READ_ONLY.value
    trust_level: float = 0.5
    freshness_policy: str = "manual"
    canonicality: str = Canonicality.UNKNOWN.value
    status: str = SourceStatus.ACTIVE.value
    domain_tags: list[str] = field(default_factory=list)
    entity_refs: list[str] = field(default_factory=list)
    project_refs: list[str] = field(default_factory=list)
    last_seen_at: float = 0.0
    last_ingested_at: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)
    evidence: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.source_id:
            self.source_id = f"src-{uuid4().hex[:8]}"
        if not self.last_seen_at:
            self.last_seen_at = time.time()

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_id": self.source_id,
            "source_type": self.source_type,
            "title": self.title,
            "description": self.description,
            "owner": self.owner,
            "account_ref": self.account_ref,
            "location_ref": self.location_ref,
            "connector_ref": self.connector_ref,
            "sync_policy": self.sync_policy,
            "trust_level": self.trust_level,
            "freshness_policy": self.freshness_policy,
            "canonicality": self.canonicality,
            "status": self.status,
            "domain_tags": self.domain_tags,
            "entity_refs": self.entity_refs,
            "project_refs": self.project_refs,
            "last_seen_at": self.last_seen_at,
            "last_ingested_at": self.last_ingested_at,
            "metadata": self.metadata,
            "evidence": self.evidence,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> ContextSource:
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


class SourceRegistry:
    def __init__(self, path: str | None = None) -> None:
        self._path = path or _SOURCES_PATH
        self._sources: dict[str, ContextSource] = {}
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
                    src = ContextSource.from_dict(d)
                    self._sources[src.source_id] = src
                except (json.JSONDecodeError, TypeError):
                    logger.warning("Skipping malformed source line")

    def _save(self) -> None:
        os.makedirs(os.path.dirname(self._path), exist_ok=True)
        with open(self._path, "w") as f:
            for src in self._sources.values():
                f.write(json.dumps(src.to_dict(), default=str) + "\n")

    def register(self, source: ContextSource) -> ContextSource:
        for existing in self._sources.values():
            if (
                existing.source_type == source.source_type
                and existing.location_ref == source.location_ref
                and existing.location_ref
            ):
                existing.last_seen_at = time.time()
                existing.status = source.status or existing.status
                self._save()
                return existing
        self._sources[source.source_id] = source
        self._save()
        return source

    def get(self, source_id: str) -> ContextSource | None:
        return self._sources.get(source_id)

    def list_sources(
        self,
        source_type: str | None = None,
        status: str | None = None,
        canonicality: str | None = None,
    ) -> list[ContextSource]:
        result = list(self._sources.values())
        if source_type:
            result = [s for s in result if s.source_type == source_type]
        if status:
            result = [s for s in result if s.status == status]
        if canonicality:
            result = [s for s in result if s.canonicality == canonicality]
        return result

    def update_status(self, source_id: str, status: str) -> bool:
        src = self._sources.get(source_id)
        if not src:
            return False
        src.status = status
        self._save()
        return True

    def mark_ingested(self, source_id: str) -> bool:
        src = self._sources.get(source_id)
        if not src:
            return False
        src.last_ingested_at = time.time()
        src.status = SourceStatus.INGESTED.value
        self._save()
        return True

    def count(self) -> int:
        return len(self._sources)

    def summary(self) -> dict[str, Any]:
        by_type: dict[str, int] = {}
        by_status: dict[str, int] = {}
        for s in self._sources.values():
            by_type[s.source_type] = by_type.get(s.source_type, 0) + 1
            by_status[s.status] = by_status.get(s.status, 0) + 1
        return {
            "total": len(self._sources),
            "by_type": by_type,
            "by_status": by_status,
        }
