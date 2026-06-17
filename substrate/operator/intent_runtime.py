"""Intent Runtime — canonical intent preservation for operator continuity.

Intent is the missing piece between transient conversation and persistent
reality. Currently, intents are classified (IntentRouter) and receipted
(IntentReceiptStore) but never persisted as versioned, queryable, conflict-
detectable entities.

IntentRuntime makes intent first-class:
  - Capture, version, supersede canonical intents across 5 scopes
  - Detect conflicts (contradiction, scope overlap, resource competition)
  - Score alignment between active work and stated intent
  - Provide session context: what intents matter right now

Composes with (never duplicates):
  - StrategicGapEngine.GoalRegistry — goals → product-scope intents
  - IntentReceiptStore — receipts link to canonical intents
  - ContinuityRuntime — resume reports include intent context

Gate 4 — Workstation Convergence Runtime. UMH substrate subsystem. Instance-agnostic.
"""

from __future__ import annotations

import json
import logging
import os
import threading
import time
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)

_REPO_ROOT = os.environ.get("UMH_ROOT", "/opt/OS")
_INTENT_DIR = os.path.join(_REPO_ROOT, "data", "umh", "intent")
_INTENTS_PATH = os.path.join(_INTENT_DIR, "intents.jsonl")
_CONFLICTS_PATH = os.path.join(_INTENT_DIR, "conflicts.jsonl")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Types
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class IntentScope(str, Enum):
    EMPIRE = "empire"
    PRODUCT = "product"
    ARCHITECTURE = "architecture"
    ENGINEERING = "engineering"
    SESSION = "session"


class CanonicalIntentStatus(str, Enum):
    ACTIVE = "active"
    SUPERSEDED = "superseded"
    ACHIEVED = "achieved"
    ABANDONED = "abandoned"


class ConflictType(str, Enum):
    CONTRADICTION = "contradiction"
    SCOPE_OVERLAP = "scope_overlap"
    RESOURCE_COMPETITION = "resource_competition"


# ── Scope hierarchy for lineage traversal and alignment scoring ──

_SCOPE_ORDER: dict[IntentScope, int] = {
    IntentScope.EMPIRE: 0,
    IntentScope.PRODUCT: 1,
    IntentScope.ARCHITECTURE: 2,
    IntentScope.ENGINEERING: 3,
    IntentScope.SESSION: 4,
}


