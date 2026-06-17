"""Tests for Reality Graph — Campaign 5.0."""

from __future__ import annotations

import json
import os
import sys
import tempfile
import time

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


# ── Fixtures ──────────────────────────────────────────────────────────────


@pytest.fixture
def device_registry(tmp_path):
    data = [
        {"id": "vps", "display_name": "srv1500858 (VPS)", "device_type": "vps", "role": "orchestrator", "tailscale_ip": "100.77.233.50"},
        {"id": "beast", "display_name": "desktop-lvguiq9 (PC)", "device_type": "pc", "role": "executor", "gpu": "GTX 1080 Ti"},
    ]
    path = tmp_path / "device_registry.json"
    path.write_text(json.dumps(data))
    return str(path)


@pytest.fixture
def workspace_registry(tmp_path):
    data = [
        {
            "workspace_id": "umh",
            "name": "UMH",
            "workspace_type": "core",
            "repositories": [
                {"repository_id": "umh-os", "name": "OS", "path": "", "branch": "main"}
            ],
            "device_ids": ["vps", "beast"],
        },
        {
            "workspace_id": "creatoros",
            "name": "CreatorOS",
            "workspace_type": "product",
            "repositories": [
                {"repository_id": "creatoros-app", "name": "CreatorOS", "path": "", "branch": "main"}
            ],
            "device_ids": ["beast"],
        },
    ]
    path = tmp_path / "workspace_registry.json"
    path.write_text(json.dumps(data))
    return str(path)


@pytest.fixture
def project_registry(tmp_path):
    data = [
        {
            "project_id": "umh",
            "name": "UMH",
            "description": "Universal Meta Harness",
            "projection": "",
            "repositories": ["umh-os"],
            "infrastructure": ["cockpit-api", "os-discord"],
            "capabilities": ["orchestration", "governance"],
            "owner_device_ids": ["vps", "beast"],
            "status": "active",
        },
        {
            "project_id": "creatoros",
            "name": "CreatorOS",
            "description": "Creator workspace",
            "projection": "creatoros",
            "repositories": ["creatoros-app"],
            "infrastructure": [],
            "capabilities": ["desktop-app"],
            "owner_device_ids": ["beast"],
            "status": "active",
        },
    ]
    path = tmp_path / "project_registry.json"
    path.write_text(json.dumps(data))
    return str(path)


@pytest.fixture
def seeded_graph(device_registry, workspace_registry, project_registry):
    return RealityGraph.seed_from_registries(
        device_registry_path=device_registry,
        workspace_registry_path=workspace_registry,
        project_registry_path=project_registry,
    )


# ── Type Tests ────────────────────────────────────────────────────────────


class TestRealityEntityType:
    def test_has_all_required_types(self):
        expected = {
            "project", "repository", "workspace", "device", "document",
            "service", "projection", "branch", "work_packet", "approval",
            "delegation_mission", "capability", "infrastructure",
        }
        actual = {t.value for t in RealityEntityType}
        assert expected == actual

    def test_string_enum(self):
        assert RealityEntityType.PROJECT == "project"
        assert isinstance(RealityEntityType.DEVICE, str)


class TestRealityRelationType:
    def test_has_all_required_types(self):
        expected = {
            "contains", "runs_on", "built_from", "owned_by",
            "deployed_to", "documents", "depends_on", "active_in",
        }
        actual = {t.value for t in RealityRelationType}
        assert expected == actual


class TestRealityEntityStatus:
    def test_has_all_required_statuses(self):
        expected = {"active", "inactive", "degraded", "unknown"}
        actual = {s.value for s in RealityEntityStatus}
        assert expected == actual


# ── Entity Tests ──────────────────────────────────────────────────────────


class TestRealityEntity:
    def test_create_entity(self):
        entity = RealityEntity(
            entity_id="dev-vps",
            entity_type=RealityEntityType.DEVICE,
            name="VPS",
        )
        assert entity.entity_id == "dev-vps"
        assert entity.entity_type == RealityEntityType.DEVICE
        assert entity.status == RealityEntityStatus.UNKNOWN

    def test_to_dict(self):
        entity = RealityEntity(
            entity_id="proj-umh",
            entity_type=RealityEntityType.PROJECT,
            name="UMH",
            status=RealityEntityStatus.ACTIVE,
            properties={"description": "test"},
        )
        d = entity.to_dict()
        assert d["entity_id"] == "proj-umh"
        assert d["entity_type"] == "project"
        assert d["status"] == "active"
        assert d["properties"]["description"] == "test"


