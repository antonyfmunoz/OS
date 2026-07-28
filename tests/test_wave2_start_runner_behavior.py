"""BEHAVIORAL regression coverage for the real `start_runner` readiness path.

Why this file exists
--------------------
Independent review R10 found that every existing reference to `start_runner` in
the suite was a docstring or an `ast.FunctionDef` name comparison — NO test ever
executed it. R10 then built an AST-SHAPE-PRESERVING mutant that keeps both the
call and the assignment (so both AST assertions still pass) but corrupts the
ARGUMENT:

    -  announced = runner_readiness_announced(head, proc.pid)
    +  announced = runner_readiness_announced(
    +      "control-plane driver up: pid=%d " % proc.pid, proc.pid)

That mutant survived the complete Wave 2 suite (888 passed) while fully
restoring the original B1 defect: a runner that emits only "runner starting:"
was reported `started=True`. Green suite, dead runner reported as started.

The lesson is one level past NEW-4: an AST pin proves a call is MADE and its
value is BOUND, but not that the value was computed from REAL EVIDENCE. Only
executing the caller against a real process can see that.

What this file does
-------------------
Every test drives the REAL `start_runner` from `scripts/wave2_field_dispatch.py`
against a REAL detached subprocess. Nothing here re-implements, mirrors, or
mocks the readiness decision:

  * the launched runner script is substituted (that is the point — we control
    exactly which markers the process emits, and whether it stays alive);
  * `Runner.run` is subclassed so the bwrap isolation preflight resolves without
    requiring bwrap on the test host (a STRUCTURAL seam — `start_runner` already
    parses this subprocess's JSON stdout);
  * `start_runner` itself, its readiness loop, its 30s deadline, its liveness
    check and its return contract are the REAL production code under test.

The negative cases must exhaust the launcher's real 30-second readiness
deadline. Rather than change production to make that literal injectable (this
correction cycle is test-only), `_accelerate_deadline` speeds up the launcher
module's view of the clock ~12x. The real loop, deadline arithmetic, liveness
poll and comparison all still execute — only wall-clock cost shrinks.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO not in sys.path:
    sys.path.insert(0, REPO)
if os.path.join(REPO, "tests") not in sys.path:
    sys.path.insert(0, os.path.join(REPO, "tests"))

from wave2_script_import import load_wave2_script  # noqa: E402


def _dispatch_mod():
    """The REAL launcher module — loaded by explicit path, never by `scripts.*`.

    `/opt/OS` is stale at Wave 0 and shadows this candidate's `scripts` package,
    so an `import scripts.wave2_field_dispatch` here can silently load the WRONG
    file. `load_wave2_script` resolves the path relative to THIS worktree.
    """
    return load_wave2_script("wave2_field_dispatch")


# --------------------------------------------------------------------------
# Test doubles: only the LAUNCHED PROCESS and the isolation preflight, never
# the readiness decision itself.
# --------------------------------------------------------------------------

# A stand-in runner script. It writes the marker lines it is told to write, then
# either exits immediately or sleeps. `%(pid)s` is expanded by the emitting
# process to its OWN pid so we can forge same-pid / other-pid cases exactly.
_FAKE_RUNNER = """\
import os, sys, time
lines = {lines!r}
for ln in lines:
    sys.stdout.write(ln.replace("@PID@", str(os.getpid())) + "\\n")
sys.stdout.flush()
if {stay_alive!r}:
    time.sleep({alive_seconds!r})
