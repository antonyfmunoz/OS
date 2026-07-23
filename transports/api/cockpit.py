"""Cockpit API endpoints — serves real data from UMH stores to the frontend.

All endpoints are prefixed /api/umh/ and registered via include_router
in operator_api.py (production) and app.py (substrate runtime).
"""

from __future__ import annotations

import os
import sys

_app_root = os.environ.get("UMH_ROOT", "/opt/OS")
if _app_root not in sys.path:
    sys.path.insert(0, _app_root)

import asyncio
import json
import logging
import os
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import psutil
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Request,
    Security,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.responses import JSONResponse
from fastapi.security import APIKeyHeader
from transports.api.cockpit_auth import require_clerk_auth, validate_ws_clerk_token

logger = logging.getLogger(__name__)

_API_KEY = os.environ.get("UMH_OPERATOR_API_KEY", "")
_OPERATOR_TOKEN = os.environ.get("UMH_OPERATOR_TOKEN", "")
_WS_TOKEN = os.environ.get("UMH_WS_TOKEN", "") or _API_KEY
_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
_operator_token_header = APIKeyHeader(name="X-Operator-Token", auto_error=False)

_DEV_BYPASS = os.environ.get("UMH_DEV_BYPASS", "").lower() in ("1", "true", "yes")

import hmac as _hmac
import ipaddress as _ipaddress

_TAILSCALE_CGNAT = _ipaddress.ip_network("100.64.0.0/10")


def _is_private_ip(ip: str) -> bool:
    if not ip:
        return False
    try:
        addr = _ipaddress.ip_address(ip)
        return addr.is_private or addr.is_loopback or addr in _TAILSCALE_CGNAT
    except ValueError:
        return False


_TRUSTED_PROXIES = {"127.0.0.1", "::1"}
_docker_bridge = os.environ.get("UMH_DOCKER_BRIDGE_IP", "172.20.0.1")
if _docker_bridge:
    _TRUSTED_PROXIES.add(_docker_bridge)


def _real_client_ip(request: Request) -> str:
    """Return the real client IP, accounting for trusted reverse proxies.

    Only reads X-Forwarded-For when the TCP source is an explicitly trusted
    proxy (localhost or Docker bridge).  Tailscale CGNAT IPs are real clients
    — not proxies — so their TCP source is used directly.
    """
    tcp_ip = request.client.host if request.client else ""
    if tcp_ip in _TRUSTED_PROXIES:
        forwarded = request.headers.get("x-forwarded-for", "")
        if forwarded:
            return forwarded.split(",")[0].strip()
    return tcp_ip


def _dev_bypass_allowed(request: Request) -> bool:
    """Allow token-free access from private IPs when UMH_DEV_BYPASS=true."""
    if not _DEV_BYPASS:
        return False
    return _is_private_ip(_real_client_ip(request))


_RATE_LIMITS: dict[str, dict[str, float]] = {}
_RATE_WINDOWS: dict[str, float] = {
    "promote": 60.0,
    "execute": 30.0,
    "approve": 30.0,
}


def _check_rate_limit(action: str, client_id: str) -> None:
    window = _RATE_WINDOWS.get(action, 60.0)
    bucket = _RATE_LIMITS.setdefault(action, {})
    now = time.time()
    last = bucket.get(client_id, 0.0)
    if now - last < window:
        remaining = int(window - (now - last))
        raise HTTPException(status_code=429, detail=f"Rate limited — retry in {remaining}s")
    bucket[client_id] = now


async def _require_api_key(
    request: Request,
    key: str | None = Security(_api_key_header),
) -> str:
    # Clerk JWT already validated by parent router — skip API key check
    clerk_user = getattr(request.state, "clerk_user_id", None)
    if clerk_user and clerk_user != "dev-bypass":
        return f"clerk:{clerk_user}"

    if not _API_KEY:
        if _dev_bypass_allowed(request):
            return "dev-bypass"
        raise HTTPException(
            status_code=503, detail="API key not configured — set UMH_OPERATOR_API_KEY"
        )
    if not key or not _hmac.compare_digest(key, _API_KEY):
        if _dev_bypass_allowed(request):
            return "dev-bypass"
        raise HTTPException(status_code=401, detail="Invalid or missing API key")
    return key


async def _require_operator_role(
    request: Request,
    key: str | None = Security(_api_key_header),
    operator_token: str | None = Security(_operator_token_header),
) -> str:
    """Validates operator-level credentials for privileged endpoints."""
    api_identity = await _require_api_key(request, key)

    if api_identity.startswith("clerk:"):
        return api_identity

    if not _OPERATOR_TOKEN:
        if _dev_bypass_allowed(request):
            logger.info("Operator dev-bypass from private IP %s", _real_client_ip(request))
            return "operator-dev-bypass"
        raise HTTPException(
            status_code=503, detail="Operator token not configured — set UMH_OPERATOR_TOKEN"
        )

    if not operator_token or not _hmac.compare_digest(operator_token, _OPERATOR_TOKEN):
        logger.warning(
            "Unauthorized operator access attempt: %s %s from %s",
            request.method,
            request.url.path,
            _real_client_ip(request),
        )
        raise HTTPException(
            status_code=403, detail="Operator token required for privileged actions"
        )

    return "operator"


