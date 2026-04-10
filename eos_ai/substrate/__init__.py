"""
eos_ai.substrate — Bridging layer between current VPS-centric EOS and the
target distributed, capability-aware AI operating system.

This package is ADDITIVE. It does not modify the hot path
(gateway, cognitive_loop, model_router, agent_runtime). Instead it introduces
typed contracts and lightweight registries that future code can route through:

    nodes         — execution targets beyond "the VPS"
    capabilities  — what a node can do (reasoning, browser_control, mic, etc.)
    station       — contract for a future local Station Daemon
    actions       — SafeAction intent schema for local computer control
    rituals       — open_day / close_day workflow scaffold
    roles         — multi-agent role registry (ea, ceo, portfolio_advisor)

Everything here is intentionally minimal. Registries are in-memory; DB
persistence hooks are marked `# FUTURE:` so they can be wired to Neon later
without changing call sites.

Import surface (stable):

    from eos_ai.substrate import (
        Node, NodeType, NodeStatus, NodeRegistry,
        Capability, CapabilityRegistry,
        StationContract, StationHeartbeat, StationEvent,
        SafeAction, ActionKind, ActionResult,
        Ritual, RitualKind, RitualState, RitualRegistry,
        AgentRole, RoleScope, RoleRegistry,
    )
"""

from eos_ai.substrate.nodes import (
    Node,
    NodeType,
    NodeStatus,
    NodeRegistry,
)
from eos_ai.substrate.capabilities import (
    Capability,
    CapabilityRegistry,
)
from eos_ai.substrate.station import (
    StationContract,
    StationHeartbeat,
    StationEvent,
    ControlMode,
)
from eos_ai.substrate.actions import (
    SafeAction,
    ActionKind,
    ActionResult,
    ActionStatus,
)
from eos_ai.substrate.rituals import (
    Ritual,
    RitualKind,
    RitualState,
    RitualRegistry,
)
from eos_ai.substrate.roles import (
    AgentRole,
    RoleScope,
    RoleRegistry,
)
from eos_ai.substrate.storage import (
    SubstrateStorage,
    JSONFileStorage,
    NeonStorage,
    get_storage,
)
from eos_ai.substrate.station_bus import (
    StationBus,
    get_station_bus,
)
from eos_ai.substrate.capability_tagging import tag_request
from eos_ai.substrate.station_daemon import StationDaemon
from eos_ai.substrate.station_helpers import (
    propose_play_sound,
    propose_speak_text,
    propose_open_url,
    propose_launch_app,
    propose_open_scene,
)
from eos_ai.substrate.scenes import (
    Scene,
    SceneStep,
    SCENE_REGISTRY,
    get_scene,
    list_scenes,
)
from eos_ai.substrate.app_allowlist import APP_ALLOWLIST, AllowedApp, resolve_app
from eos_ai.substrate.ritual_body import (
    RitualPolicy,
    run_close_day_body,
    run_open_day_body,
)
from eos_ai.substrate.role_resolver import (
    resolve_role,
    substrate_slug_for,
)
from eos_ai.substrate.voice_session import (
    VoiceSession,
    VoiceSessionStatus,
    VoiceSessionRuntime,
    VoiceTurn,
    VoiceTurnSource,
    VoiceSessionStore,
    get_voice_session_store,
    set_voice_responder,
    voice_session_report,
)

__all__ = [
    "Node",
    "NodeType",
    "NodeStatus",
    "NodeRegistry",
    "Capability",
    "CapabilityRegistry",
    "StationContract",
    "StationHeartbeat",
    "StationEvent",
    "ControlMode",
    "SafeAction",
    "ActionKind",
    "ActionResult",
    "ActionStatus",
    "Ritual",
    "RitualKind",
    "RitualState",
    "RitualRegistry",
    "AgentRole",
    "RoleScope",
    "RoleRegistry",
    "SubstrateStorage",
    "JSONFileStorage",
    "NeonStorage",
    "get_storage",
    "StationBus",
    "get_station_bus",
    "tag_request",
    "resolve_role",
    "substrate_slug_for",
    "StationDaemon",
    "propose_play_sound",
    "propose_speak_text",
    "propose_open_url",
    "propose_launch_app",
    "propose_open_scene",
    "Scene",
    "SceneStep",
    "SCENE_REGISTRY",
    "get_scene",
    "list_scenes",
    "APP_ALLOWLIST",
    "AllowedApp",
    "resolve_app",
    "RitualPolicy",
    "run_open_day_body",
    "run_close_day_body",
    "VoiceSession",
    "VoiceSessionStatus",
    "VoiceSessionRuntime",
    "VoiceTurn",
    "VoiceTurnSource",
    "VoiceSessionStore",
    "get_voice_session_store",
    "set_voice_responder",
    "voice_session_report",
]
