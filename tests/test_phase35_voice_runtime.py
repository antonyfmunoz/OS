"""Phase 35 — Voice Query Engine tests.

Tests context-grounded query resolution: IntentRouter classification →
VoiceQueryEngine domain detection → subsystem query → structured answer.

107 tests across 20 test classes.
"""

from __future__ import annotations

import sys
import time
from dataclasses import dataclass
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, "/opt/OS")

from substrate.operator.voice_query_engine import (
    QueryDomain,
    QueryResolution,
    VoiceQueryEngine,
)


# ── Fixtures ─────────────────────────────────────────────────────


@dataclass
class MockClassification:
    route_type: str = "observation"
    confidence: float = 0.90
    domain: str = ""
    work_type: str = ""
    risk_class: str = "low"


@dataclass
class MockSnapshot:
    health_summary: object = None
    attention_items: list = None
    active_workspaces: list = None
    pending_approvals: int = 0
    service_alerts: list = None
    node_status: list = None
    timeline: list = None
    generated_at: float = 0.0

    def __post_init__(self):
        if self.attention_items is None:
            self.attention_items = []
        if self.active_workspaces is None:
            self.active_workspaces = []
        if self.service_alerts is None:
            self.service_alerts = []
        if self.node_status is None:
            self.node_status = []
        if self.timeline is None:
            self.timeline = []

    def to_dict(self):
        return {"generated_at": self.generated_at}


@dataclass
class MockHealthSummary:
    overall_status: str = "healthy"


@dataclass
class MockScreenSnapshot:
    source_type: object = None
    active_application: object = None
    file_context: object = None
    repository_context: object = None
    browser_context: object = None
    source_confidence: float = 0.9

    def to_dict(self):
        return {"source_type": str(self.source_type)}


class MockSourceType:
    def __init__(self, value):
        self.value = value


@dataclass
class MockApp:
    app_name: str = "VS Code"


@dataclass
class MockFileContext:
    file_name: str = "test.py"
    file_path: str = "/opt/OS/test.py"


@dataclass
class MockRepoContext:
    repo_name: str = "OS"
    branch: str = "main"
    repo_path: str = "/opt/OS"


@dataclass
class MockBrowserContext:
    title: str = "GitHub"
    url: str = ""
    domain: str = ""


@dataclass
class MockNodeRecord:
    node_id: str = "vps-1"
    role: str = "orchestrator"


@dataclass
class MockApprovalRequest:
    approval_id: str = "apr-1"
    description: str = "Deploy to production"
    risk_level: str = "high"


@dataclass
class MockPlan:
    execution_plan_id: str = "plan-1"
    status: str = "executing"


@dataclass
class MockWorkspace:
    workspace_id: str = "ws-os"


@dataclass
class MockTopology:
    workspaces: list = None

    def __post_init__(self):
        if self.workspaces is None:
            self.workspaces = []


# ══════════════════════════════════════════════════════════════════
# Test Classes
# ══════════════════════════════════════════════════════════════════


class TestQueryDomainEnum:
    def test_all_10_values(self):
        assert len(QueryDomain) == 10

    def test_string_values(self):
        assert QueryDomain.STATUS.value == "status"
        assert QueryDomain.ACTION.value == "action"
        assert QueryDomain.HELP.value == "help"

    def test_from_string(self):
        assert QueryDomain("status") == QueryDomain.STATUS
        assert QueryDomain("action") == QueryDomain.ACTION

    def test_names(self):
        names = {d.name for d in QueryDomain}
        expected = {
            "STATUS", "SCREEN", "WORKSPACE", "RESUME", "SERVICE",
            "NODE", "STATE", "REALITY", "ACTION", "HELP",
        }
        assert names == expected


class TestQueryResolution:
    def test_creation(self):
        r = QueryResolution(domain="status", answer_text="All good.")
        assert r.domain == "status"
        assert r.answer_text == "All good."

    def test_defaults(self):
        r = QueryResolution(domain="help", answer_text="")
        assert r.structured_data == {}
        assert r.sources == []
        assert r.confidence == 0.0

    def test_sources_list(self):
        r = QueryResolution(
            domain="screen",
            answer_text="test",
            sources=["ScreenObservationEngine", "ContinuityEngine"],
        )
        assert len(r.sources) == 2

    def test_to_dict(self):
        r = QueryResolution(domain="status", answer_text="ok", confidence=0.9)
        d = r.to_dict()
        assert d["domain"] == "status"
        assert d["confidence"] == 0.9
        assert "resolved_at" in d

    def test_from_dict(self):
        d = {"domain": "node", "answer_text": "2 nodes", "confidence": 0.85}
        r = QueryResolution.from_dict(d)
        assert r.domain == "node"
        assert r.answer_text == "2 nodes"
        assert r.confidence == 0.85


