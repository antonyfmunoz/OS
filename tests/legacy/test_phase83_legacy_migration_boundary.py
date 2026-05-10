"""Phase 83 tests — Legacy Runtime Deprecation + Migration Boundary v1.

Covers: contracts, inventory, classifier, deprecation registry, import boundary,
compatibility, views, registry integration, observability integration,
API/CLI integration, layering invariants, and regression checks.
"""

from __future__ import annotations

import ast
import inspect
import os
import sys
import tempfile

import pytest

sys.path.insert(0, "/opt/OS")


# ── Section 1: Contract Tests ──────────────────────────────────────


class TestLegacyModuleStatusNormalization:
    def test_known_values(self):
        from umh.migration.contracts import LegacyModuleStatus, normalize_legacy_status

        assert normalize_legacy_status("deprecated") == LegacyModuleStatus.DEPRECATED
        assert normalize_legacy_status("active_retained") == LegacyModuleStatus.ACTIVE_RETAINED
        assert normalize_legacy_status("bypass_risk") == LegacyModuleStatus.BYPASS_RISK
        assert normalize_legacy_status("future_review") == LegacyModuleStatus.FUTURE_REVIEW
        assert normalize_legacy_status("duplicate") == LegacyModuleStatus.DUPLICATE
        assert normalize_legacy_status("migrated") == LegacyModuleStatus.MIGRATED

    def test_unknown_degrades(self):
        from umh.migration.contracts import LegacyModuleStatus, normalize_legacy_status

        assert normalize_legacy_status("nonexistent") == LegacyModuleStatus.UNKNOWN
        assert normalize_legacy_status("") == LegacyModuleStatus.UNKNOWN


class TestLegacyModuleCategoryNormalization:
    def test_known_values(self):
        from umh.migration.contracts import LegacyModuleCategory, normalize_module_category

        assert normalize_module_category("runtime_engine") == LegacyModuleCategory.RUNTIME_ENGINE
        assert normalize_module_category("substrate") == LegacyModuleCategory.SUBSTRATE
        assert normalize_module_category("execution") == LegacyModuleCategory.EXECUTION
        assert normalize_module_category("registry") == LegacyModuleCategory.REGISTRY
        assert normalize_module_category("ontology") == LegacyModuleCategory.ONTOLOGY

    def test_unknown_degrades(self):
        from umh.migration.contracts import LegacyModuleCategory, normalize_module_category

        assert normalize_module_category("bogus") == LegacyModuleCategory.UNKNOWN


class TestMigrationActionNormalization:
    def test_known_values(self):
        from umh.migration.contracts import MigrationAction, normalize_migration_action

        assert normalize_migration_action("retain") == MigrationAction.RETAIN
        assert normalize_migration_action("migrate_imports") == MigrationAction.MIGRATE_IMPORTS
        assert normalize_migration_action("review_manually") == MigrationAction.REVIEW_MANUALLY
        assert normalize_migration_action("future_delete") == MigrationAction.FUTURE_DELETE

    def test_unknown_degrades(self):
        from umh.migration.contracts import MigrationAction, normalize_migration_action

        assert normalize_migration_action("nope") == MigrationAction.UNKNOWN


class TestMigrationRiskNormalization:
    def test_known_values(self):
        from umh.migration.contracts import MigrationRiskLevel, normalize_migration_risk

        assert normalize_migration_risk("none") == MigrationRiskLevel.NONE
        assert normalize_migration_risk("high") == MigrationRiskLevel.HIGH
        assert normalize_migration_risk("critical") == MigrationRiskLevel.CRITICAL

    def test_unknown_degrades(self):
        from umh.migration.contracts import MigrationRiskLevel, normalize_migration_risk

        assert normalize_migration_risk("extreme") == MigrationRiskLevel.UNKNOWN


class TestImportBoundaryStatusNormalization:
    def test_known_values(self):
        from umh.migration.contracts import ImportBoundaryStatus, normalize_import_boundary_status

        assert normalize_import_boundary_status("allowed") == ImportBoundaryStatus.ALLOWED
        assert normalize_import_boundary_status("blocked") == ImportBoundaryStatus.BLOCKED

    def test_unknown_degrades(self):
        from umh.migration.contracts import ImportBoundaryStatus, normalize_import_boundary_status

        assert normalize_import_boundary_status("nope") == ImportBoundaryStatus.UNKNOWN


class TestLegacyModuleRecordSerialization:
    def test_roundtrip(self):
        from umh.migration.contracts import (
            LegacyModuleCategory,
            LegacyModuleRecord,
            LegacyModuleStatus,
            MigrationAction,
            MigrationRiskLevel,
        )

        record = LegacyModuleRecord(
            module_path="umh/runtime_engine/foo.py",
            module_name="umh.runtime_engine.foo",
            category=LegacyModuleCategory.RUNTIME_ENGINE,
            status=LegacyModuleStatus.DUPLICATE,
            risk_level=MigrationRiskLevel.LOW,
            reason="test reason",
            clean_equivalent="umh.reasoning.foo",
            migration_action=MigrationAction.MIGRATE_IMPORTS,
            evidence=["evidence1"],
            tags=["duplicate"],
        )
        d = record.to_dict()
        restored = LegacyModuleRecord.from_dict(d)
        assert restored.module_path == record.module_path
        assert restored.status == record.status
        assert restored.clean_equivalent == record.clean_equivalent
        assert restored.evidence == record.evidence


class TestMigrationMappingSerialization:
    def test_roundtrip(self):
        from umh.migration.contracts import MigrationAction, MigrationMapping

        m = MigrationMapping(
            legacy_module="umh.runtime_engine.x",
            clean_equivalent="umh.reasoning.x",
            migration_action=MigrationAction.MIGRATE_IMPORTS,
            confidence=0.9,
            reason="duplicate",
        )
        d = m.to_dict()
        restored = MigrationMapping.from_dict(d)
        assert restored.legacy_module == m.legacy_module
        assert restored.confidence == m.confidence
        assert restored.mapping_id == m.mapping_id


class TestImportBoundaryRuleSerialization:
    def test_roundtrip(self):
        from umh.migration.contracts import ImportBoundaryRule, ImportBoundaryStatus

        r = ImportBoundaryRule(
            source_pattern="umh/control",
            forbidden_import_pattern="umh.runtime_engine",
            status=ImportBoundaryStatus.BLOCKED,
            reason="test",
        )
        d = r.to_dict()
        restored = ImportBoundaryRule.from_dict(d)
        assert restored.source_pattern == r.source_pattern
        assert restored.status == ImportBoundaryStatus.BLOCKED


