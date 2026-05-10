"""Tests for Phase 7B: Tool Integration Layer (API + CLI).

Verifies:
- GET /tools returns list of built-in tools
- GET /tools/{name} returns tool details
- GET /tools/nonexistent returns 404
- POST /tools/{name}/execute with valid inputs
- POST /tools/{name}/execute with invalid tool returns 404
- GET /tools requires auth (401 without key)
- cmd_tools lists tools
- cmd_tools --json output
- cmd_tool_run with valid tool (mock execute)
- cmd_tool_run with unknown tool
- Tool list includes http_get, http_post, webhook
- Tool execute endpoint routes through execution engine
"""

import json
import os
import sys

sys.path.insert(0, "/opt/OS")

os.environ.setdefault("UMH_API_KEY", "test-key-phase7b")

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from umh.control.api import app

client = TestClient(app)
HEADERS = {"X-API-Key": "test-key-phase7b"}


# ── A. GET /tools — list tools ─────────────────────────────────────


class TestListTools:
    def test_list_tools_returns_list(self):
        resp = client.get("/tools", headers=HEADERS)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) >= 3  # http_get, http_post, webhook

    def test_list_tools_includes_http_get(self):
        resp = client.get("/tools", headers=HEADERS)
        names = [t["name"] for t in resp.json()]
        assert "http_get" in names

    def test_list_tools_includes_http_post(self):
        resp = client.get("/tools", headers=HEADERS)
        names = [t["name"] for t in resp.json()]
        assert "http_post" in names

    def test_list_tools_includes_webhook(self):
        resp = client.get("/tools", headers=HEADERS)
        names = [t["name"] for t in resp.json()]
        assert "webhook" in names

    def test_list_tools_structure(self):
        resp = client.get("/tools", headers=HEADERS)
        tool = resp.json()[0]
        assert "name" in tool
        assert "operation" in tool
        assert "description" in tool
        assert "required_inputs" in tool
        assert "optional_inputs" in tool
        assert "mutating" in tool
        assert "timeout_s" in tool

    def test_list_tools_requires_auth(self):
        resp = client.get("/tools")
        assert resp.status_code == 401


# ── B. GET /tools/{name} — get tool details ───────────────────────


class TestGetTool:
    def test_get_existing_tool(self):
        resp = client.get("/tools/http_get", headers=HEADERS)
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "http_get"
        assert data["operation"] == "http_request"
        assert data["mutating"] is False
        assert "url" in data["required_inputs"]
        assert "execution_class" in data

    def test_get_nonexistent_tool_returns_404(self):
        resp = client.get("/tools/nonexistent_tool", headers=HEADERS)
        assert resp.status_code == 404
        assert "Tool not found" in resp.json()["detail"]

    def test_get_tool_requires_auth(self):
        resp = client.get("/tools/http_get")
        assert resp.status_code == 401


# ── C. POST /tools/{name}/execute ──────────────────────────────────


