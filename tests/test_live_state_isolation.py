"""Behavioral regressions for the Group A live-runtime-state isolation seam.

These tests exist because the seam is load-bearing for the whole-tree gate: if it
silently stops working, 28 files quietly resume resolving into the live
production store at ``/opt/OS/data/runtime`` and the whole-tree run goes back to
timing out — while every surface signal still looks healthy. Each test below
pins one property that, if broken, would let that happen.

They assert BEHAVIOUR (what a real pytest process actually resolves and opens),
not source text. A source-text assertion would survive the seam being deleted at
runtime, which is exactly the failure these guard against.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

from tests.repo_root import REPO_ROOT
from tests.runtime_isolation import (
    GROUP_A_FILES,
    LIVE_RUNTIME_ROOT,
    SENTINEL_NAME,
    IsolationSetupError,
    assert_outside_live_runtime,
    build_isolated_root,
    is_group_a,
)

pytestmark = pytest.mark.live_state_isolated

_PROBE_TIMEOUT = 180


def _run(args: list[str], **kw) -> subprocess.CompletedProcess:
    """Run a bounded subprocess, turning a hang into a NAMED failure.

    An unbounded probe here would reproduce the very defect under test (a test
    that stalls instead of reporting), so the timeout is mandatory and its
    expiry is surfaced as an assertion failure rather than a raised exception.
    """
    try:
        return subprocess.run(
            args, capture_output=True, text=True, timeout=_PROBE_TIMEOUT, **kw
        )
    except subprocess.TimeoutExpired:
        pytest.fail(f"probe exceeded {_PROBE_TIMEOUT}s (a stall is the defect under test): {args}")


# ── manifest integrity ───────────────────────────────────────────────────────


def test_manifest_has_exactly_29_unique_files():
    """The reconciled Group A manifest is 29 unique files — no drift, no dupes.

    28 at the original isolation correction, +1 for
    test_strategic_context_runtime.py (live-state coupled in the same way,
    though its separate read cascade is not addressed by isolation).

    The literal is deliberate. The manifest is an EXACT reviewed list, so a file
    joining or leaving it must be a visible, intentional edit here rather than
    an incidental side effect of some other change.
    """
    assert len(GROUP_A_FILES) == 29


def test_every_manifest_file_exists_on_disk():
    """A manifest naming a file that no longer exists would silently under-apply."""
    missing = [n for n in GROUP_A_FILES if not (Path(REPO_ROOT) / "tests" / n).is_file()]
    assert missing == [], f"manifest names files that do not exist: {missing}"


def test_strategic_context_file_is_bound_to_the_isolation_manifest():
    """The blocking file must stay isolated — removing it fails here.

    This assertion previously read ``not in GROUP_A_FILES``, on the reasoning
    that the file's root cause (a strategic-context read cascade) was distinct
    from Group A's live-state coupling. That reasoning was correct about the
    cascade and incomplete about the file: it is ALSO live-state coupled, and
    that coupling alone is enough to make it non-terminating under whole-tree.

    Inverting the assertion rather than deleting it is deliberate — it is the
    adversarial binding. If the entry is ever dropped from the manifest, this
    fails loudly instead of the file silently resuming live reads and the gate
    silently regressing to a timeout.
    """
    assert "test_strategic_context_runtime.py" in GROUP_A_FILES


def test_manifest_binding_actually_drives_the_fixture():
    """Membership must be what the fixture consults — not a decorative list.

    Guards the mutation "manifest entry present but selector ignores it": the
    entry is only meaningful if ``is_group_a`` resolves it, since that is the
    predicate the autouse fixture branches on.
    """
    assert is_group_a("tests/test_strategic_context_runtime.py")
    assert is_group_a(Path(REPO_ROOT) / "tests" / "test_strategic_context_runtime.py")
    # And a file deliberately outside the manifest still resolves False, so the
    # predicate is discriminating rather than universally true.
    assert not is_group_a("tests/test_live_state_isolation.py")


def test_is_group_a_matches_by_filename_not_path_prefix():
    assert is_group_a("tests/test_governance_runtime.py")
    assert is_group_a(Path("/anywhere/tests/test_governance_runtime.py"))
    assert not is_group_a("tests/test_wave2_admission_pause_behavior.py")


# ── isolated-root construction ───────────────────────────────────────────────


def test_build_isolated_root_creates_relative_store_skeleton(tmp_path):
    """Relative Path("data/runtime/...") consumers need the dirs to exist."""
    root = build_isolated_root(tmp_path)
    assert (root / "data" / "runtime").is_dir()
    assert (root / "data" / "runtime" / "spine_dispatch_queue" / "inbox").is_dir()
    assert (root / SENTINEL_NAME).is_file()


def test_isolated_root_contains_no_live_production_data(tmp_path):
    """An isolated root must be EMPTY — copying live stores would defeat it."""
    root = build_isolated_root(tmp_path)
    files = [p for p in (root / "data" / "runtime").rglob("*") if p.is_file()]
    assert files == [], f"isolated runtime root must start empty, found: {files}"


def test_assert_outside_live_runtime_rejects_live_paths():
    """Fail closed: a root inside the live store is refused, not used."""
    with pytest.raises(IsolationSetupError):
        assert_outside_live_runtime(LIVE_RUNTIME_ROOT)
    with pytest.raises(IsolationSetupError):
        assert_outside_live_runtime(f"{LIVE_RUNTIME_ROOT}/umh/organism")


def test_assert_outside_live_runtime_accepts_tmp(tmp_path):
    assert_outside_live_runtime(tmp_path)  # must not raise


# ── the fixture's own behaviour, observed from inside a test ────────────────


def test_fixture_does_not_apply_to_non_group_a_tests():
    """This file is NOT in Group A, so cwd must remain the real repo root.

    Pins the scope decision: the seam is manifest-driven, not repo-wide.
    """
    assert Path(os.getcwd()).resolve() != Path(LIVE_RUNTIME_ROOT).resolve()
    assert (Path(os.getcwd()) / SENTINEL_NAME).exists() is False


# ── end-to-end: a real Group A file under the seam ───────────────────────────


def test_group_a_file_resolves_runtime_state_into_isolated_root():
    """A Group A test must resolve runtime state inside its tmp root, not /opt/OS.

    This is the core property. It is checked by running a real pytest process
    with NO env preconfigured — exactly how the whole-tree harness runs it.
    """
    env = {k: v for k, v in os.environ.items() if k not in ("UMH_STATE_DIR", "UMH_ROOT")}
    # A REAL Group A file, so the manifest-scoped fixture actually engages. The
    # -p plugin prints what runtime_state_root() ACTUALLY resolves to from
    # inside that file's test session — the resolved value is the assertion,
    # not merely that the file passed.
    target = Path(REPO_ROOT) / "tests" / "test_governance_runtime.py"
    assert target.is_file()
    res = _run(
        [
            sys.executable, "-m", "pytest", str(target),
            "-q", "--no-header", "-p", "no:cacheprovider",
            "-p", "tests.isolation_probe_plugin",
        ],
        cwd=REPO_ROOT,
        env=env,
    )
    assert res.returncode == 0, f"Group A file failed under the seam:\n{res.stdout[-3000:]}"
    markers = [ln for ln in res.stdout.splitlines() if ln.startswith("RESOLVED_STATE_ROOT=")]
    assert markers, f"probe plugin produced no marker:\n{res.stdout[-2000:]}"
    for line in markers:
        resolved = line.split("=", 1)[1].strip()
        assert not resolved.startswith(LIVE_RUNTIME_ROOT), (
            f"Group A test resolved runtime state into the LIVE store: {resolved}"
        )


def test_group_a_file_is_fast_under_isolation():
    """Duration is the symptom that made this a whole-tree blocker.

    Pre-fix this file exceeded a 60s bound; isolated it completes in ~1s. A
    generous ceiling still catches a regression to live-store resolution.
    """
    import time

    env = {k: v for k, v in os.environ.items() if k not in ("UMH_STATE_DIR", "UMH_ROOT")}
    start = time.monotonic()
    res = _run(
        [
            sys.executable, "-m", "pytest",
            str(Path(REPO_ROOT) / "tests" / "test_resource_allocation_runtime.py"),
            "-q", "--no-header", "-p", "no:cacheprovider",
        ],
        cwd=REPO_ROOT,
        env=env,
    )
    elapsed = time.monotonic() - start
    assert res.returncode == 0, res.stdout[-2000:]
    assert elapsed < 45, f"Group A file took {elapsed:.1f}s — isolation likely regressed"


def test_no_live_runtime_access_during_group_a_run(tmp_path):
    """Causal proof: audit every open() and assert none touches the live store.

    Whole-file equality on the live store would be useless here — production
    services write to it concurrently, so equality fails for reasons unrelated to
    the tests. Attribution must be causal, so this instruments open() inside the
    test process itself.
    """
    audit = tmp_path / "audit.txt"
    runner = tmp_path / "runner.py"
    runner.write_text(
        "import builtins, os, sys\n"
        f"LIVE = {LIVE_RUNTIME_ROOT!r}\n"
        f"AUDIT = {str(audit)!r}\n"
        "hits = []\n"
        "_open = builtins.open\n"
        "def spy(file, mode='r', *a, **k):\n"
        "    try:\n"
        "        p = os.path.realpath(str(file))\n"
        "        if p.startswith(LIVE):\n"
        "            hits.append(mode + ' ' + p)\n"
        "    except Exception:\n"
        "        pass\n"
        "    return _open(file, mode, *a, **k)\n"
        "builtins.open = spy\n"
        "import pytest\n"
        "code = pytest.main([sys.argv[1], '-q', '--no-header', '-p', 'no:cacheprovider'])\n"
        "builtins.open = _open\n"
        "_open(AUDIT, 'w').write('\\n'.join(hits))\n"
        "sys.exit(0 if code == 0 else 1)\n",
        encoding="utf-8",
    )
    env = {k: v for k, v in os.environ.items() if k not in ("UMH_STATE_DIR", "UMH_ROOT")}
    res = _run(
        [sys.executable, str(runner), str(Path(REPO_ROOT) / "tests" / "test_governance_runtime.py")],
        cwd=REPO_ROOT,
        env=env,
    )
    assert res.returncode == 0, res.stdout[-2000:]
    recorded = audit.read_text(encoding="utf-8").strip() if audit.exists() else ""
    assert recorded == "", f"test-attributable live-runtime access detected:\n{recorded}"


def test_subprocess_inherits_isolated_state_dir():
    """A subprocess spawned by a Group A test must not see the live root.

    The fixture exports into os.environ (not just a pytest-local monkeypatch)
    precisely so child processes inherit the isolated root.
    """
    env = {k: v for k, v in os.environ.items() if k not in ("UMH_STATE_DIR", "UMH_ROOT")}
    # Run a real Group A file with the probe plugin, which spawns a CHILD process
    # during teardown and reports what that child inherited. If the fixture used
    # a pytest-local monkeypatch instead of os.environ, the child would see the
    # live root and this assertion would fail.
    target = Path(REPO_ROOT) / "tests" / "test_c19_integration.py"
    assert target.is_file()
    res = _run(
        [
            sys.executable, "-m", "pytest", str(target),
            "-q", "--no-header", "-p", "no:cacheprovider",
            "-p", "tests.subprocess_probe_plugin",
        ],
        cwd=REPO_ROOT,
        env=env,
    )
    assert res.returncode == 0, res.stdout[-2000:]
    markers = [ln for ln in res.stdout.splitlines() if ln.startswith("CHILD_STATE_DIR=")]
    assert markers, f"subprocess probe produced no marker:\n{res.stdout[-2000:]}"
    for line in markers:
        child = line.split("=", 1)[1].strip()
        assert child != "UNSET", "subprocess did not inherit UMH_STATE_DIR"
        assert not child.startswith(LIVE_RUNTIME_ROOT), f"child inherited live root: {child}"


def test_cwd_is_isolated_during_a_group_a_test():
    """cwd MUST move into the isolated root while a Group A test runs.

    This is the ONLY thing that redirects the relative ``Path("data/runtime/...")``
    literals (mesh_nodes.json, the proof dirs, the bootstrap store list) that
    never pass through ``runtime_state_path()``. Without it those resolve against
    the repo checkout and, in a deployed layout, against live state.

    Kills the mutant that drops ``os.chdir(root)``: an env-only seam leaves cwd
    at the repo root and this assertion fails.
    """
    env = {k: v for k, v in os.environ.items() if k not in ("UMH_STATE_DIR", "UMH_ROOT")}
    res = _run(
        [
            sys.executable, "-m", "pytest",
            str(Path(REPO_ROOT) / "tests" / "test_governance_runtime.py"),
            "-q", "--no-header", "-p", "no:cacheprovider",
            "-p", "tests.cwd_probe_plugin",
        ],
        cwd=REPO_ROOT,
        env=env,
    )
    assert res.returncode == 0, res.stdout[-2000:]
    markers = [ln for ln in res.stdout.splitlines() if ln.startswith("TEST_CWD=")]
    assert markers, f"cwd probe produced no marker:\n{res.stdout[-2000:]}"
    for line in markers:
        cwd = line.split("=", 1)[1].strip()
        assert cwd != REPO_ROOT, (
            "cwd was NOT isolated during a Group A test — relative "
            "Path('data/runtime/...') consumers would resolve outside the isolated root"
        )
        assert (Path(cwd) / SENTINEL_NAME).is_file(), (
            f"cwd {cwd} is not an isolated runtime root (sentinel missing)"
        )


def test_relative_runtime_path_resolves_inside_isolated_root():
    """A relative data/runtime path must land in the isolated root, not the repo.

    Mirrors what compute_fabric_runtime.py / distributed_runtime.py actually do
    (``Path("data/runtime/mesh_nodes.json")``) and proves the isolated cwd — not
    UMH_STATE_DIR — is what contains them.
    """
    env = {k: v for k, v in os.environ.items() if k not in ("UMH_STATE_DIR", "UMH_ROOT")}
    res = _run(
        [
            sys.executable, "-m", "pytest",
            str(Path(REPO_ROOT) / "tests" / "test_governance_runtime.py"),
            "-q", "--no-header", "-p", "no:cacheprovider",
            "-p", "tests.cwd_probe_plugin",
        ],
        cwd=REPO_ROOT,
        env=env,
    )
    assert res.returncode == 0, res.stdout[-2000:]
    markers = [ln for ln in res.stdout.splitlines() if ln.startswith("RELATIVE_RUNTIME=")]
    assert markers, f"relative-path probe produced no marker:\n{res.stdout[-2000:]}"
    for line in markers:
        resolved = line.split("=", 1)[1].strip()
        assert not resolved.startswith(LIVE_RUNTIME_ROOT), resolved
        assert not resolved.startswith(REPO_ROOT), (
            f"relative runtime path resolved into the source checkout: {resolved}"
        )


def test_cwd_restored_after_group_a_test_completes():
    """Teardown MUST restore cwd, or every later file inherits a deleted tmp dir.

    pytest's tmp dirs are reaped, so a leaked cwd can leave later tests running
    in a removed directory — a failure mode that manifests far from its cause.

    Kills the mutant that drops ``os.chdir(prev_cwd)``: the probe records cwd
    after a Group A test finishes and compares it to the starting directory.
    """
    env = {k: v for k, v in os.environ.items() if k not in ("UMH_STATE_DIR", "UMH_ROOT")}
    res = _run(
        [
            sys.executable, "-m", "pytest",
            str(Path(REPO_ROOT) / "tests" / "test_governance_runtime.py"),
            "-q", "--no-header", "-p", "no:cacheprovider",
            "-p", "tests.cwd_probe_plugin",
        ],
        cwd=REPO_ROOT,
        env=env,
    )
    assert res.returncode == 0, res.stdout[-2000:]
    finals = [ln for ln in res.stdout.splitlines() if ln.startswith("FINAL_CWD=")]
    assert finals, f"final-cwd probe produced no marker:\n{res.stdout[-2000:]}"
    final = finals[-1].split("=", 1)[1].strip()
    assert final == REPO_ROOT, (
        f"cwd was not restored after the Group A file: {final!r} != {REPO_ROOT!r}"
    )


def test_state_dir_restored_after_group_a_test_completes():
    """Teardown must restore UMH_STATE_DIR to its PRE-EXISTING value.

    Two distinct leaks are possible and both matter:

    * unset -> set: a later non-Group-A test inherits a tmp root that pytest has
      already reaped;
    * set -> overwritten: an operator running the suite with a deliberate
      UMH_STATE_DIR silently loses it partway through the run.

    The second is what the ``prev_state`` restore branch exists for, so the probe
    runs with UMH_STATE_DIR PRE-SET to a known sentinel value and asserts that
    exact value survives. Restoring only on the ``None`` branch fails here.
    """
    env = {k: v for k, v in os.environ.items() if k not in ("UMH_STATE_DIR", "UMH_ROOT")}
    preset = "/tmp/umh-preset-state-dir-sentinel"
    env["UMH_STATE_DIR"] = preset
    res = _run(
        [
            sys.executable, "-m", "pytest",
            str(Path(REPO_ROOT) / "tests" / "test_governance_runtime.py"),
            "-q", "--no-header", "-p", "no:cacheprovider",
            "-p", "tests.cwd_probe_plugin",
        ],
        cwd=REPO_ROOT,
        env=env,
    )
    assert res.returncode == 0, res.stdout[-2000:]
    finals = [ln for ln in res.stdout.splitlines() if ln.startswith("FINAL_STATE_DIR=")]
    assert finals, f"final-state probe produced no marker:\n{res.stdout[-2000:]}"
    final = finals[-1].split("=", 1)[1].strip()
    assert final == preset, (
        f"UMH_STATE_DIR was not restored to its pre-existing value: {final!r} != {preset!r}"
    )


def test_state_dir_unset_stays_unset_after_group_a_test():
    """The unset->set leak direction, pinned separately from the overwrite case."""
    env = {k: v for k, v in os.environ.items() if k not in ("UMH_STATE_DIR", "UMH_ROOT")}
    res = _run(
        [
            sys.executable, "-m", "pytest",
            str(Path(REPO_ROOT) / "tests" / "test_governance_runtime.py"),
            "-q", "--no-header", "-p", "no:cacheprovider",
            "-p", "tests.cwd_probe_plugin",
        ],
        cwd=REPO_ROOT,
        env=env,
    )
    assert res.returncode == 0, res.stdout[-2000:]
    finals = [ln for ln in res.stdout.splitlines() if ln.startswith("FINAL_STATE_DIR=")]
    assert finals, f"final-state probe produced no marker:\n{res.stdout[-2000:]}"
    assert finals[-1].split("=", 1)[1].strip() == "UNSET", (
        "UMH_STATE_DIR leaked past the Group A file's teardown"
    )


def test_cwd_and_env_restored_after_group_a_file():
    """Teardown must restore cwd/env or later files inherit a stale root."""
    env = {k: v for k, v in os.environ.items() if k not in ("UMH_STATE_DIR", "UMH_ROOT")}
    res = _run(
        [
            sys.executable, "-m", "pytest",
            str(Path(REPO_ROOT) / "tests" / "test_governance_runtime.py"),
            str(Path(REPO_ROOT) / "tests" / "test_live_state_isolation.py"),
            "-q", "--no-header", "-p", "no:cacheprovider",
            "-k", "test_fixture_does_not_apply_to_non_group_a_tests or test_manifest",
        ],
        cwd=REPO_ROOT,
        env=env,
    )
    assert res.returncode == 0, (
        "running a Group A file before a non-Group-A file must leave cwd/env clean:\n"
        + res.stdout[-2500:]
    )


def test_order_independence_group_a_then_other():
    """Collection order must not change what a later file resolves."""
    env = {k: v for k, v in os.environ.items() if k not in ("UMH_STATE_DIR", "UMH_ROOT")}
    a = Path(REPO_ROOT) / "tests" / "test_governance_runtime.py"
    b = Path(REPO_ROOT) / "tests" / "test_resource_allocation_runtime.py"
    fwd = _run(
        [sys.executable, "-m", "pytest", str(a), str(b), "-q", "--no-header", "-p", "no:cacheprovider"],
        cwd=REPO_ROOT, env=env,
    )
    rev = _run(
        [sys.executable, "-m", "pytest", str(b), str(a), "-q", "--no-header", "-p", "no:cacheprovider"],
        cwd=REPO_ROOT, env=env,
    )
    assert fwd.returncode == 0, fwd.stdout[-2000:]
    assert rev.returncode == 0, rev.stdout[-2000:]


# ── Stage-1 bounded external dependency ──────────────────────────────────────


def test_stage1_skips_fast_when_service_absent():
    """Stage-1 must resolve in seconds, not accumulate ~35 x 10s timeouts."""
    import time

    env = {k: v for k, v in os.environ.items() if k not in ("UMH_STATE_DIR", "UMH_ROOT")}
    env["UMH_COCKPIT_URL"] = "http://127.0.0.1:9"  # discard port — never answers
    start = time.monotonic()
    res = _run(
        [
            sys.executable, "-m", "pytest",
            str(Path(REPO_ROOT) / "tests" / "test_stage1_acceptance_e2e.py"),
            "-q", "--no-header", "-p", "no:cacheprovider",
        ],
        cwd=REPO_ROOT,
        env=env,
    )
    elapsed = time.monotonic() - start
    assert res.returncode == 0, res.stdout[-2000:]
    assert "skipped" in res.stdout, res.stdout[-2000:]
    assert elapsed < 60, f"Stage-1 took {elapsed:.1f}s — the bounded preflight regressed"


def test_stage1_skip_reason_names_the_endpoint():
    """An absent service must be explicitly named, never silently swallowed."""
    from tests.bounded_http import require_live_service

    reason = require_live_service("http://127.0.0.1:9")
    assert reason is not None
    assert "127.0.0.1:9" in reason
    assert "unreachable" in reason


def test_probe_is_bounded_and_never_raises():
    """The probe itself must not reintroduce an unbounded wait."""
    import time

    from tests.bounded_http import probe_http

    start = time.monotonic()
    reachable, detail = probe_http("http://127.0.0.1:9", timeout=2.0)
    elapsed = time.monotonic() - start
    assert reachable is False
    assert detail
    assert elapsed < 15, f"probe took {elapsed:.1f}s — not bounded"


def test_probe_default_timeout_is_small():
    """The DEFAULT probe timeout must stay small.

    ``test_probe_is_bounded_and_never_raises`` passes ``timeout=2.0`` explicitly,
    so it cannot detect the module default being inflated — a mutant that raised
    PROBE_TIMEOUT_SECONDS survived it for exactly that reason. Callers such as
    ``require_live_service`` use the DEFAULT, so the default is the value that
    actually governs Stage-1's runtime and needs its own guard.
    """
    from tests.bounded_http import PROBE_TIMEOUT_SECONDS

    assert 0 < PROBE_TIMEOUT_SECONDS <= 10, (
        f"default probe timeout {PROBE_TIMEOUT_SECONDS}s is too large — Stage-1 would stall"
    )


def test_require_live_service_is_bounded_by_default():
    """The default-timeout path must also return quickly against a dead port."""
    import time

    from tests.bounded_http import require_live_service

    start = time.monotonic()
    reason = require_live_service("http://127.0.0.1:9")
    elapsed = time.monotonic() - start
    assert reason is not None
    assert elapsed < 20, f"default-timeout preflight took {elapsed:.1f}s — not bounded"


def test_build_isolated_root_rejects_missing_sentinel(tmp_path, monkeypatch):
    """Fail closed when the isolated root cannot be fully established.

    If the sentinel cannot be written, the root is not a proven isolated root and
    the seam must refuse rather than let a test proceed against ambiguous state.
    """
    import tests.runtime_isolation as ri

    real_write = Path.write_text

    def refuse(self, *a, **k):
        if self.name == SENTINEL_NAME:
            return 0  # silently write nothing — sentinel never appears
        return real_write(self, *a, **k)

    monkeypatch.setattr(Path, "write_text", refuse)
    with pytest.raises(ri.IsolationSetupError):
        ri.build_isolated_root(tmp_path)


def test_no_global_network_suppression():
    """Other tests must still be able to make real network calls.

    A blanket network block would hide unrelated defects; the correction is
    deliberately scoped to one suite's preflight.
    """
    import socket

    assert hasattr(socket, "socket")
    s = socket.socket()
    s.close()
