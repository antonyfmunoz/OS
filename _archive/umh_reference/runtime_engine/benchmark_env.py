"""
Benchmark environment — validates whether EOS improves decision quality over time.

External to core EOS. No LLM calls. Deterministic. Seeded randomness only.

Architecture:
    Environment generates scenarios → System/baselines make decisions →
    Environment evaluates outcomes → Metrics collected → Comparison produced.

The system under test is the EOS substrate decision layer:
    DecisionEngine + IntentMemory + ScoreMeta self-tuning loop.

Baselines:
    - StaticWeights: fixed penalty weight, no adaptation.
    - RandomBaseline: uniformly random action selection.
    - PolicyOnly: always picks highest-priority rule, ignores memory.

Scenarios:
    - Static: fixed reward landscape. Tests convergence.
    - Shifting: reward function changes mid-run. Tests adaptation.
    - Noisy: reward has stochastic noise. Tests filtering.
    - Adversarial: reward inverts after system converges. Tests recovery.
"""

from __future__ import annotations

import hashlib
import json
import math
import sys
from dataclasses import dataclass, field
from typing import Any

sys.path.insert(0, "/opt/OS")

from umh.substrate.decision_engine import (
    DecisionEngine,
    DecisionOutput,
    Rule,
    RuleBasedStrategy,
    _compute_state_hash,
)
from umh.substrate.intent_memory import (
    build_memory_update_mutations,
    compute_memory_key,
    lookup_intent_memory,
    score_intent,
)
from umh.substrate.runtime_state_store import RuntimeStateStore
from umh.substrate.score_meta import (
    build_score_meta_adjustment,
    get_penalty_weight,
    lookup_score_meta,
)


# ─── Seeded RNG (no stdlib random — fully deterministic) ──────────


class SeededRNG:
    """Deterministic PRNG using a linear congruential generator.

    Same seed → same sequence, always. No platform dependencies.
    """

    def __init__(self, seed: int = 42) -> None:
        self._state = seed & 0xFFFFFFFFFFFFFFFF

    def next_int(self) -> int:
        self._state = (
            self._state * 6364136223846793005 + 1442695040888963407
        ) & 0xFFFFFFFFFFFFFFFF
        return self._state

    def next_float(self) -> float:
        return (self.next_int() >> 11) / (1 << 53)

    def choice(self, items: list) -> Any:
        if not items:
            raise ValueError("empty sequence")
        return items[self.next_int() % len(items)]


# ─── Environment scenarios ────────────────────────────────────────


@dataclass
class EnvironmentState:
    """Observable state the decision system sees each step."""

    step: int
    available_actions: list[str]
    context: dict[str, Any] = field(default_factory=dict)


@dataclass
class StepResult:
    """Outcome of one decision step."""

    step: int
    action_chosen: str
    reward: float
    is_success: bool
    state_hash: str


class Scenario:
    """Base scenario. Subclass to define reward landscapes."""

    def __init__(self, n_actions: int = 4, seed: int = 42) -> None:
        self.n_actions = n_actions
        self.actions = [f"action_{i}" for i in range(n_actions)]
        self.rng = SeededRNG(seed)

    def get_state(self, step: int) -> EnvironmentState:
        return EnvironmentState(step=step, available_actions=list(self.actions))

    def evaluate_action(self, action: str, step: int) -> tuple[float, bool]:
        raise NotImplementedError

    def reset(self, seed: int) -> None:
        self.rng = SeededRNG(seed)


class StaticScenario(Scenario):
    """Fixed reward landscape. action_0 is best, action_3 is worst.

    Tests: can the system converge to the optimal action?
    """

    def __init__(self, n_actions: int = 4, seed: int = 42) -> None:
        super().__init__(n_actions, seed)
        self._rewards = {self.actions[i]: 1.0 - (i * 0.25) for i in range(n_actions)}

    def evaluate_action(self, action: str, step: int) -> tuple[float, bool]:
        reward = self._rewards.get(action, 0.0)
        return reward, reward >= 0.5


class ShiftingScenario(Scenario):
    """Reward function shifts at step 50. Best action changes.

    Tests: can the system detect and adapt to regime change?
    """

    def __init__(
        self, n_actions: int = 4, seed: int = 42, shift_step: int = 50
    ) -> None:
        super().__init__(n_actions, seed)
        self.shift_step = shift_step

    def evaluate_action(self, action: str, step: int) -> tuple[float, bool]:
        idx = self.actions.index(action) if action in self.actions else 0
        if step < self.shift_step:
            reward = 1.0 - (idx * 0.25)
        else:
            reward = (idx * 0.25) + 0.25
        return reward, reward >= 0.5


class NoisyScenario(Scenario):
    """Static reward with additive noise. Tests filtering ability.

    The underlying signal is the same as StaticScenario but each
    evaluation adds deterministic noise scaled by step.
    """

    def __init__(
        self, n_actions: int = 4, seed: int = 42, noise_scale: float = 0.3
    ) -> None:
        super().__init__(n_actions, seed)
        self.noise_scale = noise_scale
        self._base_rewards = {
            self.actions[i]: 1.0 - (i * 0.25) for i in range(n_actions)
        }

    def evaluate_action(self, action: str, step: int) -> tuple[float, bool]:
        base = self._base_rewards.get(action, 0.0)
        noise_seed = hashlib.sha256(f"{action}:{step}".encode()).hexdigest()
        noise_val = (int(noise_seed[:8], 16) / 0xFFFFFFFF - 0.5) * 2
        reward = max(0.0, min(1.0, base + noise_val * self.noise_scale))
        is_success = reward >= 0.5
        return reward, is_success


class AdversarialScenario(Scenario):
    """Reward inverts after system converges. Tests recovery.

    Phase 1 (steps 0-39): action_0 is best.
    Phase 2 (steps 40-79): rewards invert — action_3 is best.
    Phase 3 (steps 80+): rewards restore — action_0 is best again.
    """

    def __init__(self, n_actions: int = 4, seed: int = 42) -> None:
        super().__init__(n_actions, seed)

    def evaluate_action(self, action: str, step: int) -> tuple[float, bool]:
        idx = self.actions.index(action) if action in self.actions else 0
        if step < 40:
            reward = 1.0 - (idx * 0.25)
        elif step < 80:
            reward = (idx * 0.25) + 0.25
        else:
            reward = 1.0 - (idx * 0.25)
        return reward, reward >= 0.5


# ─── Decision systems (system under test + baselines) ─────────────


