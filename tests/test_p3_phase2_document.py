"""P3 Phase 2 — Document Generation Workflow tests.

Verifies:
1. DocumentWorkflow produces governed steps for all doc types
2. Validation catches missing required fields
3. Deterministic fallbacks produce content when adapter fails
4. Full lifecycle through WorkflowRunner

Run with: pytest tests/test_p3_phase2_document.py -v
"""

import os
import sys
import tempfile

import pytest

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _REPO_ROOT)

pytestmark = pytest.mark.smoke


class TestDocumentWorkflowStructure:

    def test_importable(self):
        from projections.eos.workflows.document import DocumentWorkflow
        assert DocumentWorkflow is not None

    def test_generate_steps_returns_3(self):
        from projections.eos.workflows.document import DocumentWorkflow
        wf = DocumentWorkflow()
        steps = wf.generate_steps("briefing", {"title": "Test", "topic": "Testing"})
        assert len(steps) == 3
        names = [s.name for s in steps]
        assert names == ["validate_request", "generate_document", "store_document"]

    def test_all_steps_have_mutation_names(self):
        from projections.eos.workflows.document import DocumentWorkflow
        wf = DocumentWorkflow()
        for doc_type in ["briefing", "board_update", "investor_update",
                         "proposal", "slides", "announcement", "crisis"]:
            ctx = {"title": "Test", "topic": "Test", "what_happened": "test"}
            steps = wf.generate_steps(doc_type, ctx)
            for step in steps:
                assert step.mutation_name, f"{doc_type}/{step.name} missing mutation_name"

    def test_invalid_doc_type_defaults_to_briefing(self):
        from projections.eos.workflows.document import DocumentWorkflow
        wf = DocumentWorkflow()
        steps = wf.generate_steps("invalid_type", {"title": "Test"})
        assert len(steps) == 3
        assert wf._doc_ctx.doc_type == "briefing"

    def test_valid_doc_types(self):
        from projections.eos.workflows.document import VALID_DOC_TYPES
        expected = {"briefing", "board_update", "investor_update", "proposal",
                    "slides", "announcement", "crisis"}
        assert VALID_DOC_TYPES == expected


class TestDocumentValidation:

    def test_validate_briefing_fills_defaults(self):
        from projections.eos.workflows.document import DocumentWorkflow
        wf = DocumentWorkflow()
        wf.generate_steps("briefing", {"topic": "UMH"})
        output, success = wf._validate_request()
        assert success
        assert wf._doc_ctx.title == "UMH"

    def test_validate_announcement_requires_topic(self):
        from projections.eos.workflows.document import DocumentWorkflow
        wf = DocumentWorkflow()
        wf.generate_steps("announcement", {})
        output, success = wf._validate_request()
        assert not success
        assert "requires a topic" in output

    def test_validate_crisis_requires_what_happened(self):
        from projections.eos.workflows.document import DocumentWorkflow
        wf = DocumentWorkflow()
        wf.generate_steps("crisis", {"topic": "outage"})
        output, success = wf._validate_request()
        assert not success
        assert "requires what_happened" in output

    def test_validate_crisis_with_what_happened_passes(self):
        from projections.eos.workflows.document import DocumentWorkflow
        wf = DocumentWorkflow()
        wf.generate_steps("crisis", {
            "topic": "outage",
            "what_happened": "server went down",
        })
        output, success = wf._validate_request()
        assert success


class TestDocumentDeterministicFallbacks:

    def test_briefing_fallback(self):
        from projections.eos.workflows.document import DocumentWorkflow, DocumentContext
        wf = DocumentWorkflow()
        dc = DocumentContext(doc_type="briefing", title="Test Brief", topic="Testing")
        content = wf._deterministic_briefing(dc)
        assert "Test Brief" in content
        assert "Testing" in content

    def test_slides_fallback(self):
        from projections.eos.workflows.document import DocumentWorkflow, DocumentContext
        wf = DocumentWorkflow()
        dc = DocumentContext(doc_type="slides", title="Test Deck", slide_count=3)
        content = wf._deterministic_slides(dc)
        assert "Test Deck" in content
        assert "Slide 1" in content
        assert "Slide 3" in content

    def test_announcement_fallback(self):
        from projections.eos.workflows.document import DocumentWorkflow, DocumentContext
        wf = DocumentWorkflow()
        dc = DocumentContext(
            doc_type="announcement", topic="Launch",
            key_message="We're live", audience="team",
        )
        content = wf._deterministic_announcement(dc)
        assert "Launch" in content
        assert "We're live" in content

    def test_crisis_fallback(self):
        from projections.eos.workflows.document import DocumentWorkflow, DocumentContext
        wf = DocumentWorkflow()
        dc = DocumentContext(
            doc_type="crisis",
            what_happened="server crashed",
            affected_parties="all users",
            what_we_are_doing="restarting",
        )
        content = wf._deterministic_crisis(dc)
        assert "server crashed" in content
        assert "all users" in content


