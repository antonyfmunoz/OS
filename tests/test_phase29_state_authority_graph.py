"""Phase 29 — Organism State Authority & Coherence tests.

Tests state domain authority models, registry, coherence engine,
workspace integration, node integration, cockpit routes, type
registration, and full integration chain.

78 tests across 14 classes.
"""

from __future__ import annotations

import json
import os
import sys
import time
import unittest
from unittest.mock import MagicMock

sys.path.insert(0, os.environ.get("UMH_ROOT", "/opt/OS"))


# ── Workcell A: State Authority Models ─────────────────────────────────────


class TestStateDomainEnum(unittest.TestCase):
    """StateDomain enum — 10 canonical state domains."""

    def test_has_10_values(self) -> None:
        from substrate.organism.state_authority_graph import StateDomain

        self.assertEqual(len(StateDomain), 10)

    def test_memory_value(self) -> None:
        from substrate.organism.state_authority_graph import StateDomain

        self.assertEqual(StateDomain.MEMORY.value, "memory")

    def test_governance_value(self) -> None:
        from substrate.organism.state_authority_graph import StateDomain

        self.assertEqual(StateDomain.GOVERNANCE.value, "governance")

    def test_workspace_value(self) -> None:
        from substrate.organism.state_authority_graph import StateDomain

        self.assertEqual(StateDomain.WORKSPACE.value, "workspace")

    def test_value_access(self) -> None:
        from substrate.organism.state_authority_graph import StateDomain

        self.assertEqual(StateDomain.RUNTIME.value, "runtime")

    def test_all_values_present(self) -> None:
        from substrate.organism.state_authority_graph import StateDomain

        expected = {
            "memory", "governance", "runtime", "workspace", "session",
            "observation", "execution", "proof", "reality", "configuration",
        }
        actual = {d.value for d in StateDomain}
        self.assertEqual(actual, expected)


class TestStateAuthorityLevel(unittest.TestCase):
    """StateAuthorityLevel enum — 5 authority levels."""

    def test_has_5_values(self) -> None:
        from substrate.organism.state_authority_graph import StateAuthorityLevel

        self.assertEqual(len(StateAuthorityLevel), 5)

    def test_primary_value(self) -> None:
        from substrate.organism.state_authority_graph import StateAuthorityLevel

        self.assertEqual(StateAuthorityLevel.PRIMARY.value, "primary")

    def test_all_values(self) -> None:
        from substrate.organism.state_authority_graph import StateAuthorityLevel

        expected = {"primary", "secondary", "cache", "mirror", "derived"}
        actual = {l.value for l in StateAuthorityLevel}
        self.assertEqual(actual, expected)

    def test_value_access(self) -> None:
        from substrate.organism.state_authority_graph import StateAuthorityLevel

        self.assertEqual(StateAuthorityLevel.DERIVED.value, "derived")


class TestStateCoherenceStatus(unittest.TestCase):
    """StateCoherenceStatus enum — 4 coherence states."""

    def test_has_4_values(self) -> None:
        from substrate.organism.state_authority_graph import StateCoherenceStatus

        self.assertEqual(len(StateCoherenceStatus), 4)

    def test_coherent_value(self) -> None:
        from substrate.organism.state_authority_graph import StateCoherenceStatus

        self.assertEqual(StateCoherenceStatus.COHERENT.value, "coherent")

    def test_stale_value(self) -> None:
        from substrate.organism.state_authority_graph import StateCoherenceStatus

        self.assertEqual(StateCoherenceStatus.STALE.value, "stale")

    def test_all_values(self) -> None:
        from substrate.organism.state_authority_graph import StateCoherenceStatus

        expected = {"coherent", "stale", "drifted", "unknown"}
        actual = {s.value for s in StateCoherenceStatus}
        self.assertEqual(actual, expected)


