"""Tests for Phase 12: Session Runtime.

Covers all types, registries, engines, and the top-level runtime.
"""

from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
import time

sys.path.insert(0, "/opt/OS")

import pytest

# Patch data dir before import
_test_dir = ""


def _patch_data_dir():
    global _test_dir
    _test_dir = tempfile.mkdtemp(prefix="test_session_")
    os.environ["UMH_ROOT"] = _test_dir
    os.makedirs(os.path.join(_test_dir, "data", "umh", "session", "timeline"), exist_ok=True)
    os.makedirs(os.path.join(_test_dir, "data", "umh", "session", "handoffs"), exist_ok=True)
    os.makedirs(os.path.join(_test_dir, "data", "umh", "session", "snapshots"), exist_ok=True)


def _cleanup_data_dir():
    global _test_dir
    if _test_dir and os.path.exists(_test_dir):
        shutil.rmtree(_test_dir)
    if "UMH_ROOT" in os.environ:
        del os.environ["UMH_ROOT"]


@pytest.fixture(autouse=True)
def isolate_test():
    _patch_data_dir()
    from substrate.organism import session_runtime
    session_runtime.reset_session_runtime()
    yield
    _cleanup_data_dir()
    session_runtime.reset_session_runtime()


# ── Enum Tests ───────────────────────────────────────────────────


class TestSessionType:
    def test_values(self):
        from substrate.organism.session_runtime import SessionType
        expected = {
            "desktop", "laptop", "phone", "tablet", "vps", "server",
            "container", "browser", "remote-desktop", "agent-session",
        }
        assert {e.value for e in SessionType} == expected

    def test_value(self):
        from substrate.organism.session_runtime import SessionType
        assert SessionType.DESKTOP.value == "desktop"


class TestSessionStatus:
    def test_values(self):
        from substrate.organism.session_runtime import SessionStatus
        expected = {"active", "background", "idle", "suspended", "disconnected"}
        assert {e.value for e in SessionStatus} == expected

    def test_is_alive(self):
        from substrate.organism.session_runtime import SessionStatus
        assert SessionStatus.ACTIVE.is_alive is True
        assert SessionStatus.BACKGROUND.is_alive is True
        assert SessionStatus.IDLE.is_alive is True
        assert SessionStatus.SUSPENDED.is_alive is False
        assert SessionStatus.DISCONNECTED.is_alive is False


class TestSessionAuthority:
    def test_values(self):
        from substrate.organism.session_runtime import SessionAuthority
        expected = {"primary", "secondary", "background"}
        assert {e.value for e in SessionAuthority} == expected


class TestSessionEventType:
    def test_values(self):
        from substrate.organism.session_runtime import SessionEventType
        expected = {
            "session_started", "session_resumed", "session_suspended",
            "session_disconnected", "session_restored", "session_promoted",
            "session_demoted", "handoff_initiated", "handoff_completed",
            "authority_changed", "work_bound", "work_unbound",
        }
        assert {e.value for e in SessionEventType} == expected


class TestHandoffStatusEnum:
    def test_values(self):
        from substrate.organism.session_runtime import HandoffStatus
        expected = {"pending", "completed", "expired"}
        assert {e.value for e in HandoffStatus} == expected


# ── Data Model Tests ─────────────────────────────────────────────


class TestSession:
    def test_auto_id(self):
        from substrate.organism.session_runtime import Session
        s = Session()
        assert s.session_id.startswith("sess-")
        assert len(s.session_id) == 17

    def test_roundtrip(self):
        from substrate.organism.session_runtime import Session
        s = Session(session_type="vps", host_id="h1", device_id="d1", profile_id="engineer")
        d = s.to_dict()
        s2 = Session.from_dict(d)
        assert s2.session_id == s.session_id
        assert s2.session_type == "vps"
        assert s2.host_id == "h1"
        assert s2.device_id == "d1"
        assert s2.profile_id == "engineer"

    def test_defaults(self):
        from substrate.organism.session_runtime import Session
        s = Session()
        assert s.status == "active"
        assert s.attention_state == "available"
        assert s.authority == "secondary"
        assert s.bound_work_packets == []
        assert s.created_at > 0
        assert s.last_seen_at > 0


class TestSessionEvent:
    def test_auto_id(self):
        from substrate.organism.session_runtime import SessionEvent
        e = SessionEvent(event_type="test", session_id="s1", summary="test event")
        assert e.event_id.startswith("sevt-")

    def test_roundtrip(self):
        from substrate.organism.session_runtime import SessionEvent
        e = SessionEvent(event_type="test", session_id="s1", summary="hello")
        d = e.to_dict()
        e2 = SessionEvent.from_dict(d)
        assert e2.event_type == "test"
        assert e2.session_id == "s1"
        assert e2.summary == "hello"


