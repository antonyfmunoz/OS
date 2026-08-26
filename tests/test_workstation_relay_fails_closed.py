from __future__ import annotations

import pytest

from substrate.execution.workers.workstation import relay_execution_transport_v1 as relay


def test_legacy_workstation_relay_send_fails_closed_before_ssh(monkeypatch: pytest.MonkeyPatch) -> None:
    def forbidden(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("legacy relay transport must not reach SSH/SCP execution")

    monkeypatch.setattr(relay, "check_ssh_reachable", forbidden)
    monkeypatch.setattr(relay, "write_request_via_scp", forbidden)
    monkeypatch.setattr(relay, "poll_relay_result", forbidden)

    result = relay.send_and_wait(
        {
            "request_id": "REQ-LEGACY-WRITE",
            "action_type": "chrome_proof",
            "payload": {"url": "https://example.invalid"},
        },
        timeout_seconds=1,
    )

    assert result.status == "durable_remote_required"
    assert "requires DurableRemote idempotent execution" in result.transport_error
    assert result.ssh_reachable is False
    assert result.inbox_written is False
    assert result.result_received is False


def test_legacy_workstation_relay_does_not_report_completed() -> None:
    result = relay.send_and_wait(
        {
            "request_id": "REQ-LEGACY-REPLAY",
            "action_type": "ingest_safe_doc",
        },
        timeout_seconds=1,
    )

    assert result.to_dict()["status"] == "durable_remote_required"
    assert result.relay_result == {}


def test_legacy_workstation_relay_write_primitives_fail_closed_before_side_effect(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    def forbidden(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("legacy relay write primitive must not reach SSH/SCP")

    monkeypatch.setattr(relay, "_run_ssh", forbidden)
    monkeypatch.setattr(relay, "gated_subprocess_run", forbidden)

    request = {
        "request_id": "REQ-DIRECT-BYPASS",
        "action_type": "chrome_proof",
    }

    shell_ok, shell_reason = relay.write_request_to_relay(request)
    scp_ok, scp_reason = relay.write_request_via_scp(request, local_tmp=tmp_path)

    assert shell_ok is False
    assert scp_ok is False
    assert "requires DurableRemote idempotent execution" in shell_reason
    assert "requires DurableRemote idempotent execution" in scp_reason
    assert list(tmp_path.iterdir()) == []
