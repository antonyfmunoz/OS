"""Tests for socket registration, IntegrationRegistry, and IntegrationAdapter."""

from __future__ import annotations

from typing import Any
from uuid import uuid4

import pytest

from services.umh.governance.risk_classes import RiskClass
from services.umh.protocols.capability import CapabilityCategory
from substrate.sockets.capability_socket import CapabilitySocket
from substrate.sockets.envelopes import (
    CapabilityRequest,
    CapabilityResponse,
    OutcomeEnvelope,
    SignalEnvelope,
    ViewFrame,
)
from substrate.sockets.outcome_socket import OutcomeSocket
from substrate.sockets.protocols import (
    CapabilityDescriptor,
    CapabilityHealth,
    SignalDescriptor,
)
from substrate.sockets.registry import (
    IntegrationAdapter,
    IntegrationManifest,
    IntegrationRegistry,
)
from substrate.sockets.signal_socket import SignalSocket
from substrate.sockets.view_socket import ViewSocket


class DummySignalEmitter:
    @property
    def integration_id(self) -> str:
        return "test_integration"

    def describe_signals(self) -> list[SignalDescriptor]:
        return [SignalDescriptor(content_type="test_event", description="A test event")]


class DummyCapabilityHandler:
    @property
    def integration_id(self) -> str:
        return "test_integration"

    def describe_capabilities(self) -> list[CapabilityDescriptor]:
        return [
            CapabilityDescriptor(
                name="do_thing",
                category=CapabilityCategory.COMPUTE,
                risk_class=RiskClass.SAFE_WRITE,
                description="Do a test thing",
            ),
        ]

    def handle_capability(self, request: CapabilityRequest) -> CapabilityResponse:
        return CapabilityResponse(
            request_id=request.request_id,
            success=True,
            result_data={"handled": True},
        )

    def health(self) -> CapabilityHealth:
        return CapabilityHealth(integration_id="test_integration", status="healthy")


class DummyOutcomeReceiver:
    def __init__(self) -> None:
        self.received: list[OutcomeEnvelope] = []

    @property
    def integration_id(self) -> str:
        return "test_integration"

    def on_outcome(self, envelope: OutcomeEnvelope) -> None:
        self.received.append(envelope)

    def accepts_outcomes(self) -> list[str]:
        return []


class DummyViewSubscriber:
    def __init__(self) -> None:
        self.frames: list[ViewFrame] = []

    @property
    def subscriber_id(self) -> str:
        return "test_subscriber"

    def on_frame(self, frame: ViewFrame) -> None:
        self.frames.append(frame)

    def accepts_events(self) -> list[str]:
        return []


def _make_registry() -> tuple[
    IntegrationRegistry, SignalSocket, CapabilitySocket, OutcomeSocket, ViewSocket
]:
    ss = SignalSocket()
    cs = CapabilitySocket()
    os_ = OutcomeSocket()
    vs = ViewSocket()
    return IntegrationRegistry(ss, cs, os_, vs), ss, cs, os_, vs


class TestSignalSocket:
    def test_register_emitter(self) -> None:
        ss = SignalSocket()
        ss.register_emitter(DummySignalEmitter())
        assert "test_integration" in ss.registered_integrations()

    def test_duplicate_emitter_raises(self) -> None:
        ss = SignalSocket()
        ss.register_emitter(DummySignalEmitter())
        with pytest.raises(ValueError, match="already registered"):
            ss.register_emitter(DummySignalEmitter())

    def test_emit_unregistered_rejected(self) -> None:
        ss = SignalSocket()
        receipt = ss.emit(SignalEnvelope(integration_id="unknown", content_type="x", payload={}))
        assert not receipt.accepted
        assert "not registered" in (receipt.rejection_reason or "")

    def test_emit_bad_content_type_rejected(self) -> None:
        ss = SignalSocket()
        ss.register_emitter(DummySignalEmitter())
        receipt = ss.emit(
            SignalEnvelope(
                integration_id="test_integration",
                content_type="nonexistent_event",
                payload={},
            )
        )
        assert not receipt.accepted
        assert "not in catalog" in (receipt.rejection_reason or "")

    def test_emit_valid_accepted(self) -> None:
        ss = SignalSocket()
        ss.register_emitter(DummySignalEmitter())
        receipt = ss.emit(
            SignalEnvelope(
                integration_id="test_integration",
                content_type="test_event",
                payload={"key": "value"},
            )
        )
        assert receipt.accepted

    def test_signal_catalog(self) -> None:
        ss = SignalSocket()
        ss.register_emitter(DummySignalEmitter())
        catalog = ss.signal_catalog()
        assert "test_integration" in catalog
        assert len(catalog["test_integration"]) == 1
        assert catalog["test_integration"][0].content_type == "test_event"