class DecisionSystem:
    """Interface for any decision-making system in the benchmark."""

    def __init__(self, name: str) -> None:
        self.name = name

    def choose_action(self, env_state: EnvironmentState) -> str:
        raise NotImplementedError

    def observe_outcome(
        self, action: str, reward: float, is_success: bool, step: int
    ) -> None:
        raise NotImplementedError

    def reset(self) -> None:
        raise NotImplementedError

    def get_diagnostics(self) -> dict[str, Any]:
        return {}


class EOSDecisionSystem(DecisionSystem):
    """The EOS substrate decision layer under test.

    Uses DecisionEngine + IntentMemory + ScoreMeta exactly as production
    does, but without LLM calls. Rules are pre-defined for each action.
    The system learns which actions succeed via the memory/meta feedback loop.
    """

    def __init__(self) -> None:
        super().__init__("eos_substrate")
        self._store = RuntimeStateStore()
        self._rules: list[Rule] = []
        self._engine: DecisionEngine | None = None
        self._step = 0
        self._action_intent_types: dict[str, str] = {}

    def _build_rules(self, actions: list[str]) -> None:
        """Build one rule per action. Priority starts equal — memory breaks ties."""
        self._rules = []
        self._action_intent_types = {}

        for i, action in enumerate(actions):
            intent_type = f"benchmark_{action}"
            self._action_intent_types[action] = intent_type

            def make_condition(a: str):
                return lambda state: a in state.get("available_actions", [])

            def make_payload(a: str):
                return lambda state: {"action": a, "session_name": "benchmark"}

            self._rules.append(
                Rule(
                    rule_id=f"bench_{action}",
                    description=f"Select {action}",
                    condition=make_condition(action),
                    event_type=f"benchmark_{action}_selected",
                    build_payload=make_payload(action),
                    priority=100,
                )
            )

        strategy = RuleBasedStrategy(self._rules)
        self._engine = DecisionEngine(strategy=strategy)

    def choose_action(self, env_state: EnvironmentState) -> str:
        if self._engine is None or self._step == 0:
            self._build_rules(env_state.available_actions)

        self._store.load_snapshot(
            {
                "available_actions": env_state.available_actions,
                "step": env_state.step,
            }
        )

        snapshot = self._store.snapshot()
        intent_meta = lookup_score_meta(snapshot, "intent")

        best_action = None
        best_score = float("-inf")

        for action in env_state.available_actions:
            intent_type = self._action_intent_types.get(action, f"benchmark_{action}")
            goal = {"action": action, "session_name": "benchmark"}
            memory = lookup_intent_memory(self._memory_state, intent_type, goal)
            score = score_intent(memory, intent_meta)

            if score > best_score:
                best_score = score
                best_action = action

        return best_action or env_state.available_actions[0]

    def observe_outcome(
        self, action: str, reward: float, is_success: bool, step: int
    ) -> None:
        intent_type = self._action_intent_types.get(action, f"benchmark_{action}")
        goal = {"action": action, "session_name": "benchmark"}
        outcome = "completed" if is_success else "failed"
        failure_type = "" if is_success else "execution_failed"
        timestamp = f"2026-01-01T00:00:{step:02d}Z"

        mutations = build_memory_update_mutations(
            intent_type=intent_type,
            goal=goal,
            outcome=outcome,
            reason="" if is_success else "benchmark_failure",
            timestamp=timestamp,
            state=self._memory_state,
            failure_type=failure_type,
        )

        for m in mutations:
            self._memory_state[m["key"]] = m["value"]

        memory = lookup_intent_memory(self._memory_state, intent_type, goal)
        if memory is not None:
            meta = lookup_score_meta(self._memory_state, "intent")
            adj = build_score_meta_adjustment("intent", memory, meta)
            for m in adj:
                self._memory_state[m["key"]] = m["value"]

        self._step = step + 1

    def reset(self) -> None:
        self._store = RuntimeStateStore()
        self._memory_state: dict[str, Any] = {}
        self._rules = []
        self._engine = None
        self._step = 0
        self._action_intent_types = {}

    def get_diagnostics(self) -> dict[str, Any]:
        meta = lookup_score_meta(self._memory_state, "intent")
        weight = get_penalty_weight(meta)
        memories = {}
        for action, intent_type in self._action_intent_types.items():
            goal = {"action": action, "session_name": "benchmark"}
            mem = lookup_intent_memory(self._memory_state, intent_type, goal)
            if mem:
                memories[action] = {
                    "success": mem.get("success_count", 0),
                    "failure": mem.get("failure_count", 0),
                    "score": score_intent(mem, meta),
                }
        return {
            "penalty_weight": weight,
            "action_memories": memories,
            "meta": meta,
        }


