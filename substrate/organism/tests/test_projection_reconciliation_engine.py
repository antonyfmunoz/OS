"""Tests for ProjectionReconciliationEngine (Phase 14.0)."""

from __future__ import annotations

import json
import os
import tempfile

import pytest

from substrate.organism.projection_reconciliation_engine import (
    DivergenceSeverity,
    DivergenceType,
    ProjectionDivergence,
    ProjectionReconciliationEngine,
)
from substrate.organism.projection_source_registry import (
    ProjectionName,
    ProjectionSource,
    ProjectionSourceRegistry,
    ProjectionSourceType,
    ReadStatus,
    SourceCanonicality,
    create_initial_registry,
)


class TestDivergenceType:
    def test_all_types_present(self):
        expected = {
            "missing_source", "duplicate_source", "stale_document", "stale_code",
            "partial_backend", "uninspected_source", "conflicting_claim",
            "local_uncommitted_source", "github_lag", "docs_ahead_of_code",
            "code_ahead_of_docs", "unknown_canonicality", "schema_version_split",
            "code_duplication", "schema_drift", "type_inconsistency",
            "instance_context_in_data",
        }
        actual = {e.value for e in DivergenceType}
        assert actual == expected


class TestDivergenceSeverity:
    def test_all_severities_present(self):
        expected = {"critical", "high", "medium", "low", "info"}
        actual = {e.value for e in DivergenceSeverity}
        assert actual == expected


class TestProjectionDivergence:
    def test_default_values(self):
        d = ProjectionDivergence()
        assert d.divergence_id.startswith("div-")
        assert d.projection == ProjectionName.UNKNOWN.value

    def test_to_dict(self):
        d = ProjectionDivergence(
            divergence_id="test-div-1",
            projection="EOS",
            divergence_type=DivergenceType.PARTIAL_BACKEND.value,
            severity=DivergenceSeverity.HIGH.value,
        )
        data = d.to_dict()
        assert data["divergence_id"] == "test-div-1"
        assert data["projection"] == "EOS"
        assert data["divergence_type"] == "partial_backend"

    def test_from_dict(self):
        data = {
            "divergence_id": "test-div-2",
            "projection": "UMH",
            "divergence_type": "schema_drift",
        }
        d = ProjectionDivergence.from_dict(data)
        assert d.divergence_id == "test-div-2"
        assert d.projection == "UMH"

    def test_roundtrip_serialization(self):
        original = ProjectionDivergence(
            divergence_id="rt-div-1",
            projection="CreatorOS",
            evidence=["test evidence"],
            requires_permission=True,
        )
        data = original.to_dict()
        restored = ProjectionDivergence.from_dict(data)
        assert restored.divergence_id == original.divergence_id
        assert restored.evidence == original.evidence


def _make_test_sources() -> list[ProjectionSource]:
    """Test-only source data for engine tests."""
    return [
        ProjectionSource(
            source_id="psrc-docs",
            projection="Shared",
            source_type=ProjectionSourceType.GOOGLE_DOCS.value,
            name="docs_source",
            permission_required=True,
            read_status=ReadStatus.UNREAD.value,
            canonicality=SourceCanonicality.CANDIDATE_CANONICAL.value,
        ),
        ProjectionSource(
            source_id="psrc-github",
            projection="Shared",
            source_type=ProjectionSourceType.GITHUB_REPOSITORY.value,
            name="github_source",
            permission_required=True,
            read_status=ReadStatus.UNREAD.value,
            canonicality=SourceCanonicality.CANDIDATE_CANONICAL.value,
        ),
        ProjectionSource(
            source_id="psrc-device",
            projection="Shared",
            source_type=ProjectionSourceType.DEVICE_FILESYSTEM.value,
            name="device_source",
            permission_required=True,
            read_status=ReadStatus.UNREAD.value,
            canonicality=SourceCanonicality.CANDIDATE_CANONICAL.value,
        ),
        ProjectionSource(
            source_id="psrc-local-umh",
            projection="UMH",
            source_type=ProjectionSourceType.LOCAL_FILESYSTEM.value,
            name="umh_source",
            permission_required=False,
            read_status=ReadStatus.INSPECTED.value,
            canonicality=SourceCanonicality.PRODUCTION_TRUTH.value,
        ),
        ProjectionSource(
            source_id="psrc-partial",
            projection="EOS",
            source_type=ProjectionSourceType.LOCAL_FILESYSTEM.value,
            name="partial_backend",
            permission_required=False,
            read_status=ReadStatus.INSPECTED.value,
            canonicality=SourceCanonicality.PARTIAL.value,
        ),
    ]


