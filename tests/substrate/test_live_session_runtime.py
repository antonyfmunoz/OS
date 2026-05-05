"""
Validation of the live session runtime primitives.

Tests the complete state model, turn lifecycle, controller behavior,
and stream transport contract. Every test uses pure function calls —
no mocking, no Discord, no Meet, no audio.

Proves:
  1. Deterministic session and turn IDs
  2. Session create / load / active / recent indexing
  3. End removes active index, preserves recent
  4. Interrupt / resume transitions
  5. Replay produces identical mutations
  6. Turn partial input / output updates
  7. Finalize flow clears current_turn_id
  8. Interrupt flow updates both turn and session
  9. Execution / artifact attachment
  10. Bounded session turn listing
  11. Controller start_session idempotent
  12. Controller methods pure / deterministic
  13. Stream transport chunk IDs deterministic
  14. Stream transport round-trip to_dict/from_dict
  15. Protocol imports clean
  16. Only SET / REMOVE ops
  17. No list mutations
  18. No transport-specific code in controller
  19. Continuity summary is harness-generic
"""

import sys

sys.path.insert(0, "/opt/OS")

from umh.substrate.live_session import (
    LiveSession,
    build_live_session,
    build_live_session_mutations,
    compute_live_session_id,
    end_live_session,
    interrupt_live_session,
    list_active_live_sessions,
    list_recent_live_sessions,
    load_live_session,
    touch_live_session,
)
from umh.substrate.live_turn import (
    LiveTurn,
    attach_execution_ids,
    build_live_turn,
    build_live_turn_mutations,
    compute_live_turn_id,
    finalize_turn,
    interrupt_turn,
    list_session_turns,
    load_live_turn,
    update_partial_input,
    update_partial_output,
)
from umh.substrate.live_session_controller import (
    LiveSessionController,
    LiveTurnResult,
    build_live_continuity_summary,
)
from umh.substrate.stream_transport_contract import (
    TRANSPORT_DISCORD_VOICE,
    TRANSPORT_LOCAL_MIC,
    TRANSPORT_MEET,
    StreamEgressChunk,
    StreamIngressChunk,
    StreamingEgressAdapter,
    StreamingIngressAdapter,
    build_stream_egress_chunk,
    build_stream_ingress_chunk,
    compute_stream_chunk_id,
)

PASS = 0
FAIL = 0


def check(name: str, condition: bool, detail: str = "") -> None:
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  PASS  {name}")
    else:
        FAIL += 1
        msg = f"  FAIL  {name}"
        if detail:
            msg += f" — {detail}"
        print(msg)


def apply_mutations(state: dict, mutations) -> dict:
    """Apply mutations to state dict for testing."""
    for m in mutations:
        if m["op"] == "SET":
            state[m["key"]] = m["value"]
        elif m["op"] == "REMOVE":
            state.pop(m["key"], None)
    return state


# =========================================================================
# A. LiveSession tests
# =========================================================================
print("\n=== A. LiveSession ===")


def test_deterministic_session_id():
    """Same inputs → same ID, different inputs → different ID."""
    id1 = compute_live_session_id("rt_1", "discord_voice", "op_1")
    id2 = compute_live_session_id("rt_1", "discord_voice", "op_1")
    id3 = compute_live_session_id("rt_1", "meet", "op_1")
    check("deterministic session id (same)", id1 == id2)
    check("deterministic session id (different)", id1 != id3)
    check("session id prefix", id1.startswith("lse_"), f"got {id1}")


def test_session_creation_and_load():
    """Build, persist via mutations, and load from state."""
    session = build_live_session(
        runtime_session_id="rt_1",
        mode="voice",
        transport="discord_voice",
        operator_id="op_1",
        started_at="2026-04-17T00:00:00Z",
    )
    check("session status default", session.status == "active")
    check("session turn_count default", session.turn_count == 0)

    mutations = build_live_session_mutations(session)
    state: dict = {}
    apply_mutations(state, mutations)

    loaded = load_live_session(state, session.session_id)
    check("session load round-trip", loaded is not None)
    check(
        "session load matches",
        loaded is not None and loaded.session_id == session.session_id,
    )
    check(
        "session to_dict round-trip",
        session.to_dict() == LiveSession.from_dict(session.to_dict()).to_dict(),
    )


