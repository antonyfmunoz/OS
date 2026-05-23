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
import json as _json_mod
import logging
import os

logger = logging.getLogger(__name__)
import re
import sys
import tempfile
import traceback
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo


# ─── Asyncio-level voice task exception suppressor ────────────────────────────
# on_error only catches event handler exceptions — Task exceptions (like the
# _MissingSentinel crash from poll_voice_ws) bypass it entirely. This handler
# intercepts them at the event loop level before they kill the process.


def _handle_task_exception(loop, context):
    exception = context.get("exception")
    if exception:
        msg = str(exception)
        if "_MissingSentinel" in msg or "poll_event" in msg or "poll_voice_ws" in msg:
            return  # silently ignore voice WS errors
    loop.default_exception_handler(context)


from substrate.observability.error_recorder import record_error as _record_error


import discord
from discord.ext import commands
import wave
import time
from discord.sinks import Sink as AudioSink

# ─── Path bootstrap ───────────────────────────────────────────────────────────

_SCRIPT_DIR = Path(__file__).parent
_REPO_ROOT = _SCRIPT_DIR.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

from dotenv import load_dotenv

load_dotenv(_SCRIPT_DIR / ".env")
load_dotenv(_REPO_ROOT / "runtime" / ".env")

# ─── EOS imports ──────────────────────────────────────────────────────────────

# Pin top-level runtime before control_plane.runtime shadows the name
import importlib.util as _ilu

_rt_spec = _ilu.find_spec("runtime", [str(_REPO_ROOT)])
if _rt_spec and "runtime" not in sys.modules:
    _rt_mod = _ilu.module_from_spec(_rt_spec)
    sys.modules["runtime"] = _rt_mod
    if _rt_spec.submodule_search_locations:
        _rt_mod.__path__ = list(_rt_spec.submodule_search_locations)
    if _rt_spec.loader:
        _rt_spec.loader.exec_module(_rt_mod)

from substrate.control_plane.runtime.gateway import EntrepreneurOSGateway
from substrate.state.context.context import load_context_from_env
from substrate.understanding.knowledge.knowledge_integrator import KnowledgeIntegrator
from substrate.execution.voice.voice_engine import VoiceEngine
from substrate.state.business.business_instance import get_ai_name
from transports.discord.discord_utils import chunk_message, post_to_webhook
from substrate.execution.bridge.session_discord_bridge import send_reply as _send_reply
from substrate.execution.bridge.discord_text_transport import (
    maybe_mirror_discord_text_message as _maybe_pseudo_live_text,
)

# Graceful import for substrate modules that may not exist yet
try:
    from substrate.execution.bridge.message_framing import get_inbound_buffer
except ImportError:
    get_inbound_buffer = None

from substrate.execution.bridge.event_spine import (
    EventType as _FrameEventType,
    create_event as _frame_create_event,
)

try:
    from substrate.execution.bridge.event_store import get_event_store as _frame_get_event_store
except ImportError:
    _frame_get_event_store = None

try:
    from substrate.execution.bridge.interaction_archive import (
        archive_inbound as _archive_inbound,
        Interface as _ArchiveInterface,
    )
except ImportError:
    _archive_inbound = None
    _ArchiveInterface = None

# Install the router-backed voice-session responder at import time so that
# every Discord pseudo-live text ingress (which flows through
# inject_transcript → VoiceSessionRuntime.submit_utterance → global responder)
# routes through runtime.model_router.call_with_fallback instead of the
# substrate's default "[role] heard: ..." stub. Idempotent; safe to call
# multiple times. The substrate architecture is preserved — we are only
# replacing the pluggable responder hook the substrate already exposes.
try:
    from substrate.execution.bridge.voice_eos_responder import (
        install_default_eos_voice_responder as _install_voice_router_responder,
        is_eos_voice_responder_installed as _is_voice_router_responder_installed,
    )

    if not _is_voice_router_responder_installed():
        _install_voice_router_responder()
        print(
            "[Discord] voice-session responder = router-backed "
            "(runtime.voice_eos_responder → model_router.call_with_fallback)",
            flush=True,
        )
    else:
        print(
            "[Discord] voice-session responder already router-backed",
            flush=True,
        )
except Exception as _voice_responder_install_err:  # noqa: BLE001
    _record_error("voice_responder_install", _voice_responder_install_err)
    print(
        f"[Discord] WARNING: failed to install router-backed voice responder: "
        f"{_voice_responder_install_err} — Discord pseudo-live will echo stub",
        flush=True,
    )

# ─── Handler imports ─────────────────────────────────────────────────────────

from transports.presence.handlers.intent_handler import run_gateway as _handler_run_gateway
from transports.presence.handlers.intent_handler import CHANNEL_MAP as _HANDLER_CHANNEL_MAP
from transports.presence.handlers.pipeline_handler import handle_pipeline_update
from transports.presence.handlers.cc_command_handler import try_inline_commands

# Extracted modules
import services.discord_message_handlers as _handlers
import services.discord_bot_commands as _bot_commands
try:
    from transports.presence.handlers.substrate_command_handler import (
        handle_substrate_command,
        is_substrate_command,
        log_startup as _substrate_log_startup,
    )
except ImportError:
    async def handle_substrate_command(_msg, _text): pass
    is_substrate_command = lambda _content: False
    _substrate_log_startup = lambda: None

# ─── Initialise ───────────────────────────────────────────────────────────────

_ctx_eos = load_context_from_env()
_gateway = EntrepreneurOSGateway()  # singleton — no ctx arg
_ki = KnowledgeIntegrator(_ctx_eos)
_ve = VoiceEngine()

from substrate.control_plane.onboarding.onboarding_engine import OnboardingEngine as _OnboardingEngine

_onboarding = _OnboardingEngine(_ctx_eos)

# Resolve AI name — refreshed on_ready so renames take effect on reconnect
AI_NAME = get_ai_name(_ctx_eos)

# Default venture for requests that don't specify one
_DEFAULT_VENTURE_ID = _ctx_eos.active_venture_id or os.getenv(
    "DEFAULT_VENTURE_ID", "lyfe_institute"
)

# Founder Discord user ID — bot auto-joins founder's voice channel
FOUNDER_ID = int(os.getenv("FOUNDER_DISCORD_ID", "0"))

# Channel sessions — one persistent session_id per channel
# Preserves conversation continuity within each channel across messages
_channel_sessions: dict[str, str] = {}

# ─── Silence-detecting voice sink ─────────────────────────────────────────────


class SilenceDetectingSink(AudioSink):
    def __init__(self, on_utterance, silence_threshold: float = 1.5):
        super().__init__()
        self.on_utterance = on_utterance
        self.silence_threshold = silence_threshold
        self._buffers = {}
        self._last_audio = {}
        self._running = True

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
            now = time.time()
            to_flush = [
                uid
                for uid, t in list(self._last_audio.items())
                if now - t >= self.silence_threshold and self._buffers.get(uid)
            ]
            for uid in to_flush:
                frames = self._buffers.pop(uid, [])
                self._last_audio.pop(uid, None)
                if frames:
                    audio_path = tempfile.mktemp(suffix=".wav")
                    with wave.open(audio_path, "wb") as wf:
                        wf.setnchannels(2)  # Discord: stereo
                        wf.setsampwidth(2)  # 16-bit samples
                        wf.setframerate(48000)  # 48 kHz
                        wf.writeframes(b"".join(frames))
                    asyncio.create_task(self.on_utterance(uid, audio_path))


