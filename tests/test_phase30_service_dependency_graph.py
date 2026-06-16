"""Phase 30 — Service Dependency & Failure Graph tests.

Tests: dependency strength, service criticality, health impact,
service dependency, service node, failure impact, topology,
registry, failure engine, seed data, cockpit routes, type
registration, topology stack integration, cross-layer queries.

~90 tests across 14 classes.
"""

import os
import sys
import json
import unittest

sys.path.insert(0, os.environ.get("UMH_ROOT", "/opt/OS"))


# ── Workcell A: Enums ───────────────────────────────────────────────────


class TestDependencyStrengthEnum(unittest.TestCase):
    """Test DependencyStrength enum — 3 values."""

    def test_enum_count(self) -> None:
        from substrate.organism.service_dependency_graph import DependencyStrength

        self.assertEqual(len(DependencyStrength), 3)

    def test_values(self) -> None:
        from substrate.organism.service_dependency_graph import DependencyStrength

        self.assertEqual(DependencyStrength.REQUIRED.value, "required")
        self.assertEqual(DependencyStrength.DEGRADED.value, "degraded")
        self.assertEqual(DependencyStrength.OPTIONAL.value, "optional")

    def test_string_enum(self) -> None:
        from substrate.organism.service_dependency_graph import DependencyStrength

        self.assertIsInstance(DependencyStrength.REQUIRED, str)

    def test_membership(self) -> None:
        from substrate.organism.service_dependency_graph import DependencyStrength

        self.assertIn("required", [e.value for e in DependencyStrength])


class TestServiceCriticalityEnum(unittest.TestCase):
    """Test ServiceCriticality enum — 4 values."""

    def test_enum_count(self) -> None:
        from substrate.organism.service_dependency_graph import ServiceCriticality

        self.assertEqual(len(ServiceCriticality), 4)

    def test_values(self) -> None:
        from substrate.organism.service_dependency_graph import ServiceCriticality

        self.assertEqual(ServiceCriticality.CRITICAL.value, "critical")
        self.assertEqual(ServiceCriticality.CORE.value, "core")
        self.assertEqual(ServiceCriticality.SUPPORTING.value, "supporting")
        self.assertEqual(ServiceCriticality.OPTIONAL.value, "optional")

    def test_string_enum(self) -> None:
        from substrate.organism.service_dependency_graph import ServiceCriticality

        self.assertIsInstance(ServiceCriticality.CRITICAL, str)

    def test_membership(self) -> None:
        from substrate.organism.service_dependency_graph import ServiceCriticality

        values = [e.value for e in ServiceCriticality]
        self.assertIn("core", values)
        self.assertIn("optional", values)


class TestServiceHealthImpactEnum(unittest.TestCase):
    """Test ServiceHealthImpact enum — 4 values."""

    def test_enum_count(self) -> None:
        from substrate.organism.service_dependency_graph import ServiceHealthImpact

        self.assertEqual(len(ServiceHealthImpact), 4)

    def test_values(self) -> None:
        from substrate.organism.service_dependency_graph import ServiceHealthImpact

        self.assertEqual(ServiceHealthImpact.BLOCKED.value, "blocked")
        self.assertEqual(ServiceHealthImpact.DEGRADED.value, "degraded")
        self.assertEqual(ServiceHealthImpact.UNAFFECTED.value, "unaffected")
        self.assertEqual(ServiceHealthImpact.UNKNOWN.value, "unknown")

    def test_string_enum(self) -> None:
        from substrate.organism.service_dependency_graph import ServiceHealthImpact

        self.assertIsInstance(ServiceHealthImpact.BLOCKED, str)

    def test_membership(self) -> None:
        from substrate.organism.service_dependency_graph import ServiceHealthImpact

        values = [e.value for e in ServiceHealthImpact]
        self.assertIn("blocked", values)
        self.assertIn("unaffected", values)


# ── Workcell A: Dataclasses ──────────────────────────────────────────────


