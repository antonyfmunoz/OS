"""BEHAVIORAL coverage for the isolation-preflight verdict in the REAL caller.

Why this file exists
--------------------
Independent review R12 built three mutations of the isolation-preflight seam in
`start_runner` and reported that ALL of them survived the complete Wave 2 suite.
Reproducing them established two separate facts, which the original finding
conflated:

1. A REAL production defect (High). The caller decided isolation SOLELY from
   the preflight subprocess's stdout::

       isolation_ok = False
       if pre is not None and getattr(pre, "stdout", ""):
           try:
               isolation_ok = bool(json.loads(pre.stdout).get("isolation_ok", False))

   `pre.returncode` and `pre.stderr` were never read. The preflight's own exit
   contract is unambiguous — `wave2_attempt_runner.py` returns `0 if (prim and
   ok) else 2` — so a preflight that PRINTED an affirmative verdict and then
   FAILED (nonzero exit, or a diagnostic on stderr) was accepted as proof of
   confinement. That is a fail-open on the Amendment v1 clause 4 control: the
   one check standing between a real worker and an unconfined host.

2. A test-adequacy gap, NOT a production defect. The briefed claim was that
   empty/unparseable stdout fabricated `isolation_ok=true`. It does not: every
   such path was already fail-closed. What was true is that NO test distinguished
   that correct behavior from the `m_t2_stdout` mutation (which flips the
   `isolation_ok = False` initializer to `True`). On any non-empty-stdout path
   the initializer is overwritten, so the mutant is equivalent there; on the
   EMPTY-stdout path it is not, and nothing noticed. Correct code, unpinned.

What this file does
-------------------
Every test drives the REAL `start_runner` and asserts on its REAL return
contract. The seam patched is the exact command-execution dependency the
production function consumes — `Runner.run` — and the object it returns is a
real `subprocess.CompletedProcess`, so returncode/stdout/stderr have production
semantics rather than mock semantics.

`_ProbeRunner` also proves the seam is LOAD-BEARING: it fails loudly if
`start_runner` stops invoking the preflight command at all (see
`test_seam_is_load_bearing_not_an_unused_name`). A monkeypatch that silently
patches a name the production path no longer calls is exactly the failure mode
R12's MEDIUM caught in the previous cycle, so it is pinned here rather than
assumed.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO not in sys.path:
    sys.path.insert(0, REPO)
if os.path.join(REPO, "tests") not in sys.path:
    sys.path.insert(0, os.path.join(REPO, "tests"))

from wave2_script_import import load_wave2_script  # noqa: E402


def _dispatch_mod():
    """The REAL launcher module — loaded by explicit path, never by `scripts.*`."""
    return load_wave2_script("wave2_field_dispatch")


AFFIRMATIVE = json.dumps(
    {"primitive": "bwrap", "isolation_ok": True, "detail": "bwrap confinement verified"}
)
NEGATIVE = json.dumps(
    {"primitive": "bwrap", "isolation_ok": False, "detail": "isolation FAILED — probe saw /opt/OS"}
)


class _ProbeRunner:
    """A Runner whose ONLY preflight answer is the one the case under test needs.

    Every other command (the `mkdir -p` of the spool root) is a no-op success, so
    the single variable across these tests is the preflight result.
    `preflight_calls` records that the production path really did invoke the
    preflight command — see `test_seam_is_load_bearing_not_an_unused_name`.

    NOTE on what counts as "launching a worker": `start_runner` calls
    `runner.run(["mkdir", "-p", spool_root])` BEFORE the preflight, so counting
    every `run()` as a launch would mis-attribute that mkdir. The real worker
    launch is `subprocess.Popen` further down, NOT a `Runner.run` call at all —
    so worker-launch is asserted via `popen_calls`, which patches the exact
    module-level `subprocess.Popen` the launcher uses.
    """

    def __init__(self, result, *, dry_run: bool = False):
        self._result = result
        self.dry_run = dry_run
        self.log: list[str] = []
        self.preflight_calls = 0

    def _is_preflight(self, cmd) -> bool:
        return any("--preflight-only" == str(part) for part in cmd)

    def run(self, cmd, *, timeout: int = 120, check: bool = False, capture: bool = True):
        if self._is_preflight(cmd):
            self.preflight_calls += 1
            if isinstance(self._result, BaseException):
                raise self._result
            return self._result
        return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="", stderr="")

    def shell(self, cmd_str, *, timeout: int = 120):
        return subprocess.CompletedProcess(args=cmd_str, returncode=0, stdout="", stderr="")


def _completed(returncode: int, stdout: str, stderr: str = ""):
    return subprocess.CompletedProcess(
        args=["python3", "wave2_attempt_runner.py", "--preflight-only"],
        returncode=returncode,
        stdout=stdout,
        stderr=stderr,
    )


class _Verdict:
    """The launcher's return value plus what it actually DID to get there."""

    def __init__(self, out, preflight_calls, popen_calls):
        self.out = out
        self.preflight_calls = preflight_calls
        self.popen_calls = popen_calls

    def __getitem__(self, k):
        return self.out[k]

    def get(self, k, default=None):
        return self.out.get(k, default)

    def __repr__(self):
        return f"<verdict out={self.out!r} preflight={self.preflight_calls} popen={self.popen_calls}>"


