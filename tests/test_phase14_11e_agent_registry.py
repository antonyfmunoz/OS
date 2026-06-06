"""Phase 14.11E — Agent registry and command center route tests."""

from __future__ import annotations

import asyncio
import json
import os
import sys
import tempfile

sys.path.insert(0, "/opt/OS")

import pytest


def _run(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


class FakeReq:
    def __init__(self, body: dict | None = None, query: dict | None = None):
        self._body = body or {}
        self.query_params = query or {}

    async def json(self):
        return self._body


class TestAgentRegistry:
    def test_agents_returns_ok(self) -> None:
        from transports.api.cockpit_command_center_routes import _agents
        result = _run(_agents(FakeReq()))
        assert result["ok"] is True

    def test_agents_has_summary(self) -> None:
        from transports.api.cockpit_command_center_routes import _agents
        result = _run(_agents(FakeReq()))
        assert "summary" in result
        assert "total" in result["summary"]
        assert "active" in result["summary"]
        assert "idle" in result["summary"]

    def test_agents_source_env(self) -> None:
        from transports.api.cockpit_command_center_routes import _agents
        result = _run(_agents(FakeReq()))
        assert result["source_env"] in ("vps", "container", "macos", "windows", "unknown")

    def test_agents_from_heartbeats(self) -> None:
        from transports.api.cockpit_command_center_routes import _agents
        result = _run(_agents(FakeReq()))
        if result["agents"]:
            agent = result["agents"][0]
            assert "agent_id" in agent
            assert "display_name" in agent
            assert "role" in agent
            assert "status" in agent
            assert "runtime" in agent
            assert "environment" in agent
            assert "node" in agent

    def test_agents_environment_labeled(self) -> None:
        from transports.api.cockpit_command_center_routes import _agents
        result = _run(_agents(FakeReq()))
        for agent in result["agents"]:
            assert "environment" in agent, f"Agent {agent.get('agent_id')} missing environment"
            assert "node" in agent, f"Agent {agent.get('agent_id')} missing node"

    def test_heartbeat_loading(self) -> None:
        from transports.api.cockpit_command_center_routes import _load_workcell_heartbeats
        heartbeats = _load_workcell_heartbeats()
        assert isinstance(heartbeats, list)
        for hb in heartbeats:
            assert "workcell_dir" in hb
            assert "status" in hb or "error" in hb

    def test_agent_fields_complete(self) -> None:
        from transports.api.cockpit_command_center_routes import _agents
        result = _run(_agents(FakeReq()))
        required_fields = [
            "agent_id", "display_name", "role", "status",
            "runtime", "authority_level", "last_heartbeat",
            "messages_processed", "inbox_depth",
            "environment", "node", "source_env",
        ]
        for agent in result["agents"]:
            for field in required_fields:
                assert field in agent, f"Missing field '{field}' in agent {agent.get('agent_id')}"


class TestWorkPacketBoard:
    def test_work_packets_returns_ok(self) -> None:
        from transports.api.cockpit_command_center_routes import _work_packets
        result = _run(_work_packets(FakeReq()))
        assert result["ok"] is True

    def test_work_packets_has_summary(self) -> None:
        from transports.api.cockpit_command_center_routes import _work_packets
        result = _run(_work_packets(FakeReq()))
        assert "summary" in result
        assert "total" in result["summary"]

    def test_work_packets_environment_labeled(self) -> None:
        from transports.api.cockpit_command_center_routes import _work_packets
        result = _run(_work_packets(FakeReq()))
        for pkt in result["packets"]:
            assert "environment" in pkt
            assert "node" in pkt

    def test_work_packets_fields(self) -> None:
        from transports.api.cockpit_command_center_routes import _work_packets
        result = _run(_work_packets(FakeReq()))
        required = [
            "packet_id", "title", "status", "risk_class",
            "blockers", "dependencies", "approval_state",
        ]
        for pkt in result["packets"]:
            for field in required:
                assert field in pkt, f"Missing '{field}' in packet {pkt.get('packet_id')}"

    def test_work_packets_limit(self) -> None:
        from transports.api.cockpit_command_center_routes import _work_packets
        result = _run(_work_packets(FakeReq(query={"limit": "5"})))
        assert len(result["packets"]) <= 5


class TestBlockedWork:
    def test_blocked_returns_ok(self) -> None:
        from transports.api.cockpit_command_center_routes import _blocked
        result = _run(_blocked(FakeReq()))
        assert result["ok"] is True

    def test_blocked_has_summary(self) -> None:
        from transports.api.cockpit_command_center_routes import _blocked
        result = _run(_blocked(FakeReq()))
        assert "summary" in result
        assert "total" in result["summary"]

    def test_blocked_items_have_type(self) -> None:
        from transports.api.cockpit_command_center_routes import _blocked
        result = _run(_blocked(FakeReq()))
        for item in result["blocked"]:
            assert item["type"] in ("work_packet", "execution_failure")

    def test_blocked_environment_labeled(self) -> None:
        from transports.api.cockpit_command_center_routes import _blocked
        result = _run(_blocked(FakeReq()))
        for item in result["blocked"]:
            assert "environment" in item


class TestApprovalsView:
    def test_approvals_returns_ok(self) -> None:
        from transports.api.cockpit_command_center_routes import _approvals_view
        result = _run(_approvals_view(FakeReq()))
        assert result["ok"] is True

    def test_approvals_has_summary(self) -> None:
        from transports.api.cockpit_command_center_routes import _approvals_view
        result = _run(_approvals_view(FakeReq()))
        assert "summary" in result

    def test_approvals_items_have_type(self) -> None:
        from transports.api.cockpit_command_center_routes import _approvals_view
        result = _run(_approvals_view(FakeReq()))
        for item in result["approvals"]:
            assert item["type"] in ("approval", "spine_envelope")

    def test_approvals_environment_labeled(self) -> None:
        from transports.api.cockpit_command_center_routes import _approvals_view
        result = _run(_approvals_view(FakeReq()))
        for item in result["approvals"]:
            assert "environment" in item


class TestTraces:
    def test_traces_returns_ok(self) -> None:
        from transports.api.cockpit_command_center_routes import _traces_view
        result = _run(_traces_view(FakeReq()))
        assert result["ok"] is True

    def test_traces_has_proofs(self) -> None:
        from transports.api.cockpit_command_center_routes import _traces_view
        result = _run(_traces_view(FakeReq()))
        assert "recent_proofs" in result
        assert isinstance(result["recent_proofs"], list)


class TestCommandCenterSummary:
    def test_summary_returns_ok(self) -> None:
        from transports.api.cockpit_command_center_routes import _summary
        result = _run(_summary(FakeReq()))
        assert result["ok"] is True

    def test_summary_has_all_sections(self) -> None:
        from transports.api.cockpit_command_center_routes import _summary
        result = _run(_summary(FakeReq()))
        sections = [
            "what_is_happening", "who_is_working",
            "what_is_blocked", "what_needs_approval",
            "what_finished", "what_failed",
            "what_should_resume_next",
        ]
        for s in sections:
            assert s in result, f"Missing section '{s}'"

    def test_summary_source_env(self) -> None:
        from transports.api.cockpit_command_center_routes import _summary
        result = _run(_summary(FakeReq()))
        assert result["source_env"] in ("vps", "container", "macos", "windows", "unknown")

    def test_summary_node(self) -> None:
        from transports.api.cockpit_command_center_routes import _summary
        result = _run(_summary(FakeReq()))
        assert result["node"] != ""

    def test_summary_agent_counts(self) -> None:
        from transports.api.cockpit_command_center_routes import _summary
        result = _run(_summary(FakeReq()))
        wih = result["what_is_happening"]
        assert "active_agents" in wih
        assert "idle_agents" in wih
        assert "total_agents" in wih
        assert wih["active_agents"] + wih["idle_agents"] <= wih["total_agents"]


class TestCrossDeviceLabeling:
    def test_label_environment(self) -> None:
        from transports.api.cockpit_command_center_routes import _label_environment
        item: dict = {}
        result = _label_environment(item)
        assert result["environment"] in ("vps", "container", "macos", "windows", "unknown")
        assert result["node"] != ""
        assert result["source_env"] in ("vps", "container", "macos", "windows", "unknown")

    def test_preserves_existing_env(self) -> None:
        from transports.api.cockpit_command_center_routes import _label_environment
        item: dict = {"environment": "windows", "node": "beast-pc"}
        result = _label_environment(item)
        assert result["environment"] == "windows"
        assert result["node"] == "beast-pc"
