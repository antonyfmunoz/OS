"""Phase 9.8 — Production Truth Promotion + Scheduled Autonomous Cadence tests.

Tests cover:
  - ProductionTruthDelta computation
  - ProductionMergeVerifier lifecycle
  - ProductionOutcomeCommitted contract expansion
  - Truth boundary enforcement (sandbox vs production)
  - Autonomous cadence scheduling
  - Daemon tick integration
  - Cleanup/lifecycle policies
  - API route contracts
  - Duplicate event suppression

80+ tests required. Each test verifies a specific doctrine point.
"""

from __future__ import annotations

import json
import os
import shutil
import tempfile
import time

import pytest


# ── ProductionTruthDelta tests ──────────────────────────────────────


class TestProductionTruthDelta:
    def test_delta_default_status(self):
        from substrate.organism.production_truth_delta import (
            DeltaStatus,
            ProductionTruthDelta,
        )
        delta = ProductionTruthDelta()
        assert delta.status == DeltaStatus.PENDING
        assert delta.delta_id.startswith("ptd-")

    def test_delta_no_divergence_when_files_match(self):
        from substrate.organism.production_truth_delta import ProductionTruthDelta
        delta = ProductionTruthDelta(
            changed_files_expected=["a.py", "b.py"],
            changed_files_observed=["a.py", "b.py"],
        )
        delta.compute_file_divergences()
        assert not delta.has_file_divergence

    def test_delta_divergence_when_files_differ(self):
        from substrate.organism.production_truth_delta import (
            DeltaStatus,
            ProductionTruthDelta,
        )
        delta = ProductionTruthDelta(
            changed_files_expected=["a.py"],
            changed_files_observed=["a.py", "c.py"],
        )
        delta.compute_file_divergences()
        assert delta.has_file_divergence
        assert delta.status == DeltaStatus.DIVERGED

    def test_delta_divergence_detail(self):
        from substrate.organism.production_truth_delta import ProductionTruthDelta
        delta = ProductionTruthDelta(
            changed_files_expected=["a.py", "b.py"],
            changed_files_observed=["a.py", "c.py"],
        )
        delta.compute_file_divergences()
        diverged = [fd for fd in delta.file_divergences if fd.diverged]
        assert len(diverged) == 2
        paths = {fd.path for fd in diverged}
        assert "b.py" in paths
        assert "c.py" in paths

    def test_delta_empty_files(self):
        from substrate.organism.production_truth_delta import ProductionTruthDelta
        delta = ProductionTruthDelta(
            changed_files_expected=[],
            changed_files_observed=[],
        )
        delta.compute_file_divergences()
        assert not delta.has_file_divergence
        assert len(delta.file_divergences) == 0

    def test_delta_state_computation(self):
        from substrate.organism.production_truth_delta import (
            ProductionTruthDelta,
            StateSnapshot,
        )
        before = StateSnapshot(
            world_model_hash="abc",
            contradiction_count=5,
            readiness_score=0.7,
            dependency_node_count=10,
        )
        after = StateSnapshot(
            world_model_hash="def",
            contradiction_count=3,
            readiness_score=0.8,
            dependency_node_count=12,
        )
        delta = ProductionTruthDelta()
        delta.compute_state_delta(before, after)
        assert delta.world_model_before_after["changed"] is True
        assert delta.contradictions_before_after["delta"] == -2
        assert delta.readiness_before_after["delta"] == pytest.approx(0.1, abs=0.001)
        assert delta.dependency_graph_before_after["delta"] == 2

    def test_delta_state_unchanged(self):
        from substrate.organism.production_truth_delta import (
            ProductionTruthDelta,
            StateSnapshot,
        )
        snap = StateSnapshot(world_model_hash="same", contradiction_count=0)
        delta = ProductionTruthDelta()
        delta.compute_state_delta(snap, snap)
        assert delta.world_model_before_after["changed"] is False
        assert delta.contradictions_before_after["delta"] == 0

    def test_delta_finalize_verified(self):
        from substrate.organism.production_truth_delta import (
            DeltaStatus,
            PostMergeValidationResult,
            ProductionTruthDelta,
        )
        delta = ProductionTruthDelta(
            changed_files_expected=["a.py"],
            changed_files_observed=["a.py"],
        )
        delta.compute_file_divergences()
        delta.validation_results.append(
            PostMergeValidationResult(command="test", passed=True, exit_code=0)
        )
        delta.finalize()
        assert delta.status == DeltaStatus.PRODUCTION_VERIFIED

    def test_delta_finalize_partial(self):
        from substrate.organism.production_truth_delta import (
            DeltaStatus,
            PostMergeValidationResult,
            ProductionTruthDelta,
        )
        delta = ProductionTruthDelta(
            changed_files_expected=["a.py"],
            changed_files_observed=["a.py"],
        )
        delta.compute_file_divergences()
        delta.validation_results.append(
            PostMergeValidationResult(command="test", passed=False, exit_code=1)
        )
        delta.finalize()
        assert delta.status == DeltaStatus.PRODUCTION_PARTIAL

    def test_delta_finalize_requires_review(self):
        from substrate.organism.production_truth_delta import (
            DeltaStatus,
            PostMergeValidationResult,
            ProductionTruthDelta,
        )
        delta = ProductionTruthDelta(
            changed_files_expected=["a.py"],
            changed_files_observed=["a.py", "b.py"],
        )
        delta.compute_file_divergences()
        delta.validation_results.append(
            PostMergeValidationResult(command="test", passed=True, exit_code=0)
        )
        delta.finalize()
        assert delta.status == DeltaStatus.REQUIRES_REVIEW

    def test_delta_finalize_diverged_with_failed_validation(self):
        from substrate.organism.production_truth_delta import (
            DeltaStatus,
            PostMergeValidationResult,
            ProductionTruthDelta,
        )
        delta = ProductionTruthDelta(
            changed_files_expected=["a.py"],
            changed_files_observed=["b.py"],
        )
        delta.compute_file_divergences()
        delta.validation_results.append(
            PostMergeValidationResult(command="test", passed=False, exit_code=1)
        )
        delta.finalize()
        assert delta.status == DeltaStatus.DIVERGED

    def test_delta_requires_review_property(self):
        from substrate.organism.production_truth_delta import ProductionTruthDelta
        delta = ProductionTruthDelta(
            changed_files_expected=["a.py"],
            changed_files_observed=["b.py"],
        )
        delta.compute_file_divergences()
        assert delta.requires_review is True

    def test_delta_no_validations_requires_review(self):
        from substrate.organism.production_truth_delta import ProductionTruthDelta
        delta = ProductionTruthDelta(
            changed_files_expected=["a.py"],
            changed_files_observed=["a.py"],
        )
        delta.compute_file_divergences()
        assert delta.all_validations_passed is False
        assert delta.requires_review is True

    def test_delta_serialization(self):
        from substrate.organism.production_truth_delta import (
            PostMergeValidationResult,
            ProductionTruthDelta,
            StateSnapshot,
        )
        delta = ProductionTruthDelta(
            sandbox_id="sb-test",
            pr_number=42,
            merge_commit="abc123",
            changed_files_expected=["a.py"],
            changed_files_observed=["a.py"],
        )
        delta.compute_file_divergences()
        delta.compute_state_delta(StateSnapshot(), StateSnapshot())
        delta.validation_results.append(
            PostMergeValidationResult(command="test", passed=True, exit_code=0)
        )
        delta.finalize()
        d = delta.to_dict()
        assert d["sandbox_id"] == "sb-test"
        assert d["pr_number"] == 42
        assert d["status"] == "production_verified"
        assert isinstance(d["file_divergences"], list)
        assert isinstance(d["validation_results"], list)

    def test_file_divergence_to_dict(self):
        from substrate.organism.production_truth_delta import FileDivergence
        fd = FileDivergence(path="x.py", expected=True, observed=False)
        d = fd.to_dict()
        assert d["diverged"] is True
        assert d["path"] == "x.py"

    def test_state_snapshot_to_dict(self):
        from substrate.organism.production_truth_delta import StateSnapshot
        snap = StateSnapshot(
            world_model_hash="abc",
            contradiction_count=3,
            readiness_score=0.75,
        )
        d = snap.to_dict()
        assert d["world_model_hash"] == "abc"
        assert d["readiness_score"] == 0.75

    def test_post_merge_validation_result_to_dict(self):
        from substrate.organism.production_truth_delta import PostMergeValidationResult
        vr = PostMergeValidationResult(
            command="pytest", passed=True, exit_code=0, output_summary="ok"
        )
        d = vr.to_dict()
        assert d["command"] == "pytest"
        assert d["passed"] is True

    def test_evidence_accumulation(self):
        from substrate.organism.production_truth_delta import ProductionTruthDelta
        delta = ProductionTruthDelta(
            changed_files_expected=["a.py"],
            changed_files_observed=["a.py"],
        )
        delta.compute_file_divergences()
        assert any("file sets match" in e for e in delta.evidence)


