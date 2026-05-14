"""Tests for real adapter implementations.

Covers:
1. Discord: correct webhook calls per event type
2. Notion: correct page creation and block appends
3. Workstation: correct state persistence and command execution
4. All: no crashes on external failure
5. All: dispatch_log captures failures correctly
6. Integration: full lifecycle with mocked externals
"""

import sys

sys.path.insert(0, "/opt/OS")

import json
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch, call
from typing import Any

from umh.adapters.contracts import AdapterContext
from umh.adapters.discord_adapter import DiscordAdapter, _format_message
from umh.adapters.notion_adapter import NotionAdapter
from umh.adapters.workstation_adapter import (
    WorkstationAdapter,
    _WORKSPACE_STATE_FILE,
    _load_workspace_state,
    _save_workspace_state,
)
from umh.adapters.registry import AdapterRegistry
from umh.adapters.event_router import route_events
from umh.substrate.event_scheduler import SchedulerEvent


# ─── Fixtures ─────────────────────────────────────────────────────────

_TS = "2026-04-17T12:00:00+00:00"


def _make_event(
    event_type: str,
    payload: dict | None = None,
    metadata: dict | None = None,
) -> SchedulerEvent:
    return SchedulerEvent(
        event_type=event_type,
        session_name="sess_test",
        source="test",
        payload=payload or {},
        metadata=metadata or {"correlation_id": "cor_test"},
    )


def _make_context(**overrides: Any) -> AdapterContext:
    defaults = {
        "state_snapshot": {"entry_transport": "discord", "timestamp": _TS},
        "runtime_session_id": "sess_test",
        "correlation_id": "cor_test",
        "metadata": {"event_id": "ev_test", "source": "test"},
    }
    defaults.update(overrides)
    return AdapterContext(**defaults)


# ═══════════════════════════════════════════════════════════════════════
# 1. DISCORD ADAPTER
# ═══════════════════════════════════════════════════════════════════════


class TestDiscordAdapter:
    def test_supports_all_event_types(self) -> None:
        adapter = DiscordAdapter()
        assert adapter.supports("open_day_started")
        assert adapter.supports("ritual_step_executed")
        assert adapter.supports("close_day_started")
        assert adapter.supports("ritual_completed")
        assert not adapter.supports("unknown_event")

    @patch("umh.adapters.discord_adapter.post_to_webhook", create=True)
    def test_open_day_calls_webhook(self, mock_post: MagicMock) -> None:
        with patch(
            "umh.runtime_engine.discord_utils.post_to_webhook", return_value=True
        ) as mock_webhook:
            adapter = DiscordAdapter(webhook_url="https://test.webhook")
            event = _make_event(
                "open_day_started", payload={"summary": "Morning session"}
            )
            ctx = _make_context()

            adapter.handle(event, ctx)

            mock_webhook.assert_called_once()
            call_kwargs = mock_webhook.call_args
            assert "Session started" in call_kwargs.kwargs.get(
                "content", call_kwargs.args[0] if call_kwargs.args else ""
            )

    @patch("umh.runtime_engine.discord_utils.post_to_webhook", return_value=True)
    def test_step_sends_step_name(self, mock_webhook: MagicMock) -> None:
        adapter = DiscordAdapter(webhook_url="https://test.webhook")
        event = _make_event(
            "ritual_step_executed",
            payload={"step_name": "load_presence_state"},
        )
        ctx = _make_context()

        adapter.handle(event, ctx)

        content = mock_webhook.call_args.kwargs.get(
            "content",
            mock_webhook.call_args.args[0] if mock_webhook.call_args.args else "",
        )
        assert "load_presence_state" in content

    @patch("umh.runtime_engine.discord_utils.post_to_webhook", return_value=True)
    def test_close_day_sends_message(self, mock_webhook: MagicMock) -> None:
        adapter = DiscordAdapter(webhook_url="https://test.webhook")
        event = _make_event("close_day_started")
        ctx = _make_context()

        adapter.handle(event, ctx)

        mock_webhook.assert_called_once()

    @patch("umh.runtime_engine.discord_utils.post_to_webhook", return_value=True)
    def test_ritual_completed_sends_summary(self, mock_webhook: MagicMock) -> None:
        adapter = DiscordAdapter(webhook_url="https://test.webhook")
        event = _make_event(
            "ritual_completed",
            payload={
                "steps_executed": ["a", "b", "c"],
                "presence_after": "active_station",
            },
        )
        ctx = _make_context()

        adapter.handle(event, ctx)

        content = mock_webhook.call_args.kwargs.get(
            "content",
            mock_webhook.call_args.args[0] if mock_webhook.call_args.args else "",
        )
        assert "3 steps" in content
        assert "active_station" in content

    @patch(
        "umh.runtime_engine.discord_utils.post_to_webhook", side_effect=Exception("Network error")
    )
    def test_webhook_failure_does_not_raise(self, mock_webhook: MagicMock) -> None:
        adapter = DiscordAdapter(webhook_url="https://test.webhook")
        event = _make_event("open_day_started")
        ctx = _make_context()

        # Must not raise
        adapter.handle(event, ctx)

    def test_format_message_open(self) -> None:
        event = _make_event("open_day_started", payload={"summary": "brief"})
        ctx = _make_context()
        msg = _format_message(event, ctx)
        assert "Session started" in msg

    def test_format_message_step(self) -> None:
        event = _make_event(
            "ritual_step_executed", payload={"step_name": "build_briefing"}
        )
        ctx = _make_context()
        msg = _format_message(event, ctx)
        assert "build_briefing" in msg


