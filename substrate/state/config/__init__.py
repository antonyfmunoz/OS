"""
UMH Config Store — layered configuration with runtime mutability.

Four config layers (most general → most specific):
  system  — one per UMH installation (ai_name, timezone, instance_id)
  user    — one per operator (display_name, preferences)
  venture — one per venture (offer defaults, channel strategies)
  channel — one per channel (discord guild, cockpit instance)

Resolution: channel → venture → user → system → hardcoded default.
Most specific wins. Missing keys fall through to the next layer.

Persistence: system + user layers → JSON files in data/umh/config/.
Venture + channel layers → BIS / DB (future, not in v1).

Usage:
    from substrate.state.config import config_store
    ai_name = config_store.get("ai_name")            # resolved value
    config_store.set("ai_name", "ARIA", layer="system")
    config_store.get_all()  # full merged dict
"""

from substrate.state.config.config_store import ConfigStore

config_store = ConfigStore()

__all__ = ["config_store", "ConfigStore"]
