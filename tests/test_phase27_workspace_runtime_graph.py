"""Tests for Phase 27 — Workspace Runtime Graph.

Covers: types, models, registry, topology engine, runtime graph integration,
health computation, cockpit routes, type registration, and integration.
"""

from __future__ import annotations

import os
import sys
import unittest

sys.path.insert(0, os.environ.get("UMH_ROOT", "/opt/OS"))


class TestWorkspaceTypes(unittest.TestCase):
    """Test workspace type enums."""

    def test_workspace_type_values(self) -> None:
        from substrate.meta_ide.workspace_runtime_graph import WorkspaceType

        self.assertEqual(WorkspaceType.CORE.value, "core")
        self.assertEqual(WorkspaceType.PRODUCT.value, "product")
        self.assertEqual(WorkspaceType.SERVICE.value, "service")
        self.assertEqual(WorkspaceType.INFRASTRUCTURE.value, "infrastructure")

    def test_runtime_target_type_values(self) -> None:
        from substrate.meta_ide.workspace_runtime_graph import RuntimeTargetType

        self.assertEqual(RuntimeTargetType.ELECTRON.value, "electron")
        self.assertEqual(RuntimeTargetType.REACT.value, "react")
        self.assertEqual(RuntimeTargetType.DOCKER.value, "docker")
        self.assertEqual(RuntimeTargetType.PYTHON.value, "python")
        self.assertEqual(RuntimeTargetType.PREVIEW.value, "preview")
        self.assertEqual(RuntimeTargetType.API.value, "api")

    def test_build_target_type_values(self) -> None:
        from substrate.meta_ide.workspace_runtime_graph import BuildTargetType

        self.assertEqual(BuildTargetType.WINDOWS.value, "windows")
        self.assertEqual(BuildTargetType.LINUX.value, "linux")
        self.assertEqual(BuildTargetType.CONTAINER.value, "container")

    def test_workspace_health_values(self) -> None:
        from substrate.meta_ide.workspace_runtime_graph import WorkspaceHealth

        self.assertEqual(WorkspaceHealth.HEALTHY.value, "healthy")
        self.assertEqual(WorkspaceHealth.DEGRADED.value, "degraded")
        self.assertEqual(WorkspaceHealth.BLOCKED.value, "blocked")
        self.assertEqual(WorkspaceHealth.UNKNOWN.value, "unknown")

    def test_workspace_type_string_conversion(self) -> None:
        from substrate.meta_ide.workspace_runtime_graph import WorkspaceType

        self.assertEqual(str(WorkspaceType.CORE), "WorkspaceType.CORE")
        self.assertEqual(WorkspaceType("product"), WorkspaceType.PRODUCT)

    def test_workspace_health_string_conversion(self) -> None:
        from substrate.meta_ide.workspace_runtime_graph import WorkspaceHealth

        self.assertEqual(WorkspaceHealth("healthy"), WorkspaceHealth.HEALTHY)
        self.assertEqual(WorkspaceHealth("blocked"), WorkspaceHealth.BLOCKED)