router = APIRouter(prefix="/api/umh", dependencies=[Depends(require_clerk_auth)])
ws_router = APIRouter(prefix="/api/umh")

_ROOT = Path(os.getenv("UMH_ROOT", "/opt/OS"))
MEMORY_STORE = _ROOT / "data" / "runtime" / "canonical_memory_store" / "memories.jsonl"
TRACE_STORE = _ROOT / "data" / "umh" / "traces" / "traces.jsonl"
SKILLS_DIR = _ROOT / "skills"
AGENTS_DIR = _ROOT / "agents"

_DOCKER_SOCK = "/var/run/docker.sock"
_DEVICE_REGISTRY_PATH = _ROOT / "infra" / "device_registry.json"


# ── Core routes (extracted to cockpit_core_routes.py for quality gate) ────────

from transports.api import cockpit_core_routes

cockpit_core_routes.configure(
    require_operator_dep=_require_operator_role,
    is_private_ip_fn=_is_private_ip,
    validate_ws_clerk_token_fn=validate_ws_clerk_token,
    ws_token=_WS_TOKEN,
    dev_bypass=_DEV_BYPASS,
    trusted_proxies=_TRUSTED_PROXIES,
)
router.include_router(cockpit_core_routes.core_router)
ws_router.include_router(cockpit_core_routes.core_ws_router)

_get_organism = cockpit_core_routes.get_organism
_get_org_id = cockpit_core_routes.get_org_id
push_chat_message = cockpit_core_routes.push_chat_message
push_organism_event = cockpit_core_routes.push_organism_event
push_mutation_event = cockpit_core_routes.push_mutation_event

# ── Phase 6.1→6.2: Spine routes extracted to cockpit_spine_router.py ─────────


def _mount_spine_router() -> None:
    from transports.api import cockpit_spine_router

    cockpit_spine_router.configure(
        get_organism_fn=_get_organism,
        check_rate_limit_fn=_check_rate_limit,
        require_operator_dep=_require_operator_role,
    )
    router.include_router(cockpit_spine_router.spine_router)


_mount_spine_router()

# ── C27: Chat routes extracted to cockpit_chat_routes.py ─────────────────────


def _mount_chat_router() -> None:
    from transports.api import cockpit_chat_routes

    cockpit_chat_routes.configure(
        get_organism_fn=_get_organism,
        push_chat_message_fn=cockpit_core_routes.push_chat_message,
        require_operator_dep=_require_operator_role,
    )
    router.include_router(cockpit_chat_routes.chat_router)


_mount_chat_router()

# ── C27: Execution/loop routes extracted to cockpit_execution_loop_routes.py ──


def _mount_execution_loop_router() -> None:
    from transports.api import cockpit_execution_loop_routes

    cockpit_execution_loop_routes.configure(
        get_organism_fn=_get_organism,
        require_operator_dep=_require_operator_role,
    )
    router.include_router(cockpit_execution_loop_routes.execution_loop_router)


_mount_execution_loop_router()

# ── Phase 10.0: Organism core routes extracted to cockpit_organism_routes.py ──


def _mount_organism_router() -> None:
    from transports.api import cockpit_organism_routes

    cockpit_organism_routes.configure(
        get_organism_fn=_get_organism,
        check_rate_limit_fn=_check_rate_limit,
        require_operator_dep=_require_operator_role,
    )
    router.include_router(cockpit_organism_routes.organism_router)


_mount_organism_router()


def _mount_entity_router() -> None:
    from transports.api import cockpit_entity_routes

    cockpit_entity_routes.configure(
        get_org_id_fn=_get_org_id,
        require_operator_dep=_require_operator_role,
    )
    router.include_router(cockpit_entity_routes.entity_router)


_mount_entity_router()


def _mount_meta_ide_critical_router() -> None:
    from transports.api import cockpit_meta_ide_critical_routes

    cockpit_meta_ide_critical_routes.configure(
        get_organism_fn=_get_organism,
        require_operator_dep=_require_operator_role,
    )
    router.include_router(cockpit_meta_ide_critical_routes.meta_ide_critical_router)


try:
    _mount_meta_ide_critical_router()
except Exception:
    logger.warning("meta-ide-critical routes failed to mount", exc_info=True)


def _mount_economy_router() -> None:
    from transports.api import cockpit_economy_routes

    cockpit_economy_routes.configure(
        get_organism_fn=_get_organism,
        require_operator_dep=_require_operator_role,
    )
    router.include_router(cockpit_economy_routes.economy_router)


def _mount_autonomous_router() -> None:
    from transports.api import cockpit_autonomous_routes

    cockpit_autonomous_routes.configure(
        get_organism_fn=_get_organism,
        require_operator_dep=_require_operator_role,
    )
    router.include_router(cockpit_autonomous_routes.autonomous_router)


