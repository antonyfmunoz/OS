"""Self-Improvement Interface — recursive system evolution.

Every major subsystem exposes four methods:
    metrics()              — current performance data
    evaluate()             — diagnosis of strengths/weaknesses
    propose_improvements() — concrete transformation proposals
    apply_improvements()   — execute the top proposal

This module defines the protocol and provides concrete implementations
for: Composition Engine, Execution Pipeline, and the Router.

Usage:
    from core.self_improvement import (
        CompositionImprover,
        PipelineImprover,
        run_improvement_cycle,
    )

    ci = CompositionImprover()
    report = ci.evaluate()
    proposals = ci.propose_improvements()
"""

from __future__ import annotations

import json
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from core.primitives import PrimitiveTag
from core.transformer import TransformationResult, transform


# ---------------------------------------------------------------------------
# Protocol
# ---------------------------------------------------------------------------


class SelfImprovingComponent(ABC):
    """Protocol that every improvable subsystem must implement.

    The four methods form a closed loop:
        metrics → evaluate → propose → apply → metrics (improved)
    """

    @abstractmethod
    def metrics(self) -> dict[str, Any]:
        """Return current performance metrics."""

    @abstractmethod
    def evaluate(self) -> dict[str, Any]:
        """Diagnose current state — what's working, what isn't."""

    @abstractmethod
    def propose_improvements(self) -> list[TransformationResult]:
        """Return ranked list of improvement proposals."""

    @abstractmethod
    def apply_improvements(
        self, proposals: list[TransformationResult] | None = None
    ) -> dict[str, Any]:
        """Apply the top proposal(s). Returns summary of changes."""


# ---------------------------------------------------------------------------
# Improvement history (append-only trace)
# ---------------------------------------------------------------------------

_DATA_DIR = Path("/opt/OS/data")
_IMPROVEMENT_LOG = _DATA_DIR / "improvement_log.jsonl"


@dataclass
class ImprovementRecord:
    """One entry in the improvement log."""

    component: str
    timestamp: float
    metrics_before: dict[str, Any]
    metrics_after: dict[str, Any]
    transformation: dict[str, Any]
    success: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "component": self.component,
            "timestamp": self.timestamp,
            "metrics_before": self.metrics_before,
            "metrics_after": self.metrics_after,
            "transformation": self.transformation,
            "success": self.success,
        }


def _log_improvement(record: ImprovementRecord) -> None:
    """Append an improvement record to the log."""
    _DATA_DIR.mkdir(parents=True, exist_ok=True)
    with _IMPROVEMENT_LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record.to_dict(), default=str) + "\n")


def load_improvement_history(
    component: str | None = None, limit: int = 100
) -> list[dict[str, Any]]:
    """Read recent improvement records, optionally filtered by component."""
    if not _IMPROVEMENT_LOG.exists():
        return []
    records: list[dict[str, Any]] = []
    with _IMPROVEMENT_LOG.open("r", encoding="utf-8") as f:
        for line in f.readlines()[-limit:]:
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except Exception:
                continue
            if component and row.get("component") != component:
                continue
            records.append(row)
    return records


# ---------------------------------------------------------------------------
# Concrete: Composition Engine Improver
# ---------------------------------------------------------------------------


