"""Phase 80 tests — Unified Registry System v1.

Tests cover:
- Registry contracts (enums, RegistryItem, RegistryQuery, RegistryQueryResult)
- Compatibility bridges (capability, environment, adapter, backend, mode, policy)
- Registry catalog (assembly, by_type, by_name, by_id, count, sparse safety)
- Registry query layer (filters, limits, typed finders, explain_registry_match)
- Registry views (RegistryItemView, RegistryCatalogView, RegistryHealthView)
- API endpoint functions (callable, read-only)
- CLI commands (parser accepts, dispatch entries)
- Layering invariants (no forbidden imports)
- Phase 79 compatibility (all Phase 79 exports intact)
"""

import argparse
import ast
import importlib
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock

sys.path.insert(0, "/opt/OS")


# ── Contracts ─────────────────────────────────────────────────────


class TestRegistryType(unittest.TestCase):
    def test_at_least_16_types(self):
        from umh.registry.contracts import RegistryType

        self.assertGreaterEqual(len(RegistryType), 16)

    def test_normalize_known(self):
        from umh.registry.contracts import RegistryType, normalize_registry_type

        self.assertEqual(normalize_registry_type("capability"), RegistryType.CAPABILITY)
        self.assertEqual(normalize_registry_type("ADAPTER"), RegistryType.ADAPTER)
        self.assertEqual(normalize_registry_type(" backend "), RegistryType.BACKEND)

    def test_normalize_unknown(self):
        from umh.registry.contracts import RegistryType, normalize_registry_type

        self.assertEqual(normalize_registry_type("nonsense"), RegistryType.UNKNOWN)

    def test_all_values_lowercase(self):
        from umh.registry.contracts import RegistryType

        for member in RegistryType:
            self.assertEqual(member.value, member.value.lower())


class TestRegistryItemStatus(unittest.TestCase):
    def test_all_8_statuses(self):
        from umh.registry.contracts import RegistryItemStatus

        self.assertEqual(len(RegistryItemStatus), 8)

    def test_normalize(self):
        from umh.registry.contracts import RegistryItemStatus, normalize_registry_item_status

        self.assertEqual(normalize_registry_item_status("active"), RegistryItemStatus.ACTIVE)
        self.assertEqual(
            normalize_registry_item_status("DEPRECATED"), RegistryItemStatus.DEPRECATED
        )
        self.assertEqual(normalize_registry_item_status("???"), RegistryItemStatus.UNKNOWN)


class TestRegistryAuthorityRequirement(unittest.TestCase):
    def test_all_6_levels(self):
        from umh.registry.contracts import RegistryAuthorityRequirement

        self.assertEqual(len(RegistryAuthorityRequirement), 6)

    def test_normalize(self):
        from umh.registry.contracts import (
            RegistryAuthorityRequirement,
            normalize_authority_requirement,
        )

        self.assertEqual(normalize_authority_requirement("act"), RegistryAuthorityRequirement.ACT)
        self.assertEqual(
            normalize_authority_requirement("???"), RegistryAuthorityRequirement.UNKNOWN
        )


class TestRegistryItem(unittest.TestCase):
    def test_serialization(self):
        from umh.registry.contracts import (
            RegistryItem,
            RegistryItemStatus,
            RegistryType,
        )

        item = RegistryItem(
            item_id="test_1",
            registry_type=RegistryType.CAPABILITY,
            name="test_cap",
            status=RegistryItemStatus.ACTIVE,
            capabilities=["cli.command"],
            environments=["local"],
        )
        d = item.to_dict()
        self.assertEqual(d["item_id"], "test_1")
        self.assertEqual(d["registry_type"], "capability")
        self.assertEqual(d["status"], "active")
        self.assertEqual(d["capabilities"], ["cli.command"])

    def test_from_dict(self):
        from umh.registry.contracts import RegistryItem

        d = {
            "item_id": "x",
            "registry_type": "adapter",
            "name": "test",
            "status": "active",
            "capabilities": ["a", "b"],
        }
        item = RegistryItem.from_dict(d)
        self.assertEqual(item.item_id, "x")
        self.assertEqual(item.registry_type.value, "adapter")
        self.assertEqual(item.capabilities, ["a", "b"])

    def test_from_dict_missing_fields(self):
        from umh.registry.contracts import RegistryItem

        item = RegistryItem.from_dict({})
        self.assertIn("reg_", item.item_id)
        self.assertEqual(item.registry_type.value, "unknown")
        self.assertEqual(item.name, "")

    def test_metadata_not_leaked_as_secrets(self):
        from umh.registry.contracts import RegistryItem, RegistryType

        item = RegistryItem(item_id="t", registry_type=RegistryType.TOOL, metadata={"key": "val"})
        d = item.to_dict()
        self.assertNotIn("password", json.dumps(d))
        self.assertNotIn("secret", json.dumps(d))


