"""Phase 14.11E — Command router integration tests for agent/task/work-packet commands."""

from __future__ import annotations

import asyncio
import sys

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


class TestNewIntentClassification:
    def test_show_active_agents(self) -> None:
        from substrate.workstation.command_router import CommandIntent, classify_intent
        assert classify_intent("show active agents") == CommandIntent.AGENT_QUERY

    def test_what_are_agents_doing(self) -> None:
        from substrate.workstation.command_router import CommandIntent, classify_intent
        assert classify_intent("what are the agents doing") == CommandIntent.AGENT_QUERY

    def test_fleet_status(self) -> None:
        from substrate.workstation.command_router import CommandIntent, classify_intent
        assert classify_intent("fleet status") == CommandIntent.AGENT_QUERY

    def test_agent_list(self) -> None:
        from substrate.workstation.command_router import CommandIntent, classify_intent
        assert classify_intent("agent list") == CommandIntent.AGENT_QUERY

    def test_what_is_blocked(self) -> None:
        from substrate.workstation.command_router import CommandIntent, classify_intent
        assert classify_intent("what is blocked") == CommandIntent.BLOCKED_QUERY

    def test_show_blockers(self) -> None:
        from substrate.workstation.command_router import CommandIntent, classify_intent
        assert classify_intent("show blockers") == CommandIntent.BLOCKED_QUERY

    def test_whats_stuck(self) -> None:
        from substrate.workstation.command_router import CommandIntent, classify_intent
        assert classify_intent("what's stuck") == CommandIntent.BLOCKED_QUERY

    def test_pause_work_packet(self) -> None:
        from substrate.workstation.command_router import CommandIntent, classify_intent
        assert classify_intent("pause this work packet") == CommandIntent.PACKET_CONTROL

    def test_resume_work_packet(self) -> None:
        from substrate.workstation.command_router import CommandIntent, classify_intent
        assert classify_intent("resume this work packet") == CommandIntent.PACKET_CONTROL

    def test_stop_work_packet(self) -> None:
        from substrate.workstation.command_router import CommandIntent, classify_intent
        assert classify_intent("stop this work packet") == CommandIntent.PACKET_CONTROL

    def test_route_to_agent(self) -> None:
        from substrate.workstation.command_router import CommandIntent, classify_intent
        assert classify_intent("route this to the right agent") == CommandIntent.PACKET_CONTROL

    def test_command_center(self) -> None:
        from substrate.workstation.command_router import CommandIntent, classify_intent
        assert classify_intent("command center") == CommandIntent.COMMAND_CENTER_QUERY

    def test_full_status(self) -> None:
        from substrate.workstation.command_router import CommandIntent, classify_intent
        assert classify_intent("full status") == CommandIntent.COMMAND_CENTER_QUERY

    def test_system_overview(self) -> None:
        from substrate.workstation.command_router import CommandIntent, classify_intent
        assert classify_intent("system overview") == CommandIntent.COMMAND_CENTER_QUERY

    def test_existing_intents_preserved(self) -> None:
        from substrate.workstation.command_router import CommandIntent, classify_intent
        assert classify_intent("what is happening") == CommandIntent.STATUS_QUERY
        assert classify_intent("catch me up") == CommandIntent.RESUME_QUERY
        assert classify_intent("what needs approval") == CommandIntent.APPROVAL_QUERY
        assert classify_intent("switch to review") == CommandIntent.MODE_SWITCH
        assert classify_intent("show dashboard") == CommandIntent.COCKPIT_NAVIGATION

    def test_case_insensitive(self) -> None:
        from substrate.workstation.command_router import CommandIntent, classify_intent
        assert classify_intent("SHOW ACTIVE AGENTS") == CommandIntent.AGENT_QUERY
        assert classify_intent("WHAT IS BLOCKED") == CommandIntent.BLOCKED_QUERY


class TestPacketControlActions:
    def test_pause_action(self) -> None:
        from substrate.workstation.command_router import resolve_packet_control_action
        assert resolve_packet_control_action("pause this work packet") == "pause"

    def test_resume_action(self) -> None:
        from substrate.workstation.command_router import resolve_packet_control_action
        assert resolve_packet_control_action("resume the work packet") == "resume"

    def test_stop_action(self) -> None:
        from substrate.workstation.command_router import resolve_packet_control_action
        assert resolve_packet_control_action("stop work packet") == "stop"

    def test_route_action(self) -> None:
        from substrate.workstation.command_router import resolve_packet_control_action
        assert resolve_packet_control_action("route this to executor") == "route"

    def test_unknown_action(self) -> None:
        from substrate.workstation.command_router import resolve_packet_control_action
        assert resolve_packet_control_action("foobar") == ""


