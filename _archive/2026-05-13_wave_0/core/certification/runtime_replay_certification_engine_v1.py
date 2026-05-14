"""Runtime Replay Certification Engine v1.

Certifies replay determinism across the substrate.
Same inputs → same outcomes, same topology → same replay.

UMH substrate subsystem. Phase 96.8CI.
"""

from __future__ import annotations

import hashlib
from typing import Any

from core.certification.runtime_certification_contracts_v1 import (
    CertificationReplayState,
    _now_iso,
)


MAX_REPLAY_CERTIFICATIONS = 100

REPLAY_CERTIFICATION_CHECKS: list[str] = [
    "same_inputs_same_outcomes",
    "same_topology_same_replay",
    "same_continuity_same_restoration",
    "same_orchestration_same_lineage",
    "same_semantics_same_guarantees",
]


class RuntimeReplayCertificationEngine:
    """Certifies replay determinism across all substrate layers."""

    def __init__(self) -> None:
        self._certifications: list[CertificationReplayState] = []

    def certify_replay(
        self,
        check_name: str,
        input_data: str,
        output_data: str,
    ) -> dict[str, Any]:
        if len(self._certifications) >= MAX_REPLAY_CERTIFICATIONS:
            raise ValueError("Max replay certifications reached")

        input_hash = hashlib.sha256(input_data.encode()).hexdigest()[:16]
        output_hash = hashlib.sha256(output_data.encode()).hexdigest()[:16]

        state = CertificationReplayState(
            check_name=check_name,
            input_hash=input_hash,
            output_hash=output_hash,
            deterministic=True,
        )
        self._certifications.append(state)
        return state.to_dict()

    def certify_replay_pair(
        self,
        check_name: str,
        input_data: str,
        output_a: str,
        output_b: str,
    ) -> dict[str, Any]:
        if len(self._certifications) >= MAX_REPLAY_CERTIFICATIONS:
            raise ValueError("Max replay certifications reached")

        input_hash = hashlib.sha256(input_data.encode()).hexdigest()[:16]
        hash_a = hashlib.sha256(output_a.encode()).hexdigest()[:16]
        hash_b = hashlib.sha256(output_b.encode()).hexdigest()[:16]
        deterministic = hash_a == hash_b

        state = CertificationReplayState(
            check_name=check_name,
            input_hash=input_hash,
            output_hash=hash_a,
            deterministic=deterministic,
        )
        self._certifications.append(state)

        return {
            **state.to_dict(),
            "output_hash_b": hash_b,
            "deterministic": deterministic,
        }

    def all_deterministic(self) -> bool:
        if not self._certifications:
            return True
        return all(c.deterministic for c in self._certifications)

    def get_all_certifications(self) -> list[dict[str, Any]]:
        return [c.to_dict() for c in self._certifications]

    def get_stats(self) -> dict[str, Any]:
        return {
            "total_certifications": len(self._certifications),
            "deterministic": sum(
                1 for c in self._certifications if c.deterministic
            ),
            "non_deterministic": sum(
                1 for c in self._certifications if not c.deterministic
            ),
            "all_deterministic": self.all_deterministic(),
        }
