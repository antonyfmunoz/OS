"""Mesh verdict token — signed governance verdicts for remote node dispatch.

The mesh trust boundary requires that a remote node can independently verify
that a write-class capability request carries a genuine governance verdict
before executing it. The node cannot reach back to the orchestrator's spine
synchronously, so the verdict must be self-verifiable: a compact HMAC-signed
token binding the verdict to a specific node + capability + risk class + expiry.

Both the orchestrator (transports/node_mesh) and the node daemon (nodes/) import
this single module — it is the canonical signer AND verifier. It is pure stdlib
(hmac, hashlib, base64, json) with no substrate imports so it is safe to import
from the node daemon, which ships as a lightweight standalone process.

Fail-closed contract:
  - No secret configured  → sign() raises; verify() returns invalid.
  - Malformed / tampered   → invalid.
  - Expired                → invalid.
  - node_id / capability mismatch → invalid.

The shared secret comes from the environment (UMH_MESH_VERDICT_SECRET), sourced
from 1Password like every other mesh secret. It is NEVER hardcoded.

UMH substrate subsystem. Instance-agnostic.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time
from dataclasses import dataclass
from typing import Any

_TOKEN_VERSION = "v1"
_VERDICT_SECRET_ENV = "UMH_MESH_VERDICT_SECRET"

# Risk classes that require a validated verdict before the node may execute.
# Anything that is not strictly read-only is treated as write-class (fail-closed:
# an unknown / unrecognized risk class is treated as write-class, never as
# read-only).
_READ_ONLY_CLASSES = frozenset({"read_only", "readonly", "read"})


def get_verdict_secret() -> str:
    """Return the shared mesh verdict secret from the environment.

    Empty string when unset — callers MUST treat empty as fail-closed.
    """
    return os.environ.get(_VERDICT_SECRET_ENV, "").strip()


def is_write_class(risk_class: str | None) -> bool:
    """True when a risk class requires a validated verdict (fail-closed).

    Only an explicit read-only class is exempt. None / unknown / anything
    else is write-class and requires a verdict.
    """
    if not risk_class:
        return True
    return risk_class.strip().lower() not in _READ_ONLY_CLASSES


@dataclass(frozen=True)
class VerdictCheck:
    """Result of verifying a mesh verdict token."""

    valid: bool
    reason: str = ""
    verdict_id: str = ""
    node_id: str = ""
    capability: str = ""
    risk_class: str = ""


def _b64e(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _b64d(s: str) -> bytes:
    pad = "=" * (-len(s) % 4)
    return base64.urlsafe_b64decode(s + pad)


def _sign_payload(payload_b64: str, secret: str) -> str:
    mac = hmac.new(secret.encode("utf-8"), payload_b64.encode("ascii"), hashlib.sha256)
    return mac.hexdigest()


def sign_verdict(
    *,
    verdict_id: str,
    node_id: str,
    capability: str,
    risk_class: str,
    ttl_seconds: int = 600,
    secret: str | None = None,
    now: float | None = None,
) -> str:
    """Produce a signed verdict token for a remote node dispatch.

    Binds the verdict to node_id + capability + risk_class + expiry so a token
    minted for node A / capability X cannot authorize node B or capability Y.

    Raises ValueError when no secret is configured — signing must never proceed
    without a secret (fail-closed).
    """
    secret = secret.strip() if secret is not None else get_verdict_secret()
    if not secret:
        raise ValueError("cannot sign mesh verdict: UMH_MESH_VERDICT_SECRET is not configured")
    if not verdict_id or not node_id or not capability:
        raise ValueError("verdict_id, node_id and capability are all required")

    issued = float(now if now is not None else time.time())
    payload: dict[str, Any] = {
        "vid": verdict_id,
        "nid": node_id,
        "cap": capability,
        "rc": risk_class,
        "iat": int(issued),
        "exp": int(issued + max(1, int(ttl_seconds))),
    }
    payload_b64 = _b64e(json.dumps(payload, separators=(",", ":"), sort_keys=True).encode())
    sig = _sign_payload(payload_b64, secret)
    return f"{_TOKEN_VERSION}.{payload_b64}.{sig}"


def verify_verdict(
    token: str,
    *,
    expected_node_id: str,
    expected_capability: str,
    secret: str | None = None,
    now: float | None = None,
) -> VerdictCheck:
    """Verify a signed verdict token against the expected node + capability.

    Fail-closed: returns VerdictCheck(valid=False, ...) for a missing secret,
    a malformed token, a bad signature, an expired token, or a node/capability
    mismatch. Only a fully-valid token yields valid=True.
    """
    secret = secret.strip() if secret is not None else get_verdict_secret()
    if not secret:
        return VerdictCheck(False, "no verdict secret configured (fail-closed)")
    if not token or not isinstance(token, str):
        return VerdictCheck(False, "empty or non-string token")

    parts = token.split(".")
    if len(parts) != 3:
        return VerdictCheck(False, "malformed token (expected 3 parts)")
    version, payload_b64, sig = parts
    if version != _TOKEN_VERSION:
        return VerdictCheck(False, f"unsupported token version: {version}")

    expected_sig = _sign_payload(payload_b64, secret)
    if not hmac.compare_digest(sig, expected_sig):
        return VerdictCheck(False, "signature mismatch")

    try:
        payload = json.loads(_b64d(payload_b64))
    except Exception:
        return VerdictCheck(False, "payload decode failed")

    vid = str(payload.get("vid", ""))
    nid = str(payload.get("nid", ""))
    cap = str(payload.get("cap", ""))
    rc = str(payload.get("rc", ""))
    exp = payload.get("exp", 0)

    cur = float(now if now is not None else time.time())
    try:
        if cur > float(exp):
            return VerdictCheck(False, "verdict expired", vid, nid, cap, rc)
    except (TypeError, ValueError):
        return VerdictCheck(False, "invalid expiry", vid, nid, cap, rc)

    if nid != expected_node_id:
        return VerdictCheck(
            False, f"node mismatch: token={nid} expected={expected_node_id}", vid, nid, cap, rc
        )
    if cap != expected_capability:
        return VerdictCheck(
            False,
            f"capability mismatch: token={cap} expected={expected_capability}",
            vid,
            nid,
            cap,
            rc,
        )

    return VerdictCheck(True, "ok", vid, nid, cap, rc)