class TestServiceDependency(unittest.TestCase):
    """Test ServiceDependency dataclass."""

    def test_construction(self) -> None:
        from substrate.organism.service_dependency_graph import ServiceDependency

        dep = ServiceDependency(
            source_service="action_bridge",
            target_service="governance",
            strength="required",
            description="Risk gate",
        )
        self.assertEqual(dep.source_service, "action_bridge")
        self.assertEqual(dep.target_service, "governance")

    def test_defaults(self) -> None:
        from substrate.organism.service_dependency_graph import ServiceDependency

        dep = ServiceDependency(source_service="test")
        self.assertEqual(dep.target_service, "")
        self.assertEqual(dep.strength, "degraded")
        self.assertEqual(dep.description, "")

    def test_to_dict(self) -> None:
        from substrate.organism.service_dependency_graph import ServiceDependency

        dep = ServiceDependency(
            source_service="a", target_service="b", strength="optional"
        )
        d = dep.to_dict()
        self.assertEqual(d["source_service"], "a")
        self.assertEqual(d["target_service"], "b")
        self.assertEqual(d["strength"], "optional")

    def test_from_dict(self) -> None:
        from substrate.organism.service_dependency_graph import ServiceDependency

        dep = ServiceDependency.from_dict({
            "source_service": "x",
            "target_service": "y",
            "strength": "required",
        })
        self.assertEqual(dep.source_service, "x")
        self.assertEqual(dep.strength, "required")

    def test_roundtrip(self) -> None:
        from substrate.organism.service_dependency_graph import ServiceDependency

        dep = ServiceDependency(
            source_service="a", target_service="b",
            strength="degraded", description="test",
        )
        dep2 = ServiceDependency.from_dict(dep.to_dict())
        self.assertEqual(dep.source_service, dep2.source_service)
        self.assertEqual(dep.description, dep2.description)

    def test_from_dict_defaults(self) -> None:
        from substrate.organism.service_dependency_graph import ServiceDependency

        dep = ServiceDependency.from_dict({})
        self.assertEqual(dep.source_service, "")
        self.assertEqual(dep.strength, "degraded")


class TestServiceNode(unittest.TestCase):
    """Test ServiceNode dataclass."""

    def test_construction(self) -> None:
        from substrate.organism.service_dependency_graph import ServiceNode

        node = ServiceNode(
            service_role="governance",
            description="Risk engine",
            criticality="critical",
            owner_node="umh-vps",
            state_domains=["governance", "proof"],
        )
        self.assertEqual(node.service_role, "governance")
        self.assertEqual(len(node.state_domains), 2)

    def test_defaults(self) -> None:
        from substrate.organism.service_dependency_graph import ServiceNode

        node = ServiceNode(service_role="test")
        self.assertEqual(node.description, "")
        self.assertEqual(node.criticality, "supporting")
        self.assertEqual(node.owner_node, "")
        self.assertEqual(node.state_domains, [])

    def test_to_dict(self) -> None:
        from substrate.organism.service_dependency_graph import ServiceNode

        node = ServiceNode(service_role="memory", owner_node="umh-vps")
        d = node.to_dict()
        self.assertEqual(d["service_role"], "memory")
        self.assertIn("state_domains", d)

    def test_from_dict(self) -> None:
        from substrate.organism.service_dependency_graph import ServiceNode

        node = ServiceNode.from_dict({
            "service_role": "event_spine",
            "criticality": "critical",
        })
        self.assertEqual(node.service_role, "event_spine")
        self.assertEqual(node.criticality, "critical")

    def test_roundtrip(self) -> None:
        from substrate.organism.service_dependency_graph import ServiceNode

        node = ServiceNode(
            service_role="meta_ide", description="IDE",
            criticality="supporting", owner_node="umh-windows",
            state_domains=["workspace"],
        )
        node2 = ServiceNode.from_dict(node.to_dict())
        self.assertEqual(node.service_role, node2.service_role)
        self.assertEqual(node.state_domains, node2.state_domains)

    def test_state_domains_list(self) -> None:
        from substrate.organism.service_dependency_graph import ServiceNode

        node = ServiceNode(
            service_role="gov",
            state_domains=["governance", "proof", "reality"],
        )
        self.assertEqual(len(node.state_domains), 3)
        self.assertIn("proof", node.state_domains)


