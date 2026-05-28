"""Tests for the AutomationPipeline — Phase 5.9."""

from __future__ import annotations

import sys
sys.path.insert(0, "/opt/OS/.claude/worktrees/anti-divergence-gate")

from substrate.organism.event_spine import EventSpine
from substrate.organism.operator_compression import (
    InterventionType,
    OperatorAction,
    OperatorCompression,
)
from substrate.organism.automation_pipeline import (
    AutomationPipeline,
    AutomationRisk,
    CandidateStatus,
)


def _make_pipeline_with_data() -> tuple[AutomationPipeline, OperatorCompression]:
    spine = EventSpine()
    compression = OperatorCompression(event_spine=spine, promotion_threshold=2)
    pipeline = AutomationPipeline(
        operator_compression=compression,
        event_spine=spine,
    )

    for i in range(3):
        compression.record_intervention(OperatorAction(
            action_id=f"act-{i}",
            intervention_type=InterventionType.RESTART,
            description=f"Restart service {i}",
            context="docker_restart",
            duration_seconds=30.0,
        ))

    return pipeline, compression


def test_scan_finds_candidates():
    pipeline, _ = _make_pipeline_with_data()
    proposals = pipeline.scan_for_candidates()
    assert len(proposals) >= 1
    assert proposals[0].status == CandidateStatus.PROPOSED


def test_no_duplicates_on_rescan():
    pipeline, _ = _make_pipeline_with_data()
    first = pipeline.scan_for_candidates()
    second = pipeline.scan_for_candidates()
    assert len(second) == 0
    assert pipeline.to_dict()["total_proposals"] == len(first)


def test_approve_proposal():
    pipeline, _ = _make_pipeline_with_data()
    proposals = pipeline.scan_for_candidates()
    pid = proposals[0].proposal_id
    assert pipeline.approve(pid)
    p = pipeline.get_proposal(pid)
    assert p is not None
    assert p.status == CandidateStatus.APPROVED
    assert p.decided_by == "operator"


def test_deny_proposal():
    pipeline, _ = _make_pipeline_with_data()
    proposals = pipeline.scan_for_candidates()
    pid = proposals[0].proposal_id
    assert pipeline.deny(pid, reason="not needed")
    p = pipeline.get_proposal(pid)
    assert p is not None
    assert p.status == CandidateStatus.DENIED
    assert p.denial_reason == "not needed"


def test_cannot_approve_nonexistent():
    spine = EventSpine()
    compression = OperatorCompression(event_spine=spine)
    pipeline = AutomationPipeline(operator_compression=compression, event_spine=spine)
    assert not pipeline.approve("fake-id")


def test_risk_classification():
    pipeline, _ = _make_pipeline_with_data()
    proposals = pipeline.scan_for_candidates()
    for p in proposals:
        assert p.risk in (AutomationRisk.LOW, AutomationRisk.MEDIUM, AutomationRisk.HIGH)


def test_leverage_scoring():
    pipeline, _ = _make_pipeline_with_data()
    proposals = pipeline.scan_for_candidates()
    for p in proposals:
        assert 0.0 <= p.leverage_score <= 1.0


def test_pipeline_tick():
    pipeline, _ = _make_pipeline_with_data()
    result = pipeline.pipeline_tick()
    assert "new_proposals" in result
    assert result["new_proposals"] >= 1


def test_list_proposals_by_status():
    pipeline, _ = _make_pipeline_with_data()
    pipeline.scan_for_candidates()
    pending = pipeline.list_proposals(status=CandidateStatus.PROPOSED)
    assert len(pending) >= 1
    all_props = pipeline.list_proposals()
    assert len(all_props) >= len(pending)


def test_event_emission():
    spine = EventSpine()
    compression = OperatorCompression(event_spine=spine, promotion_threshold=2)
    pipeline = AutomationPipeline(operator_compression=compression, event_spine=spine)

    for i in range(3):
        compression.record_intervention(OperatorAction(
            action_id=f"act-{i}",
            intervention_type=InterventionType.APPROVAL,
            description=f"Approval {i}",
            context="approval_pattern",
            duration_seconds=10.0,
        ))

    pipeline.scan_for_candidates()
    events = spine.recent(limit=100)
    event_types = [e.event_type for e in events]
    assert "automation_proposed" in event_types
