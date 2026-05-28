"""Tests for ExecutionModeManager."""
from __future__ import annotations

import sys

import os; sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from substrate.organism.execution_modes import (
    ExecutionMode,
    ExecutionModeManager,
    TransitionReason,
)


def test_initial_mode():
    emm = ExecutionModeManager()
    assert emm.current_mode == ExecutionMode.OBSERVE


def test_custom_initial_mode():
    emm = ExecutionModeManager(initial_mode=ExecutionMode.ASSISTED)
    assert emm.current_mode == ExecutionMode.ASSISTED


def test_can_execute():
    emm = ExecutionModeManager(initial_mode=ExecutionMode.ASSISTED)
    assert emm.can_execute(ExecutionMode.OBSERVE)
    assert emm.can_execute(ExecutionMode.RECOMMEND)
    assert emm.can_execute(ExecutionMode.ASSISTED)
    assert not emm.can_execute(ExecutionMode.AUTONOMOUS)


def test_promote():
    emm = ExecutionModeManager()
    assert emm.promote(ExecutionMode.RECOMMEND)
    assert emm.current_mode == ExecutionMode.RECOMMEND


def test_promote_no_downgrade():
    emm = ExecutionModeManager(initial_mode=ExecutionMode.ASSISTED)
    assert not emm.promote(ExecutionMode.OBSERVE)
    assert emm.current_mode == ExecutionMode.ASSISTED


def test_demote():
    emm = ExecutionModeManager(initial_mode=ExecutionMode.AUTONOMOUS)
    assert emm.demote(ExecutionMode.ASSISTED)
    assert emm.current_mode == ExecutionMode.ASSISTED


def test_propose_action_observe():
    emm = ExecutionModeManager()
    decision = emm.propose_action("t1", "read logs")
    assert not decision.approved


def test_propose_action_autonomous():
    emm = ExecutionModeManager(initial_mode=ExecutionMode.AUTONOMOUS)
    decision = emm.propose_action("t1", "restart container")
    assert decision.approved


def test_auto_demotion_on_failures():
    emm = ExecutionModeManager(initial_mode=ExecutionMode.ASSISTED)
    for _ in range(5):
        emm.record_outcome(f"t{_}", success=False)
    assert emm.current_mode.value in ("observe", "recommend")


def test_auto_promotion_on_success():
    emm = ExecutionModeManager(initial_mode=ExecutionMode.OBSERVE)
    for i in range(15):
        emm.record_outcome(f"t{i}", success=True)
    assert emm.current_mode != ExecutionMode.OBSERVE


def test_reliability():
    emm = ExecutionModeManager()
    emm.record_outcome("t1", success=True)
    emm.record_outcome("t2", success=True)
    emm.record_outcome("t3", success=False)
    assert abs(emm.reliability - 0.6667) < 0.01


def test_transition_history():
    emm = ExecutionModeManager()
    emm.promote(ExecutionMode.RECOMMEND)
    emm.promote(ExecutionMode.ASSISTED)
    history = emm.transition_history()
    assert len(history) == 2


def test_to_dict():
    emm = ExecutionModeManager()
    d = emm.to_dict()
    assert d["current_mode"] == "observe"
    assert "reliability" in d


if __name__ == "__main__":
    test_initial_mode()
    test_custom_initial_mode()
    test_can_execute()
    test_promote()
    test_promote_no_downgrade()
    test_demote()
    test_propose_action_observe()
    test_propose_action_autonomous()
    test_auto_demotion_on_failures()
    test_auto_promotion_on_success()
    test_reliability()
    test_transition_history()
    test_to_dict()
    print("ALL EXECUTION MODES TESTS PASSED")