class TestFailureImpact(unittest.TestCase):
    """Test FailureImpact dataclass."""

    def test_construction(self) -> None:
        from substrate.organism.service_dependency_graph import FailureImpact

        impact = FailureImpact(
            failed_service="governance",
            directly_affected=["cockpit_api", "distributed_runtime"],
            blast_radius=5,
            severity="high",
        )
        self.assertEqual(impact.failed_service, "governance")
        self.assertEqual(impact.blast_radius, 5)

    def test_defaults(self) -> None:
        from substrate.organism.service_dependency_graph import FailureImpact

        impact = FailureImpact(failed_service="test")
        self.assertEqual(impact.directly_affected, [])
        self.assertEqual(impact.transitively_affected, [])
        self.assertEqual(impact.affected_state_domains, [])
        self.assertEqual(impact.blast_radius, 0)
        self.assertEqual(impact.severity, "low")

    def test_to_dict(self) -> None:
        from substrate.organism.service_dependency_graph import FailureImpact

        impact = FailureImpact(
            failed_service="memory", blast_radius=3, severity="medium",
        )
        d = impact.to_dict()
        self.assertEqual(d["failed_service"], "memory")
        self.assertEqual(d["blast_radius"], 3)

    def test_from_dict(self) -> None:
        from substrate.organism.service_dependency_graph import FailureImpact

        impact = FailureImpact.from_dict({
            "failed_service": "event_spine",
            "blast_radius": 4,
        })
        self.assertEqual(impact.failed_service, "event_spine")
        self.assertEqual(impact.blast_radius, 4)

    def test_roundtrip(self) -> None:
        from substrate.organism.service_dependency_graph import FailureImpact

        impact = FailureImpact(
            failed_service="gov",
            directly_affected=["a"],
            transitively_affected=["b", "c"],
            affected_state_domains=["governance"],
            blast_radius=3,
            severity="medium",
        )
        impact2 = FailureImpact.from_dict(impact.to_dict())
        self.assertEqual(impact.blast_radius, impact2.blast_radius)
        self.assertEqual(impact.affected_state_domains, impact2.affected_state_domains)

    def test_severity_values(self) -> None:
        from substrate.organism.service_dependency_graph import FailureImpact

        for sev in ["low", "medium", "high", "critical"]:
            impact = FailureImpact(failed_service="x", severity=sev)
            self.assertEqual(impact.severity, sev)


class TestServiceDependencyTopology(unittest.TestCase):
    """Test ServiceDependencyTopology dataclass."""

    def test_construction(self) -> None:
        from substrate.organism.service_dependency_graph import (
            ServiceDependencyTopology,
        )

        topo = ServiceDependencyTopology()
        self.assertTrue(topo.topology_id.startswith("sdt-"))
        self.assertEqual(topo.organism_id, "umh")

    def test_to_dict_counts(self) -> None:
        from substrate.organism.service_dependency_graph import (
            ServiceDependencyTopology, ServiceNode, ServiceDependency,
        )

        topo = ServiceDependencyTopology(
            services=[ServiceNode(service_role="a"), ServiceNode(service_role="b")],
            dependencies=[ServiceDependency(source_service="a", target_service="b")],
        )
        d = topo.to_dict()
        self.assertEqual(d["service_count"], 2)
        self.assertEqual(d["dependency_count"], 1)

    def test_from_dict(self) -> None:
        from substrate.organism.service_dependency_graph import (
            ServiceDependencyTopology,
        )

        topo = ServiceDependencyTopology.from_dict({
            "topology_id": "sdt-test",
            "services": [{"service_role": "x"}],
            "dependencies": [{"source_service": "x", "target_service": "y"}],
        })
        self.assertEqual(topo.topology_id, "sdt-test")
        self.assertEqual(len(topo.services), 1)
        self.assertEqual(len(topo.dependencies), 1)

    def test_roundtrip(self) -> None:
        from substrate.organism.service_dependency_graph import (
            ServiceDependencyTopology, ServiceNode,
        )

        topo = ServiceDependencyTopology(
            services=[ServiceNode(service_role="gov")],
        )
        topo2 = ServiceDependencyTopology.from_dict(topo.to_dict())
        self.assertEqual(topo.organism_id, topo2.organism_id)
        self.assertEqual(len(topo.services), len(topo2.services))

    def test_generated_at(self) -> None:
        from substrate.organism.service_dependency_graph import (
            ServiceDependencyTopology,
        )

        topo = ServiceDependencyTopology()
        self.assertGreater(topo.generated_at, 0)


