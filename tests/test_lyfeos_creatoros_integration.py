"""Tests for EOS, LyfeOS, and CreatorOS integration adapters — protocol conformance and signal building."""

import os
import sys
from datetime import datetime, timezone
from uuid import uuid4

import pytest

_worktree = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _worktree not in sys.path:
    sys.path.insert(0, _worktree)

from substrate.sockets.protocols import (
    CapabilityHandler,
    SignalEmitter,
)

# EOS imports
from projections.eos.integration.correlation import (
    EOSCorrelationMap,
    EOSWritebackTarget,
)
from projections.eos.integration.handlers import EOSCapabilityHandler
from projections.eos.integration.manifest import (
    INTEGRATION_ID as EOS_ID,
    load_eos_config,
)
from projections.eos.integration.signals import EOSSignalEmitter
from projections.eos.integration.tables import (
    CrmActivityRow,
    CrmContactRow,
    CrmDealRow,
)

# LyfeOS imports
from projections.lyfeos.integration.correlation import (
    LyfeOSCorrelationMap,
    LyfeOSWritebackTarget,
)
from projections.lyfeos.integration.handlers import LyfeOSCapabilityHandler
from projections.lyfeos.integration.manifest import (
    INTEGRATION_ID as LYFEOS_ID,
    load_lyfeos_config,
)
from projections.lyfeos.integration.signals import LyfeOSSignalEmitter
from projections.lyfeos.integration.tables import (
    DailyLogRow,
    QuestRow,
    UserStatsRow,
)

# CreatorOS imports
from projections.creatoros.integration.correlation import (
    CreatorOSCorrelationMap,
    CreatorOSWritebackTarget,
)
from projections.creatoros.integration.handlers import CreatorOSCapabilityHandler
from projections.creatoros.integration.manifest import (
    INTEGRATION_ID as CREATOROS_ID,
    load_creatoros_config,
)
from projections.creatoros.integration.signals import CreatorOSSignalEmitter
from projections.creatoros.integration.tables import (
    PostRow,
    ProductRow,
    RevenueRow,
)


NOW = datetime.now(timezone.utc)


# ---- EOS Protocol Conformance ----


class TestEOSProtocols:
    def test_emitter_satisfies_signal_emitter(self):
        emitter = EOSSignalEmitter()
        assert isinstance(emitter, SignalEmitter)
        assert emitter.integration_id == EOS_ID

    def test_handler_satisfies_capability_handler(self):
        handler = EOSCapabilityHandler()
        assert isinstance(handler, CapabilityHandler)
        assert handler.integration_id == EOS_ID

    def test_handler_noop(self):
        from substrate.sockets.envelopes import CapabilityRequest

        handler = EOSCapabilityHandler()
        req = CapabilityRequest(
            request_id=uuid4(),
            capability_name="noop",
            integration_id="eos",
            params={"table_name": "crm_contacts", "user_id": "u1", "row_id": "r1"},
            governance_verdict_id=uuid4(),
            trace_id=uuid4(),
        )
        resp = handler.handle_capability(req)
        assert resp.success
        assert resp.result_data["received"] is True

    def test_handler_unsupported_capability(self):
        from substrate.sockets.envelopes import CapabilityRequest

        handler = EOSCapabilityHandler()
        req = CapabilityRequest(
            request_id=uuid4(),
            capability_name="nonexistent",
            integration_id="eos",
            params={},
            governance_verdict_id=uuid4(),
            trace_id=uuid4(),
        )
        resp = handler.handle_capability(req)
        assert not resp.success
        assert "unsupported" in resp.error


