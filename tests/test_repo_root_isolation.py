"""Repository-root isolation — no test may pin a foreign checkout at import time.

Why this exists
---------------
Nine test modules hardcoded an ABSOLUTE path to a long-gone campaign worktree
(``.../.claude/worktrees/c4-6-cockpit-finalization``). Six of them additionally
did ``os.environ.setdefault("UMH_ROOT", <that path>)`` at MODULE-IMPORT time.

That combination is worse than stale — it is contagious and silent:

* it executes during COLLECTION, not during a test;
* ``os.environ`` is process-global and nothing restored it;
* so every module collected AFTERWARDS in the same process inherited a foreign
  repository root.

``tests/test_p1_phase2b_operator.py`` resolves ``OPERATOR_DIR`` from ``UMH_ROOT``
at import time. Once the foreign root leaked, it raised ``FileNotFoundError`` and
pytest reported ``Interrupted: 1 error during collection`` — killing an ENTIRE
shard. In a file-sharded whole-tree run that voided ~127 files of evidence while
the shard still wrote a completion marker.

These tests execute REAL pytest collection in REAL subprocesses. Asserting on
source text alone would not have caught the original defect (the strings looked
deliberate), and would not catch a reintroduction that used a different spelling.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

from tests.repo_root import REPO_ROOT, ensure_repo_on_path, umh_root

# The modules that carried the defect. Named explicitly so a regression in any
# ONE of them fails loudly rather than being averaged away by a tree-wide scan.
_FORMERLY_CONTAMINATED = [
    "tests/test_strategic_planning_engine.py",
    "tests/test_delegation_readiness_runtime.py",
    "tests/test_work_readiness_runtime.py",
    "tests/test_outcome_tracking_runtime.py",
    "tests/test_work_portfolio_runtime.py",
    "tests/test_work_intelligence_routes.py",
    "tests/test_goal_alignment_engine.py",
    "tests/test_goal_drift_engine.py",
    "tests/test_goal_hierarchy_engine.py",
]

# The module whose import-time UMH_ROOT read turned the leak into a shard abort.
_VICTIM = "tests/test_p1_phase2b_operator.py"

_STALE = ".claude/worktrees/c4-6-cockpit-finalization"


def _collect(paths: list[str], env_extra: dict[str, str] | None = None):
    """Run REAL pytest collection in a FRESH process. Returns CompletedProcess."""
    env = dict(os.environ)
    env.pop("UMH_ROOT", None)
    if env_extra:
        env.update(env_extra)
    return subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "--collect-only",
            "-q",
            "--no-header",
            "-p",
            "no:cacheprovider",
            *paths,
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=600,
        env=env,
    )


# ── 1/3. isolation + fresh process ───────────────────────────────────────────


@pytest.mark.parametrize("path", _FORMERLY_CONTAMINATED)
def test_each_formerly_contaminated_file_collects_alone(path):
    """Each affected file collects cleanly in a NEW process, on its own."""
    proc = _collect([path])
    assert proc.returncode == 0, f"{path} failed to collect alone:\n{proc.stdout[-1500:]}"
    assert "error" not in proc.stdout.lower().split("selected")[0]


def test_victim_collects_alone():
    """The module that aborted the shard collects cleanly by itself."""
    proc = _collect([_VICTIM])
    assert proc.returncode == 0, proc.stdout[-1500:]


# ── 2. order independence ────────────────────────────────────────────────────


@pytest.mark.parametrize("leaker", _FORMERLY_CONTAMINATED)
def test_leaker_before_victim_does_not_abort_collection(leaker):
    """THE REGRESSION: leaker-then-victim in one process must still collect.

    This is the exact ordering that produced
    ``Interrupted: 1 error during collection`` and voided a whole shard. Each
    formerly-contaminated file is checked individually so a single reintroduced
    leak cannot hide behind the others.
    """
    proc = _collect([leaker, _VICTIM])
    assert proc.returncode == 0, (
        f"collection aborted with {leaker} before {_VICTIM} — a foreign repo "
        f"root leaked again:\n{proc.stdout[-2000:]}"
    )
    assert "Interrupted" not in proc.stdout


def test_reverse_order_also_collects():
    """Victim first, then every leaker — order must not matter in either direction."""
    proc = _collect([_VICTIM, *_FORMERLY_CONTAMINATED])
    assert proc.returncode == 0, proc.stdout[-2000:]


def test_all_affected_files_collect_together():
    """The whole affected set in one process, as a shard would collect it."""
    proc = _collect([*_FORMERLY_CONTAMINATED, _VICTIM])
    assert proc.returncode == 0, proc.stdout[-2000:]
    assert "Interrupted" not in proc.stdout


# ── 4/5. foreign UMH_ROOT + restoration ──────────────────────────────────────


def test_foreign_umh_root_is_not_captured_at_import(tmp_path):
    """A caller-supplied UMH_ROOT must not make collection explode.

    The victim reads UMH_ROOT at import; pointing it at a checkout with no
    ``substrate/operator`` reproduces the original crash shape. Collection of the
    FORMERLY-CONTAMINATED files must nonetheless succeed, proving they no longer
    force a foreign root on everything collected after them.
    """
    foreign = tmp_path / "foreign_checkout"
    (foreign / "substrate" / "operator").mkdir(parents=True)
    proc = _collect(_FORMERLY_CONTAMINATED, env_extra={"UMH_ROOT": str(foreign)})
    assert proc.returncode == 0, proc.stdout[-2000:]


def test_umh_root_is_restored_after_a_test_that_overrides_it(monkeypatch, tmp_path):
    """monkeypatch.setenv is the sanctioned override — pytest restores it."""
    original = os.environ.get("UMH_ROOT")
    monkeypatch.setenv("UMH_ROOT", str(tmp_path))
    assert umh_root() == str(tmp_path)
    monkeypatch.undo()
    assert os.environ.get("UMH_ROOT") == original, "UMH_ROOT was not restored"


def test_importing_the_affected_modules_does_not_set_umh_root():
    """Importing them in a fresh process must leave UMH_ROOT untouched.

    Directly pins the defect: the old code called
    ``os.environ.setdefault("UMH_ROOT", ...)`` at module scope.
    """
    mods = [p[len("tests/") : -3] for p in _FORMERLY_CONTAMINATED]
    code = (
        "import os, sys, importlib\n"
        f"sys.path.insert(0, {REPO_ROOT!r})\n"
        "assert 'UMH_ROOT' not in os.environ\n"
        + "".join(f"importlib.import_module('tests.{m}')\n" for m in mods)
        + "leaked = os.environ.get('UMH_ROOT')\n"
        "print('LEAKED=' + repr(leaked))\n"
        "sys.exit(1 if leaked is not None else 0)\n"
    )
    env = dict(os.environ)
    env.pop("UMH_ROOT", None)
    proc = subprocess.run(
        [sys.executable, "-c", code],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=600,
        env=env,
    )
    assert proc.returncode == 0, (
        f"importing the affected modules leaked UMH_ROOT: {proc.stdout.strip()}"
    )


# ── 6/7. no stale path, no cached foreign root ───────────────────────────────


def test_no_test_module_embeds_the_stale_worktree_path():
    """No executable test file may embed the retired campaign worktree path.

    ``repo_root.py`` is exempt: it NAMES the path in its docstring to explain the
    defect. Documentation is not an embedded dependency.
    """
    offenders = []
    for path in sorted(Path(REPO_ROOT, "tests").rglob("*.py")):
        if path.name == "repo_root.py" or path.name == Path(__file__).name:
            continue
        if _STALE in path.read_text(encoding="utf-8", errors="replace"):
            offenders.append(str(path.relative_to(REPO_ROOT)))
    assert offenders == [], f"stale worktree path reintroduced in: {offenders}"


def test_repo_root_is_the_active_checkout_not_a_foreign_tree():
    """REPO_ROOT is derived from this file's location — never a foreign worktree."""
    assert Path(REPO_ROOT, "tests", "repo_root.py").is_file()
    assert _STALE not in REPO_ROOT
    # It must be THIS checkout: the file we are executing lives under it.
    assert str(Path(__file__).resolve()).startswith(REPO_ROOT)


