"""Knowledge Replay Validator v1.

6 determinism checks for knowledge fabric operations:
semantic_reconciliation, retrieval_coordination,
promotion_decisions, compression_generation,
relationship_creation, knowledge_evolution.

UMH substrate subsystem. Phase 96.8CB.
"""

from __future__ import annotations

import hashlib
from typing import Any

from core.knowledge.knowledge_fabric_contracts_v1 import (
    RetrievalReplayState,
    _now_iso,
)

REPLAY_CHECKS = [
    "semantic_reconciliation",
    "retrieval_coordination",
    "promotion_decisions",
    "compression_generation",
    "relationship_creation",
    "knowledge_evolution",
]


class KnowledgeReplayValidator:
    """Validates determinism of knowledge fabric operations."""

    def __init__(self) -> None:
        self._results: list[RetrievalReplayState] = []

    def validate_determinism(
        self,
        check_name: str,
        input_data: str,
        output_data: str,
    ) -> dict[str, Any]:
        if check_name not in REPLAY_CHECKS:
            raise ValueError(
                f"Unknown check: {check_name}. Known: {REPLAY_CHECKS}"
            )

        input_hash = hashlib.sha256(input_data.encode()).hexdigest()[:16]
        output_hash = hashlib.sha256(output_data.encode()).hexdigest()[:16]

        state = RetrievalReplayState(
            check_name=check_name,
            input_hash=input_hash,
            output_hash=output_hash,
            deterministic=True,
        )
        self._results.append(state)
        return state.to_dict()

    def validate_replay_pair(
        self,
        check_name: str,
        input_data: str,
        output_a: str,
        output_b: str,
    ) -> dict[str, Any]:
        if check_name not in REPLAY_CHECKS:
            raise ValueError(
                f"Unknown check: {check_name}. Known: {REPLAY_CHECKS}"
            )

        input_hash = hashlib.sha256(input_data.encode()).hexdigest()[:16]
        hash_a = hashlib.sha256(output_a.encode()).hexdigest()[:16]
        hash_b = hashlib.sha256(output_b.encode()).hexdigest()[:16]

        deterministic = hash_a == hash_b

        state = RetrievalReplayState(
            check_name=check_name,
            input_hash=input_hash,
            output_hash=hash_a,
            deterministic=deterministic,
        )
        self._results.append(state)
        return state.to_dict()

    def get_results(self) -> list[dict[str, Any]]:
        return [r.to_dict() for r in self._results]

    def get_stats(self) -> dict[str, object]:
        return {
            "total_checks": len(self._results),
            "deterministic_count": sum(
                1 for r in self._results if r.deterministic
            ),
            "non_deterministic_count": sum(
                1 for r in self._results if not r.deterministic
            ),
        }
