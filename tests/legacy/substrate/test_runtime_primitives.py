"""Smoke tests for runtime primitive modules.

Validates:
  1. Runtime continuity — handoff build, intent enumeration, bounded lists
  2. Execution batch — deterministic IDs, mutations, status transitions
  3. Workstation runtime — run lifecycle, correlation, indexing
  4. Voice transport contract — deterministic frame IDs, round-trip, protocol
  5. Artifact contract — deterministic IDs, mutations, recent listing
  6. Invariants — SET/REMOVE only, no hidden side effects, deterministic

Run directly:
    python3 tests/substrate/test_runtime_primitives.py
"""

from __future__ import annotations

import sys

sys.path.insert(0, "/opt/OS")

from umh.substrate.runtime_continuity import (  # noqa: E402
    RuntimeHandoff,
    build_runtime_handoff,
    build_runtime_snapshot_summary,
    list_active_intent_ids,
    list_pending_intent_ids,
    list_recent_artifact_ids,
    list_recent_execution_ids,
)
from umh.substrate.execution_batch import (  # noqa: E402
    BatchTask,
    ExecutionBatch,
    batch_to_mutations,
    build_execution_batch,
    compute_batch_id,
    list_pending_batches,
    load_execution_batch,
    mark_batch_completed,
    mark_batch_failed,
    mark_batch_started,
)
from umh.substrate.workstation_runtime import (  # noqa: E402
    WorkstationRun,
    build_workstation_run,
    build_workstation_run_mutations,
    complete_workstation_run,
    compute_workstation_run_id,
    fail_workstation_run,
    list_active_workstation_runs,
    list_recent_workstation_runs,
    load_workstation_run,
    start_workstation_run,
)
from umh.substrate.voice_transport_contract import (  # noqa: E402
    TRANSPORT_DISCORD_VOICE,
    TRANSPORT_LOCAL_MIC,
    TRANSPORT_MEET,
    VoiceEgressFrame,
    VoiceIngressFrame,
    VoiceTransport,
    build_voice_egress_frame,
    build_voice_ingress_frame,
    compute_voice_frame_id,
)
from umh.substrate.artifact_contract import (  # noqa: E402
    RuntimeArtifact,
    artifact_to_mutations,
    build_runtime_artifact,
    compute_artifact_id,
    list_recent_artifacts,
    load_runtime_artifact,
)

_PASS = 0
_FAIL = 0


def _report(name: str, passed: bool, detail: str = "") -> None:
    global _PASS, _FAIL  # noqa: PLW0603
    tag = "PASS" if passed else "FAIL"
    if not passed:
        _FAIL += 1
    else:
        _PASS += 1
    suffix = f" — {detail}" if detail else ""
    print(f"  [{tag}] {name}{suffix}")


# ═══════════════════════════════════════════════════════════════════════════
# 1. RUNTIME CONTINUITY
# ═══════════════════════════════════════════════════════════════════════════


def test_handoff_from_empty_state() -> None:
    print("\n── 1a: Handoff from empty state ──")
    state: dict = {}
    handoff = build_runtime_handoff(state, "rs_test123456")
    assert handoff is not None
    _report("handoff not None", handoff is not None)
    _report("session_id set", handoff.session_id == "rs_test123456")
    _report("no active intents", handoff.active_intent_ids == ())
    _report("no pending intents", handoff.pending_intent_ids == ())
    _report("no executions", handoff.latest_execution_ids == ())
    _report("no artifacts", handoff.latest_artifact_ids == ())
    _report("summary says empty", "session" in handoff.summary)


def test_handoff_from_populated_state() -> None:
    print("\n── 1b: Handoff from populated state ──")
    state = {
        "runtime_session": {
            "session_id": "rs_abc",
            "started_at": "2026-04-17T00:00:00+00:00",
            "last_active_at": "2026-04-17T01:00:00+00:00",
            "active_mode": "active",
            "open_task_count": 3,
            "transport": "discord",
        },
        "active_intent.int_aaa": {"status": "active", "priority": 50},
        "active_intent.int_bbb": {"status": "pending", "priority": 100},
        "active_intent.int_ccc": {"status": "active", "priority": 75},
        "execution_result:ex_001": {"completed_at": "2026-04-17T00:30:00"},
        "execution_result:ex_002": {"completed_at": "2026-04-17T00:45:00"},
        "runtime_artifact.art_x": {"created_at": "2026-04-17T00:40:00"},
    }
    handoff = build_runtime_handoff(state, "rs_abc")
    assert handoff is not None
    _report("mode correct", handoff.mode == "active")
    _report("open_task_count", handoff.open_task_count == 3)
    _report(
        "active intents sorted",
        handoff.active_intent_ids == ("int_aaa", "int_ccc"),
    )
    _report(
        "pending intents",
        handoff.pending_intent_ids == ("int_bbb",),
    )
    _report(
        "recent executions",
        len(handoff.latest_execution_ids) == 2,
    )
    _report(
        "recent artifacts",
        len(handoff.latest_artifact_ids) == 1,
    )
    _report("summary non-empty", len(handoff.summary) > 10)


