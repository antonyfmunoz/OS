"""
World State Modeling — structured environment representation for UMH.

Provides a state abstraction layer that captures the environment context
in which decisions are made. Enables state-conditioned learning: the
system can generalize behavior across similar states and condition
strategy/goal selection on environment structure.

Components:
    Entity     — typed object with attributes (goal, strategy, plan, etc.)
    WorldState — frozen snapshot of entities, relationships, and features
    StateExtractor  — derives WorldState from per-turn runtime signals
    StateSimilarity — computes similarity between two WorldStates
    StateCluster    — groups similar states with associated performance
    WorldStateEngine — stateful engine: extraction, clustering, conditioning

State extraction sources:
    - Active goals (count, priorities, blend entropy)
    - Strategy rankings (top strategy score, strategy count, variance)
    - Execution signals (quality trend, confidence, exploration rate)
    - Plan state (active plans, plan confidence)

No LLM calls. No randomness. Deterministic state lifecycle.

Usage::

    from umh.world.state import (
        WorldStateEngine, get_world_state_engine, reset_world_state_engine,
    )

    engine = get_world_state_engine()
    state = engine.extract_state(registry, traces, turn)
    cluster = engine.get_nearest_cluster(state)
    bias = engine.get_conditioning_bias(state)
"""

from __future__ import annotations

import hashlib
import logging
import math
from dataclasses import dataclass, field

_log = logging.getLogger(__name__)

# ─── Constants ──────────────────────────────────────────────────────────────

MAX_CLUSTERS = 8
MAX_STATES_PER_CLUSTER = 10
MAX_STATE_HISTORY = 50
CLUSTER_SIMILARITY_THRESHOLD = 0.70
MIN_CLUSTER_SIZE = 2
FEATURE_KEYS = (
    "goal_count",
    "active_goal_priority",
    "blend_entropy",
    "exploration_rate",
    "quality_trend",
    "confidence_avg",
    "strategy_variance",
    "plan_count",
    "turn_position",
    "goal_diversity",
)
CONDITIONING_WEIGHT = 0.15
TRANSFER_SIMILARITY_THRESHOLD = 0.5
TRANSFER_WEIGHT_SCALE = 0.10
MAX_LEARNED_STATE_BIAS = 0.10
REINFORCEMENT_ALPHA = 0.3
MIN_REINFORCEMENT_OBSERVATIONS = 3

# ─── Data models ────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class Entity:
    """A typed object in the world state."""

    entity_id: str
    entity_type: str
    attributes: tuple[tuple[str, object], ...] = ()

    def to_dict(self) -> dict:
        return {
            "entity_id": self.entity_id,
            "entity_type": self.entity_type,
            "attributes": dict(self.attributes),
        }

    def attr(self, key: str, default: object = None) -> object:
        for k, v in self.attributes:
            if k == key:
                return v
        return default


@dataclass(frozen=True)
class WorldState:
    """Frozen snapshot of the environment at a single turn."""

    state_id: str
    timestamp: int
    entities: tuple[Entity, ...] = ()
    relationships: tuple[tuple[str, str, str], ...] = ()
    features: tuple[tuple[str, float], ...] = ()
    derived_signals: tuple[tuple[str, float], ...] = ()

    def to_dict(self) -> dict:
        return {
            "state_id": self.state_id,
            "timestamp": self.timestamp,
            "entities": [e.to_dict() for e in self.entities],
            "relationships": [
                {"from": r[0], "relation": r[1], "to": r[2]} for r in self.relationships
            ],
            "features": dict(self.features),
            "derived_signals": dict(self.derived_signals),
        }

    @property
    def feature_dict(self) -> dict[str, float]:
        return dict(self.features)

    @property
    def entity_ids(self) -> set[str]:
        return {e.entity_id for e in self.entities}

    @property
    def entity_types(self) -> set[str]:
        return {e.entity_type for e in self.entities}

    def get_entity(self, entity_id: str) -> Entity | None:
        for e in self.entities:
            if e.entity_id == entity_id:
                return e
        return None

    def get_feature(self, key: str, default: float = 0.0) -> float:
        for k, v in self.features:
            if k == key:
                return v
        return default


NO_STATE = WorldState(state_id="none", timestamp=0)


# ─── State similarity ──────────────────────────────────────────────────────


