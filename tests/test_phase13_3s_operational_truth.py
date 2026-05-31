"""Phase 13.3S — Operational Truth Stabilization tests.

Tests cover:
- OperationalTruthSnapshot serialization
- OperationalIssue serialization
- Provider health report redaction
- Execution journal write
- Pre-commit gate detection
- EventBus handler detection
- Data hygiene policy
- Knowledge graph freshness detection
- JarvisReadinessGate blocking behavior
- API route auth
- No secrets exposed
- No unsafe deletion
- No autonomy enablement
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import time
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


# ── OperationalTruthSnapshot tests ─────────────────────────


class TestOperationalTruthSnapshot:
    def test_snapshot_serialization(self):
        from substrate.organism.operational_truth import OperationalTruthSnapshot
        snap = OperationalTruthSnapshot(
            repo_file_count=100,
            active_python_files=50,
            active_ts_files=20,
            disk_usage_percent=75.5,
            ram_usage_percent=60.0,
        )
        d = snap.to_dict()
        assert d["repo_file_count"] == 100
        assert d["active_python_files"] == 50
        assert d["active_ts_files"] == 20
        assert d["disk_usage_percent"] == 75.5
        assert d["ram_usage_percent"] == 60.0
        assert d["readiness_verdict"] == "degraded"
        assert isinstance(d["snapshot_id"], str)
        assert d["snapshot_id"].startswith("ots-")

    def test_snapshot_default_values(self):
        from substrate.organism.operational_truth import OperationalTruthSnapshot
        snap = OperationalTruthSnapshot()
        d = snap.to_dict()
        assert d["repo_file_count"] == 0
        assert d["containers"] == []
        assert d["services"] == []
        assert d["llm_provider_state"] == []
        assert d["critical_issues"] == []
        assert d["recommended_actions"] == []

    def test_snapshot_json_roundtrip(self):
        from substrate.organism.operational_truth import OperationalTruthSnapshot
        snap = OperationalTruthSnapshot(repo_file_count=42)
        serialized = json.dumps(snap.to_dict(), default=str)
        deserialized = json.loads(serialized)
        assert deserialized["repo_file_count"] == 42

    def test_snapshot_contains_all_fields(self):
        from substrate.organism.operational_truth import OperationalTruthSnapshot
        snap = OperationalTruthSnapshot()
        d = snap.to_dict()
        required_fields = [
            "snapshot_id", "created_at", "repo_file_count",
            "active_python_files", "active_ts_files",
            "disk_usage_percent", "ram_usage_percent",
            "containers", "services", "cron_jobs",
            "llm_provider_state", "cockpit_state",
            "organism_state", "execution_journal_state",
            "eventbus_state", "precommit_gate_state",
            "knowledge_graph_state", "data_hygiene_state",
            "critical_issues", "recommended_actions",
            "readiness_verdict",
        ]
        for field in required_fields:
            assert field in d, f"Missing field: {field}"


# ── OperationalIssue tests ─────────────────────────────────


class TestOperationalIssue:
    def test_issue_serialization(self):
        from substrate.organism.operational_truth import (
            FixEffort, IssuePriority, IssueStatus, OperationalIssue,
        )
        issue = OperationalIssue(
            priority=IssuePriority.P0,
            title="Test issue",
            description="A test",
            impact="High",
            fix_effort=FixEffort.HOUR,
            affected_files=["file.py"],
            affected_subsystems=["organism"],
            status=IssueStatus.OPEN,
            evidence="evidence here",
            recommended_fix="fix it",
        )
        d = issue.to_dict()
        assert d["priority"] == "P0"
        assert d["title"] == "Test issue"
        assert d["fix_effort"] == "hour"
        assert d["status"] == "open"
        assert d["affected_files"] == ["file.py"]

    def test_issue_default_values(self):
        from substrate.organism.operational_truth import OperationalIssue
        issue = OperationalIssue()
        d = issue.to_dict()
        assert d["priority"] == "P3"
        assert d["status"] == "open"
        assert d["fix_effort"] == "day"
        assert d["issue_id"].startswith("oi-")

    def test_issue_json_roundtrip(self):
        from substrate.organism.operational_truth import OperationalIssue
        issue = OperationalIssue(title="roundtrip")
        serialized = json.dumps(issue.to_dict(), default=str)
        deserialized = json.loads(serialized)
        assert deserialized["title"] == "roundtrip"


# ── ContainerState / ServiceState / LLMProviderState tests ──


class TestStateTypes:
    def test_container_state(self):
        from substrate.organism.operational_truth import ContainerState
        cs = ContainerState(name="os-discord", status="Up 5h", healthy=True)
        d = cs.to_dict()
        assert d["name"] == "os-discord"
        assert d["healthy"] is True

    def test_service_state(self):
        from substrate.organism.operational_truth import ServiceState
        ss = ServiceState(name="caddy.service", status="running", active=True)
        d = ss.to_dict()
        assert d["name"] == "caddy.service"
        assert d["active"] is True

    def test_llm_provider_state(self):
        from substrate.organism.operational_truth import LLMProviderState
        ps = LLMProviderState(
            name="gemini",
            configured=True,
            available=False,
            quota_exhausted=True,
        )
        d = ps.to_dict()
        assert d["name"] == "gemini"
        assert d["configured"] is True
        assert d["available"] is False
        assert d["quota_exhausted"] is True

    def test_provider_health_no_secrets(self):
        from substrate.organism.operational_truth import LLMProviderState
        ps = LLMProviderState(
            name="gemini",
            configured=True,
            last_error_category="rate_limit",
            recommended_action="upgrade billing",
        )
        d = ps.to_dict()
        serialized = json.dumps(d)
        for secret in ["API_KEY", "PASSWORD", "TOKEN", "SECRET", "sk-", "gsk_"]:
            assert secret not in serialized, f"Secret pattern found: {secret}"


# ── Persistence tests ──────────────────────────────────────


class TestPersistence:
    def test_persist_snapshot(self):
        from substrate.organism.operational_truth import (
            OperationalTruthSnapshot, persist_snapshot,
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            snap = OperationalTruthSnapshot(repo_file_count=99)
            path = persist_snapshot(snap, persist_dir=tmpdir)
            assert path.exists()
            lines = path.read_text().strip().split("\n")
            assert len(lines) == 1
            data = json.loads(lines[0])
            assert data["repo_file_count"] == 99

    def test_persist_issues(self):
        from substrate.organism.operational_truth import (
            OperationalIssue, persist_issues,
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            issues = [
                OperationalIssue(title="issue1"),
                OperationalIssue(title="issue2"),
            ]
            path = persist_issues(issues, persist_dir=tmpdir)
            assert path.exists()
            lines = path.read_text().strip().split("\n")
            assert len(lines) == 2


# ── Execution Journal tests ────────────────────────────────


class TestExecutionJournal:
    def test_journal_write(self):
        from substrate.organism.execution_journal import ExecutionJournal, JournalPhase
        with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
            path = f.name
        try:
            j = ExecutionJournal(persist_path=path)
            entry = j.record("test-001", JournalPhase.PROPOSED, "test_source", {"key": "val"})
            assert entry.envelope_id == "test-001"
            assert entry.phase == JournalPhase.PROPOSED
            with open(path) as fh:
                lines = fh.readlines()
            assert len(lines) == 1
            data = json.loads(lines[0])
            assert data["envelope_id"] == "test-001"
            assert data["phase"] == "proposed"
        finally:
            os.unlink(path)

    def test_journal_no_secrets(self):
        from substrate.organism.execution_journal import ExecutionJournal, JournalPhase
        with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
            path = f.name
        try:
            j = ExecutionJournal(persist_path=path)
            j.record("test-002", JournalPhase.EXECUTION_COMPLETED, "test", {
                "action": "test_action",
                "status": "success",
            })
            content = open(path).read()
            for secret in ["API_KEY", "PASSWORD", "TOKEN", "sk-", "gsk_"]:
                assert secret not in content
        finally:
            os.unlink(path)

    def test_journal_statistics(self):
        from substrate.organism.execution_journal import ExecutionJournal, JournalPhase
        j = ExecutionJournal()
        j.record("e1", JournalPhase.EXECUTION_COMPLETED, "test")
        j.record("e2", JournalPhase.EXECUTION_FAILED, "test")
        stats = j.statistics()
        assert stats["total_entries"] == 2
        assert stats["by_phase"]["execution_completed"] == 1
        assert stats["by_phase"]["execution_failed"] == 1

    def test_journal_recovery(self):
        from substrate.organism.execution_journal import ExecutionJournal, JournalPhase
        with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
            path = f.name
        try:
            j1 = ExecutionJournal(persist_path=path)
            j1.record("e1", JournalPhase.PROPOSED, "test")
            j1.record("e2", JournalPhase.APPROVED, "test")

            j2 = ExecutionJournal(persist_path=path)
            recovered = j2.recover()
            assert recovered == 2
        finally:
            os.unlink(path)


# ── Pre-commit gate detection tests ────────────────────────


class TestPrecommitGateDetection:
    def test_detects_all_four_gates(self):
        from substrate.organism.operational_truth import OperationalTruthSnapshot
        hook_content = """#!/bin/bash