def _start(result, tmp_path):
    """Drive the REAL `start_runner` with one preflight outcome.

    Paths are redirected into `tmp_path` so the affirmative case can run the real
    post-gate launch path without touching /var/lib/umh (absent off-candidate).
    `subprocess.Popen` is replaced at the launcher module's own attribute — the
    exact name the production line binds — so "did a worker actually start?" is
    observed rather than inferred.
    """
    mod = _dispatch_mod()

    state = tmp_path / "state"
    spool = state / "spool"
    spool.mkdir(parents=True, exist_ok=True)
    (tmp_path / "targets").mkdir(parents=True, exist_ok=True)

    secret_file = state / "run_secret"
    secret_file.write_text("test-secret-value", encoding="utf-8")

    popen_calls: list = []

    class _FakePopen:
        def __init__(self, *a, **k):
            popen_calls.append(a[0] if a else None)
            self.pid = 424242

        def poll(self):
            return 0

    monkey = pytest.MonkeyPatch()
    try:
        monkey.setattr(mod, "_spool_root", lambda sha, run_id: spool)
        monkey.setattr(mod, "_state_dir", lambda sha: state)
        monkey.setattr(mod, "_targets_dir", lambda sha, run_id: tmp_path / "targets")
        monkey.setattr(mod, "_mint_run_secret", lambda runner, sha: secret_file)
        monkey.setattr(mod, "subprocess", _PopenShim(mod.subprocess, _FakePopen))
        runner = _ProbeRunner(result)
        out = mod.start_runner(runner, "c50f157" + "0" * 33, "run-iso-probe", 1)
    finally:
        monkey.undo()
    return _Verdict(out, runner.preflight_calls, len(popen_calls))


class _PopenShim:
    """`subprocess` with only Popen replaced — every other attribute is the real one."""

    def __init__(self, real, popen):
        self._real = real
        self.Popen = popen

    def __getattr__(self, name):
        return getattr(self._real, name)


# ─────────────────────────────────────────────────────────────────────────────
# The one affirmative case. Everything else in this file must fail closed.
# ─────────────────────────────────────────────────────────────────────────────


def test_rc0_affirmative_stdout_empty_stderr_is_the_only_way_to_prove_isolation(tmp_path):
    """Case 1: rc=0 + valid affirmative stdout + empty stderr => isolation proven.

    Pinned against the REAL preflight's observed output on a bwrap host:
    returncode 0, affirmative JSON on stdout, and exactly zero bytes of stderr.
    """
    out = _start(_completed(0, AFFIRMATIVE, ""), tmp_path)
    assert out.preflight_calls == 1, "production path never ran the preflight command"
    assert out.get("isolation_ok") is True, out
    assert out.get("started") is not False or "isolation" not in str(out.get("reason", "")), out


