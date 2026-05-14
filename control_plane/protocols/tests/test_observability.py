"""Tests for umh.protocols.observability."""

import pytest
from pydantic import ValidationError

from control_plane.protocols.observability import (
    ExecutionResult,
    GovernanceDecision,
    Outcome,
    ParityResult,
    ProofArtifact,
    TimestampSet,
    Trace,
    WorldStateSnapshot,
)
from control_plane.protocols.common import (
    AuthorityLevel,
    ConfirmationStatus,
    EvidenceType,
    RiskLevel,
)


class TestTrace:
    def test_minimal_construction(self) -> None:
        t = Trace(
            trace_id="trace-1",
            user_id="user-1",
            input={"text": "deploy app"},
            timestamps=TimestampSet(received_at=1700000000),
        )
        assert t.SCHEMA_VERSION == "1.0.0"
        assert t.interpretation is None
        assert t.proof is None

    def test_roundtrip(self) -> None:
        t = Trace(
            trace_id="trace-2",
            user_id="user-1",
            input={"text": "check status"},
            governance=GovernanceDecision(
                decision_id="gd-1",
                authority_level=AuthorityLevel.AUTONOMOUS,
                risk_level=RiskLevel.READ_ONLY,
                approved=True,
            ),
            execution=ExecutionResult(success=True, output="running", duration_ms=50),
            outcome=Outcome(outcome_id="out-1", achieved=True, score=1.0),
            timestamps=TimestampSet(
                received_at=1700000000,
                execution_completed_at=1700000001,
            ),
        )
        assert Trace.model_validate(t.model_dump()) == t

    def test_extra_forbidden(self) -> None:
        with pytest.raises(ValidationError):
            Trace(
                trace_id="x", user_id="x",
                input={}, timestamps=TimestampSet(received_at=0),
                bad="field",
            )

    def test_required_field_missing(self) -> None:
        with pytest.raises(ValidationError):
            Trace(trace_id="x")  # type: ignore[call-arg]


class TestProofArtifact:
    def test_minimal_construction(self) -> None:
        pa = ProofArtifact(
            proof_id="pf-1",
            action_id="act-1",
            packet_id="wp-1",
            environment_id="env-vps",
            worker_id="w-1",
            evidence_type=EvidenceType.UNIT_TEST,
            evidence_summary="test passed",
            source="pytest",
            timestamp=1700000000,
            governance_compliance=True,
            no_secret_confirmed=True,
            no_mutation_confirmed=True,
            founder_confirmation_status=ConfirmationStatus.NOT_REQUIRED,
            confidence=0.95,
        )
        assert pa.SCHEMA_VERSION == "1.0.0"
        assert pa.parity_result is None

    def test_with_parity(self) -> None:
        pa = ProofArtifact(
            proof_id="pf-2",
            action_id="act-2",
            packet_id="wp-2",
            environment_id="env-local",
            worker_id="w-2",
            evidence_type=EvidenceType.PARITY_CHECK,
            evidence_summary="API and CU match",
            source="w0-001",
            timestamp=1700000001,
            governance_compliance=True,
            no_secret_confirmed=True,
            no_mutation_confirmed=True,
            parity_result=ParityResult(
                parity_id="par-1", path_a="api", path_b="cu",
                match=True,
            ),
            founder_confirmation_status=ConfirmationStatus.CONFIRMED,
            confidence=0.99,
        )
        assert pa.parity_result is not None
        assert pa.parity_result.match is True

    def test_roundtrip(self) -> None:
        pa = ProofArtifact(
            proof_id="pf-3",
            action_id="a", packet_id="p", environment_id="e",
            worker_id="w", evidence_type=EvidenceType.LOG_TRACE,
            evidence_summary="log captured", source="runtime",
            timestamp=0, governance_compliance=True,
            no_secret_confirmed=True, no_mutation_confirmed=True,
            founder_confirmation_status=ConfirmationStatus.NOT_REQUIRED,
            confidence=0.8,
        )
        assert ProofArtifact.model_validate(pa.model_dump()) == pa

    def test_extra_forbidden(self) -> None:
        with pytest.raises(ValidationError):
            ProofArtifact(
                proof_id="x", action_id="x", packet_id="x",
                environment_id="x", worker_id="x",
                evidence_type=EvidenceType.UNIT_TEST,
                evidence_summary="x", source="x", timestamp=0,
                governance_compliance=True, no_secret_confirmed=True,
                no_mutation_confirmed=True,
                founder_confirmation_status=ConfirmationStatus.NOT_REQUIRED,
                confidence=1.0, bad="field",
            )


class TestWorldStateSnapshot:
    def test_minimal_construction(self) -> None:
        wss = WorldStateSnapshot(snapshot_id="ws-1", timestamp=1700000000)
        assert wss.SCHEMA_VERSION == "1.0.0"
        assert wss.entity_count == 0
