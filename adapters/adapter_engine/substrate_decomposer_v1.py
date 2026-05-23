"""Substrate Decomposer v1 — deterministic primitive decomposition from normalized documents.

Rule-based extraction of primitives from document text.
Deterministic: same input always produces same output (no LLM).
Replay-safe: IDs are derived from content hashes, not random UUIDs.

UMH substrate subsystem. Phase 96.8BJ.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from substrate.understanding.ontology.primitive_decomposition_v1 import (
    DecompositionResult,
    PrimitiveObservation,
    PrimitiveRelationship,
    PrimitiveType,
    RelationshipType,
)


def _deterministic_id(namespace: str, content: str) -> str:
    """Produce a stable ID from namespace + content hash."""
    h = hashlib.sha256(f"{namespace}:{content}".encode("utf-8")).hexdigest()[:16]
    return f"{namespace}-{h}"


def _extract_sentences(text: str) -> list[str]:
    """Split text into sentences, filtering noise."""
    raw = re.split(r"(?<=[.!?…])\s+", text)
    sentences = []
    for s in raw:
        s = s.strip()
        if len(s) > 10 and not s.startswith("[Tab:"):
            sentences.append(s)
    return sentences


def _classify_sentence(sentence: str) -> list[tuple[PrimitiveType, float]]:
    """Classify a sentence into primitive types with confidence."""
    s = sentence.lower()
    results: list[tuple[PrimitiveType, float]] = []

    goal_patterns = [
        r"\bwant\b",
        r"\bgoal\b",
        r"\bmission\b",
        r"\bdesigned?\b",
        r"\bbuild\b",
        r"\bcreate\b",
        r"\bescape\b",
        r"\bachieve\b",
        r"\bwin\b",
        r"\bretire\b",
        r"\blevel up\b",
    ]
    action_patterns = [
        r"\bclick\b",
        r"\bjoin\b",
        r"\binstall\b",
        r"\bplay\b",
        r"\brun\b",
        r"\bstart\b",
        r"\bcheck\b",
        r"\bwatch\b",
        r"\bfollow\b",
        r"\bchase\b",
        r"\bspend\b",
        r"\bbuilt\b",
    ]
    state_patterns = [
        r"\bare\b.*\bjust\b",
        r"\bstuck\b",
        r"\brich\b",
        r"\bpoor\b",
        r"\bfree\b",
        r"\btrapped\b",
        r"\bfollowing\b",
        r"\bliving\b",
        r"\bplaying\b",
        r"\bdesigning\b",
    ]
    change_patterns = [
        r"\bshift\b",
        r"\bturn\b",
        r"\btransform\b",
        r"\bupgrade\b",
        r"\bchange\b",
        r"\bbecome\b",
        r"\binstalled\b",
        r"\bbreak\b",
    ]
    constraint_patterns = [
        r"\bnever\b",
        r"\bcan\'t\b",
        r"\bcannot\b",
        r"\bonly\b",
        r"\bmust\b",
        r"\brequire\b",
        r"\bprison\b",
        r"\blimited\b",
    ]
    signal_patterns = [
        r"\bnotice\b",
        r"\brealize\b",
        r"\bhit me\b",
        r"\bsaw\b",
        r"\brecognize\b",
        r"\bwake up\b",
        r"\bsign\b",
    ]
    outcome_patterns = [
        r"\bresult\b",
        r"\bearned?\b",
        r"\bcash\b",
        r"\bprofit\b",
        r"\bgained?\b",
        r"\blost\b",
        r"\bwon\b",
        r"\bfailed?\b",
    ]
    resource_patterns = [
        r"\bmoney\b",
        r"\btime\b",
        r"\bsystem\b",
        r"\btool\b",
        r"\bframework\b",
        r"\bcode\b",
        r"\bgame\b",
        r"\bprogram\b",
    ]
    feedback_patterns = [
        r"\btestimoni",
        r"\bproof\b",
        r"\bcase study\b",
        r"\bstory\b",
        r"\bexample\b",
        r"\bshowed\b",
        r"\bproven\b",
    ]
    time_patterns = [
        r"\byears?\b",
        r"\bmonths?\b",
        r"\bdays?\b",
        r"\bat \d+\b",
        r"\bafter\b",
        r"\bbefore\b",
        r"\bevery\b",
        r"\bdaily\b",
    ]

    pattern_map = [
        (goal_patterns, PrimitiveType.GOAL),
        (action_patterns, PrimitiveType.ACTION),
        (state_patterns, PrimitiveType.STATE),
        (change_patterns, PrimitiveType.CHANGE),
        (constraint_patterns, PrimitiveType.CONSTRAINT),
        (signal_patterns, PrimitiveType.SIGNAL),
        (outcome_patterns, PrimitiveType.OUTCOME),
        (resource_patterns, PrimitiveType.RESOURCE),
        (feedback_patterns, PrimitiveType.FEEDBACK),
        (time_patterns, PrimitiveType.TIME),
    ]

    for patterns, ptype in pattern_map:
        matches = sum(1 for p in patterns if re.search(p, s))
        if matches > 0:
            confidence = min(0.5 + matches * 0.15, 0.95)
            results.append((ptype, confidence))

    return results


def decompose_document(
    document_id: str,
    content_hash: str,
    full_text: str,
    title: str = "",
) -> DecompositionResult:
    """Decompose document text into typed primitives.

    Deterministic: same text always produces same primitives and IDs.
    """
    decomposition_id = _deterministic_id("decomp", f"{document_id}:{content_hash}")

    sentences = _extract_sentences(full_text)
    observations: list[PrimitiveObservation] = []
    relationships: list[PrimitiveRelationship] = []
    seen_ids: set[str] = set()

    for i, sentence in enumerate(sentences):
        classifications = _classify_sentence(sentence)
        if not classifications:
            continue

        primary_type, primary_conf = max(classifications, key=lambda x: x[1])

        obs_id = _deterministic_id("obs", f"{document_id}:{i}:{sentence[:80]}")
        if obs_id in seen_ids:
            continue
        seen_ids.add(obs_id)

        label_text = sentence[:60].strip()
        if len(sentence) > 60:
            label_text += "..."

        obs = PrimitiveObservation(
            observation_id=obs_id,
            primitive_type=primary_type,
            label=label_text,
            description=sentence,
            confidence=primary_conf,
            source_reference=f"{title}:sentence_{i}",
            evidence=sentence[:200],
            is_inferred=False,
        )
        observations.append(obs)

        for secondary_type, secondary_conf in classifications:
            if secondary_type == primary_type:
                continue
            if secondary_conf < 0.5:
                continue
            rel_id_str = f"{obs_id}→{secondary_type.value}"
            rel = PrimitiveRelationship(
                from_observation_id=obs_id,
                to_observation_id=f"type:{secondary_type.value}",
                relationship_type=_infer_relationship(primary_type, secondary_type),
                confidence=secondary_conf,
                description=f"{primary_type.value} relates to {secondary_type.value}",
            )
            relationships.append(rel)

    for i in range(len(observations) - 1):
        if observations[i].primitive_type in (PrimitiveType.ACTION, PrimitiveType.SIGNAL):
            if observations[i + 1].primitive_type in (
                PrimitiveType.OUTCOME,
                PrimitiveType.CHANGE,
                PrimitiveType.STATE,
            ):
                rel = PrimitiveRelationship(
                    from_observation_id=observations[i].observation_id,
                    to_observation_id=observations[i + 1].observation_id,
                    relationship_type=RelationshipType.CAUSES,
                    confidence=0.6,
                    description="sequential causal inference",
                )
                relationships.append(rel)

    result = DecompositionResult(
        decomposition_id=decomposition_id,
        source_content_hash=content_hash,
        observations=observations,
        relationships=relationships,
    )
    result.compute_coverage()
    result.decomposition_confidence = (
        sum(o.confidence for o in observations) / len(observations) if observations else 0.0
    )

    return result


def _infer_relationship(from_type: PrimitiveType, to_type: PrimitiveType) -> RelationshipType:
    """Infer relationship type between two primitive types."""
    mapping = {
        (PrimitiveType.ACTION, PrimitiveType.OUTCOME): RelationshipType.PRODUCES,
        (PrimitiveType.ACTION, PrimitiveType.CHANGE): RelationshipType.CAUSES,
        (PrimitiveType.GOAL, PrimitiveType.ACTION): RelationshipType.REQUIRES,
        (PrimitiveType.CONSTRAINT, PrimitiveType.ACTION): RelationshipType.CONSTRAINS,
        (PrimitiveType.SIGNAL, PrimitiveType.CHANGE): RelationshipType.CAUSES,
        (PrimitiveType.RESOURCE, PrimitiveType.ACTION): RelationshipType.ENABLES,
        (PrimitiveType.STATE, PrimitiveType.CHANGE): RelationshipType.PRECEDES,
        (PrimitiveType.CHANGE, PrimitiveType.STATE): RelationshipType.PRODUCES,
        (PrimitiveType.TIME, PrimitiveType.ACTION): RelationshipType.PRECEDES,
        (PrimitiveType.FEEDBACK, PrimitiveType.GOAL): RelationshipType.MEASURES,
    }
    return mapping.get((from_type, to_type), RelationshipType.ENABLES)
