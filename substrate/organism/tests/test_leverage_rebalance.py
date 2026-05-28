"""Tests for continuous leverage rebalancing."""

from __future__ import annotations

import sys

sys.path.insert(0, "/opt/OS")

from substrate.organism.event_spine import EventDomain, EventSpine
from substrate.organism.leverage_assimilation import LeverageAssimilator


def test_rebalance_cycle():
    spine = EventSpine()
    assim = LeverageAssimilator(event_spine=spine)
    assim.ingest("Test Framework", content="pattern library for testing")
    assim.full_pipeline("Test Framework")

    result = assim.rebalance_cycle()
    assert isinstance(result, dict)
    assert "artifacts_evaluated" in result


def test_rebalance_emits_events():
    spine = EventSpine()
    assim = LeverageAssimilator(event_spine=spine)
    assim.ingest("Test", content="tool")
    assim.full_pipeline("Test")
    assim.rebalance_cycle()

    events = spine.recent(limit=50)
    rebalance_events = [e for e in events if e.event_type == "leverage_rebalanced"]
    assert len(rebalance_events) == 1
    assert rebalance_events[0].domain == EventDomain.LEVERAGE


def test_detect_degraded_primitives():
    spine = EventSpine()
    assim = LeverageAssimilator(event_spine=spine)
    assim.ingest("Flaky Tool", content="unreliable adapter")
    assim.full_pipeline("Flaky Tool")

    degraded = assim.detect_degraded()
    assert isinstance(degraded, list)


def test_works_without_spine():
    assim = LeverageAssimilator()
    assim.ingest("NoSpine", content="test")
    assim.full_pipeline("NoSpine")
    result = assim.rebalance_cycle()
    assert "artifacts_evaluated" in result
