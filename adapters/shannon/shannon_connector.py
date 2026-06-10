"""
ShannonConnector — AI penetration testing via KeygraphHQ/Shannon.

Wraps the Shannon CLI to give UMH agents autonomous security scanning
of web applications and APIs. Shannon analyzes source code, identifies
attack vectors, and executes real exploits in ephemeral Docker containers
to produce proof-by-exploitation reports.

Shannon runs as the 'ubuntu' user (refuses root) and requires Docker.

Usage:
    from adapters.shannon.shannon_connector import ShannonConnector
    sc = ShannonConnector()

    result = sc.start_scan(
        url="https://your-app.com",
        repo_path="/path/to/repo",
    )
    # result = {workspace, status, ...}

    status = sc.get_status()
    # status = {temporal, workers, ...}

    workspaces = sc.list_workspaces()
    report = sc.get_logs(workspace="my-scan")
"""

from __future__ import annotations

import logging
import os
import subprocess
import time
from pathlib import Path
from subprocess import CompletedProcess

from substrate.execution.cpu_gate import gated_subprocess_run

logger = logging.getLogger(__name__)

_SHANNON_USER = os.getenv("SHANNON_USER", "ubuntu")
_SHANNON_TIMEOUT = int(os.getenv("SHANNON_TIMEOUT", "7200"))
_SCAN_COOLDOWN_FILE = "/tmp/shannon_cooldown"
_SCAN_COOLDOWN_SECONDS = int(os.getenv("SHANNON_COOLDOWN", "60"))


def _in_cooldown() -> float:
    """Return seconds remaining in cooldown, or 0 if clear."""
    try:
        ts = float(Path(_SCAN_COOLDOWN_FILE).read_text().strip())
    except Exception:
        return 0.0
    remaining = (ts + _SCAN_COOLDOWN_SECONDS) - time.time()
    return max(0.0, remaining)


def _trip_cooldown() -> None:
    try:
        Path(_SCAN_COOLDOWN_FILE).write_text(str(time.time()))
    except Exception:
        pass


class ShannonConnector:
    """
    Wraps the Shannon CLI for AI-powered penetration testing.

    All methods are safe — they log warnings on error and return
    structured dicts, never raise.
    """

    def _run(
        self,
        *args: str,
        timeout: int | None = None,
    ) -> CompletedProcess | None:
        """
        Run a shannon CLI command as the configured non-root user.

        Returns CompletedProcess on success, None on error/cooldown.
        Uses gated_subprocess_run for CPU safety.
        """
        remaining = _in_cooldown()
        if remaining > 0:
            logger.info(
                "Shannon skipping %s: cooldown %ds remaining",
                " ".join(args),
                int(remaining),
            )
            return None

        cmd = ["su", "-", _SHANNON_USER, "-c", f"shannon {' '.join(args)}"]
        effective_timeout = timeout or _SHANNON_TIMEOUT

        try:
            result = gated_subprocess_run(
                cmd,
                capture_output=True,
                text=True,
                timeout=effective_timeout,
                caller="shannon_connector",
            )
        except subprocess.TimeoutExpired:
            logger.warning("Shannon %s timed out after %ds", args[0], effective_timeout)
            _trip_cooldown()
            return None

        if result is None:
            logger.warning("Shannon gated out by CPU load")
            return None

        if result.returncode != 0:
            stderr = (result.stderr or "").strip()
            logger.warning(
                "Shannon %s failed (rc=%d): %s", args[0], result.returncode, stderr[:500]
            )
            if "timeout" in stderr.lower() or "timed out" in stderr.lower():
                _trip_cooldown()

        return result

    def status(self) -> dict:
        """Get Shannon runtime status (Temporal + workers)."""
        result = self._run("status", timeout=30)
        if result is None or result.returncode != 0:
            return {"status": "error", "detail": "could not reach shannon"}

        return {"status": "ok", "output": result.stdout.strip()}

    def list_workspaces(self) -> dict:
        """List all Shannon scan workspaces."""
        result = self._run("workspaces", timeout=30)
        if result is None or result.returncode != 0:
            return {"status": "error", "workspaces": []}

        return {"status": "ok", "output": result.stdout.strip()}

    def start_scan(
        self,
        url: str,
        repo_path: str,
        workspace: str | None = None,
        config_path: str | None = None,
        output_dir: str | None = None,
        debug: bool = False,
    ) -> dict:
        """
        Start a Shannon penetration test scan.

        Args:
            url:         Target URL to scan.
            repo_path:   Path to the application source code.
            workspace:   Named workspace (auto-resumes if exists).
            config_path: Optional YAML config file path.
            output_dir:  Directory to copy deliverables after run.
            debug:       Preserve worker container after exit.

        Returns:
            {status, workspace, output} dict.
        """
        args = ["start", "-u", url, "-r", repo_path]
        if workspace:
            args += ["-w", workspace]
        if config_path:
            args += ["-c", config_path]
        if output_dir:
            args += ["-o", output_dir]
        if debug:
            args.append("--debug")

        result = self._run(*args)
        if result is None:
            return {"status": "error", "detail": "scan blocked by gate or cooldown"}

        return {
            "status": "ok" if result.returncode == 0 else "error",
            "workspace": workspace or "default",
            "output": result.stdout.strip() if result.stdout else "",
            "stderr": result.stderr.strip() if result.stderr else "",
        }

    def get_logs(self, workspace: str) -> dict:
        """Tail the workflow log for a workspace."""
        result = self._run("logs", workspace, timeout=30)
        if result is None or result.returncode != 0:
            return {"status": "error", "logs": ""}

        return {"status": "ok", "logs": result.stdout.strip()}

    def stop(self, clean: bool = False) -> dict:
        """Stop all Shannon containers."""
        args = ["stop"]
        if clean:
            args.append("--clean")

        result = self._run(*args, timeout=60)
        if result is None:
            return {"status": "error", "detail": "stop blocked"}

        return {
            "status": "ok" if result.returncode == 0 else "error",
            "output": result.stdout.strip() if result.stdout else "",
        }

    def health_check(self) -> bool:
        """Quick check: can we reach the shannon CLI?"""
        result = self._run("status", timeout=15)
        return result is not None and result.returncode == 0
