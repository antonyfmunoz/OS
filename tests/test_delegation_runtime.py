"""Tests for Campaign 4.7 — Delegation Runtime."""
from __future__ import annotations

import os
import sys
import tempfile

sys.path.insert(0, os.environ.get("UMH_ROOT", "/opt/OS"))

import pytest
from substrate.organism.delegation_runtime import (
    DelegationMission,
    DelegationMissionStatus,
    DelegationProposal,
    DelegationRuntime,
    NestedOrchestratorState,
    OperatorIntentType,
    classify_intent,
)


@pytest.fixture
def runtime():
    """A DelegationRuntime backed by an isolated temp store."""
    store = tempfile.mkdtemp()
    return DelegationRuntime(store_dir=store)


def _make_mission(rt: DelegationRuntime) -> DelegationMission:
    """Create a proposal, approve it, return the queued mission."""
    proposal = rt.propose_delegation("Use Clerk auth for CreatorOS")
    mission = rt.approve_proposal(proposal.proposal_id)
    assert mission is not None
    return mission


class TestIntentClassification:
    def test_discussion_lets_talk(self):
        assert classify_intent("Let's talk about auth") == OperatorIntentType.DISCUSSION

    def test_discussion_what_do_you_think(self):
        assert classify_intent("What do you think about Clerk?") == OperatorIntentType.DISCUSSION

    def test_discussion_brainstorm(self):
        assert classify_intent("Let's brainstorm options") == OperatorIntentType.DISCUSSION

    def test_question_what_are(self):
        assert classify_intent("What are the pros and cons?") == OperatorIntentType.QUESTION

    def test_question_how_does(self):
        assert classify_intent("How does the auth middleware work?") == OperatorIntentType.QUESTION

    def test_question_should_we(self):
        assert classify_intent("Should we use Clerk?") == OperatorIntentType.QUESTION

    def test_question_mark(self):
        assert classify_intent("Is this ready?") == OperatorIntentType.QUESTION

    def test_decision_i_think(self):
        assert classify_intent("I think we should use Clerk") == OperatorIntentType.DECISION

    def test_decision_lets_go(self):
        assert classify_intent("Let's go with OAuth") == OperatorIntentType.DECISION

    def test_work_intent_use(self):
        assert classify_intent("Use Clerk auth for CreatorOS") == OperatorIntentType.WORK_INTENT

    def test_work_intent_add(self):
        assert classify_intent("Add rate limiting to the API") == OperatorIntentType.WORK_INTENT

    def test_work_intent_build(self):
        assert classify_intent("Build a new authentication panel") == OperatorIntentType.WORK_INTENT

    def test_work_intent_migrate(self):
        assert classify_intent("Migrate from JWT to Clerk") == OperatorIntentType.WORK_INTENT

    def test_work_intent_integrate(self):
        assert classify_intent("Integrate Stripe with the billing system") == OperatorIntentType.WORK_INTENT

    def test_approval_approve(self):
        assert classify_intent("Approve") == OperatorIntentType.APPROVAL

    def test_approval_yes_go(self):
        assert classify_intent("Yes, go ahead") == OperatorIntentType.APPROVAL

    def test_approval_rejected(self):
        assert classify_intent("Reject this") == OperatorIntentType.APPROVAL

    def test_execution_deploy(self):
        assert classify_intent("Deploy it now") == OperatorIntentType.EXECUTION

    def test_execution_run(self):
        assert classify_intent("Run the tests") == OperatorIntentType.EXECUTION

    def test_execution_ship(self):
        assert classify_intent("Ship it") == OperatorIntentType.EXECUTION

    def test_empty_string(self):
        assert classify_intent("") == OperatorIntentType.DISCUSSION


