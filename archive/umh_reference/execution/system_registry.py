"""SystemRegistry — store and retrieve reusable system graphs for UMH.

Maintains an in-memory registry of SystemTemplates — system graphs
that executed successfully, indexed by context signature for retrieval.
Templates accumulate statistics via EMA updates.

Pipeline position:
    SystemGraph execution → register if successful
    New context → find_candidates → SystemSelector

Pure data management. No execution. No I/O.

Usage::

    from umh.execution.system_registry import SystemRegistry, SystemTemplate

    registry = SystemRegistry()
    registry.register(graph, context_sig, execution_result)
    candidates = registry.find_candidates(current_context)
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field


# ─── Constants ────────────────────────────────────────────────────

MAX_TEMPLATES = 30
EMA_ALPHA = 0.2
MIN_CONFIDENCE_FOR_REGISTRATION = 0.3
MIN_SUCCESS_RATE_FOR_REGISTRATION = 0.0
CONTEXT_MATCH_THRESHOLD = 0.4


# ─── Data models ─────────────────────────────────────────────────


@dataclass
class SystemTemplate:
    """A reusable system graph with accumulated statistics."""

    template_id: str
    graph: object  # SystemGraph
    context_signature: dict[str, str]
    action_types: tuple[str, ...]
    success_rate: float
    avg_credit: float
    usage_count: int
    confidence: float
    domains: set[str]

    def to_dict(self) -> dict:
        graph_dict = (
            self.graph.to_dict() if hasattr(self.graph, "to_dict") else str(self.graph)
        )
        return {
            "template_id": self.template_id,
            "graph": graph_dict,
            "context_signature": dict(self.context_signature),
            "action_types": list(self.action_types),
            "success_rate": round(self.success_rate, 4),
            "avg_credit": round(self.avg_credit, 4),
            "usage_count": self.usage_count,
            "confidence": round(self.confidence, 4),
            "domains": sorted(self.domains),
        }

    @classmethod
    def from_dict(cls, d: dict) -> SystemTemplate:
        return cls(
            template_id=d["template_id"],
            graph=d.get("graph"),
            context_signature=d.get("context_signature", {}),
            action_types=tuple(d.get("action_types", ())),
            success_rate=d.get("success_rate", 0.0),
            avg_credit=d.get("avg_credit", 0.0),
            usage_count=d.get("usage_count", 0),
            confidence=d.get("confidence", 0.0),
            domains=set(d.get("domains", ())),
        )


# ─── Template ID ──────────────────────────────────────────────────


def _compute_template_id(
    context_signature: dict[str, str],
    action_types: tuple[str, ...],
) -> str:
    canonical = json.dumps(
        {"ctx": context_signature, "types": list(action_types)},
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:12]


# ─── Context matching ────────────────────────────────────────────


def context_match_score(
    current: dict[str, str],
    template: dict[str, str],
) -> float:
    """Compute match score between two context signatures.

    Exact categorical match on each dimension scores 1/N.
    Returns [0.0, 1.0].
    """
    if not template:
        return 0.0
    keys = set(current.keys()) | set(template.keys())
    if not keys:
        return 0.0
    matches = sum(1 for k in keys if current.get(k) == template.get(k))
    return matches / len(keys)


# ─── Extract helpers ──────────────────────────────────────────────


def _extract_action_types(graph: object) -> tuple[str, ...]:
    """Extract sorted unique action types from a SystemGraph."""
    nodes = getattr(graph, "nodes", {})
    types: set[str] = set()
    for node in nodes.values():
        action = getattr(node, "action", None)
        if action is not None:
            at = getattr(action, "action_type", "")
            if at:
                types.add(at)
    return tuple(sorted(types))


def _extract_domains(graph: object) -> set[str]:
    """Extract unique domains from a SystemGraph."""
    nodes = getattr(graph, "nodes", {})
    domains: set[str] = set()
    for node in nodes.values():
        action = getattr(node, "action", None)
        if action is not None:
            d = getattr(action, "domain", "")
            if d:
                domains.add(d)
    return domains


def _result_credit(execution_result: object) -> float:
    """Derive a credit value from a SystemExecutionResult."""
    completed = getattr(execution_result, "completed_nodes", 0)
    total = getattr(execution_result, "total_nodes", 1) or 1
    failed = getattr(execution_result, "failed_nodes", 0)
    return (completed - failed) / total


def _result_success(execution_result: object) -> bool:
    """Determine if a system execution was successful enough to register."""
    status = getattr(execution_result, "status", "")
    if status == "completed":
        return True
    if status == "partial":
        completed = getattr(execution_result, "completed_nodes", 0)
        total = getattr(execution_result, "total_nodes", 1) or 1
        return completed / total >= 0.5
    return False


# ─── Registry ────────────────────────────────────────────────────


class SystemRegistry:
    """In-memory registry of reusable system templates."""

    def __init__(self) -> None:
        self._templates: dict[str, SystemTemplate] = {}

    @property
    def count(self) -> int:
        return len(self._templates)

    def get(self, template_id: str) -> SystemTemplate | None:
        return self._templates.get(template_id)

    def get_all(self) -> list[SystemTemplate]:
        return list(self._templates.values())

    def register(
        self,
        graph: object,
        context_signature: dict[str, str],
        execution_result: object,
    ) -> str | None:
        """Register a system graph as a reusable template.

        Only registers if execution was successful or strong partial.
        Returns template_id if registered, None if rejected.
        """
        if not _result_success(execution_result):
            return None

        action_types = _extract_action_types(graph)
        domains = _extract_domains(graph)
        credit = _result_credit(execution_result)
        template_id = _compute_template_id(context_signature, action_types)

        existing = self._templates.get(template_id)
        if existing is not None:
            new_count = existing.usage_count + 1
            new_success_rate = (
                1.0 - EMA_ALPHA
            ) * existing.success_rate + EMA_ALPHA * 1.0
            new_avg_credit = (
                1.0 - EMA_ALPHA
            ) * existing.avg_credit + EMA_ALPHA * credit
            new_confidence = min(1.0, new_count / (new_count + 10.0))
            new_domains = existing.domains | domains

            self._templates[template_id] = SystemTemplate(
                template_id=template_id,
                graph=graph,
                context_signature=context_signature,
                action_types=action_types,
                success_rate=new_success_rate,
                avg_credit=new_avg_credit,
                usage_count=new_count,
                confidence=new_confidence,
                domains=new_domains,
            )
        else:
            confidence = min(1.0, 1.0 / (1.0 + 10.0))
            self._templates[template_id] = SystemTemplate(
                template_id=template_id,
                graph=graph,
                context_signature=context_signature,
                action_types=action_types,
                success_rate=1.0,
                avg_credit=credit,
                usage_count=1,
                confidence=confidence,
                domains=domains,
            )

        if len(self._templates) > MAX_TEMPLATES:
            self._evict_weakest()

        return template_id

    def update_template(
        self,
        template_id: str,
        credit: float,
        success: bool,
    ) -> bool:
        """Update a template's statistics after re-execution.

        Returns True if template exists and was updated.
        """
        template = self._templates.get(template_id)
        if template is None:
            return False

        new_count = template.usage_count + 1
        outcome = 1.0 if success else 0.0
        new_success_rate = (
            1.0 - EMA_ALPHA
        ) * template.success_rate + EMA_ALPHA * outcome
        new_avg_credit = (1.0 - EMA_ALPHA) * template.avg_credit + EMA_ALPHA * credit
        new_confidence = min(1.0, new_count / (new_count + 10.0))

        self._templates[template_id] = SystemTemplate(
            template_id=template_id,
            graph=template.graph,
            context_signature=template.context_signature,
            action_types=template.action_types,
            success_rate=new_success_rate,
            avg_credit=new_avg_credit,
            usage_count=new_count,
            confidence=new_confidence,
            domains=template.domains,
        )
        return True

    def find_candidates(
        self,
        context_signature: dict[str, str],
    ) -> list[tuple[float, SystemTemplate]]:
        """Find templates matching a context signature.

        Returns (match_score, template) pairs sorted by match score
        descending. Only includes templates above CONTEXT_MATCH_THRESHOLD.
        """
        candidates: list[tuple[float, SystemTemplate]] = []
        for template in self._templates.values():
            score = context_match_score(context_signature, template.context_signature)
            if score >= CONTEXT_MATCH_THRESHOLD:
                candidates.append((score, template))
        candidates.sort(key=lambda x: (-x[0], -x[1].confidence))
        return candidates

    def _evict_weakest(self) -> None:
        if not self._templates:
            return
        weakest_id = min(
            self._templates,
            key=lambda tid: (
                self._templates[tid].usage_count,
                self._templates[tid].confidence,
            ),
        )
        del self._templates[weakest_id]

    def reset(self) -> None:
        self._templates.clear()

    def to_dict(self) -> dict:
        return {tid: t.to_dict() for tid, t in self._templates.items()}


if __name__ == "__main__":
    print("system_registry import OK")
