from __future__ import annotations

import asyncio
from dataclasses import replace
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
    sha256_json,
    suspend_state_evidence_rejection_reason,
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
    execution_identity = durable_execution_identity(req, claim_id=claim_id)
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


def _persist_exact_windows_launch(client, req, claim_id: str):
    material = _persist_launch(client, req, claim_id, attempted=True)
    process_identity = {
        "pid": 4242,
        "start_token": "start-4242",
        "parent_pid": 111,
        "executable": r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe",
        "observed_command_digest": "d" * 64,
        "command_digest": req.payload_digest,
        "identity_source": "psutil_process_identity",
        "logical_execution_id": material["execution_identity"]["logical_execution_id"],
        "launch_intent_id": material["launch_intent_id"],
    }
    process_tree = {
        **material,
        "root_pid": 4242,
        "process_identity": process_identity,
        "process_containment": {
            "kind": "windows_job_object",
            "containment_id": material["launch_intent_id"],
            "complete_tree_boundary": True,
        },
    }
    current = client._durable_store.mark_shell_launch_state(
        req.request_id,
        claim_id=claim_id,
        launch_state=SHELL_PROCESS_IDENTITY_PERSISTED,
        launch_material=process_tree,
    )
    assert current.lifecycle_state == "CLAIMED"
    current = client._durable_store.persist_shell_launch_thread_identity(
        req.request_id,
        claim_id=claim_id,
        thread_id=77,
    )
    assert current.lifecycle_state == "CLAIMED"
    return current.process_tree, process_identity, material["execution_identity"]


def _exact_suspend_evidence(req, claim_id: str, process_tree: dict) -> dict:
    execution = process_tree["execution_identity"]
    process = process_tree["process_identity"]
    return client_mod._SuspendStateEvidence(
        state=client_mod._SUSPEND_STATE_PROVEN_RESUMED,
        request_id=req.request_id,
        correlation_id=req.correlation_id,
        node_id=req.node_id,
        candidate_sha=req.candidate_sha,
        claim_id=claim_id,
        logical_execution_id=execution["logical_execution_id"],
        launch_intent_id=process_tree["launch_intent_id"],
        process_id=process_tree["root_pid"],
        process_start_token=process["start_token"],
        process_executable=process["executable"],
        process_observed_command_digest=process["observed_command_digest"],
        command_digest=process["command_digest"],
        process_identity_source=process["identity_source"],
        thread_id=process_tree["launch_thread_identity"]["thread_id"],
        observation_method="RESUME_THREAD_RETURN",
        observation_success=True,
        win32_error=None,
        observed_at=100.0,
        previous_suspend_count=1,
        resume_result=client_mod._RESUME_RESULT_EXPECTED,
    ).to_dict()


def _resign_suspend_evidence(evidence: dict, **changes) -> dict:
    updated = {**evidence, **changes}
    updated.pop("observation_id", None)
    updated["observation_id"] = sha256_json(updated)
    return updated


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


def test_empty_residue_without_complete_positive_cleanup_proof_reconciles(tmp_path):
    server = _durable_mesh_server(tmp_path)
    req = server._durable_store.put_request(_durable_request())
    server._durable_store.mark_claimed(req.request_id, claim_id="claim-cleanup")
    server._durable_store.mark_running(
        req.request_id,
        claim_id="claim-cleanup",
        process_tree={"root_pid": 123},
    )

    current = server._durable_store.publish_result(
        req.request_id,
        claim_id="claim-cleanup",
        state="FAILED",
        result={"success": False},
        cleanup={"cleanup_verified": False, "process_residue": []},
    )

    assert current.lifecycle_state == "RECONCILIATION_REQUIRED"
    assert server._durable_store.result_for(req.request_id) is None