class TestDelegationProposal:
    def test_propose_creates_proposal(self, runtime):
        p = runtime.propose_delegation("Use Clerk auth for CreatorOS")
        assert isinstance(p, DelegationProposal)
        assert p.proposal_id
        assert p.operator_intent == "Use Clerk auth for CreatorOS"
        assert p.proposed_title
        assert p.proposed_scope
        assert p.why_delegate

    def test_proposal_has_topology_preview(self, runtime):
        p = runtime.propose_delegation("Use Clerk auth for CreatorOS")
        assert isinstance(p.topology_preview, dict)
        assert p.topology_preview

    def test_proposal_has_understanding(self, runtime):
        understanding = {"affected_systems": ["auth"], "affected_projection": "CreatorOS"}
        p = runtime.propose_delegation("Use Clerk auth for CreatorOS", understanding=understanding)
        assert p.understanding == understanding

    def test_proposal_status_pending(self, runtime):
        p = runtime.propose_delegation("Use Clerk auth for CreatorOS")
        assert p.status == "pending"

    def test_proposal_persisted(self, runtime):
        p = runtime.propose_delegation("Use Clerk auth for CreatorOS")
        ids = [d["proposal_id"] for d in runtime.list_proposals()]
        assert p.proposal_id in ids

    def test_orchestrator_keeps_populated(self, runtime):
        p = runtime.propose_delegation("Use Clerk auth for CreatorOS")
        assert p.what_orchestrator_keeps

    def test_gets_delegated_populated(self, runtime):
        p = runtime.propose_delegation("Use Clerk auth for CreatorOS")
        assert p.what_gets_delegated


class TestProposalLifecycle:
    def test_approve_creates_mission(self, runtime):
        p = runtime.propose_delegation("Use Clerk auth for CreatorOS")
        mission = runtime.approve_proposal(p.proposal_id)
        assert isinstance(mission, DelegationMission)

    def test_approve_mission_queued(self, runtime):
        p = runtime.propose_delegation("Use Clerk auth for CreatorOS")
        mission = runtime.approve_proposal(p.proposal_id)
        assert mission.status == DelegationMissionStatus.QUEUED

    def test_approve_links_proposal(self, runtime):
        p = runtime.propose_delegation("Use Clerk auth for CreatorOS")
        mission = runtime.approve_proposal(p.proposal_id)
        assert mission.proposal_id == p.proposal_id

    def test_reject_marks_rejected(self, runtime):
        p = runtime.propose_delegation("Use Clerk auth for CreatorOS")
        result = runtime.reject_proposal(p.proposal_id)
        assert result is not None
        assert result.status == "rejected"

    def test_reject_with_reason(self, runtime):
        p = runtime.propose_delegation("Use Clerk auth for CreatorOS")
        result = runtime.reject_proposal(p.proposal_id, reason="not now")
        assert result.understanding.get("rejection_reason") == "not now"

    def test_approve_nonexistent(self, runtime):
        assert runtime.approve_proposal("dp-doesnotexist") is None

    def test_double_approve(self, runtime):
        p = runtime.propose_delegation("Use Clerk auth for CreatorOS")
        runtime.approve_proposal(p.proposal_id)
        assert runtime.approve_proposal(p.proposal_id) is None

    def test_reject_after_approve(self, runtime):
        p = runtime.propose_delegation("Use Clerk auth for CreatorOS")
        runtime.approve_proposal(p.proposal_id)
        assert runtime.reject_proposal(p.proposal_id) is None


