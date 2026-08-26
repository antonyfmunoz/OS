from __future__ import annotations

import asyncio

import transports.api.cockpit_workspace_routes as workspace_routes


class _JsonRequest:
    def __init__(self, body: dict[str, str]) -> None:
        self._body = body

    async def json(self) -> dict[str, str]:
        return self._body


def test_remote_write_file_fails_closed_before_ssh(monkeypatch) -> None:
    def forbidden_ssh(_cmd: str):
        raise AssertionError("remote write must not execute through direct SSH")

    monkeypatch.setattr(workspace_routes, "_ssh_cmd", forbidden_ssh)

    result = asyncio.run(
        workspace_routes._remote_write_file(
            _JsonRequest({"node": "windows", "path": r"C:\temp", "content": "payload"})
        )
    )

    assert result["ok"] is False
    assert "DurableRemote" in result["error"]
    assert result["path"] == r"C:\temp"