def _mount_self_build_router() -> None:
    from transports.api import cockpit_self_build_routes

    cockpit_self_build_routes.configure(
        get_organism_fn=_get_organism,
        require_operator_dep=_require_operator_role,
    )
    router.include_router(cockpit_self_build_routes.self_build_router)


def _mount_universal_work_router() -> None:
    from transports.api import cockpit_universal_work_routes

    cockpit_universal_work_routes.configure(
        require_operator_dep=_require_operator_role,
    )
    router.include_router(cockpit_universal_work_routes.universal_work_router)


def _mount_propagation_graph_router() -> None:
    from transports.api import cockpit_propagation_graph_routes

    cockpit_propagation_graph_routes.configure(
        require_operator_dep=_require_operator_role,
    )
    router.include_router(cockpit_propagation_graph_routes.propagation_graph_router)


def _mount_operator_experience_router() -> None:
    from transports.api import cockpit_operator_experience_routes

    cockpit_operator_experience_routes.configure(
        require_operator_dep=_require_operator_role,
    )
    router.include_router(cockpit_operator_experience_routes.operator_experience_router)


def _mount_runtime_surface_router() -> None:
    from transports.api import cockpit_runtime_surface_routes

    cockpit_runtime_surface_routes.configure(
        require_operator_dep=_require_operator_role,
    )
    router.include_router(cockpit_runtime_surface_routes.runtime_surface_router)


_mount_economy_router()
_mount_autonomous_router()
_mount_self_build_router()
_mount_universal_work_router()
_mount_propagation_graph_router()
_mount_operator_experience_router()
_mount_runtime_surface_router()


def _mount_context_assimilation_router() -> None:
    from transports.api import cockpit_context_assimilation_routes

    cockpit_context_assimilation_routes.configure(
        require_operator_dep=_require_operator_role,
    )
    router.include_router(cockpit_context_assimilation_routes.context_assimilation_router)


_mount_context_assimilation_router()

# ── Phase 14.7A: Reality Model routes ────────────────────────────────────────


def _mount_reality_model_router() -> None:
    from transports.api import cockpit_reality_model_routes

    cockpit_reality_model_routes.configure(
        require_operator_dep=_require_operator_role,
    )
    router.include_router(cockpit_reality_model_routes.reality_model_router)


_mount_reality_model_router()

# ── Phase 20: Reality Intelligence routes ─────────────────────────────────────


def _mount_reality_intelligence_router() -> None:
    from transports.api import cockpit_reality_intelligence_routes

    cockpit_reality_intelligence_routes.configure(
        require_operator_dep=_require_operator_role,
    )
    router.include_router(
        cockpit_reality_intelligence_routes.reality_intelligence_router,
    )


_mount_reality_intelligence_router()

# ── Phase 21: Meta IDE routes ─────────────────────────────────────────────


def _mount_meta_ide_router() -> None:
    from transports.api import cockpit_meta_ide_routes

    cockpit_meta_ide_routes.configure(
        require_operator_dep=_require_operator_role,
    )
    router.include_router(
        cockpit_meta_ide_routes.meta_ide_router,
    )


_mount_meta_ide_router()

# ── Phase 22: Engineering Loop routes ─────────────────────────────────────────


def _mount_engineering_loop_router() -> None:
    from transports.api import cockpit_engineering_routes

    cockpit_engineering_routes.configure(
        require_operator_dep=_require_operator_role,
    )
    router.include_router(
        cockpit_engineering_routes.engineering_router,
    )


_mount_engineering_loop_router()

# ── Phase 23: Engineering proof loop routes ───────────────────────────────────


def _mount_engineering_review_router() -> None:
    from transports.api import cockpit_engineering_review_routes

    cockpit_engineering_review_routes.configure(
        require_operator_dep=_require_operator_role,
    )
    router.include_router(
        cockpit_engineering_review_routes.engineering_review_router,
    )


_mount_engineering_review_router()

# ── Phase 14.7A: Operator loop routes ────────────────────────────────────────


def _mount_operator_loop_router() -> None:
    from transports.api import cockpit_operator_loop_routes

    cockpit_operator_loop_routes.configure(
        require_operator_dep=_require_operator_role,
    )
    router.include_router(cockpit_operator_loop_routes.operator_loop_router)


_mount_operator_loop_router()


def _mount_operator_loop_ext_router() -> None:
    from transports.api import cockpit_operator_loop_ext_routes

    cockpit_operator_loop_ext_routes.configure(
        require_operator_dep=_require_operator_role,
    )
    router.include_router(cockpit_operator_loop_ext_routes.operator_loop_ext_router)


_mount_operator_loop_ext_router()


def _mount_operator_loop_session_router() -> None:
    from transports.api import cockpit_operator_loop_session_routes

    cockpit_operator_loop_session_routes.configure(
        require_operator_dep=_require_operator_role,
    )
    router.include_router(cockpit_operator_loop_session_routes.operator_loop_session_router)


_mount_operator_loop_session_router()

# ── Phase 18: Operator timeline routes ─────────────────────────────────────


