"""WorldSimulation — bounded deterministic forward model for EOS.

Takes a WorldSnapshot + WorldUnderstanding + candidate action and produces
a simulated future WorldSnapshot + WorldUnderstanding + transition diagnostics.

All logic is deterministic, bounded, and domain-agnostic.
No LLM calls. No embeddings. No randomness. No external dependencies.
SimulationResult is NOT persisted — it is a derived forward view,
recomputed each turn from current world state.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from umh.world.types import (
    Entity,
    Observation,
    PrimitiveValue,
    Relation,
    StateFact,
    WorldSnapshot,
)
from umh.world.reasoning import (
    EntityAssessment,
    EntityTrend,
    WorldReasoningEngine,
    WorldUnderstanding,
    get_entity_assessment,
    get_riskiest_entities,
)
from umh.world.dynamics_adapter import DynamicsAdjustment, NEUTRAL_ADJUSTMENT

# ─── Constants ───────────────────────────────────────────────────

MAX_HORIZON = 10
MAX_CANDIDATE_ACTIONS = 10

BOOST_DEFAULT_MAGNITUDE = 0.1
SUPPRESS_DEFAULT_MAGNITUDE = 0.1
STABILIZE_REDUCTION = 0.05

TREND_CARRY_FORWARD = 0.02
STABILITY_DECAY = 0.02
RISK_PROPAGATION_PENALTY = 0.03

# ─── Data models ─────────────────────────────────────────────────


@dataclass(frozen=True)
class SimulatedAction:
    """Abstract simulation action."""

    action_id: str
    action_type: str
    target_entity: str | None = None
    parameters: dict[str, PrimitiveValue] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "action_id": self.action_id,
            "action_type": self.action_type,
            "target_entity": self.target_entity,
            "parameters": dict(self.parameters),
        }


@dataclass(frozen=True)
class StateDelta:
    """One atomic change in a simulation step."""

    entity_id: str
    key: str
    before: PrimitiveValue
    after: PrimitiveValue
    delta_type: str
    reason: str

    def to_dict(self) -> dict:
        return {
            "entity_id": self.entity_id,
            "key": self.key,
            "before": self.before,
            "after": self.after,
            "delta_type": self.delta_type,
            "reason": self.reason,
        }


@dataclass(frozen=True)
class SimulationStep:
    """One step of forward simulation."""

    step_index: int
    action_id: str
    deltas: tuple[StateDelta, ...]
    global_flags: tuple[str, ...]
    note: str

    def to_dict(self) -> dict:
        return {
            "step_index": self.step_index,
            "action_id": self.action_id,
            "deltas": [d.to_dict() for d in self.deltas],
            "global_flags": list(self.global_flags),
            "note": self.note,
        }


@dataclass(frozen=True)
class SimulationResult:
    """Complete result of simulating one action over a horizon."""

    action_id: str
    horizon: int
    final_snapshot_version: int
    final_world_snapshot: WorldSnapshot
    final_world_understanding: WorldUnderstanding
    steps: tuple[SimulationStep, ...]
    aggregate_risk: float
    aggregate_improvement: float
    confidence: float

    def to_dict(self) -> dict:
        return {
            "action_id": self.action_id,
            "horizon": self.horizon,
            "final_snapshot_version": self.final_snapshot_version,
            "steps": [s.to_dict() for s in self.steps],
            "aggregate_risk": round(self.aggregate_risk, 4),
            "aggregate_improvement": round(self.aggregate_improvement, 4),
            "confidence": round(self.confidence, 4),
        }


# ─── Snapshot manipulation helpers ───────────────────────────────


def _find_fact_in(
    facts: tuple[StateFact, ...], entity_id: str, key: str
) -> StateFact | None:
    for f in facts:
        if f.entity_id == entity_id and f.key == key:
            return f
    return None


def _find_fact(snapshot: WorldSnapshot, entity_id: str, key: str) -> StateFact | None:
    return _find_fact_in(snapshot.state_facts, entity_id, key)


def _numeric_facts_from(
    facts: tuple[StateFact, ...], entity_id: str
) -> list[StateFact]:
    return [
        f
        for f in facts
        if f.entity_id == entity_id
        and isinstance(f.value, (int, float))
        and not isinstance(f.value, bool)
    ]


def _entity_numeric_facts(snapshot: WorldSnapshot, entity_id: str) -> list[StateFact]:
    return _numeric_facts_from(snapshot.state_facts, entity_id)


def _replace_fact(
    facts: tuple[StateFact, ...], old: StateFact, new: StateFact
) -> tuple[StateFact, ...]:
    return tuple(new if f is old else f for f in facts)


def _add_fact(facts: tuple[StateFact, ...], new: StateFact) -> tuple[StateFact, ...]:
    return facts + (new,)


def _rebuild_snapshot(
    base: WorldSnapshot,
    entities: tuple[Entity, ...] | None = None,
    relations: tuple[Relation, ...] | None = None,
    state_facts: tuple[StateFact, ...] | None = None,
    version_bump: int = 1,
) -> WorldSnapshot:
    return WorldSnapshot(
        entities=entities if entities is not None else base.entities,
        relations=relations if relations is not None else base.relations,
        state_facts=state_facts if state_facts is not None else base.state_facts,
        observation_count=base.observation_count,
        version=base.version + version_bump,
    )


# ─── Action effect application ───────────────────────────────────


def _apply_boost(
    snapshot: WorldSnapshot,
    action: SimulatedAction,
) -> tuple[WorldSnapshot, list[StateDelta]]:
    if action.target_entity is None:
        return snapshot, []

    magnitude = action.parameters.get("magnitude", BOOST_DEFAULT_MAGNITUDE)
    if not isinstance(magnitude, (int, float)):
        magnitude = BOOST_DEFAULT_MAGNITUDE
    magnitude = float(magnitude)

    facts = snapshot.state_facts
    deltas: list[StateDelta] = []

    for fact in _entity_numeric_facts(snapshot, action.target_entity):
        old_val = float(fact.value)
        new_val = round(old_val + abs(magnitude), 8)
        new_fact = StateFact(
            entity_id=fact.entity_id,
            key=fact.key,
            value=new_val,
            confidence=fact.confidence,
            last_updated_turn=fact.last_updated_turn,
            update_count=fact.update_count,
        )
        facts = _replace_fact(facts, fact, new_fact)
        deltas.append(
            StateDelta(
                entity_id=fact.entity_id,
                key=fact.key,
                before=old_val,
                after=new_val,
                delta_type="numeric_shift",
                reason=f"boost +{abs(magnitude):.4f}",
            )
        )

    if not deltas:
        deltas.append(
            StateDelta(
                entity_id=action.target_entity,
                key="",
                before=None,
                after=None,
                delta_type="no_op",
                reason="no numeric facts to boost",
            )
        )

    return _rebuild_snapshot(snapshot, state_facts=facts), deltas


def _apply_suppress(
    snapshot: WorldSnapshot,
    action: SimulatedAction,
) -> tuple[WorldSnapshot, list[StateDelta]]:
    if action.target_entity is None:
        return snapshot, []

    magnitude = action.parameters.get("magnitude", SUPPRESS_DEFAULT_MAGNITUDE)
    if not isinstance(magnitude, (int, float)):
        magnitude = SUPPRESS_DEFAULT_MAGNITUDE
    magnitude = float(magnitude)

    facts = snapshot.state_facts
    deltas: list[StateDelta] = []

    for fact in _entity_numeric_facts(snapshot, action.target_entity):
        old_val = float(fact.value)
        new_val = round(old_val - abs(magnitude), 8)
        new_fact = StateFact(
            entity_id=fact.entity_id,
            key=fact.key,
            value=new_val,
            confidence=fact.confidence,
            last_updated_turn=fact.last_updated_turn,
            update_count=fact.update_count,
        )
        facts = _replace_fact(facts, fact, new_fact)
        deltas.append(
            StateDelta(
                entity_id=fact.entity_id,
                key=fact.key,
                before=old_val,
                after=new_val,
                delta_type="numeric_shift",
                reason=f"suppress -{abs(magnitude):.4f}",
            )
        )

    if not deltas:
        deltas.append(
            StateDelta(
                entity_id=action.target_entity,
                key="",
                before=None,
                after=None,
                delta_type="no_op",
                reason="no numeric facts to suppress",
            )
        )

    return _rebuild_snapshot(snapshot, state_facts=facts), deltas


def _apply_stabilize(
    snapshot: WorldSnapshot,
    action: SimulatedAction,
) -> tuple[WorldSnapshot, list[StateDelta]]:
    if action.target_entity is None:
        return snapshot, []

    facts = snapshot.state_facts
    deltas: list[StateDelta] = []
    risk_keywords = frozenset(
        {
            "risk",
            "error",
            "failed",
            "failure",
            "warning",
            "critical",
            "degraded",
            "alert",
        }
    )

    for fact in snapshot.state_facts:
        if fact.entity_id != action.target_entity:
            continue
        if not isinstance(fact.value, (int, float)) or isinstance(fact.value, bool):
            continue
        has_risk_key = any(kw in fact.key.lower() for kw in risk_keywords)
        if not has_risk_key:
            continue
        old_val = float(fact.value)
        new_val = round(old_val - STABILIZE_REDUCTION, 8)
        new_fact = StateFact(
            entity_id=fact.entity_id,
            key=fact.key,
            value=new_val,
            confidence=fact.confidence,
            last_updated_turn=fact.last_updated_turn,
            update_count=fact.update_count,
        )
        facts = _replace_fact(facts, fact, new_fact)
        deltas.append(
            StateDelta(
                entity_id=fact.entity_id,
                key=fact.key,
                before=old_val,
                after=new_val,
                delta_type="numeric_shift",
                reason=f"stabilize -{STABILIZE_REDUCTION:.4f} on risk key",
            )
        )

    if not deltas:
        deltas.append(
            StateDelta(
                entity_id=action.target_entity,
                key="",
                before=None,
                after=None,
                delta_type="no_op",
                reason="no risk/volatility keys to stabilize",
            )
        )

    return _rebuild_snapshot(snapshot, state_facts=facts), deltas


def _apply_link(
    snapshot: WorldSnapshot,
    action: SimulatedAction,
) -> tuple[WorldSnapshot, list[StateDelta]]:
    if action.target_entity is None:
        return snapshot, []

    other = action.parameters.get("other_entity")
    if not other or not isinstance(other, str):
        return snapshot, [
            StateDelta(
                entity_id=action.target_entity,
                key="",
                before=None,
                after=None,
                delta_type="no_op",
                reason="missing other_entity parameter",
            )
        ]

    rel_type = action.parameters.get("relation_type", "related_to")
    if not isinstance(rel_type, str):
        rel_type = "related_to"

    for r in snapshot.relations:
        if (
            r.source_id == action.target_entity
            and r.target_id == other
            and r.relation_type == rel_type
        ):
            return snapshot, [
                StateDelta(
                    entity_id=action.target_entity,
                    key="",
                    before=None,
                    after=None,
                    delta_type="no_op",
                    reason=f"relation {rel_type} to {other} already exists",
                )
            ]

    new_rel = Relation(
        source_id=action.target_entity,
        relation_type=rel_type,
        target_id=other,
        weight=1.0,
    )
    new_relations = snapshot.relations + (new_rel,)
    delta = StateDelta(
        entity_id=action.target_entity,
        key=rel_type,
        before=None,
        after=other,
        delta_type="relation_added",
        reason=f"linked {action.target_entity} -> {other} via {rel_type}",
    )
    return _rebuild_snapshot(snapshot, relations=new_relations), [delta]


def _apply_unlink(
    snapshot: WorldSnapshot,
    action: SimulatedAction,
) -> tuple[WorldSnapshot, list[StateDelta]]:
    if action.target_entity is None:
        return snapshot, []

    other = action.parameters.get("other_entity")
    if not other or not isinstance(other, str):
        return snapshot, [
            StateDelta(
                entity_id=action.target_entity,
                key="",
                before=None,
                after=None,
                delta_type="no_op",
                reason="missing other_entity parameter",
            )
        ]

    rel_type = action.parameters.get("relation_type", "related_to")
    if not isinstance(rel_type, str):
        rel_type = "related_to"

    remaining: list[Relation] = []
    removed = False
    for r in snapshot.relations:
        if (
            r.source_id == action.target_entity
            and r.target_id == other
            and r.relation_type == rel_type
        ):
            removed = True
        else:
            remaining.append(r)

    if not removed:
        return snapshot, [
            StateDelta(
                entity_id=action.target_entity,
                key="",
                before=None,
                after=None,
                delta_type="no_op",
                reason=f"no relation {rel_type} to {other} found",
            )
        ]

    delta = StateDelta(
        entity_id=action.target_entity,
        key=rel_type,
        before=other,
        after=None,
        delta_type="relation_removed",
        reason=f"unlinked {action.target_entity} -> {other} via {rel_type}",
    )
    return _rebuild_snapshot(snapshot, relations=tuple(remaining)), [delta]


_ACTION_HANDLERS = {
    "boost": _apply_boost,
    "suppress": _apply_suppress,
    "stabilize": _apply_stabilize,
    "link": _apply_link,
    "unlink": _apply_unlink,
}


def apply_action_to_snapshot(
    snapshot: WorldSnapshot,
    action: SimulatedAction,
) -> tuple[WorldSnapshot, list[StateDelta]]:
    """Apply a single action's effects to a snapshot copy."""
    handler = _ACTION_HANDLERS.get(action.action_type)
    if handler is None:
        return snapshot, [
            StateDelta(
                entity_id=action.target_entity or "",
                key="",
                before=None,
                after=None,
                delta_type="no_op",
                reason=f"unknown action type: {action.action_type}",
            )
        ]
    return handler(snapshot, action)


