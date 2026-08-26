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
