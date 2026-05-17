"""trigger_export.py — VPS-side trigger for browser exports on Windows.

Dispatches a 'fire_export' command through the local bridge to the Windows
workstation. Windows executes the Playwright export; MFA challenges surface
back via the bridge to Discord.

Usage:
    python3 services/trigger_export.py --service claude
    python3 services/trigger_export.py --service chatgpt
    python3 services/trigger_export.py --service instagram
    python3 services/trigger_export.py --service all
    python3 services/trigger_export.py --service claude --dry-run
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from pathlib import Path
from typing import Any

import requests

_REPO_ROOT = Path(__file__).parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")
load_dotenv(_REPO_ROOT / "runtime" / ".env")

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

_BRIDGE_IP = os.getenv("EOS_LOCAL_BRIDGE_IP", "100.74.199.102")
_BRIDGE_PORT = int(os.getenv("EOS_LOCAL_BRIDGE_PORT", "8766"))
_BASE_URL = f"http://{_BRIDGE_IP}:{_BRIDGE_PORT}"
_SEND_TIMEOUT_S = 15.0

VALID_SERVICES = ("claude", "chatgpt", "instagram", "all")


def _check_bridge_health() -> bool:
    """Verify Windows bridge is reachable."""
    try:
        resp = requests.get(f"{_BASE_URL}/health", timeout=3.0)
        return resp.status_code == 200
    except (requests.ConnectionError, requests.Timeout, OSError):
        return False


def fire_export(service: str, dry_run: bool = False) -> dict[str, Any]:
    """Dispatch a fire_export command to the Windows bridge.

    Returns the bridge response or an error dict.
    """
    if service not in VALID_SERVICES:
        return {"ok": False, "error": f"invalid service: {service}"}

    if not _check_bridge_health():
        return {"ok": False, "error": "bridge unreachable — Windows machine offline?"}

    payload = {
        "type": "fire_export",
        "service": service,
        "dry_run": dry_run,
    }

    try:
        resp = requests.post(
            f"{_BASE_URL}/fire-export",
            json=payload,
            timeout=_SEND_TIMEOUT_S,
        )
        result = resp.json()
        return result
    except requests.Timeout:
        return {"ok": False, "error": "bridge timeout — Windows may be busy"}
    except (requests.ConnectionError, OSError) as exc:
        return {"ok": False, "error": f"bridge connection failed: {exc}"}
    except Exception as exc:
        return {"ok": False, "error": f"unexpected: {exc}"}


def main() -> None:
    parser = argparse.ArgumentParser(description="Trigger browser export on Windows")
    parser.add_argument(
        "--service",
        required=True,
        choices=VALID_SERVICES,
        help="Service to export (or 'all')",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Dispatch without actually executing on Windows",
    )
    args = parser.parse_args()

    services = ["claude", "chatgpt", "instagram"] if args.service == "all" else [args.service]

    for svc in services:
        logger.info("Triggering export: %s (dry_run=%s)", svc, args.dry_run)
        result = fire_export(svc, dry_run=args.dry_run)

        if result.get("ok"):
            logger.info("[%s] Bridge accepted: %s", svc, result.get("message", ""))
        else:
            logger.error("[%s] Failed: %s", svc, result.get("error", "unknown"))


if __name__ == "__main__":
    main()
