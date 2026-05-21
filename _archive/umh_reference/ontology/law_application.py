"""Phase 81 law application records — advisory-only law application to contexts.

Law applications are analytical, not executable. They identify relevance,
constraints, and risks without mutating state or executing actions.

No execution. No mutation. No adapter calls. No LLM calls.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from umh.ontology.laws import UniversalLaw, clamp_confidence


class LawApplicationStatus(str, Enum):
    APPLICABLE = "applicable"
    PARTIALLY_APPLICABLE = "partially_applicable"
    NOT_APPLICABLE = "not_applicable"
    INSUFFICIENT_DATA = "insufficient_data"
    UNKNOWN = "unknown"


def normalize_law_application_status(value: str) -> LawApplicationStatus:
    v = value.strip().lower()
    for m in LawApplicationStatus:
        if m.value == v:
            return m
    return LawApplicationStatus.UNKNOWN


@dataclass
class LawApplication:
    application_id: str
    law_id: str = ""
    target_id: str = ""
    target_type: str = ""
    domain: str = ""
    context: str = ""
    applicable_primitives: list[str] = field(default_factory=list)
    observed_state: str = ""
    predicted_or_implied_transition: str = ""
    constraints_identified: list[str] = field(default_factory=list)
    risks_identified: list[str] = field(default_factory=list)
    confidence: float = 0.5
    status: LawApplicationStatus = LawApplicationStatus.UNKNOWN
    evidence: list[str] = field(default_factory=list)
    unknowns: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "application_id": self.application_id,
            "law_id": self.law_id,
            "target_id": self.target_id,
            "target_type": self.target_type,
            "domain": self.domain,
            "context": self.context,
            "applicable_primitives": self.applicable_primitives,
            "observed_state": self.observed_state,
            "predicted_or_implied_transition": self.predicted_or_implied_transition,
            "constraints_identified": self.constraints_identified,
            "risks_identified": self.risks_identified,
            "confidence": self.confidence,
            "status": self.status.value,
            "evidence": self.evidence,
            "unknowns": self.unknowns,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> LawApplication:
        return cls(
            application_id=data.get("application_id", f"lapp_{uuid.uuid4().hex[:10]}"),
            law_id=data.get("law_id", ""),
            target_id=data.get("target_id", ""),
            target_type=data.get("target_type", ""),
            domain=data.get("domain", ""),
            context=data.get("context", ""),
            applicable_primitives=data.get("applicable_primitives", []),
            observed_state=data.get("observed_state", ""),
            predicted_or_implied_transition=data.get("predicted_or_implied_transition", ""),
            constraints_identified=data.get("constraints_identified", []),
            risks_identified=data.get("risks_identified", []),
            confidence=clamp_confidence(data.get("confidence", 0.5)),
            status=normalize_law_application_status(data.get("status", "unknown")),
            evidence=data.get("evidence", []),
            unknowns=data.get("unknowns", []),
            metadata=data.get("metadata", {}),
        )


def apply_law_to_context(
    law: UniversalLaw,
    context: str,
    primitives: list[str] | None = None,
    domain: str = "",
) -> LawApplication:
    app_id = f"lapp_{uuid.uuid4().hex[:10]}"

    if not context:
        return LawApplication(
            application_id=app_id,
            law_id=law.law_id,
            context="",
            status=LawApplicationStatus.INSUFFICIENT_DATA,
            confidence=0.1,
            unknowns=["No context provided"],
        )

    ctx_lower = context.lower()
    matched_primitives = []
    if primitives:
        matched_primitives = [p for p in primitives if p in law.applies_to_primitives]
    else:
        for prim in law.applies_to_primitives:
            if prim.lower().replace("_", " ") in ctx_lower or prim.lower() in ctx_lower:
                matched_primitives.append(prim)

    constraints: list[str] = []
    risks: list[str] = []
    evidence: list[str] = []
    unknowns: list[str] = []
    transition = ""

    if matched_primitives:
        transition = law.state_transition_effect
        constraints = list(law.constraints_created)
        for fc in law.failure_conditions:
            risks.append(f"Failure condition: {fc}")
        evidence.append(f"Law '{law.name}' applies to primitives: {', '.join(matched_primitives)}")
    else:
        unknowns.append("No matching primitives found in context")

    if "deprecated" in ctx_lower or "stale" in ctx_lower:
        if law.law_name.value == "entropy":
            risks.append("Drift/staleness risk detected in context")
            evidence.append("Context mentions deprecated/stale state")

    if "ordering" in ctx_lower or "sequence" in ctx_lower or "boot" in ctx_lower:
        if law.law_name.value == "temporal_dependency":
            evidence.append("Context involves sequencing or ordering")

    if "feedback" in ctx_lower or "outcome" in ctx_lower:
        if law.law_name.value == "feedback":
            evidence.append("Context involves feedback or outcome signals")

    if law.law_name.value == "unity_oneness":
        _unity_keywords = [
            ("module", "Check callers, contracts, and dependency graph"),
            ("file", "Check callers, contracts, and dependency graph"),
            ("action", "Check downstream effects and governance boundary"),
            ("business", "Check team/customer/cash/brand/market systemic effects"),
            ("interface", "Interface is cockpit not engine; preserve control boundary"),
            ("agent", "Agent cannot bypass governance/storage/execution spine"),
            ("tool", "Tool cannot bypass governance/storage/execution spine"),
            ("deploy", "Deployment affects shared runtime; check systemic effects"),
            ("refactor", "Refactoring affects callers and contracts system-wide"),
        ]
        for kw, advisory in _unity_keywords:
            if kw in ctx_lower:
                risks.append(advisory)
                evidence.append(f"Context involves '{kw}' — unity/interdependence relevant")

    if matched_primitives and evidence:
        status = LawApplicationStatus.APPLICABLE
        conf = 0.7
    elif matched_primitives:
        status = LawApplicationStatus.PARTIALLY_APPLICABLE
        conf = 0.5
    elif evidence:
        status = LawApplicationStatus.PARTIALLY_APPLICABLE
        conf = 0.4
    else:
        status = LawApplicationStatus.NOT_APPLICABLE
        conf = 0.3

    if unknowns:
        conf = max(0.1, conf - 0.1 * len(unknowns))

    return LawApplication(
        application_id=app_id,
        law_id=law.law_id,
        domain=domain,
        context=context[:500],
        applicable_primitives=matched_primitives,
        observed_state=context[:200],
        predicted_or_implied_transition=transition,
        constraints_identified=constraints,
        risks_identified=risks,
        confidence=clamp_confidence(conf),
        status=status,
        evidence=evidence,
        unknowns=unknowns,
    )


def apply_laws_to_context(
    laws: list[UniversalLaw],
    context: str,
    primitives: list[str] | None = None,
    domain: str = "",
) -> list[LawApplication]:
    return [apply_law_to_context(law, context, primitives, domain) for law in laws]


def summarize_law_application(application: LawApplication) -> dict[str, Any]:
    return {
        "law_id": application.law_id,
        "status": application.status.value,
        "confidence": application.confidence,
        "matched_primitives": len(application.applicable_primitives),
        "constraints": len(application.constraints_identified),
        "risks": len(application.risks_identified),
        "unknowns": len(application.unknowns),
    }
