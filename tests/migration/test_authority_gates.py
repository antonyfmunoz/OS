"""Migration pin: authority gates — governance pre-execution check.

Pins §34 item 2: authority gates classify actions by risk and
enforce autonomy-level gates before execution.
"""

import os
import sys

import pytest

sys.path.insert(0, os.environ.get("UMH_ROOT") or "/opt/OS")

from runtime.authority_engine import (
    AUTONOMY_LEVEL_MAP,
    MIN_LEVEL_TO_EXECUTE,
    RISK_CLASSES,
    AuthorityEngine,
)

pytestmark = pytest.mark.migration


class TestRiskClassification:
    def test_critical_actions_classified(self):
        ae = _make_engine(autonomy=1)
        for action in RISK_CLASSES["CRITICAL"]:
            assert ae.classify_action(action) == "CRITICAL", f"{action} not CRITICAL"

    def test_high_actions_classified(self):
        ae = _make_engine(autonomy=1)
        for action in RISK_CLASSES["HIGH"]:
            assert ae.classify_action(action) == "HIGH", f"{action} not HIGH"

    def test_low_actions_classified(self):
        ae = _make_engine(autonomy=1)
        for action in RISK_CLASSES["LOW"]:
            assert ae.classify_action(action) == "LOW", f"{action} not LOW"

    def test_unknown_action_defaults_to_low(self):
        ae = _make_engine(autonomy=1)
        assert ae.classify_action("some_unknown_action") == "LOW"


class TestGovernanceGates:
    def test_critical_action_always_blocked(self):
        ae = _make_engine(autonomy=4)
        result = ae.check_can_execute("send_message")
        assert result["can_execute"] is False
        assert result["requires_approval"] is True
        assert result["risk_class"] == "CRITICAL"

    def test_high_action_requires_approval(self):
        ae = _make_engine(autonomy=3)
        result = ae.check_can_execute("send_dm")
        assert result["requires_approval"] is True
        assert result["risk_class"] == "HIGH"

    def test_low_action_at_minimum_autonomy_executes(self):
        ae = _make_engine(autonomy=0)
        result = ae.check_can_execute("analyze")
        assert result["can_execute"] is True
        assert result["requires_approval"] is False

    def test_medium_action_below_threshold_blocked(self):
        ae = _make_engine(autonomy=0)
        result = ae.check_can_execute("draft_message")
        assert result["can_execute"] is False

    def test_medium_action_at_threshold_executes(self):
        ae = _make_engine(autonomy=1)
        result = ae.check_can_execute("draft_message")
        assert result["can_execute"] is True

    def test_decision_includes_reason(self):
        ae = _make_engine(autonomy=1)
        result = ae.check_can_execute("send_email")
        assert "reason" in result
        assert len(result["reason"]) > 0

    def test_decision_includes_risk_class(self):
        ae = _make_engine(autonomy=1)
        result = ae.check_can_execute("analyze")
        assert "risk_class" in result
        assert result["risk_class"] == "LOW"


class TestAutonomyLevels:
    def test_manual_is_level_1(self):
        assert AUTONOMY_LEVEL_MAP["manual"] == 1

    def test_hybrid_is_level_3(self):
        assert AUTONOMY_LEVEL_MAP["hybrid"] == 3

    def test_autonomous_is_level_4(self):
        assert AUTONOMY_LEVEL_MAP["autonomous"] == 4

    def test_critical_min_level_unreachable(self):
        assert MIN_LEVEL_TO_EXECUTE["CRITICAL"] == 999


def _make_engine(autonomy: int) -> AuthorityEngine:
    """Build AuthorityEngine without DB by injecting autonomy level."""
    ae = AuthorityEngine.__new__(AuthorityEngine)
    ae._org_autonomy = autonomy
    return ae