class TestExecuteTool:
    def test_execute_nonexistent_tool_returns_404(self):
        resp = client.post(
            "/tools/nonexistent_tool/execute",
            headers=HEADERS,
            json={"inputs": {}},
        )
        assert resp.status_code == 404
        assert "Tool not found" in resp.json()["detail"]

    def test_execute_tool_routes_through_engine(self):
        """Verify tool execute calls the execution engine."""
        mock_result = MagicMock()
        mock_result.to_dict.return_value = {
            "execution_id": "tool_test123",
            "status": "succeeded",
            "outputs": {"status_code": 200, "body": "ok"},
        }

        with patch("umh.control.api.execute", return_value=mock_result) as mock_exec:
            resp = client.post(
                "/tools/http_get/execute",
                headers=HEADERS,
                json={"inputs": {"url": "https://httpbin.org/get"}},
            )
            assert resp.status_code == 200
            assert mock_exec.called
            call_args = mock_exec.call_args[0][0]
            assert call_args.operation == "http_request"
            assert call_args.inputs["url"] == "https://httpbin.org/get"
            assert call_args.inputs["tool_name"] == "http_get"

    def test_execute_tool_with_valid_inputs(self):
        """Execute tool with mock — verifies full request construction."""
        mock_result = MagicMock()
        mock_result.to_dict.return_value = {
            "execution_id": "tool_abc",
            "status": "succeeded",
            "outputs": {},
        }

        with patch("umh.control.api.execute", return_value=mock_result):
            resp = client.post(
                "/tools/http_post/execute",
                headers=HEADERS,
                json={
                    "inputs": {
                        "url": "https://httpbin.org/post",
                        "method": "POST",
                        "body": '{"key": "value"}',
                    }
                },
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["status"] == "succeeded"

    def test_execute_tool_requires_auth(self):
        resp = client.post(
            "/tools/http_get/execute",
            json={"inputs": {"url": "https://httpbin.org/get"}},
        )
        assert resp.status_code == 401

    def test_execute_tool_sets_method_default(self):
        """If no method in inputs, default to GET."""
        mock_result = MagicMock()
        mock_result.to_dict.return_value = {
            "execution_id": "tool_def",
            "status": "succeeded",
            "outputs": {},
        }

        with patch("umh.control.api.execute", return_value=mock_result) as mock_exec:
            resp = client.post(
                "/tools/http_get/execute",
                headers=HEADERS,
                json={"inputs": {"url": "https://httpbin.org/get"}},
            )
            assert resp.status_code == 200
            call_args = mock_exec.call_args[0][0]
            assert call_args.inputs["method"] == "GET"


# ── D. CLI: cmd_tools ──────────────────────────────────────────────


class TestCLITools:
    def test_cmd_tools_lists_tools(self, capsys):
        from umh.control.cli import cmd_tools

        args = MagicMock()
        args.json = False
        result = cmd_tools(args)
        assert result == 0
        captured = capsys.readouterr()
        assert "http_get" in captured.out
        assert "http_post" in captured.out
        assert "webhook" in captured.out

    def test_cmd_tools_json_output(self, capsys):
        from umh.control.cli import cmd_tools

        args = MagicMock()
        args.json = True
        result = cmd_tools(args)
        assert result == 0
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert isinstance(data, list)
        names = [t["name"] for t in data]
        assert "http_get" in names
        assert "http_post" in names
        assert "webhook" in names

    def test_cmd_tools_shows_mutating_flag(self, capsys):
        from umh.control.cli import cmd_tools

        args = MagicMock()
        args.json = False
        cmd_tools(args)
        captured = capsys.readouterr()
        assert "[MUTATING]" in captured.out

    def test_cmd_tools_shows_required_inputs(self, capsys):
        from umh.control.cli import cmd_tools

        args = MagicMock()
        args.json = False
        cmd_tools(args)
        captured = capsys.readouterr()
        assert "Required:" in captured.out
        assert "url" in captured.out


# ── E. CLI: cmd_tool_run ───────────────────────────────────────────


class TestCLIToolRun:
    def test_tool_run_unknown_tool(self, capsys):
        from umh.control.cli import cmd_tool_run

        args = MagicMock()
        args.tool_name = "nonexistent_tool"
        args.json = False
        args.url = None
        args.method = None
        args.body = None
        result = cmd_tool_run(args)
        assert result == 1
        captured = capsys.readouterr()
        assert "Unknown tool" in captured.out

    def test_tool_run_unknown_tool_json(self, capsys):
        from umh.control.cli import cmd_tool_run

        args = MagicMock()
        args.tool_name = "nonexistent_tool"
        args.json = True
        args.url = None
        args.method = None
        args.body = None
        result = cmd_tool_run(args)
        assert result == 1
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert "error" in data

    def test_tool_run_with_mock_execute(self, capsys):
        from umh.control.cli import cmd_tool_run

        mock_plan = MagicMock()
        mock_plan.status = MagicMock()
        mock_plan.status.value = "validated"

        mock_task = MagicMock()
        mock_task.to_dict.return_value = {
            "id": "tool_cli_test",
            "status": "completed",
            "steps": [{"result": {"status_code": 200, "body": '{"ok": true}'}}],
        }

        args = MagicMock()
        args.tool_name = "http_get"
        args.json = False
        args.url = "https://httpbin.org/get"
        args.method = None
        args.body = None

        from umh.planning.models import PlanStatus

        mock_plan.status = PlanStatus.VALIDATED

        with (
            patch("umh.planning.planner.create_plan", return_value=mock_plan),
            patch("umh.planning.planner.execute_plan", return_value=mock_task),
        ):
            result = cmd_tool_run(args)

        assert result == 0
        captured = capsys.readouterr()
        assert "Tool: http_get" in captured.out
        assert "Status: completed" in captured.out

    def test_tool_run_json_output(self, capsys):
        from umh.control.cli import cmd_tool_run

        mock_plan = MagicMock()
        mock_task = MagicMock()
        mock_task.to_dict.return_value = {
            "id": "tool_cli_json",
            "status": "completed",
            "steps": [],
        }

        args = MagicMock()
        args.tool_name = "http_get"
        args.json = True
        args.url = "https://httpbin.org/get"
        args.method = "GET"
        args.body = None

        from umh.planning.models import PlanStatus

        mock_plan.status = PlanStatus.VALIDATED

        with (
            patch("umh.planning.planner.create_plan", return_value=mock_plan),
            patch("umh.planning.planner.execute_plan", return_value=mock_task),
        ):
            result = cmd_tool_run(args)

        assert result == 0
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert data["status"] == "completed"


# ── F. Tool list completeness ──────────────────────────────────────


class TestToolListCompleteness:
    def test_built_in_tools_present(self):
        """Verify all three built-in tools are in the registry."""
        from umh.tools.registry import list_tools

        tools = list_tools()
        names = {t.name for t in tools}
        assert "http_get" in names
        assert "http_post" in names
        assert "webhook" in names

    def test_tool_definitions_valid(self):
        """Each built-in tool has required fields populated."""
        from umh.tools.registry import list_tools

        for tool in list_tools():
            assert tool.name
            assert tool.operation
            assert tool.description
            assert isinstance(tool.required_inputs, list)
            assert isinstance(tool.timeout_s, int)
            assert tool.timeout_s > 0