class TestStateAuthorityModel(unittest.TestCase):
    """StateAuthority dataclass — domain authority declaration."""

    def test_construction(self) -> None:
        from substrate.organism.state_authority_graph import StateAuthority

        auth = StateAuthority(
            domain="memory",
            node_id="umh-vps",
            authority_level="primary",
            storage_location="neon_postgres",
            service_owner="memory",
        )
        self.assertEqual(auth.domain, "memory")
        self.assertEqual(auth.node_id, "umh-vps")

    def test_defaults(self) -> None:
        from substrate.organism.state_authority_graph import StateAuthority

        auth = StateAuthority(domain="test")
        self.assertEqual(auth.node_id, "")
        self.assertEqual(auth.authority_level, "primary")
        self.assertEqual(auth.storage_location, "")

    def test_to_dict(self) -> None:
        from substrate.organism.state_authority_graph import StateAuthority

        auth = StateAuthority(domain="governance", node_id="umh-vps")
        d = auth.to_dict()
        self.assertEqual(d["domain"], "governance")
        self.assertEqual(d["node_id"], "umh-vps")
        self.assertIn("authority_level", d)

    def test_from_dict(self) -> None:
        from substrate.organism.state_authority_graph import StateAuthority

        data = {"domain": "runtime", "node_id": "umh-vps", "storage_location": "in_memory"}
        auth = StateAuthority.from_dict(data)
        self.assertEqual(auth.domain, "runtime")
        self.assertEqual(auth.storage_location, "in_memory")

    def test_roundtrip(self) -> None:
        from substrate.organism.state_authority_graph import StateAuthority

        original = StateAuthority(
            domain="execution",
            node_id="umh-vps",
            authority_level="primary",
            storage_location="neon_postgres",
            service_owner="distributed_runtime",
        )
        restored = StateAuthority.from_dict(original.to_dict())
        self.assertEqual(original.domain, restored.domain)
        self.assertEqual(original.node_id, restored.node_id)
        self.assertEqual(original.storage_location, restored.storage_location)
        self.assertEqual(original.service_owner, restored.service_owner)

    def test_from_dict_defaults(self) -> None:
        from substrate.organism.state_authority_graph import StateAuthority

        auth = StateAuthority.from_dict({})
        self.assertEqual(auth.domain, "")
        self.assertEqual(auth.authority_level, "primary")


class TestStateDomainStatusModel(unittest.TestCase):
    """StateDomainStatus dataclass — domain coherence status."""

    def test_construction(self) -> None:
        from substrate.organism.state_authority_graph import StateDomainStatus

        status = StateDomainStatus(
            domain="memory",
            authority_node="umh-vps",
            status="coherent",
        )
        self.assertEqual(status.domain, "memory")
        self.assertEqual(status.authority_node, "umh-vps")

    def test_defaults(self) -> None:
        from substrate.organism.state_authority_graph import StateDomainStatus

        status = StateDomainStatus(domain="test")
        self.assertEqual(status.authority_node, "")
        self.assertEqual(status.status, "unknown")
        self.assertEqual(status.secondary_nodes, [])

    def test_to_dict(self) -> None:
        from substrate.organism.state_authority_graph import StateDomainStatus

        status = StateDomainStatus(domain="governance", authority_node="umh-vps", status="coherent")
        d = status.to_dict()
        self.assertEqual(d["domain"], "governance")
        self.assertIn("secondary_nodes", d)

    def test_from_dict(self) -> None:
        from substrate.organism.state_authority_graph import StateDomainStatus

        data = {"domain": "workspace", "authority_node": "umh-windows", "status": "stale"}
        status = StateDomainStatus.from_dict(data)
        self.assertEqual(status.domain, "workspace")
        self.assertEqual(status.status, "stale")

    def test_roundtrip(self) -> None:
        from substrate.organism.state_authority_graph import StateDomainStatus

        original = StateDomainStatus(
            domain="session",
            authority_node="umh-windows",
            secondary_nodes=["umh-vps"],
            status="coherent",
            last_updated=1234567890.0,
        )
        restored = StateDomainStatus.from_dict(original.to_dict())
        self.assertEqual(original.domain, restored.domain)
        self.assertEqual(original.secondary_nodes, restored.secondary_nodes)
        self.assertEqual(original.last_updated, restored.last_updated)

    def test_with_secondary_nodes(self) -> None:
        from substrate.organism.state_authority_graph import StateDomainStatus

        status = StateDomainStatus(
            domain="observation",
            secondary_nodes=["umh-vps", "umh-laptop"],
        )
        self.assertEqual(len(status.secondary_nodes), 2)


