"""Wave 2 — the canonical authority-record loader (field defect 20260807T005250Z-p1).

WHY THIS FILE EXISTS
--------------------
The fan-in suite was green while production was broken, because every test in it
handed ``validate_against_run`` a record list the test itself assembled. The
PRODUCTION record set is assembled by
``FieldControlPlaneDriver._canonical_records()``, and that function read the
grant ledger under a filename this system never persists
(``execution_grants.jsonl``; the real name is
``execution_authorization_grants.jsonl``). The failed read was swallowed to
``logger.debug``, so the gate saw zero grants, refused composition authority,
and the integration Task fell back to ``execution_kind="worker"`` — a real model
worker was dispatched for Task C, which then failed twice with ``commits=[]``.

So every test here enters through the REAL loader and REAL predicate, over
records persisted under their REAL filenames. Nothing hand-assembles a record
list — that is precisely how the defect escaped.

The fixture under ``tests/fixtures/wave2_field_grant_defect/`` is the actual
persisted evidence from field run 20260807T005250Z-p1 (grant, plans, packets,
scenario map, execution binding), not a synthetic re-creation.
"""

from __future__ import annotations

import json
import os
import shutil
from pathlib import Path
from types import SimpleNamespace

import pytest

FIXTURE = Path(__file__).parent / "fixtures" / "wave2_field_grant_defect"

# The field run's real identities.
CAND = "131549ee4d1775a55953ecb9ff5d30fc720d20b1"
RUN = "20260807T005250Z-p1"
TASK_C = "wp-7c7ffd5be3fc"  # integration_task_id in the real scenario map
TASK_A = "wp-5013927ed089"
TASK_B = "wp-6442c7ba99fc"

# Pinned inside the real grant's [not_before, expires_at) window so the fixture
# does not rot. The grant records are used verbatim — never edited to pass.
NOW = 1786065812.2034025

REAL_GRANTS_FILENAME = "execution_authorization_grants.jsonl"
DEFECT_FILENAME = "execution_grants.jsonl"


def _candidate_tree(tmp_path: Path, *, grants_filename: str = REAL_GRANTS_FILENAME) -> str:
    """A real candidate-shaped tree with the field records persisted on disk.

    Layout is the production one the loader parses:
        <root>/candidates/wave2/<cand>/targets/<run>/    <- targets_dir
        <root>/candidates/wave2/<cand>/state/umh/...     <- record sources
    """
    base = tmp_path / "candidates" / "wave2" / CAND
    targets = base / "targets" / RUN
    targets.mkdir(parents=True, exist_ok=True)
    state = base / "state" / "umh"

    (state / "operator" / "objective_planning").mkdir(parents=True, exist_ok=True)
    (state / "universal_work").mkdir(parents=True, exist_ok=True)
    (state / "operator" / "execution_attempts").mkdir(parents=True, exist_ok=True)

    shutil.copy(
        FIXTURE / "objective_plans.jsonl",
        state / "operator" / "objective_planning" / "objective_plans.jsonl",
    )
    shutil.copy(
        FIXTURE / "work_packets.jsonl",
        state / "universal_work" / "work_packets.jsonl",
    )
    # The grant ledger is written under the name the caller asks for. The
    # DEFECT_FILENAME variant reproduces the field condition exactly: the real
    # ledger is simply not where the loader looked.
    shutil.copy(
        FIXTURE / "execution_authorization_grants.jsonl",
        state / "operator" / "execution_attempts" / grants_filename,
    )

    shutil.copy(FIXTURE / "scenario_map.json", targets / "scenario_map.json")
    shutil.copy(FIXTURE / "execution_binding.json", targets / "execution_binding.json")
    return str(targets)


def _driver(targets_dir: str):
    """A real FieldControlPlaneDriver bound to the candidate tree.

    Only the attributes the record loader / predicate touch are populated; the
    methods under test are the REAL ones.

    The VERIFIED DECLARATION is built with the REAL production builder — the
    same call ``__init__`` makes — rather than left unset. ``__new__`` skips
    ``__init__``, so a declaration-dependent method would otherwise raise
    ``AttributeError`` here while working in production (or, worse, a helper
    that stubbed it to None would make these tests pass against a driver that
    has no declaration at all — vacuity of exactly the kind this file exists to
    prevent).
    """
    from substrate.execution.attempts.field_control_plane import FieldControlPlaneDriver

    d = FieldControlPlaneDriver.__new__(FieldControlPlaneDriver)
    d._targets_dir = targets_dir
    d._store = None
    d._sandbox = None
    d._spool = None
    d._proof_runtime = None
    # Mirror EXACTLY what __init__ does: build the THREE-STATE result, and treat
    # any exception as UNANSWERABLE (never as "no composition"). A helper that
    # stubbed this to None would let these tests pass against a driver whose
    # declaration was never built — vacuity of the kind this file exists to stop.
    from substrate.execution.attempts.records import DeclarationResult

    try:
        d._declaration_result = d._build_declaration_result()
    except Exception as exc:  # noqa: BLE001 - mirrors __init__'s DEFAULT-SEALED
        d._declaration_result = DeclarationResult.unanswerable(
            f"declaration builder raised {type(exc).__name__}: {exc}"
        )
    return d


# ─────────────────────────────────────────────────────────────────────────────
# The canonical filename authority
# ─────────────────────────────────────────────────────────────────────────────
def test_canonical_grants_filename_is_the_persisted_one():
    """The loader's filename equals the name the STORE actually writes."""
    from substrate.execution.attempts.field_control_plane import _canonical_grants_filename
    from substrate.execution.attempts.store import _DEFAULT_GRANTS_PATH

    assert _canonical_grants_filename() == REAL_GRANTS_FILENAME
    # And it is the same file the store's own default path points at.
    assert os.path.basename(str(_DEFAULT_GRANTS_PATH)) == REAL_GRANTS_FILENAME


def test_canonical_filename_survives_test_isolation_monkeypatch(monkeypatch):
    """Patching the store's TEST SEAM must not change the production filename.

    ``_DEFAULT_GRANTS_PATH`` is monkeypatched to tmp files by other suites. If
    the loader derived its filename from that attribute, test isolation would
    silently redirect production record loading — the same class of divergence
    as the original defect.
    """
    from substrate.execution.attempts import store as store_mod
    from substrate.execution.attempts.field_control_plane import _canonical_grants_filename

    monkeypatch.setattr(store_mod, "_DEFAULT_GRANTS_PATH", "/tmp/g.jsonl")
    assert _canonical_grants_filename() == REAL_GRANTS_FILENAME


def test_defect_filename_appears_in_no_production_code_line():
    """The old wrong filename must never again be used as a real path.

    Scans CODE only — the name legitimately appears in docstrings/comments that
    document the field defect, and forbidding that would push the institutional
    memory out of the file that needs it most. What must never come back is a
    live string literal on an executable line.
    """
    import ast
    import io
    import tokenize

    root = Path(__file__).resolve().parent.parent
    hits: list[str] = []
    for sub in ("substrate", "scripts", "transports", "adapters"):
        for path in (root / sub).rglob("*.py"):
            try:
                text = path.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            if DEFECT_FILENAME not in text:
                continue
            # Comments are not code.
            code_lines = set()
            try:
                for tok in tokenize.generate_tokens(io.StringIO(text).readline):
                    if tok.type == tokenize.COMMENT:
                        continue
                    if DEFECT_FILENAME in tok.string and tok.type == tokenize.STRING:
                        code_lines.add(tok.start[0])
            except (tokenize.TokenError, IndentationError, SyntaxError):
                hits.append(f"{path.relative_to(root)} (unparseable)")
                continue
            if not code_lines:
                continue
            # A string TOKEN that is a docstring is documentation, not a path.
            try:
                tree = ast.parse(text)
            except SyntaxError:
                hits.append(str(path.relative_to(root)))
                continue
            doc_lines: set[int] = set()
            for node in ast.walk(tree):
                if not isinstance(
                    node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)
                ):
                    continue
                body = getattr(node, "body", None) or []
                if (
                    body
                    and isinstance(body[0], ast.Expr)
                    and isinstance(body[0].value, ast.Constant)
                    and isinstance(body[0].value.value, str)
                ):
                    d = body[0]
                    doc_lines.update(range(d.lineno, (d.end_lineno or d.lineno) + 1))
            real = sorted(code_lines - doc_lines)
            if real:
                hits.append(f"{path.relative_to(root)}:{real}")
    assert hits == [], f"the field-defect grant filename is used as CODE in: {hits}"


# ─────────────────────────────────────────────────────────────────────────────
# BEFORE / AFTER — through the REAL production loader
# ─────────────────────────────────────────────────────────────────────────────
def test_before_fix_semantics_reproduce_the_field_failure(tmp_path):
    """Grants persisted where the loader does NOT look → zero grants → refusal.

    This is the field condition reproduced exactly: the ledger exists, but under
    the real name, while the loader reads the defect name. Proves the failure
    was a record-set loss, not a validator bug.
    """
    from substrate.execution.attempts.field_scenario_map import _read_jsonl, validate_against_run

    targets = _candidate_tree(tmp_path)  # real filename on disk
    state = Path(targets).parent.parent / "state"

    # Simulate the OLD loader: read the grant ledger under the defect filename.
    records: list[dict] = []
    for rel in (
        ("umh", "operator", "objective_planning", "objective_plans.jsonl"),
        ("umh", "universal_work", "work_packets.jsonl"),
        ("umh", "operator", "execution_attempts", DEFECT_FILENAME),
    ):
        p = state.joinpath(*rel)
        if p.exists():
            records.extend(_read_jsonl(p))

    grants = [r for r in records if r.get("grant_id")]
    assert grants == [], "the defect filename must yield zero grant records"

    ok, reason = validate_against_run(targets, records=records, now=NOW)
    assert ok is False
    assert "grant" in reason.lower()


def test_after_fix_production_loader_yields_a_valid_authority(tmp_path):
    """The REAL loader now produces a record set the gate accepts."""
    from substrate.execution.attempts.field_scenario_map import validate_against_run

    targets = _candidate_tree(tmp_path)
    d = _driver(targets)

    records = d._canonical_records()  # THE PRODUCTION PATH
    grants = [r for r in records if r.get("grant_id")]
    assert len(grants) == 1, "the real grant ledger must be loaded"
    assert grants[0]["grant_id"] == "exgrant-83f371afe70e"

    ok, reason = validate_against_run(targets, records=records, now=NOW)
    assert ok is True, reason


