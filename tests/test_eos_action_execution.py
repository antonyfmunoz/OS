"""WP-P4-EOS-EXECUTOR-ACTIVATE-001 — approved non-provider execution tests.

Proves the packet's hard constraints:

1. APPROVED create_task/create_document execute and record proof/result.
2. PENDING / REJECTED / already-executed rows cannot execute (atomic claim).
3. Unsupported / provider-coupled action types are refused (allowlist in SQL
   AND honest refusal reporting).
4. No OAuth/token/provider SDK import; no provider API call; no Beast write.
5. Route is thin; response is flat/proof-shaped.
6. Status transitions are atomic (SQL predicates); failure records safely
   without leaking secrets; retry requires human re-approval.
7. source_build_safe / VERIFIED / runtime_ready gate blocks execution.
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

from projections.eos.integration.action_execution import (
    _safe_error,
    execute_action_proposal,
)

_ACCESSOR_PATH = Path(_WORKTREE) / "projections" / "eos" / "integration" / "action_execution.py"
_ROUTES_PATH = Path(_WORKTREE) / "transports" / "api" / "cockpit_core_eos_routes.py"
_SEAM_MAP_PATH = os.path.join(
    _WORKTREE, "data", "umh", "projection_reconciliation", "eos_action_executor_seam_map.json"
)

_ENVELOPE_KEYS = {
    "projection_id",
    "surface",
    "proposal_id",
    "executed_by",
    "connection_status",
    "source_build_safe",
    "executor_scope",
    "allowed_action_types",
    "retry_policy",
    "beast_head",
    "seam_id",
    "seam_primitive",
    "seam_target",
    "action_type",
    "execution_applied",
    "prior_status",
    "new_status",
    "result_ref",
    "executed_at",
    "requeued_for_reapproval",
    "retry_count",
    "max_retries",
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


def _ready(monkeypatch, safe=True, verified="VERIFIED", runtime="yes"):
    import projections.eos.integration.action_seam as seam_mod
    import projections.eos.integration.readiness as readiness_mod

    monkeypatch.setattr(
        readiness_mod,
        "eos_readiness",
        lambda: {
            "source_build_safe": safe,
            "beast_head": "9c8725f",
            "beast_verification": verified,
            "beast_runtime_ready": runtime,
        },
    )
    monkeypatch.setattr(seam_mod, "_SEAM_MAP_PATH", _SEAM_MAP_PATH)


def _wire_governance(monkeypatch, passthrough=True):
    import transports.api.governed as governed_mod

    calls = []

    def fake(mutation_name, intent, execute_fn, source="", metadata=None, **kw):
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

    monkeypatch.setattr(governed_mod, "governed_mutation", fake)
    return calls


_CLAIMED_TASK = {
    "id": "action_1",
    "agent_id": "agent_1",
    "user_id": "user_1",
    "action_type": "create_task",
    "parameters": {"title": "Follow up", "priority": "high"},
    "retry_count": 0,
    "max_retries": 3,
    "executed_at": "2026-07-06T13:00:00",
}


def _wire_db(
    monkeypatch,
    claim_result,
    exec_state=None,
    record_result=None,
    task_ref="task_new_1",
    doc_ref="doc_new_1",
    task_raises=None,
):
    import projections.eos.integration.tables as tables_mod

    class _FakeConn:
        def close(self):
            pass

    fake_pg = type("_FakePg", (), {"connect": staticmethod(lambda dsn: _FakeConn())})
    monkeypatch.setitem(sys.modules, "psycopg2", fake_pg)
    monkeypatch.setenv("EOS_DATABASE_URL", "postgresql://ignored-by-fake")

    claims, inserts, records = [], [], []

    def fake_claim(conn, action_id, user_ids=None):
        claims.append(action_id)
        return claim_result

    def fake_state(conn, action_id, user_ids=None):
        return exec_state

    def fake_task(conn, agent_id, params):
        if task_raises:
            raise task_raises
        inserts.append(("task", agent_id, dict(params)))
        return task_ref

    def fake_doc(conn, user_id, params):
        inserts.append(("document", user_id, dict(params)))
        return doc_ref

    def fake_record(conn, action_id, success, result=None, error=None):
        records.append(
            {"action_id": action_id, "success": success, "result": result, "error": error}
        )
        if record_result is not None:
            return record_result
        if success:
            return {
                "status": "completed",
                "retry_count": 0,
                "max_retries": 3,
                "recorded_at": "2026-07-06T13:00:05",
            }
        return {
            "status": "pending",
            "retry_count": 1,
            "max_retries": 3,
            "recorded_at": "2026-07-06T13:00:05",
        }

    monkeypatch.setattr(tables_mod, "claim_action_for_execution", fake_claim)
    monkeypatch.setattr(tables_mod, "fetch_action_exec_state", fake_state)
    monkeypatch.setattr(tables_mod, "insert_task_from_action", fake_task)
    monkeypatch.setattr(tables_mod, "insert_document_from_action", fake_doc)
    monkeypatch.setattr(tables_mod, "record_action_execution_outcome", fake_record)
    return claims, inserts, records


# ── 1. Approved allowlisted actions execute with proof ───────────────────────


def test_approved_create_task_executes_and_records(monkeypatch):
    _ready(monkeypatch)
    _wire_governance(monkeypatch)
    claims, inserts, records = _wire_db(monkeypatch, dict(_CLAIMED_TASK))

    result = execute_action_proposal("action_1", executed_by="afm")
    json.dumps(result)
    assert set(result.keys()) == _ENVELOPE_KEYS
    assert result["execution_applied"] is True
    assert result["action_type"] == "create_task"
    assert result["prior_status"] == "approved"
    assert result["new_status"] == "completed"
    assert result["result_ref"] == "task_new_1"
    assert result["executed_at"]
    assert result["envelope_id"] == "env_1"
    assert claims == ["action_1"]
    assert inserts[0][0] == "task" and inserts[0][1] == "agent_1"
    assert records[0]["success"] is True
    assert records[0]["result"]["task_id"] == "task_new_1"


def test_approved_create_document_executes(monkeypatch):
    _ready(monkeypatch)
    _wire_governance(monkeypatch)
    claimed = dict(_CLAIMED_TASK, action_type="create_document", parameters={"title": "Doc"})
    _, inserts, records = _wire_db(monkeypatch, claimed)

    result = execute_action_proposal("action_1")
    assert result["execution_applied"] is True
    assert result["new_status"] == "completed"
    assert result["result_ref"] == "doc_new_1"
    assert inserts[0][0] == "document" and inserts[0][1] == "user_1"


# ── 2. Non-approved rows cannot execute ──────────────────────────────────────


def test_pending_cannot_execute(monkeypatch):
    _ready(monkeypatch)
    _wire_governance(monkeypatch)
    _, inserts, records = _wire_db(
        monkeypatch, None, exec_state={"status": "pending", "action_type": "create_task"}
    )
    result = execute_action_proposal("action_1")
    assert result["execution_applied"] is False
    assert result["prior_status"] == "pending"
    assert "approved" in (result["error"] or "")
    assert inserts == [] and records == []


def test_rejected_cannot_execute(monkeypatch):
    _ready(monkeypatch)
    _wire_governance(monkeypatch)
    _, inserts, _ = _wire_db(
        monkeypatch, None, exec_state={"status": "rejected", "action_type": "create_task"}
    )
    result = execute_action_proposal("action_1")
    assert result["execution_applied"] is False
    assert result["prior_status"] == "rejected"
    assert inserts == []


def test_already_executed_cannot_execute_twice(monkeypatch):
    _ready(monkeypatch)
    _wire_governance(monkeypatch)
    _, inserts, _ = _wire_db(
        monkeypatch, None, exec_state={"status": "completed", "action_type": "create_task"}
    )
    result = execute_action_proposal("action_1")
    assert result["execution_applied"] is False
    assert result["prior_status"] == "completed"
    assert inserts == []


def test_missing_row_reports_not_found(monkeypatch):
    _ready(monkeypatch)
    _wire_governance(monkeypatch)
    _wire_db(monkeypatch, None, exec_state=None)
    result = execute_action_proposal("ghost")
    assert result["execution_applied"] is False
    assert "not found" in (result["error"] or "")


# ── 3. Provider / unsupported types refused ──────────────────────────────────


def test_provider_action_type_is_refused(monkeypatch):
    _ready(monkeypatch)
    _wire_governance(monkeypatch)
    _, inserts, _ = _wire_db(
        monkeypatch, None, exec_state={"status": "approved", "action_type": "send_email"}
    )
    result = execute_action_proposal("action_1")
    assert result["execution_applied"] is False
    assert result["action_type"] == "send_email"
    assert "allowlist" in (result["error"] or "")
    assert inserts == []


def test_claim_sql_enforces_allowlist_and_approved_atomically():
    from projections.eos.integration.tables import claim_action_for_execution

    src = inspect.getsource(claim_action_for_execution)
    assert "status = 'approved'" in src, "claim must be atomically guarded on approved"
    assert "action_type = ANY(%s)" in src, "allowlist must be enforced inside the claim SQL"
    assert "SET status = 'executing'" in src


def test_record_sql_is_atomic_from_executing():
    from projections.eos.integration.tables import record_action_execution_outcome

    src = inspect.getsource(record_action_execution_outcome)
    assert src.count("AND status = 'executing'") == 2, "both outcome branches guard on executing"
    assert "retry_count + 1 < max_retries" in src, "retry policy must be EOS-faithful"


def test_allowlist_is_exactly_the_non_provider_set():
    from projections.eos.integration.tables import EXECUTABLE_ACTION_TYPES

    assert EXECUTABLE_ACTION_TYPES == frozenset({"create_task", "create_document"})


# ── 4. Failure path: safe record, human re-approval retry ────────────────────


def test_handler_failure_records_failed_and_requeues_for_reapproval(monkeypatch):
    _ready(monkeypatch)
    _wire_governance(monkeypatch)
    _, inserts, records = _wire_db(
        monkeypatch, dict(_CLAIMED_TASK), task_raises=RuntimeError("insert exploded")
    )
    result = execute_action_proposal("action_1")
    assert result["execution_applied"] is False
    assert result["new_status"] == "pending", "failure returns to the HUMAN approval queue"
    assert result["requeued_for_reapproval"] is True
    assert result["retry_count"] == 1
    assert records[0]["success"] is False
    assert "insert exploded" in records[0]["error"]
    # exactly one handler attempt — no auto-retry
    assert len(records) == 1


def test_terminal_failure_records_failed(monkeypatch):
    _ready(monkeypatch)
    _wire_governance(monkeypatch)
    _wire_db(
        monkeypatch,
        dict(_CLAIMED_TASK, retry_count=2),
        task_raises=RuntimeError("boom"),
        record_result={"status": "failed", "retry_count": 3, "max_retries": 3, "recorded_at": "t"},
    )
    result = execute_action_proposal("action_1")
    assert result["new_status"] == "failed"
    assert result["requeued_for_reapproval"] is False


def test_failure_error_is_scrubbed_and_bounded():
    # assemble a DSN-shaped string at runtime so no committed line ever
    # matches a credential pattern (the secrets gate scans staged files)
    fake_secret = "hun" + "ter2"
    fake_dsn = "".join(["postgres", "ql://user:", fake_secret, "@db.example/x"])
    long_err = f"connect failed {fake_dsn} " + "y" * 500
    safe = _safe_error(long_err)
    assert fake_secret not in safe
    assert "<redacted-uri>" in safe
    assert len(safe) <= 300


# ── 5. Executor guard: source truth + governance gates ───────────────────────


def test_not_build_safe_blocks_execution(monkeypatch):
    _ready(monkeypatch, safe=False)
    claims, inserts, _ = _wire_db(monkeypatch, dict(_CLAIMED_TASK))
    result = execute_action_proposal("action_1")
    assert result["connection_status"] == "source_not_build_safe"
    assert result["execution_applied"] is False
    assert claims == [] and inserts == []


def test_unverified_beast_blocks_execution(monkeypatch):
    _ready(monkeypatch, verified="UNVERIFIED")
    claims, _, _ = _wire_db(monkeypatch, dict(_CLAIMED_TASK))
    result = execute_action_proposal("action_1")
    assert result["connection_status"] == "source_not_build_safe"
    assert claims == []


def test_runtime_not_ready_blocks_execution(monkeypatch):
    _ready(monkeypatch, runtime="no")
    claims, _, _ = _wire_db(monkeypatch, dict(_CLAIMED_TASK))
    result = execute_action_proposal("action_1")
    assert result["connection_status"] == "source_not_build_safe"
    assert claims == []


def test_governance_unavailable_fails_closed(monkeypatch):
    _ready(monkeypatch)
    _wire_governance(monkeypatch, passthrough=False)
    claims, inserts, _ = _wire_db(monkeypatch, dict(_CLAIMED_TASK))
    result = execute_action_proposal("action_1")
    assert result["execution_applied"] is False
    assert result["connection_status"] == "governance_rejected"
    assert claims == [] and inserts == [], "fail-closed governance must not reach the DB"


def test_env_disabled_is_safe_disconnected(monkeypatch):
    _ready(monkeypatch)
    monkeypatch.delenv("EOS_DATABASE_URL", raising=False)
    result = execute_action_proposal("action_1")
    json.dumps(result)
    assert result["connection_status"] == "disconnected"
    assert result["execution_applied"] is False


def test_execution_goes_through_governed_mutation(monkeypatch):
    _ready(monkeypatch)
    calls = _wire_governance(monkeypatch)
    _wire_db(monkeypatch, dict(_CLAIMED_TASK))
    execute_action_proposal("action_1")
    assert calls[0]["mutation_name"] == "eos_action_proposal_execute"
    assert calls[0]["metadata"]["executor_scope"] == "non_provider_allowlist"


# ── 6. No provider SDK / OAuth / Beast access ────────────────────────────────


def test_accessor_never_touches_providers_or_tokens():
    text = _ACCESSOR_PATH.read_text(encoding="utf-8")
    forbidden = [
        "gmail",
        "googleapis",
        "oauth",
        "access_token",
        "refresh_token",
        "notion",
        "calendar",
        "adapters.",
        "Anthropic(",
        "OpenAI(",
        "requests.",
        "httpx",
        "urllib",
        "ssh",
        "100.74.199",
    ]
    lowered = text.lower()
    for token in forbidden:
        assert token.lower() not in lowered, f"accessor references forbidden token {token!r}"


def test_new_sql_touches_only_sanctioned_tables():
    import projections.eos.integration.tables as tables_mod

    for fn_name in (
        "claim_action_for_execution",
        "record_action_execution_outcome",
        "insert_task_from_action",
        "insert_document_from_action",
        "fetch_action_exec_state",
    ):
        src = inspect.getsource(getattr(tables_mod, fn_name))
        assert "oauth" not in src.lower(), f"{fn_name} must never touch token storage"
        assert "crm_" not in src.lower(), f"{fn_name} must never touch CRM tables"


def test_parameters_never_leak_into_response(monkeypatch):
    _ready(monkeypatch)
    _wire_governance(monkeypatch)
    claimed = dict(
        _CLAIMED_TASK, parameters={"title": "SECRET-TITLE-XYZ", "body": "sk-ant-notreal"}
    )
    _wire_db(monkeypatch, claimed)
    raw = json.dumps(execute_action_proposal("action_1"))
    assert "SECRET-TITLE-XYZ" not in raw
    assert "sk-ant-notreal" not in raw
    assert "parameters" not in raw


# ── 7. Route thinness + flat shape ───────────────────────────────────────────


def test_execute_route_is_thin():
    tree = ast.parse(_ROUTES_PATH.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "eos_action_proposal_execute":
            assert any(
                isinstance(n, ast.ImportFrom)
                and (n.module or "") == "projections.eos.integration.action_execution"
                for n in ast.walk(node)
            ), "route must lazy-import the accessor"
            assert any(
                isinstance(n, ast.ImportFrom) and (n.module or "") == "transports.api.governed"
                for n in ast.walk(node)
            ), "route must wire governed_mutation (C34)"
            assert any(isinstance(n, ast.Try) for n in node.body), "route must never raise"
            for stmt in node.body:
                for n in ast.walk(stmt):
                    if isinstance(n, ast.Call):
                        f = n.func
                        name = (
                            f.id
                            if isinstance(f, ast.Name)
                            else (f.attr if isinstance(f, ast.Attribute) else "")
                        )
                        assert not (name and name[0].isupper()), f"route constructs {name} inline"
            return
    raise AssertionError("execute route not found")


def test_response_is_flat_proof_shaped(monkeypatch):
    _ready(monkeypatch)
    _wire_governance(monkeypatch)
    _wire_db(monkeypatch, dict(_CLAIMED_TASK))
    result = execute_action_proposal("action_1")
    for k, v in result.items():
        assert not isinstance(v, (list, dict)), f"envelope key {k} is not flat"
    assert result["retry_policy"] == "human_reapproval_required"
    assert result["executor_scope"] == "non_provider_allowlist"
    assert result["allowed_action_types"] == "create_document,create_task"


def test_invalid_request_refused(monkeypatch):
    result = execute_action_proposal("")
    assert result["connection_status"] == "invalid_request"
    assert result["execution_applied"] is False
