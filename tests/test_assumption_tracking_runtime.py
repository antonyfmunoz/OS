"""Tests for Campaign 9.2 — Assumption Tracking Runtime."""

from __future__ import annotations

import os
import sys
import time

import pytest

sys.path.insert(0, "/opt/OS")

from substrate.organism.assumption_tracking_runtime import (
    AssumptionRecord,
    AssumptionStatus,
    AssumptionTrackingRuntime,
)


# ── AssumptionStatus ──────────────────────────────────────────────────────


class TestAssumptionStatus:
    def test_values(self) -> None:
        assert AssumptionStatus.ACTIVE.value == "active"
        assert AssumptionStatus.VALIDATED.value == "validated"
        assert AssumptionStatus.INVALIDATED.value == "invalidated"
        assert AssumptionStatus.UNKNOWN.value == "unknown"

    def test_count(self) -> None:
        assert len(AssumptionStatus) == 4

    def test_string_enum(self) -> None:
        assert isinstance(AssumptionStatus.ACTIVE, str)
        assert AssumptionStatus.ACTIVE == "active"


# ── AssumptionRecord ──────────────────────────────────────────────────────


class TestAssumptionRecord:
    def test_defaults(self) -> None:
        a = AssumptionRecord()
        assert a.assumption_id.startswith("asm-")
        assert a.statement == ""
        assert a.status == "active"
        assert a.decision_refs == []
        assert a.evidence_for == []
        assert a.evidence_against == []

    def test_to_dict_keys(self) -> None:
        a = AssumptionRecord()
        keys = set(a.to_dict().keys())
        expected = {
            "assumption_id", "statement", "decision_refs", "goal_refs",
            "status", "evidence_for", "evidence_against", "source",
            "tags", "created_at", "updated_at",
        }
        assert keys == expected

    def test_to_dict_values(self) -> None:
        a = AssumptionRecord(
            statement="Pricing stays viable",
            decision_refs=["sd-1"],
            tags=["cost"],
        )
        out = a.to_dict()
        assert out["statement"] == "Pricing stays viable"
        assert out["decision_refs"] == ["sd-1"]
        assert out["tags"] == ["cost"]

    def test_from_dict_round_trip(self) -> None:
        original = AssumptionRecord(
            statement="Clerk pricing remains viable",
            decision_refs=["sd-1"],
            goal_refs=["g-1"],
            status="validated",
            evidence_for=["Pricing unchanged Q1"],
            evidence_against=[],
            source="operator",
            tags=["cost", "auth"],
        )
        restored = AssumptionRecord.from_dict(original.to_dict())
        assert restored.statement == original.statement
        assert restored.decision_refs == original.decision_refs
        assert restored.goal_refs == original.goal_refs
        assert restored.status == original.status
        assert restored.evidence_for == original.evidence_for
        assert restored.source == original.source
        assert restored.tags == original.tags

    def test_from_dict_defaults(self) -> None:
        a = AssumptionRecord.from_dict({})
        assert a.statement == ""
        assert a.status == "active"
        assert a.decision_refs == []

    def test_unique_ids(self) -> None:
        a1 = AssumptionRecord()
        a2 = AssumptionRecord()
        assert a1.assumption_id != a2.assumption_id

    def test_to_dict_immutability(self) -> None:
        a = AssumptionRecord(decision_refs=["sd-1"])
        out = a.to_dict()
        out["decision_refs"].append("sd-2")
        assert a.decision_refs == ["sd-1"]


# ── AssumptionTrackingRuntime ─────────────────────────────────────────────