def test_production_predicate_recognises_the_integration_task(tmp_path, monkeypatch):
    """The composition predicate returns True for Task C through the real path.

    This is the assertion whose absence let the defect ship: it drives
    ``_composition_task_predicate`` — the exact callable the scheduler holds —
    rather than checking a helper in isolation.
    """
    import substrate.execution.attempts.field_scenario_map as fsm

    targets = _candidate_tree(tmp_path)
    d = _driver(targets)

    # Pin validation time inside the real grant's window (the records are used
    # verbatim; only "now" is controlled).
    real_validate = fsm.validate_against_run
    monkeypatch.setattr(
        fsm,
        "validate_against_run",
        lambda td, *, records, now=None: real_validate(td, records=records, now=NOW),
    )

    predicate = d._composition_task_predicate()
    assert predicate is not None, "composition must not be silently disabled"

    assert predicate(SimpleNamespace(packet_id=TASK_C)) is True
    # And ONLY the integration task.
    assert predicate(SimpleNamespace(packet_id=TASK_A)) is False
    assert predicate(SimpleNamespace(packet_id=TASK_B)) is False


# ─────────────────────────────────────────────────────────────────────────────
# STEP 5 — the negative cases. Invalid authority NEVER means "run as worker".
# ─────────────────────────────────────────────────────────────────────────────
def test_missing_grant_ledger_refuses_composition_authority(tmp_path):
    """Absent (never-written) ledger → no authority, no crash."""
    from substrate.execution.attempts.field_scenario_map import validate_against_run

    targets = _candidate_tree(tmp_path)
    state = Path(targets).parent.parent / "state"
    (state / "umh" / "operator" / "execution_attempts" / REAL_GRANTS_FILENAME).unlink()

    d = _driver(targets)
    records = d._canonical_records()  # must not raise: absence is legitimate
    assert [r for r in records if r.get("grant_id")] == []

    ok, _ = validate_against_run(targets, records=records, now=NOW)
    assert ok is False
    assert d._validated_integration_packet_id() == ""


def test_unreadable_grant_ledger_raises_instead_of_degrading(tmp_path):
    """A PRESENT but unreadable authority ledger must fail loudly.

    Degrading to [] is what turned an authority-loss into a worker dispatch.
    """
    from substrate.execution.attempts.field_control_plane import CanonicalRecordSourceError

    targets = _candidate_tree(tmp_path)
    state = Path(targets).parent.parent / "state"
    ledger = state / "umh" / "operator" / "execution_attempts" / REAL_GRANTS_FILENAME
    ledger.chmod(0o000)

    d = _driver(targets)
    try:
        if os.geteuid() != 0:
            with pytest.raises(CanonicalRecordSourceError) as exc:
                d._canonical_records()
            assert REAL_GRANTS_FILENAME in str(exc.value)
    finally:
        ledger.chmod(0o644)


def test_unreadable_grant_ledger_raises_with_a_real_io_fault(tmp_path):
    """Read-fault variant that does NOT depend on filesystem permissions.

    CI and this VPS both run as root, where ``chmod 000`` does not deny reads —
    so a permission-based test skips and leaves the fail-loud path unproven.
    That blind spot is exactly what hid review finding F1. A directory in place
    of the file raises ``IsADirectoryError`` for EVERY user including root, so
    the branch is pinned with a real fault and no monkeypatching.
    """
    import substrate.execution.attempts.field_control_plane as fcp

    targets = _candidate_tree(tmp_path)
    state = Path(targets).parent.parent / "state"
    ledger = state / "umh" / "operator" / "execution_attempts" / REAL_GRANTS_FILENAME
    ledger.unlink()
    ledger.mkdir()

    d = _driver(targets)
    with pytest.raises(fcp.CanonicalRecordSourceError) as exc:
        d._canonical_records()
    assert REAL_GRANTS_FILENAME in str(exc.value)
    assert "unreadable" in str(exc.value)


def test_malformed_grant_ledger_raises_instead_of_degrading(tmp_path):
    """Malformed JSONL in a required authority source is a hard failure.

    Unconditional: the loader reads required sources STRICTLY, so a malformed
    line can never be skipped into a smaller-but-plausible record set.
    """
    from substrate.execution.attempts.field_control_plane import CanonicalRecordSourceError

    targets = _candidate_tree(tmp_path)
    state = Path(targets).parent.parent / "state"
    ledger = state / "umh" / "operator" / "execution_attempts" / REAL_GRANTS_FILENAME
    ledger.write_text("{not json at all\n", encoding="utf-8")

    d = _driver(targets)
    with pytest.raises(CanonicalRecordSourceError):
        d._canonical_records()


@pytest.mark.parametrize(
    "denied",
    [
        {"status": "revoked"},
        {"expires_at": 1.0},
        {"correlation_id": "w2-OTHER-RUN"},
    ],
)
def test_denied_authority_never_downgrades_the_integration_task(tmp_path, denied):
    """A DENIED verdict must refuse the integration Task, not stamp it worker.

    Review A HIGH-1, reproduced: ``run_scheduler_pass`` re-reads and validates
    its grant EXACTLY ONCE before the frontier loop, while this predicate
    re-derives authority independently and later. An operator revoke, an expiry
    crossing, or a tampered binding written after that single check is DENIED at
    predicate time — and the earlier code returned ``False``, stamping
    ``execution_kind="worker"`` on the integration Task. ``execution_kind`` is
    immutable, so the stamp is PERMANENT: a later healthy pass leaves it a
    model-worker Task forever and the composition producer is never called.

    Same end state as the field defect, through the DENIED door, and invisible
    because ``authority_unresolved`` stayed empty.
    """
    from substrate.execution.attempts.records import CompositionAuthorityUnresolved

    targets = _candidate_tree(tmp_path)
    ledger = (
        Path(targets).parent.parent
        / "state"
        / "umh"
        / "operator"
        / "execution_attempts"
        / REAL_GRANTS_FILENAME
    )
    grant = json.loads(ledger.read_text(encoding="utf-8").strip())
    grant.update(denied)
    ledger.write_text(json.dumps(grant) + "\n", encoding="utf-8")

    d = _driver(targets)
    predicate = d._composition_task_predicate()

    # The declared integration Task refuses — never a silent worker downgrade.
    with pytest.raises(CompositionAuthorityUnresolved) as exc:
        predicate(SimpleNamespace(packet_id=TASK_C))
    # The message must still distinguish DENIED from UNRESOLVED for the operator.
    assert "DENIED" in str(exc.value)

    # Ordinary Tasks are unaffected.
    assert predicate(SimpleNamespace(packet_id=TASK_A)) is False


def test_denied_authority_refusal_is_visible_through_the_real_pass(tmp_path):
    """END TO END: a denied grant leaves NO worker attempt and IS reported."""
    from substrate.execution.attempts.records import ExecutionAuthorizationGrant
    from substrate.execution.attempts.scheduler import AttemptScheduler
    from substrate.execution.attempts.store import ExecutionAttemptStore

    targets = _candidate_tree(tmp_path)
    ledger = (
        Path(targets).parent.parent
        / "state"
        / "umh"
        / "operator"
        / "execution_attempts"
        / REAL_GRANTS_FILENAME
    )
    grant_rec = json.loads(ledger.read_text(encoding="utf-8").strip())
    grant_rec["status"] = "revoked"  # operator revoke, after the pass's re-read
    ledger.write_text(json.dumps(grant_rec) + "\n", encoding="utf-8")

    d = _driver(targets)
    sdir = tmp_path / "store4"
    sdir.mkdir()
    store = ExecutionAttemptStore(
        attempts_path=str(sdir / "a.jsonl"),
        grants_path=str(sdir / "g.jsonl"),
        leases_path=str(sdir / "l.jsonl"),
        assignments_path=str(sdir / "s.jsonl"),
    )

    def _packet(pid: str):
        return SimpleNamespace(
            packet_id=pid,
            status=SimpleNamespace(value="approved"),
            dependencies=[],
            work_scope={"tenant_id": "tenant-x", "target_kind": "umh_substrate"},
            lineage={"plan_record_id": "opr-x"},
            requirements={"writable_path_scope": ["app"], "scope_declared": True},
            desired_end_state="",
            required_role_contracts=[],
            required_tools=[],
            required_templates=[],
            required_workflows=[],
            required_knowledge_models=[],
            risk_class="low",
        )

    class _Q:
        def get_packet(self, pid):
            return _packet(pid)

    # The scheduler's OWN grant is still ACTIVE — the pass admits under it.
    grant = ExecutionAuthorizationGrant(
        grant_id="g-denied",
        decision_ref="objective_plan:opr-x:execution_authorization:v1",
        plan_record_id="opr-x",
        plan_version=1,
        tenant_id="tenant-x",
        status="active",
        task_frontier=[TASK_A, TASK_C, TASK_B],
        max_attempts_per_task=2,
    )
    store.create_grant_idempotent(grant)

    s = AttemptScheduler(
        store,
        work_queue=_Q(),
        placement_fn=lambda **kw: SimpleNamespace(
            assignment_id=f"asn-{kw['attempt_id']}",
            worker_identity="cc-cli@vps-host",
            verifier_role_id="role-verifier-op",
            compute_node_id="node-1",
            environment_class="git_worktree",
            worker_agent_type="developer_agent",
            tool_profile=[],
        ),
        lease_manager=SimpleNamespace(acquire=lambda **kw: None),
        compile_fn=lambda **kw: SimpleNamespace(package_hash="pkg"),
        dispatch_fn=lambda **kw: None,
        dep_success_lookup=lambda _d: True,
        lock_dir=str(tmp_path / "locks4"),
        mutation_runner=_permit,
        latest_plan_lookup=lambda _o: SimpleNamespace(plan_record_id="opr-x", status="approved"),
        composition_task_predicate=d._composition_task_predicate(),
    )

    report = s.run_scheduler_pass(grant)

    assert TASK_C in report.authority_unresolved, "the refusal must be visible, not silent"
    assert store.attempts_for_task(TASK_C) == [], (
        "a denied authority must never leave a PERMANENT worker stamp on the "
        "integration Task — execution_kind is immutable"
    )


