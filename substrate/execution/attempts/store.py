"""ExecutionAttemptStore — JSONL persistence for the canonical execution slice.

Faithful mirror of ``substrate.execution.planning.store.PlanningStore``:
append-only JSONL + ``tempfile``/``os.replace`` atomic rewrite, hardened with an
interprocess ``fcntl`` lock per file and compare-and-swap versioning. All paths
resolve through the runtime-state boundary (``<runtime-state>/operator/
execution_attempts/``). Module-level ``_DEFAULT_*`` constants are the established
monkeypatch seam for test isolation.

This store is the SOLE current execution truth (Amendment v1 clause 3). The
dispatch spool is transport only; nothing infers execution state from files on
the spool.

The single write path for an attempt's lifecycle is :meth:`transition_cas`
(record-version + expected-status CAS, transition-table + guard validation,
append-only history, identity-field immutability). Grants use
:meth:`update_grant_cas`.
"""

from __future__ import annotations

import json
import logging
import os
import tempfile
import threading
from contextlib import contextmanager
from typing import Any, Iterator

from substrate.execution.attempts.lifecycle import validate_transition
from substrate.execution.attempts.records import (
    ATTEMPT_IMMUTABLE_FIELDS,
    GRANT_IMMUTABLE_FIELDS,
    AttemptExecutionKind,
    AttemptTransition,
    DeclarationOutcome,
    DeclarationResult,
    ExecutionAttempt,
    ExecutionAuthorizationGrant,
    VerifiedExecutionDeclaration,
)

try:  # fcntl is POSIX-only; the store degrades to thread-locking elsewhere.
    import fcntl
except ImportError:  # pragma: no cover - non-POSIX fallback
    fcntl = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)

_SUBSYSTEM = "operator/execution_attempts"


def _resolve(filename: str) -> str:
    from substrate.state.runtime_paths import runtime_state_path

    return str(runtime_state_path(_SUBSYSTEM, filename, create_parent=False))


# The ONE canonical filename of the execution-authorization grant ledger.
# Separate from _DEFAULT_GRANTS_PATH because that path is a TEST-ISOLATION seam
# (monkeypatched to tmp files), so its basename is not a truthful production
# filename. Any component that must know where grants really live reads THIS —
# never its own literal. Restating the name elsewhere is what silently
# de-authorized the integration Task in field run 20260807T005250Z-p1.
_CANONICAL_GRANTS_FILENAME = "execution_authorization_grants.jsonl"

# Test-isolation seam: suites monkeypatch these module attributes to tmp paths.
_DEFAULT_ATTEMPTS_PATH = _resolve("execution_attempts.jsonl")
_DEFAULT_GRANTS_PATH = _resolve(_CANONICAL_GRANTS_FILENAME)
_DEFAULT_READINESS_PATH = _resolve("readiness_assessments.jsonl")
_DEFAULT_LEASES_PATH = _resolve("environment_leases.jsonl")
_DEFAULT_ASSIGNMENTS_PATH = _resolve("execution_assignments.jsonl")


# The governed-candidate ledger layout. A store whose attempts file lives under
# ``<root>/candidates/<lane>/<candidate>/state/...`` IS a governed candidate
# ledger, and that fact is intrinsic to the path — it cannot be asserted away by
# a caller. ``run_id`` is deliberately NOT here: it is not encoded in the store
# path (it lives under ``targets/<run>/``), so the store must never pretend to
# know it. See ``governed_subject``.
_CANDIDATES_SEGMENT = "candidates"
_STATE_SEGMENT = "state"


def governed_subject(attempts_path: str) -> tuple[str, str] | None:
    """(lane, candidate_sha) this ledger intrinsically belongs to, or None.

    THE PERSISTENCE BOUNDARY MUST OWN THE IDENTITY OF THE SUBJECT IT PROTECTS.

    Round 12 reproduced the consequence of not owning it: the store's ledger came
    from ``UMH_STATE_DIR`` while the declaration came from an independently
    supplied ``--targets-dir``. Point the latter at any ordinary directory and a
    NO_COMPOSITION proven about THAT directory unsealed the governed candidate's
    ledger, persisting an immutable ``Task C + worker`` row. The proof was valid;
    it was about the wrong subject.

    Production happens to derive both from one SHA today, so the two agree by
    CONVENTION. This function makes it an INVARIANT: the store derives what it
    can know from its own path and refuses any authority that disagrees.

    Uses pure lexical segments of an ABSOLUTE, normalized path — never
    ``dirname(dirname(...))``, whose answer changes with a trailing slash (a
    reproduced divergence). Returns None for any non-candidate ledger (tmp test
    stores, the ordinary runtime root), which leaves those callers unchanged.
    """
    try:
        parts = os.path.normpath(os.path.abspath(str(attempts_path))).split(os.sep)
    except (TypeError, ValueError):
        return None
    for i, seg in enumerate(parts):
        # Require the FULL shape: candidates/<lane>/<candidate>/state
        if seg == _CANDIDATES_SEGMENT and len(parts) > i + 3 and parts[i + 3] == _STATE_SEGMENT:
            lane, candidate = parts[i + 1], parts[i + 2]
            _reserved = (_CANDIDATES_SEGMENT, _STATE_SEGMENT)
            if lane and candidate and lane not in _reserved and candidate not in _reserved:
                return lane, candidate
    return None


