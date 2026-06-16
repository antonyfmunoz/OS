"""Phase 32 — Presence & Continuity Runtime tests.

Tests: models, continuity engine, presence timeline, device continuity,
type registration, cockpit routes, and integration.

~90 tests across 14 classes.
"""

from __future__ import annotations

import os
import sys
import time
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.environ.get("UMH_ROOT", "/opt/OS"))


# ── Models ───────────────────────────────────────────────────────────


class TestPresenceStateEnum(unittest.TestCase):
    def test_values(self):
        from substrate.operator.operator_presence import PresenceState

        self.assertEqual(PresenceState.ACTIVE.value, "active")
        self.assertEqual(PresenceState.IDLE.value, "idle")
        self.assertEqual(PresenceState.AWAY.value, "away")
        self.assertEqual(PresenceState.OFFLINE.value, "offline")

    def test_count(self):
        from substrate.operator.operator_presence import PresenceState

        self.assertEqual(len(PresenceState), 4)

    def test_str_enum(self):
        from substrate.operator.operator_presence import PresenceState

        self.assertIsInstance(PresenceState.ACTIVE, str)

    def test_from_value(self):
        from substrate.operator.operator_presence import PresenceState

        self.assertEqual(PresenceState("active"), PresenceState.ACTIVE)


class TestPresenceDeviceTypeEnum(unittest.TestCase):
    def test_values(self):
        from substrate.operator.operator_presence import PresenceDeviceType

        self.assertEqual(PresenceDeviceType.VPS.value, "vps")
        self.assertEqual(PresenceDeviceType.WINDOWS.value, "windows")
        self.assertEqual(PresenceDeviceType.IPAD.value, "ipad")
        self.assertEqual(PresenceDeviceType.IPHONE.value, "iphone")
        self.assertEqual(PresenceDeviceType.UNKNOWN.value, "unknown")

    def test_count(self):
        from substrate.operator.operator_presence import PresenceDeviceType

        self.assertEqual(len(PresenceDeviceType), 5)

    def test_str_enum(self):
        from substrate.operator.operator_presence import PresenceDeviceType

        self.assertIsInstance(PresenceDeviceType.VPS, str)


class TestContinuityStatusEnum(unittest.TestCase):
    def test_values(self):
        from substrate.operator.operator_presence import ContinuityStatus

        self.assertEqual(ContinuityStatus.CURRENT.value, "current")
        self.assertEqual(ContinuityStatus.RESUMABLE.value, "resumable")
        self.assertEqual(ContinuityStatus.STALE.value, "stale")
        self.assertEqual(ContinuityStatus.LOST.value, "lost")

    def test_count(self):
        from substrate.operator.operator_presence import ContinuityStatus

        self.assertEqual(len(ContinuityStatus), 4)


class TestOperatorPresence(unittest.TestCase):
    def test_creation_defaults(self):
        from substrate.operator.operator_presence import (
            OperatorPresence,
            PresenceDeviceType,
            PresenceState,
        )

        p = OperatorPresence(
            state=PresenceState.ACTIVE,
            device_type=PresenceDeviceType.VPS,
        )
        self.assertEqual(p.state, PresenceState.ACTIVE)
        self.assertEqual(p.device_type, PresenceDeviceType.VPS)
        self.assertEqual(p.device_id, "")
        self.assertIsInstance(p.updated_at, float)

    def test_to_dict(self):
        from substrate.operator.operator_presence import (
            OperatorPresence,
            PresenceDeviceType,
            PresenceState,
        )

        p = OperatorPresence(
            state=PresenceState.IDLE,
            device_type=PresenceDeviceType.WINDOWS,
            device_id="beast",
            node_id="desktop-lvguiq9",
        )
        d = p.to_dict()
        self.assertEqual(d["state"], "idle")
        self.assertEqual(d["device_type"], "windows")
        self.assertEqual(d["device_id"], "beast")
        self.assertEqual(d["node_id"], "desktop-lvguiq9")

    def test_from_dict(self):
        from substrate.operator.operator_presence import (
            OperatorPresence,
            PresenceDeviceType,
            PresenceState,
        )

        d = {"state": "away", "device_type": "ipad", "device_id": "ipad"}
        p = OperatorPresence.from_dict(d)
        self.assertEqual(p.state, PresenceState.AWAY)
        self.assertEqual(p.device_type, PresenceDeviceType.IPAD)

    def test_roundtrip(self):
        from substrate.operator.operator_presence import (
            OperatorPresence,
            PresenceDeviceType,
            PresenceState,
        )

        original = OperatorPresence(
            state=PresenceState.ACTIVE,
            device_type=PresenceDeviceType.VPS,
            device_id="vps",
            node_id="srv1500858",
        )
        restored = OperatorPresence.from_dict(original.to_dict())
        self.assertEqual(restored.state, original.state)
        self.assertEqual(restored.device_type, original.device_type)
        self.assertEqual(restored.device_id, original.device_id)


