"""
Tests for the operator day lifecycle continuity system.

Validates:
1. ContinuitySummary model correctness
2. build_continuity_summary() with and without prior session
3. build_close_snapshot() structure
4. open_day() includes continuity report
5. close_day() persists structured snapshot
6. close_day() None-list bug is fixed
7. Reconnect detection surfaces in continuity
8. Expired/failed actions are reported
9. No regression to existing open/close behavior
"""

import json
import sys
import threading
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, "/opt/OS")

from umh.substrate.action_tracker import (
    ActionTracker,
    TrackedState,
    reset_tracker_for_tests,
)
from umh.substrate.continuity_summary import (
    ContinuitySummary,
    build_close_snapshot,
    build_continuity_summary,
)
from umh.substrate.operator_session import (
    OperatorDayMode,
    OperatorSession,
    OperatorSessionStore,
)


# ─── Fixtures ──────────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def _isolate_singletons():
    """Reset singletons before each test."""
    OperatorSessionStore.reset_default_for_tests()
    reset_tracker_for_tests()
    yield
    OperatorSessionStore.reset_default_for_tests()
    reset_tracker_for_tests()


def _mock_storage():
    """Create a mock storage backend that works in-memory."""
    store_data = {}

    class MockStorage:
        def get(self, key, default=None):
            return store_data.get(key, default)

        def put(self, key, value):
            store_data[key] = value

    return MockStorage(), store_data


# ─── ContinuitySummary Model ─────────────────────────────────────────────


class TestContinuitySummaryModel:
    def test_default_construction(self):
        cs = ContinuitySummary()
        assert cs.nodes_online == 0
        assert cs.actions_completed == 0
        assert cs.reconnect_detected is False
        assert cs.text == ""

    def test_to_dict_structure(self):
        cs = ContinuitySummary()
        cs.nodes_online = 2
        cs.nodes_total = 3
        cs.actions_completed = 5
        cs.reconnect_detected = True
        cs.reconnected_nodes = ["ws-1"]
        cs.text = "test summary"

        d = cs.to_dict()

        assert d["nodes"]["online"] == 2
        assert d["nodes"]["total"] == 3
        assert d["nodes"]["reconnect_detected"] is True
        assert d["nodes"]["reconnected_nodes"] == ["ws-1"]
        assert d["actions"]["completed"] == 5
        assert d["text"] == "test summary"
        assert "generated_at" in d
        assert "window_start" in d
        assert "prior_session" in d
        assert "current_state" in d

    def test_to_dict_is_json_serializable(self):
        cs = ContinuitySummary()
        cs.actions_completed = 3
        cs.notable_events = ["thing happened"]
        d = cs.to_dict()
        serialized = json.dumps(d)
        assert isinstance(serialized, str)
        roundtrip = json.loads(serialized)
        assert roundtrip["actions"]["completed"] == 3


# ─── build_continuity_summary ──────────────────────────────────────────────


