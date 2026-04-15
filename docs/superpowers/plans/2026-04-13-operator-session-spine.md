# Unified Operator Session State + Open/Close Rituals v1 — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a single authoritative operator session spine with open_day/close_day workflows integrated into the existing ritual registry and exposed via Discord.

**Architecture:** New `operator_session.py` substrate registry (dataclass + singleton store + dual-layer persistence) owns daily operator state. New `day_workflows.py` coordinates session spine writes with existing `RitualRegistry` lifecycle. Discord integration is an early natural-language intercept + two bang commands in `discord_bot.py`, both calling the same shared workflow/format/dispatch helpers.

**Tech Stack:** Python 3.12, existing substrate storage (Neon + JSON fallback), py-cord 2.6.1, existing `RitualRegistry` API.

**Implementation cautions (carry forward from spec review):**
1. The Discord natural-language intercept must NEVER double-fire with prefixed commands. If text starts with `!`, skip `_detect_day_command()` entirely.
2. The mirrored `#morning-brief` post must be best-effort only and CANNOT fail the primary response path.

**Spec:** `docs/superpowers/specs/2026-04-13-operator-session-spine-design.md`

---

## File Map

| File | Action | Responsibility |
|------|--------|----------------|
| `eos_ai/substrate/operator_session.py` | Create | OperatorDayMode enum, OperatorSession dataclass, OperatorSessionStore singleton |
| `eos_ai/substrate/day_workflows.py` | Create | `open_day()` and `close_day()` public functions coordinating session spine + ritual registry |
| `services/discord_bot.py` | Modify | Natural-language intercept, `!openday`/`!closeday` commands, shared dispatch helpers |
| `tests/substrate/test_operator_session.py` | Create | Smoke tests for session spine persistence |
| `tests/substrate/test_day_workflows.py` | Create | Smoke tests for open/close day workflows + continuity |
| `tests/substrate/test_day_discord_detect.py` | Create | Unit tests for `_detect_day_command` regex |

---

## Task 1: Operator Session Spine — Data Model + Store

**Files:**
- Create: `eos_ai/substrate/operator_session.py`
- Create: `tests/substrate/test_operator_session.py`

- [ ] **Step 1: Write the smoke test file**

Create `tests/substrate/test_operator_session.py`:

```python
"""Smoke tests for eos_ai.substrate.operator_session.

Run directly:
    python3 tests/substrate/test_operator_session.py
"""

from __future__ import annotations

import sys

sys.path.insert(0, "/opt/OS")

_PASS = 0
_FAIL = 0


def _report(name: str, passed: bool, detail: str = "") -> None:
    global _PASS, _FAIL  # noqa: PLW0603
    if passed:
        _PASS += 1
    else:
        _FAIL += 1
    tag = "PASS" if passed else "FAIL"
    suffix = f" — {detail}" if detail else ""
    print(f"  [{tag}] {name}{suffix}")


def test_create_and_persist():
    """Create a session, persist it, reset singleton, reload, verify fields."""
    from eos_ai.substrate.operator_session import (
        OperatorDayMode,
        OperatorSession,
        OperatorSessionStore,
    )

    # Reset to clean state
    OperatorSessionStore.reset_default_for_tests()
    store = OperatorSessionStore.default()

    session = OperatorSession.new(
        day_mode=OperatorDayMode.REMOTE_ACTIVE,
        active_workspace="builder",
        node_preference="auto",
    )
    session.is_day_open = True
    session.unfinished_priorities = ["fix auth", "deploy webhook"]
    session.continuity_notes_for_next_open = "auth middleware half done"
    session.last_resume_context = "was in eos_ai/auth.py line 42"
    store.put(session)

    # Verify in-memory
    loaded = store.get()
    _report(
        "in-memory round-trip",
        loaded is not None
        and loaded.day_session_id == session.day_session_id
        and loaded.day_mode == OperatorDayMode.REMOTE_ACTIVE
        and loaded.is_day_open is True
        and loaded.active_workspace == "builder"
        and loaded.unfinished_priorities == ["fix auth", "deploy webhook"]
        and loaded.continuity_notes_for_next_open == "auth middleware half done"
        and loaded.last_resume_context == "was in eos_ai/auth.py line 42",
    )

    # Reset singleton — forces reload from storage
    OperatorSessionStore.reset_default_for_tests()
    store2 = OperatorSessionStore.default()
    reloaded = store2.get()
    _report(
        "restart-safe persistence",
        reloaded is not None
        and reloaded.day_session_id == session.day_session_id
        and reloaded.is_day_open is True
        and reloaded.unfinished_priorities == ["fix auth", "deploy webhook"]
        and reloaded.continuity_notes_for_next_open == "auth middleware half done"
        and reloaded.last_resume_context == "was in eos_ai/auth.py line 42",
    )

    # Clean up
    OperatorSessionStore.reset_default_for_tests()


def test_put_overwrites():
    """Putting a new session replaces the previous one."""
    from eos_ai.substrate.operator_session import (
        OperatorDayMode,
        OperatorSession,
        OperatorSessionStore,
    )

    OperatorSessionStore.reset_default_for_tests()
    store = OperatorSessionStore.default()

    s1 = OperatorSession.new(day_mode=OperatorDayMode.REMOTE_ACTIVE)
    store.put(s1)

    s2 = OperatorSession.new(day_mode=OperatorDayMode.LOCAL_ACTIVE)
    store.put(s2)

    loaded = store.get()
    _report(
        "put overwrites previous",
        loaded is not None and loaded.day_session_id == s2.day_session_id,
    )

    OperatorSessionStore.reset_default_for_tests()


def test_enum_values():
    """All OperatorDayMode values serialize to expected strings."""
    from eos_ai.substrate.operator_session import OperatorDayMode

    expected = {
        "inactive",
        "remote_active",
        "local_active",
        "deep_work",
        "overnight",
    }
    actual = {m.value for m in OperatorDayMode}
    _report("enum values", actual == expected, f"got {actual}")


if __name__ == "__main__":
    print("=== operator_session smoke tests ===")
    test_enum_values()
    test_create_and_persist()
    test_put_overwrites()
    print(f"\n  {_PASS} passed, {_FAIL} failed")
    sys.exit(1 if _FAIL > 0 else 0)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 tests/substrate/test_operator_session.py`
Expected: ImportError — `eos_ai.substrate.operator_session` does not exist yet.

- [ ] **Step 3: Implement operator_session.py**

Create `eos_ai/substrate/operator_session.py`:

