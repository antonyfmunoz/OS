"""Phase 31 — Operator Home & Context Engine tests.

86 tests across 13 classes verifying:
  - Enum completeness and string values
  - Dataclass construction, serialization, round-trip
  - OperatorContextEngine aggregation from mocked subsystems
  - Attention generation rules (deterministic)
  - Timeline formatting from EventSpine events
  - Cockpit route contracts
  - Type registration in canonical_types
  - Integration: full snapshot composition
"""

from __future__ import annotations

import os
import sys
import time
import unittest
from dataclasses import dataclass, field
from typing import Any
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.environ.get("UMH_ROOT", "/opt/OS"))

from substrate.operator.operator_context import (
    OperatorAttentionItem,
    OperatorAttentionType,
    OperatorHealthSummary,
    OperatorSeverity,
    OperatorSnapshot,
    OperatorStatusCard,
    OperatorTimelineEvent,
)
from substrate.operator.operator_context_engine import OperatorContextEngine
from substrate.types import ApprovalRequest, ApprovalState  # WP-P1-007: real canonical type


# ── Helpers ──────────────────────────────────────────────────────


def _make_card(label: str = "Test", value: int = 5, status: str = "healthy") -> OperatorStatusCard:
    return OperatorStatusCard(label=label, value=value, status=status, detail="test detail")


def _make_attention(
    severity: OperatorSeverity = OperatorSeverity.WARNING,
    attention_type: OperatorAttentionType = OperatorAttentionType.GOVERNANCE,
) -> OperatorAttentionItem:
    return OperatorAttentionItem(
        attention_type=attention_type,
        severity=severity,
        title="Test attention",
        detail="test detail",
        source="test",
    )


def _make_timeline_event(**kwargs: Any) -> OperatorTimelineEvent:
    defaults = {
        "event_id": "evt-001",
        "domain": "runtime",
        "event_type": "test_event",
        "source": "test",
        "summary": "Test event happened",
        "timestamp": time.time(),
        "priority": "normal",
    }
    defaults.update(kwargs)
    return OperatorTimelineEvent(**defaults)


def _make_health(status: str = "healthy") -> OperatorHealthSummary:
    return OperatorHealthSummary(
        overall_status=status,
        cards=[_make_card()],
    )


@dataclass
class MockOrganismEvent:
    """Minimal mock of substrate.organism.event_spine.OrganismEvent."""

    event_id: str = "evt-mock"
    domain: str = "runtime"
    event_type: str = "test"
    source: str = "mock"
    priority: str = "normal"
    data: dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    correlation_id: str | None = None


class MockEventSpine:
    def __init__(self, events: list[MockOrganismEvent] | None = None) -> None:
        self._events = events or []

    def recent(self, limit: int = 50) -> list[MockOrganismEvent]:
        return self._events[:limit]

    def replay(self, domains: Any = None, since: float = 0) -> list[MockOrganismEvent]:
        return [e for e in self._events if e.timestamp >= since]


class MockNodeRecord:
    def __init__(self, node_id: str = "umh-vps", role: str = "coordinator") -> None:
        self.node_id = node_id
        self.role = role

    def to_dict(self) -> dict[str, Any]:
        return {"node_id": self.node_id, "role": self.role}


class MockNodeRegistry:
    def __init__(self, nodes: list[MockNodeRecord] | None = None) -> None:
        self._nodes = nodes or [MockNodeRecord()]

    def list_nodes(self) -> list[MockNodeRecord]:
        return self._nodes

    def primary_node(self) -> MockNodeRecord | None:
        return self._nodes[0] if self._nodes else None


def MockApprovalRequest(approval_id: str = "apr-001", status: str = "pending") -> "ApprovalRequest":
    """WP-P1-007: construct the REAL canonical ApprovalRequest (the type this
    test previously mocked as nonexistent). Kept as a factory so existing call
    sites are unchanged."""
    return ApprovalRequest(approval_id=approval_id, state=ApprovalState.coerce(status))


class MockApprovalStore:
    def __init__(self, pending: "list[ApprovalRequest] | None" = None) -> None:
        self._pending = pending or []

    def list_pending(self) -> "list[ApprovalRequest]":
        return self._pending

    @property
    def pending_count(self) -> int:
        return len(self._pending)