@pytest.mark.parametrize(
    "mutate,label",
    [
        (lambda g: g.update({"correlation_id": "w2-OTHER-RUN"}), "foreign run"),
        (lambda g: g.update({"status": "revoked"}), "non-ACTIVE"),
        # Expiry is judged against WALL CLOCK here, because
        # _validated_integration_packet_id() passes no `now` — so the fixture
        # must be made expired relative to real time, not to the pinned NOW.
        (lambda g: g.update({"expires_at": 1.0}), "expired"),
        (lambda g: g.update({"not_before": 4102444800.0}), "not yet valid"),
        (lambda g: g.update({"task_frontier": []}), "empty frontier"),
    ],
)
def test_invalid_grant_refuses_authority_and_never_falls_back(tmp_path, mutate, label):
    """Every invalid-authority shape refuses composition — no worker fallback.

    The critical distinction: UNKNOWN/INVALID composition authority must not
    resolve to "just run the integration Task as an ordinary worker".

    For the DECLARED integration Task the refusal is now a raise rather than a
    bare ``False`` (review A HIGH-1): a ``False`` here stamped an IMMUTABLE
    ``execution_kind="worker"`` whenever the authority was denied at predicate
    time but valid at the pass's single upstream grant re-read. Ordinary Tasks
    are unaffected and still classify as workers.
    """
    from substrate.execution.attempts.records import CompositionAuthorityUnresolved

    targets = _candidate_tree(tmp_path)
    state = Path(targets).parent.parent / "state"
    ledger = state / "umh" / "operator" / "execution_attempts" / REAL_GRANTS_FILENAME

    grant = json.loads(ledger.read_text(encoding="utf-8").strip())
    mutate(grant)
    ledger.write_text(json.dumps(grant) + "\n", encoding="utf-8")

    from substrate.execution.attempts.records import DeclarationOutcome

    d = _driver(targets)
    # DECLARATION ≠ AUTHORIZATION: an invalid GRANT must leave the run's
    # execution CLASS fully declared. Only the authority answer changes.
    assert d._declaration_result.outcome is DeclarationOutcome.DECLARED
    assert not d._validated_integration_packet_id(), f"{label} must not grant authority"

    predicate = d._composition_task_predicate()
    assert predicate is not None
    with pytest.raises(CompositionAuthorityUnresolved):
        predicate(SimpleNamespace(packet_id=TASK_C))
    # ...and an ordinary Task is still an ordinary worker Task.
    assert predicate(SimpleNamespace(packet_id=TASK_A)) is False


def test_ambiguous_duplicate_grants_refuse_authority(tmp_path):
    """Two grants matching the same binding → refuse (cardinality)."""
    targets = _candidate_tree(tmp_path)
    state = Path(targets).parent.parent / "state"
    ledger = state / "umh" / "operator" / "execution_attempts" / REAL_GRANTS_FILENAME

    line = ledger.read_text(encoding="utf-8").strip()
    ledger.write_text(line + "\n" + line + "\n", encoding="utf-8")

    d = _driver(targets)
    assert d._validated_integration_packet_id() == ""


def test_foreign_candidate_grant_refuses_authority(tmp_path):
    """A binding from another CANDIDATE never grants authority.

    ``candidate_sha`` is carried by ``execution_binding.json`` and sealed into
    the binding digest — NOT taken from the scenario map.

    SUPERSEDED (round 9): this is now caught at DECLARATION time. The run's
    candidate is derived from the canonical path, so a binding claiming a
    different candidate cannot declare this run at all — UNANSWERABLE, boundary
    sealed. Previously the map was untouched and only the digest comparison
    caught it, leaving the store armed-but-open.
    """
    targets = _candidate_tree(tmp_path)
    binding = Path(targets) / "execution_binding.json"
    data = json.loads(binding.read_text(encoding="utf-8"))
    data["candidate_sha"] = "0" * 40
    binding.write_text(json.dumps(data), encoding="utf-8")

    from substrate.execution.attempts.records import (
        CompositionAuthorityUnresolved,
        DeclarationOutcome,
    )

    d = _driver(targets)
    assert d._declaration_result.outcome is DeclarationOutcome.UNANSWERABLE
    with pytest.raises(CompositionAuthorityUnresolved):
        d._validated_integration_packet_id()


def _permit(**kw):
    """Governed-mutation runner that actually performs the write.

    Mirrors the fan-in suite's runner: the substrate's governed mutation calls
    ``execute_fn``, and THAT call is what persists the record. A stub returning
    only ``ok=True`` silently creates nothing.
    """
    fn = kw.get("execute_fn")
    out = fn() if callable(fn) else ("", True)
    return SimpleNamespace(success=True, output=out[0] if isinstance(out, tuple) else out)


def _scheduler_with(predicate):
    """A real AttemptScheduler holding ONLY the injected predicate.

    ``_create_attempt`` is the exact function that stamps ``execution_kind``,
    and the worker-fallback branch under test lives inside it.
    """
    from substrate.execution.attempts.scheduler import AttemptScheduler

    s = AttemptScheduler.__new__(AttemptScheduler)
    s._composition_task_predicate = predicate
    s._mutation_runner = lambda **kw: SimpleNamespace(ok=True, applied=True)
    return s


def _kind_for(scheduler, packet_id: str) -> str:
    """The execution_kind the REAL scheduler would stamp for this packet."""
    from substrate.execution.attempts.records import AttemptExecutionKind

    kind = AttemptExecutionKind.WORKER.value
    if scheduler._composition_task_predicate is not None:
        if scheduler._composition_task_predicate(SimpleNamespace(packet_id=packet_id)):
            kind = AttemptExecutionKind.CONTROL_PLANE_COMPOSITION.value
    return kind


def test_scheduler_stamps_composition_kind_for_the_integration_task(tmp_path, monkeypatch):
    """END TO END: valid authority → Task C is a composition attempt, not a worker."""
    import substrate.execution.attempts.field_scenario_map as fsm
    from substrate.execution.attempts.records import AttemptExecutionKind

    targets = _candidate_tree(tmp_path)
    d = _driver(targets)

    real_validate = fsm.validate_against_run
    monkeypatch.setattr(
        fsm,
        "validate_against_run",
        lambda td, *, records, now=None: real_validate(td, records=records, now=NOW),
    )

    s = _scheduler_with(d._composition_task_predicate())
    assert _kind_for(s, TASK_C) == AttemptExecutionKind.CONTROL_PLANE_COMPOSITION.value
    assert _kind_for(s, TASK_A) == AttemptExecutionKind.WORKER.value


def test_unresolvable_authority_refuses_admission_instead_of_worker_fallback(tmp_path):
    """THE STOP CONDITION: unknown authority must NOT become a worker attempt.

    Reproduces the real hazard: the loader now fails loudly, and without the
    scheduler's re-raise that exception would be caught by its generic handler
    and the integration Task would be created as an ordinary worker — exactly
    the field failure, reintroduced through the fix.
    """
    from substrate.execution.attempts.records import (
        AttemptExecutionKind,
        CompositionAuthorityUnresolved,
    )
    from substrate.execution.attempts.scheduler import AttemptScheduler

    targets = _candidate_tree(tmp_path)
    # REAL fault, no monkeypatch: a directory where the ledger belongs is
    # unreadable for every user including root.
    ledger = (
        Path(targets).parent.parent
        / "state"
        / "umh"
        / "operator"
        / "execution_attempts"
        / REAL_GRANTS_FILENAME
    )
    ledger.unlink()
    ledger.mkdir()

    d = _driver(targets)
    predicate = d._composition_task_predicate()

    # The declared integration packet: authority UNRESOLVED → refuse, never worker.
    with pytest.raises(CompositionAuthorityUnresolved):
        predicate(SimpleNamespace(packet_id=TASK_C))

    # And the REAL scheduler must let it through rather than downgrading.
    s = _scheduler_with(predicate)
    with pytest.raises(CompositionAuthorityUnresolved):
        _kind_for(s, TASK_C)

    # BEHAVIOURAL proof that the REAL _create_attempt does not swallow it.
    # Driven through the actual method, not a source-text match: if the generic
    # `except Exception` ever catches this again, _create_attempt returns a
    # WORKER attempt instead of propagating, and this fails.
    real = AttemptScheduler.__new__(AttemptScheduler)
    real._composition_task_predicate = predicate
    real._mutation_runner = lambda **kw: SimpleNamespace(ok=True, applied=True)
    packet_c = SimpleNamespace(
        packet_id=TASK_C,
        dependencies=[TASK_A, TASK_B],
        requirements={},
        work_scope={},
        lineage={},
        risk_class="low",
        required_role_contracts=[],
        required_tools=[],
    )
    grant = SimpleNamespace(
        objective_id="goal-x", plan_record_id="opr-x", plan_version=1, grant_id="g-x"
    )
    with pytest.raises(CompositionAuthorityUnresolved):
        real._create_attempt(grant, packet_c, 1, [])

    # An ORDINARY packet under the same fault stays a worker (no over-refusal).
    assert _kind_for(s, TASK_A) == AttemptExecutionKind.WORKER.value


def test_malformed_grant_line_raises_without_any_monkeypatch(tmp_path):
    """REAL fault, no injection: a malformed JSONL line must raise.

    Review finding F1: the first version of this fix wrapped
    ``field_scenario_map._read_jsonl``, which catches ``(FileNotFoundError,
    OSError)`` and SKIPS malformed lines — so the guard was dead code and the
    authority loss stayed silent. Both fail-loud tests passed only because they
    monkeypatched the reader to raise, and the permission-based test skipped
    under root. This test uses a real malformed record and no patching at all,
    so it fails if the strictness ever moves back above the I/O frame.
    """
    from substrate.execution.attempts.field_control_plane import CanonicalRecordSourceError

    targets = _candidate_tree(tmp_path)
    ledger = (
        Path(targets).parent.parent
        / "state"
        / "umh"
        / "operator"
        / "execution_attempts"
        / REAL_GRANTS_FILENAME
    )
    ledger.write_text('{"grant_id": "g1", "task_frontier": []}\n{BROKEN\n', encoding="utf-8")

    d = _driver(targets)
    with pytest.raises(CanonicalRecordSourceError) as exc:
        d._canonical_records()
    assert "malformed" in str(exc.value)


def test_undecodable_grant_ledger_raises_without_any_monkeypatch(tmp_path):
    """REAL fault, no injection: undecodable bytes must raise, not degrade."""
    from substrate.execution.attempts.field_control_plane import CanonicalRecordSourceError

    targets = _candidate_tree(tmp_path)
    ledger = (
        Path(targets).parent.parent
        / "state"
        / "umh"
        / "operator"
        / "execution_attempts"
        / REAL_GRANTS_FILENAME
    )
    ledger.write_bytes(b"\xff\xfe\x00\x01 not utf-8 at all\n")

    d = _driver(targets)
    with pytest.raises(CanonicalRecordSourceError):
        d._canonical_records()


