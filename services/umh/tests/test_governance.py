"""Tests for governance engine — PolicyEngine risk evaluation.

Adapted from umh_mvp/tests/test_governance.py. Rewritten against
services/umh/governance/policy_engine.PolicyEngine which uses
RiskClass (8-class domain enum) + GovernanceRequest/GovernanceVerdict.
"""

import sys
from pathlib import Path
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from services.umh.governance.policy_engine import PolicyEngine
from services.umh.governance.risk_classes import RiskClass
from services.umh.protocols.governance import (
    GovernanceDecision,
    GovernanceRequest,
    GovernanceVerdict,
    RiskLevel,
)


def _make_request(risk_class: RiskClass = RiskClass.READ_ONLY) -> GovernanceRequest:
    return GovernanceRequest(
        decomposition_id=uuid4(),
        component_id=uuid4(),
        proposed_action="test action",
        risk_level=risk_class.to_risk_level(),
    )


def test_read_only_auto_approved():
    engine = PolicyEngine(safe_roots=["/opt/OS"])
    verdict = engine.evaluate(RiskClass.READ_ONLY, _make_request(RiskClass.READ_ONLY))
    assert verdict.is_executable()
    assert verdict.decision == GovernanceDecision.APPROVE


def test_safe_write_inside_root_approved():
    engine = PolicyEngine(safe_roots=["/opt/OS"])
    verdict = engine.evaluate(
        RiskClass.SAFE_WRITE,
        _make_request(RiskClass.SAFE_WRITE),
        context={"target_path": "/opt/OS/data/test.json"},
    )
    assert verdict.is_executable()
    assert verdict.decision == GovernanceDecision.APPROVE


def test_safe_write_outside_root_deferred():
    engine = PolicyEngine(safe_roots=["/opt/OS"])
    verdict = engine.evaluate(
        RiskClass.SAFE_WRITE,
        _make_request(RiskClass.SAFE_WRITE),
        context={"target_path": "/tmp/outside.json"},
    )
    assert not verdict.is_executable()
    assert verdict.decision == GovernanceDecision.DEFER


def test_irreversible_write_denied():
    engine = PolicyEngine()
    verdict = engine.evaluate(
        RiskClass.IRREVERSIBLE_WRITE,
        _make_request(RiskClass.IRREVERSIBLE_WRITE),
    )
    assert not verdict.is_executable()
    assert verdict.decision == GovernanceDecision.DENY


def test_financial_denied():
    engine = PolicyEngine()
    verdict = engine.evaluate(
        RiskClass.FINANCIAL,
        _make_request(RiskClass.FINANCIAL),
    )
    assert not verdict.is_executable()
    assert verdict.decision == GovernanceDecision.DENY


def test_security_sensitive_escalated():
    engine = PolicyEngine()
    verdict = engine.evaluate(
        RiskClass.SECURITY_SENSITIVE,
        _make_request(RiskClass.SECURITY_SENSITIVE),
    )
    assert not verdict.is_executable()
    assert verdict.decision == GovernanceDecision.ESCALATE


def test_physical_world_escalated():
    engine = PolicyEngine()
    verdict = engine.evaluate(
        RiskClass.PHYSICAL_WORLD,
        _make_request(RiskClass.PHYSICAL_WORLD),
    )
    assert not verdict.is_executable()
    assert verdict.decision == GovernanceDecision.ESCALATE


if __name__ == "__main__":
    for name, func in sorted(globals().items()):
        if name.startswith("test_") and callable(func):
            try:
                func()
                print(f"  PASS  {name}")
            except AssertionError as e:
                print(f"  FAIL  {name}: {e}")
            except Exception as e:
                print(f"  ERROR {name}: {e}")