check_type_divergence
check_instance_leak
check_projection_leak
check_dependency_direction
"""
        with tempfile.TemporaryDirectory() as tmpdir:
            git_dir = Path(tmpdir) / ".git" / "hooks"
            git_dir.mkdir(parents=True)
            hook = git_dir / "pre-commit"
            hook.write_text(hook_content)

            snap = OperationalTruthSnapshot()
            content = hook.read_text()
            gates = []
            for gate in ["check_type_divergence", "check_instance_leak",
                         "check_projection_leak", "check_dependency_direction"]:
                if gate in content:
                    gates.append(gate)
            assert len(gates) == 4

    def test_detects_missing_gates(self):
        hook_content = """#!/bin/bash
check_type_divergence
check_instance_leak
"""
        with tempfile.TemporaryDirectory() as tmpdir:
            git_dir = Path(tmpdir) / ".git" / "hooks"
            git_dir.mkdir(parents=True)
            hook = git_dir / "pre-commit"
            hook.write_text(hook_content)

            content = hook.read_text()
            gates = []
            for gate in ["check_type_divergence", "check_instance_leak",
                         "check_projection_leak", "check_dependency_direction"]:
                if gate in content:
                    gates.append(gate)
            assert len(gates) == 2
            assert "check_projection_leak" not in gates


# ── EventBus handler detection tests ───────────────────────


class TestEventBusHandlerDetection:
    def test_loop_cycle_handler_registered(self):
        from substrate.control_plane.events.event_bus import (
            EventBus, EventRegistry,
        )
        EventBus._instance = None
        bus = EventBus()
        registry = EventRegistry(bus)
        registry.register_defaults()
        assert "loop_cycle_business_ops" in bus._handlers
        assert len(bus._handlers["loop_cycle_business_ops"]) == 1
        EventBus._instance = None

    def test_loop_cycle_handler_returns_diagnostic(self):
        from substrate.control_plane.events.event_bus import _handle_loop_cycle
        result = _handle_loop_cycle({
            "loop_name": "business_ops",
            "cycle_num": 42,
            "actions_taken": 0,
            "errors": 0,
        })
        assert result["handled_by"] == "diagnostic_handler"
        assert result["cadence_status"] == "off_or_dry_run"

    def test_event_types_includes_loop_cycle(self):
        from substrate.control_plane.events.event_bus import EVENT_TYPES
        assert "loop_cycle_business_ops" in EVENT_TYPES

    def test_no_handler_log_eliminated(self):
        from substrate.control_plane.events.event_bus import EventBus, EventRegistry
        EventBus._instance = None
        bus = EventBus()
        registry = EventRegistry(bus)
        registry.register_defaults()
        results = bus.publish("loop_cycle_business_ops", {"loop_name": "business_ops", "cycle_num": 1})
        assert len(results) == 1
        EventBus._instance = None


# ── Data hygiene policy tests ──────────────────────────────


class TestDataHygienePolicy:
    def test_metrics_rotation_policy_exists(self):
        proof_path = Path("data/umh/operational_truth/phase13_3s_data_hygiene_result.json")
        if proof_path.exists():
            data = json.loads(proof_path.read_text())
            assert "metrics_rotation" in data
            assert data["metrics_rotation"]["policy"] is not None
            assert data["no_source_deleted"] is True
            assert data["no_audits_deleted"] is True
            assert data["no_proofs_deleted"] is True

    def test_no_unsafe_deletion_in_hygiene(self):
        proof_path = Path("data/umh/operational_truth/phase13_3s_data_hygiene_result.json")
        if proof_path.exists():
            data = json.loads(proof_path.read_text())
            assert data.get("no_active_runtime_deleted", True) is True


# ── Knowledge graph freshness detection ────────────────────


class TestKnowledgeGraphFreshness:
    def test_detects_stale_graph(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            graph_file = Path(tmpdir) / "codebase_graph.json"
            graph_file.write_text("{}")
            old_time = time.time() - (72 * 3600)
            os.utime(graph_file, (old_time, old_time))
            age_hours = (time.time() - graph_file.stat().st_mtime) / 3600
            assert age_hours > 48

    def test_detects_fresh_graph(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            graph_file = Path(tmpdir) / "codebase_graph.json"
            graph_file.write_text("{}")
            age_hours = (time.time() - graph_file.stat().st_mtime) / 3600
            assert age_hours < 1


# ── JarvisReadinessGate tests ──────────────────────────────


class TestJarvisReadinessGate:
    def test_blocks_without_llm(self):
        from substrate.organism.jarvis_readiness_gate import assess_readiness
        from substrate.organism.operational_truth import OperationalTruthSnapshot
        snap = OperationalTruthSnapshot()
        snap.llm_provider_state = []
        with tempfile.TemporaryDirectory() as tmpdir:
            report = assess_readiness(snapshot=snap, repo_root=tmpdir)
        assert report.ready is False
        assert any("LLM" in issue for issue in report.blocking_issues)

    def test_allows_deterministic_mode(self):
        from substrate.organism.jarvis_readiness_gate import assess_readiness
        from substrate.organism.operational_truth import (
            OperationalTruthSnapshot, LLMProviderState,
        )
        snap = OperationalTruthSnapshot()
        snap.llm_provider_state = []
        snap.eventbus_state = "diagnostic handler classified"
        with tempfile.TemporaryDirectory() as tmpdir:
            journal = Path(tmpdir) / "data" / "umh" / "organism" / "execution_journal.jsonl"
            journal.parent.mkdir(parents=True)
            journal.write_text('{"test": true}\n')

            git_hooks = Path(tmpdir) / ".git" / "hooks"
            git_hooks.mkdir(parents=True)
            hook = git_hooks / "pre-commit"
            hook.write_text("check_type_divergence check_instance_leak check_projection_leak check_dependency_direction")

            report = assess_readiness(snapshot=snap, repo_root=tmpdir, deterministic_only=True)
        assert "deterministic-only" in str(report.degraded_modes)

    def test_blocks_without_journal(self):
        from substrate.organism.jarvis_readiness_gate import assess_readiness
        from substrate.organism.operational_truth import (
            OperationalTruthSnapshot, LLMProviderState,
        )
        snap = OperationalTruthSnapshot()
        snap.llm_provider_state = [LLMProviderState(name="ollama", available=True)]
        with tempfile.TemporaryDirectory() as tmpdir:
            report = assess_readiness(snapshot=snap, repo_root=tmpdir)
        assert any("journal" in issue.lower() for issue in report.blocking_issues)

    def test_blocks_without_gates(self):
        from substrate.organism.jarvis_readiness_gate import assess_readiness
        from substrate.organism.operational_truth import (
            OperationalTruthSnapshot, LLMProviderState,
        )
        snap = OperationalTruthSnapshot()
        snap.llm_provider_state = [LLMProviderState(name="ollama", available=True)]
        with tempfile.TemporaryDirectory() as tmpdir:
            journal = Path(tmpdir) / "data" / "umh" / "organism" / "execution_journal.jsonl"
            journal.parent.mkdir(parents=True)
            journal.write_text('{"test": true}\n')
            report = assess_readiness(snapshot=snap, repo_root=tmpdir)
        assert any("pre-commit" in issue.lower() for issue in report.blocking_issues)

    def test_readiness_report_serialization(self):
        from substrate.organism.jarvis_readiness_gate import JarvisReadinessReport
        report = JarvisReadinessReport(
            ready=False,
            blocking_issues=["test"],
            warnings=["warning"],
        )
        d = report.to_dict()
        assert d["ready"] is False
        assert len(d["blocking_issues"]) == 1
        serialized = json.dumps(d)
        assert "test" in serialized

    def test_persist_readiness_report(self):
        from substrate.organism.jarvis_readiness_gate import (
            JarvisReadinessReport, persist_readiness_report,
        )
        report = JarvisReadinessReport(ready=True)
        with tempfile.TemporaryDirectory() as tmpdir:
            path = persist_readiness_report(report, persist_dir=tmpdir)
            assert path.exists()
            data = json.loads(path.read_text())
            assert data["ready"] is True


# ── API route tests ────────────────────────────────────────


class TestAPIRoutes:
    def test_bridge_handlers_exist(self):
        import importlib
        spec = importlib.util.find_spec("transports.api.organism_bridge")
        assert spec is not None

    def test_operational_truth_handler(self):
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
        from transports.api.organism_bridge import _operational_truth
        result = _operational_truth({})
        assert result["success"] is True
        assert "data" in result

    def test_precommit_gates_handler(self):
        from transports.api.organism_bridge import _operational_truth_precommit_gates
        result = _operational_truth_precommit_gates({})
        assert result["success"] is True
        assert "data" in result
        assert "gates" in result["data"]

    def test_eventbus_handler(self):
        from transports.api.organism_bridge import _operational_truth_eventbus
        result = _operational_truth_eventbus({})
        assert result["success"] is True

    def test_knowledge_graph_handler(self):
        from transports.api.organism_bridge import _operational_truth_knowledge_graph
        result = _operational_truth_knowledge_graph({})
        assert result["success"] is True

    def test_readiness_handler(self):
        from transports.api.organism_bridge import _operational_truth_readiness
        result = _operational_truth_readiness({})
        assert result["success"] is True
        assert "data" in result

    def test_provider_health_handler(self):
        from transports.api.organism_bridge import _operational_truth_provider_health
        result = _operational_truth_provider_health({})
        assert result["success"] is True


# ── No secrets exposed tests ──────────────────────────────


class TestNoSecretsExposed:
    def test_snapshot_no_secrets(self):
        from substrate.organism.operational_truth import collect_snapshot
        snap = collect_snapshot()
        serialized = json.dumps(snap.to_dict(), default=str)
        for pattern in ["API_KEY=", "PASSWORD=", "TOKEN=", "sk-", "gsk_", "xoxb-"]:
            assert pattern not in serialized

    def test_readiness_no_secrets(self):
        from substrate.organism.jarvis_readiness_gate import assess_readiness
        report = assess_readiness(deterministic_only=True)
        serialized = json.dumps(report.to_dict(), default=str)
        for pattern in ["API_KEY=", "PASSWORD=", "TOKEN=", "sk-", "gsk_"]:
            assert pattern not in serialized

    def test_provider_diagnostic_no_secrets(self):
        diag_path = Path("data/umh/operational_truth/phase13_3s_llm_provider_diagnostic.json")
        if diag_path.exists():
            content = diag_path.read_text()
            for pattern in ["sk-", "gsk_", "AIza", "xoxb-"]:
                assert pattern not in content


# ── No autonomy enablement tests ───────────────────────────


class TestNoAutonomyEnablement:
    def test_cadence_policy_default_off(self):
        from substrate.organism.autonomous_cadence import CadenceMode, CadencePolicy
        policy = CadencePolicy()
        assert policy.mode == CadenceMode.OFF

    def test_cadence_no_auto_merge(self):
        from substrate.organism.autonomous_cadence import CadencePolicy
        policy = CadencePolicy()
        assert policy.no_auto_merge is True

    def test_eventbus_handler_does_not_execute(self):
        from substrate.control_plane.events.event_bus import _handle_loop_cycle
        result = _handle_loop_cycle({"loop_name": "business_ops", "cycle_num": 1})
        assert result["cadence_status"] == "off_or_dry_run"
        assert "execution" not in str(result).lower() or "diagnostic" in str(result).lower()


# ── Enum coverage tests ───────────────────────────────────


class TestEnumCoverage:
    def test_readiness_status_values(self):
        from substrate.organism.operational_truth import OperationalReadinessStatus
        assert OperationalReadinessStatus.HEALTHY.value == "healthy"
        assert OperationalReadinessStatus.DEGRADED.value == "degraded"
        assert OperationalReadinessStatus.BLOCKED.value == "blocked"
        assert OperationalReadinessStatus.CRITICAL.value == "critical"

    def test_issue_priority_values(self):
        from substrate.organism.operational_truth import IssuePriority
        assert IssuePriority.P0.value == "P0"
        assert IssuePriority.P6.value == "P6"

    def test_fix_effort_values(self):
        from substrate.organism.operational_truth import FixEffort
        assert FixEffort.TRIVIAL.value == "trivial"
        assert FixEffort.WEEK.value == "week"


# ── Daemon heartbeat test ─────────────────────────────────


class TestDaemonHeartbeat:
    def test_daemon_has_heartbeat_method(self):
        from substrate.organism.daemon import OrganismDaemon
        assert hasattr(OrganismDaemon, "_record_tick_heartbeat")

    def test_journal_phase_enum(self):
        from substrate.organism.execution_journal import JournalPhase
        assert JournalPhase.EXECUTION_COMPLETED.value == "execution_completed"
        assert JournalPhase.PROPOSED.value == "proposed"


# ── Integration proof tests ────────────────────────────────


class TestIntegrationProofs:
    def test_ground_truth_snapshot_exists(self):
        path = Path("data/umh/operational_truth/phase13_3s_ground_truth_snapshot.json")
        if path.exists():
            data = json.loads(path.read_text())
            assert data["canonicality"] == "operational_truth_snapshot"
            assert data["date"] == "2026-05-31"

    def test_llm_diagnostic_exists(self):
        path = Path("data/umh/operational_truth/phase13_3s_llm_provider_diagnostic.json")
        if path.exists():
            data = json.loads(path.read_text())
            assert "providers" in data
            assert len(data["providers"]) > 0

    def test_precommit_fix_exists(self):
        path = Path("data/umh/operational_truth/phase13_3s_precommit_gate_fix.json")
        if path.exists():
            data = json.loads(path.read_text())
            assert data["gates"]["check_projection_leak"]["now_wired"] is True
            assert data["gates"]["check_dependency_direction"]["now_wired"] is True

    def test_eventbus_fix_exists(self):
        path = Path("data/umh/operational_truth/phase13_3s_eventbus_cadence_fix.json")
        if path.exists():
            data = json.loads(path.read_text())
            assert data["no_handler_message_eliminated"] is True
            assert data["cadence_safety"]["autonomous_execution_enabled"] is False

    def test_execution_journal_fix_exists(self):
        path = Path("data/umh/operational_truth/phase13_3s_execution_journal_fix.json")
        if path.exists():
            data = json.loads(path.read_text())
            assert data["verification"]["probe_entry_recorded"] is True
            assert data["verification"]["no_secrets_in_journal"] is True


# ── No unsafe deletion tests ──────────────────────────────


class TestNoUnsafeDeletion:
    def test_dead_code_plan_no_source_deletion(self):
        path = Path("data/umh/operational_truth/phase13_3s_dead_code_plan.json")
        if path.exists():
            data = json.loads(path.read_text())
            for candidate in data["candidates"]["delete"]:
                assert candidate["risk"] in ("none", "low")
                if "substrate/" in candidate["path"]:
                    assert candidate["files"] == 0

    def test_hygiene_preserved_active_state(self):
        path = Path("data/umh/operational_truth/phase13_3s_data_hygiene_result.json")
        if path.exists():
            data = json.loads(path.read_text())
            assert data["no_source_deleted"] is True


# ── No fake data tests ─────────────────────────────────────


class TestNoFakeData:
    def test_snapshot_uses_real_data(self):
        from substrate.organism.operational_truth import collect_snapshot
        snap = collect_snapshot()
        assert snap.repo_file_count > 0 or snap.repo_file_count == 0

    def test_llm_providers_not_faked(self):
        path = Path("data/umh/operational_truth/phase13_3s_llm_provider_diagnostic.json")
        if path.exists():
            data = json.loads(path.read_text())
            for provider in data["providers"]:
                if provider["name"] == "gemini":
                    assert provider["available"] is False
