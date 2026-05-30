import sys

import pytest
from uuid import UUID
from pydantic import ValidationError

from substrate.types import (
    SignalEnvelope,
    SignalSource,
    SignalUrgency,
    Modality,
    Identity,
    ExecutionContext,
    RiskClass,
    GovernanceDecision,
    GovernanceVerdict,
    ExecutionPlan,
    AdapterResponse,
    ExecutionOutcome,
    ExecutionResult,
    TraceEventType,
    TraceEvent,
    TraceRecord,
    FeedbackType,
    FeedbackRecord,
    MemoryType,
    MemoryQuery,
    MemoryEntry,
    ComponentType,
    ComponentStatus,
    Component,
    RegistrationResult,
    PrimitiveType,
    OntologicalCategory,
    RelationshipType,
    PrimitiveObservation,
    IngestionResult,
    SubstrateStatus,
    Attachment,
    AdapterRequest,
)


class TestSignalEnvelope:
    def test_requires_source_and_content(self):
        env = SignalEnvelope(
            source=SignalSource.USER,
            content="hello",
            user_id="u1",
            organization_id="org1",
        )
        assert isinstance(env.id, UUID)
        assert env.content == "hello"

    def test_authority_tier_range(self):
        with pytest.raises(ValidationError):
            SignalEnvelope(
                source=SignalSource.USER,
                content="x",
                user_id="u",
                organization_id="o",
                authority_tier=0,
            )
        with pytest.raises(ValidationError):
            SignalEnvelope(
                source=SignalSource.USER,
                content="x",
                user_id="u",
                organization_id="o",
                authority_tier=10,
            )
        env = SignalEnvelope(
            source=SignalSource.USER,
            content="x",
            user_id="u",
            organization_id="o",
            authority_tier=1,
        )
        assert env.authority_tier == 1


class TestGovernanceVerdict:
    def test_approve_is_executable(self):
        v = GovernanceVerdict(
            signal_id=UUID("12345678-1234-1234-1234-123456789abc"),
            risk_class=RiskClass.LOW,
            decision=GovernanceDecision.APPROVE,
            rationale="low risk",
        )
        assert v.is_executable() is True

    def test_deny_is_not_executable(self):
        v = GovernanceVerdict(
            signal_id=UUID("12345678-1234-1234-1234-123456789abc"),
            risk_class=RiskClass.CRITICAL,
            decision=GovernanceDecision.DENY,
            rationale="too risky",
        )
        assert v.is_executable() is False

    def test_conditional_is_not_executable(self):
        v = GovernanceVerdict(
            signal_id=UUID("12345678-1234-1234-1234-123456789abc"),
            risk_class=RiskClass.HIGH,
            decision=GovernanceDecision.CONDITIONAL,
            rationale="needs conditions",
            conditions=["approval from founder"],
        )
        assert v.is_executable() is False


class TestExecutionResult:
    def test_success_is_success(self):
        r = ExecutionResult(
            signal_id=UUID("12345678-1234-1234-1234-123456789abc"),
            trace_id=UUID("12345678-1234-1234-1234-123456789def"),
            outcome=ExecutionOutcome.SUCCESS,
        )
        assert r.is_success() is True

    def test_partial_success_is_success(self):
        r = ExecutionResult(
            signal_id=UUID("12345678-1234-1234-1234-123456789abc"),
            trace_id=UUID("12345678-1234-1234-1234-123456789def"),
            outcome=ExecutionOutcome.PARTIAL_SUCCESS,
        )
        assert r.is_success() is True

    def test_failure_is_not_success(self):
        r = ExecutionResult(
            signal_id=UUID("12345678-1234-1234-1234-123456789abc"),
            trace_id=UUID("12345678-1234-1234-1234-123456789def"),
            outcome=ExecutionOutcome.FAILURE,
        )
        assert r.is_success() is False

    def test_blocked_is_not_success(self):
        r = ExecutionResult(
            signal_id=UUID("12345678-1234-1234-1234-123456789abc"),
            trace_id=UUID("12345678-1234-1234-1234-123456789def"),
            outcome=ExecutionOutcome.BLOCKED,
        )
        assert r.is_success() is False


class TestTraceRecord:
    def test_add_event(self):
        t = TraceRecord(signal_id=UUID("12345678-1234-1234-1234-123456789abc"))
        ev = t.add_event(TraceEventType.SIGNAL_RECEIVED, "signal received")
        assert ev.trace_id == t.id
        assert len(t.events) == 1

    def test_complete(self):
        t = TraceRecord(signal_id=UUID("12345678-1234-1234-1234-123456789abc"))
        t.complete(success=True)
        assert t.success is True
        assert t.completed_at is not None
        assert t.duration_ms is not None
        assert t.duration_ms >= 0


class TestEnumCounts:
    def test_primitive_type_has_10_values(self):
        assert len(PrimitiveType) == 10

    def test_ontological_category_has_8_values(self):
        assert len(OntologicalCategory) == 8

    def test_relationship_type_has_10_values(self):
        assert len(RelationshipType) == 10

    def test_signal_source_has_8_values(self):
        assert len(SignalSource) == 8

    def test_trace_event_type_has_19_values(self):
        assert len(TraceEventType) == 19


class TestMemoryQuery:
    def test_limit_range(self):
        with pytest.raises(ValidationError):
            MemoryQuery(query_text="test", limit=0)
        with pytest.raises(ValidationError):
            MemoryQuery(query_text="test", limit=101)
        q = MemoryQuery(query_text="test", limit=50)
        assert q.limit == 50


class TestFeedbackRecord:
    def test_quality_range(self):
        with pytest.raises(ValidationError):
            FeedbackRecord(
                trace_id=UUID("12345678-1234-1234-1234-123456789abc"),
                signal_id=UUID("12345678-1234-1234-1234-123456789abc"),
                outcome_quality=-0.1,
            )
        with pytest.raises(ValidationError):
            FeedbackRecord(
                trace_id=UUID("12345678-1234-1234-1234-123456789abc"),
                signal_id=UUID("12345678-1234-1234-1234-123456789abc"),
                outcome_quality=1.1,
            )
        f = FeedbackRecord(
            trace_id=UUID("12345678-1234-1234-1234-123456789abc"),
            signal_id=UUID("12345678-1234-1234-1234-123456789abc"),
            outcome_quality=0.75,
        )
        assert f.outcome_quality == 0.75
