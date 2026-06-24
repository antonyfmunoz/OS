"""Browser Evidence Collector — runs on executor nodes to collect verification evidence.

Executes Playwright sessions across 3 viewports (desktop, tablet, mobile)
with real browser engines on an executor node's display. Collects 4-layer
evidence per pass and returns structured data for BrowserVerificationGate.

This module is the ONLY place browser evidence is collected. The gate
validates; this collects. They form a pair.

Evidence collection ALWAYS runs on executor-roled nodes (with display),
NEVER on the orchestrator node (headless). The orchestrator triggers
collection via SSH to an executor discovered from device_registry.json.

UMH substrate subsystem. Instance-agnostic.
"""

from __future__ import annotations

import json
import logging
import os
import re
import shlex
import socket
import subprocess
import time
import urllib.parse
from dataclasses import dataclass, field
from typing import Any

from substrate.execution.cpu_gate import gated_subprocess_run
from substrate.execution.credential_gate import validate_credential_source
from substrate.meta_ide.browser_verification_gate import DEFAULT_PASS_COUNT

logger = logging.getLogger(__name__)

_ROOT = os.environ.get("UMH_ROOT") or "/opt/OS"


def _resolve_executor_ssh() -> str:
    """Resolve SSH target for an executor-roled node.

    Priority: UMH_EXECUTOR_SSH env → UMH_BEAST_SSH fallback → device_registry.json lookup.
    """
    target = os.environ.get("UMH_EXECUTOR_SSH", "")
    if target:
        return target
    target = os.environ.get("UMH_BEAST_SSH", "")
    if target:
        return target
    registry_path = os.path.join(_ROOT, "infra", "device_registry.json")
    try:
        with open(registry_path) as f:
            devices = json.load(f)
        for dev in devices:
            if dev.get("role") == "executor" and dev.get("tailscale_ip"):
                ip = dev["tailscale_ip"]
                user = dev.get("ssh_user", "")
                if user:
                    return f"{user}@{ip}"
                return ip
    except (FileNotFoundError, json.JSONDecodeError, KeyError) as exc:
        logger.debug("device registry lookup failed: %s", exc)
    return ""


def _get_executor_os() -> str:
    """Look up the executor node's OS from device_registry.json."""
    registry_path = os.path.join(_ROOT, "infra", "device_registry.json")
    try:
        with open(registry_path) as f:
            devices = json.load(f)
        for dev in devices:
            if dev.get("role") == "executor":
                return dev.get("os", "").lower()
    except (FileNotFoundError, json.JSONDecodeError):
        pass
    return ""


