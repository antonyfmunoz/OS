"""Cockpit workspace routes — file browser, diff, test results, logs, proof, health.

Mounted under /api/umh/ via include_router in cockpit.py.
Phase 14.11C. UMH transport layer. Instance-agnostic.
"""

from __future__ import annotations
from substrate.execution.cpu_gate import gated_subprocess_run, gated_popen

import json
import logging
import os
import platform
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from fastapi import APIRouter, Depends, Request

from transports.api.governed import governed_mutation

logger = logging.getLogger(__name__)

workspace_router: APIRouter = APIRouter()

_configured: bool = False

_REPO_ROOT = os.environ.get("UMH_ROOT", "/opt/OS")
_DATA_ROOT = os.path.join(_REPO_ROOT, "data")
_UMH_DATA = os.path.join(_DATA_ROOT, "umh")


def configure(
    require_operator_dep: Any,
    require_api_key_dep: Callable | None = None,
) -> None:
    global _configured, workspace_router
    _configured = True
    workspace_router = _build_router(require_operator_dep, require_api_key_dep)


def _build_router(
    require_operator_dep: Any,
    require_api_key_dep: Callable | None = None,
) -> APIRouter:
    r = APIRouter()
    auth = [Depends(require_operator_dep)]

    r.add_api_route("/workspace/browse", _browse_dir, methods=["GET"])
    r.add_api_route("/workspace/read-file", _read_file, methods=["GET"])
    r.add_api_route("/workspace/git-status", _git_status, methods=["GET"])
    r.add_api_route("/workspace/git-diff", _git_diff, methods=["GET"])
    r.add_api_route("/workspace/git-diff-file", _git_diff_file, methods=["GET"])
    r.add_api_route("/workspace/test-results", _test_results, methods=["GET"])
    r.add_api_route("/workspace/execution-logs", _execution_logs, methods=["GET"])
    r.add_api_route("/workspace/proof-artifacts", _proof_artifacts, methods=["GET"])
    r.add_api_route("/workspace/health", _health_check, methods=["GET"])
    r.add_api_route("/workspace/trace-linkage", _trace_linkage, methods=["GET"])
    r.add_api_route("/workspace/write-file", _write_file, methods=["POST"], dependencies=auth)
    r.add_api_route("/workspace/remote-browse", _remote_browse, methods=["GET"])
    r.add_api_route("/workspace/remote-read-file", _remote_read_file, methods=["GET"])
    r.add_api_route("/workspace/remote-write-file", _remote_write_file, methods=["POST"], dependencies=auth)
    r.add_api_route("/workspace/mesh-nodes", _mesh_nodes_status, methods=["GET"])

    return r


# ---------------------------------------------------------------------------
# File browser
# ---------------------------------------------------------------------------

async def _browse_dir(request: Request) -> dict[str, Any]:
    from substrate.workstation.file_browser import browse_directory
    path = request.query_params.get("path", "/")
    result = browse_directory(path)
    return result.to_dict()


def _read_file(request: Request) -> dict[str, Any]:
    from substrate.workstation.file_browser import read_file
    path = request.query_params.get("path", "")
    if not path:
        return {"ok": False, "error": "path parameter required"}
    result = read_file(path)
    return result.to_dict()


async def _write_file(request: Request) -> dict[str, Any]:
    body = await request.json()
    path: str = body.get("path", "")
    content: str = body.get("content", "")
    if not path:
        return {"ok": False, "error": "path required"}
    from substrate.workstation.file_browser import _is_path_allowed
    if not _is_path_allowed(path):
        return {"ok": False, "error": "path not in allowlist"}

    def _do_write():
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
            return f"file written: {path}", True
        except OSError as e:
            return str(e), False

    resp = governed_mutation(
        mutation_name="filesystem_write",
        intent=f"write file: {path}",
        execute_fn=_do_write,
        source="cockpit",
    )
    return resp.to_http_dict()


# ---------------------------------------------------------------------------
# Git diff / status
# ---------------------------------------------------------------------------

def _run_git(args: list[str], cwd: str | None = None) -> tuple[bool, str]:
    try:
        result = gated_subprocess_run(
            ["git"] + args,
            cwd=cwd or _REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=15,
        )
        return result.returncode == 0, result.stdout
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError) as e:
        return False, str(e)


