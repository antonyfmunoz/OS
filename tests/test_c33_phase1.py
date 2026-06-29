"""C33 Phase 1 exit gate tests — verify benchmark infrastructure works.

Covers:
  - 1A: BenchmarkHarness C33 extensions (benchmark_type, idempotency, between_cycle, verdict)
  - 1B: OperatorEscapeTracker (record, resolve, summary, escape_rate)
  - 1C: OrchestrationQualityScorer
  - 1D: GovernanceQualityScorer
  - 1E: CompanyOpsScorer
  - 1F: Multi-surface atomic approval (claim, resolve, CAS)
  - 1G: Harness superiority (profiles, route recommendation, complexity upgrade)
  - 1H: SurfaceSwitchingScorer
"""

from __future__ import annotations

import os
import tempfile
import threading

import pytest


# ── 1A: BenchmarkHarness C33 Extensions ──────────────────────────


def test_1a_benchmark_type_validation():
    from substrate.organism.benchmark_harness import BenchmarkHarness

    with tempfile.TemporaryDirectory() as td:
        path = os.path.join(td, "bench.jsonl")
        h = BenchmarkHarness(store_path=path)
        h.start_cycle("c1", "governed", "test", benchmark_type="A")
        m = h.end_cycle("c1", "governed")
        assert m.benchmark_type == "A"
        assert m.recorded_live is True
        assert m.idempotency_key != ""


def test_1a_idempotency_dedup():
    from substrate.organism.benchmark_harness import BenchmarkHarness

    with tempfile.TemporaryDirectory() as td:
        path = os.path.join(td, "bench.jsonl")
        h = BenchmarkHarness(store_path=path)
        h.start_cycle("c1", "governed", "test", benchmark_type="A")
        m = h.end_cycle("c1", "governed")

        h2 = BenchmarkHarness(store_path=path)
        assert len(h2.all_records()) == 1


def test_1a_between_cycle_analysis():
    from substrate.organism.benchmark_harness import BenchmarkHarness

    with tempfile.TemporaryDirectory() as td:
        path = os.path.join(td, "bench.jsonl")
        h = BenchmarkHarness(store_path=path)

        h.start_cycle("c1", "governed", "task A", benchmark_type="A")
        h.end_cycle("c1", "governed", files_changed=5)

        h.start_cycle("c2", "governed", "task B", benchmark_type="A")
        h.end_cycle("c2", "governed", files_changed=8)

        result = h.between_cycle_analysis(["c1", "c2"])
        assert result["cycle_count"] == 2
        assert len(result["improvements"]) >= 1


def test_1a_campaign_verdict():
    from substrate.organism.benchmark_harness import BenchmarkHarness

    with tempfile.TemporaryDirectory() as td:
        path = os.path.join(td, "bench.jsonl")
        h = BenchmarkHarness(store_path=path)

        h.start_cycle("c1", "governed", "test", benchmark_type="E")
        h.end_cycle("c1", "governed", files_changed=3)

        verdict = h.campaign_verdict("E")
        assert verdict["benchmark_type"] == "E"


# ── 1B: Operator Escape Tracker ──────────────────────────────────


def test_1b_record_escape():
    from substrate.organism.operator_escape_tracker import OperatorEscapeTracker

    with tempfile.TemporaryDirectory() as td:
        path = os.path.join(td, "escapes.jsonl")
        tracker = OperatorEscapeTracker(store_path=path)

        event = tracker.record_escape(
            destination="raw_ssh",
            reason="Need to run htop",
            missing_capability="system_monitoring",
        )
        assert event.event_id.startswith("esc-")
        assert event.destination == "raw_ssh"
        assert event.resolved is False


def test_1b_resolve_escape():
    from substrate.organism.operator_escape_tracker import OperatorEscapeTracker

    with tempfile.TemporaryDirectory() as td:
        path = os.path.join(td, "escapes.jsonl")
        tracker = OperatorEscapeTracker(store_path=path)

        event = tracker.record_escape(
            destination="manual_claude_code",
            reason="Complex debugging",
        )
        resolved = tracker.resolve_escape(event.event_id)
        assert resolved is True

        summary = tracker.summary()
        assert summary["total_escapes"] == 1
        assert summary["resolved"] == 1


def test_1b_escape_rate():
    from substrate.organism.operator_escape_tracker import OperatorEscapeTracker

    with tempfile.TemporaryDirectory() as td:
        path = os.path.join(td, "escapes.jsonl")
        tracker = OperatorEscapeTracker(store_path=path)

        tracker.record_escape(destination="raw_ssh", reason="test1")
        tracker.record_escape(destination="manual_edit", reason="test2")

        rate = tracker.escape_rate()
        assert isinstance(rate, float)


