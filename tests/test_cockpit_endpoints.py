"""Tests for cockpit API additions: activity stream, governance controls, DEX channel."""

import json
from pathlib import Path

import pytest


class TestActivityStream:
    """Test the unified activity stream merging logic."""

    def test_activity_stream_endpoint_imports(self):
        from transports.api.cockpit import activity_stream

        assert activity_stream is not None

    def test_activity_stream_merges_trace_data(self, tmp_path: Path):
        from transports.api import cockpit as cockpit_api

        trace_file = tmp_path / "traces.jsonl"
        trace_file.write_text(
            json.dumps(
                {
                    "trace_id": "t-001",
                    "input_signal": "test signal",
                    "adapter_used": "shell",
                    "governance_decision": "approve",
                    "status": "completed",
                    "created_at": "2026-05-22T00:00:00Z",
                }
            )
            + "\n"
        )

        original = cockpit_api.TRACE_STORE
        cockpit_api.TRACE_STORE = trace_file
        try:
            import asyncio

            events = asyncio.run(
                cockpit_api.activity_stream(source="trace")
            )
            assert len(events) == 1
            assert events[0]["source"] == "trace"
            assert events[0]["id"] == "t-001"
            assert events[0]["summary"] == "test signal"
        finally:
            cockpit_api.TRACE_STORE = original

    def test_activity_stream_skips_trace_updates(self, tmp_path: Path):
        from transports.api import cockpit as cockpit_api

        trace_file = tmp_path / "traces.jsonl"
        trace_file.write_text(
            json.dumps(
                {"trace_id": "t-001", "input_signal": "hello", "created_at": "2026-05-22T00:00:00Z"}
            )
            + "\n"
            + json.dumps({"_type": "trace_update", "trace_id": "t-001", "status": "failed"})
            + "\n"
        )

        original = cockpit_api.TRACE_STORE
        cockpit_api.TRACE_STORE = trace_file
        try:
            import asyncio

            events = asyncio.run(
                cockpit_api.activity_stream(source="trace")
            )
            assert len(events) == 1
        finally:
            cockpit_api.TRACE_STORE = original


class TestGovernanceControls:
    """Test governance policy read/write."""

    def test_governance_endpoint_returns_all_risk_classes(self):
        import asyncio

        from transports.api.cockpit import governance_policy

        result = asyncio.run(governance_policy())
        if "error" in result:
            pytest.skip("policy engine not available in test env")

        assert "policies" in result
        assert len(result["policies"]) == 8

        risk_classes = {p["risk_class"] for p in result["policies"]}
        assert "read_only" in risk_classes
        assert "financial" in risk_classes

    def test_governance_update_modifies_policy(self):
        import asyncio

        from substrate.governance.authority import AuthorityLevel
        from substrate.governance.policy_engine import _DEFAULT_POLICY
        from substrate.governance.risk_classes import RiskClass
        from transports.api.cockpit import update_governance

        original = _DEFAULT_POLICY[RiskClass.SAFE_WRITE]
        try:
            result = asyncio.run(
                update_governance({"policies": {"SAFE_WRITE": "APPROVE"}})
            )
            assert result["ok"] is True
            assert len(result["applied"]) == 1
            assert _DEFAULT_POLICY[RiskClass.SAFE_WRITE] == AuthorityLevel.APPROVE
        finally:
            _DEFAULT_POLICY[RiskClass.SAFE_WRITE] = original

    def test_governance_update_ignores_invalid_keys(self):
        import asyncio

        from transports.api.cockpit import update_governance

        result = asyncio.run(
            update_governance({"policies": {"NONEXISTENT": "APPROVE"}})
        )
        assert result["ok"] is True
        assert len(result["applied"]) == 0


class TestDexChannel:
    """Test DEX channel endpoints."""

    def test_dex_converse_endpoint_imports(self):
        from transports.api.cockpit import dex_converse

        assert dex_converse is not None

    def test_dex_history_endpoint_imports(self):
        from transports.api.cockpit import dex_history

        assert dex_history is not None

    def test_dex_converse_requires_organism_before_content_check(self):
        import asyncio

        from transports.api.cockpit import dex_converse

        result = asyncio.run(dex_converse({"content": ""}))
        assert result.get("error") == "organism not running"

    def test_dex_converse_requires_organism(self):
        import asyncio

        from transports.api.cockpit import dex_converse

        result = asyncio.run(dex_converse({"content": "hello"}))
        assert result.get("error") == "organism not running"
