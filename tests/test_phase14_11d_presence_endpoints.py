"""Phase 14.11D — Presence endpoint tests."""

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
    """Minimal request mock for endpoint testing."""

    def __init__(self, body: dict | None = None, query: dict | None = None):
        self._body = body or {}
        self.query_params = query or {}

    async def json(self):
        return self._body


class TestActivateEndpoint:
    def test_activate_returns_session(self) -> None:
        from transports.api.cockpit_presence_routes import _activate
        req = FakeReq(body={"source": "manual_cockpit_open"})
        result = _run(_activate(req))
        assert result["ok"] is True
        assert "session" in result
        session = result["session"]
        assert session["session_id"].startswith("ps_")
        assert session["activation"]["source"] == "manual_cockpit_open"

    def test_activate_loads_profile(self) -> None:
        from transports.api.cockpit_presence_routes import _activate
        req = FakeReq(body={"source": "hotkey", "user_id": "test_user"})
        result = _run(_activate(req))
        session = result["session"]
        assert session["profile"]["hostname"] != ""
        assert session["profile"]["platform"] != ""

    def test_activate_loads_continuity(self) -> None:
        from transports.api.cockpit_presence_routes import _activate
        req = FakeReq(body={"source": "typed_command"})
        result = _run(_activate(req))
        session = result["session"]
        assert session["continuity_state"] != ""

    def test_activate_loads_capabilities(self) -> None:
        from transports.api.cockpit_presence_routes import _activate
        req = FakeReq(body={"source": "manual_cockpit_open"})
        result = _run(_activate(req))
        session = result["session"]
        assert len(session["capabilities"]) == 8

    def test_activate_default_source(self) -> None:
        from transports.api.cockpit_presence_routes import _activate
        req = FakeReq(body={})
        result = _run(_activate(req))
        session = result["session"]
        assert session["activation"]["source"] == "manual_cockpit_open"


class TestCurrentEndpoint:
    def test_current_returns_state(self) -> None:
        from transports.api.cockpit_presence_routes import _current
        req = FakeReq(query={})
        result = _run(_current(req))
        assert result["ok"] is True
        assert result["continuity_state"] != ""
        assert result["active_node"] != ""
        assert result["source_env"] != ""

    def test_current_includes_capabilities(self) -> None:
        from transports.api.cockpit_presence_routes import _current
        req = FakeReq(query={})
        result = _run(_current(req))
        assert len(result["capabilities"]) == 8

    def test_current_includes_profile(self) -> None:
        from transports.api.cockpit_presence_routes import _current
        req = FakeReq(query={})
        result = _run(_current(req))
        assert "profile" in result
        assert result["profile"]["hostname"] != ""


class TestCapabilitiesEndpoint:
    def test_capabilities_returns_summary(self) -> None:
        from transports.api.cockpit_presence_routes import _capabilities
        req = FakeReq(query={})
        result = _run(_capabilities(req))
        assert result["ok"] is True
        assert result["summary"]["total"] == 8
        assert "stt_available" in result
        assert "tts_available" in result

    def test_capabilities_wake_word_not_implemented(self) -> None:
        from transports.api.cockpit_presence_routes import _capabilities
        req = FakeReq(query={})
        result = _run(_capabilities(req))
        caps = result["capabilities"]
        wake = next(c for c in caps if "wake" in c["name"].lower())
        assert wake["status"] == "not_implemented"

    def test_capabilities_clap_not_implemented(self) -> None:
        from transports.api.cockpit_presence_routes import _capabilities
        req = FakeReq(query={})
        result = _run(_capabilities(req))
        caps = result["capabilities"]
        clap = next(c for c in caps if "clap" in c["name"].lower())
        assert clap["status"] == "not_implemented"


class TestCommandEndpoint:
    def test_status_query(self) -> None:
        from transports.api.cockpit_presence_routes import _command
        req = FakeReq(body={"text": "what is happening?", "source": "typed_command"})
        result = _run(_command(req))
        assert result["ok"] is True
        assert result["intent"] == "status_query"
        assert result["governance"] == "informational"
        assert result["response_text"] != ""

    def test_resume_query(self) -> None:
        from transports.api.cockpit_presence_routes import _command
        req = FakeReq(body={"text": "what happened while i was gone?"})
        result = _run(_command(req))
        assert result["ok"] is True
        assert result["intent"] == "resume_query"
        assert result["governance"] == "informational"

    def test_approval_query(self) -> None:
        from transports.api.cockpit_presence_routes import _command
        req = FakeReq(body={"text": "what needs approval?"})
        result = _run(_command(req))
        assert result["ok"] is True
        assert result["intent"] == "approval_query"
        assert result["panel_target"] == "approvals"

    def test_mode_switch(self) -> None:
        from transports.api.cockpit_presence_routes import _command
        req = FakeReq(body={"text": "switch to developer mode"})
        result = _run(_command(req))
        assert result["ok"] is True
        assert result["intent"] == "mode_switch"
        assert result["mode_target"] == "developer"

    def test_navigation(self) -> None:
        from transports.api.cockpit_presence_routes import _command
        req = FakeReq(body={"text": "show workspace"})
        result = _run(_command(req))
        assert result["ok"] is True
        assert result["intent"] == "cockpit_navigation"
        assert result["panel_target"] == "workspace"

    def test_work_packet_draft_requires_governance(self) -> None:
        from transports.api.cockpit_presence_routes import _command
        req = FakeReq(body={"text": "prepare the next safe step"})
        result = _run(_command(req))
        assert result["ok"] is True
        assert result["intent"] == "work_packet_draft"
        assert result["governance"] == "requires_governance"

    def test_empty_command_rejected(self) -> None:
        from transports.api.cockpit_presence_routes import _command
        req = FakeReq(body={"text": ""})
        result = _run(_command(req))
        assert result["ok"] is False
        assert "empty" in result["error"].lower()

    def test_unknown_command(self) -> None:
        from transports.api.cockpit_presence_routes import _command
        req = FakeReq(body={"text": "xyzzy foobar baz"})
        result = _run(_command(req))
        assert result["ok"] is True
        assert result["intent"] == "unknown"

    def test_command_has_id(self) -> None:
        from transports.api.cockpit_presence_routes import _command
        req = FakeReq(body={"text": "sitrep"})
        result = _run(_command(req))
        assert result["command_id"].startswith("jcmd_")

    def test_command_has_timestamp(self) -> None:
        from transports.api.cockpit_presence_routes import _command
        req = FakeReq(body={"text": "sitrep"})
        result = _run(_command(req))
        assert result["timestamp"] != ""


class TestDetectEnv:
    def test_returns_string(self) -> None:
        from transports.api.cockpit_presence_routes import _detect_env
        env = _detect_env()
        assert isinstance(env, str)
        assert env != ""
