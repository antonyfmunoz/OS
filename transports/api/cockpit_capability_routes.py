"""Cockpit Capability Routes — API surface for emergent capability tracking.

Exposes CapabilityRuntime operations: register, list, get, lineage,
evidence, summary, discovery.

Answers operator question #10: "What capability emerged?"

Gate 5 — Capability Runtime. UMH transport layer. Instance-agnostic.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, Request

logger = logging.getLogger(__name__)

capability_router: APIRouter = APIRouter()
_configured = False


def configure(*, require_operator_dep: Any) -> None:
    global _configured
    if _configured:
        return
    _configured = True
    _router = _build_router(require_operator_dep)
    capability_router.include_router(_router)


def _get_runtime() -> Any:
    if not hasattr(_get_runtime, "_instance"):
        from substrate.organism.capability_runtime import CapabilityRuntime

        _get_runtime._instance = CapabilityRuntime()
    return _get_runtime._instance


def _build_router(require_operator_dep: Any) -> APIRouter:
    r = APIRouter()
    auth = [Depends(require_operator_dep)]

    @r.get("/capabilities", dependencies=auth)
    def list_capabilities(
        maturity: str | None = None,
        tag: str | None = None,
    ) -> dict[str, Any]:
        from substrate.organism.capability_runtime import CapabilityMaturity

        rt = _get_runtime()
        mat = None
        if maturity:
            try:
                mat = CapabilityMaturity(maturity)
            except ValueError:
                return {"error": f"invalid maturity: {maturity}"}
        caps = rt.list_capabilities(maturity=mat, tag=tag)
        return {"capabilities": [c.to_dict() for c in caps], "count": len(caps)}

    @r.get("/capabilities/summary", dependencies=auth)
    def capability_summary() -> dict[str, Any]:
        return _get_runtime().summary()

    @r.get("/capabilities/from-intent/{intent_id}", dependencies=auth)
    def capabilities_from_intent(intent_id: str) -> dict[str, Any]:
        rt = _get_runtime()
        caps = rt.capabilities_from_intent(intent_id)
        return {"capabilities": [c.to_dict() for c in caps], "count": len(caps)}

    @r.get("/capabilities/{capability_id}", dependencies=auth)
    def get_capability(capability_id: str) -> dict[str, Any]:
        rt = _get_runtime()
        cap = rt.get(capability_id)
        if cap is None:
            return {"error": f"capability {capability_id} not found"}
        return {
            "capability": cap.to_dict(),
            "lineage": rt.lineage(capability_id),
            "evidence": [e.to_dict() for e in rt.evidence_for(capability_id)],
            "maturity_score": rt.maturity_score(capability_id),
        }

    @r.post("/capabilities/register", dependencies=auth)
    async def register_capability(request: Request) -> dict[str, Any]:
        body = await request.json()
        name = body.get("name", "")
        description = body.get("description", "")
        if not name:
            return {"error": "name is required"}
        cap = rt = _get_runtime()
        cap = rt.register(
            name=name,
            description=description,
            origin_intent_id=body.get("origin_intent_id", ""),
            understanding_sources=body.get("understanding_sources"),
            owner=body.get("owner", ""),
            tags=body.get("tags"),
        )
        return {"capability": cap.to_dict()}

    @r.post("/capabilities/{capability_id}/evidence", dependencies=auth)
    async def add_evidence(capability_id: str, request: Request) -> dict[str, Any]:
        from substrate.organism.capability_runtime import CapabilityEvidenceType

        body = await request.json()
        et_str = body.get("evidence_type", "manual_attestation")
        try:
            et = CapabilityEvidenceType(et_str)
        except ValueError:
            return {"error": f"invalid evidence_type: {et_str}"}
        rt = _get_runtime()
        ev = rt.add_evidence(
            capability_id=capability_id,
            evidence_type=et,
            source_id=body.get("source_id", ""),
            description=body.get("description", ""),
            quality_score=float(body.get("quality_score", 0.5)),
        )
        if ev is None:
            return {"error": f"capability {capability_id} not found"}
        return {"evidence": ev.to_dict()}

    @r.post("/capabilities/propose", dependencies=auth)
    async def propose_capabilities(request: Request) -> dict[str, Any]:
        body = await request.json()
        outcomes = body.get("outcomes", [])
        rt = _get_runtime()
        proposals = rt.propose_from_patterns(
            outcomes,
            min_occurrences=int(body.get("min_occurrences", 3)),
            min_success_rate=float(body.get("min_success_rate", 0.6)),
        )
        return {"proposals": proposals, "count": len(proposals)}

    return r
