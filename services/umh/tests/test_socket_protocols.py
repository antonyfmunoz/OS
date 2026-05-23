"""Tests for socket layer protocol contracts and envelope dataclasses."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import pytest

from services.umh.governance.risk_classes import RiskClass
from services.umh.protocols.capability import CapabilityCategory
from services.umh.protocols.signal import SignalUrgency
from substrate.sockets.envelopes import (
    CapabilityRequest,
    CapabilityResponse,
    OutcomeEnvelope,
    SignalEnvelope,
    SignalReceipt,
    ViewFrame,
)
from substrate.sockets.protocols import (
    CapabilityDescriptor,
    CapabilityHandler,
    CapabilityHealth,
    OutcomeReceiver,
    SignalDescriptor,
    SignalEmitter,
    ViewSubscriber,
)


class TestProtocolsExist:
    """Verify all four Protocol classes exist and have the right methods."""

    def test_signal_emitter_is_protocol(self) -> None:
        assert hasattr(SignalEmitter, "__protocol_attrs__") or hasattr(
            SignalEmitter, "__abstractmethods__"
        )

    def test_signal_emitter_has_integration_id(self) -> None:
        assert "integration_id" in dir(SignalEmitter)

    def test_signal_emitter_has_describe_signals(self) -> None:
        assert "describe_signals" in dir(SignalEmitter)

    def test_capability_handler_is_protocol(self) -> None:
        assert hasattr(CapabilityHandler, "__protocol_attrs__") or hasattr(
            CapabilityHandler, "__abstractmethods__"
        )

    def test_capability_handler_has_handle_capability(self) -> None:
        assert "handle_capability" in dir(CapabilityHandler)

    def test_capability_handler_has_health(self) -> None:
        assert "health" in dir(CapabilityHandler)

    def test_outcome_receiver_is_protocol(self) -> None:
        assert hasattr(OutcomeReceiver, "__protocol_attrs__") or hasattr(
            OutcomeReceiver, "__abstractmethods__"
        )

    def test_outcome_receiver_has_on_outcome(self) -> None:
        assert "on_outcome" in dir(OutcomeReceiver)

    def test_outcome_receiver_has_accepts_outcomes(self) -> None:
        assert "accepts_outcomes" in dir(OutcomeReceiver)

    def test_view_subscriber_is_protocol(self) -> None:
        assert hasattr(ViewSubscriber, "__protocol_attrs__") or hasattr(
            ViewSubscriber, "__abstractmethods__"
        )

    def test_view_subscriber_has_on_frame(self) -> None:
        assert "on_frame" in dir(ViewSubscriber)

    def test_view_subscriber_has_accepts_events(self) -> None:
        assert "accepts_events" in dir(ViewSubscriber)


class TestProtocolSatisfaction:
    """Verify that plain classes satisfy Protocols structurally."""

    def test_dummy_satisfies_signal_emitter(self) -> None:
        class Dummy:
            @property
            def integration_id(self) -> str:
                return "test"

            def describe_signals(self) -> list[SignalDescriptor]:
                return []

        assert isinstance(Dummy(), SignalEmitter)

    def test_dummy_satisfies_capability_handler(self) -> None:
        class Dummy:
            @property
            def integration_id(self) -> str:
                return "test"

            def describe_capabilities(self) -> list[CapabilityDescriptor]:
                return []

            def handle_capability(self, request: CapabilityRequest) -> CapabilityResponse:
                return CapabilityResponse(request_id=request.request_id, success=True)

            def health(self) -> CapabilityHealth:
                return CapabilityHealth(integration_id="test", status="healthy")

        assert isinstance(Dummy(), CapabilityHandler)

    def test_dummy_satisfies_outcome_receiver(self) -> None:
        class Dummy:
            @property
            def integration_id(self) -> str:
                return "test"

            def on_outcome(self, envelope: OutcomeEnvelope) -> None:
                pass

            def accepts_outcomes(self) -> list[str]:
                return []

        assert isinstance(Dummy(), OutcomeReceiver)

    def test_dummy_satisfies_view_subscriber(self) -> None:
        class Dummy:
            @property
            def subscriber_id(self) -> str:
                return "test"

            def on_frame(self, frame: ViewFrame) -> None:
                pass

            def accepts_events(self) -> list[str]:
                return []

        assert isinstance(Dummy(), ViewSubscriber)


class TestEnvelopes:
    """Verify envelope dataclasses construct correctly."""

    def test_signal_envelope_minimal(self) -> None:
        env = SignalEnvelope(
            integration_id="test",
            content_type="event",
            payload={"key": "value"},
        )
        assert env.integration_id == "test"
        assert env.urgency == SignalUrgency.NORMAL
        assert env.raw_content is None

    def test_signal_envelope_frozen(self) -> None:
        env = SignalEnvelope(integration_id="x", content_type="y", payload={})
        with pytest.raises(AttributeError):
            env.integration_id = "z"  # type: ignore[misc]

    def test_capability_request(self) -> None:
        rid = uuid4()
        req = CapabilityRequest(
            request_id=rid,
            capability_name="create_page",
            integration_id="notion",
            params={"title": "Test"},
            governance_verdict_id=uuid4(),
            trace_id=uuid4(),
        )
        assert req.request_id == rid
        assert req.timeout_seconds == 30.0

    def test_capability_response_with_raw_error(self) -> None:
        resp = CapabilityResponse(
            request_id=uuid4(),
            success=False,
            error="capability failed",
            raw_error="NotionAPIError: 429 rate_limit_exceeded",
        )
        assert not resp.success
        assert resp.raw_error is not None
        assert "429" in resp.raw_error

    def test_outcome_envelope(self) -> None:
        env = OutcomeEnvelope(
            outcome_id=uuid4(),
            signal_id=uuid4(),
            trace_id=uuid4(),
            integration_id="notion",
            outcome_type="success",
            summary="Page created",
        )
        assert env.outcome_type == "success"
        assert env.confidence == 1.0

    def test_view_frame(self) -> None:
        frame = ViewFrame(
            frame_id=uuid4(),
            timestamp=datetime.now(timezone.utc),
            event_type="governance",
            stage=3,
            data={"decision": "approve"},
        )
        assert frame.stage == 3
        assert frame.trace_id is None

    def test_signal_receipt_accepted(self) -> None:
        receipt = SignalReceipt(
            signal_id=uuid4(),
            trace_id=uuid4(),
            accepted=True,
            accepted_at=datetime.now(timezone.utc),
        )
        assert receipt.accepted
        assert receipt.rejection_reason is None

    def test_signal_receipt_rejected(self) -> None:
        receipt = SignalReceipt(
            signal_id=uuid4(),
            trace_id=uuid4(),
            accepted=False,
            accepted_at=datetime.now(timezone.utc),
            rejection_reason="not registered",
        )
        assert not receipt.accepted


class TestDescriptors:
    """Verify descriptor dataclasses."""

    def test_signal_descriptor_defaults(self) -> None:
        d = SignalDescriptor(content_type="page_created", description="New page")
        assert d.default_urgency == SignalUrgency.NORMAL
        assert d.default_risk_class == RiskClass.READ_ONLY

    def test_capability_descriptor(self) -> None:
        d = CapabilityDescriptor(
            name="create_page",
            category=CapabilityCategory.COMMUNICATE,
            risk_class=RiskClass.EXTERNAL_COMMUNICATION,
            description="Create a Notion page",
        )
        assert d.name == "create_page"
        assert d.cost_estimate == 0.0

    def test_capability_health(self) -> None:
        h = CapabilityHealth(integration_id="notion", status="healthy")
        assert h.status == "healthy"
        assert h.detail == ""
