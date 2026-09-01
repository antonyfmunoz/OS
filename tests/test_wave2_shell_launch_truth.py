from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

from nodes.windows.umh_node import client as client_mod
from substrate.execution.attempts.model_executors.codex import (
    _codex_executable_attestation,
    _file_sha256,
)
from substrate.execution.attempts.poller import ControlPlanePoller, _WorkerResultView
from substrate.execution.attempts.worker_model_executor import run_worker_in_lease
from substrate.execution.durable_remote_transport import (
    SHELL_LAUNCH_IN_PROGRESS,
    SHELL_LAUNCH_INTENT_PERSISTED,
    SHELL_LAUNCH_RUNNING,
    SHELL_PROCESS_IDENTITY_PERSISTED,
    durable_execution_identity,
)
from tests.test_mesh_dispatch_governed import (
    _durable_mesh_server,
    _durable_node_client,
    _durable_request,
    _MeshHandlerWs,
)


@pytest.fixture(autouse=True)
def _isolate_controller_store(tmp_path, monkeypatch):
    monkeypatch.setenv("UMH_DURABLE_REMOTE_ROOT", str(tmp_path / "controller"))


def _launch_material(client, req, claim_id: str) -> dict:
    execution_identity = client._durable_execution_identity(req, claim_id=claim_id)
    return {
        "command_digest": req.payload_digest,
        "root_pid": None,
        "execution_identity": execution_identity,
        "launch_intent_id": "launch-intent-1",
        "launch_not_attempted": True,
    }


def _persist_launch(client, req, claim_id: str, *, attempted: bool = False) -> dict:
    material = _launch_material(client, req, claim_id)
    client._durable_store.mark_shell_launch_state(
        req.request_id,
        claim_id=claim_id,
        launch_state=SHELL_LAUNCH_INTENT_PERSISTED,
        launch_material=material,
    )
    if attempted:
        material = {**material, "launch_not_attempted": False, "launch_attempted_at": 1.0}
        client._durable_store.mark_shell_launch_state(
            req.request_id,
            claim_id=claim_id,
            launch_state=SHELL_LAUNCH_IN_PROGRESS,
            launch_material=material,
        )
    return material


def test_crash_after_intent_before_launch_is_definite_no_launch(tmp_path, monkeypatch):
    client = _durable_node_client(tmp_path)
    req = client._durable_store.put_request(_durable_request())
    claim_id = "claim-launch"
    client._durable_store.mark_claimed(req.request_id, claim_id=claim_id)
    _persist_launch(client, req, claim_id)

    async def _send(*_args, **_kwargs):
        return {"ok": True}

    monkeypatch.setattr(client, "_send_durable_event", _send)
    current = client._durable_store.get_request(req.request_id)
    assert current is not None
    assert asyncio.run(client._recover_interrupted_shell_launch(current)) is True
    result = client._durable_store.result_for(req.request_id)
    assert result is not None and result["state"] == "FAILED"
    assert result["cleanup"]["launch_not_attempted"] is True
    assert result["cleanup"]["process_residue"] == []


def test_crash_after_launch_attempt_before_pid_persistence_reconciles_and_fences_relaunch(
    tmp_path,
):
    client = _durable_node_client(tmp_path)
    req = client._durable_store.put_request(_durable_request())
    claim_id = "claim-uncertain"
    client._durable_store.mark_claimed(req.request_id, claim_id=claim_id)
    _persist_launch(client, req, claim_id, attempted=True)
    current = client._durable_store.get_request(req.request_id)
    assert current is not None

    assert asyncio.run(client._recover_interrupted_shell_launch(current)) is True
    recovered = client._durable_store.get_request(req.request_id)
    assert recovered is not None
    assert recovered.lifecycle_state == "RECONCILIATION_REQUIRED"
    assert recovered.cleanup["duplicate_launch_fenced"] is True
    assert recovered.cleanup["execution_outcome_unknown"] is True
    assert client._durable_store.result_for(req.request_id) is None


