"""WP-P4-EOS-ACTION-APPROVAL-COMMAND-001 — governed approve/reject seam tests.

Proves the packet's hard constraints:

1. Approve/reject change ONLY approval/status fields (SQL SET clause bounded).
2. Non-pending proposals cannot be approved or rejected (atomic SQL predicate
   + honest invalid_transition reporting).
3. Execution is never invoked; provider APIs are never called; OAuth/token
   fields are never read (source-level scans + runtime fakes).
4. The write goes through governed_mutation and fails closed when governance
   is unavailable.
5. Routes are thin wrappers; response stays flat JSON; execute_enabled=false.
6. source_build_safe required / env-disabled returns safe output; no secrets.
"""

from __future__ import annotations

import ast
import inspect
import json
import os
import sys
from pathlib import Path

_WORKTREE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _WORKTREE not in sys.path:
    sys.path.insert(0, _WORKTREE)

from projections.eos.integration.action_decisions import decide_action_proposal

_ACCESSOR_PATH = Path(_WORKTREE) / "projections" / "eos" / "integration" / "action_decisions.py"
_ROUTES_PATH = Path(_WORKTREE) / "transports" / "api" / "cockpit_core_eos_routes.py"
_SEAM_MAP_PATH = os.path.join(
    _WORKTREE, "data", "umh", "projection_reconciliation", "eos_action_executor_seam_map.json"
)

_ENVELOPE_KEYS = {
    "projection_id",
    "surface",
    "proposal_id",
    "decision",
    "decided_by",
    "reason",
    "connection_status",
    "source_build_safe",
    "execute_enabled",
    "retry_policy",
    "beast_head",
    "seam_id",
    "seam_primitive",
    "seam_target",
    "decision_applied",
    "prior_status",
    "new_status",
    "decided_at",
    "envelope_id",
    "governance_status",
    "error",
}


class _FakeMutationResponse:
    def __init__(
        self, success, output="", envelope_id="env_1", status="completed", rejected_reason=""
    ):
        self.success = success
        self.output = output
        self.envelope_id = envelope_id
        self.status = status
        self.rejected_reason = rejected_reason


def _safe_readiness(monkeypatch, safe: bool = True) -> None:
    import projections.eos.integration.action_seam as seam_mod
    import projections.eos.integration.readiness as readiness_mod

    monkeypatch.setattr(
        readiness_mod,
        "eos_readiness",
        lambda: {"source_build_safe": safe, "beast_head": "9c8725f"},
    )
    monkeypatch.setattr(seam_mod, "_SEAM_MAP_PATH", _SEAM_MAP_PATH)


def _wire_governance(monkeypatch, passthrough=True):
    """Make governed_mutation call execute_fn (spine-approved path) or fail closed."""
    import transports.api.governed as governed_mod

    calls = []

    def fake_governed_mutation(mutation_name, intent, execute_fn, source="", metadata=None, **kw):
        calls.append({"mutation_name": mutation_name, "metadata": metadata or {}})
        if not passthrough:
            return _FakeMutationResponse(
                False,
                status="rejected",
                envelope_id="",
                rejected_reason="control plane unavailable",
            )
        output, ok = execute_fn()
        return _FakeMutationResponse(ok, output=output)

    monkeypatch.setattr(governed_mod, "governed_mutation", fake_governed_mutation)
    return calls


def _wire_db(monkeypatch, update_result, current_status=None):
    """Fake the DB seam: record what the bounded write was asked to do."""
    import projections.eos.integration.tables as tables_mod

    class _FakeConn:
        def close(self):
            pass

    fake_pg = type("_FakePg", (), {"connect": staticmethod(lambda dsn: _FakeConn())})
    monkeypatch.setitem(sys.modules, "psycopg2", fake_pg)

    write_calls = []

    def fake_update(conn, action_id, decision, decided_by, user_ids=None):
        write_calls.append({"action_id": action_id, "decision": decision, "decided_by": decided_by})
        return update_result

    monkeypatch.setattr(tables_mod, "update_action_decision", fake_update)
    monkeypatch.setattr(
        tables_mod,
        "fetch_action_status",
        lambda conn, action_id, user_ids=None: current_status,
    )
    monkeypatch.setenv("EOS_DATABASE_URL", "postgresql://ignored-by-fake")
    return write_calls


_APPROVED_ROW = {
    "id": "action_1",
    "status": "approved",
    "retry_count": 1,
    "max_retries": 3,
    "approved_by": "umh_operator",
    "approved_at": "2026-07-06T12:00:00",
    "updated_at": "2026-07-06T12:00:00",
}


# ── Happy paths: bounded approve / reject ────────────────────────────────────