def compute_feature_similarity(a: WorldState, b: WorldState) -> float:
    """Cosine similarity between feature vectors."""
    fa = a.feature_dict
    fb = b.feature_dict
    keys = set(fa.keys()) | set(fb.keys())
    if not keys:
        return 1.0

    dot = sum(fa.get(k, 0.0) * fb.get(k, 0.0) for k in keys)
    mag_a = math.sqrt(sum(fa.get(k, 0.0) ** 2 for k in keys))
    mag_b = math.sqrt(sum(fb.get(k, 0.0) ** 2 for k in keys))

    if mag_a == 0.0 or mag_b == 0.0:
        return 0.0

    return max(0.0, min(1.0, dot / (mag_a * mag_b)))


def compute_entity_overlap(a: WorldState, b: WorldState) -> float:
    """Jaccard overlap of entity IDs."""
    ids_a = a.entity_ids
    ids_b = b.entity_ids
    if not ids_a and not ids_b:
        return 1.0
    union = ids_a | ids_b
    if not union:
        return 1.0
    return len(ids_a & ids_b) / len(union)


def compute_structural_similarity(a: WorldState, b: WorldState) -> float:
    """Overlap of relationship tuples."""
    rels_a = set(a.relationships)
    rels_b = set(b.relationships)
    if not rels_a and not rels_b:
        return 1.0
    union = rels_a | rels_b
    if not union:
        return 1.0
    return len(rels_a & rels_b) / len(union)


def state_similarity(a: WorldState, b: WorldState) -> float:
    """Combined similarity: weighted average of feature, entity, structural."""
    feat = compute_feature_similarity(a, b)
    entity = compute_entity_overlap(a, b)
    structural = compute_structural_similarity(a, b)
    return 0.5 * feat + 0.3 * entity + 0.2 * structural


# ─── State transfer weight ────────────────────────────────────────────────


def compute_state_transfer_weight(similarity: float) -> float:
    """Deterministic transfer weight from state similarity.

    Below TRANSFER_SIMILARITY_THRESHOLD: 0.0 (no transfer).
    Above: smooth linear ramp from 0.0 to 1.0, clamped.
    """
    if similarity < TRANSFER_SIMILARITY_THRESHOLD:
        return 0.0
    raw = (similarity - TRANSFER_SIMILARITY_THRESHOLD) / (
        1.0 - TRANSFER_SIMILARITY_THRESHOLD
    )
    return max(0.0, min(1.0, raw))


# ─── State extraction ──────────────────────────────────────────────────────


def _make_state_id(turn: int, features: dict[str, float]) -> str:
    """Deterministic state ID from turn and feature vector."""
    sig = f"t{turn}_" + "_".join(f"{k}={v:.4f}" for k, v in sorted(features.items()))
    return "ws_" + hashlib.md5(sig.encode()).hexdigest()[:10]


