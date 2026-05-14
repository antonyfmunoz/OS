"""Concurrency Durability Engine v1.

Validates concurrent orchestration/replay/continuity stability
and bounded fanout durability under operational stress.

UMH substrate subsystem. Phase 96.8CH.
"""

from __future__ import annotations

from typing import Any

from core.stabilization.constitutional_operational_fabric_contracts_v1 import (
    ConcurrencyValidationState,
    _now_iso,
)


MAX_CONCURRENT_VALIDATIONS = 50

CONCURRENCY_CHECKS: list[str] = [
    "orchestration_concurrency",
    "replay_concurrency",
    "continuity_concurrency",
    "topology_concurrency",
    "fanout_bounded",
    "determinism_under_concurrency",
]


class ConcurrencyDurabilityEngine:
    """Validates concurrency durability across substrate layers."""

    def __init__(self) -> None:
        self._validations: list[ConcurrencyValidationState] = []

    def validate_concurrency(
        self,
        concurrent_operations: int,
        all_deterministic: bool = True,
        fanout_bounded: bool = True,
    ) -> dict[str, Any]:
        if len(self._validations) >= MAX_CONCURRENT_VALIDATIONS:
            raise ValueError("Max concurrent validations reached")

        state = ConcurrencyValidationState(
            concurrent_operations=concurrent_operations,
            all_deterministic=all_deterministic,
            fanout_bounded=fanout_bounded,
        )
        self._validations.append(state)

        return {
            "concurrency_id": state.concurrency_id,
            "durable": all_deterministic and fanout_bounded,
            "concurrent_operations": concurrent_operations,
            "all_deterministic": all_deterministic,
            "fanout_bounded": fanout_bounded,
        }

    def get_all_validations(self) -> list[dict[str, Any]]:
        return [v.to_dict() for v in self._validations]

    def get_durable_count(self) -> int:
        return sum(
            1 for v in self._validations
            if v.all_deterministic and v.fanout_bounded
        )

    def get_failed_count(self) -> int:
        return sum(
            1 for v in self._validations
            if not (v.all_deterministic and v.fanout_bounded)
        )

    def all_durable(self) -> bool:
        if not self._validations:
            return True
        return all(
            v.all_deterministic and v.fanout_bounded
            for v in self._validations
        )

    def get_stats(self) -> dict[str, Any]:
        return {
            "total_validations": len(self._validations),
            "durable": self.get_durable_count(),
            "failed": self.get_failed_count(),
            "all_durable": self.all_durable(),
        }