def _get_local_node_role() -> str:
    """Look up this node's role from device_registry.json by hostname."""
    hostname = socket.gethostname().lower()
    registry_path = os.path.join(_ROOT, "infra", "device_registry.json")
    try:
        with open(registry_path) as f:
            devices = json.load(f)
        for dev in devices:
            ts_name = dev.get("tailscale_name", "").lower()
            dev_id = dev.get("id", "").lower()
            if ts_name == hostname or dev_id == hostname:
                return dev.get("role", "unknown")
    except (FileNotFoundError, json.JSONDecodeError):
        pass
    return "unknown"


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
                f"{vp.viewport_name}({vp.width}x{vp.height}): {bl.get('entry_count', 0)} entries"
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
    pass_count: int = DEFAULT_PASS_COUNT,
) -> dict[str, Any]:
    """Trigger evidence collection on an executor node via SSH.

    Returns evidence dict with 'passes' key suitable for
    BrowserVerificationGate.validate_evidence().
    """
    parsed = urllib.parse.urlparse(target_url)
    if parsed.scheme != "https":
        return {"passes": [], "error": f"Only https URLs allowed, got {parsed.scheme}"}

    executor_os = _get_executor_os()
    if executor_os == "windows":
        collector_cmd = (
            f'python "{_COLLECTOR_SCRIPT_PATH}" '
            f"--url {target_url} "
            f"--passes {int(pass_count)} "
            f"--output-json"
        )
    else:
        collector_cmd = (
            f"python {shlex.quote(_COLLECTOR_SCRIPT_PATH)} "
            f"--url {shlex.quote(target_url)} "
            f"--passes {int(pass_count)} "
            f"--output-json"
        )

    executor_ssh = _resolve_executor_ssh()
    if not executor_ssh:
        logger.error("No executor node available for browser collection")
        return {
            "passes": [],
            "error": "No executor SSH target (set UMH_EXECUTOR_SSH or register an executor in device_registry.json)",
        }

    cred_gate = validate_credential_source()
    if cred_gate.injection_ready:
        executor_tpl = _COLLECTOR_SCRIPT_PATH.replace(
            "browser_gate_collector.py", ".env.beast.tpl"
        )
        remote_cmd = f'op run --env-file="{executor_tpl}" -- {collector_cmd}'
    else:
        logger.warning(
            "Running without credential injection: %s", cred_gate.fallback_reason
        )
        remote_cmd = collector_cmd

    ssh_args = [
        "ssh",
        "-o",
        "ConnectTimeout=30",
        "-o",
        "StrictHostKeyChecking=accept-new",
        "-o",
        "ServerAliveInterval=15",
        executor_ssh,
        remote_cmd,
    ]

    logger.info(
        "Triggering browser evidence collection on executor (%s): %d passes × %d viewports",
        executor_ssh,
        pass_count,
        len(VIEWPORTS),
    )

    try:
        raw_result = gated_subprocess_run(
            ssh_args,
            capture_output=True,
            text=False,
            timeout=pass_count * len(VIEWPORTS) * 120 + 60,
            caller="browser_evidence_collector",
        )
    except subprocess.TimeoutExpired as exc:
        partial_out = exc.stdout.decode("utf-8", errors="replace") if exc.stdout else ""
        logger.error("Browser collection timed out after %ss", exc.timeout)
        return {
            "passes": [],
            "error": f"Collection timed out after {exc.timeout}s",
            "stdout": partial_out[-2000:],
        }

    if raw_result is None:
        logger.error("CPU gate blocked browser evidence collection")
        return {"passes": [], "error": "CPU gate blocked collection"}

    stdout = raw_result.stdout.decode("utf-8", errors="replace") if raw_result.stdout else ""
    stderr = raw_result.stderr.decode("utf-8", errors="replace") if raw_result.stderr else ""

    if raw_result.returncode != 0:
        logger.warning("Executor collector exited %d: %s", raw_result.returncode, stderr[:300])
        if stdout.strip():
            try:
                output = json.loads(stdout)
                output["collector_stderr"] = stderr[:500]
                output.update(node_meta)
                return output
            except json.JSONDecodeError:
                pass
        return {
            "passes": [],
            "error": stderr[:500],
            "stdout": stdout[:500],
        }

    node_meta = {
        "collection_node": socket.gethostname(),
        "collection_node_role": _get_local_node_role(),
        "executor_target": executor_ssh,
    }

    try:
        output = json.loads(stdout)
        output.update(node_meta)
        return output
    except json.JSONDecodeError:
        json_start = stdout.rfind('{"passes"')
        if json_start >= 0:
            try:
                parsed = json.loads(stdout[json_start:])
                parsed.update(node_meta)
                return parsed
            except json.JSONDecodeError:
                pass
        logger.error("Failed to parse executor collector output as JSON")
        return {
            "passes": [],
            "error": "JSON parse failed",
            "raw_output": stdout[-1000:],
            **node_meta,
        }


_LOG_REQUEST_RE = re.compile(
    r'"(?P<method>GET|POST|PUT|DELETE|PATCH|HEAD|OPTIONS)\s+'
    r'(?P<path>/[^\s"]*)\s+HTTP/[^"]*"\s+(?P<status>\d{3})'
)
_LOG_ERROR_RE = re.compile(
    r"(ERROR|Traceback|CRITICAL|WARNING.*(?:fail|error|except))",
    re.IGNORECASE,
)