def test_persisted_exact_process_identity_recovers_without_duplicate_launch(
    tmp_path,
    monkeypatch,
):
    client = _durable_node_client(tmp_path)
    req = client._durable_store.put_request(_durable_request())
    claim_id = "claim-process"
    client._durable_store.mark_claimed(req.request_id, claim_id=claim_id)
    material = _persist_launch(client, req, claim_id, attempted=True)
    process_identity = {
        "pid": 4242,
        "start_token": "start-1",
        "executable": "powershell.exe",
        "command_digest": req.payload_digest,
    }
    client._durable_store.mark_shell_launch_state(
        req.request_id,
        claim_id=claim_id,
        launch_state=SHELL_PROCESS_IDENTITY_PERSISTED,
        launch_material={
            **material,
            "root_pid": 4242,
            "process_identity": process_identity,
        },
    )
    monkeypatch.setattr(
        client_mod,
        "_durable_process_identity_matches",
        lambda *_args, **_kwargs: (True, "exact", dict(process_identity)),
    )
    current = client._durable_store.get_request(req.request_id)
    assert current is not None
    assert asyncio.run(client._recover_interrupted_shell_launch(current)) is True
    recovered = client._durable_store.get_request(req.request_id)
    assert recovered is not None
    assert recovered.lifecycle_state == "RECONCILIATION_REQUIRED"
    assert recovered.cleanup["process_identity_match"] is True
    assert recovered.cleanup["duplicate_launch_fenced"] is True
    assert client._durable_store.result_for(req.request_id) is None


def test_pid_reuse_or_missing_process_never_attaches_or_kills_unknown_process(
    tmp_path,
    monkeypatch,
):
    client = _durable_node_client(tmp_path)
    req = client._durable_store.put_request(_durable_request())
    claim_id = "claim-reused-pid"
    client._durable_store.mark_claimed(req.request_id, claim_id=claim_id)
    material = _persist_launch(client, req, claim_id, attempted=True)
    client._durable_store.mark_shell_launch_state(
        req.request_id,
        claim_id=claim_id,
        launch_state=SHELL_PROCESS_IDENTITY_PERSISTED,
        launch_material={
            **material,
            "root_pid": 5151,
            "process_identity": {
                "pid": 5151,
                "start_token": "old-start",
                "executable": "expected.exe",
                "command_digest": req.payload_digest,
            },
        },
    )
    monkeypatch.setattr(
        client_mod,
        "_durable_process_identity_matches",
        lambda *_args, **_kwargs: (
            False,
            "process identity mismatch for start_token",
            {"pid": 5151, "start_token": "new-start", "executable": "unrelated.exe"},
        ),
    )
    current = client._durable_store.get_request(req.request_id)
    assert current is not None
    assert asyncio.run(client._recover_interrupted_shell_launch(current)) is True
    recovered = client._durable_store.get_request(req.request_id)
    assert recovered is not None
    assert recovered.lifecycle_state == "RECONCILIATION_REQUIRED"
    assert recovered.cleanup["process_identity_match"] is False
    assert client._durable_store.result_for(req.request_id) is None


def test_process_identity_rejects_observed_command_digest_change(monkeypatch):
    stored = {
        "pid": 6161,
        "start_token": "start-6161",
        "parent_pid": 100,
        "executable": "powershell.exe",
        "observed_command_digest": "a" * 64,
        "command_digest": "request-digest",
    }
    monkeypatch.setattr(
        client_mod,
        "_durable_process_identity",
        lambda *_args, **_kwargs: {
            **stored,
            "observed_command_digest": "b" * 64,
        },
    )

    matched, reason, _observed = client_mod._durable_process_identity_matches(
        stored,
        command_digest="request-digest",
    )

    assert matched is False
    assert reason == "process identity mismatch for observed_command_digest"


def test_cancel_and_redelivery_during_launch_uncertainty_never_terminalize_or_relaunch(
    tmp_path,
):
    client = _durable_node_client(tmp_path)
    req = client._durable_store.put_request(_durable_request())
    claim_id = "claim-cancel-uncertain"
    client._durable_store.mark_claimed(req.request_id, claim_id=claim_id)
    _persist_launch(client, req, claim_id, attempted=True)
    cancelled = client._durable_store.request_cancel(req.request_id)
    terminal = asyncio.run(
        client._cancel_durable_request(
            cancelled,
            claim_id=claim_id,
            reason="owner cancel",
        )
    )
    assert terminal.lifecycle_state == "RECONCILIATION_REQUIRED"
    assert terminal.cleanup["duplicate_launch_fenced"] is True
    assert client._durable_store.result_for(req.request_id) is None