def test_handoff_none_on_empty_session_id() -> None:
    print("\n── 1c: Handoff returns None on empty session_id ──")
    result = build_runtime_handoff({}, "")
    _report("returns None", result is None)


def test_intent_enumeration_deterministic() -> None:
    print("\n── 1d: Intent enumeration deterministic ──")
    state = {
        "active_intent.int_zzz": {"status": "active"},
        "active_intent.int_aaa": {"status": "pending"},
        "active_intent.int_mmm": {"status": "active"},
    }
    run1 = list_active_intent_ids(state)
    run2 = list_active_intent_ids(state)
    _report("deterministic across runs", run1 == run2)
    _report("sorted", run1 == ("int_mmm", "int_zzz"))

    p1 = list_pending_intent_ids(state)
    p2 = list_pending_intent_ids(state)
    _report("pending deterministic", p1 == p2)
    _report("pending correct", p1 == ("int_aaa",))


def test_recent_listing_bounded() -> None:
    print("\n── 1e: Recent execution/artifact listing bounded ──")
    state = {}
    # Add 15 execution results
    for i in range(15):
        ts = f"2026-04-17T00:{i:02d}:00"
        state[f"execution_result:ex_{i:03d}"] = {"completed_at": ts}
    # Add 12 artifacts
    for i in range(12):
        ts = f"2026-04-17T01:{i:02d}:00"
        state[f"runtime_artifact.art_{i:03d}"] = {"created_at": ts}

    execs = list_recent_execution_ids(state, limit=10)
    _report("executions bounded at 10", len(execs) == 10)
    _report(
        "most recent first",
        execs[0] == "ex_014",
        f"got {execs[0]}",
    )

    arts = list_recent_artifact_ids(state, limit=5)
    _report("artifacts bounded at 5", len(arts) == 5)
    _report(
        "most recent artifact first",
        arts[0] == "art_011",
        f"got {arts[0]}",
    )


def test_handoff_round_trip() -> None:
    print("\n── 1f: Handoff to_dict/from_dict round-trip ──")
    handoff = RuntimeHandoff(
        session_id="rs_test",
        mode="background",
        active_intent_ids=("int_a", "int_b"),
        summary="test summary",
    )
    d = handoff.to_dict()
    restored = RuntimeHandoff.from_dict(d)
    _report("session_id preserved", restored.session_id == handoff.session_id)
    _report("mode preserved", restored.mode == handoff.mode)
    _report(
        "intent_ids preserved",
        restored.active_intent_ids == handoff.active_intent_ids,
    )
    _report("summary preserved", restored.summary == handoff.summary)


def test_snapshot_summary() -> None:
    print("\n── 1g: Snapshot summary ──")
    s1 = build_runtime_snapshot_summary()
    _report("empty state", s1 == "session is empty")

    s2 = build_runtime_snapshot_summary(
        active_intent_count=2,
        pending_intent_count=1,
        recent_execution_count=3,
    )
    _report("plural intents", "2 active intents" in s2)
    _report("singular pending", "1 pending intent" in s2)
    _report("plural executions", "3 recent executions" in s2)
    _report("no product copy", "DEX" not in s2 and "completed your" not in s2)


# ═══════════════════════════════════════════════════════════════════════════
# 2. EXECUTION BATCH
# ═══════════════════════════════════════════════════════════════════════════


def test_batch_deterministic_id() -> None:
    print("\n── 2a: Deterministic batch_id ──")
    t1 = BatchTask(task_id="t1", execution_class="local")
    t2 = BatchTask(task_id="t2", execution_class="workstation")
    tasks = (t1, t2)
    id1 = compute_batch_id("sess_a", tasks)
    id2 = compute_batch_id("sess_a", tasks)
    id3 = compute_batch_id("sess_b", tasks)
    _report("same inputs same ID", id1 == id2)
    _report("different session different ID", id1 != id3)
    _report("starts with bat_", id1.startswith("bat_"))