def _mount_operator_timeline_router() -> None:
    from transports.api import cockpit_operator_timeline_routes

    cockpit_operator_timeline_routes.configure(
        require_operator_dep=_require_operator_role,
    )
    router.include_router(cockpit_operator_timeline_routes.operator_timeline_router)


_mount_operator_timeline_router()

# ── Phase 14.7A: Self-improvement loop routes ─────────────────────────────


def _mount_self_improvement_router() -> None:
    from transports.api import cockpit_self_improvement_routes

    cockpit_self_improvement_routes.configure(
        require_operator_dep=_require_operator_role,
    )
    router.include_router(cockpit_self_improvement_routes.self_improvement_router)


_mount_self_improvement_router()

# ── Phase 14.11A: Workstation execution control routes ──────────────────────


def _mount_workstation_control_router() -> None:
    from transports.api import cockpit_workstation_control_routes

    cockpit_workstation_control_routes.configure(
        require_operator_dep=_require_operator_role,
    )
    router.include_router(cockpit_workstation_control_routes.workstation_control_router)


_mount_workstation_control_router()

# ── Phase 14.11C: Workspace routes (file browser, diff, tests, logs, proof, health) ──


def _mount_workspace_router() -> None:
    from transports.api import cockpit_workspace_routes

    cockpit_workspace_routes.configure(
        require_operator_dep=_require_operator_role,
        require_api_key_dep=_require_api_key,
    )
    router.include_router(cockpit_workspace_routes.workspace_router)


_mount_workspace_router()

# ── Phase 14.11D: Presence routes (activation, commands, capabilities) ──


def _mount_presence_router() -> None:
    from transports.api import cockpit_presence_routes

    cockpit_presence_routes.configure(
        require_operator_dep=_require_operator_role,
    )
    router.include_router(cockpit_presence_routes.presence_router)


_mount_presence_router()

# ── Phase 14.11E: Command center routes (agents, work packets, summary) ──


def _mount_command_center_router() -> None:
    from transports.api import cockpit_command_center_routes

    cockpit_command_center_routes.configure(
        require_operator_dep=_require_operator_role,
    )
    router.include_router(cockpit_command_center_routes.command_center_router)


_mount_command_center_router()


def _mount_rooms_router() -> None:
    from transports.api.cockpit_rooms_routes import rooms_router as _rooms_router
    from transports.api.cockpit_rooms_routes import rooms_public_router as _rooms_public

    router.include_router(_rooms_router)
    ws_router.include_router(_rooms_public)


_mount_rooms_router()


def _mount_broadcast_router() -> None:
    from transports.api.cockpit_broadcast_routes import broadcast_router as _br
    from transports.api.cockpit_broadcast_routes import broadcast_ws_router as _bws

    router.include_router(_br)
    ws_router.include_router(_bws)


_mount_broadcast_router()


# ── Phase 24: Distributed Worker Runtime routes ──────────────────────────────


def _mount_distributed_runtime_router() -> None:
    from transports.api import cockpit_distributed_runtime_routes

    cockpit_distributed_runtime_routes.configure(
        require_operator_dep=_require_operator_role,
    )
    router.include_router(
        cockpit_distributed_runtime_routes.distributed_runtime_router,
    )


_mount_distributed_runtime_router()


# ── Phase 25: Workspace Observation routes ─────────────────────────────────


def _mount_workspace_observation_router() -> None:
    from transports.api import cockpit_workspace_observation_routes

    cockpit_workspace_observation_routes.configure(
        require_operator_dep=_require_operator_role,
    )
    router.include_router(
        cockpit_workspace_observation_routes.workspace_observation_router,
    )


_mount_workspace_observation_router()


# ── Phase 26: Governed Action Bridge routes ──────────────────────────────────


def _mount_action_bridge_router() -> None:
    from transports.api import cockpit_action_bridge_routes

    cockpit_action_bridge_routes.configure(
        require_operator_dep=_require_operator_role,
    )
    router.include_router(
        cockpit_action_bridge_routes.action_bridge_router,
    )


_mount_action_bridge_router()

# ── Phase 27: Workspace Topology routes ──────────────────────────────────────


def _mount_workspace_topology_router() -> None:
    from transports.api import cockpit_workspace_topology_routes

    cockpit_workspace_topology_routes.configure(
        require_operator_dep=_require_operator_role,
    )
    router.include_router(
        cockpit_workspace_topology_routes.workspace_topology_router,
    )


_mount_workspace_topology_router()

# ── Phase 28: UMH Node Topology routes ─────────────────────────────────────


def _mount_umh_node_router() -> None:
    from transports.api import cockpit_umh_node_routes

    cockpit_umh_node_routes.configure(
        require_operator_dep=_require_operator_role,
    )
    router.include_router(
        cockpit_umh_node_routes.umh_node_router,
    )


_mount_umh_node_router()

# ── W1: Unified Compute Fabric routes ─────────────────────────────────────


