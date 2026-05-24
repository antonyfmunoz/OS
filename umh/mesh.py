"""Device mesh status — view connected nodes and mesh health.

Wraps transports/node_mesh for status display and health monitoring.
The mesh server runs on the VPS; this module queries it for node status
and exposes it through the CLI and interaction loop.
"""

from __future__ import annotations

import logging
import os
import sys
from typing import Any

logger = logging.getLogger(__name__)

sys.path.insert(0, os.environ.get("UMH_ROOT", "/opt/OS"))

UMH_ROOT = os.environ.get("UMH_ROOT", "/opt/OS")
MESH_METRICS_FILE = os.path.join(UMH_ROOT, "data", "umh", "mesh", "metrics.jsonl")


def get_mesh_status() -> dict[str, Any]:
    """Get current mesh status from the node registry."""
    try:
        from transports.node_mesh.registry import NodeRegistry

        registry = NodeRegistry()
        nodes = registry.all_nodes()

        node_list = []
        for node in nodes:
            node_list.append(
                {
                    "node_id": node.node_id,
                    "hostname": node.hostname,
                    "os": node.os,
                    "status": node.status,
                    "capabilities": len(node.capabilities),
                    "heartbeat_age_s": round(node.heartbeat_age_s(), 1),
                    "tailscale_ip": node.tailscale_ip,
                    "daemon_version": node.daemon_version,
                }
            )

        return {
            "online": True,
            "node_count": len(nodes),
            "nodes": node_list,
            "healthy": all(n["status"] == "connected" for n in node_list),
        }
    except ImportError:
        logger.debug("Node mesh registry not available")
    except Exception as exc:
        logger.debug("Mesh status query failed: %s", exc)

    return _status_from_daemon()


def _status_from_daemon() -> dict[str, Any]:
    """Fall back to reading daemon status file for mesh info."""
    from umh.daemon import get_daemon_status

    daemon_status = get_daemon_status()
    mesh_connected = daemon_status.get("mesh_connected", False)

    return {
        "online": mesh_connected,
        "node_count": 1 if mesh_connected else 0,
        "nodes": [],
        "healthy": mesh_connected,
        "source": "daemon_status",
    }


def get_node_count() -> int:
    """Get the number of connected mesh nodes (fast path for status display)."""
    try:
        from transports.node_mesh.registry import NodeRegistry

        return NodeRegistry().node_count()
    except Exception:
        pass

    from umh.daemon import get_daemon_status

    status = get_daemon_status()
    if status.get("mesh_connected"):
        return 1
    return 0


def format_mesh_status() -> str:
    """Format mesh status for display in the interaction loop."""
    status = get_mesh_status()

    if not status.get("online") and not status.get("nodes"):
        return "Mesh: standalone (no nodes connected)"

    lines = ["Device Mesh"]
    lines.append("-" * 40)

    nodes = status.get("nodes", [])
    if not nodes:
        connected = status.get("node_count", 0)
        if connected:
            lines.append(f"  {connected} node(s) connected (details unavailable)")
        else:
            lines.append("  No nodes connected")
    else:
        for n in nodes:
            status_icon = (
                "+" if n["status"] == "connected" else "~" if n["status"] == "degraded" else "-"
            )
            hb = n.get("heartbeat_age_s", 0)
            hb_str = f"{hb:.0f}s ago" if hb < 120 else f"{hb / 60:.0f}m ago"
            lines.append(
                f"  [{status_icon}] {n['hostname']} ({n['os']}) — "
                f"{n['capabilities']} caps, heartbeat {hb_str}"
            )

    health = "healthy" if status.get("healthy") else "degraded"
    lines.append(f"  Overall: {health}")

    return "\n".join(lines)


def show_mesh_status() -> int:
    """Print mesh status. Returns 0."""
    print()
    print(format_mesh_status())
    print()
    return 0
