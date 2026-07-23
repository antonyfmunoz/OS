"""Wave 2 C4 — GovernedExecutionSpine consumes execution authorization (clause 5)."""

from __future__ import annotations

import time
from types import SimpleNamespace

import pytest

from substrate.organism.action_envelope import ActionEnvelope, ActionType
from substrate.organism.event_spine import EventSpine
from substrate.organism.execution_journal import ExecutionJournal
from substrate.organism.execution_modes import ExecutionMode, ExecutionModeManager
from substrate.organism.governed_spine import GovernedExecutionSpine
from substrate.organism.mutation_registry import MutationRegistry


def _spine(tmp_path, authorization_lookup=None):
    mode = ExecutionModeManager(initial_mode=ExecutionMode.AUTONOMOUS)
    journal = ExecutionJournal(persist_path=str(tmp_path / "journal.jsonl"))
    return GovernedExecutionSpine(
        event_spine=EventSpine(),
        execution_mode=mode,
        mutation_registry=MutationRegistry(),
        journal=journal,
        authorization_lookup=authorization_lookup,
    )


def _grant(**kw):
    base = dict(status="active", authorized_scope_hash="hash-1",
                task_frontier=["wp-a", "wp-b"], expires_at=time.time() + 3600)
    base.update(kw)
    return SimpleNamespace(**base)


def _envelope(**kw):
    return ActionEnvelope(
        intent="do a thing", action_type=ActionType.STATE, source="test",
        execute_fn=lambda: ("ok", True),
        metadata={"mutation_name": "execution_attempt_dispatch"},
        **kw,
    )


def test_no_authorization_ref_unaffected(tmp_path):
    spine = _spine(tmp_path)  # no lookup
    env = _envelope()  # no authorization_ref
    result = spine.submit(env)
    assert result.status.value != "rejected"


def test_authorization_ref_without_lookup_fails_closed(tmp_path):
    spine = _spine(tmp_path, authorization_lookup=None)
    env = _envelope(authorization_ref="objective_plan:opr-1:execution_authorization:v1")
    result = spine.submit(env)
    assert result.status.value == "rejected"
    assert "fail closed" in result.rejected_reason


def test_in_scope_action_admitted(tmp_path):
    grant = _grant()
    spine = _spine(tmp_path, authorization_lookup=lambda ref: grant)
    env = _envelope(
        authorization_ref="objective_plan:opr-1:execution_authorization:v1",
        authorized_scope_hash="hash-1", authorized_subject_ids=["wp-a"],
    )
    result = spine.submit(env)
    assert result.status.value != "rejected"


def test_out_of_scope_subject_rejected(tmp_path):
    grant = _grant()
    spine = _spine(tmp_path, authorization_lookup=lambda ref: grant)
    env = _envelope(
        authorization_ref="objective_plan:opr-1:execution_authorization:v1",
        authorized_scope_hash="hash-1", authorized_subject_ids=["wp-OUTSIDE"],
    )
    result = spine.submit(env)
    assert result.status.value == "rejected"
    assert "not in authorized frontier" in result.rejected_reason


def test_scope_hash_mismatch_rejected(tmp_path):
    grant = _grant(authorized_scope_hash="hash-REAL")
    spine = _spine(tmp_path, authorization_lookup=lambda ref: grant)
    env = _envelope(
        authorization_ref="objective_plan:opr-1:execution_authorization:v1",
        authorized_scope_hash="hash-TAMPERED", authorized_subject_ids=["wp-a"],
    )
    result = spine.submit(env)
    assert result.status.value == "rejected"
    assert "scope hash mismatch" in result.rejected_reason


def test_expired_authorization_rejected(tmp_path):
    grant = _grant(expires_at=time.time() - 1)
    spine = _spine(tmp_path, authorization_lookup=lambda ref: grant)
    env = _envelope(
        authorization_ref="objective_plan:opr-1:execution_authorization:v1",
        authorized_scope_hash="hash-1", authorized_subject_ids=["wp-a"],
    )
    result = spine.submit(env)
    assert result.status.value == "rejected"
    assert "expired" in result.rejected_reason


def test_inactive_grant_rejected(tmp_path):
    grant = _grant(status="revoked")
    spine = _spine(tmp_path, authorization_lookup=lambda ref: grant)
    env = _envelope(
        authorization_ref="objective_plan:opr-1:execution_authorization:v1",
        authorized_scope_hash="hash-1", authorized_subject_ids=["wp-a"],
    )
    result = spine.submit(env)
    assert result.status.value == "rejected"
    assert "not active" in result.rejected_reason