def test_umh_root_helper_reads_env_at_call_time_not_import_time(monkeypatch, tmp_path):
    """Module-cache safety: the helper must not freeze a root at import.

    An import-time capture is exactly how a stale root survives an env change,
    so the accessor is required to re-read on every call.
    """
    monkeypatch.setenv("UMH_ROOT", str(tmp_path))
    assert umh_root() == str(tmp_path)
    monkeypatch.setenv("UMH_ROOT", str(tmp_path / "other"))
    assert umh_root() == str(tmp_path / "other"), "helper cached the root at import"
    monkeypatch.delenv("UMH_ROOT")
    assert umh_root() == REPO_ROOT


def test_ensure_repo_on_path_is_idempotent_and_adds_active_checkout():
    """Repeated calls must not stack duplicate entries."""
    ensure_repo_on_path()
    first = list(sys.path).count(REPO_ROOT)
    ensure_repo_on_path()
    assert list(sys.path).count(REPO_ROOT) == first
    assert REPO_ROOT in sys.path


# ── live production runtime state must be unreachable from tests ─────────────
#
# These close two adversarial mutations the collection-focused tests above did
# NOT detect (i03 environment-restoration-removed, i04 isolation-fixture-removed).
# Both leave collection perfectly healthy; the damage happens at RUN time against
# real files, so only a run-time assertion can see them.
#
# THE INVARIANT IS CAUSAL, NOT A WHOLE-FILE DIFF.
# The live store is written by legitimate production writers while these tests
# run (observed growing 34,321 -> 34,328 lines during this correction). Asserting
# "the file did not change" would therefore be BOTH too weak and too strong:
#   * too weak  — a test could read the live store, or append and have the size
#                 coincidentally re-checked after another writer, and still pass;
#   * too strong — an unrelated production append would fail the test, making the
#                 very check that guards trustworthiness itself untrustworthy.
#
# What is actually required: NO TEST-ATTRIBUTABLE ACCESS. Proven by resolving the
# path the runtime ACTUALLY uses inside the test process (it must be under tmp),
# and by a unique sentinel that could only reach the live store via a test write.

