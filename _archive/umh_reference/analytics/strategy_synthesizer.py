"""
StrategySynthesizer — creates new strategies from observed successful behavior.

Observes high-quality outcomes via DecisionTrace, extracts reusable behavioral
traits via deterministic heuristics (no LLM), and introduces new strategies
into the existing STRATEGY_REGISTRY when strict gating conditions are met.

Synthesized strategies compete via the same pick_strategies() → select_best()
pipeline as predefined strategies. They receive no special treatment and are
pruned naturally when their EMA scores decay below competitors.

Design constraints:
    - Deterministic: same traces always produce the same synthesis result.
    - Low-frequency: cooldown between synthesis attempts (default 10 turns).
    - Bounded: MAX_STRATEGIES caps the total pool; excess triggers pruning.
    - Reversible: synthesized strategies decay via StrategyMemory like any other.
    - No LLM calls. No randomness. No mutation mid-turn.

Usage::

    from umh.analytics.strategy_synthesizer import get_synthesizer

    synth = get_synthesizer()
    result = synth.maybe_synthesize(
        traces=session.stats.decision_traces,
        current_turn=session.stats.turns,
    )
    if result is not None:
        print(f"Synthesized: {result.strategy_id}")
"""

from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from umh.decision.trace import DecisionTrace

_log = logging.getLogger(__name__)

# ─── Configuration ───────────────────────────────────────────────────────────

MAX_STRATEGIES = 8
SYNTHESIS_COOLDOWN = 10
MIN_CONFIRMATIONS = 3
HIGH_QUALITY_THRESHOLD = 0.75
MIN_TRACE_WINDOW = 5
TRAIT_ANALYSIS_WINDOW = 10


# ─── Trait Detection (deterministic heuristics) ─────────────────────────────


@dataclass(frozen=True)
class TraitFingerprint:
    """Immutable set of behavioral traits extracted from winning outcomes."""

    has_structure: bool = False
    has_conciseness: bool = False
    has_high_density: bool = False
    has_explicitness: bool = False

    @property
    def trait_key(self) -> str:
        """Deterministic string key for deduplication."""
        parts = []
        if self.has_structure:
            parts.append("struct")
        if self.has_conciseness:
            parts.append("concise")
        if self.has_high_density:
            parts.append("dense")
        if self.has_explicitness:
            parts.append("explicit")
        return "+".join(sorted(parts)) if parts else ""

    @property
    def is_novel(self) -> bool:
        """True if this fingerprint represents a non-trivial trait combination."""
        active = sum(
            [
                self.has_structure,
                self.has_conciseness,
                self.has_high_density,
                self.has_explicitness,
            ]
        )
        return active >= 2


def _extract_traits(trace: DecisionTrace) -> TraitFingerprint:
    """Extract behavioral traits from a single high-quality trace.

    Uses evaluation signals already computed by OutcomeEvaluator —
    no new analysis, no LLM calls.
    """
    signals = trace.signals or {}
    scores = signals.get("dimension_scores", {})

    has_structure = scores.get("structure", 0.0) >= 0.7
    has_conciseness = scores.get("conciseness", 0.0) >= 0.7
    has_high_density = scores.get("relevance", 0.0) >= 0.8
    has_explicitness = scores.get("specificity", 0.0) >= 0.7

    return TraitFingerprint(
        has_structure=has_structure,
        has_conciseness=has_conciseness,
        has_high_density=has_high_density,
        has_explicitness=has_explicitness,
    )


# ─── Synthesis Result ────────────────────────────────────────────────────────


@dataclass(frozen=True)
class SynthesisResult:
    """Output of a successful strategy synthesis."""

    strategy_id: str
    system_directive: str
    prompt_directive: str
    source_traits: TraitFingerprint
    source_strategy: str
    creation_turn: int
    creation_reason: str

    def to_dict(self) -> dict:
        return {
            "strategy_id": self.strategy_id,
            "system_directive": self.system_directive,
            "prompt_directive": self.prompt_directive,
            "source_traits": self.source_traits.trait_key,
            "source_strategy": self.source_strategy,
            "creation_turn": self.creation_turn,
            "creation_reason": self.creation_reason,
        }


# ─── Directive Templates (trait → directive text) ────────────────────────────

_TRAIT_SYSTEM_FRAGMENTS: dict[str, str] = {
    "struct": "Use structured formatting with clear sections and numbered points.",
    "concise": "Be concise — every word must earn its place.",
    "dense": "Maximize information density. Lead with the answer.",
    "explicit": "State assumptions explicitly. Resolve ambiguity upfront.",
}

