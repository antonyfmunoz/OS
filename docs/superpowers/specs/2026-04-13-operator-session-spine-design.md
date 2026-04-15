# Unified Operator Session State + Open/Close Rituals v1

**Date:** 2026-04-13
**Status:** Approved
**Approach:** C — Session Spine + Ritual Integration

---

## Problem

Multiple parallel session/state systems exist in the substrate but do not
share one authoritative source of truth for the operator's daily lifecycle.
This blocks startup ritual, close ritual, cross-day continuity, and future
routing improvements.

The existing substrate has:
- `operator_state.py` — voice/wake FSM per node (OperatorMode)
- `rituals.py` — workflow lifecycle tracker (OPEN_DAY / CLOSE_DAY)
- `session_orchestration.py` — expected tmux sessions registry
- `nodes.py` — execution target registry
- `voice_session.py` — live voice interaction container

None of these own "where is the operator in their day" as a unified concern.

## Solution

Build three things:

1. **Operator session spine** — a new substrate registry that is the single
   authoritative source of truth for daily operator lifecycle state
2. **Day workflows** — coordination layer that drives both the session spine
   and the existing ritual registry together
3. **Discord integration** — natural language intercept + bang commands that
   invoke the day workflows

## Architectural Decisions

### Separate day_mode from OperatorMode

The existing `OperatorMode` (IDLE/STARTING/ACTIVE/FOCUSED/CLOSING/UNAVAILABLE)
drives the voice/wake/ritual state machine in `operator_transitions.py`. The
daily lifecycle modes (inactive/remote_active/local_active/deep_work/overnight)
are a different concern — where the operator is and what posture they are in
today, not what the voice subsystem is doing.

These are kept as separate enums on separate stores. `OperatorMode` stays on
`operator_state.py`. `OperatorDayMode` lives on the new session spine. No
rewrites to `operator_transitions.py`.

### Continuity on the spine, not a separate document

Continuity fields (unfinished_priorities, overnight_tasks,
continuity_notes_for_next_open, last_resume_context) live directly on the
session spine dataclass. One model, one store. A separate continuity document
would add indirection without benefit for a single-operator v1.

### Deterministic briefing, no LLM

`open_day` composes the briefing by formatting the continuity fields written
by the previous `close_day`. No LLM call, no external data fetch. Fast,
free, deterministic. LLM synthesis is a future layer.

### Session spine + ritual integration (not duplication or overloading)

The session spine owns persistent operator context. The ritual registry owns
workflow progression (PENDING -> COMPLETED). Both are updated together by the
day workflows module. The ritual is not overloaded with continuity fields.
The session spine is not burdened with workflow state transitions.

---

## 1. Session Spine Data Model

**File:** `eos_ai/substrate/operator_session.py`
**Storage key:** `"operator_session"`

### OperatorDayMode Enum

```
INACTIVE       — no day open
REMOTE_ACTIVE  — operating from Discord/phone
LOCAL_ACTIVE   — at the desk, local station
DEEP_WORK      — focused block, minimize interrupts
OVERNIGHT      — day closed, overnight tasks running
```

### OperatorSession Dataclass

| Field | Type | Semantics |
|-------|------|-----------|
| `day_session_id` | `str` | `"ds_<12hex>"`, unique per open/close cycle |
| `day_mode` | `OperatorDayMode` | Daily lifecycle posture (separate from voice/wake OperatorMode) |
| `is_day_open` | `bool` | Whether the current session cycle is active |
| `active_workspace` | `str` | `"product"` or `"builder"` — the workspace to resume into on open_day unless explicitly overridden |
| `node_preference` | `str` | `"auto"`, `"local"`, or `"vps"` |
| `last_active_node` | `str \| None` | Last node that executed work |
| `last_active_discord_channel_id` | `str \| None` | Channel ID of last Discord interaction |
| `active_tmux_session` | `str \| None` | The currently resolved or most recently targeted execution session |
| `ritual_open_id` | `str \| None` | Pointer to the OPEN_DAY ritual in RitualRegistry |
| `ritual_close_id` | `str \| None` | Pointer to the CLOSE_DAY ritual in RitualRegistry |
| `created_at` | `str` | ISO UTC — when this session record was created |
| `opened_at` | `str \| None` | ISO UTC — when open_day ran |
| `closed_at` | `str \| None` | ISO UTC — when close_day ran |
| `updated_at` | `str` | ISO UTC — last mutation timestamp |
| `last_briefing_summary` | `str \| None` | Human-readable recap (set by close_day as the durable close recap) |
| `unfinished_priorities` | `list[str]` | Items that did not get done (written by close_day, inherited by next open_day) |
| `overnight_tasks` | `list[str]` | Tasks that should continue running overnight |
| `continuity_notes_for_next_open` | `str \| None` | Free-text notes for the next open_day briefing |
| `last_resume_context` | `str \| None` | Concise carry-forward context distinct from broader continuity notes |

### OperatorSessionStore