@pytest.mark.parametrize("terminal_state", ["FAILED", "CANCELLED"])
def test_unknown_suspend_evidence_cannot_terminalize(tmp_path, terminal_state):
    server = _durable_mesh_server(tmp_path)
    req = server._durable_store.put_request(_durable_request())
    claim_id = "claim-unknown-suspend"
    server._durable_store.mark_claimed(req.request_id, claim_id=claim_id)
    server._durable_store.mark_running(
        req.request_id,
        claim_id=claim_id,
        process_tree={
            "root_pid": 123,
            "suspend_state_evidence": {
                "state": client_mod._SUSPEND_STATE_UNKNOWN,
                "observation_success": False,
                "launch_intent_id": "launch-123",
                "logical_execution_id": "execution-123",
            },
        },
    )

    current = server._durable_store.publish_result(
        req.request_id,
        claim_id=claim_id,
        state=terminal_state,
        result={"success": False, "error": "resume state unknown"},
        cleanup={
            "cleanup_verified": True,
            "enumeration_performed": True,
            "enumeration_complete": True,
            "ownership_validated": True,
            "post_termination_enumeration_complete": True,
            "residue_count": 0,
            "process_residue": [],
        },
    )

    assert current.lifecycle_state == "RECONCILIATION_REQUIRED"
    assert server._durable_store.result_for(req.request_id) is None


def _resume_test_job(*, resume_result=1, snapshot=1, open_thread=2, win32_error=5):
    class _Ctypes:
        @staticmethod
        def c_void_p(value):
            return SimpleNamespace(value=value)

        @staticmethod
        def byref(value):
            return SimpleNamespace(_obj=value)

        @staticmethod
        def sizeof(_value):
            return 1

        @staticmethod
        def get_last_error():
            return win32_error

    class _Kernel:
        def CreateToolhelp32Snapshot(self, *_args):
            return snapshot

        def Thread32First(self, _snapshot, entry_ref):
            entry = entry_ref._obj
            entry.th32OwnerProcessID = 42
            entry.th32ThreadID = 7
            return 1

        def Thread32Next(self, *_args):
            return 0

        def OpenThread(self, *_args):
            return open_thread

        def ResumeThread(self, _thread):
            return resume_result

        def CloseHandle(self, _handle):
            return 1

    job = object.__new__(client_mod._WindowsDurableJob)
    job._kernel32 = _Kernel()
    job._ctypes = _Ctypes()

    class _Entry:
        dwSize = 0
        th32OwnerProcessID = 0
        th32ThreadID = 0

    job._ThreadEntry = _Entry
    return job


def _resume(job, proc=None):
    execution_identity = {
        "request_id": "drc-test",
        "correlation_id": "corr-test",
        "node_id": "windows-desktop",
        "candidate_sha": "a" * 40,
        "claim_id": "claim-test",
        "logical_execution_id": "execution-42",
    }
    process_identity = {
        "pid": 42,
        "start_token": "start-42",
        "executable": "powershell.exe",
        "observed_command_digest": "b" * 64,
        "command_digest": "c" * 64,
        "identity_source": "psutil_process_identity",
    }
    return job.resume_suspended_process(
        proc or SimpleNamespace(pid=42),
        launch_intent_id="launch-42",
        execution_identity=execution_identity,
        process_identity=process_identity,
        persist_thread_identity=lambda _thread_id: None,
    )


def test_resume_thread_expected_one_is_the_only_normal_result():
    evidence = _resume(_resume_test_job(resume_result=1))

    assert evidence.state == client_mod._SUSPEND_STATE_PROVEN_RESUMED
    assert evidence.resume_result == client_mod._RESUME_RESULT_EXPECTED
    assert evidence.previous_suspend_count == 1
    assert evidence.observation_success is True
    assert evidence.launch_intent_id == "launch-42"
    assert evidence.logical_execution_id == "execution-42"


