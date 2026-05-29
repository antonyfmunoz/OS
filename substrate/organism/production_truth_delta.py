"""Production Truth Delta — what actually changed in production after merge.

Compares expected changes (from ChangeSetManifest) against observed
changes (from git diff on main), and captures before/after snapshots
of production state across world model, contradictions, readiness,
dependency graph, template confidence, and agent reliability.

Doctrine:
  - Expected changes must be compared against observed changes.
  - If expected and observed diverge, mark requires_review.
  - Do not emit ProductionOutcomeCommitted if validation fails.
  - Partial validation marks production_partial.

UMH substrate subsystem. Instance-agnostic.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


class DeltaStatus(str, Enum):
    PENDING = "pending"
    COMPUTED = "computed"
    DIVERGED = "diverged"
    REQUIRES_REVIEW = "requires_review"
    PRODUCTION_PARTIAL = "production_partial"
    PRODUCTION_VERIFIED = "production_verified"


@dataclass
class StateSnapshot:
    world_model_hash: str = ""
    contradiction_count: int = 0
    readiness_score: float = 0.0
    dependency_node_count: int = 0
    bottleneck_count: int = 0
    template_count: int = 0
    agent_count: int = 0
    captured_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "world_model_hash": self.world_model_hash,
            "contradiction_count": self.contradiction_count,
            "readiness_score": round(self.readiness_score, 4),
            "dependency_node_count": self.dependency_node_count,
            "bottleneck_count": self.bottleneck_count,
            "template_count": self.template_count,
            "agent_count": self.agent_count,
            "captured_at": self.captured_at,
        }


@dataclass
class FileDivergence:
    path: str = ""
    expected: bool = True
    observed: bool = True
    expected_change_type: str = ""
    observed_change_type: str = ""

    @property
    def diverged(self) -> bool:
        return self.expected != self.observed

    def to_dict(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "expected": self.expected,
            "observed": self.observed,
            "expected_change_type": self.expected_change_type,
            "observed_change_type": self.observed_change_type,
            "diverged": self.diverged,
        }


@dataclass
class PostMergeValidationResult:
    command: str = ""
    passed: bool = False
    exit_code: int = -1
    output_summary: str = ""
    validated_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "command": self.command,
            "passed": self.passed,
            "exit_code": self.exit_code,
            "output_summary": self.output_summary[:300],
            "validated_at": self.validated_at,
        }


@dataclass
class ProductionTruthDelta:
    delta_id: str = field(default_factory=lambda: f"ptd-{uuid4().hex[:8]}")
    sandbox_id: str = ""
    pr_number: int = 0
    manifest_id: str = ""
    merge_commit: str = ""
    base_commit: str = ""
    head_commit: str = ""

    changed_files_expected: list[str] = field(default_factory=list)
    changed_files_observed: list[str] = field(default_factory=list)
    file_divergences: list[FileDivergence] = field(default_factory=list)

    added_lines_expected: int = 0
    removed_lines_expected: int = 0
    added_lines_observed: int = 0
    removed_lines_observed: int = 0

    state_before: StateSnapshot = field(default_factory=StateSnapshot)
    state_after: StateSnapshot = field(default_factory=StateSnapshot)

    world_model_before_after: dict[str, Any] = field(default_factory=dict)
    contradictions_before_after: dict[str, Any] = field(default_factory=dict)
    readiness_before_after: dict[str, Any] = field(default_factory=dict)
    dependency_graph_before_after: dict[str, Any] = field(default_factory=dict)
    bottlenecks_before_after: dict[str, Any] = field(default_factory=dict)
    template_confidence_before_after: dict[str, Any] = field(default_factory=dict)
    agent_reliability_before_after: dict[str, Any] = field(default_factory=dict)

    validation_results: list[PostMergeValidationResult] = field(default_factory=list)
    evidence: list[str] = field(default_factory=list)
    mismatch_reasons: list[str] = field(default_factory=list)
    requires_operator_review: bool = False
    status: DeltaStatus = DeltaStatus.PENDING
    timestamp: float = field(default_factory=time.time)

    @property
    def has_file_divergence(self) -> bool:
        return any(fd.diverged for fd in self.file_divergences)

    @property
    def all_validations_passed(self) -> bool:
        return bool(self.validation_results) and all(
            v.passed for v in self.validation_results
        )

    @property
    def requires_review(self) -> bool:
        return self.has_file_divergence or not self.all_validations_passed

    def compute_file_divergences(self) -> None:
        expected_set = set(self.changed_files_expected)
        observed_set = set(self.changed_files_observed)
        all_files = expected_set | observed_set
        self.file_divergences = []

        for path in sorted(all_files):
            fd = FileDivergence(
                path=path,
                expected=path in expected_set,
                observed=path in observed_set,
                expected_change_type="modified" if path in expected_set else "",
                observed_change_type="modified" if path in observed_set else "",
            )
            self.file_divergences.append(fd)

        if self.has_file_divergence:
            self.status = DeltaStatus.DIVERGED
            diverged_count = sum(1 for fd in self.file_divergences if fd.diverged)
            self.evidence.append(f"file divergence: {diverged_count} files")
            for fd in self.file_divergences:
                if fd.diverged:
                    if fd.expected and not fd.observed:
                        self.mismatch_reasons.append(f"{fd.path}: expected but not observed")
                    elif fd.observed and not fd.expected:
                        self.mismatch_reasons.append(f"{fd.path}: observed but not expected")
        else:
            self.evidence.append("file sets match")

    def compute_line_counts(self, repo_root: str = "") -> None:
        import subprocess

        if not repo_root or not self.base_commit or not self.merge_commit:
            return
        try:
            result = subprocess.run(
                ["git", "diff", "--stat", f"{self.base_commit}..{self.merge_commit}"],
                cwd=repo_root,
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode == 0:
                for line in result.stdout.strip().split("\n"):
                    if "insertion" in line or "deletion" in line:
                        parts = line.split(",")
                        for part in parts:
                            part = part.strip()
                            if "insertion" in part:
                                try:
                                    self.added_lines_observed = int(
                                        part.split()[0]
                                    )
                                except (ValueError, IndexError):
                                    pass
                            elif "deletion" in part:
                                try:
                                    self.removed_lines_observed = int(
                                        part.split()[0]
                                    )
                                except (ValueError, IndexError):
                                    pass
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            pass

    def compute_state_delta(
        self,
        before: StateSnapshot,
        after: StateSnapshot,
    ) -> None:
        self.state_before = before
        self.state_after = after

        self.world_model_before_after = {
            "before_hash": before.world_model_hash,
            "after_hash": after.world_model_hash,
            "changed": before.world_model_hash != after.world_model_hash,
        }
        self.contradictions_before_after = {
            "before": before.contradiction_count,
            "after": after.contradiction_count,
            "delta": after.contradiction_count - before.contradiction_count,
        }
        self.readiness_before_after = {
            "before": round(before.readiness_score, 4),
            "after": round(after.readiness_score, 4),
            "delta": round(after.readiness_score - before.readiness_score, 4),
        }
        self.dependency_graph_before_after = {
            "before_nodes": before.dependency_node_count,
            "after_nodes": after.dependency_node_count,
            "delta": after.dependency_node_count - before.dependency_node_count,
        }
        self.bottlenecks_before_after = {
            "before": before.bottleneck_count,
            "after": after.bottleneck_count,
            "delta": after.bottleneck_count - before.bottleneck_count,
        }
        self.template_confidence_before_after = {
            "before_count": before.template_count,
            "after_count": after.template_count,
        }
        self.agent_reliability_before_after = {
            "before_count": before.agent_count,
            "after_count": after.agent_count,
        }

    def finalize(self) -> None:
        if self.has_file_divergence:
            self.requires_operator_review = True
            if self.all_validations_passed:
                self.status = DeltaStatus.REQUIRES_REVIEW
            else:
                self.status = DeltaStatus.DIVERGED
        elif not self.all_validations_passed:
            self.status = DeltaStatus.PRODUCTION_PARTIAL
            self.requires_operator_review = True
            for v in self.validation_results:
                if not v.passed:
                    self.mismatch_reasons.append(f"validation failed: {v.command}")
        else:
            self.status = DeltaStatus.PRODUCTION_VERIFIED

    def to_dict(self) -> dict[str, Any]:
        return {
            "delta_id": self.delta_id,
            "sandbox_id": self.sandbox_id,
            "pr_number": self.pr_number,
            "manifest_id": self.manifest_id,
            "merge_commit": self.merge_commit,
            "base_commit": self.base_commit,
            "head_commit": self.head_commit,
            "changed_files_expected": self.changed_files_expected,
            "changed_files_observed": self.changed_files_observed,
            "file_divergences": [fd.to_dict() for fd in self.file_divergences],
            "has_file_divergence": self.has_file_divergence,
            "added_lines_expected": self.added_lines_expected,
            "removed_lines_expected": self.removed_lines_expected,
            "added_lines_observed": self.added_lines_observed,
            "removed_lines_observed": self.removed_lines_observed,
            "state_before": self.state_before.to_dict(),
            "state_after": self.state_after.to_dict(),
            "world_model_before_after": self.world_model_before_after,
            "contradictions_before_after": self.contradictions_before_after,
            "readiness_before_after": self.readiness_before_after,
            "dependency_graph_before_after": self.dependency_graph_before_after,
            "bottlenecks_before_after": self.bottlenecks_before_after,
            "template_confidence_before_after": self.template_confidence_before_after,
            "agent_reliability_before_after": self.agent_reliability_before_after,
            "validation_results": [v.to_dict() for v in self.validation_results],
            "all_validations_passed": self.all_validations_passed,
            "requires_review": self.requires_review,
            "requires_operator_review": self.requires_operator_review,
            "mismatch_reasons": self.mismatch_reasons,
            "evidence": self.evidence,
            "status": self.status.value,
            "timestamp": self.timestamp,
        }
