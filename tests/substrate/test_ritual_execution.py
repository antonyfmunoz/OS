"""
Tests for ritual execution driver + profile resolution.

Covers:
    1. Deterministic execution (same inputs → same result)
    2. Correct profile resolution paths
    3. Correct presence transitions
    4. Correct mode transitions
    5. Artifact creation
    6. Step event emission order
    7. Replay idempotency
    8. No adapter imports
"""

import sys

sys.path.insert(0, "/opt/OS")

from umh.substrate.daily_rituals import (
    CANONICAL_CLOSE_STEPS,
    CANONICAL_OPEN_STEPS,
    build_close_day_request,
    build_open_day_request,
)
from umh.substrate.handoff_artifact import (
    ARTIFACT_KIND_CLOSE_DAY_HANDOFF,
    ARTIFACT_KIND_OPEN_DAY_BRIEF,
)
from umh.substrate.presence_state import (
    PRESENCE_ACTIVE_STATION,
    PRESENCE_OFF,
    PRESENCE_OVERNIGHT_AUTONOMOUS,
    PRESENCE_REMOTE_LIGHT,
)
from umh.substrate.profile_resolution import (
    ActiveProfile,
    build_active_profile_mutations,
    compute_active_profile_id,
    load_active_profile,
    resolve_active_profile,
)
from umh.substrate.ritual_execution_driver import (
    RitualExecutionResult,
    build_close_day_started_event,
    build_open_day_started_event,
    build_ritual_completed_event,
    build_ritual_step_event,
    execute_close_day,
    execute_open_day,
)
from umh.substrate.runtime_profile import (
    build_runtime_profile,
    build_runtime_profile_mutations,
)

# ---------------------------------------------------------------------------
# Test infrastructure
# ---------------------------------------------------------------------------
_PASS = 0
_FAIL = 0

_FIXED_TS = "2026-04-17T12:00:00+00:00"
_SESSION_ID = "sess_test_001"


def _report(name: str, passed: bool, detail: str = "") -> None:
    global _PASS, _FAIL
    tag = "PASS" if passed else "FAIL"
    if passed:
        _PASS += 1
    else:
        _FAIL += 1
    suffix = f" — {detail}" if detail else ""
    print(f"  [{tag}] {name}{suffix}")


def _build_test_profile(
    name: str = "default_profile",
    mode: str = "active",
    presence: str = "active_station",
) -> tuple[dict, str]:
    """Build a test profile and return (state_with_profile, profile_id)."""
    profile = build_runtime_profile(
        name=name,
        default_mode=mode,
        default_presence=presence,
    )
    state: dict = {}
    for m in build_runtime_profile_mutations(profile):
        state[m["key"]] = m["value"]
    return state, profile.profile_id


# ===========================================================================
# 1. Profile Resolution Tests
# ===========================================================================


def test_profile_resolution_explicit() -> None:
    """Path 1: explicit requested_profile_id resolves correctly."""
    print("\n── Test 1: Profile resolution — explicit path ──")
    state, pid = _build_test_profile()

    profile, binding = resolve_active_profile(
        state, _SESSION_ID, requested_profile_id=pid, resolved_at=_FIXED_TS
    )

    _report("profile resolved", profile is not None)
    _report("binding resolved", binding is not None)
    _report("correct profile_id", binding is not None and binding.profile_id == pid)
    _report(
        "source is explicit",
        binding is not None and binding.source == "explicit",
    )
    _report(
        "profile name matches",
        profile is not None and profile.name == "default_profile",
    )


def test_profile_resolution_binding() -> None:
    """Path 2: existing binding in state resolves correctly."""
    print("\n── Test 2: Profile resolution — binding path ──")
    state, pid = _build_test_profile()

    # Create an existing binding in state
    existing = ActiveProfile(
        binding_id="apb_existing",
        runtime_session_id=_SESSION_ID,
        profile_id=pid,
        resolved_at="2026-04-17T08:00:00+00:00",
        source="explicit",
    )
    for m in build_active_profile_mutations(existing):
        state[m["key"]] = m["value"]

    # Resolve without explicit request — should find binding
    profile, binding = resolve_active_profile(state, _SESSION_ID, resolved_at=_FIXED_TS)

    _report("profile resolved via binding", profile is not None)
    _report("binding resolved", binding is not None)
    _report("source is binding", binding is not None and binding.source == "binding")
    _report("same profile_id", binding is not None and binding.profile_id == pid)


