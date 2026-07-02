"""P3 Phase 5 — Design Workflow tests.

Verifies:
1. DesignWorkflow produces governed steps for asset review and template application
2. Brand compliance checks run deterministically
3. Template validation catches missing fields
4. Full lifecycle through WorkflowRunner

Run with: pytest tests/test_p3_phase5_design.py -v
"""

import os
import sys
import tempfile

import pytest

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _REPO_ROOT)

pytestmark = pytest.mark.smoke


class TestDesignWorkflowStructure:

    def test_importable(self):
        from projections.eos.workflows.design import DesignWorkflow
        assert DesignWorkflow is not None

    def test_asset_review_returns_3_steps(self):
        from projections.eos.workflows.design import DesignWorkflow
        wf = DesignWorkflow()
        steps = wf.asset_review_steps("my_project")
        assert len(steps) == 3
        names = [s.name for s in steps]
        assert names == ["identify_assets", "check_brand_compliance", "generate_report"]

    def test_template_apply_returns_3_steps(self):
        from projections.eos.workflows.design import DesignWorkflow
        wf = DesignWorkflow()
        steps = wf.template_apply_steps("social_post", {"headline": "Test", "cta": "Buy"})
        assert len(steps) == 3
        names = [s.name for s in steps]
        assert names == ["validate_template", "apply_context", "store_output"]

    def test_all_steps_have_mutation_names(self):
        from projections.eos.workflows.design import DesignWorkflow
        wf = DesignWorkflow()
        all_steps = (
            wf.asset_review_steps("test")
            + wf.template_apply_steps("social_post", {"headline": "X", "cta": "Y"})
        )
        for step in all_steps:
            assert step.mutation_name, f"{step.name} missing mutation_name"
            assert step.intent, f"{step.name} missing intent"

    def test_templates_defined(self):
        from projections.eos.workflows.design import TEMPLATES
        assert len(TEMPLATES) >= 5
        assert "social_post" in TEMPLATES
        assert "presentation" in TEMPLATES

    def test_brand_rules_defined(self):
        from projections.eos.workflows.design import BRAND_RULES
        assert "colors" in BRAND_RULES
        assert "fonts" in BRAND_RULES
        assert len(BRAND_RULES["colors"]) >= 3


class TestDesignAssetReview:

    def test_identify_assets_no_dir(self):
        from projections.eos.workflows.design import DesignWorkflow
        wf = DesignWorkflow()
        output, success = wf._identify_assets("nonexistent_project")
        assert success
        assert "1 design asset" in output
        assert len(wf._assets) == 1

    def test_identify_assets_with_files(self):
        from projections.eos.workflows import design as mod
        from projections.eos.workflows.design import DesignWorkflow

        with tempfile.TemporaryDirectory() as tmpdir:
            orig = mod._DESIGN_DIR
            mod._DESIGN_DIR = tmpdir
            try:
                project_dir = os.path.join(tmpdir, "projects", "test_proj")
                os.makedirs(project_dir)
                for fname in ["logo.svg", "hero.png", "notes.txt"]:
                    with open(os.path.join(project_dir, fname), "w") as f:
                        f.write("test")

                wf = DesignWorkflow()
                output, success = wf._identify_assets("test_proj")
                assert success
                assert "2 design asset" in output
                types = {a["type"] for a in wf._assets}
                assert "svg" in types
                assert "png" in types
            finally:
                mod._DESIGN_DIR = orig

    def test_brand_compliance_placeholder(self):
        from projections.eos.workflows.design import DesignWorkflow
        wf = DesignWorkflow()
        wf._identify_assets("nonexistent")
        output, success = wf._check_brand_compliance()
        assert success
        assert "0/1" in output

    def test_generate_report(self):
        from projections.eos.workflows import design as mod
        from projections.eos.workflows.design import DesignWorkflow

        with tempfile.TemporaryDirectory() as tmpdir:
            orig = mod._DESIGN_DIR
            mod._DESIGN_DIR = tmpdir
            try:
                wf = DesignWorkflow()
                wf._identify_assets("test_report")
                wf._check_brand_compliance()
                output, success = wf._generate_report("test_report")
                assert success
                assert "Design Review" in output
                reports = os.listdir(os.path.join(tmpdir, "reports"))
                assert len(reports) == 1
            finally:
                mod._DESIGN_DIR = orig


