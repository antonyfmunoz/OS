"""
StrategyMutation — deterministic strategy evolution via performance-driven transforms.

Complements StrategySynthesizer (creates from success) by evolving from
failure, stagnation, and performance gaps. Four transform types:

    - Expand: broaden criteria (add flexibility directives)
    - Narrow: specialize criteria (add precision directives)
    - Recombine: merge directives from two high-performing strategies
    - Invert: reverse the approach (structured → freeform, concise → verbose)

Mutation triggers are deterministic, derived from StrategyMemory signals:
    A. Persistent underperformance (EMA < threshold over N uses)
    B. High variance (inconsistent outcomes)
    C. Near-misses (high quality but loses arbitration frequently)
    D. Gap detection (no strategy performs well → create from scratch)

Bounded growth: total strategies capped at MAX_STRATEGIES.
No LLM calls. No randomness. Pure transforms from existing data.

Usage::

    from umh.analytics.strategy_mutation import StrategyMutationEngine

    engine = StrategyMutationEngine()
    mutations = engine.evaluate(memory, current_turn)
    for m in mutations:
        engine.register_mutation(m)
"""

from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from umh.strategy.memory import StrategyMemory, StrategyStats

_log = logging.getLogger(__name__)

# ─── Constants ────────────────────────────────────────────────────────────────

MAX_STRATEGIES = 8
MUTATION_COOLDOWN = 10
MIN_USES_FOR_MUTATION = 5

UNDERPERFORMANCE_THRESHOLD = 0.3
VARIANCE_THRESHOLD = 0.15
NEAR_MISS_THRESHOLD = 0.6
GAP_THRESHOLD = 0.4

NOVELTY_INITIAL = 1.3
NOVELTY_DECAY_RATE = 0.05

EXPAND_SUFFIX = " Explore alternative approaches and consider edge cases."
EXPAND_PROMPT = "[Approach: consider multiple angles before committing to one.]"

NARROW_SUFFIX = " Focus precisely on the core requirement. Ignore tangents."
NARROW_PROMPT = "[Approach: narrow scope to the single most important aspect.]"

INVERT_MAP: dict[str, tuple[str, str]] = {
    "clarity": (
        "Use intuitive, flowing language. Prioritize readability over precision.",
        "[Approach: write naturally — trust the reader to infer details.]",
    ),
    "concise": (
        "Be thorough and detailed. Include supporting context and examples.",
        "[Approach: completeness over brevity — leave nothing implied.]",
    ),
    "structured": (
        "Use flowing prose without rigid structure. Let ideas connect naturally.",
        "[Approach: narrative flow — no numbered lists or headers.]",
    ),
    "baseline": (
        "Take an opinionated stance. Be decisive and direct.",
        "[Approach: lead with a clear recommendation, not a balanced overview.]",
    ),
}


# ─── Data model ──────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class StrategyMutation:
    """Immutable record of a strategy mutation."""

    strategy_id: str
    parent_strategy_id: str
    mutation_type: str
    mutation_reason: str
    confidence: float
    system_directive: str
    prompt_directive: str
    creation_turn: int

    def to_dict(self) -> dict:
        return {
            "strategy_id": self.strategy_id,
            "parent_strategy_id": self.parent_strategy_id,
            "mutation_type": self.mutation_type,
            "mutation_reason": self.mutation_reason,
            "confidence": round(self.confidence, 4),
            "creation_turn": self.creation_turn,
        }


# ─── Novelty tracking ───────────────────────────────────────────────────────


def compute_novelty_factor(creation_turn: int, current_turn: int) -> float:
    """Compute novelty factor for a mutated strategy.

    New strategies get a small boost that decays over time.
    Returns a float in [1.0, NOVELTY_INITIAL].
    """
    age = max(0, current_turn - creation_turn)
    import math

    decay = math.exp(-NOVELTY_DECAY_RATE * age)
    return 1.0 + (NOVELTY_INITIAL - 1.0) * decay


# ─── Variance computation ───────────────────────────────────────────────────


def _compute_variance(stats: StrategyStats) -> float:
    """Estimate score variance from EMA deviation.

    Without raw score history, approximate variance from the gap
    between total_score/uses (true mean) and ema_score (weighted recent).
    Large gaps indicate inconsistent performance.
    """
    if stats.uses < 2:
        return 0.0
    true_mean = stats.total_score / stats.uses
    deviation = abs(stats.ema_score - true_mean)
    return deviation


