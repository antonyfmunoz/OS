"""Phase 9.7 — Sandboxed Autonomous PR Factory tests.

Tests cover:
  - WorktreeSandboxManager: creation, locks, conflicts, cleanup, status
  - ChangeSetManifest: creation, serialization, PR description, persistence
  - AutonomousPRFactory: lifecycle, validation, PR creation, outcome boundary
  - Truth boundary: sandbox vs production outcome semantics
  - Parallelization: conflict detection, dry-run scheduling
  - API/cockpit: endpoint wiring
"""

from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
import time
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, "/opt/OS")

from substrate.organism.worktree_sandbox import (
    SandboxCleanupPolicy,
    SandboxLock,
    SandboxManager,
    SandboxStatus,
    SandboxValidationResult,
    WorktreeSandbox,
    make_branch_name,
)
from substrate.organism.changeset_manifest import (
    ChangedFile,
    ChangeSetManifest,
    PropagationProof,
    RiskProof,
    RollbackProof,
    ValidationProof,
)
from substrate.organism.autonomous_pr_factory import (
    AutonomousPRFactory,
    AutonomousPRRequest,
    AutonomousPRResult,
    CandidateConflictDetector,
    OutcomeBoundary,
    PRCreationStatus,
    PRReviewPacket,
    PRValidationGate,
    ProductionOutcomeCommitted,
    SandboxOutcomeCommitted,
)
from substrate.organism.autonomous_improvement_lane import (
    AutonomousImprovementCandidate,
)


# ── Fixtures ───────────────────────────────────────────────


@pytest.fixture
def tmp_dir():
    d = tempfile.mkdtemp(prefix="test_pr_factory_")
    yield d
    shutil.rmtree(d, ignore_errors=True)


@pytest.fixture
def sandbox_manager(tmp_dir):
    store = os.path.join(tmp_dir, "sandboxes")
    return SandboxManager(
        repo_root=tmp_dir,
        worktree_base=os.path.join(tmp_dir, "worktrees"),
        store_dir=store,
        max_parallel=2,
        ttl_hours=1,
    )


@pytest.fixture
def sample_candidate():
    return AutonomousImprovementCandidate(
        candidate_id="test-candidate-001",
        description="Add missing docstring to helper function",
        affected_files=["substrate/organism/helper.py"],
        risk_class="low",
        reversible=True,
        validation_method="py_compile",
        rollback_method="git revert",
        matching_template_id="tpl-001",
        template_confidence=0.85,
        agent_reliability=0.90,
        non_mutating=False,
    )


@pytest.fixture
def sample_candidate_b():
    return AutonomousImprovementCandidate(
        candidate_id="test-candidate-002",
        description="Fix import ordering in adapters module",
        affected_files=["adapters/models/model_router.py"],
        risk_class="low",
        reversible=True,
        validation_method="py_compile",
        rollback_method="git revert",
        matching_template_id="tpl-002",
        template_confidence=0.80,
        agent_reliability=0.85,
        non_mutating=False,
    )


# ═══════════════════════════════════════════════════════════
# WorktreeSandbox tests
# ═══════════════════════════════════════════════════════════


class TestMakeBranchName:
    def test_deterministic_safe_name(self):
        name = make_branch_name("Fix helper docstring", "abc12345")
        assert name.startswith("auto/low-risk/")
        assert "abc12345" in name

    def test_slug_cleaned(self):
        name = make_branch_name("Fix 'special' chars! & more", "xyz")
        assert "'" not in name
        assert "!" not in name
        assert "&" not in name

    def test_slug_truncated(self):
        long_desc = "x" * 100
        name = make_branch_name(long_desc, "short")
        assert len(name.split("/")[-1]) <= 60

    def test_lowercase(self):
        name = make_branch_name("FIX UPPERCASE STUFF", "id1")
        assert name == name.lower()


class TestWorktreeSandbox:
    def test_default_fields(self):
        sb = WorktreeSandbox()
        assert sb.sandbox_id.startswith("sb-")
        assert sb.status == SandboxStatus.CREATED
        assert sb.pr_url == ""
        assert sb.pr_number == 0

    def test_to_dict(self):
        sb = WorktreeSandbox(
            sandbox_id="sb-test1",
            branch_name="auto/low-risk/test-1",
            status=SandboxStatus.EXECUTING,
        )
        d = sb.to_dict()
        assert d["sandbox_id"] == "sb-test1"
        assert d["status"] == "executing"
        assert d["branch_name"] == "auto/low-risk/test-1"

    def test_locks_serialization(self):
        sb = WorktreeSandbox()
        sb.locks.append(SandboxLock(file_path="a.py", sandbox_id=sb.sandbox_id))
        d = sb.to_dict()
        assert len(d["locks"]) == 1
        assert d["locks"][0]["file_path"] == "a.py"