class CompositionImprover(SelfImprovingComponent):
    """Self-improvement interface for the Composition Engine.

    Analyses composition patterns across historical pipeline results
    to identify which domain types produce the best primitive coverage
    and which consistently miss important primitives.
    """

    def __init__(self) -> None:
        self._history = load_improvement_history("composition")

    def metrics(self) -> dict[str, Any]:
        """Composition metrics: coverage by domain type, common gaps."""
        from core.domain.eos import DOMAIN_TYPES

        domain_coverage: dict[str, dict[str, Any]] = {}
        for dtype, cls in DOMAIN_TYPES.items():
            inst = cls(name=f"metric_probe:{dtype}")
            tags = inst.to_primitives()
            all_tags = set(PrimitiveTag)
            coverage = len(tags) / len(all_tags)
            missing = all_tags - tags
            domain_coverage[dtype] = {
                "primitive_count": len(tags),
                "coverage": round(coverage, 3),
                "primitives": sorted(t.value for t in tags),
                "missing": sorted(t.value for t in missing),
            }

        return {
            "domain_types": len(DOMAIN_TYPES),
            "domain_coverage": domain_coverage,
            "improvement_history_count": len(self._history),
        }

    def evaluate(self) -> dict[str, Any]:
        """Identify domain types with low coverage or missing critical primitives."""
        m = self.metrics()
        issues: list[dict[str, Any]] = []

        for dtype, data in m["domain_coverage"].items():
            # Flag domains missing OUTCOME (can't measure success)
            if "outcome" in data["missing"]:
                issues.append(
                    {
                        "domain": dtype,
                        "issue": "missing_outcome",
                        "severity": "high",
                        "detail": f"{dtype} has no OUTCOME — results can't be measured",
                    }
                )
            # Flag domains with < 50% coverage
            if data["coverage"] < 0.5:
                issues.append(
                    {
                        "domain": dtype,
                        "issue": "low_coverage",
                        "severity": "medium",
                        "detail": f"{dtype} covers {data['coverage']:.0%} of primitives",
                    }
                )

        return {
            "component": "composition",
            "issues": issues,
            "health": "healthy" if not issues else "needs_attention",
        }

    def propose_improvements(self) -> list[TransformationResult]:
        """Propose transformations for each domain type that has gaps."""
        from core.domain.eos import DOMAIN_TYPES

        proposals: list[TransformationResult] = []
        eval_result = self.evaluate()

        for issue in eval_result.get("issues", []):
            dtype = issue["domain"]
            cls = DOMAIN_TYPES.get(dtype)
            if not cls:
                continue
            inst = cls(name=f"improvement_probe:{dtype}")
            tags = inst.to_primitives()

            result = transform(
                primitives=tags,
                objective=f"improve {dtype} domain composition for completeness",
                constraints={"source": "self_improvement"},
            )
            if result.changed:
                proposals.append(result)

        return proposals

    def apply_improvements(
        self, proposals: list[TransformationResult] | None = None
    ) -> dict[str, Any]:
        """Log proposed improvements.

        Composition improvements are logged but not auto-applied — domain
        compositions are code-level definitions. The proposals serve as
        recommendations for the developer agent.
        """
        proposals = proposals or self.propose_improvements()
        if not proposals:
            return {"applied": 0, "reason": "no proposals"}

        metrics_before = self.metrics()
        for proposal in proposals:
            _log_improvement(
                ImprovementRecord(
                    component="composition",
                    timestamp=time.time(),
                    metrics_before=metrics_before,
                    metrics_after=metrics_before,  # same — proposals are advisory
                    transformation=proposal.to_dict(),
                    success=True,
                )
            )

        return {
            "applied": len(proposals),
            "mode": "advisory",
            "proposals": [p.to_dict() for p in proposals],
        }


# ---------------------------------------------------------------------------
# Concrete: Pipeline Improver
# ---------------------------------------------------------------------------