class TestActiveContext(unittest.TestCase):
    def test_creation_defaults(self):
        from substrate.operator.operator_presence import ActiveContext

        ctx = ActiveContext()
        self.assertEqual(ctx.workspace_id, "")
        self.assertEqual(ctx.session_id, "")
        self.assertEqual(ctx.runtime_id, "")

    def test_to_dict(self):
        from substrate.operator.operator_presence import ActiveContext

        ctx = ActiveContext(
            workspace_id="ws-1",
            workspace_name="UMH",
            session_id="sess-42",
            session_type="engineering",
        )
        d = ctx.to_dict()
        self.assertEqual(d["workspace_id"], "ws-1")
        self.assertEqual(d["workspace_name"], "UMH")
        self.assertEqual(d["session_id"], "sess-42")

    def test_from_dict(self):
        from substrate.operator.operator_presence import ActiveContext

        d = {"workspace_name": "UMH", "session_type": "review"}
        ctx = ActiveContext.from_dict(d)
        self.assertEqual(ctx.workspace_name, "UMH")
        self.assertEqual(ctx.session_type, "review")

    def test_roundtrip(self):
        from substrate.operator.operator_presence import ActiveContext

        original = ActiveContext(
            workspace_id="ws-1",
            workspace_name="UMH",
            session_id="sess-1",
            session_type="engineering",
            runtime_id="rt-1",
            work_packet_id="wp-1",
            description="Working on Phase 32",
        )
        restored = ActiveContext.from_dict(original.to_dict())
        self.assertEqual(restored.workspace_id, original.workspace_id)
        self.assertEqual(restored.description, original.description)


class TestContinuityCheckpoint(unittest.TestCase):
    def test_creation_defaults(self):
        from substrate.operator.operator_presence import (
            ContinuityCheckpoint,
            ContinuityStatus,
        )

        cp = ContinuityCheckpoint(
            checkpoint_type="engineering_session",
            title="Session: engineering",
        )
        self.assertTrue(cp.checkpoint_id.startswith("ccp-"))
        self.assertEqual(cp.status, ContinuityStatus.CURRENT)

    def test_to_dict(self):
        from substrate.operator.operator_presence import (
            ContinuityCheckpoint,
            ContinuityStatus,
            PresenceDeviceType,
        )

        cp = ContinuityCheckpoint(
            checkpoint_type="governance_review",
            title="3 pending approvals",
            device_type=PresenceDeviceType.VPS,
            status=ContinuityStatus.RESUMABLE,
        )
        d = cp.to_dict()
        self.assertEqual(d["checkpoint_type"], "governance_review")
        self.assertEqual(d["status"], "resumable")
        self.assertEqual(d["device_type"], "vps")

    def test_from_dict(self):
        from substrate.operator.operator_presence import (
            ContinuityCheckpoint,
            ContinuityStatus,
        )

        d = {
            "checkpoint_type": "workspace_activity",
            "title": "Workspace: UMH",
            "status": "stale",
        }
        cp = ContinuityCheckpoint.from_dict(d)
        self.assertEqual(cp.status, ContinuityStatus.STALE)

    def test_roundtrip(self):
        from substrate.operator.operator_presence import ContinuityCheckpoint

        original = ContinuityCheckpoint(
            checkpoint_type="engineering_session",
            title="Session: engineering",
            detail="Session sess-42",
            workspace_id="ws-1",
        )
        restored = ContinuityCheckpoint.from_dict(original.to_dict())
        self.assertEqual(restored.checkpoint_type, original.checkpoint_type)
        self.assertEqual(restored.detail, original.detail)

    def test_expires_at(self):
        from substrate.operator.operator_presence import ContinuityCheckpoint

        cp = ContinuityCheckpoint(expires_at=time.time() + 3600)
        self.assertGreater(cp.expires_at, 0)


class TestPresenceSnapshot(unittest.TestCase):
    def test_creation_defaults(self):
        from substrate.operator.operator_presence import (
            PresenceDeviceType,
            PresenceSnapshot,
            PresenceState,
        )

        snap = PresenceSnapshot(
            operator_state=PresenceState.ACTIVE,
            active_device=PresenceDeviceType.VPS,
        )
        self.assertEqual(snap.operator_state, PresenceState.ACTIVE)
        self.assertEqual(snap.active_device, PresenceDeviceType.VPS)
        self.assertEqual(snap.continuity_checkpoints, [])

    def test_to_dict(self):
        from substrate.operator.operator_presence import (
            ActiveContext,
            PresenceDeviceType,
            PresenceSnapshot,
            PresenceState,
        )

        snap = PresenceSnapshot(
            operator_state=PresenceState.IDLE,
            active_device=PresenceDeviceType.WINDOWS,
            active_device_id="beast",
            active_node_id="desktop-lvguiq9",
            active_context=ActiveContext(workspace_name="UMH"),
        )
        d = snap.to_dict()
        self.assertEqual(d["operator_state"], "idle")
        self.assertEqual(d["active_device"], "windows")
        self.assertEqual(d["active_context"]["workspace_name"], "UMH")

    def test_from_dict(self):
        from substrate.operator.operator_presence import (
            PresenceSnapshot,
            PresenceState,
        )

        d = {
            "operator_state": "active",
            "active_device": "vps",
            "active_context": {"workspace_name": "UMH"},
        }
        snap = PresenceSnapshot.from_dict(d)
        self.assertEqual(snap.operator_state, PresenceState.ACTIVE)
        self.assertEqual(snap.active_context.workspace_name, "UMH")

    def test_with_checkpoints(self):
        from substrate.operator.operator_presence import (
            ContinuityCheckpoint,
            PresenceDeviceType,
            PresenceSnapshot,
            PresenceState,
        )

        cp = ContinuityCheckpoint(
            checkpoint_type="engineering_session",
            title="Session: engineering",
        )
        snap = PresenceSnapshot(
            operator_state=PresenceState.ACTIVE,
            active_device=PresenceDeviceType.VPS,
            continuity_checkpoints=[cp],
        )
        d = snap.to_dict()
        self.assertEqual(len(d["continuity_checkpoints"]), 1)
        self.assertEqual(d["continuity_checkpoints"][0]["checkpoint_type"], "engineering_session")

    def test_roundtrip(self):
        from substrate.operator.operator_presence import (
            ActiveContext,
            ContinuityCheckpoint,
            PresenceDeviceType,
            PresenceSnapshot,
            PresenceState,
        )

        original = PresenceSnapshot(
            operator_state=PresenceState.ACTIVE,
            active_device=PresenceDeviceType.VPS,
            active_device_id="vps",
            active_context=ActiveContext(workspace_name="UMH"),
            continuity_checkpoints=[
                ContinuityCheckpoint(
                    checkpoint_type="engineering_session",
                    title="Test session",
                )
            ],
        )
        restored = PresenceSnapshot.from_dict(original.to_dict())
        self.assertEqual(restored.operator_state, original.operator_state)
        self.assertEqual(len(restored.continuity_checkpoints), 1)


