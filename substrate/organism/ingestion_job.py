"""Ingestion Job — tracks context ingestion work units.

An IngestionJob represents a single ingestion run against a registered
context source. It tracks scope, status, extracted entities/claims/decisions,
and output artifacts.

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
_JOBS_PATH = os.path.join(
    _REPO_ROOT, "data", "umh", "context_assimilation", "ingestion_jobs.jsonl"
)
_ITEMS_PATH = os.path.join(
    _REPO_ROOT, "data", "umh", "context_assimilation", "ingested_items.jsonl"
)


class JobType(str, Enum):
    SCAN = "scan"
    METADATA_ONLY = "metadata_only"
    EXTRACT_SUMMARY = "extract_summary"
    EXTRACT_CLAIMS = "extract_claims"
    EXTRACT_ENTITIES = "extract_entities"
    EXTRACT_DECISIONS = "extract_decisions"
    EXTRACT_WORK_ITEMS = "extract_work_items"
    DIAGNOSTIC = "diagnostic"
    RECONCILIATION = "reconciliation"


class JobStatus(str, Enum):
    DRAFTED = "drafted"
    APPROVED = "approved"
    RUNNING = "running"
    COMPLETED = "completed"
    PARTIAL = "partial"
    FAILED = "failed"
    BLOCKED = "blocked"
    CANCELLED = "cancelled"


@dataclass
class IngestedItem:
    item_id: str = ""
    job_id: str = ""
    source_id: str = ""
    item_type: str = ""
    title: str = ""
    content_ref: str = ""
    summary: str = ""
    extracted_claims: list[str] = field(default_factory=list)
    extracted_entities: list[str] = field(default_factory=list)
    extracted_decisions: list[str] = field(default_factory=list)
    extracted_work_items: list[str] = field(default_factory=list)
    freshness: str = "unknown"
    confidence: float = 0.5
    evidence: list[str] = field(default_factory=list)
    raw_content_stored: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.item_id:
            self.item_id = f"item-{uuid4().hex[:8]}"

    def to_dict(self) -> dict[str, Any]:
        return {
            "item_id": self.item_id,
            "job_id": self.job_id,
            "source_id": self.source_id,
            "item_type": self.item_type,
            "title": self.title,
            "content_ref": self.content_ref,
            "summary": self.summary,
            "extracted_claims": self.extracted_claims,
            "extracted_entities": self.extracted_entities,
            "extracted_decisions": self.extracted_decisions,
            "extracted_work_items": self.extracted_work_items,
            "freshness": self.freshness,
            "confidence": self.confidence,
            "evidence": self.evidence,
            "raw_content_stored": self.raw_content_stored,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> IngestedItem:
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


@dataclass
class IngestionJob:
    job_id: str = ""
    source_id: str = ""
    source_type: str = ""
    job_type: str = JobType.SCAN.value
    status: str = JobStatus.DRAFTED.value
    scope: str = ""
    started_at: float = 0.0
    completed_at: float = 0.0
    created_by: str = ""
    approved_by: str = ""
    risk_class: str = "low"
    item_count: int = 0
    ingested_items: int = 0
    skipped_items: int = 0
    failed_items: int = 0
    extracted_entities: list[str] = field(default_factory=list)
    extracted_decisions: list[str] = field(default_factory=list)
    extracted_claims: list[str] = field(default_factory=list)
    extracted_work_packets: list[str] = field(default_factory=list)
    extracted_open_questions: list[str] = field(default_factory=list)
    output_artifacts: list[str] = field(default_factory=list)
    error: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.job_id:
            self.job_id = f"job-{uuid4().hex[:8]}"

    def to_dict(self) -> dict[str, Any]:
        return {
            "job_id": self.job_id,
            "source_id": self.source_id,
            "source_type": self.source_type,
            "job_type": self.job_type,
            "status": self.status,
            "scope": self.scope,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "created_by": self.created_by,
            "approved_by": self.approved_by,
            "risk_class": self.risk_class,
            "item_count": self.item_count,
            "ingested_items": self.ingested_items,
            "skipped_items": self.skipped_items,
            "failed_items": self.failed_items,
            "extracted_entities": self.extracted_entities,
            "extracted_decisions": self.extracted_decisions,
            "extracted_claims": self.extracted_claims,
            "extracted_work_packets": self.extracted_work_packets,
            "extracted_open_questions": self.extracted_open_questions,
            "output_artifacts": self.output_artifacts,
            "error": self.error,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> IngestionJob:
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


class IngestionJobStore:
    def __init__(
        self, jobs_path: str | None = None, items_path: str | None = None
    ) -> None:
        self._jobs_path = jobs_path or _JOBS_PATH
        self._items_path = items_path or _ITEMS_PATH
        self._jobs: dict[str, IngestionJob] = {}
        self._items: dict[str, IngestedItem] = {}
        self._load()

    def _load(self) -> None:
        for path, store, cls in [
            (self._jobs_path, self._jobs, IngestionJob),
            (self._items_path, self._items, IngestedItem),
        ]:
            if not os.path.exists(path):
                continue
            with open(path) as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        d = json.loads(line)
                        obj = cls.from_dict(d)
                        id_field = "job_id" if cls is IngestionJob else "item_id"
                        store[getattr(obj, id_field)] = obj
                    except (json.JSONDecodeError, TypeError):
                        logger.warning("Skipping malformed %s line", cls.__name__)

    def _save_jobs(self) -> None:
        os.makedirs(os.path.dirname(self._jobs_path), exist_ok=True)
        with open(self._jobs_path, "w") as f:
            for job in self._jobs.values():
                f.write(json.dumps(job.to_dict(), default=str) + "\n")

    def _save_items(self) -> None:
        os.makedirs(os.path.dirname(self._items_path), exist_ok=True)
        with open(self._items_path, "w") as f:
            for item in self._items.values():
                f.write(json.dumps(item.to_dict(), default=str) + "\n")

    def create_job(self, job: IngestionJob) -> IngestionJob:
        self._jobs[job.job_id] = job
        self._save_jobs()
        return job

    def get_job(self, job_id: str) -> IngestionJob | None:
        return self._jobs.get(job_id)

    def list_jobs(
        self, source_id: str | None = None, status: str | None = None
    ) -> list[IngestionJob]:
        result = list(self._jobs.values())
        if source_id:
            result = [j for j in result if j.source_id == source_id]
        if status:
            result = [j for j in result if j.status == status]
        return result

    def update_job_status(self, job_id: str, status: str) -> bool:
        job = self._jobs.get(job_id)
        if not job:
            return False
        job.status = status
        if status == JobStatus.RUNNING.value:
            job.started_at = time.time()
        elif status in (
            JobStatus.COMPLETED.value,
            JobStatus.PARTIAL.value,
            JobStatus.FAILED.value,
        ):
            job.completed_at = time.time()
        self._save_jobs()
        return True

    def add_item(self, item: IngestedItem) -> IngestedItem:
        self._items[item.item_id] = item
        self._save_items()
        return item

    def get_items_for_job(self, job_id: str) -> list[IngestedItem]:
        return [i for i in self._items.values() if i.job_id == job_id]

    def list_items(self, source_id: str | None = None) -> list[IngestedItem]:
        result = list(self._items.values())
        if source_id:
            result = [i for i in result if i.source_id == source_id]
        return result

    def count_jobs(self) -> int:
        return len(self._jobs)

    def count_items(self) -> int:
        return len(self._items)
