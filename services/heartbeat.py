#!/usr/bin/env python3
"""
EOS Heartbeat Service
=====================
Scheduled jobs that run independent of Claude Code.
System health monitoring, self-awareness checks,
and periodic maintenance.

Runs as a standalone process or via cron.
Each job has a name, interval (seconds), and function.
"""

import json
import logging
import os
import sys
import time
from datetime import datetime
from zoneinfo import ZoneInfo

_ROOT = os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS"
sys.path.insert(0, _ROOT)

from dotenv import load_dotenv

load_dotenv(os.path.join(_ROOT, "runtime", ".env"))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger("heartbeat")
PDT = ZoneInfo("America/Los_Angeles")


def system_health_heartbeat() -> None:
    """EOS monitors its own operational state every 30 minutes."""
    from observability.health.system_health import get_system_health

    sh = get_system_health()

    # Quick status to log
    status = sh.system_check()
    logger.info(f"System check:\n{status}")

    # Alert if degraded
    sh.alert_if_degraded(threshold="COMPROMISED")

    # Log full report for audit
    try:
        os.makedirs(os.path.join(_ROOT, "logs"), exist_ok=True)
        report = {
            "timestamp": datetime.now(PDT).isoformat(),
            "quality_level": sh.quality_level(),
            "providers": sh.provider_status(),
        }
        with open(os.path.join(_ROOT, "logs", "heartbeat.log"), "a") as f:
            f.write(json.dumps(report, default=str) + "\n")
    except Exception as e:
        logger.warning(f"Failed to write heartbeat log: {e}")


# Job registry
JOBS = [
    {
        "name": "system_health_check",
        "interval": 1800,  # 30 minutes
        "func": system_health_heartbeat,
        "description": "EOS monitors own operational state",
    },
]


def run_once() -> None:
    """Run all jobs once (for cron or manual trigger)."""
    for job in JOBS:
        logger.info(f"Running: {job['name']}")
        try:
            job["func"]()
            logger.info(f"Completed: {job['name']}")
        except Exception as e:
            logger.error(f"Failed: {job['name']}: {e}")


def run_loop() -> None:
    """Run jobs on their intervals (long-running process)."""
    logger.info(f"Heartbeat started with {len(JOBS)} jobs")
    last_run: dict[str, float] = {}

    while True:
        now = time.time()
        for job in JOBS:
            name = job["name"]
            interval = job["interval"]
            last = last_run.get(name, 0)

            if now - last >= interval:
                logger.info(f"Running: {name}")
                try:
                    job["func"]()
                    logger.info(f"Completed: {name}")
                except Exception as e:
                    logger.error(f"Failed: {name}: {e}")
                last_run[name] = now

        time.sleep(60)  # Check every minute


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--once":
        run_once()
    else:
        run_loop()
