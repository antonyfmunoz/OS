"""Self-Model — the substrate's awareness of its own structure and state.

The self-model is the foundation for self-recursion. The system cannot
improve itself if it cannot see itself. Every learning loop, every
feedback cycle, every governance decision requires the system to know
what it is right now to decide what it should become next.

This module is the connective tissue between existing subsystems —
not a new subsystem. It unifies:

  foundation/identity.py   → identity continuity and drift detection
  foundation/epistemology.py → beliefs, confidence, evidence
  ontology/laws.py         → 14 executable governance laws
  reality_model/           → canonical patterns + instance observations
  organism/                → runtime graph, supervisor, coordinator, observer
  control_plane/registry   → registered components and adapters
  execution/trace          → execution history
  control_plane/governance → risk classification

Instance identity is loaded through a universal contract:
  1. Environment variables (works for any deployment)
  2. Config files (JSON/YAML, universal)
  3. Registered instance loaders (projections plug in here)

Projections (like EOS with its BIS) register their own loaders.
The substrate never imports projection-specific code directly.

Without self-awareness, the system cannot:
  - Harmonize with external tools and context
  - Govern its own behavior against its own laws
  - Recurse on its own performance to improve
  - Maintain coherence across sessions and context switches
  - Attribute decisions to the subsystems that made them
  - Be downloaded, instantiated, and updated independently

UMH substrate subsystem. The canonical half is universal.
The instance half is populated at runtime via registered loaders.
The operational half queries existing subsystems on demand.
"""

from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable

logger = logging.getLogger(__name__)


class Layer(str, Enum):
    """Which architectural layer a piece of code or data belongs to."""
    SUBSTRATE = "substrate"
    ADAPTER = "adapter"
    TRANSPORT = "transport"
    PROJECTION = "projection"
    INSTANCE = "instance"


class ContextKind(str, Enum):
    """Whether a value is canonical (universal) or instance (specific)."""
    CANONICAL = "canonical"
    INSTANCE = "instance"


# ── Canonical Self ───────────────────────────────────────────────────────────

@dataclass(frozen=True)
class CanonicalSelf:
    """What UMH is, universally, regardless of who runs it."""

    system_name: str = "UMH"
    system_full_name: str = "Universal Mastery Hierarchy"
    purpose: str = "Intelligence substrate that compounds capability through every interaction"

    architecture_layers: tuple[str, ...] = (
        "substrate — universal mechanisms, types, execution engine",
        "adapters — external system connectors (models, APIs, services)",
        "transports — I/O surfaces (discord, API, voice, node mesh)",
        "projections — application-specific views built on substrate",
    )

    dependency_direction: str = "projections → transports → adapters → substrate (inward only)"

    core_principles: tuple[str, ...] = (
        "deterministic-first: spine always works, AI enhances",
        "instance-agnostic: substrate works for any user",
        "type-coherent: one canonical type per concept",
        "reality-grounded: observable truth over theory",
    )

    canonical_packages: tuple[str, ...] = (
        "substrate",
        "adapters",
        "transports",
        "projections",
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "system_name": self.system_name,
            "system_full_name": self.system_full_name,
            "purpose": self.purpose,
            "layers": list(self.architecture_layers),
            "dependency_direction": self.dependency_direction,
            "principles": list(self.core_principles),
        }


CANONICAL = CanonicalSelf()


# ── Instance Self ────────────────────────────────────────────────────────────

@dataclass
class InstanceSelf:
    """Who UMH is right now — specific to this deployment."""

    ai_name: str = ""
    founder_name: str = ""
    org_id: str = ""
    org_name: str = ""
    active_venture_id: str = ""
    active_venture_name: str = ""
    business_stage: str = ""
    node_id: str = ""
    node_role: str = ""

    ventures: list[dict[str, str]] = field(default_factory=list)
    products: list[dict[str, str]] = field(default_factory=list)
    nodes: list[dict[str, str]] = field(default_factory=list)

    loaded: bool = False
    loaded_from: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "ai_name": self.ai_name,
            "founder_name": self.founder_name,
            "org_id": self.org_id,
            "org_name": self.org_name,
            "active_venture_id": self.active_venture_id,
            "business_stage": self.business_stage,
            "node_id": self.node_id,
            "ventures": self.ventures,
            "products": self.products,
            "loaded": self.loaded,
            "loaded_from": self.loaded_from,
        }


