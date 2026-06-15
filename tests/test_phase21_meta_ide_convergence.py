"""Tests for Phase 21 — Meta IDE Convergence.

Validates repository awareness, workspace intelligence, roadmap
awareness, read-only guarantee, and reality integration.
"""

from __future__ import annotations

import os
import sys
import tempfile
import time
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.environ.get("UMH_ROOT", "/opt/OS"))


# ── Workcell A: Repository Model Contracts ─────────────────────────────────


class TestRepositoryModelContracts:
    def test_repository_health_status_values(self):
        from substrate.meta_ide.repository_model import RepositoryHealthStatus

        assert RepositoryHealthStatus.HEALTHY == "healthy"
        assert RepositoryHealthStatus.DIRTY == "dirty"
        assert RepositoryHealthStatus.STALE == "stale"
        assert RepositoryHealthStatus.DETACHED == "detached"
        assert RepositoryHealthStatus.UNKNOWN == "unknown"

    def test_branch_snapshot_defaults(self):
        from substrate.meta_ide.repository_model import BranchSnapshot

        bs = BranchSnapshot(branch_name="main")
        assert bs.branch_name == "main"
        assert bs.ahead_count == 0
        assert bs.behind_count == 0
        assert bs.is_current is False

    def test_worktree_snapshot_defaults(self):
        from substrate.meta_ide.repository_model import WorktreeSnapshot

        ws = WorktreeSnapshot(path="/tmp/wt-test")
        assert ws.path == "/tmp/wt-test"
        assert ws.is_locked is False
        assert ws.is_detached is False

    def test_repository_snapshot_defaults(self):
        from substrate.meta_ide.repository_model import RepositorySnapshot

        snap = RepositorySnapshot(repo_name="test", repo_path="/tmp/test")
        assert snap.repo_name == "test"
        assert snap.dirty_files == []
        assert snap.worktree_count == 0
        assert snap.health.status.value == "unknown"

    def test_repository_health_defaults(self):
        from substrate.meta_ide.repository_model import RepositoryHealth

        h = RepositoryHealth()
        assert h.dirty_file_count == 0
        assert h.stale_branch_count == 0
        assert h.issues == []


# ── Workcell A: Repository Reader ──────────────────────────────────────────


class TestRepositoryReader:
    def test_reader_uses_umh_root(self):
        from substrate.meta_ide.repository_model import RepositoryReader

        reader = RepositoryReader()
        assert reader._repo_path in [
            os.environ.get("UMH_ROOT", "/opt/OS"),
            "/opt/OS",
        ]

    def test_reader_custom_path(self):
        from substrate.meta_ide.repository_model import RepositoryReader

        reader = RepositoryReader("/tmp/test-repo")
        assert reader._repo_path == "/tmp/test-repo"

    @patch("substrate.meta_ide.repository_model.gated_subprocess_run")
    def test_snapshot_returns_repo_name(self, mock_run):
        from substrate.meta_ide.repository_model import RepositoryReader

        result = MagicMock()
        result.returncode = 0
        result.stdout = ""
        mock_run.return_value = result

        reader = RepositoryReader("/tmp/test-repo")
        snap = reader.snapshot()
        assert snap.repo_name == "test-repo"
        assert snap.repo_path == "/tmp/test-repo"

    @patch("substrate.meta_ide.repository_model.gated_subprocess_run")
    def test_snapshot_parses_current_branch(self, mock_run):
        from substrate.meta_ide.repository_model import RepositoryReader

        def side_effect(cmd, *args, **kwargs):
            result = MagicMock()
            result.returncode = 0
            if "rev-parse" in cmd and "--abbrev-ref" in cmd:
                result.stdout = "feature/test\n"
            else:
                result.stdout = ""
            return result

        mock_run.side_effect = side_effect

        reader = RepositoryReader("/tmp/test-repo")
        snap = reader.snapshot()
        assert snap.current_branch == "feature/test"

    @patch("substrate.meta_ide.repository_model.gated_subprocess_run")
    def test_dirty_files_detection(self, mock_run):
        from substrate.meta_ide.repository_model import RepositoryReader

        def side_effect(cmd, *args, **kwargs):
            result = MagicMock()
            result.returncode = 0
            if "status" in cmd and "--porcelain" in cmd and "-u" in cmd:
                result.stdout = " M file1.py\n?? file2.py\n"
            elif "status" in cmd and "--porcelain" in cmd:
                result.stdout = "M  file3.py\n"
            else:
                result.stdout = ""
            return result

        mock_run.side_effect = side_effect

        reader = RepositoryReader("/tmp/test-repo")
        snap = reader.snapshot()
        assert "file1.py" in snap.dirty_files
        assert "file2.py" in snap.dirty_files

    @patch("substrate.meta_ide.repository_model.gated_subprocess_run")
    def test_health_assessment_dirty(self, mock_run):
        from substrate.meta_ide.repository_model import RepositoryReader, RepositoryHealthStatus

        def side_effect(cmd, *args, **kwargs):
            result = MagicMock()
            result.returncode = 0
            if "status" in cmd and "-u" in cmd:
                result.stdout = " M a.py\n M b.py\n"
            elif "status" in cmd:
                result.stdout = ""
            else:
                result.stdout = ""
            return result

        mock_run.side_effect = side_effect

        reader = RepositoryReader("/tmp/test-repo")
        snap = reader.snapshot()
        assert snap.health.status == RepositoryHealthStatus.DIRTY
        assert snap.health.dirty_file_count == 2

    @patch("substrate.meta_ide.repository_model.gated_subprocess_run")
    def test_cpu_gate_failure_returns_empty(self, mock_run):
        """CPU gate returning None should not crash."""
        from substrate.meta_ide.repository_model import RepositoryReader

        mock_run.return_value = None

        reader = RepositoryReader("/tmp/test-repo")
        snap = reader.snapshot()
        assert snap.repo_name == "test-repo"
        assert snap.current_branch == ""
        assert snap.dirty_files == []


