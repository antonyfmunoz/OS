"""Cockpit Proof Inspector routes — G10 MVP gate.

Surfaces proof packages, evidence, timeline, and artifacts for operator
inspection. All read-only except approve/reject which route through
governed mutation.

UMH transport layer. Instance-agnostic.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request

from transports.api.governed import governed_mutation

logger = logging.getLogger(__name__)

proof_inspector_router: APIRouter = APIRouter()

_configured: bool = False


def configure(require_operator_dep: Any) -> None:
    global _configured, proof_inspector_router
    _configured = True
    proof_inspector_router = _build_router(require_operator_dep)


def _get_proof_store() -> Any:
    try:
        from substrate.organism.proof_store import get_proof_store

        return get_proof_store()
    except Exception:
        return None


def _get_obs_proof_store() -> Any:
    return _get_proof_store()


def _get_journal() -> Any:
    try:
        from substrate.organism.execution_journal import ExecutionJournal
        from substrate.state.runtime_paths import runtime_state_path

        j_path = runtime_state_path("organism", "execution_journal.jsonl", create_parent=False)
        journal = ExecutionJournal(persist_path=str(j_path))
        journal.recover()
        return journal
    except Exception:
        return None


def _build_router(require_operator_dep: Any) -> APIRouter:
    r = APIRouter()
    auth = [Depends(require_operator_dep)]

    r.add_api_route("/proof-inspector/summary", _summary, methods=["GET"])
    r.add_api_route("/proof-inspector/packages", _packages, methods=["GET"])
    r.add_api_route("/proof-inspector/packages/{proof_id}", _package_detail, methods=["GET"])
    r.add_api_route(
        "/proof-inspector/packages/{proof_id}/timeline", _package_timeline, methods=["GET"]
    )
    r.add_api_route(
        "/proof-inspector/packages/{proof_id}/evidence", _package_evidence, methods=["GET"]
    )
    r.add_api_route("/proof-inspector/packages/{proof_id}/raw", _package_raw, methods=["GET"])
    r.add_api_route("/proof-inspector/artifacts", _artifacts, methods=["GET"])
    r.add_api_route(
        "/proof-inspector/packages/{proof_id}/approve",
        _approve,
        methods=["POST"],
        dependencies=auth,
    )
    r.add_api_route(
        "/proof-inspector/packages/{proof_id}/reject", _reject, methods=["POST"], dependencies=auth
    )

    return r


async def _summary(request: Request) -> dict[str, Any]:
    store = _get_proof_store()
    if store is None:
        return {"total": 0, "by_status": {}, "store_available": False}
    s = store.summary()
    s["store_available"] = True
    return s


async def _packages(request: Request) -> dict[str, Any]:
    store = _get_proof_store()
    if store is None:
        return {"packages": [], "total": 0, "store_available": False}

    status = request.query_params.get("status", "")
    limit = int(request.query_params.get("limit", "50"))
    offset = int(request.query_params.get("offset", "0"))

    pkgs = store.query(status=status, limit=limit, offset=offset)
    return {
        "packages": [p.to_dict() for p in pkgs],
        "total": len(pkgs),
        "store_available": True,
    }


async def _package_detail(request: Request) -> dict[str, Any]:
    proof_id = request.path_params["proof_id"]
    store = _get_proof_store()
    if store is None:
        raise HTTPException(status_code=503, detail="Proof store unavailable")

    pkg = store.get(proof_id)
    if pkg is None:
        raise HTTPException(status_code=404, detail=f"Proof {proof_id} not found")

    result = pkg.to_dict()
    result["evidence_files"] = _list_evidence_files(pkg)
    return result


async def _package_timeline(request: Request) -> dict[str, Any]:
    proof_id = request.path_params["proof_id"]
    store = _get_proof_store()
    if store is None:
        raise HTTPException(status_code=503, detail="Proof store unavailable")

    pkg = store.get(proof_id)
    if pkg is None:
        raise HTTPException(status_code=404, detail=f"Proof {proof_id} not found")

    journal = _get_journal()
    timeline: list[dict[str, Any]] = []
    if journal and pkg.execution_id:
        try:
            entries = journal.entries_for(pkg.execution_id)
            timeline = [
                {
                    "phase": getattr(e, "phase", "unknown"),
                    "source": getattr(e, "source", ""),
                    "details": getattr(e, "details", ""),
                    "timestamp": getattr(e, "timestamp", 0),
                }
                for e in entries
            ]
        except Exception as exc:
            logger.debug("Journal lookup failed for %s: %s", pkg.execution_id, exc)

    return {
        "proof_id": proof_id,
        "execution_id": pkg.execution_id,
        "timeline": timeline,
    }


async def _package_evidence(request: Request) -> dict[str, Any]:
    proof_id = request.path_params["proof_id"]
    store = _get_proof_store()
    if store is None:
        raise HTTPException(status_code=503, detail="Proof store unavailable")

    pkg = store.get(proof_id)
    if pkg is None:
        raise HTTPException(status_code=404, detail=f"Proof {proof_id} not found")

    return {
        "proof_id": proof_id,
        "evidence_files": _list_evidence_files(pkg),
        "browser_evidence": pkg.browser_evidence,
        "verification_results": pkg.verification_results,
    }


async def _package_raw(request: Request) -> dict[str, Any]:
    proof_id = request.path_params["proof_id"]
    store = _get_proof_store()
    if store is None:
        raise HTTPException(status_code=503, detail="Proof store unavailable")

    pkg = store.get(proof_id)
    if pkg is None:
        raise HTTPException(status_code=404, detail=f"Proof {proof_id} not found")

    return pkg.to_dict()


async def _artifacts(request: Request) -> dict[str, Any]:
    obs = _get_obs_proof_store()
    if obs is None:
        return {"artifacts": [], "store_available": False}

    limit = int(request.query_params.get("limit", "50"))
    try:
        recent = obs.query(limit=limit)
        return {
            "artifacts": [a.to_dict() if hasattr(a, "to_dict") else vars(a) for a in recent],
            "store_available": True,
        }
    except Exception as exc:
        logger.debug("Observability proof store query failed: %s", exc)
        return {"artifacts": [], "store_available": False, "error": str(exc)}


async def _approve(request: Request) -> dict[str, Any]:
    proof_id = request.path_params["proof_id"]
    body = await request.json()
    notes = body.get("notes", "")

    def _do_approve() -> tuple[str, bool]:
        store = _get_proof_store()
        if store is None:
            return "Proof store unavailable", False
        pkg = store.approve(proof_id, notes=notes, reviewer="operator")
        if pkg is None:
            return f"Proof {proof_id} not found", False
        return f"Proof {proof_id} approved", True

    result = governed_mutation(
        mutation_name="proof_review",
        intent=f"Approve proof {proof_id}",
        execute_fn=_do_approve,
        source="cockpit",
        metadata={"proof_id": proof_id, "action": "approve"},
    )
    if not result.success:
        raise HTTPException(status_code=422, detail=result.to_http_dict())
    return result.to_http_dict()


async def _reject(request: Request) -> dict[str, Any]:
    proof_id = request.path_params["proof_id"]
    body = await request.json()
    notes = body.get("notes", "")

    def _do_reject() -> tuple[str, bool]:
        store = _get_proof_store()
        if store is None:
            return "Proof store unavailable", False
        pkg = store.reject(proof_id, notes=notes, reviewer="operator")
        if pkg is None:
            return f"Proof {proof_id} not found", False
        return f"Proof {proof_id} rejected", True

    result = governed_mutation(
        mutation_name="proof_review",
        intent=f"Reject proof {proof_id}",
        execute_fn=_do_reject,
        source="cockpit",
        metadata={"proof_id": proof_id, "action": "reject"},
    )
    if not result.success:
        raise HTTPException(status_code=422, detail=result.to_http_dict())
    return result.to_http_dict()


def _list_evidence_files(pkg: Any) -> list[dict[str, Any]]:
    evidence_dir = pkg.evidence_dir
    if not evidence_dir.exists():
        return []
    files: list[dict[str, Any]] = []
    try:
        for f in sorted(evidence_dir.iterdir()):
            if f.is_file():
                files.append(
                    {
                        "name": f.name,
                        "size": f.stat().st_size,
                        "modified": f.stat().st_mtime,
                        "type": _guess_type(f.name),
                    }
                )
    except Exception as exc:
        logger.debug("Failed to list evidence dir: %s", exc)
    return files


def _guess_type(name: str) -> str:
    lower = name.lower()
    if lower.endswith((".png", ".jpg", ".jpeg", ".gif", ".webp")):
        return "image"
    if lower.endswith(".json"):
        return "json"
    if lower.endswith((".md", ".txt", ".log")):
        return "text"
    if lower.endswith(".html"):
        return "html"
    return "binary"
