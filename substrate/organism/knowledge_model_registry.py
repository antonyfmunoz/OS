"""Knowledge Model Registry — system knowledge containers.

Knowledge models are NOT mentors or agents. They are structured knowledge
containers representing principles, frameworks, playbooks, and constraints
extracted from sources (books, docs, outcomes, SOPs, market research, etc.).

Phase 11.1. UMH substrate subsystem. Instance-agnostic.
"""

from __future__ import annotations

import json
import logging
import os
import tempfile
import time
from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)

_REPO_ROOT = os.environ.get("UMH_ROOT", "/opt/OS")


@dataclass
class KnowledgeModel:
    knowledge_model_id: str = field(default_factory=lambda: f"km-{uuid4().hex[:8]}")
    name: str = ""
    description: str = ""
    source_type: str = ""
    sources: list[str] = field(default_factory=list)
    extracted_principles: list[str] = field(default_factory=list)
    frameworks: list[str] = field(default_factory=list)
    playbooks: list[str] = field(default_factory=list)
    examples: list[str] = field(default_factory=list)
    constraints: list[str] = field(default_factory=list)
    contradictions: list[str] = field(default_factory=list)
    applicability_conditions: list[str] = field(default_factory=list)
    confidence: float = 0.0
    domain_tags: list[str] = field(default_factory=list)
    related_entities: list[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "knowledge_model_id": self.knowledge_model_id,
            "name": self.name,
            "description": self.description,
            "source_type": self.source_type,
            "sources": self.sources,
            "extracted_principles": self.extracted_principles,
            "frameworks": self.frameworks,
            "playbooks": self.playbooks,
            "examples": self.examples,
            "constraints": self.constraints,
            "contradictions": self.contradictions,
            "applicability_conditions": self.applicability_conditions,
            "confidence": round(self.confidence, 4),
            "domain_tags": self.domain_tags,
            "related_entities": self.related_entities,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> KnowledgeModel:
        return cls(
            knowledge_model_id=d.get("knowledge_model_id", f"km-{uuid4().hex[:8]}"),
            name=d.get("name", ""),
            description=d.get("description", ""),
            source_type=d.get("source_type", ""),
            sources=d.get("sources", []),
            extracted_principles=d.get("extracted_principles", []),
            frameworks=d.get("frameworks", []),
            playbooks=d.get("playbooks", []),
            examples=d.get("examples", []),
            constraints=d.get("constraints", []),
            contradictions=d.get("contradictions", []),
            applicability_conditions=d.get("applicability_conditions", []),
            confidence=float(d.get("confidence", 0.0)),
            domain_tags=d.get("domain_tags", []),
            related_entities=d.get("related_entities", []),
            created_at=float(d.get("created_at", time.time())),
            updated_at=float(d.get("updated_at", time.time())),
        )


class KnowledgeModelRegistry:
    """Registry for knowledge models with domain-tag-based lookup."""

    def __init__(self, store_path: str | None = None) -> None:
        self._store_path = store_path or os.path.join(
            _REPO_ROOT, "data", "umh", "universal_work", "knowledge_models.jsonl",
        )
        self._models: dict[str, KnowledgeModel] = {}
        self._load()

    def _load(self) -> None:
        if not os.path.exists(self._store_path):
            return
        parsed: dict[str, KnowledgeModel] = {}
        with open(self._store_path, "r") as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    d = json.loads(line)
                    km = KnowledgeModel.from_dict(d)
                    parsed[km.knowledge_model_id] = km
                except (json.JSONDecodeError, KeyError, TypeError) as exc:
                    raise ValueError(
                        f"Corrupt knowledge model at line {line_num}: {exc}"
                    ) from exc
        self._models = parsed

    def _save(self) -> None:
        dir_path = os.path.dirname(self._store_path)
        os.makedirs(dir_path, exist_ok=True)
        fd, tmp_path = tempfile.mkstemp(dir=dir_path, suffix=".tmp")
        try:
            with os.fdopen(fd, "w") as f:
                for km in self._models.values():
                    f.write(json.dumps(km.to_dict()) + "\n")
            os.replace(tmp_path, self._store_path)
        except BaseException:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
            raise

    def register(self, km: KnowledgeModel) -> KnowledgeModel:
        self._models[km.knowledge_model_id] = km
        self._save()
        return km

    def get(self, km_id: str) -> KnowledgeModel | None:
        return self._models.get(km_id)

    def find_by_domain(self, domain: str) -> list[KnowledgeModel]:
        return [km for km in self._models.values() if domain in km.domain_tags]

    def find_by_entity(self, entity: str) -> list[KnowledgeModel]:
        return [km for km in self._models.values() if entity in km.related_entities]

    def all_models(self) -> list[KnowledgeModel]:
        return list(self._models.values())

    def summary(self) -> dict[str, Any]:
        domain_counts: dict[str, int] = {}
        for km in self._models.values():
            for tag in km.domain_tags:
                domain_counts[tag] = domain_counts.get(tag, 0) + 1
        return {
            "total_models": len(self._models),
            "domain_counts": domain_counts,
            "models": [
                {
                    "knowledge_model_id": km.knowledge_model_id,
                    "name": km.name,
                    "domain_tags": km.domain_tags,
                    "confidence": round(km.confidence, 4),
                }
                for km in self._models.values()
            ],
        }