def test_profile_resolution_singleton() -> None:
    """Path 3: single profile in state auto-resolves."""
    print("\n── Test 3: Profile resolution — singleton path ──")
    state, pid = _build_test_profile()

    # No binding, no explicit request, but only one profile exists
    profile, binding = resolve_active_profile(state, _SESSION_ID, resolved_at=_FIXED_TS)

    _report("profile resolved via singleton", profile is not None)
    _report("binding resolved", binding is not None)
    _report(
        "source is singleton",
        binding is not None and binding.source == "singleton",
    )
    _report("correct profile_id", binding is not None and binding.profile_id == pid)


def test_profile_resolution_none() -> None:
    """Path 4: no profiles → returns None."""
    print("\n── Test 4: Profile resolution — no profiles ──")
    state: dict = {}

    profile, binding = resolve_active_profile(state, _SESSION_ID, resolved_at=_FIXED_TS)

    _report("profile is None", profile is None)
    _report("binding is None", binding is None)


def test_profile_resolution_ambiguous() -> None:
    """Path 4b: multiple profiles, no binding, no explicit → None."""
    print("\n── Test 5: Profile resolution — ambiguous (multiple profiles) ──")
    state: dict = {}
    for name in ("profile_a", "profile_b"):
        p = build_runtime_profile(
            name=name, default_mode="active", default_presence="active_station"
        )
        for m in build_runtime_profile_mutations(p):
            state[m["key"]] = m["value"]

    profile, binding = resolve_active_profile(state, _SESSION_ID, resolved_at=_FIXED_TS)

    _report("profile is None (ambiguous)", profile is None)
    _report("binding is None (ambiguous)", binding is None)


def test_profile_resolution_missing_explicit() -> None:
    """Explicit request for nonexistent profile → None."""
    print("\n── Test 6: Profile resolution — missing explicit ──")
    state: dict = {}

    profile, binding = resolve_active_profile(
        state, _SESSION_ID, requested_profile_id="prof_nonexistent"
    )

    _report("profile is None", profile is None)
    _report("binding is None", binding is None)


# ===========================================================================
# 2. Active Profile Persistence Tests
# ===========================================================================


def test_active_profile_persistence() -> None:
    """ActiveProfile round-trips through mutations → state → load."""
    print("\n── Test 7: ActiveProfile persistence round-trip ──")
    ap = ActiveProfile(
        binding_id=compute_active_profile_id(_SESSION_ID, _FIXED_TS),
        runtime_session_id=_SESSION_ID,
        profile_id="prof_abc123",
        resolved_at=_FIXED_TS,
        source="explicit",
    )

    mutations = build_active_profile_mutations(ap)
    _report("mutations not empty", len(mutations) > 0)
    _report("all ops are SET", all(m["op"] == "SET" for m in mutations))

    # Apply mutations to state
    state: dict = {}
    for m in mutations:
        state[m["key"]] = m["value"]

    loaded = load_active_profile(state, _SESSION_ID)
    _report("loaded successfully", loaded is not None)
    _report(
        "binding_id matches", loaded is not None and loaded.binding_id == ap.binding_id
    )
    _report(
        "profile_id matches", loaded is not None and loaded.profile_id == ap.profile_id
    )
    _report("source matches", loaded is not None and loaded.source == ap.source)


def test_active_profile_deterministic_id() -> None:
    """Same inputs produce same binding ID."""
    print("\n── Test 8: ActiveProfile deterministic ID ──")
    id1 = compute_active_profile_id(_SESSION_ID, _FIXED_TS)
    id2 = compute_active_profile_id(_SESSION_ID, _FIXED_TS)
    _report("deterministic ID", id1 == id2)
    _report("starts with apb_", id1.startswith("apb_"))

    # Different inputs → different ID
    id3 = compute_active_profile_id("sess_other", _FIXED_TS)
    _report("different session → different ID", id1 != id3)