def extract_state(
    registry: object | None = None,
    traces: list | None = None,
    current_turn: int = 0,
    exploration_rate: float | None = None,
    plan_count: int = 0,
    blended_entropy: float | None = None,
    strategy_rankings: list[tuple[str, object]] | None = None,
    strategy_turn: int = 0,
) -> WorldState:
    """Derive a WorldState from current runtime signals."""
    traces = traces or []
    features: dict[str, float] = {}
    entities: list[Entity] = []
    relationships: list[tuple[str, str, str]] = []

    # ── Goal features ──────────────────────────────────────────────
    goal_count = 0
    active_priority = 0.5
    diversity = 0.0

    if registry is not None:
        goals = []
        try:
            goals = registry.get_all_goals()
        except Exception:
            pass

        goal_count = len(goals)
        if goals:
            priorities = [getattr(g, "priority", 0.5) for g in goals]
            active_priority = max(priorities)

            criteria_keys: set[str] = set()
            for g in goals:
                sc = getattr(g, "success_criteria", None)
                if sc:
                    criteria_keys.update(sc.keys())
                entities.append(
                    Entity(
                        entity_id=g.goal_id,
                        entity_type="goal",
                        attributes=(
                            ("priority", g.priority),
                            ("active", getattr(g, "active", True)),
                        ),
                    )
                )
            diversity = min(1.0, len(criteria_keys) / 10.0) if criteria_keys else 0.0

            for i in range(len(goals)):
                for j in range(i + 1, len(goals)):
                    relationships.append(
                        (goals[i].goal_id, "coexists_with", goals[j].goal_id)
                    )

    features["goal_count"] = float(goal_count)
    features["active_goal_priority"] = active_priority
    features["goal_diversity"] = diversity
    features["blend_entropy"] = blended_entropy if blended_entropy is not None else 0.0

    # ── Exploration ────────────────────────────────────────────────
    features["exploration_rate"] = (
        exploration_rate if exploration_rate is not None else 0.5
    )

    # ── Quality trend from traces ──────────────────────────────────
    quality_trend = 0.0
    confidence_avg = 0.5
    if traces:
        recent = traces[-5:]
        qualities = []
        confidences = []
        for t in recent:
            q = getattr(t, "quality_score", None)
            c = getattr(t, "confidence", None)
            if q is not None:
                qualities.append(q)
            if c is not None:
                confidences.append(c)

        if len(qualities) >= 2:
            first_half = qualities[: len(qualities) // 2]
            second_half = qualities[len(qualities) // 2 :]
            avg_first = sum(first_half) / len(first_half)
            avg_second = sum(second_half) / len(second_half)
            quality_trend = avg_second - avg_first
        elif qualities:
            quality_trend = 0.0

        if confidences:
            confidence_avg = sum(confidences) / len(confidences)

    features["quality_trend"] = quality_trend
    features["confidence_avg"] = confidence_avg

    # ── Strategy variance ──────────────────────────────────────────
    strategy_variance = 0.0
    if strategy_rankings and len(strategy_rankings) >= 2:
        try:
            scores = [
                s.effective_score(strategy_turn)
                if hasattr(s, "effective_score")
                else getattr(s, "ema_score", 0.0)
                for _, s in strategy_rankings
            ]
            mean = sum(scores) / len(scores)
            variance = sum((sc - mean) ** 2 for sc in scores) / len(scores)
            strategy_variance = min(1.0, variance * 10.0)

            for name, stats in strategy_rankings:
                entities.append(
                    Entity(
                        entity_id=f"strategy_{name}",
                        entity_type="strategy",
                        attributes=(
                            ("ema_score", round(getattr(stats, "ema_score", 0.0), 4)),
                            ("uses", getattr(stats, "uses", 0)),
                        ),
                    )
                )
        except Exception:
            pass

    features["strategy_variance"] = strategy_variance

    # ── Plan state ─────────────────────────────────────────────────
    features["plan_count"] = float(plan_count)

    # ── Turn position (normalized) ─────────────────────────────────
    features["turn_position"] = min(1.0, current_turn / 100.0)

    # ── Derived signals from traces ────────────────────────────────
    derived: list[tuple[str, float]] = []
    if traces:
        last = traces[-1]
        gs = getattr(last, "goal_score", None)
        if gs is not None:
            derived.append(("last_goal_score", gs))
        gd = getattr(last, "goal_delta", None)
        if gd is not None:
            derived.append(("last_goal_delta", gd))

    state_id = _make_state_id(current_turn, features)

    return WorldState(
        state_id=state_id,
        timestamp=current_turn,
        entities=tuple(entities),
        relationships=tuple(relationships),
        features=tuple(sorted(features.items())),
        derived_signals=tuple(derived),
    )


# ─── State clustering ──────────────────────────────────────────────────────


@dataclass
class ClusterPerformance:
    """Tracks which strategies/goals perform best in a cluster."""

    strategy_scores: dict[str, float] = field(default_factory=dict)
    strategy_counts: dict[str, int] = field(default_factory=dict)
    goal_scores: dict[str, float] = field(default_factory=dict)
    goal_counts: dict[str, int] = field(default_factory=dict)
    avg_utility: float = 0.5
    observation_count: int = 0
    quality_ema: float = 0.5
    last_used_turn: int = 0

    def record(
        self,
        strategy: str | None = None,
        strategy_score: float = 0.0,
        goal_id: str | None = None,
        goal_score: float = 0.0,
        utility: float = 0.5,
    ) -> None:
        self.observation_count += 1
        alpha = 0.3
        self.avg_utility = alpha * utility + (1 - alpha) * self.avg_utility

        if strategy:
            self.strategy_counts[strategy] = self.strategy_counts.get(strategy, 0) + 1
            prev = self.strategy_scores.get(strategy, strategy_score)
            self.strategy_scores[strategy] = alpha * strategy_score + (1 - alpha) * prev

        if goal_id:
            self.goal_counts[goal_id] = self.goal_counts.get(goal_id, 0) + 1
            prev_g = self.goal_scores.get(goal_id, goal_score)
            self.goal_scores[goal_id] = alpha * goal_score + (1 - alpha) * prev_g

    def reinforce(self, credit_weight: float, quality_signal: float, turn: int) -> None:
        """Update quality_ema using causal credit weight as learning rate scale."""
        if credit_weight < 0.01:
            return
        alpha = REINFORCEMENT_ALPHA * min(credit_weight, 1.0)
        self.quality_ema = alpha * quality_signal + (1 - alpha) * self.quality_ema
        self.last_used_turn = turn

    def best_strategy(self) -> str | None:
        if not self.strategy_scores:
            return None
        return max(
            self.strategy_scores,
            key=lambda k: (self.strategy_scores[k], self.strategy_counts.get(k, 0)),
        )

    def best_goal(self) -> str | None:
        if not self.goal_scores:
            return None
        return max(
            self.goal_scores,
            key=lambda k: (self.goal_scores[k], self.goal_counts.get(k, 0)),
        )

    def to_dict(self) -> dict:
        return {
            "strategy_scores": {
                k: round(v, 4) for k, v in self.strategy_scores.items()
            },
            "strategy_counts": dict(self.strategy_counts),
            "goal_scores": {k: round(v, 4) for k, v in self.goal_scores.items()},
            "goal_counts": dict(self.goal_counts),
            "avg_utility": round(self.avg_utility, 4),
            "observation_count": self.observation_count,
            "quality_ema": round(self.quality_ema, 4),
            "last_used_turn": self.last_used_turn,
        }


@dataclass
class StateCluster:
    """A group of similar world states with associated performance data."""

    cluster_id: str
    centroid_features: dict[str, float] = field(default_factory=dict)
    member_state_ids: list[str] = field(default_factory=list)
    performance: ClusterPerformance = field(default_factory=ClusterPerformance)
    size: int = 0

    def add_state(self, state: WorldState) -> None:
        if state.state_id not in self.member_state_ids:
            self.member_state_ids.append(state.state_id)
            if len(self.member_state_ids) > MAX_STATES_PER_CLUSTER:
                self.member_state_ids = self.member_state_ids[-MAX_STATES_PER_CLUSTER:]
        self.size = len(self.member_state_ids)
        self._update_centroid(state)

    def _update_centroid(self, state: WorldState) -> None:
        """Incremental centroid update via running average."""
        fd = state.feature_dict
        n = self.size
        if n <= 1:
            self.centroid_features = dict(fd)
            return
        for k in FEATURE_KEYS:
            old = self.centroid_features.get(k, 0.0)
            new = fd.get(k, 0.0)
            self.centroid_features[k] = old + (new - old) / n

    def centroid_similarity(self, state: WorldState) -> float:
        """Similarity between a state and this cluster's centroid."""
        fd = state.feature_dict
        if not self.centroid_features:
            return 0.0

        keys = set(self.centroid_features.keys()) | set(fd.keys())
        dot = sum(self.centroid_features.get(k, 0.0) * fd.get(k, 0.0) for k in keys)
        mag_c = math.sqrt(sum(self.centroid_features.get(k, 0.0) ** 2 for k in keys))
        mag_s = math.sqrt(sum(fd.get(k, 0.0) ** 2 for k in keys))

        if mag_c == 0.0 or mag_s == 0.0:
            return 0.0

        return max(0.0, min(1.0, dot / (mag_c * mag_s)))

    def to_dict(self) -> dict:
        return {
            "cluster_id": self.cluster_id,
            "centroid_features": {
                k: round(v, 4) for k, v in self.centroid_features.items()
            },
            "size": self.size,
            "performance": self.performance.to_dict(),
        }


# ─── Conditioning bias ─────────────────────────────────────────────────────


@dataclass(frozen=True)
class ConditioningBias:
    """Bias signals derived from state-cluster matching."""

    cluster_id: str | None
    cluster_similarity: float
    strategy_bias: dict[str, float]
    goal_bias: dict[str, float]
    expected_utility: float

    def to_dict(self) -> dict:
        return {
            "cluster_id": self.cluster_id,
            "cluster_similarity": round(self.cluster_similarity, 4),
            "strategy_bias": {k: round(v, 4) for k, v in self.strategy_bias.items()},
            "goal_bias": {k: round(v, 4) for k, v in self.goal_bias.items()},
            "expected_utility": round(self.expected_utility, 4),
        }


NO_BIAS = ConditioningBias(
    cluster_id=None,
    cluster_similarity=0.0,
    strategy_bias={},
    goal_bias={},
    expected_utility=0.5,
)


# ─── World State Engine ────────────────────────────────────────────────────


class WorldStateEngine:
    """Stateful engine for world state extraction, clustering, and conditioning."""

    def __init__(self) -> None:
        self._clusters: dict[str, StateCluster] = {}
        self._state_history: list[WorldState] = []
        self._current_state: WorldState | None = None

    @property
    def cluster_count(self) -> int:
        return len(self._clusters)

    @property
    def state_count(self) -> int:
        return len(self._state_history)

    @property
    def current_state(self) -> WorldState | None:
        return self._current_state

    def extract_and_record(
        self,
        registry: object | None = None,
        traces: list | None = None,
        current_turn: int = 0,
        exploration_rate: float | None = None,
        plan_count: int = 0,
        blended_entropy: float | None = None,
        strategy_rankings: list[tuple[str, object]] | None = None,
        strategy_turn: int = 0,
    ) -> WorldState:
        """Extract state from runtime signals and record it."""
        state = extract_state(
            registry=registry,
            traces=traces,
            current_turn=current_turn,
            exploration_rate=exploration_rate,
            plan_count=plan_count,
            blended_entropy=blended_entropy,
            strategy_rankings=strategy_rankings,
            strategy_turn=strategy_turn,
        )
        self._current_state = state
        self._state_history.append(state)
        if len(self._state_history) > MAX_STATE_HISTORY:
            self._state_history = self._state_history[-MAX_STATE_HISTORY:]

        self._assign_to_cluster(state)
        return state

    def record_outcome(
        self,
        state: WorldState,
        strategy: str | None = None,
        strategy_score: float = 0.0,
        goal_id: str | None = None,
        goal_score: float = 0.0,
        utility: float = 0.5,
    ) -> None:
        """Record performance data for the cluster containing this state."""
        cluster = self._find_best_cluster(state)
        if cluster is not None:
            cluster.performance.record(
                strategy=strategy,
                strategy_score=strategy_score,
                goal_id=goal_id,
                goal_score=goal_score,
                utility=utility,
            )

    def get_nearest_cluster(self, state: WorldState) -> StateCluster | None:
        """Find the cluster most similar to a given state."""
        if not self._clusters:
            return None

        best_cluster = None
        best_sim = -1.0

        for cluster in self._clusters.values():
            sim = cluster.centroid_similarity(state)
            if sim > best_sim:
                best_sim = sim
                best_cluster = cluster

        if best_sim < CLUSTER_SIMILARITY_THRESHOLD:
            return None

        return best_cluster

    def get_conditioning_bias(self, state: WorldState) -> ConditioningBias:
        """Compute conditioning bias from the nearest cluster's performance history."""
        cluster = self.get_nearest_cluster(state)
        if cluster is None or cluster.performance.observation_count < MIN_CLUSTER_SIZE:
            return NO_BIAS

        sim = cluster.centroid_similarity(state)
        perf = cluster.performance

        strategy_bias: dict[str, float] = {}
        for s_name, s_score in perf.strategy_scores.items():
            strategy_bias[s_name] = (s_score - 0.5) * CONDITIONING_WEIGHT * sim

        goal_bias: dict[str, float] = {}
        for g_id, g_score in perf.goal_scores.items():
            goal_bias[g_id] = (g_score - 0.5) * CONDITIONING_WEIGHT * sim

        return ConditioningBias(
            cluster_id=cluster.cluster_id,
            cluster_similarity=sim,
            strategy_bias=strategy_bias,
            goal_bias=goal_bias,
            expected_utility=perf.avg_utility,
        )

    def get_strategy_transfer_scores(
        self,
        state: WorldState,
    ) -> dict[str, float]:
        """Compute transfer scores for strategies from similar clusters.

        Aggregates EMA strategy scores across all clusters weighted by
        their similarity to the given state. Returns {strategy: score}.
        """
        scores: dict[str, float] = {}
        weights: dict[str, float] = {}

        for cluster in self._clusters.values():
            if cluster.performance.observation_count < MIN_CLUSTER_SIZE:
                continue
            sim = cluster.centroid_similarity(state)
            tw = compute_state_transfer_weight(sim)
            if tw <= 0.0:
                continue

            for s_name, s_score in cluster.performance.strategy_scores.items():
                scores[s_name] = scores.get(s_name, 0.0) + s_score * tw
                weights[s_name] = weights.get(s_name, 0.0) + tw

        result: dict[str, float] = {}
        for s_name in scores:
            if weights[s_name] > 0:
                result[s_name] = round(
                    (scores[s_name] / weights[s_name]) * TRANSFER_WEIGHT_SCALE, 4
                )
        return result

    def get_plan_transfer_score(
        self,
        state: WorldState,
        plan_goal_ids: tuple[str, ...],
        traces: list | None = None,
    ) -> float:
        """Compute transfer score for a plan from similar historical states.

        Looks at recent traces to find turns where similar goal chains
        succeeded in similar world states. Returns a bounded score in [0, 1].
        """
        traces = traces or []
        if not traces or not plan_goal_ids:
            return 0.0

        plan_goal_set = set(plan_goal_ids)
        total_score = 0.0
        total_weight = 0.0

        for trace in traces:
            t_goal = getattr(trace, "active_goal_id", None)
            if t_goal is None or t_goal not in plan_goal_set:
                continue

            t_quality = getattr(trace, "quality_score", 0.0)
            t_cluster = getattr(trace, "world_state_cluster", None)
            t_similarity = getattr(trace, "world_state_similarity", None)

            if t_cluster is None or t_similarity is None:
                continue

            tw = compute_state_transfer_weight(t_similarity)
            if tw <= 0.0:
                continue

            current_sim = 0.0
            cluster = self._clusters.get(t_cluster)
            if cluster is not None:
                current_sim = cluster.centroid_similarity(state)

            cross_tw = compute_state_transfer_weight(current_sim)
            if cross_tw <= 0.0:
                continue

            combined = tw * cross_tw
            total_score += t_quality * combined
            total_weight += combined

        if total_weight <= 0.0:
            return 0.0

        return max(0.0, min(1.0, (total_score / total_weight) * TRANSFER_WEIGHT_SCALE))

    def reinforce_cluster(
        self,
        cluster_id: str,
        credit_weight: float,
        quality_signal: float,
        turn: int,
    ) -> bool:
        """Reinforce a cluster's quality_ema using causal credit weight.

        Returns True if reinforcement was applied, False otherwise.
        """
        cluster = self._clusters.get(cluster_id)
        if cluster is None:
            return False
        if cluster.performance.observation_count < MIN_REINFORCEMENT_OBSERVATIONS:
            return False
        cluster.performance.reinforce(credit_weight, quality_signal, turn)
        return True

    def get_learned_state_bias(self, state: WorldState) -> dict[str, float]:
        """Compute learned bias from reinforced cluster quality.

        Returns strategy-keyed bias dict bounded by MAX_LEARNED_STATE_BIAS.
        Formula: (quality_ema - 0.5) * MAX_LEARNED_STATE_BIAS * similarity
        """
        cluster = self.get_nearest_cluster(state)
        if cluster is None:
            return {}
        if cluster.performance.observation_count < MIN_REINFORCEMENT_OBSERVATIONS:
            return {}

        sim = cluster.centroid_similarity(state)
        perf = cluster.performance
        quality_delta = perf.quality_ema - 0.5

        bias: dict[str, float] = {}
        for s_name in perf.strategy_scores:
            raw = quality_delta * MAX_LEARNED_STATE_BIAS * sim
            clamped = max(-MAX_LEARNED_STATE_BIAS, min(MAX_LEARNED_STATE_BIAS, raw))
            bias[s_name] = round(clamped, 4)
        return bias

    def get_all_clusters(self) -> list[StateCluster]:
        return list(self._clusters.values())

    def get_cluster(self, cluster_id: str) -> StateCluster | None:
        return self._clusters.get(cluster_id)

    def _find_best_cluster(self, state: WorldState) -> StateCluster | None:
        """Find the nearest cluster (no threshold gate — for recording)."""
        if not self._clusters:
            return None
        best_cluster = None
        best_sim = -1.0
        for cluster in self._clusters.values():
            sim = cluster.centroid_similarity(state)
            if sim > best_sim:
                best_sim = sim
                best_cluster = cluster
        return best_cluster

    # ─── Internal clustering ─────────────────────────────────────

    def _assign_to_cluster(self, state: WorldState) -> None:
        """Assign a state to the nearest cluster, or create a new one."""
        best_cluster = None
        best_sim = -1.0

        for cluster in self._clusters.values():
            sim = cluster.centroid_similarity(state)
            if sim > best_sim:
                best_sim = sim
                best_cluster = cluster

        if best_cluster is not None and best_sim >= CLUSTER_SIMILARITY_THRESHOLD:
            best_cluster.add_state(state)
            return

        if len(self._clusters) >= MAX_CLUSTERS:
            self._merge_smallest_clusters()

        cluster_id = f"cluster_{len(self._clusters)}_{state.state_id[:8]}"
        new_cluster = StateCluster(cluster_id=cluster_id)
        new_cluster.add_state(state)
        self._clusters[cluster_id] = new_cluster

    def _merge_smallest_clusters(self) -> None:
        """Merge the two smallest clusters to make room."""
        if len(self._clusters) < 2:
            return

        sorted_clusters = sorted(
            self._clusters.items(),
            key=lambda x: (x[1].size, x[0]),
        )

        smallest_id = sorted_clusters[0][0]
        second_id = sorted_clusters[1][0]

        survivor = self._clusters[second_id]
        victim = self._clusters[smallest_id]

        for sid in victim.member_state_ids:
            if sid not in survivor.member_state_ids:
                survivor.member_state_ids.append(sid)
        survivor.size = len(survivor.member_state_ids)

        vp = victim.performance
        sp = survivor.performance
        for k, v in vp.strategy_scores.items():
            if k in sp.strategy_scores:
                sp.strategy_scores[k] = (sp.strategy_scores[k] + v) / 2
            else:
                sp.strategy_scores[k] = v
        for k, v in vp.strategy_counts.items():
            sp.strategy_counts[k] = sp.strategy_counts.get(k, 0) + v
        for k, v in vp.goal_scores.items():
            if k in sp.goal_scores:
                sp.goal_scores[k] = (sp.goal_scores[k] + v) / 2
            else:
                sp.goal_scores[k] = v
        for k, v in vp.goal_counts.items():
            sp.goal_counts[k] = sp.goal_counts.get(k, 0) + v
        sp.observation_count += vp.observation_count

        del self._clusters[smallest_id]

    # ─── Persistence ─────────────────────────────────────────────

    def snapshot(self) -> dict:
        """Serialize engine state for persistence."""
        return {
            "clusters": {cid: c.to_dict() for cid, c in self._clusters.items()},
            "state_count": len(self._state_history),
            "current_state_id": self._current_state.state_id
            if self._current_state
            else None,
        }

    def restore(self, data: dict) -> None:
        """Restore clusters from persisted snapshot."""
        for cid, cdict in data.get("clusters", {}).items():
            cluster = StateCluster(
                cluster_id=cdict["cluster_id"],
                centroid_features=cdict.get("centroid_features", {}),
                member_state_ids=list(cdict.get("member_state_ids", [])),
                size=cdict.get("size", 0),
            )
            pdict = cdict.get("performance", {})
            cluster.performance = ClusterPerformance(
                strategy_scores=pdict.get("strategy_scores", {}),
                strategy_counts=pdict.get("strategy_counts", {}),
                goal_scores=pdict.get("goal_scores", {}),
                goal_counts=pdict.get("goal_counts", {}),
                avg_utility=pdict.get("avg_utility", 0.5),
                observation_count=pdict.get("observation_count", 0),
                quality_ema=pdict.get("quality_ema", 0.5),
                last_used_turn=pdict.get("last_used_turn", 0),
            )
            self._clusters[cid] = cluster


# ─── Singleton ──────────────────────────────────────────────────────────────

_engine: WorldStateEngine | None = None


def get_world_state_engine() -> WorldStateEngine:
    """Get the singleton WorldStateEngine instance."""
    global _engine
    if _engine is None:
        _engine = WorldStateEngine()
    return _engine


def reset_world_state_engine() -> None:
    """Reset the singleton for testing."""
    global _engine
    _engine = WorldStateEngine()