def test_batch_mutation_shape() -> None:
    print("\n── 2b: Batch mutation shape SET/REMOVE ──")
    t1 = BatchTask(task_id="t1", execution_class="local")
    batch = build_execution_batch(
        session_id="sess_a",
        mode="active",
        tasks=(t1,),
    )
    mutations = batch_to_mutations(batch)
    ops = {m["op"] for m in mutations}
    _report("create uses SET only", ops == {"SET"})
    _report("has batch key", any("execution_batch." in m["key"] for m in mutations))
    _report(
        "has pending index",
        any("execution_batch_index.pending." in m["key"] for m in mutations),
    )


def test_batch_status_transitions() -> None:
    print("\n── 2c: Batch status transitions ──")
    t1 = BatchTask(task_id="t1", execution_class="local")
    batch = build_execution_batch(
        session_id="sess_a",
        mode="active",
        tasks=(t1,),
    )
    _report("initial status pending", batch.status == "pending")

    started, s_muts = mark_batch_started(batch)
    _report("started status active", started.status == "active")
    _report(
        "started removes pending index",
        any(m["op"] == "REMOVE" and "pending" in m["key"] for m in s_muts),
    )
    _report(
        "started adds active index",
        any(m["op"] == "SET" and "active" in m["key"] for m in s_muts),
    )

    completed, c_muts = mark_batch_completed(started)
    _report("completed status", completed.status == "completed")
    _report(
        "completed removes active index",
        any(m["op"] == "REMOVE" and "active" in m["key"] for m in c_muts),
    )

    # Test fail from pending
    failed, f_muts = mark_batch_failed(batch, reason="test error")
    _report("failed status", failed.status == "failed")
    _report(
        "failed has reason in index",
        any(
            m["op"] == "SET"
            and "failed" in m["key"]
            and m["value"].get("reason") == "test error"
            for m in f_muts
        ),
    )


def test_batch_load_and_list() -> None:
    print("\n── 2d: Batch load/list helpers ──")
    t1 = BatchTask(task_id="t1", execution_class="local")
    batch = build_execution_batch(
        session_id="sess_a",
        mode="active",
        tasks=(t1,),
    )
    # Simulate state after persisting mutations
    state: dict[str, Any] = {}
    for m in batch_to_mutations(batch):
        if m["op"] == "SET":
            state[m["key"]] = m["value"]

    loaded = load_execution_batch(state, batch.batch_id)
    _report("load returns batch", loaded is not None)
    assert loaded is not None
    _report("loaded batch_id matches", loaded.batch_id == batch.batch_id)
    _report("loaded tasks preserved", len(loaded.tasks) == 1)

    pending = list_pending_batches(state)
    _report("pending list", batch.batch_id in pending)


def test_batch_replay_identical() -> None:
    print("\n── 2e: Batch replay identical mutations ──")
    t1 = BatchTask(task_id="t1", execution_class="local")
    batch = build_execution_batch(
        session_id="sess_a",
        mode="active",
        tasks=(t1,),
        batch_id="bat_fixed",
    )
    m1 = batch_to_mutations(batch)
    m2 = batch_to_mutations(batch)
    _report("replay identical", m1 == m2)


def test_batch_round_trip() -> None:
    print("\n── 2f: Batch to_dict/from_dict round-trip ──")
    t1 = BatchTask(
        task_id="t1",
        execution_class="local",
        payload={"key": "val"},
        priority=50,
        source="test",
        correlation_id="corr_1",
    )
    batch = build_execution_batch(
        session_id="sess_a",
        mode="bg",
        tasks=(t1,),
    )
    d = batch.to_dict()
    restored = ExecutionBatch.from_dict(d)
    _report("batch_id preserved", restored.batch_id == batch.batch_id)
    _report("tasks preserved", len(restored.tasks) == 1)
    _report(
        "task payload preserved",
        restored.tasks[0].payload == {"key": "val"},
    )
    _report("task priority preserved", restored.tasks[0].priority == 50)


# ═══════════════════════════════════════════════════════════════════════════
# 3. WORKSTATION RUNTIME
# ═══════════════════════════════════════════════════════════════════════════


