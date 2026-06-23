"""C28 Certification Suite — Cockpit Supremacy / Meta IDE Daily Driver.

Orchestrates browser-driven certification on Beast (Windows workstation).
VPS triggers collection via SSH → Beast runs Playwright with real display →
Evidence flows back → VPS scores and generates certification report.

All acceptance testing is browser-driven through the live cockpit UI.
No direct API validation counts as operator readiness.

Usage (from VPS):
  python3 tests/certification/c28_certification.py --phase panel-audit
  python3 tests/certification/c28_certification.py --phase full
  python3 tests/certification/c28_certification.py --report-only
"""

from __future__ import annotations

import json
import logging
import os
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.path.insert(0, os.environ.get("UMH_ROOT", "/opt/OS"))

from substrate.execution.cpu_gate import gated_subprocess_run
from substrate.meta_ide.browser_evidence_collector import (
    trigger_collection,
    collect_local_logs,
)

logger = logging.getLogger(__name__)

_COCKPIT_URL = "https://universalmetaharness.tech"
_BEAST_SSH = os.environ.get("UMH_BEAST_SSH", "")
_CERT_DIR = Path(os.environ.get("UMH_ROOT", "/opt/OS")) / "data" / "certification" / "c28"
_COLLECTOR_SCRIPT = "C:\\dev\\dev\\OS\\scripts\\browser_gate_collector.py"


# ---------- data types ----------

@dataclass
class PanelAuditResult:
    panel_id: str = ""
    panel_label: str = ""
    navigated: bool = False
    rendered: bool = False
    console_errors: int = 0
    network_errors: int = 0
    interactive_elements: int = 0
    clickable_tested: int = 0
    screenshot_path: str = ""
    rating: str = "UNTESTED"
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "panel_id": self.panel_id,
            "panel_label": self.panel_label,
            "navigated": self.navigated,
            "rendered": self.rendered,
            "console_errors": self.console_errors,
            "network_errors": self.network_errors,
            "interactive_elements": self.interactive_elements,
            "clickable_tested": self.clickable_tested,
            "screenshot_path": self.screenshot_path,
            "rating": self.rating,
            "notes": self.notes,
        }


@dataclass
class TaskResult:
    task_number: int = 0
    task_name: str = ""
    description: str = ""
    completed: bool = False
    stayed_in_cockpit: bool = True
    escape_reason: str = ""
    escape_tool: str = ""
    steps_completed: int = 0
    steps_total: int = 0
    console_errors: int = 0
    screenshot_paths: list[str] = field(default_factory=list)
    duration_seconds: float = 0.0
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_number": self.task_number,
            "task_name": self.task_name,
            "description": self.description,
            "completed": self.completed,
            "stayed_in_cockpit": self.stayed_in_cockpit,
            "escape_reason": self.escape_reason,
            "escape_tool": self.escape_tool,
            "steps_completed": self.steps_completed,
            "steps_total": self.steps_total,
            "console_errors": self.console_errors,
            "screenshot_paths": self.screenshot_paths,
            "duration_seconds": self.duration_seconds,
            "notes": self.notes,
        }