def _git_status(request: Request) -> dict[str, Any]:
    ok, output = _run_git(["status", "--porcelain"])
    if not ok:
        return {"ok": False, "error": output, "source_env": _detect_env()}

    changed: list[dict[str, str]] = []
    for line in output.strip().splitlines():
        if len(line) >= 4:
            status = line[:2].strip()
            filepath = line[3:]
            changed.append({"status": status, "path": filepath})

    ok2, branch_out = _run_git(["rev-parse", "--abbrev-ref", "HEAD"])
    ok3, commit_out = _run_git(["rev-parse", "--short", "HEAD"])

    return {
        "ok": True,
        "branch": branch_out.strip() if ok2 else "unknown",
        "commit": commit_out.strip() if ok3 else "unknown",
        "changed_count": len(changed),
        "changed_files": changed[:100],
        "source_env": _detect_env(),
    }


def _git_diff(request: Request) -> dict[str, Any]:
    staged = request.query_params.get("staged", "false") == "true"
    args = ["diff", "--stat"]
    if staged:
        args.append("--cached")

    ok, stat_output = _run_git(args)
    if not ok:
        return {"ok": False, "error": stat_output, "source_env": _detect_env()}

    ok2, diff_output = _run_git(["diff"] + (["--cached"] if staged else []))

    return {
        "ok": True,
        "staged": staged,
        "stat": stat_output.strip(),
        "diff": diff_output[:50000] if ok2 else "",
        "truncated": len(diff_output) > 50000 if ok2 else False,
        "source_env": _detect_env(),
    }


def _git_diff_file(request: Request) -> dict[str, Any]:
    filepath = request.query_params.get("path", "")
    if not filepath:
        return {"ok": False, "error": "path parameter required"}

    ok, output = _run_git(["diff", "--", filepath])
    if not ok:
        ok, output = _run_git(["diff", "--cached", "--", filepath])

    return {
        "ok": ok,
        "path": filepath,
        "diff": output[:50000] if ok else "",
        "truncated": len(output) > 50000 if ok else False,
        "source_env": _detect_env(),
        "error": output if not ok else "",
    }


# ---------------------------------------------------------------------------
# Test results
# ---------------------------------------------------------------------------

_TEST_RESULTS_PATH = os.path.join(_UMH_DATA, "workspace", "last_test_result.json")


def _test_results(request: Request) -> dict[str, Any]:
    if os.path.exists(_TEST_RESULTS_PATH):
        try:
            with open(_TEST_RESULTS_PATH) as f:
                data = json.load(f)
            return {"ok": True, "has_results": True, "source_env": _detect_env(), **data}
        except (json.JSONDecodeError, OSError):
            pass

    return {
        "ok": True,
        "has_results": False,
        "source_env": _detect_env(),
        "recommended_command": "python3 -m pytest tests/ -v --tb=short",
        "message": "No test results available. Run the recommended command to generate results.",
    }


# ---------------------------------------------------------------------------
# Execution logs
# ---------------------------------------------------------------------------

def _execution_logs(request: Request) -> dict[str, Any]:
    limit = int(request.query_params.get("limit", "50"))
    limit = min(limit, 200)

    logs: list[dict[str, Any]] = []

    journal_path = os.path.join(_UMH_DATA, "organism", "execution_journal.jsonl")
    if os.path.exists(journal_path):
        try:
            with open(journal_path) as f:
                lines = f.readlines()
            for line in lines[-limit:]:
                line = line.strip()
                if line:
                    try:
                        logs.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
        except OSError:
            pass

    events_path = os.path.join(_UMH_DATA, "organism", "events.jsonl")
    if os.path.exists(events_path) and len(logs) < limit:
        try:
            with open(events_path) as f:
                lines = f.readlines()
            remaining = limit - len(logs)
            for line in lines[-remaining:]:
                line = line.strip()
                if line:
                    try:
                        entry = json.loads(line)
                        entry["_source"] = "events"
                        logs.append(entry)
                    except json.JSONDecodeError:
                        continue
        except OSError:
            pass

    return {
        "ok": True,
        "count": len(logs),
        "logs": logs,
        "source_env": _detect_env(),
        "sources": ["execution_journal.jsonl", "events.jsonl"],
    }


# ---------------------------------------------------------------------------
# Proof / preview artifacts
# ---------------------------------------------------------------------------

