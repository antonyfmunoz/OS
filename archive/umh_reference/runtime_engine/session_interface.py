"""SessionInterface — user-facing control surface for the UMH meta-harness.

Accepts high-level intent, drives the full pipeline through step(),
and returns structured DecisionOutput objects. No execution side-effects
beyond what the internal pipeline produces; the interface itself is
deterministic and composable.

Five methods, one flow:

    iface = SessionInterface()
    iface.set_intent(IntentInput(goal="grow revenue", risk_tolerance=0.3))
    output = iface.step("What should I focus on today?")
    state  = iface.get_state()
    last   = iface.get_last_decision()
    iface.reset()

DecisionOutput carries: action, confidence, risk_score, explanation,
and contributing_layers — everything needed to understand what the
system decided and why, without inspecting internal traces.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from typing import Any

_log = logging.getLogger(__name__)


# ─── Output types ─────────────────────────────────────────────────


@dataclass(frozen=True)
class LayerContribution:
    """Single intelligence layer's contribution to a decision."""

    layer_name: str
    influence: float
    detail: str

    def to_dict(self) -> dict:
        return {
            "layer_name": self.layer_name,
            "influence": round(self.influence, 4),
            "detail": self.detail,
        }


@dataclass(frozen=True)
class Explanation:
    """Human-readable explanation of why an action was chosen."""

    summary: str
    contributing_layers: tuple[LayerContribution, ...]
    confidence_rationale: str
    risk_rationale: str

    def to_dict(self) -> dict:
        return {
            "summary": self.summary,
            "contributing_layers": [c.to_dict() for c in self.contributing_layers],
            "confidence_rationale": self.confidence_rationale,
            "risk_rationale": self.risk_rationale,
        }


@dataclass(frozen=True)
class DecisionOutput:
    """Structured output from a single step() call."""

    action: str
    confidence: float
    risk_score: float
    explanation: Explanation
    contributing_layers: tuple[str, ...]
    turn_id: int
    model_used: str
    latency_ms: int

    def to_dict(self) -> dict:
        return {
            "action": self.action,
            "confidence": round(self.confidence, 4),
            "risk_score": round(self.risk_score, 4),
            "explanation": self.explanation.to_dict(),
            "contributing_layers": list(self.contributing_layers),
            "turn_id": self.turn_id,
            "model_used": self.model_used,
            "latency_ms": self.latency_ms,
        }


@dataclass(frozen=True)
class InterfaceState:
    """Snapshot of the interface's current operational state."""

    mode: str
    policy_flags: dict[str, bool]
    stability_score: float
    intent_weights: dict[str, float]
    turn_count: int
    session_id: str
    total_cost_usd: float

    def to_dict(self) -> dict:
        return {
            "mode": self.mode,
            "policy_flags": dict(self.policy_flags),
            "stability_score": round(self.stability_score, 4),
            "intent_weights": {k: round(v, 4) for k, v in self.intent_weights.items()},
            "turn_count": self.turn_count,
            "session_id": self.session_id,
            "total_cost_usd": round(self.total_cost_usd, 4),
        }


# ─── Explanation builder ─────────────────────────────────────────


