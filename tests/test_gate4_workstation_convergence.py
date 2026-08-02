"""Gate 4 — Workstation Convergence Runtime — Validation Tests.

Tests cover:
  1. IntentRuntime: capture, refine, supersede, retrieve, lineage, conflict, alignment
  2. OperatorSnapshotRuntime: 5 operator questions (situation/attention/changes/decisions/next_actions)
  3. OperatorAttentionEngine: compute, top, by_category, ranking
  4. Route compilation: all new route files import cleanly
  5. Type coherence: all Gate 4 types registered in canonical_types
  6. Operator effectiveness: full Jarvis loop completable

Gate 4 — Workstation Convergence Runtime. Instance-agnostic.
"""

from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile

import pytest

sys.path.insert(0, os.environ.get("UMH_ROOT", "/opt/OS"))


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Fixtures
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


@pytest.fixture
def tmp_dir():
    d = tempfile.mkdtemp()
    yield d
    shutil.rmtree(d, ignore_errors=True)


@pytest.fixture
def intent_runtime(tmp_dir):
    from substrate.operator.intent_runtime import IntentRuntime
    return IntentRuntime(
        intents_path=os.path.join(tmp_dir, "intents.jsonl"),
        conflicts_path=os.path.join(tmp_dir, "conflicts.jsonl"),
    )


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 1. IntentRuntime
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestIntentRuntimeCapture:
    def test_capture_returns_canonical_intent(self, intent_runtime):
        from substrate.operator.intent_runtime import IntentScope
        intent = intent_runtime.capture("Build the thing", IntentScope.ENGINEERING)
        assert intent.intent_id.startswith("intent-")
        assert intent.statement == "Build the thing"
        assert intent.scope == IntentScope.ENGINEERING
        assert intent.version == 1

    def test_capture_with_all_fields(self, intent_runtime):
        from substrate.operator.intent_runtime import IntentScope
        intent = intent_runtime.capture(
            "Revenue goal",
            IntentScope.PRODUCT,
            rationale="Primary target",
            success_criteria=["10K/month"],
            parent_id="parent-123",
            tags=["revenue"],
        )
        assert intent.rationale == "Primary target"
        assert intent.success_criteria == ["10K/month"]
        assert intent.parent_id == "parent-123"
        assert intent.tags == ["revenue"]

    def test_capture_persists_to_jsonl(self, intent_runtime, tmp_dir):
        from substrate.operator.intent_runtime import IntentScope
        intent_runtime.capture("Test persistence", IntentScope.SESSION)
        path = os.path.join(tmp_dir, "intents.jsonl")
        assert os.path.exists(path)
        with open(path) as f:
            data = json.loads(f.readline())
        assert data["statement"] == "Test persistence"


class TestIntentRuntimeRefine:
    def test_refine_increments_version(self, intent_runtime):
        from substrate.operator.intent_runtime import IntentScope
        intent = intent_runtime.capture("Original", IntentScope.SESSION)
        refined = intent_runtime.refine(intent.intent_id, new_statement="Refined")
        assert refined is not None
        assert refined.version == 2
        assert refined.statement == "Refined"

    def test_refine_nonexistent_returns_none(self, intent_runtime):
        assert intent_runtime.refine("nonexistent-id") is None

    def test_refine_preserves_unchanged_fields(self, intent_runtime):
        from substrate.operator.intent_runtime import IntentScope
        intent = intent_runtime.capture(
            "Original", IntentScope.PRODUCT,
            rationale="Because",
            success_criteria=["done"],
        )
        refined = intent_runtime.refine(intent.intent_id, new_statement="New statement")
        assert refined.rationale == "Because"
        assert refined.success_criteria == ["done"]


