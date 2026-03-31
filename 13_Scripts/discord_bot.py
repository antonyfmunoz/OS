"""
EntrepreneurOS Discord Bot — DEX conversational layer.

Auto-joins founder's voice channel. Routes text through EOS gateway.
Smart routing: simple → local Qwen (free) → Claude via EOS.
AI name is user-configurable via BIS or AI_NAME env var.

Channel map (create these in your server):
  🧠 EOS:
    #general           — freeform conversation with DEX
    #morning-brief     — daily brief (auto-posted at 6am)
    #decisions         — decisions queue
    #wins              — closed deals and wins
    #agent-activity    — EOS agent log
  ⚡ Empyrean Creative:
    #empyrean-strategy — strategy
    #empyrean-pipeline — sales pipeline
    #empyrean-outreach — outreach tracking
  🏢 Lyfe Institute:
    #lyfe-strategy     — strategy
    #lyfe-pipeline     — Initiate Arena pipeline
    #lyfe-outreach     — Instagram DM tracking
  👤 Personal Brand:
    #brand-strategy    — brand strategy
    #content-ideas     — content ideas and calendar

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
from zoneinfo import ZoneInfo


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

# ─── Pending captures (venture disambiguation) ───────────────────────────────
# When a task/idea is ambiguous, we store it here and ask the founder which venture.
# channel_id -> {'text': str, 'type': str}
_pending_captures: dict[str, dict] = {}

# ─── Pending events (calendar conflict confirmation) ─────────────────────────
# When a conflict is detected, we store the parsed event here for confirmation.
# channel_id -> parsed event dict
_pending_events: dict[str, dict] = {}

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
CHANNEL_IDS: dict[str, int] = {
    'morning-brief':      1485765524766982234,
    'general':            1486289444830056540,
    'decisions':          1485765720775200808,
    'wins':               1485765745312010260,
    'agent-activity':     1486267275857235999,
    'empyrean-strategy':  1486267278239731823,
    'empyrean-pipeline':  1486267279028129863,
    'empyrean-outreach':  1486267280311586896,
    'lyfe-strategy':      1486267281901092976,
    'lyfe-pipeline':      1486267283373293568,
    'lyfe-outreach':      1486267284681920546,
    'brand-strategy':     1486267286309441566,
    'content-ideas':      1486267286913417278,
}

# Channel name → intent routing hint
CHANNEL_MAP: dict[str, str | None] = {
    'morning-brief':      'BRIEF',
    'general':            None,
    'decisions':          'DECISION',
    'wins':               None,
    'agent-activity':     None,
    'empyrean-strategy':  'STRATEGY',
    'empyrean-pipeline':  'OUTREACH',
    'empyrean-outreach':  'OUTREACH',
    'lyfe-strategy':      'STRATEGY',
    'lyfe-pipeline':      'OUTREACH',
    'lyfe-outreach':      'OUTREACH',
    'brand-strategy':     'STRATEGY',
    'content-ideas':      'CONTENT',
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
        # Only trigger the full brief dump if explicitly requested
        # Otherwise route through cognitive loop — soul doc governs response
        explicit_brief_triggers = [
            'morning brief', 'give me the brief', 'brief me',
            'run the brief', 'daily brief', 'show brief',
            'what\'s the brief', 'pull the brief',
        ]
        if any(trigger in text.lower() for trigger in explicit_brief_triggers):
            return {'type': 'brief', 'prompt': text, 'username': username}
        # Casual or ambiguous — let the cognitive loop handle it
        return {
            'type': 'agent_task',
            'prompt': text,
            'username': username,
            'venture_id': 'lyfe_institute',
            'task_type': 'ANALYZE',
        }

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


def _detect_pipeline_update(text: str) -> tuple[str, str] | None:
    """
    Detect natural language pipeline stage updates.
    Returns (stage, lead_hint) or None if not a pipeline update.

    Examples:
      "just closed that lead" → ("Won", "")
      "he ghosted" → ("Lost", "")
      "closed alex" → ("Won", "alex")
      "that lead booked a call" → ("Booked", "")
    """
    text_lower = text.lower()

    won_signals = [
        "just closed", "closed the deal", "closed them", "they signed",
        "they paid", "just won", "deal closed", "sale closed", "they bought",
        "just sold", "sold them", "closed a deal", "closed a sale",
    ]
    lost_signals = [
        "ghosted", "not interested", "lost that", "dead lead", "he left",
        "she left", "they left", "no response", "went cold", "lost them",
        "fell off", "dropped off", "unqualified",
    ]
    booked_signals = [
        "booked a call", "scheduled a call", "just booked", "call booked",
        "set a call", "locked in a call",
    ]

    stage = None
    for s in won_signals:
        if s in text_lower:
            stage = "Won"
            break
    # Bare "closed <Name>" pattern — word boundary check
    if not stage:
        import re as _re
        if _re.search(r'\bclosed\s+[A-Z][a-z]+', text):
            stage = "Won"

    if not stage:
        for s in lost_signals:
            if s in text_lower:
                stage = "Lost"
                break
    if not stage:
        for s in booked_signals:
            if s in text_lower:
                stage = "Booked"
                break

    if not stage:
        return None

    # Try to extract a lead name hint — @username or capitalized word after keyword
    import re
    username_match = re.search(r'@(\w+)', text)
    lead_hint = username_match.group(1) if username_match else ""

    if not lead_hint:
        name_match = re.search(
            r'(?:closed|lost|booked|sold|won)\s+([A-Z][a-z]+)', text
        )
        lead_hint = name_match.group(1) if name_match else ""

    return (stage, lead_hint)


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

    # Person recognition — inject context if a known person is mentioned
    try:
        import re as _re
        _names = _re.findall(r'\b[A-Z][a-z]+ [A-Z][a-z]+\b', text)
        if _names:
            from eos_ai.person_recognition import recognize_person
            for _name in _names[:2]:
                _rec = recognize_person(name=_name)
                if _rec.get('known') and _rec.get('confidence') == 'high':
                    print(f'[Discord] Known person mentioned: {_name}')
                    req['known_person'] = _name
                    req['person_context'] = _rec.get('context', '')
                    break
    except Exception:
        pass  # non-blocking

    # Cloning loop — detect when text answers an open DEX question
    try:
        from eos_ai.context import load_context_from_env
        from eos_ai.db import get_conn
        import json as _cljson
        _cl_ctx = load_context_from_env()

        with get_conn(_cl_ctx.org_id) as _cl_cur:
            _cl_cur.execute("""
                SELECT id, payload_json FROM events
                WHERE org_id = %s
                AND event_type = 'dex_question'
                AND (payload_json->>'answered' IS NULL
                     OR payload_json->>'answered' != 'true')
                AND created_at >= NOW() - INTERVAL '48 hours'
                ORDER BY created_at DESC
                LIMIT 1
            """, (str(_cl_ctx.org_id),))
            _open_q = _cl_cur.fetchone()

        if _open_q:
            _q_payload = _open_q['payload_json']
            if isinstance(_q_payload, str):
                _q_payload = _cljson.loads(_q_payload)
            _question = _q_payload.get('question', '')

            from eos_ai.model_router import get_router as _cl_get_router, TaskType as _cl_TT
            _cl_router = _cl_get_router()
            _cl_model = _cl_router.route(_cl_TT.FAST_RESPONSE)
            _cl_check = _cl_router.call(_cl_model, f"""Does this message answer this question?
