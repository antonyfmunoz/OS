"""Tests for Notion outcome writeback — correlation map, receiver, writeback logic."""

from __future__ import annotations

import os
from typing import Any
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from httpx import Headers
from notion_client import APIResponseError

from services.umh.integrations.notion.correlation import CorrelationMap, WritebackTarget
from substrate.sockets.envelopes import OutcomeEnvelope
from substrate.sockets.protocols import OutcomeReceiver


class TestCorrelationMap:
    def test_register_and_lookup(self) -> None:
        m = CorrelationMap()
        cid = uuid4()
        target = WritebackTarget(page_id="page-1")
        m.register(cid, target)
        assert m.lookup(cid) == target

    def test_lookup_missing_returns_none(self) -> None:
        m = CorrelationMap()
        assert m.lookup(uuid4()) is None

    def test_remove(self) -> None:
        m = CorrelationMap()
        cid = uuid4()
        m.register(cid, WritebackTarget(page_id="page-1"))
        m.remove(cid)
        assert m.lookup(cid) is None

    def test_remove_missing_is_noop(self) -> None:
        m = CorrelationMap()
        m.remove(uuid4())

    def test_len(self) -> None:
        m = CorrelationMap()
        assert len(m) == 0
        cid = uuid4()
        m.register(cid, WritebackTarget(page_id="page-1"))
        assert len(m) == 1

    def test_writeback_target_defaults(self) -> None:
        t = WritebackTarget(page_id="page-1")
        assert t.integration == "notion"