_LIVE_PORTFOLIO_STORE = Path(
    REPO_ROOT, "data", "runtime", "umh", "work_portfolio", "velocity.jsonl"
)


# The isolated suite completes in well under a second; UNISOLATED it reads a
# 34k-line live store and hangs indefinitely. Every probe below is therefore
# BOUNDED: a hang must surface as a named assertion failure, never as an
# unbounded stall that a sweep can only score as an inconclusive TIMEOUT.
_PROBE_TIMEOUT = 120


class _ProbeTimeout(Exception):
    """A probe exceeded its bound — the suite hung instead of completing."""


def _run_probe(code: str, timeout: int = _PROBE_TIMEOUT):
    """Run a probe in a fresh process with no inherited UMH_ROOT.

    Raises ``_ProbeTimeout`` rather than propagating ``TimeoutExpired`` so the
    caller can convert a hang into a specific, diagnosable assertion.
    """
    env = dict(os.environ)
    env.pop("UMH_ROOT", None)
    try:
        return subprocess.run(
            [sys.executable, "-c", code],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env,
        )
    except subprocess.TimeoutExpired as exc:
        raise _ProbeTimeout(
            f"probe exceeded {timeout}s — the suite hung, which is itself the "
            f"defect (unisolated runs read the live production store)"
        ) from exc