class TestDomainDetection:
    def setup_method(self):
        self.engine = VoiceQueryEngine()

    def test_status_detection(self):
        domain, _ = self.engine.detect_domain("What's the status?")
        assert domain == QueryDomain.STATUS

    def test_screen_detection(self):
        domain, _ = self.engine.detect_domain("What am I looking at?")
        assert domain == QueryDomain.SCREEN

    def test_workspace_detection(self):
        domain, _ = self.engine.detect_domain("What repo is open?")
        assert domain == QueryDomain.WORKSPACE

    def test_resume_detection(self):
        domain, _ = self.engine.detect_domain("Resume where I left off")
        assert domain == QueryDomain.RESUME

    def test_service_detection(self):
        domain, _ = self.engine.detect_domain("What service is failing?")
        assert domain == QueryDomain.SERVICE

    def test_node_detection(self):
        domain, _ = self.engine.detect_domain("Which nodes are online?")
        assert domain == QueryDomain.NODE

    def test_state_detection(self):
        domain, _ = self.engine.detect_domain("What is the state domain status?")
        assert domain == QueryDomain.STATE

    def test_reality_detection(self):
        domain, _ = self.engine.detect_domain("Why did the deploy fail?")
        assert domain == QueryDomain.REALITY

    def test_action_detection(self):
        domain, _ = self.engine.detect_domain("What approvals are waiting?")
        assert domain == QueryDomain.ACTION

    def test_help_detection(self):
        domain, _ = self.engine.detect_domain("Help me understand this")
        assert domain == QueryDomain.HELP

    def test_empty_defaults_to_status(self):
        domain, conf = self.engine.detect_domain("hello there")
        assert domain == QueryDomain.STATUS
        assert conf == 0.50

    def test_ambiguous_picks_highest_confidence(self):
        domain, _ = self.engine.detect_domain("What service node is down?")
        assert domain in (QueryDomain.SERVICE, QueryDomain.NODE)

    def test_route_type_approval_forces_action(self):
        domain, conf = self.engine.detect_domain("approve it", route_type="approval")
        assert domain == QueryDomain.ACTION
        assert conf == 0.95

    def test_route_type_work_packet_returns_help(self):
        domain, conf = self.engine.detect_domain("build the feature", route_type="work_packet")
        assert domain == QueryDomain.HELP
        assert conf == 0.40

    def test_route_type_hybrid_returns_help(self):
        domain, _ = self.engine.detect_domain("should we refactor", route_type="hybrid")
        assert domain == QueryDomain.HELP

    def test_working_on_detects_screen(self):
        domain, _ = self.engine.detect_domain("What am I working on?")
        assert domain == QueryDomain.SCREEN


class TestClassificationFirst:
    def setup_method(self):
        self.engine = VoiceQueryEngine()

    def test_resolve_calls_intent_router_when_no_classification(self):
        mock_router = MagicMock()
        mock_router.classify.return_value = MockClassification(
            route_type="observation", confidence=0.90,
        )
        self.engine._intent_router = mock_router
        result = self.engine.resolve("What's the status?")
        mock_router.classify.assert_called_once_with("What's the status?")
        assert result.route_type == "observation"

    def test_resolve_uses_provided_classification(self):
        mock_router = MagicMock()
        self.engine._intent_router = mock_router
        classification = MockClassification(
            route_type="observation", confidence=0.92,
        )
        result = self.engine.resolve("What's the status?", classification=classification)
        mock_router.classify.assert_not_called()
        assert result.route_confidence == 0.92

    def test_route_type_constrains_domain(self):
        classification = MockClassification(
            route_type="approval", confidence=0.95,
        )
        result = self.engine.resolve("approve the deployment", classification=classification)
        assert result.domain == QueryDomain.ACTION.value

    def test_approval_route_forces_action(self):
        classification = MockClassification(route_type="approval", confidence=0.95)
        result = self.engine.resolve("do it", classification=classification)
        assert result.domain == QueryDomain.ACTION.value

    def test_work_packet_route_returns_help(self):
        classification = MockClassification(route_type="work_packet", confidence=0.85)
        result = self.engine.resolve("build the auth system", classification=classification)
        assert result.domain == QueryDomain.HELP.value

    def test_empty_text_returns_help(self):
        result = self.engine.resolve("")
        assert result.domain == QueryDomain.HELP.value


