"""Gate 6 — Operationalization Runtime tests.

Tests operationalization lifecycle: creation, template linkage, invariant
extraction, reuse scoring, and API routes.
"""

from __future__ import annotations

import json
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Types
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestTypes:
    def test_operationalization_form_enum(self):
        from substrate.organism.operationalization_runtime import (
            OperationalizationForm,
        )

        assert OperationalizationForm.TEMPLATE.value == "template"
        assert OperationalizationForm.WORKFLOW.value == "workflow"
        assert OperationalizationForm.PLAYBOOK.value == "playbook"
        assert OperationalizationForm.AUTOMATION.value == "automation"

    def test_operationalization_status_enum(self):
        from substrate.organism.operationalization_runtime import (
            OperationalizationStatus,
        )

        assert OperationalizationStatus.DRAFT.value == "draft"
        assert OperationalizationStatus.VALIDATED.value == "validated"
        assert OperationalizationStatus.PRODUCTION.value == "production"
        assert OperationalizationStatus.DEPRECATED.value == "deprecated"

    def test_operationalization_creation(self):
        from substrate.organism.operationalization_runtime import (
            Operationalization,
            OperationalizationForm,
            OperationalizationStatus,
        )

        op = Operationalization(
            name="Deploy Workflow",
            capability_id="ecap-abc123",
            form=OperationalizationForm.WORKFLOW,
        )
        assert op.name == "Deploy Workflow"
        assert op.form == OperationalizationForm.WORKFLOW
        assert op.status == OperationalizationStatus.DRAFT
        assert op.operationalization_id.startswith("op-")

    def test_operationalization_to_dict(self):
        from substrate.organism.operationalization_runtime import (
            Operationalization,
            OperationalizationForm,
        )

        op = Operationalization(name="Test", form=OperationalizationForm.PLAYBOOK)
        d = op.to_dict()
        assert d["form"] == "playbook"
        assert d["status"] == "draft"
        assert isinstance(d["invariants"], list)

    def test_operationalization_from_dict(self):
        from substrate.organism.operationalization_runtime import (
            Operationalization,
            OperationalizationForm,
            OperationalizationStatus,
        )

        d = {
            "operationalization_id": "op-test",
            "name": "Test",
            "form": "automation",
            "status": "production",
        }
        op = Operationalization.from_dict(d)
        assert op.form == OperationalizationForm.AUTOMATION
        assert op.status == OperationalizationStatus.PRODUCTION

    def test_invalid_form_defaults_to_template(self):
        from substrate.organism.operationalization_runtime import (
            Operationalization,
            OperationalizationForm,
        )

        op = Operationalization.from_dict({"form": "nonexistent"})
        assert op.form == OperationalizationForm.TEMPLATE

    def test_invalid_status_defaults_to_draft(self):
        from substrate.organism.operationalization_runtime import (
            Operationalization,
            OperationalizationStatus,
        )

        op = Operationalization.from_dict({"status": "nonexistent"})
        assert op.status == OperationalizationStatus.DRAFT


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Invariant extraction
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestInvariantExtraction:
    def test_empty_steps(self):
        from substrate.organism.operationalization_runtime import (
            extract_invariants_from_steps,
        )

        result = extract_invariants_from_steps([])
        assert result["invariants"] == []
        assert result["step_count"] == 0

    def test_uniform_risk_class_is_invariant(self):
        from substrate.organism.operationalization_runtime import (
            extract_invariants_from_steps,
        )

        steps = [
            {"action": "edit", "risk_class": "low"},
            {"action": "test", "risk_class": "low"},
        ]
        result = extract_invariants_from_steps(steps)
        assert "risk_class=low" in result["invariants"]

    def test_varying_risk_class_is_variable(self):
        from substrate.organism.operationalization_runtime import (
            extract_invariants_from_steps,
        )

        steps = [
            {"action": "edit", "risk_class": "low"},
            {"action": "deploy", "risk_class": "high"},
        ]
        result = extract_invariants_from_steps(steps)
        assert "risk_class" in result["variables"]

    def test_uniform_governance_mode_is_invariant(self):
        from substrate.organism.operationalization_runtime import (
            extract_invariants_from_steps,
        )

        steps = [
            {"action": "a", "governance_mode": "autonomous"},
            {"action": "b", "governance_mode": "autonomous"},
        ]
        result = extract_invariants_from_steps(steps)
        assert "governance_mode=autonomous" in result["invariants"]

    def test_capability_required_in_all_steps_is_invariant(self):
        from substrate.organism.operationalization_runtime import (
            extract_invariants_from_steps,
        )

        steps = [
            {"action": "a", "requires_capability": "file_edit", "risk_class": "low"},
            {"action": "b", "requires_capability": "file_edit", "risk_class": "low"},
        ]
        result = extract_invariants_from_steps(steps)
        assert "requires_capability=file_edit" in result["invariants"]


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Reuse scoring
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestReuseScoring:
    def test_zero_reuse_score(self):
        from substrate.organism.operationalization_runtime import (
            Operationalization,
            compute_reuse_score,
        )

        op = Operationalization(name="Test", reuse_count=0, success_rate=0.0)
        score = compute_reuse_score(op)
        assert score["frequency_score"] == 0.0
        assert score["composite_score"] == pytest.approx(0.05, abs=0.01)

    def test_high_reuse_high_success(self):
        from substrate.organism.operationalization_runtime import (
            Operationalization,
            OperationalizationForm,
            compute_reuse_score,
        )

        op = Operationalization(
            name="Test",
            form=OperationalizationForm.AUTOMATION,
            reuse_count=15,
            success_rate=0.95,
        )
        score = compute_reuse_score(op)
        assert score["frequency_score"] == 1.0
        assert score["composite_score"] > 0.8

    def test_automation_scores_higher_than_template(self):
        from substrate.organism.operationalization_runtime import (
            Operationalization,
            OperationalizationForm,
            compute_reuse_score,
        )

        auto = Operationalization(
            form=OperationalizationForm.AUTOMATION,
            reuse_count=5,
            success_rate=0.8,
        )
        tpl = Operationalization(
            form=OperationalizationForm.TEMPLATE,
            reuse_count=5,
            success_rate=0.8,
        )
        assert (
            compute_reuse_score(auto)["composite_score"]
            > compute_reuse_score(tpl)["composite_score"]
        )


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# OperationalizationRuntime
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


