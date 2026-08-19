"""Mesh trust boundary — fail-closed relay, verdict required + validated, governed dispatch.

Deterministic. Mocks the socket/HTTP layer — no real network, no real Windows node.

Covers (WP-P0-002):
  - fail-closed relay when the relay secret is unset (refuse dispatch)
  - a signed verdict is REQUIRED on write-class dispatch
  - the verdict is VALIDATED node-side (write-class rejected without a valid verdict)
  - a governed remote exec routes through a remote_node_exec/tmux_send mutation
    (which is what emits the trace event) carrying a valid signed verdict token

Run: pytest tests/test_mesh_dispatch_governed.py -q
"""

from __future__ import annotations

import asyncio
import json
import os
import sys

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _REPO_ROOT)

import pytest

from substrate.execution.mesh_verdict import (
    is_write_class,
    sign_verdict,
    verify_verdict,
)

_SECRET = "unit-test-verdict-secret"


# ── Verdict token: signing + verification round-trip ───────────────────────


def test_verdict_round_trip_valid():
    token = sign_verdict(
        verdict_id="v1",
        node_id="node-a",
        capability="terminal.create",
        risk_class="reversible_write",
        secret=_SECRET,
    )
    check = verify_verdict(
        token,
        expected_node_id="node-a",
        expected_capability="terminal.create",
        secret=_SECRET,
    )
    assert check.valid is True
    assert check.verdict_id == "v1"


def test_verdict_rejects_node_mismatch():
    token = sign_verdict(
        verdict_id="v1",
        node_id="node-a",
        capability="terminal.create",
        risk_class="reversible_write",
        secret=_SECRET,
    )
    check = verify_verdict(
        token,
        expected_node_id="node-b",
        expected_capability="terminal.create",
        secret=_SECRET,
    )
    assert check.valid is False
    assert "node mismatch" in check.reason


def test_verdict_rejects_capability_mismatch():
    token = sign_verdict(
        verdict_id="v1",
        node_id="node-a",
        capability="terminal.create",
        risk_class="reversible_write",
        secret=_SECRET,
    )
    check = verify_verdict(
        token,
        expected_node_id="node-a",
        expected_capability="terminal.destroy",
        secret=_SECRET,
    )
    assert check.valid is False
    assert "capability mismatch" in check.reason


def test_verdict_rejects_tampered_signature():
    token = sign_verdict(
        verdict_id="v1",
        node_id="node-a",
        capability="terminal.create",
        risk_class="reversible_write",
        secret=_SECRET,
    )
    tampered = token[:-4] + ("0000" if not token.endswith("0000") else "1111")
    check = verify_verdict(
        tampered,
        expected_node_id="node-a",
        expected_capability="terminal.create",
        secret=_SECRET,
    )
    assert check.valid is False


def test_verdict_rejects_wrong_secret():
    token = sign_verdict(
        verdict_id="v1",
        node_id="node-a",
        capability="terminal.create",
        risk_class="reversible_write",
        secret=_SECRET,
    )
    check = verify_verdict(
        token,
        expected_node_id="node-a",
        expected_capability="terminal.create",
        secret="other-secret",
    )
    assert check.valid is False


def test_verify_fail_closed_when_secret_unset(monkeypatch):
    monkeypatch.delenv("UMH_MESH_VERDICT_SECRET", raising=False)
    token = sign_verdict(
        verdict_id="v1",
        node_id="node-a",
        capability="terminal.create",
        risk_class="reversible_write",
        secret=_SECRET,
    )
    # No secret in env → verify() cannot validate → fail closed.
    check = verify_verdict(
        token,
        expected_node_id="node-a",
        expected_capability="terminal.create",
    )
    assert check.valid is False
    assert "no verdict secret" in check.reason


def test_sign_fail_closed_when_secret_unset(monkeypatch):
    monkeypatch.delenv("UMH_MESH_VERDICT_SECRET", raising=False)
    with pytest.raises(ValueError):
        sign_verdict(
            verdict_id="v1",
            node_id="node-a",
            capability="terminal.create",
            risk_class="reversible_write",
        )


def test_verdict_expiry(monkeypatch):
    token = sign_verdict(
        verdict_id="v1",
        node_id="node-a",
        capability="terminal.create",
        risk_class="reversible_write",
        secret=_SECRET,
        ttl_seconds=10,
        now=1000.0,
    )
    # 20s later → expired.
    check = verify_verdict(
        token,
        expected_node_id="node-a",
        expected_capability="terminal.create",
        secret=_SECRET,
        now=1020.0,
    )
    assert check.valid is False
    assert "expired" in check.reason