def collect_log_reconciliation(
    network_evidence: list[dict[str, Any]],
    browser_actions: list[dict[str, Any]] | None = None,
    service_name: str = "os-operator",
    time_window_s: int = 120,
) -> dict[str, Any]:
    """Three-way reconciliation: network→logs, logs→network, action→trace.

    Returns a dict matching LogLayerResult fields including cross_references,
    orphan_server_errors, action_traces, and reconciliation_score.
    """
    result = gated_subprocess_run(
        ["docker", "logs", service_name, "--tail", "200", "--since", f"{time_window_s}s"],
        capture_output=True,
        text=True,
        timeout=10,
        caller="browser_evidence_collector.reconciliation",
    )
    if result is None:
        return {
            "service_name": service_name,
            "log_lines_checked": 0,
            "tracebacks_found": 0,
            "auth_failures": 0,
            "timeouts": 0,
            "cross_references": [],
            "unmatched_network_requests": 0,
            "unmatched_log_errors": 0,
            "orphan_server_errors": [],
            "action_traces": [],
            "reconciliation_score": 0.0,
            "error": "CPU gate blocked",
        }

    combined = result.stdout + result.stderr
    lines = combined.strip().splitlines()

    parsed_log_requests: list[dict[str, Any]] = []
    error_lines: list[str] = []
    for line in lines:
        m = _LOG_REQUEST_RE.search(line)
        if m:
            parsed_log_requests.append(
                {
                    "method": m.group("method"),
                    "path": m.group("path"),
                    "status": int(m.group("status")),
                    "raw": line,
                }
            )
        if _LOG_ERROR_RE.search(line):
            error_lines.append(line)

    # 1. Network → Log cross-references
    cross_refs: list[dict[str, Any]] = []
    matched_log_indices: set[int] = set()
    unmatched_net = 0

    for net_req in network_evidence:
        net_url = net_req.get("url", "")
        net_status = net_req.get("status", 0)
        net_method = net_req.get("method", "GET")
        path = urllib.parse.urlparse(net_url).path if net_url else ""

        found = False
        for i, log_req in enumerate(parsed_log_requests):
            if i in matched_log_indices:
                continue
            if log_req["path"] == path:
                matched_log_indices.add(i)
                log_status = log_req["status"]
                cr = {
                    "endpoint": path,
                    "http_method": net_method,
                    "network_status": net_status,
                    "network_timestamp": net_req.get("timestamp", 0.0),
                    "log_entry_found": True,
                    "log_status": log_status,
                    "log_clean": log_status < 400,
                    "log_errors": [],
                    "status_match": net_status == log_status,
                    "latency_ms": 0.0,
                    "direction": "network_to_log",
                }
                cross_refs.append(cr)
                found = True
                break
        if not found:
            cross_refs.append(
                {
                    "endpoint": path,
                    "http_method": net_method,
                    "network_status": net_status,
                    "network_timestamp": net_req.get("timestamp", 0.0),
                    "log_entry_found": False,
                    "log_status": 0,
                    "log_clean": False,
                    "log_errors": [],
                    "status_match": False,
                    "latency_ms": 0.0,
                    "direction": "network_to_log",
                }
            )
            unmatched_net += 1

    # 2. Orphan detection: server errors with no matching network request
    net_paths = {
        urllib.parse.urlparse(nr.get("url", "")).path for nr in network_evidence if nr.get("url")
    }
    orphans: list[str] = []
    for err_line in error_lines:
        m = _LOG_REQUEST_RE.search(err_line)
        if m:
            err_path = m.group("path")
            if err_path not in net_paths:
                orphans.append(err_line[:200])
        else:
            orphans.append(err_line[:200])

    # 3. Action → Trace reconciliation
    actions = browser_actions or []
    action_traces: list[dict[str, Any]] = []
    matched_actions = 0
    for action in actions:
        action_type = action.get("type", "")
        expected_method = "GET"
        if action_type in ("click", "submit", "form_submit"):
            expected_method = "POST"
        expected_path = action.get("expected_endpoint", "")
        trace_found = False
        if expected_path:
            for log_req in parsed_log_requests:
                if log_req["path"] == expected_path and log_req["method"] == expected_method:
                    trace_found = True
                    break
        trace = {
            "action_type": action_type,
            "expected_endpoint": expected_path,
            "expected_method": expected_method,
            "trace_found": trace_found,
            "action_description": action.get("description", ""),
        }
        action_traces.append(trace)
        if trace_found:
            matched_actions += 1

    total_reconcilable = len(network_evidence) + len(actions)
    total_matched = (len(network_evidence) - unmatched_net) + matched_actions
    recon_score = total_matched / total_reconcilable if total_reconcilable > 0 else 1.0

    tracebacks = sum(1 for l in lines if "Traceback" in l)
    auth_fails = sum(1 for l in lines if "401" in l or "403" in l)
    timeout_count = sum(1 for l in lines if "timeout" in l.lower() or "timed out" in l.lower())

    return {
        "service_name": service_name,
        "log_lines_checked": len(lines),
        "tracebacks_found": tracebacks,
        "auth_failures": auth_fails,
        "timeouts": timeout_count,
        "cross_references": cross_refs,
        "unmatched_network_requests": unmatched_net,
        "unmatched_log_errors": len(orphans),
        "orphan_server_errors": orphans[:20],
        "action_traces": action_traces,
        "reconciliation_score": round(recon_score, 3),
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
            "timeouts": sum(1 for l in lines if "timeout" in l.lower() or "timed out" in l.lower()),
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
