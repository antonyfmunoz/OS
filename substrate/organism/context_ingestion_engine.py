"""Context Ingestion Engine — ingest local/system context sources.

Registers sources, creates ingestion jobs, extracts claims/entities/decisions
from local audit docs, JSON artifacts, and system state. Phase 13.3 focuses
on local/system ingestion — no external API calls.

Phase 13.3. UMH substrate subsystem. Instance-agnostic.
"""

from __future__ import annotations

import glob
import json
import logging
import os
import re
import time
from typing import Any
from uuid import uuid4

from substrate.organism.source_registry import (
    ContextSource,
    SourceRegistry,
    SourceType,
    SourceStatus,
    SyncPolicy,
    Canonicality,
)
from substrate.organism.ingestion_job import (
    IngestionJob,
    IngestionJobStore,
    IngestedItem,
    JobType,
    JobStatus,
)

logger = logging.getLogger(__name__)

_REPO_ROOT = os.environ.get("UMH_ROOT", "/opt/OS")

_MAX_FILE_SIZE = 512 * 1024  # 512 KB
_ALLOWED_EXTENSIONS = frozenset({
    ".md", ".json", ".jsonl", ".txt", ".yaml", ".yml", ".toml",
})
_BLOCKED_PATTERNS = frozenset({
    ".env", "credentials", "secret", "token", "password", "private_key",
})

_CLAIM_PATTERNS = [
    re.compile(r"(?:is|are|was|were|has|have|will|shall)\s+(?:a|an|the)?\s*(\w[\w\s]{5,80})", re.IGNORECASE),
    re.compile(r"(?:handles?|manages?|provides?|supports?|includes?)\s+([\w\s]{5,80})", re.IGNORECASE),
]

_ENTITY_KNOWLEDGE_PATH = os.path.join(
    _REPO_ROOT, "data", "umh", "context_assimilation", "entity_knowledge.json"
)


def _load_entity_patterns() -> tuple[list[re.Pattern[str]], list[re.Pattern[str]]]:
    claim_extra: list[re.Pattern[str]] = []
    entity_pats: list[re.Pattern[str]] = []
    try:
        with open(_ENTITY_KNOWLEDGE_PATH) as f:
            knowledge = json.load(f)
        for pat_str in knowledge.get("claim_patterns_with_entities", []):
            claim_extra.append(re.compile(pat_str, re.IGNORECASE))
        for pat_str in knowledge.get("entity_patterns", []):
            entity_pats.append(re.compile(pat_str))
    except (FileNotFoundError, json.JSONDecodeError):
        pass
    return claim_extra, entity_pats

_DECISION_PATTERNS = [
    re.compile(r"(?:decided|decision|canonical|approved|confirmed)[:.]?\s+([\w\s]{5,120})", re.IGNORECASE),
    re.compile(r"(?:we\s+(?:chose|picked|selected|adopted))\s+([\w\s]{5,80})", re.IGNORECASE),
]


def _is_safe_path(path: str) -> bool:
    basename = os.path.basename(path).lower()
    for pattern in _BLOCKED_PATTERNS:
        if pattern in basename:
            return False
    return True


def _is_allowed_extension(path: str) -> bool:
    _, ext = os.path.splitext(path)
    return ext.lower() in _ALLOWED_EXTENSIONS


def _is_within_size_limit(path: str) -> bool:
    try:
        return os.path.getsize(path) <= _MAX_FILE_SIZE
    except OSError:
        return False


def _redact_secrets(text: str) -> str:
    text = re.sub(r'(?:api[_-]?key|token|secret|password)\s*[=:]\s*\S+', '[REDACTED]', text, flags=re.IGNORECASE)
    text = re.sub(r'[A-Za-z0-9+/]{40,}={0,2}', '[REDACTED_BASE64]', text)
    return text


def _extract_claims(text: str) -> list[str]:
    claims: list[str] = []
    claim_extra, _ = _load_entity_patterns()
    all_patterns = list(_CLAIM_PATTERNS) + claim_extra
    for pattern in all_patterns:
        for match in pattern.finditer(text):
            claim = match.group(0).strip()[:200]
            if len(claim) > 10 and claim not in claims:
                claims.append(claim)
            if len(claims) >= 20:
                return claims
    return claims