class TestSandboxValidationResult:
    def test_to_dict_truncates(self):
        vr = SandboxValidationResult(
            passed=True,
            command="py_compile test.py",
            stdout="x" * 1000,
            stderr="",
            exit_code=0,
        )
        d = vr.to_dict()
        assert len(d["stdout"]) <= 500


class TestSandboxManager:
    def test_init_empty(self, sandbox_manager):
        assert sandbox_manager.active_sandboxes == []
        assert sandbox_manager.all_sandboxes == []

    def test_check_file_conflicts_empty(self, sandbox_manager):
        conflicts = sandbox_manager.check_file_conflicts(["a.py"])
        assert conflicts == []

    @patch("substrate.organism.worktree_sandbox._run_git")
    def test_create_sandbox(self, mock_git, sandbox_manager):
        mock_git.return_value = MagicMock(
            returncode=0, stdout="abc123\n", stderr=""
        )
        sb = sandbox_manager.create_sandbox(
            candidate_id="c-001",
            candidate_slug="test-fix",
            template_id="tpl-1",
            affected_files=["a.py"],
        )
        assert sb.sandbox_id.startswith("sb-")
        assert sb.branch_name.startswith("auto/low-risk/")
        assert sb.status == SandboxStatus.CREATED
        assert "a.py" in sb.affected_files
        assert len(sb.locks) == 1

    @patch("substrate.organism.worktree_sandbox._run_git")
    def test_max_parallel_enforced(self, mock_git, sandbox_manager):
        mock_git.return_value = MagicMock(returncode=0, stdout="abc\n", stderr="")
        sandbox_manager.create_sandbox("c1", "fix-1")
        sandbox_manager.create_sandbox("c2", "fix-2")
        with pytest.raises(RuntimeError, match="Max parallel"):
            sandbox_manager.create_sandbox("c3", "fix-3")

    @patch("substrate.organism.worktree_sandbox._run_git")
    def test_file_lock_conflict(self, mock_git, sandbox_manager):
        mock_git.return_value = MagicMock(returncode=0, stdout="abc\n", stderr="")
        sandbox_manager.create_sandbox("c1", "fix-1", affected_files=["x.py"])
        with pytest.raises(RuntimeError, match="File lock conflict"):
            sandbox_manager.create_sandbox("c2", "fix-2", affected_files=["x.py"])

    @patch("substrate.organism.worktree_sandbox._run_git")
    def test_update_status(self, mock_git, sandbox_manager):
        mock_git.return_value = MagicMock(returncode=0, stdout="abc\n", stderr="")
        sb = sandbox_manager.create_sandbox("c1", "fix-1")
        updated = sandbox_manager.update_status(
            sb.sandbox_id, SandboxStatus.EXECUTING
        )
        assert updated.status == SandboxStatus.EXECUTING

    @patch("substrate.organism.worktree_sandbox._run_git")
    def test_update_status_terminal_releases_locks(self, mock_git, sandbox_manager):
        mock_git.return_value = MagicMock(returncode=0, stdout="abc\n", stderr="")
        sb = sandbox_manager.create_sandbox(
            "c1", "fix-1", affected_files=["locked.py"]
        )
        assert "locked.py" in sandbox_manager._file_locks
        sandbox_manager.update_status(sb.sandbox_id, SandboxStatus.MERGED)
        assert "locked.py" not in sandbox_manager._file_locks

    @patch("substrate.organism.worktree_sandbox._run_git")
    def test_abandon_sandbox(self, mock_git, sandbox_manager):
        mock_git.return_value = MagicMock(returncode=0, stdout="abc\n", stderr="")
        sb = sandbox_manager.create_sandbox("c1", "fix-1")
        abandoned = sandbox_manager.abandon_sandbox(sb.sandbox_id, "test reason")
        assert abandoned.status == SandboxStatus.ABANDONED
        assert abandoned.error == "test reason"

    @patch("substrate.organism.worktree_sandbox._run_git")
    def test_add_validation_result(self, mock_git, sandbox_manager):
        mock_git.return_value = MagicMock(returncode=0, stdout="abc\n", stderr="")
        sb = sandbox_manager.create_sandbox("c1", "fix-1")
        vr = SandboxValidationResult(passed=True, command="test", exit_code=0)
        sandbox_manager.add_validation_result(sb.sandbox_id, vr)
        assert len(sb.validation_results) == 1

    @patch("substrate.organism.worktree_sandbox._run_git")
    def test_cleanup_sandbox(self, mock_git, sandbox_manager):
        mock_git.return_value = MagicMock(returncode=0, stdout="abc\n", stderr="")
        sb = sandbox_manager.create_sandbox("c1", "fix-1", affected_files=["a.py"])
        ok = sandbox_manager.cleanup_sandbox(sb.sandbox_id)
        assert ok
        assert sb.status == SandboxStatus.CLEANED

    @patch("substrate.organism.worktree_sandbox._run_git")
    def test_unknown_sandbox_raises(self, mock_git, sandbox_manager):
        with pytest.raises(KeyError):
            sandbox_manager.update_status("nonexistent", SandboxStatus.EXECUTING)

    @patch("substrate.organism.worktree_sandbox._run_git")
    def test_persist_and_reload(self, mock_git, tmp_dir):
        mock_git.return_value = MagicMock(returncode=0, stdout="abc\n", stderr="")
        store = os.path.join(tmp_dir, "sandboxes")
        mgr1 = SandboxManager(
            repo_root=tmp_dir,
            worktree_base=os.path.join(tmp_dir, "wt"),
            store_dir=store,
        )
        sb = mgr1.create_sandbox("c1", "test-persist")
        mgr2 = SandboxManager(
            repo_root=tmp_dir,
            worktree_base=os.path.join(tmp_dir, "wt"),
            store_dir=store,
        )
        assert len(mgr2.all_sandboxes) == 1
        assert mgr2.all_sandboxes[0].sandbox_id == sb.sandbox_id

    @patch("substrate.organism.worktree_sandbox._run_git")
    def test_to_dict(self, mock_git, sandbox_manager):
        mock_git.return_value = MagicMock(returncode=0, stdout="abc\n", stderr="")
        sandbox_manager.create_sandbox("c1", "fix-1")
        d = sandbox_manager.to_dict()
        assert d["total_sandboxes"] == 1
        assert d["active_sandboxes"] == 1

    @patch("substrate.organism.worktree_sandbox._run_git")
    def test_production_truth(self, mock_git, sandbox_manager):
        mock_git.return_value = MagicMock(
            returncode=0, stdout="abc123\n", stderr=""
        )
        truth = sandbox_manager.production_truth()
        assert "main_commit" in truth

    @patch("substrate.organism.worktree_sandbox._run_git")
    def test_cleanup_expired_only_abandoned(self, mock_git, sandbox_manager):
        mock_git.return_value = MagicMock(returncode=0, stdout="abc\n", stderr="")
        sb = sandbox_manager.create_sandbox("c1", "fix-1")
        sb.created_at = time.time() - 7200
        sandbox_manager.update_status(sb.sandbox_id, SandboxStatus.ABANDONED)
        cleaned = sandbox_manager.cleanup_expired()
        assert sb.sandbox_id in cleaned

    def test_get_sandbox_nonexistent(self, sandbox_manager):
        assert sandbox_manager.get_sandbox("nope") is None


