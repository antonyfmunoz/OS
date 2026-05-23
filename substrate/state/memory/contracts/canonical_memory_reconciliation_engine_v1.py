"""Canonical Memory Reconciliation Engine v1.

Detects duplicates, semantic overlap, conflicts, staleness, and
strengthening opportunities across multi-document ingestion.

Deterministic. Rule-based. No vector similarity. No opaque AI scoring.
All decisions produce inspectable receipts with provenance lineage.

UMH substrate subsystem.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any

from .memory_identity_v1 import (
    EntityReference,
    MemoryIdentity,
    content_fingerprint,
    deterministic_id,
)


class ReconciliationAction(str, Enum):
    NEW = "new"
    DUPLICATE_SKIP = "duplicate_skip"
    STRENGTHEN = "strengthen"
    SUPERSEDE = "supersede"
    CONFLICT = "conflict"
    MERGE = "merge"


@dataclass
class ReconciliationDecision:
    """One reconciliation decision for a single candidate."""

    decision_id: str
    candidate_id: str
    candidate_fingerprint: str
    action: ReconciliationAction
    matched_memory_id: str | None = None
    reason: str = ""
    confidence_before: float = 0.0
    confidence_after: float = 0.0
    strength_before: int = 0
    strength_after: int = 0
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict[str, Any]:
        return {
            "decision_id": self.decision_id,
            "candidate_id": self.candidate_id,
            "candidate_fingerprint": self.candidate_fingerprint,
            "action": self.action.value,
            "matched_memory_id": self.matched_memory_id,
            "reason": self.reason,
            "confidence_before": self.confidence_before,
            "confidence_after": self.confidence_after,
            "strength_before": self.strength_before,
            "strength_after": self.strength_after,
            "timestamp": self.timestamp,
        }


@dataclass
class ReconciliationReceipt:
    """Full receipt for a reconciliation pass over one document's candidates."""

    receipt_id: str
    source_document_id: str
    total_candidates: int = 0
    new_count: int = 0
    duplicate_count: int = 0
    strengthen_count: int = 0
    supersede_count: int = 0
    conflict_count: int = 0
    merge_count: int = 0
    decisions: list[ReconciliationDecision] = field(default_factory=list)
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict[str, Any]:
        return {
            "receipt_id": self.receipt_id,
            "source_document_id": self.source_document_id,
            "total_candidates": self.total_candidates,
            "new_count": self.new_count,
            "duplicate_count": self.duplicate_count,
            "strengthen_count": self.strengthen_count,
            "supersede_count": self.supersede_count,
            "conflict_count": self.conflict_count,
            "merge_count": self.merge_count,
            "decisions": [d.to_dict() for d in self.decisions],
            "timestamp": self.timestamp,
        }


def _normalize_label(label: str) -> str:
    return " ".join(label.lower().strip().split())


def _label_overlap_score(label_a: str, label_b: str) -> float:
    """Token-level Jaccard similarity between two labels."""
    tokens_a = set(_normalize_label(label_a).split())
    tokens_b = set(_normalize_label(label_b).split())
    if not tokens_a or not tokens_b:
        return 0.0
    intersection = tokens_a & tokens_b
    union = tokens_a | tokens_b
    return len(intersection) / len(union)


def _content_overlap_score(content_a: str, content_b: str) -> float:
    """Token-level Jaccard on content (first 500 chars, normalized)."""
    norm_a = " ".join(content_a[:500].lower().split())
    norm_b = " ".join(content_b[:500].lower().split())
    tokens_a = set(norm_a.split())
    tokens_b = set(norm_b.split())
    if not tokens_a or not tokens_b:
        return 0.0
    intersection = tokens_a & tokens_b
    union = tokens_a | tokens_b
    return len(intersection) / len(union)


CONFLICT_MARKERS = frozenset(
    {
        "not",
        "never",
        "stop",
        "remove",
        "eliminate",
        "reject",
        "avoid",
        "don't",
        "cant",
        "cannot",
        "shouldn't",
        "won't",
        "no longer",
    }
)


def _detect_conflict(content_a: str, content_b: str) -> bool:
    """Heuristic: two memories with high overlap but opposing sentiment."""
    words_a = set(content_a.lower().split())
    words_b = set(content_b.lower().split())
    negation_a = words_a & CONFLICT_MARKERS
    negation_b = words_b & CONFLICT_MARKERS
    return bool(negation_a) != bool(negation_b)