@dataclass
class CertificationReport:
    campaign: str = "C28"
    title: str = "Cockpit Supremacy — Meta IDE Daily Driver Replacement"
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    cockpit_url: str = _COCKPIT_URL

    # Phase 8.2 — panel audit
    panel_results: list[PanelAuditResult] = field(default_factory=list)
    panels_working: int = 0
    panels_partial: int = 0
    panels_broken: int = 0
    panels_placeholder: int = 0

    # Phase 8.3 — 10-task acceptance
    task_results: list[TaskResult] = field(default_factory=list)
    tasks_completed: int = 0
    tasks_escaped: int = 0

    # Phase 8.4 — escape rate
    total_interactions: int = 0
    total_escapes: int = 0
    escape_rate: float = 0.0

    # Health
    total_console_errors: int = 0
    total_network_errors: int = 0
    beast_connected: bool = False
    operator_healthy: bool = False

    # Verdict
    verdict: str = "PENDING"
    gap_ledger: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "campaign": self.campaign,
            "title": self.title,
            "timestamp": self.timestamp,
            "cockpit_url": self.cockpit_url,
            "panel_audit": {
                "results": [p.to_dict() for p in self.panel_results],
                "working": self.panels_working,
                "partial": self.panels_partial,
                "broken": self.panels_broken,
                "placeholder": self.panels_placeholder,
            },
            "task_acceptance": {
                "results": [t.to_dict() for t in self.task_results],
                "completed": self.tasks_completed,
                "escaped": self.tasks_escaped,
            },
            "escape_rate": {
                "total_interactions": self.total_interactions,
                "total_escapes": self.total_escapes,
                "rate_percent": round(self.escape_rate * 100, 1),
                "target_percent": 10.0,
                "passed": self.escape_rate < 0.10,
            },
            "health": {
                "console_errors": self.total_console_errors,
                "network_errors": self.total_network_errors,
                "beast_connected": self.beast_connected,
                "operator_healthy": self.operator_healthy,
            },
            "verdict": self.verdict,
            "gap_ledger": self.gap_ledger,
        }

    def to_markdown(self) -> str:
        lines = [
            f"# {self.campaign} Certification Report",
            f"**{self.title}**",
            f"Generated: {self.timestamp}",
            f"Target: {self.cockpit_url}",
            "",
            "## Verdict",
            f"**{self.verdict}**",
            "",
            f"- Escape Rate: {self.escape_rate * 100:.1f}% (target < 10%)",
            f"- Console Errors: {self.total_console_errors}",
            f"- Network Errors: {self.total_network_errors}",
            f"- Beast Connected: {'YES' if self.beast_connected else 'NO'}",
            f"- Operator Healthy: {'YES' if self.operator_healthy else 'NO'}",
            "",
            "## Panel Audit",
            f"Working: {self.panels_working} | Partial: {self.panels_partial} | "
            f"Broken: {self.panels_broken} | Placeholder: {self.panels_placeholder}",
            "",
            "| Panel | Rating | Console Errors | Notes |",
            "|-------|--------|----------------|-------|",
        ]
        for p in self.panel_results:
            lines.append(
                f"| {p.panel_label} | {p.rating} | {p.console_errors} | {p.notes} |"
            )

        lines.extend([
            "",
            "## 10-Task Acceptance",
            f"Completed: {self.tasks_completed}/10 | Escapes: {self.tasks_escaped}",
            "",
            "| # | Task | Completed | In-Cockpit | Escape Reason |",
            "|---|------|-----------|------------|---------------|",
        ])
        for t in self.task_results:
            escaped = "YES" if t.stayed_in_cockpit else f"NO → {t.escape_tool}"
            lines.append(
                f"| {t.task_number} | {t.task_name} | "
                f"{'YES' if t.completed else 'NO'} | {escaped} | {t.escape_reason} |"
            )

        if self.gap_ledger:
            lines.extend(["", "## Gap Ledger (C29 Work Items)"])
            for gap in self.gap_ledger:
                lines.append(f"- {gap}")

        return "\n".join(lines)


# ---------- helpers ----------

def _check_beast_connected() -> bool:
    """Check if Beast is on the mesh."""
    try:
        import urllib.request
        resp = urllib.request.urlopen("http://localhost:8095/health", timeout=5)
        data = json.loads(resp.read())
        return data.get("connected_nodes", 0) > 0
    except Exception:
        return False


def _check_operator_health() -> bool:
    """Check os-operator health."""
    try:
        import urllib.request
        resp = urllib.request.urlopen("http://localhost:8091/api/umh/health", timeout=5)
        data = json.loads(resp.read())
        return data.get("status") == "ok"
    except Exception:
        return False


def _dispatch_beast_collector(
    extra_args: str = "",
    passes: int = 1,
) -> dict[str, Any]:
    """Dispatch browser_gate_collector.py to Beast via SSH.

    Returns parsed JSON output from Beast.
    """
    if not _BEAST_SSH:
        return {"error": "UMH_BEAST_SSH not configured", "passes": []}

    cmd = (
        f'python "{_COLLECTOR_SCRIPT}" '
        f'--url {_COCKPIT_URL} '
        f'--passes {passes} '
        f'--output-json '
        f'{extra_args}'
    )

    ssh_args = [
        "ssh", "-o", "ConnectTimeout=15",
        "-o", "StrictHostKeyChecking=accept-new",
        "-o", "ServerAliveInterval=10",
        _BEAST_SSH,
        cmd,
    ]

    logger.info("Dispatching to Beast: %s", cmd)
    result = gated_subprocess_run(
        ssh_args,
        capture_output=True,
        text=True,
        timeout=passes * 3 * 120,
        caller="c28_certification",
    )

    if result is None:
        return {"error": "CPU gate blocked", "passes": []}

    if result.returncode != 0:
        return {
            "error": f"Beast collector failed (rc={result.returncode})",
            "stderr": result.stderr[:1000],
            "passes": [],
        }

    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        json_start = result.stdout.rfind('{"passes"')
        if json_start >= 0:
            try:
                return json.loads(result.stdout[json_start:])
            except json.JSONDecodeError:
                pass
        return {
            "error": "JSON parse failed",
            "raw_tail": result.stdout[-500:],
            "passes": [],
        }


