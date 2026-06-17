"""Tests for W5 — Operator Migration Runtime.

Validates exit tracking, classification, priority scoring, coverage,
operationalization bridge, and migration lifecycle.
"""

from __future__ import annotations

import sys
import time
from dataclasses import dataclass
from typing import Any

import pytest

sys.path.insert(0, "/opt/OS")

from substrate.organism.operator_migration_runtime import (
    CoverageReport,
    ExitClassification,
    ExitEvent,
    ExitReason,
    Migration,
    MigrationPriority,
    MigrationStatus,
    MigrationStatusSnapshot,
    OperationalizationSuggestion,
    OperatorMigrationRuntime,
)


# ── Mocks ────────────────────────────────────────────────────────


class MockCompoundingEngine:
    def __init__(self):
        self._learnings: list[dict] = []

    def record_learning(self, source: str = "", description: str = ""):
        self._learnings.append({"source": source, "description": description})


class MockCapabilityRuntime:
    def query(self):
        return []


def _make_mig(**kwargs) -> OperatorMigrationRuntime:
    return OperatorMigrationRuntime(**kwargs)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Tests
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestExitRecording:
    def test_record_exit(self):
        mig = _make_mig()
        exit_id = mig.record_exit(description="debugging in VS Code", external_tool="vscode")
        assert exit_id.startswith("ex-")
        assert exit_id in mig._exits

    def test_record_return(self):
        mig = _make_mig()
        exit_id = mig.record_exit(description="checking email")
        ok = mig.record_return(exit_id)
        assert ok is True
        event = mig._exits[exit_id]
        assert event.returned_at > 0
        assert event.duration_seconds >= 0

    def test_return_nonexistent(self):
        mig = _make_mig()
        ok = mig.record_return("nonexistent")
        assert ok is False


class TestClassification:
    def test_tooling_gap(self):
        mig = _make_mig()
        c = mig.classify_exit("had to use vscode for debugging")
        assert c.reason == ExitReason.TOOLING_GAP
        assert c.confidence > 0

    def test_capability_gap(self):
        mig = _make_mig()
        c = mig.classify_exit("can't do this operation, missing feature")
        assert c.reason == ExitReason.CAPABILITY_GAP

    def test_preference(self):
        mig = _make_mig()
        c = mig.classify_exit("prefer to use the familiar tool")
        assert c.reason == ExitReason.PREFERENCE

    def test_external(self):
        mig = _make_mig()
        c = mig.classify_exit("went to a client meeting")
        assert c.reason == ExitReason.EXTERNAL

    def test_unknown_fallback(self):
        mig = _make_mig()
        c = mig.classify_exit("just stepped away")
        assert c.reason == ExitReason.UNKNOWN
        assert c.confidence == 0.3

    def test_classification_to_dict(self):
        mig = _make_mig()
        c = mig.classify_exit("opened vscode")
        d = c.to_dict()
        assert "reason" in d
        assert "confidence" in d


class TestMigrationPriorities:
    def test_priority_scoring(self):
        mig = _make_mig()
        mig.record_exit("debugging in vscode", "vscode")
        mig.record_exit("debugging in vscode again", "vscode")
        mig.record_exit("checking email", "gmail")
        # Simulate returns with duration
        for eid, event in mig._exits.items():
            event.returned_at = event.exited_at + 120
            event.duration_seconds = 120

        priorities = mig.migration_priorities()
        assert len(priorities) == 2
        assert priorities[0].pattern == "vscode"
        assert priorities[0].frequency == 2

    def test_empty_priorities(self):
        mig = _make_mig()
        assert mig.migration_priorities() == []

    def test_priority_to_dict(self):
        mig = _make_mig()
        mig.record_exit("vscode", "vscode")
        p = mig.migration_priorities()[0]
        d = p.to_dict()
        assert "priority_score" in d
        assert "feasibility_score" in d


class TestFeasibility:
    def test_external_low_feasibility(self):
        mig = _make_mig()
        score = mig._estimate_feasibility("meeting", ExitReason.EXTERNAL)
        assert score == 0.1

    def test_tooling_gap_higher(self):
        mig = _make_mig()
        score = mig._estimate_feasibility("vscode", ExitReason.TOOLING_GAP)
        assert score == 0.7

    def test_capability_gap_with_runtime(self):
        mig = _make_mig(capability_runtime=MockCapabilityRuntime())
        score = mig._estimate_feasibility("feature", ExitReason.CAPABILITY_GAP)
        assert score == 0.8