class TestWorkspaceModels(unittest.TestCase):
    """Test workspace dataclass models."""

    def test_workspace_repository_construction(self) -> None:
        from substrate.meta_ide.workspace_runtime_graph import WorkspaceRepository

        repo = WorkspaceRepository(
            repository_id="test-repo",
            name="TestRepo",
            path="/opt/test",
            branch="main",
            workspace_id="ws-1",
        )
        self.assertEqual(repo.repository_id, "test-repo")
        self.assertEqual(repo.name, "TestRepo")
        self.assertEqual(repo.workspace_id, "ws-1")

    def test_workspace_repository_to_dict(self) -> None:
        from substrate.meta_ide.workspace_runtime_graph import WorkspaceRepository

        repo = WorkspaceRepository(repository_id="r1", name="R", path="/p")
        d = repo.to_dict()
        self.assertEqual(d["repository_id"], "r1")
        self.assertEqual(d["name"], "R")
        self.assertEqual(d["path"], "/p")

    def test_workspace_repository_from_dict(self) -> None:
        from substrate.meta_ide.workspace_runtime_graph import WorkspaceRepository

        d = {"repository_id": "r1", "name": "R", "path": "/p", "branch": "dev"}
        repo = WorkspaceRepository.from_dict(d)
        self.assertEqual(repo.repository_id, "r1")
        self.assertEqual(repo.branch, "dev")

    def test_workspace_runtime_construction(self) -> None:
        from substrate.meta_ide.workspace_runtime_graph import WorkspaceRuntime

        rt = WorkspaceRuntime(
            runtime_id="rt-1",
            workspace_id="ws-1",
            runtime_type="docker",
            host_device_id="vps",
            ports=[8080],
        )
        self.assertEqual(rt.runtime_id, "rt-1")
        self.assertEqual(rt.ports, [8080])

    def test_workspace_runtime_roundtrip(self) -> None:
        from substrate.meta_ide.workspace_runtime_graph import WorkspaceRuntime

        rt = WorkspaceRuntime(runtime_id="rt-1", ports=[80, 443])
        d = rt.to_dict()
        rt2 = WorkspaceRuntime.from_dict(d)
        self.assertEqual(rt2.runtime_id, "rt-1")
        self.assertEqual(rt2.ports, [80, 443])

    def test_workspace_build_target(self) -> None:
        from substrate.meta_ide.workspace_runtime_graph import WorkspaceBuildTarget

        bt = WorkspaceBuildTarget(target_id="bt-1", build_type="linux", preferred=True)
        self.assertTrue(bt.preferred)
        d = bt.to_dict()
        self.assertEqual(d["build_type"], "linux")

    def test_workspace_definition_roundtrip(self) -> None:
        from substrate.meta_ide.workspace_runtime_graph import (
            WorkspaceDefinition,
            WorkspaceRepository,
            WorkspaceType,
        )

        ws = WorkspaceDefinition(
            workspace_id="ws-1",
            name="Test",
            workspace_type=WorkspaceType.PRODUCT,
            repositories=[WorkspaceRepository(repository_id="r1", name="R")],
            device_ids=["vps"],
        )
        d = ws.to_dict()
        ws2 = WorkspaceDefinition.from_dict(d)
        self.assertEqual(ws2.workspace_id, "ws-1")
        self.assertEqual(ws2.workspace_type, WorkspaceType.PRODUCT)
        self.assertEqual(len(ws2.repositories), 1)

    def test_workspace_runtime_graph_roundtrip(self) -> None:
        from substrate.meta_ide.workspace_runtime_graph import (
            WorkspaceDefinition,
            WorkspaceRuntimeGraph,
        )

        graph = WorkspaceRuntimeGraph(
            workspaces=[
                WorkspaceDefinition(workspace_id="ws-1", name="WS1"),
                WorkspaceDefinition(workspace_id="ws-2", name="WS2"),
            ]
        )
        d = graph.to_dict()
        self.assertEqual(d["workspace_count"], 2)
        graph2 = WorkspaceRuntimeGraph.from_dict(d)
        self.assertEqual(len(graph2.workspaces), 2)


