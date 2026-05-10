"""Session Orchestration Layer v1 — registry, health, recovery, reporting.

Bounded orchestration that knows which sessions should exist, whether they
are healthy, and how to explicitly recover them. No background processes, no autonomous
supervision, no hot-path imports.
"""

from __future__ import annotations

import datetime
import os
import sys
from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any

LAYER_NAME = "session_orchestration"
LAYER_VERSION = "v1"

__all__ = [
    "ExpectedSession",
    "SessionHealth",
    "actual_sessions",
    "ensure_expected_sessions",
    "expected_sessions",
    "reconcile_sessions",
    "recover_session",
    "session_health",
    "session_readiness_report",
]


def _now_iso() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def _log(msg: str) -> None:
    print(f"[substrate.session_orchestration] {msg}", file=sys.stderr)


# ---------------------------------------------------------------------------
# 1. Expected Session Registry
# ---------------------------------------------------------------------------

_ENV_EXTRA_SESSIONS = "EOS_EXTRA_EXPECTED_SESSIONS"


@dataclass(frozen=True)
class ExpectedSession:
    """A session that should exist in the EOS topology."""

    session_name: str
    target: str  # "vps" or "local"
    mode: str  # "builder", "product", etc.
    role: str  # human-readable purpose
    working_dir: str = "/opt/OS"


_DEFAULT_SESSIONS: list[ExpectedSession] = [
    ExpectedSession("dex_builder_main", "vps", "builder", "development"),
    ExpectedSession("dex_product_main", "vps", "product", "user-facing runtime"),
]


def expected_sessions() -> list[ExpectedSession]:
    """Return the expected session topology.

    Includes the two default sessions plus any additional entries from the
    ``EOS_EXTRA_EXPECTED_SESSIONS`` environment variable.

    Env format: ``"name:target:mode:role,name2:target2:mode2:role2"``
    Each entry must have exactly four colon-separated fields. Malformed
    entries are silently skipped.
    """
    result = list(_DEFAULT_SESSIONS)
    raw = os.getenv(_ENV_EXTRA_SESSIONS, "").strip()
    if raw:
        for entry in raw.split(","):
            parts = entry.strip().split(":")
            if len(parts) == 4:
                result.append(
                    ExpectedSession(
                        session_name=parts[0].strip(),
                        target=parts[1].strip(),
                        mode=parts[2].strip(),
                        role=parts[3].strip(),
                    )
                )
            else:
                _log(f"skipping malformed extra session entry: {entry!r}")
    return result


# ---------------------------------------------------------------------------
# 2. Actual Session State
# ---------------------------------------------------------------------------


def actual_sessions(target: str = "vps") -> list[dict[str, Any]]:
    """List actual ``dex_*`` tmux sessions via claude_session_bridge.

    Returns the ``sessions`` list from ``list_sessions`` (only dex-prefixed
    sessions). On import or call failure returns an empty list.
    """
    try:
        from eos_ai.substrate.claude_session_bridge import list_sessions
    except Exception as exc:  # noqa: BLE001
        _log(f"import list_sessions failed: {exc}")
        return []

    try:
        result = list_sessions(target)
        return result.get("sessions", [])
    except Exception as exc:  # noqa: BLE001
        _log(f"list_sessions call failed: {exc}")
        return []


# ---------------------------------------------------------------------------
# 3. Health Check
# ---------------------------------------------------------------------------