class TestSessionHandoff:
    def test_auto_id(self):
        from substrate.organism.session_runtime import SessionHandoff
        h = SessionHandoff(source_session_id="s1", target_session_id="s2")
        assert h.handoff_id.startswith("hoff-")

    def test_roundtrip(self):
        from substrate.organism.session_runtime import SessionHandoff
        h = SessionHandoff(
            source_session_id="s1",
            target_session_id="s2",
            source_device_id="d1",
            target_device_id="d2",
        )
        d = h.to_dict()
        h2 = SessionHandoff.from_dict(d)
        assert h2.source_session_id == "s1"
        assert h2.target_session_id == "s2"
        assert h2.status == "pending"

    def test_defaults(self):
        from substrate.organism.session_runtime import SessionHandoff
        h = SessionHandoff()
        assert h.active_objectives == []
        assert h.active_work_packets == []
        assert h.recent_commands == []
        assert h.continuity_snapshot == {}
        assert h.projection_snapshot == {}


class TestSessionContinuityLink:
    def test_auto_id(self):
        from substrate.organism.session_runtime import SessionContinuityLink
        l = SessionContinuityLink(session_id="s1", profile_id="engineer")
        assert l.link_id.startswith("slink-")

    def test_roundtrip(self):
        from substrate.organism.session_runtime import SessionContinuityLink
        l = SessionContinuityLink(
            profile_id="p1", session_id="s1",
            objective_id="o1", work_packet_id="wp1", outcome_id="out1",
        )
        d = l.to_dict()
        l2 = SessionContinuityLink.from_dict(d)
        assert l2.profile_id == "p1"
        assert l2.work_packet_id == "wp1"
        assert l2.outcome_id == "out1"


class TestSessionRuntimeSnapshot:
    def test_auto_id(self):
        from substrate.organism.session_runtime import SessionRuntimeSnapshot
        s = SessionRuntimeSnapshot()
        assert s.snapshot_id.startswith("sssnap-")

    def test_roundtrip(self):
        from substrate.organism.session_runtime import SessionRuntimeSnapshot
        s = SessionRuntimeSnapshot(total_active=3, total_all=5)
        d = s.to_dict()
        s2 = SessionRuntimeSnapshot.from_dict(d)
        assert s2.total_active == 3
        assert s2.total_all == 5


# ── Registry Tests ───────────────────────────────────────────────