# ─── World dynamics model ────────────────────────────────────────


def step_world_dynamics(
    snapshot: WorldSnapshot,
    understanding: WorldUnderstanding,
    adjustment: DynamicsAdjustment | None = None,
) -> tuple[WorldSnapshot, list[StateDelta]]:
    """Advance the world one step using deterministic dynamics.

    1. Trend carry-forward for up/down entities
    2. Single-hop risk propagation penalty
    3. Stability decay for unstable/volatile entities

    When adjustment is provided, multipliers/modifiers scale the base rates.
    """
    adj = adjustment or NEUTRAL_ADJUSTMENT
    facts = snapshot.state_facts
    deltas: list[StateDelta] = []

    assessment_map: dict[str, EntityAssessment] = {
        a.entity_id: a for a in understanding.entity_assessments
    }

    for entity in snapshot.entities:
        assessment = assessment_map.get(entity.entity_id)
        if assessment is None:
            continue

        # 1. Trend carry-forward (scaled by trend_multiplier)
        for trend in assessment.trend_summary:
            if trend.direction == "volatile" or trend.direction == "unknown":
                continue

            fact = _find_fact_in(facts, entity.entity_id, trend.key)
            if (
                fact is None
                or not isinstance(fact.value, (int, float))
                or isinstance(fact.value, bool)
            ):
                continue

            if trend.direction == "up":
                delta_val = TREND_CARRY_FORWARD * adj.trend_multiplier
            elif trend.direction == "down":
                delta_val = -TREND_CARRY_FORWARD * adj.trend_multiplier
            else:
                continue

            old_val = float(fact.value)
            new_val = round(old_val + delta_val, 8)
            new_fact = StateFact(
                entity_id=fact.entity_id,
                key=fact.key,
                value=new_val,
                confidence=fact.confidence,
                last_updated_turn=fact.last_updated_turn,
                update_count=fact.update_count,
            )
            facts = _replace_fact(facts, fact, new_fact)
            deltas.append(
                StateDelta(
                    entity_id=entity.entity_id,
                    key=trend.key,
                    before=old_val,
                    after=new_val,
                    delta_type="trend_carry",
                    reason=f"trend {trend.direction} carry-forward {delta_val:+.4f}",
                )
            )

        # 2. Single-hop risk propagation (scaled by risk_multiplier)
        if assessment.health in ("bad", "watch"):
            for rel in snapshot.relations:
                if rel.source_id != entity.entity_id:
                    continue
                for target_fact in _numeric_facts_from(facts, rel.target_id):
                    old_val = float(target_fact.value)
                    penalty = (
                        RISK_PROPAGATION_PENALTY * rel.weight * adj.risk_multiplier
                    )
                    new_val = round(old_val - penalty, 8)
                    new_fact = StateFact(
                        entity_id=target_fact.entity_id,
                        key=target_fact.key,
                        value=new_val,
                        confidence=target_fact.confidence,
                        last_updated_turn=target_fact.last_updated_turn,
                        update_count=target_fact.update_count,
                    )
                    facts = _replace_fact(facts, target_fact, new_fact)
                    deltas.append(
                        StateDelta(
                            entity_id=rel.target_id,
                            key=target_fact.key,
                            before=old_val,
                            after=new_val,
                            delta_type="risk_propagation",
                            reason=f"risk from {entity.entity_id} via {rel.relation_type} ({penalty:.4f})",
                        )
                    )

        # 3. Stability decay (offset by stability_decay_modifier)
        if assessment.stability in ("volatile", "unstable"):
            effective_decay = STABILITY_DECAY + adj.stability_decay_modifier
            for nf in _numeric_facts_from(facts, entity.entity_id):
                old_val = float(nf.value)
                new_val = round(old_val - effective_decay, 8)
                new_fact = StateFact(
                    entity_id=nf.entity_id,
                    key=nf.key,
                    value=new_val,
                    confidence=nf.confidence,
                    last_updated_turn=nf.last_updated_turn,
                    update_count=nf.update_count,
                )
                facts = _replace_fact(facts, nf, new_fact)
                deltas.append(
                    StateDelta(
                        entity_id=entity.entity_id,
                        key=nf.key,
                        before=old_val,
                        after=new_val,
                        delta_type="stability_decay",
                        reason=f"stability decay ({assessment.stability})",
                    )
                )

    return _rebuild_snapshot(snapshot, state_facts=facts, version_bump=0), deltas