# ── Workcell B: Workspace Intelligence ─────────────────────────────────────


class TestWorkspaceIntelligence:
    def test_engine_default_path(self):
        from substrate.meta_ide.workspace_intelligence import MetaIDEWorkspaceEngine

        engine = MetaIDEWorkspaceEngine()
        assert len(engine._repo_paths) >= 1

    def test_engine_custom_paths(self):
        from substrate.meta_ide.workspace_intelligence import MetaIDEWorkspaceEngine

        engine = MetaIDEWorkspaceEngine(repo_paths=["/a", "/b"])
        assert engine._repo_paths == ["/a", "/b"]

    @patch("substrate.meta_ide.repository_model.gated_subprocess_run")
    def test_workspace_summary_structure(self, mock_run):
        from substrate.meta_ide.workspace_intelligence import MetaIDEWorkspaceEngine

        result = MagicMock()
        result.returncode = 0
        result.stdout = ""
        mock_run.return_value = result

        engine = MetaIDEWorkspaceEngine(repo_paths=["/tmp/test"])
        summary = engine.workspace_summary()
        assert hasattr(summary, "repositories")
        assert hasattr(summary, "total_dirty_files")
        assert hasattr(summary, "risks")
        assert hasattr(summary, "overall_risk")

    @patch("substrate.meta_ide.repository_model.gated_subprocess_run")
    def test_engineering_summary_dict(self, mock_run):
        from substrate.meta_ide.workspace_intelligence import MetaIDEWorkspaceEngine

        result = MagicMock()
        result.returncode = 0
        result.stdout = ""
        mock_run.return_value = result

        engine = MetaIDEWorkspaceEngine(repo_paths=["/tmp/test"])
        summary = engine.engineering_summary()
        assert "repo_count" in summary
        assert "repos" in summary
        assert "totals" in summary
        assert "risks" in summary
        assert "overall_risk" in summary


class TestRiskDetection:
    def test_no_risks_when_clean(self):
        from substrate.meta_ide.workspace_intelligence import MetaIDEWorkspaceEngine, RiskLevel
        from substrate.meta_ide.repository_model import RepositorySnapshot, RepositoryHealth, RepositoryHealthStatus

        snap = RepositorySnapshot(
            repo_name="clean",
            repo_path="/tmp/clean",
            health=RepositoryHealth(status=RepositoryHealthStatus.HEALTHY),
        )
        engine = MetaIDEWorkspaceEngine(repo_paths=[])
        risks = engine._detect_risks([snap])
        assert len(risks) == 0

    def test_high_risk_many_dirty(self):
        from substrate.meta_ide.workspace_intelligence import MetaIDEWorkspaceEngine, RiskLevel
        from substrate.meta_ide.repository_model import RepositorySnapshot, RepositoryHealth, RepositoryHealthStatus

        snap = RepositorySnapshot(
            repo_name="messy",
            repo_path="/tmp/messy",
            dirty_files=[f"file{i}.py" for i in range(25)],
            health=RepositoryHealth(
                status=RepositoryHealthStatus.DIRTY,
                dirty_file_count=25,
            ),
        )
        engine = MetaIDEWorkspaceEngine(repo_paths=[])
        risks = engine._detect_risks([snap])
        assert any(r.level == RiskLevel.HIGH for r in risks)

    def test_worktree_sprawl_risk(self):
        from substrate.meta_ide.workspace_intelligence import MetaIDEWorkspaceEngine, RiskLevel
        from substrate.meta_ide.repository_model import RepositorySnapshot, RepositoryHealth, RepositoryHealthStatus

        snap = RepositorySnapshot(
            repo_name="sprawl",
            repo_path="/tmp/sprawl",
            worktree_count=15,
            health=RepositoryHealth(status=RepositoryHealthStatus.HEALTHY),
        )
        engine = MetaIDEWorkspaceEngine(repo_paths=[])
        risks = engine._detect_risks([snap])
        assert any(r.category == "worktree_sprawl" for r in risks)

    def test_risk_aggregation(self):
        from substrate.meta_ide.workspace_intelligence import MetaIDEWorkspaceEngine, RiskLevel, EngineeringRisk

        engine = MetaIDEWorkspaceEngine(repo_paths=[])
        risks = [
            EngineeringRisk(risk_id="1", level=RiskLevel.LOW, category="a", description="x"),
            EngineeringRisk(risk_id="2", level=RiskLevel.HIGH, category="b", description="y"),
        ]
        assert engine._aggregate_risk(risks) == RiskLevel.HIGH
        assert engine._aggregate_risk([]) == RiskLevel.NONE


