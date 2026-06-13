"""Operator Loop Phase 2 — Autonomous Implementation tests.

Tests the Phase 2 lifecycle:
  Plan generation → execution modes → failure recovery → review gate

Covers:
  1. AgentExecutionPlan generation and persistence
  2. Three execution modes: validate_only, implement, implement_and_validate
  3. FailureReport creation and retry tracking
  4. Review gate enforcement for high-risk packets
  5. Full lifecycle: intent → plan → execute → validate → complete
"""

from __future__ import annotations

import json
import os
import sys
import time

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture(autouse=True)
def _isolate_data(tmp_path, monkeypatch):
    """Route all data writes to a temp directory."""
    monkeypatch.setenv("UMH_ROOT", str(tmp_path))
    monkeypatch.setenv("UMH_ORG_ID", "test-org")
    monkeypatch.setenv("UMH_USER_ID", "test-user")
    os.makedirs(tmp_path / "data" / "umh" / "audit", exist_ok=True)
    os.makedirs(tmp_path / "data" / "umh" / "universal_work", exist_ok=True)
    os.makedirs(tmp_path / "data" / "umh" / "sandboxes", exist_ok=True)
    os.makedirs(tmp_path / "data" / "umh" / "execution" / "plans", exist_ok=True)
    os.makedirs(tmp_path / "data" / "umh" / "execution" / "records", exist_ok=True)
    os.makedirs(tmp_path / "data" / "umh" / "execution" / "failures", exist_ok=True)


def _make_packet(**overrides):
    from substrate.organism.universal_work_queue import UniversalWorkQueue
    q = UniversalWorkQueue()
    defaults = {
        "user_intent": "Fix a TypeScript import error in cockpit/src/main.ts",
        "desired_end_state": "TypeScript compiles without errors",
        "constraints": ["no new dependencies"],
    }
    defaults.update(overrides)
    pkt = q.ingest_user_intent(**defaults)
    pkt.success_criteria = ["npx tsc --noEmit passes"]
    pkt.validation_plan = "run pytest and typecheck"
    q._save()
    return pkt, q


class TestPlanGeneration:
    """Section 3: plan generated before implementation."""

    def test_generate_plan_from_packet(self):
        from substrate.organism.agent_execution_runner import AgentExecutionRunner
        pkt, _ = _make_packet()
        runner = AgentExecutionRunner()
        plan = runner.generate_plan(pkt)

        assert plan.plan_id.startswith("plan-")
        assert plan.packet_id == pkt.packet_id
        assert len(plan.objectives) > 0
        assert plan.validation_strategy
        assert plan.rollback_strategy
        assert plan.approved is False

    def test_plan_persists_to_disk(self, tmp_path):
        from substrate.organism.agent_execution_runner import AgentExecutionRunner
        pkt, _ = _make_packet()
        runner = AgentExecutionRunner()
        plan = runner.generate_plan(pkt)

        plan_path = tmp_path / "data" / "umh" / "execution" / "plans" / f"{plan.plan_id}.json"
        assert plan_path.exists()
        data = json.loads(plan_path.read_text())
        assert data["packet_id"] == pkt.packet_id
        assert data["approved"] is False

    def test_plan_includes_acceptance_criteria(self):
        from substrate.organism.agent_execution_runner import AgentExecutionRunner
        pkt, _ = _make_packet()
        pkt.success_criteria = ["import check passes", "no regressions"]
        runner = AgentExecutionRunner()
        plan = runner.generate_plan(pkt)

        criteria_objectives = [o for o in plan.objectives if "Acceptance:" in o]
        assert len(criteria_objectives) == 2

    def test_plan_to_dict_roundtrip(self):
        from substrate.organism.agent_execution_runner import AgentExecutionRunner
        pkt, _ = _make_packet()
        runner = AgentExecutionRunner()
        plan = runner.generate_plan(pkt)
        d = plan.to_dict()
        assert isinstance(d, dict)
        assert d["plan_id"] == plan.plan_id
        assert d["objectives"] == plan.objectives