# ═══════════════════════════════════════════════════════════
# ChangeSetManifest tests
# ═══════════════════════════════════════════════════════════


class TestChangedFile:
    def test_to_dict(self):
        cf = ChangedFile(path="a.py", change_type="added", added_lines=10, removed_lines=0)
        d = cf.to_dict()
        assert d["path"] == "a.py"
        assert d["added_lines"] == 10


class TestValidationProof:
    def test_output_truncated(self):
        vp = ValidationProof(
            command="test",
            passed=True,
            exit_code=0,
            output_summary="x" * 1000,
        )
        d = vp.to_dict()
        assert len(d["output_summary"]) <= 300


class TestRiskProof:
    def test_all_passed_true(self):
        rp = RiskProof()
        assert rp.all_passed

    def test_all_passed_false_on_auth(self):
        rp = RiskProof(no_auth_changes=False)
        assert not rp.all_passed

    def test_all_passed_false_on_risk(self):
        rp = RiskProof(risk_class="high")
        assert not rp.all_passed


class TestChangeSetManifest:
    def test_default_fields(self):
        m = ChangeSetManifest()
        assert m.manifest_id.startswith("csm-")
        assert m.risk_class == "low"

    def test_total_changed_files(self):
        m = ChangeSetManifest()
        m.changed_files = [ChangedFile(path="a.py"), ChangedFile(path="b.py")]
        assert m.total_changed_files == 2

    def test_all_validations_passed_empty(self):
        m = ChangeSetManifest()
        assert not m.all_validations_passed

    def test_all_validations_passed_true(self):
        m = ChangeSetManifest()
        m.validation_results = [
            ValidationProof(passed=True, command="test1", exit_code=0),
            ValidationProof(passed=True, command="test2", exit_code=0),
        ]
        assert m.all_validations_passed

    def test_all_validations_passed_false(self):
        m = ChangeSetManifest()
        m.validation_results = [
            ValidationProof(passed=True, command="test1", exit_code=0),
            ValidationProof(passed=False, command="test2", exit_code=1),
        ]
        assert not m.all_validations_passed

    def test_to_dict(self):
        m = ChangeSetManifest(
            candidate_id="c1",
            description="test manifest",
        )
        d = m.to_dict()
        assert d["candidate_id"] == "c1"
        assert d["description"] == "test manifest"
        assert "changed_files" in d

    def test_to_pr_description(self):
        m = ChangeSetManifest(
            candidate_id="c1",
            template_id="tpl-1",
            description="Add docstring",
            branch_name="auto/low-risk/test",
            base_commit="abc123456789",
        )
        m.changed_files = [ChangedFile(path="a.py", added_lines=5, removed_lines=1)]
        m.validation_results = [
            ValidationProof(passed=True, command="py_compile", exit_code=0)
        ]
        desc = m.to_pr_description()
        assert "Autonomous Improvement" in desc
        assert "c1" in desc
        assert "tpl-1" in desc
        assert "a.py" in desc
        assert "[PASS]" in desc
        assert "UMH Autonomous PR Factory" in desc

    def test_persist_and_load(self, tmp_dir):
        m = ChangeSetManifest(
            candidate_id="c1",
            description="test",
        )
        m.changed_files = [ChangedFile(path="x.py", added_lines=3)]
        path = m.persist(store_dir=tmp_dir)
        assert os.path.isfile(path)

        loaded = ChangeSetManifest.load(path)
        assert loaded.manifest_id == m.manifest_id
        assert loaded.candidate_id == "c1"
        assert len(loaded.changed_files) == 1

    def test_propagation_proof_default(self):
        pp = PropagationProof()
        assert not pp.sandbox_outcome_emitted
        assert not pp.production_outcome_emitted

    def test_rollback_proof_default(self):
        rp = RollbackProof()
        assert not rp.has_rollback


