"""
EntrepreneurOS Discord Bot — DEX conversational layer.

Auto-joins founder's voice channel. Routes text through EOS gateway.
Smart routing: simple → local Qwen (free) → Claude via EOS.
AI name is user-configurable via BIS or AI_NAME env var.

Channel map (create these in your server):
  #general        — freeform conversation
  #morning-brief  — auto-posted morning brief
  #strategy       — strategic decisions
  #outreach       — DM alerts and outreach ops
  #content        — content creation
  #decisions      — decisions queue
  #wins           — win announcements

Setup:
  1. discord.com/developers/applications → New Application
  2. Bot section → Add Bot → copy token
  3. Enable: Message Content Intent, Server Members Intent, Presence Intent
  4. OAuth2 → URL Generator → scopes: bot
     Permissions: Send Messages, Read Message History, Add Reactions,
                  Connect (voice), Speak (voice), Use Slash Commands
  5. Invite bot to your server
  6. Fill DISCORD_BOT_TOKEN, FOUNDER_DISCORD_ID, and channel IDs in .env
  7. docker compose up -d os-discord
"""

import asyncio
import logging
import os
import re
import sys
import tempfile
import traceback
from datetime import datetime
from pathlib import Path


# ─── Asyncio-level voice task exception suppressor ────────────────────────────
# on_error only catches event handler exceptions — Task exceptions (like the
# _MissingSentinel crash from poll_voice_ws) bypass it entirely. This handler
# intercepts them at the event loop level before they kill the process.

def _handle_task_exception(loop, context):
    exception = context.get('exception')
    if exception:
        msg = str(exception)
        if '_MissingSentinel' in msg or 'poll_event' in msg or 'poll_voice_ws' in msg:
            return  # silently ignore voice WS errors
    loop.default_exception_handler(context)

import discord
from discord.ext import commands
import wave
import time
from discord.sinks import Sink as AudioSink

# ─── Path bootstrap ───────────────────────────────────────────────────────────

_SCRIPT_DIR = Path(__file__).parent
_REPO_ROOT   = _SCRIPT_DIR.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from dotenv import load_dotenv
load_dotenv(_SCRIPT_DIR / ".env")
load_dotenv(_REPO_ROOT / "eos_ai" / ".env")

# ─── EOS imports ──────────────────────────────────────────────────────────────

from eos_ai.gateway import EOSGateway
from eos_ai.context import load_context_from_env
from eos_ai.knowledge_integrator import KnowledgeIntegrator
from eos_ai.voice_engine import VoiceEngine
from eos_ai.business_instance import get_ai_name
from eos_ai.discord_utils import chunk_message, post_to_webhook

# ─── Initialise ───────────────────────────────────────────────────────────────

_ctx_eos  = load_context_from_env()
_gateway  = EOSGateway()          # singleton — no ctx arg
_ki       = KnowledgeIntegrator(_ctx_eos)
_ve       = VoiceEngine()

from eos_ai.onboarding_engine import OnboardingEngine as _OnboardingEngine
_onboarding = _OnboardingEngine(_ctx_eos)

# Resolve AI name — refreshed on_ready so renames take effect on reconnect
AI_NAME = get_ai_name(_ctx_eos)

# Founder Discord user ID — bot auto-joins founder's voice channel
FOUNDER_ID = int(os.getenv('FOUNDER_DISCORD_ID', '0'))

# Channel sessions — one persistent session_id per channel
# Preserves conversation continuity within each channel across messages
_channel_sessions: dict[str, str] = {}

# ─── Multi-part message accumulation ─────────────────────────────────────────
# When founder sends Part 1/2, Part 2/2 etc., accumulate before processing.
_multipart_buffers: dict[str, dict] = {}
# channel -> {'parts': {1: text, 2: text, ...}, 'total': N, 'username': str}
_multipart_flush_tasks: dict[str, 'asyncio.Task'] = {}

_PART_RE_WORD  = re.compile(r'(?i)\bpart\s+(\d+)\s*/\s*(\d+)\b')   # "Part 1/2"
_PART_RE_START = re.compile(r'(?im)^(\d+)\s*/\s*(\d+)\s*[:\-\s]')  # "1/2:" at line start


def _detect_part(text: str) -> tuple[int, int] | None:
    """Return (part_num, total) if text is a multi-part fragment, else None."""
    m = _PART_RE_WORD.search(text)
    if m:
        return int(m.group(1)), int(m.group(2))
    m = _PART_RE_START.search(text)
    if m:
        return int(m.group(1)), int(m.group(2))
    return None


def _assemble_parts(buf: dict) -> str:
    """Combine buffered parts in order into a single prompt."""
    parts = buf.get('parts', {})
    ordered = [parts[i] for i in sorted(parts.keys()) if i in parts]
    return '\n\n'.join(ordered)


# ─── Silence-detecting voice sink ─────────────────────────────────────────────

class SilenceDetectingSink(AudioSink):
    def __init__(self, on_utterance, silence_threshold: float = 1.5):
        super().__init__()
        self.on_utterance      = on_utterance
        self.silence_threshold = silence_threshold
        self._buffers          = {}
        self._last_audio       = {}
        self._running          = True

    def write(self, data, user):
        if user is None:
            return
        uid = user  # user is already an int user_id
        if uid not in self._buffers:
            self._buffers[uid] = []
        self._buffers[uid].append(bytes(data))  # data is decoded PCM bytes
        self._last_audio[uid] = time.time()

    def cleanup(self):
        self._running = False
        self.finished = True  # prevent base-class format_audio crash

    async def monitor_silence(self, vc):
        while self._running and vc.is_connected():
            await asyncio.sleep(0.3)
            now      = time.time()
            to_flush = [
                uid for uid, t in list(self._last_audio.items())
                if now - t >= self.silence_threshold
                and self._buffers.get(uid)
            ]
            for uid in to_flush:
                frames = self._buffers.pop(uid, [])
                self._last_audio.pop(uid, None)
                if frames:
                    audio_path = tempfile.mktemp(suffix='.wav')
                    with wave.open(audio_path, 'wb') as wf:
                        wf.setnchannels(2)       # Discord: stereo
                        wf.setsampwidth(2)       # 16-bit samples
                        wf.setframerate(48000)   # 48 kHz
                        wf.writeframes(b''.join(frames))
                    asyncio.create_task(self.on_utterance(uid, audio_path))


def transcribe_with_groq(audio_path: str) -> str:
    try:
        from groq import Groq as GroqClient
        client = GroqClient(api_key=os.getenv('GROQ_API_KEY'))
        with open(audio_path, 'rb') as f:
            result = client.audio.transcriptions.create(
                model='whisper-large-v3-turbo',
                file=f,
                language='en',
            )
        text = result.text.strip()
        print(f'[Groq STT] Transcribed: {text[:50]}')
        return text
    except Exception as e:
        print(f'[Groq STT] Error: {e}')
        return ''