# ── 1C: Orchestration Quality Scorer ─────────────────────────────


def test_1c_orchestration_scoring():
    from substrate.organism.benchmarks.orchestration_quality import (
        OrchestrationDecision,
        OrchestrationQualityScorer,
    )

    with tempfile.TemporaryDirectory() as td:
        path = os.path.join(td, "orch.jsonl")
        scorer = OrchestrationQualityScorer(store_path=path)
        decision = OrchestrationDecision(
            decision_id="d1",
            task_description="Deploy cockpit",
            harness_correct=True,
            model_correct=True,
            adapter_correct=True,
            decomposition_correct=True,
            verification_correct=True,
        )
        score = scorer.score_decision(decision)
        assert score.composite == 1.0


def test_1c_critical_misroute_detection():
    from substrate.organism.benchmarks.orchestration_quality import (
        OrchestrationDecision,
        OrchestrationQualityScorer,
    )

    with tempfile.TemporaryDirectory() as td:
        path = os.path.join(td, "orch.jsonl")
        scorer = OrchestrationQualityScorer(store_path=path)
        decision = OrchestrationDecision(
            decision_id="d2",
            task_description="Schema migration",
            harness_correct=False,
            harness_selected="wrong_harness",
            model_correct=True,
            adapter_correct=True,
            decomposition_correct=True,
            verification_correct=True,
        )
        score = scorer.score_decision(decision)
        assert score.composite < 1.0
        assert score.is_critical_misroute is True


# ── 1D: Governance Quality Scorer ────────────────────────────────


def test_1d_governance_scoring():
    from substrate.organism.benchmarks.governance_quality import (
        GovernanceAssessment,
        GovernanceQualityScorer,
    )

    with tempfile.TemporaryDirectory() as td:
        path = os.path.join(td, "gov.jsonl")
        scorer = GovernanceQualityScorer(store_path=path)
        assessment = GovernanceAssessment(
            assessment_id="g1",
            envelope_id="env-001",
            approval_correct=True,
            blast_radius_correct=True,
            policies_adhered=True,
            audit_trail_complete=True,
            audit_has_intent=True,
            audit_has_decision=True,
            audit_has_execution=True,
            audit_has_outcome=True,
            audit_has_learning=True,
            replay_attempted=True,
            replay_succeeded=True,
        )
        score = scorer.score_assessment(assessment)
        assert score.composite == 1.0


# ── 1E: Company Ops Scorer ───────────────────────────────────────


