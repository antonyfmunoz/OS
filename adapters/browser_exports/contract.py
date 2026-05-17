"""Browser export contract — data classes for export requests and results."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class ExportRequest:
    """Request to trigger a data export from a web service."""

    service: str  # "claude" | "chatgpt" | "instagram"
    credentials_ref: str  # env var prefix or profile path
    output_dir: Path
    mfa_handler: str | None = None  # "totp" | "email_2fa" | "manual" | None


@dataclass
class ExportResult:
    """Result of an export attempt."""

    service: str
    status: str  # "export_requested" | "export_downloaded" | "failed"
    exported_files: list[Path] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    timestamp: str = ""
    error: str | None = None
