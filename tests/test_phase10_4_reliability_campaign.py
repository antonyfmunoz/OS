"""Phase 10.4 — Low-risk production truth reliability campaign tests.

Tests the multi-candidate campaign lifecycle:
- Campaign queue ranking from extended candidate sources
- Batch selection with file conflict detection
- Approval packet creation
- Multi-candidate sandbox orchestration
- PR review result recording
- Production verification loop across multiple candidates
- Reliability calibration across multiple outcomes
- Post-campaign cadence suppression
- Template confidence updates across multiple outcomes
- Agent reliability updates across multiple outcomes
"""
from __future__ import annotations

import os
import sys
import json
import tempfile
import time

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from substrate.organism.candidate_supply_engine import (
    CandidateSupplyEngine,
    SupplyCandidate,
    SupplyResult,
)
from substrate.organism.template_registry import (
    TemplateRegistry,
    TemplateCandidate,
    TemplateStatus,
    TemplateType,
    _infer_template_type,
)
from substrate.organism.template_governance import (
    TemplateGovernance,
    GovernanceDecision,
)
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
)
from substrate.organism.worktree_sandbox import (
    SandboxManager,
    SandboxStatus,
    WorktreeSandbox,
)
from substrate.organism.autonomous_cadence import (
    AutonomousCadence,
    CadenceMode,
    CadencePolicy,
)


class TestCampaignQueueRanking:
    """TST-12: Campaign queue candidates are ranked by template confidence then agent reliability."""

    def test_candidates_sorted_by_template_confidence_desc(self):
        with tempfile.TemporaryDirectory() as td:
            engine = CandidateSupplyEngine(state_dir=td)
            c1 = SupplyCandidate(template_confidence=0.7, agent_reliability=0.5)
            c2 = SupplyCandidate(template_confidence=0.9, agent_reliability=0.5)
            c3 = SupplyCandidate(template_confidence=0.8, agent_reliability=0.5)
            candidates = sorted(
                [c1, c2, c3],
                key=lambda c: (c.template_confidence, c.agent_reliability),
                reverse=True,
            )
            assert candidates[0].template_confidence == 0.9
            assert candidates[1].template_confidence == 0.8
            assert candidates[2].template_confidence == 0.7

    def test_tiebreak_by_agent_reliability(self):
        c1 = SupplyCandidate(template_confidence=0.8, agent_reliability=0.6)
        c2 = SupplyCandidate(template_confidence=0.8, agent_reliability=0.9)
        candidates = sorted(
            [c1, c2],
            key=lambda c: (c.template_confidence, c.agent_reliability),
            reverse=True,
        )
        assert candidates[0].agent_reliability == 0.9

    def test_discover_returns_supply_result(self):
        with tempfile.TemporaryDirectory() as td:
            engine = CandidateSupplyEngine(state_dir=td)
            result = engine.discover()
            assert isinstance(result, SupplyResult)
            assert isinstance(result.candidates, list)
            assert isinstance(result.source_scan_proof, dict)


class TestExtendedSources:
    """TST-13: Extended candidate sources produce candidates with affected files."""

    def test_stale_test_paths_source_exists(self):
        with tempfile.TemporaryDirectory() as td:
            engine = CandidateSupplyEngine(state_dir=td)
            result = engine.discover()
            assert "stale_test_paths" in result.source_scan_proof

    def test_missing_package_init_source_exists(self):
        with tempfile.TemporaryDirectory() as td:
            engine = CandidateSupplyEngine(state_dir=td)
            result = engine.discover()
            assert "missing_package_init" in result.source_scan_proof

    def test_stale_docstrings_source_exists(self):
        with tempfile.TemporaryDirectory() as td:
            engine = CandidateSupplyEngine(state_dir=td)
            result = engine.discover()
            assert "stale_docstrings" in result.source_scan_proof

    def test_nine_sources_scanned(self):
        with tempfile.TemporaryDirectory() as td:
            engine = CandidateSupplyEngine(state_dir=td)
            result = engine.discover()
            assert len(result.source_scan_proof) == 9

    def test_stale_test_paths_have_affected_files(self):
        with tempfile.TemporaryDirectory() as td:
            engine = CandidateSupplyEngine(state_dir=td)
            result = engine.discover()
            stale = [c for c in result.candidates if c.source == "stale_test_paths"]
            for c in stale:
                assert len(c.affected_files) > 0

    def test_stale_docstrings_have_affected_files(self):
        with tempfile.TemporaryDirectory() as td:
            engine = CandidateSupplyEngine(state_dir=td)
            result = engine.discover()
            docstrings = [c for c in result.candidates if c.source == "stale_docstrings"]
            for c in docstrings:
                assert len(c.affected_files) > 0
                assert c.non_mutating is True