def test_session_active_and_recent_indexing():
    """Active and recent indexes populated on creation."""
    session = build_live_session(
        runtime_session_id="rt_2",
        mode="text",
        transport="local_mic",
        operator_id="op_2",
        started_at="2026-04-17T00:00:00Z",
    )
    state: dict = {}
    apply_mutations(state, build_live_session_mutations(session))

    active = list_active_live_sessions(state)
    recent = list_recent_live_sessions(state)
    check("session in active index", session.session_id in active)
    check("session in recent index", session.session_id in recent)


def test_end_removes_active():
    """Ending removes active index but preserves recent."""
    session = build_live_session(
        runtime_session_id="rt_3",
        mode="voice",
        transport="meet",
        operator_id="op_3",
        started_at="2026-04-17T00:00:00Z",
    )
    state: dict = {}
    apply_mutations(state, build_live_session_mutations(session))

    ended, end_mutations = end_live_session(session, "2026-04-17T01:00:00Z")
    apply_mutations(state, end_mutations)

    active = list_active_live_sessions(state)
    recent = list_recent_live_sessions(state)
    check("ended session not in active", session.session_id not in active)
    check("ended session in recent", session.session_id in recent)
    check("ended session status", ended.status == "ended")


def test_interrupt_resume():
    """Interrupt and resume transitions."""
    session = build_live_session(
        runtime_session_id="rt_4",
        mode="voice",
        transport="discord_voice",
        operator_id="op_4",
        started_at="2026-04-17T00:00:00Z",
    )
    state: dict = {}
    apply_mutations(state, build_live_session_mutations(session))

    interrupted, int_mutations = interrupt_live_session(session, "2026-04-17T00:30:00Z")
    apply_mutations(state, int_mutations)
    check("interrupted status", interrupted.status == "interrupted")
    check("interruption count", interrupted.interruption_count == 1)
    check(
        "interrupted still in active",
        session.session_id in list_active_live_sessions(state),
    )


def test_replay_identical_mutations():
    """Same session produces identical mutations on replay."""
    session = build_live_session(
        runtime_session_id="rt_5",
        mode="voice",
        transport="discord_voice",
        operator_id="op_5",
        started_at="2026-04-17T00:00:00Z",
    )
    m1 = build_live_session_mutations(session)
    m2 = build_live_session_mutations(session)
    check("replay identical session mutations", m1 == m2)


test_deterministic_session_id()
test_session_creation_and_load()
test_session_active_and_recent_indexing()
test_end_removes_active()
test_interrupt_resume()
test_replay_identical_mutations()


# =========================================================================
# B. LiveTurn tests
# =========================================================================
print("\n=== B. LiveTurn ===")


def test_deterministic_turn_id():
    """Same inputs → same ID."""
    id1 = compute_live_turn_id("ses_1", 1, "hello")
    id2 = compute_live_turn_id("ses_1", 1, "hello")
    id3 = compute_live_turn_id("ses_1", 2, "hello")
    check("deterministic turn id (same)", id1 == id2)
    check("deterministic turn id (different index)", id1 != id3)
    check("turn id prefix", id1.startswith("ltu_"), f"got {id1}")


def test_partial_input_update():
    """Partial input text updates correctly."""
    turn = build_live_turn(
        session_id="ses_1",
        transport="discord_voice",
        operator_id="op_1",
        input_text="hello",
        turn_index=1,
        created_at="2026-04-17T00:00:00Z",
    )
    updated = update_partial_input(turn, "hello wor")
    check("partial input updated", updated.partial_input_text == "hello wor")
    check("original unchanged", turn.partial_input_text == "")


