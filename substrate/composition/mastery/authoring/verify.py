"""Run verify_tool_skill.py against an authored tool.

We shell out to the canonical verifier rather than reimplementing
its logic. The Author Agent's output is NEVER trusted on its own
word — the verifier is the ground truth for READY status.
"""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass, field

from .paths import VERIFY_SCRIPT


@dataclass
class VerifyReport:
    slug: str
    passed: bool
    failures: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    error: str | None = None


def verify_skill(tool_slug: str) -> VerifyReport:
    """Run verify_tool_skill.py --skill <slug> --json and parse the result."""
    if not VERIFY_SCRIPT.is_file():
        return VerifyReport(
            slug=tool_slug,
            passed=False,
            error=f"verify script missing at {VERIFY_SCRIPT}",
        )
    try:
        proc = subprocess.run(
            ["python3", str(VERIFY_SCRIPT), "--skill", tool_slug, "--json"],
            capture_output=True,
            text=True,
            timeout=30,
        )
    except subprocess.TimeoutExpired:
        return VerifyReport(slug=tool_slug, passed=False, error="verify timed out")
    except Exception as e:  # defensive
        return VerifyReport(
            slug=tool_slug, passed=False, error=f"verify error: {type(e).__name__}: {e}"
        )

    # Exit 2 = bad invocation (no such skill). Exit 1 = failures.
    if proc.returncode == 2:
        return VerifyReport(
            slug=tool_slug,
            passed=False,
            error=f"verifier rejected invocation: {proc.stderr.strip()}",
        )

    try:
        payload = json.loads(proc.stdout)
    except json.JSONDecodeError as e:
        return VerifyReport(
            slug=tool_slug,
            passed=False,
            error=f"verifier output not JSON: {e}; stdout={proc.stdout[:200]!r}",
        )

    results = payload.get("results") or []
    if not results:
        return VerifyReport(
            slug=tool_slug, passed=False, error="verifier returned no results"
        )
    row = results[0]
    return VerifyReport(
        slug=tool_slug,
        passed=bool(row.get("passed")),
        failures=list(row.get("failures") or []),
        warnings=list(row.get("warnings") or []),
    )