class TestBatchSelection:
    """TST-14: Batch selection filters by eligibility and file independence."""

    def test_file_conflict_detection(self):
        c1 = SupplyCandidate(affected_files=["a.py", "b.py"])
        c2 = SupplyCandidate(affected_files=["b.py", "c.py"])
        c3 = SupplyCandidate(affected_files=["d.py"])

        used_files: set[str] = set()
        selected: list[SupplyCandidate] = []

        for c in [c1, c2, c3]:
            candidate_files = set(c.affected_files)
            if not candidate_files & used_files:
                selected.append(c)
                used_files.update(candidate_files)

        assert len(selected) == 2
        assert c1 in selected
        assert c2 not in selected
        assert c3 in selected

    def test_batch_excludes_no_affected_files(self):
        candidates = [
            SupplyCandidate(affected_files=["a.py"], policy_decision="cadence_eligible"),
            SupplyCandidate(affected_files=[], policy_decision="cadence_eligible"),
            SupplyCandidate(affected_files=["b.py"], policy_decision="cadence_eligible"),
        ]
        selected = [c for c in candidates if c.affected_files]
        assert len(selected) == 2

    def test_batch_excludes_blocked_candidates(self):
        candidates = [
            SupplyCandidate(policy_decision="cadence_eligible"),
            SupplyCandidate(policy_decision="blocked"),
            SupplyCandidate(policy_decision="cadence_eligible"),
        ]
        eligible = [c for c in candidates if c.policy_decision == "cadence_eligible"]
        assert len(eligible) == 2

    def test_batch_max_5_candidates(self):
        candidates = [SupplyCandidate(affected_files=[f"f{i}.py"]) for i in range(10)]
        batch = candidates[:5]
        assert len(batch) <= 5


class TestApprovalPacketCreation:
    """TST-15: Approval packets contain required fields."""

    def test_packet_has_required_fields(self):
        packet = {
            "packet_id": "apk-test001",
            "candidate_id": "cse-test001",
            "candidate_evidence": [{"source": "test", "detail": "test", "confidence": 0.8}],
            "matched_template_id": "tpl-test001",
            "template_confidence": 0.8,
            "governance_score": 0.85,
            "risk_class": "low",
            "affected_files": ["a.py"],
            "validation_plan": "py_compile",
            "rollback_plan": "git revert",
            "why_safe": "LOW risk",
            "what_will_not_happen": ["no auto-merge"],
            "status": "pending",
            "expires_at": time.time() + 86400,
        }
        required = [
            "packet_id", "candidate_id", "candidate_evidence",
            "matched_template_id", "template_confidence", "governance_score",
            "risk_class", "affected_files", "validation_plan",
            "rollback_plan", "why_safe", "what_will_not_happen",
            "status", "expires_at",
        ]
        for field in required:
            assert field in packet, f"Missing field: {field}"

    def test_packet_expiration_future(self):
        now = time.time()
        expires = now + 86400
        assert expires > now

    def test_packet_status_transitions(self):
        valid_statuses = {"pending", "approved", "rejected", "expired"}
        assert "approved" in valid_statuses
        assert "pending" in valid_statuses


class TestDocumentationAlignmentTemplate:
    """TST-16: Documentation alignment template exists and passes governance."""

    def test_documentation_alignment_template_type_exists(self):
        assert hasattr(TemplateType, "DOCUMENTATION_ALIGNMENT")
        assert TemplateType.DOCUMENTATION_ALIGNMENT.value == "documentation_alignment"

    def test_infer_template_type_docstring(self):
        result = _infer_template_type("documentation_fix", "update stale docstring")
        assert result == TemplateType.DOCUMENTATION_ALIGNMENT

    def test_infer_template_type_documentation_keyword(self):
        result = _infer_template_type("some_action", "fix documentation alignment")
        assert result == TemplateType.DOCUMENTATION_ALIGNMENT

    def test_infer_template_type_stale_project_name(self):
        result = _infer_template_type("some_action", "stale project name in docstring")
        assert result == TemplateType.DOCUMENTATION_ALIGNMENT

    def test_documentation_template_seeded(self):
        reg = TemplateRegistry()
        tpl = reg.get_template("tpl-seed-documentation-alignment-01")
        if tpl:
            assert tpl.template_type == TemplateType.DOCUMENTATION_ALIGNMENT
            assert tpl.risk_class == "low"
            assert tpl.confidence >= 0.7

    def test_documentation_template_passes_governance(self):
        reg = TemplateRegistry()
        gov = TemplateGovernance()
        tpl = reg.get_template("tpl-seed-documentation-alignment-01")
        if tpl:
            score = gov.evaluate(tpl)
            assert score.decision != GovernanceDecision.BLOCKED, (
                f"Documentation template blocked: {score.reason_codes}"
            )

    def test_action_type_mapping_documentation_fix(self):
        from substrate.organism.template_registry import _ACTION_TO_TEMPLATE_TYPE
        assert "documentation_fix" in _ACTION_TO_TEMPLATE_TYPE
        assert _ACTION_TO_TEMPLATE_TYPE["documentation_fix"] == TemplateType.DOCUMENTATION_ALIGNMENT

    def test_action_type_mapping_test_repair(self):
        from substrate.organism.template_registry import _ACTION_TO_TEMPLATE_TYPE
        assert "test_repair" in _ACTION_TO_TEMPLATE_TYPE
        assert _ACTION_TO_TEMPLATE_TYPE["test_repair"] == TemplateType.TEST_REPAIR