def test_resume_thread_zero_is_unexpected_and_requires_independent_observation():
    with pytest.raises(client_mod._DurableResumeStateUncertain) as caught:
        _resume(_resume_test_job(resume_result=0))

    evidence = caught.value.evidence
    assert evidence.state == client_mod._SUSPEND_STATE_UNKNOWN
    assert evidence.resume_result == client_mod._RESUME_RESULT_UNEXPECTED
    assert evidence.previous_suspend_count == 0
    assert evidence.observation_success is False

    observed = client_mod._durable_observe_process_after_unexpected_resume(
        SimpleNamespace(pid=42, poll=lambda: None),
        evidence=evidence,
    )
    assert observed.state == client_mod._SUSPEND_STATE_PROVEN_RESUMED
    assert observed.observation_method == "PROCESS_STATE_QUERY"
    assert observed.predecessor_observation_id == evidence.observation_id
    assert observed.resume_result == client_mod._RESUME_RESULT_NOT_ATTEMPTED


def test_resume_thread_zero_with_unknown_process_observation_reconciles():
    with pytest.raises(client_mod._DurableResumeStateUncertain) as caught:
        _resume(_resume_test_job(resume_result=0))

    observed = client_mod._durable_observe_process_after_unexpected_resume(
        SimpleNamespace(pid=42, poll=lambda: (_ for _ in ()).throw(OSError("unknown"))),
        evidence=caught.value.evidence,
    )
    assert observed.state == client_mod._SUSPEND_STATE_UNKNOWN
    assert observed.observation_success is False


def test_unexpected_resume_with_exited_process_recovers_actual_exit_state():
    with pytest.raises(client_mod._DurableResumeStateUncertain) as caught:
        _resume(_resume_test_job(resume_result=0))

    observed = client_mod._durable_observe_process_after_unexpected_resume(
        SimpleNamespace(pid=42, poll=lambda: 7),
        evidence=caught.value.evidence,
    )
    assert observed.state == client_mod._SUSPEND_STATE_PROVEN_EXITED
    assert observed.observation_success is True


def test_multiple_suspend_count_is_positive_suspended_proof_without_retry():
    calls = 0

    class _Proc:
        pid = 42

        def poll(self):
            nonlocal calls
            calls += 1
            return None

    with pytest.raises(client_mod._DurableResumeStateUncertain) as caught:
        _resume(_resume_test_job(resume_result=2), _Proc())
    observed = client_mod._durable_observe_process_after_unexpected_resume(
        _Proc(), evidence=caught.value.evidence
    )
    assert observed.state == client_mod._SUSPEND_STATE_PROVEN_SUSPENDED
    assert observed.observation_success is True
    assert calls == 0

def test_resume_thread_rejects_multiple_suspend_count():
    with pytest.raises(client_mod._DurableResumeStateUncertain) as caught:
        _resume(_resume_test_job(resume_result=2))
    assert caught.value.evidence.previous_suspend_count == 2
    assert caught.value.evidence.state == client_mod._SUSPEND_STATE_PROVEN_SUSPENDED
    assert caught.value.evidence.observation_success is True


def test_resume_thread_failure_sentinel_preserves_ambiguous_launch_truth():
    with pytest.raises(client_mod._DurableResumeStateUncertain) as caught:
        _resume(_resume_test_job(resume_result=0xFFFFFFFF))
    assert caught.value.evidence.previous_suspend_count is None
    assert caught.value.evidence.state == client_mod._SUSPEND_STATE_UNKNOWN
    assert caught.value.evidence.resume_result == client_mod._RESUME_RESULT_FAILURE
    assert caught.value.evidence.observation_success is False


@pytest.mark.parametrize(
    ("snapshot", "open_thread", "method"),
    ((0, 2, "CREATE_TOOLHELP32_SNAPSHOT"), (1, 0, "OPEN_THREAD")),
)
def test_failed_windows_observation_is_unknown(snapshot, open_thread, method):
    with pytest.raises(client_mod._DurableResumeStateUncertain) as caught:
        _resume(_resume_test_job(snapshot=snapshot, open_thread=open_thread))
    evidence = caught.value.evidence
    assert evidence.state == client_mod._SUSPEND_STATE_UNKNOWN
    assert evidence.observation_success is False
    assert evidence.observation_method == method


