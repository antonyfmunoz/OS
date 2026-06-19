"""Tests for C22.6 — Source Truth Runtime (CORE DELIVERABLE).

Verifies full organizational lineage: Intent → Decision → Requirement →
WorkPacket → Execution → Review → Approval → Deployment → Outcome →
Learning → Capability — cross-referencing all subsystems.
"""
from __future__ import annotations

import sys
import time
import unittest
from dataclasses import dataclass, field
from typing import Any

sys.path.insert(0, "/opt/OS")

from substrate.organism.source_truth_runtime import (
    LineageChain,
    LineageNode,
    LineageNodeType,
    LineageSummary,
    LineageTerminalState,
    SourceTruthRuntime,
)


# ── Fakes ───────────────────────────────────────────────────────────────


@dataclass
class FakeDecision:
    decision_id: str = ""
    title: str = ""
    summary: str = ""
    rationale: str = ""
    status: str = "active"
    goal_refs: list[str] = field(default_factory=list)
    project_refs: list[str] = field(default_factory=list)
    work_packet_refs: list[str] = field(default_factory=list)
    approval_refs: list[str] = field(default_factory=list)
    created_at: float = 0.0


class FakeDecisionRegistry:
    def __init__(self, decisions: list[FakeDecision] | None = None) -> None:
        self._decisions = decisions or []

    def list_decisions(self) -> list[FakeDecision]:
        return list(self._decisions)

    def get(self, decision_id: str) -> FakeDecision | None:
        for d in self._decisions:
            if d.decision_id == decision_id:
                return d
        return None


@dataclass
class FakeWorkPacket:
    packet_id: str = ""
    title: str = ""
    user_intent: str = ""
    intent_summary: str = ""
    source_type: str = "operator_request"
    source_id: str = ""
    source_evidence: list[dict[str, Any]] = field(default_factory=list)
    status: str = "drafted"
    risk_class: str = "low"
    domain: str = ""
    parent_packet_id: str = ""
    child_packet_ids: list[str] = field(default_factory=list)
    created_at: float = 0.0

    def to_safe_dict(self) -> dict[str, Any]:
        return {"packet_id": self.packet_id, "title": self.title}


class FakeWorkPacketEngine:
    def __init__(self, packets: list[FakeWorkPacket] | None = None) -> None:
        self._packets = packets or []

    def all_packets(self) -> list[FakeWorkPacket]:
        return list(self._packets)

    def get_packet(self, packet_id: str) -> FakeWorkPacket | None:
        for p in self._packets:
            if p.packet_id == packet_id:
                return p
        return None


@dataclass
class FakeExecutionPlan:
    execution_plan_id: str = ""
    source_workpacket_id: str = ""
    description: str = ""
    status: str = "drafted"
    target_executor: str = ""
    approval_state: str = "pending"
    created_at: float = 0.0


class FakeExecutionCoordinator:
    def __init__(self, plans: list[FakeExecutionPlan] | None = None) -> None:
        self._plans_list = plans or []

    def all_plans(self) -> list[FakeExecutionPlan]:
        return list(self._plans_list)


@dataclass
class FakeLesson:
    lesson_id: str = ""
    title: str = ""
    category: str = "process_improvement"
    confidence: float = 0.0
    actionable: bool = False
    related_decision_ids: list[str] = field(default_factory=list)
    related_outcome_ids: list[str] = field(default_factory=list)
    related_capability_ids: list[str] = field(default_factory=list)
    extracted_at: float = 0.0


class FakeLearningExtraction:
    def __init__(self, lessons: list[FakeLesson] | None = None) -> None:
        self._lessons = lessons or []

    def recent_lessons(self, limit: int = 500) -> list[FakeLesson]:
        return list(self._lessons[:limit])


@dataclass
class FakeEvolutionEvent:
    event_id: str = ""
    capability_id: str = ""
    event_type: str = "new_evidence"
    trigger_outcome_id: str = ""
    timestamp: float = 0.0


