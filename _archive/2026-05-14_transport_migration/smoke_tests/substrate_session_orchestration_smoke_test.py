#!/usr/bin/env python3
"""Session Orchestration Smoke Tests."""

from __future__ import annotations

import ast
import sys

import os
sys.path.insert(0, os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS")

from runtime.transport.session_orchestration import (
    LAYER_NAME,
    LAYER_VERSION,
    ExpectedSession,
    SessionHealth,
    actual_sessions,
    ensure_expected_sessions,
    expected_sessions,
    reconcile_sessions,
    recover_session,
    session_health,
    session_readiness_report,
)

FAILURES: list[str] = []


def check(name: str, cond: bool, detail: str = "") -> None:
    if cond:
        print(f"  [PASS] {name}")
    else:
        FAILURES.append(name)
        print(f"  [FAIL] {name}  {detail}")


# ------------------------------------------------------------------
# Section 1: Registry Tests
# ------------------------------------------------------------------
def test_registry() -> int:
    print("\n--- Registry Tests ---")
    passed = 0

    # 1. expected_topology_includes_builder_product
    sessions = expected_sessions()
    names = [s.session_name for s in sessions]
    has_builder = "dex_builder_main" in names
    has_product = "dex_product_main" in names
    check(
        "expected_topology_includes_builder_product",
        has_builder and has_product,
        f"names={names}",
    )
    if has_builder and has_product:
        passed += 1

    # 2. expected_sessions_are_frozen
    ok = True
    detail = ""
    for s in sessions:
        if not isinstance(s, ExpectedSession):
            ok = False
            detail = f"not ExpectedSession: {type(s)}"
            break
        for attr in ("session_name", "target", "mode", "role"):
            if not hasattr(s, attr):
                ok = False
                detail = f"missing attr {attr}"
                break
        # frozen check
        try:
            object.__setattr__(s, "session_name", "hacked")
            # If we get here on a frozen dataclass, __setattr__ was overridden
            # but object.__setattr__ bypasses it. Check via direct assignment.
        except Exception:
            pass
        try:
            s.session_name = "hacked"  # type: ignore[misc]
            ok = False
            detail = "dataclass is not frozen"
        except AttributeError:
            pass  # expected for frozen
        except Exception:
            pass  # also fine
    check("expected_sessions_are_frozen", ok, detail)
    if ok:
        passed += 1

    # 3. actual_session_listing_works
    # actual_sessions() returns a list of session dicts (not a dict with "ok")
    result = actual_sessions("vps")
    is_list = isinstance(result, list)
    check(
        "actual_session_listing_works",
        is_list,
        f"type={type(result)}",
    )
    if is_list:
        passed += 1

    return passed


# ------------------------------------------------------------------
# Section 2: Health Tests
# ------------------------------------------------------------------
def test_health() -> int:
    print("\n--- Health Tests ---")
    passed = 0

    # 4. missing_session_classified_correctly
    # Use a name that definitely doesn't exist as a tmux session.
    # Clean up first in case a prior run left it behind.
    import subprocess

    _probe_name = "dex_orch_smoke_probe_missing"
    subprocess.run(
        ["tmux", "kill-session", "-t", _probe_name],
        capture_output=True,
        timeout=5,
    )
    result = session_health("vps", _probe_name)
    health_val = result.get("health", "")
    is_missing = health_val == SessionHealth.MISSING or health_val == "missing"
    check("missing_session_classified_correctly", is_missing, f"health={health_val}")
    if is_missing:
        passed += 1

    # 5. health_report_structure
    report = session_readiness_report()
    required_keys = {
        "checked_at",
        "expected_count",
        "healthy_count",
        "degraded_count",
        "missing_count",
        "sessions",
        "overall",
    }
    has_all = isinstance(report, dict) and required_keys.issubset(report.keys())
    check(
        "health_report_structure",
        has_all,
        f"missing={required_keys - set(report.keys()) if isinstance(report, dict) else 'not a dict'}",
    )
    if has_all:
        passed += 1

    # 6. health_never_raises
    ok = True
    try:
        session_health("", "")
        session_health("garbage_target", "garbage_session")
        session_health("vps", "")
    except Exception as exc:
        ok = False
        check("health_never_raises", False, str(exc))
    if ok:
        check("health_never_raises", True)
        passed += 1

    return passed


# ------------------------------------------------------------------
# Section 3: Recovery Tests
# ------------------------------------------------------------------
def test_recovery() -> int:
    print("\n--- Recovery Tests ---")
    passed = 0

    # 7. ensure_returns_structured_result
    result = ensure_expected_sessions()
    has_ensured = isinstance(result, dict) and isinstance(result.get("ensured"), list)
    check(
        "ensure_returns_structured_result",
        has_ensured,
        f"keys={list(result.keys()) if isinstance(result, dict) else type(result)}",
    )
    if has_ensured:
        passed += 1

    # 8. recover_returns_structured_result
    import subprocess

    _recover_name = "dex_orch_smoke_recover_test"
    result = recover_session("vps", _recover_name, strategy="ensure")
    required_keys = {"session_name", "target", "strategy", "ok"}
    has_all = isinstance(result, dict) and required_keys.issubset(result.keys())
    check(
        "recover_returns_structured_result",
        has_all,
        f"keys={list(result.keys()) if isinstance(result, dict) else type(result)}",
    )
    if has_all:
        passed += 1
    # Clean up test session
    subprocess.run(
        ["tmux", "kill-session", "-t", _recover_name],
        capture_output=True,
        timeout=5,
    )

    return passed


# ------------------------------------------------------------------
# Section 4: Reconciliation Tests
# ------------------------------------------------------------------
def test_reconciliation() -> int:
    print("\n--- Reconciliation Tests ---")
    passed = 0

    # 9. reconcile_returns_structured_result
    result = reconcile_sessions()
    required_keys = {
        "expected",
        "actual",
        "matched",
        "unexpected",
        "missing",
        "recommendations",
    }
    has_all = isinstance(result, dict) and required_keys.issubset(result.keys())
    check(
        "reconcile_returns_structured_result",
        has_all,
        f"keys={list(result.keys()) if isinstance(result, dict) else type(result)}",
    )
    if has_all:
        passed += 1

    return passed


# ------------------------------------------------------------------
# Section 5: Architecture Tripwires
# ------------------------------------------------------------------
def test_architecture() -> int:
    print("\n--- Architecture Tripwires ---")
    passed = 0

    import runtime.transport.session_orchestration as mod

    src_path = mod.__file__
    assert src_path is not None
    source = open(src_path).read()

    # 10. no_hot_path_imports
    tree = ast.parse(source, filename=src_path)
    forbidden = {
        "gateway",
        "cognitive_loop",
        "model_router",
        "agent_runtime",
        "primitives",
    }
    violations: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                for f in forbidden:
                    if f in alias.name:
                        violations.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            mod_name = node.module or ""
            for f in forbidden:
                if f in mod_name:
                    violations.append(mod_name)
    check("no_hot_path_imports", len(violations) == 0, f"violations={violations}")
    if len(violations) == 0:
        passed += 1

    # 11. no_daemon_patterns
    # Strip docstrings and comments before checking for forbidden patterns
    # to avoid false positives from documentation.
    executable_lines: list[str] = []
    for line in source.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            continue
        executable_lines.append(line)
    # Remove triple-quoted docstrings from joined executable code
    import re

    exec_source = "\n".join(executable_lines)
    exec_source = re.sub(r'""".*?"""', "", exec_source, flags=re.DOTALL)
    exec_source = re.sub(r"'''.*?'''", "", exec_source, flags=re.DOTALL)

    daemon_patterns = [
        "daemon",
        "background_thread",
        "threading.Thread",
        "while True",
        "Thread(",
    ]
    found: list[str] = []
    for pat in daemon_patterns:
        if pat in exec_source:
            found.append(pat)
    check("no_daemon_patterns", len(found) == 0, f"found={found}")
    if len(found) == 0:
        passed += 1

    return passed


# ------------------------------------------------------------------
# Section 6: Integration Guard
# ------------------------------------------------------------------
def test_integration_guard() -> int:
    print("\n--- Integration Guard ---")
    passed = 0

    ok = True
    detail = ""
    try:
        from runtime.transport.session_control import clear_session, reset_session
        from runtime.transport.claude_session_bridge import list_sessions

        if not callable(clear_session):
            ok = False
            detail = "clear_session not callable"
        if not callable(reset_session):
            ok = False
            detail = "reset_session not callable"
        if not callable(list_sessions):
            ok = False
            detail = "list_sessions not callable"
    except ImportError as exc:
        ok = False
        detail = f"ImportError: {exc}"
    except Exception as exc:
        ok = False
        detail = f"Error: {exc}"

    check("existing_session_control_still_works", ok, detail)
    if ok:
        passed += 1

    return passed


# ------------------------------------------------------------------
# Main
# ------------------------------------------------------------------
if __name__ == "__main__":
    print(f"Session Orchestration Smoke Tests  (layer={LAYER_NAME} v={LAYER_VERSION})")
    print("=" * 60)

    passed = 0
    passed += test_registry()
    passed += test_health()
    passed += test_recovery()
    passed += test_reconciliation()
    passed += test_architecture()
    passed += test_integration_guard()

    print("=" * 60)
    total = passed + len(FAILURES)
    print(f"\n{passed}/{total} passed")
    if FAILURES:
        print("FAILED:")
        for f in FAILURES:
            print(f"  - {f}")
        sys.exit(1)
    else:
        print("ALL PASSED")
        sys.exit(0)