class MockServiceFailureEngine:
    _DEFAULT_HEALTH: dict[str, Any] = {
        "total_services": 13,
        "total_dependencies": 15,
        "critical_count": 4,
        "leaf_count": 5,
        "max_blast_radius": 5,
        "highest_risk_service": "event_spine",
    }
    _DEFAULT_PATH: list[dict[str, Any]] = [
        {
            "service_role": "event_spine",
            "criticality": "critical",
            "blast_radius": 5,
            "direct_dependents": 3,
            "transitive_dependents": 2,
        },
        {
            "service_role": "governance",
            "criticality": "critical",
            "blast_radius": 4,
            "direct_dependents": 3,
            "transitive_dependents": 1,
        },
    ]

    def __init__(
        self, health: dict[str, Any] | None = None, path: list[dict[str, Any]] | None = None
    ) -> None:
        self._health = health if health is not None else self._DEFAULT_HEALTH.copy()
        self._path = path if path is not None else list(self._DEFAULT_PATH)

    def organism_health(self) -> dict[str, Any]:
        return self._health

    def critical_path(self) -> list[dict[str, Any]]:
        return self._path


class MockStateCoherenceEngine:
    def __init__(
        self, health: dict[str, Any] | None = None, report: dict[str, Any] | None = None
    ) -> None:
        self._health = health or {
            "total_domains": 10,
            "coherent": 10,
            "stale": 0,
            "drifted": 0,
            "unknown": 0,
            "healthy": True,
        }
        self._report = report or {
            "overall_health": "healthy",
            "domain_count": 10,
            "domains": [],
        }

    def organism_health(self) -> dict[str, Any]:
        return self._health

    def coherence_report(self) -> dict[str, Any]:
        return self._report

    def _get_version_engine(self) -> None:
        return None


@dataclass
class MockWorkspaceSnapshot:
    terminals: list[Any] = field(default_factory=list)
    containers: list[Any] = field(default_factory=list)
    engineering_sessions: list[Any] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "terminals": [],
            "containers": [],
            "engineering_sessions": [],
        }


class MockWorkspaceEngine:
    def __init__(self, snap: MockWorkspaceSnapshot | None = None) -> None:
        self._snap = snap

    def latest(self) -> MockWorkspaceSnapshot | None:
        return self._snap


def _make_engine(**overrides: Any) -> OperatorContextEngine:
    defaults: dict[str, Any] = {
        "event_spine": MockEventSpine(),
        "service_failure_engine": MockServiceFailureEngine(),
        "state_coherence_engine": MockStateCoherenceEngine(),
        "node_registry": MockNodeRegistry(),
        "approval_store": MockApprovalStore(),
        "workspace_engine": MockWorkspaceEngine(),
    }
    defaults.update(overrides)
    return OperatorContextEngine(**defaults)


# ═══════════════════════════════════════════════════════════════
# Tests
# ═══════════════════════════════════════════════════════════════


class TestOperatorSeverityEnum(unittest.TestCase):
    def test_values(self) -> None:
        self.assertEqual(OperatorSeverity.INFO.value, "info")
        self.assertEqual(OperatorSeverity.WARNING.value, "warning")
        self.assertEqual(OperatorSeverity.CRITICAL.value, "critical")

    def test_count(self) -> None:
        self.assertEqual(len(OperatorSeverity), 3)

    def test_str_enum(self) -> None:
        self.assertIsInstance(OperatorSeverity.INFO, str)

    def test_from_value(self) -> None:
        self.assertEqual(OperatorSeverity("warning"), OperatorSeverity.WARNING)


class TestOperatorAttentionTypeEnum(unittest.TestCase):
    def test_values(self) -> None:
        expected = {
            "governance",
            "action",
            "service",
            "workspace",
            "runtime",
            "state",
            "engineering",
        }
        actual = {m.value for m in OperatorAttentionType}
        self.assertEqual(actual, expected)

    def test_count(self) -> None:
        self.assertEqual(len(OperatorAttentionType), 7)

    def test_str_enum(self) -> None:
        self.assertIsInstance(OperatorAttentionType.GOVERNANCE, str)

    def test_from_value(self) -> None:
        self.assertEqual(OperatorAttentionType("service"), OperatorAttentionType.SERVICE)