def test_cancel_after_process_identity_uses_owned_cleanup_before_terminal_cancel(
    tmp_path, monkeypatch
):
    client = _durable_node_client(tmp_path)
    req = client._durable_store.put_request(_durable_request())
    claim_id = "claim-known-process"
    client._durable_store.mark_claimed(req.request_id, claim_id=claim_id)
    material = _persist_launch(client, req, claim_id, attempted=True)
    client._durable_store.mark_shell_launch_state(
        req.request_id,
        claim_id=claim_id,
        launch_state=SHELL_PROCESS_IDENTITY_PERSISTED,
        launch_material={
            **material,
            "root_pid": 5252,
            "process_identity": {
                "pid": 5252,
                "start_token": "start-5252",
                "executable": "powershell.exe",
                "command_digest": req.payload_digest,
            },
        },
    )

    class _Proc:
        pid = 5252

        def poll(self):
            return None

    client._durable_processes[req.request_id] = _Proc()
    current = client._durable_store.request_cancel(req.request_id)

    async def _terminate(_proc, *, graceful_timeout):
        assert _proc.pid == 5252
        return {
            "root_pid": 5252,
            "enumeration_performed": True,
            "enumeration_complete": True,
            "ownership_validated": True,
            "termination_attempted": True,
            "post_termination_enumeration_complete": True,
            "residue_count": 0,
            "cleanup_verified": True,
            "process_residue": [],
        }

    monkeypatch.setattr(client, "_terminate_durable_process_tree", _terminate)
    terminal = asyncio.run(
        client._cancel_durable_request(current, claim_id=claim_id, reason="owner cancel")
    )

    assert terminal.lifecycle_state == "CANCELLED"
    result = client._durable_store.result_for(req.request_id)
    assert result is not None and result["state"] == "CANCELLED"
    assert result["cleanup"]["cleanup_verified"] is True


def test_delivered_cancel_preserves_local_launch_uncertainty_and_reconciles(tmp_path):
    client = _durable_node_client(tmp_path)
    req = client._durable_store.put_request(_durable_request())
    claim_id = "claim-delivered-cancel"
    client._durable_store.mark_claimed(req.request_id, claim_id=claim_id)
    material = _persist_launch(client, req, claim_id, attempted=True)

    delivered = client._durable_store.get_request(req.request_id)
    assert delivered is not None
    delivered.lifecycle_state = "CANCEL_REQUESTED"
    delivered.cancellation_requested_at = 100.0
    delivered.cancellation_deadline_at = 130.0
    delivered.process_tree = {"node_pid": 1, "claimed_at": 1.0}

    asyncio.run(
        client._handle_durable_command(
            {"method": "durable_command.request", "params": delivered.to_dict()}
        )
    )

    current = client._durable_store.get_request(req.request_id)
    assert current is not None
    assert current.lifecycle_state == "RECONCILIATION_REQUIRED"
    assert current.process_tree["launch_state"] == SHELL_LAUNCH_IN_PROGRESS
    assert current.process_tree["launch_intent_id"] == material["launch_intent_id"]
    assert current.process_tree["launch_not_attempted"] is False
    assert current.cleanup["execution_outcome_unknown"] is True
    assert client._durable_store.result_for(req.request_id) is None


