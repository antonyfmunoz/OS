"""Wave 2 field failure-injection policy (qualification harness only).

The failure-qualification pass must inject a GENUINE worker failure — not a
poisoned fixture — so the graph provably fails the right way: the BACKEND task's
first attempt runs with its file-mutation tools revoked, the real worker cannot
commit, verification refuses (no Proof), C stays blocked, and a retry (A2,
unrevoked) lets the graph continue.

Targeting is by EXACT CANONICAL TASK ID (finding C2)
-----------------------------------------------------
The previous implementation pattern-matched imagined identifiers
(``tid == "a"``, ``tid.endswith("-a")``, …). Real packets are minted as
``wp-<uuid4().hex[:12]>`` by ``WorkPacket``, and a hex12 suffix contains no
``-``, so **0 of 2000 real ids matched** — arming the variant revoked nothing and
the failure pass silently ran clean. That is exactly the false green this module
exists to prevent.

The harness now records a SCENARIO MAP of the actual materialized packet ids at
fixture/plan creation:

    {"backend_task_id": "wp-3f9c1ab77e21",
     "frontend_task_id": "wp-…", "integration_task_id": "wp-…",
     "verification_task_id": "wp-…"}

and the marker names the exact task it targets. Matching is equality against a
recorded id — never a pattern.

Fail closed: if a ``tools-revoked-*`` variant is armed but the scenario map is
missing or does not name the target, ``arming_is_valid()`` reports False and the
run must be treated as INVALID rather than green — an armed failure that never
fired must never be mistaken for a recovered one.

Scope: qualification only. There is no general "inject failure" capability in the
runtime.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

# The exact revocation for the tools-revoked-backend variant. Bash is included:
# with only Edit/Write/MultiEdit/NotebookEdit revoked a CLI worker can still
# `bash -c 'cat > file'` and commit, so the "genuine failure" would not be
# genuine (review W9).
_TOOLS_REVOKED = ["Edit", "Write", "MultiEdit", "NotebookEdit", "Bash"]

_MARKER_NAME = ".inject_failure"
_SCENARIO_NAME = "scenario_map.json"

# ── same-run pre-dispatch pause (qualification only) ──────────────────────────
#
# The failure-qualification pass needs a window that did not previously exist.
# `inject-failure` can only arm against the EXACT canonical task id, which is
# resolvable only from an `execution_binding.json` captured from THIS run's
# grant — and that grant exists only after the collector drives approval +
# activation. But the full scenario ran `w15_authorize_execution` straight into
# `w16_ab_running_concurrent`: the control-plane driver turned the freshly ACTIVE
# grant into dispatch envelopes immediately, so the arming window was zero-width.
# Cross-run binding reuse is (correctly) rejected by `validate_scenario_map`, so
# a "prepare the binding in an earlier pass" workaround is not available either.
#
# The gate is a run-scoped MARKER FILE checked at SCHEDULER ADMISSION
# (`FieldControlPlaneDriver.run_cycle`, beside the graph-shape gate), so the
# sequence becomes:
#
#     authorize → grant + binding durable → (paused, zero admissions)
#     → write-scenario-map → inject-failure → resume → A1 fails → A2 recovers
#
# ADMISSION, not dispatch — this is load-bearing and two earlier designs got it
# wrong. The scheduler transitions an attempt to DISPATCHED *before* invoking
# the dispatch fn, and DISPATCHED may only go to RUNNING/FAILED/CANCELLED (never
# back to BLOCKED), so refusing inside the dispatch fn — by silent return OR by
# raising — strands the attempt in DISPATCHED forever, holding a lease, with no
# envelope and no legal transition out. Gating admission means no Attempt,
# assignment, or lease is ever created, so there is nothing to unwind and no
# post-dispatch rollback is needed. Result draining is deliberately NOT
# suppressed, so a pause can never strand an already-dispatched worker.
#
# Deliberately NOT a general workflow-pause framework: one marker, one run
# directory, one consumption point, qualification scope only. It lives beside
# `.inject_failure` because it has the same lifetime and the same blast radius.
#
# FAIL CLOSED: an unreadable marker counts as PAUSED. A gate that opens when it
# cannot read its own state is the fail-open shape this campaign has repeatedly
# had to correct — an ambiguous read must never release workers.
_PAUSE_NAME = ".pause_before_dispatch"

# Variant name. The legacy spelling is accepted so an existing runbook/CLI does
# not silently arm nothing, but it resolves through the scenario map exactly the
# same way — there is no id pattern matching on any path.
_VARIANT_BACKEND = "tools-revoked-backend"
_VARIANT_LEGACY = "tools-revoked-a"
_REVOKING_VARIANTS = frozenset({_VARIANT_BACKEND, _VARIANT_LEGACY})

_SCENARIO_KEYS = (
    "backend_task_id",
    "frontend_task_id",
    "integration_task_id",
    "verification_task_id",
)


def scenario_map_path(targets_dir: str | os.PathLike[str]) -> Path:
    return Path(targets_dir) / _SCENARIO_NAME


def write_scenario_map(targets_dir: str | os.PathLike[str], mapping: dict[str, str]) -> Path:
    """Persist the run's canonical task identities.

    Called once the fixture Plan has materialized its WorkPackets, so the harness
    knows the REAL ``wp-*`` ids it must target.
    """
    path = scenario_map_path(targets_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    recorded = {k: str(mapping.get(k, "") or "") for k in _SCENARIO_KEYS}
    path.write_text(json.dumps(recorded, indent=2, sort_keys=True), encoding="utf-8")
    return path


def read_scenario_map(targets_dir: str | os.PathLike[str]) -> dict[str, str]:
    """Return the run's canonical task identities ({} when absent/unreadable)."""
    try:
        data = json.loads(scenario_map_path(targets_dir).read_text(encoding="utf-8"))
    except (FileNotFoundError, OSError, ValueError):
        return {}
    if not isinstance(data, dict):
        return {}
    return {k: str(v) for k, v in data.items() if isinstance(v, str) and v}