# ═══════════════════════════════════════════════════════════
# AutonomousPRFactory tests
# ═══════════════════════════════════════════════════════════


class TestSandboxOutcomeCommitted:
    def test_default_boundary(self):
        soc = SandboxOutcomeCommitted()
        assert soc.boundary == "sandbox"
        assert soc.event_id.startswith("soc-")

    def test_to_dict(self):
        soc = SandboxOutcomeCommitted(
            sandbox_id="sb-1",
            candidate_id="c-1",
            validation_passed=True,
        )
        d = soc.to_dict()
        assert d["event_type"] == "sandbox_outcome_committed"
        assert d["boundary"] == "sandbox"
        assert d["validation_passed"] is True


class TestProductionOutcomeCommitted:
    def test_default_boundary(self):
        poc = ProductionOutcomeCommitted()
        assert poc.boundary == "production"
        assert poc.event_id.startswith("poc-")

    def test_to_dict(self):
        poc = ProductionOutcomeCommitted(
            sandbox_id="sb-1",
            merge_commit="def456",
            post_merge_validation_passed=True,
        )
        d = poc.to_dict()
        assert d["event_type"] == "production_outcome_committed"
        assert d["boundary"] == "production"
        assert d["merge_commit"] == "def456"


class TestPRValidationGate:
    def test_all_passed_default(self):
        gate = PRValidationGate()
        assert not gate.all_passed

    def test_all_passed_true(self):
        gate = PRValidationGate(
            py_compile_passed=True,
            type_divergence_passed=True,
            instance_leak_passed=True,
            dependency_direction_passed=True,
        )
        assert gate.all_passed

    def test_all_passed_false_one_gate(self):
        gate = PRValidationGate(
            py_compile_passed=True,
            type_divergence_passed=False,
            instance_leak_passed=True,
            dependency_direction_passed=True,
        )
        assert not gate.all_passed

    def test_custom_validations(self):
        gate = PRValidationGate(
            py_compile_passed=True,
            type_divergence_passed=True,
            instance_leak_passed=True,
            dependency_direction_passed=True,
            custom_validations=[
                ValidationProof(passed=False, command="custom", exit_code=1)
            ],
        )
        assert not gate.all_passed


class TestPRReviewPacket:
    def test_to_dict(self):
        rp = PRReviewPacket(
            sandbox_id="sb-1",
            candidate_id="c-1",
            pr_status=PRCreationStatus.PR_CREATED,
        )
        d = rp.to_dict()
        assert d["pr_status"] == "pr_created"


class TestOutcomeBoundary:
    def test_enum_values(self):
        assert OutcomeBoundary.SANDBOX.value == "sandbox"
        assert OutcomeBoundary.PRODUCTION.value == "production"