_PROOF_DIR = os.path.join(_UMH_DATA, "workspace", "proof")


def _proof_artifacts(request: Request) -> dict[str, Any]:
    artifacts: list[dict[str, Any]] = []

    if os.path.isdir(_PROOF_DIR):
        try:
            for name in sorted(os.listdir(_PROOF_DIR))[-20:]:
                fpath = os.path.join(_PROOF_DIR, name)
                if os.path.isfile(fpath):
                    stat = os.stat(fpath)
                    artifacts.append({
                        "name": name,
                        "path": fpath,
                        "size": stat.st_size,
                        "modified": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
                        "type": _classify_proof(name),
                    })
        except OSError:
            pass

    playwright_available = os.path.exists(os.path.join(_REPO_ROOT, "skills", "tools", "playwright"))

    return {
        "ok": True,
        "count": len(artifacts),
        "artifacts": artifacts,
        "proof_dir": _PROOF_DIR,
        "playwright_available": playwright_available,
        "console_capture_available": False,
        "console_capture_blocker": "Console log capture requires Playwright MCP connection — not wired for headless VPS mode yet",
        "source_env": _detect_env(),
    }


def _classify_proof(name: str) -> str:
    lower = name.lower()
    if lower.endswith((".png", ".jpg", ".jpeg", ".webp")):
        return "screenshot"
    if lower.endswith(".json"):
        return "metadata"
    if lower.endswith(".md"):
        return "report"
    if lower.endswith(".html"):
        return "html_snapshot"
    return "other"


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

