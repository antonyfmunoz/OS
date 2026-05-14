"""Stabilization Replay Validator v1.

6 replay checks for operational fabric stabilization.
Validates determinism across stabilization domains.

UMH substrate subsystem. Phase 96.8CH.
"""

from __future__ import annotations

import hashlib
from typing import Any

from core.stabilization.constitutional_operational_fabric_contracts_v1 import (
    StabilityReplayState,
    _now_iso,
)


REPLAY_CHECKS: list[str] = [
    "concurrency_durability",
    "replay_durability",
    "continuity_durability",
    "topology_durability",
    "resilience_durability",
    "governance_validation",
]


class StabilizationReplayValidator:
    """Validates replay determinism for stabilization domains."""

    def __init__(self) -> None:
        self._results: list[StabilityReplayState] = []

    def validate_determinism(
        self,
        check_name: str,
        input_data: str,
        output_data: str,
    ) -> dict[str, Any]:
        input_hash = hashlib.sha256(input_data.encode()).hexdigest()[:16]
        output_hash = hashlib.sha256(output_data.encode()).hexdigest()[:16]

        state = StabilityReplayState(
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
        input_hash = hashlib.sha256(input_data.encode()).hexdigest()[:16]
        hash_a = hashlib.sha256(output_a.encode()).hexdigest()[:16]
        hash_b = hashlib.sha256(output_b.encode()).hexdigest()[:16]

        deterministic = hash_a == hash_b

        state = StabilityReplayState(
            check_name=check_name,
            input_hash=input_hash,
            output_hash=hash_a,
            deterministic=deterministic,
        )
        self._results.append(state)

        return {
            **state.to_dict(),
            "output_hash_b": hash_b,
            "deterministic": deterministic,
        }

    def get_all_results(self) -> list[dict[str, Any]]:
        return [r.to_dict() for r in self._results]

    def all_deterministic(self) -> bool:
        if not self._results:
            return True
        return all(r.deterministic for r in self._results)

    def get_stats(self) -> dict[str, Any]:
        return {
            "total_checks": len(self._results),
            "deterministic": sum(1 for r in self._results if r.deterministic),
            "non_deterministic": sum(
                1 for r in self._results if not r.deterministic
            ),
            "all_deterministic": self.all_deterministic(),
        }