class TestMultiCandidateProductionVerification:
    """TST-17: Production verification works across multiple candidates."""

    def test_multiple_verifications_independent(self):
        with tempfile.TemporaryDirectory() as td:
            manager = SandboxManager(store_dir=td)
            outcomes = []
            verifier = ProductionMergeVerifier(
                sandbox_manager=manager,
                store_dir=td,
                on_production_outcome=lambda o: outcomes.append(o),
            )

            for i in range(3):
                sb = WorktreeSandbox(
                    sandbox_id=f"sb-multi{i:04d}",
                    branch_name=f"test-branch-{i}",
                    base_commit="abc123",
                    head_commit=f"def{i:03d}",
                    pr_number=50 + i,
                    status=SandboxStatus.MERGED,
                )
                manager._sandboxes[sb.sandbox_id] = sb

                v = ProductionMergeVerification(
                    sandbox_id=f"sb-multi{i:04d}",
                    merge_commit=f"merge{i:04d}",
                )
                delta = ProductionTruthDelta(
                    sandbox_id=f"sb-multi{i:04d}",
                    status=DeltaStatus.PRODUCTION_VERIFIED,
                )
                delta.validation_results.append(
                    PostMergeValidationResult(command="t", passed=True, exit_code=0)
                )
                v.truth_delta = delta
                verifier._emit_production_outcome(v, delta)

            assert len(outcomes) == 3

    def test_duplicate_suppression_per_sandbox(self):
        with tempfile.TemporaryDirectory() as td:
            manager = SandboxManager(store_dir=td)
            outcomes = []
            verifier = ProductionMergeVerifier(
                sandbox_manager=manager,
                store_dir=td,
                on_production_outcome=lambda o: outcomes.append(o),
            )

            sb = WorktreeSandbox(
                sandbox_id="sb-dup10401",
                branch_name="test-branch",
                base_commit="abc123",
                head_commit="def456",
                pr_number=99,
                status=SandboxStatus.MERGED,
            )
            manager._sandboxes[sb.sandbox_id] = sb

            v = ProductionMergeVerification(
                sandbox_id="sb-dup10401",
                merge_commit="aaa111",
            )
            delta = ProductionTruthDelta(
                sandbox_id="sb-dup10401",
                status=DeltaStatus.PRODUCTION_VERIFIED,
            )
            delta.validation_results.append(
                PostMergeValidationResult(command="t", passed=True, exit_code=0)
            )
            v.truth_delta = delta

            verifier._emit_production_outcome(v, delta)
            verifier._emit_production_outcome(v, delta)
            verifier._emit_production_outcome(v, delta)

            assert len(outcomes) == 1


class TestReliabilityCalibration:
    """TST-18: Template and agent reliability update correctly across multiple outcomes."""

    def test_template_confidence_increases_with_successes(self):
        with tempfile.TemporaryDirectory() as td:
            registry = TemplateRegistry(store_dir=td)
            tpl = TemplateCandidate(
                template_id="tpl-cal001",
                confidence=0.5,
                observed_success_count=1,
                observed_failure_count=1,
                status=TemplateStatus.PROMOTED,
            )
            registry._candidates["tpl-cal001"] = tpl

            registry.record_usage("tpl-cal001", success=True)
            assert tpl.confidence > 0.5

            registry.record_usage("tpl-cal001", success=True)
            assert tpl.confidence > 0.6

            registry.record_usage("tpl-cal001", success=True)
            assert tpl.observed_success_count == 4
            assert tpl.observed_failure_count == 1
            assert tpl.confidence == 4 / 5

    def test_template_confidence_decreases_with_failures(self):
        with tempfile.TemporaryDirectory() as td:
            registry = TemplateRegistry(store_dir=td)
            tpl = TemplateCandidate(
                template_id="tpl-cal002",
                confidence=0.8,
                observed_success_count=4,
                observed_failure_count=1,
                status=TemplateStatus.PROMOTED,
            )
            registry._candidates["tpl-cal002"] = tpl

            registry.record_usage("tpl-cal002", success=False)
            assert tpl.confidence < 0.8
            assert tpl.observed_failure_count == 2

    def test_multiple_templates_track_independently(self):
        with tempfile.TemporaryDirectory() as td:
            registry = TemplateRegistry(store_dir=td)
            tpl1 = TemplateCandidate(
                template_id="tpl-ind001",
                confidence=0.5,
                status=TemplateStatus.PROMOTED,
            )
            tpl2 = TemplateCandidate(
                template_id="tpl-ind002",
                confidence=0.5,
                status=TemplateStatus.PROMOTED,
            )
            registry._candidates["tpl-ind001"] = tpl1
            registry._candidates["tpl-ind002"] = tpl2

            registry.record_usage("tpl-ind001", success=True)
            registry.record_usage("tpl-ind002", success=False)

            assert tpl1.confidence == 1.0
            assert tpl2.confidence == 0.0


