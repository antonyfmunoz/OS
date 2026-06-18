"""Tests for Campaign 9.0 — Decision Registry."""

from __future__ import annotations

import json
import os
import sys
import tempfile
import time

import pytest

sys.path.insert(0, "/opt/OS")

from substrate.organism.decision_registry import (
    DecisionRegistry,
    DecisionStatus,
    StrategicDecision,
)


# ── DecisionStatus ────────────────────────────────────────────────────────


class TestDecisionStatus:
    def test_values(self) -> None:
        assert DecisionStatus.PROPOSED.value == "proposed"
        assert DecisionStatus.ACTIVE.value == "active"
        assert DecisionStatus.SUPERSEDED.value == "superseded"
        assert DecisionStatus.INVALIDATED.value == "invalidated"
        assert DecisionStatus.ARCHIVED.value == "archived"

    def test_count(self) -> None:
        assert len(DecisionStatus) == 5

    def test_string_enum(self) -> None:
        assert isinstance(DecisionStatus.ACTIVE, str)
        assert DecisionStatus.ACTIVE == "active"


# ── StrategicDecision ─────────────────────────────────────────────────────


class TestStrategicDecision:
    def test_defaults(self) -> None:
        d = StrategicDecision()
        assert d.decision_id.startswith("sd-")
        assert d.title == ""
        assert d.status == "proposed"
        assert d.goal_refs == []
        assert d.alternatives_considered == []
        assert d.metadata == {}

    def test_to_dict_keys(self) -> None:
        d = StrategicDecision()
        keys = set(d.to_dict().keys())
        expected = {
            "decision_id", "title", "summary", "rationale",
            "alternatives_considered", "assumptions", "status",
            "goal_refs", "project_refs", "work_packet_refs",
            "approval_refs", "superseded_by", "supersedes",
            "tags", "metadata", "created_at", "updated_at",
        }
        assert keys == expected

    def test_to_dict_values(self) -> None:
        d = StrategicDecision(
            title="Use Clerk",
            rationale="Best auth for our scale",
            goal_refs=["g-1"],
            tags=["auth"],
        )
        out = d.to_dict()
        assert out["title"] == "Use Clerk"
        assert out["rationale"] == "Best auth for our scale"
        assert out["goal_refs"] == ["g-1"]
        assert out["tags"] == ["auth"]

    def test_from_dict_round_trip(self) -> None:
        original = StrategicDecision(
            title="Use Clerk",
            summary="Auth provider decision",
            rationale="Pricing and DX",
            alternatives_considered=[{"title": "Auth0", "reason_rejected": "cost"}],
            assumptions=["asm-1"],
            status="active",
            goal_refs=["g-1"],
            project_refs=["p-1"],
            work_packet_refs=["wp-1"],
            approval_refs=["ap-1"],
            superseded_by="sd-new",
            supersedes="sd-old",
            tags=["auth"],
            metadata={"domain": "auth"},
        )
        restored = StrategicDecision.from_dict(original.to_dict())
        assert restored.title == original.title
        assert restored.rationale == original.rationale
        assert restored.alternatives_considered == original.alternatives_considered
        assert restored.assumptions == original.assumptions
        assert restored.goal_refs == original.goal_refs
        assert restored.superseded_by == original.superseded_by
        assert restored.tags == original.tags
        assert restored.metadata == original.metadata

    def test_from_dict_defaults(self) -> None:
        d = StrategicDecision.from_dict({})
        assert d.title == ""
        assert d.status == "proposed"
        assert d.goal_refs == []

    def test_unique_ids(self) -> None:
        d1 = StrategicDecision()
        d2 = StrategicDecision()
        assert d1.decision_id != d2.decision_id

    def test_to_dict_immutability(self) -> None:
        d = StrategicDecision(goal_refs=["g-1"])
        out = d.to_dict()
        out["goal_refs"].append("g-2")
        assert d.goal_refs == ["g-1"]


# ── DecisionRegistry ──────────────────────────────────────────────────────