@pytest.fixture
def runtime(tmp_path):
    from substrate.organism.operationalization_runtime import (
        OperationalizationRuntime,
    )

    return OperationalizationRuntime(store_path=str(tmp_path / "ops.jsonl"))


class TestOperationalizationRuntime:
    def test_create_and_get(self, runtime):
        from substrate.organism.operationalization_runtime import (
            OperationalizationForm,
        )

        op = runtime.create(
            capability_id="ecap-abc",
            form=OperationalizationForm.WORKFLOW,
            name="Test Workflow",
        )
        assert op.name == "Test Workflow"
        retrieved = runtime.get(op.operationalization_id)
        assert retrieved is not None
        assert retrieved.name == "Test Workflow"

    def test_list_all(self, runtime):
        from substrate.organism.operationalization_runtime import (
            OperationalizationForm,
        )

        runtime.create("ecap-a", OperationalizationForm.TEMPLATE, "Op1")
        runtime.create("ecap-b", OperationalizationForm.WORKFLOW, "Op2")
        ops = runtime.list_operationalizations()
        assert len(ops) == 2

    def test_list_by_capability(self, runtime):
        from substrate.organism.operationalization_runtime import (
            OperationalizationForm,
        )

        runtime.create("ecap-a", OperationalizationForm.TEMPLATE, "Op1")
        runtime.create("ecap-b", OperationalizationForm.TEMPLATE, "Op2")
        ops = runtime.list_operationalizations(capability_id="ecap-a")
        assert len(ops) == 1

    def test_list_by_form(self, runtime):
        from substrate.organism.operationalization_runtime import (
            OperationalizationForm,
        )

        runtime.create("ecap-a", OperationalizationForm.TEMPLATE, "Op1")
        runtime.create("ecap-a", OperationalizationForm.WORKFLOW, "Op2")
        ops = runtime.list_operationalizations(form=OperationalizationForm.WORKFLOW)
        assert len(ops) == 1

    def test_get_nonexistent(self, runtime):
        assert runtime.get("nonexistent") is None

    def test_from_template(self, runtime):
        from substrate.organism.operationalization_runtime import (
            OperationalizationForm,
        )

        op = runtime.create(
            "ecap-a",
            OperationalizationForm.TEMPLATE,
            "Linked Op",
            template_id="tpl-123",
        )
        found = runtime.from_template("tpl-123")
        assert found is not None
        assert found.operationalization_id == op.operationalization_id

    def test_from_template_not_found(self, runtime):
        assert runtime.from_template("nonexistent") is None

    def test_link_template(self, runtime):
        from substrate.organism.operationalization_runtime import (
            OperationalizationForm,
        )

        op = runtime.create("ecap-a", OperationalizationForm.TEMPLATE, "Op1")
        assert runtime.link_template(op.operationalization_id, "tpl-456")
        updated = runtime.get(op.operationalization_id)
        assert updated.template_id == "tpl-456"

    def test_link_template_nonexistent(self, runtime):
        assert not runtime.link_template("nonexistent", "tpl-456")

    def test_reuse_score(self, runtime):
        from substrate.organism.operationalization_runtime import (
            OperationalizationForm,
        )

        op = runtime.create("ecap-a", OperationalizationForm.TEMPLATE, "Op1")
        score = runtime.reuse_score(op.operationalization_id)
        assert "composite_score" in score

    def test_reuse_score_nonexistent(self, runtime):
        score = runtime.reuse_score("nonexistent")
        assert "error" in score

    def test_most_reused(self, runtime):
        from substrate.organism.operationalization_runtime import (
            OperationalizationForm,
        )

        op1 = runtime.create("ecap-a", OperationalizationForm.TEMPLATE, "Op1")
        op2 = runtime.create("ecap-a", OperationalizationForm.TEMPLATE, "Op2")
        runtime.record_use(op1.operationalization_id, success=True)
        runtime.record_use(op1.operationalization_id, success=True)
        runtime.record_use(op2.operationalization_id, success=True)
        top = runtime.most_reused(n=2)
        assert len(top) == 2
        assert top[0].operationalization_id == op1.operationalization_id

    def test_update_status(self, runtime):
        from substrate.organism.operationalization_runtime import (
            OperationalizationForm,
            OperationalizationStatus,
        )

        op = runtime.create("ecap-a", OperationalizationForm.TEMPLATE, "Op1")
        assert runtime.update_status(op.operationalization_id, OperationalizationStatus.PRODUCTION)
        updated = runtime.get(op.operationalization_id)
        assert updated.status == OperationalizationStatus.PRODUCTION

    def test_record_use(self, runtime):
        from substrate.organism.operationalization_runtime import (
            OperationalizationForm,
        )

        op = runtime.create("ecap-a", OperationalizationForm.TEMPLATE, "Op1")
        runtime.record_use(op.operationalization_id, success=True)
        runtime.record_use(op.operationalization_id, success=True)
        runtime.record_use(op.operationalization_id, success=False)
        updated = runtime.get(op.operationalization_id)
        assert updated.reuse_count == 3
        assert abs(updated.success_rate - 0.6667) < 0.01

    def test_record_use_nonexistent(self, runtime):
        assert not runtime.record_use("nonexistent")

    def test_lineage(self, runtime):
        from substrate.organism.operationalization_runtime import (
            OperationalizationForm,
        )

        op = runtime.create(
            "ecap-abc",
            OperationalizationForm.WORKFLOW,
            "Test",
            invariants=["risk_class=low"],
            variables=["action=edit"],
        )
        lineage = runtime.lineage(op.operationalization_id)
        assert lineage["capability_id"] == "ecap-abc"
        assert lineage["invariants"] == ["risk_class=low"]
        assert lineage["variables"] == ["action=edit"]

    def test_lineage_nonexistent(self, runtime):
        lineage = runtime.lineage("nonexistent")
        assert "error" in lineage

    def test_summary(self, runtime):
        from substrate.organism.operationalization_runtime import (
            OperationalizationForm,
        )

        runtime.create("ecap-a", OperationalizationForm.TEMPLATE, "Op1")
        runtime.create("ecap-a", OperationalizationForm.WORKFLOW, "Op2")
        summary = runtime.summary()
        assert summary["total_operationalizations"] == 2
        assert summary["by_form"]["template"] == 1
        assert summary["by_form"]["workflow"] == 1


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Persistence
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestPersistence:
    def test_jsonl_roundtrip(self, tmp_path):
        from substrate.organism.operationalization_runtime import (
            OperationalizationForm,
            OperationalizationRuntime,
        )

        path = str(tmp_path / "ops.jsonl")
        rt1 = OperationalizationRuntime(store_path=path)
        op = rt1.create("ecap-a", OperationalizationForm.WORKFLOW, "Persistent Op")
        rt2 = OperationalizationRuntime(store_path=path)
        loaded = rt2.get(op.operationalization_id)
        assert loaded is not None
        assert loaded.name == "Persistent Op"

    def test_malformed_jsonl_skipped(self, tmp_path):
        from substrate.organism.operationalization_runtime import (
            OperationalizationRuntime,
        )

        path = str(tmp_path / "ops.jsonl")
        with open(path, "w") as f:
            f.write("bad json\n")
            f.write('{"operationalization_id": "op-valid", "name": "Valid"}\n')
        rt = OperationalizationRuntime(store_path=path)
        ops = rt.list_operationalizations()
        assert len(ops) == 1


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Type coherence
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestTypeCoherence:
    def test_canonical_types_registered(self):
        from substrate.canonical_types import lookup

        assert lookup("OperationalizationForm") is not None
        assert lookup("OperationalizationStatus") is not None
        assert lookup("Operationalization") is not None
        assert lookup("OperationalizationRuntime") is not None


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Routes
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestRoutes:
    def test_operationalization_routes_importable(self):
        from transports.api.cockpit_operationalization_routes import (
            operationalization_router,
        )

        assert operationalization_router is not None

    def test_cockpit_mounts_operationalization_routes(self):
        import transports.api.cockpit as c

        route_paths = [r.path for r in c.router.routes if hasattr(r, "path")]
        assert any("/operationalizations" in p for p in route_paths)
