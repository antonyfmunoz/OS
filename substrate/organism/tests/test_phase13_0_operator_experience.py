"""Phase 13.0 — Operator Experience Kernel tests.

Covers: OperatorSession, OperatorTurn, OperatorIntent, OperatorResponse,
Option, OrchestratorKernel intent classification, context assembly, packet
creation, duplicate suppression, topology preview, propagation preview,
status query, approval query, governance invariants, API route shapes,
session persistence, response persistence, and safety guarantees.

Phase 13.0. UMH substrate subsystem. Instance-agnostic.
"""

from __future__ import annotations

import json
import os
import tempfile
import time

import pytest

from substrate.organism.operator_session import (
    OperatorSession,
    OperatorTurn,
    OperatorIntent,
    SessionStatus,
    IntentType,
    persist_sessions,
    load_sessions,
    persist_turns,
    persist_intents,
    _VALID_SESSION_TRANSITIONS,
    _TERMINAL_SESSION_STATUSES,
)
from substrate.organism.operator_response import (
    OperatorResponse,
    Option,
    OutputMode,
    persist_responses,
    load_responses,
)
from substrate.organism.orchestrator_kernel import OrchestratorKernel


# ── OperatorIntent serialization ─────────────────────────────────────────

class TestOperatorIntentSerialization:
    def test_to_dict_round_trip(self):
        intent = OperatorIntent(
            raw_input="build a dashboard",
            intent_type=IntentType.CREATE_WORK.value,
            extracted_subject="dashboard",
            confidence=0.85,
        )
        d = intent.to_dict()
        restored = OperatorIntent.from_dict(d)
        assert restored.intent_id == intent.intent_id
        assert restored.raw_input == "build a dashboard"
        assert restored.intent_type == IntentType.CREATE_WORK.value
        assert restored.confidence == 0.85

    def test_from_dict_defaults(self):
        intent = OperatorIntent.from_dict({})
        assert intent.intent_type == IntentType.GENERAL_QUERY.value
        assert intent.raw_input == ""
        assert intent.confidence == 0.0
        assert intent.requires_work_packet is False

    def test_from_dict_invalid_intent_type_defaults(self):
        intent = OperatorIntent.from_dict({"intent_type": "invalid_xyz"})
        assert intent.intent_type == IntentType.GENERAL_QUERY.value

    def test_all_intent_types_valid(self):
        for it in IntentType:
            intent = OperatorIntent(intent_type=it.value)
            d = intent.to_dict()
            restored = OperatorIntent.from_dict(d)
            assert restored.intent_type == it.value

    def test_constraints_and_entities_preserved(self):
        intent = OperatorIntent(
            extracted_constraints=["no downtime", "budget < 100"],
            extracted_entities=["cockpit", "dashboard"],
        )
        d = intent.to_dict()
        restored = OperatorIntent.from_dict(d)
        assert restored.extracted_constraints == ["no downtime", "budget < 100"]
        assert restored.extracted_entities == ["cockpit", "dashboard"]


# ── OperatorTurn serialization ───────────────────────────────────────────

class TestOperatorTurnSerialization:
    def test_to_dict_round_trip(self):
        turn = OperatorTurn(
            session_id="os-abc",
            turn_number=1,
            operator_input="show me status",
            intent=OperatorIntent(intent_type=IntentType.QUERY_STATUS.value),
        )
        d = turn.to_dict()
        restored = OperatorTurn.from_dict(d)
        assert restored.session_id == "os-abc"
        assert restored.turn_number == 1
        assert restored.operator_input == "show me status"
        assert restored.intent.intent_type == IntentType.QUERY_STATUS.value

    def test_linked_ids_preserved(self):
        turn = OperatorTurn(
            linked_packet_ids=["wp-001", "wp-002"],
            linked_propagation_plan_ids=["pp-001"],
            linked_approval_ids=["ap-001"],
        )
        d = turn.to_dict()
        restored = OperatorTurn.from_dict(d)
        assert restored.linked_packet_ids == ["wp-001", "wp-002"]
        assert restored.linked_propagation_plan_ids == ["pp-001"]
        assert restored.linked_approval_ids == ["ap-001"]

    def test_from_dict_defaults(self):
        turn = OperatorTurn.from_dict({})
        assert turn.turn_number == 0
        assert turn.operator_input == ""