Question: {_question}
Message: {text}
Return JSON: {{"answers": true, "answer_summary": "brief summary"}}""").strip()

            if '```' in _cl_check:
                _cl_check = _cl_check.split('```')[1].replace('json', '').strip()
            _cl_data = _cljson.loads(_cl_check)

            if _cl_data.get('answers'):
                _cl_now = datetime.now(ZoneInfo('America/Los_Angeles')).isoformat()
                with get_conn(_cl_ctx.org_id) as _cl_cur2:
                    _cl_cur2.execute("""
                        UPDATE events
                        SET payload_json = payload_json || %s::jsonb
                        WHERE id = %s
                    """, (
                        _cljson.dumps({
                            'answered': 'true',
                            'answer': _cl_data.get('answer_summary', ''),
                            'answered_at': _cl_now,
                        }),
                        _open_q['id'],
                    ))

                with get_conn(_cl_ctx.org_id) as _cl_cur3:
                    _cl_cur3.execute('''
                        INSERT INTO events
                        (org_id, event_type, payload_json, handled_by)
                        VALUES (%s, %s, %s, %s)
                    ''', (
                        str(_cl_ctx.org_id),
                        'dex_learning',
                        _cljson.dumps({
                            'question': _question,
                            'answer': _cl_data.get('answer_summary', ''),
                            'raw_answer': text,
                            'learned_at': _cl_now,
                        }),
                        'dex_cloning_loop',
                    ))
    except Exception:
        pass  # Non-blocking

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

    # ── Pending capture resolution (1/2/3 venture reply) ────────────────────
    _channel_id = str(message.channel.id)
    if _channel_id in _pending_captures and text.strip() in ('1', '2', '3', '1️⃣', '2️⃣', '3️⃣'):
        _pending = _pending_captures.pop(_channel_id)
        _venture_map = {'1': 'lyfe_institute', '2': 'empyrean_creative', '3': 'personal_brand'}
        _venture_id = _venture_map.get(text.strip().replace('\ufe0f\u20e3', ''), 'lyfe_institute')
        try:
            from eos_ai.founder_capture import capture
            capture(_pending['text'], venture_id=_venture_id)
            _icon = '💡' if _pending['type'] == 'idea' else '✅'
            await message.channel.send(f"{_icon} Added to your list.")
        except Exception:
            pass
        return

    # ── Pipeline update detection ─────────────────────────────────────────────
    pipeline_update = _detect_pipeline_update(text)
    if pipeline_update:
        stage, lead_hint = pipeline_update
        try:
            import sys as _sys; _sys.path.insert(0, '/opt/OS/13_Scripts')
            from calendly_webhook import update_notion_lead_stage
            success = update_notion_lead_stage(
                name=lead_hint,
                email='',
                new_stage=stage,
            )
            if success:
                await message.channel.send(
                    f"Pipeline updated — {lead_hint or 'lead'} moved to **{stage}**."
                )
            else:
                await message.channel.send(
                    f"Couldn't find that lead in Notion. "
                    f"Try mentioning their @username."
                )
        except Exception as e:
            await message.channel.send(f"Pipeline update failed: {e}")
        return

    # ── Founder capture — detect tasks/ideas, write to Your list + Notion ────
    try:
        from eos_ai.founder_capture import should_capture, capture
        _should, _ctype = should_capture(text)
        if _should:
            _text_lower = text.lower()
            if any(w in _text_lower for w in ['empyrean', 'b2b', 'ai infrastructure', 'entrepreneuros', 'saas']):
                _venture_id = 'empyrean_creative'
            elif any(w in _text_lower for w in ['brand', 'twitch', 'content', 'vigilante', 'personal brand']):
                _venture_id = 'personal_brand'
            elif any(w in _text_lower for w in ['lyfe', 'initiate', 'arena', 'coaching', 'instagram dm', 'men 18']):
                _venture_id = 'lyfe_institute'
            else:
                # Ambiguous — ask before capturing
                _channel_id = str(message.channel.id)
                await message.channel.send(
                    f"{'💡' if _ctype == 'idea' else '✅'} Got it. Which venture is this for?\n"
                    f"1️⃣ Lyfe Institute  2️⃣ Empyrean Creative  3️⃣ Personal Brand"
                )
                _pending_captures[_channel_id] = {'text': text, 'type': _ctype}
                return

            _capture_result = capture(text, venture_id=_venture_id)
            if _capture_result.get('captured'):
                _icon = '💡' if _ctype == 'idea' else '✅'
                await message.channel.send(f"{_icon} Added to your list.")
    except Exception:
        pass  # Never let capture break the main flow

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

    # ── !followup — draft a follow-up for a WAITING_ON email ────────────────
    if text.startswith('!followup'):
        email_id = text[9:].strip()
        try:
            from eos_ai.model_router import get_router, TaskType
            router = get_router()
            model = router.route(TaskType.FAST_RESPONSE)
            draft = router.call(
                model,
                f'Draft a brief, professional follow-up email '
                f'for email ID {email_id}. '
                f'Use Antony Munoz voice — direct, warm, short. '
                f'Subject: Following up. '
                f'Body: one sentence checking in on the status.',
            )
            await message.channel.send(
                f'📧 Follow-up draft:\n```\n{draft[:500]}\n```\n'
                f'Use `!approve` to send.'
            )
        except Exception as e:
            await message.channel.send(f'❌ Error: {e}')
        return

    # ── !confirm_event — create a calendar event after conflict warning ───────
    if text.lower() == '!confirm_event':
        _ch_id = str(message.channel.id)
        if _ch_id in _pending_events:
            _ev_data = _pending_events.pop(_ch_id)
            try:
                from eos_ai.gws_connector import GWSConnector
                _gws_conf = GWSConnector()
                _event = _gws_conf.create_calendar_event(
                    title=_ev_data.get('title', 'Meeting'),
                    start_iso=_ev_data.get('start_iso'),
                    duration_minutes=_ev_data.get('duration_minutes', 60),
                    attendee_email=_ev_data.get('attendee_email'),
                    description=_ev_data.get('description', ''),
                )
                if _event:
                    await message.channel.send(
                        f"✅ Created: **{_event['title']}**\n"
                        f"🕐 {_event.get('start', '')}\n"
                        f"🔗 {_event.get('meet_link', '')}"
                    )
                else:
                    await message.channel.send('❌ Failed to create event.')
            except Exception as e:
                await message.channel.send(f'❌ Error: {e}')
        else:
            await message.channel.send('No pending event to confirm.')
        return

    # ── !audit — show DEX action trail ───────────────────────────────────────
    if text.startswith('!audit'):
        _parts = text.split()
        _days = int(_parts[1]) if len(_parts) > 1 and _parts[1].isdigit() else 1
        try:
            from eos_ai.context import load_context_from_env
            from eos_ai.db import get_conn
            import json as _ajson
            _actx = load_context_from_env()
            with get_conn(_actx.org_id) as cur:
                cur.execute(
                    '''
                    SELECT event_type, payload_json, created_at
                    FROM events
                    WHERE org_id = %s
                    AND created_at >= NOW() - INTERVAL '%s days'
                    AND event_type IN (
                        'decision', 'dex_task', 'meeting_scheduled',
                        'pipeline_entry', 'email_classified',
                        'approval_requested', 'approval_granted'
                    )
                    ORDER BY created_at DESC
                    LIMIT 20
                    ''',
                    (str(_actx.org_id), _days),
                )
                _rows = cur.fetchall()

            if not _rows:
                await message.channel.send(
                    f'📋 No audit events in the last {_days} day(s).'
                )
                return

            _alines = [f'📋 **DEX Audit Log — last {_days} day(s):**']
            for _r in _rows:
                _payload = _r['payload_json']
                if isinstance(_payload, str):
                    _payload = _ajson.loads(_payload)
                _etype = _r['event_type']
                _created = str(_r['created_at'])[:16]
                if _etype == 'decision':
                    _desc = _payload.get('description', 'Decision')[:60]
                    _alines.append(f'🎯 [{_created}] Decision: {_desc}')
                elif _etype == 'dex_task':
                    _task = _payload.get('task', 'Task')[:60]
                    _alines.append(f'✅ [{_created}] Task captured: {_task}')
                elif _etype == 'meeting_scheduled':
                    _person = _payload.get('person', 'Unknown')
                    _alines.append(f'📅 [{_created}] Meeting: {_person}')
                elif _etype == 'pipeline_entry':
                    _name = _payload.get('name', 'Lead')[:40]
                    _alines.append(f'📊 [{_created}] Pipeline: {_name}')
                else:
                    _alines.append(f'📝 [{_created}] {_etype}')

            _full_audit = '\n'.join(_alines)
            for i in range(0, len(_full_audit), 1900):
                await message.channel.send(_full_audit[i:i+1900])
        except Exception as e:
            await message.channel.send(f'❌ Audit failed: {e}')
        return

    # ── Calendar write — detect scheduling intent and handle directly ─────────
    _cal_keywords = [
        'schedule', 'book', 'set up a call', 'set up a meeting',
        'reschedule', 'cancel the', 'move the', 'block time',
        'add to calendar', 'create an event',
    ]
    if any(kw in text.lower() for kw in _cal_keywords):
        try:
            from eos_ai.gws_connector import GWSConnector
            _gws = GWSConnector()
            import anthropic as _ant
            _client = _ant.Anthropic()
            _parse_resp = _client.messages.create(
                model='claude-haiku-4-5-20251001',
                max_tokens=200,
                messages=[{
                    'role': 'user',
                    'content': (
                        'Extract calendar event details from this message. '
                        f'Today is {datetime.now(ZoneInfo("America/Los_Angeles")).strftime("%A %B %d %Y")}. '
                        'Return JSON only: {"action": "create|update|delete|list", "title": "", '
                        '"start_iso": "ISO datetime in UTC", "duration_minutes": 60, '
                        '"attendee_email": null, "description": "", "event_id": null}\n'
                        f'Message: "{text}"'
                    ),
                }],
            )
            import json as _json
            _parsed = _json.loads(_parse_resp.content[0].text.strip())
            _action = _parsed.get('action', 'create')

            if _action == 'create':
                # Check for conflicts before creating
                if _parsed.get('start_iso'):
                    try:
                        _conflicts = _gws.check_conflicts(
                            start_iso=_parsed['start_iso'],
                            duration_minutes=_parsed.get('duration_minutes', 60),
                        )
                        if _conflicts:
                            _conflict_names = ', '.join(
                                c['title'] for c in _conflicts[:2]
                            )
                            await message.channel.send(
                                f'⚠️ **Conflict detected:** {_conflict_names}\n'
                                f'Still create the event? Reply `!confirm_event` '
                                f'or adjust the time.'
                            )
                            _pending_events[str(message.channel.id)] = _parsed
                            return
                    except Exception:
                        pass  # Non-blocking

                _event = _gws.create_calendar_event(
                    title=_parsed.get('title', text[:50]),
                    start_iso=_parsed.get('start_iso'),
                    duration_minutes=_parsed.get('duration_minutes', 60),
                    attendee_email=_parsed.get('attendee_email'),
                    description=_parsed.get('description', ''),
                )
                if _event:
                    _cal_reply = (
                        f"📅 Scheduled: **{_event['title']}**\n"
                        f"🕐 {_event.get('start', '')}\n"
                        f"🔗 {_event.get('meet_link', 'No Meet link')}"
                    )
                    await message.channel.send(_cal_reply)
                    return
            elif _action == 'list':
                _events = _gws.list_calendar_events(days=14, query=_parsed.get('title'))
                if _events:
                    _lines = ['📅 **Upcoming events:**']
                    for _e in _events[:5]:
                        _start = _e.get('start', {})
                        _dt = _start.get('dateTime', _start.get('date', ''))
                        _lines.append(f"• {_e.get('summary', 'Untitled')} — {_dt}")
                    await message.channel.send('\n'.join(_lines))
                else:
                    await message.channel.send('📅 No upcoming events found.')
                return
        except Exception as _cal_err:
            print(f'[Discord] Calendar handler failed: {_cal_err}')
            # Fall through to gateway

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
    """Send main response, then footer as a separate follow-up if present."""
    divider = '─' * 33  # thin dash divider used by cognitive loop footer
    if divider in output:
        parts = output.split(divider, 1)
        main   = parts[0].rstrip() + f'\n\n— {AI_NAME}'
        footer = divider + parts[1].strip()
        for chunk in chunk_message(main):
            await message.reply(chunk)
        for chunk in chunk_message(footer):
            await message.channel.send(chunk)
    else:
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
    """Portfolio health check — scans all ventures and shows binding constraint."""
    async with ctx.typing():
        loop = asyncio.get_event_loop()

        def _portfolio_scan():
            try:
                from eos_ai.portfolio_agent import PortfolioAgent
                pa       = PortfolioAgent(_ctx_eos)
                ventures = pa.scan_all_ventures()
                return pa.generate_portfolio_brief(ventures)
            except Exception as e:
                return f'Portfolio scan failed: {e}'

        output = await loop.run_in_executor(None, _portfolio_scan)

    for chunk in chunk_message(output or 'Status retrieved.'):
        await ctx.reply(chunk)


@bot.command(name='portfolio')
async def cmd_portfolio(ctx: commands.Context):
    """Trigger the weekly portfolio brief on demand."""
    import subprocess
    subprocess.Popen(['python3', '/opt/OS/scripts/portfolio_brief.py'])
    await ctx.reply('📊 Portfolio brief generating...')


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


@bot.command(name='outcome')
async def cmd_outcome(ctx: commands.Context, *, args: str = ''):
    """Capture post-meeting outcome. Usage: !outcome <event_id> [what decided] | [open loops]"""
    if not args:
        await ctx.reply('Usage: `!outcome <event_id> [outcomes] | [open loops]`')
        return
    try:
        parts = args.strip().split('|')
        left_tokens = parts[0].strip().split()
        event_id = left_tokens[0] if left_tokens else ''
        outcomes_text = ' '.join(left_tokens[1:]) if len(left_tokens) > 1 else ''
        open_loops_text = parts[1].strip() if len(parts) > 1 else ''

        from eos_ai.meetings import update_meeting_outcome
        ok = update_meeting_outcome(
            calendly_event_id=event_id,
            status='Completed',
            outcomes=outcomes_text,
            open_loops=open_loops_text,
        )
        if ok:
            await ctx.reply('✅ Outcome captured and synced to Notion.')
        else:
            await ctx.reply('⚠️ Captured locally but Notion sync failed — check NOTION_MEETINGS_ID.')
    except Exception as e:
        await ctx.reply(f'❌ Failed: {e}')


@bot.command(name='eod')
async def cmd_eod(ctx: commands.Context):
    """Trigger EOD sync manually."""
    import subprocess
    subprocess.Popen(['python3', '/opt/OS/scripts/eod_sync.py'])
    await ctx.reply('📊 EOD sync running...')


@bot.command(name='accept')
async def cmd_accept(ctx: commands.Context, event_id: str = ''):
    """Accept a pending calendar invite. Usage: !accept <event_id>"""
    if not event_id:
        await ctx.reply('Usage: `!accept <event_id>`')
        return
    try:
        from scripts.calendar_invite_handler import respond_to_invite
        ok = respond_to_invite(event_id, 'accepted')
        await ctx.reply('✅ Accepted.' if ok else '❌ Failed to accept.')
    except Exception as e:
        await ctx.reply(f'❌ Error: {e}')


@bot.command(name='decline')
async def cmd_decline(ctx: commands.Context, event_id: str = ''):
    """Decline a pending calendar invite. Usage: !decline <event_id>"""
    if not event_id:
        await ctx.reply('Usage: `!decline <event_id>`')
        return
    try:
        from scripts.calendar_invite_handler import respond_to_invite
        ok = respond_to_invite(event_id, 'declined')
        await ctx.reply('❌ Declined.' if ok else '❌ Failed to decline.')
    except Exception as e:
        await ctx.reply(f'❌ Error: {e}')


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


@bot.command(name='approve_followup')
async def cmd_approve_followup(ctx: commands.Context):
    """Approve the most recent pending follow-up email draft."""
    try:
        from eos_ai.context import load_context_from_env
        from eos_ai.db import get_conn
        import json as _json
        _ctx = load_context_from_env()
        with get_conn(_ctx.org_id) as cur:
            cur.execute('''
                SELECT id, payload_json FROM events
                WHERE org_id = %s
                AND event_type = 'email_draft_pending'
                AND payload_json->>\'status\' = \'pending_approval\'
                ORDER BY created_at DESC
                LIMIT 1
            ''', (str(_ctx.org_id),))
            row = cur.fetchone()
        if row:
            payload = row['payload_json']
            if isinstance(payload, str):
                payload = _json.loads(payload)
            draft = payload.get('draft', '')
            with get_conn(_ctx.org_id) as cur:
                cur.execute("""
                    UPDATE events
                    SET payload_json = payload_json || '{"status": "approved"}'::jsonb
                    WHERE id = %s
                """, (row['id'],))
            draft_type = payload.get('type', 'email')
            await ctx.reply(
                f'✅ {draft_type} email approved and queued for sending.\n'
                f'Preview:\n```\n{draft[:400]}\n```'
            )
        else:
            await ctx.reply('No pending follow-up email found.')
    except Exception as e:
        await ctx.reply(f'❌ Error: {e}')


@bot.command(name='nurture')
async def cmd_nurture(ctx: commands.Context, *, name: str = ''):
    """Draft a warm check-in message for a contact. Usage: !nurture [name]"""
    if not name:
        await ctx.reply('Usage: `!nurture [contact name]`')
        return
    try:
        from eos_ai.model_router import get_router, TaskType
        from eos_ai.person_recognition import build_intelligence_profile
        _router = get_router()
        _model = _router.route(TaskType.FAST_RESPONSE)
        profile = build_intelligence_profile(name=name)
        notes = getattr(profile, 'notes', None) or 'No prior context available'
        last_contact = getattr(profile, 'last_contact', None) or 'unknown'
        draft = _router.call(_model, f"""Draft a warm check-in message for {name}.

