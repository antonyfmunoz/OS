"""Wave 2 C-3 — the scenario map is consumed by the real field pipeline.

C-3 was never "a scenario-map capability is missing" — `resolve_scenario_map`
already existed. C-3 was that NOTHING in the real pipeline wrote the map: the
only non-test `write_scenario_map` occurrence was inside a remediation *string*,
so `inject-failure` read `{}` → armed:False → exit 3, and the failure pass was
unrunnable.

These tests exercise the FIELD consumer over realistic candidate records and pin
the full chain plus every C-3 failure mode:

    materialized plan nodes → exact wp-* ids → run+plan-bound scenario_map.json
    → arming validation rereads it → targets exact identity → injection fires on
    A's first attempt only → fails qualification on: absent, stale, nonexistent,
    wrong-run, wrong-plan, ambiguous-role, out-of-frontier.

Plus the architectural guard: the map is IDENTITY CORRESPONDENCE only; it is
never a mutation authority (that stays on WorkPacket requirements).
"""

from __future__ import annotations

import pytest

from substrate.execution.attempts.field_failure_policy import (
    arming_is_valid_for_run,
    disallowed_tools_for,
)
from substrate.execution.attempts.field_scenario_map import (
    ScenarioMapError,
    build_from_records,
    read_scenario_map,
    write_scenario_map,
)
from substrate.execution.attempts.field_task_scope import (
    BACKEND,
    FIXTURE_NODE_TITLES,
    VERIFICATION,
)


# ── realistic candidate records ─────────────────────────────────────────────
def _plan_record(*, version=1, status="approved", run_tag="run-1"):
    """A plan record shaped like the compiler writes: nodes carry node_id +
    title + the materialized workpacket_id."""
    node_ids = {
        BACKEND: "node-be",
        "frontend_task_id": "node-fe",
        "integration_task_id": "node-int",
        VERIFICATION: "node-ver",
    }
    wp = {
        BACKEND: "wp-aaaaaaaaaaaa",
        "frontend_task_id": "wp-bbbbbbbbbbbb",
        "integration_task_id": "wp-cccccccccccc",
        VERIFICATION: "wp-dddddddddddd",
    }
    nodes = [
        {
            "node_id": node_ids[label],
            "kind": "packet",
            "status": "active",
            "title": FIXTURE_NODE_TITLES[label],
            "workpacket_id": wp[label],
        }
        for label in (BACKEND, "frontend_task_id", "integration_task_id", VERIFICATION)
    ]
    return {
        "plan_record_id": f"opr-{run_tag}",
        "graph_version": version,
        "status": status,
        "objective_text": f"add note search [{run_tag}]",
        "workpacket_ids": [n["workpacket_id"] for n in nodes],
        "nodes": nodes,
    }


def _records(**kw):
    return [_plan_record(**kw)]


def _frontier():
    return ["wp-aaaaaaaaaaaa", "wp-bbbbbbbbbbbb", "wp-cccccccccccc", "wp-dddddddddddd"]


def _arm(targets, variant="tools-revoked-backend"):
    (targets / ".inject_failure").write_text(variant, encoding="utf-8")


# ── the happy path: real records → bound map → exact target ─────────────────


def test_build_resolves_exact_ids_and_binds_to_run_and_plan():
    payload = build_from_records(_records(), run_id="run-1", run_tag="run-1")
    assert payload[BACKEND] == "wp-aaaaaaaaaaaa"
    assert payload[VERIFICATION] == "wp-dddddddddddd"
    assert payload["run_id"] == "run-1"
    assert payload["plan_record_id"] == "opr-run-1"
    assert payload["plan_version"] == 1
    assert payload["digest"], "the map must carry a digest for staleness detection"


def test_full_chain_arms_and_targets_the_exact_backend_packet(tmp_path):
    targets = tmp_path / "targets"
    targets.mkdir()
    write_scenario_map(targets, build_from_records(_records(), run_id="run-1", run_tag="run-1"))
    _arm(targets)

    ok, reason = arming_is_valid_for_run(
        str(targets),
        run_id="run-1",
        records=_records(),
        authorized_frontier=_frontier(),
        run_tag="run-1",
    )
    assert ok is True, reason

    # The injection revokes tools for the BACKEND packet's FIRST attempt only —
    # by exact id equality, never a title/regex/shape guess.
    revoked = disallowed_tools_for(
        targets_dir=str(targets), task_id="wp-aaaaaaaaaaaa", attempt_number=1
    )
    assert "Edit" in revoked and "Bash" in revoked
    # Retry (attempt 2) runs unrevoked → the graph can recover.
    assert (
        disallowed_tools_for(targets_dir=str(targets), task_id="wp-aaaaaaaaaaaa", attempt_number=2)
        == []
    )
    # A SIBLING packet is never revoked.
    assert (
        disallowed_tools_for(targets_dir=str(targets), task_id="wp-bbbbbbbbbbbb", attempt_number=1)
        == []
    )