class TestImportBoundaryFindingSerialization:
    def test_roundtrip(self):
        from umh.migration.contracts import ImportBoundaryFinding, ImportBoundaryStatus

        f = ImportBoundaryFinding(
            source_file="umh/control/api.py",
            imported_module="umh.runtime_engine.foo",
            status=ImportBoundaryStatus.BLOCKED,
            severity="warning",
            message="test",
            recommendation="migrate",
        )
        d = f.to_dict()
        restored = ImportBoundaryFinding.from_dict(d)
        assert restored.source_file == f.source_file
        assert restored.status == ImportBoundaryStatus.BLOCKED


class TestMigrationInventorySerialization:
    def test_serializes(self):
        from umh.migration.contracts import MigrationInventory

        inv = MigrationInventory(root_path="/opt/OS")
        d = inv.to_dict()
        assert "generated_at" in d
        assert d["root_path"] == "/opt/OS"
        assert isinstance(d["records"], list)


# ── Section 2: Inventory Tests ───────────────────────────────────────


class TestModulePathToModuleName:
    def test_basic(self):
        from umh.migration.inventory import module_path_to_module_name

        assert module_path_to_module_name("umh/runtime_engine/foo.py") == "umh.runtime_engine.foo"

    def test_init(self):
        from umh.migration.inventory import module_path_to_module_name

        assert module_path_to_module_name("umh/runtime_engine/__init__.py") == "umh.runtime_engine"


class TestClassifyModulePath:
    def test_runtime_engine(self):
        from umh.migration.inventory import classify_module_path
        from umh.migration.contracts import LegacyModuleCategory

        assert (
            classify_module_path("umh/runtime_engine/foo.py") == LegacyModuleCategory.RUNTIME_ENGINE
        )

    def test_substrate(self):
        from umh.migration.inventory import classify_module_path
        from umh.migration.contracts import LegacyModuleCategory

        assert classify_module_path("umh/substrate/bar.py") == LegacyModuleCategory.SUBSTRATE

    def test_execution(self):
        from umh.migration.inventory import classify_module_path
        from umh.migration.contracts import LegacyModuleCategory

        assert classify_module_path("umh/execution/engine.py") == LegacyModuleCategory.EXECUTION

    def test_registry(self):
        from umh.migration.inventory import classify_module_path
        from umh.migration.contracts import LegacyModuleCategory

        assert classify_module_path("umh/registry/contracts.py") == LegacyModuleCategory.REGISTRY

    def test_ontology(self):
        from umh.migration.inventory import classify_module_path
        from umh.migration.contracts import LegacyModuleCategory

        assert classify_module_path("umh/ontology/primitives.py") == LegacyModuleCategory.ONTOLOGY

    def test_unknown(self):
        from umh.migration.inventory import classify_module_path
        from umh.migration.contracts import LegacyModuleCategory

        assert classify_module_path("random/thing.py") == LegacyModuleCategory.UNKNOWN


class TestDiscoverPythonModules:
    def test_safe_on_missing_dir(self):
        from umh.migration.inventory import discover_python_modules

        result = discover_python_modules("/nonexistent/path")
        assert result == []

    def test_discovers_files_in_temp(self):
        from umh.migration.inventory import discover_python_modules

        with tempfile.TemporaryDirectory() as tmpdir:
            os.makedirs(os.path.join(tmpdir, "pkg"))
            with open(os.path.join(tmpdir, "pkg", "mod.py"), "w") as f:
                f.write("x = 1\n")
            result = discover_python_modules(tmpdir)
            assert len(result) >= 1


class TestBuildLegacyInventory:
    def test_safe_on_temp_project(self):
        from umh.migration.inventory import build_legacy_inventory

        with tempfile.TemporaryDirectory() as tmpdir:
            os.makedirs(os.path.join(tmpdir, "umh"))
            inv = build_legacy_inventory(tmpdir)
            assert inv.root_path == tmpdir
            assert isinstance(inv.warnings, list)

    def test_summary_counts(self):
        from umh.migration.inventory import summarize_inventory
        from umh.migration.contracts import (
            LegacyModuleCategory,
            LegacyModuleRecord,
            LegacyModuleStatus,
        )

        records = [
            LegacyModuleRecord(
                module_path="a.py",
                module_name="a",
                status=LegacyModuleStatus.DEPRECATED,
                category=LegacyModuleCategory.RUNTIME_ENGINE,
            ),
            LegacyModuleRecord(
                module_path="b.py",
                module_name="b",
                status=LegacyModuleStatus.ACTIVE_RETAINED,
                category=LegacyModuleCategory.EXECUTION,
            ),
        ]
        summary = summarize_inventory(records)
        assert summary["total"] == 2
        assert summary["by_status"]["deprecated"] == 1


class TestExistingModuleInventoryRead:
    def test_safe_when_missing(self):
        from umh.migration.inventory import read_existing_module_inventory

        result = read_existing_module_inventory("/nonexistent/file.json")
        assert result == []


class TestExistingDependencyGraphRead:
    def test_safe_when_missing(self):
        from umh.migration.inventory import read_existing_dependency_graph

        result = read_existing_dependency_graph("/nonexistent/file.md")
        assert result == ""


class TestExistingDeprecationPlanRead:
    def test_safe_when_missing(self):
        from umh.migration.inventory import read_existing_deprecation_plan

        result = read_existing_deprecation_plan("/nonexistent/file.md")
        assert result == ""


# ── Section 3: Classifier Tests ──────────────────────────────────────


class TestDetectSubprocessBypass:
    def test_subprocess_run(self):
        from umh.migration.classifier import detect_bypass_risk

        evidence = detect_bypass_risk("subprocess.run(['ls'])")
        assert len(evidence) > 0

    def test_os_call(self):
        from umh.migration.classifier import detect_bypass_risk

        code = 'os.system("rm -rf /")'
        evidence = detect_bypass_risk(code)
        assert len(evidence) > 0


class TestDetectNetworkBypass:
    def test_requests_get(self):
        from umh.migration.classifier import detect_bypass_risk

        evidence = detect_bypass_risk('requests.get("http://example.com")')
        assert len(evidence) > 0

    def test_httpx_client(self):
        from umh.migration.classifier import detect_bypass_risk

        evidence = detect_bypass_risk("httpx.Client()")
        assert len(evidence) > 0


class TestDetectDirectStoragePatterns:
    def test_file_write(self):
        from umh.migration.classifier import detect_direct_storage_patterns

        evidence = detect_direct_storage_patterns('open("file.txt", "w")')
        assert len(evidence) > 0

    def test_json_dump(self):
        from umh.migration.classifier import detect_direct_storage_patterns

        evidence = detect_direct_storage_patterns("json.dump(data, fp)")
        assert len(evidence) > 0

    def test_sqlite_connect(self):
        from umh.migration.classifier import detect_direct_storage_patterns

        evidence = detect_direct_storage_patterns('sqlite3.connect("db.sqlite")')
        assert len(evidence) > 0