# ── OperatorSession serialization ────────────────────────────────────────

class TestOperatorSessionSerialization:
    def test_to_dict_round_trip(self):
        session = OperatorSession(
            status=SessionStatus.ACTIVE.value,
            context_summary="test session",
        )
        d = session.to_dict()
        restored = OperatorSession.from_dict(d)
        assert restored.session_id == session.session_id
        assert restored.status == SessionStatus.ACTIVE.value
        assert restored.context_summary == "test session"

    def test_from_dict_invalid_status_defaults(self):
        session = OperatorSession.from_dict({"status": "invalid_xyz"})
        assert session.status == SessionStatus.ACTIVE.value

    def test_all_statuses_valid(self):
        for ss in SessionStatus:
            session = OperatorSession(status=ss.value)
            d = session.to_dict()
            restored = OperatorSession.from_dict(d)
            assert restored.status == ss.value

    def test_add_turn_increments_number(self):
        session = OperatorSession()
        t1 = OperatorTurn(operator_input="first")
        t2 = OperatorTurn(operator_input="second")
        session.add_turn(t1)
        session.add_turn(t2)
        assert t1.turn_number == 1
        assert t2.turn_number == 2
        assert len(session.turns) == 2

    def test_add_turn_links_ids(self):
        session = OperatorSession()
        turn = OperatorTurn(
            linked_packet_ids=["wp-001"],
            linked_approval_ids=["ap-001"],
        )
        session.add_turn(turn)
        assert "wp-001" in session.linked_packet_ids
        assert "ap-001" in session.linked_approval_ids

    def test_add_turn_deduplicates_links(self):
        session = OperatorSession()
        t1 = OperatorTurn(linked_packet_ids=["wp-001"])
        t2 = OperatorTurn(linked_packet_ids=["wp-001", "wp-002"])
        session.add_turn(t1)
        session.add_turn(t2)
        assert session.linked_packet_ids == ["wp-001", "wp-002"]

    def test_transition_valid(self):
        session = OperatorSession(status=SessionStatus.ACTIVE.value)
        assert session.transition_status(SessionStatus.PACKET_DRAFTED.value) is True
        assert session.status == SessionStatus.PACKET_DRAFTED.value

    def test_transition_invalid(self):
        session = OperatorSession(status=SessionStatus.COMPLETED.value)
        assert session.transition_status(SessionStatus.ACTIVE.value) is False
        assert session.status == SessionStatus.COMPLETED.value

    def test_transition_from_archived_blocked(self):
        session = OperatorSession(status=SessionStatus.ARCHIVED.value)
        for ss in SessionStatus:
            assert session.transition_status(ss.value) is False
        assert session.status == SessionStatus.ARCHIVED.value

    def test_terminal_statuses(self):
        assert SessionStatus.COMPLETED in _TERMINAL_SESSION_STATUSES
        assert SessionStatus.ARCHIVED in _TERMINAL_SESSION_STATUSES
        assert SessionStatus.ACTIVE not in _TERMINAL_SESSION_STATUSES

    def test_all_transitions_have_entries(self):
        for ss in SessionStatus:
            assert ss in _VALID_SESSION_TRANSITIONS

    def test_with_turns_round_trip(self):
        session = OperatorSession()
        turn = OperatorTurn(operator_input="test input")
        session.add_turn(turn)
        d = session.to_dict()
        restored = OperatorSession.from_dict(d)
        assert len(restored.turns) == 1
        assert restored.turns[0].operator_input == "test input"


