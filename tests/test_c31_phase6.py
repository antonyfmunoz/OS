"""C31 Phase 6 — Daily Driver Operationalization tests.

Tests:
  1. DevSessionTracker start/record/complete/abandon flow
  2. DevSessionTracker produces correct ActionEnvelopes
  3. GitHubOperations envelope construction
  4. Projection registration in daemon (UMH + 3 projections)
  5. Daemon wiring (dev_session_tracker property, status includes dev_sessions)
  6. Production manifests include github_operations
  7. Cockpit spine router has new endpoints
"""

from __future__ import annotations

import json
import os
import sys
import tempfile

sys.path.insert(0, "/opt/OS")

import pytest

from substrate.organism.dev_session_tracker import (
    DevSession,
    DevSessionTracker,
    SessionStatus,
)
from substrate.organism.action_envelope import ActionType, BlastRadius


# ── DevSessionTracker ────────────────────────────────────────────────────────


class TestDevSessionTracker:
    def setup_method(self) -> None:
        self._tmpdir = tempfile.mkdtemp()
        self.tracker = DevSessionTracker(store_dir=self._tmpdir)

    def test_start_session(self) -> None:
        s = self.tracker.start_session("implement feature X", "eos")
        assert s.status == SessionStatus.ACTIVE
        assert s.intent == "implement feature X"
        assert s.projection_id == "eos"
        assert s.session_id.startswith("ds-")
        assert len(self.tracker.active_sessions()) == 1

    def test_record_commit(self) -> None:
        s = self.tracker.start_session("fix bug")
        assert self.tracker.record_commit(s.session_id, "abc123", "fix: the bug")
        assert len(s.commits) == 1
        assert s.commits[0]["sha"] == "abc123"

    def test_record_files_modified(self) -> None:
        s = self.tracker.start_session("refactor")
        assert self.tracker.record_files_modified(s.session_id, 5)
        assert s.files_modified == 5

    def test_complete_session_produces_envelope(self) -> None:
        s = self.tracker.start_session("add endpoint", "umh")
        self.tracker.record_commit(s.session_id, "def456", "add endpoint")
        self.tracker.record_files_modified(s.session_id, 3)

        envelope = self.tracker.complete_session(s.session_id, "endpoint added")
        assert envelope is not None
        assert envelope.action_type == ActionType.STATE
        assert envelope.source == "dev_session_tracker"
        assert envelope.risk_level == "low"
        assert envelope.blast_radius == BlastRadius.LOCAL_RUNTIME
        assert envelope.metadata["session_id"] == s.session_id
        assert envelope.metadata["projection_id"] == "umh"
        assert envelope.metadata["files_modified"] == 3
        assert len(envelope.metadata["commits"]) == 1

        output, success = envelope.execute_fn()
        assert success is True
        assert "1 commits" in output
        assert "3 files" in output

    def test_complete_session_marks_completed(self) -> None:
        s = self.tracker.start_session("test")
        self.tracker.complete_session(s.session_id, "done")
        assert s.status == SessionStatus.COMPLETED
        assert s.completed_at > 0
        assert len(self.tracker.active_sessions()) == 0

    def test_abandon_session(self) -> None:
        s = self.tracker.start_session("test")
        assert self.tracker.abandon_session(s.session_id)
        assert s.status == SessionStatus.ABANDONED
        assert len(self.tracker.active_sessions()) == 0

    def test_recent_sessions(self) -> None:
        for i in range(5):
            self.tracker.start_session(f"session {i}")
        recent = self.tracker.recent_sessions(limit=3)
        assert len(recent) == 3

    def test_summary(self) -> None:
        s1 = self.tracker.start_session("a")
        s2 = self.tracker.start_session("b")
        self.tracker.complete_session(s1.session_id, "done")
        summary = self.tracker.summary()
        assert summary["active_count"] == 1
        assert summary["completed_count"] == 1
        assert summary["total_count"] == 2

    def test_to_dict(self) -> None:
        self.tracker.start_session("x")
        d = self.tracker.to_dict()
        assert "active_sessions" in d
        assert "recent_sessions" in d
        assert d["active_count"] == 1

    def test_persistence_roundtrip(self) -> None:
        s = self.tracker.start_session("persist test")
        self.tracker.record_commit(s.session_id, "aaa", "msg")
        tracker2 = DevSessionTracker(store_dir=self._tmpdir)
        assert len(tracker2.active_sessions()) == 1
        loaded = tracker2.active_sessions()[0]
        assert loaded.session_id == s.session_id
        assert loaded.intent == "persist test"

    def test_cannot_complete_inactive(self) -> None:
        s = self.tracker.start_session("test")
        self.tracker.complete_session(s.session_id, "done")
        result = self.tracker.complete_session(s.session_id, "again")
        assert result is None

    def test_cannot_record_on_completed(self) -> None:
        s = self.tracker.start_session("test")
        self.tracker.complete_session(s.session_id, "done")
        assert not self.tracker.record_commit(s.session_id, "x", "y")
        assert not self.tracker.record_files_modified(s.session_id, 1)