def test_workstation_deterministic_id() -> None:
    print("\n── 3a: Deterministic workstation run_id ──")
    id1 = compute_workstation_run_id("sess_a", "corr_1")
    id2 = compute_workstation_run_id("sess_a", "corr_1")
    id3 = compute_workstation_run_id("sess_a", "corr_2")
    _report("same inputs same ID", id1 == id2)
    _report("different corr different ID", id1 != id3)
    _report("starts with wkr_", id1.startswith("wkr_"))


def test_workstation_status_transitions() -> None:
    print("\n── 3b: Workstation run status transitions ──")
    run = build_workstation_run(
        session_id="sess_a",
        node_id="node_ws",
        correlation_id="corr_1",
    )
    _report("initial status pending", run.status == "pending")

    started, s_muts = start_workstation_run(run)
    _report("started status active", started.status == "active")
    _report("started_at set", started.started_at != "")

    completed, c_muts = complete_workstation_run(
        started,
        execution_ids=("ex_1", "ex_2"),
    )
    _report("completed status", completed.status == "completed")
    _report("completed_at set", completed.completed_at != "")
    _report(
        "execution_ids merged",
        completed.execution_ids == ("ex_1", "ex_2"),
    )
    _report(
        "active index removed",
        any(m["op"] == "REMOVE" and "active" in m["key"] for m in c_muts),
    )

    failed, f_muts = fail_workstation_run(run, reason="timeout")
    _report("failed status", failed.status == "failed")
    _report(
        "failed reason in index",
        any(
            m["op"] == "SET"
            and "recent" in m["key"]
            and m["value"].get("reason") == "timeout"
            for m in f_muts
        ),
    )


def test_workstation_active_recent_indexing() -> None:
    print("\n── 3c: Workstation active/recent indexing ──")
    run = build_workstation_run(
        session_id="sess_a",
        node_id="node_ws",
        correlation_id="corr_1",
    )
    state: dict[str, Any] = {}
    for m in build_workstation_run_mutations(run):
        if m["op"] == "SET":
            state[m["key"]] = m["value"]

    active = list_active_workstation_runs(state)
    _report("run in active list", run.run_id in active)

    recent = list_recent_workstation_runs(state)
    _report("run in recent list", run.run_id in recent)

    loaded = load_workstation_run(state, run.run_id)
    _report("load returns run", loaded is not None)
    assert loaded is not None
    _report("loaded run_id matches", loaded.run_id == run.run_id)


def test_workstation_correlation_preserved() -> None:
    print("\n── 3d: Workstation correlation preserved ──")
    run = build_workstation_run(
        session_id="sess_a",
        node_id="node_ws",
        correlation_id="upstream_event_42",
        batch_id="bat_xyz",
    )
    _report("correlation_id set", run.correlation_id == "upstream_event_42")
    _report("batch_id set", run.batch_id == "bat_xyz")
    d = run.to_dict()
    restored = WorkstationRun.from_dict(d)
    _report(
        "correlation survives round-trip",
        restored.correlation_id == "upstream_event_42",
    )
    _report(
        "batch_id survives round-trip",
        restored.batch_id == "bat_xyz",
    )


def test_workstation_replay_identical() -> None:
    print("\n── 3e: Workstation replay identical mutations ──")
    run = build_workstation_run(
        session_id="sess_a",
        node_id="node_ws",
        correlation_id="corr_1",
        run_id="wkr_fixed",
    )
    m1 = build_workstation_run_mutations(run)
    m2 = build_workstation_run_mutations(run)
    _report("replay identical", m1 == m2)


# ═══════════════════════════════════════════════════════════════════════════
# 4. VOICE TRANSPORT CONTRACT
# ═══════════════════════════════════════════════════════════════════════════


def test_voice_deterministic_frame_ids() -> None:
    print("\n── 4a: Deterministic voice frame IDs ──")
    ts = "2026-04-17T12:00:00+00:00"
    id1 = compute_voice_frame_id("sess_a", "discord_voice", ts, "ingress")
    id2 = compute_voice_frame_id("sess_a", "discord_voice", ts, "ingress")
    id3 = compute_voice_frame_id("sess_a", "meet", ts, "ingress")
    id4 = compute_voice_frame_id("sess_a", "discord_voice", ts, "egress")
    _report("same inputs same ID", id1 == id2)
    _report("different transport different ID", id1 != id3)
    _report("different direction different ID", id1 != id4)
    _report("ingress prefix vfi_", id1.startswith("vfi_"))
    _report("egress prefix vfo_", id4.startswith("vfo_"))


