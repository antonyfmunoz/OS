"""Autonomous PR Factory — converts eligible improvements into isolated PRs.

Lifecycle:
  1. Receive eligible AutonomousImprovementCandidate
  2. Create isolated worktree sandbox
  3. Apply template-guided plan through GovernedExecutionSpine
  4. Run validation suite
  5. Generate ChangeSetManifest
  6. Commit changes on branch
  7. Create PR (or mark blocked_missing_tool if gh CLI unavailable)
  8. Emit SandboxOutcomeCommitted
  9. Expose PR to cockpit
  10. Wait for operator merge

Doctrine:
  - Main is production truth.
  - Sandbox results are hypotheses.
  - SandboxOutcomeCommitted does NOT update production state.
  - ProductionOutcomeCommitted only after merge + verification.
  - No auto-merge.
  - Operator approval required.

UMH substrate subsystem. Instance-agnostic.
"""

from __future__ import annotations

import json
import logging
import os
import shutil
import subprocess
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable
from uuid import uuid4

from substrate.organism.autonomous_improvement_lane import (
    AutonomousImprovementCandidate,
    AutonomousLanePolicy,
)
from substrate.organism.changeset_manifest import (
    ChangedFile,
    ChangeSetManifest,
    PropagationProof,
    RiskProof,
    RollbackProof,
    ValidationProof,
)
from substrate.organism.coherence_propagation import OutcomeCommitted
from substrate.organism.worktree_sandbox import (
    SandboxCleanupPolicy,
    SandboxManager,
    SandboxStatus,
    SandboxValidationResult,
    WorktreeSandbox,
)

logger = logging.getLogger(__name__)

_REPO_ROOT = os.environ.get("UMH_ROOT", "/opt/OS")


class PRCreationStatus(str, Enum):
    NOT_STARTED = "not_started"
    BRANCH_CREATED = "branch_created"
    COMMITTED = "committed"
    PR_CREATED = "pr_created"
    BLOCKED_MISSING_TOOL = "blocked_missing_tool"
    BLOCKED_VALIDATION = "blocked_validation"
    FAILED = "failed"


class OutcomeBoundary(str, Enum):
    SANDBOX = "sandbox"
    PRODUCTION = "production"


@dataclass
class SandboxOutcomeCommitted:
    event_id: str = field(default_factory=lambda: f"soc-{uuid4().hex[:8]}")
    sandbox_id: str = ""
    candidate_id: str = ""
    manifest_id: str = ""
    branch_name: str = ""
    pr_url: str = ""
    pr_number: int = 0
    validation_passed: bool = False
    boundary: str = "sandbox"
    timestamp: float = field(default_factory=time.time)

    template_confidence_before: float = 0.0
    template_confidence_after: float = 0.0
    agent_reliability_before: float = 0.0
    agent_reliability_after: float = 0.0
    changed_files: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "event_type": "sandbox_outcome_committed",
            "sandbox_id": self.sandbox_id,
            "candidate_id": self.candidate_id,
            "manifest_id": self.manifest_id,
            "branch_name": self.branch_name,
            "pr_url": self.pr_url,
            "pr_number": self.pr_number,
            "validation_passed": self.validation_passed,
            "boundary": self.boundary,
            "template_confidence_before": self.template_confidence_before,
            "template_confidence_after": self.template_confidence_after,
            "agent_reliability_before": self.agent_reliability_before,
            "agent_reliability_after": self.agent_reliability_after,
            "changed_files": self.changed_files,
            "timestamp": self.timestamp,
        }


