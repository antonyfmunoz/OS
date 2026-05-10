#!/usr/bin/env python3
"""
Discord Builder/Product Channels Setup v1.

Idempotent operator automation:
  1. Log in as the EOS Discord bot.
  2. Locate the target guild (env override → single-guild auto-detect).
  3. Ensure two text channels exist:
        - eos-builder
        - eos-product
     Reuse existing channels with the same name (no duplicates).
  4. Print their IDs so the caller can wire them into eos_ai/.env.

Does NOT edit env, ensure Claude sessions, or restart containers — those
are separate steps in the setup pipeline so they remain composable.

Env
---
  DISCORD_BOT_TOKEN        required (looked up from services/.env or env)
  DISCORD_GUILD_ID         optional; if set, use exactly this guild.
                           If unset, the bot must be in exactly one guild.

Output
------
  Emits one JSON line to stdout:
    {"builder_channel_id": "...", "product_channel_id": "...",
     "guild_id": "...", "builder_created": bool, "product_created": bool}

Exit codes
----------
  0  success
  1  misconfiguration (missing token, wrong number of guilds)
  2  Discord API error
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS")

try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv(*_a, **_k):  # type: ignore[no-redef]
        return False


BUILDER_CHANNEL_NAME = "eos-builder"
PRODUCT_CHANNEL_NAME = "eos-product"

BUILDER_TOPIC = (
    "EOS builder mode — internal/dev lane. Messages routed to "
    "dex_builder_main tmux session via substrate+shared router."
)
PRODUCT_TOPIC = (
    "EOS product mode — user-facing/SaaS runtime lane. Messages routed "
    "to dex_product_main tmux session via substrate+shared router."
)


def _log(msg: str) -> None:
    print(f"[discord_setup] {msg}", file=sys.stderr, flush=True)


def _load_token() -> str:
    # Pull env from both common locations
    for envfile in ("/opt/OS/services/.env", "/opt/OS/eos_ai/.env"):
        if Path(envfile).exists():
            load_dotenv(envfile, override=False)
    token = (
        os.getenv("DISCORD_BOT_TOKEN")
        or os.getenv("DISCORD_TOKEN")
        or ""
    ).strip()
    if not token:
        _log("DISCORD_BOT_TOKEN not found in env")
        sys.exit(1)
    return token


async def _run() -> dict:
    import discord

    token = _load_token()
    guild_id_env = (os.getenv("DISCORD_GUILD_ID") or "").strip()

    intents = discord.Intents.default()
    intents.guilds = True
    # We don't need message_content for setup.
    client = discord.Client(intents=intents)

    result: dict = {}
    error: dict = {}

    @client.event
    async def on_ready():  # noqa: D401
        try:
            _log(f"logged in as {client.user} (id={client.user.id})")
            guilds = list(client.guilds)
            _log(f"visible guilds: {[(g.name, g.id) for g in guilds]}")

            guild = None
            if guild_id_env:
                for g in guilds:
                    if str(g.id) == guild_id_env:
                        guild = g
                        break
                if guild is None:
                    error["reason"] = (
                        f"DISCORD_GUILD_ID={guild_id_env} not in visible guilds"
                    )
                    await client.close()
                    return
            else:
                if len(guilds) == 0:
                    error["reason"] = "bot is in zero guilds"
                    await client.close()
                    return
                if len(guilds) > 1:
                    error["reason"] = (
                        f"bot is in {len(guilds)} guilds — set DISCORD_GUILD_ID "
                        f"to disambiguate: "
                        f"{[(g.name, g.id) for g in guilds]}"
                    )
                    await client.close()
                    return
                guild = guilds[0]

            _log(f"using guild: {guild.name} ({guild.id})")
            result["guild_id"] = str(guild.id)
            result["guild_name"] = guild.name

            async def _ensure_channel(name: str, topic: str) -> tuple[str, bool]:
                existing = discord.utils.get(guild.text_channels, name=name)
                if existing is not None:
                    _log(f"reusing existing channel #{name} id={existing.id}")
                    # Optionally refresh the topic so it stays informative.
                    try:
                        if (existing.topic or "") != topic:
                            await existing.edit(
                                topic=topic, reason="EOS setup: refresh topic"
                            )
                    except Exception as e:  # noqa: BLE001
                        _log(f"topic refresh skipped for #{name}: {e}")
                    return str(existing.id), False

                _log(f"creating channel #{name}")
                created = await guild.create_text_channel(
                    name=name,
                    topic=topic,
                    reason="EOS Discord Builder/Product mode routing v1 setup",
                )
                _log(f"created channel #{name} id={created.id}")
                return str(created.id), True

            b_id, b_created = await _ensure_channel(
                BUILDER_CHANNEL_NAME, BUILDER_TOPIC
            )
            p_id, p_created = await _ensure_channel(
                PRODUCT_CHANNEL_NAME, PRODUCT_TOPIC
            )
            result["builder_channel_id"] = b_id
            result["builder_created"] = b_created
            result["product_channel_id"] = p_id
            result["product_created"] = p_created
        except Exception as e:  # noqa: BLE001
            error["reason"] = f"{type(e).__name__}: {e}"
        finally:
            await client.close()

    try:
        await client.start(token)
    except Exception as e:  # noqa: BLE001
        error["reason"] = error.get("reason") or f"login_failed: {e}"

    if error:
        _log(f"ERROR: {error['reason']}")
        sys.exit(2)
    return result


def main() -> int:
    res = asyncio.run(_run())
    print(json.dumps(res))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