def _build_explanation(
    trace: object | None,
    result: object | None,
    control_decision: object | None,
) -> Explanation:
    """Build a human-readable explanation from a DecisionTrace."""
    layers: list[LayerContribution] = []

    if trace is None:
        return Explanation(
            summary="No trace available — response produced without instrumentation.",
            contributing_layers=(),
            confidence_rationale="unknown",
            risk_rationale="unknown",
        )

    # Strategy selection
    selected = getattr(trace, "selected_strategy", "")
    scores = getattr(trace, "strategy_scores", {})
    if selected:
        score = scores.get(selected, 0.0)
        layers.append(
            LayerContribution(
                layer_name="strategy_selection",
                influence=score,
                detail=f"Selected '{selected}' (score {score:.2f}) from {len(scores)} candidates.",
            )
        )

    # Control layer
    if control_decision is not None:
        intervene = getattr(control_decision, "intervene", False)
        reason = getattr(control_decision, "reason", "")
        layers.append(
            LayerContribution(
                layer_name="control_layer",
                influence=1.0 if intervene else 0.0,
                detail=f"{'Intervened' if intervene else 'No intervention'}: {reason}",
            )
        )

    # Goal blending
    blended = getattr(trace, "blended_goals", None)
    primary = getattr(trace, "blended_primary_goal_id", None)
    if blended and primary:
        layers.append(
            LayerContribution(
                layer_name="goal_blending",
                influence=getattr(trace, "blended_entropy", 0.0) or 0.0,
                detail=f"Primary goal '{primary}', {len(blended)} goals in blend.",
            )
        )

    # Exploration
    exp_rate = getattr(trace, "exploration_rate", None)
    exp_reason = getattr(trace, "exploration_reason", None)
    if exp_rate is not None:
        layers.append(
            LayerContribution(
                layer_name="exploration",
                influence=exp_rate,
                detail=exp_reason or f"Exploration rate {exp_rate:.2f}.",
            )
        )

    # Unified influence
    influence_score = getattr(trace, "final_influence_score", None)
    if influence_score is not None:
        layers.append(
            LayerContribution(
                layer_name="unified_influence",
                influence=influence_score,
                detail=f"Combined influence score {influence_score:.3f}.",
            )
        )

    # World simulation
    sim_action = getattr(trace, "simulated_best_action_id", None)
    sim_improvement = getattr(trace, "simulated_best_improvement", None)
    if sim_action:
        layers.append(
            LayerContribution(
                layer_name="world_simulation",
                influence=sim_improvement or 0.0,
                detail=f"Best simulated action: {sim_action} (improvement {sim_improvement or 0:.3f}).",
            )
        )

    # Meta-control mode
    mc_mode = getattr(trace, "meta_control_mode", None)
    mc_agreement = getattr(trace, "meta_control_agreement", None)
    if mc_mode:
        layers.append(
            LayerContribution(
                layer_name="meta_control",
                influence=mc_agreement or 0.0,
                detail=f"Mode '{mc_mode}', agreement {mc_agreement or 0:.2f}.",
            )
        )

    # Build summary
    quality = getattr(trace, "quality_score", 0.0) or 0.0
    confidence = getattr(trace, "confidence", 0.0) or 0.0

    summary_parts = []
    if selected:
        summary_parts.append(f"Strategy: {selected}.")
    if primary:
        summary_parts.append(f"Goal: {primary}.")
    if mc_mode:
        summary_parts.append(f"Mode: {mc_mode}.")
    summary_parts.append(f"Quality: {quality:.2f}, confidence: {confidence:.2f}.")
    summary = " ".join(summary_parts) if summary_parts else "Decision produced."

    # Confidence rationale
    conf_parts = [f"Base confidence: {confidence:.2f}."]
    cal_conf = getattr(trace, "calibration_confidence", None)
    if cal_conf is not None:
        conf_parts.append(f"Calibrated: {cal_conf:.2f}.")
    if mc_agreement is not None:
        conf_parts.append(f"Layer agreement: {mc_agreement:.2f}.")
    confidence_rationale = " ".join(conf_parts)

    # Risk rationale
    risk_parts = []
    risk_score = _compute_risk_score(trace)
    if risk_score > 0.7:
        risk_parts.append("HIGH risk — low confidence or high instability.")
    elif risk_score > 0.4:
        risk_parts.append("MODERATE risk — some uncertainty in signals.")
    else:
        risk_parts.append("LOW risk — signals aligned and confident.")
    instability = getattr(trace, "meta_control_instability", None)
    if instability is not None:
        risk_parts.append(f"Instability: {instability:.2f}.")
    risk_rationale = " ".join(risk_parts) if risk_parts else "No risk signals."

    return Explanation(
        summary=summary,
        contributing_layers=tuple(layers),
        confidence_rationale=confidence_rationale,
        risk_rationale=risk_rationale,
    )


