"""Tests for W4 — Embodiment Runtime.

Validates intent classification, subsystem routing, persona shaping,
context assembly, and the full intent-to-response pipeline.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from typing import Any

import pytest

sys.path.insert(0, "/opt/OS")

from substrate.organism.embodiment_runtime import (
    EmbodimentContext,
    EmbodimentResponse,
    EmbodimentRuntime,
    IntentClassification,
    IntentType,
    ProcessedIntent,
    RoutingAccuracyReport,
)


# ── Mocks ────────────────────────────────────────────────────────


@dataclass
class MockAssignment:
    assignment_id: str = "fa-mock"
    agent_type: str = "builder"
    compute_node_id: str = "dn-a1b2c3d4"

    def to_dict(self) -> dict:
        return {"assignment_id": self.assignment_id, "agent_type": self.agent_type}


@dataclass
class MockDispatch:
    dispatch_id: str = "fd-mock"
    assignment_id: str = "fa-mock"
    agent_type: str = "builder"
    status: str = "dispatched"

    def to_dict(self) -> dict:
        return {"dispatch_id": self.dispatch_id, "status": self.status}


class MockAgentFleet:
    def __init__(self):
        self._count = 0

    def assign(self, capabilities_required=None, risk_class="low", domain=""):
        self._count += 1
        return MockAssignment(assignment_id=f"fa-{self._count}")

    def dispatch(self, assignment, description=""):
        return MockDispatch(dispatch_id=f"fd-{self._count}", assignment_id=assignment.assignment_id)

    def fleet_status(self):
        @dataclass
        class S:
            active_dispatches: int = 0
        return S(active_dispatches=self._count)


@dataclass
class MockIDEPlan:
    plan_id: str = "idp-mock"
    tasks: list = field(default_factory=lambda: [{"description": "test"}])
    risk_class: str = "low"


class MockMetaIDE:
    def plan_from_intent(self, text):
        return MockIDEPlan()

    def ide_status(self):
        @dataclass
        class S:
            active_streams: int = 1
            pending_reviews: int = 0

            def to_dict(self):
                return {"active_streams": self.active_streams, "pending_reviews": self.pending_reviews}
        return S()


class MockCommandRuntime:
    def classify(self, text):
        from enum import Enum
        class CI(str, Enum):
            MODE_SWITCH = "mode_switch"
        return CI.MODE_SWITCH


class MockPersona:
    def __init__(self):
        self.name = "TestAI"

        @dataclass
        class VP:
            tone: str = "direct"
            pace: str = "fast"
            formality: str = "casual"

        class PS:
            value = "tactical"

        self.voice_profile = VP()
        self.presentation_style = PS()

    @property
    def display_name(self) -> str:
        return self.name if self.name else "UMH"


def _make_emb(**kwargs) -> EmbodimentRuntime:
    return EmbodimentRuntime(**kwargs)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Tests
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestClassification:
    def test_work_intent(self):
        emb = _make_emb()
        c = emb.classify_intent("assign this task and dispatch it")
        assert c.intent_type == IntentType.WORK
        assert c.confidence > 0
        assert "assign" in c.matched_keywords

    def test_development_intent(self):
        emb = _make_emb()
        c = emb.classify_intent("build a new authentication module")
        assert c.intent_type == IntentType.DEVELOPMENT
        assert "build" in c.matched_keywords

    def test_query_intent(self):
        emb = _make_emb()
        c = emb.classify_intent("what is the current status")
        assert c.intent_type == IntentType.QUERY

    def test_command_intent(self):
        emb = _make_emb()
        c = emb.classify_intent("switch mode to production")
        assert c.intent_type == IntentType.COMMAND

    def test_conversation_fallback(self):
        emb = _make_emb()
        c = emb.classify_intent("hello there")
        assert c.intent_type == IntentType.CONVERSATION
        assert c.confidence == 0.5

    def test_classification_to_dict(self):
        emb = _make_emb()
        c = emb.classify_intent("build it")
        d = c.to_dict()
        assert "intent_type" in d
        assert "confidence" in d
        assert "subsystem_target" in d


class TestWorkRouting:
    def test_routes_through_fleet(self):
        fleet = MockAgentFleet()
        emb = _make_emb(agent_fleet=fleet)
        resp = emb.process_intent("assign and execute this task")
        assert resp.subsystem_result.get("routed") is True
        assert resp.subsystem_result.get("subsystem") == "agent_fleet"
        assert resp.lineage_id

    def test_no_fleet_available(self):
        emb = _make_emb()
        resp = emb.process_intent("dispatch this work immediately")
        assert resp.subsystem_result.get("routed") is False


class TestDevelopmentRouting:
    def test_routes_through_ide(self):
        ide = MockMetaIDE()
        emb = _make_emb(meta_ide=ide)
        resp = emb.process_intent("build a new feature for the API")
        assert resp.subsystem_result.get("routed") is True
        assert resp.subsystem_result.get("subsystem") == "meta_ide"
        assert resp.lineage_id

    def test_no_ide_available(self):
        emb = _make_emb()
        resp = emb.process_intent("implement the authentication layer")
        assert resp.subsystem_result.get("routed") is False


class TestQueryRouting:
    def test_query_assembles_data(self):
        fleet = MockAgentFleet()
        ide = MockMetaIDE()
        emb = _make_emb(agent_fleet=fleet, meta_ide=ide)
        resp = emb.process_intent("show me the current status report")
        assert resp.subsystem_result.get("routed") is True
        assert "data" in resp.subsystem_result

    def test_query_no_subsystems(self):
        emb = _make_emb()
        resp = emb.process_intent("what is happening right now")
        assert resp.subsystem_result.get("routed") is True


class TestCommandRouting:
    def test_routes_through_command_runtime(self):
        cmd = MockCommandRuntime()
        emb = _make_emb(command_runtime=cmd)
        resp = emb.process_intent("switch mode now")
        assert resp.subsystem_result.get("routed") is True
        assert resp.subsystem_result.get("command_intent") == "mode_switch"

    def test_no_command_runtime(self):
        emb = _make_emb()
        resp = emb.process_intent("restart the service now")
        assert resp.subsystem_result.get("routed") is False


class TestPersona:
    def test_persona_info_default(self):
        emb = _make_emb()
        info = emb.persona_info()
        assert info["name"] == "UMH"

    def test_persona_info_configured(self):
        persona = MockPersona()
        emb = _make_emb(persona=persona)
        info = emb.persona_info()
        assert info["name"] == "TestAI"
        assert "voice" in info

    def test_update_persona(self):
        persona = MockPersona()
        emb = _make_emb(persona=persona)
        result = emb.update_persona(name="NewName")
        assert result["name"] == "NewName"


class TestResponseShaping:
    def test_shapes_work_response(self):
        fleet = MockAgentFleet()
        emb = _make_emb(agent_fleet=fleet)
        resp = emb.process_intent("assign this task and dispatch")
        assert resp.shaped_response
        assert "dispatch" in resp.shaped_response.lower() or "Work" in resp.shaped_response

    def test_shapes_development_response(self):
        ide = MockMetaIDE()
        emb = _make_emb(meta_ide=ide)
        resp = emb.process_intent("build a new module")
        assert resp.shaped_response
        assert "plan" in resp.shaped_response.lower()


class TestHistory:
    def test_records_history(self):
        emb = _make_emb()
        emb.process_intent("hello")
        emb.process_intent("world")
        history = emb.intent_history()
        assert len(history) == 2

    def test_history_limit(self):
        emb = _make_emb()
        for i in range(10):
            emb.process_intent(f"intent {i}")
        history = emb.intent_history(limit=3)
        assert len(history) == 3

    def test_history_to_dict(self):
        emb = _make_emb()
        emb.process_intent("test")
        h = emb.intent_history()[0]
        d = h.to_dict()
        assert "intent_id" in d
        assert "classification" in d


class TestAccuracy:
    def test_empty_accuracy(self):
        emb = _make_emb()
        report = emb.routing_accuracy()
        assert report.total_processed == 0

    def test_accuracy_after_processing(self):
        emb = _make_emb()
        emb.process_intent("build something")
        emb.process_intent("what is the status")
        emb.process_intent("hello there")
        report = emb.routing_accuracy()
        assert report.total_processed == 3
        assert len(report.by_type) >= 2

    def test_accuracy_to_dict(self):
        emb = _make_emb()
        emb.process_intent("build it")
        d = emb.routing_accuracy().to_dict()
        assert "avg_confidence" in d
        assert "low_confidence_count" in d


class TestContext:
    def test_empty_context(self):
        emb = _make_emb()
        ctx = emb.current_context()
        assert ctx.fleet_active == 0
        assert ctx.ide_active_streams == 0

    def test_context_with_subsystems(self):
        fleet = MockAgentFleet()
        fleet._count = 3
        ide = MockMetaIDE()
        emb = _make_emb(agent_fleet=fleet, meta_ide=ide)
        ctx = emb.current_context()
        assert ctx.fleet_active == 3
        assert ctx.ide_active_streams == 1

    def test_context_to_dict(self):
        emb = _make_emb()
        d = emb.current_context().to_dict()
        assert "fleet_active" in d
        assert "recent_intents" in d


class TestFullPipeline:
    """Acceptance: intent → classify → route → shape → record."""

    def test_full_pipeline(self):
        fleet = MockAgentFleet()
        ide = MockMetaIDE()
        persona = MockPersona()
        emb = _make_emb(agent_fleet=fleet, meta_ide=ide, persona=persona)

        resp = emb.process_intent("build a health check endpoint")
        assert resp.intent_classification.intent_type == IntentType.DEVELOPMENT
        assert resp.subsystem_result.get("routed") is True
        assert resp.shaped_response
        assert resp.lineage_id

        history = emb.intent_history()
        assert len(history) == 1
        assert history[0].text == "build a health check endpoint"

        report = emb.routing_accuracy()
        assert report.total_processed == 1