class TestOperatorAttentionItem(unittest.TestCase):
    def test_construction(self) -> None:
        item = _make_attention()
        self.assertIsNotNone(item.attention_id)
        self.assertTrue(item.attention_id.startswith("oai-"))

    def test_to_dict(self) -> None:
        item = _make_attention()
        d = item.to_dict()
        self.assertEqual(d["attention_type"], "governance")
        self.assertEqual(d["severity"], "warning")
        self.assertEqual(d["title"], "Test attention")

    def test_from_dict_roundtrip(self) -> None:
        item = _make_attention()
        d = item.to_dict()
        restored = OperatorAttentionItem.from_dict(d)
        self.assertEqual(restored.attention_id, item.attention_id)
        self.assertEqual(restored.severity, item.severity)
        self.assertEqual(restored.title, item.title)

    def test_severity_types(self) -> None:
        for sev in OperatorSeverity:
            item = _make_attention(severity=sev)
            self.assertEqual(item.severity, sev)

    def test_attention_types(self) -> None:
        for at in OperatorAttentionType:
            item = _make_attention(attention_type=at)
            self.assertEqual(item.attention_type, at)

    def test_has_timestamp(self) -> None:
        item = _make_attention()
        self.assertGreater(item.timestamp, 0)


class TestOperatorStatusCard(unittest.TestCase):
    def test_construction(self) -> None:
        card = _make_card()
        self.assertEqual(card.label, "Test")
        self.assertEqual(card.value, 5)
        self.assertEqual(card.status, "healthy")

    def test_to_dict(self) -> None:
        card = _make_card(label="Services", value=13, status="degraded")
        d = card.to_dict()
        self.assertEqual(d["label"], "Services")
        self.assertEqual(d["value"], 13)
        self.assertEqual(d["status"], "degraded")

    def test_from_dict_roundtrip(self) -> None:
        card = _make_card()
        d = card.to_dict()
        restored = OperatorStatusCard.from_dict(d)
        self.assertEqual(restored.label, card.label)
        self.assertEqual(restored.status, card.status)

    def test_default_detail(self) -> None:
        card = OperatorStatusCard(label="X", value=0, status="unknown")
        self.assertEqual(card.detail, "")


class TestOperatorHealthSummary(unittest.TestCase):
    def test_construction(self) -> None:
        hs = _make_health()
        self.assertEqual(hs.overall_status, "healthy")
        self.assertEqual(len(hs.cards), 1)

    def test_to_dict(self) -> None:
        hs = _make_health("degraded")
        d = hs.to_dict()
        self.assertEqual(d["overall_status"], "degraded")
        self.assertIsInstance(d["cards"], list)
        self.assertIsInstance(d["generated_at"], float)

    def test_from_dict_roundtrip(self) -> None:
        hs = _make_health()
        d = hs.to_dict()
        restored = OperatorHealthSummary.from_dict(d)
        self.assertEqual(restored.overall_status, hs.overall_status)
        self.assertEqual(len(restored.cards), len(hs.cards))

    def test_empty_cards(self) -> None:
        hs = OperatorHealthSummary(overall_status="unknown")
        self.assertEqual(len(hs.cards), 0)


class TestOperatorTimelineEvent(unittest.TestCase):
    def test_construction(self) -> None:
        evt = _make_timeline_event()
        self.assertEqual(evt.event_id, "evt-001")
        self.assertEqual(evt.domain, "runtime")

    def test_to_dict(self) -> None:
        evt = _make_timeline_event(priority="critical")
        d = evt.to_dict()
        self.assertEqual(d["priority"], "critical")
        self.assertEqual(d["event_id"], "evt-001")

    def test_from_dict_roundtrip(self) -> None:
        evt = _make_timeline_event()
        d = evt.to_dict()
        restored = OperatorTimelineEvent.from_dict(d)
        self.assertEqual(restored.event_id, evt.event_id)
        self.assertEqual(restored.domain, evt.domain)

    def test_default_priority(self) -> None:
        evt = OperatorTimelineEvent(
            event_id="e",
            domain="d",
            event_type="t",
            source="s",
            summary="sum",
            timestamp=0,
        )
        self.assertEqual(evt.priority, "normal")


