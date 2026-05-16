"""Creative generation harness — Tier 1 wrapper for creative_generation capability.

Wraps Open Generative AI behind UMH's CreativeGenerationCapability contract.
Supports image, video, audio, and 3D asset generation via subprocess or HTTP API.

License status: TBD — pending curation review.
"""

from __future__ import annotations

import asyncio
import logging
import os
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any

from .contracts import (
    CapabilityResult,
    CreativeGenerationCapability,
    CreativeGenerationRequest,
)

logger = logging.getLogger(__name__)


class CreativeGenHarness(CreativeGenerationCapability):
    """Wraps Open Generative AI behind UMH's creative_generation contract."""

    def __init__(self) -> None:
        self._api_url: str = os.getenv("CREATIVE_GEN_API_URL", "")
        self._cli_bin: str = shutil.which("open-generative-ai") or os.getenv(
            "CREATIVE_GEN_BIN", "open-generative-ai"
        )
        self._timeout: int = int(os.getenv("CREATIVE_GEN_TIMEOUT_SECONDS", "300"))

    async def health_check(self) -> bool:
        """Check if the creative generation tool is available."""
        # Try HTTP API first
        if self._api_url:
            try:
                import aiohttp

                async with aiohttp.ClientSession(
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as session:
                    async with session.get(f"{self._api_url}/health") as resp:
                        if resp.status == 200:
                            logger.info("Creative gen API reachable at %s", self._api_url)
                            return True
                        logger.warning("Creative gen API returned %d", resp.status)
            except ImportError:
                logger.info("aiohttp not installed — cannot reach creative gen API")
            except Exception as e:
                logger.warning("Creative gen API health_check failed: %s", e)

        # Fall back to CLI
        try:
            result = await asyncio.to_thread(
                subprocess.run,
                [self._cli_bin, "--version"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                logger.info("Creative gen CLI available: %s", result.stdout.strip())
                return True
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass
        except Exception as e:
            logger.warning("Creative gen CLI health_check failed: %s", e)

        logger.info("Open Generative AI not installed — creative_generation not available")
        return False

    async def invoke(self, request: CreativeGenerationRequest, **kwargs: Any) -> CapabilityResult:
        """Generate a creative asset from the given prompt.

        Args:
            request: Prompt, output type, and generation parameters.

        Returns:
            CapabilityResult with generated file path or error.
        """
        start = time.time()

        valid_types = {"image", "video", "audio", "3d"}
        if request.output_type not in valid_types:
            return CapabilityResult(
                success=False,
                error=f"Unknown output_type: {request.output_type}. Use one of {valid_types}.",
                duration_ms=(time.time() - start) * 1000,
            )

        # Ensure output directory exists
        output_dir = request.output_dir or Path("/tmp/umh_creative_output")
        output_dir.mkdir(parents=True, exist_ok=True)

        # Try HTTP API
        if self._api_url:
            result = await self._invoke_api(request, output_dir, start)
            if result is not None:
                return result

        # Fall back to CLI
        return await self._invoke_cli(request, output_dir, start)

    async def _invoke_api(
        self,
        request: CreativeGenerationRequest,
        output_dir: Path,
        start: float,
    ) -> CapabilityResult | None:
        """Try invoking via HTTP API. Returns None if API unavailable."""
        try:
            import aiohttp

            payload = {
                "prompt": request.prompt,
                "output_type": request.output_type,
                "parameters": request.parameters,
                "output_dir": str(output_dir),
            }

            async with aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self._timeout)
            ) as session:
                async with session.post(
                    f"{self._api_url}/generate",
                    json=payload,
                ) as resp:
                    duration = (time.time() - start) * 1000
                    body = await resp.json()

                    if resp.status == 200:
                        files = body.get("files", [])
                        return CapabilityResult(
                            success=True,
                            output=body.get("result"),
                            files_changed=files,
                            summary=f"Generated {request.output_type}: {request.prompt[:80]}",
                            duration_ms=duration,
                            metadata=body,
                        )
                    return CapabilityResult(
                        success=False,
                        error=body.get("error", f"HTTP {resp.status}"),
                        duration_ms=duration,
                        metadata=body,
                    )
        except ImportError:
            return None  # aiohttp not available, fall through to CLI
        except Exception as e:
            logger.warning("Creative gen API invoke failed: %s", e)
            return None  # Fall through to CLI

    async def _invoke_cli(
        self,
        request: CreativeGenerationRequest,
        output_dir: Path,
        start: float,
    ) -> CapabilityResult:
        """Invoke via CLI subprocess."""
        try:
            cmd: list[str] = [
                self._cli_bin,
                "generate",
                "--type",
                request.output_type,
                "--prompt",
                request.prompt,
                "--output-dir",
                str(output_dir),
            ]

            # Pass additional parameters as --key value pairs
            for key, value in request.parameters.items():
                cmd.extend([f"--{key}", str(value)])

            result = await asyncio.to_thread(
                subprocess.run,
                cmd,
                capture_output=True,
                text=True,
                timeout=self._timeout,
            )

            duration = (time.time() - start) * 1000

            if result.returncode == 0:
                return CapabilityResult(
                    success=True,
                    output=result.stdout.strip(),
                    summary=f"Generated {request.output_type}: {request.prompt[:80]}",
                    duration_ms=duration,
                    metadata={"returncode": 0},
                )
            return CapabilityResult(
                success=False,
                error=result.stderr[:1000] if result.stderr else f"Exit code {result.returncode}",
                duration_ms=duration,
                metadata={"returncode": result.returncode},
            )

        except FileNotFoundError:
            return CapabilityResult(
                success=False,
                error=(
                    f"Creative gen tool not found at {self._cli_bin}. "
                    "Install Open Generative AI first."
                ),
                duration_ms=(time.time() - start) * 1000,
            )
        except subprocess.TimeoutExpired:
            return CapabilityResult(
                success=False,
                error=f"Creative gen timed out after {self._timeout}s",
                duration_ms=(time.time() - start) * 1000,
            )
        except Exception as e:
            logger.error("Creative gen CLI invoke failed: %s", e)
            return CapabilityResult(
                success=False,
                error=str(e),
                duration_ms=(time.time() - start) * 1000,
            )