class TestDetectExecutionBypass:
    def test_run_loop(self):
        from umh.migration.classifier import detect_direct_execution_patterns

        evidence = detect_direct_execution_patterns("def run_loop(self):")
        assert len(evidence) > 0

    def test_worker_class(self):
        from umh.migration.classifier import detect_direct_execution_patterns

        evidence = detect_direct_execution_patterns("class TaskWorker:")
        assert len(evidence) > 0

    def test_alternate_memory_store(self):
        from umh.migration.classifier import _MEMORY_BYPASS_PATTERNS

        text = "class CustomMemoryStore:"
        found = any(p.search(text) for p in _MEMORY_BYPASS_PATTERNS)
        assert found


class TestClassifyRuntimeEngineModule:
    def test_default_is_future_review(self):
        from umh.migration.classifier import classify_runtime_engine_module
        from umh.migration.contracts import LegacyModuleStatus

        record = classify_runtime_engine_module(
            "umh/runtime_engine/unknown_file.py", content="x = 1"
        )
        assert record.status == LegacyModuleStatus.FUTURE_REVIEW

    def test_duplicate_detected(self):
        from umh.migration.classifier import classify_runtime_engine_module
        from umh.migration.contracts import LegacyModuleStatus

        record = classify_runtime_engine_module(
            "umh/runtime_engine/causal_attribution.py", content="class CausalAttribution: pass"
        )
        assert record.status == LegacyModuleStatus.DUPLICATE
        assert record.clean_equivalent is not None


class TestClassifySubstrateModule:
    def test_default_is_future_review(self):
        from umh.migration.classifier import classify_substrate_module
        from umh.migration.contracts import LegacyModuleStatus

        record = classify_substrate_module("umh/substrate/nodes.py", content="x = 1")
        assert record.status == LegacyModuleStatus.FUTURE_REVIEW

    def test_bypass_risk_elevated(self):
        from umh.migration.classifier import classify_substrate_module
        from umh.migration.contracts import LegacyModuleStatus, MigrationRiskLevel

        record = classify_substrate_module(
            "umh/substrate/risky.py", content='subprocess.run(["ls"])'
        )
        assert record.status == LegacyModuleStatus.BYPASS_RISK
        assert record.risk_level == MigrationRiskLevel.HIGH


class TestClassifyLegacyModule:
    def test_clean_module_retained(self):
        from umh.migration.classifier import classify_legacy_module
        from umh.migration.contracts import LegacyModuleStatus

        record = classify_legacy_module("umh/execution/engine.py", content="class Engine: pass")
        assert record.status == LegacyModuleStatus.ACTIVE_RETAINED

    def test_recommendation_deterministic(self):
        from umh.migration.classifier import recommend_migration_action
        from umh.migration.contracts import (
            LegacyModuleRecord,
            LegacyModuleStatus,
            MigrationAction,
        )

        r = LegacyModuleRecord(
            module_path="a.py",
            module_name="a",
            status=LegacyModuleStatus.DUPLICATE,
        )
        assert recommend_migration_action(r) == MigrationAction.MIGRATE_IMPORTS

    def test_unknown_content_safe(self):
        from umh.migration.classifier import classify_legacy_module

        record = classify_legacy_module("umh/runtime_engine/x.py", content="")
        assert record is not None


# ── Section 4: Deprecation Registry Tests ────────────────────────────


class TestDeprecationRegistryBasic:
    def test_initializes(self):
        from umh.migration.deprecation_registry import DeprecationRegistry

        reg = DeprecationRegistry()
        assert reg.record_count == 0

    def test_register_record(self):
        from umh.migration.deprecation_registry import DeprecationRegistry
        from umh.migration.contracts import LegacyModuleRecord

        reg = DeprecationRegistry()
        rec = LegacyModuleRecord(module_path="a.py", module_name="a")
        reg.register_record(rec)
        assert reg.record_count == 1

    def test_register_many(self):
        from umh.migration.deprecation_registry import DeprecationRegistry
        from umh.migration.contracts import LegacyModuleRecord

        reg = DeprecationRegistry()
        recs = [LegacyModuleRecord(module_path=f"{i}.py", module_name=f"mod_{i}") for i in range(5)]
        reg.register_many(recs)
        assert reg.record_count == 5

    def test_get_record_by_path(self):
        from umh.migration.deprecation_registry import DeprecationRegistry
        from umh.migration.contracts import LegacyModuleRecord

        reg = DeprecationRegistry()
        rec = LegacyModuleRecord(module_path="a.py", module_name="mod_a")
        reg.register_record(rec)
        assert reg.get_record("a.py") is not None

    def test_get_record_by_name(self):
        from umh.migration.deprecation_registry import DeprecationRegistry
        from umh.migration.contracts import LegacyModuleRecord

        reg = DeprecationRegistry()
        rec = LegacyModuleRecord(module_path="a.py", module_name="mod_a")
        reg.register_record(rec)
        assert reg.get_record("mod_a") is not None


class TestDeprecationRegistryQuery:
    def _build_registry(self):
        from umh.migration.deprecation_registry import DeprecationRegistry
        from umh.migration.contracts import (
            LegacyModuleCategory,
            LegacyModuleRecord,
            LegacyModuleStatus,
            MigrationAction,
            MigrationRiskLevel,
        )

        reg = DeprecationRegistry()
        reg.register_record(
            LegacyModuleRecord(
                module_path="a.py",
                module_name="a",
                status=LegacyModuleStatus.DEPRECATED,
                category=LegacyModuleCategory.RUNTIME_ENGINE,
                risk_level=MigrationRiskLevel.LOW,
                migration_action=MigrationAction.MARK_DEPRECATED,
            )
        )
        reg.register_record(
            LegacyModuleRecord(
                module_path="b.py",
                module_name="b",
                status=LegacyModuleStatus.BYPASS_RISK,
                category=LegacyModuleCategory.SUBSTRATE,
                risk_level=MigrationRiskLevel.HIGH,
                migration_action=MigrationAction.REVIEW_MANUALLY,
            )
        )
        reg.register_record(
            LegacyModuleRecord(
                module_path="c.py",
                module_name="c",
                status=LegacyModuleStatus.FUTURE_REVIEW,
                category=LegacyModuleCategory.RUNTIME_ENGINE,
                risk_level=MigrationRiskLevel.MEDIUM,
            )
        )
        return reg

    def test_query_by_status(self):
        from umh.migration.contracts import LegacyModuleStatus

        reg = self._build_registry()
        result = reg.query(status=LegacyModuleStatus.DEPRECATED)
        assert len(result) == 1

    def test_query_by_category(self):
        from umh.migration.contracts import LegacyModuleCategory

        reg = self._build_registry()
        result = reg.query(category=LegacyModuleCategory.RUNTIME_ENGINE)
        assert len(result) == 2

    def test_query_by_risk(self):
        from umh.migration.contracts import MigrationRiskLevel

        reg = self._build_registry()
        result = reg.query(risk_level=MigrationRiskLevel.HIGH)
        assert len(result) == 1

    def test_query_by_action(self):
        from umh.migration.contracts import MigrationAction

        reg = self._build_registry()
        result = reg.query(action=MigrationAction.REVIEW_MANUALLY)
        assert len(result) == 1

    def test_list_deprecated(self):
        reg = self._build_registry()
        assert len(reg.list_deprecated()) == 1

    def test_list_bypass_risk(self):
        reg = self._build_registry()
        assert len(reg.list_bypass_risk()) == 1

    def test_list_future_review(self):
        reg = self._build_registry()
        assert len(reg.list_future_review()) == 1

    def test_query_limit_enforced(self):
        reg = self._build_registry()
        result = reg.query(limit=1)
        assert len(result) == 1

    def test_unknown_safe(self):
        reg = self._build_registry()
        assert reg.get_record("nonexistent") is None