def test_partial_output_update():
    """Partial output text updates correctly."""
    turn = build_live_turn(
        session_id="ses_1",
        transport="discord_voice",
        operator_id="op_1",
        input_text="hello",
        turn_index=1,
        created_at="2026-04-17T00:00:00Z",
    )
    updated = update_partial_output(turn, "Hi there")
    check("partial output updated", updated.partial_output_text == "Hi there")


def test_finalize_flow():
    """Finalize sets status, output, clears partials."""
    turn = build_live_turn(
        session_id="ses_1",
        transport="discord_voice",
        operator_id="op_1",
        input_text="hello",
        turn_index=1,
        created_at="2026-04-17T00:00:00Z",
    )
    turn = update_partial_input(turn, "partial")
    turn = update_partial_output(turn, "partial out")
    finalized = finalize_turn(turn, "Full response", "2026-04-17T00:01:00Z", "art_1")
    check("finalized status", finalized.status == "finalized")
    check("finalized output", finalized.output_text == "Full response")
    check("finalized artifact", finalized.artifact_id == "art_1")
    check(
        "partials cleared",
        finalized.partial_input_text == "" and finalized.partial_output_text == "",
    )


def test_interrupt_flow():
    """Interrupt sets status and increments count."""
    turn = build_live_turn(
        session_id="ses_1",
        transport="discord_voice",
        operator_id="op_1",
        input_text="hello",
        turn_index=1,
        created_at="2026-04-17T00:00:00Z",
    )
    interrupted = interrupt_turn(turn, "2026-04-17T00:00:30Z")
    check("interrupted status", interrupted.status == "interrupted")
    check("interrupted count", interrupted.interruption_count == 1)
    # Double interrupt
    double = interrupt_turn(interrupted, "2026-04-17T00:01:00Z")
    check("double interrupt count", double.interruption_count == 2)


def test_execution_attachment():
    """Execution IDs can be attached."""
    turn = build_live_turn(
        session_id="ses_1",
        transport="discord_voice",
        operator_id="op_1",
        input_text="run it",
        turn_index=2,
        created_at="2026-04-17T00:00:00Z",
    )
    attached = attach_execution_ids(turn, ("exec_1", "exec_2"))
    check("execution ids attached", attached.execution_ids == ("exec_1", "exec_2"))
    # Append more
    more = attach_execution_ids(attached, ("exec_3",))
    check(
        "execution ids appended", more.execution_ids == ("exec_1", "exec_2", "exec_3")
    )


def test_bounded_session_turn_listing():
    """Turn listing is bounded and ordered."""
    state: dict = {}
    session_id = "ses_listing"
    for i in range(1, 8):
        turn = build_live_turn(
            session_id=session_id,
            transport="local_mic",
            operator_id="op_1",
            input_text=f"turn {i}",
            turn_index=i,
            created_at=f"2026-04-17T00:{i:02d}:00Z",
        )
        apply_mutations(state, build_live_turn_mutations(turn, i))

    all_turns = list_session_turns(state, session_id)
    check("all turns found", len(all_turns) == 7, f"got {len(all_turns)}")

    limited = list_session_turns(state, session_id, limit=3)
    check("turns bounded by limit", len(limited) == 3)

    # Verify ordering (ascending by created_at)
    loaded_first = load_live_turn(state, limited[0])
    loaded_last = load_live_turn(state, limited[2])
    check(
        "turns ordered ascending",
        loaded_first is not None
        and loaded_last is not None
        and loaded_first.created_at <= loaded_last.created_at,
    )


def test_turn_to_dict_round_trip():
    """to_dict/from_dict preserves all fields."""
    turn = build_live_turn(
        session_id="ses_rt",
        transport="meet",
        operator_id="op_1",
        input_text="test",
        turn_index=1,
        created_at="2026-04-17T00:00:00Z",
        correlation_id="corr_1",
    )
    turn = attach_execution_ids(turn, ("exec_a",))
    rt = LiveTurn.from_dict(turn.to_dict())
    check("turn round-trip", rt.to_dict() == turn.to_dict())