class TestDesignTemplateApply:

    def test_validate_unknown_template(self):
        from projections.eos.workflows.design import DesignWorkflow
        wf = DesignWorkflow()
        output, success = wf._validate_template("nonexistent", {})
        assert not success
        assert "Unknown template" in output

    def test_validate_missing_required(self):
        from projections.eos.workflows.design import DesignWorkflow
        wf = DesignWorkflow()
        output, success = wf._validate_template("social_post", {})
        assert not success
        assert "headline" in output

    def test_validate_success(self):
        from projections.eos.workflows.design import DesignWorkflow
        wf = DesignWorkflow()
        output, success = wf._validate_template(
            "social_post", {"headline": "Test", "cta": "Buy Now"}
        )
        assert success
        assert "1080x1080" in output

    def test_apply_context(self):
        from projections.eos.workflows.design import DesignWorkflow
        wf = DesignWorkflow()
        output, success = wf._apply_context(
            "social_post", {"headline": "Launch Day", "cta": "Sign Up"}
        )
        assert success
        assert "2 fields" in output
        assert "Launch Day" in wf._template_output

    def test_store_output(self):
        from projections.eos.workflows import design as mod
        from projections.eos.workflows.design import DesignWorkflow

        with tempfile.TemporaryDirectory() as tmpdir:
            orig = mod._DESIGN_DIR
            mod._DESIGN_DIR = tmpdir
            try:
                wf = DesignWorkflow()
                wf._apply_context("thumbnail", {"headline": "Test"})
                output, success = wf._store_output("thumbnail")
                assert success
                outputs = os.listdir(os.path.join(tmpdir, "outputs"))
                assert len(outputs) == 1
            finally:
                mod._DESIGN_DIR = orig


class TestDesignThroughRunner:

    def test_asset_review_through_runner(self):
        from projections.eos.workflows import design as mod
        from projections.eos.workflows.design import DesignWorkflow
        from projections.eos.workflows.runner import WorkflowRunner

        with tempfile.TemporaryDirectory() as tmpdir:
            orig = mod._DESIGN_DIR
            mod._DESIGN_DIR = tmpdir
            try:
                wf = DesignWorkflow()
                runner = WorkflowRunner()
                result = runner.run(
                    "design_review",
                    wf.asset_review_steps("test_project"),
                    source="test",
                )
                assert result.success
                assert result.steps_completed == 3
            finally:
                mod._DESIGN_DIR = orig

    def test_template_apply_through_runner(self):
        from projections.eos.workflows import design as mod
        from projections.eos.workflows.design import DesignWorkflow
        from projections.eos.workflows.runner import WorkflowRunner

        with tempfile.TemporaryDirectory() as tmpdir:
            orig = mod._DESIGN_DIR
            mod._DESIGN_DIR = tmpdir
            try:
                wf = DesignWorkflow()
                runner = WorkflowRunner()
                result = runner.run(
                    "design_template",
                    wf.template_apply_steps("social_post", {"headline": "Go", "cta": "Now"}),
                    source="test",
                )
                assert result.success
                assert result.steps_completed == 3
            finally:
                mod._DESIGN_DIR = orig

    def test_template_validation_failure_halts(self):
        from projections.eos.workflows.design import DesignWorkflow
        from projections.eos.workflows.runner import WorkflowRunner

        wf = DesignWorkflow()
        runner = WorkflowRunner()
        result = runner.run(
            "design_template",
            wf.template_apply_steps("social_post", {}),
            source="test",
        )
        assert not result.success
        assert result.steps_completed < 3