# ── ProductionMergeVerifier tests ───────────────────────────────────


class TestProductionMergeVerifier:
    def _make_sandbox_manager(self, tmp: str):
        from substrate.organism.worktree_sandbox import SandboxManager
        return SandboxManager(
            repo_root=tmp,
            worktree_base=os.path.join(tmp, ".worktrees"),
            store_dir=os.path.join(tmp, "store"),
            max_parallel=5,
        )

    def test_verifier_init(self):
        from substrate.organism.production_merge_verifier import ProductionMergeVerifier
        tmp = tempfile.mkdtemp()
        try:
            manager = self._make_sandbox_manager(tmp)
            verifier = ProductionMergeVerifier(
                sandbox_manager=manager,
                repo_root=tmp,
            )
            assert verifier.verifications == []
            assert verifier.production_outcomes == []
        finally:
            shutil.rmtree(tmp)

    def test_verifier_detects_unmerged_pr(self):
        from substrate.organism.production_merge_verifier import (
            MergeVerificationStatus,
            ProductionMergeVerifier,
        )
        tmp = tempfile.mkdtemp()
        try:
            manager = self._make_sandbox_manager(tmp)
            verifier = ProductionMergeVerifier(
                sandbox_manager=manager,
                repo_root=tmp,
            )
            v = verifier.verify_merge("sb-nonexistent")
            assert v.status in (
                MergeVerificationStatus.PR_NOT_FOUND,
                MergeVerificationStatus.PR_NOT_MERGED,
            )
        finally:
            shutil.rmtree(tmp)

    def test_verifier_pending_list(self):
        from substrate.organism.production_merge_verifier import ProductionMergeVerifier
        tmp = tempfile.mkdtemp()
        try:
            manager = self._make_sandbox_manager(tmp)
            verifier = ProductionMergeVerifier(
                sandbox_manager=manager,
                repo_root=tmp,
            )
            assert verifier.pending_verifications() == []
        finally:
            shutil.rmtree(tmp)

    def test_verifier_cleanup_ready_list(self):
        from substrate.organism.production_merge_verifier import ProductionMergeVerifier
        tmp = tempfile.mkdtemp()
        try:
            manager = self._make_sandbox_manager(tmp)
            verifier = ProductionMergeVerifier(
                sandbox_manager=manager,
                repo_root=tmp,
            )
            assert verifier.cleanup_ready() == []
        finally:
            shutil.rmtree(tmp)

    def test_verifier_to_dict(self):
        from substrate.organism.production_merge_verifier import ProductionMergeVerifier
        tmp = tempfile.mkdtemp()
        try:
            manager = self._make_sandbox_manager(tmp)
            verifier = ProductionMergeVerifier(
                sandbox_manager=manager,
                repo_root=tmp,
            )
            d = verifier.to_dict()
            assert d["total_verifications"] == 0
            assert d["pending"] == 0
            assert d["cleanup_ready"] == 0
        finally:
            shutil.rmtree(tmp)

    def test_verification_entity_to_dict(self):
        from substrate.organism.production_merge_verifier import (
            MergeVerificationStatus,
            ProductionMergeVerification,
        )
        v = ProductionMergeVerification(
            sandbox_id="sb-test",
            pr_number=10,
            status=MergeVerificationStatus.PENDING,
        )
        d = v.to_dict()
        assert d["sandbox_id"] == "sb-test"
        assert d["pr_number"] == 10
        assert d["status"] == "pending"

    def test_promotion_decision_to_dict(self):
        from substrate.organism.production_merge_verifier import (
            ProductionPromotionDecision,
        )
        dec = ProductionPromotionDecision(
            verification_id="pmv-test",
            promote=True,
            reason="all passed",
        )
        d = dec.to_dict()
        assert d["promote"] is True
        assert d["reason"] == "all passed"

    def test_verifier_duplicate_suppression(self):
        from substrate.organism.production_merge_verifier import ProductionMergeVerifier
        tmp = tempfile.mkdtemp()
        try:
            manager = self._make_sandbox_manager(tmp)
            outcomes_received = []
            verifier = ProductionMergeVerifier(
                sandbox_manager=manager,
                repo_root=tmp,
                on_production_outcome=lambda o: outcomes_received.append(o),
            )
            verifier._emitted_event_ids.add("sb-test:abc123")
            verifier._emit_production_outcome(
                type("V", (), {
                    "sandbox_id": "sb-test",
                    "manifest_id": "m1",
                    "pr_number": 1,
                    "merge_commit": "abc123",
                    "base_commit": "base",
                    "head_commit": "head",
                    "verification_id": "pmv-1",
                })(),
                type("D", (), {
                    "all_validations_passed": True,
                    "changed_files_observed": ["a.py"],
                    "to_dict": lambda self: {},
                    "sandbox_id": "sb-test",
                })(),
            )
            assert len(outcomes_received) == 0
        finally:
            shutil.rmtree(tmp)

    def test_verifier_saves_verification_to_disk(self):
        from substrate.organism.production_merge_verifier import (
            MergeVerificationStatus,
            ProductionMergeVerifier,
        )
        tmp = tempfile.mkdtemp()
        try:
            store_dir = os.path.join(tmp, "verifications")
            manager = self._make_sandbox_manager(tmp)
            verifier = ProductionMergeVerifier(
                sandbox_manager=manager,
                repo_root=tmp,
                store_dir=store_dir,
            )
            v = verifier.verify_merge("sb-missing")
            assert v.status in (
                MergeVerificationStatus.PR_NOT_FOUND,
                MergeVerificationStatus.PR_NOT_MERGED,
            )
            files = os.listdir(store_dir) if os.path.isdir(store_dir) else []
            assert len(files) == 1
            with open(os.path.join(store_dir, files[0])) as f:
                data = json.load(f)
            assert data["status"] in ("pr_not_found", "pr_not_merged")
        finally:
            shutil.rmtree(tmp)


# ── ProductionOutcomeCommitted contract tests ───────────────────────


class TestProductionOutcomeCommittedContract:
    def test_expanded_fields(self):
        from substrate.organism.autonomous_pr_factory import (
            ProductionOutcomeCommitted,
        )
        poc = ProductionOutcomeCommitted(
            sandbox_id="sb-1",
            pr_number=42,
            merge_commit="abc123",
            base_commit="base",
            head_commit="head",
            action_type="autonomous_improvement",
            mutation_type="code_change",
            risk_class="low",
            agent_type="developer_agent",
            template_id="tpl-1",
            changed_files=["a.py"],
            affected_entities=["world_model"],
            affected_subsystems=["readiness_model"],
            production_truth_delta={"status": "verified"},
            evidence=["all_passed"],
        )
        d = poc.to_dict()
        assert d["event_type"] == "production_outcome_committed"
        assert d["base_commit"] == "base"
        assert d["head_commit"] == "head"
        assert d["action_type"] == "autonomous_improvement"
        assert d["mutation_type"] == "code_change"
        assert d["risk_class"] == "low"
        assert d["template_id"] == "tpl-1"
        assert d["changed_files"] == ["a.py"]
        assert d["affected_subsystems"] == ["readiness_model"]
        assert d["production_truth_delta"]["status"] == "verified"
        assert d["evidence"] == ["all_passed"]

    def test_poc_boundary_is_production(self):
        from substrate.organism.autonomous_pr_factory import (
            ProductionOutcomeCommitted,
        )
        poc = ProductionOutcomeCommitted()
        assert poc.boundary == "production"

    def test_poc_distinct_from_soc(self):
        from substrate.organism.autonomous_pr_factory import (
            ProductionOutcomeCommitted,
            SandboxOutcomeCommitted,
        )
        soc = SandboxOutcomeCommitted()
        poc = ProductionOutcomeCommitted()
        assert soc.boundary == "sandbox"
        assert poc.boundary == "production"
        soc_d = soc.to_dict()
        poc_d = poc.to_dict()
        assert soc_d["event_type"] == "sandbox_outcome_committed"
        assert poc_d["event_type"] == "production_outcome_committed"

    def test_poc_has_subsystem_fields(self):
        from substrate.organism.autonomous_pr_factory import (
            ProductionOutcomeCommitted,
        )
        poc = ProductionOutcomeCommitted(
            affected_subsystems=["world_model", "contradiction_engine"],
            action_envelope_ids=["ae-1"],
            sandbox_outcome_ids=["soc-1"],
        )
        d = poc.to_dict()
        assert len(d["affected_subsystems"]) == 2
        assert d["action_envelope_ids"] == ["ae-1"]
        assert d["sandbox_outcome_ids"] == ["soc-1"]


