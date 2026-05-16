"""Voice-Pro harness — Tier 1 wrapper for voice_interaction capability.

Wraps Voice-Pro behind UMH's VoiceInteractionCapability contract.
Supports transcription (audio -> text) and synthesis (text -> audio)
via Voice-Pro's HTTP API or CLI.

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

from .contracts import CapabilityResult, VoiceInteractionCapability, VoiceInteractionRequest

logger = logging.getLogger(__name__)


class VoiceProHarness(VoiceInteractionCapability):
    """Wraps Voice-Pro behind UMH's voice_interaction contract."""

    def __init__(self) -> None:
        self._api_url: str = os.getenv("VOICE_PRO_API_URL", "")
        self._cli_bin: str = shutil.which("voice-pro") or os.getenv("VOICE_PRO_BIN", "voice-pro")
        self._timeout: int = int(os.getenv("VOICE_PRO_TIMEOUT_SECONDS", "120"))

    async def health_check(self) -> bool:
        """Check if Voice-Pro service or CLI is available."""
        # Try HTTP API first
        if self._api_url:
            try:
                import aiohttp

                async with aiohttp.ClientSession(
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as session:
                    async with session.get(f"{self._api_url}/health") as resp:
                        if resp.status == 200:
                            logger.info("Voice-Pro API reachable at %s", self._api_url)
                            return True
                        logger.warning("Voice-Pro API returned %d", resp.status)
            except ImportError:
                logger.info("aiohttp not installed — cannot reach Voice-Pro API")
            except Exception as e:
                logger.warning("Voice-Pro API health_check failed: %s", e)

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
                logger.info("Voice-Pro CLI available: %s", result.stdout.strip())
                return True
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass
        except Exception as e:
            logger.warning("Voice-Pro CLI health_check failed: %s", e)

        logger.info("Voice-Pro not installed — voice_interaction not available")
        return False

    async def invoke(self, request: VoiceInteractionRequest, **kwargs: Any) -> CapabilityResult:
        """Invoke Voice-Pro for transcription, synthesis, or conversation.

        Args:
            request: Audio/text input and desired mode.

        Returns:
            CapabilityResult with text (transcribe) or audio path (synthesize).
        """
        start = time.time()

        if request.mode == "transcribe":
            return await self._transcribe(request, start)
        elif request.mode == "synthesize":
            return await self._synthesize(request, start)
        elif request.mode == "converse":
            return CapabilityResult(
                success=False,
                error="Converse mode not yet implemented for Voice-Pro harness",
                duration_ms=(time.time() - start) * 1000,
            )
        else:
            return CapabilityResult(
                success=False,
                error=f"Unknown mode: {request.mode}. Use 'transcribe', 'synthesize', or 'converse'.",
                duration_ms=(time.time() - start) * 1000,
            )

    async def _transcribe(self, request: VoiceInteractionRequest, start: float) -> CapabilityResult:
        """Transcribe audio to text."""
        if not request.audio_input:
            return CapabilityResult(
                success=False,
                error="audio_input path required for transcription",
                duration_ms=(time.time() - start) * 1000,
            )

        if not Path(request.audio_input).exists():
            return CapabilityResult(
                success=False,
                error=f"Audio file not found: {request.audio_input}",
                duration_ms=(time.time() - start) * 1000,
            )

        # Try HTTP API
        if self._api_url:
            try:
                import aiohttp

                async with aiohttp.ClientSession(
                    timeout=aiohttp.ClientTimeout(total=self._timeout)
                ) as session:
                    data = aiohttp.FormData()
                    data.add_field(
                        "audio",
                        open(request.audio_input, "rb"),
                        filename=Path(request.audio_input).name,
                    )
                    async with session.post(f"{self._api_url}/transcribe", data=data) as resp:
                        duration = (time.time() - start) * 1000
                        body = await resp.json()
                        if resp.status == 200:
                            return CapabilityResult(
                                success=True,
                                output=body.get("text", ""),
                                summary="Transcription complete",
                                duration_ms=duration,
                                metadata=body,
                            )
                        return CapabilityResult(
                            success=False,
                            error=body.get("error", f"HTTP {resp.status}"),
                            duration_ms=duration,
                        )
            except ImportError:
                pass  # Fall through to CLI
            except Exception as e:
                logger.warning("Voice-Pro API transcribe failed: %s", e)

        # Fall back to CLI
        try:
            result = await asyncio.to_thread(
                subprocess.run,
                [self._cli_bin, "transcribe", str(request.audio_input)],
                capture_output=True,
                text=True,
                timeout=self._timeout,
            )
            duration = (time.time() - start) * 1000
            if result.returncode == 0:
                return CapabilityResult(
                    success=True,
                    output=result.stdout.strip(),
                    summary="Transcription complete via CLI",
                    duration_ms=duration,
                )
            return CapabilityResult(
                success=False,
                error=result.stderr[:1000] if result.stderr else f"Exit code {result.returncode}",
                duration_ms=duration,
            )
        except FileNotFoundError:
            return CapabilityResult(
                success=False,
                error=f"Voice-Pro not found at {self._cli_bin}. Install Voice-Pro first.",
                duration_ms=(time.time() - start) * 1000,
            )
        except Exception as e:
            logger.error("Voice-Pro transcribe failed: %s", e)
            return CapabilityResult(
                success=False,
                error=str(e),
                duration_ms=(time.time() - start) * 1000,
            )

    async def _synthesize(self, request: VoiceInteractionRequest, start: float) -> CapabilityResult:
        """Synthesize text to audio."""
        if not request.text_input:
            return CapabilityResult(
                success=False,
                error="text_input required for synthesis",
                duration_ms=(time.time() - start) * 1000,
            )

        # Try HTTP API
        if self._api_url:
            try:
                import aiohttp

                async with aiohttp.ClientSession(
                    timeout=aiohttp.ClientTimeout(total=self._timeout)
                ) as session:
                    async with session.post(
                        f"{self._api_url}/synthesize",
                        json={"text": request.text_input},
                    ) as resp:
                        duration = (time.time() - start) * 1000
                        if resp.status == 200:
                            body = await resp.json()
                            return CapabilityResult(
                                success=True,
                                output=body.get("audio_path", ""),
                                summary="Synthesis complete",
                                duration_ms=duration,
                                metadata=body,
                            )
                        body = await resp.json()
                        return CapabilityResult(
                            success=False,
                            error=body.get("error", f"HTTP {resp.status}"),
                            duration_ms=duration,
                        )
            except ImportError:
                pass  # Fall through to CLI
            except Exception as e:
                logger.warning("Voice-Pro API synthesize failed: %s", e)

        # Fall back to CLI
        try:
            result = await asyncio.to_thread(
                subprocess.run,
                [self._cli_bin, "synthesize", "--text", request.text_input],
                capture_output=True,
                text=True,
                timeout=self._timeout,
            )
            duration = (time.time() - start) * 1000
            if result.returncode == 0:
                return CapabilityResult(
                    success=True,
                    output=result.stdout.strip(),
                    summary="Synthesis complete via CLI",
                    duration_ms=duration,
                )
            return CapabilityResult(
                success=False,
                error=result.stderr[:1000] if result.stderr else f"Exit code {result.returncode}",
                duration_ms=duration,
            )
        except FileNotFoundError:
            return CapabilityResult(
                success=False,
                error=f"Voice-Pro not found at {self._cli_bin}. Install Voice-Pro first.",
                duration_ms=(time.time() - start) * 1000,
            )
        except Exception as e:
            logger.error("Voice-Pro synthesize failed: %s", e)
            return CapabilityResult(
                success=False,
                error=str(e),
                duration_ms=(time.time() - start) * 1000,
            )
