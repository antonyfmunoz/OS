"""Tests for W0-001 CU document reader hardening plan."""

import sys
import os

sys.path.insert(0, os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS")

from runtime.substrate.cu_document_reader_hardening_plan import (
    CUHardeningPlan,
    ForegroundFixOption,
    HardeningPhase,
    HardeningPhaseSpec,
    PhaseStatus,
    build_hardening_plan,
    evaluate_foreground_fix_options,
)
from runtime.substrate.extraction_backend_contracts import ExtractionCapability


def test_build_hardening_plan_has_5_phases():
    """Hardening plan has 5 sequential phases."""
    plan = build_hardening_plan()
    assert len(plan.phases) == 5
    phase_ids = [p.phase for p in plan.phases]
    assert HardeningPhase.FOREGROUND_OWNERSHIP in phase_ids
    assert HardeningPhase.CLIPBOARD_EXTRACTION in phase_ids
    assert HardeningPhase.TAB_NAVIGATION in phase_ids
    assert HardeningPhase.SCROLL_AND_READ in phase_ids
    assert HardeningPhase.PARITY_VALIDATION in phase_ids


def test_phase_a_has_no_prerequisites():
    """Phase A (foreground) has no prerequisites."""
    plan = build_hardening_plan()
    phase_a = plan.phases[0]
    assert phase_a.phase == HardeningPhase.FOREGROUND_OWNERSHIP
    assert phase_a.prerequisites == []


def test_phase_e_requires_all_prior():
    """Phase E (parity validation) requires B, C, and D."""
    plan = build_hardening_plan()
    phase_e = next(p for p in plan.phases if p.phase == HardeningPhase.PARITY_VALIDATION)
    assert HardeningPhase.CLIPBOARD_EXTRACTION in phase_e.prerequisites
    assert HardeningPhase.TAB_NAVIGATION in phase_e.prerequisites
    assert HardeningPhase.SCROLL_AND_READ in phase_e.prerequisites


def test_foreground_unlocks_clipboard_and_scrolling():
    """Phase A unlocks clipboard capture and page scrolling capabilities."""
    plan = build_hardening_plan()
    phase_a = plan.phases[0]
    assert ExtractionCapability.CLIPBOARD_CAPTURE in phase_a.unlocks_capabilities
    assert ExtractionCapability.PAGE_SCROLLING in phase_a.unlocks_capabilities


def test_clipboard_phase_unlocks_document_body():
    """Phase B unlocks document body extraction."""
    plan = build_hardening_plan()
    phase_b = next(p for p in plan.phases if p.phase == HardeningPhase.CLIPBOARD_EXTRACTION)
    assert ExtractionCapability.DOCUMENT_BODY in phase_b.unlocks_capabilities


def test_get_next_actionable_returns_phase_a():
    """Next actionable phase is A when all are NOT_STARTED."""
    plan = build_hardening_plan()
    next_phase = plan.get_next_actionable_phase()
    assert next_phase is not None
    assert next_phase.phase == HardeningPhase.FOREGROUND_OWNERSHIP


def test_get_next_actionable_after_phase_a_complete():
    """After Phase A is complete, B and C both become actionable."""
    plan = build_hardening_plan()
    plan.phases[0].status = PhaseStatus.COMPLETE
    next_phase = plan.get_next_actionable_phase()
    assert next_phase is not None
    assert next_phase.phase in (HardeningPhase.CLIPBOARD_EXTRACTION, HardeningPhase.TAB_NAVIGATION)


def test_foreground_fix_options_include_recommended():
    """Foreground fix options include at least one recommended option."""
    options = evaluate_foreground_fix_options()
    assert len(options) == 6
    recommended = [o for o in options if o["recommended"]]
    assert len(recommended) >= 1
    assert recommended[0]["option"] == ForegroundFixOption.SAME_TASK_LAUNCH.value
    assert recommended[0]["install_required"] is False


def test_plan_serialization():
    """Hardening plan serializes to dict correctly."""
    plan = build_hardening_plan()
    d = plan.to_dict()
    assert d["current_phase"] == "phase_a_foreground_ownership"
    assert d["overall_status"] == "not_started"
    assert len(d["phases"]) == 5


def test_all_phases_have_exit_criteria():
    """Every phase has at least one exit criterion."""
    plan = build_hardening_plan()
    for phase in plan.phases:
        assert len(phase.exit_criteria) > 0, f"{phase.phase.value} missing exit criteria"
