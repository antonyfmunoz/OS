"""Phase 14.11B — Mode switching + overnight scaffold tests.

Tests natural-language mode command parsing, overnight queue risk gating,
approval flow, and governance constraints.
"""

from __future__ import annotations

import sys
import tempfile

sys.path.insert(0, "/opt/OS")

import pytest

from substrate.workstation.mode_commands import ModeCommandResult, parse_mode_command
from substrate.workstation.overnight_queue import OvernightQueue, OvernightWorkItem


class TestModeCommandParsing:
    def test_switch_to_developer_mode(self) -> None:
        result = parse_mode_command("switch to Developer Mode")
        assert result.recognized is True
        assert result.command_type == "profile"
        assert result.target_value == "developer"

    def test_enter_research_mode(self) -> None:
        result = parse_mode_command("enter Research Mode")
        assert result.recognized is True
        assert result.command_type == "profile"
        assert result.target_value == "research"

    def test_start_night_cycle(self) -> None:
        result = parse_mode_command("start Night Cycle")
        assert result.recognized is True
        assert result.command_type == "lifecycle"
        assert result.target_value == "night_cycle"

    def test_mark_me_away(self) -> None:
        result = parse_mode_command("mark me away")
        assert result.recognized is True
        assert result.command_type == "continuity"
        assert result.target_value == "away"

    def test_im_back(self) -> None:
        result = parse_mode_command("I'm back")
        assert result.recognized is True
        assert result.command_type == "continuity"
        assert result.target_value == "returning"

    def test_start_end_of_workday(self) -> None:
        result = parse_mode_command("start end-of-workday")
        assert result.recognized is True
        assert result.command_type == "lifecycle"
        assert result.target_value == "end_of_workday"

    def test_start_overnight_mode(self) -> None:
        result = parse_mode_command("start overnight mode")
        assert result.recognized is True
        assert result.command_type == "lifecycle"
        assert result.target_value == "overnight"

    def test_good_night(self) -> None:
        result = parse_mode_command("good night")
        assert result.recognized is True
        assert result.command_type == "continuity"
        assert result.target_value == "night_sleeping"

    def test_unrecognized_command(self) -> None:
        result = parse_mode_command("make me a sandwich")
        assert result.recognized is False

    def test_empty_input(self) -> None:
        result = parse_mode_command("")
        assert result.recognized is False

    def test_command_center(self) -> None:
        result = parse_mode_command("switch to command center")
        assert result.recognized is True
        assert result.command_type == "profile"
        assert result.target_value == "command_center"

    def test_going_remote(self) -> None:
        result = parse_mode_command("working remotely")
        assert result.recognized is True
        assert result.command_type == "continuity"
        assert result.target_value == "remote"

    def test_music_mode(self) -> None:
        result = parse_mode_command("enter music mode")
        assert result.recognized is True
        assert result.command_type == "profile"
        assert result.target_value == "music"

    def test_finance_mode(self) -> None:
        result = parse_mode_command("start finance mode")
        assert result.recognized is True
        assert result.command_type == "profile"
        assert result.target_value == "finance"

    def test_learning_mode(self) -> None:
        result = parse_mode_command("switch to learning mode")
        assert result.recognized is True
        assert result.command_type == "profile"
        assert result.target_value == "learning"

    def test_result_to_dict(self) -> None:
        result = parse_mode_command("mark me away")
        d = result.to_dict()
        assert d["recognized"] is True
        assert d["command_type"] == "continuity"
        assert d["confidence"] == "high"


class TestOvernightWorkItem:
    def test_auto_id(self) -> None:
        item = OvernightWorkItem(title="test")
        assert item.item_id.startswith("owi_")

    def test_auto_timestamp(self) -> None:
        item = OvernightWorkItem()
        assert item.queued_at != ""

    def test_to_dict(self) -> None:
        item = OvernightWorkItem(title="test", risk_level="LOW", status="queued")
        d = item.to_dict()
        assert d["title"] == "test"
        assert d["risk_level"] == "LOW"


class TestOvernightQueue:
    def test_low_risk_queued(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            q = OvernightQueue(state_dir=tmpdir)
            item = q.queue_work("wp1", "run tests", "LOW")
            assert item.status == "queued"
            assert item.approval_required is False

    def test_medium_risk_needs_approval(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            q = OvernightQueue(state_dir=tmpdir)
            item = q.queue_work("wp2", "deploy staging", "MEDIUM")
            assert item.status == "queued"
            assert item.approval_required is True
            assert item.approval_id.startswith("appr_")

    def test_high_risk_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            q = OvernightQueue(state_dir=tmpdir)
            item = q.queue_work("wp3", "drop table", "HIGH")
            assert item.status == "blocked"
            assert item.approval_required is True

    def test_critical_risk_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            q = OvernightQueue(state_dir=tmpdir)
            item = q.queue_work("wp4", "schema migration", "CRITICAL")
            assert item.status == "blocked"

    def test_get_safe_work(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            q = OvernightQueue(state_dir=tmpdir)
            q.queue_work("wp1", "low1", "LOW")
            q.queue_work("wp2", "med1", "MEDIUM")
            q.queue_work("wp3", "low2", "LOW")

            safe = q.get_safe_work()
            assert len(safe) == 2
            assert all(not i.approval_required for i in safe)

    def test_get_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            q = OvernightQueue(state_dir=tmpdir)
            q.queue_work("wp1", "low", "LOW")
            q.queue_work("wp2", "high", "HIGH")
            blocked = q.get_blocked()
            assert len(blocked) == 1
            assert blocked[0].risk_level == "HIGH"

    def test_approve(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            q = OvernightQueue(state_dir=tmpdir)
            item = q.queue_work("wp1", "staging deploy", "MEDIUM")
            assert item.approval_required is True

            approved = q.approve(item.item_id)
            assert approved is not None
            assert approved.approval_required is False

    def test_approve_nonexistent(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            q = OvernightQueue(state_dir=tmpdir)
            assert q.approve("bogus_id") is None

    def test_morning_summary(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            q = OvernightQueue(state_dir=tmpdir)
            q.queue_work("wp1", "safe", "LOW")
            q.queue_work("wp2", "needs approval", "MEDIUM")
            q.queue_work("wp3", "blocked", "HIGH")

            summary = q.morning_summary()
            assert summary["total"] == 3
            assert summary["safe_to_run"] == 1
            assert summary["pending_approval"] == 1
            assert summary["blocked"] == 1

    def test_persistence_reload(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            q1 = OvernightQueue(state_dir=tmpdir)
            q1.queue_work("wp1", "task1", "LOW")
            q1.queue_work("wp2", "task2", "HIGH")

            q2 = OvernightQueue(state_dir=tmpdir)
            assert len(q2.get_queue()) == 2

    def test_clear(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            q = OvernightQueue(state_dir=tmpdir)
            q.queue_work("wp1", "task", "LOW")
            q.clear()
            assert len(q.get_queue()) == 0

    def test_governance_risky_overnight_requires_approval(self) -> None:
        """Governance test: risky mode/overnight action requires approval or pauses."""
        with tempfile.TemporaryDirectory() as tmpdir:
            q = OvernightQueue(state_dir=tmpdir)
            medium = q.queue_work("wp-med", "deploy", "MEDIUM")
            high = q.queue_work("wp-high", "migrate", "HIGH")
            critical = q.queue_work("wp-crit", "drop", "CRITICAL")

            assert medium.approval_required is True
            assert high.status == "blocked"
            assert critical.status == "blocked"

            safe = q.get_safe_work()
            assert len(safe) == 0
