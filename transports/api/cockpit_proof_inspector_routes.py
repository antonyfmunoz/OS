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


class _CanonicalProofSource:
    """Read source for the inspector: canonical execution proofs by id.

    The governed execution system (poller, verifier, field control plane)
    persists proofs through ``ProofRuntime`` into the runtime state dir
    (``UMH_STATE_DIR``). The legacy organism ``ProofStore`` reads a different
    file under ``UMH_ROOT/data/runtime`` — inside a candidate container that
    file does not exist, so execution proofs were invisible to this surface
    (Wave 2 invocation #53, w16).

    Exposure is deliberately asymmetric:
      - ``get(proof_id)`` consults the canonical runtime FIRST, then the
        legacy store — callers that hold a proof_id (the field collector's
        w16 composition check, attempt detail views) resolve execution
        proofs.
      - ``query``/``summary`` remain LEGACY-ONLY. The two package classes
        have disjoint wire shapes (``status``/``created_at`` vs
        ``outcome``/``timestamp``); merging them corrupts the cockpit panel
        (Invalid Date, unfilterable rows, irreconcilable totals).
      - ``approve``/``reject`` stay on the legacy store — execution proofs
        are verifier-attested, immutable evidence, not operator-reviewed
        here.
    """

    def __init__(self, runtime: Any, legacy: Any) -> None:
        self._runtime = runtime
        self._legacy = legacy

    def get(self, proof_id: str) -> Any:
        if self._runtime is not None:
            pkg = self._runtime.get(proof_id)
            if pkg is not None:
                return pkg
        if self._legacy is not None:
            return self._legacy.get(proof_id)
        return None

    def query(self, status: str = "", limit: int = 50, offset: int = 0) -> list[Any]:
        if self._legacy is None:
            return []
        return self._legacy.query(status=status, limit=limit, offset=offset)

    def summary(self) -> dict[str, Any]:
        if self._legacy is None:
            return {"total": 0, "by_status": {}}
        return self._legacy.summary()

    def approve(self, proof_id: str, notes: str = "", reviewer: str = "operator") -> Any:
        if self._legacy is None:
            return None
        return self._legacy.approve(proof_id, notes=notes, reviewer=reviewer)

    def reject(self, proof_id: str, notes: str = "", reviewer: str = "operator") -> Any:
        if self._legacy is None:
            return None
        return self._legacy.reject(proof_id, notes=notes, reviewer=reviewer)


def _get_proof_store() -> Any:
    # A fresh ProofRuntime per call re-reads the durable JSONL, so proofs
    # written by other processes (workers, control plane) are visible without
    # a restart. The legacy store keeps its module singleton.
    runtime: Any = None
    try:
        from substrate.organism.proof_runtime import ProofRuntime
        from substrate.state.runtime_paths import runtime_state_path

        # create_parent=False: this is a READ surface and must never write.
        # ProofRuntime()'s default path resolution mkdirs the state dir; a
        # failed mkdir (read-only mount, uid mismatch) would silently degrade
        # this source to legacy-only — the exact invocation-#53 failure shape.
        store_path = runtime_state_path("organism", "proof_packages.jsonl", create_parent=False)
        runtime = ProofRuntime(store_path=str(store_path))
    except Exception as exc:
        # warning, not debug: losing the canonical source reproduces the w16
        # 404 defect and must be visible in production logs.
        logger.warning(
            "Canonical ProofRuntime unavailable for proof inspector — "
            "execution proofs will 404 (legacy store only): %s",
            exc,
        )
    legacy: Any = None
    try:
        from substrate.organism.proof_store import get_proof_store

        legacy = get_proof_store()
    except Exception as exc:
        logger.warning("Legacy proof store unavailable for proof inspector: %s", exc)
    if runtime is None and legacy is None:
        return None
    return _CanonicalProofSource(runtime, legacy)


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

    execution_id = getattr(pkg, "execution_id", "")
    journal = _get_journal()
    timeline: list[dict[str, Any]] = []
    if journal and execution_id:
        try:
            entries = journal.entries_for(execution_id)
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
        "execution_id": execution_id,
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
        "browser_evidence": getattr(pkg, "browser_evidence", []),
        "verification_results": getattr(pkg, "verification_results", []),
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
    # Runtime execution proofs carry inline evidence (in to_dict) and have no
    # on-disk evidence dir; only legacy proof packages expose one.
    evidence_dir = getattr(pkg, "evidence_dir", None)
    if evidence_dir is None or not evidence_dir.exists():
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