# ── Workcell B: Registry ────────────────────────────────────────────────


class TestServiceDependencyRegistry(unittest.TestCase):
    """Test ServiceDependencyRegistry — seed loading, query methods."""

    def test_seed_loads(self) -> None:
        from substrate.organism.service_dependency_registry import (
            ServiceDependencyRegistry,
        )

        reg = ServiceDependencyRegistry()
        self.assertGreater(len(reg.list_services()), 0)

    def test_service_count(self) -> None:
        from substrate.organism.service_dependency_registry import (
            ServiceDependencyRegistry,
        )

        reg = ServiceDependencyRegistry()
        self.assertEqual(len(reg.list_services()), 13)

    def test_get_service(self) -> None:
        from substrate.organism.service_dependency_registry import (
            ServiceDependencyRegistry,
        )

        reg = ServiceDependencyRegistry()
        svc = reg.get_service("governance")
        self.assertIsNotNone(svc)
        self.assertEqual(svc.criticality, "critical")

    def test_get_service_missing(self) -> None:
        from substrate.organism.service_dependency_registry import (
            ServiceDependencyRegistry,
        )

        reg = ServiceDependencyRegistry()
        self.assertIsNone(reg.get_service("nonexistent"))

    def test_dependencies_of(self) -> None:
        from substrate.organism.service_dependency_registry import (
            ServiceDependencyRegistry,
        )

        reg = ServiceDependencyRegistry()
        deps = reg.dependencies_of("cockpit_api")
        targets = [d.target_service for d in deps]
        self.assertIn("governance", targets)
        self.assertIn("memory", targets)

    def test_dependents_of(self) -> None:
        from substrate.organism.service_dependency_registry import (
            ServiceDependencyRegistry,
        )

        reg = ServiceDependencyRegistry()
        deps = reg.dependents_of("governance")
        sources = [d.source_service for d in deps]
        self.assertIn("cockpit_api", sources)
        self.assertIn("distributed_runtime", sources)
        self.assertIn("action_bridge", sources)

    def test_services_for_node(self) -> None:
        from substrate.organism.service_dependency_registry import (
            ServiceDependencyRegistry,
        )

        reg = ServiceDependencyRegistry()
        vps = reg.services_for_node("umh-vps")
        roles = [s.service_role for s in vps]
        self.assertIn("governance", roles)
        self.assertIn("memory", roles)
        self.assertIn("cockpit_api", roles)

    def test_services_for_domain(self) -> None:
        from substrate.organism.service_dependency_registry import (
            ServiceDependencyRegistry,
        )

        reg = ServiceDependencyRegistry()
        mem_services = reg.services_for_domain("memory")
        roles = [s.service_role for s in mem_services]
        self.assertIn("memory", roles)

    def test_critical_services(self) -> None:
        from substrate.organism.service_dependency_registry import (
            ServiceDependencyRegistry,
        )

        reg = ServiceDependencyRegistry()
        critical = reg.critical_services()
        roles = [s.service_role for s in critical]
        self.assertIn("governance", roles)
        self.assertIn("memory", roles)
        self.assertIn("event_spine", roles)
        self.assertIn("cockpit_api", roles)

    def test_leaf_services(self) -> None:
        from substrate.organism.service_dependency_registry import (
            ServiceDependencyRegistry,
        )

        reg = ServiceDependencyRegistry()
        leaves = reg.leaf_services()
        roles = [s.service_role for s in leaves]
        self.assertIn("vision_runtime", roles)
        self.assertIn("voice_runtime", roles)
        self.assertIn("local_builder", roles)

    def test_register_service(self) -> None:
        from substrate.organism.service_dependency_graph import ServiceNode
        from substrate.organism.service_dependency_registry import (
            ServiceDependencyRegistry,
        )

        reg = ServiceDependencyRegistry(seed=False)
        reg.register_service(ServiceNode(service_role="test_svc"))
        self.assertIsNotNone(reg.get_service("test_svc"))

    def test_topology(self) -> None:
        from substrate.organism.service_dependency_registry import (
            ServiceDependencyRegistry,
        )

        reg = ServiceDependencyRegistry()
        topo = reg.topology()
        self.assertTrue(topo.topology_id.startswith("sdt-"))
        self.assertEqual(len(topo.services), 13)
        self.assertEqual(len(topo.dependencies), 15)