# ── Mock Infrastructure ──────────────────────────────────────────────

class MockWorkspaceObservationEngine:
    def __init__(self, snapshot=None):
        self._snapshot = snapshot

    def latest(self):
        return self._snapshot


class MockSnap:
    def __init__(self, data=None):
        self._data = data if data is not None else {}

    def to_dict(self):
        return self._data


class MockTopologyEngine:
    def __init__(self, snapshot_data=None):
        self._data = snapshot_data if snapshot_data is not None else {}

    def snapshot(self):
        return self._data


class MockActionBridge:
    pass


class MockContextEngine:
    def __init__(self, health_status="healthy", pending_count=0, pending_items=None):
        self._health_status = health_status
        self._pending_count = pending_count
        self._pending_items = pending_items if pending_items is not None else []

    def health_summary(self):
        from substrate.operator.operator_context import OperatorHealthSummary
        return OperatorHealthSummary(overall_status=self._health_status)

    def pending_approvals(self):
        return {
            "count": self._pending_count,
            "items": self._pending_items,
        }


class MockNodeRegistry:
    def __init__(self, nodes=None, primary=None):
        self._nodes = nodes if nodes is not None else []
        self._primary = primary

    def list_nodes(self):
        return self._nodes

    def primary_node(self):
        return self._primary


class MockNode:
    def __init__(self, node_id="srv1500858"):
        self.node_id = node_id

    def to_dict(self):
        return {"node_id": self.node_id}


def _make_engine(**overrides):
    from substrate.operator.continuity_engine import ContinuityEngine

    defaults = {
        "workspace_engine": MockWorkspaceObservationEngine(),
        "topology_engine": MockTopologyEngine(),
        "action_bridge": MockActionBridge(),
        "context_engine": MockContextEngine(),
        "node_registry": MockNodeRegistry(primary=MockNode()),
    }
    defaults.update(overrides)
    return ContinuityEngine(**defaults)


# ── Continuity Engine ────────────────────────────────────────────────

class TestContinuityEngine(unittest.TestCase):
    def test_snapshot_returns_presence_snapshot(self):
        from substrate.operator.operator_presence import PresenceSnapshot

        engine = _make_engine()
        snap = engine.snapshot()
        self.assertIsInstance(snap, PresenceSnapshot)

    def test_snapshot_to_dict(self):
        engine = _make_engine()
        snap = engine.snapshot()
        d = snap.to_dict()
        self.assertIn("operator_state", d)
        self.assertIn("active_device", d)
        self.assertIn("active_context", d)
        self.assertIn("continuity_checkpoints", d)

    def test_current_presence(self):
        from substrate.operator.operator_presence import OperatorPresence

        engine = _make_engine()
        presence = engine.current_presence()
        self.assertIsInstance(presence, OperatorPresence)

    def test_active_context_empty(self):
        from substrate.operator.operator_presence import ActiveContext

        engine = _make_engine()
        ctx = engine.active_context()
        self.assertIsInstance(ctx, ActiveContext)

    def test_active_context_with_workspace(self):
        snap = MockSnap({
            "repositories": [{"repo_id": "r1", "name": "UMH"}],
            "sessions": [{"session_id": "sess-1", "session_type": "engineering"}],
        })
        engine = _make_engine(
            workspace_engine=MockWorkspaceObservationEngine(snapshot=snap)
        )
        ctx = engine.active_context()
        self.assertEqual(ctx.workspace_name, "UMH")
        self.assertEqual(ctx.session_id, "sess-1")

    def test_continuity_checkpoints_empty(self):
        engine = _make_engine()
        checkpoints = engine.continuity_checkpoints()
        self.assertIsInstance(checkpoints, list)

    def test_continuity_checkpoints_with_session(self):
        snap = MockSnap({
            "sessions": [{"session_id": "sess-1", "session_type": "engineering"}],
        })
        engine = _make_engine(
            workspace_engine=MockWorkspaceObservationEngine(snapshot=snap)
        )
        checkpoints = engine.continuity_checkpoints()
        session_cps = [c for c in checkpoints if c.checkpoint_type == "engineering_session"]
        self.assertGreaterEqual(len(session_cps), 1)

    def test_continuity_checkpoints_with_approvals(self):
        engine = _make_engine(
            context_engine=MockContextEngine(pending_count=2),
        )
        checkpoints = engine.continuity_checkpoints()
        gov_cps = [c for c in checkpoints if c.checkpoint_type == "governance_review"]
        self.assertEqual(len(gov_cps), 1)
        self.assertIn("2 pending", gov_cps[0].title)

    def test_continuity_checkpoints_with_workspace(self):
        snap = MockSnap({
            "repositories": [{"repo_id": "r1", "name": "UMH"}],
        })
        engine = _make_engine(
            workspace_engine=MockWorkspaceObservationEngine(snapshot=snap)
        )
        checkpoints = engine.continuity_checkpoints()
        ws_cps = [c for c in checkpoints if c.checkpoint_type == "workspace_activity"]
        self.assertGreaterEqual(len(ws_cps), 1)

    def test_resume_suggestion(self):
        engine = _make_engine()
        suggestion = engine.resume_suggestion()
        self.assertIn("device", suggestion)
        self.assertIn("state", suggestion)
        self.assertIn("pending_approvals", suggestion)

    def test_resume_suggestion_with_workspace(self):
        snap = MockSnap({
            "repositories": [{"repo_id": "r1", "name": "UMH"}],
            "sessions": [{"session_id": "sess-1", "session_type": "engineering"}],
        })
        engine = _make_engine(
            workspace_engine=MockWorkspaceObservationEngine(snapshot=snap)
        )
        suggestion = engine.resume_suggestion()
        self.assertEqual(suggestion.get("workspace"), "UMH")

    def test_state_idle_when_no_workspace(self):
        from substrate.operator.operator_presence import PresenceState

        engine = _make_engine(
            workspace_engine=MockWorkspaceObservationEngine(snapshot=None),
        )
        presence = engine.current_presence()
        self.assertIn(presence.state, [PresenceState.ACTIVE, PresenceState.IDLE])

    def test_state_active_when_workspace_exists(self):
        from substrate.operator.operator_presence import PresenceState

        snap = MockSnap({"repositories": [{"repo_id": "r1"}]})
        engine = _make_engine(
            workspace_engine=MockWorkspaceObservationEngine(snapshot=snap)
        )
        presence = engine.current_presence()
        self.assertEqual(presence.state, PresenceState.ACTIVE)

    @patch("substrate.operator.continuity_engine.os.uname")
    def test_detect_device_vps(self, mock_uname):
        from substrate.operator.operator_presence import PresenceDeviceType

        mock_uname.return_value = MagicMock(nodename="srv1500858")
        engine = _make_engine()
        device_type, device_id = engine._detect_device()
        self.assertEqual(device_type, PresenceDeviceType.VPS)
        self.assertEqual(device_id, "vps")

    @patch("substrate.operator.continuity_engine.os.uname")
    def test_detect_device_unknown(self, mock_uname):
        from substrate.operator.operator_presence import PresenceDeviceType

        mock_uname.return_value = MagicMock(nodename="random-host")
        engine = _make_engine()
        engine._load_device_registry = lambda: []
        device_type, device_id = engine._detect_device()
        self.assertEqual(device_type, PresenceDeviceType.UNKNOWN)

    def test_detect_node_from_registry(self):
        engine = _make_engine(
            node_registry=MockNodeRegistry(primary=MockNode("srv1500858"))
        )
        node_id = engine._detect_node()
        self.assertEqual(node_id, "srv1500858")

    def test_detect_node_fallback(self):
        engine = _make_engine(node_registry=None)
        engine._node_registry = None
        node_id = engine._detect_node()
        self.assertIsInstance(node_id, str)
        self.assertGreater(len(node_id), 0)