def _is_active_status(status: Any) -> bool:
    """True if ``status`` will be READ as an active lease claim.

    Must normalise the way the SERIALIZER does, not the way ``str()`` does.
    An earlier version compared ``str(payload.get("status", ""))`` to
    "active" — which misses a ``(str, Enum)`` member, because ``str(St.ACTIVE)``
    is ``'St.ACTIVE'`` on this Python while ``json.dumps`` writes its VALUE,
    ``"active"``. The row bypassed the guard and then read back as a live claim
    (round-8 review B-1, reproduced: append WROTE, `active_lease_for_task` →
    True). That is the F1 door the guard exists to close.

    So: unwrap ``.value`` first, then compare. Deliberately exact — a missing,
    differently-cased or whitespace-padded status is NOT read as active by
    ``active_lease_for_task`` either, so writer and reader stay in agreement on
    one literal. Widening this to `.strip().lower()` would make the writer
    STRICTER than the reader, refusing rows that could never be claims.
    """
    # The serializer decides what lands on disk, so the guard must model it
    # exactly. `_append_line` uses `json.dumps(..., default=str)`:
    #   * a str (or str subclass) is written verbatim;
    #   * an Enum member is written as its VALUE;
    #   * anything else json cannot encode falls back to `str(obj)`.
    # Two earlier versions approximated this instead of asking, and each left a
    # hole: comparing `str(status)` missed a `(str, Enum)` member (B-1), and
    # short-circuiting on `.value` when it happened to be a str missed an object
    # whose `.value` says "released" while its `__str__` says "active" (B-2) —
    # the guard allowed the write and the reader claimed the row.
    #
    # There is no shortcut that is safe, because only the serializer decides
    # what lands on disk. So ASK IT: round-trip through the exact call
    # `_append_line` makes and compare the result. No approximation to drift.
    try:
        encoded = json.loads(json.dumps(status, default=str))
    except (TypeError, ValueError, RecursionError):
        # Unencodable: `_append_line` would raise too, so no row — no claim.
        return False
    return encoded == "active"


def _encoded_kind(value: Any) -> Any:
    """What ``_append_line`` will actually persist for ``value``.

    ``json.dumps(..., default=str)`` writes a str (or str subclass) verbatim, an
    Enum member as its VALUE, and anything else through ``str()``. Comparing
    guard inputs after this round-trip means the guard can never disagree with
    the row it is guarding.
    """
    try:
        return json.loads(json.dumps(value, default=str))
    except (TypeError, ValueError, RecursionError):
        # Unencodable: ``_append_line`` would raise too, so no row can result.
        # Return a sentinel that equals nothing, so the guard refuses.
        return object()


class AttemptStoreConflict(RuntimeError):
    """Raised when a compare-and-swap write loses to a concurrent writer, or a
    lifecycle guard rejects the transition."""


