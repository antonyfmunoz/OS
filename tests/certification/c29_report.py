#!/usr/bin/env python3
"""C29 Harness Superiority — Certification Report Generator.

Generates the full comparative report with evidence classification,
MVP Trust Verdict, and pass/fail criteria evaluation.

Pure computation from stored results. Zero LLM calls. All scoring is
delegated to HarnessScorer / HTICalculator / UMHMetricCalculator /
MVPVerdictEngine — this module composes their outputs into the report.

Usage (from VPS):
  python3 tests/certification/c29_report.py
  python3 tests/certification/c29_report.py --dispatch
  python3 tests/certification/c29_report.py --json
"""

from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

sys.path.insert(0, os.environ.get("UMH_ROOT", "/opt/OS"))

from substrate.organism.benchmarks.harness_scorer import (
    HarnessScorer,
    HTICalculator,
    MVPVerdictEngine,
    UMHMetricCalculator,
)
from substrate.organism.benchmarks.harness_superiority import (
    BenchmarkCategory,
    EvidenceClass,
    EvidenceConfidence,
    LongitudinalCheckpoint,
    MetricWithConfidence,
    MVPVerdictLevel,
    ResultStore,
    TaskRegistry,
    Track,
    TrackResult,
    WorkdayCoverage,
)

# ---------------------------------------------------------------------------
# Display constants
# ---------------------------------------------------------------------------

_CHECK = "✓"
_CROSS = "✗"

_DIMENSION_LABELS: dict[str, str] = {
    "capability": "Capability",
    "execution": "Execution",
    "cognitive_load": "Cognitive Load",
    "interruption_resistance": "Interruption Resistance",
    "continuity": "Continuity",
    "governance": "Governance",
    "awareness": "Awareness",
    "recovery": "Recovery",
    "meta_ide": "Meta IDE",
    "cost_efficiency": "Cost Efficiency",
}

_HTI_LABELS: dict[str, str] = {
    "execution_reliability": "Execution Reliability",
    "continuity": "Continuity",
    "cognitive_load": "Cognitive Load",
    "reality_correspondence": "Reality Correspondence",
    "governance": "Governance",
    "verification_coverage": "Verification Coverage",
    "recovery_capability": "Recovery Capability",
    "workspace_awareness": "Workspace Awareness",
    "meta_ide": "Meta IDE",
    "multi_machine": "Multi-Machine Awareness",
    "operator_trust": "Operator Trust",
}

# Dimensions where the thesis demands UMH strictly EXCEED legacy (not just match).
_MUST_EXCEED = {
    "cognitive_load",
    "interruption_resistance",
    "continuity",
    "governance",
    "awareness",
    "recovery",
    "meta_ide",
}

_WORKDAY_ACTIVITIES = [
    ("coding", "Coding"),
    ("debugging", "Debugging"),
    ("review", "Review"),
    ("deployment", "Deployment"),
    ("planning", "Planning"),
    ("continuity", "Continuity"),
    ("documentation", "Documentation"),
    ("approvals", "Approvals"),
    ("knowledge_retrieval", "Knowledge Retrieval"),
    ("runtime_inspection", "Runtime Inspection"),
]

# Minimum production (A+B) runs required for a verdict above PARTIALLY_TRUSTED.
_MIN_PRODUCTION_RUNS = 15


# ---------------------------------------------------------------------------
# Report dataclass
# ---------------------------------------------------------------------------