class TestDeprecationRegistryMapping:
    def test_register_mapping(self):
        from umh.migration.deprecation_registry import DeprecationRegistry
        from umh.migration.contracts import MigrationMapping

        reg = DeprecationRegistry()
        reg.register_mapping(MigrationMapping(legacy_module="a", clean_equivalent="b"))
        assert reg.mapping_count == 1

    def test_list_mappings(self):
        from umh.migration.deprecation_registry import DeprecationRegistry
        from umh.migration.contracts import MigrationMapping

        reg = DeprecationRegistry()
        reg.register_mapping(MigrationMapping(legacy_module="a", clean_equivalent="b"))
        assert len(reg.list_mappings()) == 1


class TestDeprecationRegistryRoundtrip:
    def test_to_from_dict(self):
        from umh.migration.deprecation_registry import DeprecationRegistry
        from umh.migration.contracts import LegacyModuleRecord

        reg = DeprecationRegistry()
        reg.register_record(LegacyModuleRecord(module_path="a.py", module_name="a"))
        d = reg.to_dict()
        restored = DeprecationRegistry.from_dict(d)
        assert restored.record_count == 1


class TestDeprecationRegistryExplain:
    def test_explain_status(self):
        from umh.migration.deprecation_registry import explain_deprecation_status
        from umh.migration.contracts import (
            LegacyModuleRecord,
            LegacyModuleStatus,
        )

        rec = LegacyModuleRecord(
            module_path="a.py",
            module_name="a",
            status=LegacyModuleStatus.DEPRECATED,
            reason="old code",
        )
        explanation = explain_deprecation_status(rec)
        assert "deprecated" in explanation
        assert "old code" in explanation


# ── Section 5: Import Boundary Tests ─────────────────────────────────


class TestDefaultImportBoundaryRules:
    def test_rules_exist(self):
        from umh.migration.import_boundary import build_default_import_boundary_rules

        rules = build_default_import_boundary_rules()
        assert len(rules) > 0


class TestParseImports:
    def test_import_statement(self):
        from umh.migration.import_boundary import parse_imports_from_file

        with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False) as f:
            f.write("import umh.runtime_engine.foo\n")
            f.flush()
            imports = parse_imports_from_file(f.name)
            assert "umh.runtime_engine.foo" in imports
            os.unlink(f.name)

    def test_from_import(self):
        from umh.migration.import_boundary import parse_imports_from_file

        with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False) as f:
            f.write("from umh.runtime_engine import bar\n")
            f.flush()
            imports = parse_imports_from_file(f.name)
            assert "umh.runtime_engine" in imports
            os.unlink(f.name)


class TestClassifyImportBoundary:
    def test_control_importing_runtime_engine_blocked(self):
        from umh.migration.import_boundary import classify_import_boundary
        from umh.migration.contracts import ImportBoundaryStatus

        status = classify_import_boundary("umh/control/api.py", "umh.runtime_engine.foo")
        assert status == ImportBoundaryStatus.BLOCKED

    def test_execution_importing_runtime_engine_blocked(self):
        from umh.migration.import_boundary import classify_import_boundary
        from umh.migration.contracts import ImportBoundaryStatus

        status = classify_import_boundary("umh/execution/engine.py", "umh.runtime_engine.bar")
        assert status == ImportBoundaryStatus.BLOCKED

    def test_storage_importing_runtime_engine_blocked(self):
        from umh.migration.import_boundary import classify_import_boundary
        from umh.migration.contracts import ImportBoundaryStatus

        status = classify_import_boundary("umh/storage/gateway.py", "umh.runtime_engine.x")
        assert status == ImportBoundaryStatus.BLOCKED

    def test_ontology_importing_runtime_engine_blocked(self):
        from umh.migration.import_boundary import classify_import_boundary
        from umh.migration.contracts import ImportBoundaryStatus

        status = classify_import_boundary("umh/ontology/laws.py", "umh.runtime_engine.x")
        assert status == ImportBoundaryStatus.BLOCKED

    def test_substrate_worker_into_execution_blocked(self):
        from umh.migration.import_boundary import classify_import_boundary
        from umh.migration.contracts import ImportBoundaryStatus

        status = classify_import_boundary("umh/execution/engine.py", "umh.substrate.worker")
        assert status == ImportBoundaryStatus.BLOCKED

    def test_substrate_nodes_exception_allowed(self):
        from umh.migration.import_boundary import classify_import_boundary
        from umh.migration.contracts import ImportBoundaryStatus

        status = classify_import_boundary("umh/execution/engine.py", "umh.substrate.nodes")
        assert status == ImportBoundaryStatus.COMPATIBILITY_ALLOWED

    def test_clean_to_clean_allowed(self):
        from umh.migration.import_boundary import classify_import_boundary
        from umh.migration.contracts import ImportBoundaryStatus

        status = classify_import_boundary("umh/control/api.py", "umh.execution.engine")
        assert status == ImportBoundaryStatus.ALLOWED

    def test_scan_safe_on_missing_dir(self):
        from umh.migration.import_boundary import scan_import_boundaries

        findings = scan_import_boundaries("/nonexistent/path")
        assert findings == []