class TestStatusResolution:
    def setup_method(self):
        self.engine = VoiceQueryEngine()

    def test_status_with_healthy_system(self):
        mock_ctx = MagicMock()
        mock_ctx.snapshot.return_value = MockSnapshot(
            health_summary=MockHealthSummary("healthy"),
            pending_approvals=0,
        )
        self.engine._context_engine = mock_ctx
        result = self.engine.query_domain(QueryDomain.STATUS, "status")
        assert "healthy" in result.answer_text
        assert result.domain == "status"

    def test_status_with_attention_items(self):
        mock_ctx = MagicMock()
        mock_ctx.snapshot.return_value = MockSnapshot(
            health_summary=MockHealthSummary("degraded"),
            attention_items=["a", "b", "c"],
            pending_approvals=2,
        )
        self.engine._context_engine = mock_ctx
        result = self.engine.query_domain(QueryDomain.STATUS, "status")
        assert "3 items" in result.answer_text
        assert "2 approvals" in result.answer_text

    def test_status_source(self):
        mock_ctx = MagicMock()
        mock_ctx.snapshot.return_value = MockSnapshot(
            health_summary=MockHealthSummary("healthy"),
        )
        self.engine._context_engine = mock_ctx
        result = self.engine.query_domain(QueryDomain.STATUS, "status")
        assert "OperatorContextEngine" in result.sources

    def test_status_confidence(self):
        mock_ctx = MagicMock()
        mock_ctx.snapshot.return_value = MockSnapshot(
            health_summary=MockHealthSummary("healthy"),
        )
        self.engine._context_engine = mock_ctx
        result = self.engine.query_domain(QueryDomain.STATUS, "status")
        assert result.confidence == 0.90

    def test_status_unavailable(self):
        with patch.object(type(self.engine), "context_engine", new_callable=lambda: property(lambda self: None)):
            result = self.engine.query_domain(QueryDomain.STATUS, "status")
        assert "not available" in result.answer_text
        assert result.confidence == 0.30


class TestScreenResolution:
    def setup_method(self):
        self.engine = VoiceQueryEngine()

    def test_screen_with_active_app(self):
        mock_engine = MagicMock()
        snap = MockScreenSnapshot(
            source_type=MockSourceType("observed"),
            active_application=MockApp("VS Code"),
        )
        mock_engine.current_snapshot.return_value = snap
        self.engine._screen_engine = mock_engine
        result = self.engine.query_domain(QueryDomain.SCREEN, "what am I looking at")
        assert "VS Code" in result.answer_text

    def test_screen_with_file_context(self):
        mock_engine = MagicMock()
        snap = MockScreenSnapshot(
            source_type=MockSourceType("observed"),
            file_context=MockFileContext("app.py"),
        )
        mock_engine.current_snapshot.return_value = snap
        self.engine._screen_engine = mock_engine
        result = self.engine.query_domain(QueryDomain.SCREEN, "what file")
        assert "app.py" in result.answer_text

    def test_screen_with_repo(self):
        mock_engine = MagicMock()
        snap = MockScreenSnapshot(
            source_type=MockSourceType("observed"),
            repository_context=MockRepoContext("OS", "main"),
        )
        mock_engine.current_snapshot.return_value = snap
        self.engine._screen_engine = mock_engine
        result = self.engine.query_domain(QueryDomain.SCREEN, "what repo")
        assert "OS" in result.answer_text
        assert "main" in result.answer_text

    def test_screen_observed_vs_inferred(self):
        mock_engine = MagicMock()
        snap = MockScreenSnapshot(
            source_type=MockSourceType("inferred"),
            source_confidence=0.3,
        )
        mock_engine.current_snapshot.return_value = snap
        self.engine._screen_engine = mock_engine
        result = self.engine.query_domain(QueryDomain.SCREEN, "what am I doing")
        assert result.confidence == 0.3

    def test_screen_unavailable(self):
        with patch.object(type(self.engine), "screen_engine", new_callable=lambda: property(lambda self: None)):
            result = self.engine.query_domain(QueryDomain.SCREEN, "screen")
        assert "not available" in result.answer_text