# ─── Channel IDs ──────────────────────────────────────────────────────────────
# Filled with real IDs from server — env vars allow override
CHANNEL_IDS: dict[str, int | None] = {
    'morning-brief': int(os.getenv('DISCORD_CHANNEL_MORNING_BRIEF',
                                    '1485765524766982234')),
    'outreach':      int(os.getenv('DISCORD_CHANNEL_OUTREACH',
                                    '1485765641821487166')),
    'wins':          int(os.getenv('DISCORD_CHANNEL_WINS',
                                    '1485765745312010260')),
    'general':       int(os.getenv('DISCORD_CHANNEL_GENERAL',
                                    '1485765456739696713')),
    'strategy':      int(os.getenv('DISCORD_CHANNEL_STRATEGY',
                                    '1485765556635304016')),
    'content':       int(os.getenv('DISCORD_CHANNEL_CONTENT',
                                    '1485765687531278516')),
    'decisions':     int(os.getenv('DISCORD_CHANNEL_DECISIONS',
                                    '1485765720775200808')),
}

# Channel name → intent routing hint
CHANNEL_MAP = {
    'general':       None,
    'morning-brief': 'BRIEF',
    'strategy':      'STRATEGY',
    'outreach':      'OUTREACH',
    'content':       'CONTENT',
    'decisions':     'DECISION',
    'wins':          None,
}

# ─── Active meeting state ─────────────────────────────────────────────────────

_active_meeting: dict = {
    'type':        None,   # 'sales_call', 'strategy_session', etc.
    'lead_name':   None,
    'started_at':  None,
    'notes':       [],     # raw utterances captured
    'key_points':  [],     # AI-extracted insights
}

# ─── Intent → gateway request type mapping ───────────────────────────────────

_INTENT_TO_TEAM: dict[str, tuple[str | None, str | None]] = {
    'OUTREACH':  ('sales',    'outreach_writer'),
    'RESEARCH':  ('research', 'market_analyst'),
    'CONTENT':   ('content',  'content_writer'),
    'STRATEGY':  (None,       None),
    'DECISION':  (None,       None),
    'TASK':      (None,       None),
    'INTEL':     ('research', 'signal_analyst'),
    'PORTFOLIO': (None,       None),
    'JOURNAL':   (None,       None),
    'MODEL':     (None,       None),
    'UNKNOWN':   (None,       None),
}

# ─── Bot setup ────────────────────────────────────────────────────────────────

intents = discord.Intents.default()
intents.message_content = True
intents.voice_states    = True
intents.presences       = True
intents.members         = True

bot = commands.Bot(
    command_prefix='!',
    intents=intents,
    help_command=None,
)

# Guard: don't attempt voice connects before on_ready fires.
# on_voice_state_update can fire during gateway resume before the bot
# is fully initialised — connecting to voice in that window causes a
# _MissingSentinel / poll_event crash.
_bot_ready: bool = False


# ─── Global error handler ─────────────────────────────────────────────────────

@bot.event
async def on_error(event, *args, **kwargs):
    """Prevent voice WS errors from killing the bot process."""
    err = traceback.format_exc()
    if '_MissingSentinel' in err or 'poll_voice_ws' in err:
        print('[Voice] WS error caught — ignoring')
        return
    print(f'[Bot] Error in {event}: {err}')


# ─── Gateway routing ──────────────────────────────────────────────────────────

def _build_request(text: str, intent: str, channel_name: str, username: str) -> dict:
    """Build a valid EOSGateway request dict from classified intent."""
    if intent == 'BRIEF':
        return {'type': 'brief', 'prompt': text, 'username': username}

    if intent == 'PORTFOLIO':
        return {'type': 'status', 'prompt': text, 'username': username}

    team, sub_agent = _INTENT_TO_TEAM.get(intent, (None, None))
    req: dict = {
        'type':       'agent_task',
        'prompt':     text,
        'username':   username,
        'venture_id': 'lyfe_institute',
    }
    if team:
        req['team']      = team
        req['sub_agent'] = sub_agent
    else:
        task_map = {
            'STRATEGY': 'ANALYZE', 'DECISION': 'ANALYZE',
            'TASK':     'GENERATE', 'JOURNAL':  'SUMMARIZE',
            'MODEL':    'ANALYZE',  'UNKNOWN':  'ANALYZE',
            'OUTREACH': 'GENERATE', 'CONTENT':  'GENERATE',
            'INTEL':    'ANALYZE',  'PORTFOLIO': 'ANALYZE',
        }
        req['task_type'] = task_map.get(intent, 'ANALYZE')
        req['sub_agent'] = 'executive_assistant'
    return req


def _run_gateway(text: str, channel_name: str, username: str) -> str:
    """
    Classify intent, build request, call gateway, return output text.
    Runs synchronously — called from asyncio executor to avoid blocking.
    """
    import uuid as _uuid_mod
    global _channel_sessions
    if channel_name not in _channel_sessions:
        _channel_sessions[channel_name] = str(_uuid_mod.uuid4())
    session_id = _channel_sessions[channel_name]

    # Classify intent
    intent = _gateway.classify_intent(text)
    print(f'[Discord] #{channel_name} | {username} | intent={intent}')

    # Use channel hint if intent is UNKNOWN
    if intent == 'UNKNOWN':
        channel_hint = CHANNEL_MAP.get(channel_name)
        if channel_hint:
            intent = channel_hint

    # Build and send
    req = _build_request(text, intent, channel_name, username)
    req['session_id'] = session_id
    req['channel']    = f'discord_{channel_name}'
    result = _gateway.handle(req)

    if result.get('status') == 'error':
        print(f'[Discord] Gateway error: {result.get("error")}')
        return f'Something went wrong: {result.get("error", "unknown error")}'

    if result.get('status') == 'pending':
        return f'Queued for approval — use `!approve {result["approval_id"]}` to execute.'

    output = result.get('output') or result.get('brief') or ''

    # Integrate into permanent knowledge (best-effort)
    try:
        _ki.integrate(
            content=(
                f'Discord #{channel_name}\n'
                f'User: {text[:300]}\n'
                f'System: {output[:300]}'
            ),
            source='discord_conversation',
            category='conversation',
            metadata={'channel': channel_name, 'user': username, 'intent': intent},
        )
    except Exception as e:
        print(f'[Discord] KI integrate failed (non-blocking): {e}')

    return output


# ─── Meeting mode ─────────────────────────────────────────────────────────────

async def handle_meeting_voice(
    text: str,
    meeting_type: str,
    channel,
) -> str:
    """Handle voice input during a meeting — surfaces context, detects signals."""
    _active_meeting['notes'].append(text)
    text_lower = text.lower()

    if any(w in text_lower for w in [
        'objection', 'they said', 'pushback', 'concern', 'but what about',
    ]):
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            lambda: __import__('eos_ai.agent_teams', fromlist=['run_team_task']).run_team_task(
                team='sales',
                sub_agent='objection_handler',
                prompt=f'Objection on call: {text}',
                venture_id='lyfe_institute',
                ctx=_ctx_eos,
            ),
        )
        return result.get('output', '')

    elif any(w in text_lower for w in [
        'price', 'cost', 'how much', 'what does it cost', 'investment',
    ]):
        return (
            'Initiate Arena: $750 one-time. '
            'Frame as investment not cost. '
            'Ask: what is staying stuck worth to you?'
        )

    elif any(w in text_lower for w in [
        'close', 'ready', 'lets do it', "let's do it",
        'sign up', 'where do i pay',
    ]):
        if channel:
            await channel.send(
                f'💰 **{AI_NAME}: Buying signal detected.**\n'
                f'Send the Whop link now.\n\n— {AI_NAME}'
            )
        return 'Buying signal. Send the link.'

    elif any(w in text_lower for w in [
        'end meeting', 'wrap up', 'that is all', 'thanks everyone',
    ]):
        await end_active_meeting(channel)
        return 'Meeting ended. Running post-meeting automation.'

    else:
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            lambda: _gateway.handle({
                'type':       'agent_task',
                'prompt':     text,
                'venture_id': 'lyfe_institute',
            }),
        )
        return result.get('output', '')