def test_is_write_class_fail_closed():
    assert is_write_class("read_only") is False
    assert is_write_class("reversible_write") is True
    assert is_write_class("irreversible_write") is True
    assert is_write_class("") is True  # empty → write-class
    assert is_write_class(None) is True  # missing → write-class
    assert is_write_class("bananas") is True  # unknown → write-class


# ── Fail-closed relay dispatch (built-in governed dispatcher) ──────────────


def test_default_dispatch_fail_closed_no_relay_secret(monkeypatch):
    monkeypatch.delenv("UMH_MESH_RELAY_SECRET", raising=False)
    monkeypatch.setenv("UMH_MESH_VERDICT_SECRET", _SECRET)
    from substrate.sockets.mesh_dispatch_port import mesh_dispatch

    res = mesh_dispatch(
        node_id="node-a",
        capability="shell",
        params={"command": "ls"},
        risk_class="reversible_write",
    )
    assert res["ok"] is False
    assert res["status"] == "relay_secret_unset"


def test_default_dispatch_fail_closed_no_verdict_secret(monkeypatch):
    monkeypatch.setenv("UMH_MESH_RELAY_SECRET", "relay-secret")
    monkeypatch.delenv("UMH_MESH_VERDICT_SECRET", raising=False)
    from substrate.sockets.mesh_dispatch_port import mesh_dispatch

    res = mesh_dispatch(
        node_id="node-a",
        capability="shell",
        params={"command": "ls"},
        risk_class="reversible_write",
    )
    assert res["ok"] is False
    assert res["status"] == "verdict_secret_unset"


def test_default_dispatch_signs_verdict_and_authenticates(monkeypatch):
    """A write-class dispatch mints a valid verdict + relay bearer, no raw path."""
    monkeypatch.setenv("UMH_MESH_RELAY_SECRET", "relay-secret")
    monkeypatch.setenv("UMH_MESH_VERDICT_SECRET", _SECRET)

    captured = {}

    class _FakeResp:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def read(self):
            import json

            return json.dumps({"ok": True, "result_data": {"stdout": "ok"}}).encode()

    def _fake_urlopen(req, timeout=None):
        import json

        captured["auth"] = req.headers.get("Authorization")
        captured["payload"] = json.loads(req.data.decode())
        return _FakeResp()

    import substrate.sockets.mesh_dispatch_port as port

    monkeypatch.setattr(port.urllib.request, "urlopen", _fake_urlopen)

    res = port.mesh_dispatch(
        node_id="node-a",
        capability="shell",
        params={"command": "ls"},
        risk_class="reversible_write",
    )
    assert res["ok"] is True
    # relay bearer attached
    assert captured["auth"] == "Bearer relay-secret"
    # signed verdict present and valid, bound to node + capability
    token = captured["payload"]["verdict_token"]
    assert token
    check = verify_verdict(
        token,
        expected_node_id="node-a",
        expected_capability="shell",
        secret=_SECRET,
    )
    assert check.valid is True


# ── Node-side verdict validation ───────────────────────────────────────────


def _bare_node_client(node_id: str = "node-a"):
    """Build a NodeClient without running _init_adapters (Windows-only)."""
    from nodes.windows.umh_node.client import NodeClient
    from nodes.windows.umh_node.config import NodeConfig

    client = object.__new__(NodeClient)
    client._config = NodeConfig(node_id=node_id)
    return client


class _DurableAckWs:
    def __init__(self, client, claim_acks: list[dict[str, object]] | None = None) -> None:
        self.client = client
        self.claim_acks = list(claim_acks or [])
        self.sent: list[dict[str, object]] = []

    async def send(self, raw: str) -> None:
        msg = json.loads(raw)
        self.sent.append(msg)
        if msg.get("method") != "durable_command.claimed":
            return
        result = self.claim_acks.pop(0) if self.claim_acks else {"ok": True, "error": ""}

        async def _respond() -> None:
            await self.client._handle_message(
                json.dumps({"jsonrpc": "2.0", "result": result, "id": msg.get("id")})
            )

        asyncio.create_task(_respond())


def _durable_node_client(tmp_path, node_id: str = "windows-desktop"):
    from nodes.windows.umh_node.client import NodeClient
    from nodes.windows.umh_node.config import NodeConfig
    from substrate.execution.durable_remote_transport import DurableRemoteStore

    client = object.__new__(NodeClient)
    client._config = NodeConfig(node_id=node_id)
    client._connected = True
    client._msg_id = 0
    client._pending_rpc = {}
    client._durable_store = DurableRemoteStore(tmp_path)
    client._durable_processes = {}
    client._adapters = {}
    return client


