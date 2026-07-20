"""Cockpit bootstrap routes — extracted from cockpit_core_routes.py.

Phase 0.3 route split. UMH transport layer.
"""

from __future__ import annotations

import asyncio
import concurrent.futures
import json
import logging
import os
import re
import time
from pathlib import Path
from typing import Any

import psutil
from fastapi import Depends, Request
from fastapi.responses import JSONResponse

from transports.api.governed import governed_mutation

logger = logging.getLogger(__name__)

_ROOT = Path(os.getenv("UMH_ROOT", "/opt/OS"))
TRACE_STORE = _ROOT / "data" / "umh" / "traces" / "traces.jsonl"
_SAFE_PATH_RE = re.compile(r"^[A-Za-z]:\\[A-Za-z0-9_\\\-. ]*$")


def register_bootstrap_routes(router, _require_operator_role, helpers):
    """Register bootstrap and config routes onto the given router."""
    _build_node_metrics = helpers["_build_node_metrics"]
    _read_jsonl = helpers["_read_jsonl"]
    _get_organism = helpers["_get_organism"]

    @router.get("/bootstrap")
    async def bootstrap():
        """Aggregate boot-critical data in one response.

        Replaces ~15 parallel GET requests the cockpit fires on page load.
        Each source is independently faulted — partial data is fine.
        Runs blocking work in a thread to avoid stalling the event loop,
        with a 15-second ceiling so Fly never 504s.
        """
        try:
            return await asyncio.wait_for(
                asyncio.to_thread(_bootstrap_sync),
                timeout=15,
            )
        except asyncio.TimeoutError:
            return {"ok": False, "ts": "", "_errors": ["bootstrap timed out after 15s"]}

    def _fetch_windows_files() -> dict[str, Any]:
        """SSH to Beast for filesystem root listing — isolated so it can be deadline-capped."""
        from transports.api.cockpit_workspace_routes import _ssh_cmd

        _win_root = "C:\\"
        if not _SAFE_PATH_RE.match(_win_root):
            logger.warning("Rejected unsafe Windows path from device registry: %s", _win_root)
            return {"ok": False, "entries": []}
        _win_root_escaped = _win_root.replace("'", "''")
        _win_ok, _win_out = _ssh_cmd(
            f"powershell -Command \"Get-ChildItem -LiteralPath '{_win_root_escaped}'"
            " | ForEach-Object { $_.Name + '|'"
            " + $(if($_.PSIsContainer){'directory'}else{'file'})"
            " + '|' + $_.Length }\""
        )
        _win_entries: list[dict[str, Any]] = []
        if _win_ok:
            for _line in _win_out.strip().splitlines():
                _parts = _line.strip().split("|")
                if len(_parts) >= 2:
                    _win_entries.append(
                        {
                            "name": _parts[0],
                            "path": _win_root + "\\" + _parts[0],
                            "type": _parts[1],
                            "source_env": "windows",
                        }
                    )
        return {"ok": _win_ok, "entries": _win_entries}

    def _bootstrap_sync() -> dict[str, Any]:
        """Fast-tier bootstrap — local reads only, no SSH, no slow I/O.

        Subsystem reads run in parallel (4 threads) to cut wall-clock from
        5-15s (sequential) to ~2-4s (bounded by slowest subsystem).
        """
        import datetime as _dt

        errors: list[str] = []
        result: dict[str, Any] = {
            "ok": True,
            "ts": _dt.datetime.now(_dt.timezone.utc).isoformat(),
        }

        def _fetch_config() -> dict[str, Any]:
            from substrate.sockets.config_port import get_all_config

            return get_all_config()

        def _fetch_pulse() -> dict[str, Any]:
            node_metrics = _build_node_metrics()
            vps = node_metrics.get("vps", {})
            traces = _read_jsonl(TRACE_STORE)
            pending_traces = sum(1 for t in traces[-500:] if t.get("status") == "pending")
            uptime = int(time.time() - psutil.boot_time())
            daemon = _get_organism()
            active_agents = 0
            pending_approvals_count = 0
            if daemon is not None:
                active_agents = sum(
                    1 for a in daemon.advisor.list_agents() if a.get("status") != "offline"
                )
                pending_approvals_count = daemon.approval_store.pending_count()
            return {
                "uptime": uptime,
                "cpu_percent": vps.get("cpu", 0),
                "memory_percent": vps.get("memory", 0),
                "disk_percent": vps.get("disk", 0),
                "active_agents": active_agents,
                "pending_tasks": pending_traces,
                "pending_approvals": pending_approvals_count,
                "trace_rate": round(len(traces) / max(uptime / 3600, 1), 1),
                "node_metrics": node_metrics,
            }

        def _fetch_organism() -> dict[str, Any]:
            daemon = _get_organism()
            if daemon is not None:
                return {
                    "running": True,
                    "agent_count": len(daemon.advisor.list_agents()),
                    "workcell_count": len(getattr(daemon, "workcells", [])),
                }
            return {"running": False}

        def _fetch_mode_composite() -> dict[str, Any]:
            from substrate.workstation.mode_resolver import resolve_composite_mode

            return resolve_composite_mode()

        def _fetch_continuity() -> dict[str, Any]:
            try:
                from substrate.workstation.continuity_engine import ContinuityEngine

                engine = ContinuityEngine()
                composite = engine.get_composite_state()
                return composite.to_dict()
            except Exception:
                from transports.api.cockpit_workstation_control_routes import (
                    _get_continuity_machine,
                )

                machine = _get_continuity_machine()
                return {
                    "current_state": machine.current_state.value,
                    "valid_transitions": [s.value for s in machine.valid_transitions()],
                }

        def _fetch_command_center() -> dict[str, Any]:
            from transports.api.cockpit_command_center_routes import (
                _load_approvals,
                _load_blocked_packets,
                _load_journal_recent,
                _load_work_packets,
                _load_workcell_heartbeats,
            )

            heartbeats = _load_workcell_heartbeats()
            pending = _load_approvals(status_filter="pending")
            packets = _load_work_packets(limit=100)
            blocked = _load_blocked_packets()
            journal = _load_journal_recent(50)

            active_agents = [h for h in heartbeats if h.get("status") == "active"]
            idle_agents = [h for h in heartbeats if h.get("status") == "idle"]
            completed = [j for j in journal if j.get("phase") == "EXECUTION_COMPLETED"]
            failed = [
                j for j in journal if j.get("phase") in ("EXECUTION_FAILED", "VERIFICATION_FAILED")
            ]
            by_status: dict[str, int] = {}
            for p in packets:
                s = p.get("status", "unknown")
                by_status[s] = by_status.get(s, 0) + 1
            executing = [p for p in packets if p.get("status") in ("executing", "delegated")]
            next_packet = None
            ready = [
                p for p in packets if p.get("status") in ("approved", "ready_for_review", "planned")
            ]
            if ready:
                ready.sort(key=lambda p: p.get("leverage_score", 0), reverse=True)
                next_packet = {
                    "packet_id": ready[0].get("packet_id", ""),
                    "title": ready[0].get("title", ""),
                    "status": ready[0].get("status", ""),
                    "leverage_score": ready[0].get("leverage_score", 0),
                }

            from substrate.state.runtime_paths import runtime_state_dir

            checkpoint_path = str(
                runtime_state_dir("organism", create=False)
                / "workstation_state"
                / "latest_checkpoint.json"
            )
            checkpoint_detail: dict[str, Any] = {}
            cc_continuity = "active"
            if os.path.exists(checkpoint_path):
                try:
                    with open(checkpoint_path) as f:
                        checkpoint_detail = json.load(f)
                    cc_continuity = checkpoint_detail.get(
                        "continuity_state",
                        checkpoint_detail.get("new_continuity_state", "active"),
                    )
                except (json.JSONDecodeError, OSError):
                    pass

            return {
                "command_center": {
                    "active_workcells": len(active_agents),
                    "idle_workcells": len(idle_agents),
                    "pending_approvals": len(pending),
                },
                "command_center_summary": {
                    "ok": True,
                    "checkpoint": {
                        "last_checkpoint_id": checkpoint_detail.get("checkpoint_id", ""),
                        "continuity_state": cc_continuity,
                        "lifecycle_mode": checkpoint_detail.get("lifecycle_mode", ""),
                        "active_node": checkpoint_detail.get("active_node", ""),
                        "active_environment": checkpoint_detail.get("active_environment", ""),
                        "open_loops": checkpoint_detail.get("open_loops", []),
                        "recommended_next_action": checkpoint_detail.get(
                            "recommended_next_action", ""
                        ),
                        "transition_reason": checkpoint_detail.get("transition_reason", ""),
                    },
                    "what_is_happening": {
                        "continuity_state": cc_continuity,
                        "active_agents": len(active_agents),
                        "idle_agents": len(idle_agents),
                        "total_agents": len(heartbeats),
                        "executing_packets": len(executing),
                    },
                    "who_is_working": [
                        {
                            "agent_id": h.get("workcell_id", ""),
                            "role": h.get("role", ""),
                            "status": h.get("status", ""),
                        }
                        for h in heartbeats
                    ],
                    "what_is_blocked": {
                        "count": len(blocked),
                        "items": [
                            {
                                "id": b.get("packet_id", ""),
                                "title": b.get("title", ""),
                                "blockers": b.get("blockers", []),
                            }
                            for b in blocked[:5]
                        ],
                    },
                    "what_needs_approval": {
                        "count": len(pending),
                        "items": [
                            {
                                "id": a.get("id", ""),
                                "title": a.get("title", ""),
                                "risk_level": a.get("risk_level", ""),
                            }
                            for a in pending[:5]
                        ],
                    },
                    "what_finished": {
                        "recent_completed": len(completed),
                        "latest": completed[-1].get("details", {}).get("intent", "")
                        if completed
                        else "",
                    },
                    "what_failed": {
                        "recent_failed": len(failed),
                        "latest": failed[-1]
                        .get("details", {})
                        .get("error", failed[-1].get("source", ""))
                        if failed
                        else "",
                    },
                    "what_should_resume_next": next_packet,
                    "packets_by_status": by_status,
                    "total_packets": len(packets),
                    "source_env": os.environ.get("UMH_ENV", "container"),
                    "node": os.uname().nodename,
                },
                "approvals": [
                    {
                        "id": a.get("id", ""),
                        "title": a.get("title", ""),
                        "risk_level": a.get("risk_level", ""),
                        "status": a.get("status", ""),
                    }
                    for a in pending[:10]
                ],
            }

        def _fetch_overnight() -> dict[str, Any]:
            from substrate.workstation.overnight_queue import OvernightQueue

            queue = OvernightQueue()
            return queue.morning_summary()

        def _fetch_mesh_nodes() -> dict[str, Any]:
            nm = _build_node_metrics()
            _repo = os.environ.get("UMH_ROOT", "/opt/OS")
            _registry_path = os.path.join(_repo, "infra", "device_registry.json")
            _mesh_hb_path = os.path.join(_repo, "data", "runtime", "mesh_nodes.json")
            from substrate.state.runtime_paths import runtime_state_path

            _mesh_metrics_path = str(
                runtime_state_path("organism", "mesh_metrics.json", create_parent=False)
            )
            _registry: list[dict[str, Any]] = []
            _hb_map: dict[str, dict[str, Any]] = {}
            try:
                with open(_registry_path) as f:
                    _registry = json.load(f)
            except (json.JSONDecodeError, OSError, FileNotFoundError):
                pass

            # Read both heartbeat sources, merge fresher data per node
            _hb_sources: list[str] = [_mesh_hb_path, _mesh_metrics_path]
            for _src in _hb_sources:
                try:
                    with open(_src) as f:
                        _raw = json.load(f)
                    # mesh_metrics.json is a dict keyed by node_id;
                    # mesh_nodes.json is a list of dicts with "id" field
                    if isinstance(_raw, dict):
                        _items = [
                            {**v, "id": k} if isinstance(v, dict) else {"id": k}
                            for k, v in _raw.items()
                        ]
                    elif isinstance(_raw, list):
                        _items = _raw
                    else:
                        _items = []
                    for _n in _items:
                        _nid = _n.get("id", _n.get("node_id", ""))
                        if not _nid:
                            continue
                        existing = _hb_map.get(_nid)
                        if existing is None:
                            _hb_map[_nid] = _n
                        else:
                            new_hb = _n.get("last_heartbeat", _n.get("timestamp", ""))
                            old_hb = existing.get("last_heartbeat", existing.get("timestamp", ""))
                            if new_hb > old_hb:
                                _hb_map[_nid] = _n
                except (json.JSONDecodeError, OSError, FileNotFoundError):
                    pass
            _mesh_list = []
            for _dev in _registry:
                _mid = _dev.get("mesh_node_id", "")
                _hb = _hb_map.get(_mid, {})
                _st = "online" if _dev.get("always_online") else _hb.get("status", "offline")
                _mesh_list.append(
                    {
                        "id": _dev["id"],
                        "name": _dev.get("display_name", _dev.get("tailscale_name", _dev["id"])),
                        "os": _dev.get("os", ""),
                        "status": _st,
                        "ip": _dev.get("tailscale_ip", ""),
                        "device_type": _dev.get("device_type", ""),
                        "last_heartbeat": _hb.get("last_heartbeat", ""),
                    }
                )
            return {"mesh": {"node_count": len(nm)}, "mesh_nodes": _mesh_list}

        def _fetch_dex() -> dict[str, Any]:
            try:
                from transports.api.cockpit_chat_routes import get_dex_conversation

                conv = get_dex_conversation()
            except (ImportError, AttributeError):
                conv = None
            avail = conv is not None
            return {"dex_available": avail, "chat_available": avail}

        fetchers: dict[str, Any] = {
            "config": _fetch_config,
            "pulse": _fetch_pulse,
            "organism": _fetch_organism,
            "mode_composite": _fetch_mode_composite,
            "continuity": _fetch_continuity,
            "command_center": _fetch_command_center,
            "overnight": _fetch_overnight,
            "mesh_nodes": _fetch_mesh_nodes,
            "dex": _fetch_dex,
        }

        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
            futures = {key: pool.submit(fn) for key, fn in fetchers.items()}
            for key, future in futures.items():
                try:
                    val = future.result(timeout=10)
                    if key == "command_center":
                        result["command_center"] = val["command_center"]
                        result["command_center_summary"] = val["command_center_summary"]
                        result["approvals"] = val["approvals"]
                    elif key == "mesh_nodes":
                        result["mesh"] = val["mesh"]
                        result["mesh_nodes"] = val["mesh_nodes"]
                    elif key == "dex":
                        result["dex_available"] = val["dex_available"]
                        result["chat_available"] = val["chat_available"]
                    else:
                        result[key] = val
                except Exception as e:
                    errors.append(f"{key}: {e}")
                    if key == "command_center":
                        result["command_center"] = {}
                        result["command_center_summary"] = {}
                        result["approvals"] = []
                    elif key == "mesh_nodes":
                        result["mesh"] = {"node_count": 0}
                        result["mesh_nodes"] = []
                    elif key == "dex":
                        result["dex_available"] = False
                        result["chat_available"] = False
                    elif key == "organism":
                        result[key] = {"running": False}
                    else:
                        result[key] = {}

        result["_errors"] = errors
        if errors:
            result["ok"] = False
        return result

    @router.get("/bootstrap/slow")
    async def bootstrap_slow():
        """Slow-tier bootstrap — file trees and workstation nodes (SSH, browse)."""
        try:
            return await asyncio.wait_for(
                asyncio.to_thread(_bootstrap_slow_sync),
                timeout=15,
            )
        except asyncio.TimeoutError:
            return {"ok": False, "_errors": ["slow bootstrap timed out"]}

    def _bootstrap_slow_sync() -> dict[str, Any]:
        """Slow-tier: VPS files, Windows files (SSH), workstation nodes."""
        errors: list[str] = []
        result: dict[str, Any] = {"ok": True}

        win_executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        win_future = win_executor.submit(_fetch_windows_files)

        try:
            from transports.api.cockpit_workstation_control_routes import (
                _read_mesh_snapshot,
                _read_vps_node,
            )

            vps_node = _read_vps_node()
            mesh_snapshot = _read_mesh_snapshot()
            result["workstation_nodes"] = {
                "ok": True,
                "nodes": [vps_node] + mesh_snapshot,
                "count": 1 + len(mesh_snapshot),
                "vps": vps_node,
                "remote_nodes": mesh_snapshot,
            }
        except Exception as e:
            errors.append(f"workstation_nodes: {e}")
            result["workstation_nodes"] = {}

        try:
            from substrate.workstation.file_browser import browse_directory

            result["vps_files"] = browse_directory("/").to_dict()
        except Exception as e:
            errors.append(f"vps_files: {e}")
            result["vps_files"] = {}

        try:
            result["windows_files"] = win_future.result(timeout=10)
        except concurrent.futures.TimeoutError:
            errors.append("windows_files: SSH timed out")
            result["windows_files"] = {"ok": False, "entries": []}
        except Exception as e:
            errors.append(f"windows_files: {e}")
            result["windows_files"] = {"ok": False, "entries": []}
        finally:
            win_executor.shutdown(wait=False)

        result["_errors"] = errors
        if errors:
            result["ok"] = False
        return result

    @router.get("/config")
    def config_get():
        """Get resolved config (ai_name, timezone, theme, etc.)."""
        try:
            from substrate.sockets.config_port import get_all_config

            return get_all_config()
        except Exception as e:
            logger.error("config_get failed: %s", e)
            return {}

    @router.patch("/config", dependencies=[Depends(_require_operator_role)])
    async def config_patch(request: Request):
        """Set a config value. Body: {key, value, layer?}."""
        body = await request.json()
        key = body.get("key")
        value = body.get("value")
        layer = body.get("layer", "system")
        if not key:
            return JSONResponse({"error": "key is required"}, status_code=400)
        if value is None:
            return JSONResponse({"error": "value is required"}, status_code=400)

        from substrate.state.config.config_store import VALID_KEYS

        if key not in VALID_KEYS:
            return JSONResponse({"error": f"invalid config key: {key}"}, status_code=400)

        def _do_config_patch():
            try:
                from substrate.sockets.config_port import set_config

                set_config(key, value, layer=layer)
                return f"config {key} updated", True
            except Exception as e:
                return str(e), False

        resp = governed_mutation(
            mutation_name="config_update",
            intent=f"update config: {key}",
            execute_fn=_do_config_patch,
            source="cockpit",
        )
        return resp.to_http_dict()
