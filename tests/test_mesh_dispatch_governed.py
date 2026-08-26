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
import subprocess
import sys
import textwrap
import time
from collections import deque
from types import SimpleNamespace

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _REPO_ROOT)

import httpx  # noqa: E402
import pytest  # noqa: E402
from fastapi import HTTPException  # noqa: E402

from substrate.execution.mesh_verdict import (  # noqa: E402
    CONSEQUENTIAL_WRITE_EFFECT,
    READ_ONLY_EFFECT,
    canonical_payload_digest,
    canonical_sync_effect_policy,
    effect_policy_id,
    is_write_class,
    sign_verdict,
    verify_verdict,
)

_SECRET = "unit-test-verdict-secret"


# ── Verdict token: signing + verification round-trip ───────────────────────


def test_verdict_round_trip_valid():
    params = {"argv": ["echo", "ok"], "cwd": r"C:\dev\dev"}
    token = sign_verdict(
        verdict_id="v1",
        node_id="node-a",
        capability="terminal.create",
        risk_class="reversible_write",
        request_id="req-1",
        correlation_id="corr-1",
        candidate_sha="a" * 40,
        effect_class="CONSEQUENTIAL_WRITE",
        payload_digest=canonical_payload_digest(params),
        idempotency_key="idem-1",
        secret=_SECRET,
    )
    check = verify_verdict(
        token,
        expected_node_id="node-a",
        expected_capability="terminal.create",
        expected_risk_class="reversible_write",
        expected_request_id="req-1",
        expected_correlation_id="corr-1",
        expected_candidate_sha="a" * 40,
        expected_effect_class="CONSEQUENTIAL_WRITE",
        expected_payload_digest=canonical_payload_digest(params),
        expected_idempotency_key="idem-1",
        secret=_SECRET,
    )
    assert check.valid is True
    assert check.verdict_id == "v1"


def test_verdict_rejects_payload_digest_mismatch():
    token = sign_verdict(
        verdict_id="v1",
        node_id="node-a",
        capability="terminal.create",
        risk_class="reversible_write",
        request_id="req-1",
        correlation_id="corr-1",
        effect_class="CONSEQUENTIAL_WRITE",
        payload_digest=canonical_payload_digest({"argv": ["echo", "ok"]}),
        idempotency_key="idem-1",
        secret=_SECRET,
    )
    check = verify_verdict(
        token,
        expected_node_id="node-a",
        expected_capability="terminal.create",
        expected_request_id="req-1",
        expected_correlation_id="corr-1",
        expected_effect_class="CONSEQUENTIAL_WRITE",
        expected_payload_digest=canonical_payload_digest({"argv": ["echo", "changed"]}),
        expected_idempotency_key="idem-1",
        secret=_SECRET,
    )
    assert check.valid is False
    assert "payload_digest mismatch" in check.reason


def test_verdict_rejects_request_identity_mismatch():
    token = sign_verdict(
        verdict_id="v1",
        node_id="node-a",
        capability="terminal.create",
        risk_class="reversible_write",
        request_id="req-1",
        correlation_id="corr-1",
        effect_class="CONSEQUENTIAL_WRITE",
        payload_digest=canonical_payload_digest({"argv": ["echo", "ok"]}),
        idempotency_key="idem-1",
        secret=_SECRET,
    )
    check = verify_verdict(
        token,
        expected_node_id="node-a",
        expected_capability="terminal.create",
        expected_request_id="req-2",
        expected_correlation_id="corr-1",
        expected_effect_class="CONSEQUENTIAL_WRITE",
        expected_payload_digest=canonical_payload_digest({"argv": ["echo", "ok"]}),
        expected_idempotency_key="idem-1",
        secret=_SECRET,
    )
    assert check.valid is False
    assert "request_id mismatch" in check.reason


def test_verdict_rejects_candidate_sha_mismatch():
    token = sign_verdict(
        verdict_id="v1",
        node_id="node-a",
        capability="terminal.create",
        risk_class="reversible_write",
        request_id="req-1",
        correlation_id="corr-1",
        candidate_sha="a" * 40,
        effect_class="CONSEQUENTIAL_WRITE",
        payload_digest=canonical_payload_digest({"argv": ["echo", "ok"]}),
        idempotency_key="idem-1",
        secret=_SECRET,
    )
    check = verify_verdict(
        token,
        expected_node_id="node-a",
        expected_capability="terminal.create",
        expected_request_id="req-1",
        expected_correlation_id="corr-1",
        expected_candidate_sha="b" * 40,
        expected_effect_class="CONSEQUENTIAL_WRITE",
        expected_payload_digest=canonical_payload_digest({"argv": ["echo", "ok"]}),
        expected_idempotency_key="idem-1",
        secret=_SECRET,
    )
    assert check.valid is False
    assert "candidate_sha mismatch" in check.reason


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
        capability="terminal.capture",
        params={"command": "ls"},
        risk_class="read_only",
    )
    assert res["ok"] is False
    assert res["status"] == "relay_secret_unset"


def test_default_dispatch_fail_closed_whitespace_relay_secret(monkeypatch):
    monkeypatch.setenv("UMH_MESH_RELAY_SECRET", "   ")
    monkeypatch.setenv("UMH_MESH_VERDICT_SECRET", _SECRET)
    from substrate.sockets.mesh_dispatch_port import mesh_dispatch

    res = mesh_dispatch(
        node_id="node-a",
        capability="terminal.capture",
        params={"command": "ls"},
        risk_class="read_only",
    )
    assert res["ok"] is False
    assert res["status"] == "relay_secret_unset"


def test_default_dispatch_rejects_write_class_before_network(monkeypatch):
    monkeypatch.setenv("UMH_MESH_RELAY_SECRET", "relay-secret")
    monkeypatch.setenv("UMH_MESH_VERDICT_SECRET", _SECRET)

    import substrate.sockets.mesh_dispatch_port as port

    called = False

    def _fake_urlopen(*_args, **_kwargs):
        nonlocal called
        called = True
        raise AssertionError("write-class sync dispatch must not reach network")

    monkeypatch.setattr(port.urllib.request, "urlopen", _fake_urlopen)

    res = port.mesh_dispatch(
        node_id="node-a",
        capability="shell",
        params={"command": "ls"},
        risk_class="reversible_write",
    )
    assert res["ok"] is False
    assert res["status"] == "durable_remote_required"
    assert called is False


def test_http_dispatch_rejects_write_before_node_send(monkeypatch):
    monkeypatch.setenv("UMH_MESH_VERDICT_SECRET", _SECRET)
    from substrate.execution.executor import WorkPacketExecutor
    from substrate.sockets.capability_socket import CapabilitySocket
    from substrate.sockets.outcome_socket import OutcomeSocket
    from substrate.sockets.signal_socket import SignalSocket
    from substrate.sockets.view_socket import ViewSocket
    from transports.node_mesh.config import MeshConfig
    from transports.node_mesh.server import NodeMeshServer

    server = NodeMeshServer(
        config=MeshConfig(),
        executor=WorkPacketExecutor(),
        signal_socket=SignalSocket(),
        capability_socket=CapabilitySocket(),
        outcome_socket=OutcomeSocket(),
        view_socket=ViewSocket(),
    )

    params = {"argv": ["echo", "unsafe"]}
    result = asyncio.run(
        server._http_dispatch(
            {
                "request_id": "req-1",
                "correlation_id": "corr-1",
                "effect_class": "CONSEQUENTIAL_WRITE",
                "idempotency_key": "req-1",
                "payload_digest": canonical_payload_digest(params),
                "node_id": "node-a",
                "capability": "shell",
                "params": params,
                "risk_class": "reversible_write",
                "verdict_token": "v1.invalid.sig",
                "timeout": 1,
            }
        )
    )

    assert result["ok"] is False
    assert result["status"] == "sync_write_denied"


def test_http_dispatch_rejects_shell_declared_read_only(monkeypatch):
    from substrate.execution.executor import WorkPacketExecutor
    from substrate.sockets.capability_socket import CapabilitySocket
    from substrate.sockets.outcome_socket import OutcomeSocket
    from substrate.sockets.signal_socket import SignalSocket
    from substrate.sockets.view_socket import ViewSocket
    from transports.node_mesh.config import MeshConfig
    from transports.node_mesh.server import NodeMeshServer

    server = NodeMeshServer(
        config=MeshConfig(),
        executor=WorkPacketExecutor(),
        signal_socket=SignalSocket(),
        capability_socket=CapabilitySocket(),
        outcome_socket=OutcomeSocket(),
        view_socket=ViewSocket(),
    )
    params = {"argv": ["echo", "unsafe"]}

    result = asyncio.run(
        server._http_dispatch(
            {
                "request_id": "req-lying",
                "correlation_id": "corr-lying",
                "effect_class": READ_ONLY_EFFECT,
                "idempotency_key": "req-lying",
                "payload_digest": canonical_payload_digest(params),
                "node_id": "node-a",
                "capability": "shell",
                "params": params,
                "risk_class": "read_only",
                "timeout": 1,
            }
        )
    )

    assert result["ok"] is False
    assert result["status"] == "effect_policy_mismatch"
    assert result["authoritative_effect_class"] == CONSEQUENTIAL_WRITE_EFFECT


def test_http_dispatch_rejects_unknown_effect(monkeypatch):
    monkeypatch.setenv("UMH_MESH_VERDICT_SECRET", _SECRET)
    from substrate.execution.executor import WorkPacketExecutor
    from substrate.sockets.capability_socket import CapabilitySocket
    from substrate.sockets.outcome_socket import OutcomeSocket
    from substrate.sockets.signal_socket import SignalSocket
    from substrate.sockets.view_socket import ViewSocket
    from transports.node_mesh.config import MeshConfig
    from transports.node_mesh.server import NodeMeshServer

    server = NodeMeshServer(
        config=MeshConfig(),
        executor=WorkPacketExecutor(),
        signal_socket=SignalSocket(),
        capability_socket=CapabilitySocket(),
        outcome_socket=OutcomeSocket(),
        view_socket=ViewSocket(),
    )

    result = asyncio.run(
        server._http_dispatch(
            {
                "request_id": "req-1",
                "correlation_id": "corr-1",
                "effect_class": "UNKNOWN",
                "idempotency_key": "req-1",
                "node_id": "node-a",
                "capability": "terminal.capture",
                "params": {"name": "session-1"},
                "risk_class": "read_only",
                "timeout": 1,
            }
        )
    )

    assert result["ok"] is False
    assert result["status"] == "effect_class_required"


def test_http_dispatch_rejects_read_only_without_operation_binding(monkeypatch):
    from substrate.execution.executor import WorkPacketExecutor
    from substrate.sockets.capability_socket import CapabilitySocket
    from substrate.sockets.outcome_socket import OutcomeSocket
    from substrate.sockets.signal_socket import SignalSocket
    from substrate.sockets.view_socket import ViewSocket
    from transports.node_mesh.config import MeshConfig
    from transports.node_mesh.server import NodeMeshServer

    server = NodeMeshServer(
        config=MeshConfig(),
        executor=WorkPacketExecutor(),
        signal_socket=SignalSocket(),
        capability_socket=CapabilitySocket(),
        outcome_socket=OutcomeSocket(),
        view_socket=ViewSocket(),
    )

    result = asyncio.run(
        server._http_dispatch(
            {
                "node_id": "node-a",
                "capability": "terminal.capture",
                "params": {"name": "s1"},
                "effect_class": READ_ONLY_EFFECT,
                "risk_class": "read_only",
                "timeout": 1,
            }
        )
    )

    assert result["ok"] is False
    assert result["status"] == "operation_binding_required"


def test_http_dispatch_rejects_read_only_payload_digest_mismatch(monkeypatch):
    from substrate.execution.executor import WorkPacketExecutor
    from substrate.sockets.capability_socket import CapabilitySocket
    from substrate.sockets.outcome_socket import OutcomeSocket
    from substrate.sockets.signal_socket import SignalSocket
    from substrate.sockets.view_socket import ViewSocket
    from transports.node_mesh.config import MeshConfig
    from transports.node_mesh.server import NodeMeshServer

    server = NodeMeshServer(
        config=MeshConfig(),
        executor=WorkPacketExecutor(),
        signal_socket=SignalSocket(),
        capability_socket=CapabilitySocket(),
        outcome_socket=OutcomeSocket(),
        view_socket=ViewSocket(),
    )

    result = asyncio.run(
        server._http_dispatch(
            {
                "request_id": "req-read",
                "correlation_id": "corr-read",
                "effect_class": READ_ONLY_EFFECT,
                "idempotency_key": "req-read",
                "payload_digest": canonical_payload_digest({"name": "old"}),
                "node_id": "node-a",
                "capability": "terminal.capture",
                "params": {"name": "new"},
                "risk_class": "read_only",
                "timeout": 1,
            }
        )
    )

    assert result["ok"] is False
    assert result["status"] == "payload_digest_mismatch"


def test_http_dispatch_read_only_does_not_require_write_binding(monkeypatch):
    monkeypatch.setenv("UMH_MESH_VERDICT_SECRET", _SECRET)
    from substrate.execution.executor import WorkPacketExecutor
    from substrate.sockets.capability_socket import CapabilitySocket
    from substrate.sockets.outcome_socket import OutcomeSocket
    from substrate.sockets.signal_socket import SignalSocket
    from substrate.sockets.view_socket import ViewSocket
    from transports.node_mesh.config import MeshConfig
    from transports.node_mesh.server import NodeMeshServer

    server = NodeMeshServer(
        config=MeshConfig(),
        executor=WorkPacketExecutor(),
        signal_socket=SignalSocket(),
        capability_socket=CapabilitySocket(),
        outcome_socket=OutcomeSocket(),
        view_socket=ViewSocket(),
    )

    result = asyncio.run(
        server._http_dispatch(
            {
                "node_id": "node-a",
                "capability": "terminal.capture",
                "params": {"name": "s1"},
                "effect_class": READ_ONLY_EFFECT,
                "request_id": "req-read",
                "correlation_id": "corr-read",
                "idempotency_key": "req-read",
                "payload_digest": canonical_payload_digest({"name": "s1"}),
                "risk_class": "read_only",
                "timeout": 1,
            }
        )
    )

    assert result["ok"] is False
    assert "not connected" in result["error"]


def test_legacy_mesh_dispatch_refuses_write_before_post(monkeypatch):
    monkeypatch.setenv("UMH_MESH_RELAY_SECRET", "relay-secret")
    monkeypatch.setenv("UMH_MESH_VERDICT_SECRET", _SECRET)
    import transports.api._mesh_dispatch as mesh_dispatch

    posts = {"count": 0}

    class _FakeClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        async def get(self, *_args, **_kwargs):
            return None

        async def post(self, *_args, **_kwargs):
            posts["count"] += 1
            raise AssertionError("sync write dispatch must not POST")

    monkeypatch.setattr(httpx, "AsyncClient", _FakeClient)

    plan = SimpleNamespace(
        plan_id="plan-1",
        tasks=[SimpleNamespace(task_id="task-1", description="write something")],
        intent=SimpleNamespace(goal="goal"),
    )

    result = asyncio.run(mesh_dispatch.dispatch_plan_to_node(plan, node_id="windows-desktop"))

    assert posts["count"] == 0
    assert result["failed"] == 1
    assert result["results"][0]["error"] == "consequential writes must use DurableRemote, not sync mesh"


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
    assert res["status"] == "durable_remote_required"


def test_verdict_secret_whitespace_fails_closed(monkeypatch):
    monkeypatch.setenv("UMH_MESH_VERDICT_SECRET", "   ")

    with pytest.raises(ValueError, match="not configured"):
        sign_verdict(
            verdict_id="v1",
            node_id="node-a",
            capability="shell",
            risk_class="reversible_write",
        )
    check = verify_verdict(
        "v1.payload.signature",
        expected_node_id="node-a",
        expected_capability="shell",
    )
    assert check.valid is False
    assert "no verdict secret" in check.reason


def test_default_dispatch_read_only_authenticates_without_write_verdict(monkeypatch):
    """A read-only dispatch authenticates to relay and carries explicit READ_ONLY effect."""
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
        capability="terminal.capture",
        params={"name": "s1"},
        risk_class="read_only",
    )
    assert res["ok"] is True
    assert captured["auth"] == "Bearer relay-secret"
    assert captured["payload"]["effect_class"] == READ_ONLY_EFFECT
    assert captured["payload"]["authoritative_effect_class"] == READ_ONLY_EFFECT
    assert captured["payload"]["effect_policy"] == effect_policy_id()
    assert captured["payload"]["risk_class"] == "read_only"
    assert captured["payload"]["verdict_token"] == ""


# ── Node-side verdict validation ───────────────────────────────────────────


def _bare_node_client(node_id: str = "node-a"):
    """Build a NodeClient without running _init_adapters (Windows-only)."""
    from nodes.windows.umh_node.client import NodeClient
    from nodes.windows.umh_node.config import NodeConfig

    client = object.__new__(NodeClient)
    client._config = NodeConfig(node_id=node_id)
    return client


def _sync_node_client(node_id: str = "node-a"):
    client = _bare_node_client(node_id)
    client._capability_semaphore = asyncio.Semaphore(8)
    client._sent_ws: list[dict[str, object]] = []

    async def _send_ws(raw: str | bytes) -> None:
        client._sent_ws.append(json.loads(raw.decode() if isinstance(raw, bytes) else raw))

    client._send_ws = _send_ws
    client._adapters = {}
    return client


def _operation_bound_verdict(
    *,
    node_id: str = "node-a",
    capability: str = "shell.execute",
    risk_class: str = "reversible_write",
    request_id: str = "req-1",
    correlation_id: str = "corr-1",
    candidate_sha: str = "a" * 40,
    effect_class: str = "CONSEQUENTIAL_WRITE",
    idempotency_key: str = "idem-1",
    params: dict[str, object] | None = None,
) -> tuple[str, dict[str, object]]:
    payload = params or {"argv": ["echo", "ok"]}
    token = sign_verdict(
        verdict_id="v1",
        node_id=node_id,
        capability=capability,
        risk_class=risk_class,
        request_id=request_id,
        correlation_id=correlation_id,
        candidate_sha=candidate_sha,
        effect_class=effect_class,
        authoritative_effect_class=canonical_sync_effect_policy(
            capability,
            declared_effect_class=effect_class,
        ).authoritative_effect_class,
        effect_policy=effect_policy_id(),
        payload_digest=canonical_payload_digest(payload),
        idempotency_key=idempotency_key,
        secret=_SECRET,
    )
    return token, payload


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
        if result.get("ok") and "authority_source" not in result:
            result = {**_canonical_claim_ack(self.client, msg["params"]), **result}

        async def _respond() -> None:
            await self.client._handle_message(
                json.dumps({"jsonrpc": "2.0", "result": result, "id": msg.get("id")})
            )

        asyncio.create_task(_respond())


def _durable_node_client(tmp_path, node_id: str = "windows-desktop"):
    from nodes.windows.umh_node.client import NodeClient
    from nodes.windows.umh_node.config import NodeConfig
    from substrate.execution.durable_remote_transport import DurableRemoteStore

    os.environ.setdefault("UMH_MESH_VERDICT_SECRET", _SECRET)
    client = object.__new__(NodeClient)
    client._config = NodeConfig(node_id=node_id)
    client._connected = True
    client._msg_id = 0
    client._pending_rpc = {}
    client._ws_send_lock = asyncio.Lock()
    client._durable_store = DurableRemoteStore(tmp_path)
    client._durable_processes = {}
    client._durable_execution_locks = {}
    client._durable_request_gates = {}
    client._durable_request_trajectories = {}
    client._media_queue = deque(maxlen=4)
    client._media_event = asyncio.Event()
    client._adapters = {}
    return client


def _durable_request(**overrides):
    from substrate.execution.durable_remote_transport import make_request

    params = {"command": "echo ok", "timeout": 5}
    data = {
        "correlation_id": "unit-durable",
        "candidate_sha": "abc123",
        "node_id": "windows-desktop",
        "operation_type": "transport_unit",
        "capability": "shell",
        "params": params,
        "risk_class": "read_only",
        "ttl_seconds": 60,
    }
    data.update(overrides)
    req = make_request(**data)
    executable_params = dict(req.params)
    verdict_digest = canonical_payload_digest(executable_params)
    req.params["governance_verdict_id"] = sign_verdict(
        verdict_id="unit-durable-verdict",
        node_id=req.node_id,
        capability=req.capability,
        risk_class=req.risk_class,
        request_id=req.request_id,
        correlation_id=req.correlation_id,
        candidate_sha=req.candidate_sha,
        effect_class=CONSEQUENTIAL_WRITE_EFFECT,
        authoritative_effect_class=canonical_sync_effect_policy(
            req.capability,
            declared_effect_class=CONSEQUENTIAL_WRITE_EFFECT,
        ).authoritative_effect_class,
        effect_policy=effect_policy_id(),
        payload_digest=verdict_digest,
        idempotency_key=req.idempotency_key,
        secret=_SECRET,
    )
    req.diagnostics["verdict_payload_digest"] = verdict_digest
    return req