@dataclass
class FakeTrajectory:
    capability_id: str = ""
    current_level: str = "developing"
    trend: float = 0.0
    events: list[FakeEvolutionEvent] = field(default_factory=list)
    first_event_at: float = 0.0


class FakeCapabilityEvolution:
    def __init__(self, trajectories: list[FakeTrajectory] | None = None) -> None:
        self._trajectories = trajectories or []

    def all_trajectories(self) -> list[FakeTrajectory]:
        return list(self._trajectories)


@dataclass
class FakeConflict:
    conflict_id: str = ""
    status: str = "detected"
    detected_at: float = 0.0


class FakeGovernanceRuntime:
    def __init__(self, conflicts: list[FakeConflict] | None = None) -> None:
        self._conflicts_list = conflicts or []

    def recent_resolutions(self, limit: int = 200) -> list[FakeConflict]:
        return list(self._conflicts_list[:limit])


# ── Helpers ─────────────────────────────────────────────────────────────


def _build_runtime(
    decisions: list[FakeDecision] | None = None,
    packets: list[FakeWorkPacket] | None = None,
    plans: list[FakeExecutionPlan] | None = None,
    lessons: list[FakeLesson] | None = None,
    trajectories: list[FakeTrajectory] | None = None,
    conflicts: list[FakeConflict] | None = None,
) -> SourceTruthRuntime:
    return SourceTruthRuntime(
        decision_registry=FakeDecisionRegistry(decisions or []),
        work_packet_engine=FakeWorkPacketEngine(packets or []),
        execution_coordinator=FakeExecutionCoordinator(plans or []),
        learning_extraction=FakeLearningExtraction(lessons or []),
        capability_evolution=FakeCapabilityEvolution(trajectories or []),
        governance_runtime=FakeGovernanceRuntime(conflicts or []),
    )


def _full_chain_data() -> dict[str, Any]:
    """Build a full intent→decision→packet→execution→lesson→capability chain."""
    now = time.time()
    decisions = [FakeDecision(
        decision_id="dec-1",
        title="Build user dashboard",
        work_packet_refs=["wp-1"],
        created_at=now - 100,
    )]
    packets = [FakeWorkPacket(
        packet_id="wp-1",
        title="Implement dashboard",
        user_intent="Build user dashboard",
        source_type="operator_request",
        source_id="src-1",
        status="completed",
        created_at=now - 90,
    )]
    plans = [FakeExecutionPlan(
        execution_plan_id="exec-1",
        source_workpacket_id="wp-1",
        description="Execute dashboard build",
        status="completed",
        created_at=now - 80,
    )]
    lessons = [FakeLesson(
        lesson_id="lesson-1",
        title="Dashboard pattern works",
        related_decision_ids=["dec-1"],
        related_outcome_ids=["outcome-1"],
        related_capability_ids=["cap-1"],
        extracted_at=now - 50,
    )]
    trajectories = [FakeTrajectory(
        capability_id="cap-1",
        current_level="established",
        events=[FakeEvolutionEvent(
            event_id="ev-1",
            capability_id="cap-1",
            trigger_outcome_id="outcome-1",
        )],
        first_event_at=now - 30,
    )]
    return {
        "decisions": decisions,
        "packets": packets,
        "plans": plans,
        "lessons": lessons,
        "trajectories": trajectories,
    }


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Tests
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestLineageNodeType(unittest.TestCase):
    def test_all_11_types_exist(self) -> None:
        expected = [
            "intent", "decision", "requirement", "work_packet",
            "execution", "review", "approval", "deployment",
            "outcome", "lesson", "capability",
        ]
        for t in expected:
            self.assertIn(t, [e.value for e in LineageNodeType])

    def test_enum_count(self) -> None:
        self.assertEqual(len(LineageNodeType), 11)


