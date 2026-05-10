"""Output dispatcher — routes responses to all surfaces attached to a session.

Instead of send_to_discord(channel), callers use:
    dispatch_output(session_id, text)

The dispatcher resolves all attached surfaces and delivers to each one.

Design rules:
- Best-effort delivery to each surface — one failure doesn't block others
- Returns structured results per surface
- No substrate imports on module load — lazy imports per surface type
"""

from __future__ import annotations

import logging
from typing import Any

from umh.runtime_loop.surface_registry import SurfaceRecord, get_surface_registry

logger = logging.getLogger(__name__)


async def dispatch_output(
    session_id: str,
    text: str,
    *,
    bot: Any = None,
    ai_name: str = "",
) -> list[dict[str, Any]]:
    """Deliver output to all surfaces attached to a session.

    Args:
        session_id: Session to deliver to.
        text: Raw response text (governance applied per surface type).
        bot: Discord bot instance (required for discord surfaces).
        ai_name: AI display name for footers.

    Returns:
        List of delivery results, one per surface.
    """
    registry = get_surface_registry()
    surfaces = registry.get_surfaces(session_id)

    if not surfaces:
        logger.info("[Dispatcher] No surfaces for session %s", session_id)
        return []

    results = []
    for surface in surfaces:
        try:
            result = await _deliver_to_surface(surface, text, bot=bot, ai_name=ai_name)
            results.append(result)
            registry.update_activity(surface.surface_id)
        except Exception as exc:
            logger.warning(
                "[Dispatcher] Failed delivering to %s (%s): %s",
                surface.surface_id,
                surface.surface_type,
                exc,
            )
            results.append(
                {
                    "surface_id": surface.surface_id,
                    "surface_type": surface.surface_type,
                    "ok": False,
                    "error": str(exc),
                }
            )

    return results


async def _deliver_to_surface(
    surface: SurfaceRecord,
    text: str,
    *,
    bot: Any = None,
    ai_name: str = "",
) -> dict[str, Any]:
    """Deliver to a single surface based on its type."""
    if surface.surface_type == "discord":
        return await _deliver_discord(surface, text, bot=bot, ai_name=ai_name)
    elif surface.surface_type == "voice":
        return _deliver_voice(surface, text)
    elif surface.surface_type == "workstation":
        return {
            "surface_id": surface.surface_id,
            "surface_type": "workstation",
            "ok": False,
            "error": "not_implemented",
        }

    return {
        "surface_id": surface.surface_id,
        "surface_type": surface.surface_type,
        "ok": False,
        "error": "unknown_surface_type",
    }


async def _deliver_discord(
    surface: SurfaceRecord,
    text: str,
    *,
    bot: Any = None,
    ai_name: str = "",
) -> dict[str, Any]:
    """Deliver to a Discord channel surface."""
    channel_id = surface.config.get("channel_id")
    if not channel_id or not bot:
        return {
            "surface_id": surface.surface_id,
            "surface_type": "discord",
            "ok": False,
            "error": "no_channel_or_bot",
        }

    channel = bot.get_channel(int(channel_id))
    if not channel:
        return {
            "surface_id": surface.surface_id,
            "surface_type": "discord",
            "ok": False,
            "error": "channel_not_found",
        }

    try:
        from umh.substrate.discord_output_policy import (
            clean_for_discord,
            extract_final_answer,
            get_display_name,
        )

        cleaned = clean_for_discord(text)
        final = extract_final_answer(cleaned)
        if not final:
            return {
                "surface_id": surface.surface_id,
                "surface_type": "discord",
                "ok": True,
                "suppressed": True,
            }
        display = get_display_name(surface.config.get("session_name", ""))
        footer = f"\n\n— {ai_name}  ·  {display}"
        output = final.rstrip() + footer
    except ImportError:
        output = text

    try:
        from umh.substrate.session_discord_bridge import send_reply

        ok = await send_reply(channel, output)
        return {
            "surface_id": surface.surface_id,
            "surface_type": "discord",
            "ok": ok,
            "chars": len(output),
        }
    except Exception as exc:
        return {
            "surface_id": surface.surface_id,
            "surface_type": "discord",
            "ok": False,
            "error": str(exc),
        }


def _deliver_voice(
    surface: SurfaceRecord,
    text: str,
) -> dict[str, Any]:
    """Deliver to a voice surface via TTS."""
    try:
        from umh.substrate.station_helpers import propose_speak_text

        result = propose_speak_text(text)
        ok = result.get("accepted", False) if isinstance(result, dict) else bool(result)
        return {"surface_id": surface.surface_id, "surface_type": "voice", "ok": ok}
    except Exception as exc:
        return {
            "surface_id": surface.surface_id,
            "surface_type": "voice",
            "ok": False,
            "error": str(exc),
        }