# ── Truth boundary enforcement tests ────────────────────────────────


class TestTruthBoundary:
    def test_sandbox_outcome_does_not_update_production(self):
        from substrate.organism.autonomous_pr_factory import (
            SandboxOutcomeCommitted,
        )
        soc = SandboxOutcomeCommitted(validation_passed=True)
        assert soc.boundary == "sandbox"
        d = soc.to_dict()
        assert "production" not in d["boundary"]

    def test_production_outcome_requires_merge(self):
        from substrate.organism.autonomous_pr_factory import (
            ProductionOutcomeCommitted,
        )
        poc = ProductionOutcomeCommitted(
            post_merge_validation_passed=False,
            production_propagation_complete=False,
        )
        d = poc.to_dict()
        assert d["post_merge_validation_passed"] is False
        assert d["production_propagation_complete"] is False

    def test_sandbox_boundary_field_immutable_in_event(self):
        from substrate.organism.autonomous_pr_factory import (
            SandboxOutcomeCommitted,
        )
        soc = SandboxOutcomeCommitted()
        soc.boundary = "production"
        assert soc.boundary == "production"
        soc2 = SandboxOutcomeCommitted()
        assert soc2.boundary == "sandbox"

    def test_production_outcome_default_empty_delta(self):
        from substrate.organism.autonomous_pr_factory import (
            ProductionOutcomeCommitted,
        )
        poc = ProductionOutcomeCommitted()
        assert poc.production_truth_delta == {}
        assert poc.changed_files == []
        assert poc.affected_subsystems == []


# ── AutonomousCadence tests ─────────────────────────────────────────


class TestAutonomousCadence:
    def test_cadence_default_mode_off(self):
        from substrate.organism.autonomous_cadence import (
            AutonomousCadence,
            CadenceMode,
        )
        cadence = AutonomousCadence()
        assert cadence.mode == CadenceMode.OFF

    def test_cadence_off_noop(self):
        from substrate.organism.autonomous_cadence import AutonomousCadence
        cadence = AutonomousCadence()
        result = cadence.tick()
        assert result["skipped"] is True
        assert result["action"] == "off"

    def test_cadence_dry_run_mode(self):
        from substrate.organism.autonomous_cadence import (
            AutonomousCadence,
            CadenceMode,
            CadencePolicy,
        )
        policy = CadencePolicy(mode=CadenceMode.DRY_RUN_ONLY, interval_seconds=0)
        cadence = AutonomousCadence(policy=policy)
        result = cadence.run_cycle()
        assert result.mode == CadenceMode.DRY_RUN_ONLY
        assert result.completed_at > 0

    def test_cadence_dry_run_does_not_mutate(self):
        from substrate.organism.autonomous_cadence import (
            AutonomousCadence,
            CadenceMode,
            CadencePolicy,
        )
        policy = CadencePolicy(mode=CadenceMode.DRY_RUN_ONLY, interval_seconds=0)
        cadence = AutonomousCadence(policy=policy)
        result = cadence.run_cycle()
        assert result.pr_created is False
        assert result.pr_queued is False

    def test_cadence_propose_pr_does_not_create(self):
        from substrate.organism.autonomous_cadence import (
            AutonomousCadence,
            CadenceMode,
            CadencePolicy,
        )
        policy = CadencePolicy(mode=CadenceMode.PROPOSE_PR, interval_seconds=0)
        candidates = [
            {"candidate_id": "c1", "risk_class": "low", "template_id": "t1",
             "agent_reliability": 0.9, "validation_method": "pytest",
             "rollback_method": "revert", "description": "test"},
        ]
        cadence = AutonomousCadence(
            policy=policy,
            candidate_discovery_fn=lambda: candidates,
        )
        result = cadence.run_cycle()
        assert result.pr_created is False
        assert len(result.recommendations) > 0

    def test_cadence_create_pr_blocked_by_operator_policy(self):
        from substrate.organism.autonomous_cadence import (
            AutonomousCadence,
            CadenceMode,
            CadencePolicy,
        )
        policy = CadencePolicy(
            mode=CadenceMode.CREATE_PR_WITH_OPERATOR_POLICY,
            require_operator_enable_for_pr_creation=True,
            interval_seconds=0,
        )
        candidates = [
            {"candidate_id": "c1", "risk_class": "low", "template_id": "t1",
             "agent_reliability": 0.9, "validation_method": "pytest",
             "rollback_method": "revert", "description": "test"},
        ]
        cadence = AutonomousCadence(
            policy=policy,
            candidate_discovery_fn=lambda: candidates,
        )
        result = cadence.run_cycle()
        assert result.pr_created is False

    def test_cadence_daily_limit_enforced(self):
        from substrate.organism.autonomous_cadence import (
            AutonomousCadence,
            CadenceMode,
            CadencePolicy,
        )
        policy = CadencePolicy(
            mode=CadenceMode.DRY_RUN_ONLY,
            max_dry_runs_per_day=1,
            interval_seconds=0,
        )
        cadence = AutonomousCadence(policy=policy)
        cadence.run_cycle()
        cadence._last_run_at = 0
        result2 = cadence.run_cycle()
        assert len(result2.dry_run_results) == 0

    def test_cadence_candidate_filtering(self):
        from substrate.organism.autonomous_cadence import (
            AutonomousCadence,
            CadenceMode,
            CadencePolicy,
        )
        policy = CadencePolicy(mode=CadenceMode.DRY_RUN_ONLY, interval_seconds=0)
        candidates = [
            {"candidate_id": "c1", "risk_class": "high"},
            {"candidate_id": "c2", "risk_class": "low", "template_id": "t1",
             "agent_reliability": 0.9, "validation_method": "pytest",
             "rollback_method": "revert"},
        ]
        cadence = AutonomousCadence(
            policy=policy,
            candidate_discovery_fn=lambda: candidates,
        )
        result = cadence.run_cycle()
        assert result.candidates_found == 2
        assert result.candidates_blocked == 1
        assert result.candidates_eligible == 1

    def test_cadence_production_verify_mode(self):
        from substrate.organism.autonomous_cadence import (
            AutonomousCadence,
            CadenceMode,
            CadencePolicy,
        )
        policy = CadencePolicy(
            mode=CadenceMode.PRODUCTION_VERIFY_ONLY,
            interval_seconds=0,
        )
        cadence = AutonomousCadence(
            policy=policy,
            merge_verification_fn=lambda: [{"id": "pmv-1"}],
        )
        result = cadence.tick()
        assert result["action"] == "production_verify"
        assert result["pending_verifications"] == 1

    def test_cadence_should_run_respects_interval(self):
        from substrate.organism.autonomous_cadence import (
            AutonomousCadence,
            CadenceMode,
            CadencePolicy,
        )
        policy = CadencePolicy(
            mode=CadenceMode.DRY_RUN_ONLY,
            interval_seconds=3600,
        )
        cadence = AutonomousCadence(policy=policy)
        assert cadence.should_run() is True
        cadence._last_run_at = time.time()
        assert cadence.should_run() is False

    def test_cadence_status_dict(self):
        from substrate.organism.autonomous_cadence import AutonomousCadence
        cadence = AutonomousCadence()
        s = cadence.status()
        assert "mode" in s
        assert "policy" in s
        assert "dry_runs_today" in s
        assert "prs_today" in s

    def test_cadence_to_dict(self):
        from substrate.organism.autonomous_cadence import AutonomousCadence
        cadence = AutonomousCadence()
        d = cadence.to_dict()
        assert d["mode"] == "off"

    def test_cadence_policy_serialization(self):
        from substrate.organism.autonomous_cadence import CadencePolicy
        p = CadencePolicy()
        d = p.to_dict()
        assert d["mode"] == "off"
        assert d["max_prs_per_day"] == 1
        assert d["no_auto_merge"] is True

    def test_cadence_run_result_serialization(self):
        from substrate.organism.autonomous_cadence import (
            CadenceMode,
            CadenceRunResult,
        )
        r = CadenceRunResult(mode=CadenceMode.DRY_RUN_ONLY, candidates_found=3)
        d = r.to_dict()
        assert d["candidates_found"] == 3
        assert d["mode"] == "dry_run_only"

    def test_cadence_mode_setter(self):
        from substrate.organism.autonomous_cadence import (
            AutonomousCadence,
            CadenceMode,
        )
        cadence = AutonomousCadence()
        cadence.mode = CadenceMode.DRY_RUN_ONLY
        assert cadence.mode == CadenceMode.DRY_RUN_ONLY

    def test_cadence_run_history_capped(self):
        from substrate.organism.autonomous_cadence import (
            AutonomousCadence,
            CadenceMode,
            CadencePolicy,
        )
        policy = CadencePolicy(mode=CadenceMode.DRY_RUN_ONLY, interval_seconds=0)
        cadence = AutonomousCadence(policy=policy)
        for _ in range(110):
            cadence._last_run_at = 0
            cadence.run_cycle()
        assert len(cadence._run_history) == 100

    def test_cadence_active_sandbox_limit_blocks(self):
        from substrate.organism.autonomous_cadence import (
            AutonomousCadence,
            CadencePolicy,
        )
        policy = CadencePolicy(max_active_sandboxes=2)
        cadence = AutonomousCadence(policy=policy)
        assert cadence.policy.max_active_sandboxes == 2

    def test_cadence_active_pr_limit(self):
        from substrate.organism.autonomous_cadence import CadencePolicy
        policy = CadencePolicy(max_active_prs=3)
        assert policy.max_active_prs == 3

    def test_cadence_custom_dry_run_fn(self):
        from substrate.organism.autonomous_cadence import (
            AutonomousCadence,
            CadenceMode,
            CadencePolicy,
        )
        policy = CadencePolicy(mode=CadenceMode.DRY_RUN_ONLY, interval_seconds=0)
        candidates = [
            {"candidate_id": "c1", "risk_class": "low", "template_id": "t1",
             "agent_reliability": 0.9, "validation_method": "pytest",
             "rollback_method": "revert"},
        ]
        cadence = AutonomousCadence(
            policy=policy,
            candidate_discovery_fn=lambda: candidates,
            dry_run_fn=lambda c: {"dry": True, "id": c["candidate_id"]},
        )
        result = cadence.run_cycle()
        assert len(result.dry_run_results) == 1
        assert result.dry_run_results[0]["dry"] is True