def _mount_compute_fabric_router() -> None:
    from transports.api import cockpit_compute_fabric_routes

    cockpit_compute_fabric_routes.configure(
        require_operator_dep=_require_operator_role,
    )
    router.include_router(
        cockpit_compute_fabric_routes.compute_fabric_router,
    )


_mount_compute_fabric_router()

# ── W3: Agent Fleet routes ─────────────────────────────────────────────────


def _mount_agent_fleet_router() -> None:
    from transports.api import cockpit_agent_fleet_routes

    cockpit_agent_fleet_routes.configure(
        require_operator_dep=_require_operator_role,
    )
    router.include_router(
        cockpit_agent_fleet_routes.agent_fleet_router,
    )


_mount_agent_fleet_router()

# ── W2: Meta IDE convergence routes ───────────────────────────────────────


def _mount_meta_ide_conv_router() -> None:
    from transports.api import cockpit_meta_ide_conv_routes

    cockpit_meta_ide_conv_routes.configure(
        require_operator_dep=_require_operator_role,
    )
    router.include_router(
        cockpit_meta_ide_conv_routes.meta_ide_conv_router,
    )


_mount_meta_ide_conv_router()

# ── W4: Embodiment routes ─────────────────────────────────────────────────


def _mount_embodiment_router() -> None:
    from transports.api import cockpit_embodiment_routes

    cockpit_embodiment_routes.configure(
        require_operator_dep=_require_operator_role,
    )
    router.include_router(
        cockpit_embodiment_routes.embodiment_router,
    )


_mount_embodiment_router()

# ── W5: Operator Migration routes ─────────────────────────────────────────


def _mount_migration_router() -> None:
    from transports.api import cockpit_migration_routes

    cockpit_migration_routes.configure(
        require_operator_dep=_require_operator_role,
    )
    router.include_router(
        cockpit_migration_routes.migration_router,
    )


_mount_migration_router()

# ── Phase 29: State Authority routes ──────────────────────────────────────


def _mount_state_authority_router() -> None:
    from transports.api import cockpit_state_authority_routes

    cockpit_state_authority_routes.configure(
        require_operator_dep=_require_operator_role,
    )
    router.include_router(
        cockpit_state_authority_routes.state_authority_router,
    )


_mount_state_authority_router()

# ── Phase 30: Service Dependency Graph routes ────────────────────────────


def _mount_service_graph_router() -> None:
    from transports.api import cockpit_service_graph_routes

    cockpit_service_graph_routes.configure(
        require_operator_dep=_require_operator_role,
    )
    router.include_router(
        cockpit_service_graph_routes.service_graph_router,
    )


_mount_service_graph_router()


def _mount_operator_home_router() -> None:
    from transports.api import cockpit_operator_home_routes

    cockpit_operator_home_routes.configure(
        require_operator_dep=_require_operator_role,
    )
    router.include_router(
        cockpit_operator_home_routes.operator_home_router,
    )


_mount_operator_home_router()


def _mount_operator_presence_router() -> None:
    from transports.api import cockpit_operator_presence_routes

    cockpit_operator_presence_routes.configure(
        require_operator_dep=_require_operator_role,
    )
    router.include_router(
        cockpit_operator_presence_routes.operator_presence_router,
    )


_mount_operator_presence_router()


def _mount_screen_awareness_router() -> None:
    from transports.api import cockpit_screen_awareness_routes

    cockpit_screen_awareness_routes.configure(
        require_operator_dep=_require_operator_role,
    )
    router.include_router(
        cockpit_screen_awareness_routes.screen_awareness_router,
    )


_mount_screen_awareness_router()


def _mount_voice_router() -> None:
    from transports.api import cockpit_voice_routes

    cockpit_voice_routes.configure(
        require_operator_dep=_require_operator_role,
    )
    router.include_router(
        cockpit_voice_routes.voice_router,
    )


_mount_voice_router()


# ── Gate 3: Work Center ──────────────────────────────────────────────


def _mount_work_center_router() -> None:
    from transports.api import cockpit_work_center_routes

    cockpit_work_center_routes.configure(
        require_operator_dep=_require_operator_role,
    )
    router.include_router(
        cockpit_work_center_routes.work_center_router,
    )


_mount_work_center_router()


# ── Gate 4: Intent Runtime ───────────────────────────────────────────


def _mount_intent_router() -> None:
    from transports.api import cockpit_intent_routes

    cockpit_intent_routes.configure(
        require_operator_dep=_require_operator_role,
    )
    router.include_router(
        cockpit_intent_routes.intent_router,
    )


_mount_intent_router()


# ── Gate 4: Organism Map ────────────────────────────────────────────


def _mount_organism_map_router() -> None:
    from transports.api import cockpit_organism_map_routes

    cockpit_organism_map_routes.configure(
        require_operator_dep=_require_operator_role,
    )
    router.include_router(
        cockpit_organism_map_routes.organism_map_router,
    )


_mount_organism_map_router()


# ── Gate 4: Execution ───────────────────────────────────────────────


def _mount_execution_router() -> None:
    from transports.api import cockpit_execution_routes

    cockpit_execution_routes.configure(
        require_operator_dep=_require_operator_role,
    )
    router.include_router(
        cockpit_execution_routes.execution_router,
    )


