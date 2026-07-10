"""Phase 14.11G — Integrated workstation actionability tests."""

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


# ── Gap 1: Workspace panel target ──


class TestWorkspacePanelTarget:
    def test_work_packet_draft_has_panel_target(self) -> None:
        from transports.api.cockpit_presence_routes import _command
        result = _run(_command(FakeReq(body={"text": "create a task to fix auth"})))
        assert result["ok"] is True
        assert result["panel_target"] == "commandcenter"
        assert result["governance"] == "requires_governance"

    def test_command_center_query_has_panel_target(self) -> None:
        from transports.api.cockpit_presence_routes import _command
        result = _run(_command(FakeReq(body={"text": "command center"})))
        assert result["ok"] is True
        assert result["panel_target"] == "commandcenter"

    def test_nav_map_command_center(self) -> None:
        from substrate.workstation.command_router import _NAV_MAP
        assert _NAV_MAP["command center"] == "commandcenter"


# ── Gap 4: Checkpoint → summary ──


class TestCheckpointSummaryWiring:
    def test_summary_has_checkpoint_section(self) -> None:
        from transports.api.cockpit_command_center_routes import _summary
        result = _run(_summary(FakeReq()))
        assert result["ok"] is True
        assert "checkpoint" in result
        cp = result["checkpoint"]
        assert "last_checkpoint_id" in cp
        assert "continuity_state" in cp
        assert "lifecycle_mode" in cp
        assert "active_node" in cp
        assert "active_environment" in cp
        assert "open_loops" in cp
        assert "recommended_next_action" in cp

    def test_checkpoint_from_file(self) -> None:
        from substrate.workstation.checkpoint import CheckpointManager
        from substrate.workstation.continuity import ContinuityState
        cm = CheckpointManager()
        cm.create_checkpoint(
            previous_state="idle",
            new_state="active",
            active_node="test-node",
            active_environment="vps",
            transition_reason="14.11G test",
        )
        from transports.api.cockpit_command_center_routes import _summary
        result = _run(_summary(FakeReq()))
        cp = result["checkpoint"]
        assert cp["continuity_state"] in ("active", "idle")
        assert cp["active_node"] != "" or cp["active_environment"] != ""


# ── Gap 5: Live refresh ──


class TestLiveRefresh:
    def test_summary_polling_returns_consistent(self) -> None:
        from transports.api.cockpit_command_center_routes import _summary
        r1 = _run(_summary(FakeReq()))
        r2 = _run(_summary(FakeReq()))
        assert r1["ok"] and r2["ok"]
        assert r1["what_is_happening"]["total_agents"] == r2["what_is_happening"]["total_agents"]


# ── Gap 6: Approve / deny ──


class TestApproveAction:
    def test_approve_nonexistent(self) -> None:
        from transports.api.cockpit_command_center_routes import _approval_decide
        result = _run(_approval_decide(
            FakeReq(body={"decision": "approved"}),
            approval_id="nonexistent-id",
        ))
        assert result["ok"] is False
        assert "not found" in result["error"]

    def test_deny_nonexistent(self) -> None:
        from transports.api.cockpit_command_center_routes import _approval_decide
        result = _run(_approval_decide(
            FakeReq(body={"decision": "denied"}),
            approval_id="nonexistent-id",
        ))
        assert result["ok"] is False

    def test_invalid_decision(self) -> None:
        from transports.api.cockpit_command_center_routes import _approval_decide
        result = _run(_approval_decide(
            FakeReq(body={"decision": "maybe"}),
            approval_id="test-id",
        ))
        assert result["ok"] is False
        assert "must be" in result["error"]

    def test_approve_real_approval(self) -> None:
        from substrate.organism.approval_store import ApprovalStore
        store = ApprovalStore()
        record = store.create_approval(
            title="Test approval for 14.11G",
            description="Created by test",
            risk_level="low",
        )
        from transports.api.cockpit_command_center_routes import _approval_decide
        result = _run(_approval_decide(
            FakeReq(body={"decision": "approved", "decided_by": "test"}),
            approval_id=record["id"],
        ))
        assert result["ok"] is True
        assert result["approval"]["status"] == "approved"
        assert result["approval"]["decided_by"] == "test"

    def test_deny_real_approval(self) -> None:
        from substrate.organism.approval_store import ApprovalStore
        store = ApprovalStore()
        record = store.create_approval(
            title="Test deny for 14.11G",
            description="Created by test",
            risk_level="medium",
        )
        from transports.api.cockpit_command_center_routes import _approval_decide
        result = _run(_approval_decide(
            FakeReq(body={"decision": "denied", "decided_by": "test"}),
            approval_id=record["id"],
        ))
        assert result["ok"] is True
        assert result["approval"]["status"] == "denied"

    def test_approval_logged_to_journal(self) -> None:
        from substrate.organism.approval_store import ApprovalStore
        store = ApprovalStore()
        record = store.create_approval(
            title="Journal test",
            description="Verify journal logging",
            risk_level="low",
        )
        from transports.api.cockpit_command_center_routes import _approval_decide, _JOURNAL_PATH
        from transports.api.cockpit_command_center_routes import _load_journal_recent
        before = len(_load_journal_recent(limit=1000))
        _run(_approval_decide(
            FakeReq(body={"decision": "approved"}),
            approval_id=record["id"],
        ))
        after = len(_load_journal_recent(limit=1000))
        assert after > before