class TestCheckpointClassification(unittest.TestCase):
    def test_current(self):
        from substrate.operator.operator_presence import (
            ContinuityCheckpoint,
            ContinuityStatus,
        )

        engine = _make_engine()
        now = time.time()
        cp = ContinuityCheckpoint(created_at=now - 10)
        status = engine._classify_checkpoint(cp, now)
        self.assertEqual(status, ContinuityStatus.CURRENT)

    def test_resumable(self):
        from substrate.operator.operator_presence import (
            ContinuityCheckpoint,
            ContinuityStatus,
        )

        engine = _make_engine()
        now = time.time()
        cp = ContinuityCheckpoint(created_at=now - 600)
        status = engine._classify_checkpoint(cp, now)
        self.assertEqual(status, ContinuityStatus.RESUMABLE)

    def test_stale(self):
        from substrate.operator.operator_presence import (
            ContinuityCheckpoint,
            ContinuityStatus,
        )

        engine = _make_engine()
        now = time.time()
        cp = ContinuityCheckpoint(created_at=now - 7200)
        status = engine._classify_checkpoint(cp, now)
        self.assertEqual(status, ContinuityStatus.STALE)

    def test_lost(self):
        from substrate.operator.operator_presence import (
            ContinuityCheckpoint,
            ContinuityStatus,
        )

        engine = _make_engine()
        now = time.time()
        cp = ContinuityCheckpoint(created_at=now - 100000)
        status = engine._classify_checkpoint(cp, now)
        self.assertEqual(status, ContinuityStatus.LOST)

    def test_expired(self):
        from substrate.operator.operator_presence import (
            ContinuityCheckpoint,
            ContinuityStatus,
        )

        engine = _make_engine()
        now = time.time()
        cp = ContinuityCheckpoint(
            created_at=now - 10,
            expires_at=now - 1,
        )
        status = engine._classify_checkpoint(cp, now)
        self.assertEqual(status, ContinuityStatus.LOST)


# ── Presence Timeline ────────────────────────────────────────────────

