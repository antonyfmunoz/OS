"""C33 Phase 1 benchmark infrastructure tests.

Validates all 8 benchmark scorers/trackers built in Phase 1:
  1A — Extended BenchmarkHarness (benchmark_type, idempotency, timing)
  1B — OperatorEscapeTracker
  1C — OrchestrationQualityScorer
  1D — GovernanceQualityScorer
  1E — CompanyOpsScorer
  1F — Multi-surface atomic approval (claim/resolve/status)
  1G — Harness comparison (RouteRecommendation, profiles)
  1H — SurfaceSwitchingScorer
"""

from __future__ import annotations

import os
import tempfile
import threading
import time

import pytest


# ── 1A: Extended BenchmarkHarness ─────────────────────────────


def test_1a_benchmark_type_field():
    from substrate.organism.benchmark_harness import BenchmarkHarness

    with tempfile.TemporaryDirectory() as td:
        path = os.path.join(td, "bench.jsonl")
        h = BenchmarkHarness(store_path=path)
        h.start_cycle("c1", "governed", "test", benchmark_type="E")
        m = h.end_cycle("c1", "governed")
        assert m.benchmark_type == "E"


def test_1a_idempotency_dedup():
    from substrate.organism.benchmark_harness import BenchmarkHarness

    with tempfile.TemporaryDirectory() as td:
        path = os.path.join(td, "bench.jsonl")
        h = BenchmarkHarness(store_path=path)

        h.start_cycle("c1", "governed", "task")
        m = h.end_cycle("c1", "governed")
        key = m.idempotency_key

        h2 = BenchmarkHarness(store_path=path)
        assert len(h2.all_records()) == 1, "Same idempotency key should not duplicate"


def test_1a_timing_fields():
    from substrate.organism.benchmark_harness import BenchmarkHarness

    with tempfile.TemporaryDirectory() as td:
        path = os.path.join(td, "bench.jsonl")
        h = BenchmarkHarness(store_path=path)
        h.start_cycle("c1", "governed", "task")
        m = h.end_cycle("c1", "governed", spine_submit_ms=5.0, governance_check_ms=2.0)
        assert m.spine_submit_ms == 5.0
        assert m.governance_check_ms == 2.0


def test_1a_campaign_verdict():
    from substrate.organism.benchmark_harness import BenchmarkHarness

    with tempfile.TemporaryDirectory() as td:
        path = os.path.join(td, "bench.jsonl")
        h = BenchmarkHarness(store_path=path)
        h.start_cycle("c1", "governed", "task", benchmark_type="A")
        h.end_cycle("c1", "governed")
        verdict = h.campaign_verdict()
        assert isinstance(verdict, dict)
        assert "verdict" in verdict
        assert "benchmark_type" in verdict


# ── 1B: OperatorEscapeTracker ────────────────────────────────


def test_1b_record_and_summary():
    from substrate.organism.operator_escape_tracker import OperatorEscapeTracker

    with tempfile.TemporaryDirectory() as td:
        path = os.path.join(td, "escapes.jsonl")
        tracker = OperatorEscapeTracker(store_path=path)

        tracker.record_escape(
            destination="raw_ssh",
            reason="quick debug",
            surface_before="cli",
        )
        assert len(tracker.get_events()) == 1

        s = tracker.summary()
        assert s["total_escapes"] == 1
        assert s["top_destinations"][0][0] == "raw_ssh"


def test_1b_escape_rate():
    from substrate.organism.operator_escape_tracker import OperatorEscapeTracker

    with tempfile.TemporaryDirectory() as td:
        path = os.path.join(td, "escapes.jsonl")
        tracker = OperatorEscapeTracker(store_path=path)

        tracker.record_escape(
            destination="manual_cc",
            reason="bypass",
            surface_before="cli",
        )
        rate = tracker.escape_rate(window_hours=8.0)
        assert rate > 0


def test_1b_persistence():
    from substrate.organism.operator_escape_tracker import OperatorEscapeTracker

    with tempfile.TemporaryDirectory() as td:
        path = os.path.join(td, "escapes.jsonl")
        t1 = OperatorEscapeTracker(store_path=path)
        t1.record_escape(
            destination="raw_ssh",
            reason="test",
            surface_before="cockpit",
        )
        t2 = OperatorEscapeTracker(store_path=path)
        assert len(t2.get_events()) == 1


# ── 1C: OrchestrationQualityScorer ───────────────────────────


def test_1c_score_decision():
    from substrate.organism.benchmarks.orchestration_quality import (
        OrchestrationDecision,
        OrchestrationQualityScorer,
    )

    with tempfile.TemporaryDirectory() as td:
        path = os.path.join(td, "orch.jsonl")
        scorer = OrchestrationQualityScorer(store_path=path)
        d = OrchestrationDecision(
            task_description="deploy cockpit",
            harness_correct=True,
            model_correct=True,
            adapter_correct=True,
            decomposition_correct=True,
            recovery_needed=False,
            verification_correct=True,
        )
        score = scorer.score_decision(d)
        assert score.composite == 1.0