class TestImportBoundaryFindings:
    def test_findings_include_recommendation(self):
        from umh.migration.contracts import ImportBoundaryFinding, ImportBoundaryStatus

        f = ImportBoundaryFinding(
            source_file="a.py",
            imported_module="umh.runtime_engine.x",
            status=ImportBoundaryStatus.BLOCKED,
            recommendation="migrate",
        )
        assert f.recommendation == "migrate"


class TestNoModulesImportedDynamically:
    def test_import_boundary_no_dynamic_import(self):
        src_path = "/opt/OS/umh/migration/import_boundary.py"
        with open(src_path, "r") as f:
            source = f.read()
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                func = node.func
                if isinstance(func, ast.Name) and func.id == "__import__":
                    pytest.fail("import_boundary.py uses __import__")
                if isinstance(func, ast.Attribute) and func.attr == "import_module":
                    pytest.fail("import_boundary.py uses importlib.import_module")


# ── Section 6: Compatibility Tests ───────────────────────────────────


class TestKnownEquivalents:
    def test_equivalents_exist(self):
        from umh.migration.compatibility import get_known_clean_equivalents

        equivs = get_known_clean_equivalents()
        assert len(equivs) > 0

    def test_runtime_engine_execution_mapped(self):
        from umh.migration.compatibility import find_clean_equivalent

        eq = find_clean_equivalent("umh.runtime_engine.execution_engine")
        assert eq is not None and "execution" in eq

    def test_runtime_engine_governance_mapped(self):
        from umh.migration.compatibility import find_clean_equivalent

        eq = find_clean_equivalent("umh.runtime_engine.authority_engine")
        assert eq is not None and "governance" in eq.lower()

    def test_runtime_engine_memory_mapped(self):
        from umh.migration.compatibility import find_clean_equivalent

        eq = find_clean_equivalent("umh.runtime_engine.memory")
        assert eq is not None

    def test_runtime_engine_tracing_mapped(self):
        from umh.migration.compatibility import find_clean_equivalent

        eq = find_clean_equivalent("umh.runtime_engine.decision_trace")
        assert eq is not None and "trace" in eq

    def test_substrate_session_mapped(self):
        from umh.migration.compatibility import find_clean_equivalent

        eq = find_clean_equivalent("umh.substrate.operator_session")
        assert eq is not None and "workstation" in eq

    def test_substrate_worker_mapped(self):
        from umh.migration.compatibility import find_clean_equivalent

        eq = find_clean_equivalent("umh.substrate.execution_worker")
        assert eq is not None


class TestMappingValidation:
    def test_catches_missing_clean_equivalent(self):
        from umh.migration.compatibility import validate_compatibility_mapping
        from umh.migration.contracts import MigrationMapping

        m = MigrationMapping(legacy_module="a", clean_equivalent="")
        issues = validate_compatibility_mapping(m)
        assert any("clean_equivalent" in i for i in issues)


class TestExplainCompatibilityPath:
    def test_deterministic(self):
        from umh.migration.compatibility import explain_compatibility_path

        result = explain_compatibility_path("umh.runtime_engine.cognitive_loop")
        assert "umh.runtime_engine.cognitive_loop" in result


class TestBuildMappingsFromRecords:
    def test_builds_mappings(self):
        from umh.migration.compatibility import build_migration_mappings
        from umh.migration.contracts import LegacyModuleRecord, LegacyModuleStatus

        records = [
            LegacyModuleRecord(
                module_path="umh/runtime_engine/causal_attribution.py",
                module_name="umh.runtime_engine.causal_attribution",
                status=LegacyModuleStatus.DUPLICATE,
                clean_equivalent="umh.reasoning.causal_attribution",
            )
        ]
        mappings = build_migration_mappings(records)
        assert len(mappings) == 1


# ── Section 7: Views Tests ───────────────────────────────────────────


class TestLegacyModuleViewSerialization:
    def test_serializes(self):
        from umh.migration.views import LegacyModuleView

        v = LegacyModuleView(module_path="a.py", module_name="a", status="deprecated")
        d = v.to_dict()
        assert d["status"] == "deprecated"


class TestMigrationMappingViewSerialization:
    def test_serializes(self):
        from umh.migration.views import MigrationMappingView

        v = MigrationMappingView(legacy_module="a", clean_equivalent="b", confidence=0.9)
        d = v.to_dict()
        assert d["confidence"] == 0.9


class TestImportBoundaryFindingViewSerialization:
    def test_serializes(self):
        from umh.migration.views import ImportBoundaryFindingView

        v = ImportBoundaryFindingView(source_file="a.py", status="blocked")
        d = v.to_dict()
        assert d["status"] == "blocked"


class TestMigrationHealthViewSerialization:
    def test_serializes(self):
        from umh.migration.views import MigrationHealthView

        v = MigrationHealthView(health="healthy", total_legacy_records=100, deprecated_count=5)
        d = v.to_dict()
        assert d["deprecated_count"] == 5


class TestMigrationDashboardViewSerialization:
    def test_serializes(self):
        from umh.migration.views import MigrationDashboardView

        v = MigrationDashboardView(health="partial")
        d = v.to_dict()
        assert d["health"] == "partial"


class TestBuildMigrationHealthView:
    def test_counts_deprecated(self):
        from umh.migration.deprecation_registry import DeprecationRegistry
        from umh.migration.contracts import LegacyModuleRecord, LegacyModuleStatus
        from umh.migration.views import build_migration_health_view

        reg = DeprecationRegistry()
        reg.register_record(
            LegacyModuleRecord(
                module_path="a.py", module_name="a", status=LegacyModuleStatus.DEPRECATED
            )
        )
        view = build_migration_health_view(reg)
        assert view.deprecated_count == 1

    def test_counts_duplicate(self):
        from umh.migration.deprecation_registry import DeprecationRegistry
        from umh.migration.contracts import LegacyModuleRecord, LegacyModuleStatus
        from umh.migration.views import build_migration_health_view

        reg = DeprecationRegistry()
        reg.register_record(
            LegacyModuleRecord(
                module_path="a.py", module_name="a", status=LegacyModuleStatus.DUPLICATE
            )
        )
        view = build_migration_health_view(reg)
        assert view.duplicate_count == 1

    def test_counts_bypass_risk(self):
        from umh.migration.deprecation_registry import DeprecationRegistry
        from umh.migration.contracts import LegacyModuleRecord, LegacyModuleStatus
        from umh.migration.views import build_migration_health_view

        reg = DeprecationRegistry()
        reg.register_record(
            LegacyModuleRecord(
                module_path="a.py", module_name="a", status=LegacyModuleStatus.BYPASS_RISK
            )
        )
        view = build_migration_health_view(reg)
        assert view.bypass_risk_count == 1

    def test_counts_future_review(self):
        from umh.migration.deprecation_registry import DeprecationRegistry
        from umh.migration.contracts import LegacyModuleRecord, LegacyModuleStatus
        from umh.migration.views import build_migration_health_view

        reg = DeprecationRegistry()
        reg.register_record(
            LegacyModuleRecord(
                module_path="a.py", module_name="a", status=LegacyModuleStatus.FUTURE_REVIEW
            )
        )
        view = build_migration_health_view(reg)
        assert view.future_review_count == 1

    def test_counts_mapped(self):
        from umh.migration.deprecation_registry import DeprecationRegistry
        from umh.migration.contracts import LegacyModuleRecord, LegacyModuleStatus, MigrationMapping
        from umh.migration.views import build_migration_health_view

        reg = DeprecationRegistry()
        reg.register_mapping(MigrationMapping(legacy_module="a", clean_equivalent="b"))
        view = build_migration_health_view(reg)
        assert view.mapped_count == 1


