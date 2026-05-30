"""Phase 10.3 — Production truth promotion tests.

Tests the full production merge verification pipeline:
- ProductionMergeVerifier with correct file diff isolation
- ProductionTruthDelta computation and finalization
- ProductionOutcomeCommitted emission + idempotency
- Candidate supply resolved candidate suppression
- Template reliability update from production outcome
"""
from __future__ import annotations

import os
import sys
import json
import tempfile
import subprocess

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from substrate.organism.production_merge_verifier import (
    ProductionMergeVerifier,
    ProductionMergeVerification,
    MergeVerificationStatus,
)
from substrate.organism.production_truth_delta import (
    ProductionTruthDelta,
    DeltaStatus,
    PostMergeValidationResult,
    StateSnapshot,
    FileDivergence,
)
from substrate.organism.worktree_sandbox import (
    SandboxManager,
    SandboxStatus,
    WorktreeSandbox,
)
from substrate.organism.candidate_supply_engine import (
    CandidateSupplyEngine,
    SupplyCandidate,
)
from substrate.organism.template_registry import (
    TemplateRegistry,
    TemplateCandidate,
    TemplateStatus,
)


class TestProductionTruthDelta:
    def test_delta_finalize_verified(self):
        delta = ProductionTruthDelta(
            changed_files_expected=["a.py"],
            changed_files_observed=["a.py"],
        )
        delta.validation_results.append(
            PostMergeValidationResult(command="test", passed=True, exit_code=0)
        )
        delta.compute_file_divergences()
        delta.finalize()
        assert delta.status == DeltaStatus.PRODUCTION_VERIFIED
        assert not delta.has_file_divergence

    def test_delta_finalize_with_divergence(self):
        delta = ProductionTruthDelta(
            changed_files_expected=["a.py"],
            changed_files_observed=["a.py", "b.py"],
        )
        delta.validation_results.append(
            PostMergeValidationResult(command="test", passed=True, exit_code=0)
        )
        delta.compute_file_divergences()
        delta.finalize()
        assert delta.status == DeltaStatus.REQUIRES_REVIEW
        assert delta.has_file_divergence
        assert delta.requires_operator_review

    def test_delta_finalize_validation_failed(self):
        delta = ProductionTruthDelta(
            changed_files_expected=["a.py"],
            changed_files_observed=["a.py"],
        )
        delta.validation_results.append(
            PostMergeValidationResult(command="test", passed=False, exit_code=1)
        )
        delta.compute_file_divergences()
        delta.finalize()
        assert delta.status == DeltaStatus.PRODUCTION_PARTIAL
        assert delta.requires_operator_review

    def test_delta_state_delta_computation(self):
        delta = ProductionTruthDelta()
        before = StateSnapshot(
            world_model_hash="abc",
            template_count=5,
            agent_count=3,
        )
        after = StateSnapshot(
            world_model_hash="def",
            template_count=6,
            agent_count=3,
        )
        delta.compute_state_delta(before, after)
        assert delta.world_model_before_after["changed"] is True
        assert delta.template_confidence_before_after["before_count"] == 5
        assert delta.template_confidence_before_after["after_count"] == 6

    def test_delta_to_dict_roundtrip(self):
        delta = ProductionTruthDelta(
            sandbox_id="sb-test0001",
            pr_number=99,
        )
        delta.validation_results.append(
            PostMergeValidationResult(command="check", passed=True, exit_code=0)
        )
        d = delta.to_dict()
        assert d["sandbox_id"] == "sb-test0001"
        assert d["pr_number"] == 99
        assert len(d["validation_results"]) == 1


class TestProductionMergeVerification:
    def test_verification_initial_state(self):
        v = ProductionMergeVerification(sandbox_id="sb-test0001", pr_number=42)
        assert v.status == MergeVerificationStatus.PENDING
        assert v.pr_number == 42
        assert v.sandbox_id == "sb-test0001"

    def test_verification_to_dict(self):
        v = ProductionMergeVerification(sandbox_id="sb-test0001", pr_number=42)
        d = v.to_dict()
        assert d["status"] == "pending"
        assert d["pr_number"] == 42