def test_failed_observation_cannot_construct_positive_suspend_evidence():
    with pytest.raises(ValueError, match="failed observation"):
        client_mod._SuspendStateEvidence(
            state=client_mod._SUSPEND_STATE_PROVEN_SUSPENDED,
            request_id="drc-test",
            correlation_id="corr-test",
            node_id="windows-desktop",
            candidate_sha="a" * 40,
            claim_id="claim-test",
            logical_execution_id="execution-42",
            launch_intent_id="launch-42",
            process_id=42,
            process_start_token="start-42",
            process_executable="powershell.exe",
            process_observed_command_digest="b" * 64,
            command_digest="c" * 64,
            process_identity_source="psutil_process_identity",
            thread_id=7,
            observation_method="OPEN_THREAD",
            observation_success=False,
            win32_error=5,
            observed_at=1.0,
        )


def test_typed_suspend_evidence_rejects_unknown_observation_method():
    evidence = _resume(_resume_test_job(resume_result=1))

    with pytest.raises(ValueError, match="invalid suspend observation method"):
        replace(evidence, observation_method="UNTRUSTED_OBSERVER")


def test_typed_suspend_evidence_requires_thread_for_positive_thread_state():
    evidence = _resume(_resume_test_job(resume_result=1))

    with pytest.raises(ValueError, match="positive thread-state evidence"):
        replace(evidence, thread_id=None)


@pytest.mark.parametrize(
    ("case", "changes", "reason_fragment"),
    (
        ("N1", {"request_id": "drc-foreign"}, "request_id_mismatch"),
        ("N2", {"correlation_id": "corr-foreign"}, "correlation_id_mismatch"),
        ("N3", {"node_id": "foreign-node"}, "node_id_mismatch"),
        ("N4", {"candidate_sha": "f" * 40}, "candidate_sha_mismatch"),
        ("N5", {"claim_id": "claim-foreign"}, "claim_id_mismatch"),
        ("N6", {"logical_execution_id": "execution-foreign"}, "logical_execution_id"),
        ("N7", {"launch_intent_id": "launch-foreign"}, "launch_intent_id_mismatch"),
        ("N8", {"process_start_token": "start-reused"}, "process_start_token_mismatch"),
        ("N9", {"process_executable": "foreign.exe"}, "process_executable_mismatch"),
        ("N10", {"command_digest": "a" * 64}, "command_digest_mismatch"),
        ("N11", {"thread_id": None}, "missing_thread_id"),
        ("N12", {"thread_id": 88}, "thread_id_mismatch"),
        (
            "N13",
            {"observation_success": False, "state": "PROVEN_SUSPENDED"},
            "positive_state_without_success",
        ),
        (
            "N14",
            {"observation_success": False, "state": "PROVEN_RESUMED"},
            "positive_state_without_success",
        ),
        (
            "N15",
            {"previous_suspend_count": 0, "resume_result": "EXPECTED"},
            "incoherent_expected_resume",
        ),
        (
            "N16",
            {"previous_suspend_count": 2, "resume_result": "UNEXPECTED"},
            "resume_multiple_misclassified",
        ),
        (
            "N17",
            {"previous_suspend_count": None, "resume_result": "FAILURE"},
            "incoherent_resume_failure",
        ),
        ("N18", {"launch_intent_id": "previous-launch"}, "launch_intent_id_mismatch"),
        (
            "N19",
            {"logical_execution_id": "previous-execution"},
            "logical_execution_id_mismatch",
        ),
    ),
)
def test_suspend_evidence_negative_identity_and_coherence_matrix(
    tmp_path,
    case,
    changes,
    reason_fragment,
):
    client = _durable_node_client(tmp_path)
    req = client._durable_store.put_request(_durable_request())
    claim_id = "claim-evidence-matrix"
    client._durable_store.mark_claimed(req.request_id, claim_id=claim_id)
    process_tree, _, _ = _persist_exact_windows_launch(client, req, claim_id)
    evidence = _resign_suspend_evidence(
        _exact_suspend_evidence(req, claim_id, process_tree),
        **changes,
    )

    reason = suspend_state_evidence_rejection_reason(
        req,
        claim_id=claim_id,
        process_tree=process_tree,
        evidence=evidence,
    )

    assert reason_fragment in reason, case