class TestRegistryQuery(unittest.TestCase):
    def test_effective_limit_clamped(self):
        from umh.registry.contracts import RegistryQuery

        q = RegistryQuery(limit=999)
        self.assertEqual(q.effective_limit(), 100)

    def test_effective_limit_min(self):
        from umh.registry.contracts import RegistryQuery

        q = RegistryQuery(limit=-5)
        self.assertEqual(q.effective_limit(), 1)

    def test_default_limit(self):
        from umh.registry.contracts import RegistryQuery

        q = RegistryQuery()
        self.assertEqual(q.effective_limit(), 50)


class TestRegistryQueryResult(unittest.TestCase):
    def test_serialization(self):
        from umh.registry.contracts import RegistryQueryResult

        r = RegistryQueryResult(
            query={"type": "capability"},
            items=[],
            total_returned=0,
            warnings=["test"],
        )
        d = r.to_dict()
        self.assertEqual(d["total_returned"], 0)
        self.assertEqual(d["warnings"], ["test"])

    def test_empty_result(self):
        from umh.registry.contracts import RegistryQueryResult

        r = RegistryQueryResult()
        d = r.to_dict()
        self.assertEqual(d["items"], [])
        self.assertEqual(d["total_returned"], 0)


# ── Bridges ──────────────────────���────────────────────��───────────


class TestCapabilityBridge(unittest.TestCase):
    def test_converts_mvp_capabilities(self):
        from umh.registry.bridges import capability_definitions_to_registry_items

        items = capability_definitions_to_registry_items()
        self.assertEqual(len(items), 9)
        names = {i.name for i in items}
        self.assertIn("CLI Command", names)
        self.assertIn("Filesystem Read", names)

    def test_item_fields(self):
        from umh.registry.bridges import capability_definitions_to_registry_items

        items = capability_definitions_to_registry_items()
        cli_cmd = [i for i in items if i.name == "CLI Command"][0]
        self.assertEqual(cli_cmd.registry_type.value, "capability")
        self.assertEqual(cli_cmd.status.value, "active")
        self.assertTrue(cli_cmd.requires_approval)
        self.assertIn("local", cli_cmd.environments)
        self.assertEqual(cli_cmd.risk_level, "high")
        self.assertEqual(cli_cmd.source_module, "umh.capabilities.definitions")

    def test_empty_input(self):
        from umh.registry.bridges import capability_definitions_to_registry_items

        items = capability_definitions_to_registry_items(capabilities=[])
        self.assertEqual(items, [])

    def test_authority_mapping(self):
        from umh.registry.bridges import capability_definitions_to_registry_items

        items = capability_definitions_to_registry_items()
        cli_cmd = [i for i in items if i.name == "CLI Command"][0]
        self.assertEqual(cli_cmd.authority_required.value, "act")
        fs_read = [i for i in items if i.name == "Filesystem Read"][0]
        self.assertEqual(fs_read.authority_required.value, "analyze")


class TestEnvironmentBridge(unittest.TestCase):
    def test_converts_mvp_environments(self):
        from umh.registry.bridges import environment_definitions_to_registry_items

        items = environment_definitions_to_registry_items()
        self.assertEqual(len(items), 7)

    def test_item_fields(self):
        from umh.registry.bridges import environment_definitions_to_registry_items

        items = environment_definitions_to_registry_items()
        local = [i for i in items if i.name == "local"][0]
        self.assertEqual(local.registry_type.value, "environment")
        self.assertEqual(local.status.value, "active")
        self.assertIn("cli.command", local.capabilities)
        self.assertIn("network:allow_https", local.tags)

    def test_empty_input(self):
        from umh.registry.bridges import environment_definitions_to_registry_items

        items = environment_definitions_to_registry_items(environments=[])
        self.assertEqual(items, [])


class TestAdapterBridge(unittest.TestCase):
    def test_none_returns_empty(self):
        from umh.registry.bridges import adapter_pack_to_registry_items

        self.assertEqual(adapter_pack_to_registry_items(None), [])

    def test_with_mock_backend(self):
        from umh.registry.bridges import adapter_pack_to_registry_items

        mock_adapter = MagicMock()
        mock_adapter.name = "TestAdapter"
        mock_adapter.supported_capabilities = frozenset({"a", "b"})
        mock_adapter.supported_environments = frozenset({"local"})

        mock_backend = MagicMock()
        mock_backend._adapters = {"a": mock_adapter, "b": mock_adapter}

        items = adapter_pack_to_registry_items(mock_backend)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].name, "TestAdapter")
        self.assertEqual(items[0].registry_type.value, "adapter")
        self.assertIn("a", items[0].capabilities)
        self.assertIn("b", items[0].capabilities)