class TestDecisionRegistry:
    @pytest.fixture()
    def tmp_dir(self, tmp_path: str) -> str:
        return str(tmp_path)

    @pytest.fixture()
    def registry(self, tmp_dir: str) -> DecisionRegistry:
        return DecisionRegistry(data_dir=tmp_dir)

    def test_register_and_get(self, registry: DecisionRegistry) -> None:
        d = StrategicDecision(title="Use Clerk")
        result = registry.register(d)
        assert result.title == "Use Clerk"
        assert result.updated_at > 0
        fetched = registry.get(d.decision_id)
        assert fetched is not None
        assert fetched.title == "Use Clerk"

    def test_get_missing(self, registry: DecisionRegistry) -> None:
        assert registry.get("nonexistent") is None

    def test_list_all(self, registry: DecisionRegistry) -> None:
        registry.register(StrategicDecision(title="A"))
        registry.register(StrategicDecision(title="B"))
        all_d = registry.list_decisions()
        assert len(all_d) == 2

    def test_list_by_status(self, registry: DecisionRegistry) -> None:
        d1 = StrategicDecision(title="A", status="active")
        d2 = StrategicDecision(title="B", status="proposed")
        registry.register(d1)
        registry.register(d2)
        active = registry.list_decisions(status="active")
        assert len(active) == 1
        assert active[0].title == "A"

    def test_update_status(self, registry: DecisionRegistry) -> None:
        d = StrategicDecision(title="Test")
        registry.register(d)
        assert registry.update_status(d.decision_id, DecisionStatus.ACTIVE)
        fetched = registry.get(d.decision_id)
        assert fetched is not None
        assert fetched.status == "active"

    def test_update_status_missing(self, registry: DecisionRegistry) -> None:
        assert not registry.update_status("nonexistent", DecisionStatus.ACTIVE)

    def test_supersede(self, registry: DecisionRegistry) -> None:
        old = StrategicDecision(title="Old Decision", status="active")
        new = StrategicDecision(title="New Decision", status="active")
        registry.register(old)
        registry.register(new)
        assert registry.supersede(old.decision_id, new.decision_id)
        old_fetched = registry.get(old.decision_id)
        new_fetched = registry.get(new.decision_id)
        assert old_fetched is not None
        assert old_fetched.status == "superseded"
        assert old_fetched.superseded_by == new.decision_id
        assert new_fetched is not None
        assert new_fetched.supersedes == old.decision_id

    def test_supersede_missing(self, registry: DecisionRegistry) -> None:
        d = StrategicDecision(title="A")
        registry.register(d)
        assert not registry.supersede(d.decision_id, "nonexistent")
        assert not registry.supersede("nonexistent", d.decision_id)

    def test_decisions_for_goal(self, registry: DecisionRegistry) -> None:
        d1 = StrategicDecision(title="A", goal_refs=["g-1"])
        d2 = StrategicDecision(title="B", goal_refs=["g-2"])
        d3 = StrategicDecision(title="C", goal_refs=["g-1", "g-2"])
        registry.register(d1)
        registry.register(d2)
        registry.register(d3)
        g1 = registry.decisions_for_goal("g-1")
        assert len(g1) == 2
        titles = {d.title for d in g1}
        assert titles == {"A", "C"}

    def test_decisions_for_project(self, registry: DecisionRegistry) -> None:
        d = StrategicDecision(title="A", project_refs=["p-1"])
        registry.register(d)
        result = registry.decisions_for_project("p-1")
        assert len(result) == 1

    def test_decisions_for_work_packet(self, registry: DecisionRegistry) -> None:
        d = StrategicDecision(title="A", work_packet_refs=["wp-1"])
        registry.register(d)
        result = registry.decisions_for_work_packet("wp-1")
        assert len(result) == 1

    def test_active_decisions(self, registry: DecisionRegistry) -> None:
        registry.register(StrategicDecision(title="A", status="active"))
        registry.register(StrategicDecision(title="B", status="proposed"))
        registry.register(StrategicDecision(title="C", status="active"))
        active = registry.active_decisions()
        assert len(active) == 2

    def test_summary_keys(self, registry: DecisionRegistry) -> None:
        registry.register(StrategicDecision(title="A"))
        s = registry.summary()
        expected = {"total", "by_status", "recent", "generated_at"}
        assert set(s.keys()) == expected

    def test_summary_counts(self, registry: DecisionRegistry) -> None:
        registry.register(StrategicDecision(status="active"))
        registry.register(StrategicDecision(status="active"))
        registry.register(StrategicDecision(status="proposed"))
        s = registry.summary()
        assert s["total"] == 3
        assert s["by_status"]["active"] == 2
        assert s["by_status"]["proposed"] == 1

    def test_summary_recent_limit(self, registry: DecisionRegistry) -> None:
        for i in range(10):
            registry.register(StrategicDecision(title=f"D{i}"))
        s = registry.summary()
        assert len(s["recent"]) == 5

    def test_persistence_round_trip(self, tmp_dir: str) -> None:
        r1 = DecisionRegistry(data_dir=tmp_dir)
        d = StrategicDecision(title="Persist Test", status="active")
        r1.register(d)

        r2 = DecisionRegistry(data_dir=tmp_dir)
        fetched = r2.get(d.decision_id)
        assert fetched is not None
        assert fetched.title == "Persist Test"
        assert fetched.status == "active"

    def test_persistence_file_created(self, tmp_dir: str) -> None:
        r = DecisionRegistry(data_dir=tmp_dir)
        r.register(StrategicDecision(title="Test"))
        assert os.path.exists(os.path.join(tmp_dir, "decisions.jsonl"))

    def test_empty_registry(self, registry: DecisionRegistry) -> None:
        assert registry.list_decisions() == []
        s = registry.summary()
        assert s["total"] == 0

    def test_list_sorted_by_created_at(self, registry: DecisionRegistry) -> None:
        d1 = StrategicDecision(title="Old", created_at=100.0)
        d2 = StrategicDecision(title="New", created_at=200.0)
        registry.register(d1)
        registry.register(d2)
        results = registry.list_decisions()
        assert results[0].title == "New"
        assert results[1].title == "Old"

    def test_register_updates_updated_at(self, registry: DecisionRegistry) -> None:
        d = StrategicDecision(title="Test", updated_at=0.0)
        before = time.time()
        registry.register(d)
        assert d.updated_at >= before

    def test_reality_graph_integration(self, tmp_dir: str) -> None:
        class MockRG:
            def __init__(self):
                self.entities = []
                self.relations = []
            def add_entity(self, e):
                self.entities.append(e)
            def add_relation(self, r):
                self.relations.append(r)

        rg = MockRG()
        reg = DecisionRegistry(reality_graph=rg, data_dir=tmp_dir)
        d = StrategicDecision(
            title="Test RG",
            goal_refs=["g-1"],
            work_packet_refs=["wp-1"],
            approval_refs=["ap-1"],
        )
        reg.register(d)
        assert len(rg.entities) == 1
        assert rg.entities[0].name == "Test RG"
        assert len(rg.relations) == 3

    def test_reality_graph_none_graceful(self, registry: DecisionRegistry) -> None:
        d = StrategicDecision(title="No RG")
        registry.register(d)
        assert registry.get(d.decision_id) is not None

    def test_supersede_registers_relation(self, tmp_dir: str) -> None:
        class MockRG:
            def __init__(self):
                self.entities = []
                self.relations = []
            def add_entity(self, e):
                self.entities.append(e)
            def add_relation(self, r):
                self.relations.append(r)

        rg = MockRG()
        reg = DecisionRegistry(reality_graph=rg, data_dir=tmp_dir)
        old = StrategicDecision(title="Old")
        new = StrategicDecision(title="New")
        reg.register(old)
        reg.register(new)
        initial_rels = len(rg.relations)
        reg.supersede(old.decision_id, new.decision_id)
        assert len(rg.relations) == initial_rels + 1


# ── RealityGraph Extension ────────────────────────────────────────────────


class TestRealityGraphExtension:
    def test_decision_entity_type(self) -> None:
        from substrate.organism.reality_graph import RealityEntityType
        assert RealityEntityType.DECISION.value == "decision"

    def test_supports_relation_type(self) -> None:
        from substrate.organism.reality_graph import RealityRelationType
        assert RealityRelationType.SUPPORTS.value == "supports"

    def test_created_relation_type(self) -> None:
        from substrate.organism.reality_graph import RealityRelationType
        assert RealityRelationType.CREATED.value == "created"

    def test_approved_by_relation_type(self) -> None:
        from substrate.organism.reality_graph import RealityRelationType
        assert RealityRelationType.APPROVED_BY.value == "approved_by"

    def test_supersedes_relation_type(self) -> None:
        from substrate.organism.reality_graph import RealityRelationType
        assert RealityRelationType.SUPERSEDES.value == "supersedes"

    def test_entity_type_count(self) -> None:
        from substrate.organism.reality_graph import RealityEntityType
        assert len(RealityEntityType) == 16

    def test_relation_type_count(self) -> None:
        from substrate.organism.reality_graph import RealityRelationType
        assert len(RealityRelationType) == 13