class TestIntentRuntimeSupersede:
    def test_supersede_marks_original(self, intent_runtime):
        from substrate.operator.intent_runtime import IntentScope, CanonicalIntentStatus
        old = intent_runtime.capture("Old intent", IntentScope.PRODUCT)
        new = intent_runtime.capture("New intent", IntentScope.PRODUCT)
        ok = intent_runtime.supersede(old.intent_id, new.intent_id)
        assert ok
        updated = intent_runtime.get(old.intent_id)
        assert updated.status == CanonicalIntentStatus.SUPERSEDED
        assert updated.superseded_by == new.intent_id

    def test_supersede_nonexistent_returns_false(self, intent_runtime):
        assert intent_runtime.supersede("a", "b") is False


class TestIntentRuntimeRetrieve:
    def test_retrieve_by_scope(self, intent_runtime):
        from substrate.operator.intent_runtime import IntentScope
        intent_runtime.capture("E1", IntentScope.ENGINEERING)
        intent_runtime.capture("P1", IntentScope.PRODUCT)
        intent_runtime.capture("E2", IntentScope.ENGINEERING)
        eng = intent_runtime.retrieve(scope=IntentScope.ENGINEERING)
        assert len(eng) == 2

    def test_retrieve_active_only(self, intent_runtime):
        from substrate.operator.intent_runtime import IntentScope
        i1 = intent_runtime.capture("Active", IntentScope.SESSION)
        i2 = intent_runtime.capture("To abandon", IntentScope.SESSION)
        intent_runtime.abandon(i2.intent_id)
        active = intent_runtime.retrieve(scope=IntentScope.SESSION, status="active")
        assert len(active) == 1
        assert active[0].intent_id == i1.intent_id

    def test_active_by_scope(self, intent_runtime):
        from substrate.operator.intent_runtime import IntentScope
        intent_runtime.capture("Empire", IntentScope.EMPIRE)
        intent_runtime.capture("Product", IntentScope.PRODUCT)
        by_scope = intent_runtime.active_by_scope()
        assert len(by_scope["empire"]) == 1
        assert len(by_scope["product"]) == 1
        assert len(by_scope["session"]) == 0


class TestIntentRuntimeLineage:
    def test_lineage_walks_parent_chain(self, intent_runtime):
        from substrate.operator.intent_runtime import IntentScope
        empire = intent_runtime.capture("Empire", IntentScope.EMPIRE)
        product = intent_runtime.capture("Product", IntentScope.PRODUCT, parent_id=empire.intent_id)
        eng = intent_runtime.capture("Engineering", IntentScope.ENGINEERING, parent_id=product.intent_id)
        chain = intent_runtime.lineage(eng.intent_id)
        scopes = [i.scope.value for i in chain]
        assert scopes == ["engineering", "product", "empire"]

    def test_lineage_handles_orphan(self, intent_runtime):
        from substrate.operator.intent_runtime import IntentScope
        intent = intent_runtime.capture("Orphan", IntentScope.SESSION)
        chain = intent_runtime.lineage(intent.intent_id)
        assert len(chain) == 1


class TestIntentRuntimeConflicts:
    def test_detects_scope_overlap(self, intent_runtime):
        from substrate.operator.intent_runtime import IntentScope
        intent_runtime.capture(
            "Scale Initiate Arena to ten thousand per month",
            IntentScope.PRODUCT,
        )
        intent_runtime.capture(
            "Scale Initiate Arena to ten thousand per month immediately",
            IntentScope.PRODUCT,
        )
        conflicts = intent_runtime.conflicts()
        assert len(conflicts) >= 1
        assert any(c.conflict_type.value == "scope_overlap" for c in conflicts)

    def test_resolve_conflict(self, intent_runtime):
        from substrate.operator.intent_runtime import IntentScope
        intent_runtime.capture("A thing one way", IntentScope.PRODUCT)
        intent_runtime.capture("A thing one way again", IntentScope.PRODUCT)
        conflicts = intent_runtime.conflicts()
        if conflicts:
            ok = intent_runtime.resolve_conflict(conflicts[0].conflict_id, "Merged into one")
            assert ok
            remaining = intent_runtime.conflicts(include_resolved=False)
            assert len(remaining) == 0

    def test_no_false_positive_different_scopes(self, intent_runtime):
        from substrate.operator.intent_runtime import IntentScope
        intent_runtime.capture("Build UMH substrate", IntentScope.ARCHITECTURE)
        intent_runtime.capture("Ship Initiate Arena", IntentScope.PRODUCT)
        conflicts = intent_runtime.conflicts()
        assert len(conflicts) == 0