class TestWorkspaceRegistry(unittest.TestCase):
    """Test workspace registry with seed data."""

    def test_seed_workspace_count(self) -> None:
        from substrate.meta_ide.workspace_registry import WorkspaceRegistry

        reg = WorkspaceRegistry()
        self.assertEqual(len(reg.list_workspaces()), 4)

    def test_get_umh_workspace(self) -> None:
        from substrate.meta_ide.workspace_registry import WorkspaceRegistry

        reg = WorkspaceRegistry()
        ws = reg.get("umh")
        self.assertIsNotNone(ws)
        self.assertEqual(ws.name, "UMH")
        self.assertEqual(ws.workspace_type.value, "core")

    def test_get_product_workspaces(self) -> None:
        from substrate.meta_ide.workspace_registry import WorkspaceRegistry

        reg = WorkspaceRegistry()
        for wid in ("creatoros", "entrepreneuros", "lyfeos"):
            ws = reg.get(wid)
            self.assertIsNotNone(ws)
            self.assertEqual(ws.workspace_type.value, "product")

    def test_get_nonexistent_workspace(self) -> None:
        from substrate.meta_ide.workspace_registry import WorkspaceRegistry

        reg = WorkspaceRegistry()
        self.assertIsNone(reg.get("nonexistent"))

    def test_workspace_for_repository(self) -> None:
        from substrate.meta_ide.workspace_registry import WorkspaceRegistry

        reg = WorkspaceRegistry()
        root = os.environ.get("UMH_ROOT", "/opt/OS")
        ws = reg.workspace_for_repository(root)
        self.assertIsNotNone(ws)
        self.assertEqual(ws.workspace_id, "umh")

    def test_workspace_for_repository_not_found(self) -> None:
        from substrate.meta_ide.workspace_registry import WorkspaceRegistry

        reg = WorkspaceRegistry()
        self.assertIsNone(reg.workspace_for_repository("/nonexistent/path"))

    def test_workspace_for_device(self) -> None:
        from substrate.meta_ide.workspace_registry import WorkspaceRegistry

        reg = WorkspaceRegistry()
        beast_workspaces = reg.workspace_for_device("beast")
        names = {ws.workspace_id for ws in beast_workspaces}
        self.assertIn("creatoros", names)
        self.assertIn("entrepreneuros", names)
        self.assertIn("lyfeos", names)

    def test_register_custom_workspace(self) -> None:
        from substrate.meta_ide.workspace_registry import WorkspaceRegistry
        from substrate.meta_ide.workspace_runtime_graph import (
            WorkspaceDefinition,
            WorkspaceType,
        )

        reg = WorkspaceRegistry()
        custom = WorkspaceDefinition(
            workspace_id="custom",
            name="Custom",
            workspace_type=WorkspaceType.SERVICE,
        )
        reg.register(custom)
        self.assertEqual(len(reg.list_workspaces()), 5)
        self.assertIsNotNone(reg.get("custom"))

    def test_to_dict(self) -> None:
        from substrate.meta_ide.workspace_registry import WorkspaceRegistry

        reg = WorkspaceRegistry()
        d = reg.to_dict()
        self.assertEqual(d["workspace_count"], 4)
        self.assertIn("umh", d["workspaces"])

    def test_no_seed(self) -> None:
        from substrate.meta_ide.workspace_registry import WorkspaceRegistry

        reg = WorkspaceRegistry(seed=False)
        self.assertEqual(len(reg.list_workspaces()), 0)