class TestProjectionReconciliationEngine:
    def _make_engine(self):
        reg_file = tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False)
        diag_file = tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False)
        reg = create_initial_registry(path=reg_file.name, sources=_make_test_sources())
        engine = ProjectionReconciliationEngine(
            registry=reg, diagnostics_path=diag_file.name
        )
        return engine, reg_file.name, diag_file.name

    def test_run_diagnostic_finds_uninspected(self):
        engine, reg_path, diag_path = self._make_engine()
        try:
            findings = engine.run_diagnostic()
            uninspected = [f for f in findings if f.divergence_type == DivergenceType.UNINSPECTED_SOURCE.value]
            assert len(uninspected) == 3
        finally:
            os.unlink(reg_path)
            os.unlink(diag_path)

    def test_run_diagnostic_finds_partial_backend(self):
        engine, reg_path, diag_path = self._make_engine()
        try:
            findings = engine.run_diagnostic()
            partial = [f for f in findings if f.divergence_type == DivergenceType.PARTIAL_BACKEND.value]
            assert len(partial) == 1
            assert partial[0].projection == "EOS"
        finally:
            os.unlink(reg_path)
            os.unlink(diag_path)

    def test_run_diagnostic_finds_schema_version_split(self):
        engine, reg_path, diag_path = self._make_engine()
        try:
            findings = engine.run_diagnostic()
            schema = [f for f in findings if f.divergence_type == DivergenceType.SCHEMA_VERSION_SPLIT.value]
            assert len(schema) == 1
        finally:
            os.unlink(reg_path)
            os.unlink(diag_path)

    def test_run_diagnostic_finds_code_duplication(self):
        engine, reg_path, diag_path = self._make_engine()
        try:
            findings = engine.run_diagnostic()
            dupes = [f for f in findings if f.divergence_type == DivergenceType.CODE_DUPLICATION.value]
            assert len(dupes) == 1
        finally:
            os.unlink(reg_path)
            os.unlink(diag_path)

    def test_run_diagnostic_finds_schema_drift(self):
        engine, reg_path, diag_path = self._make_engine()
        try:
            findings = engine.run_diagnostic()
            drift = [f for f in findings if f.divergence_type == DivergenceType.SCHEMA_DRIFT.value]
            assert len(drift) == 1
        finally:
            os.unlink(reg_path)
            os.unlink(diag_path)

    def test_run_diagnostic_finds_type_inconsistency(self):
        engine, reg_path, diag_path = self._make_engine()
        try:
            findings = engine.run_diagnostic()
            types = [f for f in findings if f.divergence_type == DivergenceType.TYPE_INCONSISTENCY.value]
            assert len(types) == 1
        finally:
            os.unlink(reg_path)
            os.unlink(diag_path)

    def test_no_destructive_sync(self):
        engine, reg_path, diag_path = self._make_engine()
        try:
            findings = engine.run_diagnostic()
            for f in findings:
                assert "delete" not in f.recommendation.lower()
                assert "overwrite" not in f.recommendation.lower()
                assert "force" not in f.recommendation.lower()
        finally:
            os.unlink(reg_path)
            os.unlink(diag_path)

    def test_summary(self):
        engine, reg_path, diag_path = self._make_engine()
        try:
            engine.run_diagnostic()
            s = engine.summary()
            assert s["total_divergences"] == 9
            assert "high" in s["by_severity"]
        finally:
            os.unlink(reg_path)
            os.unlink(diag_path)

    def test_list_divergences_by_projection(self):
        engine, reg_path, diag_path = self._make_engine()
        try:
            engine.run_diagnostic()
            eos = engine.list_divergences(projection="EOS")
            assert len(eos) >= 4
        finally:
            os.unlink(reg_path)
            os.unlink(diag_path)

    def test_list_divergences_by_severity(self):
        engine, reg_path, diag_path = self._make_engine()
        try:
            engine.run_diagnostic()
            high = engine.list_divergences(severity="high")
            assert len(high) >= 3
        finally:
            os.unlink(reg_path)
            os.unlink(diag_path)

    def test_persistence(self):
        reg_file = tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False)
        diag_file = tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False)
        try:
            reg = create_initial_registry(path=reg_file.name, sources=_make_test_sources())
            engine1 = ProjectionReconciliationEngine(registry=reg, diagnostics_path=diag_file.name)
            engine1.run_diagnostic()

            engine2 = ProjectionReconciliationEngine(registry=reg, diagnostics_path=diag_file.name)
            assert len(engine2.list_divergences()) == 9
        finally:
            os.unlink(reg_file.name)
            os.unlink(diag_file.name)

    def test_instance_context_found(self):
        engine, reg_path, diag_path = self._make_engine()
        try:
            findings = engine.run_diagnostic()
            ic = [f for f in findings if f.divergence_type == DivergenceType.INSTANCE_CONTEXT_IN_DATA.value]
            assert len(ic) == 1
        finally:
            os.unlink(reg_path)
            os.unlink(diag_path)