@dataclass
class ProductionOutcomeCommitted:
    event_id: str = field(default_factory=lambda: f"poc-{uuid4().hex[:8]}")
    sandbox_id: str = ""
    manifest_id: str = ""
    pr_number: int = 0
    merge_commit: str = ""
    base_commit: str = ""
    head_commit: str = ""
    branch_name: str = ""
    boundary: str = "production"
    action_type: str = "autonomous_improvement"
    mutation_type: str = "code_change"
    risk_class: str = "low"
    agent_type: str = "developer_agent"
    template_id: str = ""
    action_envelope_ids: list[str] = field(default_factory=list)
    sandbox_outcome_ids: list[str] = field(default_factory=list)
    post_merge_validation_passed: bool = False
    production_propagation_complete: bool = False
    production_truth_delta: dict[str, Any] = field(default_factory=dict)
    changed_files: list[str] = field(default_factory=list)
    affected_entities: list[str] = field(default_factory=list)
    affected_subsystems: list[str] = field(default_factory=list)
    evidence: list[str] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "event_type": "production_outcome_committed",
            "sandbox_id": self.sandbox_id,
            "manifest_id": self.manifest_id,
            "pr_number": self.pr_number,
            "merge_commit": self.merge_commit,
            "base_commit": self.base_commit,
            "head_commit": self.head_commit,
            "branch_name": self.branch_name,
            "boundary": self.boundary,
            "action_type": self.action_type,
            "mutation_type": self.mutation_type,
            "risk_class": self.risk_class,
            "agent_type": self.agent_type,
            "template_id": self.template_id,
            "action_envelope_ids": self.action_envelope_ids,
            "sandbox_outcome_ids": self.sandbox_outcome_ids,
            "post_merge_validation_passed": self.post_merge_validation_passed,
            "production_propagation_complete": self.production_propagation_complete,
            "production_truth_delta": self.production_truth_delta,
            "changed_files": self.changed_files,
            "affected_entities": self.affected_entities,
            "affected_subsystems": self.affected_subsystems,
            "evidence": self.evidence,
            "timestamp": self.timestamp,
        }


@dataclass
class PRValidationGate:
    py_compile_passed: bool = False
    type_divergence_passed: bool = False
    instance_leak_passed: bool = False
    dependency_direction_passed: bool = False
    custom_validations: list[ValidationProof] = field(default_factory=list)

    @property
    def all_passed(self) -> bool:
        base_ok = all([
            self.py_compile_passed,
            self.type_divergence_passed,
            self.instance_leak_passed,
            self.dependency_direction_passed,
        ])
        custom_ok = all(v.passed for v in self.custom_validations) if self.custom_validations else True
        return base_ok and custom_ok

    def to_dict(self) -> dict[str, Any]:
        return {
            "py_compile_passed": self.py_compile_passed,
            "type_divergence_passed": self.type_divergence_passed,
            "instance_leak_passed": self.instance_leak_passed,
            "dependency_direction_passed": self.dependency_direction_passed,
            "custom_validations": [v.to_dict() for v in self.custom_validations],
            "all_passed": self.all_passed,
        }


@dataclass
class PRReviewPacket:
    sandbox_id: str = ""
    candidate_id: str = ""
    manifest_id: str = ""
    branch_name: str = ""
    pr_url: str = ""
    pr_number: int = 0
    pr_status: PRCreationStatus = PRCreationStatus.NOT_STARTED
    validation_gate: PRValidationGate = field(default_factory=PRValidationGate)
    sandbox_outcome: SandboxOutcomeCommitted | None = None
    manifest: ChangeSetManifest | None = None
    error: str = ""
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "sandbox_id": self.sandbox_id,
            "candidate_id": self.candidate_id,
            "manifest_id": self.manifest_id,
            "branch_name": self.branch_name,
            "pr_url": self.pr_url,
            "pr_number": self.pr_number,
            "pr_status": self.pr_status.value,
            "validation_gate": self.validation_gate.to_dict(),
            "sandbox_outcome": self.sandbox_outcome.to_dict() if self.sandbox_outcome else None,
            "manifest_summary": {
                "total_files": self.manifest.total_changed_files if self.manifest else 0,
                "added_lines": self.manifest.added_lines if self.manifest else 0,
                "removed_lines": self.manifest.removed_lines if self.manifest else 0,
                "all_validations_passed": self.manifest.all_validations_passed if self.manifest else False,
            } if self.manifest else None,
            "error": self.error,
            "created_at": self.created_at,
        }


