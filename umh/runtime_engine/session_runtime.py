"""
SessionRuntime — session-level wrapper around ExecutionSpine.

Owns the concerns that the spine deliberately does not:
    - Message accumulation for context compaction
    - Session-level token/cost aggregation across turns
    - Automatic compaction when token pressure exceeds threshold

The spine is stateless per-call.  This layer adds statefulness
per-session without modifying spine responsibilities.

Usage::

    from umh.runtime_engine.session_runtime import SessionRuntime

    session = SessionRuntime(ctx)
    result = session.run(
        message=prompt,
        unified_context=uctx,
        agent_type="executive_assistant",
        ...
    )
    # result is a SpineResult (str subclass) — same as spine.run()
    # session.stats has accumulated token/cost data
"""

import logging
import uuid
from dataclasses import dataclass, field

_log = logging.getLogger(__name__)


@dataclass
class SessionStats:
    """Accumulated metadata across all turns in a session."""

    total_tokens_in: int = 0
    total_tokens_out: int = 0
    total_cost_usd: float = 0.0
    turns: int = 0
    compactions: int = 0
    models_used: list[str] = field(default_factory=list)
    evaluations: list[dict] = field(default_factory=list)
    strategy_stats: dict[str, dict] = field(default_factory=dict)
    decision_traces: list = field(default_factory=list)

    @property
    def total_tokens(self) -> int:
        return self.total_tokens_in + self.total_tokens_out

    def sync_strategy_stats(self) -> None:
        """Pull current strategy stats from the global strategy memory."""
        try:
            from umh.strategy.memory import get_strategy_memory

            self.strategy_stats = get_strategy_memory().to_dict()
        except Exception:
            pass


CALIBRATION_INTERVAL = 10