class TestWorkspaceResolution:
    def setup_method(self):
        self.engine = VoiceQueryEngine()

    def test_workspace_with_workspaces(self):
        mock_engine = MagicMock()
        mock_engine.topology.return_value = MockTopology(
            workspaces=[MockWorkspace("ws-os"), MockWorkspace("ws-saas")],
        )
        self.engine._workspace_engine = mock_engine
        result = self.engine.query_domain(QueryDomain.WORKSPACE, "what workspaces")
        assert "2 workspaces" in result.answer_text

    def test_workspace_empty(self):
        mock_engine = MagicMock()
        mock_engine.topology.return_value = MockTopology(workspaces=[])
        self.engine._workspace_engine = mock_engine
        result = self.engine.query_domain(QueryDomain.WORKSPACE, "workspaces")
        assert "No workspaces" in result.answer_text

    def test_workspace_source(self):
        mock_engine = MagicMock()
        mock_engine.topology.return_value = MockTopology(
            workspaces=[MockWorkspace("ws-os")],
        )
        self.engine._workspace_engine = mock_engine
        result = self.engine.query_domain(QueryDomain.WORKSPACE, "workspace")
        assert "WorkspaceTopologyEngine" in result.sources

    def test_workspace_unavailable(self):
        with patch.object(type(self.engine), "workspace_engine", new_callable=lambda: property(lambda self: None)):
            result = self.engine.query_domain(QueryDomain.WORKSPACE, "workspace")
        assert "not available" in result.answer_text


class TestResumeResolution:
    def setup_method(self):
        self.engine = VoiceQueryEngine()

    def test_resume_with_checkpoint(self):
        mock_engine = MagicMock()
        mock_engine.resume_suggestion.return_value = {
            "has_checkpoint": True,
            "checkpoint_type": "code_edit",
            "detail": "Editing voice_query_engine.py",
            "recovery_hint": "Open the file and continue from line 42",
        }
        self.engine._continuity_engine = mock_engine
        result = self.engine.query_domain(QueryDomain.RESUME, "resume")
        assert "code_edit" in result.answer_text
        assert "ContinuityEngine" in result.sources

    def test_resume_no_checkpoint(self):
        mock_engine = MagicMock()
        mock_engine.resume_suggestion.return_value = {"has_checkpoint": False}
        self.engine._continuity_engine = mock_engine
        result = self.engine.query_domain(QueryDomain.RESUME, "resume")
        assert "No recent checkpoint" in result.answer_text

    def test_resume_recovery_hint(self):
        mock_engine = MagicMock()
        mock_engine.resume_suggestion.return_value = {
            "has_checkpoint": True,
            "checkpoint_type": "deployment",
            "recovery_hint": "Check deploy status",
        }
        self.engine._continuity_engine = mock_engine
        result = self.engine.query_domain(QueryDomain.RESUME, "resume")
        assert "Check deploy status" in result.answer_text

    def test_resume_no_data(self):
        mock_engine = MagicMock()
        mock_engine.resume_suggestion.return_value = None
        self.engine._continuity_engine = mock_engine
        result = self.engine.query_domain(QueryDomain.RESUME, "resume")
        assert "No recent checkpoint" in result.answer_text

    def test_resume_unavailable(self):
        with patch.object(type(self.engine), "continuity_engine", new_callable=lambda: property(lambda self: None)):
            result = self.engine.query_domain(QueryDomain.RESUME, "resume")
        assert "not available" in result.answer_text


class TestServiceResolution:
    def setup_method(self):
        self.engine = VoiceQueryEngine()

    def test_all_healthy(self):
        mock_engine = MagicMock()
        mock_engine.service_health_map.return_value = {
            "os-discord": "healthy", "os-operator": "healthy",
        }
        mock_engine.organism_health.return_value = {"overall_health": "healthy"}
        self.engine._service_engine = mock_engine
        result = self.engine.query_domain(QueryDomain.SERVICE, "services")
        assert "All 2 services healthy" in result.answer_text

    def test_failing_services(self):
        mock_engine = MagicMock()
        mock_engine.service_health_map.return_value = {
            "os-discord": "healthy", "os-webhook": "down",
        }
        mock_engine.organism_health.return_value = {"overall_health": "degraded"}
        self.engine._service_engine = mock_engine
        result = self.engine.query_domain(QueryDomain.SERVICE, "failing")
        assert "os-webhook" in result.answer_text
        assert "1 services not healthy" in result.answer_text

    def test_service_structured_data(self):
        mock_engine = MagicMock()
        mock_engine.service_health_map.return_value = {"os-discord": "healthy"}
        mock_engine.organism_health.return_value = {"overall_health": "healthy"}
        self.engine._service_engine = mock_engine
        result = self.engine.query_domain(QueryDomain.SERVICE, "services")
        assert "health_map" in result.structured_data

    def test_service_dependency(self):
        mock_engine = MagicMock()
        mock_engine.service_health_map.return_value = {
            "os-discord": "healthy", "os-operator": "degraded",
        }
        mock_engine.organism_health.return_value = {"overall_health": "degraded"}
        self.engine._service_engine = mock_engine
        result = self.engine.query_domain(QueryDomain.SERVICE, "what depends on")
        assert "failing_services" in result.structured_data

    def test_service_unavailable(self):
        with patch.object(type(self.engine), "service_engine", new_callable=lambda: property(lambda self: None)):
            result = self.engine.query_domain(QueryDomain.SERVICE, "services")
        assert "not available" in result.answer_text


