"""Mesh dispatch port — substrate-layer abstraction for governed remote dispatch.

Substrate code that needs to actuate a remote mesh node (e.g. the browser
evidence collector) must NOT reach the mesh HTTP relay directly — that raw path
carried no governance verdict and no relay authentication, and it forced
substrate to know transport details. Instead it calls the thin wrapper here.

The port always has at least a built-in governed default dispatcher that signs
a verdict and authenticates to the relay. The transport layer MAY register a
richer dispatcher (e.g. one that also records a governed mutation). There is NO
ungoverned dispatch path.

Fail-closed contract: the built-in dispatcher requires UMH_MESH_VERDICT_SECRET
(to mint the verdict for write-class capabilities) and UMH_MESH_RELAY_SECRET (to
authenticate to the relay). Missing either → not-ok result, no network call.

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

    Fail-closed: requires UMH_MESH_VERDICT_SECRET (to mint the verdict for
    write-class capabilities) and UMH_MESH_RELAY_SECRET (to authenticate to the
    relay). Missing either → not-ok result, no network call. The signed verdict
    travels in the payload so the relay and the node both validate it before
    execution.
    """
    from substrate.execution.mesh_verdict import get_verdict_secret, is_write_class, sign_verdict

    relay_secret = os.environ.get("UMH_MESH_RELAY_SECRET", "").strip()
    if not relay_secret:
        return {
            "ok": False,
            "error": "mesh relay secret unset (fail-closed)",
            "status": "relay_secret_unset",
        }

    verdict_token = ""
    if is_write_class(risk_class):
        if not get_verdict_secret():
            return {
                "ok": False,
                "error": "mesh verdict secret unset (fail-closed)",
                "status": "verdict_secret_unset",
            }
        verdict_token = sign_verdict(
            verdict_id=uuid4().hex,
            node_id=node_id,
            capability=capability,
            risk_class=risk_class,
            ttl_seconds=int(timeout) + 30,
        )

    relay_host = os.environ.get("UMH_MESH_RELAY_HOST", "localhost")
    relay_port = int(os.environ.get("UMH_MESH_HTTP_PORT", "8095"))
    payload = json.dumps(
        {
            "node_id": node_id,
            "capability": capability,
            "params": params,
            "risk_class": risk_class,
            "verdict_token": verdict_token,
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
    default. Both paths sign a verdict for write-class capabilities and
    authenticate to the relay — there is no ungoverned dispatch here.
    """
    fn = _mesh_dispatch_fn or _default_governed_dispatch
    return fn(
        node_id=node_id,
        capability=capability,
        params=params,
        risk_class=risk_class,
        timeout=timeout,
    )