class TestTopologyEngine(unittest.TestCase):
    """Test workspace topology engine."""

    def test_topology_returns_graph(self) -> None:
        from substrate.meta_ide.workspace_topology_engine import WorkspaceTopologyEngine

        engine = WorkspaceTopologyEngine()
        graph = engine.topology()
        self.assertIsNotNone(graph)
        self.assertEqual(len(graph.workspaces), 4)

    def test_topology_graph_id_present(self) -> None:
        from substrate.meta_ide.workspace_topology_engine import WorkspaceTopologyEngine

        engine = WorkspaceTopologyEngine()
        graph = engine.topology()
        self.assertTrue(graph.graph_id.startswith("wrg-"))

    def test_workspace_health_unknown_workspace(self) -> None:
        from substrate.meta_ide.workspace_runtime_graph import WorkspaceHealth
        from substrate.meta_ide.workspace_topology_engine import WorkspaceTopologyEngine

        engine = WorkspaceTopologyEngine()
        health = engine.workspace_health("nonexistent")
        self.assertEqual(health, WorkspaceHealth.UNKNOWN)

    def test_workspace_health_no_observation(self) -> None:
        from substrate.meta_ide.workspace_runtime_graph import WorkspaceHealth
        from substrate.meta_ide.workspace_topology_engine import WorkspaceTopologyEngine

        engine = WorkspaceTopologyEngine(observation_engine=None)
        health = engine.workspace_health("umh")
        self.assertEqual(health, WorkspaceHealth.UNKNOWN)

    def test_workspace_summary_returns_dict(self) -> None:
        from substrate.meta_ide.workspace_topology_engine import WorkspaceTopologyEngine

        engine = WorkspaceTopologyEngine()
        summary = engine.workspace_summary("umh")
        self.assertIsNotNone(summary)
        self.assertEqual(summary["workspace_id"], "umh")
        self.assertIn("computed_health", summary)

    def test_workspace_summary_not_found(self) -> None:
        from substrate.meta_ide.workspace_topology_engine import WorkspaceTopologyEngine

        engine = WorkspaceTopologyEngine()
        self.assertIsNone(engine.workspace_summary("nonexistent"))

    def test_preferred_build_target_umh(self) -> None:
        from substrate.meta_ide.workspace_topology_engine import WorkspaceTopologyEngine

        engine = WorkspaceTopologyEngine()
        bt = engine.preferred_build_target("umh")
        self.assertIsNotNone(bt)
        self.assertTrue(bt.preferred)
        self.assertEqual(bt.build_type, "linux")

    def test_preferred_build_target_not_found(self) -> None:
        from substrate.meta_ide.workspace_topology_engine import WorkspaceTopologyEngine

        engine = WorkspaceTopologyEngine()
        self.assertIsNone(engine.preferred_build_target("nonexistent"))

    def test_preferred_build_target_product(self) -> None:
        from substrate.meta_ide.workspace_topology_engine import WorkspaceTopologyEngine

        engine = WorkspaceTopologyEngine()
        bt = engine.preferred_build_target("creatoros")
        self.assertIsNotNone(bt)
        self.assertEqual(bt.build_type, "windows")

    def test_registry_property(self) -> None:
        from substrate.meta_ide.workspace_registry import WorkspaceRegistry
        from substrate.meta_ide.workspace_topology_engine import WorkspaceTopologyEngine

        reg = WorkspaceRegistry()
        engine = WorkspaceTopologyEngine(registry=reg)
        self.assertIs(engine.registry, reg)


class TestRuntimeGraphIntegration(unittest.TestCase):
    """Test runtime graph workspace query methods."""

    def test_workspace_for_runtime_found(self) -> None:
        from substrate.organism.runtime_graph import (
            RuntimeCapability,
            RuntimeClass,
            RuntimeGraph,
        )

        graph = RuntimeGraph()
        graph.register(
            "rt-test",
            RuntimeClass.CONTAINER,
            frozenset({RuntimeCapability.CODE_EXECUTE}),
            metadata={"workspace_id": "umh"},
        )
        self.assertEqual(graph.workspace_for_runtime("rt-test"), "umh")

    def test_workspace_for_runtime_not_found(self) -> None:
        from substrate.organism.runtime_graph import RuntimeGraph

        graph = RuntimeGraph()
        self.assertIsNone(graph.workspace_for_runtime("nonexistent"))

    def test_workspace_for_runtime_no_metadata(self) -> None:
        from substrate.organism.runtime_graph import (
            RuntimeCapability,
            RuntimeClass,
            RuntimeGraph,
        )

        graph = RuntimeGraph()
        graph.register(
            "rt-no-ws",
            RuntimeClass.PROCESS,
            frozenset({RuntimeCapability.SHELL}),
        )
        self.assertIsNone(graph.workspace_for_runtime("rt-no-ws"))

    def test_runtimes_for_workspace(self) -> None:
        from substrate.organism.runtime_graph import (
            RuntimeCapability,
            RuntimeClass,
            RuntimeGraph,
        )

        graph = RuntimeGraph()
        graph.register(
            "rt-a",
            RuntimeClass.CONTAINER,
            frozenset({RuntimeCapability.CODE_EXECUTE}),
            metadata={"workspace_id": "umh"},
        )
        graph.register(
            "rt-b",
            RuntimeClass.PROCESS,
            frozenset({RuntimeCapability.SHELL}),
            metadata={"workspace_id": "umh"},
        )
        graph.register(
            "rt-c",
            RuntimeClass.AI_CLI,
            frozenset({RuntimeCapability.CODE_WRITE}),
            metadata={"workspace_id": "creatoros"},
        )
        umh_runtimes = graph.runtimes_for_workspace("umh")
        self.assertEqual(len(umh_runtimes), 2)
        ids = {n.runtime_id for n in umh_runtimes}
        self.assertEqual(ids, {"rt-a", "rt-b"})

    def test_runtimes_for_workspace_empty(self) -> None:
        from substrate.organism.runtime_graph import RuntimeGraph

        graph = RuntimeGraph()
        self.assertEqual(graph.runtimes_for_workspace("nonexistent"), [])

    def test_runtimes_for_workspace_filters_correctly(self) -> None:
        from substrate.organism.runtime_graph import (
            RuntimeCapability,
            RuntimeClass,
            RuntimeGraph,
        )

        graph = RuntimeGraph()
        graph.register(
            "rt-x",
            RuntimeClass.CONTAINER,
            frozenset({RuntimeCapability.SHELL}),
            metadata={"workspace_id": "creatoros"},
        )
        self.assertEqual(len(graph.runtimes_for_workspace("umh")), 0)
        self.assertEqual(len(graph.runtimes_for_workspace("creatoros")), 1)