class TestProductionOutcomeIdempotency:
    def test_duplicate_emission_suppressed(self):
        with tempfile.TemporaryDirectory() as td:
            manager = SandboxManager(store_dir=td)
            sb = WorktreeSandbox(
                sandbox_id="sb-dup00001",
                branch_name="test-branch",
                base_commit="abc123",
                head_commit="def456",
                pr_number=99,
                status=SandboxStatus.MERGED,
            )
            manager._sandboxes[sb.sandbox_id] = sb

            outcomes = []
            verifier = ProductionMergeVerifier(
                sandbox_manager=manager,
                store_dir=td,
                on_production_outcome=lambda o: outcomes.append(o),
            )

            v = ProductionMergeVerification(
                sandbox_id="sb-dup00001",
                merge_commit="aaa111",
            )
            delta = ProductionTruthDelta(
                sandbox_id="sb-dup00001",
                status=DeltaStatus.PRODUCTION_VERIFIED,
            )
            delta.validation_results.append(
                PostMergeValidationResult(command="t", passed=True, exit_code=0)
            )
            v.truth_delta = delta

            verifier._emit_production_outcome(v, delta)
            verifier._emit_production_outcome(v, delta)

            assert len(outcomes) == 1
            assert len(verifier.production_outcomes) == 1


class TestCandidateSupplyResolution:
    def test_resolved_candidate_suppressed(self):
        with tempfile.TemporaryDirectory() as td:
            engine = CandidateSupplyEngine(state_dir=td)
            engine.mark_resolved("fix the thing")
            c = SupplyCandidate(
                description="fix the thing",
            )
            assert engine._is_resolved(c)

    def test_resolved_substring_match(self):
        with tempfile.TemporaryDirectory() as td:
            engine = CandidateSupplyEngine(state_dir=td)
            engine.mark_resolved("template store path does not exist")
            c = SupplyCandidate(
                description="Template audit identified gap: Template store path does not exist. More details here.",
            )
            assert engine._is_resolved(c)

    def test_unresolved_candidate_not_suppressed(self):
        with tempfile.TemporaryDirectory() as td:
            engine = CandidateSupplyEngine(state_dir=td)
            engine.mark_resolved("fix the thing")
            c = SupplyCandidate(
                description="something completely different",
            )
            assert not engine._is_resolved(c)

    def test_duplicate_mark_resolved_idempotent(self):
        with tempfile.TemporaryDirectory() as td:
            engine = CandidateSupplyEngine(state_dir=td)
            engine.mark_resolved("fix the thing")
            engine.mark_resolved("fix the thing")
            assert len(engine._resolved_descriptions) == 1


class TestTemplateReliabilityUpdate:
    def test_record_usage_updates_confidence(self):
        with tempfile.TemporaryDirectory() as td:
            registry = TemplateRegistry(store_dir=td)
            tpl = TemplateCandidate(
                template_id="tpl-test001",
                template_type="fix",
                confidence=0.5,
                status=TemplateStatus.PROMOTED,
            )
            registry._candidates["tpl-test001"] = tpl

            registry.record_usage("tpl-test001", success=True)
            assert tpl.observed_success_count == 1
            assert tpl.confidence == 1.0

            registry.record_usage("tpl-test001", success=False)
            assert tpl.observed_failure_count == 1
            assert tpl.confidence == 0.5

    def test_record_usage_nonexistent_template(self):
        with tempfile.TemporaryDirectory() as td:
            registry = TemplateRegistry(store_dir=td)
            registry.record_usage("tpl-nonexist", success=True)


class TestFileDivergence:
    def test_no_divergence(self):
        fd = FileDivergence(path="a.py", expected=True, observed=True)
        assert not fd.diverged

    def test_expected_not_observed(self):
        fd = FileDivergence(path="a.py", expected=True, observed=False)
        assert fd.diverged

    def test_observed_not_expected(self):
        fd = FileDivergence(path="a.py", expected=False, observed=True)
        assert fd.diverged


class TestMergeVerifierDiffIsolation:
    """Tests that _compute_observed_files uses merge_commit^1..merge_commit."""

    def test_compute_observed_uses_first_parent(self):
        with tempfile.TemporaryDirectory() as td:
            manager = SandboxManager(store_dir=td)
            verifier = ProductionMergeVerifier(
                sandbox_manager=manager,
                store_dir=td,
            )

            v = ProductionMergeVerification(
                merge_commit="03fe81d86fd6092338a3e9388649abbc9f2f7b00",
                base_commit="83f1da82",
            )

            verifier._compute_observed_files(v)
            assert "data/umh/organism/templates/.gitkeep" in v.observed_files
            assert "scripts/verify_template_store.py" in v.observed_files
            assert "substrate/organism/approval_gate.py" not in v.observed_files