def test_1c_suboptimal_score():
    from substrate.organism.benchmarks.orchestration_quality import (
        OrchestrationDecision,
        OrchestrationQualityScorer,
    )

    with tempfile.TemporaryDirectory() as td:
        path = os.path.join(td, "orch.jsonl")
        scorer = OrchestrationQualityScorer(store_path=path)
        d = OrchestrationDecision(
            task_description="manual task",
            harness_selected="wrong",
            harness_correct=False,
            model_correct=False,
            adapter_correct=True,
            decomposition_correct=True,
            recovery_needed=True,
            recovery_succeeded=False,
            verification_correct=False,
        )
        score = scorer.score_decision(d)
        assert score.composite < 0.5


# ── 1D: GovernanceQualityScorer ──────────────────────────────


def test_1d_score_assessment():
    from substrate.organism.benchmarks.governance_quality import (
        GovernanceAssessment,
        GovernanceQualityScorer,
    )

    with tempfile.TemporaryDirectory() as td:
        path = os.path.join(td, "gov.jsonl")
        scorer = GovernanceQualityScorer(store_path=path)
        a = GovernanceAssessment(
            task_description="deploy",
            approval_correct=True,
            blast_radius_correct=True,
            policies_adhered=True,
            audit_trail_complete=True,
            replay_attempted=True,
            replay_succeeded=True,
        )
        score = scorer.score_assessment(a)
        assert score.composite == 1.0


def test_1d_ungoverned_score():
    from substrate.organism.benchmarks.governance_quality import (
        GovernanceAssessment,
        GovernanceQualityScorer,
    )

    with tempfile.TemporaryDirectory() as td:
        path = os.path.join(td, "gov.jsonl")
        scorer = GovernanceQualityScorer(store_path=path)
        a = GovernanceAssessment(
            task_description="direct push",
            approval_correct=False,
            blast_radius_correct=False,
            policies_adhered=False,
            audit_trail_complete=False,
            audit_has_intent=False,
            audit_has_decision=False,
            audit_has_execution=False,
            audit_has_outcome=False,
            audit_has_learning=False,
            replay_attempted=True,
            replay_succeeded=False,
        )
        score = scorer.score_assessment(a)
        assert score.composite == 0.0


# ── 1E: CompanyOpsScorer ─────────────────────────────────────


def test_1e_score_task():
    from substrate.organism.benchmarks.company_ops import (
        CompanyOpsScorer,
        CompanyOpsTask,
    )

    with tempfile.TemporaryDirectory() as td:
        path = os.path.join(td, "ops.jsonl")
        scorer = CompanyOpsScorer(store_path=path)

        task = CompanyOpsTask(
            company="test_co",
            operation_type="outreach",
            automated_steps=8,
            required_human_steps=2,
            governance_applied=True,
            proof_generated=True,
            external_facing=True,
        )
        score = scorer.record_task(task)
        assert score.automation_ratio == 0.8
        assert score.governance_score == 1.0
        assert score.safety_score == 1.0


def test_1e_data_loss_penalty():
    from substrate.organism.benchmarks.company_ops import (
        CompanyOpsScorer,
        CompanyOpsTask,
    )

    with tempfile.TemporaryDirectory() as td:
        path = os.path.join(td, "ops.jsonl")
        scorer = CompanyOpsScorer(store_path=path)

        task = CompanyOpsTask(
            company="test_co",
            operation_type="fulfillment",
            automated_steps=5,
            required_human_steps=0,
            data_loss=True,
        )
        score = scorer.record_task(task)
        assert score.safety_score == 0.0


# ── 1F: Multi-Surface Atomic Approval ────────────────────────


def test_1f_claim_approval():
    from substrate.organism.approval_gate import OperatorApprovalGate

    with tempfile.TemporaryDirectory() as td:
        gate = OperatorApprovalGate(store_dir=td)
        pkt = gate.create_packet(
            candidate_id="c1", candidate_source="test",
            candidate_title="Test", candidate_description="desc",
            candidate_evidence=[], matched_template_id="t1",
            matched_template_type="endpoint", template_confidence=0.9,
            governance_score=0.85, governance_decision="approve",
            governance_dimensions=[], affected_files=["a.py"],
            expected_delta="add endpoint", validation_plan="pytest",
            rollback_plan="revert",
        )
        assert gate.claim_approval(pkt.packet_id, "cockpit") is True
        assert gate.claim_approval(pkt.packet_id, "discord") is False


def test_1f_resolve_approval():
    from substrate.organism.approval_gate import OperatorApprovalGate, ApprovalStatus

    with tempfile.TemporaryDirectory() as td:
        gate = OperatorApprovalGate(store_dir=td)
        pkt = gate.create_packet(
            candidate_id="c2", candidate_source="test",
            candidate_title="Resolve", candidate_description="desc",
            candidate_evidence=[], matched_template_id="t1",
            matched_template_type="endpoint", template_confidence=0.9,
            governance_score=0.85, governance_decision="approve",
            governance_dimensions=[], affected_files=[],
            expected_delta="", validation_plan="", rollback_plan="",
        )
        assert gate.claim_approval(pkt.packet_id, "cockpit") is True
        assert gate.resolve_approval(pkt.packet_id, "approve", "cockpit") is True

        status = gate.get_approval_status(pkt.packet_id)
        assert status["found"] is True
        assert status["status"] == "approved"
        assert status["resolved_by_surface"] == "cockpit"