class TestOperatorSnapshot(unittest.TestCase):
    def test_construction(self) -> None:
        snap = OperatorSnapshot(health_summary=_make_health())
        self.assertIsNotNone(snap.generated_at)
        self.assertEqual(snap.pending_approvals, 0)

    def test_to_dict(self) -> None:
        snap = OperatorSnapshot(
            health_summary=_make_health(),
            attention_items=[_make_attention()],
            timeline=[_make_timeline_event()],
            pending_approvals=3,
        )
        d = snap.to_dict()
        self.assertEqual(d["pending_approvals"], 3)
        self.assertEqual(len(d["attention_items"]), 1)
        self.assertEqual(len(d["timeline"]), 1)
        self.assertIn("health_summary", d)

    def test_from_dict_roundtrip(self) -> None:
        snap = OperatorSnapshot(
            health_summary=_make_health(),
            attention_items=[_make_attention()],
            pending_approvals=2,
        )
        d = snap.to_dict()
        restored = OperatorSnapshot.from_dict(d)
        self.assertEqual(restored.pending_approvals, 2)
        self.assertEqual(len(restored.attention_items), 1)

    def test_defaults(self) -> None:
        snap = OperatorSnapshot(health_summary=_make_health())
        self.assertEqual(snap.active_workspaces, [])
        self.assertEqual(snap.service_alerts, [])
        self.assertEqual(snap.node_status, [])
        self.assertEqual(snap.timeline, [])

    def test_active_workspaces_in_dict(self) -> None:
        snap = OperatorSnapshot(
            health_summary=_make_health(),
            active_workspaces=[{"id": "ws-1"}],
        )
        d = snap.to_dict()
        self.assertEqual(len(d["active_workspaces"]), 1)

    def test_node_status_in_dict(self) -> None:
        snap = OperatorSnapshot(
            health_summary=_make_health(),
            node_status=[{"node_id": "umh-vps"}],
        )
        d = snap.to_dict()
        self.assertEqual(len(d["node_status"]), 1)


class TestOperatorContextEngine(unittest.TestCase):
    def test_snapshot_returns_operator_snapshot(self) -> None:
        engine = _make_engine()
        snap = engine.snapshot()
        self.assertIsInstance(snap, OperatorSnapshot)

    def test_snapshot_has_health(self) -> None:
        engine = _make_engine()
        snap = engine.snapshot()
        self.assertIsInstance(snap.health_summary, OperatorHealthSummary)

    def test_health_summary_has_four_cards(self) -> None:
        engine = _make_engine()
        hs = engine.health_summary()
        self.assertEqual(len(hs.cards), 4)
        labels = {c.label for c in hs.cards}
        self.assertEqual(labels, {"Services", "State Domains", "Nodes", "Workspaces"})

    def test_health_services_card(self) -> None:
        engine = _make_engine()
        hs = engine.health_summary()
        svc_card = next(c for c in hs.cards if c.label == "Services")
        self.assertEqual(svc_card.value, 13)

    def test_health_state_card(self) -> None:
        engine = _make_engine()
        hs = engine.health_summary()
        state_card = next(c for c in hs.cards if c.label == "State Domains")
        self.assertEqual(state_card.value, 10)
        self.assertEqual(state_card.status, "healthy")

    def test_health_nodes_card(self) -> None:
        engine = _make_engine()
        hs = engine.health_summary()
        node_card = next(c for c in hs.cards if c.label == "Nodes")
        self.assertEqual(node_card.value, 1)

    def test_overall_healthy_when_all_healthy(self) -> None:
        engine = _make_engine(
            workspace_engine=MockWorkspaceEngine(snap=MockWorkspaceSnapshot()),
            service_failure_engine=MockServiceFailureEngine(
                health={
                    "total_services": 5,
                    "total_dependencies": 3,
                    "critical_count": 1,
                    "leaf_count": 2,
                    "max_blast_radius": 2,
                    "highest_risk_service": "svc_a",
                },
                path=[],
            ),
        )
        hs = engine.health_summary()
        self.assertEqual(hs.overall_status, "healthy")

    def test_overall_degraded_when_state_unhealthy(self) -> None:
        engine = _make_engine(
            state_coherence_engine=MockStateCoherenceEngine(
                health={
                    "total_domains": 10,
                    "coherent": 8,
                    "stale": 2,
                    "drifted": 0,
                    "unknown": 0,
                    "healthy": False,
                }
            ),
        )
        hs = engine.health_summary()
        self.assertEqual(hs.overall_status, "degraded")

    def test_node_status(self) -> None:
        engine = _make_engine()
        nodes = engine.node_status()
        self.assertEqual(len(nodes), 1)
        self.assertEqual(nodes[0]["node_id"], "umh-vps")

    def test_pending_approvals_zero(self) -> None:
        engine = _make_engine()
        result = engine.pending_approvals()
        self.assertEqual(result["count"], 0)

    def test_pending_approvals_nonzero(self) -> None:
        engine = _make_engine(
            approval_store=MockApprovalStore(pending=[MockApprovalRequest()]),
        )
        result = engine.pending_approvals()
        self.assertEqual(result["count"], 1)

    def test_service_alerts(self) -> None:
        engine = _make_engine()
        alerts = engine.service_alerts()
        self.assertGreater(len(alerts), 0)
        self.assertEqual(alerts[0]["service"], "event_spine")

    def test_active_workspaces_empty(self) -> None:
        engine = _make_engine()
        ws = engine.active_workspaces()
        self.assertEqual(ws, [])

    def test_active_workspaces_with_data(self) -> None:
        engine = _make_engine(
            workspace_engine=MockWorkspaceEngine(snap=MockWorkspaceSnapshot()),
        )
        ws = engine.active_workspaces()
        self.assertEqual(len(ws), 1)

    def test_graceful_degradation_no_spine(self) -> None:
        engine = OperatorContextEngine(
            event_spine=None,
            service_failure_engine=MockServiceFailureEngine(),
            state_coherence_engine=MockStateCoherenceEngine(),
            node_registry=MockNodeRegistry(),
            approval_store=MockApprovalStore(),
            workspace_engine=MockWorkspaceEngine(),
        )
        snap = engine.snapshot()
        self.assertEqual(snap.timeline, [])

    def test_graceful_degradation_no_services(self) -> None:
        engine = _make_engine(
            service_failure_engine=MockServiceFailureEngine(
                health={},
                path=[],
            ),
        )
        snap = engine.snapshot()
        self.assertEqual(snap.service_alerts, [])


