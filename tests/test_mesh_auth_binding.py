"""Mesh trust boundary — WS auth, token→node binding, header transport, relay read auth.

Deterministic. No real network, no real Windows node. Exercises the pure auth
and binding logic on NodeMeshServer plus the header/URL token extraction.

Covers (WP-P0-002):
  - no tokens configured  → WS refused (fail-closed)
  - valid token           → accepted
  - token bound to node A  → rejected when declaring node B
  - token read from header (Authorization: Bearer), not URL query string
  - /nodes and /health require relay auth (fail-closed when secret unset)

Run: pytest tests/test_mesh_auth_binding.py -q
"""
# ruff: noqa: E402

from __future__ import annotations

import os
import sys
from types import SimpleNamespace

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _REPO_ROOT)

from substrate.execution.executor import WorkPacketExecutor
from substrate.sockets.capability_socket import CapabilitySocket
from substrate.sockets.outcome_socket import OutcomeSocket
from substrate.sockets.signal_socket import SignalSocket
from substrate.sockets.view_socket import ViewSocket
from transports.node_mesh.config import MeshConfig, NodeTokenEntry
from transports.node_mesh.server import NodeMeshServer


def _make_server(tokens: dict[str, NodeTokenEntry] | None = None) -> NodeMeshServer:
    config = MeshConfig(port=0, node_tokens=tokens or {})
    return NodeMeshServer(
        config=config,
        executor=WorkPacketExecutor(),
        signal_socket=SignalSocket(),
        capability_socket=CapabilitySocket(),
        outcome_socket=OutcomeSocket(),
        view_socket=ViewSocket(),
    )


def _fake_ws(path: str = "/ws", headers: dict[str, str] | None = None):
    class _Headers(dict):
        def get(self, k, default=None):  # case-insensitive-ish helper
            return dict.get(self, k, dict.get(self, k.lower(), default))

    hdrs = _Headers(headers or {})
    return SimpleNamespace(request=SimpleNamespace(path=path, headers=hdrs))


# ── WS auth fail-closed ────────────────────────────────────────────────────


def test_no_tokens_configured_refuses_connection():
    server = _make_server(tokens={})
    # Fail-closed: an unconfigured mesh refuses every token, including empty.
    assert server._authenticate("") is False
    assert server._authenticate("anything") is False


def test_valid_token_accepted():
    tokens = {"node-a": NodeTokenEntry(node_id="node-a", token="secret-a")}
    server = _make_server(tokens=tokens)
    assert server._authenticate("secret-a") is True


def test_invalid_token_rejected():
    tokens = {"node-a": NodeTokenEntry(node_id="node-a", token="secret-a")}
    server = _make_server(tokens=tokens)
    assert server._authenticate("wrong") is False
    assert server._authenticate("") is False


# ── Token → node binding ───────────────────────────────────────────────────


def test_token_bound_to_correct_node():
    tokens = {
        "node-a": NodeTokenEntry(node_id="node-a", token="secret-a"),
        "node-b": NodeTokenEntry(node_id="node-b", token="secret-b"),
    }
    server = _make_server(tokens=tokens)
    assert server._node_id_for_token("secret-a") == "node-a"
    assert server._node_id_for_token("secret-b") == "node-b"


def test_token_for_node_a_does_not_map_to_node_b():
    tokens = {
        "node-a": NodeTokenEntry(node_id="node-a", token="secret-a"),
        "node-b": NodeTokenEntry(node_id="node-b", token="secret-b"),
    }
    server = _make_server(tokens=tokens)
    # secret-a is bound to node-a — it must NOT resolve to node-b.
    assert server._node_id_for_token("secret-a") != "node-b"


def test_unknown_token_binds_to_no_node():
    tokens = {"node-a": NodeTokenEntry(node_id="node-a", token="secret-a")}
    server = _make_server(tokens=tokens)
    assert server._node_id_for_token("unknown") is None
    assert server._node_id_for_token("") is None


# ── Token transport: header preferred, URL still readable ──────────────────


def test_token_read_from_authorization_header():
    server = _make_server()
    ws = _fake_ws(path="/ws", headers={"authorization": "Bearer header-token"})
    assert server._extract_token(ws) == "header-token"


def test_token_read_from_mesh_header():
    server = _make_server()
    ws = _fake_ws(path="/ws", headers={"x-umh-mesh-token": "mesh-token"})
    assert server._extract_token(ws) == "mesh-token"


def test_header_token_wins_over_url_token():
    server = _make_server()
    ws = _fake_ws(
        path="/ws?token=url-token",
        headers={"authorization": "Bearer header-token"},
    )
    # Header is preferred so the token never depends on the leaky URL.
    assert server._extract_token(ws) == "header-token"


def test_url_token_still_readable_for_legacy_nodes():
    server = _make_server()
    ws = _fake_ws(path="/ws?token=url-token", headers={})
    assert server._extract_token(ws) == "url-token"


# ── /nodes and /health require relay auth (fail-closed) ─────────────────────


def test_relay_auth_fail_closed_when_secret_unset(monkeypatch):
    monkeypatch.delenv("UMH_MESH_RELAY_SECRET", raising=False)
    # No secret → every request refused, even one carrying a bearer.
    assert NodeMeshServer._relay_auth_ok("") is False
    assert NodeMeshServer._relay_auth_ok("Bearer anything") is False


def test_relay_auth_fail_closed_when_secret_is_whitespace(monkeypatch):
    monkeypatch.setenv("UMH_MESH_RELAY_SECRET", "   ")

    assert NodeMeshServer._relay_auth_ok("Bearer    ") is False
    assert NodeMeshServer._relay_auth_ok("Bearer anything") is False


def test_relay_auth_requires_matching_bearer(monkeypatch):
    monkeypatch.setenv("UMH_MESH_RELAY_SECRET", "relay-secret")
    assert NodeMeshServer._relay_auth_ok("Bearer relay-secret") is True
    assert NodeMeshServer._relay_auth_ok("Bearer wrong") is False
    assert NodeMeshServer._relay_auth_ok("") is False
    assert NodeMeshServer._relay_auth_ok("relay-secret") is False  # missing "Bearer "
