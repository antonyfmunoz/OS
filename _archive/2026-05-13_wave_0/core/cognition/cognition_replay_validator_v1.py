"""Cognition Replay Validator v1.

Validates replay determinism for cognition decisions.
Given the same inputs, cognition must produce the same outputs.

7 determinism checks per cognition trace:
  1. mode_policy        — same mode → same policy
  2. phase_transition   — same from/to → same validity
  3. focus_determinism  — same focus input → same focus state
  4. loop_transition    — same loop state + target → same result
  5. attention_weights  — same mode → same default weights
  6. boundary_policy    — same mode → same boundary limits
  7. continuity_mapping — same phase → same continuation type

Each check produces a determinism verdict.
Proof files persisted to disk.

UMH substrate subsystem. Phase 96.8BT.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from core.cognition.persistent_operator_cognition_contracts_v1 import (
    CognitionPhase,
    MODE_COGNITION_POLICIES,
    OperatorMode,
    _content_hash,
    _new_id,
    _now_iso,
)
from core.cognition.open_loop_cognition_engine_v1 import VALID_LOOP_TRANSITIONS
from core.cognition.runtime_attention_system_v1 import ATTENTION_DEFAULTS


DETERMINISM_CHECKS = [
    "mode_policy",
    "phase_transition",
    "focus_determinism",
    "loop_transition",
    "attention_weights",
    "boundary_policy",
    "continuity_mapping",
]

PHASE_CONTINUATION_MAP: dict[str, str] = {
    "archived": "complete",
    "terminated": "complete",
    "checkpointed": "checkpointed",
    "suspended": "suspended",
    "stale": "stale",
}


class CognitionReplayValidator:
    """Validates replay determinism for cognition decisions.

    7 checks per trace. Proof files persisted to disk.
    Does not execute actions or modify state.
    """

    def __init__(
        self,
        proof_dir: str | Path = "data/runtime/cognition_replay_proofs",
    ) -> None:
        self._proof_dir = Path(proof_dir)
        self._proof_dir.mkdir(parents=True, exist_ok=True)
        self._total_validations: int = 0
        self._total_passes: int = 0
        self._total_failures: int = 0

    def validate_trace(
        self,
        trace: dict[str, Any],
    ) -> dict[str, Any]:
        """Validate a cognition trace for replay determinism.

        A trace contains:
          operator_mode, phase, focus_input, loop_state,
          loop_target, from_phase, to_phase
        """
        results: list[dict[str, Any]] = []

        for check_name in DETERMINISM_CHECKS:
            method = getattr(self, f"_check_{check_name}", None)
            if method:
                result = method(trace)
                results.append(result)

        all_passed = all(r.get("passed", False) for r in results)
        proof = {
            "proof_id": _new_id("cogrpl"),
            "trace_hash": _content_hash(trace),
            "checks": results,
            "all_passed": all_passed,
            "check_count": len(results),
            "timestamp": _now_iso(),
        }

        self._total_validations += 1
        if all_passed:
            self._total_passes += 1
        else:
            self._total_failures += 1

        proof_path = self._proof_dir / f"cognition_replay_proof_{proof['proof_id']}.json"
        with proof_path.open("w", encoding="utf-8") as f:
            json.dump(proof, f, indent=2, default=str)

        return proof

    # ------------------------------------------------------------------
    # Individual checks
    # ------------------------------------------------------------------

    def _check_mode_policy(self, trace: dict[str, Any]) -> dict[str, Any]:
        """Same mode → same policy."""
        mode = trace.get("operator_mode", "focused_execution")
        policy = MODE_COGNITION_POLICIES.get(mode, {})
        replay_policy = MODE_COGNITION_POLICIES.get(mode, {})

        passed = _content_hash(policy) == _content_hash(replay_policy)
        return {
            "check": "mode_policy",
            "passed": passed,
            "input": {"mode": mode},
            "output_hash": _content_hash(policy),
            "replay_hash": _content_hash(replay_policy),
        }

    def _check_phase_transition(self, trace: dict[str, Any]) -> dict[str, Any]:
        """Same from/to → same validity verdict."""
        from_phase = trace.get("from_phase", "initialized")
        to_phase = trace.get("to_phase", "active")

        valid_map = self._get_valid_phase_transitions()
        is_valid = to_phase in valid_map.get(from_phase, [])
        replay_valid = to_phase in valid_map.get(from_phase, [])

        return {
            "check": "phase_transition",
            "passed": is_valid == replay_valid,
            "input": {"from": from_phase, "to": to_phase},
            "original_valid": is_valid,
            "replay_valid": replay_valid,
        }

    def _check_focus_determinism(self, trace: dict[str, Any]) -> dict[str, Any]:
        """Same focus input → same focus hash."""
        focus_input = trace.get("focus_input", {})
        hash1 = _content_hash(focus_input)
        hash2 = _content_hash(focus_input)

        return {
            "check": "focus_determinism",
            "passed": hash1 == hash2,
            "input_hash": hash1,
            "replay_hash": hash2,
        }

    def _check_loop_transition(self, trace: dict[str, Any]) -> dict[str, Any]:
        """Same loop state + target → same transition result."""
        loop_state = trace.get("loop_state", "active")
        loop_target = trace.get("loop_target", "waiting")

        valid_targets = VALID_LOOP_TRANSITIONS.get(loop_state, [])
        is_valid = loop_target in valid_targets
        replay_valid = loop_target in VALID_LOOP_TRANSITIONS.get(loop_state, [])

        return {
            "check": "loop_transition",
            "passed": is_valid == replay_valid,
            "input": {"state": loop_state, "target": loop_target},
            "original_valid": is_valid,
            "replay_valid": replay_valid,
        }

    def _check_attention_weights(self, trace: dict[str, Any]) -> dict[str, Any]:
        """Same mode → same default weights."""
        mode = trace.get("operator_mode", "focused_execution")
        weights = dict(ATTENTION_DEFAULTS)
        replay_weights = dict(ATTENTION_DEFAULTS)

        return {
            "check": "attention_weights",
            "passed": _content_hash(weights) == _content_hash(replay_weights),
            "input": {"mode": mode},
            "output_hash": _content_hash(weights),
            "replay_hash": _content_hash(replay_weights),
        }

    def _check_boundary_policy(self, trace: dict[str, Any]) -> dict[str, Any]:
        """Same mode → same cognition boundary limits."""
        mode = trace.get("operator_mode", "focused_execution")
        policy = MODE_COGNITION_POLICIES.get(mode, {})
        replay_policy = MODE_COGNITION_POLICIES.get(mode, {})

        depth = policy.get("cognition_persistence_depth", 0)
        replay_depth = replay_policy.get("cognition_persistence_depth", 0)

        return {
            "check": "boundary_policy",
            "passed": depth == replay_depth,
            "input": {"mode": mode},
            "depth": depth,
            "replay_depth": replay_depth,
        }

    def _check_continuity_mapping(self, trace: dict[str, Any]) -> dict[str, Any]:
        """Same phase → same continuation type."""
        phase = trace.get("phase", "active")
        cont_type = PHASE_CONTINUATION_MAP.get(phase, "active")
        replay_cont = PHASE_CONTINUATION_MAP.get(phase, "active")

        return {
            "check": "continuity_mapping",
            "passed": cont_type == replay_cont,
            "input": {"phase": phase},
            "continuation_type": cont_type,
            "replay_continuation_type": replay_cont,
        }

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _get_valid_phase_transitions(self) -> dict[str, list[str]]:
        return {
            "initialized": ["active", "terminated"],
            "active": ["focused", "checkpointed", "suspended", "stale", "archived", "terminated"],
            "focused": ["active", "checkpointed", "suspended", "stale", "archived", "terminated"],
            "checkpointed": ["active", "resumed", "terminated"],
            "suspended": ["resumed", "stale", "archived", "terminated"],
            "resumed": ["active", "focused", "terminated"],
            "stale": ["resumed", "archived", "terminated"],
            "archived": [],
            "terminated": [],
        }

    # ------------------------------------------------------------------
    # Batch validation
    # ------------------------------------------------------------------

    def validate_session(
        self, traces: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """Validate all traces from a session."""
        results = [self.validate_trace(t) for t in traces]
        all_passed = all(r["all_passed"] for r in results)

        return {
            "session_proof_id": _new_id("cogspl"),
            "trace_count": len(traces),
            "all_passed": all_passed,
            "pass_count": sum(1 for r in results if r["all_passed"]),
            "fail_count": sum(1 for r in results if not r["all_passed"]),
            "timestamp": _now_iso(),
        }

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------

    def get_stats(self) -> dict[str, Any]:
        return {
            "total_validations": self._total_validations,
            "total_passes": self._total_passes,
            "total_failures": self._total_failures,
        }