class TestSessionRegistry:
    def test_register_and_get(self):
        from substrate.organism.session_runtime import Session, SessionRegistry
        reg = SessionRegistry()
        s = Session(session_type="desktop", device_id="d1")
        reg.register(s)
        assert reg.get(s.session_id) is not None
        assert reg.get(s.session_id).device_id == "d1"

    def test_remove(self):
        from substrate.organism.session_runtime import Session, SessionRegistry
        reg = SessionRegistry()
        s = Session(device_id="d1")
        reg.register(s)
        removed = reg.remove(s.session_id)
        assert removed is not None
        assert reg.get(s.session_id) is None

    def test_active_sessions(self):
        from substrate.organism.session_runtime import Session, SessionRegistry
        reg = SessionRegistry()
        s1 = Session(status="active")
        s2 = Session(status="disconnected")
        s3 = Session(status="background")
        reg.register(s1)
        reg.register(s2)
        reg.register(s3)
        active = reg.active_sessions()
        ids = {s.session_id for s in active}
        assert s1.session_id in ids
        assert s2.session_id not in ids
        assert s3.session_id in ids

    def test_promote_to_primary(self):
        from substrate.organism.session_runtime import Session, SessionRegistry
        reg = SessionRegistry()
        s1 = Session(authority="primary")
        s2 = Session(authority="secondary")
        reg.register(s1)
        reg.register(s2)
        success, demoted = reg.promote_to_primary(s2.session_id)
        assert success is True
        assert demoted == s1.session_id
        assert reg.get(s2.session_id).authority == "primary"
        assert reg.get(s1.session_id).authority == "secondary"

    def test_promote_same_session(self):
        from substrate.organism.session_runtime import Session, SessionRegistry
        reg = SessionRegistry()
        s = Session(authority="primary")
        reg.register(s)
        success, demoted = reg.promote_to_primary(s.session_id)
        assert success is True
        assert demoted is None

    def test_get_primary(self):
        from substrate.organism.session_runtime import Session, SessionRegistry
        reg = SessionRegistry()
        s = Session(authority="primary")
        reg.register(s)
        assert reg.get_primary().session_id == s.session_id

    def test_get_secondary(self):
        from substrate.organism.session_runtime import Session, SessionRegistry
        reg = SessionRegistry()
        s1 = Session(authority="secondary")
        s2 = Session(authority="primary")
        reg.register(s1)
        reg.register(s2)
        secondary = reg.get_secondary()
        assert len(secondary) == 1
        assert secondary[0].session_id == s1.session_id

    def test_get_background(self):
        from substrate.organism.session_runtime import Session, SessionRegistry
        reg = SessionRegistry()
        s = Session(authority="background", status="active")
        reg.register(s)
        bg = reg.get_background()
        assert len(bg) == 1

    def test_heartbeat(self):
        from substrate.organism.session_runtime import Session, SessionRegistry
        reg = SessionRegistry()
        s = Session()
        reg.register(s)
        old_ts = s.last_seen_at
        time.sleep(0.01)
        assert reg.heartbeat(s.session_id) is True
        assert reg.get(s.session_id).last_seen_at > old_ts

    def test_heartbeat_unknown(self):
        from substrate.organism.session_runtime import SessionRegistry
        reg = SessionRegistry()
        assert reg.heartbeat("nonexistent") is False

    def test_bind_work_packet(self):
        from substrate.organism.session_runtime import Session, SessionRegistry
        reg = SessionRegistry()
        s = Session()
        reg.register(s)
        assert reg.bind_work_packet(s.session_id, "wp-1") is True
        assert "wp-1" in reg.get(s.session_id).bound_work_packets

    def test_bind_work_packet_idempotent(self):
        from substrate.organism.session_runtime import Session, SessionRegistry
        reg = SessionRegistry()
        s = Session()
        reg.register(s)
        reg.bind_work_packet(s.session_id, "wp-1")
        reg.bind_work_packet(s.session_id, "wp-1")
        assert reg.get(s.session_id).bound_work_packets.count("wp-1") == 1

    def test_unbind_work_packet(self):
        from substrate.organism.session_runtime import Session, SessionRegistry
        reg = SessionRegistry()
        s = Session()
        reg.register(s)
        reg.bind_work_packet(s.session_id, "wp-1")
        assert reg.unbind_work_packet(s.session_id, "wp-1") is True
        assert "wp-1" not in reg.get(s.session_id).bound_work_packets

    def test_persistence(self):
        from substrate.organism.session_runtime import Session, SessionRegistry
        reg = SessionRegistry()
        s = Session(session_type="vps", device_id="srv1500858")
        reg.register(s)
        reg2 = SessionRegistry()
        loaded = reg2.get(s.session_id)
        assert loaded is not None
        assert loaded.session_type == "vps"
        assert loaded.device_id == "srv1500858"

    def test_update_status(self):
        from substrate.organism.session_runtime import Session, SessionRegistry
        reg = SessionRegistry()
        s = Session()
        reg.register(s)
        assert reg.update_status(s.session_id, "suspended") is True
        assert reg.get(s.session_id).status == "suspended"

    def test_update_status_unknown(self):
        from substrate.organism.session_runtime import SessionRegistry
        reg = SessionRegistry()
        assert reg.update_status("nope", "active") is False


# ── Lifecycle Engine Tests ───────────────────────────────────────