# ═══════════════════════════════════════════════════════════════════════
# 2. NOTION ADAPTER
# ═══════════════════════════════════════════════════════════════════════


class TestNotionAdapter:
    def test_supports_all_event_types(self) -> None:
        adapter = NotionAdapter()
        assert adapter.supports("open_day_started")
        assert adapter.supports("ritual_step_executed")
        assert adapter.supports("close_day_started")
        assert adapter.supports("ritual_completed")
        assert not adapter.supports("unknown_event")

    @patch(
        "umh.runtime_engine.notion_publisher._create_page", return_value="https://notion.so/abc123"
    )
    @patch("umh.runtime_engine.notion_publisher._heading")
    @patch("umh.runtime_engine.notion_publisher._paragraph")
    def test_open_day_creates_page(
        self,
        mock_para: MagicMock,
        mock_heading: MagicMock,
        mock_create: MagicMock,
    ) -> None:
        mock_heading.return_value = {"type": "heading_2"}
        mock_para.return_value = {"type": "paragraph"}

        adapter = NotionAdapter(activity_db_id="test-db-id")
        event = _make_event("open_day_started", payload={"summary": "Morning"})
        ctx = _make_context()

        adapter.handle(event, ctx)

        mock_create.assert_called_once()
        assert mock_create.call_args.args[0] == "test-db-id"

    @patch("umh.runtime_engine.notion_publisher._api_call", return_value={})
    @patch("umh.runtime_engine.notion_publisher._bulleted", return_value={"type": "bulleted"})
    def test_step_appends_to_page(
        self, mock_bulleted: MagicMock, mock_api: MagicMock
    ) -> None:
        adapter = NotionAdapter(activity_db_id="test-db-id")
        adapter._active_page_id = "page123"
        event = _make_event(
            "ritual_step_executed", payload={"step_name": "build_briefing"}
        )
        ctx = _make_context()

        adapter.handle(event, ctx)

        mock_api.assert_called_once()
        assert "PATCH" in str(mock_api.call_args)

    def test_step_noop_without_active_page(self) -> None:
        """No active page → step append is a no-op, not a crash."""
        adapter = NotionAdapter(activity_db_id="test-db-id")
        adapter._active_page_id = ""
        event = _make_event("ritual_step_executed", payload={"step_name": "x"})
        ctx = _make_context()

        # Must not raise
        adapter.handle(event, ctx)

    @patch("umh.runtime_engine.notion_publisher._create_page", side_effect=Exception("API down"))
    def test_notion_failure_does_not_raise(self, mock_create: MagicMock) -> None:
        adapter = NotionAdapter(activity_db_id="test-db-id")
        event = _make_event("open_day_started")
        ctx = _make_context()

        # Must not raise
        adapter.handle(event, ctx)

    def test_no_db_id_graceful(self) -> None:
        """Missing DB ID → logs warning, does not crash."""
        adapter = NotionAdapter(activity_db_id="")
        event = _make_event("open_day_started")
        ctx = _make_context()

        # Must not raise
        adapter.handle(event, ctx)


# ═══════════════════════════════════════════════════════════════════════
# 3. WORKSTATION ADAPTER
# ═══════════════════════════════════════════════════════════════════════


