"""Tests for C27 certification report."""

from __future__ import annotations

import sys

sys.path.insert(0, "/opt/OS")

from substrate.organism.self_use.certification_report import (
    CertificationGate,
    CertificationReport,
    CoherenceMetrics,
    GateResult,
    ReportBuilder,
)


def test_coherence_metrics_pass():
    metrics = CoherenceMetrics(
        continuity_preservation=0.96,
        context_recovery=0.92,
        governance_challenge_rate=0.85,
        reality_correction_rate=0.95,
        false_history_accepted=0,
        lost_commitments=0,
        priority_inversions=0,
    )
    assert metrics.passes


def test_coherence_metrics_fail_threshold():
    metrics = CoherenceMetrics(
        continuity_preservation=0.90,
        context_recovery=0.92,
        governance_challenge_rate=0.85,
        reality_correction_rate=0.95,
    )
    assert not metrics.passes


def test_coherence_metrics_fail_zero_tolerance():
    metrics = CoherenceMetrics(
        continuity_preservation=1.0,
        context_recovery=1.0,
        governance_challenge_rate=1.0,
        reality_correction_rate=1.0,
        false_history_accepted=1,
    )
    assert not metrics.passes


def test_coherence_metrics_fail_lost_commitments():
    metrics = CoherenceMetrics(
        continuity_preservation=1.0,
        context_recovery=1.0,
        governance_challenge_rate=1.0,
        reality_correction_rate=1.0,
        lost_commitments=1,
    )
    assert not metrics.passes


def test_coherence_override():
    report = ReportBuilder()
    report.set_surface_gate(7, 7, 0)
    report.set_production_gate(0.95, 5, 2)
    report.set_meta_ide_gate(7, 7, False)
    report.set_coherence_gate(
        CoherenceMetrics(
            continuity_preservation=0.80,
            context_recovery=0.70,
            governance_challenge_rate=0.50,
            reality_correction_rate=0.60,
        )
    )
    result = report.build()
    assert not result.overall_pass
    assert "COHERENCE OVERRIDE" in result.override_reason


def test_all_gates_pass():
    report = ReportBuilder()
    report.set_surface_gate(7, 7, 0)
    report.set_production_gate(0.90, 3, 1)
    report.set_meta_ide_gate(7, 7, False)
    report.set_coherence_gate(
        CoherenceMetrics(
            continuity_preservation=0.96,
            context_recovery=0.92,
            governance_challenge_rate=0.85,
            reality_correction_rate=0.95,
        )
    )
    result = report.build()
    assert result.overall_pass


def test_production_gate_fail():
    report = ReportBuilder()
    report.set_surface_gate(7, 7, 0)
    report.set_production_gate(0.70, 0, 0)
    report.set_meta_ide_gate(7, 7, False)
    report.set_coherence_gate(
        CoherenceMetrics(
            continuity_preservation=0.96,
            context_recovery=0.92,
            governance_challenge_rate=0.85,
            reality_correction_rate=0.95,
        )
    )
    result = report.build()
    assert not result.overall_pass
    assert "production" in result.override_reason


def test_meta_ide_critical_path_broken():
    report = ReportBuilder()
    report.set_surface_gate(7, 7, 0)
    report.set_production_gate(0.90, 3, 1)
    report.set_meta_ide_gate(7, 7, True)
    report.set_coherence_gate(
        CoherenceMetrics(
            continuity_preservation=0.96,
            context_recovery=0.92,
            governance_challenge_rate=0.85,
            reality_correction_rate=0.95,
        )
    )
    result = report.build()
    assert not result.overall_pass


def test_report_to_markdown():
    report = ReportBuilder()
    report.set_surface_gate(5, 7, 2)
    report.set_production_gate(0.88, 2, 1)
    report.set_meta_ide_gate(6, 7, False)
    report.set_coherence_gate(
        CoherenceMetrics(
            continuity_preservation=0.97,
            context_recovery=0.93,
            governance_challenge_rate=0.90,
            reality_correction_rate=0.96,
        )
    )
    result = report.build()
    md = result.to_markdown()
    assert "C27 Certification Report" in md
    assert "surface" in md.lower()
    assert "coherence" in md.lower()


def test_report_to_dict():
    report = ReportBuilder()
    report.set_surface_gate(7, 7, 0)
    report.set_production_gate(0.90, 3, 1)
    report.set_meta_ide_gate(7, 7, False)
    report.set_coherence_gate(
        CoherenceMetrics(
            continuity_preservation=0.96,
            context_recovery=0.92,
            governance_challenge_rate=0.85,
            reality_correction_rate=0.95,
        )
    )
    result = report.build()
    d = result.to_dict()
    assert "gates" in d
    assert len(d["gates"]) == 4
    assert "coherence" in d


def test_gate_result_roundtrip():
    gate = GateResult(
        gate=CertificationGate.SURFACE,
        passed=True,
        score=0.85,
        detail="5/7 exercised",
    )
    d = gate.to_dict()
    assert d["gate"] == "surface"
    assert d["passed"] is True