async def start_meeting_mode(
    meeting_type: str,
    lead_name: str = '',
    channel=None,
) -> str:
    """Activate meeting mode — loads pre-meeting brief, announces to channel."""
    from datetime import datetime, timezone

    _active_meeting['type']       = meeting_type
    _active_meeting['lead_name']  = lead_name
    _active_meeting['started_at'] = datetime.now(timezone.utc).isoformat()
    _active_meeting['notes']      = []
    _active_meeting['key_points'] = []

    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(
        None,
        lambda: __import__('eos_ai.agent_teams', fromlist=['run_team_task']).run_team_task(
            team='sales',
            sub_agent='closer',
            prompt=(
                f'Pre-meeting brief for {meeting_type} with '
                f'{lead_name or "lead"}. What do I need to know?'
            ),
            venture_id='lyfe_institute',
            ctx=_ctx_eos,
        ),
    )
    brief = result.get('output', '')

    if channel:
        await channel.send(
            f'📋 **{AI_NAME}: Meeting started — {meeting_type}**\n\n{brief}\n\n— {AI_NAME}'
        )

    # speak brief (fire-and-forget)
    asyncio.create_task(
        asyncio.get_event_loop().run_in_executor(
            None, _ve.speak, f'Meeting mode active. {brief[:200]}'
        )
    )

    return brief


async def end_active_meeting(channel=None) -> None:
    """End meeting mode and generate post-meeting summary."""
    if not _active_meeting['type']:
        return

    notes        = '\n'.join(_active_meeting['notes'][-20:])
    meeting_type = _active_meeting['type']
    lead_name    = _active_meeting['lead_name'] or 'lead'

    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(
        None,
        lambda: _gateway.handle({
            'type':       'agent_task',
            'prompt':     (
                f'Summarize this {meeting_type} with {lead_name}. '
                f'Key points, outcome, next steps:\n\n{notes}'
            ),
            'venture_id': 'lyfe_institute',
        }),
    )
    summary = result.get('output', '')

    if channel:
        await channel.send(
            f'📝 **{AI_NAME}: Meeting summary**\n\n{summary}\n\n— {AI_NAME}'
        )

    # clear state
    _active_meeting['type']       = None
    _active_meeting['lead_name']  = None
    _active_meeting['notes']      = []
    _active_meeting['key_points'] = []


# ─── Startup ──────────────────────────────────────────────────────────────────

@bot.event
async def on_ready():
    global AI_NAME, _bot_ready

    # Reset immediately so any voice state events replayed during this
    # RESUME cycle are ignored until we're fully ready.
    _bot_ready = False

    # Suppress _MissingSentinel / poll_voice_ws Task exceptions at the loop level.
    # These crash the process when voice WS dies — on_error doesn't reach them.
    asyncio.get_event_loop().set_exception_handler(_handle_task_exception)

    AI_NAME = get_ai_name(_ctx_eos)  # refresh in case BIS updated

    # Clean up any stale/broken voice clients left from the previous session.
    # py-cord tries to resume voice connections on reconnect — if the resume
    # fails (Task poll_event crash) the client object lingers in a broken state
    # and our join guard would skip the founder's next join attempt.
    for guild in bot.guilds:
        if guild.voice_client:
            try:
                await guild.voice_client.disconnect(force=True)
                print('[Voice] Cleaned up stale voice client on ready')
            except Exception:
                pass

    # Short grace period: Discord replays voice state events during RESUME
    # right around on_ready. Wait for that window to pass before allowing
    # our handler to act on voice events.
    await asyncio.sleep(2)
    _bot_ready = True

    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.watching,
            name=f'over you — {AI_NAME}',
        )
    )
    print(f'[Discord] {AI_NAME} online as {bot.user} (id={bot.user.id})')
    print(f'[Discord] Serving {len(bot.guilds)} server(s)')

    # Start ambient refresh (same as Telegram bot)
    try:
        from eos_ai.orchestrator import start_ambient_refresh_loop
        start_ambient_refresh_loop(_ctx_eos)
        print('[Discord] Ambient refresh started')
    except Exception as e:
        print(f'[Discord] Ambient refresh skipped: {e}')

    # Set up EOS Discord structure (idempotent — only creates missing channels)
    for guild in bot.guilds:
        bot.loop.create_task(_setup_server_structure(guild))


# ─── Auto-join voice ──────────────────────────────────────────────────────────

@bot.event
async def on_voice_state_update(
    member: discord.Member,
    before: discord.VoiceState,
    after:  discord.VoiceState,
):
    # Only watch the founder, and only after the bot is fully ready
    if not _bot_ready or FOUNDER_ID == 0 or member.id != FOUNDER_ID:
        return

    # Get general text channel for announcements
    general = None
    general_id = CHANNEL_IDS.get('general')
    if general_id:
        general = bot.get_channel(general_id)
    if not general:
        general = discord.utils.get(member.guild.text_channels, name='general')

    # Founder JOINED a voice channel (before=None, after=Channel)
    if after.channel is not None and before.channel is None:
        # Capture channel reference at event time — after.channel may be None later
        target_channel = after.channel
        print(f'[Voice] Branch: FOUNDER JOINED {target_channel.name}')
        await asyncio.sleep(3)
        # Re-check: founder must still be in that channel after the sleep.
        # If they left during the 3s window the LEFT branch already fired but
        # found no voice_client — without this guard we'd connect anyway.
        if member not in target_channel.members:
            print('[Voice] Founder left during sleep — aborting connect')
            return
        if member.guild.voice_client:
            return  # already connected
        vc = None
        max_attempts = 2
        await asyncio.sleep(10)
        print('[Voice] Starting connect sequence')
        for attempt in range(max_attempts):
            try:
                # Verify founder is still in the target channel before each attempt
                founder_member = member.guild.get_member(FOUNDER_ID)
                if (
                    not founder_member
                    or not founder_member.voice
                    or founder_member.voice.channel != target_channel
                ):
                    print('[Voice] Founder no longer in target channel — aborting')
                    return
                if target_channel is None:
                    print('[Voice] Channel reference lost — aborting')
                    return

                # disconnect any lingering voice client before each attempt
                if member.guild.voice_client:
                    try:
                        await member.guild.voice_client.disconnect(force=True)
                        await asyncio.sleep(1)
                    except Exception:
                        pass

                vc = await target_channel.connect(
                    timeout=15.0,
                    reconnect=False,  # we handle reconnects ourselves
                )
                print(f'[Voice] Connected on attempt {attempt + 1}')
                break  # success
            except discord.errors.ConnectionClosed as e:
                if '4006' in str(e) or 'session' in str(e).lower():
                    wait = 5 if attempt == 0 else (attempt + 1) * 30
                    print(f'[Voice] 4006 on attempt {attempt + 1} — waiting {wait}s before retry')
                    # Force-disconnect any stale session before retry
                    if member.guild.voice_client:
                        try:
                            await member.guild.voice_client.disconnect(force=True)
                        except Exception:
                            pass
                    await asyncio.sleep(wait)
                    continue
                print(f'[Voice] Connect closed: {e}')
                return
            except Exception as e:
                print(f'[Voice] Connect failed: {e}')
                if 'Already connected' in str(e):
                    if member.guild.voice_client:
                        try:
                            await member.guild.voice_client.disconnect(force=True)
                            await asyncio.sleep(2)
                        except Exception:
                            pass
                    continue
                return
        else:
            print('[Voice] Max connect attempts reached — aborting')
            return

        # verify WS initialized before starting the listen loop
        await asyncio.sleep(2)
        if not hasattr(vc, 'ws') or vc.ws is discord.utils.MISSING:
            print('[Voice] WS not initialized — aborting')
            try:
                await vc.disconnect(force=True)
            except Exception:
                pass
            return

        print(f'[Voice] WS ready: {type(vc.ws).__name__}')
        if general:
            await general.send(f'👁️ **{AI_NAME} Joined {target_channel.name} voice chat.**')
        asyncio.create_task(_listen_loop(vc, general))

    # Founder LEFT voice channel (before=Channel, after=None)
    elif before.channel is not None and after.channel is None:
        print(f'[Voice] Branch: FOUNDER LEFT {before.channel.name}')
        if member.guild.voice_client:
            try:
                await member.guild.voice_client.disconnect()
            except Exception:
                pass
        if general:
            await general.send(f'👁️ **{AI_NAME} Disconnected from {before.channel.name} voice chat.**')
                               
    # Founder SWITCHED channels (both not None)
    elif (before.channel is not None and after.channel is not None
          and before.channel.id != after.channel.id):
        print(f'[Voice] Branch: FOUNDER SWITCHED {before.channel.name} → {after.channel.name}')
        if member.guild.voice_client:
            try:
                await member.guild.voice_client.move_to(after.channel)
            except Exception:
                pass
        if general:
            await general.send(
                f'👁️ **{AI_NAME} followed you to {after.channel.name}.**'
            )