```python
"""
Operator session spine — single authoritative source of truth for the
operator's daily lifecycle state.

Purpose
-------
The substrate has multiple parallel state systems (operator_state for
voice/wake FSM, rituals for workflow progression, session_orchestration
for tmux sessions). None owns "where is the operator in their day" as
a unified concern.

This module provides that answer:

  - one bounded dataclass (OperatorSession) per operator
  - one dual-layer store (in-mem + substrate.storage)
  - separate OperatorDayMode enum (does NOT replace OperatorMode from
    operator_state.py — that drives the voice/wake state machine)

OperatorDayMode tracks daily lifecycle posture:
  inactive / remote_active / local_active / deep_work / overnight

OperatorMode (in operator_state.py) tracks voice/wake FSM:
  IDLE / STARTING / ACTIVE / FOCUSED / CLOSING / UNAVAILABLE

These are separate concerns on separate stores.

Design rules (mirror the rest of substrate)
-------------------------------------------
- Additive only. Hot path never imported.
- Bounded. One session record (singleton operator).
- Best-effort. All public methods catch and log; never raise.
- Deterministic. Storage layout is a single JSON blob.
- Reversible. Removing this file leaves substrate intact.
"""

from __future__ import annotations

import sys
import threading
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional


# ─── Constants ────────────────────────────────────────────────────────────────

_STORAGE_KEY = "operator_session"


def _log(msg: str) -> None:
    print(f"[substrate.operator_session] {msg}", file=sys.stderr)


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_id() -> str:
    return f"ds_{uuid.uuid4().hex[:12]}"


# ─── Models ──────────────────────────────────────────────────────────────────


class OperatorDayMode(str, Enum):
    """Daily lifecycle posture — separate from OperatorMode (voice/wake FSM).

    INACTIVE      — no day open
    REMOTE_ACTIVE — operating from Discord/phone
    LOCAL_ACTIVE  — at the desk, local station
    DEEP_WORK     — focused block, minimize interrupts
    OVERNIGHT     — day closed, overnight tasks running
    """

    INACTIVE = "inactive"
    REMOTE_ACTIVE = "remote_active"
    LOCAL_ACTIVE = "local_active"
    DEEP_WORK = "deep_work"
    OVERNIGHT = "overnight"


@dataclass
class OperatorSession:
    """Single operator's daily session state.

    Fields
    ------
    day_session_id : unique per open/close cycle ("ds_<12hex>")
    day_mode : daily lifecycle posture (separate from voice/wake OperatorMode)
    is_day_open : whether the current session cycle is active
    active_workspace : "product" or "builder" — the workspace to resume into
        on open_day unless explicitly overridden
    node_preference : "auto", "local", or "vps"
    last_active_node : last node that executed work
    last_active_discord_channel_id : channel ID of last Discord interaction
    active_tmux_session : the currently resolved or most recently targeted
        execution session
    ritual_open_id : pointer to the OPEN_DAY ritual in RitualRegistry
    ritual_close_id : pointer to the CLOSE_DAY ritual in RitualRegistry
    created_at : when this session record was created (ISO UTC)
    opened_at : when open_day ran (ISO UTC)
    closed_at : when close_day ran (ISO UTC)
    updated_at : last mutation timestamp (ISO UTC)
    last_briefing_summary : human-readable recap (set by close_day as the
        durable close recap containing completed and unresolved context)
    unfinished_priorities : items that did not get done (written by close_day,
        inherited by next open_day)
    overnight_tasks : tasks that should continue running overnight
    continuity_notes_for_next_open : free-text notes for the next open_day
        briefing
    last_resume_context : concise carry-forward context distinct from the
        broader continuity notes
    """

    day_session_id: str
    day_mode: OperatorDayMode = OperatorDayMode.INACTIVE
    is_day_open: bool = False
    active_workspace: str = "builder"
    node_preference: str = "auto"
    last_active_node: Optional[str] = None
    last_active_discord_channel_id: Optional[str] = None
    active_tmux_session: Optional[str] = None
    ritual_open_id: Optional[str] = None
    ritual_close_id: Optional[str] = None
    created_at: str = field(default_factory=_utcnow)
    opened_at: Optional[str] = None
    closed_at: Optional[str] = None
    updated_at: str = field(default_factory=_utcnow)
    last_briefing_summary: Optional[str] = None
    unfinished_priorities: list[str] = field(default_factory=list)
    overnight_tasks: list[str] = field(default_factory=list)
    continuity_notes_for_next_open: Optional[str] = None
    last_resume_context: Optional[str] = None

    @classmethod
    def new(
        cls,
        *,
        day_mode: OperatorDayMode = OperatorDayMode.INACTIVE,
        active_workspace: str = "builder",
        node_preference: str = "auto",
    ) -> "OperatorSession":
        """Factory for a fresh session with a new ID and timestamps."""
        now = _utcnow()
        return cls(
            day_session_id=_new_id(),
            day_mode=day_mode,
            active_workspace=active_workspace,
            node_preference=node_preference,
            created_at=now,
            updated_at=now,
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a JSON-safe dict."""
        d = asdict(self)
        d["day_mode"] = self.day_mode.value
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "OperatorSession":
        """Deserialize from a dict (storage round-trip)."""
        data = dict(data)  # shallow copy
        if "day_mode" in data:
            data["day_mode"] = OperatorDayMode(data["day_mode"])
        # Ensure list fields are lists
        for list_field in ("unfinished_priorities", "overnight_tasks"):
            if list_field not in data or data[list_field] is None:
                data[list_field] = []
        return cls(**data)


# ─── Store ───────────────────────────────────────────────────────────────────


class OperatorSessionStore:
    """Singleton store for the current operator session.

    Thread-safe, dual-layer (in-mem + substrate.storage). Holds ONE record —
    the current/last session. Not a collection.
    """

    _default: Optional["OperatorSessionStore"] = None

    def __init__(self, *, persist: bool = True) -> None:
        self._session: Optional[OperatorSession] = None
        self._persist = persist
        self._lock = threading.RLock()
        if persist:
            self._load()

    def _load(self) -> None:
        try:
            from eos_ai.substrate.storage import get_storage

            raw = get_storage().get(_STORAGE_KEY, default=None)
            if raw and isinstance(raw, dict):
                self._session = OperatorSession.from_dict(raw)
        except Exception as e:
            _log(f"load failed ({e}); starting empty")

    def _flush(self) -> None:
        if not self._persist or self._session is None:
            return
        try:
            from eos_ai.substrate.storage import get_storage

            get_storage().put(_STORAGE_KEY, self._session.to_dict())
        except Exception as e:
            _log(f"flush failed ({e}); in-memory only")

    @classmethod
    def default(cls) -> "OperatorSessionStore":
        if cls._default is None:
            cls._default = cls()
        return cls._default

    @classmethod
    def reset_default_for_tests(cls) -> None:
        """Test hook — drop the singleton so next default() re-loads."""
        cls._default = None

    def get(self) -> Optional[OperatorSession]:
        """Return the current session, or None if no session exists."""
        with self._lock:
            return self._session

    def put(self, session: OperatorSession) -> None:
        """Persist a session (replaces any existing)."""
        with self._lock:
            session.updated_at = _utcnow()
            self._session = session
            self._flush()
```

