"""Application Registry Engine v1.

Registers known applications and tracks their capabilities,
trust levels, and bindings.

Known applications: EOS, LyfeOS, CreatorOS.
Future applications registered dynamically.

UMH substrate subsystem. Phase 96.8CD.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from core.applications.application_projection_contracts_v1 import (
    ApplicationTrustTier,
    _now_iso,
    _uuid_id,
)

KNOWN_APPLICATIONS: dict[str, dict[str, Any]] = {
    "eos": {
        "name": "EntrepreneurOS",
        "trust_tier": ApplicationTrustTier.CORE.value,
        "default_domain": "business",
    },
    "lyfeos": {
        "name": "LyfeOS",
        "trust_tier": ApplicationTrustTier.GOVERNED.value,
        "default_domain": "personal",
    },
    "creatoros": {
        "name": "CreatorOS",
        "trust_tier": ApplicationTrustTier.GOVERNED.value,
        "default_domain": "creator_media",
    },
}

MAX_APPLICATIONS = 20
MAX_BINDINGS_PER_APP = 50


class ApplicationRegistryEngine:
    """Registers and tracks applications."""

    def __init__(self, state_dir: str | Path = "data/runtime/applications") -> None:
        self._state_dir = Path(state_dir)
        self._state_dir.mkdir(parents=True, exist_ok=True)
        self._applications: dict[str, dict[str, Any]] = {}

    def register(
        self,
        app_id: str,
        name: str = "",
        trust_tier: str = "restricted",
        default_domain: str = "business",
    ) -> dict[str, Any]:
        if len(self._applications) >= MAX_APPLICATIONS:
            raise ValueError(
                f"Max applications ({MAX_APPLICATIONS}) reached"
            )

        if app_id in self._applications:
            return self._applications[app_id]

        known = KNOWN_APPLICATIONS.get(app_id)
        if known is not None:
            name = name or known["name"]
            trust_tier = known["trust_tier"]
            default_domain = known["default_domain"]

        app = {
            "app_id": app_id,
            "name": name or app_id,
            "trust_tier": trust_tier,
            "default_domain": default_domain,
            "capabilities": [],
            "continuity_bindings": [],
            "observability_bindings": [],
            "replay_bindings": [],
            "environment_bindings": [],
            "registered_at": _now_iso(),
        }
        self._applications[app_id] = app

        path = self._state_dir / "registry.jsonl"
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(app, default=str) + "\n")

        return app

    def get(self, app_id: str) -> dict[str, Any] | None:
        return self._applications.get(app_id)

    def get_all(self) -> list[dict[str, Any]]:
        return list(self._applications.values())

    def get_by_trust_tier(self, trust_tier: str) -> list[dict[str, Any]]:
        return [
            a for a in self._applications.values()
            if a["trust_tier"] == trust_tier
        ]

    def add_capability(self, app_id: str, capability: str) -> bool:
        app = self._applications.get(app_id)
        if app is None:
            return False
        if len(app["capabilities"]) >= MAX_BINDINGS_PER_APP:
            return False
        if capability not in app["capabilities"]:
            app["capabilities"].append(capability)
        return True

    def add_binding(
        self,
        app_id: str,
        binding_type: str,
        binding_value: str,
    ) -> bool:
        app = self._applications.get(app_id)
        if app is None:
            return False
        key = f"{binding_type}_bindings"
        if key not in app:
            return False
        bindings = app[key]
        if len(bindings) >= MAX_BINDINGS_PER_APP:
            return False
        if binding_value not in bindings:
            bindings.append(binding_value)
        return True

    def get_stats(self) -> dict[str, object]:
        return {
            "total_applications": len(self._applications),
            "known_applications": len(KNOWN_APPLICATIONS),
            "max_applications": MAX_APPLICATIONS,
        }
