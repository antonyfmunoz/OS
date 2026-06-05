"""Phase 14.11B — Continuity state machine tests.

Tests the unified continuity lifecycle:
- Valid transitions from every state
- Invalid transitions rejected
- Transition metadata preserved
- History tracking
- Serialization round-trip
- State machine invariants
"""

from __future__ import annotations

import sys
sys.path.insert(0, "/opt/OS")

import pytest

from substrate.workstation.continuity import (
    ContinuityState,
    ContinuityStateMachine,
    ContinuityTransition,
    _VALID_TRANSITIONS,
)


class TestContinuityStateEnum:
    def test_all_states_present(self) -> None:
        expected = {
            "active", "idle", "away", "remote",
            "night_sleeping", "extended_absence",
            "returning", "resume_brief",
        }
        actual = {s.value for s in ContinuityState}
        assert actual == expected

    def test_str_enum(self) -> None:
        assert ContinuityState.ACTIVE == "active"
        assert isinstance(ContinuityState.IDLE, str)


class TestTransitionMap:
    def test_every_state_has_transitions(self) -> None:
        for state in ContinuityState:
            assert state in _VALID_TRANSITIONS, f"{state} missing from transition map"

    def test_no_self_transitions(self) -> None:
        for state, targets in _VALID_TRANSITIONS.items():
            assert state not in targets, f"{state} allows self-transition"

    def test_active_can_reach_idle_away_remote_night_extended(self) -> None:
        allowed = _VALID_TRANSITIONS[ContinuityState.ACTIVE]
        assert ContinuityState.IDLE in allowed
        assert ContinuityState.AWAY in allowed
        assert ContinuityState.REMOTE in allowed
        assert ContinuityState.NIGHT_SLEEPING in allowed
        assert ContinuityState.EXTENDED_ABSENCE in allowed

    def test_night_can_only_return_or_extend(self) -> None:
        allowed = _VALID_TRANSITIONS[ContinuityState.NIGHT_SLEEPING]
        assert allowed == frozenset({
            ContinuityState.RETURNING,
            ContinuityState.EXTENDED_ABSENCE,
        })

    def test_resume_brief_leads_to_active_or_remote(self) -> None:
        allowed = _VALID_TRANSITIONS[ContinuityState.RESUME_BRIEF]
        assert allowed == frozenset({
            ContinuityState.ACTIVE,
            ContinuityState.REMOTE,
        })

    def test_extended_absence_can_only_return(self) -> None:
        allowed = _VALID_TRANSITIONS[ContinuityState.EXTENDED_ABSENCE]
        assert allowed == frozenset({ContinuityState.RETURNING})

    def test_returning_leads_to_brief_or_active(self) -> None:
        allowed = _VALID_TRANSITIONS[ContinuityState.RETURNING]
        assert allowed == frozenset({
            ContinuityState.RESUME_BRIEF,
            ContinuityState.ACTIVE,
        })