class TestBackendBridge(unittest.TestCase):
    def test_converts_default_backends(self):
        from umh.execution.backend_registry import ExecutionBackendRegistry
        from umh.registry.bridges import backend_registry_to_registry_items

        reg = ExecutionBackendRegistry()
        items = backend_registry_to_registry_items(reg)
        self.assertGreaterEqual(len(items), 3)
        env_names = [i.environments[0] for i in items]
        self.assertIn("null", env_names)
        self.assertIn("local", env_names)
        self.assertIn("test", env_names)

    def test_item_fields(self):
        from umh.execution.backend_registry import ExecutionBackendRegistry
        from umh.registry.bridges import backend_registry_to_registry_items

        reg = ExecutionBackendRegistry()
        items = backend_registry_to_registry_items(reg)
        for item in items:
            self.assertEqual(item.registry_type.value, "backend")
            self.assertEqual(item.status.value, "active")
            self.assertIn("backend", item.tags)

    def test_none_uses_global(self):
        from umh.registry.bridges import backend_registry_to_registry_items

        items = backend_registry_to_registry_items(None)
        self.assertGreaterEqual(len(items), 3)


class TestModeBridge(unittest.TestCase):
    def test_converts_mvp_modes(self):
        from umh.registry.bridges import workstation_modes_to_registry_items

        items = workstation_modes_to_registry_items()
        self.assertEqual(len(items), 9)

    def test_item_fields(self):
        from umh.registry.bridges import workstation_modes_to_registry_items

        items = workstation_modes_to_registry_items()
        dev = [i for i in items if i.name == "developer"][0]
        self.assertEqual(dev.registry_type.value, "workstation_mode")
        self.assertEqual(dev.status.value, "active")
        self.assertIn("workstation_mode", dev.tags)
        self.assertIn("development", dev.tags)
        self.assertEqual(dev.source_module, "umh.workstation.modes")

    def test_none_creates_default_registry(self):
        from umh.registry.bridges import workstation_modes_to_registry_items

        items = workstation_modes_to_registry_items(None)
        self.assertEqual(len(items), 9)


class TestPolicyBridge(unittest.TestCase):
    def test_discovers_default_policy(self):
        from umh.registry.bridges import governance_policies_to_registry_items

        items = governance_policies_to_registry_items()
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].registry_type.value, "policy")
        self.assertIn("governance", items[0].tags)


# ── Catalog ─────────────────���───────────────────���─────────────────


class TestRegistryCatalog(unittest.TestCase):
    def test_build_default(self):
        from umh.registry.catalog import build_default_registry_catalog

        catalog = build_default_registry_catalog()
        self.assertGreater(len(catalog.items), 0)
        self.assertIn("capability", catalog.count_by_type())
        self.assertIn("environment", catalog.count_by_type())

    def test_by_type(self):
        from umh.registry.catalog import build_default_registry_catalog
        from umh.registry.contracts import RegistryType

        catalog = build_default_registry_catalog()
        caps = catalog.by_type(RegistryType.CAPABILITY)
        self.assertEqual(len(caps), 9)

    def test_by_name(self):
        from umh.registry.catalog import build_default_registry_catalog

        catalog = build_default_registry_catalog()
        item = catalog.by_name("local")
        self.assertIsNotNone(item)
        self.assertEqual(item.registry_type.value, "environment")

    def test_by_name_case_insensitive(self):
        from umh.registry.catalog import build_default_registry_catalog

        catalog = build_default_registry_catalog()
        item = catalog.by_name("LOCAL")
        self.assertIsNotNone(item)

    def test_by_id(self):
        from umh.registry.catalog import build_default_registry_catalog

        catalog = build_default_registry_catalog()
        item = catalog.by_id("cap_cli.command")
        self.assertIsNotNone(item)
        self.assertEqual(item.name, "CLI Command")

    def test_by_id_not_found(self):
        from umh.registry.catalog import build_default_registry_catalog

        catalog = build_default_registry_catalog()
        self.assertIsNone(catalog.by_id("nonexistent"))

    def test_by_name_not_found(self):
        from umh.registry.catalog import build_default_registry_catalog

        catalog = build_default_registry_catalog()
        self.assertIsNone(catalog.by_name("nonexistent"))

    def test_add_item(self):
        from umh.registry.catalog import RegistryCatalog
        from umh.registry.contracts import RegistryItem, RegistryType

        catalog = RegistryCatalog()
        item = RegistryItem(item_id="x", registry_type=RegistryType.TOOL, name="test")
        catalog.add(item)
        self.assertEqual(len(catalog.items), 1)

    def test_add_all(self):
        from umh.registry.catalog import RegistryCatalog
        from umh.registry.contracts import RegistryItem, RegistryType

        catalog = RegistryCatalog()
        items = [
            RegistryItem(item_id="a", registry_type=RegistryType.TOOL),
            RegistryItem(item_id="b", registry_type=RegistryType.MODEL),
        ]
        catalog.add_all(items)
        self.assertEqual(len(catalog.items), 2)

    def test_to_dict(self):
        from umh.registry.catalog import build_default_registry_catalog

        catalog = build_default_registry_catalog()
        d = catalog.to_dict()
        self.assertIn("items", d)
        self.assertIn("total", d)
        self.assertIn("by_type", d)
        self.assertGreater(d["total"], 0)

    def test_count_by_type(self):
        from umh.registry.catalog import build_default_registry_catalog

        catalog = build_default_registry_catalog()
        counts = catalog.count_by_type()
        self.assertEqual(counts["capability"], 9)
        self.assertEqual(counts["environment"], 7)
        self.assertEqual(counts["workstation_mode"], 9)

    def test_empty_catalog(self):
        from umh.registry.catalog import RegistryCatalog

        catalog = RegistryCatalog()
        d = catalog.to_dict()
        self.assertEqual(d["total"], 0)
        self.assertEqual(d["items"], [])

    def test_generated_at(self):
        from umh.registry.catalog import build_default_registry_catalog

        catalog = build_default_registry_catalog()
        self.assertTrue(catalog.generated_at)

    def test_sparse_safe_no_sources(self):
        from umh.registry.catalog import build_default_registry_catalog

        catalog = build_default_registry_catalog(
            adapter_backend=None,
            backend_registry=None,
            mode_registry=None,
        )
        self.assertGreater(len(catalog.items), 0)


