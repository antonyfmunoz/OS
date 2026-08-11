#!/usr/bin/env python3
"""CutStudio API — transcript-based video editing over the Phase 1 cut pipeline.

Host process on :8931 (bind 127.0.0.1 only — reached through the Caddy /
tailscale-serve edge like every other surface, never a direct Tailscale bind).

It is a SEPARATE service from operator_api on purpose (D8b): whisper `small`
plus render jobs would otherwise contend in-process with the voice engine and
the cockpit API, and the voice unit is memory-capped at 1G.

Auth is dual (D2): a Clerk bearer (how the cockpit calls it) OR an X-API-Key
(how CLI tools, agents, and the rehearsal harness call it). Both fail closed.
"""

import faulthandler
import hmac
import logging
import os
import sys

faulthandler.enable()

sys.path.insert(0, os.environ.get("UMH_ROOT", "/opt/OS"))

from contextlib import asynccontextmanager  # noqa: E402
from pathlib import Path  # noqa: E402

import uvicorn  # noqa: E402
from dotenv import load_dotenv  # noqa: E402
from fastapi import Depends, FastAPI, HTTPException, Request  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402
from fastapi.staticfiles import StaticFiles  # noqa: E402

load_dotenv("/opt/OS/services/.env")
load_dotenv("/opt/OS/.env", override=False)

UMH_ROOT = Path(os.getenv("UMH_ROOT", "/opt/OS"))
API_KEY = os.getenv("CUTSTUDIO_API_KEY", "")

logger = logging.getLogger("cutstudio_api")
logging.basicConfig(level=logging.INFO)

from knowledge.skills.marketing.content.cut.server import store  # noqa: E402
from knowledge.skills.marketing.content.cut.server.registry import get_registry  # noqa: E402
from knowledge.skills.marketing.content.cut.server.routes import (  # noqa: E402
    public_router,
    router,
)
from substrate.integrations.cors import cors_origins  # noqa: E402


def _clerk_user(request: Request):
    """Try Clerk. Returns a user or None.

    `require_clerk_auth` raises 401 whenever Clerk env is absent — correct
    for the cockpit, wrong here, because the API-key path must still work on
    a host with no Clerk configuration. So a Clerk rejection is swallowed and
    treated as "no Clerk credential", never as a grant.
    """
    try:
        from transports.api.cockpit_auth import _validate_jwt
    except ImportError as exc:
        logger.debug("clerk auth unavailable: %s", exc)
        return None

    auth_header = request.headers.get("authorization", "")
    if not auth_header.lower().startswith("bearer "):
        return None
    token = auth_header[7:].strip()
    if not token:
        return None
    try:
        return _validate_jwt(token)
    except HTTPException as exc:
        logger.warning("clerk bearer rejected: %s", exc.detail)
        return None
    except Exception as exc:
        logger.warning("clerk validation error: %s", exc)
        return None


async def require_cutstudio_auth(request: Request) -> str:
    """Clerk bearer first, then X-API-Key. 401 when neither authenticates."""
    user = _clerk_user(request)
    if user is not None:
        request.state.cutstudio_principal = "clerk:%s" % user.user_id
        return request.state.cutstudio_principal

    key = request.headers.get("x-api-key", "")
    if key and API_KEY and hmac.compare_digest(key, API_KEY):
        request.state.cutstudio_principal = "apikey"
        return "apikey"

    if key and not API_KEY:
        # Fail CLOSED: an unset key must never authenticate everyone.
        raise HTTPException(
            status_code=503, detail="API key not configured — set CUTSTUDIO_API_KEY"
        )
    raise HTTPException(status_code=401, detail="Authentication required")


@asynccontextmanager
async def lifespan(application):
    get_registry().start()
    logger.info("CutStudio API ready — projects at %s", store.root())
    yield
    logger.info("CutStudio API shutting down")


app = FastAPI(title="CutStudio", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-EDL-Rev", "Content-Range", "Accept-Ranges"],
)


@app.get("/health")
async def health() -> dict:
    """Unauthenticated liveness + the disk gate the VPS disk-full incident earned."""
    free = store.free_gb()
    return {
        "ok": True,
        "jobs_running": get_registry().running_count(),
        "disk_free_gb": round(free, 2),
        "uploads_accepted": free >= store.MIN_FREE_GB,
    }


app.include_router(router, dependencies=[Depends(require_cutstudio_auth)])
app.include_router(public_router)  # /media — the link token is the credential

# SPA mount LAST so it never shadows an API route.
_dist = UMH_ROOT / "cockpit" / "dist-web"
if _dist.exists():
    app.mount("/", StaticFiles(directory=str(_dist), html=True), name="cutstudio")


if __name__ == "__main__":
    uvicorn.run(
        app,
        host=os.getenv("CUTSTUDIO_HOST", "127.0.0.1"),
        port=int(os.getenv("CUTSTUDIO_PORT", "8931")),
        log_level="info",
    )
