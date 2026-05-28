"""Tests for EnvironmentReconciler — drift correction."""

from __future__ import annotations

import sys
import os

sys.path.insert(0, os.environ.get("UMH_ROOT", "/opt/OS"))

from substrate.organism.environment_reconciler import EnvironmentReconciler
from substrate.organism.event_spine import EventSpine
from substrate.organism.runtime_graph import (
    AvailabilityStatus,
    RuntimeCapability,
    RuntimeClass,
    RuntimeGraph,
)


def _simple_graph() -> RuntimeGraph:
    g = RuntimeGraph()
    g.register(
        "operator_api",
        RuntimeClass.PROCESS,
        frozenset({RuntimeCapability.SHELL}),
    )
    g.update_status("operator_api", AvailabilityStatus.AVAILABLE)
    return g


def test_reconcile_returns_report():
    g = _simple_graph()
    spine = EventSpine()
    r = EnvironmentReconciler(graph=g, spine=spine)

    report = r.reconcile()
    assert report.timestamp > 0
    assert report.elapsed_ms >= 0
    assert r.reconcile_count == 1


def test_reconcile_tick_returns_bool():
    g = _simple_graph()
    r = EnvironmentReconciler(graph=g)
    result = r.reconcile_tick()
    assert isinstance(result, bool)


def test_status_change_detection():
    g = RuntimeGraph()
    g.register("test_rt", RuntimeClass.PROCESS, frozenset())
    g.update_status("test_rt", AvailabilityStatus.AVAILABLE)

    class _MockAdapter:
        @property
        def runtime_id(self) -> str:
            return "test_rt"

        @property
        def runtime_class(self) -> RuntimeClass:
            return RuntimeClass.PROCESS

        @property
        def capabilities(self):
            return frozenset()

        def check_available(self) -> bool:
            return False

        def execute(self, prompt, **kwargs):
            return None

    node = g.get("test_rt")
    assert node is not None
    node.adapter = _MockAdapter()

    r = EnvironmentReconciler(graph=g)
    report = r.reconcile()

    has_change = any(sc["runtime_id"] == "test_rt" for sc in report.status_changes)
    assert has_change


def test_stale_dynamic_runtime_removed():
    g = RuntimeGraph()
    g.register("docker:dead-container", RuntimeClass.CONTAINER, frozenset())
    g.update_status("docker:dead-container", AvailabilityStatus.UNAVAILABLE)

    class _DeadAdapter:
        @property
        def runtime_id(self) -> str:
            return "docker:dead-container"

        @property
        def runtime_class(self) -> RuntimeClass:
            return RuntimeClass.CONTAINER

        @property
        def capabilities(self):
            return frozenset()

        def check_available(self) -> bool:
            return False

        def execute(self, prompt, **kwargs):
            return None

    node = g.get("docker:dead-container")
    assert node is not None
    node.adapter = _DeadAdapter()

    r = EnvironmentReconciler(graph=g)
    report = r.reconcile()

    assert "docker:dead-container" in report.removed
    assert g.get("docker:dead-container") is None


def test_to_dict():
    g = _simple_graph()
    r = EnvironmentReconciler(graph=g)
    r.reconcile()

    d = r.to_dict()
    assert d["reconcile_count"] == 1
    assert d["last_report"] is not None


def test_emits_events_on_changes():
    g = RuntimeGraph()
    g.register("docker:test", RuntimeClass.CONTAINER, frozenset())
    g.update_status("docker:test", AvailabilityStatus.UNAVAILABLE)

    class _DeadAdapter:
        @property
        def runtime_id(self) -> str:
            return "docker:test"

        @property
        def runtime_class(self) -> RuntimeClass:
            return RuntimeClass.CONTAINER

        @property
        def capabilities(self):
            return frozenset()

        def check_available(self) -> bool:
            return False

        def execute(self, prompt, **kwargs):
            return None

    node = g.get("docker:test")
    assert node is not None
    node.adapter = _DeadAdapter()

    spine = EventSpine()
    r = EnvironmentReconciler(graph=g, spine=spine)
    r.reconcile()

    events = spine.recent(limit=10)
    reconcile_events = [e for e in events if e.event_type == "environment_reconciled"]
    assert len(reconcile_events) == 1