def transcribe_with_groq(audio_path: str) -> str:
    try:
        from groq import Groq as GroqClient

        client = GroqClient(api_key=os.getenv("GROQ_API_KEY"))
        with open(audio_path, "rb") as f:
            result = client.audio.transcriptions.create(
                model="whisper-large-v3-turbo",
                file=f,
                language="en",
            )
        text = result.text.strip()
        print(f"[Groq STT] Transcribed: {text[:50]}")
        return text
    except Exception as e:
        _record_error("groq_stt", e, {"audio_path": audio_path})
        print(f"[Groq STT] Error: {e}")
        return ""


# ─── Channel IDs ──────────────────────────────────────────────────────────────
CHANNEL_IDS: dict[str, int] = {
    "morning-brief": 1485765524766982234,
    "general": 1486289444830056540,
    "decisions": 1485765720775200808,
    "wins": 1485765745312010260,
    "agent-activity": 1486267275857235999,
    "empyrean-strategy": 1486267278239731823,
    "empyrean-pipeline": 1486267279028129863,
    "empyrean-outreach": 1486267280311586896,
    "lyfe-strategy": 1486267281901092976,
    "lyfe-pipeline": 1486267283373293568,
    "lyfe-outreach": 1486267284681920546,
    "brand-strategy": 1486267286309441566,
    "content-ideas": 1486267286913417278,
}

# Channel name → intent routing hint
CHANNEL_MAP: dict[str, str | None] = {
    "morning-brief": "BRIEF",
    "general": None,
    "decisions": "DECISION",
    "wins": None,
    "agent-activity": None,
    "empyrean-strategy": "STRATEGY",
    "empyrean-pipeline": "OUTREACH",
    "empyrean-outreach": "OUTREACH",
    "lyfe-strategy": "STRATEGY",
    "lyfe-pipeline": "OUTREACH",
    "lyfe-outreach": "OUTREACH",
    "brand-strategy": "STRATEGY",
    "content-ideas": "CONTENT",
}

# ─── Day ritual helpers ───────────────────────────────────────────────────────

_OPEN_DAY_PHRASES = [
    r"start my day",
    r"open day",
    r"open my day",
    r"open session",
]

_CLOSE_DAY_PHRASES = [
    r"close day",
    r"end my day",
    r"close my day",
    r"close session",
    r"eod",
]

_OPEN_EXACT = [r"good morning"]
_CLOSE_EXACT = [r"good night"]

_OPEN_PATTERN = re.compile(
    r"^\s*(?:" + "|".join(_OPEN_DAY_PHRASES) + r")\s*[.!]?\s*$",
    re.IGNORECASE,
)
_CLOSE_PATTERN = re.compile(
    r"^\s*(?:" + "|".join(_CLOSE_DAY_PHRASES) + r")\s*[.!]?\s*$",
    re.IGNORECASE,
)
_OPEN_EXACT_PATTERN = re.compile(
    r"^\s*(?:" + "|".join(_OPEN_EXACT) + r")\s*[.!]?\s*$",
    re.IGNORECASE,
)
_CLOSE_EXACT_PATTERN = re.compile(
    r"^\s*(?:" + "|".join(_CLOSE_EXACT) + r")\s*[.!]?\s*$",
    re.IGNORECASE,
)


def _detect_day_command(text: str) -> str | None:
    if text.startswith("!"):
        return None
    if _OPEN_PATTERN.match(text):
        return "open_day"
    if _CLOSE_PATTERN.match(text):
        return "close_day"
    if _OPEN_EXACT_PATTERN.match(text):
        return "open_day"
    if _CLOSE_EXACT_PATTERN.match(text):
        return "close_day"
    return None


def _run_day_command(
    cmd: str,
    *,
    workspace: str | None = None,
    node_preference: str | None = None,
    discord_channel_id: str | None = None,
    continuity_text: str | None = None,
) -> dict:
    try:
        from substrate.execution.bridge.day_workflows import close_day, open_day

        if cmd == "open_day":
            return open_day(
                workspace=workspace,
                node_preference=node_preference,
                discord_channel_id=discord_channel_id,
            )
        elif cmd == "close_day":
            return close_day(
                continuity_notes=continuity_text,
                discord_channel_id=discord_channel_id,
            )
        else:
            return {"status": "error", "detail": f"unknown command: {cmd}"}
    except Exception as e:
        _record_error("day_ritual", e, {"command": cmd})
        print(f"[DayRitual] error in {cmd}: {e}")
        return {"status": "error", "detail": str(e)}


def _format_day_result(result: dict) -> str:
    status = result.get("status", "error")

    if status == "already_open":
        ws = result.get("active_workspace", "unknown")
        mode = result.get("day_mode", "unknown")
        opened = result.get("opened_at", "unknown")
        return f"Day is already open.\nWorkspace: {ws} | Mode: {mode} | Opened: {opened}"

    if status == "not_open":
        return "No day is currently open. Use `start my day` or `!openday` first."

    if status == "error":
        return f"Day ritual error: {result.get('detail', 'unknown')}"

    # open_day ok
    if "briefing" in result:
        b = result["briefing"]
        mode = result.get("day_mode", "unknown")
        ws = result.get("active_workspace", "unknown")
        left_off = b.get("where_we_left_off") or "Fresh start."
        priorities = b.get("unfinished_priorities") or []
        overnight = b.get("overnight_tasks") or []
        first_action = b.get("recommended_first_action") or "Check your priorities."
        resume = b.get("resume_context")
        lines = [
            f"**Day Open** — {mode}",
            f"Workspace: {ws} | Node: {result.get('node_preference', 'auto')}",
            "",
            f"**Where we left off:**\n{left_off}",
            "",
        ]
        if priorities:
            lines.append("**Unfinished priorities:**")
            for p in priorities:
                lines.append(f"- {p}")
        else:
            lines.append("**Unfinished priorities:**\nNone.")
        lines.append("")
        if overnight:
            lines.append("**Overnight tasks:**")
            for t in overnight:
                lines.append(f"- {t}")
        else:
            lines.append("**Overnight tasks:**\nNone.")
        lines.append("")
        lines.append(f"**Recommended first action:**\n{first_action}")
        if resume:
            lines.append(f"\n**Resume context:**\n{resume}")
        warning = result.get("ritual_warning")
        if warning:
            lines.append(f"\n_Ritual warning: {warning}_")
        return "\n".join(lines)

    # close_day ok
    if "summary" in result:
        s = result["summary"]
        completed = s.get("completed_today") or []
        unresolved = s.get("unresolved") or []
        overnight = s.get("overnight_tasks") or []
        notes = s.get("continuity_notes")
        mode = s.get("day_mode", "inactive")
        lines = [f"**Day Closed** — {mode}", ""]
        if completed:
            lines.append("**Completed today:**")
            for c in completed:
                lines.append(f"- {c}")
        else:
            lines.append("**Completed today:**\nNothing logged.")
        lines.append("")
        if unresolved:
            lines.append("**Unresolved:**")
            for u in unresolved:
                lines.append(f"- {u}")
        else:
            lines.append("**Unresolved:**\nAll clear.")
        lines.append("")
        if overnight:
            lines.append("**Overnight tasks:**")
            for t in overnight:
                lines.append(f"- {t}")
        else:
            lines.append("**Overnight tasks:**\nNone.")
        if notes:
            lines.append(f"\n**Continuity notes:**\n{notes}")
        warning = result.get("ritual_warning")
        if warning:
            lines.append(f"\n_Ritual warning: {warning}_")
        return "\n".join(lines)

    return f"Day ritual completed with status: {status}"


