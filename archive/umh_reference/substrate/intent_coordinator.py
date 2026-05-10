"""
Intent coordinator — top-level orchestration handler.

The ONLY orchestration subscriber to the EventScheduler.  Manages
intent lifecycle: ingress, activation, step advancement, failure,
cancellation, and pending-to-active promotion.

Subscribes to:
    Raw ingress (4 types, one handler):
        decision_intent_proposed, operator_intent_requested,
        cron_intent_requested, result_intent_requested

    Execution results (4 types, one handler):
        execution_completed, execution_failed,
        execution_timed_out, execution_rejected

    Cancellation:
        intent_cancel_requested

WorkflowDriver is a pure step machine called by this class — it never
subscribes to the scheduler directly and never emits intent-level
lifecycle events (orch_intent_completed, orch_intent_failed,
orch_intent_cancelled).  Those are emitted exclusively by this
coordinator based on the StepResult.terminal signal.

Execution-result correlation:
    At dispatch time, the coordinator stores:
        intent_step_events.{step_event_id} -> {intent_id, step_index}

    When an execution result arrives, the coordinator reads the
    in-flight record to extract causal_event_id (which matches the
    step_event_id), then looks up the intent via the stored mapping.
    This uses the existing causal_event_id field on ExecutionRequest —
    no new execution fabric contracts needed.

Active intent state model:
    Keyed index: active_intent.{intent_id} -> metadata dict
    Uses SET for add/update, REMOVE for deactivation.
    No list membership, no REMOVE_FROM_LIST.

Event ordering across intent boundaries:
    When an intent completes/fails and a pending intent is promoted,
    the emitted_events list is ordered:
        [terminal events for Intent A] then [activation events for Intent B]
    This is structural — terminal events are appended before
    _promote_next_pending is called, and promotion events are appended after.

Autonomy policy:
    When an AutonomyPolicy is provided and enabled, ingress is gated:
    - Per-source type allow/deny (decision/operator/cron/result)
    - Chain depth limits for result-driven follow-on
    - Follow-on count limits per root intent
    Lineage (root_intent_id, parent_intent_id, chain_depth,
    follow_on_count_from_root, source_type) is persisted in intent
    metadata for replay-safe enforcement.  Rejected intents emit
    orch_intent_rejected and create no state.

Concurrency policy (MVP):
    max_active=1, preemption_enabled=False.
    Excess intents stay PENDING until the active slot opens.

Usage:
    coordinator = IntentCoordinator(plan_registry, workflow_driver)
    # Wire into scheduler via orchestration_bootstrap.py
"""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from typing import Any

from umh.substrate.autonomy_policy import AutonomyPolicy, IngressSource
from umh.substrate.event_scheduler import (
    ExecutionResult as SchedulerExecutionResult,
    SchedulerEvent,
)
from umh.substrate.execution_contract import (
    ExecutionResult,
    ExecutionStatus,
)
from umh.substrate.intent_memory import build_memory_update_mutations
from umh.substrate.plan_scoring import (
    build_plan_memory_update_mutations,
    compute_state_signature,
)
from umh.substrate.decision_events import (
    build_meta_adjusted_event,
    build_meta_saturation_event,
)
from umh.substrate.score_meta import (
    DEFAULT_PENALTY_WEIGHT,
    SATURATION_WARN_THRESHOLD,
    build_score_meta_adjustment,
    get_penalty_weight,
    lookup_score_meta,
)
from umh.substrate.intent_models import (
    Intent,
    IntentStatus,
    IntentType,
    compute_intent_id,
    get_intent_from_state,
    intent_store_key,
)
from umh.substrate.plan_registry import PlanRegistry
from umh.substrate.runtime_state_store import RuntimeStateStore
from umh.substrate.workflow_driver import StepResult, WorkflowDriver
from umh.substrate.trigger_adapters import from_result
from umh.substrate.workflow_events import (
    build_orch_intent_cancelled_event,
    build_orch_intent_completed_event,
    build_orch_intent_created_event,
    build_orch_intent_failed_event,
    build_orch_intent_rejected_event,
    build_orch_intent_step_completed_event,
    build_orch_intent_step_failed_event,
)

_LOG_PREFIX = "[substrate.intent_coordinator]"


def _log(msg: str) -> None:
    print(f"{_LOG_PREFIX} {msg}", file=sys.stderr)


def _maybe_saturation_event(
    adj: list[dict],
    scope: str,
    success_count: int,
    failure_count: int,
    session_name: str,
    run_id: str | None,
) -> SchedulerEvent | None:
    """Return a saturation event if the adjustment hit the warn threshold."""
    rec = adj[0]["value"]
    sat = rec.get("saturation_count", 0)
    if sat < SATURATION_WARN_THRESHOLD:
        return None
    ec = success_count + failure_count
    return build_meta_saturation_event(
        scope=scope,
        current_weight=rec["failure_penalty_weight"],
        saturation_count=sat,
        success_rate=success_count / ec if ec else 0.0,
        failure_rate=failure_count / ec if ec else 0.0,
        execution_count=ec,
        session_name=session_name,
        run_id=run_id,
    )


