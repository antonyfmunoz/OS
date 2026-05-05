"""Phase 36 — Goal Hierarchies + Abstraction Layer v1.

Tests for:
  - MetaGoal (frozen, to_dict, defaults)
  - MetaGoalScore (frozen, to_dict)
  - HierarchyInfluence (frozen, to_dict)
  - CycleError
  - GoalHierarchy (register, query, cycle detection, aggregation, clear)
  - GoalMemory meta-goal extensions (type mapping, grouped queries)
  - HierarchyScorer (disabled, neutral, enabled, bounds)
  - Meta-planner integration (SequenceEvaluator, MetaPlanner)
  - End-to-end pipeline
  - Stability
  - Hard invariants 116-120
  - Boundary / exports / compile
"""

from __future__ import annotations

import ast
import sys
from dataclasses import FrozenInstanceError

import pytest

sys.path.insert(0, "/opt/OS")


# ---------------------------------------------------------------------------
# Section 1: MetaGoal
# ---------------------------------------------------------------------------


class TestMetaGoal:
    def test_creation(self) -> None:
        from umh.runtime.goal_hierarchy import MetaGoal

        mg = MetaGoal(name="business", child_goal_types=("revenue", "growth"))
        assert mg.name == "business"
        assert mg.child_goal_types == ("revenue", "growth")
        assert mg.weight == 0.5

    def test_frozen(self) -> None:
        from umh.runtime.goal_hierarchy import MetaGoal

        mg = MetaGoal(name="business", child_goal_types=("revenue",))
        with pytest.raises(FrozenInstanceError):
            mg.name = "other"  # type: ignore[misc]

    def test_defaults(self) -> None:
        from umh.runtime.goal_hierarchy import MetaGoal

        mg = MetaGoal(name="test", child_goal_types=("a",))
        assert mg.weight == 0.5
        assert mg.aggregation_method == "weighted_average"
        assert mg.description == ""

    def test_to_dict(self) -> None:
        from umh.runtime.goal_hierarchy import MetaGoal

        mg = MetaGoal(name="biz", child_goal_types=("rev", "growth"), weight=0.7, description="d")
        d = mg.to_dict()
        assert d["name"] == "biz"
        assert d["child_goal_types"] == ["rev", "growth"]
        assert d["weight"] == 0.7

    def test_custom_weight(self) -> None:
        from umh.runtime.goal_hierarchy import MetaGoal

        mg = MetaGoal(name="test", child_goal_types=("a",), weight=0.9)
        assert mg.weight == 0.9


# ---------------------------------------------------------------------------
# Section 2: MetaGoalScore
# ---------------------------------------------------------------------------


class TestMetaGoalScore:
    def test_creation(self) -> None:
        from umh.runtime.goal_hierarchy import MetaGoalScore

        s = MetaGoalScore("business", 0.8, {"rev": 0.9}, {"rev": 3}, 3, "reason")
        assert s.meta_goal_name == "business"
        assert s.score == 0.8

    def test_frozen(self) -> None:
        from umh.runtime.goal_hierarchy import MetaGoalScore

        s = MetaGoalScore("b", 0.8, {}, {}, 0, "r")
        with pytest.raises(FrozenInstanceError):
            s.score = 1.0  # type: ignore[misc]

    def test_to_dict(self) -> None:
        from umh.runtime.goal_hierarchy import MetaGoalScore

        s = MetaGoalScore("b", 0.812345, {"rev": 0.9123}, {"rev": 3}, 3, "r")
        d = s.to_dict()
        assert d["score"] == round(0.812345, 4)
        assert "rev" in d["child_scores"]

    def test_to_dict_sorted(self) -> None:
        from umh.runtime.goal_hierarchy import MetaGoalScore

        s = MetaGoalScore("b", 0.8, {"z": 0.1, "a": 0.9}, {"z": 1, "a": 2}, 3, "r")
        d = s.to_dict()
        keys = list(d["child_scores"].keys())
        assert keys == sorted(keys)


# ---------------------------------------------------------------------------
# Section 3: HierarchyInfluence
# ---------------------------------------------------------------------------


class TestHierarchyInfluence:
    def test_creation(self) -> None:
        from umh.runtime.goal_hierarchy import HierarchyInfluence

        h = HierarchyInfluence(
            factor=1.05, meta_goal_scores={"biz": 0.8}, contributing_types=["rev"], reason="r"
        )
        assert h.factor == 1.05

    def test_frozen(self) -> None:
        from umh.runtime.goal_hierarchy import HierarchyInfluence

        h = HierarchyInfluence(factor=1.0, meta_goal_scores={}, contributing_types=[], reason="r")
        with pytest.raises(FrozenInstanceError):
            h.factor = 0.9  # type: ignore[misc]

    def test_to_dict(self) -> None:
        from umh.runtime.goal_hierarchy import HierarchyInfluence

        h = HierarchyInfluence(
            factor=1.05, meta_goal_scores={"biz": 0.8123}, contributing_types=["rev"], reason="r"
        )
        d = h.to_dict()
        assert d["factor"] == 1.05
        assert d["meta_goal_scores"]["biz"] == round(0.8123, 4)

    def test_to_dict_sorted_scores(self) -> None:
        from umh.runtime.goal_hierarchy import HierarchyInfluence

        h = HierarchyInfluence(
            factor=1.0, meta_goal_scores={"z": 0.5, "a": 0.7}, contributing_types=[], reason="r"
        )
        d = h.to_dict()
        keys = list(d["meta_goal_scores"].keys())
        assert keys == sorted(keys)


# ---------------------------------------------------------------------------
# Section 4: CycleError
# ---------------------------------------------------------------------------


class TestCycleError:
    def test_is_value_error(self) -> None:
        from umh.runtime.goal_hierarchy import CycleError

        assert issubclass(CycleError, ValueError)

    def test_message(self) -> None:
        from umh.runtime.goal_hierarchy import CycleError

        err = CycleError("test cycle")
        assert "test cycle" in str(err)


# ---------------------------------------------------------------------------
# Section 5: GoalHierarchy registration
# ---------------------------------------------------------------------------


class TestGoalHierarchyRegistration:
    def test_empty(self) -> None:
        from umh.runtime.goal_hierarchy import GoalHierarchy

        h = GoalHierarchy()
        assert h.meta_goal_count == 0

    def test_register_single(self) -> None:
        from umh.runtime.goal_hierarchy import GoalHierarchy, MetaGoal

        h = GoalHierarchy()
        mg = MetaGoal(name="business", child_goal_types=("revenue", "growth"))
        h.register_meta_goal(mg)
        assert h.meta_goal_count == 1

    def test_register_multiple(self) -> None:
        from umh.runtime.goal_hierarchy import GoalHierarchy, MetaGoal

        h = GoalHierarchy()
        h.register_meta_goal(MetaGoal(name="business", child_goal_types=("revenue",)))
        h.register_meta_goal(MetaGoal(name="personal", child_goal_types=("health",)))
        assert h.meta_goal_count == 2

    def test_register_empty_name_raises(self) -> None:
        from umh.runtime.goal_hierarchy import GoalHierarchy, MetaGoal

        h = GoalHierarchy()
        with pytest.raises(ValueError, match="empty"):
            h.register_meta_goal(MetaGoal(name="", child_goal_types=("a",)))

    def test_register_no_children_raises(self) -> None:
        from umh.runtime.goal_hierarchy import GoalHierarchy, MetaGoal

        h = GoalHierarchy()
        with pytest.raises(ValueError, match="child"):
            h.register_meta_goal(MetaGoal(name="test", child_goal_types=()))

    def test_register_overwrites(self) -> None:
        from umh.runtime.goal_hierarchy import GoalHierarchy, MetaGoal

        h = GoalHierarchy()
        h.register_meta_goal(MetaGoal(name="biz", child_goal_types=("rev",)))
        h.register_meta_goal(MetaGoal(name="biz", child_goal_types=("rev", "growth")))
        assert h.meta_goal_count == 1
        assert len(h.get_children("biz")) == 2

    def test_get_meta_goal(self) -> None:
        from umh.runtime.goal_hierarchy import GoalHierarchy, MetaGoal

        h = GoalHierarchy()
        mg = MetaGoal(name="biz", child_goal_types=("rev",))
        h.register_meta_goal(mg)
        result = h.get_meta_goal("biz")
        assert result is not None
        assert result.name == "biz"

    def test_get_meta_goal_missing(self) -> None:
        from umh.runtime.goal_hierarchy import GoalHierarchy

        h = GoalHierarchy()
        assert h.get_meta_goal("nonexistent") is None

    def test_get_children(self) -> None:
        from umh.runtime.goal_hierarchy import GoalHierarchy, MetaGoal

        h = GoalHierarchy()
        h.register_meta_goal(MetaGoal(name="biz", child_goal_types=("rev", "growth")))
        children = h.get_children("biz")
        assert children == ("rev", "growth")

    def test_get_children_missing(self) -> None:
        from umh.runtime.goal_hierarchy import GoalHierarchy

        h = GoalHierarchy()
        assert h.get_children("missing") == ()

    def test_get_meta_goals_for_type(self) -> None:
        from umh.runtime.goal_hierarchy import GoalHierarchy, MetaGoal

        h = GoalHierarchy()
        h.register_meta_goal(MetaGoal(name="biz", child_goal_types=("rev", "growth")))
        h.register_meta_goal(MetaGoal(name="money", child_goal_types=("rev", "savings")))
        metas = h.get_meta_goals_for_type("rev")
        assert "biz" in metas
        assert "money" in metas
        assert len(metas) == 2

    def test_get_meta_goals_for_type_empty(self) -> None:
        from umh.runtime.goal_hierarchy import GoalHierarchy

        h = GoalHierarchy()
        assert h.get_meta_goals_for_type("unknown") == []

    def test_list_meta_goals_sorted(self) -> None:
        from umh.runtime.goal_hierarchy import GoalHierarchy, MetaGoal

        h = GoalHierarchy()
        h.register_meta_goal(MetaGoal(name="zebra", child_goal_types=("a",)))
        h.register_meta_goal(MetaGoal(name="alpha", child_goal_types=("b",)))
        listed = h.list_meta_goals()
        assert [m.name for m in listed] == ["alpha", "zebra"]

    def test_clear(self) -> None:
        from umh.runtime.goal_hierarchy import GoalHierarchy, MetaGoal

        h = GoalHierarchy()
        h.register_meta_goal(MetaGoal(name="biz", child_goal_types=("rev",)))
        h.clear()
        assert h.meta_goal_count == 0
        assert h.get_meta_goals_for_type("rev") == []

    def test_to_dict(self) -> None:
        from umh.runtime.goal_hierarchy import GoalHierarchy, MetaGoal

        h = GoalHierarchy()
        h.register_meta_goal(MetaGoal(name="biz", child_goal_types=("rev",)))
        d = h.to_dict()
        assert d["meta_goal_count"] == 1
        assert "biz" in d["meta_goals"]
        assert "rev" in d["type_to_meta"]


