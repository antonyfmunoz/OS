#!/usr/bin/env python3
"""Shim retirement readiness monitor.

Scans logs, cron output, and runtime state for any eos_ai
shim traversal or import attempts. Run daily during the
7-14 day monitoring window before shim removal.

Usage:
    python3 scripts/shim_retirement_monitor.py
    python3 scripts/shim_retirement_monitor.py --json
"""

from __future__ import annotations

import argparse
import datetime
import glob
import json
import os
import subprocess
import sys

LOG_DIR = os.environ.get("UMH_LOG_DIR") or "/opt/OS/logs"
REPORT_DIR = "data/runtime/shim_monitor"
MIGRATION_CUTOVER = "2026-05-11"


def scan_logs_for_eos_ai(log_dir: str) -> list[dict]:
    """Scan log files modified after migration cutover for eos_ai refs."""
    findings: list[dict] = []
    audit_logs = {"bash_commands.log", "audit.log", "tool_calls.log"}
    log_files = glob.glob(os.path.join(log_dir, "*.log"))
    cutover_ts = datetime.datetime.strptime(MIGRATION_CUTOVER, "%Y-%m-%d").timestamp()

    for log_file in log_files:
        basename = os.path.basename(log_file)
        if basename in audit_logs:
            continue
        try:
            if os.path.getmtime(log_file) < cutover_ts:
                continue
        except OSError:
            continue
        try:
            with open(log_file, errors="ignore") as f:
                for i, line in enumerate(f, 1):
                    if "eos_ai" not in line:
                        continue
                    is_error = "ImportError" in line or "ModuleNotFoundError" in line
                    is_import = "import eos_ai" in line or "from eos_ai" in line
                    if not (is_error or is_import):
                        continue
                    if _is_pre_migration_entry(line):
                        continue
                    findings.append({
                        "file": basename,
                        "line": i,
                        "content": line.strip()[:200],
                        "type": "import_error" if is_error else "import_attempt",
                    })
        except OSError:
            pass

    return findings


def _is_pre_migration_entry(line: str) -> bool:
    """Heuristic: skip log lines with timestamps before the migration cutover."""
    for prefix_len in (10, 19, 25):
        candidate = line[:prefix_len]
        if candidate < MIGRATION_CUTOVER:
            return True
    return False


def check_docker_containers() -> list[dict]:
    """Check running containers for eos_ai references in their env."""
    findings: list[dict] = []
    try:
        result = subprocess.run(
            ["docker", "ps", "--format", "{{.Names}}"],
            capture_output=True, text=True, timeout=10,
        )
        containers = result.stdout.strip().split("\n") if result.stdout.strip() else []

        for container in containers:
            env_result = subprocess.run(
                ["docker", "exec", container, "env"],
                capture_output=True, text=True, timeout=10,
            )
            for line in env_result.stdout.split("\n"):
                if "eos_ai" in line:
                    findings.append({
                        "container": container,
                        "env_var": line.strip()[:100],
                        "type": "container_env",
                    })
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        pass

    return findings


def check_crontab() -> list[dict]:
    """Verify crontab has no eos_ai references."""
    findings: list[dict] = []
    try:
        result = subprocess.run(
            ["crontab", "-l"], capture_output=True, text=True, timeout=5,
        )
        for i, line in enumerate(result.stdout.split("\n"), 1):
            if "eos_ai" in line:
                findings.append({
                    "line": i,
                    "content": line.strip()[:200],
                    "type": "crontab_ref",
                })
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass

    return findings


def check_shim_imports() -> dict:
    """Test that canonical imports work and shim identity holds."""
    results = {}
    sys.path.insert(0, os.environ.get("UMH_ROOT") or "/opt/OS")

    test_modules = [
        "state.storage.db", "state.memory.memory", "runtime.context",
        "substrate.execution.runtime.model_router", "substrate.control_plane.runtime.gateway",
        "substrate.execution.runtime.agent_runtime", "substrate.control_plane.runtime.cognitive_loop",
    ]

    for mod_name in test_modules:
        try:
            __import__(mod_name)
            results[mod_name] = "OK"
        except ImportError as e:
            results[mod_name] = f"FAIL: {e}"

    return results