def _compute_risk_score(trace: object) -> float:
    """Derive a 0-1 risk score from trace signals. Deterministic."""
    _conf = getattr(trace, "confidence", None)
    confidence = _conf if _conf is not None else 0.5
    _inst = getattr(trace, "meta_control_instability", None)
    instability = _inst if _inst is not None else 0.0
    _qual = getattr(trace, "quality_score", None)
    quality = _qual if _qual is not None else 0.5

    # risk = inverse confidence weighted with instability
    inv_confidence = 1.0 - confidence
    inv_quality = 1.0 - quality
    risk = (inv_confidence * 0.4) + (instability * 0.3) + (inv_quality * 0.3)
    return max(0.0, min(1.0, risk))


# ─── SessionInterface ─────────────────────────────────────────────


class SessionInterface:
    """User-facing control surface for the UMH meta-harness.

    Wraps SessionRuntime + ContextBuilder and exposes 5 methods:
    set_intent, step, get_state, get_last_decision, reset.

    No execution side-effects beyond what the internal pipeline produces.
    The interface itself adds no state mutations, no LLM calls, no I/O.
    """

    def __init__(
        self,
        ctx: object | None = None,
        session_id: str | None = None,
        control_enabled: bool = True,
        calibration_enabled: bool = True,
        convergence_enabled: bool = True,
        persist_memory: bool = False,
    ) -> None:
        self._session_id = session_id or str(uuid.uuid4())
        self._ctx = ctx
        self._decisions: list[DecisionOutput] = []
        self._intent: object | None = None

        # Lazy-init runtime and context — constructed on first step()
        # so that SessionInterface can be imported and tested without
        # requiring full UMH infrastructure.
        self._runtime: object | None = None
        self._builder: object | None = None
        self._last_adapted_input: object | None = None
        self._last_executable_action: object | None = None
        self._last_execution_result: object | None = None
        self._last_execution_feedback: object | None = None
        self._last_feedback_observation: object | None = None
        self._last_credit_result: object | None = None
        self._last_strategy_bias: object | None = None
        self._last_system_result: object | None = None
        self._last_environment_route: object | None = None
        self._last_adapter_result: object | None = None
        self._last_system_selection: object | None = None
        self._prototype_store: object | None = None
        self._system_registry: object | None = None
        self._control_enabled = control_enabled
        self._calibration_enabled = calibration_enabled
        self._convergence_enabled = convergence_enabled
        self._persist_memory = persist_memory

    def _ensure_runtime(self) -> None:
        """Lazily construct SessionRuntime and ContextBuilder."""
        if self._runtime is not None:
            return

        if self._ctx is None:
            from umh.environments.system_context import load_context_from_env

            self._ctx = load_context_from_env()

        from umh.runtime_engine.session_runtime import SessionRuntime
        from umh.runtime_engine.context_builder import ContextBuilder

        self._runtime = SessionRuntime(
            ctx=self._ctx,
            session_id=self._session_id,
            control_enabled=self._control_enabled,
            calibration_enabled=self._calibration_enabled,
            convergence_enabled=self._convergence_enabled,
            persist_memory=self._persist_memory,
        )
        self._builder = ContextBuilder()

    # ─── set_intent ──────────────────────────────────────────────

    def set_intent(self, intent_input: object) -> object | None:
        """Compile user intent into meta-harness configuration.

        Accepts an IntentInput (from intent_compiler) or any object with
        the same shape. Stores the compiled result and passes it to the
        runtime so subsequent step() calls are influenced.

        Returns the CompiledIntent or None if compilation fails.
        """
        self._ensure_runtime()
        self._intent = intent_input
        result = self._runtime.set_intent(intent_input)
        return result

    # ─── step ────────────────────────────────────────────────────

    def step(
        self,
        observation: str | dict,
        agent_type: str = "executive_assistant",
        authority_class: str = "analyze",
        venture_id: str | None = None,
        task_type: object = None,
        skill_name: str | None = None,
    ) -> DecisionOutput:
        """Ingest an observation, run the full pipeline, return DecisionOutput.

        Accepts either a string observation or a domain-specific dict.
        When a dict is provided, the domain adapter translates it into
        a text observation before running the pipeline.

        Dict format::

            {
                "domain": "business",
                "metrics": {"revenue": 5000, "leads": 12},
                "entity_id": "lyfe_institute",
            }

        Steps:
            1. Adapt input (dict → text via domain adapter, or pass str through)
            2. Build unified context
            3. Run SessionRuntime pipeline
            4. Extract DecisionOutput from trace and result
        """
        self._ensure_runtime()

        # 1. Domain adaptation — dict inputs are translated to text
        if isinstance(observation, dict):
            from umh.runtime_engine.domain_adapter import adapt_input, format_observations_as_text

            adapted = adapt_input(observation)
            self._last_adapted_input = adapted
            observation = format_observations_as_text(adapted)
        else:
            self._last_adapted_input = None

        # 2. Build context
        org_id = getattr(self._ctx, "org_id", None)
        uc = self._builder.build(
            ctx=self._ctx,
            message=observation,
            session_id=self._session_id,
            agent=agent_type,
            venture_id=venture_id,
        )

        # 2. Get calibrated thresholds if available
        thresholds = None
        try:
            thresholds = self._runtime.get_calibrated_thresholds()
        except Exception:
            pass

        # 3. Run pipeline
        result = self._runtime.run(
            message=observation,
            unified_context=uc,
            agent_type=agent_type,
            authority_class=authority_class,
            org_id=org_id,
            task_type=task_type,
            venture_id=venture_id,
            skill_name=skill_name,
            calibrated_thresholds=thresholds,
        )

        # 4. Extract trace
        trace = self._runtime.get_last_trace()
        control_decision = self._runtime.get_last_control_decision()

        # 5. Build explanation
        explanation = _build_explanation(trace, result, control_decision)

        # 6. Compute fields
        confidence = getattr(trace, "confidence", 0.5) if trace else 0.5
        risk_score = _compute_risk_score(trace) if trace else 0.5

        layer_names = tuple(lc.layer_name for lc in explanation.contributing_layers)

        output = DecisionOutput(
            action=str(result),
            confidence=confidence,
            risk_score=risk_score,
            explanation=explanation,
            contributing_layers=layer_names,
            turn_id=self._runtime.stats.turns,
            model_used=getattr(result, "model_used", "unknown"),
            latency_ms=getattr(result, "latency_ms", 0),
        )

        self._decisions.append(output)

        # 7. Action schema translation (when domain adapter produced an ActionPlan)
        self._last_executable_action = None
        self._last_execution_result = None
        self._last_execution_feedback = None
        self._last_feedback_observation = None
        self._last_credit_result = None
        self._last_strategy_bias = None
        self._last_system_result = None
        self._last_environment_route = None
        self._last_adapter_result = None
        self._last_system_selection = None
        if self._last_adapted_input is not None:
            try:
                from umh.runtime_engine.domain_adapter import adapt_output, DomainType
                from umh.runtime_engine.action_schema import to_executable_action

                domain_str = getattr(self._last_adapted_input, "domain", "")
                domain_enum = None
                for dt in DomainType:
                    if dt.value == domain_str:
                        domain_enum = dt
                        break
                if domain_enum is not None:
                    action_plan = adapt_output(output, domain_enum)
                    norm_result = to_executable_action(
                        action_plan=action_plan,
                        domain=domain_str,
                        confidence=output.confidence,
                        trace_id=trace.turn_id if trace else None,
                    )
                    self._last_executable_action = norm_result

                    # 8. Execution routing
                    from umh.runtime_engine.execution_router import (
                        ExecutionRequest,
                        ExecutionRouter,
                    )

                    router = ExecutionRouter()
                    exec_result = router.route(
                        ExecutionRequest(action=norm_result.executable_action)
                    )
                    self._last_execution_result = exec_result

                    # 9. Execution feedback normalization
                    from umh.runtime_engine.execution_feedback import (
                        normalize_execution_feedback,
                    )

                    fb_result = normalize_execution_feedback(
                        exec_result, confidence=output.confidence
                    )
                    self._last_execution_feedback = fb_result.feedback
                    self._last_feedback_observation = fb_result.observation

                    # 10. Execution credit assignment
                    from umh.runtime_engine.execution_credit import compute_full_credit

                    credit_result = compute_full_credit(
                        action=norm_result.executable_action,
                        feedback=fb_result.feedback,
                        trace=trace,
                    )
                    self._last_credit_result = credit_result

                    # 11. Strategy abstraction + transfer
                    from umh.runtime_engine.strategy_abstraction import (
                        StrategyPrototypeStore,
                        generate_strategy_bias,
                    )

                    if self._prototype_store is None:
                        self._prototype_store = StrategyPrototypeStore()
                    bias = generate_strategy_bias(trace, self._prototype_store)
                    self._last_strategy_bias = bias

                    # 12. System graph construction + execution
                    from umh.runtime_engine.system_graph import (
                        build_system_graph,
                        execute_system_graph,
                    )
                    from umh.runtime_engine.action_schema import normalize_full_plan

                    all_norms = normalize_full_plan(
                        action_plan=action_plan,
                        domain=domain_str,
                        confidence=output.confidence,
                        trace_id=trace.turn_id if trace else None,
                    )
                    all_actions = [nr.executable_action for nr in all_norms]
                    sys_graph = None
                    if len(all_actions) > 1:
                        sys_graph = build_system_graph(all_actions)
                        sys_result = execute_system_graph(sys_graph, router)
                        self._last_system_result = sys_result

                    # 13. Environment routing
                    from umh.runtime_engine.execution_adapters import (
                        execute_with_environment,
                    )

                    env_route, adapter_result = execute_with_environment(
                        norm_result.executable_action
                    )
                    self._last_environment_route = env_route
                    self._last_adapter_result = adapter_result

                    # 14. System registry + selection
                    from umh.runtime_engine.system_registry import SystemRegistry
                    from umh.runtime_engine.system_selector import select_system
                    from umh.runtime_engine.strategy_abstraction import (
                        extract_context_signature,
                    )

                    if self._system_registry is None:
                        self._system_registry = SystemRegistry()

                    ctx_sig = extract_context_signature(trace) if trace else {}

                    candidates = self._system_registry.find_candidates(ctx_sig)
                    selection = select_system(ctx_sig, candidates)
                    self._last_system_selection = selection

                    if self._last_system_result is not None and sys_graph is not None:
                        self._system_registry.register(
                            sys_graph, ctx_sig, self._last_system_result
                        )
            except Exception as e:
                _log.debug(
                    "Action schema / routing / feedback / credit / abstraction / system / env failed: %s",
                    e,
                )

        return output

    # ─── get_state ───────────────────────────────────────────────

    def get_state(self) -> InterfaceState:
        """Return the current operational state of the interface.

        Exposes: meta-control mode, policy flags, stability score,
        intent weights, turn count, session id, total cost.
        """
        if self._runtime is None:
            return InterfaceState(
                mode="uninitialized",
                policy_flags={},
                stability_score=1.0,
                intent_weights={},
                turn_count=0,
                session_id=self._session_id,
                total_cost_usd=0.0,
            )

        # Meta-control mode
        mode = "full"
        policy_flags: dict[str, bool] = {}
        stability_score = 1.0

        trace = self._runtime.get_last_trace()
        if trace is not None:
            mc_mode = getattr(trace, "meta_control_mode", None)
            if mc_mode:
                mode = mc_mode
            instability = getattr(trace, "meta_control_instability", 0.0) or 0.0
            stability_score = max(0.0, min(1.0, 1.0 - instability))

            # Extract policy flags from meta-control permissions
            mc_perms = getattr(trace, "meta_control_permissions", None)
            if mc_perms and isinstance(mc_perms, dict):
                policy_flags = {k: bool(v) for k, v in mc_perms.items()}

        # Intent weights
        intent_weights: dict[str, float] = {}
        compiled = getattr(self._runtime, "_compiled_intent", None)
        if compiled is not None:
            ow = getattr(compiled, "objective_weights", None)
            if ow and isinstance(ow, dict):
                intent_weights = {k: float(v) for k, v in ow.items()}

        return InterfaceState(
            mode=mode,
            policy_flags=policy_flags,
            stability_score=stability_score,
            intent_weights=intent_weights,
            turn_count=self._runtime.stats.turns,
            session_id=self._session_id,
            total_cost_usd=self._runtime.stats.total_cost_usd,
        )

    # ─── get_last_decision ───────────────────────────────────────

    def get_last_decision(self) -> DecisionOutput | None:
        """Return the most recent DecisionOutput, or None if no steps taken."""
        return self._decisions[-1] if self._decisions else None

    # ─── get_last_executable_action ─────────────────────────────

    def get_last_executable_action(self) -> object | None:
        """Return the most recent ActionNormalizationResult, or None.

        Only populated when the last step() used a dict input (domain adapter).
        """
        return self._last_executable_action

    # ─── get_last_execution_result ──────────────────────────────

    def get_last_execution_result(self) -> object | None:
        """Return the most recent ExecutionResult, or None.

        Only populated when action schema translation and execution
        routing ran on the last step().
        """
        return self._last_execution_result

    # ─── get_last_execution_feedback ───────────────────────────

    def get_last_execution_feedback(self) -> object | None:
        """Return the most recent ExecutionFeedback, or None.

        Only populated when feedback normalization ran on the last step().
        """
        return self._last_execution_feedback

    # ─── get_last_feedback_observation ──────────────────────────

    def get_last_feedback_observation(self) -> object | None:
        """Return the most recent FeedbackObservation, or None.

        Only populated when feedback normalization ran on the last step().
        """
        return self._last_feedback_observation

    # ──��� get_last_credit_result ────────────────────────────────

    def get_last_credit_result(self) -> object | None:
        """Return the most recent CreditComputationResult, or None.

        Only populated when credit assignment ran on the last step().
        """
        return self._last_credit_result

    # ─── get_last_strategy_bias ────────────────────────────────

    def get_last_strategy_bias(self) -> object | None:
        """Return the most recent StrategyBias, or None.

        Only populated when strategy abstraction ran on the last step().
        """
        return self._last_strategy_bias

    # ─── get_last_system_result ───────────────────────────────

    def get_last_system_result(self) -> object | None:
        """Return the most recent SystemExecutionResult, or None.

        Only populated when system graph execution ran on the last step()
        and the action plan had more than one step.
        """
        return self._last_system_result

    # ─── get_last_environment_route ──────────────────────────

    def get_last_environment_route(self) -> object | None:
        """Return the most recent EnvironmentRoute, or None.

        Only populated when environment routing ran on the last step().
        """
        return self._last_environment_route

    # ─── get_last_adapter_result ─────────────────────────────

    def get_last_adapter_result(self) -> object | None:
        """Return the most recent AdapterResult, or None.

        Only populated when environment-routed execution ran on the last step().
        """
        return self._last_adapter_result

    # ─── get_last_system_selection ───────���────────────────────

    def get_last_system_selection(self) -> object | None:
        """Return the most recent SystemSelectionResult, or None.

        Only populated when system registry selection ran on the last step().
        """
        return self._last_system_selection

    # ─── reset ───────────────────────────────────────────────────

    def reset(self, preserve_memory: bool = False) -> None:
        """Reset runtime state for a new session.

        When preserve_memory is True, persisted learned state (world
        substrate, objective history, strategy patterns) survives the
        reset. When False, everything is cleared.
        """
        self._decisions.clear()
        self._intent = None
        self._last_executable_action = None
        self._last_execution_result = None
        self._last_execution_feedback = None
        self._last_feedback_observation = None
        self._last_credit_result = None
        self._last_strategy_bias = None
        self._last_system_result = None
        self._last_environment_route = None
        self._last_adapter_result = None
        self._last_system_selection = None

        if self._runtime is None:
            return

        # Persist before clearing if configured
        if preserve_memory and self._persist_memory:
            try:
                self._runtime._persist_state()
            except Exception as e:
                _log.debug("Pre-reset persistence failed: %s", e)

        # Re-create runtime with fresh state
        self._session_id = str(uuid.uuid4())
        old_runtime = self._runtime
        self._runtime = None

        if preserve_memory:
            self._persist_memory = True

        self._ensure_runtime()


if __name__ == "__main__":
    print("SessionInterface import OK")
    iface = SessionInterface.__new__(SessionInterface)
    print("SessionInterface instantiation OK")
