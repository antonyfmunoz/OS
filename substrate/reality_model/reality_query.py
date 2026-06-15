"""Reality Query Contract — types for reality interrogation.

Defines the input/output contract for read-only reality intelligence queries.
No storage, no execution, no mutation. Pure data shapes.

Phase 20. UMH substrate subsystem. Instance-agnostic.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class RealityQueryType(str, Enum):
    WHY = "why"
    WHAT_CHANGED = "what_changed"
    EVIDENCE = "evidence"
    CONTRADICTIONS = "contradictions"
    LINEAGE = "lineage"
    DOMAIN_SUMMARY = "domain_summary"
    PRIORITIES = "priorities"


@dataclass
class RealityQuery:
    query_id: str
    query_type: RealityQueryType
    text: str = ""
    domain: str = ""
    entity: str = ""
    since_timestamp: float | None = None
    min_confidence: float = 0.0
    limit: int = 20


@dataclass
class RealityEvidence:
    source_type: str
    source_id: str
    content: str
    confidence: float
    domain: str
    timestamp: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class RealityQueryResult:
    query_id: str
    query_type: str
    evidence: list[RealityEvidence] = field(default_factory=list)
    confidence: float = 0.0
    reasoning: str = ""
    generated_at: float = field(default_factory=time.time)
    sources_queried: list[str] = field(default_factory=list)
