"""P3 Phase 3 — Browser Task Workflow tests.

Verifies:
1. BrowserWorkflow produces governed steps for scrape/research/monitor
2. URL and query validation works correctly
3. Mocked adapter calls execute through runner
4. Deterministic fallbacks when adapters fail

Run with: pytest tests/test_p3_phase3_browser.py -v
"""

import os
import sys
import tempfile
from unittest.mock import MagicMock, patch

import pytest

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _REPO_ROOT)

pytestmark = pytest.mark.smoke


class TestBrowserWorkflowStructure:

    def test_importable(self):
        from projections.eos.workflows.browser import BrowserWorkflow
        assert BrowserWorkflow is not None

    def test_scrape_steps_returns_3(self):
        from projections.eos.workflows.browser import BrowserWorkflow
        wf = BrowserWorkflow()
        steps = wf.scrape_steps("https://example.com")
        assert len(steps) == 3
        names = [s.name for s in steps]
        assert names == ["validate_url", "fetch_page", "extract_data"]

    def test_research_steps_returns_3(self):
        from projections.eos.workflows.browser import BrowserWorkflow
        wf = BrowserWorkflow()
        steps = wf.research_steps("competitor pricing")
        assert len(steps) == 3
        names = [s.name for s in steps]
        assert names == ["validate_query", "search_and_fetch", "synthesize_results"]

    def test_monitor_steps_returns_3(self):
        from projections.eos.workflows.browser import BrowserWorkflow
        wf = BrowserWorkflow()
        steps = wf.monitor_steps("https://example.com")
        assert len(steps) == 3
        names = [s.name for s in steps]
        assert names == ["validate_url", "fetch_current", "compare_baseline"]

    def test_all_steps_have_mutation_names(self):
        from projections.eos.workflows.browser import BrowserWorkflow
        wf = BrowserWorkflow()
        all_steps = (
            wf.scrape_steps("https://example.com")
            + wf.research_steps("test query")
            + wf.monitor_steps("https://example.com")
        )
        for step in all_steps:
            assert step.mutation_name, f"{step.name} missing mutation_name"
            assert step.intent, f"{step.name} missing intent"

    def test_package_export(self):
        from projections.eos.workflows import BrowserWorkflow
        assert BrowserWorkflow is not None


class TestBrowserValidation:

    def test_valid_url(self):
        from projections.eos.workflows.browser import BrowserWorkflow
        wf = BrowserWorkflow()
        output, success = wf._validate_url("https://example.com")
        assert success
        assert "valid" in output.lower()

    def test_empty_url(self):
        from projections.eos.workflows.browser import BrowserWorkflow
        wf = BrowserWorkflow()
        output, success = wf._validate_url("")
        assert not success

    def test_invalid_scheme(self):
        from projections.eos.workflows.browser import BrowserWorkflow
        wf = BrowserWorkflow()
        output, success = wf._validate_url("ftp://example.com")
        assert not success
        assert "scheme" in output.lower()

    def test_no_domain(self):
        from projections.eos.workflows.browser import BrowserWorkflow
        wf = BrowserWorkflow()
        output, success = wf._validate_url("https://")
        assert not success

    def test_valid_query(self):
        from projections.eos.workflows.browser import BrowserWorkflow
        wf = BrowserWorkflow()
        output, success = wf._validate_query("competitor pricing models")
        assert success

    def test_empty_query(self):
        from projections.eos.workflows.browser import BrowserWorkflow
        wf = BrowserWorkflow()
        output, success = wf._validate_query("")
        assert not success

    def test_short_query(self):
        from projections.eos.workflows.browser import BrowserWorkflow
        wf = BrowserWorkflow()
        output, success = wf._validate_query("ab")
        assert not success