class TestMissionLifecycle:
    def test_claim_creates_nested_orchestrator(self, runtime):
        mission = _make_mission(runtime)
        nested = runtime.claim_mission(mission.mission_id)
        assert isinstance(nested, NestedOrchestratorState)

    def test_claim_sets_status_claimed(self, runtime):
        mission = _make_mission(runtime)
        runtime.claim_mission(mission.mission_id)
        assert runtime._missions[mission.mission_id].status == DelegationMissionStatus.CLAIMED

    def test_claim_respects_max_concurrent(self, runtime):
        missions = [_make_mission(runtime) for _ in range(4)]
        claimed = [runtime.claim_mission(m.mission_id) for m in missions]
        assert sum(1 for c in claimed if c is not None) == runtime._max_concurrent
        assert claimed[runtime._max_concurrent] is None

    def test_submit_wp_draft(self, runtime):
        mission = _make_mission(runtime)
        runtime.claim_mission(mission.mission_id)
        result = runtime.submit_work_packet_draft(mission.mission_id, {"plan": "x"})
        assert result is not None
        assert runtime._missions[mission.mission_id].status == DelegationMissionStatus.WORK_PACKET_DRAFTED

    def test_approve_wp(self, runtime):
        mission = _make_mission(runtime)
        runtime.claim_mission(mission.mission_id)
        runtime.submit_work_packet_draft(mission.mission_id, {"plan": "x"})
        result = runtime.approve_work_packet(mission.mission_id)
        assert result is not None
        assert runtime._missions[mission.mission_id].status == DelegationMissionStatus.WORK_PACKET_APPROVED

    def test_start_execution(self, runtime):
        mission = _make_mission(runtime)
        runtime.claim_mission(mission.mission_id)
        runtime.submit_work_packet_draft(mission.mission_id, {"plan": "x"})
        runtime.approve_work_packet(mission.mission_id)
        result = runtime.start_execution(mission.mission_id)
        assert result is not None
        assert runtime._missions[mission.mission_id].status == DelegationMissionStatus.EXECUTING

    def test_complete_mission(self, runtime):
        mission = _make_mission(runtime)
        runtime.claim_mission(mission.mission_id)
        runtime.submit_work_packet_draft(mission.mission_id, {"plan": "x"})
        runtime.approve_work_packet(mission.mission_id)
        runtime.start_execution(mission.mission_id)
        result = runtime.complete_mission(mission.mission_id, {"outcome": "done"})
        assert result is not None
        assert result.status == DelegationMissionStatus.COMPLETED
        assert result.metadata["result"] == {"outcome": "done"}

    def test_fail_mission(self, runtime):
        mission = _make_mission(runtime)
        runtime.claim_mission(mission.mission_id)
        result = runtime.fail_mission(mission.mission_id, reason="broke")
        assert result is not None
        assert result.status == DelegationMissionStatus.FAILED
        assert result.metadata["failure_reason"] == "broke"

    def test_cancel_queued(self, runtime):
        mission = _make_mission(runtime)
        result = runtime.cancel_mission(mission.mission_id)
        assert result is not None
        assert result.status == DelegationMissionStatus.CANCELLED

    def test_cancel_claimed(self, runtime):
        mission = _make_mission(runtime)
        runtime.claim_mission(mission.mission_id)
        result = runtime.cancel_mission(mission.mission_id)
        assert result is not None
        assert result.status == DelegationMissionStatus.CANCELLED

    def test_invalid_transition(self, runtime):
        mission = _make_mission(runtime)
        # QUEUED → EXECUTING is not a valid transition.
        with pytest.raises(ValueError):
            mission.transition(DelegationMissionStatus.EXECUTING)


class TestQueueManagement:
    def test_queue_status_fields(self, runtime):
        status = runtime.queue_status()
        assert "queue_depth" in status
        assert "active_count" in status
        assert "max_concurrent" in status

    def test_queue_ordering(self, runtime):
        # Build a low-priority and a critical-priority mission directly.
        low = DelegationMission(title="low", priority="low", status=DelegationMissionStatus.QUEUED)
        crit = DelegationMission(title="crit", priority="critical", status=DelegationMissionStatus.QUEUED)
        runtime._missions[low.mission_id] = low
        runtime._missions[crit.mission_id] = crit
        queued = runtime.queue_status()["queued_missions"]
        order = [m["mission_id"] for m in queued]
        assert order.index(crit.mission_id) < order.index(low.mission_id)

    def test_process_queue_claims(self, runtime):
        missions = [_make_mission(runtime) for _ in range(2)]
        claimed = runtime.process_queue()
        assert set(claimed) == {m.mission_id for m in missions}

    def test_process_queue_respects_limit(self, runtime):
        for _ in range(5):
            _make_mission(runtime)
        claimed = runtime.process_queue()
        assert len(claimed) == runtime._max_concurrent