class SessionHealth(str, Enum):
    """Health state of a single session."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    MISSING = "missing"


_STATUS_TO_HEALTH: dict[str, SessionHealth] = {
    "running": SessionHealth.HEALTHY,
    "degraded": SessionHealth.DEGRADED,
    "missing": SessionHealth.MISSING,
}


def session_health(target: str, session_name: str) -> dict[str, Any]:
    """Check health of a single session.

    Returns a dict with keys: ``session_name``, ``target``, ``health``,
    ``status``, ``checked_at``, ``detail``. Never raises.
    """
    checked_at = _now_iso()
    try:
        from eos_ai.substrate.claude_session_bridge import session_status
    except Exception as exc:  # noqa: BLE001
        return {
            "session_name": session_name,
            "target": target,
            "health": SessionHealth.MISSING.value,
            "status": "import_failed",
            "checked_at": checked_at,
            "detail": str(exc),
        }

    try:
        info = session_status(target, session_name)
    except Exception as exc:  # noqa: BLE001
        return {
            "session_name": session_name,
            "target": target,
            "health": SessionHealth.MISSING.value,
            "status": "call_failed",
            "checked_at": checked_at,
            "detail": str(exc),
        }

    raw_status = info.get("status", "missing")
    health = _STATUS_TO_HEALTH.get(raw_status, SessionHealth.MISSING)
    return {
        "session_name": session_name,
        "target": target,
        "health": health.value,
        "status": raw_status,
        "checked_at": checked_at,
        "detail": info.get("detail"),
    }


def session_readiness_report() -> dict[str, Any]:
    """Full health report across all expected sessions.

    Returns a dict with keys: ``checked_at``, ``expected_count``,
    ``healthy_count``, ``degraded_count``, ``missing_count``, ``sessions``,
    ``overall``.

    ``overall`` is ``"ready"`` if all healthy, ``"degraded"`` if any
    degraded but none missing, ``"incomplete"`` if any missing.
    """
    checked_at = _now_iso()
    sessions: list[dict[str, Any]] = []
    healthy = degraded = missing = 0

    for es in expected_sessions():
        h = session_health(es.target, es.session_name)
        sessions.append(h)
        if h["health"] == SessionHealth.HEALTHY.value:
            healthy += 1
        elif h["health"] == SessionHealth.DEGRADED.value:
            degraded += 1
        else:
            missing += 1

    if missing > 0:
        overall = "incomplete"
    elif degraded > 0:
        overall = "degraded"
    else:
        overall = "ready"

    return {
        "checked_at": checked_at,
        "expected_count": len(sessions),
        "healthy_count": healthy,
        "degraded_count": degraded,
        "missing_count": missing,
        "sessions": sessions,
        "overall": overall,
    }


# ---------------------------------------------------------------------------
# 4. Recovery
# ---------------------------------------------------------------------------


def ensure_expected_sessions() -> dict[str, Any]:
    """Ensure all expected sessions exist. Idempotent.

    Returns a dict with key ``ensured`` — a list of per-session result dicts
    each containing ``session_name``, ``target``, ``action``, and ``detail``.

    Possible ``action`` values: ``"created"``, ``"already_exists"``,
    ``"failed"``.
    """
    try:
        from eos_ai.substrate.claude_session_bridge import ensure_session
    except Exception as exc:  # noqa: BLE001
        _log(f"import ensure_session failed: {exc}")
        return {
            "ensured": [
                {
                    "session_name": es.session_name,
                    "target": es.target,
                    "action": "failed",
                    "detail": f"import error: {exc}",
                }
                for es in expected_sessions()
            ]
        }

    results: list[dict[str, Any]] = []
    for es in expected_sessions():
        try:
            resp = ensure_session(
                es.target,
                es.session_name,
                working_dir=es.working_dir,
                launch_claude=True,
            )
            created = resp.get("created", False)
            action = "created" if created else "already_exists"
            detail = resp.get("detail") or resp.get("status", "ok")
            results.append(
                {
                    "session_name": es.session_name,
                    "target": es.target,
                    "action": action,
                    "detail": detail,
                }
            )
        except Exception as exc:  # noqa: BLE001
            results.append(
                {
                    "session_name": es.session_name,
                    "target": es.target,
                    "action": "failed",
                    "detail": str(exc),
                }
            )

    return {"ensured": results}


def recover_session(
    target: str,
    session_name: str,
    *,
    strategy: str = "recreate",
) -> dict[str, Any]:
    """Recover a specific session.

    Strategies:
      - ``"recreate"``: kill and recreate via ``session_control.reset_session``
      - ``"ensure"``: just ensure exists via ``ensure_session``

    Returns a dict with keys: ``session_name``, ``target``, ``strategy``,
    ``ok``, ``detail``.
    """
    base = {
        "session_name": session_name,
        "target": target,
        "strategy": strategy,
    }

    if strategy == "recreate":
        try:
            from eos_ai.substrate.session_control import reset_session
        except Exception as exc:  # noqa: BLE001
            return {**base, "ok": False, "detail": f"import error: {exc}"}
        try:
            resp = reset_session(target, session_name)
            return {
                **base,
                "ok": resp.get("ok", False),
                "detail": resp.get("detail", str(resp)),
            }
        except Exception as exc:  # noqa: BLE001
            return {**base, "ok": False, "detail": str(exc)}

    elif strategy == "ensure":
        try:
            from eos_ai.substrate.claude_session_bridge import ensure_session
        except Exception as exc:  # noqa: BLE001
            return {**base, "ok": False, "detail": f"import error: {exc}"}
        try:
            resp = ensure_session(target, session_name, launch_claude=True)
            return {
                **base,
                "ok": resp.get("ok", False),
                "detail": resp.get("detail", str(resp)),
            }
        except Exception as exc:  # noqa: BLE001
            return {**base, "ok": False, "detail": str(exc)}

    else:
        return {**base, "ok": False, "detail": f"unknown strategy: {strategy!r}"}


# ---------------------------------------------------------------------------
# 5. Reconciliation
# ---------------------------------------------------------------------------


def reconcile_sessions() -> dict[str, Any]:
    """Compare expected vs actual and return a reconciliation report.

    Returns a dict with keys: ``expected``, ``actual``, ``matched``,
    ``unexpected``, ``missing``, ``recommendations``.
    """
    exp = expected_sessions()
    exp_names = {es.session_name for es in exp}

    all_actual = actual_sessions("vps")
    actual_names = {s.get("session_name", "") for s in all_actual}

    matched = sorted(exp_names & actual_names)
    missing = sorted(exp_names - actual_names)
    unexpected = sorted(actual_names - exp_names)

    recommendations: list[str] = []
    for name in missing:
        recommendations.append(
            f"Session '{name}' is expected but missing — run ensure_expected_sessions() or recover_session()."
        )
    for name in unexpected:
        recommendations.append(
            f"Session '{name}' exists but is not in the expected registry — verify if it should be added or removed."
        )

    return {
        "expected": [asdict(es) for es in exp],
        "actual": all_actual,
        "matched": matched,
        "unexpected": unexpected,
        "missing": missing,
        "recommendations": recommendations,
    }


# ---------------------------------------------------------------------------
# Self-test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    sys.path.insert(0, "/opt/OS")
    print("=== Session Orchestration Self-Test ===")
    print(f"Layer: {LAYER_NAME} {LAYER_VERSION}")
    print()

    print("Expected sessions:")
    for es in expected_sessions():
        print(f"  {es.session_name} target={es.target} mode={es.mode} role={es.role}")
    print()

    print("Readiness report:")
    report = session_readiness_report()
    print(f"  overall: {report['overall']}")
    print(
        f"  expected={report['expected_count']} healthy={report['healthy_count']} "
        f"degraded={report['degraded_count']} missing={report['missing_count']}"
    )
    for s in report["sessions"]:
        print(f"  {s['session_name']}: {s['health']} (status={s['status']})")
    print()

    print("Reconciliation:")
    recon = reconcile_sessions()
    print(
        f"  matched={recon['matched']} missing={recon['missing']} unexpected={recon['unexpected']}"
    )
    for r in recon["recommendations"]:
        print(f"  -> {r}")
    print()
    print("Self-test complete.")