# ===========================================================================
# 3. Open Day Execution Tests
# ===========================================================================


def test_open_day_basic() -> None:
    """Basic open-day execution produces correct mutations and events."""
    print("\n── Test 9: Open day — basic execution ──")
    state, pid = _build_test_profile()

    request = build_open_day_request(
        runtime_session_id=_SESSION_ID,
        entry_transport="discord",
        requested_profile_id=pid,
        requested_at=_FIXED_TS,
        correlation_id="cor_001",
    )

    mutations, events, result = execute_open_day(state, request, timestamp=_FIXED_TS)

    _report("mutations produced", len(mutations) > 0)
    _report("events produced", len(events) > 0)
    _report("all ops are SET", all(m["op"] == "SET" for m in mutations))
    _report("plan_id set", bool(result.plan_id))
    _report("profile resolved", result.profile_id == pid)
    _report("artifact created", bool(result.artifact_id))
    _report("correlation preserved", result.correlation_id == "cor_001")
    _report(
        "steps match canonical",
        result.steps_executed == CANONICAL_OPEN_STEPS,
    )


def test_open_day_presence_discord() -> None:
    """Open-day via discord → remote_light presence."""
    print("\n── Test 10: Open day — discord → remote_light ──")
    state, pid = _build_test_profile(
        mode="active",
        presence="",  # no presence in profile
    )

    request = build_open_day_request(
        runtime_session_id=_SESSION_ID,
        entry_transport="discord",
        requested_profile_id=pid,
        requested_at=_FIXED_TS,
    )

    _, _, result = execute_open_day(state, request, timestamp=_FIXED_TS)
    _report(
        "presence is remote_light",
        result.presence_after == PRESENCE_REMOTE_LIGHT,
    )


def test_open_day_presence_local() -> None:
    """Open-day via local terminal → active_station presence."""
    print("\n── Test 11: Open day — local → active_station ──")
    state, pid = _build_test_profile(mode="active", presence="")

    request = build_open_day_request(
        runtime_session_id=_SESSION_ID,
        entry_transport="local_terminal",
        requested_profile_id=pid,
        requested_at=_FIXED_TS,
    )

    _, _, result = execute_open_day(state, request, timestamp=_FIXED_TS)
    _report(
        "presence is active_station",
        result.presence_after == PRESENCE_ACTIVE_STATION,
    )


def test_open_day_presence_override() -> None:
    """Explicit presence in request overrides transport inference."""
    print("\n── Test 12: Open day — presence override ──")
    state, pid = _build_test_profile(mode="active", presence="deep_work")

    request = build_open_day_request(
        runtime_session_id=_SESSION_ID,
        entry_transport="discord",
        requested_profile_id=pid,
        requested_at=_FIXED_TS,
    )

    _, _, result = execute_open_day(state, request, timestamp=_FIXED_TS)
    _report(
        "presence from profile (deep_work)",
        result.presence_after == "deep_work",
    )


def test_open_day_mode_from_profile() -> None:
    """Mode resolves from profile when not in request."""
    print("\n── Test 13: Open day — mode from profile ──")
    state, pid = _build_test_profile(mode="focused")

    request = build_open_day_request(
        runtime_session_id=_SESSION_ID,
        entry_transport="local",
        requested_profile_id=pid,
        requested_at=_FIXED_TS,
    )

    _, _, result = execute_open_day(state, request, timestamp=_FIXED_TS)
    _report("mode is focused", result.mode_after == "focused")


def test_open_day_no_profile() -> None:
    """Open-day with no profiles still executes (profile_id empty)."""
    print("\n── Test 14: Open day — no profile ──")
    state: dict = {}

    request = build_open_day_request(
        runtime_session_id=_SESSION_ID,
        entry_transport="discord",
        requested_at=_FIXED_TS,
    )

    mutations, events, result = execute_open_day(state, request, timestamp=_FIXED_TS)
    _report("still executes", len(mutations) > 0)
    _report("profile_id empty", result.profile_id == "")
    _report("steps still canonical", result.steps_executed == CANONICAL_OPEN_STEPS)