async def _listen_loop(
    vc: discord.VoiceClient,
    text_channel: discord.TextChannel | None,
) -> None:
    """
    Silence-detection voice loop.

    SilenceDetectingSink accumulates per-user audio frames and flushes each
    user's buffer after 1.5 s of silence.  Groq whisper-large-v3-turbo
    transcribes the resulting WAV.  All routing logic is unchanged.
    """
    print('[Voice] *** LISTEN LOOP STARTED ***')
    print(f'[Voice] Channel: {vc.channel}')

    async def on_utterance(user_id: int, audio_path: str) -> None:
        try:
            loop = asyncio.get_event_loop()
            text = await loop.run_in_executor(
                None, transcribe_with_groq, audio_path
            )
            try:
                os.remove(audio_path)
            except Exception:
                pass

            if not text or len(text.split()) < 2:
                return

            print(f'[Voice] Heard: {text}')

            should_respond, classification = _ve.should_respond(text, 0.0)
            print(f'[Voice] [{classification}] respond={should_respond}')

            if not should_respond:
                return

            context_summary = _ve.intelligent.get_context_summary()
            prompt = (
                f'{context_summary}\n\nCurrent: {text}'
                if context_summary else text
            )

            # Auto-detect meeting context
            if not _active_meeting.get('type'):
                meeting_ctx = _ve.intelligent.detect_meeting_context(
                    text, list(_ve.intelligent.context_window)
                )
                if meeting_ctx and meeting_ctx['confidence'] > 0.6:
                    _active_meeting['type'] = meeting_ctx['type']
                    if text_channel:
                        await text_channel.send(
                            f'📋 **{AI_NAME}: {meeting_ctx["type"]} detected.**\n'
                            f"Taking notes. I'll surface relevant context as needed.\n\n— {AI_NAME}"
                        )

            meeting_type = _active_meeting.get('type')

            if meeting_type:
                _active_meeting['notes'].append(text)
                response = await handle_meeting_voice(text, meeting_type, text_channel)
                if not response:
                    result = await loop.run_in_executor(
                        None,
                        lambda: _gateway.handle({
                            'type':       'agent_task',
                            'prompt':     prompt,
                            'sub_agent':  'executive_assistant',
                            'venture_id': 'lyfe_institute',
                        }),
                    )
                    response = result.get('output', '')
            elif _ve.is_simple_query(text) and _ve.is_running():
                response = await loop.run_in_executor(None, _ve.query_local, text)
                if not response:
                    result = await loop.run_in_executor(
                        None,
                        lambda: _gateway.handle({
                            'type':       'agent_task',
                            'prompt':     prompt,
                            'sub_agent':  'executive_assistant',
                            'venture_id': 'lyfe_institute',
                        }),
                    )
                    response = result.get('output', '')
            else:
                result = await loop.run_in_executor(
                    None,
                    lambda: _gateway.handle({
                        'type':       'agent_task',
                        'prompt':     prompt,
                        'sub_agent':  'executive_assistant',
                        'venture_id': 'lyfe_institute',
                    }),
                )
                response = result.get('output', '')

            if not response:
                return

            _ve.intelligent.add_to_context(text, classification, response)

            if text_channel:
                user = bot.get_user(user_id)
                name = user.display_name if user else 'You'
                msg  = f'🎙️ **{name}:** {text}\n**{AI_NAME}:** {response}'
                for chunk in chunk_message(msg):
                    await text_channel.send(chunk)

            audio_out = await loop.run_in_executor(None, _ve.speak, response[:300])
            if audio_out and os.path.exists(audio_out):
                while vc.is_playing():
                    await asyncio.sleep(0.3)
                if vc.is_connected():
                    vc.play(discord.FFmpegPCMAudio(audio_out))

            try:
                _ki.integrate(
                    content=(
                        f'Voice [{classification}]:\n'
                        f'User: {text}\n'
                        f'{AI_NAME}: {response}'
                    ),
                    source='discord_voice',
                    category='conversation',
                    metadata={
                        'classification': classification,
                        'meeting_type':   _active_meeting.get('type'),
                    },
                )
            except Exception as e:
                print(f'[Voice] KI integrate failed: {e}')

        except Exception as e:
            print(f'[Voice] Utterance error: {e}')
            import traceback
            traceback.print_exc()

    sink = SilenceDetectingSink(on_utterance=on_utterance, silence_threshold=1.5)

    try:
        vc.start_recording(sink, lambda *a: None, None)
        print('[Voice] Silence detection active')
    except Exception as e:
        print(f'[Voice] Failed to start: {e}')
        import traceback
        traceback.print_exc()
        return

    asyncio.create_task(sink.monitor_silence(vc))

    if text_channel:
        await text_channel.send(f'👁️ **{AI_NAME} is listening.**')

    while vc.is_connected():
        await asyncio.sleep(1)

    print('[Voice] Disconnected — stopping')
    sink.cleanup()
    try:
        vc.stop_recording()
    except Exception:
        pass

    print('[Voice] Loop ended')


# ─── Message handler ──────────────────────────────────────────────────────────