class IntentCoordinator:
    """Top-level orchestration handler managing intent lifecycle.

    This is the ONLY orchestration-level scheduler subscriber.
    WorkflowDriver is called as a pure step machine — never registered
    with the scheduler directly, never emits intent-level lifecycle events.
    """

    def __init__(
        self,
        plan_registry: PlanRegistry,
        workflow_driver: WorkflowDriver,
        max_active: int = 1,
        preemption_enabled: bool = False,
        autonomy_policy: AutonomyPolicy | None = None,
    ) -> None:
        self._plan_registry = plan_registry
        self._driver = workflow_driver
        self._max_active = max_active
        self._preemption_enabled = preemption_enabled
        self._autonomy_policy = autonomy_policy or AutonomyPolicy()

    # ── Scheduler handler: intent ingress ─────────────────────────────

    def _handle_intent_ingress(
        self, store: RuntimeStateStore, event: SchedulerEvent
    ) -> SchedulerExecutionResult:
        """Handle all 4 raw ingress event types.

        Extracts intent_type + goal from payload, computes deterministic
        intent_id, classifies ingress source, derives lineage, applies
        autonomy policy checks, then writes intent + membership.
        """
        payload = event.payload
        intent_type_str = payload.get("intent_type", "")
        goal = payload.get("goal", {})
        priority = payload.get("priority", 100)
        source_context = payload.get("source_context", {})

        # Parse intent type
        try:
            intent_type = IntentType(intent_type_str)
        except ValueError:
            _log(f"unknown intent type: {intent_type_str}, dropping")
            return SchedulerExecutionResult(
                metadata={"skipped": True, "reason": "unknown_intent_type"}
            )

        # ── Classify ingress source ─────────────────────────────────
        ingress_source = IngressSource.from_event_type(event.event_type)
        if ingress_source is None:
            _log(f"unrecognized ingress event type: {event.event_type}, dropping")
            return SchedulerExecutionResult(
                metadata={"skipped": True, "reason": "unknown_ingress_type"}
            )

        # ── Derive lineage fields ───────────────────────────────────
        lineage = self._derive_lineage(ingress_source, source_context, store)

        # ── Autonomy policy enforcement ─────────────────────────────
        rejection_reason = self._check_autonomy_policy(ingress_source, lineage)
        if rejection_reason is not None:
            _log(
                f"ingress rejected: type={intent_type_str} "
                f"source={ingress_source.value} reason={rejection_reason}"
            )
            return SchedulerExecutionResult(
                emitted_events=[
                    build_orch_intent_rejected_event(
                        attempted_intent_type=intent_type_str,
                        reason=rejection_reason,
                        source_type=ingress_source.value,
                        session_name=event.session_name,
                        root_intent_id=lineage.get("root_intent_id", ""),
                        parent_intent_id=lineage.get("parent_intent_id", ""),
                        attempted_chain_depth=lineage.get("chain_depth", 0),
                        attempted_follow_on_count=lineage.get(
                            "follow_on_count_from_root", 0
                        ),
                        goal_summary=goal,
                        raw_trigger_event_type=event.event_type,
                        raw_trigger_event_id=event.event_id,
                        run_id=event.run_id,
                    )
                ],
                metadata={
                    "rejected": True,
                    "reason": rejection_reason,
                    "source_type": ingress_source.value,
                },
            )

        # Deterministic intent_id
        intent_id = compute_intent_id(intent_type, goal)

        # Dedup: skip if intent already exists (active, pending, or terminal)
        existing = get_intent_from_state(store.snapshot(), intent_id)
        if existing is not None:
            _log(f"intent {intent_id} already exists (status={existing.status.value})")
            return SchedulerExecutionResult(
                metadata={
                    "skipped": True,
                    "reason": "intent_already_exists",
                    "intent_id": intent_id,
                }
            )

        # Create intent with lineage metadata
        intent_metadata = dict(lineage)
        intent = Intent(
            intent_id=intent_id,
            intent_type=intent_type,
            goal=goal,
            priority=priority,
            status=IntentStatus.PENDING,
            created_at=datetime.now(timezone.utc).isoformat(),
            session_name=event.session_name,
            metadata=intent_metadata,
        )

        mutations: list[dict[str, Any]] = []
        events: list[SchedulerEvent] = []

        # Check active slot availability
        active = self._get_active_intents(store)
        if len(active) < self._max_active:
            # Activate immediately
            act_mutations, act_events = self._activate_intent(intent, store)
            mutations.extend(act_mutations)
            events.extend(act_events)
        else:
            # No active slot — write as PENDING only
            mutations.append(
                {
                    "op": "SET",
                    "key": intent_store_key(intent_id),
                    "value": intent.to_dict(),
                }
            )
            _log(
                f"intent {intent_id} queued as PENDING (max_active={self._max_active})"
            )

        # Observability event (always last — after any activation events)
        events.append(
            build_orch_intent_created_event(
                intent_id=intent_id,
                intent_type=intent_type.value,
                goal=goal,
                priority=priority,
                session_name=event.session_name,
                raw_trigger_event_type=event.event_type,
                raw_trigger_event_id=event.event_id,
                run_id=event.run_id,
            )
        )

        _log(
            f"ingress: intent={intent_id} type={intent_type.value} "
            f"from={event.event_type} depth={lineage.get('chain_depth', 0)}"
        )
        return SchedulerExecutionResult(
            mutations=mutations,
            emitted_events=events,
            metadata={"intent_id": intent_id},
        )

    # ── Autonomy: lineage derivation and policy checks ────────────────

    @staticmethod
    def _derive_lineage(
        source: IngressSource,
        source_context: dict[str, Any],
        store: RuntimeStateStore,
    ) -> dict[str, Any]:
        """Derive lineage fields from ingress source and parent intent state.

        For first-generation ingress (decision/operator/cron):
            root_intent_id, parent_intent_id are empty, depth=0, count=0.
        For result-driven ingress:
            Reads the triggering (parent) intent from the store to inherit
            lineage.  All enforcement decisions are derived from persisted
            parent state — replay-safe.

        Returns a dict of lineage fields to embed in intent metadata.
        """
        lineage: dict[str, Any] = {
            "source_type": source.value,
            "root_intent_id": "",
            "parent_intent_id": "",
            "chain_depth": 0,
            "follow_on_count_from_root": 0,
        }

        if source != IngressSource.RESULT:
            return lineage

        # Result-driven: inherit lineage from parent intent
        parent_intent_id = source_context.get("triggering_intent_id", "")
        if not parent_intent_id:
            return lineage

        parent_raw = store.get(intent_store_key(parent_intent_id))
        if parent_raw is None:
            # Parent not found — treat as first-generation with parent ref
            lineage["parent_intent_id"] = parent_intent_id
            return lineage

        parent_meta = parent_raw.get("metadata", {})
        parent_root = parent_meta.get("root_intent_id", "")

        # If parent has no root, the parent IS the root
        root_id = parent_root if parent_root else parent_intent_id

        lineage["parent_intent_id"] = parent_intent_id
        lineage["root_intent_id"] = root_id
        lineage["chain_depth"] = parent_meta.get("chain_depth", 0) + 1
        lineage["follow_on_count_from_root"] = (
            parent_meta.get("follow_on_count_from_root", 0) + 1
        )

        return lineage

    def _check_autonomy_policy(
        self,
        source: IngressSource,
        lineage: dict[str, Any],
    ) -> str | None:
        """Apply autonomy policy checks to proposed ingress.

        Returns a rejection reason string if the policy rejects the intent,
        or None if the intent is allowed to proceed.
        """
        policy = self._autonomy_policy

        # Source type gating
        if not policy.is_source_allowed(source):
            return f"source_type_disabled:{source.value}"

        # Chain depth and follow-on count only apply to result ingress
        if source == IngressSource.RESULT:
            depth = lineage.get("chain_depth", 0)
            if not policy.check_chain_depth(depth):
                return f"chain_depth_exceeded:{depth}"

            count = lineage.get("follow_on_count_from_root", 0)
            if not policy.check_follow_on_count(count):
                return f"follow_on_count_exceeded:{count}"

        return None

    # ── Scheduler handler: execution results ─────────────────────────

    def _handle_execution_result(
        self, store: RuntimeStateStore, event: SchedulerEvent
    ) -> SchedulerExecutionResult:
        """Handle execution_completed/failed/timed_out/rejected.

        Correlates execution result to active intent via causal_event_id
        chain: result.execution_id -> in_flight record -> causal_event_id
        -> intent_step_events.{causal_event_id} -> intent_id.
        """
        result_data = event.payload.get("result")
        if result_data is None:
            return SchedulerExecutionResult()

        try:
            result = ExecutionResult.from_dict(result_data)
        except Exception:
            return SchedulerExecutionResult()

        execution_id = result.execution_id

        # Look up the in-flight record to get causal_event_id
        in_flight = store.get(f"in_flight_executions.{execution_id}")
        if in_flight is None:
            return SchedulerExecutionResult()

        # Extract causal_event_id from the original request
        original_request = in_flight.get("original_request", {})
        causal_event_id = original_request.get("causal_event_id", "")

        if not causal_event_id:
            return SchedulerExecutionResult()

        # Look up intent via step event correlation
        step_mapping = store.get(f"intent_step_events.{causal_event_id}")
        if step_mapping is None:
            # This execution wasn't triggered by an orchestration step
            return SchedulerExecutionResult()

        intent_id = step_mapping["intent_id"]
        step_index = step_mapping["step_index"]

        # Load intent
        intent = self._get_intent_from_store(store, intent_id)
        if intent is None or intent.is_terminal:
            return SchedulerExecutionResult()

        mutations: list[dict[str, Any]] = []
        events: list[SchedulerEvent] = []

        if result.status == ExecutionStatus.SUCCEEDED:
            self._handle_step_success(
                store,
                event,
                intent,
                step_index,
                execution_id,
                mutations,
                events,
            )
        else:
            self._handle_step_failure(
                store,
                event,
                intent,
                step_index,
                execution_id,
                result,
                mutations,
                events,
            )

        _log(
            f"execution result: intent={intent.intent_id} step={step_index} "
            f"status={result.status.value} mutations={len(mutations)}"
        )
        return SchedulerExecutionResult(
            mutations=mutations,
            emitted_events=events,
            metadata={
                "intent_id": intent.intent_id,
                "step_index": step_index,
                "execution_status": result.status.value,
            },
        )

    def _handle_step_success(
        self,
        store: RuntimeStateStore,
        event: SchedulerEvent,
        intent: Intent,
        step_index: int,
        execution_id: str,
        mutations: list[dict[str, Any]],
        events: list[SchedulerEvent],
    ) -> None:
        """Process a successful execution step. Mutates mutations/events in place.

        Event ordering:
            Phase 1 (Intent A terminal): step_completed, intent_completed
            Phase 2 (Intent B activation): step event, step_dispatched
        """
        # Phase 1: step-level observability
        events.append(
            build_orch_intent_step_completed_event(
                intent_id=intent.intent_id,
                step_index=step_index,
                execution_id=execution_id,
                session_name=event.session_name,
                run_id=event.run_id,
            )
        )

        step_result = self._driver.advance_step(intent, step_index, store.snapshot())
        mutations.extend(step_result.mutations)

        if step_result.terminal:
            # Phase 1 continued: intent-level terminal event (coordinator owns this)
            if step_result.terminal_status == "completed":
                events.append(
                    build_orch_intent_completed_event(
                        intent_id=intent.intent_id,
                        intent_type=intent.intent_type.value,
                        steps_executed=step_result.steps_executed,
                        session_name=intent.session_name,
                        run_id=intent.goal.get("run_id"),
                    )
                )

                # Intent memory: record success
                ts = datetime.now(timezone.utc).isoformat()
                intent_mem_muts = build_memory_update_mutations(
                    intent_type=intent.intent_type.value,
                    goal=intent.goal,
                    outcome="completed",
                    reason="",
                    timestamp=ts,
                    state=store.snapshot(),
                )
                mutations.extend(intent_mem_muts)

                # Score meta: adjust intent penalty weight
                if intent_mem_muts:
                    updated_intent_mem = intent_mem_muts[0]["value"]
                    intent_meta = lookup_score_meta(store.snapshot(), "intent")
                    meta_adj = build_score_meta_adjustment(
                        "intent", updated_intent_mem, intent_meta
                    )
                    if meta_adj:
                        meta_adj[0]["value"]["last_updated_at"] = ts
                        mutations.extend(meta_adj)
                        _sc = updated_intent_mem["success_count"]
                        _fc = updated_intent_mem["failure_count"]
                        _ec = _sc + _fc
                        _old_w = get_penalty_weight(intent_meta)
                        _new_w = meta_adj[0]["value"]["failure_penalty_weight"]
                        events.append(
                            build_meta_adjusted_event(
                                scope="intent",
                                old_weight=_old_w,
                                new_weight=_new_w,
                                success_rate=_sc / _ec if _ec else 0.0,
                                failure_rate=_fc / _ec if _ec else 0.0,
                                execution_count=_ec,
                                delta_applied=_new_w - _old_w,
                                adjustment_count=meta_adj[0]["value"][
                                    "adjustment_count"
                                ],
                                cumulative_delta=abs(_new_w - DEFAULT_PENALTY_WEIGHT),
                                failure_count=_fc,
                                session_name=intent.session_name,
                                run_id=intent.goal.get("run_id"),
                            )
                        )
                        _sat_ev = _maybe_saturation_event(
                            meta_adj,
                            "intent",
                            _sc,
                            _fc,
                            intent.session_name,
                            intent.goal.get("run_id"),
                        )
                        if _sat_ev:
                            events.append(_sat_ev)

                # Plan memory: record success per-variant
                variant_id = self._get_variant_id(store, intent.intent_id)
                if variant_id:
                    snap = store.snapshot()
                    plan_mem_muts = build_plan_memory_update_mutations(
                        intent_type=intent.intent_type.value,
                        goal=intent.goal,
                        plan_id=variant_id,
                        outcome="completed",
                        timestamp=ts,
                        state=snap,
                        state_signature=compute_state_signature(snap),
                    )
                    mutations.extend(plan_mem_muts)

                    # Score meta: adjust plan penalty weight
                    if plan_mem_muts:
                        updated_plan_mem = plan_mem_muts[0]["value"]
                        plan_meta = lookup_score_meta(snap, "plan")
                        plan_adj = build_score_meta_adjustment(
                            "plan", updated_plan_mem, plan_meta
                        )
                        if plan_adj:
                            plan_adj[0]["value"]["last_updated_at"] = ts
                            mutations.extend(plan_adj)
                            _psc = updated_plan_mem["success_count"]
                            _pfc = updated_plan_mem["failure_count"]
                            _pec = _psc + _pfc
                            _old_pw = get_penalty_weight(plan_meta)
                            _new_pw = plan_adj[0]["value"]["failure_penalty_weight"]
                            events.append(
                                build_meta_adjusted_event(
                                    scope="plan",
                                    old_weight=_old_pw,
                                    new_weight=_new_pw,
                                    success_rate=_psc / _pec if _pec else 0.0,
                                    failure_rate=_pfc / _pec if _pec else 0.0,
                                    execution_count=_pec,
                                    delta_applied=_new_pw - _old_pw,
                                    adjustment_count=plan_adj[0]["value"][
                                        "adjustment_count"
                                    ],
                                    cumulative_delta=abs(
                                        _new_pw - DEFAULT_PENALTY_WEIGHT
                                    ),
                                    failure_count=_pfc,
                                    session_name=intent.session_name,
                                    run_id=intent.goal.get("run_id"),
                                )
                            )
                            _sat_pev = _maybe_saturation_event(
                                plan_adj,
                                "plan",
                                _psc,
                                _pfc,
                                intent.session_name,
                                intent.goal.get("run_id"),
                            )
                            if _sat_pev:
                                events.append(_sat_pev)

                # Result-driven follow-on: if the completed intent's goal
                # specifies a follow_on, emit result_intent_requested so
                # the next intent enters through the ingress vocabulary.
                # Lineage is passed via source_context so ingress can
                # derive chain_depth/follow_on_count from persisted parent
                # state.  Policy rejection happens at ingress, not here.
                follow_on = intent.goal.get("follow_on")
                if isinstance(follow_on, dict) and "intent_type" in follow_on:
                    follow_event = from_result(
                        intent_type=follow_on["intent_type"],
                        goal=follow_on.get("goal", {}),
                        priority=follow_on.get("priority", 100),
                        session_name=intent.session_name,
                        triggering_intent_id=intent.intent_id,
                        run_id=intent.goal.get("run_id"),
                        source_context={
                            "triggering_intent_type": intent.intent_type.value,
                            "triggering_intent_id": intent.intent_id,
                            "trigger_reason": "follow_on_completion",
                        },
                    )
                    events.append(follow_event)
                    _log(
                        f"follow-on emitted: {follow_on['intent_type']} "
                        f"from completed intent {intent.intent_id}"
                    )
            else:
                # Driver signaled failure during advance (e.g., plan disappeared)
                events.append(
                    build_orch_intent_failed_event(
                        intent_id=intent.intent_id,
                        intent_type=intent.intent_type.value,
                        reason=step_result.terminal_reason,
                        step_index=intent.current_step,
                        session_name=intent.session_name,
                        run_id=intent.goal.get("run_id"),
                    )
                )

                # Intent memory: record failure from driver
                ts_fail = datetime.now(timezone.utc).isoformat()
                intent_fail_muts = build_memory_update_mutations(
                    intent_type=intent.intent_type.value,
                    goal=intent.goal,
                    outcome="failed",
                    reason=step_result.terminal_reason,
                    timestamp=ts_fail,
                    state=store.snapshot(),
                    failure_type="driver_failure",
                )
                mutations.extend(intent_fail_muts)

                # Score meta: adjust intent penalty weight
                if intent_fail_muts:
                    updated_drv_mem = intent_fail_muts[0]["value"]
                    intent_meta_drv = lookup_score_meta(store.snapshot(), "intent")
                    drv_adj = build_score_meta_adjustment(
                        "intent", updated_drv_mem, intent_meta_drv
                    )
                    if drv_adj:
                        drv_adj[0]["value"]["last_updated_at"] = ts_fail
                        mutations.extend(drv_adj)
                        _dsc = updated_drv_mem["success_count"]
                        _dfc = updated_drv_mem["failure_count"]
                        _dec = _dsc + _dfc
                        _old_dw = get_penalty_weight(intent_meta_drv)
                        _new_dw = drv_adj[0]["value"]["failure_penalty_weight"]
                        events.append(
                            build_meta_adjusted_event(
                                scope="intent",
                                old_weight=_old_dw,
                                new_weight=_new_dw,
                                success_rate=_dsc / _dec if _dec else 0.0,
                                failure_rate=_dfc / _dec if _dec else 0.0,
                                execution_count=_dec,
                                delta_applied=_new_dw - _old_dw,
                                adjustment_count=drv_adj[0]["value"][
                                    "adjustment_count"
                                ],
                                cumulative_delta=abs(_new_dw - DEFAULT_PENALTY_WEIGHT),
                                failure_count=_dfc,
                                session_name=intent.session_name,
                                run_id=intent.goal.get("run_id"),
                            )
                        )
                        _sat_dev = _maybe_saturation_event(
                            drv_adj,
                            "intent",
                            _dsc,
                            _dfc,
                            intent.session_name,
                            intent.goal.get("run_id"),
                        )
                        if _sat_dev:
                            events.append(_sat_dev)

                # Plan memory: record failure per-variant (with causal context)
                variant_id_fail = self._get_variant_id(store, intent.intent_id)
                if variant_id_fail:
                    snap_fail = store.snapshot()
                    plan_fail_muts = build_plan_memory_update_mutations(
                        intent_type=intent.intent_type.value,
                        goal=intent.goal,
                        plan_id=variant_id_fail,
                        outcome="failed",
                        timestamp=ts_fail,
                        state=snap_fail,
                        state_signature=compute_state_signature(snap_fail),
                        failed_step_index=intent.current_step,
                        failure_type="driver_failure",
                    )
                    mutations.extend(plan_fail_muts)

                    # Score meta: adjust plan penalty weight
                    if plan_fail_muts:
                        updated_drv_plan = plan_fail_muts[0]["value"]
                        plan_meta_drv = lookup_score_meta(snap_fail, "plan")
                        plan_drv_adj = build_score_meta_adjustment(
                            "plan", updated_drv_plan, plan_meta_drv
                        )
                        if plan_drv_adj:
                            plan_drv_adj[0]["value"]["last_updated_at"] = ts_fail
                            mutations.extend(plan_drv_adj)
                            _dpsc = updated_drv_plan["success_count"]
                            _dpfc = updated_drv_plan["failure_count"]
                            _dpec = _dpsc + _dpfc
                            _old_dpw = get_penalty_weight(plan_meta_drv)
                            _new_dpw = plan_drv_adj[0]["value"][
                                "failure_penalty_weight"
                            ]
                            events.append(
                                build_meta_adjusted_event(
                                    scope="plan",
                                    old_weight=_old_dpw,
                                    new_weight=_new_dpw,
                                    success_rate=_dpsc / _dpec if _dpec else 0.0,
                                    failure_rate=_dpfc / _dpec if _dpec else 0.0,
                                    execution_count=_dpec,
                                    delta_applied=_new_dpw - _old_dpw,
                                    adjustment_count=plan_drv_adj[0]["value"][
                                        "adjustment_count"
                                    ],
                                    cumulative_delta=abs(
                                        _new_dpw - DEFAULT_PENALTY_WEIGHT
                                    ),
                                    failure_count=_dpfc,
                                    session_name=intent.session_name,
                                    run_id=intent.goal.get("run_id"),
                                )
                            )
                            _sat_dpev = _maybe_saturation_event(
                                plan_drv_adj,
                                "plan",
                                _dpsc,
                                _dpfc,
                                intent.session_name,
                                intent.goal.get("run_id"),
                            )
                            if _sat_dpev:
                                events.append(_sat_dpev)

            mutations.append(self._deactivate_intent(intent.intent_id))

            # Phase 2: promotion (events appended after all terminal events)
            promo_mutations, promo_events = self._promote_next_pending(
                store,
                mutations,
                event.session_name,
            )
            mutations.extend(promo_mutations)
            events.extend(promo_events)
        else:
            # Non-terminal: append step events from driver
            events.extend(step_result.events)
            # Record step event correlation for newly emitted step events
            self._record_step_correlations(
                step_result.events, intent.intent_id, mutations
            )
            # Update active index with advanced step
            self._update_active_index(
                mutations, step_result.mutations, intent.intent_id
            )

    def _handle_step_failure(
        self,
        store: RuntimeStateStore,
        event: SchedulerEvent,
        intent: Intent,
        step_index: int,
        execution_id: str,
        result: ExecutionResult,
        mutations: list[dict[str, Any]],
        events: list[SchedulerEvent],
    ) -> None:
        """Process a failed execution step. MVP: fail intent immediately.

        Event ordering:
            Phase 1 (Intent A terminal): step_failed, intent_failed
            Phase 2 (Intent B activation): step event, step_dispatched
        """
        failure_reason = result.error or f"execution_{result.status.value}"

        # Phase 1: step-level observability
        events.append(
            build_orch_intent_step_failed_event(
                intent_id=intent.intent_id,
                step_index=step_index,
                execution_id=execution_id,
                failure_reason=failure_reason,
                session_name=event.session_name,
                run_id=event.run_id,
            )
        )

        step_result = self._driver.fail_workflow(intent, failure_reason)
        mutations.extend(step_result.mutations)

        # Phase 1 continued: intent-level terminal event (coordinator owns this)
        events.append(
            build_orch_intent_failed_event(
                intent_id=intent.intent_id,
                intent_type=intent.intent_type.value,
                reason=failure_reason,
                step_index=step_index,
                session_name=intent.session_name,
                run_id=intent.goal.get("run_id"),
            )
        )

        # Intent memory: record failure with classification
        _STATUS_TO_FAILURE_TYPE = {
            ExecutionStatus.FAILED: "execution_failed",
            ExecutionStatus.TIMED_OUT: "execution_timed_out",
            ExecutionStatus.REJECTED: "execution_rejected",
        }
        failure_type = _STATUS_TO_FAILURE_TYPE.get(result.status, "execution_failed")
        ts_exec_fail = datetime.now(timezone.utc).isoformat()
        exec_fail_muts = build_memory_update_mutations(
            intent_type=intent.intent_type.value,
            goal=intent.goal,
            outcome="failed",
            reason=failure_reason,
            timestamp=ts_exec_fail,
            state=store.snapshot(),
            failure_type=failure_type,
        )
        mutations.extend(exec_fail_muts)

        # Score meta: adjust intent penalty weight
        if exec_fail_muts:
            updated_exec_mem = exec_fail_muts[0]["value"]
            intent_meta_exec = lookup_score_meta(store.snapshot(), "intent")
            exec_adj = build_score_meta_adjustment(
                "intent", updated_exec_mem, intent_meta_exec
            )
            if exec_adj:
                exec_adj[0]["value"]["last_updated_at"] = ts_exec_fail
                mutations.extend(exec_adj)
                _esc = updated_exec_mem["success_count"]
                _efc = updated_exec_mem["failure_count"]
                _eec = _esc + _efc
                _old_ew = get_penalty_weight(intent_meta_exec)
                _new_ew = exec_adj[0]["value"]["failure_penalty_weight"]
                events.append(
                    build_meta_adjusted_event(
                        scope="intent",
                        old_weight=_old_ew,
                        new_weight=_new_ew,
                        success_rate=_esc / _eec if _eec else 0.0,
                        failure_rate=_efc / _eec if _eec else 0.0,
                        execution_count=_eec,
                        delta_applied=_new_ew - _old_ew,
                        adjustment_count=exec_adj[0]["value"]["adjustment_count"],
                        cumulative_delta=abs(_new_ew - DEFAULT_PENALTY_WEIGHT),
                        failure_count=_efc,
                        session_name=intent.session_name,
                        run_id=intent.goal.get("run_id"),
                    )
                )
                _sat_eev = _maybe_saturation_event(
                    exec_adj,
                    "intent",
                    _esc,
                    _efc,
                    intent.session_name,
                    intent.goal.get("run_id"),
                )
                if _sat_eev:
                    events.append(_sat_eev)

        # Plan memory: record failure per-variant (with causal context)
        variant_id_exec = self._get_variant_id(store, intent.intent_id)
        if variant_id_exec:
            snap_exec = store.snapshot()
            exec_plan_muts = build_plan_memory_update_mutations(
                intent_type=intent.intent_type.value,
                goal=intent.goal,
                plan_id=variant_id_exec,
                outcome="failed",
                timestamp=ts_exec_fail,
                state=snap_exec,
                state_signature=compute_state_signature(snap_exec),
                failed_step_index=step_index,
                failure_type=failure_type,
            )
            mutations.extend(exec_plan_muts)

            # Score meta: adjust plan penalty weight
            if exec_plan_muts:
                updated_exec_plan = exec_plan_muts[0]["value"]
                plan_meta_exec = lookup_score_meta(snap_exec, "plan")
                plan_exec_adj = build_score_meta_adjustment(
                    "plan", updated_exec_plan, plan_meta_exec
                )
                if plan_exec_adj:
                    plan_exec_adj[0]["value"]["last_updated_at"] = ts_exec_fail
                    mutations.extend(plan_exec_adj)
                    _epsc = updated_exec_plan["success_count"]
                    _epfc = updated_exec_plan["failure_count"]
                    _epec = _epsc + _epfc
                    _old_epw = get_penalty_weight(plan_meta_exec)
                    _new_epw = plan_exec_adj[0]["value"]["failure_penalty_weight"]
                    events.append(
                        build_meta_adjusted_event(
                            scope="plan",
                            old_weight=_old_epw,
                            new_weight=_new_epw,
                            success_rate=_epsc / _epec if _epec else 0.0,
                            failure_rate=_epfc / _epec if _epec else 0.0,
                            execution_count=_epec,
                            delta_applied=_new_epw - _old_epw,
                            adjustment_count=plan_exec_adj[0]["value"][
                                "adjustment_count"
                            ],
                            cumulative_delta=abs(_new_epw - DEFAULT_PENALTY_WEIGHT),
                            failure_count=_epfc,
                            session_name=intent.session_name,
                            run_id=intent.goal.get("run_id"),
                        )
                    )
                    _sat_epev = _maybe_saturation_event(
                        plan_exec_adj,
                        "plan",
                        _epsc,
                        _epfc,
                        intent.session_name,
                        intent.goal.get("run_id"),
                    )
                    if _sat_epev:
                        events.append(_sat_epev)

        mutations.append(self._deactivate_intent(intent.intent_id))

        # Phase 2: promotion
        promo_mutations, promo_events = self._promote_next_pending(
            store,
            mutations,
            event.session_name,
        )
        mutations.extend(promo_mutations)
        events.extend(promo_events)

    # ── Scheduler handler: cancellation ──────────────────────────────

    def _handle_intent_cancel(
        self, store: RuntimeStateStore, event: SchedulerEvent
    ) -> SchedulerExecutionResult:
        """Handle intent_cancel_requested events."""
        intent_id = event.payload.get("intent_id", "")
        reason = event.payload.get("reason", "cancelled")

        if not intent_id:
            return SchedulerExecutionResult(
                metadata={"skipped": True, "reason": "missing_intent_id"}
            )

        intent = self._get_intent_from_store(store, intent_id)
        if intent is None or intent.is_terminal:
            return SchedulerExecutionResult(
                metadata={"skipped": True, "reason": "not_found_or_terminal"}
            )

        mutations: list[dict[str, Any]] = []
        events: list[SchedulerEvent] = []

        step_result = self._driver.cancel_workflow(intent, reason)
        mutations.extend(step_result.mutations)

        # Phase 1: intent-level terminal event (coordinator owns this)
        events.append(
            build_orch_intent_cancelled_event(
                intent_id=intent.intent_id,
                intent_type=intent.intent_type.value,
                reason=reason,
                session_name=intent.session_name,
                run_id=intent.goal.get("run_id"),
            )
        )

        mutations.append(self._deactivate_intent(intent_id))

        # Phase 2: promotion
        promo_mutations, promo_events = self._promote_next_pending(
            store,
            mutations,
            event.session_name,
        )
        mutations.extend(promo_mutations)
        events.extend(promo_events)

        _log(f"cancelled intent: {intent_id} reason={reason}")
        return SchedulerExecutionResult(
            mutations=mutations,
            emitted_events=events,
            metadata={"intent_id": intent_id, "cancelled": True},
        )

    # ── Internal: plan memory helpers ──────────────────────────────────

    @staticmethod
    def _get_variant_id(store: RuntimeStateStore, intent_id: str) -> str:
        """Extract the variant_id for an active intent from the index.

        Returns empty string if not found (pre-upgrade intents, or
        single-variant plans that don't set variant_id).
        """
        active_meta = store.get(f"active_intent.{intent_id}")
        if active_meta is None:
            return ""
        return active_meta.get("variant_id", "")

    # ── Internal: activation ─────────────────────────────────────────

    def _activate_intent(
        self, intent: Intent, store: RuntimeStateStore
    ) -> tuple[list[dict[str, Any]], list[SchedulerEvent]]:
        """Activate a PENDING intent: derive plan, emit first step.

        Returns (mutations, events). Writes both intent:{id} and
        active_intent.{id}.

        If the driver signals immediate failure (no plan), the coordinator
        emits orch_intent_failed and does NOT write active membership.
        """
        mutations: list[dict[str, Any]] = []
        events: list[SchedulerEvent] = []

        step_result = self._driver.start_workflow(intent, store.snapshot())
        mutations.extend(step_result.mutations)

        if step_result.terminal:
            # Immediate failure (e.g., no plan available)
            events.append(
                build_orch_intent_failed_event(
                    intent_id=intent.intent_id,
                    intent_type=intent.intent_type.value,
                    reason=step_result.terminal_reason,
                    step_index=0,
                    session_name=intent.session_name,
                    run_id=intent.goal.get("run_id"),
                )
            )
            # Do NOT write active_intent — intent goes directly to FAILED
            return mutations, events

        # Non-terminal: activation succeeded
        events.extend(step_result.events)

        # Extract total_steps and variant_id from driver outputs
        total_steps = 0
        for m in step_result.mutations:
            if m.get("key") == intent_store_key(intent.intent_id) and m["op"] == "SET":
                total_steps = m["value"].get("total_steps", 0)
                break

        variant_id = ""
        for ev in step_result.events:
            vid = ev.metadata.get("_orch_variant_id", "")
            if vid:
                variant_id = vid
                break

        # Write active membership index (includes variant_id for plan memory)
        mutations.append(
            {
                "op": "SET",
                "key": f"active_intent.{intent.intent_id}",
                "value": {
                    "priority": intent.priority,
                    "intent_type": intent.intent_type.value,
                    "status": IntentStatus.ACTIVE.value,
                    "activated_at": intent.created_at,
                    "current_step": 0,
                    "total_steps": total_steps,
                    "variant_id": variant_id,
                },
            }
        )

        # Record step event correlation for emitted step events
        self._record_step_correlations(step_result.events, intent.intent_id, mutations)

        return mutations, events

    def _record_step_correlations(
        self,
        events: list[SchedulerEvent],
        intent_id: str,
        mutations: list[dict[str, Any]],
    ) -> None:
        """Write intent_step_events.{event_id} -> {intent_id, step_index}
        for any orchestration-owned step events."""
        for ev in events:
            if ev.metadata.get("_orch_intent_id") == intent_id:
                step_index = ev.metadata.get("_orch_step_index")
                if step_index is not None:
                    mutations.append(
                        {
                            "op": "SET",
                            "key": f"intent_step_events.{ev.event_id}",
                            "value": {
                                "intent_id": intent_id,
                                "step_index": step_index,
                            },
                        }
                    )

    # ── Internal: pending promotion ──────────────────────────────────

    def _promote_next_pending(
        self,
        store: RuntimeStateStore,
        pending_mutations: list[dict[str, Any]],
        session_name: str,
    ) -> tuple[list[dict[str, Any]], list[SchedulerEvent]]:
        """Find next PENDING intent and activate it if slot will be free.

        Accounts for REMOVE mutations in pending_mutations that haven't
        been applied yet (the deactivation of the current intent).

        Returns (mutations, events) for the promoted intent.
        """
        # Count active intents remaining after pending mutations
        removing = {
            m["key"]
            for m in pending_mutations
            if m.get("op") == "REMOVE" and m.get("key", "").startswith("active_intent.")
        }

        current_active = self._get_active_intents(store)
        remaining_count = sum(
            1
            for a in current_active
            if f"active_intent.{a['intent_id']}" not in removing
        )

        if remaining_count >= self._max_active:
            return [], []

        # Find PENDING intents
        snapshot = store.snapshot()
        pending: list[Intent] = []
        for key, val in snapshot.items():
            if (
                key.startswith("intent:")
                and isinstance(val, dict)
                and val.get("status") == IntentStatus.PENDING.value
            ):
                try:
                    pending.append(Intent.from_dict(val))
                except Exception:
                    continue

        if not pending:
            return [], []

        # Deterministic sort: priority asc, created_at, intent_id
        pending.sort(key=lambda i: (i.priority, i.created_at, i.intent_id))

        next_intent = pending[0]
        _log(f"promoting pending intent: {next_intent.intent_id}")

        return self._activate_intent(next_intent, store)

    # ── Internal: state helpers ──────────────────────────────────────

    def _get_active_intents(self, store: RuntimeStateStore) -> list[dict[str, Any]]:
        """Scan keyed index for active intents, sorted deterministically.

        Sort order: priority ascending, then activated_at, then intent_id.
        """
        prefix = "active_intent."
        active: list[dict[str, Any]] = []
        for key in store.keys():
            if key.startswith(prefix):
                val = store.get(key)
                if val is not None:
                    entry = dict(val)
                    entry["intent_id"] = key[len(prefix) :]
                    active.append(entry)
        active.sort(
            key=lambda x: (
                x.get("priority", 100),
                x.get("activated_at", ""),
                x.get("intent_id", ""),
            )
        )
        return active

    @staticmethod
    def _deactivate_intent(intent_id: str) -> dict[str, Any]:
        """Build REMOVE mutation for active_intent.{intent_id}."""
        return {"op": "REMOVE", "key": f"active_intent.{intent_id}"}

    @staticmethod
    def _get_intent_from_store(
        store: RuntimeStateStore, intent_id: str
    ) -> Intent | None:
        """Load an intent from the store."""
        raw = store.get(intent_store_key(intent_id))
        if raw is None:
            return None
        return Intent.from_dict(raw)

    @staticmethod
    def _update_active_index(
        mutations: list[dict[str, Any]],
        driver_mutations: list[dict[str, Any]],
        intent_id: str,
    ) -> None:
        """Update active_intent.{id} index from driver mutations (non-terminal only)."""
        for m in driver_mutations:
            if m.get("key") == intent_store_key(intent_id) and m["op"] == "SET":
                intent_data = m["value"]
                status = intent_data.get("status", "")
                if status not in (
                    IntentStatus.COMPLETED.value,
                    IntentStatus.FAILED.value,
                ):
                    mutations.append(
                        {
                            "op": "SET",
                            "key": f"active_intent.{intent_id}",
                            "value": {
                                "priority": intent_data.get("priority", 100),
                                "intent_type": intent_data.get("intent_type", "custom"),
                                "status": status,
                                "activated_at": intent_data.get("created_at", ""),
                                "current_step": intent_data.get("current_step", 0),
                                "total_steps": intent_data.get("total_steps", 0),
                            },
                        }
                    )
                break