async def _send_day_response(invoking_channel, formatted_text: str) -> None:
    await _send_reply(invoking_channel, formatted_text)
    # Best-effort mirror to #morning-brief
    try:
        _mb_id = CHANNEL_IDS.get("morning-brief")
        if _mb_id and str(invoking_channel.id) != str(_mb_id):
            _mb_chan = bot.get_channel(_mb_id)
            if _mb_chan:
                await _send_reply(_mb_chan, formatted_text)
    except Exception as _mirror_exc:
        _record_error("day_mirror", _mirror_exc)
        print(f"[DayRitual] mirror to #morning-brief failed: {_mirror_exc}")


# ─── Active meeting state ─────────────────────────────────────────────────────

_active_meeting: dict = {
    "type": None,  # 'sales_call', 'strategy_session', etc.
    "lead_name": None,
    "started_at": None,
    "notes": [],  # raw utterances captured
    "key_points": [],  # AI-extracted insights
}

# ─── Intent → gateway request type mapping ───────────────────────────────────

_INTENT_TO_TEAM: dict[str, tuple[str | None, str | None]] = {
    "OUTREACH": ("sales", "outreach_writer"),
    "RESEARCH": ("research", "market_analyst"),
    "CONTENT": ("content", "content_writer"),
    "STRATEGY": (None, None),
    "DECISION": (None, None),
    "TASK": (None, None),
    "INTEL": ("research", "signal_analyst"),
    "PORTFOLIO": (None, None),
    "JOURNAL": (None, None),
    "MODEL": (None, None),
    "UNKNOWN": (None, None),
}

# ─── Bot setup ────────────────────────────────────────────────────────────────

intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True
intents.presences = True
intents.members = True

bot = commands.Bot(
    command_prefix="!",
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
    if "_MissingSentinel" in err or "poll_voice_ws" in err:
        print("[Voice] WS error caught — ignoring")
        return
    print(f"[Bot] Error in {event}: {err}")


# ─── Gateway routing ──────────────────────────────────────────────────────────


def _build_request(text: str, intent: str, channel_name: str, username: str) -> dict:
    """Build a valid EntrepreneurOSGateway request dict from classified intent."""
    if intent == "BRIEF":
        # Only trigger the full brief dump if explicitly requested
        # Otherwise route through cognitive loop — soul doc governs response
        explicit_brief_triggers = [
            "morning brief",
            "give me the brief",
            "brief me",
            "run the brief",
            "daily brief",
            "show brief",
            "what's the brief",
            "pull the brief",
        ]
        if any(trigger in text.lower() for trigger in explicit_brief_triggers):
            return {"type": "brief", "prompt": text, "username": username}
        # Casual or ambiguous — let the cognitive loop handle it
        return {
            "type": "agent_task",
            "prompt": text,
            "username": username,
            "venture_id": _DEFAULT_VENTURE_ID,
            "task_type": "ANALYZE",
        }

    if intent == "PORTFOLIO":
        return {"type": "status", "prompt": text, "username": username}

    team, sub_agent = _INTENT_TO_TEAM.get(intent, (None, None))
    req: dict = {
        "type": "agent_task",
        "prompt": text,
        "username": username,
        "venture_id": _DEFAULT_VENTURE_ID,
    }
    if team:
        req["team"] = team
        req["sub_agent"] = sub_agent
    else:
        task_map = {
            "STRATEGY": "ANALYZE",
            "DECISION": "ANALYZE",
            "TASK": "GENERATE",
            "JOURNAL": "SUMMARIZE",
            "MODEL": "ANALYZE",
            "UNKNOWN": "ANALYZE",
            "OUTREACH": "GENERATE",
            "CONTENT": "GENERATE",
            "INTEL": "ANALYZE",
            "PORTFOLIO": "ANALYZE",
        }
        req["task_type"] = task_map.get(intent, "ANALYZE")
        req["sub_agent"] = "executive_assistant"
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
        "just closed",
        "closed the deal",
        "closed them",
        "they signed",
        "they paid",
        "just won",
        "deal closed",
        "sale closed",
        "they bought",
        "just sold",
        "sold them",
        "closed a deal",
        "closed a sale",
    ]
    lost_signals = [
        "ghosted",
        "not interested",
        "lost that",
        "dead lead",
        "he left",
        "she left",
        "they left",
        "no response",
        "went cold",
        "lost them",
        "fell off",
        "dropped off",
        "unqualified",
    ]
    booked_signals = [
        "booked a call",
        "scheduled a call",
        "just booked",
        "call booked",
        "set a call",
        "locked in a call",
    ]

    stage = None
    for s in won_signals:
        if s in text_lower:
            stage = "Won"
            break
    # Bare "closed <Name>" pattern — word boundary check
    if not stage:
        import re as _re

        if _re.search(r"\bclosed\s+[A-Z][a-z]+", text):
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

    username_match = re.search(r"@(\w+)", text)
    lead_hint = username_match.group(1) if username_match else ""

    if not lead_hint:
        name_match = re.search(r"(?:closed|lost|booked|sold|won)\s+([A-Z][a-z]+)", text)
        lead_hint = name_match.group(1) if name_match else ""

    return (stage, lead_hint)


def _run_gateway(
    text: str,
    channel_name: str,
    username: str,
    guild_id: str | None = None,
    channel_id: str | None = None,
    memory_only: bool = False,
) -> str:
    """
    Classify intent, build request, call gateway, return output text.
    Runs synchronously — called from asyncio executor to avoid blocking.
    Delegates to handlers.intent_handler.run_gateway.

    memory_only: when True, skip LLM call and only write to memory.
    Used by bypass paths that already sent a response to the user.
    """
    return _handler_run_gateway(
        text=text,
        channel_name=channel_name,
        username=username,
        gateway=_gateway,
        ki=_ki,
        channel_sessions=_channel_sessions,
        default_venture_id=_DEFAULT_VENTURE_ID,
        guild_id=guild_id,
        channel_id=channel_id,
        memory_only=memory_only,
    )


# ─── Meeting mode ─────────────────────────────────────────────────────────────


