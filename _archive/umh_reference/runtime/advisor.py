"""Advisor runtime — persistent cognitive coordinator with predictive awareness.

The advisor is the organism's continuous decision-maker. It:
  - owns the current session
  - monitors signals from brains
  - spawns worker cells based on objectives
  - attaches/detaches cells to the session
  - maintains continuity across tasks
  - generates predictions about likely next actions (Phase 20)

The advisor NEVER executes directly. It only:
  - interprets signals
  - plans responses
  - spawns cells (via CellRuntime)
  - routes objectives (via CellOrchestrator)
  - generates and caches predictions (never auto-executes)

No imports from umh/environments, umh/adapters, subprocess, or shell.
"""

from __future__ import annotations

import logging
import threading
from typing import Any

from umh.brains.signals import list_all_signals, BrainSignal
from umh.cells.models import CellContext, CellStatus, CellType, _gen_id
from umh.cells.runtime import (
    activate_cell,
    get_cell_status,
    hydrate_cell,
    list_cells,
    spawn_cell,
    terminate_cell,
)
from umh.learning.feedback import ExecutionFeedback
from umh.model.aggregator import BehaviorAggregator
from umh.model.behavior import UserBehaviorModel
from umh.runtime.arbitration import (
    ArbitrationEngine,
    ArbitrationResult,
    Objective,
)
from umh.runtime.commitment import CommitmentDecision, CommitmentEngine, CommitmentResult
from umh.runtime.goal_state import GoalStateManager
from umh.runtime.dependency import DependencyGraph
from umh.runtime.goal_memory import GoalMemory, make_goal_record
from umh.runtime.goals import GoalBiasScorer
from umh.runtime.identity import IdentityStore, SignalExtractor
from umh.runtime.meta_planner import MetaPlanResult, MetaPlanner
from umh.runtime.sequence_memory import SequenceMemory
from umh.runtime.calibration import (
    CalibrationEngine,
    CalibrationFactors,
    CalibrationStore,
    ExecutionOutcome,
    SimulationCalibrator,
)
from umh.runtime.evaluator import SimulationResult, StrategySimulator
from umh.runtime.strategy import ExecutionStrategy, StrategyBuilder
from umh.runtime.trajectory import TrajectoryPlanner, TrajectoryResult
from umh.prediction.calibrator import ConfidenceCalibrator, ThresholdAdapter
from umh.prediction.evaluator import PredictionEvaluator
from umh.prediction.intent import UserIntent
from umh.prediction.metrics import PredictionAccuracy, PredictionMetrics
from umh.prediction.persistence import FilePredictionBackend
from umh.prediction.planner import PredictedPlan, PredictionPolicy, PredictivePlanner
from umh.prediction.predictor import PredictionContext, Predictor
from umh.prediction.store import PredictionStore, record_from_intent
from umh.prediction.temporal import TemporalWeighter
from umh.prediction.weights import WeightStore
from umh.runtime.session import Session, SessionManager, SessionType

_log = logging.getLogger(__name__)