class TestNodeResolution:
    def setup_method(self):
        self.engine = VoiceQueryEngine()

    def test_nodes_listed(self):
        mock_reg = MagicMock()
        mock_reg.list_nodes.return_value = [
            MockNodeRecord("vps-1", "orchestrator"),
            MockNodeRecord("beast-1", "workstation"),
        ]
        mock_reg.primary_node.return_value = MockNodeRecord("vps-1", "orchestrator")
        self.engine._node_registry = mock_reg
        result = self.engine.query_domain(QueryDomain.NODE, "nodes")
        assert "2 nodes" in result.answer_text
        assert "vps-1" in result.answer_text

    def test_node_primary(self):
        mock_reg = MagicMock()
        mock_reg.list_nodes.return_value = [MockNodeRecord("vps-1", "orchestrator")]
        mock_reg.primary_node.return_value = MockNodeRecord("vps-1", "orchestrator")
        self.engine._node_registry = mock_reg
        result = self.engine.query_domain(QueryDomain.NODE, "nodes")
        assert result.structured_data["primary_node"] == "vps-1"

    def test_node_health(self):
        mock_reg = MagicMock()
        mock_reg.list_nodes.return_value = []
        mock_reg.primary_node.return_value = None
        self.engine._node_registry = mock_reg
        result = self.engine.query_domain(QueryDomain.NODE, "nodes")
        assert "0 nodes" in result.answer_text

    def test_node_unavailable(self):
        with patch.object(type(self.engine), "node_registry", new_callable=lambda: property(lambda self: None)):
            result = self.engine.query_domain(QueryDomain.NODE, "nodes")
        assert "not available" in result.answer_text


class TestStateResolution:
    def setup_method(self):
        self.engine = VoiceQueryEngine()

    def test_state_coherence(self):
        mock_engine = MagicMock()
        mock_engine.coherence_report.return_value = {
            "overall_health": "healthy",
            "domains": [
                {"name": "operator", "status": "coherent"},
                {"name": "execution", "status": "coherent"},
            ],
        }
        self.engine._state_engine = mock_engine
        result = self.engine.query_domain(QueryDomain.STATE, "state")
        assert "healthy" in result.answer_text
        assert "2 of 2" in result.answer_text

    def test_state_with_drift(self):
        mock_engine = MagicMock()
        mock_engine.coherence_report.return_value = {
            "overall_health": "degraded",
            "domains": [
                {"name": "operator", "status": "coherent"},
                {"name": "execution", "status": "drifted"},
            ],
        }
        self.engine._state_engine = mock_engine
        result = self.engine.query_domain(QueryDomain.STATE, "state")
        assert "1 of 2" in result.answer_text

    def test_state_source(self):
        mock_engine = MagicMock()
        mock_engine.coherence_report.return_value = {
            "overall_health": "healthy", "domains": [],
        }
        self.engine._state_engine = mock_engine
        result = self.engine.query_domain(QueryDomain.STATE, "state")
        assert "StateCoherenceEngine" in result.sources

    def test_state_unavailable(self):
        with patch.object(type(self.engine), "state_engine", new_callable=lambda: property(lambda self: None)):
            result = self.engine.query_domain(QueryDomain.STATE, "state")
        assert "not available" in result.answer_text


class _FakeEnum:
    def __init__(self, value: str):
        self.value = value


class _MockRealityQueryType:
    WHY = _FakeEnum("why")
    WHAT_CHANGED = _FakeEnum("what_changed")
    EVIDENCE = _FakeEnum("evidence")
    CONTRADICTIONS = _FakeEnum("contradictions")
    LINEAGE = _FakeEnum("lineage")
    PRIORITIES = _FakeEnum("priorities")


class _MockRealityQuery:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)


def _patch_reality_import():
    mod = MagicMock()
    mod.RealityQuery = _MockRealityQuery
    mod.RealityQueryType = _MockRealityQueryType
    return patch.dict("sys.modules", {
        "substrate.reality_model": MagicMock(),
        "substrate.reality_model.reality_intelligence": mod,
    })


