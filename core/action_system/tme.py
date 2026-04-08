"""Optional Tool Mastery Engine integration for the Control Plane.

Before execution, callers can ask: "is there a relevant skill for this?"
We shell out to scripts/query_skills.py so the Control Plane stays loosely
coupled to the TME internals.
"""

from __future__ import annotations

import subprocess

QUERY_SKILLS_CLI = "/opt/OS/scripts/query_skills.py"


def query_relevant_skills(term: str, *, timeout: int = 10) -> dict:
    """Run `query_skills.py search <term>` and return a dict with the raw output.

    Never raises — TME is advisory, not load-bearing for Control Plane v1.
    """
    try:
        proc = subprocess.run(
            ["python3", QUERY_SKILLS_CLI, "search", term],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return {
            "ok": proc.returncode == 0,
            "returncode": proc.returncode,
            "stdout": proc.stdout.strip(),
            "stderr": proc.stderr.strip(),
        }
    except FileNotFoundError:
        return {"ok": False, "error": f"{QUERY_SKILLS_CLI} not found"}
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": f"query_skills timed out after {timeout}s"}
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}