def test_exact_suspend_evidence_is_accepted_and_persisted_immutably(tmp_path):
    client = _durable_node_client(tmp_path)
    req = client._durable_store.put_request(_durable_request())
    claim_id = "claim-evidence-exact"
    client._durable_store.mark_claimed(req.request_id, claim_id=claim_id)
    process_tree, _, _ = _persist_exact_windows_launch(client, req, claim_id)
    evidence = _exact_suspend_evidence(req, claim_id, process_tree)

    assert not suspend_state_evidence_rejection_reason(
        req,
        claim_id=claim_id,
        process_tree=process_tree,
        evidence=evidence,
    )
    current = client._durable_store.record_shell_suspend_observation(
        req.request_id,
        claim_id=claim_id,
        evidence=evidence,
    )

    assert current.lifecycle_state == "CLAIMED"
    assert current.process_tree["suspend_state_evidence"] == evidence
    assert current.process_tree["suspend_state_evidence_history"] == [evidence]


def test_unknown_observation_refines_without_mutating_raw_resume_evidence(tmp_path):
    client = _durable_node_client(tmp_path)
    req = client._durable_store.put_request(_durable_request())
    claim_id = "claim-evidence-refine"
    client._durable_store.mark_claimed(req.request_id, claim_id=claim_id)
    process_tree, process_identity, execution_identity = _persist_exact_windows_launch(
        client, req, claim_id
    )
    raw = client_mod._SuspendStateEvidence(
        state=client_mod._SUSPEND_STATE_UNKNOWN,
        request_id=req.request_id,
        correlation_id=req.correlation_id,
        node_id=req.node_id,
        candidate_sha=req.candidate_sha,
        claim_id=claim_id,
        logical_execution_id=execution_identity["logical_execution_id"],
        launch_intent_id=process_tree["launch_intent_id"],
        process_id=4242,
        process_start_token=process_identity["start_token"],
        process_executable=process_identity["executable"],
        process_observed_command_digest=process_identity["observed_command_digest"],
        command_digest=process_identity["command_digest"],
        process_identity_source=process_identity["identity_source"],
        thread_id=77,
        observation_method="RESUME_THREAD_RETURN",
        observation_success=False,
        win32_error=None,
        observed_at=101.0,
        previous_suspend_count=0,
        resume_result=client_mod._RESUME_RESULT_UNEXPECTED,
    )
    client._durable_store.record_shell_suspend_observation(
        req.request_id,
        claim_id=claim_id,
        evidence=raw.to_dict(),
    )
    followup = client_mod._durable_observe_process_after_unexpected_resume(
        SimpleNamespace(pid=4242, poll=lambda: None),
        evidence=raw,
    )
    current = client._durable_store.record_shell_suspend_observation(
        req.request_id,
        claim_id=claim_id,
        evidence=followup.to_dict(),
    )

    history = current.process_tree["suspend_state_evidence_history"]
    assert [item["state"] for item in history] == ["UNKNOWN", "PROVEN_RESUMED"]
    assert history[0]["observation_id"] == raw.observation_id
    assert history[1]["predecessor_observation_id"] == raw.observation_id
    assert current.process_tree["suspend_state_evidence"] == followup.to_dict()


