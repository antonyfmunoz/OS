"""UI-TARS harness — Tier 1 wrapper for desktop_control capability.

Wraps ByteDance's UI-TARS-desktop (Apache-2.0) behind UMH's
DesktopControlCapability contract.

UI-TARS runs on a LOCAL Windows/macOS machine (not the VPS).  The harness
communicates via HTTP to a local bridge server endpoint exposed over
Tailscale.  Bridge integration is a future task — for now invoke returns a
clear "not configured" error.
"""

from __future__ import annotations

import asyncio
import logging
import os
import time
from typing import Any

from .contracts import CapabilityResult, DesktopControlCapability, DesktopControlRequest

logger = logging.getLogger(__name__)

# TODO: Bridge integration — UI-TARS runs on local Windows machine,
# reached via Tailscale at a bridge endpoint.  Once the bridge server
# is deployed, set UI_TARS_BRIDGE_URL to its address.


class UITarsHarness(DesktopControlCapability):
    """Wraps UI-TARS-desktop behind UMH's desktop_control contract."""

    def __init__(self) -> None:
        self._bridge_url: str = os.getenv("UI_TARS_BRIDGE_URL", "")
        self._timeout: int = int(os.getenv("UI_TARS_TIMEOUT_SECONDS", "60"))

    async def health_check(self) -> bool:
        """Check if UI-TARS bridge endpoint is reachable."""
        if not self._bridge_url:
            logger.info(
                "UI-TARS bridge URL not configured (set UI_TARS_BRIDGE_URL). "
                "Desktop control not available."
            )
            return False

        try:
            # Lazy import — aiohttp may not be installed in every environment
            import aiohttp

            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
                async with session.get(f"{self._bridge_url}/health") as resp:
                    healthy = resp.status == 200
                    if healthy:
                        logger.info("UI-TARS bridge reachable at %s", self._bridge_url)
                    else:
                        logger.warning(
                            "UI-TARS bridge returned %d at %s",
                            resp.status,
                            self._bridge_url,
                        )
                    return healthy
        except ImportError:
            logger.info("aiohttp not installed — cannot reach UI-TARS bridge")
            return False
        except Exception as e:
            logger.warning("UI-TARS health_check failed: %s", e)
            return False

    async def invoke(self, request: DesktopControlRequest, **kwargs: Any) -> CapabilityResult:
        """Send a desktop control action to the UI-TARS bridge.

        Args:
            request: Action to perform (click, type, open_app, etc.).

        Returns:
            CapabilityResult with action outcome or error.
        """
        start = time.time()

        if not self._bridge_url:
            return CapabilityResult(
                success=False,
                error=(
                    "UI-TARS bridge URL not configured. "
                    "Set UI_TARS_BRIDGE_URL to the local bridge endpoint."
                ),
                duration_ms=(time.time() - start) * 1000,
            )

        try:
            import aiohttp

            payload = {
                "action": request.action,
                "target": request.target,
                "parameters": request.parameters,
            }

            async with aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self._timeout)
            ) as session:
                async with session.post(
                    f"{self._bridge_url}/execute",
                    json=payload,
                ) as resp:
                    duration = (time.time() - start) * 1000
                    body = await resp.json()

                    if resp.status == 200:
                        return CapabilityResult(
                            success=True,
                            output=body.get("result"),
                            summary=f"UI-TARS executed {request.action} on {request.target}",
                            duration_ms=duration,
                            metadata=body,
                        )
                    else:
                        return CapabilityResult(
                            success=False,
                            error=body.get("error", f"HTTP {resp.status}"),
                            duration_ms=duration,
                            metadata=body,
                        )

        except ImportError:
            return CapabilityResult(
                success=False,
                error="aiohttp not installed — cannot reach UI-TARS bridge",
                duration_ms=(time.time() - start) * 1000,
            )
        except asyncio.TimeoutError:
            return CapabilityResult(
                success=False,
                error=f"UI-TARS bridge timed out after {self._timeout}s",
                duration_ms=(time.time() - start) * 1000,
            )
        except Exception as e:
            logger.error("UI-TARS invocation failed: %s", e)
            return CapabilityResult(
                success=False,
                error=str(e),
                duration_ms=(time.time() - start) * 1000,
            )