class TestWorkspaceHealth(unittest.TestCase):
    """Test health computation from observation data."""

    def _make_engine_with_obs(self, containers=None, distributed_runtime=None):
        from unittest.mock import MagicMock
        from substrate.meta_ide.workspace_topology_engine import WorkspaceTopologyEngine

        obs = MagicMock()
        if containers is not None:
            snapshot = MagicMock()
            snapshot.to_dict.return_value = {"containers": containers}
            obs.latest.return_value = snapshot
        else:
            obs.latest.return_value = None
        if distributed_runtime is None:
            distributed_runtime = MagicMock()
            distributed_runtime.device_summary.return_value = None
        return WorkspaceTopologyEngine(
            observation_engine=obs, distributed_runtime=distributed_runtime
        )

    def test_health_unknown_no_observation(self) -> None:
        from substrate.meta_ide.workspace_runtime_graph import WorkspaceHealth

        engine = self._make_engine_with_obs(containers=None)
        self.assertEqual(engine.workspace_health("umh"), WorkspaceHealth.UNKNOWN)

    def test_health_blocked_no_containers_devices_offline(self) -> None:
        from substrate.meta_ide.workspace_runtime_graph import WorkspaceHealth

        engine = self._make_engine_with_obs(containers=[])
        health = engine.workspace_health("umh")
        self.assertEqual(health, WorkspaceHealth.BLOCKED)

    def test_health_healthy_all_up(self) -> None:
        from substrate.meta_ide.workspace_runtime_graph import WorkspaceHealth

        containers = [
            {"container_name": "umh-python", "status": "Up 2h", "health": "healthy"},
            {"container_name": "umh-docker", "status": "Up 3h", "health": "healthy"},
        ]
        engine = self._make_engine_with_obs(containers=containers)
        health = engine.workspace_health("umh")
        self.assertEqual(health, WorkspaceHealth.HEALTHY)

    def test_health_degraded_some_down(self) -> None:
        from substrate.meta_ide.workspace_runtime_graph import WorkspaceHealth

        containers = [
            {"container_name": "umh-python", "status": "Up 2h", "health": "healthy"},
            {"container_name": "umh-docker", "status": "Exited (1) 5m ago", "health": "crashed"},
        ]
        engine = self._make_engine_with_obs(containers=containers)
        health = engine.workspace_health("umh")
        self.assertEqual(health, WorkspaceHealth.DEGRADED)

    def test_health_blocked_all_down(self) -> None:
        from substrate.meta_ide.workspace_runtime_graph import WorkspaceHealth

        containers = [
            {"container_name": "umh-python", "status": "Exited", "health": "crashed"},
            {"container_name": "umh-docker", "status": "Exited", "health": "crashed"},
        ]
        engine = self._make_engine_with_obs(containers=containers)
        health = engine.workspace_health("umh")
        self.assertEqual(health, WorkspaceHealth.BLOCKED)

    def test_health_degraded_unhealthy_status(self) -> None:
        from substrate.meta_ide.workspace_runtime_graph import WorkspaceHealth

        containers = [
            {"container_name": "umh-python", "status": "Up 2h", "health": "healthy"},
            {"container_name": "umh-docker", "status": "Up 1h", "health": "unhealthy"},
        ]
        engine = self._make_engine_with_obs(containers=containers)
        health = engine.workspace_health("umh")
        self.assertEqual(health, WorkspaceHealth.DEGRADED)