- [ ] **Step 4: Compile check**

Run: `python3 -m py_compile eos_ai/substrate/operator_session.py`
Expected: no output (success).

- [ ] **Step 5: Run tests to verify they pass**

Run: `python3 tests/substrate/test_operator_session.py`
Expected: 3 passed, 0 failed.

- [ ] **Step 6: Format**

Run: `ruff format eos_ai/substrate/operator_session.py tests/substrate/test_operator_session.py`

- [ ] **Step 7: Commit**

```bash
git add eos_ai/substrate/operator_session.py tests/substrate/test_operator_session.py
git commit -m "feat: operator session spine — data model + persistent store

Adds OperatorDayMode enum (inactive/remote_active/local_active/deep_work/
overnight) separate from OperatorMode (voice/wake FSM). OperatorSession
dataclass holds daily lifecycle state, continuity fields, and ritual
pointers. OperatorSessionStore is a singleton with dual-layer persistence
(in-mem + substrate.storage).

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Task 2: Day Workflows — open_day + close_day

**Files:**
- Create: `eos_ai/substrate/day_workflows.py`
- Create: `tests/substrate/test_day_workflows.py`

- [ ] **Step 1: Write the smoke test file**

Create `tests/substrate/test_day_workflows.py`:

```python
"""Smoke tests for eos_ai.substrate.day_workflows.

Validates:
  1. open_day creates session + ritual, returns briefing
  2. close_day updates session + ritual, returns summary
  3. Continuity carries forward across open/close cycles
  4. already_open / not_open guards work
  5. Restart-safe persistence

Run directly:
    python3 tests/substrate/test_day_workflows.py
"""

from __future__ import annotations

import sys

sys.path.insert(0, "/opt/OS")

_PASS = 0
_FAIL = 0


def _report(name: str, passed: bool, detail: str = "") -> None:
    global _PASS, _FAIL  # noqa: PLW0603
    if passed:
        _PASS += 1
    else:
        _FAIL += 1
    tag = "PASS" if passed else "FAIL"
    suffix = f" — {detail}" if detail else ""
    print(f"  [{tag}] {name}{suffix}")


def _reset_all():
    """Reset all singletons for test isolation."""
    from eos_ai.substrate.operator_session import OperatorSessionStore
    from eos_ai.substrate.rituals import RitualRegistry

    OperatorSessionStore.reset_default_for_tests()
    RitualRegistry.reset_default_for_tests()


def test_open_day_fresh():
    """First open_day with no prior session returns ok + empty briefing."""
    _reset_all()
    from eos_ai.substrate.day_workflows import open_day

    result = open_day()

    _report("open_day status", result["status"] == "ok")
    _report(
        "open_day session id",
        result["day_session_id"].startswith("ds_"),
        result.get("day_session_id", "missing"),
    )
    _report(
        "open_day ritual id",
        result.get("ritual_id", "").startswith("ritual_")
        or result.get("ritual_warning") is not None,
    )
    _report("open_day day_mode", result["day_mode"] == "remote_active")
    _report("open_day workspace", result["active_workspace"] == "builder")
    briefing = result.get("briefing", {})
    _report(
        "open_day empty briefing",
        briefing.get("where_we_left_off") is None
        and briefing.get("unfinished_priorities") == []
        and briefing.get("overnight_tasks") == [],
    )


def test_already_open():
    """Calling open_day when day is already open returns already_open."""
    _reset_all()
    from eos_ai.substrate.day_workflows import open_day

    open_day()
    result2 = open_day()

    _report("already_open guard", result2["status"] == "already_open")


def test_close_day():
    """close_day updates session and returns summary."""
    _reset_all()
    from eos_ai.substrate.day_workflows import close_day, open_day

    open_day()
    result = close_day(
        completed_today=["shipped webhook"],
        unresolved=["auth bug"],
        overnight_tasks=["run backfill"],
        continuity_notes="pick up auth middleware",
        resume_context="eos_ai/auth.py line 42",
    )

    _report("close_day status", result["status"] == "ok")
    summary = result.get("summary", {})
    _report(
        "close_day completed",
        summary.get("completed_today") == ["shipped webhook"],
    )
    _report(
        "close_day unresolved",
        summary.get("unresolved") == ["auth bug"],
    )
    _report(
        "close_day day_mode",
        summary.get("day_mode") == "overnight",
    )
    _report(
        "close_day workspace in summary",
        "active_workspace" in summary,
    )
    _report(
        "close_day node_preference in summary",
        "node_preference" in summary,
    )


def test_not_open():
    """close_day with no open session returns not_open."""
    _reset_all()
    from eos_ai.substrate.day_workflows import close_day

    result = close_day()
    _report("not_open guard", result["status"] == "not_open")


def test_continuity_carries_forward():
    """After close + open, the new open_day briefing contains prior continuity."""
    _reset_all()
    from eos_ai.substrate.day_workflows import close_day, open_day

    open_day()
    close_day(
        unresolved=["auth bug", "fix tests"],
        overnight_tasks=["run backfill"],
        continuity_notes="auth middleware half done",
        resume_context="was refactoring auth.py",
    )

    # New open_day should inherit continuity from the closed session
    result = open_day()
    briefing = result.get("briefing", {})
    _report(
        "continuity: unfinished_priorities",
        briefing.get("unfinished_priorities") == ["auth bug", "fix tests"],
    )
    _report(
        "continuity: overnight_tasks",
        briefing.get("overnight_tasks") == ["run backfill"],
    )
    _report(
        "continuity: where_we_left_off",
        briefing.get("where_we_left_off") == "auth middleware half done",
    )
    _report(
        "continuity: resume_context",
        briefing.get("resume_context") == "was refactoring auth.py",
    )
    _report(
        "continuity: recommended_first_action",
        briefing.get("recommended_first_action") == "auth bug",
    )