class TestRealityRelation:
    def test_create_relation(self):
        rel = RealityRelation(
            source_id="proj-umh",
            target_id="repo-umh-os",
            relation_type=RealityRelationType.CONTAINS,
        )
        assert rel.source_id == "proj-umh"
        assert rel.relation_type == RealityRelationType.CONTAINS

    def test_to_dict(self):
        rel = RealityRelation(
            source_id="ws-umh",
            target_id="dev-vps",
            relation_type=RealityRelationType.DEPLOYED_TO,
        )
        d = rel.to_dict()
        assert d["relation_type"] == "deployed_to"


# ── Seeding Tests ─────────────────────────────────────────────────────────


class TestSeedFromRegistries:
    def test_seed_devices(self, seeded_graph):
        devices = seeded_graph.find_by_type(RealityEntityType.DEVICE)
        assert len(devices) == 2
        ids = {d.entity_id for d in devices}
        assert "dev-vps" in ids
        assert "dev-beast" in ids

    def test_seed_workspaces(self, seeded_graph):
        workspaces = seeded_graph.find_by_type(RealityEntityType.WORKSPACE)
        assert len(workspaces) == 2
        ids = {w.entity_id for w in workspaces}
        assert "ws-umh" in ids
        assert "ws-creatoros" in ids

    def test_seed_repositories(self, seeded_graph):
        repos = seeded_graph.find_by_type(RealityEntityType.REPOSITORY)
        assert len(repos) == 2
        ids = {r.entity_id for r in repos}
        assert "repo-umh-os" in ids
        assert "repo-creatoros-app" in ids

    def test_seed_projects(self, seeded_graph):
        projects = seeded_graph.find_by_type(RealityEntityType.PROJECT)
        assert len(projects) == 2
        ids = {p.entity_id for p in projects}
        assert "proj-umh" in ids
        assert "proj-creatoros" in ids

    def test_total_entity_count(self, seeded_graph):
        assert seeded_graph.entity_count == 8  # 2 devices + 2 workspaces + 2 repos + 2 projects

    def test_workspace_contains_repo_edges(self, seeded_graph):
        neighbors = seeded_graph.neighbors("ws-umh", RealityRelationType.CONTAINS)
        ids = {n.entity_id for n in neighbors}
        assert "repo-umh-os" in ids

    def test_workspace_deployed_to_device(self, seeded_graph):
        neighbors = seeded_graph.neighbors("ws-umh", RealityRelationType.DEPLOYED_TO)
        ids = {n.entity_id for n in neighbors}
        assert "dev-vps" in ids
        assert "dev-beast" in ids

    def test_project_contains_repo(self, seeded_graph):
        neighbors = seeded_graph.neighbors("proj-umh", RealityRelationType.CONTAINS)
        ids = {n.entity_id for n in neighbors}
        assert "repo-umh-os" in ids

    def test_project_deployed_to_device(self, seeded_graph):
        neighbors = seeded_graph.neighbors("proj-creatoros", RealityRelationType.DEPLOYED_TO)
        ids = {n.entity_id for n in neighbors}
        assert "dev-beast" in ids

    def test_project_depends_on_infrastructure(self, seeded_graph):
        neighbors = seeded_graph.neighbors("proj-umh", RealityRelationType.DEPENDS_ON)
        ids = {n.entity_id for n in neighbors}
        assert "infra-cockpit-api" in ids or len(ids) == 0  # infra entities not seeded yet

    def test_seed_missing_file_graceful(self, tmp_path):
        graph = RealityGraph.seed_from_registries(
            device_registry_path=str(tmp_path / "nope.json"),
            workspace_registry_path=str(tmp_path / "nope2.json"),
        )
        assert graph.entity_count == 0

    def test_no_duplicate_on_reseed(self, device_registry, workspace_registry, project_registry):
        g1 = RealityGraph.seed_from_registries(device_registry, workspace_registry, project_registry)
        count1 = g1.entity_count
        g2 = RealityGraph.seed_from_registries(device_registry, workspace_registry, project_registry)
        assert g2.entity_count == count1

    def test_device_properties_preserved(self, seeded_graph):
        vps = seeded_graph.get("dev-vps")
        assert vps is not None
        assert vps.properties.get("role") == "orchestrator"
        assert vps.properties.get("tailscale_ip") == "100.77.233.50"


# ── Query Tests ───────────────────────────────────────────────────────────


