"""Tests for umh.protocols.common — enums, refs, and shared sub-models."""

import pytest
from pydantic import ValidationError

from umh.protocols.common import (
    AuthorityContext,
    AuthorityLevel,
    Benchmark,
    CapabilityRef,
    Constraint,
    CostModel,
    EnvironmentRef,
    EvidenceRef,
    EvidenceType,
    FailureMode,
    LatencyModel,
    MasteryCategory,
    MemoryType,
    Permission,
    PrimitiveType,
    ProofRequirement,
    RiskLevel,
    Severity,
    SignalModality,
    Slot,
    Step,
)


class TestEnums:
    def test_primitive_type_has_10_members(self) -> None:
        assert len(PrimitiveType) == 10

    def test_authority_level_values(self) -> None:
        assert set(AuthorityLevel) == {
            AuthorityLevel.AUTONOMOUS,
            AuthorityLevel.NOTIFY,
            AuthorityLevel.APPROVE,
            AuthorityLevel.ESCALATE,
            AuthorityLevel.DENY,
        }

    def test_risk_level_has_10_members(self) -> None:
        assert len(RiskLevel) == 10

    def test_memory_type_has_14_members(self) -> None:
        assert len(MemoryType) == 14

    def test_mastery_category_has_11_members(self) -> None:
        assert len(MasteryCategory) == 11

    def test_signal_modality_values(self) -> None:
        assert SignalModality.TEXT == "text"
        assert SignalModality.VOICE == "voice"

    def test_severity_values(self) -> None:
        assert len(Severity) == 4


class TestRefs:
    def test_evidence_ref_minimal(self) -> None:
        ref = EvidenceRef(ref_id="ev-1", source="test")
        assert ref.ref_id == "ev-1"
        assert ref.evidence_type is None

    def test_environment_ref_roundtrip(self) -> None:
        ref = EnvironmentRef(environment_id="env-1", type="vps")
        d = ref.model_dump()
        restored = EnvironmentRef.model_validate(d)
        assert restored == ref

    def test_capability_ref_extra_forbidden(self) -> None:
        with pytest.raises(ValidationError):
            CapabilityRef(capability_id="c-1", name="x", bogus="field")

    def test_all_refs_have_schema_version(self) -> None:
        ref = EvidenceRef(ref_id="x", source="s")
        assert ref.SCHEMA_VERSION == "1.0.0"


class TestSubModels:
    def test_constraint_minimal(self) -> None:
        c = Constraint(constraint_id="c-1", name="budget")
        assert c.SCHEMA_VERSION == "1.0.0"
        assert c.description == ""

    def test_constraint_roundtrip(self) -> None:
        c = Constraint(constraint_id="c-1", name="budget", description="max $100")
        assert Constraint.model_validate(c.model_dump()) == c

    def test_constraint_extra_forbidden(self) -> None:
        with pytest.raises(ValidationError):
            Constraint(constraint_id="c-1", name="x", extra_field=True)

    def test_cost_model_minimal(self) -> None:
        cm = CostModel()
        assert cm.per_call_usd is None
        assert cm.params == {}

    def test_latency_model_minimal(self) -> None:
        lm = LatencyModel(p50_ms=10.0)
        assert lm.p95_ms is None

    def test_failure_mode_minimal(self) -> None:
        fm = FailureMode(failure_id="f-1", name="timeout")
        assert fm.severity == Severity.ERROR

    def test_slot_minimal(self) -> None:
        s = Slot(slot_id="s-1", name="goal")
        assert s.required is True
        assert s.type == "string"

    def test_step_minimal(self) -> None:
        st = Step(step_id="st-1", name="plan")
        assert st.order == 0
        assert st.depends_on == []

    def test_proof_requirement_minimal(self) -> None:
        pr = ProofRequirement(
            requirement_id="pr-1", evidence_type=EvidenceType.UNIT_TEST
        )
        assert pr.required is True

    def test_benchmark_minimal(self) -> None:
        b = Benchmark(benchmark_id="b-1", name="latency")
        assert b.threshold is None

    def test_authority_context_minimal(self) -> None:
        ac = AuthorityContext(authority_level=AuthorityLevel.AUTONOMOUS)
        assert ac.SCHEMA_VERSION == "1.0.0"
        assert ac.risk_level is None

    def test_permission_minimal(self) -> None:
        p = Permission(permission_id="p-1", name="read_files")
        assert p.scope == ""

    def test_permission_required_field_missing(self) -> None:
        with pytest.raises(ValidationError):
            Permission(permission_id="p-1")  # type: ignore[call-arg]