# ── Workcell C: Failure Engine ───────────────────────────────────────────


class TestServiceFailureEngine(unittest.TestCase):
    """Test ServiceFailureEngine — failure impact, critical path."""

    def test_governance_failure_impact(self) -> None:
        from substrate.organism.service_failure_engine import ServiceFailureEngine

        engine = ServiceFailureEngine()
        impact = engine.failure_impact("governance")
        self.assertGreater(impact.blast_radius, 0)
        self.assertIn("cockpit_api", impact.directly_affected)
        self.assertIn("distributed_runtime", impact.directly_affected)
        self.assertIn("action_bridge", impact.directly_affected)

    def test_governance_transitive(self) -> None:
        from substrate.organism.service_failure_engine import ServiceFailureEngine

        engine = ServiceFailureEngine()
        impact = engine.failure_impact("governance")
        all_affected = impact.directly_affected + impact.transitively_affected
        self.assertIn("cockpit_frontend", all_affected)

    def test_leaf_service_no_impact(self) -> None:
        from substrate.organism.service_failure_engine import ServiceFailureEngine

        engine = ServiceFailureEngine()
        impact = engine.failure_impact("vision_runtime")
        self.assertEqual(impact.blast_radius, 0)
        self.assertEqual(impact.severity, "low")

    def test_memory_failure_impact(self) -> None:
        from substrate.organism.service_failure_engine import ServiceFailureEngine

        engine = ServiceFailureEngine()
        impact = engine.failure_impact("memory")
        self.assertGreater(impact.blast_radius, 0)
        self.assertIn("cockpit_api", impact.directly_affected)
        self.assertIn("distributed_runtime", impact.directly_affected)

    def test_event_spine_failure(self) -> None:
        from substrate.organism.service_failure_engine import ServiceFailureEngine

        engine = ServiceFailureEngine()
        impact = engine.failure_impact("event_spine")
        self.assertGreater(impact.blast_radius, 0)
        self.assertIn("cockpit_api", impact.directly_affected)

    def test_affected_state_domains(self) -> None:
        from substrate.organism.service_failure_engine import ServiceFailureEngine

        engine = ServiceFailureEngine()
        impact = engine.failure_impact("governance")
        self.assertIn("governance", impact.affected_state_domains)

    def test_critical_path_ordered(self) -> None:
        from substrate.organism.service_failure_engine import ServiceFailureEngine

        engine = ServiceFailureEngine()
        path = engine.critical_path()
        self.assertGreater(len(path), 0)
        for i in range(len(path) - 1):
            self.assertGreaterEqual(
                path[i]["blast_radius"], path[i + 1]["blast_radius"]
            )

    def test_critical_path_event_spine_first(self) -> None:
        from substrate.organism.service_failure_engine import ServiceFailureEngine

        engine = ServiceFailureEngine()
        path = engine.critical_path()
        self.assertEqual(path[0]["service_role"], "event_spine")

    def test_leaf_services(self) -> None:
        from substrate.organism.service_failure_engine import ServiceFailureEngine

        engine = ServiceFailureEngine()
        leaves = engine.leaf_services()
        self.assertIn("vision_runtime", leaves)
        self.assertIn("voice_runtime", leaves)
        self.assertIn("local_builder", leaves)

    def test_service_health_map(self) -> None:
        from substrate.organism.service_failure_engine import ServiceFailureEngine

        engine = ServiceFailureEngine()
        health = engine.service_health_map()
        self.assertIn("cockpit_frontend", health)
        self.assertEqual(health["cockpit_frontend"], "blocked")

    def test_organism_health(self) -> None:
        from substrate.organism.service_failure_engine import ServiceFailureEngine

        engine = ServiceFailureEngine()
        health = engine.organism_health()
        self.assertEqual(health["total_services"], 13)
        self.assertEqual(health["total_dependencies"], 15)
        self.assertGreater(health["critical_count"], 0)
        self.assertGreater(health["leaf_count"], 0)

    def test_severity_classification(self) -> None:
        from substrate.organism.service_failure_engine import ServiceFailureEngine

        engine = ServiceFailureEngine()
        gov_impact = engine.failure_impact("governance")
        self.assertIn(gov_impact.severity, ["critical", "high", "medium"])
        leaf_impact = engine.failure_impact("vision_runtime")
        self.assertEqual(leaf_impact.severity, "low")