def test_open_day_event_order() -> None:
    """Events are emitted in correct order: started, steps, completed."""
    print("\n── Test 15: Open day — event emission order ──")
    state, pid = _build_test_profile()

    request = build_open_day_request(
        runtime_session_id=_SESSION_ID,
        entry_transport="local",
        requested_profile_id=pid,
        requested_at=_FIXED_TS,
    )

    _, events, _ = execute_open_day(state, request, timestamp=_FIXED_TS)

    _report(
        "first event is open_day_started", events[0].event_type == "open_day_started"
    )

    step_events = [e for e in events if e.event_type == "ritual_step_executed"]
    _report(
        f"step events count matches ({len(step_events)})",
        len(step_events) == len(CANONICAL_OPEN_STEPS),
    )

    step_names = [e.payload["step_name"] for e in step_events]
    _report(
        "step names match canonical order",
        tuple(step_names) == CANONICAL_OPEN_STEPS,
    )

    step_indices = [e.payload["step_index"] for e in step_events]
    _report(
        "step indices sequential",
        step_indices == list(range(len(CANONICAL_OPEN_STEPS))),
    )

    _report(
        "last event is ritual_completed", events[-1].event_type == "ritual_completed"
    )


# ===========================================================================
# 4. Close Day Execution Tests
# ===========================================================================


def test_close_day_basic() -> None:
    """Basic close-day execution produces correct mutations and events."""
    print("\n── Test 16: Close day — basic execution ──")
    state: dict = {}

    request = build_close_day_request(
        runtime_session_id=_SESSION_ID,
        requested_mode_after_close="passive",
        requested_at=_FIXED_TS,
        correlation_id="cor_002",
    )

    mutations, events, result = execute_close_day(state, request, timestamp=_FIXED_TS)

    _report("mutations produced", len(mutations) > 0)
    _report("events produced", len(events) > 0)
    _report("all ops are SET", all(m["op"] == "SET" for m in mutations))
    _report("plan_id set", bool(result.plan_id))
    _report("artifact created", bool(result.artifact_id))
    _report("correlation preserved", result.correlation_id == "cor_002")
    _report("mode_after is passive", result.mode_after == "passive")
    _report(
        "steps match canonical",
        result.steps_executed == CANONICAL_CLOSE_STEPS,
    )


def test_close_day_overnight() -> None:
    """Close-day with overnight mode → overnight_autonomous presence."""
    print("\n── Test 17: Close day — overnight → overnight_autonomous ──")
    state: dict = {}

    request = build_close_day_request(
        runtime_session_id=_SESSION_ID,
        requested_mode_after_close="overnight_autonomous",
        requested_at=_FIXED_TS,
    )

    _, _, result = execute_close_day(state, request, timestamp=_FIXED_TS)
    _report(
        "presence is overnight_autonomous",
        result.presence_after == PRESENCE_OVERNIGHT_AUTONOMOUS,
    )
    _report("mode is overnight_autonomous", result.mode_after == "overnight_autonomous")


def test_close_day_passive() -> None:
    """Close-day with passive mode → off presence."""
    print("\n── Test 18: Close day — passive → off ──")
    state: dict = {}

    request = build_close_day_request(
        runtime_session_id=_SESSION_ID,
        requested_mode_after_close="passive",
        requested_at=_FIXED_TS,
    )

    _, _, result = execute_close_day(state, request, timestamp=_FIXED_TS)
    _report("presence is off", result.presence_after == PRESENCE_OFF)


