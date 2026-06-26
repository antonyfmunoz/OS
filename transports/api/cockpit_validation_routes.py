"""Cockpit validation routes — capability compounding proof + competitive matrix surface.

Mounted under /api/umh/ via include_router in cockpit.py.

Campaigns 23A + 23B. UMH transport layer. Instance-agnostic.
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
    def list_runs(
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
    def get_run(
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
    def get_report(
        _operator: Any = Depends(require_operator_dep),
    ) -> dict[str, Any]:
        rt = _get_runtime()
        if rt is None:
            return {"report": None, "error": "runtime unavailable"}
        report = rt.generate_report()
        return {"report": report.to_dict()}

    @router.get("/validation/compounding-curve")
    def get_compounding_curve(
        _operator: Any = Depends(require_operator_dep),
    ) -> dict[str, Any]:
        rt = _get_runtime()
        if rt is None:
            return {"curve": None, "error": "runtime unavailable"}
        curve = rt.compounding_curve()
        return {"curve": curve}

    @router.get("/validation/control-comparison")
    def get_control_comparison(
        _operator: Any = Depends(require_operator_dep),
    ) -> dict[str, Any]:
        rt = _get_runtime()
        if rt is None:
            return {"comparison": None, "error": "runtime unavailable"}
        comparison = rt.control_comparison()
        return {"comparison": comparison}

    @router.get("/validation/capability-freshness")
    def get_freshness(
        threshold_days: int = 30,
        _operator: Any = Depends(require_operator_dep),
    ) -> dict[str, Any]:
        rt = _get_runtime()
        if rt is None:
            return {"stale": [], "error": "runtime unavailable"}
        stale = rt.stale_capabilities(threshold_days=threshold_days)
        return {"stale": [s.to_dict() for s in stale]}

    @router.get("/validation/projection-readiness")
    def get_projection_readiness(
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
    def get_latest_benchmark(
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
    def get_summary(
        _operator: Any = Depends(require_operator_dep),
    ) -> dict[str, Any]:
        rt = _get_runtime()
        if rt is None:
            return {"summary": "runtime unavailable"}
        return {"summary": rt.summary()}

    # ------------------------------------------------------------------
    # Campaign 23B: Competitive Matrix routes
    # ------------------------------------------------------------------

    @router.get("/validation/competitive/matrix")
    def get_competitive_matrix(
        _operator: Any = Depends(require_operator_dep),
    ) -> dict[str, Any]:
        try:
            from substrate.organism.benchmarks.competitive import CompetitorRegistry
            from substrate.organism.benchmarks.composite_scorer import CompositeScorer
            reg = CompetitorRegistry()
            reg.load()
            scorer = CompositeScorer(registry=reg)
            matrix = scorer.generate_matrix()
            return {"matrix": matrix.to_dict()}
        except Exception as e:
            logger.debug("Competitive matrix error: %s", e)
            return {"matrix": None, "error": str(e)}

    @router.get("/validation/competitive/competitors")
    def get_competitors(
        market_category: str | None = None,
        _operator: Any = Depends(require_operator_dep),
    ) -> dict[str, Any]:
        try:
            from substrate.organism.benchmarks.competitive import CompetitorRegistry
            reg = CompetitorRegistry()
            reg.load()
            if market_category:
                comps = reg.by_market_category(market_category)
            else:
                comps = reg.all_competitors()
            return {"competitors": [c.to_dict() for c in comps], "count": len(comps)}
        except Exception as e:
            logger.debug("Competitors error: %s", e)
            return {"competitors": [], "error": str(e)}

    @router.get("/validation/competitive/gap-analysis")
    def get_gap_analysis(
        _operator: Any = Depends(require_operator_dep),
    ) -> dict[str, Any]:
        try:
            from substrate.organism.benchmarks.competitive import CompetitorRegistry
            from substrate.organism.benchmarks.composite_scorer import CompositeScorer
            reg = CompetitorRegistry()
            reg.load()
            scorer = CompositeScorer(registry=reg)
            gaps = scorer.gap_analysis()
            return {
                "gaps": [g.to_dict() for g in gaps],
                "leading": len([g for g in gaps if g.gap_type == "leading"]),
                "trailing": len([g for g in gaps if g.gap_type == "trailing"]),
                "parity": len([g for g in gaps if g.gap_type == "parity"]),
            }
        except Exception as e:
            logger.debug("Gap analysis error: %s", e)
            return {"gaps": [], "error": str(e)}

    @router.get("/validation/competitive/category/{category_id}")
    def get_category_detail(
        category_id: str,
        _operator: Any = Depends(require_operator_dep),
    ) -> dict[str, Any]:
        try:
            from substrate.organism.benchmarks.competitive import (
                CATEGORY_REGISTRY,
                CompetitorRegistry,
            )
            from substrate.organism.benchmarks.composite_scorer import CompositeScorer
            cat_info = CATEGORY_REGISTRY.get(category_id.upper())
            if cat_info is None:
                return {"category": None, "error": "unknown category"}
            reg = CompetitorRegistry()
            reg.load()
            scorer = CompositeScorer(registry=reg)
            cs = scorer.get_score(category_id.upper())
            return {
                "category_id": category_id.upper(),
                "info": cat_info,
                "score": cs.to_dict() if cs else None,
            }
        except Exception as e:
            logger.debug("Category detail error: %s", e)
            return {"category": None, "error": str(e)}

    @router.get("/validation/competitive/market/{market_category}")
    def get_market_comparison(
        market_category: str,
        _operator: Any = Depends(require_operator_dep),
    ) -> dict[str, Any]:
        try:
            from substrate.organism.benchmarks.competitive import CompetitorRegistry
            from substrate.organism.benchmarks.composite_scorer import CompositeScorer
            reg = CompetitorRegistry()
            reg.load()
            scorer = CompositeScorer(registry=reg)
            mc_data = scorer.market_category_comparison()
            if market_category not in mc_data:
                return {"market_category": market_category, "error": "no data"}
            return {"market_category": market_category, "data": mc_data[market_category]}
        except Exception as e:
            logger.debug("Market comparison error: %s", e)
            return {"market_category": market_category, "error": str(e)}

    @router.get("/validation/composite")
    def get_composite_scores(
        _operator: Any = Depends(require_operator_dep),
    ) -> dict[str, Any]:
        try:
            from substrate.organism.benchmarks.competitive import CompetitorRegistry
            from substrate.organism.benchmarks.composite_scorer import CompositeScorer
            reg = CompetitorRegistry()
            reg.load()
            scorer = CompositeScorer(registry=reg)
            return {"composite": scorer.summary()}
        except Exception as e:
            logger.debug("Composite scores error: %s", e)
            return {"composite": None, "error": str(e)}

    @router.get("/validation/external/{benchmark_name}/latest")
    def get_external_benchmark(
        benchmark_name: str,
        _operator: Any = Depends(require_operator_dep),
    ) -> dict[str, Any]:
        try:
            from substrate.organism.benchmarks.external_adapters import get_adapter
            adapter = get_adapter(benchmark_name, test_mode=True)
            if adapter is None:
                return {"result": None, "error": f"unknown benchmark: {benchmark_name}"}
            result = adapter.run_all()
            return {"result": result.to_dict()}
        except Exception as e:
            logger.debug("External benchmark error: %s", e)
            return {"result": None, "error": str(e)}

    @router.get("/validation/audits/{audit_name}/latest")
    def get_audit_report(
        audit_name: str,
        _operator: Any = Depends(require_operator_dep),
    ) -> dict[str, Any]:
        rt = _get_runtime()
        if rt is None:
            return {"report": None, "error": "runtime unavailable"}
        run = rt.latest_run(audit_name)
        if run is None:
            return {"report": None, "error": "no runs found"}
        return {"report": run.to_dict()}

    return router
