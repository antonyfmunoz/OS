"""Tests for EOSPoller — background polling, watermark advancement, multi-org, correlation."""

from __future__ import annotations

import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch
from uuid import UUID, uuid4

import pytest

from services.umh.integrations.eos.correlation import EOSCorrelationMap
from services.umh.integrations.eos.poller import EOSPoller
from services.umh.integrations.eos.signals import EOSSignalEmitter
from services.umh.integrations.eos.tables import EventRow
from services.umh.integrations.notion.watermarks import WatermarkStore


@dataclass
class FakePipelineResult:
    signal_id: UUID
    trace_id: UUID
    outcome_type: str = "success"


def _make_event_row(
    row_id: str = "row-1",
    org_id: str = "org-1",
    event_type: str = "lead_created",
    created_at: str = "2026-05-19T10:00:00+00:00",
) -> EventRow:
    return EventRow(
        id=row_id,
        org_id=org_id,
        event_type=event_type,
        payload_json={"name": "Test"},
        handled_by=None,
        created_at=datetime.fromisoformat(created_at),
    )


class TestEOSPoller:
    @pytest.fixture()
    def setup(self, tmp_path: Path) -> dict[str, Any]:
        correlation_map = EOSCorrelationMap()
        emitter = EOSSignalEmitter()
        outcome_receiver = MagicMock()
        watermark_store = WatermarkStore(path=tmp_path / "eos_wm.jsonl")

        submit_results: list[FakePipelineResult] = []

        def fake_submit(*args: Any, **kwargs: Any) -> FakePipelineResult:
            result = FakePipelineResult(signal_id=uuid4(), trace_id=uuid4())
            submit_results.append(result)
            return result

        submit_fn = MagicMock(side_effect=fake_submit)

        return {
            "correlation_map": correlation_map,
            "emitter": emitter,
            "submit_fn": submit_fn,
            "outcome_receiver": outcome_receiver,
            "watermark_store": watermark_store,
            "submit_results": submit_results,
        }

    def _make_poller(
        self,
        setup: dict[str, Any],
        tables: list[str] | None = None,
        org_ids: list[str] | None = None,
    ) -> EOSPoller:
        return EOSPoller(
            database_url="postgresql://test:test@localhost/test",
            correlation_map=setup["correlation_map"],
            signal_emitter=setup["emitter"],
            pipeline_submit_fn=setup["submit_fn"],
            outcome_receiver=setup["outcome_receiver"],
            tables=tables or ["events"],
            org_ids=org_ids,
            poll_interval=0.1,
            watermark_store=setup["watermark_store"],
        )

    def test_empty_config_no_work(self, setup: dict[str, Any]) -> None:
        poller = self._make_poller(setup, tables=[])
        conn = MagicMock()

        with patch.object(poller, "_get_connection", return_value=conn):
            with patch.object(poller, "_resolve_org_ids", return_value=["org-1"]):
                poller.shutdown_event.set()
                poller._run_loop()

        setup["submit_fn"].assert_not_called()

    def test_no_new_rows_no_submit(self, setup: dict[str, Any]) -> None:
        poller = self._make_poller(setup, org_ids=["org-1"])
        conn = MagicMock()

        with patch("services.umh.integrations.eos.poller.fetch_events_since", return_value=[]):
            poller._poll_table_org(conn, "events", "org-1")

        setup["submit_fn"].assert_not_called()

    def test_single_new_row_submitted(self, setup: dict[str, Any]) -> None:
        poller = self._make_poller(setup, org_ids=["org-1"])
        conn = MagicMock()
        row = _make_event_row(row_id="r-1", org_id="org-1")

        with patch("services.umh.integrations.eos.poller.fetch_events_since", return_value=[row]):
            poller._poll_table_org(conn, "events", "org-1")

        setup["submit_fn"].assert_called_once()
        call_kwargs = setup["submit_fn"].call_args[1]
        assert call_kwargs["adapter_name"] == "eos"
        assert call_kwargs["operation"] == "noop"

    def test_multi_org_processing(self, setup: dict[str, Any]) -> None:
        poller = self._make_poller(setup, org_ids=["org-A", "org-B"])
        conn = MagicMock()

        row_a = _make_event_row(row_id="r-a", org_id="org-A")
        row_b = _make_event_row(row_id="r-b", org_id="org-B")

        def fetch_side_effect(conn, org_id, since, limit=100):
            if org_id == "org-A":
                return [row_a]
            elif org_id == "org-B":
                return [row_b]
            return []

        with patch("services.umh.integrations.eos.poller.fetch_events_since", side_effect=fetch_side_effect):
            poller._poll_table_org(conn, "events", "org-A")
            poller._poll_table_org(conn, "events", "org-B")

        assert setup["submit_fn"].call_count == 2

    def test_per_org_watermark_advancement(self, setup: dict[str, Any]) -> None:
        poller = self._make_poller(setup, org_ids=["org-A", "org-B"])
        conn = MagicMock()

        row_a = _make_event_row(org_id="org-A", created_at="2026-05-19T12:00:00+00:00")
        row_b = _make_event_row(org_id="org-B", created_at="2026-05-19T14:00:00+00:00")

        with patch("services.umh.integrations.eos.poller.fetch_events_since", return_value=[row_a]):
            poller._poll_table_org(conn, "events", "org-A")
        with patch("services.umh.integrations.eos.poller.fetch_events_since", return_value=[row_b]):
            poller._poll_table_org(conn, "events", "org-B")

        wm_a = setup["watermark_store"].get_watermark("events:org-A")
        wm_b = setup["watermark_store"].get_watermark("events:org-B")

        assert "2026-05-19T12:00:00" in wm_a
        assert "2026-05-19T14:00:00" in wm_b

    def test_ordered_processing(self, setup: dict[str, Any]) -> None:
        poller = self._make_poller(setup, org_ids=["org-1"])
        conn = MagicMock()

        rows = [
            _make_event_row(row_id="r-1", created_at="2026-05-19T10:00:00+00:00"),
            _make_event_row(row_id="r-2", created_at="2026-05-19T11:00:00+00:00"),
            _make_event_row(row_id="r-3", created_at="2026-05-19T12:00:00+00:00"),
        ]

        with patch("services.umh.integrations.eos.poller.fetch_events_since", return_value=rows):
            poller._poll_table_org(conn, "events", "org-1")

        assert setup["submit_fn"].call_count == 3
        wm = setup["watermark_store"].get_watermark("events:org-1")
        assert "2026-05-19T12:00:00" in wm

    def test_jsonl_recording(self, setup: dict[str, Any]) -> None:
        poller = self._make_poller(setup, org_ids=["org-1"])
        conn = MagicMock()
        row = _make_event_row(created_at="2026-05-19T15:00:00+00:00")

        with patch("services.umh.integrations.eos.poller.fetch_events_since", return_value=[row]):
            poller._poll_table_org(conn, "events", "org-1")

        assert setup["watermark_store"].path.exists()
        content = setup["watermark_store"].path.read_text()
        assert "events:org-1" in content
        assert "2026-05-19T15:00:00" in content

    def test_shutdown_event_exits_loop(self, setup: dict[str, Any]) -> None:
        poller = self._make_poller(setup, org_ids=["org-1"])
        poller.shutdown_event.set()

        with patch.object(poller, "_get_connection", return_value=MagicMock()):
            with patch.object(poller, "_resolve_org_ids", return_value=["org-1"]):
                with patch("services.umh.integrations.eos.poller.fetch_events_since", return_value=[]):
                    thread = poller.start()
                    thread.join(timeout=2)
                    assert not thread.is_alive()

    def test_correlation_registered(self, setup: dict[str, Any]) -> None:
        poller = self._make_poller(setup, org_ids=["org-1"])
        conn = MagicMock()
        row = _make_event_row(row_id="r-1", org_id="org-1")

        with patch("services.umh.integrations.eos.poller.fetch_events_since", return_value=[row]):
            poller._poll_table_org(conn, "events", "org-1")

        assert len(setup["correlation_map"]) == 1

    def test_outcome_dispatched(self, setup: dict[str, Any]) -> None:
        poller = self._make_poller(setup, org_ids=["org-1"])
        conn = MagicMock()
        row = _make_event_row(row_id="r-1")

        with patch("services.umh.integrations.eos.poller.fetch_events_since", return_value=[row]):
            poller._poll_table_org(conn, "events", "org-1")

        setup["outcome_receiver"].on_outcome.assert_called_once()
        envelope = setup["outcome_receiver"].on_outcome.call_args[0][0]
        assert envelope.integration_id == "eos"

    def test_submit_failure_does_not_crash(self, setup: dict[str, Any]) -> None:
        setup["submit_fn"].side_effect = RuntimeError("pipeline down")
        poller = self._make_poller(setup, org_ids=["org-1"])
        conn = MagicMock()
        row = _make_event_row()

        with patch("services.umh.integrations.eos.poller.fetch_events_since", return_value=[row]):
            poller._poll_table_org(conn, "events", "org-1")

    def test_connection_error_retries_next_cycle(self, setup: dict[str, Any]) -> None:
        poller = self._make_poller(setup, org_ids=["org-1"])

        call_count = 0

        def failing_connection():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception("connection refused")
            return MagicMock()

        with patch.object(poller, "_get_connection", side_effect=failing_connection):
            with patch.object(poller, "_resolve_org_ids", return_value=["org-1"]):
                poller.shutdown_event.set()
                poller._run_loop()

    def test_watermark_key_composite(self, setup: dict[str, Any]) -> None:
        poller = self._make_poller(setup)

        assert poller._watermark_key("events", "org-1") == "events:org-1"
        assert poller._watermark_key("interactions", "org-2") == "interactions:org-2"