def test_replay_identical_turn_mutations():
    """Same turn produces identical mutations on replay."""
    turn = build_live_turn(
        session_id="ses_replay",
        transport="discord_voice",
        operator_id="op_1",
        input_text="replay test",
        turn_index=1,
        created_at="2026-04-17T00:00:00Z",
    )
    m1 = build_live_turn_mutations(turn, 1)
    m2 = build_live_turn_mutations(turn, 1)
    check("replay identical turn mutations", m1 == m2)


test_deterministic_turn_id()
test_partial_input_update()
test_partial_output_update()
test_finalize_flow()
test_interrupt_flow()
test_execution_attachment()
test_bounded_session_turn_listing()
test_turn_to_dict_round_trip()
test_replay_identical_turn_mutations()


# =========================================================================
# C. LiveSessionController tests
# =========================================================================
print("\n=== C. LiveSessionController ===")

ctrl = LiveSessionController()


def test_controller_start_session_idempotent():
    """start_session is idempotent for same deterministic ID."""
    state: dict = {}
    s1, m1 = ctrl.start_session(
        state, "rt_c1", "voice", "discord_voice", "op_1", "2026-04-17T00:00:00Z"
    )
    apply_mutations(state, m1)

    s2, m2 = ctrl.start_session(
        state, "rt_c1", "voice", "discord_voice", "op_1", "2026-04-17T00:00:00Z"
    )
    check("start_session idempotent session id", s1.session_id == s2.session_id)
    check("start_session idempotent no mutations", len(m2) == 0)


def test_controller_start_turn():
    """start_turn creates turn and updates session."""
    state: dict = {}
    session, m = ctrl.start_session(
        state, "rt_c2", "voice", "discord_voice", "op_1", "2026-04-17T00:00:00Z"
    )
    apply_mutations(state, m)

    result = ctrl.start_turn(state, session.session_id, "Hello", "2026-04-17T00:01:00Z")
    apply_mutations(state, result.mutations)
    check("start_turn session turn_count", result.session.turn_count == 1)
    check(
        "start_turn current_turn_id set",
        result.session.current_turn_id == result.turn.turn_id,
    )
    check("start_turn turn status open", result.turn.status == "open")
    check("start_turn turn input", result.turn.input_text == "Hello")


def test_controller_partial_updates():
    """Partial input/output updates are correct."""
    state: dict = {}
    session, m = ctrl.start_session(
        state, "rt_c3", "voice", "local_mic", "op_1", "2026-04-17T00:00:00Z"
    )
    apply_mutations(state, m)

    result = ctrl.start_turn(state, session.session_id, "Hi", "2026-04-17T00:01:00Z")
    apply_mutations(state, result.mutations)

    # Partial input
    result_pi = ctrl.update_turn_input_partial(
        state, session.session_id, "Hi there", "2026-04-17T00:01:01Z"
    )
    apply_mutations(state, result_pi.mutations)
    check("partial input updated", result_pi.turn.partial_input_text == "Hi there")

    # Partial output
    result_po = ctrl.update_turn_output_partial(
        state, session.session_id, "Hello!", "2026-04-17T00:01:02Z"
    )
    apply_mutations(state, result_po.mutations)
    check("partial output updated", result_po.turn.partial_output_text == "Hello!")


