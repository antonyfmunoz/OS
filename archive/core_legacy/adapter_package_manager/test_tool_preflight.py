"""Test Tool Preflight for UMH task execution.

Before a test or ingestion run, UMH must inventory the tools, access
paths, and runtimes required and verify execution readiness for each.

UMH substrate subsystem. EOS is one platform consumer.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from .maturity_enforcement import (
    AdapterExecutionMaturityStatus,
    AdapterExecutionReadinessDecision,
    AdapterPackageSnapshot,
    evaluate_adapter_package_execution_readiness,
)


class TestToolPreflightStatus(str, Enum):
    READY = "ready"
    BLOCKED = "blocked"
    PARTIAL = "partial"
    WAIVED = "waived"
    NEEDS_MATURITY_BUILDOUT = "needs_maturity_buildout"


@dataclass
class TestToolRequirement:
    tool_name: str
    capability: str = ""
    runtime_or_environment: str = ""
    reason_needed: str = ""
    required_adapter_package: str = ""
    required_access_path: str = ""
    required_mastery_pack: str = ""
    required_status: str = "execution_ready"

    def to_dict(self) -> dict[str, Any]:
        return {
            "tool_name": self.tool_name,
            "capability": self.capability,
            "runtime_or_environment": self.runtime_or_environment,
            "reason_needed": self.reason_needed,
            "required_adapter_package": self.required_adapter_package,
            "required_access_path": self.required_access_path,
            "required_mastery_pack": self.required_mastery_pack,
            "required_status": self.required_status,
        }


@dataclass
class TestToolPreflightReport:
    test_name: str = ""
    task_summary: str = ""
    required_tools: list[TestToolRequirement] = field(default_factory=list)
    readiness_decisions: list[AdapterExecutionReadinessDecision] = field(
        default_factory=list
    )
    blocked_tools: list[str] = field(default_factory=list)
    usable_tools: list[str] = field(default_factory=list)
    waived_tools: list[str] = field(default_factory=list)
    missing_packages: list[str] = field(default_factory=list)
    immature_paths: list[str] = field(default_factory=list)
    final_status: TestToolPreflightStatus = TestToolPreflightStatus.BLOCKED
    next_action: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "test_name": self.test_name,
            "task_summary": self.task_summary,
            "required_tools": [t.to_dict() for t in self.required_tools],
            "readiness_decisions": [d.to_dict() for d in self.readiness_decisions],
            "blocked_tools": self.blocked_tools,
            "usable_tools": self.usable_tools,
            "waived_tools": self.waived_tools,
            "missing_packages": self.missing_packages,
            "immature_paths": self.immature_paths,
            "final_status": self.final_status.value,
            "next_action": self.next_action,
        }


_W0_001_TOOLS: list[dict[str, str]] = [
    {
        "tool_name": "claude_code",
        "capability": "code_doc_test_orchestration",
        "reason_needed": "orchestrates code, documentation, and test execution",
        "runtime_or_environment": "vps",
    },
    {
        "tool_name": "shell_bash",
        "capability": "local_command_execution",
        "reason_needed": "local command execution on VPS",
        "runtime_or_environment": "vps",
    },
    {
        "tool_name": "python",
        "capability": "validation_test_execution",
        "reason_needed": "validation and test execution",
        "runtime_or_environment": "vps",
    },
    {
        "tool_name": "pytest",
        "capability": "test_execution",
        "reason_needed": "test framework execution",
        "runtime_or_environment": "vps",
    },
    {
        "tool_name": "git",
        "capability": "version_control",
        "reason_needed": "only if commit requested",
        "runtime_or_environment": "vps",
    },
    {
        "tool_name": "tmux",
        "capability": "session_management",
        "reason_needed": "only if active runtime",
        "runtime_or_environment": "vps",
    },
    {
        "tool_name": "google_workspace",
        "capability": "source_system_package",
        "reason_needed": "source system for document ingestion",
        "runtime_or_environment": "remote_api",
    },
    {
        "tool_name": "google_docs",
        "capability": "tab_aware_extraction",
        "reason_needed": "tab-aware document extraction",
        "runtime_or_environment": "remote_api",
    },
    {
        "tool_name": "google_drive",
        "capability": "inventory_metadata",
        "reason_needed": "inventory and metadata discovery",
        "runtime_or_environment": "remote_api",
    },
]


def detect_required_tools_for_task(task_summary: str) -> list[TestToolRequirement]:
    lower = task_summary.lower()
    reqs: list[TestToolRequirement] = []
    keywords = {
        "claude_code": ["claude code", "claude-code", "cc"],
        "shell_bash": ["shell", "bash", "command"],
        "python": ["python", "script"],
        "pytest": ["pytest", "test"],
        "git": ["git", "commit", "push"],
        "tmux": ["tmux"],
        "google_workspace": ["google workspace", "gws"],
        "google_docs": ["google docs", "gdocs", "document extraction"],
        "google_drive": ["google drive", "gdrive", "inventory"],
    }
    for tool_name, kws in keywords.items():
        for kw in kws:
            if kw in lower:
                reqs.append(TestToolRequirement(tool_name=tool_name, capability=kw))
                break
    return reqs


def build_w0_001_required_tool_inventory() -> list[TestToolRequirement]:
    return [
        TestToolRequirement(**entry) for entry in _W0_001_TOOLS
    ]


def run_test_tool_preflight(
    task_summary: str,
    package_lookup: dict[str, AdapterPackageSnapshot],
) -> TestToolPreflightReport:
    """Run preflight check for a task. package_lookup maps tool_name to snapshot."""
    tools = build_w0_001_required_tool_inventory()
    report = TestToolPreflightReport(
        test_name="W0-001",
        task_summary=task_summary,
        required_tools=tools,
    )

    for req in tools:
        snap = package_lookup.get(req.tool_name)
        if snap is None:
            decision = AdapterExecutionReadinessDecision(
                tool_name=req.tool_name,
                capability=req.capability,
                maturity_status=AdapterExecutionMaturityStatus.MISSING_ADAPTER_PACKAGE,
                block_reasons=["no adapter package exists"],
                required_fixes=["create adapter package"],
            )
            report.missing_packages.append(req.tool_name)
        else:
            decision = evaluate_adapter_package_execution_readiness(
                snap, req.capability, req.required_access_path or None
            )

        report.readiness_decisions.append(decision)

        if decision.can_execute:
            if decision.waiver_status:
                report.waived_tools.append(req.tool_name)
            else:
                report.usable_tools.append(req.tool_name)
        else:
            report.blocked_tools.append(req.tool_name)
            if decision.maturity_status == AdapterExecutionMaturityStatus.ACCESS_PATH_PARTIAL:
                report.immature_paths.append(req.tool_name)

    if not report.blocked_tools:
        report.final_status = TestToolPreflightStatus.READY
    elif report.usable_tools and report.blocked_tools:
        report.final_status = TestToolPreflightStatus.PARTIAL
        report.next_action = f"mature packages for: {', '.join(report.blocked_tools)}"
    elif report.waived_tools and not report.blocked_tools:
        report.final_status = TestToolPreflightStatus.WAIVED
    else:
        report.final_status = TestToolPreflightStatus.BLOCKED
        report.next_action = f"create/mature packages for: {', '.join(report.blocked_tools)}"

    return report


def preflight_blocks_execution(report: TestToolPreflightReport) -> bool:
    return report.final_status in (
        TestToolPreflightStatus.BLOCKED,
        TestToolPreflightStatus.NEEDS_MATURITY_BUILDOUT,
    )


def summarize_test_tool_preflight(report: TestToolPreflightReport) -> str:
    parts: list[str] = []
    parts.append(f"Test: {report.test_name}")
    parts.append(f"Status: {report.final_status.value}")
    if report.usable_tools:
        parts.append(f"Usable: {', '.join(report.usable_tools)}")
    if report.blocked_tools:
        parts.append(f"Blocked: {', '.join(report.blocked_tools)}")
    if report.missing_packages:
        parts.append(f"Missing packages: {', '.join(report.missing_packages)}")
    if report.waived_tools:
        parts.append(f"Waived: {', '.join(report.waived_tools)}")
    if report.next_action:
        parts.append(f"Next: {report.next_action}")
    return "; ".join(parts)
