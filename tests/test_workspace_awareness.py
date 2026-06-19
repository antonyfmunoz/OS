"""Tests for Workspace Awareness Runtime — Campaign 5.1."""

from __future__ import annotations

import json
import os
import sys
import time
from dataclasses import dataclass
from typing import Any
from unittest.mock import patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from substrate.organism.reality_graph import (
    RealityEntity,
    RealityEntityStatus,
    RealityEntityType,
    RealityGraph,
    RealityRelation,
    RealityRelationType,
)
from substrate.organism.workspace_awareness import (
    WorkspaceAwarenessRuntime,
    WorkspaceSnapshot,
)


# ── Mock Runtime State ────────────────────────────────────────────────────


@dataclass(frozen=True)
class MockGitRepoInfo:
    repository: str
    current_branch: str
    dirty: bool
    untracked_count: int = 0
    last_commit_hash: str = "abc123"
    last_commit_message: str = "test"


@dataclass(frozen=True)
class MockWorktreeInfo:
    worktree_id: str
    path: str
    branch: str
    is_bare: bool = False
    executor_owner: str = ""


@dataclass
class MockRuntimeSnapshot:
    snapshot_id: str = "snap-1"
    timestamp: float = 0.0
    repositories: tuple = ()
    worktrees: tuple = ()
    processes: tuple = ()
    containers: tuple = ()
    executions: tuple = ()


class MockRuntimeStateRegistry:
    def __init__(self, snap: MockRuntimeSnapshot | None = None):
        self._snap = snap

    def snapshot(self) -> MockRuntimeSnapshot | None:
        return self._snap


# ── Fixtures ──────────────────────────────────────────────────────────────


@pytest.fixture
def seeded_graph(tmp_path):
    devices = [
        {"id": "vps", "display_name": "srv1500858 (VPS)", "tailscale_name": "srv1500858", "role": "orchestrator"},
        {"id": "beast", "display_name": "desktop-lvguiq9 (PC)", "tailscale_name": "desktop-lvguiq9", "role": "executor"},
    ]
    workspaces = [
        {
            "workspace_id": "umh",
            "name": "UMH",
            "workspace_type": "core",
            "repositories": [{"repository_id": "umh-os", "name": "OS", "path": "", "branch": "main"}],
            "device_ids": ["vps", "beast"],
        },
        {
            "workspace_id": "creatoros",
            "name": "CreatorOS",
            "workspace_type": "product",
            "repositories": [{"repository_id": "creatoros-app", "name": "CreatorOS", "path": "", "branch": "main"}],
            "device_ids": ["beast"],
        },
    ]
    projects = [
        {
            "project_id": "umh",
            "name": "UMH",
            "projection": "",
            "repositories": ["umh-os"],
            "infrastructure": [],
            "owner_device_ids": ["vps", "beast"],
            "status": "active",
        },
        {
            "project_id": "creatoros",
            "name": "CreatorOS",
            "projection": "creatoros",
            "repositories": ["creatoros-app"],
            "infrastructure": [],
            "owner_device_ids": ["beast"],
            "status": "active",
        },
    ]
    dp = tmp_path / "device_registry.json"
    wp = tmp_path / "workspace_registry.json"
    pp = tmp_path / "project_registry.json"
    dp.write_text(json.dumps(devices))
    wp.write_text(json.dumps(workspaces))
    pp.write_text(json.dumps(projects))
    return RealityGraph.seed_from_registries(str(dp), str(wp), str(pp))


@pytest.fixture
def mock_runtime_state():
    snap = MockRuntimeSnapshot(
        repositories=(
            MockGitRepoInfo(repository="OS", current_branch="main", dirty=True),
        ),
        worktrees=(
            MockWorktreeInfo(worktree_id="wt-1", path="/opt/OS", branch="main"),
            MockWorktreeInfo(
                worktree_id="wt-2",
                path="/opt/OS/.claude/worktrees/c5-test",
                branch="worktree-c5-test",
            ),
        ),
    )
    return MockRuntimeStateRegistry(snap)


# ── WorkspaceSnapshot Tests ───────────────────────────────────────────────


class TestWorkspaceSnapshot:
    def test_defaults(self):
        snap = WorkspaceSnapshot()
        assert snap.device == ""
        assert snap.workspace == ""
        assert snap.repo == ""
        assert snap.dirty is False

    def test_to_dict(self):
        snap = WorkspaceSnapshot(device="vps", repo="OS", branch="main", detected_at=100.0)
        d = snap.to_dict()
        assert d["device"] == "vps"
        assert d["repo"] == "OS"
        assert d["branch"] == "main"
        assert d["detected_at"] == 100.0

    def test_to_dict_has_all_fields(self):
        snap = WorkspaceSnapshot()
        d = snap.to_dict()
        expected = {"device", "workspace", "project", "projection", "repo", "branch", "directory", "active_files", "dirty", "detected_at"}
        assert set(d.keys()) == expected


# ── Device Detection Tests ────────────────────────────────────────────────


