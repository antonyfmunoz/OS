"""Phase 85 ontology bridge — connect council to polarity synthesis and laws.

When a deliberation request references laws or polar tensions,
this module provides typed bridge functions. Advisory only.

No execution. No mutation. No adapter calls. No LLM calls.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from umh.council.contracts import _council_id


@dataclass
class OntologyContext:
    context_id: str = ""
    request_id: str = ""
    matched_laws: list[dict[str, Any]] = field(default_factory=list)
    polarity_syntheses: list[dict[str, Any]] = field(default_factory=list)
    unity_relevant: bool = False
    warnings: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "context_id": self.context_id,
            "request_id": self.request_id,
            "matched_laws": self.matched_laws,
            "polarity_syntheses": self.polarity_syntheses,
            "unity_relevant": self.unity_relevant,
            "warnings": self.warnings,
            "metadata": self.metadata,
        }


def resolve_ontology_context(
    request_id: str,
    relevant_laws: list[str] | None = None,
    relevant_polarities: list[str] | None = None,
) -> OntologyContext:
    warnings: list[str] = []
    matched_laws: list[dict[str, Any]] = []
    polarity_syntheses: list[dict[str, Any]] = []
    unity_relevant = False

    if relevant_laws:
        try:
            from umh.ontology.laws import get_law_by_id

            for law_ref in relevant_laws:
                law = get_law_by_id(law_ref)
                if law:
                    matched_laws.append({"law_id": law.law_id, "name": law.name})
                    ln = getattr(law, "law_name", None)
                    lnv = ln.value if hasattr(ln, "value") else str(ln or "")
                    if lnv == "unity_oneness":
                        unity_relevant = True
                else:
                    warnings.append(f"Law not found: {law_ref}")
        except ImportError:
            warnings.append("Ontology laws module not available")

    if relevant_polarities:
        try:
            from umh.ontology.polarity_synthesis import (
                PolarityPoleType,
                create_polarity_pair,
                create_polarity_pole,
                synthesize_polarity,
            )

            for i in range(0, len(relevant_polarities) - 1, 2):
                label_a = relevant_polarities[i]
                label_b = relevant_polarities[i + 1] if i + 1 < len(relevant_polarities) else ""
                if not label_b:
                    break
                pa = create_polarity_pole(label_a, truth_claim=f"{label_a} matters")
                pb = create_polarity_pole(label_b, truth_claim=f"{label_b} matters")
                pair = create_polarity_pair(pa, pb, shared_context="deliberation")
                result = synthesize_polarity(pair)
                polarity_syntheses.append(result.to_dict())
        except ImportError:
            warnings.append("Polarity synthesis module not available")

    return OntologyContext(
        context_id=_council_id("octx"),
        request_id=request_id,
        matched_laws=matched_laws,
        polarity_syntheses=polarity_syntheses,
        unity_relevant=unity_relevant,
        warnings=warnings,
    )