def _health_check(request: Request) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []

    ok_api, _ = _run_git(["rev-parse", "HEAD"])
    checks.append({
        "name": "git_repo",
        "status": "reachable" if ok_api else "unreachable",
        "last_check": datetime.now(tz=timezone.utc).isoformat(),
    })

    cockpit_url = os.environ.get("COCKPIT_HEALTH_URL", "")
    if cockpit_url:
        try:
            import urllib.request
            with urllib.request.urlopen(cockpit_url, timeout=5) as resp:
                checks.append({
                    "name": "cockpit_app",
                    "status": "reachable" if resp.status == 200 else "error",
                    "last_check": datetime.now(tz=timezone.utc).isoformat(),
                    "http_status": resp.status,
                })
        except Exception as e:
            checks.append({
                "name": "cockpit_app",
                "status": "unreachable",
                "last_check": datetime.now(tz=timezone.utc).isoformat(),
                "error": str(e),
            })
    else:
        checks.append({
            "name": "cockpit_app",
            "status": "unconfigured",
            "last_check": datetime.now(tz=timezone.utc).isoformat(),
            "message": "Set COCKPIT_HEALTH_URL env var to enable",
        })

    docker_ok = False
    try:
        result = gated_subprocess_run(
            ["docker", "ps", "--format", "{{.Names}}\t{{.Status}}"],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode == 0:
            docker_ok = True
            containers: list[dict[str, str]] = []
            for line in result.stdout.strip().splitlines():
                parts = line.split("\t", 1)
                if len(parts) == 2:
                    containers.append({"name": parts[0], "status": parts[1]})
            checks.append({
                "name": "docker",
                "status": "reachable",
                "last_check": datetime.now(tz=timezone.utc).isoformat(),
                "containers": containers,
            })
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        pass

    if not docker_ok:
        checks.append({
            "name": "docker",
            "status": "unreachable",
            "last_check": datetime.now(tz=timezone.utc).isoformat(),
        })

    mesh_path = os.path.join(_DATA_ROOT, "runtime", "mesh_nodes.json")
    if os.path.exists(mesh_path):
        try:
            with open(mesh_path) as f:
                nodes = json.load(f)
            checks.append({
                "name": "mesh_nodes",
                "status": "reachable",
                "node_count": len(nodes) if isinstance(nodes, list) else 0,
                "last_check": datetime.now(tz=timezone.utc).isoformat(),
            })
        except (json.JSONDecodeError, OSError):
            checks.append({"name": "mesh_nodes", "status": "unavailable",
                           "last_check": datetime.now(tz=timezone.utc).isoformat()})
    else:
        checks.append({"name": "mesh_nodes", "status": "unavailable",
                       "last_check": datetime.now(tz=timezone.utc).isoformat()})

    all_reachable = all(c.get("status") in ("reachable", "unconfigured") for c in checks)

    return {
        "ok": True,
        "overall": "healthy" if all_reachable else "degraded",
        "checks": checks,
        "source_env": _detect_env(),
    }


# ---------------------------------------------------------------------------
# Trace linkage
# ---------------------------------------------------------------------------

def _trace_linkage(request: Request) -> dict[str, Any]:
    trace_id = request.query_params.get("trace_id", "")
    work_packet_id = request.query_params.get("work_packet_id", "")

    links: dict[str, Any] = {
        "trace_id": trace_id,
        "work_packet_id": work_packet_id,
        "execution_log": None,
        "test_result": None,
        "diff": None,
        "proof": None,
        "resume_state": None,
    }

    if trace_id:
        journal_path = os.path.join(_UMH_DATA, "organism", "execution_journal.jsonl")
        if os.path.exists(journal_path):
            try:
                with open(journal_path) as f:
                    for line in f:
                        if trace_id in line:
                            try:
                                entry = json.loads(line)
                                links["execution_log"] = entry
                                break
                            except json.JSONDecodeError:
                                continue
            except OSError:
                pass

    if work_packet_id:
        wp_path = os.path.join(_UMH_DATA, "universal_work", "work_packets.jsonl")
        if os.path.exists(wp_path):
            try:
                with open(wp_path) as f:
                    for line in f:
                        if work_packet_id in line:
                            try:
                                entry = json.loads(line)
                                links["work_packet"] = entry
                                break
                            except json.JSONDecodeError:
                                continue
            except OSError:
                pass

    from substrate.workstation.checkpoint import CheckpointManager
    mgr = CheckpointManager()
    latest = mgr.latest()
    if latest:
        links["resume_state"] = latest.to_dict()

    return {"ok": True, "links": links, "source_env": _detect_env()}


# ---------------------------------------------------------------------------
# Remote node file browsing (SSH proxy to mesh nodes)
# ---------------------------------------------------------------------------

# SSH target for the Windows/executor node — from env, never a hardcoded
# account/IP (see .claude/rules/device-naming.md). Empty disables SSH proxy.
_WINDOWS_SSH = os.environ.get("UMH_WINDOWS_SSH", "")
_MESH_SSH_KEY = "/run/secrets/mesh_key"
_SSH_TIMEOUT = 8
_WINDOWS_ALLOWED_ROOT = "C:\\"
_SAFE_PATH_RE = re.compile(r"^[Cc]:\\([A-Za-z0-9_.\- \\]*)?$")


def _validate_windows_path(path: str) -> str | None:
    """Validate a Windows path. Returns error string or None if ok."""
    if ".." in path:
        return "path traversal blocked"
    if not _SAFE_PATH_RE.match(path):
        return "invalid path characters"
    return None


_MESH_KNOWN_HOSTS = "/root/.ssh/known_hosts"


def _ssh_cmd(cmd: str) -> tuple[bool, str]:
    ssh_args = ["ssh", "-o", "ConnectTimeout=5", "-o", "StrictHostKeyChecking=accept-new"]
    if os.path.exists(_MESH_SSH_KEY):
        ssh_args += ["-i", _MESH_SSH_KEY]
    if os.path.exists(_MESH_KNOWN_HOSTS):
        ssh_args += ["-o", f"UserKnownHostsFile={_MESH_KNOWN_HOSTS}"]
    ssh_args += [_WINDOWS_SSH, cmd]
    try:
        result = gated_subprocess_run(
            ssh_args, capture_output=True, text=True, timeout=_SSH_TIMEOUT,
        )
        return result.returncode == 0, result.stdout
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError) as e:
        return False, str(e)


def _get_windows_browse_root() -> str:
    """Return Windows filesystem root for browsing."""
    return "C:\\"


