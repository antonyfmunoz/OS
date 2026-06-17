"""Operator Attention Engine — deterministic ranked priorities.

Produces a ranked list of items needing operator attention, each with
a deep-link to the relevant workstation capability. Ranking is fixed:
  failures > approvals > intent misalignment > blocked work > recovery > drift > changes

The engine composes existing subsystem outputs. No LLM calls.
Each item includes a capability_link so the UI can open the correct panel.

Gate 4 — Workstation Convergence Runtime. UMH substrate subsystem. Instance-agnostic.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


_CATEGORY_PRIORITY = {
    "failure": 0,
    "approval": 1,
    "misalignment": 2,
    "blocked": 3,
    "recovery": 4,
    "drift": 5,
    "change": 6,
}

_SEVERITY_PRIORITY = {
    "critical": 0,
    "high": 1,
    "medium": 2,
    "low": 3,
}


@dataclass
class AttentionItem:
    priority: int = 0
    category: str = "change"
    severity: str = "medium"
    title: str = ""
    description: str = ""
    action_hint: str = ""
    source_id: str = ""
    source_system: str = ""
    capability_link: str = ""
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "priority": self.priority,
            "category": self.category,
            "severity": self.severity,
            "title": self.title,
            "description": self.description,
            "action_hint": self.action_hint,
            "source_id": self.source_id,
            "source_system": self.source_system,
            "capability_link": self.capability_link,
            "timestamp": self.timestamp,
        }


class OperatorAttentionEngine:
    """Deterministic ranked priority engine for operator attention."""

    def __init__(
        self,
        service_failure_engine: Any | None = None,
        work_runtime: Any | None = None,
        intent_runtime: Any | None = None,
        state_coherence_engine: Any | None = None,
        context_engine: Any | None = None,
    ) -> None:
        self._service_failure_engine = service_failure_engine
        self._work_runtime = work_runtime
        self._intent_runtime = intent_runtime
        self._state_coherence_engine = state_coherence_engine
        self._context_engine = context_engine

    # ── Lazy subsystem access ────────────────────────────────────

    @property
    def service_failure_engine(self) -> Any:
        if self._service_failure_engine is None:
            try:
                from substrate.organism.service_failure_engine import ServiceFailureEngine
                self._service_failure_engine = ServiceFailureEngine()
            except Exception:
                logger.debug("ServiceFailureEngine unavailable")
        return self._service_failure_engine

    @property
    def work_runtime(self) -> Any:
        if self._work_runtime is None:
            try:
                from substrate.organism.governed_work_runtime import GovernedWorkRuntime
                self._work_runtime = GovernedWorkRuntime()
            except Exception:
                logger.debug("GovernedWorkRuntime unavailable")
        return self._work_runtime

    @property
    def intent_runtime(self) -> Any:
        if self._intent_runtime is None:
            try:
                from substrate.operator.intent_runtime import IntentRuntime
                self._intent_runtime = IntentRuntime()
            except Exception:
                logger.debug("IntentRuntime unavailable")
        return self._intent_runtime

    @property
    def state_coherence_engine(self) -> Any:
        if self._state_coherence_engine is None:
            try:
                from substrate.organism.state_coherence_engine import StateCoherenceEngine
                self._state_coherence_engine = StateCoherenceEngine()
            except Exception:
                logger.debug("StateCoherenceEngine unavailable")
        return self._state_coherence_engine

    @property
    def context_engine(self) -> Any:
        if self._context_engine is None:
            try:
                from substrate.operator.operator_context_engine import OperatorContextEngine
                self._context_engine = OperatorContextEngine()
            except Exception:
                logger.debug("OperatorContextEngine unavailable")
        return self._context_engine

    # ── Public API ───────────────────────────────────────────────

    def compute(self) -> list[AttentionItem]:
        """Compute all attention items, ranked by category then severity."""
        items: list[AttentionItem] = []

        items.extend(self._failures())
        items.extend(self._approvals())
        items.extend(self._misalignments())
        items.extend(self._blocked_work())
        items.extend(self._recovery())
        items.extend(self._drift())

        items.sort(key=lambda item: (
            _CATEGORY_PRIORITY.get(item.category, 99),
            _SEVERITY_PRIORITY.get(item.severity, 99),
        ))

        for i, item in enumerate(items):
            item.priority = i + 1

        return items

    def top(self, n: int = 5) -> list[AttentionItem]:
        """Top N attention items."""
        return self.compute()[:n]

    def by_category(self, category: str) -> list[AttentionItem]:
        """Filter attention items by category."""
        return [item for item in self.compute() if item.category == category]

    # ── Category producers ───────────────────────────────────────

    def _failures(self) -> list[AttentionItem]:
        """Service failures → critical attention."""
        items: list[AttentionItem] = []
        if self.service_failure_engine is None:
            return items

        try:
            failures = self.service_failure_engine.current_failures()
            for f in failures:
                items.append(AttentionItem(
                    category="failure",
                    severity="critical",
                    title=f"Service failure: {f.get('service_name', 'unknown')}",
                    description=f.get("error", ""),
                    action_hint=f"Check {f.get('service_name', 'service')} in Organism Map",
                    source_id=f.get("service_id", ""),
                    source_system="service_failure_engine",
                    capability_link="organismmap",
                ))
        except Exception:
            logger.debug("Failed to get service failures")

        return items

    def _approvals(self) -> list[AttentionItem]:
        """Pending approvals → high attention."""
        items: list[AttentionItem] = []
        if self.work_runtime is None:
            return items

        try:
            if self.work_runtime.work_graph is not None:
                pending = self.work_runtime.work_graph.work_by_status("approval_pending")
                for node in pending:
                    severity = "high" if node.risk_class in ("high", "critical") else "medium"
                    items.append(AttentionItem(
                        category="approval",
                        severity=severity,
                        title=f"Approval needed: {node.description[:80]}",
                        description=f"Risk: {node.risk_class}",
                        action_hint="Review and approve or reject in Work",
                        source_id=node.work_id,
                        source_system="governed_work_runtime",
                        capability_link="approvals",
                    ))
        except Exception:
            logger.debug("Failed to get pending approvals")

        return items

    def _misalignments(self) -> list[AttentionItem]:
        """Active work misaligned with stated intent."""
        items: list[AttentionItem] = []
        if self.intent_runtime is None or self.work_runtime is None:
            return items

        try:
            active_work = self.work_runtime.active()
            for work in active_work:
                desc = work.get("description", "")
                if not desc:
                    continue
                score = self.intent_runtime.alignment_score(desc)
                if score < 0.3:
                    items.append(AttentionItem(
                        category="misalignment",
                        severity="high" if score < 0.1 else "medium",
                        title=f"Low intent alignment: {desc[:60]}",
                        description=f"Alignment score: {score:.0%}",
                        action_hint="Review intent or adjust work scope",
                        source_id=work.get("work_id", ""),
                        source_system="intent_runtime",
                        capability_link="work",
                    ))
        except Exception:
            logger.debug("Failed to check intent alignment")

        return items

    def _blocked_work(self) -> list[AttentionItem]:
        """Blocked work items."""
        items: list[AttentionItem] = []
        if self.work_runtime is None:
            return items

        try:
            blocked = self.work_runtime.blocked()
            for work in blocked:
                items.append(AttentionItem(
                    category="blocked",
                    severity="medium",
                    title=f"Blocked: {work.get('description', 'unknown')[:60]}",
                    description=f"Blockers: {len(work.get('blockers', []))}",
                    action_hint="Resolve blockers in Work",
                    source_id=work.get("work_id", ""),
                    source_system="governed_work_runtime",
                    capability_link="work",
                ))
        except Exception:
            logger.debug("Failed to get blocked work")

        return items

    def _recovery(self) -> list[AttentionItem]:
        """Recoverable work items."""
        items: list[AttentionItem] = []
        if self.work_runtime is None:
            return items

        try:
            recoverable = self.work_runtime.recovery()
            for work in recoverable:
                items.append(AttentionItem(
                    category="recovery",
                    severity="medium",
                    title=f"Recoverable: {work.get('description', 'unknown')[:60]}",
                    description=work.get("recovery_action", ""),
                    action_hint="Retry or resume in Work",
                    source_id=work.get("work_id", ""),
                    source_system="work_recovery_runtime",
                    capability_link="work",
                ))
        except Exception:
            logger.debug("Failed to get recoverable work")

        return items

    def _drift(self) -> list[AttentionItem]:
        """State coherence drift."""
        items: list[AttentionItem] = []
        if self.state_coherence_engine is None:
            return items

        try:
            incoherent = self.state_coherence_engine.incoherent_domains()
            for domain in incoherent:
                items.append(AttentionItem(
                    category="drift",
                    severity="high" if domain.get("severity") == "critical" else "medium",
                    title=f"State drift: {domain.get('domain', 'unknown')}",
                    description=domain.get("description", ""),
                    action_hint="Investigate in Organism Map",
                    source_id=domain.get("domain_id", ""),
                    source_system="state_coherence_engine",
                    capability_link="organismmap",
                ))
        except Exception:
            logger.debug("Failed to get coherence drift")

        return items