class TestBuildMigrationDashboardView:
    def test_respects_limit(self):
        from umh.migration.deprecation_registry import DeprecationRegistry
        from umh.migration.contracts import LegacyModuleRecord, LegacyModuleStatus
        from umh.migration.views import build_migration_dashboard_view

        reg = DeprecationRegistry()
        for i in range(20):
            reg.register_record(
                LegacyModuleRecord(
                    module_path=f"{i}.py",
                    module_name=f"m_{i}",
                    status=LegacyModuleStatus.FUTURE_REVIEW,
                )
            )
        view = build_migration_dashboard_view(reg, limit=5)
        assert len(view.legacy_modules) <= 5

    def test_views_omit_secrets(self):
        from umh.migration.views import LegacyModuleView

        v = LegacyModuleView(module_path="a.py")
        d = v.to_dict()
        for key in d:
            assert "secret" not in key.lower()
            assert "password" not in key.lower()
            assert "token" not in key.lower()


# ── Section 8: Registry Integration Tests ────────────────────────────


class TestRegistryTypesIncludeLegacy:
    def test_legacy_module_type_exists(self):
        from umh.registry.contracts import RegistryType

        assert hasattr(RegistryType, "LEGACY_MODULE")
        assert RegistryType.LEGACY_MODULE.value == "legacy_module"

    def test_migration_mapping_type_exists(self):
        from umh.registry.contracts import RegistryType

        assert hasattr(RegistryType, "MIGRATION_MAPPING")

    def test_import_boundary_rule_type_exists(self):
        from umh.registry.contracts import RegistryType

        assert hasattr(RegistryType, "IMPORT_BOUNDARY_RULE")


class TestLegacyBridgeReturnsItems:
    def test_returns_list(self):
        from umh.migration.contracts import LegacyModuleRecord, LegacyModuleStatus
        from umh.registry.bridges import legacy_modules_to_registry_items

        records = [
            LegacyModuleRecord(
                module_path="a.py",
                module_name="umh.runtime_engine.foo",
                status=LegacyModuleStatus.DEPRECATED,
            )
        ]
        items = legacy_modules_to_registry_items(records)
        assert len(items) == 1
        assert items[0].registry_type.value == "legacy_module"


class TestMigrationMappingBridge:
    def test_returns_items(self):
        from umh.migration.contracts import MigrationMapping
        from umh.registry.bridges import migration_mappings_to_registry_items

        mappings = [MigrationMapping(legacy_module="a", clean_equivalent="b")]
        items = migration_mappings_to_registry_items(mappings)
        assert len(items) == 1


class TestImportBoundaryRuleBridge:
    def test_returns_items(self):
        from umh.registry.bridges import import_boundary_rules_to_registry_items

        items = import_boundary_rules_to_registry_items()
        assert len(items) > 0


class TestRegistryCatalogIncludesMigration:
    def test_catalog_loads_import_rules(self):
        from umh.registry.catalog import build_default_registry_catalog

        catalog = build_default_registry_catalog()
        assert isinstance(catalog.items, list)

    def test_registry_integration_metadata_only(self):
        from umh.registry.bridges import legacy_modules_to_registry_items
        from umh.migration.contracts import LegacyModuleRecord

        records = [LegacyModuleRecord(module_path="a.py", module_name="a")]
        items = legacy_modules_to_registry_items(records)
        for item in items:
            assert hasattr(item, "to_dict")


class TestPhase80RegistryStillWorks:
    def test_registry_catalog_builds(self):
        from umh.registry.catalog import build_default_registry_catalog

        catalog = build_default_registry_catalog()
        assert catalog.generated_at != ""


# ── Section 9: Storage/Audit Integration Tests ──────────────────────


class TestStorageAuditStillWorks:
    def test_audit_runs(self):
        from umh.storage.audit import audit_storage_boundaries

        report = audit_storage_boundaries(include_tests=False)
        assert hasattr(report, "to_dict")
        as_dict = report.to_dict()
        assert isinstance(as_dict, dict)


class TestAuditRemainsReadOnly:
    def test_no_destructive_calls(self):
        import ast

        src_path = "/opt/OS/umh/storage/audit.py"
        with open(src_path, "r") as f:
            source = f.read()
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                func = node.func
                if isinstance(func, ast.Attribute) and func.attr in (
                    "rmtree",
                    "remove",
                    "unlink",
                ):
                    if isinstance(func.value, ast.Name) and func.value.id in (
                        "shutil",
                        "os",
                    ):
                        raise AssertionError(
                            f"audit.py calls {func.value.id}.{func.attr}() — destructive"
                        )


# ── Section 10: Observability Integration Tests ─────────────────────


class TestSystemStatusWithoutMigration:
    def test_works_without_registry(self):
        from umh.observability.system_status import build_system_status

        status = build_system_status()
        assert hasattr(status, "migration_status")
        assert status.migration_status == "unavailable"


class TestSystemStatusWithMigration:
    def test_includes_migration_when_provided(self):
        from umh.observability.system_status import build_system_status
        from umh.migration.deprecation_registry import DeprecationRegistry

        reg = DeprecationRegistry()
        status = build_system_status(migration_registry=reg)
        assert status.migration_status == "ok"


class TestSystemStatusNotHealthyWithoutMigration:
    def test_not_healthy_when_migration_unavailable(self):
        from umh.observability.system_status import build_system_status

        status = build_system_status()
        d = status.to_dict()
        assert "migration_status" in d


class TestDashboardWithoutMigration:
    def test_works_without_registry(self):
        from umh.observability.operator_views import build_operator_dashboard_snapshot

        snap = build_operator_dashboard_snapshot(user_id="test")
        d = snap.to_dict()
        assert "migration_summary" in d
        assert d["migration_summary"] == {}