class TestCapabilitySocket:
    def test_register_handler(self) -> None:
        cs = CapabilitySocket()
        cs.register_handler(DummyCapabilityHandler())
        catalog = cs.capability_catalog()
        assert "test_integration" in catalog

    def test_duplicate_handler_raises(self) -> None:
        cs = CapabilitySocket()
        cs.register_handler(DummyCapabilityHandler())
        with pytest.raises(ValueError, match="already registered"):
            cs.register_handler(DummyCapabilityHandler())

    def test_request_unregistered_fails(self) -> None:
        cs = CapabilitySocket()
        resp = cs.request(
            CapabilityRequest(
                request_id=uuid4(),
                capability_name="x",
                integration_id="unknown",
                params={},
                governance_verdict_id=uuid4(),
                trace_id=uuid4(),
            )
        )
        assert not resp.success
        assert "no handler" in (resp.error or "")

    def test_request_success(self) -> None:
        cs = CapabilitySocket()
        cs.register_handler(DummyCapabilityHandler())
        resp = cs.request(
            CapabilityRequest(
                request_id=uuid4(),
                capability_name="do_thing",
                integration_id="test_integration",
                params={},
                governance_verdict_id=uuid4(),
                trace_id=uuid4(),
            )
        )
        assert resp.success
        assert resp.result_data == {"handled": True}

    def test_request_handler_exception_normalized(self) -> None:
        class FailingHandler:
            @property
            def integration_id(self) -> str:
                return "failing"

            def describe_capabilities(self) -> list[CapabilityDescriptor]:
                return [
                    CapabilityDescriptor(
                        name="explode",
                        category=CapabilityCategory.COMPUTE,
                        risk_class=RiskClass.SAFE_WRITE,
                    ),
                ]

            def handle_capability(self, request: CapabilityRequest) -> CapabilityResponse:
                raise ConnectionError("API unreachable")

            def health(self) -> CapabilityHealth:
                return CapabilityHealth(integration_id="failing", status="unavailable")

        cs = CapabilitySocket()
        cs.register_handler(FailingHandler())
        resp = cs.request(
            CapabilityRequest(
                request_id=uuid4(),
                capability_name="explode",
                integration_id="failing",
                params={},
                governance_verdict_id=uuid4(),
                trace_id=uuid4(),
            )
        )
        assert not resp.success
        assert resp.error is not None
        assert resp.raw_error is not None
        assert "ConnectionError" in resp.raw_error

    def test_health_check(self) -> None:
        cs = CapabilitySocket()
        cs.register_handler(DummyCapabilityHandler())
        h = cs.health_check("test_integration")
        assert h.status == "healthy"

    def test_health_check_unregistered(self) -> None:
        cs = CapabilitySocket()
        h = cs.health_check("unknown")
        assert h.status == "unavailable"