@dataclass
class CanonicalIntent:
    intent_id: str = field(default_factory=lambda: f"intent-{uuid4().hex[:12]}")
    scope: IntentScope = IntentScope.SESSION
    statement: str = ""
    rationale: str = ""
    success_criteria: list[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    version: int = 1
    parent_id: str = ""
    status: CanonicalIntentStatus = CanonicalIntentStatus.ACTIVE
    superseded_by: str = ""
    evidence: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["scope"] = self.scope.value
        d["status"] = self.status.value
        return d

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> CanonicalIntent:
        d = dict(d)
        if "scope" in d and isinstance(d["scope"], str):
            d["scope"] = IntentScope(d["scope"])
        if "status" in d and isinstance(d["status"], str):
            d["status"] = CanonicalIntentStatus(d["status"])
        d.setdefault("success_criteria", [])
        d.setdefault("evidence", [])
        d.setdefault("tags", [])
        d.setdefault("updated_at", d.get("created_at", time.time()))
        known = set(cls.__dataclass_fields__)
        return cls(**{k: v for k, v in d.items() if k in known})


@dataclass
class IntentConflict:
    conflict_id: str = field(default_factory=lambda: f"conflict-{uuid4().hex[:8]}")
    intent_a_id: str = ""
    intent_b_id: str = ""
    conflict_type: ConflictType = ConflictType.CONTRADICTION
    description: str = ""
    resolution: str = ""
    detected_at: float = field(default_factory=time.time)
    resolved_at: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["conflict_type"] = self.conflict_type.value
        return d

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> IntentConflict:
        d = dict(d)
        if "conflict_type" in d and isinstance(d["conflict_type"], str):
            d["conflict_type"] = ConflictType(d["conflict_type"])
        known = set(cls.__dataclass_fields__)
        return cls(**{k: v for k, v in d.items() if k in known})

    @property
    def is_resolved(self) -> bool:
        return bool(self.resolution)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# JSONL Persistence (same pattern as IntentReceiptStore / GoalRegistry)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class _JSONLStore:
    """Thread-safe JSONL store with atomic rewrite."""

    _lock = threading.Lock()

    def __init__(self, path: str) -> None:
        self._path = path
        os.makedirs(os.path.dirname(self._path), exist_ok=True)

    def append(self, record: dict[str, Any]) -> None:
        with self._lock:
            with open(self._path, "a") as f:
                f.write(json.dumps(record, default=str, separators=(",", ":")) + "\n")

    def load_all(self) -> list[dict[str, Any]]:
        if not os.path.exists(self._path):
            return []
        records: list[dict[str, Any]] = []
        with open(self._path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError as exc:
                    logger.debug("Skipping malformed JSONL line: %s", exc)
        return records

    def rewrite(self, records: list[dict[str, Any]]) -> None:
        import tempfile
        with self._lock:
            dir_name = os.path.dirname(self._path)
            fd, tmp_path = tempfile.mkstemp(dir=dir_name, suffix=".tmp")
            try:
                with os.fdopen(fd, "w") as f:
                    for r in records:
                        f.write(json.dumps(r, default=str, separators=(",", ":")) + "\n")
                os.replace(tmp_path, self._path)
            except Exception:
                if os.path.exists(tmp_path):
                    os.unlink(tmp_path)
                raise


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# IntentRuntime
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class IntentRuntime:
    """Canonical intent preservation runtime.

    Captures, versions, retrieves, and detects conflicts across operator
    intents. Intents are versioned entities with scope hierarchy, lineage
    tracking, and deterministic conflict detection.
    """

    def __init__(
        self,
        intents_path: str | None = None,
        conflicts_path: str | None = None,
    ) -> None:
        self._intent_store = _JSONLStore(intents_path or _INTENTS_PATH)
        self._conflict_store = _JSONLStore(conflicts_path or _CONFLICTS_PATH)

    # ── Capture ──────────────────────────────────────────────────

    def capture(
        self,
        statement: str,
        scope: IntentScope,
        rationale: str = "",
        success_criteria: list[str] | None = None,
        parent_id: str = "",
        tags: list[str] | None = None,
    ) -> CanonicalIntent:
        """Capture a new canonical intent."""
        intent = CanonicalIntent(
            scope=scope,
            statement=statement.strip(),
            rationale=rationale.strip(),
            success_criteria=success_criteria or [],
            parent_id=parent_id,
            tags=tags or [],
        )
        self._intent_store.append(intent.to_dict())
        self._detect_conflicts_for(intent)
        return intent

    # ── Refine ───────────────────────────────────────────────────

    def refine(
        self,
        intent_id: str,
        new_statement: str = "",
        new_rationale: str = "",
        new_criteria: list[str] | None = None,
        new_tags: list[str] | None = None,
    ) -> CanonicalIntent | None:
        """Refine an existing intent — creates new version."""
        intent = self._get_by_id(intent_id)
        if intent is None:
            return None

        intent.version += 1
        intent.updated_at = time.time()
        if new_statement:
            intent.statement = new_statement.strip()
        if new_rationale:
            intent.rationale = new_rationale.strip()
        if new_criteria is not None:
            intent.success_criteria = new_criteria
        if new_tags is not None:
            intent.tags = new_tags

        self._rewrite_intent(intent)
        self._detect_conflicts_for(intent)
        return intent

    # ── Supersede ────────────────────────────────────────────────

    def supersede(self, intent_id: str, replacement_id: str) -> bool:
        """Mark an intent as superseded by another."""
        original = self._get_by_id(intent_id)
        replacement = self._get_by_id(replacement_id)
        if original is None or replacement is None:
            return False

        original.status = CanonicalIntentStatus.SUPERSEDED
        original.superseded_by = replacement_id
        original.updated_at = time.time()
        self._rewrite_intent(original)
        return True

    # ── Status changes ───────────────────────────────────────────

    def achieve(self, intent_id: str, evidence: list[str] | None = None) -> bool:
        """Mark an intent as achieved with optional evidence."""
        intent = self._get_by_id(intent_id)
        if intent is None:
            return False
        intent.status = CanonicalIntentStatus.ACHIEVED
        intent.updated_at = time.time()
        if evidence:
            intent.evidence.extend(evidence)
        self._rewrite_intent(intent)
        return True

    def abandon(self, intent_id: str, reason: str = "") -> bool:
        """Mark an intent as abandoned."""
        intent = self._get_by_id(intent_id)
        if intent is None:
            return False
        intent.status = CanonicalIntentStatus.ABANDONED
        intent.updated_at = time.time()
        if reason:
            intent.rationale = f"{intent.rationale} [abandoned: {reason}]"
        self._rewrite_intent(intent)
        return True

    # ── Retrieval ────────────────────────────────────────────────

    def retrieve(
        self,
        scope: IntentScope | None = None,
        status: str = "active",
    ) -> list[CanonicalIntent]:
        """Retrieve intents by scope and/or status."""
        intents = self._load_all_intents()
        if scope is not None:
            intents = [i for i in intents if i.scope == scope]
        if status:
            intents = [i for i in intents if i.status.value == status]
        intents.sort(key=lambda i: i.updated_at, reverse=True)
        return intents

    def get(self, intent_id: str) -> CanonicalIntent | None:
        """Get a single intent by ID."""
        return self._get_by_id(intent_id)

    def active_by_scope(self) -> dict[str, list[CanonicalIntent]]:
        """All active intents grouped by scope."""
        result: dict[str, list[CanonicalIntent]] = {s.value: [] for s in IntentScope}
        for intent in self._load_all_intents():
            if intent.status == CanonicalIntentStatus.ACTIVE:
                result[intent.scope.value].append(intent)
        return result

    # ── Lineage ──────────────────────────────────────────────────

    def lineage(self, intent_id: str) -> list[CanonicalIntent]:
        """Walk parent chain from an intent to its root (empire scope)."""
        chain: list[CanonicalIntent] = []
        seen: set[str] = set()
        current_id = intent_id

        while current_id and current_id not in seen:
            seen.add(current_id)
            intent = self._get_by_id(current_id)
            if intent is None:
                break
            chain.append(intent)
            current_id = intent.parent_id

        return chain

    # ── Conflict Detection ───────────────────────────────────────

    def conflicts(self, include_resolved: bool = False) -> list[IntentConflict]:
        """All detected conflicts."""
        all_conflicts = self._load_all_conflicts()
        if include_resolved:
            return all_conflicts
        return [c for c in all_conflicts if not c.is_resolved]

    def resolve_conflict(self, conflict_id: str, resolution: str) -> bool:
        """Resolve a conflict with explanation."""
        conflicts = self._load_all_conflicts()
        for c in conflicts:
            if c.conflict_id == conflict_id:
                c.resolution = resolution
                c.resolved_at = time.time()
                self._conflict_store.rewrite([x.to_dict() for x in conflicts])
                return True
        return False

    def _detect_conflicts_for(self, intent: CanonicalIntent) -> list[IntentConflict]:
        """Detect conflicts between a new/refined intent and existing active intents."""
        active = [i for i in self._load_all_intents()
                  if i.status == CanonicalIntentStatus.ACTIVE and i.intent_id != intent.intent_id]
        new_conflicts: list[IntentConflict] = []

        existing_conflicts = self._load_all_conflicts()
        existing_pairs = {
            (c.intent_a_id, c.intent_b_id) for c in existing_conflicts
        } | {
            (c.intent_b_id, c.intent_a_id) for c in existing_conflicts
        }

        intent_words = set(intent.statement.lower().split())
        intent_criteria_words = set()
        for c in intent.success_criteria:
            intent_criteria_words.update(c.lower().split())

        for other in active:
            pair = (intent.intent_id, other.intent_id)
            if pair in existing_pairs:
                continue

            conflict = self._check_pair_conflict(
                intent, other, intent_words, intent_criteria_words,
            )
            if conflict is not None:
                new_conflicts.append(conflict)
                self._conflict_store.append(conflict.to_dict())

        return new_conflicts

    def _check_pair_conflict(
        self,
        a: CanonicalIntent,
        b: CanonicalIntent,
        a_words: set[str],
        a_criteria_words: set[str],
    ) -> IntentConflict | None:
        """Deterministic pair-wise conflict check."""
        b_words = set(b.statement.lower().split())
        b_criteria_words = set()
        for c in b.success_criteria:
            b_criteria_words.update(c.lower().split())

        _NEGATION_MARKERS = {"not", "no", "never", "stop", "remove", "eliminate", "avoid"}
        a_negated = bool(a_words & _NEGATION_MARKERS)
        b_negated = bool(b_words & _NEGATION_MARKERS)

        statement_overlap = len(a_words & b_words) / max(len(a_words | b_words), 1)
        criteria_overlap = (
            len(a_criteria_words & b_criteria_words) /
            max(len(a_criteria_words | b_criteria_words), 1)
        ) if (a_criteria_words and b_criteria_words) else 0.0

        if statement_overlap > 0.5 and a_negated != b_negated:
            return IntentConflict(
                intent_a_id=a.intent_id,
                intent_b_id=b.intent_id,
                conflict_type=ConflictType.CONTRADICTION,
                description=(
                    f"Contradictory intents: one affirms, one negates "
                    f"(overlap={statement_overlap:.0%})"
                ),
            )

        if (a.scope == b.scope and statement_overlap > 0.6
                and a.intent_id != b.intent_id):
            return IntentConflict(
                intent_a_id=a.intent_id,
                intent_b_id=b.intent_id,
                conflict_type=ConflictType.SCOPE_OVERLAP,
                description=(
                    f"Same-scope intents with high overlap "
                    f"(scope={a.scope.value}, overlap={statement_overlap:.0%})"
                ),
            )

        if criteria_overlap > 0.5 and a.scope != b.scope:
            return IntentConflict(
                intent_a_id=a.intent_id,
                intent_b_id=b.intent_id,
                conflict_type=ConflictType.RESOURCE_COMPETITION,
                description=(
                    f"Cross-scope intents competing for same criteria "
                    f"(criteria_overlap={criteria_overlap:.0%})"
                ),
            )

        return None

    # ── Alignment Scoring ────────────────────────────────────────

    def alignment_score(self, description: str, scope: IntentScope | None = None) -> float:
        """Score how well a work description aligns with active intents.

        Returns 0.0–1.0. Higher = better alignment.
        Deterministic: keyword overlap + scope chain proximity.
        """
        active = self._load_all_intents()
        active = [i for i in active if i.status == CanonicalIntentStatus.ACTIVE]
        if scope is not None:
            active = [i for i in active if i.scope == scope]
        if not active:
            return 0.0

        desc_words = set(description.lower().split())
        if not desc_words:
            return 0.0

        _STOP_WORDS = {
            "the", "a", "an", "is", "are", "was", "were", "be", "been",
            "being", "have", "has", "had", "do", "does", "did", "will",
            "would", "could", "should", "may", "might", "shall", "can",
            "to", "of", "in", "for", "on", "with", "at", "by", "from",
            "as", "into", "through", "during", "before", "after", "and",
            "but", "or", "nor", "not", "so", "yet", "both", "either",
            "neither", "each", "every", "all", "any", "few", "more",
            "most", "other", "some", "such", "than", "too", "very",
            "just", "this", "that", "it", "its",
        }
        desc_words -= _STOP_WORDS

        best_score = 0.0
        for intent in active:
            intent_words = set(intent.statement.lower().split()) - _STOP_WORDS
            criteria_words = set()
            for c in intent.success_criteria:
                criteria_words.update(set(c.lower().split()) - _STOP_WORDS)

            all_intent_words = intent_words | criteria_words
            if not all_intent_words:
                continue

            overlap = len(desc_words & all_intent_words) / max(len(desc_words), 1)
            score = min(overlap * 2.0, 1.0)

            if score > best_score:
                best_score = score

        return round(best_score, 3)

    # ── Session Context ──────────────────────────────────────────

    def context_for_session(self) -> dict[str, Any]:
        """Build intent context for operator session.

        Returns active intents organized by scope, plus unresolved
        conflicts and overall alignment summary.
        """
        by_scope = self.active_by_scope()
        unresolved = self.conflicts(include_resolved=False)

        total_active = sum(len(v) for v in by_scope.values())

        return {
            "active_intents": {
                scope: [i.to_dict() for i in intents]
                for scope, intents in by_scope.items()
            },
            "total_active": total_active,
            "unresolved_conflicts": [c.to_dict() for c in unresolved],
            "conflict_count": len(unresolved),
            "scopes_with_intents": [
                scope for scope, intents in by_scope.items() if intents
            ],
        }

    def summary(self) -> dict[str, Any]:
        """Quick summary for dashboards."""
        all_intents = self._load_all_intents()
        active = [i for i in all_intents if i.status == CanonicalIntentStatus.ACTIVE]
        conflicts = self.conflicts(include_resolved=False)

        return {
            "total": len(all_intents),
            "active": len(active),
            "by_scope": {
                scope.value: len([i for i in active if i.scope == scope])
                for scope in IntentScope
            },
            "unresolved_conflicts": len(conflicts),
            "latest_update": max(
                (i.updated_at for i in all_intents), default=0.0,
            ),
        }

    # ── Internal persistence ─────────────────────────────────────

    def _load_all_intents(self) -> list[CanonicalIntent]:
        return [CanonicalIntent.from_dict(d) for d in self._intent_store.load_all()]

    def _load_all_conflicts(self) -> list[IntentConflict]:
        return [IntentConflict.from_dict(d) for d in self._conflict_store.load_all()]

    def _get_by_id(self, intent_id: str) -> CanonicalIntent | None:
        for intent in self._load_all_intents():
            if intent.intent_id == intent_id:
                return intent
        return None

    def _rewrite_intent(self, updated: CanonicalIntent) -> None:
        """Atomic rewrite — replace matching intent in store."""
        all_intents = self._load_all_intents()
        replaced = False
        for i, intent in enumerate(all_intents):
            if intent.intent_id == updated.intent_id:
                all_intents[i] = updated
                replaced = True
                break
        if not replaced:
            all_intents.append(updated)
        self._intent_store.rewrite([x.to_dict() for x in all_intents])