_mount_execution_router()


# ── Gate 4: Activity ────────────────────────────────────────────────


def _mount_activity_router() -> None:
    from transports.api import cockpit_activity_routes

    cockpit_activity_routes.configure(
        require_operator_dep=_require_operator_role,
    )
    router.include_router(
        cockpit_activity_routes.activity_router,
    )


_mount_activity_router()


# ── Gate 5: Capability Runtime ──────────────────────────────────


def _mount_capability_router() -> None:
    from transports.api import cockpit_capability_routes

    cockpit_capability_routes.configure(
        require_operator_dep=_require_operator_role,
    )
    router.include_router(
        cockpit_capability_routes.capability_router,
    )


_mount_capability_router()


def _mount_operationalization_router() -> None:
    from transports.api import cockpit_operationalization_routes

    cockpit_operationalization_routes.configure(
        require_operator_dep=_require_operator_role,
    )
    router.include_router(
        cockpit_operationalization_routes.operationalization_router,
    )


_mount_operationalization_router()


def _mount_execution_graph_router() -> None:
    from transports.api import cockpit_execution_graph_routes

    cockpit_execution_graph_routes.configure(
        require_operator_dep=_require_operator_role,
    )
    router.include_router(
        cockpit_execution_graph_routes.execution_graph_router,
    )


_mount_execution_graph_router()


def _mount_infrastructure_router() -> None:
    from transports.api import cockpit_infrastructure_routes

    cockpit_infrastructure_routes.configure(
        require_operator_dep=_require_operator_role,
    )
    router.include_router(
        cockpit_infrastructure_routes.infrastructure_router,
    )


_mount_infrastructure_router()


def _mount_compounding_router() -> None:
    from transports.api import cockpit_compounding_routes

    cockpit_compounding_routes.configure(
        require_operator_dep=_require_operator_role,
    )
    router.include_router(
        cockpit_compounding_routes.compounding_router,
    )


_mount_compounding_router()


def _mount_projection_router() -> None:
    from transports.api import cockpit_projection_routes

    cockpit_projection_routes.configure(
        require_operator_dep=_require_operator_role,
    )
    router.include_router(
        cockpit_projection_routes.projection_router,
    )


_mount_projection_router()


# ── Campaign 3 routes ──────────────────────────────────────────────────────


def _mount_capability_map_router() -> None:
    from transports.api import cockpit_capability_map_routes

    cockpit_capability_map_routes.configure(
        require_operator_dep=_require_operator_role,
    )
    router.include_router(
        cockpit_capability_map_routes.capability_map_router,
    )


_mount_capability_map_router()


def _mount_command_center_mvp_router() -> None:
    from transports.api import cockpit_command_center_mvp_routes

    cockpit_command_center_mvp_routes.configure(
        require_operator_dep=_require_operator_role,
    )
    router.include_router(
        cockpit_command_center_mvp_routes.command_center_mvp_router,
    )


_mount_command_center_mvp_router()


def _mount_unified_execution_router() -> None:
    from transports.api import cockpit_unified_execution_routes

    cockpit_unified_execution_routes.configure(
        require_operator_dep=_require_operator_role,
    )
    router.include_router(
        cockpit_unified_execution_routes.unified_execution_router,
    )


_mount_unified_execution_router()


def _mount_build_loop_router() -> None:
    from transports.api import cockpit_meta_ide_projection_loop_routes

    cockpit_meta_ide_projection_loop_routes.configure(
        require_operator_dep=_require_operator_role,
    )
    router.include_router(
        cockpit_meta_ide_projection_loop_routes.build_loop_router,
    )


_mount_build_loop_router()


def _mount_projection_integration_router() -> None:
    from transports.api import cockpit_projection_integration_routes

    cockpit_projection_integration_routes.configure(
        require_operator_dep=_require_operator_role,
    )
    router.include_router(
        cockpit_projection_integration_routes.projection_integration_router,
    )


_mount_projection_integration_router()


# ── Campaign 4: Operator-Orchestrator Convergence ─────────────────────────


def _mount_orchestrator_awareness_router() -> None:
    from transports.api import cockpit_orchestrator_awareness_routes

    r = cockpit_orchestrator_awareness_routes._build_router()
    router.include_router(r)


_mount_orchestrator_awareness_router()


def _mount_operating_loop_router() -> None:
    from transports.api import cockpit_operating_loop_routes

    r = cockpit_operating_loop_routes._build_router()
    router.include_router(r)


_mount_operating_loop_router()


def _mount_unified_approval_router() -> None:
    from transports.api import cockpit_unified_approval_routes

    r = cockpit_unified_approval_routes._build_router()
    router.include_router(r)


_mount_unified_approval_router()


def _mount_objective_plan_router() -> None:
    # Wave 1: objective-plan read + decision surfaces (thin adapter over the
    # canonical Operator Intent Protocol).
    from transports.api import objective_plan_routes

    objective_plan_routes.mount(router)