def _canonical_claim_readback(client, payload):
    current = client._durable_store.get_request(str(payload["request_id"]))
    assert current is not None
    return {
        "ok": True,
        "accepted": True,
        "request_id": current.request_id,
        "correlation_id": current.correlation_id,
        "candidate_sha": current.candidate_sha,
        "node_id": current.node_id,
        "claim_id": current.claim_id,
        "lifecycle_state": current.lifecycle_state,
        "lease_expires_at": current.lease_expires_at,
        "process_tree": current.process_tree,
        "authority_source": "vps_canonical_durable_store",
    }


def _canonical_claim_ack(client, payload):
    state = str(payload.get("state", ""))
    request_id = str(payload["request_id"])
    claim_id = str(payload["claim_id"])
    process_tree = payload.get("process_tree")
    if state == "CLAIMED":
        client._durable_store.mark_claimed(
            request_id,
            claim_id=claim_id,
            process_tree=process_tree if isinstance(process_tree, dict) else None,
        )
    elif state == "RUNNING":
        client._durable_store.mark_running(
            request_id,
            claim_id=claim_id,
            process_tree=process_tree if isinstance(process_tree, dict) else None,
        )
    return {**_canonical_claim_readback(client, payload), "error": ""}


def test_mesh_pump_suppresses_same_request_redelivery_before_claim_progress(tmp_path):
    env = dict(os.environ)
    env["PYTHONPATH"] = _REPO_ROOT
    script = r"""
import asyncio
import json
import sys
import time

from substrate.execution.durable_remote_transport import DurableRemoteStore, make_request
from substrate.execution.executor import WorkPacketExecutor
from substrate.sockets.capability_socket import CapabilitySocket
from substrate.sockets.outcome_socket import OutcomeSocket
from substrate.sockets.signal_socket import SignalSocket
from substrate.sockets.view_socket import ViewSocket
from transports.node_mesh.config import MeshConfig
from transports.node_mesh.server import NodeMeshServer

store_path = sys.argv[1]

class Ws:
    def __init__(self) -> None:
        self.sent = []

    async def send(self, raw: str) -> None:
        self.sent.append(json.loads(raw))

class Registry:
    @staticmethod
    def owns(_node_id: str, _connection_id: str) -> bool:
        return True

server = NodeMeshServer(
    config=MeshConfig(),
    executor=WorkPacketExecutor(),
    signal_socket=SignalSocket(),
    capability_socket=CapabilitySocket(),
    outcome_socket=OutcomeSocket(),
    view_socket=ViewSocket(),
)
server._durable_store = DurableRemoteStore(store_path)
server._registry = Registry()
ws = Ws()
node_id = "windows-desktop"
connection_id = "conn-1"
req = make_request(
    correlation_id="unit-durable",
    candidate_sha="abc123",
    node_id=node_id,
    operation_type="transport_unit",
    capability="shell",
    params={
        "command": "echo ok",
        "timeout": 5,
        "budgets": {"claim_acquisition_timeout_s": 8.0},
    },
    risk_class="read_only",
    ttl_seconds=60,
)
server._durable_store.put_request(req)

async def main() -> dict[str, object]:
    await server._pump_durable_requests(node_id, ws, connection_id)
    current = server._durable_store.get_request(req.request_id)
    assert current is not None
    current.delivered_at = time.time() - 3.0
    server._durable_store._update_request_locked(current, "TEST_REDELIVERY_ELIGIBLE")
    await server._pump_durable_requests(node_id, ws, connection_id)
    current = server._durable_store.get_request(req.request_id)
    assert current is not None
    transport = current.diagnostics.get("transport_control", {})
    return {
        "sent": ws.sent,
        "delivery_attempts": current.delivery_attempts,
        "events": [event.get("event") for event in transport.get("events", [])],
    }

print(json.dumps(asyncio.run(main()), sort_keys=True))
"""
    result = subprocess.run(
        [sys.executable, "-c", script, str(tmp_path)],
        cwd=_REPO_ROOT,
        env=env,
        check=True,
        capture_output=True,
        text=True,
        timeout=20,
    )
    payload = json.loads(result.stdout)

    assert len(payload["sent"]) == 1
    assert payload["sent"][0]["method"] == "durable_command.request"
    assert payload["delivery_attempts"] == 1
    assert "delivery_suppressed" in payload["events"]


def test_node_rejects_write_class_without_verdict(monkeypatch):
    monkeypatch.setenv("UMH_MESH_VERDICT_SECRET", _SECRET)
    client = _bare_node_client("node-a")
    ok, reason = client._validate_verdict("shell.execute", "reversible_write", "")
    assert ok is False
    assert "effect" in reason.lower()


def test_node_rejects_write_class_with_invalid_verdict(monkeypatch):
    monkeypatch.setenv("UMH_MESH_VERDICT_SECRET", _SECRET)
    client = _bare_node_client("node-a")
    ok, reason = client._validate_verdict("shell.execute", "reversible_write", "v1.bogus.sig")
    assert ok is False


def test_node_rejects_verdict_bound_to_other_node(monkeypatch):
    monkeypatch.setenv("UMH_MESH_VERDICT_SECRET", _SECRET)
    # Token minted for node-b, but this node is node-a.
    token, params = _operation_bound_verdict(node_id="node-b")
    client = _bare_node_client("node-a")
    ok, reason = client._validate_verdict(
        "shell.execute",
        "reversible_write",
        token,
        request_id="req-1",
        correlation_id="corr-1",
        candidate_sha="a" * 40,
        effect_class="CONSEQUENTIAL_WRITE",
        payload_digest=canonical_payload_digest(params),
        idempotency_key="idem-1",
        cap_params=params,
        allow_consequential_write=True,
    )
    assert ok is False
    assert "node mismatch" in reason


def test_node_rejects_valid_write_class_verdict_on_sync_path(monkeypatch):
    monkeypatch.setenv("UMH_MESH_VERDICT_SECRET", _SECRET)
    token, params = _operation_bound_verdict()
    client = _bare_node_client("node-a")
    ok, reason = client._validate_verdict(
        "shell.execute",
        "reversible_write",
        token,
        request_id="req-1",
        correlation_id="corr-1",
        candidate_sha="a" * 40,
        effect_class="CONSEQUENTIAL_WRITE",
        payload_digest=canonical_payload_digest(params),
        idempotency_key="idem-1",
        cap_params=params,
    )
    assert ok is False
    assert "DurableRemote" in reason


def test_node_accepts_valid_write_class_verdict_only_for_durable_remote(monkeypatch):
    monkeypatch.setenv("UMH_MESH_VERDICT_SECRET", _SECRET)
    token, params = _operation_bound_verdict()
    client = _bare_node_client("node-a")
    ok, reason = client._validate_verdict(
        "shell.execute",
        "reversible_write",
        token,
        request_id="req-1",
        correlation_id="corr-1",
        candidate_sha="a" * 40,
        effect_class="CONSEQUENTIAL_WRITE",
        payload_digest=canonical_payload_digest(params),
        idempotency_key="idem-1",
        cap_params=params,
        allow_consequential_write=True,
    )
    assert ok is True


def test_node_rejects_operation_bound_verdict_for_stale_payload(monkeypatch):
    monkeypatch.setenv("UMH_MESH_VERDICT_SECRET", _SECRET)
    token, _params = _operation_bound_verdict(params={"argv": ["echo", "old"]})
    changed = {"argv": ["echo", "new"]}
    client = _bare_node_client("node-a")

    ok, reason = client._validate_verdict(
        "shell.execute",
        "reversible_write",
        token,
        request_id="req-1",
        correlation_id="corr-1",
        candidate_sha="a" * 40,
        effect_class="CONSEQUENTIAL_WRITE",
        payload_digest=canonical_payload_digest(changed),
        idempotency_key="idem-1",
        cap_params=changed,
        allow_consequential_write=True,
    )

    assert ok is False
    assert "payload_digest mismatch" in reason


def test_node_sync_receiver_rejects_replayed_consequential_frame(monkeypatch):
    monkeypatch.setenv("UMH_MESH_VERDICT_SECRET", _SECRET)
    token, params = _operation_bound_verdict(capability="shell", params={"argv": ["echo", "x"]})
    client = _sync_node_client("node-a")
    calls = {"count": 0}

    class _Adapter:
        def execute(self, *_args, **_kwargs):
            calls["count"] += 1
            return {"success": True, "result_data": {"stdout": "executed"}}

    client._adapters = {"shell": _Adapter()}
    frame = {
        "jsonrpc": "2.0",
        "method": "capability.execute",
        "id": "req-1",
        "params": {
            "request_id": "req-1",
            "correlation_id": "corr-1",
            "candidate_sha": "a" * 40,
            "effect_class": "CONSEQUENTIAL_WRITE",
            "idempotency_key": "idem-1",
            "payload_digest": canonical_payload_digest(params),
            "capability_name": "shell",
            "params": params,
            "risk_class": "reversible_write",
            "governance_verdict_id": token,
            "timeout_seconds": 1,
        },
    }

    asyncio.run(client._handle_capability(frame))
    asyncio.run(client._handle_capability(frame))

    assert calls["count"] == 0
    assert len(client._sent_ws) == 2
    assert all(msg["result"]["success"] is False for msg in client._sent_ws)
    assert all("DurableRemote" in msg["result"]["error"] for msg in client._sent_ws)


def test_node_rejects_shell_declared_read_only_before_adapter(monkeypatch):
    monkeypatch.setenv("UMH_MESH_VERDICT_SECRET", _SECRET)
    client = _sync_node_client("node-a")
    calls = {"count": 0}

    class _Adapter:
        def execute(self, *_args, **_kwargs):
            calls["count"] += 1
            return {"success": True, "result_data": {"stdout": "executed"}}

    params = {"argv": ["echo", "x"]}
    client._adapters = {"shell": _Adapter()}
    frame = {
        "jsonrpc": "2.0",
        "method": "capability.execute",
        "id": "req-lying",
        "params": {
            "request_id": "req-lying",
            "correlation_id": "corr-lying",
            "candidate_sha": "a" * 40,
            "effect_class": READ_ONLY_EFFECT,
            "idempotency_key": "req-lying",
            "payload_digest": canonical_payload_digest(params),
            "capability_name": "shell",
            "params": params,
            "risk_class": "read_only",
            "governance_verdict_id": "",
            "timeout_seconds": 1,
        },
    }

    asyncio.run(client._handle_capability(frame))

    assert calls["count"] == 0
    assert client._sent_ws[0]["result"]["success"] is False
    assert "policy mismatch" in client._sent_ws[0]["result"]["error"]


def test_node_allows_read_only_without_verdict(monkeypatch):
    monkeypatch.setenv("UMH_MESH_VERDICT_SECRET", _SECRET)
    params = {"name": "s1"}
    client = _bare_node_client("node-a")
    ok, reason = client._validate_verdict(
        "terminal.capture",
        "read_only",
        "",
        request_id="req-read",
        correlation_id="corr-read",
        effect_class=READ_ONLY_EFFECT,
        payload_digest=canonical_payload_digest(params),
        idempotency_key="req-read",
        cap_params=params,
    )
    assert ok is True


def test_node_rejects_declared_consequential_for_canonical_read_only(monkeypatch):
    monkeypatch.setenv("UMH_MESH_VERDICT_SECRET", _SECRET)
    params = {"name": "s1"}
    client = _bare_node_client("node-a")
    ok, reason = client._validate_verdict(
        "terminal.capture",
        "read_only",
        "",
        request_id="req-read",
        correlation_id="corr-read",
        effect_class=CONSEQUENTIAL_WRITE_EFFECT,
        payload_digest=canonical_payload_digest(params),
        idempotency_key="req-read",
        cap_params=params,
    )
    assert ok is False
    assert "policy mismatch" in reason


def test_node_rejects_unknown_sync_effect(monkeypatch):
    monkeypatch.setenv("UMH_MESH_VERDICT_SECRET", _SECRET)
    client = _bare_node_client("node-a")
    ok, reason = client._validate_verdict("terminal.capture", "read_only", "")
    assert ok is False
    assert "effect" in reason.lower()


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
    ok, reason = client._validate_verdict(
        "shell.execute",
        "read_only",
        "",
        effect_class=READ_ONLY_EFFECT,
    )
    assert ok is False
    assert "policy mismatch" in reason.lower()


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
    assert [msg.get("method") for msg in ws.sent] == [
        "durable_command.claimed",
        "durable_command.result",
    ]
    result = client._durable_store.result_for(req.request_id)
    assert result is not None
    assert result["state"] == "FAILED"
    assert result["cleanup"]["process_residue"] == []


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


def test_durable_node_running_ack_timeout_reads_back_running_before_execution(
    tmp_path, monkeypatch
):
    from nodes.windows.umh_node import client as client_mod
    from nodes.windows.umh_node.config import CapabilityConfig

    client = _durable_node_client(tmp_path)
    client._ws = _DurableAckWs(client)
    client._config.capabilities = {
        "dummy": CapabilityConfig(enabled=True, max_risk_class="read_only")
    }
    monkeypatch.setattr(client_mod, "_DURABLE_CLAIM_RETRY_SLEEP_S", 0.0)
    executed = False
    methods: list[tuple[str, str]] = []

    class _Adapter:
        def execute(self, *_args, **_kwargs):
            nonlocal executed
            executed = True
            return {"success": True, "stdout": "ran"}

    async def _send_event(method, payload, **_kwargs):
        methods.append((method, str(payload.get("state", ""))))
        if method == "durable_command.claimed" and payload.get("state") == "CLAIMED":
            return _canonical_claim_ack(client, payload)
        if method == "durable_command.claimed" and payload.get("state") == "RUNNING":
            return {"ok": False, "error": "durable_command.claimed acknowledgement timed out"}
        return {"ok": True, "error": ""}

    readbacks: list[tuple[str, str]] = []

    async def _readback(payload, **_kwargs):
        readbacks.append((str(payload.get("request_id", "")), str(payload.get("state", ""))))
        return _canonical_claim_readback(client, payload)

    client._adapters = {"dummy": _Adapter()}
    monkeypatch.setattr(client, "_send_durable_event", _send_event)
    monkeypatch.setattr(client, "_read_canonical_durable_claim_state", _readback)
    req = _durable_request(capability="dummy.execute", params={}, risk_class="read_only")

    asyncio.run(
        client._handle_durable_command(
            {"method": "durable_command.request", "params": req.to_dict()}
        )
    )

    assert executed is True
    assert ("durable_command.claimed", "RUNNING") in methods
    assert (req.request_id, "RUNNING") in readbacks
    result = client._durable_store.result_for(req.request_id)
    assert result is not None
    assert result["state"] == "SUCCEEDED"


def test_durable_same_request_redeliveries_coalesce_before_claim_settles(
    tmp_path, monkeypatch
):
    client = _durable_node_client(tmp_path / "store")
    client._ws = _DurableAckWs(client)
    req = _durable_request()
    acquire_started = asyncio.Event()
    release_acquire = asyncio.Event()
    acquire_calls = 0
    execute_calls = 0

    async def _acquire(current, *, claim_id, process_tree):
        nonlocal acquire_calls
        acquire_calls += 1
        acquire_started.set()
        await release_acquire.wait()
        return {
            "ok": True,
            "claim_id": claim_id,
            "lifecycle_state": "CLAIMED",
            "process_tree": process_tree,
        }

    async def _execute(*_args, **_kwargs):
        nonlocal execute_calls
        execute_calls += 1
        return {"success": True, "stdout": "ok", "cleanup": {"process_residue": []}}

    monkeypatch.setattr(client, "_acquire_durable_claim", _acquire)
    monkeypatch.setattr(client, "_execute_capability_for_durable", _execute)

    async def _run() -> None:
        first = asyncio.create_task(
            client._handle_durable_command(
                {"method": "durable_command.request", "params": req.to_dict()}
            )
        )
        await asyncio.wait_for(acquire_started.wait(), timeout=1)
        duplicates = [
            asyncio.create_task(
                client._handle_durable_command(
                    {"method": "durable_command.request", "params": req.to_dict()}
                )
            )
            for _ in range(8)
        ]
        await asyncio.sleep(0)
        release_acquire.set()
        await asyncio.gather(first, *duplicates)

    asyncio.run(_run())

    result = client._durable_store.result_for(req.request_id)
    assert result is not None
    assert result["state"] == "SUCCEEDED"
    assert acquire_calls == 1
    assert execute_calls == 1
    assert client._durable_request_gates == {}


def test_durable_same_request_queued_redeliveries_do_not_reacquire_after_fail_closed(
    tmp_path, monkeypatch
):
    client = _durable_node_client(tmp_path / "store")
    client._ws = _DurableAckWs(client)
    req = _durable_request()
    acquire_started = asyncio.Event()
    release_acquire = asyncio.Event()
    acquire_calls: list[str] = []
    claim_ids: list[str] = []
    result_events: list[dict] = []

    async def _acquire(current, *, claim_id, process_tree):
        acquire_calls.append(current.request_id)
        claim_ids.append(claim_id)
        acquire_started.set()
        await release_acquire.wait()
        return {
            "ok": False,
            "error": "synthetic unresolved claim authority",
            "claim_id": claim_id,
            "attempts": [{"method": "unit", "ok": False}],
        }

    async def _send_event(method, payload, **kwargs):
        if method == "durable_command.result":
            result_events.append(dict(payload))
        return {"ok": True, "accepted": True}

    monkeypatch.setattr(client, "_acquire_durable_claim", _acquire)
    monkeypatch.setattr(client, "_send_durable_event", _send_event)

    async def _run() -> None:
        first = asyncio.create_task(
            client._handle_durable_command(
                {"method": "durable_command.request", "params": req.to_dict()}
            )
        )
        await asyncio.wait_for(acquire_started.wait(), timeout=1)
        duplicates = [
            asyncio.create_task(
                client._handle_durable_command(
                    {"method": "durable_command.request", "params": req.to_dict()}
                )
            )
            for _ in range(6)
        ]
        await asyncio.sleep(0)
        release_acquire.set()
        await asyncio.gather(first, *duplicates)

    asyncio.run(_run())

    result = client._durable_store.result_for(req.request_id)
    assert result is not None
    assert result["state"] == "FAILED"
    assert acquire_calls == [req.request_id]
    assert len(set(claim_ids)) == 1
    assert result_events
    assert all(event.get("idempotent_replay") or event["state"] == "FAILED" for event in result_events)
    trajectory = client._durable_request_trajectories[req.request_id]
    assert trajectory["status"] in {"FAIL_CLOSED", "TERMINAL_OBSERVED"}
    assert trajectory["claim_id"] == claim_ids[0]
    assert client._durable_request_gates == {}


def test_durable_fail_closed_trajectory_never_authorizes_same_claim_execution(
    tmp_path, monkeypatch
):
    client = _durable_node_client(tmp_path / "store")
    client._ws = _DurableAckWs(client)
    req = client._durable_store.put_request(_durable_request())
    claim_id = "windows-desktop-retained-claim"
    process_tree = {"node_pid": 123, "claimed_at": time.time()}
    client._durable_store.mark_claimed(
        req.request_id,
        claim_id=claim_id,
        process_tree=process_tree,
    )
    trajectory = client._durable_request_trajectory(req)
    trajectory["claim_id"] = claim_id
    trajectory["status"] = "FAIL_CLOSED"
    execute_calls = 0

    async def _execute(*_args, **_kwargs):
        nonlocal execute_calls
        execute_calls += 1
        return {"success": True, "stdout": "should-not-run", "cleanup": {"process_residue": []}}

    monkeypatch.setattr(client, "_execute_capability_for_durable", _execute)

    asyncio.run(
        client._handle_durable_command(
            {"method": "durable_command.request", "params": req.to_dict()}
        )
    )

    result = client._durable_store.result_for(req.request_id)
    assert result is not None
    assert result["state"] == "FAILED"
    assert result["claim_id"] == claim_id
    assert execute_calls == 0
    assert client._durable_request_trajectories[req.request_id]["status"] == "FAIL_CLOSED"