Context: {notes}
Last contact: {last_contact}

Antony's voice — casual, genuine, no agenda.
2-3 sentences max. Not salesy.

Subject: [subject]
[body]
[Antony]""").strip()
        await ctx.reply(
            f'📧 Check-in draft for {name}:\n```\n{draft[:500]}\n```\n'
            f'`!approve_followup` to send.'
        )
    except Exception as e:
        await ctx.reply(f'❌ Error: {e}')


@bot.command(name='expenses')
async def cmd_expenses(ctx: commands.Context):
    """Show month-to-date expenses. Usage: !expenses"""
    try:
        from eos_ai.expense_tracker import get_monthly_summary
        summary = get_monthly_summary()
        if not summary.get('total'):
            await ctx.reply('💳 No expenses logged this month.')
            return
        lines = [f'💳 **Expenses — Month to date: ${summary["total"]:,.2f}**']
        for cat, amt in sorted(
            summary['by_category'].items(),
            key=lambda x: x[1], reverse=True
        ):
            lines.append(f'• {cat}: ${amt:,.2f}')
        lines.append(f'\n_{summary["count"]} transactions_')
        await ctx.reply('\n'.join(lines))
    except Exception as e:
        await ctx.reply(f'❌ Error: {e}')


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
            import json
            from pathlib import Path

            PENDING_DIR = Path('/opt/OS/15_Orchestrator/approvals/pending')

            drafts = []
            for f in sorted(PENDING_DIR.glob('*.json')):
                try:
                    data = json.loads(f.read_text())
                    req  = data.get('request', {})
                    if req.get('type') == 'email_draft':
                        drafts.append({
                            'approval_id': data.get('approval_id'),
                            'to':          req.get('to', ''),
                            'subject':     req.get('subject', ''),
                            'body':        req.get('body', ''),
                            'queued_at':   data.get('queued_at', ''),
                        })
                except Exception:
                    continue

            if not drafts:
                return '📬 No email drafts pending approval.'

            lines = [f'📝 **{len(drafts)} Email Draft(s) Pending Approval**\n']
            for d in drafts[:5]:
                lines.append(
                    f'**ID:** `{d["approval_id"]}`\n'
                    f'**To:** {d["to"]}\n'
                    f'**Subject:** {d["subject"]}\n'
                    f'**Body:**\n{d["body"][:400]}\n'
                    f'→ `!approve {d["approval_id"]}` to send\n'
                )
            return '\n'.join(lines)

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


@bot.command(name='focus')
async def cmd_focus(ctx: commands.Context, hours: str = '2'):
    """Block focus time on calendar now. Usage: !focus [hours]"""
    async with ctx.typing():
        def _run():
            try:
                h = int(hours) if hours.isdigit() else 2
                from eos_ai.gws_connector import GWSConnector
                from datetime import datetime, timezone, timedelta
                gws = GWSConnector()
                now = datetime.now(timezone.utc)
                event = gws.create_calendar_event(
                    title='🔒 Deep Work — Do Not Disturb',
                    start_iso=now.isoformat(),
                    duration_minutes=h * 60,
                    description='Focus block created by DEX. No meetings.',
                )
                if event:
                    end_time = (now + timedelta(hours=h)).strftime('%I:%M %p')
                    return (
                        f'🔒 Focus block set for **{h}h**. '
                        f'Calendar blocked until **{end_time} UTC**.'
                    )
                return '❌ Failed to create focus block — GWS calendar error.'
            except Exception as e:
                return f'❌ Error: {e}'
        loop   = asyncio.get_event_loop()
        output = await loop.run_in_executor(None, _run)
    await ctx.reply(output)


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


@bot.command(name='verify-inbox')
async def cmd_verify_inbox(ctx: commands.Context):
    """Spot-check Gmail GPS labels — sample 5 emails per folder."""
    async with ctx.typing():
        def _run():
            try:
                from eos_ai.email_gps import EmailGPS
                gps = EmailGPS(_ctx_eos)
                return gps.verify_existing_labels(sample=5)
            except Exception as e:
                return f'Verify inbox error: {e}'
        loop   = asyncio.get_event_loop()
        output = await loop.run_in_executor(None, _run)
    for chunk in chunk_message(output):
        await ctx.reply(chunk)


@bot.command(name='folder-update')
async def cmd_folder_update(ctx: commands.Context, folder: str = '', *, instruction: str = ''):
    """Update a GPS folder definition. Usage: !folder-update <folder> <instruction>"""
    if not folder or not instruction:
        await ctx.reply(
            'Usage: `!folder-update <folder> <instruction>`\n'
            'Example: `!folder-update Receipts-Financials Apple marketing emails should never go here`\n'
            'Folders: Antony, To Respond, Review, Responded, Waiting On, Receipts-Financials, Newsletters'
        )
        return

    async with ctx.typing():
        def _run():
            try:
                from eos_ai.email_gps import EmailGPS
                gps = EmailGPS(_ctx_eos)
                new_purpose = gps.update_folder_purpose(folder, instruction)
                if new_purpose:
                    return (
                        f'✅ **Updated "{folder}"**\n\n'
                        f'New rule: {new_purpose}\n\n'
                        f'All future classifications use this definition.'
                    )
                return f'❌ Could not update "{folder}". Check the folder name and try again.'
            except Exception as e:
                return f'Folder update error: {e}'
        loop   = asyncio.get_event_loop()
        output = await loop.run_in_executor(None, _run)
    await ctx.reply(output)


@bot.command(name='delegated')
async def cmd_delegated(ctx: commands.Context):
    """Show overdue delegations."""
    def _run():
        try:
            from eos_ai.delegation_tracker import get_overdue_delegations
            overdue = get_overdue_delegations()
            if not overdue:
                return '✅ No overdue delegations.'
            lines = [f'📋 **Overdue delegations ({len(overdue)}):**']
            for d in overdue[:8]:
                task = d.get('task', '')[:60]
                to = d.get('delegated_to', 'Unknown')
                due = d.get('due_at', '')[:10]
                lines.append(f'• {task} → {to} (due {due})')
            return '\n'.join(lines)
        except Exception as e:
            return f'❌ Error: {e}'
    loop = asyncio.get_event_loop()
    output = await loop.run_in_executor(None, _run)
    await ctx.reply(output)


@bot.command(name='subscriptions')
async def cmd_subscriptions(ctx: commands.Context):
    """Show subscription registry and upcoming renewals."""
    def _run():
        try:
            from eos_ai.subscription_tracker import (
                get_subscriptions,
                get_upcoming_renewals,
                get_monthly_subscription_total,
            )
            subs = get_subscriptions()
            renewals = get_upcoming_renewals(days=14)
            monthly = get_monthly_subscription_total()

            if not subs:
                return (
                    '📋 No subscriptions tracked yet.\n'
                    'Add one: `!add_sub [vendor] [amount] [monthly/annual] [YYYY-MM-DD]`'
                )

            lines = [f'📋 **Subscriptions — ${monthly:,.2f}/month**']
            for s in subs[:10]:
                lines.append(
                    f'• {s["vendor"]} — ${s["amount"]} '
                    f'({s.get("billing_cycle","monthly")}) — '
                    f'renews {s.get("next_renewal","?")[:10]}'
                )
            if renewals:
                lines.append('\n⚠️ **Renewing soon:**')
                for r in renewals[:3]:
                    lines.append(
                        f'• {r["vendor"]} in {r["days_until"]}d — ${r["amount"]}'
                    )
            return '\n'.join(lines)
        except Exception as e:
            return f'❌ Error: {e}'
    loop = asyncio.get_event_loop()
    output = await loop.run_in_executor(None, _run)
    await ctx.reply(output)


@bot.command(name='add_sub')
async def cmd_add_sub(ctx: commands.Context, *, args: str = ''):
    """Add a subscription. Usage: !add_sub [vendor] [amount] [monthly/annual] [YYYY-MM-DD]"""
    parts = args.strip().split()
    if len(parts) < 4:
        await ctx.reply('Usage: `!add_sub [vendor] [amount] [monthly/annual] [YYYY-MM-DD]`')
        return

    def _run():
        try:
            from eos_ai.subscription_tracker import add_subscription
            vendor = parts[0]
            amount = float(parts[1])
            cycle = parts[2]
            renewal = parts[3]
            ok = add_subscription(
                vendor=vendor,
                amount=amount,
                billing_cycle=cycle,
                next_renewal=renewal,
            )
            if ok:
                return f'✅ Added: {vendor} — ${amount}/{cycle} — renews {renewal}'
            return '❌ Failed to add subscription.'
        except Exception as e:
            return f'❌ Error: {e}'
    loop = asyncio.get_event_loop()
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
        '`!focus [hours]` — block calendar now for deep work (default 2h)',
        '`!block <time> <label>` — block focus time',
        '`!waiting` — what\'s in Waiting On folder',
        '`!delegated` — overdue delegations',
        '`!subscriptions` — subscription registry + upcoming renewals',
        '`!add_sub [vendor] [amount] [cycle] [date]` — track a subscription',
        '`!verify-inbox` — spot-check GPS label accuracy',
        '`!folder-update <folder> <instruction>` — update GPS folder rule',
        '',
        '**EOS Commands**',
        '`!brief` — morning brief',
        '`!report profile` — EOS learning report from docs',
        '`!report pulse` — run world pulse scan',
        '`!status` — system health check',
        '`!approve <id>` — approve a pending action',
        '`!approve_followup` — approve most recent follow-up email draft',
        '`!nurture [name]` — draft a warm check-in for a contact',
        '`!expenses` — month-to-date expense summary',
        '`!join` — connect to your voice channel',
        '`!leave` — disconnect from voice',
        '`!say <text>` — speak text aloud in voice channel',
        '',
        '**Voice**',
        'Drop a `.wav`/`.mp3`/`.ogg` in any channel while connected',
        '→ Whisper transcribes → smart routing (Qwen local or Claude) → speaks back',
        '',
        '**Channels**',
        '`#general` — freeform conversation with DEX',
        '`#morning-brief` — daily brief (auto-posted at 6am)',
        '`#decisions` — decision evaluation',
        '`#wins` — win announcements',
        '`#agent-activity` — EOS agent log',
        '`#empyrean-strategy/pipeline/outreach` — Empyrean Creative',
        '`#lyfe-strategy/pipeline/outreach` — Lyfe Institute',
        '`#brand-strategy` / `#content-ideas` — Personal Brand',
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
