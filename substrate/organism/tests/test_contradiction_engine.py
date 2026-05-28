"""Tests for contradiction engine."""

from __future__ import annotations

import json
import os
import sys
import tempfile

sys.path.insert(0, os.environ.get("UMH_ROOT", "/opt/OS"))

import pytest

from substrate.organism.contradiction_engine import (
    Claim,
    Contradiction,
    ContradictionEngine,
    ContradictionReport,
    ContradictionSeverity,
    ContradictionType,
    Observation,
    detect_contradictions,
    persist_contradictions,
)


class TestClaim:
    def test_creation(self):
        c = Claim(source="audit", statement="Route /api/test exists", entity_id="route_test")
        assert c.source == "audit"
        assert c.entity_id == "route_test"

    def test_to_dict(self):
        c = Claim(source="code", statement="Module exists")
        d = c.to_dict()
        assert d["source"] == "code"
        assert "statement" in d


class TestObservation:
    def test_creation(self):
        o = Observation(source="filesystem", finding="File not found")
        assert o.source == "filesystem"
        assert o.observed_at > 0

    def test_to_dict(self):
        o = Observation(source="http", finding="404 returned")
        d = o.to_dict()
        assert d["source"] == "http"


class TestContradiction:
    def test_creation(self):
        c = Contradiction(
            contradiction_type=ContradictionType.DECLARED_MISSING_OBSERVED,
            severity=ContradictionSeverity.HIGH,
            claim=Claim(source="audit", statement="exists"),
            observation=Observation(source="fs", finding="missing"),
            confidence=0.9,
            evidence="File not on disk",
            recommended_fix="Create the file",
        )
        assert c.severity == ContradictionSeverity.HIGH
        assert c.confidence == 0.9
        assert c.id

    def test_to_dict(self):
        c = Contradiction(
            contradiction_type=ContradictionType.STALE_DEPLOYMENT,
            severity=ContradictionSeverity.MEDIUM,
            confidence=0.7,
            evidence="Hash mismatch",
        )
        d = c.to_dict()
        assert d["type"] == "stale_deployment"
        assert d["severity"] == "medium"
        assert d["confidence"] == 0.7


class TestContradictionReport:
    def test_add(self):
        report = ContradictionReport()
        report.add(Contradiction(
            contradiction_type=ContradictionType.WIRING_MISMATCH,
            severity=ContradictionSeverity.LOW,
        ))
        assert len(report.contradictions) == 1

    def test_by_severity(self):
        report = ContradictionReport()
        report.add(Contradiction(severity=ContradictionSeverity.CRITICAL))
        report.add(Contradiction(severity=ContradictionSeverity.LOW))
        report.add(Contradiction(severity=ContradictionSeverity.CRITICAL))
        crits = report.by_severity(ContradictionSeverity.CRITICAL)
        assert len(crits) == 2

    def test_by_type(self):
        report = ContradictionReport()
        report.add(Contradiction(contradiction_type=ContradictionType.ROUTE_MISMATCH))
        report.add(Contradiction(contradiction_type=ContradictionType.DATA_INTEGRITY))
        report.add(Contradiction(contradiction_type=ContradictionType.ROUTE_MISMATCH))
        routes = report.by_type(ContradictionType.ROUTE_MISMATCH)
        assert len(routes) == 2

    def test_summary(self):
        report = ContradictionReport()
        report.add(Contradiction(
            contradiction_type=ContradictionType.WIRING_MISMATCH,
            severity=ContradictionSeverity.HIGH,
        ))
        report.checks_performed = 3
        s = report.summary()
        assert s["total"] == 1
        assert s["checks_performed"] == 3
        assert "by_severity" in s

    def test_to_dict_serialization(self):
        report = ContradictionReport()
        report.add(Contradiction(
            contradiction_type=ContradictionType.CAPABILITY_GAP,
            severity=ContradictionSeverity.MEDIUM,
            claim=Claim(source="test", statement="cap exists"),
            observation=Observation(source="test", finding="cap missing"),
            confidence=0.8,
        ))
        d = report.to_dict()
        serialized = json.dumps(d, default=str)
        parsed = json.loads(serialized)
        assert "summary" in parsed
        assert "contradictions" in parsed
        assert len(parsed["contradictions"]) == 1


class TestConfidenceScoring:
    def test_high_confidence_for_missing_files(self):
        c = Contradiction(
            contradiction_type=ContradictionType.DECLARED_MISSING_OBSERVED,
            severity=ContradictionSeverity.HIGH,
            confidence=0.95,
        )
        assert c.confidence >= 0.9

    def test_low_confidence_for_routing(self):
        c = Contradiction(
            contradiction_type=ContradictionType.ROUTE_MISMATCH,
            severity=ContradictionSeverity.INFO,
            confidence=0.4,
        )
        assert c.confidence < 0.5


class TestContradictionEngine:
    def test_engine_runs(self):
        engine = ContradictionEngine()
        report = engine.run()
        assert report.checks_performed > 0

    def test_convenience_function(self):
        report = detect_contradictions()
        assert isinstance(report, ContradictionReport)
        assert report.checks_performed > 0

    def test_with_explicit_models(self):
        from substrate.organism.world_model import extract_world_model
        from substrate.organism.dependency_graph import build_dependency_graph
        wm = extract_world_model()
        dg = build_dependency_graph(wm)
        engine = ContradictionEngine(world_model=wm, dependency_graph=dg)
        report = engine.run()
        assert report.checks_performed >= 7


class TestPersistence:
    def test_persist_contradictions(self):
        report = ContradictionReport()
        report.add(Contradiction(
            contradiction_type=ContradictionType.DATA_INTEGRITY,
            severity=ContradictionSeverity.LOW,
            evidence="test",
        ))
        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
            path = f.name
        try:
            result = persist_contradictions(report, path=path)
            assert os.path.isfile(result)
            with open(result) as f:
                data = json.loads(f.readline())
            assert "contradictions" in data
        finally:
            os.unlink(path)
