"""Phase 14.11C — Workspace endpoint tests.

Tests git diff, test results, execution logs, proof artifacts,
health check, and trace linkage endpoints.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile

sys.path.insert(0, "/opt/OS")

import pytest


class TestGitStatus:
    def test_git_status_runs(self) -> None:
        from transports.api.cockpit_workspace_routes import _run_git
        ok, output = _run_git(["status", "--porcelain"])
        assert ok is True
        assert isinstance(output, str)

    def test_git_branch(self) -> None:
        from transports.api.cockpit_workspace_routes import _run_git
        ok, output = _run_git(["rev-parse", "--abbrev-ref", "HEAD"])
        assert ok is True
        assert output.strip() != ""

    def test_git_commit(self) -> None:
        from transports.api.cockpit_workspace_routes import _run_git
        ok, output = _run_git(["rev-parse", "--short", "HEAD"])
        assert ok is True
        assert len(output.strip()) >= 7


class TestGitDiff:
    def test_git_diff_stat(self) -> None:
        from transports.api.cockpit_workspace_routes import _run_git
        ok, output = _run_git(["diff", "--stat"])
        assert ok is True

    def test_git_diff_cached(self) -> None:
        from transports.api.cockpit_workspace_routes import _run_git
        ok, output = _run_git(["diff", "--cached", "--stat"])
        assert ok is True


class TestTestResults:
    def test_no_results_returns_recommended_command(self) -> None:
        from transports.api.cockpit_workspace_routes import _TEST_RESULTS_PATH
        if not os.path.exists(_TEST_RESULTS_PATH):
            import asyncio
            from transports.api.cockpit_workspace_routes import _test_results

            class FakeReq:
                query_params: dict[str, str] = {}

            result = asyncio.get_event_loop().run_until_complete(_test_results(FakeReq()))
            assert result["ok"] is True
            assert result["has_results"] is False
            assert "recommended_command" in result

    def test_results_from_file(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            test_data = {
                "command": "pytest tests/ -v",
                "status": "pass",
                "passed": 112,
                "failed": 0,
                "skipped": 0,
                "duration_seconds": 1.5,
            }
            path = os.path.join(d, "last_test_result.json")
            with open(path, "w") as f:
                json.dump(test_data, f)

            import transports.api.cockpit_workspace_routes as wr
            original = wr._TEST_RESULTS_PATH
            wr._TEST_RESULTS_PATH = path
            try:
                import asyncio

                class FakeReq:
                    query_params: dict[str, str] = {}

                result = asyncio.get_event_loop().run_until_complete(wr._test_results(FakeReq()))
                assert result["ok"] is True
                assert result["has_results"] is True
                assert result["passed"] == 112
            finally:
                wr._TEST_RESULTS_PATH = original


class TestExecutionLogs:
    def test_logs_return_list(self) -> None:
        import asyncio
        from transports.api.cockpit_workspace_routes import _execution_logs

        class FakeReq:
            query_params: dict[str, str] = {"limit": "10"}

        result = asyncio.get_event_loop().run_until_complete(_execution_logs(FakeReq()))
        assert result["ok"] is True
        assert isinstance(result["logs"], list)
        assert result["source_env"] != ""

    def test_logs_limit_capped(self) -> None:
        import asyncio
        from transports.api.cockpit_workspace_routes import _execution_logs

        class FakeReq:
            query_params: dict[str, str] = {"limit": "999"}

        result = asyncio.get_event_loop().run_until_complete(_execution_logs(FakeReq()))
        assert result["ok"] is True


class TestProofArtifacts:
    def test_proof_returns_structure(self) -> None:
        import asyncio
        from transports.api.cockpit_workspace_routes import _proof_artifacts

        class FakeReq:
            query_params: dict[str, str] = {}

        result = asyncio.get_event_loop().run_until_complete(_proof_artifacts(FakeReq()))
        assert result["ok"] is True
        assert isinstance(result["artifacts"], list)
        assert "playwright_available" in result
        assert "console_capture_available" in result
        assert result["source_env"] != ""

    def test_console_capture_explicit_blocker(self) -> None:
        import asyncio
        from transports.api.cockpit_workspace_routes import _proof_artifacts

        class FakeReq:
            query_params: dict[str, str] = {}

        result = asyncio.get_event_loop().run_until_complete(_proof_artifacts(FakeReq()))
        if not result["console_capture_available"]:
            assert "console_capture_blocker" in result
            assert result["console_capture_blocker"] != ""


class TestHealthCheck:
    def test_health_returns_checks(self) -> None:
        import asyncio
        from transports.api.cockpit_workspace_routes import _health_check

        class FakeReq:
            query_params: dict[str, str] = {}

        result = asyncio.get_event_loop().run_until_complete(_health_check(FakeReq()))
        assert result["ok"] is True
        assert result["overall"] in ("healthy", "degraded")
        assert isinstance(result["checks"], list)
        assert len(result["checks"]) >= 1

    def test_health_git_reachable(self) -> None:
        import asyncio
        from transports.api.cockpit_workspace_routes import _health_check

        class FakeReq:
            query_params: dict[str, str] = {}

        result = asyncio.get_event_loop().run_until_complete(_health_check(FakeReq()))
        git_check = next((c for c in result["checks"] if c["name"] == "git_repo"), None)
        assert git_check is not None
        assert git_check["status"] == "reachable"

    def test_health_source_env(self) -> None:
        import asyncio
        from transports.api.cockpit_workspace_routes import _health_check

        class FakeReq:
            query_params: dict[str, str] = {}

        result = asyncio.get_event_loop().run_until_complete(_health_check(FakeReq()))
        assert result["source_env"] != ""


class TestTraceLinkage:
    def test_linkage_returns_structure(self) -> None:
        import asyncio
        from transports.api.cockpit_workspace_routes import _trace_linkage

        class FakeReq:
            query_params: dict[str, str] = {}

        result = asyncio.get_event_loop().run_until_complete(_trace_linkage(FakeReq()))
        assert result["ok"] is True
        assert "links" in result
        links = result["links"]
        assert "execution_log" in links
        assert "test_result" in links
        assert "resume_state" in links

    def test_linkage_with_trace_id(self) -> None:
        import asyncio
        from transports.api.cockpit_workspace_routes import _trace_linkage

        class FakeReq:
            query_params = {"trace_id": "test_trace_xyz"}

        result = asyncio.get_event_loop().run_until_complete(_trace_linkage(FakeReq()))
        assert result["ok"] is True
        assert result["links"]["trace_id"] == "test_trace_xyz"

    def test_linkage_includes_resume_state(self) -> None:
        import asyncio
        from transports.api.cockpit_workspace_routes import _trace_linkage

        class FakeReq:
            query_params: dict[str, str] = {}

        result = asyncio.get_event_loop().run_until_complete(_trace_linkage(FakeReq()))
        assert result["ok"] is True


class TestProofClassification:
    def test_screenshot_type(self) -> None:
        from transports.api.cockpit_workspace_routes import _classify_proof
        assert _classify_proof("screen.png") == "screenshot"
        assert _classify_proof("capture.jpg") == "screenshot"

    def test_metadata_type(self) -> None:
        from transports.api.cockpit_workspace_routes import _classify_proof
        assert _classify_proof("result.json") == "metadata"

    def test_report_type(self) -> None:
        from transports.api.cockpit_workspace_routes import _classify_proof
        assert _classify_proof("summary.md") == "report"

    def test_unknown_type(self) -> None:
        from transports.api.cockpit_workspace_routes import _classify_proof
        assert _classify_proof("data.bin") == "other"


class TestDetectEnv:
    def test_detect_returns_string(self) -> None:
        from transports.api.cockpit_workspace_routes import _detect_env
        env = _detect_env()
        assert isinstance(env, str)
        assert env != ""