- Singleton pattern via `OperatorSessionStore.default()`
- Thread-safe (RLock)
- Dual-layer persistence: in-memory + `get_storage().put("operator_session", ...)`
- Holds **one record** — the current/last session (not a collection)
- Methods:
  - `get() -> OperatorSession | None` — load current session
  - `put(session: OperatorSession) -> None` — persist (sets updated_at)
  - `reset_default_for_tests() -> None` — test hook

---

## 2. Day Workflows

**File:** `eos_ai/substrate/day_workflows.py`

Two public functions. No classes. No LLM calls. No tmux logic. No Discord
send logic. No voice/TTS. No operator_state/operator_transitions wiring.

### open_day()

```python
def open_day(
    *,
    workspace: str | None = None,
    node_preference: str | None = None,
    discord_channel_id: str | None = None,
) -> dict:
```

**Behavior:**

1. Load current OperatorSession from store
2. If `is_day_open is True` → return `{"status": "already_open", ...}` with
   current state. No new ritual. No session spine mutation.
3. Else:
   a. Start an OPEN_DAY ritual via `RitualRegistry.default().start()`
   b. Advance ritual: INITIATED -> GATHERING -> BRIEFING -> COMPLETED
   c. If ritual start/advance fails: continue, set `ritual_warning` in response
   d. Read continuity fields from the **previous** session (if any)
   e. Compose deterministic briefing:
      - `where_we_left_off` = prior `continuity_notes_for_next_open`
      - `unfinished_priorities` = prior `unfinished_priorities`
      - `overnight_tasks` = prior `overnight_tasks`
      - `recommended_first_action` = first item of `unfinished_priorities` or None
      - `resume_context` = prior `last_resume_context`
   f. Create a **new** OperatorSession record (new `day_session_id`):
      - `created_at` = now
      - `opened_at` = now
      - `is_day_open` = True
      - `day_mode` = LOCAL_ACTIVE if node_preference == "local" else REMOTE_ACTIVE
        (v1 heuristic, not a permanent semantic equivalence)
      - `active_workspace` = workspace arg or prior value or "builder"
      - `node_preference` = node_preference arg or prior value or "auto"
      - Inherit prior continuity fields into the new record
      - `ritual_open_id` = new ritual's ID (or None if ritual failed)
   g. Persist new session
4. Return briefing dict

**Return shape:**
```json
{
    "status": "ok",
    "day_session_id": "ds_...",
    "ritual_id": "ritual_...",
    "briefing": {
        "where_we_left_off": "...",
        "unfinished_priorities": [],
        "overnight_tasks": [],
        "recommended_first_action": "...",
        "resume_context": "..."
    },
    "day_mode": "remote_active",
    "active_workspace": "builder",
    "opened_at": "2026-04-13T..."
}
```

### close_day()

```python
def close_day(
    *,
    completed_today: list[str] | None = None,
    unresolved: list[str] | None = None,
    overnight_tasks: list[str] | None = None,
    continuity_notes: str | None = None,
    resume_context: str | None = None,
    discord_channel_id: str | None = None,
) -> dict:
```

**Behavior:**

1. Load current OperatorSession from store
2. If `is_day_open is False` (or no session exists) → return `{"status": "not_open"}`
3. Else:
   a. Start a CLOSE_DAY ritual via `RitualRegistry.default().start()`
   b. Advance ritual: INITIATED -> GATHERING -> COMPLETED
   c. If ritual start/advance fails: continue, set `ritual_warning` in response
   d. Update the **current** session record:
      - `is_day_open` = False
      - `day_mode` = OVERNIGHT if overnight_tasks else INACTIVE
      - `closed_at` = now
      - `ritual_close_id` = new ritual's ID (or None if ritual failed)
      - `unfinished_priorities` = unresolved arg (replaces previous)
      - `overnight_tasks` = overnight_tasks arg
      - `continuity_notes_for_next_open` = continuity_notes arg
      - `last_resume_context` = resume_context arg
      - `last_briefing_summary` = formatted close recap containing completed
        and unresolved context (the durable human-readable close summary)
      - `last_active_discord_channel_id` = discord_channel_id if provided
   e. Persist session
4. Return close summary dict

**Return shape:**
```json
{
    "status": "ok",
    "day_session_id": "ds_...",
    "ritual_id": "ritual_...",
    "summary": {
        "completed_today": [],
        "unresolved": [],
        "overnight_tasks": [],
        "continuity_notes": "...",
        "day_mode": "overnight",
        "active_workspace": "builder",
        "node_preference": "auto"
    },
    "closed_at": "2026-04-13T..."
}
```

---

## 3. Discord Integration

**File:** `services/discord_bot.py` — two additive touch points.

### Touch Point 1: Natural Language Intercept

**Location:** After `text = message.content.strip()` and `#wins` guard,
before onboarding check, before CC injection.

**Guard:** If message starts with command prefix (`!`), skip
`_detect_day_command()` entirely. Let the command framework own those.

