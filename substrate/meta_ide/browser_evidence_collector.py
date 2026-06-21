"""Browser Evidence Collector — runs on Beast to collect verification evidence.

Executes Playwright sessions across 3 viewports (desktop, tablet, mobile)
with real browser engines on Beast's display (Session 1). Collects 4-layer
evidence per pass and returns structured data for BrowserVerificationGate.

This module is the ONLY place browser evidence is collected. The gate
validates; this collects. They form a pair.

Evidence collection ALWAYS runs on Beast (GPU workstation with display),
NEVER headless on VPS. The VPS triggers collection via SSH to Beast.

UMH substrate subsystem. Instance-agnostic.
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
import time
from dataclasses import dataclass, field
from typing import Any

from substrate.execution.cpu_gate import gated_subprocess_run

logger = logging.getLogger(__name__)

REQUIRED_PASSES = 3

_BEAST_SSH = os.environ.get("UMH_BEAST_SSH", "")

_COLLECTOR_SCRIPT_PATH = "C:\\dev\\dev\\OS\\scripts\\browser_gate_collector.py"

VIEWPORTS: list[dict[str, Any]] = [
    {
        "name": "desktop",
        "width": 1920,
        "height": 1080,
        "browser": "chromium",
        "device": None,
    },
    {
        "name": "tablet",
        "width": 820,
        "height": 1180,
        "browser": "chromium",
        "device": "iPad Pro 11",
    },
    {
        "name": "mobile",
        "width": 390,
        "height": 844,
        "browser": "webkit",
        "device": "iPhone 14",
    },
]


@dataclass
class ViewportEvidence:
    """Evidence collected for a single viewport in a single pass."""

    viewport_name: str = ""
    width: int = 0
    height: int = 0
    browser_engine: str = ""

    browser_layer: dict[str, Any] = field(default_factory=dict)
    network_layer: dict[str, Any] = field(default_factory=dict)
    console_layer: dict[str, Any] = field(default_factory=dict)
    log_layer: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "viewport_name": self.viewport_name,
            "width": self.width,
            "height": self.height,
            "browser_engine": self.browser_engine,
            "browser_layer": self.browser_layer,
            "network_layer": self.network_layer,
            "console_layer": self.console_layer,
            "log_layer": self.log_layer,
        }


@dataclass
class PassEvidence:
    """Evidence collected for all viewports in a single pass."""

    pass_number: int = 0
    viewports: list[ViewportEvidence] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)

    browser_check: dict[str, Any] = field(default_factory=dict)
    network_check: dict[str, Any] = field(default_factory=dict)
    console_check: dict[str, Any] = field(default_factory=dict)
    log_check: dict[str, Any] = field(default_factory=dict)

    def to_gate_format(self) -> dict[str, Any]:
        """Convert to the format expected by BrowserVerificationGate."""
        all_elements: list[str] = []
        all_endpoints: list[dict[str, Any]] = []
        total_network_errors = 0
        total_app_errors = 0
        all_app_error_msgs: list[str] = []
        total_ignored = 0
        snapshot_parts: list[str] = []

        log_data = {
            "service_name": "",
            "log_lines_checked": 0,
            "tracebacks_found": 0,
            "auth_failures": 0,
            "timeouts": 0,
        }

        for vp in self.viewports:
            bl = vp.browser_layer
            all_elements.extend(bl.get("elements_confirmed", []))
            snapshot_parts.append(
                f"{vp.viewport_name}({vp.width}x{vp.height}): "
                f"{bl.get('entry_count', 0)} entries"
            )

            nl = vp.network_layer
            all_endpoints.extend(nl.get("endpoints_checked", []))
            total_network_errors += nl.get("error_count", 0)

            cl = vp.console_layer
            total_app_errors += cl.get("app_error_count", 0)
            all_app_error_msgs.extend(cl.get("app_errors", []))
            total_ignored += cl.get("ignored_errors", 0)

            ll = vp.log_layer
            if ll.get("log_lines_checked", 0) > 0:
                log_data["service_name"] = ll.get("service_name", "")
                log_data["log_lines_checked"] = ll.get("log_lines_checked", 0)
                log_data["tracebacks_found"] += ll.get("tracebacks_found", 0)
                log_data["auth_failures"] += ll.get("auth_failures", 0)
                log_data["timeouts"] += ll.get("timeouts", 0)

        return {
            "pass_number": self.pass_number,
            "browser_check": {
                "elements_confirmed": all_elements,
                "snapshot_summary": " | ".join(snapshot_parts),
            },
            "network_check": {
                "endpoints_checked": all_endpoints,
                "error_count": total_network_errors,
            },
            "console_check": {
                "app_error_count": total_app_errors,
                "app_errors": all_app_error_msgs[:10],
                "ignored_errors": total_ignored,
            },
            "log_check": log_data,
            "timestamp": self.timestamp,
            "viewport_details": [v.to_dict() for v in self.viewports],
        }


def trigger_collection(
    target_url: str,
    pass_count: int = REQUIRED_PASSES,
) -> dict[str, Any]:
    """Trigger evidence collection on Beast via SSH.

    Returns evidence dict with 'passes' key suitable for
    BrowserVerificationGate.validate_evidence().
    """
    cmd = (
        f'python "{_COLLECTOR_SCRIPT_PATH}" '
        f'--url "{target_url}" '
        f'--passes {pass_count} '
        f'--output-json'
    )

    ssh_args = [
        "ssh", "-o", "ConnectTimeout=10",
        "-o", "StrictHostKeyChecking=accept-new",
        _BEAST_SSH,
        cmd,
    ]

    if not _BEAST_SSH:
        logger.error("UMH_BEAST_SSH not set — cannot trigger browser collection")
        return {"passes": [], "error": "UMH_BEAST_SSH env var not configured"}

    logger.info(
        "Triggering browser evidence collection on Beast: %d passes × %d viewports",
        pass_count,
        len(VIEWPORTS),
    )

    result = gated_subprocess_run(
        ssh_args,
        capture_output=True,
        text=True,
        timeout=pass_count * len(VIEWPORTS) * 60,
        caller="browser_evidence_collector",
    )

    if result is None:
        logger.error("CPU gate blocked browser evidence collection")
        return {"passes": [], "error": "CPU gate blocked collection"}

    if result.returncode != 0:
        logger.error("Beast collector failed: %s", result.stderr[:500])
        return {
            "passes": [],
            "error": result.stderr[:500],
            "stdout": result.stdout[:500],
        }

    try:
        output = json.loads(result.stdout)
        return output
    except json.JSONDecodeError:
        json_start = result.stdout.rfind('{"passes"')
        if json_start >= 0:
            try:
                return json.loads(result.stdout[json_start:])
            except json.JSONDecodeError:
                pass
        logger.error("Failed to parse Beast collector output as JSON")
        return {
            "passes": [],
            "error": "JSON parse failed",
            "raw_output": result.stdout[-1000:],
        }


def collect_local_logs(service_name: str = "os-operator", tail: int = 50) -> dict[str, Any]:
    """Collect Layer 4 log evidence from local Docker container."""
    try:
        result = gated_subprocess_run(
            ["docker", "logs", service_name, "--tail", str(tail)],
            capture_output=True,
            text=True,
            timeout=10,
            caller="browser_evidence_collector.logs",
        )
        if result is None:
            return {
                "service_name": service_name,
                "log_lines_checked": 0,
                "tracebacks_found": 0,
                "auth_failures": 0,
                "timeouts": 0,
                "error": "CPU gate blocked",
            }

        combined = result.stdout + result.stderr
        lines = combined.strip().splitlines()
        return {
            "service_name": service_name,
            "log_lines_checked": len(lines),
            "tracebacks_found": sum(1 for l in lines if "Traceback" in l),
            "auth_failures": sum(1 for l in lines if "401" in l or "403" in l),
            "timeouts": sum(
                1 for l in lines
                if "timeout" in l.lower() or "timed out" in l.lower()
            ),
        }
    except Exception as e:
        return {
            "service_name": service_name,
            "log_lines_checked": 0,
            "tracebacks_found": 0,
            "auth_failures": 0,
            "timeouts": 0,
            "error": str(e),
        }