def test_contradictory_exact_suspend_observation_enters_reconciliation(tmp_path):
    client = _durable_node_client(tmp_path)
    req = client._durable_store.put_request(_durable_request())
    claim_id = "claim-evidence-conflict"
    client._durable_store.mark_claimed(req.request_id, claim_id=claim_id)
    process_tree, _, _ = _persist_exact_windows_launch(client, req, claim_id)
    resumed = _exact_suspend_evidence(req, claim_id, process_tree)
    client._durable_store.record_shell_suspend_observation(
        req.request_id,
        claim_id=claim_id,
        evidence=resumed,
    )
    suspended = _resign_suspend_evidence(
        resumed,
        state="PROVEN_SUSPENDED",
        previous_suspend_count=2,
        resume_result="UNEXPECTED",
        observed_at=102.0,
    )

    current = client._durable_store.record_shell_suspend_observation(
        req.request_id,
        claim_id=claim_id,
        evidence=suspended,
    )

    assert current.lifecycle_state == "RECONCILIATION_REQUIRED"
    assert current.process_tree["suspend_state_evidence"] == resumed
    assert current.process_tree["suspend_state_evidence_history"] == [resumed, suspended]
    conflict = current.diagnostics["suspend_state_evidence_conflicts"][-1]
    assert conflict["evidence"] == suspended


def test_terminalization_rejects_re_signed_foreign_suspend_evidence(tmp_path):
    server = _durable_mesh_server(tmp_path)
    req = server._durable_store.put_request(_durable_request())
    claim_id = "claim-terminal-evidence"
    server._durable_store.mark_claimed(req.request_id, claim_id=claim_id)
    process_tree, _, _ = _persist_exact_windows_launch(server, req, claim_id)
    evidence = _exact_suspend_evidence(req, claim_id, process_tree)
    server._durable_store.record_shell_suspend_observation(
        req.request_id,
        claim_id=claim_id,
        evidence=evidence,
    )
    current = server._durable_store.get_request(req.request_id)
    assert current is not None
    server._durable_store.mark_running(
        req.request_id,
        claim_id=claim_id,
        process_tree=current.process_tree,
    )
    foreign = _resign_suspend_evidence(evidence, thread_id=88)

    terminal = server._durable_store.publish_result(
        req.request_id,
        claim_id=claim_id,
        state="FAILED",
        result={"success": False, "error": "test"},
        cleanup={
            "cleanup_verified": True,
            "enumeration_performed": True,
            "enumeration_complete": True,
            "ownership_validated": True,
            "post_termination_enumeration_complete": True,
            "residue_count": 0,
            "process_residue": [],
            "suspend_state_evidence": foreign,
        },
    )

    assert terminal.lifecycle_state == "RECONCILIATION_REQUIRED"
    assert server._durable_store.result_for(req.request_id) is None
    assert "thread_id_mismatch" in terminal.diagnostics[
        "terminal_admissibility_rejected"
    ][-1]["reason"]


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

        def resume_suspended_process(self, _proc, **_identity):
            events.append("resume")
            _identity["persist_thread_identity"](7)
            execution_identity = _identity["execution_identity"]
            process_identity = _identity["process_identity"]
            return client_mod._SuspendStateEvidence(
                state=client_mod._SUSPEND_STATE_PROVEN_RESUMED,
                request_id=execution_identity["request_id"],
                correlation_id=execution_identity["correlation_id"],
                node_id=execution_identity["node_id"],
                candidate_sha=execution_identity["candidate_sha"],
                claim_id=execution_identity["claim_id"],
                logical_execution_id=execution_identity["logical_execution_id"],
                launch_intent_id=_identity["launch_intent_id"],
                process_id=4242,
                process_start_token=process_identity["start_token"],
                process_executable=process_identity["executable"],
                process_observed_command_digest=process_identity[
                    "observed_command_digest"
                ],
                command_digest=process_identity["command_digest"],
                process_identity_source=process_identity["identity_source"],
                thread_id=7,
                observation_method="RESUME_THREAD_RETURN",
                observation_success=True,
                win32_error=None,
                observed_at=1.0,
                previous_suspend_count=1,
                resume_result=client_mod._RESUME_RESULT_EXPECTED,
            )

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
            "observed_command_digest": "d" * 64,
            "command_digest": req.payload_digest,
            "identity_source": "psutil_process_identity",
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


