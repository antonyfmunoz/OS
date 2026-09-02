"""Test-only pytest plugin: report what runtime state ACTUALLY resolves to.

Loaded explicitly with ``-p tests.isolation_probe_plugin`` by the isolation
regression suite. It is never active during a normal run.

Why a plugin rather than an assertion inside the target test: the property that
matters is what a REAL Group A test session resolves at runtime, from inside
that session, after the autouse fixture has applied. Asserting it from another
process — or from source text — would not prove the same thing, because the seam
could be inert and a text assertion would still pass.

Timing is load-bearing: the probe runs during ``pytest_runtest_call``, while the
fixture is active. At session finish the fixture has already restored the
environment, so the value observed there would describe teardown, not the run.

Only the FIRST test emits a marker, so a file with hundreds of tests does not
pay a per-test cost. The marker is written on its own line through the terminal
reporter so it cannot be appended to pytest's progress line, where a
``startswith`` scan would miss it.
"""

from __future__ import annotations

_done = False


def _emit(config, text: str) -> None:
    """Write a marker on its own line, surviving pytest's progress output."""
    reporter = config.pluginmanager.get_plugin("terminalreporter")
    if reporter is not None:
        reporter.write_line(text)
    else:  # pragma: no cover — terminal reporter is always present under -q
        print("\n" + text)


def pytest_runtest_call(item):  # pragma: no cover — exercised via subprocess
    """Emit the runtime-state root resolved while this test is running."""
    global _done
    if _done:
        return
    _done = True
    try:
        from substrate.state.runtime_paths import runtime_state_root

        _emit(item.config, f"RESOLVED_STATE_ROOT={runtime_state_root()}")
    except Exception as exc:  # noqa: BLE001 — a probe must never break the run
        _emit(item.config, f"RESOLVED_STATE_ROOT=ERROR:{type(exc).__name__}:{exc}")