def _durable_request(**overrides):
    from substrate.execution.durable_remote_transport import make_request

    data = {
        "correlation_id": "unit-durable",
        "candidate_sha": "abc123",
        "node_id": "windows-desktop",
        "operation_type": "transport_unit",
        "capability": "shell",
        "params": {"command": "echo ok", "timeout": 5},
        "risk_class": "read_only",
        "ttl_seconds": 60,
    }
    data.update(overrides)
    return make_request(**data)


def test_node_rejects_write_class_without_verdict(monkeypatch):
    monkeypatch.setenv("UMH_MESH_VERDICT_SECRET", _SECRET)
    client = _bare_node_client("node-a")
    ok, reason = client._validate_verdict("shell.execute", "reversible_write", "")
    assert ok is False
    assert "verdict" in reason.lower()


def test_node_rejects_write_class_with_invalid_verdict(monkeypatch):
    monkeypatch.setenv("UMH_MESH_VERDICT_SECRET", _SECRET)
    client = _bare_node_client("node-a")
    ok, reason = client._validate_verdict("shell.execute", "reversible_write", "v1.bogus.sig")
    assert ok is False


def test_node_rejects_verdict_bound_to_other_node(monkeypatch):
    monkeypatch.setenv("UMH_MESH_VERDICT_SECRET", _SECRET)
    # Token minted for node-b, but this node is node-a.
    token = sign_verdict(
        verdict_id="v1",
        node_id="node-b",
        capability="shell.execute",
        risk_class="reversible_write",
        secret=_SECRET,
    )
    client = _bare_node_client("node-a")
    ok, reason = client._validate_verdict("shell.execute", "reversible_write", token)
    assert ok is False
    assert "node mismatch" in reason


def test_node_accepts_valid_write_class_verdict(monkeypatch):
    monkeypatch.setenv("UMH_MESH_VERDICT_SECRET", _SECRET)
    token = sign_verdict(
        verdict_id="v1",
        node_id="node-a",
        capability="shell.execute",
        risk_class="reversible_write",
        secret=_SECRET,
    )
    client = _bare_node_client("node-a")
    ok, reason = client._validate_verdict("shell.execute", "reversible_write", token)
    assert ok is True


def test_node_allows_read_only_without_verdict(monkeypatch):
    monkeypatch.setenv("UMH_MESH_VERDICT_SECRET", _SECRET)
    client = _bare_node_client("node-a")
    ok, reason = client._validate_verdict("terminal.capture", "read_only", "")
    assert ok is True


def test_node_fail_closed_no_secret_write_class(monkeypatch):
    monkeypatch.delenv("UMH_MESH_VERDICT_SECRET", raising=False)
    client = _bare_node_client("node-a")
    ok, reason = client._validate_verdict("shell.execute", "reversible_write", "")
    assert ok is False


def test_node_rejects_risk_downgrade_attack(monkeypatch):
    """A caller cannot skip the verdict by lying that a write-class cap is read_only.

    The node's own config marks 'shell' as write-class (max_risk_class), so even
    a wire risk_class of 'read_only' still requires a verdict.
    """
    monkeypatch.setenv("UMH_MESH_VERDICT_SECRET", _SECRET)
    from nodes.windows.umh_node.config import CapabilityConfig

    client = _bare_node_client("node-a")
    client._config.capabilities = {
        "shell": CapabilityConfig(enabled=True, max_risk_class="irreversible_write")
    }
    # Caller lies: risk_class=read_only, but shell is write-class per node config.
    ok, reason = client._validate_verdict("shell.execute", "read_only", "")
    assert ok is False
    assert "verdict" in reason.lower()


def test_durable_node_does_not_execute_when_controller_rejects_claim(tmp_path, monkeypatch):
    client = _durable_node_client(tmp_path)
    ws = _DurableAckWs(client, claim_acks=[{"ok": False, "error": "claim rejected"}])
    client._ws = ws
    called = False

    async def _execute(*_args, **_kwargs):
        nonlocal called
        called = True
        return {"success": True, "stdout": "should not run"}

    monkeypatch.setattr(client, "_execute_capability_for_durable", _execute)
    req = _durable_request()

    asyncio.run(
        client._handle_durable_command(
            {"method": "durable_command.request", "params": req.to_dict()}
        )
    )

    assert called is False
    assert [msg.get("method") for msg in ws.sent] == ["durable_command.claimed"]
    assert client._durable_store.result_for(req.request_id) is None


