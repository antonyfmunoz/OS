from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

from nodes.windows.umh_node import client as client_mod
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
            "command_digest": req.payload_digest,
            "identity_source": "windows_process_times",
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


def test_governed_sol_attestation_is_exact_attempt_bound_and_mandatory():
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