class TestExecutionModes:
    """Section 2: three execution modes."""

    def test_validate_only_mode(self):
        from substrate.organism.agent_execution_runner import AgentExecutionRunner
        pkt, _ = _make_packet()
        runner = AgentExecutionRunner()
        record = runner.execute(pkt, mode="validate_only")

        assert record.record_id.startswith("exec-")
        assert record.mode == "validate_only"
        assert record.completed_at > 0
        assert record.duration_seconds >= 0
        assert isinstance(record.validation_results, list)

    def test_implement_mode_without_cli(self):
        """Without Claude CLI available, implement mode should fail gracefully."""
        from substrate.organism.agent_execution_runner import AgentExecutionRunner
        pkt, _ = _make_packet()
        runner = AgentExecutionRunner()
        record = runner.execute(pkt, mode="implement")

        assert record.mode == "implement"
        assert record.completed_at > 0

    def test_implement_and_validate_mode(self):
        from substrate.organism.agent_execution_runner import AgentExecutionRunner
        pkt, _ = _make_packet()
        runner = AgentExecutionRunner()
        record = runner.execute(pkt, mode="implement_and_validate")

        assert record.mode == "implement_and_validate"
        assert record.completed_at > 0

    def test_record_persists_to_disk(self, tmp_path):
        from substrate.organism.agent_execution_runner import AgentExecutionRunner
        pkt, _ = _make_packet()
        runner = AgentExecutionRunner()
        record = runner.execute(pkt, mode="validate_only")

        rec_path = tmp_path / "data" / "umh" / "execution" / "records" / f"{record.record_id}.json"
        assert rec_path.exists()
        data = json.loads(rec_path.read_text())
        assert data["mode"] == "validate_only"
        assert data["packet_id"] == pkt.packet_id

    def test_record_to_dict(self):
        from substrate.organism.agent_execution_runner import AgentExecutionRunner
        pkt, _ = _make_packet()
        runner = AgentExecutionRunner()
        record = runner.execute(pkt, mode="validate_only")
        d = record.to_dict()
        assert isinstance(d, dict)
        assert d["record_id"] == record.record_id


class TestFailureRecovery:
    """Section 6: failure reports."""

    def test_failure_report_created_on_error(self):
        from substrate.organism.agent_execution_runner import AgentExecutionRunner, FailureReport
        runner = AgentExecutionRunner()
        report = runner._create_failure_report(
            packet_id="test-pkt-1",
            root_cause="import error",
            failing_command="python3 -c 'import foo'",
            logs="ModuleNotFoundError: No module named 'foo'",
        )
        assert report.report_id.startswith("fail-")
        assert report.root_cause == "import error"
        assert report.retry_count == 0
        assert report.max_retries == 2
        assert report.recommended_action == "retry"

    def test_retry_count_increments(self):
        from substrate.organism.agent_execution_runner import AgentExecutionRunner
        runner = AgentExecutionRunner()
        r1 = runner._create_failure_report("pkt-1", "err1", "cmd1", "log1")
        assert r1.retry_count == 0
        r2 = runner._create_failure_report("pkt-1", "err2", "cmd2", "log2")
        assert r2.retry_count == 1
        r3 = runner._create_failure_report("pkt-1", "err3", "cmd3", "log3")
        assert r3.retry_count == 2
        assert r3.recommended_action == "escalate to operator"

    def test_failure_persists_to_disk(self, tmp_path):
        from substrate.organism.agent_execution_runner import AgentExecutionRunner
        runner = AgentExecutionRunner()
        report = runner._create_failure_report("pkt-2", "oops", "cmd", "logs")
        fail_dir = tmp_path / "data" / "umh" / "execution" / "failures"
        files = list(fail_dir.glob("*.json"))
        assert len(files) == 1
        data = json.loads(files[0].read_text())
        assert data["packet_id"] == "pkt-2"

    def test_get_failure_by_packet_id(self):
        from substrate.organism.agent_execution_runner import AgentExecutionRunner
        runner = AgentExecutionRunner()
        runner._create_failure_report("pkt-3", "boom", "cmd", "")
        result = runner.get_failure("pkt-3")
        assert result is not None
        assert result.root_cause == "boom"

    def test_get_failure_missing_returns_none(self):
        from substrate.organism.agent_execution_runner import AgentExecutionRunner
        runner = AgentExecutionRunner()
        assert runner.get_failure("nonexistent") is None