# ---------- phase runners ----------

def run_panel_audit(report: CertificationReport) -> None:
    """Phase 8.2 — Browser-driven panel surface audit.

    Dispatches Beast collector with panel-audit mode.
    Each panel navigated, screenshotted, and rated.
    """
    logger.info("=== Phase 8.2: Panel Surface Audit ===")

    primary_panels = [
        ("command-center", "Command Center"),
        ("meta-ide", "Meta IDE"),
        ("execution", "Execution"),
        ("unified-execution", "Unified Execution"),
        ("work", "Work"),
        ("planning", "Planning"),
        ("organism-map", "Organism Map"),
        ("governance", "Governance"),
        ("settings", "Settings"),
        ("deliverables", "Deliverables"),
    ]
    secondary_panels = [
        ("actions", "Actions"),
        ("distributed-runtime", "Distributed Runtime"),
        ("operator-continuity", "Operator Continuity"),
        ("operator-home", "Operator Home"),
        ("screen-awareness", "Screen Awareness"),
        ("service-graph", "Service Graph"),
        ("state-authority", "State Authority"),
        ("umh-nodes", "UMH Nodes"),
        ("workspace-topology", "Workspace Topology"),
    ]

    all_panels = primary_panels + secondary_panels

    evidence = _dispatch_beast_collector(
        extra_args=f'--panels "{",".join(p[0] for p in all_panels)}"',
        passes=1,
    )

    if evidence.get("error"):
        logger.warning("Beast collector error: %s", evidence["error"])
        for pid, plabel in all_panels:
            report.panel_results.append(PanelAuditResult(
                panel_id=pid,
                panel_label=plabel,
                rating="UNTESTED",
                notes=f"Beast collector error: {evidence.get('error', 'unknown')}",
            ))
        return

    panel_data = evidence.get("panel_audit", {})
    for pid, plabel in all_panels:
        pd = panel_data.get(pid, {})
        result = PanelAuditResult(
            panel_id=pid,
            panel_label=plabel,
            navigated=pd.get("navigated", False),
            rendered=pd.get("rendered", False),
            console_errors=pd.get("console_errors", 0),
            network_errors=pd.get("network_errors", 0),
            interactive_elements=pd.get("interactive_elements", 0),
            clickable_tested=pd.get("clickable_tested", 0),
            screenshot_path=pd.get("screenshot_path", ""),
        )

        if not result.navigated:
            result.rating = "DEAD"
        elif not result.rendered:
            result.rating = "BROKEN"
        elif result.console_errors > 0:
            result.rating = "PARTIAL"
        elif result.interactive_elements == 0:
            result.rating = "PLACEHOLDER"
        else:
            result.rating = "WORKING"

        result.notes = pd.get("notes", "")
        report.panel_results.append(result)

    report.panels_working = sum(1 for p in report.panel_results if p.rating == "WORKING")
    report.panels_partial = sum(1 for p in report.panel_results if p.rating == "PARTIAL")
    report.panels_broken = sum(1 for p in report.panel_results if p.rating in ("BROKEN", "DEAD"))
    report.panels_placeholder = sum(1 for p in report.panel_results if p.rating == "PLACEHOLDER")


def run_task_acceptance(report: CertificationReport) -> None:
    """Phase 8.3 — 10 real task acceptance test.

    Each task driven through Beast's browser against the live cockpit.
    Escape detection: if operator must leave cockpit, the escape is logged.
    """
    logger.info("=== Phase 8.3: 10-Task Acceptance ===")

    tasks = [
        (1, "Navigate all panels", "Navigate to every primary panel via LeftRail"),
        (2, "Send chat prompt", "Send a prompt in RightRail chat and observe response"),
        (3, "View execution state", "Open execution panel and verify execution data loads"),
        (4, "View governance", "Open governance panel and verify policy data renders"),
        (5, "View organism map", "Open organism map and verify node/health data"),
        (6, "View live preview", "Open Meta IDE and load a projection preview"),
        (7, "Context switch", "Switch between Command Center and Meta IDE panels"),
        (8, "View work queue", "Open work panel and verify work items display"),
        (9, "Check Beast health", "Verify Beast node shows in mesh nodes with health data"),
        (10, "Resume context", "Close and reopen cockpit — verify resume card appears"),
    ]

    evidence = _dispatch_beast_collector(
        extra_args=f'--tasks "{len(tasks)}"',
        passes=1,
    )

    task_evidence = evidence.get("task_results", {})

    for task_num, task_name, task_desc in tasks:
        te = task_evidence.get(str(task_num), {})
        result = TaskResult(
            task_number=task_num,
            task_name=task_name,
            description=task_desc,
            completed=te.get("completed", False),
            stayed_in_cockpit=te.get("stayed_in_cockpit", True),
            escape_reason=te.get("escape_reason", ""),
            escape_tool=te.get("escape_tool", ""),
            steps_completed=te.get("steps_completed", 0),
            steps_total=te.get("steps_total", 1),
            console_errors=te.get("console_errors", 0),
            screenshot_paths=te.get("screenshot_paths", []),
            duration_seconds=te.get("duration_seconds", 0.0),
            notes=te.get("notes", ""),
        )
        report.task_results.append(result)

    report.tasks_completed = sum(1 for t in report.task_results if t.completed)
    report.tasks_escaped = sum(1 for t in report.task_results if not t.stayed_in_cockpit)