class TestNotionOutcomeReceiver:
    @pytest.fixture()
    def setup(self) -> Any:
        client = MagicMock()
        correlation_map = CorrelationMap()

        from services.umh.integrations.notion.outcomes import NotionOutcomeReceiver

        receiver = NotionOutcomeReceiver(client, correlation_map)
        return receiver, client, correlation_map

    def _make_envelope(
        self,
        correlation_id: Any = None,
        outcome_type: str = "success",
        summary: str = "test completed",
    ) -> OutcomeEnvelope:
        return OutcomeEnvelope(
            outcome_id=uuid4(),
            signal_id=uuid4(),
            trace_id=uuid4(),
            integration_id="notion",
            outcome_type=outcome_type,
            summary=summary,
            correlation_id=correlation_id,
        )

    def test_satisfies_protocol(self, setup: Any) -> None:
        receiver, _, _ = setup
        assert isinstance(receiver, OutcomeReceiver)

    def test_integration_id(self, setup: Any) -> None:
        receiver, _, _ = setup
        assert receiver.integration_id == "notion"

    def test_accepts_all_outcomes(self, setup: Any) -> None:
        receiver, _, _ = setup
        assert receiver.accepts_outcomes() == []

    def test_no_correlation_id_skips_writeback(self, setup: Any) -> None:
        receiver, client, _ = setup
        envelope = self._make_envelope(correlation_id=None)
        receiver.on_outcome(envelope)
        client.pages.update.assert_not_called()

    def test_correlation_not_in_map_skips_writeback(self, setup: Any) -> None:
        receiver, client, _ = setup
        envelope = self._make_envelope(correlation_id=uuid4())
        receiver.on_outcome(envelope)
        client.pages.update.assert_not_called()

    def test_non_notion_target_skips_writeback(self, setup: Any) -> None:
        receiver, client, correlation_map = setup
        cid = uuid4()
        correlation_map.register(cid, WritebackTarget(page_id="page-1", integration="slack"))
        envelope = self._make_envelope(correlation_id=cid)
        receiver.on_outcome(envelope)
        client.pages.update.assert_not_called()

    def test_success_outcome_updates_page_and_appends_block(self, setup: Any) -> None:
        receiver, client, correlation_map = setup
        cid = uuid4()
        correlation_map.register(cid, WritebackTarget(page_id="page-99"))

        envelope = self._make_envelope(
            correlation_id=cid,
            outcome_type="success",
            summary="operation completed successfully",
        )

        receiver.on_outcome(envelope)

        client.pages.update.assert_called_once()
        update_kwargs = client.pages.update.call_args[1]
        assert update_kwargs["page_id"] == "page-99"
        assert update_kwargs["properties"]["UMH Status"]["select"]["name"] == "Success"

        client.blocks.children.append.assert_called_once()
        append_kwargs = client.blocks.children.append.call_args[1]
        assert append_kwargs["block_id"] == "page-99"
        callout = append_kwargs["children"][0]["callout"]
        text = callout["rich_text"][0]["text"]["content"]
        assert "success" in text
        assert str(envelope.trace_id) in text

        assert correlation_map.lookup(cid) is None

    def test_failure_outcome_sets_error_status(self, setup: Any) -> None:
        receiver, client, correlation_map = setup
        cid = uuid4()
        correlation_map.register(cid, WritebackTarget(page_id="page-99"))

        envelope = self._make_envelope(
            correlation_id=cid,
            outcome_type="failure",
            summary="adapter error",
        )

        receiver.on_outcome(envelope)

        update_kwargs = client.pages.update.call_args[1]
        assert update_kwargs["properties"]["UMH Status"]["select"]["name"] == "Error"

    def test_governance_denied_sets_blocked_status(self, setup: Any) -> None:
        receiver, client, correlation_map = setup
        cid = uuid4()
        correlation_map.register(cid, WritebackTarget(page_id="page-99"))

        envelope = self._make_envelope(
            correlation_id=cid,
            outcome_type="governance_denied",
            summary="risk too high",
        )

        receiver.on_outcome(envelope)

        update_kwargs = client.pages.update.call_args[1]
        assert update_kwargs["properties"]["UMH Status"]["select"]["name"] == "Blocked"

    def test_timeout_outcome_sets_timeout_status(self, setup: Any) -> None:
        receiver, client, correlation_map = setup
        cid = uuid4()
        correlation_map.register(cid, WritebackTarget(page_id="page-99"))

        envelope = self._make_envelope(
            correlation_id=cid,
            outcome_type="timeout",
            summary="adapter timed out",
        )

        receiver.on_outcome(envelope)

        update_kwargs = client.pages.update.call_args[1]
        assert update_kwargs["properties"]["UMH Status"]["select"]["name"] == "Timeout"

    def test_unknown_outcome_type_sets_unknown_status(self, setup: Any) -> None:
        receiver, client, correlation_map = setup
        cid = uuid4()
        correlation_map.register(cid, WritebackTarget(page_id="page-99"))

        envelope = self._make_envelope(
            correlation_id=cid,
            outcome_type="something_new",
            summary="unexpected",
        )

        receiver.on_outcome(envelope)

        update_kwargs = client.pages.update.call_args[1]
        assert update_kwargs["properties"]["UMH Status"]["select"]["name"] == "Unknown"

    def test_429_retries_once(self, setup: Any) -> None:
        receiver, client, correlation_map = setup
        cid = uuid4()
        correlation_map.register(cid, WritebackTarget(page_id="page-99"))

        rate_limit_error = APIResponseError(
            code="rate_limited",
            status=429,
            message="rate limited",
            headers=Headers(),
            raw_body_text="{}",
        )

        call_count = 0

        def update_side_effect(**kwargs: Any) -> dict:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise rate_limit_error
            return {"id": "page-99"}

        client.pages.update.side_effect = update_side_effect

        envelope = self._make_envelope(correlation_id=cid, outcome_type="success")

        with patch("services.umh.integrations.notion.outcomes.time.sleep"):
            receiver.on_outcome(envelope)

        assert client.pages.update.call_count == 2
        assert correlation_map.lookup(cid) is None

    def test_non_429_error_does_not_crash(self, setup: Any) -> None:
        receiver, client, correlation_map = setup
        cid = uuid4()
        correlation_map.register(cid, WritebackTarget(page_id="page-99"))

        client.pages.update.side_effect = APIResponseError(
            code="object_not_found",
            status=404,
            message="page not found",
            headers=Headers(),
            raw_body_text="{}",
        )

        envelope = self._make_envelope(correlation_id=cid, outcome_type="success")

        receiver.on_outcome(envelope)

        assert correlation_map.lookup(cid) is not None

    def test_generic_exception_does_not_crash(self, setup: Any) -> None:
        receiver, client, correlation_map = setup
        cid = uuid4()
        correlation_map.register(cid, WritebackTarget(page_id="page-99"))

        client.pages.update.side_effect = ConnectionError("network down")

        envelope = self._make_envelope(correlation_id=cid, outcome_type="success")

        receiver.on_outcome(envelope)

        assert correlation_map.lookup(cid) is not None

    def test_callout_icon_differs_for_success_vs_error(self, setup: Any) -> None:
        receiver, client, correlation_map = setup

        cid1 = uuid4()
        correlation_map.register(cid1, WritebackTarget(page_id="page-1"))
        envelope1 = self._make_envelope(correlation_id=cid1, outcome_type="success")
        receiver.on_outcome(envelope1)
        callout1 = client.blocks.children.append.call_args[1]["children"][0]["callout"]

        client.reset_mock()

        cid2 = uuid4()
        correlation_map.register(cid2, WritebackTarget(page_id="page-2"))
        envelope2 = self._make_envelope(correlation_id=cid2, outcome_type="failure")
        receiver.on_outcome(envelope2)
        callout2 = client.blocks.children.append.call_args[1]["children"][0]["callout"]

        assert callout1["icon"]["emoji"] != callout2["icon"]["emoji"]