def test_clean_run_is_always_valid(tmp_path):
    targets = tmp_path / "targets"
    targets.mkdir()
    ok, _ = arming_is_valid_for_run(
        str(targets), run_id="run-1", records=_records(), run_tag="run-1"
    )
    assert ok is True, "a clean run (no variant armed) needs no scenario map"


# ── the NINE C-3 failure modes must all fail qualification ──────────────────


def test_absent_map_fails(tmp_path):
    targets = tmp_path / "targets"
    targets.mkdir()
    _arm(targets)  # armed but no map written
    ok, reason = arming_is_valid_for_run(
        str(targets), run_id="run-1", records=_records(), run_tag="run-1"
    )
    assert ok is False and "absent" in reason


def test_stale_map_from_a_superseded_plan_fails(tmp_path):
    targets = tmp_path / "targets"
    targets.mkdir()
    # Map written against v1...
    write_scenario_map(
        targets, build_from_records(_records(version=1), run_id="run-1", run_tag="run-1")
    )
    _arm(targets)
    # ...but the live plan is now v2 (v1 superseded).
    live = _records(version=2)
    live.append(_plan_record(version=1, status="superseded"))
    ok, reason = arming_is_valid_for_run(
        str(targets), run_id="run-1", records=live, run_tag="run-1"
    )
    assert ok is False and "stale" in reason.lower()


def test_wrong_run_binding_fails(tmp_path):
    targets = tmp_path / "targets"
    targets.mkdir()
    write_scenario_map(targets, build_from_records(_records(), run_id="run-OTHER", run_tag="run-1"))
    _arm(targets)
    ok, reason = arming_is_valid_for_run(
        str(targets), run_id="run-1", records=_records(), run_tag="run-1"
    )
    assert ok is False and "another run" in reason.lower()


def test_map_referencing_a_nonexistent_task_fails(tmp_path):
    targets = tmp_path / "targets"
    targets.mkdir()
    payload = build_from_records(_records(), run_id="run-1", run_tag="run-1")
    payload[BACKEND] = "wp-ghostghostgh"  # tamper: a task that never materialized
    # Recompute a digest so it isn't caught as a plain digest mismatch first —
    # this must fail on the "not a materialized packet" / staleness check.
    write_scenario_map(targets, payload)
    _arm(targets)
    ok, reason = arming_is_valid_for_run(
        str(targets),
        run_id="run-1",
        records=_records(),
        authorized_frontier=_frontier(),
        run_tag="run-1",
    )
    assert ok is False


def test_target_outside_authorized_frontier_fails(tmp_path):
    targets = tmp_path / "targets"
    targets.mkdir()
    write_scenario_map(targets, build_from_records(_records(), run_id="run-1", run_tag="run-1"))
    _arm(targets)
    # The backend packet exists but is NOT in the (restricted) authorized frontier.
    ok, reason = arming_is_valid_for_run(
        str(targets),
        run_id="run-1",
        records=_records(),
        authorized_frontier=["wp-bbbbbbbbbbbb"],  # backend id excluded
        run_tag="run-1",
    )
    assert ok is False and "frontier" in reason.lower()


def test_ambiguous_role_two_nodes_same_title_fails():
    recs = _records()
    # Add a SECOND node with the backend title → the role is no longer singular.
    recs[0]["nodes"].append(
        {
            "node_id": "node-be2",
            "kind": "packet",
            "status": "active",
            "title": FIXTURE_NODE_TITLES[BACKEND],
            "workpacket_id": "wp-eeeeeeeeeeee",
        }
    )
    with pytest.raises(ScenarioMapError, match="matched 2 plan nodes"):
        build_from_records(recs, run_id="run-1", run_tag="run-1")


def test_no_live_plan_fails():
    with pytest.raises(ScenarioMapError, match="no live"):
        build_from_records([_plan_record(status="superseded")], run_id="run-1")


def test_unknown_variant_fails(tmp_path):
    targets = tmp_path / "targets"
    targets.mkdir()
    write_scenario_map(targets, build_from_records(_records(), run_id="run-1", run_tag="run-1"))
    (targets / ".inject_failure").write_text("tools-revoked-nonsense", encoding="utf-8")
    ok, reason = arming_is_valid_for_run(
        str(targets), run_id="run-1", records=_records(), run_tag="run-1"
    )
    assert ok is False and "unknown" in reason.lower()