class TestOrganismStateGraph(unittest.TestCase):
    """OrganismStateGraph dataclass — full state topology."""

    def test_construction(self) -> None:
        from substrate.organism.state_authority_graph import OrganismStateGraph

        graph = OrganismStateGraph()
        self.assertTrue(graph.topology_id.startswith("osg-"))
        self.assertEqual(graph.organism_id, "umh")
        self.assertEqual(graph.domains, [])

    def test_to_dict(self) -> None:
        from substrate.organism.state_authority_graph import (
            OrganismStateGraph,
            StateDomainStatus,
        )

        graph = OrganismStateGraph(
            domains=[StateDomainStatus(domain="memory", authority_node="umh-vps")]
        )
        d = graph.to_dict()
        self.assertEqual(d["domain_count"], 1)
        self.assertIn("topology_id", d)
        self.assertIn("generated_at", d)

    def test_from_dict(self) -> None:
        from substrate.organism.state_authority_graph import OrganismStateGraph

        data = {
            "topology_id": "osg-test",
            "organism_id": "umh",
            "domains": [{"domain": "governance", "authority_node": "umh-vps"}],
            "generated_at": 1000.0,
        }
        graph = OrganismStateGraph.from_dict(data)
        self.assertEqual(graph.topology_id, "osg-test")
        self.assertEqual(len(graph.domains), 1)

    def test_roundtrip(self) -> None:
        from substrate.organism.state_authority_graph import (
            OrganismStateGraph,
            StateDomainStatus,
        )

        original = OrganismStateGraph(
            domains=[
                StateDomainStatus(domain="memory", authority_node="umh-vps"),
                StateDomainStatus(domain="workspace", authority_node="umh-windows"),
            ]
        )
        restored = OrganismStateGraph.from_dict(original.to_dict())
        self.assertEqual(len(restored.domains), 2)
        self.assertEqual(restored.organism_id, "umh")


# ── Workcell B: State Registry ─────────────────────────────────────────────


class TestStateRegistry(unittest.TestCase):
    """StateRegistry — loads seed data, provides lookup API."""

    def test_seed_loads_10_domains(self) -> None:
        from substrate.organism.state_registry import StateRegistry

        reg = StateRegistry()
        self.assertEqual(len(reg.all_domains()), 10)

    def test_get_domain_memory(self) -> None:
        from substrate.organism.state_registry import StateRegistry

        reg = StateRegistry()
        auth = reg.get_domain("memory")
        self.assertIsNotNone(auth)
        self.assertEqual(auth.node_id, "umh-vps")

    def test_get_domain_workspace(self) -> None:
        from substrate.organism.state_registry import StateRegistry

        reg = StateRegistry()
        auth = reg.get_domain("workspace")
        self.assertIsNotNone(auth)
        self.assertEqual(auth.node_id, "umh-windows")

    def test_get_domain_missing(self) -> None:
        from substrate.organism.state_registry import StateRegistry

        reg = StateRegistry()
        auth = reg.get_domain("nonexistent")
        self.assertIsNone(auth)

    def test_authority_node(self) -> None:
        from substrate.organism.state_registry import StateRegistry

        reg = StateRegistry()
        self.assertEqual(reg.authority_node("governance"), "umh-vps")
        self.assertEqual(reg.authority_node("session"), "umh-windows")

    def test_authority_node_missing(self) -> None:
        from substrate.organism.state_registry import StateRegistry

        reg = StateRegistry()
        self.assertEqual(reg.authority_node("nonexistent"), "")

    def test_domains_for_vps(self) -> None:
        from substrate.organism.state_registry import StateRegistry

        reg = StateRegistry()
        vps_domains = reg.domains_for_node("umh-vps")
        self.assertEqual(len(vps_domains), 7)

    def test_domains_for_windows(self) -> None:
        from substrate.organism.state_registry import StateRegistry

        reg = StateRegistry()
        win_domains = reg.domains_for_node("umh-windows")
        self.assertEqual(len(win_domains), 3)

    def test_topology(self) -> None:
        from substrate.organism.state_registry import StateRegistry

        reg = StateRegistry()
        topo = reg.topology()
        self.assertTrue(topo.topology_id.startswith("osg-"))
        self.assertEqual(len(topo.domains), 10)

    def test_to_dict(self) -> None:
        from substrate.organism.state_registry import StateRegistry

        reg = StateRegistry()
        d = reg.to_dict()
        self.assertEqual(d["domain_count"], 10)
        self.assertIn("memory", d["domains"])


