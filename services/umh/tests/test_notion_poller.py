"""Tests for NotionPoller — background polling, watermark advancement, correlation."""

from __future__ import annotations

import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch
from uuid import UUID, uuid4

import pytest
from httpx import Headers
from notion_client import APIResponseError

from services.umh.integrations.notion.correlation import CorrelationMap
from services.umh.integrations.notion.poller import NotionPoller
from services.umh.integrations.notion.signals import NotionSignalEmitter
from services.umh.integrations.notion.watermarks import WatermarkStore


@dataclass
class FakePipelineResult:
    signal_id: UUID
    trace_id: UUID
    outcome_type: str = "success"


def _make_page(
    page_id: str = "page-1",
    last_edited: str = "2026-05-20T10:00:00.000Z",
    title: str = "Test",
) -> dict[str, Any]:
    return {
        "id": page_id,
        "last_edited_time": last_edited,
        "properties": {
            "Name": {"type": "title", "title": [{"plain_text": title}]},
        },
    }


def _make_source(
    database_id: str = "db-1",
    logical_name: str = "test_db",
    operation: str = "noop",
    poll_interval: float = 30.0,
) -> dict[str, Any]:
    return {
        "database_id": database_id,
        "logical_name": logical_name,
        "operation": operation,
        "poll_interval": poll_interval,
    }