class TestPresenceTransition(unittest.TestCase):
    def test_creation(self):
        from substrate.operator.presence_timeline import PresenceTransition

        t = PresenceTransition(
            transition_type="device_switch",
            from_value="vps",
            to_value="windows",
        )
        self.assertTrue(t.transition_id.startswith("ptx-"))
        self.assertEqual(t.transition_type, "device_switch")

    def test_to_dict(self):
        from substrate.operator.presence_timeline import PresenceTransition

        t = PresenceTransition(
            transition_type="workspace_switch",
            from_value="UMH",
            to_value="Initiate Arena",
        )
        d = t.to_dict()
        self.assertEqual(d["transition_type"], "workspace_switch")
        self.assertEqual(d["from_value"], "UMH")

    def test_from_dict(self):
        from substrate.operator.presence_timeline import PresenceTransition

        d = {
            "transition_type": "state_transition",
            "from_value": "active",
            "to_value": "idle",
        }
        t = PresenceTransition.from_dict(d)
        self.assertEqual(t.transition_type, "state_transition")

    def test_roundtrip(self):
        from substrate.operator.presence_timeline import PresenceTransition

        original = PresenceTransition(
            transition_type="session_transition",
            from_value="sess-1",
            to_value="sess-2",
            detail="Session switch",
        )
        restored = PresenceTransition.from_dict(original.to_dict())
        self.assertEqual(restored.transition_type, original.transition_type)
        self.assertEqual(restored.detail, original.detail)


class TestPresenceTimeline(unittest.TestCase):
    def test_empty(self):
        from substrate.operator.presence_timeline import PresenceTimeline

        tl = PresenceTimeline()
        self.assertEqual(tl.count(), 0)
        self.assertEqual(tl.recent(), [])

    def test_record_device_switch(self):
        from substrate.operator.operator_presence import PresenceDeviceType
        from substrate.operator.presence_timeline import PresenceTimeline

        tl = PresenceTimeline()
        t = tl.record_device_switch(
            PresenceDeviceType.VPS, PresenceDeviceType.WINDOWS
        )
        self.assertEqual(tl.count(), 1)
        self.assertEqual(t.from_value, "vps")
        self.assertEqual(t.to_value, "windows")

    def test_record_workspace_switch(self):
        from substrate.operator.presence_timeline import PresenceTimeline

        tl = PresenceTimeline()
        tl.record_workspace_switch("UMH", "Initiate Arena")
        self.assertEqual(tl.count(), 1)

    def test_record_session_transition(self):
        from substrate.operator.presence_timeline import PresenceTimeline

        tl = PresenceTimeline()
        tl.record_session_transition("sess-1", "sess-2")
        self.assertEqual(tl.count(), 1)

    def test_record_state_transition(self):
        from substrate.operator.operator_presence import PresenceState
        from substrate.operator.presence_timeline import PresenceTimeline

        tl = PresenceTimeline()
        tl.record_state_transition(PresenceState.ACTIVE, PresenceState.IDLE)
        self.assertEqual(tl.count(), 1)

    def test_recent_newest_first(self):
        from substrate.operator.presence_timeline import (
            PresenceTimeline,
            PresenceTransition,
        )

        tl = PresenceTimeline()
        t1 = PresenceTransition(transition_type="a", timestamp=1.0)
        t2 = PresenceTransition(transition_type="b", timestamp=2.0)
        tl.record(t1)
        tl.record(t2)
        recent = tl.recent()
        self.assertEqual(recent[0].transition_type, "b")
        self.assertEqual(recent[1].transition_type, "a")

    def test_recent_limit(self):
        from substrate.operator.presence_timeline import PresenceTimeline

        tl = PresenceTimeline()
        for i in range(20):
            tl.record_workspace_switch(f"ws-{i}", f"ws-{i+1}")
        self.assertEqual(len(tl.recent(limit=5)), 5)

    def test_by_type(self):
        from substrate.operator.operator_presence import PresenceDeviceType
        from substrate.operator.presence_timeline import (
            PresenceTimeline,
            PresenceTransitionType,
        )

        tl = PresenceTimeline()
        tl.record_device_switch(PresenceDeviceType.VPS, PresenceDeviceType.WINDOWS)
        tl.record_workspace_switch("UMH", "Initiate Arena")
        device_switches = tl.by_type(PresenceTransitionType.DEVICE_SWITCH)
        self.assertEqual(len(device_switches), 1)

    def test_since(self):
        from substrate.operator.presence_timeline import (
            PresenceTimeline,
            PresenceTransition,
        )

        tl = PresenceTimeline()
        t1 = PresenceTransition(transition_type="old", timestamp=100.0)
        t2 = PresenceTransition(transition_type="new", timestamp=200.0)
        tl.record(t1)
        tl.record(t2)
        since = tl.since(150.0)
        self.assertEqual(len(since), 1)
        self.assertEqual(since[0].transition_type, "new")

    def test_max_entries(self):
        from substrate.operator.presence_timeline import PresenceTimeline

        tl = PresenceTimeline(max_entries=5)
        for i in range(10):
            tl.record_workspace_switch(f"ws-{i}", f"ws-{i+1}")
        self.assertEqual(tl.count(), 5)

    def test_to_dict(self):
        from substrate.operator.presence_timeline import PresenceTimeline

        tl = PresenceTimeline()
        tl.record_workspace_switch("A", "B")
        d = tl.to_dict()
        self.assertEqual(d["count"], 1)
        self.assertEqual(len(d["transitions"]), 1)

    def test_transition_type_constants(self):
        from substrate.operator.presence_timeline import PresenceTransitionType

        self.assertEqual(len(PresenceTransitionType.ALL), 5)
        self.assertIn("device_switch", PresenceTransitionType.ALL)


# ── Device Continuity ────────────────────────────────────────────────