class TestWorkstationAdapter:
    def test_supports_all_event_types(self) -> None:
        adapter = WorkstationAdapter()
        assert adapter.supports("open_day_started")
        assert adapter.supports("ritual_step_executed")
        assert adapter.supports("close_day_started")
        assert adapter.supports("ritual_completed")
        assert not adapter.supports("unknown_event")

    @patch("umh.adapters.workstation_adapter._save_workspace_state")
    @patch(
        "umh.adapters.workstation_adapter._load_workspace_state",
        return_value={},
    )
    @patch(
        "umh.adapters.workstation_adapter._get_open_commands",
        return_value=[],
    )
    def test_open_workspace_saves_state(
        self,
        mock_cmds: MagicMock,
        mock_load: MagicMock,
        mock_save: MagicMock,
    ) -> None:
        adapter = WorkstationAdapter()
        event = _make_event("open_day_started")
        ctx = _make_context()

        adapter.handle(event, ctx)

        mock_save.assert_called_once()
        saved = mock_save.call_args.args[0]
        assert saved["session_id"] == "sess_test"
        assert saved["status"] == "active"

    @patch(
        "umh.adapters.workstation_adapter._run_command",
        return_value=True,
    )
    @patch("umh.adapters.workstation_adapter._save_workspace_state")
    @patch(
        "umh.adapters.workstation_adapter._load_workspace_state",
        return_value={},
    )
    @patch(
        "umh.adapters.workstation_adapter._get_open_commands",
        return_value=[{"cmd": "echo hello", "label": "test"}],
    )
    def test_open_runs_configured_commands(
        self,
        mock_cmds: MagicMock,
        mock_load: MagicMock,
        mock_save: MagicMock,
        mock_run: MagicMock,
    ) -> None:
        adapter = WorkstationAdapter()
        event = _make_event("open_day_started")
        ctx = _make_context()

        adapter.handle(event, ctx)

        mock_run.assert_called_once_with("echo hello", "test")

    @patch("umh.adapters.workstation_adapter._save_workspace_state")
    @patch(
        "umh.adapters.workstation_adapter._load_workspace_state",
        return_value={"session_id": "s", "status": "active"},
    )
    def test_close_updates_status(
        self, mock_load: MagicMock, mock_save: MagicMock
    ) -> None:
        adapter = WorkstationAdapter()
        event = _make_event("close_day_started")
        ctx = _make_context()

        adapter.handle(event, ctx)

        saved = mock_save.call_args.args[0]
        assert saved["status"] == "closing"

    @patch("umh.adapters.workstation_adapter._save_workspace_state")
    @patch(
        "umh.adapters.workstation_adapter._load_workspace_state",
        return_value={"session_id": "s", "status": "closing"},
    )
    def test_finalize_marks_closed(
        self, mock_load: MagicMock, mock_save: MagicMock
    ) -> None:
        adapter = WorkstationAdapter()
        event = _make_event("ritual_completed")
        ctx = _make_context()

        adapter.handle(event, ctx)

        saved = mock_save.call_args.args[0]
        assert saved["status"] == "closed"

    def test_step_noop_does_not_crash(self) -> None:
        """Step action is a no-op on VPS — must not crash."""
        adapter = WorkstationAdapter()
        event = _make_event(
            "ritual_step_executed", payload={"step_name": "build_briefing"}
        )
        ctx = _make_context()

        adapter.handle(event, ctx)


# ═══════════════════════════════════════════════════════════════════════
# 4. DISPATCH LOG CAPTURES FAILURES
# ═══════════════════════════════════════════════════════════════════════


class TestDispatchLogOnFailure:
    @patch(
        "umh.runtime_engine.discord_utils.post_to_webhook",
        side_effect=Exception("Discord down"),
    )
    def test_discord_internal_failure_still_ok_in_dispatch(
        self, mock_webhook: MagicMock
    ) -> None:
        """DiscordAdapter catches exceptions internally — router sees 'ok'.

        The adapter's try/except is by design: it logs the error and
        returns normally. The router only records 'error' when an adapter
        raises THROUGH to the router. This test confirms the graceful
        failure behavior.
        """
        registry = AdapterRegistry()
        registry.register(DiscordAdapter(webhook_url="https://test"))

        event = _make_event("open_day_started")
        state = {"entry_transport": "discord"}
        log = route_events([event], state, registry)

        assert len(log) == 1
        # Adapter swallows the exception → router sees success
        assert log[0]["status"] == "ok"
        assert log[0]["adapter"] == "DiscordAdapter"

    def test_unprotected_adapter_failure_logged_as_error(self) -> None:
        """An adapter that raises through to the router gets 'error' status."""

        class _RaisingAdapter:
            def supports(self, event_type: str) -> bool:
                return event_type == "open_day_started"

            def handle(self, event: Any, context: AdapterContext) -> None:
                raise RuntimeError("Unhandled crash")

        registry = AdapterRegistry()
        registry.register(_RaisingAdapter())

        event = _make_event("open_day_started")
        log = route_events([event], {}, registry)

        assert len(log) == 1
        assert log[0]["status"] == "error"