class TestSessionLifecycleEngine:
    def test_start_session(self):
        from substrate.organism.session_runtime import SessionLifecycleEngine, SessionRegistry
        reg = SessionRegistry()
        engine = SessionLifecycleEngine(reg)
        s = engine.start_session(session_type="desktop", device_id="d1")
        assert s.session_type == "desktop"
        assert s.status == "active"
        assert reg.get(s.session_id) is not None

    def test_suspend_and_resume(self):
        from substrate.organism.session_runtime import SessionLifecycleEngine, SessionRegistry
        reg = SessionRegistry()
        engine = SessionLifecycleEngine(reg)
        s = engine.start_session()
        assert engine.suspend_session(s.session_id) is True
        assert reg.get(s.session_id).status == "suspended"
        assert engine.resume_session(s.session_id) is True
        assert reg.get(s.session_id).status == "active"

    def test_resume_requires_suspended_or_idle(self):
        from substrate.organism.session_runtime import SessionLifecycleEngine, SessionRegistry
        reg = SessionRegistry()
        engine = SessionLifecycleEngine(reg)
        s = engine.start_session()
        assert engine.resume_session(s.session_id) is False

    def test_disconnect_and_restore(self):
        from substrate.organism.session_runtime import SessionLifecycleEngine, SessionRegistry
        reg = SessionRegistry()
        engine = SessionLifecycleEngine(reg)
        s = engine.start_session()
        assert engine.disconnect_session(s.session_id) is True
        assert reg.get(s.session_id).status == "disconnected"
        assert engine.restore_session(s.session_id) is True
        assert reg.get(s.session_id).status == "active"

    def test_restore_requires_disconnected(self):
        from substrate.organism.session_runtime import SessionLifecycleEngine, SessionRegistry
        reg = SessionRegistry()
        engine = SessionLifecycleEngine(reg)
        s = engine.start_session()
        assert engine.restore_session(s.session_id) is False

    def test_background_session(self):
        from substrate.organism.session_runtime import SessionLifecycleEngine, SessionRegistry
        reg = SessionRegistry()
        engine = SessionLifecycleEngine(reg)
        s = engine.start_session()
        assert engine.background_session(s.session_id) is True
        assert reg.get(s.session_id).status == "background"

    def test_check_timeouts_idle(self):
        from substrate.organism.session_runtime import (
            Session, SessionLifecycleEngine, SessionRegistry,
        )
        reg = SessionRegistry()
        engine = SessionLifecycleEngine(reg)
        s = Session(status="active")
        s.last_seen_at = time.time() - 400
        reg.register(s)
        transitions = engine.check_timeouts()
        assert len(transitions) == 1
        assert transitions[0][1] == "idle"

    def test_check_timeouts_disconnect(self):
        from substrate.organism.session_runtime import (
            Session, SessionLifecycleEngine, SessionRegistry,
        )
        reg = SessionRegistry()
        engine = SessionLifecycleEngine(reg)
        s = Session(status="active")
        s.last_seen_at = time.time() - 700
        reg.register(s)
        transitions = engine.check_timeouts()
        assert len(transitions) == 1
        assert transitions[0][1] == "disconnected"


# ── Handoff Runtime Tests ────────────────────────────────────────


class TestSessionHandoffRuntime:
    def test_initiate_handoff(self):
        from substrate.organism.session_runtime import (
            Session, SessionHandoffRuntime, SessionRegistry,
        )
        reg = SessionRegistry()
        s1 = Session(device_id="desktop")
        s2 = Session(device_id="phone")
        reg.register(s1)
        reg.register(s2)
        runtime = SessionHandoffRuntime(reg)
        h = runtime.initiate_handoff(s1.session_id, s2.session_id)
        assert h is not None
        assert h.source_device_id == "desktop"
        assert h.target_device_id == "phone"
        assert h.status == "pending"

    def test_initiate_handoff_missing_session(self):
        from substrate.organism.session_runtime import SessionHandoffRuntime, SessionRegistry
        reg = SessionRegistry()
        runtime = SessionHandoffRuntime(reg)
        h = runtime.initiate_handoff("nonexistent", "also-nonexistent")
        assert h is None

    def test_complete_handoff(self):
        from substrate.organism.session_runtime import (
            Session, SessionHandoffRuntime, SessionRegistry,
        )
        reg = SessionRegistry()
        s1 = Session()
        s2 = Session()
        reg.register(s1)
        reg.register(s2)
        runtime = SessionHandoffRuntime(reg)
        h = runtime.initiate_handoff(s1.session_id, s2.session_id)
        assert runtime.complete_handoff(h.handoff_id) is True
        assert runtime.get_handoff(h.handoff_id).status == "completed"

    def test_get_recent_handoffs(self):
        from substrate.organism.session_runtime import (
            Session, SessionHandoffRuntime, SessionRegistry,
        )
        reg = SessionRegistry()
        s1 = Session()
        s2 = Session()
        reg.register(s1)
        reg.register(s2)
        runtime = SessionHandoffRuntime(reg)
        runtime.initiate_handoff(s1.session_id, s2.session_id)
        recent = runtime.get_recent_handoffs()
        assert len(recent) == 1

    def test_get_pending_handoffs(self):
        from substrate.organism.session_runtime import (
            Session, SessionHandoffRuntime, SessionRegistry,
        )
        reg = SessionRegistry()
        s1 = Session()
        s2 = Session()
        reg.register(s1)
        reg.register(s2)
        runtime = SessionHandoffRuntime(reg)
        h = runtime.initiate_handoff(s1.session_id, s2.session_id)
        assert len(runtime.get_pending_handoffs()) == 1
        runtime.complete_handoff(h.handoff_id)
        assert len(runtime.get_pending_handoffs()) == 0

    def test_handoff_persists_to_disk(self):
        from substrate.organism.session_runtime import (
            Session, SessionHandoffRuntime, SessionRegistry,
        )
        reg = SessionRegistry()
        s1 = Session()
        s2 = Session()
        reg.register(s1)
        reg.register(s2)
        runtime = SessionHandoffRuntime(reg)
        h = runtime.initiate_handoff(s1.session_id, s2.session_id)
        path = os.path.join(_test_dir, "data", "umh", "session", "handoffs", f"{h.handoff_id}.json")
        assert os.path.exists(path)
        with open(path) as f:
            data = json.load(f)
        assert data["source_session_id"] == s1.session_id