# ─── Understanding recomputation ─────────────────────────────────


def recompute_understanding(
    snapshot: WorldSnapshot,
    observation_history: tuple[Observation, ...] | None = None,
) -> WorldUnderstanding:
    """Recompute WorldUnderstanding from a (possibly simulated) snapshot."""
    engine = WorldReasoningEngine()
    return engine.derive_understanding(snapshot, observation_history)


# ─── Aggregate metrics ───────────────────────────────────────────


def _compute_aggregate_improvement(
    initial: WorldUnderstanding,
    final: WorldUnderstanding,
) -> float:
    """Score how much the world improved from initial to final.

    Components:
    - entities moved from bad -> watch/good
    - entities moved from watch -> good
    - decrease in volatile/unstable counts
    - decrease in global risk flags
    """
    score = 0.0

    initial_health: dict[str, str] = {
        a.entity_id: a.health for a in initial.entity_assessments
    }
    final_health: dict[str, str] = {
        a.entity_id: a.health for a in final.entity_assessments
    }

    health_rank = {"bad": 0, "watch": 1, "good": 2}
    for eid, final_h in final_health.items():
        initial_h = initial_health.get(eid, "watch")
        if health_rank.get(final_h, 1) > health_rank.get(initial_h, 1):
            score += 0.2

    initial_volatile = sum(
        1 for a in initial.entity_assessments if a.stability in ("volatile", "unstable")
    )
    final_volatile = sum(
        1 for a in final.entity_assessments if a.stability in ("volatile", "unstable")
    )
    if initial_volatile > final_volatile:
        score += 0.1 * (initial_volatile - final_volatile)

    initial_flags = set(initial.global_flags)
    final_flags = set(final.global_flags)
    removed_flags = initial_flags - final_flags
    score += 0.1 * len(removed_flags)

    return max(0.0, min(1.0, score))


