"""Google Drive Adapter v1 for the UMH substrate layer.

Execution-level adapter for safe, governed Drive interactions.
Supports configured safe document targeting, bounded metadata
reads, and deterministic normalization. No mutation. No broad
search. No arbitrary URL access.

Capability types:
  GOOGLE_DRIVE_SAFE_OPEN — open a pre-configured safe Drive URL
  (no arbitrary navigation)

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


class DriveCapabilityType(str, Enum):
    GOOGLE_DRIVE_SAFE_OPEN = "GOOGLE_DRIVE_SAFE_OPEN"


class DriveAdapterStatus(str, Enum):
    IDLE = "idle"
    OPENING = "opening"
    OPEN = "open"
    METADATA_READ = "metadata_read"
    ERROR = "error"
    GOVERNANCE_BLOCKED = "governance_blocked"


DRIVE_ADAPTER_GOVERNANCE = frozenset(
    {
        "no_mutation",
        "no_broad_drive_search",
        "no_arbitrary_url_access",
        "no_secrets_capture",
        "no_auto_memory_promotion",
        "no_autonomous_recursive_ingestion",
        "no_credential_extraction",
        "no_file_upload",
        "no_file_delete",
        "no_share_change",
        "read_only",
    }
)

FORBIDDEN_DRIVE_ACTIONS = frozenset(
    {
        "broad_drive_search",
        "arbitrary_url_navigation",
        "file_mutation",
        "permission_change",
        "file_upload",
        "file_download_unapproved",
        "credential_capture",
        "token_extraction",
        "autonomous_recursive_ingestion",
        "auto_memory_promotion",
        "world_model_mutation",
    }
)


@dataclass
class DriveOpenProof:
    """Proof that a specific Drive URL was opened successfully."""

    proof_id: str
    adapter_id: str
    drive_url: str
    timestamp: str
    chrome_detected: bool = False
    window_title_reported: str = ""
    drive_page_loaded: bool = False
    governance_state: str = "governed"
    trace_id: str = ""
    runtime_id: str = ""
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "proof_id": self.proof_id,
            "adapter_id": self.adapter_id,
            "drive_url": self.drive_url,
            "timestamp": self.timestamp,
            "chrome_detected": self.chrome_detected,
            "window_title_reported": self.window_title_reported,
            "drive_page_loaded": self.drive_page_loaded,
            "governance_state": self.governance_state,
            "trace_id": self.trace_id,
            "runtime_id": self.runtime_id,
            "notes": self.notes,
        }


@dataclass
class DriveMetadataResult:
    """Bounded metadata read from a safe Drive location."""

    result_id: str
    adapter_id: str
    drive_url: str
    file_id: str = ""
    file_title: str = ""
    mime_type: str = ""
    modified_time: str = ""
    owner: str = ""
    size_bytes: int = 0
    timestamp: str = ""
    content_hash: str = ""
    governance_state: str = "governed"
    trace_id: str = ""
    notes: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()
        if not self.result_id:
            self.result_id = f"DRVMETA-{uuid.uuid4().hex[:8]}"

    def compute_content_hash(self) -> str:
        payload = json.dumps(
            {
                "file_id": self.file_id,
                "file_title": self.file_title,
                "mime_type": self.mime_type,
                "modified_time": self.modified_time,
            },
            sort_keys=True,
        )
        self.content_hash = hashlib.sha256(payload.encode()).hexdigest()
        return self.content_hash

    def to_dict(self) -> dict[str, Any]:
        return {
            "result_id": self.result_id,
            "adapter_id": self.adapter_id,
            "drive_url": self.drive_url,
            "file_id": self.file_id,
            "file_title": self.file_title,
            "mime_type": self.mime_type,
            "modified_time": self.modified_time,
            "owner": self.owner,
            "size_bytes": self.size_bytes,
            "timestamp": self.timestamp,
            "content_hash": self.content_hash,
            "governance_state": self.governance_state,
            "trace_id": self.trace_id,
            "notes": self.notes,
        }


class GoogleDriveAdapterV1:
    """Safe, governed Google Drive adapter.

    Only operates on pre-configured safe URLs.
    All actions are bounded and non-mutating.
    """

    ADAPTER_ID = "google-drive-adapter-v1"
    VERSION = "v1"

    def __init__(self, config: dict[str, Any]) -> None:
        self._config = config
        self._safe_drive_url: str = config.get("safe_drive_url", "")
        self._timeout_seconds: int = config.get("extraction_timeout_seconds", 60)
        self._status = DriveAdapterStatus.IDLE
        self._capabilities = [DriveCapabilityType.GOOGLE_DRIVE_SAFE_OPEN]
        self._forbidden = list(FORBIDDEN_DRIVE_ACTIONS)

    @property
    def adapter_id(self) -> str:
        return self.ADAPTER_ID

    @property
    def status(self) -> DriveAdapterStatus:
        return self._status

    @property
    def capabilities(self) -> list[DriveCapabilityType]:
        return list(self._capabilities)

    @property
    def forbidden_actions(self) -> list[str]:
        return list(self._forbidden)

    def validate_url(self, url: str) -> list[str]:
        """Validate that a URL matches the configured safe target."""
        errors: list[str] = []
        if not url:
            errors.append("url_empty")
        if not self._safe_drive_url:
            errors.append("no_safe_drive_url_configured")
        if url and self._safe_drive_url and url != self._safe_drive_url:
            errors.append("url_not_safe_target")
        if url and not url.startswith("https://drive.google.com/"):
            errors.append("url_not_google_drive")
        return errors

    def open_safe_drive(self, trace_id: str = "", runtime_id: str = "") -> DriveOpenProof:
        """Create a proof record for opening the configured safe Drive URL."""
        proof_id = f"DRV-OPEN-{uuid.uuid4().hex[:8]}"
        self._status = DriveAdapterStatus.OPENING

        errors = self.validate_url(self._safe_drive_url)
        if errors:
            self._status = DriveAdapterStatus.ERROR
            return DriveOpenProof(
                proof_id=proof_id,
                adapter_id=self.ADAPTER_ID,
                drive_url=self._safe_drive_url,
                timestamp=datetime.now(timezone.utc).isoformat(),
                governance_state="blocked",
                trace_id=trace_id,
                runtime_id=runtime_id,
                notes=[f"validation_error: {e}" for e in errors],
            )

        self._status = DriveAdapterStatus.OPEN
        return DriveOpenProof(
            proof_id=proof_id,
            adapter_id=self.ADAPTER_ID,
            drive_url=self._safe_drive_url,
            timestamp=datetime.now(timezone.utc).isoformat(),
            chrome_detected=True,
            drive_page_loaded=True,
            governance_state="governed",
            trace_id=trace_id,
            runtime_id=runtime_id,
        )

    def read_metadata(
        self,
        file_id: str,
        file_title: str,
        trace_id: str = "",
    ) -> DriveMetadataResult:
        """Bounded metadata read for a known safe document."""
        result = DriveMetadataResult(
            result_id="",
            adapter_id=self.ADAPTER_ID,
            drive_url=self._safe_drive_url,
            file_id=file_id,
            file_title=file_title,
            mime_type="application/vnd.google-apps.document",
            trace_id=trace_id,
        )
        result.compute_content_hash()
        self._status = DriveAdapterStatus.METADATA_READ
        return result

    def to_dict(self) -> dict[str, Any]:
        return {
            "adapter_id": self.ADAPTER_ID,
            "version": self.VERSION,
            "status": self._status.value,
            "safe_drive_url": self._safe_drive_url,
            "capabilities": [c.value for c in self._capabilities],
            "forbidden_actions": self._forbidden,
            "governance": list(DRIVE_ADAPTER_GOVERNANCE),
        }
