"""Cockpit routes for Meta IDE Context — Campaign 17.1.

Read-only context binding. Does NOT replace existing Meta IDE loop routes.
"""
from __future__ import annotations

import logging
from typing import Any

from pydantic import BaseModel

from transports.api.governed import governed_mutation

logger = logging.getLogger(__name__)


# ── Lazy Singleton ───────────────────────────────────────────────────────

_runtime: Any = None


def _get_runtime() -> Any:
    global _runtime
    if _runtime is None:
        try:
            from substrate.workstation.meta_ide_context_runtime import (
                MetaIdeContextRuntime,
            )

            _runtime = MetaIdeContextRuntime()
        except Exception:
            logger.debug("Failed to init MetaIdeContextRuntime", exc_info=True)
    return _runtime


# ── Request Models ───────────────────────────────────────────────────────


class ResolveIntentRequest(BaseModel):
    text: str


# ── Router ────────────────────────────────────────────────────────────────


def get_router():
    from fastapi import APIRouter

    router = APIRouter(prefix="/meta-ide-context", tags=["meta-ide-context"])

    @router.get("/context")
    def meta_ide_context() -> dict[str, Any]:
        rt = _get_runtime()
        if rt is None:
            return {"error": "meta ide context not available"}
        return rt.context().to_dict()

    @router.get("/active-files")
    def meta_ide_active_files() -> dict[str, Any]:
        rt = _get_runtime()
        if rt is None:
            return {"active_files": []}
        return {"active_files": rt.active_files()}

    @router.post("/resolve-intent")
    def meta_ide_resolve_intent(body: ResolveIntentRequest) -> dict[str, Any]:
        rt = _get_runtime()
        if rt is None:
            return {"error": "meta ide context not available"}

        def _do_resolve():
            rt.resolve_intent(body.text)
            return f"intent resolved: {body.text[:50]}", True

        resp = governed_mutation(
            mutation_name="state_mutate",
            intent=f"resolve meta IDE intent: {body.text[:50]}",
            execute_fn=_do_resolve,
            source="cockpit",
        )
        return resp.to_http_dict()

    return router