# ── Continuity Graph Tests ───────────────────────────────────────


class TestSessionContinuityGraph:
    def test_add_and_query(self):
        from substrate.organism.session_runtime import SessionContinuityGraph
        g = SessionContinuityGraph()
        g.add_link(profile_id="engineer", session_id="s1", work_packet_id="wp1")
        links = g.get_links_for_session("s1")
        assert len(links) == 1
        assert links[0].profile_id == "engineer"
        assert links[0].work_packet_id == "wp1"

    def test_query_by_profile(self):
        from substrate.organism.session_runtime import SessionContinuityGraph
        g = SessionContinuityGraph()
        g.add_link(profile_id="engineer", session_id="s1")
        g.add_link(profile_id="engineer", session_id="s2")
        g.add_link(profile_id="founder", session_id="s3")
        links = g.get_links_for_profile("engineer")
        assert len(links) == 2

    def test_query_by_work_packet(self):
        from substrate.organism.session_runtime import SessionContinuityGraph
        g = SessionContinuityGraph()
        g.add_link(session_id="s1", work_packet_id="wp1")
        g.add_link(session_id="s2", work_packet_id="wp1")
        links = g.get_links_for_work_packet("wp1")
        assert len(links) == 2

    def test_persistence(self):
        from substrate.organism.session_runtime import SessionContinuityGraph
        g = SessionContinuityGraph()
        g.add_link(profile_id="artist", session_id="s1", work_packet_id="wp1")
        g2 = SessionContinuityGraph()
        links = g2.get_all_links()
        assert len(links) >= 1
        assert links[0].profile_id == "artist"

    def test_full_lineage(self):
        from substrate.organism.session_runtime import SessionContinuityGraph
        g = SessionContinuityGraph()
        link = g.add_link(
            profile_id="engineer",
            session_id="s1",
            objective_id="obj1",
            work_packet_id="wp1",
            outcome_id="out1",
        )
        assert link.profile_id == "engineer"
        assert link.objective_id == "obj1"
        assert link.outcome_id == "out1"


# ── Timeline Tests ───────────────────────────────────────────────


class TestSessionTimeline:
    def test_emit_and_retrieve(self):
        from substrate.organism.session_runtime import SessionTimeline
        tl = SessionTimeline()
        tl.emit("session_started", "s1", "Started desktop session")
        events = tl.get_recent()
        assert len(events) == 1
        assert events[0].event_type == "session_started"

    def test_get_for_session(self):
        from substrate.organism.session_runtime import SessionTimeline
        tl = SessionTimeline()
        tl.emit("session_started", "s1", "Started")
        tl.emit("session_started", "s2", "Started another")
        events = tl.get_for_session("s1")
        assert len(events) == 1
        assert events[0].session_id == "s1"

    def test_limit(self):
        from substrate.organism.session_runtime import SessionTimeline
        tl = SessionTimeline()
        for i in range(10):
            tl.emit("test", f"s{i}", f"Event {i}")
        events = tl.get_recent(limit=5)
        assert len(events) == 5

    def test_persistence(self):
        from substrate.organism.session_runtime import SessionTimeline
        tl = SessionTimeline()
        tl.emit("test", "s1", "Persisted event")
        tl2 = SessionTimeline()
        events = tl2.get_recent()
        assert len(events) >= 1


# ── Session Runtime (Integration) Tests ──────────────────────────