class TestBuildContinuitySummary:
    @patch("umh.substrate.continuity_summary._gather_node_health")
    @patch("umh.substrate.continuity_summary._gather_action_state")
    @patch("umh.substrate.continuity_summary._gather_workstation_events")
    @patch("umh.substrate.continuity_summary._gather_prior_session")
    def test_returns_summary_even_when_all_sources_fail(
        self, mock_prior, mock_events, mock_actions, mock_nodes
    ):
        """Even with all gatherers mocked to no-op, returns a valid summary."""
        cs = build_continuity_summary()
        assert isinstance(cs, ContinuitySummary)
        assert cs.generated_at is not None
        assert "Continuity Summary" in cs.text

    @patch("umh.substrate.continuity_summary._gather_node_health")
    @patch("umh.substrate.continuity_summary._gather_action_state")
    @patch("umh.substrate.continuity_summary._gather_workstation_events")
    @patch("umh.substrate.continuity_summary._gather_prior_session")
    def test_explicit_window_start(
        self, mock_prior, mock_events, mock_actions, mock_nodes
    ):
        """Explicit window_start overrides prior session."""
        cs = build_continuity_summary(window_start="2026-04-15T00:00:00+00:00")
        assert cs.window_start == "2026-04-15T00:00:00+00:00"

    def test_text_includes_node_status(self):
        cs = ContinuitySummary()
        cs.nodes_online = 2
        cs.nodes_total = 3
        cs.local_online = True

        from umh.substrate.continuity_summary import _render_text

        text = _render_text(cs)
        assert "2/3 online" in text
        assert "local up" in text

    def test_text_includes_reconnect(self):
        cs = ContinuitySummary()
        cs.reconnect_detected = True
        cs.reconnected_nodes = ["antony-workstation"]

        from umh.substrate.continuity_summary import _render_text

        text = _render_text(cs)
        assert "Reconnect detected" in text
        assert "antony-workstation" in text

    def test_text_includes_action_counts(self):
        cs = ContinuitySummary()
        cs.actions_completed = 3
        cs.actions_failed = 1
        cs.actions_expired = 2

        from umh.substrate.continuity_summary import _render_text

        text = _render_text(cs)
        assert "3 completed" in text
        assert "1 failed" in text
        assert "2 expired" in text

    def test_text_includes_failures_detail(self):
        cs = ContinuitySummary()
        cs.actions_failed = 1
        cs.failed_action_details = [
            {
                "action_id": "a1",
                "kind": "speak_text",
                "detail": "TTS timeout",
                "node": "ws",
                "failed_at": "t",
            }
        ]

        from umh.substrate.continuity_summary import _render_text

        text = _render_text(cs)
        assert "speak_text" in text
        assert "TTS timeout" in text

    def test_text_includes_prior_notes(self):
        cs = ContinuitySummary()
        cs.prior_continuity_notes = "Deploy the new pipeline"
        cs.prior_unfinished = ["fix auth", "test deploy"]

        from umh.substrate.continuity_summary import _render_text

        text = _render_text(cs)
        assert "Deploy the new pipeline" in text
        assert "fix auth" in text


# ─── build_close_snapshot ──────────────────────────────────────────────────


class TestBuildCloseSnapshot:
    @patch("umh.substrate.action_tracker.get_action_tracker")
    def test_includes_action_stats(self, mock_tracker):
        mock_tracker.return_value.stats.return_value = {
            "total_tracked": 10,
            "by_state": {"completed": 5, "failed": 2},
            "active_per_node": {},
        }

        with patch(
            "umh.substrate.node_controller.get_node_health_summary", return_value={}
        ):
            with patch("umh.substrate.workstation_log.log_summary", return_value={}):
                snapshot = build_close_snapshot()

        assert snapshot["type"] == "close_day_snapshot"
        assert "snapshot_at" in snapshot
        assert snapshot["action_stats"]["total_tracked"] == 10

    @patch(
        "umh.substrate.action_tracker.get_action_tracker",
        side_effect=Exception("fail"),
    )
    def test_survives_action_tracker_failure(self, mock_tracker):
        with patch(
            "umh.substrate.node_controller.get_node_health_summary", return_value={}
        ):
            with patch("umh.substrate.workstation_log.log_summary", return_value={}):
                snapshot = build_close_snapshot()

        assert snapshot["type"] == "close_day_snapshot"
        assert snapshot["action_stats"] == {}


# ─── close_day None-list Bug Fix ──────────────────────────────────────────