def test_unreadable_directory_in_place_of_ledger_raises(tmp_path):
    """REAL fault, no injection and root-proof: a directory where a file belongs.

    ``chmod 000`` does not deny root, which is why the permission test skips on
    this host and in CI. Reading a DIRECTORY raises ``IsADirectoryError`` (an
    ``OSError``) for every user including root, so this pins the unreadable
    branch unconditionally.
    """
    from substrate.execution.attempts.field_control_plane import CanonicalRecordSourceError

    targets = _candidate_tree(tmp_path)
    ledger = (
        Path(targets).parent.parent
        / "state"
        / "umh"
        / "operator"
        / "execution_attempts"
        / REAL_GRANTS_FILENAME
    )
    ledger.unlink()
    ledger.mkdir()

    d = _driver(targets)
    with pytest.raises(CanonicalRecordSourceError) as exc:
        d._canonical_records()
    assert "unreadable" in str(exc.value)


def test_loader_does_not_use_the_lenient_shared_reader(tmp_path):
    """The loader must NOT route required sources through ``_read_jsonl``.

    Pins finding F1 structurally: that reader swallows OSError and skips
    malformed lines, so any future refactor that reintroduces it silently
    re-opens the authority-loss hole.
    """
    import inspect

    from substrate.execution.attempts.field_control_plane import FieldControlPlaneDriver

    src = inspect.getsource(FieldControlPlaneDriver._canonical_records)
    assert "_read_jsonl" not in src, (
        "_canonical_records must read required authority sources strictly "
        "(_read_required_jsonl), never through the lenient shared reader"
    )


def test_authority_failure_does_not_abort_the_whole_scheduler_pass(tmp_path):
    """One Task's authority failure must not drop the rest of the frontier.

    Review finding F3. ``_create_attempt``'s own comments forbid this twice:
    an escape from it "would ABORT THE WHOLE SCHEDULER PASS, killing work for
    every OTHER Task in the frontier", and "a fix that converts a one-Task
    hiccup into a fleet-wide outage trades one defect for a worse one". The
    refusal is therefore caught in the FRONTIER LOOP: the integration Task is
    refused and recorded, and every other Task still gets its attempt.
    """
    from substrate.execution.attempts.records import (
        AttemptExecutionKind,
        CompositionAuthorityUnresolved,
    )
    from substrate.execution.attempts.scheduler import SchedulerPassReport

    targets = _candidate_tree(tmp_path)
    ledger = (
        Path(targets).parent.parent
        / "state"
        / "umh"
        / "operator"
        / "execution_attempts"
        / REAL_GRANTS_FILENAME
    )
    ledger.unlink()
    ledger.mkdir()  # real, root-proof read fault

    d = _driver(targets)
    predicate = d._composition_task_predicate()

    # Simulate the frontier loop's contract over a 3-Task frontier where the
    # integration Task sits in the MIDDLE — so a bare escape would drop TASK_B.
    report = SchedulerPassReport()
    created: list[str] = []
    for task_id in (TASK_A, TASK_C, TASK_B):
        try:
            kind = AttemptExecutionKind.WORKER.value
            if predicate(SimpleNamespace(packet_id=task_id)):
                kind = AttemptExecutionKind.CONTROL_PLANE_COMPOSITION.value
        except CompositionAuthorityUnresolved:
            report.attempts_blocked.append(task_id)
            report.authority_unresolved.append(task_id)
            continue
        created.append(f"{task_id}:{kind}")

    # The integration Task is refused — and NOT as a worker.
    assert report.authority_unresolved == [TASK_C]
    assert TASK_C in report.attempts_blocked
    assert not any(t.startswith(TASK_C) for t in created)

    # Both ordinary Tasks survived, including the one AFTER the failure.
    assert created == [
        f"{TASK_A}:{AttemptExecutionKind.WORKER.value}",
        f"{TASK_B}:{AttemptExecutionKind.WORKER.value}",
    ]


def test_real_scheduler_pass_survives_an_authority_failure(tmp_path):
    """BEHAVIOURAL F3 proof — drives the REAL ``run_scheduler_pass``.

    A simulated frontier loop cannot detect removal of the handler; only
    driving the real pass can. With the integration Task in the MIDDLE of a
    3-Task frontier and its authority unresolvable, the pass must still:
      * refuse the integration Task (never a worker attempt), and
      * create attempts for BOTH ordinary Tasks, and
      * complete rather than aborting.
    """
    from substrate.execution.attempts.records import (
        AttemptExecutionKind,
        ExecutionAuthorizationGrant,
    )
    from substrate.execution.attempts.scheduler import AttemptScheduler
    from substrate.execution.attempts.store import ExecutionAttemptStore

    targets = _candidate_tree(tmp_path)
    ledger = (
        Path(targets).parent.parent
        / "state"
        / "umh"
        / "operator"
        / "execution_attempts"
        / REAL_GRANTS_FILENAME
    )
    ledger.unlink()
    ledger.mkdir()  # real, root-proof authority read fault

    d = _driver(targets)

    sdir = tmp_path / "store"
    sdir.mkdir()
    store = ExecutionAttemptStore(
        attempts_path=str(sdir / "a.jsonl"),
        grants_path=str(sdir / "g.jsonl"),
        leases_path=str(sdir / "l.jsonl"),
        assignments_path=str(sdir / "s.jsonl"),
    )

    def _packet(pid: str):
        return SimpleNamespace(
            packet_id=pid,
            status=SimpleNamespace(value="approved"),
            dependencies=[],
            work_scope={"tenant_id": "tenant-x", "target_kind": "umh_substrate"},
            lineage={"plan_record_id": "opr-x"},
            requirements={"writable_path_scope": ["app"], "scope_declared": True},
            desired_end_state="",
            required_role_contracts=[],
            required_tools=[],
            required_templates=[],
            required_workflows=[],
            required_knowledge_models=[],
            risk_class="low",
        )

    class _Q:
        def get_packet(self, pid):
            return _packet(pid)

    # Integration Task deliberately in the MIDDLE: a bare escape drops TASK_B.
    frontier = [TASK_A, TASK_C, TASK_B]
    grant = ExecutionAuthorizationGrant(
        grant_id="g-f3",
        decision_ref="objective_plan:opr-x:execution_authorization:v1",
        plan_record_id="opr-x",
        plan_version=1,
        tenant_id="tenant-x",
        status="active",
        task_frontier=list(frontier),
        max_attempts_per_task=2,
    )
    store.create_grant_idempotent(grant)

    s = AttemptScheduler(
        store,
        work_queue=_Q(),
        placement_fn=lambda **kw: SimpleNamespace(
            assignment_id=f"asn-{kw['attempt_id']}",
            worker_identity="cc-cli@vps-host",
            verifier_role_id="role-verifier-op",
            compute_node_id="node-1",
            environment_class="git_worktree",
            worker_agent_type="developer_agent",
            tool_profile=[],
        ),
        lease_manager=SimpleNamespace(acquire=lambda **kw: None),
        compile_fn=lambda **kw: SimpleNamespace(package_hash="pkg"),
        dispatch_fn=lambda **kw: None,
        dep_success_lookup=lambda _d: True,
        lock_dir=str(tmp_path / "locks"),
        # The governed runner must actually INVOKE execute_fn — that call is what
        # persists the record. A stub that only returns ok=True creates nothing.
        mutation_runner=_permit,
        latest_plan_lookup=lambda _o: SimpleNamespace(plan_record_id="opr-x", status="approved"),
        composition_task_predicate=d._composition_task_predicate(),
    )

    report = s.run_scheduler_pass(grant)  # must NOT raise

    # The integration Task was refused, durably and distinguishably.
    assert TASK_C in report.authority_unresolved
    assert TASK_C in report.attempts_blocked

    # It was NOT created as a worker attempt.
    assert store.attempts_for_task(TASK_C) == []

    # Both ordinary Tasks survived — no fleet-wide outage.
    for ordinary in (TASK_A, TASK_B):
        made = store.attempts_for_task(ordinary)
        assert len(made) == 1, f"{ordinary} was dropped by the authority failure"
        assert made[0].execution_kind == AttemptExecutionKind.WORKER.value


@pytest.mark.parametrize("shape", ["absent", "wrongname"])
def test_declared_integration_task_with_unresolvable_authority_refuses(tmp_path, shape):
    """THE DEFECT CLASS, not just the filename instance (review A CRITICAL-1).

    "Authority records are not where the loader reads them" is LITERALLY the
    field condition, and it presents as ABSENT records — not as an unreadable
    file. Fixing only the filename hardens one instance; any future divergence
    (schema move, subsystem rename, a writer emitting elsewhere) reproduces the
    same silent downgrade.

    So the invariant is affirmative: a run that DECLARES an integration Task
    must be able to resolve that Task's authority, or admission refuses.

    ``wrongname`` reproduces the original defect exactly — the grant ledger
    exists, under the pre-fix filename, i.e. not where the loader looks.
    """
    from substrate.execution.attempts.records import CompositionAuthorityUnresolved

    targets = _candidate_tree(tmp_path)
    ledger = (
        Path(targets).parent.parent
        / "state"
        / "umh"
        / "operator"
        / "execution_attempts"
        / REAL_GRANTS_FILENAME
    )
    if shape == "absent":
        ledger.unlink()
    else:
        ledger.rename(ledger.parent / DEFECT_FILENAME)

    d = _driver(targets)
    predicate = d._composition_task_predicate()
    with pytest.raises(CompositionAuthorityUnresolved) as exc:
        predicate(SimpleNamespace(packet_id=TASK_C))
    assert TASK_C in str(exc.value)

    # Ordinary Tasks are unaffected — no over-refusal.
    assert predicate(SimpleNamespace(packet_id=TASK_A)) is False


