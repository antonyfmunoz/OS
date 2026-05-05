"""Phase 81 ontology views — UI-safe read models for ontology data.

No sensitive data exposed. No execution. No mutation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from umh.core.clock import iso_now as _iso_now


@dataclass
class PrimitiveView:
    primitive_id: str
    name: str = ""
    primitive_type: str = ""
    abstraction_level: str = ""
    scope: str = ""
    confidence: float = 0.0
    examples_count: int = 0
    tags: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "primitive_id": self.primitive_id,
            "name": self.name,
            "primitive_type": self.primitive_type,
            "abstraction_level": self.abstraction_level,
            "scope": self.scope,
            "confidence": self.confidence,
            "examples_count": self.examples_count,
            "tags": self.tags,
            "metadata": self.metadata,
        }


@dataclass
class LawView:
    law_id: str
    name: str = ""
    law_name: str = ""
    law_type: str = ""
    scope: str = ""
    governs: list[str] = field(default_factory=list)
    applies_to_primitives: list[str] = field(default_factory=list)
    confidence: float = 0.0
    examples_count: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "law_id": self.law_id,
            "name": self.name,
            "law_name": self.law_name,
            "law_type": self.law_type,
            "scope": self.scope,
            "governs": self.governs,
            "applies_to_primitives": self.applies_to_primitives,
            "confidence": self.confidence,
            "examples_count": self.examples_count,
            "metadata": self.metadata,
        }


@dataclass
class DomainProjectionView:
    domain: str = ""
    primitive_projection_count: int = 0
    law_projection_count: int = 0
    constraints_count: int = 0
    confidence: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "domain": self.domain,
            "primitive_projection_count": self.primitive_projection_count,
            "law_projection_count": self.law_projection_count,
            "constraints_count": self.constraints_count,
            "confidence": self.confidence,
            "metadata": self.metadata,
        }


@dataclass
class CorrespondenceView:
    map_id: str = ""
    source_domain: str = ""
    target_domain: str = ""
    status: str = ""
    confidence: float = 0.0
    shared_primitives_count: int = 0
    shared_laws_count: int = 0
    analogy_breaks_count: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "map_id": self.map_id,
            "source_domain": self.source_domain,
            "target_domain": self.target_domain,
            "status": self.status,
            "confidence": self.confidence,
            "shared_primitives_count": self.shared_primitives_count,
            "shared_laws_count": self.shared_laws_count,
            "analogy_breaks_count": self.analogy_breaks_count,
            "metadata": self.metadata,
        }


@dataclass
class PolaritySynthesisView:
    synthesis_id: str = ""
    status: str = ""
    higher_order_frame: str = ""
    third_truth: str = ""
    confidence: str = ""
    preserved_values_count: int = 0
    remaining_tensions_count: int = 0
    warnings: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "synthesis_id": self.synthesis_id,
            "status": self.status,
            "higher_order_frame": self.higher_order_frame,
            "third_truth": self.third_truth,
            "confidence": self.confidence,
            "preserved_values_count": self.preserved_values_count,
            "remaining_tensions_count": self.remaining_tensions_count,
            "warnings": self.warnings,
            "metadata": self.metadata,
        }


def polarity_synthesis_to_view(s: Any) -> PolaritySynthesisView:
    st = getattr(s, "status", None)
    conf = getattr(s, "confidence", None)
    return PolaritySynthesisView(
        synthesis_id=getattr(s, "synthesis_id", ""),
        status=st.value if hasattr(st, "value") else str(st or ""),
        higher_order_frame=getattr(s, "higher_order_frame", ""),
        third_truth=getattr(s, "third_truth", ""),
        confidence=conf.value if hasattr(conf, "value") else str(conf or ""),
        preserved_values_count=len(getattr(s, "preserved_values", [])),
        remaining_tensions_count=len(getattr(s, "remaining_tensions", [])),
        warnings=list(getattr(s, "warnings", [])),
    )


@dataclass
class OntologyKernelView:
    generated_at: str = ""
    primitive_count: int = 0
    law_count: int = 0
    domain_projection_count: int = 0
    correspondence_count: int = 0
    validation_status: str = "unknown"
    unity_oneness_present: bool = False
    polarity_synthesis_ready: bool = False
    warnings: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "generated_at": self.generated_at,
            "primitive_count": self.primitive_count,
            "law_count": self.law_count,
            "domain_projection_count": self.domain_projection_count,
            "correspondence_count": self.correspondence_count,
            "validation_status": self.validation_status,
            "unity_oneness_present": self.unity_oneness_present,
            "polarity_synthesis_ready": self.polarity_synthesis_ready,
            "warnings": self.warnings,
            "metadata": self.metadata,
        }


def primitive_to_view(p: Any) -> PrimitiveView:
    return PrimitiveView(
        primitive_id=getattr(p, "primitive_id", ""),
        name=getattr(p, "name", ""),
        primitive_type=getattr(p, "primitive_type", PrimitiveView).value
        if hasattr(getattr(p, "primitive_type", None), "value")
        else str(getattr(p, "primitive_type", "")),
        abstraction_level=getattr(p, "abstraction_level", PrimitiveView).value
        if hasattr(getattr(p, "abstraction_level", None), "value")
        else str(getattr(p, "abstraction_level", "")),
        scope=getattr(p, "scope", PrimitiveView).value
        if hasattr(getattr(p, "scope", None), "value")
        else str(getattr(p, "scope", "")),
        confidence=getattr(p, "confidence", 0.0),
        examples_count=len(getattr(p, "examples", [])),
        tags=list(getattr(p, "tags", [])),
    )


def law_to_view(l: Any) -> LawView:
    ln = getattr(l, "law_name", None)
    lt = getattr(l, "law_type", None)
    sc = getattr(l, "scope", None)
    return LawView(
        law_id=getattr(l, "law_id", ""),
        name=getattr(l, "name", ""),
        law_name=ln.value if hasattr(ln, "value") else str(ln or ""),
        law_type=lt.value if hasattr(lt, "value") else str(lt or ""),
        scope=sc.value if hasattr(sc, "value") else str(sc or ""),
        governs=list(getattr(l, "governs", [])),
        applies_to_primitives=list(getattr(l, "applies_to_primitives", [])),
        confidence=getattr(l, "confidence", 0.0),
        examples_count=len(getattr(l, "examples", [])),
    )


def domain_projection_to_view(ps: Any) -> DomainProjectionView:
    d = getattr(ps, "domain", None)
    return DomainProjectionView(
        domain=d.value if hasattr(d, "value") else str(d or ""),
        primitive_projection_count=len(getattr(ps, "primitive_projections", [])),
        law_projection_count=len(getattr(ps, "law_projections", [])),
        constraints_count=len(getattr(ps, "domain_constraints", [])),
        confidence=getattr(ps, "confidence", 0.0),
    )


def correspondence_to_view(cm: Any) -> CorrespondenceView:
    s = getattr(cm, "status", None)
    return CorrespondenceView(
        map_id=getattr(cm, "map_id", ""),
        source_domain=getattr(cm, "source_domain", ""),
        target_domain=getattr(cm, "target_domain", ""),
        status=s.value if hasattr(s, "value") else str(s or ""),
        confidence=getattr(cm, "confidence", 0.0),
        shared_primitives_count=len(getattr(cm, "shared_primitives", [])),
        shared_laws_count=len(getattr(cm, "shared_laws", [])),
        analogy_breaks_count=len(getattr(cm, "analogy_breaks", [])),
    )


def build_ontology_kernel_view(
    primitives: list[Any] | None = None,
    laws: list[Any] | None = None,
    projections: list[Any] | None = None,
    correspondences: list[Any] | None = None,
    validation_result: Any | None = None,
) -> OntologyKernelView:
    warnings: list[str] = []
    val_status = "unknown"

    if validation_result is not None:
        val_status = "valid" if getattr(validation_result, "valid", False) else "invalid"
        warnings.extend(getattr(validation_result, "warnings", []))

    unity_present = False
    if laws:
        for law in laws:
            ln = getattr(law, "law_name", None)
            lnv = ln.value if hasattr(ln, "value") else str(ln or "")
            if lnv == "unity_oneness":
                unity_present = True
                break

    synthesis_ready = False
    try:
        from umh.ontology.polarity_synthesis import PolaritySynthesisStatus  # noqa: F401

        synthesis_ready = True
    except ImportError:
        pass

    return OntologyKernelView(
        generated_at=_iso_now(),
        primitive_count=len(primitives) if primitives else 0,
        law_count=len(laws) if laws else 0,
        domain_projection_count=len(projections) if projections else 0,
        correspondence_count=len(correspondences) if correspondences else 0,
        validation_status=val_status,
        unity_oneness_present=unity_present,
        polarity_synthesis_ready=synthesis_ready,
        warnings=warnings,
    )
