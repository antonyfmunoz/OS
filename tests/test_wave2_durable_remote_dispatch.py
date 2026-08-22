from __future__ import annotations

from itertools import chain, repeat

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


def test_preflight_observation_retries_only_unclaimed_cancellation(monkeypatch) -> None:
    dispatch = load_wave2_script("wave2_field_dispatch")
    runner = dispatch.Runner(dry_run=False)
    calls: list[str] = []
    responses = iter(
        [
            {
                "ok": False,
                "raw_status": "CANCELLED",
                "request_id": "drc-first",
                "error": "durable remote request cancelled before claim",
                "result_digest": "",
            },
            {
                "ok": True,
                "raw_status": "SUCCEEDED",
                "request_id": "drc-second",
                "stdout": "TaskName: UMH Node Daemon",
                "result_digest": "digest",
            },
        ]
    )

    def fake_mesh(_runner, command, **_kwargs):  # noqa: ANN001
        calls.append(command)
        return next(responses)

    monkeypatch.setattr(dispatch, "_mesh_read", fake_mesh)
    monkeypatch.setattr(dispatch.time, "sleep", lambda _seconds: None)

    out = dispatch._preflight_observation_read(runner, "schtasks /query", gate="schtasks_query")

    assert out["ok"] is True
    assert out["request_id"] == "drc-second"
    assert out["logical_gate"] == "schtasks_query"
    assert out["preclaim_retry_attempted"] is True
    assert out["preclaim_retry_exhausted"] is False
    assert [attempt["request_id"] for attempt in out["attempts"]] == ["drc-first", "drc-second"]
    assert calls == ["schtasks /query", "schtasks /query"]


def test_preflight_observation_does_not_retry_claimed_or_ambiguous_failure(monkeypatch) -> None:
    dispatch = load_wave2_script("wave2_field_dispatch")
    runner = dispatch.Runner(dry_run=False)
    calls: list[str] = []

    def fake_mesh(_runner, command, **_kwargs):  # noqa: ANN001
        calls.append(command)
        return {
            "ok": False,
            "raw_status": "FAILED",
            "request_id": "drc-claimed",
            "error": "claimed request failed",
        }

    monkeypatch.setattr(dispatch, "_mesh_read", fake_mesh)

    out = dispatch._preflight_observation_read(runner, "schtasks /query", gate="schtasks_query")

    assert out["ok"] is False
    assert out["request_id"] == "drc-claimed"
    assert "attempts" not in out
    assert calls == ["schtasks /query"]


def test_collector_launch_uses_run_bound_durable_transport(monkeypatch) -> None:
    dispatch = load_wave2_script("wave2_field_dispatch")
    calls: list[dict[str, object]] = []

    dispatch._ORIGIN = "https://candidate.example:10443"
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


def test_collector_launch_resolves_origin_before_durable_dispatch(monkeypatch) -> None:
    dispatch = load_wave2_script("wave2_field_dispatch")
    calls: list[dict[str, object]] = []
    dispatch._ORIGIN = None

    def fake_resolve() -> None:
        dispatch._ORIGIN = "https://candidate.example:10443"

    monkeypatch.setattr(dispatch, "_resolve_env", fake_resolve)
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

    assert out["ok"] is True
    assert "--url https://candidate.example:10443" in calls[0]["command"]
    assert "--url None" not in calls[0]["command"]


def test_collector_launch_refuses_unresolved_origin_without_dispatch(monkeypatch) -> None:
    dispatch = load_wave2_script("wave2_field_dispatch")
    dispatch._ORIGIN = None
    monkeypatch.setattr(dispatch, "_resolve_env", lambda: None)
    monkeypatch.setattr(
        dispatch,
        "_durable_remote_shell",
        lambda *_a, **_kw: (_ for _ in ()).throw(AssertionError("must not dispatch")),
    )

    out = dispatch._dispatch_collector(
        dispatch.Runner(dry_run=False),
        run_id="20260819T000000Z",
        pass_num=1,
        scenario="tools-revoked-a",
        sha="257f4104a086bad0292f721cfbb9815ed6abdc1d",
    )

    assert out["ok"] is False
    assert out["error"] == "collector origin is unresolved"


