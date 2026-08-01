"""Test-only pytest plugin: observe cwd isolation and its restoration.

Loaded explicitly with ``-p tests.cwd_probe_plugin``; never active in a normal run.

Two properties of the isolation seam cannot be observed from the parent process,
because both concern the working directory *inside* a Group A test session:

* **Isolation** — cwd must move into the isolated root while a test runs. This is
  the only mechanism that redirects the relative ``Path("data/runtime/...")``
  literals that bypass ``runtime_state_path()`` entirely.
* **Restoration** — cwd must return to the starting directory at teardown.
  pytest reaps its tmp dirs, so a leaked cwd leaves later tests executing inside
  a deleted directory, producing failures far away from the real cause.

Both were genuine mutation SURVIVORS before this plugin existed: dropping
``os.chdir(root)`` and dropping ``os.chdir(prev_cwd)`` each left the suite fully
green, because nothing was actually watching cwd. The markers below are what
make those two mutants die.

``DURING`` markers are emitted from the first test only (cheap on large files);
``FINAL`` markers are emitted once at session finish, after teardown has run.
"""

from __future__ import annotations

import os
from pathlib import Path

_done = False
_start_cwd = os.getcwd()


def _emit(config, text: str) -> None:
    """Write a marker on its own line, surviving pytest's progress output."""
    reporter = config.pluginmanager.get_plugin("terminalreporter")
    if reporter is not None:
        reporter.write_line(text)
    else:  # pragma: no cover — terminal reporter is always present under -q
        print("\n" + text)


def pytest_runtest_call(item):  # pragma: no cover — exercised via subprocess
    """Record cwd and a relative runtime path WHILE the fixture is active."""
    global _done
    if _done:
        return
    _done = True
    cwd = os.getcwd()
    _emit(item.config, f"TEST_CWD={cwd}")
    # Exactly what compute_fabric_runtime.py / distributed_runtime.py build.
    _emit(item.config, f"RELATIVE_RUNTIME={Path('data/runtime/mesh_nodes.json').resolve()}")


def pytest_unconfigure(config):  # pragma: no cover — exercised via subprocess
    """Record cwd and UMH_STATE_DIR AFTER teardown, proving restoration.

    Deliberately ``unconfigure`` rather than ``sessionfinish``: by the time the
    terminal reporter has finished its summary it no longer flushes new lines, so
    markers written at sessionfinish never reach stdout. (Observed directly — the
    first version of this plugin emitted there and the reader saw nothing.)
    Printing here is late enough that teardown has run and early enough that the
    output still lands.
    """
    print(f"FINAL_CWD={os.getcwd()}")
    print(f"FINAL_STATE_DIR={os.environ.get('UMH_STATE_DIR', 'UNSET')}")