def _compute_aggregate_risk(
    initial: WorldUnderstanding,
    final: WorldUnderstanding,
) -> float:
    """Score how much worse the world got from initial to final.

    Components:
    - increase in bad entities
    - increase in propagated relation risk
    - increase in volatile/unstable counts
    - new global flags
    """
    score = 0.0

    initial_bad = sum(1 for a in initial.entity_assessments if a.health == "bad")
    final_bad = sum(1 for a in final.entity_assessments if a.health == "bad")
    if final_bad > initial_bad:
        score += 0.15 * (final_bad - initial_bad)

    initial_impacts = len(initial.relation_impacts)
    final_impacts = len(final.relation_impacts)
    if final_impacts > initial_impacts:
        score += 0.05 * (final_impacts - initial_impacts)

    initial_volatile = sum(
        1 for a in initial.entity_assessments if a.stability in ("volatile", "unstable")
    )
    final_volatile = sum(
        1 for a in final.entity_assessments if a.stability in ("volatile", "unstable")
    )
    if final_volatile > initial_volatile:
        score += 0.1 * (final_volatile - initial_volatile)

    initial_flags = set(initial.global_flags)
    final_flags = set(final.global_flags)
    new_flags = final_flags - initial_flags
    score += 0.15 * len(new_flags)

    return max(0.0, min(1.0, score))