@bot.event
async def on_message(message: discord.Message):
    # Ignore self and other bots
    if message.author == bot.user or message.author.bot:
        return

    # Handle audio file attachments → transcribe → route → speak back
    if message.attachments:
        for att in message.attachments:
            ext = Path(att.filename).suffix.lower()
            if ext in {'.wav', '.mp3', '.ogg', '.m4a', '.flac', '.opus'}:
                async with message.channel.typing():
                    tmp = tempfile.mktemp(suffix=ext)
                    await att.save(tmp)
                    loop = asyncio.get_event_loop()
                    transcribed = await loop.run_in_executor(
                        None, _ve.transcribe, tmp
                    )
                    if transcribed:
                        await message.add_reaction('🎙️')
                        response = await loop.run_in_executor(
                            None,
                            _run_gateway,
                            transcribed,
                            getattr(message.channel, 'name', 'dm'),
                            str(message.author),
                        )
                        reply = (
                            f'🎙️ **You said:** {transcribed}\n'
                            f'**{AI_NAME}:** {response}'
                        )
                        for chunk in chunk_message(reply):
                            await message.reply(chunk)
                        # Speak in voice if connected
                        if message.guild and message.guild.voice_client:
                            vc = message.guild.voice_client
                            if vc.is_connected() and not vc.is_playing():
                                audio_out = await loop.run_in_executor(
                                    None, _ve.speak, response[:300]
                                )
                                if audio_out and os.path.exists(audio_out):
                                    vc.play(discord.FFmpegPCMAudio(audio_out))
                    else:
                        await message.reply('Could not transcribe that audio.')
                    try:
                        Path(tmp).unlink(missing_ok=True)
                    except Exception:
                        pass
                return

    text = message.content.strip()
    if not text:
        await bot.process_commands(message)
        return

    channel_name = (
        message.channel.name
        if hasattr(message.channel, 'name')
        else 'dm'
    )
    username = str(message.author)

    # #wins is one-way announcement channel
    if channel_name == 'wins':
        await bot.process_commands(message)
        return

    # ── Active onboarding session — route before anything else ────────────────
    if message.guild:
        _ob_session = _onboarding.get_session(str(message.guild.id))
        if _ob_session and not _ob_session.completed:
            # Store answer to the last question asked
            if _ob_session.pending_question:
                _onboarding.store_answer(_ob_session, text)

            next_q = _onboarding.get_next_question(_ob_session)

            if next_q:
                await message.channel.send(next_q)
            else:
                # All questions answered — provision
                await message.channel.send('⚙️ **Provisioning your EOS...**')
                try:
                    provision_result = await _onboarding.analyze_and_provision(_ob_session)

                    # Discord structure (handled here — engine can't import bot)
                    try:
                        mgr = DiscordServerManager(message.guild)
                        await mgr.setup_eos_structure()
                        await mgr.align_structure()
                        provision_result['results']['discord'] = 'provisioned'
                        print('[Onboarding] Discord structure provisioned')
                    except Exception as _de:
                        provision_result['results']['discord'] = f'error: {_de}'

                    completion = _onboarding.get_completion_message(
                        provision_result['data'],
                        provision_result['results'],
                    )
                    for chunk in chunk_message(completion):
                        await message.channel.send(chunk)
                except Exception as _pe:
                    print(f'[Onboarding] Provisioning error: {_pe}')
                    await message.channel.send(
                        f'⚠️ Provisioning encountered an issue: {_pe}\n'
                        'Run `!onboard` again to retry.'
                    )
            return

    # Meeting mode triggers — natural language detection
    meeting_match = re.search(
        r'(?:start|begin|kick off|starting)\s+'
        r'(?:a\s+)?(?:meeting|call|session|review)'
        r'(?:\s+with\s+(\w+))?',
        text, re.IGNORECASE,
    )
    if meeting_match:
        lead = meeting_match.group(1) or ''
        await start_meeting_mode('sales_call', lead, message.channel)
        return

    if any(p in text.lower() for p in [
        'end the meeting', 'end meeting', 'wrap up',
        'meeting over', 'call done', 'done with the call',
    ]):
        await end_active_meeting(message.channel)
        return

    # ── Multi-part accumulation ───────────────────────────────────────────────
    part_info = _detect_part(text)
    if part_info:
        part_num, total_parts = part_info
        ch_key = channel_name

        # Initialise or reset buffer if this is a new series
        if (ch_key not in _multipart_buffers
                or _multipart_buffers[ch_key].get('total') != total_parts):
            _multipart_buffers[ch_key] = {
                'parts': {}, 'total': total_parts, 'username': username,
            }

        _multipart_buffers[ch_key]['parts'][part_num] = text

        # Cancel any existing timeout task for this channel
        if ch_key in _multipart_flush_tasks:
            _multipart_flush_tasks[ch_key].cancel()
            _multipart_flush_tasks.pop(ch_key, None)

        if part_num < total_parts:
            # Not the last part — acknowledge and wait
            await message.add_reaction('⏳')

            async def _flush_after_timeout(
                chan_key: str,
                chan: discord.abc.Messageable,
                orig_message: discord.Message,
                cname: str,
                uname: str,
            ) -> None:
                await asyncio.sleep(30)
                buf = _multipart_buffers.pop(chan_key, None)
                if not buf:
                    return
                combined = _assemble_parts(buf)
                async with chan.typing():
                    ev_loop = asyncio.get_event_loop()
                    out = await ev_loop.run_in_executor(
                        None, _run_gateway, combined, cname, uname,
                    )
                if out:
                    await _send_response(orig_message, out)

            task = asyncio.create_task(
                _flush_after_timeout(
                    ch_key, message.channel, message, channel_name, username,
                )
            )
            _multipart_flush_tasks[ch_key] = task
            await bot.process_commands(message)
            return

        else:
            # Final part — assemble and fall through to normal processing
            buf = _multipart_buffers.pop(ch_key, None)
            if buf:
                text = _assemble_parts(buf)

    # Smart routing: simple → local Qwen (free) → Claude via EOS gateway
    async with message.channel.typing():
        loop = asyncio.get_event_loop()

        if _ve.is_simple_query(text) and _ve.is_running():
            local_response = await loop.run_in_executor(
                None, _ve.query_local, text
            )
            if local_response:
                for chunk in chunk_message(local_response):
                    await message.reply(chunk)
                await bot.process_commands(message)
                return

        # Complex query or Ollama unavailable → full EOS gateway
        output = await loop.run_in_executor(
            None,
            _run_gateway,
            text,
            channel_name,
            username,
        )

    if output:
        # Determine if founder is in a voice channel before responding
        founder_in_voice = False
        founder_member = None
        try:
            if message.guild and message.author.id == FOUNDER_ID:
                founder_member = message.guild.get_member(FOUNDER_ID)
                if (founder_member and founder_member.voice
                        and founder_member.voice.channel):
                    founder_in_voice = True
        except Exception:
            pass

        # Always post text response
        await _send_response(message, output)

        if founder_in_voice:
            # Also speak via TTS in voice channel
            try:
                vc = message.guild.voice_client
                if not vc or not vc.is_connected():
                    vc = await founder_member.voice.channel.connect(
                        timeout=10.0,
                        reconnect=False,
                    )
                audio_path = await asyncio.get_event_loop().run_in_executor(
                    None, _ve.speak, output[:300]
                )
                if audio_path and os.path.exists(audio_path):
                    while vc.is_playing():
                        await asyncio.sleep(0.3)
                    def cleanup(error):
                        try:
                            os.remove(audio_path)
                        except Exception:
                            pass
                    vc.play(
                        discord.FFmpegPCMAudio(audio_path),
                        after=cleanup,
                    )
                    print(f'[Voice] Speaking: {output[:50]}...')
            except Exception as e:
                print(f'[Voice] TTS check: {e}')

    await bot.process_commands(message)


