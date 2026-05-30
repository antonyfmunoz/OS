"""Phase 11.0 — Self-Build Engineering Queue tests.

Tests SelfBuildWorkItem model, SelfBuildQueueEngine, RoadmapEngine,
governance mapping, status transitions, duplicate suppression,
ranking, artifact linking, and lifecycle correctness.

60+ tests required for Phase 11.0 gate.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import time

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

from substrate.organism.self_build_queue import (
    SelfBuildQueueEngine,
    SelfBuildWorkItem,
    WorkItemSourceType,
    WorkItemStatus,
    _TERMINAL_STATUSES,
    _VALID_TRANSITIONS,
)
from substrate.organism.roadmap_engine import RoadmapEngine, RoadmapPhase


# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture
def tmp_store(tmp_path):
    return str(tmp_path / "items.jsonl")


@pytest.fixture
def tmp_roadmap(tmp_path):
    return str(tmp_path / "roadmap.jsonl")


@pytest.fixture
def engine(tmp_store):
    return SelfBuildQueueEngine(store_path=tmp_store)


@pytest.fixture
def roadmap(tmp_roadmap):
    return RoadmapEngine(store_path=tmp_roadmap)


def _make_candidate(cid: str = "cse-test-1", **kwargs):
    base = {
        "candidate_id": cid,
        "title": f"Test candidate {cid}",
        "description": "Test desc",
        "weighted_score": 0.85,
        "promotion_class": "execute_ready_low_risk",
        "risk_class": "low",
        "template_id": "tpl-seed-test-repair-01",
        "agent_type": "developer_agent",
        "affected_files": ["tests/test_example.py"],
        "validation_plan": "py_compile",
        "rollback_plan": "git revert",
    }
    base.update(kwargs)
    return base


# ── SelfBuildWorkItem Model Tests ─────────────────────────────────────────────


class TestSelfBuildWorkItem:
    def test_default_status_is_discovered(self):
        item = SelfBuildWorkItem()
        assert item.status == WorkItemStatus.DISCOVERED

    def test_work_item_id_format(self):
        item = SelfBuildWorkItem()
        assert item.work_item_id.startswith("wk-")
        assert len(item.work_item_id) == 11  # wk- + 8 hex chars

    def test_to_dict_roundtrip(self):
        item = SelfBuildWorkItem(
            title="Test",
            description="Desc",
            source_type="audit_finding",
            risk_class="low",
            weighted_score=0.75,
        )
        d = item.to_dict()
        item2 = SelfBuildWorkItem.from_dict(d)
        assert item2.title == item.title
        assert item2.weighted_score == item.weighted_score
        assert item2.status == item.status

    def test_to_safe_dict_omits_internal(self):
        item = SelfBuildWorkItem(
            title="Test",
            source_evidence=[{"type": "test", "data": {"secret": "x"}}],
            approval_packet_id="apk-12345678",
        )
        safe = item.to_safe_dict()
        assert "source_evidence" not in safe
        assert "approval_packet_id" not in safe
        assert safe["title"] == "Test"

    def test_from_dict_invalid_status_defaults(self):
        d = {"title": "Test", "status": "nonexistent_status"}
        item = SelfBuildWorkItem.from_dict(d)
        assert item.status == WorkItemStatus.DISCOVERED

    def test_from_dict_preserves_all_fields(self):
        item = SelfBuildWorkItem(
            title="Full",
            description="Desc",
            source_type="roadmap_requirement",
            linked_candidate_id="cand-1",
            linked_template_id="tpl-1",
            linked_agent_type="developer_agent",
            risk_class="low",
            promotion_class="execute_ready_low_risk",
            roadmap_phase="11.0",
            operator_notes="Test note",
        )
        d = item.to_dict()
        item2 = SelfBuildWorkItem.from_dict(d)
        assert item2.linked_candidate_id == "cand-1"
        assert item2.roadmap_phase == "11.0"
        assert item2.operator_notes == "Test note"

    def test_timestamps_set_on_creation(self):
        before = time.time()
        item = SelfBuildWorkItem()
        after = time.time()
        assert before <= item.created_at <= after
        assert before <= item.updated_at <= after


# ── WorkItemStatus Tests ──────────────────────────────────────────────────────


class TestWorkItemStatus:
    def test_all_20_statuses_defined(self):
        assert len(WorkItemStatus) == 20

    def test_terminal_statuses(self):
        assert WorkItemStatus.RESOLVED in _TERMINAL_STATUSES
        assert WorkItemStatus.FAILED in _TERMINAL_STATUSES
        assert WorkItemStatus.SUPERSEDED in _TERMINAL_STATUSES
        assert WorkItemStatus.ARCHIVED in _TERMINAL_STATUSES
        assert WorkItemStatus.REJECTED in _TERMINAL_STATUSES

    def test_discovered_can_transition_to_ranked(self):
        assert WorkItemStatus.RANKED in _VALID_TRANSITIONS[WorkItemStatus.DISCOVERED]

    def test_archived_has_no_transitions(self):
        assert len(_VALID_TRANSITIONS[WorkItemStatus.ARCHIVED]) == 0

    def test_every_status_has_transition_entry(self):
        for status in WorkItemStatus:
            assert status in _VALID_TRANSITIONS


# ── WorkItemSourceType Tests ──────────────────────────────────────────────────


class TestWorkItemSourceType:
    def test_all_13_source_types_defined(self):
        assert len(WorkItemSourceType) == 13

    def test_key_source_types_exist(self):
        assert WorkItemSourceType.RELIABILITY_RANKED_CANDIDATE.value == "reliability_ranked_candidate"
        assert WorkItemSourceType.AUDIT_FINDING.value == "audit_finding"
        assert WorkItemSourceType.ROADMAP_REQUIREMENT.value == "roadmap_requirement"
        assert WorkItemSourceType.OPERATOR_REQUEST.value == "operator_request"
        assert WorkItemSourceType.PRODUCT_PROJECTION_NEED.value == "product_projection_need"


# ── SelfBuildQueueEngine Tests ────────────────────────────────────────────────


class TestQueueEngineCreation:
    def test_engine_initializes_empty(self, engine):
        assert len(engine.all_items()) == 0

    def test_engine_creates_store_dir(self, tmp_path):
        sp = str(tmp_path / "sub" / "dir" / "items.jsonl")
        engine = SelfBuildQueueEngine(store_path=sp)
        engine.create_work_item("Test", "Desc", "audit_finding")
        assert os.path.exists(sp)

    def test_engine_persists_across_reload(self, tmp_store):
        e1 = SelfBuildQueueEngine(store_path=tmp_store)
        e1.create_work_item("Persist", "Desc", "audit_finding", source_id="persist-1")
        e2 = SelfBuildQueueEngine(store_path=tmp_store)
        assert len(e2.all_items()) == 1
        assert e2.all_items()[0].title == "Persist"


class TestCandidateIngestion:
    def test_ingest_ranked_candidates(self, engine):
        items = engine.ingest_ranked_candidates([_make_candidate()])
        assert len(items) == 1
        assert items[0].linked_candidate_id == "cse-test-1"
        assert items[0].linked_template_id == "tpl-seed-test-repair-01"

    def test_ingest_multiple_candidates(self, engine):
        candidates = [
            _make_candidate("cse-1"),
            _make_candidate("cse-2"),
            _make_candidate("cse-3"),
        ]
        items = engine.ingest_ranked_candidates(candidates)
        assert len(items) == 3

    def test_ingest_preserves_weighted_score(self, engine):
        items = engine.ingest_ranked_candidates([
            _make_candidate(weighted_score=0.92),
        ])
        assert items[0].weighted_score == 0.92


class TestAuditFindingIngestion:
    def test_ingest_audit_findings(self, engine):
        items = engine.ingest_audit_findings([{
            "finding_id": "af-1",
            "title": "Test finding",
            "description": "Desc",
            "risk_class": "low",
            "roadmap_phase": "11.0",
            "affected_subsystems": ["organism"],
        }])
        assert len(items) == 1
        assert items[0].source_type == WorkItemSourceType.AUDIT_FINDING.value
        assert items[0].roadmap_phase == "11.0"


class TestRoadmapRequirementIngestion:
    def test_ingest_roadmap_requirements(self, engine):
        items = engine.ingest_roadmap_requirements([{
            "requirement_id": "rr-1",
            "title": "Phase 12 prep",
            "description": "Desc",
            "risk_class": "low",
            "roadmap_phase": "12",
            "expected_leverage": 0.9,
        }])
        assert len(items) == 1
        assert items[0].expected_leverage == 0.9


class TestDuplicateSuppression:
    def test_duplicate_source_id_suppressed(self, engine):
        w1 = engine.create_work_item("A", "Desc", "audit_finding", source_id="dup-1")
        w2 = engine.create_work_item("B", "Desc", "audit_finding", source_id="dup-1")
        assert w1.work_item_id == w2.work_item_id
        assert len(engine.all_items()) == 1

    def test_empty_source_id_not_suppressed(self, engine):
        w1 = engine.create_work_item("A", "Desc", "audit_finding")
        w2 = engine.create_work_item("B", "Desc", "audit_finding")
        assert w1.work_item_id != w2.work_item_id

    def test_resolved_candidate_not_duplicated(self, engine):
        w1 = engine.create_work_item("A", "Desc", "audit_finding", source_id="res-1")
        engine.update_status(w1.work_item_id, WorkItemStatus.RANKED)
        engine.update_status(w1.work_item_id, WorkItemStatus.READY_FOR_APPROVAL)
        engine.update_status(w1.work_item_id, WorkItemStatus.APPROVAL_PENDING)
        engine.update_status(w1.work_item_id, WorkItemStatus.APPROVED)
        engine.update_status(w1.work_item_id, WorkItemStatus.SANDBOX_READY)
        engine.update_status(w1.work_item_id, WorkItemStatus.SANDBOX_RUNNING)
        engine.update_status(w1.work_item_id, WorkItemStatus.SANDBOX_COMPLETE)
        engine.update_status(w1.work_item_id, WorkItemStatus.PR_CREATED)
        engine.update_status(w1.work_item_id, WorkItemStatus.PR_REVIEW)
        engine.update_status(w1.work_item_id, WorkItemStatus.MERGED)
        engine.update_status(w1.work_item_id, WorkItemStatus.PRODUCTION_VERIFICATION_PENDING)
        engine.update_status(w1.work_item_id, WorkItemStatus.PRODUCTION_VERIFIED)
        engine.update_status(w1.work_item_id, WorkItemStatus.RESOLVED)
        # Now creating with same source_id should NOT be suppressed (terminal)
        w2 = engine.create_work_item("B", "Desc", "audit_finding", source_id="res-1")
        assert w2.work_item_id != w1.work_item_id


class TestStatusTransitions:
    def test_valid_transition_succeeds(self, engine):
        w = engine.create_work_item("Test", "Desc", "audit_finding")
        assert engine.update_status(w.work_item_id, WorkItemStatus.RANKED)
        assert engine.get_item(w.work_item_id).status == WorkItemStatus.RANKED

    def test_invalid_transition_fails(self, engine):
        w = engine.create_work_item("Test", "Desc", "audit_finding")
        assert not engine.update_status(w.work_item_id, WorkItemStatus.MERGED)
        assert engine.get_item(w.work_item_id).status == WorkItemStatus.DISCOVERED

    def test_full_happy_path(self, engine):
        w = engine.create_work_item("Happy", "Desc", "audit_finding", source_id="happy-1",
                                    source_evidence=[{"type": "test"}])
        path = [
            WorkItemStatus.RANKED,
            WorkItemStatus.READY_FOR_APPROVAL,
            WorkItemStatus.APPROVAL_PENDING,
            WorkItemStatus.APPROVED,
            WorkItemStatus.SANDBOX_READY,
            WorkItemStatus.SANDBOX_RUNNING,
            WorkItemStatus.SANDBOX_COMPLETE,
            WorkItemStatus.PR_CREATED,
            WorkItemStatus.PR_REVIEW,
            WorkItemStatus.MERGED,
            WorkItemStatus.PRODUCTION_VERIFICATION_PENDING,
            WorkItemStatus.PRODUCTION_VERIFIED,
            WorkItemStatus.RESOLVED,
        ]
        for status in path:
            assert engine.update_status(w.work_item_id, status), f"Failed at {status}"
        assert engine.get_item(w.work_item_id).status == WorkItemStatus.RESOLVED

    def test_blocked_can_return_to_discovered(self, engine):
        w = engine.create_work_item("Block", "Desc", "audit_finding")
        engine.update_status(w.work_item_id, WorkItemStatus.BLOCKED)
        assert engine.update_status(w.work_item_id, WorkItemStatus.DISCOVERED)

    def test_failed_can_return_to_discovered(self, engine):
        w = engine.create_work_item("Fail", "Desc", "audit_finding")
        engine.update_status(w.work_item_id, WorkItemStatus.RANKED)
        engine.update_status(w.work_item_id, WorkItemStatus.READY_FOR_APPROVAL)
        engine.update_status(w.work_item_id, WorkItemStatus.APPROVAL_PENDING)
        engine.update_status(w.work_item_id, WorkItemStatus.APPROVED)
        engine.update_status(w.work_item_id, WorkItemStatus.SANDBOX_READY)
        engine.update_status(w.work_item_id, WorkItemStatus.SANDBOX_RUNNING)
        engine.update_status(w.work_item_id, WorkItemStatus.FAILED)
        assert engine.update_status(w.work_item_id, WorkItemStatus.DISCOVERED)

    def test_nonexistent_item_returns_false(self, engine):
        assert not engine.update_status("wk-nonexist", WorkItemStatus.RANKED)


class TestBlockedTransitions:
    def test_mark_blocked_sets_reasons(self, engine):
        w = engine.create_work_item("Block", "Desc", "audit_finding")
        engine.mark_blocked(w.work_item_id, ["Dep missing", "Auth required"])
        item = engine.get_item(w.work_item_id)
        assert item.status == WorkItemStatus.BLOCKED
        assert len(item.blocked_reasons) == 2

    def test_blocked_items_appear_in_get_blocked(self, engine):
        w = engine.create_work_item("Block", "Desc", "audit_finding")
        engine.mark_blocked(w.work_item_id, ["Dep"])
        blocked = engine.get_blocked_work()
        assert len(blocked) == 1


class TestArtifactLinking:
    def test_link_approval_packet(self, engine):
        w = engine.create_work_item("Test", "Desc", "audit_finding")
        assert engine.link_approval_packet(w.work_item_id, "apk-12345678")
        assert engine.get_item(w.work_item_id).approval_packet_id == "apk-12345678"

    def test_link_sandbox(self, engine):
        w = engine.create_work_item("Test", "Desc", "audit_finding")
        assert engine.link_sandbox(w.work_item_id, "sbx-1", "auto/fix-branch")
        item = engine.get_item(w.work_item_id)
        assert item.sandbox_id == "sbx-1"
        assert item.branch_name == "auto/fix-branch"

    def test_link_pr(self, engine):
        w = engine.create_work_item("Test", "Desc", "audit_finding")
        assert engine.link_pr(w.work_item_id, "https://github.com/repo/pull/99")
        assert engine.get_item(w.work_item_id).pr_url == "https://github.com/repo/pull/99"

    def test_link_production_truth(self, engine):
        w = engine.create_work_item("Test", "Desc", "audit_finding")
        assert engine.link_production_truth(w.work_item_id, "ptd-abc123")
        assert engine.get_item(w.work_item_id).production_truth_delta_id == "ptd-abc123"

    def test_link_to_nonexistent_returns_false(self, engine):
        assert not engine.link_approval_packet("wk-fake", "apk-1")
        assert not engine.link_sandbox("wk-fake", "sbx-1")
        assert not engine.link_pr("wk-fake", "url")
        assert not engine.link_production_truth("wk-fake", "ptd-1")


class TestRanking:
    def test_rank_returns_sorted(self, engine):
        engine.create_work_item("Low", "Desc", "audit_finding",
                                weighted_score=0.3, expected_leverage=0.2)
        engine.create_work_item("High", "Desc", "audit_finding",
                                weighted_score=0.9, expected_leverage=0.8)
        ranked = engine.rank_work_items()
        assert ranked[0].weighted_score >= ranked[1].weighted_score

    def test_blocked_items_ranked_lower(self, engine):
        w1 = engine.create_work_item("Normal", "Desc", "audit_finding",
                                     weighted_score=0.5)
        w2 = engine.create_work_item("Blocked", "Desc", "audit_finding",
                                     weighted_score=0.9)
        engine.mark_blocked(w2.work_item_id, ["Dep"])
        ranked = engine.rank_work_items()
        normal = next(i for i in ranked if i.work_item_id == w1.work_item_id)
        blocked = next(i for i in ranked if i.work_item_id == w2.work_item_id)
        assert normal.weighted_score > blocked.weighted_score

    def test_medium_risk_excluded_from_next_best(self, engine):
        engine.create_work_item("Medium", "Desc", "audit_finding",
                                source_id="med-1",
                                source_evidence=[{"type": "test"}],
                                risk_class="medium", weighted_score=0.95)
        assert engine.get_next_best_work() is None


class TestEligibility:
    def test_eligible_with_evidence(self, engine):
        w = engine.create_work_item("Test", "Desc", "audit_finding",
                                    source_evidence=[{"type": "test"}])
        eligible, blockers = engine.check_eligibility(w)
        assert eligible
        assert len(blockers) == 0

    def test_ineligible_without_evidence(self, engine):
        w = engine.create_work_item("Test", "Desc", "audit_finding")
        eligible, blockers = engine.check_eligibility(w)
        assert not eligible
        assert "Missing source evidence" in blockers

    def test_medium_risk_blocked(self, engine):
        w = engine.create_work_item("Test", "Desc", "audit_finding",
                                    source_evidence=[{"type": "test"}],
                                    risk_class="medium")
        eligible, blockers = engine.check_eligibility(w)
        assert not eligible
        assert "Medium-risk execution blocked by policy" in blockers

    def test_advance_to_ready_succeeds(self, engine):
        w = engine.create_work_item("Test", "Desc", "audit_finding",
                                    source_evidence=[{"type": "test"}])
        ok, blockers = engine.advance_to_ready(w.work_item_id)
        assert ok
        assert engine.get_item(w.work_item_id).status == WorkItemStatus.READY_FOR_APPROVAL

    def test_advance_to_ready_fails_for_medium(self, engine):
        w = engine.create_work_item("Test", "Desc", "audit_finding",
                                    source_evidence=[{"type": "test"}],
                                    risk_class="medium")
        ok, blockers = engine.advance_to_ready(w.work_item_id)
        assert not ok


class TestQueueSummary:
    def test_summary_counts(self, engine):
        engine.create_work_item("A", "Desc", "audit_finding")
        engine.create_work_item("B", "Desc", "roadmap_requirement")
        summary = engine.compute_queue_summary()
        assert summary["total_items"] == 2
        assert summary["status_counts"]["discovered"] == 2

    def test_summary_includes_risk_counts(self, engine):
        engine.create_work_item("Low", "Desc", "audit_finding", risk_class="low")
        summary = engine.compute_queue_summary()
        assert "low" in summary["risk_counts"]

    def test_summary_includes_source_counts(self, engine):
        engine.create_work_item("A", "Desc", "audit_finding")
        summary = engine.compute_queue_summary()
        assert "audit_finding" in summary["source_counts"]


class TestMarkResolved:
    def test_mark_resolved_from_verified(self, engine):
        w = engine.create_work_item("Test", "Desc", "audit_finding", source_id="mr-1",
                                    source_evidence=[{"type": "test"}])
        for s in [WorkItemStatus.RANKED, WorkItemStatus.READY_FOR_APPROVAL,
                  WorkItemStatus.APPROVAL_PENDING, WorkItemStatus.APPROVED,
                  WorkItemStatus.SANDBOX_READY, WorkItemStatus.SANDBOX_RUNNING,
                  WorkItemStatus.SANDBOX_COMPLETE, WorkItemStatus.PR_CREATED,
                  WorkItemStatus.PR_REVIEW, WorkItemStatus.MERGED,
                  WorkItemStatus.PRODUCTION_VERIFICATION_PENDING,
                  WorkItemStatus.PRODUCTION_VERIFIED]:
            engine.update_status(w.work_item_id, s)
        assert engine.mark_resolved(w.work_item_id, "Complete")
        assert engine.get_item(w.work_item_id).status == WorkItemStatus.RESOLVED

    def test_mark_resolved_from_wrong_status_fails(self, engine):
        w = engine.create_work_item("Test", "Desc", "audit_finding")
        assert not engine.mark_resolved(w.work_item_id)


class TestMarkSuperseded:
    def test_mark_superseded(self, engine):
        w = engine.create_work_item("Old", "Desc", "audit_finding")
        engine.update_status(w.work_item_id, WorkItemStatus.RANKED)
        assert engine.mark_superseded(w.work_item_id, "wk-new-item")
        item = engine.get_item(w.work_item_id)
        assert item.status == WorkItemStatus.SUPERSEDED
        assert "wk-new-item" in item.status_reason


# ── RoadmapEngine Tests ──────────────────────────────────────────────────────


class TestRoadmapEngine:
    def test_add_and_get_phase(self, roadmap):
        p = roadmap.add_phase(RoadmapPhase(
            phase_id="11.0",
            title="Self-Build",
            status="active",
        ))
        got = roadmap.get_phase("11.0")
        assert got is not None
        assert got.title == "Self-Build"

    def test_link_work_item_to_phase(self, roadmap):
        roadmap.add_phase(RoadmapPhase(phase_id="11.0", title="SB"))
        assert roadmap.link_work_item("11.0", "wk-abc12345")
        phase = roadmap.get_phase("11.0")
        assert "wk-abc12345" in phase.linked_work_items

    def test_link_duplicate_item_idempotent(self, roadmap):
        roadmap.add_phase(RoadmapPhase(phase_id="11.0", title="SB"))
        roadmap.link_work_item("11.0", "wk-abc12345")
        roadmap.link_work_item("11.0", "wk-abc12345")
        assert len(roadmap.get_phase("11.0").linked_work_items) == 1

    def test_link_to_nonexistent_phase_fails(self, roadmap):
        assert not roadmap.link_work_item("99", "wk-abc12345")

    def test_update_phase_status(self, roadmap):
        roadmap.add_phase(RoadmapPhase(phase_id="11.0", title="SB", status="active"))
        roadmap.update_status("11.0", "complete")
        assert roadmap.get_phase("11.0").status == "complete"

    def test_all_phases(self, roadmap):
        roadmap.add_phase(RoadmapPhase(phase_id="11.0", title="A"))
        roadmap.add_phase(RoadmapPhase(phase_id="12", title="B"))
        assert len(roadmap.all_phases()) == 2

    def test_summary(self, roadmap):
        roadmap.add_phase(RoadmapPhase(phase_id="11.0", title="A", status="active"))
        roadmap.add_phase(RoadmapPhase(phase_id="12", title="B", status="planned"))
        s = roadmap.summary()
        assert s["total_phases"] == 2
        assert s["status_counts"]["active"] == 1

    def test_persistence(self, tmp_roadmap):
        r1 = RoadmapEngine(store_path=tmp_roadmap)
        r1.add_phase(RoadmapPhase(phase_id="11.0", title="Persist"))
        r2 = RoadmapEngine(store_path=tmp_roadmap)
        assert r2.get_phase("11.0") is not None

    def test_phase_to_dict_roundtrip(self):
        p = RoadmapPhase(
            phase_id="11.0",
            title="Test",
            objective="Obj",
            status="active",
            prerequisites=["10.5"],
            success_criteria=["SC1", "SC2"],
            unlocks=["12"],
        )
        d = p.to_dict()
        p2 = RoadmapPhase.from_dict(d)
        assert p2.phase_id == "11.0"
        assert p2.unlocks == ["12"]


# ── No Fake Data Tests ────────────────────────────────────────────────────────


class TestNoFakeData:
    def test_seeded_queue_has_real_candidates(self):
        path = os.path.join(
            os.path.dirname(__file__), "..", "..", "..",
            "data", "umh", "self_build", "phase11_0_seeded_queue.json",
        )
        if not os.path.exists(path):
            pytest.skip("Seeded queue not yet created")
        with open(path) as f:
            data = json.load(f)
        assert data["total_items"] > 0
        for src, count in data["source_counts"].items():
            assert src in [e.value for e in WorkItemSourceType]

    def test_preflight_all_pass(self):
        path = os.path.join(
            os.path.dirname(__file__), "..", "..", "..",
            "data", "umh", "self_build", "phase11_0_preflight.json",
        )
        if not os.path.exists(path):
            pytest.skip("Preflight not yet created")
        with open(path) as f:
            data = json.load(f)
        for check_name, check in data["checks"].items():
            assert check["status"] == "pass", f"Preflight check failed: {check_name}"

    def test_lifecycle_proof_all_pass(self):
        path = os.path.join(
            os.path.dirname(__file__), "..", "..", "..",
            "data", "umh", "self_build", "phase11_0_lifecycle_dry_run.json",
        )
        if not os.path.exists(path):
            pytest.skip("Lifecycle proof not yet created")
        with open(path) as f:
            data = json.load(f)
        assert data["all_pass"] is True


# ── Governance Mapping Tests ──────────────────────────────────────────────────


class TestGovernanceMapping:
    def test_approval_packet_generation(self, engine):
        from substrate.organism.approval_gate import ApprovalPacket
        w = engine.create_work_item("Test", "Desc", "audit_finding",
                                    source_evidence=[{"type": "test"}])
        packet = ApprovalPacket(
            candidate_id=w.linked_candidate_id,
            candidate_title=w.title,
            risk_class=w.risk_class,
        )
        assert packet.packet_id.startswith("apk-")
        engine.link_approval_packet(w.work_item_id, packet.packet_id)
        assert engine.get_item(w.work_item_id).approval_packet_id == packet.packet_id

    def test_medium_risk_blocked_by_policy(self, engine):
        w = engine.create_work_item("Med", "Desc", "audit_finding",
                                    source_evidence=[{"type": "test"}],
                                    risk_class="medium")
        eligible, blockers = engine.check_eligibility(w)
        assert not eligible
        assert any("Medium-risk" in b for b in blockers)


# ── Integration Tests ─────────────────────────────────────────────────────────


class TestIntegration:
    def test_queue_plus_roadmap_integration(self, engine, roadmap):
        roadmap.add_phase(RoadmapPhase(phase_id="11.0", title="SB", status="active"))
        items = engine.ingest_ranked_candidates([_make_candidate()])
        for item in items:
            item.roadmap_phase = "11.0"
            roadmap.link_work_item("11.0", item.work_item_id)
        phase = roadmap.get_phase("11.0")
        assert len(phase.linked_work_items) == 1

    def test_full_lifecycle_integration(self, engine, roadmap):
        roadmap.add_phase(RoadmapPhase(phase_id="11.0", title="SB", status="active"))
        items = engine.ingest_ranked_candidates([_make_candidate(
            cid="lifecycle-int",
        )])
        item = items[0]
        roadmap.link_work_item("11.0", item.work_item_id)
        ok, _ = engine.advance_to_ready(item.work_item_id)
        assert ok
        ready = engine.get_ready_for_approval()
        assert len(ready) == 1
        summary = engine.compute_queue_summary()
        assert summary["ready_for_approval"] == 1
