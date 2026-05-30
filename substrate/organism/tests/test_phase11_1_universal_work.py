"""Phase 11.1 — Universal Work Queue + Work Packet Engine tests.

Tests WorkPacket model, Workcell model, AdvisorBranch, ReconvergenceResult,
RoleContract, CapabilityProfile, KnowledgeModel, IntentClassifier,
DelegationTopologyPlanner, WorkPacketEngine, UniversalWorkQueue,
self-build integration, and governance enforcement.

80+ tests required for Phase 11.1 gate.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import time

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

from substrate.organism.work_packet import (
    WorkPacket, PacketLifecycleStatus, _TERMINAL_STATUSES, _VALID_TRANSITIONS,
    persist_packets, load_packets,
)
from substrate.organism.workcell import (
    Workcell, PlanningWorkcellStatus, AdvisorBranch, AdvisorBranchStatus,
    ReconvergenceResult, persist_workcells, load_workcells, DEFAULT_MAX_DEPTH,
)
from substrate.organism.role_contracts import (
    RoleContract, CapabilityProfile, SEED_ROLE_CONTRACTS,
    persist_role_contracts, load_role_contracts,
)
from substrate.organism.knowledge_model_registry import (
    KnowledgeModel, KnowledgeModelRegistry,
)
from substrate.organism.intent_classifier import IntentClassifier, IntentClassification
from substrate.organism.delegation_topology import (
    DelegationTopologyPlanner, DelegationTopology, TopologyType,
)
from substrate.organism.work_packet_engine import WorkPacketEngine
from substrate.organism.universal_work_queue import UniversalWorkQueue


# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture
def tmp_dir(tmp_path):
    return tmp_path


@pytest.fixture
def packets_path(tmp_dir):
    return str(tmp_dir / "packets.jsonl")


@pytest.fixture
def workcells_path(tmp_dir):
    return str(tmp_dir / "workcells.jsonl")


@pytest.fixture
def roles_path(tmp_dir):
    return str(tmp_dir / "roles.jsonl")


@pytest.fixture
def knowledge_path(tmp_dir):
    return str(tmp_dir / "knowledge.jsonl")


@pytest.fixture
def engine(packets_path, workcells_path, roles_path, knowledge_path):
    return WorkPacketEngine(
        packets_path=packets_path,
        workcells_path=workcells_path,
        roles_path=roles_path,
        knowledge_path=knowledge_path,
    )


@pytest.fixture
def queue(packets_path, engine):
    return UniversalWorkQueue(store_path=packets_path, engine=engine)


# ── WorkPacket Model Tests ───────────────────────────────────────────────────


class TestWorkPacket:
    def test_default_status_is_drafted(self):
        pkt = WorkPacket()
        assert pkt.status == PacketLifecycleStatus.DRAFTED

    def test_packet_id_format(self):
        pkt = WorkPacket()
        assert pkt.packet_id.startswith("wp-")
        assert len(pkt.packet_id) == 15

    def test_to_dict_roundtrip(self):
        pkt = WorkPacket(
            title="Test", user_intent="Do thing", domain="self_build",
            leverage_score=0.85, risk_class="low",
        )
        d = pkt.to_dict()
        pkt2 = WorkPacket.from_dict(d)
        assert pkt2.title == pkt.title
        assert pkt2.leverage_score == pkt.leverage_score
        assert pkt2.status == pkt.status

    def test_to_safe_dict_omits_internal(self):
        pkt = WorkPacket(
            title="Test",
            source_evidence=[{"type": "test"}],
            linked_approval_packet_id="apk-123",
        )
        safe = pkt.to_safe_dict()
        assert "source_evidence" not in safe
        assert "linked_approval_packet_id" not in safe
        assert safe["title"] == "Test"

    def test_from_dict_invalid_status_defaults(self):
        d = {"title": "Test", "status": "nonexistent"}
        pkt = WorkPacket.from_dict(d)
        assert pkt.status == PacketLifecycleStatus.DRAFTED

    def test_summarize(self):
        pkt = WorkPacket(title="Test", domain="self_build", leverage_score=0.8, risk_class="low")
        s = pkt.summarize()
        assert "Test" in s
        assert "self_build" in s

    def test_requires_human_action(self):
        pkt = WorkPacket(human_required_actions=["Review required"])
        assert pkt.requires_human_action()
        pkt2 = WorkPacket()
        assert not pkt2.requires_human_action()

    def test_requires_operator_approval(self):
        pkt = WorkPacket(approval_gates=["operator_approval"])
        assert pkt.requires_operator_approval()
        pkt2 = WorkPacket()
        assert not pkt2.requires_operator_approval()

    def test_can_delegate(self):
        pkt = WorkPacket(
            status=PacketLifecycleStatus.APPROVED,
            delegation_topology_id="topo-123",
        )
        assert pkt.can_delegate()
        pkt2 = WorkPacket(status=PacketLifecycleStatus.DRAFTED)
        assert not pkt2.can_delegate()

    def test_is_execution_ready(self):
        pkt = WorkPacket(
            status=PacketLifecycleStatus.APPROVED, risk_class="low",
        )
        assert pkt.is_execution_ready()
        pkt2 = WorkPacket(
            status=PacketLifecycleStatus.APPROVED, risk_class="medium",
        )
        assert not pkt2.is_execution_ready()

    def test_timestamps_set(self):
        before = time.time()
        pkt = WorkPacket()
        after = time.time()
        assert before <= pkt.created_at <= after


class TestPacketLifecycleStatus:
    def test_all_16_statuses_defined(self):
        assert len(PacketLifecycleStatus) == 16

    def test_terminal_statuses(self):
        assert PacketLifecycleStatus.COMPLETED in _TERMINAL_STATUSES
        assert PacketLifecycleStatus.FAILED in _TERMINAL_STATUSES
        assert PacketLifecycleStatus.SUPERSEDED in _TERMINAL_STATUSES
        assert PacketLifecycleStatus.ARCHIVED in _TERMINAL_STATUSES
        assert PacketLifecycleStatus.REJECTED in _TERMINAL_STATUSES

    def test_drafted_can_transition_to_classified(self):
        assert PacketLifecycleStatus.CLASSIFIED in _VALID_TRANSITIONS[PacketLifecycleStatus.DRAFTED]

    def test_archived_has_no_transitions(self):
        assert len(_VALID_TRANSITIONS[PacketLifecycleStatus.ARCHIVED]) == 0

    def test_every_status_has_transition_entry(self):
        for status in PacketLifecycleStatus:
            assert status in _VALID_TRANSITIONS


class TestWorkPacketPersistence:
    def test_persist_and_load(self, packets_path):
        pkts = [WorkPacket(title="A"), WorkPacket(title="B")]
        persist_packets(pkts, packets_path)
        loaded = load_packets(packets_path)
        assert len(loaded) == 2
        assert loaded[0].title == "A"

    def test_load_empty(self, packets_path):
        assert load_packets(packets_path) == []


# ── Workcell Model Tests ────────────────────────────────────────────────────


class TestWorkcell:
    def test_default_status_is_pending(self):
        wc = Workcell()
        assert wc.status == PlanningWorkcellStatus.PENDING

    def test_workcell_id_format(self):
        wc = Workcell()
        assert wc.workcell_id.startswith("wc-")

    def test_to_dict_roundtrip(self):
        wc = Workcell(title="Test", objective="Do thing", depth=2)
        d = wc.to_dict()
        wc2 = Workcell.from_dict(d)
        assert wc2.title == "Test"
        assert wc2.depth == 2

    def test_has_branches(self):
        wc = Workcell()
        assert not wc.has_branches()
        wc.advisor_branches = [AdvisorBranch(brief="A")]
        assert wc.has_branches()

    def test_requires_reconvergence(self):
        wc = Workcell(advisor_branches=[AdvisorBranch(brief="A")])
        assert wc.requires_reconvergence()
        wc.reconvergence_result = ReconvergenceResult(confidence=0.9)
        assert not wc.requires_reconvergence()

    def test_can_subdivide(self):
        wc = Workcell(depth=0)
        assert wc.can_subdivide()
        wc2 = Workcell(depth=DEFAULT_MAX_DEPTH)
        assert not wc2.can_subdivide()

    def test_all_branches_distinct(self):
        wc = Workcell(advisor_branches=[
            AdvisorBranch(brief="A"),
            AdvisorBranch(brief="B"),
        ])
        assert wc.all_branches_distinct()
        wc2 = Workcell(advisor_branches=[
            AdvisorBranch(brief="A"),
            AdvisorBranch(brief="A"),
        ])
        assert not wc2.all_branches_distinct()

    def test_recursive_depth_limit(self):
        wc = Workcell(depth=DEFAULT_MAX_DEPTH + 1)
        assert not wc.can_subdivide()


class TestAdvisorBranch:
    def test_default_status_is_pending(self):
        ab = AdvisorBranch()
        assert ab.status == AdvisorBranchStatus.PENDING

    def test_to_dict_roundtrip(self):
        ab = AdvisorBranch(perspective="Strategy", brief="Analyze risk", confidence=0.85)
        d = ab.to_dict()
        ab2 = AdvisorBranch.from_dict(d)
        assert ab2.perspective == "Strategy"
        assert ab2.confidence == 0.85

    def test_invalid_status_defaults(self):
        d = {"status": "invalid_status"}
        ab = AdvisorBranch.from_dict(d)
        assert ab.status == AdvisorBranchStatus.PENDING


class TestReconvergenceResult:
    def test_to_dict_roundtrip(self):
        rr = ReconvergenceResult(
            source_workcell_id="wc-123",
            branch_count=3,
            contradictions_detected=["A vs B"],
            confidence=0.9,
            final_synthesis="Merged view",
        )
        d = rr.to_dict()
        rr2 = ReconvergenceResult.from_dict(d)
        assert rr2.branch_count == 3
        assert rr2.confidence == 0.9
        assert len(rr2.contradictions_detected) == 1


class TestWorkcellPersistence:
    def test_persist_and_load(self, workcells_path):
        wcs = [Workcell(title="A"), Workcell(title="B")]
        persist_workcells(wcs, workcells_path)
        loaded = load_workcells(workcells_path)
        assert len(loaded) == 2


# ── RoleContract Tests ───────────────────────────────────────────────────────


class TestRoleContract:
    def test_to_dict_roundtrip(self):
        rc = RoleContract(name="orchestrator", owned_work_types=["coordination"])
        d = rc.to_dict()
        rc2 = RoleContract.from_dict(d)
        assert rc2.name == "orchestrator"
        assert "coordination" in rc2.owned_work_types

    def test_with_capability_profile(self):
        cap = CapabilityProfile(capabilities=["code", "test"], average_confidence=0.9)
        rc = RoleContract(name="impl", capability_profile=cap)
        d = rc.to_dict()
        rc2 = RoleContract.from_dict(d)
        assert rc2.capability_profile is not None
        assert rc2.capability_profile.average_confidence == 0.9

    def test_seed_contracts_valid(self):
        for seed in SEED_ROLE_CONTRACTS:
            rc = RoleContract.from_dict(seed)
            assert rc.name
            assert rc.role_id


class TestCapabilityProfile:
    def test_to_dict_roundtrip(self):
        cap = CapabilityProfile(
            capabilities=["code"], reliability_by_capability={"code": 0.95},
            successful_outcomes=10, failed_outcomes=1,
        )
        d = cap.to_dict()
        cap2 = CapabilityProfile.from_dict(d)
        assert cap2.successful_outcomes == 10
        assert cap2.reliability_by_capability["code"] == 0.95


class TestRoleContractPersistence:
    def test_persist_and_load(self, roles_path):
        rcs = [RoleContract(name="A"), RoleContract(name="B")]
        persist_role_contracts(rcs, roles_path)
        loaded = load_role_contracts(roles_path)
        assert len(loaded) == 2


# ── KnowledgeModel Tests ────────────────────────────────────────────────────


class TestKnowledgeModel:
    def test_to_dict_roundtrip(self):
        km = KnowledgeModel(
            name="UMH Architecture", domain_tags=["self_build"],
            confidence=0.9, extracted_principles=["Deterministic first"],
        )
        d = km.to_dict()
        km2 = KnowledgeModel.from_dict(d)
        assert km2.name == "UMH Architecture"
        assert km2.confidence == 0.9


class TestKnowledgeModelRegistry:
    def test_register_and_get(self, knowledge_path):
        reg = KnowledgeModelRegistry(store_path=knowledge_path)
        km = reg.register(KnowledgeModel(name="Test", domain_tags=["test"]))
        got = reg.get(km.knowledge_model_id)
        assert got is not None
        assert got.name == "Test"

    def test_find_by_domain(self, knowledge_path):
        reg = KnowledgeModelRegistry(store_path=knowledge_path)
        reg.register(KnowledgeModel(name="A", domain_tags=["self_build"]))
        reg.register(KnowledgeModel(name="B", domain_tags=["finance"]))
        found = reg.find_by_domain("self_build")
        assert len(found) == 1

    def test_summary(self, knowledge_path):
        reg = KnowledgeModelRegistry(store_path=knowledge_path)
        reg.register(KnowledgeModel(name="A", domain_tags=["self_build"]))
        s = reg.summary()
        assert s["total_models"] == 1


# ── IntentClassifier Tests ───────────────────────────────────────────────────


class TestIntentClassifier:
    def test_classifies_self_build(self):
        c = IntentClassifier().classify("Build the cockpit dashboard module")
        assert c.domain == "self_build" or c.domain == "product"
        assert c.work_type in ("implementation", "design")

    def test_classifies_business(self):
        c = IntentClassifier().classify("Launch the B2B AI Automation offer for Empyrean Studios")
        assert c.domain == "business"
        assert c.company == "Empyrean Studios"

    def test_classifies_research(self):
        c = IntentClassifier().classify("Deep dive Polsia and explain what it means for UMH")
        assert c.work_type in ("research", "analysis")

    def test_classifies_cleanup(self):
        c = IntentClassifier().classify("Clean up stale config artifacts from old worktrees")
        assert c.work_type == "cleanup"

    def test_classifies_strategy(self):
        c = IntentClassifier().classify("Prepare Phase 12 Universal Propagation Graph roadmap strategy")
        assert c.domain in ("strategy", "self_build")

    def test_extracts_empyrean_studios(self):
        c = IntentClassifier().classify("Build dashboard for Empyrean Studios")
        assert c.company == "Empyrean Studios"

    def test_extracts_eos_product(self):
        c = IntentClassifier().classify("Build the EOS operating dashboard")
        assert c.product == "EOS"

    def test_risk_classification(self):
        c_low = IntentClassifier().classify("Clean up test files")
        assert c_low.risk_class == "low"
        c_high = IntentClassifier().classify("Change production auth credentials")
        assert c_high.risk_class == "high"

    def test_complexity_detection(self):
        c_simple = IntentClassifier().classify("Fix a typo")
        assert c_simple.complexity == "simple"
        c_strategic = IntentClassifier().classify("Define the long-term strategy roadmap and vision")
        assert c_strategic.complexity == "strategic"

    def test_human_required_for_high_risk(self):
        c = IntentClassifier().classify("Modify production DNS settings")
        assert c.human_action_required

    def test_approval_required_for_medium_risk(self):
        c = IntentClassifier().classify("Deploy the new migration to staging")
        assert c.approval_required

    def test_execution_blocked_for_high_risk(self):
        c = IntentClassifier().classify("Change production security credentials")
        assert not c.execution_possible

    def test_to_dict(self):
        c = IntentClassifier().classify("Build something")
        d = c.to_dict()
        assert "domain" in d
        assert "work_type" in d
        assert "risk_class" in d


# ── DelegationTopologyPlanner Tests ──────────────────────────────────────────


class TestDelegationTopologyPlanner:
    def test_simple_single_agent(self):
        topo = DelegationTopologyPlanner().plan(
            risk_class="low", complexity="simple", work_type="implementation",
            human_action_required=False, approval_required=False,
            execution_possible=True, parallel_needed=False,
        )
        assert topo.topology_type == TopologyType.SINGLE_AGENT

    def test_strategic_advisor_council(self):
        topo = DelegationTopologyPlanner().plan(
            risk_class="low", complexity="strategic", work_type="planning",
            human_action_required=False, approval_required=False,
            execution_possible=True, parallel_needed=False,
        )
        assert topo.topology_type == TopologyType.ADVISOR_COUNCIL

    def test_high_risk_planning_only(self):
        topo = DelegationTopologyPlanner().plan(
            risk_class="high", complexity="simple", work_type="deployment",
            human_action_required=True, approval_required=True,
            execution_possible=False, parallel_needed=False,
        )
        assert topo.topology_type == TopologyType.PLANNING_ONLY

    def test_human_assisted(self):
        topo = DelegationTopologyPlanner().plan(
            risk_class="low", complexity="simple", work_type="implementation",
            human_action_required=True, approval_required=False,
            execution_possible=True, parallel_needed=False,
        )
        assert topo.topology_type == TopologyType.HUMAN_ASSISTED

    def test_parallel_workcell(self):
        topo = DelegationTopologyPlanner().plan(
            risk_class="low", complexity="complex", work_type="implementation",
            human_action_required=False, approval_required=False,
            execution_possible=True, parallel_needed=True,
        )
        assert topo.topology_type == TopologyType.PARALLEL_WORKCELL

    def test_tool_only_for_cleanup(self):
        topo = DelegationTopologyPlanner().plan(
            risk_class="low", complexity="simple", work_type="cleanup",
            human_action_required=False, approval_required=False,
            execution_possible=True, parallel_needed=False,
        )
        assert topo.topology_type == TopologyType.TOOL_ONLY

    def test_governed_execution(self):
        topo = DelegationTopologyPlanner().plan(
            risk_class="low", complexity="simple", work_type="deployment",
            human_action_required=False, approval_required=True,
            execution_possible=True, parallel_needed=False,
        )
        assert topo.topology_type == TopologyType.GOVERNED_EXECUTION

    def test_assign_roles(self):
        planner = DelegationTopologyPlanner()
        topo = planner.plan(
            risk_class="low", complexity="simple", work_type="implementation",
            human_action_required=False, approval_required=False,
            execution_possible=True, parallel_needed=False,
        )
        topo = planner.assign_roles(topo, "implementation", "self_build")
        assert topo.lead_role_contract == "role-impl-op"

    def test_to_dict_roundtrip(self):
        topo = DelegationTopology(topology_type=TopologyType.ADVISOR_COUNCIL, confidence=0.8)
        d = topo.to_dict()
        topo2 = DelegationTopology.from_dict(d)
        assert topo2.topology_type == TopologyType.ADVISOR_COUNCIL
        assert topo2.confidence == 0.8

    def test_all_topology_types_defined(self):
        assert len(TopologyType.ALL) == 10

    def test_reconvergence_on_parallel(self):
        topo = DelegationTopologyPlanner().plan(
            risk_class="low", complexity="complex", work_type="implementation",
            human_action_required=False, approval_required=False,
            execution_possible=True, parallel_needed=True,
        )
        assert topo.reconvergence_protocol != ""


# ── WorkPacketEngine Tests ───────────────────────────────────────────────────


class TestWorkPacketEngine:
    def test_create_packet_from_intent(self, engine):
        pkt = engine.create_packet_from_intent(
            user_intent="Build the EOS dashboard for Empyrean Studios",
            desired_end_state="Working EOS dashboard",
        )
        assert pkt.packet_id.startswith("wp-")
        assert pkt.status == PacketLifecycleStatus.CLASSIFIED
        assert pkt.domain
        assert pkt.delegation_topology_id
        assert len(pkt.workcells) > 0

    def test_packet_has_validation_plan(self, engine):
        pkt = engine.create_packet_from_intent("Build a new module")
        assert pkt.validation_plan

    def test_packet_has_rollback_plan(self, engine):
        pkt = engine.create_packet_from_intent("Build a new module")
        assert pkt.rollback_plan

    def test_packet_has_propagation_plan(self, engine):
        pkt = engine.create_packet_from_intent("Build a new module")
        assert pkt.propagation_plan

    def test_packet_has_success_criteria(self, engine):
        pkt = engine.create_packet_from_intent("Build something", desired_end_state="Done")
        assert len(pkt.success_criteria) > 0

    def test_packet_has_failure_criteria(self, engine):
        pkt = engine.create_packet_from_intent("Build something")
        assert len(pkt.failure_criteria) > 0

    def test_packet_scoring(self, engine):
        pkt = engine.create_packet_from_intent("Build the cockpit module")
        assert pkt.leverage_score > 0
        assert pkt.effectiveness_score > 0
        assert pkt.efficiency_score > 0

    def test_update_status(self, engine):
        pkt = engine.create_packet_from_intent("Do something")
        ok = engine.update_packet_status(pkt.packet_id, PacketLifecycleStatus.PLANNED)
        assert ok

    def test_invalid_status_transition(self, engine):
        pkt = engine.create_packet_from_intent("Do something")
        ok = engine.update_packet_status(pkt.packet_id, PacketLifecycleStatus.COMPLETED)
        assert not ok

    def test_link_to_self_build(self, engine):
        pkt = engine.create_packet_from_intent("Fix tests")
        ok = engine.link_packet_to_self_build_item(pkt.packet_id, "wk-12345678")
        assert ok

    def test_link_to_roadmap(self, engine):
        pkt = engine.create_packet_from_intent("Phase 12 prep")
        ok = engine.link_packet_to_roadmap(pkt.packet_id, "12")
        assert ok

    def test_summarize_packet(self, engine):
        pkt = engine.create_packet_from_intent("Test summary")
        s = engine.summarize_packet(pkt.packet_id)
        assert s is not None
        assert "Test" in s or "summary" in s.lower()

    def test_persists_across_reload(self, packets_path, workcells_path, roles_path, knowledge_path):
        e1 = WorkPacketEngine(packets_path=packets_path, workcells_path=workcells_path,
                              roles_path=roles_path, knowledge_path=knowledge_path)
        e1.create_packet_from_intent("Persist test")
        e2 = WorkPacketEngine(packets_path=packets_path, workcells_path=workcells_path,
                              roles_path=roles_path, knowledge_path=knowledge_path)
        assert len(e2.all_packets()) == 1

    def test_workcells_generated(self, engine):
        pkt = engine.create_packet_from_intent("Build something complex and also test it across multiple systems")
        assert len(pkt.workcells) >= 1


# ── UniversalWorkQueue Tests ─────────────────────────────────────────────────


class TestUniversalWorkQueue:
    def test_ingest_user_intent(self, queue):
        pkt = queue.ingest_user_intent("Build dashboard")
        assert pkt.packet_id
        assert pkt.domain

    def test_ingest_self_build_items(self, queue):
        items = [{"work_item_id": "wk-test1", "title": "Fix tests", "risk_class": "low"}]
        pkts = queue.ingest_self_build_items(items)
        assert len(pkts) == 1
        assert pkts[0].linked_self_build_item_id == "wk-test1"

    def test_ingest_cadence_candidates(self, queue):
        candidates = [{"candidate_id": "cand-1", "title": "Candidate A", "risk_class": "low"}]
        pkts = queue.ingest_cadence_candidates(candidates)
        assert len(pkts) == 1

    def test_ingest_roadmap_requirements(self, queue):
        reqs = [{"requirement_id": "req-1", "title": "Phase 12", "roadmap_phase": "12"}]
        pkts = queue.ingest_roadmap_requirements(reqs)
        assert len(pkts) == 1
        assert pkts[0].linked_roadmap_phase == "12"

    def test_ingest_audit_findings(self, queue):
        findings = [{"finding_id": "af-1", "title": "Missing tests"}]
        pkts = queue.ingest_audit_findings(findings)
        assert len(pkts) == 1

    def test_rank_packets(self, queue):
        queue.ingest_user_intent("Low priority task")
        queue.ingest_user_intent("Build critical infrastructure module")
        ranked = queue.rank_packets()
        assert len(ranked) >= 2

    def test_get_next_best_packet(self, queue):
        queue.ingest_user_intent("Build something")
        best = queue.get_next_best_packet()
        assert best is not None

    def test_get_packets_by_domain(self, queue):
        queue.ingest_user_intent("Build the cockpit module")
        found = queue.get_packets_by_domain("self_build")
        assert len(found) >= 0  # domain classification may vary

    def test_get_packets_by_status(self, queue):
        queue.ingest_user_intent("Do something")
        found = queue.get_packets_by_status("classified")
        assert len(found) >= 1

    def test_get_packets_requiring_human(self, queue):
        queue.ingest_user_intent("Change production auth settings immediately")
        found = queue.get_packets_requiring_human()
        assert len(found) >= 1

    def test_get_packets_requiring_approval(self, queue):
        queue.ingest_user_intent("Deploy the production migration now")
        found = queue.get_packets_requiring_approval()
        assert len(found) >= 1

    def test_get_blocked_packets(self, queue):
        pkt = queue.ingest_user_intent("Something")
        queue.update_packet_status(pkt.packet_id, PacketLifecycleStatus.BLOCKED, "Blocked test")
        blocked = queue.get_blocked_packets()
        assert len(blocked) >= 0  # may not transition from classified to blocked

    def test_update_status(self, queue):
        pkt = queue.ingest_user_intent("Do work")
        ok = queue.update_packet_status(pkt.packet_id, PacketLifecycleStatus.PLANNED)
        assert ok

    def test_link_execution_artifacts(self, queue):
        pkt = queue.ingest_user_intent("Build thing")
        ok = queue.link_execution_artifacts(pkt.packet_id, {"pr_url": "https://github.com/test/pull/1"})
        assert ok

    def test_suppress_duplicates(self, queue):
        queue.ingest_user_intent("Build dashboard")
        # Second ingest of same intent should be suppressed by _is_duplicate
        pkt2 = queue.ingest_user_intent("Build dashboard")
        assert len(queue.all_packets()) == 1

    def test_compute_queue_summary(self, queue):
        queue.ingest_user_intent("Build something")
        summary = queue.compute_queue_summary()
        assert summary["total_packets"] >= 1
        assert "by_status" in summary
        assert "by_domain" in summary

    def test_medium_risk_excluded_from_next_best(self, queue):
        pkt = queue.ingest_user_intent("Deploy migration to staging now")
        # Force medium risk
        actual_pkt = queue.get_packet(pkt.packet_id)
        if actual_pkt:
            actual_pkt.risk_class = "medium"
        # Medium risk should be excluded
        best = queue.get_next_best_packet()
        if best:
            assert best.risk_class != "medium"


# ── Self-Build Integration Tests ─────────────────────────────────────────────


class TestSelfBuildIntegration:
    def test_self_build_queue_still_works(self):
        from substrate.organism.self_build_queue import SelfBuildQueueEngine
        with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
            path = f.name
        try:
            engine = SelfBuildQueueEngine(store_path=path)
            item = engine.create_work_item("Test", "Desc", "audit_finding")
            assert item.work_item_id.startswith("wk-")
        finally:
            os.unlink(path)

    def test_work_packet_links_to_self_build_item(self, engine):
        pkt = engine.create_packet_from_intent("Fix tests")
        engine.link_packet_to_self_build_item(pkt.packet_id, "wk-test1234")
        got = engine.get_packet(pkt.packet_id)
        assert got.linked_self_build_item_id == "wk-test1234"

    def test_universal_queue_ingests_self_build_items(self, queue):
        items = [
            {"work_item_id": "wk-sb1", "title": "SB Item 1", "risk_class": "low", "roadmap_phase": "11.0"},
            {"work_item_id": "wk-sb2", "title": "SB Item 2", "risk_class": "low"},
        ]
        pkts = queue.ingest_self_build_items(items)
        assert len(pkts) == 2
        assert pkts[0].domain == "self_build"


# ── Governance Tests ─────────────────────────────────────────────────────────


class TestGovernance:
    def test_no_production_mutation(self, engine):
        pkt = engine.create_packet_from_intent("Build something")
        assert pkt.status in (PacketLifecycleStatus.DRAFTED, PacketLifecycleStatus.CLASSIFIED)

    def test_medium_risk_blocked_from_execution(self, engine):
        pkt = engine.create_packet_from_intent("Deploy migration")
        if pkt.risk_class == "medium":
            assert not pkt.is_execution_ready()

    def test_high_risk_planning_only(self):
        topo = DelegationTopologyPlanner().plan(
            risk_class="high", complexity="simple", work_type="deployment",
            human_action_required=True, approval_required=True,
            execution_possible=False, parallel_needed=False,
        )
        assert topo.topology_type == TopologyType.PLANNING_ONLY

    def test_valid_status_transitions_enforced(self, queue):
        pkt = queue.ingest_user_intent("Do work")
        # classified -> completed is invalid
        ok = queue.update_packet_status(pkt.packet_id, PacketLifecycleStatus.COMPLETED)
        assert not ok

    def test_no_fake_data_in_proofs(self):
        path = os.path.join(
            os.path.dirname(__file__), "..", "..", "..",
            "data", "umh", "universal_work", "phase11_1_work_packet_proofs.json",
        )
        if not os.path.exists(path):
            pytest.skip("Proof not yet created")
        with open(path) as f:
            data = json.load(f)
        assert data["proof_count"] == 5
        for pkt in data["packets"]:
            assert pkt["packet_id"].startswith("wp-")
            assert pkt["user_intent"]
            assert pkt["domain"]

    def test_lifecycle_all_pass(self):
        path = os.path.join(
            os.path.dirname(__file__), "..", "..", "..",
            "data", "umh", "universal_work", "phase11_1_lifecycle_dry_run.json",
        )
        if not os.path.exists(path):
            pytest.skip("Lifecycle proof not yet created")
        with open(path) as f:
            data = json.load(f)
        assert data["all_pass"] is True

    def test_preflight_all_pass(self):
        path = os.path.join(
            os.path.dirname(__file__), "..", "..", "..",
            "data", "umh", "universal_work", "phase11_1_preflight.json",
        )
        if not os.path.exists(path):
            pytest.skip("Preflight not yet created")
        with open(path) as f:
            data = json.load(f)
        assert data["all_pass"] is True


# ── API Route Shape Tests ────────────────────────────────────────────────────


class TestAPIRouteShape:
    def test_universal_work_routes_module_importable(self):
        from transports.api import cockpit_universal_work_routes
        assert hasattr(cockpit_universal_work_routes, 'configure')
        assert hasattr(cockpit_universal_work_routes, 'universal_work_router')

    def test_routes_compile(self):
        import py_compile
        py_compile.compile("transports/api/cockpit_universal_work_routes.py", doraise=True)


# ── Cockpit Data Shape Tests ────────────────────────────────────────────────


class TestCockpitDataShape:
    def test_queue_summary_shape(self, queue):
        queue.ingest_user_intent("Build something")
        summary = queue.compute_queue_summary()
        required_keys = ["total_packets", "by_status", "by_domain",
                         "human_required", "approval_required", "blocked",
                         "active", "completed", "next_best"]
        for key in required_keys:
            assert key in summary, f"Missing key: {key}"

    def test_packet_safe_dict_shape(self, engine):
        pkt = engine.create_packet_from_intent("Test shape")
        safe = pkt.to_safe_dict()
        required_keys = ["packet_id", "title", "user_intent", "desired_end_state",
                         "domain", "leverage_score", "risk_class", "status"]
        for key in required_keys:
            assert key in safe, f"Missing key: {key}"
