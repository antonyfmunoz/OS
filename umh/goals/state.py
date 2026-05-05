"""
GoalState — explicit session-level objective for goal-conditioned intelligence.

Defines what the session is trying to achieve. All downstream layers
(control, strategy, prompt, memory) read GoalState to condition their
behavior toward the declared objective.

Multi-goal support via GoalRegistry + GoalTracker:
    - GoalState is immutable (frozen dataclass) — defines the goal.
    - GoalTracker is mutable — tracks per-goal runtime signals
      (success_score EMA, recency_weight, delta history).
    - GoalRegistry manages the goal pool and exposes the active goal.

No LLM calls. No randomness. Pure data structure + deterministic scoring.

Usage::

    from umh.goals.state import GoalState, GoalRegistry, compute_goal_relevance

    registry = GoalRegistry()
    registry.add_goal(GoalState(
        goal_id="close_sale",
        description="Close the coaching sale",
        success_criteria={"response_type": "persuasive", "domain": "sales"},
        priority=0.9,
    ))
    registry.add_goal(GoalState(
        goal_id="analyze",
        description="Analyze architecture",
        success_criteria={"response_type": "analytical"},
        priority=0.7,
    ))

    active = registry.get_active_goal()  # highest utility or manually set
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

GOAL_WEIGHT_SCALE = 0.5
RELEVANCE_FLOOR = 0.1

RECENCY_DECAY_RATE = 0.05
TRACKER_EMA_ALPHA = 0.3


@dataclass(frozen=True)
class GoalState:
    """Immutable session-level objective."""

    goal_id: str
    description: str
    success_criteria: dict = field(default_factory=dict)
    priority: float = 0.5
    active: bool = True

    def to_dict(self) -> dict:
        return {
            "goal_id": self.goal_id,
            "description": self.description,
            "success_criteria": self.success_criteria,
            "priority": self.priority,
            "active": self.active,
        }


NO_GOAL = GoalState(
    goal_id="none",
    description="",
    success_criteria={},
    priority=0.0,
    active=False,
)


# ─── Per-goal runtime tracking ────────────────────────────────────────────────


PERSISTENCE_DECAY = 0.8


@dataclass
class GoalTracker:
    """Mutable per-goal runtime signals for arbitration."""

    goal_id: str
    success_score: float = 0.5
    recency_weight: float = 1.0
    last_active_turn: int = 0
    delta_history: list[float] = field(default_factory=list)
    uses: int = 0
    persistence_streak: float = 0.0

    def update_persistence(self, is_active: bool) -> None:
        """Update persistence_streak: increment if active, decay otherwise."""
        if is_active:
            self.persistence_streak += 1.0
        else:
            self.persistence_streak *= PERSISTENCE_DECAY

    def update_success(self, goal_score: float) -> None:
        """Update success_score via EMA."""
        if self.uses == 0:
            self.success_score = goal_score
        else:
            self.success_score = (
                TRACKER_EMA_ALPHA * goal_score + (1 - TRACKER_EMA_ALPHA) * self.success_score
            )
        self.uses += 1

    def record_delta(self, delta: float) -> None:
        """Append a delta to the history (capped at 20 entries)."""
        self.delta_history.append(delta)
        if len(self.delta_history) > 20:
            self.delta_history = self.delta_history[-20:]

    def compute_recency(self, current_turn: int) -> float:
        """Compute decayed recency weight based on staleness."""
        staleness = max(0, current_turn - self.last_active_turn)
        self.recency_weight = math.exp(-RECENCY_DECAY_RATE * staleness)
        return self.recency_weight

    def apply_outcome(
        self,
        adjusted_score: float,
        outcome_confidence: float,
    ) -> None:
        """Retroactively adjust success_score with an external outcome signal.

        Only modifies success_score EMA — does not increment uses counter.
        This is a correction to prior learning, not a new observation.
        """
        if self.uses == 0:
            return
        blend = min(outcome_confidence, TRACKER_EMA_ALPHA)
        self.success_score = (blend * adjusted_score) + ((1 - blend) * self.success_score)

    @property
    def latest_delta(self) -> float:
        """Most recent goal_delta, or 0.0 if no history."""
        return self.delta_history[-1] if self.delta_history else 0.0

    def to_dict(self) -> dict:
        return {
            "goal_id": self.goal_id,
            "success_score": round(self.success_score, 4),
            "recency_weight": round(self.recency_weight, 4),
            "last_active_turn": self.last_active_turn,
            "latest_delta": round(self.latest_delta, 4),
            "uses": self.uses,
            "persistence_streak": round(self.persistence_streak, 4),
        }


# ─── Goal Registry ────────────────────────────────────────────────────────────


class GoalRegistry:
    """Manages the goal pool for a session.

    Stores GoalState objects and their per-goal GoalTrackers.
    Supports manual active goal override or arbitrator-driven selection.

    When ``persist=True``, tracker state is saved periodically via the
    persistence layer and restored on construction. GoalState objects
    are NOT persisted — the caller reconstructs them each session.
    Only tracker EMA/recency/delta runtime signals survive restarts.
    """

    def __init__(self, persist: bool = False) -> None:
        self._goals: dict[str, GoalState] = {}
        self._trackers: dict[str, GoalTracker] = {}
        self._active_goal_id: str | None = None
        self._turn: int = 0
        self._persist = persist
        self._update_count: int = 0

        if persist:
            self._load_persisted()

    def add_goal(self, goal: GoalState) -> None:
        """Add a goal to the pool. Replaces if goal_id already exists."""
        self._goals[goal.goal_id] = goal
        if goal.goal_id not in self._trackers:
            self._trackers[goal.goal_id] = GoalTracker(goal_id=goal.goal_id)

    def remove_goal(self, goal_id: str) -> None:
        """Remove a goal and its tracker from the pool."""
        self._goals.pop(goal_id, None)
        self._trackers.pop(goal_id, None)
        if self._active_goal_id == goal_id:
            self._active_goal_id = None

    def get_goal(self, goal_id: str) -> GoalState | None:
        """Return a specific goal by ID, or None."""
        return self._goals.get(goal_id)

    def get_tracker(self, goal_id: str) -> GoalTracker | None:
        """Return the tracker for a specific goal, or None."""
        return self._trackers.get(goal_id)

    def get_all_goals(self) -> list[GoalState]:
        """Return all goals in the pool (active ones only)."""
        return [g for g in self._goals.values() if g.active]

    def get_all_trackers(self) -> dict[str, GoalTracker]:
        """Return all trackers."""
        return dict(self._trackers)

    @property
    def active_goal_id(self) -> str | None:
        return self._active_goal_id

    def set_active_goal(self, goal_id: str | None) -> None:
        """Manually override the active goal. None = let arbitrator decide."""
        self._active_goal_id = goal_id
        if goal_id is not None and goal_id in self._trackers:
            self._trackers[goal_id].last_active_turn = self._turn

    def get_active_goal(self) -> GoalState:
        """Return the currently active goal, or NO_GOAL."""
        if self._active_goal_id is not None:
            goal = self._goals.get(self._active_goal_id)
            if goal is not None and goal.active:
                return goal
        return NO_GOAL

    def advance_turn(self) -> None:
        """Increment the internal turn counter."""
        self._turn += 1

    @property
    def turn(self) -> int:
        return self._turn

    @property
    def size(self) -> int:
        return len(self._goals)

    def is_empty(self) -> bool:
        return len(self._goals) == 0

    def snapshot(self) -> dict:
        """Summarized snapshot of the goal pool for trace observability."""
        goals_summary: list[dict] = []
        for gid, goal in self._goals.items():
            tracker = self._trackers.get(gid)
            entry: dict = {
                "goal_id": gid,
                "priority": goal.priority,
                "active": goal.active,
            }
            if tracker is not None:
                entry["success_score"] = round(tracker.success_score, 4)
                entry["recency_weight"] = round(tracker.recency_weight, 4)
                entry["latest_delta"] = round(tracker.latest_delta, 4)
                entry["persistence_streak"] = round(tracker.persistence_streak, 4)
            goals_summary.append(entry)
        return {
            "goals": goals_summary,
            "active_goal_id": self._active_goal_id,
            "turn": self._turn,
        }

    def to_dict(self) -> dict:
        return self.snapshot()

    def persist_trackers(self) -> None:
        """Explicitly persist tracker state. Called by SessionRuntime after updates."""
        self._maybe_persist()

    def _maybe_persist(self) -> None:
        """Save tracker state to persistent storage if enabled."""
        if not self._persist:
            return
        self._update_count += 1
        try:
            from umh.goals.interfaces import get_goal_persistence

            backend = get_goal_persistence()
            tracker_data = {gid: t.to_dict() for gid, t in self._trackers.items()}
            backend.save_goal_trackers(tracker_data, registry_turn=self._turn)
        except Exception:
            pass

    def _load_persisted(self) -> None:
        """Restore tracker state from persistent storage on cold start.

        Only hydrates trackers for goal_ids that already exist in the
        registry, or creates new trackers for persisted IDs that the
        caller will match when re-adding goals.
        """
        try:
            from umh.goals.interfaces import get_goal_persistence

            backend = get_goal_persistence()
            data = backend.load_goal_trackers()
            if data is None:
                return

            self._turn = data.get("registry_turn", 0)
            trackers = data.get("trackers", {})
            for gid, tdict in trackers.items():
                tracker = GoalTracker(
                    goal_id=gid,
                    success_score=tdict.get("success_score", 0.5),
                    recency_weight=tdict.get("recency_weight", 1.0),
                    last_active_turn=tdict.get("last_active_turn", 0),
                    uses=tdict.get("uses", 0),
                    persistence_streak=tdict.get("persistence_streak", 0.0),
                )
                self._trackers[gid] = tracker
        except Exception:
            pass


NO_REGISTRY = GoalRegistry()


def compute_goal_relevance(
    goal: GoalState,
    context: dict,
) -> float:
    """Score how relevant a context dict is to the goal's success criteria.

    Returns a float in [0.0, 1.0]. Higher means more aligned.

    Matching logic (deterministic):
        - Each success_criteria key that exists in context and matches
          its expected value contributes equally to the score.
        - Partial matches (key present, value different) contribute half.
        - Missing keys contribute nothing.

    When the goal is inactive or has no criteria, returns RELEVANCE_FLOOR.
    """
    if not goal.active or not goal.success_criteria:
        return RELEVANCE_FLOOR

    criteria = goal.success_criteria
    total = len(criteria)
    if total == 0:
        return RELEVANCE_FLOOR

    score = 0.0
    for key, expected in criteria.items():
        actual = context.get(key)
        if actual is None:
            continue
        if actual == expected:
            score += 1.0
        else:
            score += 0.5

    raw = score / total
    return max(raw, RELEVANCE_FLOOR)


def compute_goal_weight(goal: GoalState) -> float:
    """Compute the influence weight a goal should have on system behavior.

    Returns a float in [0.0, 1.0].
    Inactive goals return 0.0.
    Active goals scale linearly with priority.
    """
    if not goal.active:
        return 0.0
    return min(goal.priority * GOAL_WEIGHT_SCALE * 2, 1.0)


def generate_goal_directives(goal: GoalState) -> tuple[str, ...]:
    """Generate prompt directives from goal state.

    Returns an empty tuple for inactive goals.
    Active goals produce 1-2 directives based on description and criteria.
    """
    if not goal.active or not goal.description:
        return ()

    directives: list[str] = []

    directives.append(
        f"Current objective: {goal.description}. Optimize responses toward this goal."
    )

    criteria_hints = []
    for key, value in goal.success_criteria.items():
        criteria_hints.append(f"{key}={value}")

    if criteria_hints:
        directives.append(
            f"Success criteria: {', '.join(criteria_hints)}. Align output accordingly."
        )

    return tuple(directives)


def compute_control_threshold_adjustment(goal: GoalState) -> dict[str, float]:
    """Compute threshold multipliers for the control layer based on goal priority.

    High-priority goals tighten thresholds (multiplier < 1.0 = stricter).
    Low-priority / exploratory goals relax them (multiplier > 1.0 = looser).

    Returns a dict with multiplier keys matching ControlPolicy's adjustment format.
    """
    if not goal.active:
        return {}

    p = goal.priority

    if p >= 0.8:
        return {
            "hallucination_confidence": 1.2,
            "low_quality": 0.85,
            "block_confidence": 1.1,
        }
    elif p >= 0.5:
        return {}
    else:
        return {
            "hallucination_confidence": 0.8,
            "low_quality": 1.2,
            "block_confidence": 0.9,
        }


def strategy_goal_score(strategy_name: str, goal: GoalState) -> float:
    """Score a strategy's relevance to a goal.

    Returns a float in [0.0, 1.0] representing how well the strategy
    aligns with the goal's success criteria.

    Strategy-criteria affinity mapping (deterministic):
        - "structured" aligns with precision/accuracy goals
        - "clarity" aligns with communication/sales goals
        - "concise" aligns with speed/efficiency goals
        - "baseline" is neutral (0.5)
    """
    if not goal.active or not goal.success_criteria:
        return 0.5

    criteria_values = set()
    for v in goal.success_criteria.values():
        if isinstance(v, str):
            criteria_values.add(v.lower())

    affinity_map: dict[str, set[str]] = {
        "structured": {
            "precision",
            "accuracy",
            "analytical",
            "technical",
            "structured",
        },
        "clarity": {"persuasive", "communication", "sales", "clear", "direct"},
        "concise": {"fast", "efficient", "speed", "concise", "brief"},
        "baseline": set(),
    }

    affinities = affinity_map.get(strategy_name, set())
    if not affinities:
        return 0.5

    overlap = affinities & criteria_values
    if overlap:
        return min(0.5 + 0.25 * len(overlap), 1.0)

    return 0.5