def test_run_without_a_declared_integration_task_is_unaffected(tmp_path):
    """No declared integration Task ⇒ nothing is refused.

    Guards the affirmative assertion against over-reach: a run with no scenario
    map at all (the real smoke shape) must classify every packet as an ordinary
    worker without raising.

    Note the map is REMOVED rather than edited. Since the declaration is now
    authenticated against ``binding_digest``, surgically deleting a key from a
    signed map is indistinguishable from tampering — and is correctly refused.
    A run that legitimately has no composition simply has no map.
    """

    targets = _candidate_tree(tmp_path)
    (Path(targets) / "scenario_map.json").unlink()
    # Authority is also unresolvable.
    (
        Path(targets).parent.parent
        / "state"
        / "umh"
        / "operator"
        / "execution_attempts"
        / REAL_GRANTS_FILENAME
    ).unlink()

    from substrate.execution.attempts.records import (
        CompositionAuthorityUnresolved,
        DeclarationOutcome,
    )

    d = _driver(targets)
    # SUPERSEDED (round 9). This run IS candidate-shaped, so a missing scenario
    # map is not "no composition" — it is a governed run whose structure cannot
    # be read, i.e. UNANSWERABLE. Reviewer A reproduced the old reading: deleting
    # the map disarmed the store and `C + worker` persisted.
    #
    # A run that legitimately has no composition is proven so by NOT being
    # candidate-shaped, never by a deleted file.
    assert d._declaration_result.outcome is DeclarationOutcome.UNANSWERABLE
    predicate = d._composition_task_predicate()
    # Every packet refuses — with the run's structure unreadable, NOTHING can be
    # classified, so no packet may be silently treated as an ordinary worker.
    for task in (TASK_A, TASK_B, TASK_C):
        with pytest.raises(CompositionAuthorityUnresolved):
            predicate(SimpleNamespace(packet_id=task))


def test_real_pass_refuses_the_integration_task_when_grants_are_absent(tmp_path):
    """END TO END over the REAL pass, with the literal field condition.

    Absent grant ledger — exactly how run 20260807T005250Z-p1 presented once the
    loader's filename diverged. Proves the refusal is durable, Task C never
    becomes a worker attempt, and the rest of the frontier still runs.
    """
    from substrate.execution.attempts.records import (
        AttemptExecutionKind,
        ExecutionAuthorizationGrant,
    )
    from substrate.execution.attempts.scheduler import AttemptScheduler
    from substrate.execution.attempts.store import ExecutionAttemptStore

    targets = _candidate_tree(tmp_path)
    (
        Path(targets).parent.parent
        / "state"
        / "umh"
        / "operator"
        / "execution_attempts"
        / REAL_GRANTS_FILENAME
    ).unlink()

    d = _driver(targets)
    sdir = tmp_path / "store2"
    sdir.mkdir()
    store = ExecutionAttemptStore(
        attempts_path=str(sdir / "a.jsonl"),
        grants_path=str(sdir / "g.jsonl"),
        leases_path=str(sdir / "l.jsonl"),
        assignments_path=str(sdir / "s.jsonl"),
    )

    def _packet(pid: str):
        return SimpleNamespace(
            packet_id=pid,
            status=SimpleNamespace(value="approved"),
            dependencies=[],
            work_scope={"tenant_id": "tenant-x", "target_kind": "umh_substrate"},
            lineage={"plan_record_id": "opr-x"},
            requirements={"writable_path_scope": ["app"], "scope_declared": True},
            desired_end_state="",
            required_role_contracts=[],
            required_tools=[],
            required_templates=[],
            required_workflows=[],
            required_knowledge_models=[],
            risk_class="low",
        )

    class _Q:
        def get_packet(self, pid):
            return _packet(pid)

    grant = ExecutionAuthorizationGrant(
        grant_id="g-c1",
        decision_ref="objective_plan:opr-x:execution_authorization:v1",
        plan_record_id="opr-x",
        plan_version=1,
        tenant_id="tenant-x",
        status="active",
        task_frontier=[TASK_A, TASK_C, TASK_B],
        max_attempts_per_task=2,
    )
    store.create_grant_idempotent(grant)

    s = AttemptScheduler(
        store,
        work_queue=_Q(),
        placement_fn=lambda **kw: SimpleNamespace(
            assignment_id=f"asn-{kw['attempt_id']}",
            worker_identity="cc-cli@vps-host",
            verifier_role_id="role-verifier-op",
            compute_node_id="node-1",
            environment_class="git_worktree",
            worker_agent_type="developer_agent",
            tool_profile=[],
        ),
        lease_manager=SimpleNamespace(acquire=lambda **kw: None),
        compile_fn=lambda **kw: SimpleNamespace(package_hash="pkg"),
        dispatch_fn=lambda **kw: None,
        dep_success_lookup=lambda _d: True,
        lock_dir=str(tmp_path / "locks2"),
        mutation_runner=_permit,
        latest_plan_lookup=lambda _o: SimpleNamespace(plan_record_id="opr-x", status="approved"),
        composition_task_predicate=d._composition_task_predicate(),
    )

    report = s.run_scheduler_pass(grant)  # must NOT escape

    assert TASK_C in report.authority_unresolved
    assert store.attempts_for_task(TASK_C) == [], "the integration Task must never become a worker"
    for ordinary in (TASK_A, TASK_B):
        made = store.attempts_for_task(ordinary)
        assert len(made) == 1
        assert made[0].execution_kind == AttemptExecutionKind.WORKER.value


@pytest.mark.parametrize(
    "missing",
    [
        ("umh", "operator", "objective_planning", "objective_plans.jsonl"),
        ("umh", "universal_work", "work_packets.jsonl"),
    ],
)
def test_any_missing_required_source_refuses_the_integration_task(tmp_path, missing):
    """EVERY required source, not just the grant ledger (review CRITICAL-1).

    ``_canonical_records`` declares three REQUIRED sources. The first version of
    the UNRESOLVED/DENIED discriminator checked only the grants file, so an
    absent PLAN or PACKET ledger read as DENIED and stamped the integration Task
    ``execution_kind="worker"`` — the field failure reproduced through a
    different door. Both reviewers found it independently; both shapes were
    reproduced against the real fixture.
    """
    from substrate.execution.attempts.records import CompositionAuthorityUnresolved

    targets = _candidate_tree(tmp_path)
    state = Path(targets).parent.parent / "state"
    state.joinpath(*missing).unlink()

    d = _driver(targets)
    predicate = d._composition_task_predicate()
    with pytest.raises(CompositionAuthorityUnresolved):
        predicate(SimpleNamespace(packet_id=TASK_C))


def test_present_but_empty_grant_ledger_is_unresolved_not_denied(tmp_path):
    """Existence is not authority (review CRITICAL-2).

    A grant ledger that exists but holds zero grant records is UNANSWERABLE, not
    a denial — reachable by truncation, an interrupted first write, or a touched
    file. Classifying it DENIED produced the verbatim field signature:
    "10 records, 0 grants, no raise, worker".
    """
    from substrate.execution.attempts.records import CompositionAuthorityUnresolved

    targets = _candidate_tree(tmp_path)
    ledger = (
        Path(targets).parent.parent
        / "state"
        / "umh"
        / "operator"
        / "execution_attempts"
        / REAL_GRANTS_FILENAME
    )
    ledger.write_text("", encoding="utf-8")

    d = _driver(targets)
    assert d._authority_records_present() is False
    predicate = d._composition_task_predicate()
    with pytest.raises(CompositionAuthorityUnresolved):
        predicate(SimpleNamespace(packet_id=TASK_C))


def test_declared_task_refuses_when_the_targets_dir_is_not_candidate_shaped(tmp_path):
    """The LAST door to the field defect (final review A HIGH-2).

    ``_composition_task_predicate`` used to return ``None`` whenever the targets
    dir did not parse as ``candidates/<lane>/<cand>/targets/<run>``. The
    scheduler guards on ``if self._composition_task_predicate is not None``, so
    a ``None`` SKIPS the authority check entirely and the declared integration
    Task is stamped with the IMMUTABLE ``execution_kind="worker"`` while
    ``authority_unresolved`` stays empty — the field outcome exactly, and
    reachable in production because ``scripts/wave2_attempt_runner.py`` takes
    ``--targets-dir`` as a free-form string with no shape validation.

    A run that DECLARES an integration Task is never "composition off".
    """
    from substrate.execution.attempts.records import CompositionAuthorityUnresolved

    # Real records + real map, but a NON-candidate-shaped layout.
    odd = tmp_path / "some" / "other" / "layout"
    odd.mkdir(parents=True)
    state = tmp_path / "state" / "umh"
    (state / "operator" / "objective_planning").mkdir(parents=True)
    (state / "universal_work").mkdir(parents=True)
    (state / "operator" / "execution_attempts").mkdir(parents=True)
    shutil.copy(
        FIXTURE / "objective_plans.jsonl",
        state / "operator" / "objective_planning" / "objective_plans.jsonl",
    )
    shutil.copy(FIXTURE / "work_packets.jsonl", state / "universal_work" / "work_packets.jsonl")
    shutil.copy(
        FIXTURE / "execution_authorization_grants.jsonl",
        state / "operator" / "execution_attempts" / REAL_GRANTS_FILENAME,
    )
    shutil.copy(FIXTURE / "scenario_map.json", odd / "scenario_map.json")
    shutil.copy(FIXTURE / "execution_binding.json", odd / "execution_binding.json")

    from substrate.execution.attempts.records import AttemptExecutionKind, ExecutionAttempt
    from substrate.execution.attempts.store import AttemptStoreConflict, ExecutionAttemptStore

    sdir = tmp_path / "sealstore"
    sdir.mkdir()
    store = ExecutionAttemptStore(
        attempts_path=str(sdir / "a.jsonl"),
        grants_path=str(sdir / "g.jsonl"),
        leases_path=str(sdir / "l.jsonl"),
        assignments_path=str(sdir / "s.jsonl"),
        governed_run=True,
    )
    d = _driver(str(odd))
    d._store = store
    cand, run = d._declaration_binding()
    store.apply_declaration_result(d._declaration_result, run_id=run, candidate_sha=cand)
    assert d._composition_binding() == ("", "", "")

    # STRUCTURAL SUPERSESSION (round 8). A non-candidate-shaped layout means the
    # canonical record sources do not resolve, so the run's lineage — and hence
    # its DECLARATION — cannot be built. That is run-authority corruption, and
    # its outcome is now a SEALED write boundary rather than a predicate that
    # refuses at admission.
    #
    # This is strictly stronger than the behaviour it replaces: the old
    # predicate only protected the path that goes THROUGH the scheduler, so a
    # caller writing directly to the store still persisted `C + worker`. The
    # seal refuses at the durable write boundary, which no caller can bypass.
    with pytest.raises(CompositionAuthorityUnresolved):
        d._declared_integration_packet_id()

    assert store._creation_sealed
    with pytest.raises(AttemptStoreConflict):
        store.create_attempt_idempotent(
            ExecutionAttempt(
                attempt_id="ea-odd",
                task_id=TASK_C,
                execution_kind=AttemptExecutionKind.WORKER.value,
                status="created",
            )
        )


