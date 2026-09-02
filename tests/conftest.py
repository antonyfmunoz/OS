import os

import pytest

import substrate.execution.bridge  # noqa: F401 — ensure namespace pkg resolves before collection
from tests.runtime_isolation import (
    IsolationSetupError,
    assert_outside_live_runtime,
    build_isolated_root,
    is_group_a,
)


def pytest_ignore_collect(collection_path, config):
    """Skip standalone script-style test files that use sys.exit() instead of pytest."""
    if collection_path.suffix == ".py" and collection_path.name.startswith("test_"):
        content = collection_path.read_text()
        has_test_functions = "def test_" in content
        has_sys_exit = "sys.exit(" in content
        if has_sys_exit and not has_test_functions:
            return True
    return None


@pytest.fixture(autouse=True)
def _isolate_live_runtime_state(request, tmp_path_factory):
    """Point Group A tests at a fresh empty runtime root instead of production.

    Applies ONLY to the exact 28-file Group A manifest (see
    ``tests/runtime_isolation.py`` for why the scope is a manifest rather than
    the whole repository, and for the evidence behind each file's inclusion).

    Closes both live-state paths at once:

    * ``UMH_STATE_DIR`` — consumed at call time by ``runtime_state_root()``, so
      setting it here redirects every canonical runtime-state lookup made after
      this point, regardless of what was imported earlier.
    * the working directory — several modules build ``Path("data/runtime/...")``
      relatively, bypassing ``runtime_state_path()`` entirely. Those resolve
      against cwd, so an isolated cwd is the only way to move them without
      editing production source.

    Both are set with ``monkeypatch``-equivalent save/restore semantics, and both
    are exported into ``os.environ`` so subprocesses spawned by a test inherit
    the same isolated root rather than silently reaching production state.

    Fails CLOSED: if the isolated root cannot be built or resolves inside the
    live store, the test errors instead of running against production.
    """
    if not is_group_a(request.path):
        yield
        return

    root = tmp_path_factory.mktemp("umh_isolated_runtime")
    assert_outside_live_runtime(root)
    build_isolated_root(root)

    state_dir = root / "data" / "runtime" / "umh"
    state_dir.mkdir(parents=True, exist_ok=True)

    prev_state = os.environ.get("UMH_STATE_DIR")
    prev_cwd = os.getcwd()

    # ONLY UMH_STATE_DIR is redirected. UMH_ROOT is deliberately left alone: it
    # names the SOURCE checkout, not runtime state. An earlier version of this
    # fixture also overrode UMH_ROOT, which broke three tests in
    # test_phase14_8c_wave3.py that legitimately resolve source artifacts
    # (scripts/check_*.py, projections/eos/) through it — a real regression
    # introduced by overreaching past the runtime-state boundary. Since
    # runtime_state_root() consults UMH_STATE_DIR FIRST and returns before ever
    # reading UMH_ROOT, redirecting the state dir alone is both sufficient for
    # isolation and correctly scoped.
    os.environ["UMH_STATE_DIR"] = str(state_dir)
    os.chdir(root)
    try:
        yield root
    finally:
        os.chdir(prev_cwd)
        if prev_state is None:
            os.environ.pop("UMH_STATE_DIR", None)
        else:
            os.environ["UMH_STATE_DIR"] = prev_state


def pytest_configure(config):
    """Register the isolation marker used by the live-access regression tests."""
    config.addinivalue_line(
        "markers",
        "live_state_isolated: test asserts behaviour of the Group A runtime-state isolation seam",
    )


__all__ = ["IsolationSetupError"]
