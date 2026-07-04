"""WP-P1-007 — canonical ApprovalRequest type + round-trip adapter tests.

Proves:
  * the canonical ``ApprovalRequest`` is registered in canonical_types;
  * every legacy approval variant round-trips into the canonical type without
    losing the fields that matter for a governance trust boundary;
  * the divergent state vocabularies (rejected vs denied) and risk field names
    (risk_class vs risk_level) collapse deterministically;
  * unknown/missing states fail closed to PENDING (never approved).
"""

from __future__ import annotations

from substrate.canonical_types import CANONICAL_TYPES
from substrate.organism.approval_authority import (
    from_approval_packet,
    from_coordinator_plan,
    from_intercept_request,
    from_organism_record,
    to_unified_dict,
)
from substrate.types import ApprovalOrigin, ApprovalRequest, ApprovalState, RiskClass

# ── registration ─────────────────────────────────────────────────────────────


def test_approval_request_registered_canonically():
    assert CANONICAL_TYPES.get("ApprovalRequest") == ["substrate.types"]
    assert CANONICAL_TYPES.get("ApprovalState") == ["substrate.types"]
    assert CANONICAL_TYPES.get("ApprovalOrigin") == ["substrate.types"]


def test_minimal_contract_matches_legacy_mock():
    """The type the phase31 test mocked must exist with .approval_id/.status/.to_dict."""
    r = ApprovalRequest()
    assert isinstance(r.approval_id, str) and r.approval_id.startswith("apr-")
    assert r.status == "pending"
    d = r.to_dict()
    assert "approval_id" in d and "status" in d


# ── state coercion (the two vocabularies) ────────────────────────────────────


def test_state_coerce_maps_denied_to_rejected():
    assert ApprovalState.coerce("denied") == ApprovalState.REJECTED
    assert ApprovalState.coerce("rejected") == ApprovalState.REJECTED


def test_state_coerce_maps_auto_approved_to_approved():
    assert ApprovalState.coerce("auto_approved") == ApprovalState.APPROVED


def test_state_coerce_unknown_fails_closed_to_pending():
    # An unrecognized status must never read as approved.
    assert ApprovalState.coerce("garbage") == ApprovalState.PENDING
    assert ApprovalState.coerce("") == ApprovalState.PENDING
    assert ApprovalState.coerce(None) == ApprovalState.PENDING  # type: ignore[arg-type]


# ── round-trip: ApprovalPacket ───────────────────────────────────────────────


def test_roundtrip_approval_packet():
    from substrate.organism.approval_gate import ApprovalPacket, ApprovalStatus

    pkt = ApprovalPacket(
        packet_id="apk-xyz",
        candidate_title="deploy service",
        candidate_description="ship v2",
        risk_class="high",
        status=ApprovalStatus.PENDING,
        claimed_by_surface="discord",
        expected_delta="+120 -3",
    )
    r = from_approval_packet(pkt)
    assert r.source_id == "apk-xyz"
    assert r.approval_id == "apr-apk-xyz"
    assert r.title == "deploy service"
    assert r.risk_class == RiskClass.HIGH
    assert r.state == ApprovalState.PENDING
    assert r.claimed_by_surface == "discord"
    assert r.metadata["expected_delta"] == "+120 -3"


def test_roundtrip_approval_packet_rejected():
    from substrate.organism.approval_gate import ApprovalPacket, ApprovalStatus

    pkt = ApprovalPacket(packet_id="apk-r", status=ApprovalStatus.REJECTED)
    r = from_approval_packet(pkt)
    assert r.state == ApprovalState.REJECTED


# ── round-trip: ApprovalInterceptRequest ─────────────────────────────────────


def test_roundtrip_intercept_request():
    from substrate.organism.executors.approval_intercept import ApprovalInterceptRequest

    req = ApprovalInterceptRequest(
        approval_id="apvl-1",
        operation="file_write",
        risk_class="medium",
        reason="needs approval",
        executor_type="coder",
    )
    r = from_intercept_request(req)
    assert r.source_id == "apvl-1"
    assert r.source_origin == ApprovalOrigin.EXECUTOR_INTERCEPT
    assert r.operation == "file_write"
    assert r.risk_class == RiskClass.MEDIUM
    assert r.metadata["executor_type"] == "coder"


# ── round-trip: CoordinatorExecutionPlan (denied vocab) ──────────────────────


def test_roundtrip_coordinator_plan_denied_maps_rejected():
    from substrate.organism.execution_coordinator import CoordinatorExecutionPlan

    plan = CoordinatorExecutionPlan(
        execution_plan_id="expl-9",
        description="run job",
        risk_class="high",
        approval_state="denied",
        session_id="sess-1",
    )
    r = from_coordinator_plan(plan)
    assert r.source_id == "expl-9"
    assert r.source_origin == ApprovalOrigin.COORDINATOR
    assert r.state == ApprovalState.REJECTED, "coordinator 'denied' must canonicalize to REJECTED"
    assert r.session_id == "sess-1"


def test_roundtrip_coordinator_plan_pending():
    from substrate.organism.execution_coordinator import CoordinatorExecutionPlan

    plan = CoordinatorExecutionPlan(execution_plan_id="expl-p", approval_state="pending")
    r = from_coordinator_plan(plan)
    assert r.state == ApprovalState.PENDING


# ── round-trip: organism ApprovalStore record (risk_level vocab) ─────────────


def test_roundtrip_organism_record_risk_level_alias():
    record = {
        "id": "u-42",
        "title": "signal",
        "description": "blocked",
        "risk_level": "medium",  # note: risk_level, not risk_class
        "status": "pending",
        "agent": "system",
        "created_at": "2026-07-04T10:00:00+00:00",
        "trace_id": "tr-1",
    }
    r = from_organism_record(record)
    assert r.source_id == "u-42"
    assert r.source_origin == ApprovalOrigin.ORGANISM_STORE
    assert r.risk_class == RiskClass.MEDIUM, "risk_level must map to risk_class"
    assert r.trace_id == "tr-1"


# ── projection into the unified read shape ───────────────────────────────────


def test_to_unified_dict_exposes_extractor_aliases():
    r = ApprovalRequest(
        title="x",
        source_id="apk-1",
        risk_class=RiskClass.HIGH,
        source_origin=ApprovalOrigin.DISCORD,
    )
    u = to_unified_dict(r)
    # UnifiedApprovalRuntime's duck-typed extractors probe these keys.
    for key in ("approval_id", "work_id", "risk_class", "created_at", "waiting_since", "status"):
        assert key in u, f"unified projection missing {key}"


def test_missing_required_field_rejected():
    """The canonical type validates required-shaped inputs (Pydantic)."""
    import pytest
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        ApprovalRequest(risk_class="not-a-risk-class")  # invalid enum value