# ── Seed Authorities ────────────────────────────────────────────────────────


class TestSeedAuthorities(unittest.TestCase):
    """Seed data validation — VPS owns 7, Beast owns 3."""

    def test_vps_owns_memory(self) -> None:
        from substrate.organism.state_registry import StateRegistry

        reg = StateRegistry()
        self.assertEqual(reg.authority_node("memory"), "umh-vps")

    def test_vps_owns_governance(self) -> None:
        from substrate.organism.state_registry import StateRegistry

        reg = StateRegistry()
        self.assertEqual(reg.authority_node("governance"), "umh-vps")

    def test_vps_owns_execution(self) -> None:
        from substrate.organism.state_registry import StateRegistry

        reg = StateRegistry()
        self.assertEqual(reg.authority_node("execution"), "umh-vps")

    def test_vps_owns_proof(self) -> None:
        from substrate.organism.state_registry import StateRegistry

        reg = StateRegistry()
        self.assertEqual(reg.authority_node("proof"), "umh-vps")

    def test_windows_owns_workspace(self) -> None:
        from substrate.organism.state_registry import StateRegistry

        reg = StateRegistry()
        self.assertEqual(reg.authority_node("workspace"), "umh-windows")

    def test_windows_owns_session(self) -> None:
        from substrate.organism.state_registry import StateRegistry

        reg = StateRegistry()
        self.assertEqual(reg.authority_node("session"), "umh-windows")

    def test_windows_owns_observation(self) -> None:
        from substrate.organism.state_registry import StateRegistry

        reg = StateRegistry()
        self.assertEqual(reg.authority_node("observation"), "umh-windows")

    def test_all_10_domains_covered(self) -> None:
        from substrate.organism.state_authority_graph import StateDomain
        from substrate.organism.state_registry import StateRegistry

        reg = StateRegistry()
        for domain in StateDomain:
            auth = reg.get_domain(domain.value)
            self.assertIsNotNone(auth, f"Domain {domain.value} not in registry")


# ── Workcell C: State Coherence Engine ──────────────────────────────────────


