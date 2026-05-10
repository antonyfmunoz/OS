"""
Replay-safe determinism boundary for the LLM planning layer.

ReplayableStrategy implements DecisionStrategy and owns the entire
determinism contract:
- Config enforcement (enabled, intent eligibility).
- State canonicalization before any downstream use.
- Per-state-hash locking to prevent duplicate LLM calls under concurrency.
- Non-leaky timeout enforcement via ThreadPoolExecutor.
- Replay store (internal, keyed by state_hash).
- Selection policy application.
- SchedulerEvent emission in deterministic proposal_step_index order.
- Full pipeline record capture (LLMDecisionRecord).
- Sentinel DecisionOutput construction (terminal, suppress-downstream).

The inner LLMPlanningStrategy is a subordinate component that never
knows about replay, timeouts, or event emission.

Design constraints:
- emitted_events in LLMDecisionRecord is the SINGLE SOURCE OF TRUTH
  for replay.  selected_event_indices is metadata only.
- validation_result is explicitly tied to schema_hash at decision time.
- proposal_step_index is the canonical ordering.  Do not rely on
  scheduler FIFO guarantees.
- Timeout uses concurrent.futures.ThreadPoolExecutor, not daemon threads.
"""

from __future__ import annotations

import concurrent.futures
import os
import sys
import threading
import weakref
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from eos_ai.transport.decision_engine import DecisionOutput
from eos_ai.transport.event_scheduler import EventScheduler, SchedulerEvent
from eos_ai.transport.intent_models import IntentType, get_active_intents_from_state
from eos_ai.transport.llm_decision_events import (
    build_llm_decision_accepted_event,
    build_llm_decision_received_event,
    build_llm_decision_rejected_event,
    build_llm_decision_requested_event,
    build_llm_decision_skipped_event,
    build_llm_response_drift_event,
)
from eos_ai.transport.llm_planner import (
    EventTypeRegistry,
    LLMEventProposal,
    LLMPlannerConfig,
    LLMPlanningStrategy,
    LLMProposalResult,
    ProposedEvent,
    SelectionPolicy,
    ValidationResult,
    _canonical_json,
    _sha256_hex,
    _sha256_prefix,
)

_LOG_PREFIX = "[substrate.llm_replay]"


def _log(msg: str) -> None:
    print(f"{_LOG_PREFIX} {msg}", file=sys.stderr)


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ─── Decision record ─────────────────────────────────────────────────


@dataclass(frozen=True)
class LLMDecisionRecord:
    """Full pipeline trace stored for replay.

    emitted_events is the SINGLE SOURCE OF TRUTH for replay.
    selected_event_indices is metadata only — never used to
    recompute event emission.

    validation_result is explicitly tied to schema_hash at
    decision time.  Replay strict mode compares recorded
    schema_hash to current registry schema_hash.
    """

    schema_version: int
    validation_version: int
    schema_hash: str
    state_hash: str
    prompt_hash: str
    raw_response: str
    response_hash: str
    canonical_json: str
    proposal_id: str
    reasoning_hash: str
    validation_result: ValidationResult
    emitted_events: tuple[ProposedEvent, ...]
    selected_event_indices: tuple[int, ...]
    selection_policy: str
    timestamp: str
    parse_failed: bool = False


# ─── Replayable strategy ─────────────────────────────────────────────