_mount_objective_plan_router()


def _mount_execution_attempt_router() -> None:
    # Wave 2: canonical execution read surface + governed cancel/retry (thin
    # adapter over substrate.execution.attempts).
    from transports.api import execution_attempt_routes

    execution_attempt_routes.mount(router)


_mount_execution_attempt_router()


def _mount_loop_coherence_router() -> None:
    from transports.api import cockpit_loop_coherence_routes

    r = cockpit_loop_coherence_routes._build_router()
    router.include_router(r)


_mount_loop_coherence_router()


def _mount_wk_session_router() -> None:
    from transports.api import cockpit_session_routes

    r = cockpit_session_routes._build_router()
    router.include_router(r)


_mount_wk_session_router()


def _mount_mvp_readiness_router() -> None:
    from transports.api import cockpit_mvp_readiness_routes

    r = cockpit_mvp_readiness_routes._build_router()
    router.include_router(r)


_mount_mvp_readiness_router()


def _mount_delegation_router() -> None:
    from transports.api import cockpit_delegation_routes

    r = cockpit_delegation_routes._build_router()
    router.include_router(r)


_mount_delegation_router()


def _mount_reality_graph_router() -> None:
    from transports.api import cockpit_reality_graph_routes

    r = cockpit_reality_graph_routes.get_router()
    router.include_router(r)


def _mount_context_resolution_router() -> None:
    from transports.api import cockpit_context_resolution_routes

    r = cockpit_context_resolution_routes.get_router()
    router.include_router(r)


_mount_reality_graph_router()
_mount_context_resolution_router()


def _mount_c6_routers() -> None:
    from transports.api.cockpit_artifact_registry_routes import router as artifact_router
    from transports.api.cockpit_repository_awareness_routes import router as repo_router
    from transports.api.cockpit_documentation_awareness_routes import router as doc_router
    from transports.api.cockpit_runtime_awareness_routes import router as runtime_router
    from transports.api.cockpit_knowledge_awareness_routes import router as knowledge_router

    router.include_router(artifact_router)
    router.include_router(repo_router)
    router.include_router(doc_router)
    router.include_router(runtime_router)
    router.include_router(knowledge_router)


_mount_c6_routers()


def _mount_strategic_router() -> None:
    from transports.api import cockpit_strategic_routes

    r = cockpit_strategic_routes.get_router()
    router.include_router(r)


_mount_strategic_router()


def _mount_goal_router() -> None:
    from transports.api import cockpit_goal_routes

    r = cockpit_goal_routes.get_router()
    router.include_router(r)


_mount_goal_router()


def _mount_memory_router() -> None:
    from transports.api import cockpit_memory_routes

    r = cockpit_memory_routes.get_router()
    router.include_router(r)


_mount_memory_router()


def _mount_capability_intelligence_router() -> None:
    from transports.api import cockpit_capability_intelligence_routes

    r = cockpit_capability_intelligence_routes.get_router()
    router.include_router(r)


_mount_capability_intelligence_router()


def _mount_work_intelligence_router() -> None:
    from transports.api import cockpit_work_intelligence_routes

    r = cockpit_work_intelligence_routes.get_router()
    router.include_router(r)


_mount_work_intelligence_router()


def _mount_learning_router() -> None:
    from transports.api import cockpit_learning_routes

    r = cockpit_learning_routes.get_router()
    router.include_router(r)


_mount_learning_router()


# ── Campaign 13: Prediction Intelligence ──────────────────────────────


def _mount_prediction_router() -> None:
    from transports.api import cockpit_prediction_routes

    r = cockpit_prediction_routes.get_router()
    router.include_router(r)


_mount_prediction_router()


# ── Campaign 14: Executive Intelligence ──────────────────────────────


def _mount_executive_router() -> None:
    from transports.api import cockpit_executive_routes

    r = cockpit_executive_routes.get_router()
    router.include_router(r)


_mount_executive_router()


# ── Campaign 15: Organism Governance ──────────────────────────────


def _mount_governance_router() -> None:
    from transports.api import cockpit_governance_routes

    r = cockpit_governance_routes.get_router()
    router.include_router(r)


_mount_governance_router()


# ── Campaign 17: Workstation Embodiment ──────────────────────────────


def _mount_orchestrator_presence_router() -> None:
    from transports.api import cockpit_orchestrator_presence_routes

    r = cockpit_orchestrator_presence_routes.get_router()
    router.include_router(r)


_mount_orchestrator_presence_router()


def _mount_meta_ide_context_router() -> None:
    from transports.api import cockpit_meta_ide_context_routes

    r = cockpit_meta_ide_context_routes.get_router()
    router.include_router(r)


_mount_meta_ide_context_router()


def _mount_workstation_presence_router() -> None:
    from transports.api import cockpit_workstation_presence_routes

    r = cockpit_workstation_presence_routes.get_router()
    router.include_router(r)


_mount_workstation_presence_router()


def _mount_unified_workstation_router() -> None:
    from transports.api import cockpit_unified_workstation_routes

    r = cockpit_unified_workstation_routes.get_router()
    router.include_router(r)