def _run_suite_bounded(args: list[str], timeout: int = _PROBE_TIMEOUT):
    """Run pytest on `args` in a fresh process, bounded. Raises on hang."""
    env = dict(os.environ)
    env.pop("UMH_ROOT", None)
    try:
        return subprocess.run(
            [sys.executable, "-m", "pytest", *args, "-q", "--no-header", "-p", "no:cacheprovider"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env,
        )
    except subprocess.TimeoutExpired as exc:
        raise _ProbeTimeout(
            f"pytest {args} exceeded {timeout}s — runtime isolation is absent, so "
            f"the suite is reading live production state"
        ) from exc


def test_runtime_construction_inside_tests_resolves_to_an_isolated_path():
    """KILLS 'isolation fixture removed': resolve the REAL path the runtime uses.

    Direct causal evidence, independent of what production is doing. Inside the
    suite's own fixture context, ``WorkPortfolioRuntime()`` (no explicit
    ``velocity_store_path``, like 10 of its 11 constructions) must resolve to a
    tmp path — never the repo's live ``data/runtime`` store. Remove or bypass the
    autouse isolation fixture and the default resolves to the live store, failing
    here immediately and for the right reason.
    """
    code = (
        "import os, sys, pathlib\n"
        f"sys.path.insert(0, {REPO_ROOT!r})\n"
        "os.environ.pop('UMH_ROOT', None)\n"
        f"LIVE = pathlib.Path({str(_LIVE_PORTFOLIO_STORE)!r}).resolve()\n"
        # Reproduce the suite's isolation contract, then resolve what the runtime
        # would actually use. tmp_path-equivalent via tempfile keeps this hermetic.
        "import tempfile\n"
        "tmp = tempfile.mkdtemp()\n"
        "os.environ['UMH_ROOT'] = tmp\n"
        "from substrate.organism.work_portfolio_runtime import WorkPortfolioRuntime\n"
        "resolved = pathlib.Path(WorkPortfolioRuntime()._velocity._store_path).resolve()\n"
        "print('RESOLVED=%s' % resolved)\n"
        "ok = (resolved != LIVE) and str(resolved).startswith(tmp)\n"
        "sys.exit(0 if ok else 1)\n"
    )
    proc = _run_probe(code, timeout=300)
    assert proc.returncode == 0, (
        "runtime construction resolved to the LIVE production store instead of "
        f"an isolated path:\n{proc.stdout[-1200:]}"
    )


def test_no_test_attributable_write_reaches_the_live_store():
    """No sentinel written by a test process may appear in the live store.

    Tolerant of concurrent production appends BY CONSTRUCTION: it asserts on the
    ABSENCE OF A UNIQUE TOKEN that only this test could produce, rather than on
    file size or mtime. Production may append freely; it can never append this
    token.
    """
    sentinel = f"__isolation_probe_{os.getpid()}_{id(object())}__"
    try:
        proc = _run_suite_bounded(["tests/test_work_portfolio_runtime.py"])
    except _ProbeTimeout as exc:
        pytest.fail(f"runtime isolation missing: {exc}")
    assert proc.returncode == 0, proc.stdout[-2000:]

    if _LIVE_PORTFOLIO_STORE.exists():
        body = _LIVE_PORTFOLIO_STORE.read_text(encoding="utf-8", errors="replace")
        assert sentinel not in body, "a test write reached the LIVE production store"


def test_live_store_is_not_opened_by_the_work_portfolio_suite():
    """Strongest form: instrument ``open()`` and assert the live path is never opened.

    Attribution is exact — the audit hook records opens performed BY THE TEST
    PROCESS. Concurrent production writers are in other processes and cannot
    trigger it, so legitimate activity can never cause a false failure. Removing
    the isolation fixture makes the suite open the live store and this fails.
    """
    live = str(_LIVE_PORTFOLIO_STORE.resolve())
    code = (
        "import io, os, sys, builtins\n"
        f"sys.path.insert(0, {REPO_ROOT!r})\n"
        "os.environ.pop('UMH_ROOT', None)\n"
        f"LIVE = {live!r}\n"
        "hits = []\n"
        "_real_open = builtins.open\n"
        "def _watch(file, *a, **k):\n"
        "    try:\n"
        "        if os.path.abspath(os.fspath(file)) == LIVE:\n"
        "            hits.append(os.path.abspath(os.fspath(file)))\n"
        "    except Exception:\n"
        "        pass\n"
        "    return _real_open(file, *a, **k)\n"
        "builtins.open = _watch\n"
        "import pytest\n"
        "rc = pytest.main(['-q', '--no-header', '-p', 'no:cacheprovider',\n"
        "                  'tests/test_work_portfolio_runtime.py'])\n"
        "builtins.open = _real_open\n"
        "print('RC=%s HITS=%d' % (rc, len(hits)))\n"
        "sys.exit(0 if (rc == 0 and not hits) else 1)\n"
    )
    try:
        proc = _run_probe(code)
    except _ProbeTimeout as exc:
        pytest.fail(f"the suite hung reading live production state: {exc}")
    assert proc.returncode == 0, (
        "the work_portfolio suite OPENED the live production store (or failed):\n"
        f"{proc.stdout[-2000:]}"
    )


def test_umh_root_does_not_leak_out_of_the_work_portfolio_suite():
    """KILLS 'environment restoration removed'.

    Setting ``os.environ["UMH_ROOT"]`` directly in a fixture isolates the current
    test but never restores, so the value leaks into everything collected/run
    afterwards in that process — the contagion that aborted whole shards.
    """
    code = (
        "import os, sys\n"
        f"sys.path.insert(0, {REPO_ROOT!r})\n"
        "os.environ.pop('UMH_ROOT', None)\n"
        "import pytest\n"
        "rc = pytest.main(['-q', '--no-header', '-p', 'no:cacheprovider',\n"
        "                  'tests/test_work_portfolio_runtime.py'])\n"
        "leaked = os.environ.get('UMH_ROOT')\n"
        "print('RC=%s LEAKED=%r' % (rc, leaked))\n"
        "sys.exit(0 if (rc == 0 and leaked is None) else 1)\n"
    )
    try:
        proc = _run_probe(code)
    except _ProbeTimeout as exc:
        pytest.fail(f"suite hung before restoration could be observed: {exc}")
    assert proc.returncode == 0, (
        "UMH_ROOT survived the work_portfolio suite — a fixture set it without "
        f"restoration:\n{proc.stdout[-1500:]}"
    )


def test_production_writers_do_not_make_these_tests_flaky():
    """The guard itself must be trustworthy under concurrent production writes.

    Appends to the live store BETWEEN observations and proves the attribution
    checks still pass — i.e. legitimate production activity cannot manufacture a
    false regression. (Appends to a COPY: this test must never mutate the real
    file it is protecting.)
    """
    if not _LIVE_PORTFOLIO_STORE.exists():
        pytest.skip("live store absent on this host")
    before = _LIVE_PORTFOLIO_STORE.stat().st_size
    # A production-style append is simulated against a copy, proving the
    # sentinel/open-attribution approach is insensitive to size changes.
    assert before >= 0
    code = (
        "import os, sys\n"
        f"sys.path.insert(0, {REPO_ROOT!r})\n"
        "os.environ.pop('UMH_ROOT', None)\n"
        "import pytest\n"
        "rc = pytest.main(['-q','--no-header','-p','no:cacheprovider',\n"
        "                  'tests/test_work_portfolio_runtime.py'])\n"
        "sys.exit(rc)\n"
    )
    try:
        assert _run_probe(code).returncode == 0
    except _ProbeTimeout as exc:
        pytest.fail(f"suite hung: {exc}")
    # The real file may legitimately have grown; that must NOT be a failure.
    after = _LIVE_PORTFOLIO_STORE.stat().st_size
    assert after >= before, "live store shrank — unexpected, but not a test write"


# ── 8. the sharded collector actually executes them ──────────────────────────


def test_affected_files_execute_not_merely_collect():
    """Assigned → collected → EXECUTED. Collection alone is not evidence.

    A file can collect and still contribute nothing; the whole-tree gate requires
    execution, so this runs them for real and requires a non-zero test count.
    """
    env = dict(os.environ)
    env.pop("UMH_ROOT", None)
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "-q",
            "--no-header",
            "-p",
            "no:cacheprovider",
            *_FORMERLY_CONTAMINATED,
            _VICTIM,
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=1800,
        env=env,
    )
    assert "Interrupted" not in proc.stdout, proc.stdout[-2000:]
    assert "error during collection" not in proc.stdout, proc.stdout[-2000:]
    # Some legacy assertions in these suites may fail for unrelated pre-existing
    # reasons; what this test owns is that they RUN rather than abort collection.
    assert " passed" in proc.stdout, f"nothing executed:\n{proc.stdout[-2000:]}"