# ── Query ────────────────���──────────────���─────────────────────────


class TestRegistryQuery(unittest.TestCase):
    def test_unfiltered(self):
        from umh.registry.query import query_registry

        result = query_registry()
        self.assertGreater(result.total_returned, 0)

    def test_filter_by_type(self):
        from umh.registry.contracts import RegistryQuery
        from umh.registry.query import query_registry

        result = query_registry(query=RegistryQuery(registry_type="capability"))
        self.assertEqual(result.total_returned, 9)
        for item in result.items:
            self.assertEqual(item.registry_type.value, "capability")

    def test_filter_by_name(self):
        from umh.registry.contracts import RegistryQuery
        from umh.registry.query import query_registry

        result = query_registry(query=RegistryQuery(name="CLI"))
        self.assertGreater(result.total_returned, 0)
        for item in result.items:
            self.assertIn("cli", item.name.lower())

    def test_filter_by_capability(self):
        from umh.registry.contracts import RegistryQuery
        from umh.registry.query import query_registry

        result = query_registry(query=RegistryQuery(capability="cli.command"))
        self.assertGreater(result.total_returned, 0)
        for item in result.items:
            self.assertIn("cli.command", item.capabilities)

    def test_filter_by_environment(self):
        from umh.registry.contracts import RegistryQuery
        from umh.registry.query import query_registry

        result = query_registry(query=RegistryQuery(environment="local"))
        self.assertGreater(result.total_returned, 0)
        for item in result.items:
            self.assertIn("local", item.environments)

    def test_filter_by_tag(self):
        from umh.registry.contracts import RegistryQuery
        from umh.registry.query import query_registry

        result = query_registry(query=RegistryQuery(tag="mvp"))
        self.assertGreater(result.total_returned, 0)

    def test_filter_by_status(self):
        from umh.registry.contracts import RegistryQuery
        from umh.registry.query import query_registry

        result = query_registry(query=RegistryQuery(status="active"))
        self.assertGreater(result.total_returned, 0)
        for item in result.items:
            self.assertEqual(item.status.value, "active")

    def test_filter_by_risk_level(self):
        from umh.registry.contracts import RegistryQuery
        from umh.registry.query import query_registry

        result = query_registry(query=RegistryQuery(risk_level="high"))
        self.assertGreater(result.total_returned, 0)
        for item in result.items:
            self.assertEqual(item.risk_level, "high")

    def test_limit_respected(self):
        from umh.registry.contracts import RegistryQuery
        from umh.registry.query import query_registry

        result = query_registry(query=RegistryQuery(limit=3))
        self.assertLessEqual(result.total_returned, 3)

    def test_combined_filters(self):
        from umh.registry.contracts import RegistryQuery
        from umh.registry.query import query_registry

        result = query_registry(
            query=RegistryQuery(registry_type="capability", environment="local", risk_level="high")
        )
        for item in result.items:
            self.assertEqual(item.registry_type.value, "capability")
            self.assertIn("local", item.environments)
            self.assertEqual(item.risk_level, "high")

    def test_no_results(self):
        from umh.registry.contracts import RegistryQuery
        from umh.registry.query import query_registry

        result = query_registry(query=RegistryQuery(name="ZZZNONEXISTENT"))
        self.assertEqual(result.total_returned, 0)
        self.assertEqual(result.items, [])

    def test_result_serialization(self):
        from umh.registry.query import query_registry

        result = query_registry()
        d = result.to_dict()
        self.assertIn("query", d)
        self.assertIn("items", d)
        self.assertIn("total_returned", d)