# ── the map is NOT mutation authority ───────────────────────────────────────


def test_scenario_map_is_identity_only_never_writable_scope():
    """The map carries task IDENTITIES, never allowed tools / writable scope /
    execution constraints. Those stay on the WorkPacket requirements (C-1)."""
    payload = build_from_records(_records(), run_id="run-1", run_tag="run-1")
    forbidden = (
        "writable_path_scope",
        "allowed_tools",
        "scope_declared",
        "allowed_paths",
        "tool_policy",
        "risk_class",
    )
    for key in forbidden:
        assert key not in payload, f"the scenario map must not carry mutation authority ({key})"
    # It carries only identity + binding.
    assert set(payload) <= {
        BACKEND,
        "frontend_task_id",
        "integration_task_id",
        VERIFICATION,
        "run_id",
        "plan_record_id",
        "plan_version",
        "digest",
    }


def test_no_id_shape_or_title_fallback_in_the_field_module():
    """Source-level: the field consumer must resolve through lineage, never a
    regex / endswith / id-shape guess. Asserted on AST-unparsed CODE."""
    import ast
    import inspect

    from substrate.execution.attempts import field_scenario_map as fsm

    src = inspect.getsource(fsm)
    tree = ast.parse(src)
    code = "\n".join(
        ast.unparse(n) for n in tree.body if not isinstance(n, (ast.Import, ast.ImportFrom))
    )
    for banned in (".endswith(", "re.match", "re.search", "re.compile"):
        assert banned not in code, f"no {banned!r} shape-guessing in scenario-map resolution"


# ── configured-but-never-observed: an armed injection that never fires ───────


def test_injection_fired_detects_a_pass_that_never_revoked_anything():
    """An armed variant that produced no revoked dispatch proves nothing — the
    qualification must treat 'configured but never observed' as a failure."""
    from substrate.execution.attempts.field_failure_policy import injection_fired

    # No dispatch carried disallowed_tools → the injection never fired.
    assert injection_fired([{"disallowed_tools": []}, {"attempt_id": "x"}]) is False
    # A revoked dispatch → it fired.
    assert injection_fired([{"disallowed_tools": ["Edit", "Bash"]}]) is True


def test_end_to_end_field_consumption_fires_on_backend_first_attempt_only(tmp_path):
    """The full C-3 chain over the FIELD consumer: build the map from real
    records, validate it against the live run, then confirm the injection targets
    exactly the backend packet's first attempt and a retry recovers."""
    from substrate.execution.attempts.field_failure_policy import injection_fired

    targets = tmp_path / "targets"
    targets.mkdir()
    records = _records()

    # 1. FIELD WRITER: resolve + persist from real materialized records.
    payload = build_from_records(records, run_id="run-1", run_tag="run-1")
    write_scenario_map(targets, payload)
    _arm(targets)

    # 2. AUTHORITATIVE arming validation against the live run.
    ok, reason = arming_is_valid_for_run(
        str(targets),
        run_id="run-1",
        records=records,
        authorized_frontier=_frontier(),
        run_tag="run-1",
    )
    assert ok, reason

    # 3. INJECTION FIRES on the backend packet's first attempt (exact id).
    be = payload[BACKEND]
    dispatched = []
    for task in _frontier():
        for attempt in (1, 2):
            tools = disallowed_tools_for(
                targets_dir=str(targets), task_id=task, attempt_number=attempt
            )
            dispatched.append({"task_id": task, "attempt": attempt, "disallowed_tools": tools})

    fired = [d for d in dispatched if d["disallowed_tools"]]
    assert len(fired) == 1, f"exactly one dispatch must be revoked, got {fired}"
    assert fired[0]["task_id"] == be and fired[0]["attempt"] == 1
    assert injection_fired(dispatched) is True, (
        "the qualification must observe the injection firing"
    )

    # 4. The backend RETRY (attempt 2) is unrevoked → recovery is possible.
    assert not disallowed_tools_for(targets_dir=str(targets), task_id=be, attempt_number=2)


def test_persisted_map_round_trips_through_read(tmp_path):
    targets = tmp_path / "targets"
    targets.mkdir()
    payload = build_from_records(_records(), run_id="run-1", run_tag="run-1")
    write_scenario_map(targets, payload)
    got = read_scenario_map(targets)
    assert got["backend_task_id"] == payload["backend_task_id"]
    assert got["digest"] == payload["digest"]
