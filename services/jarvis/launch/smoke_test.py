#!/usr/bin/env python3
"""Jarvis smoke test — verifies all integration points are operational.

Checks:
  1. Backend health endpoint
  2. Signal submission endpoint
  3. Trace retrieval endpoint
  4. Resume state endpoint
  5. Global awareness endpoint
  6. Capabilities / routing config endpoint
  7. Frontend dev server (if running)
  8. Port 8091 untouched verification
  9. Port 8092 status
  10. Model routing config validity

Usage:
  python3 services/jarvis/launch/smoke_test.py
"""

from __future__ import annotations

import json
import pathlib
import sys
import time
import urllib.request
import urllib.error
from typing import Any

BACKEND = "http://localhost:8093"
FRONTEND = "http://localhost:5173"
OPERATOR = "http://localhost:8091"
OPERATOR_UI = "http://localhost:8092"


class SmokeTestResult:
    def __init__(self, name: str) -> None:
        self.name = name
        self.passed = False
        self.error: str | None = None
        self.data: Any = None
        self.duration_ms: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "passed": self.passed,
            "error": self.error,
            "duration_ms": self.duration_ms,
        }


def _get(url: str, timeout: float = 5.0) -> tuple[int, Any]:
    """HTTP GET returning (status_code, parsed_json_or_text)."""
    req = urllib.request.Request(url, method="GET")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        body = resp.read().decode("utf-8", errors="replace")
        try:
            return resp.status, json.loads(body)
        except json.JSONDecodeError:
            return resp.status, body


def _post(url: str, data: dict[str, Any], timeout: float = 5.0) -> tuple[int, Any]:
    """HTTP POST with JSON body."""
    payload = json.dumps(data).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        body = resp.read().decode("utf-8", errors="replace")
        try:
            return resp.status, json.loads(body)
        except json.JSONDecodeError:
            return resp.status, body


def test_backend_health() -> SmokeTestResult:
    r = SmokeTestResult("backend_health")
    start = time.monotonic()
    try:
        code, data = _get(f"{BACKEND}/api/jarvis/health")
        r.duration_ms = int((time.monotonic() - start) * 1000)
        r.data = data
        if code == 200 and isinstance(data, dict) and data.get("status") == "ok":
            r.passed = True
        else:
            r.error = f"Unexpected response: code={code}"
    except Exception as e:
        r.duration_ms = int((time.monotonic() - start) * 1000)
        r.error = str(e)
    return r


def test_signal_endpoint() -> SmokeTestResult:
    r = SmokeTestResult("signal_endpoint")
    start = time.monotonic()
    try:
        code, data = _post(
            f"{BACKEND}/api/jarvis/signal",
            {"content": "smoke_test_signal", "source": "smoke_test", "risk_level": "read_only"},
        )
        r.duration_ms = int((time.monotonic() - start) * 1000)
        r.data = data
        if code == 200 and isinstance(data, dict) and "trace_id" in data:
            r.passed = True
        else:
            r.error = f"Unexpected response: code={code}"
    except Exception as e:
        r.duration_ms = int((time.monotonic() - start) * 1000)
        r.error = str(e)
    return r


def test_trace_endpoint() -> SmokeTestResult:
    r = SmokeTestResult("trace_endpoint")
    start = time.monotonic()
    try:
        code, data = _get(f"{BACKEND}/api/jarvis/traces?limit=5")
        r.duration_ms = int((time.monotonic() - start) * 1000)
        r.data = data
        if code == 200 and isinstance(data, list):
            r.passed = True
        else:
            r.error = f"Unexpected response: code={code}, type={type(data).__name__}"
    except Exception as e:
        r.duration_ms = int((time.monotonic() - start) * 1000)
        r.error = str(e)
    return r


def test_resume_endpoint() -> SmokeTestResult:
    r = SmokeTestResult("resume_endpoint")
    start = time.monotonic()
    try:
        code, data = _get(f"{BACKEND}/api/jarvis/resume")
        r.duration_ms = int((time.monotonic() - start) * 1000)
        r.data = data
        if code == 200 and isinstance(data, dict):
            r.passed = True
        else:
            r.error = f"Unexpected response: code={code}"
    except Exception as e:
        r.duration_ms = int((time.monotonic() - start) * 1000)
        r.error = str(e)
    return r


def test_awareness_endpoint() -> SmokeTestResult:
    r = SmokeTestResult("awareness_endpoint")
    start = time.monotonic()
    try:
        code, data = _get(f"{BACKEND}/api/jarvis/awareness")
        r.duration_ms = int((time.monotonic() - start) * 1000)
        r.data = data
        if code == 200 and isinstance(data, dict) and "pipeline_active" in data:
            r.passed = True
        else:
            r.error = f"Unexpected response: code={code}"
    except Exception as e:
        r.duration_ms = int((time.monotonic() - start) * 1000)
        r.error = str(e)
    return r