class TestCandidateConflictDetector:
    @patch("substrate.organism.worktree_sandbox._run_git")
    def test_non_overlapping_can_parallelize(
        self, mock_git, sandbox_manager, sample_candidate, sample_candidate_b
    ):
        mock_git.return_value = MagicMock(returncode=0, stdout="abc\n")
        detector = CandidateConflictDetector(sandbox_manager)
        can, reasons = detector.can_parallelize(sample_candidate, sample_candidate_b)
        assert can
        assert len(reasons) == 0

    @patch("substrate.organism.worktree_sandbox._run_git")
    def test_overlapping_files_blocked(
        self, mock_git, sandbox_manager, sample_candidate
    ):
        mock_git.return_value = MagicMock(returncode=0, stdout="abc\n")
        b = AutonomousImprovementCandidate(
            candidate_id="c-overlap",
            affected_files=["substrate/organism/helper.py"],
            risk_class="low",
            matching_template_id="tpl-x",
            validation_method="test",
            rollback_method="revert",
        )
        detector = CandidateConflictDetector(sandbox_manager)
        can, reasons = detector.can_parallelize(sample_candidate, b)
        assert not can
        assert any("overlapping files" in r for r in reasons)

    @patch("substrate.organism.worktree_sandbox._run_git")
    def test_high_risk_blocked(
        self, mock_git, sandbox_manager, sample_candidate
    ):
        mock_git.return_value = MagicMock(returncode=0, stdout="abc\n")
        high_risk = AutonomousImprovementCandidate(
            candidate_id="c-high",
            risk_class="high",
            matching_template_id="tpl-x",
            validation_method="test",
            rollback_method="revert",
        )
        detector = CandidateConflictDetector(sandbox_manager)
        can, reasons = detector.can_parallelize(sample_candidate, high_risk)
        assert not can
        assert any("risk=high" in r for r in reasons)

    @patch("substrate.organism.worktree_sandbox._run_git")
    def test_no_template_blocked(
        self, mock_git, sandbox_manager, sample_candidate
    ):
        mock_git.return_value = MagicMock(returncode=0, stdout="abc\n")
        no_tpl = AutonomousImprovementCandidate(
            candidate_id="c-notpl",
            risk_class="low",
            matching_template_id="",
            validation_method="test",
            rollback_method="revert",
        )
        detector = CandidateConflictDetector(sandbox_manager)
        can, reasons = detector.can_parallelize(sample_candidate, no_tpl)
        assert not can

    @patch("substrate.organism.worktree_sandbox._run_git")
    def test_parallel_dry_run(
        self, mock_git, sandbox_manager, sample_candidate, sample_candidate_b
    ):
        mock_git.return_value = MagicMock(returncode=0, stdout="abc\n")
        detector = CandidateConflictDetector(sandbox_manager)
        result = detector.parallel_dry_run([sample_candidate, sample_candidate_b])
        assert result["total_candidates"] == 2
        assert result["total_pairs"] == 1
        assert result["parallelizable_pairs"] == 1

    @patch("substrate.organism.worktree_sandbox._run_git")
    def test_parallel_dry_run_with_conflict(
        self, mock_git, sandbox_manager, sample_candidate
    ):
        mock_git.return_value = MagicMock(returncode=0, stdout="abc\n")
        overlap = AutonomousImprovementCandidate(
            candidate_id="c-ov",
            affected_files=sample_candidate.affected_files,
            risk_class="low",
            matching_template_id="tpl-y",
            validation_method="test",
            rollback_method="revert",
        )
        detector = CandidateConflictDetector(sandbox_manager)
        result = detector.parallel_dry_run([sample_candidate, overlap])
        assert result["blocked_pairs"] == 1
        assert result["parallelizable_pairs"] == 0