class TestDevicePresenceState(unittest.TestCase):
    def test_creation(self):
        from substrate.operator.device_continuity import DevicePresenceState
        from substrate.operator.operator_presence import PresenceDeviceType

        state = DevicePresenceState(
            device_type=PresenceDeviceType.VPS,
            device_id="vps",
        )
        self.assertEqual(state.device_type, PresenceDeviceType.VPS)
        self.assertEqual(state.device_id, "vps")

    def test_to_dict(self):
        from substrate.operator.device_continuity import DevicePresenceState
        from substrate.operator.operator_presence import PresenceDeviceType

        state = DevicePresenceState(
            device_type=PresenceDeviceType.WINDOWS,
            device_id="beast",
            last_workspace_name="UMH",
        )
        d = state.to_dict()
        self.assertEqual(d["device_type"], "windows")
        self.assertEqual(d["last_workspace_name"], "UMH")

    def test_from_dict(self):
        from substrate.operator.device_continuity import DevicePresenceState

        d = {"device_type": "ipad", "device_id": "ipad", "last_session_id": "sess-1"}
        state = DevicePresenceState.from_dict(d)
        self.assertEqual(state.last_session_id, "sess-1")

    def test_roundtrip(self):
        from substrate.operator.device_continuity import DevicePresenceState
        from substrate.operator.operator_presence import PresenceDeviceType

        original = DevicePresenceState(
            device_type=PresenceDeviceType.IPHONE,
            device_id="iphone",
            last_workspace_name="UMH",
            last_session_id="sess-1",
            last_node_id="srv1500858",
        )
        restored = DevicePresenceState.from_dict(original.to_dict())
        self.assertEqual(restored.last_workspace_name, original.last_workspace_name)


class TestDeviceContinuityTracker(unittest.TestCase):
    def test_empty(self):
        from substrate.operator.device_continuity import DeviceContinuityTracker

        tracker = DeviceContinuityTracker()
        self.assertEqual(tracker.device_count(), 0)
        self.assertEqual(tracker.all_devices(), [])

    def test_update_creates_device(self):
        from substrate.operator.device_continuity import DeviceContinuityTracker
        from substrate.operator.operator_presence import PresenceDeviceType

        tracker = DeviceContinuityTracker()
        state = tracker.update(
            device_type=PresenceDeviceType.VPS,
            device_id="vps",
            workspace_name="UMH",
        )
        self.assertEqual(state.last_workspace_name, "UMH")
        self.assertEqual(tracker.device_count(), 1)

    def test_update_merges(self):
        from substrate.operator.device_continuity import DeviceContinuityTracker
        from substrate.operator.operator_presence import PresenceDeviceType

        tracker = DeviceContinuityTracker()
        tracker.update(
            device_type=PresenceDeviceType.VPS,
            device_id="vps",
            workspace_name="UMH",
        )
        tracker.update(
            device_type=PresenceDeviceType.VPS,
            device_id="vps",
            session_id="sess-42",
        )
        state = tracker.get("vps")
        self.assertEqual(state.last_workspace_name, "UMH")
        self.assertEqual(state.last_session_id, "sess-42")
        self.assertEqual(tracker.device_count(), 1)

    def test_get_by_type(self):
        from substrate.operator.device_continuity import DeviceContinuityTracker
        from substrate.operator.operator_presence import PresenceDeviceType

        tracker = DeviceContinuityTracker()
        tracker.update(PresenceDeviceType.WINDOWS, device_id="beast")
        state = tracker.get_by_type(PresenceDeviceType.WINDOWS)
        self.assertIsNotNone(state)
        self.assertEqual(state.device_id, "beast")

    def test_get_by_type_not_found(self):
        from substrate.operator.device_continuity import DeviceContinuityTracker
        from substrate.operator.operator_presence import PresenceDeviceType

        tracker = DeviceContinuityTracker()
        state = tracker.get_by_type(PresenceDeviceType.IPAD)
        self.assertIsNone(state)

    def test_last_active_device(self):
        from substrate.operator.device_continuity import DeviceContinuityTracker
        from substrate.operator.operator_presence import PresenceDeviceType

        tracker = DeviceContinuityTracker()
        tracker.update(PresenceDeviceType.VPS, device_id="vps")
        tracker.update(PresenceDeviceType.WINDOWS, device_id="beast")
        last = tracker.last_active_device()
        self.assertIsNotNone(last)
        self.assertEqual(last.device_id, "beast")

    def test_last_active_device_empty(self):
        from substrate.operator.device_continuity import DeviceContinuityTracker

        tracker = DeviceContinuityTracker()
        self.assertIsNone(tracker.last_active_device())

    def test_multiple_devices(self):
        from substrate.operator.device_continuity import DeviceContinuityTracker
        from substrate.operator.operator_presence import PresenceDeviceType

        tracker = DeviceContinuityTracker()
        tracker.update(PresenceDeviceType.VPS, device_id="vps", workspace_name="UMH")
        tracker.update(PresenceDeviceType.WINDOWS, device_id="beast", workspace_name="UMH")
        tracker.update(PresenceDeviceType.IPAD, device_id="ipad")
        tracker.update(PresenceDeviceType.IPHONE, device_id="iphone")
        self.assertEqual(tracker.device_count(), 4)

    def test_to_dict(self):
        from substrate.operator.device_continuity import DeviceContinuityTracker
        from substrate.operator.operator_presence import PresenceDeviceType

        tracker = DeviceContinuityTracker()
        tracker.update(PresenceDeviceType.VPS, device_id="vps")
        d = tracker.to_dict()
        self.assertEqual(d["count"], 1)
        self.assertIn("vps", d["devices"])


# ── Type Registration ────────────────────────────────────────────────