class TestGovernanceNewIntents:
    def test_agent_query_informational(self) -> None:
        from substrate.workstation.command_router import CommandIntent, GovernanceRequirement, governance_requirement
        assert governance_requirement(CommandIntent.AGENT_QUERY) == GovernanceRequirement.INFORMATIONAL

    def test_blocked_query_informational(self) -> None:
        from substrate.workstation.command_router import CommandIntent, GovernanceRequirement, governance_requirement
        assert governance_requirement(CommandIntent.BLOCKED_QUERY) == GovernanceRequirement.INFORMATIONAL

    def test_command_center_informational(self) -> None:
        from substrate.workstation.command_router import CommandIntent, GovernanceRequirement, governance_requirement
        assert governance_requirement(CommandIntent.COMMAND_CENTER_QUERY) == GovernanceRequirement.INFORMATIONAL

    def test_packet_control_requires_governance(self) -> None:
        from substrate.workstation.command_router import CommandIntent, GovernanceRequirement, governance_requirement
        assert governance_requirement(CommandIntent.PACKET_CONTROL) == GovernanceRequirement.REQUIRES_GOVERNANCE


class TestPresenceRouteIntegration:
    def test_agent_query_via_command(self) -> None:
        from transports.api.cockpit_presence_routes import _command
        result = _run(_command(FakeReq(body={"text": "show active agents"})))
        assert result["ok"] is True
        assert result["intent"] == "agent_query"
        assert result["governance"] == "informational"
        assert result["panel_target"] == "agents"
        assert "agents" in result.get("data", {})

    def test_blocked_query_via_command(self) -> None:
        from transports.api.cockpit_presence_routes import _command
        result = _run(_command(FakeReq(body={"text": "what is blocked"})))
        assert result["ok"] is True
        assert result["intent"] == "blocked_query"
        assert result["governance"] == "informational"

    def test_packet_control_via_command(self) -> None:
        from transports.api.cockpit_presence_routes import _command
        result = _run(_command(FakeReq(body={"text": "pause this work packet"})))
        assert result["ok"] is True
        assert result["intent"] == "packet_control"
        assert result["governance"] == "requires_governance"
        assert result["data"]["action"] == "pause"

    def test_command_center_via_command(self) -> None:
        from transports.api.cockpit_presence_routes import _command
        result = _run(_command(FakeReq(body={"text": "command center"})))
        assert result["ok"] is True
        assert result["intent"] == "command_center_query"
        assert result["panel_target"] == "commandcenter"
        assert "agents" in result.get("data", {})

    def test_stop_packet_requires_governance(self) -> None:
        from transports.api.cockpit_presence_routes import _command
        result = _run(_command(FakeReq(body={"text": "stop this work packet"})))
        assert result["governance"] == "requires_governance"
        assert result["data"]["action"] == "stop"

    def test_resume_packet_requires_governance(self) -> None:
        from transports.api.cockpit_presence_routes import _command
        result = _run(_command(FakeReq(body={"text": "resume this work packet"})))
        assert result["governance"] == "requires_governance"
        assert result["data"]["action"] == "resume"

    def test_route_to_agent_requires_governance(self) -> None:
        from transports.api.cockpit_presence_routes import _command
        result = _run(_command(FakeReq(body={"text": "route this to the right agent"})))
        assert result["governance"] == "requires_governance"
        assert result["data"]["action"] == "route"

    def test_existing_14_11d_commands_still_work(self) -> None:
        from transports.api.cockpit_presence_routes import _command
        r1 = _run(_command(FakeReq(body={"text": "what is happening"})))
        assert r1["intent"] == "status_query"
        r2 = _run(_command(FakeReq(body={"text": "what needs approval"})))
        assert r2["intent"] == "approval_query"
        r3 = _run(_command(FakeReq(body={"text": "show dashboard"})))
        assert r3["intent"] == "cockpit_navigation"
