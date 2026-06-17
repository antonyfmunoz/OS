"""Knowledge Awareness Runtime — meaning, not just documents.

Tracks decisions, constraints, conventions, lessons, architecture rules
extracted deterministically from artifacts and documentation.

Read-only observation pattern. Deterministic extraction.
Instance-agnostic.

Campaign 6.4. UMH substrate layer.
"""

from __future__ import annotations

import hashlib
import logging
import re
import time
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)

_DECISION_PATTERN = re.compile(
    r"(?:^|\n)\s*(?:#{1,4}\s*)?(?:decision|decided|ruling|resolution)\s*[:—\-]\s*(.+?)(?=\n(?:#{1,4}\s|\Z)|\Z)",
    re.IGNORECASE | re.DOTALL,
)
_CONSTRAINT_PATTERN = re.compile(
    r"(?:^|\n)\s*(?:#{1,4}\s*)?(?:constraint|invariant|non-negotiable|must not|never)\s*[:—\-]\s*(.+?)(?=\n(?:#{1,4}\s|\Z)|\Z)",
    re.IGNORECASE | re.DOTALL,
)
_CONVENTION_PATTERN = re.compile(
    r"(?:^|\n)\s*(?:#{1,4}\s*)?(?:convention|pattern|standard|always)\s*[:—\-]\s*(.+?)(?=\n(?:#{1,4}\s|\Z)|\Z)",
    re.IGNORECASE | re.DOTALL,
)
_LESSON_PATTERN = re.compile(
    r"(?:^|\n)\s*(?:#{1,4}\s*)?(?:lesson|learned|gotcha|mistake|pitfall)\s*[:—\-]\s*(.+?)(?=\n(?:#{1,4}\s|\Z)|\Z)",
    re.IGNORECASE | re.DOTALL,
)
_RULE_PATTERN = re.compile(
    r"(?:^|\n)\s*(?:#{1,4}\s*)?(?:rule|law|gate|enforced)\s*[:—\-]\s*(.+?)(?=\n(?:#{1,4}\s|\Z)|\Z)",
    re.IGNORECASE | re.DOTALL,
)

_PATTERNS: dict[str, re.Pattern[str]] = {
    "decision": _DECISION_PATTERN,
    "constraint": _CONSTRAINT_PATTERN,
    "convention": _CONVENTION_PATTERN,
    "lesson_learned": _LESSON_PATTERN,
    "architecture_rule": _RULE_PATTERN,
}


# ── Types ─────────────────────────────────────────────────────────────────


class KnowledgeType(str, Enum):
    DECISION = "decision"
    CONSTRAINT = "constraint"
    CONVENTION = "convention"
    LESSON_LEARNED = "lesson_learned"
    ARCHITECTURE_RULE = "architecture_rule"


@dataclass
class KnowledgeEntry:
    knowledge_id: str
    knowledge_type: str
    summary: str
    source_artifact_id: str = ""
    entity_refs: list[str] = field(default_factory=list)
    created_at: float = 0.0
    confidence: float = 0.8

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class KnowledgeSnapshot:
    total: int
    by_type: dict[str, int] = field(default_factory=dict)
    recent: list[KnowledgeEntry] = field(default_factory=list)
    detected_at: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "total": self.total,
            "by_type": self.by_type,
            "recent": [e.to_dict() for e in self.recent],
            "detected_at": self.detected_at,
        }


# ── Knowledge Awareness Runtime ──────────────────────────────────────────