def test_ambiguous_resume_from_shell_executor_fences_duplicate_resume_and_launch(
    tmp_path, monkeypatch
):
    client = _durable_node_client(tmp_path)
    req = _durable_request()
    client._durable_store.put_request(req)
    client._durable_store.mark_claimed(req.request_id, claim_id="claim-resume-ambiguous")

    class _Proc:
        pid = 4343
        returncode = None

        def poll(self):
            return None

    class _Containment:
        containment_id = "launch-ambiguous"

        def pids(self):
            return [4343]

        def resume_suspended_process(self, _proc, **_identity):
            _identity["persist_thread_identity"](7)
            execution_identity = _identity["execution_identity"]
            process_identity = _identity["process_identity"]
            raise client_mod._DurableResumeStateUncertain(
                "ambiguous ResumeThread API failure",
                evidence=client_mod._SuspendStateEvidence(
                    state=client_mod._SUSPEND_STATE_UNKNOWN,
                    request_id=execution_identity["request_id"],
                    correlation_id=execution_identity["correlation_id"],
                    node_id=execution_identity["node_id"],
                    candidate_sha=execution_identity["candidate_sha"],
                    claim_id=execution_identity["claim_id"],
                    logical_execution_id=execution_identity["logical_execution_id"],
                    launch_intent_id=_identity["launch_intent_id"],
                    process_id=4343,
                    process_start_token=process_identity["start_token"],
                    process_executable=process_identity["executable"],
                    process_observed_command_digest=process_identity[
                        "observed_command_digest"
                    ],
                    command_digest=process_identity["command_digest"],
                    process_identity_source=process_identity["identity_source"],
                    thread_id=7,
                    observation_method="RESUME_THREAD_RETURN",
                    observation_success=False,
                    win32_error=5,
                    observed_at=1.0,
                    resume_result=client_mod._RESUME_RESULT_FAILURE,
                ),
            )

        def close(self):
            return None

    class _Collector:
        pass

    monkeypatch.setattr(client_mod.sys, "platform", "win32")
    monkeypatch.setattr(client_mod.subprocess, "CREATE_NO_WINDOW", 0x08000000, raising=False)
    monkeypatch.setattr(client_mod.subprocess, "Popen", lambda *_a, **_k: _Proc())
    monkeypatch.setattr(
        client_mod,
        "_durable_attach_process_containment",
        lambda *_a, **_k: _Containment(),
    )
    monkeypatch.setattr(client_mod, "_DurablePipeCollector", lambda _proc: _Collector())
    monkeypatch.setattr(
        client_mod,
        "_durable_process_identity",
        lambda pid, **_kwargs: {
            "pid": pid,
            "start_token": "start-4343",
            "executable": "powershell.exe",
            "observed_command_digest": "e" * 64,
            "command_digest": req.payload_digest,
            "identity_source": "psutil_process_identity",
        },
    )

    async def _cleanup(*_args, **_kwargs):
        return {
            "enumeration_performed": True,
            "enumeration_complete": True,
            "ownership_validated": True,
            "matched_processes": [],
            "termination_attempted": True,
            "post_termination_enumeration_complete": True,
            "residue_count": 0,
            "cleanup_verified": True,
            "process_residue": [],
        }

    monkeypatch.setattr(client, "_terminate_durable_process_tree", _cleanup)

    result = asyncio.run(
        client._execute_shell_for_durable(
            req,
            cap_name="shell",
            cap_params={"command": "echo never-relaunch"},
            claim_id="claim-resume-ambiguous",
            process_tree={"node_pid": 1},
            timeout=5.0,
        )
    )

    assert result["success"] is False
    assert result["execution_outcome_unresolved"] is True
    assert result["cleanup"]["resume_state_uncertain"] is True
    assert result["cleanup"]["duplicate_resume_fenced"] is True
    assert result["cleanup"]["duplicate_launch_fenced"] is True


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
        "codex_executed_object_sha256": executable_hash,
        "codex_executable_object_identity": "object-identity-1",
        "codex_executable_binding": "bwrap_ro_bind_data_sealed_memfd",
        "codex_governed_launch_path": "/tmp/umh-codex-approved",
        "post_execution_executable_sha256": executable_hash,
        "post_execution_executable_binding_verified": True,
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