def test_1e_company_ops_scoring():
    from substrate.organism.benchmarks.company_ops import (
        CompanyOpsTask,
        CompanyOpsScorer,
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
        assert score.proof_score == 1.0


# ── 1F: Multi-surface Atomic Approval ────────────────────────────


def _create_test_packet(gate):
    """Helper to create a simple pending approval packet for testing."""
    return gate.create_packet(
        candidate_id="test-cand-001",
        candidate_source="test",
        candidate_title="Test Deploy Action",
        candidate_description="Test deployment",
        candidate_evidence=[{"type": "test", "data": "test"}],
        matched_template_id="tmpl-001",
        matched_template_type="deploy",
        template_confidence=0.9,
        governance_score=0.8,
        governance_decision="approve_with_review",
        governance_dimensions=[{"dim": "risk", "score": 0.8}],
        affected_files=["test.py"],
        expected_delta="deploy test",
        validation_plan="run tests",
        rollback_plan="revert commit",
        risk_class="low",
    )


def test_1f_claim_approval():
    from substrate.organism.approval_gate import OperatorApprovalGate

    with tempfile.TemporaryDirectory() as td:
        gate = OperatorApprovalGate(store_dir=td)
        packet = _create_test_packet(gate)
        ok = gate.claim_approval(packet.packet_id, "cockpit")
        assert ok is True

        ok2 = gate.claim_approval(packet.packet_id, "discord")
        assert ok2 is False, "Second claim must fail (CAS)"


def test_1f_resolve_after_claim():
    from substrate.organism.approval_gate import OperatorApprovalGate

    with tempfile.TemporaryDirectory() as td:
        gate = OperatorApprovalGate(store_dir=td)
        packet = _create_test_packet(gate)
        gate.claim_approval(packet.packet_id, "cockpit")
        ok = gate.resolve_approval(
            packet.packet_id, "approve", "cockpit", decided_by="operator",
        )
        assert ok is True

        status = gate.get_approval_status(packet.packet_id)
        assert status["found"] is True
        assert status["decision"] == "approve"
        assert status["resolved_by_surface"] == "cockpit"


def test_1f_resolve_wrong_surface_blocked():
    from substrate.organism.approval_gate import OperatorApprovalGate

    with tempfile.TemporaryDirectory() as td:
        gate = OperatorApprovalGate(store_dir=td)
        packet = _create_test_packet(gate)
        gate.claim_approval(packet.packet_id, "cockpit")
        ok = gate.resolve_approval(
            packet.packet_id, "approve", "discord", decided_by="operator",
        )
        assert ok is False, "Resolve from non-claiming surface must fail"


def test_1f_concurrent_claims():
    """Multiple threads racing to claim — exactly one wins."""
    from substrate.organism.approval_gate import OperatorApprovalGate

    with tempfile.TemporaryDirectory() as td:
        gate = OperatorApprovalGate(store_dir=td)
        packet = _create_test_packet(gate)

        results = []
        lock = threading.Lock()
        def try_claim(surface: str) -> None:
            ok = gate.claim_approval(packet.packet_id, surface)
            with lock:
                results.append((surface, ok))

        threads = [
            threading.Thread(target=try_claim, args=(f"surface_{i}",))
            for i in range(5)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        winners = [s for s, ok in results if ok]
        assert len(winners) == 1, f"Exactly one winner expected, got {winners}"


# ── 1G: Harness Superiority ──────────────────────────────────────


def test_1g_harness_profiles():
    from substrate.organism.benchmarks.harness_superiority import (
        HARNESS_PROFILES,
        ExecutionHarness,
    )

    assert len(ExecutionHarness) == 11
    assert len(HARNESS_PROFILES) >= 10
    assert ExecutionHarness.UMH_NATIVE.value in HARNESS_PROFILES
    umh = HARNESS_PROFILES[ExecutionHarness.UMH_NATIVE.value]
    assert umh.supports_governance is True
    assert umh.supports_compounding is True


def test_1g_route_recommendation():
    from substrate.organism.benchmarks.harness_superiority import recommend_harness

    r = recommend_harness("simple_code")
    assert r.recommended_harness == "claude_code"
    assert r.umh_role == "skip_governance"
    assert r.confidence >= 0.9

    r2 = recommend_harness("business_op")
    assert r2.recommended_harness == "umh_native"
    assert r2.umh_role == "native"


def test_1g_complexity_upgrade():
    from substrate.organism.benchmarks.harness_superiority import recommend_harness

    r = recommend_harness("simple_code", "high")
    assert r.umh_role == "govern_verify", "High complexity should upgrade governance"


def test_1g_unknown_fallback():
    from substrate.organism.benchmarks.harness_superiority import recommend_harness

    r = recommend_harness("totally_new_thing")
    assert r.confidence == 0.5
    assert r.umh_role == "govern_verify"


def test_1g_route_table_complete():
    from substrate.organism.benchmarks.harness_superiority import get_route_table

    table = get_route_table()
    assert len(table) >= 8
    types = {r.task_type for r in table}
    assert "simple_code" in types
    assert "business_op" in types
    assert "schema_migration" in types


# ── 1H: Surface Switching Scorer ─────────────────────────────────


def test_1h_surface_switching_scoring():
    from substrate.organism.benchmarks.surface_switching import (
        SurfaceSwitchingScorer,
    )

    with tempfile.TemporaryDirectory() as td:
        path = os.path.join(td, "switches.jsonl")
        scorer = SurfaceSwitchingScorer(store_path=path)

        event = scorer.record_switch(
            from_surface="cockpit",
            to_surface="discord",
            context_restored_pct=95.0,
            resume_time_seconds=2.0,
            objectives_preserved=True,
            work_packets_preserved=True,
            memory_continuous=True,
            execution_continuous=True,
        )
        score = scorer.score_switch(event)
        assert score > 0.9


def test_1h_degraded_switch():
    from substrate.organism.benchmarks.surface_switching import (
        SurfaceSwitchingScorer,
    )

    with tempfile.TemporaryDirectory() as td:
        path = os.path.join(td, "switches.jsonl")
        scorer = SurfaceSwitchingScorer(store_path=path)

        event = scorer.record_switch(
            from_surface="cockpit",
            to_surface="mobile",
            context_restored_pct=40.0,
            resume_time_seconds=30.0,
            info_lost=["work_packets", "execution_state"],
            objectives_preserved=True,
            work_packets_preserved=False,
            memory_continuous=True,
            execution_continuous=False,
        )
        score = scorer.score_switch(event)
        assert score < 0.7, "Degraded switch should score low"