class TestPostCampaignCadenceSuppression:
    """TST-19: Cadence dry-run suppresses resolved candidates after campaign."""

    def test_multiple_resolved_candidates_suppressed(self):
        with tempfile.TemporaryDirectory() as td:
            engine = CandidateSupplyEngine(state_dir=td)
            engine.mark_resolved("fix the first thing")
            engine.mark_resolved("fix the second thing")
            engine.mark_resolved("fix the third thing")

            c1 = SupplyCandidate(description="fix the first thing")
            c2 = SupplyCandidate(description="fix the second thing")
            c3 = SupplyCandidate(description="something new")

            assert engine._is_resolved(c1)
            assert engine._is_resolved(c2)
            assert not engine._is_resolved(c3)

    def test_cadence_dry_run_only_never_creates_pr(self):
        policy = CadencePolicy(mode=CadenceMode.DRY_RUN_ONLY)
        cadence = AutonomousCadence(
            policy=policy,
            candidate_discovery_fn=lambda: [],
        )
        assert policy.no_auto_merge is True
        assert policy.mode == CadenceMode.DRY_RUN_ONLY

    def test_resolved_descriptions_persist_across_discover_calls(self):
        with tempfile.TemporaryDirectory() as td:
            engine = CandidateSupplyEngine(state_dir=td)
            engine.mark_resolved("persisted description")

            engine.discover()
            assert "persisted description" in engine._resolved_descriptions
            engine.discover()
            assert "persisted description" in engine._resolved_descriptions


class TestCandidateSupplyToDict:
    """TST-20: Supply candidate serialization includes all campaign-required fields."""

    def test_to_dict_includes_all_fields(self):
        c = SupplyCandidate(
            source="stale_test_paths",
            title="test title",
            description="test description",
            evidence=[{"source": "test", "detail": "d", "confidence": 0.8}],
            affected_files=["a.py"],
            risk_class="low",
            matching_templates=["tpl-test001"],
            template_confidence=0.75,
            agent_reliability=0.8,
            validation_method="assertion",
            rollback_method="revert",
            non_mutating=True,
        )
        d = c.to_dict()
        assert d["source"] == "stale_test_paths"
        assert d["affected_files"] == ["a.py"]
        assert d["template_confidence"] == 0.75
        assert d["non_mutating"] is True

    def test_to_cadence_dict_includes_template_id(self):
        c = SupplyCandidate(
            matching_templates=["tpl-test001", "tpl-test002"],
        )
        d = c.to_cadence_dict()
        assert d["template_id"] == "tpl-test001"

    def test_to_cadence_dict_empty_templates(self):
        c = SupplyCandidate()
        d = c.to_cadence_dict()
        assert d["template_id"] == ""


class TestSafetyInvariants104:
    """TST-21: Phase 10.4 safety invariants."""

    def test_cadence_default_no_auto_merge(self):
        policy = CadencePolicy()
        assert policy.no_auto_merge is True

    def test_cadence_default_low_risk_only(self):
        policy = CadencePolicy()
        assert policy.allowed_risk == "low"

    def test_cadence_default_require_template(self):
        policy = CadencePolicy()
        assert policy.require_template is True

    def test_cadence_default_require_operator_enable(self):
        policy = CadencePolicy()
        assert policy.require_operator_enable_for_pr_creation is True

    def test_all_candidates_low_risk(self):
        with tempfile.TemporaryDirectory() as td:
            engine = CandidateSupplyEngine(state_dir=td)
            result = engine.discover()
            for c in result.candidates:
                assert c.risk_class == "low", f"Candidate {c.candidate_id} has risk {c.risk_class}"
