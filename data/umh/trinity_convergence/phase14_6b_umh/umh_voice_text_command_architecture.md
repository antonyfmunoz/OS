# UMH Voice, Text, and Command Architecture

Phase: 14.6B-UMH
Status: DRAFT

## Voice Input Pipeline

- **STT**: Whisper speech-to-text
- **VAD**: Silero Voice Activity Detection
- Pipeline: Audio -> Silero VAD (segment) -> Whisper STT (transcribe) -> text -> Gateway
- Voice session management in `substrate/execution/bridge/`

## TTS Output

- **Engine**: Kokoro 82M on Beast (100.74.199.102:8880)
- Python 3.12 venv at `E:\kokoro-tts`
- Auto-starts via `schtasks ONLOGON`
- VPS calls Beast TTS endpoint over Tailscale mesh

## Text Input (Discord)

- Discord messages enter via `services/discord_bot.py`
- `transports/discord/signal_factory.py` converts message -> `SignalEnvelope`
- SignalEnvelope routes to Gateway via `substrate/control_plane/runtime/gateway.py`
- Message handlers extracted to `services/discord_message_handlers.py`

## Cockpit Command Input

- `CommandPalette` component in cockpit frontend
- User input -> API call -> execution pipeline
- Routes through substrate Gateway like all other inputs

## CLI Input

- Claude Code running in tmux session on VPS
- Session target: `EOS_ROUTER_CLAUDE_CLI_SESSION=dex_main`
- Direct substrate access via Python imports

## Cockpit Voice Components

- `VoiceCommandBar`: voice input trigger and status display
- `VoiceWaveform`: real-time audio visualization during voice capture
- Both render in cockpit frontend shell chrome

## Intent Classification

### Regex Patterns (deterministic layer, runs first)
7 compiled regex patterns for high-confidence routing:
- Status queries
- Help/capability queries
- Approval/denial responses
- Navigation commands
- Search queries
- Configuration commands
- Greeting/acknowledgment

### Gateway Categories (AI-enhanced layer)
12 gateway routing categories for intent that regex cannot classify:
- strategic_decision
- operational_task
- information_query
- creative_generation
- analysis_request
- communication_draft
- scheduling
- governance_action
- system_administration
- learning_reflection
- relationship_management
- ambiguous (fallback)

Deterministic-first: regex patterns resolve before any LLM call. Gateway categories apply only when regex returns no match.
