"""
DecisionTrace — structured per-turn observability for UMH.

Captures what happened, why it happened, and what signals influenced it.
Pure instrumentation — no behavior changes, no LLM calls, no randomness.

Each turn in a SessionRuntime produces one DecisionTrace. The trace is
frozen after creation (immutable snapshot) and appended to SessionStats.

Usage::

    from umh.decision.trace import DecisionTrace

    trace = DecisionTrace(
        turn_id=1,
        strategies_considered=("clarity",),
        strategy_scores={"clarity": 0.8},
        selected_strategy="clarity",
        quality_score=0.85,
        confidence=0.9,
        signals={},
        attributed_signals={},
        horizon={},
        directives_applied=(),
        model_used="gemini-2.5-flash",
        latency_ms=120,
        tokens_used=None,
        was_enhanced=False,
    )
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

_log = logging.getLogger(__name__)

MAX_TRACES = 50
DEBUG_TRACE = False


@dataclass(frozen=True)
class DecisionTrace:
    """Immutable snapshot of a single turn's decision path."""

    turn_id: int

    # Strategy
    strategies_considered: tuple[str, ...]
    strategy_scores: dict[str, float]
    selected_strategy: str

    # Evaluation
    quality_score: float
    confidence: float

    # Signals
    signals: dict

    # Routing
    attributed_signals: dict

    # Horizon
    horizon: dict

    # Prompt adaptation
    directives_applied: tuple[str, ...]

    # Metadata
    model_used: str
    latency_ms: int
    tokens_used: dict | None
    was_enhanced: bool

    # Control layer (None when disabled or no intervention)
    control_decision: object | None = None

    # Calibration snapshot (None when calibration disabled)
    thresholds_used: dict | None = None

    # Multi-strategy selection summary (None when single execution)
    strategy_selection: dict | None = None

    # Strategy synthesis (None when no synthesis occurred this turn)
    synthesized_strategy: str | None = None
    synthesis_reason: str | None = None

    # Goal mode (None when DEFAULT or not set)
    goal_mode: str | None = None

    # Convergence (None when disabled or no evaluation)
    convergence_status: str | None = None
    convergence_reason: str | None = None
    convergence_action: str | None = None

    # Unified influence (None when orchestrator not used)
    unified_influence: dict | None = None

    # Goal evaluation (None when no goal active)
    goal_score: float | None = None
    goal_delta: float | None = None
    goal_confidence: float | None = None

    # Behavioral gating (final resolved state)
    exploration_enabled: bool | None = None
    synthesis_enabled: bool | None = None
    goal_gating_reason: str | None = None

    # Multi-goal arbitration (None when single goal or no registry)
    active_goal_id: str | None = None
    goal_pool_snapshot: dict | None = None

    # Goal blending (None when single goal or blending not active)
    blended_goals: tuple[tuple[str, float], ...] | None = None
    blended_primary_goal_id: str | None = None
    blended_entropy: float | None = None

    # Execution budget (None when no budget allocation)
    execution_budget: dict | None = None
    candidate_distribution: dict | None = None

    # Memory persistence (None when persistence not active)
    memory_persisted: bool | None = None
    memory_version: int | None = None

    # Persistence layer observability
    persistence_loaded: bool | None = None
    persistence_saved: bool | None = None
    persistence_version: int | None = None
    persisted_components: tuple[str, ...] | None = None
    persistence_error: str | None = None

    # Outcome feedback (None when no external outcome attached)
    outcome_attached: bool | None = None
    outcome_score: float | None = None

    # Causal attribution (None when no attribution computed)
    attribution_weights: dict | None = None
    attribution_reason: str | None = None

    # Adaptive exploration (None when controller not active)
    exploration_rate: float | None = None
    exploration_reason: str | None = None

    # Deterministic exploration engine (None when engine not active)
    det_exploration_active: bool | None = None
    det_exploration_adjustments: dict | None = None

    # Meta-goal generation (None when engine not active)
    generated_goals: tuple[dict, ...] | None = None
    goal_mutations: tuple[dict, ...] | None = None
    meta_goal_reason: str | None = None

    # Goal validation (None when validator not active)
    goal_validation_results: tuple[dict, ...] | None = None
    rejected_goals: tuple[str, ...] | None = None
    validation_reason: str | None = None

    # Goal alignment (None when alignment evaluator not active)
    goal_alignment_scores: dict | None = None
    alignment_penalties: tuple[str, ...] | None = None
    alignment_decisions: tuple[dict, ...] | None = None

    # Counterfactual evaluation (None when evaluator not active)
    counterfactual_expected_utility: dict | None = None
    counterfactual_confidence: dict | None = None
    counterfactual_reasoning: dict | None = None
    counterfactual_uncertainty: dict | None = None
    counterfactual_exploration_boost: dict | None = None
    counterfactual_horizon_value: dict | None = None
    counterfactual_horizon_reason: dict | None = None

    # Plan persistence (None when persistence tracking not active)
    persistence_streaks: dict | None = None
    commitment_bonuses: dict | None = None
    switch_penalty_applied: bool | None = None

    # Strategy mutation (None when mutation engine not active)
    strategy_mutations: tuple[dict, ...] | None = None
    strategy_origins: dict | None = None
    mutation_reason: str | None = None

    # Hierarchical planning (None when plan engine not active)
    active_plan_id: str | None = None
    active_plan_step: str | None = None
    plan_confidence: float | None = None
    plan_count: int | None = None
    plan_generation_reason: str | None = None

    # World state (None when engine not active)
    world_state_id: str | None = None
    world_state_cluster: str | None = None
    world_state_similarity: float | None = None
    conditioning_bias: dict | None = None

    # Conditioning integration (None when no bias applied to strategy scoring)
    strategy_base_scores: dict | None = None
    strategy_conditioned_scores: dict | None = None

    # Plan step attribution (None when no plan step was attributed)
    plan_step_goal_id: str | None = None
    plan_step_attributed_score: float | None = None
    plan_step_attribution_source: str | None = None

    # Plan step recovery (None when no recovery state active)
    plan_step_status: str | None = None
    plan_step_retry_count: int | None = None
    plan_step_failure_streak: int | None = None

    # Cross-state transfer (None when no transfer computed)
    state_transfer_weight: float | None = None
    strategy_transfer_scores: dict | None = None
    plan_transfer_score: float | None = None
    state_similarity_used: float | None = None
    replan_adjustment: float | None = None

    # Plan evolution (None when no evolution occurred this turn)
    plan_mutation_applied: bool | None = None
    plan_mutation_type: str | None = None
    mutated_plan_id: str | None = None
    mutated_from_plan_id: str | None = None
    plan_recombination_applied: bool | None = None
    recombined_plan_id: str | None = None
    recombined_from_plan_ids: tuple[str, ...] | None = None
    plan_evolution_reason: str | None = None
    plan_origin_snapshot: dict | None = None

    # World-state reinforcement (None when no reinforcement this turn)
    world_state_cluster_quality: float | None = None
    learned_state_bias: dict | None = None
    combined_state_bias: dict | None = None
    cluster_quality_ema: float | None = None
    cluster_observation_count: int | None = None
    world_state_reinforcement_applied: bool | None = None

    # Influence scoring (None when no influence computed this turn)
    influence_components: tuple[dict, ...] | None = None
    influence_weights: dict | None = None
    final_influence_score: float | None = None
    influence_breakdown: dict | None = None
    influence_applied: bool | None = None
    influence_adjustment: float | None = None
    influence_pre_score: float | None = None
    influence_post_score: float | None = None

    # Meta-weight adaptation (None when engine not active)
    meta_weights: dict | None = None
    meta_weight_adjustments: dict | None = None
    meta_weight_signal_performance: dict | None = None

    # Policy engine (None when engine not active)
    active_policy: str | None = None
    policy_reason: str | None = None
    policy_adjustments: dict | None = None

    # Directive engine (None when engine not active)
    active_directives: tuple[dict, ...] | None = None
    directive_scores: dict | None = None
    directive_selection_reason: str | None = None
    directive_evolution_events: tuple[str, ...] | None = None

    # Memory fabric (None when fabric not active)
    memory_entries_written: tuple[str, ...] | None = None
    memory_queries_used: tuple[str, ...] | None = None
    memory_aggregation_summary: dict | None = None

    # Fabric analytics (None when analytics not computed)
    fabric_analytics_summary: dict | None = None

    # Analytics adapter (None when adapter not active)
    analytics_signal: dict | None = None
    analytics_applied: bool | None = None

    # Objective engine (None when engine not active)
    objective_snapshot: dict | None = None
    objective_value: float | None = None

    # Objective optimizer (None when optimizer not active)
    objective_trend: str | None = None
    optimization_signal: dict | None = None

    # Objective history persistence
    objective_history_length: int | None = None
    objective_persisted: bool | None = None

    # Objective decision adapter (None when adapter not active)
    objective_decision_signal: dict | None = None

    # Correction layer (None when not active)
    trap_signal_active: bool | None = None
    trap_adjustment: float | None = None
    restart_state_loaded: bool | None = None
    meta_signal_strength: float | None = None
    stability_guard_active: bool | None = None

    # Context disambiguation (None when not computed)
    context_signal: dict | None = None
    context_type: str | None = None

    # Meta-generalization (None when not active)
    meta_generalization_matched: bool | None = None
    meta_generalization_prototype_id: int | None = None
    meta_generalization_similarity: float | None = None
    meta_generalization_priors: dict | None = None
    meta_generalization_signature: dict | None = None
    meta_generalization_prototype_usage: int | None = None
    meta_generalization_prototype_avg_reward: float | None = None
    meta_generalization_suppressed: bool | None = None

    # Causal transition memory (None when not active)
    causal_signal: dict | None = None
    causal_confidence: float | None = None
    causal_applied: bool | None = None
    causal_context_match: str | None = None

    # Causal credit (None when no credit computed this turn)
    causal_credit: dict | None = None
    immediate_credit: dict | None = None
    delayed_credit: dict | None = None
    structural_credit: dict | None = None
    credit_reason: str | None = None
    credited_entities: dict | None = None

    # Temporal credit assignment (None when not active)
    credit_signal: dict | None = None
    credit_confidence: float | None = None
    credit_applied: bool | None = None
    credit_horizon: int | None = None

    # Forward rollout foresight (None when not active)
    foresight_signal: dict | None = None
    foresight_confidence: float | None = None
    foresight_applied: bool | None = None
    foresight_depth: int | None = None

    # Signal orchestration (None when not active)
    orchestration_consensus: float | None = None
    orchestration_active_count: int | None = None
    orchestration_suppressed_count: int | None = None
    orchestration_dominant_source: str | None = None

    # Signal sensitivity (None when not active)
    sensitivity_factor: float | None = None
    sensitivity_reason: str | None = None
    sensitivity_applied: bool | None = None

    # Action planner (None when not active)
    planner_active: bool | None = None
    planner_scores: dict | None = None
    planner_choice: str | None = None
    planner_confidence: float | None = None
    planner_reason: str | None = None
    planner_horizon: int | None = None
    planner_uncertainty: float | None = None
    planner_consistency: float | None = None
    planner_adjusted_confidence: float | None = None

    # World substrate (None when substrate not active)
    world_snapshot_version: int | None = None
    world_observation_count: int | None = None
    world_entity_count: int | None = None
    world_relation_count: int | None = None
    ingested_signal_count: int | None = None
    ingested_signal_sources: tuple[str, ...] | None = None

    # World reasoning (None when reasoning not active)
    world_derived_count: int | None = None
    world_global_flags: tuple[str, ...] | None = None
    world_riskiest_entity: str | None = None
    world_riskiest_entity_health: str | None = None
    world_volatile_entity_count: int | None = None
    world_bad_entity_count: int | None = None

    # World simulation (None when simulation not active)
    simulation_ran: bool | None = None
    simulated_action_count: int | None = None
    simulated_best_action_id: str | None = None
    simulated_best_improvement: float | None = None
    simulated_best_risk: float | None = None
    simulated_horizon: int | None = None
    simulated_global_flags: tuple[str, ...] | None = None

    # World calibration (None when calibration not active)
    calibration_error: float | None = None
    calibration_confidence: float | None = None
    calibration_trend_bias: float | None = None
    calibration_risk_bias: float | None = None

    # Dynamics adaptation (None when adapter not active)
    dynamics_trend_multiplier: float | None = None
    dynamics_risk_multiplier: float | None = None
    dynamics_stability_modifier: float | None = None
    dynamics_confidence_scale: float | None = None

    # Multi-world policy (None when policy not active)
    policy_world_count: int | None = None
    policy_variance: float | None = None
    policy_worst_case: float | None = None
    policy_robust_score: float | None = None

    # Objective arbitration (None when arbiter not active)
    objective_arb_mode: str | None = None
    objective_arb_reward_weight: float | None = None
    objective_arb_risk_weight: float | None = None
    objective_arb_stability_weight: float | None = None
    objective_arb_shift_reason: str | None = None

    # Strategy pattern memory (None when pattern memory not active)
    strat_pattern_match_found: bool | None = None
    strat_pattern_confidence: float | None = None
    strat_pattern_bias_applied: bool | None = None
    strat_pattern_id: str | None = None

    # Meta-control governance (None when meta-control not active)
    meta_control_mode: str | None = None
    meta_control_agreement: float | None = None
    meta_control_instability: float | None = None
    meta_control_enabled_layers: tuple[str, ...] | None = None

    # Policy / behavioral memory (None when policy tracker not active)
    policy_oscillation_score: float | None = None
    policy_consistency_score: float | None = None
    policy_flags: dict | None = None

    # Intent compilation (None when no intent compiled this turn)
    intent_source: str | None = None
    intent_compiled_weights: dict | None = None
    intent_applied_biases: dict | None = None

    # Universal action schema (None when schema translation not active)
    executable_action_id: str | None = None
    executable_action_type: str | None = None
    executable_action_name: str | None = None
    executable_target: str | None = None
    executable_domain: str | None = None
    executable_warnings: tuple[str, ...] | None = None

    # Execution routing (None when routing not active)
    execution_status: str | None = None
    execution_handler: str | None = None
    execution_resolution_path: str | None = None
    execution_error: str | None = None

    # Execution feedback (None when feedback not active)
    feedback_outcome_type: str | None = None
    feedback_signal_strength: float | None = None
    feedback_action_id: str | None = None
    feedback_ingested: bool | None = None
    feedback_warnings: tuple[str, ...] | None = None

    # Execution credit assignment (None when credit not computed)
    credit_score: float | None = None
    credit_attribution: float | None = None
    effective_credit: float | None = None
    learning_signal_applied: bool | None = None
    learning_signal_strength: float | None = None

    # Strategy abstraction (None when abstraction not active)
    strategy_prototype_id: str | None = None
    strategy_match_score: float | None = None
    strategy_bias_applied: bool | None = None

    # System graph (None when system execution not active)
    system_graph_id: str | None = None
    system_node_execution_order: tuple[str, ...] | None = None
    system_node_statuses: dict[str, str] | None = None
    system_status: str | None = None

    # Environment routing (None when environment routing not active)
    environment: str | None = None
    adapter_used: str | None = None
    adapter_result_status: bool | None = None
    adapter_latency: int | None = None

    # System registry (None when registry not active)
    system_template_used: str | None = None
    system_match_score: float | None = None
    system_source: str | None = None  # "template" | "constructed" | None

    def to_dict(self) -> dict:
        d = {
            "turn_id": self.turn_id,
            "strategies_considered": list(self.strategies_considered),
            "strategy_scores": self.strategy_scores,
            "selected_strategy": self.selected_strategy,
            "quality_score": self.quality_score,
            "confidence": self.confidence,
            "signals": self.signals,
            "attributed_signals": self.attributed_signals,
            "horizon": self.horizon,
            "directives_applied": list(self.directives_applied),
            "model_used": self.model_used,
            "latency_ms": self.latency_ms,
            "tokens_used": self.tokens_used,
            "was_enhanced": self.was_enhanced,
        }
        if self.control_decision is not None:
            d["control_decision"] = self.control_decision.to_dict()
        if self.thresholds_used is not None:
            d["thresholds_used"] = self.thresholds_used
        if self.strategy_selection is not None:
            d["strategy_selection"] = self.strategy_selection
        if self.synthesized_strategy is not None:
            d["synthesized_strategy"] = self.synthesized_strategy
            d["synthesis_reason"] = self.synthesis_reason
        if self.goal_mode is not None:
            d["goal_mode"] = self.goal_mode
        if self.convergence_status is not None:
            d["convergence_status"] = self.convergence_status
            d["convergence_reason"] = self.convergence_reason
            d["convergence_action"] = self.convergence_action
        if self.unified_influence is not None:
            d["unified_influence"] = self.unified_influence
        if self.goal_score is not None:
            d["goal_score"] = round(self.goal_score, 4)
            d["goal_delta"] = round(self.goal_delta or 0.0, 4)
            d["goal_confidence"] = round(self.goal_confidence or 0.0, 4)
        if self.exploration_enabled is not None:
            d["exploration_enabled"] = self.exploration_enabled
        if self.synthesis_enabled is not None:
            d["synthesis_enabled"] = self.synthesis_enabled
        if self.goal_gating_reason is not None:
            d["goal_gating_reason"] = self.goal_gating_reason
        if self.active_goal_id is not None:
            d["active_goal_id"] = self.active_goal_id
        if self.goal_pool_snapshot is not None:
            d["goal_pool_snapshot"] = self.goal_pool_snapshot
        if self.blended_goals is not None:
            d["blended_goals"] = [(gid, round(w, 4)) for gid, w in self.blended_goals]
        if self.blended_primary_goal_id is not None:
            d["blended_primary_goal_id"] = self.blended_primary_goal_id
        if self.blended_entropy is not None:
            d["blended_entropy"] = round(self.blended_entropy, 4)
        if self.execution_budget is not None:
            d["execution_budget"] = self.execution_budget
        if self.candidate_distribution is not None:
            d["candidate_distribution"] = self.candidate_distribution
        if self.memory_persisted is not None:
            d["memory_persisted"] = self.memory_persisted
        if self.memory_version is not None:
            d["memory_version"] = self.memory_version
        if self.persistence_loaded is not None:
            d["persistence_loaded"] = self.persistence_loaded
        if self.persistence_saved is not None:
            d["persistence_saved"] = self.persistence_saved
        if self.persistence_version is not None:
            d["persistence_version"] = self.persistence_version
        if self.persisted_components is not None:
            d["persisted_components"] = list(self.persisted_components)
        if self.persistence_error is not None:
            d["persistence_error"] = self.persistence_error
        if self.outcome_attached is not None:
            d["outcome_attached"] = self.outcome_attached
        if self.outcome_score is not None:
            d["outcome_score"] = round(self.outcome_score, 4)
        if self.attribution_weights is not None:
            d["attribution_weights"] = self.attribution_weights
        if self.attribution_reason is not None:
            d["attribution_reason"] = self.attribution_reason
        if self.exploration_rate is not None:
            d["exploration_rate"] = round(self.exploration_rate, 4)
        if self.exploration_reason is not None:
            d["exploration_reason"] = self.exploration_reason
        if self.det_exploration_active is not None:
            d["det_exploration_active"] = self.det_exploration_active
        if self.det_exploration_adjustments is not None:
            d["det_exploration_adjustments"] = self.det_exploration_adjustments
        if self.generated_goals is not None:
            d["generated_goals"] = list(self.generated_goals)
        if self.goal_mutations is not None:
            d["goal_mutations"] = list(self.goal_mutations)
        if self.meta_goal_reason is not None:
            d["meta_goal_reason"] = self.meta_goal_reason
        if self.goal_validation_results is not None:
            d["goal_validation_results"] = list(self.goal_validation_results)
        if self.rejected_goals is not None:
            d["rejected_goals"] = list(self.rejected_goals)
        if self.validation_reason is not None:
            d["validation_reason"] = self.validation_reason
        if self.goal_alignment_scores is not None:
            d["goal_alignment_scores"] = self.goal_alignment_scores
        if self.alignment_penalties is not None:
            d["alignment_penalties"] = list(self.alignment_penalties)
        if self.alignment_decisions is not None:
            d["alignment_decisions"] = list(self.alignment_decisions)
        if self.counterfactual_expected_utility is not None:
            d["counterfactual_expected_utility"] = self.counterfactual_expected_utility
        if self.counterfactual_confidence is not None:
            d["counterfactual_confidence"] = self.counterfactual_confidence
        if self.counterfactual_reasoning is not None:
            d["counterfactual_reasoning"] = self.counterfactual_reasoning
        if self.counterfactual_uncertainty is not None:
            d["counterfactual_uncertainty"] = self.counterfactual_uncertainty
        if self.counterfactual_exploration_boost is not None:
            d["counterfactual_exploration_boost"] = (
                self.counterfactual_exploration_boost
            )
        if self.counterfactual_horizon_value is not None:
            d["counterfactual_horizon_value"] = self.counterfactual_horizon_value
        if self.counterfactual_horizon_reason is not None:
            d["counterfactual_horizon_reason"] = self.counterfactual_horizon_reason
        if self.persistence_streaks is not None:
            d["persistence_streaks"] = self.persistence_streaks
        if self.commitment_bonuses is not None:
            d["commitment_bonuses"] = self.commitment_bonuses
        if self.switch_penalty_applied is not None:
            d["switch_penalty_applied"] = self.switch_penalty_applied
        if self.strategy_mutations is not None:
            d["strategy_mutations"] = list(self.strategy_mutations)
        if self.strategy_origins is not None:
            d["strategy_origins"] = self.strategy_origins
        if self.mutation_reason is not None:
            d["mutation_reason"] = self.mutation_reason
        if self.active_plan_id is not None:
            d["active_plan_id"] = self.active_plan_id
        if self.active_plan_step is not None:
            d["active_plan_step"] = self.active_plan_step
        if self.plan_confidence is not None:
            d["plan_confidence"] = round(self.plan_confidence, 4)
        if self.plan_count is not None:
            d["plan_count"] = self.plan_count
        if self.plan_generation_reason is not None:
            d["plan_generation_reason"] = self.plan_generation_reason
        if self.world_state_id is not None:
            d["world_state_id"] = self.world_state_id
        if self.world_state_cluster is not None:
            d["world_state_cluster"] = self.world_state_cluster
        if self.world_state_similarity is not None:
            d["world_state_similarity"] = round(self.world_state_similarity, 4)
        if self.conditioning_bias is not None:
            d["conditioning_bias"] = self.conditioning_bias
        if self.strategy_base_scores is not None:
            d["strategy_base_scores"] = self.strategy_base_scores
        if self.strategy_conditioned_scores is not None:
            d["strategy_conditioned_scores"] = self.strategy_conditioned_scores
        if self.plan_step_goal_id is not None:
            d["plan_step_goal_id"] = self.plan_step_goal_id
        if self.plan_step_attributed_score is not None:
            d["plan_step_attributed_score"] = round(self.plan_step_attributed_score, 4)
        if self.plan_step_attribution_source is not None:
            d["plan_step_attribution_source"] = self.plan_step_attribution_source
        if self.plan_step_status is not None:
            d["plan_step_status"] = self.plan_step_status
        if self.plan_step_retry_count is not None:
            d["plan_step_retry_count"] = self.plan_step_retry_count
        if self.plan_step_failure_streak is not None:
            d["plan_step_failure_streak"] = self.plan_step_failure_streak
        if self.state_transfer_weight is not None:
            d["state_transfer_weight"] = round(self.state_transfer_weight, 4)
        if self.strategy_transfer_scores is not None:
            d["strategy_transfer_scores"] = self.strategy_transfer_scores
        if self.plan_transfer_score is not None:
            d["plan_transfer_score"] = round(self.plan_transfer_score, 4)
        if self.state_similarity_used is not None:
            d["state_similarity_used"] = round(self.state_similarity_used, 4)
        if self.replan_adjustment is not None:
            d["replan_adjustment"] = round(self.replan_adjustment, 4)
        if self.plan_mutation_applied is not None:
            d["plan_mutation_applied"] = self.plan_mutation_applied
        if self.plan_mutation_type is not None:
            d["plan_mutation_type"] = self.plan_mutation_type
        if self.mutated_plan_id is not None:
            d["mutated_plan_id"] = self.mutated_plan_id
        if self.mutated_from_plan_id is not None:
            d["mutated_from_plan_id"] = self.mutated_from_plan_id
        if self.plan_recombination_applied is not None:
            d["plan_recombination_applied"] = self.plan_recombination_applied
        if self.recombined_plan_id is not None:
            d["recombined_plan_id"] = self.recombined_plan_id
        if self.recombined_from_plan_ids is not None:
            d["recombined_from_plan_ids"] = list(self.recombined_from_plan_ids)
        if self.plan_evolution_reason is not None:
            d["plan_evolution_reason"] = self.plan_evolution_reason
        if self.plan_origin_snapshot is not None:
            d["plan_origin_snapshot"] = self.plan_origin_snapshot
        if self.world_state_cluster_quality is not None:
            d["world_state_cluster_quality"] = round(
                self.world_state_cluster_quality, 4
            )
        if self.learned_state_bias is not None:
            d["learned_state_bias"] = self.learned_state_bias
        if self.combined_state_bias is not None:
            d["combined_state_bias"] = self.combined_state_bias
        if self.cluster_quality_ema is not None:
            d["cluster_quality_ema"] = round(self.cluster_quality_ema, 4)
        if self.cluster_observation_count is not None:
            d["cluster_observation_count"] = self.cluster_observation_count
        if self.world_state_reinforcement_applied is not None:
            d["world_state_reinforcement_applied"] = (
                self.world_state_reinforcement_applied
            )
        if self.influence_components is not None:
            d["influence_components"] = list(self.influence_components)
        if self.influence_weights is not None:
            d["influence_weights"] = self.influence_weights
        if self.final_influence_score is not None:
            d["final_influence_score"] = round(self.final_influence_score, 4)
        if self.influence_breakdown is not None:
            d["influence_breakdown"] = self.influence_breakdown
        if self.influence_applied is not None:
            d["influence_applied"] = self.influence_applied
        if self.influence_adjustment is not None:
            d["influence_adjustment"] = round(self.influence_adjustment, 4)
        if self.influence_pre_score is not None:
            d["influence_pre_score"] = round(self.influence_pre_score, 4)
        if self.influence_post_score is not None:
            d["influence_post_score"] = round(self.influence_post_score, 4)
        if self.meta_weights is not None:
            d["meta_weights"] = {k: round(v, 4) for k, v in self.meta_weights.items()}
        if self.meta_weight_adjustments is not None:
            d["meta_weight_adjustments"] = {
                k: round(v, 4) for k, v in self.meta_weight_adjustments.items()
            }
        if self.meta_weight_signal_performance is not None:
            d["meta_weight_signal_performance"] = self.meta_weight_signal_performance
        if self.active_policy is not None:
            d["active_policy"] = self.active_policy
        if self.policy_reason is not None:
            d["policy_reason"] = self.policy_reason
        if self.policy_adjustments is not None:
            d["policy_adjustments"] = self.policy_adjustments
        if self.active_directives is not None:
            d["active_directives"] = list(self.active_directives)
        if self.directive_scores is not None:
            d["directive_scores"] = {
                k: round(v, 4) for k, v in self.directive_scores.items()
            }
        if self.directive_selection_reason is not None:
            d["directive_selection_reason"] = self.directive_selection_reason
        if self.directive_evolution_events is not None:
            d["directive_evolution_events"] = list(self.directive_evolution_events)
        if self.memory_entries_written is not None:
            d["memory_entries_written"] = list(self.memory_entries_written)
        if self.memory_queries_used is not None:
            d["memory_queries_used"] = list(self.memory_queries_used)
        if self.memory_aggregation_summary is not None:
            d["memory_aggregation_summary"] = self.memory_aggregation_summary
        if self.fabric_analytics_summary is not None:
            d["fabric_analytics_summary"] = self.fabric_analytics_summary
        if self.analytics_signal is not None:
            d["analytics_signal"] = self.analytics_signal
        if self.analytics_applied is not None:
            d["analytics_applied"] = self.analytics_applied
        if self.objective_snapshot is not None:
            d["objective_snapshot"] = self.objective_snapshot
        if self.objective_value is not None:
            d["objective_value"] = round(self.objective_value, 4)
        if self.objective_trend is not None:
            d["objective_trend"] = self.objective_trend
        if self.optimization_signal is not None:
            d["optimization_signal"] = self.optimization_signal
        if self.objective_history_length is not None:
            d["objective_history_length"] = self.objective_history_length
        if self.objective_persisted is not None:
            d["objective_persisted"] = self.objective_persisted
        if self.objective_decision_signal is not None:
            d["objective_decision_signal"] = self.objective_decision_signal
        if self.trap_signal_active is not None:
            d["trap_signal_active"] = self.trap_signal_active
        if self.trap_adjustment is not None:
            d["trap_adjustment"] = round(self.trap_adjustment, 6)
        if self.restart_state_loaded is not None:
            d["restart_state_loaded"] = self.restart_state_loaded
        if self.meta_signal_strength is not None:
            d["meta_signal_strength"] = round(self.meta_signal_strength, 6)
        if self.stability_guard_active is not None:
            d["stability_guard_active"] = self.stability_guard_active
        if self.context_signal is not None:
            d["context_signal"] = self.context_signal
        if self.context_type is not None:
            d["context_type"] = self.context_type
        if self.meta_generalization_matched is not None:
            d["meta_generalization_matched"] = self.meta_generalization_matched
        if self.meta_generalization_prototype_id is not None:
            d["meta_generalization_prototype_id"] = (
                self.meta_generalization_prototype_id
            )
        if self.meta_generalization_similarity is not None:
            d["meta_generalization_similarity"] = round(
                self.meta_generalization_similarity, 4
            )
        if self.meta_generalization_priors is not None:
            d["meta_generalization_priors"] = {
                k: round(v, 6) for k, v in self.meta_generalization_priors.items()
            }
        if self.meta_generalization_signature is not None:
            d["meta_generalization_signature"] = self.meta_generalization_signature
        if self.meta_generalization_prototype_usage is not None:
            d["meta_generalization_prototype_usage"] = (
                self.meta_generalization_prototype_usage
            )
        if self.meta_generalization_prototype_avg_reward is not None:
            d["meta_generalization_prototype_avg_reward"] = round(
                self.meta_generalization_prototype_avg_reward, 4
            )
        if self.meta_generalization_suppressed is not None:
            d["meta_generalization_suppressed"] = self.meta_generalization_suppressed
        if self.causal_signal is not None:
            d["causal_signal"] = self.causal_signal
        if self.causal_confidence is not None:
            d["causal_confidence"] = round(self.causal_confidence, 4)
        if self.causal_applied is not None:
            d["causal_applied"] = self.causal_applied
        if self.causal_context_match is not None:
            d["causal_context_match"] = self.causal_context_match
        if self.causal_credit is not None:
            d["causal_credit"] = self.causal_credit
        if self.immediate_credit is not None:
            d["immediate_credit"] = self.immediate_credit
        if self.delayed_credit is not None:
            d["delayed_credit"] = self.delayed_credit
        if self.structural_credit is not None:
            d["structural_credit"] = self.structural_credit
        if self.credit_reason is not None:
            d["credit_reason"] = self.credit_reason
        if self.credited_entities is not None:
            d["credited_entities"] = self.credited_entities
        if self.credit_signal is not None:
            d["credit_signal"] = self.credit_signal
        if self.credit_confidence is not None:
            d["credit_confidence"] = round(self.credit_confidence, 4)
        if self.credit_applied is not None:
            d["credit_applied"] = self.credit_applied
        if self.credit_horizon is not None:
            d["credit_horizon"] = self.credit_horizon
        if self.foresight_signal is not None:
            d["foresight_signal"] = self.foresight_signal
        if self.foresight_confidence is not None:
            d["foresight_confidence"] = round(self.foresight_confidence, 4)
        if self.foresight_applied is not None:
            d["foresight_applied"] = self.foresight_applied
        if self.foresight_depth is not None:
            d["foresight_depth"] = self.foresight_depth
        if self.orchestration_consensus is not None:
            d["orchestration_consensus"] = round(self.orchestration_consensus, 4)
        if self.orchestration_active_count is not None:
            d["orchestration_active_count"] = self.orchestration_active_count
        if self.orchestration_suppressed_count is not None:
            d["orchestration_suppressed_count"] = self.orchestration_suppressed_count
        if self.orchestration_dominant_source is not None:
            d["orchestration_dominant_source"] = self.orchestration_dominant_source
        if self.sensitivity_factor is not None:
            d["sensitivity_factor"] = round(self.sensitivity_factor, 4)
        if self.sensitivity_reason is not None:
            d["sensitivity_reason"] = self.sensitivity_reason
        if self.sensitivity_applied is not None:
            d["sensitivity_applied"] = self.sensitivity_applied
        if self.planner_active is not None:
            d["planner_active"] = self.planner_active
        if self.planner_scores is not None:
            d["planner_scores"] = {
                k: round(v, 6) for k, v in self.planner_scores.items()
            }
        if self.planner_choice is not None:
            d["planner_choice"] = self.planner_choice
        if self.planner_confidence is not None:
            d["planner_confidence"] = round(self.planner_confidence, 4)
        if self.planner_reason is not None:
            d["planner_reason"] = self.planner_reason
        if self.planner_horizon is not None:
            d["planner_horizon"] = self.planner_horizon
        if self.planner_uncertainty is not None:
            d["planner_uncertainty"] = round(self.planner_uncertainty, 4)
        if self.planner_consistency is not None:
            d["planner_consistency"] = round(self.planner_consistency, 4)
        if self.planner_adjusted_confidence is not None:
            d["planner_adjusted_confidence"] = round(
                self.planner_adjusted_confidence, 4
            )
        if self.world_snapshot_version is not None:
            d["world_snapshot_version"] = self.world_snapshot_version
        if self.world_observation_count is not None:
            d["world_observation_count"] = self.world_observation_count
        if self.world_entity_count is not None:
            d["world_entity_count"] = self.world_entity_count
        if self.world_relation_count is not None:
            d["world_relation_count"] = self.world_relation_count
        if self.ingested_signal_count is not None:
            d["ingested_signal_count"] = self.ingested_signal_count
        if self.ingested_signal_sources is not None:
            d["ingested_signal_sources"] = list(self.ingested_signal_sources)
        if self.world_derived_count is not None:
            d["world_derived_count"] = self.world_derived_count
        if self.world_global_flags is not None:
            d["world_global_flags"] = list(self.world_global_flags)
        if self.world_riskiest_entity is not None:
            d["world_riskiest_entity"] = self.world_riskiest_entity
        if self.world_riskiest_entity_health is not None:
            d["world_riskiest_entity_health"] = self.world_riskiest_entity_health
        if self.world_volatile_entity_count is not None:
            d["world_volatile_entity_count"] = self.world_volatile_entity_count
        if self.world_bad_entity_count is not None:
            d["world_bad_entity_count"] = self.world_bad_entity_count
        if self.simulation_ran is not None:
            d["simulation_ran"] = self.simulation_ran
        if self.simulated_action_count is not None:
            d["simulated_action_count"] = self.simulated_action_count
        if self.simulated_best_action_id is not None:
            d["simulated_best_action_id"] = self.simulated_best_action_id
        if self.simulated_best_improvement is not None:
            d["simulated_best_improvement"] = round(self.simulated_best_improvement, 4)
        if self.simulated_best_risk is not None:
            d["simulated_best_risk"] = round(self.simulated_best_risk, 4)
        if self.simulated_horizon is not None:
            d["simulated_horizon"] = self.simulated_horizon
        if self.simulated_global_flags is not None:
            d["simulated_global_flags"] = list(self.simulated_global_flags)
        if self.calibration_error is not None:
            d["calibration_error"] = round(self.calibration_error, 6)
        if self.calibration_confidence is not None:
            d["calibration_confidence"] = round(self.calibration_confidence, 6)
        if self.calibration_trend_bias is not None:
            d["calibration_trend_bias"] = round(self.calibration_trend_bias, 6)
        if self.calibration_risk_bias is not None:
            d["calibration_risk_bias"] = round(self.calibration_risk_bias, 6)
        if self.dynamics_trend_multiplier is not None:
            d["dynamics_trend_multiplier"] = round(self.dynamics_trend_multiplier, 6)
        if self.dynamics_risk_multiplier is not None:
            d["dynamics_risk_multiplier"] = round(self.dynamics_risk_multiplier, 6)
        if self.dynamics_stability_modifier is not None:
            d["dynamics_stability_modifier"] = round(
                self.dynamics_stability_modifier, 6
            )
        if self.dynamics_confidence_scale is not None:
            d["dynamics_confidence_scale"] = round(self.dynamics_confidence_scale, 6)
        if self.policy_world_count is not None:
            d["policy_world_count"] = self.policy_world_count
        if self.policy_variance is not None:
            d["policy_variance"] = round(self.policy_variance, 6)
        if self.policy_worst_case is not None:
            d["policy_worst_case"] = round(self.policy_worst_case, 6)
        if self.policy_robust_score is not None:
            d["policy_robust_score"] = round(self.policy_robust_score, 6)
        if self.objective_arb_mode is not None:
            d["objective_arb_mode"] = self.objective_arb_mode
        if self.objective_arb_reward_weight is not None:
            d["objective_arb_reward_weight"] = round(
                self.objective_arb_reward_weight, 6
            )
        if self.objective_arb_risk_weight is not None:
            d["objective_arb_risk_weight"] = round(self.objective_arb_risk_weight, 6)
        if self.objective_arb_stability_weight is not None:
            d["objective_arb_stability_weight"] = round(
                self.objective_arb_stability_weight, 6
            )
        if self.objective_arb_shift_reason is not None:
            d["objective_arb_shift_reason"] = self.objective_arb_shift_reason
        if self.strat_pattern_match_found is not None:
            d["strat_pattern_match_found"] = self.strat_pattern_match_found
        if self.strat_pattern_confidence is not None:
            d["strat_pattern_confidence"] = round(self.strat_pattern_confidence, 6)
        if self.strat_pattern_bias_applied is not None:
            d["strat_pattern_bias_applied"] = self.strat_pattern_bias_applied
        if self.strat_pattern_id is not None:
            d["strat_pattern_id"] = self.strat_pattern_id
        if self.meta_control_mode is not None:
            d["meta_control_mode"] = self.meta_control_mode
        if self.meta_control_agreement is not None:
            d["meta_control_agreement"] = round(self.meta_control_agreement, 6)
        if self.meta_control_instability is not None:
            d["meta_control_instability"] = round(self.meta_control_instability, 6)
        if self.meta_control_enabled_layers is not None:
            d["meta_control_enabled_layers"] = list(self.meta_control_enabled_layers)
        if self.policy_oscillation_score is not None:
            d["policy_oscillation_score"] = round(self.policy_oscillation_score, 6)
        if self.policy_consistency_score is not None:
            d["policy_consistency_score"] = round(self.policy_consistency_score, 6)
        if self.policy_flags is not None:
            d["policy_flags"] = self.policy_flags
        if self.intent_source is not None:
            d["intent_source"] = self.intent_source
        if self.intent_compiled_weights is not None:
            d["intent_compiled_weights"] = self.intent_compiled_weights
        if self.intent_applied_biases is not None:
            d["intent_applied_biases"] = self.intent_applied_biases
        if self.executable_action_id is not None:
            d["executable_action_id"] = self.executable_action_id
        if self.executable_action_type is not None:
            d["executable_action_type"] = self.executable_action_type
        if self.executable_action_name is not None:
            d["executable_action_name"] = self.executable_action_name
        if self.executable_target is not None:
            d["executable_target"] = self.executable_target
        if self.executable_domain is not None:
            d["executable_domain"] = self.executable_domain
        if self.executable_warnings is not None:
            d["executable_warnings"] = list(self.executable_warnings)
        if self.execution_status is not None:
            d["execution_status"] = self.execution_status
        if self.execution_handler is not None:
            d["execution_handler"] = self.execution_handler
        if self.execution_resolution_path is not None:
            d["execution_resolution_path"] = self.execution_resolution_path
        if self.execution_error is not None:
            d["execution_error"] = self.execution_error
        if self.feedback_outcome_type is not None:
            d["feedback_outcome_type"] = self.feedback_outcome_type
        if self.feedback_signal_strength is not None:
            d["feedback_signal_strength"] = round(self.feedback_signal_strength, 4)
        if self.feedback_action_id is not None:
            d["feedback_action_id"] = self.feedback_action_id
        if self.feedback_ingested is not None:
            d["feedback_ingested"] = self.feedback_ingested
        if self.feedback_warnings is not None:
            d["feedback_warnings"] = list(self.feedback_warnings)
        if self.credit_score is not None:
            d["credit_score"] = round(self.credit_score, 4)
        if self.credit_attribution is not None:
            d["credit_attribution"] = round(self.credit_attribution, 4)
        if self.effective_credit is not None:
            d["effective_credit"] = round(self.effective_credit, 4)
        if self.learning_signal_applied is not None:
            d["learning_signal_applied"] = self.learning_signal_applied
        if self.learning_signal_strength is not None:
            d["learning_signal_strength"] = round(self.learning_signal_strength, 4)
        if self.strategy_prototype_id is not None:
            d["strategy_prototype_id"] = self.strategy_prototype_id
        if self.strategy_match_score is not None:
            d["strategy_match_score"] = round(self.strategy_match_score, 4)
        if self.strategy_bias_applied is not None:
            d["strategy_bias_applied"] = self.strategy_bias_applied
        if self.system_graph_id is not None:
            d["system_graph_id"] = self.system_graph_id
        if self.system_node_execution_order is not None:
            d["system_node_execution_order"] = list(self.system_node_execution_order)
        if self.system_node_statuses is not None:
            d["system_node_statuses"] = dict(self.system_node_statuses)
        if self.system_status is not None:
            d["system_status"] = self.system_status
        if self.environment is not None:
            d["environment"] = self.environment
        if self.adapter_used is not None:
            d["adapter_used"] = self.adapter_used
        if self.adapter_result_status is not None:
            d["adapter_result_status"] = self.adapter_result_status
        if self.adapter_latency is not None:
            d["adapter_latency"] = self.adapter_latency
        if self.system_template_used is not None:
            d["system_template_used"] = self.system_template_used
        if self.system_match_score is not None:
            d["system_match_score"] = round(self.system_match_score, 4)
        if self.system_source is not None:
            d["system_source"] = self.system_source
        return d


def debug_print(trace: DecisionTrace) -> None:
    """Pretty-print a trace to the log. Disabled by default."""
    lines = [
        f"{'─' * 40}",
        f"  DecisionTrace turn={trace.turn_id}",
        f"{'─' * 40}",
        f"  strategy:   {trace.selected_strategy}",
        f"  considered: {list(trace.strategies_considered)}",
        f"  scores:     {trace.strategy_scores}",
        f"  quality:    {trace.quality_score:.3f}",
        f"  confidence: {trace.confidence:.3f}",
        f"  horizon:    {trace.horizon}",
        f"  directives: {list(trace.directives_applied)}",
        f"  model:      {trace.model_used}",
        f"  latency:    {trace.latency_ms}ms",
        f"  enhanced:   {trace.was_enhanced}",
        f"{'─' * 40}",
    ]
    _log.info("\n".join(lines))