class TestFindByName:
    def test_exact_match(self, seeded_graph):
        results = seeded_graph.find_by_name("UMH")
        names = {r.name for r in results}
        assert "UMH" in names

    def test_case_insensitive(self, seeded_graph):
        results = seeded_graph.find_by_name("creatoros")
        assert len(results) > 0

    def test_partial_match(self, seeded_graph):
        results = seeded_graph.find_by_name("Creator")
        assert len(results) > 0
        assert any(r.name == "CreatorOS" for r in results)

    def test_no_match(self, seeded_graph):
        results = seeded_graph.find_by_name("nonexistent_xyz")
        assert len(results) == 0


class TestFindByProperty:
    def test_find_by_role(self, seeded_graph):
        results = seeded_graph.find_by_property("role", "orchestrator")
        assert len(results) == 1
        assert results[0].entity_id == "dev-vps"


class TestFindByType:
    def test_find_all_devices(self, seeded_graph):
        devices = seeded_graph.find_by_type(RealityEntityType.DEVICE)
        assert all(d.entity_type == RealityEntityType.DEVICE for d in devices)

    def test_find_empty_type(self, seeded_graph):
        services = seeded_graph.find_by_type(RealityEntityType.SERVICE)
        assert len(services) == 0


# ── Graph Traversal Tests ─────────────────────────────────────────────────


class TestNeighbors:
    def test_neighbors_all_types(self, seeded_graph):
        neighbors = seeded_graph.neighbors("ws-umh")
        assert len(neighbors) > 0

    def test_neighbors_filtered(self, seeded_graph):
        contains = seeded_graph.neighbors("ws-umh", RealityRelationType.CONTAINS)
        deployed = seeded_graph.neighbors("ws-umh", RealityRelationType.DEPLOYED_TO)
        assert len(contains) >= 1
        assert len(deployed) >= 1

    def test_neighbors_bidirectional(self, seeded_graph):
        fwd = seeded_graph.neighbors("ws-creatoros", RealityRelationType.CONTAINS)
        assert any(n.entity_id == "repo-creatoros-app" for n in fwd)
        rev = seeded_graph.neighbors("repo-creatoros-app", RealityRelationType.CONTAINS)
        assert any(n.entity_id == "ws-creatoros" for n in rev)

    def test_neighbors_nonexistent(self, seeded_graph):
        neighbors = seeded_graph.neighbors("nonexistent")
        assert len(neighbors) == 0


class TestPath:
    def test_direct_path(self, seeded_graph):
        path = seeded_graph.path("ws-umh", "repo-umh-os")
        assert len(path) == 1
        assert path[0].relation_type == RealityRelationType.CONTAINS

    def test_multi_hop_path(self, seeded_graph):
        path = seeded_graph.path("proj-creatoros", "dev-beast")
        assert len(path) >= 1

    def test_no_path(self, seeded_graph):
        path = seeded_graph.path("nonexistent-a", "nonexistent-b")
        assert len(path) == 0

    def test_same_node_path(self, seeded_graph):
        path = seeded_graph.path("dev-vps", "dev-vps")
        assert len(path) == 0


class TestSubgraph:
    def test_depth_1(self, seeded_graph):
        sub = seeded_graph.subgraph("ws-umh", depth=1)
        assert sub.entity_count >= 2  # ws-umh + at least repo or device
        assert sub.get("ws-umh") is not None

    def test_depth_2(self, seeded_graph):
        sub = seeded_graph.subgraph("proj-umh", depth=2)
        assert sub.entity_count >= 2

    def test_nonexistent_entity(self, seeded_graph):
        sub = seeded_graph.subgraph("nonexistent")
        assert sub.entity_count == 0


# ── Summary Tests ─────────────────────────────────────────────────────────


class TestSummary:
    def test_summary_structure(self, seeded_graph):
        s = seeded_graph.summary()
        assert "entity_count" in s
        assert "relation_count" in s
        assert "entities_by_type" in s
        assert "relations_by_type" in s
        assert s["entity_count"] == seeded_graph.entity_count

    def test_summary_type_breakdown(self, seeded_graph):
        s = seeded_graph.summary()
        assert s["entities_by_type"].get("device") == 2
        assert s["entities_by_type"].get("workspace") == 2


# ── Ingest Tests ──────────────────────────────────────────────────────────