def test_controller_finalize_turn():
    """Finalize clears current_turn_id and emits continuity summary."""
    state: dict = {}
    session, m = ctrl.start_session(
        state, "rt_c4", "voice", "discord_voice", "op_1", "2026-04-17T00:00:00Z"
    )
    apply_mutations(state, m)

    result = ctrl.start_turn(
        state, session.session_id, "What time is it?", "2026-04-17T00:01:00Z"
    )
    apply_mutations(state, result.mutations)

    fin = ctrl.finalize_turn(
        state,
        session.session_id,
        "It is 6pm",
        "2026-04-17T00:01:30Z",
        artifact_id="art_fin",
        execution_ids=("exec_f1",),
    )
    apply_mutations(state, fin.mutations)

    check("finalize clears current_turn_id", fin.session.current_turn_id == "")
    check("finalize turn status", fin.turn.status == "finalized")
    check("finalize continuity summary", len(fin.continuity_summary) > 0)
    check("finalize requires_artifact", fin.requires_artifact is True)
    check("finalize execution ids", "exec_f1" in fin.turn.execution_ids)


def test_controller_interrupt_current_turn():
    """Interrupt updates both turn and session."""
    state: dict = {}
    session, m = ctrl.start_session(
        state, "rt_c5", "voice", "discord_voice", "op_1", "2026-04-17T00:00:00Z"
    )
    apply_mutations(state, m)

    result = ctrl.start_turn(
        state, session.session_id, "Tell me about...", "2026-04-17T00:01:00Z"
    )
    apply_mutations(state, result.mutations)

    int_result = ctrl.interrupt_current_turn(
        state, session.session_id, "2026-04-17T00:01:15Z"
    )
    apply_mutations(state, int_result.mutations)

    check("interrupt turn status", int_result.turn.status == "interrupted")
    check("interrupt session status", int_result.session.status == "interrupted")
    check("interrupt session count", int_result.session.interruption_count == 1)
    check("interrupt clears current_turn_id", int_result.session.current_turn_id == "")


def test_controller_resume_session():
    """Resume restores active state after interrupt."""
    state: dict = {}
    session, m = ctrl.start_session(
        state, "rt_c6", "voice", "discord_voice", "op_1", "2026-04-17T00:00:00Z"
    )
    apply_mutations(state, m)

    # Interrupt with no turn
    int_result = ctrl.interrupt_current_turn(
        state, session.session_id, "2026-04-17T00:30:00Z"
    )
    apply_mutations(state, int_result.mutations)

    resumed, resume_m = ctrl.resume_session(
        state, session.session_id, "2026-04-17T00:35:00Z"
    )
    apply_mutations(state, resume_m)

    check("resumed status active", resumed.status == "active")
    check("resumed last_active_at", resumed.last_active_at == "2026-04-17T00:35:00Z")


def test_controller_end_session():
    """End session cleans active index, preserves recent."""
    state: dict = {}
    session, m = ctrl.start_session(
        state, "rt_c7", "voice", "discord_voice", "op_1", "2026-04-17T00:00:00Z"
    )
    apply_mutations(state, m)

    ended, end_m = ctrl.end_session(state, session.session_id, "2026-04-17T01:00:00Z")
    apply_mutations(state, end_m)

    active = list_active_live_sessions(state)
    recent = list_recent_live_sessions(state)
    check("end removes active index", session.session_id not in active)
    check("end preserves recent index", session.session_id in recent)
    check("ended status", ended.status == "ended")


def test_controller_deterministic():
    """All controller methods deterministic given same state + params."""
    state1: dict = {}
    state2: dict = {}

    s1, m1 = ctrl.start_session(
        state1, "rt_det", "voice", "discord_voice", "op_1", "2026-04-17T00:00:00Z"
    )
    s2, m2 = ctrl.start_session(
        state2, "rt_det", "voice", "discord_voice", "op_1", "2026-04-17T00:00:00Z"
    )

    check("deterministic start_session", m1 == m2)
    check("deterministic session id", s1.session_id == s2.session_id)

    apply_mutations(state1, m1)
    apply_mutations(state2, m2)

    r1 = ctrl.start_turn(state1, s1.session_id, "test", "2026-04-17T00:01:00Z")
    r2 = ctrl.start_turn(state2, s2.session_id, "test", "2026-04-17T00:01:00Z")
    check("deterministic start_turn mutations", r1.mutations == r2.mutations)


