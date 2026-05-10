"""Brain profile + expression state — the identity and epigenetic layer.

A BrainProfile is a persistent identity/view over the shared substrate.
It is NOT a separate database. It determines which primitives are active,
what authority level the brain has, and what scope it operates in.

ExpressionState is the brain's runtime epigenetic configuration —
amplified/silenced concepts, preferred patterns, learned corrections.
Corrections apply to expression state ONLY, never to the canonical
substrate/world model.

Together: BrainProfile + ExpressionState = complete brain configuration.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum, unique
from typing import Any

from umh.core.clock import iso_now as _iso_now


# ─── Authority levels ────────────────────────────────────────────────────


@unique
class AuthorityLevel(str, Enum):
    OBSERVE = "observe"
    ADVISE = "advise"
    PROPOSE = "propose"
    APPROVE = "approve"
    EXECUTE = "execute"
    ADMIN = "admin"


# Compatibility aliases for 11C context injector
OBSERVER = AuthorityLevel.OBSERVE
ADVISOR = AuthorityLevel.ADVISE
EXECUTOR = AuthorityLevel.EXECUTE
GOVERNOR = AuthorityLevel.ADMIN


# ─── Weight clamping ─────────────────────────────────────────────────────

_MIN_WEIGHT = 0.0
_MAX_WEIGHT = 1.0


def _clamp(val: float) -> float:
    return max(_MIN_WEIGHT, min(_MAX_WEIGHT, val))


# ─── BrainProfile ────────────────────────────────────────────────────────


@dataclass(frozen=True)
class BrainProfile:
    """Persistent identity and configuration of a brain instance.

    Frozen — mutations require creating a new profile.
    No execute(), run_tool(), or adapter methods by design.
    """

    brain_id: str
    name: str
    brain_type: str = "system"
    parent_brain_id: str | None = None
    scope: dict[str, Any] = field(default_factory=dict)
    authority: AuthorityLevel = AuthorityLevel.ADVISE
    active_primitives: tuple[str, ...] = ()
    retrieval_weights: dict[str, float] = field(default_factory=dict)
    tool_permissions: tuple[str, ...] = ()
    created_at: str = ""
    updated_at: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    # 11C compatibility — kept as optional overlay fields
    amplified_concepts: frozenset[str] = frozenset()
    silenced_concepts: frozenset[str] = frozenset()
    preferred_patterns: tuple[str, ...] = ()

    def __post_init__(self):
        if not self.brain_id:
            raise ValueError("brain_id must not be empty")
        if not self.name:
            raise ValueError("name must not be empty")
        if not self.created_at:
            object.__setattr__(self, "created_at", _iso_now())
        if not self.updated_at:
            object.__setattr__(self, "updated_at", self.created_at)

    def to_dict(self) -> dict[str, Any]:
        return {
            "brain_id": self.brain_id,
            "name": self.name,
            "brain_type": self.brain_type,
            "parent_brain_id": self.parent_brain_id,
            "scope": self.scope,
            "authority": self.authority.value,
            "active_primitives": list(self.active_primitives),
            "retrieval_weights": self.retrieval_weights,
            "tool_permissions": list(self.tool_permissions),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "metadata": self.metadata,
            "amplified_concepts": sorted(self.amplified_concepts),
            "silenced_concepts": sorted(self.silenced_concepts),
            "preferred_patterns": list(self.preferred_patterns),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> BrainProfile:
        authority = data.get("authority", "advise")
        if isinstance(authority, str):
            authority = AuthorityLevel(authority)
        return cls(
            brain_id=data["brain_id"],
            name=data["name"],
            brain_type=data.get("brain_type", "system"),
            parent_brain_id=data.get("parent_brain_id"),
            scope=data.get("scope", {}),
            authority=authority,
            active_primitives=tuple(data.get("active_primitives", ())),
            retrieval_weights=data.get("retrieval_weights", {}),
            tool_permissions=tuple(data.get("tool_permissions", ())),
            created_at=data.get("created_at", ""),
            updated_at=data.get("updated_at", ""),
            metadata=data.get("metadata", {}),
            amplified_concepts=frozenset(data.get("amplified_concepts", ())),
            silenced_concepts=frozenset(data.get("silenced_concepts", ())),
            preferred_patterns=tuple(data.get("preferred_patterns", ())),
        )


# ─── ExpressionState ─────────────────────────────────────────────────────


@dataclass
class ExpressionState:
    """Runtime epigenetic configuration of a brain.

    Corrections apply here, not to the substrate. Weights are clamped
    to [0.0, 1.0]. checkpoint_version increments on every mutation.
    """

    brain_id: str
    amplified_concepts: dict[str, float] = field(default_factory=dict)
    silenced_concepts: dict[str, float] = field(default_factory=dict)
    preferred_patterns: dict[str, float] = field(default_factory=dict)
    learned_corrections: list[dict[str, Any]] = field(default_factory=list)
    checkpoint_version: int = 0
    inherited_from: str | None = None
    updated_at: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    # 11C compatibility fields
    concept_weights: dict[str, float] = field(default_factory=dict)
    suppressed_intents: set[str] = field(default_factory=set)
    pattern_bias: dict[str, float] = field(default_factory=dict)
    recent_activations: list[str] = field(default_factory=list)

    def __post_init__(self):
        if not self.updated_at:
            self.updated_at = _iso_now()

    def to_dict(self) -> dict[str, Any]:
        return {
            "brain_id": self.brain_id,
            "amplified_concepts": self.amplified_concepts,
            "silenced_concepts": self.silenced_concepts,
            "preferred_patterns": self.preferred_patterns,
            "learned_corrections": self.learned_corrections[-20:],
            "checkpoint_version": self.checkpoint_version,
            "inherited_from": self.inherited_from,
            "updated_at": self.updated_at,
            "concept_weights": self.concept_weights,
            "suppressed_intents": sorted(self.suppressed_intents),
            "pattern_bias": self.pattern_bias,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ExpressionState:
        return cls(
            brain_id=data["brain_id"],
            amplified_concepts=data.get("amplified_concepts", {}),
            silenced_concepts=data.get("silenced_concepts", {}),
            preferred_patterns=data.get("preferred_patterns", {}),
            learned_corrections=data.get("learned_corrections", []),
            checkpoint_version=data.get("checkpoint_version", 0),
            inherited_from=data.get("inherited_from"),
            updated_at=data.get("updated_at", ""),
            metadata=data.get("metadata", {}),
            concept_weights=data.get("concept_weights", {}),
            suppressed_intents=set(data.get("suppressed_intents", [])),
            pattern_bias=data.get("pattern_bias", {}),
        )

    @classmethod
    def inherit(cls, parent: ExpressionState, child_brain_id: str) -> ExpressionState:
        """Create child expression state inheriting from parent."""
        return cls(
            brain_id=child_brain_id,
            amplified_concepts=dict(parent.amplified_concepts),
            silenced_concepts=dict(parent.silenced_concepts),
            preferred_patterns=dict(parent.preferred_patterns),
            learned_corrections=[],
            checkpoint_version=0,
            inherited_from=parent.brain_id,
            concept_weights=dict(parent.concept_weights),
            suppressed_intents=set(parent.suppressed_intents),
            pattern_bias=dict(parent.pattern_bias),
        )

    def amplify(self, concept: str, weight: float) -> None:
        self.amplified_concepts[concept] = _clamp(weight)
        self.silenced_concepts.pop(concept, None)
        self.checkpoint_version += 1
        self.updated_at = _iso_now()

    def silence(self, concept: str, weight: float) -> None:
        self.silenced_concepts[concept] = _clamp(weight)
        self.amplified_concepts.pop(concept, None)
        self.checkpoint_version += 1
        self.updated_at = _iso_now()

    def prefer_pattern(self, pattern: str, weight: float) -> None:
        self.preferred_patterns[pattern] = _clamp(weight)
        self.checkpoint_version += 1
        self.updated_at = _iso_now()

    def apply_correction(self, correction: dict[str, Any]) -> None:
        """Apply an epigenetic correction — modifies expression only.

        Correction dict should contain at minimum: 'type' and 'value'.
        Optional: 'reason', 'scope', 'source', 'timestamp'.
        """
        correction.setdefault("timestamp", _iso_now())

        ctype = correction.get("type", "")
        value = correction.get("value", {})

        if ctype == "amplify" and isinstance(value, dict):
            for concept, weight in value.items():
                self.amplify(concept, float(weight))
        elif ctype == "silence" and isinstance(value, dict):
            for concept, weight in value.items():
                self.silence(concept, float(weight))
        elif ctype == "prefer_pattern" and isinstance(value, dict):
            for pattern, weight in value.items():
                self.prefer_pattern(pattern, float(weight))

        self.learned_corrections.append(correction)
        self.checkpoint_version += 1
        self.updated_at = _iso_now()