# ---------------------------------------------------------------------------
# Section 6: Cycle detection
# ---------------------------------------------------------------------------


class TestCycleDetection:
    def test_self_reference(self) -> None:
        from umh.runtime.goal_hierarchy import CycleError, GoalHierarchy, MetaGoal

        h = GoalHierarchy()
        with pytest.raises(CycleError):
            h.register_meta_goal(MetaGoal(name="a", child_goal_types=("a",)))

    def test_direct_cycle(self) -> None:
        from umh.runtime.goal_hierarchy import CycleError, GoalHierarchy, MetaGoal

        h = GoalHierarchy()
        h.register_meta_goal(MetaGoal(name="a", child_goal_types=("b",)))
        with pytest.raises(CycleError):
            h.register_meta_goal(MetaGoal(name="b", child_goal_types=("a",)))

    def test_transitive_cycle(self) -> None:
        from umh.runtime.goal_hierarchy import CycleError, GoalHierarchy, MetaGoal

        h = GoalHierarchy()
        h.register_meta_goal(MetaGoal(name="a", child_goal_types=("b",)))
        h.register_meta_goal(MetaGoal(name="b", child_goal_types=("c",)))
        with pytest.raises(CycleError):
            h.register_meta_goal(MetaGoal(name="c", child_goal_types=("a",)))

    def test_no_false_positive(self) -> None:
        from umh.runtime.goal_hierarchy import GoalHierarchy, MetaGoal

        h = GoalHierarchy()
        h.register_meta_goal(MetaGoal(name="a", child_goal_types=("x", "y")))
        h.register_meta_goal(MetaGoal(name="b", child_goal_types=("y", "z")))
        assert h.meta_goal_count == 2

    def test_diamond_no_cycle(self) -> None:
        from umh.runtime.goal_hierarchy import GoalHierarchy, MetaGoal

        h = GoalHierarchy()
        h.register_meta_goal(MetaGoal(name="top", child_goal_types=("left", "right")))
        h.register_meta_goal(MetaGoal(name="left", child_goal_types=("bottom",)))
        h.register_meta_goal(MetaGoal(name="right", child_goal_types=("bottom",)))
        assert h.meta_goal_count == 3

    def test_shared_child_no_cycle(self) -> None:
        from umh.runtime.goal_hierarchy import GoalHierarchy, MetaGoal

        h = GoalHierarchy()
        h.register_meta_goal(MetaGoal(name="a", child_goal_types=("shared",)))
        h.register_meta_goal(MetaGoal(name="b", child_goal_types=("shared",)))
        assert h.meta_goal_count == 2


# ---------------------------------------------------------------------------
# Section 7: GoalHierarchy aggregation
# ---------------------------------------------------------------------------


class TestGoalHierarchyAggregation:
    def test_compute_meta_score_single_child(self) -> None:
        from umh.runtime.goal_hierarchy import GoalHierarchy, MetaGoal

        h = GoalHierarchy()
        h.register_meta_goal(MetaGoal(name="biz", child_goal_types=("rev",)))
        result = h.compute_meta_score("biz", {"rev": 0.8})
        assert result is not None
        assert result.score == 0.8
        assert result.total_records == 1

    def test_compute_meta_score_multiple_children(self) -> None:
        from umh.runtime.goal_hierarchy import GoalHierarchy, MetaGoal

        h = GoalHierarchy()
        h.register_meta_goal(MetaGoal(name="biz", child_goal_types=("rev", "growth")))
        result = h.compute_meta_score("biz", {"rev": 0.8, "growth": 0.6})
        assert result is not None
        assert abs(result.score - 0.7) < 0.001

    def test_compute_meta_score_partial_data(self) -> None:
        from umh.runtime.goal_hierarchy import GoalHierarchy, MetaGoal

        h = GoalHierarchy()
        h.register_meta_goal(MetaGoal(name="biz", child_goal_types=("rev", "growth", "retention")))
        result = h.compute_meta_score("biz", {"rev": 0.9})
        assert result is not None
        assert result.score == 0.9
        assert result.total_records == 1
        assert "1/3" in result.reason

    def test_compute_meta_score_no_data(self) -> None:
        from umh.runtime.goal_hierarchy import GoalHierarchy, MetaGoal

        h = GoalHierarchy()
        h.register_meta_goal(MetaGoal(name="biz", child_goal_types=("rev",)))
        result = h.compute_meta_score("biz", {})
        assert result is not None
        assert result.score == 1.0
        assert result.total_records == 0

    def test_compute_meta_score_clamped_high(self) -> None:
        from umh.runtime.goal_hierarchy import GoalHierarchy, MetaGoal

        h = GoalHierarchy()
        h.register_meta_goal(MetaGoal(name="biz", child_goal_types=("rev",)))
        result = h.compute_meta_score("biz", {"rev": 2.0})
        assert result is not None
        assert result.score <= 1.5

    def test_compute_meta_score_clamped_low(self) -> None:
        from umh.runtime.goal_hierarchy import GoalHierarchy, MetaGoal

        h = GoalHierarchy()
        h.register_meta_goal(MetaGoal(name="biz", child_goal_types=("rev",)))
        result = h.compute_meta_score("biz", {"rev": 0.1})
        assert result is not None
        assert result.score >= 0.5

    def test_compute_meta_score_missing_meta(self) -> None:
        from umh.runtime.goal_hierarchy import GoalHierarchy

        h = GoalHierarchy()
        assert h.compute_meta_score("nonexistent", {"rev": 0.8}) is None

    def test_compute_meta_score_reason_strong(self) -> None:
        from umh.runtime.goal_hierarchy import GoalHierarchy, MetaGoal

        h = GoalHierarchy()
        h.register_meta_goal(MetaGoal(name="biz", child_goal_types=("rev",)))
        result = h.compute_meta_score("biz", {"rev": 0.9})
        assert result is not None
        assert "strong" in result.reason

    def test_compute_meta_score_reason_weak(self) -> None:
        from umh.runtime.goal_hierarchy import GoalHierarchy, MetaGoal

        h = GoalHierarchy()
        h.register_meta_goal(MetaGoal(name="biz", child_goal_types=("rev",)))
        result = h.compute_meta_score("biz", {"rev": 0.5})
        assert result is not None
        assert "weak" in result.reason


# ---------------------------------------------------------------------------
# Section 8: GoalMemory meta-goal extensions
# ---------------------------------------------------------------------------