def _compute_simulation_confidence(
    understanding: WorldUnderstanding,
    observation_count: int,
    confidence_scale: float = 1.0,
) -> float:
    """Confidence in the simulation based on data quality.

    Derived from:
    - observation history availability
    - determinism of trend classifications
    - proportion of unknown entities/trends

    confidence_scale from DynamicsAdjustment scales the final value.
    """
    if not understanding.entity_assessments:
        return 0.1

    total = len(understanding.entity_assessments)

    unknown_health = sum(
        1
        for a in understanding.entity_assessments
        if a.health == "watch" and not a.trend_summary
    )
    data_factor = min(1.0, observation_count / 20.0)

    trend_total = 0
    unknown_trends = 0
    for a in understanding.entity_assessments:
        for t in a.trend_summary:
            trend_total += 1
            if t.direction == "unknown":
                unknown_trends += 1

    trend_factor = 1.0
    if trend_total > 0:
        trend_factor = 1.0 - (unknown_trends / trend_total) * 0.5

    avg_confidence = sum(a.confidence for a in understanding.entity_assessments) / total

    result = data_factor * 0.3 + trend_factor * 0.3 + avg_confidence * 0.4
    result *= confidence_scale
    return max(0.0, min(1.0, result))


# ─── Candidate action derivation ─────────────────────────────────

