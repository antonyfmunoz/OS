"""Node mesh configuration loader."""

from __future__ import annotations

import logging
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
    heartbeat_timeout_s: int = 90
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