class TestGoalMemoryMetaExtensions:
    def test_set_type_meta_mapping(self) -> None:
        from umh.runtime.goal_memory import GoalMemory

        m = GoalMemory()
        m.set_type_meta_mapping("revenue", ["business", "money"])
        assert m.get_meta_goals_for_type("revenue") == ["business", "money"]

    def test_get_meta_goals_for_type_empty(self) -> None:
        from umh.runtime.goal_memory import GoalMemory

        m = GoalMemory()
        assert m.get_meta_goals_for_type("unknown") == []

    def test_query_by_meta_goal(self) -> None:
        from umh.runtime.goal_memory import GoalMemory, make_goal_record

        m = GoalMemory()
        m.set_type_meta_mapping("revenue", ["business"])
        m.set_type_meta_mapping("growth", ["business"])
        m.set_type_meta_mapping("health", ["personal"])
        m.append(
            make_goal_record(goal_id="g1", goal_type="revenue", duration_ticks=5, completed=True)
        )
        m.append(
            make_goal_record(goal_id="g2", goal_type="growth", duration_ticks=3, completed=True)
        )
        m.append(
            make_goal_record(goal_id="g3", goal_type="health", duration_ticks=7, completed=True)
        )

        biz_records = m.query_by_meta_goal("business")
        assert len(biz_records) == 2
        assert all(r.goal_type in ("revenue", "growth") for r in biz_records)

    def test_query_by_meta_goal_empty(self) -> None:
        from umh.runtime.goal_memory import GoalMemory

        m = GoalMemory()
        assert m.query_by_meta_goal("unknown") == []

    def test_compute_grouped_stats(self) -> None:
        from umh.runtime.goal_memory import GoalMemory, make_goal_record

        m = GoalMemory()
        m.set_type_meta_mapping("revenue", ["business"])
        m.set_type_meta_mapping("growth", ["business"])
        m.append(
            make_goal_record(
                goal_id="g1",
                goal_type="revenue",
                duration_ticks=5,
                completed=True,
                success_rate=0.8,
            )
        )
        m.append(
            make_goal_record(
                goal_id="g2", goal_type="growth", duration_ticks=3, completed=True, success_rate=0.6
            )
        )

        stats = m.compute_grouped_stats("business")
        assert len(stats) == 2
        types = [s.goal_type for s in stats]
        assert "revenue" in types
        assert "growth" in types

    def test_compute_grouped_stats_empty(self) -> None:
        from umh.runtime.goal_memory import GoalMemory

        m = GoalMemory()
        assert m.compute_grouped_stats("unknown") == []

    def test_clear_clears_mappings(self) -> None:
        from umh.runtime.goal_memory import GoalMemory

        m = GoalMemory()
        m.set_type_meta_mapping("revenue", ["business"])
        m.clear()
        assert m.get_meta_goals_for_type("revenue") == []

    def test_to_dict_includes_mappings(self) -> None:
        from umh.runtime.goal_memory import GoalMemory

        m = GoalMemory()
        m.set_type_meta_mapping("revenue", ["business"])
        d = m.to_dict()
        assert "type_to_meta" in d
        assert "revenue" in d["type_to_meta"]


# ---------------------------------------------------------------------------
# Section 9: HierarchyScorer
# ---------------------------------------------------------------------------


class TestHierarchyScorer:
    def test_disabled(self) -> None:
        from umh.runtime.goal_hierarchy import HierarchyScorer

        scorer = HierarchyScorer(enabled=False)
        result = scorer.compute_factor(goal_type="revenue")
        assert result.factor == 1.0
        assert "disabled" in result.reason

    def test_no_hierarchy(self) -> None:
        from umh.runtime.goal_hierarchy import HierarchyScorer

        scorer = HierarchyScorer(hierarchy=None, enabled=True)
        result = scorer.compute_factor(goal_type="revenue")
        assert result.factor == 1.0

    def test_no_goal_type(self) -> None:
        from umh.runtime.goal_hierarchy import GoalHierarchy, HierarchyScorer

        scorer = HierarchyScorer(hierarchy=GoalHierarchy(), enabled=True)
        result = scorer.compute_factor(goal_type="")
        assert result.factor == 1.0
        assert "no goal type" in result.reason

    def test_type_not_in_hierarchy(self) -> None:
        from umh.runtime.goal_hierarchy import GoalHierarchy, HierarchyScorer

        scorer = HierarchyScorer(hierarchy=GoalHierarchy(), enabled=True)
        result = scorer.compute_factor(goal_type="unknown")
        assert result.factor == 1.0
        assert "not in any meta-goal" in result.reason

    def test_with_data_positive(self) -> None:
        from umh.runtime.goal_hierarchy import GoalHierarchy, HierarchyScorer, MetaGoal
        from umh.runtime.goal_memory import GoalMemory, make_goal_record
        from umh.runtime.goals import ReinforcementScorer

        hierarchy = GoalHierarchy()
        hierarchy.register_meta_goal(MetaGoal(name="biz", child_goal_types=("revenue", "growth")))
        mem = GoalMemory()
        mem.append(
            make_goal_record(
                goal_id="g1",
                goal_type="revenue",
                duration_ticks=100,
                completed=True,
                success_rate=1.0,
                identity_alignment=1.0,
                reward=1.0,
            )
        )
        mem.append(
            make_goal_record(
                goal_id="g2",
                goal_type="growth",
                duration_ticks=100,
                completed=True,
                success_rate=0.9,
                identity_alignment=0.9,
                reward=0.8,
            )
        )
        scorer = HierarchyScorer(
            hierarchy=hierarchy,
            goal_memory=mem,
            reinforcement_scorer=ReinforcementScorer(max_duration=100),
            enabled=True,
        )
        result = scorer.compute_factor(goal_type="revenue")
        assert 0.9 <= result.factor <= 1.1

    def test_factor_clamped_min(self) -> None:
        from umh.runtime.goal_hierarchy import GoalHierarchy, HierarchyScorer, MetaGoal
        from umh.runtime.goal_memory import GoalMemory, make_goal_record
        from umh.runtime.goals import ReinforcementScorer

        hierarchy = GoalHierarchy()
        hierarchy.register_meta_goal(
            MetaGoal(name="biz", child_goal_types=("revenue",), weight=5.0)
        )
        mem = GoalMemory()
        mem.append(
            make_goal_record(
                goal_id="g1",
                goal_type="revenue",
                duration_ticks=1,
                completed=False,
                success_rate=0.0,
                identity_alignment=0.0,
                reward=-1.0,
            )
        )
        scorer = HierarchyScorer(
            hierarchy=hierarchy,
            goal_memory=mem,
            reinforcement_scorer=ReinforcementScorer(max_duration=100),
            enabled=True,
        )
        result = scorer.compute_factor(goal_type="revenue")
        assert result.factor >= 0.9

    def test_factor_clamped_max(self) -> None:
        from umh.runtime.goal_hierarchy import GoalHierarchy, HierarchyScorer, MetaGoal
        from umh.runtime.goal_memory import GoalMemory, make_goal_record
        from umh.runtime.goals import ReinforcementScorer

        hierarchy = GoalHierarchy()
        hierarchy.register_meta_goal(
            MetaGoal(name="biz", child_goal_types=("revenue",), weight=5.0)
        )
        mem = GoalMemory()
        for _ in range(10):
            mem.append(
                make_goal_record(
                    goal_id="g1",
                    goal_type="revenue",
                    duration_ticks=200,
                    completed=True,
                    success_rate=1.0,
                    identity_alignment=1.0,
                    reward=1.0,
                )
            )
        scorer = HierarchyScorer(
            hierarchy=hierarchy,
            goal_memory=mem,
            reinforcement_scorer=ReinforcementScorer(max_duration=100),
            enabled=True,
        )
        result = scorer.compute_factor(goal_type="revenue")
        assert result.factor <= 1.1

    def test_properties(self) -> None:
        from umh.runtime.goal_hierarchy import GoalHierarchy, HierarchyScorer
        from umh.runtime.goal_memory import GoalMemory
        from umh.runtime.goals import ReinforcementScorer

        h = GoalHierarchy()
        m = GoalMemory()
        r = ReinforcementScorer()
        scorer = HierarchyScorer(hierarchy=h, goal_memory=m, reinforcement_scorer=r, enabled=True)
        assert scorer.enabled is True
        assert scorer.hierarchy is h
        assert scorer.goal_memory is m
        assert scorer.reinforcement_scorer is r

    def test_no_memory_no_crash(self) -> None:
        from umh.runtime.goal_hierarchy import GoalHierarchy, HierarchyScorer, MetaGoal

        hierarchy = GoalHierarchy()
        hierarchy.register_meta_goal(MetaGoal(name="biz", child_goal_types=("revenue",)))
        scorer = HierarchyScorer(hierarchy=hierarchy, goal_memory=None, enabled=True)
        result = scorer.compute_factor(goal_type="revenue")
        assert result.factor == 1.0

    def test_no_reinforcement_scorer_no_crash(self) -> None:
        from umh.runtime.goal_hierarchy import GoalHierarchy, HierarchyScorer, MetaGoal
        from umh.runtime.goal_memory import GoalMemory

        hierarchy = GoalHierarchy()
        hierarchy.register_meta_goal(MetaGoal(name="biz", child_goal_types=("revenue",)))
        scorer = HierarchyScorer(
            hierarchy=hierarchy,
            goal_memory=GoalMemory(),
            reinforcement_scorer=None,
            enabled=True,
        )
        result = scorer.compute_factor(goal_type="revenue")
        assert result.factor == 1.0

    def test_multiple_meta_goals(self) -> None:
        from umh.runtime.goal_hierarchy import GoalHierarchy, HierarchyScorer, MetaGoal
        from umh.runtime.goal_memory import GoalMemory, make_goal_record
        from umh.runtime.goals import ReinforcementScorer

        hierarchy = GoalHierarchy()
        hierarchy.register_meta_goal(MetaGoal(name="biz", child_goal_types=("revenue", "growth")))
        hierarchy.register_meta_goal(
            MetaGoal(name="money", child_goal_types=("revenue", "savings"))
        )
        mem = GoalMemory()
        mem.append(
            make_goal_record(
                goal_id="g1",
                goal_type="revenue",
                duration_ticks=100,
                completed=True,
                success_rate=0.9,
                identity_alignment=0.8,
                reward=0.7,
            )
        )
        scorer = HierarchyScorer(
            hierarchy=hierarchy,
            goal_memory=mem,
            reinforcement_scorer=ReinforcementScorer(max_duration=100),
            enabled=True,
        )
        result = scorer.compute_factor(goal_type="revenue")
        assert 0.9 <= result.factor <= 1.1
        assert len(result.meta_goal_scores) >= 1