class SessionRuntime:
    """Session-scoped wrapper that delegates to ExecutionSpine.

    Adds: message tracking, auto-compaction, metadata aggregation,
    optional control layer evaluation, and optional self-tuning
    calibration of thresholds.
    Does NOT replicate any spine logic.
    """

    def __init__(
        self,
        ctx: object,
        session_id: str | None = None,
        control_enabled: bool = False,
        calibration_enabled: bool = False,
        convergence_enabled: bool = False,
        persist_memory: bool = False,
    ) -> None:
        self.ctx = ctx
        self.session_id: str = session_id or str(uuid.uuid4())
        self.stats = SessionStats()
        self._messages: list[dict] = []
        self._pending_control_directives: list[str] = []
        self._pending_strategy_override: str | None = None
        self._pending_convergence_directives: list[str] = []
        self._pending_synthesis_suppression: bool = False
        self._pending_exploration_suppression: bool = False
        self._unified_influence: "UnifiedInfluence | None" = None
        self._goal_state: object | None = None
        self._goal_eval_current: object | None = None
        self._goal_eval_prev: object | None = None
        self._goal_registry: object | None = None
        self._goal_arbitrator: object | None = None
        self._goal_evals: dict[str, object] = {}
        self._goal_prev_evals: dict[str, object] = {}
        self._blended_goal_state: object | None = None
        self._execution_budget: object | None = None
        self._persist_memory = persist_memory
        self._memory_version: int = 0
        self._objective_history: list[float] = []
        if persist_memory:
            try:
                from umh.protocols.persistence import load_objective_history

                _loaded = load_objective_history()
                if _loaded is not None:
                    self._objective_history = _loaded
            except Exception:
                pass
        self._outcome_store: object | None = None
        self._exploration_controller: object | None = None
        self._exploration_state: object | None = None
        self._meta_goal_engine: object | None = None
        self._trap_detector: object | None = None
        self._context_classifier: object | None = None
        self._meta_gen: object | None = None
        self._causal_mem: object | None = None
        self._credit_eng: object | None = None

        self._world_substrate: object | None = None
        self._signal_ingestion: object | None = None
        self._world_calibration: object | None = None
        self._world_dynamics_adapter: object | None = None
        self._objective_arbiter: object | None = None
        self._strategy_pattern_memory: object | None = None
        self._policy_tracker: object | None = None
        self._compiled_intent: object | None = None
        if persist_memory:
            try:
                from umh.world.substrate import WorldSubstrate
                from umh.runtime_engine.signal_ingestion import SignalIngestionEngine
                from umh.protocols.persistence import load_world_substrate

                ws = WorldSubstrate()
                _ws_data = load_world_substrate()
                if _ws_data is not None:
                    ws.restore(_ws_data)
                self._world_substrate = ws
                self._signal_ingestion = SignalIngestionEngine()
            except Exception:
                pass
            try:
                from umh.world.calibration import WorldCalibrationEngine

                self._world_calibration = WorldCalibrationEngine()
            except Exception:
                pass
            try:
                from umh.world.dynamics_adapter import WorldDynamicsAdapter

                self._world_dynamics_adapter = WorldDynamicsAdapter()
            except Exception:
                pass
            try:
                from umh.runtime_engine.objective_arbitration import ObjectiveArbiter

                self._objective_arbiter = ObjectiveArbiter()
            except Exception:
                pass
            try:
                from umh.analytics.strategy_pattern_memory import StrategyPatternMemory

                self._strategy_pattern_memory = StrategyPatternMemory()
            except Exception:
                pass
            try:
                from umh.runtime_engine.policy_state import PolicyStateTracker

                self._policy_tracker = PolicyStateTracker()
            except Exception:
                pass

        self._control_policy: object | None = None
        if control_enabled:
            try:
                from umh.reasoning.control_layer import ControlPolicy

                self._control_policy = ControlPolicy(enabled=True)
            except Exception:
                pass

        self._calibration_engine: object | None = None
        if calibration_enabled:
            try:
                from umh.world.calibration import CalibrationEngine

                self._calibration_engine = CalibrationEngine(enabled=True)
            except Exception:
                pass

        self._convergence_engine: object | None = None
        if convergence_enabled:
            try:
                from umh.reasoning.convergence import ConvergenceEngine

                self._convergence_engine = ConvergenceEngine(enabled=True)
            except Exception:
                pass

    def set_intent(self, intent_input: object) -> object | None:
        """Compile a user intent into structured meta-harness configuration."""
        try:
            from umh.runtime_engine.intent_compiler import compile_intent

            self._compiled_intent = compile_intent(intent_input)
            return self._compiled_intent
        except Exception:
            return None

    def run(
        self,
        message: str,
        unified_context: object,
        agent_type: str = "executive_assistant",
        authority_class: str = "analyze",
        channel_id: str | None = None,
        org_id: str | None = None,
        user_id: str | None = None,
        task_type: object = None,
        venture_id: str | None = None,
        skill_name: str | None = None,
        calibrated_thresholds: "CalibratedThresholds | None" = None,
        goal_mode: str | None = None,
    ) -> "SpineResult":
        """Execute via spine, accumulate metadata, check compaction.

        When ``goal_mode`` is provided (or inferred from the message),
        strategy selection, directive filtering, and control sensitivity
        are adapted to the goal type. Mode is resolved once and threaded
        through all downstream layers.

        For eligible task types (GENERATE, ANALYZE), generates multiple
        candidate responses via multi-strategy, selects the best
        deterministically, and only persists the winner.  Rejected
        candidates leave zero trace in memory, feedback, or world model.
        Non-eligible tasks go through the normal single-execution spine.
        """
        from umh.runtime_engine.execution_spine import SpineResult

        # Resolve goal mode once — explicit > inferred > DEFAULT
        _resolved_mode = None
        _resolved_mode_str: str | None = None
        try:
            from umh.runtime_engine.goal_mode import GoalMode, resolve_mode

            _resolved_mode = resolve_mode(explicit=goal_mode, message=message)
            if _resolved_mode != GoalMode.DEFAULT:
                _resolved_mode_str = _resolved_mode.value
        except Exception as e:
            _log.debug("Goal mode resolution failed: %s", e)

        # Multi-goal blending: compute weighted mixture before pipeline runs.
        # Replaces single-goal arbitration with top-K blend.
        # Primary goal feeds existing pipeline; blend feeds influence layer.
        _active_goal_id: str | None = None
        _goal_pool_snapshot: dict | None = None
        _blended_goals: "tuple[tuple[str, float], ...] | None" = None
        _blended_primary_id: str | None = None
        _blended_entropy: float | None = None
        _exec_budget_dict: dict | None = None
        _candidate_dist: dict | None = None
        _previous_active_goal_id: str | None = None
        _switch_penalty_applied: bool | None = None
        _persistence_streaks: dict | None = None
        _commitment_bonuses: dict | None = None

        # Read prior turn's influence score for forward-feedback integration
        _prior_influence_score: float = 0.0
        _influence_applied: bool | None = None
        _influence_adjustment: float | None = None
        if self.stats.decision_traces:
            _last_trace = self.stats.decision_traces[-1]
            _pis = getattr(_last_trace, "final_influence_score", None)
            if _pis is not None and _pis > 0:
                _prior_influence_score = _pis

        if self._goal_registry is not None:
            try:
                from umh.runtime_engine.goal_arbitrator import GoalArbitrator

                if self._goal_arbitrator is None:
                    self._goal_arbitrator = GoalArbitrator()

                _previous_active_goal_id = self._goal_registry.active_goal_id
                self._goal_registry.advance_turn()
                blend = self._goal_arbitrator.blend_goals(
                    self._goal_registry,
                    previous_active_goal_id=_previous_active_goal_id,
                    influence_score=_prior_influence_score,
                )
                self._blended_goal_state = blend

                if blend.primary_goal_id:
                    self._goal_registry.set_active_goal(blend.primary_goal_id)
                    selected = self._goal_registry.get_active_goal()
                    self._goal_state = selected
                    _active_goal_id = blend.primary_goal_id
                    _blended_goals = blend.goals
                    _blended_primary_id = blend.primary_goal_id
                    _blended_entropy = blend.entropy

                    _switch_penalty_applied = (
                        _previous_active_goal_id is not None
                        and blend.primary_goal_id != _previous_active_goal_id
                    )

                    # Update persistence streaks for all tracked goals
                    for _gid, _trk in self._goal_registry.get_all_trackers().items():
                        _trk.update_persistence(
                            is_active=(_gid == blend.primary_goal_id)
                        )

                    # Derive execution budget from blend
                    try:
                        from umh.runtime_engine.execution_budget import derive_budget

                        _budget = derive_budget(blend)
                        self._execution_budget = _budget
                        _exec_budget_dict = _budget.to_dict()
                        _candidate_dist = _budget.candidate_distribution
                    except Exception as e:
                        _log.debug("Budget derivation skipped: %s", e)

                _goal_pool_snapshot = self._goal_registry.snapshot()
            except Exception as e:
                _log.debug("Goal blending skipped: %s", e)

        # Track user message for compaction threshold
        self._messages.append({"role": "user", "content": message})

        # Check compaction BEFORE the call (same pattern as old CognitiveLoop)
        self._maybe_compact()

        # Resolve calibrated min_confidence for strategy learning gate
        _min_conf: float | None = None
        if calibrated_thresholds is not None:
            _min_conf = calibrated_thresholds.min_confidence

        # Adaptive exploration: compute exploration_rate from recent signals.
        _exploration_rate: float | None = None
        _exploration_reason: str | None = None
        try:
            from umh.analytics.adaptive_exploration import ExplorationController

            if self._exploration_controller is None:
                self._exploration_controller = ExplorationController()

            _goal_delta_hist: list[float] = []
            for _ht in self.stats.decision_traces:
                _hd = getattr(_ht, "goal_delta", None)
                if _hd is not None:
                    _goal_delta_hist.append(_hd)

            _conv_status_str = None
            if self.stats.decision_traces:
                _last_t = self.stats.decision_traces[-1]
                _conv_status_str = getattr(_last_t, "convergence_status", None)

            _cf_unc_signal: float | None = None
            _horizon_signal: float | None = None
            if self.stats.decision_traces:
                _last_cf_unc = getattr(
                    self.stats.decision_traces[-1],
                    "counterfactual_uncertainty",
                    None,
                )
                if _last_cf_unc and isinstance(_last_cf_unc, dict):
                    _cf_unc_signal = (
                        max(_last_cf_unc.values()) if _last_cf_unc else None
                    )
                _last_horizon = getattr(
                    self.stats.decision_traces[-1],
                    "counterfactual_horizon_value",
                    None,
                )
                if _last_horizon and isinstance(_last_horizon, dict):
                    _horizon_signal = (
                        max(_last_horizon.values()) if _last_horizon else None
                    )

            _exp_state = self._exploration_controller.compute(
                goal_deltas=_goal_delta_hist or None,
                convergence_status=_conv_status_str,
                blended_entropy=_blended_entropy,
                candidate_scores=None,
                counterfactual_uncertainty=_cf_unc_signal,
                horizon_value=_horizon_signal,
            )
            self._exploration_state = _exp_state
            _exploration_rate = _exp_state.exploration_rate
            _exploration_reason = _exp_state.reason

            if _exploration_rate is not None and self._blended_goal_state is not None:
                try:
                    from umh.analytics.adaptive_exploration import (
                        exploration_rate_to_budget_modifier,
                    )
                    from umh.runtime_engine.execution_budget import derive_budget as _re_derive

                    _mod = exploration_rate_to_budget_modifier(_exploration_rate)
                    _budget = _re_derive(
                        self._blended_goal_state,
                        exploration_modifier=_mod,
                    )
                    self._execution_budget = _budget
                    _exec_budget_dict = _budget.to_dict()
                    _candidate_dist = _budget.candidate_distribution
                except Exception as _be:
                    _log.debug("Budget re-derivation skipped: %s", _be)
        except Exception as e:
            _log.debug("Exploration controller skipped: %s", e)

        # Delegate to multi-strategy layer.  For eligible task types this
        # generates multiple candidates, evaluates each deterministically,
        # selects the best, and persists only the winner (stages 6-10).
        # For non-eligible types it falls through to normal spine execution.
        try:
            from umh.runtime_engine.multi_strategy import run_with_strategies
        except ImportError:
            pass

        _influence = self.get_unified_influence()

        result = run_with_strategies(
            message=message,
            unified_context=unified_context,
            agent_type=agent_type,
            authority_class=authority_class,
            session_id=self.session_id,
            channel_id=channel_id,
            org_id=org_id,
            user_id=user_id,
            task_type=task_type,
            venture_id=venture_id,
            skill_name=skill_name,
            min_confidence=_min_conf,
            goal_mode=_resolved_mode,
            strategy_override=_influence.strategy_override,
            exploration_enabled=_influence.exploration_enabled,
            goal_state=self._goal_state,
            budget_allocation=self._execution_budget,
            goal_registry=self._goal_registry,
            exploration_rate=_exploration_rate,
        )

        # Accumulate session-level stats from SpineResult metadata
        if isinstance(result, SpineResult):
            tokens = result.tokens_used
            self.stats.total_tokens_in += tokens.get("input", 0)
            self.stats.total_tokens_out += tokens.get("output", 0)
            self.stats.total_cost_usd += result.cost_usd
            if result.model_used and result.model_used != "unknown":
                if result.model_used not in self.stats.models_used:
                    self.stats.models_used.append(result.model_used)

        self.stats.turns += 1

        # Recalibrate thresholds periodically
        if (
            self._calibration_engine is not None
            and self.stats.turns % CALIBRATION_INTERVAL == 0
        ):
            try:
                self._calibration_engine.calibrate()
            except Exception as e:
                _log.debug("Session calibration skipped: %s", e)

        # Reuse the caller-provided snapshot when available so that
        # ContextBuilder.build() and this run() share the same values.
        # Otherwise fetch from the calibration engine (or None).
        if calibrated_thresholds is not None:
            thresholds = calibrated_thresholds
            thresholds_dict = thresholds.to_dict()
        else:
            thresholds = None
            thresholds_dict = None
            if self._calibration_engine is not None:
                try:
                    from umh.world.calibration import get_thresholds

                    thresholds = get_thresholds(self._calibration_engine)
                    thresholds_dict = thresholds.to_dict()
                except Exception:
                    pass

        # Track assistant response for compaction threshold
        response_text = str(result)
        if response_text:
            self._messages.append({"role": "assistant", "content": response_text})

        # Record evaluation for adaptive prompt layer (capped to session horizon)
        evaluation: dict | None = None
        signals = None
        if response_text and not response_text.startswith("[ExecutionSpine]"):
            try:
                from umh.feedback.outcome_evaluator import evaluate_outcome
                from umh.runtime_engine.adaptive_prompt import MAX_SESSION_HISTORY

                evaluation = evaluate_outcome(
                    input_text=message,
                    output_text=response_text,
                    context={"agent_type": agent_type, "venture_id": venture_id or ""},
                    metadata={"model_used": getattr(result, "model_used", "unknown")},
                )
                self.stats.evaluations.append(evaluation)
                if len(self.stats.evaluations) > MAX_SESSION_HISTORY:
                    self.stats.evaluations = self.stats.evaluations[
                        -MAX_SESSION_HISTORY:
                    ]

                try:
                    from umh.runtime_engine.signal_router import route_signals

                    wm_thresh = (
                        thresholds.world_model_confidence_threshold
                        if thresholds is not None
                        else None
                    )
                    signals = route_signals(
                        evaluation,
                        wm_confidence_threshold=wm_thresh,
                    )
                except Exception:
                    pass
            except Exception as e:
                _log.debug("Session evaluation recording skipped: %s", e)

        # Build strategy selection summary for the trace when multi-strategy
        # was used (iterations > 1 means multiple candidates were generated).
        _strat_sel: dict | None = None
        _iterations = getattr(result, "iterations", 1)
        if _iterations > 1:
            try:
                from umh.strategy.memory import get_strategy_memory
                from umh.runtime_engine.multi_strategy import STRATEGY_PROMPT_DIRECTIVES

                _smem = get_strategy_memory()
                _ranked = _smem.rank_strategies()
                _winner_name = _ranked[0][0] if _ranked else ""

                _directive_scores: dict[str, float] = {}
                try:
                    from umh.runtime_engine.directive_memory import get_directive_memory

                    _dmem = get_directive_memory()
                    _dturn = _dmem.global_turn
                    for _dn, _ds in _dmem.rank_directives():
                        _directive_scores[_dn] = round(_ds.effective_score(_dturn), 4)
                except Exception:
                    pass

                _strat_sel = {
                    "enabled": True,
                    "candidates": _iterations,
                    "selected_strategy": _winner_name,
                    "candidate_scores": {
                        n: round(s.effective_score(_smem.global_turn), 4)
                        for n, s in _ranked
                    },
                    "prompt_directive_applied": bool(
                        STRATEGY_PROMPT_DIRECTIVES.get(_winner_name, "")
                    ),
                    "directive_scores": _directive_scores,
                }
            except Exception:
                _strat_sel = {"enabled": True, "candidates": _iterations}

        # World substrate: build snapshot for trace enrichment (read-only)
        _ws_snapshot_version: int | None = None
        _ws_obs_count: int | None = None
        _ws_entity_count: int | None = None
        _ws_relation_count: int | None = None
        _ws_signal_count: int | None = None
        _ws_signal_sources: tuple[str, ...] | None = None
        if self._world_substrate is not None:
            try:
                _ws_summary = self._world_substrate.summary()
                _ws_snapshot_version = _ws_summary.get("version", 0)
                _ws_obs_count = _ws_summary.get("observation_count", 0)
                _ws_entity_count = _ws_summary.get("entity_count", 0)
                _ws_relation_count = _ws_summary.get("relation_count", 0)
                if self._signal_ingestion is not None:
                    _si_fields = self._signal_ingestion.get_trace_fields()
                    _ws_signal_count = _si_fields.get("ingested_signal_count")
                    _ws_signal_sources = _si_fields.get("ingested_signal_sources")
            except Exception:
                pass

        # World reasoning: derive understanding from substrate (read-only)
        _wr_derived_count: int | None = None
        _wr_global_flags: tuple[str, ...] | None = None
        _wr_riskiest_entity: str | None = None
        _wr_riskiest_entity_health: str | None = None
        _wr_volatile_count: int | None = None
        _wr_bad_count: int | None = None
        if self._world_substrate is not None:
            try:
                from umh.world.reasoning import (
                    WorldReasoningEngine,
                    get_riskiest_entities,
                )

                _ws_snap = self._world_substrate.build_snapshot()
                _ws_obs = tuple(self._world_substrate.get_observations(limit=500))
                _wr_engine = WorldReasoningEngine()
                _wr_result = _wr_engine.derive_understanding(_ws_snap, _ws_obs)
                _wr_derived_count = _wr_result.derived_count
                _wr_global_flags = _wr_result.global_flags
                _wr_riskiest = get_riskiest_entities(_wr_result, limit=1)
                if _wr_riskiest:
                    _wr_riskiest_entity = _wr_riskiest[0].entity_id
                    _wr_riskiest_entity_health = _wr_riskiest[0].health
                _wr_volatile_count = sum(
                    1
                    for a in _wr_result.entity_assessments
                    if a.stability in ("volatile", "unstable")
                )
                _wr_bad_count = sum(
                    1 for a in _wr_result.entity_assessments if a.health == "bad"
                )
            except Exception:
                pass

        # World simulation: forward model from current understanding (trace-only)
        _sim_ran: bool | None = None
        _sim_action_count: int | None = None
        _sim_best_action_id: str | None = None
        _sim_best_improvement: float | None = None
        _sim_best_risk: float | None = None
        _sim_horizon: int | None = None
        _sim_global_flags: tuple[str, ...] | None = None
        _dyn_adjustment = None
        _pol_world_count: int | None = None
        _pol_variance: float | None = None
        _pol_worst_case: float | None = None
        _pol_robust_score: float | None = None
        _arb_mode: str | None = None
        _arb_reward_w: float | None = None
        _arb_risk_w: float | None = None
        _arb_stability_w: float | None = None
        _arb_shift_reason: str | None = None
        _intent_source: str | None = None
        _intent_compiled_weights: dict | None = None
        _intent_applied_biases: dict | None = None
        _mc_mode: str | None = None
        _mc_agreement: float | None = None
        _mc_instability: float | None = None
        _mc_enabled_layers: tuple[str, ...] | None = None
        _mc_permissions = None
        _ps_osc: float | None = None
        _ps_cons: float | None = None
        _ps_flags: dict | None = None
        try:
            from umh.reasoning.meta_control import compute_meta_control, permissions_for_mode

            _mc_state = compute_meta_control(self.stats.decision_traces)
            _mc_mode = _mc_state.mode
            _mc_agreement = _mc_state.agreement_score
            _mc_instability = _mc_state.instability_score
            _mc_enabled_layers = _mc_state.permissions.enabled_names()
            _mc_permissions = _mc_state.permissions

            if self._policy_tracker is not None:
                try:
                    from umh.runtime_engine.policy_state import apply_policy_to_meta_control

                    _prev_action = None
                    _prev_ctx = None
                    _prev_override = False
                    _prev_expl = False
                    if self.stats.decision_traces:
                        _lt = self.stats.decision_traces[-1]
                        _prev_action = getattr(_lt, "simulated_best_action_id", None)
                        _prev_ctx = getattr(_lt, "context_type", None)
                        _prev_override = getattr(_lt, "planner_active", False) or False
                        _prev_expl = (
                            getattr(_lt, "det_exploration_active", False) or False
                        )
                    self._policy_tracker.record_turn(
                        action_id=_prev_action,
                        mode=_mc_mode,
                        context_type=_prev_ctx,
                        planner_override_used=_prev_override,
                        exploration_used=_prev_expl,
                    )
                    _adjusted_mode = apply_policy_to_meta_control(
                        _mc_mode, self._policy_tracker
                    )
                    if _adjusted_mode != _mc_mode:
                        _mc_mode = _adjusted_mode
                        _mc_permissions = permissions_for_mode(_mc_mode)
                        _mc_enabled_layers = _mc_permissions.enabled_names()
                    _ps_fields = self._policy_tracker.get_trace_fields()
                    _ps_osc = _ps_fields.get("policy_oscillation_score")
                    _ps_cons = _ps_fields.get("policy_consistency_score")
                    _ps_flags = _ps_fields.get("policy_flags")
                except Exception:
                    pass
        except Exception:
            pass
        if self._world_substrate is not None and _wr_derived_count is not None:
            try:
                from umh.world.simulation import (
                    WorldSimulationEngine,
                    derive_simulation_actions,
                )

                if self._world_dynamics_adapter is not None:
                    _dyn_adjustment = self._world_dynamics_adapter.get_adjustments()

                # Objective arbitration: update weights from context signals
                _obj_weights = None
                if self._objective_arbiter is not None:
                    try:
                        from umh.runtime_engine.objective_arbitration import ContextSignals

                        _arb_ctx = None
                        if self.stats.decision_traces:
                            _arb_ctx = getattr(
                                self.stats.decision_traces[-1], "context_type", None
                            )
                        _arb_signals = ContextSignals(
                            context_type=_arb_ctx,
                            uncertainty=0.0,
                        )
                        _arb_result = self._objective_arbiter.update(_arb_signals)
                        if _arb_result.active:
                            _obj_weights = _arb_result.weights
                            _arb_mode = _arb_result.mode
                            _arb_reward_w = _arb_result.weights.reward_weight
                            _arb_risk_w = _arb_result.weights.risk_weight
                            _arb_stability_w = _arb_result.weights.stability_weight
                            _arb_shift_reason = _arb_result.shift_reason
                    except Exception:
                        pass

                # Intent compiler: override objective weights if user intent is set
                if self._compiled_intent is not None:
                    try:
                        from umh.runtime_engine.intent_compiler import (
                            to_objective_weights,
                            get_trace_fields as _ic_trace,
                        )

                        _intent_weights = to_objective_weights(self._compiled_intent)
                        if _intent_weights is not None:
                            _obj_weights = _intent_weights
                            _arb_reward_w = _intent_weights.reward_weight
                            _arb_risk_w = _intent_weights.risk_weight
                            _arb_stability_w = _intent_weights.stability_weight
                            _arb_shift_reason = "intent_override"
                        _ic_fields = _ic_trace(self._compiled_intent)
                        _intent_source = _ic_fields.get("intent_source")
                        _intent_compiled_weights = _ic_fields.get(
                            "intent_compiled_weights"
                        )
                        _intent_applied_biases = _ic_fields.get("intent_applied_biases")
                    except Exception:
                        pass

                _sim_actions = derive_simulation_actions(_ws_snap, _wr_result)
                if _sim_actions:
                    _sim_engine = WorldSimulationEngine()
                    _sim_results = _sim_engine.simulate_actions(
                        _ws_snap,
                        _wr_result,
                        _sim_actions,
                        horizon=3,
                        observation_history=_ws_obs,
                        adjustment=_dyn_adjustment,
                    )
                    _sim_ran = True
                    _sim_action_count = len(_sim_results)
                    _sim_horizon = 3

                    _prev_ctx = None
                    if self.stats.decision_traces:
                        _prev_ctx = getattr(
                            self.stats.decision_traces[-1], "context_type", None
                        )

                    _policy_used = False
                    try:
                        from umh.runtime_engine.multi_world_policy import (
                            evaluate_multi_world_policy,
                        )

                        _mwp_result = evaluate_multi_world_policy(
                            actions=_sim_actions,
                            snapshot=_ws_snap,
                            understanding=_wr_result,
                            base_adjustment=_dyn_adjustment,
                            horizon=3,
                            observation_history=_ws_obs,
                            context_type=_prev_ctx,
                            uncertainty=0.0,
                            objective_weights=_obj_weights,
                        )
                        if _mwp_result.active and _mwp_result.selected_action_id:
                            _policy_used = True
                            _sim_best_action_id = _mwp_result.selected_action_id
                            _best_eval = next(
                                e
                                for e in _mwp_result.evaluations
                                if e.action_id == _mwp_result.selected_action_id
                            )
                            _sim_best_improvement = _best_eval.mean_score
                            _sim_best_risk = 0.0
                            _pol_world_count = _mwp_result.world_count
                            _pol_variance = _best_eval.variance
                            _pol_worst_case = _best_eval.worst_case
                            _pol_robust_score = _best_eval.robust_score
                            _best_sim = next(
                                (
                                    r
                                    for r in _sim_results
                                    if r.action_id == _sim_best_action_id
                                ),
                                _sim_results[0],
                            )
                            _sim_global_flags = (
                                _best_sim.final_world_understanding.global_flags
                            )
                    except Exception:
                        pass

                    if not _policy_used:
                        if _obj_weights is not None:
                            from umh.runtime_engine.objective_arbitration import (
                                compute_weighted_score,
                            )

                            _best = max(
                                _sim_results,
                                key=lambda r: compute_weighted_score(
                                    weights=_obj_weights,
                                    improvement=r.aggregate_improvement,
                                    risk=r.aggregate_risk,
                                ),
                            )
                        else:
                            _best = max(
                                _sim_results,
                                key=lambda r: (
                                    r.aggregate_improvement - r.aggregate_risk
                                ),
                            )
                        _sim_best_action_id = _best.action_id
                        _sim_best_improvement = _best.aggregate_improvement
                        _sim_best_risk = _best.aggregate_risk
                        _sim_global_flags = _best.final_world_understanding.global_flags
            except Exception:
                pass

        # Strategy pattern memory: record outcome + compute bias (trace-only)
        _sp_match_found: bool | None = None
        _sp_confidence: float | None = None
        _sp_bias_applied: bool | None = None
        _sp_id: str | None = None
        if (
            self._strategy_pattern_memory is not None
            and _sim_ran
            and _sim_best_action_id is not None
        ):
            try:
                from umh.analytics.strategy_pattern_memory import build_signature

                _sp_ctx = None
                _sp_obj_mode = None
                if self.stats.decision_traces:
                    _last_t = self.stats.decision_traces[-1]
                    _sp_ctx = getattr(_last_t, "context_type", None)
                    _sp_obj_mode = getattr(_last_t, "objective_arb_mode", None)

                _sp_sig = build_signature(
                    context_type=_sp_ctx,
                    objective_mode=_sp_obj_mode,
                )

                _sp_score = (_sim_best_improvement or 0.0) - (_sim_best_risk or 0.0)
                _sp_seq = (_sim_best_action_id,)
                self._strategy_pattern_memory.record_outcome(
                    signature=_sp_sig,
                    action_sequence=_sp_seq,
                    outcome_score=_sp_score,
                    step=self.stats.turns,
                )

                _sp_allowed = (
                    _mc_permissions is None or _mc_permissions.allow_strategy_memory
                )
                _sp_matched = self._strategy_pattern_memory.find_matching(_sp_sig)
                if _sp_matched:
                    _sp_match_found = True
                    _sp_confidence = _sp_matched[0].confidence
                    _sp_id = _sp_matched[0].strategy_id
                    if _sp_allowed:
                        _sp_biases = self._strategy_pattern_memory.get_action_biases(
                            query=_sp_sig,
                            action_ids=tuple(r.action_id for r in _sim_results),
                            context_type=_sp_ctx,
                        )
                        _sp_bias_applied = bool(_sp_biases)
                    else:
                        _sp_bias_applied = False
                else:
                    _sp_match_found = False
            except Exception:
                pass

        # World calibration: record prediction + match past predictions (trace-only)
        _cal_error: float | None = None
        _cal_confidence: float | None = None
        _cal_trend_bias: float | None = None
        _cal_risk_bias: float | None = None
        if self._world_calibration is not None and _wr_derived_count is not None:
            try:
                if _sim_ran and _sim_best_action_id is not None:
                    self._world_calibration.record_prediction(
                        action_id=_sim_best_action_id,
                        predicted_snapshot=_best.final_world_snapshot,
                        predicted_understanding=_best.final_world_understanding,
                        horizon=_sim_horizon or 3,
                        timestamp_step=self.stats.turns,
                    )
                self._world_calibration.record_outcome(
                    action_id=_sim_best_action_id or f"turn_{self.stats.turns}",
                    actual_snapshot=_ws_snap,
                    actual_understanding=_wr_result,
                    timestamp_step=self.stats.turns,
                )
                _cal_summaries = self._world_calibration.match_predictions(
                    self.stats.turns
                )
                _cal_fields = self._world_calibration.get_calibration_trace_fields()
                _cal_error = _cal_fields.get("calibration_error")
                _cal_confidence = _cal_fields.get("calibration_confidence")
                _cal_trend_bias = _cal_fields.get("calibration_trend_bias")
                _cal_risk_bias = _cal_fields.get("calibration_risk_bias")
            except Exception:
                _cal_summaries = []

        # Dynamics adaptation: update adapter from new calibration summaries
        _dyn_trend_mult: float | None = None
        _dyn_risk_mult: float | None = None
        _dyn_stab_mod: float | None = None
        _dyn_conf_scale: float | None = None
        if self._world_dynamics_adapter is not None:
            try:
                _adapt_ctx = None
                if self.stats.decision_traces:
                    _adapt_ctx = getattr(
                        self.stats.decision_traces[-1], "context_type", None
                    )
                for _cal_sum in _cal_summaries or []:
                    self._world_dynamics_adapter.update_from_calibration(
                        _cal_sum,
                        context_type=_adapt_ctx,
                    )
                _dyn_fields = self._world_dynamics_adapter.get_trace_fields()
                _dyn_trend_mult = _dyn_fields.get("dynamics_trend_multiplier")
                _dyn_risk_mult = _dyn_fields.get("dynamics_risk_multiplier")
                _dyn_stab_mod = _dyn_fields.get("dynamics_stability_modifier")
                _dyn_conf_scale = _dyn_fields.get("dynamics_confidence_scale")
            except Exception:
                pass

        # Build decision trace (pure instrumentation — never blocks the response)
        try:
            from umh.runtime_engine.decision_trace import build_trace, MAX_TRACES

            trace = build_trace(
                turn_id=self.stats.turns,
                evaluation=evaluation,
                signals=signals,
                result=result,
                thresholds_used=thresholds_dict,
                strategy_selection=_strat_sel,
                goal_mode=_resolved_mode_str,
                world_snapshot_version=_ws_snapshot_version,
                world_observation_count=_ws_obs_count,
                world_entity_count=_ws_entity_count,
                world_relation_count=_ws_relation_count,
                ingested_signal_count=_ws_signal_count,
                ingested_signal_sources=_ws_signal_sources,
                world_derived_count=_wr_derived_count,
                world_global_flags=_wr_global_flags,
                world_riskiest_entity=_wr_riskiest_entity,
                world_riskiest_entity_health=_wr_riskiest_entity_health,
                world_volatile_entity_count=_wr_volatile_count,
                world_bad_entity_count=_wr_bad_count,
                simulation_ran=_sim_ran,
                simulated_action_count=_sim_action_count,
                simulated_best_action_id=_sim_best_action_id,
                simulated_best_improvement=_sim_best_improvement,
                simulated_best_risk=_sim_best_risk,
                simulated_horizon=_sim_horizon,
                simulated_global_flags=_sim_global_flags,
                calibration_error=_cal_error,
                calibration_confidence=_cal_confidence,
                calibration_trend_bias=_cal_trend_bias,
                calibration_risk_bias=_cal_risk_bias,
                dynamics_trend_multiplier=_dyn_trend_mult,
                dynamics_risk_multiplier=_dyn_risk_mult,
                dynamics_stability_modifier=_dyn_stab_mod,
                dynamics_confidence_scale=_dyn_conf_scale,
                policy_world_count=_pol_world_count,
                policy_variance=_pol_variance,
                policy_worst_case=_pol_worst_case,
                policy_robust_score=_pol_robust_score,
                objective_arb_mode=_arb_mode,
                objective_arb_reward_weight=_arb_reward_w,
                objective_arb_risk_weight=_arb_risk_w,
                objective_arb_stability_weight=_arb_stability_w,
                objective_arb_shift_reason=_arb_shift_reason,
                strat_pattern_match_found=_sp_match_found,
                strat_pattern_confidence=_sp_confidence,
                strat_pattern_bias_applied=_sp_bias_applied,
                strat_pattern_id=_sp_id,
                meta_control_mode=_mc_mode,
                meta_control_agreement=_mc_agreement,
                meta_control_instability=_mc_instability,
                meta_control_enabled_layers=_mc_enabled_layers,
                policy_oscillation_score=_ps_osc,
                policy_consistency_score=_ps_cons,
                policy_flags=_ps_flags,
                intent_source=_intent_source,
                intent_compiled_weights=_intent_compiled_weights,
                intent_applied_biases=_intent_applied_biases,
            )
            self.stats.decision_traces.append(trace)
            if len(self.stats.decision_traces) > MAX_TRACES:
                self.stats.decision_traces = self.stats.decision_traces[-MAX_TRACES:]

            # Strategy synthesis: attempt after trace is built, before control.
            # Only fires when strict gating conditions are met (cooldown,
            # high quality, repeated pattern, bounded pool).
            # Gated by unified influence: suppressed when previous turn's
            # control or convergence layers disabled synthesis.
            _synth_strategy: str | None = None
            _synth_reason: str | None = None
            _synth_result = None
            try:
                if not _influence.synthesis_enabled:
                    raise RuntimeError("synthesis suppressed by unified influence")

                from umh.analytics.strategy_synthesizer import (
                    get_synthesizer,
                    register_synthesized_strategy,
                )

                _synth_result = get_synthesizer().maybe_synthesize(
                    traces=self.stats.decision_traces,
                    current_turn=self.stats.turns,
                )
                if _synth_result is not None:
                    if register_synthesized_strategy(_synth_result):
                        _synth_strategy = _synth_result.strategy_id
                        _synth_reason = _synth_result.creation_reason
                        enriched = build_trace(
                            turn_id=trace.turn_id,
                            evaluation=evaluation,
                            signals=signals,
                            result=result,
                            thresholds_used=thresholds_dict,
                            strategy_selection=_strat_sel,
                            synthesized_strategy=_synth_strategy,
                            synthesis_reason=_synth_reason,
                            goal_mode=_resolved_mode_str,
                        )
                        self.stats.decision_traces[-1] = enriched
                        trace = enriched
            except Exception as e:
                _log.debug("Strategy synthesis skipped: %s", e)

            # Strategy mutation: evaluate underperformance/variance/gaps.
            _strategy_mutations: "tuple[dict, ...] | None" = None
            _strategy_origins: dict | None = None
            _mutation_reason: str | None = None
            try:
                from umh.analytics.strategy_mutation import get_mutation_engine
                from umh.strategy.memory import get_strategy_memory as _get_sm

                _mut_engine = get_mutation_engine()
                _sm = _get_sm()
                _mut_results = _mut_engine.evaluate(_sm, self.stats.turns)
                if _mut_results:
                    _mut_dicts: list[dict] = []
                    _origins: dict[str, str] = {}
                    _reasons: list[str] = []
                    for _mr in _mut_results:
                        if _mut_engine.register_mutation(_mr):
                            _mut_dicts.append(_mr.to_dict())
                            _origins[_mr.strategy_id] = _mr.parent_strategy_id
                            _reasons.append(_mr.mutation_reason)
                    if _mut_dicts:
                        _strategy_mutations = tuple(_mut_dicts)
                        _strategy_origins = _origins
                        _mutation_reason = "|".join(_reasons)
            except Exception as e:
                _log.debug("Strategy mutation skipped: %s", e)

            # Hierarchical planning: generate plans, identify next step.
            # Step outcome recording happens AFTER goal evaluation (below)
            # so that per-goal scores are available for attribution.
            _plan_active_id: str | None = None
            _plan_active_step: str | None = None
            _plan_confidence: float | None = None
            _plan_count: int | None = None
            _plan_generation_reason: str | None = None
            _plan_step_goal_id: str | None = None
            _plan_step_attributed_score: float | None = None
            if self._goal_registry is not None:
                try:
                    from umh.planning.hierarchical_planning import get_plan_engine

                    _pe = get_plan_engine(persist=self._persist_memory)
                    _new_plans = _pe.generate_plans(
                        self._goal_registry,
                        self.stats.decision_traces,
                        self.stats.turns,
                    )
                    if _new_plans:
                        _plan_generation_reason = _new_plans[0].generation_reason

                    _plan_action = _pe.get_next_action(
                        self._goal_registry, self.stats.turns
                    )
                    if _plan_action[0] is not None:
                        _plan_active_id = _plan_action[0]
                        _plan_active_step = _plan_action[1]
                        _p_progress = _pe.get_progress(_plan_action[0])
                        if _p_progress is not None:
                            _plan_confidence = _p_progress.confidence

                    _plan_count = _pe.plan_count
                except Exception as e:
                    _log.debug("Hierarchical planning skipped: %s", e)

            # World state: extract, cluster, and compute conditioning bias.
            _world_state_id: str | None = None
            _world_state_cluster: str | None = None
            _world_state_similarity: float | None = None
            _conditioning_bias_dict: dict | None = None
            _strategy_base_scores: dict | None = None
            _strategy_conditioned_scores: dict | None = None
            _state_transfer_weight: float | None = None
            _strategy_transfer_scores: dict | None = None
            _plan_transfer_score_val: float | None = None
            _state_similarity_used: float | None = None
            _replan_adjustment: float | None = None
            try:
                from umh.world.state import (
                    get_world_state_engine,
                    compute_state_transfer_weight,
                )

                _ws_engine = get_world_state_engine()
                _ws = _ws_engine.extract_and_record(
                    registry=self._goal_registry,
                    traces=self.stats.decision_traces,
                    current_turn=self.stats.turns,
                    exploration_rate=_exploration_rate,
                    plan_count=_plan_count or 0,
                    blended_entropy=_blended_entropy,
                )
                _world_state_id = _ws.state_id

                if _goal_score is not None:
                    _ws_engine.record_outcome(
                        _ws,
                        strategy=getattr(trace, "selected_strategy", None),
                        strategy_score=getattr(trace, "quality_score", 0.0),
                        goal_id=_active_goal_id,
                        goal_score=_goal_score,
                        utility=getattr(trace, "quality_score", 0.5),
                    )

                _bias = _ws_engine.get_conditioning_bias(_ws)
                if _bias.cluster_id is not None:
                    _world_state_cluster = _bias.cluster_id
                    _world_state_similarity = _bias.cluster_similarity
                    _conditioning_bias_dict = _bias.to_dict()
                    _state_similarity_used = _bias.cluster_similarity
                    _state_transfer_weight = compute_state_transfer_weight(
                        _bias.cluster_similarity
                    )

                    # Cross-state strategy transfer
                    _strategy_transfer_scores = (
                        _ws_engine.get_strategy_transfer_scores(_ws) or None
                    )

                    if (
                        _bias.strategy_bias
                        or _strategy_transfer_scores
                        or _prior_influence_score > 0
                    ):
                        try:
                            from umh.strategy.memory import (
                                get_strategy_memory as _get_sm_ws,
                            )
                            from umh.reasoning.influence_scoring import (
                                compute_influence_adjustment,
                            )

                            _inf_adj = compute_influence_adjustment(
                                _prior_influence_score
                            )
                            if _inf_adj > 0:
                                _influence_applied = True
                                _influence_adjustment = _inf_adj

                            _sm_ws = _get_sm_ws()
                            _strategy_base_scores, _strategy_conditioned_scores = (
                                _sm_ws.get_conditioned_scores(
                                    conditioning_bias=_bias.strategy_bias,
                                    transfer_scores=_strategy_transfer_scores,
                                    influence_adjustment=_inf_adj,
                                )
                            )
                        except Exception:
                            pass

                    # Cross-state plan transfer
                    if _plan_active_id is not None:
                        try:
                            from umh.planning.hierarchical_planning import get_plan_engine

                            _pe_xfer = get_plan_engine()
                            _xfer_plan = _pe_xfer.get_plan(_plan_active_id)
                            if _xfer_plan is not None:
                                _plan_transfer_score_val = (
                                    _ws_engine.get_plan_transfer_score(
                                        _ws,
                                        _xfer_plan.goal_ids,
                                        self.stats.decision_traces,
                                    )
                                )
                        except Exception:
                            pass

                    # Replan sensitivity adjustment
                    if len(self.stats.decision_traces) >= 2:
                        _prev_sim = getattr(
                            self.stats.decision_traces[-2],
                            "world_state_similarity",
                            None,
                        )
                        if (
                            _prev_sim is not None
                            and _world_state_similarity is not None
                        ):
                            _sim_delta = _prev_sim - _world_state_similarity
                            if abs(_sim_delta) > 0.01:
                                from umh.planning.hierarchical_planning import PlanEngine

                                _replan_adjustment = (
                                    PlanEngine.compute_replan_threshold(_sim_delta)
                                )
            except Exception as e:
                _log.debug("World state extraction skipped: %s", e)

            # Control layer: evaluate trace window, attach decision, queue
            # directives for NEXT turn.  Never re-runs the current turn.
            if self._control_policy is not None:
                try:
                    control = self._control_policy.evaluate(
                        self.stats.decision_traces,
                        thresholds=thresholds,
                        goal_mode=_resolved_mode,
                        goal_state=self._goal_state,
                    )
                    if control.intervene:
                        enriched = build_trace(
                            turn_id=trace.turn_id,
                            evaluation=evaluation,
                            signals=signals,
                            result=result,
                            directives=list(trace.directives_applied),
                            control_decision=control,
                            thresholds_used=thresholds_dict,
                            strategy_selection=_strat_sel,
                            synthesized_strategy=_synth_strategy,
                            synthesis_reason=_synth_reason,
                            goal_mode=_resolved_mode_str,
                        )
                        self.stats.decision_traces[-1] = enriched

                        self._pending_control_directives = list(
                            control.inject_directives
                        )
                        self._pending_strategy_override = control.override_strategy
                    else:
                        self._pending_control_directives = []
                        self._pending_strategy_override = None
                except Exception as e:
                    _log.debug("Control evaluation skipped: %s", e)

            # Convergence: trajectory-aware stability assessment.
            # Runs after control.  Queues corrective state for NEXT turn.
            _conv_status: str | None = None
            _conv_reason: str | None = None
            _conv_action: str | None = None
            if self._convergence_engine is not None:
                try:
                    conv = self._convergence_engine.evaluate(self.stats.decision_traces)
                    from umh.reasoning.convergence import ConvergenceAction

                    if conv.action != ConvergenceAction.NONE:
                        _conv_status = conv.status.value
                        _conv_reason = conv.reason
                        _conv_action = conv.action.value

                        enriched = build_trace(
                            turn_id=trace.turn_id,
                            evaluation=evaluation,
                            signals=signals,
                            result=result,
                            directives=list(trace.directives_applied),
                            control_decision=getattr(trace, "control_decision", None),
                            thresholds_used=thresholds_dict,
                            strategy_selection=_strat_sel,
                            synthesized_strategy=_synth_strategy,
                            synthesis_reason=_synth_reason,
                            goal_mode=_resolved_mode_str,
                            convergence_status=_conv_status,
                            convergence_reason=_conv_reason,
                            convergence_action=_conv_action,
                        )
                        self.stats.decision_traces[-1] = enriched
                        trace = enriched

                        self._pending_convergence_directives = list(conv.directives)
                        self._pending_synthesis_suppression = conv.suppress_synthesis
                        self._pending_exploration_suppression = (
                            conv.suppress_exploration
                        )
                    else:
                        self._pending_convergence_directives = []
                        self._pending_synthesis_suppression = False
                        self._pending_exploration_suppression = False
                except Exception as e:
                    _log.debug("Convergence evaluation skipped: %s", e)

            # Goal evaluation: measure progress toward session goal.
            # Runs after trace + control + convergence are built.
            # Per-goal tracking: uses _goal_evals dict keyed by goal_id
            # for multi-goal support (each goal has its own prev eval).
            _goal_score: float | None = None
            _goal_delta: float | None = None
            _goal_confidence: float | None = None
            _goal_progress_signal: float = 0.0
            if self._goal_state is not None:
                try:
                    from umh.runtime_engine.goal_evaluator import GoalEvaluator

                    _ge = GoalEvaluator()
                    _gid = getattr(self._goal_state, "goal_id", None)
                    _prev_for_goal = (
                        self._goal_evals.get(_gid) if _gid else self._goal_eval_current
                    )
                    _goal_eval = _ge.evaluate(trace, self._goal_state, _prev_for_goal)
                    self._goal_eval_prev = self._goal_eval_current
                    self._goal_eval_current = _goal_eval
                    if _gid:
                        self._goal_prev_evals[_gid] = self._goal_evals.get(_gid)
                        self._goal_evals[_gid] = _goal_eval
                    _goal_score = _goal_eval.goal_score
                    _goal_delta = _goal_eval.delta
                    _goal_confidence = _goal_eval.confidence
                    _goal_progress_signal = _goal_eval.delta

                    # Update per-goal trackers in registry.
                    # With blending: distribute partial credit proportional
                    # to each goal's blend weight. Primary goal gets full
                    # delta; secondary goals get weighted delta.
                    # Without blending: identical to previous behavior.
                    if self._goal_registry is not None and _gid:
                        if self._blended_goal_state is not None and getattr(
                            self._blended_goal_state, "goals", ()
                        ):
                            for _bgid, _bw in self._blended_goal_state.goals:
                                _btracker = self._goal_registry.get_tracker(_bgid)
                                if _btracker is not None:
                                    _btracker.update_success(_goal_score * _bw)
                                    _btracker.record_delta(
                                        _goal_delta * (1.0 if _bgid == _gid else _bw)
                                    )
                        else:
                            _tracker = self._goal_registry.get_tracker(_gid)
                            if _tracker is not None:
                                _tracker.update_success(_goal_score)
                                _tracker.record_delta(_goal_delta)

                        if self._persist_memory and hasattr(
                            self._goal_registry, "persist_trackers"
                        ):
                            self._goal_registry.persist_trackers()

                    enriched = build_trace(
                        turn_id=trace.turn_id,
                        evaluation=evaluation,
                        signals=signals,
                        result=result,
                        directives=list(trace.directives_applied),
                        control_decision=getattr(trace, "control_decision", None),
                        thresholds_used=thresholds_dict,
                        strategy_selection=_strat_sel,
                        synthesized_strategy=_synth_strategy,
                        synthesis_reason=_synth_reason,
                        goal_mode=_resolved_mode_str,
                        convergence_status=_conv_status,
                        convergence_reason=_conv_reason,
                        convergence_action=_conv_action,
                        goal_score=_goal_score,
                        goal_delta=_goal_delta,
                        goal_confidence=_goal_confidence,
                    )
                    self.stats.decision_traces[-1] = enriched
                    trace = enriched
                except Exception as e:
                    _log.debug("Goal evaluation skipped: %s", e)

            # Plan step attribution: record outcome using per-goal eval.
            # Fallback priority: direct → active_goal → blended → neutral.
            _plan_step_attribution_source: str | None = None
            _plan_step_status: str | None = None
            _plan_step_retry_count: int | None = None
            _plan_step_failure_streak: int | None = None
            if _plan_active_id is not None and _plan_active_step is not None:
                try:
                    from umh.planning.hierarchical_planning import get_plan_engine

                    _pe_attr = get_plan_engine()
                    _step_score: float | None = None
                    _step_goal_id = _plan_active_step
                    _attr_source = "fallback"

                    # Priority 1: direct eval for step's goal_id
                    _step_eval = self._goal_evals.get(_step_goal_id)
                    if _step_eval is not None:
                        _step_score = getattr(_step_eval, "goal_score", None)
                        if _step_score is not None:
                            _attr_source = "direct"

                    # Priority 2: active goal score if aligned
                    if _step_score is None:
                        if _step_goal_id == getattr(self._goal_state, "goal_id", None):
                            _step_score = _goal_score
                            if _step_score is not None:
                                _attr_source = "active_goal"

                    # Priority 3: blended score weighted by similarity
                    if _step_score is None and self._blended_goal_state is not None:
                        _blend_goals = getattr(self._blended_goal_state, "goals", ())
                        if _blend_goals and _goal_score is not None:
                            _total_w = 0.0
                            _weighted_score = 0.0
                            for _bgid, _bw in _blend_goals:
                                _bg_eval = self._goal_evals.get(_bgid)
                                if _bg_eval is not None:
                                    _bg_score = getattr(_bg_eval, "goal_score", None)
                                    if _bg_score is not None:
                                        _weighted_score += _bg_score * _bw
                                        _total_w += _bw
                            if _total_w > 0:
                                _step_score = _weighted_score / _total_w
                                _attr_source = "blended"

                    # Priority 4: neutral fallback (no decay, no guess)
                    if _step_score is None:
                        _step_score = 0.0
                        _attr_source = "fallback"

                    _pe_attr.record_step_outcome(
                        _plan_active_id,
                        _step_goal_id,
                        _step_score,
                        current_turn=self.stats.turns,
                    )
                    _plan_step_goal_id = _step_goal_id
                    _plan_step_attributed_score = _step_score
                    _plan_step_attribution_source = _attr_source

                    # Capture recovery state for observability
                    _p_progress = _pe_attr.get_progress(_plan_active_id)
                    if _p_progress is not None:
                        _plan_confidence = _p_progress.confidence
                        _rec = _p_progress.step_recovery.get(_step_goal_id)
                        if _rec is not None:
                            _plan_step_status = _rec.status
                            _plan_step_retry_count = _rec.retry_count
                            _plan_step_failure_streak = _rec.failure_streak
                except Exception as e:
                    _log.debug("Plan step attribution skipped: %s", e)

            # Plan evolution: mutation + recombination after attribution.
            _plan_mutation_applied: bool | None = None
            _plan_mutation_type: str | None = None
            _mutated_plan_id: str | None = None
            _mutated_from_plan_id: str | None = None
            _plan_recombination_applied: bool | None = None
            _recombined_plan_id: str | None = None
            _recombined_from_plan_ids: "tuple[str, ...] | None" = None
            _plan_evolution_reason: str | None = None
            _plan_origin_snapshot: dict | None = None
            if self._goal_registry is not None:
                try:
                    from umh.planning.plan_mutation import get_plan_mutation_engine
                    from umh.planning.hierarchical_planning import get_plan_engine

                    _pe_evo = get_plan_engine()
                    _pm_engine = get_plan_mutation_engine()
                    _evo_result = _pm_engine.evaluate(
                        _pe_evo,
                        self._goal_registry,
                        self.stats.turns,
                    )

                    _origins: dict[str, str] = {}
                    _reasons: list[str] = []

                    if (
                        _evo_result.has_mutation
                        and _evo_result.mutated_plan is not None
                    ):
                        if _pe_evo.register_evolved_plan(_evo_result.mutated_plan):
                            _plan_mutation_applied = True
                            _plan_mutation_type = _evo_result.mutation.mutation_type
                            _mutated_plan_id = _evo_result.mutation.mutated_plan_id
                            _mutated_from_plan_id = _evo_result.mutation.parent_plan_id
                            _reasons.append(_evo_result.mutation.mutation_reason)
                            _origins[_evo_result.mutation.mutated_plan_id] = (
                                _evo_result.mutated_plan.origin
                            )
                            _plan_count = _pe_evo.plan_count

                    if (
                        _evo_result.has_recombination
                        and _evo_result.recombined_plan is not None
                    ):
                        if _pe_evo.register_evolved_plan(_evo_result.recombined_plan):
                            _plan_recombination_applied = True
                            _recombined_plan_id = (
                                _evo_result.recombination.recombined_plan_id
                            )
                            _recombined_from_plan_ids = (
                                _evo_result.recombination.parent_plan_ids
                            )
                            _reasons.append(
                                _evo_result.recombination.recombination_reason
                            )
                            _origins[_evo_result.recombination.recombined_plan_id] = (
                                _evo_result.recombined_plan.origin
                            )
                            _plan_count = _pe_evo.plan_count

                    if _origins:
                        _plan_origin_snapshot = _origins
                    if _reasons:
                        _plan_evolution_reason = "|".join(_reasons)
                except Exception as e:
                    _log.debug("Plan evolution skipped: %s", e)

            # Meta-goal generation: evaluate whether to create/mutate/retire
            # goals based on tracker performance and trace history.
            # Validation gate: generated goals pass through GoalValidator
            # before entering GoalRegistry. Rejected goals are tracked.
            _generated_goals_dicts: "tuple[dict, ...] | None" = None
            _goal_mutations_dicts: "tuple[dict, ...] | None" = None
            _meta_goal_reason: str | None = None
            _goal_validation_results: "tuple[dict, ...] | None" = None
            _rejected_goals: "tuple[str, ...] | None" = None
            _validation_reason: str | None = None
            _goal_alignment_scores: dict | None = None
            _alignment_penalties: "tuple[str, ...] | None" = None
            _alignment_decisions: "tuple[dict, ...] | None" = None
            _cf_expected_utility: dict | None = None
            _cf_confidence: dict | None = None
            _cf_reasoning: dict | None = None
            _cf_uncertainty: dict | None = None
            _cf_exploration_boost: dict | None = None
            _cf_horizon_value: dict | None = None
            _cf_horizon_reason: dict | None = None
            if self._goal_registry is not None:
                try:
                    from umh.goals.meta_goal import MetaGoalEngine

                    if self._meta_goal_engine is None:
                        self._meta_goal_engine = MetaGoalEngine()

                    _mg_result = self._meta_goal_engine.evaluate(
                        registry=self._goal_registry,
                        traces=self.stats.decision_traces,
                        current_turn=self.stats.turns,
                    )

                    if _mg_result.has_changes:
                        _val_results: list[dict] = []
                        _rej_goals: list[str] = []
                        _val_reasons: list[str] = []

                        from umh.runtime_engine.goal_validator import GoalValidator
                        from umh.runtime_engine.goal_alignment import GoalAlignmentEvaluator
                        from umh.reasoning.counterfactual_eval import CounterfactualEvaluator

                        _validator = GoalValidator()
                        _cf_eval = CounterfactualEvaluator()
                        _aligner = GoalAlignmentEvaluator()
                        _align_scores: dict[str, float] = {}
                        _align_penalties: list[str] = []
                        _align_decisions: list[dict] = []
                        _cf_utilities: dict[str, float] = {}
                        _cf_confs: dict[str, float] = {}
                        _cf_reasons: dict[str, str] = {}
                        _cf_uncertainties: dict[str, float] = {}
                        _cf_boosts: dict[str, float] = {}
                        _cf_horizons: dict[str, float] = {}
                        _cf_horizon_reasons: dict[str, str] = {}
                        _cf_commitments: dict[str, float] = {}

                        for _mg in _mg_result.generated:
                            self._meta_goal_engine.register_generated(_mg)
                            if self._meta_goal_engine.activate_candidate(_mg.goal_id):
                                _activated = self._meta_goal_engine.get_generated(
                                    _mg.goal_id
                                )
                                _vr = _validator.validate(
                                    _activated,
                                    self._goal_registry,
                                    self.stats.decision_traces,
                                )
                                _val_results.append(_vr.to_dict())

                                if _vr.is_valid:
                                    _use_mg = (
                                        _vr.corrected_goal
                                        if _vr.corrected_goal is not None
                                        else _activated
                                    )

                                    _cfr = _cf_eval.evaluate_counterfactual(
                                        _use_mg,
                                        self._goal_registry,
                                        self.stats.decision_traces,
                                    )
                                    _cf_utilities[_mg.goal_id] = _cfr.expected_utility
                                    _cf_confs[_mg.goal_id] = _cfr.confidence
                                    _cf_reasons[_mg.goal_id] = _cfr.reasoning
                                    _cf_uncertainties[_mg.goal_id] = _cfr.uncertainty
                                    _cf_boosts[_mg.goal_id] = _cfr.exploration_boost
                                    _cf_horizons[_mg.goal_id] = _cfr.horizon_value
                                    if _cfr.horizon_reason:
                                        _cf_horizon_reasons[_mg.goal_id] = (
                                            _cfr.horizon_reason
                                        )
                                    _cf_commitments[_mg.goal_id] = _cfr.commitment_bonus

                                    _cf_adjusted_mg = _use_mg
                                    if _cfr.confidence > 0.2:
                                        _new_conf = (
                                            _use_mg.confidence * _cfr.effective_utility
                                        )
                                        _new_conf = max(_new_conf, 0.05)
                                        from umh.goals.meta_goal import MetaGoal as _MG

                                        _cf_adjusted_mg = _MG(
                                            goal_id=_use_mg.goal_id,
                                            origin=_use_mg.origin,
                                            parent_goals=_use_mg.parent_goals,
                                            confidence=_new_conf,
                                            utility_estimate=_use_mg.utility_estimate,
                                            lifecycle_state=_use_mg.lifecycle_state,
                                            description=_use_mg.description,
                                            success_criteria=_use_mg.success_criteria,
                                            priority=_use_mg.priority,
                                            generation_turn=_use_mg.generation_turn,
                                            generation_reason=_use_mg.generation_reason,
                                        )

                                    _ar = _aligner.evaluate_alignment(
                                        _cf_adjusted_mg,
                                        self._goal_registry,
                                        self.stats.decision_traces,
                                    )
                                    _align_scores[_mg.goal_id] = _ar.alignment_score
                                    _align_penalties.extend(_ar.penalties)
                                    _align_decisions.append(_ar.to_dict())

                                    if _ar.allowed:
                                        _gs = self._meta_goal_engine.to_meta_goal_state(
                                            _cf_adjusted_mg
                                        )
                                        if (
                                            _ar.adjusted_priority
                                            != _cf_adjusted_mg.priority
                                        ):
                                            from umh.goals.state import GoalState

                                            _gs = GoalState(
                                                goal_id=_gs.goal_id,
                                                description=_gs.description,
                                                success_criteria=_gs.success_criteria,
                                                priority=_ar.adjusted_priority,
                                                active=_gs.active,
                                            )
                                        self._goal_registry.add_goal(_gs)
                                        if _vr.severity == "auto-fix":
                                            _val_reasons.append("auto-fix")
                                    else:
                                        _rej_goals.append(_mg.goal_id)
                                        _val_reasons.append("alignment-rejected")
                                else:
                                    _rej_goals.append(_mg.goal_id)
                                    _val_reasons.append("rejected")

                        for _rid in _mg_result.retired:
                            self._goal_registry.remove_goal(_rid)

                        _generated_goals_dicts = tuple(
                            g.to_dict() for g in _mg_result.generated
                        )
                        _goal_mutations_dicts = tuple(
                            m.to_dict() for m in _mg_result.mutations
                        )
                        _meta_goal_reason = _mg_result.reason

                        if _val_results:
                            _goal_validation_results = tuple(_val_results)
                        if _rej_goals:
                            _rejected_goals = tuple(_rej_goals)
                        if _val_reasons:
                            _validation_reason = "_".join(_val_reasons)
                        if _align_scores:
                            _goal_alignment_scores = _align_scores
                        if _align_penalties:
                            _alignment_penalties = tuple(_align_penalties)
                        if _align_decisions:
                            _alignment_decisions = tuple(_align_decisions)
                        if _cf_utilities:
                            _cf_expected_utility = _cf_utilities
                        if _cf_confs:
                            _cf_confidence = _cf_confs
                        if _cf_reasons:
                            _cf_reasoning = _cf_reasons
                        if _cf_uncertainties:
                            _cf_uncertainty = _cf_uncertainties
                        if _cf_boosts:
                            _cf_exploration_boost = _cf_boosts
                        if _cf_horizons:
                            _cf_horizon_value = _cf_horizons
                        if _cf_horizon_reasons:
                            _cf_horizon_reason = _cf_horizon_reasons
                        if _cf_commitments:
                            _commitment_bonuses = _cf_commitments

                    # Collect persistence streaks from all trackers
                    _all_trackers = self._goal_registry.get_all_trackers()
                    if _all_trackers:
                        _streaks = {
                            gid: round(t.persistence_streak, 4)
                            for gid, t in _all_trackers.items()
                            if t.persistence_streak > 0
                        }
                        if _streaks:
                            _persistence_streaks = _streaks

                    if (
                        _goal_score is not None
                        and _active_goal_id
                        and self._meta_goal_engine.is_generated(_active_goal_id)
                    ):
                        self._meta_goal_engine.update_confidence(
                            _active_goal_id,
                            _goal_score,
                            convergence_stable=(_conv_status == "stable"),
                        )
                except Exception as e:
                    _log.debug("Meta-goal evaluation skipped: %s", e)

            # Build goal_delta history from recent traces for sustained-
            # positive detection. Includes current delta if available.
            _goal_delta_history: list[float] = []
            for _ht in self.stats.decision_traces:
                _hd = getattr(_ht, "goal_delta", None)
                if _hd is not None:
                    _goal_delta_history.append(_hd)

            # Causal credit: multi-horizon credit assignment across layers.
            # Runs AFTER all attribution/evolution, BEFORE trace enrichment.
            _causal_credit_dict: dict | None = None
            _immediate_credit: dict | None = None
            _delayed_credit: dict | None = None
            _structural_credit: dict | None = None
            _credit_reason: str | None = None
            _credited_entities: dict | None = None
            try:
                from umh.reasoning.causal_credit import (
                    compute_credit_snapshot,
                    get_delayed_credit_buffer,
                    apply_weighted_credit_to_strategy,
                    apply_weighted_credit_to_goal,
                    apply_weighted_credit_to_plan,
                )

                _recent = (
                    list(self.stats.decision_traces[:-1])
                    if len(self.stats.decision_traces) > 1
                    else []
                )
                _cc_snap = compute_credit_snapshot(trace, self.stats.turns, _recent)

                if _cc_snap.allocation.components:
                    _causal_credit_dict = _cc_snap.allocation.to_dict()
                    if _cc_snap.immediate:
                        _immediate_credit = {
                            k: round(v, 4) for k, v in _cc_snap.immediate.items()
                        }
                    if _cc_snap.delayed:
                        _delayed_credit = {
                            k: round(v, 4) for k, v in _cc_snap.delayed.items()
                        }
                    if _cc_snap.structural:
                        _structural_credit = {
                            k: round(v, 4) for k, v in _cc_snap.structural.items()
                        }
                    _credit_reason = _cc_snap.credit_reason
                    if _cc_snap.credited_entities:
                        _credited_entities = _cc_snap.credited_entities

                    # Weighted memory application
                    _sel_strat = getattr(trace, "selected_strategy", "")
                    _q_score = getattr(trace, "quality_score", 0.0)
                    _strat_w = _cc_snap.allocation.weight_for("strategy")
                    if _sel_strat and _strat_w > 0:
                        apply_weighted_credit_to_strategy(
                            _sel_strat, _q_score, _strat_w
                        )

                    _g_w = _cc_snap.allocation.weight_for("goal")
                    if _active_goal_id and _goal_score is not None and _g_w > 0:
                        apply_weighted_credit_to_goal(
                            _active_goal_id, _goal_score, _g_w, self._goal_registry
                        )

                    _step_w = _cc_snap.allocation.weight_for("step")
                    _plan_w = _cc_snap.allocation.weight_for("plan")
                    if _plan_active_id and _plan_step_goal_id:
                        apply_weighted_credit_to_plan(
                            _plan_active_id, _plan_step_goal_id, _step_w, _plan_w
                        )

                    # Delayed credit buffer: record enabling contributions
                    _dc_buf = get_delayed_credit_buffer()
                    _dc_buf.expire(self.stats.turns)
                    if _step_w > 0.1 and _plan_step_goal_id:
                        _dc_buf.add(
                            self.stats.turns,
                            "step",
                            _step_w,
                            f"step:{_plan_step_goal_id}",
                        )
                    if _plan_w > 0.1 and _plan_active_id:
                        _dc_buf.add(
                            self.stats.turns,
                            "plan",
                            _plan_w,
                            f"plan:{_plan_active_id}",
                        )

                    # Resolve pending delayed credits if current turn succeeded
                    if _goal_score is not None and _goal_score > 0.3:
                        _resolved = _dc_buf.resolve(self.stats.turns, _goal_score)
                        for _rc in _resolved:
                            if _rc.contributor == "step":
                                apply_weighted_credit_to_plan(
                                    _plan_active_id or "",
                                    _rc.entity.replace("step:", ""),
                                    _rc.credit_weight * 0.5,
                                    0.0,
                                )
                            elif _rc.contributor == "plan":
                                apply_weighted_credit_to_plan(
                                    _rc.entity.replace("plan:", ""),
                                    "",
                                    0.0,
                                    _rc.credit_weight * 0.5,
                                )
            except Exception as e:
                _log.debug("Causal credit computation skipped: %s", e)

            # World-state reinforcement: update cluster quality from causal credit.
            _ws_cluster_quality: float | None = None
            _learned_state_bias: dict | None = None
            _combined_state_bias: dict | None = None
            _cluster_quality_ema: float | None = None
            _cluster_obs_count: int | None = None
            _ws_reinforcement_applied: bool | None = None
            try:
                if (
                    _world_state_cluster
                    and _causal_credit_dict is not None
                    and _goal_score is not None
                ):
                    from umh.world.state import get_world_state_engine

                    _ws_reinf = get_world_state_engine()

                    _ws_credit_w = 0.0
                    if _cc_snap and _cc_snap.allocation.components:
                        _ws_credit_w = _cc_snap.allocation.weight_for("world_state")

                    if _ws_credit_w > 0.01:
                        _ws_reinforcement_applied = _ws_reinf.reinforce_cluster(
                            _world_state_cluster,
                            _ws_credit_w,
                            _goal_score,
                            self.stats.turns,
                        )

                    _reinf_cluster = _ws_reinf.get_cluster(_world_state_cluster)
                    if _reinf_cluster is not None:
                        _cluster_quality_ema = _reinf_cluster.performance.quality_ema
                        _cluster_obs_count = (
                            _reinf_cluster.performance.observation_count
                        )
                        _ws_cluster_quality = _cluster_quality_ema

                    if _ws_reinf.current_state is not None:
                        _lsb = _ws_reinf.get_learned_state_bias(_ws_reinf.current_state)
                        if _lsb:
                            _learned_state_bias = {
                                k: round(v, 4) for k, v in _lsb.items()
                            }
                            _combined = (
                                dict(_conditioning_bias_dict.get("strategy_bias", {}))
                                if _conditioning_bias_dict
                                else {}
                            )
                            for k, v in _lsb.items():
                                _combined[k] = _combined.get(k, 0.0) + v
                            _combined_state_bias = {
                                k: round(v, 4) for k, v in _combined.items()
                            }

                            if _strategy_conditioned_scores is not None:
                                for k, v in _lsb.items():
                                    if k in _strategy_conditioned_scores:
                                        _strategy_conditioned_scores[k] = round(
                                            _strategy_conditioned_scores[k] + v, 4
                                        )
            except Exception as e:
                _log.debug("World-state reinforcement skipped: %s", e)

            # Influence scoring: compose all signals into a single score.
            _influence_components: tuple | None = None
            _influence_weights: dict | None = None
            _final_influence_score: float | None = None
            _influence_breakdown: dict | None = None
            _influence_pre_score: float | None = None
            _influence_post_score: float | None = None
            _meta_weights: dict | None = None
            _meta_weight_adjustments: dict | None = None
            _meta_weight_signal_performance: dict | None = None
            _meta_signal_strength: float | None = None
            try:
                from umh.reasoning.influence_scoring import (
                    BASE_WEIGHTS,
                    build_influence_snapshot,
                    compute_influence_score,
                )

                _credit_total = None
                if _cc_snap and _cc_snap.allocation.total_signal > 0:
                    _credit_total = _cc_snap.allocation.total_signal

                _inf_snap = build_influence_snapshot(
                    goal_score=_goal_score,
                    plan_confidence=_plan_confidence,
                    strategy_score=getattr(trace, "quality_score", None),
                    conditioning_bias=_conditioning_bias_dict,
                    learned_state_bias=_learned_state_bias,
                    credit_total_signal=_credit_total,
                    exploration_rate=_exploration_rate,
                    commitment_bonuses=_commitment_bonuses,
                    persistence_streaks=_persistence_streaks,
                )

                # Meta-weight adaptation: get adapted weights if enough data
                _adapted_ws: dict[str, float] | None = None
                try:
                    from umh.reasoning.meta_weight_engine import get_meta_weight_engine

                    _mw_engine = get_meta_weight_engine()
                    _mw_result = _mw_engine.get_adapted_weights(BASE_WEIGHTS)
                    if _mw_result.adapted:
                        _adapted_ws = _mw_result.adapted_weights
                    _meta_weights = _mw_result.adapted_weights or None
                    _meta_weight_adjustments = _mw_result.adjustments or None
                    _meta_weight_signal_performance = (
                        _mw_result.signal_performance or None
                    )
                    _mss = _mw_engine.compute_meta_signal_strength()
                    if _mss > 0.0:
                        _meta_signal_strength = round(_mss, 6)
                except Exception as _mw_err:
                    _log.debug("Meta-weight adaptation skipped: %s", _mw_err)

                _inf_result = compute_influence_score(
                    _inf_snap, adapted_weights=_adapted_ws
                )
                _final_influence_score = _inf_result.final_score
                _influence_components = tuple(
                    c.to_dict() for c in _inf_result.components
                )
                _influence_weights = _inf_result.weights
                _influence_breakdown = {
                    c.name: round(c.contribution, 4) for c in _inf_result.components
                }

                # Record pre/post observability from prior influence applied
                if _influence_applied and _influence_adjustment is not None:
                    _q = getattr(trace, "quality_score", 0.0)
                    _influence_pre_score = _q
                    _influence_post_score = round(_q + _influence_adjustment, 4)

                # Plan influence: additive nudge to plan confidence
                if _plan_confidence is not None and _prior_influence_score > 0:
                    from umh.reasoning.influence_scoring import compute_plan_influence

                    _plan_inf = compute_plan_influence(_prior_influence_score)
                    if _plan_inf > 0:
                        _plan_confidence = min(1.0, _plan_confidence + _plan_inf)

                # Meta-weight outcome recording: feed signal values + quality
                try:
                    from umh.reasoning.meta_weight_engine import get_meta_weight_engine

                    _mw_rec = get_meta_weight_engine()
                    _signal_vals = {c.name: c.value for c in _inf_result.components}
                    _quality = getattr(trace, "quality_score", 0.0)
                    _mw_rec.record_outcome(_signal_vals, _quality)
                except Exception as _mw_rec_err:
                    _log.debug("Meta-weight recording skipped: %s", _mw_rec_err)
            except Exception as e:
                _log.debug("Influence scoring skipped: %s", e)

            # Analytics adapter: build signal from previous turn's analytics.
            _analytics_signal_dict: dict | None = None
            _analytics_applied: bool | None = None
            _analytics_obj: object | None = None
            try:
                from umh.runtime_engine.analytics_adapter import build_analytics_signal

                _prev_analytics: dict | None = None
                if self.stats.decision_traces:
                    _prev_analytics = getattr(
                        self.stats.decision_traces[-1],
                        "fabric_analytics_summary",
                        None,
                    )
                _analytics_obj = build_analytics_signal(_prev_analytics)
                if getattr(_analytics_obj, "is_active", False):
                    _analytics_signal_dict = _analytics_obj.to_dict()
                    _analytics_applied = True
                else:
                    _analytics_applied = False
            except Exception as _aa_err:
                _log.debug("Analytics adapter skipped: %s", _aa_err)

            # Objective optimizer: compute trajectory-based adjustments.
            _objective_trend: str | None = None
            _optimization_signal_dict: dict | None = None
            _opt_exploration_adj: float = 0.0
            _opt_confidence_adj: float = 0.0
            try:
                from umh.runtime_engine.objective_optimizer import compute_optimization_signal

                _opt_signal = compute_optimization_signal(self._objective_history)
                if _opt_signal.is_active:
                    _objective_trend = _opt_signal.trend.value
                    _optimization_signal_dict = _opt_signal.to_dict()
                    _opt_exploration_adj = _opt_signal.exploration_adjustment
                    _opt_confidence_adj = _opt_signal.confidence_adjustment

                    if _exploration_rate is not None:
                        _exploration_rate = max(
                            0.0,
                            min(1.0, _exploration_rate + _opt_exploration_adj),
                        )
                    if _plan_confidence is not None:
                        _plan_confidence = max(
                            0.0,
                            min(1.0, _plan_confidence + _opt_confidence_adj),
                        )
                else:
                    _objective_trend = _opt_signal.trend.value
            except Exception as _opt_err:
                _log.debug("Objective optimizer skipped: %s", _opt_err)

            # Context disambiguation: classify environment state.
            _context_signal_dict: dict | None = None
            _context_type: str | None = None
            _ctx_signal = None
            try:
                from umh.reasoning.context_engine import (
                    ContextClassifier,
                    NO_CONTEXT_SIGNAL,
                )

                if self._context_classifier is None:
                    self._context_classifier = ContextClassifier()

                _ctx_actions: list[str] = []
                _ctx_rewards: list[float] = []
                for _ct in self.stats.decision_traces:
                    _ca = getattr(_ct, "selected_strategy", None)
                    _cr = getattr(_ct, "quality_score", None)
                    if _ca is not None:
                        _ctx_actions.append(_ca)
                        _ctx_rewards.append(_cr if _cr is not None else 0.0)

                _ctx_signal = self._context_classifier.classify(
                    _ctx_actions, _ctx_rewards
                )
                if _ctx_signal is not NO_CONTEXT_SIGNAL:
                    _context_signal_dict = _ctx_signal.to_dict()
                    _context_type = _ctx_signal.dominant_type
            except Exception as _ctx_err:
                _log.debug("Context engine skipped: %s", _ctx_err)

            # Meta-generalization: cross-scenario transfer priors.
            _mg_matched: bool | None = None
            _mg_prototype_id: int | None = None
            _mg_similarity: float | None = None
            _mg_priors: dict | None = None
            _mg_signature: dict | None = None
            _mg_prototype_usage: int | None = None
            _mg_prototype_avg_reward: float | None = None
            _mg_suppressed: bool | None = None
            try:
                from umh.reasoning.meta_generalization import (
                    MetaGeneralizationEngine,
                    apply_confidence_prior,
                    apply_strategy_priors,
                )

                if self._meta_gen is None:
                    self._meta_gen = MetaGeneralizationEngine()

                _mg_actions: list[str] = []
                _mg_rewards: list[float] = []
                for _mt in self.stats.decision_traces:
                    _ma = getattr(_mt, "selected_strategy", None)
                    _mr = getattr(_mt, "quality_score", None)
                    if _ma is not None:
                        _mg_actions.append(_ma)
                        _mg_rewards.append(_mr if _mr is not None else 0.0)

                _mg_result = self._meta_gen.classify(_mg_actions, _mg_rewards)
                _mg_matched = _mg_result.matched
                if _mg_result.matched:
                    _mg_prototype_id = _mg_result.prototype_id
                    _mg_similarity = _mg_result.similarity
                    _mg_priors = _mg_result.priors if _mg_result.priors else None
                    _mg_signature = (
                        _mg_result.signature.to_dict() if _mg_result.signature else None
                    )
                    _mg_prototype_usage = _mg_result.prototype_usage_count
                    _mg_prototype_avg_reward = _mg_result.prototype_avg_reward

                    _is_stable = (
                        _ctx_signal is not None
                        and getattr(_ctx_signal, "dominant_type", None) == "stable"
                    )
                    if _is_stable:
                        _mg_suppressed = False
                        if _strategy_conditioned_scores and isinstance(
                            _strategy_conditioned_scores, dict
                        ):
                            _strategy_conditioned_scores = apply_strategy_priors(
                                _strategy_conditioned_scores, _mg_result
                            )
                        _plan_confidence = apply_confidence_prior(
                            _plan_confidence, _mg_result
                        )
                    else:
                        _mg_suppressed = True
            except Exception as _mg_err:
                _log.debug("Meta-generalization skipped: %s", _mg_err)

            # Causal transition memory: empirical action→outcome biases.
            _causal_signal_dict: dict | None = None
            _causal_confidence: float | None = None
            _causal_applied: bool | None = None
            _causal_context_match: str | None = None
            try:
                from umh.reasoning.causal_memory import (
                    CausalMemoryEngine,
                    apply_causal_bias,
                )

                if self._causal_mem is None:
                    self._causal_mem = CausalMemoryEngine()

                _causal_ctx = _context_type or "unknown"
                _causal_signal = self._causal_mem.compute_signal(
                    _causal_ctx,
                    available_actions=(
                        list(_strategy_conditioned_scores.keys())
                        if _strategy_conditioned_scores
                        and isinstance(_strategy_conditioned_scores, dict)
                        else None
                    ),
                )

                if _causal_signal.action_bias:
                    _causal_signal_dict = _causal_signal.to_dict()
                    _causal_confidence = _causal_signal.confidence
                    _causal_context_match = _causal_signal.matched_context

                    _is_stable_for_causal = _causal_ctx == "stable"
                    if (
                        _is_stable_for_causal
                        and _strategy_conditioned_scores
                        and isinstance(_strategy_conditioned_scores, dict)
                    ):
                        _strategy_conditioned_scores = apply_causal_bias(
                            _strategy_conditioned_scores, _causal_signal
                        )
                        _causal_applied = True
                    else:
                        _causal_applied = False
                else:
                    _causal_applied = False
            except Exception as _cm_err:
                _log.debug("Causal memory skipped: %s", _cm_err)

            # Temporal credit assignment: delayed outcome attribution.
            _credit_signal_dict: dict | None = None
            _credit_confidence: float | None = None
            _credit_applied: bool | None = None
            _credit_horizon: int | None = None
            try:
                from umh.reasoning.credit_assignment import (
                    CreditAssignmentEngine,
                    apply_credit_adjustment,
                )

                if self._credit_eng is None:
                    self._credit_eng = CreditAssignmentEngine()

                _credit_sig = self._credit_eng.compute_signal(
                    available_actions=(
                        list(_strategy_conditioned_scores.keys())
                        if _strategy_conditioned_scores
                        and isinstance(_strategy_conditioned_scores, dict)
                        else None
                    ),
                )

                if _credit_sig.action_credit:
                    _credit_signal_dict = _credit_sig.to_dict()
                    _credit_confidence = _credit_sig.confidence
                    _credit_horizon = _credit_sig.horizon

                    _is_stable_for_credit = (_context_type or "unknown") == "stable"
                    if (
                        _is_stable_for_credit
                        and _strategy_conditioned_scores
                        and isinstance(_strategy_conditioned_scores, dict)
                    ):
                        _strategy_conditioned_scores = apply_credit_adjustment(
                            _strategy_conditioned_scores, _credit_sig
                        )
                        _credit_applied = True
                    else:
                        _credit_applied = False
                else:
                    _credit_applied = False
            except Exception as _ca_err:
                _log.debug("Credit assignment skipped: %s", _ca_err)

            # Forward rollout foresight: shallow trajectory simulation.
            _foresight_signal_dict: dict | None = None
            _foresight_confidence: float | None = None
            _foresight_applied: bool | None = None
            _foresight_depth: int | None = None
            try:
                from umh.policy.foresight_engine import (
                    ForesightEngine,
                    apply_foresight_bias,
                    extract_causal_stats,
                    extract_credit_accumulators,
                )

                _foresight_eng = ForesightEngine()
                _foresight_ctx = _context_type or "unknown"

                _fs_causal_stats = extract_causal_stats(self._causal_mem)
                _fs_credit_accs = extract_credit_accumulators(self._credit_eng)

                _foresight_sig = _foresight_eng.compute_signal(
                    available_actions=(
                        list(_strategy_conditioned_scores.keys())
                        if _strategy_conditioned_scores
                        and isinstance(_strategy_conditioned_scores, dict)
                        else []
                    ),
                    context=_foresight_ctx,
                    causal_stats=_fs_causal_stats,
                    credit_accumulators=_fs_credit_accs,
                )

                if _foresight_sig.action_bias:
                    _foresight_signal_dict = _foresight_sig.to_dict()
                    _foresight_confidence = _foresight_sig.confidence
                    _foresight_depth = _foresight_sig.horizon

                    _is_stable_for_foresight = _foresight_ctx == "stable"
                    if (
                        _is_stable_for_foresight
                        and _strategy_conditioned_scores
                        and isinstance(_strategy_conditioned_scores, dict)
                    ):
                        _strategy_conditioned_scores = apply_foresight_bias(
                            _strategy_conditioned_scores, _foresight_sig
                        )
                        _foresight_applied = True
                    else:
                        _foresight_applied = False
                else:
                    _foresight_applied = False
            except Exception as _fs_err:
                _log.debug("Foresight engine skipped: %s", _fs_err)

            # Action planner: multi-trajectory forward evaluation.
            _planner_active: bool | None = None
            _planner_scores: dict | None = None
            _planner_choice: str | None = None
            _planner_confidence: float | None = None
            _planner_reason: str | None = None
            _planner_horizon: int | None = None
            _planner_uncertainty: float | None = None
            _planner_consistency: float | None = None
            _planner_adjusted_confidence: float | None = None
            try:
                from umh.runtime_engine.action_planner import (
                    apply_planner_override,
                    evaluate_trajectories,
                )

                _planner_ctx = _context_type or "unknown"
                _planner_actions = (
                    list(_strategy_conditioned_scores.keys())
                    if _strategy_conditioned_scores
                    and isinstance(_strategy_conditioned_scores, dict)
                    else []
                )

                _planner_result = evaluate_trajectories(
                    candidate_actions=_planner_actions,
                    context_type=_planner_ctx,
                    causal_stats=(
                        _fs_causal_stats if "_fs_causal_stats" in dir() else None
                    ),
                    credit_accumulators=(
                        _fs_credit_accs if "_fs_credit_accs" in dir() else None
                    ),
                    context_signal=_ctx_signal,
                    trap_signal_active=None,
                    stability_guard_active=None,
                    strategy_scores=_strategy_conditioned_scores,
                )

                _planner_active = _planner_result.active
                _planner_confidence = _planner_result.planner_confidence
                _planner_reason = _planner_result.reason
                _planner_horizon = _planner_result.horizon_used
                _planner_uncertainty = _planner_result.uncertainty
                _planner_consistency = _planner_result.consistency
                _planner_adjusted_confidence = _planner_result.adjusted_confidence

                if _planner_result.trajectory_scores:
                    _planner_scores = _planner_result.trajectory_scores

                if _planner_result.active and _planner_result.selected_action_override:
                    _planner_choice = _planner_result.selected_action_override
                    if _strategy_conditioned_scores and isinstance(
                        _strategy_conditioned_scores, dict
                    ):
                        _strategy_conditioned_scores = apply_planner_override(
                            _strategy_conditioned_scores, _planner_result
                        )
            except Exception as _planner_err:
                _log.debug("Action planner skipped: %s", _planner_err)

            # Trap recovery engine: detect high-confidence + low-reward traps.
            _trap_signal_active: bool | None = None
            _trap_adjustment: float | None = None
            try:
                from umh.runtime_engine.trap_recovery_engine import (
                    TrapDetector,
                    apply_trap_adjustments,
                )

                if self._trap_detector is None:
                    self._trap_detector = TrapDetector()

                _sel_strat_for_trap = ""
                _quality_for_trap = 0.0
                if self.stats.decision_traces:
                    _prev_t = self.stats.decision_traces[-1]
                    _sel_strat_for_trap = (
                        getattr(_prev_t, "selected_strategy", "") or ""
                    )
                    _quality_for_trap = getattr(_prev_t, "quality_score", 0.0) or 0.0

                if _sel_strat_for_trap:
                    self._trap_detector.observe(_sel_strat_for_trap, _quality_for_trap)

                if _strategy_conditioned_scores and isinstance(
                    _strategy_conditioned_scores, dict
                ):
                    _trap_signal = self._trap_detector.compute_signal(
                        _strategy_conditioned_scores
                    )
                    _trap_signal_active = _trap_signal.active
                    _trap_adjustment = (
                        _trap_signal.trap_adjustment if _trap_signal.active else None
                    )
                    if _trap_signal.active:
                        if _ctx_signal is not None:
                            from umh.reasoning.context_engine import gate_trap_adjustment
                            from umh.runtime_engine.trap_recovery_engine import TrapSignal

                            _gated = gate_trap_adjustment(
                                _trap_signal.trap_adjustment, _ctx_signal
                            )
                            _trap_signal = TrapSignal(
                                active=True,
                                dominant_action=_trap_signal.dominant_action,
                                trap_adjustment=_gated,
                                reward_mismatch=_trap_signal.reward_mismatch,
                                stagnation_length=_trap_signal.stagnation_length,
                                reason=_trap_signal.reason,
                            )
                            _trap_adjustment = _gated
                        _strategy_conditioned_scores = apply_trap_adjustments(
                            _strategy_conditioned_scores, _trap_signal
                        )
            except Exception as _trap_err:
                _log.debug("Trap recovery engine skipped: %s", _trap_err)

            # Exploration engine: deterministic strategy diversification.
            _det_exploration_active: bool | None = None
            _det_exploration_adjustments: dict | None = None
            try:
                from umh.analytics.exploration_engine import (
                    compute_exploration_signal,
                    apply_exploration_adjustments,
                )

                _explore_failure_streak = 0
                if _plan_step_failure_streak is not None:
                    _explore_failure_streak = _plan_step_failure_streak

                _gated_trend = _objective_trend
                if _ctx_signal is not None:
                    try:
                        from umh.reasoning.context_engine import (
                            gate_exploration_inputs,
                        )

                        _explore_failure_streak, _gated_trend = gate_exploration_inputs(
                            _explore_failure_streak,
                            _objective_trend,
                            [],
                            _ctx_signal,
                        )
                    except Exception:
                        pass

                _explore_signal = compute_exploration_signal(
                    plan_confidence=_plan_confidence,
                    objective_trend=_gated_trend,
                    failure_streak=_explore_failure_streak,
                    strategy_scores=_strategy_conditioned_scores,
                )
                if _explore_signal.exploration_active:
                    _det_exploration_active = True
                    _det_exploration_adjustments = _explore_signal.to_dict()
                    if _strategy_conditioned_scores and isinstance(
                        _strategy_conditioned_scores, dict
                    ):
                        _strategy_conditioned_scores = apply_exploration_adjustments(
                            _strategy_conditioned_scores,
                            _explore_signal,
                        )
                else:
                    _det_exploration_active = False
            except Exception as _explore_err:
                _log.debug("Exploration engine skipped: %s", _explore_err)

            # Stability guard: dampen thrashing without killing adaptation.
            _stability_guard_active: bool | None = None
            try:
                from umh.policy.stability_guard import compute_stability_signal

                _guard_actions: list[str] = []
                _guard_rewards: list[float] = []
                for _gt in self.stats.decision_traces:
                    _ga = getattr(_gt, "selected_strategy", None)
                    _gr = getattr(_gt, "quality_score", None)
                    if _ga is not None:
                        _guard_actions.append(_ga)
                        _guard_rewards.append(_gr if _gr is not None else 0.0)

                _stab_signal = compute_stability_signal(_guard_actions, _guard_rewards)
                _stability_guard_active = _stab_signal.active

                if _stab_signal.active:
                    _stab_explore_adj = _stab_signal.exploration_adjustment
                    _stab_conf_adj = _stab_signal.confidence_adjustment
                    if _ctx_signal is not None:
                        from umh.reasoning.context_engine import gate_stability_effect

                        _stab_explore_adj, _stab_conf_adj = gate_stability_effect(
                            _stab_explore_adj, _stab_conf_adj, _ctx_signal
                        )
                    if _exploration_rate is not None:
                        _exploration_rate = max(
                            0.0,
                            min(1.0, _exploration_rate + _stab_explore_adj),
                        )
                    if _plan_confidence is not None:
                        _plan_confidence = max(
                            0.0,
                            min(1.0, _plan_confidence + _stab_conf_adj),
                        )
            except Exception as _stab_err:
                _log.debug("Stability guard skipped: %s", _stab_err)

            # Signal orchestration: coordinate all adaptation signals.
            _orch_consensus: float | None = None
            _orch_active_count: int | None = None
            _orch_suppressed_count: int | None = None
            _orch_dominant_source: str | None = None
            try:
                from umh.analytics.signal_orchestrator import (
                    SignalBundle,
                    SignalOrchestrator,
                    apply_orchestrated_signal,
                )

                _orch_bundle = SignalBundle(
                    meta_signal=_meta_result if "_meta_result" in dir() else None,
                    context_signal=_ctx_signal,
                    causal_signal=(
                        _causal_signal
                        if "_causal_signal" in dir() and _causal_signal_dict is not None
                        else None
                    ),
                    credit_signal=(
                        _credit_sig
                        if "_credit_sig" in dir() and _credit_signal_dict is not None
                        else None
                    ),
                    foresight_signal=(
                        _foresight_sig
                        if "_foresight_sig" in dir()
                        and _foresight_signal_dict is not None
                        else None
                    ),
                    exploration_signal=(
                        _explore_signal
                        if "_explore_signal" in dir() and _det_exploration_active
                        else None
                    ),
                    trap_signal=(
                        _trap_signal
                        if "_trap_signal" in dir() and _trap_signal_active
                        else None
                    ),
                    stability_signal=(
                        _stab_signal
                        if "_stab_signal" in dir() and _stability_guard_active
                        else None
                    ),
                )
                _orch_signal = SignalOrchestrator().orchestrate(
                    _orch_bundle, strategy_scores=_strategy_conditioned_scores
                )
                _orch_consensus = _orch_signal.consensus_score
                _orch_active_count = len(_orch_signal.active_signals)
                _orch_suppressed_count = len(_orch_signal.suppressed_signals)
                _orch_dominant_source = _orch_signal.dominant_signal_source or None

                _is_stable_for_orch = (_context_type or "unknown") == "stable"
                if (
                    _is_stable_for_orch
                    and _orch_signal.combined_action_bias
                    and _strategy_conditioned_scores
                    and isinstance(_strategy_conditioned_scores, dict)
                ):
                    _strategy_conditioned_scores = apply_orchestrated_signal(
                        _strategy_conditioned_scores, _orch_signal
                    )
            except Exception as _orch_err:
                _log.debug("Signal orchestration skipped: %s", _orch_err)

            # Signal sensitivity: adaptive responsiveness to signal strength.
            _sensitivity_factor: float | None = None
            _sensitivity_reason: str | None = None
            _sensitivity_applied: bool | None = None
            try:
                from umh.runtime_engine.signal_sensitivity import (
                    apply_sensitivity as _apply_sens,
                    compute_sensitivity as _compute_sens,
                )

                if (
                    _orch_consensus is not None
                    and _orch_signal is not None
                    and _orch_signal.combined_action_bias
                ):
                    _sens_confidences = {
                        name: _orch_signal.total_confidence
                        for name in _orch_signal.active_signals
                    }
                    _sens_result = _compute_sens(
                        combined_action_bias=_orch_signal.combined_action_bias,
                        consensus_score=_orch_signal.consensus_score,
                        signal_confidences=_sens_confidences,
                        context_type=_context_type or "unknown",
                        active_signal_count=len(_orch_signal.active_signals),
                    )
                    _sensitivity_factor = _sens_result.sensitivity_factor
                    _sensitivity_reason = _sens_result.reason
                    _sensitivity_applied = _sens_result.applied

                    if (
                        _sens_result.applied
                        and _strategy_conditioned_scores
                        and isinstance(_strategy_conditioned_scores, dict)
                    ):
                        _scaled_bias = _apply_sens(
                            _orch_signal.combined_action_bias,
                            _sens_result,
                            strategy_scores=_strategy_conditioned_scores,
                        )
                        for _sa, _sb in _scaled_bias.items():
                            if _sa in _strategy_conditioned_scores:
                                _strategy_conditioned_scores[_sa] = (
                                    _strategy_conditioned_scores[_sa] + _sb
                                )
            except Exception as _sens_err:
                _log.debug("Signal sensitivity skipped: %s", _sens_err)

            # Objective decision adapter: adjust strategy/goal/plan scoring.
            _objective_decision_signal_dict: dict | None = None
            try:
                from umh.runtime_engine.objective_decision_adapter import (
                    apply_goal_scale,
                    apply_plan_bias,
                    apply_strategy_shift,
                    compute_decision_signal,
                )

                _oda_signal = compute_decision_signal(
                    self._objective_history, objective_trend=_objective_trend
                )
                if _oda_signal.is_active:
                    _objective_decision_signal_dict = _oda_signal.to_dict()

                    if (
                        _strategy_conditioned_scores
                        and isinstance(_strategy_conditioned_scores, dict)
                        and _oda_signal.strategy_shift != 0.0
                    ):
                        _sel = getattr(trace, "selected_strategy", "")
                        _strategy_conditioned_scores = apply_strategy_shift(
                            _strategy_conditioned_scores,
                            _oda_signal.strategy_shift,
                            _sel,
                        )

                    if _goal_score is not None and _oda_signal.goal_scale != 1.0:
                        _goal_score = apply_goal_scale(
                            _goal_score, _oda_signal.goal_scale
                        )

                    if (
                        _plan_step_attributed_score is not None
                        and _oda_signal.plan_bias != 0.0
                    ):
                        _plan_step_attributed_score = apply_plan_bias(
                            _plan_step_attributed_score, _oda_signal.plan_bias
                        )
            except Exception as _oda_err:
                _log.debug("Objective decision adapter skipped: %s", _oda_err)

            # Policy engine: select reasoning mode and apply adjustments.
            _active_policy: str | None = None
            _policy_reason: str | None = None
            _policy_adjustments: dict | None = None
            try:
                from umh.runtime_engine.policy_engine import (
                    PolicySignals,
                    apply_influence_modifiers,
                    apply_plan_confidence_modifier,
                    select_policy,
                )
                from umh.reasoning.influence_scoring import BASE_WEIGHTS as _base_ws

                _p_failure = 0
                _p_persistence = 0
                _p_sim_delta = 0.0
                if self.stats.decision_traces:
                    _lt = self.stats.decision_traces[-1]
                    _p_failure = getattr(_lt, "plan_step_failure_streak", 0) or 0
                    _ps_dict = getattr(_lt, "persistence_streaks", None)
                    if _ps_dict and isinstance(_ps_dict, dict):
                        _p_persistence = max(_ps_dict.values(), default=0)
                    _prev_sim = getattr(_lt, "world_state_similarity", None)
                    if _prev_sim is not None and _world_state_similarity is not None:
                        _p_sim_delta = _world_state_similarity - _prev_sim

                _policy_signals = PolicySignals(
                    failure_streak=_p_failure,
                    persistence_streak=_p_persistence,
                    exploration_rate=_exploration_rate or 0.0,
                    plan_confidence=_plan_confidence or 0.5,
                    state_similarity_delta=_p_sim_delta,
                )
                _policy_result = select_policy(
                    _policy_signals,
                    analytics_signal=_analytics_obj if _analytics_applied else None,
                )
                _active_policy = _policy_result.policy.value
                _policy_reason = _policy_result.reason
                _policy_adjustments = _policy_result.adjustments.to_dict()

                # Apply influence weight modifiers if influence was computed
                if (
                    _influence_weights is not None
                    and _policy_result.adjustments.influence_weight_modifiers
                ):
                    _mod_weights = apply_influence_modifiers(
                        _influence_weights,
                        _policy_result.adjustments.influence_weight_modifiers,
                    )
                    _influence_weights = _mod_weights

                # Apply plan confidence modifier
                if _plan_confidence is not None:
                    _plan_confidence = apply_plan_confidence_modifier(
                        _plan_confidence,
                        _policy_result.adjustments.plan_confidence_modifier,
                    )
            except Exception as _pe_err:
                _log.debug("Policy engine skipped: %s", _pe_err)

            # Directive engine: generate, score, select, evolve directives.
            _active_directives: "tuple[dict, ...] | None" = None
            _directive_scores: dict | None = None
            _directive_selection_reason: str | None = None
            _directive_evolution_events: "tuple[str, ...] | None" = None
            try:
                from umh.planning.directive_engine import get_directive_engine

                _de = get_directive_engine()

                _de_quality_trend = 0.0
                _de_outcome_q = 0.0
                if self.stats.decision_traces:
                    _lt_de = self.stats.decision_traces[-1]
                    _de_outcome_q = getattr(_lt_de, "quality_score", 0.0)
                    if len(self.stats.decision_traces) >= 2:
                        _prev_q = getattr(
                            self.stats.decision_traces[-2], "quality_score", 0.0
                        )
                        _de_quality_trend = _de_outcome_q - _prev_q

                _de_snap = _de.process_turn(
                    failure_streak=(
                        getattr(
                            self.stats.decision_traces[-1],
                            "plan_step_failure_streak",
                            0,
                        )
                        or 0
                    )
                    if self.stats.decision_traces
                    else 0,
                    exploration_rate=_exploration_rate or 0.0,
                    plan_confidence=_plan_confidence or 0.5,
                    quality_trend=_de_quality_trend,
                    outcome_quality=_de_outcome_q,
                    influence_score=_final_influence_score or 0.0,
                    current_turn=self.stats.turns,
                )
                _active_directives = _de_snap.active
                _directive_scores = _de_snap.scores
                _directive_selection_reason = _de_snap.selection_reason
                _directive_evolution_events = _de_snap.evolution_events

                # Apply directive effects to plan confidence
                if _plan_confidence is not None and _de_snap.effects.plan_bias != 0.0:
                    _plan_confidence = min(
                        1.0, max(0.0, _plan_confidence + _de_snap.effects.plan_bias)
                    )
            except Exception as _de_err:
                _log.debug("Directive engine skipped: %s", _de_err)

            # Memory fabric: record learning events from all subsystems.
            _memory_entries_written: "tuple[str, ...] | None" = None
            _memory_queries_used: "tuple[str, ...] | None" = None
            _memory_aggregation_summary: dict | None = None
            try:
                from umh.persistence_layer.memory_fabric import (
                    EntryType as _MFEntryType,
                    MemoryEntry as _MFEntry,
                    get_memory_fabric,
                )

                _mf = get_memory_fabric()

                # Strategy outcome
                _sel_s = getattr(trace, "selected_strategy", "")
                _q_s = getattr(trace, "quality_score", 0.0)
                if _sel_s:
                    _mf.record(
                        _MFEntry(
                            entry_type=_MFEntryType.STRATEGY_OUTCOME,
                            turn=self.stats.turns,
                            features={
                                "strategy": _sel_s,
                                "quality": _q_s,
                                "confidence": getattr(trace, "confidence", 0.0),
                            },
                            outcome=_q_s,
                            source="strategy_memory",
                        )
                    )

                # State observation
                if _world_state_id:
                    _mf.record(
                        _MFEntry(
                            entry_type=_MFEntryType.STATE_OBSERVATION,
                            turn=self.stats.turns,
                            features={
                                "state_id": _world_state_id,
                                "cluster": _world_state_cluster or "",
                                "similarity": _world_state_similarity or 0.0,
                            },
                            outcome=_q_s,
                            source="world_state",
                        )
                    )

                # Signal outcome
                if _influence_components:
                    _sig_feats: dict[str, float | str] = {}
                    for _ic in _influence_components:
                        if isinstance(_ic, dict):
                            _sig_feats[_ic.get("name", "")] = _ic.get("value", 0.0)
                    _mf.record(
                        _MFEntry(
                            entry_type=_MFEntryType.SIGNAL_OUTCOME,
                            turn=self.stats.turns,
                            features=_sig_feats,
                            outcome=_final_influence_score or 0.0,
                            source="influence_scoring",
                        )
                    )

                # Directive event
                if _active_directives:
                    for _ad in _active_directives:
                        if isinstance(_ad, dict):
                            _mf.record(
                                _MFEntry(
                                    entry_type=_MFEntryType.DIRECTIVE_EVENT,
                                    turn=self.stats.turns,
                                    features={
                                        "directive_id": _ad.get("directive_id", ""),
                                        "directive_type": _ad.get("directive_type", ""),
                                        "priority": _ad.get("priority", 0.0),
                                        "confidence": _ad.get("confidence", 0.0),
                                    },
                                    outcome=_ad.get("score", 0.0),
                                    source="directive_engine",
                                )
                            )

                # Plan outcome
                if _plan_step_attributed_score is not None:
                    _mf.record(
                        _MFEntry(
                            entry_type=_MFEntryType.PLAN_OUTCOME,
                            turn=self.stats.turns,
                            features={
                                "plan_id": _plan_active_id or "",
                                "step": _plan_active_step or "",
                                "goal_id": _plan_step_goal_id or "",
                            },
                            outcome=_plan_step_attributed_score,
                            source="plan_engine",
                        )
                    )

                # Credit event
                if _causal_credit_dict and isinstance(_causal_credit_dict, dict):
                    _cc_total = 0.0
                    _cc_comps = _causal_credit_dict.get("components", [])
                    if isinstance(_cc_comps, list):
                        for _ccc in _cc_comps:
                            if isinstance(_ccc, dict):
                                _cc_total += _ccc.get("weight", 0.0)
                    _mf.record(
                        _MFEntry(
                            entry_type=_MFEntryType.CREDIT_EVENT,
                            turn=self.stats.turns,
                            features={
                                "reason": _credit_reason or "",
                                "total_weight": _cc_total,
                            },
                            outcome=_q_s,
                            source="causal_credit",
                        )
                    )

                # Flush turn tracking for trace observability
                _mf_snap = _mf.flush_turn_tracking()
                _memory_entries_written = _mf_snap.entries_written or None
                _memory_queries_used = _mf_snap.queries_used or None
                _memory_aggregation_summary = _mf_snap.aggregation_summary or None
            except Exception as _mf_err:
                _log.debug("Memory fabric recording skipped: %s", _mf_err)

            # Fabric analytics: read-only summary for trace observability.
            _fabric_analytics_summary: dict | None = None
            try:
                from umh.analytics.fabric_analytics import compute_analytics_summary
                from umh.persistence_layer.memory_fabric import get_memory_fabric as _get_mf_analytics

                _fa_fabric = _get_mf_analytics()
                _fa_result = compute_analytics_summary(_fa_fabric)
                if _fa_result:
                    _fabric_analytics_summary = _fa_result
            except Exception as _fa_err:
                _log.debug("Fabric analytics skipped: %s", _fa_err)

            # Objective engine: compute unified trajectory value function.
            _objective_snapshot_dict: dict | None = None
            _objective_value: float | None = None
            try:
                from umh.runtime_engine.objective_engine import ObjectiveSnapshot, compute_objective

                _obj_policy_changes = 0
                _obj_prev_policy = ""
                if self.stats.decision_traces:
                    _obj_prev_policy = (
                        getattr(self.stats.decision_traces[-1], "active_policy", "")
                        or ""
                    )
                    for _ot in self.stats.decision_traces:
                        _op = getattr(_ot, "active_policy", None)
                        if _op and _op != _obj_prev_policy:
                            _obj_policy_changes += 1

                _obj_plan_steps_completed = 0
                _obj_plan_steps_total = 0
                if _plan_count is not None:
                    _obj_plan_steps_total = _plan_count
                if _plan_step_status == "completed":
                    _obj_plan_steps_completed = max(
                        1,
                        (_plan_active_step or "").count(".")
                        + (1 if _plan_active_step else 0),
                    )

                _obj_snapshot = ObjectiveSnapshot(
                    goal_score=_goal_score or 0.0,
                    goal_delta=_goal_delta or 0.0,
                    goal_confidence=_goal_confidence or 0.0,
                    plan_confidence=_plan_confidence or 0.5,
                    plan_steps_completed=_obj_plan_steps_completed,
                    plan_steps_total=_obj_plan_steps_total,
                    failure_streak=(
                        getattr(
                            self.stats.decision_traces[-1],
                            "plan_step_failure_streak",
                            0,
                        )
                        or 0
                    )
                    if self.stats.decision_traces
                    else 0,
                    quality_score=getattr(trace, "quality_score", 0.0),
                    system_confidence=getattr(trace, "confidence", 0.5),
                    policy_changes=_obj_policy_changes,
                    current_policy=_active_policy or "",
                    previous_policy=_obj_prev_policy,
                )
                _obj_result = compute_objective(_obj_snapshot)
                _objective_snapshot_dict = _obj_result.to_dict()
                _objective_value = _obj_result.value
                self._objective_history.append(_objective_value)
            except Exception as _obj_err:
                _log.debug("Objective engine skipped: %s", _obj_err)

            # Unified influence: merge all pending channels deterministically.
            try:
                from umh.reasoning.influence_orchestrator import resolve_influence

                self._unified_influence = resolve_influence(
                    control_directives=self._pending_control_directives,
                    convergence_directives=self._pending_convergence_directives,
                    strategy_override=self._pending_strategy_override,
                    synthesis_suppressed=self._pending_synthesis_suppression,
                    exploration_suppressed=self._pending_exploration_suppression,
                    goal_state=self._goal_state,
                    goal_progress_signal=_goal_progress_signal,
                    convergence_status=_conv_status,
                    goal_delta_history=_goal_delta_history,
                    blended_goal_state=self._blended_goal_state,
                    goal_registry=self._goal_registry,
                )

                enriched = build_trace(
                    turn_id=trace.turn_id,
                    evaluation=evaluation,
                    signals=signals,
                    result=result,
                    directives=list(trace.directives_applied),
                    control_decision=getattr(trace, "control_decision", None),
                    thresholds_used=thresholds_dict,
                    strategy_selection=_strat_sel,
                    synthesized_strategy=_synth_strategy,
                    synthesis_reason=_synth_reason,
                    goal_mode=_resolved_mode_str,
                    convergence_status=_conv_status,
                    convergence_reason=_conv_reason,
                    convergence_action=_conv_action,
                    unified_influence=self._unified_influence.to_dict(),
                    goal_score=_goal_score,
                    goal_delta=_goal_delta,
                    goal_confidence=_goal_confidence,
                    exploration_enabled=self._unified_influence.exploration_enabled,
                    synthesis_enabled=self._unified_influence.synthesis_enabled,
                    goal_gating_reason=self._unified_influence.goal_gating_reason,
                    active_goal_id=_active_goal_id,
                    goal_pool_snapshot=_goal_pool_snapshot,
                    blended_goals=_blended_goals,
                    blended_primary_goal_id=_blended_primary_id,
                    blended_entropy=_blended_entropy,
                    execution_budget=_exec_budget_dict,
                    candidate_distribution=_candidate_dist,
                    memory_persisted=self._persist_memory or None,
                    memory_version=self._memory_version
                    if self._persist_memory
                    else None,
                    persistence_loaded=True if self._persist_memory else None,
                    persistence_version=1 if self._persist_memory else None,
                    exploration_rate=_exploration_rate,
                    exploration_reason=_exploration_reason,
                    det_exploration_active=_det_exploration_active,
                    det_exploration_adjustments=_det_exploration_adjustments,
                    generated_goals=_generated_goals_dicts,
                    goal_mutations=_goal_mutations_dicts,
                    meta_goal_reason=_meta_goal_reason,
                    goal_validation_results=_goal_validation_results,
                    rejected_goals=_rejected_goals,
                    validation_reason=_validation_reason,
                    goal_alignment_scores=_goal_alignment_scores,
                    alignment_penalties=_alignment_penalties,
                    alignment_decisions=_alignment_decisions,
                    counterfactual_expected_utility=_cf_expected_utility,
                    counterfactual_confidence=_cf_confidence,
                    counterfactual_reasoning=_cf_reasoning,
                    counterfactual_uncertainty=_cf_uncertainty,
                    counterfactual_exploration_boost=_cf_exploration_boost,
                    counterfactual_horizon_value=_cf_horizon_value,
                    counterfactual_horizon_reason=_cf_horizon_reason,
                    persistence_streaks=_persistence_streaks,
                    commitment_bonuses=_commitment_bonuses,
                    switch_penalty_applied=_switch_penalty_applied,
                    strategy_mutations=_strategy_mutations,
                    strategy_origins=_strategy_origins,
                    mutation_reason=_mutation_reason,
                    active_plan_id=_plan_active_id,
                    active_plan_step=_plan_active_step,
                    plan_confidence=_plan_confidence,
                    plan_count=_plan_count,
                    plan_generation_reason=_plan_generation_reason,
                    world_state_id=_world_state_id,
                    world_state_cluster=_world_state_cluster,
                    world_state_similarity=_world_state_similarity,
                    conditioning_bias=_conditioning_bias_dict,
                    strategy_base_scores=_strategy_base_scores,
                    strategy_conditioned_scores=_strategy_conditioned_scores,
                    plan_step_goal_id=_plan_step_goal_id,
                    plan_step_attributed_score=_plan_step_attributed_score,
                    plan_step_attribution_source=_plan_step_attribution_source,
                    plan_step_status=_plan_step_status,
                    plan_step_retry_count=_plan_step_retry_count,
                    plan_step_failure_streak=_plan_step_failure_streak,
                    state_transfer_weight=_state_transfer_weight,
                    strategy_transfer_scores=_strategy_transfer_scores,
                    plan_transfer_score=_plan_transfer_score_val,
                    state_similarity_used=_state_similarity_used,
                    replan_adjustment=_replan_adjustment,
                    plan_mutation_applied=_plan_mutation_applied,
                    plan_mutation_type=_plan_mutation_type,
                    mutated_plan_id=_mutated_plan_id,
                    mutated_from_plan_id=_mutated_from_plan_id,
                    plan_recombination_applied=_plan_recombination_applied,
                    recombined_plan_id=_recombined_plan_id,
                    recombined_from_plan_ids=_recombined_from_plan_ids,
                    plan_evolution_reason=_plan_evolution_reason,
                    plan_origin_snapshot=_plan_origin_snapshot,
                    world_state_cluster_quality=_ws_cluster_quality,
                    learned_state_bias=_learned_state_bias,
                    combined_state_bias=_combined_state_bias,
                    cluster_quality_ema=_cluster_quality_ema,
                    cluster_observation_count=_cluster_obs_count,
                    world_state_reinforcement_applied=_ws_reinforcement_applied,
                    influence_components=_influence_components,
                    influence_weights=_influence_weights,
                    final_influence_score=_final_influence_score,
                    influence_breakdown=_influence_breakdown,
                    influence_applied=_influence_applied,
                    influence_adjustment=_influence_adjustment,
                    influence_pre_score=_influence_pre_score,
                    influence_post_score=_influence_post_score,
                    meta_weights=_meta_weights,
                    meta_weight_adjustments=_meta_weight_adjustments,
                    meta_weight_signal_performance=_meta_weight_signal_performance,
                    active_policy=_active_policy,
                    policy_reason=_policy_reason,
                    policy_adjustments=_policy_adjustments,
                    active_directives=_active_directives,
                    directive_scores=_directive_scores,
                    directive_selection_reason=_directive_selection_reason,
                    directive_evolution_events=_directive_evolution_events,
                    memory_entries_written=_memory_entries_written,
                    memory_queries_used=_memory_queries_used,
                    memory_aggregation_summary=_memory_aggregation_summary,
                    fabric_analytics_summary=_fabric_analytics_summary,
                    analytics_signal=_analytics_signal_dict,
                    analytics_applied=_analytics_applied,
                    objective_snapshot=_objective_snapshot_dict,
                    objective_value=_objective_value,
                    objective_trend=_objective_trend,
                    optimization_signal=_optimization_signal_dict,
                    objective_history_length=len(self._objective_history)
                    if self._objective_history
                    else None,
                    objective_persisted=self._persist_memory or None,
                    objective_decision_signal=_objective_decision_signal_dict,
                    causal_credit=_causal_credit_dict,
                    immediate_credit=_immediate_credit,
                    delayed_credit=_delayed_credit,
                    structural_credit=_structural_credit,
                    credit_reason=_credit_reason,
                    credited_entities=_credited_entities,
                    trap_signal_active=_trap_signal_active,
                    trap_adjustment=_trap_adjustment,
                    meta_signal_strength=_meta_signal_strength,
                    stability_guard_active=_stability_guard_active,
                    context_signal=_context_signal_dict,
                    context_type=_context_type,
                    meta_generalization_matched=_mg_matched,
                    meta_generalization_prototype_id=_mg_prototype_id,
                    meta_generalization_similarity=_mg_similarity,
                    meta_generalization_priors=_mg_priors,
                    meta_generalization_signature=_mg_signature,
                    meta_generalization_prototype_usage=_mg_prototype_usage,
                    meta_generalization_prototype_avg_reward=_mg_prototype_avg_reward,
                    meta_generalization_suppressed=_mg_suppressed,
                    causal_signal=_causal_signal_dict,
                    causal_confidence=_causal_confidence,
                    causal_applied=_causal_applied,
                    causal_context_match=_causal_context_match,
                    credit_signal=_credit_signal_dict,
                    credit_confidence=_credit_confidence,
                    credit_applied=_credit_applied,
                    credit_horizon=_credit_horizon,
                    foresight_signal=_foresight_signal_dict,
                    foresight_confidence=_foresight_confidence,
                    foresight_applied=_foresight_applied,
                    foresight_depth=_foresight_depth,
                    orchestration_consensus=_orch_consensus,
                    orchestration_active_count=_orch_active_count,
                    orchestration_suppressed_count=_orch_suppressed_count,
                    orchestration_dominant_source=_orch_dominant_source,
                    sensitivity_factor=_sensitivity_factor,
                    sensitivity_reason=_sensitivity_reason,
                    sensitivity_applied=_sensitivity_applied,
                    planner_active=_planner_active,
                    planner_scores=_planner_scores,
                    planner_choice=_planner_choice,
                    planner_confidence=_planner_confidence,
                    planner_reason=_planner_reason,
                    planner_horizon=_planner_horizon,
                    planner_uncertainty=_planner_uncertainty,
                    planner_consistency=_planner_consistency,
                    planner_adjusted_confidence=_planner_adjusted_confidence,
                )
                self.stats.decision_traces[-1] = enriched
                trace = enriched
            except Exception as e:
                _log.debug("Influence orchestration skipped: %s", e)

            # Causal memory: record transition for next-turn learning.
            try:
                if (
                    self._causal_mem is not None
                    and len(self.stats.decision_traces) >= 2
                ):
                    _cm_prev = self.stats.decision_traces[-2]
                    _cm_ctx = getattr(_cm_prev, "context_type", None) or "unknown"
                    _cm_act = getattr(_cm_prev, "selected_strategy", "") or ""
                    _cm_reward = getattr(_cm_prev, "quality_score", 0.0) or 0.0
                    _cm_obj = getattr(_cm_prev, "objective_value", None)
                    if _cm_obj is None:
                        _cm_obj = _cm_reward
                    if _cm_act:
                        self._causal_mem.record_transition(
                            _cm_ctx, _cm_act, _cm_reward, float(_cm_obj)
                        )
            except Exception as _cm_rec_err:
                _log.debug("Causal memory record skipped: %s", _cm_rec_err)

            # Credit assignment: record step for backward propagation.
            try:
                if self._credit_eng is not None and self.stats.decision_traces:
                    _ca_trace = self.stats.decision_traces[-1]
                    _ca_act = getattr(_ca_trace, "selected_strategy", "") or ""
                    _ca_ctx = getattr(_ca_trace, "context_type", None) or "unknown"
                    _ca_reward = getattr(_ca_trace, "quality_score", 0.0) or 0.0
                    _ca_obj = getattr(_ca_trace, "objective_value", None)
                    if _ca_obj is None:
                        _ca_obj = _ca_reward
                    if _ca_act:
                        self._credit_eng.record_step(
                            _ca_act, _ca_ctx, _ca_reward, float(_ca_obj)
                        )
            except Exception as _ca_rec_err:
                _log.debug("Credit assignment record skipped: %s", _ca_rec_err)

            # Batch-persist all memory layers after trace is finalized
            _persist_saved = False
            _persist_error = None
            if self._persist_memory:
                self._memory_version += 1
                try:
                    from umh.protocols.persistence import (
                        flush as persistence_flush,
                        save_meta_weights,
                        save_memory_fabric,
                        save_objective_history,
                    )
                    from umh.reasoning.meta_weight_engine import get_meta_weight_engine
                    from umh.persistence_layer.memory_fabric import get_memory_fabric

                    save_meta_weights(get_meta_weight_engine().snapshot())
                    save_memory_fabric(get_memory_fabric().snapshot())
                    save_objective_history(self._objective_history)
                    if self._world_substrate is not None:
                        from umh.protocols.persistence import save_world_substrate

                        save_world_substrate(self._world_substrate.snapshot())
                    persistence_flush()
                    _persist_saved = True
                    _persist_error = None
                except Exception as e:
                    _log.debug("Memory persistence flush skipped: %s", e)
                    _persist_saved = False
                    _persist_error = str(e)

            # Persist minimal session summary (never blocks response)
            try:
                from umh.protocols.persistence import append_session_summary

                latest = self.stats.decision_traces[-1]
                ctrl = getattr(latest, "control_decision", None)
                flags = (latest.signals or {}).get("flags", {})
                summary = {
                    "session_id": self.session_id,
                    "turn": latest.turn_id,
                    "strategy": latest.selected_strategy,
                    "quality_score": latest.quality_score,
                    "confidence": latest.confidence,
                    "signals": {
                        "hallucination": flags.get("hallucination_risk", False),
                        "incomplete": flags.get("incomplete", False),
                    },
                    "control_intervened": ctrl is not None and ctrl.intervene,
                    "goal_mode": _resolved_mode_str,
                    "convergence_status": _conv_status,
                    "persistence_saved": _persist_saved
                    if self._persist_memory
                    else None,
                    "persistence_error": _persist_error
                    if self._persist_memory
                    else None,
                }
                append_session_summary(summary)
            except Exception as e:
                _log.debug("Session summary persistence skipped: %s", e)
        except Exception as e:
            _log.debug("Decision trace skipped: %s", e)

        return result

    def get_last_trace(self) -> "DecisionTrace | None":
        """Return the most recent decision trace, or None."""
        traces = self.stats.decision_traces
        return traces[-1] if traces else None

    def get_last_control_decision(self) -> object | None:
        """Return the control decision from the most recent trace, or None."""
        trace = self.get_last_trace()
        if trace is None:
            return None
        return getattr(trace, "control_decision", None)

    def get_pending_control_directives(self) -> list[str]:
        """Return directives queued by the control layer for the next turn."""
        return list(self._pending_control_directives)

    def get_pending_strategy_override(self) -> str | None:
        """Return strategy override queued by the control layer, or None."""
        return self._pending_strategy_override

    def get_calibrated_thresholds(self) -> "CalibratedThresholds":
        """Return current calibrated thresholds, or defaults if calibration is off."""
        from umh.world.calibration import get_thresholds

        return get_thresholds(self._calibration_engine)

    def get_pending_convergence_directives(self) -> list[str]:
        """Return directives queued by convergence for the next turn."""
        return list(self._pending_convergence_directives)

    def get_convergence_suppression(self) -> dict[str, bool]:
        """Return convergence suppression flags for synthesis/exploration."""
        return {
            "suppress_synthesis": self._pending_synthesis_suppression,
            "suppress_exploration": self._pending_exploration_suppression,
        }

    def get_unified_influence(self) -> "UnifiedInfluence":
        """Return the merged influence for the next turn.

        If the orchestrator hasn't run yet (first turn or orchestration
        skipped), returns NO_INFLUENCE — identical to pre-orchestrator
        behavior (all enabled, no directives).
        """
        if self._unified_influence is not None:
            return self._unified_influence
        from umh.reasoning.influence_orchestrator import NO_INFLUENCE

        return NO_INFLUENCE

    def set_goal(self, goal_state: object) -> None:
        """Set a single active goal for this session.

        Backward-compatible: sets _goal_state directly.
        If a GoalRegistry is also in use, adds the goal to the registry.
        """
        self._goal_state = goal_state
        if self._goal_registry is not None:
            gid = getattr(goal_state, "goal_id", None)
            if gid and getattr(goal_state, "active", False):
                self._goal_registry.add_goal(goal_state)
                self._goal_registry.set_active_goal(gid)

    def set_goals(self, goals: list) -> None:
        """Set multiple goals via GoalRegistry.

        Creates a GoalRegistry if one doesn't exist, adds all goals,
        and lets the arbitrator select the active one on the next turn.
        """
        from umh.goals.state import GoalRegistry

        if self._goal_registry is None:
            self._goal_registry = GoalRegistry(persist=self._persist_memory)
        for g in goals:
            self._goal_registry.add_goal(g)
        active = self._goal_registry.get_all_goals()
        if len(active) == 1:
            self._goal_registry.set_active_goal(active[0].goal_id)
            self._goal_state = active[0]

    def add_goal(self, goal_state: object) -> None:
        """Add a goal to the registry."""
        from umh.goals.state import GoalRegistry

        if self._goal_registry is None:
            self._goal_registry = GoalRegistry(persist=self._persist_memory)
        self._goal_registry.add_goal(goal_state)
        if self._goal_state is None:
            self._goal_state = goal_state

    def get_active_goal(self) -> object:
        """Return the currently active goal selected by arbitration.

        Falls back to _goal_state for single-goal backward compat.
        """
        if self._goal_registry is not None:
            active = self._goal_registry.get_active_goal()
            from umh.goals.state import NO_GOAL

            if active != NO_GOAL:
                return active
        return self.get_goal_state()

    def get_execution_budget(self) -> object:
        """Return the current ExecutionBudget, or NO_BUDGET if not active."""
        if self._execution_budget is not None:
            return self._execution_budget
        try:
            from umh.runtime_engine.execution_budget import NO_BUDGET
        except ImportError:
            pass

        return NO_BUDGET

    def get_blended_goal(self) -> object:
        """Return the current BlendedGoalState, or NO_BLEND if not active."""
        if self._blended_goal_state is not None:
            return self._blended_goal_state
        try:
            from umh.runtime_engine.goal_arbitrator import NO_BLEND
        except ImportError:
            pass

        return NO_BLEND

    def get_goal_state(self) -> object:
        """Return the active goal, or NO_GOAL if none is set."""
        if self._goal_state is not None:
            return self._goal_state
        from umh.goals.state import NO_GOAL

        return NO_GOAL

    def get_goal_registry(self) -> object | None:
        """Return the GoalRegistry, or None if multi-goal is not active."""
        return self._goal_registry

    def get_goal_evaluation(self) -> object:
        """Return the current goal evaluation, or NO_GOAL_EVAL if none."""
        if self._goal_eval_current is not None:
            return self._goal_eval_current
        try:
            from umh.runtime_engine.goal_evaluator import NO_GOAL_EVAL
        except ImportError:
            pass

        return NO_GOAL_EVAL

    def get_goal_evaluation_for(self, goal_id: str) -> object:
        """Return the latest goal evaluation for a specific goal."""
        ev = self._goal_evals.get(goal_id)
        if ev is not None:
            return ev
        try:
            from umh.runtime_engine.goal_evaluator import NO_GOAL_EVAL
        except ImportError:
            pass

        return NO_GOAL_EVAL

    def get_last_convergence_decision(self) -> object | None:
        """Return convergence fields from the most recent trace, or None."""
        trace = self.get_last_trace()
        if trace is None:
            return None
        status = getattr(trace, "convergence_status", None)
        if status is None:
            return None
        return {
            "status": status,
            "reason": getattr(trace, "convergence_reason", None),
            "action": getattr(trace, "convergence_action", None),
        }

    def get_exploration_state(self) -> object:
        """Return the current ExplorationState, or NO_EXPLORATION_STATE."""
        if self._exploration_state is not None:
            return self._exploration_state
        from umh.analytics.adaptive_exploration import NO_EXPLORATION_STATE

        return NO_EXPLORATION_STATE

    def get_meta_goal_engine(self) -> object | None:
        """Return the MetaGoalEngine, or None if not active."""
        return self._meta_goal_engine

    @property
    def memory_version(self) -> int:
        """Return the current memory persistence version counter."""
        return self._memory_version

    @property
    def persist_memory_enabled(self) -> bool:
        """Return whether memory persistence is active."""
        return self._persist_memory

    def record_outcome(self, outcome: object) -> bool:
        """Record an external outcome signal and apply it to memory layers.

        Uses causal attribution to distribute outcome credit across
        contributing factors (strategy, directive, goal) proportional
        to each factor's influence on the turn's output.

        The outcome's turn_id links it to a specific DecisionTrace. The
        trace contains the signals needed for attribution computation.

        Supports delayed feedback: an outcome for turn 5 can arrive at
        turn 15. The trace lookup uses turn_id, not recency.

        Returns True if the outcome was applied, False if the turn was
        not found or the outcome was below confidence floor.
        """
        from umh.feedback.outcome_feedback import (
            OutcomeStore,
            apply_outcome_to_strategy_memory,
            apply_outcome_to_directive_memory,
            apply_outcome_to_goal_tracker,
        )
        from umh.reasoning.causal_attribution import compute_attribution

        if self._outcome_store is None:
            self._outcome_store = OutcomeStore()

        self._outcome_store.record(outcome)

        turn_id = getattr(outcome, "turn_id", -1)
        trace = None
        trace_idx = -1
        for i, t in enumerate(self.stats.decision_traces):
            if getattr(t, "turn_id", None) == turn_id:
                trace = t
                trace_idx = i
                break

        if trace is None:
            _log.debug("No trace found for outcome turn_id=%d", turn_id)
            return False

        attribution = compute_attribution(trace)

        strategy = getattr(trace, "selected_strategy", "")
        quality = getattr(trace, "quality_score", 0.0)
        goal_score = getattr(trace, "goal_score", None)
        goal_id = getattr(trace, "active_goal_id", None)

        if strategy:
            apply_outcome_to_strategy_memory(
                strategy,
                quality,
                outcome,
                attribution_weight=attribution.strategy_weight,
            )

        if strategy:
            apply_outcome_to_directive_memory(
                strategy,
                quality,
                outcome,
                attribution_weight=attribution.directive_weight,
            )

        if goal_id and goal_score is not None and self._goal_registry is not None:
            apply_outcome_to_goal_tracker(
                goal_id,
                goal_score,
                outcome,
                self._goal_registry,
                attribution_weight=attribution.goal_weight,
            )

        # Enrich the trace with attribution + outcome fields
        try:
            from umh.runtime_engine.decision_trace import build_trace

            enriched = build_trace(
                turn_id=trace.turn_id,
                evaluation=getattr(trace, "signals", None),
                result=None,
                directives=list(getattr(trace, "directives_applied", ())),
                control_decision=getattr(trace, "control_decision", None),
                thresholds_used=getattr(trace, "thresholds_used", None),
                strategy_selection=getattr(trace, "strategy_selection", None),
                synthesized_strategy=getattr(trace, "synthesized_strategy", None),
                synthesis_reason=getattr(trace, "synthesis_reason", None),
                goal_mode=getattr(trace, "goal_mode", None),
                convergence_status=getattr(trace, "convergence_status", None),
                convergence_reason=getattr(trace, "convergence_reason", None),
                convergence_action=getattr(trace, "convergence_action", None),
                unified_influence=getattr(trace, "unified_influence", None),
                goal_score=goal_score,
                goal_delta=getattr(trace, "goal_delta", None),
                goal_confidence=getattr(trace, "goal_confidence", None),
                exploration_enabled=getattr(trace, "exploration_enabled", None),
                synthesis_enabled=getattr(trace, "synthesis_enabled", None),
                goal_gating_reason=getattr(trace, "goal_gating_reason", None),
                active_goal_id=goal_id,
                goal_pool_snapshot=getattr(trace, "goal_pool_snapshot", None),
                blended_goals=getattr(trace, "blended_goals", None),
                blended_primary_goal_id=getattr(trace, "blended_primary_goal_id", None),
                blended_entropy=getattr(trace, "blended_entropy", None),
                execution_budget=getattr(trace, "execution_budget", None),
                candidate_distribution=getattr(trace, "candidate_distribution", None),
                memory_persisted=getattr(trace, "memory_persisted", None),
                memory_version=getattr(trace, "memory_version", None),
                persistence_loaded=getattr(trace, "persistence_loaded", None),
                persistence_saved=getattr(trace, "persistence_saved", None),
                persistence_version=getattr(trace, "persistence_version", None),
                persisted_components=getattr(trace, "persisted_components", None),
                persistence_error=getattr(trace, "persistence_error", None),
                outcome_attached=True,
                outcome_score=getattr(outcome, "success", 0.0),
                attribution_weights=attribution.to_dict(),
                attribution_reason=attribution.reason,
            )
            if trace_idx >= 0:
                self.stats.decision_traces[trace_idx] = enriched
        except Exception as e:
            _log.debug("Trace enrichment with attribution skipped: %s", e)

        _log.debug(
            "Outcome %s applied to turn %d (strategy=%s w=%.2f, directive w=%.2f, goal=%s w=%.2f, reason=%s)",
            getattr(outcome, "outcome_id", "?"),
            turn_id,
            strategy,
            attribution.strategy_weight,
            attribution.directive_weight,
            goal_id,
            attribution.goal_weight,
            attribution.reason,
        )
        return True

    def get_outcome_store(self) -> object:
        """Return the session's OutcomeStore, creating it if needed."""
        if self._outcome_store is None:
            from umh.feedback.outcome_feedback import OutcomeStore

            self._outcome_store = OutcomeStore()
        return self._outcome_store

    def _maybe_compact(self) -> None:
        """Trigger compaction if the session message list exceeds the threshold.

        Failure is isolated — compaction is an optimization, not a requirement.
        """
        try:
            from umh.runtime_engine.context_compaction import ContextCompactor

            compactor = ContextCompactor(self.ctx)
            if compactor.should_compact(self._messages):
                brief = compactor.compact(self._messages, self.session_id)
                seed = compactor.build_seeded_context(brief)
                self._messages = [{"role": "system", "content": seed}]
                self.stats.compactions += 1
                _log.info(
                    "Session %s compacted (gen %d)",
                    self.session_id[:8],
                    self.stats.compactions,
                )
        except Exception as e:
            _log.debug("Session compaction skipped: %s", e)