class TestContinuityStateMachine:
    def test_initial_state_default(self) -> None:
        sm = ContinuityStateMachine()
        assert sm.current_state == ContinuityState.ACTIVE

    def test_initial_state_custom(self) -> None:
        sm = ContinuityStateMachine(initial_state=ContinuityState.IDLE)
        assert sm.current_state == ContinuityState.IDLE

    def test_valid_transition(self) -> None:
        sm = ContinuityStateMachine()
        record = sm.transition(ContinuityState.IDLE, reason="no interaction for 15m")
        assert sm.current_state == ContinuityState.IDLE
        assert record.from_state == "active"
        assert record.to_state == "idle"
        assert record.reason == "no interaction for 15m"

    def test_invalid_transition_raises(self) -> None:
        sm = ContinuityStateMachine()
        with pytest.raises(ValueError, match="Invalid transition"):
            sm.transition(ContinuityState.RESUME_BRIEF)

    def test_can_transition(self) -> None:
        sm = ContinuityStateMachine()
        assert sm.can_transition(ContinuityState.IDLE) is True
        assert sm.can_transition(ContinuityState.RESUME_BRIEF) is False

    def test_valid_transitions_list(self) -> None:
        sm = ContinuityStateMachine()
        valid = sm.valid_transitions()
        assert ContinuityState.IDLE in valid
        assert ContinuityState.RESUME_BRIEF not in valid

    def test_history_tracking(self) -> None:
        sm = ContinuityStateMachine()
        sm.transition(ContinuityState.IDLE, reason="timeout")
        sm.transition(ContinuityState.AWAY, reason="left desk")
        assert len(sm.history) == 2
        assert sm.history[0].to_state == "idle"
        assert sm.history[1].to_state == "away"

    def test_last_transition(self) -> None:
        sm = ContinuityStateMachine()
        assert sm.last_transition() is None
        sm.transition(ContinuityState.IDLE)
        assert sm.last_transition() is not None
        assert sm.last_transition().to_state == "idle"

    def test_transition_metadata(self) -> None:
        sm = ContinuityStateMachine()
        record = sm.transition(
            ContinuityState.NIGHT_SLEEPING,
            reason="end of workday",
            active_node="vps-main",
            active_environment="linux",
            active_work_packet_id="wp_123",
            active_session_id="sess_456",
            pending_approvals_count=3,
            safe_work_constraints={"risk_ceiling": "LOW"},
        )
        assert record.active_node == "vps-main"
        assert record.active_environment == "linux"
        assert record.active_work_packet_id == "wp_123"
        assert record.active_session_id == "sess_456"
        assert record.pending_approvals_count == 3
        assert record.safe_work_constraints == {"risk_ceiling": "LOW"}

    def test_full_lifecycle_active_to_night_to_return_to_resume_to_active(self) -> None:
        sm = ContinuityStateMachine()
        sm.transition(ContinuityState.NIGHT_SLEEPING, reason="closing day")
        sm.transition(ContinuityState.RETURNING, reason="morning")
        sm.transition(ContinuityState.RESUME_BRIEF, reason="showing brief")
        sm.transition(ContinuityState.ACTIVE, reason="brief acknowledged")
        assert sm.current_state == ContinuityState.ACTIVE
        assert len(sm.history) == 4

    def test_idle_cannot_reach_remote(self) -> None:
        sm = ContinuityStateMachine(initial_state=ContinuityState.IDLE)
        with pytest.raises(ValueError):
            sm.transition(ContinuityState.REMOTE)

    def test_away_cannot_reach_active_directly(self) -> None:
        sm = ContinuityStateMachine(initial_state=ContinuityState.AWAY)
        with pytest.raises(ValueError):
            sm.transition(ContinuityState.ACTIVE)


class TestContinuityTransition:
    def test_auto_id(self) -> None:
        t = ContinuityTransition(from_state="active", to_state="idle")
        assert t.transition_id.startswith("ct_")

    def test_auto_timestamp(self) -> None:
        t = ContinuityTransition(from_state="active", to_state="idle")
        assert t.timestamp != ""

    def test_to_dict(self) -> None:
        t = ContinuityTransition(from_state="active", to_state="idle", reason="test")
        d = t.to_dict()
        assert d["from_state"] == "active"
        assert d["to_state"] == "idle"
        assert d["reason"] == "test"


class TestSerialization:
    def test_round_trip(self) -> None:
        sm = ContinuityStateMachine()
        sm.transition(ContinuityState.IDLE, reason="timeout")
        sm.transition(ContinuityState.AWAY, reason="left")

        data = sm.to_dict()
        restored = ContinuityStateMachine.from_dict(data)

        assert restored.current_state == ContinuityState.AWAY
        assert len(restored.history) == 2
        assert restored.history[0].to_state == "idle"

    def test_from_dict_invalid_state_defaults_active(self) -> None:
        restored = ContinuityStateMachine.from_dict({"current_state": "bogus"})
        assert restored.current_state == ContinuityState.ACTIVE

    def test_from_dict_empty(self) -> None:
        restored = ContinuityStateMachine.from_dict({})
        assert restored.current_state == ContinuityState.ACTIVE
        assert len(restored.history) == 0