def compute_escape_rate(report: CertificationReport) -> None:
    """Phase 8.4 — compute Operator Escape Rate."""
    total = len(report.task_results)
    escapes = report.tasks_escaped
    report.total_interactions = total
    report.total_escapes = escapes
    report.escape_rate = escapes / max(total, 1)


def compute_verdict(report: CertificationReport) -> None:
    """Final verdict computation."""
    report.total_console_errors = sum(p.console_errors for p in report.panel_results)
    report.total_console_errors += sum(t.console_errors for t in report.task_results)
    report.total_network_errors = sum(p.network_errors for p in report.panel_results)

    report.beast_connected = _check_beast_connected()
    report.operator_healthy = _check_operator_health()

    # Gap ledger — every failure becomes a C29 item
    for p in report.panel_results:
        if p.rating in ("BROKEN", "DEAD"):
            report.gap_ledger.append(f"Panel {p.panel_label}: {p.rating} — {p.notes}")
        elif p.rating == "PLACEHOLDER":
            report.gap_ledger.append(f"Panel {p.panel_label}: no interactive elements")
    for t in report.task_results:
        if not t.stayed_in_cockpit:
            report.gap_ledger.append(
                f"Task {t.task_number} ({t.task_name}): escaped to {t.escape_tool} — {t.escape_reason}"
            )
        elif not t.completed:
            report.gap_ledger.append(
                f"Task {t.task_number} ({t.task_name}): not completed — {t.notes}"
            )

    # Verdict
    passes = True
    reasons = []

    if report.escape_rate >= 0.10:
        passes = False
        reasons.append(f"escape rate {report.escape_rate*100:.1f}% >= 10%")

    if report.total_console_errors > 0:
        passes = False
        reasons.append(f"{report.total_console_errors} console errors")

    if not report.beast_connected:
        passes = False
        reasons.append("Beast not connected")

    if not report.operator_healthy:
        passes = False
        reasons.append("operator unhealthy")

    if report.panels_broken > 0:
        passes = False
        reasons.append(f"{report.panels_broken} broken panels")

    if passes:
        report.verdict = "PASS"
    else:
        report.verdict = f"FAIL: {'; '.join(reasons)}"


# ---------- orchestrator ----------

def run_certification(phases: str = "full") -> CertificationReport:
    """Run the full C28 certification suite."""
    _CERT_DIR.mkdir(parents=True, exist_ok=True)
    report = CertificationReport()

    logger.info("=== C28 Certification Starting ===")
    logger.info("Target: %s", _COCKPIT_URL)
    logger.info("Beast SSH: %s", _BEAST_SSH or "NOT SET")
    logger.info("Phases: %s", phases)

    if phases in ("panel-audit", "full"):
        run_panel_audit(report)

    if phases in ("tasks", "full"):
        run_task_acceptance(report)

    compute_escape_rate(report)
    compute_verdict(report)

    # Persist
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H%M%S")
    json_path = _CERT_DIR / f"c28_certification_{ts}.json"
    md_path = _CERT_DIR / f"c28_certification_{ts}.md"

    with open(json_path, "w") as f:
        json.dump(report.to_dict(), f, indent=2, default=str)

    with open(md_path, "w") as f:
        f.write(report.to_markdown())

    logger.info("Certification report: %s", md_path)
    logger.info("Verdict: %s", report.verdict)

    return report


# ---------- CLI ----------

def main():
    import argparse
    parser = argparse.ArgumentParser(description="C28 Certification Suite")
    parser.add_argument("--phase", default="full", choices=["panel-audit", "tasks", "full"])
    parser.add_argument("--report-only", action="store_true", help="Show latest report")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    if args.report_only:
        reports = sorted(_CERT_DIR.glob("c28_certification_*.md"))
        if reports:
            print(reports[-1].read_text())
        else:
            print("No certification reports found")
        return

    report = run_certification(args.phase)
    print("\n" + report.to_markdown())


if __name__ == "__main__":
    main()