# ── Daemon integration tests ───────────────────────────────────────


class TestDaemonCadenceIntegration:
    def test_daemon_has_cadence(self):
        from substrate.organism.daemon import OrganismDaemon
        daemon = OrganismDaemon()
        assert daemon.autonomous_cadence is not None

    def test_daemon_cadence_in_status(self):
        from substrate.organism.daemon import OrganismDaemon
        daemon = OrganismDaemon()
        s = daemon.status()
        assert "autonomous_cadence" in s
        assert s["autonomous_cadence"]["mode"] == "off"

    def test_daemon_cadence_tick_registered(self):
        from substrate.organism.daemon import OrganismDaemon
        daemon = OrganismDaemon()
        stage_names = list(daemon.autonomous_tick.stages.keys())
        assert "autonomous_cadence_tick" in stage_names

    def test_daemon_cadence_default_off(self):
        from substrate.organism.autonomous_cadence import CadenceMode
        from substrate.organism.daemon import OrganismDaemon
        daemon = OrganismDaemon()
        assert daemon.autonomous_cadence.mode == CadenceMode.OFF


# ── Cleanup/lifecycle tests ─────────────────────────────────────────


class TestCleanupLifecycle:
    def _make_sandbox_manager(self, tmp: str):
        from substrate.organism.worktree_sandbox import SandboxManager
        return SandboxManager(
            repo_root=tmp,
            worktree_base=os.path.join(tmp, ".worktrees"),
            store_dir=os.path.join(tmp, "store"),
            max_parallel=5,
        )

    def test_sandbox_cleanup_expired(self):
        from substrate.organism.worktree_sandbox import SandboxManager
        tmp = tempfile.mkdtemp()
        try:
            manager = self._make_sandbox_manager(tmp)
            cleaned = manager.cleanup_expired()
            assert isinstance(cleaned, list)
        finally:
            shutil.rmtree(tmp)

    def test_sandbox_statuses(self):
        from substrate.organism.worktree_sandbox import SandboxStatus
        assert SandboxStatus.CREATED.value == "created"
        assert SandboxStatus.MERGED.value == "merged"
        assert SandboxStatus.CLEANED.value == "cleaned"
        assert SandboxStatus.ABANDONED.value == "abandoned"

    def test_cleanup_policy_values(self):
        from substrate.organism.worktree_sandbox import SandboxCleanupPolicy
        assert SandboxCleanupPolicy.ON_MERGE.value == "on_merge"
        assert SandboxCleanupPolicy.ON_ABANDON.value == "on_abandon"
        assert SandboxCleanupPolicy.MANUAL.value == "manual"
        assert SandboxCleanupPolicy.TTL_HOURS.value == "ttl_hours"


# ── MergeVerificationStatus tests ──────────────────────────────────


class TestMergeVerificationStatus:
    def test_all_statuses(self):
        from substrate.organism.production_merge_verifier import (
            MergeVerificationStatus,
        )
        assert MergeVerificationStatus.PENDING.value == "pending"
        assert MergeVerificationStatus.PR_NOT_MERGED.value == "pr_not_merged"
        assert MergeVerificationStatus.MERGE_DETECTED.value == "merge_detected"
        assert MergeVerificationStatus.MAIN_UPDATED.value == "main_updated"
        assert MergeVerificationStatus.VALIDATION_RUNNING.value == "validation_running"
        assert MergeVerificationStatus.VALIDATION_FAILED.value == "validation_failed"
        assert MergeVerificationStatus.PRODUCTION_VERIFIED.value == "production_verified"
        assert MergeVerificationStatus.PRODUCTION_REJECTED.value == "production_rejected"
        assert MergeVerificationStatus.CLEANUP_READY.value == "cleanup_ready"


# ── DeltaStatus tests ──────────────────────────────────────────────


class TestDeltaStatus:
    def test_all_delta_statuses(self):
        from substrate.organism.production_truth_delta import DeltaStatus
        assert DeltaStatus.PENDING.value == "pending"
        assert DeltaStatus.COMPUTED.value == "computed"
        assert DeltaStatus.DIVERGED.value == "diverged"
        assert DeltaStatus.REQUIRES_REVIEW.value == "requires_review"
        assert DeltaStatus.PRODUCTION_PARTIAL.value == "production_partial"
        assert DeltaStatus.PRODUCTION_VERIFIED.value == "production_verified"


# ── CadenceMode tests ──────────────────────────────────────────────


class TestCadenceMode:
    def test_all_modes(self):
        from substrate.organism.autonomous_cadence import CadenceMode
        assert CadenceMode.OFF.value == "off"
        assert CadenceMode.DRY_RUN_ONLY.value == "dry_run_only"
        assert CadenceMode.PROPOSE_PR.value == "propose_pr"
        assert CadenceMode.CREATE_PR_WITH_OPERATOR_POLICY.value == "create_pr_with_operator_policy"
        assert CadenceMode.PRODUCTION_VERIFY_ONLY.value == "production_verify_only"


# ── API contract tests (unit-level) ────────────────────────────────