def test_durable_node_does_not_run_adapter_when_running_ack_is_rejected(tmp_path):
    from nodes.windows.umh_node.config import CapabilityConfig

    client = _durable_node_client(tmp_path)
    ws = _DurableAckWs(
        client,
        claim_acks=[
            {"ok": True, "error": ""},
            {"ok": False, "error": "running rejected"},
        ],
    )
    client._ws = ws
    client._config.capabilities = {
        "dummy": CapabilityConfig(enabled=True, max_risk_class="read_only")
    }
    executed = False

    class _Adapter:
        def execute(self, *_args, **_kwargs):
            nonlocal executed
            executed = True
            return {"success": True}

    client._adapters = {"dummy": _Adapter()}
    req = _durable_request(capability="dummy.execute", params={}, risk_class="read_only")

    asyncio.run(
        client._handle_durable_command(
            {"method": "durable_command.request", "params": req.to_dict()}
        )
    )

    assert executed is False
    methods = [msg.get("method") for msg in ws.sent]
    assert methods == [
        "durable_command.claimed",
        "durable_command.claimed",
        "durable_command.result",
    ]
    result = client._durable_store.result_for(req.request_id)
    assert result is not None
    assert result["state"] == "FAILED"
    assert "running acknowledgement rejected" in result["result"]["error"]


def test_durable_shell_does_not_start_when_running_ack_is_rejected(tmp_path):
    from nodes.windows.umh_node.config import CapabilityConfig

    marker = tmp_path / "marker.txt"
    client = _durable_node_client(tmp_path / "store")
    ws = _DurableAckWs(
        client,
        claim_acks=[
            {"ok": True, "error": ""},
            {"ok": False, "error": "running rejected"},
        ],
    )
    client._ws = ws
    client._config.capabilities = {
        "shell": CapabilityConfig(enabled=True, max_risk_class="read_only")
    }
    client._adapters = {"shell": object()}
    req = _durable_request(
        params={
            "argv": [
                sys.executable,
                "-c",
                f"from pathlib import Path; Path({str(marker)!r}).write_text('ran')",
            ],
            "timeout": 5,
        },
        risk_class="read_only",
    )

    asyncio.run(
        client._handle_durable_command(
            {"method": "durable_command.request", "params": req.to_dict()}
        )
    )

    assert marker.exists() is False
    methods = [msg.get("method") for msg in ws.sent]
    assert methods == [
        "durable_command.claimed",
        "durable_command.claimed",
        "durable_command.result",
    ]
    result = client._durable_store.result_for(req.request_id)
    assert result is not None
    assert "running acknowledgement rejected" in result["result"]["error"]


def test_durable_shell_post_start_running_update_is_not_an_execution_gate(tmp_path):
    from nodes.windows.umh_node.config import CapabilityConfig

    marker = tmp_path / "marker.txt"
    client = _durable_node_client(tmp_path / "store")
    ws = _DurableAckWs(
        client,
        claim_acks=[
            {"ok": True, "error": ""},
            {"ok": True, "error": ""},
            {"ok": False, "error": "late running update rejected"},
        ],
    )
    client._ws = ws
    client._config.capabilities = {
        "shell": CapabilityConfig(enabled=True, max_risk_class="read_only")
    }
    client._adapters = {"shell": object()}
    req = _durable_request(
        params={
            "argv": [
                sys.executable,
                "-c",
                f"from pathlib import Path; Path({str(marker)!r}).write_text('ran')",
            ],
            "timeout": 5,
        },
        risk_class="read_only",
    )

    asyncio.run(
        client._handle_durable_command(
            {"method": "durable_command.request", "params": req.to_dict()}
        )
    )

    assert marker.read_text(encoding="utf-8") == "ran"
    methods = [msg.get("method") for msg in ws.sent]
    assert methods == [
        "durable_command.claimed",
        "durable_command.claimed",
        "durable_command.claimed",
        "durable_command.result",
    ]
    result = client._durable_store.result_for(req.request_id)
    assert result is not None
    assert result["state"] == "SUCCEEDED"


def test_durable_node_sends_original_terminal_state_when_local_store_needs_reconciliation(
    tmp_path, monkeypatch
):
    client = _durable_node_client(tmp_path)
    ws = _DurableAckWs(client)
    client._ws = ws

    async def _execute(*_args, **_kwargs):
        return {
            "success": False,
            "error": "timed out",
            "cleanup": {"process_residue": [{"pid": 123, "state": "still_alive"}]},
        }

    monkeypatch.setattr(client, "_execute_capability_for_durable", _execute)
    req = _durable_request()

    asyncio.run(
        client._handle_durable_command(
            {"method": "durable_command.request", "params": req.to_dict()}
        )
    )

    result_msg = ws.sent[-1]
    assert result_msg["method"] == "durable_command.result"
    assert result_msg["params"]["state"] == "FAILED"
    assert result_msg["params"]["cleanup"]["process_residue"][0]["pid"] == 123
    local = client._durable_store.get_request(req.request_id)
    assert local is not None
    assert local.lifecycle_state == "RECONCILIATION_REQUIRED"


