"""Tests for C27 gap ledger."""

from __future__ import annotations

import json
import os
import sys
import tempfile

sys.path.insert(0, "/opt/OS")

from substrate.organism.self_use.gap_ledger import (
    GapEntry,
    GapLedger,
    GapType,
)
from substrate.organism.strategic_gap_engine import GapSeverity


def test_gap_entry_roundtrip():
    gap = GapEntry(
        gap_id="gap-test-001",
        gap_type=GapType.FEATURE_MISSING,
        severity=GapSeverity.HIGH,
        surface="cockpit",
        title="Missing certification panel",
        description="No panel to view projection certs",
        projection="CreatorOS",
    )
    d = gap.to_dict()
    assert d["gap_type"] == "feature_missing"
    assert d["severity"] == "high"
    assert d["surface"] == "cockpit"

    restored = GapEntry.from_dict(d)
    assert restored.gap_type == GapType.FEATURE_MISSING
    assert restored.severity == GapSeverity.HIGH
    assert restored.title == "Missing certification panel"


def test_ledger_add_and_query():
    ledger = GapLedger()
    g1 = GapEntry(
        gap_type=GapType.COHERENCE_FAILURE,
        severity=GapSeverity.CRITICAL,
        surface="cockpit",
        title="Lost context",
    )
    g2 = GapEntry(
        gap_type=GapType.FEATURE_MISSING,
        severity=GapSeverity.MEDIUM,
        surface="stitch",
        title="No Stitch integration",
    )
    g3 = GapEntry(
        gap_type=GapType.GOVERNANCE_BYPASS,
        severity=GapSeverity.HIGH,
        surface="meta_ide",
        title="Skipped verification",
    )

    ledger.add(g1)
    ledger.add(g2)
    ledger.add(g3)

    assert len(ledger.gaps) == 3
    assert len(ledger.by_severity(GapSeverity.CRITICAL)) == 1
    assert len(ledger.by_surface("cockpit")) == 1
    assert len(ledger.by_type(GapType.FEATURE_MISSING)) == 1
    assert len(ledger.coherence_gaps()) == 2


def test_ledger_resolve():
    ledger = GapLedger()
    gap = GapEntry(title="test gap")
    ledger.add(gap)
    assert len(ledger.unresolved()) == 1

    assert ledger.resolve(gap.gap_id)
    assert len(ledger.unresolved()) == 0
    assert not ledger.resolve("nonexistent")


def test_ledger_summary():
    ledger = GapLedger()
    ledger.add(
        GapEntry(gap_type=GapType.SURFACE_UNREACHABLE, severity=GapSeverity.HIGH, surface="stitch")
    )
    ledger.add(
        GapEntry(gap_type=GapType.CONTEXT_LOST, severity=GapSeverity.CRITICAL, surface="cockpit")
    )
    summary = ledger.summary()
    assert summary["total"] == 2
    assert summary["unresolved"] == 2
    assert summary["coherence_gaps"] == 1
    assert summary["by_severity"]["high"] == 1
    assert summary["by_severity"]["critical"] == 1


def test_ledger_json_roundtrip():
    ledger = GapLedger()
    ledger.add(
        GapEntry(
            gap_type=GapType.DEPLOYMENT_FAILURE,
            severity=GapSeverity.HIGH,
            surface="cockpit",
            title="Deploy failed",
        )
    )
    ledger.add(
        GapEntry(
            gap_type=GapType.FALSE_HISTORY_ACCEPTED,
            severity=GapSeverity.CRITICAL,
            surface="meta_ide",
            title="Accepted false claim",
        )
    )

    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        path = f.name
    try:
        ledger.to_json(path)
        restored = GapLedger.from_json(path)
        assert len(restored.gaps) == 2
        assert len(restored.coherence_gaps()) == 1
    finally:
        os.unlink(path)


def test_all_gap_types_valid():
    for gt in GapType:
        gap = GapEntry(gap_type=gt, title=f"Test {gt.value}")
        d = gap.to_dict()
        restored = GapEntry.from_dict(d)
        assert restored.gap_type == gt
