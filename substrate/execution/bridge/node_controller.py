"""
NodeController — unified routing brain for task→node dispatch.

Single decision engine that consolidates task-to-node routing.
Stateless: every call re-reads current state from the existing
singletons (NodeRegistry, StationPresenceStore, OperatorSessionStore).

Consults:
  - capability_routing.py for task→capability inference
  - nodes.py for node health and capability matching
  - station_presence.py for local availability
  - operator_session.py for operator preferences

Returns a RoutingDecision that tells callers:
  - which node to target
  - which transport to prefer (http, file_bus, vps_direct)
  - why the decision was made
  - whether fallback should be attempted on failure

Design rules (mirror substrate conventions):
- Stateless — no persistent state inside the controller.
- Deterministic — no LLM calls. Pure heuristic + registry lookup.
- Best-effort — routing failures return safe defaults, never raise.
- Additive only — never imported on the hot path.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from substrate.execution.bridge.operator_session import OperatorSession
    from substrate.execution.bridge.task_system import Task


# ─── Enums ───────────────────────────────────────────────────────────────────


class TransportPreference(str, Enum):
    """Which transport layer to attempt first."""

    HTTP = "http"  # aiohttp local agent
    FILE_BUS = "file_bus"  # existing StationBus file transport
    VPS_DIRECT = "vps_direct"  # execute on the VPS itself


class RoutingReason(str, Enum):
    """Why a routing decision was made — for logs and debugging."""

    LOCAL_PREFERRED_HTTP_UP = "local_preferred_http_up"
    LOCAL_PREFERRED_HTTP_DOWN_FILE_BUS = "local_preferred_http_down_file_bus"
    LOCAL_NEEDED_FOR_CAPABILITY = "local_needed_for_capability"
    VPS_PREFERRED = "vps_preferred"
    VPS_FALLBACK_LOCAL_UNAVAILABLE = "vps_fallback_local_unavailable"
    VPS_DEFAULT = "vps_default"
    OPERATOR_OVERRIDE_LOCAL = "operator_override_local"
    OPERATOR_OVERRIDE_VPS = "operator_override_vps"


# ─── Result ──────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class RoutingDecision:
    """Immutable routing decision with full rationale."""

    target_node_id: str
    transport: TransportPreference
    reason: RoutingReason
    fallback_transport: Optional[TransportPreference] = None
    fallback_node_id: Optional[str] = None
    detail: str = ""

    def to_dict(self) -> dict:
        d: dict = {
            "target_node_id": self.target_node_id,
            "transport": self.transport.value,
            "reason": self.reason.value,
            "detail": self.detail,
        }
        if self.fallback_transport:
            d["fallback_transport"] = self.fallback_transport.value
        if self.fallback_node_id:
            d["fallback_node_id"] = self.fallback_node_id
        return d


# ─── Constants ───────────────────────────────────────────────────────────────

VPS_NODE_ID = "vps-primary"
LOCAL_NODE_ID = "antony-workstation"

# Capabilities that require local execution
_LOCAL_REQUIRED_CAPS = frozenset(
    {
        "audio_output",
        "text_to_speech",
        "local_filesystem",
        "url_open",
        "app_launch",
        "scene_bootstrap",
        "window_focus",
    }
)


def _log(msg: str) -> None:
    print(f"[substrate.node_controller] {msg}", file=sys.stderr)


# ─── Health Checks ───────────────────────────────────────────────────────────


def _is_local_node_online() -> bool:
    """Check if the local workstation node is registered and online."""
    try:
        from substrate.execution.bridge.nodes import NodeRegistry, NodeStatus

        node = NodeRegistry.default().get(LOCAL_NODE_ID)
        return node is not None and node.status == NodeStatus.ONLINE
    except Exception:  # noqa: BLE001
        return False


def _is_http_transport_available() -> bool:
    """Probe whether the local aiohttp transport is accepting connections.

    Quick connect-and-close on the expected port. Returns False on any error.
    """
    import socket

    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(0.5)
        result = sock.connect_ex(("127.0.0.1", 7600))
        sock.close()
        return result == 0
    except Exception:  # noqa: BLE001
        return False


def _is_local_available_via_presence() -> bool:
    """Check station_presence for local availability."""
    try:
        from substrate.execution.bridge.station_presence import StationPresenceStore

        presence = StationPresenceStore.default().get()
        return presence.local_available
    except Exception:  # noqa: BLE001
        return False


def get_node_health_summary() -> dict:
    """Collect a health snapshot for all registered nodes.

    Returns a dict suitable for inclusion in day briefings.
    """
    summary: dict = {
        "total_nodes": 0,
        "online_nodes": 0,
        "local_online": False,
        "http_transport_up": False,
        "nodes": [],
    }
    try:
        from substrate.execution.bridge.nodes import NodeRegistry, NodeStatus

        registry = NodeRegistry.default()
        all_nodes = registry.all()
        summary["total_nodes"] = len(all_nodes)
        summary["online_nodes"] = sum(
            1 for n in all_nodes if n.status == NodeStatus.ONLINE
        )
        summary["local_online"] = _is_local_node_online()
        summary["http_transport_up"] = _is_http_transport_available()
        summary["nodes"] = [
            {
                "node_id": n.node_id,
                "type": n.node_type.value,
                "status": n.status.value,
                "capabilities": list(n.capabilities),
                "last_seen": n.last_seen,
            }
            for n in all_nodes
        ]
    except Exception as exc:  # noqa: BLE001
        _log(f"health summary failed: {exc}")
    return summary


# ─── Core Routing ────────────────────────────────────────────────────────────


def route(
    *,
    task: Optional["Task"] = None,
    required_capabilities: Optional[set[str]] = None,
    session: Optional["OperatorSession"] = None,
    prefer_local: bool = True,
) -> RoutingDecision:
    """Make a routing decision for a task or capability set.

    Resolution order:
    1. Operator explicit override (session.node_preference == "local" | "vps").
    2. Capability requirement — if task needs local-only caps, route local.
    3. Local preference — if prefer_local and local is online, route local.
    4. VPS fallback — if local unavailable or not preferred.

    Within local routing, transport preference:
    - HTTP if the aiohttp transport is up.
    - File bus if HTTP is down but node is registered.
    - VPS fallback if neither works.

    Args:
        task: Optional task for capability inference.
        required_capabilities: Explicit capability set (used if task is None).
        session: Operator session for preference overrides.
        prefer_local: Default local preference when session is "auto".

    Returns:
        RoutingDecision with target, transport, reason, and fallback info.
    """
    # ── Infer capabilities ──────────────────────────────────────────────────
    caps: set[str] = set(required_capabilities or set())
    if task is not None and not caps:
        try:
            from substrate.execution.bridge.capability_routing import infer_task_capabilities

            inferred = infer_task_capabilities(task)
            caps = {c.value for c in inferred}
        except Exception as exc:  # noqa: BLE001
            _log(f"capability inference failed: {exc}")

    # ── Check operator preference ───────────────────────────────────────────
    node_pref = "auto"
    if session is not None:
        node_pref = getattr(session, "node_preference", "auto") or "auto"

    # ── Check local health ──────────────────────────────────────────────────
    local_online = _is_local_node_online() or _is_local_available_via_presence()
    http_up = _is_http_transport_available() if local_online else False

    # ── Does this task REQUIRE local? ───────────────────────────────────────
    needs_local = bool(caps & _LOCAL_REQUIRED_CAPS)

    # ── Decision logic ──────────────────────────────────────────────────────

    # 1. Explicit operator override
    if node_pref == "local":
        if local_online:
            return _local_decision(
                http_up,
                RoutingReason.OPERATOR_OVERRIDE_LOCAL,
                "operator explicitly chose local",
            )
        # Local requested but unavailable — fall back to VPS
        return _vps_decision(
            RoutingReason.VPS_FALLBACK_LOCAL_UNAVAILABLE,
            "operator chose local but node offline — VPS fallback",
        )

    if node_pref == "vps":
        # Operator explicitly wants VPS — only override for hard local needs
        if needs_local and local_online:
            return _local_decision(
                http_up,
                RoutingReason.LOCAL_NEEDED_FOR_CAPABILITY,
                f"VPS preferred but task needs local caps: {caps & _LOCAL_REQUIRED_CAPS}",
            )
        return _vps_decision(
            RoutingReason.OPERATOR_OVERRIDE_VPS,
            "operator explicitly chose VPS",
        )

    # 2. Auto mode — capability-driven
    if needs_local:
        if local_online:
            return _local_decision(
                http_up,
                RoutingReason.LOCAL_NEEDED_FOR_CAPABILITY,
                f"task requires local caps: {caps & _LOCAL_REQUIRED_CAPS}",
            )
        return _vps_decision(
            RoutingReason.VPS_FALLBACK_LOCAL_UNAVAILABLE,
            f"task needs local caps but node offline: {caps & _LOCAL_REQUIRED_CAPS}",
        )

    # 3. Auto mode — preference-driven
    if prefer_local and local_online:
        return _local_decision(
            http_up,
            RoutingReason.LOCAL_PREFERRED_HTTP_UP
            if http_up
            else RoutingReason.LOCAL_PREFERRED_HTTP_DOWN_FILE_BUS,
            "auto mode, local preferred and available",
        )

    # 4. Default to VPS
    return _vps_decision(
        RoutingReason.VPS_DEFAULT,
        "auto mode, defaulting to VPS",
    )


# ─── Decision Builders ──────────────────────────────────────────────────────


def _local_decision(
    http_up: bool,
    reason: RoutingReason,
    detail: str,
) -> RoutingDecision:
    """Build a local routing decision with transport preference."""
    if http_up:
        return RoutingDecision(
            target_node_id=LOCAL_NODE_ID,
            transport=TransportPreference.HTTP,
            reason=reason,
            fallback_transport=TransportPreference.FILE_BUS,
            fallback_node_id=LOCAL_NODE_ID,
            detail=detail,
        )
    return RoutingDecision(
        target_node_id=LOCAL_NODE_ID,
        transport=TransportPreference.FILE_BUS,
        reason=reason,
        fallback_transport=TransportPreference.VPS_DIRECT,
        fallback_node_id=VPS_NODE_ID,
        detail=detail,
    )


def _vps_decision(reason: RoutingReason, detail: str) -> RoutingDecision:
    """Build a VPS routing decision."""
    return RoutingDecision(
        target_node_id=VPS_NODE_ID,
        transport=TransportPreference.VPS_DIRECT,
        reason=reason,
        detail=detail,
    )


# ─── Exports ─────────────────────────────────────────────────────────────────

__all__ = [
    "TransportPreference",
    "RoutingReason",
    "RoutingDecision",
    "route",
    "get_node_health_summary",
    "VPS_NODE_ID",
    "LOCAL_NODE_ID",
]
