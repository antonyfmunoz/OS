"""Wave 2 — the worker prompt carries the actual task spec (seventh layer).

Field run 20260725T210642Z reached the FURTHEST point: the full governed path
executed end-to-end and two real Claude CLI workers ran under bwrap isolation —
but both produced ``files=0`` and failed verification. Root cause:
``render_prompt`` compiled the task spec into the package's ``ordered_context``
and then DROPPED it (it accumulated the sections into a local ``frame`` dict that
was never appended to the prompt). The worker literally received only
"Execute task <id> per the objective contract" with no description of what to
build. This pins the fix: the rendered prompt MUST contain the task's
title/intent/desired-end-state/constraints so a worker can implement it.
"""

from __future__ import annotations

import os
import sys
from types import SimpleNamespace

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

from substrate.execution.attempts.dispatch import compile_attempt_package
from substrate.execution.attempts.worker_claude_cli import render_prompt


def _pkg():
    packet = SimpleNamespace(
        packet_id="wp-test",
        title="Add note search",
        user_intent="Add a backend search endpoint and a frontend search box.",
        desired_end_state="GET /api/notes/search?q= returns matching notes.",
        constraints=["diff confined to app/main.py, tests/test_search_api.py"],
        validation_plan="pytest tests/test_search_api.py green",
    )
    attempt = SimpleNamespace(
        task_id="wp-test",
        attempt_id="ea-test",
        plan_record_id="opr-1",
        plan_version=1,
        execution_authorization_ref="objective_plan:opr-1:execution_authorization:v1",
        timeout_seconds=600,
        max_turns=30,
    )
    assignment = SimpleNamespace(
        role_contract_id="role-impl",
        skill_requirement_refs=[],
        tool_profile=["shell", "edit"],
        model_profile={"model": "claude-opus"},
        environment_class="git_worktree",
    )
    grant = SimpleNamespace(
        tenant_id="tenant-a",
        decision_ref="objective_plan:opr-1:execution_authorization:v1",
        authorized_scope_hash="h",
        risk_ceiling="high",
        task_frontier=["wp-test"],
        verification_obligations=["verify"],
        cost_limit_usd=0.0,
        cost_enforceable=False,
    )
    return compile_attempt_package(
        attempt=attempt, packet=packet, assignment=assignment, grant=grant
    )


def test_prompt_includes_task_title_and_intent():
    prompt = render_prompt(_pkg())
    assert "Add note search" in prompt, "worker prompt must carry the task title"
    assert "search endpoint" in prompt, "worker prompt must carry the task intent"


def test_prompt_includes_desired_end_state_and_constraints():
    prompt = render_prompt(_pkg())
    assert "/api/notes/search" in prompt, "prompt must carry the desired end state"
    assert "app/main.py" in prompt, "prompt must carry the scope constraints"


def test_prompt_is_not_only_the_boilerplate_shell():
    """Regression on the exact field symptom: the prompt must be more than the
    'Execute task <id> ... Make the change' shell that produced files=0."""
    prompt = render_prompt(_pkg())
    # The task-spec section must be present, not just the identity + trailer.
    assert "Context Frame" in prompt or "intent:" in prompt, (
        "the ordered_context task spec must be rendered, not dropped"
    )
    # And it must be substantive (the field failure prompt was ~180 chars).
    assert len(prompt) > 300, "a real task prompt carries the spec, not just the id"