_TRAIT_PROMPT_FRAGMENTS: dict[str, str] = {
    "struct": "[Approach: organize into numbered sections with headers.]",
    "concise": "[Approach: density over length — cut preamble and filler.]",
    "dense": "[Approach: front-load the answer, maximize signal per sentence.]",
    "explicit": "[Approach: state assumptions, resolve ambiguity before answering.]",
}


def _build_directives(fingerprint: TraitFingerprint) -> tuple[str, str]:
    """Build system and prompt directives from a trait fingerprint."""
    trait_keys = fingerprint.trait_key.split("+") if fingerprint.trait_key else []

    system_parts = [
        _TRAIT_SYSTEM_FRAGMENTS[k] for k in trait_keys if k in _TRAIT_SYSTEM_FRAGMENTS
    ]
    prompt_parts = [
        _TRAIT_PROMPT_FRAGMENTS[k] for k in trait_keys if k in _TRAIT_PROMPT_FRAGMENTS
    ]

    return " ".join(system_parts), " ".join(prompt_parts)


def _make_strategy_id(fingerprint: TraitFingerprint) -> str:
    """Deterministic strategy ID from trait fingerprint.

    Uses a short hash suffix to avoid collisions with predefined strategies
    while remaining human-readable.
    """
    trait_key = fingerprint.trait_key
    if not trait_key:
        return ""
    h = hashlib.sha256(trait_key.encode()).hexdigest()[:6]
    return f"synth_{trait_key.replace('+', '_')}_{h}"


# ─── Core Synthesizer ───────────────────────────────────────────────────────


@dataclass
class StrategySynthesizer:
    """Observes successful outcomes and proposes new strategies.

    Strict gating:
        1. Only considers traces with quality_score >= HIGH_QUALITY_THRESHOLD
        2. Requires MIN_CONFIRMATIONS of the same trait pattern
        3. Enforces SYNTHESIS_COOLDOWN between creations
        4. Rejects duplicates (same trait fingerprint)
        5. Respects MAX_STRATEGIES pool cap
    """

    last_synthesis_turn: int = 0
    pattern_counts: dict[str, int] = field(default_factory=dict)
    synthesized_ids: set[str] = field(default_factory=set)

    def maybe_synthesize(
        self,
        traces: list[DecisionTrace],
        current_turn: int,
    ) -> SynthesisResult | None:
        """Attempt strategy synthesis from recent high-quality traces.

        Returns a SynthesisResult if a new strategy was created, None otherwise.
        Never modifies the traces or any external state — the caller is
        responsible for registering the result.
        """
        if not traces:
            return None

        if current_turn - self.last_synthesis_turn < SYNTHESIS_COOLDOWN:
            return None

        if len(traces) < MIN_TRACE_WINDOW:
            return None

        if self._pool_is_full():
            return None

        window = traces[-TRAIT_ANALYSIS_WINDOW:]

        # Only consider traces newer than the last synthesis turn to prevent
        # counting the same evidence repeatedly across calls (C1 fix).
        new_traces = [t for t in window if t.turn_id > self.last_synthesis_turn]
        if not new_traces:
            return None

        high_quality = [
            t
            for t in new_traces
            if t.quality_score >= HIGH_QUALITY_THRESHOLD
            and t.confidence >= HIGH_QUALITY_THRESHOLD
        ]

        if len(high_quality) < MIN_CONFIRMATIONS:
            return None

        fingerprints: list[tuple[TraitFingerprint, str]] = []
        for t in high_quality:
            fp = _extract_traits(t)
            if fp.is_novel:
                fingerprints.append((fp, t.selected_strategy))

        if not fingerprints:
            return None

        # Count trait pattern occurrences from new traces only.
        # Counts accumulate across calls but each trace is only
        # counted once because we filter by turn_id above.
        pattern_hits: dict[str, list[tuple[TraitFingerprint, str]]] = {}
        for fp, source in fingerprints:
            key = fp.trait_key
            if key not in pattern_hits:
                pattern_hits[key] = []
            pattern_hits[key].append((fp, source))

        for key, hits in pattern_hits.items():
            self.pattern_counts[key] = self.pattern_counts.get(key, 0) + len(hits)

        # Find patterns that meet confirmation threshold
        for key in sorted(pattern_hits.keys()):
            if self.pattern_counts.get(key, 0) < MIN_CONFIRMATIONS:
                continue

            fp, source_strategy = pattern_hits[key][0]
            strategy_id = _make_strategy_id(fp)

            if not strategy_id:
                continue
            if strategy_id in self.synthesized_ids:
                continue
            if self._strategy_exists(strategy_id):
                continue

            system_dir, prompt_dir = _build_directives(fp)

            result = SynthesisResult(
                strategy_id=strategy_id,
                system_directive=system_dir,
                prompt_directive=prompt_dir,
                source_traits=fp,
                source_strategy=source_strategy,
                creation_turn=current_turn,
                creation_reason=f"pattern '{key}' confirmed {self.pattern_counts[key]} times",
            )

            self.synthesized_ids.add(strategy_id)
            self.last_synthesis_turn = current_turn
            _log.info(
                "strategy_synthesizer: created %s from pattern '%s' (turn %d)",
                strategy_id,
                key,
                current_turn,
            )
            return result

        return None

    def _pool_is_full(self) -> bool:
        """Check if the strategy pool has reached MAX_STRATEGIES.

        Fails closed: returns True (pool full) on import failure to prevent
        unbounded growth when the registry is inaccessible.
        """
        try:
            from umh.runtime_engine.multi_strategy import STRATEGY_REGISTRY

            return len(STRATEGY_REGISTRY) >= MAX_STRATEGIES
        except Exception:
            return True

    def _strategy_exists(self, strategy_id: str) -> bool:
        """Check if a strategy ID is already registered.

        Fails closed: returns True (exists) on import failure to prevent
        duplicate creation when the registry is inaccessible.
        """
        try:
            from umh.runtime_engine.multi_strategy import STRATEGY_REGISTRY

            return strategy_id in STRATEGY_REGISTRY
        except Exception:
            return True