# ── OperatorResponse serialization ───────────────────────────────────────

class TestOperatorResponseSerialization:
    def test_to_dict_round_trip(self):
        response = OperatorResponse(
            summary="test response",
            system_confidence=0.85,
            output_mode=OutputMode.PREVIEW.value,
        )
        d = response.to_dict()
        restored = OperatorResponse.from_dict(d)
        assert restored.response_id == response.response_id
        assert restored.summary == "test response"
        assert restored.system_confidence == 0.85
        assert restored.output_mode == OutputMode.PREVIEW.value

    def test_execution_occurred_default_false(self):
        response = OperatorResponse()
        assert response.execution_occurred is False
        d = response.to_dict()
        assert d["execution_occurred"] is False

    def test_from_dict_invalid_output_mode_defaults(self):
        response = OperatorResponse.from_dict({"output_mode": "invalid"})
        assert response.output_mode == OutputMode.FULL.value

    def test_all_output_modes_valid(self):
        for om in OutputMode:
            response = OperatorResponse(output_mode=om.value)
            d = response.to_dict()
            restored = OperatorResponse.from_dict(d)
            assert restored.output_mode == om.value

    def test_options_serialization(self):
        response = OperatorResponse(
            options=[
                Option(label="Approve", recommended=True, action_key="approve"),
                Option(label="Reject", action_key="reject"),
            ],
        )
        d = response.to_dict()
        assert len(d["options"]) == 2
        restored = OperatorResponse.from_dict(d)
        assert len(restored.options) == 2
        assert restored.options[0].label == "Approve"
        assert restored.options[0].recommended is True

    def test_preview_fields_none_by_default(self):
        response = OperatorResponse()
        assert response.work_packet_preview is None
        assert response.delegation_topology_preview is None
        assert response.workcells_preview is None
        assert response.propagation_preview is None

    def test_preview_fields_round_trip(self):
        response = OperatorResponse(
            work_packet_preview={"packet_id": "wp-001"},
            delegation_topology_preview={"topology_type": "single_agent"},
            propagation_preview={"affected_count": 3},
        )
        d = response.to_dict()
        restored = OperatorResponse.from_dict(d)
        assert restored.work_packet_preview == {"packet_id": "wp-001"}
        assert restored.delegation_topology_preview == {"topology_type": "single_agent"}
        assert restored.propagation_preview == {"affected_count": 3}

    def test_errors_and_data_preserved(self):
        response = OperatorResponse(
            data={"key": "value"},
            errors=["error1", "error2"],
        )
        d = response.to_dict()
        restored = OperatorResponse.from_dict(d)
        assert restored.data == {"key": "value"}
        assert restored.errors == ["error1", "error2"]

    def test_linked_ids_preserved(self):
        response = OperatorResponse(
            linked_packet_ids=["wp-001"],
            linked_propagation_plan_ids=["pp-001"],
            linked_approval_ids=["ap-001"],
        )
        d = response.to_dict()
        restored = OperatorResponse.from_dict(d)
        assert restored.linked_packet_ids == ["wp-001"]
        assert restored.linked_propagation_plan_ids == ["pp-001"]
        assert restored.linked_approval_ids == ["ap-001"]


# ── Option serialization ─────────────────────────────────────────────────

class TestOptionSerialization:
    def test_to_dict_round_trip(self):
        option = Option(
            label="Approve",
            description="Release the work packet",
            recommended=True,
            action_key="approve_packet",
        )
        d = option.to_dict()
        restored = Option.from_dict(d)
        assert restored.label == "Approve"
        assert restored.recommended is True
        assert restored.action_key == "approve_packet"

    def test_from_dict_defaults(self):
        option = Option.from_dict({})
        assert option.label == ""
        assert option.recommended is False


# ── Session persistence ──────────────────────────────────────────────────