# ---------------------------------------------------------------------------
# Section 10: Meta-planner integration
# ---------------------------------------------------------------------------


class TestMetaPlannerIntegration:
    def _make_objective(self, oid: str, priority: int = 5, goal_type: str = ""):
        from umh.runtime.arbitration import Objective

        metadata = {}
        if goal_type:
            metadata["goal_type"] = goal_type
        return Objective(
            objective_id=oid,
            description=f"Obj {oid}",
            priority=priority,
            effort_estimate=1.0,
            expected_value=1.0,
            metadata=metadata,
        )

    def test_evaluator_property(self) -> None:
        from umh.runtime.goal_hierarchy import HierarchyScorer
        from umh.runtime.meta_planner import SequenceEvaluator

        scorer = HierarchyScorer(enabled=True)
        ev = SequenceEvaluator(hierarchy_scorer=scorer)
        assert ev.hierarchy_scorer is scorer

    def test_evaluator_none_default(self) -> None:
        from umh.runtime.meta_planner import SequenceEvaluator

        ev = SequenceEvaluator()
        assert ev.hierarchy_scorer is None

    def test_score_affected_by_hierarchy(self) -> None:
        from umh.runtime.goal_hierarchy import GoalHierarchy, HierarchyScorer, MetaGoal
        from umh.runtime.goal_memory import GoalMemory, make_goal_record
        from umh.runtime.goals import ReinforcementScorer
        from umh.runtime.meta_planner import SequenceEvaluator

        hierarchy = GoalHierarchy()
        hierarchy.register_meta_goal(MetaGoal(name="biz", child_goal_types=("revenue",)))
        mem = GoalMemory()
        for _ in range(5):
            mem.append(
                make_goal_record(
                    goal_id="g1",
                    goal_type="revenue",
                    duration_ticks=100,
                    completed=True,
                    success_rate=0.7,
                    identity_alignment=0.8,
                    reward=0.5,
                )
            )
        scorer = HierarchyScorer(
            hierarchy=hierarchy,
            goal_memory=mem,
            reinforcement_scorer=ReinforcementScorer(max_duration=100),
            enabled=True,
        )
        ev_with = SequenceEvaluator(hierarchy_scorer=scorer)
        ev_without = SequenceEvaluator()

        objs = [self._make_objective("o1", goal_type="revenue")]
        score_with = ev_with.score_sequence(objs, label="with")
        score_without = ev_without.score_sequence(objs, label="without")
        assert score_with.total_score != score_without.total_score

    def test_no_effect_when_disabled(self) -> None:
        from umh.runtime.goal_hierarchy import HierarchyScorer
        from umh.runtime.meta_planner import SequenceEvaluator

        scorer = HierarchyScorer(enabled=False)
        ev_with = SequenceEvaluator(hierarchy_scorer=scorer)
        ev_without = SequenceEvaluator()

        objs = [self._make_objective("o1")]
        score_with = ev_with.score_sequence(objs, label="with")
        score_without = ev_without.score_sequence(objs, label="without")
        assert abs(score_with.total_score - score_without.total_score) < 0.0001

    def test_planner_property(self) -> None:
        from umh.runtime.goal_hierarchy import HierarchyScorer
        from umh.runtime.meta_planner import MetaPlanner

        scorer = HierarchyScorer(enabled=True)
        planner = MetaPlanner(hierarchy_scorer=scorer)
        assert planner.hierarchy_scorer is scorer

    def test_planner_none_default(self) -> None:
        from umh.runtime.meta_planner import MetaPlanner

        planner = MetaPlanner()
        assert planner.hierarchy_scorer is None

    def test_reason_includes_hierarchy(self) -> None:
        from umh.runtime.goal_hierarchy import GoalHierarchy, HierarchyScorer, MetaGoal
        from umh.runtime.goal_memory import GoalMemory, make_goal_record
        from umh.runtime.goals import ReinforcementScorer
        from umh.runtime.meta_planner import MetaPlanner, SequenceEvaluator

        hierarchy = GoalHierarchy()
        hierarchy.register_meta_goal(MetaGoal(name="biz", child_goal_types=("revenue",)))
        mem = GoalMemory()
        for _ in range(5):
            mem.append(
                make_goal_record(
                    goal_id="g1",
                    goal_type="revenue",
                    duration_ticks=100,
                    completed=True,
                    success_rate=0.7,
                    identity_alignment=0.8,
                    reward=0.5,
                )
            )
        scorer = HierarchyScorer(
            hierarchy=hierarchy,
            goal_memory=mem,
            reinforcement_scorer=ReinforcementScorer(max_duration=100),
            enabled=True,
        )
        ev = SequenceEvaluator(hierarchy_scorer=scorer)
        planner = MetaPlanner(sequence_evaluator=ev, hierarchy_scorer=scorer)
        objs = [
            self._make_objective("o1", priority=8, goal_type="revenue"),
            self._make_objective("o2", priority=6, goal_type="revenue"),
            self._make_objective("o3", priority=4, goal_type="revenue"),
        ]
        result = planner.plan(objs)
        assert result is not None
        assert "hierarchy" in result.reason


# ---------------------------------------------------------------------------
# Section 11: End-to-end pipeline
# ---------------------------------------------------------------------------