def test_durable_interrupted_acquisition_fail_closes_before_late_duplicate(
    tmp_path, monkeypatch
):
    client = _durable_node_client(tmp_path / "store")
    client._ws = _DurableAckWs(client)
    req = _durable_request()
    acquire_calls = 0
    execute_calls = 0

    async def _acquire(current, *, claim_id, process_tree):
        nonlocal acquire_calls
        acquire_calls += 1
        raise RuntimeError("synthetic interruption after claimed persistence")

    async def _execute(*_args, **_kwargs):
        nonlocal execute_calls
        execute_calls += 1
        return {"success": True, "stdout": "should-not-run", "cleanup": {"process_residue": []}}

    monkeypatch.setattr(client, "_acquire_durable_claim", _acquire)
    monkeypatch.setattr(client, "_execute_capability_for_durable", _execute)

    asyncio.run(
        client._handle_durable_command(
            {"method": "durable_command.request", "params": req.to_dict()}
        )
    )
    asyncio.run(
        client._handle_durable_command(
            {"method": "durable_command.request", "params": req.to_dict()}
        )
    )

    result = client._durable_store.result_for(req.request_id)
    assert result is not None
    assert result["state"] == "FAILED"
    assert result["cleanup"]["process_residue"] == []
    assert result["cleanup"]["claim_acquisition_failed_closed"] is True
    assert acquire_calls == 1
    assert execute_calls == 0
    assert client._durable_request_trajectories[req.request_id]["status"] == "TERMINAL_OBSERVED"
    assert client._durable_request_gates == {}


def test_durable_cancelled_acquisition_fail_closes_before_late_duplicate(
    tmp_path, monkeypatch
):
    client = _durable_node_client(tmp_path / "store")
    client._ws = _DurableAckWs(client)
    req = _durable_request()
    acquire_started = asyncio.Event()
    release_acquire = asyncio.Event()
    acquire_calls = 0
    execute_calls = 0

    async def _acquire(current, *, claim_id, process_tree):
        nonlocal acquire_calls
        acquire_calls += 1
        acquire_started.set()
        await release_acquire.wait()
        return {
            "ok": True,
            "claim_id": claim_id,
            "lifecycle_state": "CLAIMED",
            "process_tree": process_tree,
        }

    async def _execute(*_args, **_kwargs):
        nonlocal execute_calls
        execute_calls += 1
        return {"success": True, "stdout": "should-not-run", "cleanup": {"process_residue": []}}

    monkeypatch.setattr(client, "_acquire_durable_claim", _acquire)
    monkeypatch.setattr(client, "_execute_capability_for_durable", _execute)

    async def _run() -> None:
        first = asyncio.create_task(
            client._handle_durable_command(
                {"method": "durable_command.request", "params": req.to_dict()}
            )
        )
        await asyncio.wait_for(acquire_started.wait(), timeout=1)
        first.cancel()
        with pytest.raises(asyncio.CancelledError):
            await first
        release_acquire.set()
        await client._handle_durable_command(
            {"method": "durable_command.request", "params": req.to_dict()}
        )

    asyncio.run(_run())

    result = client._durable_store.result_for(req.request_id)
    assert result is not None
    assert result["state"] == "FAILED"
    assert result["cleanup"]["process_residue"] == []
    assert result["cleanup"]["claim_acquisition_failed_closed"] is True
    assert acquire_calls == 1
    assert execute_calls == 0
    assert client._durable_request_trajectories[req.request_id]["status"] == "TERMINAL_OBSERVED"