class ReconciliationEngine:
    """Deterministic reconciliation over the canonical memory store.

    Reads existing memories, compares incoming candidates, produces
    reconciliation decisions with full provenance.
    """

    def __init__(
        self,
        store_dir: str | Path = "data/runtime/canonical_memory_store",
        receipts_dir: str | Path = "data/runtime/reconciliation_receipts",
        duplicate_fingerprint_threshold: float = 1.0,
        label_overlap_threshold: float = 0.6,
        content_overlap_threshold: float = 0.5,
    ):
        self.store_dir = Path(store_dir)
        self.receipts_dir = Path(receipts_dir)
        self.receipts_dir.mkdir(parents=True, exist_ok=True)
        self.duplicate_fingerprint_threshold = duplicate_fingerprint_threshold
        self.label_overlap_threshold = label_overlap_threshold
        self.content_overlap_threshold = content_overlap_threshold

        self._existing_memories: list[dict[str, Any]] = []
        self._fingerprint_index: dict[str, str] = {}
        self._label_index: dict[str, list[str]] = {}
        self._identity_index: dict[str, MemoryIdentity] = {}

    def load_existing_memories(self) -> int:
        """Load all memories from the JSONL store into in-memory indices."""
        self._existing_memories = []
        self._fingerprint_index = {}
        self._label_index = {}

        memories_path = self.store_dir / "memories.jsonl"
        if not memories_path.exists():
            return 0

        with open(memories_path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                entry = json.loads(line)
                self._existing_memories.append(entry)

                fp = content_fingerprint(entry.get("content", ""))
                self._fingerprint_index[fp] = entry["memory_id"]

                norm_label = _normalize_label(entry.get("label", ""))
                if norm_label not in self._label_index:
                    self._label_index[norm_label] = []
                self._label_index[norm_label].append(entry["memory_id"])

        identity_path = self.store_dir / "memory_identities.jsonl"
        if identity_path.exists():
            with open(identity_path) as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    data = json.loads(line)
                    mid = data["memory_id"]
                    self._identity_index[mid] = MemoryIdentity(
                        **{
                            k: v
                            for k, v in data.items()
                            if k in MemoryIdentity.__dataclass_fields__
                        }
                    )

        return len(self._existing_memories)

    def reconcile_candidate(self, candidate: dict[str, Any]) -> ReconciliationDecision:
        """Reconcile a single candidate against existing memories."""
        cand_content = candidate.get("content", "")
        cand_label = candidate.get("label", "")
        cand_type = candidate.get("primitive_type", "")
        cand_memory_type = candidate.get("memory_type", "")
        cand_fp = content_fingerprint(cand_content)
        cand_confidence = candidate.get("confidence", 0.0)
        cand_id = candidate.get("candidate_id", "")

        # Step 1: exact duplicate by fingerprint
        if cand_fp in self._fingerprint_index:
            matched_id = self._fingerprint_index[cand_fp]
            matched = self._get_memory(matched_id)
            return ReconciliationDecision(
                decision_id=deterministic_id("recon", f"{cand_id}:{matched_id}"),
                candidate_id=cand_id,
                candidate_fingerprint=cand_fp,
                action=ReconciliationAction.DUPLICATE_SKIP,
                matched_memory_id=matched_id,
                reason=f"Exact content fingerprint match: {cand_fp[:12]}...",
                confidence_before=matched.get("confidence", 0.0) if matched else 0.0,
                confidence_after=matched.get("confidence", 0.0) if matched else 0.0,
                strength_before=self._get_strength(matched_id),
                strength_after=self._get_strength(matched_id),
            )

        # Step 2: label + type overlap (semantic near-duplicate or strengthening)
        best_match: dict[str, Any] | None = None
        best_score = 0.0
        best_memory_id = ""

        for existing in self._existing_memories:
            if existing.get("primitive_type") != cand_type:
                continue
            if existing.get("memory_type") != cand_memory_type:
                continue

            label_score = _label_overlap_score(cand_label, existing.get("label", ""))
            if label_score < self.label_overlap_threshold:
                continue

            content_score = _content_overlap_score(cand_content, existing.get("content", ""))
            combined = (label_score * 0.4) + (content_score * 0.6)

            if combined > best_score:
                best_score = combined
                best_match = existing
                best_memory_id = existing["memory_id"]

        if best_match and best_score >= self.content_overlap_threshold:
            if _detect_conflict(cand_content, best_match.get("content", "")):
                return ReconciliationDecision(
                    decision_id=deterministic_id("recon", f"{cand_id}:{best_memory_id}"),
                    candidate_id=cand_id,
                    candidate_fingerprint=cand_fp,
                    action=ReconciliationAction.CONFLICT,
                    matched_memory_id=best_memory_id,
                    reason=f"Semantic overlap ({best_score:.2f}) with opposing sentiment",
                    confidence_before=best_match.get("confidence", 0.0),
                    confidence_after=best_match.get("confidence", 0.0),
                    strength_before=self._get_strength(best_memory_id),
                    strength_after=self._get_strength(best_memory_id),
                )

            existing_strength = self._get_strength(best_memory_id)
            if cand_confidence >= best_match.get("confidence", 0.0):
                return ReconciliationDecision(
                    decision_id=deterministic_id("recon", f"{cand_id}:{best_memory_id}"),
                    candidate_id=cand_id,
                    candidate_fingerprint=cand_fp,
                    action=ReconciliationAction.STRENGTHEN,
                    matched_memory_id=best_memory_id,
                    reason=f"Corroborating evidence (overlap={best_score:.2f}), new source strengthens",
                    confidence_before=best_match.get("confidence", 0.0),
                    confidence_after=min(best_match.get("confidence", 0.0) + 0.05, 1.0),
                    strength_before=existing_strength,
                    strength_after=existing_strength + 1,
                )
            else:
                return ReconciliationDecision(
                    decision_id=deterministic_id("recon", f"{cand_id}:{best_memory_id}"),
                    candidate_id=cand_id,
                    candidate_fingerprint=cand_fp,
                    action=ReconciliationAction.STRENGTHEN,
                    matched_memory_id=best_memory_id,
                    reason=f"Corroborating evidence (overlap={best_score:.2f}), lower confidence contributes",
                    confidence_before=best_match.get("confidence", 0.0),
                    confidence_after=best_match.get("confidence", 0.0),
                    strength_before=existing_strength,
                    strength_after=existing_strength + 1,
                )

        # Step 3: no match — new memory
        return ReconciliationDecision(
            decision_id=deterministic_id("recon", f"{cand_id}:new"),
            candidate_id=cand_id,
            candidate_fingerprint=cand_fp,
            action=ReconciliationAction.NEW,
            reason="No existing memory matches",
            confidence_before=0.0,
            confidence_after=cand_confidence,
            strength_before=0,
            strength_after=1,
        )

    def reconcile_candidates(
        self, candidates: list[dict[str, Any]], document_id: str
    ) -> ReconciliationReceipt:
        """Reconcile a full set of candidates from one document."""
        receipt_id = deterministic_id("reconreceipt", f"{document_id}:{len(candidates)}")

        receipt = ReconciliationReceipt(
            receipt_id=receipt_id,
            source_document_id=document_id,
            total_candidates=len(candidates),
        )

        for candidate in candidates:
            decision = self.reconcile_candidate(candidate)
            receipt.decisions.append(decision)

            if decision.action == ReconciliationAction.NEW:
                receipt.new_count += 1
            elif decision.action == ReconciliationAction.DUPLICATE_SKIP:
                receipt.duplicate_count += 1
            elif decision.action == ReconciliationAction.STRENGTHEN:
                receipt.strengthen_count += 1
            elif decision.action == ReconciliationAction.SUPERSEDE:
                receipt.supersede_count += 1
            elif decision.action == ReconciliationAction.CONFLICT:
                receipt.conflict_count += 1
            elif decision.action == ReconciliationAction.MERGE:
                receipt.merge_count += 1

        return receipt

    def apply_decisions(
        self,
        receipt: ReconciliationReceipt,
        candidates: list[dict[str, Any]],
        store: Any,
    ) -> dict[str, Any]:
        """Apply reconciliation decisions to the memory store.

        Returns a summary of what was applied.
        """
        applied: dict[str, list[str]] = {
            "promoted": [],
            "skipped": [],
            "strengthened": [],
            "conflicted": [],
        }

        candidate_by_id = {c["candidate_id"]: c for c in candidates}

        for decision in receipt.decisions:
            cand = candidate_by_id.get(decision.candidate_id)
            if not cand:
                continue

            if decision.action == ReconciliationAction.NEW:
                entry, promo_receipt = store.promote_candidate(
                    cand, reason="reconciliation:new", promoter="reconciliation_engine_v1"
                )
                self._register_identity(entry, cand)
                applied["promoted"].append(entry.memory_id)

            elif decision.action == ReconciliationAction.DUPLICATE_SKIP:
                applied["skipped"].append(decision.candidate_id)

            elif decision.action == ReconciliationAction.STRENGTHEN:
                self._apply_strengthening(decision)
                applied["strengthened"].append(decision.matched_memory_id or "")

            elif decision.action == ReconciliationAction.CONFLICT:
                applied["conflicted"].append(decision.candidate_id)

        return {
            "receipt_id": receipt.receipt_id,
            "document_id": receipt.source_document_id,
            "promoted": len(applied["promoted"]),
            "skipped": len(applied["skipped"]),
            "strengthened": len(applied["strengthened"]),
            "conflicted": len(applied["conflicted"]),
            "details": applied,
        }

    def save_receipt(self, receipt: ReconciliationReceipt) -> Path:
        """Persist a reconciliation receipt to disk."""
        filename = f"{receipt.source_document_id}_reconciliation.json"
        path = self.receipts_dir / filename
        with open(path, "w") as f:
            json.dump(receipt.to_dict(), f, indent=2)
        return path

    def _get_memory(self, memory_id: str) -> dict[str, Any] | None:
        for m in self._existing_memories:
            if m["memory_id"] == memory_id:
                return m
        return None

    def _get_strength(self, memory_id: str) -> int:
        identity = self._identity_index.get(memory_id)
        if identity:
            return identity.strength
        return 1

    def _register_identity(self, entry: Any, candidate: dict[str, Any]) -> None:
        """Create a MemoryIdentity for a newly promoted memory."""
        fp = content_fingerprint(candidate.get("content", ""))
        identity = MemoryIdentity(
            memory_id=entry.memory_id,
            content_fingerprint=fp,
            memory_type=candidate.get("memory_type", "canonical"),
            primitive_type=candidate.get("primitive_type", ""),
            source_document_ids=[candidate.get("source_document_id", "")],
            source_content_hashes=[candidate.get("source_content_hash", "")],
            confidence=candidate.get("confidence", 0.0),
            strength=1,
        )
        self._identity_index[entry.memory_id] = identity
        self._fingerprint_index[fp] = entry.memory_id

        identities_path = self.store_dir / "memory_identities.jsonl"
        with open(identities_path, "a") as f:
            f.write(json.dumps(identity.to_dict(), separators=(",", ":")) + "\n")

    def _apply_strengthening(self, decision: ReconciliationDecision) -> None:
        """Update the identity record for a strengthened memory."""
        if not decision.matched_memory_id:
            return
        identity = self._identity_index.get(decision.matched_memory_id)
        if identity:
            identity.strength = decision.strength_after
            identity.confidence = decision.confidence_after
            identity.updated_at = datetime.now(timezone.utc).isoformat()

    def get_entity_map(self) -> dict[str, EntityReference]:
        """Build an entity continuity map from existing memories."""
        entities: dict[str, EntityReference] = {}

        for mem in self._existing_memories:
            label = _normalize_label(mem.get("label", ""))
            ptype = mem.get("primitive_type", "")
            doc_id = mem.get("source_document_id", "")
            mem_id = mem.get("memory_id", "")
            timestamp = mem.get("timestamp", "")

            entity_type = _primitive_to_entity_type(ptype)
            entity_id = deterministic_id("entity", f"{label}:{entity_type}")

            if entity_id in entities:
                ref = entities[entity_id]
                if mem_id not in ref.memory_ids:
                    ref.memory_ids.append(mem_id)
                if doc_id not in ref.source_document_ids:
                    ref.source_document_ids.append(doc_id)
                ref.occurrence_count += 1
                if timestamp and timestamp > ref.last_seen:
                    ref.last_seen = timestamp
            else:
                entities[entity_id] = EntityReference(
                    entity_id=entity_id,
                    label=label,
                    entity_type=entity_type,
                    memory_ids=[mem_id],
                    source_document_ids=[doc_id],
                    occurrence_count=1,
                    first_seen=timestamp,
                    last_seen=timestamp,
                )

        return entities


def _primitive_to_entity_type(primitive_type: str) -> str:
    """Map primitive types to entity reference types."""
    mapping = {
        "goal": "goal",
        "constraint": "constraint",
        "resource": "concept",
        "state": "concept",
        "change": "workflow",
        "action": "workflow",
        "outcome": "concept",
        "signal": "concept",
        "feedback": "concept",
        "time": "concept",
    }
    return mapping.get(primitive_type, "concept")
