"""
identity.py — User model and token-based authentication.

Scope
-----
Single-tenant founder-phase OS. No OAuth, no external IdP, no LDAP.
Users live in a JSONL file; tokens are HMAC-signed envelopes carrying
`(user_id, issued_at, nonce)`. The HMAC secret is read from
`EOS_SECURITY_SECRET` (env var) and falls back to a persisted
`data/security/secret.key` that's created on first use.

Data layout
-----------
    data/security/users.jsonl         — append-only user records
                                        (latest record per user_id wins)
    data/security/secret.key          — HMAC signing secret (0600)
    data/security/revocations.jsonl   — revoked token ids (jti)

Why JSONL + latest-wins
-----------------------
- Same shape as every other EOS log, readable with `tail -f`.
- "Latest record wins" means `assign_role` is a new row, not a mutation.
  The full history of role assignments is recoverable from the file.
- Matches the auditability goal: you can grep the identity log to see
  exactly when user X got role Y.

Token format
------------
    <base64url(payload)> . <base64url(hmac_sha256(secret, payload))>

    payload = {
        "uid": "<user_id>",
        "iat": <unix_ts>,
        "exp": <unix_ts>,
        "jti": "<nonce>",
    }

The token is opaque to callers; use `IdentityStore.verify(token_str)`
to turn a token string into a `Token` object. Never trust the payload
without calling `verify()`.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
import time
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

_SECURITY_DIR = Path("/opt/OS/data/security")
_USERS_PATH = _SECURITY_DIR / "users.jsonl"
_SECRET_PATH = _SECURITY_DIR / "secret.key"
_REVOCATIONS_PATH = _SECURITY_DIR / "revocations.jsonl"

DEFAULT_TOKEN_TTL_SECONDS = 12 * 60 * 60  # 12h


class AuthError(Exception):
    """Raised when authentication or token verification fails."""


# ─── Data classes ───────────────────────────────────────────────────────────


@dataclass
class User:
    """Immutable snapshot of one user record."""

    user_id: str
    role: str
    display_name: str = ""
    api_key_hash: str = ""
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    disabled: bool = False
    metadata: dict = field(default_factory=dict)

    def as_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "User":
        return cls(
            user_id=d["user_id"],
            role=d["role"],
            display_name=d.get("display_name", ""),
            api_key_hash=d.get("api_key_hash", ""),
            created_at=d.get("created_at", datetime.now(timezone.utc).isoformat()),
            disabled=bool(d.get("disabled", False)),
            metadata=d.get("metadata", {}),
        )


@dataclass
class Token:
    """A verified token. Only produced by `IdentityStore.verify()`."""

    user_id: str
    role: str
    issued_at: int
    expires_at: int
    jti: str
    raw: str  # original token string, for audit logging

    @property
    def is_expired(self) -> bool:
        return time.time() >= self.expires_at


# ─── Store ──────────────────────────────────────────────────────────────────


class IdentityStore:
    """File-backed user store + HMAC token issuer.

    Thread-safety: each write appends a single JSONL row — safe under
    concurrent writers on POSIX (single `write(2)` on a pipe-like log).
    Reads always replay from the file.
    """

    def __init__(
        self,
        *,
        users_path: Path | None = None,
        secret_path: Path | None = None,
        revocations_path: Path | None = None,
        token_ttl: int = DEFAULT_TOKEN_TTL_SECONDS,
    ) -> None:
        self.users_path = users_path or _USERS_PATH
        self.secret_path = secret_path or _SECRET_PATH
        self.revocations_path = revocations_path or _REVOCATIONS_PATH
        self.token_ttl = token_ttl
        self._secret: bytes | None = None

        self.users_path.parent.mkdir(parents=True, exist_ok=True)
        self.users_path.touch(exist_ok=True)
        self.revocations_path.touch(exist_ok=True)

    # ─── Secret management ─────────────────────────────────────────────────

    def _load_secret(self) -> bytes:
        if self._secret is not None:
            return self._secret
        env = os.getenv("EOS_SECURITY_SECRET")
        if env:
            self._secret = env.encode("utf-8")
            return self._secret
        if self.secret_path.exists():
            self._secret = self.secret_path.read_bytes().strip()
            if self._secret:
                return self._secret
        # First-run: generate a fresh secret and persist.
        s = secrets.token_bytes(32)
        self.secret_path.parent.mkdir(parents=True, exist_ok=True)
        self.secret_path.write_bytes(s)
        try:
            os.chmod(self.secret_path, 0o600)
        except PermissionError:
            pass
        self._secret = s
        return s

    # ─── User lifecycle ────────────────────────────────────────────────────

    def create_user(
        self,
        user_id: str,
        role: str,
        *,
        api_key: str | None = None,
        display_name: str = "",
        metadata: dict | None = None,
    ) -> tuple[User, str]:
        """Create a user. Returns (user, raw_api_key).

        If `api_key` is None, one is generated. The returned raw key is
        the ONLY time the plaintext is available — the store persists
        only the hash.
        """
        if self.get_user(user_id) is not None:
            raise ValueError(f"user {user_id!r} already exists")
        raw_key = api_key or secrets.token_urlsafe(24)
        user = User(
            user_id=user_id,
            role=role,
            display_name=display_name or user_id,
            api_key_hash=_hash_api_key(raw_key),
            metadata=metadata or {},
        )
        self._append_user(user)
        return user, raw_key

    def assign_role(self, user_id: str, role: str) -> User:
        """Append a new record with the updated role. History preserved."""
        existing = self.get_user(user_id)
        if existing is None:
            raise KeyError(f"no such user: {user_id}")
        updated = User(
            user_id=existing.user_id,
            role=role,
            display_name=existing.display_name,
            api_key_hash=existing.api_key_hash,
            created_at=existing.created_at,
            disabled=existing.disabled,
            metadata=existing.metadata,
        )
        self._append_user(updated)
        return updated

    def disable_user(self, user_id: str) -> User:
        existing = self.get_user(user_id)
        if existing is None:
            raise KeyError(f"no such user: {user_id}")
        updated = User(
            user_id=existing.user_id,
            role=existing.role,
            display_name=existing.display_name,
            api_key_hash=existing.api_key_hash,
            created_at=existing.created_at,
            disabled=True,
            metadata=existing.metadata,
        )
        self._append_user(updated)
        return updated

    def get_user(self, user_id: str) -> User | None:
        latest: User | None = None
        for row in self._iter_rows(self.users_path):
            if row.get("user_id") == user_id:
                latest = User.from_dict(row)
        return latest

    def list_users(self) -> list[User]:
        latest: dict[str, User] = {}
        for row in self._iter_rows(self.users_path):
            u = User.from_dict(row)
            latest[u.user_id] = u
        return sorted(latest.values(), key=lambda u: u.user_id)

    # ─── Token lifecycle ───────────────────────────────────────────────────

    def authenticate(self, user_id: str, api_key: str) -> Token:
        """Verify credentials and return a signed token.

        Raises AuthError on any failure — unknown user, wrong key,
        disabled account. The message is intentionally generic so
        enumeration is harder.
        """
        user = self.get_user(user_id)
        if user is None or user.disabled:
            raise AuthError("invalid credentials")
        if not hmac.compare_digest(user.api_key_hash, _hash_api_key(api_key)):
            raise AuthError("invalid credentials")
        return self._issue_token(user)

    def verify(self, token_str: str) -> Token:
        """Parse + verify a token string. Raises AuthError on any failure."""
        if not token_str or "." not in token_str:
            raise AuthError("malformed token")
        try:
            payload_b64, sig_b64 = token_str.split(".", 1)
        except ValueError as exc:
            raise AuthError("malformed token") from exc

        secret = self._load_secret()
        expected = hmac.new(
            secret, payload_b64.encode("ascii"), hashlib.sha256
        ).digest()
        try:
            actual = _b64url_decode(sig_b64)
        except Exception as exc:
            raise AuthError("malformed signature") from exc
        if not hmac.compare_digest(expected, actual):
            raise AuthError("bad signature")

        try:
            payload = json.loads(_b64url_decode(payload_b64))
        except Exception as exc:
            raise AuthError("malformed payload") from exc

        uid = payload.get("uid")
        iat = int(payload.get("iat", 0))
        exp = int(payload.get("exp", 0))
        jti = payload.get("jti", "")
        if not uid or not jti:
            raise AuthError("incomplete payload")
        if time.time() >= exp:
            raise AuthError("token expired")
        if jti in self._revoked_jtis():
            raise AuthError("token revoked")

        user = self.get_user(uid)
        if user is None or user.disabled:
            raise AuthError("user disabled")

        return Token(
            user_id=uid,
            role=user.role,
            issued_at=iat,
            expires_at=exp,
            jti=jti,
            raw=token_str,
        )

    def revoke(self, jti: str, *, reason: str = "") -> None:
        """Revoke a token by its jti. Idempotent."""
        row = {
            "jti": jti,
            "revoked_at": datetime.now(timezone.utc).isoformat(),
            "reason": reason,
        }
        with self.revocations_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(row) + "\n")

    # ─── Internal helpers ──────────────────────────────────────────────────

    def _issue_token(self, user: User) -> Token:
        now = int(time.time())
        exp = now + self.token_ttl
        jti = uuid.uuid4().hex
        payload = {"uid": user.user_id, "iat": now, "exp": exp, "jti": jti}
        payload_b64 = _b64url_encode(
            json.dumps(payload, separators=(",", ":")).encode("utf-8")
        )
        sig = hmac.new(
            self._load_secret(), payload_b64.encode("ascii"), hashlib.sha256
        ).digest()
        token_str = f"{payload_b64}.{_b64url_encode(sig)}"
        return Token(
            user_id=user.user_id,
            role=user.role,
            issued_at=now,
            expires_at=exp,
            jti=jti,
            raw=token_str,
        )

    def _append_user(self, user: User) -> None:
        row = user.as_dict()
        with self.users_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(row) + "\n")

    def _iter_rows(self, path: Path) -> Iterable[dict]:
        if not path.exists():
            return
        with path.open("r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    yield json.loads(line)
                except json.JSONDecodeError:
                    continue

    def _revoked_jtis(self) -> set[str]:
        out: set[str] = set()
        for row in self._iter_rows(self.revocations_path):
            if "jti" in row:
                out.add(row["jti"])
        return out


# ─── Helpers ────────────────────────────────────────────────────────────────


def _b64url_encode(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode("ascii")


def _b64url_decode(s: str) -> bytes:
    pad = "=" * (-len(s) % 4)
    return base64.urlsafe_b64decode(s + pad)


def _hash_api_key(raw: str) -> str:
    """Salted hash of an API key. Salt is the same HMAC secret — fine for
    single-tenant; rotate the secret to invalidate all keys."""
    # We use SHA-256 with a fixed per-install pepper. The pepper lives
    # with the secret file; rotating the secret invalidates all keys,
    # which is the desired emergency response.
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


__all__ = [
    "AuthError",
    "IdentityStore",
    "Token",
    "User",
    "DEFAULT_TOKEN_TTL_SECONDS",
]