class TestLineageNode(unittest.TestCase):
    def test_to_dict_roundtrip(self) -> None:
        node = LineageNode(
            node_id="test-1",
            node_type=LineageNodeType.WORK_PACKET.value,
            title="Test packet",
            source_id="wp-1",
            parent_id="decision-dec-1",
            children=["execution-exec-1"],
            created_at=1000.0,
            metadata={"status": "active"},
        )
        d = node.to_dict()
        restored = LineageNode.from_dict(d)
        self.assertEqual(restored.node_id, "test-1")
        self.assertEqual(restored.node_type, "work_packet")
        self.assertEqual(restored.parent_id, "decision-dec-1")
        self.assertEqual(restored.children, ["execution-exec-1"])

    def test_defaults(self) -> None:
        node = LineageNode()
        self.assertEqual(node.node_id, "")
        self.assertEqual(node.node_type, LineageNodeType.INTENT.value)
        self.assertEqual(node.children, [])
        self.assertEqual(node.metadata, {})


class TestLineageChain(unittest.TestCase):
    def test_to_dict_roundtrip(self) -> None:
        chain = LineageChain(
            chain_id="chain-1",
            root_intent="Build dashboard",
            nodes=[{"node_id": "n1", "node_type": "intent"}],
            depth=1,
            terminal_state=LineageTerminalState.COMPLETED.value,
            generated_at=1000.0,
        )
        d = chain.to_dict()
        restored = LineageChain.from_dict(d)
        self.assertEqual(restored.chain_id, "chain-1")
        self.assertEqual(restored.root_intent, "Build dashboard")
        self.assertEqual(restored.depth, 1)

    def test_defaults(self) -> None:
        chain = LineageChain()
        self.assertEqual(chain.terminal_state, LineageTerminalState.IN_PROGRESS.value)
        self.assertEqual(chain.nodes, [])


class TestLineageSummary(unittest.TestCase):
    def test_to_dict(self) -> None:
        s = LineageSummary(total_chains=5, complete_chains=3)
        d = s.to_dict()
        self.assertEqual(d["total_chains"], 5)
        self.assertEqual(d["complete_chains"], 3)


class TestSourceTruthEmpty(unittest.TestCase):
    def test_empty_summary(self) -> None:
        rt = _build_runtime()
        s = rt.summary()
        self.assertEqual(s["total_nodes"], 0)
        self.assertEqual(s["health"], "empty")

    def test_empty_trace(self) -> None:
        rt = _build_runtime()
        chain = rt.trace_lineage("nonexistent")
        self.assertEqual(chain.terminal_state, LineageTerminalState.ORPHANED.value)
        self.assertEqual(chain.depth, 0)

    def test_empty_orphaned_work(self) -> None:
        rt = _build_runtime()
        orphans = rt.orphaned_work()
        self.assertEqual(orphans, [])

    def test_empty_chain_health(self) -> None:
        h = _build_runtime().chain_health()
        self.assertEqual(h["total_chains"], 0)
        self.assertEqual(h["health"], "empty")


class TestTraceLineage(unittest.TestCase):
    def test_trace_from_work_packet(self) -> None:
        data = _full_chain_data()
        rt = _build_runtime(**data)
        chain = rt.trace_lineage("wp-1", "work_packet")
        self.assertGreater(chain.depth, 0)
        types = [n["node_type"] for n in chain.nodes]
        self.assertIn("work_packet", types)

    def test_trace_from_decision(self) -> None:
        data = _full_chain_data()
        rt = _build_runtime(**data)
        chain = rt.trace_lineage("dec-1", "decision")
        self.assertGreater(chain.depth, 0)
        types = [n["node_type"] for n in chain.nodes]
        self.assertIn("decision", types)

    def test_trace_nonexistent_returns_orphaned(self) -> None:
        data = _full_chain_data()
        rt = _build_runtime(**data)
        chain = rt.trace_lineage("does-not-exist")
        self.assertEqual(chain.terminal_state, LineageTerminalState.ORPHANED.value)

    def test_trace_auto_detects_type(self) -> None:
        data = _full_chain_data()
        rt = _build_runtime(**data)
        chain = rt.trace_lineage("wp-1")
        self.assertGreater(chain.depth, 0)

    def test_chain_has_generated_at(self) -> None:
        data = _full_chain_data()
        rt = _build_runtime(**data)
        chain = rt.trace_lineage("wp-1")
        self.assertGreater(chain.generated_at, 0)


