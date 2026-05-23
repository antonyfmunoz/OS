"""Standalone launcher for the UMH Node Mesh server.

Usage: python3 -m services.umh.node_mesh.run
"""

from __future__ import annotations

import logging
import signal
import sys
import threading

sys.path.insert(0, "/opt/OS")

from services.umh.execution.executor import WorkPacketExecutor
from services.umh.node_mesh.config import load_mesh_config
from services.umh.node_mesh.server import NodeMeshServer
from substrate.sockets.capability_socket import CapabilitySocket
from substrate.sockets.outcome_socket import OutcomeSocket
from substrate.sockets.signal_socket import SignalSocket
from substrate.sockets.view_socket import ViewSocket

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger("node_mesh")


def main() -> None:
    config = load_mesh_config()
    logger.info("loaded mesh config: port=%d, max_nodes=%d, tokens=%d",
                config.port, config.max_nodes, len(config.node_tokens))

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