class ExecutionAttemptStore:
    """File-backed store for execution attempts, grants, readiness, and leases."""

    _thread_lock = threading.Lock()

    def __init__(
        self,
        attempts_path: str | None = None,
        grants_path: str | None = None,
        readiness_path: str | None = None,
        leases_path: str | None = None,
        assignments_path: str | None = None,
        *,
        declaration_result: DeclarationResult | None = None,
        governed_run: bool = False,
    ) -> None:
        # THE STRUCTURAL INVARIANT (see create_attempt_idempotent).
        #
        # A VERIFIED, IMMUTABLE run-scoped declaration — never a filename, never
        # a callable that re-reads mutable state on each call, and never a second
        # way for the store to decide what the integration Task is. The store
        # must not learn to read scenario_map.json, fixture literals, task names,
        # or infer from missing fields; that would move the pointwise defect down
        # a layer instead of removing it.
        #
        # It is a VALUE, not an accessor, deliberately. An accessor re-derives on
        # every call, so a file mutated after validation still changes the answer
        # — which is exactly the bypass the seventh review reproduced. A frozen
        # snapshot cannot be retargeted by any later write.
        self._verified_declaration: VerifiedExecutionDeclaration | None = None
        self._declaration_outcome: DeclarationOutcome | None = None

        # SEALED BY DEFAULT — but only for a GOVERNED Wave 2 run.
        #
        # `governed_run=True` means "this store belongs to a candidate run whose
        # execution declaration must be proven before anything is created". It
        # starts UNANSWERABLE and only `apply_declaration_result` with a
        # positively verified outcome can open it. Round 8 defaulted to
        # permissive-when-unarmed, and every one of the five reproduced bypasses
        # went through exactly that default.
        #
        # Non-Wave-2 callers (grant/read surfaces, legacy tooling) are unchanged:
        # they construct with `governed_run=False` (the default) and never enter
        # the sealed model at all. Defaulting THEM to sealed would be a broad
        # redesign of unrelated callers, which is out of scope — and unnecessary,
        # because source proves none of them can create Attempts.
        self._creation_sealed = (
            "governed run: no verified execution declaration has been applied yet "
            "(sealed by default — UNKNOWN MUST NEVER MEAN WORKER)"
            if governed_run
            else ""
        )
        self._attempts_path = attempts_path or _DEFAULT_ATTEMPTS_PATH
        self._grants_path = grants_path or _DEFAULT_GRANTS_PATH
        self._readiness_path = readiness_path or _DEFAULT_READINESS_PATH
        self._leases_path = leases_path or _DEFAULT_LEASES_PATH
        self._assignments_path = assignments_path or _DEFAULT_ASSIGNMENTS_PATH
        # THE SUBJECT THIS BOUNDARY PROTECTS — owned, not received.
        # Derived from our OWN ledger path, so no caller can substitute another
        # run's identity. None for ordinary (non-candidate) stores.
        self._governed_subject = governed_subject(self._attempts_path)
        # Applied AFTER the paths exist: the subject check reads _attempts_path,
        # and an ordering that armed before the path was set would have verified
        # against the wrong (default) ledger.
        if declaration_result is not None:
            self.apply_declaration_result(declaration_result)
        for p in (
            self._attempts_path,
            self._grants_path,
            self._readiness_path,
            self._leases_path,
            self._assignments_path,
        ):
            os.makedirs(os.path.dirname(p), exist_ok=True)

    def apply_declaration_result(
        self,
        result: DeclarationResult,
        *,
        run_id: str = "",
        candidate_sha: str = "",
    ) -> None:
        """THE ONLY transition out of the sealed state.

        Sealed→usable requires a POSITIVELY VERIFIED declaration result whose
        candidate/run binding matches this store's run context. There is
        deliberately no public ``unseal()`` an arbitrary caller can invoke, and
        no way to reach the permissive state by passing ``None``.

        The three outcomes map to exactly three behaviours:

          * DECLARED       — enforce the authenticated task→class mapping.
          * NO_COMPOSITION — unseal for ordinary worker-only execution. This is a
            POSITIVE PROOF that the run has no composition Task, never an
            absence.
          * UNANSWERABLE   — stay sealed. UNKNOWN MUST NEVER MEAN WORKER.

        Round 8 encoded the last two as the same ``None`` and three builder exits
        returned "cannot tell" while the store read "nothing to enforce": five
        reproduced bypasses persisted an immutable ``Task C + worker`` row.

        Single-shot, as before: re-applying an identical result is idempotent
        wiring; anything else raises, so no later call can retarget or disarm.
        """
        # EXACT type, not ``isinstance``. A subclass inherits the tag but not the
        # guarantees: ``Evil(DeclarationResult)`` (or a
        # ``VerifiedExecutionDeclaration`` subclass overriding
        # ``execution_class_for`` to lie) passed an isinstance check and unsealed
        # the store — reproduced. The sealed state may only be left on a value
        # this module itself defines.
        if type(result) is not DeclarationResult:
            raise AttemptStoreConflict(
                f"declaration result must be exactly a DeclarationResult, got "
                f"{type(result).__name__!r} — refusing to leave the sealed state on an "
                f"untyped or subclassed value (a subclass inherits the tag, not the "
                f"guarantees)"
            )
        # Re-validate the construction invariants that __post_init__ enforces.
        # A frozen dataclass can still be mutated via object.__setattr__ after
        # construction, bypassing __post_init__. This re-check closes that gap.
        if result.outcome is DeclarationOutcome.NO_COMPOSITION and result.declaration is not None:
            raise AttemptStoreConflict(
                "NO_COMPOSITION result carries a declaration payload — "
                "structurally incoherent (possible post-construction mutation)"
            )
        if result.outcome is DeclarationOutcome.DECLARED and result.declaration is None:
            raise AttemptStoreConflict(
                "DECLARED result carries no declaration payload — "
                "structurally incoherent (possible post-construction mutation)"
            )
        # ── SUBJECT BINDING — the store proves the authority is about ITSELF ──
        #
        # Round 12's reproduced bypass: the ledger came from UMH_STATE_DIR while
        # the declaration came from an independently supplied --targets-dir, so a
        # NO_COMPOSITION proven about an ordinary tmp directory unsealed a
        # governed candidate's ledger and persisted an immutable C+worker row.
        # Every prior round had the same shape — a valid proof about the wrong
        # subject — so this is checked ONCE here, for every outcome, rather than
        # per-branch.
        #
        # The store verifies every component it CAN know (lane+candidate, both
        # intrinsic to its path) and requires the run context for the rest.
        # run_id is NOT store-derivable (it lives under targets/<run>/), so it is
        # supplied — but it must arrive with a candidate that matches what the
        # store derived independently.
        subject = self._governed_subject
        if subject is not None and result.outcome is not DeclarationOutcome.UNANSWERABLE:
            lane, candidate = subject
            claimed = (
                result.declaration.candidate_sha
                if result.declaration is not None
                else result.candidate_sha
            )
            if str(claimed) != candidate:
                self._creation_sealed = (
                    f"this ledger belongs to governed candidate {candidate!r} (lane "
                    f"{lane!r}, derived from its own path), but the authority is about "
                    f"{claimed!r} — a proof about another subject cannot unseal this "
                    f"ledger; staying SEALED"
                )
                return
            if str(candidate_sha) != candidate:
                self._creation_sealed = (
                    f"this ledger belongs to governed candidate {candidate!r} but was "
                    f"armed with run context candidate {candidate_sha!r} — the caller's "
                    f"claimed subject disagrees with the store's own; staying SEALED"
                )
                return

        if result.outcome is DeclarationOutcome.UNANSWERABLE:
            self._creation_sealed = (
                result.reason or "the run's execution declaration is UNANSWERABLE"
            )
            return

        if result.outcome is DeclarationOutcome.DECLARED:
            declaration = result.declaration
            if declaration is None:
                # A DECLARED outcome with no declaration is a malformed result;
                # anything unexpected is UNANSWERABLE, never permissive.
                self._creation_sealed = (
                    "declaration result claims DECLARED but carries no declaration — "
                    "treating as UNANSWERABLE"
                )
                return
            # THE DECLARATION MUST GOVERN *THIS* RUN.
            #
            # A declaration built for candidate X / run X must never arm
            # candidate Y / run Y. Without this a correctly-built declaration can
            # certify a store it has nothing to do with — "built but not
            # governing", which is not protection.
            #
            # The run context is MANDATORY, never optional. It was previously
            # checked only ``if (run_id or candidate_sha)``, so a caller that
            # omitted both silently SKIPPED the check and any declaration armed
            # any governed store (reproduced). Treating absence as "skip" is the
            # same absence-means-two-things defect this whole round exists to
            # remove, one layer up: missing context must SEAL, not wave through.
            if not (run_id and candidate_sha):
                self._creation_sealed = (
                    f"declaration for run {declaration.run_id!r} was applied without a "
                    f"run context (run_id={run_id!r}, candidate_sha={candidate_sha!r}) — "
                    f"there is nothing to verify it against, so it cannot be shown to "
                    f"govern THIS store; staying SEALED"
                )
                return
            if not declaration.matches_run(run_id=run_id, candidate_sha=candidate_sha):
                self._creation_sealed = (
                    f"declaration is bound to run {declaration.run_id!r} candidate "
                    f"{declaration.candidate_sha!r} but this store's run context is "
                    f"{run_id!r}/{candidate_sha!r} — refusing to arm a store with a "
                    f"foreign declaration; staying SEALED"
                )
                return
            existing = self._verified_declaration
            if existing is not None and existing != declaration:
                raise AttemptStoreConflict(
                    f"refusing to REPLACE the installed verified execution declaration "
                    f"(run {existing.run_id!r} candidate {existing.candidate_sha!r}) with "
                    f"a different one (run {declaration.run_id!r} candidate "
                    f"{declaration.candidate_sha!r}) — a replaceable declaration is a "
                    f"mutable truth source and would re-open the retargeting bypass"
                )
            self._verified_declaration = declaration
            self._creation_sealed = ""
            self._declaration_outcome = DeclarationOutcome.DECLARED
            return

        # NO_COMPOSITION — positively proven; ordinary worker execution only.
        #
        # VERIFIED IDENTICALLY TO DECLARED. Asymmetric verification across the
        # branches of one enum was itself the defect: DECLARED required a
        # matching run context while NO_COMPOSITION ignored it entirely, so a
        # result that provably governs NOTHING unsealed any governed store
        # (reproduced). The proof must name the run it is a proof about.
        if not (run_id and candidate_sha):
            self._creation_sealed = (
                f"a NO_COMPOSITION result was applied without a run context "
                f"(run_id={run_id!r}, candidate_sha={candidate_sha!r}) — there is "
                f"nothing to verify it against; staying SEALED"
            )
            return
        if result.run_id != run_id or result.candidate_sha != candidate_sha:
            self._creation_sealed = (
                f"NO_COMPOSITION was proven for run {result.run_id!r} candidate "
                f"{result.candidate_sha!r}, but this store's run context is "
                f"{run_id!r}/{candidate_sha!r} — a proof about another run cannot "
                f"unseal this one; staying SEALED"
            )
            return
        if self._verified_declaration is not None:
            raise AttemptStoreConflict(
                f"refusing to downgrade an installed DECLARED declaration (run "
                f"{self._verified_declaration.run_id!r}) to NO_COMPOSITION — that "
                f"would disarm the structural write-boundary invariant"
            )
        self._creation_sealed = ""
        self._declaration_outcome = DeclarationOutcome.NO_COMPOSITION

    # ── Locking ──────────────────────────────────────────────────────────────

    @contextmanager
    def _file_lock(self, path: str) -> Iterator[None]:
        """Interprocess exclusive lock scoped to one store file."""
        with self._thread_lock:
            lock_path = path + ".lock"
            fd = os.open(lock_path, os.O_CREAT | os.O_RDWR, 0o644)
            try:
                if fcntl is not None:
                    fcntl.flock(fd, fcntl.LOCK_EX)
                yield
            finally:
                try:
                    if fcntl is not None:
                        fcntl.flock(fd, fcntl.LOCK_UN)
                finally:
                    os.close(fd)

    # ── Generic JSONL helpers ────────────────────────────────────────────────

    @staticmethod
    def _append_line(path: str, payload: dict[str, Any]) -> None:
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(payload, default=str, separators=(",", ":")) + "\n")

    @staticmethod
    def _read_lines(path: str) -> list[dict[str, Any]]:
        if not os.path.exists(path):
            return []
        rows: list[dict[str, Any]] = []
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError as exc:
                    logger.debug("skipping malformed execution line in %s: %s", path, exc)
        return rows

    @staticmethod
    def _rewrite_atomic(path: str, rows: list[dict[str, Any]]) -> None:
        dir_name = os.path.dirname(path)
        fd, tmp_path = tempfile.mkstemp(dir=dir_name, suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                for row in rows:
                    f.write(json.dumps(row, default=str, separators=(",", ":")) + "\n")
            os.replace(tmp_path, path)
        except Exception:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
            raise

    # ── Attempts: reads ──────────────────────────────────────────────────────

    def get_attempt(self, attempt_id: str) -> ExecutionAttempt | None:
        for row in self._read_lines(self._attempts_path):
            if row.get("attempt_id") == attempt_id:
                return ExecutionAttempt.from_dict(row)
        return None

    def attempts_for_task(self, task_id: str) -> list[ExecutionAttempt]:
        rows = [r for r in self._read_lines(self._attempts_path) if r.get("task_id") == task_id]
        attempts = [ExecutionAttempt.from_dict(r) for r in rows]
        return sorted(attempts, key=lambda a: a.attempt_number)

    def attempts_for_plan(self, plan_record_id: str) -> list[ExecutionAttempt]:
        rows = [
            r
            for r in self._read_lines(self._attempts_path)
            if r.get("plan_record_id") == plan_record_id
        ]
        return [ExecutionAttempt.from_dict(r) for r in rows]

    def active_attempts(self) -> list[ExecutionAttempt]:
        out: list[ExecutionAttempt] = []
        for row in self._read_lines(self._attempts_path):
            attempt = ExecutionAttempt.from_dict(row)
            if not attempt.is_terminal():
                out.append(attempt)
        return out

    def has_active_attempt_for_task(self, task_id: str) -> bool:
        for row in self._read_lines(self._attempts_path):
            if row.get("task_id") != task_id:
                continue
            attempt = ExecutionAttempt.from_dict(row)
            if not attempt.is_terminal():
                return True
        return False

    # ── Attempts: writes ─────────────────────────────────────────────────────

    def create_attempt_idempotent(self, attempt: ExecutionAttempt) -> tuple[ExecutionAttempt, bool]:
        """Create an attempt, or return the existing one for the same logical
        key. The idempotency key is
        ``(task_id, execution_authorization_ref, attempt_number)`` — a duplicate
        request (browser retry, queue reload, duplicate message) returns the
        EXISTING attempt and ``created=False``; it never mints a second one.

        STRUCTURAL INVARIANT — a Task DECLARED as the control-plane composition
        Task may never become durable as ``execution_kind="worker"``.

        This is the single authoritative write boundary: exactly one production
        path constructs an attempt (``AttemptScheduler._create_attempt``) and it
        persists through here, so a check placed here cannot be bypassed by a
        caller that forgets to behave. Six successive review rounds each found a
        NEW pointwise route to the same end state — wrong grant filename, an
        incomplete required-source set, an empty ledger read as authority, a
        DENIED verdict arriving after the pass's single grant re-read, an
        unparsed run binding, and a sibling exception type escaping the
        scheduler's handler. Every one produced the same durable outcome: Task C
        persisted as a worker, immutably (``execution_kind`` is in
        ``ATTEMPT_IMMUTABLE_FIELDS``), so no later healthy pass can correct it,
        and it is then dispatched to a real model worker.

        Defending that invariant at each decision point requires every future
        path to remember it. Enforcing it HERE makes the bad state unreachable.

        The declaration is a VERIFIED, IMMUTABLE run-scoped snapshot
        (``VerifiedExecutionDeclaration``), never a filename and never a callable
        that re-reads mutable state: the seventh review round moved the
        declaration itself (``integration_task_id`` is an unauthenticated field
        while the authority path digest-verifies that same field), which
        silently disarmed every gate keyed off it. A frozen snapshot built from
        recomputed lineage cannot be retargeted by any later write.

        Declaration and authority stay separate concerns — "this Task IS the
        composition Task" is durable, while "may composition run right now?" is
        the grant question. A denied or unresolved grant therefore yields NO
        attempt, never a worker attempt.

        The invariant applies to BOTH outcomes of this call: a NEW insert and an
        idempotent return of an EXISTING row. Idempotency must never legitimize
        an invalid historical record — a pre-existing ``C + worker`` row returned
        as success would be dispatched to a model worker exactly as if it had
        just been created, and ``execution_kind`` is immutable so it can never be
        repaired.
        """
        self._assert_declared_kind(attempt.task_id, attempt.execution_kind, origin="this attempt")

        with self._file_lock(self._attempts_path):
            rows = self._read_lines(self._attempts_path)
            for row in rows:
                if (
                    row.get("task_id") == attempt.task_id
                    and row.get("execution_authorization_ref")
                    == attempt.execution_authorization_ref
                    and int(row.get("attempt_number", -1)) == attempt.attempt_number
                ):
                    existing = ExecutionAttempt.from_dict(row)
                    # The EXISTING row is validated against the SAME declaration.
                    # A corrupt row is preserved on disk as evidence — never
                    # returned as success, never dispatched, and never mutated
                    # into composition (that would forge a clean history over a
                    # real corruption).
                    self._assert_declared_kind(
                        existing.task_id,
                        existing.execution_kind,
                        origin=f"the EXISTING durable row {existing.attempt_id!r}",
                    )
                    return existing, False
            self._append_line(self._attempts_path, attempt.to_dict())
            return attempt, True

    def _assert_declared_kind(self, task_id: str, execution_kind: Any, *, origin: str) -> None:
        """Refuse any execution_kind that contradicts the verified declaration.

        Shared by the INSERT and IDEMPOTENT-RETURN paths of
        ``create_attempt_idempotent`` so the two can never diverge — a guard that
        exists on only one of them is a guard with a door next to it.
        """
        if self._creation_sealed:
            raise AttemptStoreConflict(
                f"attempt creation is SEALED for this run — {self._creation_sealed}. "
                f"Refusing {origin} for task {task_id}: with no verified declaration "
                f"the execution class of this Task cannot be established, and an "
                f"unarmed write boundary would let the integration Task persist as a "
                f"worker (immutably, and it would then dispatch)"
            )
        declaration = self._verified_declaration
        if declaration is None:
            return
        # Read the frozen tuple DIRECTLY rather than calling the accessor: a
        # ``VerifiedExecutionDeclaration`` subclass overriding
        # ``execution_class_for`` to return None disarmed the guard (reproduced).
        # The data is immutable; the method is not.
        declared = None
        for _tid, _kind in declaration.execution_classes:
            if _tid == task_id:
                declared = _kind
                break
        # The check is BIDIRECTIONAL. A declared Task must match its declaration,
        # AND an UNDECLARED Task may not be promoted into the composition
        # lifecycle. A one-directional check ("declared ⇒ must match") would let a
        # future producer mint a composition attempt for an arbitrary Task — the
        # mirror image of the defect this guard exists to prevent, and equally
        # unrecoverable because ``execution_kind`` is immutable.
        expected = declared if declared is not None else AttemptExecutionKind.WORKER.value
        # Compare what the SERIALIZER will write, not what ``str()`` renders.
        #
        # ``_is_active_status`` above already reached this conclusion for lease
        # status, verbatim: "only the serializer decides what lands on disk".
        # This guard was left on ``str(x)``, so a ``str`` subclass overriding
        # ``__str__`` passed the check while ``json.dumps`` wrote its real value
        # — the guard and the row disagreeing about what was persisted
        # (reproduced). Round-tripping through the exact ``_append_line`` call
        # removes the approximation instead of patching one shape of it.
        if _encoded_kind(execution_kind) != _encoded_kind(expected):
            raise AttemptStoreConflict(
                f"task {task_id} is DECLARED as execution class {expected!r}"
                f"{'' if declared is not None else ' (undeclared ⇒ ordinary worker)'} "
                f"by the verified declaration for run {declaration.run_id!r} "
                f"(candidate {declaration.candidate_sha!r}), but {origin} carries "
                f"execution_kind={execution_kind!r} — refusing. execution_kind is "
                f"immutable, so a wrong class here is permanent and would send the "
                f"declared composition Task to a model worker"
            )

    def transition_cas(
        self,
        attempt_id: str,
        to_status: str,
        expected_record_version: int,
        expected_statuses: tuple[str, ...],
        actor: str,
        reason: str = "",
        updates: dict[str, Any] | None = None,
        event_id: str = "",
    ) -> ExecutionAttempt:
        """THE single lifecycle write path (CAS-protected).

        Under the attempts-file lock: reads the row; raises
        :class:`AttemptStoreConflict` on record-version mismatch, on an on-disk
        status outside ``expected_statuses``, or when the record vanished;
        validates ``(status → to_status)`` against the transition table and its
        guards; applies ``updates`` to binding fields only (identity fields are
        immutable — a write to one raises); appends an
        :class:`AttemptTransition`; bumps ``record_version``; atomically
        rewrites. Never blind-overwrites.
        """
        updates = dict(updates or {})
        illegal = ATTEMPT_IMMUTABLE_FIELDS & set(updates)
        if illegal:
            raise AttemptStoreConflict(
                f"attempt {attempt_id}: cannot mutate immutable identity fields {sorted(illegal)}"
            )

        with self._file_lock(self._attempts_path):
            rows = self._read_lines(self._attempts_path)
            for i, row in enumerate(rows):
                if row.get("attempt_id") != attempt_id:
                    continue
                on_disk_version = int(row.get("record_version", -1))
                if on_disk_version != expected_record_version:
                    raise AttemptStoreConflict(
                        f"attempt {attempt_id}: expected record_version "
                        f"{expected_record_version}, found {on_disk_version}"
                    )
                on_disk_status = row.get("status")
                if on_disk_status not in expected_statuses:
                    raise AttemptStoreConflict(
                        f"attempt {attempt_id}: status {on_disk_status!r} not in expected "
                        f"{list(expected_statuses)}"
                    )
                attempt = ExecutionAttempt.from_dict(row)
                # THE DECLARATION GOVERNS THE LIFECYCLE TOO.
                #
                # `create_attempt_idempotent` guards both insert and idempotent
                # return, but this is the OTHER durable write path. Without the
                # check, a poisoned `Task C + worker` row already on disk (legacy
                # data, a restored backup, a concurrent writer) can be advanced
                # through the lifecycle toward a real model worker without ever
                # calling the guarded method — reproduced to LEASED. Refusing at
                # creation while permitting advancement is a guard with a door
                # next to it.
                self._assert_declared_kind(
                    attempt.task_id,
                    attempt.execution_kind,
                    origin=f"the lifecycle transition {on_disk_status!r}→{to_status!r} of "
                    f"row {attempt_id!r}",
                )
                # Validate the transition + guards against the on-disk state,
                # with the pending binding updates in view.
                validate_transition(attempt, to_status, actor, updates)
                # Apply binding updates.
                for key, value in updates.items():
                    setattr(attempt, key, value)
                # Append immutable history entry.
                transition = AttemptTransition(
                    from_status=on_disk_status,
                    to_status=to_status,
                    actor=actor,
                    reason=reason,
                    event_id=event_id,
                )
                attempt.transitions.append(transition.to_dict())
                attempt.status = to_status
                attempt.record_version = on_disk_version + 1
                import time as _time

                attempt.updated_at = _time.time()
                rows[i] = attempt.to_dict()
                self._rewrite_atomic(self._attempts_path, rows)
                return attempt
            raise AttemptStoreConflict(f"attempt {attempt_id} not found for CAS transition")

    # ── Grants ───────────────────────────────────────────────────────────────

    def get_grant(self, decision_ref: str) -> ExecutionAuthorizationGrant | None:
        for row in self._read_lines(self._grants_path):
            if row.get("decision_ref") == decision_ref:
                return ExecutionAuthorizationGrant.from_dict(row)
        return None

    def get_grant_by_id(self, grant_id: str) -> ExecutionAuthorizationGrant | None:
        for row in self._read_lines(self._grants_path):
            if row.get("grant_id") == grant_id:
                return ExecutionAuthorizationGrant.from_dict(row)
        return None

    def grants_for_plan(self, plan_record_id: str) -> list[ExecutionAuthorizationGrant]:
        rows = [
            r
            for r in self._read_lines(self._grants_path)
            if r.get("plan_record_id") == plan_record_id
        ]
        return [ExecutionAuthorizationGrant.from_dict(r) for r in rows]

    def active_grants(self) -> list[ExecutionAuthorizationGrant]:
        out: list[ExecutionAuthorizationGrant] = []
        for row in self._read_lines(self._grants_path):
            grant = ExecutionAuthorizationGrant.from_dict(row)
            if grant.is_active():
                out.append(grant)
        return out

    def create_grant_idempotent(
        self, grant: ExecutionAuthorizationGrant
    ) -> tuple[ExecutionAuthorizationGrant, bool]:
        """Create or reuse the one grant for a ``decision_ref`` (Amendment v1
        clause 2: activation reuses one grant). Returns ``(grant, created)``."""
        with self._file_lock(self._grants_path):
            rows = self._read_lines(self._grants_path)
            for row in rows:
                if row.get("decision_ref") == grant.decision_ref:
                    return ExecutionAuthorizationGrant.from_dict(row), False
            self._append_line(self._grants_path, grant.to_dict())
            return grant, True

    def update_grant_cas(
        self,
        grant: ExecutionAuthorizationGrant,
        expected_record_version: int,
        expected_statuses: tuple[str, ...] | None = None,
    ) -> ExecutionAuthorizationGrant:
        """CAS update of one grant record (status/bounds progression/decision
        log). Fails with :class:`AttemptStoreConflict` on version mismatch,
        status outside ``expected_statuses``, immutable-field mutation, or a
        vanished record."""
        with self._file_lock(self._grants_path):
            rows = self._read_lines(self._grants_path)
            for i, row in enumerate(rows):
                if row.get("grant_id") != grant.grant_id:
                    continue
                on_disk_version = int(row.get("record_version", -1))
                if on_disk_version != expected_record_version:
                    raise AttemptStoreConflict(
                        f"grant {grant.grant_id}: expected record_version "
                        f"{expected_record_version}, found {on_disk_version}"
                    )
                if expected_statuses is not None and row.get("status") not in expected_statuses:
                    raise AttemptStoreConflict(
                        f"grant {grant.grant_id}: status {row.get('status')!r} not in expected "
                        f"{list(expected_statuses)}"
                    )
                for fld in GRANT_IMMUTABLE_FIELDS:
                    if getattr(grant, fld) != row.get(fld):
                        raise AttemptStoreConflict(
                            f"grant {grant.grant_id}: immutable field {fld!r} may not change"
                        )
                import time as _time

                grant.record_version = on_disk_version + 1
                grant.updated_at = _time.time()
                rows[i] = grant.to_dict()
                self._rewrite_atomic(self._grants_path, rows)
                return grant
            raise AttemptStoreConflict(f"grant {grant.grant_id} not found for CAS update")

    # ── Readiness (append-only evidence) ─────────────────────────────────────

    def append_readiness(self, assessment: Any) -> None:
        payload = assessment.to_dict() if hasattr(assessment, "to_dict") else dict(assessment)
        with self._file_lock(self._readiness_path):
            self._append_line(self._readiness_path, payload)

    def get_readiness(self, assessment_id: str) -> dict[str, Any] | None:
        for row in self._read_lines(self._readiness_path):
            if row.get("assessment_id") == assessment_id:
                return row
        return None

    # ── Assignments (durable placement records) ──────────────────────────────

    def append_assignment(self, assignment: Any) -> None:
        payload = assignment.to_dict() if hasattr(assignment, "to_dict") else dict(assignment)
        with self._file_lock(self._assignments_path):
            self._append_line(self._assignments_path, payload)

    def get_assignment(self, assignment_id: str) -> dict[str, Any] | None:
        for row in self._read_lines(self._assignments_path):
            if row.get("assignment_id") == assignment_id:
                return row
        return None

    def assignment_for_attempt(self, attempt_id: str) -> dict[str, Any] | None:
        latest: dict[str, Any] | None = None
        for row in self._read_lines(self._assignments_path):
            if row.get("attempt_id") == attempt_id:
                latest = row
        return latest

    # ── Leases ───────────────────────────────────────────────────────────────

    def append_lease(self, lease: Any) -> None:
        """Append a lease row that does NOT claim the task. Never for acquisition.

        Round-8 review M-3: this is the obvious name sitting beside the guarded
        one, it has ZERO production callers, and reaching for it to acquire a
        lease reintroduces F1 (the CRITICAL check-then-act that put two workers
        on one Task). `acquire()` must use `append_lease_if_no_active`, which
        performs the uniqueness check and the append in ONE critical section.

        So this refuses an ACTIVE row outright. Legitimate uses — recording a
        released/expired/revoked lease — are unaffected, and a future caller
        reaching for the wrong name gets an error instead of a silent race.
        """
        payload = lease.to_dict() if hasattr(lease, "to_dict") else dict(lease)
        if _is_active_status(payload.get("status")):
            raise AttemptStoreConflict(
                "append_lease cannot write an ACTIVE lease — that is a task "
                "CLAIM and must go through append_lease_if_no_active, which "
                "checks and appends atomically (F1)"
            )
        with self._file_lock(self._leases_path):
            self._append_line(self._leases_path, payload)

    def append_lease_if_no_active(self, lease: Any) -> None:
        """Append a lease ONLY if its task has no active lease — atomically.

        `acquire()` used to read `active_lease_for_task` and then append in a
        separate `append_lease` call. Both operations locked, but the window
        BETWEEN them did not — and git-worktree creation sits inside that
        window. Two callers could each observe "no active lease" and each
        append, producing two concurrent active leases for one Task
        (reproduced 5/25 trials directly, 1/20 through the real scheduler:
        round-7 adversarial review F1).

        Two active leases means two real workers mutating one Task's workspace
        under a single authorization, with two dispatch envelopes and two Proof
        paths — the invariant that bounds the worktree, tool profile,
        credential scope and billed worker.

        The check and the append are therefore ONE critical section here.
        Callers must treat `AttemptStoreConflict` as "someone else won the
        race" and clean up any environment they already created.
        """
        payload = lease.to_dict() if hasattr(lease, "to_dict") else dict(lease)
        task_id = str(payload.get("task_id", "") or "")
        with self._file_lock(self._leases_path):
            latest_by_id: dict[str, dict[str, Any]] = {}
            for row in self._read_lines(self._leases_path):
                if row.get("task_id") == task_id:
                    latest_by_id[row.get("lease_id", "")] = row
            for row in latest_by_id.values():
                if row.get("status") == "active":
                    raise AttemptStoreConflict(
                        f"task {task_id} already has an active lease ({row.get('lease_id', '')})"
                    )
            self._append_line(self._leases_path, payload)

    def get_lease(self, lease_id: str) -> dict[str, Any] | None:
        latest: dict[str, Any] | None = None
        for row in self._read_lines(self._leases_path):
            if row.get("lease_id") == lease_id:
                latest = row
        return latest

    def active_lease_for_task(self, task_id: str) -> dict[str, Any] | None:
        """Return the newest non-released/revoked/expired lease for a task."""
        latest_by_id: dict[str, dict[str, Any]] = {}
        for row in self._read_lines(self._leases_path):
            if row.get("task_id") == task_id:
                latest_by_id[row.get("lease_id", "")] = row
        for row in latest_by_id.values():
            if row.get("status") == "active":
                return row
        return None

    def update_lease_cas(
        self,
        lease: Any,
        expected_record_version: int,
        expected_statuses: tuple[str, ...] | None = None,
    ) -> Any:
        """CAS update of one lease record (append-latest-wins semantics: the
        newest row per lease_id is truth)."""
        lease_id = lease.lease_id if hasattr(lease, "lease_id") else lease.get("lease_id")
        payload = lease.to_dict() if hasattr(lease, "to_dict") else dict(lease)
        with self._file_lock(self._leases_path):
            rows = self._read_lines(self._leases_path)
            current: dict[str, Any] | None = None
            for row in rows:
                if row.get("lease_id") == lease_id:
                    current = row
            if current is None:
                raise AttemptStoreConflict(f"lease {lease_id} not found for CAS update")
            on_disk_version = int(current.get("record_version", -1))
            if on_disk_version != expected_record_version:
                raise AttemptStoreConflict(
                    f"lease {lease_id}: expected record_version {expected_record_version}, "
                    f"found {on_disk_version}"
                )
            if expected_statuses is not None and current.get("status") not in expected_statuses:
                raise AttemptStoreConflict(
                    f"lease {lease_id}: status {current.get('status')!r} not in expected "
                    f"{list(expected_statuses)}"
                )
            payload["record_version"] = on_disk_version + 1
            rows.append(payload)
            self._rewrite_atomic(self._leases_path, rows)
            return payload


__all__ = ["ExecutionAttemptStore", "AttemptStoreConflict"]