class TestEOSSignals:
    def test_contact_signal_builds(self):
        emitter = EOSSignalEmitter()
        row = CrmContactRow(
            id="ct-001",
            user_id="u1",
            name="Jane Doe",
            email="jane@example.com",
            status="lead",
            company="Acme Corp",
            title="CTO",
            created_at=NOW,
        )
        envelope, target = emitter.build_contact_signal(row)
        assert envelope.integration_id == "eos"
        assert envelope.content_type == "eos_contact_created"
        assert target.table_name == "crm_contacts"
        assert target.user_id == "u1"
        assert "Jane Doe" in envelope.raw_content
        assert "Acme Corp" in envelope.raw_content

    def test_deal_signal_builds(self):
        emitter = EOSSignalEmitter()
        row = CrmDealRow(
            id="dl-001",
            user_id="u1",
            title="Enterprise Contract",
            company="BigCo",
            value="50000",
            stage="proposal",
            probability=70,
            contact_id="ct-001",
            created_at=NOW,
        )
        envelope, target = emitter.build_deal_signal(row)
        assert envelope.content_type == "eos_deal_created"
        assert "50000" in envelope.raw_content
        assert target.table_name == "crm_deals"

    def test_activity_signal_builds(self):
        emitter = EOSSignalEmitter()
        row = CrmActivityRow(
            id="act-001",
            user_id="u1",
            type="call",
            subject="Follow-up call",
            date=NOW,
            related_to_type="contact",
            related_to_id="ct-001-abcdef",
            completed=False,
            created_at=NOW,
        )
        envelope, target = emitter.build_activity_signal(row)
        assert envelope.content_type == "eos_activity_logged"
        assert "call" in envelope.raw_content
        assert target.table_name == "crm_activities"


class TestEOSCorrelation:
    def test_register_lookup_remove(self):
        cmap = EOSCorrelationMap()
        cid = uuid4()
        target = EOSWritebackTarget(user_id="u1", table_name="crm_contacts", row_id="ct-001")

        cmap.register(cid, target)
        assert len(cmap) == 1
        assert cmap.lookup(cid) == target

        cmap.remove(cid)
        assert len(cmap) == 0
        assert cmap.lookup(cid) is None

    def test_lookup_missing_returns_none(self):
        cmap = EOSCorrelationMap()
        assert cmap.lookup(uuid4()) is None


class TestEOSConfig:
    def test_empty_when_no_env(self, monkeypatch):
        monkeypatch.delenv("EOS_DATABASE_URL", raising=False)
        assert load_eos_config() == {}

    def test_parses_env(self, monkeypatch):
        monkeypatch.setenv("EOS_DATABASE_URL", "postgres://test")
        monkeypatch.setenv("EOS_USER_IDS", "u1,u2")
        monkeypatch.setenv("EOS_POLL_INTERVAL", "20.0")
        config = load_eos_config()
        assert config["database_url"] == "postgres://test"
        assert config["user_ids"] == ["u1", "u2"]
        assert config["poll_interval"] == 20.0


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
        from substrate.sockets.envelopes import CapabilityRequest

        handler = LyfeOSCapabilityHandler()
        req = CapabilityRequest(
            request_id=uuid4(),
            capability_name="noop",
            integration_id="lyfeos",
            params={"table_name": "quests", "user_id": 1, "row_id": "1"},
            governance_verdict_id=uuid4(),
            trace_id=uuid4(),
        )
        resp = handler.handle_capability(req)
        assert resp.success
        assert resp.result_data["received"] is True

    def test_handler_unsupported_capability(self):
        from substrate.sockets.envelopes import CapabilityRequest

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
    def test_quest_signal_builds(self):
        emitter = LyfeOSSignalEmitter()
        row = QuestRow(
            id=1,
            user_id=1,
            title="Morning Ritual",
            description="5K run + cold shower",
            category="rituals",
            completed=True,
            energy_cost=3,
            experience_reward=50,
            difficulty="B",
            is_ritualized=True,
            ritual_group="morning",
            mission_status="confirmed",
            created_at=NOW,
            updated_at=NOW,
        )
        envelope, target = emitter.build_quest_signal(row)
        assert envelope.integration_id == "lyfeos"
        assert envelope.content_type == "lyfeos_quest_completed"
        assert target.table_name == "quests"
        assert target.user_id == 1
        assert "Morning Ritual" in envelope.raw_content

    def test_daily_log_signal_builds(self):
        emitter = LyfeOSSignalEmitter()
        row = DailyLogRow(
            id=10,
            user_id=1,
            date="2026-05-20",
            mental_state=8,
            physical_state=7,
            emotional_state=9,
            gratitude="Good progress on the build",
            went_well="Shipped three features",
            created_at=NOW,
        )
        envelope, target = emitter.build_daily_log_signal(row)
        assert envelope.content_type == "lyfeos_daily_log_created"
        assert "mental=8" in envelope.raw_content
        assert target.table_name == "user_daily_logs"

    def test_stats_signal_builds(self):
        emitter = LyfeOSSignalEmitter()
        row = UserStatsRow(
            id=1,
            user_id=1,
            energy_points_current=80,
            energy_points_max=100,
            health_points_current=90,
            health_points_max=100,
            experience_current=1200,
            experience_max=2000,
            level=5,
            streak_days=14,
            updated_at=NOW,
        )
        envelope, target = emitter.build_stats_signal(row)
        assert envelope.content_type == "lyfeos_stats_updated"
        assert "level=5" in envelope.raw_content
        assert "streak=14d" in envelope.raw_content
        assert target.table_name == "user_stats"


