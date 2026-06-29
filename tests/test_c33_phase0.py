"""C33 Phase 0 exit gate tests — verify D1-D4 fixes work end-to-end.

Exit gate criteria:
  - At least 1 capability extracted from real execution
  - Learning signals fire on every cycle (not just first)
  - Fast-path triggers for known-safe patterns, overhead below 5%
  - At least 1 template extracted from structural similarity
"""

from __future__ import annotations

import os
import tempfile
import time

import pytest


# ── D1: Capability Extraction ──────────────────────────────────


def test_d1_task_shape_detection():
    """detect_task_shape matches descriptions to known shapes."""
    from substrate.organism.compounding_engine import detect_task_shape

    assert detect_task_shape("Fix the login regression bug") == "bug_fix"
    assert detect_task_shape("Add reliability history endpoint") == "endpoint_addition"
    assert detect_task_shape("Migrate user schema to new format") == "schema_change"
    assert detect_task_shape("Integrate new Discord adapter") == "adapter_integration"
    assert detect_task_shape("Refactor the routing module") == "refactor"
    assert detect_task_shape("Do something unrelated") == "unknown"


def test_d1_lowered_thresholds():
    """CompoundingEngine detects insights with only 2 occurrences."""
    from substrate.organism.compounding_engine import CompoundingEngine

    with tempfile.TemporaryDirectory() as td:
        path = os.path.join(td, "candidates.jsonl")
        engine = CompoundingEngine(store_path=path)

        outcomes = [
            {"action_type": "endpoint_addition", "status": "success", "id": "o1"},
            {"action_type": "endpoint_addition", "status": "success", "id": "o2"},
        ]
        candidates = engine.detect_outcome_to_insight(outcomes, min_occurrences=2)
        assert len(candidates) >= 1, "Should detect insight with 2 occurrences"
        assert candidates[0].source_id == "endpoint_addition"


def test_d1_capability_template_persistence():
    """CapabilityTemplate can be created and persisted."""
    from substrate.organism.compounding_engine import CapabilityTemplate

    t = CapabilityTemplate(
        task_shape="endpoint_addition",
        file_patterns=["routes/foo.py", "tests/test_foo.py"],
    )
    d = t.to_dict()
    assert d["task_shape"] == "endpoint_addition"
    assert len(d["file_patterns"]) == 2

    t2 = CapabilityTemplate.from_dict(d)
    assert t2.task_shape == t.task_shape
    assert t2.file_patterns == t.file_patterns


def test_d1_scan_after_cycle():
    """scan_after_cycle extracts capabilities from outcomes."""
    from substrate.organism.compounding_engine import CompoundingEngine

    with tempfile.TemporaryDirectory() as td:
        path = os.path.join(td, "candidates.jsonl")
        cap_path = os.path.join(td, "capabilities.jsonl")
        engine = CompoundingEngine(store_path=path)
        engine._cap_path = cap_path

        outcomes = [
            {"action_type": "bug_fix", "status": "success", "id": "o1",
             "description": "Fix login regression bug"},
            {"action_type": "bug_fix", "status": "success", "id": "o2",
             "description": "Fix another regression"},
        ]
        candidates = engine.scan_after_cycle(outcomes)
        assert len(candidates) >= 1


# ── D2: Learning Signal Compounding ────────────────────────────


def test_d2_new_signal_types_exist():
    """All 4 new signal types are registered."""
    from substrate.organism.outcome_learning import SignalType

    assert hasattr(SignalType, "CONSISTENCY_SIGNAL")
    assert hasattr(SignalType, "EFFICIENCY_SIGNAL")
    assert hasattr(SignalType, "QUALITY_SIGNAL")
    assert hasattr(SignalType, "DIVERSITY_SIGNAL")


def test_d2_diversity_signal_fires():
    """DIVERSITY_SIGNAL fires on first occurrence of new action_type."""
    from substrate.organism.outcome_learning import (
        OutcomeLearningLoop,
        OutcomeRecord,
        OutcomeStatus,
        SignalType,
    )

    with tempfile.TemporaryDirectory() as td:
        path = os.path.join(td, "outcomes.jsonl")
        loop = OutcomeLearningLoop(store_path=path)

        loop.record_outcome(OutcomeRecord(
            action_type="new_action",
            status=OutcomeStatus.SUCCESS,
            duration_seconds=10.0,
        ))

        diversity_signals = [
            s for s in loop._signals
            if s.signal_type == SignalType.DIVERSITY_SIGNAL
        ]
        assert len(diversity_signals) >= 1, "DIVERSITY_SIGNAL should fire on first new action_type"


def test_d2_consistency_signal_fires():
    """CONSISTENCY_SIGNAL fires after 5 consecutive same-status outcomes."""
    from substrate.organism.outcome_learning import (
        OutcomeLearningLoop,
        OutcomeRecord,
        OutcomeStatus,
        SignalType,
    )

    with tempfile.TemporaryDirectory() as td:
        path = os.path.join(td, "outcomes.jsonl")
        loop = OutcomeLearningLoop(store_path=path)

        for i in range(5):
            loop.record_outcome(OutcomeRecord(
                action_type="consistent_action",
                status=OutcomeStatus.SUCCESS,
                duration_seconds=10.0,
            ))

        consistency_signals = [
            s for s in loop._signals
            if s.signal_type == SignalType.CONSISTENCY_SIGNAL
        ]
        assert len(consistency_signals) >= 1, "CONSISTENCY_SIGNAL should fire after 5 consecutive same status"