@dataclass
class C29Report:
    generated_at: str
    total_tasks: int
    total_results: int
    evidence_distribution: dict[str, int]

    # Comparative scores (10 dimensions)
    comparative_scores: dict[str, dict[str, float]]
    umh_composite: float
    legacy_composite: float

    # HTI
    hti_score: float
    hti_components: dict[str, float]

    # UMH metrics with confidence
    umh_metrics: dict[str, dict]

    # Evidence classification results
    litmus_test_passed: bool
    litmus_test_detail: str
    synthetic_only_failures: list[str]
    minimum_evidence_met: bool
    ab_only_verdict: str

    # MVP Trust Verdict
    verdict: str
    verdict_summary: str

    # Pass criteria evaluation
    pass_criteria: dict[str, dict]
    overall_pass: bool

    # Breakdowns
    category_breakdown: dict[str, dict]
    project_breakdown: dict[str, dict]

    # Workday coverage
    workday_coverage: dict[str, bool]
    coverage_score: float

    # Longitudinal checkpoints
    checkpoints: list[dict] = field(default_factory=list)

    # Gap ledger for C30
    gap_ledger: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "generated_at": self.generated_at,
            "total_tasks": self.total_tasks,
            "total_results": self.total_results,
            "evidence_distribution": self.evidence_distribution,
            "comparative_scores": self.comparative_scores,
            "umh_composite": self.umh_composite,
            "legacy_composite": self.legacy_composite,
            "hti_score": self.hti_score,
            "hti_components": self.hti_components,
            "umh_metrics": self.umh_metrics,
            "litmus_test_passed": self.litmus_test_passed,
            "litmus_test_detail": self.litmus_test_detail,
            "synthetic_only_failures": self.synthetic_only_failures,
            "minimum_evidence_met": self.minimum_evidence_met,
            "ab_only_verdict": self.ab_only_verdict,
            "verdict": self.verdict,
            "verdict_summary": self.verdict_summary,
            "pass_criteria": self.pass_criteria,
            "overall_pass": self.overall_pass,
            "category_breakdown": self.category_breakdown,
            "project_breakdown": self.project_breakdown,
            "workday_coverage": self.workday_coverage,
            "coverage_score": self.coverage_score,
            "checkpoints": self.checkpoints,
            "gap_ledger": self.gap_ledger,
        }

    # -- markdown rendering ----------------------------------------------

    def to_markdown(self) -> str:
        ed = self.evidence_distribution
        a = ed.get("A_PRODUCTION", 0)
        b = ed.get("B_CONTROLLED", 0)
        c = ed.get("C_SYNTHETIC", 0)

        lines: list[str] = [
            "# C29 — Harness Superiority Certification Report",
            "",
            f"Generated: {self.generated_at}",
            f"Tasks: {self.total_tasks} | Results: {self.total_results} | "
            f"Evidence: A={a} B={b} C={c}",
            "",
            "---",
            "",
            "## MVP Trust Verdict",
            "",
            f"**{self.verdict}**",
            "",
            self.verdict_summary,
            "",
            "---",
            "",
            "## Evidence Classification",
            "",
            "| Class | Count | Weight | Description |",
            "|-------|-------|--------|-------------|",
            f"| A — Production | {a} | 100% | Real tasks, real deployments |",
            f"| B — Controlled | {b} | 50-75% | Scripted operator tests |",
            f"| C — Synthetic | {c} | 0-25% | Mock/generated scenarios |",
            "",
            "### Hard Rules",
            "",
            f"- Litmus Test: {'PASS' if self.litmus_test_passed else 'FAIL'} — "
            f"{self.litmus_test_detail}",
            f"- Synthetic-Only Failures: "
            f"{', '.join(self.synthetic_only_failures) if self.synthetic_only_failures else 'None'}",
            f"- Minimum Production Evidence: "
            f"{'MET' if self.minimum_evidence_met else 'NOT_MET'} ({a + b} A+B runs)",
            f"- Synthetic Cannot Lift: Decisive verdict from A+B only = "
            f"{self.ab_only_verdict}",
            "",
            "---",
            "",
            "## Comparative Scores",
            "",
            "| Dimension | Weight | Legacy | UMH | Delta | Pass |",
            "|-----------|--------|--------|-----|-------|------|",
        ]

        for name, label in _DIMENSION_LABELS.items():
            d = self.comparative_scores.get(name, {})
            legacy = d.get("legacy", 0.0)
            umh = d.get("umh", 0.0)
            delta = d.get("delta", 0.0)
            weight = d.get("weight", 0.0)
            passed = self._dimension_passes(name, legacy, umh)
            lines.append(
                f"| {label} | {weight * 100:.0f}% | {legacy:.2f} | {umh:.2f} | "
                f"{delta:+.2f} | {_CHECK if passed else _CROSS} |"
            )

        lines.extend([
            "",
            f"UMH Composite: {self.umh_composite:.4f} | "
            f"Legacy Composite: {self.legacy_composite:.4f}",
            "",
            "---",
            "",
            "## HTI — Harness Trustworthiness Index",
            "",
            f"**Score: {self.hti_score:.2f}/100**",
            "",
            "| Component | Weight | Score |",
            "|-----------|--------|-------|",
        ])

        for key, weight in HTICalculator.COMPONENT_WEIGHTS.items():
            label = _HTI_LABELS.get(key, key)
            score = self.hti_components.get(key, 0.0)
            lines.append(f"| {label} | {weight * 100:.0f}% | {score:.2f} |")

        lines.extend([
            "",
            "---",
            "",
            "## UMH Metrics",
            "",
            "| Metric | Value | Target | Confidence | A | B | C | Pass |",
            "|--------|-------|--------|------------|---|---|---|------|",
        ])

        for name, m in self.umh_metrics.items():
            value = m.get("value", 0.0)
            target = m.get("target", 0.0)
            conf = m.get("confidence", "LOW")
            ca = m.get("class_a", 0)
            cb = m.get("class_b", 0)
            cc = m.get("class_c", 0)
            passed = m.get("passed", False)
            value_str, target_str = _format_metric_value(name, value, target)
            lines.append(
                f"| {name} | {value_str} | {target_str} | {conf} | "
                f"{ca} | {cb} | {cc} | {_CHECK if passed else _CROSS} |"
            )

        lines.extend([
            "",
            "---",
            "",
            "## Pass Criteria Evaluation",
            "",
            "| Criterion | Required | Actual | Pass |",
            "|-----------|----------|--------|------|",
        ])

        passed_count = 0
        for label, crit in self.pass_criteria.items():
            required = crit.get("required", "")
            actual = crit.get("actual", "")
            passed = crit.get("passed", False)
            if passed:
                passed_count += 1
            lines.append(
                f"| {label} | {required} | {actual} | "
                f"{_CHECK if passed else _CROSS} |"
            )

        lines.extend([
            "",
            f"**Overall: {'PASS' if self.overall_pass else 'FAIL'}** "
            f"({passed_count}/{len(self.pass_criteria)} criteria met)",
            "",
            "---",
            "",
            "## Category Breakdown",
            "",
            "| Category | Tasks | UMH Composite | Legacy Composite | Delta |",
            "|----------|-------|---------------|------------------|-------|",
        ])

        for cat, cb in self.category_breakdown.items():
            lines.append(
                f"| {cat} | {cb.get('task_count', 0)} | "
                f"{cb.get('umh_composite', 0.0):.2f} | "
                f"{cb.get('legacy_composite', 0.0):.2f} | "
                f"{cb.get('delta', 0.0):+.2f} |"
            )

        lines.extend([
            "",
            "## Project Breakdown",
            "",
            "| Project | Tasks | UMH Composite | Legacy Composite | Delta |",
            "|---------|-------|---------------|------------------|-------|",
        ])

        for proj, pb in self.project_breakdown.items():
            lines.append(
                f"| {proj} | {pb.get('task_count', 0)} | "
                f"{pb.get('umh_composite', 0.0):.2f} | "
                f"{pb.get('legacy_composite', 0.0):.2f} | "
                f"{pb.get('delta', 0.0):+.2f} |"
            )

        lines.extend([
            "",
            "## Workday Coverage",
            "",
            "| Activity | Covered |",
            "|----------|---------|",
        ])

        for key, label in _WORKDAY_ACTIVITIES:
            covered = self.workday_coverage.get(key, False)
            lines.append(f"| {label} | {_CHECK if covered else _CROSS} |")

        covered_n = sum(
            1 for key, _ in _WORKDAY_ACTIVITIES if self.workday_coverage.get(key, False)
        )
        lines.extend([
            "",
            f"Coverage: {covered_n}/{len(_WORKDAY_ACTIVITIES)} "
            f"({self.coverage_score * 100:.0f}%)",
            "",
            "---",
            "",
            "## Longitudinal Checkpoints",
            "",
        ])

        if self.checkpoints:
            lines.extend([
                "| # | Runs | Correct | Total | Track A Recall | Track B Recall | "
                "Avg Time (s) |",
                "|---|------|---------|-------|----------------|----------------|"
                "--------------|",
            ])
            for cp in self.checkpoints:
                lines.append(
                    f"| {cp.get('checkpoint_number', 0)} | "
                    f"{cp.get('runs_completed_at_checkpoint', 0)} | "
                    f"{cp.get('correct_answers', 0)} | "
                    f"{cp.get('total_questions', 0)} | "
                    f"{cp.get('track_a_recall_score', 0.0):.2f} | "
                    f"{cp.get('track_b_recall_score', 0.0):.2f} | "
                    f"{cp.get('time_to_answer_seconds', 0.0):.1f} |"
                )
        else:
            lines.append("No longitudinal checkpoints recorded.")

        lines.extend([
            "",
            "---",
            "",
            "## Gap Ledger for C30",
            "",
        ])

        if self.gap_ledger:
            for gap in self.gap_ledger:
                lines.append(f"- {gap}")
        else:
            lines.append("No gaps identified.")

        lines.append("")
        return "\n".join(lines)

    @staticmethod
    def _dimension_passes(name: str, legacy: float, umh: float) -> bool:
        if name in _MUST_EXCEED:
            return umh > legacy
        return umh >= legacy