class TestIntentToCapability(unittest.TestCase):
    def test_full_chain(self) -> None:
        data = _full_chain_data()
        rt = _build_runtime(**data)
        chain = rt.intent_to_capability("src-1")
        self.assertGreater(chain.depth, 0)

    def test_nonexistent_intent(self) -> None:
        rt = _build_runtime()
        chain = rt.intent_to_capability("nope")
        self.assertEqual(chain.depth, 0)


class TestWhyDoesThisExist(unittest.TestCase):
    def test_traces_back_to_intent(self) -> None:
        data = _full_chain_data()
        rt = _build_runtime(**data)
        result = rt.why_does_this_exist("wp-1")
        self.assertEqual(result["artifact_id"], "wp-1")
        self.assertIn("full_chain", result)
        self.assertIn("depth", result)

    def test_nonexistent_artifact(self) -> None:
        rt = _build_runtime()
        result = rt.why_does_this_exist("nope")
        self.assertEqual(result["depth"], 0)
        self.assertEqual(result["root_intent"], "")


class TestFullChain(unittest.TestCase):
    def test_from_root_intent(self) -> None:
        data = _full_chain_data()
        rt = _build_runtime(**data)
        chain = rt.full_chain("src-1")
        self.assertGreater(chain.depth, 0)


class TestOrphanedWork(unittest.TestCase):
    def test_detects_orphan(self) -> None:
        packets = [FakeWorkPacket(
            packet_id="wp-orphan",
            title="Orphaned work",
            user_intent="",
            source_type="unknown",
            source_id="",
            created_at=time.time(),
        )]
        rt = _build_runtime(packets=packets)
        orphans = rt.orphaned_work()
        self.assertGreater(len(orphans), 0)
        self.assertEqual(orphans[0]["source_id"], "wp-orphan")

    def test_linked_packet_not_orphan(self) -> None:
        data = _full_chain_data()
        rt = _build_runtime(**data)
        orphans = rt.orphaned_work()
        wp_ids = [o["source_id"] for o in orphans]
        self.assertNotIn("wp-1", wp_ids)


class TestNodesByType(unittest.TestCase):
    def test_filter_by_decision(self) -> None:
        data = _full_chain_data()
        rt = _build_runtime(**data)
        decisions = rt.nodes_by_type(LineageNodeType.DECISION.value)
        self.assertGreater(len(decisions), 0)
        for d in decisions:
            self.assertEqual(d["node_type"], "decision")

    def test_filter_empty_type(self) -> None:
        rt = _build_runtime()
        nodes = rt.nodes_by_type(LineageNodeType.DEPLOYMENT.value)
        self.assertEqual(nodes, [])


class TestChainHealth(unittest.TestCase):
    def test_healthy_chain(self) -> None:
        data = _full_chain_data()
        rt = _build_runtime(**data)
        h = rt.chain_health()
        self.assertIn(h["health"], ("healthy", "building", "degraded"))
        self.assertGreater(h["total_chains"], 0)

    def test_degraded_with_orphans(self) -> None:
        packets = [FakeWorkPacket(
            packet_id="wp-orphan",
            title="Orphaned",
            user_intent="Build something",
            source_type="unknown",
            source_id="",
            created_at=time.time(),
        )]
        rt = _build_runtime(packets=packets)
        h = rt.chain_health()
        self.assertEqual(h["orphaned_work_packets"], 1)


