"""Clerk JWT server-side validation for cockpit API.

Validates Authorization: Bearer <clerk_jwt> headers against
Clerk's JWKS endpoint (RS256). Fail-closed: rejects all requests
unless both CLERK_JWKS_URL and ALLOWED_CLERK_USER_IDS are configured.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass

import jwt
from fastapi import HTTPException, Request, WebSocket
from jwt import PyJWKClient

logger = logging.getLogger(__name__)

_JWKS_URL = os.environ.get("CLERK_JWKS_URL", "")
if not _JWKS_URL:
    logger.warning("CLERK_JWKS_URL not set — all Clerk auth will be rejected")

_CLERK_ISSUER = _JWKS_URL.replace("/.well-known/jwks.json", "") if _JWKS_URL else ""

_ALLOWED_USER_IDS: set[str] | None = None
_ALLOWLIST_OPEN = False
_raw_allowed = os.environ.get("ALLOWED_CLERK_USER_IDS", "")
if _raw_allowed.strip() == "*":
    _ALLOWLIST_OPEN = True
    logger.warning("ALLOWED_CLERK_USER_IDS=* — any valid Clerk user accepted (bootstrap mode)")
elif _raw_allowed.strip():
    _ALLOWED_USER_IDS = {uid.strip() for uid in _raw_allowed.split(",") if uid.strip()}
if not _ALLOWED_USER_IDS and not _ALLOWLIST_OPEN:
    logger.warning("ALLOWED_CLERK_USER_IDS not set — all Clerk auth will be rejected")

_DEV_BYPASS = os.environ.get("UMH_DEV_BYPASS", "").lower() in ("1", "true", "yes")
if _DEV_BYPASS:
    # DEV_BYPASS_PRESENT_IN_RUNTIME (P4S-VOICE-WS-AUTH-PREFLIGHT-001 security note).
    # This is a phase-appropriate, CREDENTIAL-FIRST, PRIVATE-IP-GATED fallback: it
    # only fires when NO Clerk credential was presented AND the caller's real IP is
    # private/trusted-proxy (Tailscale/localhost). Authenticated public traffic
    # (browser bearer.<jwt>) always hits _validate_jwt first and never reaches it.
    # It MUST be removed (or gated to a non-prod env) before public/multi-tenant use;
    # this warning exists so it can never silently become production doctrine.
    logger.warning(
        "UMH_DEV_BYPASS=true — private-IP, no-credential dev bypass is ACTIVE. "
        "Credential-first and private-IP-gated, but must be disabled before "
        "public/multi-tenant use. See .claude/rules/ security notes."
    )

_jwks_client: PyJWKClient | None = None


def _get_jwks_client() -> PyJWKClient:
    global _jwks_client
    if not _JWKS_URL:
        raise HTTPException(status_code=401, detail="Auth not configured")
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

    decode_opts: dict = {"verify_aud": False}
    decode_kwargs: dict = {"algorithms": ["RS256"]}
    if _CLERK_ISSUER:
        decode_kwargs["issuer"] = _CLERK_ISSUER
    else:
        decode_opts["verify_iss"] = False

    # Clerk JWTs have a 60s TTL; add generous leeway for proxy/network
    # transit and slow upstream responses (converse can take 30-90s)
    _LEEWAY_SECONDS = 120

    try:
        payload = jwt.decode(
            token,
            signing_key.key,
            options=decode_opts,
            leeway=_LEEWAY_SECONDS,
            **decode_kwargs,
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidIssuerError:
        logger.warning("JWT issuer mismatch")
        raise HTTPException(status_code=401, detail="Invalid token issuer")
    except jwt.InvalidTokenError as exc:
        logger.warning("JWT validation failed: %s", exc)
        raise HTTPException(status_code=401, detail="Invalid token")

    user_id = payload.get("sub", "")
    if not user_id:
        raise HTTPException(status_code=401, detail="Token missing subject")

    if _ALLOWLIST_OPEN:
        logger.info("Clerk user %s authenticated (bootstrap mode)", user_id)
    elif not _ALLOWED_USER_IDS:
        logger.warning("No allowlist configured — rejecting user %s", user_id)
        raise HTTPException(status_code=403, detail="Access denied")
    elif user_id not in _ALLOWED_USER_IDS:
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
            user = _validate_jwt(token)
            request.state.clerk_user_id = user.user_id
            return user

    if _dev_bypass_allowed(request):
        logger.debug("Dev-bypass auth from %s", _real_client_ip(request))
        request.state.clerk_user_id = "dev-bypass"
        return ClerkUser(user_id="dev-bypass")

    client_ip = _real_client_ip(request)
    has_auth = bool(auth_header)
    logger.warning(
        "Auth rejected: path=%s client=%s has_auth=%s auth_prefix=%s",
        request.url.path, client_ip, has_auth,
        auth_header[:20] if auth_header else "NONE",
    )
    raise HTTPException(status_code=401, detail="Authentication required")


def validate_ws_clerk_token(ws: WebSocket) -> ClerkUser | None:
    """Validate a WebSocket connection using Clerk JWT.

    Checks (in order):
    1. Authorization header — if present, must be valid (no fall-through)
    2. Sec-WebSocket-Protocol bearer.<jwt> subprotocol — same rule
    3. Dev-bypass from private IP (only if no credential was presented)

    Returns ClerkUser on success, None when no credential presented.
    Raises HTTPException when credential is present but invalid.
    """
    auth_header = ws.headers.get("authorization", "")
    if auth_header.lower().startswith("bearer "):
        token = auth_header[7:].strip()
        if token:
            return _validate_jwt(token)

    for proto in (ws.headers.get("sec-websocket-protocol") or "").split(","):
        proto = proto.strip()
        if proto.startswith("bearer."):
            token = proto[7:]
            return _validate_jwt(token)

    if _DEV_BYPASS:
        tcp_ip = ws.client.host if ws.client else ""
        if tcp_ip in _TRUSTED_PROXIES:
            forwarded = ws.headers.get("x-forwarded-for", "")
            if forwarded:
                tcp_ip = forwarded.split(",")[0].strip()
        if _is_private_ip(tcp_ip):
            return ClerkUser(user_id="dev-bypass")

    return None