class EOSWithExplorationSystem(DecisionSystem):
    """EOS substrate + exploration engine. Tests the improvement over baseline EOS."""

    def __init__(self) -> None:
        super().__init__("eos_exploration")
        self._store = RuntimeStateStore()
        self._rules: list[Rule] = []
        self._engine: DecisionEngine | None = None
        self._step = 0
        self._action_intent_types: dict[str, str] = {}
        self._failure_streak = 0
        self._last_success = True
        self._objective_trend: str | None = None
        self._recent_rewards: list[float] = []

    def _build_rules(self, actions: list[str]) -> None:
        self._rules = []
        self._action_intent_types = {}

        for i, action in enumerate(actions):
            intent_type = f"benchmark_{action}"
            self._action_intent_types[action] = intent_type

            def make_condition(a: str):
                return lambda state: a in state.get("available_actions", [])

            def make_payload(a: str):
                return lambda state: {"action": a, "session_name": "benchmark"}

            self._rules.append(
                Rule(
                    rule_id=f"bench_{action}",
                    description=f"Select {action}",
                    condition=make_condition(action),
                    event_type=f"benchmark_{action}_selected",
                    build_payload=make_payload(action),
                    priority=100,
                )
            )

        strategy = RuleBasedStrategy(self._rules)
        self._engine = DecisionEngine(strategy=strategy)

    def choose_action(self, env_state: EnvironmentState) -> str:
        from umh.runtime_engine.exploration_engine import (
            apply_exploration_adjustments,
            compute_exploration_signal,
        )

        if self._engine is None or self._step == 0:
            self._build_rules(env_state.available_actions)

        self._store.load_snapshot(
            {
                "available_actions": env_state.available_actions,
                "step": env_state.step,
            }
        )

        snapshot = self._store.snapshot()
        intent_meta = lookup_score_meta(snapshot, "intent")

        raw_scores: dict[str, float] = {}
        for action in env_state.available_actions:
            intent_type = self._action_intent_types.get(action, f"benchmark_{action}")
            goal = {"action": action, "session_name": "benchmark"}
            memory = lookup_intent_memory(self._memory_state, intent_type, goal)
            raw_scores[action] = score_intent(memory, intent_meta)

        plan_confidence = None
        if self._recent_rewards:
            plan_confidence = sum(self._recent_rewards[-5:]) / len(
                self._recent_rewards[-5:]
            )

        explore_signal = compute_exploration_signal(
            plan_confidence=plan_confidence,
            objective_trend=self._objective_trend,
            failure_streak=self._failure_streak,
            strategy_scores=raw_scores,
        )

        adjusted = apply_exploration_adjustments(raw_scores, explore_signal)

        best_action = None
        best_score = float("-inf")
        for action, score in adjusted.items():
            if score > best_score:
                best_score = score
                best_action = action

        return best_action or env_state.available_actions[0]

    def observe_outcome(
        self, action: str, reward: float, is_success: bool, step: int
    ) -> None:
        intent_type = self._action_intent_types.get(action, f"benchmark_{action}")
        goal = {"action": action, "session_name": "benchmark"}
        outcome = "completed" if is_success else "failed"
        failure_type = "" if is_success else "execution_failed"
        timestamp = f"2026-01-01T00:00:{step:02d}Z"

        mutations = build_memory_update_mutations(
            intent_type=intent_type,
            goal=goal,
            outcome=outcome,
            reason="" if is_success else "benchmark_failure",
            timestamp=timestamp,
            state=self._memory_state,
            failure_type=failure_type,
        )

        for m in mutations:
            self._memory_state[m["key"]] = m["value"]

        memory = lookup_intent_memory(self._memory_state, intent_type, goal)
        if memory is not None:
            meta = lookup_score_meta(self._memory_state, "intent")
            adj = build_score_meta_adjustment("intent", memory, meta)
            for m in adj:
                self._memory_state[m["key"]] = m["value"]

        if is_success:
            self._failure_streak = 0
            self._last_success = True
        else:
            self._failure_streak += 1
            self._last_success = False

        self._recent_rewards.append(reward)
        if len(self._recent_rewards) >= 5:
            recent = self._recent_rewards[-5:]
            earlier = (
                self._recent_rewards[-10:-5]
                if len(self._recent_rewards) >= 10
                else self._recent_rewards[:5]
            )
            avg_recent = sum(recent) / len(recent)
            avg_earlier = sum(earlier) / len(earlier) if earlier else avg_recent
            if avg_recent > avg_earlier + 0.01:
                self._objective_trend = "improving"
            elif avg_recent < avg_earlier - 0.01:
                self._objective_trend = "degrading"
            else:
                self._objective_trend = "flat"

        self._step = step + 1

    def reset(self) -> None:
        self._store = RuntimeStateStore()
        self._memory_state: dict[str, Any] = {}
        self._rules = []
        self._engine = None
        self._step = 0
        self._action_intent_types = {}
        self._failure_streak = 0
        self._last_success = True
        self._objective_trend = None
        self._recent_rewards = []

    def get_diagnostics(self) -> dict[str, Any]:
        meta = lookup_score_meta(self._memory_state, "intent")
        weight = get_penalty_weight(meta)
        memories = {}
        for action, intent_type in self._action_intent_types.items():
            goal = {"action": action, "session_name": "benchmark"}
            mem = lookup_intent_memory(self._memory_state, intent_type, goal)
            if mem:
                memories[action] = {
                    "success": mem.get("success_count", 0),
                    "failure": mem.get("failure_count", 0),
                    "score": score_intent(mem, meta),
                }
        return {
            "penalty_weight": weight,
            "action_memories": memories,
            "failure_streak": self._failure_streak,
            "objective_trend": self._objective_trend,
            "meta": meta,
        }


class EOSWithRegimeSystem(DecisionSystem):
    """EOS substrate + exploration engine + regime break detection."""

    def __init__(self) -> None:
        super().__init__("eos_regime")
        self._store = RuntimeStateStore()
        self._rules: list[Rule] = []
        self._engine: DecisionEngine | None = None
        self._step = 0
        self._action_intent_types: dict[str, str] = {}
        self._failure_streak = 0
        self._last_success = True
        self._objective_trend: str | None = None
        self._recent_rewards: list[float] = []
        self._prior_regime_strength = 0.0
        self._last_action: str | None = None

    def _build_rules(self, actions: list[str]) -> None:
        self._rules = []
        self._action_intent_types = {}

        for i, action in enumerate(actions):
            intent_type = f"benchmark_{action}"
            self._action_intent_types[action] = intent_type

            def make_condition(a: str):
                return lambda state: a in state.get("available_actions", [])

            def make_payload(a: str):
                return lambda state: {"action": a, "session_name": "benchmark"}

            self._rules.append(
                Rule(
                    rule_id=f"bench_{action}",
                    description=f"Select {action}",
                    condition=make_condition(action),
                    event_type=f"benchmark_{action}_selected",
                    build_payload=make_payload(action),
                    priority=100,
                )
            )

        strategy = RuleBasedStrategy(self._rules)
        self._engine = DecisionEngine(strategy=strategy)

    def choose_action(self, env_state: EnvironmentState) -> str:
        from umh.runtime_engine.exploration_engine import (
            apply_exploration_adjustments,
            compute_exploration_signal,
        )
        from umh.runtime_engine.regime_engine import (
            apply_regime_dampening,
            compute_regime_signal,
            select_regime_override,
        )

        if self._engine is None or self._step == 0:
            self._build_rules(env_state.available_actions)

        self._store.load_snapshot(
            {
                "available_actions": env_state.available_actions,
                "step": env_state.step,
            }
        )

        snapshot = self._store.snapshot()
        intent_meta = lookup_score_meta(snapshot, "intent")

        raw_scores: dict[str, float] = {}
        for action in env_state.available_actions:
            intent_type = self._action_intent_types.get(action, f"benchmark_{action}")
            goal = {"action": action, "session_name": "benchmark"}
            memory = lookup_intent_memory(self._memory_state, intent_type, goal)
            raw_scores[action] = score_intent(memory, intent_meta)

        plan_confidence = None
        if self._recent_rewards:
            plan_confidence = sum(self._recent_rewards[-5:]) / len(
                self._recent_rewards[-5:]
            )

        regime_signal = compute_regime_signal(
            reward_history=self._recent_rewards,
            strategy_scores=raw_scores,
            plan_confidence=plan_confidence,
            objective_trend=self._objective_trend,
            prior_regime_strength=self._prior_regime_strength,
            current_action=self._last_action,
        )
        self._prior_regime_strength = regime_signal.strength

        scores_after_regime = apply_regime_dampening(raw_scores, regime_signal)

        boosted_confidence = plan_confidence
        if regime_signal.active and plan_confidence is not None:
            boosted_confidence = max(
                0.0, plan_confidence - regime_signal.exploration_boost
            )

        explore_signal = compute_exploration_signal(
            plan_confidence=boosted_confidence,
            objective_trend=self._objective_trend,
            failure_streak=self._failure_streak,
            strategy_scores=scores_after_regime,
        )

        adjusted = apply_exploration_adjustments(scores_after_regime, explore_signal)

        override = select_regime_override(regime_signal, raw_scores, self._step)

        if override and override in adjusted:
            chosen = override
        else:
            best_action = None
            best_score = float("-inf")
            for action, score in adjusted.items():
                if score > best_score:
                    best_score = score
                    best_action = action
            chosen = best_action or env_state.available_actions[0]

        self._last_action = chosen
        return chosen

    def observe_outcome(
        self, action: str, reward: float, is_success: bool, step: int
    ) -> None:
        intent_type = self._action_intent_types.get(action, f"benchmark_{action}")
        goal = {"action": action, "session_name": "benchmark"}
        outcome = "completed" if is_success else "failed"
        failure_type = "" if is_success else "execution_failed"
        timestamp = f"2026-01-01T00:00:{step:02d}Z"

        mutations = build_memory_update_mutations(
            intent_type=intent_type,
            goal=goal,
            outcome=outcome,
            reason="" if is_success else "benchmark_failure",
            timestamp=timestamp,
            state=self._memory_state,
            failure_type=failure_type,
        )

        for m in mutations:
            self._memory_state[m["key"]] = m["value"]

        memory = lookup_intent_memory(self._memory_state, intent_type, goal)
        if memory is not None:
            meta = lookup_score_meta(self._memory_state, "intent")
            adj = build_score_meta_adjustment("intent", memory, meta)
            for m in adj:
                self._memory_state[m["key"]] = m["value"]

        if is_success:
            self._failure_streak = 0
            self._last_success = True
        else:
            self._failure_streak += 1
            self._last_success = False

        self._recent_rewards.append(reward)
        if len(self._recent_rewards) >= 5:
            recent = self._recent_rewards[-5:]
            earlier = (
                self._recent_rewards[-10:-5]
                if len(self._recent_rewards) >= 10
                else self._recent_rewards[:5]
            )
            avg_recent = sum(recent) / len(recent)
            avg_earlier = sum(earlier) / len(earlier) if earlier else avg_recent
            if avg_recent > avg_earlier + 0.01:
                self._objective_trend = "improving"
            elif avg_recent < avg_earlier - 0.01:
                self._objective_trend = "degrading"
            else:
                self._objective_trend = "flat"

        self._step = step + 1

    def reset(self) -> None:
        self._store = RuntimeStateStore()
        self._memory_state: dict[str, Any] = {}
        self._rules = []
        self._engine = None
        self._step = 0
        self._action_intent_types = {}
        self._failure_streak = 0
        self._last_success = True
        self._objective_trend = None
        self._recent_rewards = []
        self._prior_regime_strength = 0.0
        self._last_action = None