class TestSessionRuntime:
    def test_start_session(self):
        from substrate.organism.session_runtime import get_session_runtime
        rt = get_session_runtime()
        s = rt.start_session(session_type="desktop", device_id="d1", profile_id="engineer")
        assert s.session_type == "desktop"
        assert s.device_id == "d1"
        assert s.profile_id == "engineer"
        assert rt.get_session(s.session_id) is not None

    def test_start_primary_session(self):
        from substrate.organism.session_runtime import get_session_runtime
        rt = get_session_runtime()
        s = rt.start_session(
            session_type="desktop", device_id="d1", authority="primary"
        )
        primary = rt.get_primary_session()
        assert primary is not None
        assert primary.session_id == s.session_id

    def test_suspend_and_resume(self):
        from substrate.organism.session_runtime import get_session_runtime
        rt = get_session_runtime()
        s = rt.start_session()
        assert rt.suspend_session(s.session_id) is True
        assert rt.get_session(s.session_id).status == "suspended"
        assert rt.resume_session(s.session_id) is True
        assert rt.get_session(s.session_id).status == "active"

    def test_disconnect_and_restore(self):
        from substrate.organism.session_runtime import get_session_runtime
        rt = get_session_runtime()
        s = rt.start_session()
        assert rt.disconnect_session(s.session_id) is True
        assert rt.get_session(s.session_id).status == "disconnected"
        assert rt.restore_session(s.session_id) is True
        assert rt.get_session(s.session_id).status == "active"

    def test_promote_to_primary(self):
        from substrate.organism.session_runtime import get_session_runtime
        rt = get_session_runtime()
        s1 = rt.start_session(authority="primary")
        s2 = rt.start_session(authority="secondary")
        success, demoted = rt.promote_to_primary(s2.session_id)
        assert success is True
        assert demoted == s1.session_id
        assert rt.get_primary_session().session_id == s2.session_id

    def test_list_sessions(self):
        from substrate.organism.session_runtime import get_session_runtime
        rt = get_session_runtime()
        rt.start_session(session_type="desktop")
        rt.start_session(session_type="phone")
        assert len(rt.list_sessions()) == 2

    def test_list_active_sessions(self):
        from substrate.organism.session_runtime import get_session_runtime
        rt = get_session_runtime()
        s1 = rt.start_session()
        rt.start_session()
        rt.disconnect_session(s1.session_id)
        assert len(rt.list_active_sessions()) == 1

    def test_secondary_and_background(self):
        from substrate.organism.session_runtime import get_session_runtime
        rt = get_session_runtime()
        s1 = rt.start_session(authority="secondary")
        s2 = rt.start_session(authority="background")
        assert len(rt.get_secondary_sessions()) == 1
        assert len(rt.get_background_sessions()) == 1

    def test_bind_work_packet(self):
        from substrate.organism.session_runtime import get_session_runtime
        rt = get_session_runtime()
        s = rt.start_session()
        assert rt.bind_work_packet(s.session_id, "wp-1") is True
        assert "wp-1" in rt.get_session(s.session_id).bound_work_packets

    def test_unbind_work_packet(self):
        from substrate.organism.session_runtime import get_session_runtime
        rt = get_session_runtime()
        s = rt.start_session()
        rt.bind_work_packet(s.session_id, "wp-1")
        assert rt.unbind_work_packet(s.session_id, "wp-1") is True
        assert "wp-1" not in rt.get_session(s.session_id).bound_work_packets

    def test_handoff_flow(self):
        from substrate.organism.session_runtime import get_session_runtime
        rt = get_session_runtime()
        s1 = rt.start_session(session_type="desktop", device_id="d1")
        s2 = rt.start_session(session_type="phone", device_id="d2")
        h = rt.initiate_handoff(s1.session_id, s2.session_id)
        assert h is not None
        assert h.source_device_id == "d1"
        assert h.target_device_id == "d2"
        assert rt.complete_handoff(h.handoff_id) is True
        assert rt.get_handoff(h.handoff_id).status == "completed"

    def test_get_recent_handoffs(self):
        from substrate.organism.session_runtime import get_session_runtime
        rt = get_session_runtime()
        s1 = rt.start_session()
        s2 = rt.start_session()
        rt.initiate_handoff(s1.session_id, s2.session_id)
        assert len(rt.get_recent_handoffs()) == 1

    def test_get_pending_handoffs(self):
        from substrate.organism.session_runtime import get_session_runtime
        rt = get_session_runtime()
        s1 = rt.start_session()
        s2 = rt.start_session()
        h = rt.initiate_handoff(s1.session_id, s2.session_id)
        assert len(rt.get_pending_handoffs()) == 1
        rt.complete_handoff(h.handoff_id)
        assert len(rt.get_pending_handoffs()) == 0

    def test_timeline_records_lifecycle(self):
        from substrate.organism.session_runtime import get_session_runtime
        rt = get_session_runtime()
        s = rt.start_session()
        rt.suspend_session(s.session_id)
        rt.resume_session(s.session_id)
        events = rt.get_timeline()
        types = [e.event_type for e in events]
        assert "session_started" in types
        assert "session_suspended" in types
        assert "session_resumed" in types

    def test_session_timeline(self):
        from substrate.organism.session_runtime import get_session_runtime
        rt = get_session_runtime()
        s = rt.start_session()
        rt.suspend_session(s.session_id)
        events = rt.get_session_timeline(s.session_id)
        assert len(events) == 2

    def test_continuity_links(self):
        from substrate.organism.session_runtime import get_session_runtime
        rt = get_session_runtime()
        s = rt.start_session(profile_id="engineer")
        rt.bind_work_packet(s.session_id, "wp-1")
        links = rt.get_continuity_links(s.session_id)
        assert len(links) >= 1

    def test_check_timeouts(self):
        from substrate.organism.session_runtime import Session, get_session_runtime
        rt = get_session_runtime()
        s = rt.start_session()
        rt._registry._sessions[s.session_id].last_seen_at = time.time() - 400
        transitions = rt.check_timeouts()
        assert len(transitions) == 1

    def test_get_state(self):
        from substrate.organism.session_runtime import get_session_runtime
        rt = get_session_runtime()
        rt.start_session(authority="primary")
        rt.start_session(authority="secondary")
        state = rt.get_state()
        assert state["primary_session"] is not None
        assert len(state["secondary_sessions"]) == 1
        assert state["total_active"] == 2

    def test_capture_snapshot(self):
        from substrate.organism.session_runtime import get_session_runtime
        rt = get_session_runtime()
        rt.start_session(authority="primary")
        snap = rt.capture_snapshot()
        assert snap.snapshot_id.startswith("sssnap-")
        assert snap.primary_session is not None
        assert snap.total_active >= 1

    def test_promote_demote_timeline(self):
        from substrate.organism.session_runtime import get_session_runtime
        rt = get_session_runtime()
        s1 = rt.start_session(authority="primary")
        s2 = rt.start_session(authority="secondary")
        rt.promote_to_primary(s2.session_id)
        events = rt.get_timeline()
        types = [e.event_type for e in events]
        assert "session_promoted" in types
        assert "session_demoted" in types