class TestEndToEnd:
    def _make_objective(self, oid: str, priority: int = 5, goal_type: str = ""):
        from umh.runtime.arbitration import Objective

        metadata = {}
        if goal_type:
            metadata["goal_type"] = goal_type
        return Objective(
            objective_id=oid,
            description=f"Obj {oid}",
            priority=priority,
            effort_estimate=1.0,
            expected_value=1.0,
            metadata=metadata,
        )

    def test_e2e_full_chain(self) -> None:
        from umh.runtime.goal_hierarchy import GoalHierarchy, HierarchyScorer, MetaGoal
        from umh.runtime.goal_memory import GoalMemory, make_goal_record
        from umh.runtime.goals import GoalBiasScorer, ReinforcementScorer
        from umh.runtime.identity import IdentityScorer, IdentityStore
        from umh.runtime.meta_planner import SequenceEvaluator

        id_store = IdentityStore()
        id_scorer = IdentityScorer(identity_store=id_store, enabled=True)

        mem = GoalMemory()
        mem.append(
            make_goal_record(
                goal_id="g1",
                goal_type="revenue",
                duration_ticks=100,
                completed=True,
                success_rate=0.9,
                identity_alignment=0.8,
                reward=0.7,
            )
        )

        reinf_scorer = ReinforcementScorer(max_duration=100)
        goal_scorer = GoalBiasScorer(
            goal_memory=mem,
            reinforcement_scorer=reinf_scorer,
            enabled=True,
        )

        hierarchy = GoalHierarchy()
        hierarchy.register_meta_goal(MetaGoal(name="biz", child_goal_types=("revenue", "growth")))
        h_scorer = HierarchyScorer(
            hierarchy=hierarchy,
            goal_memory=mem,
            reinforcement_scorer=reinf_scorer,
            enabled=True,
        )

        ev = SequenceEvaluator(
            identity_scorer=id_scorer,
            goal_bias_scorer=goal_scorer,
            hierarchy_scorer=h_scorer,
        )
        objs = [self._make_objective("o1", priority=7, goal_type="revenue")]
        result = ev.score_sequence(objs, label="test")
        assert result.total_score > 0

    def test_e2e_hierarchy_influences_related(self) -> None:
        from umh.runtime.goal_hierarchy import GoalHierarchy, HierarchyScorer, MetaGoal
        from umh.runtime.goal_memory import GoalMemory, make_goal_record
        from umh.runtime.goals import ReinforcementScorer
        from umh.runtime.meta_planner import SequenceEvaluator

        hierarchy = GoalHierarchy()
        hierarchy.register_meta_goal(MetaGoal(name="biz", child_goal_types=("revenue", "growth")))
        mem = GoalMemory()
        for _ in range(5):
            mem.append(
                make_goal_record(
                    goal_id="g1",
                    goal_type="revenue",
                    duration_ticks=100,
                    completed=True,
                    success_rate=0.7,
                    identity_alignment=0.8,
                    reward=0.5,
                )
            )
            mem.append(
                make_goal_record(
                    goal_id="g2",
                    goal_type="growth",
                    duration_ticks=100,
                    completed=True,
                    success_rate=0.6,
                    identity_alignment=0.7,
                    reward=0.4,
                )
            )
        scorer = HierarchyScorer(
            hierarchy=hierarchy,
            goal_memory=mem,
            reinforcement_scorer=ReinforcementScorer(max_duration=100),
            enabled=True,
        )
        ev = SequenceEvaluator(hierarchy_scorer=scorer)
        ev_none = SequenceEvaluator()

        obj = [self._make_objective("o1", goal_type="revenue")]
        with_h = ev.score_sequence(obj, label="with")
        without_h = ev_none.score_sequence(obj, label="without")
        assert with_h.total_score != without_h.total_score
        assert with_h.total_score < without_h.total_score

    def test_e2e_unrelated_type_neutral(self) -> None:
        from umh.runtime.goal_hierarchy import GoalHierarchy, HierarchyScorer, MetaGoal
        from umh.runtime.goal_memory import GoalMemory, make_goal_record
        from umh.runtime.goals import ReinforcementScorer
        from umh.runtime.meta_planner import SequenceEvaluator

        hierarchy = GoalHierarchy()
        hierarchy.register_meta_goal(MetaGoal(name="biz", child_goal_types=("revenue",)))
        mem = GoalMemory()
        mem.append(
            make_goal_record(
                goal_id="g1",
                goal_type="revenue",
                duration_ticks=100,
                completed=True,
                success_rate=1.0,
                identity_alignment=1.0,
                reward=1.0,
            )
        )
        scorer = HierarchyScorer(
            hierarchy=hierarchy,
            goal_memory=mem,
            reinforcement_scorer=ReinforcementScorer(max_duration=100),
            enabled=True,
        )
        ev = SequenceEvaluator(hierarchy_scorer=scorer)
        ev_none = SequenceEvaluator()

        obj = [self._make_objective("o1", goal_type="health")]
        with_h = ev.score_sequence(obj, label="with")
        without_h = ev_none.score_sequence(obj, label="without")
        assert abs(with_h.total_score - without_h.total_score) < 0.0001


# ---------------------------------------------------------------------------
# Section 12: Stability
# ---------------------------------------------------------------------------


class TestStability:
    def test_consistent_scoring(self) -> None:
        from umh.runtime.goal_hierarchy import GoalHierarchy, HierarchyScorer, MetaGoal
        from umh.runtime.goal_memory import GoalMemory, make_goal_record
        from umh.runtime.goals import ReinforcementScorer

        hierarchy = GoalHierarchy()
        hierarchy.register_meta_goal(MetaGoal(name="biz", child_goal_types=("revenue",)))
        mem = GoalMemory()
        mem.append(
            make_goal_record(
                goal_id="g1",
                goal_type="revenue",
                duration_ticks=50,
                completed=True,
                success_rate=0.7,
                identity_alignment=0.7,
                reward=0.5,
            )
        )
        scorer = HierarchyScorer(
            hierarchy=hierarchy,
            goal_memory=mem,
            reinforcement_scorer=ReinforcementScorer(max_duration=100),
            enabled=True,
        )
        r1 = scorer.compute_factor(goal_type="revenue")
        r2 = scorer.compute_factor(goal_type="revenue")
        assert r1.factor == r2.factor

    def test_growing_data_stability(self) -> None:
        from umh.runtime.goal_hierarchy import GoalHierarchy, HierarchyScorer, MetaGoal
        from umh.runtime.goal_memory import GoalMemory, make_goal_record
        from umh.runtime.goals import ReinforcementScorer

        hierarchy = GoalHierarchy()
        hierarchy.register_meta_goal(MetaGoal(name="biz", child_goal_types=("revenue",)))
        mem = GoalMemory()
        scorer = HierarchyScorer(
            hierarchy=hierarchy,
            goal_memory=mem,
            reinforcement_scorer=ReinforcementScorer(max_duration=100),
            enabled=True,
        )
        factors: list[float] = []
        for i in range(20):
            mem.append(
                make_goal_record(
                    goal_id=f"g{i}",
                    goal_type="revenue",
                    duration_ticks=50,
                    completed=True,
                    success_rate=0.7,
                    identity_alignment=0.7,
                    reward=0.5,
                )
            )
            result = scorer.compute_factor(goal_type="revenue")
            factors.append(result.factor)

        for f in factors:
            assert abs(f - factors[-1]) < 0.01

    def test_independent_meta_goals(self) -> None:
        from umh.runtime.goal_hierarchy import GoalHierarchy, HierarchyScorer, MetaGoal
        from umh.runtime.goal_memory import GoalMemory, make_goal_record
        from umh.runtime.goals import ReinforcementScorer

        hierarchy = GoalHierarchy()
        hierarchy.register_meta_goal(MetaGoal(name="biz", child_goal_types=("revenue",)))
        hierarchy.register_meta_goal(MetaGoal(name="personal", child_goal_types=("health",)))
        mem = GoalMemory()
        for _ in range(5):
            mem.append(
                make_goal_record(
                    goal_id="g1",
                    goal_type="revenue",
                    duration_ticks=100,
                    completed=True,
                    success_rate=1.0,
                    identity_alignment=1.0,
                    reward=1.0,
                )
            )
        scorer = HierarchyScorer(
            hierarchy=hierarchy,
            goal_memory=mem,
            reinforcement_scorer=ReinforcementScorer(max_duration=100),
            enabled=True,
        )
        rev_result = scorer.compute_factor(goal_type="revenue")
        health_result = scorer.compute_factor(goal_type="health")
        assert rev_result.factor != 1.0 or health_result.factor == 1.0

    def test_mixed_children_moderate(self) -> None:
        from umh.runtime.goal_hierarchy import GoalHierarchy, HierarchyScorer, MetaGoal
        from umh.runtime.goal_memory import GoalMemory, make_goal_record
        from umh.runtime.goals import ReinforcementScorer

        hierarchy = GoalHierarchy()
        hierarchy.register_meta_goal(MetaGoal(name="biz", child_goal_types=("revenue", "growth")))
        mem = GoalMemory()
        mem.append(
            make_goal_record(
                goal_id="g1",
                goal_type="revenue",
                duration_ticks=100,
                completed=True,
                success_rate=1.0,
                identity_alignment=1.0,
                reward=1.0,
            )
        )
        mem.append(
            make_goal_record(
                goal_id="g2",
                goal_type="growth",
                duration_ticks=10,
                completed=False,
                success_rate=0.1,
                identity_alignment=0.2,
                reward=-0.5,
            )
        )
        scorer = HierarchyScorer(
            hierarchy=hierarchy,
            goal_memory=mem,
            reinforcement_scorer=ReinforcementScorer(max_duration=100),
            enabled=True,
        )
        result = scorer.compute_factor(goal_type="revenue")
        assert 0.9 <= result.factor <= 1.1


# ---------------------------------------------------------------------------
# Section 13: Hard Invariants 116-120
# ---------------------------------------------------------------------------