# ── Seed Data Consistency ────────────────────────────────────────────────


class TestSeedDataConsistency(unittest.TestCase):
    """Test seed data is internally consistent."""

    def test_all_services_present(self) -> None:
        from substrate.organism.service_dependency_registry import (
            ServiceDependencyRegistry,
        )

        reg = ServiceDependencyRegistry()
        self.assertEqual(len(reg.list_services()), 13)

    def test_services_match_umh_service_role(self) -> None:
        from substrate.organism.service_dependency_registry import (
            ServiceDependencyRegistry,
        )
        from substrate.organism.umh_node_topology import UMHServiceRole

        reg = ServiceDependencyRegistry()
        valid_roles = {e.value for e in UMHServiceRole}
        for svc in reg.list_services():
            self.assertIn(
                svc.service_role, valid_roles,
                f"Service {svc.service_role} not in UMHServiceRole",
            )

    def test_dependency_edges_reference_known_services(self) -> None:
        from substrate.organism.service_dependency_registry import (
            ServiceDependencyRegistry,
        )

        reg = ServiceDependencyRegistry()
        known = {s.service_role for s in reg.list_services()}
        topo = reg.topology()
        for dep in topo.dependencies:
            self.assertIn(dep.source_service, known, f"Unknown source: {dep.source_service}")
            self.assertIn(dep.target_service, known, f"Unknown target: {dep.target_service}")

    def test_no_self_dependencies(self) -> None:
        from substrate.organism.service_dependency_registry import (
            ServiceDependencyRegistry,
        )

        reg = ServiceDependencyRegistry()
        for dep in reg.topology().dependencies:
            self.assertNotEqual(
                dep.source_service, dep.target_service,
                f"Self-dependency: {dep.source_service}",
            )

    def test_no_duplicate_edges(self) -> None:
        from substrate.organism.service_dependency_registry import (
            ServiceDependencyRegistry,
        )

        reg = ServiceDependencyRegistry()
        edges = set()
        for dep in reg.topology().dependencies:
            edge = (dep.source_service, dep.target_service)
            self.assertNotIn(edge, edges, f"Duplicate edge: {edge}")
            edges.add(edge)

    def test_owner_nodes_valid(self) -> None:
        from substrate.organism.service_dependency_registry import (
            ServiceDependencyRegistry,
        )

        reg = ServiceDependencyRegistry()
        valid_nodes = {"umh-vps", "umh-windows"}
        for svc in reg.list_services():
            self.assertIn(
                svc.owner_node, valid_nodes,
                f"Service {svc.service_role} has invalid owner_node: {svc.owner_node}",
            )

    def test_state_domains_valid(self) -> None:
        from substrate.organism.service_dependency_registry import (
            ServiceDependencyRegistry,
        )
        from substrate.organism.state_authority_graph import StateDomain

        reg = ServiceDependencyRegistry()
        valid_domains = {e.value for e in StateDomain}
        for svc in reg.list_services():
            for domain in svc.state_domains:
                self.assertIn(
                    domain, valid_domains,
                    f"Service {svc.service_role} has invalid domain: {domain}",
                )

    def test_dependency_count(self) -> None:
        from substrate.organism.service_dependency_registry import (
            ServiceDependencyRegistry,
        )

        reg = ServiceDependencyRegistry()
        self.assertEqual(len(reg.topology().dependencies), 15)


# ── Cockpit Routes ──────────────────────────────────────────────────────