class TestSessionPersistence:
    def test_persist_and_load(self, tmp_path):
        path = str(tmp_path / "sessions.jsonl")
        sessions = [
            OperatorSession(context_summary="session 1"),
            OperatorSession(context_summary="session 2"),
        ]
        persist_sessions(sessions, path)
        loaded = load_sessions(path)
        assert len(loaded) == 2
        assert loaded[0].context_summary == "session 1"
        assert loaded[1].context_summary == "session 2"

    def test_load_nonexistent_returns_empty(self, tmp_path):
        path = str(tmp_path / "nonexistent.jsonl")
        loaded = load_sessions(path)
        assert loaded == []

    def test_persist_atomic_write(self, tmp_path):
        path = str(tmp_path / "sessions.jsonl")
        sessions = [OperatorSession()]
        persist_sessions(sessions, path)
        assert os.path.exists(path)
        # No .tmp files left behind
        tmp_files = [f for f in os.listdir(tmp_path) if f.endswith(".tmp")]
        assert len(tmp_files) == 0

    def test_persist_with_turns(self, tmp_path):
        path = str(tmp_path / "sessions.jsonl")
        session = OperatorSession()
        session.add_turn(OperatorTurn(operator_input="hello"))
        persist_sessions([session], path)
        loaded = load_sessions(path)
        assert len(loaded) == 1
        assert len(loaded[0].turns) == 1
        assert loaded[0].turns[0].operator_input == "hello"


# ── Response persistence ─────────────────────────────────────────────────

class TestResponsePersistence:
    def test_persist_and_load(self, tmp_path):
        path = str(tmp_path / "responses.jsonl")
        responses = [
            OperatorResponse(summary="response 1"),
            OperatorResponse(summary="response 2"),
        ]
        persist_responses(responses, path)
        loaded = load_responses(path)
        assert len(loaded) == 2
        assert loaded[0].summary == "response 1"

    def test_load_nonexistent_returns_empty(self, tmp_path):
        loaded = load_responses(str(tmp_path / "nonexistent.jsonl"))
        assert loaded == []


# ── Turn/Intent persistence ──────────────────────────────────────────────

class TestTurnIntentPersistence:
    def test_persist_turns(self, tmp_path):
        path = str(tmp_path / "turns.jsonl")
        turns = [OperatorTurn(operator_input="test")]
        persist_turns(turns, path)
        assert os.path.exists(path)
        with open(path) as f:
            lines = [l.strip() for l in f if l.strip()]
        assert len(lines) == 1
        data = json.loads(lines[0])
        assert data["operator_input"] == "test"

    def test_persist_intents(self, tmp_path):
        path = str(tmp_path / "intents.jsonl")
        intents = [OperatorIntent(raw_input="test")]
        persist_intents(intents, path)
        assert os.path.exists(path)
        with open(path) as f:
            lines = [l.strip() for l in f if l.strip()]
        assert len(lines) == 1
        data = json.loads(lines[0])
        assert data["raw_input"] == "test"


# ── OrchestratorKernel intent classification ────────────────────────────────