# ─── Mutation Engine ─────────────────────────────────────────────────────────


@dataclass
class StrategyMutationEngine:
    """Deterministic strategy evolution engine.

    Evaluates all strategies in memory against mutation triggers.
    Produces at most one mutation per call (bounded).
    """

    last_mutation_turn: int = 0
    mutation_history: list[str] = field(default_factory=list)

    def evaluate(
        self,
        memory: StrategyMemory,
        current_turn: int,
    ) -> list[StrategyMutation]:
        """Evaluate all strategies for mutation triggers.

        Returns a list of mutations (at most one per call to bound growth).
        Does NOT register mutations — caller is responsible.
        """
        if current_turn - self.last_mutation_turn < MUTATION_COOLDOWN:
            return []

        if self._pool_is_full():
            if not self._can_prune():
                return []

        mutations: list[StrategyMutation] = []

        ranked = memory.rank_strategies()
        if not ranked:
            return []

        stats_map: dict[str, StrategyStats] = {name: s for name, s in ranked}

        # ── Trigger A: Persistent underperformance ─────────��──────
        for name, stats in ranked:
            if stats.uses < MIN_USES_FOR_MUTATION:
                continue
            if stats.ema_score < UNDERPERFORMANCE_THRESHOLD:
                mutation = self._mutate_underperformer(name, stats, current_turn)
                if mutation is not None:
                    mutations.append(mutation)
                    break

        if mutations:
            return mutations[:1]

        # ── Trigger B: High variance ──────────────────────────────
        for name, stats in ranked:
            if stats.uses < MIN_USES_FOR_MUTATION:
                continue
            variance = _compute_variance(stats)
            if variance > VARIANCE_THRESHOLD:
                mutation = self._mutate_high_variance(name, stats, current_turn)
                if mutation is not None:
                    mutations.append(mutation)
                    break

        if mutations:
            return mutations[:1]

        # ── Trigger C: Near-misses ────────────────────────────────
        for name, stats in ranked:
            if stats.uses < MIN_USES_FOR_MUTATION:
                continue
            if stats.ema_score >= NEAR_MISS_THRESHOLD and stats.wins < stats.uses * 0.3:
                mutation = self._mutate_near_miss(name, stats, current_turn)
                if mutation is not None:
                    mutations.append(mutation)
                    break

        if mutations:
            return mutations[:1]

        # ── Trigger D: Gap detection ──────────────────────────────
        best_score = ranked[0][1].ema_score if ranked else 0.0
        if (
            best_score < GAP_THRESHOLD
            and len(ranked) >= 2
            and all(s.uses >= MIN_USES_FOR_MUTATION for _, s in ranked[:2])
        ):
            mutation = self._mutate_gap(ranked, current_turn)
            if mutation is not None:
                mutations.append(mutation)

        return mutations[:1]

    def _mutate_underperformer(
        self,
        name: str,
        stats: StrategyStats,
        current_turn: int,
    ) -> StrategyMutation | None:
        """Trigger A: Narrow an underperforming strategy to specialize."""
        strategy_id = self._make_mutation_id(name, "narrow", current_turn)
        if self._already_mutated(strategy_id):
            return None

        parent_system, parent_prompt = self._get_parent_directives(name)

        return StrategyMutation(
            strategy_id=strategy_id,
            parent_strategy_id=name,
            mutation_type="narrow",
            mutation_reason=f"underperformance:ema={stats.ema_score:.2f}<{UNDERPERFORMANCE_THRESHOLD}",
            confidence=0.3,
            system_directive=parent_system + NARROW_SUFFIX,
            prompt_directive=parent_prompt + " " + NARROW_PROMPT
            if parent_prompt
            else NARROW_PROMPT,
            creation_turn=current_turn,
        )

    def _mutate_high_variance(
        self,
        name: str,
        stats: StrategyStats,
        current_turn: int,
    ) -> StrategyMutation | None:
        """Trigger B: Narrow a high-variance strategy to stabilize."""
        strategy_id = self._make_mutation_id(name, "narrow_var", current_turn)
        if self._already_mutated(strategy_id):
            return None

        parent_system, parent_prompt = self._get_parent_directives(name)

        variance = _compute_variance(stats)
        return StrategyMutation(
            strategy_id=strategy_id,
            parent_strategy_id=name,
            mutation_type="narrow",
            mutation_reason=f"high_variance:var={variance:.2f}>{VARIANCE_THRESHOLD}",
            confidence=0.3,
            system_directive=parent_system + NARROW_SUFFIX,
            prompt_directive=parent_prompt + " " + NARROW_PROMPT
            if parent_prompt
            else NARROW_PROMPT,
            creation_turn=current_turn,
        )

    def _mutate_near_miss(
        self,
        name: str,
        stats: StrategyStats,
        current_turn: int,
    ) -> StrategyMutation | None:
        """Trigger C: Expand a near-miss strategy to increase versatility."""
        strategy_id = self._make_mutation_id(name, "expand", current_turn)
        if self._already_mutated(strategy_id):
            return None

        parent_system, parent_prompt = self._get_parent_directives(name)

        win_rate = stats.wins / stats.uses if stats.uses > 0 else 0
        return StrategyMutation(
            strategy_id=strategy_id,
            parent_strategy_id=name,
            mutation_type="expand",
            mutation_reason=f"near_miss:ema={stats.ema_score:.2f},win_rate={win_rate:.2f}",
            confidence=0.4,
            system_directive=parent_system + EXPAND_SUFFIX,
            prompt_directive=parent_prompt + " " + EXPAND_PROMPT
            if parent_prompt
            else EXPAND_PROMPT,
            creation_turn=current_turn,
        )

    def _mutate_gap(
        self,
        ranked: list[tuple[str, StrategyStats]],
        current_turn: int,
    ) -> StrategyMutation | None:
        """Trigger D: Recombine top-2 strategies when all underperform."""
        if len(ranked) < 2:
            return None

        name_a, stats_a = ranked[0]
        name_b, stats_b = ranked[1]

        strategy_id = self._make_mutation_id(
            f"{name_a}+{name_b}", "recombine", current_turn
        )
        if self._already_mutated(strategy_id):
            # Fall back to invert of the best
            return self._mutate_invert(name_a, stats_a, current_turn)

        sys_a, prompt_a = self._get_parent_directives(name_a)
        sys_b, prompt_b = self._get_parent_directives(name_b)

        combined_system = f"{sys_a} {sys_b}".strip()
        combined_prompt = f"{prompt_a} {prompt_b}".strip()

        return StrategyMutation(
            strategy_id=strategy_id,
            parent_strategy_id=f"{name_a}+{name_b}",
            mutation_type="recombine",
            mutation_reason=f"gap:best_ema={stats_a.ema_score:.2f}<{GAP_THRESHOLD}",
            confidence=0.25,
            system_directive=combined_system,
            prompt_directive=combined_prompt,
            creation_turn=current_turn,
        )

    def _mutate_invert(
        self,
        name: str,
        stats: StrategyStats,
        current_turn: int,
    ) -> StrategyMutation | None:
        """Invert a strategy's approach direction."""
        strategy_id = self._make_mutation_id(name, "invert", current_turn)
        if self._already_mutated(strategy_id):
            return None

        base_name = name.split("_")[0] if "_" in name else name
        if base_name in INVERT_MAP:
            inv_sys, inv_prompt = INVERT_MAP[base_name]
        else:
            parent_system, parent_prompt = self._get_parent_directives(name)
            inv_sys = (
                f"Take the opposite approach to: {parent_system}"
                if parent_system
                else ""
            )
            inv_prompt = "[Approach: try the reverse of what was previously attempted.]"

        return StrategyMutation(
            strategy_id=strategy_id,
            parent_strategy_id=name,
            mutation_type="invert",
            mutation_reason=f"gap_invert:ema={stats.ema_score:.2f}",
            confidence=0.2,
            system_directive=inv_sys,
            prompt_directive=inv_prompt,
            creation_turn=current_turn,
        )

    def register_mutation(self, mutation: StrategyMutation) -> bool:
        """Register a mutation into the live STRATEGY_REGISTRY.

        Prunes if at cap. Returns True on success.
        """
        try:
            from umh.runtime_engine.multi_strategy import STRATEGY_REGISTRY, register_strategy

            if mutation.strategy_id in STRATEGY_REGISTRY:
                return False

            if len(STRATEGY_REGISTRY) >= MAX_STRATEGIES:
                if not _prune_weakest_mutant():
                    return False

            success = register_strategy(
                mutation.strategy_id,
                mutation.system_directive,
                mutation.prompt_directive,
            )
            if success:
                self.mutation_history.append(mutation.strategy_id)
                self.last_mutation_turn = mutation.creation_turn
                _log.info(
                    "strategy_mutation: registered %s (type=%s, parent=%s)",
                    mutation.strategy_id,
                    mutation.mutation_type,
                    mutation.parent_strategy_id,
                )
            return success
        except Exception as e:
            _log.warning("strategy_mutation: registration failed: %s", e)
            return False

    def _make_mutation_id(self, parent: str, mutation_type: str, turn: int) -> str:
        """Deterministic mutation ID from parent + type + turn."""
        raw = f"{parent}:{mutation_type}:{turn}"
        h = hashlib.sha256(raw.encode()).hexdigest()[:6]
        return f"mut_{mutation_type}_{h}"

    def _already_mutated(self, strategy_id: str) -> bool:
        return strategy_id in self.mutation_history

    def _get_parent_directives(self, name: str) -> tuple[str, str]:
        """Get system and prompt directives for a parent strategy."""
        try:
            from umh.runtime_engine.multi_strategy import (
                STRATEGY_REGISTRY,
                STRATEGY_PROMPT_DIRECTIVES,
            )

            return (
                STRATEGY_REGISTRY.get(name, ""),
                STRATEGY_PROMPT_DIRECTIVES.get(name, ""),
            )
        except Exception:
            return "", ""

    def _pool_is_full(self) -> bool:
        try:
            from umh.runtime_engine.multi_strategy import STRATEGY_REGISTRY

            return len(STRATEGY_REGISTRY) >= MAX_STRATEGIES
        except Exception:
            return True

    def _can_prune(self) -> bool:
        try:
            from umh.runtime_engine.multi_strategy import STRATEGY_REGISTRY

            return any(
                name.startswith("mut_") or name.startswith("synth_")
                for name in STRATEGY_REGISTRY
            )
        except Exception:
            return False


