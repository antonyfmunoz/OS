"""Sprint 1 smoke tests — production stabilization.

Validates the fixes for:
1. NodeRegistry deadlock (Lock → RLock)
2. Missing runtime_execution_result_v1 module
3. Missing runtime_presence_state_v1 module
4. Ghost runtime/.env references (context.py crash)
5. Import chains for os-discord, os-operator, and node mesh
"""

import os
import threading

import pytest

os.environ.setdefault("EOS_ORG_ID", "test-org-id")
os.environ.setdefault("EOS_USER_ID", "test-user-id")


class TestNodeRegistryDeadlock:
    """Verify NodeRegistry uses RLock to prevent deadlock on heartbeat update."""

    def test_lock_is_reentrant(self):
        from transports.node_mesh.registry import NodeRegistry

        reg = NodeRegistry()
        assert isinstance(reg._lock, type(threading.RLock()))

    def test_update_heartbeat_does_not_deadlock(self):
        from transports.node_mesh.registry import NodeRegistry

        reg = NodeRegistry()
        result = reg.update_heartbeat("nonexistent-node")
        assert result is False

    def test_node_count_under_lock(self):
        from transports.node_mesh.registry import NodeRegistry

        reg = NodeRegistry()
        assert reg.node_count() == 0


class TestRuntimeExecutionResultV1:
    """Verify the restored runtime_execution_result_v1 module."""

    def test_imports(self):
        from substrate.execution.runtime.runtime_execution_result_v1 import (
            ExecutionOutcome,
            ProofArtifact,
            ProofArtifactType,
            RuntimeExecutionResult,
            persist_execution_result,
        )

        assert ExecutionOutcome.SUCCESS.value == "success"
        assert ProofArtifactType.DISPATCH_PROOF.value == "dispatch_proof"
        assert callable(persist_execution_result)

    def test_result_creation_and_hash(self):
        from substrate.execution.runtime.runtime_execution_result_v1 import (
            ExecutionOutcome,
            RuntimeExecutionResult,
        )

        r = RuntimeExecutionResult(
            result_id="",
            dispatch_id="d1",
            packet_id="p1",
            worker_id="w1",
            session_id="s1",
            action_type="test_action",
            outcome=ExecutionOutcome.SUCCESS,
        )
        assert r.result_id.startswith("RESULT-")
        assert r.succeeded is True
        h = r.compute_result_hash()
        assert len(h) == 16
        assert r.result_hash == h

    def test_result_serialization(self):
        from substrate.execution.runtime.runtime_execution_result_v1 import (
            ExecutionOutcome,
            ProofArtifact,
            ProofArtifactType,
            RuntimeExecutionResult,
        )

        proof = ProofArtifact(
            proof_id="",
            proof_type=ProofArtifactType.EXECUTION_PROOF,
            evidence={"key": "value"},
            worker_id="w1",
        )
        r = RuntimeExecutionResult(
            result_id="",
            dispatch_id="d1",
            packet_id="p1",
            worker_id="w1",
            session_id="s1",
            action_type="test",
            outcome=ExecutionOutcome.FAILURE,
            proof_artifacts=[proof],
        )
        d = r.to_dict()
        assert d["succeeded"] is False
        assert d["outcome"] == "failure"
        assert len(d["proof_artifacts"]) == 1
        assert d["proof_artifacts"][0]["proof_type"] == "execution_proof"

    def test_failure_outcome(self):
        from substrate.execution.runtime.runtime_execution_result_v1 import (
            ExecutionOutcome,
            RuntimeExecutionResult,
        )

        r = RuntimeExecutionResult(
            result_id="",
            dispatch_id="d1",
            packet_id="p1",
            worker_id="w1",
            session_id="s1",
            action_type="test",
            outcome=ExecutionOutcome.FAILURE,
        )
        assert r.succeeded is False