async def handle_meeting_voice(
    text: str,
    meeting_type: str,
    channel,
) -> str:
    """Handle voice input during a meeting — surfaces context, detects signals."""
    _active_meeting["notes"].append(text)
    text_lower = text.lower()

    if any(
        w in text_lower
        for w in [
            "objection",
            "they said",
            "pushback",
            "concern",
            "but what about",
        ]
    ):
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            lambda: __import__("runtime.agent_teams", fromlist=["run_team_task"]).run_team_task(
                team="sales",
                sub_agent="objection_handler",
                prompt=f"Objection on call: {text}",
                venture_id=_DEFAULT_VENTURE_ID,
                ctx=_ctx_eos,
            ),
        )
        return result.get("output", "")

    elif any(
        w in text_lower
        for w in [
            "price",
            "cost",
            "how much",
            "what does it cost",
            "investment",
        ]
    ):
        return (
            "Initiate Arena: $750 one-time. "
            "Frame as investment not cost. "
            "Ask: what is staying stuck worth to you?"
        )

    elif any(
        w in text_lower
        for w in [
            "close",
            "ready",
            "lets do it",
            "let's do it",
            "sign up",
            "where do i pay",
        ]
    ):
        if channel:
            await _send_reply(
                channel,
                f"💰 **{AI_NAME}: Buying signal detected.**\n"
                f"Send the Whop link now.\n\n— {AI_NAME}",
            )
        return "Buying signal. Send the link."

    elif any(
        w in text_lower
        for w in [
            "end meeting",
            "wrap up",
            "that is all",
            "thanks everyone",
        ]
    ):
        await end_active_meeting(channel)
        return "Meeting ended. Running post-meeting automation."

    else:
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            lambda: _gateway.handle(
                {
                    "type": "agent_task",
                    "prompt": text,
                    "venture_id": _DEFAULT_VENTURE_ID,
                }
            ),
        )
        return result.get("output", "")


async def start_meeting_mode(
    meeting_type: str,
    lead_name: str = "",
    channel=None,
) -> str:
    """Activate meeting mode — loads pre-meeting brief, announces to channel."""
    from datetime import datetime, timezone

    _active_meeting["type"] = meeting_type
    _active_meeting["lead_name"] = lead_name
    _active_meeting["started_at"] = datetime.now(timezone.utc).isoformat()
    _active_meeting["notes"] = []
    _active_meeting["key_points"] = []
    try:
        from substrate.execution.bridge.storage import get_storage

        get_storage().put("active_meeting", dict(_active_meeting))
    except Exception as _ms_err:
        _record_error("meeting_storage_save", _ms_err)

    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(
        None,
        lambda: __import__("runtime.agent_teams", fromlist=["run_team_task"]).run_team_task(
            team="sales",
            sub_agent="closer",
            prompt=(
                f"Pre-meeting brief for {meeting_type} with "
                f"{lead_name or 'lead'}. What do I need to know?"
            ),
            venture_id=_DEFAULT_VENTURE_ID,
            ctx=_ctx_eos,
        ),
    )
    brief = result.get("output", "")

    if channel:
        await _send_reply(
            channel,
            f"📋 **{AI_NAME}: Meeting started — {meeting_type}**\n\n{brief}\n\n— {AI_NAME}",
        )

    # speak brief (fire-and-forget)
    asyncio.create_task(
        asyncio.get_event_loop().run_in_executor(
            None, _ve.speak, f"Meeting mode active. {brief[:200]}"
        )
    )

    return brief


async def end_active_meeting(channel=None) -> None:
    """End meeting mode and generate post-meeting summary."""
    if not _active_meeting["type"]:
        return

    notes = "\n".join(_active_meeting["notes"][-20:])
    meeting_type = _active_meeting["type"]
    lead_name = _active_meeting["lead_name"] or "lead"

    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(
        None,
        lambda: _gateway.handle(
            {
                "type": "agent_task",
                "prompt": (
                    f"Summarize this {meeting_type} with {lead_name}. "
                    f"Key points, outcome, next steps:\n\n{notes}"
                ),
                "venture_id": _DEFAULT_VENTURE_ID,
            }
        ),
    )
    summary = result.get("output", "")

    if channel:
        await _send_reply(
            channel,
            f"📝 **{AI_NAME}: Meeting summary**\n\n{summary}\n\n— {AI_NAME}",
        )

    # clear state
    _active_meeting["type"] = None
    _active_meeting["lead_name"] = None
    _active_meeting["notes"] = []
    _active_meeting["key_points"] = []
    try:
        from substrate.execution.bridge.storage import get_storage

        get_storage().put("active_meeting", dict(_active_meeting))
    except Exception as _mc_err:
        _record_error("meeting_storage_clear", _mc_err)


# ─── Startup ──────────────────────────────────────────────────────────────────


async def _warmup_cc_sdk():
    """Pre-load cc_sdk session on startup to reduce cold start latency.

    Skips warmup entirely when system is under high pressure — the subprocess
    spawn would worsen the load spike during recovery restarts.
    """
    await asyncio.sleep(10)
    try:
        from substrate.state.work.work_state import _measure_pressure, Pressure

        p = _measure_pressure()
        if p in (Pressure.HIGH, Pressure.CRITICAL):
            logger.info("[Startup] cc_sdk warmup skipped — pressure=%s", p.value)
            return

        from adapters.model_adapters.cc_sdk import query_cc_sync

        result = query_cc_sync(
            prompt="Ready.",
            task_type="fast_response",
            agent_id="dex",
            max_budget_usd=0.01,
        )
        if result:
            logger.info(
                "[Startup] cc_sdk warm — session %s... %dms",
                result.session_id[:8],
                result.latency_ms,
            )
        else:
            logger.warning("[Startup] cc_sdk warm failed")
    except Exception as e:
        _record_error("cc_sdk_warmup", e)
        logger.warning("[Startup] cc_sdk warm error: %s", e)


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
                print("[Voice] Cleaned up stale voice client on ready")
            except Exception as _vc_err:
                _record_error("voice_cleanup_ready", _vc_err)

    # Short grace period: Discord replays voice state events during RESUME
    # right around on_ready. Wait for that window to pass before allowing
    # our handler to act on voice events.
    await asyncio.sleep(2)
    _bot_ready = True

    # ── Restore persisted session state from SubstrateStorage ──────────
    try:
        from substrate.execution.bridge.storage import get_storage

        _store = get_storage()
        _restored = 0
        for _key in _store.all_keys():
            if _key.startswith("session:"):
                _chan = _key[len("session:") :]
                _channel_sessions[_chan] = _store.get(_key)
                _restored += 1
        if _restored:
            print(f"[Discord] Restored {_restored} channel session(s) from storage")
        _meeting_state = _store.get("active_meeting")
        if _meeting_state and _meeting_state.get("type"):
            _active_meeting["type"] = _meeting_state["type"]
            _active_meeting["lead_name"] = _meeting_state.get("lead_name")
            _active_meeting["started_at"] = _meeting_state.get("started_at")
            _active_meeting["notes"] = _meeting_state.get("notes", [])
            _active_meeting["key_points"] = _meeting_state.get("key_points", [])
            print(f"[Discord] Restored active meeting: {_meeting_state['type']}")
    except Exception as _restore_err:
        _record_error("session_restore", _restore_err)
        print(f"[Discord] Session restore failed (non-blocking): {_restore_err}")

    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.watching,
            name=f"over you — {AI_NAME}",
        )
    )
    print(f"[Discord] {AI_NAME} online as {bot.user} (id={bot.user.id})")
    print(f"[Discord] Serving {len(bot.guilds)} server(s)")

    # Start ambient refresh (same as Telegram bot)
    try:
        from substrate.control_plane.orchestrator.orchestrator import start_ambient_refresh_loop

        start_ambient_refresh_loop(_ctx_eos)
        print("[Discord] Ambient refresh started")
    except Exception as e:
        _record_error("ambient_refresh", e)
        print(f"[Discord] Ambient refresh skipped: {e}")

    _substrate_log_startup()

    # Set up EOS Discord structure (idempotent — only creates missing channels)
    for guild in bot.guilds:
        bot.loop.create_task(_setup_server_structure(guild))

    # Warm up cc_sdk session (pre-load DEX agent, reduce cold start)
    asyncio.create_task(_warmup_cc_sdk())

    # ── Start CC reply webhook receiver ──────────────────────────────────
    # Receives POSTs from the CC Stop hook with assistant replies and
    # dispatches them to the correct Discord channel.
    try:
        from cc_webhook_receiver import start_webhook_server

        await start_webhook_server(bot, AI_NAME)
    except Exception as e:
        _record_error("cc_webhook_receiver", e)
        print(f"[Discord] CC webhook receiver failed to start: {e}")

    # ── Wire up session watcher → Discord bridge ───────────────────────────
    # SessionWatcher polls tmux panes for mid-session pauses (plan mode,
    # permission requests, questions).  SessionDiscordBridge renders them
    # as interactive Discord messages with buttons.
    try:
        from substrate.execution.bridge.session_discord_bridge import get_bridge
        from substrate.execution.bridge.session_watcher import start_watcher

        bridge = get_bridge()
        bridge.set_bot(bot)

        start_watcher("vps", "dex_builder_main", on_event=bridge.on_watcher_event)
        start_watcher("vps", "dex_product_main", on_event=bridge.on_watcher_event)
        print("[Discord] Session watchers + Discord bridge started")
    except Exception as e:
        _record_error("session_watcher_bridge", e)
        print(f"[Discord] Session watcher/bridge setup failed: {e}")

    # ── Start Station Daemon (background heartbeat loop) ─────────────────
    try:
        from substrate.execution.bridge.station_daemon import start_station_daemon

        start_station_daemon()
        print("[Discord] Station daemon started")
    except Exception as e:
        _record_error("station_daemon", e)
        print(f"[Discord] Station daemon failed to start: {e}")