# ─────────────────────────────────────────────────────────────────────────────
# THE REAL HIGH: an affirmative stdout that is contradicted by process failure.
# These two are the cases the pre-correction caller accepted.
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.parametrize("rc", [1, 2, 127, -9])
def test_nonzero_returncode_with_affirmative_stdout_fails_closed(rc, tmp_path):
    """Case 3 (the REAL High): a crashed preflight cannot prove confinement.

    `wave2_attempt_runner.py --preflight-only` returns `0 if (prim and ok) else 2`,
    so a nonzero code is the preflight itself saying "do not trust this." The
    pre-correction caller never read it and launched workers anyway.
    """
    out = _start(_completed(rc, AFFIRMATIVE, ""), tmp_path)
    assert out.preflight_calls == 1
    assert out["started"] is False, f"rc={rc} with affirmative stdout was accepted: {out}"
    assert out["isolation_ok"] is False, out
    assert out.popen_calls == 0, "a worker runner was launched without proven isolation"


def test_affirmative_stdout_with_nonempty_stderr_fails_closed(tmp_path):
    """Case 4 (the REAL High): a real successful preflight emits ZERO bytes of stderr.

    Verified on a bwrap host: rc=0, affirmative stdout, stderr exactly 0 bytes.
    Because the success path is stderr-silent, ANY stderr means something went
    wrong that the exit code may not have captured, so the contract is strict —
    there is no permitted warning channel to carve out.
    """
    out = _start(_completed(0, AFFIRMATIVE, "bwrap: setting up uid map: Permission denied"), tmp_path)
    assert out.preflight_calls == 1
    assert out["started"] is False, f"stderr-contradicted affirmative was accepted: {out}"
    assert out["isolation_ok"] is False, out
    assert out.popen_calls == 0


def test_affirmative_output_followed_by_process_failure_fails_closed(tmp_path):
    """Case 13: printed OK, then died — both failure signals present at once."""
    out = _start(_completed(2, AFFIRMATIVE, "Traceback (most recent call last): RuntimeError"), tmp_path)
    assert out["started"] is False and out["isolation_ok"] is False, out


# ─────────────────────────────────────────────────────────────────────────────
# THE COVERAGE GAP: paths that were already correct but pinned by nothing.
# These are what kill m_t2_stdout.
# ─────────────────────────────────────────────────────────────────────────────


def test_empty_stdout_fails_closed(tmp_path):
    """Case 8 — and the case that kills `m_t2_stdout`.

    `m_t2_stdout` flips the `isolation_ok = False` initializer to `True`. With
    non-empty stdout the initializer is overwritten, so the mutant is
    indistinguishable. With EMPTY stdout the guard short-circuits and the
    initializer IS the verdict — mutant returns started, real code refuses.
    """
    out = _start(_completed(2, "", "bwrap: command not found"), tmp_path)
    assert out.preflight_calls == 1
    assert out["started"] is False, f"empty-stdout preflight was accepted: {out}"
    assert out["isolation_ok"] is False, out
    assert out.popen_calls == 0


def test_whitespace_only_stdout_fails_closed(tmp_path):
    """Case 9: a preflight that emitted only whitespace proved nothing."""
    out = _start(_completed(0, "   \n\t  \n"), tmp_path)
    assert out["started"] is False and out["isolation_ok"] is False, out