class TestRuntimePresenceStateV1:
    """Verify the restored runtime_presence_state_v1 module."""

    def test_imports(self):
        from substrate.execution.runtime.runtime_presence_state_v1 import (
            WorkstationPresence,
            WorkstationPresenceState,
            is_execution_capable,
        )

        assert WorkstationPresenceState.ACTIVE.value == "active"
        assert callable(is_execution_capable)

    def test_presence_transitions(self):
        from substrate.execution.runtime.runtime_presence_state_v1 import (
            WorkstationPresence,
            WorkstationPresenceState,
            is_execution_capable,
        )

        p = WorkstationPresence()
        assert p.current_state == WorkstationPresenceState.UNKNOWN
        assert is_execution_capable(p) is False

        p.transition(WorkstationPresenceState.ACTIVE, reason="test")
        assert p.current_state == WorkstationPresenceState.ACTIVE
        assert is_execution_capable(p) is True

        p.transition(WorkstationPresenceState.EXECUTING, packet_id="pk1")
        assert p.current_state == WorkstationPresenceState.EXECUTING
        assert is_execution_capable(p) is False

    def test_presence_serialization(self):
        from substrate.execution.runtime.runtime_presence_state_v1 import (
            WorkstationPresence,
            WorkstationPresenceState,
        )

        p = WorkstationPresence()
        p.transition(WorkstationPresenceState.IDLE, reason="startup")
        d = p.to_dict()
        assert d["state"] == "idle"
        assert d["reason"] == "startup"


class TestSupervisorImportChain:
    """Verify that the full supervisor import chain works."""

    def test_supervisor_imports(self):
        from substrate.execution.runtime.local_runtime_supervisor_v1 import (
            LocalRuntimeSupervisor,
            SupervisorState,
        )

        assert SupervisorState.RUNNING.value == "running"

    def test_live_execution_imports(self):
        from substrate.execution.runtime.live_local_runtime_execution_v1 import (
            ExecutionSpineOutcome,
            LiveLocalRuntimeExecution,
        )

        assert ExecutionSpineOutcome.SUCCESS.value == "success"


class TestContextEnvLoading:
    """Verify context.py loads .env correctly and handles missing vars."""

    def test_load_context_with_env(self):
        os.environ["EOS_ORG_ID"] = "smoke-org"
        os.environ["EOS_USER_ID"] = "smoke-user"
        try:
            from substrate.state.context.context import load_context_from_env

            ctx = load_context_from_env()
            assert ctx.org_id == "smoke-org"
            assert ctx.user_id == "smoke-user"
        finally:
            os.environ["EOS_ORG_ID"] = "test-org-id"
            os.environ["EOS_USER_ID"] = "test-user-id"

    def test_load_context_missing_vars_raises(self):
        saved_org = os.environ.pop("EOS_ORG_ID", None)
        saved_user = os.environ.pop("EOS_USER_ID", None)
        try:
            from substrate.state.context.context import load_context_from_env

            with pytest.raises(KeyError):
                load_context_from_env()
        finally:
            if saved_org:
                os.environ["EOS_ORG_ID"] = saved_org
            if saved_user:
                os.environ["EOS_USER_ID"] = saved_user

    def test_try_load_context_missing_vars_returns_none(self):
        saved_org = os.environ.pop("EOS_ORG_ID", None)
        saved_user = os.environ.pop("EOS_USER_ID", None)
        try:
            from substrate.state.context.context import try_load_context_from_env

            assert try_load_context_from_env() is None
        finally:
            if saved_org:
                os.environ["EOS_ORG_ID"] = saved_org
            if saved_user:
                os.environ["EOS_USER_ID"] = saved_user


class TestServiceImportSmoke:
    """Smoke-test that key service modules can be imported without crash."""

    def test_node_mesh_registry(self):
        from transports.node_mesh.registry import NodeRegistry

        assert NodeRegistry is not None

    def test_operator_module_exists(self):
        """Verify transports/api/operator.py can be found (not fully imported
        because it starts a FastAPI app with side effects)."""
        from pathlib import Path

        assert Path("transports/api/operator.py").exists()

    def test_discord_bot_module_exists(self):
        from pathlib import Path

        assert Path("services/discord_bot.py").exists()

    @pytest.mark.skipif(
        not os.environ.get("ANTHROPIC_API_KEY"),
        reason="No API key — skip runtime instantiation",
    )
    def test_agent_runtime_import(self):
        from adapters.models.agent_runtime import AgentRuntime, TaskType

        assert TaskType.SCORE.value == "score"
