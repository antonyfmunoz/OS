#!/usr/bin/env python3
"""P4S-31C isolation demonstration app — spare-port, no daemon, no DB writes.

Boots a MINIMAL FastAPI app on 127.0.0.1:8199 that mounts ONLY the two changed
read routers (intent-loop + unified-workstation) plus a deliberately-slow
SYNCHRONOUS route (``/pool-hog``) that mimics the >55 s ``/snapshot`` block
proven in the sustained-load diagnosis. This lets us load-test the read-path
change WITHOUT booting the organism daemon, persistent loops, or touching any
DB — zero live mutation.

The point being demonstrated: with the hot read surfaces now ``async`` and
isolated on a dedicated pool, a saturated shared AnyIO limiter (drained by
``/pool-hog`` copies) can no longer wedge ``/intent-loop``. Run
``p4s31c_load_probe.py`` against this app while also hammering ``/pool-hog``.

Instance-agnostic. Read-only demo scaffold; not shipped into the runtime path.
"""

from __future__ import annotations

import os
import sys
import time

sys.path.insert(
    0, os.environ.get("UMH_ROOT", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)

from fastapi import FastAPI

app = FastAPI(title="P4S-31C isolation demo")


# A SYNCHRONOUS slow route — each call holds an AnyIO limiter token for its full
# duration, exactly like the pre-fix /snapshot. Used to drain the shared pool.
@app.get("/api/umh/pool-hog")
def pool_hog() -> dict:
    time.sleep(20.0)
    return {"hog": "done"}


# Mount the two CHANGED read routers under /api/umh (their real prefix).
def _mount() -> None:
    from fastapi import APIRouter

    umh = APIRouter(prefix="/api/umh")

    # unified-workstation (async /snapshot after fix)
    from transports.api import cockpit_unified_workstation_routes as uws

    umh.include_router(uws.get_router())

    # intent-loop (async /intent-loop after fix). It needs an operator-role dep
    # and a helpers arg; supply permissive stand-ins for the demo.
    from transports.api import cockpit_intent_loop_routes as il

    def _allow() -> str:
        return "umh_operator"

    il.register_intent_loop_routes(umh, _allow, {})

    # a trivial async pulse sibling
    @umh.get("/pulse")
    async def pulse() -> dict:
        return {"status": "ok"}

    app.include_router(umh)


_mount()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8199, log_level="warning")
