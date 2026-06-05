"""Phase 14.11A — PAUSED lifecycle state transition tests."""

from __future__ import annotations

import sys

sys.path.insert(0, "/opt/OS")

from substrate.organism.work_packet import (
    PacketLifecycleStatus,
    _VALID_TRANSITIONS,
)


class TestPausedStateExists:
    def test_paused_in_enum(self) -> None:
        assert hasattr(PacketLifecycleStatus, "PAUSED")
        assert PacketLifecycleStatus.PAUSED.value == "paused"

    def test_paused_in_transitions(self) -> None:
        assert PacketLifecycleStatus.PAUSED in _VALID_TRANSITIONS


class TestPausedAllowedTransitions:
    def test_executing_to_paused(self) -> None:
        allowed = _VALID_TRANSITIONS[PacketLifecycleStatus.EXECUTING]
        assert PacketLifecycleStatus.PAUSED in allowed

    def test_paused_to_executing(self) -> None:
        allowed = _VALID_TRANSITIONS[PacketLifecycleStatus.PAUSED]
        assert PacketLifecycleStatus.EXECUTING in allowed

    def test_paused_to_blocked(self) -> None:
        allowed = _VALID_TRANSITIONS[PacketLifecycleStatus.PAUSED]
        assert PacketLifecycleStatus.BLOCKED in allowed

    def test_paused_to_failed(self) -> None:
        allowed = _VALID_TRANSITIONS[PacketLifecycleStatus.PAUSED]
        assert PacketLifecycleStatus.FAILED in allowed

    def test_paused_to_archived(self) -> None:
        allowed = _VALID_TRANSITIONS[PacketLifecycleStatus.PAUSED]
        assert PacketLifecycleStatus.ARCHIVED in allowed


class TestPausedDisallowedTransitions:
    def test_paused_to_drafted_denied(self) -> None:
        allowed = _VALID_TRANSITIONS[PacketLifecycleStatus.PAUSED]
        assert PacketLifecycleStatus.DRAFTED not in allowed

    def test_paused_to_classified_denied(self) -> None:
        allowed = _VALID_TRANSITIONS[PacketLifecycleStatus.PAUSED]
        assert PacketLifecycleStatus.CLASSIFIED not in allowed

    def test_paused_to_completed_denied(self) -> None:
        allowed = _VALID_TRANSITIONS[PacketLifecycleStatus.PAUSED]
        assert PacketLifecycleStatus.COMPLETED not in allowed

    def test_paused_to_approved_denied(self) -> None:
        allowed = _VALID_TRANSITIONS[PacketLifecycleStatus.PAUSED]
        assert PacketLifecycleStatus.APPROVED not in allowed

    def test_paused_to_paused_denied(self) -> None:
        allowed = _VALID_TRANSITIONS[PacketLifecycleStatus.PAUSED]
        assert PacketLifecycleStatus.PAUSED not in allowed

    def test_drafted_to_paused_denied(self) -> None:
        allowed = _VALID_TRANSITIONS[PacketLifecycleStatus.DRAFTED]
        assert PacketLifecycleStatus.PAUSED not in allowed

    def test_blocked_to_paused_denied(self) -> None:
        allowed = _VALID_TRANSITIONS[PacketLifecycleStatus.BLOCKED]
        assert PacketLifecycleStatus.PAUSED not in allowed

    def test_completed_to_paused_denied(self) -> None:
        allowed = _VALID_TRANSITIONS[PacketLifecycleStatus.COMPLETED]
        assert PacketLifecycleStatus.PAUSED not in allowed


class TestPausedIsNotTerminal:
    def test_paused_not_terminal(self) -> None:
        from substrate.organism.work_packet import _TERMINAL_STATUSES
        assert PacketLifecycleStatus.PAUSED not in _TERMINAL_STATUSES


class TestAllStatesHaveTransitions:
    def test_every_status_in_transition_map(self) -> None:
        for status in PacketLifecycleStatus:
            assert status in _VALID_TRANSITIONS, f"{status} missing from _VALID_TRANSITIONS"
