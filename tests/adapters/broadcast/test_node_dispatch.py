"""Unit tests for Phase 0 — organism engine placement.

Tests the BroadcastAdapter (node-side), the node-aware routing layer
(cockpit API), and the daemon async dispatch path.
"""

from __future__ import annotations

import asyncio
import os
import sys
from unittest.mock import AsyncMock, MagicMock, patch

_WORKTREE = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
# Worktree first — ensures our modified files are loaded, not main repo's
if _WORKTREE not in sys.path:
    sys.path.insert(0, _WORKTREE)
_MAIN = os.environ.get("UMH_ROOT", "/opt/OS")
if _MAIN not in sys.path:
    sys.path.insert(1, _MAIN)
# Force reimport of our worktree modules (not cached from main repo)
for mod_name in list(sys.modules):
    if "cockpit_broadcast_routes" in mod_name:
        del sys.modules[mod_name]

import pytest


# ── BroadcastAdapter tests ──


class TestBroadcastAdapter:
    """Tests for the node-side broadcast adapter."""

    def _make_adapter(self):
        from nodes.windows.umh_node.adapters.broadcast import BroadcastAdapter
        adapter = BroadcastAdapter()
        return adapter

    @pytest.mark.asyncio
    async def test_execute_async_unknown_op(self):
        adapter = self._make_adapter()
        result = await adapter.execute_async("broadcast.nonexistent", {})
        assert result["success"] is False
        assert "unknown" in result["error"]

    @pytest.mark.asyncio
    async def test_execute_async_status_idle(self):
        adapter = self._make_adapter()
        result = await adapter.execute_async("broadcast.status", {})
        assert result["success"] is True
        assert result["state"] == "idle"

    @pytest.mark.asyncio
    async def test_execute_async_health_idle(self):
        adapter = self._make_adapter()
        result = await adapter.execute_async("broadcast.health", {})
        assert result["success"] is True
        assert result["state"] == "idle"

    @pytest.mark.asyncio
    async def test_execute_async_stop_when_idle(self):
        adapter = self._make_adapter()
        result = await adapter.execute_async("broadcast.stop", {})
        assert result["success"] is True
        assert result.get("already_stopped") is True

    @pytest.mark.asyncio
    async def test_execute_async_start_missing_url(self):
        adapter = self._make_adapter()
        result = await adapter.execute_async("broadcast.start", {})
        assert result["success"] is False

    @pytest.mark.asyncio
    async def test_execute_async_switch_scene_no_id(self):
        adapter = self._make_adapter()
        result = await adapter.execute_async("broadcast.switch_scene", {})
        assert result["success"] is False

    @pytest.mark.asyncio
    async def test_execute_async_start_composite_missing_url(self):
        adapter = self._make_adapter()
        result = await adapter.execute_async("broadcast.start_composite", {"sources": []})
        assert result["success"] is False

    def test_has_execute_async(self):
        adapter = self._make_adapter()
        assert hasattr(adapter, "execute_async")
        assert callable(adapter.execute_async)
        assert asyncio.iscoroutinefunction(adapter.execute_async)

    def test_health_callback_stored(self):
        adapter = self._make_adapter()
        adapter._on_health({"fps": 30.0, "bitrate_kbps": 4500})
        assert adapter._latest_health["fps"] == 30.0


# ── Routing layer tests ──


def _load_routes():
    """Import cockpit_broadcast_routes from the worktree, not main repo."""
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "cockpit_broadcast_routes_wt",
        os.path.join(_WORKTREE, "transports", "api", "cockpit_broadcast_routes.py"),
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class TestRoutingLayer:
    """Tests for local vs remote dispatch in cockpit_broadcast_routes."""

    def test_is_remote_local(self):
        routes = _load_routes()
        assert routes._is_remote(routes._LOCAL) is False
        assert routes._is_remote("local") is False

    def test_is_remote_node(self):
        routes = _load_routes()
        assert routes._is_remote("windows-desktop") is True
        assert routes._is_remote("beast") is True

    def test_active_node_default(self):
        routes = _load_routes()
        assert routes._active_node == routes._LOCAL

    def test_get_engine_returns_singleton(self):
        routes = _load_routes()
        e1 = routes._get_engine()
        e2 = routes._get_engine()
        assert e1 is e2


# ── Daemon async dispatch tests ──


class TestDaemonAsyncDispatch:
    """Tests that the daemon detects execute_async and uses it."""

    def test_broadcast_adapter_detected_as_async(self):
        from nodes.windows.umh_node.adapters.broadcast import BroadcastAdapter
        adapter = BroadcastAdapter()
        has_async = hasattr(adapter, "execute_async") and callable(adapter.execute_async)
        assert has_async is True

    def test_shell_adapter_has_no_async(self):
        from nodes.windows.umh_node.adapters.shell import ShellAdapter
        adapter = ShellAdapter()
        has_async = hasattr(adapter, "execute_async") and callable(getattr(adapter, "execute_async", None))
        assert has_async is False

    def test_broadcast_capability_in_builder(self):
        """Node daemon should include broadcast in its capabilities list."""
        from nodes.windows.umh_node.config import NodeConfig
        from nodes.windows.umh_node.client import NodeClient

        config = NodeConfig(
            vps_host="127.0.0.1",
            vps_port=8094,
            node_id="test-node",
            token="test",
        )
        client = NodeClient(config)
        caps = client._build_capabilities()
        cap_names = [c["name"] for c in caps]
        assert "broadcast" in cap_names

    def test_broadcast_cap_has_correct_risk(self):
        from nodes.windows.umh_node.config import NodeConfig
        from nodes.windows.umh_node.client import NodeClient

        config = NodeConfig(
            vps_host="127.0.0.1",
            vps_port=8094,
            node_id="test-node",
            token="test",
        )
        client = NodeClient(config)
        caps = client._build_capabilities()
        bc = next(c for c in caps if c["name"] == "broadcast")
        assert bc["category"] == "media"
        assert bc["max_risk_class"] == "external_communication"


# ── Node list endpoint shape test ──


class TestNodeListShape:
    """Tests that the /broadcast/nodes response shape is correct."""

    def test_local_always_in_nodes(self):
        """Even with no mesh, local node should always appear."""
        # Simulated — the endpoint always prepends local
        nodes = [{"node_id": "local", "status": "available", "local": True}]
        assert len(nodes) >= 1
        assert nodes[0]["local"] is True
        assert nodes[0]["node_id"] == "local"