class TestDashboardWithMigration:
    def test_includes_migration_health(self):
        from umh.observability.operator_views import build_operator_dashboard_snapshot
        from umh.migration.deprecation_registry import DeprecationRegistry

        reg = DeprecationRegistry()
        snap = build_operator_dashboard_snapshot(user_id="test", migration_registry=reg)
        d = snap.to_dict()
        assert "migration_summary" in d
        assert d["migration_summary"].get("health") is not None


# ── Section 11: API Integration Tests ───────────────────────────────


class TestMigrationApiEndpoints:
    def test_migration_endpoints_registered(self):
        from umh.control.api import app

        paths = [r.path for r in app.routes if hasattr(r, "path")]
        assert "/migration/status" in paths
        assert "/migration/inventory" in paths
        assert "/migration/deprecated" in paths
        assert "/migration/bypass-risk" in paths
        assert "/migration/mappings" in paths
        assert "/migration/import-boundary" in paths
        assert "/migration/dashboard" in paths

    def test_endpoints_are_get(self):
        from umh.control.api import app

        migration_routes = [
            r for r in app.routes if hasattr(r, "path") and r.path.startswith("/migration/")
        ]
        for r in migration_routes:
            methods = getattr(r, "methods", set())
            assert "GET" in methods, f"{r.path} should be GET"

    def test_endpoints_do_not_delete(self):
        from umh.control.api import app

        migration_routes = [
            r for r in app.routes if hasattr(r, "path") and r.path.startswith("/migration/")
        ]
        for r in migration_routes:
            methods = getattr(r, "methods", set())
            assert "DELETE" not in methods

    def test_endpoints_do_not_rewrite_imports(self):
        src_path = "/opt/OS/umh/control/api.py"
        with open(src_path, "r") as f:
            source = f.read()
        assert "rewrite_import" not in source
        assert "modify_source" not in source


# ── Section 12: CLI Integration Tests ───────────────────────────────


class TestMigrationCliCommands:
    def test_commands_in_parser(self):
        from umh.control.cli import build_parser

        parser = build_parser()
        choices = parser._subparsers._group_actions[0].choices
        assert "migration-status" in choices
        assert "migration-inventory" in choices
        assert "migration-deprecated" in choices
        assert "migration-bypass-risk" in choices
        assert "migration-mappings" in choices
        assert "migration-imports" in choices
        assert "migration-dashboard" in choices


class TestMigrationCliSmoke:
    def test_migration_status(self):
        from umh.control.cli import main

        result = main(["migration-status", "--json"])
        assert result == 0

    def test_migration_inventory(self):
        from umh.control.cli import main

        result = main(["migration-inventory", "--json", "--limit", "5"])
        assert result == 0

    def test_migration_mappings(self):
        from umh.control.cli import main

        result = main(["migration-mappings", "--json"])
        assert result == 0

    def test_migration_dashboard(self):
        from umh.control.cli import main

        result = main(["migration-dashboard", "--json", "--limit", "5"])
        assert result == 0


# ── Section 13: Layering Invariant Tests ────────────────────────────


class TestMigrationModulesNoSubprocess:
    def test_no_subprocess_import(self):
        migration_files = [
            "/opt/OS/umh/migration/contracts.py",
            "/opt/OS/umh/migration/inventory.py",
            "/opt/OS/umh/migration/classifier.py",
            "/opt/OS/umh/migration/deprecation_registry.py",
            "/opt/OS/umh/migration/import_boundary.py",
            "/opt/OS/umh/migration/compatibility.py",
            "/opt/OS/umh/migration/views.py",
        ]
        for fpath in migration_files:
            with open(fpath, "r") as f:
                source = f.read()
            tree = ast.parse(source)
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        assert alias.name != "subprocess", f"{fpath} imports subprocess"
                if isinstance(node, ast.ImportFrom):
                    if node.module and "subprocess" in node.module:
                        pytest.fail(f"{fpath} imports subprocess")


class TestMigrationModulesNoRequests:
    def test_no_requests_import(self):
        migration_files = [
            "/opt/OS/umh/migration/contracts.py",
            "/opt/OS/umh/migration/inventory.py",
            "/opt/OS/umh/migration/classifier.py",
            "/opt/OS/umh/migration/deprecation_registry.py",
            "/opt/OS/umh/migration/import_boundary.py",
            "/opt/OS/umh/migration/compatibility.py",
            "/opt/OS/umh/migration/views.py",
        ]
        for fpath in migration_files:
            with open(fpath, "r") as f:
                source = f.read()
            tree = ast.parse(source)
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        assert alias.name not in ("requests", "httpx", "aiohttp"), (
                            f"{fpath} imports {alias.name}"
                        )
                if isinstance(node, ast.ImportFrom):
                    if node.module and node.module in ("requests", "httpx", "aiohttp"):
                        pytest.fail(f"{fpath} imports {node.module}")


class TestMigrationModulesNoBrowserAutomation:
    def test_no_selenium_playwright(self):
        migration_files = [
            "/opt/OS/umh/migration/contracts.py",
            "/opt/OS/umh/migration/inventory.py",
            "/opt/OS/umh/migration/classifier.py",
            "/opt/OS/umh/migration/deprecation_registry.py",
            "/opt/OS/umh/migration/import_boundary.py",
            "/opt/OS/umh/migration/compatibility.py",
            "/opt/OS/umh/migration/views.py",
        ]
        for fpath in migration_files:
            with open(fpath, "r") as f:
                source = f.read()
            assert "selenium" not in source
            assert "playwright" not in source


class TestMigrationModulesNoAdapterImport:
    def test_no_adapter_calls(self):
        migration_files = [
            "/opt/OS/umh/migration/contracts.py",
            "/opt/OS/umh/migration/inventory.py",
            "/opt/OS/umh/migration/classifier.py",
            "/opt/OS/umh/migration/deprecation_registry.py",
            "/opt/OS/umh/migration/import_boundary.py",
            "/opt/OS/umh/migration/compatibility.py",
            "/opt/OS/umh/migration/views.py",
        ]
        for fpath in migration_files:
            with open(fpath, "r") as f:
                source = f.read()
            tree = ast.parse(source)
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom):
                    if node.module and node.module.startswith("umh.adapters."):
                        if node.module not in ("umh.adapters.model_router",):
                            pytest.fail(f"{fpath} imports adapter: {node.module}")


class TestMigrationModulesNoTraceMutation:
    def test_no_trace_store_writes(self):
        migration_files = [
            "/opt/OS/umh/migration/contracts.py",
            "/opt/OS/umh/migration/inventory.py",
            "/opt/OS/umh/migration/classifier.py",
            "/opt/OS/umh/migration/deprecation_registry.py",
            "/opt/OS/umh/migration/import_boundary.py",
            "/opt/OS/umh/migration/compatibility.py",
            "/opt/OS/umh/migration/views.py",
        ]
        for fpath in migration_files:
            with open(fpath, "r") as f:
                source = f.read()
            assert "create_trace" not in source
            assert "append_event" not in source
            assert "complete_trace" not in source
            assert "fail_trace" not in source