class TestSummary(unittest.TestCase):
    def test_full_summary(self) -> None:
        data = _full_chain_data()
        rt = _build_runtime(**data)
        s = rt.summary()
        self.assertGreater(s["total_nodes"], 0)
        self.assertIn("nodes_by_type", s)
        self.assertIn("health", s)
        self.assertIn("generated_at", s)
        self.assertIn("orphaned_work_packets", s)

    def test_empty_summary(self) -> None:
        rt = _build_runtime()
        s = rt.summary()
        self.assertEqual(s["total_nodes"], 0)
        self.assertEqual(s["health"], "empty")


class TestExecutionNodeExtraction(unittest.TestCase):
    def test_execution_linked_to_packet(self) -> None:
        packets = [FakeWorkPacket(
            packet_id="wp-1",
            title="Build API",
            user_intent="Build API",
            source_type="operator_request",
            source_id="src-1",
        )]
        plans = [FakeExecutionPlan(
            execution_plan_id="exec-1",
            source_workpacket_id="wp-1",
            description="Execute API build",
            status="completed",
        )]
        rt = _build_runtime(packets=packets, plans=plans)
        chain = rt.trace_lineage("wp-1", "work_packet")
        types = [n["node_type"] for n in chain.nodes]
        self.assertIn("execution", types)


class TestGovernanceNodeExtraction(unittest.TestCase):
    def test_governance_nodes_extracted(self) -> None:
        conflicts = [FakeConflict(
            conflict_id="conf-1",
            status="arbitrated",
            detected_at=time.time(),
        )]
        rt = _build_runtime(conflicts=conflicts)
        nodes = rt.nodes_by_type(LineageNodeType.APPROVAL.value)
        self.assertEqual(len(nodes), 1)
        self.assertEqual(nodes[0]["source_id"], "conf-1")


class TestLessonNodeExtraction(unittest.TestCase):
    def test_lessons_extracted(self) -> None:
        lessons = [FakeLesson(
            lesson_id="les-1",
            title="Test lesson",
            category="success_pattern",
            extracted_at=time.time(),
        )]
        rt = _build_runtime(lessons=lessons)
        nodes = rt.nodes_by_type(LineageNodeType.LESSON.value)
        self.assertEqual(len(nodes), 1)


class TestCapabilityNodeExtraction(unittest.TestCase):
    def test_capabilities_extracted(self) -> None:
        trajectories = [FakeTrajectory(
            capability_id="cap-1",
            current_level="established",
            events=[FakeEvolutionEvent(event_id="ev-1", capability_id="cap-1")],
            first_event_at=time.time(),
        )]
        rt = _build_runtime(trajectories=trajectories)
        nodes = rt.nodes_by_type(LineageNodeType.CAPABILITY.value)
        self.assertEqual(len(nodes), 1)
        self.assertEqual(nodes[0]["source_id"], "cap-1")


class TestMultiPacketChain(unittest.TestCase):
    def test_parent_child_packets_linked(self) -> None:
        packets = [
            FakeWorkPacket(
                packet_id="wp-parent",
                title="Parent packet",
                user_intent="Build system",
                source_type="operator_request",
                source_id="src-parent",
                child_packet_ids=["wp-child-1", "wp-child-2"],
            ),
            FakeWorkPacket(
                packet_id="wp-child-1",
                title="Child 1",
                parent_packet_id="wp-parent",
            ),
            FakeWorkPacket(
                packet_id="wp-child-2",
                title="Child 2",
                parent_packet_id="wp-parent",
            ),
        ]
        rt = _build_runtime(packets=packets)
        chain = rt.trace_lineage("wp-parent", "work_packet")
        node_ids = [n["node_id"] for n in chain.nodes]
        self.assertIn("work_packet-wp-parent", node_ids)
        self.assertIn("work_packet-wp-child-1", node_ids)
        self.assertIn("work_packet-wp-child-2", node_ids)


