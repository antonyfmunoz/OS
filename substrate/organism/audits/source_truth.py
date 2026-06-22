"""Audit — Source of Truth (Production Lineage).

Campaign 23B — Category I Audit.
Tier 3: organism audit (inspects system state, generates a report — no task execution).

Measures whether each production traces an unbroken lineage from intent through
to capability. A complete chain means the organism can answer "why does this
exist" at every stage. All metrics deterministic. No LLM calls.
"""

from __future__ import annotations

import logging
from dataclasses import asdict, dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


LINEAGE_STAGES = [
    "intent",
    "decision",
    "requirement",
    "packet",
    "code",
    "review",
    "deploy",
    "outcome",
    "capability",
]


@dataclass
class LineageChain:
    """Lineage completeness for a single production."""

    chain_id: str = ""
    stages_present: list[str] = field(default_factory=list)
    stages_missing: list[str] = field(default_factory=list)
    completeness: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class SourceTruthReport:
    """Result of a source-of-truth lineage audit."""

    chains_evaluated: int = 0
    avg_completeness: float = 0.0
    full_chains: int = 0
    partial_chains: int = 0
    broken_chains: int = 0
    orphan_pct: float = 0.0
    stage_coverage: dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class SourceTruthAudit:
    """Audits lineage completeness across a set of productions."""

    def run(self, productions: list[dict[str, Any]]) -> SourceTruthReport:
        """Run the source-of-truth audit.

        Each production is a dict keyed by :data:`LINEAGE_STAGES`. A truthy value
        means the stage is present; a falsy value (missing key, empty string,
        ``None``, ``False``) means it is missing.
        """
        productions = list(productions or [])

        if not productions:
            return SourceTruthReport(
                stage_coverage={stage: 0.0 for stage in LINEAGE_STAGES}
            )

        chains: list[LineageChain] = []
        for idx, production in enumerate(productions):
            chains.append(self._build_chain(idx, production))

        total = len(chains)
        avg_completeness = round(sum(c.completeness for c in chains) / total, 4)
        full = sum(1 for c in chains if c.completeness >= 1.0)
        broken = sum(1 for c in chains if c.completeness == 0.0)
        partial = total - full - broken

        # Stage coverage: how often each stage is present across all chains.
        stage_coverage: dict[str, float] = {}
        for stage in LINEAGE_STAGES:
            present = sum(1 for c in chains if stage in c.stages_present)
            stage_coverage[stage] = round(present / total, 4)

        # Orphan percentage: fraction of all (chain, stage) slots that are missing.
        total_slots = total * len(LINEAGE_STAGES)
        missing_slots = sum(len(c.stages_missing) for c in chains)
        orphan_pct = round(missing_slots / total_slots, 4) if total_slots > 0 else 0.0

        return SourceTruthReport(
            chains_evaluated=total,
            avg_completeness=avg_completeness,
            full_chains=full,
            partial_chains=partial,
            broken_chains=broken,
            orphan_pct=orphan_pct,
            stage_coverage=stage_coverage,
        )

    @staticmethod
    def _build_chain(idx: int, production: dict[str, Any]) -> LineageChain:
        chain_id = str(production.get("chain_id") or production.get("id") or f"chain-{idx}")
        present: list[str] = []
        missing: list[str] = []

        for stage in LINEAGE_STAGES:
            if SourceTruthAudit._is_present(production.get(stage)):
                present.append(stage)
            else:
                missing.append(stage)

        completeness = round(len(present) / len(LINEAGE_STAGES), 4)
        return LineageChain(
            chain_id=chain_id,
            stages_present=present,
            stages_missing=missing,
            completeness=completeness,
        )

    @staticmethod
    def _is_present(value: Any) -> bool:
        if value is None or value is False:
            return False
        if isinstance(value, str):
            return bool(value.strip())
        if isinstance(value, (list, dict, tuple, set)):
            return len(value) > 0
        return bool(value)
