"""Field fixture task-instruction boundaries — the w16 concurrency correction.

Field run ``20260803T002300Z-p1`` failed at ``w16_ab_running_concurrent``: BOTH
workers changed the SAME six files (the complete objective) and BOTH were
correctly refused with ``diff_scope``. The declared scopes were already right and
``render_prompt`` already named them — the defect was the task CONTENT the worker
received. Each lane carried only a short title, so the only substantive spec a
worker could find was the fixture repo's ``OBJECTIVE.md``, a single document
holding ALL FOUR task contracts.

These tests exercise the REAL generation path (``_declared_lanes_json`` and the
shipped ``render_prompt``) rather than asserting on source text, and they fail if
any element of the boundary contract is removed.
"""

from __future__ import annotations

import importlib.util
import json
import os
import sys

import pytest

_ROOT = os.environ.get("UMH_ROOT", "/opt/OS")
_WT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _WT)

from substrate.execution.attempts.field_task_scope import (  # noqa: E402
    BACKEND,
    FIXTURE_ALLOWED_PATHS,
    FIXTURE_PRECEDENCE_NOTE,
    FRONTEND,
    INTEGRATION,
    VERIFICATION,
    ScopeResolutionError,
    forbidden_paths_for,
    task_contract_for,
    task_intent_for,
)
from substrate.execution.attempts.worker_claude_cli import render_prompt  # noqa: E402

_BACKEND_FILES = ("app/main.py", "app/store.py", "tests/test_search_api.py")
_FRONTEND_FILES = ("app/static", "tests/test_ui_search.py")