def test_windows_process_is_contained_and_identified_before_resume(tmp_path, monkeypatch):
    client = _durable_node_client(tmp_path)
    req = client._durable_store.put_request(_durable_request())
    client._durable_store.mark_claimed(req.request_id, claim_id="claim-suspended")
    events: list[str] = []
    popen_kwargs: dict = {}

    class _Proc:
        pid = 4242
        returncode = 0

        def poll(self):
            return 0

        def kill(self):
            events.append("kill")

        def wait(self, *, timeout=None):
            return 0

    class _Containment:
        containment_id = "launch"

        def pids(self):
            return [4242]

        def resume_suspended_process(self, _proc):
            events.append("resume")

        def close(self):
            events.append("close")

    class _Collector:
        def snapshot(self, *, join_timeout):
            return {
                "stdout": "ok",
                "stderr": "",
                "output_capture": {"timed_out": False},
            }

    original_mark = client._durable_store.mark_shell_launch_state

    def _mark(*args, **kwargs):
        events.append(f"persist:{kwargs['launch_state']}")
        return original_mark(*args, **kwargs)

    def _popen(*_args, **kwargs):
        popen_kwargs.update(kwargs)
        events.append("popen")
        return _Proc()

    def _attach(_proc, *, containment_id):
        assert containment_id
        events.append("attach")
        return _Containment()

    async def _announce(*_args, **_kwargs):
        events.append("announce")
        return {"ok": True}

    monkeypatch.setattr(client_mod.sys, "platform", "win32")
    monkeypatch.setattr(client_mod.subprocess, "CREATE_NO_WINDOW", 0x08000000, raising=False)
    monkeypatch.setattr(client_mod.subprocess, "Popen", _popen)
    monkeypatch.setattr(client_mod, "_durable_attach_process_containment", _attach)
    monkeypatch.setattr(client_mod, "_DurablePipeCollector", lambda _proc: _Collector())
    monkeypatch.setattr(
        client_mod,
        "_durable_process_identity",
        lambda pid, **_kwargs: {
            "pid": pid,
            "start_token": "start-4242",
            "executable": "powershell.exe",
            "command_digest": req.payload_digest,
        },
    )
    monkeypatch.setattr(client._durable_store, "mark_shell_launch_state", _mark)
    monkeypatch.setattr(client, "_announce_durable_running", _announce)
    monkeypatch.setattr(
        client_mod,
        "_durable_post_exit_process_cleanup",
        lambda *_args, **_kwargs: {
            "post_exit_process_check_ok": True,
            "enumeration_complete": True,
            "ownership_validated": True,
            "post_termination_enumeration_complete": True,
            "cleanup_verified": True,
            "process_residue": [],
        },
    )

    result = asyncio.run(
        client._execute_shell_for_durable(
            req,
            cap_name="shell",
            cap_params={"command": "echo ok"},
            claim_id="claim-suspended",
            process_tree={"node_pid": 1},
            timeout=5.0,
        )
    )

    assert result["success"] is True
    assert popen_kwargs["creationflags"] & 0x00000004
    assert events.index("attach") < events.index(f"persist:{SHELL_PROCESS_IDENTITY_PERSISTED}")
    assert events.index(f"persist:{SHELL_PROCESS_IDENTITY_PERSISTED}") < events.index("resume")
    assert events.index("resume") < events.index("announce")


def test_shell_execution_identity_is_complete_immutable_and_claim_bound(tmp_path):
    client = _durable_node_client(tmp_path)
    req = _durable_request()
    identity = client._durable_execution_identity(req, claim_id="claim-exact")
    assert {
        "request_id",
        "correlation_id",
        "node_id",
        "candidate_sha",
        "claim_id",
        "logical_execution_id",
        "execution_id",
        "idempotency_key",
        "capability",
        "operation_type",
        "payload_digest",
        "risk_class",
        "authority_id",
        "authoritative_effect_class",
        "effect_policy_id",
        "attempt",
    } <= identity.keys()
    assert identity["logical_execution_id"] == identity["execution_id"]
    assert client._durable_execution_identity(req, claim_id="claim-exact") == identity
    assert client._durable_execution_identity(req, claim_id="claim-foreign") != identity


def test_vps_rejects_partial_shell_running_identity_before_canonical_publication(tmp_path):
    server = _durable_mesh_server(tmp_path)
    req = server._durable_store.put_request(_durable_request())
    server._durable_store.mark_claimed(req.request_id, claim_id="claim-running")
    ws = _MeshHandlerWs()

    asyncio.run(
        server._handle_durable_claimed(
            req.node_id,
            {
                "request_id": req.request_id,
                "claim_id": "claim-running",
                "state": "RUNNING",
                "process_tree": {"root_pid": 4242},
            },
            "msg-partial-running",
            ws,
        )
    )

    current = server._durable_store.get_request(req.request_id)
    assert current is not None
    assert current.lifecycle_state == "RECONCILIATION_REQUIRED"
    assert ws.sent[0]["result"]["accepted"] is False