# ─────────────────────────────────────────────────────────────────────────────
# The refusal must also tell the operator WHICH condition failed.
#
# The verdict alone is not the whole external contract: an operator who sees
# "isolation failed" has to know whether the preflight crashed, said nothing, or
# affirmatively reported a leak — those demand different responses. Two mutants
# (`m6_no_empty_guard`, `m8_none_ok`) leave the verdict correct but MISDIAGNOSE
# the cause: an empty preflight is reported as "not parseable JSON", and a
# missing result is reported as "exited None". Pinning the diagnostic is what
# makes those mutants killable rather than equivalent-by-omission.
# ─────────────────────────────────────────────────────────────────────────────


def test_refusal_names_the_condition_that_actually_failed(tmp_path):
    """Each fail-closed path must diagnose ITS OWN cause, not a neighbouring one."""
    cases = [
        (_completed(0, ""), "no evidence on stdout", "empty stdout"),
        (_completed(0, "   \n\t "), "no evidence on stdout", "whitespace-only stdout"),
        (None, "produced no result", "no result at all (CPU gate / launch failure)"),
        (_completed(2, "", "bwrap: not found"), "exited 2", "nonzero exit"),
        (_completed(0, "not json"), "not parseable JSON", "malformed stdout"),
        (_completed(0, "[1,2,3]"), "not a JSON object", "wrong JSON shape"),
        (_completed(0, NEGATIVE), "did not affirm isolation", "explicit negative"),
        (_completed(0, AFFIRMATIVE, "boom"), "wrote to stderr", "stderr contradiction"),
    ]
    for pre, expected_fragment, label in cases:
        out = _start(pre, tmp_path / f"c{abs(hash(label))}")
        assert out["isolation_ok"] is False, (label, out)
        reason = str(out.get("reason", ""))
        assert expected_fragment in reason, (
            f"{label}: refusal misdiagnosed the failure — expected a reason naming "
            f"{expected_fragment!r}, got {reason!r}"
        )


def test_command_not_found_fails_closed(tmp_path):
    """Case 5: no bwrap binary → no confinement → no execution."""
    out = _start(_completed(127, "", "/bin/sh: 1: bwrap: not found"), tmp_path)
    assert out["started"] is False and out["isolation_ok"] is False, out


def test_execution_exception_and_timeout_collapse_to_the_reachable_states(tmp_path):
    """Cases 6 and 7, adjudicated by REACHABILITY rather than assumed.

    The contract asks that an execution exception and a timeout each fail closed.
    At THIS seam neither reaches the isolation decision, and the honest response
    is to prove that rather than to wrap the call in a `try/except` no real
    dependency can trigger — dead defensive code is not a control, and a test
    that forced it would assert against a fixture instead of production.

    `start_runner` gets its preflight result from `Runner.run`, which delegates
    to `subprocess.run(..., capture_output=True, check=check)`. If that call
    raises `TimeoutExpired`, the exception propagates out of `start_runner`
    entirely — the launcher never returns a verdict at all, so there is no
    "isolation_ok=true" to fabricate; the run aborts, which is fail-closed by
    construction. The CPU gate's own failure mode is `None`, which IS reachable
    and IS pinned by `test_runner_returning_none_fails_closed`.

    So the two briefed states collapse into the two reachable ones: `None`, and a
    nonzero-rc `CompletedProcess`. This test pins the reachability CLAIM, so if
    `Runner.run` is ever changed to swallow exceptions and return a value, this
    fails and the exception cases become real work again.
    """
    import inspect

    mod = _dispatch_mod()
    src = inspect.getsource(mod.Runner.run)
    assert "subprocess.run(" in src, "Runner.run no longer delegates to subprocess.run"
    assert "capture_output=capture" in src, f"capture contract changed: {src}"
    assert "except" not in src, (
        "Runner.run now swallows exceptions — an exception can therefore reach the "
        "isolation decision as a VALUE, so cases 6/7 need real fail-closed tests"
    )

    # Both reachable failure states, driven through the real launcher.
    out_none = _start(None, tmp_path)
    assert out_none["started"] is False and out_none["isolation_ok"] is False, out_none
    out_rc = _start(_completed(2, "", "timed out after 60s"), tmp_path)
    assert out_rc["started"] is False and out_rc["isolation_ok"] is False, out_rc

    # And a raised timeout aborts rather than yielding a verdict.
    with pytest.raises(subprocess.TimeoutExpired):
        _start(subprocess.TimeoutExpired(cmd=["preflight"], timeout=60), tmp_path)


