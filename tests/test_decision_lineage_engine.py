"""Tests for Campaign 9.1 — Decision Lineage Engine."""

from __future__ import annotations

import sys
import time

import pytest

sys.path.insert(0, "/opt/OS")

from substrate.organism.decision_lineage_engine import (
    DecisionLineage,
    DecisionLineageEngine,
    LineageNode,
)
from substrate.organism.decision_registry import StrategicDecision


# ── Mock dependencies ─────────────────────────────────────────────────────


class MockGoal:
    def __init__(self, goal_id: str, title: str = "", goal_type: str = "goal", parent_goal_id: str = "") -> None:
        self.goal_id = goal_id
        self.title = title or goal_id
        self.goal_type = goal_type
        self.parent_goal_id = parent_goal_id


class MockGoalRegistry:
    def __init__(self, goals: list[MockGoal] | None = None) -> None:
        self._goals = {g.goal_id: g for g in (goals or [])}

    def get(self, goal_id: str) -> MockGoal | None:
        return self._goals.get(goal_id)


class MockGoalHierarchy:
    def __init__(self, ancestors_map: dict[str, list[MockGoal]] | None = None,
                 descendants_map: dict[str, list[MockGoal]] | None = None) -> None:
        self._ancestors = ancestors_map or {}
        self._descendants = descendants_map or {}

    def ancestors(self, goal_id: str) -> list[MockGoal]:
        return self._ancestors.get(goal_id, [])

    def descendants(self, goal_id: str) -> list[MockGoal]:
        return self._descendants.get(goal_id, [])


class MockDecisionRegistry:
    def __init__(self, decisions: list[StrategicDecision] | None = None) -> None:
        self._decisions = {d.decision_id: d for d in (decisions or [])}

    def get(self, decision_id: str) -> StrategicDecision | None:
        return self._decisions.get(decision_id)

    def list_decisions(self, status: str | None = None) -> list[StrategicDecision]:
        decs = list(self._decisions.values())
        if status:
            decs = [d for d in decs if d.status == status]
        return decs

    def decisions_for_goal(self, goal_id: str) -> list[StrategicDecision]:
        return [d for d in self._decisions.values() if goal_id in d.goal_refs]


# ── LineageNode ───────────────────────────────────────────────────────────


class TestLineageNode:
    def test_defaults(self) -> None:
        n = LineageNode()
        assert n.entity_type == ""
        assert n.entity_id == ""
        assert n.depth == 0

    def test_to_dict_keys(self) -> None:
        n = LineageNode(entity_type="goal", entity_id="g-1", label="Auth Goal", depth=2)
        d = n.to_dict()
        assert set(d.keys()) == {"entity_type", "entity_id", "label", "depth"}
        assert d["entity_type"] == "goal"
        assert d["depth"] == 2

    def test_to_dict_values(self) -> None:
        n = LineageNode(entity_type="work_packet", entity_id="wp-1", label="WP", depth=1)
        d = n.to_dict()
        assert d["entity_type"] == "work_packet"
        assert d["entity_id"] == "wp-1"


# ── DecisionLineage ──────────────────────────────────────────────────────


class TestDecisionLineage:
    def test_defaults(self) -> None:
        dl = DecisionLineage()
        assert dl.decision_id == ""
        assert dl.upstream == []
        assert dl.downstream == []
        assert dl.chain_depth == 0

    def test_to_dict_keys(self) -> None:
        dl = DecisionLineage(decision_id="sd-abc")
        expected = {
            "decision_id", "decision_title", "upstream",
            "downstream", "chain_depth", "generated_at",
        }
        assert set(dl.to_dict().keys()) == expected

    def test_from_dict_round_trip(self) -> None:
        original = DecisionLineage(
            decision_id="sd-abc",
            decision_title="Use Clerk",
            upstream=[{"entity_type": "goal", "entity_id": "g-1"}],
            downstream=[{"entity_type": "work_packet", "entity_id": "wp-1"}],
            chain_depth=3,
            generated_at=123.0,
        )
        restored = DecisionLineage.from_dict(original.to_dict())
        assert restored.decision_id == original.decision_id
        assert restored.decision_title == original.decision_title
        assert restored.upstream == original.upstream
        assert restored.downstream == original.downstream
        assert restored.chain_depth == original.chain_depth

    def test_from_dict_defaults(self) -> None:
        dl = DecisionLineage.from_dict({})
        assert dl.decision_id == ""
        assert dl.upstream == []

    def test_to_dict_immutability(self) -> None:
        dl = DecisionLineage(upstream=[{"a": 1}])
        out = dl.to_dict()
        out["upstream"].append({"b": 2})
        assert len(dl.upstream) == 1


