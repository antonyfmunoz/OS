from __future__ import annotations

from substrate.execution.durable_remote_transport import DurableRemoteStore
from tests.wave2_script_import import load_wave2_script


def test_mesh_read_submits_durable_request_with_signed_shell_shape(monkeypatch) -> None:
    dispatch = load_wave2_script("wave2_field_dispatch")
    calls: list[dict[str, object]] = []

    def fake_durable(command: str, **kwargs: object) -> dict[str, object]:
        calls.append({"command": command, **kwargs})
        return {"ok": True, "stdout": "ok", "stderr": "", "error": ""}

    monkeypatch.setattr(dispatch, "_durable_remote_shell", fake_durable)

    out = dispatch._mesh_read(
        dispatch.Runner(dry_run=False),
        "hostname",
        max_len=99,
        command_timeout=12,
        dispatch_timeout=34,
    )

    assert out["ok"] is True
    assert calls == [
        {
            "command": "hostname",
            "max_len": 99,
            "command_timeout": 12,
            "dispatch_timeout": 34,
            "operation_type": "wave2_read",
        }
    ]


def test_fast_read_uses_durable_request_not_synchronous_mesh(monkeypatch) -> None:
    dispatch = load_wave2_script("wave2_field_dispatch")
    calls: list[dict[str, object]] = []

    monkeypatch.setattr(
        dispatch,
        "_durable_remote_shell",
        lambda command, **kwargs: calls.append({"command": command, **kwargs})
        or {"ok": True, "stdout": "{}"},
    )

    out = dispatch._mesh_read_fast(dispatch.Runner(dry_run=False), "echo {}", max_len=1000)

    assert out["ok"] is True
    assert calls[0]["operation_type"] == "wave2_fast_read"
    assert calls[0]["command_timeout"] == 10
    assert calls[0]["dispatch_timeout"] == 15


def test_collector_launch_uses_run_bound_durable_transport(monkeypatch) -> None:
    dispatch = load_wave2_script("wave2_field_dispatch")
    calls: list[dict[str, object]] = []

    monkeypatch.setattr(
        dispatch,
        "_build_start_command",
        lambda **kwargs: "start collector for {run_id}".format(**kwargs),
    )
    monkeypatch.setattr(
        dispatch,
        "_durable_remote_shell",
        lambda command, **kwargs: calls.append({"command": command, **kwargs})
        or {"ok": True, "stdout": "started"},
    )

    out = dispatch._dispatch_collector(
        dispatch.Runner(dry_run=False),
        run_id="20260819T000000Z",
        pass_num=1,
        scenario="tools-revoked-a",
        sha="257f4104a086bad0292f721cfbb9815ed6abdc1d",
    )

    assert out == {"ok": True, "run_id": "20260819T000000Z", "pass_num": 1}
    assert calls == [
        {
            "command": "start collector for 20260819T000000Z",
            "max_len": 32768,
            "command_timeout": 60,
            "dispatch_timeout": 90,
            "operation_type": "wave2_collector_launch",
            "correlation_id": "w2-20260819T000000Z-p1",
            "candidate_sha": "257f4104a086bad0292f721cfbb9815ed6abdc1d",
        }
    ]


def test_dispatcher_no_longer_imports_mesh_dispatch_port_for_remote_reads() -> None:
    dispatch = load_wave2_script("wave2_field_dispatch")

    assert dispatch._mesh_read.__code__.co_names.count("_durable_remote_shell") == 1
    assert "mesh_dispatch" not in dispatch._mesh_read.__code__.co_names
    assert dispatch._mesh_read_fast.__code__.co_names.count("_durable_remote_shell") == 1


def test_durable_remote_shell_timeout_waits_for_cancel_terminalization(
    monkeypatch, tmp_path
) -> None:
    dispatch = load_wave2_script("wave2_field_dispatch")
    store = DurableRemoteStore(tmp_path)

    monkeypatch.setenv("UMH_DURABLE_REMOTE_ROOT", str(tmp_path))
    monkeypatch.setattr(dispatch, "_ensure_mesh_secrets", lambda: None)
    monkeypatch.setattr(dispatch, "_candidate_sha", lambda _default: "sha")
    monkeypatch.setattr(dispatch, "_MESH_NODE_ID", "windows-desktop")
    monkeypatch.setattr(dispatch, "uuid4", lambda: type("U", (), {"hex": "v" * 32})())

    import substrate.execution.mesh_verdict as mesh_verdict

    monkeypatch.setattr(mesh_verdict, "get_verdict_secret", lambda: "present")
    monkeypatch.setattr(mesh_verdict, "sign_verdict", lambda **_kwargs: "signed")
    monkeypatch.setattr(dispatch.time, "sleep", lambda _seconds: None)
    ticks = iter([100.0] * 20 + [101.0] * 20)
    monkeypatch.setattr(dispatch.time, "time", lambda: next(ticks))

    original_request_cancel = store.request_cancel

    def cancelling(request_id: str):
        req = original_request_cancel(request_id)
        store.mark_claimed(request_id, claim_id="node-claim")
        return store.publish_result(
            request_id,
            claim_id="node-claim",
            state="CANCELLED",
            result={"success": False, "error": "cancel requested by controller"},
            cleanup={"process_residue": []},
        )

    monkeypatch.setattr(dispatch, "DurableRemoteStore", lambda: store, raising=False)

    # Patch the imported class lookup by replacing it on the module after import.
    import substrate.execution.durable_remote_transport as durable

    monkeypatch.setattr(durable, "DurableRemoteStore", lambda: store)
    monkeypatch.setattr(store, "request_cancel", cancelling)

    out = dispatch._durable_remote_shell(
        "hostname",
        command_timeout=1,
        dispatch_timeout=0,
        operation_type="unit",
        correlation_id="corr",
        candidate_sha="sha",
    )

    assert out["ok"] is False
    assert out["raw_status"] == "CANCELLED"