def test_durable_remote_shell_preserves_argv_payload_shape(monkeypatch, tmp_path) -> None:
    dispatch = load_wave2_script("wave2_field_dispatch")
    store = DurableRemoteStore(tmp_path)

    monkeypatch.setenv("UMH_DURABLE_REMOTE_ROOT", str(tmp_path))
    monkeypatch.setattr(dispatch, "_ensure_mesh_secrets", lambda: None)
    monkeypatch.setattr(dispatch, "_candidate_sha", lambda _default: "sha")
    monkeypatch.setattr(dispatch, "_MESH_NODE_ID", "windows-desktop")
    monkeypatch.setattr(dispatch, "uuid4", lambda: type("U", (), {"hex": "a" * 32})())

    import substrate.execution.durable_remote_transport as durable
    import substrate.execution.mesh_verdict as mesh_verdict

    monkeypatch.setattr(mesh_verdict, "get_verdict_secret", lambda: "present")
    monkeypatch.setattr(mesh_verdict, "sign_verdict", lambda **_kwargs: "signed")
    monkeypatch.setattr(durable, "DurableRemoteStore", lambda: store)
    monkeypatch.setattr(dispatch.time, "sleep", lambda _seconds: None)
    ticks = chain([100.0] * 20, repeat(101.0))
    monkeypatch.setattr(dispatch.time, "time", lambda: next(ticks))

    original_put = store.put_request

    def put_and_succeed(req):
        original_put(req)
        store.mark_claimed(req.request_id, claim_id="claim-1")
        return store.publish_result(
            req.request_id,
            claim_id="claim-1",
            state="SUCCEEDED",
            result={"success": True, "stdout": "ok", "stderr": "", "exit_code": 0},
            cleanup={"process_residue": []},
        )

    monkeypatch.setattr(store, "put_request", put_and_succeed)

    out = dispatch._durable_remote_shell(
        "",
        argv=["python", "script.py", "--payload", "x" * 9000],
        cwd=r"C:\dev\wave2_wt",
        command_timeout=1,
        dispatch_timeout=5,
        operation_type="unit",
        correlation_id="corr",
        candidate_sha="sha",
    )

    req = store.get_request(out["request_id"])
    assert out["ok"] is True
    assert req is not None
    assert req.params["command"] == ""
    assert req.params["argv"] == ["python", "script.py", "--payload", "x" * 9000]
    assert req.params["cwd"] == r"C:\dev\wave2_wt"
    assert req.params["timeout"] == 1