# ── Gap 7: Work packet create ──


class TestWorkPacketCreate:
    def test_create_requires_intent(self) -> None:
        from transports.api.cockpit_command_center_routes import _work_packet_create
        result = _run(_work_packet_create(FakeReq(body={})))
        assert result["ok"] is False
        assert "user_intent" in result["error"]

    def test_create_real_packet(self) -> None:
        from transports.api.cockpit_command_center_routes import _work_packet_create
        result = _run(_work_packet_create(FakeReq(body={
            "user_intent": "Fix the auth middleware timeout bug",
            "source_type": "voice_command",
        })))
        assert result["ok"] is True
        pkt = result["packet"]
        assert pkt["user_intent"] == "Fix the auth middleware timeout bug"
        assert "packet_id" in pkt
        assert pkt["status"] in ("drafted", "classified")
        assert "risk_class" in pkt

    def test_created_packet_appears_in_board(self) -> None:
        from transports.api.cockpit_command_center_routes import _work_packet_create
        from substrate.organism.work_packet import load_packets
        create_result = _run(_work_packet_create(FakeReq(body={
            "user_intent": "Add rate limiting to API endpoints",
        })))
        assert create_result["ok"]
        pkt_id = create_result["packet"]["packet_id"]
        all_packets = load_packets()
        all_ids = [p.packet_id for p in all_packets]
        assert pkt_id in all_ids

    def test_create_logged_to_journal(self) -> None:
        from transports.api.cockpit_command_center_routes import _work_packet_create, _load_journal_recent
        before = len(_load_journal_recent(limit=1000))
        _run(_work_packet_create(FakeReq(body={
            "user_intent": "Journal logging test packet",
        })))
        after = len(_load_journal_recent(limit=1000))
        assert after > before

    def test_create_has_environment_label(self) -> None:
        from transports.api.cockpit_command_center_routes import _work_packet_create
        result = _run(_work_packet_create(FakeReq(body={
            "user_intent": "Test env labeling",
        })))
        assert result["ok"]
        assert result["source_env"] in ("vps", "container", "macos", "windows", "unknown")


# ── E2E: Voice command → work packet ──


class TestCommandToWorkPacketE2E:
    def test_voice_command_creates_packet(self) -> None:
        from transports.api.cockpit_presence_routes import _command
        from transports.api.cockpit_command_center_routes import _work_packet_create
        from substrate.organism.work_packet import load_packets
        cmd = _run(_command(FakeReq(body={"text": "create a task to upgrade the database schema"})))
        assert cmd["intent"] == "work_packet_draft"
        assert cmd["governance"] == "requires_governance"
        draft_text = cmd["data"]["draft_text"]
        create = _run(_work_packet_create(FakeReq(body={
            "user_intent": draft_text,
            "source_type": "voice_command",
        })))
        assert create["ok"]
        all_packets = load_packets()
        ids = [p.packet_id for p in all_packets]
        assert create["packet"]["packet_id"] in ids


# ── Governance integrity ──


class TestGovernanceIntegrity:
    def test_approve_endpoint_uses_real_store(self) -> None:
        from transports.api.cockpit_command_center_routes import _approval_decide
        result = _run(_approval_decide(
            FakeReq(body={"decision": "approved"}),
            approval_id="fake-id-123",
        ))
        assert result["ok"] is False

    def test_create_packet_uses_real_engine(self) -> None:
        from transports.api.cockpit_command_center_routes import _work_packet_create
        result = _run(_work_packet_create(FakeReq(body={
            "user_intent": "governance test packet",
        })))
        assert result["ok"] is True
        assert result["packet"]["user_intent"] == "governance test packet"