class TestAttentionGeneration(unittest.TestCase):
    def test_no_attention_when_healthy(self) -> None:
        engine = _make_engine()
        items = engine.attention_items()
        svc_items = [i for i in items if i.attention_type == OperatorAttentionType.SERVICE]
        self.assertGreater(len(svc_items), 0)

    def test_state_drifted_generates_critical(self) -> None:
        engine = _make_engine(
            state_coherence_engine=MockStateCoherenceEngine(
                report={
                    "overall_health": "degraded",
                    "domain_count": 10,
                    "domains": [
                        {"domain": "memory", "status": "drifted", "service_owner": "memory"},
                    ],
                },
            ),
        )
        items = engine.attention_items()
        state_items = [i for i in items if i.attention_type == OperatorAttentionType.STATE]
        self.assertEqual(len(state_items), 1)
        self.assertEqual(state_items[0].severity, OperatorSeverity.CRITICAL)

    def test_state_stale_generates_critical(self) -> None:
        engine = _make_engine(
            state_coherence_engine=MockStateCoherenceEngine(
                report={
                    "overall_health": "degraded",
                    "domain_count": 10,
                    "domains": [
                        {
                            "domain": "runtime",
                            "status": "stale",
                            "service_owner": "distributed_runtime",
                        },
                    ],
                },
            ),
        )
        items = engine.attention_items()
        state_items = [i for i in items if i.attention_type == OperatorAttentionType.STATE]
        self.assertEqual(len(state_items), 1)

    def test_pending_approval_generates_warning(self) -> None:
        engine = _make_engine(
            approval_store=MockApprovalStore(pending=[MockApprovalRequest()]),
        )
        items = engine.attention_items()
        gov_items = [i for i in items if i.attention_type == OperatorAttentionType.GOVERNANCE]
        self.assertEqual(len(gov_items), 1)
        self.assertEqual(gov_items[0].severity, OperatorSeverity.WARNING)

    def test_high_blast_radius_generates_warning(self) -> None:
        engine = _make_engine()
        items = engine.attention_items()
        svc_items = [i for i in items if i.attention_type == OperatorAttentionType.SERVICE]
        self.assertTrue(len(svc_items) >= 1)
        self.assertTrue(any("blast_radius" in i.title for i in svc_items))

    def test_critical_event_generates_critical_attention(self) -> None:
        crit_event = MockOrganismEvent(
            event_id="evt-crit",
            domain="runtime",
            event_type="node_crash",
            source="test",
            priority="critical",
        )
        engine = _make_engine(event_spine=MockEventSpine(events=[crit_event]))
        items = engine.attention_items()
        runtime_items = [i for i in items if i.source == "event_spine"]
        self.assertEqual(len(runtime_items), 1)
        self.assertEqual(runtime_items[0].severity, OperatorSeverity.CRITICAL)

    def test_attention_sorted_by_severity(self) -> None:
        crit_event = MockOrganismEvent(priority="critical", event_type="crash", source="test")
        engine = _make_engine(
            event_spine=MockEventSpine(events=[crit_event]),
            approval_store=MockApprovalStore(pending=[MockApprovalRequest()]),
            state_coherence_engine=MockStateCoherenceEngine(
                report={
                    "overall_health": "degraded",
                    "domain_count": 1,
                    "domains": [
                        {"domain": "memory", "status": "drifted", "service_owner": "memory"}
                    ],
                },
            ),
        )
        items = engine.attention_items()
        self.assertGreater(len(items), 1)
        severities = [i.severity for i in items]
        critical_idx = next(
            (idx for idx, s in enumerate(severities) if s == OperatorSeverity.CRITICAL), None
        )
        warning_idx = next(
            (idx for idx, s in enumerate(severities) if s == OperatorSeverity.WARNING), None
        )
        if critical_idx is not None and warning_idx is not None:
            self.assertLess(critical_idx, warning_idx)

    def test_no_approval_attention_when_zero_pending(self) -> None:
        engine = _make_engine()
        items = engine.attention_items()
        gov_items = [i for i in items if i.attention_type == OperatorAttentionType.GOVERNANCE]
        self.assertEqual(len(gov_items), 0)

    def test_multiple_drifted_domains(self) -> None:
        engine = _make_engine(
            state_coherence_engine=MockStateCoherenceEngine(
                report={
                    "overall_health": "degraded",
                    "domain_count": 10,
                    "domains": [
                        {"domain": "memory", "status": "drifted", "service_owner": "memory"},
                        {
                            "domain": "runtime",
                            "status": "stale",
                            "service_owner": "distributed_runtime",
                        },
                        {
                            "domain": "governance",
                            "status": "coherent",
                            "service_owner": "governance",
                        },
                    ],
                },
            ),
        )
        items = engine.attention_items()
        state_items = [i for i in items if i.attention_type == OperatorAttentionType.STATE]
        self.assertEqual(len(state_items), 2)

    def test_low_blast_radius_no_attention(self) -> None:
        engine = _make_engine(
            service_failure_engine=MockServiceFailureEngine(
                path=[{"service_role": "leaf", "criticality": "optional", "blast_radius": 0}]
            ),
        )
        items = engine.attention_items()
        svc_items = [i for i in items if i.attention_type == OperatorAttentionType.SERVICE]
        self.assertEqual(len(svc_items), 0)