def test_durable_node_replays_terminal_result_with_original_cleanup(tmp_path):
    client = _durable_node_client(tmp_path)
    ws = _DurableAckWs(client)
    client._ws = ws
    req = client._durable_store.put_request(_durable_request())
    client._durable_store.mark_claimed(req.request_id, claim_id="claim-1")
    client._durable_store.publish_result(
        req.request_id,
        claim_id="claim-1",
        state="CANCELLED",
        result={"success": False, "error": "cancelled"},
        cleanup={"process_residue": [], "cancel_reason": "unit"},
    )

    asyncio.run(
        client._handle_durable_command(
            {"method": "durable_command.request", "params": req.to_dict()}
        )
    )

    assert len(ws.sent) == 1
    replay = ws.sent[0]
    assert replay["method"] == "durable_command.result"
    assert replay["params"]["cleanup"] == {
        "process_residue": [],
        "cancel_reason": "unit",
    }
    assert replay["params"]["idempotent_replay"] is True


# ── Governed remote dispatch routes through the right mutation ─────────────


def test_governed_remote_dispatch_uses_remote_node_exec_mutation(monkeypatch):
    """create/destroy → remote_node_exec; send/send_key → tmux_send; payload has a valid verdict."""
    monkeypatch.setenv("UMH_MESH_VERDICT_SECRET", _SECRET)
    monkeypatch.setenv("UMH_MESH_RELAY_SECRET", "relay-secret")

    import transports.api.cockpit_workstation_control_routes as routes

    captured = {"mutation_name": None, "payload": None}

    async def _fake_post(payload, timeout):
        captured["payload"] = payload
        return {"ok": True, "result_data": {"session": "s1"}}

    from substrate.organism.mutation_router import MutationResponse

    def _fake_governed(mutation_name, intent, execute_fn, source="cockpit", metadata=None):
        # Record which mutation spec governs the actuation (this is the path
        # that emits the trace event) and run the real execute_fn so the signed
        # verdict is minted and the (mocked) relay call is exercised.
        captured["mutation_name"] = mutation_name
        output, ok = execute_fn()
        return MutationResponse(
            success=ok,
            output=output,
            status="executed" if ok else "failed",
        )

    monkeypatch.setattr(routes, "_post_to_relay", _fake_post)
    monkeypatch.setattr(routes, "governed_mutation", _fake_governed)

    res = asyncio.run(routes._remote_terminal_dispatch("node-a", "create", {"shell": "powershell"}))
    assert res["ok"] is True
    assert captured["mutation_name"] == "remote_node_exec"
    # payload carries a valid signed verdict token bound to node + capability
    token = captured["payload"]["verdict_token"]
    check = verify_verdict(
        token,
        expected_node_id="node-a",
        expected_capability="terminal.create",
        secret=_SECRET,
    )
    assert check.valid is True

    # send/send_key → tmux_send
    captured["mutation_name"] = None
    res2 = asyncio.run(
        routes._remote_terminal_dispatch("node-a", "send", {"name": "s1", "text": "echo hi"})
    )
    assert res2["ok"] is True
    assert captured["mutation_name"] == "tmux_send"


def test_governed_remote_dispatch_read_only_no_verdict(monkeypatch):
    """Read-only ops dispatch directly (no verdict, no governed mutation)."""
    monkeypatch.setenv("UMH_MESH_RELAY_SECRET", "relay-secret")
    import transports.api.cockpit_workstation_control_routes as routes

    captured = {}

    async def _fake_post(payload, timeout):
        captured["payload"] = payload
        return {"ok": True, "result_data": {"sessions": []}}

    def _boom(*a, **k):
        raise AssertionError("read-only op must NOT go through governed_mutation")

    monkeypatch.setattr(routes, "_post_to_relay", _fake_post)
    monkeypatch.setattr(routes, "governed_mutation", _boom)

    res = asyncio.run(routes._remote_terminal_dispatch("node-a", "list", {}))
    assert res["ok"] is True
    assert captured["payload"]["risk_class"] == "read_only"
    assert captured["payload"].get("verdict_token", "") == ""
