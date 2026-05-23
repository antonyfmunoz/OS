"""Tests for EOSSignalEmitter — builds SignalEnvelopes from EOS rows."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from services.umh.integrations.eos.correlation import EOSWritebackTarget
from services.umh.integrations.eos.signals import EOSSignalEmitter
from services.umh.integrations.eos.tables import EventRow
from substrate.sockets.envelopes import SignalEnvelope


def _make_event_row(
    row_id: str = "row-1",
    org_id: str = "org-1",
    event_type: str = "lead_created",
    payload: dict | None = None,
    handled_by: str | None = None,
) -> EventRow:
    return EventRow(
        id=row_id,
        org_id=org_id,
        event_type=event_type,
        payload_json=payload or {"name": "Test Lead"},
        handled_by=handled_by,
        created_at=datetime(2026, 5, 19, 10, 0, 0, tzinfo=timezone.utc),
    )


class TestEOSSignalEmitter:
    def test_integration_id(self) -> None:
        emitter = EOSSignalEmitter()
        assert emitter.integration_id == "eos"

    def test_describe_signals_not_empty(self) -> None:
        emitter = EOSSignalEmitter()
        signals = emitter.describe_signals()
        assert len(signals) >= 1
        assert signals[0].content_type == "eos_events_created"

    def test_build_signal_returns_envelope_and_target(self) -> None:
        emitter = EOSSignalEmitter()
        row = _make_event_row()

        envelope, target = emitter.build_signal(row, "events")

        assert isinstance(envelope, SignalEnvelope)
        assert isinstance(target, EOSWritebackTarget)

    def test_envelope_integration_id(self) -> None:
        emitter = EOSSignalEmitter()
        envelope, _ = emitter.build_signal(_make_event_row(), "events")

        assert envelope.integration_id == "eos"

    def test_envelope_content_type(self) -> None:
        emitter = EOSSignalEmitter()
        envelope, _ = emitter.build_signal(_make_event_row(), "events")

        assert envelope.content_type == "eos_events_created"

    def test_envelope_payload_contains_org_id(self) -> None:
        emitter = EOSSignalEmitter()
        envelope, _ = emitter.build_signal(_make_event_row(org_id="org-42"), "events")

        assert envelope.payload["org_id"] == "org-42"
        assert envelope.payload["table_name"] == "events"

    def test_envelope_payload_contains_row_fields(self) -> None:
        emitter = EOSSignalEmitter()
        envelope, _ = emitter.build_signal(
            _make_event_row(row_id="r-99", event_type="enrollment"),
            "events",
        )

        assert envelope.payload["row_id"] == "r-99"
        assert envelope.payload["event_type"] == "enrollment"
        assert envelope.payload["adapter_name"] == "eos"
        assert envelope.payload["operation"] == "noop"

    def test_envelope_correlation_id_set(self) -> None:
        emitter = EOSSignalEmitter()
        envelope, _ = emitter.build_signal(_make_event_row(), "events")

        assert envelope.correlation_id is not None

    def test_writeback_target_fields(self) -> None:
        emitter = EOSSignalEmitter()
        _, target = emitter.build_signal(
            _make_event_row(row_id="r-1", org_id="org-5"),
            "events",
        )

        assert target.org_id == "org-5"
        assert target.table_name == "events"
        assert target.row_id == "r-1"
        assert target.integration == "eos"

    def test_raw_content_includes_event_type(self) -> None:
        emitter = EOSSignalEmitter()
        envelope, _ = emitter.build_signal(
            _make_event_row(event_type="payment_received"),
            "events",
        )

        assert "payment_received" in envelope.raw_content

    def test_source_identifier_format(self) -> None:
        emitter = EOSSignalEmitter()
        envelope, _ = emitter.build_signal(
            _make_event_row(row_id="r-abc"),
            "events",
        )

        assert envelope.source_identifier == "eos:events:r-abc"

    def test_metadata_contains_org_id(self) -> None:
        emitter = EOSSignalEmitter()
        envelope, _ = emitter.build_signal(
            _make_event_row(org_id="org-meta"),
            "events",
        )

        assert envelope.metadata["org_id"] == "org-meta"
        assert envelope.metadata["table_name"] == "events"