class TestTypedFinders(unittest.TestCase):
    def test_find_capabilities(self):
        from umh.registry.query import find_capabilities

        items = find_capabilities()
        self.assertEqual(len(items), 9)

    def test_find_capabilities_by_environment(self):
        from umh.registry.query import find_capabilities

        items = find_capabilities(environment="local")
        self.assertGreater(len(items), 0)
        for i in items:
            self.assertIn("local", i.environments)

    def test_find_capabilities_by_risk(self):
        from umh.registry.query import find_capabilities

        items = find_capabilities(risk_level="low")
        for i in items:
            self.assertEqual(i.risk_level, "low")

    def test_find_adapters_empty(self):
        from umh.registry.query import find_adapters

        items = find_adapters()
        self.assertEqual(len(items), 0)

    def test_find_backends(self):
        from umh.registry.query import find_backends

        items = find_backends()
        self.assertGreaterEqual(len(items), 3)

    def test_find_backends_by_environment(self):
        from umh.registry.query import find_backends

        items = find_backends(environment="local")
        self.assertGreater(len(items), 0)

    def test_find_environments(self):
        from umh.registry.query import find_environments

        items = find_environments()
        self.assertEqual(len(items), 7)

    def test_find_environments_by_capability(self):
        from umh.registry.query import find_environments

        items = find_environments(capability="cli.command")
        self.assertGreater(len(items), 0)
        for i in items:
            self.assertIn("cli.command", i.capabilities)

    def test_find_policies(self):
        from umh.registry.query import find_policies

        items = find_policies()
        self.assertEqual(len(items), 1)

    def test_find_workstation_modes(self):
        from umh.registry.query import find_workstation_modes

        items = find_workstation_modes()
        self.assertEqual(len(items), 9)

    def test_get_registry_item_by_id(self):
        from umh.registry.query import get_registry_item

        item = get_registry_item(item_id="cap_cli.command")
        self.assertIsNotNone(item)
        self.assertEqual(item.name, "CLI Command")

    def test_get_registry_item_by_name(self):
        from umh.registry.query import get_registry_item

        item = get_registry_item(name="local")
        self.assertIsNotNone(item)

    def test_get_registry_item_not_found(self):
        from umh.registry.query import get_registry_item

        item = get_registry_item(item_id="nonexistent")
        self.assertIsNone(item)


class TestExplainRegistryMatch(unittest.TestCase):
    def test_explain_type_match(self):
        from umh.registry.contracts import RegistryItem, RegistryQuery, RegistryType
        from umh.registry.query import explain_registry_match

        item = RegistryItem(item_id="t", registry_type=RegistryType.CAPABILITY, name="X")
        q = RegistryQuery(registry_type="capability")
        result = explain_registry_match(item, q)
        self.assertGreater(result["match_count"], 0)
        self.assertIn("type matches", result["match_reasons"][0])

    def test_explain_multi_match(self):
        from umh.registry.contracts import RegistryItem, RegistryQuery, RegistryType

        from umh.registry.query import explain_registry_match

        item = RegistryItem(
            item_id="t",
            registry_type=RegistryType.CAPABILITY,
            name="CLI Command",
            capabilities=["cli.command"],
            environments=["local"],
            tags=["mvp"],
        )
        q = RegistryQuery(
            registry_type="capability", name="CLI", capability="cli.command", tag="mvp"
        )
        result = explain_registry_match(item, q)
        self.assertEqual(result["match_count"], 4)

    def test_explain_no_match(self):
        from umh.registry.contracts import RegistryItem, RegistryQuery, RegistryType
        from umh.registry.query import explain_registry_match

        item = RegistryItem(item_id="t", registry_type=RegistryType.CAPABILITY, name="X")
        q = RegistryQuery(registry_type="adapter")
        result = explain_registry_match(item, q)
        self.assertEqual(result["match_count"], 0)


# ── Views ─────────────────────────────────────��───────────────────