# ═══════════════════════════════════════════════════════════════════════
# 5. FULL LIFECYCLE INTEGRATION (MOCKED EXTERNALS)
# ═══════════════════════════════════════════════════════════════════════


class TestFullLifecycleWithRealAdapters:
    @patch("umh.runtime_engine.discord_utils.post_to_webhook", return_value=True)
    @patch("umh.runtime_engine.notion_publisher._create_page", return_value="https://notion.so/abc")
    @patch("umh.runtime_engine.notion_publisher._api_call", return_value={})
    @patch("umh.runtime_engine.notion_publisher._heading", return_value={"type": "heading_2"})
    @patch("umh.runtime_engine.notion_publisher._paragraph", return_value={"type": "paragraph"})
    @patch("umh.runtime_engine.notion_publisher._bulleted", return_value={"type": "bulleted"})
    @patch("umh.runtime_engine.notion_publisher._divider", return_value={"type": "divider"})
    @patch("umh.adapters.workstation_adapter._save_workspace_state")
    @patch(
        "umh.adapters.workstation_adapter._load_workspace_state",
        return_value={},
    )
    @patch(
        "umh.adapters.workstation_adapter._get_open_commands",
        return_value=[],
    )
    def test_open_day_lifecycle_all_adapters(self, *mocks: MagicMock) -> None:
        """Full open_day through lifecycle with all 3 real adapters."""
        from umh.runtime_engine.adapters import build_default_registry
        from umh.runtime_loop.context import RuntimeContext
        from umh.runtime_loop.lifecycle import run_lifecycle
        from umh.substrate.runtime_state_store import RuntimeStateStore

        store = RuntimeStateStore()
        registry = build_default_registry()
        ctx = RuntimeContext(
            runtime_session_id="sess_integration",
            transport="discord",
            timestamp=_TS,
            correlation_id="cor_integration",
            trigger="manual",
        )

        output = run_lifecycle(store, registry, ctx, "open_day")

        # All adapters should have been called
        adapter_names = {d["adapter"] for d in output["dispatch_log"] if d["adapter"]}
        assert "DiscordAdapter" in adapter_names
        assert "NotionAdapter" in adapter_names
        assert "WorkstationAdapter" in adapter_names

        # 10 events × 3 adapters = 30 dispatch entries
        assert len(output["dispatch_log"]) == 30

        # All should succeed (externals are mocked to succeed)
        assert all(d["status"] == "ok" for d in output["dispatch_log"])

    @patch("umh.runtime_engine.discord_utils.post_to_webhook", return_value=True)
    @patch("umh.runtime_engine.notion_publisher._create_page", return_value="https://notion.so/abc")
    @patch("umh.runtime_engine.notion_publisher._api_call", return_value={})
    @patch("umh.runtime_engine.notion_publisher._heading", return_value={"type": "heading_2"})
    @patch("umh.runtime_engine.notion_publisher._paragraph", return_value={"type": "paragraph"})
    @patch("umh.runtime_engine.notion_publisher._bulleted", return_value={"type": "bulleted"})
    @patch("umh.runtime_engine.notion_publisher._divider", return_value={"type": "divider"})
    @patch("umh.adapters.workstation_adapter._save_workspace_state")
    @patch(
        "umh.adapters.workstation_adapter._load_workspace_state",
        return_value={},
    )
    @patch(
        "umh.adapters.workstation_adapter._get_open_commands",
        return_value=[],
    )
    def test_close_day_lifecycle_all_adapters(self, *mocks: MagicMock) -> None:
        """Full close_day through lifecycle with all 3 real adapters."""
        from umh.runtime_engine.adapters import build_default_registry
        from umh.runtime_loop.context import RuntimeContext
        from umh.runtime_loop.lifecycle import run_lifecycle
        from umh.substrate.runtime_state_store import RuntimeStateStore

        store = RuntimeStateStore()
        registry = build_default_registry()
        ctx = RuntimeContext(
            runtime_session_id="sess_integration",
            transport="discord",
            timestamp=_TS,
            correlation_id="cor_integration",
            trigger="manual",
        )

        output = run_lifecycle(store, registry, ctx, "close_day")

        assert output["events_count"] == 10
        assert len(output["dispatch_log"]) == 30
        assert all(d["status"] == "ok" for d in output["dispatch_log"])
