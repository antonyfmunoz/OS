"""Tests for umh.protocols.governance."""

import pytest
from pydantic import ValidationError

from control_plane.protocols.governance import (
    ApprovalRequirement,
    EnvironmentLimit,
    EscalationRule,
    GovernancePolicy,
    RiskModel,
)
from control_plane.protocols.common import (
    AuthorityLevel,
    EnvironmentType,
    RiskLevel,
)


class TestGovernancePolicy:
    def test_minimal_construction(self) -> None:
        gp = GovernancePolicy(authority_level=AuthorityLevel.AUTONOMOUS)
        assert gp.SCHEMA_VERSION == "1.0.0"
        assert gp.constraints == []
        assert gp.risk_model is None

    def test_with_risk_model(self) -> None:
        gp = GovernancePolicy(
            authority_level=AuthorityLevel.APPROVE,
            risk_model=RiskModel(
                risk_level=RiskLevel.FINANCIAL,
                reversible=False,
                financial_exposure=1000.0,
            ),
        )
        assert gp.risk_model is not None
        assert gp.risk_model.financial_exposure == 1000.0

    def test_roundtrip(self) -> None:
        gp = GovernancePolicy(
            authority_level=AuthorityLevel.ESCALATE,
            escalation_rules=[
                EscalationRule(rule_id="r-1", condition="risk > high", escalate_to="founder")
            ],
            approval_requirements=[
                ApprovalRequirement(requirement_id="a-1", condition="financial > $500")
            ],
            environment_limits=[
                EnvironmentLimit(
                    limit_id="l-1",
                    environment_type=EnvironmentType.LOCAL_GUI,
                    max_actions_per_hour=10,
                    allowed_risk_levels=[RiskLevel.READ_ONLY, RiskLevel.REVERSIBLE_WRITE],
                )
            ],
        )
        assert GovernancePolicy.model_validate(gp.model_dump()) == gp

    def test_extra_forbidden(self) -> None:
        with pytest.raises(ValidationError):
            GovernancePolicy(authority_level=AuthorityLevel.DENY, bad="field")

    def test_schema_version_present(self) -> None:
        gp = GovernancePolicy(authority_level=AuthorityLevel.NOTIFY)
        assert gp.SCHEMA_VERSION == "1.0.0"

    def test_required_field_missing(self) -> None:
        with pytest.raises(ValidationError):
            GovernancePolicy()  # type: ignore[call-arg]