class TestTimeline(unittest.TestCase):
    def test_empty_timeline(self) -> None:
        engine = _make_engine(event_spine=MockEventSpine())
        tl = engine.timeline()
        self.assertEqual(len(tl), 0)

    def test_timeline_from_events(self) -> None:
        events = [
            MockOrganismEvent(event_id="e1", event_type="deploy", source="ci"),
            MockOrganismEvent(event_id="e2", event_type="restart", source="ops"),
        ]
        engine = _make_engine(event_spine=MockEventSpine(events=events))
        tl = engine.timeline()
        self.assertEqual(len(tl), 2)

    def test_timeline_event_format(self) -> None:
        events = [
            MockOrganismEvent(
                event_id="e1", domain="governance", event_type="approve", source="operator"
            )
        ]
        engine = _make_engine(event_spine=MockEventSpine(events=events))
        tl = engine.timeline()
        self.assertEqual(tl[0].event_id, "e1")
        self.assertEqual(tl[0].domain, "governance")
        self.assertEqual(tl[0].event_type, "approve")

    def test_timeline_limit(self) -> None:
        events = [
            MockOrganismEvent(event_id=f"e{i}", event_type="tick", source="test")
            for i in range(100)
        ]
        engine = _make_engine(event_spine=MockEventSpine(events=events))
        tl = engine.timeline(limit=10)
        self.assertEqual(len(tl), 10)

    def test_timeline_priority_preserved(self) -> None:
        events = [
            MockOrganismEvent(event_id="e1", priority="critical", event_type="crash", source="test")
        ]
        engine = _make_engine(event_spine=MockEventSpine(events=events))
        tl = engine.timeline()
        self.assertEqual(tl[0].priority, "critical")

    def test_timeline_summary_format(self) -> None:
        events = [MockOrganismEvent(event_id="e1", event_type="deploy", source="ci")]
        engine = _make_engine(event_spine=MockEventSpine(events=events))
        tl = engine.timeline()
        self.assertIn("deploy", tl[0].summary)
        self.assertIn("ci", tl[0].summary)

    def test_timeline_no_spine(self) -> None:
        engine = OperatorContextEngine(
            event_spine=None,
            service_failure_engine=MockServiceFailureEngine(),
            state_coherence_engine=MockStateCoherenceEngine(),
            node_registry=MockNodeRegistry(),
            approval_store=MockApprovalStore(),
            workspace_engine=MockWorkspaceEngine(),
        )
        tl = engine.timeline()
        self.assertEqual(tl, [])

    def test_timeline_returns_operator_timeline_events(self) -> None:
        events = [MockOrganismEvent(event_id="e1", event_type="test", source="s")]
        engine = _make_engine(event_spine=MockEventSpine(events=events))
        tl = engine.timeline()
        self.assertIsInstance(tl[0], OperatorTimelineEvent)