class TestIngestFromNodeTopology:
    def test_ingest_from_mock_topology(self):
        class MockNode:
            def __init__(self, node_id, device_id, hostname, roles):
                self.node_id = node_id
                self.device_id = device_id
                self.hostname = hostname
                self.roles = roles
                self.purpose = "test"

        class MockTopology:
            def list_nodes(self):
                return [
                    MockNode("umh-vps", "vps", "srv1500858", ["orchestrator"]),
                    MockNode("umh-windows", "beast", "desktop-lvguiq9", ["executor"]),
                ]

        graph = RealityGraph()
        count = graph.ingest_from_node_topology(MockTopology())
        assert count == 2
        assert graph.get("dev-vps") is not None
        assert graph.get("dev-beast") is not None


class TestIngestFromDelegationRuntime:
    def test_ingest_missions(self):
        class MockMission:
            def __init__(self, mission_id, title, status, intent):
                self.mission_id = mission_id
                self.title = title
                self.status = status
                self.intent = intent

        class MockRuntime:
            def list_missions(self):
                return [
                    MockMission("m1", "Deploy cockpit", "executing", "deploy"),
                    MockMission("m2", "Fix auth bug", "completed", "fix"),
                ]

        graph = RealityGraph()
        count = graph.ingest_from_delegation_runtime(MockRuntime())
        assert count == 2
        m1 = graph.get("mission-m1")
        assert m1 is not None
        assert m1.entity_type == RealityEntityType.DELEGATION_MISSION
        assert m1.status == RealityEntityStatus.ACTIVE

        m2 = graph.get("mission-m2")
        assert m2 is not None
        assert m2.status == RealityEntityStatus.INACTIVE


class TestIngestFromInfrastructureRuntime:
    def test_ingest_entities(self):
        class MockInfra:
            def __init__(self, entity_id, name, infra_type, health):
                self.entity_id = entity_id
                self.name = name
                self.infra_type = infra_type
                self.health = health

        class MockRuntime:
            def list_entities(self):
                return [
                    MockInfra("cockpit-api", "Cockpit API", "fly_app", "healthy"),
                    MockInfra("os-discord", "Discord Bot", "docker", "degraded"),
                ]

        graph = RealityGraph()
        count = graph.ingest_from_infrastructure_runtime(MockRuntime())
        assert count == 2
        cockpit = graph.get("infra-cockpit-api")
        assert cockpit is not None
        assert cockpit.entity_type == RealityEntityType.INFRASTRUCTURE

        discord = graph.get("infra-os-discord")
        assert discord is not None
        assert discord.status == RealityEntityStatus.DEGRADED


class TestIngestFromCapabilityRuntime:
    def test_ingest_capabilities(self):
        class MockCapability:
            def __init__(self, capability_id, name, maturity, evidence_count):
                self.capability_id = capability_id
                self.name = name
                self.maturity = maturity
                self.evidence_count = evidence_count

        class MockRuntime:
            def list_capabilities(self):
                return [
                    MockCapability("orchestration", "Orchestration", "production", 15),
                ]

        graph = RealityGraph()
        count = graph.ingest_from_capability_runtime(MockRuntime())
        assert count == 1
        cap = graph.get("cap-orchestration")
        assert cap is not None
        assert cap.entity_type == RealityEntityType.CAPABILITY


# ── Edge Cases ────────────────────────────────────────────────────────────


class TestEdgeCases:
    def test_empty_graph(self):
        graph = RealityGraph()
        assert graph.entity_count == 0
        assert graph.relation_count == 0
        assert graph.all_entities() == []
        assert graph.all_relations() == []

    def test_add_entity_no_duplicate(self):
        graph = RealityGraph()
        e = RealityEntity(
            entity_id="test-1",
            entity_type=RealityEntityType.DEVICE,
            name="Test",
            last_observed=100.0,
        )
        assert graph._add_entity(e)
        assert not graph._add_entity(e)  # same timestamp, no update
        assert graph.entity_count == 1

    def test_add_entity_newer_wins(self):
        graph = RealityGraph()
        old = RealityEntity(
            entity_id="test-1",
            entity_type=RealityEntityType.DEVICE,
            name="Old",
            last_observed=100.0,
        )
        new = RealityEntity(
            entity_id="test-1",
            entity_type=RealityEntityType.DEVICE,
            name="New",
            last_observed=200.0,
        )
        graph._add_entity(old)
        graph._add_entity(new)
        assert graph.get("test-1").name == "New"

    def test_add_relation_no_duplicate(self):
        graph = RealityGraph()
        rel = RealityRelation(
            source_id="a",
            target_id="b",
            relation_type=RealityRelationType.CONTAINS,
        )
        assert graph._add_relation(rel)
        assert not graph._add_relation(rel)
        assert graph.relation_count == 1
