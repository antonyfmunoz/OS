"""Changeset Manifest — evidence record for every autonomous branch/PR.

Every autonomous improvement produces a manifest documenting what
changed, why, validation proof, risk assessment, rollback plan,
and expected impact on organism state. The manifest serves as the
PR description source and the post-merge propagation input.

UMH substrate subsystem. Instance-agnostic.
"""

from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)

_REPO_ROOT = os.environ.get("UMH_ROOT", "/opt/OS")


@dataclass
class ChangedFile:
    path: str = ""
    change_type: str = "modified"
    added_lines: int = 0
    removed_lines: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "change_type": self.change_type,
            "added_lines": self.added_lines,
            "removed_lines": self.removed_lines,
        }


@dataclass
class ValidationProof:
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
class RiskProof:
    risk_class: str = "low"
    governance_mode: str = "autonomous"
    sensitive_content_check: bool = True
    file_count_within_limit: bool = True
    no_auth_changes: bool = True
    no_credential_changes: bool = True
    no_dns_changes: bool = True
    no_destructive_ops: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "risk_class": self.risk_class,
            "governance_mode": self.governance_mode,
            "sensitive_content_check": self.sensitive_content_check,
            "file_count_within_limit": self.file_count_within_limit,
            "no_auth_changes": self.no_auth_changes,
            "no_credential_changes": self.no_credential_changes,
            "no_dns_changes": self.no_dns_changes,
            "no_destructive_ops": self.no_destructive_ops,
        }

    @property
    def all_passed(self) -> bool:
        return all([
            self.sensitive_content_check,
            self.file_count_within_limit,
            self.no_auth_changes,
            self.no_credential_changes,
            self.no_dns_changes,
            self.no_destructive_ops,
            self.risk_class == "low",
        ])


@dataclass
class RollbackProof:
    has_rollback: bool = False
    rollback_method: str = ""
    is_non_mutating: bool = False
    rollback_tested: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "has_rollback": self.has_rollback,
            "rollback_method": self.rollback_method,
            "is_non_mutating": self.is_non_mutating,
            "rollback_tested": self.rollback_tested,
        }


@dataclass
class PropagationProof:
    sandbox_outcome_emitted: bool = False
    sandbox_outcome_id: str = ""
    production_outcome_emitted: bool = False
    production_outcome_id: str = ""
    production_state_updated: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "sandbox_outcome_emitted": self.sandbox_outcome_emitted,
            "sandbox_outcome_id": self.sandbox_outcome_id,
            "production_outcome_emitted": self.production_outcome_emitted,
            "production_outcome_id": self.production_outcome_id,
            "production_state_updated": self.production_state_updated,
        }