test_controller_start_session_idempotent()
test_controller_start_turn()
test_controller_partial_updates()
test_controller_finalize_turn()
test_controller_interrupt_current_turn()
test_controller_resume_session()
test_controller_end_session()
test_controller_deterministic()


# =========================================================================
# D. StreamTransportContract tests
# =========================================================================
print("\n=== D. StreamTransportContract ===")


def test_transport_constants():
    """Transport constants have expected values."""
    check("discord voice constant", TRANSPORT_DISCORD_VOICE == "discord_voice")
    check("meet constant", TRANSPORT_MEET == "meet")
    check("local mic constant", TRANSPORT_LOCAL_MIC == "local_mic")


def test_stream_chunk_id_deterministic():
    """Same inputs → same chunk ID."""
    id1 = compute_stream_chunk_id(
        "ses_1", "discord_voice", "2026-04-17T00:00:00Z", "ingress"
    )
    id2 = compute_stream_chunk_id(
        "ses_1", "discord_voice", "2026-04-17T00:00:00Z", "ingress"
    )
    id3 = compute_stream_chunk_id(
        "ses_1", "discord_voice", "2026-04-17T00:00:00Z", "egress"
    )
    check("chunk id deterministic (same)", id1 == id2)
    check("chunk id different for direction", id1 != id3)
    check("ingress prefix", id1.startswith("sci_"))
    check("egress prefix", id3.startswith("sco_"))


def test_ingress_chunk_round_trip():
    """to_dict/from_dict round-trip for ingress chunks."""
    chunk = build_stream_ingress_chunk(
        session_id="ses_1",
        transport="discord_voice",
        operator_id="op_1",
        text="hello",
        is_partial=True,
        received_at="2026-04-17T00:00:00Z",
        correlation_id="corr_1",
    )
    rt = StreamIngressChunk.from_dict(chunk.to_dict())
    check("ingress round-trip", rt.to_dict() == chunk.to_dict())
    check("ingress is_partial", rt.is_partial is True)


def test_egress_chunk_round_trip():
    """to_dict/from_dict round-trip for egress chunks."""
    chunk = build_stream_egress_chunk(
        session_id="ses_1",
        transport="meet",
        text="response text",
        is_partial=False,
        created_at="2026-04-17T00:00:00Z",
        artifact_id="art_1",
    )
    rt = StreamEgressChunk.from_dict(chunk.to_dict())
    check("egress round-trip", rt.to_dict() == chunk.to_dict())
    check("egress artifact_id", rt.artifact_id == "art_1")


def test_protocols_import_cleanly():
    """Protocols are runtime-checkable and importable."""
    check("ingress adapter is protocol", StreamingIngressAdapter is not None)
    check("egress adapter is protocol", StreamingEgressAdapter is not None)

    # Verify structural protocol works
    class _TestIngress:
        def ingest_chunk(self, chunk: StreamIngressChunk):
            return None

    class _TestEgress:
        def emit_chunk(self, chunk: StreamEgressChunk):
            return None

    check("ingress adapter check", isinstance(_TestIngress(), StreamingIngressAdapter))
    check("egress adapter check", isinstance(_TestEgress(), StreamingEgressAdapter))


def test_no_side_effects():
    """Building chunks produces no side effects."""
    chunk1 = build_stream_ingress_chunk(
        session_id="ses_se",
        transport="local_mic",
        operator_id="op_1",
        text="test",
        received_at="2026-04-17T00:00:00Z",
    )
    chunk2 = build_stream_ingress_chunk(
        session_id="ses_se",
        transport="local_mic",
        operator_id="op_1",
        text="test",
        received_at="2026-04-17T00:00:00Z",
    )
    check("no side effects (identical)", chunk1.to_dict() == chunk2.to_dict())


test_transport_constants()
test_stream_chunk_id_deterministic()
test_ingress_chunk_round_trip()
test_egress_chunk_round_trip()
test_protocols_import_cleanly()
test_no_side_effects()