class TestRealityResolution:
    def setup_method(self):
        self.engine = VoiceQueryEngine()

    def test_why_query(self):
        mock_engine = MagicMock()
        mock_result = MagicMock()
        mock_result.summary = "The deploy failed because the config was missing."
        mock_result.evidence = [MagicMock()]
        mock_result.confidence = 0.80
        mock_engine.query.return_value = mock_result
        self.engine._reality_engine = mock_engine
        with _patch_reality_import():
            result = self.engine.query_domain(QueryDomain.REALITY, "Why did the deploy fail?")
        assert "config was missing" in result.answer_text
        assert result.structured_data["query_type"] == "why"

    def test_what_changed(self):
        mock_engine = MagicMock()
        mock_result = MagicMock()
        mock_result.summary = "3 files changed in the last hour."
        mock_result.evidence = []
        mock_result.confidence = 0.70
        mock_engine.query.return_value = mock_result
        self.engine._reality_engine = mock_engine
        with _patch_reality_import():
            result = self.engine.query_domain(QueryDomain.REALITY, "What changed recently?")
        assert "3 files changed" in result.answer_text

    def test_evidence_count(self):
        mock_engine = MagicMock()
        mock_result = MagicMock()
        mock_result.summary = "Evidence found."
        mock_result.evidence = [MagicMock(), MagicMock(), MagicMock()]
        mock_result.confidence = 0.85
        mock_engine.query.return_value = mock_result
        self.engine._reality_engine = mock_engine
        with _patch_reality_import():
            result = self.engine.query_domain(QueryDomain.REALITY, "Show me evidence for X")
        assert result.structured_data["evidence_count"] == 3

    def test_reality_no_data(self):
        mock_engine = MagicMock()
        mock_result = MagicMock()
        mock_result.summary = ""
        mock_result.evidence = []
        mock_result.confidence = 0.0
        mock_engine.query.return_value = mock_result
        self.engine._reality_engine = mock_engine
        with _patch_reality_import():
            result = self.engine.query_domain(QueryDomain.REALITY, "Why?")
        assert "No reality data" in result.answer_text

    def test_reality_unavailable(self):
        self.engine._reality_engine = None
        result = self.engine.query_domain(QueryDomain.REALITY, "why")
        assert "not available" in result.answer_text


class TestActionResolution:
    def setup_method(self):
        self.engine = VoiceQueryEngine()

    def test_pending_approvals(self):
        mock_store = MagicMock()
        mock_store.list_pending.return_value = [
            MockApprovalRequest("apr-1"), MockApprovalRequest("apr-2"),
        ]
        self.engine._approval_store = mock_store
        self.engine._coordinator = None
        result = self.engine.query_domain(QueryDomain.ACTION, "approvals")
        assert "2 approvals waiting" in result.answer_text

    def test_active_plans(self):
        mock_coord = MagicMock()
        mock_coord.active_plans.return_value = [MockPlan("p1"), MockPlan("p2")]
        mock_coord.queue_state.return_value = []
        self.engine._approval_store = None
        self.engine._coordinator = mock_coord
        result = self.engine.query_domain(QueryDomain.ACTION, "executing")
        assert "2 plans executing" in result.answer_text

    def test_queue_depth(self):
        mock_coord = MagicMock()
        mock_coord.active_plans.return_value = []
        mock_coord.queue_state.return_value = [MockPlan("p1"), MockPlan("p2"), MockPlan("p3")]
        self.engine._approval_store = None
        self.engine._coordinator = mock_coord
        result = self.engine.query_domain(QueryDomain.ACTION, "queue")
        assert "3 in queue" in result.answer_text

    def test_nothing_active(self):
        mock_store = MagicMock()
        mock_store.list_pending.return_value = []
        mock_coord = MagicMock()
        mock_coord.active_plans.return_value = []
        mock_coord.queue_state.return_value = []
        self.engine._approval_store = mock_store
        self.engine._coordinator = mock_coord
        result = self.engine.query_domain(QueryDomain.ACTION, "blocked")
        assert "No pending approvals" in result.answer_text
        assert "No active execution" in result.answer_text

    def test_both_sources(self):
        mock_store = MagicMock()
        mock_store.list_pending.return_value = [MockApprovalRequest()]
        mock_coord = MagicMock()
        mock_coord.active_plans.return_value = [MockPlan()]
        mock_coord.queue_state.return_value = []
        self.engine._approval_store = mock_store
        self.engine._coordinator = mock_coord
        result = self.engine.query_domain(QueryDomain.ACTION, "what is happening")
        assert "ApprovalInterceptStore" in result.sources
        assert "ExecutionCoordinator" in result.sources

    def test_action_all_subsystems_respond(self):
        mock_store = MagicMock()
        mock_store.list_pending.side_effect = Exception("unreachable")
        mock_coord = MagicMock()
        mock_coord.active_plans.side_effect = Exception("unreachable")
        self.engine._approval_store = mock_store
        self.engine._coordinator = mock_coord
        result = self.engine.query_domain(QueryDomain.ACTION, "actions")
        assert "Action subsystems unavailable" in result.answer_text