def read_variant(targets_dir: str | os.PathLike[str]) -> str:
    """Return the armed failure variant for a run ('' if none/clean)."""
    marker = Path(targets_dir) / _MARKER_NAME
    try:
        variant = marker.read_text(encoding="utf-8").strip()
    except (FileNotFoundError, OSError):
        return ""
    return variant if variant and variant != "clean" else ""


def pause_marker_path(targets_dir: str | os.PathLike[str]) -> Path:
    """The run-scoped pre-dispatch pause marker for this targets dir."""
    return Path(targets_dir) / _PAUSE_NAME


# The identifiers a pause marker must carry to be honored. Path scoping alone
# (``<sha>/targets/<run_id>/``) already makes cross-run reuse physically hard,
# but "hard" is not "proven": a marker copied, restored from evidence, or
# written by a stale process would otherwise suppress admission for a run it was
# never issued against. The marker therefore names its own binding and is
# checked against the run's captured `execution_binding.json`.
_PAUSE_BINDING_FIELDS = ("run_id", "candidate_sha", "grant_id", "decision_ref")


def arm_pause_before_dispatch(targets_dir: str | os.PathLike[str]) -> Path:
    """Arm the pre-dispatch pause for THIS run, bound to its execution binding.

    Idempotent: re-arming rewrites the same content. Requires the run's captured
    ``execution_binding.json`` — arming before the binding exists is refused,
    because a pause that cannot name the grant it protects cannot be proven to
    belong to this run.

    Written atomically (tmp + os.replace) so an interrupted write can never leave
    a half-marker that reads as malformed on the admission path.
    """
    from substrate.execution.attempts.field_scenario_map import read_execution_binding

    binding = read_execution_binding(targets_dir)
    if binding is None:
        raise ValueError(
            "cannot arm pre-dispatch pause: execution_binding.json absent or "
            "malformed — the pause would not be bound to a real run/grant"
        )
    payload = {
        "kind": "pause_before_dispatch",
        "run_id": binding.run_id,
        "candidate_sha": binding.candidate_sha,
        "grant_id": binding.grant_id,
        "decision_ref": binding.decision_ref,
        "plan_record_id": binding.plan_record_id,
        "plan_version": binding.plan_version,
    }
    path = pause_marker_path(targets_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    os.replace(tmp, path)
    return path


def pause_state(targets_dir: str | os.PathLike[str]) -> tuple[bool, str]:
    """Is admission suppressed for this run? Returns (paused, diagnosable reason).

    FAIL CLOSED, with ONE way to report "not paused": the marker file is
    provably absent. Every other outcome — unreadable, malformed, truncated,
    wrong schema, missing field, binding absent, binding mismatch — reports
    PAUSED with a reason. A gate that admits work because it could not read its
    own state is precisely the fail-open shape earlier rounds of this campaign
    kept reintroducing.

    Note the asymmetry that makes this safe: a marker that does not match this
    run still PAUSES rather than being ignored. Ignoring an unmatched marker
    would let a corrupt/foreign marker silently release workers, which is the
    dangerous direction. Refusing to release is always the safe direction; the
    operator resolves it by releasing explicitly, which validates the binding.
    """
    # Path CONSTRUCTION itself raises TypeError for a non-path targets_dir, so
    # it must be inside the guard — not just the exists() call. A gate that
    # blows up before it can decide has decided nothing, and "nothing" must
    # never mean "admit".
    try:
        path = pause_marker_path(targets_dir)
        if not path.exists():
            return False, "not paused (no marker)"
    except (OSError, ValueError, TypeError) as exc:
        return True, f"pause state unreadable ({exc}) — failing closed"

    try:
        raw = path.read_text(encoding="utf-8")
    except (OSError, ValueError) as exc:
        return True, f"pause marker unreadable ({exc}) — failing closed"

    try:
        data = json.loads(raw)
    except ValueError:
        return True, "pause marker is not parseable JSON — failing closed"
    if not isinstance(data, dict):
        return True, "pause marker is not a JSON object — failing closed"
    if data.get("kind") != "pause_before_dispatch":
        return True, f"pause marker has unexpected kind {data.get('kind')!r} — failing closed"
    missing = [f for f in _PAUSE_BINDING_FIELDS if not str(data.get(f, "") or "")]
    if missing:
        return True, f"pause marker incomplete (missing {', '.join(missing)}) — failing closed"

    from substrate.execution.attempts.field_scenario_map import read_execution_binding

    binding = read_execution_binding(targets_dir)
    if binding is None:
        return True, "execution binding absent — cannot confirm pause ownership, failing closed"
    for field in _PAUSE_BINDING_FIELDS:
        expected = str(getattr(binding, field, "") or "")
        actual = str(data.get(field, "") or "")
        if expected != actual:
            return True, (
                f"pause marker {field}={actual!r} does not match this run's "
                f"binding {expected!r} — foreign marker, failing closed"
            )
    return True, f"paused before dispatch (run {binding.run_id}, grant {binding.grant_id})"


def dispatch_is_paused(targets_dir: str | os.PathLike[str]) -> bool:
    """True when scheduler admission must be suppressed for this run."""
    paused, _reason = pause_state(targets_dir)
    return paused


def release_pause_before_dispatch(targets_dir: str | os.PathLike[str]) -> tuple[bool, str]:
    """Release the pause exactly once, only for THIS run. Returns (released, detail).

    Refused when: no marker exists (nothing to release); the marker is malformed
    (releasing an unreadable marker would discard the evidence of why it was
    unreadable); or the marker is bound to a different run/grant/SHA (releasing
    another run's marker is exactly the cross-run authority leak the binding
    exists to prevent).

    A SECOND release is refused because the marker is already gone — reporting
    success would let a duplicate `resume` look like it re-authorized a run that
    is already running.
    """
    try:
        path = pause_marker_path(targets_dir)
        if not path.exists():
            return False, "not paused (no marker) — nothing to release"
    except (OSError, ValueError, TypeError) as exc:
        return False, f"pause state unreadable ({exc}) — refusing to release"

    paused, reason = pause_state(targets_dir)
    if not paused:  # pragma: no cover - marker exists, so pause_state cannot say no
        return False, "not paused — nothing to release"
    if not reason.startswith("paused before dispatch"):
        # Malformed or foreign. Do not unlink: the marker is evidence, and
        # removing a foreign marker would be acting on another run's state.
        return False, f"refusing to release: {reason}"

    try:
        path.unlink()
    except OSError as exc:
        return False, f"pause marker could not be released: {exc}"
    return True, "pause released"


def target_task_id(targets_dir: str | os.PathLike[str]) -> str:
    """The exact canonical task id the armed variant targets ('' if none)."""
    if read_variant(targets_dir) not in _REVOKING_VARIANTS:
        return ""
    return read_scenario_map(targets_dir).get("backend_task_id", "")


def arming_is_valid(targets_dir: str | os.PathLike[str]) -> tuple[bool, str]:
    """Fast local pre-check: is a revoking variant armed with a usable map?

    This checks only what is readable from ``targets_dir`` alone (marker +
    persisted map). The AUTHORITATIVE check — that the map is fresh, bound to
    this run/plan, resolves to real materialized packets, and targets an
    authorized-frontier Task — is ``arming_is_valid_for_run`` below, which needs
    the live candidate records. A pipeline MUST call the run-aware form; this one
    exists so ``inject-failure`` can fail fast before the run even starts.
    """
    variant = read_variant(targets_dir)
    if not variant:
        return True, "no failure variant armed (clean run)"
    if variant not in _REVOKING_VARIANTS:
        return False, f"unknown failure variant {variant!r}"
    mapping = read_scenario_map(targets_dir)
    if not mapping:
        return False, (
            f"variant {variant!r} armed but no {_SCENARIO_NAME} exists — the "
            f"injection cannot target a real task and would silently run clean"
        )
    if not mapping.get("backend_task_id"):
        return False, (
            f"variant {variant!r} armed but {_SCENARIO_NAME} has no "
            f"backend_task_id — nothing to revoke"
        )
    return True, f"variant {variant!r} targets {mapping['backend_task_id']}"


def arming_is_valid_for_run(
    targets_dir: str | os.PathLike[str],
    *,
    records: list[Any],
    now: float | None = None,
) -> tuple[bool, str]:
    """AUTHORITATIVE arming check against the LIVE candidate state (C-3).

    A clean run (no revoking variant) is always valid. A revoking variant is
    valid ONLY when the persisted scenario map validates against the run's
    CAPTURED execution binding (``execution_binding.json``) and the ONE canonical
    execution-authorization grant matching every binding identifier — grant_id,
    decision_ref, plan id/version, tenant/principal/membership,
    conversation/correlation. The frontier is that exact grant's task_frontier,
    resolved by run binding, never "the only ACTIVE grant" and never aggregated
    from all packets. Fails closed on every mode (absent binding/absent map/stale/
    wrong-run/nonexistent/out-of-frontier/tampered ref/tampered grant_id/
    non-ACTIVE/not-yet-valid/expired/empty-frontier/draft-or-superseded plan).
    """
    variant = read_variant(targets_dir)
    if not variant:
        return True, "no failure variant armed (clean run)"
    if variant not in _REVOKING_VARIANTS:
        return False, f"unknown failure variant {variant!r}"

    from substrate.execution.attempts.field_scenario_map import validate_against_run

    ok, reason = validate_against_run(targets_dir, records=records, now=now)
    if not ok:
        return False, f"variant {variant!r} armed but map invalid: {reason}"
    target = target_task_id(targets_dir)
    if not target:
        return False, f"variant {variant!r} armed but no backend_task_id resolved"
    return True, f"variant {variant!r} targets {target} ({reason})"


def disallowed_tools_for(
    *,
    targets_dir: str | os.PathLike[str],
    task_id: str,
    attempt_number: int,
) -> list[str]:
    """Tool revocations for THIS dispatch, honoring the armed variant.

    Revokes file-mutation tools for the BACKEND task's FIRST attempt only —
    matched by EQUALITY against the recorded canonical id, never by pattern. The
    retry (attempt 2+) runs unrevoked so the graph can recover, which is what
    proves retry-as-new-attempt works.
    """
    target = target_task_id(targets_dir)
    if not target or not task_id:
        return []
    if task_id == target and int(attempt_number) == 1:
        return list(_TOOLS_REVOKED)
    return []


def injection_fired(dispatched_envelopes: list[Any]) -> bool:
    """Did the armed injection actually reach a dispatch?

    ``dispatched_envelopes`` are objects/dicts carrying ``disallowed_tools``. The
    qualification asserts this is True for a failure pass — an armed variant that
    produced no revoked dispatch means the pass proved nothing.
    """
    for env in dispatched_envelopes or []:
        tools = (
            env.get("disallowed_tools")
            if isinstance(env, dict)
            else getattr(env, "disallowed_tools", None)
        )
        if tools:
            return True
    return False


__all__ = [
    "arm_pause_before_dispatch",
    "arming_is_valid",
    "arming_is_valid_for_run",
    "disallowed_tools_for",
    "dispatch_is_paused",
    "pause_marker_path",
    "release_pause_before_dispatch",
    "injection_fired",
    "pause_state",
    "read_scenario_map",
    "read_variant",
    "scenario_map_path",
    "target_task_id",
    "write_scenario_map",
]
