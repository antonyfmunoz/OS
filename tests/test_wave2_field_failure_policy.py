"""Wave 2 R2 — failure injection targets REAL canonical task ids.

Finding C2: the policy pattern-matched imagined identifiers (``tid == "a"``,
``tid.endswith("-a")``, …). Real packets are minted as ``wp-<hex12>``, which
contains no ``-`` in its suffix, so **0 of 2000 real ids matched**. Arming
``inject-failure`` revoked nothing, every task succeeded, and the failure pass
reported a clean green while injecting no failure at all.

Targeting is now equality against a persisted scenario map of the actual
materialized packet ids. These tests use REAL ``wp-<hex>`` identifiers
throughout; a test using a fake ``task-A`` identifier does not count.
"""

from __future__ import annotations

from uuid import uuid4

from substrate.execution.attempts.field_failure_policy import (
    arming_is_valid,
    disallowed_tools_for,
    injection_fired,
    read_scenario_map,
    read_variant,
    target_task_id,
    write_scenario_map,
)


def _real_packet_id() -> str:
    """Exactly how WorkPacket mints ids: f"wp-{uuid4().hex[:12]}"."""
    return f"wp-{uuid4().hex[:12]}"


def _arm(tmp_path, variant="tools-revoked-backend", mapping=None):
    (tmp_path / ".inject_failure").write_text(variant, encoding="utf-8")
    if mapping is not None:
        write_scenario_map(tmp_path, mapping)
    return tmp_path


def _scenario():
    return {
        "backend_task_id": _real_packet_id(),
        "frontend_task_id": _real_packet_id(),
        "integration_task_id": _real_packet_id(),
        "verification_task_id": _real_packet_id(),
    }


# ── the C2 regression: real ids must actually be targeted ───────────────────


def test_revocation_fires_on_the_real_backend_packet_id(tmp_path):
    s = _scenario()
    _arm(tmp_path, mapping=s)
    revoked = disallowed_tools_for(
        targets_dir=str(tmp_path), task_id=s["backend_task_id"], attempt_number=1
    )
    assert revoked, "the armed variant must revoke tools on the REAL backend task id"
    assert "Edit" in revoked and "Write" in revoked
    # Bash too: without it a CLI worker can `cat > file` and still commit, so the
    # 'genuine failure' would not be genuine (review W9).
    assert "Bash" in revoked, "Bash must be revoked or the worker can still commit"


def test_2000_real_ids_are_targeted_when_recorded(tmp_path):
    """The exact measurement that exposed C2 — but now the recorded id always
    fires, for every realistic id shape."""
    hits = 0
    for _ in range(2000):
        s = _scenario()
        _arm(tmp_path, mapping=s)
        if disallowed_tools_for(
            targets_dir=str(tmp_path), task_id=s["backend_task_id"], attempt_number=1
        ):
            hits += 1
    assert hits == 2000, f"expected every recorded backend id to fire, got {hits}/2000"


def test_only_the_backend_task_is_revoked(tmp_path):
    s = _scenario()
    _arm(tmp_path, mapping=s)
    for key in ("frontend_task_id", "integration_task_id", "verification_task_id"):
        assert (
            disallowed_tools_for(targets_dir=str(tmp_path), task_id=s[key], attempt_number=1) == []
        ), f"{key} must not be revoked"


def test_retry_attempt_is_not_revoked(tmp_path):
    """A2 must run unrevoked — that is what proves recovery works."""
    s = _scenario()
    _arm(tmp_path, mapping=s)
    assert disallowed_tools_for(
        targets_dir=str(tmp_path), task_id=s["backend_task_id"], attempt_number=1
    )
    assert (
        disallowed_tools_for(
            targets_dir=str(tmp_path), task_id=s["backend_task_id"], attempt_number=2
        )
        == []
    )


def test_unknown_task_id_is_never_revoked(tmp_path):
    s = _scenario()
    _arm(tmp_path, mapping=s)
    assert (
        disallowed_tools_for(targets_dir=str(tmp_path), task_id=_real_packet_id(), attempt_number=1)
        == []
    )


