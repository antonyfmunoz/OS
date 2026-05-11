"""
Backend selection engine for Phase 96.3.

Selects the best backend for a given task based on completeness,
safety, provenance, independence, and governance compatibility.

Rules:
- Production ingestion prefers most complete, safest, highest-provenance.
- Fallback tests prefer high-independence backends.
- Interface-only wrappers (LEVEL_0) do not count as independent fallbacks.
- MCP/CLI not automatically independent.
- OAuth/auth is not backend independence.
- Computer Use is first-class but must satisfy same contract.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any

from eos_ai.transport.backend_registry_contracts import (
    BackendCategory,
    BackendImplementationType,
    BackendProfile,
    BackendSelectionFactor,
    BackendStatus,
)


_INTERFACE_ONLY_TYPES = {
    BackendImplementationType.CLI_INTERFACE_WRAPPER,
    BackendImplementationType.MCP_INTERFACE_WRAPPER,
}


@dataclass
class SelectionTask:
    """Describes what the backend selection is for."""

    task_type: str
    source_type: str = ""
    require_independence: bool = False
    require_parity: bool = False
    prefer_completeness: bool = True
    prefer_safety: bool = True
    notes: str = ""


@dataclass
class SelectionResult:
    """Result of backend selection."""

    selected: BackendProfile | None = None
    ranked: list[BackendProfile] = field(default_factory=list)
    rejected: list[tuple[BackendProfile, str]] = field(default_factory=list)
    explanation: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "selected": self.selected.to_dict() if self.selected else None,
            "ranked_count": len(self.ranked),
            "rejected_count": len(self.rejected),
            "explanation": self.explanation,
        }


def detect_when_backend_is_interface_only(profile: BackendProfile) -> bool:
    """Interface-only wrappers share failure domain with their underlying backend."""
    return profile.implementation_type in _INTERFACE_ONLY_TYPES


def detect_when_backend_is_true_fallback(profile: BackendProfile) -> bool:
    """A true fallback has independence > LEVEL_0 and is not interface-only."""
    if detect_when_backend_is_interface_only(profile):
        return False
    return profile.independence_level not in ("", "level_0_interface_wrapper")


def filter_backends_by_policy(
    task: SelectionTask,
    profiles: list[BackendProfile],
) -> list[BackendProfile]:
    """Filter backends by task requirements."""
    result: list[BackendProfile] = []
    for p in profiles:
        if task.require_independence and not detect_when_backend_is_true_fallback(p):
            continue
        if p.current_status == BackendStatus.BLOCKED:
            continue
        result.append(p)
    return result


def _score_backend(task: SelectionTask, profile: BackendProfile) -> int:
    score = 0
    if profile.current_status == BackendStatus.COMPLETE:
        score += 100
    elif profile.current_status == BackendStatus.PARTIAL:
        score += 30
    if task.prefer_completeness and profile.coverage_contract_status == "complete":
        score += 50
    if task.prefer_safety and not profile.safety_constraints:
        score += 10
    if detect_when_backend_is_true_fallback(profile):
        score += 20
    if task.require_independence and detect_when_backend_is_true_fallback(profile):
        score += 40
    return score


def rank_backends_for_task(
    task: SelectionTask,
    profiles: list[BackendProfile],
) -> list[BackendProfile]:
    """Rank backends by fitness for task."""
    filtered = filter_backends_by_policy(task, profiles)
    return sorted(filtered, key=lambda p: _score_backend(task, p), reverse=True)


def select_best_backend(
    task: SelectionTask,
    profiles: list[BackendProfile],
) -> SelectionResult:
    """Select the best backend for a task."""
    ranked = rank_backends_for_task(task, profiles)

    rejected: list[tuple[BackendProfile, str]] = []
    for p in profiles:
        if p not in ranked:
            if p.current_status == BackendStatus.BLOCKED:
                rejected.append((p, "blocked"))
            elif task.require_independence and detect_when_backend_is_interface_only(p):
                rejected.append((p, "interface-only wrapper, not independent"))
            else:
                rejected.append((p, "filtered by policy"))

    selected = ranked[0] if ranked else None
    explanation = explain_backend_selection(selected, rejected)

    return SelectionResult(
        selected=selected,
        ranked=ranked,
        rejected=rejected,
        explanation=explanation,
    )


def explain_backend_selection(
    selected: BackendProfile | None,
    rejected: list[tuple[BackendProfile, str]],
) -> str:
    """Explain why a backend was selected or why all were rejected."""
    if selected is None:
        return "No backends available after policy filtering"
    parts = [f"Selected {selected.backend_id} ({selected.category.value})"]
    if rejected:
        parts.append(f"Rejected {len(rejected)} backend(s)")
    return "; ".join(parts)


def require_backend_parity_if_test_demands_it(
    task: SelectionTask,
) -> bool:
    """Backend parity tests require all selected backends to satisfy the same contract."""
    return task.require_parity
