"""
Station Daemon contract.

Defines the substrate-side interface between EOS (running on the VPS) and a
future local Station Daemon running on the founder's workstation. This module
contains NO daemon implementation — only the protocol/schema both sides will
eventually speak.

Design rules:
  - No raw remote shell. Only SafeAction intents (see eos_ai.substrate.actions).
  - Local node is the trust boundary. The VPS proposes; the station decides.
  - Station advertises capabilities on connect; EOS may not assume any.
  - All messages are JSON-serializable dicts so transport is pluggable
    (WebSocket, HTTP long-poll, SSH tunnel, etc. — chosen later).

Usage (contract consumer side — substrate, not daemon):
    from eos_ai.substrate import StationContract, StationHeartbeat

    contract = StationContract(node_id="antony-workstation")
    heartbeat = StationHeartbeat(
        node_id="antony-workstation",
        capabilities=["microphone_input", "audio_output"],
        control_mode=ControlMode.ASSIST,
    )
    contract.record_heartbeat(heartbeat)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

from eos_ai.substrate.actions import SafeAction, ActionResult, ActionKind, ActionStatus


# ─── Policy ───────────────────────────────────────────────────────────────────
#
# The ONLY action kinds allowed end-to-end in this MVP pass. Everything else
# stays defined in actions.py (so the vocabulary is stable) but is rejected
# by StationContract.propose() until each kind is explicitly cleared by the
# human operator. This is the substrate-level trust boundary — widening the
# allow-list is a deliberate, reviewable change, not an accidental one.

MVP_ALLOWED_ACTIONS: frozenset[ActionKind] = frozenset({
    ActionKind.PLAY_SOUND,
    ActionKind.SPEAK_TEXT,
    ActionKind.OPEN_URL,
    ActionKind.LAUNCH_APP,
    ActionKind.OPEN_SCENE,
    ActionKind.FOCUS_APP,
})


class ControlMode(str, Enum):
    """
    How much authority EOS has over the local station at a given moment.

    OBSERVE  — station reports state only; cannot be told to act.
    ASSIST   — station accepts suggestions; each action requires local confirm.
    DRIVE    — station executes EOS-issued SafeActions automatically, within
               the action vocabulary. Still bounded — raw shell is never allowed.
    """

    OBSERVE = "observe"
    ASSIST = "assist"
    DRIVE = "drive"


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


# ─── Messages the station sends TO EOS ────────────────────────────────────────

@dataclass
class StationHeartbeat:
    """
    Periodic liveness + capability advertisement from a station to EOS.

    Station sends this on connect and on a regular interval (to be chosen
    during daemon implementation). EOS updates NodeRegistry from it.
    """

    node_id: str
    capabilities: list[str] = field(default_factory=list)
    control_mode: ControlMode = ControlMode.OBSERVE
    active_scene: Optional[str] = None
    active_app: Optional[str] = None
    metrics: dict[str, Any] = field(default_factory=dict)  # cpu/mem/battery/etc.
    sent_at: str = field(default_factory=_utcnow)


@dataclass
class StationEvent:
    """
    Out-of-band event the station wants EOS to know about.

    Examples: user started a pomodoro, user plugged in headphones, user opened
    Notion, listener transcribed a phrase. These are *facts*, not requests.
    EOS may react via cognitive_loop but the station does not assume it will.
    """

    node_id: str
    event_type: str  # slug, e.g. "pomodoro_started", "utterance_transcribed"
    payload: dict[str, Any] = field(default_factory=dict)
    occurred_at: str = field(default_factory=_utcnow)


# ─── The contract itself ──────────────────────────────────────────────────────

class StationContract:
    """
    EOS-side handle for one local station.

    Holds the most recent heartbeat, tracks in-flight actions, and accepts
    inbound events. This is a pure in-memory contract object — transport
    (WebSocket, etc.) is out of scope for the bridging branch.

    Integration hooks (FUTURE):
      - on_heartbeat  → update NodeRegistry + emit event on EventBus
      - on_event      → feed into cognitive_loop PERCEIVE stream
      - dispatch      → actually transmit over chosen transport
    """

    def __init__(self, node_id: str) -> None:
        self.node_id = node_id
        self.last_heartbeat: Optional[StationHeartbeat] = None
        self.control_mode: ControlMode = ControlMode.OBSERVE
        self._inflight: dict[str, SafeAction] = {}
        self._results: dict[str, ActionResult] = {}
        self._event_log: list[StationEvent] = []

    # ─── Inbound from station ────────────────────────────────────────────
    def record_heartbeat(self, hb: StationHeartbeat) -> None:
        if hb.node_id != self.node_id:
            raise ValueError(
                f"heartbeat node_id {hb.node_id!r} does not match "
                f"contract node_id {self.node_id!r}"
            )
        self.last_heartbeat = hb
        self.control_mode = hb.control_mode
        # FUTURE: NodeRegistry.default().upsert(Node(... from hb ...))
        # FUTURE: EventBus().publish("station_heartbeat", hb.__dict__)

    def record_event(self, evt: StationEvent) -> None:
        if evt.node_id != self.node_id:
            raise ValueError("event node_id mismatch")
        self._event_log.append(evt)
        # Bridge to EOS EventBus — best-effort, additive, never raises on
        # bus unavailability. Events land under the "station.<event_type>"
        # namespace so existing subscribers are unaffected until they
        # explicitly subscribe.
        try:
            from eos_ai.event_bus import EventBus
            EventBus().publish_async(
                f"station.{evt.event_type}",
                {
                    "node_id": evt.node_id,
                    "payload": evt.payload,
                    "occurred_at": evt.occurred_at,
                },
            )
        except Exception as _e:
            import sys
            print(f"[substrate.station] event bridge skipped: {_e}", file=sys.stderr)

    def record_result(self, result: ActionResult) -> None:
        self._results[result.action_id] = result
        action = self._inflight.pop(result.action_id, None)
        if action is not None:
            action.status = result.status

    # ─── Outbound to station ─────────────────────────────────────────────
    def propose(self, action: SafeAction) -> SafeAction:
        """
        Register an action for transmission to the station.

        Enforces two gates in order:
          1. Control mode: OBSERVE rejects everything.
          2. MVP allow-list: only MVP_ALLOWED_ACTIONS pass in this phase.

        Accepted actions are written to the in-process inflight table and,
        if a StationBus is available, handed to it for local transport
        (see eos_ai.substrate.station_bus). Never raises on transport errors —
        actions that cannot be delivered stay inflight for retry/inspection.
        """
        if self.control_mode == ControlMode.OBSERVE:
            action.status = ActionStatus.REJECTED
            print(
                f"[substrate.station] reject {action.kind.value}: "
                f"{self.node_id} in OBSERVE mode"
            )
            return action

        if action.kind not in MVP_ALLOWED_ACTIONS:
            action.status = ActionStatus.REJECTED
            print(
                f"[substrate.station] reject {action.kind.value}: "
                f"not in MVP allow-list"
            )
            return action

        action.target_node_id = self.node_id
        action.status = ActionStatus.DISPATCHED
        self._inflight[action.action_id] = action

        try:
            from eos_ai.substrate.station_bus import get_station_bus
            get_station_bus().dispatch(self.node_id, action)
        except Exception as e:
            # Never hard-fail propose() on transport problems. The action
            # stays in _inflight; a later poll can retry.
            print(f"[substrate.station] dispatch hook failed: {e}")

        return action

    # ─── Introspection ───────────────────────────────────────────────────
    def inflight(self) -> list[SafeAction]:
        return list(self._inflight.values())

    def event_log(self) -> list[StationEvent]:
        return list(self._event_log)

    def result_for(self, action_id: str) -> Optional[ActionResult]:
        return self._results.get(action_id)