def _format_metric_value(name: str, value: float, target: float) -> tuple[str, str]:
    """Render a metric value + target with the right units."""
    if name in ("TTRC",):
        return f"{value:.1f}s", f"<{target:.0f}s"
    if name in ("OER",):
        return f"{value * 100:.1f}%", f"<{target * 100:.0f}%"
    if name in ("CPR", "RCR", "GCR", "VC"):
        return f"{value * 100:.1f}%", f">{target * 100:.0f}%"
    # Score-style metrics 0-1 (CLS, IRS, DDC, OTS).
    return f"{value:.2f}", f">{target:.2f}"


# ---------------------------------------------------------------------------
# Report generator
# ---------------------------------------------------------------------------


class ReportGenerator:
    """Generates a C29Report from stored tasks + results. Pure computation."""

    def __init__(self, task_registry: TaskRegistry, result_store: ResultStore) -> None:
        self._tasks = task_registry
        self._results = result_store

    def generate(self, workday_coverage: WorkdayCoverage | None = None) -> C29Report:
        tasks = self._tasks.list_all()
        all_results = self._results.list_all()
        legacy = [r for r in all_results if r.track == Track.A_LEGACY]
        umh = [r for r in all_results if r.track == Track.B_UMH]

        scorer = HarnessScorer(legacy, umh)
        hti = HTICalculator(umh)
        metrics_calc = UMHMetricCalculator(umh, workday_coverage)
        verdict_engine = MVPVerdictEngine(scorer, hti, metrics_calc)

        comparative = scorer.compute_all()
        hti_components = hti.compute()
        hti_score = hti.hti_score()
        metrics = metrics_calc.compute_all()
        metric_report = metrics_calc.pass_report()
        verdict = verdict_engine.derive_verdict()

        # UMH metrics with confidence merged with pass/target.
        umh_metrics: dict[str, dict] = {}
        for name, m in metrics.items():
            mr = metric_report.get(name, {})
            umh_metrics[name] = {
                "value": m.value,
                "confidence": m.confidence.value
                if isinstance(m.confidence, EvidenceConfidence)
                else str(m.confidence),
                "class_a": m.class_a_count,
                "class_b": m.class_b_count,
                "class_c": m.class_c_count,
                "target": mr.get("target", UMHMetricCalculator.TARGETS.get(name, 0.0)),
                "passed": mr.get("passed", False),
            }

        # Evidence classification results.
        litmus_passed = verdict_engine._litmus_test(umh, legacy)
        ab_umh = [r for r in umh if r.evidence_class != EvidenceClass.C_SYNTHETIC]
        litmus_detail = (
            "verdict holds at PRIMARY_WORKSTATION+ with all synthetic runs removed"
            if litmus_passed
            else "verdict would drop below PRIMARY_WORKSTATION without synthetic evidence"
        )
        synthetic_only = verdict_engine._validate_no_synthetic_only(metrics)
        ab_count = len(ab_umh)
        minimum_met = ab_count >= _MIN_PRODUCTION_RUNS
        ab_only_verdict = _verdict_str(
            verdict_engine._synthetic_cannot_lift(umh, legacy)
        )

        pass_criteria, overall_pass = self._compute_pass_criteria(
            comparative, hti_score, metrics_calc, metrics, verdict
        )

        category_breakdown = self._category_breakdown(tasks, legacy, umh)
        project_breakdown = self._project_breakdown(tasks, legacy, umh)

        wc = workday_coverage or WorkdayCoverage()
        workday_dict = {k: getattr(wc, k) for k, _ in _WORKDAY_ACTIVITIES}

        checkpoints = self._load_checkpoints()

        evidence_dist = self.evidence_distribution(all_results)

        gap_ledger = self._build_gap_ledger(
            comparative, metrics, umh_metrics, wc, verdict,
            synthetic_only, minimum_met, ab_count, litmus_passed,
            evidence_dist,
        )

        return C29Report(
            generated_at=datetime.now(timezone.utc).isoformat(),
            total_tasks=len(tasks),
            total_results=len(all_results),
            evidence_distribution=evidence_dist,
            comparative_scores=comparative,
            umh_composite=scorer.composite_score("umh"),
            legacy_composite=scorer.composite_score("legacy"),
            hti_score=hti_score,
            hti_components={k: round(v, 4) for k, v in hti_components.items()},
            umh_metrics=umh_metrics,
            litmus_test_passed=litmus_passed,
            litmus_test_detail=litmus_detail,
            synthetic_only_failures=synthetic_only,
            minimum_evidence_met=minimum_met,
            ab_only_verdict=ab_only_verdict,
            verdict=_verdict_str(verdict.verdict),
            verdict_summary=verdict.evidence_summary,
            pass_criteria=pass_criteria,
            overall_pass=overall_pass,
            category_breakdown=category_breakdown,
            project_breakdown=project_breakdown,
            workday_coverage=workday_dict,
            coverage_score=wc.coverage_score,
            checkpoints=checkpoints,
            gap_ledger=gap_ledger,
        )

    # -- evidence distribution -------------------------------------------

    @staticmethod
    def evidence_distribution(results: list[TrackResult]) -> dict[str, int]:
        dist = {ec.value: 0 for ec in EvidenceClass}
        for r in results:
            dist[r.evidence_class.value] += 1
        return dist

    # -- pass criteria ----------------------------------------------------

    def _compute_pass_criteria(
        self,
        comparative: dict[str, dict[str, float]],
        hti_score: float,
        metrics_calc: UMHMetricCalculator,
        metrics: dict[str, MetricWithConfidence],
        verdict,
    ) -> tuple[dict[str, dict], bool]:
        """Evaluate every pass criterion from the spec."""
        criteria: dict[str, dict] = {}

        def comp(name: str, must_exceed: bool, label: str) -> None:
            d = comparative.get(name, {})
            legacy = d.get("legacy", 0.0)
            umh = d.get("umh", 0.0)
            passed = umh > legacy if must_exceed else umh >= legacy
            op = ">" if must_exceed else ">="
            criteria[label] = {
                "required": f"UMH {op} Legacy",
                "actual": f"{umh:.2f} vs {legacy:.2f}",
                "passed": passed,
            }

        comp("capability", False, "Capability >= Legacy")
        comp("execution", False, "Execution >= Legacy")
        comp("cognitive_load", True, "Cognitive Load > Legacy")
        comp("interruption_resistance", True, "Interruption Resistance > Legacy")
        comp("continuity", True, "Continuity > Legacy")
        comp("governance", True, "Governance > Legacy")
        comp("awareness", True, "Awareness > Legacy")
        comp("recovery", True, "Recovery > Legacy")
        comp("meta_ide", True, "Meta IDE > Legacy")
        comp("cost_efficiency", False, "Cost Efficiency >= Legacy")

        # HTI > 90
        criteria["HTI > 90"] = {
            "required": ">90",
            "actual": f"{hti_score:.2f}",
            "passed": hti_score > 90,
        }

        # UMH metrics vs targets.
        metric_labels = {
            "CPR": ("CPR > 95%", ">95%"),
            "RCR": ("RCR > 95%", ">95%"),
            "GCR": ("GCR > 90%", ">90%"),
            "VC": ("VC > 95%", ">95%"),
            "TTRC": ("TTRC < 30s", "<30s"),
            "OER": ("OER < 10%", "<10%"),
            "CLS": ("CLS > 0.80", ">0.80"),
            "IRS": ("IRS > 0.85", ">0.85"),
            "DDC": ("DDC > 0.80", ">0.80"),
            "OTS": ("OTS > 0.80", ">0.80"),
        }
        for name, (label, required) in metric_labels.items():
            m = metrics[name]
            passed = metrics_calc.metric_passes(name, m.value)
            value_str, _ = _format_metric_value(
                name, m.value, UMHMetricCalculator.TARGETS[name]
            )
            criteria[label] = {
                "required": required,
                "actual": value_str,
                "passed": passed,
            }

        # MVP Trust Verdict >= PRIMARY_WORKSTATION.
        verdict_level = _verdict_level(verdict.verdict)
        order = [
            MVPVerdictLevel.NOT_READY,
            MVPVerdictLevel.PARTIALLY_TRUSTED,
            MVPVerdictLevel.PRIMARY_WORKSTATION,
            MVPVerdictLevel.CERTIFIED_DAILY_DRIVER,
        ]
        verdict_pass = order.index(verdict_level) >= order.index(
            MVPVerdictLevel.PRIMARY_WORKSTATION
        )
        criteria["MVP Verdict >= PRIMARY_WORKSTATION"] = {
            "required": ">= PRIMARY_WORKSTATION",
            "actual": verdict_level.value,
            "passed": verdict_pass,
        }

        overall = all(c["passed"] for c in criteria.values())
        return criteria, overall

    # -- breakdowns -------------------------------------------------------

    def _category_breakdown(
        self,
        tasks,
        legacy: list[TrackResult],
        umh: list[TrackResult],
    ) -> dict[str, dict]:
        task_cat = {t.task_id: t.category for t in tasks}
        out: dict[str, dict] = {}
        for cat in BenchmarkCategory:
            task_ids = {tid for tid, c in task_cat.items() if c == cat}
            l_sub = [r for r in legacy if r.task_id in task_ids]
            u_sub = [r for r in umh if r.task_id in task_ids]
            out[cat.value] = self._sub_composite(task_ids, l_sub, u_sub)
        return out

    def _project_breakdown(
        self,
        tasks,
        legacy: list[TrackResult],
        umh: list[TrackResult],
    ) -> dict[str, dict]:
        task_proj = {t.task_id: t.project for t in tasks}
        projects = sorted({t.project for t in tasks})
        out: dict[str, dict] = {}
        for proj in projects:
            task_ids = {tid for tid, p in task_proj.items() if p == proj}
            l_sub = [r for r in legacy if r.task_id in task_ids]
            u_sub = [r for r in umh if r.task_id in task_ids]
            out[proj] = self._sub_composite(task_ids, l_sub, u_sub)
        return out

    @staticmethod
    def _sub_composite(
        task_ids: set[str],
        legacy: list[TrackResult],
        umh: list[TrackResult],
    ) -> dict:
        scorer = HarnessScorer(legacy, umh)
        umh_comp = scorer.composite_score("umh")
        legacy_comp = scorer.composite_score("legacy")
        return {
            "task_count": len(task_ids),
            "umh_composite": umh_comp,
            "legacy_composite": legacy_comp,
            "delta": round(umh_comp - legacy_comp, 4),
        }

    # -- longitudinal checkpoints ----------------------------------------

    def _load_checkpoints(self) -> list[dict]:
        path = (
            self._results._path.parent / "checkpoints.jsonl"
            if hasattr(self._results, "_path")
            else None
        )
        if path is None or not path.exists():
            return []
        checkpoints: list[dict] = []
        with path.open("r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                cp = LongitudinalCheckpoint.from_dict(json.loads(line))
                checkpoints.append(cp.to_dict())
        checkpoints.sort(key=lambda c: c.get("checkpoint_number", 0))
        return checkpoints

    # -- gap ledger -------------------------------------------------------

    def _build_gap_ledger(
        self,
        comparative: dict[str, dict[str, float]],
        metrics: dict[str, MetricWithConfidence],
        umh_metrics: dict[str, dict],
        workday: WorkdayCoverage,
        verdict,
        synthetic_only: list[str],
        minimum_met: bool,
        ab_count: int,
        litmus_passed: bool,
        evidence_distribution: dict[str, int],
    ) -> list[str]:
        """Identify gaps for C30 from failed criteria, weak evidence, and coverage."""
        gaps: list[str] = []

        # Dimensions where legacy beats UMH (or UMH fails to exceed where required).
        for name, label in _DIMENSION_LABELS.items():
            d = comparative.get(name, {})
            legacy = d.get("legacy", 0.0)
            umh = d.get("umh", 0.0)
            if name in _MUST_EXCEED and umh <= legacy:
                gaps.append(
                    f"{label}: UMH ({umh:.2f}) does not exceed Legacy ({legacy:.2f}) "
                    "— thesis dimension not yet won"
                )
            elif name not in _MUST_EXCEED and umh < legacy:
                gaps.append(
                    f"{label}: Legacy ({legacy:.2f}) beats UMH ({umh:.2f})"
                )

        # Failed UMH metric targets.
        for name, m in umh_metrics.items():
            if not m["passed"]:
                value_str, target_str = _format_metric_value(
                    name, m["value"], UMHMetricCalculator.TARGETS.get(name, 0.0)
                )
                gaps.append(
                    f"Metric {name}: {value_str} misses target {target_str}"
                )

        # Low-confidence metrics need more production evidence.
        for name, m in umh_metrics.items():
            if m["confidence"] == EvidenceConfidence.LOW.value:
                gaps.append(
                    f"Metric {name}: LOW confidence "
                    f"(A={m['class_a']} B={m['class_b']} C={m['class_c']}) "
                    "— needs more production evidence"
                )

        # Synthetic-only auto-fail metrics.
        for name in synthetic_only:
            gaps.append(
                f"Metric {name}: zero Class A/B evidence — synthetic-only auto-fail"
            )

        # Uncovered workday activities.
        for key, label in _WORKDAY_ACTIVITIES:
            if not getattr(workday, key):
                gaps.append(f"Workday coverage: {label} not exercised")

        # Insufficient production evidence.
        if not minimum_met:
            gaps.append(
                f"Insufficient production evidence: {ab_count} Class A+B runs "
                f"(need {_MIN_PRODUCTION_RUNS})"
            )

        # Litmus test.
        if not litmus_passed:
            gaps.append(
                "Litmus test: verdict would not hold without synthetic evidence "
                "— increase Class A coverage"
            )

        # Evidence distribution heavily synthetic.
        total = sum(evidence_distribution.values())
        c_count = evidence_distribution.get("C_SYNTHETIC", 0)
        if total > 0 and c_count / total > 0.5:
            gaps.append(
                f"Evidence distribution heavily synthetic "
                f"({c_count}/{total} Class C) — increase Class A coverage"
            )

        return gaps


# ---------------------------------------------------------------------------
# Verdict helpers (verdict.verdict may be a string or an enum)
# ---------------------------------------------------------------------------


def _verdict_str(verdict) -> str:
    if isinstance(verdict, MVPVerdictLevel):
        return verdict.value
    return str(verdict)


def _verdict_level(verdict) -> MVPVerdictLevel:
    if isinstance(verdict, MVPVerdictLevel):
        return verdict
    return MVPVerdictLevel(str(verdict))


# ---------------------------------------------------------------------------
# Discord dispatch
# ---------------------------------------------------------------------------


def dispatch_to_discord(report: C29Report) -> bool:
    """Send report as file attachment to Discord Founders Office."""
    from substrate.organism.report_dispatcher import Report, ReportDispatcher

    md = report.to_markdown()
    ed = report.evidence_distribution
    dispatcher = ReportDispatcher()
    r = Report(
        title=f"C29 Harness Superiority Report — {report.verdict}",
        summary=(
            f"C29 Verdict: **{report.verdict}** | "
            f"HTI: {report.hti_score}/100 | "
            f"Evidence: A={ed.get('A_PRODUCTION', 0)} "
            f"B={ed.get('B_CONTROLLED', 0)} "
            f"C={ed.get('C_SYNTHETIC', 0)}"
        ),
        body=md,
    )
    result = dispatcher.dispatch_report(r)
    return result.discord_sent


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="C29 Harness Superiority Report")
    parser.add_argument(
        "--json", action="store_true", help="Emit JSON instead of markdown"
    )
    parser.add_argument(
        "--dispatch", action="store_true", help="Dispatch report to Discord"
    )
    args = parser.parse_args()

    registry = TaskRegistry()
    store = ResultStore()
    generator = ReportGenerator(registry, store)
    report = generator.generate()

    if args.json:
        print(json.dumps(report.to_dict(), indent=2, default=str))
    else:
        print(report.to_markdown())

    if args.dispatch:
        sent = dispatch_to_discord(report)
        print(f"\nDiscord dispatch: {'SENT' if sent else 'FAILED'}")


if __name__ == "__main__":
    main()