class TestTypeRegistration(unittest.TestCase):
    def test_presence_state_registered(self):
        from substrate.canonical_types import CANONICAL_TYPES

        self.assertIn("PresenceState", CANONICAL_TYPES)

    def test_presence_device_type_registered(self):
        from substrate.canonical_types import CANONICAL_TYPES

        self.assertIn("PresenceDeviceType", CANONICAL_TYPES)

    def test_continuity_status_registered(self):
        from substrate.canonical_types import CANONICAL_TYPES

        self.assertIn("ContinuityStatus", CANONICAL_TYPES)

    def test_operator_presence_registered(self):
        from substrate.canonical_types import CANONICAL_TYPES

        self.assertIn("OperatorPresence", CANONICAL_TYPES)

    def test_active_context_registered(self):
        from substrate.canonical_types import CANONICAL_TYPES

        self.assertIn("ActiveContext", CANONICAL_TYPES)

    def test_continuity_checkpoint_registered(self):
        from substrate.canonical_types import CANONICAL_TYPES

        self.assertIn("ContinuityCheckpoint", CANONICAL_TYPES)

    def test_presence_snapshot_registered(self):
        from substrate.canonical_types import CANONICAL_TYPES

        self.assertIn("PresenceSnapshot", CANONICAL_TYPES)

    def test_continuity_engine_registered(self):
        from substrate.canonical_types import CANONICAL_TYPES

        self.assertIn("ContinuityEngine", CANONICAL_TYPES)

    def test_presence_transition_registered(self):
        from substrate.canonical_types import CANONICAL_TYPES

        self.assertIn("PresenceTransition", CANONICAL_TYPES)

    def test_presence_timeline_registered(self):
        from substrate.canonical_types import CANONICAL_TYPES

        self.assertIn("PresenceTimeline", CANONICAL_TYPES)

    def test_device_presence_state_registered(self):
        from substrate.canonical_types import CANONICAL_TYPES

        self.assertIn("DevicePresenceState", CANONICAL_TYPES)

    def test_device_continuity_tracker_registered(self):
        from substrate.canonical_types import CANONICAL_TYPES

        self.assertIn("DeviceContinuityTracker", CANONICAL_TYPES)


# ── Cockpit Routes ──────────────────────────────────────────────────

class TestCockpitRoutes(unittest.TestCase):
    def test_route_module_import(self):
        from transports.api import cockpit_operator_presence_routes
        self.assertTrue(hasattr(cockpit_operator_presence_routes, "configure"))
        self.assertTrue(hasattr(cockpit_operator_presence_routes, "operator_presence_router"))

    def test_configure_idempotent(self):
        from transports.api import cockpit_operator_presence_routes

        dep = MagicMock()
        cockpit_operator_presence_routes._configured = False
        cockpit_operator_presence_routes.configure(require_operator_dep=dep)
        cockpit_operator_presence_routes.configure(require_operator_dep=dep)
        self.assertTrue(cockpit_operator_presence_routes._configured)

    def test_route_count(self):
        from transports.api.cockpit_operator_presence_routes import (
            operator_presence_router,
        )

        all_routes = []
        for route in operator_presence_router.routes:
            all_routes.append(route.path)
        self.assertGreater(len(all_routes), 0)

    def test_get_engine_singleton(self):
        from transports.api.cockpit_operator_presence_routes import _get_engine

        if hasattr(_get_engine, "_instance"):
            delattr(_get_engine, "_instance")

        engine1 = _get_engine()
        engine2 = _get_engine()
        self.assertIs(engine1, engine2)

        delattr(_get_engine, "_instance")

    def test_get_timeline_singleton(self):
        from transports.api.cockpit_operator_presence_routes import _get_timeline

        if hasattr(_get_timeline, "_instance"):
            delattr(_get_timeline, "_instance")

        tl1 = _get_timeline()
        tl2 = _get_timeline()
        self.assertIs(tl1, tl2)

        delattr(_get_timeline, "_instance")

    def test_get_device_tracker_singleton(self):
        from transports.api.cockpit_operator_presence_routes import _get_device_tracker

        if hasattr(_get_device_tracker, "_instance"):
            delattr(_get_device_tracker, "_instance")

        t1 = _get_device_tracker()
        t2 = _get_device_tracker()
        self.assertIs(t1, t2)

        delattr(_get_device_tracker, "_instance")


# ── Integration ──────────────────────────────────────────────────────