class TestNotionPoller:
    @pytest.fixture()
    def setup(self, tmp_path: Path) -> dict[str, Any]:
        client = MagicMock()
        correlation_map = CorrelationMap()
        emitter = NotionSignalEmitter()
        outcome_receiver = MagicMock()
        watermark_store = WatermarkStore(path=tmp_path / "wm.jsonl")

        submit_results: list[FakePipelineResult] = []

        def fake_submit(*args: Any, **kwargs: Any) -> FakePipelineResult:
            result = FakePipelineResult(signal_id=uuid4(), trace_id=uuid4(), outcome_type="success")
            submit_results.append(result)
            return result

        submit_fn = MagicMock(side_effect=fake_submit)

        return {
            "client": client,
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
        signal_sources: list[dict[str, Any]] | None = None,
    ) -> NotionPoller:
        return NotionPoller(
            client=setup["client"],
            correlation_map=setup["correlation_map"],
            signal_emitter=setup["emitter"],
            pipeline_submit_fn=setup["submit_fn"],
            outcome_receiver=setup["outcome_receiver"],
            signal_sources=signal_sources or [],
            watermark_store=setup["watermark_store"],
        )

    def test_empty_signal_sources_no_work(self, setup: dict[str, Any]) -> None:
        poller = self._make_poller(setup, signal_sources=[])
        poller.shutdown_event.set()
        poller._run_loop()
        setup["client"].request.assert_not_called()
        setup["submit_fn"].assert_not_called()

    def test_no_new_pages_no_submit(self, setup: dict[str, Any]) -> None:
        setup["client"].request.return_value = {"results": [], "has_more": False}
        poller = self._make_poller(setup, signal_sources=[_make_source()])

        poller._poll_source(_make_source())

        setup["submit_fn"].assert_not_called()

    def test_single_new_page_submitted(self, setup: dict[str, Any]) -> None:
        page = _make_page(page_id="p-1", last_edited="2026-05-20T12:00:00.000Z")
        setup["client"].request.return_value = {"results": [page], "has_more": False}

        poller = self._make_poller(setup, signal_sources=[_make_source()])
        poller._poll_source(_make_source())

        setup["submit_fn"].assert_called_once()
        call_kwargs = setup["submit_fn"].call_args
        assert call_kwargs[1]["adapter_name"] == "notion"
        assert call_kwargs[1]["operation"] == "noop"

    def test_correlation_registered(self, setup: dict[str, Any]) -> None:
        page = _make_page(page_id="p-1")
        setup["client"].request.return_value = {"results": [page], "has_more": False}

        poller = self._make_poller(setup, signal_sources=[_make_source()])
        poller._poll_source(_make_source())

        assert len(setup["correlation_map"]) == 1

    def test_watermark_advanced(self, setup: dict[str, Any]) -> None:
        page = _make_page(page_id="p-1", last_edited="2026-05-20T14:00:00.000Z")
        setup["client"].request.return_value = {"results": [page], "has_more": False}

        poller = self._make_poller(setup, signal_sources=[_make_source()])
        poller._poll_source(_make_source(database_id="db-1"))

        wm = setup["watermark_store"].get_watermark("db-1")
        assert wm == "2026-05-20T14:00:00.000Z"

    def test_multiple_pages_ascending_order(self, setup: dict[str, Any]) -> None:
        pages = [
            _make_page(page_id="p-1", last_edited="2026-05-20T10:00:00.000Z"),
            _make_page(page_id="p-2", last_edited="2026-05-20T11:00:00.000Z"),
            _make_page(page_id="p-3", last_edited="2026-05-20T12:00:00.000Z"),
        ]
        setup["client"].request.return_value = {"results": pages, "has_more": False}

        poller = self._make_poller(setup, signal_sources=[_make_source()])
        poller._poll_source(_make_source(database_id="db-1"))

        assert setup["submit_fn"].call_count == 3
        wm = setup["watermark_store"].get_watermark("db-1")
        assert wm == "2026-05-20T12:00:00.000Z"

    def test_429_retries_once(self, setup: dict[str, Any]) -> None:
        rate_limit_error = APIResponseError(
            code="rate_limited",
            status=429,
            message="rate limited",
            headers=Headers(),
            raw_body_text="{}",
        )

        call_count = 0

        def request_side_effect(**kwargs: Any) -> dict:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise rate_limit_error
            return {
                "results": [_make_page()],
                "has_more": False,
            }

        setup["client"].request.side_effect = request_side_effect

        poller = self._make_poller(setup, signal_sources=[_make_source()])
        with patch("services.umh.integrations.notion.poller.time.sleep"):
            poller._poll_source(_make_source())

        assert setup["client"].request.call_count == 2
        setup["submit_fn"].assert_called_once()

    def test_shutdown_event_exits_loop(self, setup: dict[str, Any]) -> None:
        setup["client"].request.return_value = {"results": [], "has_more": False}

        poller = self._make_poller(setup, signal_sources=[_make_source(poll_interval=0.1)])
        poller.shutdown_event.set()

        thread = poller.start()
        thread.join(timeout=2)
        assert not thread.is_alive()

    def test_outcome_writeback_dispatched(self, setup: dict[str, Any]) -> None:
        page = _make_page(page_id="p-1")
        setup["client"].request.return_value = {"results": [page], "has_more": False}

        poller = self._make_poller(setup, signal_sources=[_make_source()])
        poller._poll_source(_make_source())

        setup["outcome_receiver"].on_outcome.assert_called_once()
        envelope = setup["outcome_receiver"].on_outcome.call_args[0][0]
        assert envelope.integration_id == "notion"
        assert envelope.outcome_type == "success"

    def test_submit_failure_does_not_crash(self, setup: dict[str, Any]) -> None:
        page = _make_page(page_id="p-1")
        setup["client"].request.return_value = {"results": [page], "has_more": False}
        setup["submit_fn"].side_effect = RuntimeError("pipeline down")

        poller = self._make_poller(setup, signal_sources=[_make_source()])
        poller._poll_source(_make_source())

    def test_pagination(self, setup: dict[str, Any]) -> None:
        page1 = _make_page(page_id="p-1", last_edited="2026-05-20T10:00:00.000Z")
        page2 = _make_page(page_id="p-2", last_edited="2026-05-20T11:00:00.000Z")

        call_count = 0

        def paginated_request(**kwargs: Any) -> dict:
            nonlocal call_count
            call_count += 1
            body = kwargs.get("body", {})
            if call_count == 1:
                return {"results": [page1], "has_more": True, "next_cursor": "cursor-1"}
            return {"results": [page2], "has_more": False}

        setup["client"].request.side_effect = paginated_request

        poller = self._make_poller(setup, signal_sources=[_make_source()])
        poller._poll_source(_make_source())

        assert setup["submit_fn"].call_count == 2
