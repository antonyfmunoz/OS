"""Tests for LyfeOS and CreatorOS integration adapters — protocol conformance and signal building."""

import os
import sys
from datetime import datetime, timezone
from uuid import uuid4

import pytest

_worktree = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _worktree not in sys.path:
    sys.path.insert(0, _worktree)

from services.umh.sockets.protocols import (
    CapabilityHandler,
    OutcomeReceiver,
    SignalEmitter,
)

# LyfeOS imports
from services.umh.integrations.lyfeos.correlation import (
    LyfeOSCorrelationMap,
    LyfeOSWritebackTarget,
)
from services.umh.integrations.lyfeos.handlers import LyfeOSCapabilityHandler
from services.umh.integrations.lyfeos.manifest import (
    INTEGRATION_ID as LYFEOS_ID,
    load_lyfeos_config,
)
from services.umh.integrations.lyfeos.signals import LyfeOSSignalEmitter
from services.umh.integrations.lyfeos.tables import (
    GoalRow,
    HabitLogRow,
    HealthMetricRow,
)

# CreatorOS imports
from services.umh.integrations.creatoros.correlation import (
    CreatorOSCorrelationMap,
    CreatorOSWritebackTarget,
)
from services.umh.integrations.creatoros.handlers import CreatorOSCapabilityHandler
from services.umh.integrations.creatoros.manifest import (
    INTEGRATION_ID as CREATOROS_ID,
    load_creatoros_config,
)
from services.umh.integrations.creatoros.signals import CreatorOSSignalEmitter
from services.umh.integrations.creatoros.tables import (
    AnalyticsRow,
    AudienceMetricRow,
    ContentRow,
)


NOW = datetime.now(timezone.utc)


# ---- LyfeOS Protocol Conformance ----


class TestLyfeOSProtocols:
    def test_emitter_satisfies_signal_emitter(self):
        emitter = LyfeOSSignalEmitter()
        assert isinstance(emitter, SignalEmitter)
        assert emitter.integration_id == LYFEOS_ID

    def test_handler_satisfies_capability_handler(self):
        handler = LyfeOSCapabilityHandler()
        assert isinstance(handler, CapabilityHandler)
        assert handler.integration_id == LYFEOS_ID

    def test_handler_noop(self):
        from services.umh.sockets.envelopes import CapabilityRequest

        handler = LyfeOSCapabilityHandler()
        req = CapabilityRequest(
            request_id=uuid4(),
            capability_name="noop",
            integration_id="lyfeos",
            params={"table_name": "habit_logs", "user_id": "u1", "row_id": "r1"},
            governance_verdict_id=uuid4(),
            trace_id=uuid4(),
        )
        resp = handler.handle_capability(req)
        assert resp.success
        assert resp.result_data["received"] is True

    def test_handler_unsupported_capability(self):
        from services.umh.sockets.envelopes import CapabilityRequest

        handler = LyfeOSCapabilityHandler()
        req = CapabilityRequest(
            request_id=uuid4(),
            capability_name="nonexistent",
            integration_id="lyfeos",
            params={},
            governance_verdict_id=uuid4(),
            trace_id=uuid4(),
        )
        resp = handler.handle_capability(req)
        assert not resp.success
        assert "unsupported" in resp.error


class TestLyfeOSSignals:
    def test_habit_signal_builds(self):
        emitter = LyfeOSSignalEmitter()
        row = HabitLogRow(
            id="h1",
            user_id="u1",
            habit_name="morning_run",
            completed=True,
            notes="5K in 25 min",
            logged_at=NOW,
        )
        envelope, target = emitter.build_habit_signal(row)
        assert envelope.integration_id == "lyfeos"
        assert envelope.content_type == "lyfeos_habits_logged"
        assert target.table_name == "habit_logs"
        assert target.user_id == "u1"

    def test_goal_signal_builds(self):
        emitter = LyfeOSSignalEmitter()
        row = GoalRow(
            id="g1",
            user_id="u1",
            title="Read 50 books",
            progress_pct=40,
            status="active",
            updated_at=NOW,
        )
        envelope, target = emitter.build_goal_signal(row)
        assert envelope.content_type == "lyfeos_goals_updated"
        assert "40%" in envelope.raw_content

    def test_health_signal_builds(self):
        emitter = LyfeOSSignalEmitter()
        row = HealthMetricRow(
            id="m1",
            user_id="u1",
            metric_type="weight",
            value=175.5,
            unit="lbs",
            logged_at=NOW,
        )
        envelope, target = emitter.build_health_signal(row)
        assert envelope.content_type == "lyfeos_health_logged"
        assert "175.5" in envelope.raw_content


class TestLyfeOSCorrelation:
    def test_register_lookup_remove(self):
        cmap = LyfeOSCorrelationMap()
        cid = uuid4()
        target = LyfeOSWritebackTarget(user_id="u1", table_name="goals", row_id="g1")

        cmap.register(cid, target)
        assert len(cmap) == 1
        assert cmap.lookup(cid) == target

        cmap.remove(cid)
        assert len(cmap) == 0
        assert cmap.lookup(cid) is None

    def test_lookup_missing_returns_none(self):
        cmap = LyfeOSCorrelationMap()
        assert cmap.lookup(uuid4()) is None