class TestHardInvariants:
    def test_inv116_hierarchy_read_only_during_execution(self) -> None:
        """INV 116: GoalHierarchy is set up at init, compute methods don't modify it."""
        from umh.runtime.goal_hierarchy import GoalHierarchy, HierarchyScorer, MetaGoal
        from umh.runtime.goal_memory import GoalMemory, make_goal_record
        from umh.runtime.goals import ReinforcementScorer

        hierarchy = GoalHierarchy()
        hierarchy.register_meta_goal(MetaGoal(name="biz", child_goal_types=("revenue",)))
        count_before = hierarchy.meta_goal_count
        dict_before = hierarchy.to_dict()

        mem = GoalMemory()
        mem.append(
            make_goal_record(
                goal_id="g1",
                goal_type="revenue",
                duration_ticks=50,
                completed=True,
                success_rate=0.8,
                identity_alignment=0.7,
                reward=0.5,
            )
        )
        scorer = HierarchyScorer(
            hierarchy=hierarchy,
            goal_memory=mem,
            reinforcement_scorer=ReinforcementScorer(max_duration=100),
            enabled=True,
        )
        for _ in range(10):
            scorer.compute_factor(goal_type="revenue")

        assert hierarchy.meta_goal_count == count_before
        assert hierarchy.to_dict() == dict_before

    def test_inv116_compute_meta_score_no_mutation(self) -> None:
        """INV 116: compute_meta_score does not alter the hierarchy."""
        from umh.runtime.goal_hierarchy import GoalHierarchy, MetaGoal

        h = GoalHierarchy()
        h.register_meta_goal(MetaGoal(name="biz", child_goal_types=("rev", "growth")))
        state_before = h.to_dict()
        h.compute_meta_score("biz", {"rev": 0.8, "growth": 0.6})
        h.compute_meta_score("biz", {"rev": 0.2})
        h.compute_meta_score("biz", {})
        assert h.to_dict() == state_before

    def test_inv117_no_child_mutation_from_parent(self) -> None:
        """INV 117: MetaGoal is frozen — children cannot be mutated."""
        from umh.runtime.goal_hierarchy import MetaGoal

        mg = MetaGoal(name="biz", child_goal_types=("rev", "growth"))
        with pytest.raises(FrozenInstanceError):
            mg.child_goal_types = ("other",)  # type: ignore[misc]

    def test_inv117_score_frozen(self) -> None:
        """INV 117: MetaGoalScore is frozen."""
        from umh.runtime.goal_hierarchy import MetaGoalScore

        s = MetaGoalScore("b", 0.8, {}, {}, 0, "r")
        with pytest.raises(FrozenInstanceError):
            s.score = 0.5  # type: ignore[misc]

    def test_inv118_aggregation_deterministic(self) -> None:
        """INV 118: Same inputs produce same outputs."""
        from umh.runtime.goal_hierarchy import GoalHierarchy, MetaGoal

        h = GoalHierarchy()
        h.register_meta_goal(MetaGoal(name="biz", child_goal_types=("rev", "growth", "retention")))
        data = {"rev": 0.8, "growth": 0.6, "retention": 0.7}
        r1 = h.compute_meta_score("biz", data)
        r2 = h.compute_meta_score("biz", data)
        assert r1 is not None and r2 is not None
        assert r1.score == r2.score
        assert r1.child_scores == r2.child_scores

    def test_inv118_aggregation_deterministic_varied_order(self) -> None:
        """INV 118: Aggregation is order-independent."""
        from umh.runtime.goal_hierarchy import GoalHierarchy, MetaGoal

        h = GoalHierarchy()
        h.register_meta_goal(MetaGoal(name="biz", child_goal_types=("a", "b", "c")))
        data1 = {"a": 0.5, "b": 0.7, "c": 0.9}
        data2 = {"c": 0.9, "a": 0.5, "b": 0.7}
        r1 = h.compute_meta_score("biz", data1)
        r2 = h.compute_meta_score("biz", data2)
        assert r1 is not None and r2 is not None
        assert r1.score == r2.score

    def test_inv119_no_circular_dependencies(self) -> None:
        """INV 119: Cycles are rejected at registration time."""
        from umh.runtime.goal_hierarchy import CycleError, GoalHierarchy, MetaGoal

        h = GoalHierarchy()
        h.register_meta_goal(MetaGoal(name="a", child_goal_types=("b",)))
        h.register_meta_goal(MetaGoal(name="b", child_goal_types=("c",)))
        with pytest.raises(CycleError):
            h.register_meta_goal(MetaGoal(name="c", child_goal_types=("a",)))

    def test_inv119_self_cycle_rejected(self) -> None:
        """INV 119: Self-referencing meta-goal is rejected."""
        from umh.runtime.goal_hierarchy import CycleError, GoalHierarchy, MetaGoal

        h = GoalHierarchy()
        with pytest.raises(CycleError):
            h.register_meta_goal(MetaGoal(name="x", child_goal_types=("x",)))

    def test_inv120_hierarchy_no_override(self) -> None:
        """INV 120: Hierarchy factor in [0.9, 1.1] — never overrides base scoring."""
        from umh.runtime.goal_hierarchy import GoalHierarchy, HierarchyScorer, MetaGoal
        from umh.runtime.goal_memory import GoalMemory, make_goal_record
        from umh.runtime.goals import ReinforcementScorer

        hierarchy = GoalHierarchy()
        hierarchy.register_meta_goal(
            MetaGoal(name="biz", child_goal_types=("revenue",), weight=10.0)
        )
        mem = GoalMemory()
        for _ in range(20):
            mem.append(
                make_goal_record(
                    goal_id="g1",
                    goal_type="revenue",
                    duration_ticks=200,
                    completed=True,
                    success_rate=1.0,
                    identity_alignment=1.0,
                    reward=1.0,
                )
            )
        scorer = HierarchyScorer(
            hierarchy=hierarchy,
            goal_memory=mem,
            reinforcement_scorer=ReinforcementScorer(max_duration=100),
            enabled=True,
        )
        result = scorer.compute_factor(goal_type="revenue")
        assert 0.9 <= result.factor <= 1.1

    def test_inv120_extreme_negative_bounded(self) -> None:
        """INV 120: Even extreme negative data stays >= 0.9."""
        from umh.runtime.goal_hierarchy import GoalHierarchy, HierarchyScorer, MetaGoal
        from umh.runtime.goal_memory import GoalMemory, make_goal_record
        from umh.runtime.goals import ReinforcementScorer

        hierarchy = GoalHierarchy()
        hierarchy.register_meta_goal(
            MetaGoal(name="biz", child_goal_types=("revenue",), weight=10.0)
        )
        mem = GoalMemory()
        for _ in range(20):
            mem.append(
                make_goal_record(
                    goal_id="g1",
                    goal_type="revenue",
                    duration_ticks=1,
                    completed=False,
                    success_rate=0.0,
                    identity_alignment=0.0,
                    reward=-1.0,
                )
            )
        scorer = HierarchyScorer(
            hierarchy=hierarchy,
            goal_memory=mem,
            reinforcement_scorer=ReinforcementScorer(max_duration=100),
            enabled=True,
        )
        result = scorer.compute_factor(goal_type="revenue")
        assert result.factor >= 0.9

    def test_inv115_no_execution_imports(self) -> None:
        """INV 115 (continued): goal_hierarchy.py must not import forbidden modules."""
        source_path = "/opt/OS/umh/runtime/goal_hierarchy.py"
        with open(source_path) as f:
            tree = ast.parse(f.read())

        forbidden = {"umh.cells", "umh.environments", "umh.adapters", "subprocess"}
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                if isinstance(node, ast.ImportFrom) and node.module:
                    for fb in forbidden:
                        assert not node.module.startswith(fb), f"Forbidden import: {node.module}"
                elif isinstance(node, ast.Import):
                    for alias in node.names:
                        for fb in forbidden:
                            assert not alias.name.startswith(fb), f"Forbidden import: {alias.name}"


# ---------------------------------------------------------------------------
# Section 14: Explainability
# ---------------------------------------------------------------------------


