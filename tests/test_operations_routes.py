"""Tests for Operations API routes — Campaign 19.3."""
from __future__ import annotations

import sys
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, "/opt/OS")


# ── Execution Fabric routes ──────────────────────────────────────────


class TestExecutionFabricRoutes:
    def test_get_router_returns_router(self) -> None:
        from transports.api.cockpit_execution_fabric_routes import get_router
        router = get_router()
        assert router is not None
        assert router.prefix == "/execution-fabric"

    def test_route_paths(self) -> None:
        from transports.api.cockpit_execution_fabric_routes import get_router
        router = get_router()
        paths = [r.path for r in router.routes]
        assert any("snapshot" in p for p in paths)
        assert any("state" in p for p in paths)
        assert any("active" in p for p in paths)
        assert any("blocked" in p for p in paths)
        assert any("capacity" in p for p in paths)
        assert any("sessions" in p for p in paths)

    def test_snapshot_unavailable(self) -> None:
        import transports.api.cockpit_execution_fabric_routes as mod
        mod._runtime = None
        router = mod.get_router()
        for route in router.routes:
            if hasattr(route, "path") and "snapshot" in route.path:
                with patch.object(mod, "_get_runtime", return_value=None):
                    result = route.endpoint()
                    assert "error" in result


# ── Agent Workforce routes ───────────────────────────────────────────


class TestAgentWorkforceRoutes:
    def test_get_router_returns_router(self) -> None:
        from transports.api.cockpit_agent_workforce_routes import get_router
        router = get_router()
        assert router is not None
        assert router.prefix == "/agent-workforce"

    def test_route_paths(self) -> None:
        from transports.api.cockpit_agent_workforce_routes import get_router
        router = get_router()
        paths = [r.path for r in router.routes]
        assert any("snapshot" in p for p in paths)
        assert any("health" in p for p in paths)
        assert any("idle" in p for p in paths)
        assert any("overloaded" in p for p in paths)
        assert any("pending" in p for p in paths)
        assert any("gaps" in p for p in paths)


# ── Session Machine routes ───────────────────────────────────────────


class TestSessionMachineRoutes:
    def test_get_router_returns_router(self) -> None:
        from transports.api.cockpit_session_machine_routes import get_router
        router = get_router()
        assert router is not None
        assert router.prefix == "/session-machine"

    def test_route_paths(self) -> None:
        from transports.api.cockpit_session_machine_routes import get_router
        router = get_router()
        paths = [r.path for r in router.routes]
        assert any("snapshot" in p for p in paths)
        assert any("bindings" in p for p in paths)
        assert any("workspaces" in p for p in paths)
        assert any("primary" in p for p in paths)
        assert any("handoffs" in p for p in paths)


# ── Router mounting ──────────────────────────────────────────────────


class TestRouterMounting:
    def _cockpit_source(self) -> str:
        import os
        test_dir = os.path.dirname(os.path.abspath(__file__))
        repo_root = os.path.dirname(test_dir)
        return open(os.path.join(repo_root, "transports/api/cockpit.py")).read()

    def test_cockpit_py_has_fabric_mount(self) -> None:
        assert "_mount_execution_fabric_router" in self._cockpit_source()

    def test_cockpit_py_has_workforce_mount(self) -> None:
        assert "_mount_agent_workforce_router" in self._cockpit_source()

    def test_cockpit_py_has_session_machine_mount(self) -> None:
        assert "_mount_session_machine_router" in self._cockpit_source()
