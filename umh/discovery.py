"""Discovery — background environment scan for reality model population.

Wraps EnvironmentMapping's 20 discovery domains into a background scan
that runs during boot. This is the beginning of Phase 6 (automated
diagnostic scan) — the step that populates the reality model with the
operator's actual environment data.

The scan discovers:
  - Installed platforms (Chrome, VS Code, Obsidian, Notion, etc.)
  - Active accounts (Google, GitHub, Discord, Slack)
  - Workspaces (repos, vaults, containers)
  - Relationships between discovered entities
  - Ingestion lanes (how to extract data from each platform)

The scan runs in a background thread so the operator can start using
the system immediately while discovery proceeds.
"""

from __future__ import annotations

import json
import logging
import os
import sys
import threading
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)

sys.path.insert(0, os.environ.get("UMH_ROOT", "/opt/OS"))

UMH_ROOT = os.environ.get("UMH_ROOT", "/opt/OS")
DISCOVERY_DIR = os.path.join(UMH_ROOT, "data", "environment_maps")

DISCOVERY_DOMAINS = [
    "chrome_profiles",
    "google_accounts",
    "notion",
    "discord",
    "claude",
    "openai",
    "github",
    "gmail",
    "drive",
    "slack",
    "local_vaults",
    "obsidian",
    "vscode",
    "cursor",
    "terminals",
    "local_repos",
    "docker_containers",
    "startup_apps",
    "browser_sessions",
    "installed_desktop_apps",
]


@dataclass
class DiscoveryResult:
    """Summary of a discovery scan."""

    domains_scanned: int = 0
    platforms_found: int = 0
    accounts_found: int = 0
    workspaces_found: int = 0
    maturity_level: str = "L0_NO_MAPPING"
    scan_duration_seconds: float = 0.0
    proof_path: str | None = None
    errors: list[str] = field(default_factory=list)
    started_at: str = ""
    completed_at: str = ""

    def as_dict(self) -> dict:
        return {
            "domains_scanned": self.domains_scanned,
            "platforms_found": self.platforms_found,
            "accounts_found": self.accounts_found,
            "workspaces_found": self.workspaces_found,
            "maturity_level": self.maturity_level,
            "scan_duration_seconds": self.scan_duration_seconds,
            "proof_path": self.proof_path,
            "errors": self.errors,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
        }


