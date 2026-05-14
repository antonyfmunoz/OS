"""Tests for umh.protocols.execution."""

import pytest
from pydantic import ValidationError

from umh.protocols.execution import (
    ActionContract,
    Environment,
    StateTransition,
    WorkPacket,
)
from umh.protocols.common import (
    ApprovalStatus,
    AuthorityLevel,
    EnvironmentRef,
    EnvironmentType,
    PacketStatus,
    RiskLevel,
)


class TestActionContract:
    def test_minimal_construction(self) -> None:
        ac = ActionContract(
            action_id="act-1",
            action_type="shell_command",
            intended_state_change=StateTransition(description="create file"),
            risk_level=RiskLevel.REVERSIBLE_WRITE,
            authority_required=AuthorityLevel.AUTONOMOUS,
            idempotency_key="act-1-create-file",
        )
        assert ac.SCHEMA_VERSION == "1.0.0"
        assert ac.required_capabilities == []

    def test_roundtrip(self) -> None:
        ac = ActionContract(
            action_id="act-2",
            action_type="api_call",
            intended_state_change=StateTransition(
                from_state={"status": "draft"},
                to_state={"status": "published"},
            ),
            risk_level=RiskLevel.EXTERNAL_COMMUNICATION,
            authority_required=AuthorityLevel.APPROVE,
            idempotency_key="act-2-publish",
        )
        assert ActionContract.model_validate(ac.model_dump()) == ac

    def test_extra_forbidden(self) -> None:
        with pytest.raises(ValidationError):
            ActionContract(
                action_id="x", action_type="x",
                intended_state_change=StateTransition(),
                risk_level=RiskLevel.READ_ONLY,
                authority_required=AuthorityLevel.AUTONOMOUS,
                idempotency_key="x",
                bad="field",
            )

    def test_required_field_missing(self) -> None:
        with pytest.raises(ValidationError):
            ActionContract(action_id="x", action_type="x")  # type: ignore[call-arg]


class TestWorkPacket:
    def test_minimal_construction(self) -> None:
        wp = WorkPacket(
            packet_id="wp-1",
            work_order_id="wo-1",
            title="Deploy service",
            description="Deploy os-discord to production",
            action_type="deploy",
            target_environment=EnvironmentRef(environment_id="env-vps"),
            risk_level=RiskLevel.REVERSIBLE_WRITE,
            approval_status=ApprovalStatus.APPROVED,
            timeout_seconds=120,
            created_at=1700000000,
            expires_at=1700003600,
            status=PacketStatus.CREATED,
            trace_id="trace-1",
        )
        assert wp.SCHEMA_VERSION == "1.0.0"
        assert wp.founder_confirmation_required is False
        assert wp.blocked_actions == []

    def test_roundtrip(self) -> None:
        wp = WorkPacket(
            packet_id="wp-2",
            work_order_id="wo-2",
            title="Send email",
            description="Send outreach email",
            action_type="email",
            target_environment=EnvironmentRef(environment_id="env-vps", type=EnvironmentType.VPS),
            risk_level=RiskLevel.EXTERNAL_COMMUNICATION,
            approval_status=ApprovalStatus.PENDING,
            founder_confirmation_required=True,
            allowed_actions=["send_email"],
            blocked_actions=["delete_account"],
            timeout_seconds=60,
            created_at=1700000000,
            expires_at=1700003600,
            status=PacketStatus.QUEUED,
            trace_id="trace-2",
        )
        assert WorkPacket.model_validate(wp.model_dump()) == wp

    def test_extra_forbidden(self) -> None:
        with pytest.raises(ValidationError):
            WorkPacket(
                packet_id="x", work_order_id="x", title="x",
                description="x", action_type="x",
                target_environment=EnvironmentRef(environment_id="x"),
                risk_level=RiskLevel.READ_ONLY,
                approval_status=ApprovalStatus.NOT_REQUIRED,
                timeout_seconds=60, created_at=0, expires_at=0,
                status=PacketStatus.CREATED, trace_id="x",
                bad="field",
            )


class TestEnvironment:
    def test_minimal_construction(self) -> None:
        env = Environment(environment_id="env-1", type=EnvironmentType.VPS)
        assert env.SCHEMA_VERSION == "1.0.0"
        assert env.availability == 1.0
        assert env.capabilities == []

    def test_roundtrip(self) -> None:
        env = Environment(
            environment_id="env-2",
            type=EnvironmentType.LOCAL_GUI,
            availability=0.8,
            reliability=0.95,
        )
        assert Environment.model_validate(env.model_dump()) == env

    def test_extra_forbidden(self) -> None:
        with pytest.raises(ValidationError):
            Environment(environment_id="x", type=EnvironmentType.VPS, bad="field")
