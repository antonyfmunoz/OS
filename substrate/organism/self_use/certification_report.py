"""Certification report — 4-gate pass/fail with coherence override.

Gate 1: Surface Completeness
Gate 2: Production (COS + EOS Advancement)
Gate 3: Meta IDE Completeness
Gate 4: Coherence (NON-NEGOTIABLE — overrides all other gates)
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


class CertificationGate(str, Enum):
    SURFACE = "surface"
    PRODUCTION = "production"
    META_IDE = "meta_ide"
    COHERENCE = "coherence"


@dataclass
class CoherenceMetrics:
    """Coherence gate metrics — all must meet thresholds."""

    continuity_preservation: float = 0.0
    context_recovery: float = 0.0
    governance_challenge_rate: float = 0.0
    reality_correction_rate: float = 0.0
    false_history_accepted: int = 0
    lost_commitments: int = 0
    priority_inversions: int = 0

    THRESHOLDS = {
        "continuity_preservation": 0.95,
        "context_recovery": 0.90,
        "governance_challenge_rate": 0.80,
        "reality_correction_rate": 0.90,
    }

    @property
    def passes(self) -> bool:
        if self.false_history_accepted > 0:
            return False
        if self.lost_commitments > 0:
            return False
        if self.priority_inversions > 0:
            return False
        if self.continuity_preservation < self.THRESHOLDS["continuity_preservation"]:
            return False
        if self.context_recovery < self.THRESHOLDS["context_recovery"]:
            return False
        if self.governance_challenge_rate < self.THRESHOLDS["governance_challenge_rate"]:
            return False
        if self.reality_correction_rate < self.THRESHOLDS["reality_correction_rate"]:
            return False
        return True

    def to_dict(self) -> dict[str, Any]:
        return {
            "continuity_preservation": round(self.continuity_preservation, 4),
            "context_recovery": round(self.context_recovery, 4),
            "governance_challenge_rate": round(self.governance_challenge_rate, 4),
            "reality_correction_rate": round(self.reality_correction_rate, 4),
            "false_history_accepted": self.false_history_accepted,
            "lost_commitments": self.lost_commitments,
            "priority_inversions": self.priority_inversions,
            "passes": self.passes,
        }


@dataclass
class GateResult:
    """Result of evaluating a single gate."""

    gate: CertificationGate
    passed: bool
    score: float = 0.0
    detail: str = ""
    evidence: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "gate": self.gate.value,
            "passed": self.passed,
            "score": round(self.score, 4),
            "detail": self.detail,
            "evidence": self.evidence,
        }


@dataclass
class CertificationReport:
    """Full C27 certification report with 4-gate assessment."""

    report_id: str = field(default_factory=lambda: f"c27r-{uuid4().hex[:8]}")
    campaign: str = "C27"
    gate_results: list[GateResult] = field(default_factory=list)
    coherence: CoherenceMetrics = field(default_factory=CoherenceMetrics)
    overall_pass: bool = False
    override_reason: str = ""
    generated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def evaluate(self) -> bool:
        """Evaluate overall pass/fail with coherence override."""
        coherence_result = next(
            (g for g in self.gate_results if g.gate == CertificationGate.COHERENCE),
            None,
        )
        if coherence_result and not coherence_result.passed:
            self.overall_pass = False
            self.override_reason = (
                "COHERENCE OVERRIDE: Gate 4 failed — coherence overrides "
                "all other gates regardless of capability scores."
            )
            return False

        if not self.coherence.passes:
            self.overall_pass = False
            self.override_reason = "COHERENCE OVERRIDE: Coherence metrics below threshold."
            return False

        all_pass = all(g.passed for g in self.gate_results)
        self.overall_pass = all_pass
        if not all_pass:
            failed = [g.gate.value for g in self.gate_results if not g.passed]
            self.override_reason = f"Gates failed: {', '.join(failed)}"
        return all_pass

    def to_dict(self) -> dict[str, Any]:
        return {
            "report_id": self.report_id,
            "campaign": self.campaign,
            "overall_pass": self.overall_pass,
            "override_reason": self.override_reason,
            "gates": [g.to_dict() for g in self.gate_results],
            "coherence": self.coherence.to_dict(),
            "generated_at": self.generated_at.isoformat(),
        }

    def to_markdown(self) -> str:
        status = "PASS" if self.overall_pass else "FAIL"
        lines = [
            f"# C27 Certification Report — {status}",
            "",
            f"**Report ID:** {self.report_id}",
            f"**Generated:** {self.generated_at.isoformat()}",
            "",
        ]
        if self.override_reason:
            lines.append(f"> **{self.override_reason}**")
            lines.append("")
        lines.append("## Gates")
        lines.append("")
        lines.append("| Gate | Status | Score |")
        lines.append("|------|--------|-------|")
        for g in self.gate_results:
            mark = "PASS" if g.passed else "FAIL"
            lines.append(f"| {g.gate.value} | {mark} | {g.score:.2%} |")
        lines.append("")
        lines.append("## Coherence Metrics")
        lines.append("")
        cm = self.coherence
        lines.append(f"- Continuity preservation: {cm.continuity_preservation:.2%}")
        lines.append(f"- Context recovery: {cm.context_recovery:.2%}")
        lines.append(f"- Governance challenge rate: {cm.governance_challenge_rate:.2%}")
        lines.append(f"- Reality correction rate: {cm.reality_correction_rate:.2%}")
        lines.append(f"- False history accepted: {cm.false_history_accepted}")
        lines.append(f"- Lost commitments: {cm.lost_commitments}")
        lines.append(f"- Priority inversions: {cm.priority_inversions}")
        lines.append(f"- **Coherence pass: {cm.passes}**")
        return "\n".join(lines)


class ReportBuilder:
    """Builds the certification report from component data."""

    def __init__(self) -> None:
        self._report = CertificationReport()

    def set_surface_gate(
        self,
        surfaces_exercised: int,
        surfaces_total: int,
        gaps_documented: int,
    ) -> ReportBuilder:
        score = surfaces_exercised / max(surfaces_total, 1)
        self._report.gate_results.append(
            GateResult(
                gate=CertificationGate.SURFACE,
                passed=score >= 0.85 or (surfaces_exercised + gaps_documented >= surfaces_total),
                score=score,
                detail=f"{surfaces_exercised}/{surfaces_total} exercised, {gaps_documented} gaps documented",
                evidence={
                    "exercised": surfaces_exercised,
                    "total": surfaces_total,
                    "gaps_documented": gaps_documented,
                },
            )
        )
        return self

    def set_production_gate(
        self,
        completion_rate: float,
        delta_reduction: int,
        deploy_certify_cycles: int,
    ) -> ReportBuilder:
        self._report.gate_results.append(
            GateResult(
                gate=CertificationGate.PRODUCTION,
                passed=completion_rate >= 0.85 and delta_reduction > 0,
                score=completion_rate,
                detail=f"{completion_rate:.0%} completion, +{delta_reduction} operational capabilities, {deploy_certify_cycles} deploy cycles",
                evidence={
                    "completion_rate": round(completion_rate, 4),
                    "delta_reduction": delta_reduction,
                    "deploy_certify_cycles": deploy_certify_cycles,
                },
            )
        )
        return self

    def set_meta_ide_gate(
        self,
        subsystems_tested: int,
        subsystems_total: int,
        critical_path_broken: bool,
    ) -> ReportBuilder:
        score = subsystems_tested / max(subsystems_total, 1)
        self._report.gate_results.append(
            GateResult(
                gate=CertificationGate.META_IDE,
                passed=score >= 1.0 and not critical_path_broken,
                score=score,
                detail=f"{subsystems_tested}/{subsystems_total} tested, critical path broken: {critical_path_broken}",
                evidence={
                    "tested": subsystems_tested,
                    "total": subsystems_total,
                    "critical_path_broken": critical_path_broken,
                },
            )
        )
        return self

    def set_coherence_gate(self, metrics: CoherenceMetrics) -> ReportBuilder:
        self._report.coherence = metrics
        self._report.gate_results.append(
            GateResult(
                gate=CertificationGate.COHERENCE,
                passed=metrics.passes,
                score=(
                    metrics.continuity_preservation
                    + metrics.context_recovery
                    + metrics.governance_challenge_rate
                    + metrics.reality_correction_rate
                )
                / 4.0,
                detail="Coherence override active"
                if not metrics.passes
                else "All coherence thresholds met",
                evidence=metrics.to_dict(),
            )
        )
        return self

    def build(self) -> CertificationReport:
        self._report.evaluate()
        return self._report
