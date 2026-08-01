"""Bounded reachability preflight for tests that require a LIVE HTTP service.

Why this exists
---------------
``tests/test_stage1_acceptance_e2e.py`` is a genuine integration suite: its
docstring states it "hits the LIVE runtime at localhost:8091 — no mocks", and
that is the intended contract, not an accident. The defect is not that it uses
HTTP; it is how it behaves when the service is ABSENT.

The measured failure mode was NOT a single unbounded call. Each request already
carries ``timeout=10`` and catches every exception, so no individual call can
hang. What actually happens is accumulation: the file makes ~35 HTTP calls, and
with the service down every one burns its full 10s budget before returning a
``(0, error)`` tuple that the test then asserts against. 35 x 10s = ~350s, which
is why the file reproducibly exceeded a 300s bound at BOTH the candidate and the
accepted baseline while every other Group A file finished.

Redirecting ``UMH_STATE_DIR``/cwd does not help — the dependency is an external
service, not the runtime store. That is why this file is separate from
``tests/runtime_isolation.py``: different root cause, different correction.

The correction
--------------
One bounded preflight per session. A single short-timeout probe decides whether
the service is reachable; if it is not, the suite SKIPS with an explicit reason
instead of spending ~350s discovering the same fact 35 times over.

Deliberate properties:

* **Bounded** — the probe uses a short explicit timeout and runs once.
* **Deterministic** — reachable or not; no partial/flaky third state.
* **Named** — the skip reason states exactly which endpoint was unreachable, so
  an absent service can never be mistaken for a passing suite.
* **Narrow** — only this module's probe is affected. There is NO global network
  suppression: any other test that makes a real network call still does so, so
  this cannot mask unrelated defects.
* **Test-only** — no production module is imported, modified, or monkeypatched.

When the service IS up, the suite runs exactly as before against the real
runtime — the integration contract is preserved, not replaced by a mock.
"""

from __future__ import annotations

import os
import urllib.error
import urllib.request

# Deliberately short: this is a liveness probe, not a data fetch. A service that
# cannot answer a health endpoint within this budget is "absent" for the purpose
# of an integration suite, and waiting longer only multiplies the stall the
# preflight exists to prevent.
PROBE_TIMEOUT_SECONDS = 3.0


def probe_http(url: str, *, timeout: float = PROBE_TIMEOUT_SECONDS) -> tuple[bool, str]:
    """Return ``(reachable, detail)`` for one bounded GET.

    Never raises: a probe that blew up would reintroduce the failure mode it is
    meant to bound. Any HTTP status counts as reachable — a 404 still proves a
    server answered, which is what the preflight is deciding.
    """
    req = urllib.request.Request(url, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return True, f"HTTP {resp.status}"
    except urllib.error.HTTPError as exc:
        return True, f"HTTP {exc.code}"
    except Exception as exc:  # noqa: BLE001 — any transport failure means absent
        return False, f"{type(exc).__name__}: {exc}"


def require_live_service(base_url: str, path: str = "/health") -> str | None:
    """Return a skip reason when the service is absent, else ``None``.

    Callers use the return value with ``pytest.skip`` so the absence is reported
    explicitly rather than silently swallowed.
    """
    url = f"{base_url.rstrip('/')}{path}"
    reachable, detail = probe_http(url)
    if reachable:
        return None
    return (
        f"live service required by this integration suite is unreachable at {url} "
        f"({detail}); skipped after one {PROBE_TIMEOUT_SECONDS}s bounded probe rather than "
        f"spending ~10s per request across every test in the file"
    )


def service_base_url() -> str:
    """The base URL this suite targets (env-overridable, same default as the suite)."""
    return os.environ.get("UMH_COCKPIT_URL", "http://localhost:8091")