**`_detect_day_command(text: str) -> str | None`**

Conservative, anchored regex. Returns `"open_day"`, `"close_day"`, or `None`.

v1 triggers:

| Phrase | Maps to |
|--------|---------|
| `start my day` | open_day |
| `open day` | open_day |
| `open my day` | open_day |
| `open session` | open_day |
| `close day` | close_day |
| `end my day` | close_day |
| `close my day` | close_day |
| `close session` | close_day |
| `eod` | close_day |
| `good morning` | open_day (exact full-message match only) |
| `good night` | close_day (exact full-message match only) |

Case-insensitive. No fuzzy matching. No broad substring matching. The phrase
must be the dominant content of the message.

### Touch Point 2: Bang Commands

```
!openday [workspace=builder] [node=local]
!closeday [free text as continuity_notes]
```

- `!openday` with no args → default workspace and node preference
- `!openday workspace=builder node=local` → overrides
- `!closeday` with no args → minimal close (timestamps + mode transition)
- `!closeday shipped the webhook, auth still broken` → free text = continuity_notes

### Shared Response Dispatch

Both paths use a shared helper:

```python
async def _send_day_response(
    invoking_channel,
    formatted_text: str,
) -> None:
```

- Sends formatted response to the invoking channel (chunked)
- Mirrors to `#morning-brief` (ID 1485765524766982234) unless already there
- Mirror is best-effort: resolution/send failure does not fail the ritual
- Invoking-channel reply is the primary success path

### Internal Split

```
_run_day_command(cmd, ...) -> dict     # calls open_day() or close_day()
_format_day_result(result) -> str      # dict -> Discord-safe markdown
_send_day_response(channel, text)      # send + mirror
```

### Not Changed

- `!brief` and `!eod` remain unchanged
- CC injection block untouched
- PseudoLive fallback untouched
- Gateway path untouched
- Meeting detection untouched
- `discord_mode_routing.py` untouched
- `cc_webhook_receiver.py` untouched

---

## 4. Files Created / Modified

| File | Action | Risk |
|------|--------|------|
| `eos_ai/substrate/operator_session.py` | **Create** | LOW — new file, no imports from hot path |
| `eos_ai/substrate/day_workflows.py` | **Create** | LOW — new file, imports only from substrate |
| `services/discord_bot.py` | **Modify** | MEDIUM — additive intercept + 2 commands, no existing logic changed |

No changes to:
- `gateway.py`
- `cognitive_loop.py`
- `model_router.py`
- `agent_runtime.py`
- `primitives.py`
- `operator_state.py`
- `operator_transitions.py`
- `rituals.py`
- `ritual_runner.py`
- `discord_mode_routing.py`
- `cc_webhook_receiver.py`

---

## 5. Verification Plan

1. **Import check:** `python3 -c "from eos_ai.substrate.operator_session import OperatorSessionStore; print('ok')"`
2. **Import check:** `python3 -c "from eos_ai.substrate.day_workflows import open_day, close_day; print('ok')"`
3. **Smoke test — open_day persists:**
   ```python
   from eos_ai.substrate.day_workflows import open_day
   result = open_day()
   assert result["status"] == "ok"
   assert result["day_session_id"].startswith("ds_")
   ```
4. **Smoke test — close_day persists:**
   ```python
   from eos_ai.substrate.day_workflows import close_day
   result = close_day(unresolved=["auth bug"], continuity_notes="pick up auth")
   assert result["status"] == "ok"
   ```
5. **Smoke test — continuity carries forward:**
   ```python
   result2 = open_day()
   assert result2["briefing"]["unfinished_priorities"] == ["auth bug"]
   assert result2["briefing"]["where_we_left_off"] == "pick up auth"
   ```
6. **Smoke test — restart-safe:**
   ```python
   # Reset in-memory singleton, reload from storage
   OperatorSessionStore.reset_default_for_tests()
   session = OperatorSessionStore.default().get()
   assert session is not None
   assert session.is_day_open  # still reflects last state
   ```
7. **Smoke test — ritual progression:**
   ```python
   from eos_ai.substrate.rituals import RitualRegistry
   rituals = RitualRegistry.default().history()
   assert any(r.kind.value == "open_day" for r in rituals)
   ```
8. **Discord path:** Send "start my day" in a Discord channel, verify
   response appears in both the invoking channel and `#morning-brief`

---

## 6. Deferred Items

- LLM-synthesized briefing (layer on top of deterministic formatting)
- Ambient context injection (SessionState.get_ambient() market signals)
- operator_state.py / operator_transitions.py wiring (day_mode -> OperatorMode sync)
- Merging `!brief` into `open_day` or `!eod` into `close_day`
- Structured `!closeday` arg parsing (separate completed/unresolved/overnight fields)
- Voice/TTS entrypoints for open/close
- Local station scene launching
- Clap/wake word integration
- Capability-aware routing based on day_mode
- Historical session queries (list of past day sessions)
- Station daemon integration