class TestNoHardcodedJarvisTerminology:
    def test_no_jarvis_in_registry(self):
        import inspect
        from substrate.organism import projection_source_registry
        source = inspect.getsource(projection_source_registry)
        assert "jarvis" not in source.lower()
        assert "Jarvis" not in source

    def test_no_jarvis_in_engine(self):
        import inspect
        from substrate.organism import projection_reconciliation_engine
        source = inspect.getsource(projection_reconciliation_engine)
        assert "jarvis" not in source.lower()

    def test_no_jarvis_in_readiness_gate(self):
        import inspect
        from substrate.organism import projection_readiness_gate
        source = inspect.getsource(projection_readiness_gate)
        assert "jarvis" not in source.lower()


class TestNoExternalWrites:
    def _make_engine(self):
        reg_file = tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False)
        diag_file = tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False)
        reg = create_initial_registry(path=reg_file.name, sources=_make_test_sources())
        engine = ProjectionReconciliationEngine(
            registry=reg, diagnostics_path=diag_file.name
        )
        return engine, reg_file.name, diag_file.name

    def test_engine_only_writes_local(self):
        engine, reg_path, diag_path = self._make_engine()
        try:
            engine.run_diagnostic()
            assert os.path.isfile(diag_path)
            with open(diag_path) as f:
                content = f.read()
            assert "ssh" not in content.lower()
            assert "github.com" not in content
            assert "drive.google.com" not in content
        finally:
            os.unlink(reg_path)
            os.unlink(diag_path)


class TestReadinessGate:
    def test_blocks_feature_build_with_uninspected_sources(self):
        os.environ["UMH_ROOT"] = "/tmp/test_readiness_nonexistent"
        try:
            from substrate.organism.projection_readiness_gate import assess_projection_readiness
            report = assess_projection_readiness()
            assert report["ready_for_feature_build"] is False
        finally:
            if "UMH_ROOT" in os.environ:
                del os.environ["UMH_ROOT"]

    def test_readiness_returns_blocking_issues(self):
        os.environ["UMH_ROOT"] = "/tmp/test_readiness_nonexistent"
        try:
            from substrate.organism.projection_readiness_gate import assess_projection_readiness
            report = assess_projection_readiness()
            assert len(report["blocking_issues"]) > 0
        finally:
            if "UMH_ROOT" in os.environ:
                del os.environ["UMH_ROOT"]

    def test_readiness_returns_required_structure(self):
        os.environ["UMH_ROOT"] = "/tmp/test_readiness_nonexistent"
        try:
            from substrate.organism.projection_readiness_gate import assess_projection_readiness
            report = assess_projection_readiness()
            assert "ready_for_feature_build" in report
            assert "ready_for_source_inspection" in report
            assert "ready_for_convergence_execution" in report
            assert "blocking_issues" in report
            assert "required_permissions" in report
            assert "uninspected_sources" in report
            assert "canonicality_unknowns" in report
            assert "recommended_next_phase" in report
            assert "evidence" in report
        finally:
            if "UMH_ROOT" in os.environ:
                del os.environ["UMH_ROOT"]