class TestOutcomeSocket:
    def test_register_receiver(self) -> None:
        os_ = OutcomeSocket()
        os_.register_receiver(DummyOutcomeReceiver())
        assert "test_integration" in os_.registered_receivers()

    def test_notify_delivers(self) -> None:
        receiver = DummyOutcomeReceiver()
        os_ = OutcomeSocket()
        os_.register_receiver(receiver)
        env = OutcomeEnvelope(
            outcome_id=uuid4(),
            signal_id=uuid4(),
            trace_id=uuid4(),
            integration_id="test_integration",
            outcome_type="success",
            summary="test outcome",
        )
        os_.notify(env)
        assert len(receiver.received) == 1
        assert receiver.received[0].outcome_type == "success"

    def test_notify_wrong_integration_skips(self) -> None:
        receiver = DummyOutcomeReceiver()
        os_ = OutcomeSocket()
        os_.register_receiver(receiver)
        env = OutcomeEnvelope(
            outcome_id=uuid4(),
            signal_id=uuid4(),
            trace_id=uuid4(),
            integration_id="other",
            outcome_type="success",
            summary="test",
        )
        os_.notify(env)
        assert len(receiver.received) == 0

    def test_notify_all_broadcasts(self) -> None:
        receiver = DummyOutcomeReceiver()
        os_ = OutcomeSocket()
        os_.register_receiver(receiver)
        env = OutcomeEnvelope(
            outcome_id=uuid4(),
            signal_id=uuid4(),
            trace_id=uuid4(),
            integration_id="other",
            outcome_type="success",
            summary="broadcast test",
        )
        os_.notify_all(env)
        assert len(receiver.received) == 1

    def test_accepts_outcomes_filter(self) -> None:
        class FilteredReceiver:
            @property
            def integration_id(self) -> str:
                return "filtered"

            def on_outcome(self, envelope: OutcomeEnvelope) -> None:
                self.got_it = True

            def accepts_outcomes(self) -> list[str]:
                return ["failure"]

        receiver = FilteredReceiver()
        os_ = OutcomeSocket()
        os_.register_receiver(receiver)
        env = OutcomeEnvelope(
            outcome_id=uuid4(),
            signal_id=uuid4(),
            trace_id=uuid4(),
            integration_id="filtered",
            outcome_type="success",
            summary="should be filtered",
        )
        os_.notify(env)
        assert not hasattr(receiver, "got_it")


class TestViewSocket:
    def test_subscribe(self) -> None:
        vs = ViewSocket()
        vs.subscribe(DummyViewSubscriber())
        assert vs.subscriber_count() == 1

    def test_broadcast_delivers(self) -> None:
        sub = DummyViewSubscriber()
        vs = ViewSocket()
        vs.subscribe(sub)
        from datetime import datetime, timezone

        frame = ViewFrame(
            frame_id=uuid4(),
            timestamp=datetime.now(timezone.utc),
            event_type="signal",
            stage=1,
            data={"signal_id": "abc"},
        )
        vs.broadcast(frame)
        assert len(sub.frames) == 1
        assert sub.frames[0].event_type == "signal"

    def test_accepts_events_filter(self) -> None:
        class FilteredSub:
            @property
            def subscriber_id(self) -> str:
                return "filtered"

            def on_frame(self, frame: ViewFrame) -> None:
                self.got_it = True

            def accepts_events(self) -> list[str]:
                return ["governance"]

        sub = FilteredSub()
        vs = ViewSocket()
        vs.subscribe(sub)
        from datetime import datetime, timezone

        frame = ViewFrame(
            frame_id=uuid4(),
            timestamp=datetime.now(timezone.utc),
            event_type="signal",
            stage=1,
            data={},
        )
        vs.broadcast(frame)
        assert not hasattr(sub, "got_it")

    def test_unsubscribe(self) -> None:
        sub = DummyViewSubscriber()
        vs = ViewSocket()
        vs.subscribe(sub)
        vs.unsubscribe("test_subscriber")
        assert vs.subscriber_count() == 0