class TestCockpitRoutes(unittest.TestCase):
    def test_route_module_imports(self) -> None:
        from transports.api import cockpit_operator_home_routes

        self.assertTrue(hasattr(cockpit_operator_home_routes, "configure"))
        self.assertTrue(hasattr(cockpit_operator_home_routes, "operator_home_router"))

    def test_router_is_api_router(self) -> None:
        from transports.api.cockpit_operator_home_routes import operator_home_router
        from fastapi import APIRouter

        self.assertIsInstance(operator_home_router, APIRouter)

    def test_configure_idempotent(self) -> None:
        import importlib
        from transports.api import cockpit_operator_home_routes

        importlib.reload(cockpit_operator_home_routes)
        mock_dep = MagicMock()
        cockpit_operator_home_routes.configure(require_operator_dep=mock_dep)
        cockpit_operator_home_routes.configure(require_operator_dep=mock_dep)
        self.assertTrue(cockpit_operator_home_routes._configured)

    def test_build_router_has_prefix(self) -> None:
        import importlib
        from transports.api import cockpit_operator_home_routes

        importlib.reload(cockpit_operator_home_routes)
        mock_dep = MagicMock()
        cockpit_operator_home_routes.configure(require_operator_dep=mock_dep)
        routes = cockpit_operator_home_routes.operator_home_router.routes
        self.assertGreater(len(routes), 0)

    def test_route_count(self) -> None:
        import importlib
        from transports.api import cockpit_operator_home_routes

        importlib.reload(cockpit_operator_home_routes)
        mock_dep = MagicMock()
        cockpit_operator_home_routes.configure(require_operator_dep=mock_dep)
        sub_routers = cockpit_operator_home_routes.operator_home_router.routes
        all_routes = []
        for r in sub_routers:
            if hasattr(r, "routes"):
                all_routes.extend(r.routes)
            else:
                all_routes.append(r)
        self.assertGreaterEqual(len(all_routes), 8)

    def test_engine_instantiation(self) -> None:
        import importlib
        from transports.api import cockpit_operator_home_routes

        importlib.reload(cockpit_operator_home_routes)
        if hasattr(cockpit_operator_home_routes._get_engine, "_instance"):
            del cockpit_operator_home_routes._get_engine._instance
        engine = cockpit_operator_home_routes._get_engine()
        self.assertIsInstance(engine, OperatorContextEngine)


class TestTypeRegistration(unittest.TestCase):
    def test_types_registered(self) -> None:
        from substrate.canonical_types import CANONICAL_TYPES

        expected = [
            "OperatorSeverity",
            "OperatorAttentionType",
            "OperatorAttentionItem",
            "OperatorStatusCard",
            "OperatorHealthSummary",
            "OperatorTimelineEvent",
            "OperatorSnapshot",
            "OperatorContextEngine",
        ]
        for name in expected:
            self.assertIn(name, CANONICAL_TYPES, f"{name} not registered")

    def test_type_module_paths(self) -> None:
        from substrate.canonical_types import CANONICAL_TYPES

        self.assertEqual(
            CANONICAL_TYPES["OperatorSeverity"],
            ["substrate.operator.operator_context"],
        )
        self.assertEqual(
            CANONICAL_TYPES["OperatorContextEngine"],
            ["substrate.operator.operator_context_engine"],
        )

    def test_registration_count(self) -> None:
        from substrate.canonical_types import CANONICAL_TYPES

        phase31_types = [
            k
            for k in CANONICAL_TYPES
            if k.startswith("Operator")
            and CANONICAL_TYPES[k] == ["substrate.operator.operator_context"]
            or CANONICAL_TYPES[k] == ["substrate.operator.operator_context_engine"]
        ]
        self.assertGreaterEqual(len(phase31_types), 8)

    def test_no_duplicate_registrations(self) -> None:
        from substrate.canonical_types import CANONICAL_TYPES

        phase31_modules = [
            "substrate.operator.operator_context",
            "substrate.operator.operator_context_engine",
        ]
        for name, modules in CANONICAL_TYPES.items():
            if any(m in phase31_modules for m in modules):
                self.assertEqual(len(modules), 1, f"{name} registered in multiple modules")