class TestDeviceDetection:
    def test_detect_from_env_var(self, seeded_graph):
        runtime = WorkspaceAwarenessRuntime(reality_graph=seeded_graph)
        with patch.dict(os.environ, {"UMH_DEVICE_ID": "beast"}):
            snap = runtime.detect_active_workspace()
            assert snap.device == "beast"

    def test_detect_from_hostname_match(self, seeded_graph):
        runtime = WorkspaceAwarenessRuntime(reality_graph=seeded_graph)
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("UMH_DEVICE_ID", None)
            with patch("platform.node", return_value="srv1500858"):
                snap = runtime.detect_active_workspace()
                assert snap.device == "vps"

    def test_detect_hostname_no_match_returns_hostname(self):
        runtime = WorkspaceAwarenessRuntime(reality_graph=None)
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("UMH_DEVICE_ID", None)
            with patch("platform.node", return_value="my-laptop"):
                snap = runtime.detect_active_workspace()
                assert snap.device == "my-laptop"

    def test_detect_empty_hostname(self):
        runtime = WorkspaceAwarenessRuntime(reality_graph=None)
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("UMH_DEVICE_ID", None)
            with patch("platform.node", return_value=""):
                snap = runtime.detect_active_workspace()
                assert snap.device == ""

    def test_env_var_takes_precedence(self, seeded_graph):
        runtime = WorkspaceAwarenessRuntime(reality_graph=seeded_graph)
        with patch.dict(os.environ, {"UMH_DEVICE_ID": "override"}):
            with patch("platform.node", return_value="srv1500858"):
                snap = runtime.detect_active_workspace()
                assert snap.device == "override"


# ── Runtime State Detection Tests ─────────────────────────────────────────


class TestDetectActiveWorkspace:
    def test_detect_repo_from_runtime(self, seeded_graph, mock_runtime_state):
        runtime = WorkspaceAwarenessRuntime(
            reality_graph=seeded_graph,
            runtime_state=mock_runtime_state,
        )
        with patch.dict(os.environ, {"UMH_DEVICE_ID": "vps"}):
            snap = runtime.detect_active_workspace()
            assert snap.repo == "OS"
            assert snap.branch == "main"
            assert snap.dirty is True

    def test_detect_worktree_path(self, seeded_graph, mock_runtime_state):
        runtime = WorkspaceAwarenessRuntime(
            reality_graph=seeded_graph,
            runtime_state=mock_runtime_state,
        )
        with patch.dict(os.environ, {"UMH_DEVICE_ID": "vps"}):
            snap = runtime.detect_active_workspace()
            assert snap.directory != ""

    def test_no_runtime_state_uses_cwd(self, seeded_graph):
        runtime = WorkspaceAwarenessRuntime(reality_graph=seeded_graph, runtime_state=None)
        with patch.dict(os.environ, {"UMH_DEVICE_ID": "vps"}):
            snap = runtime.detect_active_workspace()
            assert snap.directory == os.getcwd()

    def test_runtime_state_no_snapshot(self, seeded_graph):
        empty_state = MockRuntimeStateRegistry(snap=None)
        runtime = WorkspaceAwarenessRuntime(
            reality_graph=seeded_graph,
            runtime_state=empty_state,
        )
        with patch.dict(os.environ, {"UMH_DEVICE_ID": "vps"}):
            snap = runtime.detect_active_workspace()
            assert snap.directory == os.getcwd()

    def test_multiple_repos_picks_cwd_match(self, seeded_graph):
        multi_snap = MockRuntimeSnapshot(
            repositories=(
                MockGitRepoInfo(repository="creatoros-app", current_branch="feat-1", dirty=False),
                MockGitRepoInfo(repository="OS", current_branch="main", dirty=True),
            ),
            worktrees=(),
        )
        state = MockRuntimeStateRegistry(multi_snap)
        runtime = WorkspaceAwarenessRuntime(
            reality_graph=seeded_graph,
            runtime_state=state,
        )
        with patch.dict(os.environ, {"UMH_DEVICE_ID": "vps"}):
            snap = runtime.detect_active_workspace()
            assert snap.repo in ("creatoros-app", "OS")

    def test_detected_at_is_set(self, seeded_graph):
        runtime = WorkspaceAwarenessRuntime(reality_graph=seeded_graph)
        before = time.time()
        with patch.dict(os.environ, {"UMH_DEVICE_ID": "vps"}):
            snap = runtime.detect_active_workspace()
        assert snap.detected_at >= before


# ── Graph Resolution Tests ────────────────────────────────────────────────


class TestGraphResolution:
    def test_repo_resolves_to_workspace(self, seeded_graph, mock_runtime_state):
        runtime = WorkspaceAwarenessRuntime(
            reality_graph=seeded_graph,
            runtime_state=mock_runtime_state,
        )
        with patch.dict(os.environ, {"UMH_DEVICE_ID": "vps"}):
            snap = runtime.detect_active_workspace()
            assert snap.workspace in ("umh", "UMH", "")

    def test_repo_resolves_to_project(self, seeded_graph, mock_runtime_state):
        runtime = WorkspaceAwarenessRuntime(
            reality_graph=seeded_graph,
            runtime_state=mock_runtime_state,
        )
        with patch.dict(os.environ, {"UMH_DEVICE_ID": "vps"}):
            snap = runtime.detect_active_workspace()
            assert snap.project in ("umh", "UMH", "")

    def test_no_graph_still_works(self, mock_runtime_state):
        runtime = WorkspaceAwarenessRuntime(
            reality_graph=None,
            runtime_state=mock_runtime_state,
        )
        with patch.dict(os.environ, {"UMH_DEVICE_ID": "vps"}):
            snap = runtime.detect_active_workspace()
            assert snap.repo == "OS"
            assert snap.workspace == ""
            assert snap.project == ""


