"""P2 Phase 2 — Research Workflow tests.

Verifies:
1. ResearchWorkflow produces governed steps
2. Keyword extraction is deterministic
3. Steps execute through WorkflowRunner
4. Findings are stored to filesystem

Run with: pytest tests/test_p2_phase2_research.py -v
"""

import os
import sys
import tempfile

import pytest

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _REPO_ROOT)

pytestmark = pytest.mark.smoke


class TestResearchWorkflowStructure:

    def test_importable(self):
        from projections.eos.workflows.research import ResearchWorkflow
        assert ResearchWorkflow is not None

    def test_steps_returns_4_steps(self):
        from projections.eos.workflows.research import ResearchWorkflow
        wf = ResearchWorkflow()
        steps = wf.steps("UMH architecture patterns")
        assert len(steps) == 4
        names = [s.name for s in steps]
        assert names == ["define_question", "gather_sources", "synthesize", "store_findings"]

    def test_all_steps_have_mutation_names(self):
        from projections.eos.workflows.research import ResearchWorkflow
        wf = ResearchWorkflow()
        for step in wf.steps("test topic"):
            assert step.mutation_name, f"Step {step.name} has no mutation_name"
            assert step.intent, f"Step {step.name} has no intent"

    def test_keyword_extraction(self):
        from projections.eos.workflows.research import ResearchWorkflow
        wf = ResearchWorkflow()
        keywords = wf._extract_keywords("How does the governed mutation system work?")
        assert "governed" in keywords
        assert "mutation" in keywords
        assert "system" in keywords
        assert "the" not in keywords
        assert "does" not in keywords
        assert "how" not in keywords

    def test_keyword_extraction_limits(self):
        from projections.eos.workflows.research import ResearchWorkflow
        wf = ResearchWorkflow()
        keywords = wf._extract_keywords(
            "alpha bravo charlie delta echo foxtrot golf hotel india juliet kilo lima"
        )
        assert len(keywords) <= 8


class TestResearchWorkflowExecution:

    def test_define_question_step(self):
        from projections.eos.workflows.research import ResearchWorkflow
        wf = ResearchWorkflow()
        output, success = wf._define_question("governed mutation architecture")
        assert success
        assert "Research defined" in output
        assert wf._query is not None
        assert wf._query.topic == "governed mutation architecture"

    def test_gather_sources_returns_findings(self):
        from projections.eos.workflows.research import ResearchWorkflow
        wf = ResearchWorkflow()
        wf._define_question("UMH platform specification")
        output, success = wf._gather_sources()
        assert success
        assert "findings" in output.lower()

    def test_synthesize_produces_output(self):
        from projections.eos.workflows.research import ResearchWorkflow
        wf = ResearchWorkflow()
        wf._define_question("UMH platform")
        wf._gather_sources()
        output, success = wf._synthesize()
        assert success
        assert wf._synthesis

    def test_store_findings_creates_file(self):
        from projections.eos.workflows import research as research_mod
        from projections.eos.workflows.research import ResearchWorkflow

        with tempfile.TemporaryDirectory() as tmpdir:
            original = research_mod._FINDINGS_DIR
            research_mod._FINDINGS_DIR = tmpdir
            try:
                wf = ResearchWorkflow()
                wf._define_question("test storage")
                wf._gather_sources()
                wf._synthesize()
                output, success = wf._store_findings()
                assert success
                files = os.listdir(tmpdir)
                assert len(files) == 1
                assert files[0].endswith(".md")
            finally:
                research_mod._FINDINGS_DIR = original

    def test_full_workflow_through_runner(self):
        from projections.eos.workflows import research as research_mod
        from projections.eos.workflows.research import ResearchWorkflow
        from projections.eos.workflows.runner import WorkflowRunner

        with tempfile.TemporaryDirectory() as tmpdir:
            original = research_mod._FINDINGS_DIR
            research_mod._FINDINGS_DIR = tmpdir
            try:
                wf = ResearchWorkflow()
                runner = WorkflowRunner()
                result = runner.run("research", wf.steps("UMH substrate"), source="test")
                assert result.steps_total == 4
                assert result.steps_completed >= 3
            finally:
                research_mod._FINDINGS_DIR = original