class TestWorkPacketGeneration:
    def test_work_packets_file_structure(self):
        path = os.path.join(
            os.path.dirname(__file__), "..", "..", "..",
            "data", "umh", "projection_reconciliation", "phase14_0_work_packets.json"
        )
        if not os.path.isfile(path):
            pytest.skip("Work packets not generated in worktree")
        with open(path) as f:
            data = json.load(f)
        packets = data.get("work_packets", [])
        assert len(packets) == 10

    def test_work_packets_have_required_fields(self):
        path = os.path.join(
            os.path.dirname(__file__), "..", "..", "..",
            "data", "umh", "projection_reconciliation", "phase14_0_work_packets.json"
        )
        if not os.path.isfile(path):
            pytest.skip("Work packets not generated in worktree")
        with open(path) as f:
            data = json.load(f)
        required_fields = [
            "id", "title", "objective", "source_scope", "permissions_required",
            "selected_device_runtime", "risk_class", "expected_artifacts",
            "validation_plan", "rollback_no_mutation_rule", "human_decisions_required",
        ]
        for wp in data["work_packets"]:
            for field in required_fields:
                assert field in wp, f"Work packet {wp.get('id', '?')} missing field: {field}"

    def test_work_packets_no_destructive_operations(self):
        path = os.path.join(
            os.path.dirname(__file__), "..", "..", "..",
            "data", "umh", "projection_reconciliation", "phase14_0_work_packets.json"
        )
        if not os.path.isfile(path):
            pytest.skip("Work packets not generated in worktree")
        with open(path) as f:
            content = f.read()
        assert "delete" not in content.lower() or "No" in content
        assert "overwrite" not in content.lower()
        assert "force-push" not in content.lower()


class TestNoSecretsExposed:
    def test_no_api_keys_in_data_files(self):
        data_dir = os.path.join(
            os.path.dirname(__file__), "..", "..", "..",
            "data", "umh", "projection_reconciliation",
        )
        if not os.path.isdir(data_dir):
            pytest.skip("Data dir not present")
        for fname in os.listdir(data_dir):
            if fname.endswith(".json"):
                with open(os.path.join(data_dir, fname)) as f:
                    content = f.read()
                assert "sk-" not in content
                assert "ANTHROPIC_API_KEY" not in content
                assert "password" not in content.lower() or "no" in content.lower()

    def test_no_secrets_in_source_registry(self):
        import inspect
        from substrate.organism import projection_source_registry
        source = inspect.getsource(projection_source_registry)
        assert "sk-" not in source
        assert "api_key" not in source.lower()


class TestAPIRouteAuth:
    def test_all_routes_use_operator_guard(self):
        routes_path = os.path.join(
            os.path.dirname(__file__), "..", "..", "..",
            "transports", "api", "http", "routes", "organism.ts",
        )
        if not os.path.isfile(routes_path):
            pytest.skip("Routes file not present")
        with open(routes_path) as f:
            content = f.read()
        recon_section = content[content.find("projection-reconciliation"):]
        route_lines = [l for l in recon_section.split("\n") if "router.get(" in l or "router.post(" in l]
        for line in route_lines:
            if "projection-reconciliation" in line:
                assert "operatorGuard" in line, f"Route missing operatorGuard: {line.strip()}"