def test_capabilities_endpoint() -> SmokeTestResult:
    r = SmokeTestResult("capabilities_endpoint")
    start = time.monotonic()
    try:
        code, data = _get(f"{BACKEND}/api/jarvis/capabilities")
        r.duration_ms = int((time.monotonic() - start) * 1000)
        r.data = data
        if code == 200 and isinstance(data, dict) and len(data) > 0:
            r.passed = True
        else:
            r.error = f"Unexpected response: code={code}"
    except Exception as e:
        r.duration_ms = int((time.monotonic() - start) * 1000)
        r.error = str(e)
    return r


def test_frontend_reachable() -> SmokeTestResult:
    r = SmokeTestResult("frontend_reachable")
    start = time.monotonic()
    try:
        code, data = _get(FRONTEND)
        r.duration_ms = int((time.monotonic() - start) * 1000)
        if code == 200:
            r.passed = True
        else:
            r.error = f"code={code}"
    except Exception as e:
        r.duration_ms = int((time.monotonic() - start) * 1000)
        r.error = f"Frontend not reachable (may be on Windows): {e}"
    return r


def test_port_8091_untouched() -> SmokeTestResult:
    r = SmokeTestResult("port_8091_untouched")
    start = time.monotonic()
    try:
        code, data = _get(f"{OPERATOR}/health")
        r.duration_ms = int((time.monotonic() - start) * 1000)
        if code == 200:
            r.passed = True
            r.data = "Operator API still running on 8091"
        else:
            r.error = f"Operator API returned code={code}"
    except Exception as e:
        r.duration_ms = int((time.monotonic() - start) * 1000)
        r.error = f"Operator API not reachable: {e}"
        r.passed = False
    return r


def test_port_8092_status() -> SmokeTestResult:
    r = SmokeTestResult("port_8092_status")
    start = time.monotonic()
    try:
        code, _ = _get(OPERATOR_UI)
        r.duration_ms = int((time.monotonic() - start) * 1000)
        r.passed = True
        r.data = f"Operator UI on 8092: code={code}"
    except Exception as e:
        r.duration_ms = int((time.monotonic() - start) * 1000)
        r.passed = True
        r.data = f"Operator UI on 8092 not reachable (expected if three-fronts worktree down): {e}"
    return r


def test_routing_config() -> SmokeTestResult:
    r = SmokeTestResult("routing_config_valid")
    start = time.monotonic()
    try:
        repo_root = str(pathlib.Path(__file__).resolve().parent.parent.parent.parent)
        if repo_root not in sys.path:
            sys.path.insert(0, repo_root)
        from services.jarvis.model_routing.capabilities import (
            CapabilityClass,
            CAPABILITY_REGISTRY,
        )
        from services.jarvis.model_routing.config import load_routing_config

        config = load_routing_config()
        desc = config.describe()
        r.duration_ms = int((time.monotonic() - start) * 1000)

        expected = 12
        actual = len(desc)
        if actual == expected:
            r.passed = True
            r.data = {
                "capability_count": actual,
                "local_first": config.local_capabilities(),
                "cloud_only": config.cloud_capabilities(),
            }
        else:
            r.error = f"Expected {expected} capabilities, got {actual}"
    except Exception as e:
        r.duration_ms = int((time.monotonic() - start) * 1000)
        r.error = str(e)
    return r


def run_all() -> dict[str, Any]:
    """Run all smoke tests and return summary."""
    tests = [
        test_backend_health,
        test_signal_endpoint,
        test_trace_endpoint,
        test_resume_endpoint,
        test_awareness_endpoint,
        test_capabilities_endpoint,
        test_frontend_reachable,
        test_port_8091_untouched,
        test_port_8092_status,
        test_routing_config,
    ]

    results = []
    for test_fn in tests:
        result = test_fn()
        results.append(result)
        status = "PASS" if result.passed else "FAIL"
        print(f"  [{status}] {result.name} ({result.duration_ms}ms)")
        if result.error and not result.passed:
            print(f"         {result.error}")

    passed = sum(1 for r in results if r.passed)
    failed = sum(1 for r in results if not r.passed)
    total = len(results)

    summary = {
        "timestamp": int(time.time()),
        "total": total,
        "passed": passed,
        "failed": failed,
        "all_passed": failed == 0,
        "results": [r.to_dict() for r in results],
    }

    print(f"\n  {'ALL PASSED' if failed == 0 else f'{failed} FAILED'} ({passed}/{total})")
    return summary


if __name__ == "__main__":
    print("\nJarvis Integration Smoke Test")
    print("=" * 40)
    summary = run_all()
    sys.exit(0 if summary["all_passed"] else 1)