def test_durable_remote_shell_omits_empty_cwd_for_default_shell_requests(
    monkeypatch, tmp_path
) -> None:
    dispatch = load_wave2_script("wave2_field_dispatch")
    store = DurableRemoteStore(tmp_path)

    monkeypatch.setenv("UMH_DURABLE_REMOTE_ROOT", str(tmp_path))
    monkeypatch.setattr(dispatch, "_ensure_mesh_secrets", lambda: None)
    monkeypatch.setattr(dispatch, "_candidate_sha", lambda _default: "sha")
    monkeypatch.setattr(dispatch, "_MESH_NODE_ID", "windows-desktop")
    monkeypatch.setattr(dispatch, "uuid4", lambda: type("U", (), {"hex": "b" * 32})())

    import substrate.execution.durable_remote_transport as durable
    import substrate.execution.mesh_verdict as mesh_verdict

    monkeypatch.setattr(mesh_verdict, "get_verdict_secret", lambda: "present")
    monkeypatch.setattr(mesh_verdict, "sign_verdict", lambda **_kwargs: "signed")
    monkeypatch.setattr(durable, "DurableRemoteStore", lambda: store)
    monkeypatch.setattr(dispatch.time, "sleep", lambda _seconds: None)
    ticks = chain([100.0] * 20, [200.0] * 20, repeat(400.0))
    monkeypatch.setattr(dispatch.time, "time", lambda: next(ticks))

    original_put = store.put_request

    def put_and_succeed(req):
        original_put(req)
        store.mark_claimed(req.request_id, claim_id="claim-1")
        return store.publish_result(
            req.request_id,
            claim_id="claim-1",
            state="SUCCEEDED",
            result={"success": True, "stdout": "ok", "stderr": "", "exit_code": 0},
            cleanup={"process_residue": []},
        )

    monkeypatch.setattr(store, "put_request", put_and_succeed)

    out = dispatch._durable_remote_shell(
        "hostname",
        command_timeout=1,
        dispatch_timeout=5,
        operation_type="unit",
        correlation_id="corr",
        candidate_sha="sha",
    )

    req = store.get_request(out["request_id"])
    assert out["ok"] is True
    assert req is not None
    assert req.params["command"] == "hostname"
    assert req.params["argv"] == []
    assert req.params["cwd"] is None


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
    ticks = chain([100.0] * 20, repeat(200.0))
    monkeypatch.setattr(dispatch.time, "time", lambda: next(ticks))

    original_request_cancel = store.request_cancel

    def cancelling(request_id: str):
        original_request_cancel(request_id)
        store.mark_claimed(request_id, claim_id="node-claim")
        current = store.get_request(request_id)
        assert current is not None
        return store.publish_result(
            request_id,
            claim_id="node-claim",
            state="CANCELLED",
            result={"success": False, "error": "cancel requested by controller"},
            cleanup={
                "process_residue": [],
                **current.cancellation_identity(claim_id="node-claim"),
            },
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


def test_durable_remote_shell_execution_budget_starts_after_claim(
    monkeypatch, tmp_path
) -> None:
    dispatch = load_wave2_script("wave2_field_dispatch")
    store = DurableRemoteStore(tmp_path)

    monkeypatch.setenv("UMH_DURABLE_REMOTE_ROOT", str(tmp_path))
    monkeypatch.setattr(dispatch, "_ensure_mesh_secrets", lambda: None)
    monkeypatch.setattr(dispatch, "_candidate_sha", lambda _default: "sha")
    monkeypatch.setattr(dispatch, "_MESH_NODE_ID", "windows-desktop")
    monkeypatch.setattr(dispatch, "uuid4", lambda: type("U", (), {"hex": "q" * 32})())

    import substrate.execution.durable_remote_transport as durable
    import substrate.execution.mesh_verdict as mesh_verdict

    monkeypatch.setattr(mesh_verdict, "get_verdict_secret", lambda: "present")
    monkeypatch.setattr(mesh_verdict, "sign_verdict", lambda **_kwargs: "signed")
    monkeypatch.setattr(durable, "DurableRemoteStore", lambda: store)

    clock = {"t": 100.0}
    state = {"request_id": ""}

    monkeypatch.setattr(dispatch.time, "time", lambda: clock["t"])
    monkeypatch.setattr(durable, "now_s", lambda: clock["t"])

    original_put = store.put_request

    def remember_request(req):
        state["request_id"] = req.request_id
        return original_put(req)

    def sleep_and_advance(seconds: float) -> None:
        clock["t"] += seconds
        request_id = state["request_id"]
        if not request_id:
            return
        req = store.get_request(request_id)
        if req is None:
            return
        if clock["t"] >= 160.0 and req.lifecycle_state == "QUEUED":
            store.mark_claimed(
                request_id,
                claim_id="node-claim",
                process_tree={"node_pid": 1, "claimed_at": clock["t"]},
            )
            store.mark_running(
                request_id,
                claim_id="node-claim",
                process_tree={"node_pid": 1, "root_pid": 2, "running_at": clock["t"]},
            )
        if clock["t"] >= 220.0 and req.lifecycle_state == "RUNNING":
            store.publish_result(
                request_id,
                claim_id="node-claim",
                state="SUCCEEDED",
                result={"success": True, "stdout": "ok", "stderr": "", "exit_code": 0},
                cleanup={"process_residue": []},
            )

    monkeypatch.setattr(store, "put_request", remember_request)
    monkeypatch.setattr(dispatch.time, "sleep", sleep_and_advance)

    out = dispatch._durable_remote_shell(
        "hostname",
        command_timeout=70,
        dispatch_timeout=65,
        operation_type="unit",
        correlation_id="corr",
        candidate_sha="sha",
    )

    assert out["ok"] is True
    assert out["raw_status"] == "SUCCEEDED"
    req = store.get_request(out["request_id"])
    assert req is not None
    assert req.cancellation_requested_at == 0.0
    assert req.params["budgets"]["execution_timeout_s"] == 70.0


def test_same_claim_cancel_ack_can_recover_reconciliation_window(monkeypatch, tmp_path) -> None:
    import substrate.execution.durable_remote_transport as durable
    from substrate.execution.durable_remote_transport import make_request

    clock = {"t": 100.0}
    monkeypatch.setattr(durable, "now_s", lambda: clock["t"])
    store = DurableRemoteStore(tmp_path)
    req = make_request(
        correlation_id="corr",
        candidate_sha="sha",
        node_id="windows-desktop",
        operation_type="unit",
        capability="shell",
        params={
            "command": "sleep",
            "timeout": 60,
            "budgets": {
                "cancellation_delivery_timeout_s": 1,
                "process_termination_timeout_s": 1,
                "cancellation_ack_timeout_s": 1,
                "reconciliation_timeout_s": 10,
            },
        },
        risk_class="read_only",
        ttl_seconds=120,
    )
    store.put_request(req)
    store.mark_claimed(req.request_id, claim_id="node-claim")
    store.mark_running(req.request_id, claim_id="node-claim")
    store.request_cancel(req.request_id)

    clock["t"] = 104.0
    current = store.get_request(req.request_id)
    assert current is not None
    assert current.lifecycle_state == "RECONCILIATION_REQUIRED"

    recovered = store.publish_result(
        req.request_id,
        claim_id="node-claim",
        state="CANCELLED",
        result={"success": False, "error": "cancel requested by controller"},
        cleanup={
            "process_residue": [],
            "cancel_reason": "cancel requested by controller",
            **current.cancellation_identity(claim_id="node-claim"),
        },
    )

    assert recovered.lifecycle_state == "CANCELLED"
    assert recovered.cancellation_acknowledged_at == clock["t"]
    assert store.result_for(req.request_id)["state"] == "CANCELLED"


def test_durable_remote_shell_reconciles_observed_reconciliation_required(
    monkeypatch, tmp_path
) -> None:
    dispatch = load_wave2_script("wave2_field_dispatch")
    store = DurableRemoteStore(tmp_path)

    monkeypatch.setenv("UMH_DURABLE_REMOTE_ROOT", str(tmp_path))
    monkeypatch.setattr(dispatch, "_ensure_mesh_secrets", lambda: None)
    monkeypatch.setattr(dispatch, "_candidate_sha", lambda _default: "sha")
    monkeypatch.setattr(dispatch, "_MESH_NODE_ID", "windows-desktop")

    import substrate.execution.durable_remote_transport as durable
    import substrate.execution.mesh_verdict as mesh_verdict

    monkeypatch.setattr(mesh_verdict, "get_verdict_secret", lambda: "present")
    monkeypatch.setattr(mesh_verdict, "sign_verdict", lambda **_kwargs: "signed")
    monkeypatch.setattr(durable, "DurableRemoteStore", lambda: store)
    monkeypatch.setattr(dispatch.time, "sleep", lambda _seconds: None)
    ticks = chain([100.0] * 20, [116.0] * 20, repeat(200.0))
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


def test_durable_remote_shell_returns_bounded_recovery_for_process_residue(
    monkeypatch, tmp_path
) -> None:
    dispatch = load_wave2_script("wave2_field_dispatch")
    store = DurableRemoteStore(tmp_path)

    monkeypatch.setenv("UMH_DURABLE_REMOTE_ROOT", str(tmp_path))
    monkeypatch.setattr(dispatch, "_ensure_mesh_secrets", lambda: None)
    monkeypatch.setattr(dispatch, "_candidate_sha", lambda _default: "sha")
    monkeypatch.setattr(dispatch, "_MESH_NODE_ID", "windows-desktop")

    import substrate.execution.durable_remote_transport as durable
    import substrate.execution.mesh_verdict as mesh_verdict

    clock = {"t": 100.0}
    sleeps = {"count": 0}
    monkeypatch.setattr(dispatch.time, "time", lambda: clock["t"])
    monkeypatch.setattr(durable, "now_s", lambda: clock["t"])
    monkeypatch.setattr(mesh_verdict, "get_verdict_secret", lambda: "present")
    monkeypatch.setattr(mesh_verdict, "sign_verdict", lambda **_kwargs: "signed")
    monkeypatch.setattr(durable, "DurableRemoteStore", lambda: store)

    def sleep_and_advance(seconds: float) -> None:
        sleeps["count"] += 1
        clock["t"] += seconds
        if sleeps["count"] > 160:
            raise AssertionError("durable shell residue recovery loop did not terminate")

    monkeypatch.setattr(dispatch.time, "sleep", sleep_and_advance)
    original_put = store.put_request

    def put_and_create_residue(req):
        out = original_put(req)
        store.mark_claimed(req.request_id, claim_id="claim-1")
        store.publish_result(
            req.request_id,
            claim_id="claim-1",
            state="FAILED",
            result={"success": False, "error": "residue"},
            cleanup={"process_residue": [{"pid": 123, "state": "still_alive"}]},
        )
        return out

    monkeypatch.setattr(store, "put_request", put_and_create_residue)

    out = dispatch._durable_remote_shell(
        "hostname",
        command_timeout=1,
        dispatch_timeout=5,
        operation_type="unit",
        correlation_id="corr",
        candidate_sha="sha",
    )

    assert out["ok"] is False
    assert out["raw_status"] == "RECONCILIATION_REQUIRED"
    assert out["error"] == "durable remote failure left process residue"
    current = store.get_request(out["request_id"])
    assert current is not None
    assert current.cleanup["process_residue"][0]["pid"] == 123
    assert sleeps["count"] < 140


def test_durable_store_does_not_immediately_reconcile_process_residue(
    monkeypatch, tmp_path
) -> None:
    store = DurableRemoteStore(tmp_path)

    import substrate.execution.durable_remote_transport as durable
    from substrate.execution.durable_remote_transport import make_request

    clock = {"t": 100.0}
    monkeypatch.setattr(durable, "now_s", lambda: clock["t"])

    req = make_request(
        correlation_id="corr",
        candidate_sha="sha",
        node_id="windows-desktop",
        operation_type="unit",
        capability="shell",
        params={"command": "sleep", "timeout": 60},
        risk_class="read_only",
        ttl_seconds=120,
    )
    store.put_request(req)
    store.mark_claimed(req.request_id, claim_id="claim-1")
    store.request_cancel(req.request_id)
    current = store.publish_result(
        req.request_id,
        claim_id="claim-1",
        state="CANCELLED",
        result={"success": False, "error": "cancelled"},
        cleanup={"process_residue": [{"pid": 123, "state": "still_alive"}]},
    )

    assert current.lifecycle_state == "RECONCILIATION_REQUIRED"
    assert current.diagnostics["cancel_without_cleanup"] == [{"pid": 123, "state": "still_alive"}]
    clock["t"] = 1000.0
    unresolved = store.fail_unresolved_request(req.request_id)
    assert unresolved.lifecycle_state == "RECONCILIATION_REQUIRED"
    assert unresolved.diagnostics["residue_reconciliation_pending"] is True