def test_restart_safe():
    """Session spine survives singleton reset (simulates process restart)."""
    _reset_all()
    from eos_ai.substrate.day_workflows import open_day
    from eos_ai.substrate.operator_session import OperatorSessionStore

    result = open_day()
    sid = result["day_session_id"]

    # Reset singleton — next access reloads from storage
    OperatorSessionStore.reset_default_for_tests()
    session = OperatorSessionStore.default().get()
    _report(
        "restart-safe",
        session is not None and session.day_session_id == sid and session.is_day_open,
    )


def test_ritual_created():
    """open_day and close_day each create rituals in RitualRegistry."""
    _reset_all()
    from eos_ai.substrate.day_workflows import close_day, open_day
    from eos_ai.substrate.rituals import RitualRegistry

    open_result = open_day()
    close_result = close_day()

    rituals = RitualRegistry.default().history()
    kinds = [r.kind.value for r in rituals]
    _report("open ritual created", "open_day" in kinds)
    _report("close ritual created", "close_day" in kinds)

    # Check that rituals are COMPLETED
    states = [r.state.value for r in rituals]
    _report("rituals completed", all(s == "completed" for s in states))


if __name__ == "__main__":
    print("=== day_workflows smoke tests ===")
    test_open_day_fresh()
    test_already_open()
    test_close_day()
    test_not_open()
    test_continuity_carries_forward()
    test_restart_safe()
    test_ritual_created()
    print(f"\n  {_PASS} passed, {_FAIL} failed")
    _reset_all()
    sys.exit(1 if _FAIL > 0 else 0)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 tests/substrate/test_day_workflows.py`
Expected: ImportError — `eos_ai.substrate.day_workflows` does not exist yet.

- [ ] **Step 3: Implement day_workflows.py**

Create `eos_ai/substrate/day_workflows.py`:

```python
"""
Day workflows — open_day / close_day coordination layer.

Coordinates the operator session spine (operator_session.py) with the
existing ritual registry (rituals.py). Each workflow:

  1. Manages ritual lifecycle via RitualRegistry (existing API)
  2. Creates/updates the OperatorSession spine (new)
  3. Returns a Discord-safe payload dict (caller formats + sends)

This module does NOT:
  - Make LLM calls
  - Touch tmux sessions
  - Send Discord messages
  - Invoke voice/TTS
  - Wire operator_state.py or operator_transitions.py

Those are future layers on top of this foundation.
"""

from __future__ import annotations

import sys
from typing import Any, Optional

from eos_ai.substrate.operator_session import (
    OperatorDayMode,
    OperatorSession,
    OperatorSessionStore,
)
from eos_ai.substrate.rituals import RitualKind, RitualRegistry, RitualState


def _log(msg: str) -> None:
    print(f"[substrate.day_workflows] {msg}", file=sys.stderr)


def _utcnow() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).isoformat()


# ─── open_day ────────────────────────────────────────────────────────────────


def open_day(
    *,
    workspace: Optional[str] = None,
    node_preference: Optional[str] = None,
    discord_channel_id: Optional[str] = None,
) -> dict[str, Any]:
    """Open the operator's day. Returns a Discord-safe briefing payload.

    Creates a fresh session record inheriting continuity from the prior
    session. Starts an OPEN_DAY ritual via the existing RitualRegistry.

    If the day is already open, returns {"status": "already_open", ...}
    without creating a new ritual or mutating the session spine.
    """
    store = OperatorSessionStore.default()
    prior = store.get()

    # ── Guard: already open ──────────────────────────────────────────────
    if prior is not None and prior.is_day_open:
        return {
            "status": "already_open",
            "day_session_id": prior.day_session_id,
            "day_mode": prior.day_mode.value,
            "active_workspace": prior.active_workspace,
            "opened_at": prior.opened_at,
        }

    # ── Start ritual (best-effort) ──────────────────────────────────────
    ritual_id: Optional[str] = None
    ritual_warning: Optional[str] = None
    try:
        reg = RitualRegistry.default()
        ritual = reg.start(RitualKind.OPEN_DAY, inputs={"date": _utcnow()[:10]})
        ritual_id = ritual.ritual_id
        reg.advance(ritual_id, RitualState.GATHERING)
        reg.advance(ritual_id, RitualState.BRIEFING)
        reg.complete(ritual_id, outputs={"source": "day_workflows.open_day"})
    except Exception as e:
        ritual_warning = str(e)
        _log(f"ritual failed during open_day: {e}")

    # ── Compose briefing from prior continuity ──────────────────────────
    if prior is not None:
        where_we_left_off = prior.continuity_notes_for_next_open
        unfinished = list(prior.unfinished_priorities)
        overnight = list(prior.overnight_tasks)
        resume_ctx = prior.last_resume_context
    else:
        where_we_left_off = None
        unfinished = []
        overnight = []
        resume_ctx = None

    recommended = unfinished[0] if unfinished else None

    briefing = {
        "where_we_left_off": where_we_left_off,
        "unfinished_priorities": unfinished,
        "overnight_tasks": overnight,
        "recommended_first_action": recommended,
        "resume_context": resume_ctx,
    }

    # ── Determine day_mode (v1 heuristic — not a permanent equivalence
    #    between node_preference and operator posture) ────────────────────
    resolved_node_pref = node_preference or (prior.node_preference if prior else "auto")
    if resolved_node_pref == "local":
        day_mode = OperatorDayMode.LOCAL_ACTIVE
    else:
        day_mode = OperatorDayMode.REMOTE_ACTIVE

    resolved_workspace = workspace or (prior.active_workspace if prior else "builder")

    # ── Create new session record ───────────────────────────────────────
    now = _utcnow()
    session = OperatorSession(
        day_session_id=OperatorSession.new().day_session_id,
        day_mode=day_mode,
        is_day_open=True,
        active_workspace=resolved_workspace,
        node_preference=resolved_node_pref,
        last_active_node=prior.last_active_node if prior else None,
        last_active_discord_channel_id=discord_channel_id
        or (prior.last_active_discord_channel_id if prior else None),
        active_tmux_session=prior.active_tmux_session if prior else None,
        ritual_open_id=ritual_id,
        ritual_close_id=None,
        created_at=now,
        opened_at=now,
        closed_at=None,
        updated_at=now,
        last_briefing_summary=prior.last_briefing_summary if prior else None,
        unfinished_priorities=unfinished,
        overnight_tasks=overnight,
        continuity_notes_for_next_open=where_we_left_off,
        last_resume_context=resume_ctx,
    )
    store.put(session)

    # ── Build response ──────────────────────────────────────────────────
    result: dict[str, Any] = {
        "status": "ok",
        "day_session_id": session.day_session_id,
        "ritual_id": ritual_id,
        "briefing": briefing,
        "day_mode": day_mode.value,
        "active_workspace": resolved_workspace,
        "opened_at": now,
    }
    if ritual_warning:
        result["ritual_warning"] = ritual_warning
    return result