def test_no_declared_task_and_no_binding_leaves_composition_genuinely_off(tmp_path):
    """Guard against over-reach: no integration Task declared ⇒ predicate None."""
    odd = tmp_path / "plain"
    odd.mkdir(parents=True)
    d = _driver(str(odd))
    assert d._composition_binding() == ("", "", "")
    assert d._declared_integration_packet_id() == ""
    assert d._composition_task_predicate() is None


def test_record_source_error_is_an_authority_unresolved(tmp_path):
    """The two must be related by TYPE, not merely by intent (review B F-1).

    ``_authority_records_present()`` re-reads the ledger OUTSIDE the try/except
    that guards authority resolution, purely to pick the cause string. When the
    two exceptions were siblings under ``RuntimeError``, a ledger truncated by a
    concurrent writer between the gate's read and that re-read raised
    ``CanonicalRecordSourceError``, which escaped the scheduler's specific
    ``except CompositionAuthorityUnresolved`` handler into its generic
    ``except Exception`` — stamping the declared integration Task with the
    IMMUTABLE ``execution_kind="worker"``, permanently and invisibly.
    """
    from substrate.execution.attempts.field_control_plane import CanonicalRecordSourceError
    from substrate.execution.attempts.records import CompositionAuthorityUnresolved

    assert issubclass(CanonicalRecordSourceError, CompositionAuthorityUnresolved), (
        "an unreadable REQUIRED authority source IS an unresolved authority — "
        "the type hierarchy must say so or a handler can treat one as the other"
    )


def test_ledger_corrupted_between_gate_and_cause_read_still_refuses(tmp_path, monkeypatch):
    """The F-1 race, end to end: mid-pass corruption must not yield a worker."""
    from substrate.execution.attempts.records import CompositionAuthorityUnresolved

    targets = _candidate_tree(tmp_path)
    ledger = (
        Path(targets).parent.parent
        / "state"
        / "umh"
        / "operator"
        / "execution_attempts"
        / REAL_GRANTS_FILENAME
    )
    grant = json.loads(ledger.read_text(encoding="utf-8").strip())
    grant["status"] = "revoked"  # DENIED → reaches the cause-discriminator branch
    ledger.write_text(json.dumps(grant) + "\n", encoding="utf-8")

    d = _driver(targets)
    predicate = d._composition_task_predicate()

    # A concurrent writer truncates the ledger just before the cause re-read.
    real_present = d._authority_records_present

    def _racing():
        ledger.write_text("{TRUNCATED MID-WRITE\n", encoding="utf-8")
        return real_present()

    monkeypatch.setattr(d, "_authority_records_present", _racing)

    with pytest.raises(CompositionAuthorityUnresolved):
        predicate(SimpleNamespace(packet_id=TASK_C))


@pytest.mark.parametrize(
    "tamper",
    ["duplicate_grants", "foreign_candidate", "cross_run"],
)
def test_tampered_bindings_never_stamp_the_integration_task_worker(tmp_path, tamper):
    """Outcome-level coverage for the three tamper modes (review B test note).

    These previously asserted only ``_validated_integration_packet_id() == ""``
    and never drove the predicate, so they could not prove the Task avoided a
    worker stamp — the property that actually matters.
    """
    from substrate.execution.attempts.records import CompositionAuthorityUnresolved

    targets = _candidate_tree(tmp_path)
    ledger = (
        Path(targets).parent.parent
        / "state"
        / "umh"
        / "operator"
        / "execution_attempts"
        / REAL_GRANTS_FILENAME
    )
    binding = Path(targets) / "execution_binding.json"

    if tamper == "duplicate_grants":
        line = ledger.read_text(encoding="utf-8").strip()
        ledger.write_text(line + "\n" + line + "\n", encoding="utf-8")
    elif tamper == "foreign_candidate":
        data = json.loads(binding.read_text(encoding="utf-8"))
        data["candidate_sha"] = "0" * 40
        binding.write_text(json.dumps(data), encoding="utf-8")
    else:
        data = json.loads(binding.read_text(encoding="utf-8"))
        data["run_id"] = "20260101T000000Z-p9"
        binding.write_text(json.dumps(data), encoding="utf-8")

    d = _driver(targets)
    predicate = d._composition_task_predicate()
    # Refused either at DECLARATION authentication (the binding digest covers
    # candidate_sha/run_id, so a tampered binding invalidates it) or at the
    # authority gate. Both are refusals; neither may yield a worker for Task C.
    with pytest.raises(CompositionAuthorityUnresolved):
        predicate(SimpleNamespace(packet_id=TASK_C))


def _structural_store(tmp_path, targets):
    """A real store with the driver's VERIFIED DECLARATION attached.

    The declaration is a frozen VALUE built once from lineage, not an accessor
    that re-reads mutable state per call — see
    ``tests/test_wave2_verified_declaration.py`` for why that distinction is the
    whole structural fix.
    """
    from substrate.execution.attempts.store import ExecutionAttemptStore

    sdir = tmp_path / "sstore"
    sdir.mkdir()
    store = ExecutionAttemptStore(
        attempts_path=str(sdir / "a.jsonl"),
        grants_path=str(sdir / "g.jsonl"),
        leases_path=str(sdir / "l.jsonl"),
        assignments_path=str(sdir / "s.jsonl"),
        # SEALED BY DEFAULT, exactly as the production runner constructs it.
        governed_run=True,
    )
    d = _driver(targets)
    d._store = store
    cand, run = d._declaration_binding()
    store.apply_declaration_result(d._declaration_result, run_id=run, candidate_sha=cand)
    return store, d


def test_driver_wires_the_structural_guard_into_the_store_it_is_given(tmp_path):
    """The DRIVER must attach the declaration accessor — production wiring.

    The other structural tests attach it by hand, so they cannot detect the
    driver failing to wire it (mutation S4 survived them). Here the store is
    handed to a REAL ``FieldControlPlaneDriver.__init__`` and the guard must be
    live afterwards, with no manual attachment.
    """
    from substrate.execution.attempts.field_control_plane import FieldControlPlaneDriver
    from substrate.execution.attempts.records import AttemptExecutionKind, ExecutionAttempt
    from substrate.execution.attempts.store import AttemptStoreConflict, ExecutionAttemptStore

    targets = _candidate_tree(tmp_path)
    sdir = tmp_path / "wired"
    sdir.mkdir()
    store = ExecutionAttemptStore(
        attempts_path=str(sdir / "a.jsonl"),
        grants_path=str(sdir / "g.jsonl"),
        leases_path=str(sdir / "l.jsonl"),
        assignments_path=str(sdir / "s.jsonl"),
    )

    FieldControlPlaneDriver(
        store=store,
        work_queue=SimpleNamespace(get_packet=lambda _p: None),
        spool=None,
        sandbox_manager=None,
        targets_dir=targets,
    )

    # No manual attach — the driver's __init__ must have done it.
    with pytest.raises(AttemptStoreConflict):
        store.create_attempt_idempotent(
            ExecutionAttempt(
                attempt_id="ea-unwired",
                task_id=TASK_C,
                execution_kind=AttemptExecutionKind.WORKER.value,
                status="created",
            )
        )
    assert store.attempts_for_task(TASK_C) == []


def test_direct_store_write_cannot_persist_the_integration_task_as_worker(tmp_path):
    """THE STRUCTURAL INVARIANT — bypass the scheduler entirely.

    Six rounds each found a NEW pointwise route to the same durable end state:
    the declared integration Task persisted as ``execution_kind="worker"``,
    immutably. This test does not go through any predicate, scheduler, or
    authority path — it writes straight at the one durable write boundary. If it
    passes, the invariant no longer depends on every caller behaving.
    """
    from substrate.execution.attempts.records import AttemptExecutionKind, ExecutionAttempt
    from substrate.execution.attempts.store import AttemptStoreConflict

    targets = _candidate_tree(tmp_path)
    store, _d = _structural_store(tmp_path, targets)

    with pytest.raises(AttemptStoreConflict) as exc:
        store.create_attempt_idempotent(
            ExecutionAttempt(
                attempt_id="ea-bypass",
                task_id=TASK_C,
                execution_kind=AttemptExecutionKind.WORKER.value,
                status="created",
            )
        )
    assert "DECLARED" in str(exc.value)
    # Nothing durable was written.
    assert store.attempts_for_task(TASK_C) == []


def test_structural_invariant_allows_composition_and_ordinary_workers(tmp_path):
    """The guard must not break the two legitimate outcomes."""
    from substrate.execution.attempts.records import AttemptExecutionKind, ExecutionAttempt

    targets = _candidate_tree(tmp_path)
    store, _d = _structural_store(tmp_path, targets)

    # C as composition: allowed.
    store.create_attempt_idempotent(
        ExecutionAttempt(
            attempt_id="ea-c",
            task_id=TASK_C,
            execution_kind=AttemptExecutionKind.CONTROL_PLANE_COMPOSITION.value,
            status="created",
        )
    )
    assert len(store.attempts_for_task(TASK_C)) == 1

    # Ordinary Tasks as workers: unchanged.
    for i, ordinary in enumerate((TASK_A, TASK_B)):
        store.create_attempt_idempotent(
            ExecutionAttempt(
                attempt_id=f"ea-w{i}",
                task_id=ordinary,
                execution_kind=AttemptExecutionKind.WORKER.value,
                status="created",
            )
        )
        assert len(store.attempts_for_task(ordinary)) == 1


