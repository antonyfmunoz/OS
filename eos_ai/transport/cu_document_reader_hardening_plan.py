"""
Computer Use document reader hardening plan for W0-001.

Defines the phased approach to bring the CU backend to parity with API
for Google Docs extraction. Each phase has prerequisites, steps, and
exit criteria.

Current blocker: Windows foreground ownership prevents SendKeys/clipboard.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from eos_ai.substrate.extraction_backend_contracts import (
    ExtractionBackendType,
    ExtractionCapability,
    ExtractionCoverageStatus,
    ExtractionFailureReason,
)


class HardeningPhase(str, Enum):
    FOREGROUND_OWNERSHIP = "phase_a_foreground_ownership"
    CLIPBOARD_EXTRACTION = "phase_b_clipboard_extraction"
    TAB_NAVIGATION = "phase_c_tab_navigation"
    SCROLL_AND_READ = "phase_d_scroll_and_read"
    PARITY_VALIDATION = "phase_e_parity_validation"


class PhaseStatus(str, Enum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    COMPLETE = "complete"
    SKIPPED = "skipped"


class ForegroundFixOption(str, Enum):
    SAME_TASK_LAUNCH = "a1_same_task_launch"
    UIAUTOMATION_SETFOCUS = "a2_uiautomation_setfocus"
    ATTACH_THREAD_INPUT = "a3_attach_thread_input"
    AUTOHOTKEY = "a4_autohotkey"
    LOCAL_DAEMON = "a5_local_daemon"
    MANUAL_CONFIRMATION = "a6_manual_confirmation"


@dataclass
class HardeningPhaseSpec:
    """Specification for a single hardening phase."""

    phase: HardeningPhase
    status: PhaseStatus = PhaseStatus.NOT_STARTED
    prerequisites: list[HardeningPhase] = field(default_factory=list)
    unlocks_capabilities: list[ExtractionCapability] = field(default_factory=list)
    exit_criteria: list[str] = field(default_factory=list)
    blockers: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "phase": self.phase.value,
            "status": self.status.value,
            "prerequisites": [p.value for p in self.prerequisites],
            "unlocks_capabilities": [c.value for c in self.unlocks_capabilities],
            "exit_criteria": self.exit_criteria,
            "blockers": self.blockers,
        }


@dataclass
class CUHardeningPlan:
    """Full hardening plan for CU document reader."""

    phases: list[HardeningPhaseSpec] = field(default_factory=list)
    current_phase: HardeningPhase = HardeningPhase.FOREGROUND_OWNERSHIP
    overall_status: PhaseStatus = PhaseStatus.NOT_STARTED
    recommended_foreground_fix: ForegroundFixOption = ForegroundFixOption.SAME_TASK_LAUNCH

    def to_dict(self) -> dict[str, Any]:
        return {
            "current_phase": self.current_phase.value,
            "overall_status": self.overall_status.value,
            "recommended_foreground_fix": self.recommended_foreground_fix.value,
            "phases": [p.to_dict() for p in self.phases],
        }

    def get_next_actionable_phase(self) -> HardeningPhaseSpec | None:
        """Get the next phase that can be worked on."""
        for phase in self.phases:
            if phase.status in (PhaseStatus.NOT_STARTED, PhaseStatus.BLOCKED):
                prereqs_met = all(self._phase_complete(p) for p in phase.prerequisites)
                if prereqs_met:
                    return phase
        return None

    def _phase_complete(self, phase_id: HardeningPhase) -> bool:
        for p in self.phases:
            if p.phase == phase_id:
                return p.status == PhaseStatus.COMPLETE
        return False


def build_hardening_plan() -> CUHardeningPlan:
    """Build the full CU document reader hardening plan."""
    phases = [
        HardeningPhaseSpec(
            phase=HardeningPhase.FOREGROUND_OWNERSHIP,
            status=PhaseStatus.NOT_STARTED,
            prerequisites=[],
            unlocks_capabilities=[
                ExtractionCapability.CLIPBOARD_CAPTURE,
                ExtractionCapability.PAGE_SCROLLING,
                ExtractionCapability.VISIBLE_UI_EXTRACTION,
            ],
            exit_criteria=[
                "SetForegroundWindow returns True for Chrome window",
                "SendKeys delivered to Chrome (verified by keystroke effect)",
                "Process owns foreground reliably across multiple runs",
            ],
            blockers=[
                "Windows blocks foreground stealing from non-foreground processes",
                "Task Scheduler /IT is not the foreground owner",
            ],
        ),
        HardeningPhaseSpec(
            phase=HardeningPhase.CLIPBOARD_EXTRACTION,
            status=PhaseStatus.NOT_STARTED,
            prerequisites=[HardeningPhase.FOREGROUND_OWNERSHIP],
            unlocks_capabilities=[
                ExtractionCapability.DOCUMENT_BODY,
            ],
            exit_criteria=[
                "Ctrl+A selects full document tab content",
                "Ctrl+C populates clipboard with document text",
                "Get-Clipboard returns document body (not toolbar text)",
                "Word count matches API reference within 5% tolerance",
            ],
            blockers=[],
        ),
        HardeningPhaseSpec(
            phase=HardeningPhase.TAB_NAVIGATION,
            status=PhaseStatus.NOT_STARTED,
            prerequisites=[HardeningPhase.FOREGROUND_OWNERSHIP],
            unlocks_capabilities=[
                ExtractionCapability.DOCUMENT_TABS,
                ExtractionCapability.CHILD_TABS,
            ],
            exit_criteria=[
                "All tabs clickable or invocable",
                "Tab switch confirmed via accessibility tree change",
                "Each tab's content independently extractable",
                "Tab order preserved",
            ],
            blockers=[],
        ),
        HardeningPhaseSpec(
            phase=HardeningPhase.SCROLL_AND_READ,
            status=PhaseStatus.NOT_STARTED,
            prerequisites=[
                HardeningPhase.CLIPBOARD_EXTRACTION,
                HardeningPhase.TAB_NAVIGATION,
            ],
            unlocks_capabilities=[
                ExtractionCapability.PAGE_SCROLLING,
            ],
            exit_criteria=[
                "Multi-page tabs fully captured",
                "End-of-tab detection works (no new content after scroll)",
                "OR: Ctrl+A captures full tab without scrolling (hypothesis)",
            ],
            blockers=[],
        ),
        HardeningPhaseSpec(
            phase=HardeningPhase.PARITY_VALIDATION,
            status=PhaseStatus.NOT_STARTED,
            prerequisites=[
                HardeningPhase.CLIPBOARD_EXTRACTION,
                HardeningPhase.TAB_NAVIGATION,
                HardeningPhase.SCROLL_AND_READ,
            ],
            unlocks_capabilities=[
                ExtractionCapability.COMPLETENESS_VALIDATION,
            ],
            exit_criteria=[
                "Tab recall >= 100% vs API reference",
                "Word recall >= 95% vs API reference",
                "Phrase recall >= 95% vs API reference",
                "False positive content < 1%",
                "CanonicalSourceRecord emitted and validates",
            ],
            blockers=[],
        ),
    ]

    return CUHardeningPlan(
        phases=phases,
        current_phase=HardeningPhase.FOREGROUND_OWNERSHIP,
        overall_status=PhaseStatus.NOT_STARTED,
        recommended_foreground_fix=ForegroundFixOption.SAME_TASK_LAUNCH,
    )


def evaluate_foreground_fix_options() -> list[dict[str, Any]]:
    """Evaluate available foreground fix options."""
    return [
        {
            "option": ForegroundFixOption.SAME_TASK_LAUNCH.value,
            "description": "Launch Chrome AND reader from same scheduled task process",
            "install_required": False,
            "risk": "low",
            "recommended": True,
            "rationale": "Same process owns foreground. Zero install. Just restructure task.",
        },
        {
            "option": ForegroundFixOption.UIAUTOMATION_SETFOCUS.value,
            "description": "UIAutomation SetFocus on Chrome document element by PID",
            "install_required": False,
            "risk": "low",
            "recommended": False,
            "rationale": "SetFocus works for some elements but not guaranteed for Chrome canvas.",
        },
        {
            "option": ForegroundFixOption.ATTACH_THREAD_INPUT.value,
            "description": "Win32 AttachThreadInput to share foreground rights between threads",
            "install_required": False,
            "risk": "medium",
            "recommended": False,
            "rationale": "Known Windows API approach. Can work but fragile across Windows versions.",
        },
        {
            "option": ForegroundFixOption.AUTOHOTKEY.value,
            "description": "AutoHotkey script for window activation",
            "install_required": True,
            "risk": "low",
            "recommended": False,
            "rationale": "Reliable but requires install approval.",
        },
        {
            "option": ForegroundFixOption.LOCAL_DAEMON.value,
            "description": "Local desktop daemon that always has foreground rights",
            "install_required": True,
            "risk": "medium",
            "recommended": False,
            "rationale": "Most robust long-term but requires new service approval.",
        },
        {
            "option": ForegroundFixOption.MANUAL_CONFIRMATION.value,
            "description": "Founder manually confirms Chrome is in foreground before extraction",
            "install_required": False,
            "risk": "none",
            "recommended": False,
            "rationale": "Degraded UX. Last resort only.",
        },
    ]