def test_approve_applies_and_returns_proof(monkeypatch):
    _safe_readiness(monkeypatch)
    _wire_governance(monkeypatch, passthrough=True)
    writes = _wire_db(monkeypatch, dict(_APPROVED_ROW))

    result = decide_action_proposal("action_1", "approve", decided_by="afm", reason="ship it")
    json.dumps(result)
    assert set(result.keys()) == _ENVELOPE_KEYS
    assert result["decision_applied"] is True
    assert result["prior_status"] == "pending"
    assert result["new_status"] == "approved"
    assert result["decided_at"]
    assert result["envelope_id"] == "env_1"
    assert result["execute_enabled"] is False
    assert writes == [{"action_id": "action_1", "decision": "approve", "decided_by": "afm"}]


def test_reject_applies_and_returns_proof(monkeypatch):
    _safe_readiness(monkeypatch)
    _wire_governance(monkeypatch, passthrough=True)
    row = dict(_APPROVED_ROW, status="rejected", approved_by=None, approved_at=None)
    writes = _wire_db(monkeypatch, row)

    result = decide_action_proposal("action_1", "reject")
    assert result["decision_applied"] is True
    assert result["new_status"] == "rejected"
    assert result["execute_enabled"] is False
    assert writes[0]["decision"] == "reject"


def test_retry_and_execution_fields_pass_through_untouched(monkeypatch):
    """The proof echoes retry_count from the row — the write never alters it."""
    _safe_readiness(monkeypatch)
    _wire_governance(monkeypatch, passthrough=True)
    _wire_db(monkeypatch, dict(_APPROVED_ROW, retry_count=2))
    result = decide_action_proposal("action_1", "approve")
    assert result["decision_applied"] is True
    # boundedness is enforced at the SQL layer; see test_update_sql_is_bounded


# ── Invalid transitions ──────────────────────────────────────────────────────


def test_non_pending_proposal_cannot_be_decided(monkeypatch):
    _safe_readiness(monkeypatch)
    _wire_governance(monkeypatch, passthrough=True)
    _wire_db(monkeypatch, None, current_status="completed")

    result = decide_action_proposal("action_1", "approve")
    assert result["decision_applied"] is False
    assert result["prior_status"] == "completed"
    assert result["new_status"] is None
    assert "pending" in (result["error"] or "")


def test_missing_proposal_reports_not_found(monkeypatch):
    _safe_readiness(monkeypatch)
    _wire_governance(monkeypatch, passthrough=True)
    _wire_db(monkeypatch, None, current_status=None)

    result = decide_action_proposal("ghost", "reject")
    assert result["decision_applied"] is False
    assert result["prior_status"] is None
    assert "not found" in (result["error"] or "")


def test_invalid_decision_is_refused(monkeypatch):
    result = decide_action_proposal("action_1", "execute")
    assert result["decision_applied"] is False
    assert result["connection_status"] == "invalid_request"
    result = decide_action_proposal("", "approve")
    assert result["decision_applied"] is False


# ── Gates: build safety, env, governance ─────────────────────────────────────


def test_not_build_safe_blocks_write(monkeypatch):
    _safe_readiness(monkeypatch, safe=False)
    writes = _wire_db(monkeypatch, dict(_APPROVED_ROW))
    result = decide_action_proposal("action_1", "approve")
    assert result["connection_status"] == "source_not_build_safe"
    assert result["decision_applied"] is False
    assert writes == [], "no write may happen when the Beast is not build-safe"


def test_env_disabled_is_safe_disconnected(monkeypatch):
    _safe_readiness(monkeypatch)
    monkeypatch.delenv("EOS_DATABASE_URL", raising=False)
    result = decide_action_proposal("action_1", "approve")
    json.dumps(result)
    assert set(result.keys()) == _ENVELOPE_KEYS
    assert result["connection_status"] == "disconnected"
    assert result["decision_applied"] is False


def test_governance_unavailable_fails_closed(monkeypatch):
    """Daemon down → governed_mutation rejects → no write, honest report."""
    _safe_readiness(monkeypatch)
    _wire_governance(monkeypatch, passthrough=False)
    writes = _wire_db(monkeypatch, dict(_APPROVED_ROW))

    result = decide_action_proposal("action_1", "approve")
    assert result["decision_applied"] is False
    assert result["connection_status"] == "governance_rejected"
    assert "unavailable" in (result["error"] or "")
    assert writes == [], "fail-closed governance must not reach the DB"