class TestCockpitRoutes(unittest.TestCase):
    """Test cockpit route module structure."""

    def test_import(self) -> None:
        from transports.api import cockpit_service_graph_routes

        self.assertIsNotNone(cockpit_service_graph_routes)

    def test_has_router(self) -> None:
        from transports.api.cockpit_service_graph_routes import service_graph_router

        self.assertIsNotNone(service_graph_router)

    def test_has_configure(self) -> None:
        from transports.api.cockpit_service_graph_routes import configure

        self.assertTrue(callable(configure))

    def test_singleton_pattern(self) -> None:
        from transports.api.cockpit_service_graph_routes import (
            _get_registry,
            _get_engine,
        )

        self.assertTrue(callable(_get_registry))
        self.assertTrue(callable(_get_engine))


# ── Type Registration ────────────────────────────────────────────────────


class TestTypeRegistration(unittest.TestCase):
    """Test Phase 30 types registered in canonical_types.py."""

    def test_all_types_registered(self) -> None:
        from substrate.canonical_types import CANONICAL_TYPES

        expected = [
            "DependencyStrength",
            "ServiceCriticality",
            "ServiceHealthImpact",
            "ServiceDependency",
            "ServiceNode",
            "FailureImpact",
            "ServiceDependencyTopology",
            "ServiceDependencyRegistry",
            "ServiceFailureEngine",
        ]
        for type_name in expected:
            self.assertIn(
                type_name, CANONICAL_TYPES,
                f"Type {type_name} not registered",
            )

    def test_type_count(self) -> None:
        from substrate.canonical_types import CANONICAL_TYPES

        phase30_types = [
            k for k, v in CANONICAL_TYPES.items()
            if any("service_dependency" in m or "service_failure" in m for m in v)
        ]
        self.assertEqual(len(phase30_types), 9)

    def test_lookup_returns_correct_module(self) -> None:
        from substrate.canonical_types import CANONICAL_TYPES

        self.assertIn(
            "substrate.organism.service_dependency_graph",
            CANONICAL_TYPES["ServiceNode"],
        )
        self.assertIn(
            "substrate.organism.service_failure_engine",
            CANONICAL_TYPES["ServiceFailureEngine"],
        )

    def test_no_collision_with_existing_types(self) -> None:
        from substrate.canonical_types import CANONICAL_TYPES

        phase30_names = {
            "DependencyStrength", "ServiceCriticality", "ServiceHealthImpact",
            "ServiceDependency", "ServiceNode", "FailureImpact",
            "ServiceDependencyTopology", "ServiceDependencyRegistry",
            "ServiceFailureEngine",
        }
        for name in phase30_names:
            paths = CANONICAL_TYPES[name]
            self.assertEqual(len(paths), 1, f"Type {name} has multiple paths: {paths}")


# ── Topology Stack Integration ───────────────────────────────────────────