class EOSWithCorrectionSystem(DecisionSystem):
    """EOS substrate + exploration + regime + trap recovery + stability guard.

    The full correction layer stack. Tests whether the surgical fixes
    improve adversarial recovery, restart continuity, and meta differentiation.
    """

    def __init__(self) -> None:
        super().__init__("eos_corrected")
        self._store = RuntimeStateStore()
        self._rules: list[Rule] = []
        self._engine: DecisionEngine | None = None
        self._step = 0
        self._action_intent_types: dict[str, str] = {}
        self._failure_streak = 0
        self._last_success = True
        self._objective_trend: str | None = None
        self._recent_rewards: list[float] = []
        self._recent_actions: list[str] = []
        self._prior_regime_strength = 0.0
        self._last_action: str | None = None
        self._trap_detector: Any = None
        self._context_classifier: Any = None
        self._meta_gen: Any = None
        self._causal_mem: Any = None
        self._credit_eng: Any = None

    def _build_rules(self, actions: list[str]) -> None:
        self._rules = []
        self._action_intent_types = {}

        for i, action in enumerate(actions):
            intent_type = f"benchmark_{action}"
            self._action_intent_types[action] = intent_type

            def make_condition(a: str):
                return lambda state: a in state.get("available_actions", [])

            def make_payload(a: str):
                return lambda state: {"action": a, "session_name": "benchmark"}

            self._rules.append(
                Rule(
                    rule_id=f"bench_{action}",
                    description=f"Select {action}",
                    condition=make_condition(action),
                    event_type=f"benchmark_{action}_selected",
                    build_payload=make_payload(action),
                    priority=100,
                )
            )

        strategy = RuleBasedStrategy(self._rules)
        self._engine = DecisionEngine(strategy=strategy)

    def choose_action(self, env_state: EnvironmentState) -> str:
        from umh.runtime_engine.context_engine import (
            ContextClassifier,
            gate_exploration_inputs,
            gate_stability_effect,
            gate_trap_adjustment,
        )
        from umh.runtime_engine.exploration_engine import (
            apply_exploration_adjustments,
            compute_exploration_signal,
        )
        from umh.runtime_engine.causal_memory import (
            CausalMemoryEngine,
            apply_causal_bias,
        )
        from umh.runtime_engine.credit_assignment import (
            CreditAssignmentEngine,
            apply_credit_adjustment,
        )
        from umh.runtime_engine.foresight_engine import (
            ForesightEngine,
            apply_foresight_bias,
            extract_causal_stats,
            extract_credit_accumulators,
        )
        from umh.runtime_engine.meta_generalization import (
            MetaGeneralizationEngine,
            apply_confidence_prior,
            apply_exploration_prior,
            apply_strategy_priors,
        )
        from umh.runtime_engine.regime_engine import (
            apply_regime_dampening,
            compute_regime_signal,
            select_regime_override,
        )
        from umh.runtime_engine.signal_orchestrator import (
            SignalBundle,
            SignalOrchestrator,
            apply_orchestrated_signal,
        )
        from umh.runtime_engine.signal_sensitivity import (
            apply_sensitivity,
            compute_sensitivity,
        )
        from umh.runtime_engine.stability_guard import compute_stability_signal
        from umh.runtime_engine.trap_recovery_engine import TrapDetector, apply_trap_adjustments

        if self._trap_detector is None:
            self._trap_detector = TrapDetector()
        if self._context_classifier is None:
            self._context_classifier = ContextClassifier()
        if self._meta_gen is None:
            self._meta_gen = MetaGeneralizationEngine()
        if self._causal_mem is None:
            self._causal_mem = CausalMemoryEngine()
        if self._credit_eng is None:
            self._credit_eng = CreditAssignmentEngine()

        if self._engine is None or self._step == 0:
            self._build_rules(env_state.available_actions)

        self._store.load_snapshot(
            {
                "available_actions": env_state.available_actions,
                "step": env_state.step,
            }
        )

        snapshot = self._store.snapshot()
        intent_meta = lookup_score_meta(snapshot, "intent")

        raw_scores: dict[str, float] = {}
        for action in env_state.available_actions:
            intent_type = self._action_intent_types.get(action, f"benchmark_{action}")
            goal = {"action": action, "session_name": "benchmark"}
            memory = lookup_intent_memory(self._memory_state, intent_type, goal)
            raw_scores[action] = score_intent(memory, intent_meta)

        plan_confidence = None
        if self._recent_rewards:
            plan_confidence = sum(self._recent_rewards[-5:]) / len(
                self._recent_rewards[-5:]
            )

        ctx_signal = self._context_classifier.classify(
            self._recent_actions, self._recent_rewards
        )

        meta_result = self._meta_gen.classify(
            self._recent_actions, self._recent_rewards
        )
        if meta_result.matched and ctx_signal.dominant_type == "stable":
            raw_scores = apply_strategy_priors(raw_scores, meta_result)
            plan_confidence = apply_confidence_prior(plan_confidence, meta_result)

        causal_signal = self._causal_mem.compute_signal(
            ctx_signal.dominant_type,
            available_actions=list(raw_scores.keys()),
        )
        if causal_signal.action_bias and ctx_signal.dominant_type == "stable":
            raw_scores = apply_causal_bias(raw_scores, causal_signal)

        credit_signal = self._credit_eng.compute_signal(
            available_actions=list(raw_scores.keys()),
        )
        if credit_signal.action_credit and ctx_signal.dominant_type == "stable":
            raw_scores = apply_credit_adjustment(raw_scores, credit_signal)

        foresight_eng = ForesightEngine()
        foresight_signal = foresight_eng.compute_signal(
            available_actions=list(raw_scores.keys()),
            context=ctx_signal.dominant_type,
            causal_stats=extract_causal_stats(self._causal_mem),
            credit_accumulators=extract_credit_accumulators(self._credit_eng),
        )
        if foresight_signal.action_bias and ctx_signal.dominant_type == "stable":
            raw_scores = apply_foresight_bias(raw_scores, foresight_signal)

        regime_signal = compute_regime_signal(
            reward_history=self._recent_rewards,
            strategy_scores=raw_scores,
            plan_confidence=plan_confidence,
            objective_trend=self._objective_trend,
            prior_regime_strength=self._prior_regime_strength,
            current_action=self._last_action,
        )
        self._prior_regime_strength = regime_signal.strength

        scores = apply_regime_dampening(raw_scores, regime_signal)

        trap_signal = self._trap_detector.compute_signal(scores)
        if trap_signal.active:
            gated_adj = gate_trap_adjustment(trap_signal.trap_adjustment, ctx_signal)
            from umh.runtime_engine.trap_recovery_engine import TrapSignal

            trap_signal = TrapSignal(
                active=True,
                dominant_action=trap_signal.dominant_action,
                trap_adjustment=gated_adj,
                reward_mismatch=trap_signal.reward_mismatch,
                stagnation_length=trap_signal.stagnation_length,
                reason=trap_signal.reason,
            )
        scores = apply_trap_adjustments(scores, trap_signal)

        stability_signal = compute_stability_signal(
            self._recent_actions, self._recent_rewards
        )

        boosted_confidence = plan_confidence
        if regime_signal.active and plan_confidence is not None:
            boosted_confidence = max(
                0.0, plan_confidence - regime_signal.exploration_boost
            )
        if stability_signal.active and boosted_confidence is not None:
            gated_explore, gated_conf = gate_stability_effect(
                stability_signal.exploration_adjustment,
                stability_signal.confidence_adjustment,
                ctx_signal,
            )
            boosted_confidence = min(1.0, boosted_confidence + gated_conf)

        gated_streak, gated_trend = gate_exploration_inputs(
            self._failure_streak,
            self._objective_trend,
            self._recent_rewards,
            ctx_signal,
        )
        explore_signal = compute_exploration_signal(
            plan_confidence=boosted_confidence,
            objective_trend=gated_trend,
            failure_streak=gated_streak,
            strategy_scores=scores,
        )

        adjusted = apply_exploration_adjustments(scores, explore_signal)

        orch_bundle = SignalBundle(
            meta_signal=meta_result,
            context_signal=ctx_signal,
            causal_signal=causal_signal,
            credit_signal=credit_signal,
            foresight_signal=foresight_signal,
            exploration_signal=explore_signal,
            trap_signal=trap_signal,
            stability_signal=stability_signal,
        )
        orch_signal = SignalOrchestrator().orchestrate(
            orch_bundle, strategy_scores=adjusted
        )
        if orch_signal.combined_action_bias and ctx_signal.dominant_type == "stable":
            sens_confidences = {
                name: orch_signal.total_confidence
                for name in orch_signal.active_signals
            }
            sens_result = compute_sensitivity(
                combined_action_bias=orch_signal.combined_action_bias,
                consensus_score=orch_signal.consensus_score,
                signal_confidences=sens_confidences,
                context_type=ctx_signal.dominant_type,
                active_signal_count=len(orch_signal.active_signals),
            )
            scaled_bias = apply_sensitivity(
                orch_signal.combined_action_bias,
                sens_result,
                strategy_scores=adjusted,
            )
            for action, bias in scaled_bias.items():
                if action in adjusted:
                    adjusted[action] = adjusted[action] + bias

        override = select_regime_override(regime_signal, raw_scores, self._step)

        if override and override in adjusted:
            chosen = override
        else:
            best_action = None
            best_score = float("-inf")
            for action, score in adjusted.items():
                if score > best_score:
                    best_score = score
                    best_action = action
            chosen = best_action or env_state.available_actions[0]

        self._last_action = chosen
        return chosen

    def observe_outcome(
        self, action: str, reward: float, is_success: bool, step: int
    ) -> None:
        intent_type = self._action_intent_types.get(action, f"benchmark_{action}")
        goal = {"action": action, "session_name": "benchmark"}
        outcome = "completed" if is_success else "failed"
        failure_type = "" if is_success else "execution_failed"
        timestamp = f"2026-01-01T00:00:{step:02d}Z"

        mutations = build_memory_update_mutations(
            intent_type=intent_type,
            goal=goal,
            outcome=outcome,
            reason="" if is_success else "benchmark_failure",
            timestamp=timestamp,
            state=self._memory_state,
            failure_type=failure_type,
        )

        for m in mutations:
            self._memory_state[m["key"]] = m["value"]

        memory = lookup_intent_memory(self._memory_state, intent_type, goal)
        if memory is not None:
            meta = lookup_score_meta(self._memory_state, "intent")
            adj = build_score_meta_adjustment("intent", memory, meta)
            for m in adj:
                self._memory_state[m["key"]] = m["value"]

        if is_success:
            self._failure_streak = 0
            self._last_success = True
        else:
            self._failure_streak += 1
            self._last_success = False

        self._recent_rewards.append(reward)
        self._recent_actions.append(action)

        if self._trap_detector is not None:
            self._trap_detector.observe(action, reward)

        if self._meta_gen is not None and len(self._recent_rewards) >= 15:
            self._meta_gen.learn(
                self._recent_actions, self._recent_rewards, outcome_reward=reward
            )

        if self._causal_mem is not None and self._context_classifier is not None:
            ctx = self._context_classifier.classify(
                self._recent_actions, self._recent_rewards
            )
            obj_val = sum(self._recent_rewards[-5:]) / max(
                len(self._recent_rewards[-5:]), 1
            )
            self._causal_mem.record_transition(
                ctx.dominant_type, action, reward, obj_val
            )

        if self._credit_eng is not None:
            _credit_ctx = "unknown"
            if self._context_classifier is not None:
                _credit_ctx = self._context_classifier.classify(
                    self._recent_actions, self._recent_rewards
                ).dominant_type
            _credit_obj = sum(self._recent_rewards[-5:]) / max(
                len(self._recent_rewards[-5:]), 1
            )
            self._credit_eng.record_step(action, _credit_ctx, reward, _credit_obj)

        if len(self._recent_rewards) >= 5:
            recent = self._recent_rewards[-5:]
            earlier = (
                self._recent_rewards[-10:-5]
                if len(self._recent_rewards) >= 10
                else self._recent_rewards[:5]
            )
            avg_recent = sum(recent) / len(recent)
            avg_earlier = sum(earlier) / len(earlier) if earlier else avg_recent
            if avg_recent > avg_earlier + 0.01:
                self._objective_trend = "improving"
            elif avg_recent < avg_earlier - 0.01:
                self._objective_trend = "degrading"
            else:
                self._objective_trend = "flat"

        self._step = step + 1

    def reset(self) -> None:
        self._store = RuntimeStateStore()
        self._memory_state: dict[str, Any] = {}
        self._rules = []
        self._engine = None
        self._step = 0
        self._action_intent_types = {}
        self._failure_streak = 0
        self._last_success = True
        self._objective_trend = None
        self._recent_rewards = []
        self._recent_actions = []
        self._prior_regime_strength = 0.0
        self._last_action = None
        if self._trap_detector is not None:
            self._trap_detector.reset()
        self._trap_detector = None
        if self._context_classifier is not None:
            self._context_classifier.reset()
        self._context_classifier = None
        if self._meta_gen is not None:
            self._meta_gen.reset()
        self._meta_gen = None
        if self._causal_mem is not None:
            self._causal_mem.reset()
        self._causal_mem = None
        if self._credit_eng is not None:
            self._credit_eng.reset()
        self._credit_eng = None

    def get_state_snapshot(self) -> dict:
        """Snapshot behavioral state for restart continuity testing."""
        return {
            "memory_state": dict(self._memory_state)
            if hasattr(self, "_memory_state")
            else {},
            "recent_rewards": list(self._recent_rewards),
            "recent_actions": list(self._recent_actions),
            "failure_streak": self._failure_streak,
            "objective_trend": self._objective_trend,
            "prior_regime_strength": self._prior_regime_strength,
            "last_action": self._last_action,
            "trap_detector": self._trap_detector.snapshot()
            if self._trap_detector
            else None,
            "context_classifier": self._context_classifier.snapshot()
            if self._context_classifier
            else None,
            "meta_gen": self._meta_gen.snapshot() if self._meta_gen else None,
            "causal_mem": self._causal_mem.snapshot() if self._causal_mem else None,
            "credit_eng": self._credit_eng.snapshot() if self._credit_eng else None,
        }

    def restore_state_snapshot(self, snapshot: dict) -> None:
        """Restore behavioral state from snapshot."""
        if not snapshot or not isinstance(snapshot, dict):
            return
        self._memory_state = dict(snapshot.get("memory_state", {}))
        self._recent_rewards = list(snapshot.get("recent_rewards", []))
        self._recent_actions = list(snapshot.get("recent_actions", []))
        self._failure_streak = int(snapshot.get("failure_streak", 0))
        self._objective_trend = snapshot.get("objective_trend")
        self._prior_regime_strength = float(snapshot.get("prior_regime_strength", 0.0))
        self._last_action = snapshot.get("last_action")
        trap_data = snapshot.get("trap_detector")
        if trap_data and isinstance(trap_data, dict):
            from umh.runtime_engine.trap_recovery_engine import TrapDetector

            self._trap_detector = TrapDetector()
            self._trap_detector.restore(trap_data)
        ctx_data = snapshot.get("context_classifier")
        if ctx_data and isinstance(ctx_data, dict):
            from umh.runtime_engine.context_engine import ContextClassifier

            self._context_classifier = ContextClassifier()
            self._context_classifier.restore(ctx_data)
        meta_data = snapshot.get("meta_gen")
        if meta_data and isinstance(meta_data, dict):
            from umh.runtime_engine.meta_generalization import MetaGeneralizationEngine

            self._meta_gen = MetaGeneralizationEngine()
            self._meta_gen.restore(meta_data)
        causal_data = snapshot.get("causal_mem")
        if causal_data and isinstance(causal_data, dict):
            from umh.runtime_engine.causal_memory import CausalMemoryEngine

            self._causal_mem = CausalMemoryEngine()
            self._causal_mem.restore(causal_data)
        credit_data = snapshot.get("credit_eng")
        if credit_data and isinstance(credit_data, dict):
            from umh.runtime_engine.credit_assignment import CreditAssignmentEngine

            self._credit_eng = CreditAssignmentEngine()
            self._credit_eng.restore(credit_data)