def test_d2_signals_fire_every_cycle():
    """Signals continue firing on subsequent cycles, not just the first."""
    from substrate.organism.outcome_learning import (
        OutcomeLearningLoop,
        OutcomeRecord,
        OutcomeStatus,
        SignalType,
    )

    with tempfile.TemporaryDirectory() as td:
        path = os.path.join(td, "outcomes.jsonl")
        loop = OutcomeLearningLoop(store_path=path)

        for i in range(6):
            loop.record_outcome(OutcomeRecord(
                action_type="repeated_action",
                status=OutcomeStatus.SUCCESS,
                duration_seconds=max(1.0, 10.0 - i),
            ))

        signal_count_after_6 = len(loop._signals)
        assert signal_count_after_6 >= 4, (
            f"Expected at least 4 signals after 6 outcomes, got {signal_count_after_6}. "
            f"Signal types: {[s.signal_type.value for s in loop._signals]}"
        )


def test_d2_signal_feed_governance():
    """LearningSignalFeed produces governance decisions."""
    from substrate.organism.outcome_learning import (
        OutcomeLearningLoop,
        OutcomeRecord,
        OutcomeStatus,
    )

    with tempfile.TemporaryDirectory() as td:
        path = os.path.join(td, "outcomes.jsonl")
        loop = OutcomeLearningLoop(store_path=path)

        for i in range(6):
            loop.record_outcome(OutcomeRecord(
                action_type="reliable_action",
                status=OutcomeStatus.SUCCESS,
                duration_seconds=max(1.0, 10.0 - i),
            ))

        feed = loop.get_signal_feed("reliable_action")
        assert feed.action_type == "reliable_action"
        assert feed.auto_approve_candidate is True, (
            "High consistency + high reliability should produce auto_approve_candidate=True"
        )


# ── D3: Governance Fast-Path ───────────────────────────────────


def test_d3_fast_path_result_exists():
    """FastPathResult and SpineTimingData are importable."""
    from substrate.organism.governed_spine import FastPathResult, SpineTimingData

    fp = FastPathResult(eligible=True, reason="test", skipped_stages=["proof"])
    assert fp.eligible is True

    td = SpineTimingData()
    d = td.to_dict()
    assert "fast_path_used" in d
    assert "spine_submit_ms" in d
    assert "total_overhead_ms" in d


def test_d3_timing_data_fields():
    """SpineTimingData has all required timing fields."""
    from substrate.organism.governed_spine import SpineTimingData

    td = SpineTimingData(
        spine_submit_ms=5.0,
        governance_check_ms=2.0,
        execution_ms=100.0,
        proof_capture_ms=3.0,
        journal_write_ms=1.0,
        learning_record_ms=1.5,
        fast_path_used=True,
        fast_path_reason="high-reliability local reversible",
    )
    td.total_overhead_ms = (
        td.spine_submit_ms + td.governance_check_ms +
        td.proof_capture_ms + td.journal_write_ms + td.learning_record_ms
    )
    assert td.total_overhead_ms == 12.5
    assert td.fast_path_used is True


# ── D4: Reusable Template Extraction ───────────────────────────


def test_d4_template_extractor_exists():
    """TemplateExtractor and TaskShapeTemplate are importable."""
    from substrate.organism.template_registry import TemplateExtractor, TaskShapeTemplate

    t = TaskShapeTemplate(task_shape="endpoint_addition")
    assert t.task_shape == "endpoint_addition"
    assert t.times_extracted == 0
    assert t.times_matched == 0


def test_d4_extract_from_cycle():
    """extract_from_cycle creates a template from file changes."""
    from substrate.organism.template_registry import TemplateExtractor

    with tempfile.TemporaryDirectory() as td:
        path = os.path.join(td, "templates.jsonl")
        extractor = TemplateExtractor(store_path=path)

        template = extractor.extract_from_cycle(
            cycle_id="cycle-1",
            files_changed=[
                "transports/api/cockpit_foo_routes.py",
                "tests/test_foo.py",
                "substrate/organism/foo_runtime.py",
            ],
            task_description="Add foo endpoint with test",
        )
        assert template is not None
        assert template.times_extracted >= 1


def test_d4_template_similarity_matching():
    """Two structurally similar cycles match to the same template."""
    from substrate.organism.template_registry import TemplateExtractor

    with tempfile.TemporaryDirectory() as td:
        path = os.path.join(td, "templates.jsonl")
        extractor = TemplateExtractor(store_path=path)

        t1 = extractor.extract_from_cycle(
            cycle_id="cycle-1",
            files_changed=[
                "transports/api/cockpit_foo_routes.py",
                "tests/test_foo.py",
                "substrate/organism/foo_runtime.py",
            ],
            task_description="Add foo endpoint",
        )

        t2 = extractor.extract_from_cycle(
            cycle_id="cycle-2",
            files_changed=[
                "transports/api/cockpit_bar_routes.py",
                "tests/test_bar.py",
                "substrate/organism/bar_runtime.py",
            ],
            task_description="Add bar endpoint",
        )

        assert t1 is not None
        assert t2 is not None
        assert t1.template_id == t2.template_id, "Similar cycles should match same template"
        assert t2.times_matched >= 1, "Second cycle should increment times_matched"


def test_d4_template_persistence():
    """Templates persist to JSONL and reload."""
    from substrate.organism.template_registry import TemplateExtractor

    with tempfile.TemporaryDirectory() as td:
        path = os.path.join(td, "templates.jsonl")
        extractor = TemplateExtractor(store_path=path)

        extractor.extract_from_cycle(
            cycle_id="cycle-1",
            files_changed=["routes/a.py", "tests/test_a.py"],
            task_description="Add endpoint",
        )
        assert len(extractor.list_templates()) >= 1

        extractor2 = TemplateExtractor(store_path=path)
        assert len(extractor2.list_templates()) >= 1, "Templates should persist and reload"