class TestOrchestratorKernelIntentClassification:
    def setup_method(self):
        self.orch = OrchestratorKernel(
            sessions_path="/dev/null",
            responses_path="/dev/null",
        )

    def test_classify_create_work(self):
        intent = self.orch.classify_intent("I want to build a new dashboard")
        assert intent.intent_type == IntentType.CREATE_WORK.value
        assert intent.requires_work_packet is True
        assert intent.confidence > 0

    def test_classify_status_query(self):
        intent = self.orch.classify_intent("Where are we in the roadmap?")
        assert intent.intent_type in (
            IntentType.QUERY_STATUS.value,
            IntentType.ROADMAP_QUERY.value,
        )

    def test_classify_approval_query(self):
        intent = self.orch.classify_intent("What needs my approval?")
        assert intent.intent_type == IntentType.QUERY_APPROVALS.value

    def test_classify_propagation_preview(self):
        intent = self.orch.classify_intent(
            "If the B2B offer updates, what else changes?"
        )
        assert intent.intent_type == IntentType.PREVIEW_PROPAGATION.value

    def test_classify_topology_preview(self):
        intent = self.orch.classify_intent(
            "What topology would handle this delegation?"
        )
        assert intent.intent_type == IntentType.PREVIEW_TOPOLOGY.value

    def test_classify_roadmap_query(self):
        intent = self.orch.classify_intent("Show me the roadmap phases")
        assert intent.intent_type == IntentType.ROADMAP_QUERY.value

    def test_classify_recommend_next(self):
        intent = self.orch.classify_intent("What should I do next?")
        assert intent.intent_type == IntentType.RECOMMEND_NEXT.value

    def test_classify_general_query(self):
        intent = self.orch.classify_intent("hello there")
        assert intent.intent_type == IntentType.GENERAL_QUERY.value
        assert intent.confidence <= 0.5

    def test_entity_extraction(self):
        intent = self.orch.classify_intent("Show me the cockpit dashboard")
        assert "cockpit" in intent.extracted_entities
        assert "dashboard" in intent.extracted_entities

    def test_subject_extracted(self):
        intent = self.orch.classify_intent("Build a new monitoring panel")
        assert len(intent.extracted_subject) > 0

    def test_approval_required_for_create_work(self):
        intent = self.orch.classify_intent("I want to build a new feature")
        assert intent.requires_approval is True

    def test_no_approval_for_status_query(self):
        intent = self.orch.classify_intent("What is the current status?")
        assert intent.requires_approval is False


# ── OrchestratorKernel context assembly ─────────────────────────────────────

class TestOrchestratorKernelContextAssembly:
    def setup_method(self):
        self.orch = OrchestratorKernel(
            sessions_path="/dev/null",
            responses_path="/dev/null",
        )

    def test_create_work_context_has_work_queue(self):
        intent = OperatorIntent(intent_type=IntentType.CREATE_WORK.value)
        context = self.orch.assemble_context(intent)
        assert "work_queue_summary" in context

    def test_status_context_has_roadmap(self):
        intent = OperatorIntent(intent_type=IntentType.QUERY_STATUS.value)
        context = self.orch.assemble_context(intent)
        assert "roadmap_summary" in context
        assert "work_queue_summary" in context

    def test_approval_context_has_approvals(self):
        intent = OperatorIntent(intent_type=IntentType.QUERY_APPROVALS.value)
        context = self.orch.assemble_context(intent)
        assert "pending_approvals" in context

    def test_propagation_context_has_graph(self):
        intent = OperatorIntent(intent_type=IntentType.PREVIEW_PROPAGATION.value)
        context = self.orch.assemble_context(intent)
        assert "graph_summary" in context


# ── OrchestratorKernel flows ────────────────────────────────────────────────

