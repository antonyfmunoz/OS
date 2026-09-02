"""Wave 2 C1 — convergence gates (hard prohibitions).

Mechanical guards that keep the canonical execution slice from re-growing the
rivals it converged. All checks are source/AST-level so they hold without a live
runtime.

Prohibitions enforced (Wave 2 Amendment v1 + plan §V/§XVI):
- attempts/* imports none of the legacy execution rivals;
- no default fake-success executor reachable on the canonical path;
- no canonical-execution fallback to coordinator dispatch_next();
- no target_executor="simulation" DEFAULT on canonical entry points;
- no new execution-lifecycle JSONL authority (only the shared EventSpine);
- WorkcellDaemon is not wired as a production supervisor;
- ExecutionAuthorizationGrant carries no second Decision lifecycle
  (no requested/denied grant state).
"""

from __future__ import annotations

import ast
import pathlib

import pytest

REPO = pathlib.Path(__file__).resolve().parents[1]
ATTEMPTS_DIR = REPO / "substrate" / "execution" / "attempts"

# The legacy execution rivals attempts/* must never import.
_FORBIDDEN_IMPORTS = (
    "substrate.organism.execution_coordinator",
    "substrate.organism.executor_runtime",
    "substrate.organism.plan_execution_adapter",
    "substrate.organism.composition_engine",
    "substrate.organism.governed_work_runtime",
)


def _py_files(root: pathlib.Path) -> list[pathlib.Path]:
    return [p for p in root.rglob("*.py") if "__pycache__" not in p.parts]


