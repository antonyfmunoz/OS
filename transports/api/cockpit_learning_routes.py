"""Cockpit routes for Learning Intelligence — Campaign 12.4.

Exposes learning extraction, outcome patterns, capability evolution,
portfolio health, drift detection, and compounding scores to the cockpit.
10 endpoints under /learning/ prefix. Read-only.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

# ── Lazy Singletons ───────────────────────────────────────────────────────

_extraction_runtime: Any = None
_pattern_engine: Any = None
_evolution_engine: Any = None
_portfolio_runtime: Any = None


def _get_extraction() -> Any:
    global _extraction_runtime
    if _extraction_runtime is None:
        try:
            from substrate.organism.learning_extraction_runtime import LearningExtractionRuntime
            _extraction_runtime = LearningExtractionRuntime()
        except Exception:
            logger.debug("Failed to init LearningExtractionRuntime", exc_info=True)
    return _extraction_runtime


def _get_patterns() -> Any:
    global _pattern_engine
    if _pattern_engine is None:
        try:
            from substrate.organism.outcome_pattern_engine import OutcomePatternEngine
            _pattern_engine = OutcomePatternEngine()
        except Exception:
            logger.debug("Failed to init OutcomePatternEngine", exc_info=True)
    return _pattern_engine


def _get_evolution() -> Any:
    global _evolution_engine
    if _evolution_engine is None:
        try:
            from substrate.organism.capability_evolution_engine import CapabilityEvolutionEngine
            _evolution_engine = CapabilityEvolutionEngine()
        except Exception:
            logger.debug("Failed to init CapabilityEvolutionEngine", exc_info=True)
    return _evolution_engine


def _get_portfolio() -> Any:
    global _portfolio_runtime
    if _portfolio_runtime is None:
        try:
            from substrate.organism.learning_portfolio_runtime import LearningPortfolioRuntime
            _portfolio_runtime = LearningPortfolioRuntime()
        except Exception:
            logger.debug("Failed to init LearningPortfolioRuntime", exc_info=True)
    return _portfolio_runtime


def get_router() -> Any:
    from fastapi import APIRouter

    router = APIRouter(
        prefix="/learning",
        tags=["learning-intelligence"],
    )

    @router.get("/overview")
    def learning_overview() -> dict[str, Any]:
        rt = _get_portfolio()
        if rt is None:
            return {"error": "unavailable"}
        try:
            return rt.snapshot().to_dict()
        except Exception:
            logger.debug("Overview query failed", exc_info=True)
            return {"error": "snapshot failed"}

    @router.get("/lessons")
    def learning_lessons() -> dict[str, Any]:
        rt = _get_extraction()
        if rt is None:
            return {"lessons": []}
        try:
            lessons = rt.recent_lessons(limit=50)
            return {"lessons": [l.to_dict() for l in lessons]}
        except Exception:
            logger.debug("Lessons query failed", exc_info=True)
            return {"lessons": []}

    @router.get("/lessons/actionable")
    def actionable_lessons() -> dict[str, Any]:
        rt = _get_extraction()
        if rt is None:
            return {"lessons": []}
        try:
            lessons = rt.actionable_lessons()
            return {"lessons": [l.to_dict() for l in lessons]}
        except Exception:
            logger.debug("Actionable lessons query failed", exc_info=True)
            return {"lessons": []}

    @router.get("/patterns")
    def learning_patterns() -> dict[str, Any]:
        rt = _get_patterns()
        if rt is None:
            return {"patterns": []}
        try:
            patterns = rt.top_patterns(limit=30)
            return {"patterns": [p.to_dict() for p in patterns]}
        except Exception:
            logger.debug("Patterns query failed", exc_info=True)
            return {"patterns": []}

    @router.get("/patterns/{pattern_id}")
    def pattern_detail(pattern_id: str) -> dict[str, Any]:
        rt = _get_patterns()
        if rt is None:
            return {"error": "unavailable"}
        try:
            patterns = rt.top_patterns(limit=200)
            for p in patterns:
                if p.id == pattern_id:
                    return p.to_dict()
            return {"error": "not found"}
        except Exception:
            logger.debug("Pattern detail query failed", exc_info=True)
            return {"error": "query failed"}

    @router.get("/evolution")
    def capability_evolution() -> dict[str, Any]:
        rt = _get_evolution()
        if rt is None:
            return {"trajectories": []}
        try:
            trajectories = rt.all_trajectories()
            return {"trajectories": [t.to_dict() for t in trajectories]}
        except Exception:
            logger.debug("Evolution query failed", exc_info=True)
            return {"trajectories": []}

    @router.get("/evolution/{capability_id}")
    def evolution_detail(capability_id: str) -> dict[str, Any]:
        rt = _get_evolution()
        if rt is None:
            return {"error": "unavailable"}
        try:
            t = rt.trajectory(capability_id)
            if t is None:
                return {"error": "not found"}
            return t.to_dict()
        except Exception:
            logger.debug("Evolution detail query failed", exc_info=True)
            return {"error": "query failed"}

    @router.get("/drift")
    def learning_drift() -> dict[str, Any]:
        rt = _get_portfolio()
        if rt is None:
            return {"warnings": []}
        try:
            warnings = rt.drift_warnings()
            return {"warnings": [w.to_dict() for w in warnings]}
        except Exception:
            logger.debug("Drift query failed", exc_info=True)
            return {"warnings": []}

    @router.get("/health")
    def learning_health() -> dict[str, Any]:
        rt = _get_portfolio()
        if rt is None:
            return {"health": "unknown"}
        try:
            h = rt.health()
            eff = rt.learning_effectiveness()
            return {
                "health": h.value if hasattr(h, "value") else str(h),
                "effectiveness": eff,
            }
        except Exception:
            logger.debug("Health query failed", exc_info=True)
            return {"health": "unknown"}

    @router.get("/compounding")
    def learning_compounding() -> dict[str, Any]:
        rt = _get_portfolio()
        if rt is None:
            return {"compounding_score": 0.0}
        try:
            score = rt.compounding_score()
            velocity = rt.lesson_velocity()
            return {
                "compounding_score": round(score, 4),
                "lesson_velocity": round(velocity, 4),
            }
        except Exception:
            logger.debug("Compounding query failed", exc_info=True)
            return {"compounding_score": 0.0}

    return router
