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


def _ensure_docker_relay_access(http_port: int) -> None:
    """Add iptables rule so Docker containers can reach the HTTP relay."""
    if os.geteuid() != 0:
        return
    import subprocess
    from substrate.execution.cpu_gate import gated_subprocess_run
    check = gated_subprocess_run(
        ["iptables", "-C", "INPUT", "-s", "172.18.0.0/16", "-p", "tcp",
         "--dport", str(http_port), "-j", "ACCEPT"],
        caller="mesh_relay_iptables_check",
    )
    if check is not None and check.returncode == 0:
        return
    result = gated_subprocess_run(
        ["iptables", "-I", "INPUT", "1", "-s", "172.18.0.0/16", "-p", "tcp",
         "--dport", str(http_port), "-j", "ACCEPT"],
        caller="mesh_relay_iptables_add",
    )
    if result is not None and result.returncode == 0:
        logger.info("added iptables INPUT rule for Docker → port %d", http_port)
    else:
        logger.warning("failed to add iptables rule for port %d", http_port)


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