def test_durable_cancelled_running_trajectory_terminates_owned_process(
    tmp_path, monkeypatch
):
    client = _durable_node_client(tmp_path / "store")
    client._ws = _DurableAckWs(client)
    req = client._durable_store.put_request(_durable_request())
    claim_id = "windows-desktop-running-claim"
    proc = subprocess.Popen(
        ["sleep", "30"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        start_new_session=True,
    )
    try:
        process_tree = {"node_pid": 123, "claimed_at": time.time(), "root_pid": proc.pid}
        client._durable_store.mark_claimed(
            req.request_id,
            claim_id=claim_id,
            process_tree={"node_pid": 123, "claimed_at": process_tree["claimed_at"]},
        )
        running = client._durable_store.mark_running(
            req.request_id,
            claim_id=claim_id,
            process_tree=process_tree,
        )
        client._durable_processes[req.request_id] = proc
        trajectory = client._durable_request_trajectory(running)
        trajectory["claim_id"] = claim_id
        trajectory["status"] = "RUNNING_OR_RECONCILING"
        result_events: list[dict] = []

        async def _send_event(method, payload, **kwargs):
            if method == "durable_command.result":
                result_events.append(dict(payload))
            return {"ok": True, "accepted": True}

        monkeypatch.setattr(client, "_send_durable_event", _send_event)

        asyncio.run(
            client._fail_interrupted_durable_request_trajectory(
                running,
                trajectory=trajectory,
                exc=asyncio.CancelledError(),
            )
        )

        result = client._durable_store.result_for(req.request_id)
        assert result is not None
        assert result["state"] == "FAILED"
        assert result["cleanup"]["interrupted_running_failed_closed"] is True
        assert result["cleanup"]["process_residue"] == []
        assert proc.poll() is not None
        assert result_events
    finally:
        if proc.poll() is None:
            proc.kill()
            proc.wait(timeout=5)


def test_durable_handle_cancellation_after_shell_start_terminalizes_and_cleans_process(
    tmp_path
):
    client = _durable_node_client(tmp_path / "store")
    client._ws = _DurableAckWs(client)
    client._adapters = {"shell": object()}
    req = _durable_request(params={"argv": ["sleep", "30"], "timeout": 30})

    async def _run() -> None:
        task = asyncio.create_task(
            client._handle_durable_command(
                {"method": "durable_command.request", "params": req.to_dict()}
            )
        )
        deadline = time.monotonic() + 3.0
        proc = None
        while time.monotonic() < deadline:
            proc = client._durable_processes.get(req.request_id)
            if proc is not None and proc.poll() is None:
                break
            await asyncio.sleep(0.05)
        assert proc is not None
        assert proc.poll() is None
        task.cancel()
        await task
        return proc

    proc = asyncio.run(_run())

    result = client._durable_store.result_for(req.request_id)
    assert result is not None
    assert result["state"] == "FAILED"
    assert result["cleanup"]["interrupted_running_failed_closed"] is True
    assert result["cleanup"]["process_residue"] == []
    assert proc.poll() is not None
    assert client._durable_processes.get(req.request_id) is None


def test_durable_terminal_canonical_truth_overrides_local_fail_closed_tombstone(
    tmp_path, monkeypatch
):
    client = _durable_node_client(tmp_path / "store")
    client._ws = _DurableAckWs(client)
    req = client._durable_store.put_request(_durable_request())
    claim_id = "windows-desktop-terminal-claim"
    process_tree = {"node_pid": 123, "claimed_at": time.time()}
    client._durable_store.mark_claimed(
        req.request_id,
        claim_id=claim_id,
        process_tree=process_tree,
    )
    client._durable_store.publish_result(
        req.request_id,
        claim_id=claim_id,
        state="SUCCEEDED",
        result={"success": True, "stdout": "done"},
        cleanup={"process_residue": []},
    )
    trajectory = client._durable_request_trajectory(req)
    trajectory["claim_id"] = claim_id
    trajectory["status"] = "FAIL_CLOSED"

    asyncio.run(
        client._handle_durable_command(
            {"method": "durable_command.request", "params": req.to_dict()}
        )
    )

    result = client._durable_store.result_for(req.request_id)
    assert result is not None
    assert result["state"] == "SUCCEEDED"
    assert client._durable_request_trajectories[req.request_id]["status"] == "TERMINAL_OBSERVED"


def test_durable_trajectory_identity_mismatch_fails_closed_with_evidence(
    tmp_path, monkeypatch
):
    client = _durable_node_client(tmp_path / "store")
    client._ws = _DurableAckWs(client)
    req = _durable_request()
    trajectory = client._durable_request_trajectory(req)
    foreign = _durable_request()
    foreign.request_id = req.request_id
    foreign.idempotency_key = req.idempotency_key
    foreign.payload_digest = req.payload_digest
    foreign.correlation_id = "foreign-correlation"
    result_events: list[dict] = []

    async def _send_event(method, payload, **kwargs):
        if method == "durable_command.result":
            result_events.append(dict(payload))
        return {"ok": True, "accepted": True}

    monkeypatch.setattr(client, "_send_durable_event", _send_event)

    asyncio.run(client._handle_durable_command_locked(foreign, trajectory))

    result = client._durable_store.result_for(foreign.request_id)
    assert result is not None
    assert result["state"] == "FAILED"
    assert "identity mismatch" in result["result"]["reason"]
    assert result["cleanup"]["process_residue"] == []
    assert result_events


def test_durable_distinct_requests_keep_concurrent_claim_acquisition(
    tmp_path, monkeypatch
):
    client = _durable_node_client(tmp_path / "store")
    client._ws = _DurableAckWs(client)
    req_a = _durable_request()
    req_a.request_id = "drc-a"
    req_a.idempotency_key = "drc-a"
    req_b = _durable_request()
    req_b.request_id = "drc-b"
    req_b.idempotency_key = "drc-b"
    started: set[str] = set()
    both_started = asyncio.Event()
    release_acquire = asyncio.Event()
    execute_calls: list[str] = []

    async def _acquire(current, *, claim_id, process_tree):
        started.add(current.request_id)
        if started == {req_a.request_id, req_b.request_id}:
            both_started.set()
        await release_acquire.wait()
        return {
            "ok": True,
            "claim_id": claim_id,
            "lifecycle_state": "CLAIMED",
            "process_tree": process_tree,
        }

    async def _execute(current, **_kwargs):
        execute_calls.append(current.request_id)
        return {"success": True, "stdout": current.request_id, "cleanup": {"process_residue": []}}

    monkeypatch.setattr(client, "_acquire_durable_claim", _acquire)
    monkeypatch.setattr(client, "_execute_capability_for_durable", _execute)

    async def _run() -> None:
        tasks = [
            asyncio.create_task(
                client._handle_durable_command(
                    {"method": "durable_command.request", "params": req_a.to_dict()}
                )
            ),
            asyncio.create_task(
                client._handle_durable_command(
                    {"method": "durable_command.request", "params": req_b.to_dict()}
                )
            ),
        ]
        await asyncio.wait_for(both_started.wait(), timeout=1)
        release_acquire.set()
        await asyncio.gather(*tasks)

    asyncio.run(_run())

    assert set(execute_calls) == {req_a.request_id, req_b.request_id}
    assert client._durable_store.result_for(req_a.request_id)["state"] == "SUCCEEDED"
    assert client._durable_store.result_for(req_b.request_id)["state"] == "SUCCEEDED"
    assert client._durable_request_gates == {}


def test_durable_cancel_redelivery_updates_store_while_execution_gate_is_held(
    tmp_path, monkeypatch
):
    client = _durable_node_client(tmp_path / "store")
    client._ws = _DurableAckWs(client)
    req = _durable_request()
    execute_started = asyncio.Event()
    release_execute = asyncio.Event()
    execute_calls = 0

    async def _execute(*_args, **_kwargs):
        nonlocal execute_calls
        execute_calls += 1
        execute_started.set()
        await release_execute.wait()
        return {"success": False, "error": "cancelled", "cleanup": {"process_residue": []}}

    monkeypatch.setattr(client, "_execute_capability_for_durable", _execute)

    async def _run() -> None:
        first = asyncio.create_task(
            client._handle_durable_command(
                {"method": "durable_command.request", "params": req.to_dict()}
            )
        )
        await asyncio.wait_for(execute_started.wait(), timeout=1)
        current = client._durable_store.get_request(req.request_id)
        assert current is not None
        cancel = current
        cancel.lifecycle_state = "CANCEL_REQUESTED"
        cancel.cancellation_requested_at = time.time()
        cancel.cancellation_deadline_at = cancel.cancellation_requested_at + 30.0
        cancel_task = asyncio.create_task(
            client._handle_durable_command(
                {"method": "durable_command.request", "params": cancel.to_dict()}
            )
        )
        await asyncio.sleep(0)
        observed = client._durable_store.get_request(req.request_id)
        assert observed is not None
        assert observed.lifecycle_state == "CANCEL_REQUESTED"
        release_execute.set()
        await asyncio.gather(first, cancel_task)

    asyncio.run(_run())

    assert execute_calls == 1
    assert client._durable_request_gates == {}


def test_durable_node_missing_running_ack_reads_back_running_before_execution(
    tmp_path, monkeypatch
):
    from nodes.windows.umh_node.config import CapabilityConfig

    client = _durable_node_client(tmp_path)
    client._ws = _DurableAckWs(client)
    client._config.capabilities = {
        "dummy": CapabilityConfig(enabled=True, max_risk_class="read_only")
    }
    executed = False

    class _Adapter:
        def execute(self, *_args, **_kwargs):
            nonlocal executed
            executed = True
            return {"success": True, "stdout": "ran"}

    async def _send_event(method, payload, **_kwargs):
        if method == "durable_command.claimed" and payload.get("state") == "CLAIMED":
            return {"ok": True, "error": ""}
        if method == "durable_command.claimed" and payload.get("state") == "RUNNING":
            return None
        return {"ok": True, "error": ""}

    async def _readback(payload, **_kwargs):
        return _canonical_claim_readback(client, payload)

    client._adapters = {"dummy": _Adapter()}
    monkeypatch.setattr(client, "_send_durable_event", _send_event)
    monkeypatch.setattr(client, "_read_canonical_durable_claim_state", _readback)
    req = _durable_request(capability="dummy.execute", params={}, risk_class="read_only")

    asyncio.run(
        client._handle_durable_command(
            {"method": "durable_command.request", "params": req.to_dict()}
        )
    )

    assert executed is True
    result = client._durable_store.result_for(req.request_id)
    assert result is not None
    assert result["state"] == "SUCCEEDED"


def test_durable_node_running_ack_timeout_rejected_readback_does_not_execute(
    tmp_path, monkeypatch
):
    from nodes.windows.umh_node import client as client_mod
    from nodes.windows.umh_node.config import CapabilityConfig

    client = _durable_node_client(tmp_path)
    client._ws = _DurableAckWs(client)
    client._config.capabilities = {
        "dummy": CapabilityConfig(enabled=True, max_risk_class="read_only")
    }
    monkeypatch.setattr(client_mod, "_DURABLE_CLAIM_RETRY_SLEEP_S", 0.0)
    executed = False

    class _Adapter:
        def execute(self, *_args, **_kwargs):
            nonlocal executed
            executed = True
            return {"success": True, "stdout": "ran"}

    async def _send_event(method, payload, **_kwargs):
        if method == "durable_command.claimed" and payload.get("state") == "CLAIMED":
            return _canonical_claim_ack(client, payload)
        if method == "durable_command.claimed" and payload.get("state") == "RUNNING":
            return {"ok": False, "error": "durable_command.claimed acknowledgement timed out"}
        return {"ok": True, "error": ""}

    client._adapters = {"dummy": _Adapter()}
    monkeypatch.setattr(client, "_send_durable_event", _send_event)

    async def _readback(_payload, **_kwargs):
        return {
            "ok": False,
            "accepted": False,
            "error": "claim readback mismatch: lifecycle_state",
            "retryable": False,
        }

    monkeypatch.setattr(client, "_read_canonical_durable_claim_state", _readback)
    req = _durable_request(capability="dummy.execute", params={}, risk_class="read_only")

    asyncio.run(
        client._handle_durable_command(
            {"method": "durable_command.request", "params": req.to_dict()}
        )
    )

    assert executed is False
    result = client._durable_store.result_for(req.request_id)
    assert result is not None
    assert result["state"] == "FAILED"
    assert "running acknowledgement rejected" in result["result"]["error"]


def test_durable_bare_running_ack_with_retryable_readback_does_not_execute(
    tmp_path, monkeypatch
):
    from nodes.windows.umh_node.config import CapabilityConfig

    executed = False
    client = _durable_node_client(tmp_path)
    client._ws = _DurableAckWs(client)
    client._config.capabilities = {
        "dummy": CapabilityConfig(enabled=True, max_risk_class="read_only")
    }

    class _Adapter:
        def execute(self, *_args, **_kwargs):
            nonlocal executed
            executed = True
            return {"success": True, "stdout": "ran"}

    async def _send_event(method, payload, **_kwargs):
        if method == "durable_command.claimed" and payload.get("state") == "CLAIMED":
            return _canonical_claim_ack(client, payload)
        if method == "durable_command.claimed" and payload.get("state") == "RUNNING":
            return {"ok": True, "error": ""}
        return {"ok": True, "error": ""}

    async def _readback(_payload, **_kwargs):
        return {
            "ok": False,
            "accepted": False,
            "error": "canonical running state unavailable",
            "retryable": True,
        }

    client._adapters = {"dummy": _Adapter()}
    monkeypatch.setattr(client, "_send_durable_event", _send_event)
    monkeypatch.setattr(client, "_read_canonical_durable_claim_state", _readback)
    req = _durable_request(capability="dummy.execute", params={}, risk_class="read_only")

    asyncio.run(
        client._handle_durable_command(
            {"method": "durable_command.request", "params": req.to_dict()}
        )
    )

    assert executed is False
    result = client._durable_store.result_for(req.request_id)
    assert result is not None
    assert result["state"] == "FAILED"
    assert "canonical running state unavailable" in result["result"]["error"]


def test_durable_control_send_waits_for_shared_ws_send_lock(tmp_path):
    client = _durable_node_client(tmp_path)

    class _Ws:
        def __init__(self) -> None:
            self.sent: list[dict[str, object]] = []

        async def send(self, raw: str) -> None:
            msg = json.loads(raw)
            self.sent.append(msg)
            await client._handle_message(
                json.dumps(
                    {
                        "jsonrpc": "2.0",
                        "result": {"ok": True, "error": ""},
                        "id": msg.get("id"),
                    }
                )
            )

    async def _run() -> tuple[list[dict[str, object]], dict[str, object], bool]:
        assert client._ws_send_lock is not None
        await client._ws_send_lock.acquire()
        client._ws = _Ws()
        task = asyncio.create_task(
            client._send_durable_event(
                "durable_command.claimed",
                {"request_id": "req-1", "claim_id": "claim-1", "state": "CLAIMED"},
                expect_ack=True,
                timeout_s=1.0,
            )
        )
        await asyncio.sleep(0)
        blocked_without_send = not client._ws.sent
        client._ws_send_lock.release()
        ack = await task
        return client._ws.sent, ack or {}, blocked_without_send

    sent, ack, blocked_without_send = asyncio.run(_run())
    assert blocked_without_send is True
    assert sent[0]["method"] == "durable_command.claimed"
    assert ack["ok"] is True


def test_node_client_has_no_ws_send_path_outside_shared_helper() -> None:
    source = open(
        os.path.join(_REPO_ROOT, "nodes", "windows", "umh_node", "client.py"),
        encoding="utf-8",
    ).read()
    assert "async def _send_ws" in source
    assert source.count("await self._ws.send(") == 2


def test_durable_ack_delayed_inside_timeout_succeeds(tmp_path):
    client = _durable_node_client(tmp_path)

    class _Ws:
        async def send(self, raw: str) -> None:
            msg = json.loads(raw)

            async def _respond() -> None:
                await asyncio.sleep(0.02)
                await client._handle_message(
                    json.dumps(
                        {
                            "jsonrpc": "2.0",
                            "result": {"ok": True, "error": ""},
                            "id": msg.get("id"),
                        }
                    )
                )

            asyncio.create_task(_respond())

    async def _run() -> dict[str, object]:
        client._ws = _Ws()
        return await client._send_durable_event(
            "durable_command.claimed",
            {"request_id": "req-1", "claim_id": "claim-1", "state": "CLAIMED"},
            expect_ack=True,
            timeout_s=0.2,
        ) or {}

    assert asyncio.run(_run())["ok"] is True


def test_durable_ack_timeout_is_bounded_and_next_send_can_proceed(tmp_path):
    client = _durable_node_client(tmp_path)

    class _Ws:
        def __init__(self) -> None:
            self.sent: list[dict[str, object]] = []
            self.respond = False

        async def send(self, raw: str) -> None:
            msg = json.loads(raw)
            self.sent.append(msg)
            if self.respond:
                await client._handle_message(
                    json.dumps(
                        {
                            "jsonrpc": "2.0",
                            "result": {"ok": True, "error": ""},
                            "id": msg.get("id"),
                        }
                    )
                )

    async def _run() -> tuple[dict[str, object], dict[str, object], int]:
        ws = _Ws()
        client._ws = ws
        first = await client._send_durable_event(
            "durable_command.claimed",
            {"request_id": "req-1", "claim_id": "claim-1", "state": "CLAIMED"},
            expect_ack=True,
            timeout_s=0.01,
        )
        ws.respond = True
        second = await client._send_durable_event(
            "durable_command.claimed",
            {"request_id": "req-2", "claim_id": "claim-2", "state": "CLAIMED"},
            expect_ack=True,
            timeout_s=0.2,
        )
        return first or {}, second or {}, len(ws.sent)

    first, second, sent_count = asyncio.run(_run())
    assert first["ok"] is False
    assert "timed out" in str(first["error"])
    assert second["ok"] is True
    assert sent_count == 2


def test_ws_send_exception_and_cancellation_do_not_deadlock(tmp_path):
    client = _durable_node_client(tmp_path)

    class _Ws:
        def __init__(self) -> None:
            self.fail_next = True
            self.sent: list[str | bytes] = []

        async def send(self, raw: str | bytes) -> None:
            if self.fail_next:
                self.fail_next = False
                raise OSError("synthetic send failure")
            self.sent.append(raw)

    async def _run() -> list[str | bytes]:
        assert client._ws_send_lock is not None
        client._ws = _Ws()
        try:
            await client._send_ws("first")
        except OSError:
            pass
        await client._send_ws("second")
        await client._ws_send_lock.acquire()
        blocked = asyncio.create_task(client._send_ws("cancelled"))
        await asyncio.sleep(0)
        blocked.cancel()
        try:
            await blocked
        except asyncio.CancelledError:
            pass
        client._ws_send_lock.release()
        await client._send_ws("third")
        return client._ws.sent

    assert asyncio.run(_run()) == ["second", "third"]


def test_durable_event_send_exception_cleans_pending_rpc(tmp_path):
    client = _durable_node_client(tmp_path)

    class _FailingWs:
        async def send(self, _raw: str) -> None:
            raise OSError("synthetic durable send failure")

    async def _run() -> dict[object, object]:
        client._ws = _FailingWs()
        try:
            await client._send_durable_event(
                "durable_command.claimed",
                {"request_id": "req-1", "claim_id": "claim-1", "state": "CLAIMED"},
                expect_ack=True,
                timeout_s=0.2,
            )
        except OSError:
            pass
        return client._pending_rpc

    assert asyncio.run(_run()) == {}


def test_durable_event_cancellation_while_waiting_cleans_pending_rpc(tmp_path):
    client = _durable_node_client(tmp_path)

    class _SilentWs:
        async def send(self, _raw: str) -> None:
            return None

    async def _run() -> dict[object, object]:
        client._ws = _SilentWs()
        task = asyncio.create_task(
            client._send_durable_event(
                "durable_command.claimed",
                {"request_id": "req-1", "claim_id": "claim-1", "state": "CLAIMED"},
                expect_ack=True,
                timeout_s=10.0,
            )
        )
        await asyncio.sleep(0)
        assert client._pending_rpc
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        return client._pending_rpc

    assert asyncio.run(_run()) == {}


def test_durable_event_late_ack_after_timeout_is_ignored(tmp_path):
    client = _durable_node_client(tmp_path)

    class _LateWs:
        def __init__(self) -> None:
            self.msg_id: object | None = None

        async def send(self, raw: str) -> None:
            self.msg_id = json.loads(raw).get("id")

    async def _run() -> tuple[dict[str, object], dict[object, object]]:
        ws = _LateWs()
        client._ws = ws
        first = await client._send_durable_event(
            "durable_command.claimed",
            {"request_id": "req-1", "claim_id": "claim-1", "state": "CLAIMED"},
            expect_ack=True,
            timeout_s=0.01,
        )
        await client._handle_message(
            json.dumps(
                {
                    "jsonrpc": "2.0",
                    "result": {"ok": True, "error": ""},
                    "id": ws.msg_id,
                }
            )
        )
        return first or {}, client._pending_rpc

    first, pending = asyncio.run(_run())
    assert first["ok"] is False
    assert pending == {}


def test_multiple_durable_control_sends_serialize_and_ack(tmp_path):
    client = _durable_node_client(tmp_path)

    class _Ws:
        def __init__(self) -> None:
            self.sent: list[str] = []

        async def send(self, raw: str) -> None:
            msg = json.loads(raw)
            self.sent.append(str(msg["params"]["request_id"]))
            await asyncio.sleep(0.01)
            await client._handle_message(
                json.dumps(
                    {
                        "jsonrpc": "2.0",
                        "result": {"ok": True, "error": ""},
                        "id": msg.get("id"),
                    }
                )
            )

    async def _run() -> tuple[list[dict[str, object]], list[str]]:
        client._ws = _Ws()
        tasks = [
            asyncio.create_task(
                client._send_durable_event(
                    "durable_command.claimed",
                    {"request_id": f"req-{i}", "claim_id": f"claim-{i}", "state": "CLAIMED"},
                    expect_ack=True,
                    timeout_s=0.5,
                )
            )
            for i in range(3)
        ]
        return [r or {} for r in await asyncio.gather(*tasks)], client._ws.sent

    acks, sent = asyncio.run(_run())
    assert [ack["ok"] for ack in acks] == [True, True, True]
    assert sent == ["req-0", "req-1", "req-2"]


def test_media_frame_and_durable_control_share_ws_send_lock(tmp_path):
    client = _durable_node_client(tmp_path)

    class _Ws:
        def __init__(self) -> None:
            self.sent: list[str] = []

        async def send(self, raw: str | bytes) -> None:
            if isinstance(raw, bytes):
                self.sent.append("media")
                await asyncio.sleep(0.02)
                return
            msg = json.loads(raw)
            self.sent.append(str(msg.get("method")))
            await client._handle_message(
                json.dumps(
                    {
                        "jsonrpc": "2.0",
                        "result": {"ok": True, "error": ""},
                        "id": msg.get("id"),
                    }
                )
            )

    async def _run() -> tuple[list[str], dict[str, object]]:
        client._ws = _Ws()
        client._media_queue.append(b"frame")
        client._media_event.set()
        drain = asyncio.create_task(client._media_drain_loop())
        await asyncio.sleep(0)
        ack = await client._send_durable_event(
            "durable_command.claimed",
            {"request_id": "req-1", "claim_id": "claim-1", "state": "CLAIMED"},
            expect_ack=True,
            timeout_s=0.5,
        )
        drain.cancel()
        try:
            await drain
        except asyncio.CancelledError:
            pass
        return client._ws.sent, ack or {}

    sent, ack = asyncio.run(_run())
    assert sent == ["media", "durable_command.claimed"]
    assert ack["ok"] is True


def test_heartbeat_and_durable_control_share_ws_send_lock(tmp_path, monkeypatch):
    client = _durable_node_client(tmp_path)
    client._config.signals.metrics_interval_s = 0
    monkeypatch.setattr(
        "nodes.windows.umh_node.client.collect_metrics",
        lambda: {"cpu": 1, "memory": 2},
    )

    class _Ws:
        def __init__(self) -> None:
            self.sent: list[dict[str, object]] = []

        async def send(self, raw: str) -> None:
            msg = json.loads(raw)
            self.sent.append(msg)
            if msg.get("method") == "durable_command.claimed":
                await client._handle_message(
                    json.dumps(
                        {
                            "jsonrpc": "2.0",
                            "result": {"ok": True, "error": ""},
                            "id": msg.get("id"),
                        }
                    )
                )

    async def _run() -> tuple[list[str], dict[str, object]]:
        assert client._ws_send_lock is not None
        client._ws = _Ws()
        heartbeat = asyncio.create_task(client._heartbeat_loop())
        durable = asyncio.create_task(
            client._send_durable_event(
                "durable_command.claimed",
                {"request_id": "req-1", "claim_id": "claim-1", "state": "CLAIMED"},
                expect_ack=True,
                timeout_s=0.2,
            )
        )
        ack = await durable
        while not any(m.get("method") == "node.heartbeat" for m in client._ws.sent):
            await asyncio.sleep(0)
        heartbeat.cancel()
        try:
            await heartbeat
        except asyncio.CancelledError:
            pass
        return [str(m.get("method", "<response>")) for m in client._ws.sent], ack or {}

    methods, ack = asyncio.run(_run())
    assert "durable_command.claimed" in methods
    assert "node.heartbeat" in methods
    assert ack["ok"] is True


def test_duplicate_and_late_ack_do_not_mutate_completed_future(tmp_path):
    client = _durable_node_client(tmp_path)

    async def _run() -> tuple[dict[str, object], dict[object, object]]:
        future: asyncio.Future[dict[str, object]] = asyncio.get_running_loop().create_future()
        client._pending_rpc[7] = future
        await client._handle_message(
            json.dumps({"jsonrpc": "2.0", "result": {"ok": True}, "id": 7})
        )
        first = future.result()
        await client._handle_message(
            json.dumps({"jsonrpc": "2.0", "result": {"ok": False}, "id": 7})
        )
        await client._handle_message(
            json.dumps({"jsonrpc": "2.0", "result": {"ok": False}, "id": 999})
        )
        return first, client._pending_rpc

    first, pending = asyncio.run(_run())
    assert first["ok"] is True
    assert pending == {}


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
    result = client._durable_store.result_for(req.request_id)
    assert result is not None
    assert result["state"] == "FAILED"
    assert result["cleanup"]["process_residue"] == []
    methods = [msg.get("method") for msg in ws.sent]
    assert methods == [
        "durable_command.claimed",
        "durable_command.claimed",
        "durable_command.result",
    ]
    result = client._durable_store.result_for(req.request_id)
    assert result is not None
    assert "running acknowledgement rejected" in result["result"]["error"]


def test_durable_claim_ack_timeout_reconciles_same_claim_before_execution(
    tmp_path, monkeypatch
):
    from nodes.windows.umh_node import client as client_mod
    from nodes.windows.umh_node.config import CapabilityConfig

    marker = tmp_path / "marker.txt"
    client = _durable_node_client(tmp_path / "store")
    client._ws = _DurableAckWs(client)
    client._config.capabilities = {
        "shell": CapabilityConfig(enabled=True, max_risk_class="read_only")
    }
    client._adapters = {"shell": object()}
    monkeypatch.setattr(client_mod, "_DURABLE_CLAIM_RETRY_SLEEP_S", 0.0)
    events: list[tuple[str, str]] = []

    async def _send_event(method, payload, **_kwargs):
        events.append((method, str(payload.get("state", ""))))
        if method == "durable_command.claimed" and payload.get("state") == "CLAIMED":
            _canonical_claim_ack(client, payload)
            return {"ok": False, "error": "durable_command.claimed acknowledgement timed out"}
        if method == "durable_command.claimed":
            return _canonical_claim_ack(client, payload)
        return {"ok": True, "error": ""}

    readbacks: list[str] = []

    async def _readback(payload, **_kwargs):
        readbacks.append(str(payload.get("request_id", "")))
        return _canonical_claim_readback(client, payload)

    monkeypatch.setattr(client, "_send_durable_event", _send_event)
    monkeypatch.setattr(client, "_read_canonical_durable_claim_state", _readback)
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
    result = client._durable_store.result_for(req.request_id)
    assert result is not None
    assert result["state"] == "SUCCEEDED"
    claimed_events = [event for event in events if event == ("durable_command.claimed", "CLAIMED")]
    assert len(claimed_events) == 1
    assert readbacks == [req.request_id]


def test_durable_lost_claim_ack_reads_back_canonical_claim_before_execution(
    tmp_path, monkeypatch
):
    from nodes.windows.umh_node import client as client_mod
    from nodes.windows.umh_node.config import CapabilityConfig

    marker = tmp_path / "marker.txt"
    client = _durable_node_client(tmp_path / "store")
    client._ws = _DurableAckWs(client)
    client._config.capabilities = {
        "shell": CapabilityConfig(enabled=True, max_risk_class="read_only")
    }
    client._adapters = {"shell": object()}
    monkeypatch.setattr(client_mod, "_DURABLE_CLAIM_RETRY_SLEEP_S", 0.0)
    events: list[tuple[str, str, str]] = []

    async def _send_event(method, payload, **_kwargs):
        events.append((method, str(payload.get("request_id", "")), str(payload.get("claim_id", ""))))
        if method == "durable_command.claimed" and payload.get("state") == "CLAIMED":
            _canonical_claim_ack(client, payload)
            return {"ok": False, "error": "durable_command.claimed acknowledgement timed out"}
        if method == "durable_command.claimed":
            return _canonical_claim_ack(client, payload)
        return {"ok": True, "error": ""}

    readbacks: list[str] = []

    async def _readback(payload, **_kwargs):
        readbacks.append(str(payload.get("request_id", "")))
        return _canonical_claim_readback(client, payload)

    monkeypatch.setattr(client, "_send_durable_event", _send_event)
    monkeypatch.setattr(client, "_read_canonical_durable_claim_state", _readback)
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
    result = client._durable_store.result_for(req.request_id)
    assert result is not None
    assert result["state"] == "SUCCEEDED"
    methods = [event[0] for event in events]
    assert methods[0] == "durable_command.claimed"
    assert "durable_command.claim_state" not in methods
    assert readbacks == [req.request_id]


def test_durable_missing_claim_ack_reads_back_canonical_claim_before_execution(
    tmp_path, monkeypatch
):
    from nodes.windows.umh_node import client as client_mod
    from nodes.windows.umh_node.config import CapabilityConfig

    marker = tmp_path / "marker.txt"
    client = _durable_node_client(tmp_path / "store")
    client._ws = _DurableAckWs(client)
    client._config.capabilities = {
        "shell": CapabilityConfig(enabled=True, max_risk_class="read_only")
    }
    client._adapters = {"shell": object()}
    monkeypatch.setattr(client_mod, "_DURABLE_CLAIM_RETRY_SLEEP_S", 0.0)

    async def _send_event(method, payload, **_kwargs):
        if method == "durable_command.claimed" and payload.get("state") == "CLAIMED":
            return None
        return {"ok": True, "error": ""}

    async def _readback(payload, **_kwargs):
        return _canonical_claim_readback(client, payload)

    monkeypatch.setattr(client, "_send_durable_event", _send_event)
    monkeypatch.setattr(client, "_read_canonical_durable_claim_state", _readback)
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


def test_durable_claim_ack_timeout_fails_closed_and_replay_does_not_execute(
    tmp_path, monkeypatch
):
    from nodes.windows.umh_node import client as client_mod
    from nodes.windows.umh_node.config import CapabilityConfig

    marker = tmp_path / "marker.txt"
    client = _durable_node_client(tmp_path / "store")
    client._ws = _DurableAckWs(client)
    client._config.capabilities = {
        "shell": CapabilityConfig(enabled=True, max_risk_class="read_only")
    }
    client._adapters = {"shell": object()}
    monkeypatch.setattr(client_mod, "_DURABLE_CLAIM_ACQUIRE_TIMEOUT_S", 0.01)
    monkeypatch.setattr(client_mod, "_DURABLE_CLAIM_RETRY_SLEEP_S", 0.0)
    allow_claim = False
    claim_events = 0

    async def _send_event(method, payload, **_kwargs):
        nonlocal claim_events
        if method == "durable_command.claimed" and payload.get("state") == "CLAIMED":
            claim_events += 1
            if not allow_claim:
                return {"ok": False, "error": "durable_command.claimed acknowledgement timed out"}
            return {"ok": True, "error": ""}
        if method == "durable_command.claim_state" and not allow_claim:
            return {"ok": False, "error": "claim readback unavailable", "retryable": True}
        return {"ok": True, "error": ""}

    monkeypatch.setattr(client, "_send_durable_event", _send_event)
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
    result = client._durable_store.result_for(req.request_id)
    assert result is not None
    assert result["state"] == "FAILED"
    assert result["result"]["error"] == "durable claim acquisition failed closed"
    assert result["cleanup"]["process_residue"] == []
    current = client._durable_store.get_request(req.request_id)
    assert current is not None
    assert current.lifecycle_state == "FAILED"
    allow_claim = True

    asyncio.run(
        client._handle_durable_command(
            {"method": "durable_command.request", "params": current.to_dict()}
        )
    )

    assert marker.exists() is False
    result = client._durable_store.result_for(req.request_id)
    assert result is not None
    assert result["state"] == "FAILED"
    assert result["cleanup"]["process_residue"] == []
    assert claim_events >= 1


def test_durable_claimed_redelivery_after_fail_closed_does_not_execute(
    tmp_path, monkeypatch
):
    from nodes.windows.umh_node import client as client_mod
    from nodes.windows.umh_node.config import CapabilityConfig

    marker = tmp_path / "marker.txt"
    client = _durable_node_client(tmp_path / "store")
    client._ws = _DurableAckWs(client)
    client._config.capabilities = {
        "shell": CapabilityConfig(enabled=True, max_risk_class="read_only")
    }
    client._adapters = {"shell": object()}
    monkeypatch.setattr(client_mod, "_DURABLE_CLAIM_ACQUIRE_TIMEOUT_S", 0.01)
    monkeypatch.setattr(client_mod, "_DURABLE_CLAIM_RETRY_SLEEP_S", 0.0)

    async def _send_event(method, payload, **_kwargs):
        if method == "durable_command.claimed" and payload.get("state") == "CLAIMED":
            return {"ok": False, "error": "durable_command.claimed acknowledgement timed out"}
        if method == "durable_command.claim_state":
            return {"ok": False, "error": "claim readback unavailable", "retryable": True}
        return {"ok": True, "error": ""}

    monkeypatch.setattr(client, "_send_durable_event", _send_event)
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
    current = client._durable_store.get_request(req.request_id)
    assert current is not None
    assert current.lifecycle_state == "FAILED"

    asyncio.run(
        client._handle_durable_command(
            {"method": "durable_command.request", "params": current.to_dict()}
        )
    )

    assert marker.exists() is False
    result = client._durable_store.result_for(req.request_id)
    assert result is not None
    assert result["state"] == "FAILED"
    assert result["cleanup"]["process_residue"] == []


def test_durable_claim_ack_uncertain_fails_closed_without_execution(tmp_path, monkeypatch):
    from nodes.windows.umh_node import client as client_mod
    from nodes.windows.umh_node.config import CapabilityConfig

    marker = tmp_path / "marker.txt"
    client = _durable_node_client(tmp_path / "store")
    client._ws = _DurableAckWs(client)
    client._config.capabilities = {
        "shell": CapabilityConfig(enabled=True, max_risk_class="read_only")
    }
    client._adapters = {"shell": object()}
    monkeypatch.setattr(client_mod, "_DURABLE_CLAIM_ACQUIRE_TIMEOUT_S", 0.02)
    monkeypatch.setattr(client_mod, "_DURABLE_CLAIM_RETRY_SLEEP_S", 0.001)

    async def _send_event(method, payload, **_kwargs):
        if method == "durable_command.claimed" and payload.get("state") == "CLAIMED":
            return {"ok": False, "error": "durable_command.claimed acknowledgement timed out"}
        if method == "durable_command.claim_state":
            return {"ok": False, "error": "claim readback unavailable", "retryable": True}
        return {"ok": True, "error": ""}

    monkeypatch.setattr(client, "_send_durable_event", _send_event)
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
    result = client._durable_store.result_for(req.request_id)
    assert result is not None
    assert result["state"] == "FAILED"
    assert result["result"]["error"] == "durable claim acquisition failed closed"
    assert result["cleanup"]["process_residue"] == []
    current = client._durable_store.get_request(req.request_id)
    assert current is not None
    assert current.lifecycle_state == "FAILED"


def test_durable_bare_claim_ack_cannot_authorize_without_canonical_readback(
    tmp_path, monkeypatch
):
    from nodes.windows.umh_node.config import CapabilityConfig

    marker = tmp_path / "marker.txt"
    client = _durable_node_client(tmp_path / "store")
    client._ws = _DurableAckWs(client)
    client._config.capabilities = {
        "shell": CapabilityConfig(enabled=True, max_risk_class="read_only")
    }
    client._adapters = {"shell": object()}

    async def _send_event(method, payload, **_kwargs):
        if method == "durable_command.claimed" and payload.get("state") == "CLAIMED":
            return {"ok": True, "error": ""}
        return {"ok": True, "error": ""}

    async def _readback(_payload, **_kwargs):
        return {
            "ok": False,
            "accepted": False,
            "error": "canonical state unavailable",
            "retryable": False,
        }

    monkeypatch.setattr(client, "_send_durable_event", _send_event)
    monkeypatch.setattr(client, "_read_canonical_durable_claim_state", _readback)
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
    result = client._durable_store.result_for(req.request_id)
    assert result is not None
    assert result["state"] == "FAILED"
    assert result["result"]["error"] == "durable claim acquisition failed closed"
    assert result["cleanup"]["process_residue"] == []


def test_durable_canonical_claim_read_unavailable_remains_bounded_retryable(
    tmp_path, monkeypatch
):
    from nodes.windows.umh_node import client as client_mod
    from nodes.windows.umh_node.config import CapabilityConfig

    marker = tmp_path / "marker.txt"
    client = _durable_node_client(tmp_path / "store")
    client._ws = _DurableAckWs(client)
    client._config.capabilities = {
        "shell": CapabilityConfig(enabled=True, max_risk_class="read_only")
    }
    client._adapters = {"shell": object()}
    monkeypatch.setattr(client_mod, "_DURABLE_CLAIM_ACQUIRE_TIMEOUT_S", 0.02)
    monkeypatch.setattr(client_mod, "_DURABLE_CLAIM_RETRY_SLEEP_S", 0.0)
    readback_calls = 0

    async def _send_event(method, payload, **_kwargs):
        if method == "durable_command.claimed" and payload.get("state") == "CLAIMED":
            return {"ok": False, "error": "durable_command.claimed acknowledgement timed out"}
        return {"ok": True, "error": ""}

    async def _readback(_payload, **_kwargs):
        nonlocal readback_calls
        readback_calls += 1
        return {"ok": False, "error": "canonical read unavailable", "retryable": True}

    monkeypatch.setattr(client, "_send_durable_event", _send_event)
    monkeypatch.setattr(client, "_read_canonical_durable_claim_state", _readback)
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

    assert readback_calls >= 2
    assert marker.exists() is False
    result = client._durable_store.result_for(req.request_id)
    assert result is not None
    assert result["state"] == "FAILED"
    assert result["cleanup"]["process_residue"] == []
    current = client._durable_store.get_request(req.request_id)
    assert current is not None
    assert current.lifecycle_state == "FAILED"


def test_durable_canonical_claim_read_rejection_fails_closed(
    tmp_path, monkeypatch
):
    from nodes.windows.umh_node import client as client_mod
    from nodes.windows.umh_node.config import CapabilityConfig

    marker = tmp_path / "marker.txt"
    client = _durable_node_client(tmp_path / "store")
    client._ws = _DurableAckWs(client)
    client._config.capabilities = {
        "shell": CapabilityConfig(enabled=True, max_risk_class="read_only")
    }
    client._adapters = {"shell": object()}
    monkeypatch.setattr(client_mod, "_DURABLE_CLAIM_ACQUIRE_TIMEOUT_S", 0.02)
    monkeypatch.setattr(client_mod, "_DURABLE_CLAIM_RETRY_SLEEP_S", 0.0)
    readback_calls = 0

    async def _send_event(method, payload, **_kwargs):
        if method == "durable_command.claimed" and payload.get("state") == "CLAIMED":
            return {"ok": False, "error": "durable_command.claimed acknowledgement timed out"}
        return {"ok": True, "error": ""}

    async def _readback(_payload, **_kwargs):
        nonlocal readback_calls
        readback_calls += 1
        return {"ok": False, "error": "claim readback not accepted", "retryable": False}

    monkeypatch.setattr(client, "_send_durable_event", _send_event)
    monkeypatch.setattr(client, "_read_canonical_durable_claim_state", _readback)
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

    assert readback_calls == 1
    assert marker.exists() is False
    result = client._durable_store.result_for(req.request_id)
    assert result is not None
    assert result["state"] == "FAILED"


def test_durable_claim_foreign_rejection_fails_closed_without_execution(tmp_path, monkeypatch):
    from nodes.windows.umh_node.config import CapabilityConfig

    marker = tmp_path / "marker.txt"
    client = _durable_node_client(tmp_path / "store")
    client._ws = _DurableAckWs(client)
    client._config.capabilities = {
        "shell": CapabilityConfig(enabled=True, max_risk_class="read_only")
    }
    client._adapters = {"shell": object()}

    async def _send_event(method, payload, **_kwargs):
        if method == "durable_command.claimed" and payload.get("state") == "CLAIMED":
            return {"ok": False, "error": "claim rejected into RECONCILIATION_REQUIRED"}
        return {"ok": True, "error": ""}

    monkeypatch.setattr(client, "_send_durable_event", _send_event)
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


def test_durable_claim_readback_foreign_claim_fails_closed_without_execution(
    tmp_path, monkeypatch
):
    from nodes.windows.umh_node import client as client_mod
    from nodes.windows.umh_node.config import CapabilityConfig

    marker = tmp_path / "marker.txt"
    client = _durable_node_client(tmp_path / "store")
    client._ws = _DurableAckWs(client)
    client._config.capabilities = {
        "shell": CapabilityConfig(enabled=True, max_risk_class="read_only")
    }
    client._adapters = {"shell": object()}
    monkeypatch.setattr(client_mod, "_DURABLE_CLAIM_RETRY_SLEEP_S", 0.0)

    async def _send_event(method, payload, **_kwargs):
        if method == "durable_command.claimed" and payload.get("state") == "CLAIMED":
            return {"ok": False, "error": "durable_command.claimed acknowledgement timed out"}
        if method == "durable_command.claim_state":
            return {
                "ok": False,
                "accepted": False,
                "error": "claim readback mismatch: foreign claim",
                "request_id": payload["request_id"],
                "claim_id": "foreign-claim",
                "lifecycle_state": "CLAIMED",
                "retryable": False,
            }
        return {"ok": True, "error": ""}

    monkeypatch.setattr(client, "_send_durable_event", _send_event)
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
    result = client._durable_store.result_for(req.request_id)
    assert result is not None
    assert result["state"] == "FAILED"
    assert result["cleanup"]["process_residue"] == []


def test_durable_claim_readback_accepted_wrong_identity_fails_closed(
    tmp_path, monkeypatch
):
    from nodes.windows.umh_node import client as client_mod
    from nodes.windows.umh_node.config import CapabilityConfig

    marker = tmp_path / "marker.txt"
    client = _durable_node_client(tmp_path / "store")
    client._ws = _DurableAckWs(client)
    client._config.capabilities = {
        "shell": CapabilityConfig(enabled=True, max_risk_class="read_only")
    }
    client._adapters = {"shell": object()}
    monkeypatch.setattr(client_mod, "_DURABLE_CLAIM_RETRY_SLEEP_S", 0.0)

    async def _send_event(method, payload, **_kwargs):
        if method == "durable_command.claimed" and payload.get("state") == "CLAIMED":
            return {"ok": False, "error": "durable_command.claimed acknowledgement timed out"}
        if method == "durable_command.claim_state":
            return {
                "ok": True,
                "accepted": True,
                "request_id": payload["request_id"],
                "correlation_id": "foreign-correlation",
                "candidate_sha": "foreign-sha",
                "node_id": "foreign-node",
                "claim_id": payload["claim_id"],
                "lifecycle_state": "CLAIMED",
                "lease_expires_at": 9_999_999_999.0,
                "process_tree": {},
            }
        return {"ok": True, "error": ""}

    monkeypatch.setattr(client, "_send_durable_event", _send_event)
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
    result = client._durable_store.result_for(req.request_id)
    assert result is not None
    assert result["state"] == "FAILED"
    assert result["cleanup"]["process_residue"] == []


@pytest.mark.parametrize(
    "field,bad_value",
    [
        ("request_id", "foreign-request"),
        ("correlation_id", "foreign-correlation"),
        ("candidate_sha", "foreign-sha"),
        ("node_id", "foreign-node"),
        ("claim_id", "foreign-claim"),
    ],
)
def test_durable_claim_readback_accepted_single_identity_mismatch_fails_closed(
    tmp_path, monkeypatch, field, bad_value
):
    from nodes.windows.umh_node import client as client_mod
    from nodes.windows.umh_node.config import CapabilityConfig

    marker = tmp_path / "marker.txt"
    client = _durable_node_client(tmp_path / "store")
    client._ws = _DurableAckWs(client)
    client._config.capabilities = {
        "shell": CapabilityConfig(enabled=True, max_risk_class="read_only")
    }
    client._adapters = {"shell": object()}
    monkeypatch.setattr(client_mod, "_DURABLE_CLAIM_RETRY_SLEEP_S", 0.0)

    async def _send_event(method, payload, **_kwargs):
        if method == "durable_command.claimed" and payload.get("state") == "CLAIMED":
            return {"ok": False, "error": "durable_command.claimed acknowledgement timed out"}
        if method == "durable_command.claim_state":
            current = client._durable_store.get_request(str(payload["request_id"]))
            assert current is not None
            response = {
                "ok": True,
                "accepted": True,
                "request_id": current.request_id,
                "correlation_id": current.correlation_id,
                "candidate_sha": current.candidate_sha,
                "node_id": current.node_id,
                "claim_id": current.claim_id,
                "lifecycle_state": current.lifecycle_state,
                "lease_expires_at": 9_999_999_999.0,
                "process_tree": {},
            }
            response[field] = bad_value
            return response
        return {"ok": True, "error": ""}

    monkeypatch.setattr(client, "_send_durable_event", _send_event)
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
    result = client._durable_store.result_for(req.request_id)
    assert result is not None
    assert result["state"] == "FAILED"
    assert result["cleanup"]["process_residue"] == []


def test_durable_claim_readback_same_claim_running_without_root_fails_closed_not_mismatch(
    tmp_path, monkeypatch
):
    from nodes.windows.umh_node import client as client_mod
    from nodes.windows.umh_node.config import CapabilityConfig

    marker = tmp_path / "marker.txt"
    client = _durable_node_client(tmp_path / "store")
    client._ws = _DurableAckWs(client)
    client._config.capabilities = {
        "shell": CapabilityConfig(enabled=True, max_risk_class="read_only")
    }
    client._adapters = {"shell": object()}
    monkeypatch.setattr(client_mod, "_DURABLE_CLAIM_RETRY_SLEEP_S", 0.0)

    async def _send_event(method, payload, **_kwargs):
        if method == "durable_command.claimed" and payload.get("state") == "CLAIMED":
            return {"ok": False, "error": "durable_command.claimed acknowledgement timed out"}
        return _canonical_claim_ack(client, payload)

    async def _readback(payload, **_kwargs):
        client._durable_store.mark_running(
            str(payload["request_id"]),
            claim_id=str(payload["claim_id"]),
            process_tree={"node_pid": 1, "root_pid": None, "pre_start_containment": True},
        )
        return _canonical_claim_readback(client, payload)

    monkeypatch.setattr(client, "_send_durable_event", _send_event)
    monkeypatch.setattr(client, "_read_canonical_durable_claim_state", _readback)
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
    result = client._durable_store.result_for(req.request_id)
    assert result is not None
    assert result["state"] == "FAILED"
    assert result["cleanup"]["process_residue"] == []
    assert "lifecycle_state" not in result["result"]["reason"]
    assert "running without root pid" in result["result"]["reason"]


def test_durable_claim_readback_shell_running_without_process_evidence_fails_closed(
    tmp_path, monkeypatch
):
    from nodes.windows.umh_node import client as client_mod
    from nodes.windows.umh_node.config import CapabilityConfig

    marker = tmp_path / "marker.txt"
    client = _durable_node_client(tmp_path / "store")
    client._ws = _DurableAckWs(client)
    client._config.capabilities = {
        "shell": CapabilityConfig(enabled=True, max_risk_class="read_only")
    }
    client._adapters = {"shell": object()}
    monkeypatch.setattr(client_mod, "_DURABLE_CLAIM_RETRY_SLEEP_S", 0.0)

    async def _send_event(method, payload, **_kwargs):
        if method == "durable_command.claimed" and payload.get("state") == "CLAIMED":
            return {"ok": False, "error": "durable_command.claimed acknowledgement timed out"}
        return _canonical_claim_ack(client, payload)

    async def _readback(payload, **_kwargs):
        client._durable_store.mark_running(
            str(payload["request_id"]),
            claim_id=str(payload["claim_id"]),
            process_tree={"node_pid": 1, "running_at": time.time()},
        )
        return _canonical_claim_readback(client, payload)

    monkeypatch.setattr(client, "_send_durable_event", _send_event)
    monkeypatch.setattr(client, "_read_canonical_durable_claim_state", _readback)
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
    result = client._durable_store.result_for(req.request_id)
    assert result is not None
    assert result["state"] == "FAILED"
    assert "running without root pid" in result["result"]["reason"]
    assert result["cleanup"]["process_residue"] == []


def test_durable_claim_readback_same_claim_running_with_root_does_not_relaunch(
    tmp_path, monkeypatch
):
    from nodes.windows.umh_node import client as client_mod
    from nodes.windows.umh_node.config import CapabilityConfig

    marker = tmp_path / "marker.txt"
    client = _durable_node_client(tmp_path / "store")
    client._ws = _DurableAckWs(client)
    client._config.capabilities = {
        "shell": CapabilityConfig(enabled=True, max_risk_class="read_only")
    }
    client._adapters = {"shell": object()}
    monkeypatch.setattr(client_mod, "_DURABLE_CLAIM_RETRY_SLEEP_S", 0.0)
    sent: list[dict[str, object]] = []

    async def _send_event(method, payload, **_kwargs):
        sent.append({"method": method, "payload": payload})
        if method == "durable_command.claimed" and payload.get("state") == "CLAIMED":
            return {"ok": False, "error": "durable_command.claimed acknowledgement timed out"}
        return _canonical_claim_ack(client, payload)

    async def _readback(payload, **_kwargs):
        client._durable_store.mark_running(
            str(payload["request_id"]),
            claim_id=str(payload["claim_id"]),
            process_tree={"node_pid": 1, "root_pid": 4242, "running_at": time.time()},
        )
        return _canonical_claim_readback(client, payload)

    monkeypatch.setattr(client, "_send_durable_event", _send_event)
    monkeypatch.setattr(client, "_read_canonical_durable_claim_state", _readback)
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
    assert client._durable_store.result_for(req.request_id) is None
    running_replays = [
        msg
        for msg in sent
        if msg["method"] == "durable_command.claimed"
        and msg["payload"].get("state") == "RUNNING"
    ]
    assert len(running_replays) == 1


def test_durable_claim_ack_same_claim_running_does_not_use_stale_local_claim_to_launch(
    tmp_path, monkeypatch
):
    from nodes.windows.umh_node import client as client_mod
    from nodes.windows.umh_node.config import CapabilityConfig

    marker = tmp_path / "marker.txt"
    client = _durable_node_client(tmp_path / "store")
    client._ws = _DurableAckWs(client)
    client._config.capabilities = {
        "shell": CapabilityConfig(enabled=True, max_risk_class="read_only")
    }
    client._adapters = {"shell": object()}
    monkeypatch.setattr(client_mod, "_DURABLE_CLAIM_RETRY_SLEEP_S", 0.0)
    sent: list[dict[str, object]] = []

    async def _send_event(method, payload, **_kwargs):
        sent.append({"method": method, "payload": payload})
        if method == "durable_command.claimed" and payload.get("state") == "CLAIMED":
            current = client._durable_store.get_request(str(payload["request_id"]))
            assert current is not None
            return {
                "ok": True,
                "accepted": True,
                "request_id": current.request_id,
                "correlation_id": current.correlation_id,
                "candidate_sha": current.candidate_sha,
                "node_id": current.node_id,
                "claim_id": current.claim_id,
                "lifecycle_state": "RUNNING",
                "lease_expires_at": current.lease_expires_at,
                "process_tree": {"node_pid": 1, "root_pid": 4242, "running_at": time.time()},
                "authority_source": "vps_canonical_durable_store",
            }
        return _canonical_claim_ack(client, payload)

    monkeypatch.setattr(client, "_send_durable_event", _send_event)
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
    assert client._durable_store.result_for(req.request_id) is None
    states = [
        msg["payload"].get("state")
        for msg in sent
        if msg["method"] == "durable_command.claimed"
    ]
    assert states == ["CLAIMED", "RUNNING"]


def test_durable_claim_readback_same_claim_terminal_does_not_relaunch(
    tmp_path, monkeypatch
):
    from nodes.windows.umh_node import client as client_mod
    from nodes.windows.umh_node.config import CapabilityConfig

    marker = tmp_path / "marker.txt"
    client = _durable_node_client(tmp_path / "store")
    client._ws = _DurableAckWs(client)
    client._config.capabilities = {
        "shell": CapabilityConfig(enabled=True, max_risk_class="read_only")
    }
    client._adapters = {"shell": object()}
    monkeypatch.setattr(client_mod, "_DURABLE_CLAIM_RETRY_SLEEP_S", 0.0)
    sent: list[dict[str, object]] = []

    async def _send_event(method, payload, **_kwargs):
        sent.append({"method": method, "payload": payload})
        if method == "durable_command.claimed" and payload.get("state") == "CLAIMED":
            return {"ok": False, "error": "durable_command.claimed acknowledgement timed out"}
        return _canonical_claim_ack(client, payload)

    async def _readback(payload, **_kwargs):
        client._durable_store.publish_result(
            str(payload["request_id"]),
            claim_id=str(payload["claim_id"]),
            state="SUCCEEDED",
            result={"success": True, "stdout": "already done"},
            cleanup={"process_residue": []},
        )
        return _canonical_claim_readback(client, payload)

    monkeypatch.setattr(client, "_send_durable_event", _send_event)
    monkeypatch.setattr(client, "_read_canonical_durable_claim_state", _readback)
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
    result = client._durable_store.result_for(req.request_id)
    assert result is not None
    assert result["state"] == "SUCCEEDED"
    result_events = [msg for msg in sent if msg["method"] == "durable_command.result"]
    assert len(result_events) == 1
    assert result_events[0]["payload"]["idempotent_replay"] is True


def test_durable_claim_send_exception_fails_closed_without_execution(tmp_path, monkeypatch):
    from nodes.windows.umh_node.config import CapabilityConfig

    marker = tmp_path / "marker.txt"
    client = _durable_node_client(tmp_path / "store")
    client._ws = _DurableAckWs(client)
    client._config.capabilities = {
        "shell": CapabilityConfig(enabled=True, max_risk_class="read_only")
    }
    client._adapters = {"shell": object()}

    async def _send_event(method, payload, **_kwargs):
        if method == "durable_command.claimed" and payload.get("state") == "CLAIMED":
            raise OSError("synthetic disconnect")
        if method == "durable_command.claim_state":
            return {"ok": False, "error": "claim readback unavailable", "retryable": True}
        return {"ok": True, "error": ""}

    monkeypatch.setattr(client, "_send_durable_event", _send_event)
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
    result = client._durable_store.result_for(req.request_id)
    assert result is not None
    assert result["state"] == "FAILED"
    assert result["cleanup"]["process_residue"] == []


def test_durable_claim_cancel_during_acquisition_publishes_bound_cancel_ack(
    tmp_path, monkeypatch
):
    from nodes.windows.umh_node import client as client_mod
    from nodes.windows.umh_node.config import CapabilityConfig

    marker = tmp_path / "marker.txt"
    client = _durable_node_client(tmp_path / "store")
    client._ws = _DurableAckWs(client)
    client._config.capabilities = {
        "shell": CapabilityConfig(enabled=True, max_risk_class="read_only")
    }
    client._adapters = {"shell": object()}
    monkeypatch.setattr(client_mod, "_DURABLE_CLAIM_RETRY_SLEEP_S", 0.0)
    claim_seen = False

    async def _send_event(method, payload, **_kwargs):
        nonlocal claim_seen
        if method == "durable_command.claimed" and payload.get("state") == "CLAIMED":
            if not claim_seen:
                claim_seen = True
                client._durable_store.request_cancel(str(payload["request_id"]))
                return {"ok": True, "error": ""}
        return {"ok": True, "error": ""}

    monkeypatch.setattr(client, "_send_durable_event", _send_event)
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
    result = client._durable_store.result_for(req.request_id)
    assert result is not None
    assert result["state"] == "CANCELLED"
    assert result["cleanup"]["process_residue"] == []


def test_durable_same_claim_replay_executes_once_under_concurrency(tmp_path, monkeypatch):
    client = _durable_node_client(tmp_path / "store")
    client._ws = _DurableAckWs(client)
    req = client._durable_store.put_request(_durable_request())
    client._durable_store.mark_claimed(
        req.request_id,
        claim_id="claim-1",
        process_tree={"node_pid": 1, "claimed_at": 1.0},
    )
    delivered = client._durable_store.get_request(req.request_id)
    assert delivered is not None
    starts = 0
    release = asyncio.Event()

    async def _send_event(method, payload, **_kwargs):
        if method == "durable_command.claimed":
            return _canonical_claim_ack(client, payload)
        return {"ok": True, "error": ""}

    async def _execute(*_args, **_kwargs):
        nonlocal starts
        starts += 1
        await release.wait()
        return {"success": True, "stdout": "ok", "cleanup": {"process_residue": []}}

    monkeypatch.setattr(client, "_send_durable_event", _send_event)
    monkeypatch.setattr(client, "_execute_capability_for_durable", _execute)

    async def _run() -> None:
        first = asyncio.create_task(
            client._handle_durable_command(
                {"method": "durable_command.request", "params": delivered.to_dict()}
            )
        )
        await asyncio.sleep(0)
        second = asyncio.create_task(
            client._handle_durable_command(
                {"method": "durable_command.request", "params": delivered.to_dict()}
            )
        )
        await asyncio.sleep(0)
        release.set()
        await asyncio.gather(first, second)

    asyncio.run(_run())

    assert starts == 1
    result = client._durable_store.result_for(req.request_id)
    assert result is not None
    assert result["state"] == "SUCCEEDED"


def test_durable_claimed_redelivery_with_root_pid_fails_closed_without_execution(
    tmp_path, monkeypatch
):
    client = _durable_node_client(tmp_path / "store")
    client._ws = _DurableAckWs(client)
    req = client._durable_store.put_request(_durable_request())
    client._durable_store.mark_claimed(
        req.request_id,
        claim_id="claim-1",
        process_tree={"node_pid": 1, "root_pid": 4242, "claimed_at": 1.0},
    )
    delivered = client._durable_store.get_request(req.request_id)
    assert delivered is not None
    executed = False

    async def _execute(*_args, **_kwargs):
        nonlocal executed
        executed = True
        return {"success": True, "cleanup": {"process_residue": []}}

    monkeypatch.setattr(client, "_execute_capability_for_durable", _execute)

    asyncio.run(
        client._handle_durable_command(
            {"method": "durable_command.request", "params": delivered.to_dict()}
        )
    )

    assert executed is False
    result = client._durable_store.result_for(req.request_id)
    assert result is not None
    assert result["state"] == "FAILED"
    assert result["result"]["success"] is False
    assert "root pid before running" in result["result"]["reason"]
    assert result["cleanup"]["process_residue"] == []


def test_durable_running_replay_without_root_pid_fails_closed_without_fabricated_running(
    tmp_path, monkeypatch
):
    client = _durable_node_client(tmp_path / "store")
    client._ws = _DurableAckWs(client)
    req = client._durable_store.put_request(_durable_request())
    client._durable_store.mark_claimed(req.request_id, claim_id="claim-1")
    client._durable_store.mark_running(
        req.request_id,
        claim_id="claim-1",
        process_tree={"node_pid": 1, "root_pid": None, "pre_start_containment": True},
    )
    delivered = client._durable_store.get_request(req.request_id)
    assert delivered is not None
    executed = False

    async def _execute(*_args, **_kwargs):
        nonlocal executed
        executed = True
        return {"success": True, "cleanup": {"process_residue": []}}

    monkeypatch.setattr(client, "_execute_capability_for_durable", _execute)

    asyncio.run(
        client._handle_durable_command(
            {"method": "durable_command.request", "params": delivered.to_dict()}
        )
    )

    assert executed is False
    result = client._durable_store.result_for(req.request_id)
    assert result is not None
    assert result["state"] == "FAILED"
    assert "running without root pid" in result["result"]["reason"]
    assert result["cleanup"]["process_residue"] == []


def test_durable_prestart_running_redelivery_with_local_owner_does_not_fail_closed(
    tmp_path, monkeypatch
):
    client = _durable_node_client(tmp_path / "store")
    client._ws = _DurableAckWs(client)
    req = client._durable_store.put_request(_durable_request())
    client._durable_store.mark_claimed(req.request_id, claim_id="claim-1")
    prestart_tree = {
        "node_pid": os.getpid(),
        "root_pid": None,
        "pre_start_containment": True,
        "claimed_at": time.time(),
    }
    client._durable_store.mark_running(
        req.request_id,
        claim_id="claim-1",
        process_tree=prestart_tree,
    )
    delivered = client._durable_store.get_request(req.request_id)
    assert delivered is not None
    executed = False

    async def _execute(*_args, **_kwargs):
        nonlocal executed
        executed = True
        return {"success": True, "cleanup": {"process_residue": []}}

    monkeypatch.setattr(client, "_execute_capability_for_durable", _execute)
    lock = client._durable_execution_locks.setdefault(req.request_id, asyncio.Lock())

    async def _redeliver_while_owned():
        await lock.acquire()
        try:
            await client._handle_durable_command(
                {"method": "durable_command.request", "params": delivered.to_dict()}
            )
        finally:
            lock.release()

    asyncio.run(_redeliver_while_owned())

    assert executed is False
    assert client._durable_store.result_for(req.request_id) is None
    current = client._durable_store.get_request(req.request_id)
    assert current is not None
    assert current.lifecycle_state == "RUNNING"
    assert current.process_tree.get("root_pid") is None


def test_durable_expired_request_fails_closed_before_claim_or_execution(tmp_path, monkeypatch):
    client = _durable_node_client(tmp_path / "store")
    client._ws = _DurableAckWs(client)
    req = _durable_request(ttl_seconds=-1)
    executed = False

    async def _execute(*_args, **_kwargs):
        nonlocal executed
        executed = True
        return {"success": True, "cleanup": {"process_residue": []}}

    monkeypatch.setattr(client, "_execute_capability_for_durable", _execute)

    asyncio.run(
        client._handle_durable_command(
            {"method": "durable_command.request", "params": req.to_dict()}
        )
    )

    assert executed is False
    result = client._durable_store.result_for(req.request_id)
    assert result is not None
    assert result["state"] == "FAILED"
    assert result["result"]["reason"] == "request expired before claim authority"
    current = client._durable_store.get_request(req.request_id)
    assert current is not None
    assert current.claim_id == "unclaimed"


def test_durable_non_shell_cancel_after_running_ack_before_adapter_execute_does_not_run(
    tmp_path, monkeypatch
):
    from nodes.windows.umh_node.config import CapabilityConfig

    class _Adapter:
        def __init__(self):
            self.called = False

        def execute(self, _cap_name, _cap_params):
            self.called = True
            return {"success": True, "cleanup": {"process_residue": []}}

    client = _durable_node_client(tmp_path / "store")
    adapter = _Adapter()
    client._config.capabilities = {
        "demo": CapabilityConfig(enabled=True, max_risk_class="read_only")
    }
    client._adapters = {"demo": adapter}
    req = client._durable_store.put_request(
        _durable_request(capability="demo.execute", params={"timeout": 5})
    )
    client._durable_store.mark_claimed(req.request_id, claim_id="claim-1")

    async def _send_event(method, payload, **_kwargs):
        if method == "durable_command.claimed" and payload.get("state") == "RUNNING":
            ack = _canonical_claim_ack(client, payload)
            client._durable_store.request_cancel(str(payload["request_id"]))
            return ack
        if method == "durable_command.claimed":
            return _canonical_claim_ack(client, payload)
        return {"ok": True, "error": ""}

    monkeypatch.setattr(client, "_send_durable_event", _send_event)

    result = asyncio.run(
        client._execute_capability_for_durable(
            req,
            claim_id="claim-1",
            process_tree={"node_pid": 1},
        )
    )

    assert adapter.called is False
    assert result["success"] is False
    assert result["error"] == "cancel requested before adapter start"
    assert result["cleanup"]["process_residue"] == []


def test_durable_non_shell_running_replay_without_root_pid_is_not_failed_as_shell_prestart(
    tmp_path, monkeypatch
):
    from nodes.windows.umh_node.config import CapabilityConfig

    client = _durable_node_client(tmp_path / "store")
    client._ws = _DurableAckWs(client)
    client._config.capabilities = {
        "demo": CapabilityConfig(enabled=True, max_risk_class="read_only")
    }
    req = client._durable_store.put_request(
        _durable_request(capability="demo.execute", params={"timeout": 5})
    )
    client._durable_store.mark_claimed(req.request_id, claim_id="claim-1")
    client._durable_store.mark_running(
        req.request_id,
        claim_id="claim-1",
        process_tree={"node_pid": 1, "claimed_at": 1.0, "running_at": 2.0},
    )
    delivered = client._durable_store.get_request(req.request_id)
    assert delivered is not None
    sent: list[dict[str, object]] = []

    async def _send_event(method, payload, **_kwargs):
        sent.append({"method": method, "payload": payload})
        return {"ok": True, "error": ""}

    monkeypatch.setattr(client, "_send_durable_event", _send_event)

    asyncio.run(
        client._handle_durable_command(
            {"method": "durable_command.request", "params": delivered.to_dict()}
        )
    )

    assert client._durable_store.result_for(req.request_id) is None
    assert sent == [
        {
            "method": "durable_command.claimed",
            "payload": {
                "request_id": req.request_id,
                "claim_id": "claim-1",
                "state": "RUNNING",
                "process_tree": delivered.process_tree,
            },
        }
    ]


def test_durable_shell_expired_after_running_ack_before_popen_does_not_spawn(
    tmp_path, monkeypatch
):
    from nodes.windows.umh_node import client as client_mod

    client = _durable_node_client(tmp_path / "store")
    req = client._durable_store.put_request(_durable_request())
    client._durable_store.mark_claimed(req.request_id, claim_id="claim-1")
    spawned = False

    async def _send_event(method, payload, **_kwargs):
        if method == "durable_command.claimed" and payload.get("state") == "RUNNING":
            current = client._durable_store.get_request(str(payload["request_id"]))
            assert current is not None
            ack = _canonical_claim_ack(client, payload)
            current.expires_at = time.time() - 1.0
            client._durable_store.update_request(current, "EXPIRED_FOR_TEST")
            return ack
        if method == "durable_command.claimed":
            return _canonical_claim_ack(client, payload)
        return {"ok": True, "error": ""}

    def _popen(*_args, **_kwargs):
        nonlocal spawned
        spawned = True
        raise AssertionError("Popen must not be reached after expiry")

    monkeypatch.setattr(client, "_send_durable_event", _send_event)
    monkeypatch.setattr(client_mod.subprocess, "Popen", _popen)

    result = asyncio.run(
        client._execute_shell_for_durable(
            req,
            cap_name="shell",
            cap_params={"command": "echo ok"},
            claim_id="claim-1",
            process_tree={"node_pid": 1},
            timeout=5.0,
        )
    )

    assert spawned is False
    assert result["success"] is False
    assert result["error"] == "request expired before process start"
    assert result["cleanup"]["process_residue"] == []


def test_durable_shell_missing_local_state_after_running_ack_does_not_spawn(
    tmp_path, monkeypatch
):
    from nodes.windows.umh_node import client as client_mod

    client = _durable_node_client(tmp_path / "store")
    req = client._durable_store.put_request(_durable_request())
    client._durable_store.mark_claimed(req.request_id, claim_id="claim-1")
    spawned = False

    async def _send_event(method, payload, **_kwargs):
        if method == "durable_command.claimed" and payload.get("state") == "RUNNING":
            ack = _canonical_claim_ack(client, payload)
            client._durable_store.remove_request(str(payload["request_id"]))
            return ack
        if method == "durable_command.claimed":
            return _canonical_claim_ack(client, payload)
        return {"ok": True, "error": ""}

    def _popen(*_args, **_kwargs):
        nonlocal spawned
        spawned = True
        raise AssertionError("Popen must not be reached without local durable state")

    monkeypatch.setattr(client, "_send_durable_event", _send_event)
    monkeypatch.setattr(client_mod.subprocess, "Popen", _popen)

    result = asyncio.run(
        client._execute_shell_for_durable(
            req,
            cap_name="shell",
            cap_params={"command": "echo ok"},
            claim_id="claim-1",
            process_tree={"node_pid": 1},
            timeout=5.0,
        )
    )

    assert spawned is False
    assert result["success"] is False
    assert result["error"] == "durable request missing before process start"
    assert result["cleanup"]["process_residue"] == []


def test_durable_non_shell_missing_local_state_after_running_ack_does_not_execute(
    tmp_path, monkeypatch
):
    from nodes.windows.umh_node.config import CapabilityConfig

    class _Adapter:
        def __init__(self):
            self.called = False

        def execute(self, _cap_name, _cap_params):
            self.called = True
            return {"success": True, "cleanup": {"process_residue": []}}

    client = _durable_node_client(tmp_path / "store")
    adapter = _Adapter()
    client._config.capabilities = {
        "demo": CapabilityConfig(enabled=True, max_risk_class="read_only")
    }
    client._adapters = {"demo": adapter}
    req = client._durable_store.put_request(
        _durable_request(capability="demo.execute", params={"timeout": 5})
    )
    client._durable_store.mark_claimed(req.request_id, claim_id="claim-1")

    async def _send_event(method, payload, **_kwargs):
        if method == "durable_command.claimed" and payload.get("state") == "RUNNING":
            ack = _canonical_claim_ack(client, payload)
            client._durable_store.remove_request(str(payload["request_id"]))
            return ack
        if method == "durable_command.claimed":
            return _canonical_claim_ack(client, payload)
        return {"ok": True, "error": ""}

    monkeypatch.setattr(client, "_send_durable_event", _send_event)

    result = asyncio.run(
        client._execute_capability_for_durable(
            req,
            claim_id="claim-1",
            process_tree={"node_pid": 1},
        )
    )

    assert adapter.called is False
    assert result["success"] is False
    assert result["error"] == "durable request missing before adapter start"
    assert result["cleanup"]["process_residue"] == []


def test_durable_handler_missing_local_state_after_running_ack_emits_failed_result(
    tmp_path, monkeypatch
):
    from nodes.windows.umh_node import client as client_mod
    from nodes.windows.umh_node.config import CapabilityConfig

    client = _durable_node_client(tmp_path / "store")
    client._config.capabilities = {
        "shell": CapabilityConfig(enabled=True, max_risk_class="read_only")
    }
    client._adapters = {"shell": object()}
    sent: list[dict[str, object]] = []
    spawned = False

    async def _send_event(method, payload, **_kwargs):
        sent.append({"method": method, "payload": payload})
        if method == "durable_command.claimed" and payload.get("state") == "RUNNING":
            ack = _canonical_claim_ack(client, payload)
            client._durable_store.remove_request(str(payload["request_id"]))
            return ack
        if method == "durable_command.claimed":
            return _canonical_claim_ack(client, payload)
        return {"ok": True, "error": ""}

    def _popen(*_args, **_kwargs):
        nonlocal spawned
        spawned = True
        raise AssertionError("Popen must not be reached without local durable state")

    monkeypatch.setattr(client, "_send_durable_event", _send_event)
    monkeypatch.setattr(client_mod.subprocess, "Popen", _popen)
    req = _durable_request(
        params={
            "argv": [
                sys.executable,
                "-c",
                "print('should-not-run')",
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

    assert spawned is False
    result_events = [msg for msg in sent if msg["method"] == "durable_command.result"]
    assert len(result_events) == 1
    payload = result_events[0]["payload"]
    assert payload["state"] == "FAILED"
    assert payload["result"]["error"] == "durable request missing before process start"
    assert payload["cleanup"]["process_residue"] == []


def test_durable_running_redelivery_ack_failure_with_root_enters_reconciliation(
    tmp_path, monkeypatch
):
    client = _durable_node_client(tmp_path / "store")
    sent: list[dict[str, object]] = []
    req = client._durable_store.put_request(_durable_request())
    client._durable_store.mark_claimed(req.request_id, claim_id="claim-1")
    client._durable_store.mark_running(
        req.request_id,
        claim_id="claim-1",
        process_tree={"node_pid": 1, "root_pid": 4242, "running_at": 2.0},
    )
    delivered = client._durable_store.get_request(req.request_id)
    assert delivered is not None

    async def _send_event(method, payload, **_kwargs):
        sent.append({"method": method, "payload": payload})
        if method == "durable_command.claimed" and payload.get("state") == "RUNNING":
            return {"ok": False, "error": "running replay rejected"}
        return {"ok": True, "error": ""}

    monkeypatch.setattr(client, "_send_durable_event", _send_event)

    asyncio.run(
        client._handle_durable_command(
            {"method": "durable_command.request", "params": delivered.to_dict()}
        )
    )

    result_events = [msg for msg in sent if msg["method"] == "durable_command.result"]
    assert len(result_events) == 1
    payload = result_events[0]["payload"]
    assert payload["state"] == "FAILED"
    assert payload["result"]["error"] == "durable running acknowledgement failed closed"
    assert payload["cleanup"]["process_residue"] == [
        {"pid": 4242, "state": "running_redelivery_ack_unresolved"}
    ]
    current = client._durable_store.get_request(req.request_id)
    assert current is not None
    assert current.lifecycle_state == "RECONCILIATION_REQUIRED"


def test_durable_shell_cancel_after_running_ack_before_popen_does_not_spawn(
    tmp_path, monkeypatch
):
    from nodes.windows.umh_node import client as client_mod

    client = _durable_node_client(tmp_path / "store")
    req = client._durable_store.put_request(_durable_request())
    client._durable_store.mark_claimed(req.request_id, claim_id="claim-1")
    spawned = False

    async def _send_event(method, payload, **_kwargs):
        if method == "durable_command.claimed" and payload.get("state") == "RUNNING":
            ack = _canonical_claim_ack(client, payload)
            client._durable_store.request_cancel(str(payload["request_id"]))
            return ack
        if method == "durable_command.claimed":
            return _canonical_claim_ack(client, payload)
        return {"ok": True, "error": ""}

    def _popen(*_args, **_kwargs):
        nonlocal spawned
        spawned = True
        raise AssertionError("Popen must not be reached after cancellation")

    monkeypatch.setattr(client, "_send_durable_event", _send_event)
    monkeypatch.setattr(client_mod.subprocess, "Popen", _popen)

    result = asyncio.run(
        client._execute_shell_for_durable(
            req,
            cap_name="shell",
            cap_params={"command": "echo ok"},
            claim_id="claim-1",
            process_tree={"node_pid": 1},
            timeout=5.0,
        )
    )

    assert spawned is False
    assert result["success"] is False
    assert result["error"] == "cancel requested before process start"
    assert result["cleanup"]["process_residue"] == []


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
    req = client._durable_store.request_cancel(req.request_id)
    cleanup = {
        "process_residue": [],
        "cancel_reason": "unit",
        **req.cancellation_identity(claim_id="claim-1"),
    }
    client._durable_store.publish_result(
        req.request_id,
        claim_id="claim-1",
        state="CANCELLED",
        result={"success": False, "error": "cancelled"},
        cleanup=cleanup,
    )

    asyncio.run(
        client._handle_durable_command(
            {"method": "durable_command.request", "params": req.to_dict()}
        )
    )

    assert len(ws.sent) == 1
    replay = ws.sent[0]
    assert replay["method"] == "durable_command.result"
    assert replay["params"]["cleanup"] == cleanup
    assert replay["params"]["idempotent_replay"] is True


def test_durable_cancel_ack_includes_request_bound_generation(tmp_path):
    client = _durable_node_client(tmp_path)
    ws = _DurableAckWs(client)
    client._ws = ws
    req = client._durable_store.put_request(_durable_request())
    client._durable_store.mark_claimed(req.request_id, claim_id="claim-1")
    req = client._durable_store.request_cancel(req.request_id)

    terminal = asyncio.run(
        client._cancel_durable_request(
            req,
            claim_id="claim-1",
            reason="cancel requested by controller",
        )
    )

    assert terminal.lifecycle_state == "CANCELLED"
    assert terminal.cleanup["process_residue"] == []
    assert terminal.cleanup["cancel_reason"] == "cancel requested by controller"
    assert terminal.cleanup["cancellation_generation"] == req.cancellation_requested_at
    assert terminal.cleanup["cancellation_requested_at"] == req.cancellation_requested_at
    assert terminal.cleanup["cancellation_deadline_at"] == req.cancellation_deadline_at
    assert terminal.cleanup["claim_id"] == "claim-1"
    assert terminal.cleanup["cancellation_envelope_digest"] == req.cancellation_identity(
        claim_id="claim-1"
    )["cancellation_envelope_digest"]


def test_durable_cancel_after_restart_with_root_pid_fails_closed(tmp_path):
    client = _durable_node_client(tmp_path)
    req = client._durable_store.put_request(_durable_request())
    client._durable_store.mark_claimed(req.request_id, claim_id="claim-1")
    client._durable_store.mark_running(
        req.request_id,
        claim_id="claim-1",
        process_tree={"node_pid": 1, "root_pid": 4242, "running_at": time.time()},
    )
    req = client._durable_store.request_cancel(req.request_id)
    client._durable_processes.clear()

    terminal = asyncio.run(
        client._cancel_durable_request(
            req,
            claim_id="claim-1",
            reason="cancel requested after restart",
        )
    )

    assert terminal.lifecycle_state == "RECONCILIATION_REQUIRED"
    assert terminal.cleanup["process_residue"] == [
        {"pid": 4242, "state": "running_process_owner_lost_after_restart"}
    ]
    assert terminal.cleanup["process_owner_lost_after_restart"] is True
    assert client._durable_store.result_for(req.request_id) is None


def test_durable_cancel_delivery_after_claim_uses_delivered_cancellation_identity(tmp_path):
    client = _durable_node_client(tmp_path)
    ws = _DurableAckWs(client)
    client._ws = ws
    original = client._durable_store.put_request(_durable_request())
    client._durable_store.mark_claimed(original.request_id, claim_id="claim-1")
    client._durable_store.mark_running(original.request_id, claim_id="claim-1")
    delivered = client._durable_store.get_request(original.request_id)
    assert delivered is not None
    delivered.lifecycle_state = "CANCEL_REQUESTED"
    delivered.cancellation_requested_at = 1234.5
    delivered.cancellation_deadline_at = 1300.5

    asyncio.run(
        client._handle_durable_command(
            {"method": "durable_command.request", "params": delivered.to_dict()}
        )
    )

    result = client._durable_store.result_for(original.request_id)
    assert result is not None
    assert result["state"] == "CANCELLED"
    cleanup = result["cleanup"]
    assert cleanup["process_residue"] == []
    assert cleanup["cancellation_generation"] == 1234.5
    assert cleanup["cancellation_requested_at"] == 1234.5
    assert cleanup["cancellation_deadline_at"] == 1300.5
    assert cleanup["claim_id"] == "claim-1"
    assert cleanup["cancellation_envelope_digest"] == delivered.cancellation_identity(
        claim_id="claim-1"
    )["cancellation_envelope_digest"]


def test_durable_cancel_delivery_missing_identity_does_not_terminalize(tmp_path):
    client = _durable_node_client(tmp_path)
    ws = _DurableAckWs(client)
    client._ws = ws
    original = client._durable_store.put_request(_durable_request())
    client._durable_store.mark_claimed(original.request_id, claim_id="claim-1")
    delivered = client._durable_store.get_request(original.request_id)
    assert delivered is not None
    delivered.lifecycle_state = "CANCEL_REQUESTED"
    delivered.cancellation_requested_at = 0.0
    delivered.cancellation_deadline_at = 0.0

    asyncio.run(
        client._handle_durable_command(
            {"method": "durable_command.request", "params": delivered.to_dict()}
        )
    )

    assert client._durable_store.result_for(original.request_id) is None
    current = client._durable_store.get_request(original.request_id)
    assert current is not None
    assert current.lifecycle_state == "CLAIMED"


def test_durable_shell_cancel_during_execution_includes_request_bound_generation(
    tmp_path, monkeypatch
):
    from nodes.windows.umh_node import client as client_mod

    client = _durable_node_client(tmp_path)
    req = client._durable_store.put_request(_durable_request())
    client._durable_store.mark_claimed(req.request_id, claim_id="claim-1")

    class _Proc:
        pid = 12345

        def poll(self):
            client._durable_store.request_cancel(req.request_id)
            return None

    async def _terminate(_proc, *, graceful_timeout):
        return {"process_residue": []}

    async def _running_ack(*_args, **_kwargs):
        client._durable_store.mark_running(
            req.request_id, claim_id="claim-1", process_tree={"node_pid": 1}
        )
        return {"ok": True}

    async def _send_event(*_args, **_kwargs):
        return {"ok": True}

    monkeypatch.setattr(client_mod.subprocess, "Popen", lambda *_args, **_kwargs: _Proc())
    monkeypatch.setattr(client, "_terminate_durable_process_tree", _terminate)
    monkeypatch.setattr(client, "_announce_durable_running", _running_ack)
    monkeypatch.setattr(client, "_send_durable_event", _send_event)

    result = asyncio.run(
        client._execute_shell_for_durable(
            req,
            cap_name="shell",
            cap_params={"command": "echo ok"},
            claim_id="claim-1",
            process_tree={"node_pid": 1},
            timeout=5.0,
        )
    )

    assert result["success"] is False
    current = client._durable_store.get_request(req.request_id)
    assert current is not None
    assert result["cleanup"]["process_residue"] == []
    assert result["cleanup"]["cancel_reason"] == "cancel requested during execution"
    assert result["cleanup"]["cancellation_generation"] == current.cancellation_requested_at
    assert result["cleanup"]["cancellation_requested_at"] == current.cancellation_requested_at
    assert result["cleanup"]["cancellation_deadline_at"] == current.cancellation_deadline_at
    assert result["cleanup"]["claim_id"] == "claim-1"


def test_durable_shell_cancel_reader_timeout_fails_closed_without_known_descendant(
    tmp_path,
    monkeypatch,
):
    from nodes.windows.umh_node import client as client_mod

    client = _durable_node_client(tmp_path / "store")
    req = client._durable_store.put_request(_durable_request())
    client._durable_store.mark_claimed(req.request_id, claim_id="claim-1")

    class _Proc:
        pid = 6161

        def poll(self):
            client._durable_store.request_cancel(req.request_id)
            return None

    class _Collector:
        @property
        def has_readers(self):
            return True

        def snapshot(self, *, join_timeout):
            return {
                "stdout": "partial",
                "stderr": "",
                "output_capture": {"timed_out": True, "concurrent_drain": True},
            }

    async def _terminate(_proc, *, graceful_timeout):
        return {"root_pid": _proc.pid, "process_residue": []}

    async def _running_ack(*_args, **_kwargs):
        client._durable_store.mark_running(
            req.request_id, claim_id="claim-1", process_tree={"node_pid": 1}
        )
        return {"ok": True}

    async def _send_event(*_args, **_kwargs):
        return {"ok": True}

    monkeypatch.setattr(client_mod.subprocess, "Popen", lambda *_args, **_kwargs: _Proc())
    monkeypatch.setattr(client_mod, "_DurablePipeCollector", lambda _proc: _Collector())
    monkeypatch.setattr(client_mod, "_durable_owned_process_tree_pids", lambda _pid: [6161])
    monkeypatch.setattr(client_mod, "_durable_alive_pids", lambda _pids: [])
    monkeypatch.setattr(client, "_terminate_durable_process_tree", _terminate)
    monkeypatch.setattr(client, "_announce_durable_running", _running_ack)
    monkeypatch.setattr(client, "_send_durable_event", _send_event)

    result = asyncio.run(
        client._execute_shell_for_durable(
            req,
            cap_name="shell",
            cap_params={"command": "echo ok"},
            claim_id="claim-1",
            process_tree={"node_pid": 1},
            timeout=5.0,
        )
    )

    assert result["success"] is False
    assert result["cleanup"]["reader_timeout_after_termination"] is True
    assert result["cleanup"]["process_residue"] == [
        {"state": "reader_timeout_descendant_identity_unknown"}
    ]


def test_durable_shell_timeout_preserves_bounded_redacted_partial_output(
    tmp_path, monkeypatch
):
    from nodes.windows.umh_node import client as client_mod

    client = _durable_node_client(tmp_path)
    req = client._durable_store.put_request(_durable_request())
    client._durable_store.mark_claimed(req.request_id, claim_id="claim-1")

    class _Proc:
        pid = 7777
        returncode = None

        def poll(self):
            return None

        def communicate(self, *, timeout=None):
            return (
                "phase-line\n" + ("x" * 25000),
                "Authorization: Bearer secret-token\n"
                + "stderr phase\n"
                + ("y" * 25000),
            )

    async def _terminate(_proc, *, graceful_timeout):
        return {"root_pid": _proc.pid, "process_residue": []}

    async def _running_ack(*_args, **_kwargs):
        client._durable_store.mark_running(
            req.request_id, claim_id="claim-1", process_tree={"node_pid": 1}
        )
        return {"ok": True}

    async def _send_event(*_args, **_kwargs):
        return {"ok": True}

    monkeypatch.setattr(client_mod.subprocess, "Popen", lambda *_args, **_kwargs: _Proc())
    monkeypatch.setattr(client, "_terminate_durable_process_tree", _terminate)
    monkeypatch.setattr(client, "_announce_durable_running", _running_ack)
    monkeypatch.setattr(client, "_send_durable_event", _send_event)

    result = asyncio.run(
        client._execute_shell_for_durable(
            req,
            cap_name="shell",
            cap_params={"command": "echo ok"},
            claim_id="claim-1",
            process_tree={"node_pid": 1},
            timeout=0.0,
        )
    )

    assert result["success"] is False
    assert result["error"] == "shell timed out after 0s"
    assert result["cleanup"]["process_residue"] == []
    assert len(result["stdout"]) <= client_mod._DURABLE_TIMEOUT_STDOUT_LIMIT
    assert len(result["stderr"]) <= client_mod._DURABLE_TIMEOUT_STDERR_LIMIT
    assert "secret-token" not in result["stderr"]
    assert "[redacted credential-bearing line]" in result["stderr"]
    assert result["output_capture"]["attempted"] is True
    assert result["output_capture"]["stdout_truncated"] is True
    assert result["output_capture"]["stderr_truncated"] is True
    assert result["output_capture"]["timed_out"] is False


def test_durable_shell_timeout_reader_timeout_fails_closed_without_known_descendant(
    tmp_path,
    monkeypatch,
):
    from nodes.windows.umh_node import client as client_mod

    client = _durable_node_client(tmp_path / "store")
    req = client._durable_store.put_request(_durable_request())
    client._durable_store.mark_claimed(req.request_id, claim_id="claim-1")

    class _Proc:
        pid = 6262

        def poll(self):
            return None

    class _Collector:
        @property
        def has_readers(self):
            return True

        def snapshot(self, *, join_timeout):
            return {
                "stdout": "partial",
                "stderr": "",
                "output_capture": {"timed_out": True, "concurrent_drain": True},
            }

    async def _terminate(_proc, *, graceful_timeout):
        return {"root_pid": _proc.pid, "process_residue": []}

    async def _running_ack(*_args, **_kwargs):
        client._durable_store.mark_running(
            req.request_id, claim_id="claim-1", process_tree={"node_pid": 1}
        )
        return {"ok": True}

    async def _send_event(*_args, **_kwargs):
        return {"ok": True}

    monkeypatch.setattr(client_mod.subprocess, "Popen", lambda *_args, **_kwargs: _Proc())
    monkeypatch.setattr(client_mod, "_DurablePipeCollector", lambda _proc: _Collector())
    monkeypatch.setattr(client_mod, "_durable_owned_process_tree_pids", lambda _pid: [6262])
    monkeypatch.setattr(client_mod, "_durable_alive_pids", lambda _pids: [])
    monkeypatch.setattr(client, "_terminate_durable_process_tree", _terminate)
    monkeypatch.setattr(client, "_announce_durable_running", _running_ack)
    monkeypatch.setattr(client, "_send_durable_event", _send_event)

    result = asyncio.run(
        client._execute_shell_for_durable(
            req,
            cap_name="shell",
            cap_params={"command": "echo ok"},
            claim_id="claim-1",
            process_tree={"node_pid": 1},
            timeout=0.0,
        )
    )

    assert result["success"] is False
    assert result["error"] == "shell timed out after 0s"
    assert result["cleanup"]["reader_timeout_after_termination"] is True
    assert result["cleanup"]["process_residue"] == [
        {"state": "reader_timeout_descendant_identity_unknown"}
    ]


def test_durable_shell_drains_large_stdout_and_stderr_while_running(tmp_path):
    from nodes.windows.umh_node import client as client_mod

    client = _durable_node_client(tmp_path / "store")
    client._ws = _DurableAckWs(client)
    req = client._durable_store.put_request(
        _durable_request(
            params={
                "argv": [
                    sys.executable,
                    "-c",
                    textwrap.dedent(
                        """
                        import json, sys
                        sys.stdout.write('out-start\\n' + ('O' * 262144) + '\\n')
                        sys.stdout.write(json.dumps({'status':'terminal','stream':'stdout'}) + '\\n')
                        sys.stdout.flush()
                        sys.stderr.write('Authorization: Bearer secret-token\\n')
                        sys.stderr.write('err-start\\n' + ('E' * 262144) + '\\n')
                        sys.stderr.write('terminal_result_flushed\\n')
                        sys.stderr.flush()
                        """
                    ),
                ],
                "timeout": 10,
            },
            risk_class="read_only",
        )
    )
    client._durable_store.mark_claimed(req.request_id, claim_id="claim-1")

    result = asyncio.run(
        client._execute_shell_for_durable(
            req,
            cap_name="shell",
            cap_params=req.params,
            claim_id="claim-1",
            process_tree={"node_pid": 1},
            timeout=10.0,
        )
    )

    assert result["success"] is True
    assert result["exit_code"] == 0
    assert "terminal" in result["stdout"]
    assert "terminal_result_flushed" in result["stderr"]
    assert "secret-token" not in result["stderr"]
    assert "[redacted credential-bearing line]" in result["stderr"]
    capture = result["output_capture"]
    assert capture["concurrent_drain"] is True
    assert capture["stdout_bytes_seen"] > client_mod._DURABLE_TIMEOUT_STDOUT_LIMIT
    assert capture["stderr_bytes_seen"] > client_mod._DURABLE_TIMEOUT_STDERR_LIMIT
    assert capture["stdout_truncated"] is True
    assert capture["stderr_truncated"] is True
    assert capture["total_truncated"] is True
    assert capture["redacted"] is True


def test_durable_shell_normal_exit_fails_closed_with_lingering_descendant(
    tmp_path, monkeypatch
):
    from nodes.windows.umh_node import client as client_mod

    client = _durable_node_client(tmp_path / "store")
    req = client._durable_store.put_request(_durable_request())
    client._durable_store.mark_claimed(req.request_id, claim_id="claim-1")

    class _Proc:
        pid = 5151
        returncode = 0

        def poll(self):
            return 0

    class _Collector:
        @property
        def has_readers(self):
            return True

        def snapshot(self, *, join_timeout):
            return {
                "stdout": "ok",
                "stderr": "",
                "output_capture": {"timed_out": False, "concurrent_drain": True},
            }

    async def _running_ack(*_args, **_kwargs):
        client._durable_store.mark_running(
            req.request_id,
            claim_id="claim-1",
            process_tree={"node_pid": 1},
        )
        return {"ok": True}

    async def _send_event(*_args, **_kwargs):
        return {"ok": True}

    monkeypatch.setattr(client_mod.subprocess, "Popen", lambda *_args, **_kwargs: _Proc())
    monkeypatch.setattr(client_mod, "_DurablePipeCollector", lambda _proc: _Collector())
    monkeypatch.setattr(client_mod, "_durable_owned_process_tree_pids", lambda _pid: [5151, 6161])
    monkeypatch.setattr(client_mod, "_durable_alive_pids", lambda _pids: [6161])
    monkeypatch.setattr(client_mod, "_durable_force_exact_pids", lambda _pids: ["force failed"])
    monkeypatch.setattr(client, "_announce_durable_running", _running_ack)
    monkeypatch.setattr(client, "_send_durable_event", _send_event)

    result = asyncio.run(
        client._execute_shell_for_durable(
            req,
            cap_name="shell",
            cap_params={"command": "echo ok"},
            claim_id="claim-1",
            process_tree={"node_pid": 1},
            timeout=5.0,
        )
    )

    assert result["success"] is False
    assert result["error"] == "durable success process residue unproven"
    assert result["cleanup"]["post_exit_process_check"] is True
    assert result["cleanup"]["post_exit_process_check_ok"] is True
    assert result["cleanup"]["process_residue_detected_after_exit"] is True
    assert result["cleanup"]["process_residue"] == [{"pid": 6161, "state": "still_alive"}]


def test_durable_shell_normal_exit_publishes_positive_zero_residue(
    tmp_path, monkeypatch
):
    from nodes.windows.umh_node import client as client_mod

    client = _durable_node_client(tmp_path / "store")
    req = client._durable_store.put_request(_durable_request())
    client._durable_store.mark_claimed(req.request_id, claim_id="claim-1")

    class _Proc:
        pid = 7171
        returncode = 0

        def poll(self):
            return 0

    class _Collector:
        @property
        def has_readers(self):
            return True

        def snapshot(self, *, join_timeout):
            return {
                "stdout": "ok",
                "stderr": "",
                "output_capture": {"timed_out": False, "concurrent_drain": True},
            }

    async def _running_ack(*_args, **_kwargs):
        client._durable_store.mark_running(
            req.request_id,
            claim_id="claim-1",
            process_tree={"node_pid": 1},
        )
        return {"ok": True}

    async def _send_event(*_args, **_kwargs):
        return {"ok": True}

    monkeypatch.setattr(client_mod.subprocess, "Popen", lambda *_args, **_kwargs: _Proc())
    monkeypatch.setattr(client_mod, "_DurablePipeCollector", lambda _proc: _Collector())
    monkeypatch.setattr(client_mod, "_durable_owned_process_tree_pids", lambda _pid: [7171])
    monkeypatch.setattr(client_mod, "_durable_alive_pids", lambda _pids: [])
    monkeypatch.setattr(client, "_announce_durable_running", _running_ack)
    monkeypatch.setattr(client, "_send_durable_event", _send_event)

    result = asyncio.run(
        client._execute_shell_for_durable(
            req,
            cap_name="shell",
            cap_params={"command": "echo ok"},
            claim_id="claim-1",
            process_tree={"node_pid": 1},
            timeout=5.0,
        )
    )

    assert result["success"] is True
    assert result["cleanup"] == {
        "root_pid": 7171,
        "post_exit_process_check": True,
        "post_exit_process_check_ok": True,
        "forced": False,
        "process_residue": [],
    }


def test_durable_shell_normal_exit_fails_closed_when_residue_check_errors(
    tmp_path, monkeypatch
):
    from nodes.windows.umh_node import client as client_mod

    client = _durable_node_client(tmp_path / "store")
    req = client._durable_store.put_request(_durable_request())
    client._durable_store.mark_claimed(req.request_id, claim_id="claim-1")

    class _Proc:
        pid = 8181
        returncode = 0

        def poll(self):
            return 0

    class _Collector:
        @property
        def has_readers(self):
            return True

        def snapshot(self, *, join_timeout):
            return {
                "stdout": "ok",
                "stderr": "",
                "output_capture": {"timed_out": False, "concurrent_drain": True},
            }

    async def _running_ack(*_args, **_kwargs):
        client._durable_store.mark_running(
            req.request_id,
            claim_id="claim-1",
            process_tree={"node_pid": 1},
        )
        return {"ok": True}

    async def _send_event(*_args, **_kwargs):
        return {"ok": True}

    def _raise(_pid):
        raise RuntimeError("scan failed")

    monkeypatch.setattr(client_mod.subprocess, "Popen", lambda *_args, **_kwargs: _Proc())
    monkeypatch.setattr(client_mod, "_DurablePipeCollector", lambda _proc: _Collector())
    monkeypatch.setattr(client_mod, "_durable_owned_process_tree_pids", _raise)
    monkeypatch.setattr(client, "_announce_durable_running", _running_ack)
    monkeypatch.setattr(client, "_send_durable_event", _send_event)

    result = asyncio.run(
        client._execute_shell_for_durable(
            req,
            cap_name="shell",
            cap_params={"command": "echo ok"},
            claim_id="claim-1",
            process_tree={"node_pid": 1},
            timeout=5.0,
        )
    )

    assert result["success"] is False
    assert result["error"] == "durable success process residue unproven"
    assert result["cleanup"]["post_exit_process_check_ok"] is False
    assert result["cleanup"]["process_residue"] == [
        {"state": "post_exit_process_tree_unverified"}
    ]


def test_durable_shell_normal_exit_fails_closed_when_alive_scan_errors(
    tmp_path, monkeypatch
):
    from nodes.windows.umh_node import client as client_mod

    client = _durable_node_client(tmp_path / "store")
    req = client._durable_store.put_request(_durable_request())
    client._durable_store.mark_claimed(req.request_id, claim_id="claim-1")

    class _Proc:
        pid = 9191
        returncode = 0

        def poll(self):
            return 0

    class _Collector:
        @property
        def has_readers(self):
            return True

        def snapshot(self, *, join_timeout):
            return {
                "stdout": "ok",
                "stderr": "",
                "output_capture": {"timed_out": False, "concurrent_drain": True},
            }

    async def _running_ack(*_args, **_kwargs):
        client._durable_store.mark_running(
            req.request_id,
            claim_id="claim-1",
            process_tree={"node_pid": 1},
        )
        return {"ok": True}

    async def _send_event(*_args, **_kwargs):
        return {"ok": True}

    def _alive_raises(_pids):
        raise RuntimeError("alive scan failed")

    monkeypatch.setattr(client_mod.subprocess, "Popen", lambda *_args, **_kwargs: _Proc())
    monkeypatch.setattr(client_mod, "_DurablePipeCollector", lambda _proc: _Collector())
    monkeypatch.setattr(client_mod, "_durable_owned_process_tree_pids", lambda _pid: [9191, 9292])
    monkeypatch.setattr(client_mod, "_durable_alive_pids", _alive_raises)
    monkeypatch.setattr(client, "_announce_durable_running", _running_ack)
    monkeypatch.setattr(client, "_send_durable_event", _send_event)

    result = asyncio.run(
        client._execute_shell_for_durable(
            req,
            cap_name="shell",
            cap_params={"command": "echo ok"},
            claim_id="claim-1",
            process_tree={"node_pid": 1},
            timeout=5.0,
        )
    )

    assert result["success"] is False
    assert result["error"] == "durable success process residue unproven"
    assert result["cleanup"]["post_exit_process_check_ok"] is False
    assert result["cleanup"]["process_residue"] == [
        {"state": "post_exit_alive_scan_unverified"}
    ]


def test_durable_process_tree_enumeration_nonzero_is_not_clean(monkeypatch):
    from nodes.windows.umh_node import client as client_mod

    monkeypatch.setattr(client_mod.sys, "platform", "linux")
    monkeypatch.setattr(
        client_mod.subprocess,
        "run",
        lambda *_args, **_kwargs: subprocess.CompletedProcess(
            args=["ps"], returncode=1, stdout="", stderr="ps failed"
        ),
    )

    with pytest.raises(RuntimeError, match="process tree enumeration failed rc=1"):
        client_mod._durable_owned_process_tree_pids(1234)


def test_durable_process_tree_enumeration_uses_posix_parent_map(monkeypatch):
    from nodes.windows.umh_node import client as client_mod

    monkeypatch.setattr(client_mod.sys, "platform", "linux")
    monkeypatch.setattr(
        client_mod.subprocess,
        "run",
        lambda *_args, **_kwargs: subprocess.CompletedProcess(
            args=["ps"],
            returncode=0,
            stdout="1234 1\n2345 1234\n3456 2345\n4567 1\n",
            stderr="",
        ),
    )

    assert client_mod._durable_owned_process_tree_pids(1234) == [1234, 2345, 3456]


def test_durable_shell_timeout_captures_phase_tail_and_cleans_descendant(tmp_path):
    child = tmp_path / "pipe_holder.py"
    child.write_text(
        "import sys,time\n"
        "print('descendant_retaining_stdout', flush=True)\n"
        "print('descendant_retaining_stderr', file=sys.stderr, flush=True)\n"
        "time.sleep(60)\n"
    )
    probe = tmp_path / "fake_probe.py"
    probe.write_text(
        "import subprocess,sys,time,json\n"
        "print('interpreter_entered', file=sys.stderr, flush=True)\n"
        "print('codex_process_spawned', file=sys.stderr, flush=True)\n"
        "print('inner_deadline_armed', file=sys.stderr, flush=True)\n"
        f"subprocess.Popen([sys.executable, {str(child)!r}], stdout=sys.stdout, stderr=sys.stderr)\n"
        "deadline=time.time()+0.2\n"
        "while time.time()<deadline: time.sleep(0.01)\n"
        "print('inner_timeout_fired', file=sys.stderr, flush=True)\n"
        "print(json.dumps({'status':'TIMEOUT','phase':'terminal_result_flushed'}), flush=True)\n"
        "time.sleep(60)\n"
    )
    client = _durable_node_client(tmp_path / "store")
    client._ws = _DurableAckWs(client)
    req = client._durable_store.put_request(
        _durable_request(
            params={"argv": [sys.executable, str(probe)], "timeout": 1},
            risk_class="read_only",
        )
    )
    client._durable_store.mark_claimed(req.request_id, claim_id="claim-1")

    result = asyncio.run(
        client._execute_shell_for_durable(
            req,
            cap_name="shell",
            cap_params=req.params,
            claim_id="claim-1",
            process_tree={"node_pid": 1},
            timeout=1.0,
        )
    )

    assert result["success"] is False
    assert result["error"] == "shell timed out after 1s"
    assert result["cleanup"]["process_residue"] == []
    assert "inner_deadline_armed" in result["stderr"]
    assert "inner_timeout_fired" in result["stderr"]
    assert "terminal_result_flushed" in result["stdout"]
    assert result["output_capture"]["concurrent_drain"] is True
    assert result["output_capture"]["timed_out"] is False


def test_durable_pipe_collector_reader_join_is_bounded(monkeypatch):
    from nodes.windows.umh_node.client import _DurablePipeCollector

    class _BlockingStream:
        def read(self, _size):
            import time

            time.sleep(60)
            return ""

        def close(self):
            return None

    class _Proc:
        pid = 9999
        stdout = _BlockingStream()
        stderr = _BlockingStream()

    collector = _DurablePipeCollector(_Proc())
    snapshot = collector.snapshot(join_timeout=0.01)

    assert snapshot["output_capture"]["timed_out"] is True
    assert snapshot["output_capture"]["concurrent_drain"] is True


def test_durable_pipe_buffer_redacts_long_split_credential_line():
    from nodes.windows.umh_node import client as client_mod
    from nodes.windows.umh_node.client import _BoundedStreamBuffer

    buf = _BoundedStreamBuffer(client_mod._DURABLE_TIMEOUT_STDERR_LIMIT)
    buf.append("Authorization: Bearer ")
    buf.append("secret-token-fragment" * 5000)
    buf.append("\nterminal_result_flushed\n")
    text = buf.text()

    assert "secret-token-fragment" not in text
    assert "[redacted credential-bearing line]" in text
    assert "terminal_result_flushed" in text
    assert len(text.encode("utf-8")) <= client_mod._DURABLE_TIMEOUT_STDERR_LIMIT


def test_durable_pipe_buffer_redacts_credential_marker_split_across_chunks():
    from nodes.windows.umh_node.client import _BoundedStreamBuffer

    buf = _BoundedStreamBuffer(20000)
    buf.append("Authoriz")
    buf.append("ation: Bearer tok_abc123\nterminal_result_flushed\n")
    text = buf.text()

    assert "tok_abc123" not in text
    assert "[redacted credential-bearing line]" in text
    assert "terminal_result_flushed" in text
    assert buf.redacted is True


def test_durable_pipe_buffer_redacts_long_regex_token_line():
    from nodes.windows.umh_node.client import _BoundedStreamBuffer

    buf = _BoundedStreamBuffer(20000)
    buf.append("token=")
    buf.append("secret-fragment" * 5000)
    buf.append("\nterminal_result_flushed\n")
    text = buf.text()

    assert "secret-fragment" not in text
    assert "[redacted credential-bearing line]" in text
    assert "terminal_result_flushed" in text
    assert buf.redacted is True


@pytest.mark.parametrize("prefix", ["api_key=", "password=", "secret=", "credential="])
def test_durable_pipe_buffer_redacts_long_secret_key_lines(prefix):
    from nodes.windows.umh_node.client import _BoundedStreamBuffer

    buf = _BoundedStreamBuffer(20000)
    buf.append(prefix)
    buf.append("secret-fragment" * 5000)
    buf.append("\nterminal_result_flushed\n")
    text = buf.text()

    assert "secret-fragment" not in text
    assert "[redacted credential-bearing line]" in text
    assert "terminal_result_flushed" in text
    assert buf.redacted is True


def test_durable_pipe_buffer_redacts_long_bare_openai_key_line():
    from nodes.windows.umh_node.client import _BoundedStreamBuffer

    buf = _BoundedStreamBuffer(20000)
    buf.append("prefix ")
    buf.append("sk-" + ("A" * 50000))
    buf.append("\nterminal_result_flushed\n")
    text = buf.text()

    assert "sk-" not in text
    assert "AAAAAA" not in text
    assert "[redacted credential-bearing line]" in text
    assert "terminal_result_flushed" in text
    assert buf.redacted is True


def test_durable_pipe_buffer_redacts_regex_token_marker_split_across_chunks():
    from nodes.windows.umh_node.client import _BoundedStreamBuffer

    buf = _BoundedStreamBuffer(20000)
    buf.append("prefix " + ("x" * 100) + "tok")
    buf.append("en=secret-fragment" * 4000)
    buf.append("\nterminal_result_flushed\n")
    text = buf.text()

    assert "secret-fragment" not in text
    assert "[redacted credential-bearing line]" in text
    assert "terminal_result_flushed" in text
    assert buf.redacted is True


def test_durable_pipe_buffer_pending_line_is_bounded_without_newline():
    from nodes.windows.umh_node import client as client_mod
    from nodes.windows.umh_node.client import _BoundedStreamBuffer

    buf = _BoundedStreamBuffer(client_mod._DURABLE_TIMEOUT_STDOUT_LIMIT)
    buf.append("x" * 120000)

    assert len(buf._pending_line) <= client_mod._DURABLE_SECRET_SCAN_TAIL_CHARS
    assert buf.truncated is True
    assert buf.bytes_seen == 120000
    assert len(buf.text().encode("utf-8")) <= client_mod._DURABLE_TIMEOUT_STDOUT_LIMIT


def test_durable_pipe_buffer_enforces_byte_limit_for_non_ascii_output():
    from nodes.windows.umh_node import client as client_mod
    from nodes.windows.umh_node.client import _BoundedStreamBuffer

    buf = _BoundedStreamBuffer(client_mod._DURABLE_TIMEOUT_STDOUT_LIMIT)
    buf.append("é" * 30000)
    text = buf.text()

    assert buf.truncated is True
    assert buf.bytes_seen == len(("é" * 30000).encode("utf-8"))
    assert len(text.encode("utf-8")) <= client_mod._DURABLE_TIMEOUT_STDOUT_LIMIT


def test_durable_pipe_collector_redaction_metadata_false_for_clean_output():
    from nodes.windows.umh_node.client import _DurablePipeCollector

    class _Stream:
        def __init__(self, chunks):
            self._chunks = list(chunks)

        def read(self, _size):
            if self._chunks:
                return self._chunks.pop(0)
            return ""

        def close(self):
            return None

    class _Proc:
        pid = 4343
        stdout = _Stream(["clean output\n"])
        stderr = _Stream(["clean stderr\n"])

    snapshot = _DurablePipeCollector(_Proc()).snapshot(join_timeout=1.0)

    assert snapshot["stdout"] == "clean output\n"
    assert snapshot["stderr"] == "clean stderr\n"
    assert snapshot["output_capture"]["redacted"] is False


def test_durable_pipe_collector_does_not_redact_clean_policy_words():
    from nodes.windows.umh_node.client import _DurablePipeCollector

    class _Stream:
        def __init__(self, chunks):
            self._chunks = list(chunks)

        def read(self, _size):
            if self._chunks:
                return self._chunks.pop(0)
            return ""

        def close(self):
            return None

    class _Proc:
        pid = 4444
        stdout = _Stream(["authorization required by policy\n"])
        stderr = _Stream(["no credential material here\n"])

    snapshot = _DurablePipeCollector(_Proc()).snapshot(join_timeout=1.0)

    assert snapshot["stdout"] == "authorization required by policy\n"
    assert snapshot["stderr"] == "no credential material here\n"
    assert snapshot["output_capture"]["redacted"] is False


def test_durable_shell_reader_timeout_after_root_exit_fails_closed(tmp_path, monkeypatch):
    from nodes.windows.umh_node import client as client_mod

    client = _durable_node_client(tmp_path / "store")
    req = client._durable_store.put_request(_durable_request())
    client._durable_store.mark_claimed(req.request_id, claim_id="claim-1")

    class _Proc:
        pid = 4242
        returncode = 0

        def poll(self):
            return 0

    class _Collector:
        def snapshot(self, *, join_timeout):
            return {
                "stdout": "partial",
                "stderr": "",
                "output_capture": {"timed_out": True, "concurrent_drain": True},
            }

    async def _running_ack(*_args, **_kwargs):
        client._durable_store.mark_running(
            req.request_id, claim_id="claim-1", process_tree={"node_pid": 1}
        )
        return {"ok": True}

    async def _send_event(*_args, **_kwargs):
        return {"ok": True}

    async def _terminate(_proc, *, graceful_timeout):
        return {"root_pid": _proc.pid, "process_residue": []}

    monkeypatch.setattr(client_mod.subprocess, "Popen", lambda *_args, **_kwargs: _Proc())
    monkeypatch.setattr(client_mod, "_DurablePipeCollector", lambda _proc: _Collector())
    monkeypatch.setattr(client_mod, "_durable_owned_process_tree_pids", lambda _pid: [4242])
    monkeypatch.setattr(client, "_announce_durable_running", _running_ack)
    monkeypatch.setattr(client, "_send_durable_event", _send_event)
    monkeypatch.setattr(client, "_terminate_durable_process_tree", _terminate)

    result = asyncio.run(
        client._execute_shell_for_durable(
            req,
            cap_name="shell",
            cap_params={"command": "echo ok"},
            claim_id="claim-1",
            process_tree={"node_pid": 1},
            timeout=5.0,
        )
    )

    assert result["success"] is False
    assert result["error"] == "durable output readers timed out after process exit"
    assert result["cleanup"]["process_residue"] == [
        {"state": "reader_timeout_descendant_identity_unknown"}
    ]


def test_durable_shell_reader_timeout_after_root_exit_force_cleans_known_tree(
    tmp_path,
    monkeypatch,
):
    from nodes.windows.umh_node import client as client_mod

    client = _durable_node_client(tmp_path / "store")
    req = client._durable_store.put_request(_durable_request())
    client._durable_store.mark_claimed(req.request_id, claim_id="claim-1")
    forced: list[list[int]] = []
    alive_calls = 0

    class _Proc:
        pid = 4242
        returncode = 0

        def poll(self):
            return 0

    class _Collector:
        @property
        def has_readers(self):
            return True

        def snapshot(self, *, join_timeout):
            return {
                "stdout": "partial",
                "stderr": "",
                "output_capture": {"timed_out": True, "concurrent_drain": True},
            }

    async def _running_ack(*_args, **_kwargs):
        client._durable_store.mark_running(
            req.request_id, claim_id="claim-1", process_tree={"node_pid": 1}
        )
        return {"ok": True}

    async def _send_event(*_args, **_kwargs):
        return {"ok": True}

    async def _terminate(_proc, *, graceful_timeout):
        return {"root_pid": _proc.pid, "process_residue": []}

    def _alive(pids):
        nonlocal alive_calls
        alive_calls += 1
        if alive_calls == 1:
            return [4343]
        return []

    def _force(pids):
        forced.append(list(pids))
        return [f"exact pid force cleanup pid={pid}" for pid in pids]

    monkeypatch.setattr(client_mod.subprocess, "Popen", lambda *_args, **_kwargs: _Proc())
    monkeypatch.setattr(client_mod, "_DurablePipeCollector", lambda _proc: _Collector())
    monkeypatch.setattr(client_mod, "_durable_owned_process_tree_pids", lambda _pid: [4242, 4343])
    monkeypatch.setattr(client_mod, "_durable_alive_pids", _alive)
    monkeypatch.setattr(client_mod, "_durable_force_exact_pids", _force)
    monkeypatch.setattr(client, "_announce_durable_running", _running_ack)
    monkeypatch.setattr(client, "_send_durable_event", _send_event)
    monkeypatch.setattr(client, "_terminate_durable_process_tree", _terminate)

    result = asyncio.run(
        client._execute_shell_for_durable(
            req,
            cap_name="shell",
            cap_params={"command": "echo ok"},
            claim_id="claim-1",
            process_tree={"node_pid": 1},
            timeout=5.0,
        )
    )

    assert result["success"] is False
    assert result["error"] == "durable output readers timed out after process exit"
    assert forced == [[4343]]
    assert result["cleanup"]["process_residue"] == []


def test_durable_process_cleanup_targets_posix_process_group(tmp_path, monkeypatch):
    from nodes.windows.umh_node import client as client_mod

    client = _durable_node_client(tmp_path)
    signaled: list[tuple[int, int]] = []

    class _Proc:
        pid = 8888

        def __init__(self):
            self.wait_calls = 0

        def wait(self, *, timeout=None):
            self.wait_calls += 1
            if self.wait_calls == 1:
                raise subprocess.TimeoutExpired(cmd=["fake"], timeout=timeout)
            return 0

        def kill(self):
            raise AssertionError("root-only kill must not be used for process-group cleanup")

        def terminate(self):
            raise AssertionError("root-only terminate must not be used for process-group cleanup")

    proc = _Proc()
    monkeypatch.setattr(client_mod.sys, "platform", "linux")
    monkeypatch.setattr(
        client_mod.os,
        "killpg",
        lambda pid, sig: signaled.append((pid, sig)),
    )

    cleanup = asyncio.run(client._terminate_durable_process_tree(proc, graceful_timeout=0.01))

    assert signaled == [(8888, client_mod.signal.SIGTERM), (8888, client_mod.signal.SIGKILL)]
    assert cleanup["forced"] is True
    assert cleanup["process_residue"] == []


# ── Remote write-class terminal dispatch requires DurableRemote ────────────


def test_remote_terminal_write_class_requires_durable_remote(monkeypatch):
    """create/send write-class operations never go through sync mesh."""

    import transports.api.cockpit_workstation_control_routes as routes

    called = {"post": 0, "mutation": 0}

    async def _fake_post(payload, timeout):
        called["post"] += 1
        raise AssertionError("write-class terminal dispatch must not POST to sync relay")

    def _fake_governed(*_args, **_kwargs):
        called["mutation"] += 1
        raise AssertionError("write-class terminal dispatch must not create sync mutation")

    monkeypatch.setattr(routes, "_post_to_relay", _fake_post)
    monkeypatch.setattr(routes, "governed_mutation", _fake_governed)

    res = asyncio.run(routes._remote_terminal_dispatch("node-a", "create", {"shell": "powershell"}))
    assert res["ok"] is False
    assert res["status"] == "durable_remote_required"

    res2 = asyncio.run(
        routes._remote_terminal_dispatch("node-a", "send", {"name": "s1", "text": "echo hi"})
    )
    assert res2["ok"] is False
    assert res2["status"] == "durable_remote_required"
    assert called == {"post": 0, "mutation": 0}


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
    assert captured["payload"]["effect_class"] == READ_ONLY_EFFECT
    assert captured["payload"]["request_id"]
    assert captured["payload"]["correlation_id"].startswith("cockpit-terminal:list:")
    assert captured["payload"]["idempotency_key"] == captured["payload"]["request_id"]
    assert captured["payload"]["payload_digest"] == canonical_payload_digest({})
    assert captured["payload"].get("verdict_token", "") == ""


def test_remote_broadcast_write_class_requires_durable_remote():
    import transports.api.cockpit_broadcast_routes as routes

    with pytest.raises(HTTPException) as exc:
        asyncio.run(routes._dispatch_remote("node-a", "start", {}, timeout=1))

    assert exc.value.status_code == 409
    assert "DurableRemote" in str(exc.value)