def _imported_modules(path: pathlib.Path) -> set[str]:
    tree = ast.parse(path.read_text(), filename=str(path))
    mods: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                mods.add(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module and node.level == 0:
                mods.add(node.module)
    return mods


# ── Import law ───────────────────────────────────────────────────────────────


def test_attempts_package_never_imports_legacy_rivals():
    offenders: list[str] = []
    for path in _py_files(ATTEMPTS_DIR):
        mods = _imported_modules(path)
        for forbidden in _FORBIDDEN_IMPORTS:
            if any(m == forbidden or m.startswith(forbidden + ".") for m in mods):
                offenders.append(f"{path.relative_to(REPO)} imports {forbidden}")
    assert not offenders, "attempts/* imported a legacy execution rival:\n" + "\n".join(offenders)


def test_attempts_package_imports_are_downward_only():
    """attempts/* must not import transports/ services/ (dependency direction)."""
    offenders: list[str] = []
    for path in _py_files(ATTEMPTS_DIR):
        for m in _imported_modules(path):
            if m.startswith(("transports.", "services.")):
                offenders.append(f"{path.relative_to(REPO)} imports {m}")
    assert not offenders, "attempts/* imported an upward layer:\n" + "\n".join(offenders)


# ── No fake executor / no simulation default on canonical entry points ───────


def test_no_default_fake_execute_in_plan_execution_adapter():
    path = REPO / "substrate" / "organism" / "plan_execution_adapter.py"
    tree = ast.parse(path.read_text())
    # No FUNCTION named _default_execute may be DEFINED (a docstring that names
    # the removed stub is fine — a live definition is not).
    defined = {
        n.name for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
    }
    assert "_default_execute" not in defined, (
        "plan_execution_adapter must not define a default fake-success executor"
    )
    assert "PlanExecutionAdapterError" in path.read_text(), (
        "plan_execution_adapter must raise when no executor is bound"
    )


def test_no_simulation_default_on_canonical_entry_points():
    """submit_work / operator decide / cockpit work-submit must not default the
    target executor to the fake 'simulation'."""
    gwr = (REPO / "substrate" / "organism" / "governed_work_runtime.py").read_text()
    assert 'target_executor: str = "simulation"' not in gwr
    olr = (REPO / "substrate" / "organism" / "operator_loop_runtime.py").read_text()
    assert 'target_executor: str = "simulation"' not in olr
    route = (REPO / "transports" / "api" / "cockpit_work_center_routes.py").read_text()
    assert 'body.get("target_executor", "simulation")' not in route


def test_no_coordinator_dispatch_fallback_in_execute_work():
    """execute_work must not silently fall back to coordinator dispatch_next()."""
    src = (REPO / "substrate" / "organism" / "governed_work_runtime.py").read_text()
    tree = ast.parse(src)

    def _find(fn_name):
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == fn_name:
                return node
        return None

    execute_work = _find("execute_work")
    assert execute_work is not None
    calls = [
        n
        for n in ast.walk(execute_work)
        if isinstance(n, ast.Call)
        and isinstance(n.func, ast.Attribute)
        and n.func.attr == "dispatch_next"
    ]
    assert not calls, "execute_work must not call dispatch_next() (fail-closed, no fallback)"


# ── No new execution-lifecycle JSONL authority ───────────────────────────────


def test_attempts_events_use_only_shared_event_spine():
    """The execution events module emits on the ONE shared EventSpine — it must
    not open its own JSONL event log. (Checked at the AST level so descriptive
    docstrings that merely name the spine's file don't trip the gate.)"""
    path = ATTEMPTS_DIR / "events.py"
    src = path.read_text()
    assert "get_shared_event_spine" in src
    tree = ast.parse(src)
    # No open()/write calls in the events module — it only emits on the spine.
    open_calls = [
        n
        for n in ast.walk(tree)
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == "open"
    ]
    assert not open_calls, "attempts/events.py must not open files — emit on the shared spine only"


def test_attempts_store_files_are_ledgers_not_event_authority():
    """The attempt store persists attempt/grant/lease/readiness ledgers — none
    of which is an *event* lifecycle authority (events live on the spine)."""
    src = (ATTEMPTS_DIR / "store.py").read_text()
    # The store's JSONL files are state ledgers, not an events.jsonl authority.
    assert "organism_events.jsonl" not in src
    assert "lifecycle/events.jsonl" not in src


# ── WorkcellDaemon not wired as a production supervisor ──────────────────────


def test_attempts_do_not_wire_workcell_daemon_supervisor():
    for path in _py_files(ATTEMPTS_DIR):
        src = path.read_text()
        assert "WorkcellDaemon" not in src, (
            f"{path.relative_to(REPO)} references WorkcellDaemon — Wave 2 does not "
            f"wire it as a persistent supervisor (Wave 3 boundary)"
        )


# ── No second Decision lifecycle inside the grant ────────────────────────────


def test_grant_has_no_requested_or_denied_state():
    from substrate.execution.attempts.records import ExecutionAuthorizationGrantStatus

    values = {s.value for s in ExecutionAuthorizationGrantStatus}
    assert "requested" not in values and "denied" not in values, (
        "ExecutionAuthorizationGrant must not carry pending/rejected Decision "
        "state — ApprovalRequest is the sole Decision authority"
    )


def test_grant_docstring_declares_it_is_not_a_decision():
    src = (ATTEMPTS_DIR / "records.py").read_text()
    assert "NOT a Decision" in src or "not a Decision" in src.replace("NOT", "not")


# ── R3: ONE admission authority (finding R2-5) ─────────────────────────────


def test_scheduler_binds_the_canonical_admission_symbol():
    """The scheduler must bind THE canonical authority, not a rival copy.

    This is a BINDING check only — it deliberately no longer claims to be
    behavioral. `hasattr` + symbol identity both hold for a module that imports
    a function and never calls it, which is EXACTLY the R2-5 shape
    (`evaluate_execution_readiness` was defined, exported, and never called).
    A gate that cannot detect the defect it is named for is worse than no gate
    (adversarial review F4). Consumption is proven by
    `test_admission_verdict_is_actually_consumed` below.
    """
    from substrate.execution.attempts import admission, scheduler

    assert hasattr(scheduler, "authorize_admission"), (
        "the scheduler does not import the admission authority — admission is "
        "being decided somewhere else, which is how R2-5 happened"
    )
    assert scheduler.authorize_admission is admission.authorize_admission, (
        "the scheduler is bound to a DIFFERENT authorize_admission than the "
        "canonical one — a rival admission authority exists"
    )


def test_admission_verdict_is_actually_consumed(tmp_path, monkeypatch):
    """The scheduler must CALL the authority and HONOUR its refusal.

    Genuinely behavioral: a recording stub replaces the authority and returns a
    REFUSAL for otherwise-valid work. If the scheduler merely imports the
    symbol (the R2-5 shape) the stub is never invoked; if it calls but ignores
    the verdict (the R2-1 shape) the attempt is admitted anyway. Both fail here.
    """
    from types import SimpleNamespace

    from substrate.execution.attempts import scheduler as sched_mod
    from substrate.execution.attempts.admission import AdmissionVerdict
    from substrate.execution.attempts.records import (
        ExecutionAttempt,
        ExecutionAuthorizationGrant,
    )
    from substrate.execution.attempts.store import ExecutionAttemptStore

    store = ExecutionAttemptStore(
        attempts_path=str(tmp_path / "a.jsonl"),
        grants_path=str(tmp_path / "g.jsonl"),
        readiness_path=str(tmp_path / "r.jsonl"),
        leases_path=str(tmp_path / "l.jsonl"),
        assignments_path=str(tmp_path / "asn.jsonl"),
    )
    packet = SimpleNamespace(
        packet_id="T",
        status=SimpleNamespace(value="approved"),
        dependencies=[],
        work_scope={"tenant_id": "t", "target_kind": "k"},
        lineage={"plan_record_id": "p"},
        requirements={},
        validation_plan="v",
        required_tools=[],
        rollback_plan="",
    )
    grant = ExecutionAuthorizationGrant(
        decision_ref="r",
        tenant_id="t",
        plan_record_id="p",
        plan_version=1,
        task_frontier=["T"],
        objective_id="g",
        max_attempts_per_task=2,
        environment_classes=["git_worktree"],
        verification_obligations=["v"],
    )
    grant.status = "active"
    created, _ = store.create_grant_idempotent(grant)
    att, _ = store.create_attempt_idempotent(
        ExecutionAttempt(
            task_id="T",
            plan_record_id="p",
            plan_version=1,
            execution_authorization_ref="r",
            attempt_number=1,
            tenant_id="t",
        )
    )
    store.transition_cas(
        att.attempt_id,
        "ready",
        expected_record_version=att.record_version,
        expected_statuses=("created",),
        actor="test",
        reason="ready",
    )

    calls: list[str] = []
    leased: list[str] = []

    def _recording_refusal(**kw):
        calls.append(kw["attempt"].attempt_id)
        return AdmissionVerdict(
            admitted=False,
            task_id=kw["attempt"].task_id,
            attempt_id=kw["attempt"].attempt_id,
            refusal_code="stub_refusal",
            reason="stub refusal",
        )

    monkeypatch.setattr(sched_mod, "authorize_admission", _recording_refusal)

    def _permit(**kw):
        fn = kw.get("execute_fn")
        out, ok = fn() if fn else ("", True)
        return SimpleNamespace(success=ok, output=out)

    s = sched_mod.AttemptScheduler(
        store,
        work_queue=SimpleNamespace(get_packet=lambda p: packet if p == "T" else None),
        placement_fn=lambda **kw: SimpleNamespace(
            assignment_id="as",
            worker_identity="w",
            verifier_role_id="role-verify-op",
            tool_profile=[],
            model_profile={},
            environment_class="git_worktree",
        ),
        lease_manager=SimpleNamespace(
            acquire=lambda **kw: (
                leased.append(kw["attempt"].attempt_id)
                or SimpleNamespace(lease_id="L", worktree_path=str(tmp_path), base_commit="c")
            ),
            release=lambda *a, **k: None,
        ),
        compile_fn=lambda **kw: SimpleNamespace(package_hash="h"),
        dispatch_fn=lambda **kw: None,
        mutation_runner=_permit,
        lock_dir=str(tmp_path / "locks"),
        latest_plan_lookup=lambda _o: SimpleNamespace(
            plan_record_id="p", status="approved"
        ),
    )
    report = s.run_scheduler_pass(
        created,
        role_resolver=lambda p: SimpleNamespace(
            role_id="role-impl-op",
            allowed_tools=["shell"],
            permitted_skill_ids=[],
            prohibited_skill_ids=[],
        ),
        verifier_role_resolver=lambda p: "role-verify-op",
    )

    assert calls, (
        "the scheduler never CALLED the admission authority — importing it is "
        "not consuming it, and that is precisely the R2-5 shape"
    )
    assert not report.attempts_admitted, "the scheduler ignored a REFUSAL verdict"
    assert not leased, "a refused attempt acquired a lease"


def test_readiness_module_claims_no_admission_authority():
    """The advisory module must not be re-described as the gate.

    `readiness.py` once documented itself as the execution gate while having
    zero production callers, and comments elsewhere cited it as coverage. This
    pins the disclaimer so the laundering cannot silently return.
    """
    import inspect

    from substrate.execution.attempts import readiness

    doc = inspect.getdoc(readiness) or ""
    assert "NO ADMISSION AUTHORITY" in doc.upper(), (
        "readiness.py must state that it holds no admission authority"
    )


def test_no_second_component_decides_admission():
    """Exactly ONE module may define an admission decision function.

    A second `authorize_admission` (or a scheduler-local reimplementation) is
    the divergence this finding is about: two components independently deciding
    whether execution may proceed.
    """
    import pathlib

    root = pathlib.Path(__file__).resolve().parents[1] / "substrate" / "execution" / "attempts"
    definers = [
        p.name
        for p in root.glob("*.py")
        if "def authorize_admission" in p.read_text(encoding="utf-8")
    ]
    assert definers == ["admission.py"], (
        f"admission must be defined in exactly one module, found: {definers}"
    )
