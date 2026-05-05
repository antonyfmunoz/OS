"""Phase 84A polarity synthesis contracts — typed advisory-only polarity integration.

Polarity synthesis identifies third-truth integration patterns for
paradoxically opposed forces. Deterministic rule-based v1.

No execution. No mutation. No adapter calls. No LLM calls.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from umh.ontology.laws import clamp_confidence


class PolaritySynthesisStatus(str, Enum):
    SYNTHESIZED = "synthesized"
    PARTIAL = "partial"
    INSUFFICIENT_DATA = "insufficient_data"
    CONFLICT_UNRESOLVED = "conflict_unresolved"
    INVALID = "invalid"
    UNKNOWN = "unknown"


class PolarityPoleType(str, Enum):
    FORCE = "force"
    VALUE = "value"
    CONSTRAINT = "constraint"
    STRATEGY = "strategy"
    RESOURCE = "resource"
    RISK = "risk"
    PRINCIPLE = "principle"
    PERSPECTIVE = "perspective"
    UNKNOWN = "unknown"


class SynthesisConfidence(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    UNKNOWN = "unknown"


def normalize_polarity_synthesis_status(value: str) -> PolaritySynthesisStatus:
    v = value.strip().lower()
    for m in PolaritySynthesisStatus:
        if m.value == v:
            return m
    return PolaritySynthesisStatus.UNKNOWN


def normalize_pole_type(value: str) -> PolarityPoleType:
    v = value.strip().lower()
    for m in PolarityPoleType:
        if m.value == v:
            return m
    return PolarityPoleType.UNKNOWN


def normalize_synthesis_confidence(value: str) -> SynthesisConfidence:
    v = value.strip().lower()
    for m in SynthesisConfidence:
        if m.value == v:
            return m
    return SynthesisConfidence.UNKNOWN


@dataclass
class PolarityPole:
    pole_id: str
    label: str = ""
    pole_type: PolarityPoleType = PolarityPoleType.UNKNOWN
    truth_claim: str = ""
    value_preserved: str = ""
    risk_if_dominant: str = ""
    evidence: list[str] = field(default_factory=list)
    confidence: float = 0.5
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "pole_id": self.pole_id,
            "label": self.label,
            "pole_type": self.pole_type.value,
            "truth_claim": self.truth_claim,
            "value_preserved": self.value_preserved,
            "risk_if_dominant": self.risk_if_dominant,
            "evidence": self.evidence,
            "confidence": self.confidence,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PolarityPole:
        return cls(
            pole_id=data.get("pole_id", f"pole_{uuid.uuid4().hex[:8]}"),
            label=data.get("label", ""),
            pole_type=normalize_pole_type(data.get("pole_type", "unknown")),
            truth_claim=data.get("truth_claim", ""),
            value_preserved=data.get("value_preserved", ""),
            risk_if_dominant=data.get("risk_if_dominant", ""),
            evidence=data.get("evidence", []),
            confidence=clamp_confidence(data.get("confidence", 0.5)),
            metadata=data.get("metadata", {}),
        )


@dataclass
class PolarityPair:
    pair_id: str
    pole_a: PolarityPole = field(default_factory=lambda: PolarityPole(pole_id=""))
    pole_b: PolarityPole = field(default_factory=lambda: PolarityPole(pole_id=""))
    shared_context: str = ""
    contradiction_layer: str = ""
    governing_laws: list[str] = field(default_factory=list)
    constraints: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "pair_id": self.pair_id,
            "pole_a": self.pole_a.to_dict(),
            "pole_b": self.pole_b.to_dict(),
            "shared_context": self.shared_context,
            "contradiction_layer": self.contradiction_layer,
            "governing_laws": self.governing_laws,
            "constraints": self.constraints,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PolarityPair:
        return cls(
            pair_id=data.get("pair_id", f"pair_{uuid.uuid4().hex[:8]}"),
            pole_a=PolarityPole.from_dict(data.get("pole_a", {})),
            pole_b=PolarityPole.from_dict(data.get("pole_b", {})),
            shared_context=data.get("shared_context", ""),
            contradiction_layer=data.get("contradiction_layer", ""),
            governing_laws=data.get("governing_laws", []),
            constraints=data.get("constraints", []),
            metadata=data.get("metadata", {}),
        )


@dataclass
class PolaritySynthesis:
    synthesis_id: str
    pair_id: str = ""
    status: PolaritySynthesisStatus = PolaritySynthesisStatus.UNKNOWN
    higher_order_frame: str = ""
    third_truth: str = ""
    integrated_action_recommendation: str = ""
    preserved_values: list[str] = field(default_factory=list)
    reduced_failure_modes: list[str] = field(default_factory=list)
    remaining_tensions: list[str] = field(default_factory=list)
    confidence: SynthesisConfidence = SynthesisConfidence.UNKNOWN
    warnings: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "synthesis_id": self.synthesis_id,
            "pair_id": self.pair_id,
            "status": self.status.value,
            "higher_order_frame": self.higher_order_frame,
            "third_truth": self.third_truth,
            "integrated_action_recommendation": self.integrated_action_recommendation,
            "preserved_values": self.preserved_values,
            "reduced_failure_modes": self.reduced_failure_modes,
            "remaining_tensions": self.remaining_tensions,
            "confidence": self.confidence.value,
            "warnings": self.warnings,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PolaritySynthesis:
        return cls(
            synthesis_id=data.get("synthesis_id", f"syn_{uuid.uuid4().hex[:8]}"),
            pair_id=data.get("pair_id", ""),
            status=normalize_polarity_synthesis_status(data.get("status", "unknown")),
            higher_order_frame=data.get("higher_order_frame", ""),
            third_truth=data.get("third_truth", ""),
            integrated_action_recommendation=data.get("integrated_action_recommendation", ""),
            preserved_values=data.get("preserved_values", []),
            reduced_failure_modes=data.get("reduced_failure_modes", []),
            remaining_tensions=data.get("remaining_tensions", []),
            confidence=normalize_synthesis_confidence(data.get("confidence", "unknown")),
            warnings=data.get("warnings", []),
            metadata=data.get("metadata", {}),
        )


def create_polarity_pole(
    label: str,
    *,
    pole_type: PolarityPoleType = PolarityPoleType.FORCE,
    truth_claim: str = "",
    value_preserved: str = "",
    risk_if_dominant: str = "",
    evidence: list[str] | None = None,
    confidence: float = 0.5,
    metadata: dict[str, Any] | None = None,
) -> PolarityPole:
    return PolarityPole(
        pole_id=f"pole_{uuid.uuid4().hex[:8]}",
        label=label,
        pole_type=pole_type,
        truth_claim=truth_claim,
        value_preserved=value_preserved,
        risk_if_dominant=risk_if_dominant,
        evidence=evidence or [],
        confidence=clamp_confidence(confidence),
        metadata=metadata or {},
    )


def create_polarity_pair(
    pole_a: PolarityPole,
    pole_b: PolarityPole,
    *,
    shared_context: str = "",
    contradiction_layer: str = "",
    governing_laws: list[str] | None = None,
    constraints: list[str] | None = None,
    metadata: dict[str, Any] | None = None,
) -> PolarityPair:
    return PolarityPair(
        pair_id=f"pair_{uuid.uuid4().hex[:8]}",
        pole_a=pole_a,
        pole_b=pole_b,
        shared_context=shared_context,
        contradiction_layer=contradiction_layer,
        governing_laws=governing_laws or [],
        constraints=constraints or [],
        metadata=metadata or {},
    )


_KNOWN_SYNTHESES: dict[tuple[str, str], dict[str, str]] = {
    ("speed", "safety"): {
        "frame": "governed execution",
        "third_truth": "governed acceleration",
        "recommendation": "Apply safety gates at decision boundaries, not on every operation",
    },
    ("autonomy", "control"): {
        "frame": "bounded agency",
        "third_truth": "bounded autonomy",
        "recommendation": "Define authority levels and escalation boundaries",
    },
    ("simplicity", "complexity"): {
        "frame": "layered disclosure",
        "third_truth": "progressive disclosure",
        "recommendation": "Simple interface with discoverable depth",
    },
    ("local first", "cloud availability"): {
        "frame": "environment-explicit routing",
        "third_truth": "environment-explicit runtime routing",
        "recommendation": "Route based on declared environment, not assumed connectivity",
    },
    ("stability", "adaptation"): {
        "frame": "dynamic equilibrium",
        "third_truth": "adaptive stability / homeostasis",
        "recommendation": "Stable core with bounded adaptation at edges",
    },
    ("exploration", "exploitation"): {
        "frame": "staged resource allocation",
        "third_truth": "staged exploration with exploitation gates",
        "recommendation": "Explore with time/resource bounds, exploit validated patterns",
    },
    ("human creativity", "machine execution"): {
        "frame": "augmented intention",
        "third_truth": "governed AI leverage of human intention",
        "recommendation": "Human sets intention and constraints, machine executes within them",
    },
    ("individual sovereignty", "collective context"): {
        "frame": "differentiated agency",
        "third_truth": "differentiated agency inside shared reality",
        "recommendation": "Individual boundaries respected within shared systemic context",
    },
}


def _normalize_label(label: str) -> str:
    return label.strip().lower().replace("_", " ").replace("-", " ")


def synthesize_polarity(pair: PolarityPair) -> PolaritySynthesis:
    sid = f"syn_{uuid.uuid4().hex[:8]}"
    warnings: list[str] = []

    if not pair.pole_a.truth_claim:
        return PolaritySynthesis(
            synthesis_id=sid,
            pair_id=pair.pair_id,
            status=PolaritySynthesisStatus.INSUFFICIENT_DATA,
            warnings=["Pole A missing truth_claim"],
            confidence=SynthesisConfidence.LOW,
        )
    if not pair.pole_b.truth_claim:
        return PolaritySynthesis(
            synthesis_id=sid,
            pair_id=pair.pair_id,
            status=PolaritySynthesisStatus.INSUFFICIENT_DATA,
            warnings=["Pole B missing truth_claim"],
            confidence=SynthesisConfidence.LOW,
        )

    label_a = _normalize_label(pair.pole_a.label)
    label_b = _normalize_label(pair.pole_b.label)
    key = (label_a, label_b)
    key_rev = (label_b, label_a)

    known = _KNOWN_SYNTHESES.get(key) or _KNOWN_SYNTHESES.get(key_rev)

    if not pair.contradiction_layer:
        warnings.append("Missing contradiction_layer")

    preserved_values: list[str] = []
    if pair.pole_a.value_preserved:
        preserved_values.append(pair.pole_a.value_preserved)
    if pair.pole_b.value_preserved:
        preserved_values.append(pair.pole_b.value_preserved)

    reduced_failure_modes: list[str] = []
    if pair.pole_a.risk_if_dominant:
        reduced_failure_modes.append(f"Avoids: {pair.pole_a.risk_if_dominant}")
    if pair.pole_b.risk_if_dominant:
        reduced_failure_modes.append(f"Avoids: {pair.pole_b.risk_if_dominant}")

    if known:
        status = PolaritySynthesisStatus.SYNTHESIZED
        if not pair.contradiction_layer:
            status = PolaritySynthesisStatus.PARTIAL
        return PolaritySynthesis(
            synthesis_id=sid,
            pair_id=pair.pair_id,
            status=status,
            higher_order_frame=known["frame"],
            third_truth=known["third_truth"],
            integrated_action_recommendation=known["recommendation"],
            preserved_values=preserved_values,
            reduced_failure_modes=reduced_failure_modes,
            remaining_tensions=[
                "Context-specific tradeoffs remain",
                "Boundary placement requires domain judgment",
            ],
            confidence=SynthesisConfidence.HIGH
            if pair.contradiction_layer
            else SynthesisConfidence.MEDIUM,
            warnings=warnings,
        )

    ctx = pair.shared_context or "the shared domain"
    generic_third = (
        f"Both poles preserve partial truth within {ctx}; synthesis requires "
        f"a higher-order frame that preserves both values while reducing "
        f"dominance risks."
    )
    frame = f"integration of {label_a} and {label_b}"

    status = PolaritySynthesisStatus.PARTIAL
    if not pair.contradiction_layer:
        status = PolaritySynthesisStatus.INSUFFICIENT_DATA
        warnings.append("Cannot determine synthesis without contradiction_layer")

    return PolaritySynthesis(
        synthesis_id=sid,
        pair_id=pair.pair_id,
        status=status,
        higher_order_frame=frame,
        third_truth=generic_third,
        integrated_action_recommendation=(
            "Identify the higher-order frame that contains both poles and act from there"
        ),
        preserved_values=preserved_values,
        reduced_failure_modes=reduced_failure_modes,
        remaining_tensions=[
            "Generic synthesis — domain-specific reasoning needed",
            "Known pattern library does not cover this polarity",
        ],
        confidence=SynthesisConfidence.LOW,
        warnings=warnings,
    )