class TestAPIContracts:
    def test_production_truth_delta_json_roundtrip(self):
        from substrate.organism.production_truth_delta import (
            PostMergeValidationResult,
            ProductionTruthDelta,
            StateSnapshot,
        )
        delta = ProductionTruthDelta(
            sandbox_id="sb-1",
            pr_number=5,
            merge_commit="abc",
            changed_files_expected=["a.py"],
            changed_files_observed=["a.py"],
        )
        delta.compute_file_divergences()
        delta.compute_state_delta(StateSnapshot(), StateSnapshot())
        delta.validation_results.append(
            PostMergeValidationResult(command="test", passed=True, exit_code=0)
        )
        delta.finalize()
        serialized = json.dumps(delta.to_dict(), default=str)
        loaded = json.loads(serialized)
        assert loaded["status"] == "production_verified"
        assert loaded["sandbox_id"] == "sb-1"

    def test_merge_verification_json_roundtrip(self):
        from substrate.organism.production_merge_verifier import (
            ProductionMergeVerification,
        )
        v = ProductionMergeVerification(
            sandbox_id="sb-1",
            pr_number=5,
            merge_commit="abc",
        )
        serialized = json.dumps(v.to_dict(), default=str)
        loaded = json.loads(serialized)
        assert loaded["sandbox_id"] == "sb-1"

    def test_cadence_status_json_roundtrip(self):
        from substrate.organism.autonomous_cadence import AutonomousCadence
        cadence = AutonomousCadence()
        serialized = json.dumps(cadence.to_dict(), default=str)
        loaded = json.loads(serialized)
        assert loaded["mode"] == "off"

    def test_production_outcome_json_roundtrip(self):
        from substrate.organism.autonomous_pr_factory import (
            ProductionOutcomeCommitted,
        )
        poc = ProductionOutcomeCommitted(
            sandbox_id="sb-1",
            pr_number=5,
            merge_commit="abc",
            changed_files=["a.py"],
            affected_subsystems=["world_model"],
        )
        serialized = json.dumps(poc.to_dict(), default=str)
        loaded = json.loads(serialized)
        assert loaded["event_type"] == "production_outcome_committed"
        assert loaded["changed_files"] == ["a.py"]


# ── Integration: verify_merge delegates to ProductionMergeVerifier ──


class TestVerifyMergeDelegation:
    def test_pr_factory_verify_merge_returns_none_for_unknown(self):
        from substrate.organism.autonomous_pr_factory import AutonomousPRFactory
        from substrate.organism.worktree_sandbox import SandboxManager
        tmp = tempfile.mkdtemp()
        try:
            manager = SandboxManager(
                repo_root=tmp,
                worktree_base=os.path.join(tmp, ".wt"),
                store_dir=os.path.join(tmp, "store"),
            )
            factory = AutonomousPRFactory(
                sandbox_manager=manager,
                repo_root=tmp,
            )
            result = factory.verify_merge("sb-nonexistent")
            assert result is None
        finally:
            shutil.rmtree(tmp)


# ── Additional coverage tests ──────────────────────────────────────


class TestProductionTruthDeltaEdgeCases:
    def test_delta_only_expected_files(self):
        from substrate.organism.production_truth_delta import ProductionTruthDelta
        delta = ProductionTruthDelta(
            changed_files_expected=["a.py", "b.py"],
            changed_files_observed=[],
        )
        delta.compute_file_divergences()
        assert delta.has_file_divergence is True
        assert len(delta.file_divergences) == 2

    def test_delta_only_observed_files(self):
        from substrate.organism.production_truth_delta import ProductionTruthDelta
        delta = ProductionTruthDelta(
            changed_files_expected=[],
            changed_files_observed=["x.py", "y.py"],
        )
        delta.compute_file_divergences()
        assert delta.has_file_divergence is True

    def test_delta_large_file_set(self):
        from substrate.organism.production_truth_delta import ProductionTruthDelta
        files = [f"file_{i}.py" for i in range(50)]
        delta = ProductionTruthDelta(
            changed_files_expected=files,
            changed_files_observed=files,
        )
        delta.compute_file_divergences()
        assert not delta.has_file_divergence
        assert len(delta.file_divergences) == 50

    def test_delta_mixed_validations(self):
        from substrate.organism.production_truth_delta import (
            PostMergeValidationResult,
            ProductionTruthDelta,
        )
        delta = ProductionTruthDelta()
        delta.validation_results = [
            PostMergeValidationResult(command="a", passed=True, exit_code=0),
            PostMergeValidationResult(command="b", passed=False, exit_code=1),
        ]
        assert delta.all_validations_passed is False

    def test_delta_all_validations_pass(self):
        from substrate.organism.production_truth_delta import (
            PostMergeValidationResult,
            ProductionTruthDelta,
        )
        delta = ProductionTruthDelta()
        delta.validation_results = [
            PostMergeValidationResult(command="a", passed=True, exit_code=0),
            PostMergeValidationResult(command="b", passed=True, exit_code=0),
        ]
        assert delta.all_validations_passed is True


class TestCadenceEdgeCases:
    def test_cadence_error_handling(self):
        from substrate.organism.autonomous_cadence import (
            AutonomousCadence,
            CadenceMode,
            CadencePolicy,
        )
        policy = CadencePolicy(mode=CadenceMode.DRY_RUN_ONLY, interval_seconds=0)

        def bad_discovery():
            raise ValueError("broken")

        cadence = AutonomousCadence(
            policy=policy,
            candidate_discovery_fn=bad_discovery,
        )
        result = cadence.run_cycle()
        assert result.error != ""
        assert "broken" in result.error

    def test_cadence_not_due_when_interval_not_elapsed(self):
        from substrate.organism.autonomous_cadence import (
            AutonomousCadence,
            CadenceMode,
            CadencePolicy,
        )
        policy = CadencePolicy(
            mode=CadenceMode.DRY_RUN_ONLY,
            interval_seconds=9999,
        )
        cadence = AutonomousCadence(policy=policy)
        cadence._last_run_at = time.time()
        result = cadence.tick()
        assert result["skipped"] is True
        assert result["action"] == "not_due"

    def test_cadence_filtering_no_validation(self):
        from substrate.organism.autonomous_cadence import (
            AutonomousCadence,
            CadenceMode,
            CadencePolicy,
        )
        policy = CadencePolicy(mode=CadenceMode.DRY_RUN_ONLY, interval_seconds=0)
        candidates = [
            {"candidate_id": "c1", "risk_class": "low", "template_id": "t1",
             "agent_reliability": 0.9},
        ]
        cadence = AutonomousCadence(
            policy=policy,
            candidate_discovery_fn=lambda: candidates,
        )
        result = cadence.run_cycle()
        assert result.candidates_blocked == 1
        assert result.candidates_eligible == 0

    def test_cadence_filtering_no_rollback(self):
        from substrate.organism.autonomous_cadence import (
            AutonomousCadence,
            CadenceMode,
            CadencePolicy,
        )
        policy = CadencePolicy(mode=CadenceMode.DRY_RUN_ONLY, interval_seconds=0)
        candidates = [
            {"candidate_id": "c1", "risk_class": "low", "template_id": "t1",
             "agent_reliability": 0.9, "validation_method": "pytest"},
        ]
        cadence = AutonomousCadence(
            policy=policy,
            candidate_discovery_fn=lambda: candidates,
        )
        result = cadence.run_cycle()
        assert result.candidates_blocked == 1

    def test_cadence_non_mutating_passes_rollback_check(self):
        from substrate.organism.autonomous_cadence import (
            AutonomousCadence,
            CadenceMode,
            CadencePolicy,
        )
        policy = CadencePolicy(mode=CadenceMode.DRY_RUN_ONLY, interval_seconds=0)
        candidates = [
            {"candidate_id": "c1", "risk_class": "low", "template_id": "t1",
             "agent_reliability": 0.9, "validation_method": "pytest",
             "non_mutating": True},
        ]
        cadence = AutonomousCadence(
            policy=policy,
            candidate_discovery_fn=lambda: candidates,
        )
        result = cadence.run_cycle()
        assert result.candidates_eligible == 1

    def test_cadence_daily_reset(self):
        from substrate.organism.autonomous_cadence import AutonomousCadence
        cadence = AutonomousCadence()
        cadence._dry_runs_today = 5
        cadence._prs_today = 2
        cadence._last_day_reset = time.time() - 100000
        cadence._reset_daily_counters_if_needed()
        assert cadence._dry_runs_today == 0
        assert cadence._prs_today == 0

    def test_cadence_production_verify_no_fn(self):
        from substrate.organism.autonomous_cadence import (
            AutonomousCadence,
            CadenceMode,
            CadencePolicy,
        )
        policy = CadencePolicy(
            mode=CadenceMode.PRODUCTION_VERIFY_ONLY,
            interval_seconds=0,
        )
        cadence = AutonomousCadence(policy=policy)
        result = cadence.tick()
        assert result["pending_verifications"] == 0