# ─── Auto-join voice ──────────────────────────────────────────────────────────


@bot.event
async def on_voice_state_update(
    member: discord.Member,
    before: discord.VoiceState,
    after: discord.VoiceState,
):
    # Only watch the founder, and only after the bot is fully ready
    if not _bot_ready or FOUNDER_ID == 0 or member.id != FOUNDER_ID:
        return

    # Get general text channel for announcements
    general = None
    general_id = CHANNEL_IDS.get("general")
    if general_id:
        general = bot.get_channel(general_id)
    if not general:
        general = discord.utils.get(member.guild.text_channels, name="general")

    # Founder JOINED a voice channel (before=None, after=Channel)
    if after.channel is not None and before.channel is None:
        # Capture channel reference at event time — after.channel may be None later
        target_channel = after.channel
        print(f"[Voice] Branch: FOUNDER JOINED {target_channel.name}")
        await asyncio.sleep(3)
        # Re-check: founder must still be in that channel after the sleep.
        # If they left during the 3s window the LEFT branch already fired but
        # found no voice_client — without this guard we'd connect anyway.
        if member not in target_channel.members:
            print("[Voice] Founder left during sleep — aborting connect")
            return
        if member.guild.voice_client:
            return  # already connected
        vc = None
        max_attempts = 2
        await asyncio.sleep(10)
        print("[Voice] Starting connect sequence")
        for attempt in range(max_attempts):
            try:
                # Verify founder is still in the target channel before each attempt
                founder_member = member.guild.get_member(FOUNDER_ID)
                if (
                    not founder_member
                    or not founder_member.voice
                    or founder_member.voice.channel != target_channel
                ):
                    print("[Voice] Founder no longer in target channel — aborting")
                    return
                if target_channel is None:
                    print("[Voice] Channel reference lost — aborting")
                    return

                # disconnect any lingering voice client before each attempt
                if member.guild.voice_client:
                    try:
                        await member.guild.voice_client.disconnect(force=True)
                        await asyncio.sleep(1)
                    except Exception as _vd1:
                        _record_error("voice_disconnect_pre_connect", _vd1)

                vc = await target_channel.connect(
                    timeout=15.0,
                    reconnect=False,  # we handle reconnects ourselves
                )
                print(f"[Voice] Connected on attempt {attempt + 1}")
                break  # success
            except discord.errors.ConnectionClosed as e:
                if "4006" in str(e) or "session" in str(e).lower():
                    wait = 5 if attempt == 0 else (attempt + 1) * 30
                    print(f"[Voice] 4006 on attempt {attempt + 1} — waiting {wait}s before retry")
                    # Force-disconnect any stale session before retry
                    if member.guild.voice_client:
                        try:
                            await member.guild.voice_client.disconnect(force=True)
                        except Exception as _vd2:
                            _record_error("voice_disconnect_4006_retry", _vd2)
                    await asyncio.sleep(wait)
                    continue
                print(f"[Voice] Connect closed: {e}")
                return
            except Exception as e:
                _record_error("voice_connect", e)
                print(f"[Voice] Connect failed: {e}")
                if "Already connected" in str(e):
                    if member.guild.voice_client:
                        try:
                            await member.guild.voice_client.disconnect(force=True)
                            await asyncio.sleep(2)
                        except Exception as _vd3:
                            _record_error("voice_disconnect_already_connected", _vd3)
                    continue
                return
        else:
            print("[Voice] Max connect attempts reached — aborting")
            return

        # verify WS initialized before starting the listen loop
        await asyncio.sleep(2)
        if not hasattr(vc, "ws") or vc.ws is discord.utils.MISSING:
            print("[Voice] WS not initialized — aborting")
            try:
                await vc.disconnect(force=True)
            except Exception as _vd4:
                _record_error("voice_disconnect_ws_missing", _vd4)
            return

        print(f"[Voice] WS ready: {type(vc.ws).__name__}")
        if general:
            await _send_reply(
                general,
                f"👁️ **{AI_NAME} Joined {target_channel.name} voice chat.**",
            )
        asyncio.create_task(_listen_loop(vc, general))

    # Founder LEFT voice channel (before=Channel, after=None)
    elif before.channel is not None and after.channel is None:
        print(f"[Voice] Branch: FOUNDER LEFT {before.channel.name}")
        if member.guild.voice_client:
            try:
                await member.guild.voice_client.disconnect()
            except Exception as _vd5:
                _record_error("voice_disconnect_founder_left", _vd5)
        if general:
            await _send_reply(
                general,
                f"👁️ **{AI_NAME} Disconnected from {before.channel.name} voice chat.**",
            )

    # Founder SWITCHED channels (both not None)
    elif (
        before.channel is not None
        and after.channel is not None
        and before.channel.id != after.channel.id
    ):
        print(f"[Voice] Branch: FOUNDER SWITCHED {before.channel.name} → {after.channel.name}")
        if member.guild.voice_client:
            try:
                await member.guild.voice_client.move_to(after.channel)
            except Exception as _vd6:
                _record_error("voice_move_founder_switched", _vd6)
        if general:
            await _send_reply(general, f"👁️ **{AI_NAME} followed you to {after.channel.name}.**")


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
    print("[Voice] *** LISTEN LOOP STARTED ***")
    print(f"[Voice] Channel: {vc.channel}")

    async def on_utterance(user_id: int, audio_path: str) -> None:
        try:
            loop = asyncio.get_event_loop()
            text = await loop.run_in_executor(None, transcribe_with_groq, audio_path)
            try:
                os.remove(audio_path)
            except Exception as _rm_err:
                _record_error("audio_temp_cleanup", _rm_err, {"path": audio_path})

            if not text or len(text.split()) < 2:
                return

            print(f"[Voice] Heard: {text}")

            # ── Bounded substrate mirror (opt-in, default OFF) ──────────────
            # When EOS_DISCORD_VOICE_TRANSPORT_ENABLED is truthy, mirror this
            # transcript through the bounded voice seam so it lands in
            # voice_session / audio_loop / SPEAK_TEXT alongside the existing
            # gateway routing. Never raises. Returns None when disabled.
            try:
                from substrate.execution.bridge.discord_voice_transport import (
                    maybe_mirror_discord_utterance,
                )

                _guild_id = (
                    str(getattr(getattr(vc, "channel", None), "guild", None).id)
                    if getattr(vc, "channel", None) is not None
                    and getattr(vc.channel, "guild", None) is not None
                    else None
                )
                _channel_id = (
                    str(vc.channel.id) if getattr(vc, "channel", None) is not None else None
                )
                # Pass `voice_client=vc` so that when
                # EOS_DISCORD_VOICE_PLAYBACK_ENABLED is also truthy, the
                # mirror hook can opportunistically attach the live VC and
                # play the EOS reply back into the channel. Default-off:
                # if either env var is unset, this is a transcript-only no-op.
                maybe_mirror_discord_utterance(
                    text,
                    user_id=user_id,
                    guild_id=_guild_id,
                    channel_id=_channel_id,
                    voice_client=vc,
                )
            except Exception as _mirror_err:  # noqa: BLE001
                _record_error("voice_substrate_mirror", _mirror_err)
                print(f"[Voice] substrate mirror skipped: {_mirror_err}")

            should_respond, classification = _ve.should_respond(text, 0.0)
            print(f"[Voice] [{classification}] respond={should_respond}")

            if not should_respond:
                return

            # ── Voice-first: play ack BEFORE LLM call (eliminates dead air) ──
            try:
                from substrate.execution.bridge.voice_first import (
                    needs_ack,
                    play_ack,
                    VOICE_SYSTEM_SUFFIX,
                )

                if needs_ack(text):
                    asyncio.create_task(play_ack(vc))
                _voice_prompt_suffix = VOICE_SYSTEM_SUFFIX
            except Exception as _vf_ack_err:
                _record_error("voice_first_ack", _vf_ack_err)
                _voice_prompt_suffix = ""

            context_summary = _ve.intelligent.get_context_summary()
            prompt = f"{context_summary}\n\nCurrent: {text}" if context_summary else text
            prompt += _voice_prompt_suffix

            # Auto-detect meeting context
            if not _active_meeting.get("type"):
                meeting_ctx = _ve.intelligent.detect_meeting_context(
                    text, list(_ve.intelligent.context_window)
                )
                if meeting_ctx and meeting_ctx["confidence"] > 0.6:
                    _active_meeting["type"] = meeting_ctx["type"]
                    if text_channel:
                        await _send_reply(
                            text_channel,
                            f"📋 **{AI_NAME}: {meeting_ctx['type']} detected.**\n"
                            f"Taking notes. I'll surface relevant context as needed.\n\n— {AI_NAME}",
                        )

            meeting_type = _active_meeting.get("type")

            if meeting_type:
                _active_meeting["notes"].append(text)
                response = await handle_meeting_voice(text, meeting_type, text_channel)
                if not response:
                    result = await loop.run_in_executor(
                        None,
                        lambda: _gateway.handle(
                            {
                                "type": "agent_task",
                                "prompt": prompt,
                                "sub_agent": "executive_assistant",
                                "venture_id": _DEFAULT_VENTURE_ID,
                            }
                        ),
                    )
                    response = result.get("output", "")
            elif _ve.is_simple_query(text) and _ve.is_running():
                response = await loop.run_in_executor(None, _ve.query_local, text)
                if not response:
                    result = await loop.run_in_executor(
                        None,
                        lambda: _gateway.handle(
                            {
                                "type": "agent_task",
                                "prompt": prompt,
                                "sub_agent": "executive_assistant",
                                "venture_id": _DEFAULT_VENTURE_ID,
                            }
                        ),
                    )
                    response = result.get("output", "")
            else:
                result = await loop.run_in_executor(
                    None,
                    lambda: _gateway.handle(
                        {
                            "type": "agent_task",
                            "prompt": prompt,
                            "sub_agent": "executive_assistant",
                            "venture_id": _DEFAULT_VENTURE_ID,
                        }
                    ),
                )
                response = result.get("output", "")

            if not response:
                return

            _ve.intelligent.add_to_context(text, classification, response)

            # ── Voice-first response path ─────────────────────────────
            # Speak FIRST, then post text as transcript/subtitle.
            try:
                from substrate.execution.bridge.voice_first import (
                    voice_first_respond,
                )

                user = bot.get_user(user_id)
                name = user.display_name if user else "You"
                vf_result = await voice_first_respond(
                    vc,
                    utterance=text,
                    response=response,
                    voice_engine=_ve,
                    text_channel=text_channel,
                    user_name=name,
                    ai_name=AI_NAME,
                    ack_already_played=True,
                )
                if vf_result.spoke:
                    print(
                        f"[Voice] voice-first: spoke={vf_result.spoke} ack={vf_result.ack_played}"
                    )
                elif vf_result.error:
                    print(f"[Voice] voice-first degraded: {vf_result.error}")
            except Exception as _vf_err:
                _record_error("voice_first_call", _vf_err)
                print(f"[Voice] voice-first import/call failed, falling back: {_vf_err}")
                # Fallback: original text-first path
                if text_channel:
                    user = bot.get_user(user_id)
                    name = user.display_name if user else "You"
                    msg = f"\U0001f3a4 **{name}:** {text}\n**{AI_NAME}:** {response}"
                    await _send_reply(text_channel, msg)
                audio_out = await loop.run_in_executor(None, _ve.speak, response[:300])
                if audio_out and os.path.exists(audio_out):
                    while vc.is_playing():
                        await asyncio.sleep(0.3)
                    if vc.is_connected():
                        vc.play(discord.FFmpegPCMAudio(audio_out))

            try:
                _ki.integrate(
                    content=(f"Voice [{classification}]:\nUser: {text}\n{AI_NAME}: {response}"),
                    source="discord_voice",
                    category="conversation",
                    metadata={
                        "classification": classification,
                        "meeting_type": _active_meeting.get("type"),
                    },
                )
            except Exception as e:
                _record_error("voice_ki_integrate", e)
                print(f"[Voice] KI integrate failed: {e}")

        except Exception as e:
            _record_error("voice_utterance", e)
            print(f"[Voice] Utterance error: {e}")
            import traceback

            traceback.print_exc()

    sink = SilenceDetectingSink(on_utterance=on_utterance, silence_threshold=1.5)

    try:
        vc.start_recording(sink, lambda *a: None, None)
        print("[Voice] Silence detection active")
    except Exception as e:
        _record_error("voice_start_recording", e)
        print(f"[Voice] Failed to start: {e}")
        import traceback

        traceback.print_exc()
        return

    asyncio.create_task(sink.monitor_silence(vc))

    if text_channel:
        await _send_reply(text_channel, f"👁️ **{AI_NAME} is listening.**")

    while vc.is_connected():
        await asyncio.sleep(1)

    print("[Voice] Disconnected — stopping")
    sink.cleanup()
    try:
        vc.stop_recording()
    except Exception as _sr_err:
        _record_error("voice_stop_recording", _sr_err)

    print("[Voice] Loop ended")


