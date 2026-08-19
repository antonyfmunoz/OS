from __future__ import annotations

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