def _prune_weakest_mutant() -> bool:
    """Remove the lowest-performing mutated strategy.

    Only prunes strategies with 'mut_' prefix. Never prunes predefined.
    """
    try:
        from umh.runtime_engine.multi_strategy import STRATEGY_REGISTRY, unregister_strategy
        from umh.strategy.memory import get_strategy_memory

        mem = get_strategy_memory()
        current_turn = mem.global_turn

        mutants = [name for name in STRATEGY_REGISTRY if name.startswith("mut_")]
        if not mutants:
            return False

        worst_name = ""
        worst_score = float("inf")
        for name in mutants:
            stats = mem.get_stats(name)
            score = stats.effective_score(current_turn) if stats else 0.0
            if score < worst_score:
                worst_score = score
                worst_name = name

        if not worst_name:
            return False

        removed = unregister_strategy(worst_name)
        if removed:
            _log.info(
                "strategy_mutation: pruned %s (score=%.4f)",
                worst_name,
                worst_score,
            )
        return removed
    except Exception as e:
        _log.warning("strategy_mutation: pruning failed: %s", e)
        return False


def compute_strategy_score(
    base_score: float,
    strategy_confidence: float,
    creation_turn: int | None,
    current_turn: int,
) -> float:
    """Compute selection-pressure-adjusted strategy score.

    strategy_score = base_score * strategy_confidence * novelty_factor
    """
    novelty = 1.0
    if creation_turn is not None:
        novelty = compute_novelty_factor(creation_turn, current_turn)
    return base_score * strategy_confidence * novelty


# ─── Module-level singleton ──────────────────────────────────────────────────

_global_engine: StrategyMutationEngine | None = None


def get_mutation_engine() -> StrategyMutationEngine:
    """Return the process-wide strategy mutation engine singleton."""
    global _global_engine
    if _global_engine is None:
        _global_engine = StrategyMutationEngine()
    return _global_engine


def reset_mutation_engine() -> None:
    """Reset the singleton. Used in tests only."""
    global _global_engine
    _global_engine = None