# ── Self-Model ───────────────────────────────────────────────────────────────

class SelfModel:
    """The system's unified self-awareness — the foundation for self-recursion.

    Three layers, all querying existing subsystems:

    1. Canonical — what UMH is universally (frozen, never changes)
    2. Instance — who UMH is right now (loaded at runtime)
    3. Operational — what UMH can do and has done (live queries into
       registry, organism, traces, governance, reality model, laws)

    Instance loading uses a universal contract:
      - Env vars first (AI_NAME, UMH_ORG_ID, UMH_NODE_ID, etc.)
      - Config file second (instance.json in data dir)
      - Registered loaders third (projections plug in here)

    Projections register their loaders via register_instance_loader().
    The substrate never imports projection code — projections push in.

    Subsystems register themselves via register_subsystems().
    Same pattern — they push references in, self-model queries them.
    """

    def __init__(self) -> None:
        self.canonical = CANONICAL
        self.instance = InstanceSelf()
        self._subsystems: dict[str, Any] = {}
        self._instance_loaders: list[Callable[[InstanceSelf], None]] = []
        self._boot_time = time.monotonic()

    # ── Subsystem Registration ───────────────────────────────────────

    def register_subsystems(self, **subsystems: Any) -> None:
        """Accept references to existing subsystems for live queries."""
        self._subsystems.update(subsystems)

    def _get(self, name: str) -> Any:
        return self._subsystems.get(name)

    # ── Instance Loader Registration ─────────────────────────────────

    def register_instance_loader(self, loader: Callable[[InstanceSelf], None]) -> None:
        """Register a projection-specific instance loader.

        Loaders are callables that receive InstanceSelf and populate
        fields from their own data source (DB, API, config, etc.).
        Called in registration order after env vars and config file.
        """
        self._instance_loaders.append(loader)

    # ── Instance Loading ─────────────────────────────────────────────

    def load_instance(self) -> InstanceSelf:
        """Load instance identity from universal sources + registered loaders.

        Loading order (later sources fill gaps, never overwrite):
          1. Environment variables (universal, works everywhere)
          2. Config file: data/umh/instance.json (universal, no DB needed)
          3. Registered loaders (projection-specific, e.g. EOS BIS)

        Safe to call multiple times — reloads from source each time.
        """
        inst = self.instance

        # 1. Environment variables — universal, always available
        inst.ai_name = os.environ.get("AI_NAME", "")
        inst.founder_name = os.environ.get("UMH_FOUNDER_NAME", "")
        inst.org_id = os.environ.get("UMH_ORG_ID", "") or os.environ.get("EOS_ORG_ID", "")
        inst.org_name = os.environ.get("UMH_ORG_NAME", "")
        inst.node_id = os.environ.get("UMH_NODE_ID", "")
        inst.node_role = os.environ.get("UMH_NODE_ROLE", "")
        inst.business_stage = os.environ.get("UMH_BUSINESS_STAGE", "")
        inst.active_venture_id = os.environ.get("UMH_ACTIVE_VENTURE", "")

        # 2. Config file — universal, no projection dependency
        self._load_from_config_file(inst)

        # 3. Registered loaders — projection-specific (e.g. EOS BIS)
        for loader in self._instance_loaders:
            try:
                loader(inst)
            except Exception as e:
                logger.debug("instance loader failed: %s", e)

        inst.loaded = True
        inst.loaded_from = inst.loaded_from or "env"
        logger.info(
            "self-model instance loaded: ai=%s org=%s venture=%s stage=%s source=%s",
            inst.ai_name or "(unset)",
            inst.org_id or "(unset)",
            inst.active_venture_id or "(unset)",
            inst.business_stage or "(unset)",
            inst.loaded_from,
        )
        return inst

    def _load_from_config_file(self, inst: InstanceSelf) -> None:
        """Load from data/umh/instance.json if it exists."""
        root = os.environ.get("UMH_ROOT", "/opt/OS")
        config_path = Path(root) / "data" / "umh" / "instance.json"
        if not config_path.exists():
            return
        try:
            data = json.loads(config_path.read_text(encoding="utf-8"))
            inst.ai_name = inst.ai_name or data.get("ai_name", "")
            inst.founder_name = inst.founder_name or data.get("founder_name", "")
            inst.org_id = inst.org_id or data.get("org_id", "")
            inst.org_name = inst.org_name or data.get("org_name", "")
            inst.active_venture_id = inst.active_venture_id or data.get("active_venture_id", "")
            inst.active_venture_name = inst.active_venture_name or data.get("active_venture_name", "")
            inst.business_stage = inst.business_stage or data.get("business_stage", "")
            inst.node_id = inst.node_id or data.get("node_id", "")
            inst.node_role = inst.node_role or data.get("node_role", "")
            inst.ventures = inst.ventures or data.get("ventures", [])
            inst.products = inst.products or data.get("products", [])
            inst.nodes = inst.nodes or data.get("nodes", [])
            inst.loaded_from = "config"
        except Exception as e:
            logger.debug("instance config load failed: %s", e)

    # ── Classification ───────────────────────────────────────────────

    def classify(self, value_description: str) -> ContextKind:
        """Classify whether a described value is canonical or instance."""
        instance_signals = {
            "name", "founder", "company", "venture", "product",
            "ip", "host", "address", "account", "node_id", "session",
            "org_id", "user_id", "channel", "server",
        }
        desc_lower = value_description.lower()
        if any(signal in desc_lower for signal in instance_signals):
            return ContextKind.INSTANCE
        return ContextKind.CANONICAL

    def which_layer(self, module_path: str) -> Layer:
        """Determine which architectural layer a module belongs to."""
        if module_path.startswith("substrate"):
            return Layer.SUBSTRATE
        elif module_path.startswith("adapters"):
            return Layer.ADAPTER
        elif module_path.startswith("transports"):
            return Layer.TRANSPORT
        elif module_path.startswith("projections"):
            return Layer.PROJECTION
        return Layer.INSTANCE

    def is_instance_value(self, value: str) -> bool:
        """Check if a string matches a known instance value."""
        if not self.instance.loaded:
            return False
        inst = self.instance
        known_values = {
            v for v in [
                inst.ai_name, inst.founder_name, inst.org_name,
                inst.org_id, inst.active_venture_id,
                inst.active_venture_name, inst.node_id,
            ] if v
        }
        for venture in inst.ventures:
            known_values.update(v for v in venture.values() if v)
        for product in inst.products:
            known_values.update(v for v in product.values() if v)
        return value in known_values

    # ── Operational Awareness ────────────────────────────────────────

    def capabilities(self) -> dict[str, Any]:
        """What components are registered — from the live registry."""
        registry = self._get("registry")
        if registry is None:
            return {"available": False, "components": 0}
        return {"available": True, "components": registry.count()}

    def runtimes(self) -> dict[str, Any]:
        """What execution runtimes exist — from the organism's runtime graph."""
        graph = self._get("runtime_graph")
        if graph is None:
            return {"available": False, "total": 0, "active": 0}
        return {
            "available": True,
            "total": graph.node_count,
            "active": graph.available_count,
        }

    def traces(self) -> dict[str, Any]:
        """What the system has executed — from the trace recorder."""
        recorder = self._get("trace_recorder")
        if recorder is None:
            return {"available": False, "count": 0}
        return {"available": True, "count": recorder.count()}

    def laws(self) -> dict[str, Any]:
        """What laws govern this system — from the ontology law registry."""
        try:
            from substrate.ontology.laws import _ALL_LAWS
            return {
                "available": True,
                "count": len(_ALL_LAWS),
                "names": [law.name for law in _ALL_LAWS],
            }
        except Exception:
            return {"available": False, "count": 0}

    def reality(self) -> dict[str, Any]:
        """What the system knows about reality — from the reality model."""
        result: dict[str, Any] = {"canonical": None, "instance": None}
        canonical = self._get("reality_model_canonical")
        if canonical is not None:
            result["canonical"] = canonical.stats()
        instance = self._get("reality_model_instance")
        if instance is not None:
            result["instance"] = instance.stats()
        return result

    def organism(self) -> dict[str, Any]:
        """The organism's health — from the observer."""
        observer = self._get("organism_observer")
        if observer is None:
            return {"available": False}
        try:
            snap = observer.snapshot()
            return {
                "available": True,
                "snapshot": snap.to_dict() if hasattr(snap, "to_dict") else str(snap),
            }
        except Exception as e:
            return {"available": False, "error": str(e)}

    def identity_continuity(self) -> dict[str, Any]:
        """Identity drift and continuity — from the foundation identity state."""
        state = self._get("identity_state")
        if state is None:
            return {"available": False}
        try:
            return {
                "available": True,
                "active_role": state.active_role,
                "anchor_count": len(state.anchors),
                "immutable_anchors": len(state.immutable_anchors()),
                "continuity_score": state.continuity_score,
            }
        except Exception:
            return {"available": False}

    # ── Unified Queries ──────────────────────────────────────────────

    def who_am_i(self) -> dict[str, Any]:
        """Full self-model snapshot — structure + identity + operational state."""
        if not self.instance.loaded:
            self.load_instance()

        return {
            "canonical": self.canonical.to_dict(),
            "instance": self.instance.to_dict(),
            "operational": {
                "uptime_seconds": time.monotonic() - self._boot_time,
                "subsystems_connected": list(self._subsystems.keys()),
                "capabilities": self.capabilities(),
                "runtimes": self.runtimes(),
                "traces": self.traces(),
                "laws": self.laws(),
                "reality": self.reality(),
                "organism": self.organism(),
                "identity_continuity": self.identity_continuity(),
            },
            "identity_summary": self._identity_summary(),
        }

    def _identity_summary(self) -> str:
        """One-line summary of current identity and state."""
        inst = self.instance
        parts = [f"I am {self.canonical.system_name}"]
        if inst.ai_name:
            parts.append(f"instantiated as {inst.ai_name}")
        if inst.org_name or inst.org_id:
            parts.append(f"for {inst.org_name or inst.org_id}")
        if inst.business_stage:
            parts.append(f"at {inst.business_stage} stage")
        rt = self.runtimes()
        if rt["available"]:
            parts.append(f"{rt['active']}/{rt['total']} runtimes")
        cap = self.capabilities()
        if cap["available"]:
            parts.append(f"{cap['components']} components")
        tr = self.traces()
        if tr["available"] and tr["count"] > 0:
            parts.append(f"{tr['count']} traces")
        return ", ".join(parts) + "."

    def to_dict(self) -> dict[str, Any]:
        return self.who_am_i()

    def handler_prefix(self) -> str:
        """Runtime prefix for handler names, event types, and similar identifiers.

        Derived from AI_NAME env var or loaded instance name. Falls back to "ai_".
        """
        name = os.environ.get("AI_NAME", "") or self.instance.ai_name
        if name:
            return name.lower() + "_"
        return "ai_"


def get_handler_prefix() -> str:
    """Return the AI-name-based prefix for handler names and event types.

    Pure env-var lookup — safe to call at import time, no self_model state needed.
    """
    name = os.environ.get("AI_NAME", "")
    if name:
        return name.lower() + "_"
    return "ai_"


# ── Module-level singleton ───────────────────────────────────────────────────

self_model = SelfModel()


def register_instance_loader(loader: "Callable[[InstanceSelf], None]") -> None:
    """Module-level shortcut: register a projection-specific instance loader."""
    self_model.register_instance_loader(loader)