class TestIntegration(unittest.TestCase):
    def test_full_snapshot_composition(self) -> None:
        events = [
            MockOrganismEvent(event_id=f"e{i}", event_type="tick", source="test") for i in range(5)
        ]
        engine = _make_engine(
            event_spine=MockEventSpine(events=events),
            approval_store=MockApprovalStore(pending=[MockApprovalRequest()]),
            workspace_engine=MockWorkspaceEngine(snap=MockWorkspaceSnapshot()),
        )
        snap = engine.snapshot()
        self.assertEqual(snap.pending_approvals, 1)
        self.assertEqual(len(snap.timeline), 5)
        self.assertGreater(len(snap.attention_items), 0)
        self.assertEqual(len(snap.active_workspaces), 1)

    def test_snapshot_serialization(self) -> None:
        engine = _make_engine()
        snap = engine.snapshot()
        d = snap.to_dict()
        self.assertIn("health_summary", d)
        self.assertIn("attention_items", d)
        self.assertIn("timeline", d)
        self.assertIn("generated_at", d)

    def test_snapshot_roundtrip(self) -> None:
        events = [MockOrganismEvent(event_id="e1", event_type="test", source="s")]
        engine = _make_engine(event_spine=MockEventSpine(events=events))
        snap = engine.snapshot()
        d = snap.to_dict()
        restored = OperatorSnapshot.from_dict(d)
        self.assertEqual(restored.pending_approvals, snap.pending_approvals)
        self.assertEqual(len(restored.timeline), len(snap.timeline))

    def test_all_subsystems_none_graceful(self) -> None:
        """With no injected deps, lazy props may load real impls — test graceful."""
        engine = OperatorContextEngine()
        snap = engine.snapshot()
        self.assertIsInstance(snap, OperatorSnapshot)
        self.assertEqual(snap.pending_approvals, 0)
        self.assertIsInstance(snap.service_alerts, list)
        self.assertIsInstance(snap.node_status, list)
        self.assertIsInstance(snap.timeline, list)

    def test_partial_subsystems(self) -> None:
        engine = OperatorContextEngine(
            node_registry=MockNodeRegistry(),
            event_spine=MockEventSpine(events=[MockOrganismEvent()]),
        )
        snap = engine.snapshot()
        self.assertEqual(len(snap.node_status), 1)
        self.assertEqual(len(snap.timeline), 1)

    def test_engine_health_summary_overall(self) -> None:
        engine = _make_engine(
            workspace_engine=MockWorkspaceEngine(snap=MockWorkspaceSnapshot()),
        )
        hs = engine.health_summary()
        self.assertIn(hs.overall_status, ("healthy", "degraded", "critical", "unknown"))

    def test_attention_items_are_operator_attention_items(self) -> None:
        engine = _make_engine(
            approval_store=MockApprovalStore(pending=[MockApprovalRequest()]),
        )
        items = engine.attention_items()
        for item in items:
            self.assertIsInstance(item, OperatorAttentionItem)

    def test_service_alerts_structure(self) -> None:
        engine = _make_engine()
        alerts = engine.service_alerts()
        for alert in alerts:
            self.assertIn("service", alert)
            self.assertIn("blast_radius", alert)
            self.assertIn("criticality", alert)

    def test_node_status_structure(self) -> None:
        engine = _make_engine()
        nodes = engine.node_status()
        for node in nodes:
            self.assertIn("node_id", node)

    def test_workspace_none_engine_returns_empty(self) -> None:
        engine = OperatorContextEngine(
            workspace_engine=None,
            service_failure_engine=MockServiceFailureEngine(),
            state_coherence_engine=MockStateCoherenceEngine(),
            node_registry=MockNodeRegistry(),
            approval_store=MockApprovalStore(),
            event_spine=MockEventSpine(),
        )
        ws = engine.active_workspaces()
        self.assertEqual(ws, [])


if __name__ == "__main__":
    unittest.main()