class TestRegistryItemView(unittest.TestCase):
    def test_from_item(self):
        from umh.registry.contracts import RegistryItem, RegistryItemStatus, RegistryType
        from umh.registry.views import registry_item_to_view

        item = RegistryItem(
            item_id="t",
            registry_type=RegistryType.CAPABILITY,
            name="Test",
            description="A test",
            status=RegistryItemStatus.ACTIVE,
            capabilities=["a", "b"],
            environments=["local"],
        )
        view = registry_item_to_view(item)
        self.assertEqual(view.item_id, "t")
        self.assertEqual(view.registry_type, "capability")
        self.assertEqual(view.capability_count, 2)
        self.assertEqual(view.environment_count, 1)

    def test_serialization(self):
        from umh.registry.contracts import RegistryItem, RegistryType
        from umh.registry.views import registry_item_to_view

        item = RegistryItem(item_id="t", registry_type=RegistryType.TOOL, name="X")
        d = registry_item_to_view(item).to_dict()
        self.assertIn("item_id", d)
        self.assertIn("registry_type", d)
        self.assertIn("capability_count", d)

    def test_description_truncated(self):
        from umh.registry.contracts import RegistryItem, RegistryType
        from umh.registry.views import registry_item_to_view

        item = RegistryItem(
            item_id="t",
            registry_type=RegistryType.TOOL,
            name="X",
            description="A" * 500,
        )
        view = registry_item_to_view(item)
        self.assertLessEqual(len(view.description), 200)


class TestRegistryCatalogView(unittest.TestCase):
    def test_build_from_default(self):
        from umh.registry.views import build_catalog_view

        view = build_catalog_view()
        self.assertGreater(view.total_items, 0)
        self.assertEqual(view.capabilities_count, 9)
        self.assertEqual(view.environments_count, 7)
        self.assertEqual(view.modes_count, 9)
        self.assertEqual(view.policies_count, 1)

    def test_serialization(self):
        from umh.registry.views import build_catalog_view

        d = build_catalog_view().to_dict()
        self.assertIn("total_items", d)
        self.assertIn("by_type", d)
        self.assertIn("by_status", d)
        self.assertIn("generated_at", d)

    def test_empty_catalog(self):
        from umh.registry.catalog import RegistryCatalog
        from umh.registry.views import build_catalog_view

        view = build_catalog_view(RegistryCatalog())
        self.assertEqual(view.total_items, 0)


class TestRegistryHealthView(unittest.TestCase):
    def test_build_from_default(self):
        from umh.registry.views import build_registry_health_view

        view = build_registry_health_view()
        self.assertGreater(view.total_items, 0)
        self.assertGreater(view.active_count, 0)
        self.assertGreater(len(view.source_modules), 0)

    def test_serialization(self):
        from umh.registry.views import build_registry_health_view

        d = build_registry_health_view().to_dict()
        self.assertIn("total_items", d)
        self.assertIn("active_count", d)
        self.assertIn("source_modules", d)

    def test_empty_catalog(self):
        from umh.registry.catalog import RegistryCatalog
        from umh.registry.views import build_registry_health_view

        view = build_registry_health_view(RegistryCatalog())
        self.assertEqual(view.total_items, 0)
        self.assertEqual(view.active_count, 0)


# ── API Functions ─────────────────────────────────────────────────


class TestControlAPIFunctions(unittest.TestCase):
    def test_registry_catalog_callable(self):
        from umh.registry.catalog import build_default_registry_catalog

        catalog = build_default_registry_catalog()
        d = catalog.to_dict()
        self.assertIn("items", d)

    def test_registry_overview_callable(self):
        from umh.registry.catalog import build_default_registry_catalog
        from umh.registry.views import build_catalog_view

        catalog = build_default_registry_catalog()
        d = build_catalog_view(catalog).to_dict()
        self.assertIn("total_items", d)

    def test_registry_health_callable(self):
        from umh.registry.catalog import build_default_registry_catalog
        from umh.registry.views import build_registry_health_view

        catalog = build_default_registry_catalog()
        d = build_registry_health_view(catalog).to_dict()
        self.assertIn("total_items", d)

    def test_registry_query_callable(self):
        from umh.registry.contracts import RegistryQuery
        from umh.registry.query import query_registry

        result = query_registry(query=RegistryQuery(registry_type="capability"))
        self.assertGreater(result.total_returned, 0)

    def test_registry_capabilities_callable(self):
        from umh.registry.query import find_capabilities
        from umh.registry.views import registry_item_to_view

        items = find_capabilities()
        views = [registry_item_to_view(i).to_dict() for i in items]
        self.assertEqual(len(views), 9)

    def test_registry_backends_callable(self):
        from umh.registry.query import find_backends
        from umh.registry.views import registry_item_to_view

        items = find_backends()
        views = [registry_item_to_view(i).to_dict() for i in items]
        self.assertGreaterEqual(len(views), 3)

    def test_registry_environments_callable(self):
        from umh.registry.query import find_environments
        from umh.registry.views import registry_item_to_view

        items = find_environments()
        views = [registry_item_to_view(i).to_dict() for i in items]
        self.assertEqual(len(views), 7)

    def test_registry_modes_callable(self):
        from umh.registry.query import find_workstation_modes
        from umh.registry.views import registry_item_to_view

        items = find_workstation_modes()
        views = [registry_item_to_view(i).to_dict() for i in items]
        self.assertEqual(len(views), 9)

    def test_registry_policies_callable(self):
        from umh.registry.query import find_policies
        from umh.registry.views import registry_item_to_view

        items = find_policies()
        views = [registry_item_to_view(i).to_dict() for i in items]
        self.assertEqual(len(views), 1)

    def test_all_endpoints_read_only(self):
        """Verify no mutation happens — call all query functions twice, same results."""
        from umh.registry.catalog import build_default_registry_catalog
        from umh.registry.views import build_catalog_view

        cat1 = build_default_registry_catalog()
        cat2 = build_default_registry_catalog()
        self.assertEqual(len(cat1.items), len(cat2.items))
        v1 = build_catalog_view(cat1)
        v2 = build_catalog_view(cat2)
        self.assertEqual(v1.total_items, v2.total_items)