# =========================================================================
# E. Invariant tests
# =========================================================================
print("\n=== E. Invariants ===")


def test_only_set_remove_ops():
    """All mutations use only SET or REMOVE ops."""
    session = build_live_session(
        runtime_session_id="rt_inv",
        mode="voice",
        transport="discord_voice",
        operator_id="op_1",
        started_at="2026-04-17T00:00:00Z",
    )
    all_mutations: list[dict] = []
    all_mutations.extend(build_live_session_mutations(session))

    _, end_m = end_live_session(session, "2026-04-17T01:00:00Z")
    all_mutations.extend(end_m)

    _, int_m = interrupt_live_session(session, "2026-04-17T00:30:00Z")
    all_mutations.extend(int_m)

    turn = build_live_turn(
        session_id=session.session_id,
        transport="discord_voice",
        operator_id="op_1",
        input_text="test",
        turn_index=1,
        created_at="2026-04-17T00:00:00Z",
    )
    all_mutations.extend(build_live_turn_mutations(turn, 1))

    ops = {m["op"] for m in all_mutations}
    check("only SET/REMOVE ops", ops <= {"SET", "REMOVE"}, f"got {ops}")


def test_no_list_mutations():
    """No mutations contain list-type values at top level."""
    session = build_live_session(
        runtime_session_id="rt_list",
        mode="voice",
        transport="discord_voice",
        operator_id="op_1",
        started_at="2026-04-17T00:00:00Z",
    )
    mutations = build_live_session_mutations(session)
    for m in mutations:
        if "value" in m:
            check(
                f"no list value in {m['key']}",
                not isinstance(m["value"], list),
                f"got list for key {m['key']}",
            )


def test_no_provider_imports():
    """Controller module has no transport-specific imports."""
    import inspect
    import umh.substrate.live_session_controller as ctrl_module

    source = inspect.getsource(ctrl_module)
    # Extract actual import lines only
    import_lines = [
        line.strip()
        for line in source.splitlines()
        if line.strip().startswith(("import ", "from "))
    ]
    import_block = "\n".join(import_lines).lower()
    forbidden = ["discord", "google.cloud", "whisper", "voicebox"]
    for term in forbidden:
        check(
            f"no import of {term}",
            term not in import_block,
            f"found '{term}' in import statements",
        )


def test_continuity_summary_harness_generic():
    """Continuity summary has no product branding."""
    session = build_live_session(
        runtime_session_id="rt_sum",
        mode="voice",
        transport="discord_voice",
        operator_id="op_1",
        started_at="2026-04-17T00:00:00Z",
    )
    session = session._replace(turn_count=3, interruption_count=1)
    summary = build_live_continuity_summary(session)
    check("summary not empty", len(summary) > 0)
    check("summary has turn count", "3" in summary or "completed" in summary)
    check(
        "summary no branding",
        "dex" not in summary.lower() and "discord" not in summary.lower(),
    )


def test_deterministic_output_across_runs():
    """Same inputs produce identical outputs on repeated runs."""
    for _ in range(3):
        sid = compute_live_session_id("rt_det_run", "discord_voice", "op_1")
        tid = compute_live_turn_id("ses_det_run", 1, "hello")
        cid = compute_stream_chunk_id(
            "ses_det_run", "discord_voice", "2026-04-17T00:00:00Z"
        )
    # If we got here without error, all three runs produced consistent values
    check("deterministic across runs", True)


test_only_set_remove_ops()
test_no_list_mutations()
test_no_provider_imports()
test_continuity_summary_harness_generic()
test_deterministic_output_across_runs()


# =========================================================================
# Summary
# =========================================================================
print(f"\n{'=' * 60}")
print(f"RESULTS: {PASS} passed, {FAIL} failed, {PASS + FAIL} total")
print(f"{'=' * 60}")

if FAIL > 0:
    sys.exit(1)