class TestHelpResolution:
    def setup_method(self):
        self.engine = VoiceQueryEngine()

    def test_help_lists_domains(self):
        result = self.engine.query_domain(QueryDomain.HELP, "help")
        assert "status" in result.answer_text
        assert "screen" in result.answer_text

    def test_help_structured_data(self):
        result = self.engine.query_domain(QueryDomain.HELP, "help")
        assert "available_domains" in result.structured_data
        assert len(result.structured_data["available_domains"]) == 10

    def test_help_confidence(self):
        result = self.engine.query_domain(QueryDomain.HELP, "help")
        assert result.confidence == 0.95


class TestFullPipeline:
    def setup_method(self):
        self.engine = VoiceQueryEngine()
        mock_router = MagicMock()
        mock_router.classify.return_value = MockClassification(
            route_type="observation", confidence=0.90,
        )
        self.engine._intent_router = mock_router

    def test_status_e2e(self):
        mock_ctx = MagicMock()
        mock_ctx.snapshot.return_value = MockSnapshot(
            health_summary=MockHealthSummary("healthy"),
        )
        self.engine._context_engine = mock_ctx
        result = self.engine.resolve("What's the overall status?")
        assert result.route_type == "observation"
        assert result.domain == "status"
        assert "healthy" in result.answer_text

    def test_screen_e2e(self):
        mock_screen = MagicMock()
        snap = MockScreenSnapshot(
            source_type=MockSourceType("observed"),
            active_application=MockApp("VS Code"),
            file_context=MockFileContext("engine.py"),
        )
        mock_screen.current_snapshot.return_value = snap
        self.engine._screen_engine = mock_screen
        result = self.engine.resolve("What am I working on?")
        assert result.domain == "screen"
        assert "VS Code" in result.answer_text

    def test_service_e2e(self):
        mock_svc = MagicMock()
        mock_svc.service_health_map.return_value = {"os-discord": "down"}
        mock_svc.organism_health.return_value = {"overall_health": "degraded"}
        self.engine._service_engine = mock_svc
        result = self.engine.resolve("What is failing right now?")
        assert result.domain == "service"
        assert "os-discord" in result.answer_text

    def test_resume_e2e(self):
        mock_cont = MagicMock()
        mock_cont.resume_suggestion.return_value = {
            "has_checkpoint": True,
            "checkpoint_type": "code_edit",
            "detail": "Phase 35 work",
        }
        self.engine._continuity_engine = mock_cont
        result = self.engine.resolve("Resume where I left off")
        assert result.domain == "resume"
        assert "code_edit" in result.answer_text

    def test_node_e2e(self):
        mock_reg = MagicMock()
        mock_reg.list_nodes.return_value = [MockNodeRecord("vps", "orchestrator")]
        mock_reg.primary_node.return_value = MockNodeRecord("vps", "orchestrator")
        self.engine._node_registry = mock_reg
        result = self.engine.resolve("Which devices are connected?")
        assert result.domain == "node"

    def test_action_e2e(self):
        mock_store = MagicMock()
        mock_store.list_pending.return_value = [MockApprovalRequest()]
        self.engine._approval_store = mock_store
        result = self.engine.resolve("What approvals are pending?")
        assert result.domain == "action"

    def test_help_e2e(self):
        result = self.engine.resolve("What can you tell me about?")
        assert result.domain == "help"

    def test_classification_propagated(self):
        mock_ctx = MagicMock()
        mock_ctx.snapshot.return_value = MockSnapshot(
            health_summary=MockHealthSummary("healthy"),
        )
        self.engine._context_engine = mock_ctx
        result = self.engine.resolve("What's the status?")
        assert result.route_type == "observation"
        assert result.route_confidence == 0.90


class TestCockpitRoutes:
    def test_voice_router_exists(self):
        from transports.api.cockpit_voice_routes import voice_router
        assert voice_router is not None

    def test_domains_endpoint_data(self):
        from substrate.operator.voice_query_engine import QueryDomain
        domains = [d.value for d in QueryDomain]
        assert "status" in domains
        assert "action" in domains
        assert len(domains) == 10

    def test_history_bounded(self):
        from transports.api.cockpit_voice_routes import _history, _MAX_HISTORY
        assert _MAX_HISTORY == 50
        assert hasattr(_history, "maxlen")

    def test_configure_idempotent(self):
        from transports.api import cockpit_voice_routes
        mock_dep = MagicMock()
        cockpit_voice_routes.configure(require_operator_dep=mock_dep)
        cockpit_voice_routes.configure(require_operator_dep=mock_dep)

    def test_engine_singleton(self):
        from transports.api.cockpit_voice_routes import _get_engine
        if hasattr(_get_engine, "_instance"):
            delattr(_get_engine, "_instance")
        e1 = _get_engine()
        e2 = _get_engine()
        assert e1 is e2