# ── the retained fake-id regression: it must control NOTHING ────────────────


def test_legacy_fake_task_a_identifiers_control_nothing(tmp_path):
    """RETAINED REGRESSION for C2.

    These are the identifiers the old matcher recognised. With targeting bound to
    the scenario map they must have no effect whatsoever — proving the fake-id
    path no longer controls the injection.
    """
    s = _scenario()
    _arm(tmp_path, mapping=s)
    for fake in ("A", "a", "wp-a", "task-a", "A-1", "a-1", "backend-a"):
        assert (
            disallowed_tools_for(targets_dir=str(tmp_path), task_id=fake, attempt_number=1) == []
        ), f"fake identifier {fake!r} still controls the injection"


# ── fail-closed arming ──────────────────────────────────────────────────────


def test_armed_without_scenario_map_is_invalid_not_clean(tmp_path):
    """The silent false green: armed, but nothing to target. Must be INVALID."""
    _arm(tmp_path, mapping=None)
    ok, reason = arming_is_valid(str(tmp_path))
    assert ok is False
    assert "scenario_map" in reason or "cannot target" in reason
    # And it genuinely revokes nothing, so the run would have looked clean.
    assert (
        disallowed_tools_for(targets_dir=str(tmp_path), task_id=_real_packet_id(), attempt_number=1)
        == []
    )


def test_armed_with_empty_backend_id_is_invalid(tmp_path):
    s = _scenario()
    s["backend_task_id"] = ""
    _arm(tmp_path, mapping=s)
    ok, reason = arming_is_valid(str(tmp_path))
    assert ok is False and "backend_task_id" in reason


def test_clean_run_is_valid_and_revokes_nothing(tmp_path):
    write_scenario_map(tmp_path, _scenario())
    ok, _reason = arming_is_valid(str(tmp_path))
    assert ok is True
    assert read_variant(str(tmp_path)) == ""
    assert target_task_id(str(tmp_path)) == ""


def test_unknown_variant_is_invalid(tmp_path):
    _arm(tmp_path, variant="something-else", mapping=_scenario())
    ok, reason = arming_is_valid(str(tmp_path))
    assert ok is False and "unknown failure variant" in reason


def test_legacy_variant_name_still_resolves_through_the_map(tmp_path):
    """The old CLI spelling must not silently arm nothing."""
    s = _scenario()
    _arm(tmp_path, variant="tools-revoked-a", mapping=s)
    ok, _r = arming_is_valid(str(tmp_path))
    assert ok is True
    assert disallowed_tools_for(
        targets_dir=str(tmp_path), task_id=s["backend_task_id"], attempt_number=1
    )


# ── scenario map + fired detection ──────────────────────────────────────────


def test_scenario_map_roundtrip(tmp_path):
    s = _scenario()
    write_scenario_map(tmp_path, s)
    loaded = read_scenario_map(tmp_path)
    for key, value in s.items():
        assert loaded[key] == value


def test_injection_fired_detects_a_revoked_dispatch(tmp_path):
    assert injection_fired([{"disallowed_tools": []}, {"disallowed_tools": ["Edit"]}])
    assert not injection_fired([{"disallowed_tools": []}, {"disallowed_tools": []}])
    assert not injection_fired([])


def test_marker_changes_the_computed_policy(tmp_path):
    """The load-bearing anti-dead-write assertion, on a REAL id."""
    s = _scenario()
    write_scenario_map(tmp_path, s)
    before = disallowed_tools_for(
        targets_dir=str(tmp_path), task_id=s["backend_task_id"], attempt_number=1
    )
    (tmp_path / ".inject_failure").write_text("tools-revoked-backend", encoding="utf-8")
    after = disallowed_tools_for(
        targets_dir=str(tmp_path), task_id=s["backend_task_id"], attempt_number=1
    )
    assert before == [] and after != [], "arming the marker must change the policy"
