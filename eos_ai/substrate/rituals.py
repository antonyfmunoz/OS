"""
Ritual workflow scaffold — open_day / close_day.

Rituals are named, stateful workflows that run at specific points in the
founder's day. They coordinate multiple agents/components (briefings, handoffs,
summaries) without each cron script reinventing structure.

This module defines the *shape* of a ritual and a minimal registry. It does
NOT wire rituals into every interface yet — that is intentionally deferred
until the node/capability layer is consumed by routing. For now, orchestrator
scripts and scheduled jobs can register and advance rituals through this API.

Usage:
    from eos_ai.substrate import RitualRegistry, RitualKind, RitualState

    reg = RitualRegistry.default()
    ritual = reg.start(RitualKind.OPEN_DAY, inputs={"date": "2026-04-06"})
    reg.advance(ritual.ritual_id, RitualState.BRIEFING)
    reg.complete(ritual.ritual_id, outputs={"briefing_doc_id": "..."})
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional


class RitualKind(str, Enum):
    OPEN_DAY = "open_day"
    CLOSE_DAY = "close_day"


class RitualState(str, Enum):
    """
    Canonical lifecycle for any ritual. Specific kinds may only use a subset.

        PENDING   → INITIATED → GATHERING → BRIEFING → HANDOFF → COMPLETED
                                        ↘ FAILED

    Kept linear on purpose — rituals are checkpoints, not general workflows.
    Complex branching belongs in workflow_engine.py, not here.
    """

    PENDING = "pending"
    INITIATED = "initiated"
    GATHERING = "gathering"        # collecting inputs (memory, pulse, etc.)
    BRIEFING = "briefing"          # producing the founder-facing summary
    HANDOFF = "handoff"            # passing control to the next phase
    COMPLETED = "completed"
    FAILED = "failed"


_TERMINAL = {RitualState.COMPLETED, RitualState.FAILED}


def _new_id() -> str:
    return f"ritual_{uuid.uuid4().hex[:12]}"


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class Ritual:
    """
    A single in-flight or historical ritual instance.

    `inputs`  — data provided at start (date, timezone, scope).
    `outputs` — data produced by completion (briefing id, handoff target).
    `trace`   — append-only list of (state, timestamp) transitions for audit.

    Integration hook (FUTURE): persist Ritual to Neon `rituals` table so the
    morning brief cron and close-of-day cron can share state across processes.
    """

    kind: RitualKind
    ritual_id: str = field(default_factory=_new_id)
    state: RitualState = RitualState.PENDING
    inputs: dict[str, Any] = field(default_factory=dict)
    outputs: dict[str, Any] = field(default_factory=dict)
    trace: list[dict[str, str]] = field(default_factory=list)
    started_at: str = field(default_factory=_utcnow)
    ended_at: Optional[str] = None

    def is_terminal(self) -> bool:
        return self.state in _TERMINAL


class RitualRegistry:
    """
    Persistent ritual tracker.

    Rituals are flushed through eos_ai.substrate.storage on every lifecycle
    transition so cron scripts running in separate processes can share state
    (morning cron starts an open_day ritual; a later EA interaction can find
    and reference it). Storage falls back to JSON file if Neon is unavailable.
    """

    _STORAGE_KEY = "rituals"
    _default: Optional["RitualRegistry"] = None

    def __init__(self, *, persist: bool = True) -> None:
        self._rituals: dict[str, Ritual] = {}
        self._persist = persist
        if persist:
            self._load()

    # ─── Persistence ──────────────────────────────────────────────────────
    def _load(self) -> None:
        try:
            from eos_ai.substrate.storage import get_storage
            raw = get_storage().get(self._STORAGE_KEY, default={}) or {}
            for rid, data in raw.items():
                self._rituals[rid] = Ritual(
                    kind=RitualKind(data["kind"]),
                    ritual_id=data["ritual_id"],
                    state=RitualState(data.get("state", RitualState.PENDING.value)),
                    inputs=data.get("inputs", {}) or {},
                    outputs=data.get("outputs", {}) or {},
                    trace=list(data.get("trace", [])),
                    started_at=data.get("started_at", _utcnow()),
                    ended_at=data.get("ended_at"),
                )
        except Exception as e:
            import sys
            print(f"[substrate.rituals] load failed ({e}); starting empty", file=sys.stderr)

    def _flush(self) -> None:
        if not self._persist:
            return
        try:
            from eos_ai.substrate.storage import get_storage
            payload = {
                rid: {
                    "ritual_id": r.ritual_id,
                    "kind": r.kind.value,
                    "state": r.state.value,
                    "inputs": r.inputs,
                    "outputs": r.outputs,
                    "trace": r.trace,
                    "started_at": r.started_at,
                    "ended_at": r.ended_at,
                }
                for rid, r in self._rituals.items()
            }
            get_storage().put(self._STORAGE_KEY, payload)
        except Exception as e:
            import sys
            print(f"[substrate.rituals] flush failed ({e}); in-memory only", file=sys.stderr)

    @classmethod
    def default(cls) -> "RitualRegistry":
        if cls._default is None:
            cls._default = cls()
        return cls._default

    @classmethod
    def reset_default_for_tests(cls) -> None:
        cls._default = None

    # ─── Lifecycle ────────────────────────────────────────────────────────
    def start(self, kind: RitualKind, inputs: Optional[dict] = None) -> Ritual:
        ritual = Ritual(kind=kind, inputs=inputs or {})
        ritual.state = RitualState.INITIATED
        ritual.trace.append({"state": ritual.state.value, "at": _utcnow()})
        self._rituals[ritual.ritual_id] = ritual
        self._flush()
        return ritual

    def advance(self, ritual_id: str, new_state: RitualState) -> Ritual:
        ritual = self._require(ritual_id)
        if ritual.is_terminal():
            raise ValueError(f"ritual {ritual_id} already terminal ({ritual.state})")
        ritual.state = new_state
        ritual.trace.append({"state": new_state.value, "at": _utcnow()})
        if new_state in _TERMINAL:
            ritual.ended_at = _utcnow()
        self._flush()
        return ritual

    def complete(self, ritual_id: str, outputs: Optional[dict] = None) -> Ritual:
        ritual = self._require(ritual_id)
        ritual.outputs.update(outputs or {})
        return self.advance(ritual_id, RitualState.COMPLETED)

    def fail(self, ritual_id: str, reason: str) -> Ritual:
        ritual = self._require(ritual_id)
        ritual.outputs["error"] = reason
        return self.advance(ritual_id, RitualState.FAILED)

    # ─── Queries ──────────────────────────────────────────────────────────
    def get(self, ritual_id: str) -> Optional[Ritual]:
        return self._rituals.get(ritual_id)

    def active(self, kind: Optional[RitualKind] = None) -> list[Ritual]:
        return [
            r for r in self._rituals.values()
            if not r.is_terminal() and (kind is None or r.kind == kind)
        ]

    def history(self) -> list[Ritual]:
        return list(self._rituals.values())

    # ─── Internal ─────────────────────────────────────────────────────────
    def _require(self, ritual_id: str) -> Ritual:
        ritual = self._rituals.get(ritual_id)
        if ritual is None:
            raise KeyError(f"unknown ritual_id {ritual_id!r}")
        return ritual