def test_runner_returning_none_fails_closed(tmp_path):
    """The CPU gate returns None rather than a CompletedProcess — not a verdict."""
    out = _start(None, tmp_path)
    assert out["started"] is False and out["isolation_ok"] is False, out


def test_malformed_stdout_fails_closed(tmp_path):
    """Case 10: unparseable output is not evidence."""
    out = _start(_completed(0, "bwrap confinement verified (not json)"), tmp_path)
    assert out["started"] is False and out["isolation_ok"] is False, out


def test_truncated_json_fails_closed(tmp_path):
    """Case 10b: a partial write that cuts the JSON mid-object."""
    out = _start(_completed(0, '{"primitive": "bwrap", "isolation_ok": tr'), tmp_path)
    assert out["started"] is False and out["isolation_ok"] is False, out


def test_ambiguous_stdout_without_the_key_fails_closed(tmp_path):
    """Case 11: valid JSON that never affirms isolation."""
    out = _start(_completed(0, json.dumps({"primitive": "bwrap", "detail": "ran"})), tmp_path)
    assert out["started"] is False and out["isolation_ok"] is False, out


def test_non_object_json_fails_closed(tmp_path):
    """Case 11b: valid JSON of the wrong shape must not crash OR pass."""
    for body in ("[1, 2, 3]", '"isolation_ok"', "true", "null", "42"):
        out = _start(_completed(0, body), tmp_path)
        assert out["started"] is False, f"{body!r} was accepted: {out}"
        assert out["isolation_ok"] is False, body


def test_stderr_only_failure_fails_closed(tmp_path):
    """Case 12: nothing on stdout, diagnostics on stderr."""
    out = _start(_completed(1, "", "bwrap: No permitted namespaces"), tmp_path)
    assert out["started"] is False and out["isolation_ok"] is False, out


def test_explicit_negative_evidence_fails_closed(tmp_path):
    """Case 2: the preflight ran cleanly and said the probe SAW /opt/OS."""
    out = _start(_completed(2, NEGATIVE, ""), tmp_path)
    assert out.preflight_calls == 1
    assert out["started"] is False and out["isolation_ok"] is False, out
    assert out.popen_calls == 0


def test_truthy_non_boolean_isolation_value_fails_closed(tmp_path):
    """A string/number in the field is not affirmative proof of confinement."""
    for val in ("true", "yes", 1, [1]):
        body = json.dumps({"primitive": "bwrap", "isolation_ok": val})
        out = _start(_completed(0, body), tmp_path)
        assert out["started"] is False, f"{val!r} was accepted as affirmative: {out}"
        assert out["isolation_ok"] is False, val


# ─────────────────────────────────────────────────────────────────────────────
# Case 14 + seam integrity.
# ─────────────────────────────────────────────────────────────────────────────


def test_caller_refuses_worker_execution_unless_isolation_is_proven(tmp_path):
    """Case 14: no launch of ANY kind happens on an unproven preflight."""
    for result in (
        _completed(1, AFFIRMATIVE, ""),
        _completed(0, AFFIRMATIVE, "warn"),
        _completed(0, ""),
        _completed(0, "garbage"),
        None,
    ):
        out = _start(result, tmp_path)
        assert out["started"] is False, out
        assert out.popen_calls == 0, f"worker launched despite {out}"