class TestIntegrationRegistry:
    def test_register_full_manifest(self) -> None:
        registry, ss, cs, os_, vs = _make_registry()
        manifest = IntegrationManifest(
            integration_id="test_integration",
            signal_emitter=DummySignalEmitter(),
            capability_handler=DummyCapabilityHandler(),
            outcome_receiver=DummyOutcomeReceiver(),
            view_subscriber=DummyViewSubscriber(),
        )
        adapter = registry.register(manifest)
        assert adapter is not None
        assert "test_integration" in registry.registered()
        assert "test_integration" in ss.registered_integrations()
        assert vs.subscriber_count() == 1

    def test_register_signal_only(self) -> None:
        registry, ss, cs, os_, vs = _make_registry()
        manifest = IntegrationManifest(
            integration_id="signal_only",
            signal_emitter=DummySignalEmitter(),
        )
        adapter = registry.register(manifest)
        assert adapter is None
        assert "signal_only" in registry.registered()

    def test_duplicate_registration_raises(self) -> None:
        registry, *_ = _make_registry()
        manifest = IntegrationManifest(integration_id="dup")
        registry.register(manifest)
        with pytest.raises(ValueError, match="already registered"):
            registry.register(manifest)

    def test_adapter_created_with_risk_map(self) -> None:
        registry, *_ = _make_registry()
        manifest = IntegrationManifest(
            integration_id="test_integration",
            capability_handler=DummyCapabilityHandler(),
        )
        adapter = registry.register(manifest)
        assert adapter is not None
        assert adapter.name == "test_integration"
        assert adapter.classify_risk("do_thing", {}) == RiskClass.SAFE_WRITE

    def test_adapter_classify_risk_unknown_defaults(self) -> None:
        registry, *_ = _make_registry()
        manifest = IntegrationManifest(
            integration_id="test_integration",
            capability_handler=DummyCapabilityHandler(),
        )
        adapter = registry.register(manifest)
        assert adapter is not None
        assert adapter.classify_risk("unknown_op", {}) == RiskClass.EXTERNAL_COMMUNICATION

    def test_adapter_execute_success(self) -> None:
        registry, ss, cs, os_, vs = _make_registry()
        manifest = IntegrationManifest(
            integration_id="test_integration",
            capability_handler=DummyCapabilityHandler(),
        )
        adapter = registry.register(manifest)
        assert adapter is not None
        result = adapter.execute("do_thing", {})
        assert result["handled"] is True

    def test_adapter_execute_failure_raises(self) -> None:
        class FailHandler:
            @property
            def integration_id(self) -> str:
                return "fail"

            def describe_capabilities(self) -> list[CapabilityDescriptor]:
                return [
                    CapabilityDescriptor(
                        name="fail_op",
                        category=CapabilityCategory.COMPUTE,
                        risk_class=RiskClass.SAFE_WRITE,
                    ),
                ]

            def handle_capability(self, request: CapabilityRequest) -> CapabilityResponse:
                raise ValueError("boom")

            def health(self) -> CapabilityHealth:
                return CapabilityHealth(integration_id="fail", status="unavailable")

        registry, *_ = _make_registry()
        manifest = IntegrationManifest(
            integration_id="fail",
            capability_handler=FailHandler(),
        )
        adapter = registry.register(manifest)
        assert adapter is not None
        with pytest.raises(RuntimeError, match="boom"):
            adapter.execute("fail_op", {})

    def test_unregister(self) -> None:
        registry, *_ = _make_registry()
        manifest = IntegrationManifest(integration_id="temp")
        registry.register(manifest)
        registry.unregister("temp")
        assert "temp" not in registry.registered()

    def test_health(self) -> None:
        registry, *_ = _make_registry()
        manifest = IntegrationManifest(
            integration_id="test_integration",
            capability_handler=DummyCapabilityHandler(),
        )
        registry.register(manifest)
        health = registry.health()
        assert "test_integration" in health
        assert health["test_integration"].status == "healthy"


class TestIntegrationAdapterProtocol:
    """Verify IntegrationAdapter satisfies executor's AdapterProtocol."""

    def test_has_name_property(self) -> None:
        cs = CapabilitySocket()
        adapter = IntegrationAdapter("test", cs, [])
        assert isinstance(adapter.name, str)

    def test_has_execute_method(self) -> None:
        cs = CapabilitySocket()
        adapter = IntegrationAdapter("test", cs, [])
        assert callable(adapter.execute)

    def test_has_classify_risk_method(self) -> None:
        cs = CapabilitySocket()
        adapter = IntegrationAdapter("test", cs, [])
        assert callable(adapter.classify_risk)