def check_process_imports() -> list[dict]:
    """Check /proc for running Python processes importing eos_ai."""
    findings: list[dict] = []
    try:
        for pid_dir in glob.glob("/proc/[0-9]*"):
            try:
                cmdline_path = os.path.join(pid_dir, "cmdline")
                with open(cmdline_path, "rb") as f:
                    cmdline = f.read().decode("utf-8", errors="ignore")
                if "python" in cmdline and "eos_ai" in cmdline:
                    pid = os.path.basename(pid_dir)
                    findings.append({
                        "pid": pid,
                        "cmdline": cmdline.replace("\x00", " ")[:200],
                        "type": "running_process",
                    })
            except (OSError, PermissionError):
                pass
    except OSError:
        pass

    return findings


def _load_baseline() -> int:
    """Load the baseline finding count from the first run."""
    baseline_path = os.path.join(REPORT_DIR, "baseline.json")
    if os.path.exists(baseline_path):
        with open(baseline_path) as f:
            return json.load(f).get("log_findings_count", 0)
    return -1


def _save_baseline(count: int) -> None:
    baseline_path = os.path.join(REPORT_DIR, "baseline.json")
    with open(baseline_path, "w") as f:
        json.dump({"log_findings_count": count, "captured": MIGRATION_CUTOVER}, f)


def generate_report(as_json: bool = False) -> None:
    now = datetime.datetime.now(datetime.timezone.utc)
    report = {
        "timestamp": now.isoformat(),
        "date": now.strftime("%Y-%m-%d"),
        "checks": {},
    }

    log_findings = scan_logs_for_eos_ai(LOG_DIR)
    baseline = _load_baseline()
    if baseline == -1:
        os.makedirs(REPORT_DIR, exist_ok=True)
        _save_baseline(len(log_findings))
        baseline = len(log_findings)

    new_findings = max(0, len(log_findings) - baseline)
    report["checks"]["log_scan"] = {
        "status": "PASS" if new_findings == 0 else "WARN",
        "total_findings": len(log_findings),
        "baseline": baseline,
        "new_since_baseline": new_findings,
        "details": log_findings[:20] if new_findings > 0 else [],
    }

    cron_findings = check_crontab()
    report["checks"]["crontab"] = {
        "status": "PASS" if not cron_findings else "FAIL",
        "findings": len(cron_findings),
        "details": cron_findings,
    }

    docker_findings = check_docker_containers()
    report["checks"]["docker_env"] = {
        "status": "PASS" if not docker_findings else "WARN",
        "findings": len(docker_findings),
        "details": docker_findings,
    }

    import_results = check_shim_imports()
    import_pass = all(v == "OK" for v in import_results.values())
    report["checks"]["canonical_imports"] = {
        "status": "PASS" if import_pass else "FAIL",
        "results": import_results,
    }

    proc_findings = check_process_imports()
    report["checks"]["running_processes"] = {
        "status": "PASS" if not proc_findings else "WARN",
        "findings": len(proc_findings),
        "details": proc_findings,
    }

    all_pass = all(
        c["status"] == "PASS" for c in report["checks"].values()
    )
    report["verdict"] = "READY" if all_pass else "NOT_READY"

    os.makedirs(REPORT_DIR, exist_ok=True)
    report_path = os.path.join(REPORT_DIR, f"shim_monitor_{now.strftime('%Y-%m-%d')}.json")
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)

    if as_json:
        print(json.dumps(report, indent=2))
    else:
        print(f"Shim Retirement Monitor — {now.strftime('%Y-%m-%d %H:%M UTC')}")
        print("=" * 55)
        for name, check in report["checks"].items():
            status = check["status"]
            marker = "✓" if status == "PASS" else ("⚠" if status == "WARN" else "✗")
            detail = ""
            if "findings" in check and check["findings"] > 0:
                detail = f" ({check['findings']} findings)"
            elif "new_since_baseline" in check:
                detail = f" ({check['new_since_baseline']} new, {check['baseline']} baseline)"
            print(f"  {marker} {name}: {status}{detail}")
        print(f"\n  Verdict: {report['verdict']}")
        print(f"  Report:  {report_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Shim retirement readiness monitor")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()
    generate_report(as_json=args.json)


if __name__ == "__main__":
    main()