class TestStateCoherenceEngine(unittest.TestCase):
    """StateCoherenceEngine — detects authority coherence."""

    def _make_engine(
        self,
        node_status: str = "online",
        node_last_seen: float = 0.0,
        node_version_status: str = "coherent",
    ) -> "StateCoherenceEngine":
        from substrate.organism.state_authority_graph import StateDomain
        from substrate.organism.state_coherence_engine import StateCoherenceEngine
        from substrate.organism.state_registry import StateRegistry

        mock_node = MagicMock()
        mock_node.status = node_status
        mock_node.last_seen = node_last_seen
        mock_node.version = MagicMock()
        mock_node.version.git_commit = "abc123"

        mock_node_registry = MagicMock()
        mock_node_registry.get_node.return_value = mock_node

        engine = StateCoherenceEngine(
            state_registry=StateRegistry(),
            node_registry=mock_node_registry,
        )
        return engine

    def test_coherent_when_online(self) -> None:
        engine = self._make_engine(node_status="online")
        status = engine.domain_status("memory")
        self.assertEqual(status.status, "coherent")

    def test_stale_when_offline(self) -> None:
        engine = self._make_engine(node_status="offline")
        status = engine.domain_status("memory")
        self.assertEqual(status.status, "stale")

    def test_stale_when_old_last_seen(self) -> None:
        old_time = time.time() - 7200
        engine = self._make_engine(node_status="online", node_last_seen=old_time)
        status = engine.domain_status("memory")
        self.assertEqual(status.status, "stale")

    def test_unknown_when_no_node(self) -> None:
        from substrate.organism.state_coherence_engine import StateCoherenceEngine
        from substrate.organism.state_registry import StateRegistry

        mock_node_registry = MagicMock()
        mock_node_registry.get_node.return_value = None

        engine = StateCoherenceEngine(
            state_registry=StateRegistry(),
            node_registry=mock_node_registry,
        )
        status = engine.domain_status("memory")
        self.assertEqual(status.status, "unknown")

    def test_unknown_domain(self) -> None:
        engine = self._make_engine()
        status = engine.domain_status("nonexistent")
        self.assertEqual(status.status, "unknown")

    def test_coherence_report_has_10_domains(self) -> None:
        engine = self._make_engine()
        report = engine.coherence_report()
        self.assertEqual(report["domain_count"], 10)
        self.assertIn("overall_health", report)

    def test_organism_health_all_coherent(self) -> None:
        engine = self._make_engine()
        health = engine.organism_health()
        self.assertEqual(health["total_domains"], 10)
        self.assertEqual(health["coherent"], 10)
        self.assertTrue(health["healthy"])

    def test_organism_health_with_stale(self) -> None:
        engine = self._make_engine(node_status="offline")
        health = engine.organism_health()
        self.assertGreater(health["stale"], 0)
        self.assertFalse(health["healthy"])


# ── Workcell D: Workspace Integration ───────────────────────────────────────


class TestWorkspaceIntegration(unittest.TestCase):
    """workspace_state_domains() — derived from node ownership."""

    def test_umh_workspace_has_all_domains(self) -> None:
        from substrate.meta_ide.workspace_topology_engine import WorkspaceTopologyEngine

        engine = WorkspaceTopologyEngine()
        result = engine.workspace_state_domains("umh")
        self.assertIsNotNone(result)
        self.assertEqual(result["workspace"], "umh")
        self.assertEqual(len(result["domains"]), 10)

    def test_creatoros_workspace_has_beast_domains(self) -> None:
        from substrate.meta_ide.workspace_topology_engine import WorkspaceTopologyEngine

        engine = WorkspaceTopologyEngine()
        result = engine.workspace_state_domains("creatoros")
        self.assertIsNotNone(result)
        for domain in ["workspace", "session", "observation"]:
            self.assertIn(domain, result["domains"])

    def test_creatoros_also_has_vps_domains(self) -> None:
        from substrate.meta_ide.workspace_topology_engine import WorkspaceTopologyEngine

        engine = WorkspaceTopologyEngine()
        result = engine.workspace_state_domains("creatoros")
        self.assertIsNotNone(result)
        self.assertEqual(len(result["domains"]), 10)

    def test_unknown_workspace_returns_none(self) -> None:
        from substrate.meta_ide.workspace_topology_engine import WorkspaceTopologyEngine

        engine = WorkspaceTopologyEngine()
        result = engine.workspace_state_domains("nonexistent")
        self.assertIsNone(result)

    def test_domains_are_unique(self) -> None:
        from substrate.meta_ide.workspace_topology_engine import WorkspaceTopologyEngine

        engine = WorkspaceTopologyEngine()
        result = engine.workspace_state_domains("umh")
        self.assertIsNotNone(result)
        domains = result["domains"]
        self.assertEqual(len(domains), len(set(domains)))

    def test_return_structure(self) -> None:
        from substrate.meta_ide.workspace_topology_engine import WorkspaceTopologyEngine

        engine = WorkspaceTopologyEngine()
        result = engine.workspace_state_domains("umh")
        self.assertIn("workspace", result)
        self.assertIn("domains", result)
        self.assertIsInstance(result["domains"], list)