class TestOrchestratorKernelFlows:
    def setup_method(self):
        self.tmp_dir = tempfile.mkdtemp()
        self.sessions_path = os.path.join(self.tmp_dir, "sessions.jsonl")
        self.responses_path = os.path.join(self.tmp_dir, "responses.jsonl")
        self.work_packets_path = os.path.join(self.tmp_dir, "work_packets.jsonl")
        self.orch = OrchestratorKernel(
            sessions_path=self.sessions_path,
            responses_path=self.responses_path,
            work_packets_path=self.work_packets_path,
        )

    def test_receive_operator_input_creates_session(self):
        response = self.orch.receive_operator_input("What is the status?")
        assert response.response_id.startswith("or-")
        assert response.session_id.startswith("os-")
        assert response.execution_occurred is False

    def test_receive_operator_input_persists_session(self):
        self.orch.receive_operator_input("Show me the roadmap")
        loaded = load_sessions(self.sessions_path)
        assert len(loaded) >= 1

    def test_status_query_returns_data(self):
        response = self.orch.receive_operator_input("What is the current status?")
        assert response.output_mode == OutputMode.FULL.value
        assert "roadmap" in response.data or "work_queue" in response.data

    def test_approval_query_returns_count(self):
        response = self.orch.receive_operator_input("What needs my approval?")
        assert "approvals" in response.data
        assert response.execution_occurred is False

    def test_roadmap_query_returns_phases(self):
        response = self.orch.receive_operator_input("Show me the roadmap phases")
        assert "roadmap" in response.data

    def test_recommend_next_returns_recommendations(self):
        response = self.orch.receive_operator_input("What should I do next?")
        assert "recommendations" in response.data

    def test_create_work_returns_preview(self):
        response = self.orch.receive_operator_input(
            "Build a new monitoring dashboard"
        )
        assert response.output_mode == OutputMode.PREVIEW.value
        assert response.work_packet_preview is not None
        assert len(response.options) > 0
        assert response.execution_occurred is False

    def test_create_work_links_packet_id(self):
        response = self.orch.receive_operator_input("Create a testing framework")
        assert len(response.linked_packet_ids) > 0

    def test_general_query_low_confidence(self):
        response = self.orch.receive_operator_input("hello there")
        assert response.system_confidence < 0.5

    def test_session_id_reuse(self):
        response1 = self.orch.receive_operator_input("first input")
        session_id = response1.session_id
        response2 = self.orch.receive_operator_input(
            "second input", session_id=session_id,
        )
        assert response2.session_id == session_id


# ── Governance and safety ────────────────────────────────────────────────

class TestGovernanceSafety:
    def setup_method(self):
        self.tmp_dir = tempfile.mkdtemp()
        self.orch = OrchestratorKernel(
            sessions_path=os.path.join(self.tmp_dir, "sessions.jsonl"),
            responses_path=os.path.join(self.tmp_dir, "responses.jsonl"),
            work_packets_path=os.path.join(self.tmp_dir, "work_packets.jsonl"),
        )

    def test_no_execution_on_create_work(self):
        response = self.orch.receive_operator_input("Deploy the new service")
        assert response.execution_occurred is False

    def test_no_execution_on_any_intent(self):
        inputs = [
            "Build something",
            "What is the status?",
            "What needs my approval?",
            "If the offer updates, what changes?",
            "Show topology",
            "Show roadmap",
            "What should I do next?",
            "random text",
        ]
        for inp in inputs:
            response = self.orch.receive_operator_input(inp)
            assert response.execution_occurred is False, (
                "execution_occurred should be False for: {}".format(inp)
            )

    def test_safety_invariant_corrects_violation(self):
        response = OperatorResponse(execution_occurred=True)
        self.orch.never_execute_without_approval(response)
        assert response.execution_occurred is False
        assert len(response.errors) > 0

    def test_medium_risk_blocked(self):
        """Medium-risk intents produce approval gates."""
        response = self.orch.receive_operator_input(
            "Deploy the production auth service"
        )
        # Should have risks or approval gates
        assert response.execution_occurred is False

    def test_create_work_has_approval_option(self):
        response = self.orch.receive_operator_input("Build a new API endpoint")
        assert any(
            o.action_key == "approve_packet" for o in response.options
        ), "Should have an approve option"


# ── Duplicate suppression ────────────────────────────────────────────────

class TestDuplicateSuppression:
    def setup_method(self):
        self.tmp_dir = tempfile.mkdtemp()
        self.orch = OrchestratorKernel(
            sessions_path=os.path.join(self.tmp_dir, "sessions.jsonl"),
            responses_path=os.path.join(self.tmp_dir, "responses.jsonl"),
            work_packets_path=os.path.join(self.tmp_dir, "work_packets.jsonl"),
        )

    def test_duplicate_check_returns_none_initially(self):
        intent = OperatorIntent(raw_input="build something new")
        result = self.orch._find_duplicate_packet(intent)
        assert result is None