# ── Singleton Tests ──────────────────────────────────────────────


class TestSingleton:
    def test_same_instance(self):
        from substrate.organism.session_runtime import get_session_runtime
        r1 = get_session_runtime()
        r2 = get_session_runtime()
        assert r1 is r2

    def test_reset(self):
        from substrate.organism.session_runtime import (
            get_session_runtime, reset_session_runtime,
        )
        r1 = get_session_runtime()
        reset_session_runtime()
        r2 = get_session_runtime()
        assert r1 is not r2


# ── Acceptance Tests ─────────────────────────────────────────────


class TestAcceptance:
    def test_full_lifecycle(self):
        """Acceptance scenario from spec: desktop → phone → desktop."""
        from substrate.organism.session_runtime import get_session_runtime
        rt = get_session_runtime()

        desktop = rt.start_session(
            session_type="desktop", device_id="desktop-1",
            profile_id="engineer", authority="primary",
        )
        assert rt.get_primary_session().session_id == desktop.session_id

        rt.bind_work_packet(desktop.session_id, "wp-bugfix-1")
        rt.bind_work_packet(desktop.session_id, "wp-bugfix-2")

        rt.suspend_session(desktop.session_id)

        phone = rt.start_session(
            session_type="phone", device_id="phone-1",
            profile_id="engineer",
        )
        rt.promote_to_primary(phone.session_id)
        assert rt.get_primary_session().session_id == phone.session_id

        handoff = rt.initiate_handoff(desktop.session_id, phone.session_id)
        assert handoff is not None
        rt.complete_handoff(handoff.handoff_id)

        rt.suspend_session(phone.session_id)
        rt.resume_session(desktop.session_id)
        rt.promote_to_primary(desktop.session_id)
        assert rt.get_primary_session().session_id == desktop.session_id

        events = rt.get_timeline()
        types = [e.event_type for e in events]
        assert "session_started" in types
        assert "session_suspended" in types
        assert "session_promoted" in types
        assert "handoff_initiated" in types
        assert "handoff_completed" in types
        assert "session_resumed" in types

    def test_multi_device_awareness(self):
        """Multiple devices with correct authority classification."""
        from substrate.organism.session_runtime import get_session_runtime
        rt = get_session_runtime()

        desktop = rt.start_session(
            session_type="desktop", device_id="d1",
            profile_id="engineer", authority="primary",
        )
        phone = rt.start_session(
            session_type="phone", device_id="d2",
            authority="secondary",
        )
        vps = rt.start_session(
            session_type="vps", device_id="vps1",
            authority="background",
        )

        assert rt.get_primary_session().session_id == desktop.session_id
        assert len(rt.get_secondary_sessions()) == 1
        assert len(rt.get_background_sessions()) == 1
        assert len(rt.list_active_sessions()) == 3

    def test_work_binding_lineage(self):
        """Work packets bound to sessions create continuity links."""
        from substrate.organism.session_runtime import get_session_runtime
        rt = get_session_runtime()

        s = rt.start_session(profile_id="engineer")
        rt.bind_work_packet(s.session_id, "wp-1")
        rt.bind_work_packet(s.session_id, "wp-2")

        links = rt.get_continuity_links(s.session_id)
        assert len(links) >= 2
        wp_ids = {l.work_packet_id for l in links if l.work_packet_id}
        assert "wp-1" in wp_ids
        assert "wp-2" in wp_ids

    def test_session_types_all_valid(self):
        """All 10 session types can be created."""
        from substrate.organism.session_runtime import SessionType, get_session_runtime
        rt = get_session_runtime()
        for st in SessionType:
            s = rt.start_session(session_type=st.value)
            assert s.session_type == st.value

    def test_no_execution(self):
        """Session runtime does NOT execute work or launch applications."""
        from substrate.organism.session_runtime import SessionRuntime
        methods = dir(SessionRuntime)
        execution_terms = ["execute", "launch", "run_command", "deploy", "approve"]
        for term in execution_terms:
            matching = [m for m in methods if term in m.lower() and not m.startswith("_")]
            assert len(matching) == 0, f"Found execution method: {matching}"

    def test_handoff_package_contents(self):
        """Handoff package captures operational context."""
        from substrate.organism.session_runtime import get_session_runtime
        rt = get_session_runtime()
        s1 = rt.start_session(session_type="desktop", device_id="d1")
        s2 = rt.start_session(session_type="phone", device_id="d2")
        rt.bind_work_packet(s1.session_id, "wp-1")
        h = rt.initiate_handoff(s1.session_id, s2.session_id)
        assert h is not None
        d = h.to_dict()
        required_keys = [
            "active_work_packets", "continuity_snapshot",
            "projection_snapshot", "workstation_state", "profile_context",
        ]
        for key in required_keys:
            assert key in d, f"Missing handoff key: {key}"

    def test_timeout_detection(self):
        """Tick integration: timeout detection works."""
        from substrate.organism.session_runtime import get_session_runtime
        rt = get_session_runtime()
        s = rt.start_session()
        rt._registry._sessions[s.session_id].last_seen_at = time.time() - 700
        transitions = rt.check_timeouts()
        assert len(transitions) >= 1
        events = rt.get_timeline()
        disconnect_events = [
            e for e in events if e.event_type == "session_disconnected"
        ]
        assert len(disconnect_events) >= 1

    def test_snapshot_captures_authority(self):
        """Snapshot correctly captures authority hierarchy."""
        from substrate.organism.session_runtime import get_session_runtime
        rt = get_session_runtime()
        rt.start_session(authority="primary", device_id="d1")
        rt.start_session(authority="secondary", device_id="d2")
        rt.start_session(authority="background", device_id="d3")
        snap = rt.capture_snapshot()
        assert snap.primary_session is not None
        assert len(snap.secondary_sessions) == 1
        assert len(snap.background_sessions) == 1

    def test_profile_session_binding(self):
        """Session start with profile_id creates continuity link."""
        from substrate.organism.session_runtime import get_session_runtime
        rt = get_session_runtime()
        s = rt.start_session(profile_id="engineer")
        links = rt.get_all_continuity_links()
        profile_links = [l for l in links if l.profile_id == "engineer"]
        assert len(profile_links) >= 1
        assert profile_links[0].session_id == s.session_id

    def test_all_session_statuses(self):
        """All 5 session statuses are reachable."""
        from substrate.organism.session_runtime import get_session_runtime
        rt = get_session_runtime()
        statuses_seen = set()

        s = rt.start_session()
        statuses_seen.add(rt.get_session(s.session_id).status)

        rt._registry.update_status(s.session_id, "background")
        statuses_seen.add(rt.get_session(s.session_id).status)

        rt._registry.update_status(s.session_id, "idle")
        statuses_seen.add(rt.get_session(s.session_id).status)

        rt._registry.update_status(s.session_id, "suspended")
        statuses_seen.add(rt.get_session(s.session_id).status)

        rt._registry.update_status(s.session_id, "disconnected")
        statuses_seen.add(rt.get_session(s.session_id).status)

        assert statuses_seen == {"active", "background", "idle", "suspended", "disconnected"}