async def _remote_browse(request: Request) -> dict[str, Any]:
    node = request.query_params.get("node", "windows")
    path = request.query_params.get("path", "")
    if not path:
        path = _get_windows_browse_root()
    if node != "windows":
        return {"ok": False, "error": f"Unknown remote node: {node}"}
    err = _validate_windows_path(path)
    if err:
        return {"ok": False, "error": err, "source_env": "windows", "path": path}
    safe_path = path.replace("'", "''")
    ok, output = _ssh_cmd(
        f"powershell -Command \"Get-ChildItem -LiteralPath '{safe_path}'"
        " | ForEach-Object { $_.Name + '|'"
        " + $(if($_.PSIsContainer){'directory'}else{'file'})"
        " + '|' + $_.Length }\""
    )
    if not ok:
        return {"ok": False, "error": output[:500], "source_env": "windows", "path": path}
    entries = []
    for line in output.strip().splitlines():
        parts = line.strip().split("|")
        if len(parts) >= 2:
            name = parts[0]
            etype = parts[1]
            size = int(parts[2]) if len(parts) > 2 and parts[2].isdigit() else 0
            child_path = path.rstrip("\\") + "\\" + name
            entries.append({"name": name, "path": child_path, "type": etype, "size": size, "source_env": "windows"})
    return {"ok": True, "path": path, "source_env": "windows", "entries": entries, "error": ""}


def _remote_read_file(request: Request) -> dict[str, Any]:
    node = request.query_params.get("node", "windows")
    path = request.query_params.get("path", "")
    if not path:
        return {"ok": False, "error": "path required"}
    if node != "windows":
        return {"ok": False, "error": f"Unknown remote node: {node}"}
    err = _validate_windows_path(path)
    if err:
        return {"ok": False, "error": err, "path": path}
    safe_path = path.replace("'", "''")
    ok, output = _ssh_cmd(f"powershell -Command \"Get-Content -LiteralPath '{safe_path}' -Raw -ErrorAction Stop\"")
    if not ok:
        return {"ok": False, "error": output[:500], "path": path}
    return {"ok": True, "path": path, "content": output, "source_env": "windows"}


async def _remote_write_file(request: Request) -> dict[str, Any]:
    body = await request.json()
    node: str = body.get("node", "windows")
    path: str = body.get("path", "")
    content: str = body.get("content", "")
    if not path:
        return {"ok": False, "error": "path required"}
    if node != "windows":
        return {"ok": False, "error": f"Unknown remote node: {node}"}
    err = _validate_windows_path(path)
    if err:
        return {"ok": False, "error": err, "path": path}

    def _do_remote_write():
        import base64
        encoded = base64.b64encode(content.encode("utf-8")).decode("ascii")
        safe_path = path.replace("'", "''")
        ok, output = _ssh_cmd(
            f"powershell -Command \"[System.IO.File]::WriteAllBytes("
            f"'{safe_path}', [Convert]::FromBase64String('{encoded}'))\""
        )
        if not ok:
            return output[:500], False
        return f"remote file written: {path}", True

    resp = governed_mutation(
        mutation_name="filesystem_write",
        intent=f"write remote file: {node}:{path}",
        execute_fn=_do_remote_write,
        source="cockpit",
    )
    return resp.to_http_dict()


def _mesh_nodes_status(request: Request) -> dict[str, Any]:
    registry_path = os.path.join(_REPO_ROOT, "infra", "device_registry.json")
    mesh_path = os.path.join(_DATA_ROOT, "runtime", "mesh_nodes.json")
    registry: list[dict[str, Any]] = []
    heartbeats: dict[str, dict[str, Any]] = {}
    try:
        with open(registry_path) as f:
            registry = json.load(f)
    except (json.JSONDecodeError, OSError, FileNotFoundError):
        pass
    try:
        with open(mesh_path) as f:
            for n in json.load(f):
                heartbeats[n.get("id", "")] = n
    except (json.JSONDecodeError, OSError, FileNotFoundError):
        pass
    nodes = []
    for dev in registry:
        mesh_id = dev.get("mesh_node_id", "")
        hb = heartbeats.get(mesh_id, {})
        status = "online" if dev.get("always_online") else hb.get("status", "offline")
        nodes.append({
            "id": dev["id"],
            "name": dev.get("display_name", dev.get("tailscale_name", dev["id"])),
            "os": dev.get("os", ""),
            "status": status,
            "ip": dev.get("tailscale_ip", ""),
            "device_type": dev.get("device_type", ""),
            "last_heartbeat": hb.get("last_heartbeat", ""),
        })
    return {"ok": True, "nodes": nodes}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _detect_env() -> str:
    system = platform.system().lower()
    if system == "linux":
        if os.path.exists("/.dockerenv"):
            return "container"
        return "vps"
    if system == "windows":
        return "windows"
    return system
