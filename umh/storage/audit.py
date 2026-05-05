"""Phase 82 storage audit — read-only scan for persistence boundary bypasses.

Scans project files using AST or text matching to identify likely direct file
writes, JSON dumps, destructive operations, and append-only violations.

Read-only. Does not import or execute target modules.
No execution. No adapter calls. No LLM calls.
"""

from __future__ import annotations

import ast
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from umh.core.clock import iso_now as _iso_now


class StorageAuditSeverity:
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


@dataclass
class StorageAuditFinding:
    finding_id: str
    severity: str = "warning"
    file_path: str = ""
    module: str = ""
    finding_type: str = ""
    message: str = ""
    recommendation: str = ""
    line_number: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "finding_id": self.finding_id,
            "severity": self.severity,
            "file_path": self.file_path,
            "module": self.module,
            "finding_type": self.finding_type,
            "message": self.message,
            "recommendation": self.recommendation,
            "line_number": self.line_number,
            "metadata": self.metadata,
        }


@dataclass
class StorageAuditReport:
    generated_at: str = ""
    findings: list[StorageAuditFinding] = field(default_factory=list)
    total_findings: int = 0
    critical_count: int = 0
    error_count: int = 0
    warning_count: int = 0
    info_count: int = 0
    checked_paths: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "generated_at": self.generated_at,
            "findings": [f.to_dict() for f in self.findings],
            "total_findings": self.total_findings,
            "critical_count": self.critical_count,
            "error_count": self.error_count,
            "warning_count": self.warning_count,
            "info_count": self.info_count,
            "checked_paths": self.checked_paths,
            "metadata": self.metadata,
        }


def _finding_id() -> str:
    return f"saf_{uuid.uuid4().hex[:10]}"


def _make_finding(
    severity: str,
    file_path: str,
    finding_type: str,
    message: str,
    recommendation: str,
    line_number: int = 0,
) -> StorageAuditFinding:
    return StorageAuditFinding(
        finding_id=_finding_id(),
        severity=severity,
        file_path=str(file_path),
        finding_type=finding_type,
        message=message,
        recommendation=recommendation,
        line_number=line_number,
    )


def _collect_python_files(root: str, include_tests: bool = False) -> list[Path]:
    root_path = Path(root)
    paths: list[Path] = []
    for py_file in root_path.rglob("*.py"):
        rel = str(py_file.relative_to(root_path))
        if "__pycache__" in rel:
            continue
        if not include_tests and rel.startswith("tests/"):
            continue
        if rel.startswith(("venv/", ".venv/", "node_modules/", "saas/")):
            continue
        paths.append(py_file)
    return sorted(paths)


def scan_for_direct_file_writes(paths: list[Path]) -> list[StorageAuditFinding]:
    findings: list[StorageAuditFinding] = []
    patterns = ["open(", "Path(", "pathlib"]
    write_modes = ["'w'", '"w"', "'w+'", '"w+"', "'a'", '"a"', "'a+'", '"a+"', "'wb'", '"wb"']

    for path in paths:
        try:
            src = path.read_text(errors="replace")
        except Exception:
            continue
        for i, line in enumerate(src.splitlines(), 1):
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            for wm in write_modes:
                if wm in stripped and ("open(" in stripped or "open (" in stripped):
                    findings.append(
                        _make_finding(
                            StorageAuditSeverity.WARNING,
                            str(path),
                            "direct_file_write",
                            f"Likely direct file write with mode {wm}",
                            "Consider routing through storage gateway",
                            line_number=i,
                        )
                    )
                    break
    return findings


def scan_for_json_dump_writes(paths: list[Path]) -> list[StorageAuditFinding]:
    findings: list[StorageAuditFinding] = []
    for path in paths:
        try:
            src = path.read_text(errors="replace")
        except Exception:
            continue
        for i, line in enumerate(src.splitlines(), 1):
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            if "json.dump(" in stripped and "json.dumps(" not in stripped:
                findings.append(
                    _make_finding(
                        StorageAuditSeverity.WARNING,
                        str(path),
                        "json_dump_write",
                        "Likely JSON file write via json.dump()",
                        "Consider routing through storage gateway",
                        line_number=i,
                    )
                )
    return findings


def scan_for_delete_clear_pop_methods(paths: list[Path]) -> list[StorageAuditFinding]:
    findings: list[StorageAuditFinding] = []
    patterns = [".clear()", ".pop(", "os.remove(", "os.unlink(", "shutil.rmtree("]

    for path in paths:
        try:
            src = path.read_text(errors="replace")
        except Exception:
            continue
        for i, line in enumerate(src.splitlines(), 1):
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            for pat in patterns:
                if pat in stripped:
                    findings.append(
                        _make_finding(
                            StorageAuditSeverity.WARNING,
                            str(path),
                            "destructive_operation",
                            f"Likely destructive operation: {pat.rstrip('(')}",
                            "Verify this does not bypass append-only constraints",
                            line_number=i,
                        )
                    )
                    break
    return findings


def scan_for_sqlite_direct_access(paths: list[Path]) -> list[StorageAuditFinding]:
    findings: list[StorageAuditFinding] = []
    for path in paths:
        try:
            src = path.read_text(errors="replace")
        except Exception:
            continue
        for i, line in enumerate(src.splitlines(), 1):
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            if "sqlite3.connect(" in stripped:
                findings.append(
                    _make_finding(
                        StorageAuditSeverity.INFO,
                        str(path),
                        "sqlite_direct_access",
                        "Direct SQLite connection",
                        "Ensure this goes through an approved store singleton",
                        line_number=i,
                    )
                )
    return findings


def scan_for_append_only_violations(paths: list[Path]) -> list[StorageAuditFinding]:
    findings: list[StorageAuditFinding] = []
    violation_keywords = [
        "DELETE FROM traces",
        "DELETE FROM trace_events",
        "UPDATE traces SET status",
        "DROP TABLE traces",
    ]

    for path in paths:
        try:
            src = path.read_text(errors="replace")
        except Exception:
            continue
        src_lower = src.lower()
        for kw in violation_keywords:
            if kw.lower() in src_lower:
                findings.append(
                    _make_finding(
                        StorageAuditSeverity.ERROR,
                        str(path),
                        "append_only_violation",
                        f"Likely append-only violation: {kw}",
                        "Traces and events must be append-only",
                    )
                )
    return findings


def audit_storage_boundaries(
    root_path: str = "/opt/OS",
    include_tests: bool = False,
) -> StorageAuditReport:
    paths = _collect_python_files(root_path, include_tests)
    findings: list[StorageAuditFinding] = []

    findings.extend(scan_for_direct_file_writes(paths))
    findings.extend(scan_for_json_dump_writes(paths))
    findings.extend(scan_for_delete_clear_pop_methods(paths))
    findings.extend(scan_for_sqlite_direct_access(paths))
    findings.extend(scan_for_append_only_violations(paths))

    critical = sum(1 for f in findings if f.severity == StorageAuditSeverity.CRITICAL)
    error = sum(1 for f in findings if f.severity == StorageAuditSeverity.ERROR)
    warning = sum(1 for f in findings if f.severity == StorageAuditSeverity.WARNING)
    info = sum(1 for f in findings if f.severity == StorageAuditSeverity.INFO)

    return StorageAuditReport(
        generated_at=_iso_now(),
        findings=findings,
        total_findings=len(findings),
        critical_count=critical,
        error_count=error,
        warning_count=warning,
        info_count=info,
        checked_paths=[str(p) for p in paths],
    )