def test_close_day_event_order() -> None:
    """Events emitted in order: started, steps, completed."""
    print("\n── Test 19: Close day — event emission order ──")
    state: dict = {}

    request = build_close_day_request(
        runtime_session_id=_SESSION_ID,
        requested_mode_after_close="passive",
        requested_at=_FIXED_TS,
    )

    _, events, _ = execute_close_day(state, request, timestamp=_FIXED_TS)

    _report(
        "first event is close_day_started", events[0].event_type == "close_day_started"
    )

    step_events = [e for e in events if e.event_type == "ritual_step_executed"]
    _report(
        f"step events count matches ({len(step_events)})",
        len(step_events) == len(CANONICAL_CLOSE_STEPS),
    )

    step_names = [e.payload["step_name"] for e in step_events]
    _report(
        "step names match canonical order",
        tuple(step_names) == CANONICAL_CLOSE_STEPS,
    )

    _report(
        "last event is ritual_completed", events[-1].event_type == "ritual_completed"
    )


# ===========================================================================
# 5. Determinism / Replay Tests
# ===========================================================================


def test_replay_idempotency_open() -> None:
    """Same inputs → deterministic non-plan fields for open-day.

    Note: plan_id includes created_at which uses _utcnow() inside
    build_open_day_plan — this is intentional (each plan is unique).
    Replay safety means same request + same timestamp → same result
    for everything the driver controls (presence, mode, profile, steps).
    """
    print("\n── Test 20: Replay idempotency — open day ──")
    state, pid = _build_test_profile()

    request = build_open_day_request(
        runtime_session_id=_SESSION_ID,
        entry_transport="discord",
        requested_profile_id=pid,
        requested_at=_FIXED_TS,
        correlation_id="cor_replay",
    )

    _, _, r1 = execute_open_day(state, request, timestamp=_FIXED_TS)
    _, _, r2 = execute_open_day(state, request, timestamp=_FIXED_TS)

    _report("same presence", r1.presence_after == r2.presence_after)
    _report("same mode", r1.mode_after == r2.mode_after)
    _report("same profile", r1.profile_id == r2.profile_id)
    _report("same steps", r1.steps_executed == r2.steps_executed)
    _report("same artifact_id", r1.artifact_id == r2.artifact_id)
    _report("both have plan_ids", bool(r1.plan_id) and bool(r2.plan_id))


def test_replay_idempotency_close() -> None:
    """Same inputs → deterministic non-plan fields for close-day."""
    print("\n── Test 21: Replay idempotency — close day ──")
    state: dict = {}

    request = build_close_day_request(
        runtime_session_id=_SESSION_ID,
        requested_mode_after_close="overnight_autonomous",
        requested_at=_FIXED_TS,
        correlation_id="cor_replay_close",
    )

    _, _, r1 = execute_close_day(state, request, timestamp=_FIXED_TS)
    _, _, r2 = execute_close_day(state, request, timestamp=_FIXED_TS)

    _report("same presence", r1.presence_after == r2.presence_after)
    _report("same mode", r1.mode_after == r2.mode_after)
    _report("same artifact_id", r1.artifact_id == r2.artifact_id)
    _report("same steps", r1.steps_executed == r2.steps_executed)
    _report("both have plan_ids", bool(r1.plan_id) and bool(r2.plan_id))


# ===========================================================================
# 6. Mutation Structure Tests
# ===========================================================================


def test_mutation_structure() -> None:
    """All mutations are well-formed SET operations with valid keys."""
    print("\n── Test 22: Mutation structure validation ──")
    state, pid = _build_test_profile()

    request = build_open_day_request(
        runtime_session_id=_SESSION_ID,
        entry_transport="local",
        requested_profile_id=pid,
        requested_at=_FIXED_TS,
    )

    mutations, _, _ = execute_open_day(state, request, timestamp=_FIXED_TS)

    for i, m in enumerate(mutations):
        _report(f"mutation[{i}] has op", "op" in m)
        _report(f"mutation[{i}] op is SET", m.get("op") == "SET")
        _report(f"mutation[{i}] has key", "key" in m and isinstance(m["key"], str))
        _report(f"mutation[{i}] has value", "value" in m)


# ===========================================================================
# 7. No Adapter Import Test
# ===========================================================================


