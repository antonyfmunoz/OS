"""BusinessOpsLoop — persistent loop for empire operations.

Composes:
  - Orchestrator signal drain (pending signals → workflow handlers)
  - Scheduled operations check (deadline monitor, DM replies, calendar sync)
  - Stale deferred action escalation

Each cycle is fully deterministic. AI calls happen inside workflow
handlers — not in the loop itself.

Interval: 5 minutes (300s) — matches the orchestrator default.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from substrate.execution.loop.persistent_loop import CycleReport, PersistentLoop

logger = logging.getLogger(__name__)


class BusinessOpsLoop(PersistentLoop):
    """Run empire operations: signal drain + scheduled checks."""

    def __init__(self, interval_seconds: int = 300) -> None:
        super().__init__(
            name="business_ops",
            domain="operations",
            interval_seconds=interval_seconds,
        )

    def run_cycle(self) -> CycleReport:
        t0 = datetime.now(timezone.utc)
        actions = 0
        errors = 0
        details: list[dict] = []

        # Phase 1: Drain pending signals via orchestrator
        try:
            from substrate.control_plane.runtime.orchestrator.loop import (
                LoopConfig,
                run_cycle as orchestrator_cycle,
            )

            orch_report = orchestrator_cycle(LoopConfig())
            actions += orch_report.signals_drained + orch_report.retries_attempted
            errors += orch_report.escalations
            details.append({
                "phase": "signal_drain",
                "signals_drained": orch_report.signals_drained,
                "workflows_triggered": orch_report.workflows_triggered,
                "stale_deferred": orch_report.stale_deferred,
                "failures_detected": orch_report.failures_detected,
            })
        except Exception as e:
            errors += 1
            details.append({"phase": "signal_drain", "error": str(e)})
            logger.warning(f"[business_ops] signal drain failed: {e}")

        # Phase 2: Check for actionable items (deterministic scans)
        try:
            scan_result = self._scan_actionable_items()
            actions += scan_result.get("items_found", 0)
            details.append({"phase": "actionable_scan", **scan_result})
        except Exception as e:
            errors += 1
            details.append({"phase": "actionable_scan", "error": str(e)})
            logger.warning(f"[business_ops] actionable scan failed: {e}")

        return CycleReport(
            loop_name=self.name,
            cycle_num=self._cycle_count,
            started_at=t0.isoformat(),
            finished_at=datetime.now(timezone.utc).isoformat(),
            actions_taken=actions,
            errors=errors,
            details=details,
        )

    def _scan_actionable_items(self) -> dict:
        """Deterministic scan for items needing attention.

        Checks:
        - Overdue tasks (deadline passed, not completed)
        - Unhandled DM replies
        - Stale open loops
        """
        items_found = 0
        findings: list[str] = []

        try:
            from substrate.state.storage.db import get_conn, ORG_ID
            conn = get_conn()
            if conn:
                cur = conn.cursor()

                # Overdue tasks
                cur.execute(
                    "SELECT COUNT(*) FROM tasks "
                    "WHERE org_id = %s AND status = 'active' "
                    "AND due_date < NOW()",
                    (ORG_ID,),
                )
                overdue = cur.fetchone()[0]
                if overdue:
                    items_found += overdue
                    findings.append(f"{overdue} overdue tasks")

                # Unhandled replies
                cur.execute(
                    "SELECT COUNT(*) FROM leads "
                    "WHERE org_id = %s AND replied = true AND status = 'new'",
                    (ORG_ID,),
                )
                replies = cur.fetchone()[0]
                if replies:
                    items_found += replies
                    findings.append(f"{replies} unhandled replies")

                conn.close()
        except Exception as e:
            logger.debug(f"[business_ops] DB scan skipped: {e}")

        return {"items_found": items_found, "findings": findings}