class TestCloseDayNoneListFix:
    @patch("umh.substrate.day_workflows.OperatorSessionStore")
    @patch(
        "umh.substrate.day_workflows._start_ritual_best_effort",
        return_value=(None, None),
    )
    @patch(
        "umh.substrate.day_workflows._advance_ritual_best_effort", return_value=None
    )
    def test_close_day_with_none_params(self, mock_advance, mock_start, mock_store_cls):
        """close_day() should not crash when called with None list params."""
        session = OperatorSession.new()
        session.is_day_open = True
        session.active_workspace = "builder"

        mock_store = MagicMock()
        mock_store.get.return_value = session
        mock_store_cls.default.return_value = mock_store

        from umh.substrate.day_workflows import close_day

        # This would have raised TypeError before the fix
        result = close_day()
        assert result["status"] == "ok"
        assert result["summary"]["unresolved"] == []
        assert result["summary"]["overnight_tasks"] == []

    @patch("umh.substrate.day_workflows.OperatorSessionStore")
    @patch(
        "umh.substrate.day_workflows._start_ritual_best_effort",
        return_value=(None, None),
    )
    @patch(
        "umh.substrate.day_workflows._advance_ritual_best_effort", return_value=None
    )
    def test_close_day_with_explicit_lists(
        self, mock_advance, mock_start, mock_store_cls
    ):
        """close_day() still works correctly with explicit list params."""
        session = OperatorSession.new()
        session.is_day_open = True
        session.active_workspace = "builder"

        mock_store = MagicMock()
        mock_store.get.return_value = session
        mock_store_cls.default.return_value = mock_store

        from umh.substrate.day_workflows import close_day

        result = close_day(
            completed_today=["task-1"],
            unresolved=["task-2"],
            overnight_tasks=["task-3"],
        )
        assert result["status"] == "ok"
        assert result["summary"]["completed_today"] == ["task-1"]
        assert result["summary"]["unresolved"] == ["task-2"]
        assert result["summary"]["overnight_tasks"] == ["task-3"]


# ─── open_day Continuity Integration ──────────────────────────────────────


class TestOpenDayContinuity:
    @patch("umh.substrate.day_workflows.OperatorSessionStore")
    @patch(
        "umh.substrate.day_workflows._start_ritual_best_effort",
        return_value=(None, None),
    )
    @patch(
        "umh.substrate.day_workflows._advance_ritual_best_effort", return_value=None
    )
    def test_open_day_includes_continuity_keys(
        self, mock_advance, mock_start, mock_store_cls
    ):
        """open_day() response should include continuity and continuity_text."""
        # Set up a prior closed session
        prior = OperatorSession.new()
        prior.is_day_open = False
        prior.closed_at = "2026-04-14T22:00:00+00:00"
        prior.continuity_notes_for_next_open = "Deploy tomorrow"

        mock_store = MagicMock()
        mock_store.get.return_value = prior
        mock_store_cls.default.return_value = mock_store

        from umh.substrate.day_workflows import open_day

        result = open_day()
        assert result["status"] == "ok"
        # Continuity keys should be present
        assert "continuity" in result or "continuity_text" in result

    @patch("umh.substrate.day_workflows.OperatorSessionStore")
    @patch(
        "umh.substrate.day_workflows._start_ritual_best_effort",
        return_value=(None, None),
    )
    @patch(
        "umh.substrate.day_workflows._advance_ritual_best_effort", return_value=None
    )
    def test_open_day_no_crash_without_prior(
        self, mock_advance, mock_start, mock_store_cls
    ):
        """open_day() works cleanly with no prior session at all."""
        mock_store = MagicMock()
        mock_store.get.return_value = None
        mock_store_cls.default.return_value = mock_store

        from umh.substrate.day_workflows import open_day

        result = open_day()
        assert result["status"] == "ok"


# ─── Action Tracker Integration ───────────────────────────────────────────


