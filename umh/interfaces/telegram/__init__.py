"""Telegram interface — transport layer only.

The Telegram bot (services/telegram_control.py) is the runtime transport.
It normalizes user messages into signals and delegates to
EOSGateway.handle() which routes through the execution spine.

UMH contract: interfaces NEVER contain intelligence. They:
1. Receive raw input from the transport (Telegram message, command)
2. Normalize to a UMH signal (text, metadata, chat context)
3. Call umh.run() or EOSGateway.handle()
4. Format the response for the transport and send it back

The actual service lives at services/telegram_control.py.
This package exists to hold any UMH-native Telegram adapters
that may replace the legacy service.
"""
