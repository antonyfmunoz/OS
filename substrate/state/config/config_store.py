"""
ConfigStore — layered JSON-file-backed configuration.

Resolution order (most specific wins):
  channel → venture → user → system → DEFAULTS

System and user layers persist to data/umh/config/.
Venture and channel layers are in-memory overlays
populated at runtime by transports (e.g. organism bridge).

Thread-safe via a reentrant lock on all mutations.
"""

from __future__ import annotations

import json
import logging
import os
import threading
from pathlib import Path
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)

_ROOT = os.environ.get("UMH_ROOT", "/opt/OS")
_CONFIG_DIR = Path(_ROOT) / "data" / "umh" / "config"

LAYERS = ("system", "user", "venture", "channel")

DEFAULTS: dict[str, Any] = {
    "ai_name": "Assistant",
    "timezone": "UTC",
    "locale": "en",
    "theme": "dark",
}

VALID_KEYS: set[str] = {
    "ai_name",
    "timezone",
    "locale",
    "theme",
    "founder_name",
    "org_name",
    "display_mode",
}


class ConfigStore:
    """Layered config with JSON persistence and change notification."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._layers: dict[str, dict[str, Any]] = {layer: {} for layer in LAYERS}
        self._listeners: list[Callable[[str, Any, str], None]] = []
        self._load_persisted()

    def _layer_path(self, layer: str) -> Path:
        return _CONFIG_DIR / f"{layer}.json"

    def _load_persisted(self) -> None:
        for layer in ("system", "user"):
            path = self._layer_path(layer)
            if path.exists():
                try:
                    data = json.loads(path.read_text(encoding="utf-8"))
                    if isinstance(data, dict):
                        self._layers[layer] = data
                        logger.debug("Loaded config layer %s from %s", layer, path)
                except Exception:
                    logger.exception("Failed to load config layer %s", layer)

    def _persist(self, layer: str) -> None:
        if layer not in ("system", "user"):
            return
        path = self._layer_path(layer)
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        try:
            tmp.write_text(
                json.dumps(self._layers[layer], indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            tmp.replace(path)
        except Exception:
            logger.exception("Failed to persist config layer %s", layer)
            if tmp.exists():
                tmp.unlink(missing_ok=True)

    def get(self, key: str, default: Any = None) -> Any:
        """Resolve a config key across all layers (most specific wins)."""
        with self._lock:
            for layer in reversed(LAYERS):
                val = self._layers[layer].get(key)
                if val is not None:
                    return val
            return DEFAULTS.get(key, default)

    def get_layer(self, layer: str) -> dict[str, Any]:
        """Return a copy of a single layer's values."""
        with self._lock:
            return dict(self._layers.get(layer, {}))

    def get_all(self) -> dict[str, Any]:
        """Return the fully resolved config (all layers merged)."""
        with self._lock:
            merged = dict(DEFAULTS)
            for layer in LAYERS:
                merged.update(self._layers[layer])
            return merged

    def set(self, key: str, value: Any, layer: str = "system") -> None:
        """Set a config value in the specified layer and persist."""
        if layer not in LAYERS:
            raise ValueError(f"Invalid layer: {layer}. Must be one of {LAYERS}")
        with self._lock:
            old = self.get(key)
            self._layers[layer][key] = value
            self._persist(layer)
            new = self.get(key)
        if old != new:
            self._notify(key, new, layer)

    def delete(self, key: str, layer: str = "system") -> None:
        """Remove a key from a layer."""
        with self._lock:
            if key in self._layers.get(layer, {}):
                del self._layers[layer][key]
                self._persist(layer)

    def set_layer(self, layer: str, data: dict[str, Any]) -> None:
        """Replace an entire layer's data (used by runtime loaders)."""
        if layer not in LAYERS:
            raise ValueError(f"Invalid layer: {layer}. Must be one of {LAYERS}")
        with self._lock:
            self._layers[layer] = dict(data)
            self._persist(layer)

    def on_change(self, listener: Callable[[str, Any, str], None]) -> Callable[[], None]:
        """Register a change listener. Returns unsubscribe function.

        Listener receives (key, new_value, layer).
        """
        self._listeners.append(listener)

        def unsub() -> None:
            try:
                self._listeners.remove(listener)
            except ValueError:
                pass

        return unsub

    def _notify(self, key: str, value: Any, layer: str) -> None:
        for fn in list(self._listeners):
            try:
                fn(key, value, layer)
            except Exception:
                logger.exception("Config change listener error")

    def seed_from_instance_json(self) -> None:
        """Bootstrap system layer from data/umh/instance.json if system.json is empty."""
        with self._lock:
            if self._layers["system"]:
                return
        instance_path = Path(_ROOT) / "data" / "umh" / "instance.json"
        if not instance_path.exists():
            return
        try:
            data = json.loads(instance_path.read_text(encoding="utf-8"))
            seed: dict[str, Any] = {}
            if data.get("ai_name"):
                seed["ai_name"] = data["ai_name"]
            if data.get("founder_name"):
                seed["founder_name"] = data["founder_name"]
            if data.get("org_name"):
                seed["org_name"] = data["org_name"]
            if seed:
                with self._lock:
                    self._layers["system"].update(seed)
                    self._persist("system")
                logger.info("Seeded config from instance.json: %s", list(seed.keys()))
        except Exception:
            logger.exception("Failed to seed config from instance.json")