async def _send_response(message: discord.Message, output: str) -> None:
    """Split long responses at paragraph boundaries."""
    output = output.rstrip() + f'\n\n— {AI_NAME}'
    for chunk in chunk_message(output):
        await message.reply(chunk)


# ─── Discord Server Manager ───────────────────────────────────────────────────

class DiscordServerManager:
    """Idempotent Discord server structure manager.
    Creates channels and categories only if they don't already exist.
    Called on bot ready and via !setup command.
    """

    def __init__(self, guild: discord.Guild):
        self.guild = guild

    async def ensure_category(self, name: str) -> discord.CategoryChannel:
        """Find or create a category."""
        existing = discord.utils.get(self.guild.categories, name=name)
        if existing:
            return existing
        cat = await self.guild.create_category(name)
        print(f'[Discord] Created category: {name}')
        return cat

    async def ensure_channel(
        self,
        name: str,
        category_name: str | None = None,
        topic: str = '',
        channel_type: str = 'text',
    ) -> discord.abc.GuildChannel | None:
        """Find or create a channel. Returns channel object."""
        if channel_type == 'voice':
            existing = discord.utils.get(self.guild.voice_channels, name=name)
        else:
            existing = discord.utils.get(self.guild.text_channels, name=name)
        if existing:
            return existing

        category = None
        if category_name:
            category = await self.ensure_category(category_name)

        try:
            if channel_type == 'voice':
                ch = await self.guild.create_voice_channel(name=name, category=category)
            else:
                ch = await self.guild.create_text_channel(
                    name=name, topic=topic, category=category
                )
            print(f'[Discord] Created #{name}')
            return ch
        except discord.Forbidden:
            print(f'[Discord] Permission denied creating #{name}')
            return None
        except Exception as e:
            print(f'[Discord] Error creating #{name}: {e}')
            return None

    async def setup_eos_structure(self) -> list[str]:
        """Create full EOS Discord structure. Only creates what doesn't exist."""
        print('[Discord] Setting up EOS structure...')

        structure: dict[str, list[tuple[str, str, str]]] = {
            '🧠 EOS': [
                ('general',        'text',  'Main conversation with DEX'),
                ('morning-brief',  'text',  'Daily intelligence from DEX'),
                ('decisions',      'text',  'Logged decisions'),
                ('wins',           'text',  'Closed deals and wins'),
                ('agent-activity', 'text',  'EOS agent activity log'),
            ],
            '⚡ Empyrean Creative': [
                ('empyrean-strategy', 'text', 'Empyrean Creative strategic decisions'),
                ('empyrean-pipeline', 'text', 'Empyrean Creative sales pipeline'),
                ('empyrean-outreach', 'text', 'Empyrean Creative outreach tracking'),
            ],
            '🏢 Lyfe Institute': [
                ('lyfe-strategy', 'text', 'Lyfe Institute strategy'),
                ('lyfe-pipeline', 'text', 'Initiate Arena pipeline'),
                ('lyfe-outreach', 'text', 'Instagram DM tracking'),
            ],
            '👤 Personal Brand': [
                ('brand-strategy', 'text', 'Personal brand strategy'),
                ('content-ideas',  'text', 'Content ideas and calendar'),
            ],
            '🎙️ Voice': [
                ("Founder's Office", 'voice', ''),
            ],
        }

        created: list[str] = []
        for category_name, channels in structure.items():
            for ch_name, ch_type, topic in channels:
                ch = await self.ensure_channel(
                    name=ch_name,
                    category_name=category_name,
                    topic=topic,
                    channel_type=ch_type,
                )
                if ch:
                    created.append(ch_name)

        # Remove War Room if it exists — one voice channel only
        war_room_vc = discord.utils.get(self.guild.voice_channels, name='War Room')
        if war_room_vc:
            await war_room_vc.delete(reason='One voice channel only')
            print('[Discord] Removed War Room voice')

        print(f'[Discord] Structure ready: {len(created)} channels verified')
        return created

    async def align_structure(self) -> None:
        """
        Enforce the canonical EOS channel layout.
        Moves uncategorized channels into 🧠 EOS.
        Removes redundant generic channels.
        Safe to call on every startup.
        """
        print('[Discord] Aligning structure...')

        # Get or create 🧠 EOS category
        eos_cat = discord.utils.get(self.guild.categories, name='🧠 EOS')
        if not eos_cat:
            eos_cat = await self.guild.create_category('🧠 EOS')
            print('[Discord] Created 🧠 EOS category')

        # Recreate #general if deleted, or move if uncategorized
        general = discord.utils.get(self.guild.text_channels, name='general')
        if not general:
            general = await self.guild.create_text_channel(
                name='general',
                topic='Primary conversation with DEX',
                category=eos_cat,
            )
            print('[Discord] Recreated #general')
        elif general.category != eos_cat:
            await general.edit(category=eos_cat)
            print('[Discord] Moved #general → 🧠 EOS')

        # Move these channels into 🧠 EOS if not already there
        move_to_eos = ['morning-brief', 'decisions', 'wins', 'agent-activity']
        for ch_name in move_to_eos:
            ch = discord.utils.get(self.guild.text_channels, name=ch_name)
            if ch and ch.category != eos_cat:
                await ch.edit(category=eos_cat)
                print(f'[Discord] Moved #{ch_name} → 🧠 EOS')

        # Remove redundant generic channels — company-specific equivalents exist
        for ch_name in ('strategy', 'outreach', 'content'):
            ch = discord.utils.get(self.guild.text_channels, name=ch_name)
            if ch:
                await ch.delete(reason='Redundant — company-specific channels exist')
                print(f'[Discord] Removed #{ch_name}')

        # War Room guard — belt-and-suspenders
        war_room = discord.utils.get(self.guild.voice_channels, name='War Room')
        if war_room:
            await war_room.delete(reason='One voice channel only')
            print('[Discord] Removed War Room voice')

        print('[Discord] Structure aligned ✅')

    async def update_for_stage_change(
        self,
        company: str,
        new_stage: int,
    ) -> list[str]:
        """Create stage-appropriate channels when a venture advances."""
        stage_channels: dict[int, list[tuple[str, str, str]]] = {
            2: [
                (f'{company}-content', 'text', 'Content strategy (unlocked Stage 2)'),
                (f'{company}-systems', 'text', 'Systems and processes'),
            ],
            3: [
                (f'{company}-hiring',     'text', 'Hiring and team building'),
                (f'{company}-operations', 'text', 'Operations management'),
            ],
        }

        new_channels = stage_channels.get(new_stage, [])
        category_name = company.replace('_', ' ').title()
        created: list[str] = []

        for ch_name, ch_type, topic in new_channels:
            ch = await self.ensure_channel(
                name=ch_name,
                category_name=category_name,
                topic=topic,
            )
            if ch:
                created.append(ch_name)

        # Announce in general
        general = discord.utils.get(self.guild.text_channels, name='general')
        if general:
            await general.send(
                f'🎯 **Stage {new_stage} unlocked for {company}.**\n\n'
                f'New channels and primitives now active.\n'
                f'{AI_NAME} has updated your operating system.\n\n— {AI_NAME}'
            )

        return created