class ReplayableStrategy:
    """Determinism boundary.  Implements DecisionStrategy.

    Wraps LLMPlanningStrategy and handles:
    - Config enforcement at the entry point.
    - Per-state-hash locking to prevent duplicate LLM calls.
    - Non-leaky timeout via ThreadPoolExecutor.
    - Replay store (internal dict[state_hash, LLMDecisionRecord]).
    - Drift detection within identical execution context only.
    - Selection policy application.
    - SchedulerEvent emission in deterministic proposal_step_index order.
    - Full pipeline record capture.
    - Sentinel DecisionOutput (is_terminal=True, suppress_downstream=True).

    The sentinel is a control signal, not a domain decision.  It tells
    IntentAwareStrategy "I handled this, stop the chain."  It carries
    event_type="llm_proposal_accepted" which has no subscribers and
    produces no mutations.
    """

    def __init__(
        self,
        inner: LLMPlanningStrategy,
        scheduler: EventScheduler,
        config: LLMPlannerConfig,
        registry: EventTypeRegistry,
    ) -> None:
        self._inner = inner
        self._scheduler = scheduler
        self._config = config
        self._registry = registry

        # Replay store: state_hash → LLMDecisionRecord
        self._replay_store: dict[str, LLMDecisionRecord] = {}
        self._store_lock = threading.Lock()

        # Per-key locks to prevent duplicate LLM calls for same state.
        # WeakValueDictionary: locks are GC'd when no thread holds a
        # reference, preventing unbounded growth from unique state hashes.
        self._key_locks: weakref.WeakValueDictionary[str, threading.Lock] = (
            weakref.WeakValueDictionary()
        )
        self._key_locks_guard = threading.Lock()

        # Drift detection: prompt_hash → set of all distinct response_hashes.
        # Drift fires when prompt_hash matches but response_hash is novel.
        # prompt_hash is composite over (prompt, model, temp, config_v, registry_v).
        self._drift_store: dict[str, set[str]] = {}
        self._drift_lock = threading.Lock()

        # ThreadPoolExecutor for non-leaky LLM timeouts.
        # Parallel capacity for different state_hash values; per-key lock
        # deduplicates same-state calls.
        self._executor = concurrent.futures.ThreadPoolExecutor(
            max_workers=min(32, (os.cpu_count() or 4) * 4),
            thread_name_prefix="llm_planner",
        )

    @property
    def name(self) -> str:
        return "llm_replayable"

    def shutdown(self) -> None:
        """Shut down the executor cleanly.  Call on system teardown."""
        self._executor.shutdown(wait=False)

    # ── Per-key locking ──────────────────────────────────────────────

    def _get_key_lock(self, state_hash: str) -> threading.Lock:
        """Get or create a lock for a specific state_hash.

        Returns a strong reference.  The caller MUST hold this reference
        for the duration of its critical section.  Once all strong refs
        are dropped, the WeakValueDictionary entry is GC'd, preventing
        unbounded lock registry growth.
        """
        with self._key_locks_guard:
            lock = self._key_locks.get(state_hash)
            if lock is None:
                lock = threading.Lock()
                self._key_locks[state_hash] = lock
            return lock

    # ── Replay store access ──────────────────────────────────────────

    def _store_get(self, state_hash: str) -> LLMDecisionRecord | None:
        with self._store_lock:
            return self._replay_store.get(state_hash)

    def _store_put(self, state_hash: str, record: LLMDecisionRecord) -> None:
        with self._store_lock:
            self._replay_store[state_hash] = record

    # ── Drift detection ──────────────────────────────────────────────

    def _check_drift(
        self, prompt_hash: str, response_hash: str, session_name: str
    ) -> None:
        """Detect response drift within identical execution context.

        Drift = same prompt_hash (composite of prompt + model + temp +
        config_v + registry_v) but a NOVEL response_hash not previously
        seen for that prompt_hash.

        Tracks all distinct response_hash values per prompt_hash so
        drift fires once per newly observed variant, not repeatedly.

        Different prompt_hash values are NOT drift — they represent
        different execution contexts.
        """
        emit_drift = False
        with self._drift_lock:
            seen = self._drift_store.get(prompt_hash)
            if seen is None:
                # First response for this prompt_hash — no drift
                self._drift_store[prompt_hash] = {response_hash}
            elif response_hash not in seen:
                # Novel response for known prompt_hash — drift
                seen.add(response_hash)
                emit_drift = True

        if emit_drift:
            _log(
                f"response drift detected: prompt_hash={prompt_hash}, "
                f"new_response={response_hash}"
            )
            self._scheduler.emit(
                build_llm_response_drift_event(
                    prompt_hash=prompt_hash,
                    response_hash_a="<multi>",
                    response_hash_b=response_hash,
                    session_name=session_name,
                )
            )

    # ── Event emission ───────────────────────────────────────────────

    def _emit_proposed_events(
        self,
        events: tuple[ProposedEvent, ...],
        proposal_id: str,
        session_name: str,
    ) -> None:
        """Emit selected ProposedEvents as SchedulerEvents.

        HARD BOUNDARY: events are sorted by their position in the tuple
        (which IS proposal_step_index order) before emission.  Every
        emitted event carries proposal_id and proposal_step_index in
        metadata.  source="llm_planner".

        Invariant: for source=="llm_planner", emitted events are a
        deterministic function of (canonical_proposal, selection_policy).
        Ordering is defined by proposal_step_index, not scheduler FIFO.
        """
        # Events are already in proposal_step_index order from the
        # selection policy.  Enumerate to get the index.
        for step_index, proposed in enumerate(events):
            sev = SchedulerEvent(
                event_type=proposed.event_type,
                session_name=session_name,
                source="llm_planner",
                payload=proposed.payload,
                metadata={
                    "proposal_id": proposal_id,
                    "proposal_step_index": step_index,
                },
            )
            self._scheduler.emit(sev)

    # ── Sentinel construction ────────────────────────────────────────

    @staticmethod
    def _build_sentinel(
        proposal_id: str,
        state_hash: str,
        session_name: str,
        event_count: int,
    ) -> DecisionOutput:
        """Build the terminal sentinel DecisionOutput.

        This is a CONTROL SIGNAL, not a domain decision.  It tells
        IntentAwareStrategy "I handled this, stop the chain."

        Invariant: event_type=="llm_proposal_accepted" must not emit
        further events or be processed as a normal decision.
        """
        return DecisionOutput(
            decision_id=f"llm_{proposal_id[:12]}",
            event_type="llm_proposal_accepted",
            payload={
                "proposal_id": proposal_id,
                "session_name": session_name,
                "emitted_event_count": event_count,
            },
            reasoning=f"LLM proposal {proposal_id[:12]} accepted ({event_count} events)",
            state_hash=state_hash,
            strategy_name="llm_replayable",
            is_terminal=True,
            suppress_downstream=True,
        )

    # ── Main evaluation ──────────────────────────────────────────────

    def evaluate(self, state: dict[str, Any]) -> DecisionOutput | None:
        """Evaluate state via the LLM planning layer.

        Implements DecisionStrategy protocol.  Returns terminal sentinel
        on success, None on any failure (silent fallback to planner).
        """
        session_name = state.get("session_name", "")

        # 1. Config check
        if not self._config.enabled:
            self._scheduler.emit(
                build_llm_decision_skipped_event(
                    reason="disabled",
                    state_hash="",
                    session_name=session_name,
                )
            )
            return None

        # 2. Intent type eligibility
        if self._config.enabled_intent_types is not None:
            active_intents = get_active_intents_from_state(state)
            if not active_intents:
                self._scheduler.emit(
                    build_llm_decision_skipped_event(
                        reason="no_active_intents",
                        state_hash="",
                        session_name=session_name,
                    )
                )
                return None
            eligible = any(
                self._config.is_enabled_for_intent(intent.intent_type)
                for intent in active_intents
            )
            if not eligible:
                self._scheduler.emit(
                    build_llm_decision_skipped_event(
                        reason="intent_type_excluded",
                        state_hash="",
                        session_name=session_name,
                    )
                )
                return None

        # 3. Canonicalize state
        canonical_state = _canonical_json(state)
        state_hash = _sha256_prefix(canonical_state)

        # 4. Acquire per-key lock
        key_lock = self._get_key_lock(state_hash)
        with key_lock:
            # 5. Re-check store inside lock
            record = self._store_get(state_hash)

            if record is not None:
                # ── CACHE HIT (replay path) ──────────────────────
                return self._handle_cache_hit(record, state_hash, session_name)

            # ── CACHE MISS (live LLM call) ───────────────────────
            return self._handle_cache_miss(
                canonical_state, state_hash, session_name, state
            )

    # ── Cache hit ────────────────────────────────────────────────────

    def _handle_cache_hit(
        self,
        record: LLMDecisionRecord,
        state_hash: str,
        session_name: str,
    ) -> DecisionOutput | None:
        """Handle replay from stored record.

        Re-emits from record.emitted_events (single source of truth).
        Does NOT recompute from selected_event_indices.

        In strict mode, compares recorded schema_hash to current
        registry schema_hash.  If they differ, re-validates the
        canonical proposal against the current registry.
        """
        if self._config.strict_replay_validation:
            # Strict replay always re-runs live validation against the
            # current registry, regardless of schema_hash match.  Schema
            # hash equality is a fast signal but NOT sufficient — validation
            # rules may evolve independently of schema registration.
            if record.canonical_json:
                revalidation = self._revalidate_canonical(record.canonical_json)
                if revalidation is None or not revalidation.valid:
                    _log(
                        f"strict re-validation failed for state_hash={state_hash}, "
                        f"falling through to deterministic planner"
                    )
                    return None
            else:
                _log("no canonical_json in record, falling through")
                return None

        # Re-emit from stored emitted_events (source of truth)
        self._emit_proposed_events(
            events=record.emitted_events,
            proposal_id=record.proposal_id,
            session_name=session_name,
        )

        return self._build_sentinel(
            proposal_id=record.proposal_id,
            state_hash=state_hash,
            session_name=session_name,
            event_count=len(record.emitted_events),
        )

    def _revalidate_canonical(self, canonical_json: str) -> ValidationResult | None:
        """Re-validate a canonical proposal JSON against the current registry."""
        try:
            import json

            parsed = json.loads(canonical_json)
            raw_events = parsed.get("events", [])
            if not isinstance(raw_events, list):
                return None
            events = tuple(
                ProposedEvent(
                    event_type=e["event_type"],
                    payload=e.get("payload", {}),
                    description=e.get("description"),
                )
                for e in raw_events
                if isinstance(e, dict) and "event_type" in e
            )
            proposal = LLMEventProposal(
                events=events,
                proposal_id="revalidation",
            )
            return self._registry.validate_proposal(proposal, self._config)
        except Exception as exc:
            _log(f"re-validation parse error: {exc}")
            return None

    # ── Cache miss ───────────────────────────────────────────────────

    def _handle_cache_miss(
        self,
        canonical_state: str,
        state_hash: str,
        session_name: str,
        state: dict[str, Any],
    ) -> DecisionOutput | None:
        """Handle live LLM call with timeout, validation, and recording."""
        # Extract active intent IDs for observability
        active_intents = get_active_intents_from_state(state)
        intent_ids = [i.intent_id for i in active_intents]
        intent_dicts = [i.to_dict() for i in active_intents]

        # Emit REQUESTED
        self._scheduler.emit(
            build_llm_decision_requested_event(
                state_hash=state_hash,
                prompt_hash="",  # filled after prompt construction
                active_intent_ids=intent_ids,
                session_name=session_name,
            )
        )

        # Call inner with non-leaky timeout via ThreadPoolExecutor
        timeout_s = self._config.timeout_ms / 1000.0
        future = self._executor.submit(
            self._inner.propose, canonical_state, state_hash, intent_dicts
        )

        try:
            result: LLMProposalResult = future.result(timeout=timeout_s)
        except concurrent.futures.TimeoutError:
            _log(f"LLM call timed out after {self._config.timeout_ms}ms")
            future.cancel()
            self._scheduler.emit(
                build_llm_decision_rejected_event(
                    proposal_id="",
                    prompt_hash="",
                    rejection_reason="timeout",
                    rejected_event_count=0,
                    session_name=session_name,
                )
            )
            return None
        except Exception as exc:
            _log(f"LLM call failed: {exc}")
            self._scheduler.emit(
                build_llm_decision_rejected_event(
                    proposal_id="",
                    prompt_hash="",
                    rejection_reason=f"error: {exc}",
                    rejected_event_count=0,
                    session_name=session_name,
                )
            )
            return None

        # Parse failure
        if result.parse_failed or result.proposal is None:
            _log(f"proposal parse failed: {result.proposal_id}")
            self._scheduler.emit(
                build_llm_decision_rejected_event(
                    proposal_id=result.proposal_id,
                    prompt_hash=result.prompt_hash,
                    rejection_reason="parse_error",
                    rejected_event_count=0,
                    session_name=session_name,
                )
            )
            return None

        # Emit RECEIVED
        self._scheduler.emit(
            build_llm_decision_received_event(
                proposal_id=result.proposal_id,
                prompt_hash=result.prompt_hash,
                response_hash=result.response_hash,
                event_count=len(result.proposal.events),
                latency_ms=result.latency_ms,
                session_name=session_name,
            )
        )

        # Drift detection — only within identical execution context.
        # prompt_hash is composite over (prompt, model, temp, config_v, registry_v).
        # Different prompt_hash = different context = not drift.
        self._check_drift(result.prompt_hash, result.response_hash, session_name)

        # Validation
        validation = result.validation
        if validation is None or not validation.accepted_events:
            reason = "all_events_rejected"
            rejected_count = len(result.proposal.events)
            if validation and validation.rejection_reasons:
                reason = "; ".join(validation.rejection_reasons.values())
            self._scheduler.emit(
                build_llm_decision_rejected_event(
                    proposal_id=result.proposal_id,
                    prompt_hash=result.prompt_hash,
                    rejection_reason=reason,
                    rejected_event_count=rejected_count,
                    session_name=session_name,
                )
            )
            return None

        # Apply selection policy
        accepted = validation.accepted_events
        if self._config.selection_policy == SelectionPolicy.FIRST:
            selected = (accepted[0],)
            selected_indices = (0,)
        else:  # ALL
            selected = accepted
            selected_indices = tuple(range(len(accepted)))

        # Emit selected events in deterministic proposal_step_index order
        self._emit_proposed_events(
            events=selected,
            proposal_id=result.proposal_id,
            session_name=session_name,
        )

        # Emit ACCEPTED
        self._scheduler.emit(
            build_llm_decision_accepted_event(
                proposal_id=result.proposal_id,
                emitted_event_count=len(selected),
                selection_policy=self._config.selection_policy.value,
                session_name=session_name,
            )
        )

        # Build and store full pipeline record
        record = LLMDecisionRecord(
            schema_version=self._config.config_version,
            validation_version=self._registry.version,
            schema_hash=self._registry.schema_hash,
            state_hash=state_hash,
            prompt_hash=result.prompt_hash,
            raw_response=result.raw_response,
            response_hash=result.response_hash,
            canonical_json=result.canonical_json or "",
            proposal_id=result.proposal_id,
            reasoning_hash=_sha256_prefix(result.proposal.reasoning or ""),
            validation_result=validation,
            emitted_events=selected,  # SINGLE SOURCE OF TRUTH
            selected_event_indices=selected_indices,  # metadata only
            selection_policy=self._config.selection_policy.value,
            timestamp=_utcnow_iso(),
            parse_failed=result.parse_failed,
        )
        self._store_put(state_hash, record)

        # Return terminal sentinel
        return self._build_sentinel(
            proposal_id=result.proposal_id,
            state_hash=state_hash,
            session_name=session_name,
            event_count=len(selected),
        )