def test_durable_remote_shell_reconciles_observed_reconciliation_required(
    monkeypatch, tmp_path
) -> None:
    dispatch = load_wave2_script("wave2_field_dispatch")
    store = DurableRemoteStore(tmp_path)

    monkeypatch.setenv("UMH_DURABLE_REMOTE_ROOT", str(tmp_path))
    monkeypatch.setattr(dispatch, "_ensure_mesh_secrets", lambda: None)
    monkeypatch.setattr(dispatch, "_candidate_sha", lambda _default: "sha")
    monkeypatch.setattr(dispatch, "_MESH_NODE_ID", "windows-desktop")

    import substrate.execution.mesh_verdict as mesh_verdict
    import substrate.execution.durable_remote_transport as durable

    monkeypatch.setattr(mesh_verdict, "get_verdict_secret", lambda: "present")
    monkeypatch.setattr(mesh_verdict, "sign_verdict", lambda **_kwargs: "signed")
    monkeypatch.setattr(durable, "DurableRemoteStore", lambda: store)
    monkeypatch.setattr(dispatch.time, "sleep", lambda _seconds: None)
    ticks = iter([100.0] * 20 + [100.1] * 20)
    monkeypatch.setattr(dispatch.time, "time", lambda: next(ticks))

    original_put = store.put_request

    def put_and_conflict(req):
        out = original_put(req)
        store.mark_claimed(req.request_id, claim_id="claim-1")
        store.publish_result(
            req.request_id,
            claim_id="foreign",
            state="SUCCEEDED",
            result={"success": True},
        )
        return out

    monkeypatch.setattr(store, "put_request", put_and_conflict)

    out = dispatch._durable_remote_shell(
        "hostname",
        command_timeout=1,
        dispatch_timeout=5,
        operation_type="unit",
        correlation_id="corr",
        candidate_sha="sha",
    )

    assert out["ok"] is False
    assert out["raw_status"] == "FAILED"
    assert "reconciliation failed closed" in out["error"]
    assert store.get_request(out["request_id"]) is not None


def test_durable_remote_shell_does_not_immediately_reconcile_process_residue(
    monkeypatch, tmp_path
) -> None:
    dispatch = load_wave2_script("wave2_field_dispatch")
    store = DurableRemoteStore(tmp_path)

    monkeypatch.setenv("UMH_DURABLE_REMOTE_ROOT", str(tmp_path))
    monkeypatch.setattr(dispatch, "_ensure_mesh_secrets", lambda: None)
    monkeypatch.setattr(dispatch, "_candidate_sha", lambda _default: "sha")
    monkeypatch.setattr(dispatch, "_MESH_NODE_ID", "windows-desktop")

    import substrate.execution.mesh_verdict as mesh_verdict
    import substrate.execution.durable_remote_transport as durable

    monkeypatch.setattr(mesh_verdict, "get_verdict_secret", lambda: "present")
    monkeypatch.setattr(mesh_verdict, "sign_verdict", lambda **_kwargs: "signed")
    monkeypatch.setattr(durable, "DurableRemoteStore", lambda: store)
    monkeypatch.setattr(dispatch.time, "sleep", lambda _seconds: None)
    ticks = iter([100.0] * 100 + [111.0] * 100)
    monkeypatch.setattr(dispatch.time, "time", lambda: next(ticks))

    original_put = store.put_request

    def put_and_report_residue(req):
        out = original_put(req)
        store.mark_claimed(req.request_id, claim_id="claim-1")
        store.request_cancel(req.request_id)
        store.publish_result(
            req.request_id,
            claim_id="claim-1",
            state="CANCELLED",
            result={"success": False, "error": "cancelled"},
            cleanup={"process_residue": [{"pid": 123, "state": "still_alive"}]},
        )
        return out

    def forbidden_reconcile(*_args, **_kwargs):
        raise AssertionError("residue-bearing recovery must not reconcile immediately")

    monkeypatch.setattr(store, "put_request", put_and_report_residue)
    monkeypatch.setattr(store, "reconcile_request", forbidden_reconcile)

    out = dispatch._durable_remote_shell(
        "hostname",
        command_timeout=1,
        dispatch_timeout=0,
        operation_type="unit",
        correlation_id="corr",
        candidate_sha="sha",
    )

    assert out["ok"] is False
    assert out["raw_status"] == "RECONCILIATION_REQUIRED"
    assert "process residue" in out["error"]
    assert store.get_request(out["request_id"]) is not None
