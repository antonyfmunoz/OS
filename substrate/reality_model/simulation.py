"""Simulation Reality — non-mutating hypothesis testing.

Clone instance reality into an ephemeral sandbox, execute plans
against it, and produce diffs without mutating real state.

Use cases:
  - "What if I run this shell command?" → simulate outcome
  - "What would happen if we deployed this?" → predict impact
  - Pre-execution dry run before committing to real execution
"""

from __future__ import annotations

import copy
import logging
import time
from dataclasses import dataclass, field
from typing import Any
from uuid import UUID, uuid4

from substrate.reality_model.canonical import CanonicalPattern, CanonicalRealityModel
from substrate.reality_model.instance import InstanceObservation, InstanceRealityModel

logger = logging.getLogger(__name__)


@dataclass
class SimulationStep:
    step_number: int
    action: str
    predicted_outcome: str
    confidence: float = 0.5
    observations_added: int = 0
    patterns_matched: list[str] = field(default_factory=list)


@dataclass
class SimulationDiff:
    """What changed in the simulated reality vs. the real one."""

    new_observations: list[dict[str, Any]] = field(default_factory=list)
    matched_patterns: list[str] = field(default_factory=list)
    confidence_deltas: dict[str, float] = field(default_factory=dict)
    predicted_outcome: str = "unknown"
    risk_factors: list[str] = field(default_factory=list)


@dataclass
class SimulationResult:
    simulation_id: UUID = field(default_factory=uuid4)
    hypothesis: str = ""
    steps: list[SimulationStep] = field(default_factory=list)
    diff: SimulationDiff = field(default_factory=SimulationDiff)
    overall_confidence: float = 0.0
    duration_ms: float = 0.0
    safe_to_execute: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "simulation_id": str(self.simulation_id),
            "hypothesis": self.hypothesis,
            "step_count": len(self.steps),
            "overall_confidence": round(self.overall_confidence, 3),
            "duration_ms": round(self.duration_ms, 1),
            "safe_to_execute": self.safe_to_execute,
            "predicted_outcome": self.diff.predicted_outcome,
            "risk_factors": self.diff.risk_factors,
            "new_observations": len(self.diff.new_observations),
            "matched_patterns": self.diff.matched_patterns,
        }


_RISK_KEYWORDS = {
    "delete": "destructive operation — data loss possible",
    "drop": "destructive operation — irreversible schema change",
    "rm -rf": "recursive deletion — cannot be undone",
    "force": "forced operation — bypasses safety checks",
    "production": "production environment — real user impact",
    "deploy": "deployment — changes live system",
    "migrate": "migration — schema change in live database",
    "truncate": "table truncation — all data removed",
    "password": "credential operation — security sensitive",
    "secret": "secret handling — requires encryption",
}

_OUTCOME_PATTERNS = {
    "success": ["list", "read", "get", "show", "display", "query", "search", "check", "status"],
    "modification": ["write", "update", "set", "change", "modify", "edit", "create", "add"],
    "deletion": ["delete", "remove", "drop", "truncate", "clean", "purge", "clear"],
    "deployment": ["deploy", "release", "ship", "push", "publish"],
    "analysis": ["analyze", "evaluate", "assess", "audit", "review", "inspect"],
}