@pytest.mark.parametrize("blank_stderr", ["   ", "\n", "\r\n", "\t\n "])
def test_whitespace_only_stderr_is_not_a_contradiction(tmp_path, blank_stderr):
    """A trailing newline on stderr must not be read as "the preflight complained".

    The contract is "stderr empty" — and `stderr` is NORMALIZED with `.strip()`
    before it is tested, so whitespace counts as empty. Independent review R14
    mutated that normalization away (`(... or "").strip()` -> `(... or "")`) and
    it SURVIVED: nothing pinned the whitespace case.

    The direction of that mutant is fail-CLOSED — it REFUSES where real code
    proceeds — so it is not a security regression. It is still a real behavioral
    difference, and the behavior it breaks is one that matters operationally: a
    healthy bwrap host that emits a stray newline on stderr would be refused, and
    the field run would abort claiming isolation could not be proven. That is a
    false negative on the Amendment v1 clause 4 gate, which costs a whole run.

    Pinning it keeps the strict no-stderr rule strict about CONTENT without making
    it brittle about WHITESPACE.
    """
    out = _start(_completed(0, AFFIRMATIVE, blank_stderr), tmp_path)
    assert out.preflight_calls == 1
    assert out.get("isolation_ok") is True, (
        f"whitespace-only stderr {blank_stderr!r} was treated as a contradiction — "
        f"a healthy host would be refused: {out}"
    )


@pytest.mark.parametrize("bad_stdout", [None, 0, False, 12345])
def test_a_result_with_a_non_string_stdout_fails_closed(tmp_path, bad_stdout):
    """A result whose `stdout` is not a string must refuse CLEANLY, not crash.

    Independent review R15 re-derived its own mutant set and found that dropping the
    `or ""` coercion in `stdout = getattr(pre, "stdout", "") or ""` SURVIVES the whole
    suite while being non-equivalent: with `pre.stdout` of None/0/False the real code
    refuses cleanly ("preflight emitted no evidence on stdout"), while the mutant dies
    with `AttributeError: 'NoneType' object has no attribute 'strip'`.

    The direction is fail-closed either way — an unhandled exception aborts the launcher
    with zero workers started, so it cannot fabricate isolation — and it is unreachable
    under today's producer, since `Runner.run` calls `subprocess.run(..., text=True)`
    and `.stdout` is therefore always `str`.

    It is pinned regardless, because it is the SAME hazard already pinned for the exit
    status in `test_a_result_without_a_usable_returncode_fails_closed`, on the same
    reasoning: unreachability is a property of the CURRENT producer, not a guarantee.
    Leaving the sibling coercion unpinned would be an inconsistency, and a duck-typed
    result reaching this seam should produce a diagnosable refusal rather than a
    traceback an operator has to decode.
    """

    class _OddStdout:
        returncode = 0
        stderr = ""

    result = _OddStdout()
    result.stdout = bad_stdout

    out = _start(result, tmp_path)
    assert out["started"] is False, f"stdout={bad_stdout!r} was accepted: {out}"
    assert out["isolation_ok"] is False, out
    assert out.popen_calls == 0, "worker launched on a preflight with unusable stdout"


@pytest.mark.parametrize("silent_stderr", [None, "", b"", b"   ", bytearray(b" ")])
def test_an_empty_non_string_stderr_is_still_silence(tmp_path, silent_stderr):
    """An EMPTY non-str stderr means the preflight said nothing — isolation may pass.

    `None`/`""`/`b""` all mean "no diagnostic". They must not be treated as a
    contradiction, or a healthy host with a slightly unusual result object would be
    refused.
    """

    class _Silent:
        returncode = 0
        stdout = AFFIRMATIVE

    result = _Silent()
    result.stderr = silent_stderr

    out = _start(result, tmp_path)
    assert out.get("isolation_ok") is True, (
        f"empty stderr {silent_stderr!r} was misread as a contradiction: {out}"
    )


