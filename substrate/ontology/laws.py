"""Governing laws for the UMH substrate.

Laws are constraints that the substrate enforces. They are loaded once
at boot and checked by the GovernanceEngine during signal classification.

The canonical law definitions live in services/umh/foundation/laws.py
as Pydantic models. This module provides a lightweight registry that
merges those foundation laws with the spec's 8 invariants into a single
list-of-dicts interface for governance checks.
"""

from __future__ import annotations


def get_laws() -> list[dict[str, str]]:
    """Return the governing laws registry.

    Returns a merged set of laws:
    - The 6 foundation laws from services/umh/foundation/laws.py
    - The 8 spec invariants (some overlap, deduplicated by name)

    Each law dict has: name, description, enforcement.
    """
    # Spec invariants — the minimum set from ARCHITECTURE.md
    _SPEC_LAWS: list[dict[str, str]] = [
        {
            "name": "identity_before_execution",
            "description": "Every execution must resolve identity first",
            "enforcement": "hard",
        },
        {
            "name": "governance_before_action",
            "description": "No adapter call without governance classification",
            "enforcement": "hard",
        },
        {
            "name": "trace_everything",
            "description": "Every execution produces a trace record",
            "enforcement": "hard",
        },
        {
            "name": "feedback_closes_loops",
            "description": "Every trace gets a feedback record",
            "enforcement": "hard",
        },
        {
            "name": "registry_is_truth",
            "description": "Unregistered components do not exist to the substrate",
            "enforcement": "hard",
        },
        {
            "name": "memory_discipline",
            "description": "No direct Neon writes outside state/",
            "enforcement": "hard",
        },
        {
            "name": "deterministic_first",
            "description": "Every LLM call has a deterministic fallback",
            "enforcement": "hard",
        },
        {
            "name": "pydantic_only",
            "description": "No runtime dataclasses in substrate/",
            "enforcement": "hard",
        },
    ]

    # Foundation laws from services/umh/foundation/laws.py, translated
    # to the same dict shape. These represent the substrate's own
    # operational constraints.
    _FOUNDATION_LAWS: list[dict[str, str]] = [
        {
            "name": "signal_intake",
            "description": "All external input enters the substrate exclusively through the signal intake pathway",
            "enforcement": "hard",
        },
        {
            "name": "no_direct_execution",
            "description": "No execution may occur without a governance decision",
            "enforcement": "hard",
        },
        {
            "name": "adapter_mediation",
            "description": "All interaction with external systems must be mediated by the adapter protocol",
            "enforcement": "hard",
        },
        {
            "name": "memory_pathway",
            "description": "All durable state writes must go through the memory candidate/update pathway",
            "enforcement": "hard",
        },
        {
            "name": "traceability",
            "description": "Every execution must produce a trace. Untraceable operations are illegal",
            "enforcement": "hard",
        },
        {
            "name": "epistemic_humility",
            "description": "The substrate must track confidence and uncertainty",
            "enforcement": "soft",
        },
    ]

    # Merge: spec laws first, then foundation laws (skip duplicates by name)
    seen: set[str] = set()
    merged: list[dict[str, str]] = []
    for law in _SPEC_LAWS + _FOUNDATION_LAWS:
        if law["name"] not in seen:
            seen.add(law["name"])
            merged.append(law)
    return merged