# ── GitHubOperations ─────────────────────────────────────────────────────────


class TestGitHubOperations:
    def test_create_pr_envelope(self) -> None:
        from adapters.github.github_operations import GitHubOperations

        gh = GitHubOperations(repo="test/repo")
        env = gh.create_pr_envelope("title", "body", "feature-branch")
        assert env.action_type == ActionType.STATE
        assert env.source == "github_operations"
        assert env.risk_level == "medium"
        assert env.blast_radius == BlastRadius.EXTERNAL
        assert env.constraints.require_approval is True
        assert env.metadata["repo"] == "test/repo"
        assert env.metadata["head"] == "feature-branch"

    def test_merge_pr_envelope(self) -> None:
        from adapters.github.github_operations import GitHubOperations

        gh = GitHubOperations()
        env = gh.merge_pr_envelope(42)
        assert env.action_type == ActionType.STATE
        assert env.constraints.require_approval is True
        assert env.metadata["pr_number"] == 42

    def test_create_branch_envelope(self) -> None:
        from adapters.github.github_operations import GitHubOperations

        gh = GitHubOperations()
        env = gh.create_branch_envelope("feature/new", "main")
        assert env.action_type == ActionType.FILESYSTEM
        assert env.risk_level == "low"
        assert env.blast_radius == BlastRadius.LOCAL_RUNTIME
        assert env.constraints.require_approval is False

    def test_to_dict(self) -> None:
        from adapters.github.github_operations import GitHubOperations

        gh = GitHubOperations()
        d = gh.to_dict()
        assert d["operations_count"] == 0
        assert d["last_pr"] is None


# ── Production manifests ─────────────────────────────────────────────────────


def test_github_manifest_in_production():
    from adapters.adapter_engine.production_manifests import (
        ALL_PRODUCTION_MANIFESTS,
        populate_production_registry,
    )

    ids = [m.adapter_id for m in ALL_PRODUCTION_MANIFESTS]
    assert "github_operations" in ids

    registry = populate_production_registry()
    assert "github_operations" in registry.adapters
    gh_desc = registry.adapters["github_operations"]
    assert len(gh_desc.capabilities) == 3


# ── Projection registration ─────────────────────────────────────────────────


def test_projection_port_registers_umh():
    from substrate.sockets.projection_port import ProjectionPort, ProjectionRegistration

    port = ProjectionPort.__new__(ProjectionPort)
    port._lock = __import__("threading").Lock()
    port._registrations = {}
    port._path = "/dev/null"

    port.register(
        ProjectionRegistration(
            projection_id="umh",
            name="Universal Meta Harness",
            capabilities_consumed=["governance", "execution"],
        )
    )
    assert port.get("umh") is not None
    assert port.get("umh").name == "Universal Meta Harness"

    summary = port.summary()
    assert summary["total_registrations"] == 1


# ── Cockpit endpoint count ───────────────────────────────────────────────────


def test_cockpit_spine_router_endpoint_count():
    import re

    router_path = os.path.join(
        os.path.dirname(__file__), "..", "transports", "api", "cockpit_spine_router.py"
    )
    with open(router_path, "r") as f:
        content = f.read()

    count = len(re.findall(r"add_api_route\(", content))
    assert count >= 37, f"Expected at least 37 endpoints, got {count}"


# ── Daemon wiring ────────────────────────────────────────────────────────────


def test_daemon_has_dev_session_tracker():
    daemon_path = os.path.join(
        os.path.dirname(__file__), "..", "substrate", "organism", "daemon.py"
    )
    with open(daemon_path, "r") as f:
        content = f.read()

    assert "DevSessionTracker" in content
    assert "dev_session_tracker" in content
    assert "substrate_projection_port" in content
    assert '"dev_sessions"' in content