class TestAutonomousPRFactory:
    @patch("substrate.organism.worktree_sandbox._run_git")
    def test_create_pr_no_candidate(self, mock_git, sandbox_manager, tmp_dir):
        factory = AutonomousPRFactory(
            sandbox_manager=sandbox_manager,
            store_dir=tmp_dir,
        )
        req = AutonomousPRRequest()
        result = factory.create_pr(req)
        assert not result.success
        assert "No candidate" in result.error

    @patch("substrate.organism.worktree_sandbox._run_git")
    def test_create_pr_lifecycle(self, mock_git, sandbox_manager, tmp_dir, sample_candidate):
        mock_git.return_value = MagicMock(
            returncode=0, stdout="abc123\n", stderr=""
        )

        sandbox_outcome_received = []

        def on_sandbox_outcome(soc):
            sandbox_outcome_received.append(soc)

        factory = AutonomousPRFactory(
            sandbox_manager=sandbox_manager,
            store_dir=tmp_dir,
            on_sandbox_outcome=on_sandbox_outcome,
        )

        def step_factory(candidate):
            return {"step1": lambda wt: None}

        req = AutonomousPRRequest(
            candidate=sample_candidate,
            candidate_slug="test-fix",
            step_executors_factory=step_factory,
        )

        with patch.object(factory, "_run_validation_gate") as mock_gate, \
             patch.object(factory, "_create_github_pr") as mock_pr, \
             patch.object(factory, "_commit_changes"):
            mock_gate.return_value = PRValidationGate(
                py_compile_passed=True,
                type_divergence_passed=True,
                instance_leak_passed=True,
                dependency_direction_passed=True,
            )
            mock_pr.return_value = ("", 0)

            result = factory.create_pr(req)

        assert result.success
        assert result.sandbox is not None
        assert result.manifest is not None
        assert result.sandbox_outcome is not None
        assert result.review_packet.pr_status == PRCreationStatus.BLOCKED_MISSING_TOOL
        assert len(sandbox_outcome_received) == 1
        assert sandbox_outcome_received[0].boundary == "sandbox"

    @patch("substrate.organism.worktree_sandbox._run_git")
    def test_create_pr_validation_failure(self, mock_git, sandbox_manager, tmp_dir, sample_candidate):
        mock_git.return_value = MagicMock(
            returncode=0, stdout="abc123\n", stderr=""
        )

        factory = AutonomousPRFactory(
            sandbox_manager=sandbox_manager,
            store_dir=tmp_dir,
        )

        req = AutonomousPRRequest(
            candidate=sample_candidate,
            candidate_slug="test-fail",
        )

        with patch.object(factory, "_run_validation_gate") as mock_gate:
            mock_gate.return_value = PRValidationGate(
                py_compile_passed=False,
                type_divergence_passed=True,
                instance_leak_passed=True,
                dependency_direction_passed=True,
            )

            result = factory.create_pr(req)

        assert not result.success
        assert result.review_packet.pr_status == PRCreationStatus.BLOCKED_VALIDATION

    @patch("substrate.organism.worktree_sandbox._run_git")
    def test_review_packets_tracked(self, mock_git, sandbox_manager, tmp_dir, sample_candidate):
        mock_git.return_value = MagicMock(
            returncode=0, stdout="abc123\n", stderr=""
        )

        factory = AutonomousPRFactory(
            sandbox_manager=sandbox_manager,
            store_dir=tmp_dir,
        )

        req = AutonomousPRRequest(
            candidate=sample_candidate,
            candidate_slug="test",
        )

        with patch.object(factory, "_run_validation_gate") as mock_gate, \
             patch.object(factory, "_create_github_pr") as mock_pr, \
             patch.object(factory, "_commit_changes"):
            mock_gate.return_value = PRValidationGate(
                py_compile_passed=True,
                type_divergence_passed=True,
                instance_leak_passed=True,
                dependency_direction_passed=True,
            )
            mock_pr.return_value = ("https://github.com/test/pull/42", 42)
            factory.create_pr(req)

        assert len(factory.review_packets) == 1
        assert factory.review_packets[0].pr_number == 42
        assert factory.review_packets[0].pr_status == PRCreationStatus.PR_CREATED

    @patch("substrate.organism.worktree_sandbox._run_git")
    def test_to_dict(self, mock_git, sandbox_manager, tmp_dir):
        factory = AutonomousPRFactory(
            sandbox_manager=sandbox_manager,
            store_dir=tmp_dir,
        )
        d = factory.to_dict()
        assert d["total_review_packets"] == 0
        assert "sandbox_manager" in d

    @patch("substrate.organism.worktree_sandbox._run_git")
    def test_factory_exception_handling(self, mock_git, sandbox_manager, tmp_dir, sample_candidate):
        mock_git.return_value = MagicMock(
            returncode=0, stdout="abc123\n", stderr=""
        )

        factory = AutonomousPRFactory(
            sandbox_manager=sandbox_manager,
            store_dir=tmp_dir,
        )

        def bad_executor(candidate):
            return {"step1": lambda wt: (_ for _ in ()).throw(RuntimeError("boom"))}

        req = AutonomousPRRequest(
            candidate=sample_candidate,
            candidate_slug="test-boom",
            step_executors_factory=bad_executor,
        )

        result = factory.create_pr(req)
        assert not result.success
        assert "boom" in result.error


# ═══════════════════════════════════════════════════════════
# Truth boundary tests
# ═══════════════════════════════════════════════════════════