class AdvisorRuntime:
    """Persistent brain that coordinates the organism's cognitive activity."""

    def __init__(
        self,
        session_manager: SessionManager | None = None,
        *,
        predictor: Predictor | None = None,
        predictive_planner: PredictivePlanner | None = None,
        prediction_store: PredictionStore | None = None,
        prediction_evaluator: PredictionEvaluator | None = None,
        prediction_metrics: PredictionMetrics | None = None,
        weight_store: WeightStore | None = None,
        confidence_calibrator: ConfidenceCalibrator | None = None,
        threshold_adapter: ThresholdAdapter | None = None,
        persistence_backend: FilePredictionBackend | None = None,
        temporal_weighter: TemporalWeighter | None = None,
        behavior_aggregator: BehaviorAggregator | None = None,
        strategy_builder: StrategyBuilder | None = None,
        strategy_simulator: StrategySimulator | None = None,
        calibration_engine: CalibrationEngine | None = None,
        calibration_store: CalibrationStore | None = None,
        simulation_calibrator: SimulationCalibrator | None = None,
        trajectory_planner: TrajectoryPlanner | None = None,
        arbitration_engine: ArbitrationEngine | None = None,
        meta_planner: MetaPlanner | None = None,
        dependency_graph: DependencyGraph | None = None,
        sequence_memory: SequenceMemory | None = None,
        commitment_engine: CommitmentEngine | None = None,
        goal_state_manager: GoalStateManager | None = None,
        identity_store: IdentityStore | None = None,
        goal_memory: GoalMemory | None = None,
        goal_bias_scorer: GoalBiasScorer | None = None,
    ) -> None:
        self._lock = threading.Lock()
        self._sessions = session_manager or SessionManager()
        self._advisor_cell_id: str | None = None
        self._processed_signal_ids: set[str] = set()
        self._spawned_cells: list[str] = []
        self._tick_count: int = 0
        self._predictor = predictor
        self._predictive_planner = predictive_planner
        self._pending_predictions: list[PredictedPlan] = []
        self._prediction_context: PredictionContext | None = None
        self._prediction_store = prediction_store
        self._prediction_evaluator = prediction_evaluator
        self._prediction_metrics = prediction_metrics
        self._weight_store = weight_store
        self._confidence_calibrator = confidence_calibrator
        self._threshold_adapter = threshold_adapter
        self._persistence_backend = persistence_backend
        self._temporal_weighter = temporal_weighter
        self._behavior_aggregator = behavior_aggregator
        self._behavior_model: UserBehaviorModel | None = None
        self._strategy_builder = strategy_builder
        self._strategy_simulator = strategy_simulator
        self._current_strategy: ExecutionStrategy | None = None
        self._last_simulation: SimulationResult | None = None
        self._calibration_engine = calibration_engine
        self._calibration_store = calibration_store
        self._simulation_calibrator = simulation_calibrator
        self._calibration_factors = CalibrationFactors()
        self._trajectory_planner = trajectory_planner
        self._last_trajectory: TrajectoryResult | None = None
        self._arbitration_engine = arbitration_engine
        self._objectives: list[Objective] = []
        self._last_arbitration: ArbitrationResult | None = None
        self._meta_planner = meta_planner
        self._last_meta_plan: MetaPlanResult | None = None
        self._dependency_graph = dependency_graph
        self._sequence_memory = sequence_memory
        self._commitment_engine = commitment_engine
        self._goal_state_manager = goal_state_manager or GoalStateManager()
        self._last_commitment: CommitmentResult | None = None
        self._identity_store = identity_store
        self._signal_extractor = SignalExtractor()
        self._identity_goals_attempted: int = 0
        self._identity_goals_completed: int = 0
        self._identity_switches: int = 0
        self._goal_memory = goal_memory
        self._goal_bias_scorer = goal_bias_scorer

    @property
    def session_manager(self) -> SessionManager:
        return self._sessions

    @property
    def advisor_cell_id(self) -> str | None:
        return self._advisor_cell_id

    @property
    def tick_count(self) -> int:
        return self._tick_count

    @property
    def pending_predictions(self) -> list[PredictedPlan]:
        return list(self._pending_predictions)

    @property
    def predictor(self) -> Predictor | None:
        return self._predictor

    @property
    def predictive_planner(self) -> PredictivePlanner | None:
        return self._predictive_planner

    @property
    def prediction_store(self) -> PredictionStore | None:
        return self._prediction_store

    @property
    def prediction_evaluator(self) -> PredictionEvaluator | None:
        return self._prediction_evaluator

    @property
    def weight_store(self) -> WeightStore | None:
        return self._weight_store

    @property
    def confidence_calibrator(self) -> ConfidenceCalibrator | None:
        return self._confidence_calibrator

    @property
    def threshold_adapter(self) -> ThresholdAdapter | None:
        return self._threshold_adapter

    @property
    def persistence_backend(self) -> FilePredictionBackend | None:
        return self._persistence_backend

    @property
    def temporal_weighter(self) -> TemporalWeighter | None:
        return self._temporal_weighter

    @property
    def behavior_aggregator(self) -> BehaviorAggregator | None:
        return self._behavior_aggregator

    @property
    def behavior_model(self) -> UserBehaviorModel | None:
        return self._behavior_model

    @property
    def strategy_builder(self) -> StrategyBuilder | None:
        return self._strategy_builder

    @property
    def current_strategy(self) -> ExecutionStrategy | None:
        return self._current_strategy

    @property
    def strategy_simulator(self) -> StrategySimulator | None:
        return self._strategy_simulator

    @property
    def last_simulation(self) -> SimulationResult | None:
        return self._last_simulation

    @property
    def calibration_engine(self) -> CalibrationEngine | None:
        return self._calibration_engine

    @property
    def calibration_store(self) -> CalibrationStore | None:
        return self._calibration_store

    @property
    def simulation_calibrator(self) -> SimulationCalibrator | None:
        return self._simulation_calibrator

    @property
    def calibration_factors(self) -> CalibrationFactors:
        return self._calibration_factors

    @property
    def trajectory_planner(self) -> TrajectoryPlanner | None:
        return self._trajectory_planner

    @property
    def last_trajectory(self) -> TrajectoryResult | None:
        return self._last_trajectory

    @property
    def arbitration_engine(self) -> ArbitrationEngine | None:
        return self._arbitration_engine

    @property
    def last_arbitration(self) -> ArbitrationResult | None:
        return self._last_arbitration

    @property
    def objectives(self) -> list[Objective]:
        return list(self._objectives)

    @property
    def meta_planner(self) -> MetaPlanner | None:
        return self._meta_planner

    @property
    def last_meta_plan(self) -> MetaPlanResult | None:
        return self._last_meta_plan

    @property
    def dependency_graph(self) -> DependencyGraph | None:
        return self._dependency_graph

    @property
    def sequence_memory(self) -> SequenceMemory | None:
        return self._sequence_memory

    @property
    def commitment_engine(self) -> CommitmentEngine | None:
        return self._commitment_engine

    @property
    def goal_state_manager(self) -> GoalStateManager:
        return self._goal_state_manager

    @property
    def last_commitment(self) -> CommitmentResult | None:
        return self._last_commitment

    @property
    def identity_store(self) -> IdentityStore | None:
        return self._identity_store

    @property
    def goal_memory(self) -> GoalMemory | None:
        return self._goal_memory

    @property
    def goal_bias_scorer(self) -> GoalBiasScorer | None:
        return self._goal_bias_scorer

    def add_objective(self, objective: Objective) -> None:
        self._objectives.append(objective)

    def remove_objective(self, objective_id: str) -> bool:
        before = len(self._objectives)
        self._objectives = [o for o in self._objectives if o.objective_id != objective_id]
        return len(self._objectives) < before

    def start(self, session_type: SessionType = SessionType.DAY) -> Session:
        session = self._sessions.start_session(session_type)
        self._spawn_advisor_cell(session)
        return session

    def stop(self) -> Session | None:
        if self._advisor_cell_id:
            try:
                status = get_cell_status(self._advisor_cell_id)
                if status and status not in (CellStatus.TERMINATED, CellStatus.FAILED):
                    terminate_cell(self._advisor_cell_id, reason="advisor shutdown")
            except Exception:
                pass
            self._sessions.detach_cell(self._advisor_cell_id)
            self._advisor_cell_id = None

        for cell_id in list(self._spawned_cells):
            try:
                status = get_cell_status(cell_id)
                if status and status not in (CellStatus.TERMINATED, CellStatus.FAILED):
                    terminate_cell(cell_id, reason="session ending")
            except Exception:
                pass
            self._sessions.detach_cell(cell_id)
        self._spawned_cells.clear()

        return self._sessions.end_session()

    def tick(
        self,
        *,
        prediction_context: PredictionContext | None = None,
        completed_feedback: list[ExecutionFeedback] | None = None,
    ) -> dict[str, Any]:
        self._tick_count += 1
        result: dict[str, Any] = {
            "tick": self._tick_count,
            "signals_processed": 0,
            "cells_spawned": 0,
            "cells_cleaned": 0,
            "predictions_generated": 0,
            "predictions_stored": 0,
            "predictions_matched": 0,
            "predictions_expired": 0,
            "weights_updated": 0,
            "threshold_adapted": False,
            "persisted": False,
            "model_updated": False,
            "strategy_rebuilt": False,
            "calibration_recorded": 0,
            "calibration_adjusted": False,
            "trajectory_planned": False,
            "objective_selected": False,
            "meta_plan_selected": False,
            "goal_committed": False,
            "goal_decision": None,
            "identity_updated": False,
            "goal_memory_recorded": False,
        }

        new_signals = self._read_new_signals()
        result["signals_processed"] = len(new_signals)

        for sig in new_signals:
            self._process_signal(sig)

        cleaned = self._cleanup_terminated_cells()
        result["cells_cleaned"] = cleaned

        prediction_count = self._run_prediction_pass(prediction_context)
        result["predictions_generated"] = prediction_count

        stored = self._store_predictions()
        result["predictions_stored"] = stored

        matched = self._evaluate_predictions(completed_feedback)
        result["predictions_matched"] = matched

        expired = self._expire_predictions()
        result["predictions_expired"] = expired

        weights_updated, threshold_adapted = self._adapt_prediction_weights()
        result["weights_updated"] = weights_updated
        result["threshold_adapted"] = threshold_adapted

        model_updated = self._update_behavior_model(completed_feedback)
        result["model_updated"] = model_updated

        strategy_rebuilt = self._rebuild_strategy()
        result["strategy_rebuilt"] = strategy_rebuilt

        cal_recorded, cal_adjusted = self._calibrate_simulation(completed_feedback)
        result["calibration_recorded"] = cal_recorded
        result["calibration_adjusted"] = cal_adjusted

        trajectory_planned = self._plan_trajectory()
        result["trajectory_planned"] = trajectory_planned

        objective_selected = self._arbitrate_objectives()
        result["objective_selected"] = objective_selected

        meta_plan_selected = self._meta_plan_objectives()
        result["meta_plan_selected"] = meta_plan_selected

        goal_committed, goal_decision = self._commit_to_goal()
        result["goal_committed"] = goal_committed
        result["goal_decision"] = goal_decision

        if goal_decision == CommitmentDecision.SWITCH.value:
            self._identity_switches += 1
            self._identity_goals_attempted += 1

        identity_updated = self._update_identity()
        result["identity_updated"] = identity_updated

        goal_memory_recorded = self._record_goal_outcome(goal_decision)
        result["goal_memory_recorded"] = goal_memory_recorded

        persisted = self._persist_state()
        result["persisted"] = persisted

        return result

    def spawn_worker(
        self,
        cell_type: CellType,
        objective: str,
        **metadata: Any,
    ) -> str:
        identity = spawn_cell(cell_type, parent_cell_id=self._advisor_cell_id)
        ctx = CellContext(
            cell_id=identity.cell_id,
            objective=objective,
            metadata=metadata,
        )
        hydrate_cell(identity.cell_id, ctx)
        activate_cell(identity.cell_id)

        self._sessions.attach_cell(identity.cell_id)
        with self._lock:
            self._spawned_cells.append(identity.cell_id)

        return identity.cell_id

    def get_prediction_accuracy(self) -> PredictionAccuracy | None:
        """Compute current prediction accuracy. Read-only."""
        if self._prediction_store is None or self._prediction_metrics is None:
            return None
        return self._prediction_metrics.compute_accuracy_from_store(self._prediction_store)

    def get_state(self) -> dict[str, Any]:
        session = self._sessions.get_active_session()
        state: dict[str, Any] = {
            "advisor_cell_id": self._advisor_cell_id,
            "session": session.to_dict() if session else None,
            "tick_count": self._tick_count,
            "spawned_cells": list(self._spawned_cells),
            "processed_signals": len(self._processed_signal_ids),
            "pending_predictions": len(self._pending_predictions),
        }
        if self._prediction_store is not None:
            state["prediction_store_total"] = self._prediction_store.total
            state["prediction_store_pending"] = self._prediction_store.pending_count
        accuracy = self.get_prediction_accuracy()
        if accuracy is not None:
            state["prediction_accuracy"] = accuracy.to_dict()
        if self._threshold_adapter is not None:
            state["prediction_threshold"] = self._threshold_adapter.threshold
        if self._weight_store is not None:
            state["prediction_weight_patterns"] = len(self._weight_store.list_weights())
        if self._persistence_backend is not None:
            state["persistence_enabled"] = True
        if self._temporal_weighter is not None:
            state["temporal_decay_rate"] = self._temporal_weighter.decay_rate
            decayed = self.get_decayed_weights()
            if decayed:
                state["decayed_weights"] = decayed
        if self._behavior_model is not None:
            state["behavior_model_confidence"] = self._behavior_model.confidence_score
            dominant = self._behavior_model.dominant_traits
            if dominant:
                state["dominant_traits"] = [t.name for t in dominant[:3]]
        if self._current_strategy is not None:
            state["strategy"] = self._current_strategy.to_dict()
        if self._last_simulation is not None:
            state["simulation"] = self._last_simulation.to_dict()
        if self._calibration_store is not None:
            state["calibration"] = self._calibration_store.to_dict()
            state["calibration_factors"] = self._calibration_factors.to_dict()
        if self._last_trajectory is not None:
            state["trajectory"] = self._last_trajectory.to_dict()
        if self._objectives:
            state["objectives_count"] = len(self._objectives)
        if self._last_arbitration is not None:
            state["arbitration"] = self._last_arbitration.to_dict()
        if self._last_meta_plan is not None:
            state["meta_plan"] = self._last_meta_plan.to_dict()
        if self._dependency_graph is not None:
            state["dependency_edges"] = self._dependency_graph.edge_count
        if self._sequence_memory is not None:
            state["sequence_memory_count"] = self._sequence_memory.count
        if self._goal_state_manager.has_active:
            state["goal_state"] = self._goal_state_manager.to_dict()
        if self._last_commitment is not None:
            state["commitment"] = self._last_commitment.to_dict()
        if self._identity_store is not None:
            state["identity"] = self._identity_store.to_dict()
        if self._goal_memory is not None:
            state["goal_memory_count"] = self._goal_memory.count
        return state

    def _spawn_advisor_cell(self, session: Session) -> None:
        identity = spawn_cell(
            CellType.MONITOR,
            metadata={"role": "advisor", "session_id": session.session_id},
        )
        ctx = CellContext(
            cell_id=identity.cell_id,
            objective="persistent advisor — monitor signals, coordinate cells",
            metadata={"session_id": session.session_id},
        )
        hydrate_cell(identity.cell_id, ctx)
        activate_cell(identity.cell_id)

        self._advisor_cell_id = identity.cell_id
        self._sessions.attach_cell(identity.cell_id)

    def _read_new_signals(self) -> list[BrainSignal]:
        all_signals = list_all_signals(limit=50)
        new = []
        for sig in all_signals:
            if sig.signal_id not in self._processed_signal_ids:
                self._processed_signal_ids.add(sig.signal_id)
                new.append(sig)
        return new

    def _process_signal(self, signal: BrainSignal) -> None:
        _log.debug("Advisor processing signal: %s/%s", signal.signal_type, signal.signal_id)

    def _cleanup_terminated_cells(self) -> int:
        cleaned = 0
        with self._lock:
            remaining = []
            for cell_id in self._spawned_cells:
                status = get_cell_status(cell_id)
                if status in (CellStatus.TERMINATED, CellStatus.FAILED):
                    self._sessions.detach_cell(cell_id)
                    cleaned += 1
                else:
                    remaining.append(cell_id)
            self._spawned_cells = remaining
        return cleaned

    def clear_predictions(self) -> None:
        """Discard all pending predictions and clear the prediction store."""
        self._pending_predictions.clear()
        if self._predictive_planner is not None:
            self._predictive_planner.clear_cache()
        if self._prediction_store is not None:
            self._prediction_store.clear()
        if self._weight_store is not None:
            self._weight_store.clear()
        if self._threshold_adapter is not None:
            self._threshold_adapter.reset()

    def _run_prediction_pass(
        self,
        context: PredictionContext | None = None,
    ) -> int:
        """Generate predictions from context. Never auto-executes."""
        if self._predictor is None or self._predictive_planner is None:
            return 0

        if context is not None:
            self._prediction_context = context

        if self._prediction_context is None:
            return 0

        try:
            intents = self._predictor.predict_intent(self._prediction_context)
            if not intents:
                return 0

            plans = self._predictive_planner.predict_plans(intents)
            self._pending_predictions.extend(plans)
            return len(plans)
        except Exception as e:
            _log.debug("Prediction pass error (non-fatal): %s", e)
            return 0

    def _store_predictions(self) -> int:
        """Store newly generated predictions in the prediction store."""
        if self._prediction_store is None:
            return 0
        stored = 0
        for plan in self._pending_predictions:
            record = record_from_intent(plan.intent, tick=self._tick_count)
            self._prediction_store.append(record)
            stored += 1
        return stored

    def _evaluate_predictions(
        self,
        completed_feedback: list[ExecutionFeedback] | None,
    ) -> int:
        """Evaluate pending predictions against completed jobs."""
        if (
            self._prediction_store is None
            or self._prediction_evaluator is None
            or not completed_feedback
        ):
            return 0

        try:
            pending = self._prediction_store.list_pending()
            if not pending:
                return 0

            results = self._prediction_evaluator.match_predictions(pending, completed_feedback)
            matched = 0
            for mr in results:
                if mr.matched:
                    self._prediction_store.mark_matched(
                        mr.prediction_id, matched_job_id=mr.matched_job_id
                    )
                    matched += 1
            return matched
        except Exception as e:
            _log.debug("Prediction evaluation error (non-fatal): %s", e)
            return 0

    def _expire_predictions(self) -> int:
        """Expire stale pending predictions."""
        if self._prediction_store is None:
            return 0
        try:
            return self._prediction_store.expire_old_predictions(current_tick=self._tick_count)
        except Exception as e:
            _log.debug("Prediction expiry error (non-fatal): %s", e)
            return 0

    def _adapt_prediction_weights(self) -> tuple[int, bool]:
        """Update weights from resolved predictions and adapt threshold.

        Runs AFTER evaluation and expiration. Uses newly resolved
        records to update pattern weights, then adjusts the confidence
        threshold based on overall accuracy.

        Returns (weights_updated, threshold_adapted).
        """
        weights_updated = 0
        threshold_adapted = False

        if self._weight_store is not None and self._prediction_store is not None:
            try:
                resolved = self._prediction_store.list_resolved()
                for rec in resolved:
                    from umh.prediction.store import PredictionStatus

                    if rec.status == PredictionStatus.MATCHED:
                        pattern_key = rec.source or rec.inferred_goal
                        self._weight_store.update_weight(pattern_key, matched=True)
                        weights_updated += 1
                    elif rec.status in (PredictionStatus.MISSED, PredictionStatus.EXPIRED):
                        pattern_key = rec.source or rec.inferred_goal
                        self._weight_store.update_weight(pattern_key, matched=False)
                        weights_updated += 1
            except Exception as e:
                _log.debug("Weight adaptation error (non-fatal): %s", e)

        if (
            self._threshold_adapter is not None
            and self._prediction_store is not None
            and self._prediction_metrics is not None
        ):
            try:
                accuracy = self._prediction_metrics.compute_accuracy_from_store(
                    self._prediction_store
                )
                resolved_count = accuracy.matched + accuracy.missed + accuracy.expired
                if resolved_count >= 3:
                    self._threshold_adapter.adapt(accuracy.accuracy_rate)
                    threshold_adapted = True
            except Exception as e:
                _log.debug("Threshold adaptation error (non-fatal): %s", e)

        return weights_updated, threshold_adapted

    def _update_behavior_model(
        self,
        completed_feedback: list[ExecutionFeedback] | None,
    ) -> bool:
        """Update the behavior model from available data. Never crashes."""
        if self._behavior_aggregator is None:
            return False

        try:
            fb = completed_feedback or []
            preds = self._prediction_store.list_all() if self._prediction_store is not None else []
            pw = (
                [w.to_dict() for w in self._weight_store.list_weights()]
                if self._weight_store is not None
                else []
            )

            if self._behavior_model is None:
                self._behavior_model = self._behavior_aggregator.build_model(
                    feedback=fb,
                    predictions=preds,
                    pattern_weights=pw,
                )
            else:
                self._behavior_aggregator.update_model(
                    self._behavior_model,
                    new_feedback=fb,
                    new_predictions=preds,
                    pattern_weights=pw,
                )
            return True
        except Exception as e:
            _log.debug("Behavior model update error (non-fatal): %s", e)
            return False

    def _rebuild_strategy(self) -> bool:
        """Rebuild execution strategy from current behavior model. Never crashes."""
        if self._strategy_builder is None:
            return False
        try:
            base = self._strategy_builder.build_strategy(self._behavior_model)

            if self._strategy_simulator is not None:
                sim_result = self._strategy_simulator.run(
                    base, self._behavior_model, self._calibration_factors
                )
                self._current_strategy = sim_result.selected.strategy
                self._last_simulation = sim_result
            else:
                self._current_strategy = base
                self._last_simulation = None

            return True
        except Exception as e:
            _log.debug("Strategy rebuild error (non-fatal): %s", e)
            return False

    def record_outcome(self, outcome: ExecutionOutcome) -> bool:
        """Record a real execution outcome for calibration. Thread-safe."""
        if self._calibration_engine is None or self._calibration_store is None:
            return False
        if self._last_simulation is None:
            return False
        try:
            record = self._calibration_engine.build_record(self._last_simulation.selected, outcome)
            self._calibration_store.append(record)
            return True
        except Exception as e:
            _log.debug("Outcome recording error (non-fatal): %s", e)
            return False

    def _calibrate_simulation(
        self,
        completed_feedback: list[ExecutionFeedback] | None,
    ) -> tuple[int, bool]:
        """Run calibration from completed feedback, adjust factors."""
        if (
            self._calibration_engine is None
            or self._calibration_store is None
            or self._simulation_calibrator is None
        ):
            return 0, False

        recorded = 0
        adjusted = False

        if completed_feedback and self._last_simulation is not None:
            try:
                for fb in completed_feedback:
                    outcome = ExecutionOutcome(
                        actual_completion_rate=getattr(fb, "completion_rate", 0.7),
                        actual_latency=getattr(fb, "latency", 1.0),
                        actual_failure_rate=getattr(fb, "failure_rate", 0.1),
                        actual_effort=getattr(fb, "effort", 0.5),
                    )
                    record = self._calibration_engine.build_record(
                        self._last_simulation.selected, outcome
                    )
                    self._calibration_store.append(record)
                    recorded += 1
            except Exception as e:
                _log.debug("Calibration recording error (non-fatal): %s", e)

        if self._calibration_store.count >= 3:
            try:
                mean_err = self._calibration_store.mean_errors()
                if mean_err is not None:
                    new_factors, _ = self._simulation_calibrator.calibrate(
                        self._calibration_factors, mean_err
                    )
                    self._calibration_factors = new_factors
                    adjusted = True
            except Exception as e:
                _log.debug("Calibration adjustment error (non-fatal): %s", e)

        return recorded, adjusted

    def _plan_trajectory(self) -> bool:
        """Plan a multi-step trajectory from current strategy. Never crashes."""
        if self._trajectory_planner is None or self._current_strategy is None:
            return False
        try:
            result = self._trajectory_planner.plan(
                self._current_strategy,
                model=self._behavior_model,
                calibration=self._calibration_factors,
            )
            self._last_trajectory = result
            self._current_strategy = result.selected.first_strategy
            return True
        except Exception as e:
            _log.debug("Trajectory planning error (non-fatal): %s", e)
            return False

    def _arbitrate_objectives(self) -> bool:
        """Select the best objective from the current set. Never crashes."""
        if self._arbitration_engine is None or not self._objectives:
            return False
        try:
            result = self._arbitration_engine.select(self._objectives)
            if result is not None:
                self._last_arbitration = result
                return True
            return False
        except Exception as e:
            _log.debug("Objective arbitration error (non-fatal): %s", e)
            return False

    def _meta_plan_objectives(self) -> bool:
        """Run meta-planning across objectives to find best sequence. Never crashes."""
        if self._meta_planner is None or not self._objectives:
            return False
        try:
            result = self._meta_planner.plan(self._objectives)
            if result is not None:
                self._last_meta_plan = result
                return True
            return False
        except Exception as e:
            _log.debug("Meta-planning error (non-fatal): %s", e)
            return False

    def _update_identity(self) -> bool:
        """Update identity traits from behavioral signals. Never crashes."""
        if self._identity_store is None:
            return False
        try:
            signals = self._signal_extractor.extract(
                total_ticks=self._tick_count,
                goals_completed=self._identity_goals_completed,
                goals_attempted=self._identity_goals_attempted,
                switches=self._identity_switches,
            )
            self._identity_store.update_from_signals(signals)
            return True
        except Exception as e:
            _log.debug("Identity update error (non-fatal): %s", e)
            return False

    def _record_goal_outcome(self, goal_decision: str | None) -> bool:
        """Record goal outcome to memory when a goal completes or is abandoned. Never crashes."""
        if self._goal_memory is None:
            return False
        if goal_decision not in (CommitmentDecision.ABANDON.value, CommitmentDecision.SWITCH.value):
            return False
        try:
            history = self._goal_state_manager.get_history()
            if not history:
                return False
            last = history[-1]
            goal_type = last.active_objective.metadata.get("goal_type", "general")
            completed = goal_decision == CommitmentDecision.SWITCH.value and last.progress >= 0.9
            identity_alignment = 0.5
            if self._identity_store is not None and self._identity_store.update_count > 0:
                profile = self._identity_store.get_profile()
                if profile.traits:
                    identity_alignment = sum(profile.traits.values()) / len(profile.traits)
            record = make_goal_record(
                goal_id=last.active_objective.objective_id,
                goal_type=goal_type,
                duration_ticks=last.elapsed_ticks(self._tick_count),
                completed=completed,
                success_rate=last.progress,
                identity_alignment=identity_alignment,
                reward=last.progress if completed else last.progress * 0.5,
            )
            self._goal_memory.append(record)
            return True
        except Exception as e:
            _log.debug("Goal memory recording error (non-fatal): %s", e)
            return False

    def _commit_to_goal(self) -> tuple[bool, str | None]:
        """Run commitment logic: persist, continue, switch, or abandon. Never crashes."""
        if self._commitment_engine is None:
            return False, None

        try:
            candidate = None
            if self._last_meta_plan is not None:
                candidate = self._last_meta_plan.next_objective
            elif self._last_arbitration is not None:
                candidate = self._last_arbitration.selected

            active = self._goal_state_manager.get_active()

            if active is None:
                if candidate is not None:
                    self._goal_state_manager.set_active(candidate, self._tick_count)
                    self._last_commitment = None
                    return True, CommitmentDecision.SWITCH.value

                return False, None

            if candidate is not None and candidate.objective_id == active.objective_id:
                candidate = None

            result = self._commitment_engine.decide(active, candidate, self._tick_count)
            self._last_commitment = result

            if result.decision == CommitmentDecision.SWITCH and candidate is not None:
                self._goal_state_manager.set_active(candidate, self._tick_count)
                return True, CommitmentDecision.SWITCH.value

            if result.decision == CommitmentDecision.ABANDON:
                self._goal_state_manager.abandon()
                return True, CommitmentDecision.ABANDON.value

            return True, CommitmentDecision.CONTINUE.value

        except Exception as e:
            _log.debug("Goal commitment error (non-fatal): %s", e)
            return False, None

    def _persist_state(self) -> bool:
        """Persist prediction records and weights to disk. Never crashes."""
        if self._persistence_backend is None:
            return False

        any_error = False
        try:
            if self._prediction_store is not None:
                records = self._prediction_store.list_all()
                stats = self._persistence_backend.save_records(records)
                if stats.errors:
                    any_error = True

            if self._weight_store is not None:
                weights = self._weight_store.list_weights()
                stats = self._persistence_backend.save_weights([w.to_dict() for w in weights])
                if stats.errors:
                    any_error = True

            return not any_error
        except Exception as e:
            _log.debug("Persistence error (non-fatal): %s", e)
            return False

    def get_decayed_weights(self) -> dict[str, float]:
        """Get all weights with temporal decay applied. Read-only."""
        if self._weight_store is None or self._temporal_weighter is None:
            return {}
        from umh.core.clock import iso_now

        now = iso_now()
        result: dict[str, float] = {}
        for pw in self._weight_store.list_weights():
            if pw.last_updated:
                age_h = self._temporal_weighter.compute_age_hours(pw.last_updated, now)
                dr = self._temporal_weighter.apply_decay(pw.weight, age_h)
                result[pw.pattern_key] = dr.decayed_weight
            else:
                result[pw.pattern_key] = pw.weight
        return result

    def clear(self) -> None:
        self._advisor_cell_id = None
        self._processed_signal_ids.clear()
        self._spawned_cells.clear()
        self._tick_count = 0
        self._sessions.clear()
        self._pending_predictions.clear()
        self._prediction_context = None
        if self._prediction_store is not None:
            self._prediction_store.clear()
        if self._weight_store is not None:
            self._weight_store.clear()
        if self._threshold_adapter is not None:
            self._threshold_adapter.reset()
        self._behavior_model = None
        self._current_strategy = None
        self._last_simulation = None
        self._last_trajectory = None
        self._last_arbitration = None
        self._last_meta_plan = None
        self._objectives.clear()
        if self._sequence_memory is not None:
            self._sequence_memory.clear()
        if self._dependency_graph is not None:
            self._dependency_graph.clear()
        self._goal_state_manager.clear()
        self._last_commitment = None
        if self._identity_store is not None:
            self._identity_store.clear()
        self._identity_goals_attempted = 0
        self._identity_goals_completed = 0
        self._identity_switches = 0
        if self._goal_memory is not None:
            self._goal_memory.clear()
        self._calibration_factors = CalibrationFactors()
        if self._calibration_store is not None:
            self._calibration_store._records.clear()