_mount_unified_workstation_router()


def _mount_attention_router() -> None:
    from transports.api import cockpit_attention_routes

    r = cockpit_attention_routes.get_router()
    router.include_router(r)


_mount_attention_router()


def _mount_execution_fabric_router() -> None:
    from transports.api import cockpit_execution_fabric_routes

    r = cockpit_execution_fabric_routes.get_router()
    router.include_router(r)


_mount_execution_fabric_router()


def _mount_agent_workforce_router() -> None:
    from transports.api import cockpit_agent_workforce_routes

    r = cockpit_agent_workforce_routes.get_router()
    router.include_router(r)


_mount_agent_workforce_router()


def _mount_session_machine_router() -> None:
    from transports.api import cockpit_session_machine_routes

    r = cockpit_session_machine_routes.get_router()
    router.include_router(r)


_mount_session_machine_router()


def _mount_voice_ingress_router() -> None:
    from transports.api import cockpit_voice_ingress_routes

    r = cockpit_voice_ingress_routes.get_router()
    router.include_router(r)


_mount_voice_ingress_router()


def _mount_voice_session_router() -> None:
    from transports.api import cockpit_voice_session_routes

    r = cockpit_voice_session_routes.get_router()
    router.include_router(r)


_mount_voice_session_router()


def _mount_ambient_wake_router() -> None:
    from transports.api import cockpit_ambient_wake_routes

    r = cockpit_ambient_wake_routes.get_router()
    router.include_router(r)


_mount_ambient_wake_router()


def _mount_voice_output_router() -> None:
    from transports.api import cockpit_voice_output_routes

    r = cockpit_voice_output_routes.get_router()
    router.include_router(r)


_mount_voice_output_router()


def _mount_voice_ops_router() -> None:
    from transports.api import cockpit_voice_ops_routes

    r = cockpit_voice_ops_routes.get_router()
    router.include_router(r)


_mount_voice_ops_router()


# ── Campaign 21: Visual Awareness & Environmental Context ───────────


def _mount_visual_awareness_router() -> None:
    from transports.api import cockpit_visual_awareness_routes

    r = cockpit_visual_awareness_routes.get_router()
    router.include_router(r)


_mount_visual_awareness_router()


def _mount_visual_environment_router() -> None:
    from transports.api import cockpit_visual_environment_routes

    r = cockpit_visual_environment_routes.get_router()
    router.include_router(r)


_mount_visual_environment_router()


def _mount_visual_context_router() -> None:
    from transports.api import cockpit_visual_context_routes

    r = cockpit_visual_context_routes.get_router()
    router.include_router(r)


_mount_visual_context_router()


def _mount_visual_attention_router() -> None:
    from transports.api import cockpit_visual_attention_routes

    r = cockpit_visual_attention_routes.get_router()
    router.include_router(r)


_mount_visual_attention_router()


def _mount_visual_ops_router() -> None:
    from transports.api import cockpit_visual_ops_routes

    r = cockpit_visual_ops_routes.get_router()
    router.include_router(r)


_mount_visual_ops_router()


def _mount_production_router() -> None:
    from transports.api import cockpit_production_routes

    cockpit_production_routes.configure(_require_operator_role)
    router.include_router(cockpit_production_routes.production_router)


_mount_production_router()

# ── Device onboarding routes ───────────────────────────────────────────────


def _mount_device_router() -> None:
    from transports.api import cockpit_device_routes

    cockpit_device_routes.configure(_require_operator_role)
    router.include_router(cockpit_device_routes.device_router)


_mount_device_router()


# ── Push notification routes ──────────────────────────────────────────────


def _mount_push_router() -> None:
    from transports.api import cockpit_push_routes

    cockpit_push_routes.configure(_require_operator_role)
    router.include_router(cockpit_push_routes.push_router)


_mount_push_router()


# ── C31: Adapter status routes ─────────────────────────────────────────────


def _mount_adapter_status_router() -> None:
    try:
        from transports.api import cockpit_adapter_status_routes

        router.include_router(cockpit_adapter_status_routes.router)
    except Exception:
        logger.debug("adapter status router not available", exc_info=True)


_mount_adapter_status_router()


# ── M1: Proof Inspector routes (G10) ──────────────────────────────────────


def _mount_proof_inspector_router() -> None:
    from transports.api import cockpit_proof_inspector_routes

    cockpit_proof_inspector_routes.configure(
        require_operator_dep=_require_operator_role,
    )
    router.include_router(cockpit_proof_inspector_routes.proof_inspector_router)


_mount_proof_inspector_router()


# ── M1: Recovery Dashboard routes (G11) ───────────────────────────────────


def _mount_recovery_dashboard_router() -> None:
    from transports.api import cockpit_recovery_dashboard_routes

    cockpit_recovery_dashboard_routes.configure(
        require_operator_dep=_require_operator_role,
    )
    router.include_router(cockpit_recovery_dashboard_routes.recovery_dashboard_router)


_mount_recovery_dashboard_router()
