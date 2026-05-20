"""Tests for NotionSignalEmitter — build_signal produces correct envelopes."""

from __future__ import annotations

from typing import Any

import pytest

from services.umh.integrations.notion.signals import NotionSignalEmitter


def _make_page(
    page_id: str = "page-123",
    title: str = "Test Page",
    last_edited: str = "2026-05-20T10:00:00.000Z",
) -> dict[str, Any]:
    return {
        "id": page_id,
        "last_edited_time": last_edited,
        "properties": {
            "Name": {
                "type": "title",
                "title": [{"plain_text": title}],
            },
            "Status": {
                "type": "select",
                "select": {"name": "In Progress"},
            },
            "Notes": {
                "type": "rich_text",
                "rich_text": [{"plain_text": "some notes"}],
            },
        },
    }


def _make_config(
    database_id: str = "db-456",
    operation: str = "noop",
    logical_name: str = "test_db",
) -> dict[str, Any]:
    return {
        "database_id": database_id,
        "operation": operation,
        "logical_name": logical_name,
    }


class TestNotionSignalEmitter:
    def test_satisfies_protocol(self) -> None:
        from services.umh.sockets.protocols import SignalEmitter

        emitter = NotionSignalEmitter()
        assert isinstance(emitter, SignalEmitter)

    def test_integration_id(self) -> None:
        emitter = NotionSignalEmitter()
        assert emitter.integration_id == "notion"

    def test_describe_signals_nonempty(self) -> None:
        emitter = NotionSignalEmitter()
        signals = emitter.describe_signals()
        assert len(signals) >= 3

    def test_build_signal_returns_tuple(self) -> None:
        emitter = NotionSignalEmitter()
        result = emitter.build_signal(_make_page(), _make_config())
        assert isinstance(result, tuple)
        assert len(result) == 2

    def test_envelope_integration_id(self) -> None:
        emitter = NotionSignalEmitter()
        envelope, _ = emitter.build_signal(_make_page(), _make_config())
        assert envelope.integration_id == "notion"

    def test_envelope_content_type(self) -> None:
        emitter = NotionSignalEmitter()
        envelope, _ = emitter.build_signal(_make_page(), _make_config())
        assert envelope.content_type == "page_updated"

    def test_envelope_payload_page_id(self) -> None:
        emitter = NotionSignalEmitter()
        envelope, _ = emitter.build_signal(_make_page(page_id="p-99"), _make_config())
        assert envelope.payload["page_id"] == "p-99"

    def test_envelope_payload_database_id(self) -> None:
        emitter = NotionSignalEmitter()
        envelope, _ = emitter.build_signal(_make_page(), _make_config(database_id="db-xyz"))
        assert envelope.payload["database_id"] == "db-xyz"

    def test_envelope_payload_operation(self) -> None:
        emitter = NotionSignalEmitter()
        envelope, _ = emitter.build_signal(_make_page(), _make_config(operation="noop"))
        assert envelope.payload["operation"] == "noop"
        assert envelope.payload["adapter_name"] == "notion"

    def test_envelope_correlation_id_set(self) -> None:
        emitter = NotionSignalEmitter()
        envelope, _ = emitter.build_signal(_make_page(), _make_config())
        assert envelope.correlation_id is not None

    def test_envelope_source_identifier(self) -> None:
        emitter = NotionSignalEmitter()
        envelope, _ = emitter.build_signal(_make_page(page_id="p-42"), _make_config())
        assert envelope.source_identifier == "notion:page:p-42"

    def test_envelope_raw_content_is_title(self) -> None:
        emitter = NotionSignalEmitter()
        envelope, _ = emitter.build_signal(_make_page(title="My Task"), _make_config())
        assert envelope.raw_content == "My Task"

    def test_writeback_to_shape(self) -> None:
        emitter = NotionSignalEmitter()
        _, writeback_to = emitter.build_signal(_make_page(page_id="p-42"), _make_config())
        assert writeback_to == {"page_id": "p-42", "integration": "notion"}

    def test_page_properties_extracted(self) -> None:
        emitter = NotionSignalEmitter()
        envelope, _ = emitter.build_signal(_make_page(), _make_config())
        props = envelope.payload["page_properties"]
        assert props["Name"] == "Test Page"
        assert props["Status"] == "In Progress"
        assert props["Notes"] == "some notes"

    def test_page_without_title(self) -> None:
        page = {"id": "p-1", "last_edited_time": "2026-01-01", "properties": {}}
        emitter = NotionSignalEmitter()
        envelope, _ = emitter.build_signal(page, _make_config())
        assert envelope.raw_content == "Untitled"

    def test_metadata_contains_poll_source(self) -> None:
        emitter = NotionSignalEmitter()
        envelope, _ = emitter.build_signal(_make_page(), _make_config(logical_name="my_db"))
        assert envelope.metadata["poll_source"] == "my_db"