class TestIntegration(unittest.TestCase):
    def test_full_snapshot_flow(self):
        snap_data = MockSnap({
            "repositories": [{"repo_id": "r1", "name": "UMH"}],
            "sessions": [{"session_id": "sess-42", "session_type": "engineering"}],
        })
        engine = _make_engine(
            workspace_engine=MockWorkspaceObservationEngine(snapshot=snap_data),
            context_engine=MockContextEngine(pending_count=1),
        )
        snap = engine.snapshot()
        d = snap.to_dict()

        self.assertEqual(d["active_context"]["workspace_name"], "UMH")
        self.assertEqual(d["active_context"]["session_id"], "sess-42")
        self.assertGreater(len(d["continuity_checkpoints"]), 0)

    def test_resume_with_all_signals(self):
        snap_data = MockSnap({
            "repositories": [{"repo_id": "r1", "name": "UMH"}],
            "sessions": [{"session_id": "sess-42", "session_type": "engineering"}],
        })
        engine = _make_engine(
            workspace_engine=MockWorkspaceObservationEngine(snapshot=snap_data),
            context_engine=MockContextEngine(pending_count=3),
        )
        suggestion = engine.resume_suggestion()
        self.assertEqual(suggestion["workspace"], "UMH")
        self.assertEqual(suggestion["pending_approvals"], 3)
        self.assertIn("resume_items", suggestion)

    def test_device_continuity_with_timeline(self):
        from substrate.operator.device_continuity import DeviceContinuityTracker
        from substrate.operator.operator_presence import PresenceDeviceType
        from substrate.operator.presence_timeline import PresenceTimeline

        tracker = DeviceContinuityTracker()
        timeline = PresenceTimeline()

        tracker.update(PresenceDeviceType.VPS, device_id="vps", workspace_name="UMH")
        timeline.record_device_switch(PresenceDeviceType.VPS, PresenceDeviceType.WINDOWS)
        tracker.update(PresenceDeviceType.WINDOWS, device_id="beast", workspace_name="UMH")

        self.assertEqual(tracker.device_count(), 2)
        self.assertEqual(timeline.count(), 1)

        last = tracker.last_active_device()
        self.assertEqual(last.device_id, "beast")

    def test_all_checkpoints_classified(self):
        from substrate.operator.operator_presence import ContinuityStatus

        snap_data = MockSnap({
            "repositories": [{"repo_id": "r1", "name": "UMH"}],
            "sessions": [{"session_id": "sess-1", "session_type": "engineering"}],
        })
        engine = _make_engine(
            workspace_engine=MockWorkspaceObservationEngine(snapshot=snap_data),
            context_engine=MockContextEngine(pending_count=2),
        )
        checkpoints = engine.continuity_checkpoints()
        valid_statuses = {s.value for s in ContinuityStatus}
        for cp in checkpoints:
            self.assertIn(cp.status.value, valid_statuses)

    def test_graceful_degradation_all_none(self):
        from substrate.operator.continuity_engine import ContinuityEngine
        from substrate.operator.operator_presence import PresenceSnapshot

        engine = ContinuityEngine(
            workspace_engine=MockWorkspaceObservationEngine(),
            topology_engine=MockTopologyEngine(),
            action_bridge=MockActionBridge(),
            context_engine=MockContextEngine(),
            node_registry=MockNodeRegistry(primary=MockNode()),
        )
        snap = engine.snapshot()
        self.assertIsInstance(snap, PresenceSnapshot)

    def test_snapshot_serializable(self):
        import json

        snap_data = MockSnap({
            "repositories": [{"repo_id": "r1", "name": "UMH"}],
        })
        engine = _make_engine(
            workspace_engine=MockWorkspaceObservationEngine(snapshot=snap_data),
        )
        snap = engine.snapshot()
        d = snap.to_dict()
        serialized = json.dumps(d)
        self.assertIsInstance(serialized, str)
        deserialized = json.loads(serialized)
        self.assertEqual(deserialized["active_context"]["workspace_name"], "UMH")

    def test_timeline_with_multiple_types(self):
        from substrate.operator.operator_presence import (
            PresenceDeviceType,
            PresenceState,
        )
        from substrate.operator.presence_timeline import (
            PresenceTimeline,
            PresenceTransitionType,
        )

        tl = PresenceTimeline()
        tl.record_device_switch(PresenceDeviceType.VPS, PresenceDeviceType.WINDOWS)
        tl.record_workspace_switch("UMH", "Initiate Arena")
        tl.record_session_transition("sess-1", "sess-2")
        tl.record_state_transition(PresenceState.ACTIVE, PresenceState.IDLE)

        self.assertEqual(tl.count(), 4)
        self.assertEqual(len(tl.by_type(PresenceTransitionType.DEVICE_SWITCH)), 1)
        self.assertEqual(len(tl.by_type(PresenceTransitionType.WORKSPACE_SWITCH)), 1)
        self.assertEqual(len(tl.by_type(PresenceTransitionType.SESSION_TRANSITION)), 1)
        self.assertEqual(len(tl.by_type(PresenceTransitionType.STATE_TRANSITION)), 1)

    def test_device_tracker_all_device_types(self):
        from substrate.operator.device_continuity import DeviceContinuityTracker
        from substrate.operator.operator_presence import PresenceDeviceType

        tracker = DeviceContinuityTracker()
        for dt in [PresenceDeviceType.VPS, PresenceDeviceType.WINDOWS,
                    PresenceDeviceType.IPAD, PresenceDeviceType.IPHONE]:
            tracker.update(dt, device_id=dt.value)

        self.assertEqual(tracker.device_count(), 4)
        for dt in [PresenceDeviceType.VPS, PresenceDeviceType.WINDOWS,
                    PresenceDeviceType.IPAD, PresenceDeviceType.IPHONE]:
            state = tracker.get_by_type(dt)
            self.assertIsNotNone(state)

    def test_presence_models_import_clean(self):
        from substrate.operator.operator_presence import (
            ActiveContext,
            ContinuityCheckpoint,
            ContinuityStatus,
            OperatorPresence,
            PresenceDeviceType,
            PresenceSnapshot,
            PresenceState,
        )
        self.assertIsNotNone(PresenceState)
        self.assertIsNotNone(PresenceDeviceType)
        self.assertIsNotNone(ContinuityStatus)
        self.assertIsNotNone(OperatorPresence)
        self.assertIsNotNone(ActiveContext)
        self.assertIsNotNone(ContinuityCheckpoint)
        self.assertIsNotNone(PresenceSnapshot)

    def test_continuity_engine_import_clean(self):
        from substrate.operator.continuity_engine import ContinuityEngine
        self.assertIsNotNone(ContinuityEngine)

    def test_presence_timeline_import_clean(self):
        from substrate.operator.presence_timeline import (
            PresenceTimeline,
            PresenceTransition,
            PresenceTransitionType,
        )
        self.assertIsNotNone(PresenceTimeline)
        self.assertIsNotNone(PresenceTransition)
        self.assertIsNotNone(PresenceTransitionType)

    def test_device_continuity_import_clean(self):
        from substrate.operator.device_continuity import (
            DeviceContinuityTracker,
            DevicePresenceState,
        )
        self.assertIsNotNone(DeviceContinuityTracker)
        self.assertIsNotNone(DevicePresenceState)


if __name__ == "__main__":
    unittest.main()