class DiscoveryScanner:
    """Manages background environment discovery scans."""

    def __init__(self) -> None:
        self._thread: threading.Thread | None = None
        self._result: DiscoveryResult | None = None
        self._running = False

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def result(self) -> DiscoveryResult | None:
        return self._result

    def start_background_scan(self) -> bool:
        """Start environment scan in a background thread.

        Returns True if scan started, False if already running or failed.
        """
        if self._running:
            return False

        self._running = True
        self._result = None
        self._thread = threading.Thread(target=self._run_scan, daemon=True, name="umh-discovery")
        self._thread.start()
        return True

    def run_synchronous(self) -> None:
        """Run the discovery scan in the current thread (blocking)."""
        if self._running:
            return
        self._running = True
        self._result = None
        self._run_scan()

    def _run_scan(self) -> None:
        """Execute the scan (runs in background thread)."""
        result = DiscoveryResult(
            started_at=datetime.now(datetime.UTC).isoformat(),
        )
        start_time = datetime.now(datetime.UTC)

        try:
            try:
                result = self._scan_with_substrate(result)
            except Exception as exc:
                logger.debug("Substrate scan failed, using basic scan: %s", exc)
                result = self._scan_basic(result)

            end_time = datetime.now(datetime.UTC)
            result.scan_duration_seconds = (end_time - start_time).total_seconds()
            result.completed_at = end_time.isoformat()

            self._save_result(result)
            self._result = result
            logger.info(
                "Discovery scan complete: %d platforms, %d accounts, %d workspaces (%.1fs)",
                result.platforms_found,
                result.accounts_found,
                result.workspaces_found,
                result.scan_duration_seconds,
            )
        except Exception as exc:
            logger.debug("Discovery scan failed: %s", exc)
        finally:
            self._running = False

    def _scan_with_substrate(self, result: DiscoveryResult) -> DiscoveryResult:
        """Use the substrate's EnvironmentMapping engine."""
        from substrate.execution.workers.workstation.environment_mapping_engine_v1 import (
            build_full_environment_proof,
            send_explore_environment_request,
        )

        relay_result = send_explore_environment_request(timeout_seconds=120)
        proof = build_full_environment_proof(relay_result, founder_confirmed=False)

        result.domains_scanned = len(DISCOVERY_DOMAINS)
        result.platforms_found = len(proof.topology.platforms)
        result.accounts_found = len(proof.topology.accounts)
        result.workspaces_found = len(proof.topology.workspaces)
        result.maturity_level = proof.maturity_level

        # Persist the proof
        from substrate.execution.workers.workstation.environment_mapping_engine_v1 import (
            persist_environment_mapping_proof,
        )

        proof_path = persist_environment_mapping_proof(proof)
        result.proof_path = str(proof_path)

        return result

    def _scan_basic(self, result: DiscoveryResult) -> DiscoveryResult:
        """Basic discovery without substrate — checks what's locally available."""
        import shutil
        import subprocess

        platforms: list[str] = []
        workspaces: list[str] = []

        # Check installed tools
        tool_checks = {
            "git": "github",
            "docker": "docker_containers",
            "code": "vscode",
            "ollama": "ollama",
            "obsidian": "obsidian",
            "cursor": "cursor",
            "node": "nodejs",
            "python3": "python",
        }
        for cmd, name in tool_checks.items():
            if shutil.which(cmd):
                platforms.append(name)

        # Check for local repos
        home = os.path.expanduser("~")
        common_repo_dirs = [
            os.path.join(home, "dev"),
            os.path.join(home, "projects"),
            os.path.join(home, "code"),
            os.environ.get("UMH_ROOT", "/opt/OS"),
        ]
        for d in common_repo_dirs:
            if os.path.isdir(d):
                workspaces.append(d)

        # Check running processes for known platforms
        try:
            ps_out = subprocess.run(["ps", "aux"], capture_output=True, text=True, timeout=5)
            if ps_out.returncode == 0:
                process_names = {
                    "chrome",
                    "firefox",
                    "slack",
                    "discord",
                    "code",
                    "cursor",
                    "obsidian",
                }
                for name in process_names:
                    if name in ps_out.stdout.lower():
                        platforms.append(name)
        except Exception as exc:
            logger.debug("Process discovery failed: %s", exc)

        # Check for docker containers
        try:
            docker_out = subprocess.run(
                ["docker", "ps", "--format", "{{.Names}}"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if docker_out.returncode == 0 and docker_out.stdout.strip():
                containers = docker_out.stdout.strip().split("\n")
                workspaces.extend(f"container:{c}" for c in containers)
        except Exception as exc:
            logger.debug("Docker container discovery failed: %s", exc)

        result.domains_scanned = len(DISCOVERY_DOMAINS)
        result.platforms_found = len(set(platforms))
        result.workspaces_found = len(workspaces)
        result.maturity_level = "L1_BASIC_MAPPING" if platforms else "L0_NO_MAPPING"

        return result

    def _save_result(self, result: DiscoveryResult) -> None:
        """Save scan result to disk."""
        os.makedirs(DISCOVERY_DIR, exist_ok=True)
        timestamp = datetime.now(datetime.UTC).strftime("%Y-%m-%d_%H%M%S")
        path = os.path.join(DISCOVERY_DIR, f"scan_{timestamp}.json")
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(result.as_dict(), f, indent=2)
            result.proof_path = path
        except Exception as exc:
            logger.debug("Failed to save discovery result: %s", exc)
            result.errors.append(f"save failed: {exc}")

    def get_latest_result(self) -> DiscoveryResult | None:
        """Load the most recent scan result from disk."""
        if not os.path.isdir(DISCOVERY_DIR):
            return None
        files = sorted(
            (f for f in os.listdir(DISCOVERY_DIR) if f.startswith("scan_")),
            reverse=True,
        )
        if not files:
            return None
        try:
            path = os.path.join(DISCOVERY_DIR, files[0])
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            result = DiscoveryResult(**{k: v for k, v in data.items() if k != "errors"})
            result.errors = data.get("errors", [])
            return result
        except Exception as exc:
            logger.debug("Failed to load discovery result: %s", exc)
            return None

    def display_result(self, result: DiscoveryResult | None = None) -> None:
        """Print discovery scan results."""
        r = result or self._result
        if r is None:
            print("  No discovery scan results available.")
            return

        print()
        print("Environment Discovery")
        print("-" * 40)
        print(f"  Domains scanned:  {r.domains_scanned}")
        print(f"  Platforms found:  {r.platforms_found}")
        print(f"  Accounts found:   {r.accounts_found}")
        print(f"  Workspaces found: {r.workspaces_found}")
        print(f"  Maturity level:   {r.maturity_level}")
        print(f"  Duration:         {r.scan_duration_seconds:.1f}s")
        if r.errors:
            print(f"  Errors:           {len(r.errors)}")
        print()