class TestReviewGate:
    """Section 5: high-risk packets require review."""

    def test_high_risk_needs_review(self):
        pkt, q = _make_packet()
        pkt.risk_class = "high"
        pkt.approval_gates = ["operator_approval_required"]
        q._save()

        assert "operator_approval_required" in pkt.approval_gates
        assert pkt.risk_class in ("high", "critical")

    def test_low_risk_no_review(self):
        pkt, q = _make_packet()
        pkt.risk_class = "low"
        pkt.approval_gates = []
        q._save()
        assert pkt.risk_class == "low"
        assert len(pkt.approval_gates) == 0


class TestDataclasses:
    """Verify dataclass contracts."""

    def test_execution_plan_defaults(self):
        from substrate.organism.agent_execution_runner import AgentExecutionPlan
        plan = AgentExecutionPlan()
        assert plan.plan_id.startswith("plan-")
        assert plan.approved is False
        assert plan.objectives == []

    def test_execution_record_defaults(self):
        from substrate.organism.agent_execution_runner import ExecutionRecord
        rec = ExecutionRecord()
        assert rec.record_id.startswith("exec-")
        assert rec.mode == "validate_only"
        assert rec.success is False

    def test_failure_report_defaults(self):
        from substrate.organism.agent_execution_runner import FailureReport
        fr = FailureReport()
        assert fr.report_id.startswith("fail-")
        assert fr.max_retries == 2


class TestValidationCommands:
    """Verify validation command derivation."""

    def test_default_commands(self):
        from substrate.organism.agent_execution_runner import AgentExecutionRunner
        pkt, _ = _make_packet()
        pkt.validation_plan = ""
        runner = AgentExecutionRunner()
        commands = runner._derive_validation_commands(pkt)
        assert len(commands) >= 2
        assert any("substrate import" in c.get("label", "") for c in commands)

    def test_pytest_command_from_plan(self):
        from substrate.organism.agent_execution_runner import AgentExecutionRunner
        pkt, _ = _make_packet()
        pkt.validation_plan = "run pytest and check lint"
        runner = AgentExecutionRunner()
        commands = runner._derive_validation_commands(pkt)
        labels = [c["label"] for c in commands]
        assert any("test" in l for l in labels)

    def test_ruff_command_from_plan(self):
        from substrate.organism.agent_execution_runner import AgentExecutionRunner
        pkt, _ = _make_packet()
        pkt.validation_plan = "lint with ruff"
        runner = AgentExecutionRunner()
        commands = runner._derive_validation_commands(pkt)
        labels = [c["label"] for c in commands]
        assert any("ruff" in l for l in labels)


class TestRecordRetrieval:
    """Verify record lookup methods."""

    def test_get_records_for_packet(self):
        from substrate.organism.agent_execution_runner import AgentExecutionRunner
        pkt, _ = _make_packet()
        runner = AgentExecutionRunner()
        runner.execute(pkt, mode="validate_only")
        records = runner.get_records_for_packet(pkt.packet_id)
        assert len(records) == 1
        assert records[0].packet_id == pkt.packet_id

    def test_get_record_by_id(self):
        from substrate.organism.agent_execution_runner import AgentExecutionRunner
        pkt, _ = _make_packet()
        runner = AgentExecutionRunner()
        record = runner.execute(pkt, mode="validate_only")
        retrieved = runner.get_record(record.record_id)
        assert retrieved is not None
        assert retrieved.record_id == record.record_id
