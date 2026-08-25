"""Wave 2 field control-plane driver (run-scoped — NOT a persistent supervisor).

This is the HOST-side control-plane half of the field execution loop. The
candidate operator (in its container) surfaces the execution-authorization
Decision in the HUD and, on approve, activates the grant + transitions the
authorized Tasks PLANNED→APPROVED in the SHARED ``ExecutionAttemptStore`` /
WorkPacketQueue (both under ``UMH_STATE_DIR`` = the candidate's state mount,
visible to host and container alike). But nothing INSIDE the container drives a
scheduler pass or writes dispatch envelopes — the candidate is deliberately
mesh-less and worker-less (workers cannot run in a container; ``cc_sdk`` refuses
inside ``/.dockerenv``). This driver is what closes that seam.

It composes the REAL, already-tested substrate pieces against the shared ledger
and the run's signed spool:

    active grant + WorkPacketQueue (shared candidate state)
      → AttemptScheduler (real place_attempt / LeaseManager over a real
        SandboxManager rooted at the fixture repo / compile_attempt_package /
        a spool-writing dispatch_fn that consults the field-failure policy)
      → ControlPlanePoller (real verify_attempt; drains the outbox the host
        WORKER runner fills, advances the canonical ledger, re-runs the
        scheduler so the newly-unblocked frontier dispatches)

The WORKER half — claim inbox → run the real isolated Claude-CLI worker → write
signed outbox result — is ``scripts/wave2_attempt_runner.py``'s existing loop.
This driver and that worker loop share ONE spool; running both is the full
field loop. Ownership boundaries hold exactly as in the no-quota rehearsal
(``tests/test_wave2_harness_rehearsal.py``), with real components swapped for the
stubs: the store is the sole current truth; the spool is ephemeral transport;
the verifier identity is always distinct from the worker; a worker's self-report
is never trusted to complete a Task.

Imports only downward (substrate + same-package). Never touches
transports/services/adapters.
"""

from __future__ import annotations

import json
import logging
import os
import shutil
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable
from uuid import uuid4

from substrate.execution.attempts.records import (
    CompositionAuthorityUnresolved,
    DeclarationResult,
    ExecutionAttemptStatus,
)

logger = logging.getLogger(__name__)

# The run-scope token for a positively-ordinary (non-Wave-2) run. Such a run has
# no candidate/run identity, so its NO_COMPOSITION proof is bound to this literal
# plus its targets dir — enough for the store's binding check to still run, so a
# proof about one ordinary run cannot unseal another's store.
_ORDINARY_RUN_SCOPE = "ordinary-non-wave2-run"

_S = ExecutionAttemptStatus


class CanonicalRecordSourceError(CompositionAuthorityUnresolved):
    """A REQUIRED canonical authority ledger exists but could not be read.

    Raised instead of degrading to an incomplete record set. An incomplete set
    makes the scenario-map gate report "no composition authority", which is
    indistinguishable from a legitimately unauthorized run — and in field run
    20260807T005250Z-p1 that ambiguity dispatched a real model worker for the
    integration Task.

    SUBCLASSES ``CompositionAuthorityUnresolved`` deliberately. The two were
    siblings under ``RuntimeError``, and that gap was a third door into the very
    defect this packet exists to close: ``_authority_records_present()`` reads
    the ledger again, OUTSIDE the try/except that guards authority resolution,
    purely to decide whether the cause is UNRESOLVED or DENIED. If the ledger is
    truncated or corrupted by a concurrent writer between the gate's read and
    that re-read, this error escaped the scheduler's specific
    ``except CompositionAuthorityUnresolved`` handler, fell into its generic
    ``except Exception``, and the declared integration Task was stamped with the
    IMMUTABLE ``execution_kind="worker"`` — permanently, and invisibly.
    Reproduced with a real mid-pass ledger truncation.

    An unreadable required authority source IS an unresolved authority, so the
    type hierarchy now says so and no handler can treat one as the other.
    """


def _read_required_jsonl(path: Path) -> list[dict[str, Any]]:
    """Read a REQUIRED authority record source, or RAISE.

    Deliberately NOT ``field_scenario_map._read_jsonl``. That reader is correct
    for its own callers but is lenient by design: it catches
    ``(FileNotFoundError, OSError)`` and returns ``[]``, and it silently skips a
    malformed line. Both behaviours convert an authority-record LOSS into a
    smaller-but-plausible record set.

    That leniency is exactly what made field run 20260807T005250Z-p1 fail
    silently, and a guard wrapped around the lenient reader is dead code — no
    exception ever reaches it (adversarial review finding F1, reproduced with a
    real permission fault as a non-root user: 10 records, 0 grants, no raise).
    So the strictness has to live at the frame that actually performs the I/O.

    Absence is handled by the CALLER (a not-yet-written ledger is legitimate);
    everything else — unreadable, undecodable, malformed — raises.
    """
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        # UnicodeDecodeError is a ValueError, NOT an OSError — a corrupt/binary
        # ledger would otherwise escape as a bare decode error rather than a
        # typed authority failure, and the scheduler's generic handler would
        # then downgrade the integration Task to a worker.
        raise CanonicalRecordSourceError(
            f"required canonical record source {path} is present but unreadable "
            f"({type(exc).__name__}: {exc}) — refusing to evaluate composition "
            f"authority against an incomplete record set"
        ) from exc

    out: list[dict[str, Any]] = []
    for lineno, line in enumerate(text.splitlines(), start=1):
        line = line.strip()
        if not line:
            continue
        try:
            rec = json.loads(line)
        except ValueError as exc:
            raise CanonicalRecordSourceError(
                f"required canonical record source {path} has a malformed record at "
                f"line {lineno} ({exc}) — refusing to evaluate composition authority "
                f"against a partially-parsed record set"
            ) from exc
        if not isinstance(rec, dict):
            # Well-formed JSON that is not an object (`[1,2]`, `null`) would
            # otherwise be dropped silently — the same "shrink the record set
            # without saying so" shape this reader exists to eliminate, just
            # one syntax layer up.
            raise CanonicalRecordSourceError(
                f"required canonical record source {path} has a non-object record at "
                f"line {lineno} (got {type(rec).__name__}) — refusing to evaluate "
                f"composition authority against a partially-parsed record set"
            )
        out.append(rec)
    return out


def _canonical_grants_filename() -> str:
    """Basename of the execution-authorization grant ledger, from its ONE home.

    Derived from the store's own canonical resolver rather than restated as a
    literal here, so this loader can never again diverge from the file the store
    actually writes (the defect in field run 20260807T005250Z-p1).

    Deliberately NOT read from ``store._DEFAULT_GRANTS_PATH``: that module
    attribute is a documented TEST-ISOLATION seam that suites monkeypatch to a
    tmp file (e.g. ``g.jsonl``). Its basename is therefore not a truthful
    production filename. This resolves the constant the store computes, which
    is the same value in tests and production.
    """
    from substrate.execution.attempts.store import _CANONICAL_GRANTS_FILENAME

    return _CANONICAL_GRANTS_FILENAME


def _git_read(repo: str, args: list[str]) -> tuple[int, str, str]:
    """Read-only git under the CPU gate. Shared by the composition closures."""
    from substrate.execution.attempts.composition import _git

    return _git(repo, args, caller="control_plane_read")


# Deterministic role identities. The implementer role is distinct from the
# verifier role by construction (separation of duty; the placement + lifecycle
# guards re-check this). Frontend vs backend vs integration all use the same
# implementer role id here — the SoD invariant Wave 2 enforces is
# verifier ≠ worker, not per-task role uniqueness.
_IMPLEMENTER_ROLE_ID = "role-implementer-op"
_INTEGRATOR_ROLE_ID = "role-integrator-op"
_VERIFIER_ROLE_ID = "role-verifier-op"

# The verification role AS SPELLED IN THE CANONICAL ROLE STORE. Worker roles
# resolve from that store, so the verifier must be compared in the same
# namespace or `verifier != worker_role` is a tautology (review R5-F2).
_SEED_VERIFIER_ROLE_ID = "role-verify-op"

# How long an UNCLAIMED dispatch envelope may wait in the inbox before it is
# reaped. This is the QUEUE budget and is deliberately distinct from the
# execution budget (``timeout_seconds``): a claimed envelope never expires under
# a running worker (finding C3).
_CLAIM_BUDGET_SECONDS = 1800.0


def governance_envelope_fields(package: Any) -> dict[str, Any]:
    """The governance authority a dispatch envelope must carry (finding F-2).

    ``package`` is the sealed ``ModelExecutionPackage`` from
    ``compile_attempt_package``. It already carries the Task's
    ``writable_path_scope=`` constraint under ``package_hash`` — it was in scope
    at the dispatch site all along and simply never read, so the scope died in
    transit and the launcher fail-closed on every real dispatch.

    These fields are inside ``DispatchEnvelope.signable()`` (which uses
    ``asdict``), so they are covered by the HMAC: a scope cannot be widened in
    transit, and the worker — which never holds the signing secret — cannot forge
    one.

    A named module-level function, not an inline literal, so the regression tests
    can drive THIS construction. A test that inlines the same dict proves nothing
    about the dispatch path.
    """
    return {
        "governance_constraints": [
            str(c) for c in (getattr(package, "governance_constraints", []) or [])
        ],
        "role_instructions": str(getattr(package, "role_instructions", "") or ""),
        "operation_instructions": str(getattr(package, "operation_instructions", "") or ""),
        "ordered_context": [
            c for c in (getattr(package, "ordered_context", []) or []) if isinstance(c, dict)
        ],
        "operation_identity": dict(getattr(package, "operation_identity", {}) or {}),
        "verification_requirements": [
            str(v) for v in (getattr(package, "verification_requirements", []) or [])
        ],
    }


class _RecordView:
    """Attribute view over a store record dict.

    The store returns plain dicts, but ``verify_attempt`` reads its inputs with
    ``getattr`` — so passing the raw dict would make every field read as empty
    and the verifier would run blind even after the lookup was fixed (finding
    C4). Wrapping keeps the store's dict contract while satisfying the verifier.
    """

    __slots__ = ("_d",)

    def __init__(self, data: dict[str, Any]) -> None:
        self._d = dict(data or {})

    @classmethod
    def wrap(cls, data: Any) -> Any:
        if data is None or not isinstance(data, dict):
            return data
        return cls(data)

    def __getattr__(self, name: str) -> Any:
        try:
            return self._d[name]
        except KeyError as exc:
            raise AttributeError(name) from exc

    def to_dict(self) -> dict[str, Any]:
        return dict(self._d)


@dataclass
class _RoleView:
    """Minimal RoleContract shape the placement + admission pipeline reads.

    Field parity with the canonical ``RoleContract`` matters: admission reads
    these by ``getattr`` with an empty default, so a field this view OMITS is
    not "unset" — it silently disables the guard that reads it. ``_RoleView``
    previously had no ``permitted_skill_ids`` at all, so the skill ALLOWLIST
    half of admission check 9 could never fire in production and a Task
    requiring any skill whatsoever was admitted (adversarial review F2, HIGH).

    ``permitted_skill_ids`` is empty by default, which means "this role does
    not narrow skills" — the denylist still applies. It is present so that
    populating it from a real RoleContract ENFORCES rather than silently
    doing nothing.
    """

    role_id: str
    allowed_tools: list[str] = field(default_factory=lambda: ["shell", "Edit", "Write"])
    permitted_skill_ids: list[str] = field(default_factory=list)
    prohibited_skill_ids: list[str] = field(default_factory=list)


