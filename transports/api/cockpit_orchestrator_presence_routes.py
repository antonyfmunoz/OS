"""Cockpit routes for Orchestrator Presence — Campaign 17.0."""
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
            from substrate.workstation.orchestrator_presence_runtime import (
                OrchestratorPresenceRuntime,
            )

            _runtime = OrchestratorPresenceRuntime()
        except Exception:
            logger.debug("Failed to init OrchestratorPresenceRuntime", exc_info=True)
    return _runtime


# ── Request Models ───────────────────────────────────────────────────────


class InterpretRequest(BaseModel):
    text: str


# ── Router ────────────────────────────────────────────────────────────────


def get_router():
    from fastapi import APIRouter

    router = APIRouter(prefix="/orchestrator-presence", tags=["orchestrator-presence"])

    @router.get("/snapshot")
    def presence_snapshot() -> dict[str, Any]:
        rt = _get_runtime()
        if rt is None:
            return {"error": "orchestrator presence not available"}
        return rt.snapshot().to_dict()

    @router.get("/context")
    def presence_context() -> dict[str, Any]:
        rt = _get_runtime()
        if rt is None:
            return {"error": "orchestrator presence not available"}
        return rt.context()

    @router.post("/interpret")
    def presence_interpret(body: InterpretRequest) -> dict[str, Any]:
        rt = _get_runtime()
        if rt is None:
            return {"error": "orchestrator presence not available"}

        def _do_interpret():
            rt.interpret(body.text)
            return f"presence interpreted: {body.text[:50]}", True

        resp = governed_mutation(
            mutation_name="state_mutate",
            intent=f"interpret orchestrator presence: {body.text[:50]}",
            execute_fn=_do_interpret,
            source="cockpit",
        )
        return resp.to_http_dict()

    return router
