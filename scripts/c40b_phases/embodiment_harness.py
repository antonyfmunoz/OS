"""C40B Embodiment Harness — 4-dimensional runtime qualification.

Wraps the existing QualificationHarness for the Organism dimension.
Adds Runtime, Projection, and Operator dimensions for full-stack certification.
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import asdict, dataclass, field
from typing import Any

import os
import sys
_PHASE_DIR = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.dirname(os.path.dirname(_PHASE_DIR))
sys.path.insert(0, "/opt/OS")
sys.path.insert(0, _REPO_ROOT)

from substrate.organism.qualification_harness import (
    ConfidenceEstimate,
    ConvergenceWindow,
    ORL,
    QualificationHarness,
    QualificationReport,
)

from scripts.c40b_phases.campaign_context import SLOTracker

logger = logging.getLogger("c40b")


# ── Dimension dataclasses ────────────────────────────────────────────────


@dataclass
class DimensionResult:
    name: str
    status: str = "UNTESTED"
    metrics: dict = field(default_factory=dict)
    gate_passed: bool = False
    evidence: str = ""
    blockers: list = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "status": self.status,
            "metrics": self.metrics,
            "gate_passed": self.gate_passed,
            "evidence": self.evidence,
            "blockers": self.blockers,
        }


@dataclass
class ProductionReadinessCheck:
    check: str
    requirement: str
    met: bool = False
    evidence: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class EmbodimentReport:
    organism: DimensionResult = field(
        default_factory=lambda: DimensionResult(name="Organism")
    )
    runtime: DimensionResult = field(
        default_factory=lambda: DimensionResult(name="Runtime")
    )
    projection: DimensionResult = field(
        default_factory=lambda: DimensionResult(name="Projection")
    )
    operator: DimensionResult = field(
        default_factory=lambda: DimensionResult(name="Operator")
    )
    production_readiness: list = field(default_factory=list)
    verdict: str = "NOT READY"
    timestamp: float = 0.0

    def all_dimensions_pass(self) -> bool:
        return all(
            d.status == "PASS"
            for d in [self.organism, self.runtime, self.projection, self.operator]
        )

    def all_production_checks_met(self) -> bool:
        return all(c.met for c in self.production_readiness)

    def is_production_ready(self) -> bool:
        return self.all_dimensions_pass() and self.all_production_checks_met()

    def to_dict(self) -> dict:
        return {
            "organism": self.organism.to_dict(),
            "runtime": self.runtime.to_dict(),
            "projection": self.projection.to_dict(),
            "operator": self.operator.to_dict(),
            "production_readiness": [c.to_dict() for c in self.production_readiness],
            "verdict": self.verdict,
            "timestamp": self.timestamp,
        }


# ── Embodiment Harness ────────────────────────────────────────────────────


class EmbodimentHarness:
    """4-dimensional runtime certification harness."""

    def __init__(self) -> None:
        self.report = EmbodimentReport(timestamp=time.time())

    def evaluate_organism(
        self,
        qual_report: QualificationReport | None = None,
    ) -> DimensionResult:
        dim = self.report.organism
        if qual_report is None:
            dim.status = "UNTESTED"
            dim.evidence = "no qualification report provided"
            return dim

        orl_val = (
            qual_report.orl_achieved.value
            if isinstance(qual_report.orl_achieved, ORL)
            else qual_report.orl_achieved
        )
        conf = qual_report.orl_confidence
        pa = qual_report.predictive_accuracy

        dim.metrics = {
            "orl": orl_val,
            "confidence": round(conf, 4),
            "predictive_accuracy": round(pa, 4),
            "total_mutations": qual_report.total_mutations,
            "weakest_property": qual_report.weakest_property,
        }

        passed = orl_val >= 8 and conf >= 0.95
        dim.gate_passed = passed
        dim.status = "PASS" if passed else "FAIL"
        if not passed:
            if orl_val < 8:
                dim.blockers.append("ORL %d < 8" % orl_val)
            if conf < 0.95:
                dim.blockers.append("confidence %.3f < 0.95" % conf)
        dim.evidence = "qualification_harness"
        return dim

    def evaluate_runtime(self, slo: SLOTracker) -> DimensionResult:
        dim = self.report.runtime
        scorecard = slo.to_scorecard()
        dim.metrics = scorecard

        passed = slo.all_slos_met()
        dim.gate_passed = passed
        dim.status = "PASS" if passed else "FAIL"

        if not passed:
            if slo.mesh_reliability() < 0.99:
                dim.blockers.append(
                    "mesh reliability %.1f%% < 99%%" % (slo.mesh_reliability() * 100)
                )
            if slo.session_availability() < 0.95:
                dim.blockers.append(
                    "session availability %.1f%% < 95%%"
                    % (slo.session_availability() * 100)
                )
            if slo.dispatch_success_rate() < 0.95:
                dim.blockers.append(
                    "dispatch success %.1f%% < 95%%"
                    % (slo.dispatch_success_rate() * 100)
                )
            if slo.avg_latency_ms() >= 1000:
                dim.blockers.append(
                    "avg latency %.0fms >= 1000ms" % slo.avg_latency_ms()
                )
            if slo.p95_latency_ms() >= 3000:
                dim.blockers.append(
                    "p95 latency %.0fms >= 3000ms" % slo.p95_latency_ms()
                )
            if slo.event_loss > 0:
                dim.blockers.append("event loss: %d" % slo.event_loss)

        dim.evidence = "slo_scorecard"
        return dim

    def evaluate_projection(
        self,
        event_loss: int = 0,
        surface_equivalence: float = 1.0,
        proof_completeness: float = 1.0,
        surfaces_tested: int = 0,
    ) -> DimensionResult:
        dim = self.report.projection
        dim.metrics = {
            "event_loss": event_loss,
            "surface_equivalence": round(surface_equivalence, 4),
            "proof_completeness": round(proof_completeness, 4),
            "surfaces_tested": surfaces_tested,
        }

        passed = (
            event_loss == 0
            and surface_equivalence >= 1.0
            and proof_completeness >= 1.0
        )
        dim.gate_passed = passed
        dim.status = "PASS" if passed else "FAIL"

        if event_loss > 0:
            dim.blockers.append("event loss: %d" % event_loss)
        if surface_equivalence < 1.0:
            dim.blockers.append(
                "surface equivalence %.1f%% < 100%%"
                % (surface_equivalence * 100)
            )
        if proof_completeness < 1.0:
            dim.blockers.append(
                "proof completeness %.1f%% < 100%%"
                % (proof_completeness * 100)
            )

        dim.evidence = "projection_measurement"
        return dim

    def evaluate_operator(
        self,
        scenario_success_rate: float = 0.0,
        scenarios_passed: int = 0,
        scenarios_total: int = 25,
        total_executions: int = 0,
        synthetic_evidence_count: int = 0,
        evidence_quality_rate: float = 0.0,
    ) -> DimensionResult:
        dim = self.report.operator
        dim.metrics = {
            "scenario_success_rate": round(scenario_success_rate, 4),
            "scenarios_passed": scenarios_passed,
            "scenarios_total": scenarios_total,
            "total_executions": total_executions,
            "synthetic_evidence_count": synthetic_evidence_count,
            "evidence_quality_rate": round(evidence_quality_rate, 4),
        }

        passed = (
            scenario_success_rate >= 0.95
            and synthetic_evidence_count == 0
            and total_executions >= 100
        )
        dim.gate_passed = passed
        dim.status = "PASS" if passed else "FAIL"

        if scenario_success_rate < 0.95:
            dim.blockers.append(
                "scenario success %.1f%% < 95%%"
                % (scenario_success_rate * 100)
            )
        if synthetic_evidence_count > 0:
            dim.blockers.append(
                "synthetic evidence: %d" % synthetic_evidence_count
            )
        if total_executions < 100:
            dim.blockers.append(
                "total executions %d < 100" % total_executions
            )

        dim.evidence = "operator_qualification"
        return dim

    def build_production_readiness(
        self,
        slo: SLOTracker,
        scenarios_passed: int = 0,
        synthetic_count: int = 0,
        recovery_demonstrated: bool = False,
        total_operator_executions: int = 0,
        browser_availability: float = 0.0,
        proof_chain_complete: bool = False,
        orl_preserved: bool = False,
    ) -> list[ProductionReadinessCheck]:
        checks = [
            ProductionReadinessCheck(
                check="Core workflows",
                requirement="25/25 scenarios pass",
                met=scenarios_passed >= 25,
                evidence="%d/25 passed" % scenarios_passed,
            ),
            ProductionReadinessCheck(
                check="No synthetic evidence",
                requirement="Zero synthetic evidence files",
                met=synthetic_count == 0,
                evidence="%d synthetic" % synthetic_count,
            ),
            ProductionReadinessCheck(
                check="Recovery demonstrated",
                requirement="10+ injected failures recovered",
                met=recovery_demonstrated,
                evidence="recovery tested" if recovery_demonstrated else "not tested",
            ),
            ProductionReadinessCheck(
                check="Computer Use stable",
                requirement="100+ operator executions",
                met=total_operator_executions >= 100,
                evidence="%d executions" % total_operator_executions,
            ),
            ProductionReadinessCheck(
                check="Browser stable",
                requirement="Chrome + Playwright >= 95%%",
                met=browser_availability >= 0.95,
                evidence="%.1f%% availability" % (browser_availability * 100),
            ),
            ProductionReadinessCheck(
                check="Proof chain complete",
                requirement="Every action traceable intent to proof",
                met=proof_chain_complete,
                evidence="complete" if proof_chain_complete else "incomplete",
            ),
            ProductionReadinessCheck(
                check="Qualification stable",
                requirement="ORL-8 preserved",
                met=orl_preserved,
                evidence="preserved" if orl_preserved else "degraded",
            ),
            ProductionReadinessCheck(
                check="Runtime SLOs met",
                requirement="All SLO targets met",
                met=slo.all_slos_met(),
                evidence=json.dumps(slo.to_scorecard()),
            ),
        ]
        self.report.production_readiness = checks
        return checks

    def finalize(self) -> EmbodimentReport:
        if self.report.is_production_ready():
            self.report.verdict = "PRODUCTION READY"
        else:
            self.report.verdict = "NOT READY"
        self.report.timestamp = time.time()
        return self.report
