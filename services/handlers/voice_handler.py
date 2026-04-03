"""
Voice handler — skeleton module.
Voice logic remains in discord_bot.py for now due to
tight coupling with bot instance, voice client state,
and asyncio task management.

This module exists as a future extraction target.
When voice is refactored, move here:
- SilenceDetectingSink
- transcribe_with_groq
- _listen_loop
- handle_meeting_voice
- start_meeting_mode
- end_active_meeting
- on_voice_state_update

Current blockers for extraction:
- SilenceDetectingSink needs discord.sinks.Sink
- _listen_loop creates asyncio tasks tied to bot event loop
- Meeting state (_active_meeting) is shared mutable dict
- Voice client management needs guild.voice_client access
"""