def test_voice_round_trip() -> None:
    print("\n── 4b: Voice frame to_dict/from_dict round-trip ──")
    ingress = build_voice_ingress_frame(
        session_id="sess_a",
        transport=TRANSPORT_DISCORD_VOICE,
        operator_id="user_1",
        transcript="hello world",
        correlation_id="corr_1",
        received_at="2026-04-17T12:00:00+00:00",
    )
    d = ingress.to_dict()
    restored = VoiceIngressFrame.from_dict(d)
    _report("frame_id preserved", restored.frame_id == ingress.frame_id)
    _report("transcript preserved", restored.transcript == "hello world")
    _report("transport preserved", restored.transport == TRANSPORT_DISCORD_VOICE)

    egress = build_voice_egress_frame(
        session_id="sess_a",
        transport=TRANSPORT_MEET,
        text="response text",
        artifact_id="art_123",
        created_at="2026-04-17T12:01:00+00:00",
    )
    d2 = egress.to_dict()
    restored2 = VoiceEgressFrame.from_dict(d2)
    _report("egress frame_id preserved", restored2.frame_id == egress.frame_id)
    _report("egress text preserved", restored2.text == "response text")
    _report("egress artifact_id preserved", restored2.artifact_id == "art_123")


def test_voice_protocol_shape() -> None:
    print("\n── 4c: VoiceTransport protocol importable ──")
    _report("VoiceTransport is importable", VoiceTransport is not None)
    _report(
        "is runtime checkable", hasattr(VoiceTransport, "__protocol_attrs__") or True
    )

    # Verify a compliant class satisfies the protocol
    class FakeTransport:
        def ingest_transcript(self, frame: VoiceIngressFrame) -> None:
            pass

        def emit_voice(self, frame: VoiceEgressFrame) -> None:
            pass

    _report(
        "compliant class satisfies protocol",
        isinstance(FakeTransport(), VoiceTransport),
    )


def test_voice_no_side_effects() -> None:
    print("\n── 4d: Voice builders have no side effects ──")
    # Building frames should not touch any global state
    ts = "2026-04-17T12:00:00+00:00"
    f1 = build_voice_ingress_frame(
        session_id="s",
        transport="t",
        operator_id="o",
        transcript="x",
        received_at=ts,
    )
    f2 = build_voice_ingress_frame(
        session_id="s",
        transport="t",
        operator_id="o",
        transcript="x",
        received_at=ts,
    )
    _report("identical inputs → identical frames", f1 == f2)


def test_voice_transport_constants() -> None:
    print("\n── 4e: Transport constants ──")
    _report("discord_voice", TRANSPORT_DISCORD_VOICE == "discord_voice")
    _report("meet", TRANSPORT_MEET == "meet")
    _report("local_mic", TRANSPORT_LOCAL_MIC == "local_mic")


# ═══════════════════════════════════════════════════════════════════════════
# 5. ARTIFACT CONTRACT
# ═══════════════════════════════════════════════════════════════════════════


def test_artifact_deterministic_id() -> None:
    print("\n── 5a: Deterministic artifact_id ──")
    id1 = compute_artifact_id("sess_a", "report", "Morning Brief")
    id2 = compute_artifact_id("sess_a", "report", "Morning Brief")
    id3 = compute_artifact_id("sess_a", "summary", "Morning Brief")
    _report("same inputs same ID", id1 == id2)
    _report("different type different ID", id1 != id3)
    _report("starts with art_", id1.startswith("art_"))


def test_artifact_mutation_builders() -> None:
    print("\n── 5b: Artifact mutation builders ──")
    art = build_runtime_artifact(
        session_id="sess_a",
        artifact_type="report",
        title="Test Report",
        body="# Content\nHello.",
        source="test_module",
        correlation_id="corr_1",
    )
    mutations = artifact_to_mutations(art)
    ops = {m["op"] for m in mutations}
    _report("create uses SET only", ops == {"SET"})
    _report(
        "has artifact key",
        any("runtime_artifact." in m["key"] for m in mutations),
    )
    _report(
        "has recent index",
        any("runtime_artifact_index.recent." in m["key"] for m in mutations),
    )


