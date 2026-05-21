"""Discord interface — transport layer only.

The Discord bot (services/discord_bot.py) is the runtime transport.
It normalizes user messages into signals and delegates to
EOSGateway.handle() which routes through the execution spine.

UMH contract: interfaces NEVER contain intelligence. They:
1. Receive raw input from the transport (Discord message, slash command)
2. Normalize to a UMH signal (text, metadata, channel context)
3. Call umh.run() or EOSGateway.handle()
4. Format the response for the transport and send it back

The actual service lives at services/discord_bot.py.
This package exists to hold any UMH-native Discord adapters
that may replace the legacy service.
"""