class TestCockpitRoutes(unittest.TestCase):
    """Test cockpit route configuration."""

    def test_import_routes(self) -> None:
        from transports.api import cockpit_workspace_topology_routes

        self.assertTrue(hasattr(cockpit_workspace_topology_routes, "workspace_topology_router"))
        self.assertTrue(hasattr(cockpit_workspace_topology_routes, "configure"))

    def test_configure_idempotent(self) -> None:
        from transports.api import cockpit_workspace_topology_routes

        async def mock_dep():
            return "operator"

        cockpit_workspace_topology_routes._configured = False
        cockpit_workspace_topology_routes.configure(require_operator_dep=mock_dep)
        cockpit_workspace_topology_routes.configure(require_operator_dep=mock_dep)
        cockpit_workspace_topology_routes._configured = False

    def test_router_has_routes(self) -> None:
        from transports.api import cockpit_workspace_topology_routes

        async def mock_dep():
            return "operator"

        cockpit_workspace_topology_routes._configured = False
        cockpit_workspace_topology_routes.configure(require_operator_dep=mock_dep)

        rtr = cockpit_workspace_topology_routes.workspace_topology_router
        paths = [r.path for r in rtr.routes if hasattr(r, "path")]
        self.assertTrue(len(paths) > 0)
        cockpit_workspace_topology_routes._configured = False

    def test_engine_singleton(self) -> None:
        from transports.api.cockpit_workspace_topology_routes import _get_engine

        if hasattr(_get_engine, "_instance"):
            delattr(_get_engine, "_instance")
        engine = _get_engine()
        self.assertIsNotNone(engine)
        engine2 = _get_engine()
        self.assertIs(engine, engine2)
        delattr(_get_engine, "_instance")


class TestTypeRegistration(unittest.TestCase):
    """Test canonical type registration."""

    def test_phase27_types_registered(self) -> None:
        from substrate.canonical_types import CANONICAL_TYPES

        phase27_types = [
            "WorkspaceType",
            "RuntimeTargetType",
            "BuildTargetType",
            "WorkspaceHealth",
            "WorkspaceRepository",
            "WorkspaceRuntime",
            "WorkspaceBuildTarget",
            "WorkspaceDefinition",
            "WorkspaceRuntimeGraph",
        ]
        for t in phase27_types:
            self.assertIn(t, CANONICAL_TYPES, f"{t} not registered in canonical_types")
            self.assertEqual(
                CANONICAL_TYPES[t],
                ["substrate.meta_ide.workspace_runtime_graph"],
                f"{t} registered to wrong module",
            )

    def test_no_collision_with_existing_workspace_types(self) -> None:
        from substrate.canonical_types import CANONICAL_TYPES

        existing_ws_types = [
            "WorkspaceStatus",
            "WorkspaceTemplate",
            "WorkspaceState",
            "WorkspaceSnapshot",
            "WorkspaceSequence",
            "WorkspaceSummary",
        ]
        for t in existing_ws_types:
            self.assertIn(t, CANONICAL_TYPES, f"Existing type {t} missing")
            self.assertNotEqual(
                CANONICAL_TYPES[t],
                ["substrate.meta_ide.workspace_runtime_graph"],
                f"{t} should NOT point to Phase 27 module",
            )

    def test_import_from_meta_ide_package(self) -> None:
        from substrate.meta_ide import (
            WorkspaceType,
            RuntimeTargetType,
            BuildTargetType,
            WorkspaceHealth,
            WorkspaceRepository,
            WorkspaceRuntime,
            WorkspaceBuildTarget,
            WorkspaceDefinition,
            WorkspaceRuntimeGraph,
            WorkspaceRegistry,
            WorkspaceTopologyEngine,
        )

        self.assertEqual(WorkspaceType.CORE.value, "core")
        self.assertIsNotNone(WorkspaceRegistry)
        self.assertIsNotNone(WorkspaceTopologyEngine)

    def test_canonical_type_lookup(self) -> None:
        from substrate.canonical_types import lookup

        result = lookup("WorkspaceDefinition")
        self.assertIsNotNone(result)
        self.assertIn("substrate.meta_ide.workspace_runtime_graph", result)