# ── Workcell E: Node Integration ────────────────────────────────────────────


class TestNodeIntegration(unittest.TestCase):
    """owned_state_domains on UMHNodeRecord."""

    def test_vps_has_7_domains(self) -> None:
        from substrate.organism.umh_node_registry import UMHNodeRegistry

        reg = UMHNodeRegistry()
        vps = reg.get_node("umh-vps")
        self.assertIsNotNone(vps)
        self.assertEqual(len(vps.owned_state_domains), 7)

    def test_windows_has_3_domains(self) -> None:
        from substrate.organism.umh_node_registry import UMHNodeRegistry

        reg = UMHNodeRegistry()
        win = reg.get_node("umh-windows")
        self.assertIsNotNone(win)
        self.assertEqual(len(win.owned_state_domains), 3)

    def test_vps_owns_memory(self) -> None:
        from substrate.organism.umh_node_registry import UMHNodeRegistry

        reg = UMHNodeRegistry()
        vps = reg.get_node("umh-vps")
        self.assertIn("memory", vps.owned_state_domains)

    def test_windows_owns_workspace(self) -> None:
        from substrate.organism.umh_node_registry import UMHNodeRegistry

        reg = UMHNodeRegistry()
        win = reg.get_node("umh-windows")
        self.assertIn("workspace", win.owned_state_domains)

    def test_to_dict_includes_owned_state_domains(self) -> None:
        from substrate.organism.umh_node_registry import UMHNodeRegistry

        reg = UMHNodeRegistry()
        vps = reg.get_node("umh-vps")
        d = vps.to_dict()
        self.assertIn("owned_state_domains", d)
        self.assertEqual(len(d["owned_state_domains"]), 7)

    def test_from_dict_roundtrip(self) -> None:
        from substrate.organism.umh_node_topology import UMHNodeRecord

        record = UMHNodeRecord(
            node_id="test-node",
            owned_state_domains=["memory", "governance"],
        )
        restored = UMHNodeRecord.from_dict(record.to_dict())
        self.assertEqual(restored.owned_state_domains, ["memory", "governance"])


# ── Workcell F: Cockpit Routes ──────────────────────────────────────────────


class TestCockpitRoutes(unittest.TestCase):
    """Cockpit state authority route module."""

    def test_import(self) -> None:
        from transports.api import cockpit_state_authority_routes

        self.assertIsNotNone(cockpit_state_authority_routes)

    def test_has_router(self) -> None:
        from transports.api.cockpit_state_authority_routes import state_authority_router

        self.assertIsNotNone(state_authority_router)

    def test_has_configure(self) -> None:
        from transports.api.cockpit_state_authority_routes import configure

        self.assertTrue(callable(configure))

    def test_singleton_pattern(self) -> None:
        from transports.api import cockpit_state_authority_routes

        self.assertFalse(cockpit_state_authority_routes._configured)


# ── Workcell G: Type Registration ───────────────────────────────────────────


class TestTypeRegistration(unittest.TestCase):
    """Canonical type registration for Phase 29 types."""

    def test_state_domain_registered(self) -> None:
        from substrate.canonical_types import CANONICAL_TYPES

        self.assertIn("StateDomain", CANONICAL_TYPES)

    def test_state_registry_registered(self) -> None:
        from substrate.canonical_types import CANONICAL_TYPES

        self.assertIn("StateRegistry", CANONICAL_TYPES)

    def test_coherence_engine_registered(self) -> None:
        from substrate.canonical_types import CANONICAL_TYPES

        self.assertIn("StateCoherenceEngine", CANONICAL_TYPES)

    def test_all_8_types_registered(self) -> None:
        from substrate.canonical_types import CANONICAL_TYPES

        expected = {
            "StateDomain",
            "StateAuthorityLevel",
            "StateCoherenceStatus",
            "StateAuthority",
            "StateDomainStatus",
            "OrganismStateGraph",
            "StateRegistry",
            "StateCoherenceEngine",
        }
        for name in expected:
            self.assertIn(name, CANONICAL_TYPES, f"{name} not registered")


