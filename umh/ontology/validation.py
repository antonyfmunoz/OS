"""Phase 81 ontology validation — structural checks for primitives, laws, projections.

No execution. No mutation. No adapter calls. No LLM calls.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any

from umh.ontology.domain_projection import DomainProjectionSet
from umh.ontology.laws import DomainLawProjection, LawScope, UniversalLaw
from umh.ontology.primitives import (
    PrimitiveProjection,
    PrimitiveScope,
    UniversalPrimitive,
)


@dataclass
class OntologyValidationIssue:
    issue_id: str
    severity: str = "warning"
    target_id: str = ""
    target_type: str = ""
    message: str = ""
    law_or_primitive_ref: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "issue_id": self.issue_id,
            "severity": self.severity,
            "target_id": self.target_id,
            "target_type": self.target_type,
            "message": self.message,
            "law_or_primitive_ref": self.law_or_primitive_ref,
            "metadata": self.metadata,
        }


@dataclass
class OntologyValidationResult:
    valid: bool = True
    issues: list[OntologyValidationIssue] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    checked_primitives: int = 0
    checked_laws: int = 0
    checked_projections: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "valid": self.valid,
            "issues": [i.to_dict() for i in self.issues],
            "warnings": self.warnings,
            "checked_primitives": self.checked_primitives,
            "checked_laws": self.checked_laws,
            "checked_projections": self.checked_projections,
            "metadata": self.metadata,
        }


def _issue(
    severity: str, target_id: str, target_type: str, message: str, ref: str = ""
) -> OntologyValidationIssue:
    return OntologyValidationIssue(
        issue_id=f"vi_{uuid.uuid4().hex[:8]}",
        severity=severity,
        target_id=target_id,
        target_type=target_type,
        message=message,
        law_or_primitive_ref=ref,
    )


def validate_universal_primitive(primitive: UniversalPrimitive) -> list[OntologyValidationIssue]:
    issues: list[OntologyValidationIssue] = []
    pid = primitive.primitive_id

    if not primitive.definition:
        issues.append(_issue("error", pid, "primitive", "Missing definition"))
    if not primitive.evidence_basis:
        issues.append(_issue("warning", pid, "primitive", "Missing evidence_basis"))
    if primitive.abstraction_level.value == "unknown":
        issues.append(_issue("warning", pid, "primitive", "Abstraction level is UNKNOWN"))
    if primitive.scope != PrimitiveScope.UNIVERSAL:
        issues.append(
            _issue(
                "error",
                pid,
                "primitive",
                f"Universal primitive has non-UNIVERSAL scope: {primitive.scope.value}",
            )
        )
    return issues


def validate_universal_law(law: UniversalLaw) -> list[OntologyValidationIssue]:
    issues: list[OntologyValidationIssue] = []
    lid = law.law_id

    if not law.definition:
        issues.append(_issue("error", lid, "law", "Missing definition"))
    if not law.evidence_basis:
        issues.append(_issue("error", lid, "law", "Missing evidence_basis"))
    if not law.failure_conditions:
        issues.append(_issue("error", lid, "law", "Missing failure_conditions"))
    if law.scope != LawScope.UNIVERSAL:
        issues.append(
            _issue("error", lid, "law", f"Universal law has non-UNIVERSAL scope: {law.scope.value}")
        )
    if not law.applies_to_primitives:
        issues.append(_issue("warning", lid, "law", "No applies_to_primitives declared"))
    if not law.state_transition_effect:
        issues.append(_issue("warning", lid, "law", "Missing state_transition_effect"))
    return issues


def validate_primitive_projection(
    projection: PrimitiveProjection,
    primitives: list[UniversalPrimitive],
) -> list[OntologyValidationIssue]:
    issues: list[OntologyValidationIssue] = []
    pid = projection.projection_id
    prim_ids = {p.primitive_id for p in primitives}

    if projection.universal_primitive_id and projection.universal_primitive_id not in prim_ids:
        issues.append(
            _issue(
                "error",
                pid,
                "primitive_projection",
                f"References unknown primitive: {projection.universal_primitive_id}",
            )
        )
    return issues


def validate_law_projection(
    projection: DomainLawProjection,
    laws: list[UniversalLaw],
) -> list[OntologyValidationIssue]:
    issues: list[OntologyValidationIssue] = []
    pid = projection.projection_id
    law_ids = {l.law_id for l in laws}

    if projection.universal_law_id and projection.universal_law_id not in law_ids:
        issues.append(
            _issue(
                "error",
                pid,
                "law_projection",
                f"References unknown law: {projection.universal_law_id}",
            )
        )
    return issues


def validate_no_domain_projection_marked_universal(
    projection_sets: list[DomainProjectionSet],
) -> list[OntologyValidationIssue]:
    issues: list[OntologyValidationIssue] = []
    for ps in projection_sets:
        if ps.domain.value == "unknown":
            continue
        for pp in ps.primitive_projections:
            if hasattr(pp, "scope") and getattr(pp, "scope", None) == PrimitiveScope.UNIVERSAL:
                issues.append(
                    _issue(
                        "error",
                        pp.projection_id,
                        "primitive_projection",
                        "Domain projection claims UNIVERSAL scope",
                    )
                )
    return issues


def validate_law_has_scope_evidence_failure_conditions(
    law: UniversalLaw,
) -> list[OntologyValidationIssue]:
    issues: list[OntologyValidationIssue] = []
    lid = law.law_id
    if law.scope.value == "unknown":
        issues.append(_issue("error", lid, "law", "Law scope is UNKNOWN"))
    if not law.evidence_basis:
        issues.append(_issue("error", lid, "law", "Law missing evidence_basis"))
    if not law.failure_conditions:
        issues.append(_issue("error", lid, "law", "Law missing failure_conditions"))
    return issues


def validate_domain_projection_set(
    projection_set: DomainProjectionSet,
    primitives: list[UniversalPrimitive],
    laws: list[UniversalLaw],
) -> list[OntologyValidationIssue]:
    issues: list[OntologyValidationIssue] = []
    for pp in projection_set.primitive_projections:
        issues.extend(validate_primitive_projection(pp, primitives))
    for lp in projection_set.law_projections:
        issues.extend(validate_law_projection(lp, laws))
    issues.extend(validate_no_domain_projection_marked_universal([projection_set]))
    return issues


def validate_polarity_pole(pole: Any) -> list[OntologyValidationIssue]:
    issues: list[OntologyValidationIssue] = []
    pid = getattr(pole, "pole_id", "unknown")
    if not getattr(pole, "truth_claim", ""):
        issues.append(_issue("error", pid, "polarity_pole", "Missing truth_claim"))
    if not getattr(pole, "label", ""):
        issues.append(_issue("warning", pid, "polarity_pole", "Missing label"))
    return issues


def validate_polarity_pair(pair: Any) -> list[OntologyValidationIssue]:
    issues: list[OntologyValidationIssue] = []
    pid = getattr(pair, "pair_id", "unknown")
    pole_a = getattr(pair, "pole_a", None)
    pole_b = getattr(pair, "pole_b", None)
    if pole_a:
        issues.extend(validate_polarity_pole(pole_a))
    else:
        issues.append(_issue("error", pid, "polarity_pair", "Missing pole_a"))
    if pole_b:
        issues.extend(validate_polarity_pole(pole_b))
    else:
        issues.append(_issue("error", pid, "polarity_pair", "Missing pole_b"))
    if not getattr(pair, "contradiction_layer", ""):
        issues.append(_issue("warning", pid, "polarity_pair", "Missing contradiction_layer"))
    return issues


def validate_polarity_synthesis(synthesis: Any) -> list[OntologyValidationIssue]:
    issues: list[OntologyValidationIssue] = []
    sid = getattr(synthesis, "synthesis_id", "unknown")
    if not getattr(synthesis, "higher_order_frame", ""):
        issues.append(_issue("warning", sid, "polarity_synthesis", "Missing higher_order_frame"))
    if not getattr(synthesis, "third_truth", ""):
        issues.append(_issue("warning", sid, "polarity_synthesis", "Missing third_truth"))
    return issues


def validate_ontology_kernel(
    primitives: list[UniversalPrimitive],
    laws: list[UniversalLaw],
    projection_sets: list[DomainProjectionSet] | None = None,
) -> OntologyValidationResult:
    issues: list[OntologyValidationIssue] = []
    warnings: list[str] = []

    for p in primitives:
        issues.extend(validate_universal_primitive(p))
    for l in laws:
        issues.extend(validate_universal_law(l))
        issues.extend(validate_law_has_scope_evidence_failure_conditions(l))

    proj_count = 0
    if projection_sets:
        for ps in projection_sets:
            issues.extend(validate_domain_projection_set(ps, primitives, laws))
            proj_count += len(ps.primitive_projections) + len(ps.law_projections)

    errors = [i for i in issues if i.severity == "error"]
    for i in issues:
        if i.severity == "warning":
            warnings.append(f"{i.target_type}:{i.target_id} — {i.message}")

    return OntologyValidationResult(
        valid=len(errors) == 0,
        issues=issues,
        warnings=warnings,
        checked_primitives=len(primitives),
        checked_laws=len(laws),
        checked_projections=proj_count,
    )
