"""Node daemon configuration — reads umh_node.toml and .env."""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

if sys.platform == "win32":
    DEFAULT_CONFIG_DIR = Path(os.environ.get("PROGRAMDATA", "C:\\ProgramData")) / "UMH"
else:
    DEFAULT_CONFIG_DIR = Path.home() / ".umh"

DEFAULT_CONFIG_PATH = DEFAULT_CONFIG_DIR / "umh_node.toml"
DEFAULT_ENV_PATH = DEFAULT_CONFIG_DIR / ".env"
DEFAULT_LOG_DIR = DEFAULT_CONFIG_DIR / "logs"


@dataclass
class CapabilityConfig:
    enabled: bool = True
    max_risk_class: str = "IRREVERSIBLE_WRITE"
    allowed_commands: list[str] = field(default_factory=list)
    allowed_paths: list[str] = field(default_factory=list)


@dataclass
class SignalsConfig:
    metrics_interval_s: int = 30
    workspace_enabled: bool = True
    workspace_debounce_s: float = 2.0
    filewatch_enabled: bool = False
    filewatch_paths: list[str] = field(default_factory=list)
    filewatch_debounce_s: float = 2.0


@dataclass
class NodeConfig:
    vps_host: str = ""
    vps_port: int = 8094
    node_id: str = ""
    hostname: str = ""
    token: str = ""
    reconnect_max_backoff_s: int = 60
    capabilities: dict[str, CapabilityConfig] = field(default_factory=dict)
    signals: SignalsConfig = field(default_factory=SignalsConfig)

    @property
    def ws_url(self) -> str:
        return f"ws://{self.vps_host}:{self.vps_port}/ws?token={self.token}"


def _load_env(path: Path) -> None:
    """Load key=value pairs from .env file into os.environ."""
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" in line:
            key, _, value = line.partition("=")
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def load_node_config(config_path: Path | None = None, env_path: Path | None = None) -> NodeConfig:
    """Load config from TOML + .env, falling back to defaults and env vars."""
    env_path = env_path or DEFAULT_ENV_PATH
    _load_env(env_path)

    config = NodeConfig(
        vps_host=os.environ.get("UMH_VPS_HOST", ""),
        vps_port=int(os.environ.get("UMH_VPS_PORT", "8094")),
        token=os.environ.get("UMH_NODE_TOKEN", ""),
        node_id=os.environ.get("UMH_NODE_ID", ""),
        hostname=os.environ.get("UMH_HOSTNAME", ""),
    )

    config_path = config_path or DEFAULT_CONFIG_PATH
    if not config_path.exists():
        return config

    try:
        import tomllib
    except ModuleNotFoundError:
        try:
            import tomli as tomllib  # type: ignore[no-redef]
        except ModuleNotFoundError:
            return config

    try:
        with open(config_path, "rb") as f:
            data = tomllib.load(f)
    except Exception:
        return config

    conn = data.get("connection", {})
    config.vps_host = conn.get("vps_host", config.vps_host)
    config.vps_port = conn.get("vps_port", config.vps_port)
    config.reconnect_max_backoff_s = conn.get(
        "reconnect_max_backoff_s", config.reconnect_max_backoff_s
    )

    identity = data.get("identity", {})
    config.node_id = identity.get("node_id", config.node_id)
    config.hostname = identity.get("hostname", config.hostname)

    for cap_name, cap_data in data.get("capabilities", {}).items():
        if isinstance(cap_data, dict):
            config.capabilities[cap_name] = CapabilityConfig(
                enabled=cap_data.get("enabled", True),
                max_risk_class=cap_data.get("max_risk_class", "IRREVERSIBLE_WRITE"),
                allowed_commands=cap_data.get("allowed_commands", []),
                allowed_paths=cap_data.get("allowed_paths", []),
            )

    sigs = data.get("signals", {})
    metrics = sigs.get("metrics", {})
    config.signals.metrics_interval_s = metrics.get("interval_s", config.signals.metrics_interval_s)

    workspace = sigs.get("workspace", {})
    config.signals.workspace_enabled = workspace.get("enabled", config.signals.workspace_enabled)
    config.signals.workspace_debounce_s = workspace.get(
        "debounce_s", config.signals.workspace_debounce_s
    )

    filewatch = sigs.get("filewatch", {})
    config.signals.filewatch_enabled = filewatch.get("enabled", config.signals.filewatch_enabled)
    config.signals.filewatch_paths = filewatch.get("paths", config.signals.filewatch_paths)
    config.signals.filewatch_debounce_s = filewatch.get(
        "debounce_s", config.signals.filewatch_debounce_s
    )

    return config