def register_synthesized_strategy(result: SynthesisResult) -> bool:
    """Register a synthesized strategy into the live STRATEGY_REGISTRY.

    Uses multi_strategy.register_strategy() (single writer) instead of
    mutating the registry dict directly.

    Returns True if registration succeeded, False if the pool is full
    or the strategy already exists.
    """
    try:
        from umh.runtime_engine.multi_strategy import STRATEGY_REGISTRY, register_strategy

        if result.strategy_id in STRATEGY_REGISTRY:
            return False

        if len(STRATEGY_REGISTRY) >= MAX_STRATEGIES:
            if not _prune_weakest_strategy():
                return False

        success = register_strategy(
            result.strategy_id,
            result.system_directive,
            result.prompt_directive,
        )
        if success:
            _log.info(
                "strategy_synthesizer: registered %s in STRATEGY_REGISTRY",
                result.strategy_id,
            )
        return success
    except Exception as e:
        _log.warning("strategy_synthesizer: registration failed: %s", e)
        return False


def _prune_weakest_strategy() -> bool:
    """Remove the lowest-performing strategy to make room for a new one.

    Only prunes synthesized strategies (prefix 'synth_'). Never prunes
    predefined strategies. Uses multi_strategy.unregister_strategy()
    (single writer). Returns True if a strategy was pruned.
    """
    try:
        from umh.runtime_engine.multi_strategy import STRATEGY_REGISTRY, unregister_strategy
        from umh.strategy.memory import get_strategy_memory

        mem = get_strategy_memory()
        current_turn = mem.global_turn

        synth_strategies = [
            name for name in STRATEGY_REGISTRY if name.startswith("synth_")
        ]
        if not synth_strategies:
            return False

        worst_name = ""
        worst_score = float("inf")
        for name in synth_strategies:
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
                "strategy_synthesizer: pruned %s (score=%.4f)",
                worst_name,
                worst_score,
            )
        return removed
    except Exception as e:
        _log.warning("strategy_synthesizer: pruning failed: %s", e)
        return False


# ─── Module-level singleton ──────────────────────────────────────────────────

_global_synthesizer: StrategySynthesizer | None = None


def get_synthesizer() -> StrategySynthesizer:
    """Return the process-wide strategy synthesizer singleton."""
    global _global_synthesizer
    if _global_synthesizer is None:
        _global_synthesizer = StrategySynthesizer()
    return _global_synthesizer


def reset_synthesizer() -> None:
    """Reset the singleton. Used in tests only."""
    global _global_synthesizer
    _global_synthesizer = None