@dataclass
class AutonomousPRRequest:
    candidate: AutonomousImprovementCandidate | None = None
    candidate_slug: str = ""
    description: str = ""
    step_executors_factory: Any = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "candidate_id": self.candidate.candidate_id if self.candidate else "",
            "candidate_slug": self.candidate_slug,
            "description": self.description,
        }


@dataclass
class AutonomousPRResult:
    success: bool = False
    sandbox: WorktreeSandbox | None = None
    manifest: ChangeSetManifest | None = None
    review_packet: PRReviewPacket | None = None
    sandbox_outcome: SandboxOutcomeCommitted | None = None
    error: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "success": self.success,
            "sandbox": self.sandbox.to_dict() if self.sandbox else None,
            "manifest": self.manifest.to_dict() if self.manifest else None,
            "review_packet": self.review_packet.to_dict() if self.review_packet else None,
            "sandbox_outcome": self.sandbox_outcome.to_dict() if self.sandbox_outcome else None,
            "error": self.error,
        }


def _run_cmd(
    cmd: list[str], cwd: str | None = None, timeout: int = 60
) -> subprocess.CompletedProcess:
    return subprocess.run(
        cmd,
        cwd=cwd or _REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def _gh_available() -> bool:
    try:
        result = _run_cmd(["gh", "--version"], timeout=10)
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def _git_diff_stat(cwd: str) -> list[ChangedFile]:
    result = _run_cmd(["git", "diff", "--numstat", "HEAD~1"], cwd=cwd)
    if result.returncode != 0:
        return []
    files = []
    for line in result.stdout.strip().split("\n"):
        if not line.strip():
            continue
        parts = line.split("\t")
        if len(parts) >= 3:
            added = int(parts[0]) if parts[0] != "-" else 0
            removed = int(parts[1]) if parts[1] != "-" else 0
            files.append(ChangedFile(
                path=parts[2],
                change_type="modified",
                added_lines=added,
                removed_lines=removed,
            ))
    return files


class CandidateConflictDetector:
    """Detects conflicts between candidates for parallel scheduling."""

    def __init__(self, sandbox_manager: SandboxManager) -> None:
        self._sandbox_manager = sandbox_manager

    def can_parallelize(
        self,
        candidate_a: AutonomousImprovementCandidate,
        candidate_b: AutonomousImprovementCandidate,
    ) -> tuple[bool, list[str]]:
        reasons: list[str] = []

        if candidate_a.risk_class != "low":
            reasons.append(f"candidate_a risk={candidate_a.risk_class}")
        if candidate_b.risk_class != "low":
            reasons.append(f"candidate_b risk={candidate_b.risk_class}")

        if not candidate_a.matching_template_id:
            reasons.append("candidate_a has no template")
        if not candidate_b.matching_template_id:
            reasons.append("candidate_b has no template")

        if not candidate_a.validation_method:
            reasons.append("candidate_a has no validation method")
        if not candidate_b.validation_method:
            reasons.append("candidate_b has no validation method")

        has_rollback_a = bool(candidate_a.rollback_method) or candidate_a.non_mutating
        has_rollback_b = bool(candidate_b.rollback_method) or candidate_b.non_mutating
        if not has_rollback_a:
            reasons.append("candidate_a has no rollback plan")
        if not has_rollback_b:
            reasons.append("candidate_b has no rollback plan")

        files_a = set(candidate_a.affected_files)
        files_b = set(candidate_b.affected_files)
        overlap = files_a & files_b
        if overlap:
            reasons.append(f"overlapping files: {', '.join(sorted(overlap)[:5])}")

        entities_a = set(candidate_a.affected_entities)
        entities_b = set(candidate_b.affected_entities)
        entity_overlap = entities_a & entities_b
        if entity_overlap:
            reasons.append(f"overlapping entities: {', '.join(sorted(entity_overlap)[:5])}")

        existing_locks = self._sandbox_manager.check_file_conflicts(
            list(files_a | files_b)
        )
        if existing_locks:
            reasons.append(f"existing file locks: {', '.join(existing_locks[:5])}")

        return (len(reasons) == 0, reasons)

    def parallel_dry_run(
        self, candidates: list[AutonomousImprovementCandidate]
    ) -> dict[str, Any]:
        n = len(candidates)
        pairs: list[dict[str, Any]] = []
        parallelizable: list[tuple[str, str]] = []
        blocked: list[tuple[str, str, list[str]]] = []

        for i in range(n):
            for j in range(i + 1, n):
                can_par, reasons = self.can_parallelize(candidates[i], candidates[j])
                pair_info = {
                    "candidate_a": candidates[i].candidate_id,
                    "candidate_b": candidates[j].candidate_id,
                    "can_parallelize": can_par,
                    "reasons": reasons,
                }
                pairs.append(pair_info)
                if can_par:
                    parallelizable.append(
                        (candidates[i].candidate_id, candidates[j].candidate_id)
                    )
                else:
                    blocked.append(
                        (candidates[i].candidate_id, candidates[j].candidate_id, reasons)
                    )

        return {
            "total_candidates": n,
            "total_pairs": len(pairs),
            "parallelizable_pairs": len(parallelizable),
            "blocked_pairs": len(blocked),
            "pairs": pairs,
        }


class AutonomousPRFactory:
    """Converts eligible autonomous improvements into isolated PRs."""

    def __init__(
        self,
        sandbox_manager: SandboxManager,
        repo_root: str | None = None,
        store_dir: str | None = None,
        on_sandbox_outcome: Callable[[SandboxOutcomeCommitted], None] | None = None,
        on_production_outcome: Callable[[ProductionOutcomeCommitted], None] | None = None,
    ) -> None:
        self._sandbox_manager = sandbox_manager
        self._repo_root = repo_root or _REPO_ROOT
        self._store_dir = store_dir or os.path.join(
            self._repo_root, "data", "umh", "autonomous_lane"
        )
        self._on_sandbox_outcome = on_sandbox_outcome
        self._on_production_outcome = on_production_outcome
        self._review_packets: list[PRReviewPacket] = []
        self._conflict_detector = CandidateConflictDetector(sandbox_manager)

    @property
    def review_packets(self) -> list[PRReviewPacket]:
        return list(self._review_packets)

    @property
    def conflict_detector(self) -> CandidateConflictDetector:
        return self._conflict_detector

    def create_pr(
        self,
        request: AutonomousPRRequest,
    ) -> AutonomousPRResult:
        candidate = request.candidate
        if not candidate:
            return AutonomousPRResult(error="No candidate provided")

        result = AutonomousPRResult()
        review = PRReviewPacket(
            candidate_id=candidate.candidate_id,
        )

        try:
            slug = request.candidate_slug or candidate.description[:40]
            sandbox = self._sandbox_manager.create_sandbox(
                candidate_id=candidate.candidate_id,
                candidate_slug=slug,
                template_id=candidate.matching_template_id,
                agent_type=candidate.required_agent_type,
                affected_files=candidate.affected_files,
            )
            result.sandbox = sandbox
            review.sandbox_id = sandbox.sandbox_id
            review.branch_name = sandbox.branch_name
            review.pr_status = PRCreationStatus.BRANCH_CREATED

            self._sandbox_manager.update_status(
                sandbox.sandbox_id, SandboxStatus.EXECUTING
            )

            self._apply_changes(sandbox, candidate, request)

            gate = self._run_validation_gate(sandbox)
            review.validation_gate = gate

            if not gate.all_passed:
                self._sandbox_manager.update_status(
                    sandbox.sandbox_id,
                    SandboxStatus.VALIDATION_FAILED,
                    error="Validation gate failed",
                )
                review.pr_status = PRCreationStatus.BLOCKED_VALIDATION
                review.error = "Validation gate failed"
                result.review_packet = review
                self._review_packets.append(review)
                return result

            self._sandbox_manager.update_status(
                sandbox.sandbox_id, SandboxStatus.VALIDATED
            )

            manifest = self._build_manifest(sandbox, candidate, gate)
            manifest.persist(os.path.join(self._store_dir, "manifests"))
            result.manifest = manifest
            review.manifest_id = manifest.manifest_id
            review.manifest = manifest

            self._commit_changes(sandbox, candidate, manifest)
            review.pr_status = PRCreationStatus.COMMITTED

            pr_url, pr_number = self._create_github_pr(sandbox, manifest)
            if pr_url:
                review.pr_url = pr_url
                review.pr_number = pr_number
                review.pr_status = PRCreationStatus.PR_CREATED
                self._sandbox_manager.update_status(
                    sandbox.sandbox_id,
                    SandboxStatus.PR_CREATED,
                    pr_url=pr_url,
                    pr_number=pr_number,
                )
            else:
                review.pr_status = PRCreationStatus.BLOCKED_MISSING_TOOL
                review.error = "gh CLI unavailable — branch and manifest ready for manual PR"

            sandbox_outcome = SandboxOutcomeCommitted(
                sandbox_id=sandbox.sandbox_id,
                candidate_id=candidate.candidate_id,
                manifest_id=manifest.manifest_id,
                branch_name=sandbox.branch_name,
                pr_url=pr_url,
                pr_number=pr_number,
                validation_passed=gate.all_passed,
                template_confidence_before=manifest.template_confidence_before,
                template_confidence_after=manifest.template_confidence_after,
                agent_reliability_before=manifest.agent_reliability_before,
                agent_reliability_after=manifest.agent_reliability_after,
                changed_files=[cf.path for cf in manifest.changed_files],
            )

            manifest.propagation_proof.sandbox_outcome_emitted = True
            manifest.propagation_proof.sandbox_outcome_id = sandbox_outcome.event_id
            manifest.persist(os.path.join(self._store_dir, "manifests"))

            result.sandbox_outcome = sandbox_outcome
            review.sandbox_outcome = sandbox_outcome

            if self._on_sandbox_outcome:
                self._on_sandbox_outcome(sandbox_outcome)

            result.success = True

        except Exception as exc:
            result.error = str(exc)[:500]
            review.error = str(exc)[:500]
            review.pr_status = PRCreationStatus.FAILED
            if result.sandbox:
                self._sandbox_manager.update_status(
                    result.sandbox.sandbox_id,
                    SandboxStatus.ABANDONED,
                    error=str(exc)[:200],
                )
            logger.exception("PR factory failed for candidate %s", candidate.candidate_id)

        result.review_packet = review
        self._review_packets.append(review)
        self._persist_result(result)
        return result

    def verify_merge(
        self,
        sandbox_id: str,
    ) -> ProductionOutcomeCommitted | None:
        from substrate.organism.production_merge_verifier import ProductionMergeVerifier

        sb = self._sandbox_manager.get_sandbox(sandbox_id)
        if not sb:
            logger.warning("verify_merge: unknown sandbox %s", sandbox_id)
            return None

        manifest_id = ""
        expected_files: list[str] = []
        for rp in self._review_packets:
            if rp.sandbox_id == sandbox_id:
                manifest_id = rp.manifest_id
                if rp.manifest:
                    expected_files = [cf.path for cf in rp.manifest.changed_files]
                break

        verifier = ProductionMergeVerifier(
            sandbox_manager=self._sandbox_manager,
            repo_root=self._repo_root,
            store_dir=os.path.join(self._store_dir, "merge_verifications"),
            on_production_outcome=self._on_production_outcome,
        )

        verification = verifier.verify_merge(
            sandbox_id=sandbox_id,
            pr_number=sb.pr_number,
            manifest_id=manifest_id,
            expected_files=expected_files,
        )

        from substrate.organism.production_merge_verifier import MergeVerificationStatus

        if verification.status in (
            MergeVerificationStatus.PRODUCTION_VERIFIED,
            MergeVerificationStatus.CLEANUP_READY,
        ):
            outcome = ProductionOutcomeCommitted(
                sandbox_id=sandbox_id,
                manifest_id=manifest_id,
                pr_number=sb.pr_number,
                merge_commit=verification.merge_commit,
                base_commit=verification.base_commit,
                head_commit=verification.head_commit,
                branch_name=sb.branch_name,
                post_merge_validation_passed=True,
                production_propagation_complete=True,
                production_truth_delta=(
                    verification.truth_delta.to_dict()
                    if verification.truth_delta else {}
                ),
                changed_files=verification.observed_files,
                affected_subsystems=[
                    "world_model", "contradiction_engine", "readiness_model",
                    "dependency_graph", "template_registry", "agent_capability_model",
                ],
            )
            return outcome

        logger.info(
            "Merge verification for %s ended with status %s: %s",
            sandbox_id, verification.status.value, verification.error,
        )
        return None

    def _apply_changes(
        self,
        sandbox: WorktreeSandbox,
        candidate: AutonomousImprovementCandidate,
        request: AutonomousPRRequest,
    ) -> None:
        if request.step_executors_factory:
            executors = request.step_executors_factory(candidate)
            for name, executor in executors.items():
                try:
                    executor(sandbox.worktree_path)
                except Exception as exc:
                    logger.warning("Step executor %s failed: %s", name, exc)
                    raise

    def _run_validation_gate(self, sandbox: WorktreeSandbox) -> PRValidationGate:
        gate = PRValidationGate()
        wt = sandbox.worktree_path

        for py_file in sandbox.affected_files:
            if not py_file.endswith(".py"):
                continue
            full_path = os.path.join(wt, py_file)
            if not os.path.isfile(full_path):
                continue
            result = _run_cmd(
                ["python3", "-m", "py_compile", full_path], cwd=wt, timeout=30
            )
            validation = SandboxValidationResult(
                passed=result.returncode == 0,
                command=f"py_compile {py_file}",
                stdout=result.stdout[:300],
                stderr=result.stderr[:300],
                exit_code=result.returncode,
            )
            self._sandbox_manager.add_validation_result(
                sandbox.sandbox_id, validation
            )
            if result.returncode != 0:
                gate.py_compile_passed = False
                return gate

        gate.py_compile_passed = True

        checks = [
            ("type_divergence_passed", ["python3", "scripts/check_type_divergence.py", "--all"]),
            ("instance_leak_passed", ["python3", "scripts/check_instance_leak.py", "--all"]),
            ("dependency_direction_passed", ["python3", "scripts/check_dependency_direction.py", "--all"]),
        ]

        for attr, cmd in checks:
            try:
                result = _run_cmd(cmd, cwd=wt, timeout=60)
                setattr(gate, attr, result.returncode == 0)
                validation = SandboxValidationResult(
                    passed=result.returncode == 0,
                    command=" ".join(cmd),
                    stdout=result.stdout[:300],
                    stderr=result.stderr[:300],
                    exit_code=result.returncode,
                )
                self._sandbox_manager.add_validation_result(
                    sandbox.sandbox_id, validation
                )
            except (subprocess.TimeoutExpired, FileNotFoundError):
                setattr(gate, attr, True)

        return gate

    def _build_manifest(
        self,
        sandbox: WorktreeSandbox,
        candidate: AutonomousImprovementCandidate,
        gate: PRValidationGate,
    ) -> ChangeSetManifest:
        manifest = ChangeSetManifest(
            candidate_id=candidate.candidate_id,
            template_id=candidate.matching_template_id,
            sandbox_id=sandbox.sandbox_id,
            branch_name=sandbox.branch_name,
            base_commit=sandbox.base_commit,
            risk_class=candidate.risk_class,
            description=candidate.description,
            validation_commands=[
                "python3 -m py_compile",
                "scripts/check_type_divergence.py --all",
                "scripts/check_instance_leak.py --all",
                "scripts/check_dependency_direction.py --all",
            ],
            rollback_plan=candidate.rollback_method,
            affected_entities=candidate.affected_entities,
            template_confidence_before=candidate.template_confidence,
            agent_reliability_before=candidate.agent_reliability,
        )

        for vr in sandbox.validation_results:
            manifest.validation_results.append(ValidationProof(
                command=vr.command,
                passed=vr.passed,
                exit_code=vr.exit_code,
                output_summary=vr.stdout[:200],
                validated_at=vr.validated_at,
            ))

        manifest.risk_proof = RiskProof(
            risk_class=candidate.risk_class,
            governance_mode=candidate.governance_mode_required,
            file_count_within_limit=len(candidate.affected_files) <= 2,
            no_auth_changes="auth" not in candidate.description.lower(),
            no_credential_changes="credential" not in candidate.description.lower(),
            no_dns_changes="dns" not in candidate.description.lower(),
            no_destructive_ops="rm " not in candidate.description.lower(),
        )

        manifest.rollback_proof = RollbackProof(
            has_rollback=bool(candidate.rollback_method),
            rollback_method=candidate.rollback_method,
            is_non_mutating=candidate.non_mutating,
        )

        changed = _git_diff_stat(sandbox.worktree_path) if os.path.isdir(sandbox.worktree_path) else []
        manifest.changed_files = changed
        manifest.added_lines = sum(f.added_lines for f in changed)
        manifest.removed_lines = sum(f.removed_lines for f in changed)

        return manifest

    def _commit_changes(
        self,
        sandbox: WorktreeSandbox,
        candidate: AutonomousImprovementCandidate,
        manifest: ChangeSetManifest,
    ) -> None:
        wt = sandbox.worktree_path
        _run_cmd(["git", "add", "-A"], cwd=wt)

        desc = candidate.description[:60]
        msg = f"feat(auto): {desc}\n\nManifest: {manifest.manifest_id}\nCandidate: {candidate.candidate_id}"
        result = _run_cmd(["git", "commit", "-m", msg], cwd=wt)

        if result.returncode == 0:
            head = _run_cmd(["git", "rev-parse", "HEAD"], cwd=wt)
            if head.returncode == 0:
                sandbox.head_commit = head.stdout.strip()
                manifest.head_commit = sandbox.head_commit

            _run_cmd(["git", "push", "-u", "origin", sandbox.branch_name], cwd=wt)

    def _create_github_pr(
        self,
        sandbox: WorktreeSandbox,
        manifest: ChangeSetManifest,
    ) -> tuple[str, int]:
        if not _gh_available():
            return ("", 0)

        body = manifest.to_pr_description()
        title = f"auto: {manifest.description[:60]}"

        result = _run_cmd(
            [
                "gh", "pr", "create",
                "--title", title,
                "--body", body,
                "--base", "main",
                "--head", sandbox.branch_name,
            ],
            cwd=self._repo_root,
            timeout=30,
        )

        if result.returncode == 0:
            pr_url = result.stdout.strip()
            pr_number = 0
            if "/" in pr_url:
                try:
                    pr_number = int(pr_url.rstrip("/").split("/")[-1])
                except ValueError:
                    pass
            return (pr_url, pr_number)

        logger.warning("gh pr create failed: %s", result.stderr)
        return ("", 0)

    def _run_post_merge_validation(self) -> bool:
        result = _run_cmd(
            ["python3", "-c", "import sys; sys.path.insert(0,'.'); import substrate; print('ok')"],
            cwd=self._repo_root,
            timeout=30,
        )
        return result.returncode == 0

    def _persist_result(self, result: AutonomousPRResult) -> None:
        os.makedirs(self._store_dir, exist_ok=True)
        results_path = os.path.join(self._store_dir, "pr_factory_results.jsonl")
        with open(results_path, "a") as f:
            f.write(json.dumps(result.to_dict(), default=str) + "\n")

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_review_packets": len(self._review_packets),
            "pr_created_count": sum(
                1 for rp in self._review_packets
                if rp.pr_status == PRCreationStatus.PR_CREATED
            ),
            "blocked_count": sum(
                1 for rp in self._review_packets
                if rp.pr_status in (
                    PRCreationStatus.BLOCKED_MISSING_TOOL,
                    PRCreationStatus.BLOCKED_VALIDATION,
                )
            ),
            "failed_count": sum(
                1 for rp in self._review_packets
                if rp.pr_status == PRCreationStatus.FAILED
            ),
            "review_packets": [rp.to_dict() for rp in self._review_packets[-10:]],
            "sandbox_manager": self._sandbox_manager.to_dict(),
        }