# ── Workcell C: Roadmap Intelligence ──────────────────────────────────────


class TestRoadmapIntelligence:
    def test_status_structure(self):
        from substrate.meta_ide.roadmap_intelligence import RoadmapIntelligence

        ri = RoadmapIntelligence(root_path="/tmp/nonexistent")
        status = ri.status()
        assert hasattr(status, "completed_phases")
        assert hasattr(status, "planned_phases")
        assert hasattr(status, "blocked_phases")
        assert hasattr(status, "completion_ratio")

    def test_phase_status_defaults(self):
        from substrate.meta_ide.roadmap_intelligence import PhaseStatus, PhaseState

        ps = PhaseStatus(phase_number="17", phase_name="Organism")
        assert ps.state == PhaseState.UNKNOWN
        assert ps.blockers == []

    def test_scan_audits_with_real_dir(self):
        from substrate.meta_ide.roadmap_intelligence import RoadmapIntelligence

        root = os.environ.get("UMH_ROOT", "/opt/OS")
        audit_dir = os.path.join(root, "data", "audits")
        if not os.path.isdir(audit_dir):
            pytest.skip("No audits directory")

        ri = RoadmapIntelligence(root_path=root)
        phases = ri._scan_audits()
        assert isinstance(phases, list)

    def test_roadmap_from_memory(self):
        from substrate.meta_ide.roadmap_intelligence import RoadmapIntelligence

        ri = RoadmapIntelligence()
        phases = ri._scan_memory_files()
        assert isinstance(phases, list)

    def test_merge_deduplicates(self):
        from substrate.meta_ide.roadmap_intelligence import (
            RoadmapIntelligence,
            PhaseStatus,
            PhaseState,
        )

        ri = RoadmapIntelligence(root_path="/tmp/none")
        a = [PhaseStatus(phase_number="17", phase_name="A", state=PhaseState.COMPLETED)]
        b = [PhaseStatus(phase_number="17", phase_name="B", state=PhaseState.UNKNOWN)]
        merged = ri._merge_phases(a, b)
        assert len(merged) == 1
        assert merged[0].phase_name == "B"


# ── Workcell E: Reality Integration ────────────────────────────────────────


class TestRealityIntegration:
    def test_meta_ide_mutation_source_exists(self):
        from substrate.reality_model.reality_mutation import MutationSource

        assert MutationSource.META_IDE == "meta_ide"

    def test_meta_ide_mutation_source_in_enum(self):
        from substrate.reality_model.reality_mutation import MutationSource

        sources = [s.value for s in MutationSource]
        assert "meta_ide" in sources


# ── Read-Only Guarantee ───────────────────────────────────────────────────