async def _setup_server_structure(guild: discord.Guild) -> None:
    """Called on_ready to ensure EOS Discord structure exists."""
    try:
        mgr = DiscordServerManager(guild)
        await mgr.setup_eos_structure()
        await mgr.align_structure()
    except Exception as e:
        print(f'[Discord] Server setup error: {e}')


# ─── Commands ─────────────────────────────────────────────────────────────────

@bot.command(name='brief')
async def cmd_brief(ctx: commands.Context):
    """Trigger morning brief on demand."""
    async with ctx.typing():
        loop   = asyncio.get_event_loop()
        output = await loop.run_in_executor(
            None,
            lambda: _run_gateway('morning brief', ctx.channel.name, str(ctx.author)),
        )
    await ctx.reply(output or 'Brief generated.')


@bot.command(name='status')
async def cmd_status(ctx: commands.Context):
    """System health check."""
    async with ctx.typing():
        loop   = asyncio.get_event_loop()
        output = await loop.run_in_executor(
            None,
            lambda: _run_gateway('system status', ctx.channel.name, str(ctx.author)),
        )
    await ctx.reply(output or 'Status retrieved.')


@bot.command(name='join')
async def cmd_join(ctx: commands.Context):
    """Join the voice channel the user is currently in."""
    if not ctx.author.voice:
        await ctx.reply('Join a voice channel first.')
        return
    channel = ctx.author.voice.channel
    already_connected = bool(ctx.voice_client)
    if already_connected:
        await ctx.voice_client.move_to(channel)
        vc = ctx.voice_client
    else:
        vc = await channel.connect()
    await ctx.send(
        f'🎙️ **{AI_NAME} connected.** Talk to me. '
        'Drop an audio file and I\'ll transcribe + respond.'
    )
    # Only start the listen loop on a fresh connect.
    # Auto-join (on_voice_state_update) already started it if the bot
    # was already in a channel — starting a second loop causes duplicate recording.
    if not already_connected:
        await asyncio.sleep(3)  # wait for voice WS to initialize
        asyncio.create_task(_listen_loop(vc, ctx.channel))


@bot.command(name='leave')
async def cmd_leave(ctx: commands.Context):
    """Disconnect from voice channel."""
    if ctx.voice_client:
        await ctx.voice_client.disconnect()
        await ctx.send(f'👁️ **{AI_NAME} disconnected.**')
    else:
        await ctx.reply('Not connected to any voice channel.')


@bot.command(name='say')
async def cmd_say(ctx: commands.Context, *, text: str):
    """Speak text aloud in the voice channel."""
    if not ctx.voice_client:
        await ctx.reply('Use `!join` first to connect to voice.')
        return
    if ctx.voice_client.is_playing():
        ctx.voice_client.stop()
    loop       = asyncio.get_event_loop()
    audio_path = await loop.run_in_executor(None, _ve.speak, text)
    if audio_path and os.path.exists(audio_path):
        ctx.voice_client.play(discord.FFmpegPCMAudio(audio_path))
        await ctx.send(f'🔊 {text[:80]}{"..." if len(text) > 80 else ""}')
    else:
        await ctx.reply('TTS failed — check that espeak is installed.')


@bot.command(name='approve')
async def cmd_approve(ctx: commands.Context, approval_id: str = ''):
    """Approve a pending gateway action."""
    if not approval_id:
        await ctx.reply('Usage: `!approve <approval_id>`')
        return
    result = _gateway.approve(approval_id)
    if result.get('status') == 'ok':
        output = result.get('output') or 'Approved and executed.'
        for chunk in chunk_message(output):
            await ctx.reply(chunk)
    else:
        await ctx.reply(f'Error: {result.get("error", "unknown")}')


@bot.command(name='setup')
async def cmd_setup(ctx: commands.Context):
    """Setup EOS Discord server structure. Founder only."""
    if ctx.author.id != FOUNDER_ID:
        await ctx.reply('Only the founder can run setup.')
        return
    async with ctx.typing():
        mgr = DiscordServerManager(ctx.guild)
        created = await mgr.setup_eos_structure()
    await ctx.reply(
        f'✅ **EOS Discord structure ready.**\n'
        f'{len(created)} channels verified across all companies.'
    )


@bot.command(name='align')
async def cmd_align(ctx: commands.Context):
    """Align Discord structure with EOS architecture. Founder only."""
    if ctx.author.id != FOUNDER_ID:
        await ctx.reply('Only the founder can run this.')
        return
    async with ctx.typing():
        mgr = DiscordServerManager(ctx.guild)
        await mgr.align_structure()
    await ctx.reply(
        '✅ Discord structure aligned.\n'
        '🧠 EOS category organized.\n'
        'Redundant channels removed.'
    )


@bot.command(name='report')
async def cmd_report(ctx: commands.Context, report_type: str = 'profile'):
    """Send EOS reports on demand. Types: profile, pulse. Founder only."""
    if ctx.author.id != FOUNDER_ID:
        await ctx.reply('Founder only.')
        return

    if report_type == 'profile':
        async with ctx.typing():
            profile_path = Path('/opt/OS/data/founder_profile.md')
            if not profile_path.exists():
                await ctx.reply('No profile yet. Run a GWS scan first.')
                return
            profile = profile_path.read_text()
        for chunk in chunk_message(profile, title='📊 EOS LEARNING REPORT'):
            await ctx.channel.send(chunk)
        await ctx.message.add_reaction('✅')

    elif report_type == 'pulse':
        await ctx.reply('Running world pulse scan... (this takes a minute)')
        loop = asyncio.get_event_loop()
        results = await loop.run_in_executor(
            None,
            lambda: __import__('eos_ai.world_pulse', fromlist=['WorldPulse']).WorldPulse(_ctx_eos).run_pulse_scan(),
        )
        total = results.get('total_integrated', 0)
        await ctx.reply(f'✅ Pulse scan complete. {total} items integrated. Report posted via webhook.')

    else:
        await ctx.reply('Usage: `!report profile` or `!report pulse`')


@bot.command(name='onboard')
async def cmd_onboard(ctx: commands.Context):
    """Start the EOS onboarding flow for a new founder."""
    if not ctx.guild:
        await ctx.reply('Run this in a server, not a DM.')
        return

    session = _onboarding.start_session(
        org_id=str(ctx.guild.id),
        user_id=str(ctx.author.id),
    )
    welcome = _onboarding.get_welcome_message()
    await ctx.reply(welcome)

    # Get and send the first question immediately
    first_q = _onboarding.get_next_question(session)
    if first_q:
        await ctx.send(first_q)


@bot.command(name='sync')
async def cmd_sync(ctx: commands.Context):
    """Run the Daily Sync meeting now."""
    async with ctx.typing():
        def _run():
            try:
                from eos_ai.daily_sync import DailySyncEngine
                dse = DailySyncEngine(_ctx_eos)
                return dse.run_sync()
            except Exception as e:
                return f'Daily sync error: {e}'
        loop   = asyncio.get_event_loop()
        output = await loop.run_in_executor(None, _run)
    for chunk in chunk_message(output):
        await ctx.reply(chunk)