class TestExplainability:
    def test_meta_goal_score_has_reason(self) -> None:
        from umh.runtime.goal_hierarchy import GoalHierarchy, MetaGoal

        h = GoalHierarchy()
        h.register_meta_goal(MetaGoal(name="biz", child_goal_types=("rev", "growth")))
        result = h.compute_meta_score("biz", {"rev": 0.8})
        assert result is not None
        assert len(result.reason) > 0

    def test_hierarchy_influence_has_reason(self) -> None:
        from umh.runtime.goal_hierarchy import GoalHierarchy, HierarchyScorer, MetaGoal
        from umh.runtime.goal_memory import GoalMemory, make_goal_record
        from umh.runtime.goals import ReinforcementScorer

        hierarchy = GoalHierarchy()
        hierarchy.register_meta_goal(MetaGoal(name="biz", child_goal_types=("revenue",)))
        mem = GoalMemory()
        mem.append(
            make_goal_record(
                goal_id="g1",
                goal_type="revenue",
                duration_ticks=50,
                completed=True,
                success_rate=0.8,
                identity_alignment=0.7,
                reward=0.5,
            )
        )
        scorer = HierarchyScorer(
            hierarchy=hierarchy,
            goal_memory=mem,
            reinforcement_scorer=ReinforcementScorer(max_duration=100),
            enabled=True,
        )
        result = scorer.compute_factor(goal_type="revenue")
        assert len(result.reason) > 0

    def test_contributing_types_populated(self) -> None:
        from umh.runtime.goal_hierarchy import GoalHierarchy, HierarchyScorer, MetaGoal
        from umh.runtime.goal_memory import GoalMemory, make_goal_record
        from umh.runtime.goals import ReinforcementScorer

        hierarchy = GoalHierarchy()
        hierarchy.register_meta_goal(MetaGoal(name="biz", child_goal_types=("revenue", "growth")))
        mem = GoalMemory()
        mem.append(
            make_goal_record(
                goal_id="g1",
                goal_type="revenue",
                duration_ticks=50,
                completed=True,
                success_rate=0.8,
                identity_alignment=0.7,
                reward=0.5,
            )
        )
        mem.append(
            make_goal_record(
                goal_id="g2",
                goal_type="growth",
                duration_ticks=50,
                completed=True,
                success_rate=0.7,
                identity_alignment=0.6,
                reward=0.4,
            )
        )
        scorer = HierarchyScorer(
            hierarchy=hierarchy,
            goal_memory=mem,
            reinforcement_scorer=ReinforcementScorer(max_duration=100),
            enabled=True,
        )
        result = scorer.compute_factor(goal_type="revenue")
        assert "revenue" in result.contributing_types
        assert "growth" in result.contributing_types

    def test_meta_goal_scores_populated(self) -> None:
        from umh.runtime.goal_hierarchy import GoalHierarchy, HierarchyScorer, MetaGoal
        from umh.runtime.goal_memory import GoalMemory, make_goal_record
        from umh.runtime.goals import ReinforcementScorer

        hierarchy = GoalHierarchy()
        hierarchy.register_meta_goal(MetaGoal(name="biz", child_goal_types=("revenue",)))
        mem = GoalMemory()
        mem.append(
            make_goal_record(
                goal_id="g1",
                goal_type="revenue",
                duration_ticks=50,
                completed=True,
                success_rate=0.8,
                identity_alignment=0.7,
                reward=0.5,
            )
        )
        scorer = HierarchyScorer(
            hierarchy=hierarchy,
            goal_memory=mem,
            reinforcement_scorer=ReinforcementScorer(max_duration=100),
            enabled=True,
        )
        result = scorer.compute_factor(goal_type="revenue")
        assert "biz" in result.meta_goal_scores


# ---------------------------------------------------------------------------
# Section 15: Boundary / Exports / Compile
# ---------------------------------------------------------------------------


class TestBoundaryExports:
    def test_import_goal_hierarchy(self) -> None:
        from umh.runtime.goal_hierarchy import (
            CycleError,
            GoalHierarchy,
            HierarchyInfluence,
            HierarchyScorer,
            MetaGoal,
            MetaGoalScore,
        )

        assert GoalHierarchy is not None
        assert MetaGoal is not None
        assert MetaGoalScore is not None
        assert HierarchyInfluence is not None
        assert HierarchyScorer is not None
        assert CycleError is not None

    def test_compile_goal_hierarchy(self) -> None:
        import py_compile

        py_compile.compile("/opt/OS/umh/runtime/goal_hierarchy.py", doraise=True)

    def test_compile_goal_memory(self) -> None:
        import py_compile

        py_compile.compile("/opt/OS/umh/runtime/goal_memory.py", doraise=True)

    def test_compile_meta_planner(self) -> None:
        import py_compile

        py_compile.compile("/opt/OS/umh/runtime/meta_planner.py", doraise=True)

    def test_compile_init(self) -> None:
        import py_compile

        py_compile.compile("/opt/OS/umh/runtime/__init__.py", doraise=True)

    def test_runtime_exports_hierarchy(self) -> None:
        from umh.runtime import (
            CycleError,
            GoalHierarchy,
            HierarchyInfluence,
            HierarchyScorer,
            MetaGoal,
            MetaGoalScore,
        )

        assert GoalHierarchy is not None
        assert HierarchyScorer is not None

    def test_all_exports_present(self) -> None:
        import umh.runtime as rt

        expected = [
            "CycleError",
            "GoalHierarchy",
            "HierarchyInfluence",
            "HierarchyScorer",
            "MetaGoal",
            "MetaGoalScore",
        ]
        for name in expected:
            assert name in rt.__all__, f"{name} not in __all__"

    def test_meta_goal_to_dict_round_trip(self) -> None:
        from umh.runtime.goal_hierarchy import MetaGoal

        mg = MetaGoal(name="biz", child_goal_types=("rev", "growth"), weight=0.7)
        d = mg.to_dict()
        assert d["name"] == "biz"
        assert isinstance(d["child_goal_types"], list)

    def test_hierarchy_influence_to_dict(self) -> None:
        from umh.runtime.goal_hierarchy import HierarchyInfluence

        h = HierarchyInfluence(
            factor=1.05, meta_goal_scores={"b": 0.8}, contributing_types=["r"], reason="r"
        )
        d = h.to_dict()
        assert d["factor"] == 1.05

    def test_meta_goal_score_to_dict(self) -> None:
        from umh.runtime.goal_hierarchy import MetaGoalScore

        s = MetaGoalScore("b", 0.8, {"r": 0.9}, {"r": 1}, 1, "reason")
        d = s.to_dict()
        assert d["meta_goal_name"] == "b"
        assert d["total_records"] == 1

    def test_goal_memory_to_dict_has_meta(self) -> None:
        from umh.runtime.goal_memory import GoalMemory

        m = GoalMemory()
        m.set_type_meta_mapping("rev", ["biz"])
        d = m.to_dict()
        assert "type_to_meta" in d

    def test_hierarchy_to_dict(self) -> None:
        from umh.runtime.goal_hierarchy import GoalHierarchy, MetaGoal

        h = GoalHierarchy()
        h.register_meta_goal(MetaGoal(name="biz", child_goal_types=("rev",)))
        d = h.to_dict()
        assert "meta_goals" in d
        assert "type_to_meta" in d


# ---------------------------------------------------------------------------
# Section 16: Additional coverage
# ---------------------------------------------------------------------------