class TestTruthBoundary:
    def test_sandbox_outcome_is_not_production(self):
        soc = SandboxOutcomeCommitted()
        assert soc.boundary == "sandbox"
        assert soc.boundary != "production"

    def test_production_outcome_is_production(self):
        poc = ProductionOutcomeCommitted()
        assert poc.boundary == "production"

    def test_sandbox_outcome_does_not_claim_production(self):
        soc = SandboxOutcomeCommitted(
            sandbox_id="sb-1",
            validation_passed=True,
        )
        d = soc.to_dict()
        assert d["boundary"] == "sandbox"
        assert "production" not in d["event_type"]

    def test_production_outcome_claims_production(self):
        poc = ProductionOutcomeCommitted(
            sandbox_id="sb-1",
            merge_commit="abc",
            post_merge_validation_passed=True,
            production_propagation_complete=True,
        )
        d = poc.to_dict()
        assert d["boundary"] == "production"
        assert d["production_propagation_complete"] is True

    @patch("substrate.organism.worktree_sandbox._run_git")
    def test_sandbox_success_no_production_update(
        self, mock_git, sandbox_manager, tmp_dir, sample_candidate
    ):
        """Sandbox success must NOT trigger production state updates."""
        mock_git.return_value = MagicMock(
            returncode=0, stdout="abc123\n", stderr=""
        )

        production_updates = []

        def on_production(poc):
            production_updates.append(poc)

        factory = AutonomousPRFactory(
            sandbox_manager=sandbox_manager,
            store_dir=tmp_dir,
            on_production_outcome=on_production,
        )

        req = AutonomousPRRequest(
            candidate=sample_candidate,
            candidate_slug="test",
        )

        with patch.object(factory, "_run_validation_gate") as mock_gate, \
             patch.object(factory, "_create_github_pr") as mock_pr, \
             patch.object(factory, "_commit_changes"):
            mock_gate.return_value = PRValidationGate(
                py_compile_passed=True,
                type_divergence_passed=True,
                instance_leak_passed=True,
                dependency_direction_passed=True,
            )
            mock_pr.return_value = ("", 0)
            factory.create_pr(req)

        assert len(production_updates) == 0

    def test_propagation_proof_tracks_boundary(self):
        pp = PropagationProof(
            sandbox_outcome_emitted=True,
            sandbox_outcome_id="soc-1",
            production_outcome_emitted=False,
        )
        d = pp.to_dict()
        assert d["sandbox_outcome_emitted"] is True
        assert d["production_outcome_emitted"] is False


class TestVerifyMerge:
    @patch("substrate.organism.worktree_sandbox._run_git")
    @patch("substrate.organism.autonomous_pr_factory._run_cmd")
    def test_verify_merge_not_found(self, mock_cmd, mock_git, sandbox_manager, tmp_dir):
        mock_git.return_value = MagicMock(returncode=0, stdout="abc\n", stderr="")
        sb = sandbox_manager.create_sandbox("c1", "fix-1")
        sandbox_manager.update_status(sb.sandbox_id, SandboxStatus.PR_CREATED)

        mock_cmd.return_value = MagicMock(
            returncode=0, stdout="some unrelated commit\n", stderr=""
        )

        factory = AutonomousPRFactory(
            sandbox_manager=sandbox_manager,
            store_dir=tmp_dir,
        )
        outcome = factory.verify_merge(sb.sandbox_id)
        assert outcome is None

    @patch("substrate.organism.worktree_sandbox._run_git")
    @patch("substrate.organism.autonomous_pr_factory._run_cmd")
    def test_verify_merge_found(self, mock_cmd, mock_git, sandbox_manager, tmp_dir):
        mock_git.return_value = MagicMock(returncode=0, stdout="abc\n", stderr="")
        sb = sandbox_manager.create_sandbox("c1", "fix-1")
        sandbox_manager.update_status(
            sb.sandbox_id, SandboxStatus.PR_CREATED, pr_number=42
        )

        def cmd_side_effect(cmd, cwd=None, timeout=60):
            if "log" in cmd:
                return MagicMock(
                    returncode=0,
                    stdout=f"abc123 Merge pull request #{42} from test\n",
                    stderr="",
                )
            if "rev-parse" in cmd:
                return MagicMock(returncode=0, stdout="merged_abc\n", stderr="")
            return MagicMock(returncode=0, stdout="ok\n", stderr="")

        mock_cmd.side_effect = cmd_side_effect

        production_received = []
        factory = AutonomousPRFactory(
            sandbox_manager=sandbox_manager,
            store_dir=tmp_dir,
            on_production_outcome=lambda poc: production_received.append(poc),
        )
        outcome = factory.verify_merge(sb.sandbox_id)
        assert outcome is not None
        assert outcome.boundary == "production"
        assert len(production_received) == 1

    def test_verify_merge_unknown_sandbox(self, sandbox_manager, tmp_dir):
        factory = AutonomousPRFactory(
            sandbox_manager=sandbox_manager,
            store_dir=tmp_dir,
        )
        assert factory.verify_merge("nope") is None


# ═══════════════════════════════════════════════════════════
# PRCreationStatus enum tests
# ═══════════════════════════════════════════════════════════


class TestPRCreationStatus:
    def test_all_values(self):
        expected = {
            "not_started", "branch_created", "committed",
            "pr_created", "blocked_missing_tool",
            "blocked_validation", "failed",
        }
        actual = {s.value for s in PRCreationStatus}
        assert actual == expected

    def test_blocked_missing_tool_truthful(self):
        assert PRCreationStatus.BLOCKED_MISSING_TOOL.value == "blocked_missing_tool"


class TestSandboxStatus:
    def test_all_values(self):
        expected = {
            "created", "executing", "validation_failed",
            "validated", "pr_created", "merged",
            "abandoned", "cleaned",
        }
        actual = {s.value for s in SandboxStatus}
        assert actual == expected


# ═══════════════════════════════════════════════════════════
# API endpoint wiring tests
# ═══════════════════════════════════════════════════════════


