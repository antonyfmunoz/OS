"""Mesh dispatch port — substrate-layer abstraction for governed remote dispatch.

Substrate code that needs to actuate a remote mesh node (e.g. the browser
evidence collector) must NOT reach the mesh HTTP relay directly — that raw path
carried no governance verdict and no relay authentication, and it forced
substrate to know transport details. Instead it calls the thin wrapper here.

The port always has at least a built-in governed default dispatcher that signs
a verdict and authenticates to the relay. The transport layer MAY register a
richer dispatcher (e.g. one that also records a governed mutation). There is NO
ungoverned dispatch path.

Fail-closed contract: the built-in dispatcher only sends explicitly read-only
operations through synchronous mesh. Consequential writes must enter
DurableRemote. Read-only sync dispatch requires UMH_MESH_RELAY_SECRET to
authenticate to the relay. Missing relay auth → not-ok result, no network call.

This module imports only stdlib + substrate.execution.mesh_verdict — never
transports — so dependency direction is preserved.

UMH substrate subsystem. Instance-agnostic.
"""

from __future__ import annotations

import json
import logging
import os
import urllib.request
from typing import Any, Callable, Optional
from uuid import uuid4

logger = logging.getLogger(__name__)

_mesh_dispatch_fn: Optional[Callable[..., dict[str, Any]]] = None


def register_mesh_dispatch(fn: Callable[..., dict[str, Any]]) -> None:
    """Register a concrete governed dispatcher, overriding the default.

    The transport layer may register a richer dispatcher. When none is
    registered, the built-in governed default (`_default_governed_dispatch`) is
    used — it signs a verdict and attaches the relay bearer secret.
    """
    global _mesh_dispatch_fn
    _mesh_dispatch_fn = fn


def is_mesh_dispatch_available() -> bool:
    """True — the port always has at least the governed default dispatcher."""
    return True


def _default_governed_dispatch(
    node_id: str,
    capability: str,
    params: dict[str, Any],
    *,
    risk_class: str = "reversible_write",
    timeout: int = 300,
) -> dict[str, Any]:
    """Built-in governed dispatcher: sign a verdict, authenticate to the relay.

    Fail-closed: synchronous mesh only admits explicitly read-only operations.
    Consequential writes must enter DurableRemote so canonical request
    trajectory/idempotency owns redelivery and replay.
    """
    from substrate.execution.mesh_verdict import (
        canonical_payload_digest,
        canonical_sync_effect_policy,
    )

    declared_effect = "READ_ONLY"
    policy = canonical_sync_effect_policy(capability, declared_effect_class=declared_effect)
    if not policy.sync_allowed:
        return {
            "ok": False,
            "error": policy.reason,
            "status": "durable_remote_required"
            if policy.authoritative_effect_class
            else "effect_policy_unavailable",
            "authoritative_effect_class": policy.authoritative_effect_class,
            "effect_policy": policy.policy_id,
        }

    relay_secret = os.environ.get("UMH_MESH_RELAY_SECRET", "").strip()
    if not relay_secret:
        return {
            "ok": False,
            "error": "mesh relay secret unset (fail-closed)",
            "status": "relay_secret_unset",
        }

    request_id = f"sync-{uuid4().hex}"
    correlation_id = f"mesh-dispatch-port:{request_id}"
    payload_digest = canonical_payload_digest(params)

    relay_host = os.environ.get("UMH_MESH_RELAY_HOST", "localhost")
    relay_port = int(os.environ.get("UMH_MESH_HTTP_PORT", "8095"))
    payload = json.dumps(
        {
            "request_id": request_id,
            "correlation_id": correlation_id,
            "candidate_sha": os.environ.get("UMH_SOURCE_SHA", "").strip(),
            "effect_class": declared_effect,
            "authoritative_effect_class": policy.authoritative_effect_class,
            "effect_policy": policy.policy_id,
            "idempotency_key": request_id,
            "payload_digest": payload_digest,
            "node_id": node_id,
            "capability": capability,
            "params": params,
            "risk_class": risk_class,
            "verdict_token": "",
            "timeout": timeout,
        }
    ).encode()

    req = urllib.request.Request(
        f"http://{relay_host}:{relay_port}/dispatch",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {relay_secret}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout + 30) as resp:
            return json.loads(resp.read().decode())
    except Exception as exc:
        logger.error("mesh dispatch to %s failed: %s", node_id, exc)
        return {"ok": False, "error": f"dispatch failed: {exc}", "status": "transport_error"}


def mesh_dispatch(
    node_id: str,
    capability: str,
    params: dict[str, Any],
    *,
    risk_class: str = "reversible_write",
    timeout: int = 300,
) -> dict[str, Any]:
    """Dispatch a capability to a mesh node through the governed path.

    Uses a registered dispatcher when present, otherwise the built-in governed
    default. The built-in path is read-only only; consequential writes must use
    DurableRemote rather than synchronous mesh.
    """
    fn = _mesh_dispatch_fn or _default_governed_dispatch
    return fn(
        node_id=node_id,
        capability=capability,
        params=params,
        risk_class=risk_class,
        timeout=timeout,
    )
