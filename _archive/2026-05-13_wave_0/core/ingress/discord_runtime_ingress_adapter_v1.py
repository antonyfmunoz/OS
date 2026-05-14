"""Discord Runtime Ingress Adapter v1.

Converts Discord events into RuntimeIngressSignal for
routing through the canonical spine.

The Discord adapter:
  - Converts Discord messages → RuntimeIngressSignal
  - Preserves Discord session lineage
  - Preserves Discord operator identity
  - CANNOT execute workflows directly
  - CANNOT bypass the ingress router

UMH substrate subsystem. Phase 96.8BU.
"""

from __future__ import annotations

from typing import Any

from core.ingress.live_runtime_ingress_contracts_v1 import (
    IngressSource,
    RuntimeIngressIdentity,
    RuntimeIngressSignal,
    _new_id,
    _now_iso,
)


class DiscordRuntimeIngressAdapter:
    """Converts Discord events to normalized ingress signals.

    Cannot execute directly — produces signals for the
    ingress router to dispatch through the spine.
    """

    def __init__(self) -> None:
        self._total_adapted: int = 0
        self._identities: dict[str, RuntimeIngressIdentity] = {}

    def adapt_message(
        self,
        content: str,
        author_id: str = "",
        author_name: str = "",
        channel_id: str = "",
        guild_id: str = "",
        message_id: str = "",
        roles: list[str] | None = None,
    ) -> RuntimeIngressSignal:
        """Convert a Discord message into an ingress signal."""
        identity = self._resolve_identity(
            author_id, author_name, roles or [],
        )

        signal = RuntimeIngressSignal(
            source=IngressSource.DISCORD,
            raw_input=content,
            operator_id=identity.operator_id,
            channel_id=channel_id,
            payload={
                "guild_id": guild_id,
                "message_id": message_id,
                "author_name": author_name,
                "discord_user_id": author_id,
            },
        )
        self._total_adapted += 1
        return signal

    def adapt_command(
        self,
        command_name: str,
        args: str = "",
        author_id: str = "",
        author_name: str = "",
        channel_id: str = "",
    ) -> RuntimeIngressSignal:
        """Convert a Discord slash/prefix command into an ingress signal."""
        raw = f"!{command_name}"
        if args:
            raw = f"{raw} {args}"

        return self.adapt_message(
            content=raw,
            author_id=author_id,
            author_name=author_name,
            channel_id=channel_id,
        )

    def _resolve_identity(
        self,
        discord_user_id: str,
        display_name: str,
        roles: list[str],
    ) -> RuntimeIngressIdentity:
        """Resolve or create an operator identity from Discord user."""
        if discord_user_id in self._identities:
            identity = self._identities[discord_user_id]
            identity.display_name = display_name
            identity.roles = roles
            return identity

        operator_id = f"op-discord-{discord_user_id}" if discord_user_id else _new_id("op")
        identity = RuntimeIngressIdentity(
            operator_id=operator_id,
            source=IngressSource.DISCORD,
            display_name=display_name,
            source_specific_id=discord_user_id,
            authenticated=bool(discord_user_id),
            roles=roles,
        )
        if discord_user_id:
            self._identities[discord_user_id] = identity
        return identity

    def get_identity(self, discord_user_id: str) -> RuntimeIngressIdentity | None:
        return self._identities.get(discord_user_id)

    def get_stats(self) -> dict[str, Any]:
        return {
            "total_adapted": self._total_adapted,
            "known_identities": len(self._identities),
        }