class TestAssumptionTrackingRuntime:
    @pytest.fixture()
    def tmp_dir(self, tmp_path: str) -> str:
        return str(tmp_path)

    @pytest.fixture()
    def runtime(self, tmp_dir: str) -> AssumptionTrackingRuntime:
        return AssumptionTrackingRuntime(data_dir=tmp_dir)

    def test_add_and_get(self, runtime: AssumptionTrackingRuntime) -> None:
        a = AssumptionRecord(statement="Pricing viable")
        result = runtime.add(a)
        assert result.statement == "Pricing viable"
        assert result.updated_at > 0
        fetched = runtime.get(a.assumption_id)
        assert fetched is not None
        assert fetched.statement == "Pricing viable"

    def test_get_missing(self, runtime: AssumptionTrackingRuntime) -> None:
        assert runtime.get("nonexistent") is None

    def test_list_all(self, runtime: AssumptionTrackingRuntime) -> None:
        runtime.add(AssumptionRecord(statement="A"))
        runtime.add(AssumptionRecord(statement="B"))
        all_a = runtime.list_assumptions()
        assert len(all_a) == 2

    def test_list_by_status(self, runtime: AssumptionTrackingRuntime) -> None:
        runtime.add(AssumptionRecord(statement="A", status="active"))
        runtime.add(AssumptionRecord(statement="B", status="invalidated"))
        active = runtime.list_assumptions(status="active")
        assert len(active) == 1
        assert active[0].statement == "A"

    def test_update_status(self, runtime: AssumptionTrackingRuntime) -> None:
        a = AssumptionRecord(statement="Test")
        runtime.add(a)
        assert runtime.update_status(
            a.assumption_id, AssumptionStatus.VALIDATED, "Evidence found"
        )
        fetched = runtime.get(a.assumption_id)
        assert fetched is not None
        assert fetched.status == "validated"
        assert "Evidence found" in fetched.evidence_for

    def test_update_status_invalidated_adds_evidence_against(
        self, runtime: AssumptionTrackingRuntime
    ) -> None:
        a = AssumptionRecord(statement="Test")
        runtime.add(a)
        runtime.update_status(
            a.assumption_id, AssumptionStatus.INVALIDATED, "Price doubled"
        )
        fetched = runtime.get(a.assumption_id)
        assert fetched is not None
        assert fetched.status == "invalidated"
        assert "Price doubled" in fetched.evidence_against
        assert fetched.evidence_for == []

    def test_update_status_missing(
        self, runtime: AssumptionTrackingRuntime
    ) -> None:
        assert not runtime.update_status(
            "nonexistent", AssumptionStatus.VALIDATED
        )

    def test_update_status_no_evidence(
        self, runtime: AssumptionTrackingRuntime
    ) -> None:
        a = AssumptionRecord(statement="Test")
        runtime.add(a)
        runtime.update_status(a.assumption_id, AssumptionStatus.UNKNOWN)
        fetched = runtime.get(a.assumption_id)
        assert fetched is not None
        assert fetched.status == "unknown"
        assert fetched.evidence_for == []
        assert fetched.evidence_against == []

    def test_assumptions_for_decision(
        self, runtime: AssumptionTrackingRuntime
    ) -> None:
        runtime.add(AssumptionRecord(statement="A", decision_refs=["sd-1"]))
        runtime.add(AssumptionRecord(statement="B", decision_refs=["sd-2"]))
        runtime.add(
            AssumptionRecord(statement="C", decision_refs=["sd-1", "sd-2"])
        )
        result = runtime.assumptions_for_decision("sd-1")
        assert len(result) == 2
        stmts = {a.statement for a in result}
        assert stmts == {"A", "C"}

    def test_invalidated(self, runtime: AssumptionTrackingRuntime) -> None:
        runtime.add(AssumptionRecord(statement="A", status="active"))
        runtime.add(AssumptionRecord(statement="B", status="invalidated"))
        runtime.add(AssumptionRecord(statement="C", status="invalidated"))
        inv = runtime.invalidated()
        assert len(inv) == 2

    def test_active(self, runtime: AssumptionTrackingRuntime) -> None:
        runtime.add(AssumptionRecord(statement="A", status="active"))
        runtime.add(AssumptionRecord(statement="B", status="invalidated"))
        act = runtime.active()
        assert len(act) == 1
        assert act[0].statement == "A"

    def test_summary_keys(self, runtime: AssumptionTrackingRuntime) -> None:
        runtime.add(AssumptionRecord(statement="A"))
        s = runtime.summary()
        expected = {"total", "by_status", "invalidated_count", "generated_at"}
        assert set(s.keys()) == expected

    def test_summary_counts(self, runtime: AssumptionTrackingRuntime) -> None:
        runtime.add(AssumptionRecord(status="active"))
        runtime.add(AssumptionRecord(status="invalidated"))
        runtime.add(AssumptionRecord(status="invalidated"))
        s = runtime.summary()
        assert s["total"] == 3
        assert s["invalidated_count"] == 2
        assert s["by_status"]["active"] == 1

    def test_persistence_round_trip(self, tmp_dir: str) -> None:
        r1 = AssumptionTrackingRuntime(data_dir=tmp_dir)
        a = AssumptionRecord(statement="Persist Test", status="active")
        r1.add(a)

        r2 = AssumptionTrackingRuntime(data_dir=tmp_dir)
        fetched = r2.get(a.assumption_id)
        assert fetched is not None
        assert fetched.statement == "Persist Test"

    def test_persistence_file_created(self, tmp_dir: str) -> None:
        r = AssumptionTrackingRuntime(data_dir=tmp_dir)
        r.add(AssumptionRecord(statement="Test"))
        assert os.path.exists(os.path.join(tmp_dir, "assumptions.jsonl"))

    def test_empty_runtime(self, runtime: AssumptionTrackingRuntime) -> None:
        assert runtime.list_assumptions() == []
        assert runtime.invalidated() == []
        assert runtime.active() == []
        s = runtime.summary()
        assert s["total"] == 0
        assert s["invalidated_count"] == 0

    def test_list_sorted_by_created_at(
        self, runtime: AssumptionTrackingRuntime
    ) -> None:
        a1 = AssumptionRecord(statement="Old", created_at=100.0)
        a2 = AssumptionRecord(statement="New", created_at=200.0)
        runtime.add(a1)
        runtime.add(a2)
        results = runtime.list_assumptions()
        assert results[0].statement == "New"
        assert results[1].statement == "Old"