class TestAdditionalCoverage:
    def test_meta_goal_empty_description(self) -> None:
        from umh.runtime.goal_hierarchy import MetaGoal

        mg = MetaGoal(name="x", child_goal_types=("a",))
        assert mg.description == ""

    def test_meta_goal_custom_description(self) -> None:
        from umh.runtime.goal_hierarchy import MetaGoal

        mg = MetaGoal(name="x", child_goal_types=("a",), description="Business goals")
        assert mg.description == "Business goals"
        assert mg.to_dict()["description"] == "Business goals"

    def test_meta_goal_custom_aggregation_method(self) -> None:
        from umh.runtime.goal_hierarchy import MetaGoal

        mg = MetaGoal(name="x", child_goal_types=("a",), aggregation_method="max")
        assert mg.aggregation_method == "max"

    def test_hierarchy_type_to_meta_multi_parent(self) -> None:
        from umh.runtime.goal_hierarchy import GoalHierarchy, MetaGoal

        h = GoalHierarchy()
        h.register_meta_goal(MetaGoal(name="biz", child_goal_types=("revenue",)))
        h.register_meta_goal(MetaGoal(name="growth", child_goal_types=("revenue",)))
        parents = h.get_meta_goals_for_type("revenue")
        assert "biz" in parents
        assert "growth" in parents
        assert len(parents) == 2

    def test_hierarchy_overwrite_updates_children(self) -> None:
        from umh.runtime.goal_hierarchy import GoalHierarchy, MetaGoal

        h = GoalHierarchy()
        h.register_meta_goal(MetaGoal(name="biz", child_goal_types=("revenue",)))
        assert h.get_children("biz") == ("revenue",)
        h.register_meta_goal(MetaGoal(name="biz", child_goal_types=("revenue", "growth")))
        assert h.get_children("biz") == ("revenue", "growth")

    def test_compute_meta_score_reason_moderate(self) -> None:
        from umh.runtime.goal_hierarchy import GoalHierarchy, MetaGoal

        h = GoalHierarchy()
        h.register_meta_goal(MetaGoal(name="biz", child_goal_types=("rev",)))
        result = h.compute_meta_score("biz", {"rev": 0.7})
        assert result is not None
        assert "moderate" in result.reason

    def test_compute_meta_score_child_counts(self) -> None:
        from umh.runtime.goal_hierarchy import GoalHierarchy, MetaGoal

        h = GoalHierarchy()
        h.register_meta_goal(MetaGoal(name="biz", child_goal_types=("rev", "growth", "retention")))
        result = h.compute_meta_score("biz", {"rev": 0.8, "growth": 0.6})
        assert result is not None
        assert result.child_counts == {"rev": 1, "growth": 1}
        assert result.total_records == 2
        assert "2/3 child types contributing" in result.reason

    def test_scorer_empty_hierarchy(self) -> None:
        from umh.runtime.goal_hierarchy import GoalHierarchy, HierarchyScorer

        h = GoalHierarchy()
        scorer = HierarchyScorer(hierarchy=h, enabled=True)
        result = scorer.compute_factor(goal_type="revenue")
        assert result.factor == 1.0
        assert "not in any meta-goal" in result.reason

    def test_scorer_no_records_for_children(self) -> None:
        from umh.runtime.goal_hierarchy import GoalHierarchy, HierarchyScorer, MetaGoal
        from umh.runtime.goal_memory import GoalMemory
        from umh.runtime.goals import ReinforcementScorer

        h = GoalHierarchy()
        h.register_meta_goal(MetaGoal(name="biz", child_goal_types=("revenue",)))
        mem = GoalMemory()
        scorer = HierarchyScorer(
            hierarchy=h,
            goal_memory=mem,
            reinforcement_scorer=ReinforcementScorer(max_duration=100),
            enabled=True,
        )
        result = scorer.compute_factor(goal_type="revenue")
        assert result.factor == 1.0
        assert "no meta-goal data" in result.reason

    def test_scorer_reason_positive_direction(self) -> None:
        from umh.runtime.goal_hierarchy import GoalHierarchy, HierarchyScorer, MetaGoal
        from umh.runtime.goal_memory import GoalMemory, make_goal_record
        from umh.runtime.goals import ReinforcementScorer

        h = GoalHierarchy()
        h.register_meta_goal(MetaGoal(name="biz", child_goal_types=("revenue",)))
        mem = GoalMemory()
        mem.append(
            make_goal_record(
                goal_id="g1",
                goal_type="revenue",
                duration_ticks=100,
                completed=True,
                success_rate=1.0,
                identity_alignment=1.0,
                reward=1.0,
            )
        )
        scorer = HierarchyScorer(
            hierarchy=h,
            goal_memory=mem,
            reinforcement_scorer=ReinforcementScorer(max_duration=100),
            enabled=True,
        )
        result = scorer.compute_factor(goal_type="revenue")
        assert "neutral" in result.reason

    def test_scorer_reason_negative_direction(self) -> None:
        from umh.runtime.goal_hierarchy import GoalHierarchy, HierarchyScorer, MetaGoal
        from umh.runtime.goal_memory import GoalMemory, make_goal_record
        from umh.runtime.goals import ReinforcementScorer

        h = GoalHierarchy()
        h.register_meta_goal(MetaGoal(name="biz", child_goal_types=("revenue",)))
        mem = GoalMemory()
        mem.append(
            make_goal_record(
                goal_id="g1",
                goal_type="revenue",
                duration_ticks=50,
                completed=True,
                success_rate=0.5,
                identity_alignment=0.5,
                reward=0.2,
            )
        )
        scorer = HierarchyScorer(
            hierarchy=h,
            goal_memory=mem,
            reinforcement_scorer=ReinforcementScorer(max_duration=100),
            enabled=True,
        )
        result = scorer.compute_factor(goal_type="revenue")
        assert "penalty" in result.reason

    def test_meta_goal_score_to_dict_rounding(self) -> None:
        from umh.runtime.goal_hierarchy import MetaGoalScore

        s = MetaGoalScore("b", 0.123456789, {"r": 0.987654321}, {"r": 1}, 1, "reason")
        d = s.to_dict()
        assert d["score"] == 0.1235
        assert d["child_scores"]["r"] == 0.9877

    def test_hierarchy_influence_to_dict_rounding(self) -> None:
        from umh.runtime.goal_hierarchy import HierarchyInfluence

        h = HierarchyInfluence(
            factor=1.123456789,
            meta_goal_scores={"b": 0.987654321},
            contributing_types=["r"],
            reason="test",
        )
        d = h.to_dict()
        assert d["factor"] == 1.1235
        assert d["meta_goal_scores"]["b"] == 0.9877

    def test_meta_goal_weight_in_to_dict(self) -> None:
        from umh.runtime.goal_hierarchy import MetaGoal

        mg = MetaGoal(name="x", child_goal_types=("a",), weight=0.333333)
        d = mg.to_dict()
        assert d["weight"] == 0.3333

    def test_goal_memory_query_by_meta_goal_multiple_types(self) -> None:
        from umh.runtime.goal_memory import GoalMemory, make_goal_record

        mem = GoalMemory()
        mem.set_type_meta_mapping("revenue", ["biz"])
        mem.set_type_meta_mapping("growth", ["biz"])
        mem.append(
            make_goal_record(
                goal_id="g1",
                goal_type="revenue",
                duration_ticks=10,
                completed=True,
                success_rate=1.0,
            )
        )
        mem.append(
            make_goal_record(
                goal_id="g2",
                goal_type="growth",
                duration_ticks=10,
                completed=True,
                success_rate=0.8,
            )
        )
        mem.append(
            make_goal_record(
                goal_id="g3",
                goal_type="other",
                duration_ticks=10,
                completed=True,
                success_rate=0.5,
            )
        )
        results = mem.query_by_meta_goal("biz")
        assert len(results) == 2
        assert {r.goal_type for r in results} == {"revenue", "growth"}

    def test_goal_memory_grouped_stats_ordering(self) -> None:
        from umh.runtime.goal_memory import GoalMemory, make_goal_record

        mem = GoalMemory()
        mem.set_type_meta_mapping("zeta", ["group"])
        mem.set_type_meta_mapping("alpha", ["group"])
        mem.append(
            make_goal_record(
                goal_id="g1",
                goal_type="zeta",
                duration_ticks=10,
                completed=True,
                success_rate=1.0,
            )
        )
        mem.append(
            make_goal_record(
                goal_id="g2",
                goal_type="alpha",
                duration_ticks=10,
                completed=True,
                success_rate=0.8,
            )
        )
        stats = mem.compute_grouped_stats("group")
        assert len(stats) == 2
        assert stats[0].goal_type == "alpha"
        assert stats[1].goal_type == "zeta"

    def test_has_path_no_path(self) -> None:
        from umh.runtime.goal_hierarchy import GoalHierarchy, MetaGoal

        h = GoalHierarchy()
        h.register_meta_goal(MetaGoal(name="a", child_goal_types=("x",)))
        h.register_meta_goal(MetaGoal(name="b", child_goal_types=("y",)))
        assert not h._has_path("a", "b")
        assert not h._has_path("b", "a")

    def test_cycle_detection_long_chain(self) -> None:
        from umh.runtime.goal_hierarchy import CycleError, GoalHierarchy, MetaGoal

        h = GoalHierarchy()
        h.register_meta_goal(MetaGoal(name="a", child_goal_types=("b",)))
        h.register_meta_goal(MetaGoal(name="b", child_goal_types=("c",)))
        h.register_meta_goal(MetaGoal(name="c", child_goal_types=("d",)))
        with pytest.raises(CycleError):
            h.register_meta_goal(MetaGoal(name="d", child_goal_types=("a",)))

    def test_scorer_weight_affects_factor(self) -> None:
        from umh.runtime.goal_hierarchy import GoalHierarchy, HierarchyScorer, MetaGoal
        from umh.runtime.goal_memory import GoalMemory, make_goal_record
        from umh.runtime.goals import ReinforcementScorer

        mem = GoalMemory()
        mem.append(
            make_goal_record(
                goal_id="g1",
                goal_type="revenue",
                duration_ticks=50,
                completed=True,
                success_rate=0.5,
                identity_alignment=0.5,
                reward=0.2,
            )
        )

        h_low = GoalHierarchy()
        h_low.register_meta_goal(MetaGoal(name="biz", child_goal_types=("revenue",), weight=0.1))
        scorer_low = HierarchyScorer(
            hierarchy=h_low,
            goal_memory=mem,
            reinforcement_scorer=ReinforcementScorer(max_duration=100),
            enabled=True,
        )

        h_high = GoalHierarchy()
        h_high.register_meta_goal(MetaGoal(name="biz", child_goal_types=("revenue",), weight=1.0))
        scorer_high = HierarchyScorer(
            hierarchy=h_high,
            goal_memory=mem,
            reinforcement_scorer=ReinforcementScorer(max_duration=100),
            enabled=True,
        )

        r_low = scorer_low.compute_factor(goal_type="revenue")
        r_high = scorer_high.compute_factor(goal_type="revenue")
        assert abs(r_low.factor - 1.0) < abs(r_high.factor - 1.0)