@pytest.mark.parametrize(
    "noisy_stderr", [b"bwrap: permission denied", bytearray(b"denied"), 12345, ["err"]]
)
def test_a_non_string_stderr_carrying_content_fails_closed(tmp_path, noisy_stderr):
    """A non-str stderr that CARRIES CONTENT is a contradiction, never silence.

    This pins finding R16 F-1, a fail-OPEN this file's own author introduced. The first
    attempt at type-coercing stderr blanked every non-str value, which DISCARDED a real
    diagnostic: with `stderr=b"boom"` the launcher reported `isolation_ok=True` and
    LAUNCHED A WORKER (popen=1), where the prior code had correctly refused. Blanking is
    worse than crashing — the crash was at least fail-closed.

    The earlier version of this test asserted only `popen_calls <= 1` and
    `isolation_ok is not None`, which is vacuous: independent review confirmed it passes
    against the UNCORRECTED parent. These assertions are the real contract.
    """

    class _Noisy:
        returncode = 0
        stdout = AFFIRMATIVE

    result = _Noisy()
    result.stderr = noisy_stderr

    out = _start(result, tmp_path)
    assert out["isolation_ok"] is False, (
        f"a non-string stderr carrying {noisy_stderr!r} was discarded rather than "
        f"treated as a contradiction — isolation was affirmed on a noisy preflight: {out}"
    )
    assert out["started"] is False, out
    assert out.popen_calls == 0, "worker launched despite a real stderr diagnostic"


def test_a_non_stream_stderr_is_a_contradiction_even_when_its_repr_is_empty(tmp_path):
    """A non-stream stderr must be a contradiction by CONSTRUCTION, not by its repr().

    Self-found while briefing the next reviewer on the failure mode this sequence keeps
    producing: each fix introduced the next fail-open. Deriving the verdict from
    `repr(_raw_stderr)` had exactly that shape — an object whose `__repr__` returns `""`
    yields an empty `stderr`, the contradiction check sees silence, and the launcher
    reports `isolation_ok=True` and LAUNCHES A WORKER.

    Reproduced through the real caller before the fix: `isolation_ok=True, popen=1`.

    The distinction that matters: whitespace-only *streams* (`"  "`, `b"  "`) genuinely
    mean the preflight said nothing, so they remain silence. A non-stream OBJECT is not
    a stream at all — its emptiness is a property of its rendering, not evidence that the
    preflight was quiet. The type-name prefix makes it non-empty regardless.
    """

    class _EmptyRepr:
        def __repr__(self) -> str:
            return ""

    class _WhitespaceRepr:
        def __repr__(self) -> str:
            return "   "

    for obj in (_EmptyRepr(), _WhitespaceRepr()):

        class _Result:
            returncode = 0
            stdout = AFFIRMATIVE

        result = _Result()
        result.stderr = obj

        out = _start(result, tmp_path / f"r{id(obj)}")
        assert out["isolation_ok"] is False, (
            f"a {type(obj).__name__} stderr was read as silence because its repr() is "
            f"empty — isolation was affirmed on a non-stream stderr: {out}"
        )
        assert out.popen_calls == 0, "worker launched on a non-stream stderr"


def test_a_result_with_no_stdout_attribute_at_all_fails_closed(tmp_path):
    """A result object lacking `stdout` entirely must default to NO evidence.

    Pins finding R16 F-2: the `getattr(pre, "stdout", "")` DEFAULT was unpinned, so a
    mutant defaulting it to affirmative JSON survived the suite. The default is the
    value used when the attribute is absent — defaulting it to anything that could
    read as proof would fabricate isolation from a result that never carried any.
    """

    class _NoStdoutAttr:
        returncode = 0
        stderr = ""

    out = _start(_NoStdoutAttr(), tmp_path)
    assert out["isolation_ok"] is False, f"absent stdout defaulted to proof: {out}"
    assert out["started"] is False, out
    assert out.popen_calls == 0, "worker launched on a result with no stdout at all"