class SimulationReality:
    """Non-mutating hypothesis testing against a cloned reality model.

    Creates ephemeral copies of canonical and instance models,
    runs simulated actions, and reports what would change.
    """

    def __init__(
        self,
        canonical: CanonicalRealityModel | None = None,
        instance: InstanceRealityModel | None = None,
    ) -> None:
        self._canonical = canonical or CanonicalRealityModel()
        self._instance = instance or InstanceRealityModel(
            user_id="default", org_id="default"
        )

    def simulate(
        self,
        hypothesis: str,
        actions: list[str] | None = None,
    ) -> SimulationResult:
        """Run a simulation against cloned reality models.

        Args:
            hypothesis: Natural language description of what to test
            actions: Optional list of specific action strings to simulate
        """
        t0 = time.monotonic()
        result = SimulationResult(hypothesis=hypothesis)

        sim_observations = list(self._instance.all())
        canonical_patterns = list(self._canonical.all())

        if actions is None:
            actions = [hypothesis]

        for i, action in enumerate(actions):
            step = self._simulate_step(
                i + 1,
                action,
                sim_observations,
                canonical_patterns,
            )
            result.steps.append(step)

        result.diff = self._compute_diff(
            original_count=self._instance.count(),
            sim_observations=sim_observations,
            canonical_patterns=canonical_patterns,
            actions=actions,
        )

        if result.steps:
            confidences = [s.confidence for s in result.steps]
            result.overall_confidence = sum(confidences) / len(confidences)

        result.safe_to_execute = len(result.diff.risk_factors) == 0
        result.duration_ms = (time.monotonic() - t0) * 1000

        return result

    def _simulate_step(
        self,
        step_num: int,
        action: str,
        sim_observations: list[InstanceObservation],
        canonical_patterns: list[CanonicalPattern],
    ) -> SimulationStep:
        """Simulate a single action step."""
        action_lower = action.lower()

        predicted = self._predict_outcome(action_lower)
        matched = self._match_patterns(action_lower, canonical_patterns)
        confidence = self._estimate_confidence(action_lower, matched, sim_observations)

        sim_obs = InstanceObservation(
            content=f"[simulated] {predicted}: {action[:500]}",
            domain="simulation",
            confidence=confidence,
        )
        sim_observations.append(sim_obs)

        return SimulationStep(
            step_number=step_num,
            action=action[:300],
            predicted_outcome=predicted,
            confidence=confidence,
            observations_added=1,
            patterns_matched=[p.name for p in matched],
        )

    def _predict_outcome(self, action_lower: str) -> str:
        """Predict the outcome category of an action."""
        for outcome, keywords in _OUTCOME_PATTERNS.items():
            if any(kw in action_lower for kw in keywords):
                return outcome
        return "unknown"

    def _match_patterns(
        self,
        action_lower: str,
        patterns: list[CanonicalPattern],
    ) -> list[CanonicalPattern]:
        """Find canonical patterns relevant to this action."""
        matched: list[CanonicalPattern] = []
        for pattern in patterns:
            searchable = f"{pattern.name} {pattern.domain} {pattern.description}".lower()
            if any(word in searchable for word in action_lower.split()[:5]):
                matched.append(pattern)
        return matched

    def _estimate_confidence(
        self,
        action_lower: str,
        matched_patterns: list[CanonicalPattern],
        existing_obs: list[InstanceObservation],
    ) -> float:
        """Estimate confidence based on pattern matches and prior observations."""
        base = 0.5

        if matched_patterns:
            pattern_conf = max(p.effective_confidence() for p in matched_patterns)
            base = max(base, pattern_conf)

        similar = [
            obs for obs in existing_obs
            if any(word in obs.content.lower() for word in action_lower.split()[:3])
        ]
        if similar:
            base = min(1.0, base + 0.1 * min(len(similar), 3))

        return round(base, 3)

    def _compute_diff(
        self,
        original_count: int,
        sim_observations: list[InstanceObservation],
        canonical_patterns: list[CanonicalPattern],
        actions: list[str],
    ) -> SimulationDiff:
        """Compute the diff between real and simulated reality."""
        new_obs = sim_observations[original_count:]
        all_matched: list[str] = []
        for pattern in canonical_patterns:
            for action in actions:
                if any(w in pattern.name.lower() for w in action.lower().split()[:3]):
                    if pattern.name not in all_matched:
                        all_matched.append(pattern.name)

        risk_factors: list[str] = []
        for action in actions:
            action_lower = action.lower()
            for keyword, risk in _RISK_KEYWORDS.items():
                if keyword in action_lower:
                    risk_factors.append(risk)

        predicted = "success"
        if risk_factors:
            predicted = "risky"
        elif any(s.predicted_outcome == "deletion" for s in []):
            predicted = "destructive"

        combined_actions = " ".join(actions).lower()
        predicted = self._predict_outcome(combined_actions)

        return SimulationDiff(
            new_observations=[
                {"content": obs.content[:200], "confidence": obs.confidence}
                for obs in new_obs
            ],
            matched_patterns=all_matched,
            predicted_outcome=predicted,
            risk_factors=list(set(risk_factors)),
        )