class TestTerminalStateDetection(unittest.TestCase):
    def test_completed_with_capability(self) -> None:
        nodes = [
            LineageNode(node_type=LineageNodeType.INTENT.value),
            LineageNode(node_type=LineageNodeType.CAPABILITY.value),
        ]
        rt = _build_runtime()
        state = rt._determine_terminal_state(nodes)
        self.assertEqual(state, LineageTerminalState.COMPLETED.value)

    def test_failed_with_failed_status(self) -> None:
        nodes = [
            LineageNode(
                node_type=LineageNodeType.EXECUTION.value,
                metadata={"status": "failed"},
            ),
        ]
        rt = _build_runtime()
        state = rt._determine_terminal_state(nodes)
        self.assertEqual(state, LineageTerminalState.FAILED.value)

    def test_in_progress_default(self) -> None:
        nodes = [
            LineageNode(node_type=LineageNodeType.WORK_PACKET.value),
        ]
        rt = _build_runtime()
        state = rt._determine_terminal_state(nodes)
        self.assertEqual(state, LineageTerminalState.IN_PROGRESS.value)

    def test_empty_is_orphaned(self) -> None:
        rt = _build_runtime()
        state = rt._determine_terminal_state([])
        self.assertEqual(state, LineageTerminalState.ORPHANED.value)


class _NullSub:
    """Null subsystem that returns empty for all expected methods."""
    def list_decisions(self) -> list[Any]:
        return []
    def all_packets(self) -> list[Any]:
        return []
    def all_plans(self) -> list[Any]:
        return []
    def recent_lessons(self, limit: int = 500) -> list[Any]:
        return []
    def all_trajectories(self) -> list[Any]:
        return []
    def recent_resolutions(self, limit: int = 200) -> list[Any]:
        return []


class TestGracefulDegradation(unittest.TestCase):
    def test_no_subsystems(self) -> None:
        null = _NullSub()
        rt = SourceTruthRuntime(
            decision_registry=null,
            work_packet_engine=null,
            execution_coordinator=null,
            learning_extraction=null,
            capability_evolution=null,
            governance_runtime=null,
        )
        s = rt.summary()
        self.assertEqual(s["total_nodes"], 0)
        self.assertEqual(s["health"], "empty")

    def test_partial_subsystems(self) -> None:
        packets = [FakeWorkPacket(
            packet_id="wp-1",
            title="Partial chain",
            user_intent="Build something",
            source_type="operator_request",
            source_id="src-1",
        )]
        null = _NullSub()
        rt = SourceTruthRuntime(
            work_packet_engine=FakeWorkPacketEngine(packets),
            decision_registry=null,
            execution_coordinator=null,
            learning_extraction=null,
            capability_evolution=null,
            governance_runtime=null,
        )
        s = rt.summary()
        self.assertGreater(s["total_nodes"], 0)

    def test_broken_subsystem_doesnt_crash(self) -> None:
        class BrokenEngine:
            def all_packets(self) -> list[Any]:
                raise RuntimeError("Subsystem down")

        null = _NullSub()
        rt = SourceTruthRuntime(
            work_packet_engine=BrokenEngine(),
            decision_registry=null,
            execution_coordinator=null,
            learning_extraction=null,
            capability_evolution=null,
            governance_runtime=null,
        )
        s = rt.summary()
        self.assertEqual(s["total_nodes"], 0)


class TestDecisionToPacketLinkage(unittest.TestCase):
    def test_decision_children_include_packets(self) -> None:
        decisions = [FakeDecision(
            decision_id="dec-1",
            title="Architecture decision",
            work_packet_refs=["wp-1"],
        )]
        packets = [FakeWorkPacket(
            packet_id="wp-1",
            title="Implement",
            user_intent="Build",
            source_type="operator_request",
            source_id="src-1",
        )]
        rt = _build_runtime(decisions=decisions, packets=packets)
        dec_nodes = rt.nodes_by_type(LineageNodeType.DECISION.value)
        self.assertEqual(len(dec_nodes), 1)
        self.assertIn("work_packet-wp-1", dec_nodes[0]["children"])


if __name__ == "__main__":
    unittest.main()
