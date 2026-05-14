"""Tests for umh.protocols.learning."""

import pytest
from pydantic import ValidationError

from umh.protocols.learning import InternalSignal
from umh.protocols.common import Severity, SignalType


class TestInternalSignal:
    def test_minimal_construction(self) -> None:
        sig = InternalSignal(
            source_module="memory",
            signal_type=SignalType.HEALTH_CHECK,
            severity=Severity.INFO,
            timestamp=1700000000,
        )
        assert sig.SCHEMA_VERSION == "1.0.0"
        assert sig.payload == {}
        assert sig.recommended_action is None

    def test_with_payload(self) -> None:
        sig = InternalSignal(
            source_module="execution",
            signal_type=SignalType.STUCK_LOOP,
            severity=Severity.ERROR,
            payload={"queue_depth": 50, "oldest_item_age_seconds": 300},
            timestamp=1700000001,
            recommended_action="flush_queue",
        )
        assert sig.payload["queue_depth"] == 50
        assert sig.recommended_action == "flush_queue"

    def test_roundtrip(self) -> None:
        sig = InternalSignal(
            source_module="governance",
            signal_type=SignalType.ANOMALY,
            severity=Severity.WARNING,
            timestamp=0,
        )
        assert InternalSignal.model_validate(sig.model_dump()) == sig

    def test_extra_forbidden(self) -> None:
        with pytest.raises(ValidationError):
            InternalSignal(
                source_module="x",
                signal_type=SignalType.HEARTBEAT,
                severity=Severity.INFO,
                timestamp=0,
                bad="field",
            )

    def test_schema_version_present(self) -> None:
        sig = InternalSignal(
            source_module="x",
            signal_type=SignalType.HEARTBEAT,
            severity=Severity.INFO,
            timestamp=0,
        )
        assert sig.SCHEMA_VERSION == "1.0.0"

    def test_required_field_missing(self) -> None:
        with pytest.raises(ValidationError):
            InternalSignal(source_module="x")  # type: ignore[call-arg]