@bot.command(name='inbox')
async def cmd_inbox(ctx: commands.Context):
    """Show Email GPS status — current inbox routing."""
    async with ctx.typing():
        def _run():
            try:
                from eos_ai.email_gps import EmailGPS
                gps       = EmailGPS(_ctx_eos)
                processed = gps.process_inbox(limit=20)
                return gps.generate_inbox_report(processed)
            except Exception as e:
                return f'Email GPS error: {e}'
        loop   = asyncio.get_event_loop()
        output = await loop.run_in_executor(None, _run)
    await ctx.reply(output)


@bot.command(name='draft')
async def cmd_draft(ctx: commands.Context):
    """Show email drafts awaiting approval."""
    async with ctx.typing():
        def _run():
            try:
                from eos_ai.email_gps import EmailGPS
                gps       = EmailGPS(_ctx_eos)
                processed = gps.process_inbox(limit=20)
                drafts    = gps.get_drafts_pending(processed)
                if not drafts:
                    return '📬 No drafts pending approval.'
                lines = [f'📝 **{len(drafts)} Draft(s) Ready for Approval**\n']
                for i, e in enumerate(drafts[:5], 1):
                    lines.append(
                        f'**{i}. To:** {e.from_name or e.from_address}\n'
                        f'**Subject:** {e.subject}\n'
                        f'**Draft:**\n{e.draft_response[:400]}\n'
                    )
                return '\n'.join(lines)
            except Exception as e:
                return f'Draft error: {e}'
        loop   = asyncio.get_event_loop()
        output = await loop.run_in_executor(None, _run)
    for chunk in chunk_message(output):
        await ctx.reply(chunk)


@bot.command(name='cal')
async def cmd_cal(ctx: commands.Context, period: str = 'today'):
    """Show calendar. Usage: !cal or !cal week"""
    async with ctx.typing():
        def _run():
            try:
                from eos_ai.gws_connector import GWSConnector
                gws = GWSConnector()
                if period == 'week':
                    events = gws.get_week_events() if hasattr(gws, 'get_week_events') else gws.get_today_events()
                    label  = "This Week"
                else:
                    events = gws.get_today_events()
                    label  = "Today"

                if not events:
                    return f'📅 **Calendar {label}:** Clear'
                lines = [f'📅 **Calendar — {label}**']
                for e in events[:10]:
                    title = e.get('title', '') or e.get('summary', '')
                    start = e.get('start', '')
                    if isinstance(start, dict):
                        start = start.get('dateTime', '') or start.get('date', '')
                    if start and 'T' in str(start):
                        start = str(start).split('T')[1][:5]
                    lines.append(f'  {start} — {title}')
                return '\n'.join(lines)
            except Exception as e:
                return f'Calendar error: {e}'
        loop   = asyncio.get_event_loop()
        output = await loop.run_in_executor(None, _run)
    await ctx.reply(output)


@bot.command(name='block')
async def cmd_block(ctx: commands.Context, *, time_range: str = ''):
    """Block focus time on calendar. Usage: !block 2pm-4pm deep work"""
    if not time_range:
        await ctx.reply('Usage: `!block 2pm-4pm deep work`')
        return
    await ctx.reply(
        f'📅 Focus block noted: **{time_range}**\n'
        f'Calendar blocking via GWS coming in next build.'
    )


@bot.command(name='waiting')
async def cmd_waiting(ctx: commands.Context):
    """Show what\'s in the Waiting On folder."""
    async with ctx.typing():
        def _run():
            try:
                from eos_ai.email_gps import EmailGPS
                gps       = EmailGPS(_ctx_eos)
                processed = gps.process_inbox(limit=30)
                waiting   = gps.get_waiting_on(processed)
                if not waiting:
                    return '⏳ **Waiting On:** Nothing currently waiting on a reply.'
                lines = [f'⏳ **Waiting On Reply** ({len(waiting)}):']
                for e in waiting:
                    lines.append(
                        f'  • {e.from_name or e.from_address}: {e.subject[:50]}'
                    )
                return '\n'.join(lines)
            except Exception as e:
                return f'Waiting On error: {e}'
        loop   = asyncio.get_event_loop()
        output = await loop.run_in_executor(None, _run)
    await ctx.reply(output)


@bot.command(name='help')
async def cmd_help(ctx: commands.Context):
    """Show available commands."""
    lines = [
        f'**{AI_NAME} — Discord Commands**',
        '',
        'Just type naturally in any channel — I route automatically.',
        '',
        '**EA Commands (DEX Email + Calendar)**',
        '`!sync` — run daily sync meeting now',
        '`!inbox` — Email GPS status',
        '`!draft` — drafts awaiting your approval',
        '`!cal` — today\'s calendar',
        '`!cal week` — this week\'s calendar',
        '`!block <time> <label>` — block focus time',
        '`!waiting` — what\'s in Waiting On folder',
        '',
        '**EOS Commands**',
        '`!brief` — morning brief',
        '`!report profile` — EOS learning report from docs',
        '`!report pulse` — run world pulse scan',
        '`!status` — system health check',
        '`!approve <id>` — approve a pending action',
        '`!join` — connect to your voice channel',
        '`!leave` — disconnect from voice',
        '`!say <text>` — speak text aloud in voice channel',
        '',
        '**Voice**',
        'Drop a `.wav`/`.mp3`/`.ogg` in any channel while connected',
        '→ Whisper transcribes → smart routing (Qwen local or Claude) → speaks back',
        '',
        '**Channels**',
        '`#general` — freeform conversation',
        '`#morning-brief` — daily brief (auto-posted at 6am)',
        '`#strategy` — strategic questions',
        '`#outreach` — DM alerts and pipeline',
        '`#content` — content creation',
        '`#decisions` — decision evaluation',
        '`#wins` — win announcements',
    ]
    await ctx.reply('\n'.join(lines))


# ─── Webhook helpers (called by orchestrator and dm_monitor) ──────────────────

async def post_to_channel(channel_name: str, content: str) -> bool:
    """Post content to a named channel by ID. Returns True if sent."""
    channel_id = CHANNEL_IDS.get(channel_name)
    if not channel_id:
        print(f'[Discord] No ID set for channel \'{channel_name}\' — skipping post')
        return False
    channel = bot.get_channel(channel_id)
    if not channel:
        print(f'[Discord] Channel {channel_id} not found in cache')
        return False
    for chunk in chunk_message(content):
        await channel.send(chunk)
    return True


async def post_morning_brief(brief: str) -> None:
    await post_to_channel('morning-brief', brief)


async def post_outreach_alert(alert: str) -> None:
    await post_to_channel('outreach', f'📩 {alert}')


async def post_win(win: str) -> None:
    await post_to_channel('wins', f'🏆 {win}')


# ─── Entry point ──────────────────────────────────────────────────────────────

if __name__ == '__main__':
    token = os.getenv('DISCORD_BOT_TOKEN')
    if not token:
        print('[Discord] DISCORD_BOT_TOKEN not set in .env — exiting')
        sys.exit(1)

    print(f'[Discord] Starting {AI_NAME} Discord bot...')
    bot.run(token, reconnect=True)
    # No in-process restart loop — py-cord closes the event loop on exit
    # and it cannot be reused. Docker restart: on-failure handles restarts
    # at the process level, giving each restart a fresh event loop.
