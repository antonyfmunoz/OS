"""Node mesh configuration loader and token management."""

from __future__ import annotations

import base64
import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

DEFAULT_CONFIG_PATH = Path("/opt/OS/data/umh/mesh/node_mesh_config.toml")


@dataclass
class NodeTokenEntry:
    node_id: str
    token: str
    display_name: str = ""


@dataclass
class MeshConfig:
    port: int = 8094
    heartbeat_interval_s: int = 5
    heartbeat_timeout_s: int = 30
    max_nodes: int = 10
    buffer_size: int = 1000
    flush_interval_s: int = 300
    anomaly_cpu_threshold: float = 90.0
    anomaly_disk_threshold: float = 95.0
    anomaly_battery_threshold: float = 10.0
    node_tokens: dict[str, NodeTokenEntry] = field(default_factory=dict)


def load_mesh_config(path: Path | None = None) -> MeshConfig:
    """Load mesh config from TOML file, falling back to defaults."""
    path = path or DEFAULT_CONFIG_PATH
    config = MeshConfig()

    if not path.exists():
        logger.info("no mesh config at %s, using defaults", path)
        return config

    try:
        import tomllib
    except ModuleNotFoundError:
        import tomli as tomllib  # type: ignore[no-redef]

    try:
        with open(path, "rb") as f:
            data = tomllib.load(f)
    except Exception as exc:
        logger.warning("failed to load mesh config: %s", exc)
        return config

    server = data.get("server", {})
    config.port = server.get("port", config.port)
    config.heartbeat_interval_s = server.get("heartbeat_interval_s", config.heartbeat_interval_s)
    config.heartbeat_timeout_s = server.get("heartbeat_timeout_s", config.heartbeat_timeout_s)
    config.max_nodes = server.get("max_nodes", config.max_nodes)

    metrics = data.get("metrics", {})
    config.buffer_size = metrics.get("buffer_size", config.buffer_size)
    config.flush_interval_s = metrics.get("flush_interval_s", config.flush_interval_s)
    config.anomaly_cpu_threshold = metrics.get(
        "anomaly_cpu_threshold", config.anomaly_cpu_threshold
    )
    config.anomaly_disk_threshold = metrics.get(
        "anomaly_disk_threshold", config.anomaly_disk_threshold
    )
    config.anomaly_battery_threshold = metrics.get(
        "anomaly_battery_threshold", config.anomaly_battery_threshold
    )

    nodes = data.get("nodes", {})
    for node_id, node_data in nodes.items():
        if isinstance(node_data, dict) and "token" in node_data:
            config.node_tokens[node_id] = NodeTokenEntry(
                node_id=node_id,
                token=node_data["token"],
                display_name=node_data.get("display_name", node_id),
            )

    return config


# ── Token Management ──────────────────────────────────────────────────


def generate_token() -> str:
    """Generate a cryptographically random mesh auth token."""
    return base64.urlsafe_b64encode(os.urandom(32)).rstrip(b"=").decode()


def _serialize_toml(data: dict[str, Any]) -> str:
    """Serialize a simple nested dict to TOML string.

    Handles [section] and [section.subsection] patterns. Values are
    strings (quoted) or numbers (bare).
    """
    lines: list[str] = []
    for section, values in data.items():
        if not isinstance(values, dict):
            continue
        has_nested = any(isinstance(v, dict) for v in values.values())
        if has_nested:
            for sub_key, sub_val in values.items():
                if isinstance(sub_val, dict):
                    lines.append(f"[{section}.{sub_key}]")
                    for k, v in sub_val.items():
                        if isinstance(v, str):
                            lines.append(f'{k} = "{v}"')
                        else:
                            lines.append(f"{k} = {v}")
                    lines.append("")
                else:
                    if not any(l.startswith(f"[{section}]") for l in lines):
                        lines.insert(0, f"[{section}]")
                        lines.insert(1, "")
                    idx = lines.index(f"[{section}]") + 1
                    if isinstance(sub_val, str):
                        lines.insert(idx, f'{sub_key} = "{sub_val}"')
                    else:
                        lines.insert(idx, f"{sub_key} = {sub_val}")
        else:
            lines.append(f"[{section}]")
            for k, v in values.items():
                if isinstance(v, str):
                    lines.append(f'{k} = "{v}"')
                else:
                    lines.append(f"{k} = {v}")
            lines.append("")
    return "\n".join(lines) + "\n"


def _read_toml_data(path: Path) -> dict[str, Any]:
    """Read TOML file into a dict."""
    try:
        import tomllib
    except ModuleNotFoundError:
        import tomli as tomllib  # type: ignore[no-redef]

    if not path.exists():
        return {}
    with open(path, "rb") as f:
        return tomllib.load(f)


def add_node_token(
    config_path: Path | None,
    node_id: str,
    display_name: str,
) -> str:
    """Add a new node token to the config. Returns the generated token."""
    path = config_path or DEFAULT_CONFIG_PATH
    data = _read_toml_data(path)

    token = generate_token()

    if "nodes" not in data:
        data["nodes"] = {}
    data["nodes"][node_id] = {
        "token": token,
        "display_name": display_name,
    }

    if "server" not in data:
        data["server"] = {"port": 8094}

    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(_serialize_toml(data))
    tmp.replace(path)

    logger.info("Added mesh token for node %s", node_id)
    return token


def remove_node_token(
    config_path: Path | None,
    node_id: str,
) -> bool:
    """Remove a node token from the config. Returns True if removed."""
    path = config_path or DEFAULT_CONFIG_PATH
    data = _read_toml_data(path)

    nodes = data.get("nodes", {})
    if node_id not in nodes:
        return False

    del nodes[node_id]

    tmp = path.with_suffix(".tmp")
    tmp.write_text(_serialize_toml(data))
    tmp.replace(path)

    logger.info("Removed mesh token for node %s", node_id)
    return True