class TestReadOnlyGuarantee:
    def test_repository_reader_has_no_write_methods(self):
        from substrate.meta_ide.repository_model import RepositoryReader

        write_methods = [
            m for m in dir(RepositoryReader)
            if not m.startswith("_")
            and callable(getattr(RepositoryReader, m, None))
            and any(kw in m.lower() for kw in [
                "write", "push", "commit", "checkout", "reset",
                "delete", "remove", "merge", "rebase", "execute",
                "dispatch", "mutate", "create_branch",
            ])
        ]
        assert write_methods == [], f"Write methods found: {write_methods}"

    def test_workspace_engine_has_no_write_methods(self):
        from substrate.meta_ide.workspace_intelligence import MetaIDEWorkspaceEngine

        write_methods = [
            m for m in dir(MetaIDEWorkspaceEngine)
            if not m.startswith("_")
            and callable(getattr(MetaIDEWorkspaceEngine, m, None))
            and any(kw in m.lower() for kw in [
                "write", "push", "commit", "checkout", "reset",
                "delete", "remove", "merge", "execute", "dispatch",
                "mutate",
            ])
        ]
        assert write_methods == [], f"Write methods found: {write_methods}"

    def test_roadmap_intelligence_has_no_write_methods(self):
        from substrate.meta_ide.roadmap_intelligence import RoadmapIntelligence

        write_methods = [
            m for m in dir(RoadmapIntelligence)
            if not m.startswith("_")
            and callable(getattr(RoadmapIntelligence, m, None))
            and any(kw in m.lower() for kw in [
                "write", "push", "commit", "execute", "dispatch",
                "mutate", "delete", "create",
            ])
        ]
        assert write_methods == [], f"Write methods found: {write_methods}"

    def test_no_execution_authority(self):
        """Meta IDE must not import governance or execution mechanisms."""
        import importlib

        mod = importlib.import_module("substrate.meta_ide.repository_model")
        source = open(mod.__file__, "r").read()
        forbidden = [
            "from substrate.governance",
            "from substrate.organism.organism_loop",
            "from substrate.organism.execution_coordinator",
            "WorkPacket(",
            "execute_intent(",
        ]
        for pattern in forbidden:
            assert pattern not in source, f"Forbidden import found: {pattern}"


# ── Type Registry ─────────────────────────────────────────────────────────


class TestTypeRegistry:
    def test_phase21_types_registered(self):
        from substrate.canonical_types import CANONICAL_TYPES

        expected = [
            "RepositoryHealthStatus",
            "BranchSnapshot",
            "WorktreeSnapshot",
            "RepositoryHealth",
            "RepositorySnapshot",
            "RepositoryReader",
            "MetaIDEWorkspaceEngine",
            "EngineeringRisk",
            "WorkspaceSummary",
            "PhaseState",
            "PhaseStatus",
            "RoadmapStatus",
            "RoadmapIntelligence",
        ]
        for name in expected:
            assert name in CANONICAL_TYPES, f"{name} not in CANONICAL_TYPES"

    def test_type_paths_correct(self):
        from substrate.canonical_types import CANONICAL_TYPES

        assert CANONICAL_TYPES["RepositoryReader"] == ["substrate.meta_ide.repository_model"]
        assert CANONICAL_TYPES["MetaIDEWorkspaceEngine"] == ["substrate.meta_ide.workspace_intelligence"]
        assert CANONICAL_TYPES["RoadmapIntelligence"] == ["substrate.meta_ide.roadmap_intelligence"]


# ── Cockpit Routes ────────────────────────────────────────────────────────


class TestCockpitRoutes:
    def test_meta_ide_routes_module_imports(self):
        from transports.api import cockpit_meta_ide_routes

        assert hasattr(cockpit_meta_ide_routes, "configure")
        assert hasattr(cockpit_meta_ide_routes, "meta_ide_router")

    def test_routes_require_auth(self):
        """All routes must use dependencies=auth pattern."""
        import inspect
        from transports.api import cockpit_meta_ide_routes

        source = inspect.getsource(cockpit_meta_ide_routes._build_router)
        route_count = source.count("@r.get(")
        auth_count = source.count("dependencies=auth")
        assert route_count == auth_count, (
            f"{route_count} routes but only {auth_count} have auth"
        )

    def test_all_routes_are_get(self):
        """Meta IDE is read-only — no POST/PUT/DELETE."""
        import inspect
        from transports.api import cockpit_meta_ide_routes

        source = inspect.getsource(cockpit_meta_ide_routes._build_router)
        assert "@r.post(" not in source
        assert "@r.put(" not in source
        assert "@r.delete(" not in source
        assert "@r.patch(" not in source


# ── Package Export ────────────────────────────────────────────────────────


class TestPackageExport:
    def test_meta_ide_package_imports(self):
        from substrate.meta_ide import (
            BranchSnapshot,
            EngineeringRisk,
            MetaIDEWorkspaceEngine,
            PhaseStatus,
            RepositoryHealth,
            RepositorySnapshot,
            RoadmapIntelligence,
            RoadmapStatus,
            WorkspaceSummary,
            WorktreeSnapshot,
        )
        assert RepositorySnapshot is not None
        assert MetaIDEWorkspaceEngine is not None
        assert RoadmapIntelligence is not None