def test_no_adapter_imports() -> None:
    """Neither module imports adapter/product-layer code."""
    print("\n── Test 23: No adapter imports ──")
    import importlib

    forbidden = [
        "discord",
        "notion",
        "telegram",
        "flask",
        "fastapi",
        "obs",
    ]

    for mod_name in [
        "umh.substrate.profile_resolution",
        "umh.substrate.ritual_execution_driver",
    ]:
        mod = importlib.import_module(mod_name)
        source_file = mod.__file__ or ""
        if source_file:
            with open(source_file, "r") as f:
                source = f.read()
            for fb in forbidden:
                found = f"import {fb}" in source or f"from {fb}" in source
                _report(
                    f"{mod_name} does not import {fb}",
                    not found,
                    detail=f"found 'import {fb}'" if found else "",
                )


# ===========================================================================
# 8. Event Builder Standalone Tests
# ===========================================================================


def test_event_builders() -> None:
    """Event builders produce correctly-typed SchedulerEvents."""
    print("\n── Test 24: Event builder contracts ──")
    from umh.substrate.daily_rituals import build_open_day_plan

    state, pid = _build_test_profile()
    request = build_open_day_request(
        runtime_session_id=_SESSION_ID,
        entry_transport="local",
        requested_profile_id=pid,
        requested_at=_FIXED_TS,
    )
    plan = build_open_day_plan(state, request)

    evt = build_open_day_started_event(plan, _SESSION_ID, correlation_id="cor_evt")
    _report("event_type is open_day_started", evt.event_type == "open_day_started")
    _report(
        "source is ritual_execution_driver", evt.source == "ritual_execution_driver"
    )
    _report("has plan in payload", "plan" in evt.payload)

    step_evt = build_ritual_step_event(
        plan_id=plan.plan_id,
        step_name="load_presence_state",
        step_index=2,
        session_name=_SESSION_ID,
        ritual_kind="open_day",
    )
    _report("step event type correct", step_evt.event_type == "ritual_step_executed")
    _report(
        "step_name in payload",
        step_evt.payload.get("step_name") == "load_presence_state",
    )
    _report("step_index in payload", step_evt.payload.get("step_index") == 2)

    result = RitualExecutionResult(
        runtime_session_id=_SESSION_ID,
        plan_id=plan.plan_id,
        steps_executed=CANONICAL_OPEN_STEPS,
        presence_after="active_station",
        mode_after="active",
        profile_id=pid,
        artifact_id="hda_test123",
        correlation_id="cor_evt",
    )
    comp_evt = build_ritual_completed_event(result, _SESSION_ID, ritual_kind="open_day")
    _report("completed event type correct", comp_evt.event_type == "ritual_completed")
    _report("result in payload", "result" in comp_evt.payload)


# ===========================================================================
# Runner
# ===========================================================================


def main() -> None:
    print("=" * 60)
    print("RITUAL EXECUTION + PROFILE RESOLUTION — Smoke Tests")
    print("=" * 60)

    # Profile resolution
    test_profile_resolution_explicit()
    test_profile_resolution_binding()
    test_profile_resolution_singleton()
    test_profile_resolution_none()
    test_profile_resolution_ambiguous()
    test_profile_resolution_missing_explicit()

    # Active profile persistence
    test_active_profile_persistence()
    test_active_profile_deterministic_id()

    # Open day execution
    test_open_day_basic()
    test_open_day_presence_discord()
    test_open_day_presence_local()
    test_open_day_presence_override()
    test_open_day_mode_from_profile()
    test_open_day_no_profile()
    test_open_day_event_order()

    # Close day execution
    test_close_day_basic()
    test_close_day_overnight()
    test_close_day_passive()
    test_close_day_event_order()

    # Replay idempotency
    test_replay_idempotency_open()
    test_replay_idempotency_close()

    # Mutation structure
    test_mutation_structure()

    # No adapter imports
    test_no_adapter_imports()

    # Event builders
    test_event_builders()

    print("\n" + "=" * 60)
    print(f"Results: {_PASS} passed, {_FAIL} failed")
    if _FAIL == 0:
        print("All smoke tests passed.")
    else:
        print(f"FAILURES: {_FAIL}")
    print("=" * 60)

    sys.exit(1 if _FAIL > 0 else 0)


if __name__ == "__main__":
    main()
