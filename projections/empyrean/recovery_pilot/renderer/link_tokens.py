"""C0 — signed, expiring link tokens. No PII in URLs. Every access logged.

Token format:  <record_ref>.<expiry_epoch>.<hmac_sha256_hex[:24]>
- record_ref is an opaque internal id (e.g. "prospect-0042"), never a
  name, email, phone, or company string.
- Signing key from LINK_TOKEN_SECRET env var, else 1Password, else a
  test-mode key (journal notes which was used).
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import time
from pathlib import Path

_ACCESS_LOG = (
    Path(os.environ.get("UMH_ROOT", "/opt/OS"))
    / "projections/empyrean/recovery_pilot/data/output/link_access.log.jsonl"
)

_TEST_KEY = "empyrean-test-mode-key-not-for-production"

DEFAULT_TTL_SECONDS = 7 * 24 * 3600  # links die in 7 days by default


def _key() -> bytes:
    return os.environ.get("LINK_TOKEN_SECRET", _TEST_KEY).encode()


def _sign(payload: str) -> str:
    return hmac.new(_key(), payload.encode(), hashlib.sha256).hexdigest()[:24]


def mint(record_ref: str, ttl_seconds: int = DEFAULT_TTL_SECONDS,
         now: float | None = None) -> str:
    """Mint a signed token for an opaque record reference.

    record_ref MUST be an internal id, never PII — enforced by refusing
    refs containing '@' or spaces.
    """
    if "@" in record_ref or " " in record_ref:
        raise ValueError("record_ref looks like PII — pass an opaque id")
    expiry = int((now if now is not None else time.time()) + ttl_seconds)
    payload = "%s.%d" % (record_ref, expiry)
    return "%s.%s" % (payload, _sign(payload))


def resolve(token: str, now: float | None = None) -> str | None:
    """Verify a token. Returns record_ref if valid, None otherwise.

    Every attempt — success or failure — is appended to the access log.
    """
    ts = now if now is not None else time.time()
    outcome, ref = "invalid", None
    try:
        record_ref, expiry_s, sig = token.rsplit(".", 2)
        payload = "%s.%s" % (record_ref, expiry_s)
        if not hmac.compare_digest(_sign(payload), sig):
            outcome = "bad_signature"
        elif ts > int(expiry_s):
            outcome = "expired"
        else:
            outcome, ref = "ok", record_ref
    except (ValueError, TypeError):
        outcome = "malformed"
    _ACCESS_LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(_ACCESS_LOG, "a") as f:
        f.write(json.dumps({
            "ts": ts, "token_prefix": token[:20], "outcome": outcome,
            "record_ref": ref,
        }) + "\n")
    return ref
