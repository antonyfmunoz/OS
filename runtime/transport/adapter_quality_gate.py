"""
Adapter quality gate for Phase 96.5 + 96.6.

An adapter cannot be promoted to the registry unless it passes
all quality checks: contracts, tests, safety policy, no-secret
policy, documentation, tool mastery, parity/completeness.

Tool Mastery is an internal layer of the Adapter Engine.
Mature adapters require a Tool Mastery Pack — expert-level
usage knowledge that makes the tool usable like a master,
not just connectable.

Phase 96.6 addition: Tool Mastery maturity validation.
A mastery pack that exists but lacks completeness requirements,
failure modes, anti-patterns, or validation checklists is
technically present but operationally incomplete.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any

from eos_ai.transport.adapter_engine_contracts import (
    AdapterRegistryEntry,
    ToolMasteryPack,
    tool_mastery_is_mature,
)


@dataclass
class QualityCheckResult:
    """Result of a single quality check."""

    check_name: str
    passed: bool = False
    reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "check_name": self.check_name,
            "passed": self.passed,
            "reason": self.reason,
        }


@dataclass
class AdapterQualityReport:
    """Full quality report for an adapter."""

    adapter_id: str
    checks: list[QualityCheckResult] = field(default_factory=list)
    overall_passed: bool = False
    promotable: bool = False
    maturity_score: float = 0.0
    gaps_to_100: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "adapter_id": self.adapter_id,
            "checks": [c.to_dict() for c in self.checks],
            "overall_passed": self.overall_passed,
            "promotable": self.promotable,
            "maturity_score": self.maturity_score,
            "gaps_to_100": self.gaps_to_100,
        }


def adapter_has_required_contracts(entry: AdapterRegistryEntry) -> bool:
    return entry.has_contract


def adapter_has_tests(entry: AdapterRegistryEntry) -> bool:
    return entry.has_tests


def adapter_has_safety_policy(entry: AdapterRegistryEntry) -> bool:
    return entry.safety_policy is not None


def adapter_has_no_secret_policy(entry: AdapterRegistryEntry) -> bool:
    if entry.safety_policy is None:
        return False
    return entry.safety_policy.no_secret_exposure and entry.safety_policy.no_credential_capture


def adapter_has_docs(entry: AdapterRegistryEntry) -> bool:
    return entry.has_docs


def adapter_has_tool_mastery(entry: AdapterRegistryEntry) -> bool:
    """Mature adapters require a Tool Mastery Pack."""
    return entry.has_tool_mastery


def adapter_is_promotable(entry: AdapterRegistryEntry) -> bool:
    """An adapter is promotable only if ALL quality checks pass."""
    return all(
        [
            adapter_has_required_contracts(entry),
            adapter_has_tests(entry),
            adapter_has_safety_policy(entry),
            adapter_has_no_secret_policy(entry),
            adapter_has_docs(entry),
            adapter_has_tool_mastery(entry),
        ]
    )


def _score_and_gaps(checks: list[QualityCheckResult]) -> tuple[float, list[str]]:
    """Compute maturity score (0.0-100.0) and list of gaps from check results."""
    if not checks:
        return 0.0, []
    passed = sum(1 for c in checks if c.passed)
    score = round((passed / len(checks)) * 100.0, 1)
    gaps = [c.reason or c.check_name for c in checks if not c.passed]
    return score, gaps


def evaluate_adapter_quality(entry: AdapterRegistryEntry) -> AdapterQualityReport:
    """Run all quality checks and produce a report."""
    checks = [
        QualityCheckResult(
            "has_contracts",
            adapter_has_required_contracts(entry),
            "" if entry.has_contract else "missing contract",
        ),
        QualityCheckResult(
            "has_tests", adapter_has_tests(entry), "" if entry.has_tests else "missing tests"
        ),
        QualityCheckResult(
            "has_safety_policy",
            adapter_has_safety_policy(entry),
            "" if entry.safety_policy else "missing safety policy",
        ),
        QualityCheckResult(
            "has_no_secret_policy",
            adapter_has_no_secret_policy(entry),
            "" if adapter_has_no_secret_policy(entry) else "missing no-secret policy",
        ),
        QualityCheckResult(
            "has_docs", adapter_has_docs(entry), "" if entry.has_docs else "missing documentation"
        ),
        QualityCheckResult(
            "has_tool_mastery",
            adapter_has_tool_mastery(entry),
            "" if entry.has_tool_mastery else "missing tool mastery pack",
        ),
    ]

    all_passed = all(c.passed for c in checks)
    score, gaps = _score_and_gaps(checks)

    return AdapterQualityReport(
        adapter_id=entry.profile.adapter_id,
        checks=checks,
        overall_passed=all_passed,
        promotable=all_passed,
        maturity_score=score,
        gaps_to_100=gaps,
    )


def adapter_tool_mastery_is_mature(entry: AdapterRegistryEntry) -> bool:
    """A mature adapter's Tool Mastery Pack must have all critical sections."""
    if entry.tool_mastery is None:
        return False
    return tool_mastery_is_mature(entry.tool_mastery)


def evaluate_adapter_maturity(entry: AdapterRegistryEntry) -> AdapterQualityReport:
    """Extended quality check including mastery maturity (Phase 96.6).

    Goes beyond has_tool_mastery (boolean flag) to validate the mastery
    pack's actual content — completeness requirements, failure modes,
    anti-patterns, and validation checklist must all be populated.
    """
    base = evaluate_adapter_quality(entry)

    maturity_check = QualityCheckResult(
        "tool_mastery_is_mature",
        adapter_tool_mastery_is_mature(entry),
        "" if adapter_tool_mastery_is_mature(entry) else "mastery pack missing critical sections",
    )
    base.checks.append(maturity_check)
    base.overall_passed = all(c.passed for c in base.checks)
    base.promotable = base.overall_passed
    base.maturity_score, base.gaps_to_100 = _score_and_gaps(base.checks)
    return base


def build_adapter_quality_report(entry: AdapterRegistryEntry) -> dict[str, Any]:
    """Build quality report as dict."""
    report = evaluate_adapter_quality(entry)
    return report.to_dict()