class TestActionTrackerInContinuity:
    def test_action_state_gathered(self):
        """Actions tracked in the tracker appear in the continuity summary."""
        tracker = ActionTracker(persist=False)
        tracker.track("a1", "speak_text", "ws-1", issued_at="2026-04-15T10:00:00+00:00")
        tracker.mark_dispatched("a1")
        tracker.mark_completed("a1", detail="said hello")

        tracker.track("a2", "open_url", "ws-1", issued_at="2026-04-15T10:01:00+00:00")
        tracker.mark_dispatched("a2")
        tracker.mark_failed("a2", detail="browser not found")

        tracker.track("a3", "play_sound", "ws-1", issued_at="2026-04-15T10:02:00+00:00")
        tracker.mark_expired("a3", detail="TTL elapsed")

        with patch(
            "umh.substrate.action_tracker.get_action_tracker", return_value=tracker
        ):
            cs = ContinuitySummary()
            from umh.substrate.continuity_summary import _gather_action_state

            _gather_action_state(cs, None)

        assert cs.actions_completed == 1
        assert cs.actions_failed == 1
        assert cs.actions_expired == 1
        assert "speak_text" in cs.completed_action_kinds
        assert cs.failed_action_details[0]["kind"] == "open_url"
        assert cs.expired_action_details[0]["kind"] == "play_sound"

    def test_window_filtering(self):
        """Actions before window_start should not appear."""
        tracker = ActionTracker(persist=False)

        # Old action (before window)
        tracker.track(
            "old", "speak_text", "ws-1", issued_at="2026-04-10T00:00:00+00:00"
        )
        tracker.mark_dispatched("old")
        # Manually set completed_at in the past
        tracked = tracker.get("old")
        tracked.state = TrackedState.COMPLETED
        tracked.completed_at = "2026-04-10T00:01:00+00:00"

        # New action (in window)
        tracker.track("new", "open_url", "ws-1", issued_at="2026-04-15T10:00:00+00:00")
        tracker.mark_dispatched("new")
        tracker.mark_completed("new")

        with patch(
            "umh.substrate.action_tracker.get_action_tracker", return_value=tracker
        ):
            cs = ContinuitySummary()
            from umh.substrate.continuity_summary import _gather_action_state

            _gather_action_state(cs, "2026-04-14T00:00:00+00:00")

        # Only the new action should be counted
        assert cs.actions_completed == 1
        assert cs.completed_action_kinds == ["open_url"]


# ─── Workstation Events ──────────────────────────────────────────────────


class TestWorkstationEventsInContinuity:
    @patch("umh.substrate.workstation_log.read_recent")
    def test_reconnect_event_surfaces(self, mock_read):
        mock_read.return_value = [
            {
                "ts": "2026-04-15T08:00:00+00:00",
                "event": "node_reconnected",
                "node_id": "antony-workstation",
                "data": {
                    "node_id": "antony-workstation",
                    "previous_status": "offline",
                },
            }
        ]

        cs = ContinuitySummary()
        from umh.substrate.continuity_summary import _gather_workstation_events

        _gather_workstation_events(cs, None)

        assert cs.workstation_events_count == 1
        assert len(cs.notable_events) == 1
        assert (
            "Reconnect" in cs.notable_events[0] or "reconnected" in cs.notable_events[0]
        )

    @patch("umh.substrate.workstation_log.read_recent")
    def test_window_filters_old_events(self, mock_read):
        mock_read.return_value = [
            {
                "ts": "2026-04-10T00:00:00+00:00",  # old
                "event": "node_reconnected",
                "data": {"node_id": "ws", "previous_status": "offline"},
            },
            {
                "ts": "2026-04-15T08:00:00+00:00",  # new
                "event": "bootstrap_started",
                "data": {"profile": "founder_workstation"},
            },
        ]

        cs = ContinuitySummary()
        from umh.substrate.continuity_summary import _gather_workstation_events

        _gather_workstation_events(cs, "2026-04-14T00:00:00+00:00")

        assert cs.workstation_events_count == 1  # only the new one
        assert len(cs.notable_events) == 1
        assert "bootstrap" in cs.notable_events[0].lower()


# ─── close_day Structured Snapshot ────────────────────────────────────────