class TestLyfeOSCorrelation:
    def test_register_lookup_remove(self):
        cmap = LyfeOSCorrelationMap()
        cid = uuid4()
        target = LyfeOSWritebackTarget(user_id=1, table_name="quests", row_id="1")

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
        monkeypatch.setenv("LYFEOS_USER_IDS", "1,2")
        monkeypatch.setenv("LYFEOS_POLL_INTERVAL", "45.0")
        config = load_lyfeos_config()
        assert config["database_url"] == "postgres://test"
        assert config["user_ids"] == ["1", "2"]
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
        from substrate.sockets.envelopes import CapabilityRequest

        handler = CreatorOSCapabilityHandler()
        req = CapabilityRequest(
            request_id=uuid4(),
            capability_name="noop",
            integration_id="creatoros",
            params={"table_name": "posts", "user_id": 1, "row_id": "1"},
            governance_verdict_id=uuid4(),
            trace_id=uuid4(),
        )
        resp = handler.handle_capability(req)
        assert resp.success
        assert resp.result_data["received"] is True

    def test_handler_unsupported_capability(self):
        from substrate.sockets.envelopes import CapabilityRequest

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
    def test_post_signal_builds(self):
        emitter = CreatorOSSignalEmitter()
        row = PostRow(
            id=1,
            user_id=1,
            content="How to Build a Business from Scratch",
            media_type="text",
            likes=120,
            comments=45,
            created_at=NOW,
        )
        envelope, target = emitter.build_post_signal(row)
        assert envelope.integration_id == "creatoros"
        assert envelope.content_type == "creatoros_post_created"
        assert target.table_name == "posts"
        assert target.user_id == 1
        assert "likes:120" in envelope.raw_content

    def test_product_signal_builds(self):
        emitter = CreatorOSSignalEmitter()
        row = ProductRow(
            id=1,
            user_id=1,
            title="Digital Marketing Course",
            description="Complete guide to digital marketing",
            price=49.99,
            category="education",
            rating=4.8,
            review_count=200,
            created_at=NOW,
        )
        envelope, target = emitter.build_product_signal(row)
        assert envelope.content_type == "creatoros_product_listed"
        assert "49.99" in envelope.raw_content
        assert target.table_name == "products"

    def test_revenue_signal_builds(self):
        emitter = CreatorOSSignalEmitter()
        row = RevenueRow(
            id=1,
            user_id=1,
            amount=250.00,
            date=NOW,
            source="course_sales",
        )
        envelope, target = emitter.build_revenue_signal(row)
        assert envelope.content_type == "creatoros_revenue_recorded"
        assert "250.00" in envelope.raw_content
        assert target.table_name == "revenue"


class TestCreatorOSCorrelation:
    def test_register_lookup_remove(self):
        cmap = CreatorOSCorrelationMap()
        cid = uuid4()
        target = CreatorOSWritebackTarget(user_id=1, table_name="posts", row_id="1")

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
        monkeypatch.setenv("CREATOROS_USER_IDS", "1,2,3")
        monkeypatch.setenv("CREATOROS_POLL_INTERVAL", "120.0")
        config = load_creatoros_config()
        assert config["database_url"] == "postgres://test"
        assert config["user_ids"] == ["1", "2", "3"]
        assert config["poll_interval"] == 120.0