class TestIntegration(unittest.TestCase):
    """End-to-end integration tests."""

    def test_full_topology_chain(self) -> None:
        from substrate.meta_ide.workspace_topology_engine import WorkspaceTopologyEngine

        engine = WorkspaceTopologyEngine()
        graph = engine.topology()
        self.assertEqual(len(graph.workspaces), 4)

        ws_ids = {ws.workspace_id for ws in graph.workspaces}
        self.assertEqual(ws_ids, {"umh", "creatoros", "entrepreneuros", "lyfeos"})

        d = graph.to_dict()
        self.assertEqual(d["workspace_count"], 4)
        self.assertIn("graph_id", d)

    def test_registry_to_engine_to_routes(self) -> None:
        from substrate.meta_ide.workspace_registry import WorkspaceRegistry
        from substrate.meta_ide.workspace_topology_engine import WorkspaceTopologyEngine

        reg = WorkspaceRegistry()
        engine = WorkspaceTopologyEngine(registry=reg)
        self.assertEqual(len(engine.topology().workspaces), 4)
        self.assertIsNotNone(engine.workspace_summary("umh"))
        self.assertIsNotNone(engine.preferred_build_target("umh"))

    def test_umh_workspace_has_repos_and_runtimes(self) -> None:
        from substrate.meta_ide.workspace_registry import WorkspaceRegistry

        reg = WorkspaceRegistry()
        umh = reg.get("umh")
        self.assertIsNotNone(umh)
        self.assertTrue(len(umh.repositories) > 0)
        self.assertTrue(len(umh.runtimes) > 0)
        self.assertTrue(len(umh.build_targets) > 0)

    def test_product_workspaces_have_electron_runtime(self) -> None:
        from substrate.meta_ide.workspace_registry import WorkspaceRegistry

        reg = WorkspaceRegistry()
        for wid in ("creatoros", "entrepreneuros", "lyfeos"):
            ws = reg.get(wid)
            runtime_types = [r.runtime_type for r in ws.runtimes]
            self.assertIn("electron", runtime_types)
            self.assertIn("react", runtime_types)

    def test_device_registry_consistency(self) -> None:
        from substrate.meta_ide.workspace_registry import WorkspaceRegistry

        reg = WorkspaceRegistry()
        umh = reg.get("umh")
        self.assertIn("vps", umh.device_ids)
        creatoros = reg.get("creatoros")
        self.assertIn("beast", creatoros.device_ids)

    def test_topology_to_dict_complete(self) -> None:
        from substrate.meta_ide.workspace_topology_engine import WorkspaceTopologyEngine

        engine = WorkspaceTopologyEngine()
        graph = engine.topology()
        d = graph.to_dict()

        for ws in d["workspaces"]:
            self.assertIn("workspace_id", ws)
            self.assertIn("name", ws)
            self.assertIn("workspace_type", ws)
            self.assertIn("health", ws)
            self.assertIn("repositories", ws)
            self.assertIn("runtimes", ws)
            self.assertIn("build_targets", ws)
            self.assertIn("device_ids", ws)


if __name__ == "__main__":
    unittest.main()