# ── Populate Context Tests ────────────────────────────────────────────────


class TestPopulateContext:
    def test_populates_orchestrator_context(self, seeded_graph, mock_runtime_state):
        from substrate.organism.orchestrator_awareness_runtime import OrchestratorContext
        ctx = OrchestratorContext()
        runtime = WorkspaceAwarenessRuntime(
            reality_graph=seeded_graph,
            runtime_state=mock_runtime_state,
        )
        with patch.dict(os.environ, {"UMH_DEVICE_ID": "vps"}):
            runtime.populate_context(ctx)
        assert ctx.active_device == "vps"
        assert ctx.active_repo == "OS"

    def test_populates_directory(self, seeded_graph, mock_runtime_state):
        from substrate.organism.orchestrator_awareness_runtime import OrchestratorContext
        ctx = OrchestratorContext()
        runtime = WorkspaceAwarenessRuntime(
            reality_graph=seeded_graph,
            runtime_state=mock_runtime_state,
        )
        with patch.dict(os.environ, {"UMH_DEVICE_ID": "vps"}):
            runtime.populate_context(ctx)
        assert ctx.active_directory != ""

    def test_populates_plain_dict_ctx(self, seeded_graph, mock_runtime_state):
        class PlainCtx:
            active_device: str = ""
            active_repo: str = ""
            active_directory: str = ""
            active_files: list = []
            active_projection: str = ""
            active_project: str = ""

        ctx = PlainCtx()
        runtime = WorkspaceAwarenessRuntime(
            reality_graph=seeded_graph,
            runtime_state=mock_runtime_state,
        )
        with patch.dict(os.environ, {"UMH_DEVICE_ID": "vps"}):
            runtime.populate_context(ctx)
        assert ctx.active_device == "vps"

    def test_does_not_overwrite_empty(self, seeded_graph):
        from substrate.organism.orchestrator_awareness_runtime import OrchestratorContext
        ctx = OrchestratorContext(active_projection="already-set")
        runtime = WorkspaceAwarenessRuntime(
            reality_graph=seeded_graph,
            runtime_state=None,
        )
        with patch.dict(os.environ, {"UMH_DEVICE_ID": "vps"}):
            runtime.populate_context(ctx)
        assert ctx.active_device == "vps"


# ── Snapshot API Tests ────────────────────────────────────────────────────


class TestSnapshotAPI:
    def test_snapshot_returns_dict(self, seeded_graph, mock_runtime_state):
        runtime = WorkspaceAwarenessRuntime(
            reality_graph=seeded_graph,
            runtime_state=mock_runtime_state,
        )
        with patch.dict(os.environ, {"UMH_DEVICE_ID": "vps"}):
            d = runtime.snapshot()
        assert isinstance(d, dict)
        assert "device" in d
        assert "repo" in d
        assert "detected_at" in d

    def test_snapshot_caches(self, seeded_graph, mock_runtime_state):
        runtime = WorkspaceAwarenessRuntime(
            reality_graph=seeded_graph,
            runtime_state=mock_runtime_state,
        )
        with patch.dict(os.environ, {"UMH_DEVICE_ID": "vps"}):
            d1 = runtime.snapshot()
            d2 = runtime.snapshot()
        assert d1["detected_at"] == d2["detected_at"]


# ── Fallback Tests ────────────────────────────────────────────────────────


class TestFallbacks:
    def test_no_graph_no_state(self):
        runtime = WorkspaceAwarenessRuntime(reality_graph=None, runtime_state=None)
        with patch.dict(os.environ, {"UMH_DEVICE_ID": "test-dev"}):
            snap = runtime.detect_active_workspace()
        assert snap.device == "test-dev"
        assert snap.directory == os.getcwd()
        assert snap.repo == ""

    def test_graph_only(self, seeded_graph):
        runtime = WorkspaceAwarenessRuntime(reality_graph=seeded_graph, runtime_state=None)
        with patch.dict(os.environ, {"UMH_DEVICE_ID": "vps"}):
            snap = runtime.detect_active_workspace()
        assert snap.device == "vps"
        assert snap.directory == os.getcwd()

    def test_state_only(self, mock_runtime_state):
        runtime = WorkspaceAwarenessRuntime(reality_graph=None, runtime_state=mock_runtime_state)
        with patch.dict(os.environ, {"UMH_DEVICE_ID": "vps"}):
            snap = runtime.detect_active_workspace()
        assert snap.repo == "OS"
        assert snap.workspace == ""