class TestAPIWiring:
    def test_organism_bridge_has_pr_factory_actions(self):
        from transports.api.organism_bridge import _ACTIONS
        assert "organism.pr_factory" in _ACTIONS
        assert "organism.pr_factory.sandboxes" in _ACTIONS
        assert "organism.pr_factory.sandbox_detail" in _ACTIONS
        assert "organism.pr_factory.production_truth" in _ACTIONS

    def test_cockpit_pr_factory_endpoints_importable(self):
        from transports.api.cockpit import router
        routes = [r.path for r in router.routes]
        assert any("autonomous-pr-factory" in r for r in routes)
        assert any("autonomous-pr-factory/sandboxes" in r for r in routes)
        assert any("autonomous-pr-factory/production-truth" in r for r in routes)

    def test_cockpit_verify_merge_endpoint(self):
        from transports.api.cockpit import router
        routes = [r.path for r in router.routes]
        assert any("verify-merge" in r for r in routes)


# ═══════════════════════════════════════════════════════════
# Integration-style tests
# ═══════════════════════════════════════════════════════════


class TestIntegration:
    @patch("substrate.organism.worktree_sandbox._run_git")
    def test_full_lifecycle_sandbox_to_manifest(
        self, mock_git, sandbox_manager, tmp_dir, sample_candidate
    ):
        mock_git.return_value = MagicMock(
            returncode=0, stdout="abc123\n", stderr=""
        )

        factory = AutonomousPRFactory(
            sandbox_manager=sandbox_manager,
            store_dir=tmp_dir,
        )

        req = AutonomousPRRequest(
            candidate=sample_candidate,
            candidate_slug="integration-test",
        )

        with patch.object(factory, "_run_validation_gate") as mock_gate, \
             patch.object(factory, "_create_github_pr") as mock_pr, \
             patch.object(factory, "_commit_changes"):
            mock_gate.return_value = PRValidationGate(
                py_compile_passed=True,
                type_divergence_passed=True,
                instance_leak_passed=True,
                dependency_direction_passed=True,
            )
            mock_pr.return_value = ("", 0)
            result = factory.create_pr(req)

        assert result.success
        manifest_dir = os.path.join(tmp_dir, "manifests")
        manifests = [f for f in os.listdir(manifest_dir) if f.endswith(".json")]
        assert len(manifests) >= 1

        loaded = ChangeSetManifest.load(
            os.path.join(manifest_dir, manifests[0])
        )
        assert loaded.candidate_id == sample_candidate.candidate_id
        assert loaded.manifest_id != ""

    @patch("substrate.organism.worktree_sandbox._run_git")
    def test_parallel_candidates_non_overlapping(
        self, mock_git, sandbox_manager, sample_candidate, sample_candidate_b
    ):
        mock_git.return_value = MagicMock(returncode=0, stdout="abc\n", stderr="")
        detector = CandidateConflictDetector(sandbox_manager)
        dry = detector.parallel_dry_run([sample_candidate, sample_candidate_b])
        assert dry["parallelizable_pairs"] == 1

        sb_a = sandbox_manager.create_sandbox(
            sample_candidate.candidate_id,
            "test-a",
            affected_files=sample_candidate.affected_files,
        )
        conflicts = sandbox_manager.check_file_conflicts(sample_candidate_b.affected_files)
        assert conflicts == []

        sb_b = sandbox_manager.create_sandbox(
            sample_candidate_b.candidate_id,
            "test-b",
            affected_files=sample_candidate_b.affected_files,
        )
        assert len(sandbox_manager.active_sandboxes) == 2

    @patch("substrate.organism.worktree_sandbox._run_git")
    def test_factory_persists_results(
        self, mock_git, sandbox_manager, tmp_dir, sample_candidate
    ):
        mock_git.return_value = MagicMock(
            returncode=0, stdout="abc123\n", stderr=""
        )

        factory = AutonomousPRFactory(
            sandbox_manager=sandbox_manager,
            store_dir=tmp_dir,
        )

        req = AutonomousPRRequest(
            candidate=sample_candidate,
            candidate_slug="persist-test",
        )

        with patch.object(factory, "_run_validation_gate") as mock_gate, \
             patch.object(factory, "_create_github_pr") as mock_pr, \
             patch.object(factory, "_commit_changes"):
            mock_gate.return_value = PRValidationGate(
                py_compile_passed=True,
                type_divergence_passed=True,
                instance_leak_passed=True,
                dependency_direction_passed=True,
            )
            mock_pr.return_value = ("", 0)
            factory.create_pr(req)

        results_path = os.path.join(tmp_dir, "pr_factory_results.jsonl")
        assert os.path.isfile(results_path)
        with open(results_path) as f:
            lines = f.readlines()
        assert len(lines) >= 1
        data = json.loads(lines[0])
        assert data["success"] is True
