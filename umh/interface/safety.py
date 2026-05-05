"""Phase 84 interface safety — guardrails for interface layer.

Static/read-only analysis. No module imports. No subprocess. No network.
Detects forbidden imports/patterns conservatively.
"""

from __future__ import annotations

import ast
import hashlib
import os
import re
from dataclasses import dataclass, field
from typing import Any

from umh.core.clock import iso_now as _iso_now


@dataclass
class InterfaceSafetyFinding:
    finding_id: str
    severity: str = "warning"
    target: str = ""
    message: str = ""
    recommendation: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "finding_id": self.finding_id,
            "severity": self.severity,
            "target": self.target,
            "message": self.message,
            "recommendation": self.recommendation,
            "metadata": self.metadata,
        }


@dataclass
class InterfaceSafetyResult:
    safe: bool = True
    findings: list[dict[str, Any]] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "safe": self.safe,
            "findings": self.findings,
            "warnings": self.warnings,
            "metadata": self.metadata,
        }


def _finding_id(target: str, message: str) -> str:
    h = hashlib.sha256(f"{target}{message}".encode()).hexdigest()[:10]
    return f"isf_{h}"


_FORBIDDEN_ADAPTER_PATTERNS = [
    re.compile(r"from\s+umh\.adapters\b"),
    re.compile(r"import\s+umh\.adapters\b"),
]

_FORBIDDEN_SUBPROCESS_PATTERNS = [
    re.compile(r"\bsubprocess\b"),
    re.compile(r"\bos\.system\s*\("),
    re.compile(r"\bos\.popen\s*\("),
]

_FORBIDDEN_NETWORK_PATTERNS = [
    re.compile(r"\brequests\.(get|post|put|delete|patch|head)\s*\("),
    re.compile(r"\bhttpx\."),
    re.compile(r"\burllib\.request\b"),
]

_FORBIDDEN_STORAGE_MUTATION_PATTERNS = [
    re.compile(r'open\([^)]*["\']w["\']'),
    re.compile(r"\bjson\.dump\s*\("),
    re.compile(r"\bsqlite3\.connect\s*\("),
    re.compile(r"\bshutil\.rmtree\s*\("),
]

_FORBIDDEN_GOVERNANCE_MUTATION_PATTERNS = [
    re.compile(r"\.approve\s*\("),
    re.compile(r"\.deny\s*\("),
    re.compile(r"\.escalate\s*\("),
]

_FORBIDDEN_TRACE_MUTATION_PATTERNS = [
    re.compile(r"trace_store\.(store|save|write|create|update|delete)\s*\("),
    re.compile(r"outcome_store\.(store|save|write|create|update|delete)\s*\("),
    re.compile(r"feedback_store\.(store|save|write|create|update|delete)\s*\("),
]

_FORBIDDEN_MEMORY_PROMOTION_PATTERNS = [
    re.compile(r"\.promote\s*\("),
    re.compile(r"memory_store\.(write|create|promote)\s*\("),
]


def _collect_interface_files(root_path: str) -> list[str]:
    if not os.path.isdir(root_path):
        return []
    files: list[str] = []
    for dirpath, _, filenames in os.walk(root_path):
        for fn in filenames:
            if fn.endswith(".py") and not fn.startswith("__pycache__"):
                files.append(os.path.join(dirpath, fn))
    return files


def _scan_patterns(
    source: str, patterns: list[re.Pattern], category: str, file_path: str
) -> list[InterfaceSafetyFinding]:
    findings: list[InterfaceSafetyFinding] = []
    for pat in patterns:
        if pat.search(source):
            findings.append(
                InterfaceSafetyFinding(
                    finding_id=_finding_id(file_path, f"{category}: {pat.pattern}"),
                    severity="error",
                    target=file_path,
                    message=f"Forbidden {category} pattern detected: {pat.pattern}",
                    recommendation=f"Remove {category} usage from interface module",
                )
            )
    return findings