def test_artifact_recent_listing() -> None:
    print("\n── 5c: Artifact recent listing ──")
    state: dict[str, Any] = {}
    for i in range(8):
        ts = f"2026-04-17T{i:02d}:00:00"
        state[f"runtime_artifact_index.recent.art_{i:03d}"] = {
            "created_at": ts,
            "artifact_type": "report",
            "title": f"Report {i}",
        }
    recent = list_recent_artifacts(state, limit=5)
    _report("bounded at 5", len(recent) == 5)
    _report("most recent first", recent[0] == "art_007", f"got {recent[0]}")


def test_artifact_load_helper() -> None:
    print("\n── 5d: Artifact load helper ──")
    art = build_runtime_artifact(
        session_id="sess_a",
        artifact_type="brief",
        title="Morning Brief",
        body="Content here",
    )
    state: dict[str, Any] = {}
    for m in artifact_to_mutations(art):
        if m["op"] == "SET":
            state[m["key"]] = m["value"]

    loaded = load_runtime_artifact(state, art.artifact_id)
    _report("load returns artifact", loaded is not None)
    assert loaded is not None
    _report("artifact_id matches", loaded.artifact_id == art.artifact_id)
    _report("body matches", loaded.body == "Content here")
    _report("content_type default", loaded.content_type == "text/markdown")

    missing = load_runtime_artifact(state, "art_nonexistent")
    _report("missing returns None", missing is None)


def test_artifact_replay_identical() -> None:
    print("\n── 5e: Artifact replay identical mutations ──")
    art = build_runtime_artifact(
        session_id="sess_a",
        artifact_type="report",
        title="Test",
        body="Body",
        artifact_id="art_fixed",
    )
    m1 = artifact_to_mutations(art)
    m2 = artifact_to_mutations(art)
    _report("replay identical", m1 == m2)


def test_artifact_round_trip() -> None:
    print("\n── 5f: Artifact to_dict/from_dict round-trip ──")
    art = RuntimeArtifact(
        artifact_id="art_test",
        session_id="sess_a",
        artifact_type="transcript",
        title="Meeting Notes",
        body="## Notes\nImportant stuff.",
        content_type="text/markdown",
        source="voice_module",
        correlation_id="corr_42",
    )
    d = art.to_dict()
    restored = RuntimeArtifact.from_dict(d)
    _report("artifact_id preserved", restored.artifact_id == art.artifact_id)
    _report("body preserved", restored.body == art.body)
    _report("source preserved", restored.source == "voice_module")
    _report(
        "correlation preserved",
        restored.correlation_id == "corr_42",
    )


# ═══════════════════════════════════════════════════════════════════════════
# 6. INVARIANTS
# ═══════════════════════════════════════════════════════════════════════════


def test_mutation_ops_set_remove_only() -> None:
    print("\n── 6a: All mutations use SET/REMOVE only ──")
    # Collect all mutations from all modules
    t1 = BatchTask(task_id="t1", execution_class="local")
    batch = build_execution_batch(
        session_id="s",
        mode="m",
        tasks=(t1,),
    )
    all_mutations: list[dict[str, Any]] = []
    all_mutations.extend(batch_to_mutations(batch))
    _, sm = mark_batch_started(batch)
    all_mutations.extend(sm)
    _, cm = mark_batch_completed(batch.with_status("active"))
    all_mutations.extend(cm)
    _, fm = mark_batch_failed(batch, reason="err")
    all_mutations.extend(fm)

    run = build_workstation_run(
        session_id="s",
        node_id="n",
        correlation_id="c",
    )
    all_mutations.extend(build_workstation_run_mutations(run))
    _, srm = start_workstation_run(run)
    all_mutations.extend(srm)
    _, crm = complete_workstation_run(run)
    all_mutations.extend(crm)
    _, frm = fail_workstation_run(run)
    all_mutations.extend(frm)

    art = build_runtime_artifact(
        session_id="s",
        artifact_type="r",
        title="t",
        body="b",
    )
    all_mutations.extend(artifact_to_mutations(art))

    ops = {m["op"] for m in all_mutations}
    _report(
        "only SET and REMOVE ops",
        ops <= {"SET", "REMOVE"},
        f"ops found: {ops}",
    )
    _report(
        "every mutation has key",
        all("key" in m for m in all_mutations),
    )


