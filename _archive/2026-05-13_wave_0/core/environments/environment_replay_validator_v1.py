"""Environment Replay Validator v1.

Replays:
  environment routing, environment delegation,
  topology synchronization, environment restoration,
  environment chronology.

Verifies:
  same topology + same input → same routing decisions.

UMH substrate subsystem. Phase 96.8BX.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from core.environments.live_environment_topology_contracts_v1 import (
    _content_hash,
    _new_id,
    _now_iso,
)

REPLAY_CHECKS: list[str] = [
    "environment_routing",
    "environment_delegation",
    "topology_synchronization",
    "environment_restoration",
    "environment_chronology",
]


class EnvironmentReplayValidator:
    """Validates deterministic replay of environment decisions."""

    def __init__(
        self,
        state_dir: str | Path = "data/runtime/environment_coordination/replay",
    ) -> None:
        self._state_dir = Path(state_dir)
        self._state_dir.mkdir(parents=True, exist_ok=True)
        self._proofs: list[dict[str, Any]] = []
        self._total_validations: int = 0
        self._total_passes: int = 0

    def validate_trace(
        self,
        trace_data: dict[str, Any],
    ) -> dict[str, Any]:
        results: dict[str, dict[str, Any]] = {}
        for check in REPLAY_CHECKS:
            check_data = trace_data.get(check, {})
            hash_val = _content_hash(check_data) if check_data else ""
            results[check] = {
                "check": check,
                "hash": hash_val,
                "passed": bool(check_data),
                "timestamp": _now_iso(),
            }

        all_passed = all(r["passed"] for r in results.values())
        self._total_validations += 1
        if all_passed:
            self._total_passes += 1

        proof = {
            "proof_id": _new_id("eproof"),
            "checks": results,
            "all_passed": all_passed,
            "trace_hash": _content_hash(trace_data),
            "timestamp": _now_iso(),
        }
        self._proofs.append(proof)
        self._persist_proof(proof)
        return proof

    def validate_routing_determinism(
        self,
        decisions_a: list[dict[str, Any]],
        decisions_b: list[dict[str, Any]],
    ) -> dict[str, Any]:
        hash_a = _content_hash(decisions_a)
        hash_b = _content_hash(decisions_b)
        passed = hash_a == hash_b
        self._total_validations += 1
        if passed:
            self._total_passes += 1

        result = {
            "check": "routing_determinism",
            "hash_a": hash_a,
            "hash_b": hash_b,
            "passed": passed,
            "timestamp": _now_iso(),
        }
        self._persist_proof(result)
        return result

    def validate_delegation_determinism(
        self,
        delegations_a: list[dict[str, Any]],
        delegations_b: list[dict[str, Any]],
    ) -> dict[str, Any]:
        hash_a = _content_hash(delegations_a)
        hash_b = _content_hash(delegations_b)
        passed = hash_a == hash_b
        self._total_validations += 1
        if passed:
            self._total_passes += 1

        result = {
            "check": "delegation_determinism",
            "hash_a": hash_a,
            "hash_b": hash_b,
            "passed": passed,
            "timestamp": _now_iso(),
        }
        self._persist_proof(result)
        return result

    def validate_sync_determinism(
        self,
        syncs_a: list[dict[str, Any]],
        syncs_b: list[dict[str, Any]],
    ) -> dict[str, Any]:
        hash_a = _content_hash(syncs_a)
        hash_b = _content_hash(syncs_b)
        passed = hash_a == hash_b
        self._total_validations += 1
        if passed:
            self._total_passes += 1

        result = {
            "check": "sync_determinism",
            "hash_a": hash_a,
            "hash_b": hash_b,
            "passed": passed,
            "timestamp": _now_iso(),
        }
        self._persist_proof(result)
        return result

    def _persist_proof(self, proof: dict[str, Any]) -> None:
        path = self._state_dir / "environment_replay_proofs.jsonl"
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(proof, default=str) + "\n")

    def get_stats(self) -> dict[str, Any]:
        return {
            "total_validations": self._total_validations,
            "total_passes": self._total_passes,
            "total_proofs": len(self._proofs),
        }
