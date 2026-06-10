"""Standalone launcher for the UMH Node Mesh server.

Usage: python3 -m transports.node_mesh.run
"""

from __future__ import annotations

import logging
import signal
import os
import sys
import threading

sys.path.insert(0, os.environ.get("UMH_ROOT", "/opt/OS"))

from substrate.execution.executor import WorkPacketExecutor
from transports.node_mesh.config import load_mesh_config
from transports.node_mesh.server import NodeMeshServer
from substrate.sockets.capability_socket import CapabilitySocket
from substrate.sockets.outcome_socket import OutcomeSocket
from substrate.sockets.signal_socket import SignalSocket
from substrate.sockets.view_socket import ViewSocket

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger("node_mesh")


_RELAY_CHAIN = "UMH_MESH_RELAY"
_DOCKER_CIDR = "172.18.0.0/16"


def _validate_relay_port(port: object) -> int:
    """Validate relay port is an integer in the unprivileged range."""
    try:
        value = int(port)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        raise ValueError(f"invalid relay port: {port!r}")
    if value < 1024 or value > 65535:
        raise ValueError(f"relay port out of allowed range: {value}")
    return value


def _ensure_docker_relay_access(http_port: object) -> None:
    """Create a dedicated iptables chain for Docker→relay access.

    Uses a dedicated UMH_MESH_RELAY chain jumped to from INPUT.
    Idempotent — safe to call on every startup.
    """
    if os.geteuid() != 0:
        logger.info("not root — skipping iptables setup for relay port")
        return

    port = _validate_relay_port(http_port)
    from substrate.execution.cpu_gate import gated_subprocess_run

    def _ipt(*args: str, caller: str = "mesh_relay_fw") -> int:
        r = gated_subprocess_run(["iptables", *args], caller=caller)
        return r.returncode if r is not None else 1

    # 1. Create dedicated chain if it doesn't exist
    if _ipt("-N", _RELAY_CHAIN) == 0:
        logger.info("created iptables chain %s", _RELAY_CHAIN)

    # 2. Flush the chain to ensure exactly one rule (idempotent on restart)
    _ipt("-F", _RELAY_CHAIN)

    # 3. Add the scoped ACCEPT rule inside the dedicated chain
    rc = _ipt(
        "-A", _RELAY_CHAIN,
        "-s", _DOCKER_CIDR, "-p", "tcp", "--dport", str(port),
        "-j", "ACCEPT",
    )
    if rc != 0:
        logger.warning("failed to add ACCEPT rule in %s for port %d", _RELAY_CHAIN, port)
        return

    # 4. Add RETURN at end of chain (explicit — traffic not matching falls back to INPUT)
    _ipt("-A", _RELAY_CHAIN, "-j", "RETURN")

    # 5. Ensure INPUT jumps to our chain (skip if already present)
    jump_check = _ipt("-C", "INPUT", "-j", _RELAY_CHAIN)
    if jump_check != 0:
        _ipt("-A", "INPUT", "-j", _RELAY_CHAIN)
        logger.info("added INPUT → %s jump for Docker relay port %d", _RELAY_CHAIN, port)
    else:
        logger.info("iptables %s chain already active for port %d", _RELAY_CHAIN, port)

    # 6. Clean up any legacy top-of-chain rule from 14.13N
    legacy_check = _ipt(
        "-C", "INPUT",
        "-s", _DOCKER_CIDR, "-p", "tcp", "--dport", str(port),
        "-j", "ACCEPT",
    )
    if legacy_check == 0:
        _ipt(
            "-D", "INPUT",
            "-s", _DOCKER_CIDR, "-p", "tcp", "--dport", str(port),
            "-j", "ACCEPT",
        )
        logger.info("removed legacy top-of-chain INPUT rule for port %d", port)


def main() -> None:
    config = load_mesh_config()
    logger.info(
        "loaded mesh config: port=%d, max_nodes=%d, tokens=%d",
        config.port,
        config.max_nodes,
        len(config.node_tokens),
    )

    server = NodeMeshServer(
        config=config,
        executor=WorkPacketExecutor(),
        signal_socket=SignalSocket(),
        capability_socket=CapabilitySocket(),
        outcome_socket=OutcomeSocket(),
        view_socket=ViewSocket(),
    )

    shutdown = threading.Event()

    def handle_signal(signum, frame):
        logger.info("shutdown signal received")
        shutdown.set()

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    _ensure_docker_relay_access(config.port + 1)

    try:
        from umh.vision_relay import receive_mesh_frame
        server.register_frame_callback(
            lambda node_id, b64: receive_mesh_frame({"node_id": node_id, "image_base64": b64})
        )
        logger.info("vision relay frame callback registered")
    except ImportError:
        logger.info("vision relay not available — camera frame forwarding disabled")

    thread = server.start()
    logger.info("node mesh server running on port %d — waiting for connections", config.port)

    try:
        shutdown.wait()
    except KeyboardInterrupt:
        pass

    logger.info("stopping mesh server...")
    server.stop()
    thread.join(timeout=5)
    logger.info("mesh server stopped")


if __name__ == "__main__":
    main()