class TestCoverage:
    def test_full_coverage_no_exits(self):
        mig = _make_mig()
        report = mig.coverage_report()
        assert report.total_exits == 0
        assert report.coverage_pct > 0.9

    def test_coverage_with_exits(self):
        mig = _make_mig()
        mig._session_start = time.time() - 1000
        exit_id = mig.record_exit("vscode", "vscode")
        mig._exits[exit_id].duration_seconds = 500
        report = mig.coverage_report()
        assert 0 < report.coverage_pct < 1.0
        assert report.total_exits == 1

    def test_top_exit_tools(self):
        mig = _make_mig()
        mig.record_exit("vscode work", "vscode")
        mig.record_exit("vscode again", "vscode")
        mig.record_exit("gmail check", "gmail")
        report = mig.coverage_report()
        assert "vscode" in report.top_exit_tools

    def test_coverage_to_dict(self):
        mig = _make_mig()
        d = mig.coverage_report().to_dict()
        assert "coverage_pct" in d
        assert "trend" in d


class TestOperationalizationBridge:
    def test_suggest_for_tooling_gap(self):
        mig = _make_mig()
        mig.record_exit("had to use vscode for editing", "vscode")
        suggestion = mig.suggest_operationalization("vscode")
        assert suggestion is not None
        assert suggestion.suggested_form == "automation"

    def test_suggest_for_capability_gap(self):
        mig = _make_mig()
        mig.record_exit("can't do advanced search, missing feature", "search-tool")
        suggestion = mig.suggest_operationalization("search-tool")
        assert suggestion is not None
        assert suggestion.suggested_form == "workflow"

    def test_suggest_no_match(self):
        mig = _make_mig()
        suggestion = mig.suggest_operationalization("nonexistent")
        assert suggestion is None

    def test_suggestion_to_dict(self):
        mig = _make_mig()
        mig.record_exit("vscode debugging", "vscode")
        s = mig.suggest_operationalization("vscode")
        d = s.to_dict()
        assert "suggested_form" in d
        assert "rationale" in d


class TestMigrationLifecycle:
    def test_propose(self):
        mig = _make_mig()
        m = mig.propose_migration("vscode", "vscode")
        assert m.migration_id.startswith("mg-")
        assert m.status == MigrationStatus.PROPOSED

    def test_start(self):
        mig = _make_mig()
        m = mig.propose_migration("vscode")
        ok = mig.start_migration(m.migration_id)
        assert ok is True
        assert mig._migrations[m.migration_id].status == MigrationStatus.IN_PROGRESS

    def test_complete_success(self):
        mig = _make_mig()
        m = mig.propose_migration("vscode")
        ok = mig.complete_migration(m.migration_id, success=True)
        assert ok is True
        assert mig._migrations[m.migration_id].status == MigrationStatus.COMPLETED

    def test_complete_failure(self):
        mig = _make_mig()
        m = mig.propose_migration("vscode")
        mig.complete_migration(m.migration_id, success=False)
        assert mig._migrations[m.migration_id].status == MigrationStatus.ABANDONED

    def test_complete_nonexistent(self):
        mig = _make_mig()
        ok = mig.complete_migration("nonexistent")
        assert ok is False

    def test_active_migrations(self):
        mig = _make_mig()
        mig.propose_migration("vscode")
        mig.propose_migration("gmail")
        m3 = mig.propose_migration("done")
        mig.complete_migration(m3.migration_id)
        active = mig.active_migrations()
        assert len(active) == 2

    def test_compounding_feedback(self):
        engine = MockCompoundingEngine()
        mig = _make_mig(compounding_engine=engine)
        m = mig.propose_migration("vscode")
        mig.complete_migration(m.migration_id, success=True)
        assert len(engine._learnings) == 1
        assert "vscode" in engine._learnings[0]["description"]


class TestMigrationStatus:
    def test_status_snapshot(self):
        mig = _make_mig()
        s = mig.migration_status()
        d = s.to_dict()
        assert "total_exits" in d
        assert "coverage_pct" in d
        assert "active_migrations" in d

    def test_status_counts(self):
        mig = _make_mig()
        mig.record_exit("vscode", "vscode")
        mig.propose_migration("vscode")
        s = mig.migration_status()
        assert s.total_exits == 1
        assert s.active_migrations == 1


class TestFullLoop:
    """Acceptance: record exit → classify → return → prioritize → propose → complete."""

    def test_full_migration_loop(self):
        engine = MockCompoundingEngine()
        mig = _make_mig(compounding_engine=engine)
        mig._session_start = time.time() - 1000

        exit_id = mig.record_exit("debugging in vscode editor", "vscode")
        assert exit_id

        event = mig._exits[exit_id]
        assert event.reason == ExitReason.TOOLING_GAP

        mig.record_return(exit_id)
        assert mig._exits[exit_id].duration_seconds >= 0

        priorities = mig.migration_priorities()
        assert len(priorities) >= 1
        assert priorities[0].feasibility_score > 0

        report = mig.coverage_report()
        assert 0 <= report.coverage_pct <= 1.0

        m = mig.propose_migration("vscode", "vscode")
        mig.start_migration(m.migration_id)
        mig.complete_migration(m.migration_id, success=True)

        assert mig._migrations[m.migration_id].status == MigrationStatus.COMPLETED
        assert len(engine._learnings) == 1