def _lanes() -> dict[str, dict]:
    """Run the REAL lane producer from the shipped dispatcher."""
    spec = importlib.util.spec_from_file_location(
        "wfd_boundaries", os.path.join(_WT, "scripts", "wave2_field_dispatch.py")
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules["wfd_boundaries"] = mod
    spec.loader.exec_module(mod)
    return {lane["lane_key"]: lane for lane in json.loads(mod._declared_lanes_json())}


class _Package:
    """Minimal stand-in for the sealed package shape ``render_prompt`` consumes."""

    def __init__(self, lane: dict) -> None:
        self.role_instructions = ""
        self.operation_instructions = lane["intent"]
        self.operation_identity = {"task_id": f"wp-{lane['lane_key']}"}
        self.ordered_context = [
            {"section": "task", "payload": {"title": lane["title"]}},
            {"section": "desired_end_state", "payload": lane["desired_end_state"]},
            {"section": "constraints", "payload": lane["constraints"]},
        ]
        self.governance_constraints = [
            f"writable_path_scope={sorted(lane['writable_path_scope'])}"
        ]


def _prompt_for(lane_key: str) -> str:
    return render_prompt(_Package(_lanes()[lane_key]))


# ── 1/2. Each Task receives only its own write authority ─────────────────────


def test_backend_lane_declares_only_backend_write_authority():
    lane = _lanes()["backend"]
    assert sorted(lane["writable_path_scope"]) == sorted(_BACKEND_FILES)
    for path in _FRONTEND_FILES:
        assert path not in lane["writable_path_scope"]


def test_frontend_lane_declares_only_frontend_write_authority():
    lane = _lanes()["frontend"]
    assert sorted(lane["writable_path_scope"]) == sorted(_FRONTEND_FILES)
    for path in _BACKEND_FILES:
        assert path not in lane["writable_path_scope"]


# ── 3. Each package names its exact allowed files ────────────────────────────


@pytest.mark.parametrize(
    ("lane_key", "expected"),
    [("backend", _BACKEND_FILES), ("frontend", _FRONTEND_FILES)],
)
def test_prompt_names_every_allowed_path(lane_key, expected):
    prompt = _prompt_for(lane_key)
    assert "Writable Scope" in prompt
    for path in expected:
        assert path in prompt, f"{lane_key} prompt must name its allowed path {path}"


@pytest.mark.parametrize(
    ("lane_key", "expected"),
    [("backend", _BACKEND_FILES), ("frontend", _FRONTEND_FILES)],
)
def test_lane_constraints_carry_the_explicit_allowed_file_list(lane_key, expected):
    """The Task-LOCAL constraint must itself enumerate the allowed paths.

    Distinct from the sealed ``## Writable Scope`` section: mutation m1 deleted
    the constraint-level list and the scope section alone kept the suite green,
    so the boundary was only half-asserted.
    """
    lane = _lanes()[lane_key]
    joined = "\n".join(lane["constraints"])
    assert "You may change ONLY these paths" in joined
    for path in expected:
        assert path in joined, f"{lane_key} constraints must enumerate {path}"


@pytest.mark.parametrize("lane_key", ["backend", "frontend"])
def test_lane_constraints_forbid_solving_the_whole_objective_verbatim(lane_key):
    """Exact-string form: mutation m6 replaced this line and a lowercased
    substring check still matched, so the prohibition was not really pinned."""
    joined = "\n".join(_lanes()[lane_key]["constraints"])
    assert "do NOT solve the complete objective" in joined
    assert "Implement the complete objective." not in joined


# ── 4. Each package explicitly forbids the other Task's files ────────────────


def test_backend_prompt_explicitly_forbids_frontend_files():
    prompt = _prompt_for("backend")
    assert "FORBIDDEN" in prompt
    for path in _FRONTEND_FILES:
        assert path in prompt, f"backend prompt must NAME the forbidden path {path}"


def test_frontend_prompt_explicitly_forbids_backend_files():
    prompt = _prompt_for("frontend")
    assert "FORBIDDEN" in prompt
    for path in _BACKEND_FILES:
        assert path in prompt, f"frontend prompt must NAME the forbidden path {path}"


def test_forbidden_paths_are_mutually_exclusive_with_allowed():
    for label in (BACKEND, FRONTEND):
        allowed = set(FIXTURE_ALLOWED_PATHS[label])
        forbidden = set(forbidden_paths_for(label))
        assert allowed and forbidden
        assert not (allowed & forbidden), f"{label}: allowed and forbidden overlap"


# ── 5. Each package forbids solving the entire objective ─────────────────────


@pytest.mark.parametrize("lane_key", ["backend", "frontend"])
def test_prompt_forbids_solving_the_complete_objective(lane_key):
    prompt = _prompt_for(lane_key).lower()
    assert "do not solve the complete objective" in prompt


# ── 6. OBJECTIVE.md cannot broaden the Task scope ────────────────────────────


@pytest.mark.parametrize("lane_key", ["backend", "frontend"])
def test_prompt_subordinates_the_global_objective(lane_key):
    prompt = _prompt_for(lane_key)
    assert "OBJECTIVE.md" in prompt
    assert "INFORMATIONAL ONLY" in prompt
    assert "does NOT authorize you to widen your change surface" in prompt


def test_precedence_order_is_unambiguous():
    note = FIXTURE_PRECEDENCE_NOTE
    i_grant = note.index("grant and WorkPacket authorization")
    i_task = note.index("This Task's instructions")
    i_arch = note.index("Shared architectural context")
    i_obj = note.index("`OBJECTIVE.md` and any other repository document")
    assert i_grant < i_task < i_arch < i_obj, "precedence must be strictly ordered"


# ── 7/8. Each slice is completable without the other's files ─────────────────


def test_backend_contract_is_self_sufficient_without_frontend_edits():
    contract = task_contract_for(BACKEND)
    assert "/api/notes/search" in contract
    assert "400" in contract
    assert "tests/test_search_api.py" in contract
    assert "Do NOT create or edit any frontend file." in contract


def test_frontend_contract_is_self_sufficient_without_backend_edits():
    contract = task_contract_for(FRONTEND)
    assert "note-search-input" in contract
    assert "note-search-results" in contract
    assert "tests/test_ui_search.py" in contract
    assert "Do NOT create or edit any backend file." in contract
    # Its test must not require the backend to exist, or the lanes are coupled.
    assert "must NOT require the backend endpoint to exist" in contract


def test_frontend_is_told_the_backend_runs_concurrently():
    """Without this the frontend worker "helpfully" implements the endpoint."""
    text = task_intent_for(FRONTEND) + task_contract_for(FRONTEND)
    assert "CONCURRENTLY" in text or "concurrently" in text
    assert "do NOT implement it yourself" in text


# ── 11. The two accepted slices compose into the complete objective ──────────


def test_backend_and_frontend_scopes_compose_to_the_whole_objective():
    union = set(FIXTURE_ALLOWED_PATHS[BACKEND]) | set(FIXTURE_ALLOWED_PATHS[FRONTEND])
    # Every file the integration lane may touch must be owned by A or B.
    assert set(FIXTURE_ALLOWED_PATHS[INTEGRATION]) <= union


# ── 12. Verification stays zero-write ────────────────────────────────────────


def test_verification_lane_remains_zero_write():
    assert FIXTURE_ALLOWED_PATHS[VERIFICATION] == []
    prompt = _prompt_for("verification")
    assert "READ-ONLY" in prompt
    assert "ZERO writable paths" in prompt


# ── fail-closed accessors ────────────────────────────────────────────────────


def test_accessors_fail_closed_on_unknown_label():
    for fn in (task_intent_for, task_contract_for, forbidden_paths_for):
        with pytest.raises(ScopeResolutionError):
            fn("not_a_real_label")


# ── the exact field regression ───────────────────────────────────────────────


def test_the_six_file_overreach_is_forbidden_by_both_lanes():
    """The EXACT files both workers changed in run 20260803T002300Z-p1."""
    overreach = [
        "app/main.py",
        "app/static/app.js",
        "app/static/index.html",
        "app/store.py",
        "tests/test_search_api.py",
        "tests/test_ui_search.py",
    ]
    for label in (BACKEND, FRONTEND):
        allowed = FIXTURE_ALLOWED_PATHS[label]
        outside = [
            p
            for p in overreach
            if not any(p == a or p.startswith(a.rstrip("/") + "/") for a in allowed)
        ]
        assert outside, f"{label} must NOT be authorized for the whole six-file set"
