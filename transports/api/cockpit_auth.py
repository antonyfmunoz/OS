"""Clerk JWT server-side validation for cockpit API.

Validates Authorization: Bearer <clerk_jwt> headers against
Clerk's JWKS endpoint (RS256). Only allows authenticated Clerk
users whose ID is in the ALLOWED_CLERK_USER_IDS allowlist (or
any valid Clerk user if the allowlist is not configured).
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass

import jwt
from fastapi import HTTPException, Request, WebSocket
from jwt import PyJWKClient

logger = logging.getLogger(__name__)

_JWKS_URL = os.environ.get(
    "CLERK_JWKS_URL",
    "https://obliging-donkey-31.clerk.accounts.dev/.well-known/jwks.json",
)

_ALLOWED_USER_IDS: set[str] | None = None
_raw_allowed = os.environ.get("ALLOWED_CLERK_USER_IDS", "")
if _raw_allowed.strip():
    _ALLOWED_USER_IDS = {uid.strip() for uid in _raw_allowed.split(",") if uid.strip()}

_DEV_BYPASS = os.environ.get("UMH_DEV_BYPASS", "").lower() in ("1", "true", "yes")

_jwks_client: PyJWKClient | None = None


def _get_jwks_client() -> PyJWKClient:
    global _jwks_client
    if _jwks_client is None:
        _jwks_client = PyJWKClient(_JWKS_URL, cache_keys=True, lifespan=3600)
    return _jwks_client


@dataclass
class ClerkUser:
    user_id: str
    email: str | None = None
    session_id: str | None = None


def _is_private_ip(ip: str) -> bool:
    if not ip:
        return False
    try:
        import ipaddress
        addr = ipaddress.ip_address(ip)
        tailscale_cgnat = ipaddress.ip_network("100.64.0.0/10")
        return addr.is_private or addr.is_loopback or addr in tailscale_cgnat
    except ValueError:
        return False


_TRUSTED_PROXIES = {"127.0.0.1", "::1"}
_docker_bridge = os.environ.get("UMH_DOCKER_BRIDGE_IP", "172.20.0.1")
if _docker_bridge:
    _TRUSTED_PROXIES.add(_docker_bridge)


def _real_client_ip(request: Request) -> str:
    tcp_ip = request.client.host if request.client else ""
    if tcp_ip in _TRUSTED_PROXIES:
        forwarded = request.headers.get("x-forwarded-for", "")
        if forwarded:
            return forwarded.split(",")[0].strip()
    return tcp_ip


def _dev_bypass_allowed(request: Request) -> bool:
    if not _DEV_BYPASS:
        return False
    return _is_private_ip(_real_client_ip(request))


def _validate_jwt(token: str) -> ClerkUser:
    """Validate a Clerk JWT and return the authenticated user."""
    client = _get_jwks_client()
    try:
        signing_key = client.get_signing_key_from_jwt(token)
    except (jwt.exceptions.PyJWKClientError, jwt.exceptions.DecodeError) as exc:
        logger.warning("JWKS key fetch failed: %s", exc)
        raise HTTPException(status_code=401, detail="Invalid token") from exc

    try:
        payload = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            options={"verify_aud": False},
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError as exc:
        logger.warning("JWT validation failed: %s", exc)
        raise HTTPException(status_code=401, detail="Invalid token")

    user_id = payload.get("sub", "")
    if not user_id:
        raise HTTPException(status_code=401, detail="Token missing subject")

    if _ALLOWED_USER_IDS and user_id not in _ALLOWED_USER_IDS:
        logger.warning("Clerk user %s not in allowlist", user_id)
        raise HTTPException(status_code=403, detail="Access denied")

    return ClerkUser(
        user_id=user_id,
        email=payload.get("email"),
        session_id=payload.get("sid"),
    )


async def require_clerk_auth(request: Request) -> ClerkUser:
    """FastAPI dependency — validates Clerk JWT from Authorization header.

    Falls back to dev-bypass for Tailscale/localhost when UMH_DEV_BYPASS=true.
    """
    auth_header = request.headers.get("authorization", "")

    if auth_header.lower().startswith("bearer "):
        token = auth_header[7:].strip()
        if token:
            return _validate_jwt(token)

    if _dev_bypass_allowed(request):
        logger.debug("Dev-bypass auth from %s", _real_client_ip(request))
        return ClerkUser(user_id="dev-bypass")

    raise HTTPException(status_code=401, detail="Authentication required")


def validate_ws_clerk_token(ws: WebSocket) -> ClerkUser | None:
    """Validate a WebSocket connection using Clerk JWT.

    Checks (in order):
    1. Authorization header (if present)
    2. Sec-WebSocket-Protocol bearer.<jwt> subprotocol
    3. ?token= query param (for backwards compat with WS token)
    4. Dev-bypass from private IP

    Returns ClerkUser on success, None on failure.
    """
    auth_header = ws.headers.get("authorization", "")
    if auth_header.lower().startswith("bearer "):
        token = auth_header[7:].strip()
        if token:
            try:
                return _validate_jwt(token)
            except HTTPException:
                pass

    for proto in (ws.headers.get("sec-websocket-protocol") or "").split(","):
        proto = proto.strip()
        if proto.startswith("bearer."):
            token = proto[7:]
            try:
                return _validate_jwt(token)
            except HTTPException:
                pass

    if _DEV_BYPASS:
        tcp_ip = ws.client.host if ws.client else ""
        if tcp_ip in _TRUSTED_PROXIES:
            forwarded = ws.headers.get("x-forwarded-for", "")
            if forwarded:
                tcp_ip = forwarded.split(",")[0].strip()
        if _is_private_ip(tcp_ip):
            return ClerkUser(user_id="dev-bypass")

    return None
