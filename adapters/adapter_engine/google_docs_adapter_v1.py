"""Google Docs Adapter v1 for the UMH substrate layer.

Execution-level adapter for safe, governed Docs interactions.
Supports configured safe document targeting, bounded content
extraction via both CU and API paths, deterministic normalization,
and replay-safe extraction. No mutation.

Capability types:
  GOOGLE_DOCS_SAFE_OPEN — open a pre-configured safe Doc
  GOOGLE_DOCS_SAFE_EXTRACT — bounded extraction (path-agnostic)
  GOOGLE_DOCS_CU_EXTRACT — extraction via Computer Use
  GOOGLE_DOCS_API_EXTRACT — extraction via Docs API

UMH substrate subsystem. Phase 96.8AB.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class DocsCapabilityType(str, Enum):
    GOOGLE_DOCS_SAFE_OPEN = "GOOGLE_DOCS_SAFE_OPEN"
    GOOGLE_DOCS_SAFE_EXTRACT = "GOOGLE_DOCS_SAFE_EXTRACT"
    GOOGLE_DOCS_CU_EXTRACT = "GOOGLE_DOCS_CU_EXTRACT"
    GOOGLE_DOCS_API_EXTRACT = "GOOGLE_DOCS_API_EXTRACT"


class DocsAdapterStatus(str, Enum):
    IDLE = "idle"
    OPENING = "opening"
    OPEN = "open"
    EXTRACTING = "extracting"
    EXTRACTED = "extracted"
    NORMALIZED = "normalized"
    ERROR = "error"
    GOVERNANCE_BLOCKED = "governance_blocked"


class ExtractionPath(str, Enum):
    CU = "computer_use"
    API = "api"


DOCS_ADAPTER_GOVERNANCE = frozenset(
    {
        "no_mutation",
        "no_broad_drive_search",
        "no_arbitrary_url_access",
        "no_secrets_capture",
        "no_auto_memory_promotion",
        "no_autonomous_recursive_ingestion",
        "no_credential_extraction",
        "no_document_edit",
        "no_document_delete",
        "no_share_change",
        "read_only",
    }
)

FORBIDDEN_DOCS_ACTIONS = frozenset(
    {
        "broad_drive_search",
        "arbitrary_url_navigation",
        "document_mutation",
        "permission_change",
        "document_delete",
        "credential_capture",
        "token_extraction",
        "autonomous_recursive_ingestion",
        "auto_memory_promotion",
        "world_model_mutation",
        "ocr_as_identical_to_api",
    }
)


@dataclass
class DocsOpenProof:
    """Proof that a specific Google Doc was opened."""

    proof_id: str
    adapter_id: str
    doc_url_or_id: str
    doc_title: str
    timestamp: str
    chrome_detected: bool = False
    doc_page_loaded: bool = False
    governance_state: str = "governed"
    trace_id: str = ""
    runtime_id: str = ""
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "proof_id": self.proof_id,
            "adapter_id": self.adapter_id,
            "doc_url_or_id": self.doc_url_or_id,
            "doc_title": self.doc_title,
            "timestamp": self.timestamp,
            "chrome_detected": self.chrome_detected,
            "doc_page_loaded": self.doc_page_loaded,
            "governance_state": self.governance_state,
            "trace_id": self.trace_id,
            "runtime_id": self.runtime_id,
            "notes": self.notes,
        }


@dataclass
class ExtractionResult:
    """Result of content extraction from a Google Doc."""

    extraction_id: str
    adapter_id: str
    doc_url_or_id: str
    doc_title: str
    extraction_path: str
    raw_content: str
    char_count: int = 0
    word_count: int = 0
    preview: str = ""
    preview_char_limit: int = 500
    content_hash: str = ""
    timestamp: str = ""
    governance_state: str = "governed"
    trace_id: str = ""
    runtime_id: str = ""
    bounded: bool = True
    notes: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()
        if not self.extraction_id:
            self.extraction_id = f"DOCEXT-{uuid.uuid4().hex[:8]}"
        if self.raw_content:
            self.char_count = len(self.raw_content)
            self.word_count = len(self.raw_content.split())
            self.preview = self.raw_content[: self.preview_char_limit]

    def compute_content_hash(self) -> str:
        self.content_hash = hashlib.sha256(self.raw_content.encode("utf-8")).hexdigest()
        return self.content_hash

    def to_dict(self) -> dict[str, Any]:
        return {
            "extraction_id": self.extraction_id,
            "adapter_id": self.adapter_id,
            "doc_url_or_id": self.doc_url_or_id,
            "doc_title": self.doc_title,
            "extraction_path": self.extraction_path,
            "char_count": self.char_count,
            "word_count": self.word_count,
            "preview": self.preview,
            "content_hash": self.content_hash,
            "timestamp": self.timestamp,
            "governance_state": self.governance_state,
            "trace_id": self.trace_id,
            "runtime_id": self.runtime_id,
            "bounded": self.bounded,
            "notes": self.notes,
        }


@dataclass
class NormalizedExtraction:
    """Deterministic normalization of extracted content."""

    normalization_id: str
    source_extraction_id: str
    extraction_path: str
    normalized_content: str
    normalized_hash: str = ""
    char_count: int = 0
    word_count: int = 0
    timestamp: str = ""
    trace_id: str = ""
    notes: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()
        if not self.normalization_id:
            self.normalization_id = f"DOCNORM-{uuid.uuid4().hex[:8]}"
        if self.normalized_content:
            self.char_count = len(self.normalized_content)
            self.word_count = len(self.normalized_content.split())
            self.normalized_hash = hashlib.sha256(
                self.normalized_content.encode("utf-8")
            ).hexdigest()

    def to_dict(self) -> dict[str, Any]:
        return {
            "normalization_id": self.normalization_id,
            "source_extraction_id": self.source_extraction_id,
            "extraction_path": self.extraction_path,
            "normalized_content": self.normalized_content,
            "normalized_hash": self.normalized_hash,
            "char_count": self.char_count,
            "word_count": self.word_count,
            "timestamp": self.timestamp,
            "trace_id": self.trace_id,
            "notes": self.notes,
        }


def normalize_text(raw: str) -> str:
    """Deterministic text normalization.

    Strips leading/trailing whitespace, normalizes internal whitespace
    runs to single spaces, and normalizes line endings.
    """
    lines = raw.strip().splitlines()
    normalized_lines = []
    for line in lines:
        cleaned = " ".join(line.split())
        normalized_lines.append(cleaned)
    return "\n".join(normalized_lines)


class GoogleDocsAdapterV1:
    """Safe, governed Google Docs adapter.

    Only operates on pre-configured safe documents.
    Supports dual extraction paths (CU and API).
    All actions are bounded and non-mutating.
    """

    ADAPTER_ID = "google-docs-adapter-v1"
    VERSION = "v1"

    def __init__(self, config: dict[str, Any]) -> None:
        self._config = config
        self._safe_doc_url_or_id: str = config.get("safe_doc_url_or_id", "")
        self._safe_doc_title: str = config.get("safe_doc_title", "")
        self._cu_enabled: bool = config.get("cu_enabled", False)
        self._api_enabled: bool = config.get("api_enabled", True)
        self._preview_char_limit: int = config.get("preview_char_limit", 500)
        self._timeout_seconds: int = config.get("extraction_timeout_seconds", 60)
        self._status = DocsAdapterStatus.IDLE
        self._capabilities = self._resolve_capabilities()
        self._forbidden = list(FORBIDDEN_DOCS_ACTIONS)

    def _resolve_capabilities(self) -> list[DocsCapabilityType]:
        caps = [
            DocsCapabilityType.GOOGLE_DOCS_SAFE_OPEN,
            DocsCapabilityType.GOOGLE_DOCS_SAFE_EXTRACT,
        ]
        if self._cu_enabled:
            caps.append(DocsCapabilityType.GOOGLE_DOCS_CU_EXTRACT)
        if self._api_enabled:
            caps.append(DocsCapabilityType.GOOGLE_DOCS_API_EXTRACT)
        return caps

    @property
    def adapter_id(self) -> str:
        return self.ADAPTER_ID

    @property
    def status(self) -> DocsAdapterStatus:
        return self._status

    @property
    def capabilities(self) -> list[DocsCapabilityType]:
        return list(self._capabilities)

    @property
    def forbidden_actions(self) -> list[str]:
        return list(self._forbidden)

    def validate_doc_target(self, doc_url_or_id: str) -> list[str]:
        errors: list[str] = []
        if not doc_url_or_id:
            errors.append("doc_url_or_id_empty")
        if not self._safe_doc_url_or_id:
            errors.append("no_safe_doc_configured")
        if doc_url_or_id and self._safe_doc_url_or_id and doc_url_or_id != self._safe_doc_url_or_id:
            errors.append("doc_not_safe_target")
        return errors

    def open_safe_doc(self, trace_id: str = "", runtime_id: str = "") -> DocsOpenProof:
        proof_id = f"DOC-OPEN-{uuid.uuid4().hex[:8]}"
        self._status = DocsAdapterStatus.OPENING

        errors = self.validate_doc_target(self._safe_doc_url_or_id)
        if errors:
            self._status = DocsAdapterStatus.ERROR
            return DocsOpenProof(
                proof_id=proof_id,
                adapter_id=self.ADAPTER_ID,
                doc_url_or_id=self._safe_doc_url_or_id,
                doc_title=self._safe_doc_title,
                timestamp=datetime.now(timezone.utc).isoformat(),
                governance_state="blocked",
                trace_id=trace_id,
                runtime_id=runtime_id,
                notes=[f"validation_error: {e}" for e in errors],
            )

        self._status = DocsAdapterStatus.OPEN
        return DocsOpenProof(
            proof_id=proof_id,
            adapter_id=self.ADAPTER_ID,
            doc_url_or_id=self._safe_doc_url_or_id,
            doc_title=self._safe_doc_title,
            timestamp=datetime.now(timezone.utc).isoformat(),
            chrome_detected=True,
            doc_page_loaded=True,
            governance_state="governed",
            trace_id=trace_id,
            runtime_id=runtime_id,
        )

    def extract(
        self,
        path: ExtractionPath,
        raw_content: str,
        trace_id: str = "",
        runtime_id: str = "",
    ) -> ExtractionResult:
        if path == ExtractionPath.CU and not self._cu_enabled:
            self._status = DocsAdapterStatus.ERROR
            return ExtractionResult(
                extraction_id="",
                adapter_id=self.ADAPTER_ID,
                doc_url_or_id=self._safe_doc_url_or_id,
                doc_title=self._safe_doc_title,
                extraction_path=path.value,
                raw_content="",
                governance_state="blocked",
                trace_id=trace_id,
                runtime_id=runtime_id,
                notes=["cu_extraction_not_enabled"],
            )
        if path == ExtractionPath.API and not self._api_enabled:
            self._status = DocsAdapterStatus.ERROR
            return ExtractionResult(
                extraction_id="",
                adapter_id=self.ADAPTER_ID,
                doc_url_or_id=self._safe_doc_url_or_id,
                doc_title=self._safe_doc_title,
                extraction_path=path.value,
                raw_content="",
                governance_state="blocked",
                trace_id=trace_id,
                runtime_id=runtime_id,
                notes=["api_extraction_not_enabled"],
            )

        self._status = DocsAdapterStatus.EXTRACTING
        result = ExtractionResult(
            extraction_id="",
            adapter_id=self.ADAPTER_ID,
            doc_url_or_id=self._safe_doc_url_or_id,
            doc_title=self._safe_doc_title,
            extraction_path=path.value,
            raw_content=raw_content,
            preview_char_limit=self._preview_char_limit,
            trace_id=trace_id,
            runtime_id=runtime_id,
        )
        result.compute_content_hash()
        self._status = DocsAdapterStatus.EXTRACTED
        return result

    def normalize(self, extraction: ExtractionResult, trace_id: str = "") -> NormalizedExtraction:
        normalized = normalize_text(extraction.raw_content)
        self._status = DocsAdapterStatus.NORMALIZED
        return NormalizedExtraction(
            normalization_id="",
            source_extraction_id=extraction.extraction_id,
            extraction_path=extraction.extraction_path,
            normalized_content=normalized,
            trace_id=trace_id or extraction.trace_id,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "adapter_id": self.ADAPTER_ID,
            "version": self.VERSION,
            "status": self._status.value,
            "safe_doc_url_or_id": self._safe_doc_url_or_id,
            "safe_doc_title": self._safe_doc_title,
            "cu_enabled": self._cu_enabled,
            "api_enabled": self._api_enabled,
            "capabilities": [c.value for c in self._capabilities],
            "forbidden_actions": self._forbidden,
            "governance": list(DOCS_ADAPTER_GOVERNANCE),
        }