def _extract_entities(text: str) -> list[str]:
    entities: set[str] = set()
    _, entity_pats = _load_entity_patterns()
    for pattern in entity_pats:
        for match in pattern.finditer(text):
            entities.add(match.group(0).strip())
    return sorted(entities)


def _extract_decisions(text: str) -> list[str]:
    decisions: list[str] = []
    for pattern in _DECISION_PATTERNS:
        for match in pattern.finditer(text):
            dec = match.group(0).strip()[:200]
            if len(dec) > 10 and dec not in decisions:
                decisions.append(dec)
            if len(decisions) >= 10:
                return decisions
    return decisions


def _classify_freshness(path: str) -> str:
    try:
        mtime = os.path.getmtime(path)
        age_days = (time.time() - mtime) / 86400
        if age_days < 1:
            return "fresh"
        if age_days < 7:
            return "recent"
        if age_days < 30:
            return "aging"
        return "stale"
    except OSError:
        return "unknown"


class ContextIngestionEngine:
    def __init__(
        self,
        registry: SourceRegistry | None = None,
        job_store: IngestionJobStore | None = None,
    ) -> None:
        self._registry = registry or SourceRegistry()
        self._job_store = job_store or IngestionJobStore()

    @property
    def registry(self) -> SourceRegistry:
        return self._registry

    @property
    def job_store(self) -> IngestionJobStore:
        return self._job_store

    def register_source(self, source: ContextSource) -> ContextSource:
        return self._registry.register(source)

    def list_sources(self, **kwargs: Any) -> list[ContextSource]:
        return self._registry.list_sources(**kwargs)

    def create_ingestion_job(
        self,
        source_id: str,
        job_type: str = JobType.SCAN.value,
        scope: str = "",
        created_by: str = "system",
    ) -> IngestionJob | None:
        source = self._registry.get(source_id)
        if not source:
            logger.warning("Source %s not found", source_id)
            return None
        if source.sync_policy == SyncPolicy.IGNORE.value:
            logger.info("Source %s has ignore sync policy", source_id)
            return None
        job = IngestionJob(
            source_id=source_id,
            source_type=source.source_type,
            job_type=job_type,
            scope=scope,
            created_by=created_by,
        )
        return self._job_store.create_job(job)

    def run_metadata_scan(self, source_id: str) -> IngestionJob | None:
        source = self._registry.get(source_id)
        if not source or not source.location_ref:
            return None
        job = self.create_ingestion_job(source_id, JobType.METADATA_ONLY.value)
        if not job:
            return None
        self._job_store.update_job_status(job.job_id, JobStatus.RUNNING.value)
        location = source.location_ref
        if os.path.isdir(location):
            files = self._scan_directory(location)
            job.item_count = len(files)
            for fpath in files:
                item = IngestedItem(
                    job_id=job.job_id,
                    source_id=source_id,
                    item_type="file_metadata",
                    title=os.path.basename(fpath),
                    content_ref=fpath,
                    summary=f"File: {fpath} ({os.path.getsize(fpath)} bytes)",
                    freshness=_classify_freshness(fpath),
                )
                self._job_store.add_item(item)
                job.ingested_items += 1
        elif os.path.isfile(location):
            job.item_count = 1
            item = IngestedItem(
                job_id=job.job_id,
                source_id=source_id,
                item_type="file_metadata",
                title=os.path.basename(location),
                content_ref=location,
                summary=f"File: {location} ({os.path.getsize(location)} bytes)",
                freshness=_classify_freshness(location),
            )
            self._job_store.add_item(item)
            job.ingested_items = 1
        self._job_store.update_job_status(job.job_id, JobStatus.COMPLETED.value)
        self._registry.mark_ingested(source_id)
        return self._job_store.get_job(job.job_id)

    def run_local_audit_ingestion(self, source_id: str) -> IngestionJob | None:
        source = self._registry.get(source_id)
        if not source or not source.location_ref:
            return None
        job = self.create_ingestion_job(source_id, JobType.EXTRACT_CLAIMS.value)
        if not job:
            return None
        self._job_store.update_job_status(job.job_id, JobStatus.RUNNING.value)
        location = source.location_ref
        files = self._scan_directory(location) if os.path.isdir(location) else [location]
        files = [f for f in files if _is_allowed_extension(f) and _is_safe_path(f) and _is_within_size_limit(f)]
        job.item_count = len(files)

        for fpath in files:
            try:
                with open(fpath) as fp:
                    content = fp.read()
                content = _redact_secrets(content)
                claims = _extract_claims(content)
                entities = _extract_entities(content)
                decisions = _extract_decisions(content)

                item = IngestedItem(
                    job_id=job.job_id,
                    source_id=source_id,
                    item_type="audit_doc" if fpath.endswith(".md") else "artifact",
                    title=os.path.basename(fpath),
                    content_ref=fpath,
                    summary=content[:300] if len(content) > 300 else content,
                    extracted_claims=claims,
                    extracted_entities=entities,
                    extracted_decisions=decisions,
                    freshness=_classify_freshness(fpath),
                    confidence=0.6,
                    raw_content_stored=False,
                )
                self._job_store.add_item(item)
                job.ingested_items += 1
                job.extracted_entities.extend(e for e in entities if e not in job.extracted_entities)
                job.extracted_claims.extend(c for c in claims if c not in job.extracted_claims)
                job.extracted_decisions.extend(d for d in decisions if d not in job.extracted_decisions)
            except (OSError, UnicodeDecodeError) as exc:
                logger.warning("Failed to ingest %s: %s", fpath, exc)
                job.failed_items += 1

        status = JobStatus.COMPLETED.value if job.failed_items == 0 else JobStatus.PARTIAL.value
        self._job_store.update_job_status(job.job_id, status)
        self._registry.mark_ingested(source_id)
        self._job_store._save_jobs()
        return self._job_store.get_job(job.job_id)

    def run_local_artifact_ingestion(self, source_id: str) -> IngestionJob | None:
        source = self._registry.get(source_id)
        if not source or not source.location_ref:
            return None
        job = self.create_ingestion_job(source_id, JobType.EXTRACT_ENTITIES.value)
        if not job:
            return None
        self._job_store.update_job_status(job.job_id, JobStatus.RUNNING.value)
        location = source.location_ref
        files = self._scan_directory(location) if os.path.isdir(location) else [location]
        files = [
            f for f in files
            if f.endswith((".json", ".jsonl"))
            and _is_safe_path(f)
            and _is_within_size_limit(f)
        ]
        job.item_count = len(files)

        for fpath in files:
            try:
                with open(fpath) as fp:
                    raw = fp.read()
                raw = _redact_secrets(raw)
                entities = _extract_entities(raw)
                item = IngestedItem(
                    job_id=job.job_id,
                    source_id=source_id,
                    item_type="json_artifact",
                    title=os.path.basename(fpath),
                    content_ref=fpath,
                    summary=raw[:200],
                    extracted_entities=entities,
                    freshness=_classify_freshness(fpath),
                    confidence=0.7,
                    raw_content_stored=False,
                )
                self._job_store.add_item(item)
                job.ingested_items += 1
                job.extracted_entities.extend(e for e in entities if e not in job.extracted_entities)
            except (OSError, json.JSONDecodeError, UnicodeDecodeError) as exc:
                logger.warning("Failed to ingest artifact %s: %s", fpath, exc)
                job.failed_items += 1

        status = JobStatus.COMPLETED.value if job.failed_items == 0 else JobStatus.PARTIAL.value
        self._job_store.update_job_status(job.job_id, status)
        self._registry.mark_ingested(source_id)
        self._job_store._save_jobs()
        return self._job_store.get_job(job.job_id)

    def seed_local_sources(self) -> list[ContextSource]:
        seeds = [
            ContextSource(
                source_type=SourceType.GITHUB_REPO.value,
                title="UMH OS Repository",
                description="Primary UMH codebase",
                location_ref=_REPO_ROOT,
                sync_policy=SyncPolicy.CANONICAL_SOURCE.value,
                canonicality=Canonicality.CANONICAL.value,
                trust_level=0.9,
                domain_tags=["infrastructure", "substrate", "codebase"],
            ),
            ContextSource(
                source_type=SourceType.AUDIT_DOC.value,
                title="Convergence Audit Documents",
                description="Phase audit reports in docs/audits/convergence/",
                location_ref=os.path.join(_REPO_ROOT, "docs", "audits", "convergence"),
                sync_policy=SyncPolicy.READ_ONLY.value,
                canonicality=Canonicality.CANONICAL.value,
                trust_level=0.85,
                domain_tags=["audits", "phases", "convergence"],
            ),
            ContextSource(
                source_type=SourceType.RUNTIME_ARTIFACT.value,
                title="UMH Runtime Artifacts",
                description="Production data artifacts in data/umh/",
                location_ref=os.path.join(_REPO_ROOT, "data", "umh"),
                sync_policy=SyncPolicy.READ_ONLY.value,
                canonicality=Canonicality.CANONICAL.value,
                trust_level=0.8,
                domain_tags=["runtime", "artifacts", "organism"],
            ),
            ContextSource(
                source_type=SourceType.WORK_PACKET.value,
                title="Universal Work Queue",
                description="Work packets in substrate/organism/",
                location_ref=os.path.join(_REPO_ROOT, "data", "umh", "organism"),
                sync_policy=SyncPolicy.READ_ONLY.value,
                canonicality=Canonicality.CANONICAL.value,
                trust_level=0.85,
                domain_tags=["work_packets", "execution"],
            ),
            ContextSource(
                source_type=SourceType.LOCAL_DOC.value,
                title="Planning State",
                description="Project planning state in .planning/",
                location_ref=os.path.join(_REPO_ROOT, ".planning"),
                sync_policy=SyncPolicy.READ_ONLY.value,
                canonicality=Canonicality.CANONICAL.value,
                trust_level=0.9,
                domain_tags=["planning", "roadmap", "state"],
            ),
            ContextSource(
                source_type=SourceType.KNOWLEDGE_MODEL.value,
                title="Knowledge System",
                description="Wiki and knowledge docs in knowledge/",
                location_ref=os.path.join(_REPO_ROOT, "knowledge"),
                sync_policy=SyncPolicy.READ_ONLY.value,
                canonicality=Canonicality.REFERENCE_ONLY.value,
                trust_level=0.7,
                domain_tags=["knowledge", "wiki", "reference"],
            ),
        ]
        registered: list[ContextSource] = []
        for seed in seeds:
            if os.path.exists(seed.location_ref):
                registered.append(self.register_source(seed))
        return registered

    def prevent_duplicate_ingestion(self, source_id: str) -> bool:
        recent_jobs = self._job_store.list_jobs(source_id=source_id)
        if not recent_jobs:
            return False
        latest = max(recent_jobs, key=lambda j: j.completed_at or 0)
        if latest.status in (JobStatus.COMPLETED.value, JobStatus.PARTIAL.value):
            age = time.time() - (latest.completed_at or 0)
            if age < 3600:
                return True
        return False

    def summarize_ingestion(self) -> dict[str, Any]:
        jobs = self._job_store.list_jobs()
        items = self._job_store.list_items()
        all_entities: set[str] = set()
        all_claims: list[str] = []
        for job in jobs:
            all_entities.update(job.extracted_entities)
            all_claims.extend(c for c in job.extracted_claims if c not in all_claims)
        return {
            "total_jobs": len(jobs),
            "total_items": len(items),
            "completed_jobs": sum(1 for j in jobs if j.status == JobStatus.COMPLETED.value),
            "unique_entities": sorted(all_entities),
            "total_claims": len(all_claims),
            "sources": self._registry.summary(),
        }

    def _scan_directory(self, directory: str, max_files: int = 200) -> list[str]:
        found: list[str] = []
        for root, _dirs, files in os.walk(directory):
            if any(skip in root for skip in ("__pycache__", ".git", "node_modules", ".mypy_cache")):
                continue
            for fname in sorted(files):
                fpath = os.path.join(root, fname)
                if _is_allowed_extension(fpath) and _is_safe_path(fpath):
                    found.append(fpath)
                    if len(found) >= max_files:
                        return found
        return found