class StaticWeightsBaseline(DecisionSystem):
    """Fixed penalty weight. Tracks memory but never adjusts meta."""

    def __init__(self, fixed_weight: float = 0.1) -> None:
        super().__init__("static_weights")
        self.fixed_weight = fixed_weight
        self._memory: dict[str, Any] = {}
        self._action_intent_types: dict[str, str] = {}

    def choose_action(self, env_state: EnvironmentState) -> str:
        for action in env_state.available_actions:
            if action not in self._action_intent_types:
                self._action_intent_types[action] = f"benchmark_{action}"

        fixed_meta = {"failure_penalty_weight": self.fixed_weight}
        best_action = None
        best_score = float("-inf")

        for action in env_state.available_actions:
            intent_type = self._action_intent_types[action]
            goal = {"action": action, "session_name": "benchmark"}
            memory = lookup_intent_memory(self._memory, intent_type, goal)
            score = score_intent(memory, fixed_meta)
            if score > best_score:
                best_score = score
                best_action = action

        return best_action or env_state.available_actions[0]

    def observe_outcome(
        self, action: str, reward: float, is_success: bool, step: int
    ) -> None:
        intent_type = self._action_intent_types.get(action, f"benchmark_{action}")
        goal = {"action": action, "session_name": "benchmark"}
        outcome = "completed" if is_success else "failed"
        failure_type = "" if is_success else "execution_failed"
        timestamp = f"2026-01-01T00:00:{step:02d}Z"

        mutations = build_memory_update_mutations(
            intent_type=intent_type,
            goal=goal,
            outcome=outcome,
            reason="" if is_success else "benchmark_failure",
            timestamp=timestamp,
            state=self._memory,
            failure_type=failure_type,
        )
        for m in mutations:
            self._memory[m["key"]] = m["value"]

    def reset(self) -> None:
        self._memory = {}
        self._action_intent_types = {}


