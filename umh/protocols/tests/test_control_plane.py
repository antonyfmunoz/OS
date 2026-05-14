"""Tests for umh.protocols.control_plane."""

import pytest
from pydantic import ValidationError

from umh.protocols.common import AuthorityContext, AuthorityLevel, RiskLevel
from umh.protocols.control_plane import ControlPlaneEvent


class TestControlPlaneEvent:
    def test_minimal_construction(self) -> None:
        evt = ControlPlaneEvent(
            event_id="evt-1",
            source="discord",
            event_type="signal_received",
            payload={"text": "hello"},
            schema_version="1.0.0",
            user_instance_id="user-1",
            session_id="sess-1",
            environment_id="env-vps",
            timestamp=1700000000,
            authority_context=AuthorityContext(
                authority_level=AuthorityLevel.AUTONOMOUS
            ),
            trace_id="trace-1",
        )
        assert evt.event_id == "evt-1"
        assert evt.SCHEMA_VERSION == "1.0.0"

    def test_serialization_roundtrip(self) -> None:
        evt = ControlPlaneEvent(
            event_id="evt-2",
            source="api",
            event_type="action_requested",
            payload={"action": "deploy"},
            schema_version="1.0.0",
            user_instance_id="user-1",
            session_id="sess-2",
            environment_id="env-vps",
            timestamp=1700000001,
            authority_context=AuthorityContext(
                authority_level=AuthorityLevel.APPROVE,
                risk_level=RiskLevel.IRREVERSIBLE_WRITE,
            ),
            trace_id="trace-2",
        )
        d = evt.model_dump()
        restored = ControlPlaneEvent.model_validate(d)
        assert restored == evt

    def test_extra_field_forbidden(self) -> None:
        with pytest.raises(ValidationError):
            ControlPlaneEvent(
                event_id="evt-3",
                source="cli",
                event_type="test",
                payload={},
                schema_version="1.0.0",
                user_instance_id="u",
                session_id="s",
                environment_id="e",
                timestamp=0,
                authority_context=AuthorityContext(
                    authority_level=AuthorityLevel.AUTONOMOUS
                ),
                trace_id="t",
                extra_field="boom",
            )

    def test_schema_version_present(self) -> None:
        evt = ControlPlaneEvent(
            event_id="evt-4",
            source="test",
            event_type="test",
            payload={},
            schema_version="1.0.0",
            user_instance_id="u",
            session_id="s",
            environment_id="e",
            timestamp=0,
            authority_context=AuthorityContext(
                authority_level=AuthorityLevel.AUTONOMOUS
            ),
            trace_id="t",
        )
        assert evt.SCHEMA_VERSION == "1.0.0"

    def test_required_field_missing(self) -> None:
        with pytest.raises(ValidationError):
            ControlPlaneEvent(
                event_id="evt-5",
                source="test",
                # missing event_type and others
            )  # type: ignore[call-arg]
