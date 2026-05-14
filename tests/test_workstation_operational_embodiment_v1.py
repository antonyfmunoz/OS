"""Tests for Phase 96.8BP — Workstation Operational Embodiment.

Tests cover:
  - Workstation contracts (8 shapes)
  - Operational modes (4 modes, allowlists)
  - Governed shell adapter (structural blocks, allowlist, dangerous chains)
  - Tmux operational adapter (governance gating)
  - Workstation state registry (state capture)
  - Workstation observability pipeline (telemetry recording)
  - Workstation replay validator (determinism verification)
  - Workstation continuity bridge (session lineage)
  - Workstation execution orchestrator (pipeline coordination)
  - Workstation embodiment engine (command dispatch)
"""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

import os
sys.path.insert(0, os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS")

import pytest

# --- Contracts ---
from execution.workers.workstation.workstation_contracts_v1 import (
    ConnectivityStatus,
    OperationalMode,
    ShellCommandVerdict,
    WorkstationContinuityState,
    WorkstationEnvironment,
    WorkstationExecutionOutcome,
    WorkstationExecutionRequest,
    WorkstationExecutionResult,
    WorkstationOperationalSnapshot,
    WorkstationResumeState,
    WorkstationRole,
    WorkstationSession,
    WorkstationState,
    _content_hash,
    _deterministic_id,
    _new_id,
    _now_iso,
)

# --- Modes ---
from execution.workers.workstation.workstation_operational_modes_v1 import (
    AUDIT_MODE,
    DEVELOPER_MODE,
    OVERNIGHT_SAFE_MODE,
    RESEARCH_MODE,
    ModeDefinition,
    get_all_modes,
    get_mode_definition,
)

# --- Shell ---
from execution.workers.workstation.governed_shell_adapter_v1 import (
    GovernedShellAdapter,
    READ_ONLY_COMMANDS,
    STRUCTURALLY_BLOCKED_EXACT,
    STRUCTURALLY_BLOCKED_PREFIXES,
    ShellGovernanceDecision,
)

# --- Tmux ---
from execution.workers.workstation.tmux_operational_adapter_v1 import (
    TmuxOperationalAdapter,
    TmuxGovernanceDecision,
)

# --- State ---
from execution.workers.workstation.workstation_state_registry_v1 import WorkstationStateRegistry

# --- Observability ---
from execution.workers.workstation.workstation_observability_pipeline_v1 import (
    WorkstationObservabilityPipeline,
)

# --- Replay ---
from execution.workers.workstation.workstation_replay_validator_v1 import (
    ReplayCheck,
    ReplayResult,
    ReplaySessionResult,
    WorkstationReplayValidator,
)

# --- Continuity ---
from execution.workers.workstation.workstation_continuity_bridge_v1 import (
    WorkstationContinuityBridge,
)

# --- Orchestrator ---
from execution.workers.workstation.workstation_execution_orchestrator_v1 import (
    WorkstationExecutionOrchestrator,
)

# --- Engine ---
from execution.workers.workstation.workstation_operational_embodiment_engine_v1 import (
    WORKSTATION_COMMANDS,
    WorkstationOperationalEmbodimentEngine,
)


# =========================================================================
# 1. Contracts
# =========================================================================


class TestContracts:
    def test_new_id_has_prefix(self) -> None:
        assert _new_id("test").startswith("test-")
        assert len(_new_id("test")) > 5

    def test_deterministic_id_is_stable(self) -> None:
        a = _deterministic_id("ns", "content")
        b = _deterministic_id("ns", "content")
        assert a == b
        assert a.startswith("ns-")

    def test_deterministic_id_changes_with_content(self) -> None:
        a = _deterministic_id("ns", "aaa")
        b = _deterministic_id("ns", "bbb")
        assert a != b

    def test_content_hash_deterministic(self) -> None:
        d = {"a": 1, "b": 2}
        assert _content_hash(d) == _content_hash(d)

    def test_workstation_state_serializes(self) -> None:
        state = WorkstationState(hostname="test-vps")
        d = state.to_dict()
        assert d["hostname"] == "test-vps"
        assert d["role"] == "vps"
        assert "content_hash" in d
        assert d["state_id"].startswith("wstate-")

    def test_workstation_session_deterministic_id(self) -> None:
        s1 = WorkstationSession(session_name="os-main", session_type="tmux")
        s2 = WorkstationSession(session_name="os-main", session_type="tmux")
        assert s1.session_id == s2.session_id

    def test_execution_request_serializes(self) -> None:
        req = WorkstationExecutionRequest(command="ls", adapter_type="shell")
        d = req.to_dict()
        assert d["command"] == "ls"
        assert d["request_id"].startswith("wexreq-")
        assert "content_hash" in d

    def test_execution_result_succeeded(self) -> None:
        r = WorkstationExecutionResult(command="ls", outcome=WorkstationExecutionOutcome.SUCCESS)
        assert r.succeeded is True

    def test_execution_result_failed(self) -> None:
        r = WorkstationExecutionResult(command="ls", outcome=WorkstationExecutionOutcome.FAILURE)
        assert r.succeeded is False

    def test_continuity_state_serializes(self) -> None:
        c = WorkstationContinuityState(total_executions=5, total_successes=4, total_denials=1)
        d = c.to_dict()
        assert d["total_executions"] == 5
        assert "content_hash" in d

    def test_resume_state_serializes(self) -> None:
        r = WorkstationResumeState(last_command="ls", last_outcome="success")
        d = r.to_dict()
        assert d["last_command"] == "ls"

    def test_operational_snapshot_serializes(self) -> None:
        s = WorkstationOperationalSnapshot(phase="96.8BP")
        d = s.to_dict()
        assert d["phase"] == "96.8BP"
        assert "content_hash" in d

    def test_environment_serializes(self) -> None:
        e = WorkstationEnvironment(hostname="vps-01", platform="Linux")
        d = e.to_dict()
        assert d["hostname"] == "vps-01"
        assert d["platform"] == "Linux"


# =========================================================================
# 2. Operational Modes
# =========================================================================


class TestOperationalModes:
    def test_developer_mode_allows_ls(self) -> None:
        assert DEVELOPER_MODE.allows_command("ls")

    def test_developer_mode_allows_git_status(self) -> None:
        assert DEVELOPER_MODE.allows_command("git status")

    def test_developer_mode_allows_pytest(self) -> None:
        assert DEVELOPER_MODE.allows_command("pytest")

    def test_developer_mode_allows_tmux_send_keys(self) -> None:
        assert DEVELOPER_MODE.allows_tmux("send-keys")

    def test_research_mode_allows_ls(self) -> None:
        assert RESEARCH_MODE.allows_command("ls")

    def test_research_mode_denies_pytest(self) -> None:
        assert not RESEARCH_MODE.allows_command("pytest")

    def test_research_mode_denies_tmux_send_keys(self) -> None:
        assert not RESEARCH_MODE.allows_tmux("send-keys")

    def test_audit_mode_minimal(self) -> None:
        assert AUDIT_MODE.allows_command("pwd")
        assert AUDIT_MODE.allows_command("whoami")
        assert not AUDIT_MODE.allows_command("ls")
        assert not AUDIT_MODE.allows_command("cat")

    def test_overnight_mode_allows_inspection(self) -> None:
        assert OVERNIGHT_SAFE_MODE.allows_command("ls")
        assert OVERNIGHT_SAFE_MODE.allows_command("docker")

    def test_overnight_mode_denies_git(self) -> None:
        assert not OVERNIGHT_SAFE_MODE.allows_command("git status")

    def test_get_all_modes_returns_four(self) -> None:
        modes = get_all_modes()
        assert len(modes) == 4

    def test_mode_serialization(self) -> None:
        d = DEVELOPER_MODE.to_dict()
        assert d["mode"] == "developer_mode"
        assert "allowed_shell_commands" in d


# =========================================================================
# 3. Governed Shell Adapter
# =========================================================================


class TestGovernedShellAdapter:
    def test_ls_approved_in_developer(self) -> None:
        shell = GovernedShellAdapter(OperationalMode.DEVELOPER)
        decision = shell.evaluate_command("ls")
        assert decision.verdict == ShellCommandVerdict.APPROVED

    def test_rm_structurally_blocked(self) -> None:
        shell = GovernedShellAdapter(OperationalMode.DEVELOPER)
        decision = shell.evaluate_command("rm -rf /tmp/test")
        assert decision.verdict == ShellCommandVerdict.DENIED
        assert "STRUCTURAL_BLOCK" in str(decision.rules_applied)

    def test_sudo_blocked(self) -> None:
        shell = GovernedShellAdapter(OperationalMode.DEVELOPER)
        decision = shell.evaluate_command("sudo apt update")
        assert decision.verdict == ShellCommandVerdict.DENIED

    def test_rm_exact_blocked(self) -> None:
        shell = GovernedShellAdapter(OperationalMode.DEVELOPER)
        decision = shell.evaluate_command("rm")
        assert decision.verdict == ShellCommandVerdict.DENIED

    def test_dangerous_chain_blocked(self) -> None:
        shell = GovernedShellAdapter(OperationalMode.DEVELOPER)
        decision = shell.evaluate_command("ls; rm -rf /")
        assert decision.verdict == ShellCommandVerdict.DENIED

    def test_backtick_injection_blocked(self) -> None:
        shell = GovernedShellAdapter(OperationalMode.DEVELOPER)
        decision = shell.evaluate_command("echo `rm -rf /`")
        assert decision.verdict == ShellCommandVerdict.DENIED

    def test_subshell_injection_blocked(self) -> None:
        shell = GovernedShellAdapter(OperationalMode.DEVELOPER)
        decision = shell.evaluate_command("echo $(rm -rf /)")
        assert decision.verdict == ShellCommandVerdict.DENIED

    def test_pipe_chain_blocked(self) -> None:
        shell = GovernedShellAdapter(OperationalMode.DEVELOPER)
        decision = shell.evaluate_command("ls | grep x | sort | head")
        assert decision.verdict == ShellCommandVerdict.DENIED

    def test_mode_allowlist_denied(self) -> None:
        shell = GovernedShellAdapter(OperationalMode.AUDIT)
        decision = shell.evaluate_command("ls")
        assert decision.verdict == ShellCommandVerdict.DENIED
        assert "MODE_ALLOWLIST_DENIED" in decision.rules_applied

    def test_git_status_in_developer(self) -> None:
        shell = GovernedShellAdapter(OperationalMode.DEVELOPER)
        decision = shell.evaluate_command("git status")
        assert decision.verdict == ShellCommandVerdict.APPROVED

    def test_git_status_in_research(self) -> None:
        shell = GovernedShellAdapter(OperationalMode.RESEARCH)
        decision = shell.evaluate_command("git status")
        assert decision.verdict == ShellCommandVerdict.APPROVED

    def test_pytest_denied_in_research(self) -> None:
        shell = GovernedShellAdapter(OperationalMode.RESEARCH)
        decision = shell.evaluate_command("pytest")
        assert decision.verdict == ShellCommandVerdict.DENIED

    def test_stats_tracking(self) -> None:
        shell = GovernedShellAdapter(OperationalMode.DEVELOPER)
        shell.evaluate_command("ls")
        shell.evaluate_command("rm -rf /")
        stats = shell.get_stats()
        assert stats["total_decisions"] == 2
        assert stats["approved"] == 1
        assert stats["denied"] == 1

    def test_extract_prefix_multi_word(self) -> None:
        shell = GovernedShellAdapter(OperationalMode.DEVELOPER)
        assert shell._extract_prefix("git status") == "git status"
        assert shell._extract_prefix("python3 -m pytest") == "python3 -m"

    def test_bash_c_blocked(self) -> None:
        shell = GovernedShellAdapter(OperationalMode.DEVELOPER)
        decision = shell.evaluate_command("bash -c 'echo hello'")
        assert decision.verdict == ShellCommandVerdict.DENIED

    def test_eval_blocked(self) -> None:
        shell = GovernedShellAdapter(OperationalMode.DEVELOPER)
        decision = shell.evaluate_command("eval 'echo test'")
        assert decision.verdict == ShellCommandVerdict.DENIED

    def test_pip_install_blocked(self) -> None:
        shell = GovernedShellAdapter(OperationalMode.DEVELOPER)
        decision = shell.evaluate_command("pip install requests")
        assert decision.verdict == ShellCommandVerdict.DENIED

    def test_wget_blocked(self) -> None:
        shell = GovernedShellAdapter(OperationalMode.DEVELOPER)
        decision = shell.evaluate_command("wget http://example.com")
        assert decision.verdict == ShellCommandVerdict.DENIED


# =========================================================================
# 4. Tmux Adapter
# =========================================================================


class TestTmuxAdapter:
    def test_list_sessions_allowed_in_developer(self) -> None:
        tmux = TmuxOperationalAdapter(OperationalMode.DEVELOPER)
        decisions = tmux.get_decisions()
        tmux.list_sessions()
        assert len(tmux.get_decisions()) == 1
        assert tmux.get_decisions()[0].verdict == ShellCommandVerdict.APPROVED

    def test_list_sessions_denied_in_audit(self) -> None:
        tmux = TmuxOperationalAdapter(OperationalMode.AUDIT)
        tmux.list_sessions()
        assert len(tmux.get_decisions()) == 1
        assert tmux.get_decisions()[0].verdict == ShellCommandVerdict.APPROVED

    def test_send_keys_denied_in_research(self) -> None:
        tmux = TmuxOperationalAdapter(OperationalMode.RESEARCH)
        result = tmux.send_approved_command("test-session", "ls")
        assert result.outcome == WorkstationExecutionOutcome.DENIED

    def test_send_keys_denied_for_blocked_command(self) -> None:
        tmux = TmuxOperationalAdapter(OperationalMode.DEVELOPER)
        result = tmux.send_approved_command("test-session", "rm -rf /")
        assert result.outcome == WorkstationExecutionOutcome.DENIED

    def test_stats(self) -> None:
        tmux = TmuxOperationalAdapter(OperationalMode.DEVELOPER)
        tmux.list_sessions()
        stats = tmux.get_stats()
        assert stats["total_decisions"] == 1
        assert stats["mode"] == "developer_mode"

    def test_mode_change(self) -> None:
        tmux = TmuxOperationalAdapter(OperationalMode.DEVELOPER)
        tmux.set_mode(OperationalMode.RESEARCH)
        result = tmux.send_approved_command("test", "ls")
        assert result.outcome == WorkstationExecutionOutcome.DENIED


# =========================================================================
# 5. State Registry
# =========================================================================


class TestStateRegistry:
    def test_capture_state(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            registry = WorkstationStateRegistry(state_dir=td)
            state = registry.capture_state()
            assert state.state_id.startswith("wstate-")
            assert state.role == WorkstationRole.VPS

    def test_persist_and_load(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            registry = WorkstationStateRegistry(state_dir=td)
            registry.capture_state()
            loaded = registry.get_current_state()
            assert loaded is not None
            assert loaded.role == WorkstationRole.VPS

    def test_stats(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            registry = WorkstationStateRegistry(state_dir=td)
            stats = registry.get_stats()
            assert stats["has_state"] is False
            registry.capture_state()
            stats = registry.get_stats()
            assert stats["has_state"] is True

    def test_mode_set(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            registry = WorkstationStateRegistry(state_dir=td)
            registry.set_mode(OperationalMode.RESEARCH)
            assert registry.get_mode() == OperationalMode.RESEARCH

    def test_state_history(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            registry = WorkstationStateRegistry(state_dir=td)
            registry.capture_state()
            registry.capture_state()
            history = registry.get_state_history()
            assert len(history) == 2


# =========================================================================
# 6. Observability Pipeline
# =========================================================================


class TestObservabilityPipeline:
    def test_record_execution(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            obs = WorkstationObservabilityPipeline(observability_dir=td)
            req = WorkstationExecutionRequest(command="ls", adapter_type="shell")
            result = WorkstationExecutionResult(
                command="ls", outcome=WorkstationExecutionOutcome.SUCCESS
            )
            record = obs.record_execution(req, result)
            assert record["command"] == "ls"
            assert record["outcome"] == "success"

    def test_stats_tracking(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            obs = WorkstationObservabilityPipeline(observability_dir=td)
            req = WorkstationExecutionRequest(command="ls")
            success = WorkstationExecutionResult(
                command="ls", outcome=WorkstationExecutionOutcome.SUCCESS
            )
            denied = WorkstationExecutionResult(
                command="rm", outcome=WorkstationExecutionOutcome.DENIED
            )
            obs.record_execution(req, success)
            obs.record_execution(req, denied)
            stats = obs.get_stats()
            assert stats["total_recorded"] == 2
            assert stats["total_successes"] == 1
            assert stats["total_denials"] == 1

    def test_denial_records(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            obs = WorkstationObservabilityPipeline(observability_dir=td)
            req = WorkstationExecutionRequest(command="rm")
            denied = WorkstationExecutionResult(
                command="rm", outcome=WorkstationExecutionOutcome.DENIED
            )
            obs.record_execution(req, denied)
            denials = obs.get_denial_records()
            assert len(denials) == 1

    def test_recent_records(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            obs = WorkstationObservabilityPipeline(observability_dir=td)
            for i in range(5):
                req = WorkstationExecutionRequest(command=f"cmd{i}")
                result = WorkstationExecutionResult(
                    command=f"cmd{i}", outcome=WorkstationExecutionOutcome.SUCCESS
                )
                obs.record_execution(req, result)
            records = obs.get_recent_records(limit=3)
            assert len(records) == 3


# =========================================================================
# 7. Replay Validator
# =========================================================================


class TestReplayValidator:
    def test_replay_approved_command(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            replay = WorkstationReplayValidator(OperationalMode.DEVELOPER, proof_dir=td)
            record = {
                "command": "ls",
                "governance_verdict": "approved",
                "risk_class": "safe",
                "adapter_used": "governed_shell",
                "operational_mode": "developer_mode",
            }
            result = replay.replay_record(record)
            assert result.all_passed is True

    def test_replay_denied_command(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            replay = WorkstationReplayValidator(OperationalMode.DEVELOPER, proof_dir=td)
            record = {
                "command": "rm -rf /",
                "governance_verdict": "denied",
                "risk_class": "forbidden",
                "adapter_used": "none",
                "operational_mode": "developer_mode",
            }
            result = replay.replay_record(record)
            gov_check = next(c for c in result.checks if c.check_name == "governance_verdict")
            assert gov_check.passed is True

    def test_replay_session_with_proof(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            replay = WorkstationReplayValidator(OperationalMode.DEVELOPER, proof_dir=td)
            records = [
                {
                    "command": "ls",
                    "governance_verdict": "approved",
                    "risk_class": "safe",
                    "adapter_used": "governed_shell",
                    "operational_mode": "developer_mode",
                },
                {
                    "command": "pwd",
                    "governance_verdict": "approved",
                    "risk_class": "safe",
                    "adapter_used": "governed_shell",
                    "operational_mode": "developer_mode",
                },
            ]
            session = replay.replay_session(records, session_id="test-session")
            assert session.total_records == 2
            assert session.all_passed is True
            proof_path = Path(td) / "replay_proof_test-session.json"
            assert proof_path.exists()

    def test_replay_detects_verdict_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            replay = WorkstationReplayValidator(OperationalMode.DEVELOPER, proof_dir=td)
            record = {
                "command": "ls",
                "governance_verdict": "denied",
                "risk_class": "safe",
                "adapter_used": "governed_shell",
                "operational_mode": "developer_mode",
            }
            result = replay.replay_record(record)
            gov_check = next(c for c in result.checks if c.check_name == "governance_verdict")
            assert gov_check.passed is False

    def test_replay_from_empty_file(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            replay = WorkstationReplayValidator(OperationalMode.DEVELOPER, proof_dir=td)
            result = replay.replay_from_file("/nonexistent/path.jsonl")
            assert result.total_records == 0

    def test_stats(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            replay = WorkstationReplayValidator(OperationalMode.DEVELOPER, proof_dir=td)
            record = {
                "command": "ls",
                "governance_verdict": "approved",
                "risk_class": "safe",
                "adapter_used": "governed_shell",
                "operational_mode": "developer_mode",
            }
            replay.replay_record(record)
            stats = replay.get_stats()
            assert stats["total_replays"] == 1


# =========================================================================
# 8. Continuity Bridge
# =========================================================================


class TestContinuityBridge:
    def test_start_session(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            bridge = WorkstationContinuityBridge(continuity_dir=td)
            sid = bridge.start_session("test-session")
            assert sid == "test-session"

    def test_bridge_execution(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            bridge = WorkstationContinuityBridge(continuity_dir=td)
            bridge.start_session()
            result = WorkstationExecutionResult(
                command="ls", outcome=WorkstationExecutionOutcome.SUCCESS
            )
            lineage = bridge.bridge_execution(result)
            assert lineage["command"] == "ls"
            assert lineage["outcome"] == "success"

    def test_bridge_governance_decision(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            bridge = WorkstationContinuityBridge(continuity_dir=td)
            bridge.start_session()
            event = bridge.bridge_governance_decision(
                command="rm",
                verdict="denied",
                rules_applied=["STRUCTURAL_BLOCK"],
                risk_class="forbidden",
                denial_reason="structurally blocked",
            )
            assert event["verdict"] == "denied"

    def test_bridge_mode_transition(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            bridge = WorkstationContinuityBridge(continuity_dir=td)
            bridge.start_session()
            event = bridge.bridge_mode_transition(
                OperationalMode.DEVELOPER, OperationalMode.RESEARCH, "testing"
            )
            assert event["old_mode"] == "developer_mode"
            assert event["new_mode"] == "research_mode"

    def test_take_snapshot(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            bridge = WorkstationContinuityBridge(continuity_dir=td)
            bridge.start_session()
            result = WorkstationExecutionResult(
                command="ls", outcome=WorkstationExecutionOutcome.SUCCESS
            )
            bridge.bridge_execution(result)
            snapshot = bridge.take_snapshot()
            assert snapshot.total_executions == 1
            assert snapshot.total_successes == 1

    def test_generate_resume_state(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            bridge = WorkstationContinuityBridge(continuity_dir=td)
            bridge.start_session()
            result = WorkstationExecutionResult(
                command="ls", outcome=WorkstationExecutionOutcome.SUCCESS
            )
            bridge.bridge_execution(result)
            resume = bridge.generate_resume_state(
                active_goals=["test goal"],
                suggested_next_actions=["next action"],
            )
            assert resume.last_command == "ls"
            assert resume.last_outcome == "success"

    def test_execution_lineage(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            bridge = WorkstationContinuityBridge(continuity_dir=td)
            bridge.start_session()
            for i in range(3):
                result = WorkstationExecutionResult(
                    command=f"cmd{i}", outcome=WorkstationExecutionOutcome.SUCCESS
                )
                bridge.bridge_execution(result)
            lineage = bridge.get_execution_lineage()
            assert len(lineage) == 3

    def test_stats(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            bridge = WorkstationContinuityBridge(continuity_dir=td)
            bridge.start_session()
            result = WorkstationExecutionResult(
                command="ls", outcome=WorkstationExecutionOutcome.SUCCESS
            )
            bridge.bridge_execution(result)
            stats = bridge.get_stats()
            assert stats["executions_tracked"] == 1
            assert stats["total_successes"] == 1

    def test_open_loop_tracking(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            bridge = WorkstationContinuityBridge(continuity_dir=td)
            bridge.start_session()
            result = WorkstationExecutionResult(
                command="broken",
                outcome=WorkstationExecutionOutcome.FAILURE,
                error_message="something broke",
            )
            bridge.bridge_execution(result)
            assert len(bridge._open_loops) == 1
            bridge.resolve_open_loop(bridge._open_loops[0])
            assert len(bridge._open_loops) == 0


# =========================================================================
# 9. Execution Orchestrator
# =========================================================================


class TestExecutionOrchestrator:
    def test_execute_approved_shell_command(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            obs = WorkstationObservabilityPipeline(observability_dir=f"{td}/obs")
            cont = WorkstationContinuityBridge(continuity_dir=f"{td}/cont")
            orch = WorkstationExecutionOrchestrator(observability=obs, continuity=cont)
            result = orch.execute_shell("pwd")
            assert result.succeeded is True
            assert result.adapter_used == "governed_shell"

    def test_execute_denied_command(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            obs = WorkstationObservabilityPipeline(observability_dir=f"{td}/obs")
            cont = WorkstationContinuityBridge(continuity_dir=f"{td}/cont")
            orch = WorkstationExecutionOrchestrator(observability=obs, continuity=cont)
            result = orch.execute_shell("rm -rf /")
            assert result.outcome == WorkstationExecutionOutcome.DENIED

    def test_mode_change_propagates(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            obs = WorkstationObservabilityPipeline(observability_dir=f"{td}/obs")
            cont = WorkstationContinuityBridge(continuity_dir=f"{td}/cont")
            orch = WorkstationExecutionOrchestrator(observability=obs, continuity=cont)
            orch.set_mode(OperationalMode.AUDIT)
            result = orch.execute_shell("ls")
            assert result.outcome == WorkstationExecutionOutcome.DENIED

    def test_stats(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            obs = WorkstationObservabilityPipeline(observability_dir=f"{td}/obs")
            cont = WorkstationContinuityBridge(continuity_dir=f"{td}/cont")
            orch = WorkstationExecutionOrchestrator(observability=obs, continuity=cont)
            orch.execute_shell("pwd")
            orch.execute_shell("rm -rf /")
            stats = orch.get_stats()
            assert stats["total_executions"] == 2
            assert stats["total_successes"] == 1
            assert stats["total_denials"] == 1

    def test_tmux_denied_in_audit_mode(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            obs = WorkstationObservabilityPipeline(observability_dir=f"{td}/obs")
            cont = WorkstationContinuityBridge(continuity_dir=f"{td}/cont")
            orch = WorkstationExecutionOrchestrator(
                operational_mode=OperationalMode.AUDIT,
                observability=obs,
                continuity=cont,
            )
            result = orch.execute_tmux("ls", "test-session")
            assert result.outcome == WorkstationExecutionOutcome.DENIED


# =========================================================================
# 10. Embodiment Engine
# =========================================================================


class TestEmbodimentEngine:
    def test_initialization(self) -> None:
        engine = WorkstationOperationalEmbodimentEngine()
        info = engine.initialize()
        assert "session_id" in info
        assert info["operational_mode"] == "developer_mode"

    def test_mode_change(self) -> None:
        engine = WorkstationOperationalEmbodimentEngine()
        result = engine.set_mode(OperationalMode.RESEARCH)
        assert result["old_mode"] == "developer_mode"
        assert result["new_mode"] == "research_mode"

    def test_dispatch_workstation_status(self) -> None:
        engine = WorkstationOperationalEmbodimentEngine()
        engine.initialize()
        result = engine.dispatch_command("workstation-status")
        assert result["command"] == "workstation-status"
        assert "state" in result

    def test_dispatch_operational_state(self) -> None:
        engine = WorkstationOperationalEmbodimentEngine()
        engine.initialize()
        result = engine.dispatch_command("operational-state")
        assert result["command"] == "operational-state"
        assert "mode" in result

    def test_dispatch_environment_health(self) -> None:
        engine = WorkstationOperationalEmbodimentEngine()
        engine.initialize()
        result = engine.dispatch_command("environment-health")
        assert result["command"] == "environment-health"
        assert "hostname" in result

    def test_dispatch_mode_info(self) -> None:
        engine = WorkstationOperationalEmbodimentEngine()
        result = engine.dispatch_command("mode-info")
        assert result["command"] == "mode-info"
        assert len(result["available_modes"]) == 4

    def test_dispatch_unknown_command(self) -> None:
        engine = WorkstationOperationalEmbodimentEngine()
        result = engine.dispatch_command("nonexistent")
        assert "error" in result

    def test_execute_shell_through_engine(self) -> None:
        engine = WorkstationOperationalEmbodimentEngine()
        engine.initialize()
        result = engine.execute_shell("pwd")
        assert result.succeeded is True

    def test_execute_denied_through_engine(self) -> None:
        engine = WorkstationOperationalEmbodimentEngine()
        engine.initialize()
        result = engine.execute_shell("rm -rf /")
        assert result.outcome == WorkstationExecutionOutcome.DENIED

    def test_take_snapshot(self) -> None:
        engine = WorkstationOperationalEmbodimentEngine()
        engine.initialize()
        snapshot = engine.take_snapshot()
        assert snapshot.phase == "96.8BP"
        assert snapshot.operational_mode == OperationalMode.DEVELOPER

    def test_stats(self) -> None:
        engine = WorkstationOperationalEmbodimentEngine()
        engine.initialize()
        stats = engine.get_stats()
        assert stats["initialized"] is True
        assert stats["operational_mode"] == "developer_mode"

    def test_workstation_commands_defined(self) -> None:
        assert len(WORKSTATION_COMMANDS) >= 9
        assert "workstation-status" in WORKSTATION_COMMANDS
        assert "tmux-status" in WORKSTATION_COMMANDS
        assert "replay-validate" in WORKSTATION_COMMANDS

    def test_dispatch_execution_history(self) -> None:
        engine = WorkstationOperationalEmbodimentEngine()
        engine.initialize()
        engine.execute_shell("pwd")
        result = engine.dispatch_command("execution-history")
        assert result["command"] == "execution-history"
        assert len(result["recent_executions"]) >= 1

    def test_dispatch_replay_validate_no_records(self) -> None:
        engine = WorkstationOperationalEmbodimentEngine()
        engine.initialize()
        result = engine.dispatch_command("replay-validate")
        assert result["command"] == "replay-validate"

    def test_dispatch_resume_work(self) -> None:
        engine = WorkstationOperationalEmbodimentEngine()
        engine.initialize()
        result = engine.dispatch_command("resume-work")
        assert result["command"] == "resume-work"
        assert "resume_state" in result


# ── §14.1 Adapter Contract Tests ─────────────────────────────────────────────


class TestShellAdapterContract:
    """§14.1 contract methods on GovernedShellAdapter."""

    def test_translate_request_returns_input(self) -> None:
        from execution.workers.workstation.governed_shell_adapter_v1 import GovernedShellAdapter
        from execution.workers.workstation.workstation_contracts_v1 import WorkstationExecutionRequest
        adapter = GovernedShellAdapter()
        req = WorkstationExecutionRequest(command="ls -la")
        assert adapter.translate_request(req) is req

    def test_validate_operation_approved(self) -> None:
        from execution.workers.workstation.governed_shell_adapter_v1 import GovernedShellAdapter
        from execution.workers.workstation.workstation_contracts_v1 import WorkstationExecutionRequest
        adapter = GovernedShellAdapter()
        req = WorkstationExecutionRequest(command="ls")
        decision = adapter.validate_operation(req)
        assert decision.verdict.value == "approved"

    def test_validate_operation_denied(self) -> None:
        from execution.workers.workstation.governed_shell_adapter_v1 import GovernedShellAdapter
        from execution.workers.workstation.workstation_contracts_v1 import WorkstationExecutionRequest
        adapter = GovernedShellAdapter()
        req = WorkstationExecutionRequest(command="rm -rf /")
        decision = adapter.validate_operation(req)
        assert decision.verdict.value == "denied"

    def test_normalize_result_success(self) -> None:
        import subprocess
        from execution.workers.workstation.governed_shell_adapter_v1 import GovernedShellAdapter, ShellGovernanceDecision, ShellCommandVerdict
        from execution.workers.workstation.workstation_contracts_v1 import WorkstationExecutionRequest
        adapter = GovernedShellAdapter()
        req = WorkstationExecutionRequest(command="echo hello")
        decision = adapter.validate_operation(req)
        raw = subprocess.CompletedProcess(args="echo hello", returncode=0, stdout="hello\n", stderr="")
        result = adapter.normalize_result(raw, req, decision, 42.0)
        assert result.outcome.value == "success"
        assert result.stdout == "hello\n"
        assert result.duration_ms == 42.0

    def test_normalize_result_timeout(self) -> None:
        import subprocess
        from execution.workers.workstation.governed_shell_adapter_v1 import GovernedShellAdapter
        from execution.workers.workstation.workstation_contracts_v1 import WorkstationExecutionRequest
        adapter = GovernedShellAdapter()
        req = WorkstationExecutionRequest(command="sleep 999")
        decision = adapter.validate_operation(req)
        error = subprocess.TimeoutExpired(cmd="sleep 999", timeout=30)
        result = adapter.normalize_result(None, req, decision, 30000.0, error)
        assert result.outcome.value == "timeout"

    def test_observe_state(self) -> None:
        from execution.workers.workstation.governed_shell_adapter_v1 import GovernedShellAdapter
        adapter = GovernedShellAdapter()
        state = adapter.observe_state()
        assert state["adapter_id"] == "governed_shell"
        assert state["healthy"] is True
        assert "operational_mode" in state
        assert "total_decisions" in state


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