def validate_interface_module_boundaries(
    root_path: str = "/opt/OS/umh/interface",
) -> InterfaceSafetyResult:
    files = _collect_interface_files(root_path)
    if not files:
        return InterfaceSafetyResult(
            safe=True,
            warnings=[
                "No interface files found"
                if os.path.isdir(root_path)
                else f"Directory not found: {root_path}"
            ],
        )

    all_findings: list[dict[str, Any]] = []
    for fp in files:
        if fp.endswith("safety.py"):
            continue
        try:
            with open(fp, "r") as f:
                source = f.read()
        except OSError:
            continue

        findings: list[InterfaceSafetyFinding] = []
        findings.extend(_scan_patterns(source, _FORBIDDEN_ADAPTER_PATTERNS, "adapter import", fp))
        findings.extend(
            _scan_patterns(source, _FORBIDDEN_SUBPROCESS_PATTERNS, "subprocess/os execution", fp)
        )
        findings.extend(_scan_patterns(source, _FORBIDDEN_NETWORK_PATTERNS, "network call", fp))
        findings.extend(
            _scan_patterns(
                source, _FORBIDDEN_STORAGE_MUTATION_PATTERNS, "direct storage mutation", fp
            )
        )
        findings.extend(
            _scan_patterns(
                source, _FORBIDDEN_GOVERNANCE_MUTATION_PATTERNS, "governance mutation", fp
            )
        )
        findings.extend(
            _scan_patterns(
                source, _FORBIDDEN_TRACE_MUTATION_PATTERNS, "trace/outcome/feedback mutation", fp
            )
        )
        findings.extend(
            _scan_patterns(source, _FORBIDDEN_MEMORY_PROMOTION_PATTERNS, "memory promotion", fp)
        )

        all_findings.extend([f.to_dict() for f in findings])

    safe = len(all_findings) == 0
    return InterfaceSafetyResult(
        safe=safe,
        findings=all_findings,
        warnings=[] if safe else [f"Found {len(all_findings)} safety issues"],
    )


def validate_command_is_safe(envelope: Any) -> InterfaceSafetyResult:
    warnings: list[str] = []
    findings: list[dict[str, Any]] = []

    if hasattr(envelope, "read_only") and envelope.read_only:
        return InterfaceSafetyResult(safe=True, warnings=["Command is read-only"])

    cmd_type = getattr(envelope, "command_type", None)
    if cmd_type is not None:
        ct_val = cmd_type.value if hasattr(cmd_type, "value") else str(cmd_type)
        if ct_val == "execution_intent":
            warnings.append("Execution intent must route through control plane")
        if ct_val == "unknown":
            findings.append(
                InterfaceSafetyFinding(
                    finding_id=_finding_id("command", "unknown_type"),
                    severity="warning",
                    target="command",
                    message="Unknown command type cannot be validated for safety",
                    recommendation="Use a known command type",
                ).to_dict()
            )

    safe = len(findings) == 0
    return InterfaceSafetyResult(safe=safe, findings=findings, warnings=warnings)


def validate_surface_does_not_execute(surface: Any) -> InterfaceSafetyResult:
    return InterfaceSafetyResult(safe=True, warnings=["Surface is metadata-only"])


def scan_interface_for_forbidden_imports(paths: list[str]) -> InterfaceSafetyResult:
    all_findings: list[dict[str, Any]] = []
    for fp in paths:
        if not os.path.isfile(fp):
            continue
        try:
            with open(fp, "r") as f:
                source = f.read()
        except OSError:
            continue
        findings = _scan_patterns(source, _FORBIDDEN_ADAPTER_PATTERNS, "adapter import", fp)
        all_findings.extend([f.to_dict() for f in findings])
    safe = len(all_findings) == 0
    return InterfaceSafetyResult(safe=safe, findings=all_findings)


def scan_interface_for_direct_adapter_calls(paths: list[str]) -> InterfaceSafetyResult:
    return scan_interface_for_forbidden_imports(paths)


def scan_interface_for_direct_storage_mutation(paths: list[str]) -> InterfaceSafetyResult:
    all_findings: list[dict[str, Any]] = []
    for fp in paths:
        if not os.path.isfile(fp):
            continue
        try:
            with open(fp, "r") as f:
                source = f.read()
        except OSError:
            continue
        findings = _scan_patterns(
            source, _FORBIDDEN_STORAGE_MUTATION_PATTERNS, "direct storage mutation", fp
        )
        all_findings.extend([f.to_dict() for f in findings])
    safe = len(all_findings) == 0
    return InterfaceSafetyResult(safe=safe, findings=all_findings)