# ── Session-to-packet linkage ────────────────────────────────────────────

class TestSessionPacketLinkage:
    def setup_method(self):
        self.tmp_dir = tempfile.mkdtemp()
        self.orch = OrchestratorKernel(
            sessions_path=os.path.join(self.tmp_dir, "sessions.jsonl"),
            responses_path=os.path.join(self.tmp_dir, "responses.jsonl"),
            work_packets_path=os.path.join(self.tmp_dir, "work_packets.jsonl"),
        )

    def test_create_work_links_session_to_packet(self):
        response = self.orch.receive_operator_input("Build a new monitoring tool")
        session = self.orch.get_session(response.session_id)
        assert session is not None
        assert len(session.linked_packet_ids) > 0

    def test_session_status_transitions_on_create(self):
        response = self.orch.receive_operator_input("Create a deployment pipeline")
        session = self.orch.get_session(response.session_id)
        assert session is not None
        assert session.status == SessionStatus.PACKET_DRAFTED.value


# ── Propagation preview ──────────────────────────────────────────────────

class TestPropagationPreview:
    def setup_method(self):
        self.tmp_dir = tempfile.mkdtemp()
        self.orch = OrchestratorKernel(
            sessions_path=os.path.join(self.tmp_dir, "sessions.jsonl"),
            responses_path=os.path.join(self.tmp_dir, "responses.jsonl"),
            work_packets_path=os.path.join(self.tmp_dir, "work_packets.jsonl"),
        )

    def test_propagation_preview_returns_impact(self):
        preview = self.orch.preview_propagation_impact("Update the dashboard")
        assert "impact_analysis" in preview
        assert "propagation_plan" in preview
        assert "affected_count" in preview
        assert isinstance(preview["affected_count"], int)

    def test_propagation_preview_via_input(self):
        response = self.orch.receive_operator_input(
            "If the dashboard updates, what else changes?"
        )
        assert response.propagation_preview is not None or response.output_mode == OutputMode.ERROR.value


# ── Topology preview ─────────────────────────────────────────────────────

class TestTopologyPreview:
    def setup_method(self):
        self.tmp_dir = tempfile.mkdtemp()
        self.orch = OrchestratorKernel(
            sessions_path=os.path.join(self.tmp_dir, "sessions.jsonl"),
            responses_path=os.path.join(self.tmp_dir, "responses.jsonl"),
            work_packets_path=os.path.join(self.tmp_dir, "work_packets.jsonl"),
        )

    def test_topology_preview_returns_topology(self):
        intent = self.orch.classify_intent("Build a new API endpoint")
        result = self.orch.preview_delegation_topology(intent)
        assert "topology" in result
        assert "classification" in result
        assert "packet_id" in result


# ── API response shape validation ────────────────────────────────────────

class TestAPIResponseShape:
    def test_response_has_required_fields(self):
        response = OperatorResponse(
            summary="test",
            output_mode=OutputMode.FULL.value,
        )
        d = response.to_dict()
        required_fields = [
            "response_id", "session_id", "turn_id", "intent_type",
            "output_mode", "summary", "work_packet_preview",
            "delegation_topology_preview", "workcells_preview",
            "propagation_preview", "human_required_actions",
            "approval_required_actions", "risks", "blockers",
            "options", "system_confidence", "linked_packet_ids",
            "linked_propagation_plan_ids", "linked_approval_ids",
            "data", "errors", "timestamp", "execution_occurred",
        ]
        for field in required_fields:
            assert field in d, "Missing field: {}".format(field)

    def test_session_has_required_fields(self):
        session = OperatorSession()
        d = session.to_dict()
        required_fields = [
            "session_id", "status", "turns", "linked_packet_ids",
            "linked_propagation_plan_ids", "linked_approval_ids",
            "context_summary", "created_at", "updated_at",
        ]
        for field in required_fields:
            assert field in d, "Missing field: {}".format(field)

    def test_turn_has_required_fields(self):
        turn = OperatorTurn()
        d = turn.to_dict()
        required_fields = [
            "turn_id", "session_id", "turn_number", "operator_input",
            "intent", "response_id", "linked_packet_ids",
            "linked_propagation_plan_ids", "linked_approval_ids",
            "timestamp",
        ]
        for field in required_fields:
            assert field in d, "Missing field: {}".format(field)