# ── Integration Tests ───────────────────────────────────────────────────────


class TestIntegration(unittest.TestCase):
    """Full chain: state → node → workspace composition."""

    def test_state_registry_loads(self) -> None:
        from substrate.organism.state_registry import StateRegistry

        reg = StateRegistry()
        self.assertEqual(len(reg.all_domains()), 10)

    def test_node_registry_loads(self) -> None:
        from substrate.organism.umh_node_registry import UMHNodeRegistry

        reg = UMHNodeRegistry()
        self.assertEqual(len(reg.list_nodes()), 2)

    def test_state_node_consistency(self) -> None:
        """State authority node_ids match actual node IDs in node registry."""
        from substrate.organism.state_registry import StateRegistry
        from substrate.organism.umh_node_registry import UMHNodeRegistry

        state_reg = StateRegistry()
        node_reg = UMHNodeRegistry()
        node_ids = {n.node_id for n in node_reg.list_nodes()}

        for auth in state_reg.all_domains():
            self.assertIn(
                auth.node_id, node_ids,
                f"State domain {auth.domain} references unknown node {auth.node_id}",
            )

    def test_node_domains_match_state_registry(self) -> None:
        """owned_state_domains on nodes match state registry assignments."""
        from substrate.organism.state_registry import StateRegistry
        from substrate.organism.umh_node_registry import UMHNodeRegistry

        state_reg = StateRegistry()
        node_reg = UMHNodeRegistry()

        for node in node_reg.list_nodes():
            state_domains = state_reg.domains_for_node(node.node_id)
            state_domain_names = {a.domain for a in state_domains}
            owned_set = set(node.owned_state_domains)
            self.assertEqual(
                state_domain_names, owned_set,
                f"Node {node.node_id}: state registry says {state_domain_names}, "
                f"node says {owned_set}",
            )

    def test_topology_stack(self) -> None:
        """Phase 27 + 28 + 29 topology stack composes."""
        from substrate.meta_ide.workspace_topology_engine import WorkspaceTopologyEngine
        from substrate.organism.state_registry import StateRegistry

        ws_engine = WorkspaceTopologyEngine()
        state_reg = StateRegistry()

        ws_topo = ws_engine.topology()
        state_topo = state_reg.topology()

        self.assertGreater(len(ws_topo.workspaces), 0)
        self.assertEqual(len(state_topo.domains), 10)

    def test_coherence_engine_composes_both_registries(self) -> None:
        from substrate.organism.state_coherence_engine import StateCoherenceEngine

        engine = StateCoherenceEngine()
        health = engine.organism_health()
        self.assertEqual(health["total_domains"], 10)

    def test_register_custom_authority(self) -> None:
        from substrate.organism.state_authority_graph import StateAuthority
        from substrate.organism.state_registry import StateRegistry

        reg = StateRegistry()
        custom = StateAuthority(
            domain="custom_domain",
            node_id="umh-vps",
            authority_level="secondary",
        )
        reg.register_authority(custom)
        self.assertEqual(len(reg.all_domains()), 11)
        self.assertIsNotNone(reg.get_domain("custom_domain"))

    def test_organism_state_graph_contains_all_domains(self) -> None:
        from substrate.organism.state_registry import StateRegistry

        reg = StateRegistry()
        graph = reg.topology()
        domain_names = {d.domain for d in graph.domains}
        expected = {
            "memory", "governance", "runtime", "workspace", "session",
            "observation", "execution", "proof", "reality", "configuration",
        }
        self.assertEqual(domain_names, expected)


if __name__ == "__main__":
    unittest.main()
