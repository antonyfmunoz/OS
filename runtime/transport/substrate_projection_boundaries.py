"""
UMH/EOS boundary enforcement for Phase 94D.4.

UMH = Universal Meta Harness = substrate / intelligence infrastructure.
EOS = EntrepreneurOS = business SaaS/domain projection powered by UMH.

Everything above primitives/laws is a projection, specialization,
interface, instantiation, or execution surface.

Text saying "EOS is the substrate" should be flagged.
Text saying "EOS is powered by UMH" should be valid.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class ComponentBoundary(str, Enum):
    UMH_SUBSTRATE = "umh_substrate"
    PROJECTION = "projection"
    AMBIGUOUS = "ambiguous"


UMH_SUBSTRATE_TERMS: frozenset[str] = frozenset(
    {
        "umh",
        "universal meta harness",
        "substrate",
        "execution spine",
        "governance engine",
        "authority engine",
        "cognitive loop",
        "primitives",
        "laws",
        "ritual",
        "station",
        "station daemon",
        "station bus",
        "node registry",
        "topology",
        "capability routing",
        "worker runtime",
        "governance gate",
        "message bus",
        "advisor session",
        "interface projection",
        "control plane",
        "execution fabric",
        "meta harness",
    }
)

EOS_PROJECTION_TERMS: frozenset[str] = frozenset(
    {
        "eos",
        "entrepreneuros",
        "entrepenuros",
        "business os",
        "business operating system",
        "saas",
        "initiate arena",
        "game of lyfe",
        "lyfe institute",
        "empyrean studio",
        "portfolio advisor",
        "morning brief",
        "daily cycle",
        "venture management",
        "lead pipeline",
        "crm",
        "content calendar",
    }
)

PROJECTION_TERMS: frozenset[str] = frozenset(
    {
        "lyfeos",
        "creatoros",
        "lyfe os",
        "creator os",
        "personal os",
        "distribution platform",
        "audience platform",
        "human optimization",
    }
)


@dataclass
class BoundaryClassification:
    name: str
    boundary: ComponentBoundary
    reason: str


def classify_component_boundary(
    name: str,
    path: str = "",
    description: str = "",
) -> BoundaryClassification:
    """Classify a component as UMH substrate or projection."""
    combined = f"{name} {path} {description}".lower()

    if path:
        path_lower = path.lower()
        if "eos_ai/substrate/" in path_lower or "runtime/substrate/" in path_lower or "runtime/transport/" in path_lower:
            return BoundaryClassification(
                name=name,
                boundary=ComponentBoundary.UMH_SUBSTRATE,
                reason="Located in substrate package",
            )
        if "saas/" in path_lower or "services/discord" in path_lower:
            return BoundaryClassification(
                name=name,
                boundary=ComponentBoundary.PROJECTION,
                reason="Located in projection/service package",
            )

    name_lower = name.lower()
    for term in UMH_SUBSTRATE_TERMS:
        if term in name_lower:
            return BoundaryClassification(
                name=name,
                boundary=ComponentBoundary.UMH_SUBSTRATE,
                reason=f"Matches substrate term: {term}",
            )

    for term in EOS_PROJECTION_TERMS:
        if term in name_lower:
            return BoundaryClassification(
                name=name,
                boundary=ComponentBoundary.PROJECTION,
                reason=f"Matches projection term: {term}",
            )

    for term in PROJECTION_TERMS:
        if term in name_lower:
            return BoundaryClassification(
                name=name,
                boundary=ComponentBoundary.PROJECTION,
                reason=f"Matches projection term: {term}",
            )

    return BoundaryClassification(
        name=name,
        boundary=ComponentBoundary.AMBIGUOUS,
        reason="Could not classify — review needed",
    )


_CONFUSION_PATTERNS: list[tuple[str, str]] = [
    ("eos is the substrate", "EOS is a projection, not the substrate. UMH is the substrate."),
    ("eos is substrate", "EOS is a projection, not the substrate. UMH is the substrate."),
    ("entrepreneuros is the substrate", "EntrepreneurOS is a projection powered by UMH substrate."),
    ("eos substrate layer", "The substrate layer is UMH, not EOS. EOS is a projection."),
    ("eos powers umh", "UMH powers EOS, not the reverse."),
    ("entrepreneuros powers umh", "UMH powers EntrepreneurOS, not the reverse."),
]

_VALID_PATTERNS: list[str] = [
    "eos is powered by umh",
    "eos is a projection",
    "eos is a saas",
    "eos is a business execution",
    "eos is a domain projection",
    "entrepreneuros is powered by",
    "umh is the substrate",
    "umh powers eos",
    "umh substrate",
    "eos projection",
    "lyfeos is a projection",
    "creatoros is a projection",
]


def detect_umh_eos_confusion(text: str) -> list[str]:
    """Detect statements that collapse EOS into UMH or reverse the relationship.

    Returns list of warning messages. Empty list means no confusion detected.
    """
    warnings: list[str] = []
    text_lower = text.lower()
    for pattern, warning in _CONFUSION_PATTERNS:
        if pattern in text_lower:
            warnings.append(warning)
    return warnings


def validate_boundary_statement(text: str) -> bool:
    """Check if a statement correctly describes UMH/EOS boundary.

    Returns True if the statement is valid (no confusion detected).
    """
    text_lower = text.lower()

    for pattern, _ in _CONFUSION_PATTERNS:
        if pattern in text_lower:
            return False

    for valid in _VALID_PATTERNS:
        if valid in text_lower:
            return True

    return True