class KnowledgeAwarenessRuntime:
    """Extracts and indexes decisions, constraints, conventions, lessons,
    and architecture rules from artifacts and documentation.

    All extraction is deterministic — pattern matching against known
    markers in document content. Zero LLM dependency.
    """

    def __init__(
        self,
        artifact_registry: Any = None,
        documentation_runtime: Any = None,
        repository_runtime: Any = None,
        reality_graph: Any = None,
    ) -> None:
        self._artifacts = artifact_registry
        self._docs = documentation_runtime
        self._repo = repository_runtime
        self._graph = reality_graph
        self._entries: dict[str, KnowledgeEntry] = {}

    def scan_knowledge(self) -> KnowledgeSnapshot:
        """Aggregate knowledge from all sources."""
        now = time.time()

        if self._artifacts is not None:
            self._scan_artifacts()

        if self._docs is not None:
            self._scan_documents()

        by_type: dict[str, int] = {}
        for entry in self._entries.values():
            by_type[entry.knowledge_type] = by_type.get(entry.knowledge_type, 0) + 1

        sorted_entries = sorted(
            self._entries.values(),
            key=lambda e: e.created_at,
            reverse=True,
        )

        return KnowledgeSnapshot(
            total=len(self._entries),
            by_type=by_type,
            recent=sorted_entries[:20],
            detected_at=now,
        )

    def extract_from_content(
        self,
        content: str,
        source_id: str = "",
        entity_refs: list[str] | None = None,
    ) -> list[KnowledgeEntry]:
        """Extract knowledge entries from text content."""
        entries: list[KnowledgeEntry] = []
        refs = entity_refs or []

        for ktype, pattern in _PATTERNS.items():
            for match in pattern.finditer(content):
                summary = match.group(1).strip()[:300]
                if len(summary) < 5:
                    continue

                kid = self._generate_id(ktype, summary)
                entry = KnowledgeEntry(
                    knowledge_id=kid,
                    knowledge_type=ktype,
                    summary=summary,
                    source_artifact_id=source_id,
                    entity_refs=list(refs),
                    created_at=time.time(),
                    confidence=0.8,
                )
                self._entries[kid] = entry
                entries.append(entry)

        return entries

    def find_for_entity(self, entity_id: str) -> list[KnowledgeEntry]:
        return [
            e for e in self._entries.values()
            if entity_id in e.entity_refs
        ]

    def find_decisions(self) -> list[KnowledgeEntry]:
        return self._find_by_type(KnowledgeType.DECISION.value)

    def find_constraints(self) -> list[KnowledgeEntry]:
        return self._find_by_type(KnowledgeType.CONSTRAINT.value)

    def find_conventions(self) -> list[KnowledgeEntry]:
        return self._find_by_type(KnowledgeType.CONVENTION.value)

    def find_lessons(self) -> list[KnowledgeEntry]:
        return self._find_by_type(KnowledgeType.LESSON_LEARNED.value)

    def find_rules(self) -> list[KnowledgeEntry]:
        return self._find_by_type(KnowledgeType.ARCHITECTURE_RULE.value)

    def get(self, knowledge_id: str) -> KnowledgeEntry | None:
        return self._entries.get(knowledge_id)

    def list_entries(
        self,
        knowledge_type: str | None = None,
        entity_id: str | None = None,
    ) -> list[KnowledgeEntry]:
        result = list(self._entries.values())
        if knowledge_type:
            result = [e for e in result if e.knowledge_type == knowledge_type]
        if entity_id:
            result = [e for e in result if entity_id in e.entity_refs]
        return result

    def snapshot(self) -> dict[str, Any]:
        return self.scan_knowledge().to_dict()

    # ── Internal ──────────────────────────────────────────────────────

    def _find_by_type(self, ktype: str) -> list[KnowledgeEntry]:
        return [e for e in self._entries.values() if e.knowledge_type == ktype]

    def _scan_artifacts(self) -> None:
        artifacts = []
        if hasattr(self._artifacts, "list_artifacts"):
            artifacts = self._artifacts.list_artifacts(artifact_type="decision_record")
        elif hasattr(self._artifacts, "_artifacts"):
            artifacts = [
                a for a in self._artifacts._artifacts.values()
                if getattr(a, "artifact_type", "") == "decision_record"
            ]

        for artifact in artifacts:
            a_id = getattr(artifact, "artifact_id", "")
            path = getattr(artifact, "source_path", "")
            refs = getattr(artifact, "entity_refs", [])

            content = self._read_content(path)
            if content:
                self.extract_from_content(content, source_id=a_id, entity_refs=refs)

    def _scan_documents(self) -> None:
        docs = []
        if hasattr(self._docs, "list_documents"):
            docs = self._docs.list_documents()
        elif hasattr(self._docs, "_documents"):
            docs = list(self._docs._documents.values())

        for doc in docs:
            doc_id = getattr(doc, "doc_id", "")
            path = getattr(doc, "path_or_url", "")
            refs = getattr(doc, "entity_refs", [])

            content = self._read_content(path)
            if content:
                self.extract_from_content(content, source_id=doc_id, entity_refs=refs)

    @staticmethod
    def _read_content(path: str, max_bytes: int = 100_000) -> str:
        import os
        if not path or not os.path.isfile(path):
            return ""
        try:
            with open(path, "r", errors="replace") as f:
                return f.read(max_bytes)
        except OSError:
            return ""

    @staticmethod
    def _generate_id(ktype: str, summary: str) -> str:
        key = f"{ktype}:{summary[:100]}"
        return f"kn-{hashlib.sha256(key.encode()).hexdigest()[:12]}"