class TestBrowserExecution:

    @patch("projections.eos.workflows.browser.ScraplingConnector", create=True)
    def test_fetch_page_success(self, _mock_class):
        from projections.eos.workflows.browser import BrowserWorkflow

        mock_sc = MagicMock()
        mock_sc.fetch.return_value = {
            "url": "https://example.com",
            "title": "Example",
            "text": "Hello world content",
            "links": ["https://link1.com"],
            "status": "ok",
        }

        with patch(
            "adapters.scrapling.scrapling_connector.ScraplingConnector",
            return_value=mock_sc,
        ):
            wf = BrowserWorkflow()
            output, success = wf._fetch_page("https://example.com")
            assert success
            assert "Example" in output
            assert wf._scrape_result is not None

    def test_fetch_page_import_error(self):
        from projections.eos.workflows.browser import BrowserWorkflow

        with patch.dict("sys.modules", {"adapters.scrapling.scrapling_connector": None}):
            wf = BrowserWorkflow()
            output, success = wf._fetch_page("https://example.com")
            assert not success
            assert "not installed" in output or "error" in output.lower()

    def test_extract_data_no_fetch(self):
        from projections.eos.workflows.browser import BrowserWorkflow
        wf = BrowserWorkflow()
        output, success = wf._extract_data()
        assert not success

    def test_extract_data_after_fetch(self):
        from projections.eos.workflows.browser import BrowserWorkflow, ScrapeResult

        with tempfile.TemporaryDirectory() as tmpdir:
            import projections.eos.workflows.browser as mod
            orig = mod._BROWSER_DATA_DIR
            mod._BROWSER_DATA_DIR = tmpdir
            try:
                wf = BrowserWorkflow()
                wf._scrape_result = ScrapeResult(
                    url="https://example.com",
                    title="Test Page",
                    text="Some extracted text content",
                    links=["https://link1.com"],
                    status="ok",
                )
                output, success = wf._extract_data()
                assert success
                assert "Test Page" in output or "Extracted" in output
                files = os.listdir(tmpdir)
                assert len(files) == 1
            finally:
                mod._BROWSER_DATA_DIR = orig

    def test_monitor_report_no_result(self):
        from projections.eos.workflows.browser import BrowserWorkflow
        wf = BrowserWorkflow()
        output, success = wf._report_monitor()
        assert not success

    def test_monitor_report_with_result(self):
        from projections.eos.workflows.browser import BrowserWorkflow, MonitorResult
        wf = BrowserWorkflow()
        wf._monitor_result = MonitorResult(
            url="https://example.com",
            changed=True,
            title="Example",
            status="ok",
        )
        output, success = wf._report_monitor()
        assert success
        assert "CHANGED" in output

    def test_scrape_through_runner(self):
        from projections.eos.workflows.browser import BrowserWorkflow
        from projections.eos.workflows.runner import WorkflowRunner

        wf = BrowserWorkflow()
        runner = WorkflowRunner()
        result = runner.run("scrape", wf.scrape_steps("ftp://bad"), source="test")
        assert result.steps_total == 3
        assert result.steps_completed == 0
        assert not result.success

    def test_research_through_runner_bad_query(self):
        from projections.eos.workflows.browser import BrowserWorkflow
        from projections.eos.workflows.runner import WorkflowRunner

        wf = BrowserWorkflow()
        runner = WorkflowRunner()
        result = runner.run("research", wf.research_steps(""), source="test")
        assert not result.success

    def test_monitor_through_runner_valid_url(self):
        from projections.eos.workflows.browser import BrowserWorkflow
        from projections.eos.workflows.runner import WorkflowRunner

        with patch(
            "adapters.scrapling.scrapling_connector.ScraplingConnector"
        ) as mock_cls:
            mock_sc = MagicMock()
            mock_sc.monitor_competitor.return_value = {
                "url": "https://example.com",
                "changed": False,
                "title": "Example",
                "status": "ok",
            }
            mock_cls.return_value = mock_sc

            wf = BrowserWorkflow()
            runner = WorkflowRunner()
            result = runner.run(
                "monitor",
                wf.monitor_steps("https://example.com"),
                source="test",
            )
            assert result.success
            assert result.steps_completed == 3
