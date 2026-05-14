"""Persistent Operator Cognition Engine v1.

Central coordinator for persistent operator cognition.
Maintains all cognitive state across sessions, workflows,
runtime traversals, embodiment contexts, operational loops,
and temporal execution windows.

The cognition engine:
  - Maintains active operator context
  - Maintains working cognition (bounded window)
  - Maintains operational focus (operator-set)
  - Maintains active loops (7-state lifecycle)
  - Maintains continuity focus (cross-session)
  - Maintains temporal continuity (chronology)
  - Maintains cognition lineage (receipts)

The cognition engine CANNOT:
  - Execute actions directly
  - Generate its own operational intent
  - Self-direct or self-task
  - Bypass governance
  - Promote memory without operator consent

UMH substrate subsystem. Phase 96.8BT.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from core.cognition.persistent_operator_cognition_contracts_v1 import (
    ActiveOperationalFocus,
    AttentionWeightType,
    CognitionDecisionType,
    CognitionPhase,
    CognitiveCheckpoint,
    CognitiveLineageReceipt,
    ContinuityFocusState,
    LoopState,
    MODE_COGNITION_POLICIES,
    OpenOperationalLoop,
    OperationalIntentState,
    OperatorCognitiveState,
    OperatorMode,
    RuntimeAttentionMap,
    TemporalExecutionContext,
    WorkingCognitionWindow,
    _content_hash,
    _new_id,
    _now_iso,
)


class PersistentOperatorCognitionEngine:
    """Maintains persistent operator cognition across sessions.

    Single entrypoint for all cognition state management.
    Cannot execute actions — only maintains and exposes state.
    All mutations emit lineage receipts.
    """

    def __init__(
        self,
        session_id: str = "",
        state_dir: str | Path = "data/runtime/cognition_state",
    ) -> None:
        self._session_id = session_id or _new_id("sess")
        self._state_dir = Path(state_dir)
        self._state_dir.mkdir(parents=True, exist_ok=True)

        self._cognitive_state = OperatorCognitiveState(
            session_id=self._session_id,
        )
        self._working_window = WorkingCognitionWindow(
            session_id=self._session_id,
        )
        self._attention_map = RuntimeAttentionMap(
            session_id=self._session_id,
        )
        self._temporal_context = TemporalExecutionContext(
            session_id=self._session_id,
        )
        self._continuity_focus = ContinuityFocusState(
            session_id=self._session_id,
        )

        self._active_focuses: dict[str, ActiveOperationalFocus] = {}
        self._open_loops: dict[str, OpenOperationalLoop] = {}
        self._intents: dict[str, OperationalIntentState] = {}
        self._checkpoints: list[CognitiveCheckpoint] = []
        self._receipts: list[CognitiveLineageReceipt] = []

        self._total_focus_shifts: int = 0
        self._total_loop_operations: int = 0
        self._total_checkpoints: int = 0
        self._total_receipts: int = 0

    @property
    def session_id(self) -> str:
        return self._session_id

    @property
    def cognitive_state(self) -> OperatorCognitiveState:
        return self._cognitive_state

    @property
    def operator_mode(self) -> OperatorMode:
        return self._cognitive_state.operator_mode

    @property
    def phase(self) -> CognitionPhase:
        return self._cognitive_state.phase

    # ------------------------------------------------------------------
    # Operator mode management
    # ------------------------------------------------------------------

    def set_operator_mode(self, mode: OperatorMode) -> CognitiveLineageReceipt:
        """Set the operator mode. Adjusts cognition policies accordingly."""
        old_mode = self._cognitive_state.operator_mode
        self._cognitive_state.operator_mode = mode

        policy = MODE_COGNITION_POLICIES.get(mode.value, {})
        max_items = policy.get("cognition_persistence_depth", 5) * 4
        self._working_window.max_items = max_items
        self._working_window.mode = mode
        self._attention_map.mode = mode

        receipt = self._emit_receipt(
            decision_type=CognitionDecisionType.MODE_TRANSITION,
            action=f"mode_transition:{old_mode.value}->{mode.value}",
            component="cognition_engine",
            input_hash=_content_hash({"old_mode": old_mode.value}),
            output_hash=_content_hash({"new_mode": mode.value}),
        )
        self._sync_cognitive_state()
        return receipt

    # ------------------------------------------------------------------
    # Phase management
    # ------------------------------------------------------------------

    def set_phase(self, phase: CognitionPhase) -> bool:
        """Set the cognition phase. Returns False if transition invalid."""
        current = self._cognitive_state.phase
        if not self._is_valid_phase_transition(current, phase):
            return False
        self._cognitive_state.phase = phase
        self._cognitive_state.last_activity_iso = _now_iso()
        self._sync_cognitive_state()
        return True

    def _is_valid_phase_transition(
        self, from_phase: CognitionPhase, to_phase: CognitionPhase
    ) -> bool:
        valid = {
            CognitionPhase.INITIALIZED: {
                CognitionPhase.ACTIVE,
                CognitionPhase.TERMINATED,
            },
            CognitionPhase.ACTIVE: {
                CognitionPhase.FOCUSED,
                CognitionPhase.CHECKPOINTED,
                CognitionPhase.SUSPENDED,
                CognitionPhase.STALE,
                CognitionPhase.ARCHIVED,
                CognitionPhase.TERMINATED,
            },
            CognitionPhase.FOCUSED: {
                CognitionPhase.ACTIVE,
                CognitionPhase.CHECKPOINTED,
                CognitionPhase.SUSPENDED,
                CognitionPhase.STALE,
                CognitionPhase.ARCHIVED,
                CognitionPhase.TERMINATED,
            },
            CognitionPhase.CHECKPOINTED: {
                CognitionPhase.ACTIVE,
                CognitionPhase.RESUMED,
                CognitionPhase.TERMINATED,
            },
            CognitionPhase.SUSPENDED: {
                CognitionPhase.RESUMED,
                CognitionPhase.STALE,
                CognitionPhase.ARCHIVED,
                CognitionPhase.TERMINATED,
            },
            CognitionPhase.RESUMED: {
                CognitionPhase.ACTIVE,
                CognitionPhase.FOCUSED,
                CognitionPhase.TERMINATED,
            },
            CognitionPhase.STALE: {
                CognitionPhase.RESUMED,
                CognitionPhase.ARCHIVED,
                CognitionPhase.TERMINATED,
            },
            CognitionPhase.ARCHIVED: set(),
            CognitionPhase.TERMINATED: set(),
        }
        return to_phase in valid.get(from_phase, set())

    # ------------------------------------------------------------------
    # Focus management (operator-set only)
    # ------------------------------------------------------------------

    def set_focus(
        self,
        focus_type: str,
        description: str,
        priority: float = 1.0,
        related_workflow_ids: list[str] | None = None,
        related_loop_ids: list[str] | None = None,
    ) -> ActiveOperationalFocus:
        """Set a new operational focus. Always set_by=operator."""
        for existing in self._active_focuses.values():
            existing.active = False

        focus = ActiveOperationalFocus(
            session_id=self._session_id,
            focus_type=focus_type,
            focus_description=description,
            priority=priority,
            related_workflow_ids=related_workflow_ids or [],
            related_loop_ids=related_loop_ids or [],
            set_by="operator",
        )
        self._active_focuses[focus.focus_id] = focus
        self._cognitive_state.active_focus_id = focus.focus_id
        self._total_focus_shifts += 1

        self._emit_receipt(
            decision_type=CognitionDecisionType.FOCUS_SHIFT,
            action=f"focus_set:{focus_type}",
            component="cognition_engine",
            input_hash=_content_hash({"description": description}),
            output_hash=_content_hash(focus.to_dict()),
        )

        self._add_to_working_window({
            "type": "focus_shift",
            "focus_id": focus.focus_id,
            "focus_type": focus_type,
            "description": description,
        }, weight=AttentionWeightType.OPERATOR_FOCUS)

        self._sync_cognitive_state()
        return focus

    def get_active_focus(self) -> ActiveOperationalFocus | None:
        focus_id = self._cognitive_state.active_focus_id
        return self._active_focuses.get(focus_id)

    def get_all_focuses(self) -> list[ActiveOperationalFocus]:
        return list(self._active_focuses.values())

    # ------------------------------------------------------------------
    # Intent management (operator-originated only)
    # ------------------------------------------------------------------

    def register_intent(
        self,
        description: str,
        source_command: str = "",
        related_focus_ids: list[str] | None = None,
    ) -> OperationalIntentState:
        """Register an operator-originated intent. set_by always 'operator'."""
        intent = OperationalIntentState(
            session_id=self._session_id,
            intent_description=description,
            set_by="operator",
            source_command=source_command,
            related_focus_ids=related_focus_ids or [],
        )
        self._intents[intent.intent_id] = intent
        self._sync_cognitive_state()
        return intent

    def deactivate_intent(self, intent_id: str) -> bool:
        intent = self._intents.get(intent_id)
        if not intent:
            return False
        intent.active = False
        return True

    def get_active_intents(self) -> list[OperationalIntentState]:
        return [i for i in self._intents.values() if i.active]

    # ------------------------------------------------------------------
    # Open loop management
    # ------------------------------------------------------------------

    def open_loop(
        self,
        source_type: str,
        source_id: str,
        description: str,
        priority: float = 1.0,
        stale_after_seconds: float = 3600.0,
        tags: list[str] | None = None,
        related_workflow_ids: list[str] | None = None,
    ) -> OpenOperationalLoop:
        """Open a new operational loop."""
        loop = OpenOperationalLoop(
            session_id=self._session_id,
            source_type=source_type,
            source_id=source_id,
            description=description,
            priority=priority,
            stale_after_seconds=stale_after_seconds,
            tags=tags or [],
            related_workflow_ids=related_workflow_ids or [],
        )
        self._open_loops[loop.loop_id] = loop
        self._total_loop_operations += 1

        self._emit_receipt(
            decision_type=CognitionDecisionType.LOOP_PRIORITIZE,
            action=f"loop_opened:{source_type}",
            component="cognition_engine",
            input_hash=_content_hash({"source_id": source_id}),
            output_hash=_content_hash(loop.to_dict()),
        )

        self._add_to_working_window({
            "type": "loop_opened",
            "loop_id": loop.loop_id,
            "source_type": source_type,
            "description": description,
        }, weight=AttentionWeightType.LOOP_URGENCY)

        self._sync_cognitive_state()
        return loop

    def transition_loop(
        self,
        loop_id: str,
        to_state: LoopState,
        resolution_summary: str = "",
    ) -> bool:
        """Transition a loop to a new state."""
        loop = self._open_loops.get(loop_id)
        if not loop:
            return False

        valid_transitions: dict[LoopState, set[LoopState]] = {
            LoopState.ACTIVE: {
                LoopState.WAITING, LoopState.SUSPENDED,
                LoopState.STALE, LoopState.RESOLVED,
            },
            LoopState.WAITING: {
                LoopState.ACTIVE, LoopState.RESUMED,
                LoopState.STALE, LoopState.RESOLVED,
            },
            LoopState.SUSPENDED: {
                LoopState.RESUMED, LoopState.STALE,
                LoopState.ARCHIVED,
            },
            LoopState.STALE: {
                LoopState.RESUMED, LoopState.ARCHIVED,
            },
            LoopState.RESUMED: {
                LoopState.ACTIVE, LoopState.RESOLVED,
            },
            LoopState.RESOLVED: {LoopState.ARCHIVED},
            LoopState.ARCHIVED: set(),
        }

        if to_state not in valid_transitions.get(loop.state, set()):
            return False

        loop.state = to_state
        loop.last_touched = _now_iso()
        if resolution_summary:
            loop.resolution_summary = resolution_summary
        self._total_loop_operations += 1
        self._sync_cognitive_state()
        return True

    def get_active_loops(self) -> list[OpenOperationalLoop]:
        active_states = {LoopState.ACTIVE, LoopState.WAITING, LoopState.RESUMED}
        return [l for l in self._open_loops.values() if l.state in active_states]

    def get_all_loops(self) -> list[OpenOperationalLoop]:
        return list(self._open_loops.values())

    # ------------------------------------------------------------------
    # Working cognition window
    # ------------------------------------------------------------------

    def _add_to_working_window(
        self,
        item: dict[str, Any],
        weight: AttentionWeightType = AttentionWeightType.WORKFLOW,
    ) -> bool:
        w = self._attention_map.get_weight(weight)
        if not self._working_window.add_item(item, weight=w):
            self._working_window.evict_lowest_weight()
            return self._working_window.add_item(item, weight=w)
        return True

    def get_working_window(self) -> WorkingCognitionWindow:
        return self._working_window

    # ------------------------------------------------------------------
    # Attention management
    # ------------------------------------------------------------------

    def reweight_attention(
        self,
        weight_type: AttentionWeightType,
        value: float,
    ) -> CognitiveLineageReceipt:
        """Reweight an attention dimension."""
        old_weight = self._attention_map.get_weight(weight_type)
        self._attention_map.set_weight(weight_type, value)

        receipt = self._emit_receipt(
            decision_type=CognitionDecisionType.ATTENTION_REWEIGHT,
            action=f"reweight:{weight_type.value}:{old_weight:.2f}->{value:.2f}",
            component="cognition_engine",
            input_hash=_content_hash({"type": weight_type.value, "old": old_weight}),
            output_hash=_content_hash({"type": weight_type.value, "new": value}),
        )
        return receipt

    def get_attention_map(self) -> RuntimeAttentionMap:
        return self._attention_map

    # ------------------------------------------------------------------
    # Temporal continuity
    # ------------------------------------------------------------------

    def record_temporal_event(self) -> None:
        """Record a temporal event in the execution chronology."""
        self._temporal_context.chronology_entries += 1
        self._temporal_context.timestamp = _now_iso()

    def get_temporal_context(self) -> TemporalExecutionContext:
        return self._temporal_context

    def link_previous_session(
        self,
        previous_session_id: str,
        gap_seconds: float = 0.0,
    ) -> None:
        """Link this session to a previous one for continuity."""
        self._temporal_context.previous_session_id = previous_session_id
        self._temporal_context.continuity_gap_seconds = gap_seconds
        self._temporal_context.restart_count += 1
        self._temporal_context.last_resumption_iso = _now_iso()
        self._sync_cognitive_state()

    # ------------------------------------------------------------------
    # Continuity focus (cross-session restoration)
    # ------------------------------------------------------------------

    def restore_continuity(
        self,
        previous_session_id: str,
        focus_ids: list[str] | None = None,
        loop_ids: list[str] | None = None,
        workflow_ids: list[str] | None = None,
        continuity_score: float = 0.0,
    ) -> ContinuityFocusState:
        """Restore continuity from a previous session."""
        self._continuity_focus = ContinuityFocusState(
            session_id=self._session_id,
            previous_session_id=previous_session_id,
            restored_focus_ids=focus_ids or [],
            restored_loop_ids=loop_ids or [],
            restored_workflow_ids=workflow_ids or [],
            continuity_score=continuity_score,
            restoration_complete=True,
        )

        self._emit_receipt(
            decision_type=CognitionDecisionType.CONTINUITY_RESTORE,
            action=f"continuity_restore:from:{previous_session_id}",
            component="cognition_engine",
            input_hash=_content_hash({"previous_session": previous_session_id}),
            output_hash=_content_hash(self._continuity_focus.to_dict()),
        )

        self._cognitive_state.continuity_chain_length += 1
        self._sync_cognitive_state()
        return self._continuity_focus

    def get_continuity_focus(self) -> ContinuityFocusState:
        return self._continuity_focus

    # ------------------------------------------------------------------
    # Checkpointing
    # ------------------------------------------------------------------

    def create_checkpoint(self) -> CognitiveCheckpoint:
        """Create a full cognitive state checkpoint."""
        checkpoint = CognitiveCheckpoint(
            session_id=self._session_id,
            operator_mode=self._cognitive_state.operator_mode,
            phase=self._cognitive_state.phase,
            cognitive_state_snapshot=self._cognitive_state.to_dict(),
            active_focus_snapshot=(
                self.get_active_focus().to_dict()
                if self.get_active_focus()
                else {}
            ),
            open_loops_snapshot=[l.to_dict() for l in self.get_active_loops()],
            attention_snapshot=self._attention_map.to_dict(),
            continuity_chain_ids=[
                c.checkpoint_id for c in self._checkpoints[-5:]
            ],
        )
        self._checkpoints.append(checkpoint)
        self._cognitive_state.last_checkpoint_id = checkpoint.checkpoint_id
        self._total_checkpoints += 1

        self._emit_receipt(
            decision_type=CognitionDecisionType.CHECKPOINT,
            action="checkpoint_created",
            component="cognition_engine",
            input_hash=_content_hash(self._cognitive_state.to_dict()),
            output_hash=_content_hash(checkpoint.to_dict()),
        )

        self._persist_checkpoint(checkpoint)
        self._sync_cognitive_state()
        return checkpoint

    def get_latest_checkpoint(self) -> CognitiveCheckpoint | None:
        return self._checkpoints[-1] if self._checkpoints else None

    def get_all_checkpoints(self) -> list[CognitiveCheckpoint]:
        return list(self._checkpoints)

    def _persist_checkpoint(self, checkpoint: CognitiveCheckpoint) -> None:
        path = self._state_dir / f"checkpoint_{checkpoint.checkpoint_id}.json"
        with path.open("w", encoding="utf-8") as f:
            json.dump(checkpoint.to_dict(), f, indent=2, default=str)

    # ------------------------------------------------------------------
    # Lineage receipts
    # ------------------------------------------------------------------

    def _emit_receipt(
        self,
        decision_type: CognitionDecisionType,
        action: str,
        component: str,
        input_hash: str = "",
        output_hash: str = "",
        approved: bool = True,
    ) -> CognitiveLineageReceipt:
        receipt = CognitiveLineageReceipt(
            session_id=self._session_id,
            cognition_phase=self._cognitive_state.phase,
            decision_type=decision_type,
            action=action,
            component=component,
            input_hash=input_hash,
            output_hash=output_hash,
            approved=approved,
        )
        self._receipts.append(receipt)
        self._total_receipts += 1

        lineage_path = self._state_dir / "cognition_lineage.jsonl"
        with lineage_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(receipt.to_dict(), default=str) + "\n")

        return receipt

    def get_recent_receipts(self, limit: int = 10) -> list[dict[str, Any]]:
        return [r.to_dict() for r in self._receipts[-limit:]]

    # ------------------------------------------------------------------
    # State synchronization
    # ------------------------------------------------------------------

    def _sync_cognitive_state(self) -> None:
        """Keep the top-level cognitive state in sync with subsystems."""
        self._cognitive_state.open_loop_count = len(self.get_active_loops())
        self._cognitive_state.attention_window_size = len(
            self._working_window.items
        )
        self._cognitive_state.last_activity_iso = _now_iso()

    # ------------------------------------------------------------------
    # Stats / introspection
    # ------------------------------------------------------------------

    def get_stats(self) -> dict[str, Any]:
        return {
            "session_id": self._session_id,
            "operator_mode": self._cognitive_state.operator_mode.value,
            "phase": self._cognitive_state.phase.value,
            "active_focuses": len([
                f for f in self._active_focuses.values() if f.active
            ]),
            "total_focuses": len(self._active_focuses),
            "active_intents": len(self.get_active_intents()),
            "total_intents": len(self._intents),
            "active_loops": len(self.get_active_loops()),
            "total_loops": len(self._open_loops),
            "working_window_items": len(self._working_window.items),
            "working_window_max": self._working_window.max_items,
            "checkpoints": len(self._checkpoints),
            "continuity_chain_length": (
                self._cognitive_state.continuity_chain_length
            ),
            "total_focus_shifts": self._total_focus_shifts,
            "total_loop_operations": self._total_loop_operations,
            "total_checkpoints": self._total_checkpoints,
            "total_receipts": self._total_receipts,
        }

    def get_cognitive_snapshot(self) -> dict[str, Any]:
        """Full snapshot of current cognitive state for serialization."""
        return {
            "cognitive_state": self._cognitive_state.to_dict(),
            "working_window": self._working_window.to_dict(),
            "attention_map": self._attention_map.to_dict(),
            "temporal_context": self._temporal_context.to_dict(),
            "continuity_focus": self._continuity_focus.to_dict(),
            "active_focus": (
                self.get_active_focus().to_dict()
                if self.get_active_focus()
                else None
            ),
            "active_intents": [i.to_dict() for i in self.get_active_intents()],
            "active_loops": [l.to_dict() for l in self.get_active_loops()],
            "stats": self.get_stats(),
        }