# ─── close_day ───────────────────────────────────────────────────────────────


def close_day(
    *,
    completed_today: Optional[list[str]] = None,
    unresolved: Optional[list[str]] = None,
    overnight_tasks: Optional[list[str]] = None,
    continuity_notes: Optional[str] = None,
    resume_context: Optional[str] = None,
    discord_channel_id: Optional[str] = None,
) -> dict[str, Any]:
    """Close the operator's day. Returns a Discord-safe close summary payload.

    Updates the current session record with continuity fields and starts a
    CLOSE_DAY ritual via the existing RitualRegistry.

    If the day is not open (or no session exists), returns
    {"status": "not_open"}.
    """
    store = OperatorSessionStore.default()
    session = store.get()

    # ── Guard: not open ──────────────────────────────────────────────────
    if session is None or not session.is_day_open:
        return {"status": "not_open"}

    # ── Start ritual (best-effort) ──────────────────────────────────────
    ritual_id: Optional[str] = None
    ritual_warning: Optional[str] = None
    try:
        reg = RitualRegistry.default()
        ritual = reg.start(RitualKind.CLOSE_DAY, inputs={"date": _utcnow()[:10]})
        ritual_id = ritual.ritual_id
        reg.advance(ritual_id, RitualState.GATHERING)
        reg.complete(ritual_id, outputs={"source": "day_workflows.close_day"})
    except Exception as e:
        ritual_warning = str(e)
        _log(f"ritual failed during close_day: {e}")

    # ── Build durable close recap ───────────────────────────────────────
    completed = completed_today or []
    unresolved_items = unresolved or []
    overnight = overnight_tasks or []

    recap_parts = []
    if completed:
        recap_parts.append("Completed: " + "; ".join(completed))
    if unresolved_items:
        recap_parts.append("Unresolved: " + "; ".join(unresolved_items))
    if overnight:
        recap_parts.append("Overnight: " + "; ".join(overnight))
    if continuity_notes:
        recap_parts.append("Notes: " + continuity_notes)
    close_recap = " | ".join(recap_parts) if recap_parts else None

    # ── Determine day_mode ──────────────────────────────────────────────
    if overnight:
        day_mode = OperatorDayMode.OVERNIGHT
    else:
        day_mode = OperatorDayMode.INACTIVE

    now = _utcnow()

    # ── Update session record ───────────────────────────────────────────
    session.is_day_open = False
    session.day_mode = day_mode
    session.closed_at = now
    session.ritual_close_id = ritual_id
    session.unfinished_priorities = unresolved_items
    session.overnight_tasks = overnight
    session.continuity_notes_for_next_open = continuity_notes
    session.last_resume_context = resume_context
    session.last_briefing_summary = close_recap
    if discord_channel_id:
        session.last_active_discord_channel_id = discord_channel_id
    store.put(session)

    # ── Build response ──────────────────────────────────────────────────
    result: dict[str, Any] = {
        "status": "ok",
        "day_session_id": session.day_session_id,
        "ritual_id": ritual_id,
        "summary": {
            "completed_today": completed,
            "unresolved": unresolved_items,
            "overnight_tasks": overnight,
            "continuity_notes": continuity_notes,
            "day_mode": day_mode.value,
            "active_workspace": session.active_workspace,
            "node_preference": session.node_preference,
        },
        "closed_at": now,
    }
    if ritual_warning:
        result["ritual_warning"] = ritual_warning
    return result
```

- [ ] **Step 4: Compile check**

Run: `python3 -m py_compile eos_ai/substrate/day_workflows.py`
Expected: no output (success).

- [ ] **Step 5: Run tests to verify they pass**

Run: `python3 tests/substrate/test_day_workflows.py`
Expected: all passed, 0 failed.

- [ ] **Step 6: Format**

Run: `ruff format eos_ai/substrate/day_workflows.py tests/substrate/test_day_workflows.py`

- [ ] **Step 7: Commit**

```bash
git add eos_ai/substrate/day_workflows.py tests/substrate/test_day_workflows.py
git commit -m "feat: day workflows — open_day/close_day with ritual integration

Coordinates OperatorSessionStore with existing RitualRegistry. open_day
creates a new session, inherits prior continuity, starts an OPEN_DAY
ritual. close_day writes continuity fields and starts a CLOSE_DAY ritual.
Both handle ritual failures as best-effort warnings. No LLM, no tmux,
no Discord send logic.

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Task 3: Discord Day Command Detection — Regex + Tests

**Files:**
- Create: `tests/substrate/test_day_discord_detect.py`

The `_detect_day_command` function will live in `discord_bot.py` (Task 4), but we test the regex logic in isolation first.

- [ ] **Step 1: Write the test file**

Create `tests/substrate/test_day_discord_detect.py`:

```python
"""Unit tests for day command detection regex.

Tests the _detect_day_command function that will be added to discord_bot.py.
The function is extracted here for isolated testing.

Run directly:
    python3 tests/substrate/test_day_discord_detect.py
"""

from __future__ import annotations

import re
import sys

sys.path.insert(0, "/opt/OS")

_PASS = 0
_FAIL = 0


def _report(name: str, passed: bool, detail: str = "") -> None:
    global _PASS, _FAIL  # noqa: PLW0603
    if passed:
        _PASS += 1
    else:
        _FAIL += 1
    tag = "PASS" if passed else "FAIL"
    suffix = f" — {detail}" if detail else ""
    print(f"  [{tag}] {name}{suffix}")


# ─── Regex (must match discord_bot.py implementation exactly) ─────────────

_OPEN_DAY_PHRASES = [
    r"start my day",
    r"open day",
    r"open my day",
    r"open session",
]

_CLOSE_DAY_PHRASES = [
    r"close day",
    r"end my day",
    r"close my day",
    r"close session",
    r"eod",
]

_OPEN_EXACT = [r"good morning"]
_CLOSE_EXACT = [r"good night"]

_OPEN_PATTERN = re.compile(
    r"^\s*(?:" + "|".join(_OPEN_DAY_PHRASES) + r")\s*[.!]?\s*$",
    re.IGNORECASE,
)
_CLOSE_PATTERN = re.compile(
    r"^\s*(?:" + "|".join(_CLOSE_DAY_PHRASES) + r")\s*[.!]?\s*$",
    re.IGNORECASE,
)
_OPEN_EXACT_PATTERN = re.compile(
    r"^\s*(?:" + "|".join(_OPEN_EXACT) + r")\s*[.!]?\s*$",
    re.IGNORECASE,
)
_CLOSE_EXACT_PATTERN = re.compile(
    r"^\s*(?:" + "|".join(_CLOSE_EXACT) + r")\s*[.!]?\s*$",
    re.IGNORECASE,
)


def _detect_day_command(text: str) -> str | None:
    """Detect day ritual commands from message text.

    Returns "open_day", "close_day", or None.
    Skips messages starting with '!' (bang commands handled separately).
    """
    if text.startswith("!"):
        return None
    if _OPEN_PATTERN.match(text):
        return "open_day"
    if _CLOSE_PATTERN.match(text):
        return "close_day"
    if _OPEN_EXACT_PATTERN.match(text):
        return "open_day"
    if _CLOSE_EXACT_PATTERN.match(text):
        return "close_day"
    return None


# ─── Tests ───────────────────────────────────────────────────────────────────


def test_open_day_triggers():
    cases = [
        ("start my day", "open_day"),
        ("Start My Day", "open_day"),
        ("open day", "open_day"),
        ("open my day", "open_day"),
        ("open session", "open_day"),
        ("good morning", "open_day"),
        ("Good Morning!", "open_day"),
        ("  start my day  ", "open_day"),
        ("open day.", "open_day"),
    ]
    for text, expected in cases:
        result = _detect_day_command(text)
        _report(f"open: {text!r}", result == expected, f"got {result!r}")


def test_close_day_triggers():
    cases = [
        ("close day", "close_day"),
        ("end my day", "close_day"),
        ("close my day", "close_day"),
        ("close session", "close_day"),
        ("eod", "close_day"),
        ("EOD", "close_day"),
        ("good night", "close_day"),
        ("Good Night!", "close_day"),
        ("  close day  ", "close_day"),
    ]
    for text, expected in cases:
        result = _detect_day_command(text)
        _report(f"close: {text!r}", result == expected, f"got {result!r}")


def test_no_match():
    """These should NOT trigger day commands."""
    cases = [
        "I want to start my day planner project",
        "can you open day mode for the API",
        "let's close day trading logic",
        "what is eod price",
        "good morning everyone how are you",
        "say good night to the team",
        "deploy the webhook",
        "fix auth bug",
        "!openday",
        "!closeday",
        "!eod",
    ]
    for text in cases:
        result = _detect_day_command(text)
        _report(f"no-match: {text!r}", result is None, f"got {result!r}")


def test_bang_prefix_skip():
    """Messages starting with ! must be skipped entirely."""
    cases = [
        "!start my day",
        "!open day",
        "!close day",
        "!eod",
        "!openday",
        "!closeday",
    ]
    for text in cases:
        result = _detect_day_command(text)
        _report(f"bang-skip: {text!r}", result is None, f"got {result!r}")


if __name__ == "__main__":
    print("=== day command detection tests ===")
    test_open_day_triggers()
    test_close_day_triggers()
    test_no_match()
    test_bang_prefix_skip()
    print(f"\n  {_PASS} passed, {_FAIL} failed")
    sys.exit(1 if _FAIL > 0 else 0)
```

- [ ] **Step 2: Run tests to verify they pass**

Run: `python3 tests/substrate/test_day_discord_detect.py`
Expected: all passed, 0 failed. (These test the regex in isolation — no external dependencies.)

- [ ] **Step 3: Format**

Run: `ruff format tests/substrate/test_day_discord_detect.py`

- [ ] **Step 4: Commit**

```bash
git add tests/substrate/test_day_discord_detect.py
git commit -m "test: day command detection regex — open/close/no-match/bang-skip

Isolated unit tests for _detect_day_command regex patterns before
integrating into discord_bot.py. Covers positive matches, false
positive rejection, and bang-prefix skip guard.

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Task 4: Discord Integration — Intercept + Bang Commands + Response Dispatch

**Files:**
- Modify: `services/discord_bot.py`

- [ ] **Step 1: Add the day command detection function and helpers**

Add the following block in `services/discord_bot.py` **after** the existing imports section and **before** the `on_message` handler. Find a suitable location near the other helper functions (around the `# ─── Commands ───` section, or in a new section above it).

Add this code block after the channel/intent maps and before `on_message`:

```python
# ─── Day ritual helpers ──────────────────────────────────────────────────────

_OPEN_DAY_PHRASES = [
    r"start my day",
    r"open day",
    r"open my day",
    r"open session",
]

_CLOSE_DAY_PHRASES = [
    r"close day",
    r"end my day",
    r"close my day",
    r"close session",
    r"eod",
]

_OPEN_EXACT = [r"good morning"]
_CLOSE_EXACT = [r"good night"]

_OPEN_PATTERN = re.compile(
    r"^\s*(?:" + "|".join(_OPEN_DAY_PHRASES) + r")\s*[.!]?\s*$",
    re.IGNORECASE,
)
_CLOSE_PATTERN = re.compile(
    r"^\s*(?:" + "|".join(_CLOSE_DAY_PHRASES) + r")\s*[.!]?\s*$",
    re.IGNORECASE,
)
_OPEN_EXACT_PATTERN = re.compile(
    r"^\s*(?:" + "|".join(_OPEN_EXACT) + r")\s*[.!]?\s*$",
    re.IGNORECASE,
)
_CLOSE_EXACT_PATTERN = re.compile(
    r"^\s*(?:" + "|".join(_CLOSE_EXACT) + r")\s*[.!]?\s*$",
    re.IGNORECASE,
)


def _detect_day_command(text: str) -> str | None:
    """Detect day ritual commands from message text.

    Returns "open_day", "close_day", or None.
    Skips messages starting with '!' (bang commands handled separately).
    """
    if text.startswith("!"):
        return None
    if _OPEN_PATTERN.match(text):
        return "open_day"
    if _CLOSE_PATTERN.match(text):
        return "close_day"
    if _OPEN_EXACT_PATTERN.match(text):
        return "open_day"
    if _CLOSE_EXACT_PATTERN.match(text):
        return "close_day"
    return None


def _run_day_command(
    cmd: str,
    *,
    workspace: str | None = None,
    node_preference: str | None = None,
    discord_channel_id: str | None = None,
    continuity_text: str | None = None,
) -> dict:
    """Execute open_day or close_day workflow. Returns result dict."""
    try:
        from eos_ai.substrate.day_workflows import close_day, open_day

        if cmd == "open_day":
            return open_day(
                workspace=workspace,
                node_preference=node_preference,
                discord_channel_id=discord_channel_id,
            )
        elif cmd == "close_day":
            return close_day(
                continuity_notes=continuity_text,
                discord_channel_id=discord_channel_id,
            )
        else:
            return {"status": "error", "detail": f"unknown command: {cmd}"}
    except Exception as e:
        print(f"[DayRitual] error in {cmd}: {e}")
        return {"status": "error", "detail": str(e)}


def _format_day_result(result: dict) -> str:
    """Format a day workflow result dict into Discord-safe markdown."""
    status = result.get("status", "error")

    if status == "already_open":
        ws = result.get("active_workspace", "unknown")
        mode = result.get("day_mode", "unknown")
        opened = result.get("opened_at", "unknown")
        return f"Day is already open.\nWorkspace: {ws} | Mode: {mode} | Opened: {opened}"

    if status == "not_open":
        return "No day is currently open. Use `start my day` or `!openday` first."

    if status == "error":
        return f"Day ritual error: {result.get('detail', 'unknown')}"

    # ── open_day ok ──────────────────────────────────────────────────────
    if "briefing" in result:
        b = result["briefing"]
        mode = result.get("day_mode", "unknown")
        ws = result.get("active_workspace", "unknown")

        left_off = b.get("where_we_left_off") or "Fresh start."
        priorities = b.get("unfinished_priorities") or []
        overnight = b.get("overnight_tasks") or []
        first_action = b.get("recommended_first_action") or "Check your priorities."
        resume = b.get("resume_context")

        lines = [
            f"**Day Open** — {mode}",
            f"Workspace: {ws} | Node: {result.get('node_preference', 'auto')}",
            "",
            f"**Where we left off:**\n{left_off}",
            "",
        ]
        if priorities:
            lines.append("**Unfinished priorities:**")
            for p in priorities:
                lines.append(f"- {p}")
        else:
            lines.append("**Unfinished priorities:**\nNone.")
        lines.append("")
        if overnight:
            lines.append("**Overnight tasks:**")
            for t in overnight:
                lines.append(f"- {t}")
        else:
            lines.append("**Overnight tasks:**\nNone.")
        lines.append("")
        lines.append(f"**Recommended first action:**\n{first_action}")
        if resume:
            lines.append(f"\n**Resume context:**\n{resume}")

        warning = result.get("ritual_warning")
        if warning:
            lines.append(f"\n_Ritual warning: {warning}_")

        return "\n".join(lines)

    # ── close_day ok ─────────────────────────────────────────────────────
    if "summary" in result:
        s = result["summary"]
        completed = s.get("completed_today") or []
        unresolved = s.get("unresolved") or []
        overnight = s.get("overnight_tasks") or []
        notes = s.get("continuity_notes")
        mode = s.get("day_mode", "inactive")

        lines = [f"**Day Closed** — {mode}", ""]
        if completed:
            lines.append("**Completed today:**")
            for c in completed:
                lines.append(f"- {c}")
        else:
            lines.append("**Completed today:**\nNothing logged.")
        lines.append("")
        if unresolved:
            lines.append("**Unresolved:**")
            for u in unresolved:
                lines.append(f"- {u}")
        else:
            lines.append("**Unresolved:**\nAll clear.")
        lines.append("")
        if overnight:
            lines.append("**Overnight tasks:**")
            for t in overnight:
                lines.append(f"- {t}")
        else:
            lines.append("**Overnight tasks:**\nNone.")
        if notes:
            lines.append(f"\n**Continuity notes:**\n{notes}")

        warning = result.get("ritual_warning")
        if warning:
            lines.append(f"\n_Ritual warning: {warning}_")

        return "\n".join(lines)

    return f"Day ritual completed with status: {status}"


async def _send_day_response(
    invoking_channel,
    formatted_text: str,
) -> None:
    """Send formatted day response to invoking channel + mirror to #morning-brief.

    Mirror is best-effort only — failure does not affect the primary response.
    """
    for chunk in chunk_message(formatted_text):
        await invoking_channel.send(chunk)

    # ── Best-effort mirror to #morning-brief ─────────────────────────────
    try:
        _mb_id = CHANNEL_IDS.get("morning-brief")
        if _mb_id and str(invoking_channel.id) != str(_mb_id):
            _mb_chan = bot.get_channel(_mb_id)
            if _mb_chan:
                for chunk in chunk_message(formatted_text):
                    await _mb_chan.send(chunk)
    except Exception as _mirror_exc:
        print(f"[DayRitual] mirror to #morning-brief failed: {_mirror_exc}")
```

- [ ] **Step 2: Add the natural-language intercept in on_message**

In `on_message()`, insert the intercept block **after** the `#wins` guard (line 1255) and **before** the onboarding check (line 1257). Find this exact code in `discord_bot.py`:

```python
    # #wins is one-way announcement channel
    if channel_name == "wins":
        await bot.process_commands(message)
        return

    # ── Active onboarding session — route before anything else ────────────────
```

Insert between these two blocks:

```python
    # ── Day ritual intercept (before onboarding/CC injection/gateway) ────────
    _day_cmd = _detect_day_command(text)
    if _day_cmd:
        async with message.channel.typing():
            loop = asyncio.get_event_loop()
            _day_result = await loop.run_in_executor(
                None,
                lambda cmd=_day_cmd: _run_day_command(
                    cmd,
                    discord_channel_id=str(message.channel.id),
                ),
            )
            _day_text = _format_day_result(_day_result)
            await _send_day_response(message.channel, _day_text)
        return

```

- [ ] **Step 3: Add the bang commands**

Add these two commands in the `# ─── Commands ───` section of `discord_bot.py`, after the existing `cmd_eod` function:

```python
@bot.command(name="openday")
async def cmd_openday(ctx: commands.Context, *, args: str = ""):
    """Open the operator's day. Usage: !openday [workspace=builder] [node=local]"""
    if ctx.author.id != FOUNDER_ID:
        await ctx.reply("Founder only.")
        return
    # Parse optional overrides
    workspace = None
    node_pref = None
    for part in args.split():
        if part.startswith("workspace="):
            workspace = part.split("=", 1)[1]
        elif part.startswith("node="):
            node_pref = part.split("=", 1)[1]
    async with ctx.typing():
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            lambda: _run_day_command(
                "open_day",
                workspace=workspace,
                node_preference=node_pref,
                discord_channel_id=str(ctx.channel.id),
            ),
        )
        formatted = _format_day_result(result)
        await _send_day_response(ctx.channel, formatted)


@bot.command(name="closeday")
async def cmd_closeday(ctx: commands.Context, *, args: str = ""):
    """Close the operator's day. Usage: !closeday [continuity notes as free text]"""
    if ctx.author.id != FOUNDER_ID:
        await ctx.reply("Founder only.")
        return
    continuity = args.strip() if args.strip() else None
    async with ctx.typing():
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            lambda: _run_day_command(
                "close_day",
                continuity_text=continuity,
                discord_channel_id=str(ctx.channel.id),
            ),
        )
        formatted = _format_day_result(result)
        await _send_day_response(ctx.channel, formatted)
```

