"""Tests for substrate.organism.report_dispatcher."""

from __future__ import annotations

import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

import pytest
from substrate.organism.report_dispatcher import Report, ReportDispatcher, DispatchResult


class TestReport:
    def test_report_creation(self):
        r = Report(title="Test", summary="Summary", body="Body content")
        assert r.title == "Test"
        assert r.summary == "Summary"
        assert r.body == "Body content"
        assert r.created_at > 0

    def test_report_with_file_path(self):
        r = Report(title="T", summary="S", body="B", file_path="/tmp/report.md")
        assert r.file_path == "/tmp/report.md"

    def test_report_with_metadata(self):
        r = Report(title="T", summary="S", body="B", metadata={"pr": "#7"})
        assert r.metadata["pr"] == "#7"


class TestDispatchResult:
    def test_all_succeeded_true(self):
        r = DispatchResult(discord_sent=True, cockpit_sent=True, store_saved=True)
        assert r.all_succeeded is True

    def test_all_succeeded_false(self):
        r = DispatchResult(discord_sent=False, cockpit_sent=True, store_saved=True)
        assert r.all_succeeded is False

    def test_to_dict(self):
        r = DispatchResult(discord_sent=True, cockpit_sent=True, store_saved=True, errors=["e1"])
        d = r.to_dict()
        assert d["discord_sent"] is True
        assert d["errors"] == ["e1"]
        assert "all_succeeded" in d


class TestReportDispatcherLocal:
    """Tests that don't require Discord (local store + cockpit only)."""

    def test_save_to_store(self):
        with tempfile.TemporaryDirectory() as td:
            dispatcher = ReportDispatcher(store_dir=td, discord_token="", discord_channel_id="")
            report = Report(title="Test Report", summary="Test summary", body="Full body")
            result = dispatcher.dispatch_report(report)
            assert result.store_saved is True
            reports_path = os.path.join(td, "reports.jsonl")
            assert os.path.exists(reports_path)
            with open(reports_path) as f:
                record = json.loads(f.readline())
            assert record["title"] == "Test Report"
            assert record["type"] == "report"

    def test_send_to_cockpit(self):
        with tempfile.TemporaryDirectory() as td:
            dispatcher = ReportDispatcher(store_dir=td, discord_token="", discord_channel_id="")
            report = Report(title="Cockpit Report", summary="For cockpit", body="Details")
            result = dispatcher.dispatch_report(report)
            assert result.cockpit_sent is True
            messages_path = os.path.join(td, "messages.jsonl")
            assert os.path.exists(messages_path)
            with open(messages_path) as f:
                msg = json.loads(f.readline())
            assert msg["sender"] == "system"
            assert msg["recipient"] == "operator"
            assert msg["intent"] == "report"
            assert msg["payload"]["title"] == "Cockpit Report"

    def test_discord_fails_gracefully_without_credentials(self, monkeypatch):
        monkeypatch.setenv("UMH_ROOT", "/nonexistent")
        with tempfile.TemporaryDirectory() as td:
            dispatcher = ReportDispatcher(store_dir=td, discord_token="", discord_channel_id="")
            dispatcher._discord_token = ""
            dispatcher._discord_channel_id = ""
            report = Report(title="T", summary="S", body="B")
            result = dispatcher.dispatch_report(report)
            assert result.discord_sent is False
            assert len(result.errors) == 1
            assert "not configured" in result.errors[0]
            assert result.store_saved is True
            assert result.cockpit_sent is True

    def test_list_reports_empty(self):
        with tempfile.TemporaryDirectory() as td:
            dispatcher = ReportDispatcher(store_dir=td)
            assert dispatcher.list_reports() == []

    def test_list_reports_returns_saved(self):
        with tempfile.TemporaryDirectory() as td:
            dispatcher = ReportDispatcher(store_dir=td, discord_token="", discord_channel_id="")
            dispatcher.dispatch_report(Report(title="R1", summary="S1", body="B1"))
            dispatcher.dispatch_report(Report(title="R2", summary="S2", body="B2"))
            reports = dispatcher.list_reports()
            assert len(reports) == 2
            assert reports[0]["title"] == "R1"
            assert reports[1]["title"] == "R2"

    def test_list_reports_respects_limit(self):
        with tempfile.TemporaryDirectory() as td:
            dispatcher = ReportDispatcher(store_dir=td, discord_token="", discord_channel_id="")
            for i in range(5):
                dispatcher.dispatch_report(Report(title=f"R{i}", summary="S", body="B"))
            reports = dispatcher.list_reports(limit=2)
            assert len(reports) == 2
            assert reports[0]["title"] == "R3"

    def test_cockpit_message_format_is_agent_message_compatible(self):
        """Cockpit messages must have the same fields as AgentMessage."""
        with tempfile.TemporaryDirectory() as td:
            dispatcher = ReportDispatcher(store_dir=td, discord_token="", discord_channel_id="")
            dispatcher.dispatch_report(Report(title="T", summary="S", body="B"))
            with open(os.path.join(td, "messages.jsonl")) as f:
                msg = json.loads(f.readline())
            required_fields = {"id", "sender", "recipient", "intent", "payload", "conversation_id", "parent_message_id", "created_at"}
            assert required_fields.issubset(set(msg.keys()))

    def test_report_with_file_path_records_it(self):
        with tempfile.TemporaryDirectory() as td:
            dispatcher = ReportDispatcher(store_dir=td, discord_token="", discord_channel_id="")
            report = Report(title="T", summary="S", body="B", file_path="/opt/OS/docs/report.md")
            dispatcher.dispatch_report(report)
            with open(os.path.join(td, "reports.jsonl")) as f:
                record = json.loads(f.readline())
            assert record["file_path"] == "/opt/OS/docs/report.md"


class TestBridgeIntegration:
    def test_dispatch_report_handler_exists(self):
        from saas.bridge.organism_bridge import _ACTIONS
        assert "organism.dispatch_report" in _ACTIONS

    def test_reports_handler_exists(self):
        from saas.bridge.organism_bridge import _ACTIONS
        assert "organism.reports" in _ACTIONS

    def test_chat_history_handler_exists(self):
        from saas.bridge.organism_bridge import _ACTIONS
        assert "organism.chat_history" in _ACTIONS

    def test_dispatch_requires_title_and_summary(self):
        from saas.bridge.organism_bridge import _ACTIONS
        handler = _ACTIONS["organism.dispatch_report"]
        result = handler({"body": "just a body"})
        assert result["success"] is False
        assert "title and summary required" in result["error"]