class TestTopologyStackIntegration(unittest.TestCase):
    """Test full topology stack: workspace→node→state→service."""

    def test_registry_loads(self) -> None:
        from substrate.organism.service_dependency_registry import (
            ServiceDependencyRegistry,
        )

        reg = ServiceDependencyRegistry()
        self.assertEqual(len(reg.list_services()), 13)

    def test_engine_composes(self) -> None:
        from substrate.organism.service_failure_engine import ServiceFailureEngine

        engine = ServiceFailureEngine()
        health = engine.organism_health()
        self.assertEqual(health["total_services"], 13)

    def test_vps_services(self) -> None:
        from substrate.organism.service_dependency_registry import (
            ServiceDependencyRegistry,
        )

        reg = ServiceDependencyRegistry()
        vps = reg.services_for_node("umh-vps")
        roles = {s.service_role for s in vps}
        expected = {
            "cockpit_api", "cockpit_frontend", "governance",
            "memory", "event_spine", "distributed_runtime", "action_bridge",
        }
        self.assertEqual(roles, expected)

    def test_windows_services(self) -> None:
        from substrate.organism.service_dependency_registry import (
            ServiceDependencyRegistry,
        )

        reg = ServiceDependencyRegistry()
        win = reg.services_for_node("umh-windows")
        roles = {s.service_role for s in win}
        expected = {
            "meta_ide", "workspace_observation", "workstation_control",
            "local_builder", "vision_runtime", "voice_runtime",
        }
        self.assertEqual(roles, expected)

    def test_node_registry_services_subset(self) -> None:
        from substrate.organism.service_dependency_registry import (
            ServiceDependencyRegistry,
        )
        from substrate.organism.umh_node_registry import UMHNodeRegistry

        svc_reg = ServiceDependencyRegistry()
        node_reg = UMHNodeRegistry()

        for node in node_reg.list_nodes():
            node_service_roles = {s.service_role for s in node.active_services}
            svc_for_node = {s.service_role for s in svc_reg.services_for_node(node.node_id)}
            self.assertTrue(
                node_service_roles.issubset(svc_for_node),
                f"Node {node.node_id} active_services not subset of dependency registry: "
                f"missing {node_service_roles - svc_for_node}",
            )

    def test_state_service_owners_exist(self) -> None:
        from substrate.organism.service_dependency_registry import (
            ServiceDependencyRegistry,
        )
        from substrate.organism.state_registry import StateRegistry

        svc_reg = ServiceDependencyRegistry()
        state_reg = StateRegistry()

        for auth in state_reg.all_domains():
            if auth.service_owner:
                svc = svc_reg.get_service(auth.service_owner)
                self.assertIsNotNone(
                    svc,
                    f"State domain {auth.domain} references unknown service: {auth.service_owner}",
                )

    def test_failure_impact_has_event_spine_highest(self) -> None:
        from substrate.organism.service_failure_engine import ServiceFailureEngine

        engine = ServiceFailureEngine()
        path = engine.critical_path()
        self.assertEqual(path[0]["service_role"], "event_spine")

    def test_full_organism_health(self) -> None:
        from substrate.organism.service_failure_engine import ServiceFailureEngine

        engine = ServiceFailureEngine()
        health = engine.organism_health()
        self.assertIn("highest_risk_service", health)
        self.assertEqual(health["highest_risk_service"], "event_spine")

    def test_topology_id_prefix(self) -> None:
        from substrate.organism.service_dependency_registry import (
            ServiceDependencyRegistry,
        )

        reg = ServiceDependencyRegistry()
        topo = reg.topology()
        self.assertTrue(topo.topology_id.startswith("sdt-"))

    def test_to_dict_complete(self) -> None:
        from substrate.organism.service_dependency_registry import (
            ServiceDependencyRegistry,
        )

        reg = ServiceDependencyRegistry()
        d = reg.to_dict()
        self.assertEqual(d["service_count"], 13)
        self.assertEqual(d["dependency_count"], 15)
        self.assertIn("services", d)
        self.assertIn("dependencies", d)


# ── Cross-Layer Queries ──────────────────────────────────────────────────


class TestCrossLayerQueries(unittest.TestCase):
    """Test cross-layer queries between service, state, and node registries."""

    def test_services_for_memory_domain(self) -> None:
        from substrate.organism.service_dependency_registry import (
            ServiceDependencyRegistry,
        )

        reg = ServiceDependencyRegistry()
        services = reg.services_for_domain("memory")
        roles = [s.service_role for s in services]
        self.assertIn("memory", roles)

    def test_services_for_governance_domain(self) -> None:
        from substrate.organism.service_dependency_registry import (
            ServiceDependencyRegistry,
        )

        reg = ServiceDependencyRegistry()
        services = reg.services_for_domain("governance")
        roles = [s.service_role for s in services]
        self.assertIn("governance", roles)

    def test_services_for_workspace_domain(self) -> None:
        from substrate.organism.service_dependency_registry import (
            ServiceDependencyRegistry,
        )

        reg = ServiceDependencyRegistry()
        services = reg.services_for_domain("workspace")
        roles = [s.service_role for s in services]
        self.assertIn("workspace_observation", roles)

    def test_no_services_for_nonexistent_domain(self) -> None:
        from substrate.organism.service_dependency_registry import (
            ServiceDependencyRegistry,
        )

        reg = ServiceDependencyRegistry()
        services = reg.services_for_domain("nonexistent")
        self.assertEqual(len(services), 0)

    def test_governance_failure_affects_state_domains(self) -> None:
        from substrate.organism.service_failure_engine import ServiceFailureEngine

        engine = ServiceFailureEngine()
        impact = engine.failure_impact("governance")
        self.assertIn("governance", impact.affected_state_domains)
        self.assertIn("proof", impact.affected_state_domains)
        self.assertIn("reality", impact.affected_state_domains)


if __name__ == "__main__":
    unittest.main()