- [ ] **Step 4: Compile check**

Run: `python3 -m py_compile services/discord_bot.py`
Expected: no output (success).

- [ ] **Step 5: Verify the intercept ordering**

Manually read the `on_message` function to verify:
1. `_detect_day_command` is called AFTER `text = message.content.strip()` and `#wins` guard
2. `_detect_day_command` is called BEFORE onboarding check
3. `_detect_day_command` is called BEFORE CC injection block
4. `_detect_day_command` skips messages starting with `!` (the function itself guards this)

Run: `grep -n "day_cmd\|_detect_day\|onboarding\|CC injection\|process_commands" services/discord_bot.py | head -20`

Expected output should show `_detect_day_command` appearing before both the onboarding block and the CC injection block.

- [ ] **Step 6: Format**

Run: `ruff format services/discord_bot.py`

- [ ] **Step 7: Commit**

```bash
git add services/discord_bot.py
git commit -m "feat: Discord day rituals — natural language intercept + bang commands

Adds _detect_day_command regex intercept (conservative, anchored patterns)
before CC injection/gateway. Adds !openday and !closeday bang commands.
Both paths use shared _run_day_command/_format_day_result/_send_day_response
helpers. Morning-brief mirror is best-effort only. Bang prefix messages
skip natural-language detection to prevent double-fire.

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Task 5: Integration Smoke Test + Final Verification

**Files:**
- No new files — runs existing tests and live verification commands

- [ ] **Step 1: Run all smoke tests**

```bash
python3 tests/substrate/test_operator_session.py && \
python3 tests/substrate/test_day_workflows.py && \
python3 tests/substrate/test_day_discord_detect.py
```

Expected: all tests pass across all three files.

- [ ] **Step 2: Import verification**

```bash
python3 -c "from eos_ai.substrate.operator_session import OperatorSessionStore, OperatorDayMode, OperatorSession; print('operator_session: ok')" && \
python3 -c "from eos_ai.substrate.day_workflows import open_day, close_day; print('day_workflows: ok')"
```

Expected: both print ok.

- [ ] **Step 3: End-to-end smoke — open, close, continuity, restart**

```bash
python3 -c "
import sys; sys.path.insert(0, '/opt/OS')
from eos_ai.substrate.operator_session import OperatorSessionStore
from eos_ai.substrate.day_workflows import open_day, close_day
from eos_ai.substrate.rituals import RitualRegistry

# Reset for clean test
OperatorSessionStore.reset_default_for_tests()
RitualRegistry.reset_default_for_tests()

# 1. Open day
r1 = open_day()
assert r1['status'] == 'ok', f'open failed: {r1}'
print(f'PASS: open_day -> {r1[\"day_session_id\"]}')

# 2. Close day with continuity
r2 = close_day(
    completed_today=['shipped webhook'],
    unresolved=['auth bug'],
    overnight_tasks=['run backfill'],
    continuity_notes='pick up auth middleware',
    resume_context='auth.py line 42',
)
assert r2['status'] == 'ok', f'close failed: {r2}'
print(f'PASS: close_day -> closed_at={r2[\"closed_at\"]}')

# 3. Restart-safe
OperatorSessionStore.reset_default_for_tests()
session = OperatorSessionStore.default().get()
assert session is not None, 'session lost after restart'
assert not session.is_day_open, 'should be closed'
assert session.unfinished_priorities == ['auth bug'], f'priorities: {session.unfinished_priorities}'
print('PASS: restart-safe persistence')

# 4. Re-open and check continuity
RitualRegistry.reset_default_for_tests()
r3 = open_day()
assert r3['status'] == 'ok', f'reopen failed: {r3}'
b = r3['briefing']
assert b['unfinished_priorities'] == ['auth bug'], f'continuity lost: {b}'
assert b['where_we_left_off'] == 'pick up auth middleware'
assert b['recommended_first_action'] == 'auth bug'
assert b['resume_context'] == 'auth.py line 42'
print('PASS: continuity carries forward')

# 5. Rituals created
RitualRegistry.reset_default_for_tests()
# Load fresh from storage
rituals = RitualRegistry.default().history()
kinds = [r.kind.value for r in rituals]
assert 'open_day' in kinds, f'no open ritual: {kinds}'
assert 'close_day' in kinds, f'no close ritual: {kinds}'
print(f'PASS: rituals created ({len(rituals)} total)')

# Clean up
OperatorSessionStore.reset_default_for_tests()
print()
print('ALL INTEGRATION CHECKS PASSED')
"
```

Expected: ALL INTEGRATION CHECKS PASSED

- [ ] **Step 4: Verify Discord bot compiles cleanly**

```bash
python3 -m py_compile services/discord_bot.py && echo "discord_bot.py: ok"
```

Expected: ok

- [ ] **Step 5: Commit all test files (if not already committed)**

Verify everything is committed:
```bash
git status
```

If any uncommitted test files remain:
```bash
git add tests/substrate/test_operator_session.py tests/substrate/test_day_workflows.py tests/substrate/test_day_discord_detect.py
git commit -m "chore: ensure all day ritual test files are committed

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Summary of Deliverables

| Deliverable | Location |
|-------------|----------|
| Session spine data model + store | `eos_ai/substrate/operator_session.py` |
| Day workflows (open/close) | `eos_ai/substrate/day_workflows.py` |
| Discord integration | `services/discord_bot.py` (3 insertions, 0 deletions of existing code) |
| Session spine tests | `tests/substrate/test_operator_session.py` |
| Workflow tests | `tests/substrate/test_day_workflows.py` |
| Detection regex tests | `tests/substrate/test_day_discord_detect.py` |

## Deferred (not in this plan)

- LLM-synthesized briefing
- Ambient context injection
- operator_state.py / operator_transitions.py wiring
- Merging `!brief` / `!eod` into day workflows
- Structured `!closeday` arg parsing
- Voice/TTS entrypoints
- Local station scene launching
- Clap/wake word integration
- Capability-aware routing
- Historical session queries
- Station daemon integration