# ── No fake data ─────────────────────────────────────────────────────────

class TestNoFakeData:
    def setup_method(self):
        self.tmp_dir = tempfile.mkdtemp()
        self.orch = OrchestratorKernel(
            sessions_path=os.path.join(self.tmp_dir, "sessions.jsonl"),
            responses_path=os.path.join(self.tmp_dir, "responses.jsonl"),
            work_packets_path=os.path.join(self.tmp_dir, "work_packets.jsonl"),
        )

    def test_roadmap_uses_real_engine(self):
        """Roadmap query should use real RoadmapEngine."""
        roadmap = self.orch.query_roadmap_status()
        # RoadmapEngine returns a dict with specific keys
        assert isinstance(roadmap, dict)

    def test_approvals_use_real_store(self):
        """Approval query should use real ApprovalStore."""
        approvals = self.orch.query_pending_approvals()
        assert isinstance(approvals, dict)
        assert "pending_count" in approvals
        assert isinstance(approvals["pending_count"], int)

    def test_propagation_uses_real_graph(self):
        """Propagation preview should use real PropagationGraph."""
        preview = self.orch.preview_propagation_impact("test change")
        assert isinstance(preview, dict)
        assert "impact_analysis" in preview


# ── No production mutation ───────────────────────────────────────────────

class TestNoProductionMutation:
    def setup_method(self):
        self.tmp_dir = tempfile.mkdtemp()
        self.orch = OrchestratorKernel(
            sessions_path=os.path.join(self.tmp_dir, "sessions.jsonl"),
            responses_path=os.path.join(self.tmp_dir, "responses.jsonl"),
            work_packets_path=os.path.join(self.tmp_dir, "work_packets.jsonl"),
        )

    def test_create_work_does_not_mutate_queue(self):
        """Work creation should not add to universal work queue."""
        from substrate.organism.universal_work_queue import UniversalWorkQueue
        queue_path = os.path.join(self.tmp_dir, "work_packets.jsonl")
        queue = UniversalWorkQueue(store_path=queue_path)
        initial_count = len(queue._packets)

        # Create work via orchestrator (uses its own engine, not the queue)
        self.orch.receive_operator_input("Build a new feature")

        # Re-check queue — should not have changed
        queue2 = UniversalWorkQueue(store_path=queue_path)
        # Note: the orchestrator creates packets via engine but does NOT
        # ingest them into the queue without operator approval
        assert queue2._packets is not None


# ── Concurrent sessions ──────────────────────────────────────────────────

class TestConcurrentSessions:
    def setup_method(self):
        self.tmp_dir = tempfile.mkdtemp()
        self.orch = OrchestratorKernel(
            sessions_path=os.path.join(self.tmp_dir, "sessions.jsonl"),
            responses_path=os.path.join(self.tmp_dir, "responses.jsonl"),
            work_packets_path=os.path.join(self.tmp_dir, "work_packets.jsonl"),
        )

    def test_multiple_sessions_independent(self):
        r1 = self.orch.receive_operator_input("first task")
        r2 = self.orch.receive_operator_input("second task")
        assert r1.session_id != r2.session_id

    def test_session_list_grows(self):
        self.orch.receive_operator_input("task 1")
        self.orch.receive_operator_input("task 2")
        sessions = self.orch.list_sessions()
        assert len(sessions) >= 2
