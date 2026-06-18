"""Tests for Campaign 17.1 — MetaIdeContextRuntime.

Read-only context binding for Meta IDE surface.
"""
from __future__ import annotations

import sys

sys.path.insert(0, "/opt/OS")

from typing import Any
from unittest.mock import MagicMock

from substrate.workstation.meta_ide_context_runtime import (
    MetaIdeContextRuntime,
    MetaIdeContextSnapshot,
)


# ── Shared fakes ─────────────────────────────────────────────────────


class _FakeContextResolution:
    def __init__(self, resolved: dict[str, Any] | None = None) -> None:
        self._resolved = resolved or {"project_name": "UMH"}

    def resolve(self, text: str) -> MagicMock:
        m = MagicMock()
        result = dict(self._resolved)
        result["query"] = text
        m.to_dict.return_value = result
        return m


class _FakeWorkspaceAwareness:
    def __init__(self, workspace: dict[str, Any] | None = None) -> None:
        self._workspace = workspace or {"repo": "OS", "branch": "main", "directory": "/opt/OS"}

    def snapshot(self) -> dict[str, Any]:
        return self._workspace


class _FakeDeviceAwareness:
    def __init__(self, device: str = "srv1500858") -> None:
        self._device = device

    def detect_active_device(self) -> str:
        return self._device


class _FakeMetaIdeLoop:
    def __init__(self, requests: list[dict] | None = None) -> None:
        self._requests = requests or []

    def active_requests(self) -> list[dict]:
        return self._requests


class _FakeOrchestratorAwareness:
    def __init__(self, ctx: dict[str, Any] | None = None) -> None:
        self._ctx = ctx or {
            "active_repo": "OS",
            "active_directory": "/opt/OS",
            "active_projection": "eos",
            "active_files": ["cockpit.py", "types.py"],
            "documents": [{"id": "doc-1"}],
            "decisions": [{"id": "dec-1"}],
        }

    def context(self) -> MagicMock:
        m = MagicMock()
        m.to_dict.return_value = self._ctx
        return m


# ── Factory ──────────────────────────────────────────────────────────


def _mic(**overrides: Any) -> MetaIdeContextRuntime:
    defaults: dict[str, Any] = {
        "context_resolution": _FakeContextResolution(),
        "workspace_awareness": _FakeWorkspaceAwareness(),
        "device_awareness": _FakeDeviceAwareness(),
        "meta_ide_loop": _FakeMetaIdeLoop(),
        "orchestrator_awareness": _FakeOrchestratorAwareness(),
    }
    defaults.update(overrides)
    return MetaIdeContextRuntime(**defaults)


# ── Context tests ────────────────────────────────────────────────────


class TestMetaIdeContext:
    def test_context_returns_snapshot(self) -> None:
        rt = _mic()
        ctx = rt.context()
        assert isinstance(ctx, MetaIdeContextSnapshot)
        d = ctx.to_dict()
        expected = {
            "device", "repo", "branch", "directory", "active_files",
            "projection", "build_target", "related_docs", "related_decisions",
            "related_goals", "active_requests", "constraints", "generated_at",
        }
        assert expected.issubset(set(d.keys()))

    def test_context_pulls_from_workspace(self) -> None:
        rt = _mic(workspace_awareness=_FakeWorkspaceAwareness({
            "repo": "trinity", "branch": "feat/auth", "directory": "/opt/trinity"
        }))
        ctx = rt.context()
        assert ctx.branch == "feat/auth"

    def test_context_pulls_device(self) -> None:
        rt = _mic(device_awareness=_FakeDeviceAwareness("desktop-lvguiq9"))
        ctx = rt.context()
        assert ctx.device == "desktop-lvguiq9"

    def test_context_pulls_projection_from_orchestrator(self) -> None:
        rt = _mic()
        ctx = rt.context()
        assert ctx.projection == "eos"

    def test_context_pulls_docs_from_orchestrator(self) -> None:
        rt = _mic()
        ctx = rt.context()
        assert len(ctx.related_docs) == 1
        assert ctx.related_docs[0]["id"] == "doc-1"


# ── Active files tests ───────────────────────────────────────────────


class TestActiveFiles:
    def test_active_files_returns_list(self) -> None:
        rt = _mic()
        files = rt.active_files()
        assert isinstance(files, list)
        assert "cockpit.py" in files

    def test_active_files_returns_list_always(self) -> None:
        rt = _mic(orchestrator_awareness=_FakeOrchestratorAwareness({}))
        files = rt.active_files()
        assert isinstance(files, list)


# ── Resolve intent tests ─────────────────────────────────────────────


class TestResolveIntent:
    def test_resolve_intent_delegates(self) -> None:
        rt = _mic(context_resolution=_FakeContextResolution({"project_name": "CreatorOS"}))
        result = rt.resolve_intent("Use Clerk for auth")
        assert result["project_name"] == "CreatorOS"
        assert "meta_ide_workspace" in result
        assert "active_requests" in result

    def test_resolve_intent_includes_workspace(self) -> None:
        rt = _mic(workspace_awareness=_FakeWorkspaceAwareness({"repo": "trinity"}))
        result = rt.resolve_intent("test")
        assert result["meta_ide_workspace"]["repo"] == "trinity"


# ── Snapshot / Summary tests ─────────────────────────────────────────


class TestMetaIdeSnapshot:
    def test_snapshot_aliases_context(self) -> None:
        rt = _mic()
        snap = rt.snapshot()
        ctx = rt.context()
        assert snap.device == ctx.device
        assert snap.repo == ctx.repo

    def test_summary_returns_dict(self) -> None:
        rt = _mic()
        s = rt.summary()
        assert isinstance(s, dict)
        assert "device" in s
        assert "repo" in s
        assert s["active_file_count"] == 2

    def test_active_requests_propagated(self) -> None:
        rt = _mic(meta_ide_loop=_FakeMetaIdeLoop([
            {"request_id": "r-1", "status": "pending"},
            {"request_id": "r-2", "status": "approved"},
        ]))
        ctx = rt.context()
        assert len(ctx.active_requests) == 2