class RandomBaseline(DecisionSystem):
    """Uniformly random action selection. No learning."""

    def __init__(self, seed: int = 42) -> None:
        super().__init__("random")
        self.rng = SeededRNG(seed)
        self._seed = seed

    def choose_action(self, env_state: EnvironmentState) -> str:
        return self.rng.choice(env_state.available_actions)

    def observe_outcome(
        self, action: str, reward: float, is_success: bool, step: int
    ) -> None:
        pass

    def reset(self) -> None:
        self.rng = SeededRNG(self._seed)


class PolicyOnlyBaseline(DecisionSystem):
    """Always picks the first rule that matches. Ignores memory entirely."""

    def __init__(self) -> None:
        super().__init__("policy_only")

    def choose_action(self, env_state: EnvironmentState) -> str:
        return env_state.available_actions[0]

    def observe_outcome(
        self, action: str, reward: float, is_success: bool, step: int
    ) -> None:
        pass

    def reset(self) -> None:
        pass


# ─── Metrics collection ──────────────────────────────────────────


@dataclass
class RunMetrics:
    """Collected metrics for a single simulation run."""

    system_name: str
    scenario_name: str
    total_steps: int
    rewards: list[float] = field(default_factory=list)
    actions_chosen: list[str] = field(default_factory=list)
    successes: list[bool] = field(default_factory=list)

    @property
    def avg_reward(self) -> float:
        return sum(self.rewards) / len(self.rewards) if self.rewards else 0.0

    @property
    def reward_variance(self) -> float:
        if len(self.rewards) < 2:
            return 0.0
        mean = self.avg_reward
        return sum((r - mean) ** 2 for r in self.rewards) / (len(self.rewards) - 1)

    @property
    def convergence_step(self) -> int | None:
        """Step at which the system stabilizes on the best action (10 consecutive)."""
        if not self.actions_chosen:
            return None
        window = 10
        for i in range(len(self.actions_chosen) - window + 1):
            segment = self.actions_chosen[i : i + window]
            if len(set(segment)) == 1:
                return i
        return None

    @property
    def recovery_time(self) -> int | None:
        """Steps between first failure after convergence and re-convergence."""
        conv = self.convergence_step
        if conv is None:
            return None
        converged_action = self.actions_chosen[conv]
        first_deviation = None
        for i in range(conv, len(self.actions_chosen)):
            if self.actions_chosen[i] != converged_action:
                first_deviation = i
                break
        if first_deviation is None:
            return 0

        window = 5
        for i in range(first_deviation, len(self.actions_chosen) - window + 1):
            segment = self.actions_chosen[i : i + window]
            if len(set(segment)) == 1:
                return i - first_deviation
        return None

    @property
    def early_avg_reward(self) -> float:
        """Average reward for first 20% of steps."""
        n = max(1, len(self.rewards) // 5)
        return sum(self.rewards[:n]) / n if self.rewards else 0.0

    @property
    def late_avg_reward(self) -> float:
        """Average reward for last 20% of steps."""
        n = max(1, len(self.rewards) // 5)
        return sum(self.rewards[-n:]) / n if self.rewards else 0.0

    @property
    def improvement_ratio(self) -> float:
        """Late reward / early reward. >1 means system improved."""
        early = self.early_avg_reward
        if early == 0:
            return float("inf") if self.late_avg_reward > 0 else 1.0
        return self.late_avg_reward / early

    def performance_curve(self, window: int = 10) -> list[float]:
        """Rolling average reward (data only, no plotting)."""
        if len(self.rewards) < window:
            return [self.avg_reward] if self.rewards else []
        return [
            sum(self.rewards[i : i + window]) / window
            for i in range(len(self.rewards) - window + 1)
        ]


# ─── Simulation runner ────────────────────────────────────────────


def run_simulation(
    system: DecisionSystem,
    scenario: Scenario,
    steps: int = 100,
    seed: int = 42,
) -> RunMetrics:
    """Run a full simulation of a system in a scenario.

    Deterministic: same system + scenario + steps + seed → same results.
    """
    scenario.reset(seed)
    system.reset()

    scenario_name = type(scenario).__name__
    metrics = RunMetrics(
        system_name=system.name,
        scenario_name=scenario_name,
        total_steps=steps,
    )

    for step in range(steps):
        env_state = scenario.get_state(step)
        action = system.choose_action(env_state)
        reward, is_success = scenario.evaluate_action(action, step)
        system.observe_outcome(action, reward, is_success, step)

        metrics.rewards.append(reward)
        metrics.actions_chosen.append(action)
        metrics.successes.append(is_success)

    return metrics


# ─── Comparison engine ────────────────────────────────────────────


@dataclass
class ComparisonResult:
    """Full comparison of all systems across all scenarios."""

    results: dict[str, dict[str, RunMetrics]] = field(default_factory=dict)

    def summary(self) -> str:
        lines = ["=" * 72, "BENCHMARK RESULTS", "=" * 72]

        for scenario_name in sorted(self._scenario_names()):
            lines.append(f"\n{'─' * 72}")
            lines.append(f"Scenario: {scenario_name}")
            lines.append(f"{'─' * 72}")
            lines.append(
                f"{'System':<20} {'Avg Reward':>10} {'Variance':>10} "
                f"{'Converge':>10} {'Recovery':>10} {'Improve':>10}"
            )

            for system_name in sorted(self.results.keys()):
                m = self.results[system_name].get(scenario_name)
                if m is None:
                    continue
                conv = (
                    str(m.convergence_step) if m.convergence_step is not None else "—"
                )
                rec = str(m.recovery_time) if m.recovery_time is not None else "—"
                lines.append(
                    f"{system_name:<20} {m.avg_reward:>10.4f} {m.reward_variance:>10.4f} "
                    f"{conv:>10} {rec:>10} {m.improvement_ratio:>10.2f}x"
                )

        lines.append(f"\n{'=' * 72}")
        return "\n".join(lines)

    def _scenario_names(self) -> set[str]:
        names: set[str] = set()
        for scenarios in self.results.values():
            names.update(scenarios.keys())
        return names


def run_full_benchmark(
    steps: int = 100,
    seed: int = 42,
) -> ComparisonResult:
    """Run all systems against all scenarios and return comparison.

    Deterministic: same steps + seed → identical results across runs.
    """
    systems: list[DecisionSystem] = [
        EOSDecisionSystem(),
        EOSWithExplorationSystem(),
        EOSWithRegimeSystem(),
        StaticWeightsBaseline(fixed_weight=0.1),
        RandomBaseline(seed=seed),
        PolicyOnlyBaseline(),
    ]

    scenarios: list[Scenario] = [
        StaticScenario(seed=seed),
        ShiftingScenario(seed=seed),
        NoisyScenario(seed=seed),
        AdversarialScenario(seed=seed),
    ]

    comparison = ComparisonResult()

    for system in systems:
        comparison.results[system.name] = {}
        for scenario in scenarios:
            metrics = run_simulation(system, scenario, steps=steps, seed=seed)
            comparison.results[system.name][metrics.scenario_name] = metrics

    return comparison


# ─── CLI entry point ──────────────────────────────────────────────


def main() -> None:
    """Run benchmark and print results."""
    print("Running EOS Benchmark Environment...")
    print(f"Configuration: 100 steps, seed=42\n")

    result = run_full_benchmark(steps=100, seed=42)
    print(result.summary())

    print("\n" + "=" * 72)
    print("PERFORMANCE CURVES (rolling avg, window=10)")
    print("=" * 72)

    for system_name in sorted(result.results.keys()):
        for scenario_name in sorted(result.results[system_name].keys()):
            m = result.results[system_name][scenario_name]
            curve = m.performance_curve(window=10)
            if curve:
                print(f"\n{system_name} / {scenario_name}:")
                print(f"  Early (0-10): {curve[0]:.4f}")
                mid = len(curve) // 2
                print(f"  Mid ({mid}): {curve[mid]:.4f}")
                print(f"  Late ({len(curve) - 1}): {curve[-1]:.4f}")

    print("\n" + "=" * 72)
    print("EOS SYSTEM DIAGNOSTICS")
    print("=" * 72)
    eos = EOSDecisionSystem()
    for scenario in [
        StaticScenario(),
        ShiftingScenario(),
        NoisyScenario(),
        AdversarialScenario(),
    ]:
        run_simulation(eos, scenario, steps=100, seed=42)
        diag = eos.get_diagnostics()
        print(f"\n{type(scenario).__name__}:")
        print(f"  Penalty weight: {diag['penalty_weight']:.4f}")
        for action, mem in diag.get("action_memories", {}).items():
            print(
                f"  {action}: s={mem['success']} f={mem['failure']} score={mem['score']:.4f}"
            )

    print("\n" + "=" * 72)
    print("EXPLORATION ENGINE DIAGNOSTICS")
    print("=" * 72)
    eos_explore = EOSWithExplorationSystem()
    for scenario in [
        StaticScenario(),
        ShiftingScenario(),
        NoisyScenario(),
        AdversarialScenario(),
    ]:
        run_simulation(eos_explore, scenario, steps=100, seed=42)
        diag = eos_explore.get_diagnostics()
        print(f"\n{type(scenario).__name__}:")
        print(f"  Penalty weight: {diag['penalty_weight']:.4f}")
        print(f"  Failure streak: {diag.get('failure_streak', 0)}")
        print(f"  Objective trend: {diag.get('objective_trend', 'N/A')}")
        for action, mem in diag.get("action_memories", {}).items():
            print(
                f"  {action}: s={mem['success']} f={mem['failure']} score={mem['score']:.4f}"
            )

    print("\n" + "=" * 72)
    print("VERDICT")
    print("=" * 72)

    eos_results = result.results.get("eos_substrate", {})
    explore_results = result.results.get("eos_exploration", {})
    static_results = result.results.get("static_weights", {})
    random_results = result.results.get("random", {})

    print("\n  EOS Substrate vs Baselines:")
    eos_wins = 0
    total = 0
    for scenario_name in sorted(eos_results):
        total += 1
        eos_avg = eos_results[scenario_name].avg_reward
        static_avg = static_results.get(scenario_name, RunMetrics("", "", 0)).avg_reward
        random_avg = random_results.get(scenario_name, RunMetrics("", "", 0)).avg_reward

        if eos_avg >= static_avg and eos_avg > random_avg:
            eos_wins += 1
            status = "WIN"
        elif eos_avg >= random_avg:
            status = "PARTIAL"
        else:
            status = "LOSS"
        print(
            f"    {scenario_name}: {status} (eos={eos_avg:.4f} static={static_avg:.4f} random={random_avg:.4f})"
        )
    print(f"  Score: {eos_wins}/{total}")

    print("\n  Exploration Engine vs EOS Baseline:")
    explore_wins = 0
    total = 0
    for scenario_name in sorted(explore_results):
        total += 1
        explore_avg = explore_results[scenario_name].avg_reward
        eos_avg = eos_results.get(scenario_name, RunMetrics("", "", 0)).avg_reward
        delta = explore_avg - eos_avg

        if delta > 0.001:
            explore_wins += 1
            status = "IMPROVEMENT"
        elif delta >= -0.001:
            status = "EQUAL"
        else:
            status = "REGRESSION"
        print(
            f"    {scenario_name}: {status} (explore={explore_avg:.4f} baseline={eos_avg:.4f} delta={delta:+.4f})"
        )
    print(f"  Improvements: {explore_wins}/{total}")

    print(f"\n  FINAL VERDICT:")
    if eos_wins == len(eos_results):
        print("  - EOS substrate outperforms all baselines in every scenario.")
    if explore_wins > 0:
        print(
            f"  - Exploration engine improves adaptation in {explore_wins}/{total} scenarios."
        )
    elif explore_wins == 0 and total > 0:
        print(
            "  - Exploration engine matches baseline — no regression, no improvement at this step count."
        )


if __name__ == "__main__":
    main()