@dataclass
class ChangeSetManifest:
    manifest_id: str = field(default_factory=lambda: f"csm-{uuid4().hex[:8]}")
    candidate_id: str = ""
    template_id: str = ""
    sandbox_id: str = ""
    branch_name: str = ""
    base_commit: str = ""
    head_commit: str = ""
    changed_files: list[ChangedFile] = field(default_factory=list)
    added_lines: int = 0
    removed_lines: int = 0
    risk_class: str = "low"
    validation_commands: list[str] = field(default_factory=list)
    validation_results: list[ValidationProof] = field(default_factory=list)
    risk_proof: RiskProof = field(default_factory=RiskProof)
    rollback_proof: RollbackProof = field(default_factory=RollbackProof)
    propagation_proof: PropagationProof = field(default_factory=PropagationProof)
    rollback_plan: str = ""
    affected_entities: list[str] = field(default_factory=list)
    affected_dependencies: list[str] = field(default_factory=list)
    expected_contradiction_delta: int = 0
    expected_readiness_delta: float = 0.0
    outcome_ids: list[str] = field(default_factory=list)
    propagation_event_ids: list[str] = field(default_factory=list)
    template_confidence_before: float = 0.0
    template_confidence_after: float = 0.0
    agent_reliability_before: float = 0.0
    agent_reliability_after: float = 0.0
    description: str = ""
    created_at: float = field(default_factory=time.time)

    @property
    def total_changed_files(self) -> int:
        return len(self.changed_files)

    @property
    def all_validations_passed(self) -> bool:
        return bool(self.validation_results) and all(
            v.passed for v in self.validation_results
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "manifest_id": self.manifest_id,
            "candidate_id": self.candidate_id,
            "template_id": self.template_id,
            "sandbox_id": self.sandbox_id,
            "branch_name": self.branch_name,
            "base_commit": self.base_commit,
            "head_commit": self.head_commit,
            "changed_files": [f.to_dict() for f in self.changed_files],
            "total_changed_files": self.total_changed_files,
            "added_lines": self.added_lines,
            "removed_lines": self.removed_lines,
            "risk_class": self.risk_class,
            "validation_commands": self.validation_commands,
            "validation_results": [v.to_dict() for v in self.validation_results],
            "risk_proof": self.risk_proof.to_dict(),
            "rollback_proof": self.rollback_proof.to_dict(),
            "propagation_proof": self.propagation_proof.to_dict(),
            "rollback_plan": self.rollback_plan,
            "affected_entities": self.affected_entities,
            "affected_dependencies": self.affected_dependencies,
            "expected_contradiction_delta": self.expected_contradiction_delta,
            "expected_readiness_delta": self.expected_readiness_delta,
            "outcome_ids": self.outcome_ids,
            "propagation_event_ids": self.propagation_event_ids,
            "template_confidence_before": round(self.template_confidence_before, 3),
            "template_confidence_after": round(self.template_confidence_after, 3),
            "agent_reliability_before": round(self.agent_reliability_before, 3),
            "agent_reliability_after": round(self.agent_reliability_after, 3),
            "description": self.description,
            "created_at": self.created_at,
        }

    def to_pr_description(self) -> str:
        lines = [
            "## Autonomous Improvement — Changeset Manifest",
            "",
            f"**Candidate:** {self.candidate_id}",
            f"**Template:** {self.template_id}",
            f"**Risk:** {self.risk_class}",
            f"**Branch:** {self.branch_name}",
            f"**Base:** {self.base_commit[:12]}",
            "",
            "### Description",
            self.description or "(no description)",
            "",
            "### Changed Files",
        ]
        for cf in self.changed_files:
            lines.append(f"- `{cf.path}` ({cf.change_type}: +{cf.added_lines}/-{cf.removed_lines})")
        lines.append("")
        lines.append("### Validation")
        for vr in self.validation_results:
            status = "PASS" if vr.passed else "FAIL"
            lines.append(f"- [{status}] `{vr.command}` (exit {vr.exit_code})")
        lines.append("")
        lines.append("### Risk Proof")
        rp = self.risk_proof
        lines.append(f"- Risk class: {rp.risk_class}")
        lines.append(f"- No auth changes: {rp.no_auth_changes}")
        lines.append(f"- No credential changes: {rp.no_credential_changes}")
        lines.append(f"- No DNS changes: {rp.no_dns_changes}")
        lines.append(f"- No destructive ops: {rp.no_destructive_ops}")
        lines.append("")
        lines.append("### Rollback")
        rb = self.rollback_proof
        lines.append(f"- Has rollback: {rb.has_rollback}")
        lines.append(f"- Non-mutating: {rb.is_non_mutating}")
        if rb.rollback_method:
            lines.append(f"- Method: {rb.rollback_method}")
        lines.append("")
        lines.append("---")
        lines.append("*Generated by UMH Autonomous PR Factory*")
        return "\n".join(lines)

    def persist(self, store_dir: str | None = None) -> str:
        base = store_dir or os.path.join(
            _REPO_ROOT, "data", "umh", "autonomous_lane", "manifests"
        )
        os.makedirs(base, exist_ok=True)
        path = os.path.join(base, f"{self.manifest_id}.json")
        with open(path, "w") as f:
            json.dump(self.to_dict(), f, indent=2, default=str)
        return path

    @classmethod
    def load(cls, path: str) -> ChangeSetManifest:
        with open(path) as f:
            data = json.load(f)
        manifest = cls(
            manifest_id=data.get("manifest_id", ""),
            candidate_id=data.get("candidate_id", ""),
            template_id=data.get("template_id", ""),
            sandbox_id=data.get("sandbox_id", ""),
            branch_name=data.get("branch_name", ""),
            base_commit=data.get("base_commit", ""),
            head_commit=data.get("head_commit", ""),
            risk_class=data.get("risk_class", "low"),
            description=data.get("description", ""),
            created_at=data.get("created_at", 0),
            added_lines=data.get("added_lines", 0),
            removed_lines=data.get("removed_lines", 0),
            validation_commands=data.get("validation_commands", []),
            rollback_plan=data.get("rollback_plan", ""),
            affected_entities=data.get("affected_entities", []),
            affected_dependencies=data.get("affected_dependencies", []),
            expected_contradiction_delta=data.get("expected_contradiction_delta", 0),
            expected_readiness_delta=data.get("expected_readiness_delta", 0.0),
            outcome_ids=data.get("outcome_ids", []),
            propagation_event_ids=data.get("propagation_event_ids", []),
            template_confidence_before=data.get("template_confidence_before", 0.0),
            template_confidence_after=data.get("template_confidence_after", 0.0),
            agent_reliability_before=data.get("agent_reliability_before", 0.0),
            agent_reliability_after=data.get("agent_reliability_after", 0.0),
        )
        for cf_data in data.get("changed_files", []):
            manifest.changed_files.append(ChangedFile(
                path=cf_data.get("path", ""),
                change_type=cf_data.get("change_type", "modified"),
                added_lines=cf_data.get("added_lines", 0),
                removed_lines=cf_data.get("removed_lines", 0),
            ))
        return manifest
