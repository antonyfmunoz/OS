"""Review workflow — governed code/work review with outcome tracking.

Steps: identify_scope → analyze → generate_findings → report

Deterministic-first: scope identification uses file system checks.
Analysis runs pre-commit gates and import verification.
AI enhances finding generation when available.
"""

from __future__ import annotations

import logging
import os
import subprocess
from dataclasses import dataclass, field
from typing import Any

from projections.eos.workflows.types import WorkflowStep
from substrate.execution.cpu_gate import gated_subprocess_run

logger = logging.getLogger(__name__)

_REPO_ROOT = os.environ.get("UMH_ROOT", "/opt/OS")


@dataclass
class ReviewFinding:
    severity: str
    category: str
    description: str
    file_path: str = ""
    line: int = 0


@dataclass
class ReviewScope:
    scope_type: str
    target: str
    files: list[str] = field(default_factory=list)
    file_count: int = 0


class ReviewWorkflow:
    """Multi-step review workflow through governed mutation."""

    REVIEW_TYPES = {
        "architecture": "Check dependency direction and layer violations",
        "types": "Check type coherence against canonical_types.py",
        "imports": "Check for stale or circular imports",
        "tests": "Run test suite and report failures",
        "gates": "Run all pre-commit gates",
    }

    def __init__(self, org_id: str = "", venture_id: str = "") -> None:
        self._org_id = org_id
        self._venture_id = venture_id
        self._scope: ReviewScope | None = None
        self._findings: list[ReviewFinding] = []

    def steps(self, target: str) -> list[WorkflowStep]:
        return [
            WorkflowStep(
                name="identify_scope",
                mutation_name="command_submit",
                intent=f"Identify review scope: {target[:80]}",
                execute_fn=lambda: self._identify_scope(target),
            ),
            WorkflowStep(
                name="analyze",
                mutation_name="command_submit",
                intent=f"Analyze: {target[:80]}",
                execute_fn=self._analyze,
            ),
            WorkflowStep(
                name="generate_findings",
                mutation_name="command_submit",
                intent=f"Generate findings for: {target[:80]}",
                execute_fn=self._generate_findings,
            ),
        ]

    def _identify_scope(self, target: str) -> tuple[str, bool]:
        target_lower = target.lower().strip()

        if target_lower in self.REVIEW_TYPES:
            self._scope = ReviewScope(
                scope_type=target_lower,
                target=target,
            )
            return (f"Scope: {target_lower} review", True)

        target_path = os.path.join(_REPO_ROOT, target)
        if os.path.isdir(target_path):
            py_files = []
            for root, dirs, files in os.walk(target_path):
                dirs[:] = [d for d in dirs if d not in ("__pycache__", ".git", "node_modules")]
                for f in files:
                    if f.endswith(".py"):
                        py_files.append(os.path.join(root, f))
            self._scope = ReviewScope(
                scope_type="directory",
                target=target,
                files=py_files[:200],
                file_count=len(py_files),
            )
            return (f"Scope: directory '{target}' ({len(py_files)} Python files)", True)

        if os.path.isfile(target_path):
            self._scope = ReviewScope(
                scope_type="file",
                target=target,
                files=[target_path],
                file_count=1,
            )
            return (f"Scope: single file '{target}'", True)

        self._scope = ReviewScope(
            scope_type="gates",
            target="all pre-commit gates",
        )
        return (f"Target '{target}' not found — defaulting to gates review", True)

    def _analyze(self) -> tuple[str, bool]:
        if not self._scope:
            return ("no scope defined", False)

        self._findings = []

        if self._scope.scope_type == "gates":
            self._run_gates()
        elif self._scope.scope_type == "architecture":
            self._check_architecture()
        elif self._scope.scope_type == "types":
            self._check_types()
        elif self._scope.scope_type == "imports":
            self._check_imports()
        elif self._scope.scope_type == "tests":
            self._run_tests()
        elif self._scope.scope_type in ("directory", "file"):
            self._check_file_quality()

        return (f"Analysis complete: {len(self._findings)} findings", True)

    def _generate_findings(self) -> tuple[str, bool]:
        if not self._scope:
            return ("no scope", False)

        if not self._findings:
            return ("Review clean — no findings", True)

        by_severity: dict[str, int] = {}
        for f in self._findings:
            by_severity[f.severity] = by_severity.get(f.severity, 0) + 1

        summary_parts = []
        for sev in ("critical", "high", "medium", "low"):
            count = by_severity.get(sev, 0)
            if count:
                summary_parts.append(f"{count} {sev}")

        details = []
        for f in self._findings[:20]:
            loc = f"({f.file_path}:{f.line})" if f.file_path else ""
            details.append(f"[{f.severity}] {f.category}: {f.description} {loc}")

        return (
            f"Findings: {', '.join(summary_parts)}\n" + "\n".join(details),
            True,
        )

    def _run_gates(self) -> None:
        gate_scripts = [
            "scripts/check_dependency_direction.py",
            "scripts/check_type_divergence.py",
            "scripts/check_projection_leak.py",
            "scripts/check_instance_leak.py",
            "scripts/check_cpu_gate.py",
            "scripts/check_credential_injection.py",
        ]
        for gate in gate_scripts:
            gate_path = os.path.join(_REPO_ROOT, gate)
            if not os.path.exists(gate_path):
                continue
            result = gated_subprocess_run(
                ["python3", gate_path],
                caller="review_workflow",
                capture_output=True,
                text=True,
                timeout=30,
                cwd=_REPO_ROOT,
            )
            if result is None:
                self._findings.append(ReviewFinding(
                    severity="low",
                    category="cpu_gate",
                    description=f"Gate {gate} skipped — CPU gate blocked",
                ))
                continue
            if result.returncode != 0:
                self._findings.append(ReviewFinding(
                    severity="high",
                    category="gate_failure",
                    description=f"{gate}: {result.stdout[:200] or result.stderr[:200]}",
                ))

    def _check_architecture(self) -> None:
        gate_path = os.path.join(_REPO_ROOT, "scripts", "check_dependency_direction.py")
        if os.path.exists(gate_path):
            result = gated_subprocess_run(
                ["python3", gate_path],
                caller="review_workflow",
                capture_output=True,
                text=True,
                timeout=30,
                cwd=_REPO_ROOT,
            )
            if result and result.returncode != 0:
                for line in (result.stdout or "").split("\n"):
                    if line.strip():
                        self._findings.append(ReviewFinding(
                            severity="high",
                            category="architecture",
                            description=line.strip()[:200],
                        ))

    def _check_types(self) -> None:
        gate_path = os.path.join(_REPO_ROOT, "scripts", "check_type_divergence.py")
        if os.path.exists(gate_path):
            result = gated_subprocess_run(
                ["python3", gate_path],
                caller="review_workflow",
                capture_output=True,
                text=True,
                timeout=30,
                cwd=_REPO_ROOT,
            )
            if result and result.returncode != 0:
                self._findings.append(ReviewFinding(
                    severity="medium",
                    category="type_coherence",
                    description=(result.stdout or result.stderr or "failed")[:300],
                ))

    def _check_imports(self) -> None:
        if not self._scope or not self._scope.files:
            return
        for filepath in self._scope.files[:50]:
            try:
                with open(filepath) as f:
                    for i, line in enumerate(f, 1):
                        stripped = line.strip()
                        if stripped.startswith("from ") and "_dormant" in stripped:
                            rel = os.path.relpath(filepath, _REPO_ROOT)
                            self._findings.append(ReviewFinding(
                                severity="medium",
                                category="stale_import",
                                description=f"Imports from _dormant module: {stripped[:100]}",
                                file_path=rel,
                                line=i,
                            ))
            except OSError:
                continue

    def _run_tests(self) -> None:
        result = gated_subprocess_run(
            ["python3", "-m", "pytest", "tests/", "-x", "--tb=line", "-q"],
            caller="review_workflow",
            capture_output=True,
            text=True,
            timeout=120,
            cwd=_REPO_ROOT,
        )
        if result is None:
            self._findings.append(ReviewFinding(
                severity="low",
                category="cpu_gate",
                description="Test run skipped — CPU gate blocked",
            ))
            return
        if result.returncode != 0:
            for line in (result.stdout or "").split("\n"):
                if "FAILED" in line:
                    self._findings.append(ReviewFinding(
                        severity="high",
                        category="test_failure",
                        description=line.strip()[:200],
                    ))

    def _check_file_quality(self) -> None:
        if not self._scope or not self._scope.files:
            return
        for filepath in self._scope.files[:50]:
            try:
                with open(filepath) as f:
                    lines = f.readlines()
                if len(lines) > 3000:
                    rel = os.path.relpath(filepath, _REPO_ROOT)
                    self._findings.append(ReviewFinding(
                        severity="medium",
                        category="god_file",
                        description=f"File exceeds 3000 lines ({len(lines)} lines)",
                        file_path=rel,
                    ))
                has_silent_except = any(
                    "except:" in line and "pass" in lines[i + 1] if i + 1 < len(lines) else False
                    for i, line in enumerate(lines)
                )
                if has_silent_except:
                    rel = os.path.relpath(filepath, _REPO_ROOT)
                    self._findings.append(ReviewFinding(
                        severity="medium",
                        category="silent_except",
                        description="Silent except-pass found",
                        file_path=rel,
                    ))
            except OSError:
                continue