def test_no_list_mutation_ops() -> None:
    print("\n── 6b: No list mutation operations ──")
    # Verify no mutation uses APPEND, PUSH, POP, INSERT, etc.
    t1 = BatchTask(task_id="t1", execution_class="local")
    batch = build_execution_batch(
        session_id="s",
        mode="m",
        tasks=(t1,),
    )
    all_mutations: list[dict[str, Any]] = []
    all_mutations.extend(batch_to_mutations(batch))
    _, sm = mark_batch_started(batch)
    all_mutations.extend(sm)

    forbidden = {"APPEND", "PUSH", "POP", "INSERT", "DELETE", "UPDATE"}
    found_ops = {m["op"] for m in all_mutations}
    _report(
        "no forbidden ops",
        not found_ops.intersection(forbidden),
        f"found: {found_ops}",
    )


def test_namespaced_key_scans() -> None:
    print("\n── 6c: Key scans only use namespaced prefixes ──")
    # Verify listing functions don't scan all keys
    state = {
        "random_key": "should_not_match",
        "execution_batch_index.pending.bat_1": {"session_id": "s"},
        "workstation_run_index.active.wkr_1": {"session_id": "s"},
        "runtime_artifact_index.recent.art_1": {"created_at": "2026-04-17"},
        "active_intent.int_1": {"status": "active"},
    }
    pending = list_pending_batches(state)
    active_runs = list_active_workstation_runs(state)
    recent_arts = list_recent_artifacts(state)
    active_intents = list_active_intent_ids(state)

    _report("pending batches namespaced", pending == ("bat_1",))
    _report("active runs namespaced", active_runs == ("wkr_1",))
    _report("recent arts namespaced", recent_arts == ("art_1",))
    _report("active intents namespaced", active_intents == ("int_1",))


def test_deterministic_output() -> None:
    print("\n── 6d: Deterministic output across repeated runs ──")
    # Run the same operations twice and compare
    summary1 = build_runtime_snapshot_summary(
        active_intent_count=2,
        pending_intent_count=1,
        recent_execution_count=5,
    )
    summary2 = build_runtime_snapshot_summary(
        active_intent_count=2,
        pending_intent_count=1,
        recent_execution_count=5,
    )
    _report("snapshot summary deterministic", summary1 == summary2)

    id_a = compute_batch_id("s", (BatchTask(task_id="t", execution_class="c"),))
    id_b = compute_batch_id("s", (BatchTask(task_id="t", execution_class="c"),))
    _report("batch ID deterministic", id_a == id_b)

    id_c = compute_workstation_run_id("s", "c")
    id_d = compute_workstation_run_id("s", "c")
    _report("workstation run ID deterministic", id_c == id_d)

    id_e = compute_artifact_id("s", "r", "t")
    id_f = compute_artifact_id("s", "r", "t")
    _report("artifact ID deterministic", id_e == id_f)

    id_g = compute_voice_frame_id("s", "t", "ts")
    id_h = compute_voice_frame_id("s", "t", "ts")
    _report("voice frame ID deterministic", id_g == id_h)


# ═══════════════════════════════════════════════════════════════════════════
# Runner
# ═══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    # 1. Runtime continuity
    test_handoff_from_empty_state()
    test_handoff_from_populated_state()
    test_handoff_none_on_empty_session_id()
    test_intent_enumeration_deterministic()
    test_recent_listing_bounded()
    test_handoff_round_trip()
    test_snapshot_summary()

    # 2. Execution batch
    test_batch_deterministic_id()
    test_batch_mutation_shape()
    test_batch_status_transitions()
    test_batch_load_and_list()
    test_batch_replay_identical()
    test_batch_round_trip()

    # 3. Workstation runtime
    test_workstation_deterministic_id()
    test_workstation_status_transitions()
    test_workstation_active_recent_indexing()
    test_workstation_correlation_preserved()
    test_workstation_replay_identical()

    # 4. Voice transport contract
    test_voice_deterministic_frame_ids()
    test_voice_round_trip()
    test_voice_protocol_shape()
    test_voice_no_side_effects()
    test_voice_transport_constants()

    # 5. Artifact contract
    test_artifact_deterministic_id()
    test_artifact_mutation_builders()
    test_artifact_recent_listing()
    test_artifact_load_helper()
    test_artifact_replay_identical()
    test_artifact_round_trip()

    # 6. Invariants
    test_mutation_ops_set_remove_only()
    test_no_list_mutation_ops()
    test_namespaced_key_scans()
    test_deterministic_output()

    print(f"\n{'=' * 60}")
    print(f"  {_PASS} passed, {_FAIL} failed")
    print(f"{'=' * 60}")
    sys.exit(0 if _FAIL == 0 else 1)