def test_write_goes_through_governed_mutation(monkeypatch):
    _safe_readiness(monkeypatch)
    calls = _wire_governance(monkeypatch, passthrough=True)
    _wire_db(monkeypatch, dict(_APPROVED_ROW))
    decide_action_proposal("action_1", "approve", reason="why not")
    assert calls[0]["mutation_name"] == "eos_action_proposal_decision"
    assert calls[0]["metadata"]["reason"] == "why not"
    assert calls[0]["metadata"]["execute_enabled"] is False


# ── Execution / provider / OAuth impossibility ───────────────────────────────


def test_accessor_never_touches_execution_or_providers():
    text = _ACCESSOR_PATH.read_text(encoding="utf-8")
    forbidden = [
        "executeAction",
        "execute_action",
        "sendEmail",
        "send_email(",
        "googleapis",
        "oauth",
        "access_token",
        "refresh_token",
        "adapters.",
        "capability_router",
        "Anthropic(",
        "OpenAI(",
    ]
    for token in forbidden:
        assert token not in text, f"accessor references forbidden execution token {token!r}"


def test_update_sql_is_bounded():
    """The decision UPDATE touches ONLY approval/status fields, atomically."""
    from projections.eos.integration.tables import update_action_decision

    src = inspect.getsource(update_action_decision)
    assert "status = 'pending'" in src, "transition must be atomically guarded on pending"
    # the SET clause may only name these columns
    for forbidden_col in (
        "retry_count =",
        "execution_result",
        "parameters",
        "max_retries =",
        "error_message",
        "executed_at",
        "completed_at",
        "failed_at",
    ):
        assert forbidden_col not in src, f"bounded write must not set {forbidden_col!r}"
    for allowed in ("status = %s", "updated_at = NOW()"):
        assert allowed in src


def test_approved_by_is_fk_safe_app_principal():
    """approved_by must stamp the row's OWN user_id, never a UMH identity.

    agent_actions.approved_by is FK-constrained to the app's users.id
    (agent_actions_approved_by_users_id_fk). Writing the UMH operator
    identity there violated the FK on the first live organic approve
    (action_1783367421127_b0ztpntev). The app's own approve stamps an app
    user id; the seam mirrors that by stamping the row's user_id column
    directly in SQL. The UMH decider stays in the governed envelope only.
    """
    from projections.eos.integration.tables import update_action_decision

    src = inspect.getsource(update_action_decision)
    assert "approved_by = user_id" in src, "approve must stamp the row's own app user_id (FK-safe)"
    assert "approved_by = %s" not in src, "approved_by must never be a caller-supplied parameter"

    captured: dict = {}

    class _Cur:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def execute(self, query, params):
            captured["query"] = query
            captured["params"] = list(params)

        def fetchone(self):
            return None

    class _Conn:
        def cursor(self, cursor_factory=None):
            return _Cur()

        def commit(self):
            pass

    result = update_action_decision(_Conn(), "action_1", "approve", decided_by="umh_operator")
    assert result is None
    assert "umh_operator" not in captured["params"], "UMH identity must not reach the EOS row"
    assert captured["params"] == ["approved", "action_1"]


def test_no_oauth_table_access_in_new_sql():
    from projections.eos.integration.tables import fetch_action_status, update_action_decision

    for fn in (fetch_action_status, update_action_decision):
        src = inspect.getsource(fn)
        assert "oauth" not in src.lower(), f"{fn.__name__} must never touch oauth_tokens"


# ── Route thinness + flatness ────────────────────────────────────────────────


def _post_route_fns():
    tree = ast.parse(_ROUTES_PATH.read_text(encoding="utf-8"))
    fns = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "register_eos_routes":
            for fn in node.body:
                if not isinstance(fn, ast.FunctionDef):
                    continue
                for dec in fn.decorator_list:
                    if (
                        isinstance(dec, ast.Call)
                        and isinstance(dec.func, ast.Attribute)
                        and dec.func.attr == "post"
                        and dec.args
                        and isinstance(dec.args[0], ast.Constant)
                        and "/eos/action-proposals/" in dec.args[0].value
                    ):
                        fns[dec.args[0].value] = fn
    return fns


def test_decision_routes_exist_and_are_thin():
    fns = _post_route_fns()
    decision_routes = {
        "/eos/action-proposals/{proposal_id}/approve",
        "/eos/action-proposals/{proposal_id}/reject",
    }
    # the decision routes must exist; later packets may add sibling
    # action-proposal routes (e.g. /execute per WP-P4-EOS-EXECUTOR-ACTIVATE-001)
    # with their own thinness tests.
    assert decision_routes <= set(fns)
    for route in sorted(decision_routes):
        fn = fns[route]
        # thin: body is a single return delegating to the shared helper
        assert len(fn.body) == 2 and isinstance(fn.body[1], ast.Return), (
            f"{route} must be a one-line delegation after its docstring"
        )
        # no inline construction in the body (decorator Depends excluded)
        for stmt in fn.body:
            for n in ast.walk(stmt):
                if isinstance(n, ast.Call):
                    f = n.func
                    name = (
                        f.id
                        if isinstance(f, ast.Name)
                        else (f.attr if isinstance(f, ast.Attribute) else "")
                    )
                    assert not (name and name[0].isupper()), f"{route} constructs {name} inline"