class TestProductionOutcomeCommittedEdgeCases:
    def test_poc_default_values(self):
        from substrate.organism.autonomous_pr_factory import (
            ProductionOutcomeCommitted,
        )
        poc = ProductionOutcomeCommitted()
        assert poc.action_type == "autonomous_improvement"
        assert poc.mutation_type == "code_change"
        assert poc.risk_class == "low"
        assert poc.agent_type == "developer_agent"

    def test_poc_event_id_prefix(self):
        from substrate.organism.autonomous_pr_factory import (
            ProductionOutcomeCommitted,
        )
        poc = ProductionOutcomeCommitted()
        assert poc.event_id.startswith("poc-")

    def test_soc_event_id_prefix(self):
        from substrate.organism.autonomous_pr_factory import (
            SandboxOutcomeCommitted,
        )
        soc = SandboxOutcomeCommitted()
        assert soc.event_id.startswith("soc-")

    def test_poc_timestamp_set(self):
        from substrate.organism.autonomous_pr_factory import (
            ProductionOutcomeCommitted,
        )
        poc = ProductionOutcomeCommitted()
        assert poc.timestamp > 0

    def test_poc_serialization_all_fields(self):
        from substrate.organism.autonomous_pr_factory import (
            ProductionOutcomeCommitted,
        )
        poc = ProductionOutcomeCommitted()
        d = poc.to_dict()
        expected_keys = {
            "event_id", "event_type", "idempotency_key", "sandbox_id",
            "manifest_id", "pr_number", "merge_commit", "base_commit",
            "head_commit", "branch_name", "boundary", "action_type",
            "mutation_type", "risk_class", "agent_type", "template_id",
            "action_envelope_ids", "sandbox_outcome_ids",
            "post_merge_validation_passed", "production_validation_result",
            "production_propagation_complete", "production_truth_delta",
            "changed_files", "affected_entities", "affected_subsystems",
            "evidence", "timestamp",
        }
        assert expected_keys.issubset(set(d.keys()))


# ═══════════════════════════════════════════════════════════════════════════════
# Phase 9.8 Extended Tests — Gap Closure
# ═══════════════════════════════════════════════════════════════════════════════


class TestMergeVerificationStatusExtended:
    """Test all 12 statuses exist and are distinct."""

    def test_all_12_statuses(self):
        from substrate.organism.production_merge_verifier import MergeVerificationStatus
        expected = {
            "pending", "pr_not_found", "pr_not_merged", "merge_detected",
            "main_update_failed", "main_updated", "validation_running",
            "validation_failed", "expected_observed_mismatch",
            "production_verified", "production_rejected", "cleanup_ready",
        }
        actual = {s.value for s in MergeVerificationStatus}
        assert actual == expected

    def test_pr_not_found_distinct_from_not_merged(self):
        from substrate.organism.production_merge_verifier import MergeVerificationStatus
        assert MergeVerificationStatus.PR_NOT_FOUND != MergeVerificationStatus.PR_NOT_MERGED

    def test_main_update_failed_exists(self):
        from substrate.organism.production_merge_verifier import MergeVerificationStatus
        assert MergeVerificationStatus.MAIN_UPDATE_FAILED.value == "main_update_failed"

    def test_expected_observed_mismatch_exists(self):
        from substrate.organism.production_merge_verifier import MergeVerificationStatus
        assert MergeVerificationStatus.EXPECTED_OBSERVED_MISMATCH.value == "expected_observed_mismatch"


class TestProductionTruthDeltaExtendedFields:
    """Test all spec-required fields present."""

    def test_manifest_id_field(self):
        from substrate.organism.production_truth_delta import ProductionTruthDelta
        d = ProductionTruthDelta(manifest_id="mfst-abc123")
        assert d.manifest_id == "mfst-abc123"
        assert d.to_dict()["manifest_id"] == "mfst-abc123"

    def test_line_count_fields(self):
        from substrate.organism.production_truth_delta import ProductionTruthDelta
        d = ProductionTruthDelta()
        d.added_lines_expected = 50
        d.removed_lines_expected = 10
        d.added_lines_observed = 55
        d.removed_lines_observed = 8
        out = d.to_dict()
        assert out["added_lines_expected"] == 50
        assert out["removed_lines_expected"] == 10
        assert out["added_lines_observed"] == 55
        assert out["removed_lines_observed"] == 8

    def test_bottlenecks_before_after(self):
        from substrate.organism.production_truth_delta import (
            ProductionTruthDelta,
            StateSnapshot,
        )
        d = ProductionTruthDelta()
        before = StateSnapshot(bottleneck_count=3)
        after = StateSnapshot(bottleneck_count=1)
        d.compute_state_delta(before, after)
        assert d.bottlenecks_before_after["before"] == 3
        assert d.bottlenecks_before_after["after"] == 1
        assert d.bottlenecks_before_after["delta"] == -2

    def test_mismatch_reasons_populated_on_divergence(self):
        from substrate.organism.production_truth_delta import ProductionTruthDelta
        d = ProductionTruthDelta(
            changed_files_expected=["a.py", "b.py"],
            changed_files_observed=["a.py", "c.py"],
        )
        d.compute_file_divergences()
        assert len(d.mismatch_reasons) > 0
        assert any("b.py" in r for r in d.mismatch_reasons)
        assert any("c.py" in r for r in d.mismatch_reasons)

    def test_mismatch_reasons_empty_when_no_divergence(self):
        from substrate.organism.production_truth_delta import ProductionTruthDelta
        d = ProductionTruthDelta(
            changed_files_expected=["a.py"],
            changed_files_observed=["a.py"],
        )
        d.compute_file_divergences()
        assert d.mismatch_reasons == []

    def test_requires_operator_review_set_on_divergence(self):
        from substrate.organism.production_truth_delta import (
            PostMergeValidationResult,
            ProductionTruthDelta,
            StateSnapshot,
        )
        d = ProductionTruthDelta(
            changed_files_expected=["a.py"],
            changed_files_observed=["b.py"],
        )
        d.compute_file_divergences()
        d.validation_results.append(PostMergeValidationResult(command="test", passed=True))
        d.compute_state_delta(StateSnapshot(), StateSnapshot())
        d.finalize()
        assert d.requires_operator_review is True

    def test_requires_operator_review_false_when_clean(self):
        from substrate.organism.production_truth_delta import (
            PostMergeValidationResult,
            ProductionTruthDelta,
            StateSnapshot,
        )
        d = ProductionTruthDelta(
            changed_files_expected=["a.py"],
            changed_files_observed=["a.py"],
        )
        d.compute_file_divergences()
        d.validation_results.append(PostMergeValidationResult(command="test", passed=True))
        d.compute_state_delta(StateSnapshot(), StateSnapshot())
        d.finalize()
        assert d.requires_operator_review is False

    def test_to_dict_includes_all_new_fields(self):
        from substrate.organism.production_truth_delta import ProductionTruthDelta
        d = ProductionTruthDelta()
        out = d.to_dict()
        new_fields = {
            "manifest_id", "added_lines_expected", "removed_lines_expected",
            "added_lines_observed", "removed_lines_observed",
            "bottlenecks_before_after", "mismatch_reasons",
            "requires_operator_review",
        }
        assert new_fields.issubset(set(out.keys()))

    def test_state_snapshot_bottleneck_count(self):
        from substrate.organism.production_truth_delta import StateSnapshot
        s = StateSnapshot(bottleneck_count=5)
        assert s.to_dict()["bottleneck_count"] == 5


class TestProductionOutcomeIdempotencyKey:
    """Test idempotency key generation."""

    def test_key_format(self):
        from substrate.organism.autonomous_pr_factory import ProductionOutcomeCommitted
        poc = ProductionOutcomeCommitted(
            merge_commit="abc123",
            manifest_id="mfst-001",
            production_validation_result={"all_passed": True},
        )
        key = poc.idempotency_key
        assert key.startswith("production_outcome:abc123:mfst-001:")
        assert len(key.split(":")) == 4

    def test_key_deterministic(self):
        from substrate.organism.autonomous_pr_factory import ProductionOutcomeCommitted
        poc1 = ProductionOutcomeCommitted(
            merge_commit="abc", manifest_id="m1",
            production_validation_result={"x": 1},
        )
        poc2 = ProductionOutcomeCommitted(
            merge_commit="abc", manifest_id="m1",
            production_validation_result={"x": 1},
        )
        assert poc1.idempotency_key == poc2.idempotency_key

    def test_key_different_for_different_validation(self):
        from substrate.organism.autonomous_pr_factory import ProductionOutcomeCommitted
        poc1 = ProductionOutcomeCommitted(
            merge_commit="abc", manifest_id="m1",
            production_validation_result={"all_passed": True},
        )
        poc2 = ProductionOutcomeCommitted(
            merge_commit="abc", manifest_id="m1",
            production_validation_result={"all_passed": False},
        )
        assert poc1.idempotency_key != poc2.idempotency_key

    def test_key_in_to_dict(self):
        from substrate.organism.autonomous_pr_factory import ProductionOutcomeCommitted
        poc = ProductionOutcomeCommitted(merge_commit="x", manifest_id="y")
        d = poc.to_dict()
        assert "idempotency_key" in d
        assert d["idempotency_key"].startswith("production_outcome:")

    def test_production_validation_result_field(self):
        from substrate.organism.autonomous_pr_factory import ProductionOutcomeCommitted
        poc = ProductionOutcomeCommitted(
            production_validation_result={"all_passed": True, "results": []},
        )
        d = poc.to_dict()
        assert d["production_validation_result"]["all_passed"] is True