# ── DecisionLineageEngine ────────────────────────────────────────────────


class TestDecisionLineageEngine:
    def test_trace_no_deps(self) -> None:
        engine = DecisionLineageEngine()
        result = engine.trace("sd-missing")
        assert result.decision_id == "sd-missing"
        assert result.upstream == []
        assert result.downstream == []

    def test_trace_decision_not_found(self) -> None:
        reg = MockDecisionRegistry([])
        engine = DecisionLineageEngine(decision_registry=reg)
        result = engine.trace("sd-missing")
        assert result.decision_title == ""

    def test_trace_with_goals(self) -> None:
        dec = StrategicDecision(
            decision_id="sd-1",
            title="Use Clerk",
            goal_refs=["g-auth"],
        )
        goal = MockGoal("g-auth", "Auth System", "outcome")
        reg = MockDecisionRegistry([dec])
        goal_reg = MockGoalRegistry([goal])
        engine = DecisionLineageEngine(
            decision_registry=reg,
            goal_registry=goal_reg,
        )
        result = engine.trace("sd-1")
        assert result.decision_title == "Use Clerk"
        assert len(result.upstream) == 1
        assert result.upstream[0]["entity_id"] == "g-auth"
        assert result.upstream[0]["label"] == "Auth System"

    def test_trace_with_goal_hierarchy(self) -> None:
        dec = StrategicDecision(
            decision_id="sd-1",
            title="Use Clerk",
            goal_refs=["g-auth"],
        )
        goal = MockGoal("g-auth", "Auth System")
        parent = MockGoal("g-infra", "Infrastructure")
        vision = MockGoal("g-vision", "Company Vision")

        reg = MockDecisionRegistry([dec])
        goal_reg = MockGoalRegistry([goal, parent, vision])
        hierarchy = MockGoalHierarchy(
            ancestors_map={"g-auth": [parent, vision]}
        )
        engine = DecisionLineageEngine(
            decision_registry=reg,
            goal_registry=goal_reg,
            goal_hierarchy=hierarchy,
        )
        result = engine.trace("sd-1")
        assert len(result.upstream) == 3
        assert result.chain_depth == 3

    def test_trace_downstream_work(self) -> None:
        dec = StrategicDecision(
            decision_id="sd-1",
            title="Use Clerk",
            work_packet_refs=["wp-1", "wp-2"],
            approval_refs=["ap-1"],
            project_refs=["p-1"],
        )
        reg = MockDecisionRegistry([dec])
        engine = DecisionLineageEngine(decision_registry=reg)
        result = engine.trace("sd-1")
        assert len(result.downstream) == 4
        types = [n["entity_type"] for n in result.downstream]
        assert "work_packet" in types
        assert "approval" in types
        assert "project" in types

    def test_trace_superseded_downstream(self) -> None:
        dec = StrategicDecision(
            decision_id="sd-1",
            title="Old",
            superseded_by="sd-2",
        )
        reg = MockDecisionRegistry([dec])
        engine = DecisionLineageEngine(decision_registry=reg)
        result = engine.trace("sd-1")
        decision_nodes = [n for n in result.downstream if n["entity_type"] == "decision"]
        assert len(decision_nodes) == 1
        assert decision_nodes[0]["entity_id"] == "sd-2"

    def test_full_chain_empty(self) -> None:
        engine = DecisionLineageEngine()
        assert engine.full_chain("g-1") == []

    def test_full_chain_with_decisions(self) -> None:
        dec1 = StrategicDecision(decision_id="sd-1", title="A", goal_refs=["g-1"])
        dec2 = StrategicDecision(decision_id="sd-2", title="B", goal_refs=["g-1"])
        reg = MockDecisionRegistry([dec1, dec2])
        engine = DecisionLineageEngine(decision_registry=reg)
        chains = engine.full_chain("g-1")
        assert len(chains) == 2

    def test_full_chain_includes_child_goals(self) -> None:
        dec1 = StrategicDecision(decision_id="sd-1", title="A", goal_refs=["g-1"])
        dec2 = StrategicDecision(decision_id="sd-2", title="B", goal_refs=["g-child"])
        child = MockGoal("g-child", "Child Goal")
        reg = MockDecisionRegistry([dec1, dec2])
        hierarchy = MockGoalHierarchy(descendants_map={"g-1": [child]})
        engine = DecisionLineageEngine(
            decision_registry=reg,
            goal_hierarchy=hierarchy,
        )
        chains = engine.full_chain("g-1")
        assert len(chains) == 2
        ids = {c.decision_id for c in chains}
        assert ids == {"sd-1", "sd-2"}

    def test_full_chain_deduplicates(self) -> None:
        dec = StrategicDecision(decision_id="sd-1", title="A", goal_refs=["g-1", "g-child"])
        child = MockGoal("g-child", "Child")
        reg = MockDecisionRegistry([dec])
        hierarchy = MockGoalHierarchy(descendants_map={"g-1": [child]})
        engine = DecisionLineageEngine(
            decision_registry=reg,
            goal_hierarchy=hierarchy,
        )
        chains = engine.full_chain("g-1")
        assert len(chains) == 1

    def test_blast_radius_empty(self) -> None:
        engine = DecisionLineageEngine()
        result = engine.blast_radius("sd-missing")
        assert result["affected_goals"] == []
        assert result["depth"] == 0

    def test_blast_radius_basic(self) -> None:
        dec = StrategicDecision(
            decision_id="sd-1",
            title="Use Clerk",
            goal_refs=["g-1"],
            work_packet_refs=["wp-1"],
            approval_refs=["ap-1"],
        )
        reg = MockDecisionRegistry([dec])
        engine = DecisionLineageEngine(decision_registry=reg)
        result = engine.blast_radius("sd-1")
        assert "g-1" in result["affected_goals"]
        assert "wp-1" in result["affected_work"]
        assert "ap-1" in result["affected_approvals"]
        assert result["depth"] >= 1

    def test_blast_radius_with_hierarchy(self) -> None:
        dec = StrategicDecision(
            decision_id="sd-1",
            title="Use Clerk",
            goal_refs=["g-1"],
        )
        child = MockGoal("g-child", "Child Goal")
        reg = MockDecisionRegistry([dec])
        hierarchy = MockGoalHierarchy(descendants_map={"g-1": [child]})
        engine = DecisionLineageEngine(
            decision_registry=reg,
            goal_hierarchy=hierarchy,
        )
        result = engine.blast_radius("sd-1")
        assert "g-child" in result["affected_goals"]
        assert result["depth"] >= 2

    def test_blast_radius_with_supersession(self) -> None:
        dec = StrategicDecision(
            decision_id="sd-1",
            title="Old",
            superseded_by="sd-2",
        )
        reg = MockDecisionRegistry([dec])
        engine = DecisionLineageEngine(decision_registry=reg)
        result = engine.blast_radius("sd-1")
        assert "sd-2" in result["affected_decisions"]

    def test_blast_radius_related_decisions(self) -> None:
        dec1 = StrategicDecision(decision_id="sd-1", title="A", goal_refs=["g-1"])
        dec2 = StrategicDecision(decision_id="sd-2", title="B", goal_refs=["g-1"])
        reg = MockDecisionRegistry([dec1, dec2])
        engine = DecisionLineageEngine(decision_registry=reg)
        result = engine.blast_radius("sd-1")
        assert "sd-2" in result["affected_decisions"]

    def test_blast_radius_keys(self) -> None:
        dec = StrategicDecision(decision_id="sd-1", title="A")
        reg = MockDecisionRegistry([dec])
        engine = DecisionLineageEngine(decision_registry=reg)
        result = engine.blast_radius("sd-1")
        expected = {"decision", "affected_goals", "affected_work",
                    "affected_approvals", "affected_decisions", "depth"}
        assert set(result.keys()) == expected

    def test_summary_no_deps(self) -> None:
        engine = DecisionLineageEngine()
        s = engine.summary()
        assert s["total_decisions"] == 0

    def test_summary_with_decisions(self) -> None:
        dec1 = StrategicDecision(decision_id="sd-1", title="A", goal_refs=["g-1"])
        dec2 = StrategicDecision(decision_id="sd-2", title="B")
        reg = MockDecisionRegistry([dec1, dec2])
        engine = DecisionLineageEngine(decision_registry=reg)
        s = engine.summary()
        assert s["total_decisions"] == 2
        assert "average_depth" in s
        assert "max_depth" in s
        assert "generated_at" in s

    def test_summary_keys(self) -> None:
        engine = DecisionLineageEngine()
        expected = {"total_decisions", "average_depth", "max_depth", "generated_at"}
        assert set(engine.summary().keys()) == expected

    def test_graceful_degrade_all_none(self) -> None:
        engine = DecisionLineageEngine()
        assert engine.trace("x").upstream == []
        assert engine.full_chain("x") == []
        assert engine.blast_radius("x")["depth"] == 0
        assert engine.summary()["total_decisions"] == 0
