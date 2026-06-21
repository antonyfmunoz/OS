"""Cockpit validation routes — capability compounding proof surface.

Mounted under /api/umh/ via include_router in cockpit.py.

Campaign 23A. UMH transport layer. Instance-agnostic.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends

logger = logging.getLogger(__name__)

validation_router: APIRouter = APIRouter()

_configured: bool = False


def configure(require_operator_dep: Any) -> None:
    global _configured, validation_router
    _configured = True
    validation_router = _build_router(require_operator_dep)


def register_validation_routes(app: Any, require_operator_dep: Any | None = None) -> None:
    if require_operator_dep is not None:
        configure(require_operator_dep)
    app.include_router(validation_router, prefix="/api/umh")


_validation_runtime: Any = None


def _get_runtime() -> Any:
    global _validation_runtime
    if _validation_runtime is None:
        try:
            from substrate.organism.capability_validation_runtime import (
                CapabilityValidationRuntime,
            )
            _validation_runtime = CapabilityValidationRuntime()
        except Exception:
            logger.debug("CapabilityValidationRuntime unavailable")
            return None
    return _validation_runtime


def _build_router(require_operator_dep: Any) -> APIRouter:
    router = APIRouter(tags=["validation"])

    @router.get("/validation/runs")
    async def list_runs(
        benchmark_type: str | None = None,
        track: str | None = None,
        _operator: Any = Depends(require_operator_dep),
    ) -> dict[str, Any]:
        rt = _get_runtime()
        if rt is None:
            return {"runs": [], "error": "runtime unavailable"}
        if benchmark_type:
            runs = rt.runs_by_type(benchmark_type, track=track)
        else:
            runs = rt.all_runs()
        return {"runs": [r.to_dict() for r in runs]}

    @router.get("/validation/runs/{run_id}")
    async def get_run(
        run_id: str,
        _operator: Any = Depends(require_operator_dep),
    ) -> dict[str, Any]:
        rt = _get_runtime()
        if rt is None:
            return {"run": None, "error": "runtime unavailable"}
        run = rt.run_by_id(run_id)
        if run is None:
            return {"run": None, "error": "not found"}
        return {"run": run.to_dict()}

    @router.get("/validation/report")
    async def get_report(
        _operator: Any = Depends(require_operator_dep),
    ) -> dict[str, Any]:
        rt = _get_runtime()
        if rt is None:
            return {"report": None, "error": "runtime unavailable"}
        report = rt.generate_report()
        return {"report": report.to_dict()}

    @router.get("/validation/compounding-curve")
    async def get_compounding_curve(
        _operator: Any = Depends(require_operator_dep),
    ) -> dict[str, Any]:
        rt = _get_runtime()
        if rt is None:
            return {"curve": None, "error": "runtime unavailable"}
        curve = rt.compounding_curve()
        return {"curve": curve}

    @router.get("/validation/control-comparison")
    async def get_control_comparison(
        _operator: Any = Depends(require_operator_dep),
    ) -> dict[str, Any]:
        rt = _get_runtime()
        if rt is None:
            return {"comparison": None, "error": "runtime unavailable"}
        comparison = rt.control_comparison()
        return {"comparison": comparison}

    @router.get("/validation/capability-freshness")
    async def get_freshness(
        threshold_days: int = 30,
        _operator: Any = Depends(require_operator_dep),
    ) -> dict[str, Any]:
        rt = _get_runtime()
        if rt is None:
            return {"stale": [], "error": "runtime unavailable"}
        stale = rt.stale_capabilities(threshold_days=threshold_days)
        return {"stale": [s.to_dict() for s in stale]}

    @router.get("/validation/projection-readiness")
    async def get_projection_readiness(
        _operator: Any = Depends(require_operator_dep),
    ) -> dict[str, Any]:
        try:
            from substrate.organism.benchmarks.projection_readiness import (
                ProjectionReadinessBenchmark,
            )
            bench = ProjectionReadinessBenchmark()
            result = bench.evaluate()
            return {"readiness": result.to_dict()}
        except Exception as e:
            logger.debug("ProjectionReadinessBenchmark error: %s", e)
            return {"readiness": None, "error": str(e)}

    @router.get("/validation/benchmarks/{benchmark_type}/latest")
    async def get_latest_benchmark(
        benchmark_type: str,
        _operator: Any = Depends(require_operator_dep),
    ) -> dict[str, Any]:
        rt = _get_runtime()
        if rt is None:
            return {"run": None, "error": "runtime unavailable"}
        run = rt.latest_run(benchmark_type)
        if run is None:
            return {"run": None, "error": "no runs found"}
        return {"run": run.to_dict()}

    @router.get("/validation/summary")
    async def get_summary(
        _operator: Any = Depends(require_operator_dep),
    ) -> dict[str, Any]:
        rt = _get_runtime()
        if rt is None:
            return {"summary": "runtime unavailable"}
        return {"summary": rt.summary()}

    return router