@pytest.mark.parametrize(
    "break_it",
    # `delete_plans` was moved OUT of this list in round 8 and given its own
    # test below. It never belonged here: the plan ledger is not AUTHORITY, it
    # is the declaration's own SOURCE. Destroying it is run-authority
    # corruption, whose correct outcome is a sealed write boundary (refuse
    # everything), not "the declaration survives". Keeping it here would have
    # asserted that a Task stays classified after its classifier was destroyed.
    ["revoke", "delete_grants", "empty_grants", "wrongname"],
)
def test_declaration_survives_every_authority_failure(tmp_path, break_it):
    """DECLARATION ≠ AUTHORITY: grant state must never change the Task's class.

    If the declaration consulted grant validity, a revoked or unreadable grant
    would silently reclassify Task C — re-opening the worker door through the
    guard meant to close it. The declared class must hold regardless, so that a
    failed authority yields NO attempt rather than a worker attempt.
    """
    from substrate.execution.attempts.records import AttemptExecutionKind, ExecutionAttempt
    from substrate.execution.attempts.store import AttemptStoreConflict

    targets = _candidate_tree(tmp_path)
    state = Path(targets).parent.parent / "state"
    ledger = state / "umh" / "operator" / "execution_attempts" / REAL_GRANTS_FILENAME

    if break_it == "revoke":
        g = json.loads(ledger.read_text(encoding="utf-8").strip())
        g["status"] = "revoked"
        ledger.write_text(json.dumps(g) + "\n", encoding="utf-8")
    elif break_it == "delete_grants":
        ledger.unlink()
    elif break_it == "empty_grants":
        ledger.write_text("", encoding="utf-8")
    elif break_it == "delete_plans":
        (state / "umh" / "operator" / "objective_planning" / "objective_plans.jsonl").unlink()
    else:
        ledger.rename(ledger.parent / DEFECT_FILENAME)

    store, d = _structural_store(tmp_path, targets)

    # The DECLARATION is unchanged by any authority failure...
    assert (
        d._declared_execution_class_for(TASK_C)
        == AttemptExecutionKind.CONTROL_PLANE_COMPOSITION.value
    )
    # ...so a worker attempt for C remains impossible to persist.
    with pytest.raises(AttemptStoreConflict):
        store.create_attempt_idempotent(
            ExecutionAttempt(
                attempt_id="ea-x",
                task_id=TASK_C,
                execution_kind=AttemptExecutionKind.WORKER.value,
                status="created",
            )
        )
    assert store.attempts_for_task(TASK_C) == []


@pytest.mark.parametrize("moved_to", ["wp-5013927ed089", "wp-doesnotexist", ""])
def test_retargeted_declaration_is_refused_not_silently_disarming(tmp_path, moved_to):
    """THE SEVENTH DOOR — authenticate the declaration itself.

    Six rounds each hardened a CONSUMER of ``declared``; none authenticated
    ``declared`` itself. ``integration_task_id`` was read from an unauthenticated
    file while the authority path digest-verifies that exact same field. Move it
    and the DECLARATION moves while the AUTHORITY correctly refuses — so every
    gate keyed to ``declared`` silently skips, the store guard disarms for the
    REAL Task C, and a worker row is persisted. Immutable, so permanent, and it
    dispatches to a real model worker.

    ``binding_digest`` already covers the semantic mapping; verifying it makes
    the declaration as trustworthy as the authority that consumes it.
    """
    from substrate.execution.attempts.records import (
        AttemptExecutionKind,
        CompositionAuthorityUnresolved,
        ExecutionAttempt,
    )
    from substrate.execution.attempts.store import AttemptStoreConflict

    targets = _candidate_tree(tmp_path)
    smap = Path(targets) / "scenario_map.json"
    data = json.loads(smap.read_text(encoding="utf-8"))
    data["integration_task_id"] = moved_to  # the unauthenticated field
    smap.write_text(json.dumps(data), encoding="utf-8")

    store, d = _structural_store(tmp_path, targets)

    # STRUCTURAL SUPERSESSION (round 8): the declaration is no longer READ from
    # this field at all — it is recomputed from plan/packet lineage — so moving
    # the field is a NON-EVENT rather than a refusal. That is strictly stronger
    # than the previous behaviour: the earlier design detected the retarget via
    # ``binding_digest`` and refused (safe, but availability-costly and reliant
    # on every consumer remembering to verify); the declaration now simply does
    # not move, so Task C stays DECLARED and ordinary work is unaffected.
    #
    # The assertion is therefore on the OUTCOME the invariant is about, not on
    # the mechanism that used to deliver it.
    assert d._declared_integration_packet_id() == TASK_C, (
        "a retargeted map field moved the declaration — the seventh bypass"
    )

    # And the store guard has NOT been disarmed for the real Task C: a worker
    # row must not become durable.
    try:
        store.create_attempt_idempotent(
            ExecutionAttempt(
                attempt_id="ea-poison",
                task_id=TASK_C,
                execution_kind=AttemptExecutionKind.WORKER.value,
                status="created",
            )
        )
    except (AttemptStoreConflict, CompositionAuthorityUnresolved):
        pass
    assert store.attempts_for_task(TASK_C) == [], (
        "a retargeted declaration must never let a worker row for the real "
        "integration Task become durable"
    )


def test_untampered_field_scenario_map_authenticates(tmp_path):
    """The real persisted field map must PASS authentication.

    Guards the digest check against being too strict: if the harness's own
    scenario map did not authenticate, production would refuse every run.
    """
    targets = _candidate_tree(tmp_path)
    d = _driver(targets)
    assert d._declared_integration_packet_id() == TASK_C


def test_undeclared_task_cannot_be_promoted_into_composition(tmp_path):
    """The guard is BIDIRECTIONAL (review B LOW-1).

    A one-directional check ("declared ⇒ must match") would let a future
    producer mint a composition attempt for an arbitrary Task — the mirror
    image of the defect, and equally unrecoverable since ``execution_kind`` is
    immutable.
    """
    from substrate.execution.attempts.records import AttemptExecutionKind, ExecutionAttempt
    from substrate.execution.attempts.store import AttemptStoreConflict

    targets = _candidate_tree(tmp_path)
    store, _d = _structural_store(tmp_path, targets)

    with pytest.raises(AttemptStoreConflict):
        store.create_attempt_idempotent(
            ExecutionAttempt(
                attempt_id="ea-promote",
                task_id="wp-undeclared999",
                execution_kind=AttemptExecutionKind.CONTROL_PLANE_COMPOSITION.value,
                status="created",
            )
        )
    assert store.attempts_for_task("wp-undeclared999") == []


def test_runner_reports_authority_refusal_instead_of_idle():
    """A refused cycle must not log as 'no eligible work' (review B HIGH-1).

    The refusal creates no attempt record, so without a dedicated branch the
    run's only human-facing signal was "control-plane idle" — the exact
    false-completion the field defect produced. The cycle already reports
    ``idle=False``; the operator log must agree with it.
    """
    import ast

    root = Path(__file__).resolve().parent.parent
    runner_src = (root / "scripts" / "wave2_attempt_runner.py").read_text(encoding="utf-8")

    # Structural, not a substring grep: find an `elif` in the reporting ladder
    # whose TEST actually reads the `authority_unresolved` attribute and whose
    # body logs. A grep passes against a renamed/disabled branch (mutation S7
    # survived exactly that), so walk the AST instead.
    tree = ast.parse(runner_src)
    found = False
    for node in ast.walk(tree):
        if not isinstance(node, ast.If):
            continue
        names = {
            n.value
            for n in ast.walk(node.test)
            if isinstance(n, ast.Constant) and isinstance(n.value, str)
        }
        attrs = {n.attr for n in ast.walk(node.test) if isinstance(n, ast.Attribute)}
        if "authority_unresolved" not in (names | attrs):
            continue
        # Its body must actually emit something (not `pass`).
        if any(isinstance(b, ast.Expr) for b in node.body):
            found = True
            break
    assert found, (
        "the runner's reporting ladder must have a LIVE branch that tests "
        "authority_unresolved and logs it — the same way it already surfaces "
        "skipped_not_approved. A refused cycle must never log as idle."
    )


def test_records_exports_the_authority_exception():
    """The cross-module authority contract must be in ``__all__``."""
    from substrate.execution.attempts import records

    assert "CompositionAuthorityUnresolved" in records.__all__


def test_refusal_message_distinguishes_unresolved_from_denied(tmp_path):
    """The SAFE outcome is identical; the reported CAUSE must still differ.

    After the HIGH-1 fix the declared integration Task refuses either way, so
    ``_authority_records_present()`` no longer decides WHETHER to refuse — only
    which cause the operator is told. That makes a mutation of the existence
    check equivalent on safety, so the distinction is pinned HERE instead:
    conflating the two would leave an operator unable to tell "the ledger is
    missing" from "the grant was revoked".
    """
    from substrate.execution.attempts.records import CompositionAuthorityUnresolved

    # (a) UNRESOLVED — a required source absent. Deliberately the PLAN ledger,
    # not the grant ledger: a discriminator that checks only the grants file
    # would still report UNRESOLVED for a missing grants file, so that shape
    # cannot detect the CRITICAL-1 regression. This one can.
    t_absent = _candidate_tree(tmp_path / "a")
    (
        Path(t_absent).parent.parent
        / "state"
        / "umh"
        / "operator"
        / "objective_planning"
        / "objective_plans.jsonl"
    ).unlink()
    with pytest.raises(CompositionAuthorityUnresolved) as unresolved:
        _driver(t_absent)._composition_task_predicate()(SimpleNamespace(packet_id=TASK_C))
    assert "UNRESOLVED" in str(unresolved.value)
    assert "DENIED" not in str(unresolved.value)

    # (b) DENIED — records read, grant revoked.
    t_denied = _candidate_tree(tmp_path / "b")
    ledger = (
        Path(t_denied).parent.parent
        / "state"
        / "umh"
        / "operator"
        / "execution_attempts"
        / REAL_GRANTS_FILENAME
    )
    grant = json.loads(ledger.read_text(encoding="utf-8").strip())
    grant["status"] = "revoked"
    ledger.write_text(json.dumps(grant) + "\n", encoding="utf-8")
    with pytest.raises(CompositionAuthorityUnresolved) as denied:
        _driver(t_denied)._composition_task_predicate()(SimpleNamespace(packet_id=TASK_C))
    assert "DENIED" in str(denied.value)
    assert "UNRESOLVED" not in str(denied.value)


def test_discriminator_and_loader_share_one_required_source_list(tmp_path):
    """The two must never again answer different questions.

    CRITICAL-1 existed because the loader declared three required sources while
    the discriminator hand-checked one. Both now derive from
    ``_required_record_sources``.
    """
    import inspect

    from substrate.execution.attempts.field_control_plane import FieldControlPlaneDriver

    targets = _candidate_tree(tmp_path)
    d = _driver(targets)
    sources = d._required_record_sources()
    assert len(sources) == 3
    assert sources[-1].name == REAL_GRANTS_FILENAME

    for fn in (
        FieldControlPlaneDriver._canonical_records,
        FieldControlPlaneDriver._authority_records_present,
    ):
        assert "_required_record_sources" in inspect.getsource(fn), (
            f"{fn.__name__} must derive from the ONE required-source list"
        )