class TestExecutionResolution:
    def test_resolve_with_approved_wp(self, runtime):
        mission = _make_mission(runtime)
        runtime.claim_mission(mission.mission_id)
        runtime.submit_work_packet_draft(mission.mission_id, {"plan": "x"})
        runtime.approve_work_packet(mission.mission_id)
        result = runtime.resolve_execution_intent("Deploy it now")
        assert result["resolution"] == "existing_work_packet"
        assert result["mission_id"] == mission.mission_id

    def test_resolve_without_wp(self, runtime):
        result = runtime.resolve_execution_intent("Deploy it now")
        assert result["resolution"] == "needs_work_packet"

    def test_execution_never_direct(self, runtime):
        # With an approved WP: governed start path, not direct execution.
        mission = _make_mission(runtime)
        runtime.claim_mission(mission.mission_id)
        runtime.submit_work_packet_draft(mission.mission_id, {"plan": "x"})
        runtime.approve_work_packet(mission.mission_id)
        with_wp = runtime.resolve_execution_intent("Ship it")
        assert with_wp["action"] in ("start_execution", "propose_delegation")
        assert "direct" not in with_wp.get("action", "")
        # Without an approved WP: must route through proposal, never direct.
        rt2 = DelegationRuntime(store_dir=tempfile.mkdtemp())
        without_wp = rt2.resolve_execution_intent("Ship it")
        assert without_wp["action"] == "propose_delegation"


class TestPersistence:
    def test_missions_persist_and_reload(self):
        store = tempfile.mkdtemp()
        rt = DelegationRuntime(store_dir=store)
        mission = _make_mission(rt)
        rt2 = DelegationRuntime(store_dir=store)
        assert rt2.get_mission(mission.mission_id) is not None

    def test_proposals_persist_and_reload(self):
        store = tempfile.mkdtemp()
        rt = DelegationRuntime(store_dir=store)
        p = rt.propose_delegation("Use Clerk auth for CreatorOS")
        rt2 = DelegationRuntime(store_dir=store)
        assert rt2.get_proposal(p.proposal_id) is not None


class TestExplainUnderstanding:
    def test_work_intent_returns_understanding(self, runtime):
        u = runtime.explain_understanding(
            "Use Clerk auth for CreatorOS", OperatorIntentType.WORK_INTENT,
        )
        assert u
        assert "affected_systems" in u

    def test_discussion_returns_empty(self, runtime):
        u = runtime.explain_understanding(
            "Let's talk about auth", OperatorIntentType.DISCUSSION,
        )
        assert u == {}


class TestQueryInterface:
    def test_list_proposals_all(self, runtime):
        runtime.propose_delegation("Use Clerk auth for CreatorOS")
        runtime.propose_delegation("Add rate limiting to the API")
        assert len(runtime.list_proposals()) == 2

    def test_list_proposals_filtered(self, runtime):
        p1 = runtime.propose_delegation("Use Clerk auth for CreatorOS")
        runtime.propose_delegation("Add rate limiting to the API")
        runtime.reject_proposal(p1.proposal_id)
        rejected = runtime.list_proposals(status="rejected")
        assert len(rejected) == 1
        assert rejected[0]["proposal_id"] == p1.proposal_id

    def test_list_missions_all(self, runtime):
        _make_mission(runtime)
        _make_mission(runtime)
        assert len(runtime.list_missions()) == 2

    def test_active_missions(self, runtime):
        active = _make_mission(runtime)
        done = _make_mission(runtime)
        runtime.cancel_mission(done.mission_id)
        active_ids = [m["mission_id"] for m in runtime.active_missions()]
        assert active.mission_id in active_ids
        assert done.mission_id not in active_ids

    def test_summary_counts(self, runtime):
        _make_mission(runtime)
        runtime.propose_delegation("Add rate limiting to the API")
        summary = runtime.summary()
        assert summary["total_missions"] == 1
        assert summary["pending_proposals"] == 1