MAX_DERIVED_ACTIONS = 3


def derive_simulation_actions(
    snapshot: WorldSnapshot,
    understanding: WorldUnderstanding,
) -> tuple[SimulatedAction, ...]:
    """Derive candidate simulation actions from current world state.

    Generic rules:
    - bad entities with numeric facts -> "boost"
    - volatile/unstable entities -> "stabilize"
    - entities with risk flags from relations -> "suppress"

    Capped to MAX_DERIVED_ACTIONS.
    """
    actions: list[SimulatedAction] = []

    for assessment in understanding.entity_assessments:
        if len(actions) >= MAX_DERIVED_ACTIONS:
            break

        if assessment.health == "bad":
            has_numeric = any(
                isinstance(f.value, (int, float)) and not isinstance(f.value, bool)
                for f in snapshot.state_facts
                if f.entity_id == assessment.entity_id
            )
            if has_numeric:
                actions.append(
                    SimulatedAction(
                        action_id=f"sim_boost_{assessment.entity_id}",
                        action_type="boost",
                        target_entity=assessment.entity_id,
                        parameters={"magnitude": BOOST_DEFAULT_MAGNITUDE},
                    )
                )
                continue

        if assessment.stability in ("volatile", "unstable"):
            actions.append(
                SimulatedAction(
                    action_id=f"sim_stabilize_{assessment.entity_id}",
                    action_type="stabilize",
                    target_entity=assessment.entity_id,
                    parameters={},
                )
            )
            if len(actions) >= MAX_DERIVED_ACTIONS:
                break
            continue

        if assessment.risk_flags:
            has_numeric = any(
                isinstance(f.value, (int, float)) and not isinstance(f.value, bool)
                for f in snapshot.state_facts
                if f.entity_id == assessment.entity_id
            )
            if has_numeric:
                actions.append(
                    SimulatedAction(
                        action_id=f"sim_suppress_{assessment.entity_id}",
                        action_type="suppress",
                        target_entity=assessment.entity_id,
                        parameters={"magnitude": SUPPRESS_DEFAULT_MAGNITUDE},
                    )
                )
                if len(actions) >= MAX_DERIVED_ACTIONS:
                    break

    return tuple(actions)