class TestIntentRuntimeAlignment:
    def test_aligned_work_scores_high(self, intent_runtime):
        from substrate.operator.intent_runtime import IntentScope
        intent_runtime.capture(
            "Scale revenue pipeline for Initiate Arena outreach",
            IntentScope.PRODUCT,
            success_criteria=["10K monthly revenue"],
        )
        score = intent_runtime.alignment_score("Revenue pipeline scaling for Arena")
        assert score > 0.3

    def test_unrelated_work_scores_low(self, intent_runtime):
        from substrate.operator.intent_runtime import IntentScope
        intent_runtime.capture(
            "Scale revenue pipeline",
            IntentScope.PRODUCT,
        )
        score = intent_runtime.alignment_score("Fix CSS button color on login page")
        assert score < 0.3


class TestIntentRuntimeLifecycle:
    def test_achieve_with_evidence(self, intent_runtime):
        from substrate.operator.intent_runtime import IntentScope, CanonicalIntentStatus
        intent = intent_runtime.capture("Hit revenue target", IntentScope.PRODUCT)
        ok = intent_runtime.achieve(intent.intent_id, evidence=["Stripe confirms 10K"])
        assert ok
        updated = intent_runtime.get(intent.intent_id)
        assert updated.status == CanonicalIntentStatus.ACHIEVED
        assert "Stripe confirms 10K" in updated.evidence

    def test_abandon_with_reason(self, intent_runtime):
        from substrate.operator.intent_runtime import IntentScope, CanonicalIntentStatus
        intent = intent_runtime.capture("Pivot idea", IntentScope.SESSION)
        ok = intent_runtime.abandon(intent.intent_id, reason="Decided against")
        assert ok
        updated = intent_runtime.get(intent.intent_id)
        assert updated.status == CanonicalIntentStatus.ABANDONED