sys.exit({exit_code!r})
"""


class _PreflightOKRunner:
    """Real `Runner` contract, with the bwrap preflight resolved structurally.

    `start_runner` calls `runner.run([...,"--preflight-only"])` and parses the
    JSON on stdout. This returns exactly that shape, so the launcher's real
    parsing/branching executes. `mkdir -p` is genuinely performed. Every other
    command runs for real.
    """

    def __init__(self, isolation_ok: bool = True) -> None:
        self.dry_run = False
        self.log: list[str] = []
        self._isolation_ok = isolation_ok

    def run(self, cmd, *, timeout: int = 120, check: bool = False, capture: bool = True):
        self.log.append(" ".join(str(c) for c in cmd))
        if any(str(c) == "--preflight-only" for c in cmd):
            return subprocess.CompletedProcess(
                cmd,
                0,
                stdout=json.dumps(
                    {
                        "primitive": "bwrap",
                        "isolation_ok": self._isolation_ok,
                        "detail": "test seam",
                    }
                ),
                stderr="",
            )
        return subprocess.run(cmd, timeout=timeout, check=check, capture_output=capture, text=True)

    def shell(self, cmd_str: str, *, timeout: int = 120):
        self.log.append(cmd_str)
        return subprocess.run(cmd_str, shell=True, timeout=timeout, capture_output=True, text=True)


def _install_fake_runner_script(
    mod,
    tmp_path: Path,
    monkeypatch,
    *,
    lines: list[str],
    stay_alive: bool = True,
    alive_seconds: float = 30.0,
    exit_code: int = 0,
) -> Path:
    """Point the launcher's `_WORKTREE` at a scratch tree holding our stand-in.

    `start_runner` builds the launch line as
    `_WORKTREE / "scripts" / "wave2_attempt_runner.py"`, so redirecting
    `_WORKTREE` substitutes the LAUNCHED PROCESS while leaving every line of
    `start_runner` — including the readiness loop — untouched and real.
    """
    scripts = tmp_path / "fake_worktree" / "scripts"
    scripts.mkdir(parents=True, exist_ok=True)
    target = scripts / "wave2_attempt_runner.py"
    target.write_text(
        _FAKE_RUNNER.format(
            lines=lines,
            stay_alive=stay_alive,
            alive_seconds=alive_seconds,
            exit_code=exit_code,
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(mod, "_WORKTREE", tmp_path / "fake_worktree")
    return target


def _accelerate_deadline(mod, monkeypatch, factor: float = 12.0):
    """Make the launcher's REAL 30s readiness deadline elapse ~12x faster.

    The deadline is a hardcoded literal in production (`time.time() + 30.0`), and
    this correction cycle is test-only — so instead of changing production to make
    it injectable, we accelerate the launcher module's view of the clock. The real
    loop, the real `deadline` arithmetic, the real 1s sleep, the real liveness
    poll and the real comparison all still execute; only wall-clock cost shrinks.
    `time.sleep` is left REAL so the subprocess genuinely gets scheduled.
    """
    import time as _time

    t0 = _time.time()

    class _FastClock:
        @staticmethod
        def time():
            return t0 + (_time.time() - t0) * factor

        @staticmethod
        def sleep(seconds):
            _time.sleep(min(seconds, 0.25))

    monkeypatch.setattr(mod, "time", _FastClock)


@pytest.fixture()
def env(tmp_path, monkeypatch):
    """Redirect every host path the launcher writes into tmp_path."""
    mod = _dispatch_mod()
    _accelerate_deadline(mod, monkeypatch)
    state = tmp_path / "state"
    state.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(mod, "_state_dir", lambda sha: state)
    monkeypatch.setattr(mod, "_spool_root", lambda sha, run_id: state / "spool" / run_id)
    monkeypatch.setattr(mod, "_targets_dir", lambda sha, run_id: state / "targets" / run_id)

    secret = state / "run_secret"
    secret.write_text("s" * 64, encoding="utf-8")
    secret.chmod(0o600)
    monkeypatch.setattr(mod, "_mint_run_secret", lambda runner, sha: secret)
    monkeypatch.setattr(mod, "_declared_lanes_json", lambda: "[]")
    return mod


def _start(mod, runner=None, *, max_iterations: int = 1):
    return start_or_fail(mod, runner or _PreflightOKRunner(), max_iterations)


def start_or_fail(mod, runner, max_iterations: int):
    return mod.start_runner(runner, "deadbeef" * 5, "run-behav", max_iterations)


# --------------------------------------------------------------------------
# POSITIVE: authoritative markers permit readiness
# --------------------------------------------------------------------------


def test_control_plane_driver_marker_for_this_pid_permits_started(env, tmp_path, monkeypatch):
    """The exact control-plane readiness marker for the LAUNCHED pid → started."""
    mod = env
    _install_fake_runner_script(
        mod,
        tmp_path,
        monkeypatch,
        lines=["runner starting: pid=@PID@ run_root=/x", "control-plane driver up: pid=@PID@ ok"],
    )
    out = _start(mod)
    assert out["started"] is True, f"authoritative readiness was not accepted: {out}"
    assert out["isolation_ok"] is True
    assert out.get("runner_pid")


def test_worker_only_marker_permits_started(env, tmp_path, monkeypatch):
    """`runner ready worker-only:` is the OTHER authoritative marker — the mode
    where no control-plane driver is built. It must permit readiness, and it is
    allowed only because the runner emits it AFTER driver construction resolves
    (to "no driver in this mode"), unlike `runner up:`."""
    mod = env
    _install_fake_runner_script(
        mod,
        tmp_path,
        monkeypatch,
        lines=[
            "runner starting: pid=@PID@ run_root=/x",
            # exact production format (wave2_attempt_runner.py:367) — the trailing
            # content after the pid matters: `pid_tag` requires a TRAILING SPACE,
            # so `pid=<N>` at end-of-line is correctly NOT a readiness match.
            "runner ready worker-only: pid=@PID@ run_root=/x mode=worker",
        ],
    )
    out = _start(mod)
    assert out["started"] is True, f"worker-only readiness was not accepted: {out}"


def test_realistic_startup_volume_still_reaches_the_marker(env, tmp_path, monkeypatch):
    """The readiness read must cover the WHOLE log, not a fixed window of it.

    Third gap in this file, found by independent review R11: every other fixture
    here writes 1-3 short lines, so no test made the log LONG. A truncating read
    (`read_text(...)[:200]`, a tail-read, any fixed window) is therefore
    invisible — it passes all 14 of the other tests while reporting a HEALTHY
    runner as failed after burning the entire deadline.

    That is not hypothetical. Measured against the REAL runner
    (`scripts/wave2_attempt_runner.py`), a MINIMAL startup with ZERO
    crash-recovery lines already writes **309 bytes** before
    `control-plane driver up:` —

        [wave2-runner] isolation preflight: True (<detail>)          (line 278)
        [wave2-runner] crash-recovery swept stale run ...   UNBOUNDED (line 299)
        [wave2-runner] runner starting: pid=... run_root=... ...     (line 317)

    — and each crash-recovery line adds ~124 bytes more. So the marker sits
    beyond any small window on EVERY real launch, not just an unlucky one.

    This fixture reproduces that shape: realistic chatter first, marker last.
    """
    mod = env
    chatter = [
        "isolation preflight: True (bwrap confinement verified: /opt/OS hidden, creds scrubbed)",
        *[
            f"crash-recovery swept stale run /var/lib/umh/candidates/wave2/x/targets/run-{i}: "
            f"ok=True ['worker_home', 'lease', 'credentials']"
            for i in range(12)
        ],
        "runner starting: pid=@PID@ run_root=/x spool=/y primitive=bwrap max_workers=2",
    ]
    # Chatter BEFORE the marker kills a head-window read; chatter AFTER it kills
    # a tail-window read. A real runner produces both — it logs its startup
    # sequence, announces, then logs worker-loop activity — so the fixture must
    # bracket the marker on BOTH sides or one truncation direction stays
    # invisible. (Found by extending R11's M6 along its own axis: `[:200]` and
    # `[:400]` are caught by the leading chatter, `[-200:]` only by the trailing.)
    post_announce = [f"claimed dispatch 0000000{i}-ea-wp-a.json" for i in range(8)]
    _install_fake_runner_script(
        mod,
        tmp_path,
        monkeypatch,
        lines=[*chatter, "control-plane driver up: pid=@PID@ run_root=/x", *post_announce],
    )
    out = _start(mod)
    assert out["started"] is True, (
        "a healthy runner whose readiness marker sits past realistic startup "
        f"chatter was reported failed — the evidence read is truncating: {out}"
    )


def test_a_slow_runner_that_announces_later_is_still_accepted(env, tmp_path, monkeypatch):
    """The launcher must POLL until the deadline, not decide on the first look.

    Second finding from self-adversarial mutation: replacing `if not alive:
    break` with an unconditional `break` survived the original suite, because
    every fixture wrote its log before the first poll. A real runner takes time
    to start — under that mutant a slow-but-healthy runner is rejected on
    iteration 1 with announced=False.

    Here the process sleeps past several polls before announcing, so only an
    implementation that keeps polling can see it.
    """
    mod = env
    scripts = tmp_path / "fake_worktree" / "scripts"
    scripts.mkdir(parents=True, exist_ok=True)
    # The launcher's clock is accelerated 12x by `_accelerate_deadline`, so its
    # real 30s deadline elapses in ~2.5s of wall time and each 1s poll sleeps
    # 0.25s. Announce after ~0.6s: comfortably past the FIRST poll (which is what
    # the mutant decides on) yet well inside the budget.
    (scripts / "wave2_attempt_runner.py").write_text(
        "import os, sys, time\n"
        # nothing on stdout for the first couple of polls
        "time.sleep(0.6)\n"
        'sys.stdout.write("control-plane driver up: pid=%d run_root=/x\\n" % os.getpid())\n'
        "sys.stdout.flush()\n"
        "time.sleep(30)\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(mod, "_WORKTREE", tmp_path / "fake_worktree")
    out = _start(mod)
    assert out["started"] is True, (
        "a healthy runner that announced after the first poll was rejected — "
        f"the launcher is not polling to its deadline: {out}"
    )


def test_announced_then_died_is_not_started(env, tmp_path, monkeypatch):
    """A process that ANNOUNCES readiness and then DIES must not be started.

    Found by self-adversarial mutation of this very file: dropping the `alive`
    half of the launcher's guard (`if not (alive and announced)` -> `if not
    announced`) survived all 12 original tests, because every one of them held
    `alive` and `announced` in lockstep. This is the case that separates them —
    the real code returns alive=False, announced=True, started=False, and the
    mutant returns started=True.

    Readiness is a CONJUNCTION: announced AND still running. A runner that
    printed its readiness line and then crashed is not ready, it is dead.
    """
    mod = env
    _install_fake_runner_script(
        mod,
        tmp_path,
        monkeypatch,
        lines=["control-plane driver up: pid=@PID@ run_root=/x"],
        stay_alive=False,
        exit_code=9,
    )
    out = _start(mod)
    # assert the VERDICT first: under the mutant this is True and the success
    # dict carries no diagnostic keys, so checking `announced` first would fail
    # with a bare KeyError instead of naming the defect.
    assert out["started"] is False, (
        "a runner that announced readiness and then DIED was reported started — "
        "the liveness half of the readiness conjunction is not enforced"
    )
    assert out["announced"] is True, "fixture did not actually announce readiness"
    assert out["alive"] is False, "fixture was supposed to exit after announcing"


# --------------------------------------------------------------------------
# NEGATIVE: everything that must NOT permit readiness.
# --------------------------------------------------------------------------


def test_readiness_markers_match_what_the_runner_actually_emits():
    """Cross-module pin: the launcher's markers must match the runner's emissions.

    Found while writing this file — a fixture using `pid=<N>` at end-of-line did
    NOT match, because `pid_tag` requires a TRAILING SPACE (the guard against
    `pid=4242` prefix-matching `pid=42424`). That is correct production behavior,
    but it means every authoritative marker the runner emits MUST be followed by
    more text. Pin both halves so a future edit to either module cannot silently
    desynchronize them.
    """
    dispatch = _dispatch_mod()
    runner_src = Path(REPO, "scripts", "wave2_attempt_runner.py").read_text(encoding="utf-8")
    for marker in dispatch.RUNNER_READY_MARKERS:
        assert marker in runner_src, (
            f"launcher waits for {marker!r} but the runner never emits it — "
            "readiness could never be announced"
        )
        # the emitted line must carry content AFTER `pid={...}` or the trailing
        # space in pid_tag can never match
        idx = runner_src.find(marker)
        tail = runner_src[idx : idx + 220]
        assert "pid={os.getpid()} " in tail, (
            f"marker {marker!r} is emitted without a trailing space after the pid — "
            "runner_readiness_announced can never match it"
        )


def test_startup_only_marker_does_not_permit_started(env, tmp_path, monkeypatch):
    """`runner starting:` is emitted BEFORE the control plane exists. Accepting
    it was the original B1 defect."""
    mod = env
    _install_fake_runner_script(
        mod,
        tmp_path,
        monkeypatch,
        lines=["runner starting: pid=@PID@ run_root=/x"],
        alive_seconds=40.0,
    )
    out = _start(mod)
    assert out["started"] is False, "a startup-only marker was accepted as readiness (B1)"
    assert out["announced"] is False


def test_legacy_runner_up_marker_does_not_permit_started(env, tmp_path, monkeypatch):
    """The legacy `runner up:` marker is emitted before driver construction and
    must never satisfy readiness — it is deliberately absent from
    RUNNER_READY_MARKERS."""
    mod = env
    _install_fake_runner_script(
        mod,
        tmp_path,
        monkeypatch,
        lines=["runner up: pid=@PID@ spool=/x"],
        alive_seconds=40.0,
    )
    out = _start(mod)
    assert out["started"] is False, "legacy 'runner up:' was accepted as readiness (B1)"


def test_another_pids_readiness_does_not_permit_started(env, tmp_path, monkeypatch):
    """A readiness line belonging to a DIFFERENT pid (e.g. a previous run's
    leftover log) must not satisfy readiness for THIS process."""
    mod = env
    _install_fake_runner_script(
        mod,
        tmp_path,
        monkeypatch,
        lines=["control-plane driver up: pid=999999 ok"],
        alive_seconds=40.0,
    )
    out = _start(mod)
    assert out["started"] is False, "another pid's readiness was accepted"


def test_pid_prefix_collision_does_not_permit_started(env, tmp_path, monkeypatch):
    """`pid=4242` must not prefix-match `pid=42424`. The launcher's pid tag keeps
    a TRAILING SPACE for exactly this reason; without it this test fails."""
    mod = env
    # emit readiness for OUR pid with an extra digit appended -> a strict prefix
    _install_fake_runner_script(
        mod,
        tmp_path,
        monkeypatch,
        lines=["control-plane driver up: pid=@PID@9 ok"],
        alive_seconds=40.0,
    )
    out = _start(mod)
    assert out["started"] is False, "a pid-prefix collision was accepted as readiness"


def test_driver_fatal_does_not_permit_started(env, tmp_path, monkeypatch):
    """A FATAL driver line means the control plane never came up. The process
    exits, so the launcher must fail closed rather than wait out the deadline."""
    mod = env
    _install_fake_runner_script(
        mod,
        tmp_path,
        monkeypatch,
        lines=[
            "runner starting: pid=@PID@ run_root=/x",
            "FATAL: control-plane driver construction failed",
        ],
        stay_alive=False,
        exit_code=3,
    )
    out = _start(mod)
    assert out["started"] is False, "a FATAL driver exit was reported as started"
    assert out["alive"] is False


def test_instant_exit_does_not_permit_started(env, tmp_path, monkeypatch):
    """A process that dies immediately (bad launch line) must never be started."""
    mod = env
    _install_fake_runner_script(mod, tmp_path, monkeypatch, lines=[], stay_alive=False, exit_code=1)
    out = _start(mod)
    assert out["started"] is False, "an instantly-dead runner was reported as started"
    assert out["alive"] is False


def test_never_announcing_but_alive_times_out_fail_closed(env, tmp_path, monkeypatch):
    """A process that stays alive but never announces must TIME OUT fail-closed
    — liveness is not readiness."""
    mod = env
    _install_fake_runner_script(
        mod,
        tmp_path,
        monkeypatch,
        lines=["some unrelated chatter"],
        alive_seconds=40.0,
    )
    out = _start(mod)
    assert out["started"] is False, "a live-but-silent runner was reported as started"
    assert out["alive"] is True, "process should still have been alive at timeout"
    assert out["announced"] is False


# --------------------------------------------------------------------------
# THE MUTATION TEST — the reason this file exists.
# --------------------------------------------------------------------------


def test_r10_n4b_mutation_is_killed_by_real_behavior(env, tmp_path, monkeypatch):
    """THE load-bearing test.

    R10's AST-shape-preserving mutant replaced the REAL log contents with a
    fabricated readiness string:

        announced = runner_readiness_announced(
            "control-plane driver up: pid=%d " % proc.pid, proc.pid)

    Both AST assertions still pass (the call is made, its value is bound), and
    the full 888-test suite still passed. This test kills it: with the mutation
    applied, a runner emitting ONLY "runner starting:" would be reported started.

    Rather than editing the source, we prove the equivalent property directly on
    the real function: the readiness verdict must be a function of the REAL LOG
    CONTENTS. A launcher that fabricates its evidence cannot distinguish these
    two runs — this one, and the positive test above — because the fabricated
    string is identical in both. Since this run MUST be `started=False` while the
    positive test MUST be `started=True`, no fabricated-evidence implementation
    can satisfy both.
    """
    mod = env
    _install_fake_runner_script(
        mod,
        tmp_path,
        monkeypatch,
        lines=["runner starting: pid=@PID@ run_root=/x"],
        alive_seconds=40.0,
    )
    out = _start(mod)
    assert out["started"] is False, (
        "R10 N4b mutation is live: readiness was decided from a fabricated string "
        "rather than the real launch log — a dead/unready runner reports started"
    )


def test_readiness_verdict_reads_the_real_launch_log(env, tmp_path, monkeypatch):
    """Complementary structural proof, executed rather than asserted on source.

    Capture the ACTUAL arguments the launcher passes to
    `runner_readiness_announced`. The first argument must be the real log body
    (containing what the process actually wrote), not a synthesized string. This
    kills N4b directly and instantly, without waiting out a deadline.
    """
    mod = env
    seen: list[tuple[str, int]] = []
    real = mod.runner_readiness_announced

    def _spy(log_body, pid):
        seen.append((log_body, pid))
        return real(log_body, pid)

    monkeypatch.setattr(mod, "runner_readiness_announced", _spy)
    _install_fake_runner_script(
        mod,
        tmp_path,
        monkeypatch,
        lines=[
            "runner starting: pid=@PID@ run_root=/x",
            "MARKER-FROM-REAL-LOG",
            "control-plane driver up: pid=@PID@ ok",
        ],
    )
    out = _start(mod)
    assert out["started"] is True
    assert seen, "start_runner never consulted runner_readiness_announced"
    assert any("MARKER-FROM-REAL-LOG" in body for body, _ in seen), (
        "the readiness verdict was computed from a value that does NOT contain the "
        "real launch-log contents — evidence is being fabricated (R10 N4b)"
    )