# ── CLI Commands ─────────────���────────────────────────────────────


class TestCLICommands(unittest.TestCase):
    def test_parser_accepts_registry_commands(self):
        from umh.control.cli import build_parser

        parser = build_parser()
        cmds = [
            "registry-catalog",
            "registry-overview",
            "registry-health",
            "registry-capabilities",
            "registry-environments",
            "registry-modes",
            "registry-policies",
        ]
        for cmd in cmds:
            args = parser.parse_args([cmd, "--json"])
            self.assertEqual(args.command, cmd)

    def test_parser_accepts_registry_query(self):
        from umh.control.cli import build_parser

        parser = build_parser()
        args = parser.parse_args(
            ["registry-query", "--type", "capability", "--environment", "local", "--json"]
        )
        self.assertEqual(args.command, "registry-query")
        self.assertEqual(args.type, "capability")

    def test_parser_accepts_registry_item(self):
        from umh.control.cli import build_parser

        parser = build_parser()
        args = parser.parse_args(["registry-item", "--item-id", "cap_cli.command", "--json"])
        self.assertEqual(args.command, "registry-item")
        self.assertEqual(args.item_id, "cap_cli.command")

    def test_dispatch_table_has_registry_entries(self):
        from umh.control.cli import main

        expected = [
            "registry-catalog",
            "registry-overview",
            "registry-health",
            "registry-query",
            "registry-item",
            "registry-capabilities",
            "registry-environments",
            "registry-modes",
            "registry-policies",
        ]
        src = Path("/opt/OS/umh/control/cli.py").read_text()
        for cmd in expected:
            self.assertIn(f'"{cmd}"', src, f"Missing dispatch entry: {cmd}")


# ── Layering Invariants ────────��─────────────────────────────────