class TestLyfeOSConfig:
    def test_empty_when_no_env(self, monkeypatch):
        monkeypatch.delenv("LYFEOS_DATABASE_URL", raising=False)
        assert load_lyfeos_config() == {}

    def test_parses_env(self, monkeypatch):
        monkeypatch.setenv("LYFEOS_DATABASE_URL", "postgres://test")
        monkeypatch.setenv("LYFEOS_USER_IDS", "u1,u2")
        monkeypatch.setenv("LYFEOS_POLL_INTERVAL", "45.0")
        config = load_lyfeos_config()
        assert config["database_url"] == "postgres://test"
        assert config["user_ids"] == ["u1", "u2"]
        assert config["poll_interval"] == 45.0


# ---- CreatorOS Protocol Conformance ----


class TestCreatorOSProtocols:
    def test_emitter_satisfies_signal_emitter(self):
        emitter = CreatorOSSignalEmitter()
        assert isinstance(emitter, SignalEmitter)
        assert emitter.integration_id == CREATOROS_ID

    def test_handler_satisfies_capability_handler(self):
        handler = CreatorOSCapabilityHandler()
        assert isinstance(handler, CapabilityHandler)
        assert handler.integration_id == CREATOROS_ID

    def test_handler_noop(self):
        from services.umh.sockets.envelopes import CapabilityRequest

        handler = CreatorOSCapabilityHandler()
        req = CapabilityRequest(
            request_id=uuid4(),
            capability_name="noop",
            integration_id="creatoros",
            params={"table_name": "content", "creator_id": "c1", "row_id": "r1"},
            governance_verdict_id=uuid4(),
            trace_id=uuid4(),
        )
        resp = handler.handle_capability(req)
        assert resp.success
        assert resp.result_data["received"] is True

    def test_handler_unsupported_capability(self):
        from services.umh.sockets.envelopes import CapabilityRequest

        handler = CreatorOSCapabilityHandler()
        req = CapabilityRequest(
            request_id=uuid4(),
            capability_name="nonexistent",
            integration_id="creatoros",
            params={},
            governance_verdict_id=uuid4(),
            trace_id=uuid4(),
        )
        resp = handler.handle_capability(req)
        assert not resp.success
        assert "unsupported" in resp.error


class TestCreatorOSSignals:
    def test_content_signal_builds(self):
        emitter = CreatorOSSignalEmitter()
        row = ContentRow(
            id="c1",
            creator_id="cr1",
            platform="youtube",
            content_type="long_form",
            title="How to Build a Business",
            status="published",
            published_at=NOW,
            created_at=NOW,
        )
        envelope, target = emitter.build_content_signal(row)
        assert envelope.integration_id == "creatoros"
        assert envelope.content_type == "creatoros_content_published"
        assert target.table_name == "content"
        assert target.creator_id == "cr1"

    def test_analytics_signal_builds(self):
        emitter = CreatorOSSignalEmitter()
        row = AnalyticsRow(
            id="a1",
            creator_id="cr1",
            content_id="c1",
            views=15000,
            likes=800,
            comments=120,
            shares=45,
            updated_at=NOW,
        )
        envelope, target = emitter.build_analytics_signal(row)
        assert envelope.content_type == "creatoros_analytics_updated"
        assert "15000" in envelope.raw_content

    def test_audience_signal_builds(self):
        emitter = CreatorOSSignalEmitter()
        row = AudienceMetricRow(
            id="am1",
            creator_id="cr1",
            platform="instagram",
            metric_type="followers",
            value=10000,
            recorded_at=NOW,
        )
        envelope, target = emitter.build_audience_signal(row)
        assert envelope.content_type == "creatoros_audience_milestone"
        assert "10000" in envelope.raw_content


class TestCreatorOSCorrelation:
    def test_register_lookup_remove(self):
        cmap = CreatorOSCorrelationMap()
        cid = uuid4()
        target = CreatorOSWritebackTarget(creator_id="cr1", table_name="content", row_id="c1")

        cmap.register(cid, target)
        assert len(cmap) == 1
        assert cmap.lookup(cid) == target

        cmap.remove(cid)
        assert len(cmap) == 0
        assert cmap.lookup(cid) is None

    def test_lookup_missing_returns_none(self):
        cmap = CreatorOSCorrelationMap()
        assert cmap.lookup(uuid4()) is None


class TestCreatorOSConfig:
    def test_empty_when_no_env(self, monkeypatch):
        monkeypatch.delenv("CREATOROS_DATABASE_URL", raising=False)
        assert load_creatoros_config() == {}

    def test_parses_env(self, monkeypatch):
        monkeypatch.setenv("CREATOROS_DATABASE_URL", "postgres://test")
        monkeypatch.setenv("CREATOROS_CREATOR_IDS", "c1,c2,c3")
        monkeypatch.setenv("CREATOROS_POLL_INTERVAL", "120.0")
        config = load_creatoros_config()
        assert config["database_url"] == "postgres://test"
        assert config["creator_ids"] == ["c1", "c2", "c3"]
        assert config["poll_interval"] == 120.0
