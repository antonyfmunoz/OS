"""Goose harness — Tier 1 subprocess wrapper for software_creation capability.

Wraps Block's Goose CLI (Apache-2.0) behind UMH's SoftwareCreationCapability
contract.  When Goose is not installed, health_check returns False and invoke
returns a clear error — no silent failures.
"""

from __future__ import annotations

import asyncio
import logging
import os
import shutil
import subprocess
import time
from typing import Any

from .contracts import CapabilityResult, SoftwareCreationCapability, SoftwareCreationRequest

logger = logging.getLogger(__name__)


class GooseHarness(SoftwareCreationCapability):
    """Wraps Goose CLI behind UMH's software_creation contract."""

    def __init__(self) -> None:
        self._goose_bin: str = shutil.which("goose") or os.getenv("GOOSE_BIN", "goose")
        self._timeout: int = int(os.getenv("GOOSE_TIMEOUT_SECONDS", "300"))

    async def health_check(self) -> bool:
        """Check if the Goose CLI is available and responds to --version."""
        try:
            result = await asyncio.to_thread(
                subprocess.run,
                [self._goose_bin, "--version"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            healthy = result.returncode == 0
            if healthy:
                logger.info("Goose available: %s", result.stdout.strip())
            else:
                logger.warning("Goose returned non-zero: %s", result.stderr.strip())
            return healthy
        except FileNotFoundError:
            logger.info("Goose binary not found at %s — not installed", self._goose_bin)
            return False
        except subprocess.TimeoutExpired:
            logger.warning("Goose --version timed out")
            return False
        except Exception as e:
            logger.error("Goose health_check failed: %s", e)
            return False

    async def invoke(self, request: SoftwareCreationRequest, **kwargs: Any) -> CapabilityResult:
        """Invoke Goose to generate or modify code.

        Args:
            request: What to build and where.

        Returns:
            CapabilityResult with stdout on success, error details on failure.
        """
        start = time.time()

        # Pre-flight: binary exists?
        if not shutil.which(self._goose_bin) and self._goose_bin == "goose":
            return CapabilityResult(
                success=False,
                error=f"Goose binary not found at {self._goose_bin}. Install Goose first.",
                duration_ms=(time.time() - start) * 1000,
            )

        try:
            # Build command — Goose CLI: goose run "<task>"
            cmd: list[str] = [self._goose_bin, "run", request.task]

            env = os.environ.copy()
            if request.repo_path:
                env["GOOSE_WORKING_DIR"] = str(request.repo_path)

            result = await asyncio.to_thread(
                subprocess.run,
                cmd,
                capture_output=True,
                text=True,
                timeout=self._timeout,
                cwd=str(request.repo_path) if request.repo_path else None,
                env=env,
            )

            duration = (time.time() - start) * 1000

            if result.returncode == 0:
                return CapabilityResult(
                    success=True,
                    output=result.stdout,
                    summary=f"Goose completed task: {request.task[:100]}",
                    duration_ms=duration,
                    metadata={
                        "returncode": 0,
                        "stderr": result.stderr[:500] if result.stderr else "",
                    },
                )
            else:
                return CapabilityResult(
                    success=False,
                    error=result.stderr[:1000]
                    if result.stderr
                    else f"Exit code {result.returncode}",
                    duration_ms=duration,
                    metadata={"returncode": result.returncode},
                )

        except subprocess.TimeoutExpired:
            return CapabilityResult(
                success=False,
                error=f"Goose timed out after {self._timeout}s",
                duration_ms=(time.time() - start) * 1000,
            )
        except FileNotFoundError:
            return CapabilityResult(
                success=False,
                error=f"Goose binary not found at {self._goose_bin}",
                duration_ms=(time.time() - start) * 1000,
            )
        except Exception as e:
            logger.error("Goose invocation failed: %s", e)
            return CapabilityResult(
                success=False,
                error=str(e),
                duration_ms=(time.time() - start) * 1000,
            )