class PipelineImprover(SelfImprovingComponent):
    """Self-improvement interface for the Execution Pipeline.

    Analyses pipeline execution logs to identify failure patterns,
    slow steps, and primitive-level bottlenecks.
    """

    def __init__(self) -> None:
        self._history = load_improvement_history("pipeline")
        self._action_log = _DATA_DIR / "action_log.jsonl"

    def metrics(self) -> dict[str, Any]:
        """Pipeline metrics from action log."""
        if not self._action_log.exists():
            return {"total_runs": 0, "success_rate": 0.0}

        rows: list[dict[str, Any]] = []
        with self._action_log.open("r", encoding="utf-8") as f:
            for line in f.readlines()[-500:]:
                line = line.strip()
                if not line:
                    continue
                try:
                    rows.append(json.loads(line))
                except Exception:
                    continue

        total = len(rows)
        ok_count = sum(1 for r in rows if r.get("status") == "executed")
        failed = sum(1 for r in rows if r.get("status") == "failed")

        return {
            "total_runs": total,
            "success_rate": round(ok_count / total, 3) if total else 0.0,
            "failure_rate": round(failed / total, 3) if total else 0.0,
            "ok_count": ok_count,
            "failed_count": failed,
            "improvement_history_count": len(self._history),
        }

    def evaluate(self) -> dict[str, Any]:
        """Diagnose pipeline health."""
        m = self.metrics()
        issues: list[dict[str, Any]] = []

        if m["total_runs"] > 0 and m["failure_rate"] > 0.3:
            issues.append(
                {
                    "issue": "high_failure_rate",
                    "severity": "high",
                    "detail": f"failure rate is {m['failure_rate']:.0%} over {m['total_runs']} runs",
                }
            )

        if m["total_runs"] == 0:
            issues.append(
                {
                    "issue": "no_data",
                    "severity": "info",
                    "detail": "no pipeline executions recorded yet",
                }
            )

        return {
            "component": "pipeline",
            "issues": issues,
            "health": "healthy" if not issues else "needs_attention",
        }

    def propose_improvements(self) -> list[TransformationResult]:
        """Propose primitive-level improvements based on pipeline failures."""
        eval_result = self.evaluate()
        proposals: list[TransformationResult] = []

        for issue in eval_result.get("issues", []):
            if issue["issue"] == "high_failure_rate":
                # Propose adding FEEDBACK + OUTCOME to catch failures earlier
                base_tags = {PrimitiveTag.ACTION, PrimitiveTag.GOAL}
                result = transform(
                    primitives=base_tags,
                    objective="reduce pipeline failure rate through better feedback loops",
                    constraints={
                        "must_include_feedback": True,
                        "must_include_outcome": True,
                    },
                )
                if result.changed:
                    proposals.append(result)

        return proposals

    def apply_improvements(
        self, proposals: list[TransformationResult] | None = None
    ) -> dict[str, Any]:
        """Log pipeline improvement proposals."""
        proposals = proposals or self.propose_improvements()
        if not proposals:
            return {"applied": 0, "reason": "no proposals"}

        metrics_before = self.metrics()
        for proposal in proposals:
            _log_improvement(
                ImprovementRecord(
                    component="pipeline",
                    timestamp=time.time(),
                    metrics_before=metrics_before,
                    metrics_after=metrics_before,
                    transformation=proposal.to_dict(),
                    success=True,
                )
            )

        return {
            "applied": len(proposals),
            "mode": "advisory",
            "proposals": [p.to_dict() for p in proposals],
        }


# ---------------------------------------------------------------------------
# Concrete: Router Improver
# ---------------------------------------------------------------------------


class RouterImprover(SelfImprovingComponent):
    """Self-improvement interface for intent routing.

    Analyses how well the intent → domain resolution performs by
    checking for misrouted intents (based on execution feedback).
    """

    def __init__(self) -> None:
        self._history = load_improvement_history("router")

    def metrics(self) -> dict[str, Any]:
        """Router metrics from improvement history."""
        return {
            "improvement_history_count": len(self._history),
            "component": "router",
        }

    def evaluate(self) -> dict[str, Any]:
        """Evaluate router health — requires feedback data to be meaningful."""
        return {
            "component": "router",
            "issues": [],
            "health": "healthy",
        }

    def propose_improvements(self) -> list[TransformationResult]:
        """No automatic proposals for router — requires human judgment."""
        return []

    def apply_improvements(
        self, proposals: list[TransformationResult] | None = None
    ) -> dict[str, Any]:
        """Router improvements require code changes — always advisory."""
        return {
            "applied": 0,
            "mode": "advisory",
            "reason": "router changes require human review",
        }


# ---------------------------------------------------------------------------
# Orchestration: run a full improvement cycle across all components
# ---------------------------------------------------------------------------

# Registry of all improvable components
IMPROVABLE_COMPONENTS: dict[str, type[SelfImprovingComponent]] = {
    "composition": CompositionImprover,
    "pipeline": PipelineImprover,
    "router": RouterImprover,
}


def run_improvement_cycle(
    components: list[str] | None = None,
) -> dict[str, Any]:
    """Run evaluate → propose → apply across specified components.

    Returns a summary of all proposals generated and their status.
    """
    targets = components or list(IMPROVABLE_COMPONENTS.keys())
    results: dict[str, Any] = {}

    for name in targets:
        cls = IMPROVABLE_COMPONENTS.get(name)
        if not cls:
            results[name] = {"error": f"unknown component: {name}"}
            continue

        improver = cls()
        evaluation = improver.evaluate()
        proposals = improver.propose_improvements()
        apply_result = improver.apply_improvements(proposals)

        results[name] = {
            "evaluation": evaluation,
            "proposals_count": len(proposals),
            "apply_result": apply_result,
        }

    return {
        "cycle_timestamp": time.time(),
        "components_checked": targets,
        "results": results,
    }


__all__ = [
    "SelfImprovingComponent",
    "CompositionImprover",
    "PipelineImprover",
    "RouterImprover",
    "IMPROVABLE_COMPONENTS",
    "run_improvement_cycle",
    "load_improvement_history",
]