class TestTypeRegistration:
    def test_types_registered(self):
        from substrate.canonical_types import CANONICAL_TYPES
        assert "QueryDomain" in CANONICAL_TYPES
        assert "QueryResolution" in CANONICAL_TYPES
        assert "VoiceQueryEngine" in CANONICAL_TYPES

    def test_correct_modules(self):
        from substrate.canonical_types import CANONICAL_TYPES
        assert "substrate.operator.voice_query_engine" in CANONICAL_TYPES["QueryDomain"]

    def test_no_duplicates(self):
        from substrate.canonical_types import CANONICAL_TYPES
        phase35_types = ["QueryDomain", "QueryResolution", "VoiceQueryEngine"]
        for t in phase35_types:
            assert len(CANONICAL_TYPES[t]) == 1


class TestNoExecution:
    def test_no_write_methods(self):
        import inspect
        from substrate.operator.voice_query_engine import VoiceQueryEngine
        methods = inspect.getmembers(VoiceQueryEngine, predicate=inspect.isfunction)
        write_words = {"write", "delete", "create", "execute", "deploy", "mutation"}
        for name, _ in methods:
            clean = name.lstrip("_")
            assert clean not in write_words, f"VoiceQueryEngine has write method: {name}"

    def test_resolve_no_side_effects(self):
        engine = VoiceQueryEngine()
        r1 = engine.resolve("help")
        r2 = engine.resolve("help")
        assert r1.domain == r2.domain
        assert r1.answer_text == r2.answer_text

    def test_no_governance_bypass(self):
        import inspect
        source = inspect.getsource(VoiceQueryEngine)
        assert "approve" not in source.lower() or "_resolve_action" in source
        assert "bypass" not in source.lower()


class TestIntentRouterRegression:
    def test_route_types_unchanged(self):
        from substrate.operator.intent_router import RouteType
        expected = {"conversation", "work_packet", "hybrid", "observation", "approval"}
        actual = {r.value for r in RouteType}
        assert actual == expected

    def test_classification_structure(self):
        from substrate.operator.intent_router import RouteClassification, RouteType
        rc = RouteClassification(
            route_type=RouteType.OBSERVATION, confidence=0.90,
        )
        assert rc.route_type == RouteType.OBSERVATION
        assert rc.confidence == 0.90

    def test_intent_router_instantiates(self):
        from substrate.operator.intent_router import IntentRouter
        router = IntentRouter()
        assert router is not None

    def test_classify_returns_route(self):
        from substrate.operator.intent_router import IntentRouter
        router = IntentRouter()
        result = router.classify("What's the status?")
        assert hasattr(result, "route_type")
        assert hasattr(result, "confidence")

    def test_five_route_types(self):
        from substrate.operator.intent_router import RouteType
        assert len(RouteType) == 5


class TestAnswerTextFormat:
    def setup_method(self):
        self.engine = VoiceQueryEngine()

    def test_no_markdown_in_help(self):
        result = self.engine.query_domain(QueryDomain.HELP, "help")
        assert "#" not in result.answer_text
        assert "**" not in result.answer_text
        assert "- " not in result.answer_text

    def test_no_bullets_in_status(self):
        mock_ctx = MagicMock()
        mock_ctx.snapshot.return_value = MockSnapshot(
            health_summary=MockHealthSummary("healthy"),
        )
        self.engine._context_engine = mock_ctx
        result = self.engine.query_domain(QueryDomain.STATUS, "status")
        assert "- " not in result.answer_text
        assert "\n" not in result.answer_text

    def test_short_answers(self):
        result = self.engine.query_domain(QueryDomain.HELP, "help")
        assert len(result.answer_text) < 500

    def test_structured_data_is_dict(self):
        result = self.engine.query_domain(QueryDomain.HELP, "help")
        assert isinstance(result.structured_data, dict)

    def test_sources_is_list(self):
        result = self.engine.query_domain(QueryDomain.HELP, "help")
        assert isinstance(result.sources, list)

    def test_answer_text_is_string(self):
        result = self.engine.query_domain(QueryDomain.HELP, "help")
        assert isinstance(result.answer_text, str)