# ─── Response formatter ──────────────────────────────────────────────────────


async def _send_response(message: discord.Message, output: str) -> None:
    """Send response to Discord with full footer intact."""
    output = output.rstrip() + f"\n\n— {AI_NAME}"
    await _send_reply(message.channel, output)


# ─── Message dispatcher ─────────────────────────────────────────────────────



@bot.event
async def on_message(message: discord.Message):
    # ── Early returns ────────────────────────────────────────────────────
    if message.author == bot.user or message.author.bot:
        return

    # Wake idle system — a real user message is a work signal
    try:
        from substrate.state.work.work_state import record_signal, reset_idle_counter

        record_signal()
        reset_idle_counter()
    except Exception as _ws_err:
        _record_error("work_state_signal", _ws_err)

    # ── Attachment handling (audio / image) ──────────────────────────────
    if message.attachments:
        if await _handlers._handle_audio_attachment(message):
            return
        if await _handlers._handle_image_attachment(message):
            return

    # ── Extract text, early-exit on empty or #wins ──────────────────────
    text = message.content.strip()
    if not text:
        await bot.process_commands(message)
        return

    channel_name = message.channel.name if hasattr(message.channel, "name") else "dm"
    username = str(message.author)

    if channel_name == "wins":
        await bot.process_commands(message)
        return

    # ── Inbound buffer commands (/done, /buffer, accumulate) ────────────
    _ib = get_inbound_buffer() if get_inbound_buffer else None
    _uid = str(message.author.id)
    _cid_str = str(message.channel.id)

    if text.strip().lower() == "/done" and _ib is not None:
        handled, text = await _handlers._handle_buffer_done(
            message, text, channel_name, username, _ib, _uid, _cid_str,
        )
        if handled:
            return
        # Fall through to normal processing with combined text

    elif text.strip().lower() == "/buffer" and _ib is not None:
        await _handlers._handle_buffer_start(
            message, text, channel_name, username, _ib, _uid, _cid_str,
        )
        return

    elif _ib is not None and _ib.has_active(_uid, _cid_str):
        await _handlers._handle_buffer_accumulate(
            message, text, channel_name, username, _ib, _uid, _cid_str,
        )
        return

    # ── Day ritual intercept ────────────────────────────────────────────
    _day_cmd = _detect_day_command(text)
    if _day_cmd:
        await _handlers._handle_day_ritual(message, text, channel_name, username, _day_cmd)
        return

    # ── Active onboarding session ───────────────────────────────────────
    if await _handlers._handle_onboarding(message, text, channel_name, username):
        return

    # ── Archive single inbound verbatim ─────────────────────────────────
    try:
        _archive_inbound(
            text,
            interface=_ArchiveInterface.DISCORD.value,
            metadata={
                "type": "single",
                "user_id": _uid,
                "channel_id": _cid_str,
                "channel_name": channel_name,
            },
        )
    except Exception as _ar2_err:
        _record_error("archive_single", _ar2_err)

    # ── Substrate commands ──────────────────────────────────────────────
    if is_substrate_command(text):
        await handle_substrate_command(message, text)
        return

    # ── Orchestration ingress ───────────────────────────────────────────
    if await _handlers._handle_orchestration_ingress(
        message, text, channel_name, username, _uid, _cid_str,
    ):
        return

    # ── CC injection (dormant) ──────────────────────────────────────────
    if await _handlers._handle_cc_injection(message, text, channel_name, username):
        return

    # ── PseudoLive fallback ─────────────────────────────────────────────
    if await _handlers._handle_pseudolive(message, text, channel_name, username):
        return

    # ── Meeting mode triggers ───────────────────────────────────────────
    if await _handlers._handle_meeting_trigger(message, text, channel_name, username):
        return

    # ── Pending capture resolution (1/2/3 venture reply) ────────────────
    if await _handlers._handle_pending_capture(message, text, channel_name, username):
        return

    # ── Pipeline update detection ───────────────────────────────────────
    if await _handlers._handle_pipeline_update_check(message, text, channel_name, username):
        return

    # ── Founder capture (tasks/ideas) ───────────────────────────────────
    if await _handlers._handle_founder_capture(message, text, channel_name, username):
        return

    # ── Multi-part accumulation ─────────────────────────────────────────
    handled, text = await _handlers._handle_multipart(message, text, channel_name, username)
    if handled:
        return

    # ── Inline commands ─────────────────────────────────────────────────
    if await _handlers._handle_inline_commands(message, text, channel_name, username):
        return

    # ── Full EOS gateway dispatch (terminal) ────────────────────────────
    await _handlers._handle_gateway_dispatch(message, text, channel_name, username)


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
        print(f"[Discord] Created category: {name}")
        return cat

    async def ensure_channel(
        self,
        name: str,
        category_name: str | None = None,
        topic: str = "",
        channel_type: str = "text",
    ) -> discord.abc.GuildChannel | None:
        """Find or create a channel. Returns channel object."""
        if channel_type == "voice":
            existing = discord.utils.get(self.guild.voice_channels, name=name)
        else:
            existing = discord.utils.get(self.guild.text_channels, name=name)
        if existing:
            return existing

        category = None
        if category_name:
            category = await self.ensure_category(category_name)

        try:
            if channel_type == "voice":
                ch = await self.guild.create_voice_channel(name=name, category=category)
            else:
                ch = await self.guild.create_text_channel(name=name, topic=topic, category=category)
            print(f"[Discord] Created #{name}")
            return ch
        except discord.Forbidden:
            print(f"[Discord] Permission denied creating #{name}")
            return None
        except Exception as e:
            _record_error("ensure_channel", e)
            print(f"[Discord] Error creating #{name}: {e}")
            return None

    async def setup_eos_structure(self) -> list[str]:
        """Create full EOS Discord structure. Only creates what doesn't exist."""
        print("[Discord] Setting up EOS structure...")

        structure: dict[str, list[tuple[str, str, str]]] = {
            "🧠 EOS": [
                ("general", "text", "Main conversation with DEX"),
                ("morning-brief", "text", "Daily intelligence from DEX"),
                ("decisions", "text", "Logged decisions"),
                ("wins", "text", "Closed deals and wins"),
                ("agent-activity", "text", "EOS agent activity log"),
            ],
            "⚡ Empyrean Creative": [
                ("empyrean-strategy", "text", "Empyrean Creative strategic decisions"),
                ("empyrean-pipeline", "text", "Empyrean Creative sales pipeline"),
                ("empyrean-outreach", "text", "Empyrean Creative outreach tracking"),
            ],
            "🏢 Lyfe Institute": [
                ("lyfe-strategy", "text", "Lyfe Institute strategy"),
                ("lyfe-pipeline", "text", "Initiate Arena pipeline"),
                ("lyfe-outreach", "text", "Instagram DM tracking"),
            ],
            "👤 Personal Brand": [
                ("brand-strategy", "text", "Personal brand strategy"),
                ("content-ideas", "text", "Content ideas and calendar"),
            ],
            "🎙️ Voice": [
                ("Founder's Office", "voice", ""),
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
        war_room_vc = discord.utils.get(self.guild.voice_channels, name="War Room")
        if war_room_vc:
            await war_room_vc.delete(reason="One voice channel only")
            print("[Discord] Removed War Room voice")

        print(f"[Discord] Structure ready: {len(created)} channels verified")
        return created

    async def align_structure(self) -> None:
        """
        Enforce the canonical EOS channel layout.
        Moves uncategorized channels into 🧠 EOS.
        Removes redundant generic channels.
        Safe to call on every startup.
        """
        print("[Discord] Aligning structure...")

        # Get or create 🧠 EOS category
        eos_cat = discord.utils.get(self.guild.categories, name="🧠 EOS")
        if not eos_cat:
            eos_cat = await self.guild.create_category("🧠 EOS")
            print("[Discord] Created 🧠 EOS category")

        # Recreate #general if deleted, or move if uncategorized
        general = discord.utils.get(self.guild.text_channels, name="general")
        if not general:
            general = await self.guild.create_text_channel(
                name="general",
                topic="Primary conversation with DEX",
                category=eos_cat,
            )
            print("[Discord] Recreated #general")
        elif general.category != eos_cat:
            await general.edit(category=eos_cat)
            print("[Discord] Moved #general → 🧠 EOS")

        # Move these channels into 🧠 EOS if not already there
        move_to_eos = ["morning-brief", "decisions", "wins", "agent-activity"]
        for ch_name in move_to_eos:
            ch = discord.utils.get(self.guild.text_channels, name=ch_name)
            if ch and ch.category != eos_cat:
                await ch.edit(category=eos_cat)
                print(f"[Discord] Moved #{ch_name} → 🧠 EOS")

        # Remove redundant generic channels — company-specific equivalents exist
        for ch_name in ("strategy", "outreach", "content"):
            ch = discord.utils.get(self.guild.text_channels, name=ch_name)
            if ch:
                await ch.delete(reason="Redundant — company-specific channels exist")
                print(f"[Discord] Removed #{ch_name}")

        # War Room guard — belt-and-suspenders
        war_room = discord.utils.get(self.guild.voice_channels, name="War Room")
        if war_room:
            await war_room.delete(reason="One voice channel only")
            print("[Discord] Removed War Room voice")

        print("[Discord] Structure aligned ✅")

    async def update_for_stage_change(
        self,
        company: str,
        new_stage: int,
    ) -> list[str]:
        """Create stage-appropriate channels when a venture advances."""
        stage_channels: dict[int, list[tuple[str, str, str]]] = {
            2: [
                (f"{company}-content", "text", "Content strategy (unlocked Stage 2)"),
                (f"{company}-systems", "text", "Systems and processes"),
            ],
            3: [
                (f"{company}-hiring", "text", "Hiring and team building"),
                (f"{company}-operations", "text", "Operations management"),
            ],
        }

        new_channels = stage_channels.get(new_stage, [])
        category_name = company.replace("_", " ").title()
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
        general = discord.utils.get(self.guild.text_channels, name="general")
        if general:
            await _send_reply(
                general,
                f"🎯 **Stage {new_stage} unlocked for {company}.**\n\n"
                f"New channels and primitives now active.\n"
                f"{AI_NAME} has updated your operating system.\n\n— {AI_NAME}",
            )

        return created


async def _setup_server_structure(guild: discord.Guild) -> None:
    """Called on_ready to ensure EOS Discord structure exists."""
    try:
        mgr = DiscordServerManager(guild)
        await mgr.setup_eos_structure()
        await mgr.align_structure()
    except Exception as e:
        _record_error("server_setup", e)
        print(f"[Discord] Server setup error: {e}")


# ─── Wire extracted modules ─────────────────────────────────────────────────

_handlers.init(
    bot=bot,
    run_gateway=_run_gateway,
    run_day_command=_run_day_command,
    format_day_result=_format_day_result,
    send_day_response=_send_day_response,
    onboarding=_onboarding,
    ve=_ve,
    ai_name_getter=lambda: AI_NAME,
    default_venture_id=_DEFAULT_VENTURE_ID,
    founder_id=FOUNDER_ID,
    start_meeting_mode_fn=start_meeting_mode,
    end_active_meeting_fn=end_active_meeting,
    discord_server_manager_cls=DiscordServerManager,
    send_response_fn=_send_response,
)

_bot_commands.register_commands(
    bot,
    ctx_eos=_ctx_eos,
    gateway=_gateway,
    ve=_ve,
    onboarding=_onboarding,
    run_gateway=_run_gateway,
    run_day_command=_run_day_command,
    format_day_result=_format_day_result,
    send_day_response=_send_day_response,
    ai_name_getter=lambda: AI_NAME,
    default_venture_id=_DEFAULT_VENTURE_ID,
    founder_id=FOUNDER_ID,
    repo_root=_REPO_ROOT,
    discord_server_manager_cls=DiscordServerManager,
)


# ─── Entry point ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    # Register transport implementations into substrate socket layer
    from substrate.sockets.notification import register_notifier, register_chunker
    from substrate.sockets.channel_port import register_channel_router
    from transports.discord.discord_utils import post_to_webhook, chunk_message
    from transports.channels.channel import get_channel_router as _get_channel_router
    register_notifier(post_to_webhook)
    register_chunker(chunk_message)
    register_channel_router(_get_channel_router)

    token = os.getenv("DISCORD_BOT_TOKEN")
    if not token:
        print("[Discord] DISCORD_BOT_TOKEN not set in .env — exiting")
        sys.exit(1)

    print(f"[Discord] Starting {AI_NAME} Discord bot...")
    bot.run(token, reconnect=True)
    # No in-process restart loop — py-cord closes the event loop on exit
    # and it cannot be reused. Docker restart: on-failure handles restarts
    # at the process level, giving each restart a fresh event loop.