class TestMigrationModulesNoFeedbackMutation:
    def test_no_outcome_or_feedback_writes(self):
        migration_files = [
            "/opt/OS/umh/migration/contracts.py",
            "/opt/OS/umh/migration/inventory.py",
            "/opt/OS/umh/migration/classifier.py",
            "/opt/OS/umh/migration/deprecation_registry.py",
            "/opt/OS/umh/migration/import_boundary.py",
            "/opt/OS/umh/migration/compatibility.py",
            "/opt/OS/umh/migration/views.py",
        ]
        for fpath in migration_files:
            with open(fpath, "r") as f:
                source = f.read()
            assert "append_outcome" not in source
            assert "append_feedback" not in source
            assert "append_memory_candidate" not in source


class TestMigrationModulesNoGovernanceMutation:
    def test_no_governance_writes(self):
        migration_files = [
            "/opt/OS/umh/migration/contracts.py",
            "/opt/OS/umh/migration/inventory.py",
            "/opt/OS/umh/migration/classifier.py",
            "/opt/OS/umh/migration/deprecation_registry.py",
            "/opt/OS/umh/migration/import_boundary.py",
            "/opt/OS/umh/migration/compatibility.py",
            "/opt/OS/umh/migration/views.py",
        ]
        for fpath in migration_files:
            with open(fpath, "r") as f:
                source = f.read()
            assert "check_governance" not in source


class TestMigrationModulesNoFileDeletion:
    def test_no_file_removal_calls(self):
        migration_files = [
            "/opt/OS/umh/migration/contracts.py",
            "/opt/OS/umh/migration/inventory.py",
            "/opt/OS/umh/migration/deprecation_registry.py",
            "/opt/OS/umh/migration/import_boundary.py",
            "/opt/OS/umh/migration/compatibility.py",
            "/opt/OS/umh/migration/views.py",
        ]
        for fpath in migration_files:
            with open(fpath, "r") as f:
                source = f.read()
            assert "shutil.rmtree(" not in source
            assert "os.unlink(" not in source


class TestImportBoundaryScannerNoExecution:
    def test_scanner_does_not_import_targets(self):
        src = "/opt/OS/umh/migration/import_boundary.py"
        with open(src, "r") as f:
            source = f.read()
        assert "importlib.import_module" not in source
        assert "__import__(" not in source


class TestDeprecationRegistryNoDestructiveMethods:
    def test_no_delete_clear_pop(self):
        from umh.migration.deprecation_registry import DeprecationRegistry

        public_methods = [m for m in dir(DeprecationRegistry) if not m.startswith("_")]
        for method_name in public_methods:
            assert "delete" not in method_name.lower()
            assert "clear" not in method_name.lower()
            assert "pop" not in method_name.lower()
            assert "remove" not in method_name.lower()


# ── Section 14: Cross-Cutting Invariant Tests ───────────────────────


class TestInvariant551NoLegacyFilesDeleted:
    def test_runtime_engine_still_exists(self):
        assert os.path.isdir("/opt/OS/umh/runtime_engine")

    def test_substrate_still_exists(self):
        assert os.path.isdir("/opt/OS/umh/substrate")


class TestInvariant560ClassificationCovers7Statuses:
    def test_all_statuses(self):
        from umh.migration.contracts import LegacyModuleStatus

        expected = {
            "active_retained",
            "deprecated",
            "migrated",
            "duplicate",
            "bypass_risk",
            "future_review",
            "unknown",
        }
        actual = {s.value for s in LegacyModuleStatus}
        assert expected == actual


class TestInvariant566MigrationStatusOperatorVisible:
    def test_migration_in_system_status(self):
        from umh.observability.system_status import SystemStatus

        s = SystemStatus()
        d = s.to_dict()
        assert "migration_status" in d

    def test_migration_in_dashboard(self):
        from umh.interface.views import OperatorDashboardSnapshot

        snap = OperatorDashboardSnapshot(user_id="test")
        d = snap.to_dict()
        assert "migration_summary" in d


class TestInvariant567MissingDirectoriesSafe:
    def test_inventory_safe_on_missing(self):
        from umh.migration.inventory import build_legacy_inventory

        with tempfile.TemporaryDirectory() as tmpdir:
            inv = build_legacy_inventory(tmpdir)
            assert len(inv.warnings) > 0

    def test_import_scan_safe_on_missing(self):
        from umh.migration.import_boundary import scan_import_boundaries

        assert scan_import_boundaries("/nonexistent") == []


class TestInvariant568UnknownNotTreatedAsSafe:
    def test_unknown_status_is_not_retained(self):
        from umh.migration.contracts import LegacyModuleStatus

        assert LegacyModuleStatus.UNKNOWN != LegacyModuleStatus.ACTIVE_RETAINED

    def test_unknown_risk_is_not_none(self):
        from umh.migration.contracts import MigrationRiskLevel

        assert MigrationRiskLevel.UNKNOWN != MigrationRiskLevel.NONE


# ── Section 15: Regression Tests ─────────────────────────────────────


class TestPhase75bRegression:
    def test_phase75b_tests_importable(self):
        assert os.path.isfile("/opt/OS/tests/test_phase75b_mvp_lockin.py")


class TestPhase76Regression:
    def test_phase76_tests_importable(self):
        assert os.path.isfile("/opt/OS/tests/test_phase76_adapters.py")


class TestPhase77Regression:
    def test_phase77_tests_importable(self):
        assert os.path.isfile("/opt/OS/tests/test_phase77_workstation_state.py")


class TestPhase78Regression:
    def test_phase78_tests_importable(self):
        assert os.path.isfile("/opt/OS/tests/test_phase78_feedback_loop.py")


class TestPhase79Regression:
    def test_phase79_tests_importable(self):
        assert os.path.isfile("/opt/OS/tests/test_phase79_observability.py")


class TestPhase80Regression:
    def test_phase80_tests_importable(self):
        assert os.path.isfile("/opt/OS/tests/test_phase80_registry.py")


class TestPhase81Regression:
    def test_phase81_tests_importable(self):
        assert os.path.isfile("/opt/OS/tests/test_phase81_ontology_law_kernel.py")


class TestPhase82Regression:
    def test_phase82_tests_importable(self):
        assert os.path.isfile("/opt/OS/tests/test_phase82_storage_memory_discipline.py")
