"""Tests for Gate 7 — Infrastructure Runtime.

Verifies:
- Types: InfrastructureType, InfrastructureHealth, InfrastructureEntity
- System vs institutional classification
- InfrastructureRuntime: register, get, list, lineage, health, dependencies
- Sync from existing systems
- Persistence: JSONL roundtrip
- Type coherence: canonical_types registration
- Routes: cockpit route mounting
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.environ.get("UMH_ROOT", "/opt/OS"))


class TestTypes(unittest.TestCase):
    def test_infrastructure_type_enum(self) -> None:
        from substrate.organism.infrastructure_runtime import InfrastructureType

        assert InfrastructureType.RUNTIME.value == "runtime"
        assert InfrastructureType.COMPANY.value == "company"
        assert len(InfrastructureType) == 12

    def test_infrastructure_health_enum(self) -> None:
        from substrate.organism.infrastructure_runtime import InfrastructureHealth

        assert InfrastructureHealth.HEALTHY.value == "healthy"
        assert InfrastructureHealth.FAILING.value == "failing"
        assert len(InfrastructureHealth) == 4

    def test_entity_creation(self) -> None:
        from substrate.organism.infrastructure_runtime import InfrastructureEntity

        ent = InfrastructureEntity(name="test runtime")
        assert ent.name == "test runtime"
        assert ent.infrastructure_id.startswith("infra-")

    def test_entity_to_dict(self) -> None:
        from substrate.organism.infrastructure_runtime import InfrastructureEntity

        ent = InfrastructureEntity(name="test")
        d = ent.to_dict()
        assert d["name"] == "test"
        assert d["infra_type"] == "runtime"
        assert d["health"] == "unknown"
        assert "is_system" in d
        assert "is_institutional" in d

    def test_entity_from_dict(self) -> None:
        from substrate.organism.infrastructure_runtime import (
            InfrastructureEntity,
            InfrastructureType,
        )

        d = {
            "infrastructure_id": "infra-abc",
            "name": "spine",
            "infra_type": "execution_spine",
        }
        ent = InfrastructureEntity.from_dict(d)
        assert ent.infrastructure_id == "infra-abc"
        assert ent.infra_type == InfrastructureType.EXECUTION_SPINE

    def test_invalid_type_defaults(self) -> None:
        from substrate.organism.infrastructure_runtime import (
            InfrastructureEntity,
            InfrastructureType,
        )

        ent = InfrastructureEntity.from_dict({"infra_type": "invalid"})
        assert ent.infra_type == InfrastructureType.RUNTIME

    def test_invalid_health_defaults(self) -> None:
        from substrate.organism.infrastructure_runtime import (
            InfrastructureEntity,
            InfrastructureHealth,
        )

        ent = InfrastructureEntity.from_dict({"health": "bogus"})
        assert ent.health == InfrastructureHealth.UNKNOWN


class TestClassification(unittest.TestCase):
    def test_system_types(self) -> None:
        from substrate.organism.infrastructure_runtime import (
            InfrastructureEntity,
            InfrastructureType,
        )

        for it in [
            InfrastructureType.RUNTIME,
            InfrastructureType.ADAPTER,
            InfrastructureType.EXECUTION_SPINE,
            InfrastructureType.GOVERNANCE_SYSTEM,
        ]:
            ent = InfrastructureEntity(infra_type=it)
            assert ent.is_system, f"{it} should be system"
            assert not ent.is_institutional

    def test_institutional_types(self) -> None:
        from substrate.organism.infrastructure_runtime import (
            InfrastructureEntity,
            InfrastructureType,
        )

        for it in [
            InfrastructureType.COMPANY,
            InfrastructureType.MEDIA_ENGINE,
            InfrastructureType.SCHOOL,
            InfrastructureType.CAPITAL_STRUCTURE,
        ]:
            ent = InfrastructureEntity(infra_type=it)
            assert ent.is_institutional, f"{it} should be institutional"
            assert not ent.is_system


class TestInfrastructureRuntime(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.mkdtemp()
        self._path = os.path.join(self._tmp, "infrastructure.jsonl")

    def _make_runtime(self) -> "InfrastructureRuntime":
        from substrate.organism.infrastructure_runtime import InfrastructureRuntime

        return InfrastructureRuntime(store_path=self._path)

    def test_register_and_get(self) -> None:
        from substrate.organism.infrastructure_runtime import InfrastructureType

        rt = self._make_runtime()
        ent = rt.register(name="test", infra_type=InfrastructureType.RUNTIME)
        assert ent.name == "test"
        fetched = rt.get(ent.infrastructure_id)
        assert fetched is not None
        assert fetched.name == "test"

    def test_get_nonexistent(self) -> None:
        rt = self._make_runtime()
        assert rt.get("nonexistent") is None

    def test_list_all(self) -> None:
        from substrate.organism.infrastructure_runtime import InfrastructureType

        rt = self._make_runtime()
        rt.register(name="a", infra_type=InfrastructureType.RUNTIME)
        rt.register(name="b", infra_type=InfrastructureType.COMPANY)
        assert len(rt.list_entities()) == 2

    def test_list_by_type(self) -> None:
        from substrate.organism.infrastructure_runtime import InfrastructureType

        rt = self._make_runtime()
        rt.register(name="a", infra_type=InfrastructureType.RUNTIME)
        rt.register(name="b", infra_type=InfrastructureType.COMPANY)
        runtimes = rt.list_entities(infra_type=InfrastructureType.RUNTIME)
        assert len(runtimes) == 1
        assert runtimes[0].name == "a"

    def test_list_system_only(self) -> None:
        from substrate.organism.infrastructure_runtime import InfrastructureType

        rt = self._make_runtime()
        rt.register(name="a", infra_type=InfrastructureType.RUNTIME)
        rt.register(name="b", infra_type=InfrastructureType.COMPANY)
        systems = rt.list_entities(system_only=True)
        assert len(systems) == 1
        assert systems[0].name == "a"

    def test_list_institutional_only(self) -> None:
        from substrate.organism.infrastructure_runtime import InfrastructureType

        rt = self._make_runtime()
        rt.register(name="a", infra_type=InfrastructureType.RUNTIME)
        rt.register(name="b", infra_type=InfrastructureType.COMPANY)
        inst = rt.list_entities(institutional_only=True)
        assert len(inst) == 1
        assert inst[0].name == "b"

    def test_full_lineage(self) -> None:
        from substrate.organism.infrastructure_runtime import InfrastructureType

        rt = self._make_runtime()
        ent = rt.register(
            name="spine",
            infra_type=InfrastructureType.EXECUTION_SPINE,
            origin_capability_ids=["cap-1"],
            operationalization_ids=["op-1"],
        )
        lineage = rt.full_lineage(ent.infrastructure_id)
        assert lineage["name"] == "spine"
        assert "cap-1" in lineage["origin_capability_ids"]

    def test_full_lineage_nonexistent(self) -> None:
        rt = self._make_runtime()
        result = rt.full_lineage("nope")
        assert "error" in result

    def test_update_health(self) -> None:
        from substrate.organism.infrastructure_runtime import (
            InfrastructureHealth,
            InfrastructureType,
        )

        rt = self._make_runtime()
        ent = rt.register(name="test", infra_type=InfrastructureType.RUNTIME)
        assert rt.update_health(ent.infrastructure_id, InfrastructureHealth.HEALTHY)
        assert rt.get(ent.infrastructure_id).health == InfrastructureHealth.HEALTHY

    def test_update_health_nonexistent(self) -> None:
        from substrate.organism.infrastructure_runtime import InfrastructureHealth

        rt = self._make_runtime()
        assert rt.update_health("nope", InfrastructureHealth.HEALTHY) is False

    def test_health_check(self) -> None:
        from substrate.organism.infrastructure_runtime import (
            InfrastructureHealth,
            InfrastructureType,
        )

        rt = self._make_runtime()
        rt.register(
            name="a",
            infra_type=InfrastructureType.RUNTIME,
            health=InfrastructureHealth.HEALTHY,
        )
        rt.register(
            name="b",
            infra_type=InfrastructureType.ADAPTER,
            health=InfrastructureHealth.FAILING,
        )
        hc = rt.health_check()
        assert hc["total"] == 2
        assert len(hc["failing"]) == 1
        assert hc["healthy_rate"] == 0.5

    def test_add_dependency(self) -> None:
        from substrate.organism.infrastructure_runtime import InfrastructureType

        rt = self._make_runtime()
        a = rt.register(name="a", infra_type=InfrastructureType.RUNTIME)
        b = rt.register(name="b", infra_type=InfrastructureType.ADAPTER)
        assert rt.add_dependency(b.infrastructure_id, a.infrastructure_id)
        assert a.infrastructure_id in rt.dependencies_of(b.infrastructure_id)
        assert b.infrastructure_id in rt.dependents_of(a.infrastructure_id)

    def test_add_dependency_nonexistent(self) -> None:
        rt = self._make_runtime()
        assert rt.add_dependency("x", "y") is False

    def test_summary(self) -> None:
        from substrate.organism.infrastructure_runtime import InfrastructureType

        rt = self._make_runtime()
        rt.register(name="a", infra_type=InfrastructureType.RUNTIME)
        rt.register(name="b", infra_type=InfrastructureType.COMPANY)
        s = rt.summary()
        assert s["total_infrastructure"] == 2
        assert s["system_count"] == 1
        assert s["institutional_count"] == 1

    def test_sync_from_service_graph(self) -> None:
        rt = self._make_runtime()
        count = rt.sync_from_service_graph()
        assert isinstance(count, int)

    def test_sync_from_node_registry(self) -> None:
        rt = self._make_runtime()
        count = rt.sync_from_node_registry()
        assert isinstance(count, int)


class TestPersistence(unittest.TestCase):
    def test_jsonl_roundtrip(self) -> None:
        from substrate.organism.infrastructure_runtime import (
            InfrastructureRuntime,
            InfrastructureType,
        )

        tmp = tempfile.mkdtemp()
        path = os.path.join(tmp, "infrastructure.jsonl")
        r1 = InfrastructureRuntime(store_path=path)
        r1.register(name="a", infra_type=InfrastructureType.RUNTIME)
        r1.register(name="b", infra_type=InfrastructureType.COMPANY)

        r2 = InfrastructureRuntime(store_path=path)
        assert len(r2.list_entities()) == 2

    def test_malformed_jsonl_skipped(self) -> None:
        from substrate.organism.infrastructure_runtime import InfrastructureRuntime

        tmp = tempfile.mkdtemp()
        path = os.path.join(tmp, "infrastructure.jsonl")
        with open(path, "w") as f:
            f.write("not valid json\n")
            f.write(json.dumps({"infrastructure_id": "infra-ok", "name": "valid"}) + "\n")

        r = InfrastructureRuntime(store_path=path)
        assert len(r.list_entities()) == 1


class TestTypeCoherence(unittest.TestCase):
    def test_canonical_types_registered(self) -> None:
        from substrate.canonical_types import CANONICAL_TYPES

        for name in [
            "InfrastructureType",
            "InfrastructureHealth",
            "InfrastructureEntity",
            "InfrastructureRuntime",
        ]:
            assert name in CANONICAL_TYPES, f"{name} not in canonical_types"
            assert "substrate.organism.infrastructure_runtime" in CANONICAL_TYPES[name]


class TestRoutes(unittest.TestCase):
    def test_routes_importable(self) -> None:
        from transports.api.cockpit_infrastructure_routes import (
            infrastructure_router,
        )

        assert infrastructure_router is not None

    def test_cockpit_mounts_infrastructure_routes(self) -> None:
        import transports.api.cockpit as c

        route_paths = [r.path for r in c.router.routes]
        assert any("/infrastructure" in p for p in route_paths)
        assert any("/infrastructure/summary" in p for p in route_paths)
        assert any("/infrastructure/health" in p for p in route_paths)


if __name__ == "__main__":
    unittest.main()
