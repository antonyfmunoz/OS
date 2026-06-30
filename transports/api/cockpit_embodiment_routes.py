"""Cockpit Embodiment routes — natural language intent surface.

Mounted under /api/umh/ via include_router in cockpit.py.
Operator intent → classification → routing → persona-shaped response.

W4. UMH transport layer. Instance-agnostic.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from transports.api.governed import governed_mutation

logger = logging.getLogger(__name__)

embodiment_router: APIRouter = APIRouter()

_configured: bool = False
_embodiment_instance: Any = None


def configure(*, require_operator_dep: Any) -> None:
    global _configured, embodiment_router
    if _configured:
        return
    _configured = True
    embodiment_router = _build_router(require_operator_dep)


def _get_embodiment() -> Any:
    global _embodiment_instance
    if _embodiment_instance is not None:
        return _embodiment_instance
    try:
        from substrate.organism.embodiment_runtime import EmbodimentRuntime

        _embodiment_instance = EmbodimentRuntime()
        return _embodiment_instance
    except Exception as exc:
        logger.debug("embodiment routes: failed to create runtime: %s", exc)
        return None


def _build_router(require_operator_dep: Any) -> APIRouter:
    r = APIRouter(dependencies=[Depends(require_operator_dep)])

    @r.post("/embodiment/intent")
    def process_intent(payload: dict) -> dict:
        emb = _get_embodiment()
        if emb is None:
            raise HTTPException(status_code=503, detail="embodiment unavailable")
        text = str(payload.get("text", ""))
        if not text:
            raise HTTPException(status_code=400, detail="text required")
        captured: dict = {}

        def _do_intent():
            response = emb.process_intent(text, context=payload.get("context"))
            captured.update(response.to_dict())
            return f"embodiment intent: {text[:80]}", True

        resp = governed_mutation(
            mutation_name="state_mutate",
            intent=f"embodiment intent: {text[:80]}",
            execute_fn=_do_intent,
            source="cockpit",
            metadata={"text": text[:200]},
        )
        if not resp.success:
            return resp.to_http_dict()
        return captured

    @r.post("/embodiment/classify")
    def classify_intent(payload: dict) -> dict:
        emb = _get_embodiment()
        if emb is None:
            raise HTTPException(status_code=503, detail="embodiment unavailable")
        text = str(payload.get("text", ""))
        if not text:
            raise HTTPException(status_code=400, detail="text required")
        captured: dict = {}

        def _do_classify():
            classification = emb.classify_intent(text)
            captured.update(classification.to_dict())
            return f"embodiment classify: {text[:80]}", True

        resp = governed_mutation(
            mutation_name="state_mutate",
            intent=f"embodiment classify: {text[:80]}",
            execute_fn=_do_classify,
            source="cockpit",
            metadata={"text": text[:200]},
        )
        if not resp.success:
            return resp.to_http_dict()
        return captured

    @r.get("/embodiment/context")
    def embodiment_context() -> dict:
        emb = _get_embodiment()
        if emb is None:
            return {"error": "embodiment unavailable"}
        return emb.current_context().to_dict()

    @r.get("/embodiment/persona")
    def embodiment_persona() -> dict:
        emb = _get_embodiment()
        if emb is None:
            return {"name": "UMH", "style": "tactical"}
        return emb.persona_info()

    @r.patch("/embodiment/persona")
    def update_persona(payload: dict) -> dict:
        emb = _get_embodiment()
        if emb is None:
            raise HTTPException(status_code=503, detail="embodiment unavailable")
        captured: dict = {}

        def _do_update():
            result = emb.update_persona(**payload)
            captured.update(result)
            return "updated embodiment persona", True

        resp = governed_mutation(
            mutation_name="settings_update",
            intent="update embodiment persona",
            execute_fn=_do_update,
            source="cockpit",
            metadata=payload,
        )
        if not resp.success:
            return resp.to_http_dict()
        return captured

    @r.get("/embodiment/history")
    def intent_history(limit: int = 50) -> dict:
        emb = _get_embodiment()
        if emb is None:
            return {"history": []}
        return {"history": [h.to_dict() for h in emb.intent_history(limit)]}

    @r.get("/embodiment/accuracy")
    def routing_accuracy() -> dict:
        emb = _get_embodiment()
        if emb is None:
            return {"total_processed": 0}
        return emb.routing_accuracy().to_dict()

    return r