@dataclass
class ControlPlaneCycleReport:
    """What one driver cycle did — truthful, side-effect-free summary."""

    grant_ref: str = ""
    results_drained: int = 0
    succeeded: list[str] = field(default_factory=list)
    failed: list[str] = field(default_factory=list)
    admitted: list[str] = field(default_factory=list)
    idle: bool = False
    # Tasks in the grant frontier that the scheduler skipped because their
    # packet is not APPROVED/DELEGATED yet (review W5). The scheduler skips
    # these with a bare `continue`, and the runner only logged when something
    # happened — so an activation that never transitioned the packets presented
    # as a HEALTHY-looking process doing nothing, forever.
    skipped_not_approved: list[str] = field(default_factory=list)
    # Tasks REFUSED because their composition authority could not be RESOLVED
    # (records absent from the canonical location, unreadable, or holding no
    # grant). Distinct from a DENIED authority, which is a real answer. Surfaced
    # here — and excluded from `idle` — because a refused Task creates no
    # attempt record, so it is otherwise indistinguishable from a Task that
    # never reached the frontier, and the run reads as finished.
    authority_unresolved: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "grant_ref": self.grant_ref,
            "results_drained": self.results_drained,
            "succeeded": list(self.succeeded),
            "failed": list(self.failed),
            "admitted": list(self.admitted),
            "idle": self.idle,
            "skipped_not_approved": list(self.skipped_not_approved),
            "authority_unresolved": list(self.authority_unresolved),
            "errors": list(self.errors),
        }


def _canonical_role(role_contract_id: str) -> Any:
    """Resolve a role from the canonical role store — PERSISTED first, then seeds.

    The PERSISTED store (`load_role_contracts()` →
    runtime-state `universal_work/role_contracts.jsonl`) is where an operator
    actually populates `permitted_skill_ids` / `prohibited_skill_ids`. Reading
    ONLY `SEED_ROLE_CONTRACTS` — as this did — meant admission check 9 could
    never refuse, because every hardcoded seed leaves both skill lists unset:
    the R4-2 fix repaired the RESOLVER while the STORE it resolved from carried
    no skill bounds at all (review R5-F1, HIGH). Fixing the resolver alone was
    the same "contract exists but nothing fires it" shape one level down.

    Seeds remain the fallback so a fresh instance with no persisted store still
    resolves the roles the compiler stamps.
    """
    try:
        from substrate.organism.role_contracts import load_role_contracts

        for contract in load_role_contracts() or []:
            if getattr(contract, "role_id", "") == role_contract_id:
                return contract
    except Exception as exc:  # unreadable persisted store → fall through to seeds
        logger.debug("persisted role store unreadable for %s: %s", role_contract_id, exc)

    try:
        from substrate.organism.role_contracts import SEED_ROLE_CONTRACTS, RoleContract

        for seed in SEED_ROLE_CONTRACTS:
            if seed.get("role_id") == role_contract_id:
                return RoleContract.from_dict(seed)
    except Exception as exc:  # unreadable store → caller fails closed, never crashes
        logger.debug("role contract load failed for %s: %s", role_contract_id, exc)
    return None


def _default_role_resolver(packet: Any) -> Any:
    """The role the PACKET declares, resolved from the canonical role store.

    This previously returned a hardcoded ``_RoleView(role_id=_IMPLEMENTER_ROLE_ID)``
    for every packet, which made two admission guards unable to refuse anything
    in production (adversarial review R4-2/R4-3):

    * ``skills_role_authorized`` — the stub's ``permitted_skill_ids`` and
      ``prohibited_skill_ids`` were both permanently empty, so a Task requiring
      ANY skill was admitted;
    * ``tools_permitted`` — the stub's ``allowed_tools`` (``shell/Edit/Write``)
      is DISJOINT from every archetype's ``tool_policy``
      (``repository/test_runner/typecheck``, ``editor``, ``shell_gated/docker``,
      …), so all 5 real archetypes were refused ``tool_not_authorized``. The
      fixture tests could not see it: they hand-build packets with
      ``required_tools=[]``.

    Resolving the packet's OWN declared role from the same store the compiler
    used makes both guards judge against real authority. The ``_RoleView``
    fallback is retained for packets that declare no role (hand-built fixtures
    and any pre-compiler packet) so admission stays decidable — it is a
    fallback, never the primary path.
    """
    raw = getattr(packet, "required_role_contracts", None) or []
    if isinstance(raw, (str, bytes)) or not isinstance(raw, (list, tuple, set)):
        # A non-sequence is MALFORMED, not "no role declared". Iterating it
        # either raised out of `_admit` (an int) or walked characters/dict keys
        # and resolved something arbitrary (review R5-F6).
        logger.error(
            "packet %s declares a malformed required_role_contracts (%s) — no role resolved",
            getattr(packet, "packet_id", ""),
            type(raw).__name__,
        )
        return None
    declared = [str(r) for r in raw if str(r)]

    if not declared:
        # DECLARED NOTHING — the legitimate fallback. Hand-built fixtures and
        # any pre-compiler packet take this path and stay decidable.
        return _RoleView(role_id=_IMPLEMENTER_ROLE_ID)

    for role_id in declared:
        resolved = _canonical_role(role_id)
        if resolved is not None:
            return resolved

    # DECLARED SOMETHING UNRESOLVABLE — a resolution FAILURE that must not wear
    # the fallback's clothes. Both cases previously shared one branch, so a
    # packet naming a role that does not exist was silently RELABELLED
    # `role-implementer-op` and admitted under a grant scoped to THAT role,
    # while a packet naming a REAL but unauthorized role was correctly refused.
    # The guard refused honest declarations and admitted unresolvable ones —
    # the F1/R4-1 inversion shape, one layer up (review R5-F3, HIGH).
    #
    # Returning None makes admission check 8's `bool(role_id)` leg refuse.
    logger.error(
        "packet %s declares role(s) %s that resolve to nothing — refusing to "
        "substitute a different role",
        getattr(packet, "packet_id", ""),
        declared,
    )
    return None


def _verifier_role_resolver(packet: Any) -> str:
    """The VERIFIER role id, in the SAME namespace the worker role comes from.

    This returned the module constant ``role-verifier-op`` while the R4-2 fix
    moved the worker role into ``SEED_ROLE_CONTRACTS``, whose verification role
    is spelled ``role-verify-op``. The two namespaces are disjoint, so
    ``verifier != role_id`` became UNCONDITIONALLY true and both admission
    check 13 and the ``placement.py`` separation-of-duty raise went unreachable
    in production — the very control R4-4 was deferred on (review R5-F2, HIGH).
    My own R4-2 fix created that tautology.

    Resolving the verifier from the same store the worker role comes from makes
    the comparison meaningful again: a packet whose declared role IS the
    verification role now collides and is refused.
    """
    if _canonical_role(_SEED_VERIFIER_ROLE_ID) is not None:
        return _SEED_VERIFIER_ROLE_ID
    return _VERIFIER_ROLE_ID


def _worker_candidates() -> list[dict[str, Any]]:
    """The single real worker candidate: the governed host model executor.

    Its capabilities cover the fixture Tasks' required capabilities. The
    placement ranker is deterministic (single candidate → stable winner).
    """
    return [
        {
            "worker_identity": "model-executor@vps-host",
            "agent_type": "developer_agent",
            "capabilities": [
                "code_write",
                "code_read",
                "shell",
                "git",
                "test_run",
                "integration",
            ],
            "reliability": 0.9,
            "model_profile": {"model": "policy-selected", "executor_contract": "ModelExecutor"},
            "harness_profile": {"harness": "governed_model_executor"},
        }
    ]


def _compute_nodes() -> list[dict[str, Any]]:
    """The VPS host is the one compute node for field workers."""
    return [{"node_id": "vps-host", "headroom": 2}]