def test_shared_route_body_is_thin_wrapper():
    tree = ast.parse(_ROUTES_PATH.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "_decide_proposal":
            assert any(
                isinstance(n, ast.ImportFrom)
                and (n.module or "") == "projections.eos.integration.action_decisions"
                for n in ast.walk(node)
            ), "_decide_proposal must lazy-import the accessor"
            assert any(
                isinstance(n, ast.ImportFrom) and (n.module or "") == "transports.api.governed"
                for n in ast.walk(node)
            ), "_decide_proposal must wire the canonical governed_mutation (C34)"
            assert any(isinstance(n, ast.Try) for n in node.body), "must never raise"
            return
    raise AssertionError("_decide_proposal helper not found")


def test_response_is_flat_json(monkeypatch):
    _safe_readiness(monkeypatch)
    _wire_governance(monkeypatch, passthrough=True)
    _wire_db(monkeypatch, dict(_APPROVED_ROW))
    result = decide_action_proposal("action_1", "approve")
    json.dumps(result)
    for k, v in result.items():
        assert not isinstance(v, (list, dict)), f"envelope key {k} is not flat"


# ── No secrets / EOS-only ────────────────────────────────────────────────────


def test_no_secrets_in_output(monkeypatch):
    import re

    _safe_readiness(monkeypatch)
    _wire_governance(monkeypatch, passthrough=True)
    _wire_db(monkeypatch, dict(_APPROVED_ROW))
    raw = json.dumps(decide_action_proposal("action_1", "approve"))
    for pattern in (
        r"postgres(?:ql)?://",
        r"sk-ant-[A-Za-z0-9_-]{10,}",
        r"-----BEGIN [A-Z ]*PRIVATE KEY-----",
        r"ya29\.[A-Za-z0-9_-]{20,}",
    ):
        assert not re.search(pattern, raw), f"secret-like value matches {pattern}"


def test_only_eos_is_touched(monkeypatch):
    text = _ACCESSOR_PATH.read_text(encoding="utf-8").lower()
    for name in ("creatoros", "lyfeos", "crm_"):
        assert name not in text, f"accessor references {name!r}"


# ── WP-P4-FIRST-LIVE-PROPOSAL-PROOF-001 — live-run regression ─────────────────
#
# The first live proposal run (2026-07-06) surfaced that both EOS seam mutation
# names were UNREGISTERED in the canonical MutationRegistry: every fake
# mutation_runner in this suite accepted them, but the real governed spine
# fail-closed with "unregistered mutation: eos_action_proposal_decision" and
# no decision could ever be applied in production. These tests pin the real
# registry — not a fake — so the gap can never silently reopen.


def test_decision_mutation_is_registered_in_real_registry():
    from substrate.organism.mutation_registry import MutationRegistry

    reg = MutationRegistry()
    spec = reg.lookup("eos_action_proposal_decision")
    assert spec is not None, (
        "eos_action_proposal_decision missing from MutationRegistry builtins — "
        "the governed approve/reject seam fail-closes on every live call"
    )
    assert spec.risk_level == "medium"
    assert spec.require_approval is False  # operator already authenticated at the route


def test_execute_mutation_is_registered_in_real_registry():
    from substrate.organism.mutation_registry import MutationRegistry

    reg = MutationRegistry()
    spec = reg.lookup("eos_action_proposal_execute")
    assert spec is not None, (
        "eos_action_proposal_execute missing from MutationRegistry builtins — "
        "the governed executor seam fail-closes on every live call"
    )
    assert spec.risk_level == "medium"
    assert spec.require_approval is False


def test_registered_names_match_seam_call_sites():
    """The literal mutation_name each seam submits must be the registered name."""
    from substrate.organism.mutation_registry import MutationRegistry

    reg = MutationRegistry()
    decisions_src = _ACCESSOR_PATH.read_text(encoding="utf-8")
    assert 'mutation_name="eos_action_proposal_decision"' in decisions_src
    execution_src = (
        Path(_WORKTREE) / "projections" / "eos" / "integration" / "action_execution.py"
    ).read_text(encoding="utf-8")
    assert 'mutation_name="eos_action_proposal_execute"' in execution_src
    for name in ("eos_action_proposal_decision", "eos_action_proposal_execute"):
        assert reg.is_registered(name)
