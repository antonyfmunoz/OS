"""Tests for Gate 4 — IntentRuntime (Workstation Convergence).

Tests intent capture, refinement, supersession, lineage, conflict
detection, alignment scoring, and session context.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from substrate.operator.intent_runtime import (
    CanonicalIntent,
    CanonicalIntentStatus,
    ConflictType,
    IntentConflict,
    IntentRuntime,
    IntentScope,
    _JSONLStore,
)

IntentStatus = CanonicalIntentStatus


@pytest.fixture
def tmp_dir():
    with tempfile.TemporaryDirectory() as d:
        yield d


@pytest.fixture
def runtime(tmp_dir):
    intents_path = os.path.join(tmp_dir, "intents.jsonl")
    conflicts_path = os.path.join(tmp_dir, "conflicts.jsonl")
    return IntentRuntime(intents_path=intents_path, conflicts_path=conflicts_path)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Type tests
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestIntentScope:
    def test_all_scopes_exist(self):
        assert set(IntentScope) == {
            IntentScope.EMPIRE,
            IntentScope.PRODUCT,
            IntentScope.ARCHITECTURE,
            IntentScope.ENGINEERING,
            IntentScope.SESSION,
        }

    def test_scope_values(self):
        assert IntentScope.EMPIRE.value == "empire"
        assert IntentScope.SESSION.value == "session"


class TestIntentStatus:
    def test_all_statuses(self):
        assert set(IntentStatus) == {
            IntentStatus.ACTIVE,
            IntentStatus.SUPERSEDED,
            IntentStatus.ACHIEVED,
            IntentStatus.ABANDONED,
        }


class TestCanonicalIntent:
    def test_default_creation(self):
        intent = CanonicalIntent()
        assert intent.intent_id.startswith("intent-")
        assert intent.scope == IntentScope.SESSION
        assert intent.status == IntentStatus.ACTIVE
        assert intent.version == 1

    def test_roundtrip(self):
        intent = CanonicalIntent(
            scope=IntentScope.ARCHITECTURE,
            statement="Build the workstation convergence runtime",
            success_criteria=["All 13 capabilities accessible"],
            tags=["gate-4"],
        )
        d = intent.to_dict()
        restored = CanonicalIntent.from_dict(d)
        assert restored.scope == IntentScope.ARCHITECTURE
        assert restored.statement == "Build the workstation convergence runtime"
        assert restored.tags == ["gate-4"]

    def test_from_dict_missing_fields(self):
        d = {"intent_id": "test-1", "scope": "empire", "statement": "test"}
        intent = CanonicalIntent.from_dict(d)
        assert intent.success_criteria == []
        assert intent.tags == []


class TestIntentConflict:
    def test_is_resolved(self):
        c = IntentConflict()
        assert not c.is_resolved
        c.resolution = "resolved by operator"
        assert c.is_resolved

    def test_roundtrip(self):
        c = IntentConflict(
            intent_a_id="a", intent_b_id="b",
            conflict_type=ConflictType.CONTRADICTION,
            description="test",
        )
        d = c.to_dict()
        restored = IntentConflict.from_dict(d)
        assert restored.conflict_type == ConflictType.CONTRADICTION


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# JSONL Store tests
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestJSONLStore:
    def test_append_and_load(self, tmp_dir):
        path = os.path.join(tmp_dir, "test.jsonl")
        store = _JSONLStore(path)
        store.append({"key": "value1"})
        store.append({"key": "value2"})
        records = store.load_all()
        assert len(records) == 2
        assert records[0]["key"] == "value1"

    def test_rewrite(self, tmp_dir):
        path = os.path.join(tmp_dir, "test.jsonl")
        store = _JSONLStore(path)
        store.append({"key": "original"})
        store.rewrite([{"key": "replaced"}])
        records = store.load_all()
        assert len(records) == 1
        assert records[0]["key"] == "replaced"

    def test_empty_file(self, tmp_dir):
        path = os.path.join(tmp_dir, "empty.jsonl")
        store = _JSONLStore(path)
        assert store.load_all() == []

    def test_malformed_lines_skipped(self, tmp_dir):
        path = os.path.join(tmp_dir, "bad.jsonl")
        with open(path, "w") as f:
            f.write('{"good": true}\n')
            f.write("not json\n")
            f.write('{"also_good": true}\n')
        store = _JSONLStore(path)
        records = store.load_all()
        assert len(records) == 2


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Capture tests
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestCapture:
    def test_basic_capture(self, runtime):
        intent = runtime.capture(
            statement="Build UMH as isomorphic reality approximation",
            scope=IntentScope.EMPIRE,
        )
        assert intent.intent_id.startswith("intent-")
        assert intent.scope == IntentScope.EMPIRE
        assert intent.status == IntentStatus.ACTIVE
        assert intent.version == 1

    def test_capture_with_criteria(self, runtime):
        intent = runtime.capture(
            statement="Gate 4 workstation convergence",
            scope=IntentScope.ARCHITECTURE,
            success_criteria=["13 canonical capabilities", "IntentRuntime operational"],
            tags=["gate-4"],
        )
        assert len(intent.success_criteria) == 2
        assert "gate-4" in intent.tags

    def test_capture_with_parent(self, runtime):
        parent = runtime.capture(
            statement="Empire vision", scope=IntentScope.EMPIRE,
        )
        child = runtime.capture(
            statement="Product direction", scope=IntentScope.PRODUCT,
            parent_id=parent.intent_id,
        )
        assert child.parent_id == parent.intent_id

    def test_capture_persists(self, runtime):
        runtime.capture(
            statement="Persisted intent", scope=IntentScope.SESSION,
        )
        retrieved = runtime.retrieve(scope=IntentScope.SESSION)
        assert len(retrieved) == 1
        assert retrieved[0].statement == "Persisted intent"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Refine tests
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestRefine:
    def test_refine_updates_statement(self, runtime):
        intent = runtime.capture(
            statement="Build cockpit", scope=IntentScope.ARCHITECTURE,
        )
        refined = runtime.refine(intent.intent_id, new_statement="Build workstation")
        assert refined is not None
        assert refined.statement == "Build workstation"
        assert refined.version == 2

    def test_refine_preserves_unchanged(self, runtime):
        intent = runtime.capture(
            statement="Original",
            scope=IntentScope.PRODUCT,
            tags=["keep-this"],
        )
        refined = runtime.refine(intent.intent_id, new_rationale="Updated rationale")
        assert refined is not None
        assert refined.statement == "Original"
        assert refined.tags == ["keep-this"]

    def test_refine_nonexistent_returns_none(self, runtime):
        result = runtime.refine("nonexistent-id", new_statement="test")
        assert result is None

    def test_refine_bumps_version(self, runtime):
        intent = runtime.capture(statement="v1", scope=IntentScope.SESSION)
        runtime.refine(intent.intent_id, new_statement="v2")
        runtime.refine(intent.intent_id, new_statement="v3")
        latest = runtime.get(intent.intent_id)
        assert latest is not None
        assert latest.version == 3


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Supersede tests
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestSupersede:
    def test_supersede_marks_original(self, runtime):
        old = runtime.capture(
            statement="Cockpit convergence", scope=IntentScope.ARCHITECTURE,
        )
        new = runtime.capture(
            statement="Workstation convergence", scope=IntentScope.ARCHITECTURE,
        )
        ok = runtime.supersede(old.intent_id, new.intent_id)
        assert ok

        old_updated = runtime.get(old.intent_id)
        assert old_updated is not None
        assert old_updated.status == IntentStatus.SUPERSEDED
        assert old_updated.superseded_by == new.intent_id

    def test_supersede_nonexistent_fails(self, runtime):
        ok = runtime.supersede("nonexistent", "also-nonexistent")
        assert not ok


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Status transition tests
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestStatusTransitions:
    def test_achieve_with_evidence(self, runtime):
        intent = runtime.capture(
            statement="Ship gate 3", scope=IntentScope.ENGINEERING,
        )
        ok = runtime.achieve(intent.intent_id, evidence=["103 tests pass"])
        assert ok
        achieved = runtime.get(intent.intent_id)
        assert achieved is not None
        assert achieved.status == IntentStatus.ACHIEVED
        assert "103 tests pass" in achieved.evidence

    def test_abandon_with_reason(self, runtime):
        intent = runtime.capture(
            statement="Old approach", scope=IntentScope.SESSION,
        )
        ok = runtime.abandon(intent.intent_id, reason="replaced by better approach")
        assert ok
        abandoned = runtime.get(intent.intent_id)
        assert abandoned is not None
        assert abandoned.status == IntentStatus.ABANDONED

    def test_achieve_nonexistent_fails(self, runtime):
        assert not runtime.achieve("fake-id")

    def test_abandon_nonexistent_fails(self, runtime):
        assert not runtime.abandon("fake-id")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Retrieval tests
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestRetrieval:
    def test_retrieve_by_scope(self, runtime):
        runtime.capture(statement="Empire vision", scope=IntentScope.EMPIRE)
        runtime.capture(statement="Session task", scope=IntentScope.SESSION)
        empire = runtime.retrieve(scope=IntentScope.EMPIRE)
        assert len(empire) == 1
        assert empire[0].scope == IntentScope.EMPIRE

    def test_retrieve_by_status(self, runtime):
        a = runtime.capture(statement="Active one", scope=IntentScope.SESSION)
        b = runtime.capture(statement="To abandon", scope=IntentScope.SESSION)
        runtime.abandon(b.intent_id)
        active = runtime.retrieve(status="active")
        assert len(active) == 1
        assert active[0].intent_id == a.intent_id

    def test_active_by_scope(self, runtime):
        runtime.capture(statement="E1", scope=IntentScope.EMPIRE)
        runtime.capture(statement="P1", scope=IntentScope.PRODUCT)
        runtime.capture(statement="S1", scope=IntentScope.SESSION)
        by_scope = runtime.active_by_scope()
        assert len(by_scope["empire"]) == 1
        assert len(by_scope["product"]) == 1
        assert len(by_scope["session"]) == 1
        assert len(by_scope["architecture"]) == 0

    def test_get_nonexistent(self, runtime):
        assert runtime.get("nonexistent") is None


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Lineage tests
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestLineage:
    def test_full_lineage_chain(self, runtime):
        empire = runtime.capture(
            statement="11-figure empire", scope=IntentScope.EMPIRE,
        )
        product = runtime.capture(
            statement="Initiate Arena $10K/month",
            scope=IntentScope.PRODUCT,
            parent_id=empire.intent_id,
        )
        arch = runtime.capture(
            statement="Gate 4 workstation convergence",
            scope=IntentScope.ARCHITECTURE,
            parent_id=product.intent_id,
        )
        eng = runtime.capture(
            statement="Build IntentRuntime",
            scope=IntentScope.ENGINEERING,
            parent_id=arch.intent_id,
        )

        chain = runtime.lineage(eng.intent_id)
        assert len(chain) == 4
        assert chain[0].intent_id == eng.intent_id
        assert chain[1].intent_id == arch.intent_id
        assert chain[2].intent_id == product.intent_id
        assert chain[3].intent_id == empire.intent_id

    def test_lineage_handles_missing_parent(self, runtime):
        intent = runtime.capture(
            statement="Orphaned",
            scope=IntentScope.SESSION,
            parent_id="nonexistent",
        )
        chain = runtime.lineage(intent.intent_id)
        assert len(chain) == 1

    def test_lineage_nonexistent_intent(self, runtime):
        chain = runtime.lineage("nonexistent")
        assert chain == []

    def test_lineage_cycle_protection(self, runtime):
        a = runtime.capture(statement="A", scope=IntentScope.SESSION)
        b = runtime.capture(
            statement="B", scope=IntentScope.SESSION, parent_id=a.intent_id,
        )
        chain = runtime.lineage(b.intent_id)
        assert len(chain) == 2


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Conflict detection tests
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestConflictDetection:
    def test_contradiction_detected(self, runtime):
        runtime.capture(
            statement="Always deploy to production immediately",
            scope=IntentScope.ENGINEERING,
        )
        runtime.capture(
            statement="Never deploy to production immediately",
            scope=IntentScope.ENGINEERING,
        )
        conflicts = runtime.conflicts()
        assert len(conflicts) >= 1
        assert any(c.conflict_type == ConflictType.CONTRADICTION for c in conflicts)

    def test_scope_overlap_detected(self, runtime):
        runtime.capture(
            statement="build the cockpit convergence runtime for UMH workstation",
            scope=IntentScope.ARCHITECTURE,
        )
        runtime.capture(
            statement="build the cockpit convergence runtime for the UMH workstation surface",
            scope=IntentScope.ARCHITECTURE,
        )
        conflicts = runtime.conflicts()
        assert len(conflicts) >= 1

    def test_no_conflict_for_different_scopes(self, runtime):
        runtime.capture(
            statement="Build revenue", scope=IntentScope.EMPIRE,
        )
        runtime.capture(
            statement="Build revenue", scope=IntentScope.PRODUCT,
        )
        conflicts = runtime.conflicts()
        contradiction_conflicts = [
            c for c in conflicts if c.conflict_type == ConflictType.CONTRADICTION
        ]
        assert len(contradiction_conflicts) == 0

    def test_resolve_conflict(self, runtime):
        runtime.capture(
            statement="Always use microservices architecture",
            scope=IntentScope.ARCHITECTURE,
        )
        runtime.capture(
            statement="Never use microservices architecture",
            scope=IntentScope.ARCHITECTURE,
        )
        conflicts = runtime.conflicts()
        assert len(conflicts) >= 1

        cid = conflicts[0].conflict_id
        ok = runtime.resolve_conflict(cid, "Operator chose monolith")
        assert ok

        remaining = runtime.conflicts()
        assert len(remaining) == 0

    def test_resolve_nonexistent_conflict(self, runtime):
        assert not runtime.resolve_conflict("fake-conflict", "resolution")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Alignment scoring tests
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestAlignmentScoring:
    def test_aligned_description(self, runtime):
        runtime.capture(
            statement="Build cockpit convergence runtime with 13 capabilities",
            scope=IntentScope.ARCHITECTURE,
        )
        score = runtime.alignment_score(
            "cockpit convergence runtime capabilities",
        )
        assert score > 0.3

    def test_unaligned_description(self, runtime):
        runtime.capture(
            statement="Build cockpit convergence runtime",
            scope=IntentScope.ARCHITECTURE,
        )
        score = runtime.alignment_score(
            "completely unrelated database migration task",
        )
        assert score < 0.5

    def test_no_active_intents_returns_zero(self, runtime):
        score = runtime.alignment_score("anything")
        assert score == 0.0

    def test_scope_filter(self, runtime):
        runtime.capture(
            statement="Build infrastructure",
            scope=IntentScope.ARCHITECTURE,
        )
        runtime.capture(
            statement="Ship product",
            scope=IntentScope.PRODUCT,
        )
        score = runtime.alignment_score(
            "infrastructure changes",
            scope=IntentScope.ARCHITECTURE,
        )
        assert score > 0.0


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Session context tests
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestSessionContext:
    def test_context_structure(self, runtime):
        runtime.capture(statement="E1", scope=IntentScope.EMPIRE)
        runtime.capture(statement="S1", scope=IntentScope.SESSION)
        ctx = runtime.context_for_session()
        assert "active_intents" in ctx
        assert "total_active" in ctx
        assert ctx["total_active"] == 2
        assert "conflict_count" in ctx

    def test_empty_context(self, runtime):
        ctx = runtime.context_for_session()
        assert ctx["total_active"] == 0

    def test_summary(self, runtime):
        runtime.capture(statement="E1", scope=IntentScope.EMPIRE)
        runtime.capture(statement="A1", scope=IntentScope.ARCHITECTURE)
        s = runtime.summary()
        assert s["total"] == 2
        assert s["active"] == 2
        assert s["by_scope"]["empire"] == 1
        assert s["by_scope"]["architecture"] == 1


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Integration tests
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestIntegration:
    def test_full_lifecycle(self, runtime):
        """Capture → refine → supersede → achieve lifecycle."""
        empire = runtime.capture(
            statement="Build 11-figure empire by 50",
            scope=IntentScope.EMPIRE,
            success_criteria=["$10K/month net profit"],
        )

        product = runtime.capture(
            statement="Initiate Arena as first revenue source",
            scope=IntentScope.PRODUCT,
            parent_id=empire.intent_id,
        )

        runtime.refine(
            product.intent_id,
            new_criteria=["$10K/month net", "Scalable beyond founder effort"],
        )

        arch_v1 = runtime.capture(
            statement="Cockpit convergence",
            scope=IntentScope.ARCHITECTURE,
            parent_id=product.intent_id,
        )

        arch_v2 = runtime.capture(
            statement="Workstation convergence with IntentRuntime",
            scope=IntentScope.ARCHITECTURE,
            parent_id=product.intent_id,
        )
        runtime.supersede(arch_v1.intent_id, arch_v2.intent_id)

        chain = runtime.lineage(arch_v2.intent_id)
        assert len(chain) == 3

        runtime.achieve(arch_v2.intent_id, evidence=["Gate 4 shipped"])
        achieved = runtime.get(arch_v2.intent_id)
        assert achieved is not None
        assert achieved.status == IntentStatus.ACHIEVED

    def test_session_survives_reload(self, tmp_dir):
        """Intents persist and survive runtime re-creation."""
        intents_path = os.path.join(tmp_dir, "intents.jsonl")
        conflicts_path = os.path.join(tmp_dir, "conflicts.jsonl")

        rt1 = IntentRuntime(intents_path=intents_path, conflicts_path=conflicts_path)
        rt1.capture(statement="Persistent intent", scope=IntentScope.EMPIRE)

        rt2 = IntentRuntime(intents_path=intents_path, conflicts_path=conflicts_path)
        intents = rt2.retrieve(scope=IntentScope.EMPIRE)
        assert len(intents) == 1
        assert intents[0].statement == "Persistent intent"

    def test_intent_preservation_acceptance(self, runtime):
        """Acceptance test: express intent, verify retrieval without reconstruction."""
        runtime.capture(
            statement="UMH is an isomorphic reality approximation",
            scope=IntentScope.EMPIRE,
            rationale="Not operational tooling — it models reality",
            success_criteria=["Stage 1 is indivisible organism"],
        )
        runtime.capture(
            statement="Gate 4 is Workstation Convergence Runtime",
            scope=IntentScope.ARCHITECTURE,
            rationale="Cockpit is not the center — intent is",
            success_criteria=["IntentRuntime prevents multi-chat drift"],
            tags=["gate-4"],
        )

        ctx = runtime.context_for_session()
        assert ctx["total_active"] == 2
        assert "empire" in ctx["active_intents"]
        assert "architecture" in ctx["active_intents"]

        empire_intents = ctx["active_intents"]["empire"]
        assert len(empire_intents) == 1
        assert "isomorphic reality" in empire_intents[0]["statement"]

    def test_canonical_types_registered(self):
        """Verify IntentRuntime types are in canonical registry."""
        from substrate.canonical_types import lookup
        for name in ["IntentScope", "CanonicalIntent", "IntentConflict",
                      "IntentRuntime", "ConflictType"]:
            result = lookup(name)
            assert result is not None, f"{name} not registered in canonical_types.py"
            assert any(
                "intent_runtime" in path for path in result
            ), f"{name} not pointing to intent_runtime"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Route tests (import/compile only, no HTTP)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestRouteImports:
    def test_intent_routes_importable(self):
        from transports.api.cockpit_intent_routes import intent_router
        assert intent_router is not None

    def test_intent_runtime_importable(self):
        from substrate.operator.intent_runtime import IntentRuntime
        rt = IntentRuntime.__new__(IntentRuntime)
        assert rt is not None

    def test_snapshot_runtime_importable(self):
        from substrate.operator.operator_snapshot_runtime import (
            OperatorQuestionSnapshot,
            OperatorSnapshotRuntime,
        )
        assert OperatorQuestionSnapshot is not None
        assert OperatorSnapshotRuntime is not None

    def test_attention_engine_importable(self):
        from substrate.operator.operator_attention_engine import (
            AttentionItem,
            OperatorAttentionEngine,
        )
        assert AttentionItem is not None
        assert OperatorAttentionEngine is not None


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Operator Snapshot Runtime tests (Workcell D)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestOperatorSnapshotRuntime:
    def test_snapshot_with_no_subsystems(self):
        from substrate.operator.operator_snapshot_runtime import OperatorSnapshotRuntime
        rt = OperatorSnapshotRuntime()
        snap = rt.snapshot()
        assert snap.generated_at > 0
        assert isinstance(snap.attention, list)
        assert isinstance(snap.changes, list)
        assert isinstance(snap.decisions, list)
        assert isinstance(snap.next_actions, list)

    def test_snapshot_to_dict(self):
        from substrate.operator.operator_snapshot_runtime import (
            OperatorQuestionSnapshot,
        )
        snap = OperatorQuestionSnapshot()
        d = snap.to_dict()
        assert "situation" in d
        assert "attention" in d
        assert "changes" in d
        assert "decisions" in d
        assert "next_actions" in d
        assert "generated_at" in d

    def test_snapshot_with_intent_runtime(self, tmp_dir):
        from substrate.operator.intent_runtime import IntentRuntime, IntentScope
        from substrate.operator.operator_snapshot_runtime import OperatorSnapshotRuntime

        intent_rt = IntentRuntime(
            intents_path=os.path.join(tmp_dir, "intents.jsonl"),
            conflicts_path=os.path.join(tmp_dir, "conflicts.jsonl"),
        )
        intent_rt.capture(
            statement="Test intent for snapshot",
            scope=IntentScope.ARCHITECTURE,
        )

        snap_rt = OperatorSnapshotRuntime(intent_runtime=intent_rt)
        snap = snap_rt.snapshot()
        sit = snap.situation
        assert sit.intent_alignment.get("total_active", 0) >= 1

    def test_situation_includes_intent_alignment(self, tmp_dir):
        from substrate.operator.intent_runtime import IntentRuntime, IntentScope
        from substrate.operator.operator_snapshot_runtime import OperatorSnapshotRuntime

        intent_rt = IntentRuntime(
            intents_path=os.path.join(tmp_dir, "intents.jsonl"),
            conflicts_path=os.path.join(tmp_dir, "conflicts.jsonl"),
        )
        intent_rt.capture(
            statement="Empire intent in snapshot",
            scope=IntentScope.EMPIRE,
        )

        snap_rt = OperatorSnapshotRuntime(intent_runtime=intent_rt)
        snap = snap_rt.snapshot()
        sit_dict = snap.situation.to_dict()
        assert "intent_alignment" in sit_dict

    def test_snapshot_types_registered(self):
        from substrate.canonical_types import lookup
        for name in ["OperatorQuestionSnapshot", "OperatorSnapshotRuntime"]:
            result = lookup(name)
            assert result is not None, f"{name} not in canonical_types"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Operator Attention Engine tests (Workcell E)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestOperatorAttentionEngine:
    def test_compute_with_no_subsystems(self):
        from substrate.operator.operator_attention_engine import OperatorAttentionEngine
        engine = OperatorAttentionEngine()
        items = engine.compute()
        assert isinstance(items, list)

    def test_attention_item_to_dict(self):
        from substrate.operator.operator_attention_engine import AttentionItem
        item = AttentionItem(
            category="approval",
            severity="high",
            title="Test approval",
            action_hint="Approve it",
            capability_link="approvals",
        )
        d = item.to_dict()
        assert d["category"] == "approval"
        assert d["severity"] == "high"
        assert d["capability_link"] == "approvals"

    def test_top_returns_subset(self):
        from substrate.operator.operator_attention_engine import OperatorAttentionEngine
        engine = OperatorAttentionEngine()
        top = engine.top(3)
        assert isinstance(top, list)
        assert len(top) <= 3

    def test_by_category_filters(self):
        from substrate.operator.operator_attention_engine import OperatorAttentionEngine
        engine = OperatorAttentionEngine()
        approvals = engine.by_category("approval")
        assert isinstance(approvals, list)

    def test_items_ranked_by_category_then_severity(self):
        from substrate.operator.operator_attention_engine import (
            AttentionItem,
            OperatorAttentionEngine,
        )

        class MockWorkRuntime:
            work_graph = None
            def blocked(self): return []
            def recovery(self): return []
            def active(self): return []

        class MockIntentRuntime:
            def conflicts(self, include_resolved=False): return []
            def active_by_scope(self): return {}
            def alignment_score(self, desc, scope=None): return 0.0

        engine = OperatorAttentionEngine(
            work_runtime=MockWorkRuntime(),
            intent_runtime=MockIntentRuntime(),
        )
        items = engine.compute()
        assert isinstance(items, list)

    def test_attention_types_registered(self):
        from substrate.canonical_types import lookup
        for name in ["AttentionItem", "OperatorAttentionEngine"]:
            result = lookup(name)
            assert result is not None, f"{name} not in canonical_types"