def test_1f_cross_surface_reject():
    from substrate.organism.approval_gate import OperatorApprovalGate

    with tempfile.TemporaryDirectory() as td:
        gate = OperatorApprovalGate(store_dir=td)
        pkt = gate.create_packet(
            candidate_id="c3", candidate_source="test",
            candidate_title="Cross", candidate_description="",
            candidate_evidence=[], matched_template_id="t1",
            matched_template_type="", template_confidence=0.5,
            governance_score=0.5, governance_decision="review",
            governance_dimensions=[], affected_files=[],
            expected_delta="", validation_plan="", rollback_plan="",
        )
        assert gate.claim_approval(pkt.packet_id, "cockpit") is True
        assert gate.resolve_approval(pkt.packet_id, "approve", "discord") is False


def test_1f_concurrent_claim():
    from substrate.organism.approval_gate import OperatorApprovalGate

    with tempfile.TemporaryDirectory() as td:
        gate = OperatorApprovalGate(store_dir=td)
        pkt = gate.create_packet(
            candidate_id="c4", candidate_source="test",
            candidate_title="Race", candidate_description="",
            candidate_evidence=[], matched_template_id="t1",
            matched_template_type="", template_confidence=0.5,
            governance_score=0.5, governance_decision="review",
            governance_dimensions=[], affected_files=[],
            expected_delta="", validation_plan="", rollback_plan="",
        )

        results = []

        def try_claim(surface):
            results.append(gate.claim_approval(pkt.packet_id, surface))

        threads = [
            threading.Thread(target=try_claim, args=(f"surface_{i}",))
            for i in range(5)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert sum(results) == 1, "Exactly one surface should win the CAS race"


def test_1f_get_approval_status_not_found():
    from substrate.organism.approval_gate import OperatorApprovalGate

    with tempfile.TemporaryDirectory() as td:
        gate = OperatorApprovalGate(store_dir=td)
        status = gate.get_approval_status("nonexistent")
        assert status["found"] is False


# ── 1G: Harness Comparison Framework ────────────────────────


def test_1g_harness_profiles_complete():
    from substrate.organism.benchmarks.harness_superiority import (
        ExecutionHarness,
        HARNESS_PROFILES,
    )

    for h in ExecutionHarness:
        if h == ExecutionHarness.COMPUTER_USE:
            continue
        assert h.value in HARNESS_PROFILES, f"Missing profile for {h.value}"


def test_1g_recommend_harness():
    from substrate.organism.benchmarks.harness_superiority import recommend_harness

    r = recommend_harness("business_op")
    assert r.recommended_harness == "umh_native"
    assert r.umh_role == "native"

    r2 = recommend_harness("simple_code")
    assert r2.umh_role == "skip_governance"


def test_1g_complexity_upgrade():
    from substrate.organism.benchmarks.harness_superiority import recommend_harness

    r = recommend_harness("simple_code", complexity="high")
    assert r.umh_role == "govern_verify"


def test_1g_unknown_task_fallback():
    from substrate.organism.benchmarks.harness_superiority import recommend_harness

    r = recommend_harness("never_seen_this")
    assert r.confidence == 0.5
    assert r.umh_role == "govern_verify"


def test_1g_route_table():
    from substrate.organism.benchmarks.harness_superiority import get_route_table

    table = get_route_table()
    assert len(table) >= 8
    types = {r.task_type for r in table}
    assert "business_op" in types
    assert "schema_migration" in types


# ── 1H: SurfaceSwitchingScorer ───────────────────────────────


def test_1h_score_switch():
    from substrate.organism.benchmarks.surface_switching import (
        SurfaceSwitchEvent,
        SurfaceSwitchingScorer,
    )

    with tempfile.TemporaryDirectory() as td:
        path = os.path.join(td, "switches.jsonl")
        scorer = SurfaceSwitchingScorer(store_path=path)

        event = SurfaceSwitchEvent(
            from_surface="cockpit",
            to_surface="cli",
            context_restored_pct=95.0,
            resume_time_seconds=2.0,
            objectives_preserved=True,
            work_packets_preserved=True,
            memory_continuous=True,
            execution_continuous=True,
        )
        score = scorer.score_switch(event)
        assert score > 0.8


def test_1h_data_loss_penalty():
    from substrate.organism.benchmarks.surface_switching import (
        SurfaceSwitchEvent,
        SurfaceSwitchingScorer,
    )

    with tempfile.TemporaryDirectory() as td:
        path = os.path.join(td, "switches.jsonl")
        scorer = SurfaceSwitchingScorer(store_path=path)

        event = SurfaceSwitchEvent(
            from_surface="cockpit",
            to_surface="mobile",
            context_restored_pct=0.0,
            resume_time_seconds=120.0,
            objectives_preserved=False,
            work_packets_preserved=False,
            memory_continuous=False,
            execution_continuous=False,
        )
        score = scorer.score_switch(event)
        assert score < 0.3