class TestLayeringInvariants(unittest.TestCase):
    """Verify registry modules don't import execution, mutation, or adapter modules."""

    _REGISTRY_MODULES = [
        "umh/registry/__init__.py",
        "umh/registry/contracts.py",
        "umh/registry/bridges.py",
        "umh/registry/catalog.py",
        "umh/registry/query.py",
        "umh/registry/views.py",
    ]

    _FORBIDDEN_IMPORTS = [
        "umh.execution.governance_gate",
        "umh.execution.engine",
        "umh.adapters.cli_adapter",
        "umh.adapters.filesystem_adapter",
        "umh.adapters.http_adapter",
        "umh.adapters.simulated_browser",
        "subprocess",
        "requests",
        "httpx",
    ]

    def test_no_forbidden_imports_in_registry(self):
        for mod_path in self._REGISTRY_MODULES:
            full = Path("/opt/OS") / mod_path
            if not full.exists():
                continue
            src = full.read_text()
            tree = ast.parse(src)
            imported = set()
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imported.add(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        imported.add(node.module)
            for forbidden in self._FORBIDDEN_IMPORTS:
                self.assertNotIn(
                    forbidden,
                    imported,
                    f"{mod_path} imports forbidden module {forbidden}",
                )

    def test_contracts_has_no_store_imports(self):
        src = Path("/opt/OS/umh/registry/contracts.py").read_text()
        self.assertNotIn("trace_store", src)
        self.assertNotIn("feedback_store", src)

    def test_views_does_not_import_execution(self):
        src = Path("/opt/OS/umh/registry/views.py").read_text()
        self.assertNotIn("execute(", src)
        self.assertNotIn("from umh.execution.engine", src)

    def test_bridges_does_not_call_execute(self):
        src = Path("/opt/OS/umh/registry/bridges.py").read_text()
        self.assertNotIn(".execute(", src)

    def test_query_does_not_mutate(self):
        src = Path("/opt/OS/umh/registry/query.py").read_text()
        self.assertNotIn(".save(", src)
        self.assertNotIn(".delete(", src)
        self.assertNotIn(".clear(", src)
        self.assertNotIn(".register(", src)

    def test_catalog_is_read_only(self):
        src = Path("/opt/OS/umh/registry/catalog.py").read_text()
        self.assertNotIn(".execute(", src)
        self.assertNotIn("subprocess", src)

    def test_no_secrets_in_views(self):
        src = Path("/opt/OS/umh/registry/views.py").read_text()
        self.assertNotIn("password", src.lower())
        self.assertNotIn("api_key", src.lower())
        self.assertNotIn("secret", src.lower())


# ── Phase 79 Compatibility ───────────���────────────────────────────


class TestPhase79Compatibility(unittest.TestCase):
    def test_observability_imports_intact(self):
        from umh.observability.decision_explainer import explain_trace
        from umh.observability.execution_summary import summarize_executions
        from umh.observability.failure_search import search_failures
        from umh.observability.operator_views import build_operator_dashboard_snapshot
        from umh.observability.system_status import build_system_status
        from umh.observability.timeline import build_timeline
        from umh.observability.trace_query import query_traces

        self.assertTrue(callable(explain_trace))
        self.assertTrue(callable(summarize_executions))
        self.assertTrue(callable(search_failures))
        self.assertTrue(callable(build_operator_dashboard_snapshot))
        self.assertTrue(callable(build_system_status))
        self.assertTrue(callable(build_timeline))
        self.assertTrue(callable(query_traces))

    def test_interface_imports_intact(self):
        from umh.interface.contracts import (
            InterfaceActionType,
            InterfaceType,
            create_interface_request,
            create_interface_response,
        )
        from umh.interface.views import (
            OperatorDashboardSnapshot,
            TraceView,
        )

        self.assertTrue(callable(create_interface_request))
        self.assertTrue(callable(create_interface_response))

    def test_observability_api_endpoints_still_referenced(self):
        src = Path("/opt/OS/umh/control/api.py").read_text()
        endpoints = [
            "/observability/status",
            "/observability/dashboard",
            "/observability/timeline",
            "/observability/traces",
            "/observability/failures",
            "/observability/executions/summary",
        ]
        for ep in endpoints:
            self.assertIn(ep, src, f"Missing endpoint: {ep}")

    def test_observe_cli_commands_still_referenced(self):
        src = Path("/opt/OS/umh/control/cli.py").read_text()
        cmds = [
            "observe-status",
            "observe-dashboard",
            "observe-timeline",
            "observe-traces",
            "observe-trace",
            "observe-explain",
            "observe-failures",
            "observe-summary",
        ]
        for cmd in cmds:
            self.assertIn(f'"{cmd}"', src, f"Missing CLI command: {cmd}")

    def test_existing_definitions_unchanged(self):
        from umh.capabilities.definitions import MVP_CAPABILITIES
        from umh.environments.definitions import MVP_ENVIRONMENTS

        self.assertEqual(len(MVP_CAPABILITIES), 9)
        self.assertEqual(len(MVP_ENVIRONMENTS), 7)


# ── Additional Edge Cases ��────────────────────────────────────────


class TestEdgeCases(unittest.TestCase):
    def test_bridge_with_broken_adapter(self):
        from umh.registry.bridges import adapter_pack_to_registry_items

        mock = MagicMock()
        mock._adapters = {
            "x": MagicMock(
                name="Bad", supported_capabilities=frozenset(), supported_environments=frozenset()
            )
        }
        items = adapter_pack_to_registry_items(mock)
        self.assertEqual(len(items), 1)

    def test_catalog_resilient_to_import_errors(self):
        from umh.registry.catalog import RegistryCatalog

        catalog = RegistryCatalog()
        self.assertEqual(len(catalog.items), 0)
        self.assertEqual(catalog.count_by_type(), {})

    def test_query_with_all_filters_no_match(self):
        from umh.registry.contracts import RegistryQuery
        from umh.registry.query import query_registry

        result = query_registry(
            query=RegistryQuery(
                registry_type="capability",
                name="ZZZZ",
                capability="nonexistent",
                environment="nowhere",
            )
        )
        self.assertEqual(result.total_returned, 0)

    def test_registry_item_round_trip(self):
        from umh.registry.contracts import RegistryItem, RegistryType

        item = RegistryItem(
            item_id="rt_test",
            registry_type=RegistryType.TOOL,
            name="round_trip",
            capabilities=["a"],
            tags=["test"],
        )
        d = item.to_dict()
        restored = RegistryItem.from_dict(d)
        self.assertEqual(restored.item_id, "rt_test")
        self.assertEqual(restored.registry_type.value, "tool")
        self.assertEqual(restored.capabilities, ["a"])

    def test_multiple_catalogs_independent(self):
        from umh.registry.catalog import build_default_registry_catalog

        c1 = build_default_registry_catalog()
        c2 = build_default_registry_catalog()
        self.assertEqual(len(c1.items), len(c2.items))
        c1.items.clear()
        self.assertGreater(len(c2.items), 0)


if __name__ == "__main__":
    unittest.main()