# ─── World Simulation Engine ─────────────────────────────────────


class WorldSimulationEngine:
    """Bounded deterministic forward model.

    Takes snapshot + understanding + candidate action → simulated future.
    Stateless. Operates on copies only. Never mutates real world state.
    """

    def simulate_action(
        self,
        snapshot: WorldSnapshot,
        understanding: WorldUnderstanding,
        action: SimulatedAction,
        horizon: int = 3,
        observation_history: tuple[Observation, ...] | None = None,
        adjustment: DynamicsAdjustment | None = None,
    ) -> SimulationResult:
        """Simulate one action forward over horizon steps."""
        horizon = max(1, min(horizon, MAX_HORIZON))
        adj = adjustment or NEUTRAL_ADJUSTMENT
        current_snapshot = snapshot
        current_understanding = understanding
        steps: list[SimulationStep] = []

        for step_idx in range(horizon):
            all_deltas: list[StateDelta] = []

            # Apply action effects (only on step 0)
            if step_idx == 0:
                current_snapshot, action_deltas = apply_action_to_snapshot(
                    current_snapshot, action
                )
                all_deltas.extend(action_deltas)

            # Apply world dynamics (with calibration-derived adjustments)
            current_snapshot, dynamics_deltas = step_world_dynamics(
                current_snapshot, current_understanding, adjustment=adj
            )
            all_deltas.extend(dynamics_deltas)

            # Recompute understanding
            current_understanding = recompute_understanding(
                current_snapshot, observation_history
            )

            steps.append(
                SimulationStep(
                    step_index=step_idx,
                    action_id=action.action_id,
                    deltas=tuple(all_deltas),
                    global_flags=current_understanding.global_flags,
                    note=f"step {step_idx}: {len(all_deltas)} deltas",
                )
            )

        improvement = _compute_aggregate_improvement(
            understanding, current_understanding
        )
        risk = _compute_aggregate_risk(understanding, current_understanding)
        confidence = _compute_simulation_confidence(
            current_understanding,
            snapshot.observation_count,
            confidence_scale=adj.confidence_scale,
        )

        return SimulationResult(
            action_id=action.action_id,
            horizon=horizon,
            final_snapshot_version=current_snapshot.version,
            final_world_snapshot=current_snapshot,
            final_world_understanding=current_understanding,
            steps=tuple(steps),
            aggregate_risk=risk,
            aggregate_improvement=improvement,
            confidence=confidence,
        )

    def simulate_actions(
        self,
        snapshot: WorldSnapshot,
        understanding: WorldUnderstanding,
        actions: tuple[SimulatedAction, ...],
        horizon: int = 3,
        observation_history: tuple[Observation, ...] | None = None,
        adjustment: DynamicsAdjustment | None = None,
    ) -> tuple[SimulationResult, ...]:
        """Simulate multiple actions independently."""
        capped = actions[:MAX_CANDIDATE_ACTIONS]
        return tuple(
            self.simulate_action(
                snapshot,
                understanding,
                action,
                horizon,
                observation_history,
                adjustment=adjustment,
            )
            for action in capped
        )