class FieldControlPlaneDriver:
    """Run-scoped host-side control-plane loop over the shared ledger + spool.

    Constructed with the shared store/queue (pointed at the candidate state via
    ``UMH_STATE_DIR``), the run's ``DispatchSpool``, a ``SandboxManager`` rooted
    at the fixture repo, and the failure-injection ``targets_dir`` (so the
    ``.inject_failure`` marker genuinely revokes tools on the arming pass).

    ``run_cycle()`` performs exactly one bounded control-plane pass per ACTIVE
    grant: drain the worker outbox → apply canonical transitions with an
    independent verifier → re-run the scheduler so the next frontier is admitted
    and its dispatch envelopes are written to the inbox for the worker loop.
    """

    def __init__(
        self,
        *,
        store: Any,
        work_queue: Any,
        spool: Any,
        sandbox_manager: Any,
        targets_dir: str,
        mutation_runner: Callable[..., Any] | None = None,
        lock_dir: str | None = None,
        proof_runtime: Any | None = None,
        enforce_graph_shape: bool = False,
        latest_plan_lookup: Any | None = None,
    ) -> None:
        # Forwarded to the scheduler, which asks the supersession question on
        # every pass. None means "use the scheduler's own default lookup"
        # (the real PlanningStore) — never "skip supersession".
        self._latest_plan_lookup = latest_plan_lookup
        # Pre-quota graph-shape enforcement. OFF by default so a legitimate
        # single-Task objective (the planning-rail smoke) is not misreported as
        # a malformed graph; the multi-lane field protocol turns it ON, and a
        # wrong-shaped graph is then refused BEFORE any worker quota is spent.
        self._enforce_graph_shape = bool(enforce_graph_shape)
        self._store = store
        self._queue = work_queue
        self._spool = spool
        self._sandbox = sandbox_manager
        self._targets_dir = targets_dir
        self._mutation_runner = mutation_runner
        self._lock_dir = lock_dir
        # STRUCTURAL INVARIANT WIRING. The driver is the component that holds the
        # validated scenario-map authority, so it — not the store — supplies the
        # DECLARATION of what execution class a task_id has. The store then
        # refuses to persist any attempt whose kind contradicts it, at the one
        # durable write boundary, so the invariant no longer depends on every
        # decision path remembering to defend it.
        #
        # THE RESULT IS THREE-STATE, never an absence. DECLARED / NO_COMPOSITION
        # / UNANSWERABLE are distinguishable, and anything unexpected — including
        # an exception from the builder — is UNANSWERABLE, which keeps the store
        # SEALED. Round 8 collapsed the last two into one `None`, and every one of
        # the five reproduced bypasses walked through that collapse.
        self._declaration_result: Any = None
        try:
            self._declaration_result = self._build_declaration_result()
        except Exception as exc:  # noqa: BLE001 — DEFAULTS TO SEALED, never open
            self._declaration_result = DeclarationResult.unanswerable(
                f"declaration builder raised {type(exc).__name__}: {exc}"
            )
        if self._declaration_result.is_sealed:
            logger.error(
                "execution declaration UNANSWERABLE (%s) — the attempt-creation "
                "boundary stays SEALED; no governed Attempt may be created",
                self._declaration_result.reason,
            )
        # The declaration this driver built must govern THIS run's store. Passing
        # the run context makes the store verify that binding, so a declaration
        # that was built correctly but belongs to another candidate/run cannot
        # silently certify this one ("built but not governing" is not protection).
        # The context comes from the RESULT, which is what the store verifies
        # against. A DECLARED result binds through its declaration's
        # run/candidate; a NO_COMPOSITION result binds through its own. Deriving
        # it from the path instead would hand the store ("", "") for an ordinary
        # run, and "absence skips the check" is the defect this round removes.
        _run, _cand = self._declaration_store_context()
        _apply = getattr(store, "apply_declaration_result", None)
        if _apply is not None:
            _apply(self._declaration_result, run_id=_run, candidate_sha=_cand)
        else:
            logger.warning(
                "attempt store does not support verified-declaration enforcement; "
                "the integration Task's structural guard is NOT active"
            )
        # The verifying→succeeded lifecycle guard requires a real AttemptProof
        # (proof_id). Wire the ONE canonical ProofRuntime (honors UMH_STATE_DIR →
        # the shared candidate proof store) so a passing verification actually
        # mints a proof; without it, every passing attempt would be refused
        # succeeded for lack of a proof.
        if proof_runtime is None:
            from substrate.organism.proof_runtime import ProofRuntime

            proof_runtime = ProofRuntime()
        self._proof_runtime = proof_runtime
        self._seq = 0
        # ONE LeaseManager instance, shared by the scheduler and the poller so a
        # poller-side release is visible to the next scheduler acquire (C-2).
        self._lease_mgr: Any = None

    def _run_root(self) -> str:
        """Where per-attempt credential homes live: ``<run_root>/worker-homes/``.

        The host runner uses ``targets_dir`` as run_root when invoking the worker
        (``run_root = targets_dir``), so terminalization must use the SAME root to
        find and destroy the home the worker created."""
        return self._targets_dir

    # ── the signed spool dispatch_fn (real transport) ────────────────────────

    def _dispatch_fn(self) -> Callable[..., None]:
        from substrate.execution.attempts.field_failure_policy import disallowed_tools_for
        from substrate.execution.attempts.model_executor_selection import selected_provider_name
        from substrate.execution.attempts.spool import DispatchEnvelope
        from substrate.execution.attempts.worker_model_executor import (
            capability_policy_for_disallowed_tools,
        )

        def dispatch(
            *, attempt: Any, assignment: Any, lease: Any, package: Any, grant: Any
        ) -> None:
            self._seq += 1
            # Consult the field-failure policy so `inject-failure --variant
            # tools-revoked-a` genuinely revokes Edit/Write on A's FIRST attempt
            # (the marker is ACTUALLY consumed here — review W1). A clean run has
            # no marker → empty revocation.
            revoked = disallowed_tools_for(
                targets_dir=self._targets_dir,
                task_id=getattr(attempt, "task_id", ""),
                attempt_number=int(getattr(attempt, "attempt_number", 1) or 1),
            )
            operation_identity = dict(getattr(package, "operation_identity", {}) or {})
            operation_identity.setdefault("task_id", getattr(attempt, "task_id", ""))
            operation_identity.setdefault("attempt_id", getattr(attempt, "attempt_id", ""))
            operation_identity.setdefault(
                "execution_authorization_ref", getattr(grant, "decision_ref", "")
            )
            policy, policy_error = capability_policy_for_disallowed_tools(
                provider=selected_provider_name(),
                disallowed_tools=list(revoked),
                operation_identity=operation_identity,
            )
            if policy_error:
                raise RuntimeError(
                    f"unsupported worker capability policy for attempt "
                    f"{getattr(attempt, 'attempt_id', '')}: {policy_error}"
                )
            # Unique per DISPATCH, not per attempt (review W6). `d-<attempt_id>`
            # collided whenever an attempt was re-dispatched, and the spool
            # filename is `<sequence>-<dispatch_id>.json` written with os.replace
            # — a silent overwrite that stranded the clobbered attempt. `_seq`
            # also reset to 0 on runner restart, so a fresh dispatch could
            # overwrite a pending envelope for a DIFFERENT attempt.
            unique = uuid4().hex[:8]
            # RV-HIGH-2: durably record the lease in the run manifest the moment it
            # is dispatched, so recover_stale_runs / a run-teardown sweep given a
            # LeaseManager can release a lease stranded by a crash. Runtime lease
            # release remains the poller's authority (it re-drives revoke on a
            # release fault); this manifest entry is the crash-recovery backstop.
            lease_id = getattr(lease, "lease_id", "")
            if lease_id:
                try:
                    from substrate.execution.attempts.run_teardown import register_resource

                    register_resource(self._run_root(), kind="lease", ident=str(lease_id))
                except Exception:  # manifest write must never break dispatch
                    pass
            self._spool.enqueue(
                DispatchEnvelope(
                    dispatch_id=f"d-{attempt.attempt_id}-{unique}",
                    attempt_id=attempt.attempt_id,
                    task_id=attempt.task_id,
                    authorization_ref=getattr(grant, "decision_ref", ""),
                    package_hash=getattr(package, "package_hash", ""),
                    lease_id=lease_id,
                    worktree_path=getattr(lease, "worktree_path", ""),
                    # The AUTHORIZED base the worker attributes its artifacts
                    # against. Without it the worker fell back to "HEAD", making
                    # the range `HEAD..HEAD` — empty by definition.
                    base_commit=str(getattr(lease, "snapshot_ref", "") or ""),
                    nonce=uuid4().hex,  # anti-replay: must not reset on restart
                    sequence=self._seq,
                    # CLAIM budget, NOT the execution budget (finding C3). This
                    # bounds how long an UNCLAIMED envelope may wait; once
                    # claimed it never expires under the running worker.
                    # Previously this was now+timeout_seconds for BOTH A and B,
                    # so B was quarantined while A held the full 600s.
                    expires_at=time.time() + _CLAIM_BUDGET_SECONDS,
                    disallowed_tools=list(revoked),
                    capability_policy=policy,
                    max_turns=int(getattr(attempt, "max_turns", 30) or 30),
                    timeout_seconds=int(getattr(attempt, "timeout_seconds", 600) or 600),
                    payload_hash=getattr(package, "package_hash", ""),
                    # ── CANONICAL AUTHORITY ACROSS THE TRANSPORT (finding F-2) ──
                    **governance_envelope_fields(package),
                )
            )

        return dispatch

    # ── assemble the real scheduler + poller ─────────────────────────────────

    def _lease_manager(self) -> Any:
        """ONE LeaseManager shared by the scheduler (acquire) and the poller
        (release via terminalization). They must be the same instance so a
        release the poller performs is seen by the next admit's acquire."""
        if self._lease_mgr is None:
            from substrate.execution.attempts.leases import LeaseManager

            self._lease_mgr = LeaseManager(
                self._store, self._sandbox, mutation_runner=self._mutation_runner
            )
        return self._lease_mgr

    def _build_scheduler(self) -> Any:
        from substrate.execution.attempts.dispatch import compile_attempt_package
        from substrate.execution.attempts.field_failure_policy import disallowed_tools_for
        from substrate.execution.attempts.model_executor_selection import selected_provider_name
        from substrate.execution.attempts.placement import place_attempt
        from substrate.execution.attempts.scheduler import AttemptScheduler
        from substrate.execution.attempts.worker_model_executor import (
            capability_policy_for_disallowed_tools,
        )

        def compile_with_capability_validation(**kwargs: Any) -> Any:
            attempt = kwargs.get("attempt")
            grant = kwargs.get("grant")
            package = compile_attempt_package(**kwargs)
            revoked = disallowed_tools_for(
                targets_dir=self._targets_dir,
                task_id=getattr(attempt, "task_id", ""),
                attempt_number=int(getattr(attempt, "attempt_number", 1) or 1),
            )
            operation_identity = dict(getattr(package, "operation_identity", {}) or {})
            operation_identity.setdefault("task_id", getattr(attempt, "task_id", ""))
            operation_identity.setdefault("attempt_id", getattr(attempt, "attempt_id", ""))
            operation_identity.setdefault(
                "execution_authorization_ref", getattr(grant, "decision_ref", "")
            )
            _policy, policy_error = capability_policy_for_disallowed_tools(
                provider=selected_provider_name(),
                disallowed_tools=list(revoked),
                operation_identity=operation_identity,
            )
            if policy_error:
                raise RuntimeError(
                    f"unsupported worker capability policy for attempt "
                    f"{getattr(attempt, 'attempt_id', '')}: {policy_error}"
                )
            return package

        return AttemptScheduler(
            self._store,
            work_queue=self._queue,
            placement_fn=place_attempt,
            lease_manager=self._lease_manager(),
            compile_fn=compile_with_capability_validation,
            dispatch_fn=self._dispatch_fn(),
            max_concurrency=2,
            mutation_runner=self._mutation_runner,
            lock_dir=self._lock_dir,
            latest_plan_lookup=self._latest_plan_lookup,
            # Governed fan-in composition. Each is a closure capturing the repo /
            # candidate / run / store / proof-runtime this driver already owns,
            # so the scheduler stays free of repository and proof concerns. All
            # three return None when the run is not candidate-shaped, which turns
            # composition off cleanly rather than leaving it half-wired.
            composition_task_predicate=self._composition_task_predicate(),
            composition_producer=self._composition_producer(),
            downstream_base_resolver=self._downstream_base_resolver(),
        )

    def _build_poller(self, scheduler: Any, grant: Any) -> Any:
        from substrate.execution.attempts.poller import ControlPlanePoller
        from substrate.execution.attempts.verification import verify_attempt

        return ControlPlanePoller(
            store=self._store,
            spool=self._spool,
            scheduler=scheduler,
            verify_fn=verify_attempt,
            proof_runtime=self._proof_runtime,
            assignment_lookup=self._assignment_lookup,
            lease_lookup=self._lease_lookup,
            packet_lookup=self._packet_lookup,
            independent_checks_for=self._independent_checks_for,
            # C-2 terminalization: the poller releases the lease + destroys the
            # credential home on every terminal transition, through the SAME
            # lease manager the scheduler acquires with.
            lease_manager=self._lease_manager(),
            run_root=self._run_root(),
            scheduler_pass_kwargs=dict(
                grant=grant,
                role_resolver=_default_role_resolver,
                verifier_role_resolver=_verifier_role_resolver,
                worker_candidates=_worker_candidates(),
                compute_nodes=_compute_nodes(),
            ),
        )

    def _assignment_lookup(self, assignment_id: str) -> Any:
        """Resolve the durable FleetAssignment via the REAL store API.

        This previously called ``store.list_assignments()`` — a method that does
        not exist — behind a ``getattr`` guard, so it silently returned None for
        every attempt and the verifier ran with no assignment context (finding
        C4). ``get_assignment`` is the actual durable accessor.
        """
        if not assignment_id:
            return None
        getter = getattr(self._store, "get_assignment", None)
        if not callable(getter):
            raise AttributeError(
                "ExecutionAttemptStore has no get_assignment(); refusing to verify "
                "without assignment context"
            )
        return _RecordView.wrap(getter(assignment_id))

    def _reload_queue(self) -> None:
        """Re-read the WorkPacket store from disk into the cached queue.

        ``UniversalWorkQueue`` loads packets once at construction; the driver is
        a persistent loop, so packets the candidate app writes after startup are
        invisible until reloaded. This mirrors the store's stateless per-call
        reads. Fail-open: a queue without a private ``_load`` is left as-is
        rather than crashing the cycle (never worse than the prior behavior).
        """
        reload_fn = getattr(self._queue, "_load", None)
        if callable(reload_fn):
            try:
                reload_fn()
            except Exception as exc:  # a transient read must not stall the loop
                logger.debug("work-queue reload failed (using cached view): %s", exc)

    def _packet_lookup(self, task_id: str) -> Any:
        """The canonical WorkPacket for a Task — the diff-scope AUTHORITY (C-1).

        Returns the packet AS PERSISTED. The writable-path authority is a
        first-class field on its requirements contract
        (``writable_path_scope`` + ``scope_declared``), seeded at
        materialization by ``seed_scope_from_label``.

        It is deliberately NOT synthesized here from a semantic label. Doing so
        would mean the enforced scope is whatever the verifier recomputed this
        run rather than what the Task contract actually records — and it would
        route mutation authority through descriptive lineage, which
        ``EvidenceRef`` prohibits ("Evidence is provenance — it can never be a
        mutation authority"). A packet whose contract declares no scope fails
        closed inside ``verify_attempt``.
        """
        if not task_id:
            return None
        return self._queue.get_packet(task_id)

    def _composition_producer(self) -> Callable[..., Any] | None:
        """Perform + verify + settle ONE control-plane composition attempt.

        Called by the scheduler in place of compile+dispatch when the persisted
        ``execution_kind`` says this attempt is a composition. No worker is
        launched, no instruction package is sealed, no spool envelope is written
        — so no model quota is spent.

        Restart safety: every step below either validates existing durable state
        or is CAS-protected, so the SAME attempt resumes rather than a second one
        being minted. Composition reuses an existing composed ref; the Proof is
        searched before it is created.
        """
        repo, candidate, run_id = self._composition_binding()
        if not (repo and candidate and run_id):
            return None
        accept = self._composition_acceptance_verifier()
        if accept is None:
            return None
        control_plane = self

        def _produce(*, attempt: Any, packet: Any, lease: Any, grant: Any) -> Any:
            from substrate.execution.attempts.composition import (
                CompositionConflict,
                CompositionError,
                compose_predecessors,
                composition_proof_action,
                mint_composition_proof,
                resolve_predecessor_commits,
            )
            from substrate.execution.attempts.terminalization import terminalize

            store = control_plane._store
            task_id = str(getattr(attempt, "task_id", ""))
            deps = [str(d) for d in (getattr(packet, "dependencies", []) or [])]
            verifier_identity = f"verifier:{_INTEGRATOR_ROLE_ID}"

            def _block(reason: str) -> Any:
                """Refuse this composition, choosing the LEGAL terminal for the
                state it is actually in, then release its resources.

                VERIFYING has no BLOCKED target — ``TRANSITIONS['verifying']`` is
                ``('succeeded','failed')`` — so a single hardcoded BLOCKED left a
                failed acceptance STRANDED in VERIFYING with an ACTIVE lease and
                its sandbox slot held (measured: `illegal transition
                'verifying' → 'blocked'`, swallowed by the handler below). A
                rejected verification is a FAILED attempt, which is exactly the
                terminal the poller uses for `verification_rejected`.
                """
                fresh = store.get_attempt(attempt.attempt_id) or attempt
                to_status = (
                    _S.FAILED.value if fresh.status == _S.VERIFYING.value else _S.BLOCKED.value
                )
                try:
                    settled_fail = store.transition_cas(
                        fresh.attempt_id,
                        to_status,
                        fresh.record_version,
                        (fresh.status,),
                        "composer:control-plane",
                        reason[:200],
                        updates={"blocked_reason": reason[:200], "error": reason[:200]},
                    )
                except Exception as exc:  # noqa: BLE001 - recorded, never swallowed
                    logger.error("could not refuse composition %s: %s", fresh.attempt_id, exc)
                    return fresh

                # FAILED is terminal, so its lease/worktree must be released or
                # the slot is held for the rest of the run. BLOCKED is not
                # terminal (retry may re-admit), so terminalize would refuse it.
                if to_status == _S.FAILED.value:
                    try:
                        terminalize(
                            attempt=settled_fail,
                            reason="verification_rejected",
                            lease_manager=control_plane._lease_manager(),
                            run_root=control_plane._run_root(),
                            spool=control_plane._spool,
                            raise_on_security_failure=False,
                        )
                    except Exception as exc:  # noqa: BLE001
                        logger.error(
                            "composition %s failure-terminalization raised: %s",
                            settled_fail.attempt_id,
                            exc,
                        )
                return settled_fail

            try:
                predecessors = resolve_predecessor_commits(
                    repo=repo,
                    candidate=candidate,
                    run_id=run_id,
                    store=store,
                    dependency_task_ids=deps,
                )
                result = compose_predecessors(
                    repo=repo,
                    candidate=candidate,
                    run_id=run_id,
                    task_id=task_id,
                    attempt_id=attempt.attempt_id,
                    predecessor_commits=predecessors,
                )
            except CompositionConflict as exc:
                logger.error("composition CONFLICT for %s: %s", attempt.attempt_id, exc)
                return _block(f"composition conflict: {exc}")
            except CompositionError as exc:
                logger.error("composition FAILED for %s: %s", attempt.attempt_id, exc)
                return _block(f"composition failed: {exc}")

            # LEASED → VERIFYING. Legal only because the PERSISTED execution_kind
            # is the composition kind and no worker identity is set.
            attempt_v = store.transition_cas(
                attempt.attempt_id,
                _S.VERIFYING.value,
                attempt.record_version,
                (_S.LEASED.value,),
                "composer:control-plane",
                "composition produced — verifying",
                updates={"commits": [result.composed_commit]},
            )

            try:
                checks, evidence = accept(
                    attempt_v,
                    composed_commit=result.composed_commit,
                    predecessor_commits=result.predecessor_commits,
                    packet=packet,
                )
            except Exception as exc:  # noqa: BLE001 - a verifier fault is not a pass
                logger.error("composition acceptance raised for %s: %s", attempt.attempt_id, exc)
                return _block(f"composition acceptance error: {exc}")

            passed = bool(checks) and all(bool(getattr(c, "ok", False)) for c in checks)
            if not passed:
                failed = [
                    getattr(c, "check_id", "?") for c in checks if not getattr(c, "ok", False)
                ]
                return _block(f"composition acceptance failed: {failed}")

            predecessor_proofs = {
                t: str(getattr(a, "proof_id", ""))
                for t in deps
                for a in store.attempts_for_task(t)
                if str(getattr(a, "status", "")) == "succeeded"
            }
            action = composition_proof_action(
                attempt=attempt_v,
                result=result,
                predecessor_proofs=predecessor_proofs,
                run_id=run_id,
                candidate_sha=candidate,
            )
            try:
                proof = mint_composition_proof(
                    proof_runtime=control_plane._proof_runtime,
                    attempt=attempt_v,
                    action=action,
                    verifier_identity=verifier_identity,
                )
            except CompositionError as exc:
                return _block(f"composition proof conflict: {exc}")

            settled = store.transition_cas(
                attempt_v.attempt_id,
                _S.SUCCEEDED.value,
                attempt_v.record_version,
                (_S.VERIFYING.value,),
                verifier_identity,
                "composition verified",
                updates={
                    "proof_id": proof.proof_id,
                    "verifier_identity": verifier_identity,
                    "verifier_role_id": _INTEGRATOR_ROLE_ID,
                    "commits": [result.composed_commit],
                },
            )
            logger.info(
                "composition %s SUCCEEDED: commit=%s proof=%s",
                settled.attempt_id,
                result.composed_commit[:12],
                proof.proof_id,
            )

            # TERMINALIZE. The composition attempt NEVER enters the spool, so the
            # poller — the only other production terminalize caller — can never
            # see it. Without this call the lease stays ACTIVE forever, its
            # sandbox slot is never freed (at the production max_parallel=2 that
            # starves the rest of the run), and the attempt's credential home is
            # never destroyed. Composition is the ONE terminal path that has to
            # terminalize itself, because it is the one attempt the spool does
            # not carry.
            #
            # The composed ref is already durable, and `_retain_verified` skips
            # worker retention for this kind, so this is a pure resource release.
            # It is deliberately non-fatal: a cleanup fault must not un-succeed a
            # verified composition, but it IS recorded (never silently dropped),
            # and the lease-withheld path is surfaced loudly because it blocks
            # retry admission for this Task.
            try:
                term = terminalize(
                    attempt=settled,
                    reason="succeeded",
                    lease_manager=control_plane._lease_manager(),
                    run_root=control_plane._run_root(),
                    spool=control_plane._spool,
                    raise_on_security_failure=False,
                )
                if not term.ok:
                    logger.error(
                        "composition %s terminalization left errors: %s residue=%s",
                        settled.attempt_id,
                        term.errors,
                        term.credential_residue,
                    )
                if term.lease_withheld_reason:
                    logger.error(
                        "composition %s lease WITHHELD (%s) — lease %s stays ACTIVE",
                        settled.attempt_id,
                        term.lease_withheld_reason,
                        term.lease_id or "(none)",
                    )
            except Exception as exc:  # noqa: BLE001 - recorded, never swallowed
                logger.error(
                    "composition %s terminalization raised: %s — lease/home may leak",
                    settled.attempt_id,
                    exc,
                )
            return settled

        return _produce

    # ── governed fan-in composition seam ─────────────────────────────────────
    def _composition_binding(self) -> tuple[str, str, str]:
        """(repo, candidate, run_id) for this run, from the targets path alone.

        Canonical layout: ``.../candidates/<lane>/<candidate>/targets/<run>/``.
        Both components come from ONE anchor match — resolving them from
        independent anchors is what previously produced silently misattributed
        refs. Returns ("", "", "") when the path is not candidate-shaped, which
        disables composition rather than guessing a binding.
        """
        parts = [p for p in str(self._targets_dir or "").split(os.sep) if p]
        for i, seg in enumerate(parts):
            if seg != "candidates" or len(parts) <= i + 4 or parts[i + 3] != "targets":
                continue
            cand, run = parts[i + 2], parts[i + 4]
            if cand in ("candidates", "targets") or run in ("candidates", "targets"):
                continue
            return os.path.join(self._targets_dir, "fixture"), cand, run
        return "", "", ""

    def _required_record_sources(self) -> tuple[Path, ...]:
        """The REQUIRED authority record sources for this run — the ONE list.

        Both the loader and the UNRESOLVED/DENIED discriminator derive from this
        so they can never answer different questions about "the required
        sources". They previously did not: the discriminator checked only the
        grants file while the loader declared three, so an absent plan or packet
        ledger read as DENIED and drove the integration Task to a worker
        (adversarial review CRITICAL-1, reproduced on both shapes).
        """
        state = os.path.join(os.path.dirname(os.path.dirname(self._targets_dir)), "state")
        return tuple(
            Path(state).joinpath(*rel)
            for rel in (
                ("umh", "operator", "objective_planning", "objective_plans.jsonl"),
                ("umh", "universal_work", "work_packets.jsonl"),
                ("umh", "operator", "execution_attempts", _canonical_grants_filename()),
            )
        )

    def _authority_records_present(self) -> bool:
        """Can this run's composition authority be ANSWERED at all?

        Separates the two ways composition authority can fail to be granted:

          * DENIED — the records are all there and the gate answered "no"
            (revoked, expired, not-yet-valid, tampered binding, wrong
            run/candidate). A real, resolved answer; composition is simply not
            authorized.
          * UNRESOLVABLE — the records needed to answer are not where the
            canonical loader reads them, so NO answer exists. This is the
            field-defect class and must never read as "ordinary worker task".

        BOTH refuse admission for a declared integration Task — an earlier
        version refused only for UNRESOLVED, and a DENIED verdict arriving after
        the scheduler's single upstream grant re-read then stamped an immutable
        worker kind. This method therefore no longer decides WHETHER to refuse;
        it selects only which CAUSE the operator is told, which is what keeps
        "the ledger is missing" distinguishable from "the grant was revoked".

        Two things are checked, because both were reproduced driving the
        integration Task to ``execution_kind="worker"``:

          1. EVERY required source exists — not just the grant ledger. A missing
             plan or packet ledger is equally an inability to answer.
          2. The grant ledger actually CONTAINS at least one grant record. A
             present-but-empty ledger (truncation, an interrupted first write, a
             touched file) is unanswerable, not a denial — and produced the
             verbatim field signature "10 records, 0 grants, no raise, worker".

        Read failures are NOT swallowed here: an unreadable required source
        raises out of ``_read_required_jsonl``, which is itself the
        unresolvable answer.
        """
        sources = self._required_record_sources()
        if not all(p.exists() for p in sources):
            return False
        grants_path = sources[-1]
        return any(rec.get("grant_id") for rec in _read_required_jsonl(grants_path))

    def _validated_integration_packet_id(self) -> str:
        """The canonical integration packet id, or "" — via the FULL authority path.

        This is deliberately NOT a read of ``scenario_map.json``. It calls
        ``validate_against_run``, the same gate failure-injection arming uses,
        which rereads the run's captured ``execution_binding.json`` and the
        canonical stores and fails closed on: wrong run, tampered/stale binding
        digest (which covers the BINDING's ``candidate_sha`` from
        ``execution_binding.json`` — the scenario map's own ``candidate_sha``
        field is not part of the compared key set, and no consumer reads it),
        unresolvable or non-ACTIVE or
        expired grant, a role id that is not a real persisted WorkPacket, a role
        id outside the grant's authorized frontier, and ambiguous cardinality.

        So a scenario map copied from another run or another candidate can never
        promote an ordinary packet into the composition lifecycle.

        AUTHORITY is asked here; IDENTITY comes from the verified declaration.
        This deliberately does NOT re-read ``integration_task_id`` from disk
        after validating. Re-reading it was the seventh bypass: the field is
        unauthenticated, so a retarget moved the identity while validation
        passed on the recomputed mapping. The identity therefore projects from
        the immutable snapshot, and this method answers only "may composition
        run now?".
        """
        from substrate.execution.attempts.field_scenario_map import validate_against_run

        declared = self._declared_integration_packet_id()
        if not declared:
            return ""
        records = self._canonical_records()
        ok, reason = validate_against_run(self._targets_dir, records=records)
        if not ok:
            logger.warning(
                "scenario map INVALID for this run (%s) — no composition authority granted",
                reason,
            )
            return ""
        return declared

    def _canonical_records(self) -> list[dict[str, Any]]:
        """Canonical plan/packet/grant records for scenario-map validation.

        Every source here is REQUIRED authority: ``resolve_canonical_grant``
        needs the grant record, the exact Plan version it references, AND every
        frontier WorkPacket. Losing any one silently degrades the record set
        into "0 grants matched", which the validator correctly refuses — but the
        refusal then reads as "no composition authority" rather than "the
        authority ledger could not be read". Field run 20260807T005250Z-p1 lost
        the integration Task to exactly that: the grant ledger was read under a
        filename this system never persists
        (``execution_grants.jsonl``; the canonical name is owned by
        ``store._CANONICAL_GRANTS_FILENAME``), the miss was swallowed to
        ``logger.debug``, and Task C fell back to ``execution_kind="worker"``
        and was dispatched to a real model worker.

        So the filename comes from the ONE canonical home (the store's default
        paths — never a second literal), and an unreadable REQUIRED source
        raises instead of degrading. Absence of the FILE is not an error here
        (a run legitimately has no records before they are written); the
        validator fails closed on the resulting empty set, and
        ``_validated_integration_packet_id`` refuses composition authority
        without ever dispatching a worker for the integration packet.
        """
        records: list[dict[str, Any]] = []
        # ONE list, shared with the UNRESOLVED/DENIED discriminator, so the two
        # can never again disagree about what "the required sources" are.
        for path in self._required_record_sources():
            if not path.exists():
                # Not-yet-written is a legitimate state; the gate fails closed on
                # the empty set. Recorded so an absent ledger is never invisible.
                # A DECLARED integration Task with a missing source is separately
                # caught as UNRESOLVED by `_authority_records_present`.
                logger.info("canonical record source absent (not yet written): %s", path)
                continue
            records.extend(_read_required_jsonl(path))
        return records

    def _declared_execution_class_for(self, task_id: str) -> str | None:
        """The DECLARED execution class of ``task_id``, or None if undeclared.

        The structural invariant's authority (see
        ``ExecutionAttemptStore.create_attempt_idempotent``). Deliberately
        answers the DECLARATION question — "is this Task the composition Task?"
        — and NEVER the authority question — "may composition run right now?".

        Those must stay separate. If this consulted grant validity, a revoked or
        unreadable grant would change the Task's execution CLASS, which is
        exactly the conflation that produced six pointwise defects: a Task's
        identity would depend on transient authority state, and every failure of
        that state would re-open the worker door. So a declared integration Task
        is ALWAYS declared, whatever the grant says; when authority is denied or
        unresolved the correct outcome is NO attempt, not a worker attempt.

        Returns None for every ordinary Task, leaving A/B/D behaviour untouched.
        Reads the run's IMMUTABLE VERIFIED DECLARATION — built once at
        construction from recomputed canonical lineage — so no file re-read and
        no second way to decide what the integration Task is enters the system.
        """
        if not task_id:
            return None
        # NO try/except around the refusal. If the declaration could not be
        # built, the refusal must reach the caller — swallowing it to None
        # disarms the structural guard for the real integration Task, which is
        # precisely the bypass a retargeted declaration exploited: the
        # declaration moved, this returned None, and the store then accepted a
        # worker row for the real Task C. An unanswerable declaration is a
        # refusal, never an absence.
        result = self._declaration_result
        if result is None or result.is_sealed:
            raise CompositionAuthorityUnresolved(self._declaration_refusal())
        if result.declaration is None:
            return None  # POSITIVELY PROVEN: this run declares no composition
        return result.declaration.execution_class_for(task_id)

    def _declaration_refusal(self) -> str:
        """The refusal message for an UNANSWERABLE declaration.

        Always UNRESOLVED by construction: the declaration is built from lineage
        alone and never consults the grant, so it cannot fail because authority
        said "no" — only because the inputs needed to ANSWER are missing,
        unreadable, foreign, or structurally non-authoritative. Saying so keeps
        the operator's UNRESOLVED-vs-DENIED distinction intact on this path.
        """
        result = self._declaration_result
        reason = getattr(result, "reason", "") or "no declaration result was produced"
        # Carries BOTH the operator verdict word (UNRESOLVED — the term the
        # scheduler/poller surfaces and operators grep for) and the internal
        # state name (UNANSWERABLE). The verdict word appears exactly once and
        # its counterpart (DENIED) never appears, so a log filter searching for
        # a verdict cannot match both.
        return (
            f"the run's execution declaration is UNANSWERABLE — composition authority "
            f"is UNRESOLVED ({reason}). Run-structure corruption, not a grant verdict: "
            f"the declaration never consults grant validity. No Task can be classified, "
            f"so the attempt-creation boundary stays SEALED rather than risking a worker "
            f"dispatch for the integration Task"
        )

    def _composition_task_predicate(self) -> Callable[[Any], bool] | None:
        """Is THIS packet the run's canonical, grant-authorized integration Task?

        Returns None ONLY when the run has no candidate binding AND declares no
        integration Task — composition is genuinely off, not half-wired.

        A run that DOES declare an integration Task but whose targets dir is not
        candidate-shaped is NOT "composition off": it is a misconfigured run
        whose authority cannot be evaluated. Returning None there was the last
        remaining door to the field defect — the scheduler's
        ``if self._composition_task_predicate is not None`` guard skips the
        authority check entirely, and the declared integration Task is stamped
        with the IMMUTABLE ``execution_kind="worker"`` while
        ``authority_unresolved`` stays empty. Reproduced from a real scenario map
        declaring Task C under a non-candidate-shaped path, which
        ``scripts/wave2_attempt_runner.py`` accepts as a free-form
        ``--targets-dir``. So that case returns a predicate that REFUSES the
        declared Task instead of a None that silently disables the check.
        """
        repo, candidate, run_id = self._composition_binding()
        control_plane = self
        if not (repo and candidate and run_id):
            try:
                declared_without_binding = self._declared_integration_packet_id()
            except CompositionAuthorityUnresolved:
                # No run binding AND an unreadable/unauthenticatable map.
                #
                # Refusing every packet here is WRONG: with no candidate binding
                # there is no Wave 2 composition run at all, so there is no
                # integration Task to protect — this is an ordinary non-field
                # scheduler with a stray file in its targets dir. Refusing the
                # whole frontier for that starves unrelated worker Tasks (caught
                # by test_driver_dispatch_fn_consults_failure_marker).
                #
                # Composition is simply OFF. The candidate-shaped path — where a
                # real run DOES declare an integration Task — is where an
                # unauthenticatable declaration refuses, and that is unchanged.
                logger.warning(
                    "scenario map present but unreadable/unauthenticated AND the targets "
                    "dir is not candidate-shaped — treating this as a run with no "
                    "composition; no integration Task can be declared without a binding"
                )
                return None
            if not declared_without_binding:
                return None  # genuinely no composition in this run

            def _refuse_declared(packet: Any) -> bool:
                if str(getattr(packet, "packet_id", "")) == declared_without_binding:
                    raise CompositionAuthorityUnresolved(
                        f"the run declares {declared_without_binding!r} as its integration "
                        f"Task, but its targets dir {control_plane._targets_dir!r} is not "
                        f"candidate-shaped so no run/candidate binding resolves and "
                        f"composition authority cannot be evaluated — refusing admission "
                        f"rather than dispatching a worker for the integration Task"
                    )
                return False

            return _refuse_declared

        def _is_composition(packet: Any) -> bool:
            packet_id = str(getattr(packet, "packet_id", ""))
            # Identify the declared integration Task FIRST. A PRESENT-but-
            # unreadable scenario map raises out of here for EVERY packet, and
            # that breadth is deliberate, not an oversight:
            #
            # The reviewer proposed narrowing the raise to "only the declared
            # Task". That is not implementable — when the map is unparseable
            # there IS no declared Task to compare against. The grant's
            # `task_frontier` is an unordered id list and does not say which
            # member is the integration Task (verified against the real field
            # grant), so nothing else in the run can identify it. Any packet
            # might be the integration Task, and guessing wrong is precisely a
            # model-worker dispatch of Task C — the field defect.
            #
            # So a corrupt map refuses the whole frontier. That is an
            # availability cost (Tasks A/B are refused too), accepted because
            # the alternative risks the safety invariant. It is fail-closed,
            # fully reported in `authority_unresolved`, does not abort the pass,
            # creates no attempts, and clears the moment the map is repaired.
            declared = control_plane._declared_integration_packet_id()
            try:
                target = control_plane._validated_integration_packet_id()
            except Exception as exc:
                # Authority could not be RESOLVED (unreadable ledger, etc.). This
                # is not "this packet is an ordinary worker task" — it is "we do
                # not know". Returning False here would let the scheduler's
                # fail-closed-to-worker branch dispatch a real model worker for
                # the integration Task, which is exactly what happened in field
                # run 20260807T005250Z-p1. Re-raise for the DECLARED integration
                # packet so admission refuses instead of downgrading it.
                if packet_id and packet_id == declared:
                    raise CompositionAuthorityUnresolved(
                        f"composition authority for the declared integration packet "
                        f"{packet_id!r} could not be resolved ({type(exc).__name__}: {exc}) "
                        f"— refusing admission rather than dispatching a worker"
                    ) from exc
                logger.warning(
                    "composition authority unresolved (%s) while classifying %s — "
                    "treating as ordinary worker task",
                    exc,
                    packet_id,
                )
                return False
            if not target:
                # THE DEFECT CLASS, not just the one instance (review A CRITICAL-1).
                #
                # A run that DECLARES an integration Task must be able to resolve
                # that Task's authority. If it cannot, the honest reading is "the
                # authority records are not where we look" — which is LITERALLY
                # what happened in field run 20260807T005250Z-p1 — not "this is an
                # ordinary worker task". Returning False here is what stamped
                # execution_kind="worker" on Task C and sent it to a real model
                # worker that failed twice with no commits.
                #
                # Fixing only the filename hardens ONE instance of the class. Any
                # future divergence (a schema move, a subsystem rename, a writer
                # emitting elsewhere) presents as ABSENT records and reproduces
                # the same silent downgrade. So the invariant is stated
                # affirmatively and checked on every classification: declared ⇒
                # resolvable, else refuse.
                #
                # A run with NO declared integration Task is untouched: `declared`
                # is "" and every packet classifies as an ordinary worker.
                #
                # The DECLARED integration Task is never classified as an
                # ordinary worker — for ANY reason, not only an unresolvable one.
                #
                # An earlier version refused only when the authority records were
                # UNRESOLVABLE, reasoning that a revoked/expired/tampered grant is
                # a real answer the scheduler "already refuses upstream via
                # `is_authorization_valid`". THAT REASONING WAS WRONG, and the
                # adversarial review reproduced it: `run_scheduler_pass` re-reads
                # and validates the grant EXACTLY ONCE (scheduler.py, before the
                # frontier loop), while this predicate re-derives authority
                # independently and later, from the ledger on disk. Any authority
                # that is denied at predicate time but was valid at that single
                # re-read — an operator revoke, an expiry crossing, a tampered
                # binding written mid-pass — fell through `return False` and
                # stamped `execution_kind="worker"` on the integration Task.
                # Because `execution_kind` is immutable, that stamp is permanent:
                # a later, fully healthy pass leaves the Task a model-worker Task
                # forever and the composition producer is never called. Same end
                # state as field run 20260807T005250Z-p1, reached through the
                # DENIED door instead of the UNRESOLVED one — and invisible,
                # since `authority_unresolved` stayed empty.
                #
                # So the discriminator is no longer "was the authority readable?"
                # but the invariant itself: DECLARED ⇒ we must be able to say YES.
                # Anything else refuses admission. DENIED and UNRESOLVED remain
                # distinguishable to the operator through the message, but they
                # produce the SAME safe outcome for this one Task: never a worker.
                #
                # A run with NO declared integration Task is untouched: `declared`
                # is "" and every packet classifies as an ordinary worker.
                if declared and packet_id == declared:
                    resolvable = control_plane._authority_records_present()
                    cause = (
                        "the authority records are absent, empty or unreadable at the "
                        "canonical location (UNRESOLVED)"
                        if not resolvable
                        else "the authority records were read and the gate DENIED this run "
                        "(revoked, expired, not-yet-valid, ambiguous, or a tampered/stale "
                        "binding) — note the pass validated its grant only once, before "
                        "the frontier loop, so this denial may postdate that check"
                    )
                    raise CompositionAuthorityUnresolved(
                        f"the run declares {declared!r} as its integration Task, but its "
                        f"composition authority does not resolve: {cause} — refusing "
                        f"admission rather than dispatching a worker for the integration Task"
                    )
                return False
            return packet_id == target

        return _is_composition

    def _declaration_binding(self) -> tuple[str, str]:
        """(candidate_sha, run_id) for this run — the authenticated run context.

        Derived from the canonical candidate-shaped targets path, the same ONE
        anchor match ``_composition_binding`` uses. Returns ("", "") when the
        path is not candidate-shaped.
        """
        _repo, cand, run = self._composition_binding()
        return cand, run

    def _declaration_store_context(self) -> tuple[str, str]:
        """(run_id, candidate_sha) this run's store must be armed with.

        Taken from the RESULT, never re-derived from the path: the store's
        binding check exists to prove the result governs THIS store, so the two
        must be two views of one value.
        """
        result = self._declaration_result
        if result is None:
            return "", ""
        if result.declaration is not None:
            return result.declaration.run_id, result.declaration.candidate_sha
        return result.run_id, result.candidate_sha

    def _build_declaration_result(self) -> DeclarationResult:
        """Build this run's THREE-STATE execution declaration result.

        THE SINGLE DECLARATION AUTHORITY, created once at driver construction.

        Returns exactly one of:

          * ``DECLARED``       — lineage resolved and names a composition Task.
          * ``NO_COMPOSITION`` — lineage RESOLVED and positively contains no
            composition Task. A proof, never an absence.
          * ``UNANSWERABLE``   — the declaration cannot be safely determined.
            The store stays SEALED.

        Round 8 returned a bare ``None`` for the last two, and three of its exits
        took the "cannot tell" path while the store read "nothing to enforce".
        Five bypasses followed. Every failure shape here is UNANSWERABLE, so a
        new one cannot silently become NO_COMPOSITION.

        Derived by RECOMPUTING the mapping from canonical PLAN and PACKET
        lineage, never by reading the persisted map's ``integration_task_id``.
        The GRANT ledger is deliberately not consulted: lineage answers "what
        type of execution is this Task?", the grant answers "may it happen now?".
        Coupling them let an expired grant undeclare Task C (measured on the real
        fixture, whose grant is ~0.1 days past ``expires_at``).
        """
        from substrate.execution.attempts.field_scenario_map import (
            build_verified_declaration,
            execution_binding_path,
            read_execution_binding,
            scenario_map_path,
        )

        # ``lexists``, NOT ``exists``. The question here is "does this run PRESENT
        # a Wave 2 name?", not "does that name resolve to readable content?".
        #
        # ``os.path.exists`` FOLLOWS symlinks, so a dangling link reports False
        # for a file the directory plainly lists. A targets dir visibly holding
        # ``scenario_map.json`` and ``execution_binding.json`` was therefore
        # classified as presenting NO Wave 2 evidence, took the NO_COMPOSITION
        # branch, unsealed the store, and persisted an immutable
        # ``Task C + worker`` row (reproduced end to end).
        #
        # The comment below already named a dangling symlink as the case to
        # defend against — ``exists`` is the one primitive that cannot see it.
        # A name that is present but does NOT resolve is the STRONGEST evidence
        # of a mutated governed run, so it must weigh toward UNANSWERABLE.
        map_present = os.path.lexists(scenario_map_path(self._targets_dir))
        binding_present = os.path.lexists(execution_binding_path(self._targets_dir))
        candidate_sha, run_id = self._declaration_binding()
        if not (candidate_sha and run_id):
            # NEITHER PATH SHAPE NOR FILE ABSENCE IS PROOF.
            #
            # ``--targets-dir`` is a free-form string, so path shape cannot show
            # a run is not governed. And absence is what an rsync, a cleanup, a
            # dangling symlink, or an attacker produces — the destructive
            # mutation must never be the permissive one. Deleting the map alone
            # previously yielded NO_COMPOSITION here and persisted a durable
            # ``C + worker`` row through the real scheduler (reproduced).
            #
            # A run is positively ordinary only when it presents NO Wave 2
            # evidence at all: no scenario map AND no execution binding. Any
            # residue of a governed run, with no binding to evaluate it against,
            # is UNANSWERABLE.
            if map_present or binding_present:
                return DeclarationResult.unanswerable(
                    f"targets dir {self._targets_dir!r} is not candidate-shaped, so no "
                    f"candidate/run binding resolves — yet Wave 2 evidence is present "
                    f"(scenario_map={map_present}, execution_binding={binding_present}). "
                    f"This run may be governed and cannot be evaluated; refusing rather "
                    f"than treating unevaluable evidence as 'no composition'"
                )
            return DeclarationResult.no_composition(
                f"targets dir {self._targets_dir!r} is not candidate-shaped and presents "
                f"no Wave 2 evidence (no scenario map, no execution binding) — "
                f"positively an ordinary non-Wave-2 scheduler",
                # An ordinary run has no candidate/run identity of its own, so the
                # proof is bound to the ONLY identity it has: this targets dir.
                # The store is armed with the same value, so the binding check
                # still runs — a NO_COMPOSITION proven for one directory cannot
                # unseal a store belonging to another.
                run_id=_ORDINARY_RUN_SCOPE,
                candidate_sha=str(self._targets_dir or ""),
            )

        # From here the run IS a governed candidate run, so every input must be
        # readable. Absence is no longer "no composition" — it is UNANSWERABLE.
        binding = read_execution_binding(self._targets_dir)
        if binding is None:
            return DeclarationResult.unanswerable(
                f"governed run {run_id!r} (candidate {candidate_sha!r}) has no readable "
                f"execution binding — absent, unparseable, non-object, or a field that "
                f"failed coercion (``read_execution_binding`` collapses all of these to "
                f"None). The run's declaration cannot be determined"
            )
        if binding.run_id != run_id or binding.candidate_sha != candidate_sha:
            return DeclarationResult.unanswerable(
                f"execution binding claims run {binding.run_id!r} candidate "
                f"{binding.candidate_sha!r} but this run is {run_id!r}/{candidate_sha!r} "
                f"— a foreign or replayed binding cannot declare this run"
            )
        if not map_present:
            return DeclarationResult.unanswerable(
                f"governed run {run_id!r} has no scenario map — its composition "
                f"structure cannot be determined. (A run that genuinely has no "
                f"composition is proven so by resolved lineage, not by a missing file: "
                f"file absence is exactly what an rsync, a cleanup, or an attacker "
                f"produces.)"
            )
        try:
            declaration = build_verified_declaration(self._lineage_records(), binding=binding)
        except Exception as exc:  # noqa: BLE001 — DEFAULTS TO SEALED
            return DeclarationResult.unanswerable(
                f"lineage could not be resolved for governed run {run_id!r} "
                f"({type(exc).__name__}: {exc})"
            )
        if not declaration.execution_classes:
            # POSITIVE ABSENCE: lineage RESOLVED and declared no composition Task.
            #
            # TRUTHFULLY: unreachable for the CURRENT Wave 2 graph.
            # ``resolve_scenario_map`` requires exactly one node for EVERY entry of
            # SEMANTIC_LABELS — including ``integration_task_id`` — so a governed
            # Wave 2 run structurally always declares a composition Task, and a
            # run missing that node raises above rather than arriving here.
            #
            # It is kept because it is the only SAFE reading of "lineage resolved
            # and named nothing": the alternative (falling through to DECLARED
            # with an empty mapping) would arm the store with a declaration that
            # classifies nothing, which is indistinguishable from unarmed. If a
            # future graph shape makes label sets optional, this branch is
            # already correct rather than being discovered as a gap.
            return DeclarationResult.no_composition(
                f"governed run {run_id!r} lineage resolved and declares no composition "
                f"Task — ordinary worker execution only"
            )
        return DeclarationResult.declared(declaration)

    def _lineage_records(self) -> list[dict[str, Any]]:
        """PLAN + PACKET records only — the declaration's inputs.

        Strictly narrower than ``_canonical_records`` (which additionally loads
        the grant ledger for the AUTHORITY question). Keeping the grant out of
        the declaration's input set is what makes DECLARATION ≠ AUTHORIZATION
        structural rather than merely documented.
        """
        grants_filename = _canonical_grants_filename()
        records: list[dict[str, Any]] = []
        for path in self._required_record_sources():
            # Selected by NAME, not by list position: an index slice would break
            # silently the moment a source is added or reordered, and the failure
            # mode would be "the declaration quietly reads the grant again".
            if path.name == grants_filename:
                continue
            if not path.exists():
                logger.info("lineage record source absent (not yet written): %s", path)
                continue
            records.extend(_read_required_jsonl(path))
        return records

    def _declared_integration_packet_id(self) -> str:
        """The integration packet id this run's VERIFIED DECLARATION names.

        A pure read of the immutable snapshot — no file access, no digest
        recomputation, no authority question. Used to recognise which packet an
        authority-resolution FAILURE is about, so that failure can refuse
        admission instead of silently downgrading the integration Task to a
        worker. Never used to GRANT composition: that remains
        ``_validated_integration_packet_id``.

        Returns "" when the run declares no composition.
        """
        from substrate.execution.attempts.records import AttemptExecutionKind

        result = self._declaration_result
        if result is None or result.is_sealed:
            raise CompositionAuthorityUnresolved(self._declaration_refusal())
        if result.declaration is None:
            return ""  # POSITIVELY PROVEN: no composition Task in this run
        for tid, kind in result.declaration.execution_classes:
            if kind == AttemptExecutionKind.CONTROL_PLANE_COMPOSITION.value:
                return tid
        return ""

    def _downstream_base_resolver(self) -> Callable[[Any, list], str] | None:
        """The exact verified composition commit a dependent Task must build on."""
        repo, candidate, run_id = self._composition_binding()
        if not (repo and candidate and run_id):
            return None
        control_plane = self

        def _resolve(packet: Any, dependency_task_ids: list) -> str:
            from substrate.execution.attempts.composition import resolve_downstream_base

            return resolve_downstream_base(
                repo=repo,
                candidate=candidate,
                run_id=run_id,
                store=control_plane._store,
                proof_runtime=control_plane._proof_runtime,
                dependency_task_ids=[str(d) for d in (dependency_task_ids or [])],
            )

        return _resolve

    def _composition_acceptance_verifier(
        self,
    ) -> Callable[..., tuple[list[Any], Any]] | None:
        """Task C's REAL acceptance contract, run against the composed commit.

        The persisted contract says "make the FULL test suite pass (base +
        backend tests + frontend tests)". That sentence is never PARSED to pick
        behavior — prose is not control-plane authority. Instead the canonical
        contract text is hash-matched for equality, and the acceptance itself is
        the existing confined full-suite verifier.

        Three conjuncts, all required:
          1. the confined pytest run exits 0;
          2. the COLLECTION FLOOR holds — every predecessor-authored file is
             present. Bare pytest collects whatever happens to be there, so a
             composed tree missing both lanes' test files would go green on the
             6 base tests and prove nothing;
          3. the composed commit descends from BOTH predecessors.
        """
        repo, candidate, run_id = self._composition_binding()
        if not (repo and candidate and run_id):
            return None
        control_plane = self

        def _accept(
            attempt: Any, *, composed_commit: str, predecessor_commits: dict, packet: Any
        ) -> tuple[list[Any], Any]:
            import hashlib
            import tempfile

            from substrate.execution.attempts import field_task_scope as fts
            from substrate.execution.attempts.composition import (
                assert_descends_from_all,
                remove_verification_worktree,
                verification_worktree,
                verify_composed_scope,
                verify_predecessor_content,
            )
            from substrate.execution.attempts.verification import VerificationCheck
            from substrate.execution.attempts.verifier_isolation import (
                run_confined_verifier_checks,
            )

            checks: list[Any] = []

            # (1) Exact integration packet identity, via the validated map.
            target = control_plane._validated_integration_packet_id()
            packet_id = str(getattr(packet, "packet_id", ""))
            ident_ok = bool(target) and packet_id == target
            checks.append(
                VerificationCheck(
                    check_id="composition_packet_identity",
                    kind="policy",
                    ok=ident_ok,
                    detail=(
                        f"packet {packet_id} is the grant-authorized integration Task"
                        if ident_ok
                        else f"packet {packet_id} is NOT the validated integration Task "
                        f"({target!r}) — refusing composition acceptance"
                    ),
                )
            )

            # (2) Canonical contract equality — hash-match, never prose parsing.
            canonical = fts.task_contract_for(fts.INTEGRATION)
            persisted = str(getattr(packet, "desired_end_state", "") or "")
            want = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
            got = hashlib.sha256(persisted.encode("utf-8")).hexdigest()
            contract_ok = want == got
            checks.append(
                VerificationCheck(
                    check_id="composition_contract_match",
                    kind="policy",
                    ok=contract_ok,
                    detail=(
                        "persisted Task C contract equals the canonical contract"
                        if contract_ok
                        else f"persisted contract digest {got[:12]} ≠ canonical {want[:12]} "
                        f"— refusing to accept a drifted or foreign contract"
                    ),
                )
            )

            # (3) Ancestry from BOTH predecessors.
            missing = assert_descends_from_all(
                repo=repo,
                composed_commit=composed_commit,
                predecessor_commits=predecessor_commits,
            )
            checks.append(
                VerificationCheck(
                    check_id="composition_ancestry",
                    kind="commits",
                    ok=not missing,
                    detail=(
                        "composed commit descends from every predecessor"
                        if not missing
                        else f"composed commit does NOT descend from {missing}"
                    ),
                )
            )

            # (4) Confined full-suite acceptance at the EXACT composed commit,
            #     plus the predecessor-derived collection floor.
            work = tempfile.mkdtemp(prefix="umh-compverify-", dir=control_plane._run_root())
            checkout = os.path.join(work, "tree")
            evidence: Any = None
            try:
                verification_worktree(repo, composed_commit, checkout)

                base_rc, base_sha, _e = _git_read(
                    repo, ["merge-base", *predecessor_commits.values()]
                )
                content_ok, violations, produced = verify_predecessor_content(
                    repo=repo,
                    base=base_sha,
                    composed_tree=composed_commit,
                    predecessor_commits=predecessor_commits,
                )
                checks.append(
                    VerificationCheck(
                        check_id="composition_content_equivalence",
                        kind="diff",
                        ok=content_ok,
                        detail=(
                            f"all {len(produced)} predecessor effects survive"
                            if content_ok
                            else f"predecessor content lost: {violations[:5]}"
                        ),
                    )
                )

                # UNION-SCOPE containment. Every composed delta must be inside the
                # Task's PERSISTED writable_path_scope, judged by the same
                # `paths_outside` authority the worker diff-scope check uses.
                # Without it, composition could introduce content into the trusted
                # downstream base that a worker attempt would have been refused
                # for — the one bypass a control-plane-performed mutation could
                # otherwise open.
                from substrate.execution.attempts.field_task_scope import allowed_paths_for

                scope_ok, outside = verify_composed_scope(
                    repo=repo,
                    base=base_sha,
                    composed_tree=composed_commit,
                    allowed_paths=allowed_paths_for(packet),
                )
                checks.append(
                    VerificationCheck(
                        check_id="composition_scope_union",
                        kind="diff",
                        ok=scope_ok,
                        detail=(
                            "every composed delta is inside the declared union scope"
                            if scope_ok
                            else f"composed delta OUTSIDE the declared scope: {outside[:5]}"
                        ),
                    )
                )

                # COLLECTION FLOOR — derived from what the predecessors actually
                # produced, never from a hardcoded fixture filename.
                absent = [p for p in produced if not os.path.exists(os.path.join(checkout, p))]
                floor_ok = bool(produced) and not absent
                checks.append(
                    VerificationCheck(
                        check_id="composition_collection_floor",
                        kind="artifact",
                        ok=floor_ok,
                        detail=(
                            f"all {len(produced)} predecessor-authored files present in the "
                            f"verified checkout"
                            if floor_ok
                            else f"predecessor-authored files ABSENT from the composed "
                            f"checkout: {absent[:5]} — a green suite here would prove nothing"
                        ),
                    )
                )

                suite_checks, evidence = run_confined_verifier_checks(
                    attempt=attempt,
                    run_root=control_plane._run_root(),
                    source_path=checkout,
                    verifier_role_id=_INTEGRATOR_ROLE_ID,
                    worker_identity="",
                    base_commit=base_sha,
                    expected_result_commit=composed_commit,
                )
                checks.extend(suite_checks)
            finally:
                remove_verification_worktree(repo, checkout)
                shutil.rmtree(work, ignore_errors=True)

            return checks, evidence

        return _accept

    def _independent_checks_for(self, attempt: Any) -> Callable[[Any], list[Any]] | None:
        """Independent checks the VERIFIER runs itself for this attempt.

        C-4: worker-authored code (the fixture's pytest + its ``conftest.py``) runs
        ONLY through the canonical confined verifier seam
        (``run_confined_verifier_checks``) — a distinct verifier lease, bwrap-only
        (fail-closed, never an unconfined host subprocess), source mounted
        READ-ONLY, network unshared, credential-free env, parent-side zero-diff
        integrity proof, and lease teardown on every terminal path. This method
        NEVER runs worker-tree pytest directly on the host.

        Returns None when no fixture is wired (the context check then carries the
        weight); the qualification asserts a real confined check ran.
        """
        fixture = os.path.join(self._targets_dir, "fixture")
        if not os.path.isdir(fixture):
            return None

        control_plane = self

        def _checks(att: Any, *, effective_base: str = "") -> tuple[list[Any], Any]:
            from substrate.execution.attempts.verifier_isolation import (
                run_confined_verifier_checks,
            )

            # The integration source under verification is the lease worktree when
            # present (worker-authored), else the seeded fixture. Either way it is
            # mounted READ-ONLY inside bwrap and never executed on the host.
            lease = control_plane._lease_lookup(getattr(att, "lease_id", "") or "")
            worktree = str(getattr(lease, "worktree_path", "") or "") if lease else ""
            source = worktree if worktree and os.path.isdir(worktree) else fixture
            # base_commit is the AUTHORIZED diff base — the verifier reads the
            # actual worktree HEAD itself as verified_commit (C-4a). They are
            # never conflated.
            #
            # ``effective_base`` is the base the poller actually ENFORCED for this
            # attempt (the authorized trusted-projection re-anchor, when one was
            # allowed). This lookup returns a FRESH lease record carrying the
            # ledger's original snapshot_ref, so without the passed-in value the
            # Proof would attest to a base that was not the one enforced.
            base_commit = effective_base or (
                str(getattr(lease, "snapshot_ref", "") or "") if lease else ""
            )
            worker_identity = getattr(att, "worker_identity", "") or ""

            # Returns (checks, VerifierEvidence). The evidence is threaded through
            # verify_attempt → _persist_proof INTO this attempt's Proof — there is
            # NO process-local `_last_verifier_evidence` authority.
            return run_confined_verifier_checks(
                attempt=att,
                run_root=control_plane._run_root(),
                source_path=source,
                verifier_role_id=_VERIFIER_ROLE_ID,
                worker_identity=worker_identity,
                base_commit=base_commit,
                assignment_id=getattr(att, "assignment_id", "") or "",
                package_hash=getattr(att, "instruction_package_hash", "") or "",
            )

        return _checks

    def _lease_lookup(self, lease_id: str) -> Any:
        """Resolve the durable EnvironmentLease (never silently None)."""
        if not lease_id:
            return None
        getter = getattr(self._store, "get_lease", None)
        if not callable(getter):
            return None
        return _RecordView.wrap(getter(lease_id))

    # ── one bounded cycle ────────────────────────────────────────────────────

    def run_cycle(self) -> list[ControlPlaneCycleReport]:
        """One control-plane pass across every ACTIVE grant in the shared ledger.

        For each ACTIVE grant, run ONE poller pass: drain the worker outbox →
        apply canonical transitions with an independent verifier → run one
        scheduler pass so the next frontier is admitted and its dispatch
        envelopes are written to the inbox. The poller ALWAYS runs the scheduler
        after draining (even with an empty outbox), so the very first cycle
        admits the initial frontier — no separate admission pass is needed (a
        second, direct pass would re-enter admission for still-dispatched
        attempts and conflict on their active leases). Idempotent and safe to
        call repeatedly — terminal attempts are no-ops.
        """
        reports: list[ControlPlaneCycleReport] = []
        # Refresh the WorkPacket view from disk BEFORE reading grants. The driver
        # is a long-lived poll loop; ``ExecutionAttemptStore`` is stateless
        # per-call (every read hits disk), but ``UniversalWorkQueue`` caches its
        # packets in memory at construction and never reloads. The candidate app
        # writes the authorized packets (PLANNED→APPROVED) to disk AFTER the
        # runner starts, so without this reload ``get_packet`` returns None for
        # every packet minted this run and the frontier looks permanently
        # ``(missing)`` — the grant activates, the task is APPROVED on disk, and
        # yet no worker is ever dispatched. Reloading each cycle makes the queue
        # match the store's fresh-read contract.
        from substrate.execution.attempts.field_failure_policy import pause_state

        self._reload_queue()
        grants = [g for g in self._store.active_grants() if getattr(g, "status", "") == "active"]
        for grant in grants:
            report = ControlPlaneCycleReport(grant_ref=getattr(grant, "decision_ref", ""))
            try:
                # PRE-QUOTA GRAPH-SHAPE GATE. This is the last point before an
                # ACTIVE grant becomes signed dispatches — i.e. before any real
                # worker quota can be spent. A graph of the wrong shape is a
                # PLANNING defect that used to surface only after a worker had
                # already run (field run 20260726T025143Z-p1: one umbrella Task,
                # quota spent, then a guaranteed failure at the two-concurrent-
                # Tasks assertion). Refusing here costs zero quota.
                # SAME-RUN PRE-DISPATCH PAUSE (qualification only). Suppresses
                # ADMISSION exactly like the graph-shape gate below, and for the
                # same reason: this is the last point before an ACTIVE grant
                # becomes signed dispatches, so refusing here costs zero quota
                # and creates no attempt, lease, or assignment to unwind.
                #
                # It must gate ADMISSION, not the dispatch fn. The scheduler
                # transitions an attempt to DISPATCHED *before* invoking dispatch,
                # and DISPATCHED may only go to RUNNING/FAILED/CANCELLED — never
                # back to BLOCKED — so refusing inside the dispatch fn (by return
                # OR by raise) strands the attempt in DISPATCHED forever with no
                # envelope. Gating admission means no attempt is ever created.
                #
                # Result draining is deliberately NOT suppressed, matching the
                # graph-shape gate's precedent: a pause must never strand an
                # already-dispatched worker's result or its lease.
                paused, pause_reason = pause_state(self._targets_dir)
                if paused:
                    report.errors.append(f"paused_before_dispatch: {pause_reason}")
                    logger.info(
                        "field control-plane PAUSED before dispatch (zero quota spent) "
                        "for grant %s — %s",
                        getattr(grant, "decision_ref", ""),
                        pause_reason,
                    )
                shape = self._graph_shape_verdict(grant)
                shape_ok = shape is None or shape.get("ok", False)
                if not shape_ok:
                    report.errors.extend(
                        f"graph_shape_gate: {f}" for f in shape.get("failures", [])
                    )
                    logger.warning(
                        "field control-plane REFUSED admission (zero quota spent) — "
                        "graph shape invalid for grant %s: %s",
                        getattr(grant, "decision_ref", ""),
                        "; ".join(shape.get("failures", [])),
                    )
                scheduler = self._build_scheduler()
                poller = self._build_poller(scheduler, grant)
                # A failed gate suppresses ADMISSION only — never result
                # draining. `continue`ing here would skip the one path that
                # drains the worker outbox, so a transient gate failure (the
                # packet-visibility race _reload_queue exists for) would strand
                # already-dispatched workers: their results never applied, their
                # leases never released.
                pass_report = poller.run_pass(run_scheduler=shape_ok and not paused)
                report.results_drained = pass_report.results_drained
                report.succeeded = list(pass_report.succeeded)
                report.failed = list(pass_report.failed)
                report.admitted = list(pass_report.scheduler_admitted)
                # A PAUSED cycle is never idle. Idle means "this grant has no
                # work left to do"; paused means "work is deliberately withheld".
                # Conflating them would report a false idle state to the operator
                # and to reconciliation — the run looks finished while its whole
                # frontier is still waiting to be admitted.
                report.authority_unresolved = list(pass_report.authority_unresolved)
                # A cycle that REFUSED a Task for unresolvable composition
                # authority is not idle either. Idle means "no work left"; an
                # authority refusal means "work exists and we could not decide
                # whether we may run it". A refused Task creates no attempt
                # record, so without this term the run reports IDLE — i.e.
                # finished — while its integration Task never ran at all. That is
                # the same false-completion shape the paused/idle split above
                # exists to prevent.
                report.idle = (
                    not paused
                    and not report.authority_unresolved
                    and report.results_drained == 0
                    and not report.admitted
                    and not self._has_live_attempts(grant)
                )
                # EXTEND, never replace: the graph-shape refusal reasons were
                # recorded above and a plain assignment would discard them, so
                # a refused run would report no cause at all.
                report.errors.extend(pass_report.errors)
                report.skipped_not_approved = self._not_approved_frontier(grant)
            except Exception as exc:  # a bad grant never stalls the others
                # Surface the TEXT (review W8): the runner previously logged only
                # `errors=N`, so a systematic failure presented as a silent
                # counter with no cause.
                report.errors.append(f"{type(exc).__name__}: {exc}")
                logger.warning("field control-plane cycle failed: %s", exc, exc_info=True)
                logger.debug("field control-plane cycle failed: %s", exc, exc_info=True)
            reports.append(report)
        return reports

    def _graph_shape_verdict(self, grant: Any) -> dict[str, Any] | None:
        """Evaluate the persisted Task graph for one grant BEFORE dispatch.

        Returns ``None`` when the gate does not apply (it is enabled explicitly
        for the multi-lane field protocol, so a legitimate single-Task smoke
        objective is not misreported as a malformed graph). Read-only: it never
        creates, repairs, or re-scopes a Task, and it derives no authority — it
        asserts only what the persisted contracts already say.
        """
        if not self._enforce_graph_shape:
            return None
        from substrate.execution.attempts.graph_shape_gate import evaluate_graph_shape

        plan_id = str(getattr(grant, "plan_record_id", "") or "")
        frontier = [str(t) for t in (getattr(grant, "task_frontier", []) or [])]
        packets: list[dict[str, Any]] = []
        missing: list[str] = []
        for task_id in frontier:
            packet = self._queue.get_packet(task_id)
            if packet is None:
                # NEVER skip silently: skipping shrinks the evaluated set, so a
                # 6-Task grant with 2 unresolvable ids would present exactly 4
                # packets and PASS a gate whose whole purpose is fail-closed —
                # while the two unexamined Tasks dispatch. (The packet-visibility
                # race this hits is real: it is why _reload_queue exists.)
                missing.append(task_id)
                logger.debug("graph-shape gate: frontier task %s not resolvable", task_id)
                continue
            as_dict = packet.to_dict() if hasattr(packet, "to_dict") else dict(packet)
            packets.append(as_dict)
        # The zero-attempt invariant applies only to the FIRST admission for
        # this plan. Later cycles legitimately see live attempts (the driver is
        # a poll loop), so asserting it every cycle would refuse the run the
        # moment its own first worker started. Shape itself is re-checked every
        # cycle — only this one pre-dispatch invariant is first-cycle-only.
        #
        # This comment previously described an intent the code never
        # implemented: `attempt_count` was simply never passed, so the check was
        # skipped on EVERY cycle including the first and production evaluated 11
        # checks while the qualification claim said 12 (adversarial-review LOW).
        # Reading the ledger here arms it exactly once, as described.
        attempt_count: int | None = None
        try:
            existing = self._store.attempts_for_plan(plan_id)
            if not existing:
                attempt_count = 0
        except Exception as exc:  # ledger unreadable → leave the check unarmed
            logger.debug("graph-shape gate: attempt ledger unreadable: %s", exc)
        verdict = evaluate_graph_shape(
            packets=packets,
            plan_record_id=plan_id,
            attempt_count=attempt_count,
            frontier_size=len(frontier),
            unresolvable_tasks=missing,
        )
        return verdict.to_dict()

    def _not_approved_frontier(self, grant: Any) -> list[str]:
        """Frontier tasks whose packet is not yet APPROVED/DELEGATED.

        The scheduler silently skips these, so without reporting them an
        activation that failed to transition the packets looks identical to
        "no work to do" (review W5).
        """
        out: list[str] = []
        for task_id in list(getattr(grant, "task_frontier", []) or []):
            packet = self._queue.get_packet(task_id)
            if packet is None:
                out.append(f"{task_id}(missing)")
                continue
            status = getattr(getattr(packet, "status", None), "value", "")
            if status not in ("approved", "delegated"):
                out.append(f"{task_id}({status or 'unknown'})")
        return out

    def _has_live_attempts(self, grant: Any) -> bool:
        plan_id = getattr(grant, "plan_record_id", "")
        for att in self._store.attempts_for_plan(plan_id):
            if not att.is_terminal():
                return True
        return False


__all__ = [
    "FieldControlPlaneDriver",
    "ControlPlaneCycleReport",
]