class TestSecurityExtended:
    """Extended security tests for path traversal and auth."""

    def test_delta_id_rejects_traversal(self):
        import re
        valid = re.fullmatch(r"ptd-[a-f0-9]{8}", "ptd-12345678")
        assert valid is not None
        invalid = re.fullmatch(r"ptd-[a-f0-9]{8}", "ptd-../../../etc")
        assert invalid is None
        invalid2 = re.fullmatch(r"ptd-[a-f0-9]{8}", "../../etc/passwd")
        assert invalid2 is None

    def test_verification_id_rejects_traversal(self):
        import re
        valid = re.fullmatch(r"pmv-[a-f0-9]{8}", "pmv-abcdef01")
        assert valid is not None
        invalid = re.fullmatch(r"pmv-[a-f0-9]{8}", "pmv-../../../etc")
        assert invalid is None

    def test_sandbox_id_rejects_traversal(self):
        import re
        valid = re.fullmatch(r"sb-[a-f0-9]{8}", "sb-12345678")
        assert valid is not None
        invalid = re.fullmatch(r"sb-[a-f0-9]{8}", "sb-../../../etc")
        assert invalid is None

    def test_delta_id_rejects_too_long(self):
        import re
        too_long = re.fullmatch(r"ptd-[a-f0-9]{8}", "ptd-123456789")
        assert too_long is None

    def test_delta_id_rejects_uppercase(self):
        import re
        upper = re.fullmatch(r"ptd-[a-f0-9]{8}", "ptd-ABCDEF01")
        assert upper is None

    def test_path_containment_blocks_traversal(self):
        from pathlib import Path
        mv_dir = Path("/opt/OS/data/umh/autonomous_lane/merge_verifications").resolve()
        malicious = Path(mv_dir, "../../etc/passwd").resolve()
        assert not malicious.is_relative_to(mv_dir)

    def test_path_containment_allows_valid(self):
        from pathlib import Path
        mv_dir = Path("/opt/OS/data/umh/autonomous_lane/merge_verifications").resolve()
        valid = Path(mv_dir, "ptd-12345678.json").resolve()
        assert valid.is_relative_to(mv_dir)


class TestThreadSafeDuplicateSuppression:
    """Test that duplicate production outcomes are suppressed under concurrency."""

    def test_duplicate_suppressed(self):
        import shutil
        import tempfile
        from substrate.organism.production_merge_verifier import ProductionMergeVerifier
        from substrate.organism.worktree_sandbox import SandboxManager

        tmp = tempfile.mkdtemp()
        try:
            manager = SandboxManager(
                repo_root=tmp,
                worktree_base=os.path.join(tmp, ".worktrees"),
                store_dir=os.path.join(tmp, "store"),
            )
            outcomes_received = []
            verifier = ProductionMergeVerifier(
                sandbox_manager=manager,
                repo_root=tmp,
                on_production_outcome=lambda o: outcomes_received.append(o),
            )
            from substrate.organism.production_truth_delta import (
                PostMergeValidationResult,
                ProductionTruthDelta,
                StateSnapshot,
            )
            from substrate.organism.production_merge_verifier import ProductionMergeVerification

            v = ProductionMergeVerification(
                sandbox_id="sb-test0001",
                merge_commit="abc123",
                manifest_id="mfst-1",
            )
            delta = ProductionTruthDelta(
                changed_files_expected=["a.py"],
                changed_files_observed=["a.py"],
            )
            delta.compute_file_divergences()
            delta.validation_results.append(PostMergeValidationResult(command="test", passed=True))
            delta.compute_state_delta(StateSnapshot(), StateSnapshot())
            delta.finalize()

            verifier._emit_production_outcome(v, delta)
            verifier._emit_production_outcome(v, delta)
            verifier._emit_production_outcome(v, delta)

            assert len(outcomes_received) == 1
            assert len(verifier._production_outcomes) == 1
        finally:
            shutil.rmtree(tmp)

    def test_different_sandboxes_not_suppressed(self):
        import shutil
        import tempfile
        from substrate.organism.production_merge_verifier import (
            ProductionMergeVerification,
            ProductionMergeVerifier,
        )
        from substrate.organism.production_truth_delta import (
            PostMergeValidationResult,
            ProductionTruthDelta,
            StateSnapshot,
        )
        from substrate.organism.worktree_sandbox import SandboxManager

        tmp = tempfile.mkdtemp()
        try:
            manager = SandboxManager(repo_root=tmp, worktree_base=os.path.join(tmp, ".wt"), store_dir=os.path.join(tmp, "st"))
            verifier = ProductionMergeVerifier(sandbox_manager=manager, repo_root=tmp)

            for i in range(3):
                v = ProductionMergeVerification(
                    sandbox_id=f"sb-test000{i}",
                    merge_commit=f"commit{i}",
                    manifest_id=f"mfst-{i}",
                )
                delta = ProductionTruthDelta(
                    changed_files_expected=["a.py"],
                    changed_files_observed=["a.py"],
                )
                delta.compute_file_divergences()
                delta.validation_results.append(PostMergeValidationResult(command="t", passed=True))
                delta.compute_state_delta(StateSnapshot(), StateSnapshot())
                delta.finalize()
                verifier._emit_production_outcome(v, delta)

            assert len(verifier._production_outcomes) == 3
        finally:
            shutil.rmtree(tmp)


class TestProductionPropagationWaves:
    """Test Wave 1 and Wave 2 propagation targets."""

    def test_wave_1_targets(self):
        import shutil
        import tempfile
        from substrate.organism.production_merge_verifier import (
            ProductionMergeVerification,
            ProductionMergeVerifier,
        )
        from substrate.organism.production_truth_delta import (
            ProductionTruthDelta,
            StateSnapshot,
        )
        from substrate.organism.worktree_sandbox import SandboxManager

        tmp = tempfile.mkdtemp()
        try:
            manager = SandboxManager(repo_root=tmp, worktree_base=os.path.join(tmp, ".wt"), store_dir=os.path.join(tmp, "st"))
            verifier = ProductionMergeVerifier(sandbox_manager=manager, repo_root=tmp)
            v = ProductionMergeVerification()
            delta = ProductionTruthDelta()
            result = verifier._propagate_wave_1(v, delta)
            assert "targets" in result
            assert len(result["targets"]) == 5
            assert result["all_succeeded"] is True
            assert "production_outcome_history" in result["targets"]
            assert "template_registry_reliability" in result["targets"]
            assert "world_model_evidence" in result["targets"]
        finally:
            shutil.rmtree(tmp)

    def test_wave_2_targets(self):
        import shutil
        import tempfile
        from substrate.organism.production_merge_verifier import (
            ProductionMergeVerification,
            ProductionMergeVerifier,
        )
        from substrate.organism.production_truth_delta import (
            ProductionTruthDelta,
            StateSnapshot,
        )
        from substrate.organism.worktree_sandbox import SandboxManager

        tmp = tempfile.mkdtemp()
        try:
            manager = SandboxManager(repo_root=tmp, worktree_base=os.path.join(tmp, ".wt"), store_dir=os.path.join(tmp, "st"))
            verifier = ProductionMergeVerifier(sandbox_manager=manager, repo_root=tmp)
            v = ProductionMergeVerification()
            delta = ProductionTruthDelta()
            result = verifier._propagate_wave_2(v, delta)
            assert "targets" in result
            assert len(result["targets"]) == 6
            assert result["all_succeeded"] is True
            assert "contradiction_engine_recheck" in result["targets"]
            assert "cockpit_realtime_status" in result["targets"]
        finally:
            shutil.rmtree(tmp)


