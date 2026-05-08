"""Canonical Memory Query contracts for the UMH substrate layer.

Deterministic, lineage-aware, non-mutating retrieval of canonical memory.
Every query is policy-bounded and produces a QueryProofArtifact.

Core principle: no memory retrieval without lineage traceability.

UMH substrate subsystem. Phase 96.8V.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class QueryScope(str, Enum):
    EXACT_MEMORY_LOOKUP = "exact_memory_lookup"
    LINEAGE_TRAVERSAL = "lineage_traversal"
    ROLLBACK_TRAVERSAL = "rollback_traversal"
    TRACE_ID_LOOKUP = "trace_id_lookup"
    CANONICAL_HASH_LOOKUP = "canonical_hash_lookup"


ALLOWED_QUERY_SCOPES = frozenset(QueryScope)

FORBIDDEN_QUERY_ACTIONS = frozenset(
    {
        "semantic_interpretation",
        "summarization",
        "embedding_generation",
        "autonomous_expansion",
        "recursive_querying",
        "hidden_memory_expansion",
        "world_model_mutation",
        "canonical_writes",
        "cross_tenant_scans",
        "drive_wide_scans",
        "global_scans",
    }
)


@dataclass
class CanonicalMemoryQuery:
    """A governed query against the canonical memory store."""

    query_id: str
    scope: QueryScope
    lookup_key: str
    trace_id: str = ""
    requester: str = ""
    timestamp: str = ""
    no_mutation: bool = True
    no_interpretation: bool = True
    no_expansion: bool = True

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict[str, Any]:
        return {
            "query_id": self.query_id,
            "scope": self.scope.value,
            "lookup_key": self.lookup_key,
            "trace_id": self.trace_id,
            "requester": self.requester,
            "timestamp": self.timestamp,
            "no_mutation": self.no_mutation,
            "no_interpretation": self.no_interpretation,
            "no_expansion": self.no_expansion,
        }

    def compute_query_hash(self) -> str:
        """Deterministic hash of the query parameters (excludes timestamp)."""
        stable = {
            "scope": self.scope.value,
            "lookup_key": self.lookup_key,
            "no_mutation": self.no_mutation,
            "no_interpretation": self.no_interpretation,
            "no_expansion": self.no_expansion,
        }
        return hashlib.sha256(json.dumps(stable, sort_keys=True).encode("utf-8")).hexdigest()


@dataclass
class MemoryLineageReference:
    """Reference to a step in the transformation lineage of a memory."""

    state_id: str
    stage: str
    transformer_name: str
    content_hash: str
    governance_reference: str = ""
    rollback_reference: str = ""
    timestamp: str = ""


@dataclass
class QueryResultReference:
    """Result of a canonical memory query."""

    query_id: str
    scope: str
    result_count: int
    results: list[dict[str, Any]] = field(default_factory=list)
    lineage: list[MemoryLineageReference] = field(default_factory=list)
    rollback_chain: list[dict[str, str]] = field(default_factory=list)
    query_hash: str = ""
    result_hash: str = ""
    no_mutation_confirmed: bool = True
    no_interpretation_confirmed: bool = True
    no_expansion_confirmed: bool = True
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()

    def compute_result_hash(self) -> str:
        """Deterministic hash of results for reproducibility verification."""
        stable = json.dumps(self.results, sort_keys=True)
        return hashlib.sha256(stable.encode("utf-8")).hexdigest()

    def to_dict(self) -> dict[str, Any]:
        return {
            "query_id": self.query_id,
            "scope": self.scope,
            "result_count": self.result_count,
            "results": self.results,
            "lineage": [
                {
                    "state_id": lr.state_id,
                    "stage": lr.stage,
                    "transformer_name": lr.transformer_name,
                    "content_hash": lr.content_hash,
                    "governance_reference": lr.governance_reference,
                    "rollback_reference": lr.rollback_reference,
                    "timestamp": lr.timestamp,
                }
                for lr in self.lineage
            ],
            "rollback_chain": self.rollback_chain,
            "query_hash": self.query_hash,
            "result_hash": self.result_hash,
            "no_mutation_confirmed": self.no_mutation_confirmed,
            "no_interpretation_confirmed": self.no_interpretation_confirmed,
            "no_expansion_confirmed": self.no_expansion_confirmed,
            "timestamp": self.timestamp,
        }


@dataclass
class QueryProofArtifact:
    """Proof that a canonical memory query was executed within policy bounds."""

    proof_id: str
    query_id: str
    query_hash: str
    result_hash: str
    scope: str
    result_count: int
    governance_lineage_verified: bool = False
    rollback_chain_available: bool = False
    mutation_attempted: bool = False
    interpretation_attempted: bool = False
    expansion_attempted: bool = False
    forbidden_actions_checked: int = 0
    forbidden_actions_found: int = 0
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()

    @property
    def passed(self) -> bool:
        return (
            not self.mutation_attempted
            and not self.interpretation_attempted
            and not self.expansion_attempted
            and self.forbidden_actions_found == 0
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "proof_id": self.proof_id,
            "query_id": self.query_id,
            "query_hash": self.query_hash,
            "result_hash": self.result_hash,
            "scope": self.scope,
            "result_count": self.result_count,
            "governance_lineage_verified": self.governance_lineage_verified,
            "rollback_chain_available": self.rollback_chain_available,
            "mutation_attempted": self.mutation_attempted,
            "interpretation_attempted": self.interpretation_attempted,
            "expansion_attempted": self.expansion_attempted,
            "forbidden_actions_checked": self.forbidden_actions_checked,
            "forbidden_actions_found": self.forbidden_actions_found,
            "passed": self.passed,
            "timestamp": self.timestamp,
        }
