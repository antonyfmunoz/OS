"""Test-only pytest plugin: prove a CHILD process inherits the isolated root.

Loaded explicitly with ``-p tests.subprocess_probe_plugin`` by the isolation
regression suite; never active during a normal run.

The isolation fixture exports ``UMH_STATE_DIR``/``UMH_ROOT`` into ``os.environ``
rather than confining them to a pytest-local monkeypatch, specifically so that
subprocesses spawned by a test inherit the isolated root. That property cannot
be observed from the parent alone — it requires actually spawning a child and
asking what it sees.

Timing is load-bearing. The probe MUST run while the autouse fixture is still
active: at ``pytest_sessionfinish`` the fixture has already torn down and
restored the environment, so a child spawned there reports ``UNSET`` and the
probe would report a false negative. (That is not hypothetical — the first
version of this plugin used ``sessionfinish`` and did exactly that.) Hooking
``pytest_runtest_call`` keeps the observation inside the fixture's window.

Only the FIRST test spawns a child, so the probe cannot become a per-test cost
on a file with hundreds of tests. Output is written on its own line via the
terminal writer so it cannot be appended to pytest's progress line, where a
``startswith`` scan would miss it.
"""

from __future__ import annotations

import os
import subprocess
import sys

_PROBE_TIMEOUT = 60
_done = False


def _emit(config, text: str) -> None:
    """Write a marker on its own line, surviving pytest's progress output."""
    reporter = config.pluginmanager.get_plugin("terminalreporter")
    if reporter is not None:
        reporter.write_line(text)
    else:  # pragma: no cover — terminal reporter is always present under -q
        print("\n" + text)


def pytest_runtest_call(item):  # pragma: no cover — exercised via subprocess
    """Spawn one child WHILE the isolation fixture is active and report its root."""
    global _done
    if _done:
        return
    _done = True
    try:
        out = subprocess.run(
            [sys.executable, "-c", 'import os;print(os.environ.get("UMH_STATE_DIR","UNSET"))'],
            capture_output=True,
            text=True,
            timeout=_PROBE_TIMEOUT,
            cwd=os.getcwd(),
        ).stdout.strip()
    except Exception as exc:  # noqa: BLE001 — a probe must never break the run
        out = f"ERROR:{type(exc).__name__}:{exc}"
    _emit(item.config, f"CHILD_STATE_DIR={out}")