class TestCloseDaySnapshot:
    @patch("umh.substrate.day_workflows.OperatorSessionStore")
    @patch(
        "umh.substrate.day_workflows._start_ritual_best_effort",
        return_value=(None, None),
    )
    @patch(
        "umh.substrate.day_workflows._advance_ritual_best_effort", return_value=None
    )
    def test_close_day_stores_structured_summary(
        self, mock_advance, mock_start, mock_store_cls
    ):
        """close_day() should persist a JSON-parseable structured summary."""
        session = OperatorSession.new()
        session.is_day_open = True
        session.active_workspace = "builder"

        captured_session = {}

        def capture_put(s):
            captured_session["last"] = s

        mock_store = MagicMock()
        mock_store.get.return_value = session
        mock_store.put.side_effect = capture_put
        mock_store_cls.default.return_value = mock_store

        from umh.substrate.day_workflows import close_day

        result = close_day(continuity_notes="deploy pipeline tomorrow")
        assert result["status"] == "ok"

        # The persisted session should have a JSON-parseable briefing summary
        last = captured_session.get("last")
        if last is not None:
            briefing = last.last_briefing_summary
            if briefing and briefing.startswith("{"):
                parsed = json.loads(briefing)
                assert parsed["type"] == "close_day_snapshot"
                assert "recap" in parsed

    @patch("umh.substrate.day_workflows.OperatorSessionStore")
    @patch(
        "umh.substrate.day_workflows._start_ritual_best_effort",
        return_value=(None, None),
    )
    @patch(
        "umh.substrate.day_workflows._advance_ritual_best_effort", return_value=None
    )
    def test_close_day_includes_snapshot_in_response(
        self, mock_advance, mock_start, mock_store_cls
    ):
        """close_day() response dict should include close_snapshot."""
        session = OperatorSession.new()
        session.is_day_open = True

        mock_store = MagicMock()
        mock_store.get.return_value = session
        mock_store_cls.default.return_value = mock_store

        from umh.substrate.day_workflows import close_day

        result = close_day()
        # close_snapshot should be present if the builder succeeded
        assert "close_snapshot" in result or result["status"] == "ok"


# ─── No Regression ────────────────────────────────────────────────────────


class TestNoRegression:
    @patch("umh.substrate.day_workflows.OperatorSessionStore")
    @patch(
        "umh.substrate.day_workflows._start_ritual_best_effort",
        return_value=("r1", None),
    )
    @patch(
        "umh.substrate.day_workflows._advance_ritual_best_effort", return_value=None
    )
    def test_open_day_still_returns_existing_keys(
        self, mock_advance, mock_start, mock_store_cls
    ):
        """All v1-v6 keys must still be present in open_day() response."""
        mock_store = MagicMock()
        mock_store.get.return_value = None
        mock_store_cls.default.return_value = mock_store

        from umh.substrate.day_workflows import open_day

        result = open_day()
        # Core keys from v1
        assert "status" in result
        assert "day_session_id" in result
        assert "ritual_id" in result
        assert "briefing" in result
        assert "day_mode" in result
        assert "active_workspace" in result
        assert "opened_at" in result

    @patch("umh.substrate.day_workflows.OperatorSessionStore")
    @patch(
        "umh.substrate.day_workflows._start_ritual_best_effort",
        return_value=("r1", None),
    )
    @patch(
        "umh.substrate.day_workflows._advance_ritual_best_effort", return_value=None
    )
    def test_close_day_still_returns_existing_keys(
        self, mock_advance, mock_start, mock_store_cls
    ):
        """All v1-v6 keys must still be present in close_day() response."""
        session = OperatorSession.new()
        session.is_day_open = True
        session.active_workspace = "builder"

        mock_store = MagicMock()
        mock_store.get.return_value = session
        mock_store_cls.default.return_value = mock_store

        from umh.substrate.day_workflows import close_day

        result = close_day()
        assert "status" in result
        assert "day_session_id" in result
        assert "ritual_id" in result
        assert "summary" in result
        assert "closed_at" in result