class TestDocumentExecution:

    def test_generate_briefing_with_fallback(self):
        from projections.eos.workflows.document import DocumentWorkflow
        wf = DocumentWorkflow()
        wf.generate_steps("briefing", {"title": "Test", "topic": "Test topic"})
        wf._validate_request()
        output, success = wf._generate_document()
        assert success
        assert wf._content

    def test_generate_slides_with_fallback(self):
        from projections.eos.workflows.document import DocumentWorkflow
        wf = DocumentWorkflow()
        wf.generate_steps("slides", {"title": "Deck", "topic": "UMH", "slide_count": 3})
        wf._validate_request()
        output, success = wf._generate_document()
        assert success
        assert wf._content

    def test_generate_announcement_with_fallback(self):
        from projections.eos.workflows.document import DocumentWorkflow
        wf = DocumentWorkflow()
        wf.generate_steps("announcement", {
            "topic": "Launch", "key_message": "Go", "audience": "team",
        })
        wf._validate_request()
        output, success = wf._generate_document()
        assert success

    def test_generate_crisis_with_fallback(self):
        from projections.eos.workflows.document import DocumentWorkflow
        wf = DocumentWorkflow()
        wf.generate_steps("crisis", {
            "topic": "outage",
            "what_happened": "server down",
            "affected_parties": "users",
            "what_we_are_doing": "fixing",
        })
        wf._validate_request()
        output, success = wf._generate_document()
        assert success

    def test_store_document_creates_file(self):
        from projections.eos.workflows import document as doc_mod
        from projections.eos.workflows.document import DocumentWorkflow

        with tempfile.TemporaryDirectory() as tmpdir:
            original = doc_mod._DOCS_DIR
            doc_mod._DOCS_DIR = tmpdir
            try:
                wf = DocumentWorkflow()
                wf.generate_steps("briefing", {"title": "Store Test", "topic": "Test"})
                wf._validate_request()
                wf._generate_document()
                output, success = wf._store_document()
                assert success
                files = os.listdir(tmpdir)
                assert len(files) == 1
                assert files[0].endswith(".md")
            finally:
                doc_mod._DOCS_DIR = original

    def test_full_workflow_through_runner(self):
        from projections.eos.workflows import document as doc_mod
        from projections.eos.workflows.document import DocumentWorkflow
        from projections.eos.workflows.runner import WorkflowRunner

        with tempfile.TemporaryDirectory() as tmpdir:
            original = doc_mod._DOCS_DIR
            doc_mod._DOCS_DIR = tmpdir
            try:
                wf = DocumentWorkflow()
                runner = WorkflowRunner()
                result = runner.run(
                    "document_generate",
                    wf.generate_steps("briefing", {
                        "title": "Runner Test",
                        "topic": "Integration",
                    }),
                    source="test",
                )
                assert result.success
                assert result.steps_completed == 3
                assert result.steps_total == 3
                files = os.listdir(tmpdir)
                assert len(files) == 1
            finally:
                doc_mod._DOCS_DIR = original

    def test_all_doc_types_through_runner(self):
        from projections.eos.workflows import document as doc_mod
        from projections.eos.workflows.document import DocumentWorkflow
        from projections.eos.workflows.runner import WorkflowRunner

        with tempfile.TemporaryDirectory() as tmpdir:
            original = doc_mod._DOCS_DIR
            doc_mod._DOCS_DIR = tmpdir
            try:
                runner = WorkflowRunner()
                doc_types = [
                    ("briefing", {"title": "Brief", "topic": "Test"}),
                    ("board_update", {"topic": "Review"}),
                    ("investor_update", {"topic": "Progress"}),
                    ("proposal", {"title": "Deal", "topic": "Partnership"}),
                    ("slides", {"title": "Deck", "topic": "UMH", "slide_count": 3}),
                    ("announcement", {"topic": "Launch", "key_message": "Live"}),
                    ("crisis", {
                        "topic": "outage",
                        "what_happened": "down",
                        "what_we_are_doing": "fixing",
                    }),
                ]
                for doc_type, ctx in doc_types:
                    wf = DocumentWorkflow()
                    result = runner.run(
                        f"doc_{doc_type}",
                        wf.generate_steps(doc_type, ctx),
                        source="test",
                    )
                    assert result.success, f"{doc_type} failed: {result.summary()}"

                files = os.listdir(tmpdir)
                assert len(files) == 7, f"Expected 7 docs, got {len(files)}: {files}"
            finally:
                doc_mod._DOCS_DIR = original