def test_a_result_without_a_usable_returncode_fails_closed(tmp_path):
    """A preflight result whose returncode is absent/None is NOT proof of isolation.

    Independent review R14 mutated `if rc != 0:` to `if rc not in (0, None):` and it
    SURVIVED — nothing pinned what happens when the result object carries no usable
    exit status. Today that is unreachable (the seam's only producer is `Runner.run`,
    typed `CompletedProcess | None`, and the `None` case is caught by the
    `pre is not None` guard), but "unreachable" is a property of the CURRENT
    producer, not a guarantee. If a future seam returns a duck-typed result — a
    wrapper, a cached record, a mesh-relayed verdict — `rc` becomes None and the
    mutated form would treat a preflight with NO exit status as success.

    Pinning it costs one test and removes the survivor rather than arguing it away.
    """

    class _NoReturnCode:
        """A result object that carries evidence but no exit status."""

        stdout = AFFIRMATIVE
        stderr = ""

    out = _start(_NoReturnCode(), tmp_path)
    assert out["started"] is False, f"a result with no returncode was accepted: {out}"
    assert out["isolation_ok"] is False, out
    assert out.popen_calls == 0, "worker launched on a preflight with no exit status"


# NOTE — r14_g_dry_run_bypass is a PROVEN EQUIVALENT MUTANT, deliberately untested.
#
# Independent review R14 mutated the refusal gate to
# `not getattr(runner, "dry_run", True)` and it survived every attempt to kill it,
# including a test written specifically for it. Instrumenting the mutant showed why,
# and the reason is STRUCTURAL rather than a gap in coverage: a runner lacking
# `dry_run` never reaches a differing outcome, because `start_runner` reads
# `runner.dry_run` AGAIN a few lines later (the dry-run branch) and that second
# access is not mutated. So the attribute-less runner raises AttributeError in BOTH
# versions, with zero workers launched.
#
# Proven by execution over all 9 reachable runner shapes (dry_run absent/False/True
# x preflight rc 0/1/2): identical isolation verdict, identical started value,
# identical worker-launch count, identical exception type. Zero distinguishable
# cases. A test asserting a difference here would assert something the code cannot
# do — so none is written, and the equivalence is recorded instead of papered over.


def test_seam_is_load_bearing_not_an_unused_name(tmp_path):
    """The patched dependency must be the one production actually calls.

    If `start_runner` stopped invoking `--preflight-only`, every fail-closed test
    above could pass vacuously. This pins that the production path really reaches
    the seam, so the suite fails loudly rather than silently patching a dead name.
    """
    out = _start(_completed(0, AFFIRMATIVE, ""), tmp_path)
    assert out.preflight_calls == 1, (
        "start_runner did not invoke the --preflight-only command — the isolation "
        "seam moved or was bypassed, and these tests would be vacuous"
    )
    assert out.get("isolation_ok") is True, out


def test_real_preflight_success_emits_rc0_and_silent_stderr():
    """Pins the CONTRACT the strict-stderr rule depends on, against the real script.

    If a future change makes the successful preflight chatty on stderr, the
    strict rule would start rejecting healthy hosts. This test fails at that
    moment rather than in the field. Skipped where bwrap is absent, because then
    the preflight legitimately fails closed and proves nothing about the success
    path.
    """
    import shutil

    if shutil.which("bwrap") is None:
        pytest.skip("bwrap absent — the success-path contract cannot be observed here")

    script = os.path.join(REPO, "scripts", "wave2_attempt_runner.py")
    proc = subprocess.run(
        [sys.executable, script, "--spool-root", "/tmp/w2-iso-contract", "--preflight-only"],
        capture_output=True,
        text=True,
        timeout=120,
        cwd=REPO,
    )
    if proc.returncode != 0:
        pytest.skip(f"preflight could not confirm isolation here (rc={proc.returncode})")
    assert json.loads(proc.stdout)["isolation_ok"] is True, proc.stdout
    assert proc.stderr == "", (
        "the successful preflight emitted stderr — the strict no-stderr contract "
        f"in start_runner would now reject a healthy host: {proc.stderr!r}"
    )