def test_non_object_json_line_raises(tmp_path):
    """A well-formed non-object line must not silently shrink the record set."""
    from substrate.execution.attempts.field_control_plane import CanonicalRecordSourceError

    targets = _candidate_tree(tmp_path)
    ledger = (
        Path(targets).parent.parent
        / "state"
        / "umh"
        / "operator"
        / "execution_attempts"
        / REAL_GRANTS_FILENAME
    )
    ledger.write_text("[1, 2, 3]\n", encoding="utf-8")

    d = _driver(targets)
    with pytest.raises(CanonicalRecordSourceError) as exc:
        d._canonical_records()
    assert "non-object" in str(exc.value)


def test_authority_refusal_reaches_the_operator_surfaces(tmp_path):
    """The refusal must not exist only as a log line (review HIGH-1).

    The poller previously read ONLY ``attempts_admitted`` off the scheduler
    report, so ``authority_unresolved`` was discarded at the first production
    frame. A refused Task creates no attempt record, so the run then reported
    IDLE — reading as complete while its integration Task never ran.
    """
    from substrate.execution.attempts.field_control_plane import ControlPlaneCycleReport
    from substrate.execution.attempts.poller import PollerPassReport

    # Both operator-facing reports must carry the field...
    assert "authority_unresolved" in PollerPassReport().to_dict()
    assert "authority_unresolved" in ControlPlaneCycleReport().to_dict()

    # ...and the REAL idle computation must exclude an authority refusal.
    # Asserting on a hand-set report proves nothing (mutation M19 survived it):
    # drive the actual expression from the driver's source instead.
    import inspect

    from substrate.execution.attempts.field_control_plane import FieldControlPlaneDriver

    src = inspect.getsource(FieldControlPlaneDriver.run_cycle)
    idle_expr = src[src.index("report.idle = (") : src.index("report.idle = (") + 400]
    assert "authority_unresolved" in idle_expr, (
        "a cycle that refused a Task for unresolvable authority must NOT report "
        "idle — idle means 'no work left', and the refused Task creates no "
        "attempt record, so the run would read as complete"
    )


def test_poller_propagates_authority_unresolved_through_the_real_chain(tmp_path):
    """REAL PRODUCTION PATH: unresolvable authority reaches the poller report.

    Drives the whole chain with real objects — real record loader, real
    predicate, real ``AttemptScheduler``, real ``ControlPlanePoller.run_pass`` —
    over the real field fixture with an absent grant ledger:

        authority unresolved
          -> scheduler refuses the integration Task
          -> poller report carries the refusal
          -> NOT idle-complete

    A source-text assertion cannot detect the field being populated with a
    constant empty list, which is exactly how this leaked the first time
    (mutation M18 survived that weaker test).
    """
    from substrate.execution.attempts.poller import ControlPlanePoller
    from substrate.execution.attempts.records import ExecutionAuthorizationGrant
    from substrate.execution.attempts.scheduler import AttemptScheduler
    from substrate.execution.attempts.store import ExecutionAttemptStore

    targets = _candidate_tree(tmp_path)
    (
        Path(targets).parent.parent
        / "state"
        / "umh"
        / "operator"
        / "execution_attempts"
        / REAL_GRANTS_FILENAME
    ).unlink()  # the literal field condition

    d = _driver(targets)
    sdir = tmp_path / "store3"
    sdir.mkdir()
    store = ExecutionAttemptStore(
        attempts_path=str(sdir / "a.jsonl"),
        grants_path=str(sdir / "g.jsonl"),
        leases_path=str(sdir / "l.jsonl"),
        assignments_path=str(sdir / "s.jsonl"),
    )

    def _packet(pid: str):
        return SimpleNamespace(
            packet_id=pid,
            status=SimpleNamespace(value="approved"),
            dependencies=[],
            work_scope={"tenant_id": "tenant-x", "target_kind": "umh_substrate"},
            lineage={"plan_record_id": "opr-x"},
            requirements={"writable_path_scope": ["app"], "scope_declared": True},
            desired_end_state="",
            required_role_contracts=[],
            required_tools=[],
            required_templates=[],
            required_workflows=[],
            required_knowledge_models=[],
            risk_class="low",
        )

    class _Q:
        def get_packet(self, pid):
            return _packet(pid)

    class _Spool:
        def drain_results(self, *a, **kw):
            return []

    grant = ExecutionAuthorizationGrant(
        grant_id="g-poller",
        decision_ref="objective_plan:opr-x:execution_authorization:v1",
        plan_record_id="opr-x",
        plan_version=1,
        tenant_id="tenant-x",
        status="active",
        task_frontier=[TASK_A, TASK_C, TASK_B],
        max_attempts_per_task=2,
    )
    store.create_grant_idempotent(grant)

    scheduler = AttemptScheduler(
        store,
        work_queue=_Q(),
        placement_fn=lambda **kw: SimpleNamespace(
            assignment_id=f"asn-{kw['attempt_id']}",
            worker_identity="cc-cli@vps-host",
            verifier_role_id="role-verifier-op",
            compute_node_id="node-1",
            environment_class="git_worktree",
            worker_agent_type="developer_agent",
            tool_profile=[],
        ),
        lease_manager=SimpleNamespace(acquire=lambda **kw: None),
        compile_fn=lambda **kw: SimpleNamespace(package_hash="pkg"),
        dispatch_fn=lambda **kw: None,
        dep_success_lookup=lambda _d: True,
        lock_dir=str(tmp_path / "locks3"),
        mutation_runner=_permit,
        latest_plan_lookup=lambda _o: SimpleNamespace(plan_record_id="opr-x", status="approved"),
        composition_task_predicate=d._composition_task_predicate(),
    )

    poller = ControlPlanePoller(
        store=store,
        spool=_Spool(),
        scheduler=scheduler,
        verify_fn=lambda **kw: None,
        scheduler_pass_kwargs={"grant": grant},
    )

    report = poller.run_pass(run_scheduler=True)

    assert TASK_C in report.authority_unresolved, (
        "the poller must carry the scheduler's authority refusal forward — "
        "discarding it is what made the refusal invisible in production"
    )
    assert report.to_dict()["authority_unresolved"] == list(report.authority_unresolved)
    # And the integration Task never became a worker attempt.
    assert store.attempts_for_task(TASK_C) == []


def test_corrupt_scenario_map_refuses_instead_of_worker_fallback(tmp_path):
    """A PRESENT but unparseable scenario map must never yield a worker for C.

    STRUCTURAL SUPERSESSION (round 8). Previously the map WAS the declaration
    source, so a corrupt map made the integration Task unrecognisable and the
    only safe response was to refuse the ENTIRE frontier — an availability cost
    the code documented as "accepted because the alternative risks the safety
    invariant".

    The declaration is now recomputed from plan/packet lineage, so a corrupt map
    cannot make Task C unrecognisable. The safety outcome is unchanged (C is
    still never a worker) and the availability cost is gone: ordinary Tasks are
    no longer starved by a corrupt file they do not depend on.
    """
    from substrate.execution.attempts.records import (
        AttemptExecutionKind,
        CompositionAuthorityUnresolved,
        ExecutionAttempt,
    )
    from substrate.execution.attempts.store import AttemptStoreConflict

    targets = _candidate_tree(tmp_path)
    (Path(targets) / "scenario_map.json").write_text("{corrupt not json", encoding="utf-8")

    store, d = _structural_store(tmp_path, targets)

    # Task C is STILL recognised as the integration Task.
    assert d._declared_integration_packet_id() == TASK_C

    # The authority question still refuses (the map cannot be validated), so no
    # composition is granted...
    predicate = d._composition_task_predicate()
    with pytest.raises(CompositionAuthorityUnresolved):
        predicate(SimpleNamespace(packet_id=TASK_C))

    # ...and C can never become durable as a worker.
    with pytest.raises((AttemptStoreConflict, CompositionAuthorityUnresolved)):
        store.create_attempt_idempotent(
            ExecutionAttempt(
                attempt_id="ea-corrupt",
                task_id=TASK_C,
                execution_kind=AttemptExecutionKind.WORKER.value,
                status="created",
            )
        )

    # An ORDINARY Task is unaffected — no frontier-wide starvation.
    assert predicate(SimpleNamespace(packet_id=TASK_A)) is False


def test_absent_scenario_map_is_an_ordinary_run_not_a_refusal(tmp_path):
    """A GOVERNED run with no scenario map is UNANSWERABLE — sealed, not ordinary.

    SUPERSEDED (round 9). Previously file ABSENCE was read as "this run has no
    composition". That is precisely what an rsync, a cleanup, or an attacker
    produces, and reviewer A reproduced it: deleting the map disarmed the store
    and `C + worker` persisted.

    Absence of a file is not proof of absence of a composition Task. Inside a
    candidate-shaped governed run the map MUST be readable, so its absence is
    UNANSWERABLE and the boundary stays SEALED.

    Legitimate non-composition runs are still unaffected — they are proven so by
    NOT being candidate-shaped (see the plain-run cases), not by a missing file.
    """

    targets = _candidate_tree(tmp_path)
    (Path(targets) / "scenario_map.json").unlink()

    from substrate.execution.attempts.records import (
        CompositionAuthorityUnresolved,
        DeclarationOutcome,
    )

    d = _driver(targets)
    assert d._declaration_result.outcome is DeclarationOutcome.UNANSWERABLE
    # The declaration cannot be answered, so no Task may be classified.
    with pytest.raises(CompositionAuthorityUnresolved):
        d._declared_integration_packet_id()


def test_cross_run_replay_refuses_authority(tmp_path):
    """A binding whose run_id is another run's never grants authority.

    SUPERSEDED (round 9), caught one layer EARLIER: the run id is derived from
    the canonical path, so a binding claiming a foreign run cannot DECLARE this
    run at all — UNANSWERABLE, and the write boundary seals. Previously this
    only made authority return empty, which left the store armed-but-open.
    """
    from substrate.execution.attempts.records import (
        CompositionAuthorityUnresolved,
        DeclarationOutcome,
    )

    targets = _candidate_tree(tmp_path)
    binding = Path(targets) / "execution_binding.json"
    data = json.loads(binding.read_text(encoding="utf-8"))
    data["run_id"] = "20260101T000000Z-p9"
    binding.write_text(json.dumps(data), encoding="utf-8")

    d = _driver(targets)
    assert d._declaration_result.outcome is DeclarationOutcome.UNANSWERABLE
    with pytest.raises(CompositionAuthorityUnresolved):
        d._validated_integration_packet_id()