class TestIntentRuntimeContext:
    def test_context_for_session(self, intent_runtime):
        from substrate.operator.intent_runtime import IntentScope
        intent_runtime.capture("Empire vision", IntentScope.EMPIRE)
        intent_runtime.capture("Product goal", IntentScope.PRODUCT)
        ctx = intent_runtime.context_for_session()
        assert ctx["total_active"] == 2
        assert "empire" in ctx["scopes_with_intents"]

    def test_summary(self, intent_runtime):
        from substrate.operator.intent_runtime import IntentScope
        intent_runtime.capture("A", IntentScope.EMPIRE)
        intent_runtime.capture("B", IntentScope.PRODUCT)
        s = intent_runtime.summary()
        assert s["total"] == 2
        assert s["active"] == 2
        assert s["by_scope"]["empire"] == 1

    def test_serialization_roundtrip(self, intent_runtime):
        from substrate.operator.intent_runtime import IntentScope, CanonicalIntent
        intent = intent_runtime.capture("Roundtrip test", IntentScope.ARCHITECTURE)
        d = intent.to_dict()
        restored = CanonicalIntent.from_dict(d)
        assert restored.intent_id == intent.intent_id
        assert restored.scope == intent.scope
        assert restored.statement == intent.statement


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 2. OperatorSnapshotRuntime
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestOperatorSnapshotRuntime:
    def test_import(self):
        from substrate.operator.operator_snapshot_runtime import OperatorSnapshotRuntime
        rt = OperatorSnapshotRuntime()
        assert rt is not None

    def test_snapshot_returns_all_5_sections(self):
        from substrate.operator.operator_snapshot_runtime import OperatorSnapshotRuntime
        rt = OperatorSnapshotRuntime()
        snap = rt.snapshot()
        d = snap.to_dict()
        assert "situation" in d
        assert "attention" in d
        assert "changes" in d
        assert "decisions" in d
        assert "next_actions" in d
        assert "generated_at" in d

    def test_situation_returns_dataclass(self):
        from substrate.operator.operator_snapshot_runtime import OperatorSnapshotRuntime, SituationSnapshot
        rt = OperatorSnapshotRuntime()
        sit = rt.situation()
        assert isinstance(sit, SituationSnapshot)
        assert hasattr(sit, "device")
        assert hasattr(sit, "active_intents")

    def test_attention_returns_list(self):
        from substrate.operator.operator_snapshot_runtime import OperatorSnapshotRuntime
        rt = OperatorSnapshotRuntime()
        items = rt.attention()
        assert isinstance(items, list)

    def test_changes_returns_list(self):
        from substrate.operator.operator_snapshot_runtime import OperatorSnapshotRuntime
        rt = OperatorSnapshotRuntime()
        changes = rt.changes()
        assert isinstance(changes, list)

    def test_decisions_returns_list(self):
        from substrate.operator.operator_snapshot_runtime import OperatorSnapshotRuntime
        rt = OperatorSnapshotRuntime()
        decisions = rt.decisions()
        assert isinstance(decisions, list)

    def test_next_actions_returns_list(self):
        from substrate.operator.operator_snapshot_runtime import OperatorSnapshotRuntime
        rt = OperatorSnapshotRuntime()
        actions = rt.next_actions()
        assert isinstance(actions, list)

    def test_snapshot_with_intent_runtime(self, tmp_dir):
        from substrate.operator.intent_runtime import IntentRuntime, IntentScope
        from substrate.operator.operator_snapshot_runtime import OperatorSnapshotRuntime
        ir = IntentRuntime(
            intents_path=os.path.join(tmp_dir, "intents.jsonl"),
            conflicts_path=os.path.join(tmp_dir, "conflicts.jsonl"),
        )
        ir.capture("Test intent", IntentScope.PRODUCT)
        rt = OperatorSnapshotRuntime(intent_runtime=ir)
        sit = rt.situation()
        assert len(sit.active_intents) >= 1


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 3. OperatorAttentionEngine
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestOperatorAttentionEngine:
    def test_import(self):
        from substrate.operator.operator_attention_engine import OperatorAttentionEngine
        engine = OperatorAttentionEngine()
        assert engine is not None

    def test_compute_returns_list(self):
        from substrate.operator.operator_attention_engine import OperatorAttentionEngine
        engine = OperatorAttentionEngine()
        items = engine.compute()
        assert isinstance(items, list)

    def test_top_limits_results(self):
        from substrate.operator.operator_attention_engine import OperatorAttentionEngine
        engine = OperatorAttentionEngine()
        items = engine.top(3)
        assert len(items) <= 3

    def test_by_category(self):
        from substrate.operator.operator_attention_engine import OperatorAttentionEngine
        engine = OperatorAttentionEngine()
        items = engine.by_category("nonexistent_category")
        assert items == []

    def test_attention_item_has_capability_link(self):
        from substrate.operator.operator_attention_engine import OperatorAttentionEngine
        engine = OperatorAttentionEngine()
        items = engine.compute()
        for item in items:
            assert hasattr(item, "capability_link")

    def test_items_sorted_by_severity(self):
        from substrate.operator.operator_attention_engine import OperatorAttentionEngine
        engine = OperatorAttentionEngine()
        items = engine.compute()
        if len(items) > 1:
            sev_order = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}
            for i in range(len(items) - 1):
                assert sev_order.get(items[i].severity, 4) <= sev_order.get(items[i + 1].severity, 4)

    def test_with_intent_conflicts(self, tmp_dir):
        """Active work that does not align with stated intent raises a misalignment.

        Both collaborators are supplied explicitly. ``_misalignments()`` scores
        each ACTIVE work item's description against the captured intents, so the
        test must arrange BOTH sides itself: the intents (via an isolated
        IntentRuntime) and the active work (via the injected work runtime). It
        must never depend on whatever happens to be in the live production work
        store — that ambient dependency is exactly what made this assertion
        unreliable.
        """
        from substrate.operator.intent_runtime import IntentRuntime, IntentScope
        from substrate.operator.operator_attention_engine import OperatorAttentionEngine

        ir = IntentRuntime(
            intents_path=os.path.join(tmp_dir, "intents.jsonl"),
            conflicts_path=os.path.join(tmp_dir, "conflicts.jsonl"),
        )
        ir.capture("Do the thing one way", IntentScope.PRODUCT)
        ir.capture("Do the thing one way differently", IntentScope.PRODUCT)

        class _IsolatedWorkRuntime:
            """Deterministic stand-in for the governed work runtime.

            Returns exactly one ACTIVE work item whose vocabulary is disjoint
            from every captured intent, so alignment_score() is driven to 0.0
            (well under the 0.3 misalignment threshold) by construction.
            """

            def active(self):
                return [
                    {
                        "work_id": "wp-isolated-misaligned",
                        "description": "Refactor unrelated telemetry serialization buffers",
                    }
                ]

        engine = OperatorAttentionEngine(
            intent_runtime=ir,
            work_runtime=_IsolatedWorkRuntime(),
        )
        items = engine.compute()
        misalignment = [i for i in items if i.category == "misalignment"]
        assert len(misalignment) >= 1
        assert any(i.source_id == "wp-isolated-misaligned" for i in misalignment)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 4. Route compilation
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestRouteCompilation:
    def test_command_center_routes_import(self):
        from transports.api.cockpit_command_center_routes import command_center_router
        assert command_center_router is not None

    def test_intent_routes_import(self):
        from transports.api.cockpit_intent_routes import intent_router
        assert intent_router is not None

    def test_organism_map_routes_import(self):
        from transports.api.cockpit_organism_map_routes import organism_map_router
        assert organism_map_router is not None

    def test_work_center_routes_import(self):
        from transports.api.cockpit_work_center_routes import work_center_router
        assert work_center_router is not None

    def test_execution_routes_import(self):
        from transports.api.cockpit_execution_routes import execution_router
        assert execution_router is not None

    def test_activity_routes_import(self):
        from transports.api.cockpit_activity_routes import activity_router
        assert activity_router is not None

    def test_meta_ide_routes_import(self):
        from transports.api.cockpit_meta_ide_routes import meta_ide_router
        assert meta_ide_router is not None

    def test_cockpit_main_import(self):
        from transports.api.cockpit import router
        assert len(router.routes) > 0


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 5. Type coherence
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestTypeCoherence:
    GATE4_TYPES = [
        ("IntentScope", "substrate.operator.intent_runtime"),
        ("CanonicalIntentStatus", "substrate.operator.intent_runtime"),
        ("CanonicalIntent", "substrate.operator.intent_runtime"),
        ("IntentConflict", "substrate.operator.intent_runtime"),
        ("IntentRuntime", "substrate.operator.intent_runtime"),
        ("ConflictType", "substrate.operator.intent_runtime"),
        ("SituationSnapshot", "substrate.operator.operator_snapshot_runtime"),
        ("OperatorQuestionSnapshot", "substrate.operator.operator_snapshot_runtime"),
        ("OperatorSnapshotRuntime", "substrate.operator.operator_snapshot_runtime"),
        ("AttentionItem", "substrate.operator.operator_attention_engine"),
        ("OperatorAttentionEngine", "substrate.operator.operator_attention_engine"),
    ]

    @pytest.mark.parametrize("type_name,module", GATE4_TYPES)
    def test_type_registered(self, type_name, module):
        from substrate.canonical_types import lookup
        locations = lookup(type_name)
        assert locations is not None, f"{type_name} not registered in canonical_types"
        assert module in locations, f"{type_name} not registered under {module}"

    @pytest.mark.parametrize("type_name,module", GATE4_TYPES)
    def test_no_divergence(self, type_name, module):
        from substrate.canonical_types import check_name
        err = check_name(type_name, module)
        assert err is None, f"Divergence: {err}"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 6. Operator effectiveness — Jarvis loop
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestOperatorEffectivenessLoop:
    """The full Jarvis loop must be completable from workstation capabilities."""

    def test_observe_via_command_center(self):
        from substrate.operator.operator_snapshot_runtime import OperatorSnapshotRuntime
        rt = OperatorSnapshotRuntime()
        sit = rt.situation()
        attention = rt.attention()
        assert sit is not None
        assert isinstance(attention, list)

    def test_understand_via_changes(self):
        from substrate.operator.operator_snapshot_runtime import OperatorSnapshotRuntime
        rt = OperatorSnapshotRuntime()
        changes = rt.changes()
        assert isinstance(changes, list)

    def test_decide_via_work_submit(self):
        from substrate.organism.governed_work_runtime import GovernedWorkRuntime
        rt = GovernedWorkRuntime()
        submission = rt.submit_work(intent="Test decision", risk_class="low")
        assert submission.work_id != ""

    def test_approve_via_work_runtime(self):
        from substrate.organism.governed_work_runtime import GovernedWorkRuntime
        rt = GovernedWorkRuntime()
        submission = rt.submit_work(intent="Approval test", risk_class="low")
        if submission.requires_approval:
            result = rt.approve_work(submission.work_id)
            assert isinstance(result, dict)

    def test_execute_via_work_runtime(self):
        from substrate.organism.governed_work_runtime import GovernedWorkRuntime
        rt = GovernedWorkRuntime()
        submission = rt.submit_work(intent="Execution test", risk_class="low")
        receipt = rt.execute_work(submission.work_id)
        assert receipt is not None

    def test_verify_via_proof(self):
        from substrate.organism.governed_work_runtime import GovernedWorkRuntime
        rt = GovernedWorkRuntime()
        submission = rt.submit_work(intent="Proof test")
        proof = rt.proof(submission.work_id)
        assert proof is None or isinstance(proof, dict)

    def test_recover_via_recovery(self):
        from substrate.organism.governed_work_runtime import GovernedWorkRuntime
        rt = GovernedWorkRuntime()
        recovery = rt.recovery()
        assert isinstance(recovery, list)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 7. Intent continuity (acceptance test)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestIntentContinuity:
    """Can intent survive a session restart?"""

    def test_intent_persists_across_instances(self, tmp_dir):
        from substrate.operator.intent_runtime import IntentRuntime, IntentScope
        intents_path = os.path.join(tmp_dir, "intents.jsonl")
        conflicts_path = os.path.join(tmp_dir, "conflicts.jsonl")

        rt1 = IntentRuntime(intents_path=intents_path, conflicts_path=conflicts_path)
        intent = rt1.capture(
            "Build UMH as isomorphic reality approximation",
            IntentScope.ARCHITECTURE,
            rationale="Core vision",
        )
        del rt1

        rt2 = IntentRuntime(intents_path=intents_path, conflicts_path=conflicts_path)
        retrieved = rt2.retrieve(scope=IntentScope.ARCHITECTURE)
        assert len(retrieved) == 1
        assert retrieved[0].intent_id == intent.intent_id
        assert retrieved[0].statement == "Build UMH as isomorphic reality approximation"

    def test_context_survives_restart(self, tmp_dir):
        from substrate.operator.intent_runtime import IntentRuntime, IntentScope
        intents_path = os.path.join(tmp_dir, "intents.jsonl")
        conflicts_path = os.path.join(tmp_dir, "conflicts.jsonl")

        rt1 = IntentRuntime(intents_path=intents_path, conflicts_path=conflicts_path)
        rt1.capture("Empire goal", IntentScope.EMPIRE)
        rt1.capture("Product goal", IntentScope.PRODUCT)
        del rt1

        rt2 = IntentRuntime(intents_path=intents_path, conflicts_path=conflicts_path)
        ctx = rt2.context_for_session()
        assert ctx["total_active"] == 2

    def test_conflicts_survive_restart(self, tmp_dir):
        from substrate.operator.intent_runtime import IntentRuntime, IntentScope
        intents_path = os.path.join(tmp_dir, "intents.jsonl")
        conflicts_path = os.path.join(tmp_dir, "conflicts.jsonl")

        rt1 = IntentRuntime(intents_path=intents_path, conflicts_path=conflicts_path)
        rt1.capture("Do thing one way definitely", IntentScope.PRODUCT)
        rt1.capture("Do thing one way definitely also", IntentScope.PRODUCT)
        c1 = rt1.conflicts()
        del rt1

        rt2 = IntentRuntime(intents_path=intents_path, conflicts_path=conflicts_path)
        c2 = rt2.conflicts()
        assert len(c2) == len(c1)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 8. Engineering gates (route file constraints)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestEngineeringGates:
    @staticmethod
    def _repo_root() -> str:
        here = os.path.dirname(os.path.abspath(__file__))
        return os.path.dirname(here)

    def test_no_route_file_exceeds_3500_lines(self):
        import glob
        route_files = glob.glob(
            os.path.join(self._repo_root(), "transports/api/cockpit_*routes*.py")
        )
        for path in route_files:
            with open(path) as f:
                lines = sum(1 for _ in f)
            assert lines <= 3500, f"{os.path.basename(path)} has {lines} lines (max 3500)"

    def test_canonical_route_modules_exist(self):
        root = self._repo_root()
        required = [
            "cockpit_command_center_routes.py",
            "cockpit_work_center_routes.py",
            "cockpit_organism_map_routes.py",
            "cockpit_intent_routes.py",
        ]
        for name in required:
            path = os.path.join(root, "transports/api", name)
            assert os.path.exists(path), f"Missing canonical route module: {name}"

    def test_all_route_files_compile(self):
        import glob
        import py_compile
        route_files = glob.glob(
            os.path.join(self._repo_root(), "transports/api/cockpit_*routes*.py")
        )
        for path in route_files:
            try:
                py_compile.compile(path, doraise=True)
            except py_compile.PyCompileError as e:
                pytest.fail(f"{os.path.basename(path)} fails to compile: {e}")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 9. Instrument gates — Human Supremacy invariant
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestInstrumentGates:
    def test_command_center_provides_all_questions(self):
        from substrate.operator.operator_snapshot_runtime import OperatorSnapshotRuntime
        rt = OperatorSnapshotRuntime()
        snap = rt.snapshot()
        d = snap.to_dict()
        for key in ("situation", "attention", "changes", "decisions", "next_actions"):
            assert key in d, f"Command Center missing '{key}' operator question"

    def test_organism_map_provides_topology_and_health(self):
        from transports.api.cockpit_organism_map_routes import organism_map_router
        paths = [r.path for r in organism_map_router.routes]
        assert any("topology" in p for p in paths) or len(paths) == 0

    def test_snapshot_runtime_aggregates_intent(self):
        from substrate.operator.operator_snapshot_runtime import OperatorSnapshotRuntime
        rt = OperatorSnapshotRuntime()
        assert hasattr(rt, "_intent_runtime") or hasattr(rt, "intent_runtime")

    def test_attention_engine_produces_ranked_items(self):
        from substrate.operator.operator_attention_engine import OperatorAttentionEngine
        engine = OperatorAttentionEngine()
        items = engine.compute()
        for item in items:
            assert hasattr(item, "priority")
            assert hasattr(item, "capability_link")

    def test_intent_runtime_full_lifecycle(self, tmp_dir):
        from substrate.operator.intent_runtime import IntentRuntime, IntentScope, CanonicalIntentStatus
        ir = IntentRuntime(
            intents_path=os.path.join(tmp_dir, "i.jsonl"),
            conflicts_path=os.path.join(tmp_dir, "c.jsonl"),
        )
        i = ir.capture("Test", IntentScope.SESSION)
        assert ir.get(i.intent_id) is not None
        ir.refine(i.intent_id, new_statement="Updated")
        assert ir.get(i.intent_id).statement == "Updated"
        ir.achieve(i.intent_id)
        assert ir.get(i.intent_id).status == CanonicalIntentStatus.ACHIEVED