def test_vps_accepts_only_exact_full_shell_running_identity(tmp_path):
    server = _durable_mesh_server(tmp_path)
    req = server._durable_store.put_request(_durable_request())
    claim_id = "claim-running-exact"
    server._durable_store.mark_claimed(req.request_id, claim_id=claim_id)
    process_tree = {
        "launch_state": SHELL_LAUNCH_RUNNING,
        "launch_intent_id": "launch-exact",
        "root_pid": 4242,
        "process_identity": {
            "pid": 4242,
            "start_token": "start-exact",
            "executable": "powershell.exe",
            "observed_command_digest": "f" * 64,
            "command_digest": req.payload_digest,
            "identity_source": "psutil_process_identity",
        },
        "execution_identity": durable_execution_identity(req, claim_id=claim_id),
    }
    ws = _MeshHandlerWs()

    asyncio.run(
        server._handle_durable_claimed(
            req.node_id,
            {
                "request_id": req.request_id,
                "claim_id": claim_id,
                "state": "RUNNING",
                "process_tree": process_tree,
            },
            "msg-exact-running",
            ws,
        )
    )

    current = server._durable_store.get_request(req.request_id)
    assert current is not None
    assert current.lifecycle_state == "RUNNING"
    assert current.process_tree["execution_identity"] == process_tree["execution_identity"]
    assert ws.sent[0]["result"]["accepted"] is True


def test_governed_sol_attestation_is_exact_attempt_bound_and_mandatory(tmp_path, monkeypatch):
    executable = tmp_path / "codex"
    executable.write_bytes(b"approved-codex")
    executable.chmod(0o755)
    executable_hash = _file_sha256(str(executable))
    monkeypatch.setenv(
        "UMH_CODEX_APPROVED_EXECUTABLES_JSON",
        client_mod.json.dumps({str(executable.resolve()): executable_hash}),
    )
    attempt = SimpleNamespace(attempt_id="ea-sol-1")
    raw = {
        "package_hash": "pkg-1",
        "required_model_attestation": {"provider": "codex", "model": "gpt-5.6-sol"},
    }
    evidence = {
        "provider_requested": "codex",
        "model_requested": "gpt-5.6-sol",
        "trusted_model_resolved": "gpt-5.6-sol",
        "trusted_model_resolution_source": "turn.completed.model",
        "attempt_id": "ea-sol-1",
        "package_hash": "pkg-1",
        "explicit_model_argument_present": True,
        "user_config_ignored": True,
        "invocation_accepted": True,
        "model_resolution_observable": True,
        "output_content_present": True,
        "usage_present": True,
        "credential_isolation_verified": True,
        "workspace_integrity_verified": True,
        **_codex_executable_attestation(
            str(executable.resolve()), version="codex-cli 0.test"
        ),
    }
    result = _WorkerResultView(
        {
            "ok": True,
            "status": "succeeded",
            "executor": {"provider": "codex", "model": "gpt-5.6-sol"},
            "execution_identity": evidence,
        }
    )
    assert ControlPlanePoller._worker_result_gate_error(attempt, result, raw) == ""
    for mutation in (
        {"trusted_model_resolved": ""},
        {"trusted_model_resolved": "gpt-5.5"},
        {"attempt_id": "ea-other"},
        {"package_hash": "pkg-other"},
        {"model_resolution_observable": False},
        {"trusted_model_resolution_source": "totally-trusted-bro"},
        {"codex_executable_approved": False},
        {"codex_executable_sha256": ""},
        {"codex_executable_path": str(tmp_path / "copied-codex")},
        {"codex_executable_policy_identity": "c" * 64},
    ):
        rejected = _WorkerResultView(
            {
                "ok": True,
                "status": "succeeded",
                "executor": {"provider": "codex", "model": "gpt-5.6-sol"},
                "execution_identity": {**evidence, **mutation},
            }
        )
        assert ControlPlanePoller._worker_result_gate_error(attempt, rejected, raw)


def test_governed_worker_rejects_ambient_codex_model_substitution(tmp_path, monkeypatch):
    worktree = tmp_path / "worktree"
    worktree.mkdir()
    monkeypatch.setenv("UMH_CODEX_MODEL", "gpt-5.5")
    result = run_worker_in_lease(
        package=SimpleNamespace(),
        lease=SimpleNamespace(worktree_path=str(worktree), snapshot_ref="abc123"),
        attempt_id="ea-ambient-model",
        run_root=str(tmp_path / "run"),
        provider="codex",
    )
    assert result.ok is False
    assert "require exact model 'gpt-5.6-sol'" in result.error