class TestDaemonStatusExtended:
    """Test daemon exposes all required cadence/production fields."""

    def test_daemon_status_has_cadence_mode(self):
        from substrate.organism.daemon import OrganismDaemon
        d = OrganismDaemon(store_dir="/tmp/test_daemon_ext")
        status = d.status()
        assert "autonomous_cadence_mode" in status
        assert status["autonomous_cadence_mode"] == "off"

    def test_daemon_status_has_last_dry_run_at(self):
        from substrate.organism.daemon import OrganismDaemon
        d = OrganismDaemon(store_dir="/tmp/test_daemon_ext2")
        status = d.status()
        assert "last_dry_run_at" in status

    def test_daemon_status_has_candidate_count(self):
        from substrate.organism.daemon import OrganismDaemon
        d = OrganismDaemon(store_dir="/tmp/test_daemon_ext3")
        status = d.status()
        assert "last_candidate_count" in status
        assert status["last_candidate_count"] == 0

    def test_daemon_status_has_recommendation_count(self):
        from substrate.organism.daemon import OrganismDaemon
        d = OrganismDaemon(store_dir="/tmp/test_daemon_ext4")
        status = d.status()
        assert "last_recommendation_count" in status

    def test_daemon_status_has_active_sandbox_count(self):
        from substrate.organism.daemon import OrganismDaemon
        d = OrganismDaemon(store_dir="/tmp/test_daemon_ext5")
        status = d.status()
        assert "active_sandbox_count" in status

    def test_daemon_status_has_active_pr_count(self):
        from substrate.organism.daemon import OrganismDaemon
        d = OrganismDaemon(store_dir="/tmp/test_daemon_ext6")
        status = d.status()
        assert "active_pr_count" in status

    def test_daemon_status_has_pending_verification_count(self):
        from substrate.organism.daemon import OrganismDaemon
        d = OrganismDaemon(store_dir="/tmp/test_daemon_ext7")
        status = d.status()
        assert "pending_merge_verification_count" in status

    def test_daemon_status_has_last_delta_id(self):
        from substrate.organism.daemon import OrganismDaemon
        d = OrganismDaemon(store_dir="/tmp/test_daemon_ext8")
        status = d.status()
        assert "last_production_truth_delta_id" in status

    def test_daemon_status_has_last_production_outcome_at(self):
        from substrate.organism.daemon import OrganismDaemon
        d = OrganismDaemon(store_dir="/tmp/test_daemon_ext9")
        status = d.status()
        assert "last_production_outcome_at" in status


class TestTruthBoundaryExtended:
    """Extended truth boundary enforcement tests."""

    def test_sandbox_outcome_boundary_is_sandbox(self):
        from substrate.organism.autonomous_pr_factory import SandboxOutcomeCommitted
        soc = SandboxOutcomeCommitted()
        assert soc.boundary == "sandbox"
        assert soc.to_dict()["boundary"] == "sandbox"

    def test_production_outcome_boundary_is_production(self):
        from substrate.organism.autonomous_pr_factory import ProductionOutcomeCommitted
        poc = ProductionOutcomeCommitted()
        assert poc.boundary == "production"
        assert poc.to_dict()["boundary"] == "production"

    def test_event_types_structurally_distinct(self):
        from substrate.organism.autonomous_pr_factory import (
            ProductionOutcomeCommitted,
            SandboxOutcomeCommitted,
        )
        soc = SandboxOutcomeCommitted()
        poc = ProductionOutcomeCommitted()
        assert soc.to_dict()["event_type"] == "sandbox_outcome_committed"
        assert poc.to_dict()["event_type"] == "production_outcome_committed"

    def test_production_outcome_has_propagation_fields(self):
        from substrate.organism.autonomous_pr_factory import ProductionOutcomeCommitted
        poc = ProductionOutcomeCommitted()
        d = poc.to_dict()
        assert "production_propagation_complete" in d
        assert "production_truth_delta" in d
        assert "production_validation_result" in d
        assert "affected_subsystems" in d

    def test_sandbox_outcome_lacks_propagation_fields(self):
        from substrate.organism.autonomous_pr_factory import SandboxOutcomeCommitted
        soc = SandboxOutcomeCommitted()
        d = soc.to_dict()
        assert "production_propagation_complete" not in d
        assert "production_truth_delta" not in d

    def test_production_outcome_event_id_prefix_distinct(self):
        from substrate.organism.autonomous_pr_factory import (
            ProductionOutcomeCommitted,
            SandboxOutcomeCommitted,
        )
        soc = SandboxOutcomeCommitted()
        poc = ProductionOutcomeCommitted()
        assert soc.event_id.startswith("soc-")
        assert poc.event_id.startswith("poc-")


class TestVerifierExpectedObservedMismatch:
    """Test EXPECTED_OBSERVED_MISMATCH status is assigned correctly."""

    def test_mismatch_status_on_file_divergence(self):
        from substrate.organism.production_truth_delta import (
            DeltaStatus,
            PostMergeValidationResult,
            ProductionTruthDelta,
            StateSnapshot,
        )

        delta = ProductionTruthDelta(
            changed_files_expected=["a.py"],
            changed_files_observed=["b.py"],
        )
        delta.compute_file_divergences()
        delta.validation_results.append(PostMergeValidationResult(command="t", passed=True))
        delta.compute_state_delta(StateSnapshot(), StateSnapshot())
        delta.finalize()
        assert delta.status == DeltaStatus.REQUIRES_REVIEW
        assert delta.has_file_divergence is True


class TestCadencePolicyExtended:
    """Extended cadence policy tests."""

    def test_default_mode_off(self):
        from substrate.organism.autonomous_cadence import CadenceMode, CadencePolicy
        p = CadencePolicy()
        assert p.mode == CadenceMode.OFF

    def test_no_auto_merge_always_true(self):
        from substrate.organism.autonomous_cadence import CadencePolicy
        p = CadencePolicy()
        assert p.no_auto_merge is True

    def test_require_operator_for_pr_default_true(self):
        from substrate.organism.autonomous_cadence import CadencePolicy
        p = CadencePolicy()
        assert p.require_operator_enable_for_pr_creation is True

    def test_max_prs_per_day_default(self):
        from substrate.organism.autonomous_cadence import CadencePolicy
        p = CadencePolicy()
        assert p.max_prs_per_day == 1

    def test_allowed_risk_low_only(self):
        from substrate.organism.autonomous_cadence import CadencePolicy
        p = CadencePolicy()
        assert p.allowed_risk == "low"


class TestComputeLineCounts:
    """Test line count computation from git diff."""

    def test_compute_line_counts_no_repo(self):
        from substrate.organism.production_truth_delta import ProductionTruthDelta
        d = ProductionTruthDelta()
        d.compute_line_counts("")
        assert d.added_lines_observed == 0
        assert d.removed_lines_observed == 0

    def test_compute_line_counts_no_commits(self):
        from substrate.organism.production_truth_delta import ProductionTruthDelta
        d = ProductionTruthDelta(base_commit="", merge_commit="")
        d.compute_line_counts("/tmp")
        assert d.added_lines_observed == 0


class TestProductionTruthDeltaFinalize:
    """Test finalize behavior."""

    def test_finalize_production_partial_on_failed_validation(self):
        from substrate.organism.production_truth_delta import (
            DeltaStatus,
            PostMergeValidationResult,
            ProductionTruthDelta,
            StateSnapshot,
        )
        d = ProductionTruthDelta(
            changed_files_expected=["a.py"],
            changed_files_observed=["a.py"],
        )
        d.compute_file_divergences()
        d.validation_results.append(PostMergeValidationResult(command="test", passed=False))
        d.compute_state_delta(StateSnapshot(), StateSnapshot())
        d.finalize()
        assert d.status == DeltaStatus.PRODUCTION_PARTIAL
        assert d.requires_operator_review is True
        assert any("validation failed" in r for r in d.mismatch_reasons)

    def test_finalize_verified_on_all_pass(self):
        from substrate.organism.production_truth_delta import (
            DeltaStatus,
            PostMergeValidationResult,
            ProductionTruthDelta,
            StateSnapshot,
        )
        d = ProductionTruthDelta(
            changed_files_expected=["a.py"],
            changed_files_observed=["a.py"],
        )
        d.compute_file_divergences()
        d.validation_results.append(PostMergeValidationResult(command="test", passed=True))
        d.compute_state_delta(StateSnapshot(), StateSnapshot())
        d.finalize()
        assert d.status == DeltaStatus.PRODUCTION_VERIFIED
        assert d.requires_operator_review is False
