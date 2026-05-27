#!/usr/bin/env python3
"""Memory Watcher Daemon — runs the substrate memory watcher.

Watches agent memory directories for new/modified files and
instantly syncs them to the canonical memory store.

Usage:
    python3 scripts/memory_watcher_daemon.py              # foreground
    python3 scripts/memory_watcher_daemon.py --add /path agent-name  # add custom dir

Agent-agnostic: any process that writes a .md file with YAML
frontmatter to a watched directory gets auto-synced.
"""

import logging
import signal
import os
import sys
import time

sys.path.insert(0, os.environ.get("UMH_ROOT", "/opt/OS"))

from substrate.memory.watcher import start_memory_watcher

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("memory-watcher")


def main():
    watcher = start_memory_watcher()

    if "--add" in sys.argv:
        idx = sys.argv.index("--add")
        if idx + 2 < len(sys.argv):
            path = sys.argv[idx + 1]
            agent = sys.argv[idx + 2]
            watcher.add_directory(path, agent_name=agent)
            logger.info("Added custom watch: %s for %s", path, agent)

    logger.info("Watching %d directories. Ctrl+C to stop.", len(watcher.watches))
    for w in watcher.watches:
        logger.info("  %s", w)

    shutdown = False

    def handle_signal(signum, frame):
        nonlocal shutdown
        shutdown = True

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    while not shutdown:
        time.sleep(1)

    watcher.stop()
    logger.info("Stopped.")


if __name__ == "__main__":
    main()
