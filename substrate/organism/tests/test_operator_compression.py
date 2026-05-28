"""Tests for OperatorCompression engine."""
from __future__ import annotations

import sys

import os; sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from substrate.organism.operator_compression import (
    InterventionType,
    OperatorAction,
    OperatorCompression,
)


def test_empty_compression():
    oc = OperatorCompression()
    assert oc.compression_ratio() == 0.0
    assert len(oc.automation_candidates()) == 0


def test_autonomous_records():
    oc = OperatorCompression()
    oc.record_autonomous()
    oc.record_autonomous()
    assert oc.compression_ratio() == 1.0


def test_intervention_reduces_ratio():
    oc = OperatorCompression()
    oc.record_autonomous()
    oc.record_intervention(OperatorAction(
        action_id="a1",
        intervention_type=InterventionType.APPROVAL,
        description="Approved deployment",
        context="deploy",
    ))
    assert oc.compression_ratio() == 0.5


def test_automation_candidate_detection():
    oc = OperatorCompression(promotion_threshold=2)
    for i in range(3):
        oc.record_intervention(OperatorAction(
            action_id=f"a{i}",
            intervention_type=InterventionType.RESTART,
            description="Restarted os-discord",
            context="docker_restart",
            duration_seconds=30,
        ))
    candidates = oc.automation_candidates()
    assert len(candidates) == 1
    assert candidates[0].occurrence_count == 3
    assert candidates[0].total_operator_seconds == 90.0


def test_different_patterns_tracked():
    oc = OperatorCompression(promotion_threshold=2)
    for i in range(3):
        oc.record_intervention(OperatorAction(
            action_id=f"a{i}",
            intervention_type=InterventionType.RESTART,
            description="Restart",
            context="docker",
        ))
    for i in range(3):
        oc.record_intervention(OperatorAction(
            action_id=f"b{i}",
            intervention_type=InterventionType.APPROVAL,
            description="Approve",
            context="deploy",
        ))
    candidates = oc.automation_candidates()
    assert len(candidates) == 2


def test_compression_tick():
    oc = OperatorCompression(promotion_threshold=2)
    for i in range(3):
        oc.record_intervention(OperatorAction(
            action_id=f"a{i}",
            intervention_type=InterventionType.OVERRIDE,
            description="Override",
            context="risk",
        ))
    result = oc.compression_tick()
    assert result["automation_candidates"] == 1
    assert result["total_manual"] == 3


def test_to_dict():
    oc = OperatorCompression()
    oc.record_autonomous()
    d = oc.to_dict()
    assert d["total_autonomous"] == 1
    assert d["compression_ratio"] == 1.0


if __name__ == "__main__":
    test_empty_compression()
    test_autonomous_records()
    test_intervention_reduces_ratio()
    test_automation_candidate_detection()
    test_different_patterns_tracked()
    test_compression_tick()
    test_to_dict()
    print("ALL OPERATOR COMPRESSION TESTS PASSED")
